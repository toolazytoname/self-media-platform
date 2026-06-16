# Self-Media Platform 操作手册

> **谁用**:自媒体运营/创作者  
> **目的**:AI 生成 + 多平台分发的内容生产全链路  
> **本手册配 21 张截图,按"做什么"→"在哪点"→"结果"的方式写**

---

## 0. 30 秒看懂架构

```
┌────────────┐   ┌────────────┐   ┌────────────┐
│  ① 来源管理 │──▶│ ② AI 工具  │──▶│ ③ 内容管理 │
│  PDF/URL/   │   │ 摘要/扩写  │   │  草稿 →   │
│  文本/NLM   │   │ /标题/标签 │   │  待审 →   │
└────────────┘   └────────────┘   │  已发布   │
                                  └─────┬──────┘
                                        ▼
                                  ┌────────────┐
                                  │ ④ 审核 →  │
                                  │ ⑤ 平台账号│
                                  │ ⑥ 发布 →  │
                                  │ ⑦ 数据    │
                                  └────────────┘
```

---

## 1. 登录 / 注册

打开 http://localhost:9000 → 跳到登录页。

| 操作 | 步骤 |
|------|------|
| **登录** | 输入用户名 + 密码 → 点「登录」 |
| **注册** | 切到「注册」tab → 用户名(3-32 字符) + 密码(≥6 位) → 点「注册」 |
| **没登录** | 直接访问受保护页 → 自动跳 `/login?redirect=<原路径>`,登录后回原页 |

> 🔑 密码在 `backend/.env` 配置的 JWT_SECRET 签发,有效期 24 小时。

![登录页](images/ui-1-login.png)

---

## 2. 侧边栏导航(按内容生产顺序)

```
📁 来源
   ├─ 来源管理     ← ① 起点的 PDF/URL/文本/NotebookLM
   ├─ 选题库
   └─ 素材库
🤖 AI 工具
   └─ AI 生成      ← ② 摘要/扩写/标题/标签/文案/图像/视频
📄 内容
   ├─ 内容管理     ← ③ 草稿/待审/已发布
   └─ 内容模板
🔁 工作流
   ├─ 审核         ← ④ 待审 → 通过/拒绝
   ├─ 平台账号     ← ⑤ 抖音/小红书/快手/B站/视频号/公众号
   └─ 发布记录     ← ⑥ 真发后看历史
📊 系统
   ├─ 数据         ← ⑦ 看板 + 4 数字 + 2 饼图
   └─ 设置         ← ⑧ 切 AI provider / 换 key
```

---

## 3. 起点:来源管理

> **干什么**:把 PDF 书、公众号文章、NotebookLM 笔记本做成"来源",AI 工具可以从这些来源读内容。

### 3.1 添加 PDF 来源(最常用)

![添加来源弹窗](images/ui-pdf-1-dialog.png)

1. 侧边栏点「来源管理」 → 右上「添加来源」
2. 填「名称」(例:期权入门与精通)
3. 类型选「PDF 文件(自动切章节)」
4. **拖 PDF 到虚线框** 或 点选文件
   - 支持 `.pdf` 单个文件,最大 100MB
5. 上传成功后会显示文件名 +「重新选择」按钮
6. 点「创建」 → 后台自动切章节
7. 弹窗关闭,列表里出现新卡片

**查看章节**:点卡片标题 → 详情页有切分好的章节列表 → 点单个章节看全文

### 3.2 添加 URL / 文本 / NotebookLM

| 类型 | 字段 | 用途 |
|------|------|------|
| URL | `URL` | 公众号文章、博客文章,后续 AI 抓内容 |
| 文本 | `内容`(长文本) | 粘贴现成素材 |
| NotebookLM | 多个 `URL` / `文件` + 可选 `Web 搜索` + `CLI Profile` | 接 Google NotebookLM 走 AI 生成 audio/video/quiz 等多格式 |

### 3.3 NotebookLM 多账号管理

![NotebookLM 弹窗](images/ui-10-nlm-dialog.png)

点「连接 NotebookLM」按钮:
- 列表显示所有 profile(灰点=未登录,绿点=已登录)
- **新建 profile**:填名(英文/数字)→ 「新建」
- **浏览器登录**:点「浏览器登录」→ 后端在 Mac 屏幕开 Edge → 你扫码登 Google → cookie 自动落盘,UI 2s 轮询直到「已登录」
- **上传 cookie**:在自己电脑跑 `notebooklm -p X login --browser-cookies chrome` 拿到 `storage_state.json` → 「上传 cookie」选这个文件
- **删除**:点「删除」(default 不可删)

