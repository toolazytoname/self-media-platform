"""一稿多发 / 平台改写引擎 — TASK-P0-3 测试

覆盖:
  - POST /api/ai/adapt        并发 4 平台 LLM 改写, 返 4 variants
  - POST /api/ai/adapt/save   把选定 variant 创建为 draft Content
  - platform_tips 模板: 4 平台调性
  - 失败处理: 单平台 LLM fail → 其他平台仍成功(graceful degrade)
  - 单平台传参: 只输出目标平台
  - 字数约束: 公众号长文 / 小红书短 / 抖音脚本 / 知乎中长

约束:
  - mock chat_completion (走 chat_completion 直接调用,非 _timed_chat)
  - 测试只 mock LLM,不走真实 provider
"""
import asyncio
import time
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.store import store


# ============ 工具函数 ============

def _register_and_login(client, username="adapt_user", password="test1234"):
    r = client.post("/api/auth/register", json={
        "username": username, "password": password, "display_name": username,
    })
    assert r.status_code in (200, 201), r.text
    r = client.post("/api/auth/login", json={"username": username, "password": "test1234"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ============ /api/ai/adapt 并发 4 平台 ============

class TestAdaptEndpoint:
    """POST /api/ai/adapt — 输入 topic + platforms, 并发 LLM 调 4 平台."""

    def _mock_llm_per_platform(self):
        """返回一个 chat_completion mock: 根据 system prompt 里的 platform 关键词返对应内容。
        模拟"4 个平台并发改写"行为。
        """
        async def fake_chat(messages, model=None, provider=None, **kwargs):
            # 从 system prompt 里提取 platform 关键词
            sys = (messages[0].get("content") or "") if messages else ""
            if "公众号" in sys or "wechat" in sys.lower():
                return "【公众号深度长文】\n\n" + ("正文段 " * 50 + "\n") * 5
            if "小红书" in sys or "xiaohongshu" in sys.lower():
                return "【小红书笔记】✨ emoji 友好 ✨\n\n干货分享～"
            if "抖音" in sys or "douyin" in sys.lower():
                return "【抖音脚本】\n前3秒:震惊！\n中段:干货\n结尾:关注"
            if "知乎" in sys or "zhihu" in sys.lower():
                return "【知乎回答】\n\n## 背景\n...\n\n## 结论\n...\n" + ("段落" * 30)
            return "通用 fallback 内容"
        return fake_chat

    def test_default_4_platforms(self, client, fresh_store):
        """不传 platforms → 默认 4 平台 (wechat/xiaohongshu/douyin/zhihu), 并发改写"""
        token = _register_and_login(client)
        with patch("app.api.ai_generate.chat_completion", new=self._mock_llm_per_platform()):
            r = client.post("/api/ai/adapt", headers=_auth(token), json={
                "topic": "期权入门",
                "length_hint": "medium",
            })
        assert r.status_code == 200, r.text
        body = r.json()
        assert "variants" in body
        variants = body["variants"]
        assert len(variants) == 4
        platforms_seen = {v["platform"] for v in variants}
        assert platforms_seen == {"wechat", "xiaohongshu", "douyin", "zhihu"}

    def test_each_variant_has_title_and_body(self, client, fresh_store):
        """每个 variant 至少含 title + body + platform 字段"""
        token = _register_and_login(client)
        with patch("app.api.ai_generate.chat_completion", new=self._mock_llm_per_platform()):
            r = client.post("/api/ai/adapt", headers=_auth(token), json={
                "topic": "AI 工具盘点",
            })
        assert r.status_code == 200
        for v in r.json()["variants"]:
            assert "platform" in v
            assert "title" in v
            assert "body" in v
            assert v["body"]
            assert v["title"]

    def test_custom_platforms_subset(self, client, fresh_store):
        """传 platforms=['wechat','xiaohongshu'] → 只返 2 个 variants"""
        token = _register_and_login(client)
        with patch("app.api.ai_generate.chat_completion", new=self._mock_llm_per_platform()):
            r = client.post("/api/ai/adapt", headers=_auth(token), json={
                "topic": "X",
                "platforms": ["wechat", "xiaohongshu"],
            })
        assert r.status_code == 200
        assert len(r.json()["variants"]) == 2

    def test_partial_failure_returns_what_succeeded(self, client, fresh_store):
        """1 个平台 LLM fail → 其他 3 个仍成功, 返回 3 variants + 1 error"""
        async def fail_on_douyin(messages, **kwargs):
            sys = (messages[0].get("content") or "") if messages else ""
            if "抖音" in sys:
                raise Exception("抖音 LLM 临时挂了")
            # 其他平台正常
            if "公众号" in sys:
                return "公众号内容"
            if "小红书" in sys:
                return "小红书内容"
            if "知乎" in sys:
                return "知乎内容"
            return "通用"

        token = _register_and_login(client)
        with patch("app.api.ai_generate.chat_completion", new=fail_on_douyin):
            r = client.post("/api/ai/adapt", headers=_auth(token), json={"topic": "X"})
        assert r.status_code == 200
        body = r.json()
        assert len(body["variants"]) == 3
        # douyin 标记 failed
        failed = [v for v in body.get("failed", [])]
        assert "douyin" in failed

    def test_length_hint_medium(self, client, fresh_store):
        """length_hint 影响 system prompt(medium 应指导中篇)"""
        captured_prompts = []

        async def capture(messages, **kwargs):
            captured_prompts.append(messages[0]["content"])
            return "captured"

        token = _register_and_login(client)
        with patch("app.api.ai_generate.chat_completion", new=capture):
            r = client.post("/api/ai/adapt", headers=_auth(token), json={
                "topic": "X",
                "platforms": ["wechat"],
                "length_hint": "short",
            })
        assert r.status_code == 200
        # 至少有一个 prompt 含 "short" 或 "短" 字样
        assert any("短" in p or "short" in p.lower() for p in captured_prompts), \
            f"length_hint=short 应注入 prompt, 实际: {captured_prompts}"

    def test_uses_topic_in_prompt(self, client, fresh_store):
        """user prompt 必须包含 topic"""
        captured = []

        async def capture(messages, **kwargs):
            captured.append(messages)
            return "result"

        token = _register_and_login(client)
        with patch("app.api.ai_generate.chat_completion", new=capture):
            r = client.post("/api/ai/adapt", headers=_auth(token), json={
                "topic": "我的专属主题词",
                "platforms": ["wechat"],
            })
        assert r.status_code == 200
        assert any("我的专属主题词" in m[1]["content"] for m in captured)

    def test_requires_auth(self, client, fresh_store):
        """无 token → 401"""
        r = client.post("/api/ai/adapt", json={"topic": "X"})
        assert r.status_code == 401


# ============ /api/ai/adapt/save 把 variant 创建为 Content ============

class TestAdaptSaveEndpoint:
    """POST /api/ai/adapt/save — 把选定的 variant 创建为 draft Content."""

    def test_creates_content_from_variant(self, client, fresh_store):
        token = _register_and_login(client)
        r = client.post("/api/ai/adapt/save", headers=_auth(token), json={
            "title": "标题 X",
            "body": "正文 Y",
            "platform": "wechat",
            "tags": ["期权", "理财"],
        })
        assert r.status_code in (200, 201), r.text
        body = r.json()
        cid = body.get("content_id")
        assert cid
        # store.contents 里有这条
        c = next((x for x in store.contents if x["id"] == cid), None)
        assert c is not None
        assert c["title"] == "标题 X"
        assert c["body"] == "正文 Y"
        assert c["platform"] == "wechat"
        assert c["tags"] == ["期权", "理财"]
        assert c["status"] == "draft"

    def test_save_with_topic_links_back(self, client, fresh_store):
        """传 source_topic → Content 上记录 source_topic 字段(后续可做一稿多发追踪)"""
        token = _register_and_login(client)
        r = client.post("/api/ai/adapt/save", headers=_auth(token), json={
            "title": "T", "body": "B", "platform": "xiaohongshu",
            "source_topic": "我的主题词",
        })
        assert r.status_code in (200, 201)
        cid = r.json()["content_id"]
        c = next(x for x in store.contents if x["id"] == cid)
        assert c.get("source_topic") == "我的主题词"

    def test_save_requires_auth(self, client, fresh_store):
        r = client.post("/api/ai/adapt/save", json={
            "title": "T", "body": "B", "platform": "wechat",
        })
        assert r.status_code == 401


# ============ Platform tips 模板 ============

class TestPlatformTips:
    """验证 platform_tips dict 覆盖 4 个核心平台 + 各自有调性约束"""

    def test_all_four_platforms_have_tips(self):
        from app.api.ai_generate import PLATFORM_TIPS
        assert "wechat" in PLATFORM_TIPS
        assert "xiaohongshu" in PLATFORM_TIPS
        assert "douyin" in PLATFORM_TIPS
        assert "zhihu" in PLATFORM_TIPS

    def test_each_tip_has_length_guidance(self):
        """每个 tip 必须有字数/长度指导(防止 AI 写出不符合平台调性的内容)"""
        from app.api.ai_generate import PLATFORM_TIPS
        # 检查中文关键词: 字数 / 字 / 长度 / 短 / 长
        for platform, tip in PLATFORM_TIPS.items():
            assert any(kw in tip for kw in ("字", "长度", "短", "长", "中")), \
                f"{platform} tip 缺长度指导: {tip!r}"

    def test_wechat_tip_emphasizes_long_form(self):
        from app.api.ai_generate import PLATFORM_TIPS
        # 公众号应该长文
        assert any(kw in PLATFORM_TIPS["wechat"] for kw in ("长", "深度", "3000", "5000"))

    def test_xiaohongshu_tip_emphasizes_emoji(self):
        from app.api.ai_generate import PLATFORM_TIPS
        assert "emoji" in PLATFORM_TIPS["xiaohongshu"].lower() or "emoji" in PLATFORM_TIPS["xiaohongshu"]

    def test_douyin_tip_emphasizes_hook(self):
        from app.api.ai_generate import PLATFORM_TIPS
        # 抖音应该强调开头钩子
        assert any(kw in PLATFORM_TIPS["douyin"] for kw in ("钩", "前3秒", "开头"))

    def test_zhihu_tip_emphasizes_logic(self):
        from app.api.ai_generate import PLATFORM_TIPS
        assert any(kw in PLATFORM_TIPS["zhihu"] for kw in ("专业", "逻辑", "深度", "分析"))
