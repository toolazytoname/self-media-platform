"""WeChatAdapter 单元测试 — Phase 2 ext (公众号图文草稿箱)"""
import asyncio
import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from pathlib import Path

from app.platforms.wechat import (
    WeChatAdapter,
    WeChatUploadError,
    _TokenCache,
)


# ============ Token 缓存 ============

class TestTokenCache:
    def test_init_invalid(self):
        c = _TokenCache()
        assert c.is_valid() is False
        assert c.token is None

    def test_set_then_valid(self):
        c = _TokenCache()
        c.set("abc123", 7200)
        assert c.is_valid() is True
        assert c.token == "abc123"

    def test_expired(self):
        c = _TokenCache()
        c.set("abc", 1)  # 1 秒
        # 用 1s 缓冲:expires_at 实际是 time.time() + 1
        # 1 秒后还没"提前 60s 失效",所以 is_valid 返 False
        import time
        time.sleep(2)
        assert c.is_valid() is False


# ============ Adapter 构造 ============

class TestAdapterConstruction:
    def test_required_fields_missing_raises(self):
        """AppID / AppSecret 都缺 → publish_article 报 WeChatUploadError(在 _ensure_token 时)"""
        from app.store import store
        from app.core.config import settings
        # 清掉 env(用 monkeypatch 不行,直接改 .env 不行;用空 account 构造)
        with patch.object(settings, "WECHAT_APP_ID", None):
            with patch.object(settings, "WECHAT_APP_SECRET", None):
                a = WeChatAdapter({"platform": "wechat", "name": "t", "id": "x"})
                assert a.app_id is None
                assert a.app_secret is None
                # 调 _ensure_token 直接抛
                with pytest.raises(WeChatUploadError, match="AppID"):
                    asyncio.run(a._ensure_token())

    def test_adapter_picks_up_app_id(self):
        from app.core.config import settings
        with patch.object(settings, "WECHAT_APP_ID", "wx_global_id"):
            a = WeChatAdapter({"platform": "wechat", "name": "t", "id": "x"})
            assert a.app_id == "wx_global_id"

    def test_account_overrides_global(self):
        from app.core.config import settings
        with patch.object(settings, "WECHAT_APP_ID", "wx_global"):
            a = WeChatAdapter({
                "platform": "wechat", "name": "t", "id": "x",
                "app_id": "wx_account",
            })
            assert a.app_id == "wx_account"


# ============ HTTP mock helper ============

class FakeResponse:
    """httpx.Response 替代:dict 直接给 json(),status_code 给定"""
    def __init__(self, data, status_code=200):
        self.data = data
        self.status_code = status_code

    def json(self):
        return self.data


def _mock_httpx(method_to_response: dict):
    """返一个 callable,签名同 httpx.AsyncClient 内的 get/post/files 调用。

    method_to_response:  {"GET:/cgi-bin/token": {"access_token": "x", ...}, ...}
    """
    async def fake_get(self, url, params=None, **kwargs):
        key = f"GET:{Path(url).path}"
        return FakeResponse(method_to_response.get(key, {}))

    async def fake_post(self, url, params=None, json=None, files=None, **kwargs):
        key = f"POST:{Path(url).path}"
        return FakeResponse(method_to_response.get(key, {}))

    return fake_get, fake_post


# ============ publish_article 端到端 ============

