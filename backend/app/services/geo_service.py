"""GEO 优化 (Generative Engine Optimization) — P1-3

策略(MVP):
- 评估一段文字的 GEO 友好度(0-100)
- 6 维特征:FAQ / 数据 / 来源 / 问题词 / 段落长度 / 概念定义
- 提供 AI 改写端点(让 LLM 重写为 GEO-friendly 版本)
- 返 checklist,告诉用户"哪里可以改进"

借鉴: Writesonic 2025 pivot / Focus GEO / AIWriteX 的 GEO 模块
"""
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger("geo_service")


# ============ 6 维特征 ============

GEO_DIMENSIONS = [
    "faq_structure",      # 含 Q&A 段落
    "specific_data",      # 含具体数字
    "source_citation",    # 含来源/链接
    "question_words",     # 段首/标题含问题词
    "paragraph_length",   # 段落长度适配(单段 < 200 字)
    "concept_definition", # 概念有明确定义
]


# 问题词(中文 + 英文)
_QUESTION_WORDS = ("什么是", "怎么", "如何", "为什么", "哪", "什么", "如何", "为何",
                  "how", "what", "why", "when", "where", "which", "who")

# FAQ 段标识
_FAQ_HEADERS = ("faq", "常见问题", "问答", "q&a", "qa:", "f.a.q")

# 链接 regex
_LINK_RE = re.compile(r"https?://[^\s)）]+", re.IGNORECASE)


# ============ 6 维评分 ============
GEO_DIMENSIONS_HELPER_TEXT: Dict[str, str] = {
    "faq_structure": "在文末加 FAQ 段: 列 3-5 个'什么是 X?' / '怎么 Y?' + 短答",
    "specific_data": "加具体数字: 年份(2024 年)、百分比(增长 30%)、金额(1.2 万亿)",
    "source_citation": "加 1-3 个权威链接 + '据 X 报告' / '来源: Y'",
    "question_words": "段首用问题词: 什么是 / 怎么 / 为什么 / 哪个",
    "paragraph_length": "单段 ≤ 200 字(AI 搜索结果常截短段)",
    "concept_definition": "关键概念用'X 是 Y'或'X 指 Y'句式明确定义",
}

def _score_faq_structure(text: str) -> Tuple[int, str]:
    """FAQ 段结构: 含 'FAQ:' / '常见问题' 等 + Q&A 短答"""
    score = 0
    notes = []
    lower = text.lower()
    has_faq_header = any(h in lower for h in _FAQ_HEADERS)
    # 宽松 Q&A 检测: 有 ? 问号行 + 有回答(行尾不是 ? 也不是空)
    qa_pairs = 0
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            continue
        if s.endswith(("?", "？")) and 5 <= len(s) <= 100:
            qa_pairs += 1
    if has_faq_header:
        score += 50
        notes.append("含 FAQ 段标题(AI 搜索友好)")
    if qa_pairs >= 2:
        score += 50
        notes.append(f"含 {qa_pairs} 个问答对(便于 AI 提取)")
    elif qa_pairs >= 1:
        score += 30
        notes.append(f"{qa_pairs} 个问题(可加 FAQ 段)")
    if not notes:
        notes.append("缺 FAQ 段: 加 'FAQ:' 或 '常见问题' 段, 列 3-5 个问答")
    return min(score, 100), "; ".join(notes)


def _score_specific_data(text: str) -> Tuple[int, str]:
    """含具体数字(年/月/百分比/金额)"""
    score = 0
    notes = []
    has_year = bool(re.search(r"\b(19|20)\d{2}\s*年", text))
    has_pct = bool(re.search(r"\d+(?:\.\d+)?\s*%", text))
    has_amount = bool(re.search(r"\d+(?:\.\d+)?\s*(亿|万|千|百|元|块|￥|\$|块)", text))
    has_any_number = bool(re.search(r"\d+", text))
    if has_year:
        score += 40
        notes.append("含年份(具体时间锚点)")
    if has_pct:
        score += 40
        notes.append("含百分比(可量化)")
    if has_amount:
        score += 40
        notes.append("含金额/单位(具体规模)")
    if has_any_number and score == 0:
        score += 10
        notes.append("有数字但缺少时间/百分比/单位")
    if score == 0:
        notes.append("缺具体数字: 加年份、百分比、金额等可量化指标")
    return min(score, 100), "; ".join(notes)


def _score_source_citation(text: str) -> Tuple[int, str]:
    """含 http(s) 链接 / 来源 / 数据出处"""
    score = 0
    notes = []
    links = _LINK_RE.findall(text)
    has_source_word = bool(re.search(r"(来源|出处|引用|据[一-鿿 ]|according to|source:|reference:)", text, re.IGNORECASE))
    if len(links) >= 2:
        score += 60
        notes.append(f"含 {len(links)} 个链接(可信度好)")
    elif len(links) == 1:
        score += 40
        notes.append("含 1 个链接(可加更多)")
    if has_source_word:
        score += 40
        notes.append("含'来源'/'据'等引用词")
    if not links and not has_source_word:
        notes.append("缺来源: 加 1-3 个权威链接 + 引用'据 X 报告'")
    return min(score, 100), "; ".join(notes)


