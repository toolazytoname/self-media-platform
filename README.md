# Self-Media Platform

```
├── backend/           # FastAPI 后端 (Python)
│   ├── app/
│   │   ├── api/       # API路由
│   │   ├── core/      # 核心配置
│   │   ├── models/    # 数据模型
│   │   ├── platforms/ # 平台适配器
│   │   └── services/   # 业务服务 (MiniMax API)
│   └── requirements.txt
│
├── frontend/          # Vue3 前端
│   └── src/
│       ├── views/     # 页面组件
│       │   ├── Content/   # 内容管理
│       │   ├── Topic/     # 选题库
│       │   ├── Material/  # 素材库
│       │   ├── Review/    # 审核
│       │   ├── Platform/  # 平台管理
│       │   ├── AI/        # AI生成
│       │   └── Stats/     # 数据统计
│       ├── router/    # 路由配置
│       └── App.vue    # 根组件
│
├── cms/               # CMS管理后台 (预留)
├── docker-compose.yml # Docker部署
├── README.md
└── SPEC.md           # 详细规格文档
```

## 快速开始

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
```

## 技术栈

- **后端**: FastAPI (Python 3.9+)
- **前端**: Vue 3 + TypeScript + Vite
- **AI**: MiniMax Max (M3/M2.7)
- **数据库**: PostgreSQL
- **存储**: MinIO (S3兼容)
- **调度**: Celery + Redis

## 核心功能

1. **内容中台**: 选题管理 / 素材库 / 内容队列 / 审核流
2. **AI生成**: 摘要 / 播客脚本 / 文案 / 图片 / 视频
3. **多平台分发**: 抖音 / B站 / YouTube / 小红书 / 头条 / 公众号
4. **CMS后台**: 完整的创作者管理界面