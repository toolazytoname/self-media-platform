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
    MINIMAX_MODEL: str = "MiniMax-M3"

    # OpenAI 备选
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Claude (Anthropic)
    CLAUDE_API_KEY: Optional[str] = None
    CLAUDE_BASE_URL: str = "https://api.anthropic.com"
    CLAUDE_MODEL: str = "claude-haiku-4-5"

    # Phase A: 默认 AI provider("minimax" / "claude" / "openai")
    DEFAULT_AI_PROVIDER: str = "minimax"

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

    # ===== Phase 2: 视频生成 / 多平台分发 存储 =====
    # 根目录(在 .gitignore 里,运行时自动建)
    STORAGE_DIR: str = "./storage"
    # 生成的视频文件落盘位置
    VIDEOS_DIR: str = ""  # 空时 = STORAGE_DIR/videos
    # 抖音 cookie(由 `sau douyin login` 写入)
    COOKIES_DIR: str = ""  # 空时 = STORAGE_DIR/cookies

    # Phase 2: social-auto-upload CLI 集成
    # `sau` 二进制路径;默认从 PATH 找
    DOUYIN_SAU_BIN: str = "sau"
    # 默认抖音账号名(cookie_path = COOKIES_DIR/{name}.json)
    DOUYIN_DEFAULT_ACCOUNT: str = "default"

    # Phase 2: 视频生成超时/轮询
    SCHEDULER_VIDEO_TIMEOUT_SECONDS: int = 600
    VIDEO_POLL_INTERVAL_SECONDS: int = 5
    VIDEO_POLL_MAX_WAIT_SECONDS: int = 600

    class Config:
        # .env 路径: backend/.env
        env_file = str(ENV_FILE) if ENV_FILE.exists() else None
        env_file_encoding = "utf-8"
        extra = "allow"

    def model_post_init(self, __context):
        """将 VIDEOS_DIR / COOKIES_DIR 在空时自动派生为 STORAGE_DIR 的子目录。"""
        if not self.VIDEOS_DIR:
            self.VIDEOS_DIR = str(Path(self.STORAGE_DIR) / "videos")
        if not self.COOKIES_DIR:
            self.COOKIES_DIR = str(Path(self.STORAGE_DIR) / "cookies")


settings = Settings()