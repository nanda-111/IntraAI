"""
对话 API 路由模块

提供两种对话接口：
  1. 普通对话（POST /api/chat/）     — 一次性返回完整回答
  2. 流式对话（POST /api/chat/stream）— 通过 SSE 协议逐字/逐段返回回答

支持多轮对话上下文维护（通过 session_id）。
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import asc
from sqlalchemy import func as sql_func
from sqlalchemy.orm import Session as DbSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.conversation import Conversation
from app.models.session import Session
from app.models.usage_log import UsageLog
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.llm import chat_completion, generate_summary, generate_title
from app.services.rag import ask_with_rag

router = APIRouter(prefix="/api/chat", tags=["对话"])


def _load_session_history(session_id: int, db: DbSession):
    """加载会话的历史上下文和摘要"""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    summary = session.summary

    # 获取最近 5 轮对话作为历史上下文
    recent_convs = (
        db.query(Conversation)
        .filter(Conversation.session_id == session_id)
        .order_by(Conversation.created_at.desc())
        .limit(5)
        .all()
    )
    recent_convs = list(reversed(recent_convs))

    history = None
    if recent_convs:
        history = []
        for conv in recent_convs:
            history.append({"role": "user", "content": conv.question})
            history.append({"role": "assistant", "content": conv.answer})

    return session, summary, history


def _save_conversation(data: ChatRequest, answer: str, user: User, db: DbSession):
    """保存对话记录和用量日志"""
    conv = Conversation(
        user_id=user.id,
        kb_id=data.kb_id,
        session_id=data.session_id,
        question=data.question,
        answer=answer,
    )
    db.add(conv)
    log = UsageLog(user_id=user.id, action="chat")
    db.add(log)
    db.commit()


def _post_chat(session: Session | None, data: ChatRequest, answer: str, db: DbSession):
    """对话后的处理：更新会话时间、生成标题、触发摘要压缩"""
    if not session:
        return

    session.updated_at = sql_func.now()
    db.commit()

    # 标题生成：如果是会话的第一条消息且标题还是"新对话"
    if session.title == "新对话":
        title = generate_title(data.question, answer)
        session.title = title
        db.commit()

    # 摘要压缩：检查对话数量是否达到 20
    _maybe_compress(session.id, db)


def _maybe_compress(session_id: int, db: DbSession):
    """检查会话对话数量，超过 20 轮时触发摘要压缩"""
    conv_count = db.query(Conversation).filter(Conversation.session_id == session_id).count()

    if conv_count < 20:
        return

    # 取前 15 轮对话
    old_convs = (
        db.query(Conversation)
        .filter(Conversation.session_id == session_id)
        .order_by(asc(Conversation.created_at))
        .limit(15)
        .all()
    )

    # 构造对话列表用于生成摘要
    conversations = []
    for conv in old_convs:
        conversations.append({"role": "user", "content": conv.question})
        conversations.append({"role": "assistant", "content": conv.answer})

    new_summary = generate_summary(conversations)

    # 获取会话，拼接已有摘要
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        return

    if session.summary:
        combined = f"{session.summary}\n\n---\n\n{new_summary}"
    else:
        combined = new_summary

    session.summary = combined

    # 删除这 15 轮对话记录
    for conv in old_convs:
        db.delete(conv)

    db.commit()


@router.post("/", response_model=ChatResponse)
def chat(
    data: ChatRequest,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """普通对话接口（支持多轮上下文）"""
    session = None
    summary = None
    history = None

    if data.session_id:
        session, summary, history = _load_session_history(data.session_id, db)

    # Agent 模式
    if data.mode == "agent":
        from app.services.langchain_agent import run_agent as agent_run

        answer = agent_run(data.question, history, kb_id=data.kb_id or 1)
    elif data.kb_id:
        answer = ask_with_rag(data.question, data.kb_id, history=history, summary=summary)
    elif history or summary:
        messages = []
        if summary:
            messages.append({"role": "system", "content": f"以下是对之前对话的摘要：\n{summary}"})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": data.question})
        _, answer = chat_completion(messages)
    else:
        _, answer = chat_completion([{"role": "user", "content": data.question}])

    _save_conversation(data, answer, current_user, db)
    _post_chat(session, data, answer, db)

    return ChatResponse(answer=answer, kb_id=data.kb_id)


@router.post("/stream")
def chat_stream(
    data: ChatRequest,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """流式对话接口（支持多轮上下文）"""

    def generate():
        session = None
        summary = None
        history = None

        try:
            if data.session_id:
                session, summary, history = _load_session_history(data.session_id, db)

            full_answer = ""

            if data.mode == "agent":
                # Agent 流式模式
                import asyncio

                from app.services.langchain_agent import run_agent_stream as agent_stream

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    agen = agent_stream(data.question, history, kb_id=data.kb_id or 1)
                    while True:
                        try:
                            chunk = loop.run_until_complete(agen.__anext__())
                            full_answer += chunk["content"]
                            yield f"data: {json.dumps(chunk)}\n\n"
                        except StopAsyncIteration:
                            break
                finally:
                    loop.close()
            elif data.kb_id:
                from app.services.rag import ask_with_rag_stream

                for chunk in ask_with_rag_stream(
                    data.question, data.kb_id, history=history, summary=summary
                ):
                    full_answer += chunk["content"]
                    yield f"data: {json.dumps(chunk)}\n\n"
            elif history or summary:
                from app.services.llm import chat_completion_stream as llm_stream

                messages = []
                if summary:
                    messages.append(
                        {"role": "system", "content": f"以下是对之前对话的摘要：\n{summary}"}
                    )
                if history:
                    messages.extend(history)
                messages.append({"role": "user", "content": data.question})
                for chunk in llm_stream(messages):
                    full_answer += chunk["content"]
                    yield f"data: {json.dumps(chunk)}\n\n"
            else:
                from app.services.llm import chat_completion_stream as llm_stream

                for chunk in llm_stream([{"role": "user", "content": data.question}]):
                    full_answer += chunk["content"]
                    yield f"data: {json.dumps(chunk)}\n\n"

            yield "data: [DONE]\n\n"

            try:
                if full_answer:
                    _save_conversation(data, full_answer, current_user, db)
                    _post_chat(session, data, full_answer, db)
            except Exception:
                pass
        except Exception:
            yield "data: [ERROR]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
