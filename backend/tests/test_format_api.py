"""POST /api/content/format — 公众号排版预览端点 — TASK-P0-7"""
import pytest
from fastapi.testclient import TestClient


def _register_and_login(client, username="format_user", password="test1234"):
    r = client.post("/api/auth/register", json={
        "username": username, "password": password, "display_name": username,
    })
    assert r.status_code in (200, 201), r.text
    r = client.post("/api/auth/login", json={"username": username, "password": "test1234"})
    return r.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


class TestFormatPreview:
    def test_default_theme(self, client, fresh_store):
        token = _register_and_login(client)
        r = client.post("/api/content/format", headers=_auth(token), json={
            "body": "# 标题\n\n正文",
            "theme": "default",
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["theme"] == "default"
        assert body["html"]
        assert "<h1" in body["html"]

    def test_all_themes(self, client, fresh_store):
        token = _register_and_login(client)
        for theme in ["default", "grace", "simple"]:
            r = client.post("/api/content/format", headers=_auth(token), json={
                "body": "# T", "theme": theme,
            })
            assert r.status_code == 200
            assert r.json()["theme_name"]

    def test_unknown_theme_returns_400(self, client, fresh_store):
        token = _register_and_login(client)
        r = client.post("/api/content/format", headers=_auth(token), json={
            "body": "T", "theme": "bogus",
        })
        assert r.status_code == 400
        assert "available" in r.json().get("detail", "").lower() or "available" in r.text.lower()

    def test_empty_body(self, client, fresh_store):
        """空 markdown 返占位 <p>"""
        token = _register_and_login(client)
        r = client.post("/api/content/format", headers=_auth(token), json={
            "body": "",
        })
        assert r.status_code == 200
        assert "<p" in r.json()["html"]

    def test_requires_auth(self, client, fresh_store):
        r = client.post("/api/content/format", json={"body": "T"})
        assert r.status_code == 401
