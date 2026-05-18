"""
大语言模型（LLM）调用服务模块

功能：封装对大语言模型的调用，支持普通调用和流式输出两种模式。

什么是大语言模型（LLM）？
  - LLM 是基于海量文本数据训练的深度学习模型，能够理解和生成自然语言
  - 典型应用包括：对话问答、文本摘要、代码生成、翻译等
  - 本项目使用 OpenAI 兼容的 Chat Completions API 进行调用

Chat Completions API 请求格式：
  - endpoint: POST /v1/chat/completions
  - 请求体包含：
    - model: 模型名称（如 gpt-4o-mini）
    - messages: 对话消息列表，每条消息包含 role 和 content
    - temperature: 控制输出随机性的参数
    - stream: 是否启用流式输出

三种消息角色的区别：
  - system（系统消息）：设定 AI 的角色、行为规范和知识范围
    例："你是一个专业的法律顾问，请用正式的语言回答"
  - user（用户消息）：用户的输入，即用户对 AI 说的话
    例："请解释一下什么是知识产权"
  - assistant（助手消息）：AI 的历史回复，用于多轮对话的上下文
    例：上一轮 AI 的回答，帮助 AI 理解对话的连贯性

流式输出（Streaming）的工作原理：
  - 普通调用：客户端发送请求后，服务端等待 AI 完全生成所有文本后一次性返回
    优点：逻辑简单，拿到完整结果直接处理
    缺点：长文本生成时用户等待时间长，体验差
  - 流式调用：使用 SSE（Server-Sent Events）协议，服务端边生成边返回增量文本
    优点：用户可以实时看到 AI 的回复逐字出现，类似打字效果
    缺点：需要处理流式数据，前端也要相应适配
  - SSE 协议：基于 HTTP 的单向推送协议，服务端通过
    Content-Type: text/event-stream 向客户端持续推送数据

使用方式：
    from app.services.llm import chat_completion, chat_completion_stream

    # 普通调用：获取完整回答
    answer = chat_completion([{"role": "user", "content": "你好"}])

    # 流式调用：逐段获取回答
    for chunk in chat_completion_stream([{"role": "user", "content": "你好"}]):
        print(chunk, end="")
"""

from openai import OpenAI

from app.core.config import settings

# 创建 OpenAI 客户端实例（与 embedding.py 共享相同的配置）
# 两个服务使用同一个 API Key 和 Base URL，便于统一管理
client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)


def chat_completion(messages: list[dict], model: str | None = None) -> tuple[str, str]:
    response = client.chat.completions.create(
        model=model or settings.OPENAI_MODEL,
        messages=messages,
        temperature=0.7,
    )
    msg = response.choices[0].message
    reasoning = getattr(msg, "reasoning_content", None) or ""
    answer = msg.content or ""
    return reasoning, answer


def chat_completion_stream(messages: list[dict], model: str | None = None):
    """
    流式调用大语言模型，以生成器的形式逐段返回回答。

    这是流式调用方式，适用于：
      - 聊天对话场景，用户希望实时看到 AI 的回复
      - 长文本生成，避免长时间等待
      - 前端配合 SSE 或 WebSocket 实现打字效果

    流式调用与普通调用的关键区别：
      - 普通调用：stream=False（默认），返回完整响应对象
      - 流式调用：stream=True，返回一个可迭代的事件流

    关于 yield 和生成器（Generator）：
      - yield 是 Python 中定义生成器函数的关键字
      - 普通函数用 return 返回一个值后函数就结束了
      - 生成器函数用 yield 可以产生多个值，每次产生后函数暂停，下次调用时继续执行
      - 使用方式：for chunk in chat_completion_stream(...): 处理每个 chunk
      - 优势：不需要等待所有数据生成完毕，节省内存，实现惰性求值

    参数：
        messages: 对话消息列表，格式与 chat_completion 相同
        model: 使用的模型名称，默认使用配置中的 OPENAI_MODEL

    生成器 yield 的内容：
        每次 yield 一小段文本增量（通常是几个字符到一个句子）
        调用方需要将这些增量拼接起来得到完整回答
    """
    response = client.chat.completions.create(
        model=model or settings.OPENAI_MODEL,
        messages=messages,
        temperature=0.7,
        stream=True,
    )

    for chunk in response:
        delta = chunk.choices[0].delta
        reasoning = getattr(delta, "reasoning_content", None)
        if reasoning:
            yield {"type": "reasoning", "content": reasoning}
        elif delta.content:
            yield {"type": "answer", "content": delta.content}


def generate_title(question: str, answer: str) -> str:
    """
    根据第一轮对话生成会话标题。

    参数：
        question: 用户的问题
        answer: AI 的回答

    返回：
        不超过20个字的标题
    """
    prompt = (
        "请用不超过20个字概括以下对话的主题，只输出标题，不要加引号：\n"
        f"用户问：{question}\n"
        f"AI答：{answer}"
    )
    _, title = chat_completion([{"role": "user", "content": prompt}])
    return title.strip().strip('"').strip("'").strip("「」").strip("“”")[:50]


def generate_summary(conversations: list[dict]) -> str:
    """
    对多轮对话生成摘要。

    参数：
        conversations: 对话列表，每项包含 role 和 content

    返回：
        摘要文本
    """
    history_text = ""
    for conv in conversations:
        role_label = "用户" if conv["role"] == "user" else "AI"
        history_text += f"{role_label}：{conv['content']}\n\n"

    prompt = f"请用简洁的语言概括以下对话的主要内容和结论，控制在200字以内：\n\n{history_text}"
    _, summary = chat_completion([{"role": "user", "content": prompt}])
    return summary
