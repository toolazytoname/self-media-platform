"""Sources API 集成测试 — Task 3"""
import pytest
import shutil
from pathlib import Path
from unittest.mock import patch, AsyncMock


def _copy_pdf(name: str) -> str:
    src = Path("/Users/lazy/Code/crack/claude/self-media-platform/data") / name
    if not src.exists():
        pytest.skip(f"测试 PDF 不存在: {src}")
    dst_dir = Path("/tmp/sources_api_test")
    dst_dir.mkdir(exist_ok=True)
    dst = dst_dir / name
    shutil.copy(src, dst)
    return str(dst)


class TestSourcesCreate:
    def test_create_text_source(self, client, fresh_store):
        """text 类型:直接给 content,无 chapter。"""
        r = client.post("/api/sources", json={
            "name": "我的笔记",
            "type": "text",
            "content": "这是我的第一篇笔记。包含一些思考。",
        })
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["type"] == "text"
        assert data["chapter_count"] == 0
        assert data["content_preview"].startswith("这是我的")
        assert "笔记" in data["content_preview"]
        assert data["id"].startswith("src_")

    def test_create_url_source(self, client, fresh_store):
        """url 类型:存 URL,无 chapter 切分。"""
        r = client.post("/api/sources", json={
            "name": "微信文章 - AI 改变生活",
            "type": "url",
            "url": "https://mp.weixin.qq.com/s/abc123",
            "metadata": {"author": "张三"},
        })
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["type"] == "url"
        assert data["url"] == "https://mp.weixin.qq.com/s/abc123"
        assert data["metadata"]["author"] == "张三"

    def test_create_pdf_source(self, client, fresh_store):
        """pdf 类型:自动切章节。"""
        path = _copy_pdf("小狗钱钱.pdf")
        r = client.post("/api/sources", json={
            "name": "小狗钱钱(测试)",
            "type": "pdf",
            "path": path,
        })
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["type"] == "pdf"
        assert data["kind"] == "text"
        assert data["page_count"] == 383
        assert data["chapter_count"] >= 25
        assert data["has_toc"] is False  # 没 PDF outline,正则识别

    def test_create_scanned_pdf(self, client, fresh_store):
        """扫描 PDF:kind=scanned,可能 1 个 chapter(全本)。"""
        path = _copy_pdf("期权入门与精通(高清).pdf")
        r = client.post("/api/sources", json={
            "name": "期权入门与精通(高清)",
            "type": "pdf",
            "path": path,
        })
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["kind"] == "scanned"
        assert data["chapter_count"] >= 1

    def test_create_pdf_not_found_404(self, client, fresh_store):
        r = client.post("/api/sources", json={
            "name": "missing",
            "type": "pdf",
            "path": "/nonexistent/file.pdf",
        })
        assert r.status_code == 404
        assert "不存在" in r.json()["detail"]

    def test_create_unknown_type_400(self, client, fresh_store):
        r = client.post("/api/sources", json={
            "name": "x",
            "type": "audio",
        })
        assert r.status_code == 400


class TestSourcesList:
    def test_list_all(self, client, fresh_store):
        for t in ["text", "text", "url"]:
            payload = {"name": t, "type": t}
            if t == "text":
                payload["content"] = "x"
            elif t == "url":
                payload["url"] = "http://x.com"
            client.post("/api/sources", json=payload)
        r = client.get("/api/sources")
        assert r.status_code == 200
        assert len(r.json()) == 3

    def test_list_filter_by_type(self, client, fresh_store):
        client.post("/api/sources", json={"name": "t1", "type": "text", "content": "x"})
        client.post("/api/sources", json={"name": "u1", "type": "url", "url": "http://x"})
        r = client.get("/api/sources", params={"type": "text"})
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["type"] == "text"


