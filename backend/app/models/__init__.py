"""导入所有 ORM 模型，确保 Base.metadata 能收集到所有表定义。"""

from app.models.conversation import Conversation as Conversation
from app.models.document import Document as Document
from app.models.knowledge_base import KnowledgeBase as KnowledgeBase
from app.models.session import Session as Session
from app.models.usage_log import UsageLog as UsageLog
from app.models.user import User as User
