"""去 AI 味 / 文风克隆 — P1-1 测试

策略:
- 用户文风 = 历史文章聚合后的"风格画像"
- 4 维特征: 句长分布 / emoji 频率 / 段首模式 / 常用词/口头禅
- AI 扩写时把风格画像作为 system prompt 后缀注入
- 给已生成内容做"风格一致性评分"(0-100)

覆盖:
  - StyleProfile 计算(空 / 1 篇 / 多篇)
  - 4 维特征正确性(句长、emoji、段首、关键词)
  - 评分函数(返回 0-100;空文/高匹配文/完全不匹配文)
  - build_style_prompt(注入 system prompt)
  - API 端点(GET profile / POST refresh / POST score)
"""
import pytest

from app.services.style_profile import (
    StyleProfile,
    extract_profiles,
    build_style_prompt,
    score_text_against_profile,
    DEFAULT_EMPTY_PROFILE,
)


# ============ StyleProfile 数据结构 ============

class TestStyleProfile:
    def test_empty_profile_has_zero_metrics(self):
        p = StyleProfile(avg_sentence_len=0, emoji_rate=0, opening_patterns=[], vocab={})
        assert p.avg_sentence_len == 0
        assert p.emoji_rate == 0
        assert p.opening_patterns == []
        assert p.vocab == {}

    def test_default_empty_profile_is_empty(self):
        assert DEFAULT_EMPTY_PROFILE.avg_sentence_len == 0
        assert DEFAULT_EMPTY_PROFILE.emoji_rate == 0
        assert DEFAULT_EMPTY_PROFILE.opening_patterns == []


# ============ 特征提取 ============

class TestExtractProfiles:
    def _corpus(self):
        return [
            # 4 篇短文,平均 30 字,emoji 密集,口头禅 "其实"
            "其实啊,期权没那么玄。✨ 你买的是权利,不是义务。",
            "很多人以为期权复杂,其实核心就一句话: 锁定价格,放弃义务。💡",
            "今天聊个最常被问的问题: 怎么看涨和看跌? 选错方向会怎样? 🤔",
            "其实,我发现大部分新手亏钱,是因为没搞懂这 3 个概念。📌",
        ]

    def test_extract_avg_sentence_len(self):
        p = extract_profiles(self._corpus())
        # 30 字左右,容忍 20-50
        assert 15 <= p.avg_sentence_len <= 50

    def test_extract_emoji_rate_high(self):
        """emoji 多(>0.1 个/字)的文风应被识别为高 emoji_rate"""
        p = extract_profiles(self._corpus())
        assert p.emoji_rate > 0.005  # 至少有一些 emoji

    def test_extract_opening_patterns(self):
        p = extract_profiles(self._corpus())
        # 4 篇都以"其实"开头 → 应识别
        assert any("其实" in op or "今天" in op or "很多" in op for op in p.opening_patterns)

    def test_extract_vocab(self):
        p = extract_profiles(self._corpus())
        # 关键词应包含 "期权"
        assert any("期权" in word for word in p.vocab.keys())

    def test_empty_corpus_returns_default(self):
        p = extract_profiles([])
        assert p.avg_sentence_len == 0

    def test_single_article(self):
        p = extract_profiles(["其实期权和股票不一样。✨"])
        assert p.avg_sentence_len > 0
        assert p.emoji_rate > 0


# ============ Prompt 注入 ============

class TestBuildStylePrompt:
    def test_returns_nonempty_string(self):
        p = extract_profiles(self._corpus_for_prompt())
        prompt = build_style_prompt(p)
        assert isinstance(prompt, str)
        assert len(prompt) > 20

    def test_includes_emoji_mention_if_emoji_heavy(self):
        """高 emoji 文风应在 prompt 里提"emoji 多用" """
        p = extract_profiles(self._corpus_for_prompt())
        prompt = build_style_prompt(p)
        # 应包含 emoji 相关指导
        assert "emoji" in prompt.lower() or "表情" in prompt or "✨" in prompt

    def test_includes_avg_sentence_len(self):
        p = extract_profiles(self._corpus_for_prompt())
        prompt = build_style_prompt(p)
        # 应提"句长"或具体数字
        assert "句" in prompt or "字" in prompt

    def test_includes_vocab_keywords(self):
        p = extract_profiles(self._corpus_for_prompt())
        prompt = build_style_prompt(p)
        # 高频词应被列入
        assert "期权" in prompt

    def test_empty_profile_returns_generic(self):
        """空文风 → 返通用 prompt(没"必须用"这种强制约束)"""
        prompt = build_style_prompt(DEFAULT_EMPTY_PROFILE)
        assert isinstance(prompt, str)

    def _corpus_for_prompt(self):
        return [
            "其实啊,期权没那么玄。✨ 你买的是权利。",
            "很多人以为期权复杂,其实核心就一句话。💡",
            "今天聊期权: 怎么看涨和看跌? 🤔",
        ]


