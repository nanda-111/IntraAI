"""管理后台 API，所有接口需要管理员权限。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_admin_user
from app.core.database import get_db
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.models.usage_log import UsageLog
from app.models.user import User
from app.schemas.user import UserOut

router = APIRouter(prefix="/api/admin", tags=["管理后台"], dependencies=[Depends(get_admin_user)])


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    """获取所有用户列表，按创建时间倒序排列"""
    return db.query(User).order_by(User.created_at.desc()).all()


@router.put("/users/{user_id}/toggle")
def toggle_user(user_id: int, db: Session = Depends(get_db)):
    """启用/禁用用户（切换 is_active 状态）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.is_active = not user.is_active
    db.commit()
    return {"id": user.id, "is_active": user.is_active}


@router.put("/users/{user_id}/admin")
def toggle_admin(user_id: int, db: Session = Depends(get_db)):
    """设置/取消管理员（切换 is_admin 状态）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.is_admin = not user.is_admin
    db.commit()
    return {"id": user.id, "is_admin": user.is_admin}


@router.get("/knowledge-bases")
def admin_list_kbs(db: Session = Depends(get_db)):
    """获取所有知识库（包含所有者用户名和文档数量）。"""
    kbs = db.query(KnowledgeBase).all()
    result = []
    for kb in kbs:
        doc_count = db.query(Document).filter(Document.kb_id == kb.id).count()
        owner = db.query(User).filter(User.id == kb.owner_id).first()
        result.append(
            {
                "id": kb.id,
                "name": kb.name,
                "description": kb.description,
                "owner": owner.username if owner else "已删除",
                "doc_count": doc_count,
                "created_at": kb.created_at,
            }
        )
    return result


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """获取平台统计数据（用户数、知识库数、文档数、对话数等）"""
    return {
        "user_count": db.query(User).count(),
        "active_user_count": db.query(User).filter(User.is_active.is_(True)).count(),
        "kb_count": db.query(KnowledgeBase).count(),
        "doc_count": db.query(Document).count(),
        "chat_count": db.query(Conversation).count(),
    }


@router.get("/usage-logs")
def get_usage_logs(
    page: int = Query(1, ge=1),  # 页码，从 1 开始，最小值为 1
    size: int = Query(20, ge=1, le=100),  # 每页条数，范围 1-100
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
    logs = db.query(UsageLog).order_by(UsageLog.created_at.desc()).offset(offset).limit(size).all()
    # 查询总记录数，用于前端分页控件
    total = db.query(UsageLog).count()

    # 组装返回数据：为每条日志附上用户名
    result = []
    for log in logs:
        user = db.query(User).filter(User.id == log.user_id).first()
        result.append(
            {
                "id": log.id,
                "user": user.username if user else "已删除",
                "action": log.action,
                "tokens_used": log.tokens_used,
                "created_at": log.created_at,
            }
        )
    return {"total": total, "items": result}
