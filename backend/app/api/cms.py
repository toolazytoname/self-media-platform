# CMS 管理 API
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from app.store import store

router = APIRouter()


# ============ Pydantic 模型 ============

class TopicCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    priority: int = Field(3, ge=1, le=5)


class TopicUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    status: Optional[str] = None  # active/done/archived


class MaterialCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    type: str = Field(..., description="image/video/audio/text")
    path: str = Field(..., min_length=1)
    tags: List[str] = []
    description: str = ""


class MaterialUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    type: Optional[str] = None
    path: Optional[str] = None
    tags: Optional[List[str]] = None
    description: Optional[str] = None


class ReviewUpdate(BaseModel):
    status: str = Field(..., description="pending/approved/rejected")
    comment: Optional[str] = None


VALID_TOPIC_STATUSES = {"active", "done", "archived"}
VALID_MATERIAL_TYPES = {"image", "video", "audio", "text"}
VALID_REVIEW_STATUSES = {"pending", "approved", "rejected"}


# ============ 路由：选题 ============

@router.post("/topics", status_code=201)
async def create_topic(req: TopicCreate):
    """创建选题"""
    return store.add_topic(req.model_dump())


@router.get("/topics")
async def list_topics(status: Optional[str] = None):
    """列出选题"""
    if status and status not in VALID_TOPIC_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    return store.list_topics(status=status)


@router.get("/topics/{topic_id}")
async def get_topic(topic_id: str):
    """获取单个选题"""
    item = store.get_topic(topic_id)
    if not item:
        raise HTTPException(status_code=404, detail="Topic not found")
    return item


@router.put("/topics/{topic_id}")
async def update_topic(topic_id: str, update: TopicUpdate):
    """更新选题"""
    if update.status and update.status not in VALID_TOPIC_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {update.status}")
    item = store.update_topic(topic_id, update.model_dump(exclude_unset=True))
    if not item:
        raise HTTPException(status_code=404, detail="Topic not found")
    return item


@router.delete("/topics/{topic_id}")
async def delete_topic(topic_id: str):
    """删除选题"""
    if not store.delete_topic(topic_id):
        raise HTTPException(status_code=404, detail="Topic not found")
    return {"message": "deleted", "id": topic_id}


# ============ 路由：素材 ============

@router.post("/materials", status_code=201)
async def create_material(req: MaterialCreate):
    """创建素材记录（外部存储引用）"""
    if req.type not in VALID_MATERIAL_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid type: {req.type}")
    return store.add_material(req.model_dump())


@router.get("/materials")
async def list_materials(type: Optional[str] = None):
    """列出素材"""
    if type and type not in VALID_MATERIAL_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid type: {type}")
    return store.list_materials(type_=type)


@router.get("/materials/{material_id}")
async def get_material(material_id: str):
    """获取单个素材"""
    item = store.get_material(material_id)
    if not item:
        raise HTTPException(status_code=404, detail="Material not found")
    return item


@router.put("/materials/{material_id}")
async def update_material(material_id: str, update: MaterialUpdate):
    """更新素材"""
    if update.type and update.type not in VALID_MATERIAL_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid type: {update.type}")
    item = store.update_material(material_id, update.model_dump(exclude_unset=True))
    if not item:
        raise HTTPException(status_code=404, detail="Material not found")
    return item


@router.delete("/materials/{material_id}")
async def delete_material(material_id: str):
    """删除素材"""
    if not store.delete_material(material_id):
        raise HTTPException(status_code=404, detail="Material not found")
    return {"message": "deleted", "id": material_id}


# ============ 路由：审核 ============

class ReviewTaskCreate(BaseModel):
    content_id: str
    content_title: str


@router.post("/review", status_code=201)
async def create_review_task(req: ReviewTaskCreate):
    """创建审核任务"""
    return store.add_review(req.model_dump())


@router.put("/review/{task_id}")
async def update_review(task_id: str, body: ReviewUpdate):
    """更新审核状态"""
    if body.status not in VALID_REVIEW_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {body.status}")
    item = store.update_review(task_id, body.status, body.comment)
    if not item:
        raise HTTPException(status_code=404, detail="Task not found")
    # 同步更新 content 状态
    content_id = item.get("content_id")
    if content_id:
        if body.status == "approved":
            store.update_content(content_id, {"status": "published"})
        elif body.status == "rejected":
            store.update_content(content_id, {"status": "draft"})
    return item


@router.get("/review/tasks")
async def list_review_tasks(status: Optional[str] = None):
    """列出审核任务"""
    if status and status not in VALID_REVIEW_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    return store.list_reviews(status=status)


# ============ 路由：统计 ============

@router.get("/stats")
async def get_stats():
    """获取统计数据"""
    return store.get_stats()