class TestSourceGet:
    def test_get_pdf_with_chapters(self, client, fresh_store):
        path = _copy_pdf("小狗钱钱.pdf")
        r = client.post("/api/sources", json={"name": "x", "type": "pdf", "path": path})
        sid = r.json()["id"]
        # 重新 GET
        r2 = client.get(f"/api/sources/{sid}")
        assert r2.status_code == 200
        assert r2.json()["chapter_count"] >= 25

    def test_get_404(self, client, fresh_store):
        r = client.get("/api/sources/src_nonexistent")
        assert r.status_code == 404


class TestSourceChapters:
    def test_list_chapters(self, client, fresh_store):
        path = _copy_pdf("小狗钱钱.pdf")
        r = client.post("/api/sources", json={"name": "x", "type": "pdf", "path": path})
        sid = r.json()["id"]
        r2 = client.get(f"/api/sources/{sid}/chapters")
        assert r2.status_code == 200
        chapters = r2.json()
        assert len(chapters) >= 25
        # 第一个应该是"第一章"
        assert "第一章" in chapters[0]["title"]

    def test_get_chapter_full_text(self, client, fresh_store):
        path = _copy_pdf("小狗钱钱.pdf")
        sid = client.post("/api/sources", json={"name": "x", "type": "pdf", "path": path}).json()["id"]
        chapters = client.get(f"/api/sources/{sid}/chapters").json()
        first = chapters[0]
        r = client.get(f"/api/sources/{sid}/chapters/{first['id']}")
        assert r.status_code == 200
        full = r.json()
        assert "content" in full
        assert len(full["content"]) > 3000
        # 关键词命中
        assert "拉布拉多" in full["content"] or "钱钱" in full["content"]


class TestSourceDelete:
    def test_delete(self, client, fresh_store):
        path = _copy_pdf("小狗钱钱.pdf")
        sid = client.post("/api/sources", json={"name": "x", "type": "pdf", "path": path}).json()["id"]
        # 删
        r = client.delete(f"/api/sources/{sid}")
        assert r.status_code == 200
        assert r.json()["ok"] is True
        # 验证:GET 返 404
        r2 = client.get(f"/api/sources/{sid}")
        assert r2.status_code == 404
        # 验证:chapter 端点也返 404(source 已删,chapters 一起被清)
        r3 = client.get(f"/api/sources/{sid}/chapters")
        assert r3.status_code == 404

    def test_delete_404(self, client, fresh_store):
        r = client.delete("/api/sources/src_nonexistent")
        assert r.status_code == 404


# ============ Phase 5/6: NotebookLM 端点 ============

class TestNotebookLMAuthCheck:
    def test_returns_login_command_when_unauth(self, client, fresh_store):
        with patch("app.services.notebooklm_client.NotebookLMClient") as MockClient:
            instance = MockClient.return_value
            instance.get_auth_status = AsyncMock(return_value={
                "authenticated": False,
                "login_command": "notebooklm login -p default",
                "error": "no cookies",
            })
            resp = client.get("/api/sources/notebooklm/auth-check")
        assert resp.status_code == 200
        data = resp.json()
        assert data["authenticated"] is False
        assert "notebooklm login" in data["login_command"]
        assert data["profile"] == "default"

    def test_returns_authenticated_when_ok(self, client, fresh_store):
        with patch("app.services.notebooklm_client.NotebookLMClient") as MockClient:
            instance = MockClient.return_value
            instance.get_auth_status = AsyncMock(return_value={
                "authenticated": True,
                "login_command": "notebooklm login -p work",
                "details": {"profile": "work"},
            })
            resp = client.get("/api/sources/notebooklm/auth-check?profile=work")
        assert resp.status_code == 200
        assert resp.json()["authenticated"] is True


def _make_nlm_source(client, fresh_store, notebook_id="nb_test123", name="Test Notebook"):
    """直接往 store 注入一个 notebooklm 来源(绕开 CLI 登录)。"""
    from app.store import store
    rec = store.add_source({
        "name": name,
        "type": "notebooklm",
        "notebook_id": notebook_id,
        "profile": "default",
        "source_refs": [{"content": "https://x.com", "type": "url"}],
    })
    return rec["id"]


