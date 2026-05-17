"""
Alembic 迁移环境配置

本文件由 alembic init 自动生成，已修改为使用 IntraAI 项目的：
  - 数据库连接串（来自 app.core.config.settings）
  - ORM 模型元数据（来自 app.core.database.Base）
"""

import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# 将 backend/ 目录加入 Python 路径，使 `from app.core...` 导入可以正常工作
# alembic 命令在 backend/ 目录下运行，但 env.py 在 alembic/ 子目录中，
# 不加这行会导致 import app.core.config 报 ModuleNotFoundError
sys.path.insert(0, ".")

# 导入项目的数据库配置和 ORM 基类
# 导入所有模型，确保 Base.metadata 收集到所有表定义
# 不导入的话，autogenerate 会认为数据库中没有表
from app.core.config import settings
from app.core.database import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# 使用项目的数据库连接串覆盖 alembic.ini 中的 sqlalchemy.url
# 这样只需在项目的 .env 文件中维护一份数据库配置
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# target_metadata 告诉 autogenerate "期望的表结构"是什么
# autogenerate 会对比 target_metadata 和数据库实际结构，生成差异迁移脚本
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
