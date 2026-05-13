"""
对话相关的 Pydantic 模型（请求/响应 schema）

Pydantic 模型的作用：
  - 定义 API 的请求体和响应体的数据结构
  - FastAPI 会自动根据这些模型进行请求参数校验和响应序列化
  - 生成 OpenAPI/Swagger 文档中的请求/响应示例
"""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """
    对话请求模型

    字段说明：
      - question: 用户提出的问题（必填）
      - kb_id:     可选的知识库 ID
                   - 如果指定了 kb_id，对话会走 RAG 流程（检索知识库 → 拼装上下文 → 交给 LLM 回答）
                   - 如果不指定（为 None），则直接将问题交给 LLM 回答（不检索任何知识库）
    """
    question: str                # 用户的问题（必填）
    kb_id: int | None = None     # 可选的知识库 ID，不选则直接问 LLM（不走 RAG）
    session_id: int | None = None  # 可选的会话 ID，用于多轮对话上下文
    mode: str = "normal"  # "normal" 走现有流程，"agent" 走 LangChain Agent


class ChatResponse(BaseModel):
    """
    对话响应模型

    字段说明：
      - answer: AI 生成的回答文本
      - kb_id:  本次对话使用了哪个知识库（如果有的话）
    """
    answer: str                  # AI 的回答
    kb_id: int | None = None     # 使用的知识库 ID