def _score_question_words(text: str) -> Tuple[int, str]:
    """标题 / 段首含问题词(什么/怎么/为什么)"""
    score = 0
    notes = []
    # 段首(line 开头,或全角问号 ?)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    question_line_count = 0
    for line in lines[:10]:  # 前 10 行
        if line.endswith(("?", "？")) or any(line.startswith(qw) for qw in _QUESTION_WORDS):
            question_line_count += 1
    if question_line_count >= 2:
        score = 100
        notes.append(f"{question_line_count} 行问题(AI 提取友好)")
    elif question_line_count >= 1:
        score = 100
        notes.append(f"{question_line_count} 行问题(AI 提取友好)")
    else:
        notes.append("缺问题词开头: '什么是 X?' / '怎么 Y?' / '为什么 Z?'")
    return score, "; ".join(notes)


def _score_paragraph_length(text: str) -> Tuple[int, str]:
    """段落长度适配 — 单段 < 200 字易被 AI 截取"""
    # 按双换行或单换行分段(宽松)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n|\n", text) if p.strip()]
    if not paragraphs:
        return 0, "无段落(空)"
    # 评分: 短段落比例(容差放到 ≤ 250 字符)
    short_count = sum(1 for p in paragraphs if len(p) <= 250)
    ratio = short_count / len(paragraphs)
    if ratio >= 0.7:
        score = 100
        notes = f"{short_count}/{len(paragraphs)} 段 ≤ 250 字(完美)"
    elif ratio >= 0.4:
        score = 75
        notes = f"{short_count}/{len(paragraphs)} 段 ≤ 250 字(可拆段)"
    else:
        score = 40
        notes = f"只 {short_count}/{len(paragraphs)} 段短(段太长 AI 难截取)"
    return score, notes


def _score_concept_definition(text: str) -> Tuple[int, str]:
    """概念定义: 'X 是 Y' / 'X 指 Y' / 'X means Y'"""
    score = 0
    notes = []
    # 限制: 匹配 "X 是 Y" 时, X 是 2-12 个汉字,后面跟"是/为/指/等于",Y 是 2+ 汉字
    # 找不重叠的匹配(从左到右贪心)
    pattern = re.compile(r"([一-鿿]{2,12})\s*(?:是|为|指|等于)\s*([一-鿿]{2,30})")
    matches = []
    last_end = 0
    for m in pattern.finditer(text):
        if m.start() >= last_end:
            matches.append(m.group(0))
            last_end = m.end()
    definitions = len(matches)
    if definitions >= 2:
        score = 100
        notes = f"{definitions} 处概念定义(清晰)"
    elif definitions >= 1:
        score = 80
        notes = f"{definitions} 处定义(可加更多)"
    else:
        notes = "缺概念定义: 用 'X 是 Y' 或 'X 指 Y' 句式定义关键概念"
    return score, notes


# ============ 主评分 ============

def score_geo_friendliness(text: str, return_breakdown: bool = False):
    """评 0-100 分(6 维各占约 16.7 分)。

    return_breakdown=True → 返 {score, dimensions: {dim: {score, tip}}}
    """
    if not text or not text.strip():
        if return_breakdown:
            return {"score": 0, "dimensions": {}}
        return 0

    scorers = {
        "faq_structure": _score_faq_structure,
        "specific_data": _score_specific_data,
        "source_citation": _score_source_citation,
        "question_words": _score_question_words,
        "paragraph_length": _score_paragraph_length,
        "concept_definition": _score_concept_definition,
    }
    dimensions: Dict[str, Dict[str, Any]] = {}
    total = 0
    for name, scorer in scorers.items():
        s, tip = scorer(text)
        dimensions[name] = {"score": s, "tip": tip}
        total += s
    final = int(total / len(scorers))  # 平均到 0-100

    if return_breakdown:
        return {"score": final, "dimensions": dimensions}
    return final


def build_geo_checklist(text: str) -> Dict[str, Dict[str, Any]]:
    """返各维 score + tip dict(供前端渲染 checklist UI)。"""
    result = score_geo_friendliness(text, return_breakdown=True)
    return result["dimensions"]


# 默认空 checklist (给 /api/geo/checklist 用)
DEFAULT_CHECKLIST: Dict[str, Dict[str, Any]] = {
    name: {"score": 0, "tip": GEO_DIMENSIONS_HELPER_TEXT.get(name, "")}
    for name in GEO_DIMENSIONS
}


__all__ = [
    "GEO_DIMENSIONS",
    "DEFAULT_CHECKLIST",
    "score_geo_friendliness",
    "build_geo_checklist",
]
