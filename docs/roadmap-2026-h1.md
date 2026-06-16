# 2026 H1 路线图 — 借鉴行业 + 全自动图文混排

> 起止：2026 H1（基于 [competitor-analysis-2026.md](./competitor-analysis-2026.md)）
> 核心主题：**从"半自动"补成"全自动"** — 公众号真发布、选题主动发现、一稿多发。

---

## P0 — 必须做

### 1. 公众号全自动图文混排

**问题**：当前 `WeChatAdapter.publish_article` 只调 `cgi-bin/draft/add` 写草稿箱，要人工到公众号后台点"发布"。

**目标**：端到端自动 — 上传图床 → HTML 内联图片 → 写入草稿 → 调 `freepublish/submit` 派发 → 轮询状态直到发布成功（`freepublish/get` 返回 `publish_status = 4`）。

**子任务**：
- [ ] **1.1 图床上传** — 调 `cgi-bin/media/uploadimg` 拿 `https://mmbiz.qpic.cn/...` 永久 URL（不是临时素材，正文用这个）
- [ ] **1.2 HTML 图片内联** — 把 `content` HTML 里的 `<img src="本地路径">` 全部替换成 `mmbiz.qpic.cn` 链接（用 BeautifulSoup 或 regex）
- [ ] **1.3 草稿写入** — `cgi-bin/draft/add` 拿到 `media_id`（draft id）
- [ ] **1.4 派发发布** — `cgi-bin/freepublish/submit` 用 draft 的 `media_id` 拿到 `publish_id`
- [ ] **1.5 状态轮询** — `cgi-bin/freepublish/get` 查 `publish_status`（0=成功, 1=审核中, 2=原创审核, 3=校验失败, 4=失败）
- [ ] **1.6 失败重试 + 错误暴露** — 轮询 N 次后超时上报，4 类错误分类提示
- [ ] **1.7 单元 + E2E 测试**（TDD：先写 mock 测试，再实现）

**产出**：`/api/platforms/publish-now` 一键 `status: "published" + 公众号文章 URL`

