# Self-Media Platform - 自媒体内容管理平台

一个基于 AI 的自媒体内容创作与多平台分发管理系统。

## 🚀 Phase 2 视频生成 + 多平台分发(NEW)

### 架构

```
AI 文字 → MiniMax-Hailuo-03 → .mp4 落盘
                                   ↓
                       抖音 douyin 平台账号 + cookie
                                   ↓
                          `sau douyin upload-video`
                          (social-auto-upload + patchright Chromium)
                                   ↓
                            发布记录 + 状态回流
```

### 一次性环境准备

```bash
# 1. 在部署机器上(同 atelier-smp VM 即可)装 social-auto-upload
pipx install social-auto-upload

# 2. 第一次登录抖音(扫码,30 秒,cookie 落盘到 ~/.local/share/sau/douyin/)
sau douyin login --account default

# 3. 把 cookie 复制到本项目期望的位置(默认路径由 settings.COOKIES_DIR 决定)
mkdir -p backend/storage/cookies
cp ~/.local/share/sau/douyin/default.json backend/storage/cookies/default.json

# 4. 在 backend/.env 配真实的 MiniMax API key(否则 video gen 走 mock)
echo "MINIMAX_API_KEY=your_real_key" >> backend/.env
```

### 跑通路径

1. 登录 web: `cd frontend && pnpm dev`
2. 打开 AI tab → 视频子 tab → 填 prompt → 点 "生成视频"
3. 切到 "发布记录" → "发布视频" → 选内容 + 视频 + 抖音 + 账号 → 立即发布
4. 看到 dispatch 结果;失败的话看 error_message 排

### Mock / 降级

- 没装 `sau`:`GET /api/platforms/sau-status` 返 `sau_installed: false`
- 没 `MINIMAX_API_KEY` 或 API 返 5xx:视频落 `storage/videos/{vid}.mp4.mock`,`is_mock=true`,前端不播放
- mock 视频尝试发布:dispatch 直接拒(不让浪费 sau 调用)

### 代码结构

```
backend/app/
├── platforms/
│   ├── base.py            # 抽象基类
│   ├── douyin.py          # 抖音 adapter(subprocess wrapper)
│   └── __init__.py        # 工厂 get_adapter()
├── services/
│   ├── minimax_client.py  # + poll_video / download_video / generate_video_and_download
│   └── scheduler_loop.py  # 真派发,替代 stub
├── api/
│   ├── ai_generate.py     # + VideoRecord / video/list / video/{id} / video/{id}
│   ├── platforms.py       # + publish-now / sau-status / cookie_path 字段
│   └── content.py         # + media_urls / video_id / video_url / video_duration
└── store.py               # + videos / get_account / update_account / 扩展 publish_record
```

## 📁 项目结构

```
self-media-platform/
├── backend/              # FastAPI 后端 (Python)
│   ├── app/
│   │   ├── api/          # API 路由
│   │   │   ├── content.py     # 内容管理
│   │   │   ├── platforms.py  # 平台配置
│   │   │   ├── ai_generate.py # AI 生成
│   │   │   ├── scheduler.py  # 定时任务
│   │   │   ├── settings.py   # 系统设置
│   │   │   └── cms.py        # CMS 接口
│   │   ├── core/         # 核心配置
│   │   ├── services/     # 业务服务 (MiniMax API)
│   │   └── platforms/    # 平台适配器
│   ├── requirements.txt
│   └── .env.example      # 环境变量模板
│
├── frontend/             # Vue 3 前端
│   ├── src/
│   │   ├── views/       # 页面组件
│   │   │   ├── Content/     # 内容管理
│   │   │   ├── Platform/    # 平台管理
│   │   │   └── Settings/    # 设置页面
│   │   ├── router/      # 路由配置
│   │   └── App.vue      # 根组件
│   └── package.json
│
├── docker-compose.yml   # Docker 部署配置
├── .gitignore          # Git 忽略配置
└── README.md
```

## 🚀 快速开始

### 前置要求

- Python 3.9+
- Node.js 18+
- Redis (可选，用于定时任务)

### 1. 克隆项目

```bash
git clone https://github.com/toolazytoname/self-media-platform.git
cd self-media-platform
```

### 2. 后端启动

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入您的 MiniMax API Key

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 4. 访问

- 前端: http://localhost:3000
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

## ⚙️ 配置

### 环境变量 (.env)

```env
# MiniMax API 配置
MINIMAX_API_KEY=your_api_key_here
MINIMAX_BASE_URL=https://api.minimaxi.com/v1
MINIMAX_MODEL=MiniMax-M3
```

> **注意**: 请从 [MiniMax 开放平台](https://platform.minimaxi.com) 获取 API Key

## 🎯 核心功能

### 1. 内容管理
- [ ] 选题管理
- [ ] 素材库
- [ ] 内容队列
- [ ] 审核流程

### 2. AI 智能生成
- [x] 内容摘要
- [x] 播客脚本生成
- [x] 多平台文案生成
- [x] 视频脚本生成
- [ ] 图片生成
- [ ] 视频生成

### 3. 多平台分发
- [x] 平台配置管理
- [ ] 抖音
- [ ] 小红书
- [ ] B站
- [ ] 今日头条
- [ ] 微信公众号
- [ ] YouTube

### 4. 数据统计
- [ ] 播放量统计
- [ ] 收益分析
- [ ] 趋势图表

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| **后端** | FastAPI (Python 3.9+) |
| **前端** | Vue 3 + TypeScript + Vite |
| **UI 组件** | Element Plus |
| **AI 服务** | MiniMax Max (M3/M2.7) |
| **数据库** | PostgreSQL |
| **对象存储** | MinIO (S3 兼容) |
| **任务调度** | Celery + Redis |
| **容器化** | Docker + Docker Compose |

## 📦 Docker 部署

```bash
# 一键启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 🔧 开发指南

### API 接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/config` | 获取配置 |
| POST | `/api/config/test` | 测试 AI 连接 |
| POST | `/api/config` | 更新配置 |
| POST | `/api/ai/summary` | 内容摘要 |
| POST | `/api/ai/podcast/script` | 播客脚本 |
| POST | `/api/ai/copy` | 文案生成 |
| POST | `/api/ai/video/script` | 视频脚本 |
| GET | `/api/content` | 内容列表 |
| POST | `/api/content` | 创建内容 |
| GET | `/api/platforms` | 平台列表 |
| POST | `/api/platforms` | 添加平台 |

### 目录说明

- `backend/app/api/` - API 路由定义
- `backend/app/services/` - 业务逻辑和外部服务集成
- `backend/app/platforms/` - 各平台 API 适配器
- `frontend/src/views/` - Vue 页面组件
- `frontend/src/api/` - 前端 API 调用封装

## 📝 待完成功能

- [ ] 用户认证系统
- [ ] 内容编辑器和富文本支持
- [ ] 定时自动发布
- [ ] 平台 API 对接 (发布内容)
- [ ] 数据统计 Dashboard
- [ ] 团队协作功能
- [ ] 微信小程序支持

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License