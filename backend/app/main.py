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
    settings as settings_api
)
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    print("🚀 Self-Media Platform 启动中...")
    yield
    # 关闭时
    print("👋 Self-Media Platform 关闭")


app = FastAPI(
    title="Self-Media Platform",
    description="自媒体内容分发平台：AI生成 + 多平台分发 + CMS管理",
    version="1.0.0",
    lifespan=lifespan
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


@app.get("/")
async def root():
    return {"message": "Self-Media Platform API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}