class TestCreateNotebookLMSource:
    def test_create_success(self, client, fresh_store):
        """已登录 → 创建 notebook + 加 url,落 source 记录。"""
        with patch("app.services.notebooklm_client.NotebookLMClient") as MockClient:
            instance = MockClient.return_value
            instance.get_auth_status = AsyncMock(return_value={"authenticated": True})
            instance.create_notebook = AsyncMock(return_value="nb_abc123")
            instance.add_source = AsyncMock(return_value={
                "stdout": "source src_001 added", "stderr": "",
            })
            resp = client.post("/api/sources", json={
                "name": "AI News Sep",
                "type": "notebooklm",
                "urls": ["https://example.com/a", "https://example.com/b"],
                "profile": "default",
            })
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["type"] == "notebooklm"
        assert data["notebook_id"] == "nb_abc123"
        assert len(data["source_refs"]) == 2
        for ref in data["source_refs"]:
            assert ref["type"] == "url"

    def test_unauthenticated_returns_401(self, client, fresh_store):
        """未登录 → 401 + login_command 透传给前端。"""
        with patch("app.services.notebooklm_client.NotebookLMClient") as MockClient:
            instance = MockClient.return_value
            instance.get_auth_status = AsyncMock(return_value={
                "authenticated": False,
                "login_command": "notebooklm login -p default",
                "error": "no cookies",
            })
            resp = client.post("/api/sources", json={
                "name": "X",
                "type": "notebooklm",
                "urls": ["https://example.com"],
            })
        assert resp.status_code == 401
        body = resp.json()["detail"]
        assert body["code"] == "notebooklm_not_authenticated"
        assert "notebooklm login" in body["login_command"]

    def test_no_input_400(self, client, fresh_store):
        """无 urls/files/query → 400(必须至少一项)。"""
        with patch("app.services.notebooklm_client.NotebookLMClient") as MockClient:
            instance = MockClient.return_value
            instance.get_auth_status = AsyncMock(return_value={"authenticated": True})
            resp = client.post("/api/sources", json={
                "name": "Empty",
                "type": "notebooklm",
            })
        assert resp.status_code == 400
        assert "至少要传" in resp.json()["detail"]

    def test_query_triggers_research(self, client, fresh_store):
        """带 query → 触发 source add-research。"""
        with patch("app.services.notebooklm_client.NotebookLMClient") as MockClient:
            instance = MockClient.return_value
            instance.get_auth_status = AsyncMock(return_value={"authenticated": True})
            instance.create_notebook = AsyncMock(return_value="nb_q1")
            instance._run = AsyncMock(return_value={
                "returncode": 0,
                "stdout": "researched: 5 results",
                "stderr": "",
            })
            resp = client.post("/api/sources", json={
                "name": "Research topic",
                "type": "notebooklm",
                "query": "AI safety latest papers",
            })
        assert resp.status_code == 201
        assert resp.json()["research_query"] == "AI safety latest papers"
        research_calls = [
            c for c in instance._run.call_args_list
            if "add-research" in c.args[0]
        ]
        assert len(research_calls) == 1

    def test_create_failure_500(self, client, fresh_store):
        """notebooklm create 失败 → 500 + 错误信息。"""
        with patch("app.services.notebooklm_client.NotebookLMClient") as MockClient:
            instance = MockClient.return_value
            instance.get_auth_status = AsyncMock(return_value={"authenticated": True})
            from app.services.notebooklm_client import NotebookLMError
            instance.create_notebook = AsyncMock(
                side_effect=NotebookLMError("server 500"),
            )
            resp = client.post("/api/sources", json={
                "name": "Fail",
                "type": "notebooklm",
                "urls": ["https://x.com"],
            })
        assert resp.status_code == 500
        assert "create notebook 失败" in resp.json()["detail"]


