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
