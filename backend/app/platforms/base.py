# 平台适配器抽象层

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from enum import Enum


class PlatformType(Enum):
    DOUYIN = "douyin"
    BILIBILI = "bilibili"
    YOUTUBE = "youtube"
    XIAOHONGSHU = "xiaohongshu"
    TOUTIAO = "toutiao"
    WECHAT = "wechat"  # 微信公众号
    TIKTOK = "tiktok"
    KUAISHOU = "kuaishou"
    BAIJIA = "baijia"


class ContentType(Enum):
    TEXT = "text"       # 图文
    VIDEO = "video"     # 视频
    AUDIO = "audio"    # 音频/播客


class PublishStatus(Enum):
    PENDING = "pending"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"


class PlatformAdapter(ABC):
    """平台适配器基类"""

    def __init__(self, platform: PlatformType):
        self.platform = platform

    @abstractmethod
    async def authenticate(self, auth_code: str) -> Dict[str, Any]:
        """OAuth认证"""
        pass

    @abstractmethod
    async def refresh_token(self) -> Dict[str, Any]:
        """刷新Token"""
        pass

    @abstractmethod
    async def upload_video(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: List[str],
        thumbnail_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """上传视频"""
        pass

    @abstractmethod
    async def upload_image(
        self,
        image_path: str,
        content: str,
        title: str
    ) -> Dict[str, Any]:
        """上传图文"""
        pass

    @abstractmethod
    async def publish_article(
        self,
        title: str,
        content: str,
        cover_image: Optional[str] = None
    ) -> Dict[str, Any]:
        """发布文章"""
        pass

    @abstractmethod
    async def get_publish_status(self, publish_id: str) -> PublishStatus:
        """获取发布状态"""
        pass

    async def randomize_interval(self, min_seconds: int = 300, max_seconds: int = 900):
        """随机间隔（反机器检测）"""
        import random
        import asyncio
        interval = random.randint(min_seconds, max_seconds)
        await asyncio.sleep(interval)

    def get_user_agent(self) -> str:
        """随机User-Agent"""
        import random
        ua_list = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Firefox/120.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
        ]
        return random.choice(ua_list)