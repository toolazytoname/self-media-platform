# 后台调度任务循环
# 在应用启动时创建 asyncio 任务，每 30 秒扫描一次待执行任务
import asyncio
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from app.store import store

logger = logging.getLogger("scheduler")


class SchedulerLoop:
    """简单的 in-process 调度循环"""

    def __init__(self, interval_seconds: int = 30):
        self.interval = interval_seconds
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self.running = False

    async def _run_due_tasks(self) -> int:
        """执行到期的调度任务"""
        now = datetime.now()
        executed = 0
        for task in store.scheduled_tasks:
            if task.get("status") != "pending":
                continue
            try:
                scheduled = datetime.fromisoformat(task["scheduled_time"])
            except (ValueError, TypeError, KeyError):
                continue
            if scheduled <= now:
                task["status"] = "running"
                # 模拟执行：标记为完成
                task["executed_at"] = now.isoformat()
                task["status"] = "completed"
                # 同步 publish_records
                pid = task.get("publish_id")
                if pid:
                    store.update_publish_record(pid, {
                        "status": "published",
                        "executed_at": now.isoformat(),
                    })
                # 同步关联内容状态
                cid = task.get("content_id")
                if cid:
                    store.update_content(cid, {"status": "published"})
                executed += 1
                logger.info(f"Scheduler executed task {task.get('id')}")
        return executed

    async def _loop(self):
        """主循环"""
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
        """启动后台循环（不阻塞）"""
        if self._task is None or self._task.done():
            self._stop_event.clear()
            self._task = asyncio.create_task(self._loop())

    async def stop(self):
        """停止后台循环"""
        self._stop_event.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=5)
            except asyncio.TimeoutError:
                self._task.cancel()


# 全局单例
scheduler_loop = SchedulerLoop(interval_seconds=30)
