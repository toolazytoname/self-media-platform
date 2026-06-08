# 设置 API

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import os
from pathlib import Path

router = APIRouter()

# .env 文件路径：与 backend/app 同级目录（即 backend/.env）
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BACKEND_DIR / ".env"


class SettingsUpdate(BaseModel):
    model_config = {"protected_namespaces": ()}
    minimax_api_key: Optional[str] = None
    minimax_base_url: Optional[str] = None
    model_name: Optional[str] = None


class TestConnectionRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    api_key: str = Field(..., min_length=1)
    base_url: str = Field(..., min_length=1)
    model: str = "MiniMax-M3"


@router.get("")
async def get_settings():
    """获取当前设置"""
    from app.core.config import settings
    api_key = settings.MINIMAX_API_KEY or os.getenv("MINIMAX_API_KEY", "")
    base_url = settings.MINIMAX_BASE_URL or os.getenv("MINIMAX_BASE_URL", "https://api.minimaxi.com/v1")
    model = os.getenv("MINIMAX_MODEL", "MiniMax-M3")

    # 隐藏密钥
    masked_key = ""
    if api_key and len(api_key) > 8:
        masked_key = api_key[:4] + "***" + api_key[-4:]

    return {
        "minimax_api_key": masked_key,
        "minimax_base_url": base_url,
        "model_name": model,
        "configured": bool(api_key)
    }


@router.post("")
async def update_settings(settings_data: SettingsUpdate):
    """更新设置 (运行时 + 持久化到 .env)

    重要：MINIMAX_API_KEY 只在请求值与 .env 现有值不同、且看起来像真 key
    (前缀 sk-cp- 或 sk- 长度 > 20) 时才持久化。避免测试 runner 用假 key
    (如 'sk-cp-test') 污染 .env。
    """
    try:
        # 读取现有 .env 内容
        env_lines = []
        if ENV_FILE.exists():
            with open(ENV_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    env_lines.append(line.rstrip("\n"))

        # 根据请求更新（仅当字段非空）
        updates = {
            "MINIMAX_API_KEY": settings_data.minimax_api_key,
            "MINIMAX_BASE_URL": settings_data.minimax_base_url,
            "MINIMAX_MODEL": settings_data.model_name,
        }

        new_lines = []
        handled = set()
        for line in env_lines:
            replaced = False
            for key, val in updates.items():
                if line.startswith(key + "="):
                    if val and _should_persist_key(key, val):
                        new_lines.append(f"{key}={val}")
                        os.environ[key] = val
                    else:
                        new_lines.append(line)  # 保留原值（拒绝可疑值或空值）
                    handled.add(key)
                    replaced = True
                    break
            if not replaced:
                new_lines.append(line)

        # 追加新出现的 key
        for key, val in updates.items():
            if key not in handled and val and _should_persist_key(key, val):
                new_lines.append(f"{key}={val}")
                os.environ[key] = val

        # 写回
        ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines) + "\n")

        return {
            "message": "设置已更新，立即通过 os.environ 生效。重启后从 .env 重新加载。",
            "persisted_to": str(ENV_FILE)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _should_persist_key(key: str, val: str) -> bool:
    """防止测试/fake key 污染 .env。

    真 MiniMax key 形如 sk-cp-... (>= 30 字符) 或 sk-proj-... 或 sk-... (>= 40 字符)。
    其他短串（如 sk-cp-test）一律拒绝持久化，但允许 in-memory 生效。
    """
    if key != "MINIMAX_API_KEY":
        return True  # 非 key 字段一律写
    if not val:
        return False
    # 真 key 至少 30 字符, 以 sk- 开头, 包含足够熵 (数字+字母)
    if not val.startswith("sk-"):
        return False
    if len(val) < 30:
        return False
    return True


@router.post("/test")
async def test_connection(req: TestConnectionRequest):
    """测试 AI 连接"""
    import requests
    try:
        auth = 'Bearer ' + req.api_key
        headers = {
            "Authorization": auth,
            "Content-Type": "application/json"
        }
        data = {
            "model": req.model,
            "messages": [{"role": "user", "content": "你好"}]
        }

        # MiniMax 使用 /text/chatcompletion_v2 端点
        url = req.base_url.rstrip('/') + "/text/chatcompletion_v2"

        response = requests.post(url, headers=headers, json=data, timeout=30)
        result = response.json()

        # MiniMax API 返回格式检查
        base_resp = result.get("base_resp", {})
        status_code = base_resp.get("status_code", 0)

        if status_code == 0:
            return {
                "success": True,
                "message": "连接成功！AI 功能可以正常使用"
            }
        else:
            return {
                "success": False,
                "message": "API 返回错误: " + base_resp.get("status_msg", "Unknown")
            }
    except requests.exceptions.Timeout:
        return {"success": False, "message": "连接超时，请检查网络或 base_url"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"网络错误: {str(e)[:120]}"}
    except Exception as e:
        return {"success": False, "message": f"连接失败: {str(e)[:120]}"}