class TestPublishArticle:
    def _adapter(self) -> WeChatAdapter:
        return WeChatAdapter({
            "platform": "wechat", "name": "test", "id": "acc_1",
            "app_id": "wx_test", "app_secret": "secret",
        })

    def test_token_then_draft_add(self, tmp_path):
        """token 获取 → 上传封面 → draft/add 全链路。"""
        cover = tmp_path / "cover.jpg"
        cover.write_bytes(b"\xff\xd8\xff\xe0fake-jpeg-bytes")

        responses = {
            "GET:/cgi-bin/token": {"access_token": "tok123", "expires_in": 7200},
            "POST:/cgi-bin/material/add_material": {"media_id": "media_img_001", "url": "http://x"},
            "POST:/cgi-bin/draft/add": {"media_id": "draft_001"},
        }
        get_fn, post_fn = _mock_httpx(responses)

        a = self._adapter()
        with patch.object(a, "_request_override", new=_override(responses)):
            result = asyncio.run(a.publish_article(
                title="测试文章",
                content="<p>正文</p>",
                cover_image=str(cover),
            ))

        assert result["platform_publish_id"] == "draft_001"
        assert result["status"] == "draft_added"
        assert result["thumb_media_id"] == "media_img_001"

    def test_no_cover_uses_text_type(self, tmp_path):
        """没传封面时,只 draft/add 不上传图片。"""
        responses = {
            "GET:/cgi-bin/token": {"access_token": "tok123", "expires_in": 7200},
            "POST:/cgi-bin/draft/add": {"media_id": "draft_002"},
        }
        a = self._adapter()
        with patch.object(a, "_request_override", new=_override(responses)):
            result = asyncio.run(a.publish_article(
                title="纯文字",
                content="<p>无图文章</p>",
            ))

        assert result["platform_publish_id"] == "draft_002"
        assert result["thumb_media_id"] == ""

    def test_draft_add_error_raises(self, tmp_path):
        """draft/add 返 errcode != 0 → 抛 WeChatUploadError。"""
        responses = {
            "GET:/cgi-bin/token": {"access_token": "tok", "expires_in": 7200},
            "POST:/cgi-bin/draft/add": {"errcode": 40001, "errmsg": "invalid credential"},
        }
        a = self._adapter()
        with patch.object(a, "_request_override", new=_override(responses)):
            with pytest.raises(WeChatUploadError, match="40001"):
                asyncio.run(a.publish_article(
                    title="x", content="<p>y</p>",
                ))

    def test_token_caches(self, tmp_path):
        """连续两次 publish 第二次不会重新拿 token。"""
        call_count = {"token": 0, "draft": 0}
        async def override(method, url, **kw):
            if "token" in url:
                call_count["token"] += 1
                return {"access_token": "tok", "expires_in": 7200}
            else:
                call_count["draft"] += 1
                return {"media_id": f"draft_{call_count['draft']}"}
        a = self._adapter()
        with patch.object(a, "_request_override", new=override):
            asyncio.run(a.publish_article("t1", "c1"))
            asyncio.run(a.publish_article("t2", "c2"))
        # token 只调 1 次(token 缓存),draft 调 2 次
        assert call_count["token"] == 1
        assert call_count["draft"] == 2

    def test_title_too_long_raises(self):
        a = self._adapter()
        with patch.object(a, "_request_override", new=_override({})):
            with pytest.raises(WeChatUploadError, match="1-64"):
                asyncio.run(a.publish_article(title="x" * 100, content="<p>y</p>"))

    def test_empty_content_raises(self):
        a = self._adapter()
        with patch.object(a, "_request_override", new=_override({})):
            with pytest.raises(WeChatUploadError, match="content"):
                asyncio.run(a.publish_article(title="x", content=""))

    def test_cover_not_found_raises(self):
        a = self._adapter()
        # 无 override:走真的 _api_post,但 cover check 在 _api_post 之前抛
        with pytest.raises(WeChatUploadError, match="封面图不存在"):
            asyncio.run(a.publish_article(title="x", content="<p>y</p>", cover_image="/nonexistent.jpg"))

    def test_token_endpoint_error_raises(self):
        """token 端点返 errcode != 0 → 抛错(没 cache 可用)。"""
        async def override(method, url, **kw):
            if "token" in url:
                return {"errcode": 40013, "errmsg": "invalid appid"}
            return {}
        a = self._adapter()
        with patch.object(a, "_request_override", new=override):
            with pytest.raises(WeChatUploadError, match="40013"):
                asyncio.run(a.publish_article(title="x", content="<p>y</p>"))


# ============ refresh_token / get_publish_status ============

