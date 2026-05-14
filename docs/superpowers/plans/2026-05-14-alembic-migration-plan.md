# Alembic 数据库迁移集成 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 IntraAI 后端引入 Alembic 数据库迁移工具，替换现有的 `create_all()` 方式，支持表结构的版本化管理和增量变更。

**Architecture:** 在 `backend/` 目录下初始化 Alembic，配置 `env.py` 读取现有 `app.core.config.settings.DATABASE_URL` 作为连接串，并通过 `target_metadata = Base.metadata` 自动发现 ORM 模型。首次迁移通过 `alembic revision --autogenerate` 生成包含现有 6 张表的基线迁移脚本。`main.py` 中的 `create_all()` 替换为 `alembic upgrade head`。

**Tech Stack:** Alembic, SQLAlchemy, FastAPI, MySQL

---

## 文件结构

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/requirements.txt` | 修改 | 添加 `alembic` 依赖 |
| `backend/alembic.ini` | 新建 | Alembic 配置入口文件 |
| `backend/alembic/env.py` | 新建 | 迁移环境脚本，连接项目配置和模型 |
| `backend/alembic/script.py.mako` | 新建 | 迁移脚本模板（`alembic init` 自动生成） |
| `backend/alembic/versions/` | 新建 | 迁移脚本存放目录 |
| `backend/alembic/versions/xxxx_baseline.py` | 新建 | 首次基线迁移脚本（autogenerate 生成） |
| `backend/app/main.py` | 修改 | 替换 `create_all()` 为 Alembic 调用 |

---

### Task 1: 安装 Alembic 并初始化目录结构

- [ ] **Step 1: 添加 alembic 到 requirements.txt**

在 `backend/requirements.txt` 末尾添加一行：

```
alembic>=1.14.0
```

- [ ] **Step 2: 安装依赖**

```bash
cd F:/IntraAI/backend && pip install alembic
```

- [ ] **Step 3: 初始化 Alembic**

在 `backend/` 目录下运行：

```bash
cd F:/IntraAI/backend && alembic init alembic
```

这会生成 `alembic.ini` 和 `alembic/` 目录（包含 `env.py`、`script.py.mako`、`versions/`）。

- [ ] **Step 4: 验证目录结构**

```bash
ls F:/IntraAI/backend/alembic/
```

预期输出包含：`env.py`、`script.py.mako`、`versions/`、`README`

---

### Task 2: 配置 alembic.ini 连接串

- [ ] **Step 1: 修改 alembic.ini 的 sqlalchemy.url**

打开 `backend/alembic.ini`，找到 `[alembic]` 段下的 `sqlalchemy.url`，将其注释掉（因为我们将通过 `env.py` 动态设置）：

```ini
# sqlalchemy.url = driver://user:pass@localhost/dbname
```

- [ ] **Step 2: 修改 script_location**

确认 `backend/alembic.ini` 中的 `script_location` 指向正确路径：

```ini
script_location = alembic
```

（`alembic init` 默认生成的就是这个值，通常不需要改）

---

### Task 3: 配置 env.py 连接项目模型

- [ ] **Step 1: 重写 backend/alembic/env.py**

将 `env.py` 替换为以下内容，使其：
- 导入项目的 `settings.DATABASE_URL` 作为连接串
- 导入 `Base` 并导入所有模型，使 `Base.metadata` 包含所有 6 张表
- 配置 `target_metadata` 供 autogenerate 使用

```python
"""
Alembic 迁移环境配置

本文件由 alembic init 自动生成，已修改为使用 IntraAI 项目的：
  - 数据库连接串（来自 app.core.config.settings）
  - ORM 模型元数据（来自 app.core.database.Base）
"""
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# 将 backend/ 目录加入 Python 路径，使 `from app.core...` 导入可以正常工作
# alembic 命令在 backend/ 目录下运行，但 env.py 在 alembic/ 子目录中，
# 不加这行会导致 import app.core.config 报 ModuleNotFoundError
sys.path.insert(0, ".")

# 导入项目的数据库配置和 ORM 基类
from app.core.config import settings
from app.core.database import Base

# 导入所有模型，确保 Base.metadata 收集到所有表定义
# 不导入的话，autogenerate 会认为数据库中没有表
import app.models

# Alembic 的 Config 对象，从中读取 alembic.ini 的配置
config = context.config

