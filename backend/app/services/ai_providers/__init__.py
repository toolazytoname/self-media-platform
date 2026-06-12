"""
AI Provider 工厂 + 注册表

要加新 provider:
  1. 写一个 BaseProvider 子类(参见 minimax_provider.py)
  2. `register_provider("name", YourClass)` 在 main.py lifespan 里
  3. settings.py 加对应环境变量
  4. 前端 Settings 页面加 provider 卡片
"""
from typing import Dict, Type, List, Optional

from app.services.ai_providers.base import BaseProvider

# 注册表:name -> Provider 类
_REGISTRY: Dict[str, Type[BaseProvider]] = {}


def register_provider(name: str, cls: Type[BaseProvider]) -> None:
    """注册 provider。main.py lifespan 调用,也可测试时临时注册 mock。"""
    if name in _REGISTRY:
        # 允许覆盖(测试场景);生产只注册一次
        pass
    _REGISTRY[name] = cls


def get_provider(
    name: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    default_model: Optional[str] = None,
) -> BaseProvider:
    """根据名字取 provider 实例。name 不在注册表里抛 NotImplementedError。"""
    cls = _REGISTRY.get(name)
    if not cls:
        raise NotImplementedError(
            f"AI provider {name!r} 未注册。"
            f"已注册: {supported_providers()}"
        )
    return cls(api_key=api_key, base_url=base_url, default_model=default_model)


def supported_providers() -> List[str]:
    """已注册的 provider name 列表。"""
    return list(_REGISTRY.keys())


def get_default_provider_name() -> str:
    """从 settings 读 DEFAULT_AI_PROVIDER,不在注册表则返 'minimax'。"""
    from app.core.config import settings
    name = (settings.DEFAULT_AI_PROVIDER or "minimax").lower()
    if name not in _REGISTRY:
        # 默认 fallback
        return "minimax"
    return name


__all__ = [
    "BaseProvider",
    "register_provider",
    "get_provider",
    "supported_providers",
    "get_default_provider_name",
]
