"""对话 API 集成测试

覆盖端点和内部函数：
  1. POST /api/chat/      — 普通对话
  2. POST /api/chat/stream — 流式对话
  3. _load_session_history — 加载会话历史
  4. _maybe_compress       — 摘要压缩
"""

import json
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest


# ============================================================
# POST /api/chat/
# ============================================================
class TestChatEndpoint:
    """POST /api/chat/ 测试"""

    @patch("app.api.chat.chat_completion")
    def test_chat_basic(self, mock_chat, client, user_headers, db_session):
        """基本对话：不带 session，不带 kb"""
        mock_chat.return_value = ("", "测试回答")

        res = client.post(
            "/api/chat/",
            json={"question": "你好"},
            headers=user_headers,
        )

        assert res.status_code == 200
        data = res.json()
        assert data["answer"] == "测试回答"
        assert data["kb_id"] is None

    @patch("app.api.chat.ask_with_rag")
    def test_chat_with_kb(self, mock_rag, client, user_headers, db_session):
        """带知识库的对话"""
        from app.models.knowledge_base import KnowledgeBase

        kb = KnowledgeBase(name="测试知识库", description="测试", owner_id=1)
        db_session.add(kb)
        db_session.commit()
        db_session.refresh(kb)

        mock_rag.return_value = "RAG 回答"

        res = client.post(
            "/api/chat/",
            json={"question": "问题", "kb_id": kb.id},
            headers=user_headers,
        )

        assert res.status_code == 200
        assert res.json()["answer"] == "RAG 回答"
        mock_rag.assert_called_once()

    @patch("app.api.chat.chat_completion")
    def test_chat_with_session(self, mock_chat, client, user_headers, db_session):
        """带会话的对话：会话存在，加载历史"""
        from app.models.session import Session

        mock_chat.return_value = ("", "回答")

        session = Session(user_id=1, title="新对话")
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        res = client.post(
            "/api/chat/",
            json={"question": "你好", "session_id": session.id},
            headers=user_headers,
        )

        assert res.status_code == 200
        assert res.json()["answer"] == "回答"

    @patch("app.api.chat.generate_title")
    @patch("app.api.chat.chat_completion")
    def test_chat_session_title_generation(
        self, mock_chat, mock_title, client, user_headers, db_session
    ):
        """会话标题为'新对话'时自动生成标题"""
        from app.models.session import Session

        mock_chat.return_value = ("", "回答内容")
        mock_title.return_value = "自动生成的标题"

        session = Session(user_id=1, title="新对话")
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        res = client.post(
            "/api/chat/",
            json={"question": "你好", "session_id": session.id},
            headers=user_headers,
        )

        assert res.status_code == 200
        mock_title.assert_called_once()

    def test_chat_agent_mode(self, client, user_headers):
        """Agent 模式对话"""
        mock_agent_module = MagicMock()
        mock_agent_module.run_agent.return_value = "Agent 回答"
        sys.modules["app.services.langchain_agent"] = mock_agent_module
        try:
            res = client.post(
                "/api/chat/",
                json={"question": "问题", "mode": "agent"},
                headers=user_headers,
            )
            assert res.status_code == 200
            assert res.json()["answer"] == "Agent 回答"
            mock_agent_module.run_agent.assert_called_once_with("问题", None)
        finally:
            del sys.modules["app.services.langchain_agent"]

    def test_chat_agent_with_session(self, client, user_headers, db_session):
        """Agent 模式 + 会话历史"""
        from app.models.conversation import Conversation
        from app.models.session import Session

        mock_agent_module = MagicMock()
        mock_agent_module.run_agent.return_value = "Agent 历史回答"
        sys.modules["app.services.langchain_agent"] = mock_agent_module
        try:
            session = Session(user_id=1, title="测试")
            db_session.add(session)
            db_session.commit()
            db_session.refresh(session)

            conv = Conversation(
                user_id=1,
                session_id=session.id,
                question="之前的问题",
                answer="之前的回答",
            )
            db_session.add(conv)
            db_session.commit()

            res = client.post(
                "/api/chat/",
                json={
                    "question": "后续问题",
                    "mode": "agent",
                    "session_id": session.id,
                },
                headers=user_headers,
            )

            assert res.status_code == 200
            assert res.json()["answer"] == "Agent 历史回答"
            # 验证 history 被传入（1 轮 -> 2 条消息）
            call_args = mock_agent_module.run_agent.call_args
            assert call_args[0][0] == "后续问题"
            assert call_args[0][1] is not None
            assert len(call_args[0][1]) == 2
        finally:
            del sys.modules["app.services.langchain_agent"]

    def test_chat_no_auth(self, client):
        """未认证请求被拒绝"""
        res = client.post("/api/chat/", json={"question": "你好"})
        assert res.status_code == 401

    @patch("app.api.chat.chat_completion")
    def test_chat_creates_conversation_record(
        self, mock_chat, client, user_headers, db_session
    ):
        """对话后正确创建 conversation 记录"""
        from app.models.conversation import Conversation

        mock_chat.return_value = ("", "记录测试回答")

        res = client.post(
            "/api/chat/",
            json={"question": "记录测试"},
            headers=user_headers,
        )

        assert res.status_code == 200

        conv = db_session.query(Conversation).filter(
            Conversation.question == "记录测试"
        ).first()
        assert conv is not None
        assert conv.answer == "记录测试回答"