> ⚠️ cookie 含 Google session,别提交到 git。

![来源列表(创建后)](images/ui-pdf-2-in-list.png)

---

## 4. 核心:AI 智能生成

> **干什么**:用 AI 跑摘要/扩写/标题/标签/文案/脚本,真烧 token,值得每一项都跑一次。

### 4.1 内容摘要

把长文/链接/PDF 文本 → 关键要点(150-300 字)。

![摘要示例](images/ui-ai-1-summary.png)

1. 侧边栏点「AI 生成」→ 选「内容摘要」
2. 粘贴正文(≤20000 字符)
3. 选 AI 模型(默认 / MiniMax / Claude / OpenAI)
4. 点「生成摘要」→ 等 5-15s
5. 结果区出现「📝 摘要 (147字)」+ 摘要正文

### 4.2 扩写

短文 → 3 档长度(短 300 / 中 600-800 / 长 1500+)+ 3 种语气(轻松/正式/学术)。

![扩写示例](images/ui-ai-2-expand.png)

- 例:原文 `AI 改写内容创作` → 中 + 轻松 → 500+ 字真实扩写
- 「应用到内容 →」按钮把结果灌进新建内容表单

### 4.3 标题生成

正文 → N 个候选标题(可指定平台 + 风格)。

![标题示例](images/ui-ai-3-titles.png)

- 默认 5 个,可调多
- 风格选项:中性 / 标题党 / 学术
- 每个标题卡片有「应用为标题」「复制」按钮

### 4.4 标签提取

正文 → N 个标签,按 **主题 / 情绪 / 受众 / 热点** 自动分组。

![标签示例](images/ui-ai-4-tags.png)

- 例:实测返 "国产大模型M3 + 应用"、"值得推荐 + 情绪"、"内容创作者 + 受众"、"国产大模型 + 热点"
- 「+ 应用」按钮加到当前内容的标签栏

### 4.5 多平台文案

主题 → 不同平台风格文案(抖音钩子 / 小红书种草 / 公众号深度)。

![多平台文案](images/ui-ai-5-copy.png)

- 选平台 → AI 出 3-5 种不同调性方案
- 「复制全文」一键复制

### 4.6 视频脚本 + 播客脚本

- 视频脚本:分镜 + 字幕 + 配音提示词
- 播客脚本:主播 A / 主播 B 对话形式(1500-2000 字 ≈ 5-8 分钟朗读)

### 4.7 视觉创作:图像 / 视频生成

| 功能 | 端点 | 状态 |
|------|------|------|
| 图像 | `image-01` 模型 | 真实生成,1-4 张 |
| 视频 | `MiniMax-Hailuo-03`,3/6/10s,**3 条/日限额** | 提交 → 后台轮询 status → 落盘本地 |

---

## 5. 内容管理

![内容列表](images/ui-2-content.png)

### 5.1 列表操作

- **筛选**:搜索(标题/正文) / 状态(草稿/待审/已发布/失败/上传中) / 平台
- **翻页**:每页 20 条
- **导出**:右上「导出 JSON / Markdown / CSV」(整批)
- **新建**:右上「新建内容」
- **每条卡片**:查看 / 编辑 / 提交审核 / 复制 / 删除

### 5.2 创建内容

![创建内容](images/ui-3-content-create.png)

1. 右上「新建内容」
2. 填标题(≤200)、正文(≤100000,支持 Markdown)
3. 选标签(回车添加) + 目标平台
4. 三个 AI 辅助按钮(填了内容才能激活):
   - **扩写** — 把短文拉长
   - **摘要** — 把长文压短
   - **改写文案** — 改语气风格
5. 「创建内容」→ 跳回列表,新卡片出现

![创建后](images/ui-4-after-create.png)

### 5.3 状态机

```
[草稿] ──提交审核──▶ [待审]
                          │
                ┌─────────┴─────────┐
                ▼                   ▼
            [已发布]             [草稿] (驳回回流)
```

### 5.4 提交审核

1. 列表上点「提交审核」→ 确认弹窗
2. 状态变 `pending`,创建 review task
3. 跳去「审核」队列

---

## 6. 审核队列

