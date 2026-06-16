# FastAPI 应用入口
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api import (
    content,
    ai_generate,
    platforms,
    scheduler,
    cms,
    settings as settings_api,
    auth as auth_api,
    templates as templates_api,
    sources as sources_api,
    hot,  # P0-2: 选题雷达
    style,  # P1-1: 文风克隆
    metrics,  # P1-2: 数据回流
)
from app.core.config import settings
from app.services.scheduler_loop import scheduler_loop
from app.services.ai_providers import register_provider
from app.services.ai_providers.minimax_provider import MiniMaxProvider
from app.services.ai_providers.claude_provider import ClaudeProvider
from app.services.ai_providers.openai_provider import OpenAIProvider


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    print("🚀 Self-Media Platform 启动中...")
    # Phase A: 注册 AI providers
    register_provider("minimax", MiniMaxProvider)
    register_provider("claude", ClaudeProvider)
    register_provider("openai", OpenAIProvider)
    print(f"   AI providers: minimax / claude / openai (default: {settings.DEFAULT_AI_PROVIDER})")
    # Phase 2: 确保视频 / cookie / 上传 目录存在
    Path(settings.STORAGE_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.VIDEOS_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.COOKIES_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.UPLOADS_DIR).mkdir(parents=True, exist_ok=True)
    # Phase 6: SQLite 持久化 — 启动时建表 + 从 DB 加载回内存
    from app.db.init_db import init_db, load_into_store
    init_db()
    loaded = load_into_store()
    print(f"   💾 SQLite: tables ready, {loaded} rows loaded into memory")
    # 初始化默认模板
    templates_api.init_default_templates()
    # 启动后台调度循环
    scheduler_loop.start()
    print(f"✅ 后台调度循环已启动 (interval={scheduler_loop.interval}s)")
    yield
    # 关闭时
    print("👋 Self-Media Platform 关闭")
    await scheduler_loop.stop()


app = FastAPI(
    title="Self-Media Platform",
    description="自媒体内容分发平台：AI生成 + 多平台分发 + CMS管理",
    version="1.1.0",
    lifespan=lifespan,
    redirect_slashes=False,  # 不要 307 重定向, 前端用无尾斜杠路径
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(content.router, prefix="/api/content", tags=["内容管理"])
app.include_router(ai_generate.router, prefix="/api/ai", tags=["AI生成"])
app.include_router(platforms.router, prefix="/api/platforms", tags=["平台管理"])
app.include_router(scheduler.router, prefix="/api/scheduler", tags=["调度管理"])
app.include_router(cms.router, prefix="/api/cms", tags=["CMS"])
app.include_router(settings_api.router, prefix="/api/config", tags=["设置"])
app.include_router(auth_api.router, prefix="/api/auth", tags=["认证"])
app.include_router(templates_api.router, prefix="/api/templates", tags=["模板"])
app.include_router(sources_api.router, prefix="/api/sources", tags=["来源管理"])


# P0-2: 选题雷达 / 热榜聚合
app.include_router(hot.router, prefix="/api/hot", tags=["热榜雷达"])


# P1-1: 去 AI 味 / 文风克隆
app.include_router(style.router, prefix="/api/style", tags=["文风克隆"])


# P1-2: 数据回流闭环
app.include_router(metrics.router, prefix="/api/metrics", tags=["数据回流"])


@app.get("/")
async def root():
    return {
        "message": "Self-Media Platform API",
        "version": "1.1.0",
        "scheduler_running": scheduler_loop.running,
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "scheduler_running": scheduler_loop.running,
    }
