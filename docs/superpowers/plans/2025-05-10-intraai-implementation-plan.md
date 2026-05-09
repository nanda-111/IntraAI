# IntraAI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从零搭建 IntraAI 企业内部 AI 助手平台，包含知识库/RAG、用户权限、管理后台，支持 Docker 部署

**Architecture:** Python FastAPI 后端 + Vue 3 前端 + MySQL 业务数据 + ChromaDB 向量存储，分 6 个阶段逐步搭建，每个阶段可独立运行验证

**Tech Stack:** FastAPI, SQLAlchemy, MySQL 8.0, ChromaDB, Vue 3, Ant Design Vue, Docker Compose

---

## File Structure (项目文件总览)

```
F:/a/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI 入口，注册路由
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py        # 配置（数据库连接、JWT密钥等）
│   │   │   ├── database.py      # 数据库引擎和会话管理
│   │   │   └── security.py      # 密码加密、JWT生成/验证
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py          # 用户表
│   │   │   ├── knowledge_base.py # 知识库表
│   │   │   ├── document.py      # 文档表
│   │   │   ├── conversation.py  # 对话记录表
│   │   │   └── usage_log.py     # 用量日志表
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── user.py          # 用户请求/响应模型
│   │   │   ├── knowledge_base.py
│   │   │   ├── document.py
│   │   │   └── chat.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py          # 依赖注入（获取当前用户等）
│   │   │   ├── auth.py          # 登录/注册接口
│   │   │   ├── users.py         # 用户管理接口
│   │   │   ├── knowledge_bases.py # 知识库接口
│   │   │   ├── documents.py     # 文档接口
│   │   │   ├── chat.py          # 对话接口
│   │   │   └── admin.py         # 管理后台接口
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── document_processor.py  # 文档解析+切片
│   │       ├── vector_store.py        # ChromaDB操作
│   │       ├── embedding.py           # 向量化
│   │       ├── llm.py                 # LLM调用
│   │       └── rag.py                 # RAG流程编排
│   ├── uploads/                 # 上传文件存储目录
│   ├── chroma_data/             # ChromaDB持久化目录
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── main.js              # Vue入口
│   │   ├── App.vue              # 根组件
│   │   ├── api/
│   │   │   ├── index.js         # Axios配置
│   │   │   ├── auth.js          # 登录/注册API
│   │   │   ├── knowledge.js     # 知识库API
│   │   │   ├── chat.js          # 对话API
│   │   │   └── admin.js         # 管理API
│   │   ├── router/
│   │   │   └── index.js         # 路由配置
│   │   ├── stores/
│   │   │   └── auth.js          # 认证状态
│   │   ├── views/
│   │   │   ├── LoginView.vue    # 登录页
│   │   │   ├── ChatView.vue     # 对话页
│   │   │   ├── KnowledgeView.vue # 知识库页
│   │   │   └── AdminView.vue    # 管理后台
│   │   └── components/
│   │       ├── ChatMessage.vue  # 聊天气泡
│   │       └── FileUpload.vue   # 文件上传
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── Dockerfile
├── docker-compose.yml
└── docs/
    └── superpowers/
        └── specs/
            └── 2025-05-10-ai-assistant-platform-design.md
```

---

# 阶段 1：后端基础（FastAPI + SQLAlchemy + MySQL）

**学习目标：** 理解 REST API 开发、ORM 概念、数据库操作、JWT 认证

**验证标准：** 用 Postman/curl 能测试所有 API 接口

## Task 1.1: 项目初始化与依赖安装

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`

- [ ] **Step 1: 创建 requirements.txt**

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
sqlalchemy==2.0.36
pymysql==1.1.1
cryptography==44.0.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.20
pydantic-settings==2.7.1
chromadb==0.6.3
PyMuPDF==1.25.1
python-docx==1.1.2
openai==1.58.1
httpx==0.28.1
```

- [ ] **Step 2: 创建 .env.example**

```env
# 数据库
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DB=intraai

# JWT
SECRET_KEY=your-secret-key-change-this-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# OpenAI (或兼容API)
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# 文件存储
UPLOAD_DIR=./uploads
CHROMA_DIR=./chroma_data
```

- [ ] **Step 3: 创建 backend/app/__init__.py**

```python
# 空文件，标记为Python包
```

- [ ] **Step 4: 创建 FastAPI 入口文件**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="IntraAI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok"}
```

- [ ] **Step 5: 安装依赖并验证**

```bash
cd F:/a/backend
python -m venv venv
source venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Expected: 启动成功，访问 http://localhost:8000/health 返回 `{"status":"ok"}`，访问 http://localhost:8000/docs 看到 Swagger 文档

---

## Task 1.2: 配置管理

**Files:**
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`

- [ ] **Step 1: 创建配置模块**

```python
# backend/app/core/__init__.py
```

```python
# backend/app/core/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # MySQL
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DB: str = "intraai"

    # JWT
    SECRET_KEY: str = "dev-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24小时

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # 文件
    UPLOAD_DIR: str = "./uploads"
    CHROMA_DIR: str = "./chroma_data"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
        )

    class Config:
        env_file = ".env"


settings = Settings()
```

- [ ] **Step 2: 创建 .env 文件并测试**

```bash
cp .env.example .env
# 编辑 .env 填入你的 MySQL 密码
```

在 main.py 中验证配置加载：

```python
# backend/app/main.py — 追加测试路由
from app.core.config import settings

@app.get("/config-check")
def config_check():
    return {
        "db": settings.MYSQL_DB,
        "model": settings.OPENAI_MODEL,
    }
```

访问 http://localhost:8000/config-check 确认配置加载正确，然后删除这个测试路由。

---

## Task 1.3: 数据库连接

**Files:**
- Create: `backend/app/core/database.py`

- [ ] **Step 1: 创建数据库模块**

```python
# backend/app/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI 依赖：每次请求获取一个数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 2: 创建 MySQL 数据库**

在 MySQL 中执行：

```sql
CREATE DATABASE intraai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

- [ ] **Step 3: 在 main.py 中测试连接**

```python
# backend/app/main.py — 追加
from app.core.database import engine
from sqlalchemy import text

@app.get("/db-check")
def db_check():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        return {"db": result.scalar()}
```

访问 http://localhost:8000/db-check 返回 `{"db": 1}` 表示数据库连接成功，然后删除此路由。

---

## Task 1.4: 用户数据模型

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/user.py`

- [ ] **Step 1: 创建用户模型**

```python
# backend/app/models/__init__.py
from app.models.user import User
```

```python
# backend/app/models/user.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

- [ ] **Step 2: 创建数据库表**

在 main.py 启动时自动建表：

```python
# backend/app/main.py — 追加
from app.core.database import Base, engine
import app.models  # 导入所有模型

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
```

重启服务，检查 MySQL 中是否生成了 `users` 表：

```sql
USE intraai;
DESCRIBE users;
```

---

## Task 1.5: 安全工具（密码 + JWT）

**Files:**
- Create: `backend/app/core/security.py`

- [ ] **Step 1: 创建安全模块**

```python
# backend/app/core/security.py
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
```

- [ ] **Step 2: 测试安全功能**

在 main.py 添加临时测试：

```python
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token

