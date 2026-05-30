"""LangChain LLM 封装模块测试"""

import sys
from unittest.mock import MagicMock, patch

# ---- 模块级 Mock：处理 CI 环境中的依赖问题 ----
# Mock sentence_transformers（CI 中可能未安装）
if "sentence_transformers" not in sys.modules:
    sys.modules["sentence_transformers"] = MagicMock()

# Mock langchain_openai 内部函数（版本兼容性问题）
import langchain_openai.chat_models.base as _lc_base  # noqa: E402

if not hasattr(_lc_base, "_convert_from_v1_to_chat_completions"):
    _lc_base._convert_from_v1_to_chat_completions = MagicMock()
if not hasattr(_lc_base, "_convert_message_to_dict"):
    _lc_base._convert_message_to_dict = MagicMock()


class TestConvertDictToMessageWithReasoning:
    """_convert_dict_to_message_with_reasoning 函数测试"""

    def test_assistant_with_reasoning(self):
        """测试 assistant 消息带 reasoning_content"""
        from app.services.langchain_llm import _convert_dict_to_message_with_reasoning

        _dict = {
            "role": "assistant",
            "content": "回答内容",
            "reasoning_content": "思考过程",
        }

        with patch("app.services.langchain_llm._orig_convert_dict") as mock_orig:
            mock_msg = MagicMock()
            mock_msg.additional_kwargs = {}
            mock_orig.return_value = mock_msg

            result = _convert_dict_to_message_with_reasoning(_dict)

            assert result.additional_kwargs["reasoning_content"] == "思考过程"

    def test_assistant_without_reasoning(self):
        """测试 assistant 消息不带 reasoning_content"""
        from app.services.langchain_llm import _convert_dict_to_message_with_reasoning

        _dict = {
            "role": "assistant",
            "content": "回答内容",
        }

        with patch("app.services.langchain_llm._orig_convert_dict") as mock_orig:
            mock_msg = MagicMock()
            mock_msg.additional_kwargs = {}
            mock_orig.return_value = mock_msg

            result = _convert_dict_to_message_with_reasoning(_dict)

            assert "reasoning_content" not in result.additional_kwargs

    def test_non_assistant_message(self):
        """测试非 assistant 消息"""
        from app.services.langchain_llm import _convert_dict_to_message_with_reasoning

        _dict = {
            "role": "user",
            "content": "用户问题",
        }

        with patch("app.services.langchain_llm._orig_convert_dict") as mock_orig:
            mock_msg = MagicMock()
            mock_msg.additional_kwargs = {}
            mock_orig.return_value = mock_msg

            result = _convert_dict_to_message_with_reasoning(_dict)

            assert "reasoning_content" not in result.additional_kwargs

    def test_assistant_with_empty_reasoning(self):
        """测试 assistant 消息带空字符串 reasoning_content（不注入）"""
        from app.services.langchain_llm import _convert_dict_to_message_with_reasoning

        _dict = {
            "role": "assistant",
            "content": "回答内容",
            "reasoning_content": "",
        }

        with patch("app.services.langchain_llm._orig_convert_dict") as mock_orig:
            mock_msg = MagicMock()
            mock_msg.additional_kwargs = {}
            mock_orig.return_value = mock_msg

            result = _convert_dict_to_message_with_reasoning(_dict)

            # 空字符串为 falsy，不应注入
            assert "reasoning_content" not in result.additional_kwargs

    def test_assistant_with_none_reasoning(self):
        """测试 assistant 消息带 None reasoning_content（不注入）"""
        from app.services.langchain_llm import _convert_dict_to_message_with_reasoning

        _dict = {
            "role": "assistant",
            "content": "回答内容",
            "reasoning_content": None,
        }

        with patch("app.services.langchain_llm._orig_convert_dict") as mock_orig:
            mock_msg = MagicMock()
            mock_msg.additional_kwargs = {}
            mock_orig.return_value = mock_msg

            result = _convert_dict_to_message_with_reasoning(_dict)

            assert "reasoning_content" not in result.additional_kwargs

    def test_calls_original_function(self):
        """测试确实调用了原始 _convert_dict_to_message"""
        from app.services.langchain_llm import _convert_dict_to_message_with_reasoning

        _dict = {"role": "assistant", "content": "hello"}

        with patch("app.services.langchain_llm._orig_convert_dict") as mock_orig:
            mock_msg = MagicMock()
            mock_msg.additional_kwargs = {}
            mock_orig.return_value = mock_msg

            _convert_dict_to_message_with_reasoning(_dict)

            mock_orig.assert_called_once_with(_dict)

    def test_returns_original_message(self):
        """测试返回原始消息对象（不是副本）"""
        from app.services.langchain_llm import _convert_dict_to_message_with_reasoning

        _dict = {"role": "assistant", "content": "hello"}

        with patch("app.services.langchain_llm._orig_convert_dict") as mock_orig:
            mock_msg = MagicMock()
            mock_msg.additional_kwargs = {}
            mock_orig.return_value = mock_msg

            result = _convert_dict_to_message_with_reasoning(_dict)

            assert result is mock_msg


