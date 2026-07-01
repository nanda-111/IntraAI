"""RAG 服务模块测试"""

from unittest.mock import patch

import pytest


class TestBuildContext:
    """_build_context 函数测试"""

    def test_build_context_with_results(self):
        """测试有检索结果时构建上下文"""
        from app.services.rag import _build_context

        results = [
            ("文档内容1", {"source": "doc1.pdf"}, 0.95),
            ("文档内容2", {"source": "doc2.pdf"}, 0.85),
        ]

        context = _build_context(results)

        assert "文档内容1" in context
        assert "文档内容2" in context
        assert "[片段1 - 来源: doc1.pdf]" in context
        assert "[片段2 - 来源: doc2.pdf]" in context

    def test_build_context_empty_results(self):
        """测试无检索结果时返回默认文本"""
        from app.services.rag import _build_context

        context = _build_context([])

        assert context == "（无相关资料）"

    def test_build_context_no_source(self):
        """测试没有来源信息的情况"""
        from app.services.rag import _build_context

        results = [("文档内容", {}, 0.8)]

        context = _build_context(results)

        assert "文档内容" in context
        assert "[来源:" not in context

    def test_build_context_multiple_results_separator(self):
        """测试多个结果之间用分隔符连接"""
        from app.services.rag import _build_context

        results = [
            ("内容A", {"source": "a.pdf"}, 0.9),
            ("内容B", {"source": "b.pdf"}, 0.8),
        ]

        context = _build_context(results)

        assert "---" in context

    def test_build_context_single_result(self):
        """测试单个检索结果"""
        from app.services.rag import _build_context

        results = [("单条文档", {"source": "single.pdf"}, 0.9)]

        context = _build_context(results)

        assert context == "[片段1 - 来源: single.pdf]\n单条文档"

    def test_build_context_mixed_source_presence(self):
        """测试混合有来源和无来源的结果"""
        from app.services.rag import _build_context

        results = [
            ("有来源的内容", {"source": "doc.pdf"}, 0.9),
            ("无来源的内容", {}, 0.7),
        ]

        context = _build_context(results)

        assert "[片段1 - 来源: doc.pdf]" in context
        assert "有来源的内容" in context
        assert "无来源的内容" in context
        # 无来源的不应该出现 [来源:]
        parts = context.split("---")
        assert "[来源:" not in parts[1]


class TestRetrieveAndRerank:
    """retrieve_and_rerank 函数测试"""

    @patch("app.services.rag.rerank")
    @patch("app.services.rag.hybrid_search")
    @patch("app.services.rag.get_embeddings")
    def test_basic_retrieval(self, mock_embeddings, mock_hybrid, mock_rerank):
        """测试基本检索+重排序流程"""
        from app.services.rag import retrieve_and_rerank

        mock_embeddings.return_value = [[0.1] * 768]
        mock_hybrid.return_value = [
            ("文档A", {"source": "a.pdf"}, 0.9, 0.8),
            ("文档B", {"source": "b.pdf"}, 0.7, 0.9),
        ]
        mock_rerank.return_value = [
            ("文档B", {"source": "b.pdf"}, 0.95),
            ("文档A", {"source": "a.pdf"}, 0.85),
        ]

        results = retrieve_and_rerank("测试问题", kb_id=1)

        assert len(results) == 2
        assert results[0][0] == "文档B"
        assert results[0][2] == 0.95
        mock_hybrid.assert_called_once()
        mock_rerank.assert_called_once()

    @patch("app.services.rag.rerank")
    @patch("app.services.rag.hybrid_search")
    @patch("app.services.rag.get_embeddings")
    def test_empty_hybrid_results(self, mock_embeddings, mock_hybrid, mock_rerank):
        """测试混合检索无结果时跳过重排序"""
        from app.services.rag import retrieve_and_rerank

        mock_embeddings.return_value = [[0.1] * 768]
        mock_hybrid.return_value = []

        results = retrieve_and_rerank("问题", kb_id=1)

        assert results == []
        mock_rerank.assert_not_called()

    @patch("app.services.rag.rerank")
    @patch("app.services.rag.hybrid_search")
    @patch("app.services.rag.get_embeddings")
    def test_custom_candidates_and_top_k(self, mock_embeddings, mock_hybrid, mock_rerank):
        """测试自定义候选数和返回数"""
        from app.services.rag import retrieve_and_rerank

        mock_embeddings.return_value = [[0.1] * 768]
        mock_hybrid.return_value = [("doc", {}, 0.5, 0.5)]
        mock_rerank.return_value = [("doc", {}, 0.9)]

        retrieve_and_rerank("问题", kb_id=1, candidates=30, top_k=3)

        call_kwargs = mock_hybrid.call_args
        assert call_kwargs[1]["top_k"] == 30 or call_kwargs[0][3] == 30

        rerank_kwargs = mock_rerank.call_args
        assert rerank_kwargs[1]["top_k"] == 3 or rerank_kwargs[0][2] == 3


