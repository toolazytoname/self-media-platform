# CMS 管理 API

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

router = APIRouter()


# ============ 数据模型 ============

class TopicCreate(BaseModel):
    title: str
    description: str = ""
    priority: int = 1


class Topic(BaseModel):
    id: str
    title: str
    description: str
    priority: int = 1
    status: str = "active"  # active/done/archived
    created_at: datetime


class MaterialCreate(BaseModel):
    name: str
    type: str  # image/video/audio/text
    path: str
    tags: List[str] = []


class Material(BaseModel):
    id: str
    name: str
    type: str
    path: str
    tags: List[str] = []
    created_at: datetime


class ReviewTaskCreate(BaseModel):
    content_id: str
    content_title: str


class ReviewTask(BaseModel):
    id: str
    content_id: str
    content_title: str
    status: str = "pending"  # pending/approved/rejected
    reviewer_comment: Optional[str] = None
    created_at: datetime


# ============ 存储 ============

TOPICS = []
MATERIALS = []
REVIEW_TASKS = []


# ============ 路由 ============

# --- 选题库 ---

@router.post("/topics")
async def create_topic(req: TopicCreate):
    """创建选题"""
    topic = Topic(
        id=str(uuid.uuid4()),
        title=req.title,
        description=req.description,
        priority=req.priority,
        created_at=datetime.now()
    )
    TOPICS.append(topic)
    return topic


@router.get("/topics")
async def list_topics(status: Optional[str] = None):
    """列出选题"""
    if status:
        return [t for t in TOPICS if t.status == status]
    return TOPICS


# --- 素材库 ---

@router.post("/materials")
async def upload_material(req: MaterialCreate):
    """上传素材"""
    material = Material(
        id=str(uuid.uuid4()),
        name=req.name,
        type=req.type,
        path=req.path,
        tags=req.tags,
        created_at=datetime.now()
    )
    MATERIALS.append(material)
    return material


@router.get("/materials")
async def list_materials(type: Optional[str] = None):
    """列出素材"""
    if type:
        return [m for m in MATERIALS if m.type == type]
    return MATERIALS


# --- 审核流 ---

@router.post("/review")
async def create_review_task(req: ReviewTaskCreate):
    """创建审核任务"""
    task = ReviewTask(
        id=str(uuid.uuid4()),
        content_id=req.content_id,
        content_title=req.content_title,
        created_at=datetime.now()
    )
    REVIEW_TASKS.append(task)
    return task


@router.put("/review/{task_id}")
async def update_review(task_id: str, status: str, comment: Optional[str] = None):
    """更新审核状态"""
    for task in REVIEW_TASKS:
        if task.id == task_id:
            task.status = status
            task.reviewer_comment = comment
            return task
    raise HTTPException(status_code=404, detail="Task not found")


@router.get("/review/tasks")
async def list_review_tasks(status: Optional[str] = None):
    """列出审核任务"""
    if status:
        return [t for t in REVIEW_TASKS if t.status == status]
    return REVIEW_TASKS


# --- 统计 ---

@router.get("/stats")
async def get_stats():
    """获取统计数据"""
    return {
        "topics_total": len(TOPICS),
        "materials_total": len(MATERIALS),
        "review_pending": len([t for t in REVIEW_TASKS if t.status == "pending"]),
        "content_total": len([]),  # TODO: 关联content模块
        "platforms_connected": 0   # TODO: 关联platforms模块
    }