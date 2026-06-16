"""数据回流闭环 — P1-2 service

策略(快速可行版本):
- 手工录入为主(各平台反爬限制大, 自动抓取留 TODO)
- 趋势 API: top 内容 / 最佳发布时段
- 后续可接: 知乎热榜/微博热搜 公开数据源

存储: store.publish_metrics: dict[content_id, {views, likes, comments, shares, ...}]
"""
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

log = logging.getLogger("metrics_service")


# ============ 录入 / 查询 ============

def record_metrics(
    content_id: str,
    *,
    views: int = 0,
    likes: int = 0,
    comments: int = 0,
    shares: int = 0,
    platform: Optional[str] = None,
    source: str = "manual",
) -> Dict[str, Any]:
    """录入一条数据(同 content_id 覆盖)。"""
    from app.store import store  # 避免循环 import
    rec: Dict[str, Any] = {
        "content_id": content_id,
        "views": int(views),
        "likes": int(likes),
        "comments": int(comments),
        "shares": int(shares),
        "platform": platform,
        "source": source,
        "fetched_at": datetime.now().isoformat(),
    }
    store.publish_metrics[content_id] = rec
    return rec


def get_metrics(content_id: str) -> Optional[Dict[str, Any]]:
    from app.store import store
    return store.publish_metrics.get(content_id)


def list_all_metrics() -> List[Dict[str, Any]]:
    from app.store import store
    return list(store.publish_metrics.values())


# ============ 趋势: top 表现内容 ============

def get_trending(top_n: int = 10, platform: Optional[str] = None) -> List[Dict[str, Any]]:
    """top N 高 views 内容(可按平台过滤)。"""
    from app.store import store
    items = list_all_metrics()
    if platform:
        items = [m for m in items if m.get("platform") == platform]
    # 计算综合得分(简单加权: views * 1 + likes * 5 + comments * 10)
    def score(m: Dict[str, Any]) -> int:
        return m.get("views", 0) + m.get("likes", 0) * 5 + m.get("comments", 0) * 10
    items.sort(key=score, reverse=True)
    return items[:top_n]


# ============ 最佳发布时段统计 ============

def compute_best_time(platform: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """根据历史 publish_records + metrics 统计每个小时的"平均 views"。

    返回: {best_hour, sample_size, avg_views_by_hour: {hour: avg_views}}
    """
    from app.store import store
    by_hour: Dict[int, List[int]] = defaultdict(list)
    sample_size = 0
    for rec in store.publish_records:
        if rec.get("status") != "published":
            continue
        if platform and rec.get("platform") != platform:
            continue
        cid = rec.get("content_id")
        m = store.publish_metrics.get(cid)
        if not m:
            continue
        # 取 scheduled_time 或 attempted_at
        ts = rec.get("scheduled_time") or rec.get("attempted_at")
        if not ts:
            continue
        try:
            hour = datetime.fromisoformat(ts).hour
        except Exception:
            continue
        by_hour[hour].append(m.get("views", 0))
        sample_size += 1

    if sample_size == 0:
        return None

    avg = {h: int(sum(v) / len(v)) for h, v in by_hour.items()}
    best_hour = max(avg, key=avg.get)
    return {
        "best_hour": best_hour,
        "best_avg_views": avg[best_hour],
        "sample_size": sample_size,
        "avg_views_by_hour": avg,
    }


__all__ = [
    "record_metrics",
    "get_metrics",
    "list_all_metrics",
    "get_trending",
    "compute_best_time",
]
