"""公众号 Markdown → 微信兼容 HTML 排版引擎 — P0-7

借鉴 baoyu-post-to-wechat 的 default/grace/simple 3 套主题。
公众号会过滤 <style> 标签,所以**所有 CSS 必须 inline 在 style 属性**。
图片用 <img> 直接(外链会被公众号自动拉取;mmbiz 链接是首选)。

用法:
    from app.services.wechat_formatter import render
    html = render("# 标题\n\n正文", theme="grace")
"""
import html as html_lib
import logging
import re
from typing import Dict

log = logging.getLogger("wechat_formatter")


# ============ 3 套主题定义 ============
# 所有颜色/字号/边距 inline 到 style 属性。
# 公众号不解析 <style> 标签,也不保证 class 生效 — 全部 inline。

THEMES: Dict[str, Dict[str, str]] = {
    "default": {
        "name": "清爽",
        "body_style": (
            "font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', "
            "'Hiragino Sans GB', 'Microsoft YaHei', sans-serif; "
            "font-size: 16px; line-height: 1.75; "
            "color: #333; max-width: 100%; "
            "padding: 16px 4px; margin: 0; word-wrap: break-word;"
        ),
        "h1_style": (
            "font-size: 22px; font-weight: 600; "
            "color: #1a1a1a; margin: 28px 0 16px; "
            "padding: 0 0 8px; border-bottom: 2px solid #1a1a1a;"
        ),
        "h2_style": (
            "font-size: 19px; font-weight: 600; "
            "color: #1a1a1a; margin: 24px 0 12px; "
            "padding-left: 10px; border-left: 3px solid #1a1a1a;"
        ),
        "h3_style": (
            "font-size: 17px; font-weight: 600; "
            "color: #333; margin: 20px 0 10px;"
        ),
        "p_style": (
            "margin: 12px 0; color: #333; font-size: 16px; line-height: 1.75;"
        ),
        "strong_style": "color: #1a1a1a; font-weight: 600;",
        "em_style": "color: #555;",
        "a_style": "color: #1e6bb8; text-decoration: none;",
        "blockquote_style": (
            "border-left: 4px solid #ddd; padding: 10px 16px; "
            "margin: 16px 0; color: #666; "
            "background: #f7f7f7; "
            "border-radius: 4px;"
        ),
        "code_style": (
            "background: #f4f4f4; padding: 2px 6px; "
            "border-radius: 3px; font-family: Consolas, monospace; "
            "font-size: 14px; color: #c7254e;"
        ),
        "ul_style": "margin: 12px 0; padding-left: 28px;",
        "li_style": "margin: 4px 0; line-height: 1.75;",
        "img_style": (
            "max-width: 100%; height: auto; "
            "display: block; margin: 16px auto; "
            "border-radius: 6px;"
        ),
    },
    "grace": {
        # 优雅主题: 暖色调 + 装饰
        "name": "优雅",
        "body_style": (
            "font-family: 'Source Han Serif SC', 'Noto Serif CJK SC', "
            "Georgia, serif; font-size: 16px; line-height: 1.85; "
            "color: #4a4a4a; max-width: 100%; "
            "padding: 20px 8px; margin: 0; word-wrap: break-word; "
            "background: #fdfbf7;"
        ),
        "h1_style": (
            "font-size: 24px; font-weight: 500; "
            "color: #722; margin: 32px 0 18px; "
            "padding: 0 0 12px; border-bottom: 1px dashed #c37; "
            "text-align: center;"
        ),
        "h2_style": (
            "font-size: 20px; font-weight: 500; "
            "color: #722; margin: 26px 0 14px; "
            "padding-left: 14px; border-left: 4px solid #c37; "
            "background: linear-gradient(to right, #f9f2ed, transparent);"
        ),
        "h3_style": (
            "font-size: 18px; font-weight: 500; "
            "color: #844; margin: 20px 0 10px;"
        ),
        "p_style": (
            "margin: 14px 0; color: #4a4a4a; font-size: 16px; line-height: 1.85;"
        ),
        "strong_style": "color: #722; font-weight: 600;",
        "em_style": "color: #955;",
        "a_style": "color: #a35; text-decoration: none; border-bottom: 1px solid #cba;",
        "blockquote_style": (
            "border-left: 4px solid #c37; padding: 12px 18px; "
            "margin: 18px 0; color: #6a4a4a; "
            "background: #fbf3ec; "
            "border-radius: 6px; font-style: italic;"
        ),
        "code_style": (
            "background: #fbf3ec; padding: 2px 6px; "
            "border-radius: 3px; font-family: Consolas, monospace; "
            "font-size: 14px; color: #a35;"
        ),
        "ul_style": "margin: 14px 0; padding-left: 30px;",
        "li_style": "margin: 6px 0; line-height: 1.85;",
        "img_style": (
            "max-width: 100%; height: auto; "
            "display: block; margin: 20px auto; "
            "border-radius: 8px; box-shadow: 0 4px 12px rgba(180,120,100,0.15);"
        ),
    },
    "simple": {
        # 极简: 黑白灰
        "name": "极简",
        "body_style": (
            "font-family: -apple-system, BlinkMacSystemFont, sans-serif; "
            "font-size: 15px; line-height: 1.7; "
            "color: #333; max-width: 100%; "
            "padding: 12px 0; margin: 0; word-wrap: break-word;"
        ),
        "h1_style": (
            "font-size: 20px; font-weight: 700; "
            "color: #000; margin: 24px 0 14px; padding: 0;"
        ),
        "h2_style": (
            "font-size: 17px; font-weight: 700; "
            "color: #000; margin: 20px 0 10px; padding: 0;"
        ),
        "h3_style": (
            "font-size: 16px; font-weight: 600; "
            "color: #222; margin: 16px 0 8px;"
        ),
        "p_style": (
            "margin: 10px 0; color: #333; font-size: 15px; line-height: 1.7;"
        ),
        "strong_style": "color: #000; font-weight: 700;",
        "em_style": "color: #555;",
        "a_style": "color: #000; text-decoration: underline;",
        "blockquote_style": (
            "border-left: 3px solid #ccc; padding: 8px 14px; "
            "margin: 14px 0; color: #555;"
        ),
        "code_style": (
            "background: #eee; padding: 2px 5px; "
            "border-radius: 2px; font-family: Consolas, monospace; "
            "font-size: 13px; color: #222;"
        ),
        "ul_style": "margin: 10px 0; padding-left: 24px;",
        "li_style": "margin: 3px 0; line-height: 1.7;",
        "img_style": (
            "max-width: 100%; height: auto; "
            "display: block; margin: 14px auto;"
        ),
    },
}


