# 平台管理 API
import os
import shutil
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.store import store
from app.core.config import settings
from app.platforms.base import PlatformType, ContentType, PublishStatus
from app.platforms import supported_platforms

router = APIRouter()


VALID_PLATFORMS = {p.value for p in PlatformType}


# ============ Pydantic 模型 ============

class AccountCreate(BaseModel):
    platform: str
    name: str = Field(..., min_length=1, max_length=100)
    account_id: Optional[str] = None  # 平台上的账号 ID
    description: str = ""
    cookie_path: Optional[str] = None  # Phase 2: sau 的 storage_state 路径


class AccountUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    status: Optional[str] = None  # active/inactive
    description: Optional[str] = None
    cookie_path: Optional[str] = None


class PublishRequest(BaseModel):
    content_id: str
    platform: str
    scheduled_time: Optional[datetime] = None
    account_id: Optional[str] = None  # Phase 2: 多账号
    video_id: Optional[str] = None    # Phase 2: 关联视频


class PublishNowRequest(BaseModel):
    """前端 "立即发布视频" 按钮"""
    content_id: str
    platform: str
    account_id: str
    video_id: str


# ============ 路由 ============

@router.get("/accounts")
async def list_accounts():
    """列出所有平台账号"""
    return store.list_accounts()


@router.post("/accounts", status_code=201)
async def add_account(req: AccountCreate):
    """添加平台账号"""
    if req.platform not in VALID_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {req.platform}")
    data = req.model_dump()
    # cookie_path 缺省 = storage/cookies/{name}.json
    if not data.get("cookie_path"):
        data["cookie_path"] = str(Path(settings.COOKIES_DIR) / f"{data['name']}.json")
    return store.add_account(data)


@router.put("/accounts/{account_id}")
async def update_account(account_id: str, update: AccountUpdate):
    """更新平台账号(用 store.update_account,行为一致)"""
    payload = update.model_dump(exclude_unset=True)
    acc = store.update_account(account_id, payload)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    return acc


@router.delete("/accounts/{account_id}")
async def delete_account(account_id: str):
    """删除平台账号"""
    if not store.delete_account(account_id):
        raise HTTPException(status_code=404, detail="Account not found")
    return {"message": "deleted", "id": account_id}


@router.post("/publish", status_code=201)
async def publish_content(req: PublishRequest):
    """发布内容到平台（创建发布记录;Phase 2 可选绑 account + video）"""
    if req.platform not in VALID_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {req.platform}")

    content = store.get_content(req.content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    # 优先用请求里的 video_id, 否则用 content.video_id
    video_id = req.video_id or content.get("video_id")

    record = {
        "content_id": req.content_id,
        "content_title": content.get("title"),
        "platform": req.platform,
        "scheduled_time": req.scheduled_time.isoformat() if req.scheduled_time else None,
        "status": "scheduled" if req.scheduled_time else "pending",
        "account_id": req.account_id,
        "video_id": video_id,
    }
    record = store.add_publish_record(record)

    # 定时发布:同时建调度任务
    if req.scheduled_time:
        store.add_scheduled_task({
            "content_id": req.content_id,
            "platform": req.platform,
            "scheduled_time": req.scheduled_time.isoformat(),
            "status": "pending",
            "publish_id": record["publish_id"],
            "account_id": req.account_id,
            "video_id": video_id,
        })

    return record


@router.post("/publish-now")
async def publish_now(req: PublishNowRequest):
    """前端"立即发布"按钮 — 同步派发,返回 dispatch summary。
    不走 scheduler tick,直接调 scheduler_loop.publish_now。
    """
    if req.platform not in VALID_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {req.platform}")
    if PlatformType(req.platform) not in supported_platforms():
        raise HTTPException(
            status_code=501,
            detail=f"platform {req.platform} 暂未实装 adapter。已支持: "
                   f"{[p.value for p in supported_platforms()]}",
        )
    from app.services.scheduler_loop import scheduler_loop
    result = await scheduler_loop.publish_now(
        content_id=req.content_id,
        platform=req.platform,
        account_id=req.account_id,
        video_id=req.video_id,
    )
    return result


@router.get("/publish/records")
async def list_publish_records(status: Optional[str] = None):
    """列出发布记录"""
    return store.list_publish_records(status=status)


@router.get("/status/{publish_id}")
async def get_publish_status(publish_id: str):
    """获取发布状态"""
    record = store.get_publish_record(publish_id)
    if not record:
        raise HTTPException(status_code=404, detail="Publish record not found")
    return record


@router.get("/sau-status")
async def sau_status(account_id: Optional[str] = None):
    """健康检查: sau 是否装、版本、默认 cookie 路径等。
    帮前端 Settings / PublishRecords 提示用户该跑什么命令。
    """
    from app.platforms.douyin import _resolve_sau_bin
    sau_bin = _resolve_sau_bin(getattr(settings, "DOUYIN_SAU_BIN", "sau"))
    info: Dict[str, Any] = {
        "sau_installed": bool(sau_bin),
        "sau_bin": sau_bin,
        "videos_dir": settings.VIDEOS_DIR,
        "cookies_dir": settings.COOKIES_DIR,
        "default_account": settings.DOUYIN_DEFAULT_ACCOUNT,
        "supported_platforms": [p.value for p in supported_platforms()],
        "login_command": (
            f"{sau_bin} douyin login --account {settings.DOUYIN_DEFAULT_ACCOUNT}"
            if sau_bin else None
        ),
    }
    if account_id:
        acc = store.get_account(account_id)
        if acc:
            cookie_path = acc.get("cookie_path") or ""
            info["account_id"] = acc.get("id")
            info["account_name"] = acc.get("name")
            info["account_platform"] = acc.get("platform")
            info["cookie_path"] = cookie_path
            info["cookie_exists"] = bool(cookie_path) and Path(cookie_path).is_file()
    else:
        # 默认账号的 cookie 状态
        default_cookie = str(Path(settings.COOKIES_DIR) / f"{settings.DOUYIN_DEFAULT_ACCOUNT}.json")
        info["cookie_path"] = default_cookie
        info["cookie_exists"] = Path(default_cookie).is_file()
    return info
