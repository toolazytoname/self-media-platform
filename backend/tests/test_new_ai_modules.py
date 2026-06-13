"""Phase B.5: 新增 AI 模块(扩写/标题/标签) + ai_creations 历史

镜像现有 test_ai_platforms.py 风格,全程通过 TestClient,关键路径 mock。
"""
import pytest
import shutil
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.ai_providers import get_provider, register_provider
from app.services.ai_providers.base import BaseProvider
from app.store import store


def _copy_pdf(name: str) -> str:
    src = Path("/Users/lazy/Code/crack/claude/self-media-platform/data") / name
    if not src.exists():
        pytest.skip(f"测试 PDF 不存在: {src}")
    dst_dir = Path("/tmp/source_ctx_test")
    dst_dir.mkdir(exist_ok=True)
    dst = dst_dir / name
    shutil.copy(src, dst)
    return str(dst)


# ============ Mock provider for tests ============

class MockProvider(BaseProvider):
    """测试用:可控响应,模块级单例(测试间共享 _response 状态)。"""
    label = "Mock"
    name = "mock"
    default_model = "mock-1"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._response = "mock response"
        self.last_messages = None

    async def chat(self, messages, model=None, max_tokens=2048, temperature=0.7, **kwargs):
        self.last_messages = messages
        return self._response


# 模块级单例 — 所有测试共享这一个实例(便于 set _response 影响后续调用)
_MOCK_INSTANCE = MockProvider()


@pytest.fixture(autouse=True)
def use_mock_provider():
    """整个 test module 自动用 mock provider。"""
    from app.services.ai_providers import _REGISTRY
    from app.core.config import settings
    # 注册 _MOCK_INSTANCE 作为 mock 的 provider(直接挂实例,工厂直接返它)
    _REGISTRY["mock"] = lambda *a, **k: _MOCK_INSTANCE
    original = settings.DEFAULT_AI_PROVIDER
    settings.DEFAULT_AI_PROVIDER = "mock"
    # 重置 mock 状态
    _MOCK_INSTANCE._response = "mock response"
    _MOCK_INSTANCE.last_messages = None
    yield _MOCK_INSTANCE
    _REGISTRY.pop("mock", None)
    settings.DEFAULT_AI_PROVIDER = original


@pytest.fixture
def mock_provider(use_mock_provider):
    """实例访问。"""
    return use_mock_provider


# ============ 扩写 ============

