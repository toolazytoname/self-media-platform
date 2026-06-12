"""
E2E smoke test — mirrors the 12 sections of the legacy e2e_test.py as pytest
classes. Runs in-process via FastAPI TestClient, no live server needed.

AI endpoints (which can fail with 5xx when the network is unreachable) are
accepted as passing when the status code is in (200, 500, 502, 503).
The /duplicate endpoint is expected to return 201 (semantic-correct for a
"create a copy" POST); the legacy script asserted 200, which was a test bug.
"""
import time
from datetime import datetime, timedelta

import pytest


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _ok(response, expected):
    """Assert response.status_code is in `expected` (int or tuple)."""
    if isinstance(expected, (tuple, list)):
        assert response.status_code in expected, (
            f"expected status in {expected}, got {response.status_code}: "
            f"{response.text[:200]}"
        )
    else:
        assert response.status_code == expected, (
            f"expected {expected}, got {response.status_code}: {response.text[:200]}"
        )


def _register_and_login(client, username, password="test1234", display="E2E"):
    r = client.post("/api/auth/register", json={
        "username": username, "password": password, "display_name": display,
    })
    _ok(r, (200, 201))
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    _ok(r, 200)
    return r.json()["access_token"]


# ---------------------------------------------------------------------------
# 1. Health & basics
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health(self, client):
        _ok(client.get("/health"), 200)

    def test_root(self, client):
        _ok(client.get("/"), 200)

    def test_cms_stats(self, client):
        _ok(client.get("/api/cms/stats"), 200)


# ---------------------------------------------------------------------------
# 2. Auth
# ---------------------------------------------------------------------------

class TestAuth:
    def test_register_random_user(self, client):
        r = client.post("/api/auth/register", json={
            "username": f"e2e_{int(time.time() * 1000)}",
            "password": "test1234",
            "display_name": "E2E User",
        })
        _ok(r, 201)

    def test_register_and_login_roundtrip(self, client):
        token = _register_and_login(client, "e2e_test")
        assert token

    def test_me_with_token(self, client):
        token = _register_and_login(client, "e2e_test")
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        _ok(r, 200)
        assert r.json()["username"] == "e2e_test"

    def test_me_invalid_token_rejected(self, client):
        _ok(client.get("/api/auth/me", headers={"Authorization": "Bearer invalid"}), 401)

    def test_login_wrong_password(self, client):
        _register_and_login(client, "e2e_test")
        r = client.post("/api/auth/login", json={"username": "e2e_test", "password": "wrongpassword"})
        _ok(r, 401)

    def test_register_duplicate_rejected(self, client):
        _register_and_login(client, "e2e_test")
        r = client.post("/api/auth/register", json={"username": "e2e_test", "password": "test1234"})
        _ok(r, 400)


# ---------------------------------------------------------------------------
# 3. Content CRUD + filters + bulk + export
# ---------------------------------------------------------------------------

class TestContentCRUD:
    def test_create_and_get(self, client):
        r = client.post("/api/content/", json={
            "title": "E2E 测试内容 1", "body": "# Hello\n\n**粗体**",
            "tags": ["test", "e2e"], "platform": "douyin",
        })
        _ok(r, 201)
        cid = r.json()["id"]
        _ok(client.get(f"/api/content/{cid}"), 200)

    def test_list(self, client):
        _ok(client.get("/api/content/"), 200)

    def test_update(self, client):
        r = client.post("/api/content/", json={
            "title": "x", "body": "y", "tags": [], "platform": "all",
        })
        cid = r.json()["id"]
        _ok(client.put(f"/api/content/{cid}", json={"title": "Updated", "tags": ["updated"]}), 200)

    def test_update_invalid_status(self, client):
        r = client.post("/api/content/", json={
            "title": "x", "body": "y", "tags": [], "platform": "all",
        })
        cid = r.json()["id"]
        _ok(client.put(f"/api/content/{cid}", json={"status": "wrong"}), 400)

    def test_get_404(self, client):
        _ok(client.get("/api/content/nonexistent"), 404)

    def test_duplicate_returns_201(self, client):
        r = client.post("/api/content/", json={
            "title": "E2E dup", "body": "# Hello\n\n这是 **粗体** 文字。",
            "tags": ["test"], "platform": "douyin",
        })
        cid = r.json()["id"]
        # 1a45f67 changed duplicate to return 201 (create semantics)
        _ok(client.post(f"/api/content/{cid}/duplicate"), 201)

    def test_submit_review(self, client):
        r = client.post("/api/content/", json={
            "title": "review me", "body": "x", "tags": [], "platform": "all",
        })
        cid = r.json()["id"]
        _ok(client.post(f"/api/content/{cid}/submit-review"), 200)

    def test_duplicate_missing_404(self, client):
        _ok(client.post("/api/content/nonexistent/duplicate"), 404)

    def test_filter_keyword(self, client):
        _ok(client.get("/api/content/?keyword=Updated"), 200)

    def test_filter_platform(self, client):
        _ok(client.get("/api/content/?platform=douyin"), 200)

    def test_filter_status(self, client):
        _ok(client.get("/api/content/?status=pending"), 200)


