"""
平台适配器工厂 — Phase 2 + C 阶段 + P0-10

注册表 + `get_adapter(platform_type, account)` 一站式拿实例。
要加新平台只需:
  1. 在 `app/platforms/<name>.py` 实现 PlatformAdapter
  2. 在 _REGISTRY 加一行
"""
from typing import Dict, Type

from app.platforms.base import PlatformAdapter, PlatformType
from app.platforms.douyin import DouyinAdapter
from app.platforms.wechat import WeChatAdapter
from app.platforms.xiaohongshu import XiaohongshuAdapter
from app.platforms.kuaishou import KuaishouAdapter
from app.platforms.bilibili import BilibiliAdapter
from app.platforms.weixin_channels import WeixinChannelsAdapter  # P0-10

# Phase 2 + C + P0-10 注册表
_REGISTRY: Dict[PlatformType, Type[PlatformAdapter]] = {
    PlatformType.DOUYIN: DouyinAdapter,
    PlatformType.WECHAT: WeChatAdapter,
    # C 阶段:sau CLI 通用基类的 3 个
    PlatformType.XIAOHONGSHU: XiaohongshuAdapter,
    PlatformType.KUAISHOU: KuaishouAdapter,
    PlatformType.BILIBILI: BilibiliAdapter,
    # P0-10: 视频号(框架注册完成,核心 upload 抛明确错误等扫码+ tencent_uploader)
    PlatformType.WEIXIN_CHANNELS: WeixinChannelsAdapter,
}


def get_adapter(platform: PlatformType, account: dict) -> PlatformAdapter:
    """根据 platform_type 取具体 adapter 实例。"""
    cls = _REGISTRY.get(platform)
    if not cls:
        raise NotImplementedError(
            f"平台 {platform.value} 的 adapter 还没实现。"
            f"已支持的: {[p.value for p in _REGISTRY.keys()]}"
        )
    return cls(account)


def supported_platforms():
    """返回已实现的 platform_type 列表(给前端 / API 用)。"""
    return list(_REGISTRY.keys())


__all__ = [
    "PlatformAdapter",
    "PlatformType",
    "PublishStatus",
    "ContentType",
    "get_adapter",
    "supported_platforms",
    "DouyinAdapter",
    "WeChatAdapter",
    "XiaohongshuAdapter",
    "KuaishouAdapter",
    "BilibiliAdapter",
    "WeixinChannelsAdapter",  # P0-10
]
