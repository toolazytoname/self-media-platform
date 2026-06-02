"""测试 cms API：主题/素材/审核/平台账号/发布记录"""
import pytest
from datetime import datetime, timedelta


class TestTopics:
    def test_list_empty(self, client, fresh_store):
        r = client.get("/api/cms/topics")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_and_get(self, client, fresh_store):
        r = client.post("/api/cms/topics", json={
            "title": "选题1", "description": "描述", "priority": 3,
        })
        assert r.status_code in (200, 201)
        item = r.json()
        assert item["title"] == "选题1"
        assert "id" in item

        r = client.get(f"/api/cms/topics/{item['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == item["id"]

    def test_create_validation(self, client, fresh_store):
        r = client.post("/api/cms/topics", json={})
        assert r.status_code == 422
        r = client.post("/api/cms/topics", json={"title": "T", "priority": 10})  # > 5
        assert r.status_code == 422

    def test_get_not_found(self, client, fresh_store):
        r = client.get("/api/cms/topics/missing-id")
        assert r.status_code == 404

    def test_update(self, client, fresh_store):
        r = client.post("/api/cms/topics", json={"title": "Original"})
        tid = r.json()["id"]
        r = client.put(f"/api/cms/topics/{tid}", json={"title": "Updated", "status": "done"})
        assert r.status_code == 200
        assert r.json()["title"] == "Updated"
        assert r.json()["status"] == "done"

    def test_update_not_found(self, client, fresh_store):
        r = client.put("/api/cms/topics/missing-id", json={"title": "X"})
        assert r.status_code == 404

    def test_update_invalid_status(self, client, fresh_store):
        r = client.post("/api/cms/topics", json={"title": "X"})
        tid = r.json()["id"]
        r = client.put(f"/api/cms/topics/{tid}", json={"status": "invalid"})
        assert r.status_code == 400

    def test_delete(self, client, fresh_store):
        r = client.post("/api/cms/topics", json={"title": "X"})
        tid = r.json()["id"]
        r = client.delete(f"/api/cms/topics/{tid}")
        assert r.status_code == 200
        r = client.get(f"/api/cms/topics/{tid}")
        assert r.status_code == 404

    def test_delete_not_found(self, client, fresh_store):
        r = client.delete("/api/cms/topics/missing-id")
        assert r.status_code == 404


class TestMaterials:
    def test_list_empty(self, client, fresh_store):
        r = client.get("/api/cms/materials")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create(self, client, fresh_store):
        r = client.post("/api/cms/materials", json={
            "name": "图片1", "type": "image", "path": "/uploads/1.png",
        })
        assert r.status_code in (200, 201)
        assert r.json()["name"] == "图片1"

    def test_create_validation(self, client, fresh_store):
        # 缺字段
        r = client.post("/api/cms/materials", json={"name": "X"})
        assert r.status_code == 422
        # 缺 path
        r = client.post("/api/cms/materials", json={"name": "X", "type": "image"})
        assert r.status_code == 422
        # 无效 type
        r = client.post("/api/cms/materials", json={
            "name": "X", "type": "invalid", "path": "/x",
        })
        assert r.status_code == 400

    def test_filter_by_type(self, client, fresh_store):
        client.post("/api/cms/materials", json={"name": "img1", "type": "image", "path": "/x"})
        client.post("/api/cms/materials", json={"name": "vid1", "type": "video", "path": "/y"})
        r = client.get("/api/cms/materials", params={"type": "image"})
        items = r.json()
        assert all(m["type"] == "image" for m in items)

    def test_update_and_delete(self, client, fresh_store):
        r = client.post("/api/cms/materials", json={
            "name": "img1", "type": "image", "path": "/x",
        })
        mid = r.json()["id"]

        r = client.put(f"/api/cms/materials/{mid}", json={"name": "renamed"})
        assert r.status_code == 200
        assert r.json()["name"] == "renamed"

        r = client.delete(f"/api/cms/materials/{mid}")
        assert r.status_code == 200

    def test_update_not_found(self, client, fresh_store):
        r = client.put("/api/cms/materials/missing", json={"name": "X"})
        assert r.status_code == 404


class TestReview:
    def test_list_empty(self, client, fresh_store):
        r = client.get("/api/cms/review/tasks")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_review_task(self, client, fresh_store):
        # 先有 content
        content = client.post("/api/content/", json={
            "title": "T", "body": "B", "tags": [], "platform": "all",
        }).json()
        r = client.post("/api/cms/review", json={
            "content_id": content["id"],
            "content_title": content["title"],
        })
        assert r.status_code in (200, 201)
        assert r.json()["status"] == "pending"

    def test_filter_by_status(self, client, fresh_store):
        r = client.get("/api/cms/review/tasks", params={"status": "pending"})
        assert r.status_code == 200
        r = client.get("/api/cms/review/tasks", params={"status": "invalid"})
        assert r.status_code == 400

    def test_approve_reject(self, client, fresh_store):
        # 创建 content
        content = client.post("/api/content/", json={
            "title": "T", "body": "B", "tags": [], "platform": "all",
        }).json()
        review = client.post("/api/cms/review", json={
            "content_id": content["id"],
            "content_title": content["title"],
        }).json()
        rid = review["id"]

        # 批准
        r = client.put(f"/api/cms/review/{rid}", json={
            "status": "approved", "comment": "ok",
        })
        assert r.status_code == 200
        # 验证 content 状态
        r = client.get(f"/api/content/{content['id']}")
        assert r.json()["status"] == "published"

        # 再创建一个拒绝
        content2 = client.post("/api/content/", json={
            "title": "Y", "body": "B", "tags": [], "platform": "all",
        }).json()
        review2 = client.post("/api/cms/review", json={
            "content_id": content2["id"],
            "content_title": content2["title"],
        }).json()
        r = client.put(f"/api/cms/review/{review2['id']}", json={
            "status": "rejected", "comment": "no",
        })
        assert r.status_code == 200
        # 验证 content 状态回到 draft
        r = client.get(f"/api/content/{content2['id']}")
        assert r.json()["status"] == "draft"

    def test_update_invalid_status(self, client, fresh_store):
        content = client.post("/api/content/", json={
            "title": "T", "body": "B", "tags": [], "platform": "all",
        }).json()
        review = client.post("/api/cms/review", json={
            "content_id": content["id"],
            "content_title": content["title"],
        }).json()
        r = client.put(f"/api/cms/review/{review['id']}", json={"status": "invalid"})
        assert r.status_code == 400

    def test_update_not_found(self, client, fresh_store):
        r = client.put("/api/cms/review/missing", json={"status": "approved"})
        assert r.status_code == 404


class TestStats:
    def test_stats(self, client, fresh_store):
        r = client.get("/api/cms/stats")
        assert r.status_code == 200
        data = r.json()
        for key in ("content_total", "content_draft", "content_published",
                    "topics_total", "materials_total", "review_pending",
                    "platforms_connected", "publish_records_total",
                    "scheduled_tasks_total", "platform_distribution"):
            assert key in data