@app.get("/security-test")
def security_test():
    hashed = hash_password("123456")
    ok = verify_password("123456", hashed)
    token = create_access_token({"sub": "testuser"})
    payload = decode_access_token(token)
    return {"password_ok": ok, "token_sub": payload["sub"]}
```

访问验证，然后删除此路由。

---

## Task 1.6: Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/user.py`

- [ ] **Step 1: 创建用户 Schema**

```python
# backend/app/schemas/__init__.py
```

```python
# backend/app/schemas/user.py
from datetime import datetime
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    is_admin: bool
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
```

注意：这里 email 用 `str` 而不是 `EmailStr`，避免额外依赖。如果需要邮箱校验，可以 `pip install email-validator` 后改为 `EmailStr`。

---

## Task 1.7: 认证 API（注册 + 登录）

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/deps.py`
- Create: `backend/app/api/auth.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 创建依赖注入**

```python
# backend/app/api/__init__.py
```

```python
# backend/app/api/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(token)
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="无效的令牌")
    except JWTError:
        raise HTTPException(status_code=401, detail="无效的令牌")

    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    return user


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user
```

- [ ] **Step 2: 创建认证路由**

```python
# backend/app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, Token, UserOut

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=UserOut)
def register(data: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="邮箱已注册")

    # 第一个注册的用户自动成为管理员
    is_first = db.query(User).count() == 0

    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        is_admin=is_first,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用")

    token = create_access_token({"sub": user.username})
    return Token(access_token=token, user=user)
```

- [ ] **Step 3: 注册路由到 main.py**

```python
# backend/app/main.py — 修改
from app.api.auth import router as auth_router

app.include_router(auth_router)
```

- [ ] **Step 4: 测试注册和登录**

```bash
# 注册
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","email":"admin@test.com","password":"123456"}'

# 登录
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"123456"}'
```

Expected: 注册返回用户信息（第一个用户 is_admin=true），登录返回 access_token。

---

## Task 1.8: 用户管理 API

**Files:**
- Create: `backend/app/api/users.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 创建用户管理路由**

```python
# backend/app/api/users.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserOut

router = APIRouter(prefix="/api/users", tags=["用户"])


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
```

- [ ] **Step 2: 注册路由**

```python
# backend/app/main.py — 追加
from app.api.users import router as users_router

app.include_router(users_router)
```

- [ ] **Step 3: 测试获取当前用户**

```bash
# 用登录获取的 token
curl http://localhost:8000/api/users/me \
  -H "Authorization: Bearer <你的token>"
```

---

## Task 1.9: 知识库 + 文档数据模型

**Files:**
- Create: `backend/app/models/knowledge_base.py`
- Create: `backend/app/models/document.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: 创建知识库模型**

```python
# backend/app/models/knowledge_base.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.core.database import Base


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

- [ ] **Step 2: 创建文档模型**

```python
# backend/app/models/document.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False)  # pdf/docx/txt/md
    file_size = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)  # 切片数量
    kb_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
```

- [ ] **Step 3: 更新 models/__init__.py**

```python
# backend/app/models/__init__.py
from app.models.user import User
from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document
```

重启服务，检查 MySQL 新表是否创建成功。

---

## Task 1.10: 知识库 CRUD API

**Files:**
- Create: `backend/app/schemas/knowledge_base.py`
- Create: `backend/app/api/knowledge_bases.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 创建知识库 Schema**

```python
# backend/app/schemas/knowledge_base.py
from datetime import datetime
from pydantic import BaseModel


class KBCreate(BaseModel):
    name: str
    description: str | None = None


class KBUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class KBOut(BaseModel):
    id: int
    name: str
    description: str | None
    owner_id: int
    created_at: datetime

    class Config:
        from_attributes = True
```

- [ ] **Step 2: 创建知识库路由**

```python
# backend/app/api/knowledge_bases.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.knowledge_base import KnowledgeBase
from app.schemas.knowledge_base import KBCreate, KBUpdate, KBOut

router = APIRouter(prefix="/api/knowledge-bases", tags=["知识库"])


@router.post("/", response_model=KBOut)
def create_kb(
    data: KBCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    kb = KnowledgeBase(name=data.name, description=data.description, owner_id=current_user.id)
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return kb


@router.get("/", response_model=list[KBOut])
def list_kbs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.is_admin:
        return db.query(KnowledgeBase).all()
    return db.query(KnowledgeBase).filter(KnowledgeBase.owner_id == current_user.id).all()


@router.get("/{kb_id}", response_model=KBOut)
def get_kb(
    kb_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if not current_user.is_admin and kb.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问")
    return kb


@router.put("/{kb_id}", response_model=KBOut)
def update_kb(
    kb_id: int,
    data: KBUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if not current_user.is_admin and kb.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权修改")
    if data.name is not None:
        kb.name = data.name
    if data.description is not None:
        kb.description = data.description
    db.commit()
    db.refresh(kb)
    return kb


@router.delete("/{kb_id}")
def delete_kb(
    kb_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if not current_user.is_admin and kb.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除")
    db.delete(kb)
    db.commit()
    return {"message": "已删除"}
```

- [ ] **Step 3: 注册路由**

```python
# backend/app/main.py — 追加
from app.api.knowledge_bases import router as kb_router

app.include_router(kb_router)
```

- [ ] **Step 4: 测试 CRUD**

```bash
# 创建知识库
curl -X POST http://localhost:8000/api/knowledge-bases/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"name":"技术文档库","description":"存放技术相关文档"}'

# 列表
curl http://localhost:8000/api/knowledge-bases/ \
  -H "Authorization: Bearer <token>"
```

---

