"""LLM 服务模块测试"""

from unittest.mock import MagicMock, patch

import pytest


class TestChatCompletion:
    """chat_completion 函数测试"""

    @patch("app.services.llm.client")
    def test_chat_completion_success(self, mock_client):
        """测试普通对话调用成功"""
        from app.services.llm import chat_completion

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "你好"
        mock_response.choices[0].message.reasoning_content = "思考过程"
        mock_client.chat.completions.create.return_value = mock_response

        reasoning, answer = chat_completion([{"role": "user", "content": "你好"}])

        assert answer == "你好"
        assert reasoning == "思考过程"
        mock_client.chat.completions.create.assert_called_once()

    @patch("app.services.llm.client")
    def test_chat_completion_no_reasoning(self, mock_client):
        """测试没有 reasoning_content 的情况"""
        from app.services.llm import chat_completion

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "回答"
        mock_response.choices[0].message.reasoning_content = None
        mock_client.chat.completions.create.return_value = mock_response

        reasoning, answer = chat_completion([{"role": "user", "content": "测试"}])

        assert answer == "回答"
        assert reasoning == ""

    @patch("app.services.llm.client")
    def test_chat_completion_custom_model(self, mock_client):
        """测试使用自定义模型"""
        from app.services.llm import chat_completion

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "回答"
        mock_response.choices[0].message.reasoning_content = ""
        mock_client.chat.completions.create.return_value = mock_response

        chat_completion([{"role": "user", "content": "测试"}], model="custom-model")

        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "custom-model"


class TestChatCompletionStream:
    """chat_completion_stream 函数测试"""

    @patch("app.services.llm.client")
    def test_stream_success(self, mock_client):
        """测试流式调用成功"""
        from app.services.llm import chat_completion_stream

        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [MagicMock()]
        mock_chunk1.choices[0].delta.content = "你好"
        mock_chunk1.choices[0].delta.reasoning_content = None

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [MagicMock()]
        mock_chunk2.choices[0].delta.content = None
        mock_chunk2.choices[0].delta.reasoning_content = "思考"

        mock_client.chat.completions.create.return_value = iter([mock_chunk1, mock_chunk2])

        chunks = list(chat_completion_stream([{"role": "user", "content": "你好"}]))

        assert len(chunks) == 2
        assert chunks[0] == {"type": "answer", "content": "你好"}
        assert chunks[1] == {"type": "reasoning", "content": "思考"}

    @patch("app.services.llm.client")
    def test_stream_empty_choices(self, mock_client):
        """测试空 choices 的情况"""
        from app.services.llm import chat_completion_stream

        mock_chunk = MagicMock()
        mock_chunk.choices = []

        mock_client.chat.completions.create.return_value = iter([mock_chunk])

        chunks = list(chat_completion_stream([{"role": "user", "content": "测试"}]))

        assert len(chunks) == 0

    @patch("app.services.llm.client")
    def test_stream_custom_model(self, mock_client):
        """测试流式调用使用自定义模型"""
        from app.services.llm import chat_completion_stream

        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock()]
        mock_chunk.choices[0].delta.content = "回答"
        mock_chunk.choices[0].delta.reasoning_content = None

        mock_client.chat.completions.create.return_value = iter([mock_chunk])

        list(chat_completion_stream([{"role": "user", "content": "测试"}], model="custom-model"))

        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "custom-model"
        assert call_args[1]["stream"] is True


class TestGenerateTitle:
    """generate_title 函数测试"""

    @patch("app.services.llm.chat_completion")
    def test_generate_title_success(self, mock_chat):
        """测试标题生成成功"""
        from app.services.llm import generate_title

        mock_chat.return_value = ("", "公司请假制度说明")

        title = generate_title("公司的请假制度是什么？", "根据公司规定...")

        assert title == "公司请假制度说明"

    @patch("app.services.llm.chat_completion")
    def test_generate_title_with_quotes(self, mock_chat):
        """测试标题去除引号"""
        from app.services.llm import generate_title

        mock_chat.return_value = ("", '"公司请假制度"')

        title = generate_title("请假制度", "回答")

        assert '"' not in title
        assert "'" not in title

    @patch("app.services.llm.chat_completion")
    def test_generate_title_with_chinese_quotes(self, mock_chat):
        """测试标题去除中文引号"""
        from app.services.llm import generate_title

        mock_chat.return_value = ("", "“公司请假制度”")

        title = generate_title("请假制度", "回答")

        assert "“" not in title
        assert "”" not in title

    @patch("app.services.llm.chat_completion")
    def test_generate_title_truncation(self, mock_chat):
        """测试标题超过50字被截断"""
        from app.services.llm import generate_title

        long_title = "这是一个非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常长的标题"
        mock_chat.return_value = ("", long_title)

        title = generate_title("问题", "回答")

        assert len(title) <= 50


class TestGenerateSummary:
    """generate_summary 函数测试"""

    @patch("app.services.llm.chat_completion")
    def test_generate_summary_success(self, mock_chat):
        """测试摘要生成成功"""
        from app.services.llm import generate_summary

        mock_chat.return_value = ("", "用户询问了请假制度，AI进行了解答")

        conversations = [
            {"role": "user", "content": "请假制度是什么？"},
            {"role": "assistant", "content": "根据公司规定..."},
        ]

        summary = generate_summary(conversations)

        assert summary == "用户询问了请假制度，AI进行了解答"

    @patch("app.services.llm.chat_completion")
    def test_generate_summary_prompt_contains_history(self, mock_chat):
        """测试摘要生成的 prompt 包含对话历史"""
        from app.services.llm import generate_summary

        mock_chat.return_value = ("", "摘要")

        conversations = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好，有什么可以帮您？"},
        ]

        generate_summary(conversations)

        call_args = mock_chat.call_args
        prompt = call_args[0][0][0]["content"]
        assert "你好" in prompt
        assert "你好，有什么可以帮您？" in prompt
