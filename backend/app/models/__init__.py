"""
数据模型包初始化模块

本模块导入所有数据模型，确保 SQLAlchemy 的 Base.metadata 能够收集到所有表定义。

为什么需要导入所有模型？
  SQLAlchemy 通过 Base 的元数据（Base.metadata）来追踪所有继承了 Base 的模型类。
  但只有当模型类被 Python 解释器实际导入（import）后，它才会被注册到 Base.metadata 中。
  如果某个模型存在但从未被导入，SQLAlchemy 就不知道这张表的存在，
  导致 Base.metadata.create_all() 不会为它创建表。

因此，在应用启动时，必须通过本模块统一导入所有模型，
然后在 main.py 中执行 import app.models，确保所有模型都被加载。

添加新模型的步骤：
  1. 在 app/models/ 目录下创建新的模型文件（如 role.py）
  2. 在本文件中添加对应的导入语句（如 from app.models.role import Role）
  3. 这样 main.py 中的 import app.models 就会自动加载新模型
"""

from app.models.conversation import Conversation as Conversation
from app.models.document import Document as Document
from app.models.knowledge_base import KnowledgeBase as KnowledgeBase
from app.models.session import Session as Session
from app.models.usage_log import UsageLog as UsageLog
from app.models.user import User as User
