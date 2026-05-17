import os

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.documents import router as docs_router
from app.api.knowledge_bases import router as kb_router
from app.api.sessions import router as sessions_router
from app.api.users import router as users_router

# 创建 FastAPI 应用实例
# title 会显示在 Swagger 文档的标题栏
app = FastAPI(title="IntraAI", version="0.1.0")

# 配置跨域中间件（CORS）
# 前端开发服务器运行在 localhost:5173，需要允许它访问后端 API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # 允许的前端地址
    allow_credentials=True,  # 允许携带 Cookie
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有请求头
)


# ==================== 应用启动事件 ====================
# 应用启动时自动执行数据库迁移，将数据库 schema 升级到最新版本。
# 使用 Alembic 替代了原来的 create_all()，支持表结构的版本化管理和增量变更。
@app.on_event("startup")
def startup():
    """应用启动时自动执行数据库迁移（alembic upgrade head）"""
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    alembic_cfg = Config(os.path.join(backend_dir, "alembic.ini"))
    command.upgrade(alembic_cfg, "head")


# 注册认证路由（/api/auth/register、/api/auth/login）
app.include_router(auth_router)

# 注册用户管理路由（/api/users/me）
app.include_router(users_router)

# 注册知识库 CRUD 路由（/api/knowledge-bases/）
app.include_router(kb_router)

# 注册文档管理路由（/api/documents/）
app.include_router(docs_router)

# 注册对话路由（/api/chat/）
app.include_router(chat_router)

# 注册管理后台路由（/api/admin/）— 所有接口都需要管理员权限
app.include_router(admin_router)

# 注册会话管理路由（/api/sessions/）
app.include_router(sessions_router)


# 健康检查接口 — 用于确认服务是否正常运行
# Docker 部署时也可以用来做容器健康检查
@app.get("/health")
def health_check():
    return {"status": "ok"}