![审核](images/ui-6-review.png)

- 4 tab:全部 / 待审核 / 已通过 / 已拒绝
- 每条显示标题 + 全文 + 提交时间
- 「通过」/「拒绝」按钮 → 弹窗确认
  - 通过 → content 状态变 `published`,可走发布流程
  - 拒绝 → content 状态回 `draft`,退回作者修改

![通过后](images/ui-7-after-approve.png)

---

## 7. 平台账号管理(C 阶段)

> **当前状态**:5 个真发布 adapter 已写(sau CLI 走 Patchright 浏览器自动化)+ 公众号草稿箱

### 7.1 添加账号(预跑)

> ⚠️ 真发布需要先安装 `sau` CLI + 跑登录,**用户在系统级操作**:

```bash
# 1. 在 VM 里装 sau(系统级,不是 pip 包)
pipx install social-auto-upload
# 或: uv tool install social-auto-upload
sau --version
```

### 7.2 登录账号(任一平台)

每个平台账号对应一份 cookie:
- `sau douyin login --account creator`  → 弹 Chromium,扫抖音创作者中心 QR
- `sau xiaohongshu login --account personal`  → 扫小红书
- `sau kuaishou login --account partner`  → 扫快手
- `sau bilibili login --account mybili`  → 扫 B 站
- 视频号无 CLI,需额外 import `tencent_uploader` 库

cookie 落 `~/.sau/cookies/<platform>/<account>.json`,sau 自己管。

### 7.3 UI 端:选择账号 + 立即发布

(在 `/platforms` 页面)

1. 点「添加账号」 → 选平台 → 填账号名(对应 sau CLI 的 `--account` 值)
2. 列表显示所有账号
3. 选一条 `已发布` 状态 content → 「立即发布」→ 选账号 → 真发
4. 「发布记录」页面看历史

> **公众号说明**:WeChat MP 公开 API 只能写到**草稿箱**。要真发需在 MP 后台人工扫码或用已认证服务号的 access_token。**不能 100% 自动化**。

### 7.4 平台支持矩阵

| 平台 | 真实发布 | 视频 | 图文 | 备注 |
|------|---------|------|------|------|
| 抖音 | ✅ | ✅ | ✅ | 最完整 |
| 小红书 | ✅ | ✅ | ✅ | 走浏览器 |
| 快手 | ✅ | ✅ | ✅ | 走浏览器 |
| B 站 | ✅ | ✅ | ❌ | 自动装 biliup |
| 视频号 | ⚠️ 需 Python import | ✅ | ❌ | 走 tencent_uploader 库 |
| 公众号 | ⚠️ 草稿箱 only | ❌ | ✅ | 写草稿,真发需 MP 后台 |

---

## 8. 发布记录

看历史:
- 状态:pending / publishing / published / failed
- 平台、账号、内容、时间
- 失败看 error_message,Cookie 过期就回 7.2 重登

---

## 9. 数据看板

![数据](images/ui-15-stats.png)

- **4 数字卡**:内容总数 / 选题 / 素材 / 待审核
- **2 饼图**:平台发布分布 + 内容状态分布
- **汇总**:发布记录 / 已连接平台 / 调度任务

实时反映,新建/发布/审核通过后数字+1。

---

## 10. 设置

![设置](images/ui-16-settings.png)

3 个 AI provider 卡片(当前默认: MiniMax):
- 填 API Key(带前缀占位) + Base URL + 默认模型
- 「测试连接」验通 → 「保存」→ 立即生效
- 「设为默认」把当前 provider 提到首位

新增/换 key 不用重启后端。

---

## 11. 端到端完整流程(实战示例:做一篇公众号深度文)

按实战顺序,1 个工作流跑完整个系统:

| 步骤 | 在哪 | 做什么 |
|------|------|--------|
| 1 | /sources | 拖 PDF 进弹窗,创建来源 `期权入门与精通` |
| 2 | /ai → 扩写 | 原文填短句 → AI 扩到 600-800 字 |
| 3 | /ai → 标题 | 扩写结果填入 → 选 5 个标题 |
| 4 | /ai → 标签 | 选 8 个标签(主题/情绪/受众/热点) |
| 5 | /content | 新建内容,粘贴扩写正文,选标题和标签,平台选「公众号」 |
| 6 | /content | 提交审核 → 状态变 `pending` |
| 7 | /review | 点「通过」→ 状态变 `published` |
| 8 | /platform | 选公众号账号 → 「立即发布」→ 写草稿箱(真发需 MP 后台) |
| 9 | /publish-records | 看记录状态 |
| 10 | /stats | 看数字 +1 |