class TestConvertDeltaToMessageChunkWithReasoning:
    """_convert_delta_to_message_chunk_with_reasoning 函数测试"""

    def test_delta_with_reasoning(self):
        """测试 delta 带 reasoning_content"""
        from app.services.langchain_llm import _convert_delta_to_message_chunk_with_reasoning

        _dict = {"reasoning_content": "流式思考"}

        with patch("app.services.langchain_llm._orig_convert_delta") as mock_orig:
            mock_chunk = MagicMock()
            mock_chunk.additional_kwargs = {}
            mock_orig.return_value = mock_chunk

            result = _convert_delta_to_message_chunk_with_reasoning(_dict, MagicMock())

            assert result.additional_kwargs["reasoning_content"] == "流式思考"

    def test_delta_without_reasoning(self):
        """测试 delta 不带 reasoning_content"""
        from app.services.langchain_llm import _convert_delta_to_message_chunk_with_reasoning

        _dict = {"content": "内容"}

        with patch("app.services.langchain_llm._orig_convert_delta") as mock_orig:
            mock_chunk = MagicMock()
            mock_chunk.additional_kwargs = {}
            mock_orig.return_value = mock_chunk

            result = _convert_delta_to_message_chunk_with_reasoning(_dict, MagicMock())

            assert "reasoning_content" not in result.additional_kwargs

    def test_delta_with_empty_reasoning(self):
        """测试 delta 带空字符串 reasoning_content（不注入）"""
        from app.services.langchain_llm import _convert_delta_to_message_chunk_with_reasoning

        _dict = {"reasoning_content": ""}

        with patch("app.services.langchain_llm._orig_convert_delta") as mock_orig:
            mock_chunk = MagicMock()
            mock_chunk.additional_kwargs = {}
            mock_orig.return_value = mock_chunk

            result = _convert_delta_to_message_chunk_with_reasoning(_dict, MagicMock())

            assert "reasoning_content" not in result.additional_kwargs

    def test_calls_original_function(self):
        """测试确实调用了原始 _convert_delta_to_message_chunk"""
        from app.services.langchain_llm import _convert_delta_to_message_chunk_with_reasoning

        _dict = {"content": "hello"}
        default_class = MagicMock()

        with patch("app.services.langchain_llm._orig_convert_delta") as mock_orig:
            mock_chunk = MagicMock()
            mock_chunk.additional_kwargs = {}
            mock_orig.return_value = mock_chunk

            _convert_delta_to_message_chunk_with_reasoning(_dict, default_class)

            mock_orig.assert_called_once_with(_dict, default_class)

    def test_returns_original_chunk(self):
        """测试返回原始 chunk 对象"""
        from app.services.langchain_llm import _convert_delta_to_message_chunk_with_reasoning

        _dict = {"content": "hello"}

        with patch("app.services.langchain_llm._orig_convert_delta") as mock_orig:
            mock_chunk = MagicMock()
            mock_chunk.additional_kwargs = {}
            mock_orig.return_value = mock_chunk

            result = _convert_delta_to_message_chunk_with_reasoning(_dict, MagicMock())

            assert result is mock_chunk


