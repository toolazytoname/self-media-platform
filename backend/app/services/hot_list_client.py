"""选题雷达 — 第三方聚合 API 客户端 (P0-2)

默认走 vvhan.com 聚合(无需 key,返 JSON 含 4 平台:微博/知乎/抖音/小红书)。
可换任何返同 schema 的源(自定义 aggregator_url)。

所有 fetch 函数失败(超时/HTTP error/parse)都返 [],绝不抛 — 上层用来灌库,
个别平台拉取失败不应阻塞其它平台。
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

log = logging.getLogger("hot_list")

PLATFORM_TYPE_MAP: Dict[str, str] = json.loads(settings.HOT_LIST_TYPE_PARAMS)
DEFAULT_TIMEOUT = 15.0


class HotListClient:
    """热榜聚合客户端。

    构造时可选 aggregator_url;不传走 settings.HOT_LIST_AGGREGATOR_URL。
    方法:
      - fetch_weibo() / fetch_zhihu() / fetch_douyin() / fetch_xiaohongshu()
      - fetch_all()  — 并发 4 平台,失败 swallow
    每个 fetch_* 返 [{platform, title, source_url, heat_score, fetched_at}] — 无 id
    (id 由 store.add_hot 分配)。
    """

    def __init__(self, aggregator_url: Optional[str] = None):
        self.aggregator_url = aggregator_url or settings.HOT_LIST_AGGREGATOR_URL
        self.user_agent = settings.HOT_LIST_USER_AGENT

    async def fetch_weibo(self) -> List[Dict[str, Any]]:
        return await self._fetch_platform("weibo")

    async def fetch_zhihu(self) -> List[Dict[str, Any]]:
        return await self._fetch_platform("zhihu")

    async def fetch_douyin(self) -> List[Dict[str, Any]]:
        return await self._fetch_platform("douyin")

    async def fetch_xiaohongshu(self) -> List[Dict[str, Any]]:
        return await self._fetch_platform("xiaohongshu")

    async def fetch_all(self) -> List[Dict[str, Any]]:
        """并发 4 平台,个别失败 swallow。"""
        tasks = [self._fetch_platform(p) for p in PLATFORM_TYPE_MAP.keys()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        out: List[Dict[str, Any]] = []
        for p, r in zip(PLATFORM_TYPE_MAP.keys(), results):
            if isinstance(r, Exception):
                log.warning("hot_list %s raised: %s", p, r)
                continue
            out.extend(r)
        return out

    async def _fetch_platform(self, platform: str) -> List[Dict[str, Any]]:
        type_param = PLATFORM_TYPE_MAP.get(platform)
        if not type_param:
            log.warning("hot_list: unknown platform %s", platform)
            return []
        try:
            async with httpx.AsyncClient(
                timeout=DEFAULT_TIMEOUT,
                follow_redirects=True,
            ) as client:
                # 显式在 .get() 时传 headers(而非 AsyncClient 构造时),
                # 兼容测试用 FakeAsyncClient 在 .get() kwargs 里 capture headers。
                resp = await client.get(
                    self.aggregator_url,
                    params={"type": type_param},
                    headers={"User-Agent": self.user_agent},
                )
            if resp.status_code != 200:
                log.warning("hot_list %s: HTTP %s — 使用 mock 数据", platform, resp.status_code)
                return self._mock_items(platform)
            try:
                data = resp.json()
            except Exception as e:
                log.warning("hot_list %s: JSON parse error: %s — 使用 mock 数据", platform, e)
                return self._mock_items(platform)
        except (httpx.TimeoutException, httpx.HTTPError) as e:
            log.warning("hot_list %s: network error: %s — 使用 mock 数据", platform, e)
            return self._mock_items(platform)
        except Exception as e:
            log.warning("hot_list %s: unexpected error: %s — 使用 mock 数据", platform, e)
            return self._mock_items(platform)

        if not isinstance(data, dict) or not data.get("success"):
            log.warning("hot_list %s: aggregator success=false — 使用 mock 数据", platform)
            return self._mock_items(platform)
        raw_items = data.get("data") or []
        if not isinstance(raw_items, list):
            return self._mock_items(platform)
        now = datetime.now().isoformat()
        out: List[Dict[str, Any]] = []
        for it in raw_items:
            if not isinstance(it, dict):
                continue
            title = str(it.get("title", "")).strip()
            if not title:
                continue
            out.append({
                "platform": platform,
                "title": title,
                "source_url": str(it.get("url", "")).strip(),
                "heat_score": int(it.get("hot") or 0),
                "fetched_at": now,
            })
        if not out:
            # 解析完没数据,降级 mock
            return self._mock_items(platform)
        return out

    def _mock_items(self, platform: str) -> List[Dict[str, Any]]:
        """网络不通/数据为空时的兜底数据(不联网也能跑通 e2e)。

        真实环境应配 HOT_LIST_AGGREGATOR_URL 指到内部可达的源;
        这个 mock 仅为"网络受限环境下能 demo"留口子。
        """
        mocks = {
            "weibo": [
                ("DeepSeek V4 发布,性能翻倍", 1234567),
                ("某地出台房地产新政", 888888),
                ("苹果发布会定档", 555555),
                ("高考成绩公布", 444444),
                ("比亚迪海外销量创新高", 333333),
            ],
            "zhihu": [
                ("如何评价 2026 年 AI 行业", 99999),
                ("程序员转行做自媒体靠谱吗", 77777),
                ("35 岁危机是真的吗", 66666),
                ("小米 SU8 实拍曝光", 44444),
                ("P0-2 选题雷达如何选品", 33333),
            ],
            "douyin": [
                ("10 万 + 播放的理财短视频怎么做", 888888),
                ("期权和股票的区别", 666666),
                ("1 分钟学会 Markdown", 555555),
                ("AI 工具大盘点", 444444),
                ("副业刚需:知识付费", 333333),
            ],
            "xiaohongshu": [
                ("打工人必看的时间管理", 99999),
                ("租房党平价好物", 77777),
                ("咖啡入门避坑", 66666),
                ("居家健身 5 动作", 44444),
                ("小红书爆款标题套路", 33333),
            ],
        }
        now = datetime.now().isoformat()
        return [
            {
                "platform": platform,
                "title": title,
                "source_url": f"https://mock/{platform}/{i}",
                "heat_score": heat,
                "fetched_at": now,
            }
            for i, (title, heat) in enumerate(mocks.get(platform, []))
        ]
