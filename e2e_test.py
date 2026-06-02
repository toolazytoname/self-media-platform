#!/usr/bin/env python3
"""
端到端功能测试脚本
通过 HTTP 真实调用后端 API，验证每个 endpoint 的行为
"""
import json
import sys
import time
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE = "http://localhost:8000"
TOKEN = None

passed = 0
failed = 0
failures = []


def http(method, path, data=None, headers=None, expect_status=None, label=None):
    """发送 HTTP 请求并返回 (status, body_dict)"""
    global passed, failed, failures
    url = BASE + path
    body = None
    hdrs = {"Content-Type": "application/json"}
    if TOKEN:
        hdrs["Authorization"] = f"Bearer {TOKEN}"
    if headers:
        hdrs.update(headers)
    if data is not None:
        body = json.dumps(data).encode("utf-8")
    req = Request(url, data=body, method=method, headers=hdrs)
    try:
        with urlopen(req, timeout=30) as r:
            status = r.status
            text = r.read().decode()
    except HTTPError as e:
        status = e.code
        text = e.read().decode() if e.fp else ""
    try:
        body_dict = json.loads(text) if text else None
    except Exception:
        body_dict = text

    ok = True
    if expect_status is not None:
        if isinstance(expect_status, (tuple, list)):
            ok = status in expect_status
        else:
            ok = (status == expect_status)
    if ok:
        passed += 1
        mark = "✓"
    else:
        failed += 1
        mark = "✗"
        failures.append((label or path, method, path, expect_status, status, body_dict))
    label_str = label or f"{method} {path}"
    print(f"  {mark} [{status}] {label_str}")
    if not ok:
        print(f"     expected={expect_status} got={status} body={str(body_dict)[:200]}")
    return status, body_dict


def section(title):
    print(f"\n=== {title} ===")