class TestInjectReasoning:
    """_inject_reasoning 函数测试"""

    def test_inject_reasoning_to_ai_message(self):
        """测试注入 reasoning 到 AIMessage"""
        from langchain_core.messages import AIMessage

        from app.services.langchain_llm import _inject_reasoning

        msg = AIMessage(content="回答")
        msg.additional_kwargs["reasoning_content"] = "思考过程"

        msg_dict = {"role": "assistant", "content": "回答"}

        result = _inject_reasoning(msg_dict, msg)

        assert result["reasoning_content"] == "思考过程"

    def test_skip_non_ai_message(self):
        """测试跳过非 AIMessage"""
        from langchain_core.messages import HumanMessage

        from app.services.langchain_llm import _inject_reasoning

        msg = HumanMessage(content="问题")
        msg_dict = {"role": "user", "content": "问题"}

        result = _inject_reasoning(msg_dict, msg)

        assert "reasoning_content" not in result

    def test_skip_existing_reasoning(self):
        """测试跳过已有 reasoning 的消息"""
        from langchain_core.messages import AIMessage

        from app.services.langchain_llm import _inject_reasoning

        msg = AIMessage(content="回答")
        msg.additional_kwargs["reasoning_content"] = "思考"

        msg_dict = {"role": "assistant", "content": "回答", "reasoning_content": "已有"}

        result = _inject_reasoning(msg_dict, msg)

        assert result["reasoning_content"] == "已有"

    def test_skip_ai_message_without_reasoning(self):
        """测试 AIMessage 没有 reasoning_content 时不注入"""
        from langchain_core.messages import AIMessage

        from app.services.langchain_llm import _inject_reasoning

        msg = AIMessage(content="回答")
        # additional_kwargs 中没有 reasoning_content

        msg_dict = {"role": "assistant", "content": "回答"}

        result = _inject_reasoning(msg_dict, msg)

        assert "reasoning_content" not in result

    def test_returns_same_dict(self):
        """测试返回的是同一个 dict 对象（原地修改）"""
        from langchain_core.messages import AIMessage

        from app.services.langchain_llm import _inject_reasoning

        msg = AIMessage(content="回答")
        msg.additional_kwargs["reasoning_content"] = "思考"

        msg_dict = {"role": "assistant", "content": "回答"}

        result = _inject_reasoning(msg_dict, msg)

        assert result is msg_dict

    def test_inject_with_multiline_reasoning(self):
        """测试注入多行 reasoning 内容"""
        from langchain_core.messages import AIMessage

        from app.services.langchain_llm import _inject_reasoning

        long_reasoning = "第一步思考\n第二步推理\n第三步总结"
        msg = AIMessage(content="回答")
        msg.additional_kwargs["reasoning_content"] = long_reasoning

        msg_dict = {"role": "assistant", "content": "回答"}

        result = _inject_reasoning(msg_dict, msg)

        assert result["reasoning_content"] == long_reasoning


