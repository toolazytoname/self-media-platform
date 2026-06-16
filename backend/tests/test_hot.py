"""Hot API 集成测试 — TASK-P0-2 选题雷达 CRUD 端点

覆盖:
  - GET   /api/hot               列表 + 过滤 + 限制 + 鉴权
  - POST  /api/hot/refresh       抓取 + 落库
  - POST  /api/hot/rewrite/{id}  AI 改写 + 落库
  - POST  /api/hot/{id}/create-content  一键草稿
  - POST  /api/ai/hot-rewrite    AI 单独端点

约定:
  - store.hot_topics 列表直接操作(方法 add_hot 等暂未实现, RED 阶段用 list.append)
  - AI 调用 patch `app.api.hot.chat_completion` (或 _timed_chat)
  - hot_list_client patch `app.api.hot.fetch_all` / `fetch_weibo` 等
"""
import json
import time
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime


# ============ 工具函数 ============

def _register_and_login(client, username="hot_user", password="test1234"):
    """注册并登录,返 access_token。"""
    r = client.post("/api/auth/register", json={
        "username": username, "password": password, "display_name": username,
    })
    assert r.status_code in (200, 201), r.text
    r = client.post("/api/auth/login", json={
        "username": username, "password": password,
    })
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _make_hot(**overrides) -> dict:
    """构造一个 hot item dict(不调 store.add_hot — RED 阶段直接 append)"""
    item = {
        "id": f"hot_{int(time.time() * 1000) % 10_000_000:07d}",
        "platform": "weibo",
        "title": "默认标题",
        "source_url": "https://example.com/1",
        "heat_score": 1000,
        "fetched_at": datetime.now().isoformat(),
        "status": "new",
        "ai_angle": None,
        "ai_rewritten_at": None,
        "related_content_id": None,
    }
    item.update(overrides)
    return item


# ============ GET /api/hot 列表 ============

class TestListHot:
    def test_empty_returns_empty_list(self, client, fresh_store):
        """无 hot items → 200, items=[]"""
        token = _register_and_login(client)
        r = client.get("/api/hot", headers=_auth(token))
        assert r.status_code == 200, r.text
        body = r.json()
        # 允许 {"items": []} 或 [], 两种都接受
        if isinstance(body, list):
            assert body == []
        else:
            assert body.get("items") == []
            assert body.get("total", 0) == 0

    def test_returns_persisted_items(self, client, fresh_store):
        """seed 3 hot items → 返 3 条, 最新在前"""
        from app.store import store
        token = _register_and_login(client)
        for i in range(3):
            store.hot_topics.append(_make_hot(title=f"标题{i}", platform="weibo"))
        r = client.get("/api/hot", headers=_auth(token))
        assert r.status_code == 200
        body = r.json()
        items = body if isinstance(body, list) else body["items"]
        assert len(items) == 3

    def test_filter_by_platform(self, client, fresh_store):
        """seed 2 weibo + 1 zhihu → ?platform=weibo 返 2"""
        from app.store import store
        token = _register_and_login(client)
        store.hot_topics.append(_make_hot(platform="weibo", title="w1"))
        store.hot_topics.append(_make_hot(platform="weibo", title="w2"))
        store.hot_topics.append(_make_hot(platform="zhihu", title="z1"))
        r = client.get("/api/hot", params={"platform": "weibo"}, headers=_auth(token))
        assert r.status_code == 200
        items = r.json() if isinstance(r.json(), list) else r.json()["items"]
        assert len(items) == 2
        assert all(it["platform"] == "weibo" for it in items)

    def test_filter_by_status(self, client, fresh_store):
        """seed new/used/dismissed → ?status=new 返 1"""
        from app.store import store
        token = _register_and_login(client)
        store.hot_topics.append(_make_hot(status="new"))
        store.hot_topics.append(_make_hot(status="used"))
        store.hot_topics.append(_make_hot(status="dismissed"))
        r = client.get("/api/hot", params={"status": "new"}, headers=_auth(token))
        assert r.status_code == 200
        items = r.json() if isinstance(r.json(), list) else r.json()["items"]
        assert len(items) == 1
        assert items[0]["status"] == "new"

    def test_respects_limit(self, client, fresh_store):
        """seed 60 → ?limit=10 返 10"""
        from app.store import store
        token = _register_and_login(client)
        for i in range(60):
            store.hot_topics.append(_make_hot(title=f"t{i}"))
        r = client.get("/api/hot", params={"limit": 10}, headers=_auth(token))
        assert r.status_code == 200
        items = r.json() if isinstance(r.json(), list) else r.json()["items"]
        assert len(items) == 10

    def test_requires_auth(self, client, fresh_store):
        """无 Authorization → 401"""
        r = client.get("/api/hot")
        assert r.status_code == 401


# ============ POST /api/hot/refresh 抓取 ============

