# Pytest 配置和 fixtures
import pytest
import sys
from pathlib import Path

# 将 backend 目录加入 sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture
def client():
    """FastAPI 测试客户端"""
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
    # 重新初始化默认模板
    from app.api.templates import init_default_templates
    init_default_templates()
    return store
