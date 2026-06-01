# Self-Media Platform - 项目执行计划

> 方便智能体/协作者接手的项目交接文档

---

## 📋 基本信息

| 项目名称 | Self-Media Platform |
|----------|---------------------|
| 仓库地址 | https://github.com/toolazytoname/self-media-platform |
| 状态 | 🚧 开发中 |
| 创建时间 | 2025-06-01 |
| 主要维护者 | @toolazytoname |
| AI 助手 | MiniMax M3 |

---

## 🎯 项目目标

**愿景**：打造一个 AI 驱动的自媒体内容创作与多平台分发系统，实现"一键生成、多平台分发"的自动化变现流程。

**核心场景**：
1. 用户输入主题/素材 → AI 生成多种形式内容
2. 内容审核 → 排期发布
3. 多平台一键分发 → 数据回收

---

## 📊 当前进度

### ✅ 已完成

| 模块 | 功能 | 状态 | 备注 |
|------|------|------|------|
| **后端框架** | FastAPI 基础架构 | ✅ | 含 API 路由、中间件 |
| **配置管理** | MiniMax API 集成 | ✅ | 可测试连接 |
| **AI 生成** | 摘要生成 | ✅ | `/api/ai/summary` |
| **AI 生成** | 播客脚本 | ✅ | `/api/ai/podcast/script` |
| **AI 生成** | 多平台文案 | ✅ | `/api/ai/copy` |
| **AI 生成** | 视频脚本 | ✅ | `/api/ai/video/script` |
| **前端** | 基础页面结构 | ✅ | Vue 3 + Vite |
| **前端** | 平台管理页面 | ✅ | 增删改查 |
| **前端** | 设置页面 | ✅ | API Key 配置 |
| **前端** | AI 生成页面 | ✅ | 表单 + 调用后端 |
| **文档** | README | ✅ | 完整使用文档 |

### 🔄 进行中

| 模块 | 功能 | 状态 | 负责人 |
|------|------|------|--------|
| CMS 后台 | 内容管理 UI | 🔄 | 待开发 |
| 前端 | 内容列表页 | 🔄 | 待开发 |

### ⏳ 待办

| 优先级 | 功能 | 描述 | 备注 |
|--------|------|------|------|
| P0 | 平台 API 对接 | 抖音、小红书、B站等实际发布接口 | 核心功能 |
| P0 | 用户认证 | JWT 登录、权限管理 | 安全必备 |
| P1 | 内容编辑器 | 富文本编辑器，支持 Markdown | |
| P1 | 定时发布 | Celery 定时任务排期 | |
| P2 | 图片生成 | AI 生成配图 | 依赖 Stable Diffusion |
| P2 | 视频生成 | AI 生成视频 | 技术难度高 |
| P2 | 数据统计 | Dashboard 图表 | |
| P3 | 微信小程序 | 移动端支持 | 可选 |

---

## 🔧 技术架构

### 目录结构

```
self-media-platform/
├── backend/
│   ├── app/
│   │   ├── api/           # API 路由入口
│   │   │   ├── __init__.py
│   │   │   ├── content.py    # 内容 CRUD
│   │   │   ├── platforms.py  # 平台配置
│   │   │   ├── ai_generate.py # AI 生成接口
│   │   │   ├── scheduler.py  # 定时任务
│   │   │   ├── settings.py   # 系统设置
│   │   │   └── cms.py        # CMS API
│   │   ├── core/
│   │   │   ├── config.py     # 配置管理
│   │   │   └── security.py   # 安全工具
│   │   ├── models/          # 数据模型 (Pydantic)
│   │   ├── platforms/        # 平台适配器
│   │   └── services/
│   │       ├── minimax.py   # MiniMax API 调用
│   │       └── content.py   # 内容服务
│   ├── main.py              # FastAPI 入口
│   ├── requirements.txt
│   └── .env.example          # 环境变量模板
│
├── frontend/
│   ├── src/
│   │   ├── views/          # 页面组件
│   │   ├── api/             # 前端 API 调用
│   │   ├── router/          # 路由
│   │   └── main.ts
│   ├── package.json
│   └── vite.config.ts
│
└── docker-compose.yml       # Docker 部署
```

### 关键文件说明

| 文件路径 | 作用 | 重要度 |
|----------|------|--------|
| `backend/app/api/ai_generate.py` | AI 生成核心逻辑 | ⭐⭐⭐ |
| `backend/app/services/minimax.py` | MiniMax API 调用封装 | ⭐⭐⭐ |
| `backend/app/core/config.py` | 全局配置 | ⭐⭐ |
| `frontend/src/api/index.ts` | 前端 API 调用封装 | ⭐⭐ |

---

## ⚠️ 注意事项

### 环境要求
- Python 3.9+ (开发环境测试通过)
- Node.js 18+
- Redis (定时任务可选)

### API 密钥
- MiniMax API Key 从 https://platform.minimaxi.com 获取
- 本地 `.env` 文件**不**上传 GitHub（已配置 .gitignore）
- 测试时 API Key 通过 HTTPS 传输，建议定期更换

### 开发规范

1. **API 返回格式**：统一使用 Pydantic 模型
2. **错误处理**：所有 API 必须有错误处理和日志
3. **前端状态管理**：使用 Pinia
4. **Git 提交**：使用 `feat:`、`fix:`、`docs:` 等前缀

### MiniMax API 调用

```python
# 位于 backend/app/services/minimax.py
# 使用流式响应，调用方式：
POST https://api.minimaxi.com/v1
Headers: Authorization: Bearer $API_KEY
Body: {
    "model": "MiniMax-M3",
    "messages": [{"role": "user", "content": "..."}]
}
```

### 平台适配器模式

```
backend/app/platforms/
├── base.py           # 基类，定义统一接口
├── douyin.py         # 抖音适配器
├── xiaohongshu.py    # 小红书适配器
├── bilibili.py       # B站适配器
├── youtube.py        # YouTube 适配器
└── ...
```

每个平台需要实现：
- `auth()` - 获取授权
- `publish(content)` - 发布内容
- `get_stats()` - 获取数据

---

## 🔗 集成参考

以下是项目中计划集成但尚未实现的参考项目：

| 项目 | 地址 | 说明 |
|------|------|------|
| aitoearn | - | AI 变现项目，可参考内容生成逻辑 |
| social-auto-upload | jart/social-auto-upload | 视频自动上传，已实现多平台 |
| NotebookLM | Google 产品 | 内容形式和风格参考 |
| baoyu skill | - | 自媒体全流程参考 |

---

## 🚀 下一步行动

### 立即可做

1. **完善 CMS 内容管理**
   - 内容列表页（增删改查）
   - 内容编辑页（富文本）
   - 审核流程

2. **平台 API 对接（以抖音为例）**
   - 申请抖音开放平台账号
   - 实现 OAuth 授权流程
   - 实现视频上传接口
   - 实现图文发布接口

### 后续迭代

1. 添加用户系统（注册/登录/权限）
2. 实现定时发布任务
3. 开发数据统计 Dashboard

---

## 📞 联系方式

- GitHub Issues: https://github.com/toolazytoname/self-media-platform/issues
- 仓库管理员: @toolazytoname

---

*最后更新: 2025-06-01*