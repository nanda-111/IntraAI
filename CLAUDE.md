# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目简介

PrintCare — 多品牌多型号打印机售后智能服务平台（基于原 IntraAI 重建）。FastAPI 后端 + Vue 3 前端 + MySQL/SQLite + ChromaDB，通过 OpenAI 兼容接口调用阿里云百炼大模型。

首期覆盖 HP DeskJet 2700、Canon PIXMA TS5300、Epson EcoTank L3250、Brother DCP-T420W 四个系列，六类故障：进纸、供墨、打印质量、连接、电源、扫描。

## 环境说明

- **开发环境**: Windows 本地开发，CentOS 7 部署服务器
- **网络**: 国内访问 GitHub / Docker Hub 经常不通，需要用镜像或 SCP 传输
- **本地演示**：`.env` 设置 `DATABASE_URL=sqlite:///./intraai.db` 可绕过 MySQL；启动时自动建表并写入种子数据
- 文件路径含中文时，使用短 8.3 路径或正斜杠

## 常用命令

### 后端 (Python / FastAPI)

```bash
# 安装依赖（项目根目录执行）
cd backend && pip install -r requirements.txt

# 启动开发服务器
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 本地 SQLite 演示（无需 MySQL）
cd backend && DATABASE_URL="sqlite:///./intraai.db" SEED_DEMO_DATA=true uvicorn app.main:app --reload --port 8000

# 运行全部测试
python -m pytest backend/tests/ -q --tb=short

# 运行平台核心测试
python -m pytest backend/tests/api/test_platform.py -v --tb=short

# 覆盖率
python -m pytest backend/tests/ --cov=backend/app --cov-report=term-missing

# 代码检查
cd backend && ruff check app/
cd backend && ruff format app/

# 数据库迁移
cd backend && alembic upgrade head
cd backend && alembic revision --autogenerate -m "描述"
```

### 前端 (Vue 3 / Vite)

```bash
cd frontend
npm install
npm run dev      # 端口 5173，API 指向 localhost:8000
npm run build
npm run lint
npm test
```

`start-dev.bat` 可同时启动前后端。

## 架构概览

### 后端结构 (`backend/app/`)

```
app/
├── api/              # 路由层
│   ├── auth.py / users.py        # 注册登录、个人资料
│   ├── products.py               # 品牌型号、能力、用户设备（含 /api/admin/products）
│   ├── knowledge.py              # 用户端知识中心（仅已审核/已发布）
│   ├── assistant.py              # 智能客服会话与 SSE 流式回答
│   ├── diagnosis.py              # 诊断会话、步骤反馈
│   ├── tickets.py                # 用户工单 + 客服工单管理
│   ├── knowledge_admin.py        # 来源、导入、审核、发布、索引
│   ├── cases.py                  # 维修案例管理
│   ├── evaluation.py             # 评测中心
│   ├── admin_platform.py         # 驾驶舱、配置、审计、检索日志
│   ├── admin.py                  # 旧版用户管理（兼容保留）
│   └── chat.py 等                # 旧版通用知识库/聊天接口（兼容保留）
├── domains/printer/  # registry（型号解析）、capabilities、fault_taxonomy、safety_policy
├── core/             # 配置、数据库、JWT + bcrypt
├── models/           # 品牌型号/知识/诊断/工单/客服/评测/审计
├── schemas/          # Pydantic 请求响应
├── services/
│   ├── printer_rag_service.py    # 硬过滤 + 向量/BM25 + RRF + 重排 + Evidence Gate
│   ├── diagnosis_service.py      # 诊断状态机
│   ├── knowledge_ingestion.py    # 文件解析、切片、结构化草稿
│   ├── knowledge_review.py       # 审核、发布、索引、回滚
│   ├── ticket_service.py         # 工单流转与脱敏
│   ├── evaluation_service.py     # 真实检索指标计算
│   ├── audit_service.py          # 审计日志
│   └── vector_store.py / embedding.py / reranker.py / llm.py  # 基础能力
└── seed.py           # 幂等种子数据（4 品牌 / 9 型号 / 24 条知识 / 5 个测试集）
```