# ============ Markdown 解析(轻量自实现, 不依赖外部库) ============
# 用 regex 走 GFM 子集,够公众号 99% 用例。
# 不用 mistune/markdown 库: 公众号场景太简单,加依赖不值。

def _md_to_html(md: str, theme: Dict[str, str]) -> str:
    """把 markdown 转成 inline-style HTML 字符串。

    顺序: 块级元素先 → 块内 inline 元素后。
    """
    if not md or not md.strip():
        # 空: 返占位
        return f'<p style="{theme["p_style"]}">&nbsp;</p>'

    lines = md.split("\n")
    out: list[str] = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # 跳过空行
        if not line.strip():
            i += 1
            continue

        # 代码块 ``` ... ```
        if line.strip().startswith("```"):
            i += 1
            code_lines = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # 跳过闭合 ```
            code_text = html_lib.escape("\n".join(code_lines))
            out.append(
                f'<pre style="background:#f4f4f4; padding:12px; border-radius:4px; '
                f'overflow-x:auto; font-family:Consolas,monospace; font-size:14px; '
                f'color:#333; margin:14px 0;"><code>{code_text}</code></pre>'
            )
            continue

        # 标题
        m = re.match(r"^(#{1,3})\s+(.+)$", line)
        if m:
            level = len(m.group(1))
            text = _inline(m.group(2), theme)
            tag = f"h{level}"
            out.append(f'<{tag} style="{theme[f"h{level}_style"]}">{text}</{tag}>')
            i += 1
            continue

        # 引用块 > ...(连续)
        if line.lstrip().startswith(">"):
            quote_lines = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                quote_lines.append(re.sub(r"^>\s*", "", lines[i]))
                i += 1
            inner = _inline(" ".join(quote_lines), theme)
            out.append(
                f'<blockquote style="{theme["blockquote_style"]}">'
                f'<p style="{theme["p_style"]}; margin:0;">{inner}</p>'
                f'</blockquote>'
            )
            continue

        # 无序列表 - * + -
        if re.match(r"^[\s]*[-*+]\s+", line):
            items = []
            while i < len(lines) and re.match(r"^[\s]*[-*+]\s+", lines[i]):
                item_text = re.sub(r"^[\s]*[-*+]\s+", "", lines[i])
                items.append(_inline(item_text, theme))
                i += 1
            lis = "".join(
                f'<li style="{theme["li_style"]}">{it}</li>' for it in items
            )
            out.append(
                f'<ul style="{theme["ul_style"]}">{lis}</ul>'
            )
            continue

        # 普通段落(可跨多行直到空行/特殊行)
        para_lines = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and \
              not _is_block_start(lines[i]):
            para_lines.append(lines[i])
            i += 1
        para_text = " ".join(para_lines)
        out.append(f'<p style="{theme["p_style"]}">{_inline(para_text, theme)}</p>')

    return "".join(out)


def _is_block_start(line: str) -> bool:
    """判断是否是新的块级元素起点"""
    s = line.lstrip()
    if not s:
        return True
    if s.startswith(("#", ">", "```", "-", "*", "+")):
        return True
    return False


