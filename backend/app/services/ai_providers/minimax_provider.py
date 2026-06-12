"""
MiniMax provider — 包装现有 MiniMaxClient,作为默认 provider

把 chat() 接口和现有 minimax_client.MiniMaxClient 串起来。
更具体的(image / video / tts / music)走 minimax_client 自己的方法,这里不重复。
"""
from typing import Dict, Any, List, Optional

from app.services.ai_providers.base import BaseProvider
from app.services.minimax_client import MiniMaxClient


class MiniMaxProvider(BaseProvider):
    label = "MiniMax"
    name = "minimax"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
    ):
        super().__init__(api_key, base_url, default_model)
        from app.core.config import settings
        self.api_key = self.api_key or settings.MINIMAX_API_KEY
        self.base_url = self.base_url or settings.MINIMAX_BASE_URL or "https://api.minimaxi.com/v1"
        self.default_model = self.default_model or settings.MINIMAX_MODEL or "MiniMax-M3"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        # MiniMaxClient 接受自己的 model 参数;max_tokens/temperature 走 body
        client = MiniMaxClient(
            api_key=self.api_key,
            base_url=self.base_url,
            model=model or self.default_model,
        )
        return await client.chat(messages, model=model or self.default_model, **kwargs)