---

## 12. 常见问题

| 问题 | 解决 |
|------|------|
| 登录页跳到 /content 立刻被踢回 /login | localStorage 里 token 过期 → 重新登录 |
| 401 Unauthorized | 后端重启了 → token 还在但 secret 改了 → 重新登录 |
| AI 报错 "响应无 choices 字段" | key 配错了 / model 名错 / 网络问题 → 看后端日志的真实响应 |
| 视频生成报 "MiniMax 未返回 job_id" | key 限额触发了 → 等或换 key |
| PDF 拖上去后 preview 是乱码 | 扫描版 PDF 无文字层 → 这是物理限制,真要文字用 OCR(paddleocr/tesseract,不在本系统) |
| 公众号发布报错 | 默认就是写草稿箱,需要在 MP 后台「群发」 |
| NotebookLM 浏览器登录无反应 | 没装 `notebooklm-py[browser]`;VM 里没 GUI(无头环境)需要 Xvfb |
| 侧边栏顺序跟我不一样 | 这是 v1.0 的顺序(A1 重排前),升级后会按"来源→AI→内容→工作流→系统"展示 |

---

## 13. 部署 / 启动速查

```bash
# 后端(8000)
cd /Users/lazy/Code/crack/claude/self-media-platform
bin/devbox run bash -c '
  cd /mnt/mac/Users/lazy/Code/crack/claude/self-media-platform/backend
  nohup ./.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/smp-8000.log 2>&1 & disown
'

# 前端(9000)
bin/devbox run bash -c '
  cd /mnt/mac/Users/lazy/Code/crack/claude/self-media-platform/frontend
  setsid nohup pnpm dev </dev/null >/tmp/smp-frontend.log 2>&1 & disown
'

# 装外部 CLI(可选)
pipx install social-auto-upload
pipx install "notebooklm-py[browser]"
```

| 端点 | 地址 |
|------|------|
| 前端 | http://localhost:9000 |
| 后端 API | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |
| 后端日志 | /tmp/smp-8000.log |
| 前端日志 | /tmp/smp-frontend.log |
| SQLite | `backend/storage/smp.db` |
| 上传 PDF | `backend/storage/uploads/` |
| AI 视频 | `backend/storage/videos/` |
| 平台 cookie | `backend/storage/cookies/` |

---

## 14. 截图速查

| 截图 | 页面 |
|------|------|
| `ui-1-login.png` | 登录 |
| `ui-2-content.png` | 内容管理列表 |
| `ui-3-content-create.png` | 创建内容 |
| `ui-4-after-create.png` | 创建后 |
| `ui-5-after-submit.png` | 提交审核后 |
| `ui-6-review.png` | 审核队列 |
| `ui-7-after-approve.png` | 审核通过后 |
| `ui-8-topic.png` | 选题库(空) |
| `ui-9-sources.png` | 来源管理(空) |
| `ui-10-nlm-dialog.png` | NotebookLM 多账号弹窗 |
| `ui-11-ai.png` | AI 智能生成主页 |
| `ui-12-templates.png` | 内容模板 |
| `ui-13-platform.png` | 平台账号(空) |
| `ui-14-publish.png` | 发布记录(空) |
| `ui-15-stats.png` | 数据看板 |

---

## 15. 新功能(2026-06 迭代)

> P0-1 / P0-2 / P0-3 三轮迭代,后端 API 全部就绪并通过单元/集成测试。
> 部分前端 UI 在 P1 阶段补齐,本章同时给出"API 用法"和"UI 状态"。

### 15.1 选题雷达 / 爆款发现 (P0-2)

> **干什么**:聚合 4 平台热榜(微博/知乎/抖音/小红书)→ AI 改写为初始选题 → 一键创建为草稿。
> **状态**:**后端 API ✅**(50+ 测试通过),前端 UI 在 P1 补齐(API 已可手动调用)。

#### 手动 API 流程(无需前端 UI)

