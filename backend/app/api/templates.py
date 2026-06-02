# 内容模板 API
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List

from app.store import store

router = APIRouter()


VALID_CATEGORIES = {"article", "video_script", "podcast", "copy", "other"}


class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    category: str = Field("article")
    description: str = ""
    body: str = Field(..., min_length=1)


class TemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = None
    description: Optional[str] = None
    body: Optional[str] = None


@router.post("", status_code=201)
async def create_template(req: TemplateCreate):
    if req.category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category: {req.category}")
    return store.add_template(req.model_dump())


@router.get("")
async def list_templates(category: Optional[str] = None):
    if category and category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
    return store.list_templates(category=category)


@router.get("/{template_id}")
async def get_template(template_id: str):
    item = store.get_template(template_id)
    if not item:
        raise HTTPException(status_code=404, detail="Template not found")
    return item


@router.put("/{template_id}")
async def update_template(template_id: str, update: TemplateUpdate):
    if update.category and update.category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category: {update.category}")
    item = store.update_template(template_id, update.model_dump(exclude_unset=True))
    if not item:
        raise HTTPException(status_code=404, detail="Template not found")
    return item


@router.delete("/{template_id}")
async def delete_template(template_id: str):
    if not store.delete_template(template_id):
        raise HTTPException(status_code=404, detail="Template not found")
    return {"message": "deleted", "id": template_id}


# 初始化默认模板（首次启动时）
DEFAULT_TEMPLATES = [
    {
        "name": "公众号深度文章",
        "category": "article",
        "description": "结构完整的公众号长文模板：钩子 + 3-5 段 + 总结 + CTA",
        "body": "# 标题\n\n## 开场钩子\n\n（一句反常识 / 数据 / 问题抓住读者）\n\n## 核心观点 1\n（数据 + 案例 + 解读）\n\n## 核心观点 2\n（数据 + 案例 + 解读）\n\n## 核心观点 3\n（数据 + 案例 + 解读）\n\n## 总结\n（3 句话回顾核心观点）\n\n## 互动引导\n（引导点赞 / 收藏 / 关注）",
    },
    {
        "name": "抖音短视频脚本",
        "category": "video_script",
        "description": "60 秒抖音脚本：钩子 + 3 段内容 + 引导",
        "body": "【0-3s 钩子】\n（反问 / 震惊 / 利益点）\n\n【3-20s 痛点】\n（场景还原 + 痛点放大）\n\n【20-45s 解决方案】\n（3 个要点快节奏）\n\n【45-60s 收尾】\n（结果展示 + 引导）",
    },
    {
        "name": "小红书种草笔记",
        "category": "copy",
        "description": "小红书爆款笔记：标题 + 痛点 + 测评 + 总结",
        "body": "🌟 标题党：xxx 真的 yyds！\n\n📌 自用感受：\n（产品/服务背景）\n\n✨ 优点 1：\n✨ 优点 2：\n✨ 优点 3：\n\n⚠️ 缺点 / 注意：\n（保持真实感）\n\n🏷️ #标签1 #标签2 #标签3",
    },
    {
        "name": "播客对话脚本",
        "category": "podcast",
        "description": "双主播对话式播客脚本模板",
        "body": "【开场 - 自我介绍 + 本期话题】\nA: ...\nB: ...\n\n【话题引入 - 引发兴趣】\n\n【深度讨论 - 3 个核心问题】\nQ1: ...\nQ2: ...\nQ3: ...\n\n【观点碰撞 - 不同视角】\n\n【总结 - 金句 + 行动建议】\n\n【结束语 + 下期预告】",
    },
]


def init_default_templates():
    """启动时确保默认模板存在"""
    if not store.templates:
        for tpl in DEFAULT_TEMPLATES:
            store.add_template(tpl)
