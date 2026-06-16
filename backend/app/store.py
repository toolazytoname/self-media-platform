"""
进程级共享存储 + SQLite write-through cache

- 内存 dict 仍为热路径(读操作零开销)
- 每次 add/update/delete 同步写一份到 SQLite(单条 < 1ms,无感)
- 启动时从 SQLite 加载回内存(app.db.init_db.load_into_store)
- 105+ 个调用点 API 保持 sync 兼容

生产替换 Alembic 时,只需把 upsert_row/delete_row 换成 migration-aware 版本
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid


# list_attr -> ORM 模型类(供 _persist_to_db / _delete_from_db 查)
_LIST_TO_MODEL_ATTR = "_LIST_TO_MODEL"


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
        # AIGC 图片
        self.images: List[Dict[str, Any]] = []
        # AIGC 视频
        self.videos: List[Dict[str, Any]] = []
        # AI 创作历史
        self.ai_creations: List[Dict[str, Any]] = []
        # 来源
        self.sources: List[Dict[str, Any]] = []
        self.source_chapters: List[Dict[str, Any]] = []
        # P0-2: 选题雷达 / 热榜
        self.hot_topics: List[Dict[str, Any]] = []
        # P1-1: 文风画像 (per-user dict, key=user_id, value=StyleProfile)
        self.user_style_profiles: Dict[str, Any] = {}

    # ============ Write-Through Helpers ============

    def _persist(self, list_attr: str, item: Dict[str, Any]) -> None:
        """把一个 dict 同步落 SQLite(upsert)。失败只 log,不抛。"""
        from app.db.init_db import upsert_row
        model = self._model_for_list(list_attr)
        if model is None:
            return
        row_id = item.get("id")
        if not row_id:
            return
        # 关键修复:把"显式列"字段(status/type/platform/...)也塞进 data,
        # 这样 load 时只需从 data JSON 还原,不需要 ORM 列合并
        upsert_row(model, row_id, item)

    def _delete_persist(self, list_attr: str, row_id: str) -> None:
        from app.db.init_db import delete_row
        model = self._model_for_list(list_attr)
        if model is None:
            return
        delete_row(model, row_id)

    def _model_for_list(self, list_attr: str):
        """list_attr -> ORM 模型类的查找表(懒加载)"""
        cache = getattr(self, _LIST_TO_MODEL_ATTR, None)
        if cache is None:
            from app.db.models import (
                UserRow, ContentRow, TopicRow, MaterialRow, ReviewTaskRow,
                PlatformAccountRow, PublishRecordRow, ScheduledTaskRow,
                TemplateRow, ImageRow, VideoRow, AICreationRow,
                SourceRow, SourceChapterRow,
            )
            cache = {
                "users": UserRow,
                "contents": ContentRow,
                "topics": TopicRow,
                "materials": MaterialRow,
                "review_tasks": ReviewTaskRow,
                "platform_accounts": PlatformAccountRow,
                "publish_records": PublishRecordRow,
                "scheduled_tasks": ScheduledTaskRow,
                "templates": TemplateRow,
                "images": ImageRow,
                "videos": VideoRow,
                "ai_creations": AICreationRow,
                "sources": SourceRow,
                "source_chapters": SourceChapterRow,
            }
            setattr(self, _LIST_TO_MODEL_ATTR, cache)
        return cache.get(list_attr)

    # ============ AIGC Images ============
    def add_image(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item["id"] = item.get("id") or f"img_{uuid.uuid4().hex[:10]}"
        item.setdefault("created_at", datetime.now().isoformat())
        self.images.append(item)
        self._persist("images", item)
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
                self._delete_persist("images", image_id)
                return True
        return False

    # ============ AIGC Videos ============
    def add_video(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item["id"] = item.get("id") or f"vid_{uuid.uuid4().hex[:10]}"
        item.setdefault("created_at", datetime.now().isoformat())
        self.videos.append(item)
        self._persist("videos", item)
        return item

    def list_videos(self, limit: int = 50) -> List[Dict[str, Any]]:
        return list(reversed(self.videos[-limit:]))

    def get_video(self, video_id: str) -> Dict[str, Any] | None:
        for v in self.videos:
            if v.get("id") == video_id:
                return v
        return None

    def delete_video(self, video_id: str) -> bool:
        for i, v in enumerate(self.videos):
            if v.get("id") == video_id:
                removed = self.videos.pop(i)
                self._delete_persist("videos", video_id)
                return removed
        return None

    # ============ AI Creations ============
    def add_ai_creation(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item["id"] = item.get("id") or f"aic_{uuid.uuid4().hex[:10]}"
        item.setdefault("created_at", datetime.now().isoformat())
        self.ai_creations.append(item)
        self._persist("ai_creations", item)
        return item

    def list_creations(
        self, type: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        items = self.ai_creations
        if type:
            items = [c for c in items if c.get("type") == type]
        return list(reversed(items[-limit:]))

    def get_creation(self, creation_id: str) -> Dict[str, Any] | None:
        for c in self.ai_creations:
            if c.get("id") == creation_id:
                return c
        return None

    def delete_creation(self, creation_id: str) -> bool:
        for i, c in enumerate(self.ai_creations):
            if c.get("id") == creation_id:
                self.ai_creations.pop(i)
                self._delete_persist("ai_creations", creation_id)
                return True
        return False

    # ============ Users ============
    def add_user(self, item: Dict[str, Any]) -> Dict[str, Any]:
        # 给 user 一个 id(用 username 当主键,稳定可查)
        item["id"] = item.get("id") or item.get("username") or str(uuid.uuid4())
        item["created_at"] = item.get("created_at") or datetime.now().isoformat()
        self.users.append(item)
        self._persist("users", item)
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
        self._persist("templates", item)
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
                self._persist("templates", t)
                return t
        return None

    def delete_template(self, template_id: str) -> bool:
        for i, t in enumerate(self.templates):
            if t.get("id") == template_id:
                self.templates.pop(i)
                self._delete_persist("templates", template_id)
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
        self._persist("contents", item)
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
                self._persist("contents", c)
                return c
        return None

    def delete_content(self, content_id: str) -> bool:
        for i, c in enumerate(self.contents):
            if c.get("id") == content_id:
                self.contents.pop(i)
                self._delete_persist("contents", content_id)
                return True
        return False

    # ============ Topic ============
    def add_topic(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item["id"] = item.get("id") or str(uuid.uuid4())
        item.setdefault("status", "active")
        item.setdefault("created_at", datetime.now().isoformat())
        self.topics.append(item)
        self._persist("topics", item)
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
                self._persist("topics", t)
                return t
        return None

    def delete_topic(self, topic_id: str) -> bool:
        for i, t in enumerate(self.topics):
            if t.get("id") == topic_id:
                self.topics.pop(i)
                self._delete_persist("topics", topic_id)
                return True
        return False

    # ============ Material ============
    def add_material(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item["id"] = item.get("id") or str(uuid.uuid4())
        item.setdefault("created_at", datetime.now().isoformat())
        self.materials.append(item)
        self._persist("materials", item)
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
                self._persist("materials", m)
                return m
        return None

    def delete_material(self, material_id: str) -> bool:
        for i, m in enumerate(self.materials):
            if m.get("id") == material_id:
                self.materials.pop(i)
                self._delete_persist("materials", material_id)
                return True
        return False

    # ============ Review ============
    def add_review(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item["id"] = item.get("id") or str(uuid.uuid4())
        item.setdefault("status", "pending")
        item.setdefault("created_at", datetime.now().isoformat())
        self.review_tasks.append(item)
        self._persist("review_tasks", item)
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
                self._persist("review_tasks", r)
                return r
        return None

    # ============ Platform Accounts ============
    def add_account(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item["id"] = item.get("id") or str(uuid.uuid4())
        item.setdefault("status", "active")
        item.setdefault("created_at", datetime.now().isoformat())
        self.platform_accounts.append(item)
        self._persist("platform_accounts", item)
        return item

    def list_accounts(self) -> List[Dict[str, Any]]:
        return list(self.platform_accounts)

    def get_account(self, account_id: str) -> Dict[str, Any] | None:
        for a in self.platform_accounts:
            if a.get("id") == account_id:
                return a
        return None

    def update_account(self, account_id: str, update: Dict[str, Any]) -> Dict[str, Any] | None:
        for a in self.platform_accounts:
            if a.get("id") == account_id:
                for k, v in update.items():
                    if v is not None:
                        a[k] = v
                self._persist("platform_accounts", a)
                return a
        return None

    def delete_account(self, account_id: str) -> bool:
        for i, a in enumerate(self.platform_accounts):
            if a.get("id") == account_id:
                self.platform_accounts.pop(i)
                self._delete_persist("platform_accounts", account_id)
                return True
        return False

    # ============ Publish Records ============
    def add_publish_record(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item["publish_id"] = item.get("publish_id") or str(uuid.uuid4())
        item.setdefault("status", "pending")
        item.setdefault("created_at", datetime.now().isoformat())
        item.setdefault("platform_publish_id", None)
        item.setdefault("url", None)
        item.setdefault("error_message", None)
        item.setdefault("attempted_at", None)
        item.setdefault("video_id", None)
        item.setdefault("account_id", None)
        self.publish_records.append(item)
        # publish_id 是唯一键,同步到 id 列(ORM 主键)
        persist_item = dict(item)
        persist_item["id"] = item["publish_id"]
        self._persist("publish_records", persist_item)
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
                persist_item = dict(p)
                persist_item["id"] = publish_id
                self._persist("publish_records", persist_item)
                return p
        return None

    # ============ Scheduled Tasks ============
    def add_scheduled_task(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item["id"] = item.get("id") or str(uuid.uuid4())
        item.setdefault("status", "pending")
        item.setdefault("attempt_count", 0)
        item.setdefault("account_id", None)
        item.setdefault("video_id", None)
        item.setdefault("error_message", None)
        self.scheduled_tasks.append(item)
        self._persist("scheduled_tasks", item)
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
                self._persist("scheduled_tasks", t)
                return t
        return None

    def delete_scheduled_task(self, task_id: str) -> bool:
        for i, t in enumerate(self.scheduled_tasks):
            if t.get("id") == task_id:
                self.scheduled_tasks.pop(i)
                self._delete_persist("scheduled_tasks", task_id)
                return True
        return False

    # ============ Sources ============
    def add_source(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item["id"] = item.get("id") or f"src_{uuid.uuid4().hex[:10]}"
        item.setdefault("created_at", datetime.now().isoformat())
        self.sources.append(item)
        self._persist("sources", item)
        return item

    def list_sources(self, type: Optional[str] = None) -> List[Dict[str, Any]]:
        items = self.sources
        if type:
            items = [s for s in items if s.get("type") == type]
        return list(reversed(items))

    def get_source(self, source_id: str) -> Dict[str, Any] | None:
        for s in self.sources:
            if s.get("id") == source_id:
                return s
        return None

    def delete_source(self, source_id: str) -> bool:
        for i, s in enumerate(self.sources):
            if s.get("id") == source_id:
                self.sources.pop(i)
                self.source_chapters = [
                    c for c in self.source_chapters if c.get("source_id") != source_id
                ]
                self._delete_persist("sources", source_id)
                return True
        return False

    def add_source_chapter(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item["id"] = item.get("id") or f"sch_{uuid.uuid4().hex[:10]}"
        item.setdefault("created_at", datetime.now().isoformat())
        self.source_chapters.append(item)
        self._persist("source_chapters", item)
        return item

    def list_source_chapters(self, source_id: str) -> List[Dict[str, Any]]:
        items = [c for c in self.source_chapters if c.get("source_id") == source_id]
        items.sort(key=lambda c: c.get("chapter_index", 0))
        return items

    def get_source_chapter(self, chapter_id: str) -> Dict[str, Any] | None:
        for c in self.source_chapters:
            if c.get("id") == chapter_id:
                return c
        return None

    # ============ P0-2: 选题雷达 / 热榜 ============
    def add_hot(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item["id"] = item.get("id") or f"hot_{uuid.uuid4().hex[:10]}"
        item.setdefault("status", "new")
        item.setdefault("fetched_at", datetime.now().isoformat())
        self.hot_topics.append(item)
        # hot_topics 暂不落 SQL(无 ORM 模型);测试 + 内存够用
        return item

    def list_hot(self, platform: Optional[str] = None, status: Optional[str] = None,
                 limit: int = 50) -> List[Dict[str, Any]]:
        res = self.hot_topics
        if platform:
            res = [h for h in res if h.get("platform") == platform]
        if status:
            res = [h for h in res if h.get("status") == status]
        return list(reversed(res))[:limit]

    def get_hot(self, hot_id: str) -> Dict[str, Any] | None:
        for h in self.hot_topics:
            if h.get("id") == hot_id:
                return h
        return None

    def update_hot(self, hot_id: str, updates: Dict[str, Any]) -> Dict[str, Any] | None:
        for i, h in enumerate(self.hot_topics):
            if h.get("id") == hot_id:
                self.hot_topics[i] = {**h, **updates}
                return self.hot_topics[i]
        return None

    def delete_hot(self, hot_id: str) -> bool:
        for i, h in enumerate(self.hot_topics):
            if h.get("id") == hot_id:
                self.hot_topics.pop(i)
                return True
        return False

    # ============ Stats ============
    def get_stats(self) -> Dict[str, int]:
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
