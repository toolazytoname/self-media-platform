# 调度管理 API
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta
import random

from app.store import store

router = APIRouter()


# ============ Pydantic 模型 ============

class ScheduleCreate(BaseModel):
    content_id: str
    platform: str
    scheduled_time: datetime


class ScheduleUpdate(BaseModel):
    scheduled_time: Optional[datetime] = None
    status: Optional[str] = None  # pending/running/completed/failed


# ============ 路由 ============

@router.post("/schedule", status_code=201)
async def create_schedule(req: ScheduleCreate):
    """创建定时发布任务"""
    content = store.get_content(req.content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    task = store.add_scheduled_task({
        "content_id": req.content_id,
        "platform": req.platform,
        "scheduled_time": req.scheduled_time.isoformat(),
        "status": "pending",
    })
    return task


@router.get("/tasks")
async def list_tasks(status: Optional[str] = None):
    """列出调度任务"""
    return store.list_scheduled_tasks(status=status)


@router.get("/task/{task_id}")
async def get_task(task_id: str):
    """获取调度任务详情"""
    task = store.get_scheduled_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/task/{task_id}")
async def update_task(task_id: str, update: ScheduleUpdate):
    """更新调度任务"""
    payload = update.model_dump(exclude_unset=True)
    if "scheduled_time" in payload and isinstance(payload["scheduled_time"], datetime):
        payload["scheduled_time"] = payload["scheduled_time"].isoformat()
    item = store.update_scheduled_task(task_id, payload)
    if not item:
        raise HTTPException(status_code=404, detail="Task not found")
    return item


@router.delete("/task/{task_id}")
async def cancel_task(task_id: str):
    """取消定时任务"""
    if not store.delete_scheduled_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "cancelled", "id": task_id}


@router.post("/random-interval")
async def add_random_interval(min_minutes: int = 5, max_minutes: int = 15):
    """添加随机间隔（反机器检测）"""
    if min_minutes < 1 or max_minutes < min_minutes:
        raise HTTPException(status_code=400, detail="Invalid range")
    interval = random.randint(min_minutes, max_minutes)
    scheduled = datetime.now() + timedelta(minutes=interval)
    return {
        "message": f"随机间隔: {interval} 分钟",
        "scheduled_time": scheduled.isoformat(),
        "interval_minutes": interval,
    }


@router.post("/run-due")
async def run_due_tasks():
    """执行到期的调度任务（demo: 标记为 completed，不实际调用平台）"""
    now = datetime.now()
    executed = []
    for task in store.scheduled_tasks:
        if task.get("status") != "pending":
            continue
        try:
            scheduled = datetime.fromisoformat(task["scheduled_time"])
        except (ValueError, TypeError):
            continue
        if scheduled <= now:
            task["status"] = "running"
            # 模拟执行：标记为完成
            task["status"] = "completed"
            task["executed_at"] = now.isoformat()
            # 同步 publish_records
            pid = task.get("publish_id")
            if pid:
                store.update_publish_record(pid, {"status": "published", "executed_at": now.isoformat()})
            executed.append(task)
    return {"executed": len(executed), "tasks": executed}
