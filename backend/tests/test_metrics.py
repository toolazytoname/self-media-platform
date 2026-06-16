"""数据回流闭环 — P1-2 测试

策略(快速可行版本):
- 手工录入为主(各平台反爬限制大,自动抓取留 TODO)
- 公开数据抓取:知乎热榜等(可选)
- 趋势 API: top 内容 / 最佳发布时段

覆盖:
  - store.publish_metrics dict 持久化
  - POST /api/metrics/record  录入数据
  - GET  /api/metrics/content/{id}  取某 content 指标
  - GET  /api/metrics/trending  top 表现内容
  - GET  /api/metrics/best-time  最佳发布时段统计
"""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _register_login(client, username="metrics_user"):
    client.post("/api/auth/register", json={
        "username": username, "password": "test1234", "display_name": username,
    })
    r = client.post("/api/auth/login", json={"username": username, "password": "test1234"})
    return r.json()["access_token"]


# ============ Service: 录入 / 趋势计算 / 最佳时段 ============

class TestMetricsService:
    def test_record_metrics(self, fresh_store):
        from app.services.metrics_service import record_metrics, get_metrics
        from app.store import store
        store.add_content({
            "title": "t1", "body": "b1", "tags": [], "platform": "wechat",
        })
        cid = store.contents[0]["id"]
        result = record_metrics(cid, views=100, likes=10, comments=5, shares=2)
        assert result["content_id"] == cid
        assert result["views"] == 100
        # 已落库
        m = get_metrics(cid)
        assert m is not None
        assert m["views"] == 100

    def test_record_metrics_overwrites(self, fresh_store):
        """重复录入覆盖(同 content_id 后写的覆盖前)"""
        from app.services.metrics_service import record_metrics, get_metrics
        from app.store import store
        store.add_content({
            "title": "t1", "body": "b1", "tags": [], "platform": "wechat",
        })
        cid = store.contents[0]["id"]
        record_metrics(cid, views=100)
        record_metrics(cid, views=200)  # 覆盖
        assert get_metrics(cid)["views"] == 200

    def test_get_metrics_none_for_missing(self, fresh_store):
        from app.services.metrics_service import get_metrics
        assert get_metrics("non_existent") is None

    def test_trending_top_by_views(self, fresh_store):
        """trending 按 views 倒序 top N"""
        from app.services.metrics_service import record_metrics, get_trending
        from app.store import store
        for i in range(5):
            store.add_content({
                "title": f"t{i}", "body": "b", "tags": [], "platform": "wechat",
            })
            record_metrics(store.contents[i]["id"], views=i * 100)
        top = get_trending(top_n=3)
        assert len(top) == 3
        # 倒序:views=400, 300, 200
        assert [m["views"] for m in top] == [400, 300, 200]

    def test_trending_filter_by_platform(self, fresh_store):
        """trending 可按平台过滤"""
        from app.services.metrics_service import record_metrics, get_trending
        from app.store import store
        for i, plat in enumerate(["wechat", "wechat", "douyin", "douyin"]):
            cid = store.add_content({
                "title": f"t{i}", "body": "b", "tags": [], "platform": plat,
            })["id"]
            record_metrics(cid, views=(i + 1) * 100, platform=plat)
        # 只看 wechat
        top = get_trending(top_n=10, platform="wechat")
        assert all(m.get("platform") == "wechat" for m in top)
        assert len(top) == 2

    def test_best_time_from_history(self, fresh_store):
        """基于历史 publish_records 统计"最佳发布时段"(小时)"""
        from app.services.metrics_service import record_metrics, compute_best_time
        from app.store import store
        # 模拟 3 篇: 14:00 100 views, 9:00 50 views, 14:00 200 views
        for i, views, hour in [(1, 100, 14), (2, 50, 9), (3, 200, 14)]:
            store.add_publish_record({
                "id": f"pub_{i}",
                "content_id": f"c{i}",
                "platform": "wechat",
                "status": "published",
                "scheduled_time": datetime(2026, 1, 1, hour, 0, 0).isoformat(),
            })
            record_metrics(f"c{i}", views=views)
        best = compute_best_time(platform="wechat")
        assert best is not None
        # 14 点平均 (100+200)/2 = 150, 9 点 50
        assert best["best_hour"] == 14
        assert best["sample_size"] == 3
        assert best["avg_views_by_hour"][14] > best["avg_views_by_hour"][9]

    def test_compute_best_time_empty_returns_none(self, fresh_store):
        from app.services.metrics_service import compute_best_time
        # 没数据
        assert compute_best_time(platform="wechat") is None


