# 共享内存存储
# 用于在多个 API 模块间共享数据。生产环境会替换为数据库。

from typing import Dict, List, Any
from datetime import datetime
import uuid


class Store:
    """进程级共享存储。"""

    def __init__(self):
        # 用户
        self.users: List[Dict[str, Any]] = []
        # 内容
        self.contents: List[Dict[str, Any]] = []
        # 选题
        self.topics: List[Dict[str, Any]] = []
        # 素材
        self.materials: List[Dict[str, Any]] = []
        # 审核任务
        self.review_tasks: List[Dict[str, Any]] = []
        # 平台账号
        self.platform_accounts: List[Dict[str, Any]] = []
        # 发布记录
        self.publish_records: List[Dict[str, Any]] = []
        # 调度任务
        self.scheduled_tasks: List[Dict[str, Any]] = []
        # 内容模板
        self.templates: List[Dict[str, Any]] = []
        # AIGC 图片 (image gen)
        self.images: List[Dict[str, Any]] = []
        # AIGC 视频 (video gen) — Phase 2
        self.videos: List[Dict[str, Any]] = []

    # ============ AIGC Images ============
    def add_image(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item["id"] = item.get("id") or f"img_{uuid.uuid4().hex[:10]}"
        item.setdefault("created_at", datetime.now().isoformat())
        self.images.append(item)
        return item

    def list_images(self, limit: int = 50) -> List[Dict[str, Any]]:
        return list(reversed(self.images[-limit:]))

    def get_image(self, image_id: str) -> Dict[str, Any] | None:
        for i in self.images:
            if i.get("id") == image_id:
                return i
        return None

    def delete_image(self, image_id: str) -> bool:
        for i, item in enumerate(self.images):
            if item.get("id") == image_id:
                self.images.pop(i)
                return True
        return False

    # ============ AIGC Videos (Phase 2) ============
    def add_video(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item["id"] = item.get("id") or f"vid_{uuid.uuid4().hex[:10]}"
        item.setdefault("created_at", datetime.now().isoformat())
        self.videos.append(item)
        return item

    def list_videos(self, limit: int = 50) -> List[Dict[str, Any]]:
        return list(reversed(self.videos[-limit:]))

    def get_video(self, video_id: str) -> Dict[str, Any] | None:
        for v in self.videos:
            if v.get("id") == video_id:
                return v
        return None

    def delete_video(self, video_id: str) -> bool:
        """删除记录,返回被删的 video 完整 dict(便于 caller 清理磁盘文件)。"""
        for i, v in enumerate(self.videos):
            if v.get("id") == video_id:
                removed = self.videos.pop(i)
                return removed
        return None

    # ============ Users ============
    def add_user(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item["created_at"] = item.get("created_at") or datetime.now().isoformat()
        self.users.append(item)
        return item

    def get_user(self, username: str) -> Dict[str, Any] | None:
        for u in self.users:
            if u.get("username") == username:
                return u
        return None

    def list_users(self) -> List[Dict[str, Any]]:
        return [self._sanitize_user(u) for u in self.users]

    @staticmethod
    def _sanitize_user(u: Dict[str, Any]) -> Dict[str, Any]:
        """去掉敏感字段"""
        return {k: v for k, v in u.items() if k != "password_hash"}

    # ============ Templates ============
    def add_template(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item["id"] = item.get("id") or f"tpl_{uuid.uuid4().hex[:8]}"
        item.setdefault("created_at", datetime.now().isoformat())
        self.templates.append(item)
        return item

    def list_templates(self, category: str = None) -> List[Dict[str, Any]]:
        if category:
            return [t for t in self.templates if t.get("category") == category]
        return list(self.templates)

    def get_template(self, template_id: str) -> Dict[str, Any] | None:
        for t in self.templates:
            if t.get("id") == template_id:
                return t
        return None

    def update_template(self, template_id: str, update: Dict[str, Any]) -> Dict[str, Any] | None:
        for t in self.templates:
            if t.get("id") == template_id:
                for k, v in update.items():
                    if v is not None:
                        t[k] = v
                return t
        return None

    def delete_template(self, template_id: str) -> bool:
        for i, t in enumerate(self.templates):
            if t.get("id") == template_id:
                self.templates.pop(i)
                return True
        return False

    # ============ Content ============
    def add_content(self, item: Dict[str, Any]) -> Dict[str, Any]:
        if "id" not in item or not item["id"]:
            item["id"] = f"content_{len(self.contents) + 1}_{uuid.uuid4().hex[:6]}"
        now = datetime.now().isoformat()
        item.setdefault("status", "draft")
        item.setdefault("created_at", now)
        item["updated_at"] = now
        self.contents.append(item)
        return item

    def list_contents(self, skip: int = 0, limit: int = 20, status: str = None,
                      platform: str = None, keyword: str = None) -> List[Dict[str, Any]]:
        results = self.contents
        if status:
            results = [c for c in results if c.get("status") == status]
        if platform:
            results = [c for c in results if c.get("platform") == platform]
        if keyword:
            kw = keyword.lower()
            results = [c for c in results
                       if kw in (c.get("title") or "").lower()
                       or kw in (c.get("body") or "").lower()]
        return results[skip:skip + limit]

    def get_content(self, content_id: str) -> Dict[str, Any] | None:
        for c in self.contents:
            if c.get("id") == content_id:
                return c
        return None

    def update_content(self, content_id: str, update: Dict[str, Any]) -> Dict[str, Any] | None:
        for c in self.contents:
            if c.get("id") == content_id:
                for k, v in update.items():
                    if v is not None:
                        c[k] = v
                c["updated_at"] = datetime.now().isoformat()
                return c
        return None

    def delete_content(self, content_id: str) -> bool:
        for i, c in enumerate(self.contents):
            if c.get("id") == content_id:
                self.contents.pop(i)
                return True
        return False

    # ============ Topic ============
    def add_topic(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item["id"] = item.get("id") or str(uuid.uuid4())
        item.setdefault("status", "active")
        item.setdefault("created_at", datetime.now().isoformat())
        self.topics.append(item)
        return item

    def get_topic(self, topic_id: str) -> Dict[str, Any] | None:
        for t in self.topics:
            if t.get("id") == topic_id:
                return t
        return None

    def list_topics(self, status: str = None) -> List[Dict[str, Any]]:
        if status:
            return [t for t in self.topics if t.get("status") == status]
        return list(self.topics)

    def update_topic(self, topic_id: str, update: Dict[str, Any]) -> Dict[str, Any] | None:
        for t in self.topics:
            if t.get("id") == topic_id:
                for k, v in update.items():
                    if v is not None:
                        t[k] = v
                return t
        return None

    def delete_topic(self, topic_id: str) -> bool:
        for i, t in enumerate(self.topics):
            if t.get("id") == topic_id:
                self.topics.pop(i)
                return True
        return False

    # ============ Material ============
    def add_material(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item["id"] = item.get("id") or str(uuid.uuid4())
        item.setdefault("created_at", datetime.now().isoformat())
        self.materials.append(item)
        return item

    def get_material(self, material_id: str) -> Dict[str, Any] | None:
        for m in self.materials:
            if m.get("id") == material_id:
                return m
        return None

    def list_materials(self, type_: str = None) -> List[Dict[str, Any]]:
        if type_:
            return [m for m in self.materials if m.get("type") == type_]
        return list(self.materials)

    def update_material(self, material_id: str, update: Dict[str, Any]) -> Dict[str, Any] | None:
        for m in self.materials:
            if m.get("id") == material_id:
                for k, v in update.items():
                    if v is not None:
                        m[k] = v
                return m
        return None

    def delete_material(self, material_id: str) -> bool:
        for i, m in enumerate(self.materials):
            if m.get("id") == material_id:
                self.materials.pop(i)
                return True
        return False

    # ============ Review ============
    def add_review(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item["id"] = item.get("id") or str(uuid.uuid4())
        item.setdefault("status", "pending")
        item.setdefault("created_at", datetime.now().isoformat())
        self.review_tasks.append(item)
        return item

    def list_reviews(self, status: str = None) -> List[Dict[str, Any]]:
        if status:
            return [r for r in self.review_tasks if r.get("status") == status]
        return list(self.review_tasks)

    def update_review(self, task_id: str, status: str, comment: str = None) -> Dict[str, Any] | None:
        for r in self.review_tasks:
            if r.get("id") == task_id:
                r["status"] = status
                if comment is not None:
                    r["reviewer_comment"] = comment
                r["reviewed_at"] = datetime.now().isoformat()
                return r
        return None

    # ============ Platform Accounts ============
    def add_account(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item["id"] = item.get("id") or str(uuid.uuid4())
        item.setdefault("status", "active")
        item.setdefault("created_at", datetime.now().isoformat())
        self.platform_accounts.append(item)
        return item

    def list_accounts(self) -> List[Dict[str, Any]]:
        return list(self.platform_accounts)

    def get_account(self, account_id: str) -> Dict[str, Any] | None:
        """Phase 2: 给 scheduler 查 credentials 用。"""
        for a in self.platform_accounts:
            if a.get("id") == account_id:
                return a
        return None

    def update_account(self, account_id: str, update: Dict[str, Any]) -> Dict[str, Any] | None:
        """Phase 2: 替换 PUT /platforms/accounts/{id} 原本手写的 in-place 逻辑。"""
        for a in self.platform_accounts:
            if a.get("id") == account_id:
                for k, v in update.items():
                    if v is not None:
                        a[k] = v
                return a
        return None

    def delete_account(self, account_id: str) -> bool:
        for i, a in enumerate(self.platform_accounts):
            if a.get("id") == account_id:
                self.platform_accounts.pop(i)
                return True
        return False

    # ============ Publish Records ============
    def add_publish_record(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item["publish_id"] = item.get("publish_id") or str(uuid.uuid4())
        item.setdefault("status", "pending")
        item.setdefault("created_at", datetime.now().isoformat())
        # Phase 2 扩展字段:由 adapter 写入
        item.setdefault("platform_publish_id", None)  # 平台侧返回的 ID / URL
        item.setdefault("url", None)                  # 平台侧发布后的公开 URL
        item.setdefault("error_message", None)        # 失败时的原因
        item.setdefault("attempted_at", None)         # 上次尝试时间
        item.setdefault("video_id", None)             # 关联的视频记录 id
        item.setdefault("account_id", None)           # 关联的平台账号 id
        self.publish_records.append(item)
        return item

    def list_publish_records(self, status: str = None) -> List[Dict[str, Any]]:
        if status:
            return [p for p in self.publish_records if p.get("status") == status]
        return list(self.publish_records)

    def get_publish_record(self, publish_id: str) -> Dict[str, Any] | None:
        for p in self.publish_records:
            if p.get("publish_id") == publish_id:
                return p
        return None

    def update_publish_record(self, publish_id: str, update: Dict[str, Any]) -> Dict[str, Any] | None:
        for p in self.publish_records:
            if p.get("publish_id") == publish_id:
                for k, v in update.items():
                    if v is not None:
                        p[k] = v
                return p
        return None

    # ============ Scheduled Tasks ============
    def add_scheduled_task(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item["id"] = item.get("id") or str(uuid.uuid4())
        item.setdefault("status", "pending")
        # Phase 2 扩展字段
        item.setdefault("attempt_count", 0)    # 已尝试次数,scheduler 用
        item.setdefault("account_id", None)   # 关联平台账号
        item.setdefault("video_id", None)     # 关联视频记录
        item.setdefault("error_message", None) # 上次失败的错误
        self.scheduled_tasks.append(item)
        return item

    def list_scheduled_tasks(self, status: str = None) -> List[Dict[str, Any]]:
        if status:
            return [t for t in self.scheduled_tasks if t.get("status") == status]
        return list(self.scheduled_tasks)

    def get_scheduled_task(self, task_id: str) -> Dict[str, Any] | None:
        for t in self.scheduled_tasks:
            if t.get("id") == task_id:
                return t
        return None

    def update_scheduled_task(self, task_id: str, update: Dict[str, Any]) -> Dict[str, Any] | None:
        for t in self.scheduled_tasks:
            if t.get("id") == task_id:
                for k, v in update.items():
                    if v is not None:
                        t[k] = v
                return t
        return None

    def delete_scheduled_task(self, task_id: str) -> bool:
        for i, t in enumerate(self.scheduled_tasks):
            if t.get("id") == task_id:
                self.scheduled_tasks.pop(i)
                return True
        return False

    # ============ Stats ============
    def get_stats(self) -> Dict[str, int]:
        # 平台发布分布
        platform_distribution: Dict[str, int] = {}
        for p in self.publish_records:
            pf = p.get("platform", "unknown")
            platform_distribution[pf] = platform_distribution.get(pf, 0) + 1
        return {
            "topics_total": len(self.topics),
            "materials_total": len(self.materials),
            "review_pending": len([r for r in self.review_tasks if r.get("status") == "pending"]),
            "content_total": len(self.contents),
            "content_draft": len([c for c in self.contents if c.get("status") == "draft"]),
            "content_pending": len([c for c in self.contents if c.get("status") == "pending"]),
            "content_published": len([c for c in self.contents if c.get("status") == "published"]),
            "platforms_connected": len(set(a.get("platform") for a in self.platform_accounts)),
            "publish_records_total": len(self.publish_records),
            "scheduled_tasks_total": len(self.scheduled_tasks),
            "platform_distribution": platform_distribution,
        }


# 全局单例
store = Store()
