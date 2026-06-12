"""
AI Provider 抽象基类

Phase A.1:把 MiniMax 单一依赖抽成多 provider 模式。
每家 provider 一个 subclass,实现 chat() 接口即可被 factory 返回。
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseProvider(ABC):
    """AI Provider 抽象基类。

    每家 provider 的子类实现 `async chat()` 即可。
    `default_model` 在 subclass 上设,工厂返回时一起带出。
    """

    #: 在 UI 上展示的名字
    label: str = "Base"

    #: Provider 唯一标识,注册表 key
    name: str = "base"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.default_model = default_model

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """同步 chat 端点(非流式)。返回 assistant 文本。"""
        raise NotImplementedError

    def is_configured(self) -> bool:
        """API key 是否已配。可用 provider 才会出现在 /api/config/providers。"""
        return bool(self.api_key)
