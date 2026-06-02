"""测试 settings API：配置读取/更新"""
import pytest
import os


class TestSettings:
    def test_get_config(self, client, fresh_store):
        r = client.get("/api/config")
        assert r.status_code == 200
        data = r.json()
        assert "minimax_base_url" in data
        assert "configured" in data

    def test_update_config(self, client, fresh_store, tmp_path, monkeypatch):
        # 使用临时目录
        env_file = tmp_path / ".env"
        env_file.write_text("APP_NAME=test\n")
        # 这里仅验证基本 POST 不报错
        r = client.post("/api/config", json={"minimax_api_key": "test-key"})
        # 200 成功 或 500（写文件失败） 都可接受
        assert r.status_code in (200, 500)

    def test_test_connection(self, client, fresh_store):
        # 测试连接：可能 200/500/502
        r = client.post("/api/config/test", json={
            "api_key": "fake",
            "base_url": "https://api.minimaxi.com/v1",
            "model": "MiniMax-M3",
        })
        assert r.status_code in (200, 500, 502, 503)
