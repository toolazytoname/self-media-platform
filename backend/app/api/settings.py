"""
设置 API — Phase A: 多 provider 配置

持久化到 backend/.env(跟现有机制一致):
  - 真 key 形如 sk-... 至少 30 字符 → 写盘
  - 假 key / 空 → 留原值,允许 in-memory 生效
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import os
from pathlib import Path

router = APIRouter()

# .env 路径
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BACKEND_DIR / ".env"


# ============ Request 模型 ============

class ProviderConfig(BaseModel):
    """单 provider 配置(对应一个卡片)"""
    model_config = {"protected_namespaces": ()}
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None


class SettingsUpdate(BaseModel):
    """整批更新所有 provider + 默认 provider"""
    model_config = {"protected_namespaces": ()}
    default_provider: Optional[str] = None
    minimax: Optional[ProviderConfig] = None
    claude: Optional[ProviderConfig] = None
    openai: Optional[ProviderConfig] = None


class TestConnectionRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    provider: str = Field(default="minimax", description="minimax / claude / openai")
    api_key: str = Field(..., min_length=1)
    base_url: str = Field(..., min_length=1)
    model: str = Field(default="MiniMax-M3")


# ============ Provider 元数据(供前端展示) ============

# 注:label/默认 base 在这里 hardcode,避免前端也 hardcode
_PROVIDER_META: Dict[str, Dict[str, str]] = {
    "minimax": {
        "label": "MiniMax",
        "default_base": "https://api.minimaxi.com/v1",
        "default_model": "MiniMax-M3",
        "model_options": "MiniMax-M3,MiniMax-Text-01,abab6.5s-chat,abab6.5-chat",
        "key_prefix": "sk-cp-",
    },
    "claude": {
        "label": "Claude",
        "default_base": "https://api.anthropic.com",
        "default_model": "claude-haiku-4-5",
        "model_options": "claude-haiku-4-5,claude-sonnet-4-6,claude-opus-4-8",
        "key_prefix": "sk-ant-",
    },
    "openai": {
        "label": "OpenAI",
        "default_base": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "model_options": "gpt-4o-mini,gpt-4o,gpt-4-turbo,gpt-3.5-turbo",
        "key_prefix": "sk-",
    },
}


# ============ 路由 ============

@router.get("")
async def get_settings():
    """获取当前设置(全 provider + 默认)"""
    from app.core.config import settings
    providers: Dict[str, Any] = {}
    for name, meta in _PROVIDER_META.items():
        key, base, model = _read_env(name)
        providers[name] = {
            "label": meta["label"],
            "base_url": base,
            "model": model,
            "model_options": meta["model_options"],
            "key_prefix": meta["key_prefix"],
            "api_key_masked": _mask_key(key),
            "configured": bool(key),
        }
    return {
        "default_provider": settings.DEFAULT_AI_PROVIDER or "minimax",
        "providers": providers,
        "configured": bool(_read_env(settings.DEFAULT_AI_PROVIDER)[0]),
    }


@router.get("/providers")
async def list_providers():
    """Provider 元数据(供前端 Settings 渲染,不用 hardcode)"""
    from app.core.config import settings
    items: List[Dict[str, Any]] = []
    for name, meta in _PROVIDER_META.items():
        key, base, model = _read_env(name)
        items.append({
            "name": name,
            "label": meta["label"],
            "default_base": meta["default_base"],
            "default_model": meta["default_model"],
            "model_options": meta["model_options"],
            "key_prefix": meta["key_prefix"],
            "api_key_masked": _mask_key(key),
            "configured": bool(key),
            "is_default": name == (settings.DEFAULT_AI_PROVIDER or "minimax"),
        })
    return {"providers": items, "default": settings.DEFAULT_AI_PROVIDER or "minimax"}


@router.post("")
async def update_settings(payload: SettingsUpdate):
    """更新设置 — 同时写所有 provider + 默认 provider"""
    try:
        from app.core.config import settings

        env_lines = []
        if ENV_FILE.exists():
            with open(ENV_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    env_lines.append(line.rstrip("\n"))

        # 收集所有要写的 (key, value) 对
        all_updates: Dict[str, str] = {}
        if payload.minimax is not None:
            if payload.minimax.api_key: all_updates["MINIMAX_API_KEY"] = payload.minimax.api_key
            if payload.minimax.base_url: all_updates["MINIMAX_BASE_URL"] = payload.minimax.base_url
            if payload.minimax.model: all_updates["MINIMAX_MODEL"] = payload.minimax.model
        if payload.claude is not None:
            if payload.claude.api_key: all_updates["CLAUDE_API_KEY"] = payload.claude.api_key
            if payload.claude.base_url: all_updates["CLAUDE_BASE_URL"] = payload.claude.base_url
            if payload.claude.model: all_updates["CLAUDE_MODEL"] = payload.claude.model
        if payload.openai is not None:
            if payload.openai.api_key: all_updates["OPENAI_API_KEY"] = payload.openai.api_key
            if payload.openai.base_url: all_updates["OPENAI_BASE_URL"] = payload.openai.base_url
            if payload.openai.model: all_updates["OPENAI_MODEL"] = payload.openai.model
        if payload.default_provider:
            all_updates["DEFAULT_AI_PROVIDER"] = payload.default_provider
            settings.DEFAULT_AI_PROVIDER = payload.default_provider  # in-memory

        # 更新现有行
        new_lines = []
        handled = set()
        for line in env_lines:
            replaced = False
            for key, val in all_updates.items():
                if line.startswith(key + "="):
                    if _should_persist(key, val):
                        new_lines.append(f"{key}={val}")
                        os.environ[key] = val
                    else:
                        new_lines.append(line)  # 拒绝可疑值,保留原值
                    handled.add(key)
                    replaced = True
                    break
            if not replaced:
                new_lines.append(line)

        # 追加新 key
        for key, val in all_updates.items():
            if key not in handled and _should_persist(key, val):
                new_lines.append(f"{key}={val}")
                os.environ[key] = val

        ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines) + "\n")

        return {
            "message": "设置已更新",
            "persisted_to": str(ENV_FILE),
            "default_provider": settings.DEFAULT_AI_PROVIDER,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def test_connection(req: TestConnectionRequest):
    """用指定 provider + key 测连接(不再绑死 minimax)"""
    from app.services.ai_providers import get_provider
    try:
        p = get_provider(
            req.provider,
            api_key=req.api_key,
            base_url=req.base_url,
            default_model=req.model,
        )
        # 用 hello 做一次 chat 验证
        result = await p.chat(
            [{"role": "user", "content": "ping"}],
            model=req.model,
            max_tokens=16,
        )
        return {
            "success": True,
            "message": f"连接成功 ({req.provider}: {req.model})",
            "response_preview": (result or "")[:80],
        }
    except ValueError as e:
        return {"success": False, "message": f"配置错误: {e}"}
    except Exception as e:
        msg = str(e)[:300]
        return {"success": False, "message": f"{req.provider} 连接失败: {msg}"}


# ============ helpers ============

def _read_env(provider: str) -> tuple:
    """从 settings + os.environ 读 (api_key, base_url, model)"""
    from app.core.config import settings
    meta = _PROVIDER_META.get(provider, {})
    if provider == "minimax":
        return (
            settings.MINIMAX_API_KEY,
            settings.MINIMAX_BASE_URL,
            settings.MINIMAX_MODEL,
        )
    if provider == "claude":
        return (
            settings.CLAUDE_API_KEY,
            settings.CLAUDE_BASE_URL,
            settings.CLAUDE_MODEL,
        )
    if provider == "openai":
        return (
            settings.OPENAI_API_KEY,
            settings.OPENAI_BASE_URL,
            settings.OPENAI_MODEL,
        )
    return ("", meta.get("default_base", ""), meta.get("default_model", ""))


def _mask_key(k: str) -> str:
    if not k:
        return ""
    if len(k) <= 8:
        return "***"
    return f"{k[:4]}***{k[-4:]}"


def _should_persist(key: str, val: str) -> bool:
    """防止 fake key 污染 .env。"""
    if not val:
        return False
    if not key.endswith("_API_KEY"):
        return True  # 非 key 字段一律写
    # 真 key 至少 30 字符, 以 sk- 开头
    if not val.startswith("sk-"):
        return False
    if len(val) < 30:
        return False
    return True