# ============================================================
# POST /api/chat/stream
# ============================================================
def _parse_sse(text: str) -> list[dict]:
    """解析 SSE 响应体，提取 data: 行中的 JSON 对象"""
    chunks = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if line.startswith("data: ") and line != "data: [DONE]":
            payload = line[len("data: "):]
            chunks.append(json.loads(payload))
    return chunks


class TestChatStreamEndpoint:
    """POST /api/chat/stream 测试"""

    @patch("app.services.llm.chat_completion_stream")
    def test_chat_stream_basic(self, mock_stream, client, user_headers):
        """基本流式对话"""
        mock_stream.return_value = iter(
            [
                {"type": "answer", "content": "你好"},
                {"type": "answer", "content": "世界"},
            ]
        )

        res = client.post(
            "/api/chat/stream",
            json={"question": "你好"},
            headers=user_headers,
        )

        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]

        # 解析 SSE 数据
        chunks = _parse_sse(res.text)
        contents = [c["content"] for c in chunks]
        assert "你好" in contents
        assert "世界" in contents
        assert "[DONE]" in res.text

    @patch("app.api.chat.generate_title")
    @patch("app.services.llm.chat_completion_stream")
    def test_chat_stream_with_session(
        self, mock_stream, mock_title, client, user_headers, db_session
    ):
        """流式对话带会话"""
        from app.models.session import Session

        mock_stream.return_value = iter(
            [{"type": "answer", "content": "流式回答"}]
        )
        mock_title.return_value = "标题"

        session = Session(user_id=1, title="流式测试")
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        res = client.post(
            "/api/chat/stream",
            json={"question": "你好", "session_id": session.id},
            headers=user_headers,
        )

        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]
        chunks = _parse_sse(res.text)
        contents = [c["content"] for c in chunks]
        assert "流式回答" in contents

    @patch("app.services.rag.ask_with_rag_stream")
    def test_chat_stream_with_kb(self, mock_rag_stream, client, user_headers, db_session):
        """流式对话带知识库"""
        from app.models.knowledge_base import KnowledgeBase

        kb = KnowledgeBase(name="流式知识库", description="测试", owner_id=1)
        db_session.add(kb)
        db_session.commit()
        db_session.refresh(kb)

        mock_rag_stream.return_value = iter(
            [{"type": "answer", "content": "RAG流式"}]
        )

        res = client.post(
            "/api/chat/stream",
            json={"question": "问题", "kb_id": kb.id},
            headers=user_headers,
        )

        assert res.status_code == 200
        chunks = _parse_sse(res.text)
        contents = [c["content"] for c in chunks]
        assert "RAG流式" in contents

    def test_chat_stream_no_auth(self, client):
        """流式对话未认证被拒绝"""
        res = client.post("/api/chat/stream", json={"question": "你好"})
        assert res.status_code == 401


