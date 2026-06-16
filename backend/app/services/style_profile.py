"""去 AI 味 / 文风克隆 — P1-1

策略:
- 用户文风 = 历史文章聚合后的 StyleProfile
- 4 维特征:
  1. 句长分布(平均字/句)
  2. emoji 频率(emoji 数 / 总字数)
  3. 段首模式(最常用的开头 N 个短语)
  4. 高频词/口头禅(去停用词后的 top 关键词)
- AI 扩写/改写时,把 StyleProfile 转成"风格指令"塞进 system prompt
- 给已生成内容打"风格一致性评分" (0-100)

本模块纯函数,无外部依赖(避免 jieba 等慢启动)。
"""
import logging
import re
from collections import Counter
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

log = logging.getLogger("style_profile")


# ============ 数据结构 ============

@dataclass
class StyleProfile:
    """用户文风画像"""
    avg_sentence_len: float = 0.0       # 平均每句多少字
    emoji_rate: float = 0.0             # emoji 数 / 总字数
    opening_patterns: List[str] = field(default_factory=list)  # 最常用开头(2-4 字短语)
    vocab: Dict[str, int] = field(default_factory=dict)        # 高频词 → 次数(去停用词)
    sample_size: int = 0                # 用了多少篇文章算的


DEFAULT_EMPTY_PROFILE = StyleProfile()


# ============ 工具 ============

# 中文停用词(简化版,够用)
_STOPWORDS = {
    "的", "了", "是", "在", "和", "与", "或", "也", "都", "就", "还",
    "你", "我", "他", "她", "它", "我们", "你们", "他们", "的", "吗", "呢",
    "啊", "吧", "哦", "嗯", "嗯嗯", "哈", "哈哈", "是", "不是", "有", "没",
    "一个", "一些", "这个", "那个", "这样", "那样", "什么", "怎么", "为什么",
    "可以", "应该", "可能", "需要", "想要", "就是", "不是", "还是", "但是",
    "如果", "因为", "所以", "虽然", "但是", "然后", "现在", "之前", "之后",
    "今天", "昨天", "明天", "最近", "刚才", "以前", "将来",
    "https", "http", "www", "com", "cn", "html", "jpg", "png", "mp4",  # URL 片段
}

# emoji 检测 (含常见表情 + unicode ranges)
_EMOJI_RE = re.compile(
    r"[\U0001F300-\U0001F9FF"   # symbols & pictographs
    r"\U0001F600-\U0001F64F"      # emoticons
    r"\U0001F680-\U0001F6FF"      # transport & map
    r"☀-➿"              # misc symbols + dingbats
    r"\U0001F1E6-\U0001F1FF]"     # flags
)


def _split_sentences(text: str) -> List[str]:
    """粗略按 。！？ \n 分句"""
    parts = re.split(r"[。！？\n!?;]+", text)
    return [p.strip() for p in parts if p.strip() and len(p.strip()) > 1]


def _top_n_opening(sentences: List[str], n: int = 3) -> List[str]:
    """取最常用的开头 2-4 字短语"""
    opens = []
    for s in sentences[:30]:  # 只看前 30 句
        # 2-4 字开头
        for k in (2, 3, 4):
            if len(s) >= k:
                opens.append(s[:k])
                break
    if not opens:
        return []
    counter = Counter(opens)
    return [s for s, _ in counter.most_common(n)]


def _top_keywords(text: str, n: int = 10) -> Dict[str, int]:
    """取高频词,过滤停用词 + 短词(<2 字) + 纯标点"""
    counter = Counter()
    for word in re.findall(r"[一-鿿A-Za-z0-9]+", text):
        if len(word) < 2 or word in _STOPWORDS:
            continue
        counter[word] += 1
    return dict(counter.most_common(n))


# ============ 主入口 ============

def extract_profiles(corpus: List[str]) -> StyleProfile:
    """从用户历史文章提取 StyleProfile。

    corpus: 历史文章 body 列表(markdown / plain text 都可)
    """
    if not corpus:
        return DEFAULT_EMPTY_PROFILE

    all_text = "\n".join(corpus)
    sentences = _split_sentences(all_text)
    if not sentences:
        return DEFAULT_EMPTY_PROFILE

    # 1. 句长
    avg_len = sum(len(s) for s in sentences) / len(sentences)

    # 2. emoji 频率
    emoji_count = len(_EMOJI_RE.findall(all_text))
    emoji_rate = emoji_count / max(len(all_text), 1)

    # 3. 段首模式
    openings = _top_n_opening(sentences, n=3)

    # 4. 高频词
    vocab = _top_keywords(all_text, n=10)

    return StyleProfile(
        avg_sentence_len=round(avg_len, 1),
        emoji_rate=round(emoji_rate, 5),
        opening_patterns=openings,
        vocab=vocab,
        sample_size=len(corpus),
    )


