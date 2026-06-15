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


# ============ P0-1: 公众号 publish_wechat_now ============

@pytest.mark.asyncio
async def test_publish_wechat_now_happy_path(fresh_store, tmp_path):
    """完整 content + account + image_id,adapter mock 成功 → record 含新字段 + content.status=published"""
    cover_local = tmp_path / "cover.jpg"
    cover_local.write_bytes(b"\xff\xd8\xff\xe0cover")
    image = store.add_image({
        "prompt": "p", "image_url": str(cover_local),  # 已是本地路径
        "is_mock": False,
    })
    content = store.add_content({
        "title": "图文", "body": "<p>x</p>", "tags": [],
        "platform": "wechat", "image_id": image["id"],
    })
    account = store.add_account({
        "platform": "wechat", "name": "wx1",
        "app_id": "wx_x", "app_secret": "sec",
    })

    fake_adapter = MagicMock()
    fake_adapter.publish_article_full_auto = AsyncMock(return_value={
        "status": "published",
        "platform_publish_id": "pid_001",
        "draft_media_id": "draft_001",
        "freepublish_id": "pid_001",
        "freepublish_status": 0,
        "article_url": "https://mp.weixin.qq.com/s?ok",
        "thumb_media_id": "thumb_001",
        "body_html": "<p>x</p>",
    })

    with patch("app.platforms.wechat.WeChatAdapter", return_value=fake_adapter):
        loop = SchedulerLoop(interval_seconds=1)
        result = await loop.publish_wechat_now(
            content_id=content["id"], account_id=account["id"],
        )

    assert result["status"] == "published"
    assert result["url"] == "https://mp.weixin.qq.com/s?ok"
    assert result["freepublish_id"] == "pid_001"
    assert result["draft_media_id"] == "draft_001"
    # 验证 publish_record 持久化
    recs = [r for r in store.publish_records if r["content_id"] == content["id"]]
    assert len(recs) == 1
    rec = recs[0]
    assert rec["status"] == "published"
    assert rec["url"] == "https://mp.weixin.qq.com/s?ok"
    assert rec["freepublish_id"] == "pid_001"
    assert rec["draft_media_id"] == "draft_001"
    assert rec["freepublish_status"] == 0
    # content 状态更新
    assert store.get_content(content["id"])["status"] == "published"


@pytest.mark.asyncio
async def test_publish_wechat_now_missing_cover_returns_failed(fresh_store, tmp_path):
    """content 没 image_id,也没 image_url → 返 failed,不调 adapter"""
    content = store.add_content({
        "title": "无封面", "body": "<p>x</p>", "tags": [],
        "platform": "wechat",
        # 故意没有 image_id 也没 image_url
    })
    account = store.add_account({
        "platform": "wechat", "name": "wx1",
        "app_id": "wx", "app_secret": "sec",
    })
    fake_adapter = MagicMock()
    fake_adapter.publish_article_full_auto = AsyncMock()

    with patch("app.platforms.wechat.WeChatAdapter", return_value=fake_adapter):
        loop = SchedulerLoop(interval_seconds=1)
        result = await loop.publish_wechat_now(
            content_id=content["id"], account_id=account["id"],
        )

    assert result["status"] == "failed"
    assert "封面" in result.get("error_message", "")
    # adapter 一次都没调
    assert fake_adapter.publish_article_full_auto.call_count == 0
    # record 失败记录
    recs = [r for r in store.publish_records if r["content_id"] == content["id"]]
    assert recs[0]["status"] == "failed"
    # content 状态不变
    assert store.get_content(content["id"])["status"] != "published"


@pytest.mark.asyncio
async def test_publish_wechat_now_adapter_raises(fresh_store, tmp_path):
    """adapter 抛异常 → record.status=failed,error_message 写入"""
    cover_local = tmp_path / "cover.jpg"
    cover_local.write_bytes(b"\xff\xd8\xff\xe0c")
    image = store.add_image({"image_url": str(cover_local), "is_mock": False})
    content = store.add_content({
        "title": "T", "body": "<p>x</p>", "platform": "wechat",
        "image_id": image["id"],
    })
    account = store.add_account({
        "platform": "wechat", "name": "w", "app_id": "a", "app_secret": "b",
    })

    fake_adapter = MagicMock()
    fake_adapter.publish_article_full_auto = AsyncMock(
        side_effect=Exception("公众号 token 获取失败: 40013 invalid appid"),
    )

    with patch("app.platforms.wechat.WeChatAdapter", return_value=fake_adapter):
        loop = SchedulerLoop(interval_seconds=1)
        result = await loop.publish_wechat_now(
            content_id=content["id"], account_id=account["id"],
        )

    assert result["status"] == "failed"
    assert "40013" in result["error_message"]
    recs = [r for r in store.publish_records if r["content_id"] == content["id"]]
    assert recs[0]["status"] == "failed"
    # content 不回滚到 published
    assert store.get_content(content["id"])["status"] != "published"