# ============================================================
# _load_session_history
# ============================================================
class TestLoadSessionHistory:
    """_load_session_history 函数测试"""

    def test_load_existing_session_empty(self, db_session):
        """加载存在但无对话的会话"""
        from app.api.chat import _load_session_history
        from app.models.session import Session

        session = Session(user_id=1, title="测试会话")
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        loaded_session, summary, history = _load_session_history(
            session.id, db_session
        )

        assert loaded_session.id == session.id
        assert summary is None
        assert history is None

    def test_load_session_with_conversations(self, db_session):
        """加载有历史对话的会话"""
        from app.api.chat import _load_session_history
        from app.models.conversation import Conversation
        from app.models.session import Session

        session = Session(user_id=1, title="历史会话")
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        # 创建 3 条对话，使用不同的 created_at 保证排序确定性
        base_time = datetime(2026, 1, 1, 12, 0, 0)
        for i in range(3):
            conv = Conversation(
                user_id=1,
                session_id=session.id,
                question=f"问题{i}",
                answer=f"回答{i}",
                created_at=base_time + timedelta(minutes=i),
            )
            db_session.add(conv)
        db_session.commit()

        loaded_session, summary, history = _load_session_history(
            session.id, db_session
        )

        assert loaded_session.id == session.id
        assert summary is None
        assert history is not None
        assert len(history) == 6  # 3 条对话 -> 6 条消息（user+assistant）
        # 按时间正序：最早的在前
        assert history[0] == {"role": "user", "content": "问题0"}
        assert history[1] == {"role": "assistant", "content": "回答0"}
        assert history[4] == {"role": "user", "content": "问题2"}
        assert history[5] == {"role": "assistant", "content": "回答2"}

    def test_load_session_with_summary(self, db_session):
        """加载有摘要的会话"""
        from app.api.chat import _load_session_history
        from app.models.session import Session

        session = Session(user_id=1, title="摘要会话", summary="之前的摘要")
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        loaded_session, summary, history = _load_session_history(
            session.id, db_session
        )

        assert loaded_session.id == session.id
        assert summary == "之前的摘要"
        assert history is None

    def test_load_session_max_5_rounds(self, db_session):
        """历史对话最多取最近 5 轮"""
        from app.api.chat import _load_session_history
        from app.models.conversation import Conversation
        from app.models.session import Session

        session = Session(user_id=1, title="长会话")
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        # 创建 8 条对话，使用不同时间戳保证排序确定性
        base_time = datetime(2026, 1, 1, 12, 0, 0)
        for i in range(8):
            conv = Conversation(
                user_id=1,
                session_id=session.id,
                question=f"问题{i}",
                answer=f"回答{i}",
                created_at=base_time + timedelta(minutes=i),
            )
            db_session.add(conv)
        db_session.commit()

        _, _, history = _load_session_history(session.id, db_session)

        # 应该只取最近 5 轮 -> 10 条消息
        assert history is not None
        assert len(history) == 10
        # 最早的 3 轮（0,1,2）被截断，第 4 轮（3）起保留
        assert history[0] == {"role": "user", "content": "问题3"}
        assert history[-1] == {"role": "assistant", "content": "回答7"}

    def test_load_nonexistent_session(self, db_session):
        """加载不存在的会话抛 404"""
        from fastapi import HTTPException

        from app.api.chat import _load_session_history

        with pytest.raises(HTTPException) as exc_info:
            _load_session_history(999, db_session)

        assert exc_info.value.status_code == 404


