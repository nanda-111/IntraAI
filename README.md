# IntraAI

企业内部 AI 知识问答平台 — 上传文档，即刻问答。

IntraAI 是一个基于 RAG（检索增强生成）的企业知识库系统，支持文档上传、智能问答、会话管理和多用户协作。通过混合检索（向量 + BM25）和 CrossEncoder 重排序，实现高精度的文档问答。

## 功能特性

- **智能问答** — 基于上传文档的 RAG 问答，支持流式输出
- **混合检索** — 向量相似度 + BM25 关键词匹配 + CrossEncoder 重排序，三阶段检索保障精度
- **Agent 模式** — LangChain Agent 自动选择工具（知识库检索 / 数据库查询 / 网页搜索）
- **文档管理** — 支持 PDF、DOCX、TXT、PPTX、XLSX 等格式的上传与解析
- **多知识库** — 支持创建多个知识库，按业务场景分类管理文档
- **会话管理** — 多轮对话、历史记录、自动摘要压缩（超过 20 轮自动压缩）
- **用户系统** — 注册 / 登录 / JWT 认证 / 管理员权限控制
- **管理后台** — 用户管理、使用统计、系统概览
- **企业级 UI** — 基于 Ant Design Vue 的响应式界面

## 技术栈

| 层级 | 技术 |
|------|------|
| **前端** | Vue 3 + Vite + Ant Design Vue + Pinia + Vue Router |
| **后端** | FastAPI + SQLAlchemy + Alembic + Pydantic |
| **数据库** | MySQL 8.0（业务数据）+ ChromaDB（向量存储） |
| **AI/ML** | OpenAI 兼容 API（小米 MiMo）+ Sentence-Transformers + LangChain |
| **检索** | 向量检索（ChromaDB）+ BM25（rank-bm25 + jieba）+ CrossEncoder 重排序 |
| **部署** | Docker Compose + Nginx 反向代理 |
| **CI/CD** | GitHub Actions（Lint → Test → Build） |

## 项目结构

```
IntraAI/
├── backend/                    # Python 后端
│   ├── app/
│   │   ├── api/                # FastAPI 路由（auth、chat、documents、admin、sessions、knowledge_bases、users）
│   │   ├── core/               # 基础设施：配置、数据库、安全（JWT + bcrypt）
│   │   ├── models/             # SQLAlchemy ORM 模型
│   │   ├── schemas/            # Pydantic 请求/响应模型
│   │   └── services/           # 业务逻辑
│   │       ├── llm.py                  # OpenAI 兼容 LLM 客户端
│   │       ├── rag.py                  # RAG 编排（检索 → 重排序 → 生成）
│   │       ├── langchain_agent.py      # LangChain Agent
│   │       ├── langchain_tools.py      # Agent 工具集
│   │       ├── embedding.py            # 文本向量化
│   │       ├── vector_store.py         # ChromaDB + BM25 混合检索
│   │       ├── reranker.py             # CrossEncoder 重排序
│   │       └── document_processor.py   # 文档解析与分片
│   ├── tests/                  # 单元测试（pytest，覆盖率 ≥ 95%）
│   ├── eval/                   # RAG 效果评估框架（RAGAS）
│   ├── alembic/                # 数据库迁移
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                   # Vue 3 前端
│   ├── src/
│   │   ├── views/              # 页面组件（Login、Chat、Knowledge、Admin）
│   │   ├── components/         # 通用组件（AppLayout、ChatMessage）
│   │   ├── api/                # Axios HTTP 客户端
│   │   ├── stores/             # Pinia 状态管理
│   │   └── router/             # Vue Router 路由配置
│   ├── nginx.conf              # 生产环境 Nginx 配置
│   └── Dockerfile              # 多阶段构建（Node → Nginx）
├── docker-compose.yml          # 一键编排（MySQL + Backend + Frontend）
├── .github/workflows/ci.yml    # CI 流水线
└── pyproject.toml              # Ruff + Pytest 配置
```

## 快速开始

### 前置条件

