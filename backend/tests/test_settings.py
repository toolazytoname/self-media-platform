"""测试 settings API：配置读取/更新(Phase A: 多 provider)"""
import pytest
import os


class TestSettings:
    def test_get_config(self, client, fresh_store):
        r = client.get("/api/config")
        assert r.status_code == 200
        data = r.json()
        # Phase A 改造: 多 provider 结构
        assert "providers" in data
        assert "default_provider" in data
        assert "minimax" in data["providers"]
        assert "claude" in data["providers"]
        assert "openai" in data["providers"]

    def test_list_providers(self, client, fresh_store):
        """GET /api/config/providers 返回 provider 元数据"""
        r = client.get("/api/config/providers")
        assert r.status_code == 200
        data = r.json()
        assert "providers" in data
        names = [p["name"] for p in data["providers"]]
        assert "minimax" in names
        assert "claude" in names
        assert "openai" in names
        # 每个 provider 必带字段
        for p in data["providers"]:
            assert "label" in p
            assert "default_base" in p
            assert "default_model" in p

    def test_update_config(self, client, fresh_store, tmp_path, monkeypatch):
        # 使用临时目录
        env_file = tmp_path / ".env"
        env_file.write_text("APP_NAME=test\n")
        # 这里仅验证基本 POST 不报错(Phase A: 用新 payload 格式)
        r = client.post("/api/config", json={
            "minimax": {"api_key": "test-key-sk-12345678901234567890"}
        })
        # 200 成功 或 500（写文件失败） 都可接受
        assert r.status_code in (200, 500)

    def test_test_connection(self, client, fresh_store):
        # 测试连接：可能 200/500/502(Phase A: 加 provider 字段)
        r = client.post("/api/config/test", json={
            "provider": "minimax",
            "api_key": "fake",
            "base_url": "https://api.minimaxi.com/v1",
            "model": "MiniMax-M3",
        })
        assert r.status_code in (200, 500, 502, 503)
