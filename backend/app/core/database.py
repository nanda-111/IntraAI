"""
数据库连接模块

使用 SQLAlchemy ORM 管理数据库引擎（Engine）和会话（Session）。

核心概念：
  1. 引擎（Engine）：SQLAlchemy 与数据库之间的桥梁，负责管理数据库连接池和执行 SQL 语句。
     创建引擎时并不会立即建立物理连接，而是在第一次真正执行查询时才会连接数据库。
  2. 会话工厂（SessionLocal）：通过 sessionmaker 创建的工厂函数。
     每次调用 SessionLocal() 就会生成一个独立的数据库会话（Session）对象。
     会话是所有数据库操作的入口，用于添加、查询、更新、删除记录。
  3. 声明式基类（Base）：所有 ORM 模型（数据表对应的 Python 类）都要继承这个基类。
     SQLAlchemy 通过它来追踪所有模型类，进而生成和管理数据库表结构（CREATE TABLE 等）。
  4. 依赖注入（get_db）：FastAPI 的核心机制之一。在路由函数中声明 db: Session = Depends(get_db)，
     FastAPI 会在每次 HTTP 请求时自动调用 get_db 获取数据库会话，请求结束后自动关闭会话，
     无需手动管理数据库连接的打开和关闭。

使用方式：
  from app.core.database import Base, engine, get_db
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings

# ==================== 创建数据库引擎 ====================
# create_engine() 的第一个参数是数据库连接字符串（URL），格式如下：
#   mysql+pymysql://用户名:密码@主机:端口/数据库名
# 其中 "mysql+pymysql" 表示使用 PyMySQL 驱动连接 MySQL 数据库。
#
# echo=True 会在控制台打印所有生成的 SQL 语句，方便开发调试。
# 生产环境建议设置为 False，避免日志过多。
engine = create_engine(settings.DATABASE_URL, echo=True)

# ==================== 创建会话工厂 ====================
# sessionmaker 是一个工厂类，调用它返回的是"会话创建函数"，而非会话本身。
# bind=engine 参数表示所有通过该工厂创建的会话都使用同一个引擎来连接数据库。
# 我们在 get_db() 函数中调用 SessionLocal() 来获取实际的数据库会话。
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    """
    所有 ORM 数据模型的声明式基类。

    什么是声明式基类？
      在 SQLAlchemy 中，每个数据库表都对应一个 Python 类（称为 ORM 模型）。
      这些类必须继承 DeclarativeBase 的子类，SQLAlchemy 才能识别它们为"数据表模型"，
      并通过它们自动生成 CREATE TABLE 等 DDL 语句。

    使用方式：
      from app.core.database import Base

      class User(Base):
          __tablename__ = "users"
          id = Column(Integer, primary_key=True)
          name = Column(String(100))
    """
    pass


def get_db():
    """
    FastAPI 依赖注入函数 — 为每次 HTTP 请求提供数据库会话。

    工作原理：
      FastAPI 的依赖注入系统会在调用路由函数之前，先执行 Depends(get_db) 中的 get_db 函数。
      get_db 是一个生成器函数（使用 yield），它的执行流程如下：

      1. db = SessionLocal()  →  创建一个新的数据库会话
      2. yield db             →  将会话传递给路由函数使用
      3. finally: db.close()  →  路由函数执行完毕后（无论成功还是异常），关闭会话

    使用方式：
      from fastapi import Depends
      from sqlalchemy.orm import Session
      from app.core.database import get_db

      @app.get("/users")
      def list_users(db: Session = Depends(get_db)):
          users = db.query(User).all()
          return users

    为什么用 try/finally？
      确保即使路由函数抛出异常，数据库会话也能被正确关闭，避免连接泄漏。
    """
    # 第一步：从会话工厂创建一个数据库会话实例
    db = SessionLocal()
    try:
        # 第二步：将会话"交给"路由函数使用（yield 会暂停执行，等待路由函数完成）
        yield db
    finally:
        # 第三步：无论路由函数是否成功，都关闭会话，释放数据库连接资源
        db.close()