class TestExpand:
    def test_expand_happy_path(self, client, fresh_store, mock_provider):
        mock_provider._response = (
            "AI 改变生活是一个宏大的命题。它意味着我们日常的每一个细节——"
            "从搜索信息到出行规划,从工作协助到娱乐消费——都在被算法重塑。"
            "这种重塑不是冷冰冰的替代,而是赋能与延伸。AI 让人类有更多时间去"
        )
        r = client.post("/api/ai/expand", json={
            "content": "AI 改变生活", "target_length": "medium",
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert "expanded" in data
        # "AI 改变生活" — 中英文混排,精确 7 字符(AI + 空格 + 改 + 变 + 生 + 活 = 6 显示字符 + 1 空格 = 7)
        # 用 len() 而不是字面量,让中文测试也稳定
        assert data["original_length"] == len("AI 改变生活")
        assert data["expanded_length"] > 0
        assert data["target_length"] == "medium"
        assert data["ratio"] > 0

    def test_expand_target_length_options(self, client, fresh_store, mock_provider):
        """3 档 target_length 都通过"""
        mock_provider._response = "ok"
        for length in ("short", "medium", "long"):
            r = client.post("/api/ai/expand", json={
                "content": "x", "target_length": length,
            })
            assert r.status_code == 200, f"{length}: {r.text}"
            assert r.json()["target_length"] == length

    def test_expand_3_tones(self, client, fresh_store, mock_provider):
        """casual / formal / academic 3 种 tone 都通过"""
        mock_provider._response = "ok"
        for tone in ("casual", "formal", "academic"):
            r = client.post("/api/ai/expand", json={
                "content": "x", "tone": tone,
            })
            assert r.status_code == 200, f"{tone}: {r.text}"
            assert r.json()["tone"] == tone
            # 验证 prompt 包含对应 tone 提示词
            sys_msg = mock_provider.last_messages[0]["content"]
            if tone == "casual":
                assert "轻松" in sys_msg or "口语" in sys_msg
            elif tone == "formal":
                assert "正式" in sys_msg or "严谨" in sys_msg
            elif tone == "academic":
                assert "学术" in sys_msg or "论据" in sys_msg


# ============ 标题 ============

class TestTitles:
    def test_titles_happy_path(self, client, fresh_store, mock_provider):
        mock_provider._response = (
            "AI 如何重塑自媒体\n"
            "未来已来:AI 创作工具深度评测\n"
            "从 0 到 1:我的 AI 内容工作流\n"
            "不写一行代码:AI 帮你做短视频\n"
            "AI 创作全攻略:效率翻 10 倍"
        )
        r = client.post("/api/ai/titles", json={
            "content": "AI 改变自媒体创作", "n": 5,
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["total"] >= 3
        assert all("text" in t for t in data["titles"])
        # 每个标题 2-50 字
        for t in data["titles"]:
            assert 2 <= len(t["text"]) <= 50

    def test_titles_platform_hint(self, client, fresh_store, mock_provider):
        """platform=douyin 时 prompt 含平台提示词"""
        mock_provider._response = "ok"
        r = client.post("/api/ai/titles", json={
            "content": "x", "n": 3, "platform": "douyin", "style": "clickbait",
        })
        assert r.status_code == 200
        sys_msg = mock_provider.last_messages[0]["content"]
        assert "抖音" in sys_msg  # 中文平台名
        assert "clickbait" in sys_msg.lower() or "点击" in sys_msg

    def test_titles_default_neutral(self, client, fresh_store, mock_provider):
        """默认 style=neutral, prompt 含中性描述"""
        mock_provider._response = "ok"
        r = client.post("/api/ai/titles", json={"content": "x", "n": 1})
        assert r.status_code == 200
        sys_msg = mock_provider.last_messages[0]["content"]
        assert "中性" in sys_msg


# ============ 标签 ============

class TestTags:
    def test_tags_happy_path(self, client, fresh_store, mock_provider):
        mock_provider._response = (
            "topic|AI\n"
            "topic|自媒体\n"
            "emotion|inspiring\n"
            "audience|content creators\n"
            "trending|chatgpt"
        )
        r = client.post("/api/ai/tags", json={
            "content": "AI 改变自媒体", "n": 5, "locale": "mixed",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 5
        # 4 个 group 都有
        groups = {t["group"] for t in data["tags"]}
        assert "topic" in groups
        assert "emotion" in groups
        assert "audience" in groups
        assert "trending" in groups

    def test_tags_locale_options(self, client, fresh_store, mock_provider):
        """4 种 locale 都通过"""
        mock_provider._response = "ok"
        for locale in ("zh", "en", "emoji", "mixed"):
            r = client.post("/api/ai/tags", json={
                "content": "x", "n": 1, "locale": locale,
            })
            assert r.status_code == 200, f"{locale}: {r.text}"
            assert r.json()["locale"] == locale
            sys_msg = mock_provider.last_messages[0]["content"]
            # 验证 prompt 含 locale 描述
            if locale == "zh":
                assert "中文" in sys_msg
            elif locale == "en":
                assert "英文" in sys_msg
            elif locale == "emoji":
                assert "emoji" in sys_msg.lower()
            elif locale == "mixed":
                assert "混合" in sys_msg or "中英" in sys_msg

    def test_tags_malformed_lines_ignored(self, client, fresh_store, mock_provider):
        """格式不对的行被忽略(没 | 分隔 + 不在合法 group 里的)"""
        mock_provider._response = (
            "topic|AI\n"                    # ok
            "this line has no pipe\n"      # bad: 没 |
            "invalid_group|test\n"         # bad: group 不在 4 个里
            "audience|devs\n"              # ok
        )
        r = client.post("/api/ai/tags", json={"content": "x", "n": 10})
        assert r.status_code == 200
        data = r.json()
        # 应该 2 个有效的
        assert data["total"] == 2
        groups = {t["group"] for t in data["tags"]}
        assert "topic" in groups
        assert "audience" in groups


# ============ AI Creations 历史 ============

class TestAICreations:
    def test_ai_creations_recorded_after_call(self, client, fresh_store, mock_provider):
        """每个 AI 端点调后,store.creations 多一条"""
        mock_provider._response = "ok 1\nok 2"
        before = len(store.list_creations())
        client.post("/api/ai/expand", json={"content": "test1", "target_length": "short"})
        client.post("/api/ai/titles", json={"content": "test2", "n": 2})
        client.post("/api/ai/tags", json={"content": "test3", "n": 3})
        after = len(store.list_creations())
        assert after - before == 3
        # 类型正确
        types = [c["type"] for c in store.list_creations()]
        assert "expand" in types
        assert "titles" in types
        assert "tags" in types

    def test_ai_creations_list_filter_by_type(self, client, fresh_store, mock_provider):
        """list_creations(type) 只返指定类型"""
        mock_provider._response = "ok"
        client.post("/api/ai/expand", json={"content": "x"})
        client.post("/api/ai/titles", json={"content": "x", "n": 1})
        client.post("/api/ai/expand", json={"content": "y"})
        # 只返 expand
        items = store.list_creations(type="expand")
        assert all(c["type"] == "expand" for c in items)
        assert len(items) == 2

    def test_ai_creations_list_endpoint(self, client, fresh_store, mock_provider):
        """GET /api/ai/creations 返 JSON"""
        mock_provider._response = "ok"
        client.post("/api/ai/expand", json={"content": "x"})
        r = client.get("/api/ai/creations?type=expand&limit=10")
        assert r.status_code == 200
        data = r.json()
        assert "total" in data
        assert "items" in data
        assert all(c["type"] == "expand" for c in data["items"])

    def test_ai_creations_get_and_delete(self, client, fresh_store, mock_provider):
        """GET /{id} + DELETE /{id} 路径"""
        mock_provider._response = "ok"
        client.post("/api/ai/expand", json={"content": "x"})
        items = store.list_creations(type="expand")
        assert len(items) == 1
        cid = items[0]["id"]
        # GET
        r = client.get(f"/api/ai/creations/{cid}")
        assert r.status_code == 200
        assert r.json()["id"] == cid
        # GET missing
        r = client.get("/api/ai/creations/nonexistent")
        assert r.status_code == 404
        # DELETE
        r = client.delete(f"/api/ai/creations/{cid}")
        assert r.status_code == 200
        assert r.json()["ok"] is True
        # 二次 DELETE → 404
        r = client.delete(f"/api/ai/creations/{cid}")
        assert r.status_code == 404

    def test_ai_creations_records_provider_and_latency(self, client, fresh_store, mock_provider):
        """creation 记录含 provider + latency_ms"""
        mock_provider._response = "ok"
        client.post("/api/ai/expand", json={"content": "x"})
        rec = store.list_creations(type="expand")[0]
        assert rec["provider"] == "mock"
        assert "latency_ms" in rec
        assert rec["latency_ms"] >= 0
        # prompt + result 都有
        assert "prompt" in rec
        assert "result" in rec
        assert rec["result"] == "ok"


# ============ Phase 3: 来源 context 注入 ============

class TestSourceContextInjection:
    """AI 端点接受 source_id / chapter_id 时,把章节内容注入到 system message 头部。"""

    def test_expand_with_text_source(self, client, fresh_store, mock_provider):
        """text 类型 source: 整篇 content 注入。"""
        client.post("/api/sources", json={
            "name": "notes", "type": "text",
            "content": "这是来自我的笔记的一段话,讲述 AI 改变生活的故事。",
        })
        src_id = client.get("/api/sources").json()[0]["id"]
        r = client.post("/api/ai/expand", json={
            "content": "原文",
            "target_length": "medium",
            "source_id": src_id,
        })
        assert r.status_code == 200
        # mock provider 的 last_messages 应该含 source context
        msgs = mock_provider.last_messages
        assert any("参考资料来源" in m.get("content", "") for m in msgs)
        # 来源内容也应该注入
        assert any("AI 改变生活" in m.get("content", "") for m in msgs)

    def test_expand_with_pdf_chapter(self, client, fresh_store, mock_provider):
        """pdf + chapter_id: 单章内容注入(懒加载)。"""
        path = _copy_pdf("小狗钱钱.pdf")
        sid = client.post("/api/sources", json={
            "name": "x", "type": "pdf", "path": path,
        }).json()["id"]
        chapters = client.get(f"/api/sources/{sid}/chapters").json()
        first_ch = chapters[0]
        r = client.post("/api/ai/expand", json={
            "content": "用小狗钱钱第一章做扩写输入",
            "source_id": sid,
            "chapter_id": first_ch["id"],
        })
        assert r.status_code == 200
        msgs = mock_provider.last_messages
        # source context 注入,且是 chapter 全文(触发懒加载)
        assert any("拉布拉多" in m.get("content", "") for m in msgs)

    def test_no_source_id_no_injection(self, client, fresh_store, mock_provider):
        """没传 source_id → 不注入 context。"""
        client.post("/api/ai/expand", json={"content": "无 source"})
        msgs = mock_provider.last_messages
        assert not any("参考资料来源" in m.get("content", "") for m in msgs)

    def test_invalid_source_id_silently_ignored(self, client, fresh_store, mock_provider):
        """source_id 不存在 → 当没传处理,不报错。"""
        r = client.post("/api/ai/expand", json={
            "content": "x",
            "source_id": "src_nonexistent",
        })
        assert r.status_code == 200
        msgs = mock_provider.last_messages
        assert not any("参考资料来源" in m.get("content", "") for m in msgs)

    def test_titles_with_source(self, client, fresh_store, mock_provider):
        """titles 模块也接 source_id。"""
        client.post("/api/sources", json={
            "name": "t", "type": "text",
            "content": "AI 在内容创作领域的应用。",
        })
        src_id = client.get("/api/sources").json()[0]["id"]
        mock_provider._response = "标题1\n标题2"
        r = client.post("/api/ai/titles", json={
            "content": "x",
            "source_id": src_id,
        })
        assert r.status_code == 200
        assert any("参考资料来源" in m.get("content", "") for m in mock_provider.last_messages)