def main():
    global TOKEN

    # ============ 健康检查 ============
    section("1. 健康检查 & 基础")
    http("GET", "/health", expect_status=200, label="GET /health")
    http("GET", "/", expect_status=200, label="GET /")
    http("GET", "/api/cms/stats", expect_status=200, label="GET /api/cms/stats")

    # ============ 认证 ============
    section("2. 用户认证")
    http("POST", "/api/auth/register", data={
        "username": f"e2e_{int(time.time())}",
        "password": "test1234",
        "display_name": "E2E User",
    }, expect_status=201, label="POST /api/auth/register")

    r, login = http("POST", "/api/auth/login", data={
        "username": "e2e_test", "password": "test1234",
    })
    # 注册一个稳定测试用户
    http("POST", "/api/auth/register", data={
        "username": "e2e_test", "password": "test1234", "display_name": "E2E"
    })
    r, login = http("POST", "/api/auth/login", data={
        "username": "e2e_test", "password": "test1234",
    }, expect_status=200, label="POST /api/auth/login")
    if r == 200 and login and "access_token" in login:
        TOKEN = login["access_token"]
    http("GET", "/api/auth/me", expect_status=200, label="GET /api/auth/me (with token)")
    http("GET", "/api/auth/me", headers={"Authorization": "Bearer invalid"}, expect_status=401,
         label="GET /api/auth/me (no auth)")
    http("POST", "/api/auth/login", data={"username": "e2e_test", "password": "wrongpass"},
         expect_status=401, label="login wrong password")
    http("POST", "/api/auth/register", data={"username": "e2e_test", "password": "test1234"},
         expect_status=400, label="register duplicate")

    # ============ 内容管理 ============
    section("3. 内容管理")
    r, c1 = http("POST", "/api/content/", data={
        "title": "E2E 测试内容 1",
        "body": "# Hello\n\n这是 **粗体** 文字。",
        "tags": ["test", "e2e"],
        "platform": "douyin",
    }, expect_status=201, label="POST /api/content/")
    cid = c1["id"]

    http("GET", "/api/content/", expect_status=200, label="GET /api/content/ (list)")
    http("GET", f"/api/content/{cid}", expect_status=200, label="GET /api/content/{id}")
    http("PUT", f"/api/content/{cid}", data={
        "title": "Updated Title", "tags": ["updated"]
    }, expect_status=200, label="PUT /api/content/{id}")
    http("PUT", f"/api/content/{cid}", data={"status": "wrong"},
         expect_status=400, label="PUT invalid status")
    http("GET", f"/api/content/nonexistent", expect_status=404, label="GET not found")
    http("POST", f"/api/content/{cid}/duplicate", expect_status=200,
         label="POST /api/content/{id}/duplicate")
    http("POST", f"/api/content/{cid}/submit-review", expect_status=200,
         label="POST /api/content/{id}/submit-review")
    http("POST", f"/api/content/nonexistent/duplicate", expect_status=404,
         label="duplicate not found")
    http("GET", "/api/content/?keyword=Updated", expect_status=200,
         label="GET /api/content/?keyword=")
    http("GET", "/api/content/?platform=douyin", expect_status=200,
         label="GET /api/content/?platform=")
    http("GET", "/api/content/?status=pending", expect_status=200,
         label="GET /api/content/?status=")

    # 批量操作
    cids = []
    for i in range(3):
        r, x = http("POST", "/api/content/", data={
            "title": f"Bulk {i}", "body": "x", "tags": [], "platform": "all",
        })
        if r == 201: cids.append(x["id"])
    http("POST", "/api/content/bulk/delete", data={"ids": cids[:2]},
         expect_status=200, label="POST /api/content/bulk/delete")
    http("POST", "/api/content/bulk/update", data={"ids": cids[2:], "status": "published"},
         expect_status=200, label="POST /api/content/bulk/update")
    http("POST", "/api/content/bulk/update", data={"ids": cids, "status": "invalid"},
         expect_status=400, label="bulk update invalid status")

    # 导出
    http("GET", "/api/content/export/all?format=json", expect_status=200,
         label="GET /api/content/export/all?format=json")
    http("GET", "/api/content/export/all?format=markdown", expect_status=200,
         label="GET /api/content/export/all?format=markdown")
    http("GET", "/api/content/export/all?format=csv", expect_status=200,
         label="GET /api/content/export/all?format=csv")
    http("GET", "/api/content/export/all?format=xml", expect_status=400,
         label="GET /api/content/export/all?format=xml (invalid)")

    # 删除
    http("DELETE", f"/api/content/{cid}", expect_status=200, label="DELETE /api/content/{id}")
    http("DELETE", "/api/content/missing", expect_status=404, label="DELETE not found")

    # ============ 模板管理 ============
    section("4. 模板管理")
    r, t1 = http("POST", "/api/templates", data={
        "name": "E2E 模板", "category": "article", "description": "测试", "body": "## 标题",
    }, expect_status=201, label="POST /api/templates")
    tid = t1["id"]
    http("GET", "/api/templates", expect_status=200, label="GET /api/templates")
    http("GET", f"/api/templates/{tid}", expect_status=200, label="GET /api/templates/{id}")
    http("GET", "/api/templates/missing", expect_status=404, label="GET template not found")
    http("GET", "/api/templates?category=article", expect_status=200,
         label="GET /api/templates?category=")
    http("PUT", f"/api/templates/{tid}", data={"name": "Updated"},
         expect_status=200, label="PUT /api/templates/{id}")
    http("PUT", "/api/templates/missing", data={"name": "X"},
         expect_status=404, label="PUT template not found")
    http("POST", "/api/templates", data={"name": "X", "category": "invalid", "body": "X"},
         expect_status=400, label="POST template invalid category")
    http("DELETE", f"/api/templates/{tid}", expect_status=200, label="DELETE /api/templates/{id}")
    http("DELETE", "/api/templates/missing", expect_status=404, label="DELETE template not found")

    # ============ 选题 ============
    section("5. 选题管理")
    r, topic = http("POST", "/api/cms/topics", data={
        "title": "选题1", "description": "测试", "priority": 3,
    }, expect_status=201, label="POST /api/cms/topics")
    topic_id = topic["id"]
    http("GET", "/api/cms/topics", expect_status=200, label="GET /api/cms/topics")
    http("GET", f"/api/cms/topics/{topic_id}", expect_status=200, label="GET /api/cms/topics/{id}")
    http("GET", "/api/cms/topics/missing", expect_status=404, label="GET topic not found")
    http("PUT", f"/api/cms/topics/{topic_id}", data={"title": "Updated", "status": "done"},
         expect_status=200, label="PUT /api/cms/topics/{id}")
    http("PUT", f"/api/cms/topics/{topic_id}", data={"status": "invalid"},
         expect_status=400, label="PUT topic invalid status")
    http("PUT", "/api/cms/topics/missing", data={"title": "X"},
         expect_status=404, label="PUT topic not found")
    http("DELETE", f"/api/cms/topics/{topic_id}", expect_status=200, label="DELETE /api/cms/topics/{id}")
    http("DELETE", "/api/cms/topics/missing", expect_status=404, label="DELETE topic not found")
    http("GET", "/api/cms/topics?status=active", expect_status=200,
         label="GET /api/cms/topics?status=")

    # ============ 素材 ============
    section("6. 素材管理")
    r, m1 = http("POST", "/api/cms/materials", data={
        "name": "图片1", "type": "image", "path": "/uploads/1.png",
    }, expect_status=201, label="POST /api/cms/materials")
    mid = m1["id"]
    http("GET", "/api/cms/materials", expect_status=200, label="GET /api/cms/materials")
    http("GET", f"/api/cms/materials/{mid}", expect_status=200, label="GET /api/cms/materials/{id}")
    http("GET", "/api/cms/materials?type=image", expect_status=200,
         label="GET /api/cms/materials?type=")
    http("PUT", f"/api/cms/materials/{mid}", data={"name": "renamed"},
         expect_status=200, label="PUT /api/cms/materials/{id}")
    http("DELETE", f"/api/cms/materials/{mid}", expect_status=200,
         label="DELETE /api/cms/materials/{id}")
    http("POST", "/api/cms/materials", data={"name": "X", "type": "invalid", "path": "/x"},
         expect_status=400, label="POST material invalid type")

    # ============ 审核 ============
    section("7. 审核流程")
    r, c1 = http("POST", "/api/content/", data={
        "title": "审核测试", "body": "x", "tags": [], "platform": "all",
    })
    r, review = http("POST", "/api/cms/review", data={
        "content_id": c1["id"], "content_title": c1["title"],
    }, expect_status=201, label="POST /api/cms/review")
    rid = review["id"]
    http("GET", "/api/cms/review/tasks", expect_status=200, label="GET /api/cms/review/tasks")
    http("GET", "/api/cms/review/tasks?status=pending", expect_status=200,
         label="GET /api/cms/review/tasks?status=")
    http("GET", "/api/cms/review/tasks?status=invalid", expect_status=400,
         label="GET review tasks invalid status")
    http("PUT", f"/api/cms/review/{rid}", data={"status": "approved", "comment": "ok"},
         expect_status=200, label="PUT approve")
    http("PUT", f"/api/cms/review/{rid}", data={"status": "invalid"},
         expect_status=400, label="PUT invalid status")
    http("PUT", "/api/cms/review/missing", data={"status": "approved"},
         expect_status=404, label="PUT review not found")

    # ============ 平台账号 ============
    section("8. 平台账号")
    http("GET", "/api/platforms/accounts", expect_status=200, label="GET /api/platforms/accounts")
    http("POST", "/api/platforms/accounts", data={}, expect_status=422,
         label="POST platform account (empty)")
    http("POST", "/api/platforms/accounts", data={
        "platform": "douyin", "name": "test_dy",
    }, expect_status=(200, 201), label="POST platform account")
    http("GET", "/api/platforms/accounts", expect_status=200, label="GET accounts after add")

    # ============ 调度 ============
    section("9. 调度任务")
    r, c1 = http("POST", "/api/content/", data={
        "title": "调度测试", "body": "x", "tags": [], "platform": "all",
    })
    future = (datetime.now() + timedelta(hours=1)).isoformat()
    r, task = http("POST", "/api/scheduler/schedule", data={
        "content_id": c1["id"], "platform": "douyin", "scheduled_time": future,
    }, expect_status=(200, 201), label="POST /api/scheduler/schedule")
    task_id = task.get("id", "missing")
    http("GET", "/api/scheduler/tasks", expect_status=200, label="GET /api/scheduler/tasks")
    http("GET", f"/api/scheduler/task/{task_id}", expect_status=200,
         label="GET /api/scheduler/task/{id}")
    http("GET", "/api/scheduler/task/missing", expect_status=404, label="GET task not found")
    http("PUT", f"/api/scheduler/task/{task_id}",
         data={"scheduled_time": (datetime.now() + timedelta(hours=2)).isoformat()},
         expect_status=200, label="PUT /api/scheduler/task/{id}")
    http("DELETE", f"/api/scheduler/task/{task_id}", expect_status=200,
         label="DELETE /api/scheduler/task/{id}")
    http("DELETE", "/api/scheduler/task/missing", expect_status=404, label="DELETE task not found")
    http("POST", "/api/scheduler/random-interval", expect_status=200,
         label="POST /api/scheduler/random-interval")
    http("POST", "/api/scheduler/run-due", expect_status=200, label="POST /api/scheduler/run-due")
    http("POST", "/api/scheduler/schedule", data={"content_id": "missing-id", "platform": "douyin", "scheduled_time": future},
         expect_status=404, label="schedule with missing content")
    http("POST", "/api/scheduler/schedule", data={"content_id": "x", "platform": "y"},
         expect_status=422, label="schedule with missing fields")

    # ============ 设置 ============
    section("10. 系统设置")
    http("GET", "/api/config", expect_status=200, label="GET /api/config")
    http("POST", "/api/config", data={"minimax_api_key": "test-key"},
         expect_status=(200, 500), label="POST /api/config")
    http("POST", "/api/config/test", data={
        "api_key": "fake", "base_url": "https://api.minimaxi.com/v1", "model": "MiniMax-M3",
    }, expect_status=(200, 500, 502, 503), label="POST /api/config/test")

    # ============ AI ============
    section("11. AI 生成（允许网络失败）")
    http("POST", "/api/ai/summary", data={"content": "测试" * 20},
         expect_status=(200, 500, 502, 503), label="POST /api/ai/summary")
    http("POST", "/api/ai/copy", data={"topic": "AI", "platform": "wechat"},
         expect_status=(200, 500, 502, 503), label="POST /api/ai/copy")
    http("POST", "/api/ai/podcast/script", data={"content": "x"},
         expect_status=(200, 500, 502, 503), label="POST /api/ai/podcast/script")
    http("POST", "/api/ai/video/script", data={"topic": "x", "duration": 60},
         expect_status=(200, 500, 502, 503), label="POST /api/ai/video/script")
    http("POST", "/api/ai/image", data={"prompt": "cat"},
         expect_status=(200, 500, 502, 503), label="POST /api/ai/image")
    http("POST", "/api/ai/video/generate", data={"prompt": "x"},
         expect_status=(200, 202, 500, 502, 503), label="POST /api/ai/video/generate")
    http("GET", "/api/ai/video/status/test-job-id", expect_status=(200, 404, 500, 502, 503),
         label="GET /api/ai/video/status/{id}")

    # ============ 404 测试 ============
    section("12. 错误处理")
    http("GET", "/api/nonexistent", expect_status=404, label="GET unknown route")

    # ============ 总结 ============
    print(f"\n{'='*50}")
    print(f"结果: {passed} passed, {failed} failed")
    if failures:
        print(f"\n失败详情:")
        for label, method, path, expected, got, body in failures:
            print(f"  - {label}: {method} {path}, expected={expected}, got={got}")
            if body:
                print(f"    body: {str(body)[:150]}")
    print(f"{'='*50}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