class TestRefreshHot:
    def test_refresh_calls_fetch_all_and_persists(self, client, fresh_store):
        """mock fetch_all 返 5 items → POST /api/hot/refresh → store 增 5, response count=5"""
        from app.store import store
        token = _register_and_login(client)
        mock_items = [_make_hot(title=f"fetched_{i}") for i in range(5)]
        with patch("app.api.hot.fetch_all", new=AsyncMock(return_value=mock_items)):
            r = client.post("/api/hot/refresh", headers=_auth(token))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("count") == 5
        assert len(store.hot_topics) == 5

    def test_refresh_handles_empty_result(self, client, fresh_store):
        """fetch_all 返 [] → 200, count=0, store 不变"""
        from app.store import store
        token = _register_and_login(client)
        with patch("app.api.hot.fetch_all", new=AsyncMock(return_value=[])):
            r = client.post("/api/hot/refresh", headers=_auth(token))
        assert r.status_code == 200, r.text
        assert r.json().get("count") == 0
        assert store.hot_topics == []

    def test_refresh_with_platform_param(self, client, fresh_store):
        """?platform=weibo → 调 fetch_weibo, 不调 fetch_all"""
        from app.store import store
        token = _register_and_login(client)
        mock_items = [_make_hot(platform="weibo", title=f"w_{i}") for i in range(3)]
        with patch("app.api.hot.fetch_weibo", new=AsyncMock(return_value=mock_items)) as fw, \
             patch("app.api.hot.fetch_all", new=AsyncMock(return_value=[])) as fa:
            r = client.post("/api/hot/refresh?platform=weibo", headers=_auth(token))
        assert r.status_code == 200, r.text
        assert r.json().get("count") == 3
        # fetch_weibo 被调, fetch_all 不该被调
        assert fw.call_count == 1
        assert fa.call_count == 0

    def test_refresh_failure_does_not_crash(self, client, fresh_store):
        """fetch_all 抛异常 → 5xx + 错误 detail, store 不留半成品"""
        from app.store import store
        token = _register_and_login(client)
        with patch("app.api.hot.fetch_all", new=AsyncMock(side_effect=Exception("aggregator down"))):
            r = client.post("/api/hot/refresh", headers=_auth(token))
        assert r.status_code >= 500
        assert "aggregator down" in r.json().get("detail", "")
        assert store.hot_topics == []


# ============ POST /api/hot/rewrite/{id} AI 改写 ============

class TestRewriteHot:
    def test_rewrite_calls_ai_and_persists_angle(self, client, fresh_store):
        """seed hot item, patch chat_completion → 返角度 → store.ai_angle 写入, response 返角度"""
        from app.store import store
        token = _register_and_login(client)
        item = _make_hot(title="DeepSeek V4 发布")
        store.hot_topics.append(item)
        with patch("app.api.hot.chat_completion", new=AsyncMock(return_value="这是一个很棒的自媒体角度")):
            r = client.post(f"/api/hot/rewrite/{item['id']}", headers=_auth(token))
        assert r.status_code == 200, r.text
        body = r.json()
        assert "angle" in body or "ai_angle" in body
        angle = body.get("angle") or body.get("ai_angle")
        assert "自媒体角度" in angle
        # store 也得写入
        persisted = next(h for h in store.hot_topics if h["id"] == item["id"])
        assert "自媒体角度" in (persisted.get("ai_angle") or "")
        assert persisted.get("ai_rewritten_at") is not None

    def test_rewrite_404_for_missing_item(self, client, fresh_store):
        token = _register_and_login(client)
        with patch("app.api.hot.chat_completion", new=AsyncMock(return_value="x")):
            r = client.post("/api/hot/rewrite/nonexistent_hot_id", headers=_auth(token))
        assert r.status_code == 404

    def test_rewrite_does_not_overwrite_existing_angle(self, client, fresh_store):
        """seed item with ai_angle='old' → 调 rewrite → angle 变成新的(覆盖)"""
        from app.store import store
        token = _register_and_login(client)
        item = _make_hot(title="t", ai_angle="old angle")
        store.hot_topics.append(item)
        with patch("app.api.hot.chat_completion", new=AsyncMock(return_value="new angle")):
            r = client.post(f"/api/hot/rewrite/{item['id']}", headers=_auth(token))
        assert r.status_code == 200
        persisted = next(h for h in store.hot_topics if h["id"] == item["id"])
        # 用户主动触发 rewrite 时应当覆盖旧值
        assert "new angle" in (persisted.get("ai_angle") or "")
        assert "old angle" not in (persisted.get("ai_angle") or "")


# ============ POST /api/hot/{id}/create-content 一键草稿 ============

