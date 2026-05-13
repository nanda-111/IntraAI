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


def chat_completion(messages: list[dict], model: str | None = None) -> str:
    """
    调用大语言模型，获取完整的回答文本。

    这是普通（非流式）调用方式，适用于：
      - 不需要实时展示的后台任务（如文档摘要、文本分析）
      - 需要完整回答后再做后续处理的场景
      - 对响应时间不敏感的简单查询

    参数：
        messages: 对话消息列表，格式如：
            [
                {"role": "system", "content": "你是一个助手"},
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "你好！有什么可以帮助你的？"},
                {"role": "user", "content": "介绍一下你自己"},
            ]
        model: 使用的模型名称，默认使用配置中的 OPENAI_MODEL（如 gpt-4o-mini）

    返回：
        AI 的完整回答文本（字符串）

    关于 temperature 参数：
      - temperature 控制模型输出的随机程度，取值范围通常为 0.0 ~ 2.0
      - temperature = 0：输出最确定、最稳定，适合需要精确答案的场景（如代码生成）
      - temperature = 0.7：适中的随机性，平衡创造性和准确性（本模块使用的默认值）
      - temperature = 1.0+：输出更多样化、更有创意，但可能不够准确
      - 工作原理：temperature 影响 token 概率分布的平滑程度
        temperature 越高，低概率 token 被选中的机会越大，输出越多样化
    """
    response = client.chat.completions.create(
        model=model or settings.OPENAI_MODEL,
        messages=messages,
        temperature=0.7,  # 中等随机性，兼顾回答质量和多样性
    )
    # response.choices 是返回的候选回答列表（通常只有一个）
    # .message.content 是回答的文本内容
    return response.choices[0].message.content


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
        stream=True,  # 启用流式输出，API 将以 SSE 事件流的方式返回数据
    )

    # 遍历流式响应中的每个 chunk（数据块）
    # 每个 chunk 包含一个 delta（增量），即新生成的一小段文本
    for chunk in response:
        # chunk.choices[0].delta.content 是当前 chunk 的增量文本内容
        # 注意：某些 chunk 的 content 可能为 None（如表示流结束的最后一个 chunk）
        # 因此需要先判断是否为 None，避免将 None yield 出去
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


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
    title = chat_completion([{"role": "user", "content": prompt}])
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

    prompt = (
        "请用简洁的语言概括以下对话的主要内容和结论，控制在200字以内：\n\n"
        f"{history_text}"
    )
    return chat_completion([{"role": "user", "content": prompt}])