class TestChatMiMo:
    """ChatMiMo 类测试"""

    def test_llm_type(self):
        """测试 LLM 类型属性"""
        from app.services.langchain_llm import ChatMiMo

        with patch("app.services.langchain_llm.settings"):
            llm = ChatMiMo(api_key="test-key")
            assert llm._llm_type == "chat-mimo"

    def test_chatmimo_inherits_chat_openai(self):
        """测试 ChatMiMo 继承自 ChatOpenAI"""
        from langchain_openai import ChatOpenAI

        from app.services.langchain_llm import ChatMiMo

        assert issubclass(ChatMiMo, ChatOpenAI)

    @patch("app.services.langchain_llm.settings")
    def test_get_mimo_llm(self, mock_settings):
        """测试获取 MiMo LLM 实例"""
        from app.services.langchain_llm import ChatMiMo, get_mimo_llm

        mock_settings.OPENAI_MODEL = "test-model"
        mock_settings.OPENAI_API_KEY = "test-key"
        mock_settings.OPENAI_BASE_URL = "http://test.com"

        llm = get_mimo_llm(temperature=0.5, streaming=True)

        assert isinstance(llm, ChatMiMo)
        assert llm.temperature == 0.5
        assert llm.streaming is True

    @patch("app.services.langchain_llm.settings")
    def test_get_mimo_llm_default_params(self, mock_settings):
        """测试 get_mimo_llm 默认参数"""
        from app.services.langchain_llm import get_mimo_llm

        mock_settings.OPENAI_MODEL = "test-model"
        mock_settings.OPENAI_API_KEY = "test-key"
        mock_settings.OPENAI_BASE_URL = "http://test.com"

        llm = get_mimo_llm()

        assert llm.temperature == 0.7
        assert llm.streaming is False

    @patch("app.services.langchain_llm.settings")
    def test_get_mimo_llm_uses_settings(self, mock_settings):
        """测试 get_mimo_llm 使用 settings 配置"""
        from app.services.langchain_llm import get_mimo_llm

        mock_settings.OPENAI_MODEL = "mimo-v2"
        mock_settings.OPENAI_API_KEY = "sk-secret"
        mock_settings.OPENAI_BASE_URL = "https://api.mimo.com/v1"

        llm = get_mimo_llm()

        assert llm.model_name == "mimo-v2"
        assert llm.openai_api_key.get_secret_value() == "sk-secret"

    @patch("app.services.langchain_llm.settings")
    def test_get_request_payload_injects_reasoning(self, mock_settings):
        """测试 _get_request_payload 注入 reasoning_content"""
        from langchain_core.messages import AIMessage

        from app.services.langchain_llm import ChatMiMo

        mock_settings.OPENAI_MODEL = "test"
        mock_settings.OPENAI_API_KEY = "test"
        mock_settings.OPENAI_BASE_URL = "http://test"

        llm = ChatMiMo(api_key="test-key")

        # 创建带 reasoning_content 的 AIMessage
        msg = AIMessage(content="回答")
        msg.additional_kwargs["reasoning_content"] = "思考过程"

        # 调用 _get_request_payload
        payload = llm._get_request_payload([msg])

        # 检查 payload 中的 messages 包含 reasoning_content
        messages = payload["messages"]
        assert len(messages) == 1
        assert messages[0]["reasoning_content"] == "思考过程"

    @patch("app.services.langchain_llm.settings")
    def test_get_request_payload_no_reasoning(self, mock_settings):
        """测试 _get_request_payload 无 reasoning_content 时不注入"""
        from langchain_core.messages import AIMessage

        from app.services.langchain_llm import ChatMiMo

        mock_settings.OPENAI_MODEL = "test"
        mock_settings.OPENAI_API_KEY = "test"
        mock_settings.OPENAI_BASE_URL = "http://test"

        llm = ChatMiMo(api_key="test-key")

        msg = AIMessage(content="回答")

        payload = llm._get_request_payload([msg])

        messages = payload["messages"]
        assert len(messages) == 1
        assert "reasoning_content" not in messages[0]

    @patch("app.services.langchain_llm.settings")
    def test_get_request_payload_multiple_messages(self, mock_settings):
        """测试 _get_request_payload 多条消息混合场景"""
        from langchain_core.messages import AIMessage, HumanMessage

        from app.services.langchain_llm import ChatMiMo

        mock_settings.OPENAI_MODEL = "test"
        mock_settings.OPENAI_API_KEY = "test"
        mock_settings.OPENAI_BASE_URL = "http://test"

        llm = ChatMiMo(api_key="test-key")

        ai_msg = AIMessage(content="回答")
        ai_msg.additional_kwargs["reasoning_content"] = "思考"
        messages = [
            HumanMessage(content="问题"),
            ai_msg,
            HumanMessage(content="追问"),
        ]

        payload = llm._get_request_payload(messages)

        payload_msgs = payload["messages"]
        assert len(payload_msgs) == 3
        # user 消息没有 reasoning_content
        assert "reasoning_content" not in payload_msgs[0]
        # ai 消息有 reasoning_content
        assert payload_msgs[1]["reasoning_content"] == "思考"
        # user 消息没有 reasoning_content
        assert "reasoning_content" not in payload_msgs[2]

    @patch("app.services.langchain_llm.settings")
    def test_get_request_payload_with_stop(self, mock_settings):
        """测试 _get_request_payload 传递 stop 参数"""
        from langchain_core.messages import HumanMessage

        from app.services.langchain_llm import ChatMiMo

        mock_settings.OPENAI_MODEL = "test"
        mock_settings.OPENAI_API_KEY = "test"
        mock_settings.OPENAI_BASE_URL = "http://test"

        llm = ChatMiMo(api_key="test-key")

        payload = llm._get_request_payload([HumanMessage(content="hello")], stop=["STOP"])

        assert payload["stop"] == ["STOP"]

    @patch("app.services.langchain_llm.settings")
    def test_get_request_payload_stop_none(self, mock_settings):
        """测试 _get_request_payload stop=None 时不添加 stop"""
        from langchain_core.messages import HumanMessage

        from app.services.langchain_llm import ChatMiMo

        mock_settings.OPENAI_MODEL = "test"
        mock_settings.OPENAI_API_KEY = "test"
        mock_settings.OPENAI_BASE_URL = "http://test"

        llm = ChatMiMo(api_key="test-key")

        payload = llm._get_request_payload([HumanMessage(content="hello")], stop=None)

        assert "stop" not in payload
