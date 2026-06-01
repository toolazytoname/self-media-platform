# MiniMax API 集成

import os
from typing import Optional, Dict, Any, List
import httpx


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
        """对话生成 - 使用正确的 MiniMax 端点"""
        model = model or self.default_model

        # MiniMax 使用 /text/chatcompletion_v2 端点
        url = self.base_url.rstrip('/') + "/text/chatcompletion_v2"

        headers = {
            "Authorization": 'Bearer ' + self.api_key,
            "Content-Type": "application/json"
        }
        data = {"model": model, "messages": messages}

        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=data)

        result = response.json()

        # MiniMax API 返回格式检查
        base_resp = result.get("base_resp", {})
        if base_resp.get("status_code") != 0:
            raise Exception("API Error: " + base_resp.get("status_msg", "Unknown"))

        # MiniMax 成功响应的格式
        choices = result.get("choices", [])
        if choices:
            return choices[0]["message"]["content"]
        else:
            raise Exception("No choices in response: " + str(result))

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
        model: str = "MiniMax-Image-01"
    ) -> str:
        """图像生成 - 返回图片URL"""
        url = self.base_url.rstrip('/') + "/images/generations"
        
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
        return result["data"][0]["url"]

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
        """视频生成 - 返回视频URL (限额3条/日)"""
        url = self.base_url.rstrip('/') + "/video/generations"
        
        headers = {
            "Authorization": 'Bearer ' + self.api_key,
            "Content-Type": "application/json"
        }
        data = {
            "model": "MiniMax-Video",
            "prompt": prompt,
            "duration": duration
        }
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=data)
        
        if response.status_code != 200:
            raise Exception("API Error: " + response.text)
        
        result = response.json()
        return result["id"]

    async def get_video_status(self, job_id: str) -> Dict[str, Any]:
        """获取视频生成状态"""
        url = self.base_url.rstrip('/') + f"/video/generations/{job_id}"
        
        headers = {
            "Authorization": 'Bearer ' + self.api_key,
        }
        
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=headers)
        
        if response.status_code != 200:
            raise Exception("API Error: " + response.text)
        
        result = response.json()
        return {
            "status": result.get("status", "unknown"),
            "video_url": result.get("output", {}).get("video_url") if "output" in result else None
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