# AI 生成 API - 使用 provider 工厂(Phase A)

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
import asyncio
import time
from pathlib import Path

from app.core.security import require_user  # P0-3: /ai/adapt/save 需要 auth

router = APIRouter()


# ============ P0-3: 平台调性模板(被 /ai/expand /adapt 复用) ============
# 每个平台的核心约束:字数 + 语气 + 必备元素(emoji/钩子/逻辑等)。
PLATFORM_TIPS: Dict[str, str] = {
    "wechat": (
        "公众号风格:深度长文(3000-5000 字)、专业有观点、有温度、有数据/案例支撑、"
        "段落清晰、有小标题、避免空话。适合有阅读深度的目标读者。"
    ),
    "xiaohongshu": (
        "小红书风格:500-800 字短笔记,emoji 多用(每段 1-2 个)、分段清晰、"
        "首图钩子强、口语化闺蜜感、'干货'/'避坑'等关键词、有具体数字。"
    ),
    "douyin": (
        "抖音风格:200-300 字视频脚本,前 3 秒钩子抓人、口语化、有节奏感、"
        "分镜清晰(画面+字幕+配音)、结尾引导关注/点赞/评论。"
    ),
    "zhihu": (
        "知乎风格:1500-2500 字中长回答,逻辑严谨、有论据链、"
        "专业术语准确、引用数据/来源、'先说结论'结构、有反思深度。"
    ),
}

LENGTH_HINTS: Dict[str, str] = {
    "short": "整体偏短(快速读完)",
    "medium": "中等长度(详细但不过分)",
    "long": "尽量长(深度展开)",
}


# ============ Provider 工厂统一入口(Phase A 改造) ============

async def chat_completion(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    provider: Optional[str] = None,
    max_tokens: int = 2048,
    temperature: float = 0.7,
) -> str:
    """调 provider 工厂(默认 DEFAULT_AI_PROVIDER)。"""
    from app.services.ai_providers import get_provider, get_default_provider_name
    name = (provider or get_default_provider_name()).lower()
    p = get_provider(name)
    return await p.chat(
        messages,
        model=model or p.default_model,
        max_tokens=max_tokens,
        temperature=temperature,
    )


def _resolve_source_context(
    source_id: Optional[str], chapter_id: Optional[str], max_chars: int = 6000
) -> Optional[str]:
    """Phase 3:从来源 store 取 context。

    返回:
      - None: 没传 source_id,或 source 不存在
      - str: 章节全文(或来源 content 前 max_chars 字)

    caller 把它当 system message 或 user message 前缀注入。
    """
    if not source_id:
        return None
    from app.store import store
    src = store.get_source(source_id)
    if not src:
        return None

    if chapter_id:
        ch = store.get_source_chapter(chapter_id)
        if not ch or ch.get("source_id") != source_id:
            return None
        # 懒加载章节全文(首次访问提取 PDF)
        if "content" not in ch and src.get("type") == "pdf":
            try:
                from app.services.pdf_processor import PdfProcessor, Chapter as PdfChapter
                ch_obj = PdfChapter(
                    id=ch["id"], title=ch["title"],
                    page_start=ch["page_start"], page_end=ch["page_end"],
                    char_count=ch["char_count"], method=ch["method"], preview=ch["preview"],
                )
                ch["content"] = PdfProcessor(src["path"]).extract_chapter(ch_obj)
            except Exception:
                return None
        text = ch.get("content") or ch.get("preview", "")
    else:
        # 没指定 chapter:用来源自身 content (text 类型) 或第一章节的 preview
        if src.get("type") == "text":
            text = src.get("content", "")
        else:
            chapters = store.list_source_chapters(source_id)
            if chapters:
                text = chapters[0].get("preview", "")
            else:
                text = ""

    if not text:
        return None
    # 截断到 max_chars
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[…(剩余内容已截断)]"
    return text


def _inject_source_context_into(
    messages: List[Dict[str, str]],
    source_id: Optional[str],
    chapter_id: Optional[str],
) -> List[Dict[str, str]]:
    """把 source context 塞到 messages 头部作为 system message。

    规则:
      - 已存在 system message → 追加内容(不覆盖)
      - 没 system message → 在最前面插入新 system message
    """
    ctx = _resolve_source_context(source_id, chapter_id)
    if not ctx:
        return messages
    new_messages = list(messages)
    if new_messages and new_messages[0].get("role") == "system":
        new_messages[0] = {
            "role": "system",
            "content": new_messages[0]["content"] + "\n\n# 参考资料来源\n\n" + ctx,
        }
    else:
        new_messages.insert(0, {
            "role": "system",
            "content": "# 参考资料来源\n\n" + ctx,
        })
    return new_messages


