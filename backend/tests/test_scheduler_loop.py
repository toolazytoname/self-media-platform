"""测试 scheduler_loop 后台任务循环"""
import asyncio
import pytest
from datetime import datetime, timedelta
from app.services.scheduler_loop import SchedulerLoop
from app.store import store


@pytest.mark.asyncio
async def test_run_due_tasks_executes_past_tasks(fresh_store):
    """到期任务应被标记为 completed"""
    past = (datetime.now() - timedelta(minutes=10)).isoformat()
    store.add_scheduled_task({
        "id": "t1",
        "content_id": "c1",
        "platform": "douyin",
        "scheduled_time": past,
        "status": "pending",
    })
    loop = SchedulerLoop(interval_seconds=1)
    executed = await loop._run_due_tasks()
    assert executed == 1
    assert store.scheduled_tasks[0]["status"] == "completed"
    assert store.scheduled_tasks[0]["executed_at"] is not None


@pytest.mark.asyncio
async def test_run_due_tasks_skips_future(fresh_store):
    """未到期任务不应被执行"""
    future = (datetime.now() + timedelta(hours=1)).isoformat()
    store.add_scheduled_task({
        "id": "t1",
        "content_id": "c1",
        "platform": "douyin",
        "scheduled_time": future,
        "status": "pending",
    })
    loop = SchedulerLoop(interval_seconds=1)
    executed = await loop._run_due_tasks()
    assert executed == 0
    assert store.scheduled_tasks[0]["status"] == "pending"


@pytest.mark.asyncio
async def test_run_due_tasks_skips_completed(fresh_store):
    """已完成任务不会被重新执行"""
    past = (datetime.now() - timedelta(minutes=10)).isoformat()
    store.add_scheduled_task({
        "id": "t1",
        "content_id": "c1",
        "platform": "douyin",
        "scheduled_time": past,
        "status": "completed",
    })
    loop = SchedulerLoop(interval_seconds=1)
    executed = await loop._run_due_tasks()
    assert executed == 0