# 使用项目的数据库连接串覆盖 alembic.ini 中的 sqlalchemy.url
# 这样只需在项目的 .env 文件中维护一份数据库配置
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# 配置 Python 日志（如果 alembic.ini 中有 loggers 段）
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# target_metadata 告诉 autogenerate "期望的表结构"是什么
# autogenerate 会对比 target_metadata 和数据库实际结构，生成差异迁移脚本
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式迁移 — 不需要连接数据库，仅生成 SQL 脚本"""
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
    """在线模式迁移 — 直接连接数据库执行迁移"""
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
```

- [ ] **Step 2: 验证 env.py 可以导入项目模块**

```bash
cd F:/IntraAI/backend && python -c "import sys; sys.path.insert(0,'.'); from app.core.config import settings; print(settings.DATABASE_URL)"
```

预期输出：数据库连接字符串（如 `mysql+pymysql://root:***@localhost:3306/intraai`）

---

### Task 4: 生成基线迁移脚本

- [ ] **Step 1: 确保 MySQL 中已有 IntraAI 的 6 张表**

Alembic autogenerate 会对比"模型定义"和"数据库实际结构"来生成迁移。由于数据库中已有表，需要先生成一个"基线"迁移。

运行以下命令生成初始迁移：

```bash
cd F:/IntraAI/backend && alembic revision --autogenerate -m "baseline existing tables"
```

预期输出：`Generating /path/to/alembic/versions/xxxx_baseline_existing_tables.py`

- [ ] **Step 2: 检查生成的迁移脚本**

打开生成的 `alembic/versions/xxxx_baseline_existing_tables.py`，确认：
- `upgrade()` 中应**为空**（因为数据库中已有这些表，autogenerate 发现模型和数据库一致）
- 如果 `upgrade()` 中有内容，说明数据库表和模型不一致，需要排查

> **重要：** 如果数据库中的表和模型完全一致，autogenerate 会生成一个空的迁移脚本（upgrade 和 downgrade 都是 `pass`）。这是正常行为，表示当前状态已同步。后续模型变更时，autogenerate 才会生成实际的 DDL 语句。

- [ ] **Step 3: 如果 migration 为空（表已存在），手动 stamp 为当前版本**

由于数据库中已有表，而 autogenerate 可能生成空迁移，更干净的做法是直接标记当前数据库状态为最新：

```bash
cd F:/IntraAI/backend && alembic stamp head
```

这会在数据库中创建 `alembic_version` 表并记录当前迁移版本号，告诉 Alembic "数据库已是最新状态"。

然后**删除**空的迁移脚本文件。

> **备选方案：** 如果希望保留迁移脚本作为记录，可以在迁移脚本中手动添加 `CREATE TABLE` 语句（从 autogenerate 输出中复制），然后运行 `alembic upgrade head`。但 stamp 方式更简洁。

- [ ] **Step 4: 验证 Alembic 状态**

```bash
cd F:/IntraAI/backend && alembic current
```

预期输出：显示当前版本号（如果有迁移脚本）或无输出（如果使用 stamp 且删除了空脚本）。

---

### Task 5: 修改 main.py 使用 Alembic

- [ ] **Step 1: 替换 main.py 中的 create_all()**

将 `backend/app/main.py` 中的 startup 事件从 `create_all()` 改为调用 Alembic 命令行迁移：

```python
from alembic.config import Config
from alembic import command
import os

@app.on_event("startup")
def startup():
    """应用启动时自动执行数据库迁移"""
    # 获取 backend/ 目录的绝对路径（main.py 在 backend/app/ 下）
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    alembic_cfg = Config(os.path.join(backend_dir, "alembic.ini"))
    command.upgrade(alembic_cfg, "head")
```

同时删除不再需要的 `from app.core.database import Base, engine` 导入（改为仅导入需要的部分），并移除 `import app.models`（如果 Alembic 的 env.py 已经负责导入模型）。

完整修改后的文件头部应为：

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from alembic.config import Config
from alembic import command
import os

from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.knowledge_bases import router as kb_router
from app.api.documents import router as docs_router
from app.api.chat import router as chat_router
from app.api.admin import router as admin_router
from app.api.sessions import router as sessions_router
```

startup 函数：

```python
@app.on_event("startup")
def startup():
    """应用启动时自动执行数据库迁移"""
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    alembic_cfg = Config(os.path.join(backend_dir, "alembic.ini"))
    command.upgrade(alembic_cfg, "head")
```

- [ ] **Step 2: 验证应用可以正常启动**

```bash
cd F:/IntraAI/backend && python -m uvicorn app.main:app --reload
```

预期：应用正常启动，无报错。控制台中可以看到 Alembic 的迁移日志。

- [ ] **Step 3: 提交代码**

```bash
git add backend/requirements.txt backend/alembic.ini backend/alembic/ backend/app/main.py
git commit -m "feat: add Alembic database migration support

Replace create_all() with Alembic migrations for versioned schema management.
- Add alembic dependency and config
- Configure env.py to use project settings and models
- Use alembic upgrade head on startup instead of create_all"
```

---

### Task 6: 验证迁移流程可用

- [ ] **Step 1: 测试模型变更检测**

在 `backend/app/models/user.py` 的 User 模型中添加一个测试字段（稍后删除）：

```python
test_field = Column(String(50), nullable=True)
```

- [ ] **Step 2: 生成变更迁移**

```bash
cd F:/IntraAI/backend && alembic revision --autogenerate -m "add test_field to users"
```

检查生成的迁移脚本，`upgrade()` 中应包含 `op.add_column('users', sa.Column('test_field', ...))`。

- [ ] **Step 3: 执行迁移**

```bash
cd F:/IntraAI/backend && alembic upgrade head
```

验证 MySQL 中 users 表已添加 `test_field` 列。

- [ ] **Step 4: 回滚迁移**

```bash
cd F:/IntraAI/backend && alembic downgrade -1
```

验证 users 表中 `test_field` 列已被删除。

- [ ] **Step 5: 清理测试**

删除测试迁移脚本文件，从 `user.py` 中删除 `test_field` 字段，重新生成迁移：

```bash
cd F:/IntraAI/backend && alembic revision --autogenerate -m "remove test_field from users"
cd F:/IntraAI/backend && alembic upgrade head
```

或者直接 stamp 到干净状态：

```bash
cd F:/IntraAI/backend && alembic stamp head
```

- [ ] **Step 6: 提交清理后的代码**

```bash
git add backend/
git commit -m "chore: clean up test migration artifacts"
```