async def _record_ai_creation(
    creation_type: str,
    prompt_summary: str,
    provider: Optional[str],
    model: Optional[str],
    result_summary: str,
    latency_ms: int,
) -> None:
    """落 ai_creations 历史(Phase B.4)。失败也吞掉,不阻塞主流程。"""
    try:
        from app.store import store
        from app.services.ai_providers import get_default_provider_name
        from app.core.config import settings as _s
        store.add_ai_creation({
            "type": creation_type,
            "provider": (provider or get_default_provider_name()).lower(),
            "model": model or "",
            "prompt": prompt_summary[:1000],
            "result": result_summary[:2000],
            "latency_ms": latency_ms,
        })
    except Exception:
        pass


async def _timed_chat(
    creation_type: str,
    messages: List[Dict[str, str]],
    prompt_summary: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    max_tokens: int = 2048,
    temperature: float = 0.7,
) -> str:
    """包 chat_completion + 自动落库,返回结果文本。"""
    t0 = time.time()
    result = await chat_completion(
        messages, model=model, provider=provider,
        max_tokens=max_tokens, temperature=temperature,
    )
    latency_ms = int((time.time() - t0) * 1000)
    await _record_ai_creation(
        creation_type=creation_type,
        prompt_summary=prompt_summary,
        provider=provider,
        model=model,
        result_summary=result,
        latency_ms=latency_ms,
    )
    return result


# ============ 请求模型 ============
# Phase A: 每个端点都加 provider/model 字段(可选,默认走 DEFAULT_AI_PROVIDER)
# Phase 3: 加 source_id / chapter_id 字段 — 让 AI 生成能引用 NotebookLM 风格来源

class ContentSummaryRequest(BaseModel):
    content: str
    provider: Optional[str] = None
    model: Optional[str] = None
    source_id: Optional[str] = None   # Phase 3: 从来源注入 context
    chapter_id: Optional[str] = None


class PodcastScriptRequest(BaseModel):
    content: str
    style: Optional[str] = "两主播对话讨论"
    provider: Optional[str] = None
    model: Optional[str] = None
    source_id: Optional[str] = None
    chapter_id: Optional[str] = None


class CopyRequest(BaseModel):
    topic: str
    platform: str = "douyin"
    content_type: Optional[str] = "short_video"
    provider: Optional[str] = None
    model: Optional[str] = None
    source_id: Optional[str] = None
    chapter_id: Optional[str] = None


class VideoScriptRequest(BaseModel):
    topic: str
    duration: Optional[int] = 60
    provider: Optional[str] = None
    model: Optional[str] = None
    source_id: Optional[str] = None
    chapter_id: Optional[str] = None


class ImageGenerateRequest(BaseModel):
    prompt: str
    style: Optional[str] = "写实摄影"   # 风格: 写实摄影/插画/3D 渲染/水墨/极简矢量
    ratio: Optional[str] = "1:1"        # 1:1 / 16:9 / 9:16 / 4:3 / 3:4
    n: Optional[int] = 1                # 生成数量 1-4
    negative_prompt: Optional[str] = None


class ImageRecord(BaseModel):
    id: str
    prompt: str
    style: str = "写实摄影"
    ratio: str = "1:1"
    image_url: str
    is_mock: bool = False
    model: str = "MiniMax-Image-01"
    created_at: str


class ImageListResponse(BaseModel):
    total: int
    items: List[ImageRecord]


# ---- Phase 2: 视频生成 ----

class VideoGenerateRequest(BaseModel):
    prompt: str
    duration: int = Field(default=6, description="视频秒数,3 / 6 / 10")
    ratio: Optional[str] = Field(default="16:9", description="16:9 / 9:16 / 1:1")
    style: Optional[str] = None
    image_url: Optional[str] = Field(default=None, description="(可选) 图生视频参考图")
    auto_poll: bool = Field(default=True, description="True=服务端轮询后返回 video;False=立即返回 job_id")
    timeout_seconds: int = Field(default=600, description="auto_poll 总超时(秒)")

    @field_validator("duration")
    @classmethod
    def _check_duration(cls, v: int) -> int:
        from app.services.minimax_client import DOUYIN_DURATION_OPTIONS
        if v not in DOUYIN_DURATION_OPTIONS:
            raise ValueError(
                f"duration 必须是 {DOUYIN_DURATION_OPTIONS} 之一,收到 {v}"
            )
        return v


