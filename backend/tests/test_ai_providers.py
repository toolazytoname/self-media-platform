"""Phase A.5: AI Provider 抽象测试

覆盖:
  - 工厂: get_provider / register_provider / supported_providers
  - 3 个 provider 的请求结构(用 respx 拦截 httpx)
  - 缺 API key 抛 ValueError
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


# ============ 工厂 ============

class TestFactory:
    def test_get_provider_unknown_raises(self):
        from app.services.ai_providers import get_provider
        with pytest.raises(NotImplementedError, match="未注册"):
            get_provider("nonexistent_provider_xyz")

    def test_supported_providers_after_register(self):
        from app.services.ai_providers import register_provider, supported_providers, _REGISTRY
        from app.services.ai_providers.base import BaseProvider

        class TempProvider(BaseProvider):
            label = "Temp"
            name = "temp_factory_test"

            async def chat(self, messages, model=None, **kwargs):
                return "x"

        register_provider("temp_factory_test", TempProvider)
        try:
            assert "temp_factory_test" in supported_providers()
        finally:
            _REGISTRY.pop("temp_factory_test", None)

    def test_default_provider_name_fallback(self):
        from app.services.ai_providers import get_default_provider_name
        from app.core.config import settings
        # 不管 settings.DEFAULT_AI_PROVIDER 是什么,返回值要么是注册表里的,要么是 'minimax'
        name = get_default_provider_name()
        assert name in ("minimax", "claude", "openai")


# ============ ClaudeProvider ============

class TestClaudeProvider:
    def test_no_api_key_raises(self):
        from app.services.ai_providers.claude_provider import ClaudeProvider
        from app.core.config import settings
        # 清空 env var + 字段
        with patch.object(settings, "CLAUDE_API_KEY", None):
            with patch.dict("os.environ", {}, clear=False):
                with patch.dict("os.environ", {"CLAUDE_API_KEY": ""}, clear=False):
                    p = ClaudeProvider()
                    with pytest.raises(ValueError, match="未配置"):
                        import asyncio
                        asyncio.run(p.chat([{"role": "user", "content": "x"}]))

    def test_request_structure(self):
        """Claude chat 应该用 x-api-key + anthropic-version 头,POST /v1/messages,body 含 max_tokens"""
        from app.services.ai_providers.claude_provider import ClaudeProvider
        import httpx

        # mock 整个 httpx.AsyncClient
        captured = {}

        class FakeResp:
            status_code = 200
            def json(self):
                return {"content": [{"type": "text", "text": "claude says hi"}]}
            def raise_for_status(self):
                pass

        async def fake_post(self, url, headers=None, json=None, **kwargs):
            captured["url"] = url
            captured["headers"] = headers
            captured["body"] = json
            return FakeResp()

        with patch.object(httpx.AsyncClient, "post", fake_post):
            p = ClaudeProvider(api_key="sk-ant-test12345", base_url="https://api.anthropic.com", default_model="claude-haiku-4-5")
            import asyncio
            result = asyncio.run(p.chat(
                [{"role": "system", "content": "be helpful"}, {"role": "user", "content": "hi"}],
                max_tokens=512,
            ))
        assert result == "claude says hi"
        assert captured["url"] == "https://api.anthropic.com/v1/messages"
        assert captured["headers"]["x-api-key"] == "sk-ant-test12345"
        assert captured["headers"]["anthropic-version"] == "2023-06-01"
        # system 抽到 body.system,user 进 messages
        assert captured["body"]["system"] == "be helpful"
        assert captured["body"]["messages"] == [{"role": "user", "content": "hi"}]
        assert captured["body"]["max_tokens"] == 512
        assert captured["body"]["model"] == "claude-haiku-4-5"


# ============ OpenAIProvider ============

class TestOpenAIProvider:
    def test_no_api_key_raises(self):
        from app.services.ai_providers.openai_provider import OpenAIProvider
        from app.core.config import settings
        with patch.object(settings, "OPENAI_API_KEY", None):
            with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False):
                p = OpenAIProvider()
                with pytest.raises(ValueError, match="未配置"):
                    import asyncio
                    asyncio.run(p.chat([{"role": "user", "content": "x"}]))

    def test_request_structure(self):
        """OpenAI chat 走 Bearer auth,POST /chat/completions,body 含 max_tokens"""
        from app.services.ai_providers.openai_provider import OpenAIProvider
        import httpx

        captured = {}

        class FakeResp:
            status_code = 200
            def json(self):
                return {"choices": [{"message": {"content": "openai says hi"}}]}
            def raise_for_status(self):
                pass

        async def fake_post(self, url, headers=None, json=None, **kwargs):
            captured["url"] = url
            captured["headers"] = headers
            captured["body"] = json
            return FakeResp()

        with patch.object(httpx.AsyncClient, "post", fake_post):
            p = OpenAIProvider(api_key="sk-test12345", base_url="https://api.openai.com/v1", default_model="gpt-4o-mini")
            import asyncio
            result = asyncio.run(p.chat(
                [{"role": "user", "content": "hi"}],
                max_tokens=1024,
            ))
        assert result == "openai says hi"
        assert captured["url"] == "https://api.openai.com/v1/chat/completions"
        assert captured["headers"]["Authorization"] == "Bearer sk-test12345"
        assert captured["body"]["messages"] == [{"role": "user", "content": "hi"}]
        assert captured["body"]["max_tokens"] == 1024
        assert captured["body"]["model"] == "gpt-4o-mini"


# ============ MiniMaxProvider ============

class TestMiniMaxProvider:
    def test_provider_passes_through_to_client(self):
        """MiniMaxProvider.chat 直接调 MiniMaxClient.chat"""
        from app.services.ai_providers.minimax_provider import MiniMaxProvider
        from app.services import minimax_client as mmc
        captured = {}
        async def fake_chat(self, messages, model=None, **kwargs):
            captured["messages"] = messages
            captured["model"] = model
            return "minimax ok"
        with patch.object(mmc.MiniMaxClient, "chat", fake_chat):
            p = MiniMaxProvider(api_key="sk-test", base_url="https://api.minimaxi.com/v1", default_model="MiniMax-M3")
            import asyncio
            result = asyncio.run(p.chat([{"role": "user", "content": "hi"}]))
        assert result == "minimax ok"
        assert captured["model"] == "MiniMax-M3"

    def test_is_configured_checks_api_key(self):
        from app.services.ai_providers.minimax_provider import MiniMaxProvider
        from app.core.config import settings
        with patch.object(settings, "MINIMAX_API_KEY", "sk-cp-test12345"):
            p = MiniMaxProvider()
            assert p.is_configured() is True
        with patch.object(settings, "MINIMAX_API_KEY", ""):
            p = MiniMaxProvider(api_key="")
            assert p.is_configured() is False


# ============ BaseProvider ============

class TestBaseProvider:
    def test_chat_is_abstract(self):
        from app.services.ai_providers.base import BaseProvider
        with pytest.raises(TypeError):
            # 不能直接实例化抽象类
            BaseProvider()
