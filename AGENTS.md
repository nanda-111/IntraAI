# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## 项目简介

IntraAI — 企业内部 AI 知识问答平台。FastAPI 后端 + Vue 3 前端 + MySQL + ChromaDB。通过 OpenAI 兼容接口调用小米 MiMo 大模型。

## 环境说明

- **开发环境**: Windows 本地开发，CentOS 7 部署服务器
- **网络**: 国内访问 GitHub / Docker Hub 经常不通，需要用镜像或 SCP 传输
- 修改代码前先确认当前环境（本地 Windows 还是远程 CentOS）
- 文件路径含中文时，使用短 8.3 路径或正斜杠

## 常用命令

### 后端 (Python / FastAPI)

```bash
# 安装依赖（项目根目录执行）
cd backend && pip install -r requirements.txt

# 启动开发服务器（项目根目录执行）
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 运行全部测试（项目根目录执行）
python -m pytest backend/tests/ -v --tb=short

# 运行单个测试文件
python -m pytest backend/tests/api/test_chat.py -v --tb=short

# 运行单个测试类或方法
python -m pytest backend/tests/api/test_chat.py::TestChatEndpoint::test_chat_basic -v

# 运行测试并生成覆盖率报告
python -m pytest backend/tests/ --cov=backend/app --cov-report=term-missing

# 覆盖率阈值: 95%（pyproject.toml 中配置）

# 代码检查
cd backend && ruff check app/
cd backend && ruff format app/

# 数据库迁移（Alembic）
cd backend && alembic upgrade head
cd backend && alembic revision --autogenerate -m "描述"
```

### 前端 (Vue 3 / Vite)

```bash
cd frontend

# 安装依赖
npm install

# 开发服务器（端口 5173，代理到 localhost:8000 后端）
npm run dev

# 生产构建
npm run build

# 代码检查
npm run lint

# 运行测试（Vitest）
npm test
```

### 快速启动（前后端同时）

```bash
# Windows 批处理脚本
start-dev.bat
# 后端: http://localhost:8000 | 前端: http://localhost:5173 | API 文档: http://localhost:8000/docs
```

### Docker Compose

```bash
docker compose up -d              # 启动全部服务（MySQL + 后端 + 前端）
docker compose down               # 停止并删除容器
docker compose logs -f            # 查看日志
docker compose build --no-cache   # 依赖变更后强制重建镜像
```

## 架构概览

### 后端结构 (`backend/app/`)

```
app/
├── api/          # FastAPI 路由层（auth、chat、documents、admin、sessions、knowledge_bases、users）
├── core/         # 公共基础设施：配置（pydantic-settings）、数据库（SQLAlchemy）、安全（bcrypt + JWT）
├── models/       # SQLAlchemy ORM 模型（User、Document、KnowledgeBase、Session、Conversation、UsageLog）
├── schemas/      # Pydantic 请求/响应模型
└── services/     # 业务逻辑层
    ├── llm.py                  # OpenAI 兼容 LLM 客户端（chat_completion、chat_completion_stream）
    ├── rag.py                  # RAG 编排（向量检索 → 上下文拼接 → LLM 生成）
    ├── langchain_agent.py      # LangChain Agent（工具：rag_search、db_query、web_search）
    ├── langchain_llm.py        # ChatMiMo 自定义封装，支持 reasoning_content
    ├── langchain_tools.py      # Agent 工具：知识库检索、SQL 查询、DuckDuckGo 网页搜索
    ├── embedding.py            # Sentence-transformers 文本向量化
    ├── vector_store.py         # ChromaDB 向量存储操作
    └── document_processor.py   # PDF/DOCX/TXT 文本提取与分片
```

### 核心数据流

1. **对话（RAG 模式）**: 用户提问 → 向量化 → ChromaDB 检索 → 上下文 + 问题 → LLM → 回答
2. **对话（Agent 模式）**: 用户提问 → LangChain Agent → 自动选择工具（知识库/数据库/网页） → LLM → 回答
3. **文档上传**: 文件 → 提取文本 → 分片 → 向量化 → 存入 ChromaDB
4. **会话管理**: 对话记录存 MySQL；超过 20 轮自动摘要压缩（保留最近 5 轮，删除前 15 轮）

### 前端结构 (`frontend/src/`)

- **页面**: LoginView（登录）、ChatView（主对话）、KnowledgeView（文档管理）、AdminView（用户/统计）
- **API 层**: Axios 实例，自动注入 token，401 时跳转登录页（`src/api/index.js`）
- **状态管理**: Pinia 存储登录态（`src/stores/auth.js`）
- **路由**: Vue Router + 路由守卫；`/admin` 需要管理员权限

### 配置管理

- **后端配置**: `app/core/config.py` — pydantic-settings 自动从 `.env` 和环境变量读取
- **关键环境变量**: `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`、`MYSQL_*`、`SECRET_KEY`、`UPLOAD_DIR`、`CHROMA_DIR`
- **前端配置**: 开发模式 Vite 代理；Docker 生产环境 Nginx 反向代理

## 开发规范

- 每次只改一个文件，验证通过后再改下一个
- 改完后验证完整流程：注册 → 登录 → 使用核心功能，每步检查日志
- 安装包时带全依赖（不要用 `--no-deps`），安装后验证 import 是否正常

## 部署注意事项

- 远程服务器可能没有 `.env` 文件，部署前先检查
- Docker 镜像看起来没更新时，用 `--no-cache` 重建
- 部署后必须测试完整用户流程再宣告成功

## 测试约定

- 测试使用 SQLite 内存数据库（CI 无需 MySQL）
- 外部依赖全部 mock：LLM API（`app.services.llm.client`）、ChromaDB、sentence-transformers
- conftest.py 提供 fixtures：`client`（TestClient）、`test_user`/`test_admin`、`user_headers`/`admin_headers`、`mock_llm`、`mock_embeddings`、`mock_vector_store`
- pytest 配置：`asyncio_mode = "auto"`、`pythonpath = ["backend"]`、`testpaths = ["backend/tests"]`

## 代码质量

- Python: ruff 做 lint 和格式化（目标 py311，行宽 100）
- JavaScript/Vue: ESLint + vue 插件
- Pydantic schemas 使用 `orm_mode = True` 做 SQLAlchemy 模型序列化（class-based config 已弃用，可迁移至 `ConfigDict`）