# ============================================================
# _maybe_compress
# ============================================================
class TestMaybeCompress:
    """_maybe_compress 函数测试"""

    @patch("app.api.chat.generate_summary")
    def test_compress_at_20_conversations(self, mock_summary, db_session):
        """对话数量达到 20 时触发压缩"""
        from app.api.chat import _maybe_compress
        from app.models.conversation import Conversation
        from app.models.session import Session

        mock_summary.return_value = "对话摘要"

        session = Session(user_id=1, title="测试")
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        # 创建 20 条对话
        for i in range(20):
            conv = Conversation(
                user_id=1,
                session_id=session.id,
                question=f"问题{i}",
                answer=f"回答{i}",
            )
            db_session.add(conv)
        db_session.commit()

        _maybe_compress(session.id, db_session)

        # 验证：前 15 条被删除，剩余 5 条
        remaining = (
            db_session.query(Conversation)
            .filter(Conversation.session_id == session.id)
            .count()
        )
        assert remaining == 5

        # 验证摘要被保存
        db_session.refresh(session)
        assert session.summary == "对话摘要"

        # 验证 generate_summary 被调用，参数为前 15 轮对话
        mock_summary.assert_called_once()
        call_args = mock_summary.call_args[0][0]
        assert len(call_args) == 30  # 15 轮 -> 30 条消息

    @patch("app.api.chat.generate_summary")
    def test_compress_over_20_conversations(self, mock_summary, db_session):
        """对话数量超过 20 时也触发压缩"""
        from app.api.chat import _maybe_compress
        from app.models.conversation import Conversation
        from app.models.session import Session

        mock_summary.return_value = "摘要"

        session = Session(user_id=1, title="测试")
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        # 创建 25 条对话
        for i in range(25):
            conv = Conversation(
                user_id=1,
                session_id=session.id,
                question=f"问题{i}",
                answer=f"回答{i}",
            )
            db_session.add(conv)
        db_session.commit()

        _maybe_compress(session.id, db_session)

        remaining = (
            db_session.query(Conversation)
            .filter(Conversation.session_id == session.id)
            .count()
        )
        # 25 - 15 = 10
        assert remaining == 10

    def test_no_compress_below_20(self, db_session):
        """对话数量不足 20 时不压缩"""
        from app.api.chat import _maybe_compress
        from app.models.conversation import Conversation
        from app.models.session import Session

        session = Session(user_id=1, title="测试")
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        # 创建 5 条对话
        for i in range(5):
            conv = Conversation(
                user_id=1,
                session_id=session.id,
                question=f"问题{i}",
                answer=f"回答{i}",
            )
            db_session.add(conv)
        db_session.commit()

        _maybe_compress(session.id, db_session)

        remaining = (
            db_session.query(Conversation)
            .filter(Conversation.session_id == session.id)
            .count()
        )
        assert remaining == 5

    @patch("app.api.chat.generate_summary")
    def test_compress_appends_to_existing_summary(
        self, mock_summary, db_session
    ):
        """已有摘要时，新摘要追加到旧摘要后面"""
        from app.api.chat import _maybe_compress
        from app.models.conversation import Conversation
        from app.models.session import Session

        mock_summary.return_value = "新摘要"

        session = Session(user_id=1, title="测试", summary="旧摘要")
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        for i in range(20):
            conv = Conversation(
                user_id=1,
                session_id=session.id,
                question=f"问题{i}",
                answer=f"回答{i}",
            )
            db_session.add(conv)
        db_session.commit()

        _maybe_compress(session.id, db_session)

        db_session.refresh(session)
        assert "旧摘要" in session.summary
        assert "新摘要" in session.summary
        assert "---" in session.summary

    def test_compress_empty_session(self, db_session):
        """无对话的会话不触发压缩"""
        from app.api.chat import _maybe_compress
        from app.models.session import Session

        session = Session(user_id=1, title="空会话")
        db_session.add(session)
        db_session.commit()

        # 不应抛异常
        _maybe_compress(session.id, db_session)

    @patch("app.api.chat.generate_summary")
    def test_compress_verify_deleted_conversations_are_oldest(
        self, mock_summary, db_session
    ):
        """验证被删除的是最早的 15 条对话"""
        from app.api.chat import _maybe_compress
        from app.models.conversation import Conversation
        from app.models.session import Session

        mock_summary.return_value = "摘要"

        session = Session(user_id=1, title="测试")
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        # 使用显式时间戳保证 _maybe_compress 中 ORDER BY created_at 的确定性
        base_time = datetime(2026, 1, 1, 12, 0, 0)
        for i in range(20):
            conv = Conversation(
                user_id=1,
                session_id=session.id,
                question=f"问题{i}",
                answer=f"回答{i}",
                created_at=base_time + timedelta(minutes=i),
            )
            db_session.add(conv)
        db_session.commit()

        _maybe_compress(session.id, db_session)

        remaining = (
            db_session.query(Conversation)
            .filter(Conversation.session_id == session.id)
            .all()
        )
        remaining_questions = {c.question for c in remaining}
        # 最早的 15 条（问题0-14）被删除，保留问题15-19
        for i in range(15):
            assert f"问题{i}" not in remaining_questions
        for i in range(15, 20):
            assert f"问题{i}" in remaining_questions
