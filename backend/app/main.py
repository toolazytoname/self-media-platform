# FastAPI 应用入口
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
)
from app.core.config import settings
from app.services.scheduler_loop import scheduler_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    print("🚀 Self-Media Platform 启动中...")
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
