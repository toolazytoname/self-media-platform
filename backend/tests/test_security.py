"""测试 security 模块：JWT 与密码哈希"""
import time
import pytest
from app.core.security import (
    hash_password, verify_password,
    create_access_token, decode_token,
)


class TestPasswordHash:
    def test_hash_and_verify(self):
        h = hash_password("secret123")
        assert h != "secret123"  # 应该是哈希值
        assert verify_password("secret123", h) is True

    def test_wrong_password(self):
        h = hash_password("secret123")
        assert verify_password("wrong", h) is False

    def test_empty_password(self):
        h = hash_password("secret")
        assert verify_password("", h) is False


class TestJWTToken:
    def test_create_and_decode(self):
        token = create_access_token("alice", {"role": "admin"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "alice"
        assert payload["role"] == "admin"
        assert "exp" in payload
        assert "iat" in payload

    def test_invalid_token(self):
        assert decode_token("not-a-token") is None
        assert decode_token("") is None

    def test_expired_token(self):
        # 创建 1 分钟过期
        token = create_access_token("alice", expires_minutes=0)
        # 立即解码应失败（已过期）
        time.sleep(1)
        assert decode_token(token) is None
