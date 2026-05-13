from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.knowledge_bases import router as kb_router
from app.api.documents import router as docs_router
from app.api.chat import router as chat_router
from app.api.admin import router as admin_router
from app.api.sessions import router as sessions_router
import app.models  # 导入所有模型，让 SQLAlchemy 的 Base.metadata 收集到所有表定义

# 创建 FastAPI 应用实例
# title 会显示在 Swagger 文档的标题栏
app = FastAPI(title="IntraAI", version="0.1.0")

# 配置跨域中间件（CORS）
# 前端开发服务器运行在 localhost:5173，需要允许它访问后端 API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # 允许的前端地址
    allow_credentials=True,                    # 允许携带 Cookie
    allow_methods=["*"],                       # 允许所有 HTTP 方法
    allow_headers=["*"],                       # 允许所有请求头
)


# ==================== 应用启动事件 ====================
# @app.on_event("startup") 是 FastAPI 的生命周期事件装饰器。
# 被装饰的函数会在应用启动时（接收第一个请求之前）自动执行一次。
# 这里用来自动创建数据库表。
#
# Base.metadata.create_all() 的工作机制：
#   1. Base.metadata 中存储了所有继承了 Base 的模型类的表结构信息。
#      这些信息是通过 import app.models 加载进来的（见文件顶部的导入语句）。
#   2. create_all(bind=engine) 会检查目标数据库中是否已存在对应的表。
#   3. 如果表不存在，则执行 CREATE TABLE 语句创建表。
#   4. 如果表已存在，则跳过（不会删除或修改已有表的结构和数据）。
#   5. 因此这个操作是安全的，可以反复执行而不会丢失数据。
#
# 注意事项：
#   - create_all 只能创建新表，不能修改已有表的结构（如添加列、修改列类型）。
#     如果需要修改表结构，应使用 Alembic 等数据库迁移工具。
#   - MySQL 未运行时，create_all 会抛出连接异常，但不会影响应用启动（异常会被捕获）。
#     实际开发中应确保数据库服务已启动。
@app.on_event("startup")
def startup():
    """应用启动时自动创建所有数据库表（如果表已存在则跳过）"""
    Base.metadata.create_all(bind=engine)


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