class TestAskWithRag:
    """ask_with_rag 函数测试"""

    @patch("app.services.rag.chat_completion")
    @patch("app.services.rag.retrieve_and_rerank")
    def test_ask_with_rag_basic(self, mock_retrieve, mock_chat):
        """测试基本 RAG 问答"""
        from app.services.rag import ask_with_rag

        mock_retrieve.return_value = [
            ("公司规定每年有10天年假", {"source": "员工手册.pdf"}, 0.95),
        ]
        mock_chat.return_value = ("", "根据公司规定，每年有10天年假。")

        answer = ask_with_rag("年假有多少天？", kb_id=1)

        assert answer == "根据公司规定，每年有10天年假。"
        mock_retrieve.assert_called_once()

    @patch("app.services.rag.chat_completion")
    @patch("app.services.rag.retrieve_and_rerank")
    def test_ask_with_rag_empty_results(self, mock_retrieve, mock_chat):
        """测试检索结果为空时的 RAG 问答"""
        from app.services.rag import ask_with_rag

        mock_retrieve.return_value = []
        mock_chat.return_value = ("", "根据现有知识库，我无法回答这个问题。")

        answer = ask_with_rag("未知问题", kb_id=1)

        assert answer == "根据现有知识库，我无法回答这个问题。"
        # 验证传给 LLM 的 messages 中包含"无相关资料"
        call_args = mock_chat.call_args[0][0]
        system_msg = call_args[0]["content"]
        assert "无相关资料" in system_msg

    @patch("app.services.rag.chat_completion")
    @patch("app.services.rag.retrieve_and_rerank")
    def test_ask_with_rag_with_history(self, mock_retrieve, mock_chat):
        """测试带历史对话的 RAG 问答"""
        from app.services.rag import ask_with_rag

        mock_retrieve.return_value = [("文档内容", {"source": "test.pdf"}, 0.9)]
        mock_chat.return_value = ("", "回答")

        history = [
            {"role": "user", "content": "之前的问题"},
            {"role": "assistant", "content": "之前的回答"},
        ]

        answer = ask_with_rag("新问题", kb_id=1, history=history)

        assert answer == "回答"
        call_args = mock_chat.call_args[0][0]
        assert len(call_args) > 2  # system + history + user

    @patch("app.services.rag.chat_completion")
    @patch("app.services.rag.retrieve_and_rerank")
    def test_ask_with_rag_with_summary(self, mock_retrieve, mock_chat):
        """测试带摘要的 RAG 问答"""
        from app.services.rag import ask_with_rag

        mock_retrieve.return_value = [("文档内容", {"source": "test.pdf"}, 0.9)]
        mock_chat.return_value = ("", "回答")

        answer = ask_with_rag("问题", kb_id=1, summary="之前的对话摘要")

        assert answer == "回答"
        call_args = mock_chat.call_args[0][0]
        summary_msg = [m for m in call_args if "摘要" in m.get("content", "")]
        assert len(summary_msg) > 0

    @patch("app.services.rag.chat_completion")
    @patch("app.services.rag.retrieve_and_rerank")
    def test_ask_with_rag_with_history_and_summary(self, mock_retrieve, mock_chat):
        """测试同时带历史对话和摘要的 RAG 问答"""
        from app.services.rag import ask_with_rag

        mock_retrieve.return_value = [("文档内容", {"source": "test.pdf"}, 0.9)]
        mock_chat.return_value = ("", "综合回答")

        history = [
            {"role": "user", "content": "历史问题"},
            {"role": "assistant", "content": "历史回答"},
        ]

        answer = ask_with_rag("新问题", kb_id=1, history=history, summary="对话摘要")

        assert answer == "综合回答"
        call_args = mock_chat.call_args[0][0]
        # 消息结构：system(含context) + system(含摘要) + history(2条) + user
        assert len(call_args) == 5
        assert call_args[0]["role"] == "system"
        assert "摘要" in call_args[1]["content"]
        assert call_args[2]["role"] == "user"
        assert call_args[3]["role"] == "assistant"
        assert call_args[4]["role"] == "user"
        assert call_args[4]["content"] == "新问题"

    @patch("app.services.rag.retrieve_and_rerank")
    def test_ask_with_rag_retrieval_error(self, mock_retrieve):
        """测试检索服务异常"""
        from app.services.rag import ask_with_rag

        mock_retrieve.side_effect = Exception("检索服务不可用")

        with pytest.raises(Exception, match="检索服务不可用"):
            ask_with_rag("问题", kb_id=1)

    @patch("app.services.rag.chat_completion")
    @patch("app.services.rag.retrieve_and_rerank")
    def test_ask_with_rag_llm_error(self, mock_retrieve, mock_chat):
        """测试 LLM 服务异常"""
        from app.services.rag import ask_with_rag

        mock_retrieve.return_value = [("文档内容", {"source": "test.pdf"}, 0.9)]
        mock_chat.side_effect = Exception("LLM 服务不可用")

        with pytest.raises(Exception, match="LLM 服务不可用"):
            ask_with_rag("问题", kb_id=1)

    @patch("app.services.rag.chat_completion")
    @patch("app.services.rag.retrieve_and_rerank")
    def test_ask_with_rag_passes_correct_kb_id(self, mock_retrieve, mock_chat):
        """测试 kb_id 正确传递给 retrieve_and_rerank"""
        from app.services.rag import ask_with_rag

        mock_retrieve.return_value = []
        mock_chat.return_value = ("", "回答")

        ask_with_rag("问题", kb_id=42)

        call_args = mock_retrieve.call_args
        assert call_args[0][1] == 42

    @patch("app.services.rag.chat_completion")
    @patch("app.services.rag.retrieve_and_rerank")
    def test_ask_with_rag_system_prompt_contains_context(self, mock_retrieve, mock_chat):
        """测试系统提示中包含检索到的上下文"""
        from app.services.rag import ask_with_rag

        mock_retrieve.return_value = [
            ("特定文档内容XYZ", {"source": "specific.pdf"}, 0.9),
        ]
        mock_chat.return_value = ("", "回答")

        ask_with_rag("问题", kb_id=1)

        call_args = mock_chat.call_args[0][0]
        system_content = call_args[0]["content"]
        assert "特定文档内容XYZ" in system_content
        assert "[片段1 - 来源: specific.pdf]" in system_content