class TestContentBulk:
    def test_bulk_delete(self, client):
        cids = []
        for i in range(3):
            r = client.post("/api/content/", json={
                "title": f"Bulk {i}", "body": "x", "tags": [], "platform": "all",
            })
            if r.status_code == 201:
                cids.append(r.json()["id"])
        _ok(client.post("/api/content/bulk/delete", json={"ids": cids[:2]}), 200)

    def test_bulk_update(self, client):
        cids = []
        for i in range(3):
            r = client.post("/api/content/", json={
                "title": f"BulkU {i}", "body": "x", "tags": [], "platform": "all",
            })
            if r.status_code == 201:
                cids.append(r.json()["id"])
        _ok(client.post("/api/content/bulk/update",
                        json={"ids": cids, "status": "published"}), 200)

    def test_bulk_update_invalid_status(self, client):
        _ok(client.post("/api/content/bulk/update",
                        json={"ids": ["x"], "status": "invalid"}), 400)


class TestContentExport:
    def test_export_json(self, client):
        _ok(client.get("/api/content/export/all?format=json"), 200)

    def test_export_markdown(self, client):
        _ok(client.get("/api/content/export/all?format=markdown"), 200)

    def test_export_csv(self, client):
        _ok(client.get("/api/content/export/all?format=csv"), 200)

    def test_export_xml_invalid(self, client):
        _ok(client.get("/api/content/export/all?format=xml"), 400)


class TestContentDelete:
    def test_delete_and_404(self, client):
        r = client.post("/api/content/", json={
            "title": "del me", "body": "x", "tags": [], "platform": "all",
        })
        cid = r.json()["id"]
        _ok(client.delete(f"/api/content/{cid}"), 200)
        _ok(client.delete("/api/content/missing"), 404)


# ---------------------------------------------------------------------------
# 4. Templates
# ---------------------------------------------------------------------------

class TestTemplates:
    def test_template_crud(self, client):
        r = client.post("/api/templates", json={
            "name": "E2E 模板", "category": "article", "description": "测试", "body": "## 标题",
        })
        _ok(r, 201)
        tid = r.json()["id"]
        _ok(client.get("/api/templates"), 200)
        _ok(client.get(f"/api/templates/{tid}"), 200)
        _ok(client.get("/api/templates/missing"), 404)
        _ok(client.get("/api/templates?category=article"), 200)
        _ok(client.put(f"/api/templates/{tid}", json={"name": "Updated"}), 200)
        _ok(client.put("/api/templates/missing", json={"name": "X"}), 404)
        _ok(client.post("/api/templates", json={"name": "X", "category": "invalid", "body": "X"}), 400)
        _ok(client.delete(f"/api/templates/{tid}"), 200)
        _ok(client.delete("/api/templates/missing"), 404)


# ---------------------------------------------------------------------------
# 5. Topics
# ---------------------------------------------------------------------------

class TestTopics:
    def test_topic_crud(self, client):
        r = client.post("/api/cms/topics", json={
            "title": "选题1", "description": "测试", "priority": 3,
        })
        _ok(r, 201)
        tid = r.json()["id"]
        _ok(client.get("/api/cms/topics"), 200)
        _ok(client.get(f"/api/cms/topics/{tid}"), 200)
        _ok(client.get("/api/cms/topics/missing"), 404)
        _ok(client.put(f"/api/cms/topics/{tid}", json={"title": "Updated", "status": "done"}), 200)
        _ok(client.put(f"/api/cms/topics/{tid}", json={"status": "invalid"}), 400)
        _ok(client.put("/api/cms/topics/missing", json={"title": "X"}), 404)
        _ok(client.delete(f"/api/cms/topics/{tid}"), 200)
        _ok(client.delete("/api/cms/topics/missing"), 404)
        _ok(client.get("/api/cms/topics?status=active"), 200)


# ---------------------------------------------------------------------------
# 6. Materials
# ---------------------------------------------------------------------------

class TestMaterials:
    def test_material_crud(self, client):
        r = client.post("/api/cms/materials", json={
            "name": "图片1", "type": "image", "path": "/uploads/1.png",
        })
        _ok(r, 201)
        mid = r.json()["id"]
        _ok(client.get("/api/cms/materials"), 200)
        _ok(client.get(f"/api/cms/materials/{mid}"), 200)
        _ok(client.get("/api/cms/materials?type=image"), 200)
        _ok(client.put(f"/api/cms/materials/{mid}", json={"name": "renamed"}), 200)
        _ok(client.delete(f"/api/cms/materials/{mid}"), 200)
        _ok(client.post("/api/cms/materials",
                        json={"name": "X", "type": "invalid", "path": "/x"}), 400)


# ---------------------------------------------------------------------------
# 7. Review
# ---------------------------------------------------------------------------