class TestLifecycle:
    def test_refresh_token_forces_new(self):
        a = WeChatAdapter({"platform": "wechat", "name": "t", "app_id": "wx", "app_secret": "s"})
        # 预填一个"假" token
        a._token.set("old_token", 7200)
        responses = {
            "GET:/cgi-bin/token": {"access_token": "new_token", "expires_in": 7200},
        }
        with patch.object(a, "_request_override", new=_override(responses)):
            result = asyncio.run(a.refresh_token())
        assert result["status"] == "ok"
        assert a._token.token == "new_token"

    def test_get_publish_status_returns_published(self):
        # 公众号"草稿已写入"即视为 published (草稿是否最终发布由用户手动操作)
        a = WeChatAdapter({"platform": "wechat", "name": "t"})
        result = asyncio.run(a.get_publish_status("any_draft_id"))
        from app.platforms.base import PublishStatus
        assert result == PublishStatus.PUBLISHED


# ============ abstract method check ============

class TestNotImplemented:
    def test_upload_video_raises(self):
        a = WeChatAdapter({"platform": "wechat", "name": "t"})
        with pytest.raises(NotImplementedError, match="仅支持图文"):
            asyncio.run(a.upload_video(
                video_path="/tmp/x.mp4", title="x", description="",
                tags=[], thumbnail_path=None,
            ))


# ============ P0-1: 上传正文图片 (uploadimg) ============

class TestUploadInlineImage:
    """POST /cgi-bin/media/uploadimg → mmbiz.qpic.cn URL"""

    def _adapter(self) -> WeChatAdapter:
        return WeChatAdapter({
            "platform": "wechat", "name": "test", "id": "acc_1",
            "app_id": "wx_test", "app_secret": "secret",
        })

    def test_returns_mmbiz_url(self, tmp_path):
        img = tmp_path / "inline.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0fake-jpeg")
        responses = {
            "GET:/cgi-bin/token": {"access_token": "tok", "expires_in": 7200},
            "POST:/cgi-bin/media/uploadimg": {
                "url": "https://mmbiz.qpic.cn/mmbiz_png/abc/0?wx_fmt=png",
            },
        }
        a = self._adapter()
        with patch.object(a, "_request_override", new=_override(responses)):
            url = asyncio.run(a._upload_inline_image(str(img)))
        assert url == "https://mmbiz.qpic.cn/mmbiz_png/abc/0?wx_fmt=png"

    def test_error_code_raises(self, tmp_path):
        img = tmp_path / "inline.jpg"
        img.write_bytes(b"x")
        responses = {
            "GET:/cgi-bin/token": {"access_token": "tok", "expires_in": 7200},
            "POST:/cgi-bin/media/uploadimg": {"errcode": 45001, "errmsg": "media size out of limit"},
        }
        a = self._adapter()
        with patch.object(a, "_request_override", new=_override(responses)):
            with pytest.raises(WeChatUploadError, match="45001"):
                asyncio.run(a._upload_inline_image(str(img)))


# ============ P0-1: freepublish/submit ============

class TestSubmitForPublish:
    """POST /cgi-bin/freepublish/submit → publish_id"""

    def _adapter(self) -> WeChatAdapter:
        return WeChatAdapter({
            "platform": "wechat", "name": "test", "id": "acc_1",
            "app_id": "wx_test", "app_secret": "secret",
        })

    def test_returns_publish_id(self):
        responses = {
            "GET:/cgi-bin/token": {"access_token": "tok", "expires_in": 7200},
            "POST:/cgi-bin/freepublish/submit": {"publish_id": "1000000001"},
        }
        a = self._adapter()
        with patch.object(a, "_request_override", new=_override(responses)):
            pid = asyncio.run(a.submit_for_publish("draft_abc"))
        assert pid == "1000000001"

    def test_error_code_raises(self):
        responses = {
            "GET:/cgi-bin/token": {"access_token": "tok", "expires_in": 7200},
            "POST:/cgi-bin/freepublish/submit": {"errcode": 58000, "errmsg": "freepublish API not enabled"},
        }
        a = self._adapter()
        with patch.object(a, "_request_override", new=_override(responses)):
            with pytest.raises(WeChatUploadError, match="58000"):
                asyncio.run(a.submit_for_publish("draft_abc"))