阶段 1 完成。后端基础 API 全部可用：注册、登录、知识库 CRUD。用 Postman 或 Swagger 文档 (http://localhost:8000/docs) 逐一测试。

---

# 阶段 2：前端基础（Vue 3 + Ant Design Vue）

**学习目标：** Vue 3 组合式 API、组件化开发、前后端联调、路由与状态管理

**验证标准：** 浏览器能打开页面，能登录、查看知识库列表

## Task 2.1: 初始化前端项目

**Files:**
- Create: `frontend/` (via Vite)

- [ ] **Step 1: 用 Vite 创建 Vue 项目**

```bash
cd F:/a
npm create vite@latest frontend -- --template vue
cd frontend
npm install
npm install ant-design-vue @ant-design/icons-vue
npm install vue-router@4 pinia axios
npm install markdown-it
```

- [ ] **Step 2: 清理默认文件**

删除 `frontend/src/components/HelloWorld.vue`、`frontend/src/assets/vue.svg` 等默认文件。

---

## Task 2.2: 项目入口与路由

**Files:**
- Create: `frontend/src/router/index.js`
- Modify: `frontend/src/main.js`
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: 创建路由配置**

```javascript
// frontend/src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
  },
  {
    path: '/',
    name: 'Chat',
    component: () => import('../views/ChatView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/knowledge',
    name: 'Knowledge',
    component: () => import('../views/KnowledgeView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('../views/AdminView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router
```

- [ ] **Step 2: 修改 main.js**

```javascript
// frontend/src/main.js
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(Antd)
app.mount('#app')
```

- [ ] **Step 3: 修改 App.vue 为路由出口**

```vue
<!-- frontend/src/App.vue -->
<template>
  <router-view />
</template>
```

---

## Task 2.3: Axios 封装与 API 模块

**Files:**
- Create: `frontend/src/api/index.js`
- Create: `frontend/src/api/auth.js`
- Create: `frontend/src/api/knowledge.js`

- [ ] **Step 1: Axios 配置**

```javascript
// frontend/src/api/index.js
import axios from 'axios'
import { message } from 'ant-design-vue'

const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    message.error(err.response?.data?.detail || '请求失败')
    return Promise.reject(err)
  }
)

export default api
```

- [ ] **Step 2: 认证 API**

```javascript
// frontend/src/api/auth.js
import api from './index'

export function login(data) {
  return api.post('/api/auth/login', data)
}

export function register(data) {
  return api.post('/api/auth/register', data)
}

export function getMe() {
  return api.get('/api/users/me')
}
```

- [ ] **Step 3: 知识库 API**

```javascript
// frontend/src/api/knowledge.js
import api from './index'

export function listKnowledgeBases() {
  return api.get('/api/knowledge-bases/')
}

export function createKnowledgeBase(data) {
  return api.post('/api/knowledge-bases/', data)
}

export function deleteKnowledgeBase(id) {
  return api.delete(`/api/knowledge-bases/${id}`)
}
```

---

## Task 2.4: 认证状态管理

**Files:**
- Create: `frontend/src/stores/auth.js`

- [ ] **Step 1: 创建 Pinia Store**

```javascript
// frontend/src/stores/auth.js
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as loginApi, register as registerApi, getMe } from '../api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(null)

  async function login(data) {
    const res = await loginApi(data)
    token.value = res.data.access_token
    user.value = res.data.user
    localStorage.setItem('token', token.value)
  }

  async function register(data) {
    await registerApi(data)
  }

  async function fetchUser() {
    if (!token.value) return
    const res = await getMe()
    user.value = res.data
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
  }

  return { token, user, login, register, fetchUser, logout }
})
```

---

## Task 2.5: 登录页面

**Files:**
- Create: `frontend/src/views/LoginView.vue`

- [ ] **Step 1: 创建登录页**

```vue
<!-- frontend/src/views/LoginView.vue -->
<template>
  <div class="login-container">
    <a-card class="login-card" :title="isLogin ? '登录 IntraAI' : '注册 IntraAI'">
      <a-form :model="form" @finish="handleSubmit" layout="vertical">
        <a-form-item label="用户名" name="username" :rules="[{ required: true }]">
          <a-input v-model:value="form.username" placeholder="请输入用户名" />
        </a-form-item>
        <a-form-item v-if="!isLogin" label="邮箱" name="email" :rules="[{ required: true }]">
          <a-input v-model:value="form.email" placeholder="请输入邮箱" />
        </a-form-item>
        <a-form-item label="密码" name="password" :rules="[{ required: true }]">
          <a-input-password v-model:value="form.password" placeholder="请输入密码" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" html-type="submit" :loading="loading" block>
            {{ isLogin ? '登录' : '注册' }}
          </a-button>
        </a-form-item>
        <a @click="isLogin = !isLogin" style="text-align: center; display: block; cursor: pointer">
          {{ isLogin ? '没有账号？去注册' : '已有账号？去登录' }}
        </a>
      </a-form>
    </a-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const isLogin = ref(true)
const loading = ref(false)
const form = reactive({ username: '', email: '', password: '' })

async function handleSubmit() {
  loading.value = true
  try {
    if (isLogin.value) {
      await authStore.login({ username: form.username, password: form.password })
      message.success('登录成功')
      router.push('/')
    } else {
      await authStore.register(form)
      message.success('注册成功，请登录')
      isLogin.value = true
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: #f0f2f5;
}
.login-card {
  width: 400px;
}
</style>
```

---

## Task 2.6: 知识库页面

**Files:**
- Create: `frontend/src/views/KnowledgeView.vue`

- [ ] **Step 1: 创建知识库列表页**

```vue
<!-- frontend/src/views/KnowledgeView.vue -->
<template>
  <a-layout>
    <a-layout-header class="header">
      <div class="logo">IntraAI</div>
      <a-menu theme="dark" mode="horizontal" :selected-keys="['knowledge']">
        <a-menu-item key="chat" @click="$router.push('/')">对话</a-menu-item>
        <a-menu-item key="knowledge">知识库</a-menu-item>
        <a-menu-item key="admin" v-if="authStore.user?.is_admin" @click="$router.push('/admin')">管理</a-menu-item>
      </a-menu>
      <a-button type="text" style="color: white" @click="handleLogout">退出</a-button>
    </a-layout-header>
    <a-layout-content style="padding: 24px">
      <a-card title="知识库管理">
        <template #extra>
          <a-button type="primary" @click="showCreate = true">新建知识库</a-button>
        </template>
        <a-table :data-source="kbs" :columns="columns" :loading="loading" row-key="id">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'action'">
              <a-popconfirm title="确认删除？" @confirm="handleDelete(record.id)">
                <a-button type="link" danger>删除</a-button>
              </a-popconfirm>
            </template>
          </template>
        </a-table>
      </a-card>
      <a-modal v-model:open="showCreate" title="新建知识库" @ok="handleCreate">
        <a-form layout="vertical">
          <a-form-item label="名称" required>
            <a-input v-model:value="newKb.name" />
          </a-form-item>
          <a-form-item label="描述">
            <a-textarea v-model:value="newKb.description" />
          </a-form-item>
        </a-form>
      </a-modal>
    </a-layout-content>
  </a-layout>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useAuthStore } from '../stores/auth'
import { listKnowledgeBases, createKnowledgeBase, deleteKnowledgeBase } from '../api/knowledge'

const router = useRouter()
const authStore = useAuthStore()
const kbs = ref([])
const loading = ref(false)
const showCreate = ref(false)
const newKb = reactive({ name: '', description: '' })

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '描述', dataIndex: 'description', key: 'description' },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at' },
  { title: '操作', key: 'action', width: 100 },
]

async function fetchKbs() {
  loading.value = true
  try {
    const res = await listKnowledgeBases()
    kbs.value = res.data
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  await createKnowledgeBase(newKb)
  message.success('创建成功')
  showCreate.value = false
  newKb.name = ''
  newKb.description = ''
  fetchKbs()
}

async function handleDelete(id) {
  await deleteKnowledgeBase(id)
  message.success('已删除')
  fetchKbs()
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

onMounted(async () => {
  await authStore.fetchUser()
  fetchKbs()
})
</script>

<style scoped>
.header {
  display: flex;
  align-items: center;
}
.logo {
  color: white;
  font-size: 18px;
  font-weight: bold;
  margin-right: 24px;
}
</style>
```

---

## Task 2.7: 对话和管理页面占位

**Files:**
- Create: `frontend/src/views/ChatView.vue`
- Create: `frontend/src/views/AdminView.vue`

- [ ] **Step 1: 创建对话页占位**

```vue
<!-- frontend/src/views/ChatView.vue -->
<template>
  <a-layout>
    <a-layout-header class="header">
      <div class="logo">IntraAI</div>
      <a-menu theme="dark" mode="horizontal" :selected-keys="['chat']">
        <a-menu-item key="chat">对话</a-menu-item>
        <a-menu-item key="knowledge" @click="$router.push('/knowledge')">知识库</a-menu-item>
        <a-menu-item key="admin" v-if="authStore.user?.is_admin" @click="$router.push('/admin')">管理</a-menu-item>
      </a-menu>
      <a-button type="text" style="color: white" @click="handleLogout">退出</a-button>
    </a-layout-header>
    <a-layout-content style="padding: 24px; display: flex; justify-content: center; align-items: center;">
      <a-empty description="对话功能将在阶段 4 实现" />
    </a-layout-content>
  </a-layout>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

onMounted(() => authStore.fetchUser())
</script>
```

- [ ] **Step 2: 创建管理页占位**

```vue
<!-- frontend/src/views/AdminView.vue -->
<template>
  <a-layout>
    <a-layout-header class="header">
      <div class="logo">IntraAI</div>
      <a-menu theme="dark" mode="horizontal" :selected-keys="['admin']">
        <a-menu-item key="chat" @click="$router.push('/')">对话</a-menu-item>
        <a-menu-item key="knowledge" @click="$router.push('/knowledge')">知识库</a-menu-item>
        <a-menu-item key="admin">管理</a-menu-item>
      </a-menu>
      <a-button type="text" style="color: white" @click="handleLogout">退出</a-button>
    </a-layout-header>
    <a-layout-content style="padding: 24px; display: flex; justify-content: center; align-items: center;">
      <a-empty description="管理后台将在阶段 5 实现" />
    </a-layout-content>
  </a-layout>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>
```

- [ ] **Step 3: 启动前端测试**

```bash
cd F:/a/frontend
npm run dev
```

浏览器访问 http://localhost:5173，测试：
1. 自动跳转到登录页
2. 注册新用户
3. 登录后看到知识库列表页
4. 创建/删除知识库
5. 顶部导航切换页面
6. 退出登录

---

阶段 2 完成。前端可以登录、管理知识库，对话页和管理后台为占位。

---

# 阶段 3：知识库功能（文档解析 + 向量化）

**学习目标：** 理解文本切片原理、向量化（Embedding）、向量相似度检索

**验证标准：** 上传文档后能在 ChromaDB 中检索到相关切片

## Task 3.1: 文档上传 API

**Files:**
- Create: `backend/app/schemas/document.py`
- Create: `backend/app/api/documents.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 创建文档 Schema**

```python
# backend/app/schemas/document.py
from datetime import datetime
from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: int
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    kb_id: int
    created_at: datetime

    class Config:
        from_attributes = True
```

- [ ] **Step 2: 创建文档路由**

```python
# backend/app/api/documents.py
import os
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document
from app.schemas.document import DocumentOut

router = APIRouter(prefix="/api/documents", tags=["文档"])

ALLOWED_TYPES = {"pdf", "docx", "txt", "md"}


@router.post("/upload/{kb_id}", response_model=DocumentOut)
async def upload_document(
    kb_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 检查知识库权限
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if not current_user.is_admin and kb.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作")

    # 检查文件类型
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}")

    # 保存文件
    upload_dir = os.path.join(settings.UPLOAD_DIR, str(kb_id))
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, file.filename)
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    # 保存记录
    doc = Document(
        filename=file.filename,
        filepath=filepath,
        file_type=ext,
        file_size=len(content),
        kb_id=kb_id,
        uploaded_by=current_user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/list/{kb_id}", response_model=list[DocumentOut])
def list_documents(
    kb_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return db.query(Document).filter(Document.kb_id == kb_id).all()


@router.delete("/{doc_id}")
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    # 删除文件
    if os.path.exists(doc.filepath):
        os.remove(doc.filepath)
    db.delete(doc)
    db.commit()
    return {"message": "已删除"}
```

- [ ] **Step 3: 注册路由**

```python
# backend/app/main.py — 追加
from app.api.documents import router as docs_router

app.include_router(docs_router)
```

- [ ] **Step 4: 创建 uploads 目录并测试上传**

```bash
mkdir -p F:/a/backend/uploads
```

用 Swagger 文档测试文件上传，或用 curl：

```bash
curl -X POST http://localhost:8000/api/documents/upload/1 \
  -H "Authorization: Bearer <token>" \
  -F "file=@/path/to/test.txt"
```

---

## Task 3.2: 文档解析与文本切片

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/document_processor.py`

- [ ] **Step 1: 创建文档处理服务**

```python
# backend/app/services/__init__.py
```

```python
# backend/app/services/document_processor.py
import os
import fitz  # PyMuPDF
from docx import Document as DocxDocument


def extract_text(filepath: str, file_type: str) -> str:
    """根据文件类型提取文本"""
    if file_type == "pdf":
        return _extract_pdf(filepath)
    elif file_type == "docx":
        return _extract_docx(filepath)
    elif file_type in ("txt", "md"):
        return _extract_text_file(filepath)
    else:
        raise ValueError(f"不支持的文件类型: {file_type}")


def _extract_pdf(filepath: str) -> str:
    doc = fitz.open(filepath)
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts)


def _extract_docx(filepath: str) -> str:
    doc = DocxDocument(filepath)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _extract_text_file(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def split_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """按固定长度切分文本，带重叠"""
    if not text.strip():
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap  # 重叠部分
        if start < 0:
            start = 0
    return chunks
```

- [ ] **Step 2: 测试文档处理**

在 main.py 添加临时测试：

```python
from app.services.document_processor import extract_text, split_text

@app.get("/doc-test")
def doc_test():
    # 创建测试文件
    test_path = "test_doc.txt"
    with open(test_path, "w", encoding="utf-8") as f:
        f.write("这是一段测试文本。" * 100)
    text = extract_text(test_path, "txt")
    chunks = split_text(text, chunk_size=100, overlap=20)
    os.remove(test_path)
    return {"text_length": len(text), "chunk_count": len(chunks), "first_chunk": chunks[0] if chunks else ""}
```

验证切片逻辑正确后删除此路由。

---

## Task 3.3: 向量化与 ChromaDB

**Files:**
- Create: `backend/app/services/embedding.py`
- Create: `backend/app/services/vector_store.py`

- [ ] **Step 1: 创建 Embedding 服务**

```python
# backend/app/services/embedding.py
from openai import OpenAI
from app.core.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """调用 OpenAI Embedding API 获取向量"""
    response = client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]
```

- [ ] **Step 2: 创建向量存储服务**

```python
# backend/app/services/vector_store.py
import chromadb
from app.core.config import settings

# 嵌入式 ChromaDB，数据持久化到本地目录
_client = chromadb.PersistentClient(path=settings.CHROMA_DIR)


def get_collection(kb_id: int):
    """获取或创建知识库对应的向量集合"""
    return _client.get_or_create_collection(
        name=f"kb_{kb_id}",
        metadata={"hnsw:space": "cosine"},
    )


def add_documents(kb_id: int, chunks: list[str], embeddings: list[list[float]]):
    """将文档切片和向量存入 ChromaDB"""
    collection = get_collection(kb_id)
    existing = collection.count()
    ids = [f"chunk_{existing + i}" for i in range(len(chunks))]
    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
    )
    return len(chunks)


def search(kb_id: int, query_embedding: list[float], top_k: int = 5) -> list[str]:
    """检索与问题最相关的文档切片"""
    collection = get_collection(kb_id)
    if collection.count() == 0:
        return []
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
    )
    return results["documents"][0] if results["documents"] else []
```

---

## Task 3.4: 文档处理流水线（上传后自动切片+向量化）

**Files:**
- Modify: `backend/app/api/documents.py`

- [ ] **Step 1: 在上传接口中集成处理流水线**

修改 `upload_document` 函数，在保存文件后添加切片+向量化：

```python
# backend/app/api/documents.py — 在 save doc 之前加入处理逻辑
# （替换原来的 doc = Document(...) 和 db.add(doc) 部分）

from app.services.document_processor import extract_text, split_text
from app.services.embedding import get_embeddings
from app.services.vector_store import add_documents

@router.post("/upload/{kb_id}", response_model=DocumentOut)
async def upload_document(
    kb_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 检查权限（不变）
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if not current_user.is_admin and kb.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}")

    # 保存文件
    upload_dir = os.path.join(settings.UPLOAD_DIR, str(kb_id))
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, file.filename)
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    # 文档解析 → 切片 → 向量化 → 存入 ChromaDB
    text = extract_text(filepath, ext)
    chunks = split_text(text, chunk_size=500, overlap=50)
    chunk_count = 0
    if chunks:
        # 批量获取向量（每批最多100条，避免API限制）
        all_embeddings = []
        for i in range(0, len(chunks), 100):
            batch = chunks[i:i + 100]
            embeddings = get_embeddings(batch)
            all_embeddings.extend(embeddings)
        chunk_count = add_documents(kb_id, chunks, all_embeddings)

    doc = Document(
        filename=file.filename,
        filepath=filepath,
        file_type=ext,
        file_size=len(content),
        chunk_count=chunk_count,
        kb_id=kb_id,
        uploaded_by=current_user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc
```

- [ ] **Step 2: 测试完整流程**

1. 上传一个文本文件到知识库
2. 检查 ChromaDB 目录（`backend/chroma_data/`）是否生成了数据
3. 检查文档记录的 `chunk_count` 是否大于 0

注意：此步骤需要有效的 OpenAI API Key。

---

## Task 3.5: 向量检索测试接口

**Files:**
- Modify: `backend/app/api/documents.py`

- [ ] **Step 1: 添加检索测试接口**

```python
from app.services.embedding import get_embeddings
from app.services.vector_store import search

@router.post("/search/{kb_id}")
def search_kb(
    kb_id: int,
    query: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    query_embedding = get_embeddings([query])[0]
    results = search(kb_id, query_embedding, top_k=3)
    return {"query": query, "results": results}
```

- [ ] **Step 2: 测试检索**

在 Swagger 文档中调用搜索接口，输入与文档内容相关的问题，验证返回的切片是否相关。

---

阶段 3 完成。文档上传后自动解析、切片、向量化并存入 ChromaDB，支持向量检索。

---

# 阶段 4：AI 对话（LLM API + RAG 流程）

**学习目标：** Prompt Engineering、RAG（检索增强生成）完整流程、流式输出

**验证标准：** 在对话页选择知识库提问，AI 能基于文档内容回答

## Task 4.1: 对话数据模型

**Files:**
- Create: `backend/app/models/conversation.py`
- Create: `backend/app/models/usage_log.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: 创建对话模型**

```python
# backend/app/models/conversation.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.core.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    kb_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
```

- [ ] **Step 2: 创建用量日志模型**

```python
# backend/app/models/usage_log.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.core.database import Base


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(50), nullable=False)  # chat, upload, etc.
    tokens_used = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
```

- [ ] **Step 3: 更新 models/__init__.py**

```python
from app.models.user import User
from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document
from app.models.conversation import Conversation
from app.models.usage_log import UsageLog
```

---

## Task 4.2: LLM 调用服务

**Files:**
- Create: `backend/app/services/llm.py`

- [ ] **Step 1: 创建 LLM 服务**

```python
# backend/app/services/llm.py
from openai import OpenAI
from app.core.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)


