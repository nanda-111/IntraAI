"""
LangChain MiMo LLM 封装模块

使用 LangChain 的 ChatOpenAI 类对接小米 MiMo API（OpenAI 兼容接口）。

MiMo 特殊处理：
  MiMo 使用思考模式（thinking mode），在 API 响应中返回 reasoning_content。
  多轮工具调用时，reasoning_content 必须回传给 API，否则报 400 错误。

  需要两个补丁：
  1. _convert_dict_to_message：从 API 响应中提取 reasoning_content → 存入 AIMessage
  2. _get_request_payload：将 AIMessage 中的 reasoning_content 注入 API 请求
"""

from typing import Any

from langchain_core.messages import AIMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langchain_openai.chat_models import base as _lc_base
from langchain_openai.chat_models.base import (
    _convert_from_v1_to_chat_completions,
    _convert_message_to_dict,
)

from app.core.config import settings

# ==================== 补丁 1: 捕获 reasoning_content ====================
# LangChain 的 _convert_dict_to_message 不提取 reasoning_content。
# 我们需要在 AIMessage 创建时把它存入 additional_kwargs。

_orig_convert_dict = _lc_base._convert_dict_to_message


def _convert_dict_to_message_with_reasoning(_dict):
    msg = _orig_convert_dict(_dict)
    if _dict.get("role") == "assistant" and _dict.get("reasoning_content"):
        msg.additional_kwargs["reasoning_content"] = _dict["reasoning_content"]
    return msg


_lc_base._convert_dict_to_message = _convert_dict_to_message_with_reasoning


# ==================== 补丁 1b: 流式模式也要捕获 reasoning_content ====================
# 流式模式使用 _convert_delta_to_message_chunk，它也不提取 reasoning_content。

_orig_convert_delta = _lc_base._convert_delta_to_message_chunk


def _convert_delta_to_message_chunk_with_reasoning(_dict, default_chunk_class):
    msg = _orig_convert_delta(_dict, default_chunk_class)
    if _dict.get("reasoning_content"):
        msg.additional_kwargs["reasoning_content"] = _dict["reasoning_content"]
    return msg


_lc_base._convert_delta_to_message_chunk = _convert_delta_to_message_chunk_with_reasoning


# ==================== 补丁 2: 回传 reasoning_content ====================
# 在 _get_request_payload 中注入 reasoning_content 到 API 请求。


def _inject_reasoning(msg_dict: dict, original_msg: BaseMessage) -> dict:
    if (
        isinstance(original_msg, AIMessage)
        and "reasoning_content" in original_msg.additional_kwargs
        and "reasoning_content" not in msg_dict
    ):
        msg_dict["reasoning_content"] = original_msg.additional_kwargs["reasoning_content"]
    return msg_dict


class ChatMiMo(ChatOpenAI):
    """自定义 MiMo Chat 模型，自动处理 reasoning_content 回传。"""

    def _get_request_payload(
        self,
        input_: Any,
        *,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> dict:
        messages = self._convert_input(input_).to_messages()
        if stop is not None:
            kwargs["stop"] = stop

        payload = {**self._default_params, **kwargs}
        payload["messages"] = [
            _inject_reasoning(
                _convert_message_to_dict(
                    _convert_from_v1_to_chat_completions(m) if isinstance(m, AIMessage) else m
                ),
                m,
            )
            for m in messages
        ]
        return payload

    @property
    def _llm_type(self) -> str:
        return "chat-mimo"


def get_mimo_llm(temperature: float = 0.7, streaming: bool = False) -> ChatMiMo:
    """获取封装了 MiMo API 的 LangChain LLM 实例。"""
    return ChatMiMo(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        temperature=temperature,
        streaming=streaming,
    )
