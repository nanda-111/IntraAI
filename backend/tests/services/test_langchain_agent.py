"""LangChain Agent 模块测试"""

import sys
from unittest.mock import MagicMock, patch

import pytest

# ---- 模块级 Mock：在 langchain_agent 首次导入前拦截外部依赖 ----
# 1. DuckDuckGoSearchRun 需要 ddgs 包，CI 可能未安装
# 2. sentence_transformers 需要额外安装，CI 可能未安装
# 3. langchain.agents.create_agent 可能不存在于当前 langchain 版本

_mock_ddg_instance = MagicMock()
_mock_ddg_instance.run.return_value = ""

_ddg_patcher = patch(
    "langchain_community.tools.DuckDuckGoSearchRun",
    return_value=_mock_ddg_instance,
)
_ddg_patcher.start()

# Mock sentence_transformers（CI 中可能未安装）
if "sentence_transformers" not in sys.modules:
    sys.modules["sentence_transformers"] = MagicMock()

# Mock create_agent（可能不存在于当前 langchain 版本）
import langchain.agents  # noqa: E402

if not hasattr(langchain.agents, "create_agent"):
    langchain.agents.create_agent = MagicMock()

# 清除之前因导入失败而缓存的残留状态
for mod_name in ["app.services.langchain_tools", "app.services.langchain_agent"]:
    if mod_name in sys.modules:
        del sys.modules[mod_name]

import app.services.langchain_agent as _agent_module  # noqa: E402
from app.services.langchain_agent import (  # noqa: E402
    AGENT_SYSTEM_PROMPT,
    _convert_history,
)


@pytest.fixture(autouse=True)
def reset_agent_cache():
    """每个测试前重置 Agent 缓存"""
    _agent_module._agent_cache = None
    yield
    _agent_module._agent_cache = None


class TestConvertHistory:
    """_convert_history 函数测试"""

    def test_convert_none_history(self):
        """测试 None 历史返回空列表"""
        result = _convert_history(None)
        assert result == []

    def test_convert_empty_list(self):
        """测试空列表返回空列表"""
        result = _convert_history([])
        assert result == []

    def test_convert_user_message(self):
        """测试转换 user 消息为 HumanMessage"""
        from langchain_core.messages import HumanMessage

        history = [{"role": "user", "content": "你好"}]
        result = _convert_history(history)

        assert len(result) == 1
        assert isinstance(result[0], HumanMessage)
        assert result[0].content == "你好"

    def test_convert_assistant_message(self):
        """测试转换 assistant 消息为 AIMessage"""
        from langchain_core.messages import AIMessage

        history = [{"role": "assistant", "content": "你好啊"}]
        result = _convert_history(history)

        assert len(result) == 1
        assert isinstance(result[0], AIMessage)
        assert result[0].content == "你好啊"

    def test_convert_multiple_messages(self):
        """测试转换多条混合消息"""
        from langchain_core.messages import AIMessage, HumanMessage

        history = [
            {"role": "user", "content": "问题1"},
            {"role": "assistant", "content": "回答1"},
            {"role": "user", "content": "问题2"},
        ]

        result = _convert_history(history)

        assert len(result) == 3
        assert isinstance(result[0], HumanMessage)
        assert result[0].content == "问题1"
        assert isinstance(result[1], AIMessage)
        assert result[1].content == "回答1"
        assert isinstance(result[2], HumanMessage)
        assert result[2].content == "问题2"

    def test_convert_skips_unknown_roles(self):
        """测试未知 role 会被跳过"""
        from langchain_core.messages import AIMessage, HumanMessage

        history = [
            {"role": "user", "content": "问题"},
            {"role": "system", "content": "系统消息"},
            {"role": "assistant", "content": "回答"},
        ]

        result = _convert_history(history)

        assert len(result) == 2
        assert isinstance(result[0], HumanMessage)
        assert isinstance(result[1], AIMessage)