### 核心数据流

1. **智能客服**：问题 → 识别型号/错误码/故障类别 → 型号+品类硬过滤 → 向量+BM25 → RRF → CrossEncoder → Evidence Gate → LLM（失败时模板回退）→ 带来源回答
2. **故障诊断**：确认型号 → 校验支持状态与能力 → 检索 → 生成 L1/L2 步骤 → 一次一条 → 用户反馈 → 下一条或转人工
3. **知识发布**：来源登记 → 导入解析 → 待审核草稿 → 审核通过 → 发布 → 写入 Chroma；未发布知识不参与检索
4. **工单**：诊断/用户确认 → 建单（携带步骤与证据）→ 分配 → 处理 → 关闭；用户与客服权限隔离

### 前端结构 (`frontend/src/`)

- **布局**: `components/PlatformLayout.vue` 按角色显示用户端/运营端导航
- **用户页面**: `views/user/` — Dashboard、ProductCatalog、ProductDetail、KnowledgeCenter、Assistant、DiagnosisWorkspace、DiagnosisDetail、TicketList/Detail、Maintenance、History、Profile
- **管理页面**: `views/admin/` — Dashboard、ModelAdmin、KnowledgeSources/Import/Review、RepairCaseAdmin、TicketAdmin、Evaluation、UserAdmin、Settings
- **API**: `src/api/*.js`，Axios 自动注入 token；SSE 由 `assistant.js` 的 `streamMessage` 处理
- **路由**: `src/router/index.js` 使用嵌套路由 + 角色守卫

### 角色与权限

`user` / `agent`（客服）/ `knowledge_admin`（知识管理员）/ `system_admin`（系统管理员）。旧 `is_admin=True` 视为 `system_admin`。后端依赖：`get_staff`、`get_knowledge_manager`、`get_support_staff`、`get_system_admin`。

### 配置

- `app/core/config.py`：`DATABASE_URL` 为空时由 `MYSQL_*` 拼接；`SEED_DEMO_DATA` 控制启动种子；`AUTO_INDEX_SEED` 控制启动时构建向量索引；`ENABLE_LEGACY_AGENT` 默认 False（旧版 SQL Agent 已停用）
- 关键环境变量：`OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`、`MYSQL_*`、`SECRET_KEY`、`UPLOAD_DIR`、`CHROMA_DIR`

## 开发规范

- 每次只改一个文件，验证通过后再改下一个
- 业务规则放在领域服务（`domains/printer`、`services`），不要全部塞进 prompt
- 不重写底层 vector store；通过 metadata filter 与查询路径扩展
- 知识必须有来源、适用范围、步骤、安全提示才允许发布
- 品牌错误码不得跨品牌映射；型号未知的社区案例不得转化为型号结论
- 改完后验证完整流程：注册 → 登录 → 选型号 → 客服/诊断 → 工单；每步检查日志

## 测试约定

- 使用 SQLite 内存数据库；`conftest.py` 提供 `client`、`test_user`/`test_admin`、`user_headers`/`admin_headers`
- `tests/api/test_platform.py` 使用 `seeded` fixture + `platform_env` 隔离 embedding/reranker/LLM/Chroma
- 外部依赖全部 mock；保留旧版测试（326 条）确保兼容接口不回归
- pytest 配置：`asyncio_mode = "auto"`、`pythonpath = ["backend"]`、`testpaths = ["backend/tests"]`

## 部署注意事项

- 远程服务器可能没有 `.env`，部署前先检查
- MySQL 部署启动时自动 `alembic upgrade head`；SQLite 模式直接 `create_all`
- Docker 镜像像没更新时用 `--no-cache` 重建
- 部署后必须测试完整用户流程再宣告成功
- 演示种子数据是人工整理知识（C 级）关联官方来源（A 级），不能当作官方手册原文使用