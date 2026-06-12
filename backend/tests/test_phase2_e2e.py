"""Phase 2 端到端测试:content → video → publish-now(同步派发)→ status 流转

全链路 mock:
  - MiniMax:patch generate_video_and_download 返 is_mock=False
  - DouyinAdapter:patch get_adapter 返 fake adapter,upload_video 返 published
"""
import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.core.config import settings
from app.services.scheduler_loop import scheduler_loop


def _fake_minimax_response(local_path: str):
    return {
        "is_mock": False,
        "job_id": "test_e2e_job_001",
        "status": "ready",
        "video_url": "https://cdn.example.com/e2e.mp4",
        "local_path": local_path,
        "model": "MiniMax-Hailuo-03",
    }


def _fake_adapter_upload(**kwargs):
    return {
        "platform_publish_id": "https://creator.douyin.com/creator-micro/content/manage/12345",
        "url": "https://creator.douyin.com/creator-micro/content/manage/12345",
        "status": "published",
    }


@pytest.fixture
def setup_phase2_data(fresh_store, tmp_path):
    """布置一个完整的 content / video / account / cookie 场景"""
    # 1) 内容
    content = fresh_store.add_content({
        "title": "Phase 2 E2E 测试",
        "body": "测试 body 内容",
        "tags": ["e2e", "test"],
        "platform": "douyin",
    })
    # 2) 账号(带 cookie_path)
    cookie = tmp_path / "e2e_cookie.json"
    cookie.write_text("{}")
    account = fresh_store.add_account({
        "platform": "douyin",
        "name": "e2e_test",
        "cookie_path": str(cookie),
    })
    # 3) 视频文件
    video_file = tmp_path / "e2e_video.mp4"
    video_file.write_bytes(b"fake mp4 for e2e")
    return {
        "content": content,
        "account": account,
        "cookie_path": str(cookie),
        "video_file": str(video_file),
    }


class TestPhase2FullChain:
    @pytest.mark.asyncio
    async def test_chain_content_to_published(
        self, client, fresh_store, setup_phase2_data, tmp_path,
    ):
        """1) POST /ai/video/generate(MiniMax mock) → 落 record
           2) POST /platforms/publish-now(adapter mock) → 同步派发 → published
           3) GET /api/cms/stats 看到 published 内容计数上升"""

        data = setup_phase2_data
        video_local_path = data["video_file"]

        # --- 1) 视频生成(mock MiniMax 返成功) ---
        with patch(
            "app.services.minimax_client.MiniMaxClient.generate_video_and_download",
            new=AsyncMock(return_value=_fake_minimax_response(video_local_path)),
        ):
            r = client.post("/api/ai/video/generate", json={
                "prompt": "e2e test", "duration": 6, "ratio": "16:9",
            })
        assert r.status_code == 200, r.text
        rec = r.json()["record"]
        assert rec["is_mock"] is False
        assert rec["status"] == "ready"
        video_id = rec["id"]

        # 把 video_id 挂到 content 上(content 已经有 video_id 字段)
        client.put(f"/api/content/{data['content']['id']}", json={"video_id": video_id})

        # --- 2) publish-now(同步派发, mock adapter) ---
        fake_adapter = MagicMock()
        fake_adapter.upload_video = AsyncMock(side_effect=_fake_adapter_upload)
        with patch("app.services.scheduler_loop.get_adapter", return_value=fake_adapter):
            r = client.post("/api/platforms/publish-now", json={
                "content_id": data["content"]["id"],
                "platform": "douyin",
                "account_id": data["account"]["id"],
                "video_id": video_id,
            })
        assert r.status_code == 200, r.text
        result = r.json()
        assert result["status"] == "published"
        assert "creator.douyin.com" in result["url"]

        # --- 3) 状态校验 ---
        # 视频:不变(ready)
        v = fresh_store.get_video(video_id)
        assert v["status"] == "ready"
        # 内容:published
        c = fresh_store.get_content(data["content"]["id"])
        assert c["status"] == "published"
        # publish_record:published + url
        records = fresh_store.list_publish_records()
        pub = [r for r in records if r["video_id"] == video_id]
        assert len(pub) == 1
        assert pub[0]["status"] == "published"
        assert "creator.douyin.com" in (pub[0].get("url") or "")

    @pytest.mark.asyncio
    async def test_chain_mock_video_rejected(
        self, client, fresh_store, setup_phase2_data,
    ):
        """mock 视频 + 走 publish-now → adapter 不会被调,直接 failed"""
        data = setup_phase2_data

        # 生成一个 mock 视频
        with patch(
            "app.services.minimax_client.MiniMaxClient.generate_video_and_download",
            new=AsyncMock(return_value={
                "is_mock": True, "error": "fake", "job_id": None,
            }),
        ):
            r = client.post("/api/ai/video/generate", json={"prompt": "x", "duration": 6})
        assert r.status_code == 200
        mock_video_id = r.json()["record"]["id"]
        assert r.json()["record"]["is_mock"] is True

        # 尝试发布
        fake_adapter = MagicMock()
        fake_adapter.upload_video = AsyncMock(side_effect=_fake_adapter_upload)
        with patch("app.services.scheduler_loop.get_adapter", return_value=fake_adapter) as m:
            r = client.post("/api/platforms/publish-now", json={
                "content_id": data["content"]["id"],
                "platform": "douyin",
                "account_id": data["account"]["id"],
                "video_id": mock_video_id,
            })
        assert r.status_code == 200
        result = r.json()
        assert result["status"] == "failed"
        assert "mock" in (result.get("error") or "").lower()
        # adapter 根本没被调
        fake_adapter.upload_video.assert_not_called()

    @pytest.mark.asyncio
    async def test_chain_adapter_error_marks_failed(
        self, client, fresh_store, setup_phase2_data, tmp_path,
    ):
        """adapter upload_video 抛异常 → status=failed, error_message 有内容"""
        from app.platforms.douyin import DouyinUploadError
        data = setup_phase2_data

        # 生成一个真视频记录
        video_file = tmp_path / "real_v.mp4"; video_file.write_bytes(b"real")
        with patch(
            "app.services.minimax_client.MiniMaxClient.generate_video_and_download",
            new=AsyncMock(return_value=_fake_minimax_response(str(video_file))),
        ):
            r = client.post("/api/ai/video/generate", json={"prompt": "x", "duration": 6})
        video_id = r.json()["record"]["id"]

        # adapter 抛错
        fake_adapter = MagicMock()
        fake_adapter.upload_video = AsyncMock(
            side_effect=DouyinUploadError("sau exit=1, stderr: cookie expired")
        )
        with patch("app.services.scheduler_loop.get_adapter", return_value=fake_adapter):
            r = client.post("/api/platforms/publish-now", json={
                "content_id": data["content"]["id"],
                "platform": "douyin",
                "account_id": data["account"]["id"],
                "video_id": video_id,
            })
        assert r.status_code == 200
        result = r.json()
        assert result["status"] == "failed"
        assert "cookie expired" in (result.get("error") or "")

        # publish_record 上也有 error_message
        records = fresh_store.list_publish_records(status="failed")
        assert any("cookie expired" in (r.get("error_message") or "") for r in records)