```bash
# 1. 登录拿 token
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"你的用户","password":"密码"}' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")

# 2. 抓 4 平台热榜(网络 fail 返 mock 兜底)
curl -s -X POST http://127.0.0.1:8000/api/hot/refresh \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head -30

# 3. 看列表(按平台过滤)
curl -s "http://127.0.0.1:8000/api/hot?platform=weibo&limit=10" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# 4. AI 改写单条热榜 → 自媒体角度(消耗 LLM token)
curl -s -X POST http://127.0.0.1:8000/api/hot/rewrite/<hot_id> \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"n":3, "tone":"casual"}'

# 5. 一键创建为草稿 Content
curl -s -X POST http://127.0.0.1:8000/api/hot/<hot_id>/create-content \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
# → {"content_id": "content_xxx"}  然后跳 /content/edit/<id>
```

#### 端点契约

| 端点 | 方法 | 鉴权 | 说明 |
|------|------|------|------|
| `/api/hot` | GET | ✅ | 列表,支持 `?platform=weibo&status=new&limit=50` |
| `/api/hot/refresh` | POST | ✅ | 抓取,支持 `?platform=weibo` 单独刷一个 |
| `/api/hot/rewrite/{id}` | POST | ✅ | AI 改写为角度(消耗 LLM) |
| `/api/hot/{id}/create-content` | POST | ✅ | 创建草稿 Content,关联 `related_content_id` |
| `/api/ai/hot-rewrite` | POST | ❌ | 单独 AI 改写端点,接收 `hot_title + platform` |

#### 第三方数据源

默认走 `https://api.vvhan.com/api/hotlist?type=wbHot/zhihuHot/douyinHot/xhsHot`,**无需 API key**。
如果网络不通,**自动降级**到 4×5 条 mock 兜底数据,前端任何时候都能 demo。

---

### 15.2 一稿多发 / 平台改写引擎 (P0-3)

> **干什么**:同主题 → 并发 4 平台 LLM 改写(公众号 5000 字 / 小红书 500 字 / 抖音 200 字脚本 / 知乎 2000 字)→ 用户挑喜欢的版本落库。
> **状态**:**后端 API ✅**(16/16 测试通过),前端 UI 在 P1 补齐(API 已可手动调用)。

#### 手动 API 流程

```bash
# 1. 改写 — 不需 auth,纯文本生成
curl -s -X POST http://127.0.0.1:8000/api/ai/adapt \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "DeepSeek V4 对自媒体的 3 个机会",
    "length_hint": "medium",
    "source_excerpt": "可选,给 LLM 看一段原文..."
  }' | python3 -m json.tool

# → {
#     "topic": "...",
#     "variants": [
#       {"platform": "wechat",     "title": "...", "body": "...", "char_count": 3200},
#       {"platform": "xiaohongshu", "title": "...", "body": "...", "char_count": 600},
#       {"platform": "douyin",     "title": "...", "body": "...", "char_count": 250},
#       {"platform": "zhihu",      "title": "...", "body": "...", "char_count": 1800}
#     ],
#     "failed": [],
#     "elapsed_ms": 18432
#   }

# 2. 选定一个 variant 落库(需 auth)
curl -s -X POST http://127.0.0.1:8000/api/ai/adapt/save \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "<从 variant 拿的 title>",
    "body": "<从 variant 拿的 body>",
    "platform": "wechat",
    "tags": ["AI", "DeepSeek"],
    "source_topic": "DeepSeek V4 对自媒体的 3 个机会"
  }'
# → {"content_id": "content_xxx"}  跳 /content/edit/<id>
```

#### 平台调性(`PLATFORM_TIPS` 模板)

| 平台 | 字数 | 核心约束 |
|------|------|---------|
| **wechat 公众号** | 3000-5000 | 深度长文、专业有观点、有数据/案例、小标题清晰 |
| **xiaohongshu** | 500-800 | emoji 多用、口语化闺蜜感、首图钩子、数字具体 |
| **douyin 抖音** | 200-300 | 前 3 秒钩子抓人、分镜清晰(画面+字幕+配音)、结尾引导互动 |
| **zhihu 知乎** | 1500-2500 | 逻辑严谨、引用数据/来源、先说结论、有反思深度 |

#### 端点契约

| 端点 | 方法 | 鉴权 | 说明 |
|------|------|------|------|
| `/api/ai/adapt` | POST | ❌ | 并发改写, 4 平台同时调 LLM(单平台 fail 不阻塞) |
| `/api/ai/adapt/save` | POST | ✅ | 落库为草稿 Content,带 `source_topic` 字段追踪一稿多发 |

