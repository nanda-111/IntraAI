# PrintCare · 多品牌打印机售后智能服务平台

面向家用喷墨打印机的售后服务平台：先确认品牌与具体型号，再提供型号感知的知识检索、智能客服、有状态分步诊断、售后工单、知识运营与质量评测。

基于原 IntraAI 的 Vue 3 + FastAPI + MySQL + ChromaDB + LangChain 技术底座重建，保留通用知识库/聊天接口作为迁移期兼容能力，主流程改为打印机售后业务。

## 首期范围

| 品牌 | 代表型号系列 | 代码体系 |
|------|--------------|----------|
| HP | DeskJet 2700 系列 | HP 错误代码/指示灯 |
| Canon | PIXMA TS5300 系列 | Canon Support Code |
| Epson | EcoTank L3250 系列 | Epson 指示灯组合/消息 |
| Brother | DCP-T420W 系列 | Brother LED/消息 |

首期覆盖六类故障：进纸与卡纸、墨盒与供墨、打印质量、连接与网络、电源与开机、扫描与复印。

平台不连接打印机硬件、不读取传感器、不提供拆机/电源/电路板自助维修步骤。涉及 L3 高风险操作时停止自动指导并建议转人工。

## 核心能力

- **品牌型号注册中心** — 品牌、系列、具体型号、别名、地区版本、能力映射与支持状态（planned/building/pilot/active/suspended）。
- **型号感知 RAG** — 审核状态/品牌/型号/地区硬过滤 → Chroma 向量召回 + BM25 → RRF 融合 → CrossEncoder 重排 → Evidence Gate → 带来源回答。
- **智能客服** — 会话承载型号上下文，自动识别型号、错误码与故障类别；SSE 流式回答，展示引用与安全提示。
- **故障诊断状态机** — `MODEL_PENDING → COLLECTING → RETRIEVING → STEP_READY → WAIT_USER_ACTION → RESOLVED/ESCALATED`，一次只推送一条步骤。
- **售后工单** — 用户确认后建单，携带型号、现象、已执行步骤和证据；客服分配、处理、备注与关闭。
- **知识运营** — 来源登记、PDF/DOCX/TXT/MD/HTML/JSON 导入、审核、发布、索引同步、版本回滚。
- **维修案例** — 社区/人工案例独立管理，明确标注“不是官方维修步骤”。
- **评测中心** — 按品牌/型号维护测试集，真实计算 Recall@5、MRR@5、故障分类准确率、转人工召回率与耗时。
- **RBAC** — 普通用户 / 客服人员 / 知识库管理员 / 系统管理员；关键操作写审计日志。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + Ant Design Vue + Pinia + Vue Router |
| 后端 | FastAPI + SQLAlchemy + Alembic + Pydantic |
| 数据 | MySQL 8.0（业务数据）+ ChromaDB（向量）+ 本地文件（原始资料）|
| AI | OpenAI 兼容接口（阿里云百炼 DeepSeek）+ sentence-transformers + bge-reranker |
| 检索 | Chroma 向量 + BM25（jieba / rank-bm25）+ RRF + CrossEncoder |
| 部署 | Docker Compose + Nginx |

## 项目结构

```
backend/app/
├── api/                  # auth/users/products/knowledge/assistant/diagnosis/tickets/
│                         # knowledge_admin/cases/evaluation/admin_platform/admin
├── domains/printer/      # registry、capabilities、fault_taxonomy、safety_policy
├── models/               # 品牌型号、知识、诊断、工单、会话、评测、审计
├── schemas/              # 请求/响应模型
├── services/
│   ├── printer_rag_service.py    # 型号感知检索、证据校验、受控回答
│   ├── diagnosis_service.py      # 诊断状态机
│   ├── knowledge_ingestion.py    # 导入解析与知识草稿
│   ├── knowledge_review.py       # 审核发布与索引
│   ├── ticket_service.py         # 工单状态流转
│   ├── evaluation_service.py     # 评测指标
│   └── audit_service.py          # 审计日志
└── seed.py               # 首期演示数据（4 品牌 / 9 型号 / 24 条知识）

frontend/src/
├── components/           # PlatformLayout、PageHeader、ModelSelect、StatusTag、SourceList
├── views/user/           # 首页、品牌型号、知识中心、智能客服、诊断、工单、维护、历史、个人中心
└── views/admin/          # 运营概览、型号、知识来源/导入/审核、案例、工单、评测、用户、设置
```

