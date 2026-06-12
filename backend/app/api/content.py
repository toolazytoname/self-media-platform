# 内容管理 API
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel, Field

from app.store import store

router = APIRouter()


# ============ Pydantic 模型 ============

class ContentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=0)
    tags: List[str] = []
    platform: str = Field("all", description="目标平台: douyin/xiaohongshu/bilibili/toutiao/wechat/youtube/all")
    # Phase 2: 媒体引用(视频 / 图片)
    media_urls: List[str] = Field(default_factory=list, description="通用媒体 URL 列表")
    video_id: Optional[str] = Field(default=None, description="关联 store.videos.id")
    video_url: Optional[str] = Field(default=None, description="冗余存储的视频 URL")
    video_duration: Optional[int] = Field(default=None, description="视频秒数")
    thumbnail_url: Optional[str] = Field(default=None, description="封面/缩略图 URL")
    image_id: Optional[str] = Field(default=None, description="关联 store.images.id(封面图)")


class ContentCreate(ContentBase):
    pass


class ContentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    body: Optional[str] = None
    tags: Optional[List[str]] = None
    platform: Optional[str] = None
    status: Optional[str] = Field(None, description="draft/pending/published/failed/uploading")
    # Phase 2 媒体字段
    media_urls: Optional[List[str]] = None
    video_id: Optional[str] = None
    video_url: Optional[str] = None
    video_duration: Optional[int] = None
    thumbnail_url: Optional[str] = None
    image_id: Optional[str] = None


class ContentResponse(ContentBase):
    id: str
    status: str
    created_at: str
    updated_at: str


class ContentListResponse(BaseModel):
    total: int
    items: List[ContentResponse]
    skip: int
    limit: int


VALID_STATUSES = {"draft", "pending", "published", "failed", "archived", "uploading"}
VALID_PLATFORMS = {"douyin", "xiaohongshu", "bilibili", "toutiao", "wechat", "youtube", "all"}


# ============ 路由 ============

@router.post("/", response_model=ContentResponse, status_code=201)
@router.post("", response_model=ContentResponse, status_code=201)
async def create_content(content: ContentCreate):
    """创建内容"""
    if content.platform not in VALID_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Invalid platform: {content.platform}")
    item = store.add_content(content.model_dump())
    return item


@router.get("/", response_model=ContentListResponse)
@router.get("", response_model=ContentListResponse)
async def list_content(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    platform: Optional[str] = None,
    keyword: Optional[str] = None,
):
    """列出内容（支持筛选/分页/搜索）"""
    if status and status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    if platform and platform not in VALID_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Invalid platform: {platform}")

    all_filtered = store.list_contents(skip=0, limit=10_000, status=status, platform=platform, keyword=keyword)
    items = all_filtered[skip:skip + limit]
    return ContentListResponse(total=len(all_filtered), items=items, skip=skip, limit=limit)


@router.get("/{content_id}", response_model=ContentResponse)
async def get_content(content_id: str):
    """获取内容详情"""
    item = store.get_content(content_id)
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    return item


@router.put("/{content_id}", response_model=ContentResponse)
async def update_content(content_id: str, update: ContentUpdate):
    """更新内容"""
    if update.status and update.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {update.status}")
    if update.platform and update.platform not in VALID_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Invalid platform: {update.platform}")
    item = store.update_content(content_id, update.model_dump(exclude_unset=True))
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    return item


@router.delete("/{content_id}")
async def delete_content(content_id: str):
    """删除内容"""
    if not store.delete_content(content_id):
        raise HTTPException(status_code=404, detail="Content not found")
    return {"message": "deleted", "id": content_id}


@router.post("/{content_id}/submit-review")
async def submit_for_review(content_id: str):
    """提交审核（创建审核任务并将内容状态改为 pending）"""
    content = store.get_content(content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    store.add_review({
        "content_id": content_id,
        "content_title": content.get("title", ""),
        "content_body": content.get("body", ""),
    })
    store.update_content(content_id, {"status": "pending"})
    return {"message": "submitted for review", "content_id": content_id}


@router.post("/{content_id}/duplicate", status_code=201)
async def duplicate_content(content_id: str):
    """复制内容（创建草稿副本）"""
    content = store.get_content(content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    new_item = {
        "title": (content.get("title") or "") + " (副本)",
        "body": content.get("body", ""),
        "tags": list(content.get("tags") or []),
        "platform": content.get("platform", "all"),
    }
    new_content = store.add_content(new_item)
    return new_content


class BulkDeleteRequest(BaseModel):
    ids: List[str] = Field(..., min_length=1, max_length=100)


class BulkUpdateRequest(BaseModel):
    ids: List[str] = Field(..., min_length=1, max_length=100)
    platform: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None


@router.post("/bulk/delete")
async def bulk_delete(req: BulkDeleteRequest):
    """批量删除"""
    deleted = []
    failed = []
    for cid in req.ids:
        if store.delete_content(cid):
            deleted.append(cid)
        else:
            failed.append(cid)
    return {"deleted": deleted, "failed": failed, "deleted_count": len(deleted)}


@router.post("/bulk/update")
async def bulk_update(req: BulkUpdateRequest):
    """批量更新"""
    if req.status and req.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {req.status}")
    if req.platform and req.platform not in VALID_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Invalid platform: {req.platform}")

    updated = []
    failed = []
    update_payload = {}
    if req.platform is not None:
        update_payload["platform"] = req.platform
    if req.status is not None:
        update_payload["status"] = req.status
    if req.tags is not None:
        update_payload["tags"] = req.tags

    for cid in req.ids:
        item = store.update_content(cid, update_payload)
        if item:
            updated.append(cid)
        else:
            failed.append(cid)
    return {"updated": updated, "failed": failed, "updated_count": len(updated)}


@router.get("/export/all")
async def export_all(format: str = "json", status: Optional[str] = None, platform: Optional[str] = None):
    """导出内容（json / markdown / csv）"""
    items = store.list_contents(skip=0, limit=10000, status=status, platform=platform)
    if format == "json":
        return items
    if format == "markdown":
        from io import StringIO
        buf = StringIO()
        for c in items:
            buf.write(f"# {c.get('title','')}\n\n")
            buf.write(f"> 平台: {c.get('platform','')} | 状态: {c.get('status','')} | 标签: {', '.join(c.get('tags') or [])}\n\n")
            buf.write(c.get("body", "") + "\n\n---\n\n")
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(buf.getvalue(), media_type="text/markdown")
    if format == "csv":
        import csv
        from io import StringIO
        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow(["id", "title", "body", "platform", "status", "tags", "created_at", "updated_at"])
        for c in items:
            writer.writerow([
                c.get("id", ""),
                c.get("title", ""),
                c.get("body", ""),
                c.get("platform", ""),
                c.get("status", ""),
                ";".join(c.get("tags") or []),
                c.get("created_at", ""),
                c.get("updated_at", ""),
            ])
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(buf.getvalue(), media_type="text/csv")
    raise HTTPException(status_code=400, detail="format must be json/markdown/csv")
