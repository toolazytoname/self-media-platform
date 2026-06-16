"""视频号 (WeChat Channels) Adapter — TASK-P0-10 测试

策略: 快赢 - 实现注册 + 框架,核心 upload 抛明确错误提示
(需要扫码登录 + tencent_uploader 集成)。

覆盖:
- PlatformType.WEIXIN_CHANNELS 存在
- _REGISTRY 包含 WeixinChannelsAdapter
- get_adapter 不抛 NotImplementedError
- upload_video 抛明确错误(无 tencent_uploader)
- upload_image / publish_article 抛 NotImplementedError(MVP 范围外)
- get_publish_status / refresh_token / authenticate 不抛
- account 配置最小(只要 platform + name,不用 app_id/secret)
"""
import asyncio
import pytest
from unittest.mock import patch, AsyncMock

from app.platforms.base import PlatformType, PublishStatus
from app.platforms import get_adapter, supported_platforms, _REGISTRY
from app.platforms.weixin_channels import WeixinChannelsNotConfiguredError


# ============ 注册 ============

class TestRegistration:
    def test_weixin_channels_in_enum(self):
        assert hasattr(PlatformType, "WEIXIN_CHANNELS")
        assert PlatformType.WEIXIN_CHANNELS.value == "weixin_channels"

    def test_weixin_channels_in_registry(self):
        from app.platforms.weixin_channels import WeixinChannelsAdapter
        assert PlatformType.WEIXIN_CHANNELS in _REGISTRY
        assert _REGISTRY[PlatformType.WEIXIN_CHANNELS] is WeixinChannelsAdapter

    def test_supported_platforms_includes_weixin_channels(self):
        platforms = supported_platforms()
        assert PlatformType.WEIXIN_CHANNELS in platforms

    def test_get_adapter_returns_instance(self):
        account = {"platform": "weixin_channels", "name": "test_channels"}
        adapter = get_adapter(PlatformType.WEIXIN_CHANNELS, account)
        assert adapter.platform == PlatformType.WEIXIN_CHANNELS


# ============ 核心:upload_video 必须抛明确错误 ============

class TestUploadVideo:
    """MVP 范围: upload_video 抛明确错误,等 tencent_uploader 集成后再实现"""

    def _adapter(self):
        account = {"platform": "weixin_channels", "name": "test_channels"}
        return get_adapter(PlatformType.WEIXIN_CHANNELS, account)

    def test_raises_specific_error(self, tmp_path):
        """上传视频抛 WeixinChannelsNotConfiguredError(不是 NotImplementedError)"""
        video = tmp_path / "v.mp4"
        video.write_bytes(b"fake video content")
        adapter = self._adapter()
        with pytest.raises(WeixinChannelsNotConfiguredError) as exc_info:
            asyncio.run(adapter.upload_video(
                video_path=str(video), title="t", description="d", tags=[],
            ))
        # 错误消息必须提到"扫码"或"tencent_uploader"或"cookie"
        msg = str(exc_info.value).lower()
        assert any(kw in msg for kw in (
            "扫码", "cookie", "tencent_uploader", "tencent", "扫码登录",
            "scan", "login", "未配置", "未实现",
        )), f"错误消息应说明需要扫码/cookie, 实际: {msg!r}"

    def test_raises_if_video_not_found(self):
        """视频文件不存在也抛明确错误(而不是裸 FileNotFoundError)"""
        adapter = self._adapter()
        with pytest.raises(WeixinChannelsNotConfiguredError) as exc_info:
            asyncio.run(adapter.upload_video(
                video_path="/nonexistent/v.mp4", title="t", description="d", tags=[],
            ))
        # 错误消息要明确说"不存在"或"未配置"
        msg = str(exc_info.value)
        assert "不存在" in msg or "未配置" in msg or "not found" in msg.lower()


# ============ MVP 范围外: 抛 NotImplementedError ============

class TestOutOfScope:
    """图文 / 文章 不支持,抛 NotImplementedError"""

    def _adapter(self):
        account = {"platform": "weixin_channels", "name": "test_channels"}
        return get_adapter(PlatformType.WEIXIN_CHANNELS, account)

    def test_upload_image_raises_not_implemented(self, tmp_path):
        img = tmp_path / "i.png"
        img.write_bytes(b"fake")
        adapter = self._adapter()
        with pytest.raises(NotImplementedError):
            asyncio.run(adapter.upload_image(
                image_path=str(img), content="x", title="t",
            ))

    def test_publish_article_raises_not_implemented(self, tmp_path):
        cover = tmp_path / "c.jpg"
        cover.write_bytes(b"x")
        adapter = self._adapter()
        with pytest.raises(NotImplementedError):
            asyncio.run(adapter.publish_article(
                title="t", content="<p>x</p>", cover_image=str(cover),
            ))


# ============ 必须实现: 不抛 ============

class TestImplemented:
    """refresh_token / authenticate / get_publish_status 必须不抛(无 NotImplementedError)"""

    def _adapter(self):
        account = {"platform": "weixin_channels", "name": "test_channels"}
        return get_adapter(PlatformType.WEIXIN_CHANNELS, account)

    def test_refresh_token_no_raise(self):
        adapter = self._adapter()
        # 不抛 NotImplementedError(可以返个 noop result)
        result = asyncio.run(adapter.refresh_token())
        assert isinstance(result, dict)

    def test_authenticate_no_raise(self):
        adapter = self._adapter()
        # 视频号不需 OAuth (走扫码 cookie);authenticate 应是 noop
        result = asyncio.run(adapter.authenticate(""))
        assert isinstance(result, dict)
        # 应说明 noop 或扫码模式
        msg = str(result).lower()
        assert any(kw in msg for kw in ("noop", "扫码", "scan", "cookie"))

    def test_get_publish_status_returns_known_value(self):
        adapter = self._adapter()
        result = asyncio.run(adapter.get_publish_status("any_id"))
        # MVP 假设:返回 PUBLISHED (后续接入真轮询再改)
        assert result in (PublishStatus.PUBLISHED, PublishStatus.PUBLISHING, PublishStatus.PENDING)


# ============ Account 字段最小化 ============

class TestAccountMinimal:
    """视频号账号配置不应要求 app_id / app_secret(走扫码 cookie)"""

    def test_minimal_account_only_needs_name(self):
        """只传 platform + name 也能构造 adapter(不抛)"""
        account = {"platform": "weixin_channels", "name": "minimal"}
        adapter = get_adapter(PlatformType.WEIXIN_CHANNELS, account)
        # 构造成功
        assert adapter is not None
        assert adapter.platform == PlatformType.WEIXIN_CHANNELS
