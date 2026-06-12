"""
抖音平台适配器 — Phase 2 MVP

通过 `sau` (social-auto-upload) CLI 调用 patchright/Chromium 完成上传。
Subprocess wrapper 模式,避免与 sau 内部耦合。

Cookie 走 sau 的 storage_state 机制,不归我们管;我们只持有 cookie_path。

MVP 假设:
- 一次只能上传一个视频(没做并发)
- 不做 image_url 缩略图(留给 Phase 3)
- 不实现 image / article(只 video)
- get_publish_status 在 MVP 直接返 PUBLISHED(MVP 假设: 上传是同步的,无后续轮询)
"""

import asyncio
import logging
import os
import re
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.platforms.base import PlatformAdapter, PlatformType, PublishStatus

log = logging.getLogger("douyin")


class DouyinUploadError(Exception):
    """sau 调用失败 / 抖音拒绝。"""


# 抖音标题硬上限 30 字符(UTF-8 字节,可能更严)
DOUYIN_TITLE_MAX_BYTES = 30

# 从 sau stdout 抓 "已发布" URL 的模式
# 抖音创作者中心发布后跳 /creator-micro/content/manage?... 或短链
_MANAGE_URL_RE = re.compile(
    r"https?://[^\s\"']+(?:/content/manage|/content/post|creator\.douyin\.com/creator-micro[^\s\"']*)",
    re.IGNORECASE,
)


def _clamp_title_to_bytes(title: str, max_bytes: int = DOUYIN_TITLE_MAX_BYTES) -> str:
    """UTF-8 安全截断到 max_bytes 字节,避免抖音硬截失败。"""
    b = title.encode("utf-8")
    if len(b) <= max_bytes:
        return title
    truncated = b[:max_bytes]
    # 防止把多字节字符切到一半
    while truncated and (truncated[-1] & 0xC0) == 0x80:
        truncated = truncated[:-1]
    return truncated.decode("utf-8", errors="ignore")


def _resolve_sau_bin(env_bin: str) -> Optional[str]:
    """解析 sau 二进制路径。找不到返回 None(让 __init__ 装成 None,延迟到 upload 时报错)。"""
    if env_bin and os.path.isabs(env_bin) and os.path.isfile(env_bin):
        return env_bin
    if env_bin and shutil.which(env_bin):
        return env_bin
    return shutil.which("sau")


class DouyinAdapter(PlatformAdapter):
    """抖音适配器。account dict 必填字段: name, cookie_path(可选)。"""

    def __init__(self, account: Dict[str, Any]):
        super().__init__(PlatformType.DOUYIN)
        self.account_id = account.get("id", "default")
        self.name = account.get("name") or "default"
        # cookie_path 是 sau 的 storage_state JSON 文件
        # 缺省走 settings.COOKIES_DIR/{name}.json
        from app.core.config import settings
        self.cookie_path = (
            account.get("cookie_path")
            or str(Path(settings.COOKIES_DIR) / f"{self.name}.json")
        )
        # 允许通过 account dict 显式覆盖 sau 路径(测试用)
        self.sau_bin = (
            account.get("sau_bin")
            or _resolve_sau_bin(getattr(settings, "DOUYIN_SAU_BIN", "sau"))
        )

    def _require_sau(self) -> str:
        if not self.sau_bin:
            raise DouyinUploadError(
                "未找到 sau 二进制。请先安装 social-auto-upload: "
                "`pipx install social-auto-upload` (系统级,不是 pip 包)"
            )
        return self.sau_bin

    # --------- 抽象方法:不实现(MVP 只做 video) ---------

    async def authenticate(self, auth_code: str) -> Dict[str, Any]:
        # 抖音走 QR 扫码,不是 OAuth code;不实现
        return {
            "status": "noop",
            "note": "douyin 用 sau douyin login --account X 跑 QR 扫码,见 README",
            "cookie_path": self.cookie_path,
        }

    async def refresh_token(self) -> Dict[str, Any]:
        # 抖音无 token 刷新;cookie 由 sau 自己维护
        return {"status": "noop", "note": "douyin 用 cookie 而非 token,不需要 refresh"}

    async def upload_image(
        self, image_path: str, content: str, title: str
    ) -> Dict[str, Any]:
        raise NotImplementedError("DouyinAdapter MVP: 仅支持 video")

    async def publish_article(
        self, title: str, content: str, cover_image: Optional[str] = None
    ) -> Dict[str, Any]:
        raise NotImplementedError("DouyinAdapter MVP: 仅支持 video")

    async def get_publish_status(self, publish_id: str) -> PublishStatus:
        # MVP 假设: 上传是同步的,无后续轮询
        return PublishStatus.PUBLISHED

    # --------- 真正实现的核心:upload_video ---------

    async def upload_video(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: List[str],
        thumbnail_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """调 `sau douyin upload-video` 上传一个视频。

        成功:返回 {platform_publish_id, url, status:"published"}
        失败:raise DouyinUploadError(stderr 摘要)
        """
        if not Path(video_path).exists():
            raise DouyinUploadError(f"video file not found: {video_path}")

        clamped = _clamp_title_to_bytes(title)
        if clamped != title:
            log.warning(
                "douyin title 截断: %r -> %r (%d bytes)",
                title, clamped, len(clamped.encode("utf-8")),
            )

        cmd = [
            self._require_sau(), "douyin", "upload-video",
            "--account", self.name,
            "--file", str(video_path),
            "--title", clamped,
            "--desc", description or "",
            "--tags", ",".join(tags or []),
        ]
        if thumbnail_path:
            cmd.extend(["--thumbnail", str(thumbnail_path)])

        log.info("douyin upload: %s", " ".join(cmd[:6]) + " ...")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=600
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise DouyinUploadError("sau douyin upload-video timeout (600s)")

        out = (stdout or b"").decode("utf-8", errors="replace")
        err = (stderr or b"").decode("utf-8", errors="replace")

        if proc.returncode != 0:
            raise DouyinUploadError(
                f"sau exit={proc.returncode}, stderr: {err[-1000:]!r}"
            )

        # 抓 URL
        url_match = _MANAGE_URL_RE.search(out)
        url = url_match.group(0) if url_match else None

        return {
            "platform_publish_id": url or f"sau-success-{self.account_id}",
            "url": url,
            "status": "published",
            "raw_stdout_tail": out[-500:],
        }

    def __repr__(self) -> str:
        return f"<DouyinAdapter account={self.name!r} cookie={self.cookie_path}>"