#### 失败处理

- 单平台 LLM 抛异常 → 该平台进 `failed` 列表,其他 3 个仍正常返回
- 全部失败 → `variants=[]`, `failed=[4 平台]`
- `/save` 端点需登录(创建内容是个人资源)

---

### 15.3 公众号全自动图文混排 (P0-1)

> **干什么**:从 Content 一键发到公众号,**端到端全自动**(图床上传 → 草稿写入 → 派发 → 轮询发布结果 → 返文章 URL)。
> **状态**:**后端 API ✅**(50/50 测试通过) + **前端 UI ✅**("发布到公众号"按钮已上线,Content 详情页)。

#### 前端 UI 流程(已有)

1. 打开任一 Content 详情页 (`/content/<id>`)
2. 右上角点「**发布到公众号**」(绿色按钮,disabled if 没封面图)
3. 弹窗:
   - 选公众号账号(已在 平台账号 创建的)
   - 看封面预览 + 内联图计数
4. 点「**确认发布**」 → 30s 内弹结果
5. 成功 → 弹文章 URL(`https://mp.weixin.qq.com/s?__biz=...`),点开就是公众号文章
6. 失败 → toast 错误分类(图床失败 / 草稿失败 / 派发失败 / 审核失败)

#### 全自动流程(后端 4 步串行)

```
Content.body
   ↓ 1. (P0-7) Markdown → 套主题渲染 → 带 inline-CSS HTML
   ↓ 2. 解析 <img src="远程URL">
   ↓ 3. 下载到 STORAGE_DIR/images/wechat_inline/ + 上传 uploadimg
   ↓ 4. rewrite_html 替换 src 为 mmbiz.qpic.cn URL
   ↓ 5. material/add_material 上传封面 → 永久素材 thumb_media_id
   ↓ 6. draft/add 写草稿 → 草稿 id
   ↓ 7. freepublish/submit 派发 → publish_id
   ↓ 8. 轮询 freepublish/get,2s 间隔,30s 超时
   ↓
返回 {status: published, article_url, freepublish_id, theme, ...}
```

#### 主题选择(P0-7 集成)

`publish-article-now` 支持 `theme` 字段(default/grace/simple),发布前自动套用。
若 body 已是 HTML(<p>/<img> 等),**跳过**主题渲染(避免转义已有标签)。

#### 前置:公众号测试号

需要微信公众号**测试号**或**正式号**:
1. 登录 https://mp.weixin.qq.com
2. 开发 → 基本配置 → 拿 AppID + AppSecret
3. **必须启用"发布能力"**(默认关闭,在 开发 → 接口权限 申请)
4. 回本平台 平台账号 → 新建账号 → 平台选「公众号」→ 填 AppID + AppSecret

#### 端点契约

| 端点 | 方法 | 鉴权 | 说明 |
|------|------|------|------|
| `/api/platforms/publish-article-now` | POST | ✅ | 端到端发布,30s 内阻塞,返最终结果 |

请求:
```json
{ "content_id": "content_xxx", "account_id": "acc_xxx", "theme": "grace" }
```

响应(成功):
```json
{
  "status": "published",
  "url": "https://mp.weixin.qq.com/s?__biz=...",
  "platform_publish_id": "100000_xxx",
  "draft_media_id": "draft_xxx",
  "freepublish_id": "100000_xxx",
  "freepublish_status": 0,
  "thumb_media_id": "media_xxx",
  "theme": "grace",
  "error_message": null
}
```

响应(失败分类):
| `error_message` 关键词 | 原因 | 解决 |
|------|------|------|
| `uploadimg 失败` | 单图 > 10MB 或网络 fail | 压缩图片 |
| `draft/add 失败 errcode=40001` | AppID/Secret 错 | 重新填 |
| `freepublish/submit 失败 errcode=58000` | 未启用发布能力 | 去公众号后台申请 |
| `freepublish timed out after 30s` | 审核排队 | 等几分钟后看发布记录 |

#### 失败重试

发布记录存在 `store.publish_records`,有 `freepublish_id`。30s 超时的情况:等几分钟后手动查 `GET /api/platforms/status/<publish_id>` 看是否最终成功。

---

### 15.4 公众号排版引擎 3 主题 (P0-7)

