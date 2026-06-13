"""
Sources API — Phase 3 (NotebookLM 风格来源管理)

支持三种来源类型:
  - pdf: 文件路径(用 PdfProcessor 切章节)
  - url: 公开网页(本期 MVP:只存 URL,content 等手动 fill)
  - text: 纯文本(直接存 content)

来源创建后,PDF 类型的会自动切章节,存到 source_chapters。
AI 生成时可指定 source_id + chapter_id 把内容作为 context 注入。
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

router = APIRouter()


# ============ Pydantic 模型 ============

class SourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    type: str = Field(..., description="pdf | url | text")
    path: Optional[str] = None       # pdf: 文件路径
    url: Optional[str] = None        # url: 网页 URL
    content: Optional[str] = None     # text: 直接给内容
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
    else:
        raise HTTPException(status_code=400, detail=f"不支持的 type: {req.type}")


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
        "created_at": s.get("created_at", ""),
        "metadata": s.get("metadata"),
    }
