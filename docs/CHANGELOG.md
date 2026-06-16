# CHANGELOG

> 已完成任务归档。每个 task 带 commit SHA + 测试 + 验证结果。
> 活跃任务在 [TASKS.md](./TASKS.md)。

---

## 2026-06-15 — P0-1 公众号全自动图文混排

- **Commit**: `0e45665 feat(wechat): 全自动公众号图文混排发布 (P0-1)`
- **范围**: 13 文件 / +1915 行
- **测试**: 50/50 wechat 测试通过
  - `test_wechat_cdn.py` (16 用例) — extract/rewrite/download/get_inline_dir
  - `test_wechat_adapter.py` (11 新用例) — uploadimg / submit / get / full-auto 5 个端到端
  - `test_scheduler_loop.py` (3 新用例) — happy / missing cover / adapter raises
- **API 验证** (Playwright + curl):
  - AI 扩写 79字 → 972字 ✅
  - AI 标题/标签/摘要/图像生成 ✅
  - 内容保存 + 列表 ✅
  - `POST /platforms/publish-article-now` 错误路径（无封面 → failed / 无账号 → 404）✅
- **关键模块**:
  - `backend/app/services/wechat_cdn.py` (新) — HTML 解析 + `<img src>` 改写 + 远程图下载
  - `wechat.py` 追加 4 方法: `_upload_inline_image` / `submit_for_publish` / `query_publish_status` / `publish_article_full_auto`
  - `scheduler_loop.publish_wechat_now` (新) — 独立路径不动视频 `_dispatch_task`
- **前端**: `Content/View.vue` 加"发布到公众号"按钮 + dialog; `PublishRecords` 新状态标签
- **设计文档**: [竞品分析](./competitor-analysis-2026.md) / [路线图](./roadmap-2026-h1.md) / [实施计划](../.claude/plans/giggly-greeting-church.md)
- **未做（待 P0-1 v2 增强）**: 主题排版引擎（baoyu 三套主题）/ frontmatter 自动提取
