"""视频号 (WeChat Channels) Adapter — P0-10 快赢

策略: 注册 + 框架完成,核心 upload 抛明确错误提示用户
需要先扫码登录 + 后续集成 `tencent_uploader` 库。

范围:
  ✅ 实现: register / get_adapter / refresh_token / authenticate / get_publish_status
  ⚠️ 部分实现 (MVP 抛明确错误): upload_video
  ❌ 抛 NotImplementedError (MVP 范围外): upload_image / publish_article
"""
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.platforms.base import PlatformAdapter, PlatformType, PublishStatus

log = logging.getLogger("weixin_channels")


class WeixinChannelsNotConfiguredError(Exception):
    """视频号 adapter 尚未配置完成(需要扫码 cookie + tencent_uploader 集成)。"""


class WeixinChannelsAdapter(PlatformAdapter):
    """视频号 adapter (Phase P0-10)。

    account dict 必填字段:
      - platform: "weixin_channels"
      - name:     账号名(对应扫码登录后的 cookie 文件名,后续会用)

    注: 视频号不要求 AppID/AppSecret(走扫码 cookie)。
    """

    def __init__(self, account: Dict[str, Any]):
        super().__init__(PlatformType.WEIXIN_CHANNELS)
        self.account_id = account.get("id", "default")
        self.name = account.get("name") or "default"
        self.cookie_path: Optional[str] = account.get("cookie_path")
        # 视频号特有的 token (扫码后写入)
        self._token: Optional[str] = account.get("token")

    # ============== 必须实现:不抛 ==============

    async def authenticate(self, auth_code: str) -> Dict[str, Any]:
        """视频号不需 OAuth, 走扫码 cookie。authenticate 应是 noop。"""
        return {
            "status": "noop",
            "note": "视频号不需 OAuth, 请用扫码登录(scan_qrcode)拿 cookie",
        }

    async def refresh_token(self) -> Dict[str, Any]:
        """无 token 概念, 直接返 noop。后续接入 tencent_uploader 时再实现。"""
        return {
            "status": "noop",
            "token_expires_at": None,
            "note": "视频号 token 走扫码 cookie 刷新",
        }

    async def get_publish_status(self, publish_id: str) -> PublishStatus:
        """MVP 假设: 上传是同步的,无后续轮询。后续接入 tencent_uploader 时再实现。"""
        return PublishStatus.PUBLISHED

    # ============== 部分实现 (MVP 抛明确错误) ==============

    async def upload_video(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: List[str],
        thumbnail_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """上传视频到视频号。

        现状 (P0-10): 抛 WeixinChannelsNotConfiguredError,
        因为需要先扫码登录 + 集成 `tencent_uploader` 库。

        完整接入步骤(给未来的 TODO):
          1. 扫码登录拿 cookie (参考 `tencent_uploader` README)
          2. 集成 tencent_uploader: `pip install tencent_uploader`
          3. 实现 multipart 上传视频 + 标题 + 描述 + 标签
          4. 实现真 get_publish_status (轮询)
        """
        if not video_path or not Path(video_path).exists():
            raise WeixinChannelsNotConfiguredError(
                f"视频文件不存在: {video_path!r}; 无法上传到视频号"
            )
        # 现状: 抛明确错误
        raise WeixinChannelsNotConfiguredError(
            "视频号 adapter 待集成: 需要扫码登录拿 cookie + pip install tencent_uploader。\n"
            f"已就绪: adapter 已注册到 _REGISTRY, account={self.name!r}, cookie_path={self.cookie_path!r}\n"
            "请到 /platform 创建视频号账号并扫码登录, 或在 P0-10 后续 PR 接入 tencent_uploader。"
        )

    # ============== MVP 范围外: 抛 NotImplementedError ==============

    async def upload_image(
        self,
        image_path: str,
        content: str,
        title: str,
    ) -> Dict[str, Any]:
        raise NotImplementedError("WeixinChannelsAdapter MVP: 仅支持 video")

    async def publish_article(
        self,
        title: str,
        content: str,
        cover_image: Optional[str] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError("WeixinChannelsAdapter MVP: 仅支持 video")