## 快速开始

### 方式一：本地 SQLite 演示（最快）

在项目根目录 `.env` 中加入：

```bash
DATABASE_URL=sqlite:///./intraai.db
SEED_DEMO_DATA=true
```

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

另开终端：

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173 。首次注册的账号自动成为系统管理员。启动时会自动建表并写入演示品牌、型号、知识、案例和评测集。

> 向量索引默认不自动构建；检索会自动回退到数据库关键词召回。登录后在「系统配置 → 重建知识索引」可构建 Chroma 索引。

### 方式二：MySQL + Docker Compose

```bash
cp .env.example .env
# 填入 OPENAI_API_KEY
docker compose up -d
```

访问 http://localhost 。后端启动时执行 Alembic 迁移并写入演示数据。

## 环境变量

```bash
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=deepseek-v4.1-flash-1017

# MySQL（Docker 部署必填）
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your-password
MYSQL_DB=intraai

# 可选：直接指定连接串（SQLite 演示）
# DATABASE_URL=sqlite:///./intraai.db

SECRET_KEY=change-me
UPLOAD_DIR=./uploads
CHROMA_DIR=./chroma_data
SEED_DEMO_DATA=true
AUTO_INDEX_SEED=false

# 旧版 LangChain Agent（含通用 SQL 查询工具）默认停用
ENABLE_LEGACY_AGENT=false
```

> `SECRET_KEY` 生产环境必须替换为随机长字符串。API Key 仅从环境变量读取，不会返回前端。

## 主要 API

所有业务接口使用 `/api` 前缀；`/api/admin/*` 按角色鉴权。

| 模块 | 代表接口 |
|------|----------|
| 品牌型号 | `GET /api/products/brands`、`GET /api/products/models`、`GET /api/products/models/{id}`、`GET/POST /api/products/devices` |
| 知识中心 | `GET /api/knowledge`、`GET /api/knowledge/{doc_id}` |
| 智能客服 | `POST /api/assistant/sessions`、`POST /api/assistant/sessions/{id}/messages`、`.../messages/stream` |
| 故障诊断 | `POST /api/diagnosis/sessions`、`POST .../messages`、`POST .../steps/{step_id}/result` |
| 工单 | `POST/GET /api/tickets`、`GET /api/admin/tickets`、`PUT /api/admin/tickets/{id}` |
| 知识运营 | `POST /api/admin/knowledge/import`、`POST /api/admin/knowledge/{doc_id}/review` |
| 评测 | `GET/POST /api/admin/evaluation/datasets`、`POST .../datasets/{id}/run` |
| 运营 | `GET /api/admin/dashboard`、`GET /api/admin/settings`、`GET /api/admin/audit-logs` |

完整接口见 http://localhost:8000/docs 。

## 测试与质量

```bash
# 后端（SQLite 内存库，外部依赖 mock）
python -m pytest backend/tests/ -v --tb=short

# 前端
cd frontend && npm test && npm run lint && npm run build

# 代码检查
ruff check backend/app
ruff format backend/app
```

- 启动脚本：`start-dev.bat`
- 数据库迁移：`cd backend && alembic upgrade head`
- 新迁移：`cd backend && alembic revision --autogenerate -m "描述"`

## 安全边界

- LLM 不执行任意 SQL、Shell、Python 或远程设备控制。
- 维修步骤必须来自已审核知识；Evidence Gate 校验型号范围、来源等级、步骤完整性、有效期和安全标记。
- 社区案例与官方知识分离，不进入正式维修步骤检索。
- 用户诊断、会话、工单按 `user_id` 隔离；客服查看联系方式默认脱敏。
- 日志记录型号过滤条件、召回证据 ID、工具调用与状态，不记录不必要的敏感全文。