class VideoRecord(BaseModel):
    id: str
    prompt: str
    duration: int = 6
    ratio: str = "16:9"
    style: Optional[str] = None
    job_id: Optional[str] = None
    status: str = "generating"          # generating | ready | failed
    local_path: Optional[str] = None    # 落盘路径
    video_url: Optional[str] = None     # 平台侧 URL
    is_mock: bool = False               # 关键:是占位 mock 还是真生成
    model: str = "MiniMax-Hailuo-03"
    error: Optional[str] = None
    created_at: str


class VideoListResponse(BaseModel):
    total: int
    items: List[VideoRecord]


# ============ 路由 ============

@router.post("/summary")
async def summarize_content(req: ContentSummaryRequest) -> Dict[str, Any]:
    """内容摘要生成"""
    try:
        messages = [
            {"role": "system", "content": "你是一个内容分析专家，擅长提取关键信息并生成结构化摘要。"},
            {"role": "user", "content": "请分析以下内容，生成简洁的摘要（150字以内）和关键要点：\n\n" + req.content[:10000]}
        ]
        messages = _inject_source_context_into(messages, req.source_id, req.chapter_id)
        result = await _timed_chat(
            creation_type="summary",
            messages=messages,
            prompt_summary=req.content[:200],
            provider=req.provider,
            model=req.model,
        )
        return {"summary": result, "original_length": len(req.content)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/podcast/script")
async def generate_podcast(req: PodcastScriptRequest) -> Dict[str, Any]:
    """播客脚本生成"""
    try:
        messages = [
            {"role": "system", "content": "你是一个播客脚本写作专家。生成为两个角色（主播A和主播B）的对话脚本。要求：1. 对话自然、有深度 2. 涵盖内容的核心要点 3. 有问答、有讨论、有总结 4. 约1500-2000字（5-8分钟朗读）"},
            {"role": "user", "content": "基于以下内容生成播客脚本：\n\n" + req.content[:8000]}
        ]
        messages = _inject_source_context_into(messages, req.source_id, req.chapter_id)
        script = await _timed_chat(
            creation_type="podcast",
            messages=messages,
            prompt_summary=req.content[:200],
            provider=req.provider, model=req.model,
        )
        return {
            "script": script,
            "characters": ["主播A", "主播B"],
            "estimated_duration": "5-8分钟"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/copy")
async def generate_copy(req: CopyRequest) -> Dict[str, Any]:
    """文案生成"""
    try:
        platform_tips = {
            "douyin": "抖音风格：简短有力，有爆点，适合短视频，30字以内标题，正文生动有钩子",
            "xiaohongshu": "小红书风格：温馨、有干货、带emoji，分段清晰",
            "toutiao": "头条风格：严肃、深度、资讯类，适合中长文章",
            "wechat": "公众号风格：深度长文、有观点、有温度",
            "youtube": "YouTube风格：英文、SEO友好、吸引点击",
            "bilibili": "B站风格：年轻化、有梗、弹幕友好"
        }
        tip = platform_tips.get(req.platform, "通用风格")

        messages = [
            {"role": "system", "content": "你是自媒体内容专家，擅长生成适合平台的发布文案。\n" + tip},
            {"role": "user", "content": "为主题「" + req.topic + "」生成发布文案，包括标题和正文"}
        ]
        messages = _inject_source_context_into(messages, req.source_id, req.chapter_id)
        result = await _timed_chat(
            creation_type="copy",
            messages=messages,
            prompt_summary=f"topic={req.topic}, platform={req.platform}",
            provider=req.provider, model=req.model,
        )
        return {"copy": result, "platform": req.platform}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/video/script")
async def generate_video_script(req: VideoScriptRequest) -> Dict[str, Any]:
    """视频脚本生成"""
    try:
        messages = [
            {"role": "system", "content": "你是一个视频脚本写作专家。生成视频脚本，要求：1. 分镜描述（画面、字幕、配音）2. 时长控制 3. 节奏把控 4. 开头留人、结尾引导 格式清晰，便于制作"},
            {"role": "user", "content": "为主题「" + req.topic + "」生成" + str(req.duration) + "秒视频脚本"}
        ]
        messages = _inject_source_context_into(messages, req.source_id, req.chapter_id)
        script = await _timed_chat(
            creation_type="video_script",
            messages=messages,
            prompt_summary=f"topic={req.topic}, duration={req.duration}",
            provider=req.provider, model=req.model,
        )
        return {"script": script, "duration": req.duration}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/image")
async def generate_image(req: ImageGenerateRequest) -> Dict[str, Any]:
    """图像生成 — 真 API 失败时降级到 mock, 保证前端不报错"""
    from app.store import store
    n = max(1, min(req.n or 1, 4))
    is_mock = False
    image_urls: List[str] = []
    error_msg: Optional[str] = None

    try:
        from app.services.minimax_client import MiniMaxClient
        client = MiniMaxClient()
        for _ in range(n):
            url = await client.generate_image(req.prompt)
            image_urls.append(url)
    except ValueError as e:
        # No API key configured — fall back to mock deterministically
        import hashlib
        is_mock = True
        error_msg = str(e)
        for _ in range(n):
            seed = hashlib.md5((req.prompt + str(len(image_urls))).encode()).hexdigest()[:8]
            image_urls.append(f"https://picsum.photos/seed/{seed}/1024/1024")
    except Exception as e:
        # Real API error — fall back to mock rather than 500
        import hashlib
        is_mock = True
        error_msg = f"{type(e).__name__}: {e}"
        for _ in range(n):
            seed = hashlib.md5((req.prompt + str(len(image_urls))).encode()).hexdigest()[:8]
            image_urls.append(f"https://picsum.photos/seed/{seed}/1024/1024")

    # Persist records
    records = []
    for url in image_urls:
        rec = store.add_image({
            "prompt": req.prompt,
            "style": req.style or "写实摄影",
            "ratio": req.ratio or "1:1",
            "image_url": url,
            "is_mock": is_mock,
            "model": "image-01",
        })
        records.append(rec)

    return {
        "items": records,
        "count": len(records),
        "is_mock": is_mock,
        "error": error_msg,
    }


@router.get("/image/list")
async def list_images(limit: int = 50) -> ImageListResponse:
    """列出最近生成的图片"""
    from app.store import store
    items = store.list_images(limit=limit)
    return ImageListResponse(total=len(items), items=items)


@router.get("/image/{image_id}")
async def get_image(image_id: str) -> ImageRecord:
    """获取单张图片详情"""
    from app.store import store
    rec = store.get_image(image_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Image not found")
    return rec


@router.delete("/image/{image_id}")
async def delete_image(image_id: str) -> Dict[str, Any]:
    """删除一张图片"""
    from app.store import store
    ok = store.delete_image(image_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Image not found")
    return {"ok": True, "id": image_id}


@router.post("/video/generate")
async def generate_video(req: VideoGenerateRequest) -> Dict[str, Any]:
    """视频生成 — auto_poll 模式下服务端轮询+落盘,失败时降级 mock。"""
    from app.core.config import settings
    from app.services.minimax_client import DOUYIN_DURATION_OPTIONS, MiniMaxClient
    from app.store import store

    # 1) 提交 + 轮询 + 下载(orchestrator 内部已经包含 mock fallback)
    is_mock = True
    video_url: Optional[str] = None
    local_path: Optional[str] = None
    job_id: Optional[str] = None
    error_msg: Optional[str] = None
    model = "MiniMax-Hailuo-03"

    try:
        client = MiniMaxClient()
        result = await client.generate_video_and_download(
            prompt=req.prompt,
            duration=req.duration,
            poll_max_wait=req.timeout_seconds,
        )
        is_mock = result.get("is_mock", True)
        job_id = result.get("job_id")
        video_url = result.get("video_url")
        local_path = result.get("local_path")
        error_msg = result.get("error")
        if not is_mock and req.duration not in DOUYIN_DURATION_OPTIONS:
            # 客户端传错 duration 也允许,但记录提示
            error_msg = (
                f"duration {req.duration} 超出官方支持 {DOUYIN_DURATION_OPTIONS},仍按服务返回处理"
            )
    except ValueError as e:
        # 没配 API key — 走 mock 占位
        error_msg = f"API key 未配置: {e}"
    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"

    # 2) mock 兜底:写一个 0 字节占位文件,is_mock=True,前端不会真正播放
    if is_mock:
        from app.core.config import settings as _s
        # 用 prompt + 时间戳生成稳定的 mock id
        import hashlib, time
        mock_id_seed = req.prompt + str(time.time_ns())
        mock_id = "vid_" + hashlib.md5(mock_id_seed.encode()).hexdigest()[:10]
        placeholder = Path(_s.VIDEOS_DIR) / f"{mock_id}.mp4.mock"
        placeholder.parent.mkdir(parents=True, exist_ok=True)
        placeholder.write_text("MOCK VIDEO - replace sau cookie + real MiniMax key to enable real generation\n")
        local_path = str(placeholder)
        # 也写一个 video_url 指向 picsum video 占位(如果有)
        if not video_url:
            seed = hashlib.md5(req.prompt.encode()).hexdigest()[:8]
            # picsum 不支持视频,用 placeholder gif
            video_url = f"https://picsum.photos/seed/{seed}/640/360.jpg"

    # 3) 落库 — 一旦落到 store (有 local_path),就标 ready;error 字段承载 mock 原因
    rec = store.add_video({
        "prompt": req.prompt,
        "duration": req.duration,
        "ratio": req.ratio or "16:9",
        "style": req.style,
        "job_id": job_id,
        # mock placeholder 仍然是可交付物;真失败且无 mock 才标 failed
        "status": "ready" if local_path else "failed",
        "local_path": local_path,
        "video_url": video_url,
        "is_mock": is_mock,
        "model": model,
        "error": error_msg,
    })

    return {
        "record": rec,
        "is_mock": is_mock,
        "error": error_msg,
    }


@router.get("/video/list")
async def list_videos(limit: int = 50) -> VideoListResponse:
    """列出最近生成的视频"""
    from app.store import store
    items = store.list_videos(limit=limit)
    return VideoListResponse(total=len(items), items=items)


@router.get("/video/{video_id}")
async def get_video(video_id: str) -> VideoRecord:
    """获取单条视频详情"""
    from app.store import store
    rec = store.get_video(video_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Video not found")
    return rec


@router.delete("/video/{video_id}")
async def delete_video(video_id: str) -> Dict[str, Any]:
    """删除视频记录 + 清理落盘文件"""
    from app.store import store
    rec = store.delete_video(video_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Video not found")
    # 删磁盘文件
    if rec.get("local_path"):
        try:
            Path(rec["local_path"]).unlink(missing_ok=True)
        except Exception as e:
            print(f"[video] warning: failed to remove {rec['local_path']}: {e}")
    return {"ok": True, "id": video_id}


@router.get("/video/status/{job_id}")
async def get_video_status(job_id: str) -> Dict[str, Any]:
    """获取视频生成状态(保留旧端点,用于 auto_poll=False 的客户端轮询)"""
    try:
        from app.services.minimax_client import MiniMaxClient
        client = MiniMaxClient()
        result = await client.get_video_status(job_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Phase B: 3 个新模块(扩写/标题/标签) + 历史 ============

class ExpandRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    target_length: str = Field(default="medium", description="short / medium / long")
    tone: str = Field(default="casual", description="casual / formal / academic")
    provider: Optional[str] = None
    model: Optional[str] = None
    source_id: Optional[str] = None  # Phase 3: 来源(context 注入)
    chapter_id: Optional[str] = None


@router.post("/expand")
async def expand_content(req: ExpandRequest) -> Dict[str, Any]:
    """扩写:把短内容拉长到指定档位。"""
    try:
        length_map = {
            "short": ("约 200-300 字", 400),
            "medium": ("约 600-800 字", 1200),
            "long": ("约 1500-2000 字", 2500),
        }
        target_desc, max_tokens = length_map.get(req.target_length, length_map["medium"])
        tone_prompts = {
            "casual": "语气轻松、口语化,适合自媒体短视频/帖子。",
            "formal": "语气正式、严谨,适合商务/技术内容。",
            "academic": "语气学术、有论据,适合深度分析。",
        }
        tone_desc = tone_prompts.get(req.tone, tone_prompts["casual"])
        system_prompt = (
            "你是一位内容创作助手,擅长把短内容扩写成长文。"
            f"目标长度:{target_desc}。{tone_desc}"
            "保持原内容的核心信息和观点不变,扩写时补充细节、举例、过渡。"
            "输出纯文本,不要带标题或 markdown 标记。"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "请扩写以下内容:\n\n" + req.content},
        ]
        messages = _inject_source_context_into(messages, req.source_id, req.chapter_id)
        expanded = await _timed_chat(
            creation_type="expand",
            messages=messages,
            prompt_summary=req.content[:200],
            provider=req.provider, model=req.model,
            max_tokens=max_tokens,
        )
        return {
            "expanded": expanded,
            "original_length": len(req.content),
            "expanded_length": len(expanded),
            "ratio": round(len(expanded) / max(1, len(req.content)), 2),
            "target_length": req.target_length,
            "tone": req.tone,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class TitlesRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    n: int = Field(default=5, ge=1, le=10)
    platform: Optional[str] = None
    style: str = Field(default="neutral", description="clickbait / neutral / professional")
    provider: Optional[str] = None
    model: Optional[str] = None
    source_id: Optional[str] = None
    chapter_id: Optional[str] = None


class TitleSuggestion(BaseModel):
    text: str
    score: Optional[int] = None
    rationale: Optional[str] = None


class TitlesResponse(BaseModel):
    titles: List[TitleSuggestion]
    platform: Optional[str] = None
    style: str
    total: int


@router.post("/titles")
async def generate_titles(req: TitlesRequest) -> TitlesResponse:
    """标题生成:基于内容生成 N 个候选标题。"""
    try:
        style_prompts = {
            "clickbait": "吸引点击、有点击欲,但不夸张失实。适合短视频/公众号。",
            "neutral": "中性、清晰、信息量足,适合大部分场景。",
            "professional": "专业、严谨,适合 B 站/知乎/技术博客。",
        }
        style_desc = style_prompts.get(req.style, style_prompts["neutral"])
        platform_hint = ""
        if req.platform:
            # 简单映射(后端不依赖前端 constants)
            platform_names = {
                "douyin": "抖音", "xiaohongshu": "小红书", "toutiao": "头条",
                "wechat": "公众号", "youtube": "YouTube", "bilibili": "B站",
                "tiktok": "TikTok", "kuaishou": "快手", "baijia": "百家号",
            }
            name = platform_names.get(req.platform, req.platform)
            platform_hint = f"目标平台:{name}。请考虑该平台用户的阅读习惯和偏好。\n"
        system_prompt = (
            f"你是内容标题专家。基于给定内容生成 {req.n} 个候选标题。\n"
            f"{platform_hint}"
            f"风格:{style_desc}\n"
            "每个标题一行,不要编号,不要带引号。标题控制在 5-30 字之间。"
        )
        user_prompt = (
            f"请基于以下内容生成 {req.n} 个候选标题(每行一个):\n\n"
            + req.content[:5000]
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        messages = _inject_source_context_into(messages, req.source_id, req.chapter_id)
        raw = await _timed_chat(
            creation_type="titles",
            messages=messages,
            prompt_summary=req.content[:200],
            provider=req.provider, model=req.model,
            max_tokens=1024,
        )
        # 解析每行(去掉空行、编号、序号、引号)
        lines = [l.strip().lstrip("0123456789. 、-").strip().strip("\"'「」『』")
                 for l in raw.split("\n")]
        titles = [l for l in lines if l and 2 <= len(l) <= 50][:req.n]
        if not titles:
            titles = [raw.strip()[:30]]  # fallback: 把整个返当作 1 个
        return TitlesResponse(
            titles=[TitleSuggestion(text=t) for t in titles],
            platform=req.platform,
            style=req.style,
            total=len(titles),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class TagsRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    n: int = Field(default=10, ge=1, le=30)
    locale: str = Field(default="mixed", description="zh / en / emoji / mixed")
    provider: Optional[str] = None
    model: Optional[str] = None
    source_id: Optional[str] = None
    chapter_id: Optional[str] = None


class TagItem(BaseModel):
    text: str
    group: str = "topic"  # topic / emotion / audience / trending


class TagsResponse(BaseModel):
    tags: List[TagItem]
    total: int
    locale: str


@router.post("/tags")
async def generate_tags(req: TagsRequest) -> TagsResponse:
    """标签生成:从内容提 N 个标签,按 group 分类。"""
    try:
        locale_desc = {
            "zh": "中文(简体/繁体均可)",
            "en": "英文小写,空格分隔多词",
            "emoji": "纯 emoji 标签,如 🔥 AI",
            "mixed": "中英混合 + 适当 emoji",
        }[req.locale]
        system_prompt = (
            f"你是内容标签专家。基于给定内容生成 {req.n} 个标签。\n"
            f"语言/字符:{locale_desc}\n"
            "每个标签必须明确归类到以下 4 组之一:\n"
            "  - topic(主题/领域)\n"
            "  - emotion(情绪/感受)\n"
            "  - audience(目标人群/受众)\n"
            "  - trending(热点/趋势)\n"
            f"输出格式(每行一个,严格遵守):\n"
            "  group|text\n"
            f"例:\n  topic|AI\n  emotion|inspiring\n  audience|developers\n  trending|chatgpt\n"
            "不要编号、不要 markdown 标记。"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": req.content[:5000]},
        ]
        messages = _inject_source_context_into(messages, req.source_id, req.chapter_id)
        raw = await _timed_chat(
            creation_type="tags",
            messages=messages,
            prompt_summary=req.content[:200],
            provider=req.provider, model=req.model,
            max_tokens=1024,
        )
        tags: List[TagItem] = []
        for line in raw.split("\n"):
            line = line.strip().lstrip("0123456789. 、-*").strip()
            # 严格要求 "group|text" 格式,缺一就丢
            if "|" in line:
                grp, txt = line.split("|", 1)
                grp = grp.strip().lower()
                txt = txt.strip().lstrip("#").strip()
                if txt and grp in ("topic", "emotion", "audience", "trending"):
                    tags.append(TagItem(text=txt, group=grp))
            if len(tags) >= req.n:
                break
        return TagsResponse(tags=tags, total=len(tags), locale=req.locale)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ AI Creations 历史(Phase B.4) ============

@router.get("/creations")
async def list_creations(type: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    """跨模块 AI 创作历史"""
    from app.store import store
    items = store.list_creations(type=type, limit=limit)
    return {"total": len(items), "items": items}


@router.get("/creations/{creation_id}")
async def get_creation(creation_id: str) -> Dict[str, Any]:
    from app.store import store
    rec = store.get_creation(creation_id)
    if not rec:
        raise HTTPException(status_code=404, detail="AI creation not found")
    return rec


@router.delete("/creations/{creation_id}")
async def delete_creation(creation_id: str) -> Dict[str, Any]:
    from app.store import store
    if not store.delete_creation(creation_id):
        raise HTTPException(status_code=404, detail="AI creation not found")
    return {"ok": True, "id": creation_id}

# ============ P0-2: 选题雷达 — AI 单独端点 ============

class HotRewriteRequest(BaseModel):
    hot_title: str = Field(..., min_length=1, max_length=200)
    platform: str = Field(..., description="weibo|zhihu|douyin|xiaohongshu")
    n: int = Field(3, ge=1, le=10)
    tone: str = Field("casual", description="casual|professional|clickbait")
    provider: Optional[str] = None
    model: Optional[str] = None


class HotAngleItem(BaseModel):
    text: str
    hook: str
    target_platform: str


class HotRewriteResponse(BaseModel):
    angles: List[HotAngleItem]
    platform: str
    total: int


@router.post("/hot-rewrite", response_model=HotRewriteResponse)
async def hot_rewrite(req: HotRewriteRequest):
    """把一个热榜话题改写为 N 个自媒体角度(含 hook 和目标平台)。"""
    import json
    import re
    system = (
        f"你是自媒体选题专家。用户给你一个来自 {req.platform} 的热搜话题。"
        f"请生成 {req.n} 个适合做自媒体内容的角度,语气:{req.tone}。"
        "每条包含:text(角度标题)/hook(开头钩子)/target_platform(适合哪个平台)。"
        "请用 JSON 数组格式输出。"
    )
    user_msg = (
        f"热搜话题:{req.hot_title}\n"
        f"请输出 {req.n} 个角度。严格 JSON 数组,每条字段:text,hook,target_platform。"
    )
    raw = await _timed_chat(
        creation_type="hot_angle",
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user_msg}],
        prompt_summary=f"hot_rewrite:{req.hot_title[:50]}",
        provider=req.provider,
        model=req.model,
        max_tokens=1024,
    )
    # 尝试解析 JSON 数组;失败就按行切分
    angles: List[Dict[str, str]] = []
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    if m:
        try:
            parsed = json.loads(m.group(0))
            if isinstance(parsed, list):
                for it in parsed[:req.n]:
                    if isinstance(it, dict):
                        angles.append({
                            "text": str(it.get("text", "")).strip(),
                            "hook": str(it.get("hook", "")).strip(),
                            "target_platform": str(it.get("target_platform", req.platform)).strip(),
                        })
        except Exception:
            pass
    if not angles:
        # fallback: 按行切,去掉编号/引号
        for line in raw.splitlines():
            t = line.strip().lstrip("0123456789. 、-").strip().strip("\"'「」『』")
            if t and 2 <= len(t) <= 200:
                angles.append({"text": t, "hook": "", "target_platform": req.platform})
                if len(angles) >= req.n:
                    break
    if not angles:
        # 兜底
        angles = [{"text": raw.strip()[:200], "hook": "", "target_platform": req.platform}]
    return HotRewriteResponse(
        angles=[HotAngleItem(**a) for a in angles],
        platform=req.platform,
        total=len(angles),
    )


# ============ P0-3: 一稿多发 / 平台改写引擎 ============
# 端点:
#   POST /ai/adapt        并发调 LLM 出 N 个平台改写 variant(不落库)
#   POST /ai/adapt/save   把选定的 variant 创建为 draft Content
# 一稿多发会创建 N 条 Content 行(每平台一条),用 source_topic 关联回原主题。

import logging
log = logging.getLogger("ai_generate")


class AdaptRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500, description="原始主题")
    platforms: Optional[List[str]] = Field(
        None, description="目标平台;None=4 个核心平台 (wechat/xiaohongshu/douyin/zhihu)",
    )
    length_hint: str = Field("medium", description="short|medium|long")
    provider: Optional[str] = None
    model: Optional[str] = None
    source_excerpt: Optional[str] = Field(None, max_length=10000)


class AdaptVariant(BaseModel):
    platform: str
    title: str
    body: str
    char_count: int


class AdaptResponse(BaseModel):
    topic: str
    variants: List[AdaptVariant]
    failed: List[str] = Field(default_factory=list)
    elapsed_ms: int


@router.post("/adapt", response_model=AdaptResponse)
async def adapt_to_platforms(req: AdaptRequest, _user=Depends(require_user)):
    """一稿多发:并发 N 平台改写。返回 variants + failed 列表。需要登录。"""
    platforms = req.platforms or list(PLATFORM_TIPS.keys())
    platforms = [p for p in platforms if p in PLATFORM_TIPS]
    if not platforms:
        raise HTTPException(400, "no valid platforms specified")

    length_desc = LENGTH_HINTS.get(req.length_hint, LENGTH_HINTS["medium"])
    t0 = time.time()

    async def adapt_one(platform: str) -> Dict[str, Any]:
        tip = PLATFORM_TIPS[platform]
        system = (
            "你是一稿多发改写专家。用户给一个主题,你要按目标平台调性产出 1 个版本。\n"
            f"目标平台:{platform}\n"
            f"调性要求:{tip}\n"
            f"长度倾向:{length_desc}\n"
            "输出严格 2 段,第一行是标题,空行后是正文:\n"
            "TITLE: <不超过 30 字的标题>\n"
            "BODY:\n<正文>"
        )
        user_parts = [f"主题:{req.topic}"]
        if req.source_excerpt:
            user_parts.append(f"原文片段:\n{req.source_excerpt[:3000]}")
        user_parts.append("请产出该平台版本。")
        user_msg = "\n\n".join(user_parts)
        raw = await chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            model=req.model,
            provider=req.provider,
            max_tokens=2048,
        )
        title = req.topic[:30]
        body = raw
        if "TITLE:" in raw and "BODY:" in raw:
            head, _, rest = raw.partition("BODY:")
            title_line = head.split("TITLE:", 1)[-1].strip().splitlines()[0].strip()
            if title_line:
                title = title_line[:80]
            body = rest.strip()
        return {
            "platform": platform,
            "title": title,
            "body": body,
            "char_count": len(body),
        }

    tasks = [adapt_one(p) for p in platforms]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    variants: List[Dict[str, Any]] = []
    failed: List[str] = []
    for p, r in zip(platforms, results):
        if isinstance(r, Exception):
            log.warning("adapt %s failed: %s", p, r)
            failed.append(p)
        else:
            variants.append(r)

    elapsed = int((time.time() - t0) * 1000)
    return AdaptResponse(
        topic=req.topic,
        variants=[AdaptVariant(**v) for v in variants],
        failed=failed,
        elapsed_ms=elapsed,
    )


class AdaptSaveRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1)
    platform: str = Field(..., description="wechat|xiaohongshu|douyin|zhihu")
    tags: List[str] = Field(default_factory=list)
    source_topic: Optional[str] = Field(None, description="原主题(可选,用于追踪一稿多发)")


@router.post("/adapt/save")
async def adapt_save(req: AdaptSaveRequest, _user=Depends(require_user)):
    """把选定 variant 创建为 draft Content(返回 content_id)。"""
    from app.store import store
    content = store.add_content({
        "title": req.title,
        "body": req.body,
        "tags": req.tags,
        "platform": req.platform,
        "source_topic": req.source_topic,
        "status": "draft",
    })
    return {"content_id": content["id"]}
