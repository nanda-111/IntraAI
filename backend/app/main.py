import logging
import os

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.admin_platform import router as admin_platform_router
from app.api.assistant import router as assistant_router
from app.api.auth import router as auth_router
from app.api.cases import router as cases_router
from app.api.chat import router as chat_router
from app.api.diagnosis import router as diagnosis_router
from app.api.documents import router as docs_router
from app.api.evaluation import router as evaluation_router
from app.api.knowledge import router as knowledge_router
from app.api.knowledge_admin import router as knowledge_admin_router
from app.api.knowledge_bases import router as kb_router
from app.api.products import admin_router as products_admin_router
from app.api.products import router as products_router
from app.api.sessions import router as sessions_router
from app.api.tickets import admin_router as tickets_admin_router
from app.api.tickets import router as tickets_router
from app.api.users import router as users_router
from app.core.config import settings

logger = logging.getLogger(__name__)

# 创建 FastAPI 应用实例
# title 会显示在 Swagger 文档的标题栏
app = FastAPI(title="打印机售后智能服务平台", version="1.0.0")

# 配置跨域中间件（CORS）
# 前端开发服务器运行在 localhost:5173，需要允许它访问后端 API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 应用启动事件 ====================
@app.on_event("startup")
def startup():
    """启动时执行数据库迁移，并按配置写入首期演示数据。"""
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    from sqlalchemy import inspect

    import app.models  # noqa: F401  确保收集所有模型
    from app.core.database import Base, engine

    if settings.database_url.startswith("sqlite"):
        # 本地 SQLite 演示模式：直接建表（Alembic 迁移面向 MySQL）
        Base.metadata.create_all(engine)
    else:
        alembic_cfg = Config(os.path.join(backend_dir, "alembic.ini"))
        existing_tables = set(inspect(engine).get_table_names())
        if "users" not in existing_tables:
            # 全新数据库：直接按当前 ORM 元数据建表，并把迁移版本标记为最新。
            # 旧版基线迁移只包含增量外键，无法在空库上执行。
            Base.metadata.create_all(engine)
            command.stamp(alembic_cfg, "head")
        else:
            command.upgrade(alembic_cfg, "head")

    if settings.SEED_DEMO_DATA:
        from app.core.database import SessionLocal
        from app.seed import seed_all

        db = SessionLocal()
        try:
            stats = seed_all(db)
            logger.info("演示数据初始化完成: %s", stats)
            if settings.AUTO_INDEX_SEED:
                from app.services import printer_rag_service

                logger.info("重建知识索引: %s", printer_rag_service.reindex_all(db))
        except Exception:
            db.rollback()
            logger.exception("演示数据初始化失败，平台仍可启动")
        finally:
            db.close()


# ==================== 用户端 ====================
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(products_router)
app.include_router(knowledge_router)
app.include_router(assistant_router)
app.include_router(diagnosis_router)
app.include_router(tickets_router)

# ==================== 运营管理端 ====================
app.include_router(admin_router)
app.include_router(admin_platform_router)
app.include_router(products_admin_router)
app.include_router(knowledge_admin_router)
app.include_router(cases_router)
app.include_router(tickets_admin_router)
app.include_router(evaluation_router)

# ==================== 兼容保留的通用知识库能力 ====================
# 旧版知识库/文档/聊天接口保留，供迁移期使用；平台主流程使用新的型号感知接口。
app.include_router(kb_router)
app.include_router(docs_router)
app.include_router(chat_router)
app.include_router(sessions_router)


# 健康检查接口 — 用于确认服务是否正常运行
@app.get("/health")
def health_check():
    return {"status": "ok"}
