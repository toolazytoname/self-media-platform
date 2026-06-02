"""测试 content API：CRUD、提交审核、复制、批量操作、导出"""
import pytest
import json


def _create(client, **overrides):
    payload = {"title": "T", "body": "B", "tags": [], "platform": "all"}
    payload.update(overrides)
    return client.post("/api/content/", json=payload)


class TestContentCRUD:
    def test_create_and_list(self, client, fresh_store):
        r = _create(client, title="Hello", body="World", tags=["t1"], platform="douyin")
        assert r.status_code in (200, 201)
        item = r.json()
        assert item["title"] == "Hello"
        assert item["status"] == "draft"
        assert "id" in item

        r = client.get("/api/content/")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    def test_validation(self, client, fresh_store):
        # 缺字段
        r = client.post("/api/content/", json={"title": "T"})
        assert r.status_code == 422
        # 无效平台
        r = _create(client, platform="invalid_platform")
        assert r.status_code == 400

    def test_get_update_delete(self, client, fresh_store):
        item = _create(client, title="T").json()
        cid = item["id"]

        r = client.get(f"/api/content/{cid}")
        assert r.status_code == 200
        assert r.json()["id"] == cid

        r = client.put(f"/api/content/{cid}", json={"title": "Updated", "status": "pending"})
        assert r.status_code == 200
        assert r.json()["title"] == "Updated"
        assert r.json()["status"] == "pending"

        r = client.delete(f"/api/content/{cid}")
        assert r.status_code == 200

        r = client.get(f"/api/content/{cid}")
        assert r.status_code == 404

    def test_update_invalid_status(self, client, fresh_store):
        item = _create(client).json()
        r = client.put(f"/api/content/{item['id']}", json={"status": "wrong"})
        assert r.status_code == 400

    def test_list_filters(self, client, fresh_store):
        _create(client, title="A", platform="douyin", status="draft")
        item_b = _create(client, title="B", platform="wechat").json()
        # 刷新 status
        client.put(f"/api/content/{item_b['id']}", json={"status": "published"})

        # 平台过滤
        r = client.get("/api/content/", params={"platform": "douyin"})
        assert r.json()["total"] == 1

        # 状态过滤
        r = client.get("/api/content/", params={"status": "published"})
        assert r.json()["total"] == 1

    def test_list_keyword(self, client, fresh_store):
        _create(client, title="Python 教程", body="x")
        _create(client, title="Java 教程", body="x")
        r = client.get("/api/content/", params={"keyword": "Python"})
        assert r.json()["total"] == 1
        assert r.json()["items"][0]["title"] == "Python 教程"

    def test_pagination(self, client, fresh_store):
        for i in range(5):
            _create(client, title=f"T{i}")
        r = client.get("/api/content/", params={"limit": 2, "skip": 0})
        assert r.json()["total"] == 5
        assert len(r.json()["items"]) == 2
        r = client.get("/api/content/", params={"limit": 2, "skip": 4})
        assert len(r.json()["items"]) == 1


class TestContentWorkflow:
    def test_submit_review(self, client, fresh_store):
        item = _create(client).json()
        r = client.post(f"/api/content/{item['id']}/submit-review")
        assert r.status_code == 200
        # 内容状态改为 pending
        r = client.get(f"/api/content/{item['id']}")
        assert r.json()["status"] == "pending"

    def test_submit_review_not_found(self, client, fresh_store):
        r = client.post("/api/content/missing/submit-review")
        assert r.status_code == 404

    def test_duplicate(self, client, fresh_store):
        item = _create(client, title="Original", body="body", tags=["t"]).json()
        r = client.post(f"/api/content/{item['id']}/duplicate")
        assert r.status_code == 200
        new_item = r.json()
        assert new_item["id"] != item["id"]
        assert "副本" in new_item["title"]
        assert new_item["body"] == item["body"]
        assert new_item["status"] == "draft"

    def test_duplicate_not_found(self, client, fresh_store):
        r = client.post("/api/content/missing/duplicate")
        assert r.status_code == 404


class TestBulkOperations:
    def test_bulk_delete(self, client, fresh_store):
        ids = [_create(client).json()["id"] for _ in range(3)]
        r = client.post("/api/content/bulk/delete", json={"ids": ids})
        assert r.status_code == 200
        data = r.json()
        assert data["deleted_count"] == 3
        assert len(data["failed"]) == 0

    def test_bulk_delete_partial(self, client, fresh_store):
        ids = [_create(client).json()["id"] for _ in range(2)]
        ids.append("nonexistent")
        r = client.post("/api/content/bulk/delete", json={"ids": ids})
        assert r.status_code == 200
        data = r.json()
        assert data["deleted_count"] == 2
        assert "nonexistent" in data["failed"]

    def test_bulk_update(self, client, fresh_store):
        ids = [_create(client, platform="douyin").json()["id"] for _ in range(2)]
        r = client.post("/api/content/bulk/update", json={
            "ids": ids, "platform": "wechat", "status": "published",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["updated_count"] == 2

        # 验证
        for cid in ids:
            r = client.get(f"/api/content/{cid}")
            assert r.json()["platform"] == "wechat"
            assert r.json()["status"] == "published"

    def test_bulk_update_invalid_status(self, client, fresh_store):
        ids = [_create(client).json()["id"]]
        r = client.post("/api/content/bulk/update", json={
            "ids": ids, "status": "wrong",
        })
        assert r.status_code == 400


class TestExport:
    def test_export_json(self, client, fresh_store):
        _create(client, title="A")
        r = client.get("/api/content/export/all", params={"format": "json"})
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) == 1

    def test_export_markdown(self, client, fresh_store):
        _create(client, title="Title1", body="Body1")
        r = client.get("/api/content/export/all", params={"format": "markdown"})
        assert r.status_code == 200
        assert "Title1" in r.text
        assert "Body1" in r.text

    def test_export_csv(self, client, fresh_store):
        _create(client, title="Title1", body="Body1")
        r = client.get("/api/content/export/all", params={"format": "csv"})
        assert r.status_code == 200
        lines = r.text.strip().split("\n")
        assert len(lines) == 2  # header + 1 row
        assert "Title1" in lines[1]

    def test_export_invalid_format(self, client, fresh_store):
        r = client.get("/api/content/export/all", params={"format": "xml"})
        assert r.status_code == 400

    def test_export_with_filters(self, client, fresh_store):
        _create(client, title="A", platform="douyin")
        _create(client, title="B", platform="wechat")
        r = client.get("/api/content/export/all", params={"format": "json", "platform": "douyin"})
        data = r.json()
        assert len(data) == 1
        assert data[0]["platform"] == "douyin"