class TestReview:
    def test_review_flow(self, client):
        r = client.post("/api/content/", json={
            "title": "审核测试", "body": "x", "tags": [], "platform": "all",
        })
        cid = r.json()["id"]
        r = client.post("/api/cms/review", json={
            "content_id": cid, "content_title": "审核测试",
        })
        _ok(r, 201)
        rid = r.json()["id"]
        _ok(client.get("/api/cms/review/tasks"), 200)
        _ok(client.get("/api/cms/review/tasks?status=pending"), 200)
        _ok(client.get("/api/cms/review/tasks?status=invalid"), 400)
        _ok(client.put(f"/api/cms/review/{rid}", json={"status": "approved", "comment": "ok"}), 200)
        _ok(client.put(f"/api/cms/review/{rid}", json={"status": "invalid"}), 400)
        _ok(client.put("/api/cms/review/missing", json={"status": "approved"}), 404)


# ---------------------------------------------------------------------------
# 8. Platform accounts
# ---------------------------------------------------------------------------

class TestPlatforms:
    def test_accounts_crud(self, client):
        _ok(client.get("/api/platforms/accounts"), 200)
        _ok(client.post("/api/platforms/accounts", json={}), 422)
        _ok(client.post("/api/platforms/accounts",
                        json={"platform": "douyin", "name": "test_dy"}), (200, 201))
        _ok(client.get("/api/platforms/accounts"), 200)


# ---------------------------------------------------------------------------
# 9. Scheduler
# ---------------------------------------------------------------------------

class TestScheduler:
    def test_scheduler_crud(self, client):
        r = client.post("/api/content/", json={
            "title": "调度测试", "body": "x", "tags": [], "platform": "all",
        })
        cid = r.json()["id"]
        future = (datetime.now() + timedelta(hours=1)).isoformat()
        r = client.post("/api/scheduler/schedule", json={
            "content_id": cid, "platform": "douyin", "scheduled_time": future,
        })
        _ok(r, (200, 201))
        task_id = r.json()["id"]
        _ok(client.get("/api/scheduler/tasks"), 200)
        _ok(client.get(f"/api/scheduler/task/{task_id}"), 200)
        _ok(client.get("/api/scheduler/task/missing"), 404)
        _ok(client.put(f"/api/scheduler/task/{task_id}", json={
            "scheduled_time": (datetime.now() + timedelta(hours=2)).isoformat(),
        }), 200)
        _ok(client.delete(f"/api/scheduler/task/{task_id}"), 200)
        _ok(client.delete("/api/scheduler/task/missing"), 404)
        _ok(client.post("/api/scheduler/random-interval"), 200)
        _ok(client.post("/api/scheduler/run-due"), 200)
        _ok(client.post("/api/scheduler/schedule", json={
            "content_id": "missing-id", "platform": "douyin", "scheduled_time": future,
        }), 404)
        _ok(client.post("/api/scheduler/schedule", json={
            "content_id": "x", "platform": "y",
        }), 422)


# ---------------------------------------------------------------------------
# 10. Settings
# ---------------------------------------------------------------------------

class TestSettings:
    def test_settings_roundtrip(self, client):
        _ok(client.get("/api/config"), 200)
        _ok(client.post("/api/config", json={"minimax_api_key": "test-key"}), (200, 500))
        _ok(client.post("/api/config/test", json={
            "api_key": "fake", "base_url": "https://api.minimaxi.com/v1", "model": "MiniMax-M3",
        }), (200, 500, 502, 503))


# ---------------------------------------------------------------------------
# 11. AI (network failures accepted)
# ---------------------------------------------------------------------------

class TestAI:
    def test_ai_summary(self, client):
        _ok(client.post("/api/ai/summary", json={"content": "测试" * 20}),
            (200, 500, 502, 503))

    def test_ai_copy(self, client):
        _ok(client.post("/api/ai/copy", json={"topic": "AI", "platform": "wechat"}),
            (200, 500, 502, 503))

    def test_ai_podcast_script(self, client):
        _ok(client.post("/api/ai/podcast/script", json={"content": "x"}),
            (200, 500, 502, 503))

    def test_ai_video_script(self, client):
        _ok(client.post("/api/ai/video/script", json={"topic": "x", "duration": 60}),
            (200, 500, 502, 503))

    def test_ai_image(self, client):
        _ok(client.post("/api/ai/image", json={"prompt": "cat"}),
            (200, 500, 502, 503))

    def test_ai_video_generate(self, client):
        _ok(client.post("/api/ai/video/generate", json={"prompt": "x"}),
            (200, 202, 500, 502, 503))

    def test_ai_video_status(self, client):
        _ok(client.get("/api/ai/video/status/test-job-id"),
            (200, 404, 500, 502, 503))


# ---------------------------------------------------------------------------
# 12. Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_404_on_unknown_route(self, client):
        _ok(client.get("/api/nonexistent"), 404)
