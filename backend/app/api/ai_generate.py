# AI 生成 API - 使用 MiniMaxClient

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
import asyncio
from pathlib import Path

router = APIRouter()


async def chat_completion(messages: List[Dict], model: str = "MiniMax-M3") -> str:
    """调用 MiniMax API"""
    from app.services.minimax_client import MiniMaxClient
    
    client = MiniMaxClient()
    return await client.chat(messages, model=model)


# ============ 请求模型 ============

class ContentSummaryRequest(BaseModel):
    content: str


class PodcastScriptRequest(BaseModel):
    content: str
    style: Optional[str] = "两主播对话讨论"


class CopyRequest(BaseModel):
    topic: str
    platform: str = "douyin"
    content_type: Optional[str] = "short_video"


class VideoScriptRequest(BaseModel):
    topic: str
    duration: Optional[int] = 60


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
        result = await chat_completion(messages)
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
        script = await chat_completion(messages)
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
        result = await chat_completion(messages)
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
        script = await chat_completion(messages)
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