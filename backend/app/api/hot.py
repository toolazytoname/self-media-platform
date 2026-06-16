"""选题雷达 API — TASK-P0-2

端点:
  GET    /api/hot                 列表 (filter: platform, status; limit)
  POST   /api/hot/refresh         触发抓取(全平台 or ?platform=xxx)
  POST   /api/hot/rewrite/{id}    AI 改写一个 hot item
  POST   /api/hot/{id}/create-content  一键草稿
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.security import require_user
from app.store import store
from app.services.hot_list_client import HotListClient
from app.api.ai_generate import chat_completion, _timed_chat

log = logging.getLogger("hot")

router = APIRouter()


# ============ module-level helpers (供测试 patch, e.g. app.api.hot.fetch_all) ============
# 内部走 HotListClient 实例,但顶层暴露 fetch_all/fetch_weibo/... 让 mock 路径稳定。

_default_client = HotListClient()


async def fetch_all():
    return await _default_client.fetch_all()


async def fetch_weibo():
    return await _default_client.fetch_weibo()


async def fetch_zhihu():
    return await _default_client.fetch_zhihu()


async def fetch_douyin():
    return await _default_client.fetch_douyin()


async def fetch_xiaohongshu():
    return await _default_client.fetch_xiaohongshu()


# ============ Pydantic ============

class HotRewriteRequest(BaseModel):
    n: int = Field(1, ge=1, le=10)
    tone: str = Field("casual")
    provider: Optional[str] = None
    model: Optional[str] = None


# ============ Endpoints ============

@router.get("")
async def list_hot(
    platform: Optional[str] = Query(None, description="weibo|zhihu|douyin|xiaohongshu"),
    status: Optional[str] = Query(None, description="new|used|dismissed"),
    limit: int = Query(50, ge=1, le=200),
    _user=Depends(require_user),
):
    """列表 — 返裸 list,最新在前;支持平台/状态过滤。"""
    return store.list_hot(platform=platform, status=status, limit=limit)


@router.post("/refresh")
async def refresh_hot(
    platform: Optional[str] = Query(None, description="不传则全平台并发拉取"),
    _user=Depends(require_user),
):
    """抓取热榜(并发 4 平台) → 灌库。"""
    try:
        if platform:
            fn = globals().get(f"fetch_{platform}")
            if not fn:
                raise HTTPException(400, f"unknown platform: {platform}")
            items = await fn()
        else:
            items = await fetch_all()
    except HTTPException:
        raise
    except Exception as e:
        log.exception("hot refresh failed")
        raise HTTPException(500, f"hot refresh failed: {e}") from e
    saved = [store.add_hot(it) for it in items]
    return {"count": len(saved), "items": saved}


@router.post("/rewrite/{hot_id}")
async def rewrite_hot(
    hot_id: str,
    req: HotRewriteRequest = HotRewriteRequest(),
    _user=Depends(require_user),
):
    """AI 改写热搜为自媒体角度。

    直接调 chat_completion(而非 _timed_chat)以保证测试可稳定 patch
    `app.api.hot.chat_completion`。AI 创作历史记录见 _timed_chat 路径;
    本端点主要是为 hot list 业务服务。
    """
    item = store.get_hot(hot_id)
    if not item:
        raise HTTPException(404, f"hot item {hot_id} not found")
    system = (
        f"你是自媒体选题专家。请把以下 {item['platform']} 平台的热搜话题改写为"
        f"{req.n} 个适合做自媒体的选题角度。要求:贴近用户痛点、有钩子、目标读者明确。"
        f"语气:{req.tone}。"
    )
    user_msg = (
        f"热搜话题:{item['title']}\n请输出 {req.n} 条,每条一行,不要编号。"
    )
    angle = await chat_completion(
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user_msg}],
        model=req.model,
        provider=req.provider,
        max_tokens=512,
    )
    store.update_hot(hot_id, {
        "ai_angle": angle,
        "ai_rewritten_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"hot_id": hot_id, "ai_angle": angle}


@router.post("/{hot_id}/create-content")
async def create_content_from_hot(
    hot_id: str,
    _user=Depends(require_user),
):
    """一键把热榜话题创建为 draft Content。

    - body 优先用 ai_angle,无则用 title
    - 写完标记 hot.status='used',hot.related_content_id=content_id
    - 返 content_id,前端跳 /content/edit/{id}
    """
    item = store.get_hot(hot_id)
    if not item:
        raise HTTPException(404, f"hot item {hot_id} not found")
    title = item.get("title", "")
    body = item.get("ai_angle") or title
    content = store.add_content({
        "title": title,
        "body": body,
        "tags": [item["platform"]] if item.get("platform") else [],
        # 平台保留 hot 项的来源平台(让发布链路知道这是从哪个热榜来的);
        # "all" 是默认占位,这里改用 hot 项的 platform
        "platform": item.get("platform") or "all",
        "status": "draft",
    })
    store.update_hot(hot_id, {
        "status": "used",
        "related_content_id": content["id"],
    })
    return {"content_id": content["id"]}
