"""公众号图文混排 — 图床 & HTML 改写工具

被 WeChatAdapter 调,不依赖 WeChat 特定 import(纯函数 + httpx)。

复用 minimax_client.download_video 的流式下载模式 (L341-356)。
"""
import logging
import re
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

log = logging.getLogger("wechat_cdn")

# 微信 uploadimg 端点单图 10MB 限制,留点 buffer
WECHAT_UPLOADIMG_MAX_BYTES = 10 * 1024 * 1024

# content-type → 后缀
_CONTENT_TYPE_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def get_inline_dir() -> Path:
    """STORAGE_DIR/images/wechat_inline/ — 用 wechat_cdn 下载的临时目录。

    自动 mkdir。download_image 落盘到这里,然后 unlink 掉。
    """
    from app.core.config import settings
    d = Path(settings.STORAGE_DIR) / "images" / "wechat_inline"
    d.mkdir(parents=True, exist_ok=True)
    return d


def extract_img_urls(html: str) -> List[str]:
    """从 HTML 里抓所有 <img src> URL,去重保序,跳过 data: URI。

    >>> extract_img_urls('<p>x</p><img src="https://a/1.jpg"/>')
    ['https://a/1.jpg']
    """
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    seen: set = set()
    out: List[str] = []
    for img in soup.find_all("img"):
        src = img.get("src", "").strip()
        if not src or src.startswith("data:"):
            continue
        if src in seen:
            continue
        seen.add(src)
        out.append(src)
    return out


def rewrite_html_with_cdn(html: str, src_to_url: Dict[str, str]) -> str:
    """把 <img src=old> 替换为 new,其它 attr 保留。

    未在映射里的 src 保持原样。
    """
    if not html or not src_to_url:
        return html
    soup = BeautifulSoup(html, "lxml")

    def _rewrite(tag):
        old = tag.get("src", "").strip()
        if old in src_to_url:
            tag["src"] = src_to_url[old]
        return tag

    for img in soup.find_all("img"):
        _rewrite(img)

    # 用 str() 保持 BeautifulSoup 输出,前端用 marked 重新解析也能识别
    return str(soup)


async def download_image(url: str, dest_dir: Path, timeout: float = 60.0) -> str:
    """把远程图片下载到 dest_dir,返本地绝对路径。

    失败抛 WeChatUploadError。

    复用 minimax_client.download_video 模式 (L341-356) — 同样的 stream + chunked write,
    区别是允许 image/* + application/octet-stream,不强制 video/*。

    :param url: 远程图片 URL(http/https)
    :param dest_dir: 落盘目录(自动 mkdir)
    :param timeout: 单次 HTTP timeout(秒)
    :return: 落盘后本地路径
    """
    from app.platforms.wechat import WeChatUploadError  # 避免循环 import

    dest_dir.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        async with client.stream("GET", url) as resp:
            if resp.status_code != 200:
                raise WeChatUploadError(
                    f"图片下载失败 {resp.status_code}: {url!r}"
                )
            ct = resp.headers.get("content-type", "")
            ext = _CONTENT_TYPE_EXT.get(ct.split(";")[0].strip().lower(), "")
            dest = dest_dir / f"inline_{uuid.uuid4().hex[:12]}{ext}"
            written = 0
            with dest.open("wb") as f:
                async for chunk in resp.aiter_bytes(64 * 1024):
                    written += len(chunk)
                    if written > WECHAT_UPLOADIMG_MAX_BYTES:
                        f.close()
                        dest.unlink(missing_ok=True)
                        raise WeChatUploadError(
                            f"图片超过 10MB 限制 ({url!r},已下 {written} bytes)"
                        )
                    f.write(chunk)
            if written == 0:
                dest.unlink(missing_ok=True)
                raise WeChatUploadError(f"图片下载为空: {url!r}")
    log.info("wechat_cdn.download_image: %s → %s (%d bytes)", url, dest, written)
    return str(dest)