- Python 3.11+
- Node.js 20+
- MySQL 8.0（或使用 Docker Compose 自动启动）
- 小米 MiMo API Key（[申请地址](https://token-plan-cn.xiaomimimo.com)）

### 方式一：本地开发

**1. 克隆项目**

```bash
git clone <repo-url> IntraAI
cd IntraAI
```

**2. 配置环境变量**

```bash
cp .env.example .env
# 编辑 .env，填入你的 OPENAI_API_KEY
```

**3. 启动后端**

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**4. 启动前端**

```bash
cd frontend
npm install
npm run dev
```

**5. 访问应用**

| 服务 | 地址 |
|------|------|
| 前端页面 | http://localhost:5173 |
| 后端 API | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |

> Windows 用户可直接运行 `start-dev.bat` 一键启动前后端。

### 方式二：Docker Compose

```bash
# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY

# 一键启动
docker compose up -d

# 查看日志
docker compose logs -f

# 停止服务
docker compose down
```

启动后访问 http://localhost 即可（前端 80 端口，Nginx 反向代理到后端）。

## 环境变量

在项目根目录创建 `.env` 文件：

```bash
# MiMo API 配置（必填）
OPENAI_API_KEY=sk-your-key-here
OPENAI_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
OPENAI_MODEL=mimo-v2.5-pro

# 以下为可选配置（已有默认值）
# MYSQL_HOST=localhost
# MYSQL_PORT=3306
# MYSQL_USER=root
# MYSQL_PASSWORD=
# MYSQL_DB=intraai
# SECRET_KEY=your-random-secret-key
# UPLOAD_DIR=./uploads
# CHROMA_DIR=./chroma_data
```

> **安全提示**：生产环境务必修改 `SECRET_KEY` 为随机长字符串，不要使用默认值。

## 核心数据流

### RAG 问答模式

```
用户提问 → 文本向量化 → 混合检索（向量 + BM25，50 候选）
         → CrossEncoder 重排序（Top 5）→ 上下文拼接 → LLM 生成回答
```

### Agent 模式

```
用户提问 → LangChain Agent → 自动选择工具
         ├─ 知识库检索（RAG）
         ├─ 数据库查询（SQL）
         └─ 网页搜索（DuckDuckGo）
         → LLM 综合回答
```

### 文档处理流程

```
文件上传 → 文本提取（PyMuPDF / python-docx）→ 智能分片
        → 文本向量化 → 存入 ChromaDB
```

## 开发命令

### 后端

```bash
# 安装依赖
cd backend && pip install -r requirements.txt

# 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 运行测试
python -m pytest backend/tests/ -v --tb=short

# 运行测试 + 覆盖率报告
python -m pytest backend/tests/ --cov=backend/app --cov-report=term-missing

# 代码检查与格式化
ruff check app/
ruff format app/

# 数据库迁移
alembic upgrade head
alembic revision --autogenerate -m "描述"
```

### 前端

```bash
cd frontend

# 安装依赖
npm install

# 开发服务器
npm run dev

# 生产构建
npm run build

# 代码检查
npm run lint

# 运行测试
npm test
```

## 测试

- **后端**：pytest + SQLite 内存数据库，外部依赖全部 mock（LLM API、ChromaDB、sentence-transformers）
- **前端**：Vitest + Vue Test Utils
- **覆盖率阈值**：95%（`pyproject.toml` 中配置）
- **CI**：GitHub Actions 自动执行 Lint → Test → Build

## 部署

### Docker Compose（推荐）

```bash
docker compose up -d
```

包含三个服务：MySQL（数据持久化） + Backend（FastAPI） + Frontend（Nginx），数据卷自动管理。

### 手动部署

1. 配置 MySQL 数据库，创建 `intraai` 数据库
2. 配置 `.env` 文件
3. 启动后端：`uvicorn app.main:app --host 0.0.0.0 --port 8000`
4. 构建前端：`npm run build`，将 `dist/` 部署到 Nginx

> 部署后务必测试完整流程：注册 → 登录 → 上传文档 → 提问。

## 许可证

本项目为内部使用项目，暂未设定开源许可证。
