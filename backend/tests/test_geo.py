"""GEO 优化 — P1-3 测试

策略(MVP):
- 评估一段文字的 GEO 友好度(0-100)
- 提供 GEO-friendly 改写(AI 调用)
- 给出 checklist(用户写作时参考)

GEO 评估维度:
  1. 含 FAQ / Q&A 段落(AI 搜索喜欢 Q&A 形式)
  2. 含具体数据 / 数字(具体 > 抽象)
  3. 含来源 / 引用链接(可信度)
  4. 标题 / 段首含问题词(什么/怎么/为什么)
  5. 段落长度适配(单段 < 200 字,易被 AI 截取)
  6. 概念有明确定义(避免歧义)

覆盖:
  - check 评分函数(0-100)
  - 6 维特征单独可识别
  - build_checklist 返 checklist dict
  - rewrite 端点(AI mock)
  - /api/geo/check + /api/geo/optimize + /api/geo/checklist
"""
import pytest

from app.services.geo_service import (
    score_geo_friendliness,
    build_geo_checklist,
    GEO_DIMENSIONS,
    DEFAULT_CHECKLIST,
)


# ============ GEO 评分 ============

class TestGEOScore:
    def test_empty_returns_zero(self):
        score = score_geo_friendliness("")
        assert score == 0

    def test_perfect_text_scores_high(self):
        """全维度都满足 → 100 分"""
        text = """什么是期权? 期权是衍生品,赋予买方在未来某一时间以约定价格买入或卖出标的资产的权利。

回答: 期权有 2 种基本类型,看涨(Call)和看跌(Put)。根据 2024 年数据,中国期权市场成交额达 1.2 万亿。

引用来源: https://www.example.com/options-report.pdf

FAQ:
- 期权风险大吗? 是的,杠杆可放大亏损。
- 期权适合谁? 适合有一定金融基础且能承受高风险的投资者。"""
        score = score_geo_friendliness(text)
        assert score >= 80

    def test_no_qa_no_data_low_score(self):
        """没 Q&A 没数据没来源 → 低分"""
        text = "期权是一种金融工具,买入方有权利,卖出方有义务。它很复杂。"
        score = score_geo_friendliness(text)
        assert score < 60

    def test_qa_question_words_detected(self):
        """含 '什么是' / '怎么' / '为什么' 问题词 → 段首模式加分"""
        text = "什么是期权? 期权是衍生品。怎么交易期权? 需要开期权账户。"
        score = score_geo_friendliness(text)
        # 至少要 50+
        assert score >= 50

    def test_specific_numbers_score_higher(self):
        """含具体数字(2024 / 1.2 万亿) > 含笼统词(很多/大量)"""
        text_specific = "2024 年中国期权市场成交额达 1.2 万亿元,同比增长 23%。"
        text_vague = "近年来中国期权市场成交额大幅增长,数字很好看。"
        s1 = score_geo_friendliness(text_specific)
        s2 = score_geo_friendliness(text_vague)
        assert s1 > s2

    def test_citation_links_score_higher(self):
        """含 http(s) 链接 → 来源维度加分"""
        text_with = "据 https://example.com/report 报道,2024 年期权市场增长 30%。"
        text_without = "据某报告报道,2024 年期权市场增长 30%。"
        s1 = score_geo_friendliness(text_with)
        s2 = score_geo_friendliness(text_without)
        assert s1 > s2

    def test_score_range_zero_to_hundred(self):
        for txt in ["", "x", "x" * 1000, "## FAQ\n- 什么是 x?\n- 怎么 y?"]:
            s = score_geo_friendliness(txt)
            assert 0 <= s <= 100

    def test_score_includes_dimensions_breakdown(self):
        """score_geo_friendliness 可返 breakdown dict 看各维度得分"""
        result = score_geo_friendliness("什么是 x? 2024 年增长 30%", return_breakdown=True)
        assert "score" in result
        assert "dimensions" in result
        # 6 维
        assert len(result["dimensions"]) == 6


# ============ Checklist ============

class TestChecklist:
    def test_default_checklist_has_all_dimensions(self):
        assert len(DEFAULT_CHECKLIST) == 6
        for d in GEO_DIMENSIONS:
            assert d in DEFAULT_CHECKLIST

    def test_build_checklist_returns_tips(self):
        cl = build_geo_checklist("纯文本,啥都没有")
        assert isinstance(cl, dict)
        assert len(cl) == 6
        for dim, info in cl.items():
            assert "score" in info
            assert "tip" in info
            assert 0 <= info["score"] <= 100


# ============ API ============

class TestGEOAPI:
    def _auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def _register_login(self, client, username="geo_user"):
        client.post("/api/auth/register", json={
            "username": username, "password": "test1234", "display_name": username,
        })
        r = client.post("/api/auth/login", json={"username": username, "password": "test1234"})
        return r.json()["access_token"]

    def test_check_endpoint(self, client, fresh_store):
        token = self._register_login(client)
        r = client.post("/api/geo/check", headers=self._auth(token), json={
            "text": "什么是期权? 2024 年市场成交 1.2 万亿,https://x.com/report",
        })
        assert r.status_code == 200
        body = r.json()
        assert "score" in body
        assert body["score"] >= 50
        assert "checklist" in body

    def test_optimize_endpoint_uses_ai(self, client, fresh_store):
        """optimize 端点调 AI chat_completion, 返改写后文本"""
        from unittest.mock import patch, AsyncMock
        token = self._register_login(client)
        with patch("app.api.geo.chat_completion", new=AsyncMock(
            return_value="【GEO 重写】什么是期权? 2024 年...",
        )):
            r = client.post("/api/geo/optimize", headers=self._auth(token), json={
                "text": "期权很复杂。", "provider": "minimax",
            })
        assert r.status_code == 200
        body = r.json()
        assert "GEO 重写" in body["optimized"]
        assert "original_score" in body

    def test_checklist_endpoint(self, client, fresh_store):
        token = self._register_login(client)
        r = client.get("/api/geo/checklist", headers=self._auth(token))
        assert r.status_code == 200
        body = r.json()
        # 6 维
        assert len(body) == 6

    def test_check_requires_auth(self, client, fresh_store):
        r = client.post("/api/geo/check", json={"text": "x"})
        assert r.status_code == 401

    def test_optimize_requires_auth(self, client, fresh_store):
        r = client.post("/api/geo/optimize", json={"text": "x"})
        assert r.status_code == 401
