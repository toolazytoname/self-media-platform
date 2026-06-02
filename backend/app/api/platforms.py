# 平台管理 API
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.store import store
from app.platforms.base import PlatformType, ContentType, PublishStatus

router = APIRouter()


VALID_PLATFORMS = {p.value for p in PlatformType}


# ============ Pydantic 模型 ============

class AccountCreate(BaseModel):
    platform: str
    name: str = Field(..., min_length=1, max_length=100)
    account_id: Optional[str] = None  # 平台上的账号 ID
    description: str = ""


class AccountUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    status: Optional[str] = None  # active/inactive
    description: Optional[str] = None


class PublishRequest(BaseModel):
    content_id: str
    platform: str
    scheduled_time: Optional[datetime] = None


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
    return store.add_account(req.model_dump())


@router.put("/accounts/{account_id}")
async def update_account(account_id: str, update: AccountUpdate):
    """更新平台账号"""
    for acc in store.platform_accounts:
        if acc.get("id") == account_id:
            for k, v in update.model_dump(exclude_unset=True).items():
                if v is not None:
                    acc[k] = v
            return acc
    raise HTTPException(status_code=404, detail="Account not found")


@router.delete("/accounts/{account_id}")
async def delete_account(account_id: str):
    """删除平台账号"""
    if not store.delete_account(account_id):
        raise HTTPException(status_code=404, detail="Account not found")
    return {"message": "deleted", "id": account_id}


@router.post("/publish", status_code=201)
async def publish_content(req: PublishRequest):
    """发布内容到平台（创建发布记录）"""
    if req.platform not in VALID_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {req.platform}")

    # 验证内容存在
    content = store.get_content(req.content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    # 创建发布记录
    record = {
        "content_id": req.content_id,
        "content_title": content.get("title"),
        "platform": req.platform,
        "scheduled_time": req.scheduled_time.isoformat() if req.scheduled_time else None,
        "status": "scheduled" if req.scheduled_time else "pending",
    }
    record = store.add_publish_record(record)

    # 如果是定时发布，创建调度任务
    if req.scheduled_time:
        store.add_scheduled_task({
            "content_id": req.content_id,
            "platform": req.platform,
            "scheduled_time": req.scheduled_time.isoformat(),
            "status": "pending",
            "publish_id": record["publish_id"],
        })

    return record


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
