# 内容管理 API

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()


# ============ 数据模型 ============

class ContentBase(BaseModel):
    title: str
    body: str
    tags: List[str] = []
    platform: str = "all"


class ContentCreate(ContentBase):
    pass


class ContentUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None


class ContentResponse(ContentBase):
    id: str
    status: str
    created_at: datetime
    updated_at: datetime


# ============ 路由 ============

CONTENT_STORE = []  # 临时存储，生产环境用数据库


@router.post("/", response_model=ContentResponse)
async def create_content(content: ContentCreate):
    """创建内容"""
    now = datetime.now()
    item = ContentResponse(
        id=f"content_{len(CONTENT_STORE) + 1}",
        **content.model_dump(),
        status="draft",
        created_at=now,
        updated_at=now
    )
    CONTENT_STORE.append(item)
    return item


@router.get("/")
async def list_content(skip: int = 0, limit: int = 20):
    """列出内容"""
    return CONTENT_STORE[skip:skip+limit]


@router.get("/{content_id}")
async def get_content(content_id: str):
    """获取内容详情"""
    for item in CONTENT_STORE:
        if item.id == content_id:
            return item
    raise HTTPException(status_code=404, detail="Content not found")


@router.put("/{content_id}")
async def update_content(content_id: str, update: ContentUpdate):
    """更新内容"""
    for i, item in enumerate(CONTENT_STORE):
        if item.id == content_id:
            update_data = update.model_dump(exclude_unset=True)
            for k, v in update_data.items():
                setattr(item, k, v)
            item.updated_at = datetime.now()
            return item
    raise HTTPException(status_code=404, detail="Content not found")


@router.delete("/{content_id}")
async def delete_content(content_id: str):
    """删除内容"""
    global CONTENT_STORE
    for i, item in enumerate(CONTENT_STORE):
        if item.id == content_id:
            CONTENT_STORE.pop(i)
            return {"message": "deleted"}
    raise HTTPException(status_code=404, detail="Content not found")