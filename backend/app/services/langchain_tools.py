"""
LangChain Agent 工具模块

定义 Agent 可调用的工具。每个工具用 @tool 装饰器定义。

学习点：
  - @tool 装饰器：将普通函数转为 LangChain Tool 对象
  - docstring = 工具描述：Agent 靠它决定何时调用此工具，所以要写清楚
    "什么时候用这个工具" + "这个工具做什么"
  - 函数参数 = 工具参数：类型标注会自动生成 JSON Schema 给 LLM
  - 返回值必须是 str：Agent 需要文本形式的结果来继续推理
"""

import re

from langchain_core.tools import tool
from sqlalchemy import text

from app.services.embedding import get_embeddings
from app.services.vector_store import search as vector_search
from app.core.database import SessionLocal


@tool
def rag_search(query: str) -> str:
    """当用户询问与知识库中的文档、资料、规章制度相关的问题时，使用此工具搜索知识库。
    输入应该是用户的原始问题，工具会自动向量化并在知识库中搜索最相关的内容。"""
    try:
        embeddings = get_embeddings([query])
        if not embeddings:
            return "向量化失败，无法搜索知识库。"
        chunks = vector_search(kb_id=1, query_embedding=embeddings[0], top_k=5)
        if not chunks:
            return "知识库中没有找到相关内容。"
        return "\n\n---\n\n".join(chunks)
    except Exception as e:
        return f"知识库搜索出错：{str(e)}"


@tool
def db_query(sql: str) -> str:
    """当用户需要查询数据库中的数据时，使用此工具执行 SQL 查询。
    仅支持 SELECT 查询。可用于查询用户信息、统计数据、对话记录等。
    输入应该是完整的 SQL SELECT 语句。"""
    sql_stripped = sql.strip()
    sql_upper = sql_stripped.upper()

    if not sql_upper.startswith("SELECT"):
        return "错误：只允许 SELECT 查询语句。"

    for kw in ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE"]:
        if re.search(r'\b' + kw + r'\b', sql_upper):
            return f"错误：禁止使用 {kw} 语句。"

    try:
        db = SessionLocal()
        try:
            result = db.execute(text(sql_stripped))
            rows = result.fetchall()
            if not rows:
                return "查询结果为空。"
            columns = list(result.keys())
            rows = rows[:20]
            lines = [" | ".join(columns)]
            lines.append("-" * len(lines[0]))
            for row in rows:
                lines.append(" | ".join(str(v) if v is not None else "NULL" for v in row))
            return "\n".join(lines)
        finally:
            db.close()
    except Exception as e:
        return f"数据库查询出错：{str(e)}"


@tool
def web_search(query: str) -> str:
    """当用户需要查询实时信息、新闻、天气、或知识库和数据库中没有的信息时，使用此工具搜索互联网。
    输入应该是简洁的搜索关键词或问题。"""
    try:
        from langchain_community.tools import DuckDuckGoSearchRun
        search = DuckDuckGoSearchRun()
        result = search.run(query)
        if not result:
            return "未找到相关搜索结果。"
        return result
    except Exception as e:
        return f"网页搜索出错：{str(e)}"
