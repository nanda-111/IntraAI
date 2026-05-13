"""会话管理 API 路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DbSession
from sqlalchemy import desc

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.session import Session
from app.models.conversation import Conversation
from app.schemas.session import SessionOut, SessionDetail, ConversationItem

router = APIRouter(prefix="/api/sessions", tags=["会话"])


@router.post("/", response_model=SessionOut)
def create_session(
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """新建会话"""
    session = Session(user_id=current_user.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/", response_model=list[SessionOut])
def list_sessions(
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户所有会话（按更新时间倒序）"""
    return (
        db.query(Session)
        .filter(Session.user_id == current_user.id)
        .order_by(desc(Session.updated_at))
        .all()
    )


@router.get("/{session_id}", response_model=SessionDetail)
def get_session(
    session_id: int,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取会话详情（含对话记录）"""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问")

    conversations = (
        db.query(Conversation)
        .filter(Conversation.session_id == session_id)
        .order_by(Conversation.created_at.asc())
        .all()
    )

    return SessionDetail(
        id=session.id,
        title=session.title,
        summary=session.summary,
        created_at=session.created_at,
        updated_at=session.updated_at,
        conversations=[
            ConversationItem(
                id=c.id,
                question=c.question,
                answer=c.answer,
                created_at=c.created_at,
            )
            for c in conversations
        ],
    )


@router.delete("/{session_id}")
def delete_session(
    session_id: int,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除会话及其下所有对话记录"""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除")

    db.query(Conversation).filter(Conversation.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return {"message": "已删除"}
