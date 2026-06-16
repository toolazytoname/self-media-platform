"""去 AI 味 / 文风克隆 — P1-1 API

端点:
  GET  /api/style/profile     取当前用户的 StyleProfile
  POST /api/style/refresh     重新分析用户历史 content → 写入 store
  POST /api/style/score       输入一段文字, 返 0-100 风格一致性评分
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.security import require_user
from app.store import store
from app.services.style_profile import (
    DEFAULT_EMPTY_PROFILE,
    StyleProfile,
    build_style_prompt,
    extract_profiles,
    profile_to_dict,
    score_text_against_profile,
)

log = logging.getLogger("style")

router = APIRouter()


# ============ Helpers ============

def _get_user_id(user: Dict[str, Any]) -> str:
    """从 JWT 拿 user id (用户名)."""
    return user.get("username", "default")


def _load_user_corpus(user_id: str) -> List[str]:
    """拉该用户所有 content body, 作为风格分析语料。"""
    items = [
        c for c in store.contents
        if c.get("owner") == user_id or c.get("user_id") == user_id
        or _is_user_content(c, user_id)
    ]
    bodies = [c.get("body", "") for c in items if c.get("body")]
    return bodies


def _is_user_content(c: Dict, user_id: str) -> bool:
    """粗略判断 content 是否属该 user — store 现在不一定记 owner,用 created_by 字段"""
    return c.get("created_by") == user_id or not c.get("owner")


# ============ 端点 ============

@router.get("/profile")
async def get_profile(_user=Depends(require_user)):
    """取当前用户 StyleProfile(空用户返 DEFAULT_EMPTY_PROFILE)。"""
    user_id = _get_user_id(_user)
    profile = store.user_style_profiles.get(user_id, DEFAULT_EMPTY_PROFILE)
    return profile_to_dict(profile)


@router.post("/refresh")
async def refresh_profile(_user=Depends(require_user)):
    """重新分析用户历史 content → 更新 StyleProfile。"""
    user_id = _get_user_id(_user)
    corpus = _load_user_corpus(user_id)
    profile = extract_profiles(corpus)
    # 落库(per-user)
    store.user_style_profiles[user_id] = profile
    return profile_to_dict(profile)


class ScoreRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20000)


@router.post("/score")
async def score_text(req: ScoreRequest, _user=Depends(require_user)):
    """给输入文字打 0-100 风格一致性分(用当前用户的 profile)。"""
    user_id = _get_user_id(_user)
    profile = store.user_style_profiles.get(user_id, DEFAULT_EMPTY_PROFILE)
    score = score_text_against_profile(req.text, profile)
    return {
        "score": score,
        "profile_sample_size": profile.sample_size,
        "prompt_hint": build_style_prompt(profile),  # 给用户参考
    }


# ============ 内部用:让 LLM 调用注入风格 ============

def make_chat_with_style(user_id: str):
    """helper: 返回一个包装 chat_completion 的函数,自动注入用户 StyleProfile。

    用法(在 chat_completion 调用处):
        from app.api.style import make_chat_with_style
        chat = make_chat_with_style(user_id)
        result = await chat(messages, ...)
    """
    from app.api.ai_generate import chat_completion
    profile = store.user_style_profiles.get(user_id, DEFAULT_EMPTY_PROFILE)
    prompt_suffix = build_style_prompt(profile)
    if not prompt_suffix:
        return chat_completion

    async def _chat_with_style(messages, **kwargs):
        # 注入到 system prompt 末尾
        if messages and messages[0].get("role") == "system":
            messages = [{"role": "system", "content": messages[0]["content"] + "\n\n" + prompt_suffix}] + list(messages[1:])
        else:
            messages = [{"role": "system", "content": prompt_suffix}] + list(messages)
        return await chat_completion(messages, **kwargs)

    return _chat_with_style
