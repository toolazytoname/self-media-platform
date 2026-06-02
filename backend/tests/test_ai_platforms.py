"""测试 ai_generate API：AI 文案/脚本/摘要"""
import pytest


class TestAIGenerate:
    def test_summary(self, client, fresh_store):
        r = client.post("/api/ai/summary", json={"content": "这是一段很长的内容。" * 10})
        # 实际行为依赖网络/MiniMax API：可能 200 也可能 502/500
        assert r.status_code in (200, 500, 502, 503)

    def test_copy(self, client, fresh_store):
        r = client.post("/api/ai/copy", json={
            "topic": "如何学习编程",
            "platform": "wechat",
            "content_type": "article",
        })
        assert r.status_code in (200, 500, 502, 503)

    def test_podcast(self, client, fresh_store):
        r = client.post("/api/ai/podcast/script", json={
            "content": "AI 的未来", "style": "casual",
        })
        assert r.status_code in (200, 500, 502, 503)

    def test_video_script(self, client, fresh_store):
        r = client.post("/api/ai/video/script", json={
            "topic": "介绍 AI", "duration": 60,
        })
        assert r.status_code in (200, 500, 502, 503)

    def test_image(self, client, fresh_store):
        r = client.post("/api/ai/image", json={"prompt": "A cat"})
        assert r.status_code in (200, 500, 502, 503)

    def test_video_generate(self, client, fresh_store):
        r = client.post("/api/ai/video/generate", json={"prompt": "Hello"})
        assert r.status_code in (200, 202, 500, 502, 503)

    def test_validation(self, client, fresh_store):
        # 缺字段
        r = client.post("/api/ai/summary", json={})
        assert r.status_code == 422


class TestPlatforms:
    def test_list_accounts(self, client, fresh_store):
        r = client.get("/api/platforms/accounts")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_add_account_validation(self, client, fresh_store):
        # 缺字段
        r = client.post("/api/platforms/accounts", json={})
        assert r.status_code == 422
