"""数据回流闭环 — P1-2 API

端点:
  POST /api/metrics/record             录入一条数据(content_id + views/likes/comments/shares)
  GET  /api/metrics/content/{id}        取某 content 指标
  GET  /api/metrics/trending?top_n=10   趋势 top 内容(可按平台过滤)
  GET  /api/metrics/best-time?platform  最佳发布时段统计

MVP: 手工录入为主。后续可接自动抓取(知乎/微博公开 API)。
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.security import require_user
from app.store import store
from app.services.metrics_service import (
    record_metrics,
    get_metrics,
    get_trending,
    compute_best_time,
)

log = logging.getLogger("metrics")

router = APIRouter()


class RecordMetricsRequest(BaseModel):
    content_id: str
    views: int = Field(0, ge=0)
    likes: int = Field(0, ge=0)
    comments: int = Field(0, ge=0)
    shares: int = Field(0, ge=0)
    platform: Optional[str] = None
    source: str = "manual"


@router.post("/record", status_code=201)
async def record(req: RecordMetricsRequest, _user=Depends(require_user)):
    """录入一条数据(content 必须存在)。"""
    if not store.get_content(req.content_id):
        raise HTTPException(400, f"content {req.content_id} not found")
    rec = record_metrics(
        req.content_id,
        views=req.views,
        likes=req.likes,
        comments=req.comments,
        shares=req.shares,
        platform=req.platform,
        source=req.source,
    )
    return rec


@router.get("/content/{content_id}")
async def get_content_metrics(content_id: str, _user=Depends(require_user)):
    """取某 content 的指标(404 if 没数据)。"""
    m = get_metrics(content_id)
    if not m:
        raise HTTPException(404, f"no metrics for content {content_id}")
    return m


@router.get("/trending")
async def trending(
    top_n: int = Query(10, ge=1, le=50),
    platform: Optional[str] = Query(None),
    _user=Depends(require_user),
):
    """top N 高表现内容(简单综合得分: views + likes*5 + comments*10)。"""
    items = get_trending(top_n=top_n, platform=platform)
    return {"items": items, "count": len(items)}


@router.get("/best-time")
async def best_time(
    platform: Optional[str] = Query(None),
    _user=Depends(require_user),
):
    """统计"最佳发布时段"(基于历史 publish_records + metrics)。

    返回: {best_hour, best_avg_views, sample_size, avg_views_by_hour: {0..23: avg}}
    """
    result = compute_best_time(platform=platform)
    if not result:
        return {
            "best_hour": None,
            "best_avg_views": None,
            "sample_size": 0,
            "avg_views_by_hour": {},
            "note": "无已发布 + 已录入指标的数据 — 需要先录入 metrics",
        }
    return result
