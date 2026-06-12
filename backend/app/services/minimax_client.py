# MiniMax API 集成

import asyncio
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
import httpx


# Hailuo-03 支持的时长档位(minimax 官方约束)
DOUYIN_DURATION_OPTIONS = [3, 6, 10]


class MiniMaxClient:
    """MiniMax API 客户端 - 使用直接 HTTP 调用"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        # 优先从 settings 读取（已从 .env 加载），其次从环境变量，最后才用默认值
        from app.core.config import settings
        self.api_key = api_key or settings.MINIMAX_API_KEY or os.getenv("OPENAI_API_KEY", "")
        self.base_url = base_url or settings.MINIMAX_BASE_URL or "https://api.minimaxi.com/v1"
        self.default_model = model or os.getenv("MINIMAX_MODEL") or "MiniMax-M3"

        if not self.api_key:
            raise ValueError("MiniMax API Key 未配置，请先在设置页面配置")

    # ============ 文本生成 (M3/M2.7) ============

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """对话生成 - 使用正确的 MiniMax 端点

        试用 /v1/text/chatcompletion_v2 (minimax 官方)，fallback 到 OpenAI 兼容的
        /v1/chat/completions。两者都失败时抛清晰错误（key 限图权限等）。
        """
        model = model or self.default_model
        base = self.base_url.rstrip('/')

        # 备用端点列表
        endpoints = [
            (f"{base}/text/chatcompletion_v2", "minimax-native"),
            (f"{base}/chat/completions", "openai-compat"),
        ]

        last_error = None
        for url, label in endpoints:
            try:
                headers = {
                    "Authorization": 'Bearer ' + self.api_key,
                    "Content-Type": "application/json"
                }
                data = {"model": model, "messages": messages}
                with httpx.Client(timeout=60.0) as client:
                    response = client.post(url, headers=headers, json=data)

                result = response.json()

                # 区分: minimax 风格 200+1004 (无权限) vs OpenAI 风格 401 (无 key)
                if "base_resp" in result:
                    base_resp = result.get("base_resp", {})
                    if base_resp.get("status_code") == 0:
                        # 真成功
                        choices = result.get("choices", [])
                        if choices:
                            return choices[0]["message"]["content"]
                    # 1004 'login fail' 意味着 key 不被这个端点接受, 试下一个
                    last_error = f"{label}: {base_resp.get('status_msg', 'unknown')}"
                    continue

                # OpenAI 风格成功
                if "choices" in result and result["choices"]:
                    return result["choices"][0]["message"]["content"]

                last_error = f"{label}: 响应无 choices 字段"
            except Exception as e:
                last_error = f"{label}: {type(e).__name__}: {e}"
                continue

        # 都失败
        raise Exception(
            f"AI 文本服务不可用 ({last_error})。"
            f"可能原因：API key 限图权限、无效、或服务暂不可用。"
            f"请检查 key 或换一个有 text 权限的 key。"
        )

    async def content_summary(self, content: str) -> Dict[str, Any]:
        """内容摘要 - 将长文/URL/PDF内容提取要点"""
        messages = [
            {"role": "system", "content": "你是一个内容分析专家，擅长提取关键信息并生成结构化摘要。"},
            {"role": "user", "content": f"请分析以下内容，生成摘要和关键要点：\n\n{content[:10000]}"}
        ]
        result = await self.chat(messages)
        return {"summary": result, "original_length": len(content)}

    # ============ 图像生成 ============

    async def generate_image(
        self,
        prompt: str,
        model: str = "image-01"
    ) -> str:
        """图像生成 - 返回图片 URL

        MiniMax 的 image 端点是 /v1/image_generation（不是 OpenAI 风格的
        /v1/images/generations）。响应是 {"data": {"image_urls": [...]}, ...}。
        """
        url = self.base_url.rstrip('/') + "/image_generation"

        headers = {
            "Authorization": 'Bearer ' + self.api_key,
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "prompt": prompt
        }

        with httpx.Client(timeout=120.0) as client:
            response = client.post(url, headers=headers, json=data)

        if response.status_code != 200:
            raise Exception("API Error: " + response.text)

        result = response.json()
        urls = result.get("data", {}).get("image_urls") or []
        if not urls:
            raise Exception("No image_urls in response: " + str(result)[:300])
        return urls[0]

    # ============ 语音合成 ============

    async def text_to_speech(
        self,
        text: str,
        voice_id: str = "default"
    ) -> bytes:
        """语音合成 - 返回音频bytes"""
        url = self.base_url.rstrip('/') + "/audio/speech"
        
        headers = {
            "Authorization": 'Bearer ' + self.api_key,
            "Content-Type": "application/json"
        }
        data = {
            "model": "MiniMax-TTS",
            "voice": voice_id,
            "input": text
        }
        
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=data)
        
        if response.status_code != 200:
            raise Exception("API Error: " + response.text)
        
        return response.content

    # ============ 音乐生成 ============

    async def generate_music(
        self,
        prompt: str,
        duration: int = 180
    ) -> str:
        """音乐生成 - 返回音乐URL"""
        url = self.base_url.rstrip('/') + "/audio/generations"
        
        headers = {
            "Authorization": 'Bearer ' + self.api_key,
            "Content-Type": "application/json"
        }
        data = {
            "model": "MiniMax-Music",
            "prompt": prompt,
            "duration": duration
        }
        
        with httpx.Client(timeout=120.0) as client:
            response = client.post(url, headers=headers, json=data)
        
        if response.status_code != 200:
            raise Exception("API Error: " + response.text)
        
        result = response.json()
        return result["data"][0]["url"]

    # ============ 视频生成 (3条/日限制) ============

    async def generate_video(
        self,
        prompt: str,
        duration: int = 6
    ) -> str:
        """视频生成 - 返回任务 ID (限额3条/日)

        MiniMax 端点是 /v1/video_generation（不是 OpenAI 风格的 /video/generations）。
        """
        if duration not in DOUYIN_DURATION_OPTIONS:
            raise ValueError(
                f"duration 必须是 {DOUYIN_DURATION_OPTIONS} 之一,收到 {duration}"
            )

        url = self.base_url.rstrip('/') + "/video_generation"

        headers = {
            "Authorization": 'Bearer ' + self.api_key,
            "Content-Type": "application/json"
        }
        data = {
            "model": "MiniMax-Hailuo-03",
            "prompt": prompt,
            "duration": duration
        }

        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=data)

        if response.status_code != 200:
            raise Exception("API Error: " + response.text)

        result = response.json()
        # MiniMax 返回 job_id 在 base_resp 或顶层, 兼容两种
        job_id = (
            result.get("id")
            or result.get("job_id")
            or result.get("data", {}).get("id")
            or result.get("base_resp", {}).get("id")
        )
        if not job_id:
            raise Exception(
                "MiniMax 未返回 job_id,响应: " + str(result)[:300]
            )
        return job_id

    async def get_video_status(self, job_id: str) -> Dict[str, Any]:
        """获取视频生成状态。

        注意: 状态端点路径与创建端点保持一致(/video_generation/{id}),
        旧版 /video/generations/{id} 是早期 OpenAI 风格的猜测,已修正。
        """
        url = self.base_url.rstrip('/') + f"/video_generation/{job_id}"

        headers = {
            "Authorization": 'Bearer ' + self.api_key,
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=headers)

        if response.status_code != 200:
            raise Exception("API Error: " + response.text)

        result = response.json()
        # 兼容多种返回结构
        video_url = (
            result.get("video_url")
            or result.get("output", {}).get("video_url")
            or result.get("data", {}).get("video_url")
        )
        return {
            "status": result.get("status", "unknown"),
            "video_url": video_url,
        }

    async def poll_video(
        self,
        job_id: str,
        max_wait: int = 600,
        interval: int = 5
    ) -> Dict[str, Any]:
        """轮询视频生成状态,直到完成 / 失败 / 超时。

        返回最后一次 `get_video_status` 的 dict。指数 backoff(5→10→20→30s cap)。
        """
        deadline = time.time() + max_wait
        delay = interval
        last_status: Dict[str, Any] = {}
        while time.time() < deadline:
            try:
                st = await self.get_video_status(job_id)
            except Exception as e:
                # 单次轮询失败不终止 — minimax 偶尔返 5xx
                last_status = {"status": "polling_error", "error": str(e)}
            else:
                last_status = st
                status_lower = (st.get("status") or "").lower()
                if status_lower in ("success", "finished", "completed", "succeeded"):
                    return st
                if status_lower in ("failed", "error", "cancelled"):
                    return st
            await asyncio.sleep(delay)
            delay = min(delay * 2, 30)
        # 超时: 返回最后一次状态(由 caller 决定怎么处理)
        return last_status or {"status": "timeout"}

    async def download_video(self, url: str, dest_path: str) -> str:
        """把视频 URL 流式下载到本地。校验 Content-Type 是 video/*。"""
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
            async with client.stream("GET", url) as resp:
                if resp.status_code != 200:
                    raise Exception(f"下载失败 {resp.status_code}: {await resp.aread()[:200]!r}")
                ct = resp.headers.get("content-type", "")
                # 不强校验,many CDNs 返 application/octet-stream
                if ct and not ct.startswith("video/") and ct != "application/octet-stream":
                    print(f"[minimax] warning: unexpected content-type {ct!r}")
                with dest.open("wb") as f:
                    async for chunk in resp.aiter_bytes(64 * 1024):
                        f.write(chunk)
        return str(dest)

    async def generate_video_and_download(
        self,
        prompt: str,
        duration: int = 6,
        dest_path: Optional[str] = None,
        poll_interval: int = 5,
        poll_max_wait: int = 600,
    ) -> Dict[str, Any]:
        """一站式: 提交 → 轮询 → 下载 → 落盘。返回 dict,任何错误都带 `is_mock=True`。

        成功时:`{job_id, status="ready", local_path, video_url, is_mock=False, model}`
        失败时:`{is_mock=True, error="...", job_id=None}`
        """
        from app.core.config import settings

        try:
            job_id = await self.generate_video(prompt, duration=duration)
        except Exception as e:
            return {"is_mock": True, "error": f"submit failed: {e}"}

        final = await self.poll_video(
            job_id, max_wait=poll_max_wait, interval=poll_interval
        )
        video_url = final.get("video_url")
        status = (final.get("status") or "").lower()
        if not video_url or status not in ("success", "finished", "completed", "succeeded"):
            return {
                "is_mock": True,
                "error": f"video not ready: status={status!r}, video_url={video_url!r}",
                "job_id": job_id,
            }

        # 落盘路径
        if not dest_path:
            safe_id = "".join(c for c in job_id if c.isalnum() or c in "-_")[:32]
            dest_path = str(Path(settings.VIDEOS_DIR) / f"{safe_id}.mp4")

        try:
            local_path = await self.download_video(video_url, dest_path)
        except Exception as e:
            return {
                "is_mock": True,
                "error": f"download failed: {e}",
                "job_id": job_id,
                "video_url": video_url,
            }

        return {
            "is_mock": False,
            "job_id": job_id,
            "status": "ready",
            "video_url": video_url,
            "local_path": local_path,
            "model": "MiniMax-Hailuo-03",
        }

    # ============ 播客脚本生成 ============

    async def generate_podcast_script(
        self,
        content: str,
        style: str = "两主播对话讨论"
    ) -> Dict[str, Any]:
        """生成播客脚本 - 双人对话形式"""
        messages = [
            {"role": "system", "content": """你是一个播客脚本写作专家。
生成为两个角色（主播A和主播B）的对话脚本。
要求：
1. 对话自然、有深度
2. 涵盖内容的核心要点
3. 有问答、有讨论、有总结
4. 约1500-2000字（5-8分钟朗读）"""},
            {"role": "user", "content": f"基于以下内容生成播客脚本：\n\n{content[:8000]}"}
        ]
        script = await self.chat(messages)
        return {
            "script": script,
            "characters": ["主播A", "主播B"],
            "estimated_duration": "5-8分钟"
        }

    # ============ 文案生成 ============

    async def generate_copy(
        self,
        topic: str,
        platform: str,
        content_type: str = "short_video"
    ) -> Dict[str, Any]:
        """生成发布文案"""
        platform_tips = {
            "douyin": "抖音风格：简短有力，有爆点，30字以内",
            "xiaohongshu": "小红书风格：温馨、有干货、带emoji",
            "toutiao": "头条风格：严肃、深度、资讯类",
            "wechat": "公众号风格：深度长文、有深度",
            "youtube": "YouTube风格：英文、SEO友好",
            "bilibili": "B站风格：年轻化、有梗"
        }
        tip = platform_tips.get(platform, "")

        messages = [
            {"role": "system", "content": f"你是自媒体内容专家，擅长生成适合平台的发布文案。\n{tip}"},
            {"role": "user", "content": f"为主题「{topic}」生成文案"}
        ]
        result = await self.chat(messages)
        return {"copy": result, "platform": platform}

    # ============ 脚本生成 ============

    async def generate_video_script(
        self,
        topic: str,
        duration: int = 60
    ) -> Dict[str, Any]:
        """生成视频脚本 - 含分镜建议"""
        messages = [
            {"role": "system", "content": """你是一个视频脚本写作专家。
生成视频脚本，要求：
1. 分镜描述（画面、字幕、配音）
2. 时长控制
3. 节奏把控
4. 开头留人、结尾引导"""},
            {"role": "user", "content": f"为主题「{topic}」生成{duration}秒视频脚本"}
        ]
        script = await self.chat(messages)
        return {"script": script, "duration": duration}