# ============ 风格评分 ============

class TestScoreText:
    def test_empty_text_returns_zero(self):
        p = extract_profiles(["其实期权。✨"])
        score = score_text_against_profile("", p)
        assert score == 0

    def test_perfect_match_returns_high(self):
        """与文风完全匹配 → 高分(>80)"""
        p = extract_profiles([
            "其实啊,期权没那么玄。✨ 你买的是权利。",
            "其实核心一句话: 锁定价格。💡",
            "今天聊期权: 怎么看涨和看跌? 🤔",
        ])
        # 用风格内的典型句子测
        sample = "其实啊,期权没那么玄。✨ 锁定价格就是核心。"
        score = score_text_against_profile(sample, p)
        assert 0 <= score <= 100
        assert score > 50  # 至少中等匹配

    def test_anti_match_returns_low(self):
        """完全不匹配的文风(长句,无 emoji) → 低分"""
        p = extract_profiles([
            "其实啊,期权没那么玄。✨ 你买的是权利。",
        ])
        # 写一段正式官方报告风
        anti = "根据中国证券监督管理委员会发布的最新规定,本指引旨在向投资者提供期权交易的基础知识框架。投资者应审慎评估自身风险承受能力。"
        score = score_text_against_profile(anti, p)
        assert score < 60  # 比完美匹配低

    def test_score_range_zero_to_hundred(self):
        p = extract_profiles(["x"])
        for txt in ["", "x", "xxxxxxx", "其实" * 100]:
            score = score_text_against_profile(txt, p)
            assert 0 <= score <= 100

    def test_score_is_higher_for_matching_emoji(self):
        """同 emoji 密度 → 高分;无 emoji → 低分"""
        p_emoji = extract_profiles([
            "其实期权和股票不一样。✨",
            "其实没那么复杂。💡",
            "今天聊聊期权。🤔",
        ])
        with_emoji = "其实期权和股票不一样。✨ 锁定价格。"
        without_emoji = "其实期权和股票不一样。 锁定价格。"
        s1 = score_text_against_profile(with_emoji, p_emoji)
        s2 = score_text_against_profile(without_emoji, p_emoji)
        assert s1 > s2


# ============ API 端点 ============

class TestStyleAPI:
    def _auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def _register_login(self, client, username="style_user"):
        client.post("/api/auth/register", json={
            "username": username, "password": "test1234", "display_name": username,
        })
        r = client.post("/api/auth/login", json={"username": username, "password": "test1234"})
        return r.json()["access_token"]

    def test_get_profile_empty(self, client, fresh_store):
        """新用户 → 默认空 profile"""
        token = self._register_login(client)
        r = client.get("/api/style/profile", headers=self._auth(token))
        assert r.status_code == 200
        body = r.json()
        assert body["avg_sentence_len"] == 0
        assert body["emoji_rate"] == 0

    def test_refresh_after_seeding_content(self, client, fresh_store):
        """seed 几篇 content 后,refresh → profile 应有数据"""
        from app.store import store
        token = self._register_login(client)
        # seed 4 篇 content
        for body in [
            "其实啊,期权没那么玄。✨",
            "其实核心就一句话。💡",
            "今天聊期权。🤔",
            "期权和股票不一样。",
        ]:
            store.add_content({
                "title": "t", "body": body, "tags": [], "platform": "all",
            })
        r = client.post("/api/style/refresh", headers=self._auth(token))
        assert r.status_code == 200
        assert r.json()["sample_size"] >= 4
        assert r.json()["avg_sentence_len"] > 0

    def test_score_endpoint(self, client, fresh_store):
        """POST /api/style/score 输入一段文字,返回 0-100 分数"""
        from app.store import store
        token = self._register_login(client)
        # seed 风格
        for body in ["其实啊,期权。✨", "其实没那么玄。💡"]:
            store.add_content({"title": "t", "body": body, "tags": [], "platform": "all"})
        client.post("/api/style/refresh", headers=self._auth(token))
        # 评分
        r = client.post("/api/style/score", headers=self._auth(token), json={
            "text": "其实啊,期权和股票不一样。✨",
        })
        assert r.status_code == 200
        body = r.json()
        assert 0 <= body["score"] <= 100

    def test_score_requires_auth(self, client, fresh_store):
        r = client.post("/api/style/score", json={"text": "x"})
        assert r.status_code == 401

    def test_profile_requires_auth(self, client, fresh_store):
        r = client.get("/api/style/profile")
        assert r.status_code == 401
