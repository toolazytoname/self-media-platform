# 设置 API

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os

router = APIRouter()


class SettingsUpdate(BaseModel):
    minimax_api_key: Optional[str] = None
    minimax_base_url: Optional[str] = None
    model_name: Optional[str] = None


class TestConnectionRequest(BaseModel):
    api_key: str
    base_url: str
    model: str = "MiniMax-M3"


@router.get("")
async def get_settings():
    """获取当前设置"""
    from app.core.config import settings
    api_key = settings.MINIMAX_API_KEY or ""
    base_url = settings.MINIMAX_BASE_URL or "https://api.minimaxi.com/v1"
    model = os.getenv("MINIMAX_MODEL", "MiniMax-M3")
    
    # 隐藏密钥
    masked_key = ""
    if api_key and len(api_key) > 8:
        masked_key = api_key[:8] + "***" + api_key[-4:]

    return {
        "minimax_api_key": masked_key,
        "minimax_base_url": base_url,
        "model_name": model,
        "configured": bool(settings.MINIMAX_API_KEY)
    }


@router.post("")
async def update_settings(settings: SettingsUpdate):
    """更新设置"""
    try:
        if settings.minimax_api_key:
            os.environ["MINIMAX_API_KEY"] = settings.minimax_api_key
        if settings.minimax_base_url:
            os.environ["MINIMAX_BASE_URL"] = settings.minimax_base_url
        if settings.model_name:
            os.environ["MINIMAX_MODEL"] = settings.model_name
        
        # 同时保存到文件以便重启后恢复
        env_file = "/Users/lazy/.pilotdeck/projects/self-media-platform/backend/.env"
        with open(env_file, "w") as f:
            f.write("MINIMAX_API_KEY=" + os.environ.get("MINIMAX_API_KEY", "") + "\n")
            f.write("MINIMAX_BASE_URL=" + os.environ.get("MINIMAX_BASE_URL", "https://api.minimaxi.com/v1") + "\n")
            f.write("MINIMAX_MODEL=" + os.environ.get("MINIMAX_MODEL", "MiniMax-M3") + "\n")
        
        return {"message": "设置已更新，重启后生效"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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

        print("DEBUG /config/test:")
        print("  API key length:", len(req.api_key))
        print("  Auth header:", auth[:40] + "...")
        print("  URL:", url)

        response = requests.post(url, headers=headers, json=data, timeout=30)
        result = response.json()

        print("  Response:", result)

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
    except Exception as e:
        return {
            "success": False,
            "message": "连接失败: " + str(e)[:100]
        }