# ============ P0-1: freepublish/get (轮询) ============

class TestQueryPublishStatus:
    """POST /cgi-bin/freepublish/get → publish_status + article_url"""

    def _adapter(self) -> WeChatAdapter:
        return WeChatAdapter({
            "platform": "wechat", "name": "test", "id": "acc_1",
            "app_id": "wx_test", "app_secret": "secret",
        })

    def test_status_zero_success(self):
        responses = {
            "GET:/cgi-bin/token": {"access_token": "tok", "expires_in": 7200},
            "POST:/cgi-bin/freepublish/get": {
                "publish_id": "1000000001",
                "publish_status": 0,  # 成功
                "article_url": "https://mp.weixin.qq.com/s?__biz=MzA&mid=1&idx=1",
            },
        }
        a = self._adapter()
        with patch.object(a, "_request_override", new=_override(responses)):
            res = asyncio.run(a.query_publish_status("1000000001"))
        assert res["publish_status"] == 0
        assert "mp.weixin.qq.com/s" in res["article_url"]

    def test_status_four_failure(self):
        responses = {
            "GET:/cgi-bin/token": {"access_token": "tok", "expires_in": 7200},
            "POST:/cgi-bin/freepublish/get": {
                "publish_id": "1000000001",
                "publish_status": 4,
                "fail_idx": [12345678, 12345679],
            },
        }
        a = self._adapter()
        with patch.object(a, "_request_override", new=_override(responses)):
            res = asyncio.run(a.query_publish_status("1000000001"))
        assert res["publish_status"] == 4
        assert res.get("article_url") is None


# ============ P0-1: publish_article_full_auto 端到端 ============

