"""LLM 流式服务测试 — 验证 yield dict 格式"""

from unittest.mock import MagicMock, patch


class TestChatCompletionStreamDictFormat:
    @patch("app.services.llm.client")
    def test_yields_answer_dict(self, mock_client):
        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock()]
        mock_chunk.choices[0].delta.content = "你好"
        del mock_chunk.choices[0].delta.reasoning_content

        mock_client.chat.completions.create.return_value = iter([mock_chunk])

        from app.services.llm import chat_completion_stream

        results = list(chat_completion_stream([{"role": "user", "content": "hi"}]))
        assert len(results) == 1
        assert results[0] == {"type": "answer", "content": "你好"}

    @patch("app.services.llm.client")
    def test_yields_reasoning_dict(self, mock_client):
        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock()]
        mock_chunk.choices[0].delta.content = None
        mock_chunk.choices[0].delta.reasoning_content = "让我想想..."

        mock_client.chat.completions.create.return_value = iter([mock_chunk])

        from app.services.llm import chat_completion_stream

        results = list(chat_completion_stream([{"role": "user", "content": "hi"}]))
        assert len(results) == 1
        assert results[0] == {"type": "reasoning", "content": "让我想想..."}

    @patch("app.services.llm.client")
    def test_reasoning_then_answer(self, mock_client):
        chunk1 = MagicMock()
        chunk1.choices = [MagicMock()]
        chunk1.choices[0].delta.content = None
        chunk1.choices[0].delta.reasoning_content = "思考中"

        chunk2 = MagicMock()
        chunk2.choices = [MagicMock()]
        chunk2.choices[0].delta.content = "回答"
        del chunk2.choices[0].delta.reasoning_content

        mock_client.chat.completions.create.return_value = iter([chunk1, chunk2])

        from app.services.llm import chat_completion_stream

        results = list(chat_completion_stream([{"role": "user", "content": "hi"}]))
        assert len(results) == 2
        assert results[0] == {"type": "reasoning", "content": "思考中"}
        assert results[1] == {"type": "answer", "content": "回答"}


class TestChatCompletionReturnsTuple:
    @patch("app.services.llm.client")
    def test_returns_reasoning_and_answer(self, mock_client):
        mock_response = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = "这是回答"
        mock_msg.reasoning_content = "这是思考"
        mock_response.choices = [MagicMock(message=mock_msg)]

        mock_client.chat.completions.create.return_value = mock_response

        from app.services.llm import chat_completion

        reasoning, answer = chat_completion([{"role": "user", "content": "hi"}])
        assert reasoning == "这是思考"
        assert answer == "这是回答"

    @patch("app.services.llm.client")
    def test_returns_empty_reasoning_when_none(self, mock_client):
        mock_response = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = "这是回答"
        del mock_msg.reasoning_content
        mock_response.choices = [MagicMock(message=mock_msg)]

        mock_client.chat.completions.create.return_value = mock_response

        from app.services.llm import chat_completion

        reasoning, answer = chat_completion([{"role": "user", "content": "hi"}])
        assert reasoning == ""
        assert answer == "这是回答"