class TestGenerateArtifact:
    def test_short_artifact_completed(self, client, fresh_store):
        """quiz 短任务 --wait → completed + 已下载。"""
        src_id = _make_nlm_source(client, fresh_store, "nb_short")
        with patch("app.services.notebooklm_client.NotebookLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_artifact = AsyncMock(return_value={
                "status": "completed",
                "artifact_type": "quiz",
                "stdout": "quiz generated",
            })
            instance.download_artifact = AsyncMock(return_value="/tmp/quiz.json")
            resp = client.post(
                f"/api/sources/{src_id}/notebooklm/generate",
                json={"type": "quiz", "instructions": ""},
            )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "completed"
        assert data["local_path"] == "/tmp/quiz.json"
        assert data["type"] == "quiz"

    def test_long_artifact_polling(self, client, fresh_store):
        """audio 长任务 → status=polling,local_path 为空。"""
        src_id = _make_nlm_source(client, fresh_store, "nb_long")
        with patch("app.services.notebooklm_client.NotebookLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_artifact = AsyncMock(return_value={
                "status": "polling",
                "artifact_type": "audio",
                "stdout": "task task_audio_001 started",
            })
            instance.download_artifact = AsyncMock()
            resp = client.post(
                f"/api/sources/{src_id}/notebooklm/generate",
                json={"type": "audio", "instructions": "深度讲解"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "polling"
        assert data["local_path"] is None
        instance.download_artifact.assert_not_called()

    def test_generate_failure_500(self, client, fresh_store):
        """生成抛错 → 500 + 透传错误。"""
        src_id = _make_nlm_source(client, fresh_store, "nb_fail")
        with patch("app.services.notebooklm_client.NotebookLMClient") as MockClient:
            instance = MockClient.return_value
            from app.services.notebooklm_client import NotebookLMError
            instance.generate_artifact = AsyncMock(
                side_effect=NotebookLMError("rate limit"),
            )
            resp = client.post(
                f"/api/sources/{src_id}/notebooklm/generate",
                json={"type": "audio"},
            )
        assert resp.status_code == 500
        assert "rate limit" in resp.json()["detail"]

    def test_source_not_found_404(self, client, fresh_store):
        with patch("app.services.notebooklm_client.NotebookLMClient"):
            resp = client.post(
                "/api/sources/src_nonexistent/notebooklm/generate",
                json={"type": "quiz"},
            )
        assert resp.status_code == 404

    def test_wrong_source_type_400(self, client, fresh_store):
        """对 text 类型来源触发 notebooklm generate → 400。"""
        from app.store import store
        rec = store.add_source({
            "name": "TXT",
            "type": "text",
            "content": "hi",
            "content_preview": "hi",
        })
        resp = client.post(
            f"/api/sources/{rec['id']}/notebooklm/generate",
            json={"type": "quiz"},
        )
        assert resp.status_code == 400
        assert "notebooklm 类型" in resp.json()["detail"]

    def test_persists_artifact_to_source(self, client, fresh_store):
        """触发生成后,artifact 应存进 source.artifacts。"""
        from app.store import store
        src_id = _make_nlm_source(client, fresh_store, "nb_persist")
        with patch("app.services.notebooklm_client.NotebookLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_artifact = AsyncMock(return_value={
                "status": "completed",
                "artifact_type": "report",
                "stdout": "report done",
            })
            instance.download_artifact = AsyncMock(return_value="/tmp/r.md")
            client.post(
                f"/api/sources/{src_id}/notebooklm/generate",
                json={"type": "report"},
            )
        s = store.get_source(src_id)
        artifacts = s.get("artifacts", [])
        assert len(artifacts) == 1
        assert artifacts[0]["type"] == "report"
        assert artifacts[0]["status"] == "completed"


class TestBatchGenerate:
    def test_three_types(self, client, fresh_store):
        """一次生成三种格式。"""
        src_id = _make_nlm_source(client, fresh_store, "nb_batch")
        with patch("app.services.notebooklm_client.NotebookLMClient") as MockClient:
            instance = MockClient.return_value

            async def fake_gen(nb, t, instr):
                return {
                    "quiz": {"status": "completed", "stdout": "q"},
                    "audio": {"status": "polling", "stdout": "a"},
                    "flashcards": {"status": "completed", "stdout": "f"},
                }[t]
            instance.generate_artifact = AsyncMock(side_effect=fake_gen)
            instance.download_artifact = AsyncMock(side_effect=lambda *a, **kw: a[-1])
            resp = client.post(
                f"/api/sources/{src_id}/notebooklm/batch-generate",
                json={"types": ["quiz", "audio", "flashcards"], "instructions": "深度"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["batch_size"] == 3
        assert data["succeeded"] == 2  # quiz + flashcards
        types_in_results = sorted(r["type"] for r in data["results"])
        assert types_in_results == ["audio", "flashcards", "quiz"]

    def test_invalid_type_400(self, client, fresh_store):
        src_id = _make_nlm_source(client, fresh_store, "nb_batch_bad")
        resp = client.post(
            f"/api/sources/{src_id}/notebooklm/batch-generate",
            json={"types": ["quiz", "unicorn"]},
        )
        assert resp.status_code == 400
        assert "unicorn" in resp.json()["detail"]

    def test_continues_on_individual_failure(self, client, fresh_store):
        """一个 type 失败不影响其他的。"""
        src_id = _make_nlm_source(client, fresh_store, "nb_batch_partial")
        with patch("app.services.notebooklm_client.NotebookLMClient") as MockClient:
            instance = MockClient.return_value
            from app.services.notebooklm_client import NotebookLMError

            async def fake_gen(nb, t, instr):
                if t == "audio":
                    raise NotebookLMError("rate limit")
                return {"status": "completed", "stdout": "ok"}
            instance.generate_artifact = AsyncMock(side_effect=fake_gen)
            instance.download_artifact = AsyncMock(return_value="/tmp/x")
            resp = client.post(
                f"/api/sources/{src_id}/notebooklm/batch-generate",
                json={"types": ["quiz", "audio", "flashcards"]},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["succeeded"] == 2  # quiz + flashcards
        audio_result = [r for r in data["results"] if r["type"] == "audio"][0]
        assert audio_result["status"] == "failed"


class TestListArtifacts:
    def test_list_empty(self, client, fresh_store):
        src_id = _make_nlm_source(client, fresh_store, "nb_empty_art")
        resp = client.get(f"/api/sources/{src_id}/artifacts")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["artifacts"] == []

    def test_list_after_generate(self, client, fresh_store):
        src_id = _make_nlm_source(client, fresh_store, "nb_list_art")
        with patch("app.services.notebooklm_client.NotebookLMClient") as MockClient:
            instance = MockClient.return_value
            instance.generate_artifact = AsyncMock(return_value={
                "status": "completed", "stdout": "ok",
            })
            instance.download_artifact = AsyncMock(return_value="/tmp/q.json")
            client.post(
                f"/api/sources/{src_id}/notebooklm/generate",
                json={"type": "quiz"},
            )
        resp = client.get(f"/api/sources/{src_id}/artifacts")
        data = resp.json()
        assert data["total"] == 1
        assert data["artifacts"][0]["type"] == "quiz"


class TestListFilterNotebookLM:
    def test_filter_by_type(self, client, fresh_store):
        _make_nlm_source(client, fresh_store, "nb_filter1", name="A")
        _make_nlm_source(client, fresh_store, "nb_filter2", name="B")
        from app.store import store
        store.add_source({"name": "TXT", "type": "text", "content": "x"})
        resp = client.get("/api/sources?type=notebooklm")
        assert resp.status_code == 200
        items = resp.json()
        assert all(it["type"] == "notebooklm" for it in items)
        assert len(items) == 2
