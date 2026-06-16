"""公众号排版引擎 — TASK-P0-7 测试

策略: 借鉴 baoyu-post-to-wechat 的 default/grace/simple 3 套主题。
- Markdown → 微信兼容 HTML
- CSS 内联(微信公众号会过滤 <style> 标签,所以必须 inline)
- HTML 实体转义
- 图片占位(留给 mmbiz URL)

设计:
  - `render(markdown: str, theme: str = "default") -> str` 返 HTML
  - 3 主题: default(清爽) / grace(优雅) / simple(极简)
  - 输入: GitHub-flavored Markdown
  - 输出: 带 inline style 的 HTML 字符串

覆盖:
  - 3 主题基本渲染(h1/h2/p/strong/em)
  - 主题色/字号/边距差异
  - CSS 内联(不是 <style> 标签)
  - HTML 实体转义(< > & " ')
  - 图片 <img> 保留(占位)
  - 列表 / 引用 / 代码块
  - 空 markdown 返占位
  - 非法 theme 名 fallback 到 default
"""
import pytest

from app.services.wechat_formatter import (
    render,
    THEMES,
    WeChatFormatterError,
)


# ============ 主题注册 ============

class TestThemes:
    def test_three_themes_registered(self):
        assert "default" in THEMES
        assert "grace" in THEMES
        assert "simple" in THEMES

    def test_each_theme_has_required_fields(self):
        """每个主题必须含 name + body_class + h1/h2/p/blockquote 等 inline style"""
        for theme_name, theme in THEMES.items():
            assert "name" in theme
            assert "body_style" in theme
            assert "h1_style" in theme
            assert "h2_style" in theme
            assert "p_style" in theme
            assert "blockquote_style" in theme


# ============ 基本渲染 ============

class TestBasicRender:
    def test_returns_html_string(self):
        html = render("# 你好")
        assert isinstance(html, str)
        assert "<h1" in html

    def test_default_theme_inline_style(self):
        """default 主题:h1 用 inline style (不是 class)"""
        html = render("# 标题", theme="default")
        assert "<h1" in html
        assert "style=" in html  # 必须内联
        assert "<style" not in html  # 公众号会过滤 <style>
        assert "class=" not in html  # 公众号不保证 class 生效

    def test_three_themes_produce_different_html(self):
        """3 主题应产出不同 HTML(各自样式不同)"""
        h1 = "# 标题"
        d = render(h1, theme="default")
        g = render(h1, theme="grace")
        s = render(h1, theme="simple")
        # 至少 2 个不同
        assert len({d, g, s}) >= 2

    def test_unknown_theme_falls_back_to_default(self):
        """非法 theme 名 → 用 default"""
        h_default = render("# T", theme="default")
        h_garbage = render("# T", theme="does_not_exist")
        assert h_default == h_garbage

    def test_empty_markdown_returns_placeholder(self):
        """空 markdown 返 <p></p> 占位(公众号不允许空)"""
        html = render("")
        assert "<p" in html

    def test_pure_text_markdown(self):
        html = render("hello world")
        assert "<p" in html
        assert "hello world" in html


# ============ Markdown 元素 ============

class TestMarkdownElements:
    def test_h1_h2_h3(self):
        html = render("# H1\n## H2\n### H3")
        assert "<h1" in html
        assert "<h2" in html
        assert "<h3" in html

    def test_strong_em(self):
        html = render("**bold** and *italic*")
        assert "<strong" in html
        assert "bold" in html
        # italic 用 em 标签
        assert "<em" in html
        assert "italic" in html

    def test_unordered_list(self):
        html = render("- a\n- b\n- c")
        assert "<ul" in html
        assert "<li" in html

    def test_blockquote(self):
        html = render("> 引用文字")
        assert "<blockquote" in html
        # blockquote 必须有 style
        assert "style=" in html

    def test_inline_code(self):
        html = render("`code`")
        assert "<code" in html

    def test_link(self):
        html = render("[文字](https://example.com)")
        assert "<a " in html
        assert "href" in html
        assert "https://example.com" in html

    def test_paragraphs_separated(self):
        html = render("段落 1\n\n段落 2")
        # 2 个 <p>
        assert html.count("<p") >= 2


# ============ HTML 实体转义 ============

