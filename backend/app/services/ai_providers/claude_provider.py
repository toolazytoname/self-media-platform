"""
Claude provider — 直接 HTTP 调 Anthropic Messages API

不引 anthropic SDK(零额外依赖),用项目里已有的 httpx。
"""
from typing import Dict, Any, List, Optional
import httpx

from app.services.ai_providers.base import BaseProvider


# Anthropic 当前 API 版本
ANTHROPIC_API_VERSION = "2023-06-01"

# Claude 默认模型(可以 env 覆盖)
DEFAULT_CLAUDE_MODEL = "claude-haiku-4-5"


class ClaudeProvider(BaseProvider):
    label = "Claude"
    name = "claude"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
    ):
        super().__init__(api_key, base_url, default_model)
        from app.core.config import settings
        self.api_key = self.api_key or settings.CLAUDE_API_KEY
        # Anthropic 没有"base URL"概念但有等价物,允许走代理
        self.base_url = self.base_url or settings.CLAUDE_BASE_URL or "https://api.anthropic.com"
        self.default_model = self.default_model or settings.CLAUDE_MODEL or DEFAULT_CLAUDE_MODEL

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        if not self.api_key:
            raise ValueError("Claude API key 未配置 (CLAUDE_API_KEY)")

        # Anthropic Messages API 需要 system / user 分开
        system_parts: List[str] = []
        user_messages: List[Dict[str, str]] = []
        for m in messages:
            if m.get("role") == "system":
                system_parts.append(m.get("content", ""))
            else:
                user_messages.append(m)

        body: Dict[str, Any] = {
            "model": model or self.default_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": user_messages,
        }
        if system_parts:
            body["system"] = "\n\n".join(system_parts)

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_API_VERSION,
            "content-type": "application/json",
        }

        url = f"{self.base_url.rstrip('/')}/v1/messages"
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(url, headers=headers, json=body)

        if r.status_code != 200:
            raise Exception(f"Claude API Error {r.status_code}: {r.text[:500]}")

        data = r.json()
        # 标准响应格式
        content = data.get("content", [])
        text_parts = [b.get("text", "") for b in content if b.get("type") == "text"]
        result = "".join(text_parts)
        if not result:
            # 错误结构
            err = data.get("error", {})
            raise Exception(
                f"Claude no text in response: {err.get('message') or data!r}"
            )
        return result