class TestCreateContentFromHot:
    def test_creates_draft_content_with_ai_angle(self, client, fresh_store):
        """seed hot item(title + ai_angle) → POST → 201, content_id 返, Content 写入"""
        from app.store import store
        token = _register_and_login(client)
        item = _make_hot(
            title="热点标题 X",
            platform="weibo",
            ai_angle="角度正文 abc",
        )
        store.hot_topics.append(item)
        r = client.post(f"/api/hot/{item['id']}/create-content", headers=_auth(token))
        assert r.status_code in (200, 201), r.text
        body = r.json()
        cid = body.get("content_id") or body.get("id")
        assert cid
        # store.contents 里有这条
        c = next((c for c in store.contents if c["id"] == cid), None)
        assert c is not None
        assert c["title"] == "热点标题 X"
        assert c["body"] == "角度正文 abc"
        assert c["platform"] == "weibo"
        assert c["status"] == "draft"

    def test_create_without_ai_angle_falls_back_to_title(self, client, fresh_store):
        """seed item(无 ai_angle) → POST → body=title, 不为空"""
        from app.store import store
        token = _register_and_login(client)
        item = _make_hot(title="裸标题 Y", ai_angle=None)
        store.hot_topics.append(item)
        r = client.post(f"/api/hot/{item['id']}/create-content", headers=_auth(token))
        assert r.status_code in (200, 201), r.text
        cid = r.json().get("content_id") or r.json().get("id")
        c = next(c for c in store.contents if c["id"] == cid)
        assert c["body"] == "裸标题 Y"
        assert c["body"] != ""

    def test_create_links_back_to_hot(self, client, fresh_store):
        """创建后 hot.related_content_id 指回 content"""
        from app.store import store
        token = _register_and_login(client)
        item = _make_hot(title="t", ai_angle="a")
        store.hot_topics.append(item)
        r = client.post(f"/api/hot/{item['id']}/create-content", headers=_auth(token))
        cid = r.json().get("content_id") or r.json().get("id")
        persisted = next(h for h in store.hot_topics if h["id"] == item["id"])
        assert persisted.get("related_content_id") == cid

    def test_create_marks_hot_as_used(self, client, fresh_store):
        """创建后 hot.status='used'"""
        from app.store import store
        token = _register_and_login(client)
        item = _make_hot(title="t", ai_angle="a", status="new")
        store.hot_topics.append(item)
        r = client.post(f"/api/hot/{item['id']}/create-content", headers=_auth(token))
        assert r.status_code in (200, 201)
        persisted = next(h for h in store.hot_topics if h["id"] == item["id"])
        assert persisted.get("status") == "used"

    def test_create_404_for_missing_item(self, client, fresh_store):
        token = _register_and_login(client)
        r = client.post("/api/hot/no_such_hot_id/create-content", headers=_auth(token))
        assert r.status_code == 404
        # 必须有 detail 字段,且提到 hot 找不到(不是路由不存在的通用 'Not Found')
        body = r.json()
        assert "detail" in body
        assert "hot" in body["detail"].lower()


# ============ POST /api/ai/hot-rewrite AI 单独端点 ============

class TestAiHotRewriteEndpoint:
    def _auth_client(self, client):
        return _auth(_register_and_login(client))

    def test_returns_n_angles(self, client, fresh_store):
        """request n=3, mock chat_completion 返 3 行 → response 含 3 个 angle"""
        token = self._auth_client(client)
        numbered = "1. 角度一\n2. 角度二\n3. 角度三"
        with patch("app.api.ai_generate.chat_completion", new=AsyncMock(return_value=numbered)):
            r = client.post(
                "/api/ai/hot-rewrite",
                headers=_auth(token),
                json={"hot_title": "某热点", "platform": "weibo", "n": 3, "tone": "casual"},
            )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "angles" in body
        assert len(body["angles"]) == 3
        # 每条都得有 text
        for a in body["angles"]:
            assert "text" in a
            assert a["text"]

    def test_passes_provider_and_model_through(self, client, fresh_store):
        """request provider='claude' model='claude-haiku-4-5' → chat_completion 被以这俩参数调"""
        token = self._auth_client(client)
        captured = {}

        async def fake_chat(messages, model=None, provider=None, **kwargs):
            captured["model"] = model
            captured["provider"] = provider
            return "1. 角度X"

        with patch("app.api.ai_generate.chat_completion", new=fake_chat):
            r = client.post(
                "/api/ai/hot-rewrite",
                headers=_auth(token),
                json={
                    "hot_title": "某热点",
                    "platform": "weibo",
                    "n": 1,
                    "tone": "casual",
                    "provider": "claude",
                    "model": "claude-haiku-4-5",
                },
            )
        assert r.status_code == 200, r.text
        assert captured.get("provider") == "claude"
        assert captured.get("model") == "claude-haiku-4-5"

    def test_records_ai_creation(self, client, fresh_store):
        """调完 hot-rewrite 后 store.ai_creations 多一条 type='hot_angle' 的记录"""
        from app.store import store
        token = self._auth_client(client)
        before = len(store.ai_creations)
        with patch("app.api.ai_generate.chat_completion", new=AsyncMock(return_value="1. 角度")):
            r = client.post(
                "/api/ai/hot-rewrite",
                headers=_auth(token),
                json={"hot_title": "某热点", "platform": "weibo", "n": 1, "tone": "casual"},
            )
        assert r.status_code == 200, r.text
        after = len(store.ai_creations)
        assert after == before + 1, f"ai_creations 应当 +1, before={before} after={after}"
        latest = store.ai_creations[-1]
        assert latest.get("type") == "hot_angle"
