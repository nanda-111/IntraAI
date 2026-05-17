"""
pytest 全局 fixtures

为集成测试提供：
  - SQLite 内存数据库（CI 中无需 MySQL）
  - FastAPI TestClient（自动注入测试数据库）
  - 预置测试用户和管理员账号
  - 认证 token 生成
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.models.user import User

# ---- 测试数据库 ----
# SQLite 内存数据库：轻量、无需外部服务，适合 CI 流水线
# StaticPool 保证整个测试期间复用同一个连接（内存数据库不能有多个连接）
TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(bind=TEST_ENGINE)


@pytest.fixture(autouse=True)
def setup_db():
    """每个测试前创建表，测试后销毁表，保证测试隔离"""
    Base.metadata.create_all(TEST_ENGINE)
    yield
    Base.metadata.drop_all(TEST_ENGINE)


@pytest.fixture
def db_session():
    """提供一个独立的数据库会话"""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    """带测试数据库的 FastAPI TestClient"""
    import sys
    from unittest.mock import MagicMock

    # mock sentence_transformers（CI 环境中可能未安装）
    if "sentence_transformers" not in sys.modules:
        sys.modules["sentence_transformers"] = MagicMock()

    from app.main import app

    # 清除 startup 事件（避免在 CI 中执行 alembic 迁移）
    app.router.on_startup.clear()

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """创建并返回一个普通测试用户"""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hash_password("testpass123"),
        is_admin=False,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_admin(db_session):
    """创建并返回一个管理员测试用户"""
    admin = User(
        username="admin",
        email="admin@example.com",
        hashed_password=hash_password("adminpass123"),
        is_admin=True,
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture
def user_token(test_user):
    """普通用户的 JWT token"""
    return create_access_token({"sub": test_user.username})


@pytest.fixture
def admin_token(test_admin):
    """管理员的 JWT token"""
    return create_access_token({"sub": test_admin.username})


@pytest.fixture
def user_headers(user_token):
    """带普通用户认证的请求头"""
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def admin_headers(admin_token):
    """带管理员认证的请求头"""
    return {"Authorization": f"Bearer {admin_token}"}
