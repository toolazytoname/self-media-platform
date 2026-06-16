# 任务进度跟踪 (TASKS)

> 活页本 — 长程任务用。每个任务独立 section,带状态 + 上下文 + 恢复点。
> 完成后迁移到 CHANGELOG.md。

---

## 当前活跃任务

### TASK-P0-2: 选题雷达 / 爆款发现

- **状态**: in_progress (GREEN ✅ — 33/33 通过;待前端 UI + e2e)
- **优先级**: P0-1 (ROI ⭐⭐⭐⭐⭐)
- **借鉴**: AIWriteX / 易撰 / 新榜小豆芽
- **复杂度**: 中
- **预计**: 1-2 周
- **开始**: 2026-06-16
- **完成**:
- **最近更新**: 2026-06-16 02:25

**目标**
聚合多平台热榜 → AI 改写为初始选题 → 推送给用户 → 一键进入创作流程。

**子任务**
- [x] **2.1 数据模型** — `store.hot_topics[]` + add_hot / list_hot / get_hot / update_hot / delete_hot
- [x] **2.2 hot_list_client.py** — `HotListClient` 类,httpx 抓 vvhan.com 聚合;fetch_weibo/zhihu/douyin/xiaohongshu + fetch_all
- [x] **2.3 后端 CRUD** — `GET /api/hot` / `POST /api/hot/refresh` / `POST /api/hot/rewrite/{id}` / `POST /api/hot/{id}/create-content`
- [x] **2.4 AI endpoint** — `POST /api/ai/hot-rewrite` 模仿 `/ai/titles` 模板
- [ ] **2.5 前端 UI** — `Sources/index.vue` 加"热榜" tab + 卡片网格 + 刷新按钮 + AI 改写按钮 + "应用到内容" 跳 `/content/create?title=&body=&add_tag=`
- [ ] **2.6 端到端 e2e 验证** (Playwright)

**进度备注**
- [00:10] 探索完成
- [00:18] RED 33 个测试(子 agent)
- [00:55] GREEN 全部 33/33 + 50/50 wechat 无 regression
  - 子 agent 跑 TDD GREEN 时撞 Token 限额;接手修复
  - 修复了:HotListClient 类化 / 顶层 fetch_* shim 兼容 mock / naive datetime / FakeAsyncClient params 拼接
  - 5 个 list 测试补 _auth header(子 agent 写漏,5 个与 test_requires_auth 自相矛盾)
  - rewrite 端点用 chat_completion 而非 _timed_chat(让 mock 路径稳定)
  - 修复 1 测试 bug(FakeAsyncClient 不拼接 params,handler 匹配失败)

**关键文件**
- `backend/app/services/hot_list_client.py` (新, HotListClient 类)
- `backend/app/api/hot.py` (新, 4 端点)
- `backend/app/api/ai_generate.py` (+`/hot-rewrite` 端点)
- `backend/app/store.py` (+`hot_topics` + 5 CRUD)
- `backend/app/core/config.py` (+HOT_LIST_*)
- `backend/app/main.py` (注册 hot router)
- `backend/tests/conftest.py` (清 hot_topics)
- `backend/tests/test_hot_list_client.py` (新, 12)
- `backend/tests/test_hot.py` (新, 21)
- `frontend/src/api/hot.ts` (待建)
- `frontend/src/views/Sources/index.vue` (待改)

**下个会话从这里继续**
- [ ] 2.5: `frontend/src/api/hot.ts` — 镜像 `ai.ts` 模式
- [ ] 2.5: `Sources/index.vue` 加 `<el-tab-pane label="热榜" name="trending" />`
- [ ] 2.5: 卡片 grid + 刷新 + AI 改写 + "应用到内容" 按钮(跳 `/content/create?title=&body=&add_tag=`)
- [ ] 2.6: e2e 验证(Playwright) + commit

---

### TASK-P0-3: 一稿多发 / 平台改写引擎

- **状态**: pending
- **优先级**: P0-2 (ROI ⭐⭐⭐⭐)
- **借鉴**: IP Publisher / Copy.ai Workflows
- **复杂度**: 中
- **预计**: 2 周
- **开始**:
- **完成**:

**目标**
同主题 → 自动产出 4 个平台版本:公众号 5000 字长文 / 小红书 500 字笔记 / 抖音 200 字脚本 / 知乎 2000 字回答。

**子任务**
- [ ] **3.1 平台调性模板** — 4 套 system prompt
- [ ] **3.2 一键改写接口** — `/api/content/adapt` 输入 source + 目标平台
- [ ] **3.3 配图建议** — 小红书 9 宫格 / 公众号 6-10 张章节配图
- [ ] **3.4 调度整合** — AI 中心加"多平台适配"入口

**进度备注**

**关键文件**

**下个会话从这里继续**

---

### TASK-P0-10: 视频号 (WeChat Channels) — 快赢

- **状态**: pending
- **优先级**: P0-3 (ROI ⭐⭐⭐)
- **借鉴**: `tencent_uploader` 库
- **复杂度**: 中 (代码量小)
- **预计**: 1 周
- **开始**:
- **完成**:

**目标**
补齐 5→6 平台覆盖,实现 `WeixinChannelsAdapter` 注册到 `_REGISTRY`。

**子任务**
- [ ] **10.1** 选型:tencent_uploader vs 自研
- [ ] **10.2** Adapter 实现
- [ ] **10.3** 测试

**进度备注**

**关键文件**

**下个会话从这里继续**

---

### TASK-P0-7: 公众号排版引擎 (3 套主题)

- **状态**: pending
- **优先级**: P0-4 (ROI ⭐⭐⭐⭐)
- **借鉴**: 135 编辑器 / 壹伴 / wechat-publisher / baoyu (default/grace/simple)
- **复杂度**: 中
- **预计**: 1 周
- **开始**:
- **完成**:

**目标**
Markdown → 微信兼容 HTML,3 套主题(default / grace / simple),CSS 内联。

**子任务**
- [ ] **7.1** CSS 模板 3 套
- [ ] **7.2** 渲染管线
- [ ] **7.3** 前端主题选择器

**进度备注**

**关键文件**

**下个会话从这里继续**

---

## 已完成任务

### TASK-P0-1: 公众号全自动图文混排 ✅
- **完成**: 2026-06-15
- **Commit**: `0e45665`
- **测试**: 50/50 passed
- **验证**: Playwright AI 全链路 + 端到端 API
- **详情**: 详见 CHANGELOG.md

---

## 操作约定 (给 agent)

1. **接到新任务**: 在"当前活跃任务"加 section,状态 pending
2. **开始做**: 状态改 in_progress,填"开始"时间 + "关键文件"
3. **每完成子任务**: 勾选 checkbox,在"进度备注"加一行(谁/做了什么/测试结果)
4. **完成**: 状态改 completed,移到"已完成任务",记录 commit SHA
5. **断点恢复**: 下次会话先 `cat docs/TASKS.md`,从"下个会话从这里继续"读起
6. **里程碑必存档** — 不要只在 conversation 里讲,必须写到文件
