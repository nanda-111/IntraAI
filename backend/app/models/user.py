"""
用户数据模型（User ORM Model）

本模块定义了 User 类，对应数据库中的 users 表。
SQLAlchemy 通过声明式映射（Declarative Mapping）将 Python 类与数据库表关联起来。

核心概念：
  - __tablename__：告诉 SQLAlchemy 这个类对应数据库中的哪张表。
    命名约定：表名使用小写复数形式（如 users、orders），单词之间用下划线分隔。
  - Column：定义表中的每一列（字段），包括字段类型、约束、默认值等。
  - Base：所有 ORM 模型必须继承的基类，由 app.core.database 提供。
    SQLAlchemy 通过 Base.metadata 收集所有继承了 Base 的子类，从而知道有哪些表需要管理。
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class User(Base):
    """
    用户表（users）的 ORM 模型

    对应数据库中的 users 表，存储系统用户的基本信息。
    """

    # ==================== 表名定义 ====================
    # __tablename__ 是 SQLAlchemy 的特殊属性，用于指定该模型对应的数据库表名。
    # 约定：使用小写字母 + 下划线命名法（snake_case），使用复数形式。
    # 例如：User 类 -> users 表，UserRole 类 -> user_roles 表。
    __tablename__ = "users"

    # ==================== 字段定义 ====================

    # 主键字段（Primary Key）
    # primary_key=True：将该字段设为表的主键，数据库会自动为其创建唯一索引。
    #   主键的作用是唯一标识表中的每一行记录，类似于身份证号。
    # autoincrement=True：启用自增，每次插入新记录时数据库自动分配一个递增的整数值。
    #   这样就不需要手动指定 id，由数据库保证 id 的唯一性。
    # 类型 Integer：对应数据库中的 INT 类型，范围约 -21 亿到 +21 亿。
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 用户名字段
    # String(50)：最大长度为 50 个字符的变长字符串，对应数据库中的 VARCHAR(50)。
    # unique=True：在该列上创建唯一约束（UNIQUE INDEX），确保不会有两条记录的 username 相同。
    #   数据库会自动为该列创建唯一索引，重复插入相同用户名会报 IntegrityError。
    # nullable=False：该字段不允许为 NULL，即必填字段。
    #   等同于数据库中的 NOT NULL 约束。如果不设置此值，SQLAlchemy 默认 nullable=True（可为空）。
    # index=True：为该列创建普通索引（INDEX），加速按用户名查询的速度。
    #   与 unique 索引不同，普通索引允许重复值，但查询效率更高。
    #   建议为经常出现在 WHERE 子句中的字段创建索引。
    username = Column(String(50), unique=True, nullable=False, index=True)

    # 邮箱字段
    # String(100)：邮箱最大长度设为 100 字符，覆盖绝大多数邮箱地址长度。
    # unique=True：邮箱也需要唯一，一个邮箱只能注册一个账号。
    # nullable=False：邮箱为必填项。
    email = Column(String(100), unique=True, nullable=False)

    # 哈希密码字段
    # String(255)：哈希后的密码长度可能较长（如 bcrypt 生成的哈希值约 60 字符），
    #   预留 255 字符以应对不同哈希算法。
    # nullable=False：密码为必填项。
    # 注意：这里存储的是经过哈希处理的密码（如 bcrypt.hash(password)），绝不能存储明文密码！
    hashed_password = Column(String(255), nullable=False)

    # 是否为管理员
    # Boolean：对应数据库中的 TINYINT(1)（MySQL）或 BOOLEAN（PostgreSQL）。
    # default=False：插入新记录时，如果没有显式指定该字段的值，默认为 False（普通用户）。
    #   default 是 Python 层面的默认值，SQLAlchemy 在生成 INSERT 语句时会自动填充。
    is_admin = Column(Boolean, default=False)

    # 是否激活（账号状态）
    # default=True：新注册的用户默认处于激活状态。
    # 实际业务中，可以通过将 is_active 设为 False 来"软删除"或"禁用"用户，
    # 而不是直接从数据库中删除记录（软删除是一种常见的数据保留策略）。
    is_active = Column(Boolean, default=True)

    # 创建时间
    # DateTime：对应数据库中的 DATETIME 类型。
    # server_default=func.now()：设置数据库层面的默认值。
    #   func.now() 是 SQLAlchemy 的 SQL 函数封装，会被翻译为数据库的 NOW() 函数。
    #   与 Python 层面的 default=datetime.now 的区别：
    #     - server_default：由数据库服务器在插入记录时自动填充时间，即使绕过 ORM 直接操作 SQL 也能生效。
    #     - default（Python 层面）：由 SQLAlchemy 在生成 INSERT 语句时填充，使用应用服务器的系统时间。
    #   使用 server_default 更可靠，因为它不依赖应用服务器的时区设置。
    created_at = Column(DateTime, server_default=func.now())

    # 更新时间
    # server_default=func.now()：新记录插入时，updated_at 的初始值与 created_at 相同。
    # onupdate=func.now()：当记录被更新（UPDATE）时，SQLAlchemy 会自动将该字段刷新为当前时间。
    #   onupdate 是 SQLAlchemy 特有的机制，它在 ORM 层面工作：
    #   当你修改了模型实例的属性并调用 session.commit() 时，SQLAlchemy 会在 UPDATE 语句中
    #   自动包含 updated_at = NOW()，无需手动设置。
    #   注意：onupdate 只在通过 ORM 更新时生效，直接执行 SQL UPDATE 不会触发。
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
