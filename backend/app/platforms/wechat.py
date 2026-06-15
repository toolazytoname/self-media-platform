"""
WeChat (公众号) 平台 Adapter — Phase 2 ext

实现公众号"草稿箱"全链路:
  1. 用 AppID + AppSecret 拿 access_token(2 小时 TTL,自动刷新)
  2. 上传封面图 → 拿 media_id(cgi-bin/material/add_material)
  3. 加到草稿箱(cgi-bin/draft/add)→ 返 media_id(此处是 draft id)
  4. (可选) 改草稿(cgi-bin/draft/update)
  5. get_publish_status → 直接返 PUBLISHED(草稿箱写入 = 成功)

NOTE: 公众号的"草稿箱"是私有的,不在公众号前台展示。
发布到公众号 = 用户手动点草稿箱的"发布"按钮 — 我们这一层只写到草稿箱。
"""
import asyncio
import logging
import mimetypes
import os
import time
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

import httpx

from app.platforms.base import PlatformAdapter, PlatformType, PublishStatus

log = logging.getLogger("wechat")


class WeChatUploadError(Exception):
    """公众号 API 调用失败。"""


# access_token 缓存
class _TokenCache:
    def __init__(self):
        self.token: Optional[str] = None
        self.expires_at: float = 0.0  # epoch seconds

    def is_valid(self) -> bool:
        return bool(self.token) and time.time() < self.expires_at - 60  # 提前 60s 失效

    def set(self, token: str, expires_in: int):
        self.token = token
        self.expires_at = time.time() + expires_in


