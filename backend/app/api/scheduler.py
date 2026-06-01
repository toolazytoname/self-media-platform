# 调度管理 API

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import uuid
import random

router = APIRouter()


# ============ 数据模型 ============

class ScheduleTask(BaseModel):
    id: str
    content_id: str
    platform: str
    scheduled_time: datetime
    status: str = "pending"  # pending/running/completed/failed


class ScheduleCreate(BaseModel):
    content_id: str
    platform: str
    scheduled_time: datetime


# ============ 任务存储 ============

SCHEDULED_TASKS = []


# ============ 路由 ============

@router.post("/schedule")
async def create_schedule(req: ScheduleCreate):
    """创建定时发布任务"""
    task = ScheduleTask(
        id=str(uuid.uuid4()),
        content_id=req.content_id,
        platform=req.platform,
        scheduled_time=req.scheduled_time,
        status="pending"
    )
    SCHEDULED_TASKS.append(task)
    return task


@router.get("/tasks")
async def list_tasks(status: Optional[str] = None):
    """列出调度任务"""
    if status:
        return [t for t in SCHEDULED_TASKS if t.status == status]
    return SCHEDULED_TASKS


@router.delete("/task/{task_id}")
async def cancel_task(task_id: str):
    """取消定时任务"""
    for i, task in enumerate(SCHEDULED_TASKS):
        if task.id == task_id:
            SCHEDULED_TASKS.pop(i)
            return {"message": "cancelled"}
    raise HTTPException(status_code=404, detail="Task not found")


@router.post("/random-interval")
async def add_random_interval(min_minutes: int = 5, max_minutes: int = 15):
    """添加随机间隔（反机器检测）"""
    interval = random.randint(min_minutes, max_minutes)
    scheduled = datetime.now() + timedelta(minutes=interval)
    return {
        "message": f"随机间隔: {interval} 分钟",
        "scheduled_time": scheduled,
        "interval_minutes": interval
    }