**参考**：
- [wechat-publisher](https://github.com/jiji262/wechat-publisher) — CDN 上传 + 草稿全流程
- 微信官方文档：`cgi-bin/media/uploadimg` / `cgi-bin/draft/add` / `cgi-bin/freepublish/submit` / `cgi-bin/freepublish/get`

---

### 2. 选题雷达 / 爆款发现

**问题**：当前来源层是被动（用户传 PDF / 链接），没有主动发现机制。

**目标**：聚合多平台热榜 → AI 改写为初始选题 → 推送给用户 → 一键进入创作流程。

**子任务**：
- [ ] **2.1 热榜抓取** — 微博热搜、知乎热榜、抖音榜单、小红书热门标签
- [ ] **2.2 选题 AI 改写** — 接入 minimax/sau provider，把热榜话题改写为"自媒体角度的选题"
- [ ] **2.3 个性化过滤** — 根据用户历史内容做相关性打分（哪些选题跟用户调性更匹配）
- [ ] **2.4 前端 UI** — Sources 页加"热榜"tab，热点列表 + 选题生成按钮

**产出**：用户打开 Sources 看到 5-10 个今日热点 + AI 选题建议。

**参考**：
- [AIWriteX 热搜聚合](https://aiwritex.voidai.cc/)
- [易撰](https://aicats.wiki/2026/04/20/133174.html)
- [新榜小豆芽](https://www.cnblogs.com/clarance/p/19880870)

---

### 3. 一稿多发 — 平台改写引擎

**问题**：当前多平台发布是"同一份内容发到多个平台"，没做平台调性适配。

**目标**：同主题 → 自动产出 4 个平台版本：公众号 3000-5000 字长文 / 小红书 300-500 字笔记 + 9 宫格图 / 抖音 200 字脚本 / 知乎 1500-2000 字回答。

**子任务**：
- [ ] **3.1 平台调性模板** — 4 套 system prompt：公众号（专业+深度）、小红书（闺蜜+emoji+首图钩子）、抖音（前 3 秒钩子+口语）、知乎（专业+逻辑）
- [ ] **3.2 一键改写接口** — `/api/content/adapt` 输入 source content + 目标平台，输出适配版本
- [ ] **3.3 配图建议** — 小红书：自动生成 9 宫格图 / 公众号：根据章节切分生成 6-10 张配图
- [ ] **3.4 调度整合** — AI 中心加"多平台适配"入口

**产出**：一个主题 → 4 个平台版本内容 → 一键分平台发布。

**参考**：
- [IP Publisher](https://github.com/veeicwgy/ip-publisher) — 平台改写核心
- [Copy.ai Workflows](https://stackcoast.com/jasper-vs-copyai-vs-writesonic/)
- [Douyin vs Xiaohongshu vs WeChat Channels 算法分析](https://bluebookdigital.com/douyin-vs-xiaohongshu-vs-wechat-channels-2026-algorithm-differences-and-content-strategy-analysis/)

---

## P1 — 应当做

### 4. 去 AI 味 / 个人文风克隆

**目标**：学习用户历史文章的语气、句式、词汇偏好，输出风格化结果。

**子任务**：
- [ ] **4.1 历史文章收集** — 用户上传的 PDF/链接/已发布内容入库
- [ ] **4.2 风格特征提取** — 句长分布、emoji 频率、段首模式、常用词、口头禅
- [ ] **4.3 文风 prompt 注入** — AI 中心扩写/改写时自动加入"匹配用户文风"指令
- [ ] **4.4 风格对比展示** — 生成前显示"目标风格样本" + 生成后显示"风格一致性评分"

**参考**：
- [AIWriteX 个人文风克隆](https://aiwritex.voidai.cc/)
- [Humanizer-zh](https://github.com/veeicwgy/ip-publisher) (引用)

---

### 5. 数据回流闭环

**问题**：发布完就完了，没有"哪些选题受欢迎"的反馈。

**目标**：发布后自动抓取阅读量/播放量/评论 → 回写到 AI 中心 → 辅助"哪些选题更受欢迎"判断。

**子任务**：
- [ ] **5.1 数据抓取** — 各平台 API/爬虫抓取已发布内容的阅读量、播放量、评论、转发
- [ ] **5.2 数据回写** — 关联 content_id 存到 store
- [ ] **5.3 趋势面板** — 前端统计页：哪些选题表现好、哪个时段发布更有效
- [ ] **5.4 AI 中心利用** — "推荐选题"时优先推历史表现好的类型

**参考**：
- [易媒助手 数据监控](https://www.taojinge.com/zixun/67.html)
- [小火花 跨平台数据看板](https://www.taojinge.com/zixun/67.html)

---

### 6. GEO 优化（新蓝海，前沿机会）

**目标**：跟踪品牌/选题在 DeepSeek / 文心一言 / 豆包 / Kimi 等 AI 搜索结果中的曝光。

**子任务**：
- [ ] **6.1 AI 搜索可见度查询** — 模拟用户问题，向 4 大国内 AI 提问，看品牌/选题是否被推荐
- [ ] **6.2 优化建议** — 输出"哪些词/数据/引用需要补"才能被 AI 搜索推荐
- [ ] **6.3 自动补全** — AI 中心扩写时自动加 GEO 友好内容（结构化数据、Q&A 段、来源链接）

**参考**：
- [Writesonic GEO pivot (2025)](https://stackcoast.com/jasper-vs-copyai-vs-writesonic/)
- [Focus GEO 优化](https://www.cnblogs.com/clarance/p/19880870)

---

## P2 — 可以做

### 7. 排版引擎（公众号专项）

- Markdown → 微信兼容 HTML（CSS 内联，HTML 实体转义）
- 参考 135 编辑器、壹伴、wechat-publisher

### 8. 浏览器扩展 + AI 评论回复

- Chrome 扩展，在平台后台用 AI 回复评论
- 参考 [AiToEarn](https://ezpzai.com/en/2026-05-14-yikart-aitoearn-en/)

### 9. 数字人 / AI 混剪

- 数字人主播（参考腾讯智影、度加）
- AI 混剪防重复（参考聚媒通、易创精灵）

### 10. 视频号 (WeChat Channels)

- 用 `tencent_uploader` 库实现 `WeixinChannelsAdapter`
- 注册到 `_REGISTRY`

---

## 工作量估算

| 任务 | 复杂度 | 预计交付 | 备注 |
|------|--------|---------|------|
| 1. 公众号全自动图文混排 | 中 | 1 周 | TDD 走通即可 |
| 2. 选题雷达 | 中 | 1-2 周 | 涉及多个外部 API |
| 3. 一稿多发 | 中 | 2 周 | AI prompt 调优为主 |
| 4. 去 AI 味 | 高 | 2-3 周 | 文风建模有挑战 |
| 5. 数据回流 | 高 | 3-4 周 | 各平台反爬限制多 |
| 6. GEO 优化 | 高 | 2-3 周 | 全新领域，调研成本高 |

---

## 下一步行动

**立即执行**：P0-1 公众号全自动图文混排（用户明确要求）— 进入 plan mode 设计实施方案。

### 2026-06-15 更新

P0-1 已完成实施(commit 待提交):
- ✅ 1.1-1.7 全部完成
- ✅ `wechat_cdn.py` 工具模块(extract/rewrite/download)
- ✅ `wechat.py` 加 4 个方法:`_upload_inline_image` / `submit_for_publish` / `query_publish_status` / `publish_article_full_auto`
- ✅ `scheduler_loop.py` 加 `publish_wechat_now`(独立路径,不动视频 `_dispatch_task`)
- ✅ 新 API `POST /platforms/publish-article-now`
- ✅ 前端 `Content/View.vue` "发布到公众号" 按钮 + dialog
- ✅ 前端 `PublishRecords/index.vue` 新状态标签(`publishing`/`draft_added`/`freepublish_submitted`)
- ✅ 50/50 wechat 测试通过

**P0-1 v2 增强(借鉴 baoyu skill,2026-06-15)**:
- 主题排版(参考 baoyu-post-to-wechat 的 default/grace/simple 三套主题) — 需做 CSS 模板 + marked 渲染管线
- Markdown frontmatter 自动提取 title/author — Editor 输入 → API 解析

参考: `/Users/lazy/.agents/skills/baoyu-post-to-wechat/`(Chrome CDP 路径,代码不可复用,仅设计思路借鉴)

## 2026-06-16 更新

**P0-2 选题雷达已完成** (commit `977fcaf`):
- ✅ `hot_list_client.py` (HotListClient 类,vvhan.com 聚合 + 网络 fail 兜底 mock)
- ✅ `hot.py` router (list / refresh / rewrite / create-content)
- ✅ `ai_generate.py` 加 `/ai/hot-rewrite` 端点
- ✅ `store.py` 加 hot_topics + 5 CRUD
- ✅ 33/33 hot 测试通过
- ⏳ 前端 UI (Sources 热榜 tab) — P1 补齐

**P0-3 一稿多发已完成** (commit `a4eaf45`):
- ✅ `ai_generate.py` 加 PLATFORM_TIPS 4 平台模板
- ✅ `/api/ai/adapt` 并发改写 (asyncio.gather)
- ✅ `/api/ai/adapt/save` 落库为草稿
- ✅ 16/16 adapt 测试通过
- ⏳ 前端 UI (AI 中心"一稿多发" tab) — P1 补齐

**累计: 99/99 测试通过,3 个 P0 全部完成。**

---

## 参考

- [竞品分析](./competitor-analysis-2026.md)
- [CLAUDE.md 架构说明](../CLAUDE.md)
- [项目交接 PLAN.md](../PLAN.md)