class TestGetAgent:
    """_get_agent 函数测试"""

    def test_get_agent_creates_agent(self):
        """测试首次调用会创建 Agent"""
        mock_agent = MagicMock()
        mock_create = MagicMock(return_value=mock_agent)
        mock_llm = MagicMock()

        with patch.object(_agent_module, "create_agent", mock_create):
            with patch.object(_agent_module, "get_mimo_llm", mock_llm):
                result = _agent_module._get_agent()

                assert result is mock_agent
                mock_llm.assert_called_once_with(streaming=True)
                mock_create.assert_called_once()

    def test_get_agent_uses_cache(self):
        """测试 Agent 缓存机制 — 只创建一次"""
        mock_agent = MagicMock()
        mock_create = MagicMock(return_value=mock_agent)
        mock_llm = MagicMock()

        with patch.object(_agent_module, "create_agent", mock_create):
            with patch.object(_agent_module, "get_mimo_llm", mock_llm):
                agent1 = _agent_module._get_agent()
                agent2 = _agent_module._get_agent()

                assert agent1 is agent2
                mock_create.assert_called_once()

    def test_get_agent_passes_system_prompt(self):
        """测试创建 Agent 时传入 system_prompt"""
        mock_create = MagicMock(return_value=MagicMock())
        mock_llm = MagicMock()

        with patch.object(_agent_module, "create_agent", mock_create):
            with patch.object(_agent_module, "get_mimo_llm", mock_llm):
                _agent_module._get_agent()

                call_kwargs = mock_create.call_args.kwargs
                assert call_kwargs["system_prompt"] == AGENT_SYSTEM_PROMPT

    def test_get_agent_passes_tools(self):
        """测试创建 Agent 时传入 tools"""
        mock_create = MagicMock(return_value=MagicMock())
        mock_llm = MagicMock()

        with patch.object(_agent_module, "create_agent", mock_create):
            with patch.object(_agent_module, "get_mimo_llm", mock_llm):
                _agent_module._get_agent()

                call_kwargs = mock_create.call_args.kwargs
                tools = call_kwargs["tools"]
                assert len(tools) == 3


class TestRunAgent:
    """run_agent 函数测试"""

    def test_run_agent_basic(self):
        """测试基本 Agent 调用"""
        mock_agent = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = "Agent 回答"
        mock_agent.invoke.return_value = {"messages": [mock_msg]}

        with patch.object(_agent_module, "_get_agent", return_value=mock_agent):
            result = _agent_module.run_agent("测试问题")

            assert result == "Agent 回答"
            mock_agent.invoke.assert_called_once()

    def test_run_agent_returns_last_message(self):
        """测试返回最后一条消息的内容"""
        mock_agent = MagicMock()
        msg1 = MagicMock()
        msg1.content = "中间回答"
        msg2 = MagicMock()
        msg2.content = "最终回答"
        mock_agent.invoke.return_value = {"messages": [msg1, msg2]}

        with patch.object(_agent_module, "_get_agent", return_value=mock_agent):
            result = _agent_module.run_agent("问题")

            assert result == "最终回答"

    def test_run_agent_with_history(self):
        """测试带历史消息的 Agent 调用"""
        mock_agent = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = "回答"
        mock_agent.invoke.return_value = {"messages": [mock_msg]}

        history = [
            {"role": "user", "content": "之前的问题"},
            {"role": "assistant", "content": "之前的回答"},
        ]

        with patch.object(_agent_module, "_get_agent", return_value=mock_agent):
            result = _agent_module.run_agent("新问题", history=history)

            assert result == "回答"
            # 验证 invoke 时 messages 包含历史 + 新问题
            call_args = mock_agent.invoke.call_args
            messages = call_args[0][0]["messages"]
            assert len(messages) == 3

    def test_run_agent_no_history(self):
        """测试不带历史消息的 Agent 调用"""
        mock_agent = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = "回答"
        mock_agent.invoke.return_value = {"messages": [mock_msg]}

        with patch.object(_agent_module, "_get_agent", return_value=mock_agent):
            result = _agent_module.run_agent("问题", history=None)

            assert result == "回答"
            call_args = mock_agent.invoke.call_args
            messages = call_args[0][0]["messages"]
            assert len(messages) == 1

    def test_run_agent_invoke_error(self):
        """测试 Agent 调用出错时抛出异常"""
        mock_agent = MagicMock()
        mock_agent.invoke.side_effect = RuntimeError("调用失败")

        with patch.object(_agent_module, "_get_agent", return_value=mock_agent):
            with pytest.raises(RuntimeError, match="调用失败"):
                _agent_module.run_agent("问题")