> **干什么**:Markdown → 微信兼容 HTML,3 套主题(default/grace/simple),**所有 CSS inline**(公众号会过滤 `<style>` 标签)。
> **状态**:**后端 API ✅**(35/35 测试通过)。前端 UI 在 P1 补齐(API 已可手动调用)。

#### 主题选择

| 主题 | 风格 | 适合 |
|------|------|------|
| **default(清爽)** | 黑白灰、h1 下边线、h2 左边线、blockquote 浅灰 | 通用科技/商业文 |
| **grace(优雅)** | 暖色调 (#722 / #c37)、h1 dashed 下边线居中、h2 渐变背景 | 文艺 / 生活方式 / 情感文 |
| **simple(极简)** | 纯黑/灰、h1 加粗无装饰、blockquote 极细边 | 短消息 / 通知 / 极简风 |

#### 手动 API 流程

```bash
# 1. 预览(不需要保存,纯渲染)
curl -s -X POST http://127.0.0.1:8000/api/content/format \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "body": "# 期权入门\n\n## 什么是期权\n\n期权是**衍生品**...\n\n> 重要:杠杆高,风险大",
    "theme": "grace"
  }' | python3 -m json.tool

# → {
#     "theme": "grace",
#     "theme_name": "优雅",
#     "body_chars": 30,
#     "html": "<h1 style='...'>期权入门</h1>...",
#     "html_chars": 380
#   }

# 2. (推荐) 直接发布到公众号,带 theme
curl -s -X POST http://127.0.0.1:8000/api/platforms/publish-article-now \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content_id": "content_xxx",
    "account_id": "acc_yyy",
    "theme": "grace"
  }' | python3 -m json.tool
```

#### 支持的 Markdown 元素

| 元素 | 支持 | 例 |
|------|------|-----|
| 标题 | ✅ | `# H1` `## H2` `### H3` |
| 加粗 / 斜体 | ✅ | `**bold**` / `*italic*` |
| 链接 | ✅ | `[文字](https://...)` |
| 图片 | ✅ | `![alt](https://mmbiz.qpic.cn/...)` |
| 列表 | ✅ | `- item` / `* item` |
| 引用块 | ✅ | `> quote` |
| inline code | ✅ | `` `code` `` |
| 代码块 | ✅ | ` ```code``` ` |
| HTML 嵌入 | ⚠️ | 不会 escape 但建议用 markdown |
| 表格 | ❌ | 不支持(用列表代替) |

#### 设计选择

- **为什么用 placeholder 保护 inline 标签?** 普通 escape 会把 `<strong>` 标签也转义成 `&lt;strong&gt;` 失效。
- **为什么用纯 Python 解析 markdown?** 公众号场景简单,加 mistune/markdown 库不值。
- **为什么 3 套主题?** baoyu-post-to-wechat 设计验证 3 套覆盖 80% 场景;更多主题运营成本高。
- **HTML 输入会跳过主题**:避免转义已有 `<img>` 标签。

#### 端点契约

| 端点 | 方法 | 鉴权 | 说明 |
|------|------|------|------|
| `/api/content/format` | POST | ✅ | 预览(不保存),返 theme_name + html |
| `/api/platforms/publish-article-now` | POST | ✅ | `theme` 字段(P0-7 集成),发布前自动套主题 |

---

---

## 16. 配套文档

| 文档 | 说明 |
|------|------|
| [CHANGELOG.md](./CHANGELOG.md) | 已完成任务归档 + commit SHA + 验证结果 |
| [TASKS.md](./TASKS.md) | 活跃任务进度,会话重启指引 |
| [roadmap-2026-h1.md](./roadmap-2026-h1.md) | 2026 H1 路线图 + P0/P1/P2 排期 |
| [competitor-analysis-2026.md](./competitor-analysis-2026.md) | 行业 11 款工具横评 + 借鉴清单 |
| `ui-16-settings.png` | 设置 |
| `ui-pdf-1-dialog.png` | PDF 拖拽弹窗 |
| `ui-pdf-2-in-list.png` | PDF 创建后列表 |
| `ui-ai-1-summary.png` ~ `ui-ai-5-copy.png` | 5 个 AI 功能实跑结果 |

---

**有任何问题**:
- 后端报错 → 看 `/tmp/smp-8000.log`
- 前端报错 → 浏览器 DevTools Console / `/tmp/smp-frontend.log`
- 进度文档:`docs/A2C-phase-progress-2026-06-14.md`
- 工作流总览:`docs/content-production-workflow.md`