def chat_completion(messages: list[dict], model: str | None = None) -> str:
    """调用 LLM 获取回答"""
    response = client.chat.completions.create(
        model=model or settings.OPENAI_MODEL,
        messages=messages,
        temperature=0.7,
    )
    return response.choices[0].message.content


def chat_completion_stream(messages: list[dict], model: str | None = None):
    """流式调用 LLM，返回生成器"""
    response = client.chat.completions.create(
        model=model or settings.OPENAI_MODEL,
        messages=messages,
        temperature=0.7,
        stream=True,
    )
    for chunk in response:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
```

---

## Task 4.3: RAG 服务

**Files:**
- Create: `backend/app/services/rag.py`

- [ ] **Step 1: 创建 RAG 编排服务**

```python
# backend/app/services/rag.py
from app.services.embedding import get_embeddings
from app.services.vector_store import search
from app.services.llm import chat_completion, chat_completion_stream

SYSTEM_PROMPT = """你是一个企业内部知识助手。根据以下参考资料回答用户的问题。

要求：
1. 只根据参考资料回答，不要编造信息
2. 如果参考资料中没有相关信息，请明确说明"根据现有知识库，我无法回答这个问题"
3. 回答要简洁、专业

参考资料：
{context}
"""


def ask_with_rag(question: str, kb_id: int) -> str:
    """RAG 完整流程：检索 → 拼 Prompt → 调 LLM"""
    # 1. 问题向量化
    query_embedding = get_embeddings([question])[0]

    # 2. 向量检索
    chunks = search(kb_id, query_embedding, top_k=5)

    # 3. 拼接上下文
    context = "\n\n---\n\n".join(chunks) if chunks else "（无相关资料）"

    # 4. 构造消息
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
        {"role": "user", "content": question},
    ]

    # 5. 调用 LLM
    return chat_completion(messages)