def _inline(text: str, theme: Dict[str, str]) -> str:
    """处理 inline 元素: 加粗、斜体、链接、图片、inline code。

    关键问题: 我们生成的 inline HTML 标签 <strong> <em> <a> <img> <code> 在第 6 步
    被 escape 会被转义掉(< 变 &lt;),导致标签失效。
    解决: 用 placeholder 保护已生成的标签,escape 后再还原。
    """
    # Sentinel: 用 6 字符的不可见 unicode 包裹, 不可能出现在用户输入里
    PH_OPEN = "\x01\x02\x03"
    PH_CLOSE = "\x03\x02\x01"
    placeholders: list[str] = []

    def _protect(html_fragment: str) -> str:
        """把生成的 HTML 片段用 placeholder 包起来。"""
        placeholders.append(html_fragment)
        return f"{PH_OPEN}{len(placeholders) - 1}{PH_CLOSE}"

    # 1. 图片必须先于链接(![..](..) 优先匹配)
    text = re.sub(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        lambda m: _protect(
            f'<img src="{_attr(m.group(2))}" alt="{_attr(m.group(1))}" '
            f'style="{theme["img_style"]}"/>'
        ),
        text,
    )

    # 2. 链接 [text](url)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: _protect(
            f'<a href="{_attr(m.group(2))}" '
            f'style="{theme["a_style"]}" target="_blank">{_inline_basic(m.group(1), theme)}</a>'
        ),
        text,
    )

    # 3. inline code `...`
    text = re.sub(
        r"`([^`]+)`",
        lambda m: _protect(
            f'<code style="{theme["code_style"]}">{html_lib.escape(m.group(1))}</code>'
        ),
        text,
    )

    # 4. 加粗 **...** 或 __...__
    text = re.sub(
        r"\*\*([^*]+)\*\*",
        lambda m: _protect(
            f'<strong style="{theme["strong_style"]}">{_inline_basic(m.group(1), theme)}</strong>'
        ),
        text,
    )
    text = re.sub(
        r"__([^_]+)__",
        lambda m: _protect(
            f'<strong style="{theme["strong_style"]}">{_inline_basic(m.group(1), theme)}</strong>'
        ),
        text,
    )

    # 5. 斜体 *...* 或 _..._(避免破坏加粗)
    text = re.sub(
        r"(?<!\*)\*([^*\n]+)\*(?!\*)",
        lambda m: _protect(
            f'<em style="{theme["em_style"]}">{_inline_basic(m.group(1), theme)}</em>'
        ),
        text,
    )
    text = re.sub(
        r"(?<!_)_([^_\n]+)_(?!_)",
        lambda m: _protect(
            f'<em style="{theme["em_style"]}">{_inline_basic(m.group(1), theme)}</em>'
        ),
        text,
    )

    # 6. escape 剩余的"裸"用户文本(防 XSS),不会动 placeholder
    text = html_lib.escape(text, quote=False)

    # 7. 还原 placeholder
    def _restore(match: "re.Match") -> str:
        idx = int(match.group(1))
        return placeholders[idx]

    text = re.sub(
        rf"{re.escape(PH_OPEN)}(\d+){re.escape(PH_CLOSE)}",
        _restore,
        text,
    )
    return text


def _inline_basic(text: str, theme: Dict[str, str]) -> str:
    """_inline 的子集,用于 <a> 内部文本(不做 link/inline-code 替换避免递归)"""
    text = re.sub(
        r"\*\*([^*]+)\*\*",
        lambda m: f'<strong style="{theme["strong_style"]}">{m.group(1)}</strong>',
        text,
    )
    text = re.sub(
        r"(?<!\*)\*([^*\n]+)\*(?!\*)",
        lambda m: f'<em style="{theme["em_style"]}">{m.group(1)}</em>',
        text,
    )
    return html_lib.escape(text, quote=False)


def _attr(s: str) -> str:
    """HTML 属性值转义(< > & " ')"""
    return html_lib.escape(s, quote=True)


# ============ 主入口 ============

def render(markdown: str, theme: str = "default") -> str:
    """把 markdown 渲染为带 inline-CSS 的微信公众号 HTML。

    Args:
        markdown: GitHub-flavored markdown 文本(支持 # ## ### / **bold** / *italic* /
                [link](url) / ![img](url) / > quote / - list / ```code```)
        theme: 主题名 — "default" / "grace" / "simple",非法值 fallback 到 default

    Returns:
        str — 公众号可粘贴的 HTML(无 <style> 标签,所有 CSS inline)
    """
    if theme not in THEMES:
        log.debug("wechat_formatter: unknown theme %r, fallback to default", theme)
        theme = "default"
    t = THEMES[theme]
    return _md_to_html(markdown, t)


__all__ = ["render", "THEMES", "WeChatFormatterError"]


class WeChatFormatterError(Exception):
    """(预留) 未来若引入异步 / 资源加载时报此错"""
    pass