def build_style_prompt(profile: StyleProfile) -> str:
    """把 StyleProfile 转成"风格指令"字符串(注入 system prompt 后缀)。

    强调: 这是 **指导**,不是 **强约束** — LLM 应该模仿风格,但不应僵硬到失去内容质量。
    """
    if profile.sample_size == 0:
        return ""  # 空文风:不注入

    lines: List[str] = []
    lines.append("【风格指南】")
    lines.append(f"基于用户 {profile.sample_size} 篇历史文章学习到以下写作风格,模仿它:")

    # 句长
    n = profile.avg_sentence_len
    if n > 0:
        if n < 15:
            lines.append(f"- 句长偏短(平均 {n} 字):多用短句、口语化、节奏感强")
        elif n < 40:
            lines.append(f"- 句长适中(平均 {n} 字):简洁清晰、避免冗长")
        else:
            lines.append(f"- 句长较长(平均 {n} 字):允许展开论述、深入分析")

    # emoji
    if profile.emoji_rate > 0.01:
        lines.append(f"- emoji 频繁(频率 {profile.emoji_rate:.3f}):适当使用 emoji 让表达更生动,建议每段 1-3 个")
    elif profile.emoji_rate > 0.003:
        lines.append(f"- emoji 偶尔(频率 {profile.emoji_rate:.3f}):关键位置点缀,不过度")
    else:
        lines.append(f"- 几乎不用 emoji(频率 {profile.emoji_rate:.5f}):保持文字克制,极简风")

    # 段首
    if profile.opening_patterns:
        examples = "、".join(profile.opening_patterns)
        lines.append(f"- 常见开头:「{examples}」等,可适当模仿(但不必每段都用)")

    # 高频词
    if profile.vocab:
        top_words = list(profile.vocab.keys())[:5]
        lines.append(f"- 高频词:「{'」、「'.join(top_words)}」等 — 这是用户的标志性用词")

    lines.append("")  # 空行
    lines.append("注意:风格模仿是软约束,内容质量优先。如果用户要求'专业'或'严肃'风格,放弃模仿。")

    return "\n".join(lines)


def score_text_against_profile(text: str, profile: StyleProfile) -> int:
    """给一段文字打"风格一致性评分" 0-100。

    评分维度:
      - 句长匹配 (40 分)
      - emoji 密度匹配 (30 分)
      - 段首模式匹配 (20 分)
      - 高频词命中 (10 分)
    """
    if not text or not text or profile.sample_size == 0:
        return 0

    score = 0

    # 1. 句长匹配 (40 分)
    sentences = _split_sentences(text)
    if sentences and profile.avg_sentence_len > 0:
        text_avg = sum(len(s) for s in sentences) / len(sentences)
        target = profile.avg_sentence_len
        # 距离越近分越高
        diff_ratio = abs(text_avg - target) / max(target, 1)
        if diff_ratio < 0.2:
            score += 40
        elif diff_ratio < 0.5:
            score += 28
        elif diff_ratio < 1.0:
            score += 15
        else:
            score += 5

    # 2. emoji 密度匹配 (30 分)
    if profile.emoji_rate > 0.001:
        text_emoji = len(_EMOJI_RE.findall(text)) / max(len(text), 1)
        target = profile.emoji_rate
        if target > 0.005:
            # 用户 emoji 密:文字有 emoji 给高分
            if text_emoji > 0.003:
                score += 30
            elif text_emoji > 0.001:
                score += 15
            else:
                score += 5
        else:
            # 用户几乎不用 emoji:文字无 emoji 给高分
            if text_emoji < 0.002:
                score += 30
            elif text_emoji < 0.005:
                score += 15
            else:
                score += 5

    # 3. 段首匹配 (20 分)
    if profile.opening_patterns:
        first_chars = text.lstrip()[:4]
        if any(op in text[:30] for op in profile.opening_patterns):
            score += 20
        elif first_chars and len(first_chars) >= 2:
            score += 8  # 用了某种开头但不是 top pattern

    # 4. 高频词命中 (10 分)
    if profile.vocab:
        text_lower = text
        hits = sum(1 for w in profile.vocab.keys() if w in text_lower)
        hit_rate = hits / max(len(profile.vocab), 1)
        if hit_rate > 0.3:
            score += 10
        elif hit_rate > 0.1:
            score += 6
        elif hits > 0:
            score += 3

    return min(score, 100)


def profile_to_dict(p: StyleProfile) -> Dict:
    """StyleProfile → dict (用于 API response / JSON 序列化)"""
    return asdict(p)


__all__ = [
    "StyleProfile",
    "DEFAULT_EMPTY_PROFILE",
    "extract_profiles",
    "build_style_prompt",
    "score_text_against_profile",
    "profile_to_dict",
]
