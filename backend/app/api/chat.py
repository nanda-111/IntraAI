"""
对话 API 路由模块

提供两种对话接口：
  1. 普通对话（POST /api/chat/）     — 一次性返回完整回答
  2. 流式对话（POST /api/chat/stream）— 通过 SSE 协议逐字/逐段返回回答

========================================
流式 vs 非流式的使用场景
========================================
  - 非流式（普通对话）：
      适用于简单场景，前端拿到完整回答后再渲染。
      缺点是用户需要等待较长时间（LLM 生成 1000 字可能需要几秒），体验像"转圈等待"。

  - 流式对话：
      适用于需要实时反馈的场景。LLM 边生成边返回，前端可以像 ChatGPT 那样逐字显示。
      用户体验更好，减少了"等待焦虑"。

========================================
SSE（Server-Sent Events）协议格式
========================================
  SSE 是一种基于 HTTP 的服务端推送协议，格式非常简单：
    - 每条消息以 "data: " 开头
    - 每条消息以 "\n\n"（两个换行符）结尾
    - 例如：data: 你好\n\n
    - 特殊标记 "data: [DONE]\n\n" 表示流结束

  前端接收方式（两种）：
    1. EventSource API（仅支持 GET，不适用于 POST）
    2. fetch + ReadableStream（支持 POST，更通用）：
       const response = await fetch('/api/chat/stream', {
         method: 'POST',
         headers: { 'Content-Type': 'application/json' },
         body: JSON.stringify({ question: '你好' }),
       });
       const reader = response.body.getReader();
       // 逐块读取...

========================================
为什么流式接口也保存对话记录？
========================================
  虽然流式接口的响应是"流"式的，但生成器函数内部会累积完整的回答文本。
  流结束后，完整回答会被保存到 Conversation 表中。
  这样做的好处：
    1. 用户可以在对话历史中查看完整的对话内容
    2. 方便后续做对话上下文管理（多轮对话需要历史记录）
    3. 便于做数据分析和审计
"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.conversation import Conversation
from app.models.usage_log import UsageLog
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rag import ask_with_rag
from app.services.llm import chat_completion

# 创建对话路由，统一前缀为 /api/chat
router = APIRouter(prefix="/api/chat", tags=["对话"])


@router.post("/", response_model=ChatResponse)
def chat(
    data: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    普通对话接口（返回完整回答）

    工作流程：
      1. 如果指定了 kb_id，走 RAG 流程：
         - 从知识库中检索与问题相关的文档片段
         - 将检索到的片段作为上下文，连同问题一起交给 LLM 生成回答
      2. 如果未指定 kb_id，直接将问题交给 LLM 回答
      3. 将对话记录保存到数据库（Conversation 表）
      4. 记录用量日志（UsageLog 表），用于统计和审计
      5. 返回完整回答
    """
    # 判断是否走 RAG 流程
    if data.kb_id:
        # 指定了知识库：从知识库检索相关文档，结合上下文生成回答
        answer = ask_with_rag(data.question, data.kb_id)
    else:
        # 未指定知识库：直接将问题交给 LLM（不检索任何知识库）
        answer = chat_completion([
            {"role": "user", "content": data.question}
        ])

    # 保存对话记录到数据库
    # Conversation 表存储了用户与 AI 的每一轮对话，便于后续查看历史
    conv = Conversation(
        user_id=current_user.id,    # 关联到当前登录用户
        kb_id=data.kb_id,           # 关联到使用的知识库（可为 None）
        question=data.question,     # 用户的问题
        answer=answer,              # AI 的回答
    )
    db.add(conv)

    # 记录用量日志
    # UsageLog 用于统计用户的 API 调用次数，可用于计费或限流
    log = UsageLog(user_id=current_user.id, action="chat")
    db.add(log)

    # 提交事务，将上述两条记录写入数据库
    db.commit()

    # 返回对话响应
    return ChatResponse(answer=answer, kb_id=data.kb_id)


@router.post("/stream")
def chat_stream(
    data: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    流式对话接口（逐字返回回答）

    使用 StreamingResponse 实现服务端推送。

    ========================================
    StreamingResponse 的工作原理
    ========================================
      1. StreamingResponse 接受一个"生成器函数"作为参数
      2. 生成器函数使用 yield 逐段产出数据（而不是 return 一次性返回）
      3. FastAPI/Starlette 框架会将 yield 的每段数据立即发送给客户端
      4. 客户端收到数据后可以立即渲染，无需等待整个响应完成
      5. 这实现了"边生成边返回"的效果，用户可以看到 AI 逐字输出

      对比普通响应：
        - 普通响应：函数 return 一个对象 → 框架序列化 → 一次性发送给客户端
        - 流式响应：生成器 yield → 框架立即发送 → 再 yield → 再发送 → ...

    media_type="text/event-stream" 告诉浏览器这是 SSE 流，
    浏览器会按照 SSE 协议格式解析每条消息。
    """

    def generate():
        """
        生成器函数 — 每次 yield 一小段文本。

        SSE（Server-Sent Events）协议格式：
          - 每条消息以 "data: " 开头，以 "\\n\\n" 结尾
          - 前端通过 EventSource 或 fetch + ReadableStream 接收
          - 发送 "data: [DONE]\\n\\n" 表示流结束

        生成器执行过程：
          1. LLM 服务返回一个迭代器（iterator），每次产出一小段文本
          2. 我们将这段文本用 SSE 格式包装后 yield 出去
          3. 框架立即发送给客户端
          4. 累积完整回答，用于最后保存对话记录
        """
        full_answer = ""  # 累积完整回答，用于保存对话记录

        if data.kb_id:
            # RAG 流式版本：检索知识库 + 流式生成回答
            from app.services.rag import ask_with_rag_stream
            for chunk in ask_with_rag_stream(data.question, data.kb_id):
                full_answer += chunk
                # 用 SSE 格式包装每段文本并发送
                yield f"data: {chunk}\n\n"
        else:
            # 直接问 LLM 的流式版本（不检索知识库）
            from app.services.llm import chat_completion_stream as llm_stream
            for chunk in llm_stream([
                {"role": "user", "content": data.question}
            ]):
                full_answer += chunk
                # 用 SSE 格式包装每段文本并发送
                yield f"data: {chunk}\n\n"

        # 流结束标记 — 告诉前端"数据已经全部发送完毕"
        yield "data: [DONE]\n\n"

        # ==================== 保存对话记录 ====================
        # 注意：这段代码在生成器函数内部，在流结束之后执行。
        # 为什么流式接口也保存对话记录？
        #   - 用户可以在对话历史中查看完整的对话内容
        #   - 方便后续做多轮对话（需要引用历史上下文）
        #   - 便于数据分析、审计和计费
        conv = Conversation(
            user_id=current_user.id,
            kb_id=data.kb_id,
            question=data.question,
            answer=full_answer,  # 累积的完整回答
        )
        db.add(conv)

        # 记录用量日志
        log = UsageLog(user_id=current_user.id, action="chat")
        db.add(log)
        db.commit()

    # 返回 StreamingResponse，将生成器包装为 HTTP 流式响应
    # media_type="text/event-stream" 表示这是 SSE（Server-Sent Events）流
    return StreamingResponse(generate(), media_type="text/event-stream")
