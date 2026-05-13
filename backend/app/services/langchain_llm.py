"""
LangChain MiMo LLM 封装模块

使用 LangChain 的 ChatOpenAI 类对接小米 MiMo API（OpenAI 兼容接口）。

学习点：
  - ChatOpenAI：LangChain 对 OpenAI 兼容 LLM 的封装
    它内部管理 API 调用、消息格式转换、流式处理等细节
  - 通过 base_url 参数可以指向任何 OpenAI 兼容的 API 端点
  - streaming=True 让模型支持逐 token 输出，Agent 的流式功能依赖于此
"""

from langchain_openai import ChatOpenAI

from app.core.config import settings


def get_mimo_llm(temperature: float = 0.7, streaming: bool = False) -> ChatOpenAI:
    """
    获取封装了 MiMo API 的 LangChain LLM 实例。

    参数：
        temperature: 控制输出随机性（0.0~2.0），默认 0.7
        streaming: 是否启用流式输出，默认 False

    返回：
        ChatOpenAI 实例，可以像 LangChain 中的其他 LLM 一样使用

    用法示例：
        llm = get_mimo_llm()
        response = llm.invoke("你好")  # 普通调用

        llm = get_mimo_llm(streaming=True)
        for chunk in llm.stream("你好"):  # 流式调用
            print(chunk.content, end="")
    """
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        temperature=temperature,
        streaming=streaming,
    )