class TestPublishArticleFullAuto:
    """全流程: token → uploadimg(×N) → material/add → draft/add → freepublish/submit → freepublish/get 轮询"""

    def _adapter(self) -> WeChatAdapter:
        return WeChatAdapter({
            "platform": "wechat", "name": "test", "id": "acc_1",
            "app_id": "wx_test", "app_secret": "secret",
        })

    def _stub_inline_download(self, tmp_path, count: int = 2):
        """Stub wechat_cdn.download_image:不真下载,直接返回已存在的本地文件路径。"""
        files = []
        for i in range(count):
            p = tmp_path / f"inline_{i}.jpg"
            p.write_bytes(b"\xff\xd8\xff\xe0fake")
            files.append(str(p))

        async def fake_download(url, dest_dir, **kw):
            # round-robin: 传几次 URL 拿几次
            if not hasattr(fake_download, "idx"):
                fake_download.idx = 0
            p = files[fake_download.idx % len(files)]
            fake_download.idx += 1
            return p

        return files, fake_download

    def test_happy_path_with_two_inline_images(self, tmp_path):
        cover = tmp_path / "cover.jpg"
        cover.write_bytes(b"\xff\xd8\xff\xe0cover")

        responses = {
            "GET:/cgi-bin/token": {"access_token": "tok", "expires_in": 7200},
            "POST:/cgi-bin/media/uploadimg": {"url": "https://mmbiz.qpic.cn/inline_x"},
            "POST:/cgi-bin/material/add_material": {"media_id": "media_thumb"},
            "POST:/cgi-bin/draft/add": {"media_id": "draft_xyz"},
            "POST:/cgi-bin/freepublish/submit": {"publish_id": "1000000099"},
            # 第一次 get 返 status=1(审核中),第二次返 0(成功)+ article_url
            "POST:/cgi-bin/freepublish/get:0": {
                "publish_id": "1000000099", "publish_status": 1,
            },
            "POST:/cgi-bin/freepublish/get:1": {
                "publish_id": "1000000099", "publish_status": 0,
                "article_url": "https://mp.weixin.qq.com/s?__biz=MzA&mid=99&idx=1",
            },
        }

        # 用 sequence 化 override:freepublish/get 第一次返 1,第二次返 0
        get_calls = {"n": 0}

        async def override(method, url, **kw):
            url_str = str(url)
            if "/cgi-bin/token" in url_str:
                return responses["GET:/cgi-bin/token"]
            if "/cgi-bin/media/uploadimg" in url_str:
                return {"url": f"https://mmbiz.qpic.cn/inline_{get_calls.setdefault('inline', 0) or get_calls.__setitem__('inline', get_calls['inline']+1)}"}
            if "/cgi-bin/material/add_material" in url_str:
                return responses["POST:/cgi-bin/material/add_material"]
            if "/cgi-bin/draft/add" in url_str:
                return responses["POST:/cgi-bin/draft/add"]
            if "/cgi-bin/freepublish/submit" in url_str:
                return responses["POST:/cgi-bin/freepublish/submit"]
            if "/cgi-bin/freepublish/get" in url_str:
                idx = get_calls.setdefault("get", 0)
                get_calls["get"] = idx + 1
                if idx == 0:
                    return {"publish_id": "1000000099", "publish_status": 1}
                return responses["POST:/cgi-bin/freepublish/get:1"]
            return {}

        _files, fake_dl = self._stub_inline_download(tmp_path, count=2)

        body_html = (
            '<p>正文</p>'
            '<img src="https://orig.example/1.jpg"/>'
            '<img src="https://orig.example/2.jpg"/>'
        )

        a = self._adapter()
        with patch.object(a, "_request_override", new=override):
            with patch("app.services.wechat_cdn.download_image", new=fake_dl):
                with patch("asyncio.sleep", new=AsyncMock()):  # 快进轮询
                    result = asyncio.run(a.publish_article_full_auto(
                        title="测试图文",
                        body_html=body_html,
                        cover_image_path=str(cover),
                        poll_interval=0.01, poll_timeout=2.0,
                    ))

        assert result["status"] == "published"
        assert result["platform_publish_id"] == "1000000099"
        assert result["draft_media_id"] == "draft_xyz"
        assert result["freepublish_id"] == "1000000099"
        assert result["freepublish_status"] == 0
        assert "mp.weixin.qq.com" in result["article_url"]
        assert result["thumb_media_id"] == "media_thumb"
        # 验证 HTML 被改写
        assert "mmbiz.qpic.cn" in result["body_html"]

    def test_no_inline_images_skips_uploadimg(self, tmp_path):
        cover = tmp_path / "cover.jpg"
        cover.write_bytes(b"\xff\xd8\xff\xe0c")

        called = {"uploadimg": 0}

        async def override(method, url, **kw):
            url_str = str(url)
            if "/cgi-bin/token" in url_str:
                return {"access_token": "tok", "expires_in": 7200}
            if "/cgi-bin/media/uploadimg" in url_str:
                called["uploadimg"] += 1
                return {"url": "https://mmbiz.qpic.cn/x"}
            if "/cgi-bin/material/add_material" in url_str:
                return {"media_id": "thumb"}
            if "/cgi-bin/draft/add" in url_str:
                return {"media_id": "draft_no_img"}
            if "/cgi-bin/freepublish/submit" in url_str:
                return {"publish_id": "pid_no_img"}
            if "/cgi-bin/freepublish/get" in url_str:
                return {"publish_id": "pid_no_img", "publish_status": 0,
                        "article_url": "https://mp.weixin.qq.com/s?ok"}
            return {}

        a = self._adapter()
        with patch.object(a, "_request_override", new=override):
            with patch("asyncio.sleep", new=AsyncMock()):
                result = asyncio.run(a.publish_article_full_auto(
                    title="纯文字文章",
                    body_html="<p>无图</p>",
                    cover_image_path=str(cover),
                    poll_interval=0.01, poll_timeout=2.0,
                ))

        assert result["status"] == "published"
        assert called["uploadimg"] == 0  # 上传图床没被调

    def test_publish_status_4_returns_failed(self, tmp_path):
        cover = tmp_path / "cover.jpg"
        cover.write_bytes(b"\xff\xd8\xff\xe0c")

        async def override(method, url, **kw):
            url_str = str(url)
            if "/cgi-bin/token" in url_str:
                return {"access_token": "tok", "expires_in": 7200}
            if "/cgi-bin/material/add_material" in url_str:
                return {"media_id": "thumb"}
            if "/cgi-bin/draft/add" in url_str:
                return {"media_id": "draft_fail"}
            if "/cgi-bin/freepublish/submit" in url_str:
                return {"publish_id": "pid_fail"}
            if "/cgi-bin/freepublish/get" in url_str:
                return {"publish_id": "pid_fail", "publish_status": 4, "fail_idx": [99]}
            return {}

        a = self._adapter()
        with patch.object(a, "_request_override", new=override):
            with patch("asyncio.sleep", new=AsyncMock()):
                result = asyncio.run(a.publish_article_full_auto(
                    title="会失败的文章",
                    body_html="<p>x</p>",
                    cover_image_path=str(cover),
                    poll_interval=0.01, poll_timeout=2.0,
                ))

        assert result["status"] == "failed"
        assert result["freepublish_status"] == 4
        assert result.get("article_url") is None
        assert result.get("error_message")

    def test_poll_timeout_returns_freepublish_submitted(self, tmp_path):
        cover = tmp_path / "cover.jpg"
        cover.write_bytes(b"\xff\xd8\xff\xe0c")

        async def override(method, url, **kw):
            url_str = str(url)
            if "/cgi-bin/token" in url_str:
                return {"access_token": "tok", "expires_in": 7200}
            if "/cgi-bin/material/add_material" in url_str:
                return {"media_id": "thumb"}
            if "/cgi-bin/draft/add" in url_str:
                return {"media_id": "draft_slow"}
            if "/cgi-bin/freepublish/submit" in url_str:
                return {"publish_id": "pid_slow"}
            if "/cgi-bin/freepublish/get" in url_str:
                # 永远返 status=1(审核中) — 不可能到 0
                return {"publish_id": "pid_slow", "publish_status": 1}
            return {}

        a = self._adapter()
        with patch.object(a, "_request_override", new=override):
            # 不 mock sleep — poll_timeout=0.05 让循环只跑一次就超时
            result = asyncio.run(a.publish_article_full_auto(
                title="慢发布",
                body_html="<p>x</p>",
                cover_image_path=str(cover),
                poll_interval=0.5, poll_timeout=0.05,
            ))

        assert result["status"] == "freepublish_submitted"
        assert result["freepublish_id"] == "pid_slow"
        assert result["freepublish_status"] == 1
        assert result.get("article_url") is None
        assert "timed out" in (result.get("error_message") or "").lower()

    def test_inline_image_download_failure_returns_failed(self, tmp_path):
        cover = tmp_path / "cover.jpg"
        cover.write_bytes(b"\xff\xd8\xff\xe0c")

        async def fake_download_fail(url, dest_dir, **kw):
            raise WeChatUploadError(f"下载 {url} 失败: ConnectionError")

        async def override(method, url, **kw):
            url_str = str(url)
            if "/cgi-bin/token" in url_str:
                return {"access_token": "tok", "expires_in": 7200}
            return {}

        body_html = '<p>正文</p><img src="https://broken.example/1.jpg"/>'

        a = self._adapter()
        with patch.object(a, "_request_override", new=override):
            with patch("app.services.wechat_cdn.download_image", new=fake_download_fail):
                result = asyncio.run(a.publish_article_full_auto(
                    title="下载失败",
                    body_html=body_html,
                    cover_image_path=str(cover),
                ))

        assert result["status"] == "failed"
        assert "下载" in (result.get("error_message") or "")


# ============ helpers ============

def _override(responses: dict):
    """生成一个 _request_override callable,method 是 GET/POST/UPLOAD,url 是 path-less 或 full。

    responses keys: "GET:/cgi-bin/token", "POST:/cgi-bin/draft/add", "UPLOAD:/..."。
    """
    async def _fake(method, url, params=None, body=None, file_path=None, **kw):
        url_str = str(url)
        for key, val in responses.items():
            m, p = key.split(":", 1)
            if p in url_str:
                return val
        return {}
    return _fake
