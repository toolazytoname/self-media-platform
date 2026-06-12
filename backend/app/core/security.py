# 安全工具：JWT Token 生成 / 校验 / 密码哈希
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import bcrypt
import jwt

from app.core.config import settings

# bcrypt 的有效负载上限是 72 字节;超长密码按规范应在应用层截断。
# 这里用 [:72] 显式截断,避免 bcrypt>=4.1 抛 ValueError。
_BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    """对密码进行 bcrypt 哈希"""
    pwd = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(pwd, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文密码与哈希是否匹配"""
    try:
        pwd = plain.encode("utf-8")[:_BCRYPT_MAX_BYTES]
        return bcrypt.checkpw(pwd, hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(
    subject: str,
    extra: Optional[Dict[str, Any]] = None,
    expires_minutes: Optional[int] = None,
) -> str:
    """
    生成 JWT access token.
    subject: 用户唯一标识（用户名/id）
    extra:   payload 中追加的字段
    """
    expire = datetime.utcnow() + timedelta(
        minutes=expires_minutes if expires_minutes is not None else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload: Dict[str, Any] = {
        "sub": str(subject),
        "exp": int(expire.timestamp()),
        "iat": int(datetime.utcnow().timestamp()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    解码 JWT, 返回 payload 字典。失败返回 None。
    """
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# FastAPI 依赖注入辅助
from fastapi import Header, HTTPException, status


async def get_current_user(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    """
    从 Authorization Header 解析当前用户。
    返回 None 表示未登录（用于可选登录的接口）。
    """
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    payload = decode_token(parts[1])
    if not payload:
        return None
    return {"username": payload.get("sub"), **payload}


async def require_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """强制要求登录的依赖。"""
    user = await get_current_user(authorization)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
