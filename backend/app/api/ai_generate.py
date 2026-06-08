# AI 生成 API - 使用 MiniMaxClient

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio

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
async def generate_video(req: ImageGenerateRequest) -> Dict[str, Any]:
    """视频生成（限额3条/日）"""
    try:
        from app.services.minimax_client import MiniMaxClient
        client = MiniMaxClient()
        job_id = await client.generate_video(req.prompt)
        return {"job_id": job_id, "status": "pending"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/video/status/{job_id}")
async def get_video_status(job_id: str) -> Dict[str, Any]:
    """获取视频生成状态"""
    try:
        from app.services.minimax_client import MiniMaxClient
        client = MiniMaxClient()
        result = await client.get_video_status(job_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))