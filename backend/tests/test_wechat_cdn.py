"""wechat_cdn 工具模块单元测试 — P0-1 公众号图文混排"""
import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.wechat_cdn import (
    extract_img_urls,
    rewrite_html_with_cdn,
    download_image,
    get_inline_dir,
)
from app.platforms.wechat import WeChatUploadError


# ============ extract_img_urls ============

class TestExtractImgUrls:
    def test_no_img_returns_empty(self):
        assert extract_img_urls("<p>hello</p>") == []

    def test_single_img(self):
        html = '<p>x</p><img src="https://cdn.example.com/a.jpg" alt="x"/>'
        assert extract_img_urls(html) == ["https://cdn.example.com/a.jpg"]

    def test_multiple_imgs_preserves_order(self):
        html = (
            '<img src="https://a/1.png"/>'
            '<p>中间</p>'
            '<img src="https://b/2.jpg"/>'
            '<img src="https://c/3.gif"/>'
        )
        assert extract_img_urls(html) == [
            "https://a/1.png",
            "https://b/2.jpg",
            "https://c/3.gif",
        ]

    def test_dedupes_duplicate_srcs(self):
        html = '<img src="https://a/1.png"/><img src="https://a/1.png"/>'
        assert extract_img_urls(html) == ["https://a/1.png"]

    def test_skips_data_uris(self):
        html = (
            '<img src="data:image/png;base64,abcdef"/>'
            '<img src="https://a/1.png"/>'
        )
        assert extract_img_urls(html) == ["https://a/1.png"]

    def test_malformed_html_doesnt_crash(self):
        # BeautifulSoup with lxml is forgiving
        assert extract_img_urls("<<<broken>>>") == []

    def test_preserves_srcset_in_html(self):
        # rewrite 测试覆盖 srcset,我们只关心 src
        html = '<img src="https://a/1.jpg" srcset="https://a/1x 1x"/>'
        assert extract_img_urls(html) == ["https://a/1.jpg"]


# ============ rewrite_html_with_cdn ============

class TestRewriteHtmlWithCdn:
    def test_no_img_unchanged(self):
        html = "<p>no img</p>"
        assert rewrite_html_with_cdn(html, {}) == html

    def test_replaces_single_src(self):
        html = '<p>x</p><img src="https://orig/a.jpg"/>'
        out = rewrite_html_with_cdn(html, {"https://orig/a.jpg": "https://mmbiz.qpic.cn/abc"})
        assert 'src="https://mmbiz.qpic.cn/abc"' in out
        assert "orig/a.jpg" not in out

    def test_preserves_other_attributes(self):
        html = '<img src="https://a/1.jpg" alt="hello" class="pic" data-id="42"/>'
        out = rewrite_html_with_cdn(html, {"https://a/1.jpg": "https://mmbiz/x"})
        assert 'alt="hello"' in out
        assert 'class="pic"' in out
        assert 'data-id="42"' in out
        assert 'src="https://mmbiz/x"' in out

    def test_only_replaces_known_srcs(self):
        html = '<img src="https://known/a.jpg"/><img src="https://unknown/b.jpg"/>'
        out = rewrite_html_with_cdn(html, {"https://known/a.jpg": "https://mmbiz/x"})
        assert 'src="https://mmbiz/x"' in out
        # unknown src 保持原样
        assert 'src="https://unknown/b.jpg"' in out

    def test_handles_unmatched_html(self):
        # rewrite 不应该因为 HTML 不规整而崩
        # 用 close 的 img + 孤立 <p> 模拟现实破损
        html = '<p>broken<p><img src="https://a.jpg"/></p>'
        out = rewrite_html_with_cdn(html, {"https://a.jpg": "https://mmbiz/x"})
        assert 'src="https://mmbiz/x"' in out


# ============ download_image ============

class TestDownloadImage:
    def test_writes_to_dest_dir(self, tmp_path):
        """httpx stream 写入本地,返路径。"""
        from httpx import MockTransport, Response, AsyncClient

        async def run():
            transport = MockTransport(lambda req: Response(200, content=b"\x89PNG\r\n\x1a\n" + b"x" * 100,
                                                              headers={"content-type": "image/png"}))
            # patch httpx.AsyncClient 用我们的 transport
            real_init = AsyncClient.__init__

            def patched_init(self, *args, **kwargs):
                kwargs["transport"] = transport
                kwargs["timeout"] = 60.0
                real_init(self, *args, **kwargs)

            with patch.object(AsyncClient, "__init__", patched_init):
                return await download_image("https://x/a.png", tmp_path)

        path = asyncio.run(run())
        p = Path(path)
        assert p.exists()
        assert p.parent == tmp_path
        assert p.stat().st_size > 0
        assert p.suffix == ".png"

    def test_raises_on_non_2xx(self, tmp_path):
        from httpx import MockTransport, Response, AsyncClient

        async def run():
            transport = MockTransport(lambda req: Response(404, content=b"nope"))

            real_init = AsyncClient.__init__

            def patched_init(self, *args, **kwargs):
                kwargs["transport"] = transport
                kwargs["timeout"] = 60.0
                real_init(self, *args, **kwargs)

            with patch.object(AsyncClient, "__init__", patched_init):
                return await download_image("https://x/a.png", tmp_path)

        with pytest.raises(WeChatUploadError, match="404"):
            asyncio.run(run())

    def test_uses_jpg_extension_for_jpeg(self, tmp_path):
        from httpx import MockTransport, Response, AsyncClient

        async def run():
            transport = MockTransport(lambda req: Response(200, content=b"\xff\xd8\xff" + b"x" * 50,
                                                              headers={"content-type": "image/jpeg"}))
            real_init = AsyncClient.__init__

            def patched_init(self, *args, **kwargs):
                kwargs["transport"] = transport
                real_init(self, *args, **kwargs)

            with patch.object(AsyncClient, "__init__", patched_init):
                return await download_image("https://x/a", tmp_path)

        path = asyncio.run(run())
        assert Path(path).suffix == ".jpg"


# ============ get_inline_dir ============

class TestGetInlineDir:
    def test_returns_storage_path(self, tmp_path, monkeypatch):
        """STORAGE_DIR 由 monkeypatch 控制,get_inline_dir 应在 STORAGE_DIR/images/wechat_inline/ 下。"""
        from app.core import config
        monkeypatch.setattr(config.settings, "STORAGE_DIR", str(tmp_path))
        # 重新读 settings 因为 settings 是单例 — 但 settings 在 model_post_init 里派生目录
        # 所以这里直接验证最终路径
        d = get_inline_dir()
        assert d.exists()  # 应自动创建
        assert d.name == "wechat_inline"
        assert str(d).startswith(str(tmp_path))