def ask_with_rag_stream(question: str, kb_id: int):
    """RAG 流式版本"""
    query_embedding = get_embeddings([question])[0]
    chunks = search(kb_id, query_embedding, top_k=5)
    context = "\n\n---\n\n".join(chunks) if chunks else "（无相关资料）"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
        {"role": "user", "content": question},
    ]

    yield from chat_completion_stream(messages)
```

---

## Task 4.4: 对话 API

**Files:**
- Create: `backend/app/schemas/chat.py`
- Create: `backend/app/api/chat.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 创建对话 Schema**

```python
# backend/app/schemas/chat.py
from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str
    kb_id: int | None = None  # 可选，不选则不走 RAG


class ChatResponse(BaseModel):
    answer: str
    kb_id: int | None = None
```

- [ ] **Step 2: 创建对话路由**

```python
# backend/app/api/chat.py
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.conversation import Conversation
from app.models.usage_log import UsageLog
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rag import ask_with_rag, ask_with_rag_stream
from app.services.llm import chat_completion

router = APIRouter(prefix="/api/chat", tags=["对话"])


@router.post("/", response_model=ChatResponse)
def chat(
    data: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.kb_id:
        answer = ask_with_rag(data.question, data.kb_id)
    else:
        answer = chat_completion([
            {"role": "user", "content": data.question}
        ])

    # 保存对话记录
    conv = Conversation(
        user_id=current_user.id,
        kb_id=data.kb_id,
        question=data.question,
        answer=answer,
    )
    db.add(conv)

    # 记录用量
    log = UsageLog(user_id=current_user.id, action="chat")
    db.add(log)
    db.commit()

    return ChatResponse(answer=answer, kb_id=data.kb_id)


@router.post("/stream")
def chat_stream(
    data: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    def generate():
        full_answer = ""
        if data.kb_id:
            for chunk in ask_with_rag_stream(data.question, data.kb_id):
                full_answer += chunk
                yield f"data: {chunk}\n\n"
        else:
            from app.services.llm import chat_completion_stream as llm_stream
            for chunk in llm_stream([
                {"role": "user", "content": data.question}
            ]):
                full_answer += chunk
                yield f"data: {chunk}\n\n"

        # 异步保存（在生成器结束后）
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

- [ ] **Step 3: 注册路由**

```python
# backend/app/main.py — 追加
from app.api.chat import router as chat_router

