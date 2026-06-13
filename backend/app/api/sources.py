"""
Sources API — Phase 3 (NotebookLM 风格来源管理)

支持 4 种来源类型:
  - pdf: 文件路径(用 PdfProcessor 切章节)
  - url: 公开网页(本期 MVP:只存 URL,content 等手动 fill)
  - text: 纯文本(直接存 content)
  - notebooklm: NotebookLM notebook(参考 qiaomu)
    创建 notebook + add 多个 URL/文件 sources + 触发 AI 生成
    前端: 连一个 Google NotebookLM,跟 1 个 notebook 关联
    登录: 走 CLI `notebooklm login`(浏览器引导),backend 探测登录态

来源创建后,PDF 类型的会自动切章节,存到 source_chapters。
AI 生成时可指定 source_id + chapter_id 把内容作为 context 注入。
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from pathlib import Path

router = APIRouter()


class NotebookLMBatchGenerateRequest(BaseModel):
    types: List[str] = Field(..., description="要批量触发的 artifact 列表")
    instructions: Optional[str] = ""


# ============ Pydantic 模型 ============

class SourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    type: str = Field(..., description="pdf | url | text | notebooklm")
    path: Optional[str] = None       # pdf: 文件路径
    url: Optional[str] = None        # url: 网页 URL
    content: Optional[str] = None     # text: 直接给内容
    # notebooklm 类型专用
    urls: Optional[List[str]] = None   # notebooklm:多个 URL 一起加
    files: Optional[List[str]] = None  # notebooklm:多个本地文件
    query: Optional[str] = None       # notebooklm:web 搜索关键词(可选,触发 add-research)
    profile: Optional[str] = None     # notebooklm:CLI profile 名(默认 'default')
    metadata: Optional[Dict[str, Any]] = None  # 任意元数据(作者、来源等)


class SourceResponse(BaseModel):
    id: str
    name: str
    type: str
    path: Optional[str] = None
    url: Optional[str] = None
    content_preview: Optional[str] = None
    page_count: Optional[int] = None
    kind: Optional[str] = None       # pdf 才有: text | scanned
    chapter_count: int = 0
    has_toc: bool = False
    created_at: str
    metadata: Optional[Dict[str, Any]] = None
    # notebooklm 专用
    notebook_id: Optional[str] = None
    profile: Optional[str] = None
    source_refs: Optional[List[Dict[str, Any]]] = None
    research_query: Optional[str] = None


class ChapterResponse(BaseModel):
    id: str
    source_id: str
    chapter_index: int
    title: str
    page_start: int
    page_end: int
    char_count: int
    method: str
    preview: str
    created_at: str


class NotebookLMStatusResponse(BaseModel):
    """GET /api/sources/notebooklm/auth-check 返回"""
    authenticated: bool
    login_command: str
    profile: str
    details: Optional[Dict[str, Any]] = None


class NotebookLMGenerateRequest(BaseModel):
    type: str = Field(..., description="audio / video / cinematic-video / quiz / flashcards / report / mind-map / 等")
    instructions: Optional[str] = ""
    output_path: Optional[str] = None  # 下载路径(默认 backend/storage/notebooklm/<nb>_<type>.<ext>)


class NotebookLMArtifactResponse(BaseModel):
    id: str
    source_id: str
    notebook_id: str
    type: str
    status: str       # "polling" / "completed" / "failed"
    local_path: Optional[str] = None
    error: Optional[str] = None
    created_at: str


class ChapterFullResponse(ChapterResponse):
    """含全文"""
    content: str


# ============ 路由 ============

@router.post("", response_model=SourceResponse, status_code=201)
async def create_source(req: SourceCreate) -> Any:
    """创建来源(自动 PDF 切章节)。"""
    from app.store import store
    from app.services.pdf_processor import PdfProcessor

    if req.type == "pdf":
        if not req.path:
            raise HTTPException(status_code=400, detail="pdf type 需要 path 字段")
        try:
            proc = PdfProcessor(req.path)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"文件不存在: {req.path}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"无法读取 PDF: {e}")
        summary = proc.summary()
        if summary.kind == "unknown" or summary.kind == "encrypted":
            raise HTTPException(
                status_code=400,
                detail=f"PDF 无法处理 (kind={summary.kind})",
            )
        chapters = proc.split()
        # 落 source
        rec = store.add_source({
            "name": req.name,
            "type": "pdf",
            "path": req.path,
            "page_count": summary.page_count,
            "kind": summary.kind,
            "has_toc": summary.has_toc,
            "content_preview": chapters[0].preview if chapters else "",
            "metadata": {**(req.metadata or {}), "title": summary.title, "author": summary.author},
        })
        # 落 chapter
        for i, c in enumerate(chapters):
            store.add_source_chapter({
                "source_id": rec["id"],
                "chapter_index": i,
                "title": c.title,
                "page_start": c.page_start,
                "page_end": c.page_end,
                "char_count": c.char_count,
                "method": c.method,
                "preview": c.preview,
            })
        return _source_to_response(rec, chapters)
    elif req.type == "url":
        if not req.url:
            raise HTTPException(status_code=400, detail="url type 需要 url 字段")
        rec = store.add_source({
            "name": req.name,
            "type": "url",
            "url": req.url,
            "content_preview": None,
            "metadata": req.metadata or {},
        })
        return _source_to_response(rec, [])
    elif req.type == "text":
        if not req.content:
            raise HTTPException(status_code=400, detail="text type 需要 content 字段")
        rec = store.add_source({
            "name": req.name,
            "type": "text",
            "content": req.content,
            "content_preview": req.content[:300],
            "char_count": len(req.content),
            "metadata": req.metadata or {},
        })
        return _source_to_response(rec, [])
    elif req.type == "notebooklm":
        return await _create_notebooklm_source(req, store)
    else:
        raise HTTPException(status_code=400, detail=f"不支持的 type: {req.type}")


async def _create_notebooklm_source(req: SourceCreate, store) -> Dict[str, Any]:
    """Phase 5: 创建 NotebookLM 来源(创建 notebook + add 多个 URL/文件)。

    流程:
      1. 探测 login: notebooklm auth check
         → 未登录返 401 + login_command(给前端展示)
      2. notebooklm create <name> → notebook_id
      3. notebooklm source add <url_or_file> × N
      4. 落 source 记录(notebook_id, source_refs, ...)
    """
    from app.services.notebooklm_client import NotebookLMClient, NotebookLMError

    profile = req.profile or "default"
    items = (req.urls or []) + (req.files or [])
    if not items and not req.query:
        raise HTTPException(
            status_code=400,
            detail="notebooklm type 至少要传 urls / files / query 其一",
        )
    client = NotebookLMClient(profile=profile)
    auth = await client.get_auth_status()
    if not auth.get("authenticated"):
        raise HTTPException(
            status_code=401,
            detail={
                "code": "notebooklm_not_authenticated",
                "message": "NotebookLM 未登录。请在终端跑 `notebooklm login` 引导浏览器登录,然后重试。",
                "login_command": auth.get("login_command"),
            },
        )
    # 1) create notebook
    try:
        notebook_id = await client.create_notebook(req.name)
    except NotebookLMError as e:
        raise HTTPException(status_code=500, detail=f"create notebook 失败: {e}")

    # 2) add sources
    source_refs: List[Dict[str, Any]] = []
    for content in items:
        # 自动判断类型:http(s):// → url, 否则 → file(若文件存在) / text
        if content.startswith("http://") or content.startswith("https://"):
            kind = "url"
        elif Path(content).is_file():
            kind = "file"
        else:
            kind = "text"
        try:
            ref = await client.add_source(
                notebook_id, content, source_type=kind, title=None,
            )
            source_refs.append({"content": content, "type": kind, "result": ref.get("stdout", "")[:200]})
        except NotebookLMError as e:
            source_refs.append({"content": content, "type": kind, "error": str(e)[:300]})

    # 3) 可选:web research
    research_log = None
    if req.query:
        try:
            r = await client._run(
                ["source", "add-research", "-n", notebook_id, req.query],
                timeout=120,
            )
            research_log = r.get("stdout", "")[-300:]
        except NotebookLMError as e:
            research_log = f"error: {e}"

    # 4) 落 source
    rec = store.add_source({
        "name": req.name,
        "type": "notebooklm",
        "notebook_id": notebook_id,
        "profile": profile,
        "source_refs": source_refs,
        "research_query": req.query,
        "research_log": research_log,
        "content_preview": f"NotebookLM notebook (id: {notebook_id[:12]}...) 含 {len(source_refs)} 个 sources",
        "metadata": req.metadata or {},
    })
    return _source_to_response(rec, [])


@router.get("", response_model=List[SourceResponse])
async def list_sources(type: Optional[str] = None) -> List[Dict[str, Any]]:
    from app.store import store
    return [_source_to_response(s, []) for s in store.list_sources(type=type)]


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(source_id: str) -> Dict[str, Any]:
    from app.store import store
    s = store.get_source(source_id)
    if not s:
        raise HTTPException(status_code=404, detail="Source not found")
    chapters = store.list_source_chapters(source_id)
    return _source_to_response(s, chapters)


@router.delete("/{source_id}")
async def delete_source(source_id: str) -> Dict[str, Any]:
    from app.store import store
    if not store.delete_source(source_id):
        raise HTTPException(status_code=404, detail="Source not found")
    return {"ok": True, "id": source_id}


@router.get("/{source_id}/chapters", response_model=List[ChapterResponse])
async def list_chapters(source_id: str) -> List[Dict[str, Any]]:
    from app.store import store
    s = store.get_source(source_id)
    if not s:
        raise HTTPException(status_code=404, detail="Source not found")
    return [c for c in store.list_source_chapters(source_id)]


@router.get("/{source_id}/chapters/{chapter_id}", response_model=ChapterFullResponse)
async def get_chapter(source_id: str, chapter_id: str) -> Dict[str, Any]:
    """返回单章全文(按需提取 PDF 真实页,文本类型直接存的就是 content)。"""
    from app.store import store
    s = store.get_source(source_id)
    if not s:
        raise HTTPException(status_code=404, detail="Source not found")
    ch = store.get_source_chapter(chapter_id)
    if not ch or ch.get("source_id") != source_id:
        raise HTTPException(status_code=404, detail="Chapter not found")
    # 懒加载:首次访问提取 PDF
    if "content" not in ch and s.get("type") == "pdf":
        try:
            from app.services.pdf_processor import PdfProcessor
            from dataclasses import dataclass
            # 把 dict 还原成 Chapter
            from app.services.pdf_processor import Chapter
            ch_obj = Chapter(
                id=ch["id"],
                title=ch["title"],
                page_start=ch["page_start"],
                page_end=ch["page_end"],
                char_count=ch["char_count"],
                method=ch["method"],
                preview=ch["preview"],
            )
            content = PdfProcessor(s["path"]).extract_chapter(ch_obj)
            ch["content"] = content
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"提取章节失败: {e}")
    # text 类型直接有 content
    if "content" not in ch and s.get("type") == "text":
        ch["content"] = s.get("content", "")
    return ch


# ============ helpers ============

def _source_to_response(s: Dict[str, Any], chapters: List[Dict[str, Any]]) -> Dict[str, Any]:
    """归一化 source dict → API 响应结构。"""
    ch_count = len(chapters) if chapters else 0
    return {
        "id": s["id"],
        "name": s.get("name", ""),
        "type": s.get("type", "text"),
        "path": s.get("path"),
        "url": s.get("url"),
        "content_preview": s.get("content_preview"),
        "page_count": s.get("page_count"),
        "kind": s.get("kind"),
        "chapter_count": ch_count,
        "has_toc": s.get("has_toc", False),
        "notebook_id": s.get("notebook_id"),
        "profile": s.get("profile"),
        "source_refs": s.get("source_refs", []),
        "research_query": s.get("research_query"),
        "created_at": s.get("created_at", ""),
        "metadata": s.get("metadata"),
    }


# ============ Phase 5: NotebookLM 端点(放在 /sources 路由器下) ============

@router.get("/notebooklm/auth-check", response_model=NotebookLMStatusResponse)
async def notebooklm_auth_check(profile: Optional[str] = None) -> Dict[str, Any]:
    """探测 notebooklm CLI 登录态。给前端"连接 NotebookLM"按钮用。

    流程(参考 qiaomu):
      1. 用户点"连接" → 调这个端点
      2. 若 authenticated=true → 返 OK,前端跳到 source 创建
      3. 若 authenticated=false → 返 login_command,前端显示给用户跑
      4. 用户跑完再点重试
    """
    from app.services.notebooklm_client import NotebookLMClient
    profile = profile or "default"
    client = NotebookLMClient(profile=profile)
    result = await client.get_auth_status()
    # 给 response model 补 profile 字段
    result.setdefault("profile", profile)
    return result


@router.post("/{source_id}/notebooklm/generate", response_model=NotebookLMArtifactResponse)
async def notebooklm_generate(
    source_id: str, req: NotebookLMGenerateRequest,
) -> Dict[str, Any]:
    """Phase 5 + 6: 触发 notebooklm 生成某 artifact(audio / video / quiz / 等)。

    返回的 artifact 记录含:
      - status: "polling" (长任务 audio/video) 或 "completed" (短任务 quiz/flashcards)
      - local_path: 下载路径(已落盘)
    """
    from app.services.notebooklm_client import NotebookLMClient, NotebookLMError
    from app.core.config import settings
    from app.store import store
    from datetime import datetime as _dt
    s = store.get_source(source_id)
    if not s:
        raise HTTPException(status_code=404, detail="Source not found")
    if s.get("type") != "notebooklm":
        raise HTTPException(status_code=400, detail="只能对 notebooklm 类型来源触发生成")
    nb_id = s.get("notebook_id")
    if not nb_id:
        raise HTTPException(status_code=500, detail="来源缺 notebook_id(创建失败?)")

    profile = s.get("profile") or "default"
    client = NotebookLMClient(profile=profile)

    # 决定下载路径
    if req.output_path:
        out = req.output_path
    else:
        ext_map = {
            "audio": "mp3", "video": "mp4", "cinematic-video": "mp4",
            "slide-deck": "pdf", "infographic": "png", "report": "md",
            "mind-map": "json", "quiz": "json", "flashcards": "json",
            "data-table": "csv",
        }
        ext = ext_map.get(req.type, "bin")
        safe = "".join(c for c in s.get("name", "src") if c.isalnum() or c in "-_")[:40]
        out = str(Path(settings.STORAGE_DIR) / "notebooklm" / f"{safe}_{nb_id[:8]}_{req.type}.{ext}")

    # 触发生成
    try:
        gen_result = await client.generate_artifact(
            nb_id, req.type, req.instructions or "",
        )
    except NotebookLMError as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {e}")

    # 长任务(polling)暂不下载;短任务(completed)立即下载
    local_path = None
    if gen_result.get("status") == "completed":
        try:
            local_path = await client.download_artifact(nb_id, req.type, out)
        except NotebookLMError as e:
            gen_result["status"] = "failed"
            gen_result["error"] = str(e)

    # 落 source 内的 artifacts 列表
    artifacts = s.setdefault("artifacts", [])
    artifact = {
        "id": f"art_{len(artifacts)+1:03d}",
        "type": req.type,
        "status": "completed" if local_path else gen_result.get("status", "polling"),
        "local_path": local_path,
        "instructions": req.instructions or "",
        "created_at": _dt.now().isoformat(),
    }
    if gen_result.get("error"):
        artifact["error"] = gen_result["error"]
    artifacts.append(artifact)
    # 给 response model 补 source_id / notebook_id(存在 source 上,不在 artifact 上)
    artifact["source_id"] = source_id
    artifact["notebook_id"] = nb_id

    return artifact


@router.post("/{source_id}/notebooklm/batch-generate")
async def notebooklm_batch_generate(
    source_id: str, req: NotebookLMBatchGenerateRequest,
) -> Dict[str, Any]:
    """Phase 6: 一鱼多吃 — 同一个 notebooklm 来源批量生成多种格式。

    一次性触发:audio / video / slide-deck / quiz / 等(NotebookLM 一次 notebook 出多 artifact)。
    """
    from app.services.notebooklm_client import ARTIFACT_TYPES, NotebookLMError
    from app.store import store
    from datetime import datetime as _dt
    s = store.get_source(source_id)
    if not s or s.get("type") != "notebooklm":
        raise HTTPException(status_code=404, detail="NotebookLM 来源不存在")
    nb_id = s.get("notebook_id")
    profile = s.get("profile") or "default"
    types = req.types
    instructions = req.instructions or ""

    # 校验所有 type
    for t in types:
        if t not in ARTIFACT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的 artifact_type '{t}'。可选: {list(ARTIFACT_TYPES.keys())}",
            )

    from app.services.notebooklm_client import NotebookLMClient
    client = NotebookLMClient(profile=profile)

    # 顺序触发(NotebookLM 单 notebook 串行较稳)
    results = []
    for t in types:
        try:
            gen = await client.generate_artifact(nb_id, t, instructions)
            local_path = None
            if gen.get("status") == "completed":
                try:
                    from app.core.config import settings
                    ext_map = {
                        "audio": "mp3", "video": "mp4", "cinematic-video": "mp4",
                        "slide-deck": "pdf", "infographic": "png", "report": "md",
                        "mind-map": "json", "quiz": "json", "flashcards": "json",
                        "data-table": "csv",
                    }
                    ext = ext_map.get(t, "bin")
                    safe = "".join(c for c in s.get("name", "src") if c.isalnum() or c in "-_")[:40]
                    out = str(Path(settings.STORAGE_DIR) / "notebooklm" / f"{safe}_{nb_id[:8]}_{t}.{ext}")
                    local_path = await client.download_artifact(nb_id, t, out)
                except Exception as e:
                    gen["status"] = "failed"
                    gen["error"] = str(e)
            results.append({
                "type": t, "status": gen.get("status"),
                "local_path": local_path, "log": gen.get("stdout", "")[-200:],
            })
        except Exception as e:
            results.append({"type": t, "status": "failed", "error": str(e)})

    # 批量记录
    artifacts = s.setdefault("artifacts", [])
    for r in results:
        artifacts.append({
            "id": f"art_{len(artifacts)+1:03d}",
            "type": r["type"],
            "status": r.get("status", "failed"),
            "local_path": r.get("local_path"),
            "instructions": instructions,
            "created_at": _dt.now().isoformat(),
            "error": r.get("error"),
        })

    return {
        "source_id": source_id,
        "notebook_id": nb_id,
        "batch_size": len(types),
        "succeeded": sum(1 for r in results if r.get("status") == "completed"),
        "results": results,
    }


@router.get("/{source_id}/artifacts")
async def list_artifacts(source_id: str) -> Dict[str, Any]:
    """列出来源产出的 artifacts(batch generate 的产物)。"""
    from app.store import store
    s = store.get_source(source_id)
    if not s:
        raise HTTPException(status_code=404, detail="Source not found")
    return {
        "source_id": source_id,
        "total": len(s.get("artifacts", [])),
        "artifacts": s.get("artifacts", []),
    }
