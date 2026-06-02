"""测试 auth API：注册/登录/获取当前用户"""
import pytest


class TestAuth:
    def test_register_success(self, client, fresh_store):
        r = client.post("/api/auth/register", json={
            "username": "alice",
            "password": "pass123",
            "display_name": "Alice"
        })
        assert r.status_code == 201
        data = r.json()
        assert "access_token" in data
        assert data["user"]["username"] == "alice"
        assert data["user"]["display_name"] == "Alice"
        # 重新注册同名应失败
        r2 = client.post("/api/auth/register", json={
            "username": "alice",
            "password": "pass123",
        })
        assert r2.status_code == 400
        assert "已" in r2.json()["detail"]

    def test_register_validation(self, client, fresh_store):
        # 用户名太短
        r = client.post("/api/auth/register", json={
            "username": "ab",
            "password": "pass123",
        })
        assert r.status_code == 422

        # 密码太短
        r = client.post("/api/auth/register", json={
            "username": "alice",
            "password": "123",
        })
        assert r.status_code == 422

    def test_login_success(self, client, fresh_store):
        client.post("/api/auth/register", json={
            "username": "bob",
            "password": "secret",
        })
        r = client.post("/api/auth/login", json={
            "username": "bob",
            "password": "secret",
        })
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_login_wrong_password(self, client, fresh_store):
        client.post("/api/auth/register", json={
            "username": "bob",
            "password": "secret",
        })
        r = client.post("/api/auth/login", json={
            "username": "bob",
            "password": "wrongpass",
        })
        assert r.status_code == 401

    def test_login_nonexistent_user(self, client, fresh_store):
        r = client.post("/api/auth/login", json={
            "username": "ghost",
            "password": "secret",
        })
        assert r.status_code == 401

    def test_me(self, client, fresh_store):
        client.post("/api/auth/register", json={
            "username": "carol",
            "password": "secret",
        })
        r = client.post("/api/auth/login", json={
            "username": "carol",
            "password": "secret",
        })
        token = r.json()["access_token"]

        # 无 token
        r = client.get("/api/auth/me")
        assert r.status_code == 401

        # 有 token
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["username"] == "carol"

    def test_me_invalid_token(self, client, fresh_store):
        r = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid-token"})
        assert r.status_code == 401
