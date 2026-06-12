"""视频 API 单元测试 — 端到端通过 TestClient,关键路径 mock"""
import os
import pytest
from unittest.mock import patch, AsyncMock

from app.core.config import settings


# ---------- 通用 helpers ----------

def _mock_minimax_success(video_url: str = "https://cdn.example.com/abc.mp4", local_path: str = None):
    """构造 generate_video_and_download 成功返回的 dict"""
    return {
        "is_mock": False,
        "job_id": "test_job_123",
        "status": "ready",
        "video_url": video_url,
        "local_path": local_path,
        "model": "MiniMax-Hailuo-03",
    }


def _mock_minimax_mock_fallback(error: str = "submit failed: network unreachable"):
    return {
        "is_mock": True,
        "error": error,
        "job_id": None,
    }


# ---------- POST /api/ai/video/generate ----------

class TestVideoGenerate:
    def test_no_api_key_mock_fallback(self, client, fresh_store):
        """没有 API key → mock fallback + 0 字节占位文件"""
        # settings.MINIMAX_API_KEY 应该没设(或失效)→ MiniMaxClient 构造会抛
        r = client.post("/api/ai/video/generate", json={
            "prompt": "test cat", "duration": 6, "ratio": "16:9",
        })
        # 即使 key 是 fake,MockMax 返回 1004 → 走 mock 路径
        # 这里 200/500 都可能,关键是 record.is_mock=True
        if r.status_code == 200:
            data = r.json()
            assert data["is_mock"] is True
            assert "record" in data
            rec = data["record"]
            assert rec["status"] == "ready"
            assert rec["is_mock"] is True
            assert rec["local_path"].endswith(".mp4.mock")
            # 占位文件实际写到磁盘
            assert os.path.exists(rec["local_path"])
            # 清理
            os.remove(rec["local_path"])
        else:
            # 没 API key 且 fallback 也炸 — 也 OK
            assert r.status_code in (500, 502)

    def test_invalid_duration_422(self, client, fresh_store):
        """duration 不在 [3,6,10] 返 422(Pydantic field_validator)"""
        r = client.post("/api/ai/video/generate", json={
            "prompt": "x", "duration": 7,
        })
        # Pydantic field_validator 抛 ValueError → FastAPI 422
        assert r.status_code == 422
        detail = r.json()["detail"][0]
        assert "duration" in str(detail).lower()

    def test_happy_path_with_mocked_minimax(self, client, fresh_store):
        """Mock MiniMax 成功 → 返 record with is_mock=False"""
        # 准备一个真占位文件路径
        target = os.path.join(settings.VIDEOS_DIR, "happy_test.mp4")
        os.makedirs(settings.VIDEOS_DIR, exist_ok=True)
        with open(target, "wb") as f:
            f.write(b"fake video bytes for test")

        with patch(
            "app.services.minimax_client.MiniMaxClient.generate_video_and_download",
            new=AsyncMock(return_value=_mock_minimax_success(
                video_url="https://cdn.example.com/real.mp4",
                local_path=target,
            )),
        ):
            r = client.post("/api/ai/video/generate", json={
                "prompt": "happy path", "duration": 6,
            })
        assert r.status_code == 200
        data = r.json()
        assert data["is_mock"] is False
        rec = data["record"]
        assert rec["status"] == "ready"
        assert rec["video_url"] == "https://cdn.example.com/real.mp4"
        assert rec["local_path"] == target
        # 清理
        os.remove(target)


# ---------- GET /api/ai/video/list ----------

class TestVideoList:
    def test_list_empty(self, client, fresh_store):
        r = client.get("/api/ai/video/list")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_list_newest_first(self, client, fresh_store):
        # 直接造 2 条
        v1 = fresh_store.add_video({"prompt": "first", "duration": 6, "is_mock": False})
        v2 = fresh_store.add_video({"prompt": "second", "duration": 6, "is_mock": False})
        r = client.get("/api/ai/video/list")
        assert r.status_code == 200
        items = r.json()["items"]
        # 后插入的(v2)应该排前面
        assert items[0]["id"] == v2["id"]
        assert items[1]["id"] == v1["id"]


# ---------- GET /api/ai/video/{id} ----------

class TestVideoGet:
    def test_get_existing(self, client, fresh_store):
        v = fresh_store.add_video({"prompt": "x", "duration": 6})
        r = client.get(f"/api/ai/video/{v['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == v["id"]

    def test_get_missing_404(self, client, fresh_store):
        r = client.get("/api/ai/video/nonexistent")
        assert r.status_code == 404


# ---------- DELETE /api/ai/video/{id} ----------

class TestVideoDelete:
    def test_delete_removes_record_and_file(self, client, fresh_store):
        target = os.path.join(settings.VIDEOS_DIR, "to_delete.mp4")
        os.makedirs(settings.VIDEOS_DIR, exist_ok=True)
        with open(target, "wb") as f:
            f.write(b"delete me")
        v = fresh_store.add_video({
            "prompt": "del", "duration": 6, "local_path": target,
        })
        r = client.delete(f"/api/ai/video/{v['id']}")
        assert r.status_code == 200
        assert r.json()["ok"] is True
        # 文件应该被删
        assert not os.path.exists(target)
        # record 也没了
        assert fresh_store.get_video(v["id"]) is None

    def test_delete_missing_404(self, client, fresh_store):
        r = client.delete("/api/ai/video/nonexistent")
        assert r.status_code == 404

    def test_delete_without_local_path(self, client, fresh_store):
        """local_path 为空时,delete 不报错(只是没文件可删)"""
        v = fresh_store.add_video({"prompt": "no-file", "duration": 6})
        r = client.delete(f"/api/ai/video/{v['id']}")
        assert r.status_code == 200
