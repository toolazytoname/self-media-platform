# 核心配置

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


# backend/.env 路径 (相对当前文件: app/core/config.py -> backend/.env)
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    # 应用
    APP_NAME: str = "Self-Media Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # MiniMax API
    MINIMAX_API_KEY: Optional[str] = None
    MINIMAX_BASE_URL: str = "https://api.minimaxi.com/v1"

    # OpenAI 备选
    OPENAI_API_KEY: Optional[str] = None

    # 数据库
    DATABASE_URL: str = "postgresql://localhost:5432/selfmedia"

    # 对象存储
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "selfmedia"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str = "change-me-in-production-please-use-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    class Config:
        # .env 路径: backend/.env
        env_file = str(ENV_FILE) if ENV_FILE.exists() else None
        env_file_encoding = "utf-8"
        extra = "allow"


settings = Settings()