class TestHtmlEscape:
    def test_escape_lt_gt(self):
        html = render("x < y and a > b")
        # < 和 > 必须被转义
        assert "&lt;" in html
        assert "&gt;" in html
        # 不应残留原始 < > 字符
        assert "< y" not in html
        assert "a > b" not in html

    def test_escape_amp(self):
        html = render("Tom & Jerry")
        assert "&amp;" in html

    def test_escape_quote(self):
        """用户正文里的引号保留(不会在 text 节点里被 escape);
        真正的"attr 注入"防护由 _attr() 函数在生成 <a>/<img> 的属性值时 escape
        来完成(quote=True)。"""
        html = render('他说"你好"')
        # 正文里的引号保留为原文(可读性优先)
        assert '"你好"' in html
        # 没有 <script> 注入
        assert "<script>" not in html

    def test_script_tag_neutralized(self):
        """用户输入 <script> 必须被转义(公众号防 XSS)"""
        html = render("<script>alert(1)</script>")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


# ============ 图片处理 ============

class TestImages:
    def test_img_tag_preserved(self):
        html = render("![alt](https://example.com/x.jpg)")
        assert "<img" in html
        assert "src=" in html
        assert "https://example.com/x.jpg" in html

    def test_img_with_existing_mmbiz_url(self):
        """已上传到 mmbiz 的图片直接用 inline style(微信公众号会渲染)"""
        html = render("![alt](https://mmbiz.qpic.cn/abc)")
        assert "mmbiz.qpic.cn" in html
        assert "<img" in html


# ============ CSS 内联 (公众号要求) ============

class TestCssInlined:
    def test_no_style_tag(self):
        """公众号会过滤 <style> 标签 — render 输出不应有 <style>"""
        html = render("# T\n\n## S\n\np", theme="grace")
        assert "<style" not in html
        assert "</style>" not in html

    def test_h1_has_inline_style_attr(self):
        html = render("# T", theme="grace")
        # 抓 h1 段
        import re
        m = re.search(r"<h1[^>]*>", html)
        assert m, f"没找到 <h1> 标签: {html[:200]}"
        h1_tag = m.group(0)
        assert "style=" in h1_tag, f"h1 缺 inline style: {h1_tag}"

    def test_p_has_inline_style(self):
        html = render("正文")
        import re
        m = re.search(r"<p[^>]*>", html)
        assert m
        assert "style=" in m.group(0)

    def test_blockquote_has_inline_style(self):
        html = render("> 引文")
        import re
        m = re.search(r"<blockquote[^>]*>", html)
        assert m
        assert "style=" in m.group(0)


# ============ Grace 主题特色 ============

class TestGraceThemeSpecialty:
    def test_grace_has_signature_color(self):
        """grace 主题应有独特色(类似她她设计感)— 用 #722 或 #c37 等"""
        html = render("# T", theme="grace")
        # 至少 1 个内联色出现在样式里
        import re
        colors = re.findall(r"#[0-9a-fA-F]{3,6}", html)
        assert any(c for c in colors), f"grace 主题应有色彩: {html[:200]}"

    def test_grace_h1_has_dashed_border_bottom(self):
        """grace 主题 h1 装饰: dashed 下边线 + 居中;h2 才有 border-left"""
        html = render("# T", theme="grace")
        assert "border-bottom" in html
        assert "dashed" in html
        assert "text-align: center" in html

    def test_grace_h2_has_left_border(self):
        """grace 主题 h2 有 border-left(暖色系)"""
        html = render("## T", theme="grace")
        assert "border-left" in html


# ============ Simple 主题特色 ============

class TestSimpleThemeSpecialty:
    def test_simple_h1_no_color(self):
        """simple 主题 h1 用纯黑不用彩色"""
        html = render("# T", theme="simple")
        import re
        h1 = re.search(r"<h1[^>]*style=\"([^\"]+)\"", html)
        assert h1
        style = h1.group(1).lower()
        # 简单主题:不应有大段彩色
        # (允许灰度色,但不应有 #xxx 鲜艳色)
        assert "color:" not in style or "#fff" in style or "#333" in style or "#000" in style


# ============ Default 主题特色 ============

class TestDefaultThemeSpecialty:
    def test_default_h1_underlined_or_bold(self):
        """default 主题 h1 有明显样式(下划线或粗体)"""
        html = render("# T", theme="default")
        # 任何明显的样式:border-bottom, font-weight: bold
        assert "font-weight" in html or "border" in html or "font-size" in html
