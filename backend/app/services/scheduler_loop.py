"""
后台调度任务循环 — Phase 2 实装

每个 tick:
  1. 扫 store.scheduled_tasks, 找 status=pending 且 scheduled_time <= now 的
  2. 解析 content / video / account
  3. mock video 直接拒
  4. 调对应 PlatformAdapter.upload_video()
  5. 成功 → status="completed", publish_record "published", content "published"
     失败 → status="failed", publish_record "failed", 写 error_message
  6. attempt_count 自增, 超 3 次永久 failed

publish_now(content_id, platform, account_id, video_id) 给前端 "立即发布" 用,
不走 scheduled_time 检查, 同步返回结果。
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from app.store import store
from app.platforms import get_adapter
from app.platforms.base import PlatformType

logger = logging.getLogger("scheduler")

# 同一任务最大尝试次数,超了就永久 failed(避免死循环)
MAX_ATTEMPTS = 3


class SchedulerLoop:
    """in-process 调度循环 + publish-now 同步派发"""

    def __init__(self, interval_seconds: int = 30):
        self.interval = interval_seconds
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self.running = False

    # ============================================================
    # 核心: 派发单个任务(供 _run_due_tasks 和 publish_now 共用)
    # ============================================================
    async def _dispatch_task(self, task: Dict[str, Any], allow_retry: bool = True) -> Dict[str, Any]:
        """对单个 scheduled task 跑一次完整上传流。返回 summary dict。

        task 字段预期: id, content_id, platform, account_id, video_id, publish_id
        """
        from app.core.config import settings
        import shutil

        now_iso = datetime.now().isoformat()
        platform_str = task.get("platform", "douyin")
        account_id = task.get("account_id")
        video_id = task.get("video_id")
        content_id = task.get("content_id")
        publish_id = task.get("publish_id")

        # --- 1) 校验必需资源 ---
        content = store.get_content(content_id) if content_id else None
        if not content:
            return self._mark_failed(task, publish_id, content_id, "content not found")

        account = store.get_account(account_id) if account_id else None
        if not account:
            return self._mark_failed(
                task, publish_id, content_id,
                f"platform account not found (account_id={account_id});"
                f" 用户需先在 /platforms 添加账号",
            )

        video = store.get_video(video_id) if video_id else None
        if not video:
            return self._mark_failed(
                task, publish_id, content_id,
                f"video record not found (video_id={video_id})",
            )
        if video.get("is_mock"):
            return self._mark_failed(
                task, publish_id, content_id,
                "mock video 不能真实发布 — 请装 sau + 抖音 cookie 后重新生成",
            )

        # --- 2) 解析 platform ---
        try:
            platform = PlatformType(platform_str)
        except ValueError:
            return self._mark_failed(
                task, publish_id, content_id,
                f"unsupported platform: {platform_str!r}",
            )

        # --- 3) 拿 adapter + 检查 cookie 存在 ---
        if not Path_safe(account.get("cookie_path")):
            return self._mark_failed(
                task, publish_id, content_id,
                f"cookie file missing: {account.get('cookie_path')}; "
                f"先在 VM 上跑 `sau douyin login --account {account.get('name')}`",
            )

        # --- 4) 准备元数据,30 字节 title 截断(adapter 也会再截) ---
        raw_title = content.get("title") or ""
        title = raw_title[:30] if len(raw_title.encode("utf-8")) > 30 else raw_title
        description = content.get("body", "")[:2000]
        tags = (content.get("tags") or [])[:10]
        local_path = video.get("local_path") or ""

        # --- 5) 派发 ---
        task["status"] = "running"
        task["attempt_count"] = task.get("attempt_count", 0) + 1
        if publish_id:
            store.update_publish_record(publish_id, {
                "status": "uploading",
                "attempted_at": now_iso,
            })

        try:
            adapter = get_adapter(platform, account)
            result = await adapter.upload_video(
                video_path=local_path,
                title=title,
                description=description,
                tags=tags,
            )
        except Exception as e:
            logger.exception("dispatch failed for task %s", task.get("id"))
            # publish-now 不允许重试,第一次失败就标 failed
            if not allow_retry or task["attempt_count"] >= MAX_ATTEMPTS:
                return self._mark_failed(
                    task, publish_id, content_id,
                    f"max attempts reached, last error: {e}",
                    permanent=True,
                )
            # 留 pending,下次 tick 再试
            task["status"] = "pending"
            task["error_message"] = f"attempt {task['attempt_count']}/{MAX_ATTEMPTS}: {e}"[:500]
            return {
                "status": "retrying",
                "task_id": task.get("id"),
                "error": str(e),
            }

        # --- 6) 成功: 落盘所有状态 ---
        task["status"] = "completed"
        task["executed_at"] = now_iso
        task["error_message"] = None
        if publish_id:
            store.update_publish_record(publish_id, {
                "status": "published",
                "url": result.get("url"),
                "platform_publish_id": result.get("platform_publish_id"),
                "attempted_at": now_iso,
                "error_message": None,
                "video_id": video_id,
                "account_id": account_id,
            })
        if content_id:
            store.update_content(content_id, {"status": "published"})

        return {
            "status": "published",
            "task_id": task.get("id"),
            "publish_id": publish_id,
            "platform_publish_id": result.get("platform_publish_id"),
            "url": result.get("url"),
        }

    def _mark_failed(
        self,
        task: Dict[str, Any],
        publish_id: Optional[str],
        content_id: Optional[str],
        error: str,
        permanent: bool = True,
    ) -> Dict[str, Any]:
        """统一失败处理:标 task failed + publish_record failed + (optional) content failed"""
        now_iso = datetime.now().isoformat()
        task["status"] = "failed"
        task["executed_at"] = now_iso
        task["error_message"] = error[:500]
        if publish_id:
            store.update_publish_record(publish_id, {
                "status": "failed",
                "error_message": error[:500],
                "attempted_at": now_iso,
            })
        # 内容状态: 只有当永久失败才推回 draft, 否则让重试
        if permanent and content_id:
            try:
                store.update_content(content_id, {"status": "failed"})
            except Exception:
                pass
        return {
            "status": "failed",
            "task_id": task.get("id"),
            "publish_id": publish_id,
            "error": error[:500],
        }

    # ============================================================
    # 周期任务
    # ============================================================
    async def _run_due_tasks(self) -> int:
        """执行到期的调度任务,返回成功执行数。"""
        now = datetime.now()
        executed = 0
        # 拍快照避免并发改
        for task in list(store.scheduled_tasks):
            if task.get("status") != "pending":
                continue
            try:
                scheduled = datetime.fromisoformat(task["scheduled_time"])
            except (ValueError, TypeError, KeyError):
                continue
            if scheduled <= now:
                result = await self._dispatch_task(task)
                if result.get("status") in ("published", "failed", "retrying"):
                    executed += 1
                    logger.info(
                        "task %s → %s (%s)",
                        task.get("id"), result.get("status"), result.get("error", ""),
                    )
        return executed

    async def _loop(self):
        logger.info(f"Scheduler loop started (interval={self.interval}s)")
        self.running = True
        while not self._stop_event.is_set():
            try:
                count = await self._run_due_tasks()
                if count > 0:
                    logger.info(f"Scheduler executed {count} task(s)")
            except Exception as e:
                logger.exception(f"Scheduler loop error: {e}")
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval)
            except asyncio.TimeoutError:
                pass
        self.running = False
        logger.info("Scheduler loop stopped")

    def start(self):
        if self._task is None or self._task.done():
            self._stop_event.clear()
            self._task = asyncio.create_task(self._loop())

    async def stop(self):
        self._stop_event.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=5)
            except asyncio.TimeoutError:
                self._task.cancel()

    # ============================================================
    # 立即发布(供前端 "立即发布" 按钮)
    # ============================================================
    async def publish_now(
        self,
        content_id: str,
        platform: str,
        account_id: str,
        video_id: str,
    ) -> Dict[str, Any]:
        """不走 scheduled_time,立即派发一次。返回 dispatch summary。"""
        # 先建 publish_record(pending),然后调 dispatch
        # 拿到 dispatch 结果再 update publish_record
        # 这里为了不重复建记录, dispatch 自己会去找 publish_id
        # 所以先建一条临时 task 让 dispatch 走完整路径
        task = store.add_scheduled_task({
            "content_id": content_id,
            "platform": platform,
            "account_id": account_id,
            "video_id": video_id,
            "scheduled_time": datetime.now().isoformat(),  # 立刻到期
            "status": "pending",
        })
        # publish_id 暂时没有(用户从 publish-now 还没建 publish_record)
        # 但 adapter 需要 publish_id 写回 url。简化: publish-now 自己建 publish_record,
        # 然后传给 dispatch。改造 dispatch 让 publish_id 可选。
        # 这里用 task["id"] 作为 publish_id 反向引用
        publish_record = store.add_publish_record({
            "content_id": content_id,
            "content_title": (store.get_content(content_id) or {}).get("title"),
            "platform": platform,
            "account_id": account_id,
            "video_id": video_id,
            "scheduled_time": None,
            "status": "pending",
        })
        task["publish_id"] = publish_record["publish_id"]
        return await self._dispatch_task(task, allow_retry=False)

    # ============================================================
    # P0-1: 公众号图文立即派发(独立路径,不动视频 _dispatch_task)
    # ============================================================
    async def publish_wechat_now(
        self, content_id: str, account_id: str,
    ) -> Dict[str, Any]:
        """公众号图文立即派发端到端。

        流程:
          1. 查 content + account
          2. 解析封面:content.image_id → store.get_image → image_url
             - 本地路径 → 校验后用
             - http(s):// → wechat_cdn.download_image 落到 STORAGE_DIR/images/wechat_inline/
             - 没有 → 返 failed "公众号 image-text 强制需要封面图"
          3. 建 publish_record(status="publishing")
          4. try: 调 WeChatAdapter.publish_article_full_auto
          5. update publish_record + (成功时)content.status="published"
          6. except 全部吞,record 记 failed

        跟视频 _dispatch_task 区别:
          - 不要 video / cookie_path
          - 不走 _dispatch_task(那路径假定 upload_video)
        """
        from app.platforms.wechat import WeChatAdapter
        from app.services.wechat_cdn import download_image, get_inline_dir

        content = store.get_content(content_id)
        account = store.get_account(account_id)
        if not content:
            return {"status": "failed", "error_message": f"content {content_id} not found"}
        if not account:
            return {"status": "failed", "error_message": f"account {account_id} not found"}
        if account.get("platform") != "wechat":
            return {"status": "failed", "error_message": (
                f"账号 platform={account.get('platform')} 不是公众号"
            )}

        # 先建 record
        record = store.add_publish_record({
            "content_id": content_id,
            "content_title": content.get("title"),
            "platform": "wechat",
            "account_id": account_id,
            "video_id": None,
            "scheduled_time": None,
            "status": "publishing",
            "attempted_at": datetime.now().isoformat(),
        })

        result: Dict[str, Any] = {"status": "failed", "error_message": None}

        try:
            # 解析封面
            cover_local = self._resolve_wechat_cover(content)
            if not cover_local:
                result["error_message"] = "公众号 image-text 强制需要封面图(请在 content 上设 image_id 或 image_url)"
                store.update_publish_record(record["publish_id"], {
                    "status": "failed",
                    "error_message": result["error_message"],
                })
                return result

            adapter = WeChatAdapter(account)
            full_result = await adapter.publish_article_full_auto(
                title=content.get("title", ""),
                body_html=content.get("body", ""),
                cover_image_path=cover_local,
            )
            result = full_result
            # 对外契约统一用 "url"(跟视频流 publish_now 一致),内部 adapter 叫 article_url
            if "article_url" in result and "url" not in result:
                result = {**result, "url": result.get("article_url")}

            # 写回 record
            update: Dict[str, Any] = {
                "status": full_result["status"],
                "url": full_result.get("article_url"),
                "platform_publish_id": full_result.get("platform_publish_id"),
                "draft_media_id": full_result.get("draft_media_id"),
                "freepublish_id": full_result.get("freepublish_id"),
                "freepublish_status": full_result.get("freepublish_status"),
                "thumb_media_id": full_result.get("thumb_media_id"),
                "error_message": full_result.get("error_message"),
                "attempted_at": datetime.now().isoformat(),
            }
            store.update_publish_record(record["publish_id"], update)

            # 成功时更新 content
            if full_result["status"] == "published":
                store.update_content(content_id, {"status": "published"})

            return result

        except Exception as e:
            err = f"{type(e).__name__}: {e}"[:500]
            result = {"status": "failed", "error_message": err}
            try:
                store.update_publish_record(record["publish_id"], {
                    "status": "failed",
                    "error_message": err,
                    "attempted_at": datetime.now().isoformat(),
                })
            except Exception:
                pass
            return result

    def _resolve_wechat_cover(self, content: Dict[str, Any]) -> Optional[str]:
        """从 content 拿封面图本地路径(下载远程 → 本地)。

        优先用 content.image_id → store.images[].image_url
        否则用 content.thumbnail_url / content.image_url(冗余)
        """
        from app.services.wechat_cdn import download_image, get_inline_dir
        import asyncio
        from pathlib import Path

        cover_url: Optional[str] = None
        image_id = content.get("image_id")
        if image_id:
            img = store.get_image(image_id)
            if img:
                cover_url = img.get("image_url")
        if not cover_url:
            cover_url = content.get("thumbnail_url") or content.get("image_url")
        if not cover_url:
            return None

        if cover_url.startswith("http://") or cover_url.startswith("https://"):
            # 远程 → 下载到本地(同步执行,publish_wechat_now 是 async)
            return asyncio.get_event_loop().run_until_complete(
                download_image(cover_url, get_inline_dir())
            )
        # 本地路径
        if Path(cover_url).exists():
            return cover_url
        return None


# -------- helpers --------

def Path_safe(p) -> bool:
    """'safe' cookie 路径检查:文件存在 + 是文件(不是目录/不存在都算 not-safe)。"""
    from pathlib import Path
    if not p:
        return False
    try:
        path = Path(p)
        return path.is_file()
    except Exception:
        return False


# 全局单例
scheduler_loop = SchedulerLoop(interval_seconds=30)