app.include_router(chat_router)
```

- [ ] **Step 4: 测试对话 API**

```bash
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"question":"你好","kb_id":1}'
```

---

## Task 4.5: 前端对话页面

**Files:**
- Create: `frontend/src/api/chat.js`
- Create: `frontend/src/components/ChatMessage.vue`
- Modify: `frontend/src/views/ChatView.vue`

- [ ] **Step 1: 创建对话 API**

```javascript
// frontend/src/api/chat.js
import api from './index'

export function sendChat(data) {
  return api.post('/api/chat/', data)
}
```

- [ ] **Step 2: 创建聊天气泡组件**

```vue
<!-- frontend/src/components/ChatMessage.vue -->
<template>
  <div :class="['message', message.role]">
    <div class="avatar">
      {{ message.role === 'user' ? '我' : 'AI' }}
    </div>
    <div class="content" v-html="renderedContent"></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt()
const props = defineProps({ message: Object })

const renderedContent = computed(() => {
  if (props.message.role === 'assistant') {
    return md.render(props.message.content)
  }
  return props.message.content
})
</script>

<style scoped>
.message {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  padding: 8px 0;
}
.message.user {
  flex-direction: row-reverse;
}
.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
}
.message.user .avatar {
  background: #1677ff;
  color: white;
}
.message.assistant .avatar {
  background: #52c41a;
  color: white;
}
.content {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 8px;
  line-height: 1.6;
}
.message.user .content {
  background: #1677ff;
  color: white;
}
.message.assistant .content {
  background: #f5f5f5;
}
</style>
```

- [ ] **Step 3: 重写对话页面**

```vue
<!-- frontend/src/views/ChatView.vue -->
<template>
  <a-layout style="height: 100vh">
    <a-layout-header class="header">
      <div class="logo">IntraAI</div>
      <a-menu theme="dark" mode="horizontal" :selected-keys="['chat']">
        <a-menu-item key="chat">对话</a-menu-item>
        <a-menu-item key="knowledge" @click="$router.push('/knowledge')">知识库</a-menu-item>
        <a-menu-item key="admin" v-if="authStore.user?.is_admin" @click="$router.push('/admin')">管理</a-menu-item>
      </a-menu>
      <a-button type="text" style="color: white" @click="handleLogout">退出</a-button>
    </a-layout-header>
    <a-layout-content class="chat-content">
      <div class="chat-area">
        <div class="messages" ref="messagesRef">
          <a-empty v-if="messages.length === 0" description="选择知识库后开始提问" />
          <ChatMessage v-for="(msg, i) in messages" :key="i" :message="msg" />
        </div>
        <div class="input-area">
          <a-select
            v-model:value="selectedKb"
            placeholder="选择知识库（可选）"
            style="width: 200px; margin-bottom: 8px"
            :options="kbOptions"
            allow-clear
          />
          <div class="input-row">
            <a-textarea
              v-model:value="question"
              placeholder="输入问题..."
              :auto-size="{ minRows: 1, maxRows: 4 }"
              @keydown.enter.exact="handleSend"
            />
            <a-button type="primary" :loading="loading" @click="handleSend">发送</a-button>
          </div>
        </div>
      </div>
    </a-layout-content>
  </a-layout>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useAuthStore } from '../stores/auth'
import { listKnowledgeBases } from '../api/knowledge'
import { sendChat } from '../api/chat'
import ChatMessage from '../components/ChatMessage.vue'

const router = useRouter()
const authStore = useAuthStore()
const messages = ref([])
const question = ref('')
const loading = ref(false)
const selectedKb = ref(null)
const kbOptions = ref([])
const messagesRef = ref(null)

async function fetchKbs() {
  const res = await listKnowledgeBases()
  kbOptions.value = res.data.map(kb => ({ label: kb.name, value: kb.id }))
}

async function handleSend() {
  if (!question.value.trim() || loading.value) return

  const q = question.value.trim()
  question.value = ''
  messages.value.push({ role: 'user', content: q })
  loading.value = true

  await nextTick()
  scrollToBottom()

  try {
    const res = await sendChat({ question: q, kb_id: selectedKb.value })
    messages.value.push({ role: 'assistant', content: res.data.answer })
  } catch {
    message.error('发送失败')
  } finally {
    loading.value = false
    await nextTick()
    scrollToBottom()
  }
}

function scrollToBottom() {
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

onMounted(async () => {
  await authStore.fetchUser()
  fetchKbs()
})
</script>

<style scoped>
.header {
  display: flex;
  align-items: center;
}
.logo {
  color: white;
  font-size: 18px;
  font-weight: bold;
  margin-right: 24px;
}
.chat-content {
  display: flex;
  justify-content: center;
  padding: 24px;
  overflow: hidden;
}
.chat-area {
  width: 100%;
  max-width: 800px;
  display: flex;
  flex-direction: column;
  height: 100%;
}
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px 0;
}
.input-area {
  border-top: 1px solid #f0f0f0;
  padding-top: 12px;
}
.input-row {
  display: flex;
  gap: 8px;
}
</style>
```

- [ ] **Step 4: 测试完整对话流程**

1. 启动前后端
2. 登录 → 进入对话页
3. 选择一个已上传文档的知识库
4. 提问与文档内容相关的问题
5. 验证 AI 回答基于文档内容

---

阶段 4 完成。AI 对话功能可用，支持选择知识库进行 RAG 问答。

---

# 阶段 5：管理后台（权限 + 统计）

**学习目标：** RBAC 权限模型、数据统计查询、管理界面设计

**验证标准：** 管理员能管理用户、查看用量统计

## Task 5.1: 管理后台 API

**Files:**
- Create: `backend/app/api/admin.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 创建管理后台路由**

