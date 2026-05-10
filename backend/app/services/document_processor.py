"""
文档解析与文本切片服务

功能：
  - 从 PDF/Word/TXT/Markdown 文件中提取纯文本
  - 将长文本按固定长度切分为多个小片段（chunk），相邻片段之间有重叠

这是 RAG（检索增强生成）系统的核心步骤：
  1. 文档上传 → 提取文本 → 切分为小片段
  2. 每个小片段通过 Embedding 模型转化为向量
  3. 用户提问时，检索最相关的片段，交给大模型生成回答
"""

import os
import fitz  # PyMuPDF — 用于解析 PDF 文件（需安装：pip install PyMuPDF）
from docx import Document as DocxDocument  # python-docx — 用于解析 .docx 文件（需安装：pip install python-docx）


def extract_text(filepath: str, file_type: str) -> str:
    """
    根据文件类型提取文本内容。

    参数：
        filepath: 文件的完整路径
        file_type: 文件类型，支持 pdf / docx / txt / md

    返回：
        提取出的纯文本字符串
    """
    if file_type == "pdf":
        return _extract_pdf(filepath)
    elif file_type == "docx":
        return _extract_docx(filepath)
    elif file_type in ("txt", "md"):
        return _extract_text_file(filepath)
    else:
        raise ValueError(f"不支持的文件类型: {file_type}")


def _extract_pdf(filepath: str) -> str:
    """
    提取 PDF 文件中的文本。

    PyMuPDF (fitz) 的工作机制：
      - fitz.open() 打开 PDF 文件，返回一个 Document 对象
        （底层解析 PDF 的二进制结构，提取文本、图片、字体等信息）
      - Document 对象可按页迭代，每一页是一个 Page 对象
      - page.get_text() 从当前页面中提取所有可见文本
        （它会按照 PDF 内部的文本绘制顺序来拼接文字，因此可能偶尔出现顺序问题）
      - 最后将所有页面的文本用换行符连接，保留原始的页面分隔
    """
    doc = fitz.open(filepath)
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts)


def _extract_docx(filepath: str) -> str:
    """
    提取 Word (.docx) 文件中的文本。

    python-docx 的工作机制：
      - .docx 文件本质上是一个 ZIP 压缩包，内部包含多个 XML 文件
        （你可以将 .docx 后缀改为 .zip 后用解压工具查看其内部结构）
      - DocxDocument() 解析这个 ZIP 包，读取 word/document.xml 中的段落和表格信息
      - document.paragraphs 是一个列表，包含文档中的所有段落对象
      - 每个段落的 .text 属性就是该段落的纯文本内容
      - 使用 strip() 过滤掉空段落（有些段落仅用于排版，不含实际文字）
    """
    doc = DocxDocument(filepath)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _extract_text_file(filepath: str) -> str:
    """
    读取纯文本文件（TXT 或 Markdown）。

    这是最简单的情况：直接按 UTF-8 编码读取文件内容即可。
    使用 UTF-8 编码是因为它兼容 ASCII，且能正确处理中文等多字节字符。
    如果遇到编码问题，可以考虑改用 chardet 库自动检测编码。
    """
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def split_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    将长文本切分为多个小片段（chunk），相邻片段之间有重叠。

    ---- 为什么需要切片？ ----
    1. Embedding API 对单次输入有长度限制（例如 OpenAI 的 text-embedding-ada-002 最多 8191 个 token）
       如果直接将整篇文档送入，可能会超长导致报错
    2. 小片段的向量表示更精确：一个向量最好只编码一个主题/段落的信息
       如果一个向量包含太多内容，检索时的语义匹配精度会下降
    3. 检索时只需返回最相关的几个片段，而不是整个文档，节省上下文窗口

    ---- overlap 的作用 ----
    相邻片段之间保留 overlap 个字符的重叠区域，目的是：
    - 防止关键句子在切片边界被切断，导致语义丢失
    - 例如："今天天气很好。我们决定去公园。" 如果刚好在"。"处切开，
      第一个片段可能只看到"今天天气很好"，第二个片段只看到"我们决定去公园"。
      有了 overlap，两个片段都会包含完整的一句话。

    参数：
        text: 原始文本
        chunk_size: 每个片段的最大字符数（默认 500）
        overlap: 相邻片段之间的重叠字符数（默认 50）

    工作原理（以 text="ABCDEFGHIJ", chunk_size=5, overlap=2 为例）：
      第 1 片：text[0:5] = "ABCDE"，下一个起点 = 5 - 2 = 3
      第 2 片：text[3:8] = "DEFGH"，下一个起点 = 8 - 2 = 6
      第 3 片：text[6:11] = "GHIJ"（文本末尾，不足 chunk_size 就取剩余部分）

    返回：
        切分后的片段列表，每个元素是一个非空字符串
    """
    # 空文本或纯空白文本直接返回空列表，避免产生无意义的空片段
    if not text.strip():
        return []

    # 防止 overlap >= chunk_size 导致死循环：overlap 必须小于 chunk_size
    if overlap >= chunk_size:
        overlap = chunk_size - 1

    chunks = []
    start = 0  # 当前片段的起始位置
    while start < len(text):
        # 计算当前片段的结束位置
        end = start + chunk_size
        # 截取 [start, end) 范围内的文本
        chunk = text[start:end].strip()
        # strip() 的必要性：由于 overlap 机制，某些片段的开头可能包含
        # 上一片尾部的空白字符（如换行符、空格），strip() 可以去除这些
        # 不影响语义的多余空白，保证每个片段都是干净的纯文本
        if chunk:
            chunks.append(chunk)
        # 如果当前片段已经覆盖到文本末尾（或超出），无需再切，结束循环
        if end >= len(text):
            break
        # 下一个片段的起点 = 当前终点 - overlap
        # 这样相邻两个片段之间就有 overlap 个字符的重叠区域
        start = end - overlap
    return chunks
