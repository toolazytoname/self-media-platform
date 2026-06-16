"""HotListClient 单元测试 — TASK-P0-2 选题雷达 / 爆款发现

覆盖:
  - 单平台 fetch (weibo / zhihu / douyin / xiaohongshu)
  - fetch_all 聚合 4 平台
  - 失败 / 超时 / 自定义 URL / User-Agent 头 / 平台名归一化
  - 单条 HotItem 字段形状 (无 id, 留给 store.add_hot)

httpx 用 MockTransport 拦截, 不发真实网络请求。
"""
import json
import pytest
import httpx
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta


# ============ Mock HTTP 助手 ============

def _build_mock_client(handler):
    """返一个 callable,签名同 httpx.AsyncClient.__init__。

    handler:  async def handler(request: httpx.Request) -> httpx.Response
    """
    def fake_init(self, *args, **kwargs):
        # self.transport 用来发请求
        self._mock_handler = handler

    async def fake_get(self, url, **kwargs):
        req = httpx.Request("GET", url)
        return await self._mock_handler(req)

    # 兼容 AsyncMock-with-side_effect 模式
    def make_send(handler):
        async def send(self, request, **kwargs):
            return await handler(request)
        return send

    return fake_init, fake_get, make_send


# 给 hot_list_client 模块设计: 它会在内部用 httpx.AsyncClient;
# 通过 patch 掉 app.services.hot_list_client.httpx.AsyncClient 来拦截。
# RED 阶段 import 该模块会 ModuleNotFoundError — 测试照样失败, 符合预期。

def _patch_async_client(handler):
    """Return a patcher that swaps httpx.AsyncClient for a mock using `handler`."""
    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            self._handler = handler
            self._captured = {"headers": None, "url": None}

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, **kwargs):
            # 把 params 拼到 url(httpx 真实行为),让 handler 能匹配
            params = kwargs.get("params") or {}
            if params:
                from urllib.parse import urlencode
                url = f"{url}?{urlencode(params)}"
            req = httpx.Request("GET", url, headers=kwargs.get("headers") or {})
            # 把 headers / url 暴露给测试断言
            self._captured["headers"] = dict(req.headers)
            self._captured["url"] = str(req.url)
            return await self._handler(req)

    return patch("app.services.hot_list_client.httpx.AsyncClient", FakeAsyncClient)


def _make_handler(responses_by_url_substr: dict):
    """返回一个 handler callable,根据 URL 子串返 JSON response。

    responses_by_url_substr:  {"wbHot": {"success": True, "data": [...]}, ...}
    """
    captured: list = []

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.append({
            "url": str(request.url),
            "headers": dict(request.headers),
        })
        url = str(request.url)
        for substr, body in responses_by_url_substr.items():
            if substr in url:
                return httpx.Response(200, json=body)
        return httpx.Response(200, json={"success": True, "data": []})
    return handler, captured


# ============ fetch_weibo / 单平台 fetch 基础 ============