# ============ API ============

class TestMetricsAPI:
    def test_record_endpoint(self, client, fresh_store):
        from app.store import store
        token = _register_login(client)
        store.add_content({
            "title": "t1", "body": "b1", "tags": [], "platform": "wechat",
        })
        cid = store.contents[0]["id"]
        r = client.post("/api/metrics/record", headers=_auth(token), json={
            "content_id": cid, "views": 100, "likes": 10, "comments": 5, "shares": 2,
        })
        assert r.status_code in (200, 201)
        body = r.json()
        assert body["views"] == 100
        assert body["likes"] == 10

    def test_record_validates_content_exists(self, client, fresh_store):
        token = _register_login(client)
        r = client.post("/api/metrics/record", headers=_auth(token), json={
            "content_id": "no_such_id", "views": 100,
        })
        assert r.status_code == 400
        assert "not found" in r.json().get("detail", "").lower() or \
               "不存在" in r.json().get("detail", "")

    def test_get_metrics_for_content(self, client, fresh_store):
        from app.store import store
        from app.services.metrics_service import record_metrics
        token = _register_login(client)
        store.add_content({
            "title": "t1", "body": "b1", "tags": [], "platform": "wechat",
        })
        cid = store.contents[0]["id"]
        record_metrics(cid, views=200, likes=20)
        r = client.get(f"/api/metrics/content/{cid}", headers=_auth(token))
        assert r.status_code == 200
        body = r.json()
        assert body["views"] == 200
        assert body["likes"] == 20

    def test_get_metrics_for_missing_returns_404(self, client, fresh_store):
        token = _register_login(client)
        r = client.get("/api/metrics/content/no_such_id", headers=_auth(token))
        assert r.status_code == 404

    def test_trending_endpoint(self, client, fresh_store):
        from app.store import store
        from app.services.metrics_service import record_metrics
        token = _register_login(client)
        for i in range(3):
            store.add_content({
                "title": f"t{i}", "body": "b", "tags": [], "platform": "wechat",
            })
            record_metrics(store.contents[i]["id"], views=(i + 1) * 100)
        r = client.get("/api/metrics/trending?top_n=2", headers=_auth(token))
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) == 2
        assert items[0]["views"] >= items[1]["views"]

    def test_best_time_endpoint(self, client, fresh_store):
        from app.store import store
        from app.services.metrics_service import record_metrics
        token = _register_login(client)
        for i, hour in [(1, 14), (2, 9), (3, 14)]:
            store.add_publish_record({
                "id": f"pub_{i}",
                "content_id": f"c{i}",
                "platform": "wechat",
                "status": "published",
                "scheduled_time": datetime(2026, 1, 1, hour, 0, 0).isoformat(),
            })
            record_metrics(f"c{i}", views=hour * 10)
        r = client.get("/api/metrics/best-time?platform=wechat", headers=_auth(token))
        assert r.status_code == 200
        body = r.json()
        assert body["best_hour"] == 14

    def test_all_require_auth(self, client, fresh_store):
        r1 = client.post("/api/metrics/record", json={"content_id": "x", "views": 1})
        r2 = client.get("/api/metrics/content/x")
        r3 = client.get("/api/metrics/trending")
        r4 = client.get("/api/metrics/best-time")
        assert all(r.status_code == 401 for r in [r1, r2, r3, r4])