class TestAskWithRagStream:
    """ask_with_rag_stream 函数测试"""

    @patch("app.services.rag.chat_completion_stream")
    @patch("app.services.rag.retrieve_and_rerank")
    def test_stream_basic(self, mock_retrieve, mock_stream):
        """测试流式 RAG 问答"""
        from app.services.rag import ask_with_rag_stream

        mock_retrieve.return_value = [("文档内容", {"source": "test.pdf"}, 0.9)]
        mock_stream.return_value = iter(
            [
                {"type": "answer", "content": "回答"},
            ]
        )

        chunks = list(ask_with_rag_stream("问题", kb_id=1))

        assert len(chunks) == 1
        assert chunks[0]["content"] == "回答"

    @patch("app.services.rag.chat_completion_stream")
    @patch("app.services.rag.retrieve_and_rerank")
    def test_stream_multiple_chunks(self, mock_retrieve, mock_stream):
        """测试流式返回多个 chunk"""
        from app.services.rag import ask_with_rag_stream

        mock_retrieve.return_value = [("文档内容", {"source": "test.pdf"}, 0.9)]
        mock_stream.return_value = iter(
            [
                {"type": "reasoning", "content": "思考中"},
                {"type": "answer", "content": "你"},
                {"type": "answer", "content": "好"},
            ]
        )

        chunks = list(ask_with_rag_stream("问题", kb_id=1))

        assert len(chunks) == 3
        assert chunks[0]["type"] == "reasoning"
        assert chunks[1]["content"] == "你"
        assert chunks[2]["content"] == "好"

    @patch("app.services.rag.chat_completion_stream")
    @patch("app.services.rag.retrieve_and_rerank")
    def test_stream_empty_results(self, mock_retrieve, mock_stream):
        """测试检索结果为空时的流式问答"""
        from app.services.rag import ask_with_rag_stream

        mock_retrieve.return_value = []
        mock_stream.return_value = iter(
            [
                {"type": "answer", "content": "无法回答"},
            ]
        )

        chunks = list(ask_with_rag_stream("未知问题", kb_id=1))

        assert len(chunks) == 1
        # 验证传给 LLM 的 system message 包含"无相关资料"
        call_args = mock_stream.call_args[0][0]
        assert "无相关资料" in call_args[0]["content"]

    @patch("app.services.rag.chat_completion_stream")
    @patch("app.services.rag.retrieve_and_rerank")
    def test_stream_with_history(self, mock_retrieve, mock_stream):
        """测试带历史对话的流式问答"""
        from app.services.rag import ask_with_rag_stream

        mock_retrieve.return_value = [("文档内容", {"source": "test.pdf"}, 0.9)]
        mock_stream.return_value = iter(
            [
                {"type": "answer", "content": "流式回答"},
            ]
        )

        history = [
            {"role": "user", "content": "历史问题"},
            {"role": "assistant", "content": "历史回答"},
        ]

        chunks = list(ask_with_rag_stream("新问题", kb_id=1, history=history))

        assert len(chunks) == 1
        call_args = mock_stream.call_args[0][0]
        assert len(call_args) > 2  # system + history + user

    @patch("app.services.rag.chat_completion_stream")
    @patch("app.services.rag.retrieve_and_rerank")
    def test_stream_with_summary(self, mock_retrieve, mock_stream):
        """测试带摘要的流式问答"""
        from app.services.rag import ask_with_rag_stream

        mock_retrieve.return_value = [("文档内容", {"source": "test.pdf"}, 0.9)]
        mock_stream.return_value = iter(
            [
                {"type": "answer", "content": "回答"},
            ]
        )

        chunks = list(ask_with_rag_stream("问题", kb_id=1, summary="摘要内容"))

        assert len(chunks) == 1
        call_args = mock_stream.call_args[0][0]
        summary_msg = [m for m in call_args if "摘要" in m.get("content", "")]
        assert len(summary_msg) > 0

    @patch("app.services.rag.retrieve_and_rerank")
    def test_stream_retrieval_error(self, mock_retrieve):
        """测试流式问答中检索服务异常"""
        from app.services.rag import ask_with_rag_stream

        mock_retrieve.side_effect = Exception("检索失败")

        with pytest.raises(Exception, match="检索失败"):
            list(ask_with_rag_stream("问题", kb_id=1))

    @patch("app.services.rag.chat_completion_stream")
    @patch("app.services.rag.retrieve_and_rerank")
    def test_stream_llm_error(self, mock_retrieve, mock_stream):
        """测试流式问答中 LLM 服务异常"""
        from app.services.rag import ask_with_rag_stream

        mock_retrieve.return_value = [("文档内容", {"source": "test.pdf"}, 0.9)]
        mock_stream.side_effect = Exception("LLM 流式错误")

        with pytest.raises(Exception, match="LLM 流式错误"):
            list(ask_with_rag_stream("问题", kb_id=1))

    @patch("app.services.rag.chat_completion_stream")
    @patch("app.services.rag.retrieve_and_rerank")
    def test_stream_empty_generator(self, mock_retrieve, mock_stream):
        """测试流式返回空生成器"""
        from app.services.rag import ask_with_rag_stream

        mock_retrieve.return_value = [("文档内容", {"source": "test.pdf"}, 0.9)]
        mock_stream.return_value = iter([])

        chunks = list(ask_with_rag_stream("问题", kb_id=1))

        assert len(chunks) == 0
