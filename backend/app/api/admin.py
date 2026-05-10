"""
管理后台 API（Admin Routes）

本模块提供管理后台的所有接口，包括：
  1. 用户管理：查看用户列表、启用/禁用用户、设置/取消管理员
  2. 知识库管理：查看所有知识库及其文档数量
  3. 用量统计：平台整体统计数据、操作日志分页查询

【路由级别的依赖注入（dependencies=[Depends(get_admin_user)]）】
  在 APIRouter 上通过 dependencies 参数声明的依赖，会作用于该路由组下的**所有接口**。
  与在每个路由函数参数中单独声明 Depends() 不同，路由级别的依赖注入有以下特点：
    1. 该依赖的返回值不会注入到路由函数参数中（因为它不是函数参数级别的声明）。
    2. 它纯粹用于"守卫"（guard）目的——在执行任何路由函数之前先验证权限。
    3. 如果依赖抛出异常（如 HTTPException 403），整个请求立即终止，不会进入路由函数。
  这种方式非常适合"整组接口都需要同一权限"的场景（如管理后台），
  避免了在每个路由函数上重复声明 Depends(get_admin_user)。
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_admin_user
from app.models.user import User
from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document
from app.models.usage_log import UsageLog
from app.models.conversation import Conversation
from app.schemas.user import UserOut

# 管理后台路由 — 所有接口都需要管理员权限
# dependencies=[Depends(get_admin_user)] 表示整个路由组都需要管理员权限
# 任何非管理员用户访问这些接口时，会直接返回 403 Forbidden
router = APIRouter(prefix="/api/admin", tags=["管理后台"], dependencies=[Depends(get_admin_user)])


# ==================== 用户管理 ====================

@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    """获取所有用户列表，按创建时间倒序排列"""
    # 查询所有用户，order_by(User.created_at.desc()) 表示最新注册的用户排在最前面
    return db.query(User).order_by(User.created_at.desc()).all()


@router.put("/users/{user_id}/toggle")
def toggle_user(user_id: int, db: Session = Depends(get_db)):
    """启用/禁用用户（切换 is_active 状态）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    # 取反 is_active：True → False（禁用），False → True（启用）
    user.is_active = not user.is_active
    db.commit()
    return {"id": user.id, "is_active": user.is_active}


@router.put("/users/{user_id}/admin")
def toggle_admin(user_id: int, db: Session = Depends(get_db)):
    """设置/取消管理员（切换 is_admin 状态）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    # 取反 is_admin：True → False（取消管理员），False → True（设为管理员）
    user.is_admin = not user.is_admin
    db.commit()
    return {"id": user.id, "is_admin": user.is_admin}


# ==================== 知识库管理 ====================

@router.get("/knowledge-bases")
def admin_list_kbs(db: Session = Depends(get_db)):
    """
    获取所有知识库（包含所有者用户名和文档数量）

    【为什么手动组装数据而非使用 SQLAlchemy relationship 联表查询？】
      管理后台的知识库列表需要同时展示：
        1. 知识库自身的信息（名称、描述、创建时间）
        2. 所有者的用户名（来自 users 表）
        3. 文档数量（需要对 documents 表做 COUNT 聚合）
      这三个数据分散在三张表中，且 documents 表与 knowledge_bases 表之间
      没有在 ORM 模型中定义 relationship 关系。

      手动组装数据的方案：
        - 先查出所有知识库
        - 遍历每个知识库，分别查询其文档数量和所有者信息
        - 组装成字典列表返回

      注意：这种方式会产生 N+1 查询问题（每个知识库额外执行 2 条 SQL）。
      当知识库数量较少时（管理后台通常不会太多），性能可以接受。
      如果后续知识库数量增大，可以优化为：
        - 使用 SQLAlchemy 的 joinedload/subqueryload 预加载关联数据
        - 或使用原生 SQL 的 JOIN + GROUP BY 一次性查询
    """
    kbs = db.query(KnowledgeBase).all()
    result = []
    for kb in kbs:
        # 查询该知识库下的文档数量
        doc_count = db.query(Document).filter(Document.kb_id == kb.id).count()
        # 查询该知识库的所有者
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


# ==================== 用量统计 ====================

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """获取平台统计数据（用户数、知识库数、文档数、对话数等）"""
    return {
        "user_count": db.query(User).count(),
        "active_user_count": db.query(User).filter(User.is_active == True).count(),
        "kb_count": db.query(KnowledgeBase).count(),
        "doc_count": db.query(Document).count(),
        "chat_count": db.query(Conversation).count(),
    }


@router.get("/usage-logs")
def get_usage_logs(
    page: int = Query(1, ge=1),            # 页码，从 1 开始，最小值为 1
    size: int = Query(20, ge=1, le=100),   # 每页条数，范围 1-100
    db: Session = Depends(get_db),
):
    """
    获取操作日志（分页）

    【分页查询的实现（offset + limit）】
      分页是 Web API 中常见的数据展示方式，核心原理是 SQL 的 OFFSET 和 LIMIT 子句：
        - OFFSET：跳过前 N 条记录（即"前面几页已经展示过的数据"）
        - LIMIT：最多返回 N 条记录（即"当前页要展示的数据"）

      计算公式：
        offset = (page - 1) * size
        例如：page=2, size=20 时，offset = (2-1)*20 = 20，即跳过前 20 条，返回第 21-40 条

      Query 参数说明：
        - Query(1, ge=1)：默认值为 1，ge=1 表示最小值为 1（页码不能小于 1）
        - Query(20, ge=1, le=100)：默认值为 20，范围限制在 1-100 之间，防止客户端请求过大的数据量

      除了返回分页数据外，还返回 total（总记录数），前端需要它来计算总页数并渲染分页控件。
    """
    # 根据页码和每页条数计算偏移量
    offset = (page - 1) * size
    # 查询当前页的数据：按创建时间倒序，跳过 offset 条，取 size 条
    logs = (
        db.query(UsageLog)
        .order_by(UsageLog.created_at.desc())
        .offset(offset)
        .limit(size)
        .all()
    )
    # 查询总记录数，用于前端分页控件
    total = db.query(UsageLog).count()

    # 组装返回数据：为每条日志附上用户名
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
