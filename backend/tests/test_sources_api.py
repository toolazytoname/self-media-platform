"""Sources API 集成测试 — Task 3"""
import pytest
import shutil
from pathlib import Path


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
