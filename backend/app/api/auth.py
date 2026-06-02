# 用户认证 API
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Optional

from app.core.security import (
    hash_password, verify_password,
    create_access_token, require_user
)
from app.store import store

router = APIRouter()


# ============ Pydantic 模型 ============

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: Optional[str] = Field(None, max_length=100)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=6, max_length=128)


class UserInfo(BaseModel):
    username: str
    display_name: str
    created_at: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInfo


# ============ 路由 ============

@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(req: RegisterRequest):
    """注册新用户"""
    if store.get_user(req.username):
        raise HTTPException(status_code=400, detail="用户名已被占用")
    user = store.add_user({
        "username": req.username,
        "display_name": req.display_name or req.username,
        "password_hash": hash_password(req.password),
    })
    token = create_access_token(user["username"], {"display_name": user["display_name"]})
    return AuthResponse(
        access_token=token,
        user=UserInfo(**{k: user[k] for k in ("username", "display_name", "created_at")})
    )


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    """登录"""
    user = store.get_user(req.username)
    if not user or not verify_password(req.password, user.get("password_hash", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    token = create_access_token(user["username"], {"display_name": user["display_name"]})
    return AuthResponse(
        access_token=token,
        user=UserInfo(**{k: user[k] for k in ("username", "display_name", "created_at")})
    )


@router.get("/me", response_model=UserInfo)
async def me(user: dict = Depends(require_user)):
    """获取当前登录用户信息"""
    u = store.get_user(user["username"])
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return UserInfo(**{k: u[k] for k in ("username", "display_name", "created_at")})