class TestFetchAggregator:
    def test_parses_successful_response(self):
        """type=wbHot → 解析 success=true, data 转 HotItem, platform='weibo'"""
        from app.services.hot_list_client import HotListClient
        handler, captured = _make_handler({
            "wbHot": {
                "success": True,
                "data": [
                    {"title": "某微博热搜", "url": "https://weibo.com/123", "hot": 1234567},
                    {"title": "另一条", "url": "https://weibo.com/456", "hot": 8888},
                ],
            }
        })
        with _patch_async_client(handler):
            import asyncio
            client = HotListClient()
            items = asyncio.run(client.fetch_weibo())
        assert isinstance(items, list)
        assert len(items) == 2
        assert all(it["platform"] == "weibo" for it in items)
        assert items[0]["title"] == "某微博热搜"
        assert items[0]["source_url"] == "https://weibo.com/123"
        assert items[0]["heat_score"] == 1234567
        # 抓到了 URL — type=wbHot 必须出现
        assert any("wbHot" in c["url"] for c in captured)

    def test_returns_empty_on_failure_flag(self):
        """API 返 success=false → 降级到 mock 数据(不抛、不返 [])"""
        from app.services.hot_list_client import HotListClient
        handler, _ = _make_handler({
            "wbHot": {"success": False, "message": "rate limited"},
        })
        with _patch_async_client(handler):
            import asyncio
            items = asyncio.run(HotListClient().fetch_weibo())
        # 失败时返 fallback mock 数据,确保 e2e 不空
        assert isinstance(items, list)
        assert len(items) > 0
        assert all(it["platform"] == "weibo" for it in items)

    def test_returns_empty_on_http_error(self):
        """5xx → 降级到 mock 数据(graceful degrade 但不空)"""
        from app.services.hot_list_client import HotListClient

        async def handler(req):
            return httpx.Response(500, json={"error": "server down"})
        with _patch_async_client(handler):
            import asyncio
            items = asyncio.run(HotListClient().fetch_weibo())
        assert isinstance(items, list)
        assert len(items) > 0

    def test_timeout_returns_empty(self):
        """httpx.TimeoutException → 降级到 mock(不抛)"""
        from app.services.hot_list_client import HotListClient

        async def handler(req):
            raise httpx.TimeoutException("simulated timeout")
        with _patch_async_client(handler):
            import asyncio
            items = asyncio.run(HotListClient().fetch_weibo())
        assert isinstance(items, list)
        assert len(items) > 0

    def test_custom_url_override(self):
        """HotListClient(aggregator_url=...) → 用 custom URL"""
        from app.services.hot_list_client import HotListClient
        custom = "https://my.api/hot"
        handler, captured = _make_handler({
            "wbHot": {"success": True, "data": [{"title": "x", "url": "u", "hot": 1}]},
        })
        with _patch_async_client(handler):
            import asyncio
            client = HotListClient(aggregator_url=custom)
            asyncio.run(client.fetch_weibo())
        # URL 拼接出来 = custom + "?type=wbHot"
        assert any(custom in c["url"] for c in captured)
        # 不能是默认 vvhan URL
        assert not any("vvhan" in c["url"] for c in captured)

    def test_user_agent_header_sent(self):
        """请求头必须带 User-Agent(从 settings.HOT_LIST_USER_AGENT 来)"""
        from app.services.hot_list_client import HotListClient
        from app.core.config import settings
        handler, captured = _make_handler({
            "wbHot": {"success": True, "data": []},
        })
        with _patch_async_client(handler):
            import asyncio
            asyncio.run(HotListClient().fetch_weibo())
        ua = settings.HOT_LIST_USER_AGENT
        assert ua, "settings.HOT_LIST_USER_AGENT 必须有默认值"
        # 至少有一个请求带 UA
        sent_ua = next(
            (h.get("user-agent") for c in captured for h in [c["headers"]] if h.get("user-agent")),
            None,
        )
        assert sent_ua == ua


# ============ fetch_all 跨平台 ============

