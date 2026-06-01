# 平台管理 API

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

router = APIRouter()


# ============ 数据模型 ============

class AccountCreate(BaseModel):
    platform: str
    name: str


class PlatformAccount(BaseModel):
    id: str
    platform: str
    name: str
    status: str = "active"
    created_at: datetime


class PublishRequest(BaseModel):
    content_id: str
    platform: str
    scheduled_time: Optional[datetime] = None


# ============ 平台账号存储 ============

PLATFORM_ACCOUNTS = []  # 临时存储


# ============ 路由 ============

@router.get("/accounts")
async def list_accounts():
    """列出所有平台账号"""
    return PLATFORM_ACCOUNTS


@router.post("/accounts")
async def add_account(req: AccountCreate):
    """添加平台账号（待OAuth）"""
    account = PlatformAccount(
        id=str(uuid.uuid4()),
        platform=req.platform,
        name=req.name,
        created_at=datetime.now()
    )
    PLATFORM_ACCOUNTS.append(account)
    return account


@router.delete("/accounts/{account_id}")
async def delete_account(account_id: str):
    """删除平台账号"""
    global PLATFORM_ACCOUNTS
    for i, acc in enumerate(PLATFORM_ACCOUNTS):
        if acc.id == account_id:
            PLATFORM_ACCOUNTS.pop(i)
            return {"message": "deleted"}
    raise HTTPException(status_code=404, detail="Account not found")


@router.post("/publish")
async def publish_content(req: PublishRequest):
    """发布内容到平台（待实现完整逻辑）"""
    return {
        "publish_id": str(uuid.uuid4()),
        "content_id": req.content_id,
        "platform": req.platform,
        "status": "pending",
        "scheduled_time": req.scheduled_time
    }


@router.get("/status/{publish_id}")
async def get_publish_status(publish_id: str):
    """获取发布状态"""
    return {
        "publish_id": publish_id,
        "status": "pending",
        "progress": 0
    }