class TestRunAgentStream:
    """run_agent_stream 函数测试"""

    async def test_run_agent_stream_yields_chunks(self):
        """测试流式 Agent 返回多个 chunk"""
        mock_agent = MagicMock()

        chunk1 = MagicMock()
        chunk1.content = "你好"
        chunk2 = MagicMock()
        chunk2.content = "世界"

        async def mock_astream(*args, **kwargs):
            yield ("messages", [chunk1])
            yield ("messages", [chunk2])

        mock_agent.astream = mock_astream

        with patch.object(_agent_module, "_get_agent", return_value=mock_agent):
            chunks = []
            async for chunk in _agent_module.run_agent_stream("测试"):
                chunks.append(chunk)

            assert len(chunks) == 2
            assert chunks[0] == {"type": "answer", "content": "你好"}
            assert chunks[1] == {"type": "answer", "content": "世界"}

    async def test_run_agent_stream_skips_empty_content(self):
        """测试流式 Agent 跳过空内容的 chunk"""
        mock_agent = MagicMock()

        chunk_empty = MagicMock()
        chunk_empty.content = ""
        chunk_valid = MagicMock()
        chunk_valid.content = "有效内容"

        async def mock_astream(*args, **kwargs):
            yield ("messages", [chunk_empty])
            yield ("messages", [chunk_valid])

        mock_agent.astream = mock_astream

        with patch.object(_agent_module, "_get_agent", return_value=mock_agent):
            chunks = []
            async for chunk in _agent_module.run_agent_stream("测试"):
                chunks.append(chunk)

            assert len(chunks) == 1
            assert chunks[0]["content"] == "有效内容"

    async def test_run_agent_stream_skips_non_message_events(self):
        """测试流式 Agent 跳过非 messages 类型事件"""
        mock_agent = MagicMock()

        chunk = MagicMock()
        chunk.content = "回答"

        async def mock_astream(*args, **kwargs):
            yield ("other_event", [chunk])
            yield ("messages", [chunk])

        mock_agent.astream = mock_astream

        with patch.object(_agent_module, "_get_agent", return_value=mock_agent):
            chunks = []
            async for chunk in _agent_module.run_agent_stream("测试"):
                chunks.append(chunk)

            assert len(chunks) == 1
            assert chunks[0]["content"] == "回答"

    async def test_run_agent_stream_skips_empty_event_data(self):
        """测试流式 Agent 跳过空 event_data"""
        mock_agent = MagicMock()

        chunk = MagicMock()
        chunk.content = "回答"

        async def mock_astream(*args, **kwargs):
            yield ("messages", [])
            yield ("messages", [chunk])

        mock_agent.astream = mock_astream

        with patch.object(_agent_module, "_get_agent", return_value=mock_agent):
            chunks = []
            async for chunk in _agent_module.run_agent_stream("测试"):
                chunks.append(chunk)

            assert len(chunks) == 1

    async def test_run_agent_stream_with_history(self):
        """测试带历史消息的流式调用"""
        mock_agent = MagicMock()
        chunk = MagicMock()
        chunk.content = "回答"

        async def mock_astream(*args, **kwargs):
            yield ("messages", [chunk])

        mock_agent.astream = mock_astream

        history = [{"role": "user", "content": "历史问题"}]

        with patch.object(_agent_module, "_get_agent", return_value=mock_agent):
            chunks = []
            async for c in _agent_module.run_agent_stream("新问题", history=history):
                chunks.append(c)

            assert len(chunks) == 1

    async def test_run_agent_stream_passes_correct_messages(self):
        """测试流式调用传递正确的 messages 参数"""
        mock_agent = MagicMock()
        captured_args = []

        async def mock_astream(*args, **kwargs):
            captured_args.append(args)
            yield ("messages", [])

        mock_agent.astream = mock_astream

        with patch.object(_agent_module, "_get_agent", return_value=mock_agent):
            async for _ in _agent_module.run_agent_stream("问题"):
                pass

            assert len(captured_args) == 1
            messages = captured_args[0][0]["messages"]
            assert len(messages) == 1
            assert messages[0].content == "问题"
