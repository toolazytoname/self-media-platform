"""测试 scheduler API：定时任务、随机间隔、自动执行"""
import pytest
from datetime import datetime, timedelta
from app.store import store


class TestScheduler:
    def test_list_empty(self, client, fresh_store):
        r = client.get("/api/scheduler/tasks")
        assert r.status_code == 200
        assert r.json() == []

    def _create_content(self, client):
        """辅助：创建一个内容返回其 id"""
        return client.post("/api/content/", json={
            "title": "T", "body": "B", "tags": [], "platform": "all",
        }).json()["id"]

    def test_create_task(self, client, fresh_store):
        future = (datetime.now() + timedelta(hours=1)).isoformat()
        cid = self._create_content(client)
        r = client.post("/api/scheduler/schedule", json={
            "content_id": cid,
            "platform": "douyin",
            "scheduled_time": future,
        })
        assert r.status_code in (200, 201)
        task = r.json()
        assert task["status"] == "pending"
        assert task["content_id"] == cid

    def test_create_task_content_not_found(self, client, fresh_store):
        future = (datetime.now() + timedelta(hours=1)).isoformat()
        r = client.post("/api/scheduler/schedule", json={
            "content_id": "missing-id",
            "platform": "douyin",
            "scheduled_time": future,
        })
        assert r.status_code == 404

    def test_get_task(self, client, fresh_store):
        future = (datetime.now() + timedelta(hours=1)).isoformat()
        cid = self._create_content(client)
        task = client.post("/api/scheduler/schedule", json={
            "content_id": cid, "platform": "douyin", "scheduled_time": future,
        }).json()
        r = client.get(f"/api/scheduler/task/{task['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == task["id"]

    def test_get_not_found(self, client, fresh_store):
        r = client.get("/api/scheduler/task/missing")
        assert r.status_code == 404

    def test_update_task(self, client, fresh_store):
        future = (datetime.now() + timedelta(hours=1)).isoformat()
        cid = self._create_content(client)
        task = client.post("/api/scheduler/schedule", json={
            "content_id": cid, "platform": "douyin", "scheduled_time": future,
        }).json()
        new_time = (datetime.now() + timedelta(hours=2)).isoformat()
        r = client.put(f"/api/scheduler/task/{task['id']}", json={"scheduled_time": new_time})
        assert r.status_code == 200

    def test_cancel_task(self, client, fresh_store):
        future = (datetime.now() + timedelta(hours=1)).isoformat()
        cid = self._create_content(client)
        task = client.post("/api/scheduler/schedule", json={
            "content_id": cid, "platform": "douyin", "scheduled_time": future,
        }).json()
        r = client.delete(f"/api/scheduler/task/{task['id']}")
        assert r.status_code == 200

    def test_cancel_not_found(self, client, fresh_store):
        r = client.delete("/api/scheduler/task/missing")
        assert r.status_code == 404

    def test_random_interval(self, client, fresh_store):
        r = client.post("/api/scheduler/random-interval", params={"min_minutes": 5, "max_minutes": 15})
        assert r.status_code == 200
        data = r.json()
        assert "scheduled_time" in data
        assert data["interval_minutes"] >= 5
        assert data["interval_minutes"] <= 15

    def test_run_due(self, client, fresh_store):
        # 创建一个过期的任务
        past = (datetime.now() - timedelta(minutes=10)).isoformat()
        cid = self._create_content(client)
        client.post("/api/scheduler/schedule", json={
            "content_id": cid, "platform": "douyin", "scheduled_time": past,
        })
        r = client.post("/api/scheduler/run-due")
        assert r.status_code == 200
        data = r.json()
        assert data["executed"] >= 1
        # 验证任务已标记为 completed
        for task in data["tasks"]:
            assert task["status"] == "completed"
            assert task["executed_at"] is not None

    def test_run_due_skips_future(self, client, fresh_store):
        future = (datetime.now() + timedelta(hours=1)).isoformat()
        cid = self._create_content(client)
        client.post("/api/scheduler/schedule", json={
            "content_id": cid, "platform": "douyin", "scheduled_time": future,
        })
        r = client.post("/api/scheduler/run-due")
        assert r.json()["executed"] == 0

    def test_list_by_status(self, client, fresh_store):
        future = (datetime.now() + timedelta(hours=1)).isoformat()
        cid = self._create_content(client)
        client.post("/api/scheduler/schedule", json={
            "content_id": cid, "platform": "douyin", "scheduled_time": future,
        })
        r = client.get("/api/scheduler/tasks", params={"status": "pending"})
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_create_task_validation(self, client, fresh_store):
        # 缺字段
        r = client.post("/api/scheduler/schedule", json={
            "content_id": "c1", "platform": "douyin",
        })
        assert r.status_code == 422