```python
# backend/app/api/admin.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.api.deps import get_admin_user
from app.models.user import User
from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document
from app.models.usage_log import UsageLog
from app.models.conversation import Conversation
from app.schemas.user import UserOut

router = APIRouter(prefix="/api/admin", tags=["管理后台"], dependencies=[Depends(get_admin_user)])


# --- 用户管理 ---

@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.put("/users/{user_id}/toggle")
def toggle_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.is_active = not user.is_active
    db.commit()
    return {"id": user.id, "is_active": user.is_active}


@router.put("/users/{user_id}/admin")
def toggle_admin(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.is_admin = not user.is_admin
    db.commit()
    return {"id": user.id, "is_admin": user.is_admin}


# --- 知识库管理 ---

@router.get("/knowledge-bases")
def admin_list_kbs(db: Session = Depends(get_db)):
    kbs = db.query(KnowledgeBase).all()
    result = []
    for kb in kbs:
        doc_count = db.query(Document).filter(Document.kb_id == kb.id).count()
        owner = db.query(User).filter(User.id == kb.owner_id).first()
        result.append({
            "id": kb.id,
            "name": kb.name,
            "description": kb.description,
            "owner": owner.username if owner else "已删除",
            "doc_count": doc_count,
            "created_at": kb.created_at,
        })
    return result


# --- 用量统计 ---

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    user_count = db.query(User).count()
    active_user_count = db.query(User).filter(User.is_active == True).count()
    kb_count = db.query(KnowledgeBase).count()
    doc_count = db.query(Document).count()
    chat_count = db.query(Conversation).count()

    return {
        "user_count": user_count,
        "active_user_count": active_user_count,
        "kb_count": kb_count,
        "doc_count": doc_count,
        "chat_count": chat_count,
    }


@router.get("/usage-logs")
def get_usage_logs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * size
    logs = (
        db.query(UsageLog)
        .order_by(UsageLog.created_at.desc())
        .offset(offset)
        .limit(size)
        .all()
    )
    total = db.query(UsageLog).count()
    result = []
    for log in logs:
        user = db.query(User).filter(User.id == log.user_id).first()
        result.append({
            "id": log.id,
            "user": user.username if user else "已删除",
            "action": log.action,
            "tokens_used": log.tokens_used,
            "created_at": log.created_at,
        })
    return {"total": total, "items": result}
```

- [ ] **Step 2: 注册路由**

```python
# backend/app/main.py — 追加
from app.api.admin import router as admin_router

app.include_router(admin_router)
```

---

## Task 5.2: 管理后台前端 API

**Files:**
- Create: `frontend/src/api/admin.js`

- [ ] **Step 1: 创建管理 API**

```javascript
// frontend/src/api/admin.js
import api from './index'

export function getStats() {
  return api.get('/api/admin/stats')
}

export function getUsers() {
  return api.get('/api/admin/users')
}

export function toggleUser(id) {
  return api.put(`/api/admin/users/${id}/toggle`)
}

export function toggleAdmin(id) {
  return api.put(`/api/admin/users/${id}/admin`)
}

export function getAdminKnowledgeBases() {
  return api.get('/api/admin/knowledge-bases')
}

export function getUsageLogs(params) {
  return api.get('/api/admin/usage-logs', { params })
}
```

---

## Task 5.3: 管理后台页面

**Files:**
- Modify: `frontend/src/views/AdminView.vue`

- [ ] **Step 1: 重写管理后台**

```vue
<!-- frontend/src/views/AdminView.vue -->
<template>
  <a-layout style="height: 100vh">
    <a-layout-header class="header">
      <div class="logo">IntraAI</div>
      <a-menu theme="dark" mode="horizontal" :selected-keys="['admin']">
        <a-menu-item key="chat" @click="$router.push('/')">对话</a-menu-item>
        <a-menu-item key="knowledge" @click="$router.push('/knowledge')">知识库</a-menu-item>
        <a-menu-item key="admin">管理</a-menu-item>
      </a-menu>
      <a-button type="text" style="color: white" @click="handleLogout">退出</a-button>
    </a-layout-header>
    <a-layout>
      <a-layout-sider width="200" theme="light">
        <a-menu mode="inline" v-model:selected-keys="activeTab" style="height: 100%">
          <a-menu-item key="stats">数据概览</a-menu-item>
          <a-menu-item key="users">用户管理</a-menu-item>
          <a-menu-item key="kbs">知识库管理</a-menu-item>
          <a-menu-item key="logs">操作日志</a-menu-item>
        </a-menu>
      </a-layout-sider>
      <a-layout-content style="padding: 24px">
        <!-- 数据概览 -->
        <template v-if="activeTab[0] === 'stats'">
          <a-row :gutter="16">
            <a-col :span="6" v-for="item in statCards" :key="item.title">
              <a-card>
                <a-statistic :title="item.title" :value="item.value" />
              </a-card>
            </a-col>
          </a-row>
        </template>

        <!-- 用户管理 -->
        <template v-if="activeTab[0] === 'users'">
          <a-card title="用户管理">
            <a-table :data-source="users" :columns="userColumns" row-key="id" :loading="loadingUsers">
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'status'">
                  <a-tag :color="record.is_active ? 'green' : 'red'">
                    {{ record.is_active ? '正常' : '禁用' }}
                  </a-tag>
                </template>
                <template v-if="column.key === 'admin'">
                  <a-tag :color="record.is_admin ? 'blue' : 'default'">
                    {{ record.is_admin ? '管理员' : '用户' }}
                  </a-tag>
                </template>
                <template v-if="column.key === 'action'">
                  <a-space>
                    <a-button size="small" @click="handleToggleUser(record)">
                      {{ record.is_active ? '禁用' : '启用' }}
                    </a-button>
                    <a-button size="small" @click="handleToggleAdmin(record)">
                      {{ record.is_admin ? '取消管理员' : '设为管理员' }}
                    </a-button>
                  </a-space>
                </template>
              </template>
            </a-table>
          </a-card>
        </template>

        <!-- 知识库管理 -->
        <template v-if="activeTab[0] === 'kbs'">
          <a-card title="知识库管理">
            <a-table :data-source="adminKbs" :columns="kbColumns" row-key="id" :loading="loadingKbs" />
          </a-card>
        </template>

        <!-- 操作日志 -->
        <template v-if="activeTab[0] === 'logs'">
          <a-card title="操作日志">
            <a-table :data-source="logs" :columns="logColumns" row-key="id" :loading="loadingLogs"
              :pagination="{ current: logPage, total: logTotal, pageSize: 20, onChange: handleLogPageChange }" />
          </a-card>
        </template>
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useAuthStore } from '../stores/auth'
import { getStats, getUsers, toggleUser, toggleAdmin, getAdminKnowledgeBases, getUsageLogs } from '../api/admin'

const router = useRouter()
const authStore = useAuthStore()
const activeTab = ref(['stats'])

// 统计
const stats = ref({})
const statCards = computed(() => [
  { title: '总用户数', value: stats.value.user_count || 0 },
  { title: '活跃用户', value: stats.value.active_user_count || 0 },
  { title: '知识库数', value: stats.value.kb_count || 0 },
  { title: '对话次数', value: stats.value.chat_count || 0 },
])

// 用户
const users = ref([])
const loadingUsers = ref(false)
const userColumns = [
  { title: 'ID', dataIndex: 'id', width: 60 },
  { title: '用户名', dataIndex: 'username' },
  { title: '邮箱', dataIndex: 'email' },
  { title: '状态', key: 'status' },
  { title: '角色', key: 'admin' },
  { title: '注册时间', dataIndex: 'created_at' },
  { title: '操作', key: 'action', width: 250 },
]

// 知识库
const adminKbs = ref([])
const loadingKbs = ref(false)
const kbColumns = [
  { title: 'ID', dataIndex: 'id', width: 60 },
  { title: '名称', dataIndex: 'name' },
  { title: '描述', dataIndex: 'description' },
  { title: '所有者', dataIndex: 'owner' },
  { title: '文档数', dataIndex: 'doc_count' },
  { title: '创建时间', dataIndex: 'created_at' },
]

// 日志
const logs = ref([])
const logTotal = ref(0)
const logPage = ref(1)
const loadingLogs = ref(false)
const logColumns = [
  { title: 'ID', dataIndex: 'id', width: 60 },
  { title: '用户', dataIndex: 'user' },
  { title: '操作', dataIndex: 'action' },
  { title: '时间', dataIndex: 'created_at' },
]

async function fetchStats() {
  const res = await getStats()
  stats.value = res.data
}

async function fetchUsers() {
  loadingUsers.value = true
  try {
    const res = await getUsers()
    users.value = res.data
  } finally {
    loadingUsers.value = false
  }
}

async function fetchKbs() {
  loadingKbs.value = true
  try {
    const res = await getAdminKnowledgeBases()
    adminKbs.value = res.data
  } finally {
    loadingKbs.value = false
  }
}

async function fetchLogs(page = 1) {
  loadingLogs.value = true
  try {
    const res = await getUsageLogs({ page, size: 20 })
    logs.value = res.data.items
    logTotal.value = res.data.total
    logPage.value = page
  } finally {
    loadingLogs.value = false
  }
}

async function handleToggleUser(record) {
  await toggleUser(record.id)
  message.success('操作成功')
  fetchUsers()
}

async function handleToggleAdmin(record) {
  await toggleAdmin(record.id)
  message.success('操作成功')
  fetchUsers()
}

function handleLogPageChange(page) {
  fetchLogs(page)
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

watch(activeTab, ([tab]) => {
  if (tab === 'stats') fetchStats()
  if (tab === 'users') fetchUsers()
  if (tab === 'kbs') fetchKbs()
  if (tab === 'logs') fetchLogs()
})

onMounted(() => {
  authStore.fetchUser()
  fetchStats()
})
</script>

<style scoped>
.header {
  display: flex;
  align-items: center;
}
.logo {
  color: white;
  font-size: 18px;
  font-weight: bold;
  margin-right: 24px;
}
</style>
```

