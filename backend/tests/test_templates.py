"""测试 templates API"""
import pytest


class TestTemplates:
    def test_default_templates_exist(self, client, fresh_store):
        """启动时应有默认模板"""
        r = client.get("/api/templates")
        assert r.status_code == 200
        items = r.json()
        assert len(items) >= 4  # 4 个默认模板
        names = [x["name"] for x in items]
        assert "公众号深度文章" in names
        assert "抖音短视频脚本" in names

    def test_create(self, client, fresh_store):
        r = client.post("/api/templates", json={
            "name": "我的模板",
            "category": "article",
            "description": "测试",
            "body": "# Hello",
        })
        assert r.status_code == 201
        assert r.json()["name"] == "我的模板"
        assert r.json()["id"] is not None

    def test_create_invalid_category(self, client, fresh_store):
        r = client.post("/api/templates", json={
            "name": "X",
            "category": "invalid",
            "body": "X",
        })
        assert r.status_code == 400

    def test_get(self, client, fresh_store):
        r = client.post("/api/templates", json={
            "name": "T1",
            "category": "article",
            "body": "B",
        })
        tid = r.json()["id"]
        r = client.get(f"/api/templates/{tid}")
        assert r.status_code == 200
        assert r.json()["name"] == "T1"

    def test_get_not_found(self, client, fresh_store):
        r = client.get("/api/templates/missing")
        assert r.status_code == 404

    def test_list_by_category(self, client, fresh_store):
        client.post("/api/templates", json={"name": "A1", "category": "article", "body": "x"})
        client.post("/api/templates", json={"name": "V1", "category": "video_script", "body": "x"})
        r = client.get("/api/templates", params={"category": "article"})
        items = r.json()
        assert all(t["category"] == "article" for t in items)

    def test_update(self, client, fresh_store):
        r = client.post("/api/templates", json={
            "name": "Original", "category": "article", "body": "B1",
        })
        tid = r.json()["id"]
        r = client.put(f"/api/templates/{tid}", json={"name": "Updated", "body": "B2"})
        assert r.status_code == 200
        assert r.json()["name"] == "Updated"
        assert r.json()["body"] == "B2"

    def test_update_not_found(self, client, fresh_store):
        r = client.put("/api/templates/missing", json={"name": "X"})
        assert r.status_code == 404

    def test_delete(self, client, fresh_store):
        r = client.post("/api/templates", json={
            "name": "ToDelete", "category": "article", "body": "B",
        })
        tid = r.json()["id"]
        r = client.delete(f"/api/templates/{tid}")
        assert r.status_code == 200
        r = client.get(f"/api/templates/{tid}")
        assert r.status_code == 404

    def test_delete_not_found(self, client, fresh_store):
        r = client.delete("/api/templates/missing")
        assert r.status_code == 404
