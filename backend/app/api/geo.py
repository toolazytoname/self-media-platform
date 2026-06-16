"""GEO 优化 API — P1-3

端点:
  POST /api/geo/check       评估一段文字的 GEO 友好度
  POST /api/geo/optimize    AI 改写为 GEO-friendly 版本
  GET  /api/geo/checklist   返通用 GEO 优化 checklist(空文本 / 教学用)
"""
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.security import require_user
from app.services.geo_service import (
    DEFAULT_CHECKLIST,
    build_geo_checklist,
    score_geo_friendliness,
)
# 顶层 import 让测试 patch app.api.geo.chat_completion 能命中
from app.api.ai_generate import chat_completion

log = logging.getLogger("geo")

router = APIRouter()


class CheckRequest(BaseModel):
    text: str = Field(..., min_length=0, max_length=20000)


class OptimizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20000)
    provider: Optional[str] = None
    model: Optional[str] = None
    target_score: int = Field(70, ge=0, le=100, description="目标 GEO 评分")


@router.post("/check")
async def check(req: CheckRequest, _user=Depends(require_user)):
    """评估一段文字的 GEO 友好度,返 score + 6 维 breakdown + checklist。"""
    result = score_geo_friendliness(req.text, return_breakdown=True)
    return {
        "score": result["score"],
        "checklist": result["dimensions"],
    }


@router.post("/optimize")
async def optimize(req: OptimizeRequest, _user=Depends(require_user)):
    """AI 改写为 GEO-friendly 版本。

    流程:
      1. 先 check 当前 score
      2. 调 chat_completion, system prompt 注入 GEO 改写指令
      3. 返原 score + 改写后文本 + 改写后 score
    """
    original = score_geo_friendliness(req.text, return_breakdown=True)
    original_score = original["score"]

    system = (
        "你是 GEO 优化专家(Generative Engine Optimization)。"
        "你的任务是把用户给的普通文章改写为'AI 搜索引擎(ChatGPT/DeepSeek/文心/豆包/Kimi)"
        "更愿意推荐'的版本。\n\n"
        "GEO 改写 6 维指南:\n"
        "1. FAQ 段: 文末加 'FAQ:' 段, 列 3-5 个 '什么是 X?' / '怎么 Y?' + 短答\n"
        "2. 具体数据: 加 年份(2024 年) / 百分比(增长 30%) / 金额(1.2 万亿)\n"
        "3. 来源引用: 加 1-3 个权威链接 + '据 X 报告' / '来源: Y'\n"
        "4. 问题词: 段首/小标题用 '什么是' / '怎么' / '为什么'\n"
        "5. 段落短: 单段 ≤ 200 字(AI 搜索结果常截短段)\n"
        "6. 概念定义: 'X 是 Y' 或 'X 指 Y' 明确定义关键概念\n\n"
        f"目标 GEO 评分 ≥ {req.target_score}。"
        "改写时保持原文核心信息,不要瞎编数据(数字要合理)。"
    )
    user_msg = (
        f"原文:\n{req.text}\n\n"
        f"原文 GEO 评分: {original_score} / 100\n"
        f"逐维评分: {original['dimensions']}\n\n"
        "请输出改写后的完整文章。"
    )
    optimized = await chat_completion(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ],
        model=req.model,
        provider=req.provider,
        max_tokens=2048,
    )
    optimized_result = score_geo_friendliness(optimized, return_breakdown=True)

    return {
        "original_score": original_score,
        "original_checklist": original["dimensions"],
        "optimized": optimized,
        "optimized_score": optimized_result["score"],
        "optimized_checklist": optimized_result["dimensions"],
    }


@router.get("/checklist")
async def get_checklist(_user=Depends(require_user)):
    """返通用 GEO 优化 checklist(空文本参考 / 教学用)。"""
    return DEFAULT_CHECKLIST
