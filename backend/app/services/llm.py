"""LLM 调用服务：支持普通调用和流式输出（SSE）。"""

from openai import OpenAI

from app.core.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)


def chat_completion(
    messages: list[dict], model: str | None = None, temperature: float = 0.3
) -> tuple[str, str]:
    """调用 LLM，返回 (reasoning_content, answer)。"""
    response = client.chat.completions.create(
        model=model or settings.OPENAI_MODEL,
        messages=messages,
        temperature=temperature,
    )
    msg = response.choices[0].message
    reasoning = getattr(msg, "reasoning_content", None) or ""
    answer = msg.content or ""
    return reasoning, answer


def chat_completion_stream(
    messages: list[dict], model: str | None = None, temperature: float = 0.3
):
    """流式调用 LLM，yield {"type": "reasoning"|"answer", "content": ...}。"""
    response = client.chat.completions.create(
        model=model or settings.OPENAI_MODEL,
        messages=messages,
        temperature=temperature,
        stream=True,
    )

    for chunk in response:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        reasoning = getattr(delta, "reasoning_content", None)
        if reasoning:
            yield {"type": "reasoning", "content": reasoning}
        elif delta.content:
            yield {"type": "answer", "content": delta.content}


def generate_title(question: str, answer: str) -> str:
    """根据第一轮对话生成不超过 20 字的会话标题。"""
    prompt = (
        "请用不超过20个字概括以下对话的主题，只输出标题，不要加引号：\n"
        f"用户问：{question}\n"
        f"AI答：{answer}"
    )
    _, title = chat_completion([{"role": "user", "content": prompt}])
    return title.strip().strip('"').strip("'").strip("「」").strip("“”")[:50]


def generate_summary(conversations: list[dict]) -> str:
    """对多轮对话生成 200 字以内的摘要。"""
    history_text = ""
    for conv in conversations:
        role_label = "用户" if conv["role"] == "user" else "AI"
        history_text += f"{role_label}：{conv['content']}\n\n"

    prompt = f"请用简洁的语言概括以下对话的主要内容和结论，控制在200字以内：\n\n{history_text}"
    _, summary = chat_completion([{"role": "user", "content": prompt}])
    return summary
