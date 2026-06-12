"""
OpenAI provider — 走 OpenAI 兼容的 chat/completions 端点

兼容:
  - OpenAI 官方(https://api.openai.com/v1)
  - 任何 OpenAI 兼容服务(Ollama / vLLM / LM Studio / Together / Groq …)
  - 注意:minimax 自己的 /v1/chat/completions 也兼容(已在 MiniMaxClient 里有 fallback)
"""
from typing import Dict, Any, List, Optional
import httpx

from app.services.ai_providers.base import BaseProvider


DEFAULT_OPENAI_BASE = "https://api.openai.com/v1"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


class OpenAIProvider(BaseProvider):
    label = "OpenAI"
    name = "openai"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
    ):
        super().__init__(api_key, base_url, default_model)
        from app.core.config import settings
        self.api_key = self.api_key or settings.OPENAI_API_KEY
        self.base_url = self.base_url or settings.OPENAI_BASE_URL or DEFAULT_OPENAI_BASE
        self.default_model = self.default_model or settings.OPENAI_MODEL or DEFAULT_OPENAI_MODEL

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        if not self.api_key:
            raise ValueError("OpenAI API key 未配置 (OPENAI_API_KEY)")

        body: Dict[str, Any] = {
            "model": model or self.default_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(url, headers=headers, json=body)

        if r.status_code != 200:
            raise Exception(f"OpenAI API Error {r.status_code}: {r.text[:500]}")

        data = r.json()
        choices = data.get("choices", [])
        if not choices:
            err = data.get("error", {})
            raise Exception(
                f"OpenAI no choices in response: {err.get('message') or data!r}"
            )
        return choices[0].get("message", {}).get("content", "")
