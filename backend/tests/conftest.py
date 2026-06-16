# Pytest 配置和 fixtures
import pytest
import sys
from pathlib import Path

# 将 backend 目录加入 sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture
def client(fresh_store):
    """FastAPI 测试客户端(每个测试自动重置 store,避免跨测试污染)"""
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


@pytest.fixture
def fresh_store():
    """干净的内存存储（每个测试前重置）"""
    from app.store import store
    # 清空所有集合
    store.users.clear()
    store.contents.clear()
    store.topics.clear()
    store.materials.clear()
    store.review_tasks.clear()
    store.platform_accounts.clear()
    store.publish_records.clear()
    store.scheduled_tasks.clear()
    store.templates.clear()
    store.images.clear()
    store.videos.clear()  # Phase 2
    store.ai_creations.clear()  # Phase B.4
    store.sources.clear()  # Phase 3 — 来源
    store.source_chapters.clear()
    store.hot_topics.clear()  # P0-2: 选题雷达
    store.user_style_profiles.clear()  # P1-1: 文风画像
    store.publish_metrics.clear()  # P1-2: 数据回流
    # 重新初始化默认模板
    from app.api.templates import init_default_templates
    init_default_templates()
    return store