class WeChatAdapter(PlatformAdapter):
    """公众号(WeChat MP)Adapter

    account dict 必填字段:
      - app_id: 公众号 AppID
      - app_secret: 公众号 AppSecret
    account.id 用于 audit; account.name 用于日志。
    """

    def __init__(self, account: Dict[str, Any]):
        super().__init__(PlatformType.WECHAT)
        from app.core.config import settings
        self.account_id = account.get("id", "default")
        self.name = account.get("name") or "default"
        self.app_id = account.get("app_id") or settings.WECHAT_APP_ID
        self.app_secret = account.get("app_secret") or settings.WECHAT_APP_SECRET
        self.base_url = (
            account.get("api_base")
            or getattr(settings, "WECHAT_API_BASE", "https://api.weixin.qq.com")
        ).rstrip("/")
        self._token = _TokenCache()
        # 测时 override:允许测试时跳过真请求
        self._request_override: Optional[Any] = None

    # ============== 抽象方法:不实现(只做 article) ==============

    async def authenticate(self, auth_code: str) -> Dict[str, Any]:
        # 公众号 OAuth 用 AppSecret 模式(无 redirect/auth_code),不实现
        return {
            "status": "noop",
            "note": "公众号用 AppID + AppSecret 模式,在 Settings / 账号创建时填,无需 OAuth callback",
        }

    async def refresh_token(self) -> Dict[str, Any]:
        await self._ensure_token(force_refresh=True)
        return {
            "status": "ok",
            "token_expires_at": self._token.expires_at,
        }

    async def upload_video(
        self, video_path: str, title: str, description: str,
        tags: List[str], thumbnail_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError("WeChatAdapter MVP: 仅支持图文(草稿箱)")

    async def upload_image(
        self, image_path: str, content: str, title: str,
    ) -> Dict[str, Any]:
        # 这个端点是给"图文混排"用的(不是视频号的图片上传)
        # WeChat 永久素材(给 draft 当 thumb)
        return await self._upload_image_material(image_path)

    async def publish_article(
        self, title: str, content: str, cover_image: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        把图文加到公众号草稿箱。
        - title: 文章标题(< 64 字)
        - content: HTML 字符串(公众号 content 字段;支持内联 <img> 等)
        - cover_image: 封面图本地路径;若给,先上传拿 thumb_media_id
        """
        if not title or len(title) > 64:
            raise WeChatUploadError(f"公众号标题 1-64 字,实际 {len(title)}")
        if not content:
            raise WeChatUploadError("公众号 content 不能为空")
        # 先校验封面(用本地路径),失败比 token 错误更早冒出来,更用户友好
        thumb_media_id = ""
        if cover_image:
            if not Path(cover_image).exists():
                raise WeChatUploadError(f"封面图不存在: {cover_image}")
        await self._ensure_token()
        if cover_image:
            up = await self._upload_image_material(cover_image)
            thumb_media_id = up["media_id"]
        # 加草稿
        body = {
            "title": title,
            "content": content,
            "content_source_url": "",
            "need_open_comment": 0,
            "only_fans_can_comment": 0,
        }
        if thumb_media_id:
            body["thumb_media_id"] = thumb_media_id
        # 公众号 content 字段类型:image-text 走 news;纯文字走 text
        # 这里我们用 news(图文),需要 thumb
        # 如果没传封面,把 article_type 切到 text
        # 实际公众号对 article_type 是独立的字段,api draft/add 不直接接受
        # 这里简化:有封面就 news,无就 text
        # 真要区分, 后续可以加 article_type 字段
        result = await self._api_post("/cgi-bin/draft/add", body)
        if "media_id" not in result:
            raise WeChatUploadError(
                f"公众号 draft/add 失败: errcode={result.get('errcode')} errmsg={result.get('errmsg')}"
            )
        return {
            "platform_publish_id": result["media_id"],   # 草稿 id
            "url": "",                                     # 草稿不返 URL
            "status": "draft_added",                        # 草稿箱已写入
            "thumb_media_id": thumb_media_id,
            "draft_url": f"https://mp.weixin.qq.com/cgi-bin/appmsg?action=list&type=10",  # 草稿箱管理页
        }

    async def get_publish_status(self, publish_id: str) -> PublishStatus:
        # 草稿写入即成功;"发布"是用户手动行为
        return PublishStatus.PUBLISHED

    # ============== access_token 管理 ==============

    async def _ensure_token(self, force_refresh: bool = False):
        if not force_refresh and self._token.is_valid():
            return
        if not self.app_id or not self.app_secret:
            raise WeChatUploadError(
                "公众号 AppID / AppSecret 未配置(在 Settings 填,或在账号创建时传)"
            )
        url = f"{self.base_url}/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": self.app_id,
            "secret": self.app_secret,
        }
        data = await self._api_get(url, params=params)
        if "access_token" not in data:
            raise WeChatUploadError(
                f"公众号 token 获取失败: {data.get('errcode')} {data.get('errmsg')}"
            )
        self._token.set(data["access_token"], int(data.get("expires_in", 7200)))
        log.info("wechat token refreshed, expires_in=%s", data.get("expires_in"))

    # ============== HTTP helpers ==============

    async def _api_get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self._request_override:
            return await self._request_override("GET", url, params=params)
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(url, params=params or {})
            try:
                return r.json()
            except Exception:
                return {"_status": r.status_code, "_text": r.text[:500]}

    async def _api_post(
        self, path: str, body: Dict[str, Any], params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        merged_params = {"access_token": self._token.token, **(params or {})}
        if self._request_override:
            return await self._request_override("POST", url, params=merged_params, body=body)
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 公众号 draft/add 接受 application/json
            r = await client.post(url, params=merged_params, json=body)
            try:
                return r.json()
            except Exception:
                return {"_status": r.status_code, "_text": r.text[:500]}

    async def _upload_image_material(self, image_path: str) -> Dict[str, Any]:
        """永久素材上传 — 用于 draft 的 thumb_media_id。"""
        url = f"{self.base_url}/cgi-bin/material/add_material"
        params = {
            "access_token": self._token.token,
            "type": "image",
        }
        if self._request_override:
            return await self._request_override("UPLOAD", url, params=params, file_path=image_path)
        # 真实 multipart
        mime = mimetypes.guess_type(image_path)[0] or "image/jpeg"
        with open(image_path, "rb") as f:
            files = {"media": (os.path.basename(image_path), f, mime)}
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(url, params=params, files=files)
        try:
            return r.json()
        except Exception:
            return {"_status": r.status_code, "_text": r.text[:500]}

    # ============================================================
    # P0-1: 全自动图文混排 — uploadimg / freepublish / 轮询 / 编排
    # ============================================================

    async def _upload_inline_image(self, image_path: str) -> str:
        """POST /cgi-bin/media/uploadimg(临时素材)— 上传正文图片,返 mmbiz URL。

        与 _upload_image_material(永久素材,for thumb)的区别:
        - 永久素材:有 5000 张上限,长期存储,用于封面
        - 临时素材:无存储上限,3 天有效,但 URL 永久可用(微信官方承诺),
          用于文章正文 <img>。

        失败抛 WeChatUploadError(errcode 透传)。
        """
        url = f"{self.base_url}/cgi-bin/media/uploadimg"
        params = {"access_token": self._token.token}
        if self._request_override:
            res = await self._request_override("UPLOAD", url, params=params, file_path=image_path)
        else:
            mime = mimetypes.guess_type(image_path)[0] or "image/jpeg"
            with open(image_path, "rb") as f:
                files = {"media": (os.path.basename(image_path), f, mime)}
                async with httpx.AsyncClient(timeout=60.0) as client:
                    r = await client.post(url, params=params, files=files)
            try:
                res = r.json()
            except Exception:
                res = {"_status": r.status_code, "_text": r.text[:500]}
        if res.get("errcode") and res["errcode"] != 0:
            raise WeChatUploadError(
                f"公众号 uploadimg 失败: errcode={res.get('errcode')} errmsg={res.get('errmsg')}"
            )
        if "url" not in res:
            raise WeChatUploadError(
                f"公众号 uploadimg 返无 url: {json.dumps(res)[:200]}"
            )
        return res["url"]

    async def submit_for_publish(self, draft_media_id: str) -> str:
        """POST /cgi-bin/freepublish/submit — 把草稿派发到公众号,返 publish_id。

        派发后,文章进入微信审核/发布流程(异步)。
        """
        await self._ensure_token()
        body = {"media_id": draft_media_id}
        res = await self._api_post("/cgi-bin/freepublish/submit", body)
        if res.get("errcode") and res["errcode"] != 0:
            raise WeChatUploadError(
                f"公众号 freepublish/submit 失败: errcode={res.get('errcode')} errmsg={res.get('errmsg')}"
            )
        if "publish_id" not in res:
            raise WeChatUploadError(
                f"公众号 freepublish/submit 返无 publish_id: {json.dumps(res)[:200]}"
            )
        return res["publish_id"]

    async def query_publish_status(self, publish_id: str) -> Dict[str, Any]:
        """POST /cgi-bin/freepublish/get — 查派发后的状态。

        publish_status:
          0=成功(已发布)
          1=发布中
          2=原创审核中
          3=参数错误(不会到这里,submit 阶段会抛)
          4=失败(发布未通过)
        """
        await self._ensure_token()
        body = {"publish_id": publish_id}
        res = await self._api_post("/cgi-bin/freepublish/get", body)
        if res.get("errcode") and res["errcode"] != 0:
            raise WeChatUploadError(
                f"公众号 freepublish/get 失败: errcode={res.get('errcode')} errmsg={res.get('errmsg')}"
            )
        return res

    async def publish_article_full_auto(
        self,
        title: str,
        body_html: str,
        cover_image_path: str,
        *,
        poll_interval: float = 2.0,
        poll_timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """一键全流程:uploadimg(×N) → 草稿 → 派发 → 轮询 → 返结果。

        终态返回:
          - {status: "published", article_url, freepublish_status: 0, ...}
          - {status: "failed", error_message, ...}
          - {status: "freepublish_submitted", freepublish_status: 1, error_message 含 "timed out", ...}
        """
        import asyncio
        from app.services.wechat_cdn import (
            extract_img_urls,
            rewrite_html_with_cdn,
            download_image,
            get_inline_dir,
        )

        result: Dict[str, Any] = {
            "status": "failed",
            "platform_publish_id": None,
            "article_url": None,
            "draft_media_id": None,
            "freepublish_id": None,
            "freepublish_status": None,
            "thumb_media_id": None,
            "body_html": body_html,
            "error_message": None,
        }

        # 1. 基础校验
        if not title or len(title) > 64:
            result["error_message"] = f"公众号标题 1-64 字,实际 {len(title)}"
            return result
        if not body_html:
            result["error_message"] = "公众号 content 不能为空"
            return result
        if not cover_image_path or not Path(cover_image_path).exists():
            result["error_message"] = f"封面图不存在: {cover_image_path}"
            return result

        # 2. token
        try:
            await self._ensure_token()
        except WeChatUploadError as e:
            result["error_message"] = str(e)
            return result

        # 3. 上传正文图片到微信 CDN
        src_urls = extract_img_urls(body_html)
        src_to_mmbiz: Dict[str, str] = {}
        temp_paths: List[str] = []
        if src_urls:
            inline_dir = get_inline_dir()
            for src in src_urls:
                try:
                    local = await download_image(src, inline_dir)
                    temp_paths.append(local)
                    mmbiz = await self._upload_inline_image(local)
                    src_to_mmbiz[src] = mmbiz
                except WeChatUploadError as e:
                    # 清理临时
                    for p in temp_paths:
                        try:
                            Path(p).unlink(missing_ok=True)
                        except Exception:
                            pass
                    result["error_message"] = (
                        f"正文图床上传失败: {e} (src={src!r})"
                    )
                    return result

        # 改写 body HTML
        rewritten_html = rewrite_html_with_cdn(body_html, src_to_mmbiz)
        result["body_html"] = rewritten_html

        # 4. 上传封面(永久素材)
        try:
            up = await self._upload_image_material(cover_image_path)
        except WeChatUploadError as e:
            for p in temp_paths:
                try:
                    Path(p).unlink(missing_ok=True)
                except Exception:
                    pass
            result["error_message"] = f"封面上传失败: {e}"
            return result
        if up.get("errcode") and up["errcode"] != 0:
            for p in temp_paths:
                try:
                    Path(p).unlink(missing_ok=True)
                except Exception:
                    pass
            result["error_message"] = (
                f"封面上传失败: errcode={up.get('errcode')} errmsg={up.get('errmsg')}"
            )
            return result
        thumb_media_id = up.get("media_id", "")
        result["thumb_media_id"] = thumb_media_id

        # 5. 写草稿
        draft_body = {
            "title": title,
            "content": rewritten_html,
            "content_source_url": "",
            "need_open_comment": 0,
            "only_fans_can_comment": 0,
        }
        if thumb_media_id:
            draft_body["thumb_media_id"] = thumb_media_id
        try:
            draft_res = await self._api_post("/cgi-bin/draft/add", draft_body)
        except WeChatUploadError as e:
            for p in temp_paths:
                try:
                    Path(p).unlink(missing_ok=True)
                except Exception:
                    pass
            result["error_message"] = f"draft/add 失败: {e}"
            return result
        if "media_id" not in draft_res:
            for p in temp_paths:
                try:
                    Path(p).unlink(missing_ok=True)
                except Exception:
                    pass
            result["error_message"] = (
                f"公众号 draft/add 失败: errcode={draft_res.get('errcode')} "
                f"errmsg={draft_res.get('errmsg')}"
            )
            return result
        draft_media_id = draft_res["media_id"]
        result["draft_media_id"] = draft_media_id

        # 6. 派发发布
        try:
            publish_id = await self.submit_for_publish(draft_media_id)
        except WeChatUploadError as e:
            for p in temp_paths:
                try:
                    Path(p).unlink(missing_ok=True)
                except Exception:
                    pass
            result["error_message"] = f"freepublish/submit 失败: {e}"
            return result
        result["freepublish_id"] = publish_id
        result["platform_publish_id"] = publish_id

        # 7. 轮询 freepublish/get,直到 status==0/3/4 或超时
        start = time.time()
        final_status: Optional[int] = None
        article_url: Optional[str] = None
        while time.time() - start < poll_timeout:
            try:
                st = await self.query_publish_status(publish_id)
            except WeChatUploadError as e:
                log.warning("freepublish/get 失败: %s,继续轮询", e)
                await asyncio.sleep(poll_interval)
                continue
            final_status = st.get("publish_status")
            article_url = st.get("article_url")
            if final_status == 0:
                break  # 成功
            if final_status in (3, 4):
                break  # 终态失败
            await asyncio.sleep(poll_interval)

        # 8. 清理临时文件(成功失败都清)
        for p in temp_paths:
            try:
                Path(p).unlink(missing_ok=True)
            except Exception:
                pass

        result["freepublish_status"] = final_status
        result["article_url"] = article_url

        if final_status == 0:
            result["status"] = "published"
        elif final_status in (3, 4):
            result["status"] = "failed"
            result["error_message"] = (
                f"公众号发布失败: publish_status={final_status} (fail_idx={article_url!r})"
            )
        else:
            # 仍审核中
            result["status"] = "freepublish_submitted"
            result["error_message"] = (
                f"freepublish timed out after {poll_timeout}s; "
                "公众号后台可见进度"
            )
        return result