- [ ] **Step 2: 测试管理后台**

1. 用管理员账号登录
2. 进入管理后台
3. 验证四个 Tab：数据概览、用户管理、知识库管理、操作日志
4. 测试启用/禁用用户、设置管理员

---

阶段 5 完成。管理后台功能完整，支持用户管理、知识库管理、用量统计。

---

# 阶段 6：Docker 部署

**学习目标：** Dockerfile 编写、Docker Compose 编排、容器间网络通信

**验证标准：** `docker-compose up` 一键启动整个平台

## Task 6.1: 后端 Dockerfile

**Files:**
- Create: `backend/Dockerfile`

- [ ] **Step 1: 编写后端 Dockerfile**

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Task 6.2: 前端 Dockerfile

**Files:**
- Create: `frontend/Dockerfile`

- [ ] **Step 1: 编写前端 Dockerfile**

```dockerfile
# frontend/Dockerfile
FROM node:18-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

- [ ] **Step 2: 创建 Nginx 配置**

Create: `frontend/nginx.conf`

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

- [ ] **Step 3: 修改前端 API 地址**

在生产环境下，前端 API 的 `baseURL` 应该为空（因为 Nginx 会代理 `/api` 到后端）：

```javascript
// frontend/src/api/index.js — 修改 baseURL
const api = axios.create({
  baseURL: import.meta.env.PROD ? '' : 'http://localhost:8000',
  timeout: 30000,
})
```

---

## Task 6.3: Docker Compose 编排

**Files:**
- Create: `docker-compose.yml`

- [ ] **Step 1: 编写 docker-compose.yml**

```yaml
services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: intraai123
      MYSQL_DATABASE: intraai
      MYSQL_CHARSET: utf8mb4
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      retries: 5

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      MYSQL_HOST: mysql
      MYSQL_PORT: 3306
      MYSQL_USER: root
      MYSQL_PASSWORD: intraai123
      MYSQL_DB: intraai
      SECRET_KEY: change-this-to-a-random-string
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      OPENAI_BASE_URL: ${OPENAI_BASE_URL:-https://api.openai.com/v1}
      OPENAI_MODEL: ${OPENAI_MODEL:-gpt-4o-mini}
      UPLOAD_DIR: /app/uploads
      CHROMA_DIR: /app/chroma_data
    volumes:
      - upload_data:/app/uploads
      - chroma_data:/app/chroma_data
    depends_on:
      mysql:
        condition: service_healthy

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  mysql_data:
  upload_data:
  chroma_data:
```

- [ ] **Step 2: 创建 .env 文件**

在项目根目录创建 `.env`：

```env
OPENAI_API_KEY=sk-your-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

- [ ] **Step 3: 构建并启动**

```bash
cd F:/a
docker-compose up --build
```

等待所有容器启动完成：
- MySQL 在 localhost:3306
- 后端在 localhost:8000（Swagger: localhost:8000/docs）
- 前端在 localhost:80

- [ ] **Step 4: 测试完整流程**

1. 访问 http://localhost
2. 注册第一个用户（自动成为管理员）
3. 创建知识库，上传文档
4. 在对话页提问，验证 RAG 回答
5. 进入管理后台查看统计

---

阶段 6 完成。整个平台可通过 `docker-compose up` 一键部署。

---

## 总览

| 阶段 | 核心产出 | 学习重点 |
|------|---------|---------|
| 1 | FastAPI 后端 API | REST API、ORM、JWT 认证 |
| 2 | Vue 前端界面 | 组件化、路由、状态管理、前后端联调 |
| 3 | 文档解析+向量化 | 文本切片、Embedding、向量检索 |
| 4 | AI 对话+RAG | Prompt Engineering、RAG 流程 |
| 5 | 管理后台 | 权限设计、数据统计 |
| 6 | Docker 部署 | Dockerfile、Compose 编排 |