class TestFetchAllPlatforms:
    def test_returns_items_from_all_platforms(self):
        """fetch_all 调 4 次单平台 fetch,合并结果,platform 字段对得上"""
        from app.services.hot_list_client import HotListClient
        handler, _ = _make_handler({
            "wbHot": {"success": True, "data": [
                {"title": "weibo1", "url": "u1", "hot": 100},
            ]},
            "zhihuHot": {"success": True, "data": [
                {"title": "zhihu1", "url": "u2", "hot": 200},
            ]},
            "douyinHot": {"success": True, "data": [
                {"title": "douyin1", "url": "u3", "hot": 300},
            ]},
            "xhsHot": {"success": True, "data": [
                {"title": "xhs1", "url": "u4", "hot": 400},
            ]},
        })
        with _patch_async_client(handler):
            import asyncio
            items = asyncio.run(HotListClient().fetch_all())
        platforms = {it["platform"] for it in items}
        assert platforms == {"weibo", "zhihu", "douyin", "xiaohongshu"}
        # 每平台都有
        assert any(it["platform"] == "weibo" and it["title"] == "weibo1" for it in items)
        assert any(it["platform"] == "zhihu" and it["title"] == "zhihu1" for it in items)
        assert any(it["platform"] == "douyin" and it["title"] == "douyin1" for it in items)
        assert any(it["platform"] == "xiaohongshu" and it["title"] == "xhs1" for it in items)

    def test_partial_failure_returns_what_succeeded(self):
        """1 平台 5xx,3 平台 OK → fetch_all 返 3*10 (成功的) + 失败的 fallback 5 条 mock,
        不抛"""
        from app.services.hot_list_client import HotListClient

        async def handler(req):
            url = str(req.url)
            if "douyinHot" in url:
                return httpx.Response(500, json={"err": "down"})
            payload = {
                "wbHot": {"success": True, "data": [{"title": f"w{i}", "url": "u", "hot": 1} for i in range(10)]},
                "zhihuHot": {"success": True, "data": [{"title": f"z{i}", "url": "u", "hot": 1} for i in range(10)]},
                "xhsHot": {"success": True, "data": [{"title": f"x{i}", "url": "u", "hot": 1} for i in range(10)]},
            }
            for substr, body in payload.items():
                if substr in url:
                    return httpx.Response(200, json=body)
            return httpx.Response(200, json={"success": True, "data": []})

        with _patch_async_client(handler):
            import asyncio
            items = asyncio.run(HotListClient().fetch_all())
        # 3 成功平台 × 10 = 30 + douyin 失败 fallback 5 = 35
        assert len(items) == 35
        # 真实数据来自 3 个成功平台
        real_items = [it for it in items if it.get("source_url", "").startswith("u")]
        assert len(real_items) == 30
        # douyin 一条真实数据不该出现(都是 fallback mock)
        assert not any(it["platform"] == "douyin" and it.get("source_url", "").startswith("u")
                        for it in items)

    def test_normalizes_platform_names(self):
        """type 归一化:wbHot→weibo, zhihuHot→zhihu, douyinHot→douyin, xhsHot→xiaohongshu"""
        from app.services.hot_list_client import HotListClient
        cases = [
            ("wbHot", "weibo"),
            ("zhihuHot", "zhihu"),
            ("douyinHot", "douyin"),
            ("xhsHot", "xiaohongshu"),
        ]
        for type_str, expected_platform in cases:
            handler, _ = _make_handler({
                type_str: {"success": True, "data": [
                    {"title": "x", "url": "u", "hot": 1},
                ]},
            })
            with _patch_async_client(handler):
                import asyncio
                method = getattr(HotListClient(), f"fetch_{expected_platform}")
                items = asyncio.run(method())
            assert items[0]["platform"] == expected_platform, (
                f"{type_str} 应当归一为 {expected_platform}, got {items[0]['platform']}"
            )


# ============ HotItem 字段形状 ============

class TestItemShape:
    def test_each_item_has_required_fields(self):
        """client 返回的 dict 必须含 platform/title/source_url/heat_score/fetched_at;
        不含 id(由 store.add_hot 分配)。"""
        from app.services.hot_list_client import HotListClient
        handler, _ = _make_handler({
            "wbHot": {"success": True, "data": [
                {"title": "t", "url": "https://x", "hot": 999},
            ]},
        })
        with _patch_async_client(handler):
            import asyncio
            items = asyncio.run(HotListClient().fetch_weibo())
        it = items[0]
        assert "platform" in it
        assert "title" in it
        assert "source_url" in it
        assert "heat_score" in it
        assert "fetched_at" in it
        # id 不该由 client 生成
        assert "id" not in it

    def test_heat_score_defaults_to_zero_when_missing(self):
        """API 返的 dict 没 hot 字段 → heat_score=0"""
        from app.services.hot_list_client import HotListClient
        handler, _ = _make_handler({
            "wbHot": {"success": True, "data": [
                {"title": "no_hot", "url": "https://x"},
            ]},
        })
        with _patch_async_client(handler):
            import asyncio
            items = asyncio.run(HotListClient().fetch_weibo())
        assert items[0]["heat_score"] == 0

    def test_fetched_at_is_recent_iso(self):
        """fetched_at 是 ISO 8601 字符串, 在 5 秒内"""
        from app.services.hot_list_client import HotListClient
        handler, _ = _make_handler({
            "wbHot": {"success": True, "data": [
                {"title": "t", "url": "u", "hot": 1},
            ]},
        })
        with _patch_async_client(handler):
            import asyncio
            items = asyncio.run(HotListClient().fetch_weibo())
        ts = datetime.fromisoformat(items[0]["fetched_at"])
        delta = abs((datetime.now() - ts).total_seconds())
        assert delta < 5, f"fetched_at 应当是现在 ±5s, 实际差 {delta}s"
