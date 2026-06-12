"""测试 scheduler_loop 后台任务循环 — Phase 2: 真 adapter 派发路径"""
import asyncio
import tempfile
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.scheduler_loop import SchedulerLoop
from app.store import store


@pytest.mark.asyncio
async def test_run_due_tasks_executes_past_tasks(fresh_store, tmp_path):
    """到期任务 + 完整 content/video/account + mocked adapter → completed"""
    past = (datetime.now() - timedelta(minutes=10)).isoformat()
    cookie_path = tmp_path / "test_dy.json"
    cookie_path.write_text("{}")  # sau 的 storage_state 模板(空 cookie 即可)
    content = store.add_content({
        "title": "T", "body": "B", "tags": ["a"], "platform": "douyin",
    })
    account = store.add_account({
        "platform": "douyin", "name": "test",
        "cookie_path": str(cookie_path),
    })
    video = store.add_video({
        "prompt": "p", "duration": 6, "is_mock": False,
        "local_path": str(tmp_path / "video.mp4"), "video_url": "x", "job_id": "j",
    })
    # video file must exist
    Path(video["local_path"]).write_bytes(b"fake mp4")
    pub = store.add_publish_record({
        "content_id": content["id"], "platform": "douyin",
        "status": "pending", "account_id": account["id"], "video_id": video["id"],
    })
    store.add_scheduled_task({
        "id": "t1",
        "content_id": content["id"],
        "platform": "douyin",
        "scheduled_time": past,
        "status": "pending",
        "publish_id": pub["publish_id"],
        "account_id": account["id"],
        "video_id": video["id"],
    })
    # mock adapter 让它"成功" — 不依赖 sau
    fake_adapter = MagicMock()
    fake_adapter.upload_video = AsyncMock(
        return_value={"url": "https://creator.douyin.com/manage", "platform_publish_id": "fake-1", "status": "published"}
    )
    with patch("app.services.scheduler_loop.get_adapter", return_value=fake_adapter):
        loop = SchedulerLoop(interval_seconds=1)
        executed = await loop._run_due_tasks()
    assert executed == 1
    assert store.scheduled_tasks[0]["status"] == "completed"
    assert store.scheduled_tasks[0]["executed_at"] is not None
    assert store.get_publish_record(pub["publish_id"])["status"] == "published"
    assert store.get_content(content["id"])["status"] == "published"


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
