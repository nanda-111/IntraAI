# RAG 文本切分与元数据优化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 优化文档切分策略（结构感知 + 语义切分混合方案），增强 chunk 元数据（页码、标题路径、字符偏移等）

**Architecture:** 在 `document_processor.py` 中新增页面感知提取、标题检测、结构感知切分、语义切分四个模块，通过 `split_document` 统一入口自动选择切分策略。保持旧接口 `extract_text` / `split_text` 向后兼容。上传端点改用新流水线，元数据写入 ChromaDB。

**Tech Stack:** PyMuPDF (fitz), sentence-transformers, numpy, pytest, unittest.mock

---

## 文件结构

### 新增文件
- `backend/tests/test_chunking_strategy.py` — 切分策略集成测试（标题检测、结构切分、语义切分、混合策略、页码追踪）

### 修改文件
- `backend/app/services/document_processor.py` — 新增页面提取、标题检测、结构切分、语义切分、统一入口
- `backend/app/api/documents.py` — 上传流水线改用 `split_document`，传递增强元数据

---

## Task 1: 页面感知文本提取（PDF 页码追踪）

**Files:**
- Modify: `backend/app/services/document_processor.py`
- Test: `backend/tests/test_chunking_strategy.py`

- [ ] **Step 1: 编写页面感知提取测试**

创建 `backend/tests/test_chunking_strategy.py`：

```python
"""RAG 文本切分策略测试"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest


class TestExtractTextWithPages:
    """extract_text_with_pages 函数测试"""

    @patch("app.services.document_processor.fitz")
    def test_pdf_tracks_page_numbers(self, mock_fitz):
        """PDF 提取应返回每段文本对应的页码"""
        from app.services.document_processor import extract_text_with_pages

        mock_page1 = MagicMock()
        mock_page1.get_text.return_value = "第一页内容。"
        mock_page2 = MagicMock()
        mock_page2.get_text.return_value = "第二页内容。"

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page1, mock_page2]))
        mock_doc.close = MagicMock()
        mock_fitz.open.return_value = mock_doc

        result = extract_text_with_pages("test.pdf", "pdf")

        assert len(result) == 2
        assert result[0] == ("第一页内容。", 1)
        assert result[1] == ("第二页内容。", 2)
        mock_doc.close.assert_called_once()

    def test_txt_returns_page_1(self):
        """TXT 文件所有文本归为第 1 页"""
        from app.services.document_processor import extract_text_with_pages

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("纯文本内容")
            filepath = f.name

        try:
            result = extract_text_with_pages(filepath, "txt")
            assert len(result) == 1
            assert result[0][0] == "纯文本内容"
            assert result[0][1] == 1
        finally:
            os.unlink(filepath)

    def test_docx_returns_page_1(self):
        """DOCX 文件所有文本归为第 1 页（DOCX 无精确页码）"""
        from app.services.document_processor import extract_text_with_pages

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".docx", delete=False, encoding="utf-8"
        ) as f:
            f.write("dummy")
            filepath = f.name

        try:
            with patch("app.services.document_processor.DocxDocument") as mock_docx:
                mock_para = MagicMock()
                mock_para.text = "Word 内容"
                mock_doc = MagicMock()
                mock_doc.paragraphs = [mock_para]
                mock_docx.return_value = mock_doc

                result = extract_text_with_pages(filepath, "docx")
                assert len(result) == 1
                assert result[0][0] == "Word 内容"
                assert result[0][1] == 1
        finally:
            os.unlink(filepath)

    def test_unsupported_type_raises(self):
        """不支持的文件类型应抛出 ValueError"""
        from app.services.document_processor import extract_text_with_pages

        with pytest.raises(ValueError, match="不支持"):
            extract_text_with_pages("test.xyz", "xyz")
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd F:/IntraAI && python -m pytest backend/tests/test_chunking_strategy.py::TestExtractTextWithPages -v --tb=short 2>&1 | tail -15
```

预期：`AttributeError: module has no attribute 'extract_text_with_pages'`

- [ ] **Step 3: 实现 extract_text_with_pages**

在 `backend/app/services/document_processor.py` 中，在 `extract_text` 函数之后添加：

```python
def extract_text_with_pages(filepath: str, file_type: str) -> list[tuple[str, int]]:
    """
    提取文本并追踪每段文本的页码。

    返回：
        [(文本段落, 页码), ...] 列表。页码从 1 开始。
        非 PDF 文件所有文本归为第 1 页。
    """
    if file_type == "pdf":
        return _extract_pdf_with_pages(filepath)
    elif file_type == "docx":
        text = _extract_docx(filepath)
        return [(text, 1)] if text.strip() else []
    elif file_type in ("txt", "md"):
        text = _extract_text_file(filepath)
        return [(text, 1)] if text.strip() else []
    else:
        raise ValueError(f"不支持的文件类型: {file_type}")


def _extract_pdf_with_pages(filepath: str) -> list[tuple[str, int]]:
    """提取 PDF 文本，保留页码信息。"""
    doc = fitz.open(filepath)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text().strip()
        if text:
            pages.append((text, i + 1))
    doc.close()
    return pages
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd F:/IntraAI && python -m pytest backend/tests/test_chunking_strategy.py::TestExtractTextWithPages -v --tb=short 2>&1 | tail -15
```

预期：4 个测试全部 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/document_processor.py backend/tests/test_chunking_strategy.py
git commit -m "feat: add page-aware text extraction for PDF documents"
```

---

## Task 2: 标题检测

**Files:**
- Modify: `backend/app/services/document_processor.py`
- Test: `backend/tests/test_chunking_strategy.py`

- [ ] **Step 1: 编写标题检测测试**

在 `backend/tests/test_chunking_strategy.py` 末尾添加：

```python
class TestDetectHeaders:
    """_detect_header 和 _is_header_line 函数测试"""

    def test_chinese_chapter_header(self):
        """检测中文章节标题"""
        from app.services.document_processor import _is_header_line

        assert _is_header_line("第一章 总则") is True
        assert _is_header_line("第二章 薪酬制度") is True
        assert _is_header_line("第三节 绩效考核") is True

    def test_numbered_header(self):
        """检测数字编号标题"""
        from app.services.document_processor import _is_header_line

        assert _is_header_line("1. 概述") is True
        assert _is_header_line("2.3 薪资结构") is True
        assert _is_header_line("3.1.2 细则") is True

    def test_markdown_header(self):
        """检测 Markdown 标题"""
        from app.services.document_processor import _is_header_line

        assert _is_header_line("# 一级标题") is True
        assert _is_header_line("## 二级标题") is True
        assert _is_header_line("### 三级标题") is True

    def test_non_header_text(self):
        """普通文本不应被识别为标题"""
        from app.services.document_processor import _is_header_line

        assert _is_header_line("这是一段普通内容。") is False
        assert _is_header_line("员工应按时上下班。") is False
        assert _is_header_line("") is False

    def test_detect_headers_in_text(self):
        """从文本中提取所有标题及其位置"""
        from app.services.document_processor import _detect_headers

        text = "第一章 总则\n\n这是总则内容。\n\n第二章 制度\n\n制度内容。"
        headers = _detect_headers(text)

        assert len(headers) == 2
        assert headers[0][1] == "第一章 总则"
        assert headers[1][1] == "第二章 制度"

    def test_detect_headers_returns_offset(self):
        """标题检测应返回在原文中的字符偏移"""
        from app.services.document_processor import _detect_headers

        text = "前言内容。\n\n第一章 标题"
        headers = _detect_headers(text)

        assert len(headers) == 1
        offset = headers[0][0]
        assert text[offset : offset + 6] == "第一章 "

    def test_no_headers(self):
        """无标题文本应返回空列表"""
        from app.services.document_processor import _detect_headers

        text = "普通段落一。\n\n普通段落二。"
        headers = _detect_headers(text)
        assert headers == []
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd F:/IntraAI && python -m pytest backend/tests/test_chunking_strategy.py::TestDetectHeaders -v --tb=short 2>&1 | tail -15
```

预期：`AttributeError`

- [ ] **Step 3: 实现标题检测**

在 `backend/app/services/document_processor.py` 中，在 `_SENTENCE_ENDINGS` 之后添加：

```python
# 标题检测正则
_HEADER_PATTERNS = [
    re.compile(r"^第[一二三四五六七八九十百千万\d]+[章节篇部条]"),  # 第一章、第二节
    re.compile(r"^\d+(?:\.\d+)*[.\s]"),  # 1. / 2.3 / 3.1.2
    re.compile(r"^#{1,6}\s"),  # Markdown 标题
]


def _is_header_line(line: str) -> bool:
    """判断一行文本是否是标题。"""
    stripped = line.strip()
    if not stripped or len(stripped) > 80:
        return False
    return any(pat.match(stripped) for pat in _HEADER_PATTERNS)


def _detect_headers(text: str) -> list[tuple[int, str]]:
    """
    检测文本中所有标题及其字符偏移位置。

    返回：
        [(偏移位置, 标题文本), ...]
    """
    headers = []
    for match in re.finditer(r"[^\n]+", text):
        line = match.group()
        if _is_header_line(line):
            headers.append((match.start(), line.strip()))
    return headers
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd F:/IntraAI && python -m pytest backend/tests/test_chunking_strategy.py::TestDetectHeaders -v --tb=short 2>&1 | tail -15
```

预期：7 个测试全部 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/document_processor.py backend/tests/test_chunking_strategy.py
git commit -m "feat: add header detection for Chinese and Markdown documents"
```

---

## Task 3: 标题层级路径构建

**Files:**
- Modify: `backend/app/services/document_processor.py`
- Test: `backend/tests/test_chunking_strategy.py`

- [ ] **Step 1: 编写标题路径构建测试**

在 `backend/tests/test_chunking_strategy.py` 末尾添加：

```python
class TestBuildTitlePath:
    """_build_title_path 函数测试"""

    def test_single_header(self):
        """单个标题应返回自身"""
        from app.services.document_processor import _build_title_path

        headers = [(0, "第一章 总则")]
        text = "第一章 总则\n\n内容。"
        path = _build_title_path(text, 10, headers)
        assert path == "第一章 总则"

    def test_nested_headers(self):
        """嵌套标题应返回层级路径"""
        from app.services.document_processor import _build_title_path

        headers = [(0, "第二章 薪酬"), (15, "2.1 基本工资")]
        text = "第二章 薪酬\n\n2.1 基本工资\n\n内容。"
        path = _build_title_path(text, 25, headers)
        assert "第二章 薪酬" in path
        assert "2.1 基本工资" in path

    def test_content_before_any_header(self):
        """第一个标题之前的内容，路径为空字符串"""
        from app.services.document_processor import _build_title_path

        headers = [(10, "第一章 标题")]
        text = "前言内容。\n\n第一章 标题"
        path = _build_title_path(text, 2, headers)
        assert path == ""

    def test_no_headers(self):
        """无标题时返回空字符串"""
        from app.services.document_processor import _build_title_path

        path = _build_title_path("普通内容。", 0, [])
        assert path == ""
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd F:/IntraAI && python -m pytest backend/tests/test_chunking_strategy.py::TestBuildTitlePath -v --tb=short 2>&1 | tail -15
```

预期：`AttributeError`

- [ ] **Step 3: 实现标题路径构建**

在 `backend/app/services/document_processor.py` 中，在 `_detect_headers` 之后添加：

```python
def _build_title_path(text: str, char_offset: int, headers: list[tuple[int, str]]) -> str:
    """
    根据字符偏移位置，构建当前位置的标题层级路径。

    参数：
        text: 完整文本
        char_offset: 当前 chunk 在原文中的字符偏移
        headers: _detect_headers 返回的 [(偏移, 标题文本), ...]

    返回：
        标题层级路径，如 "第二章 薪酬 > 2.1 基本工资"
    """
    if not headers:
        return ""

    # 找到 offset 之前（含）的所有标题
    applicable = [(off, title) for off, title in headers if off <= char_offset]
    if not applicable:
        return ""

    return " > ".join(title for _, title in applicable)
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd F:/IntraAI && python -m pytest backend/tests/test_chunking_strategy.py::TestBuildTitlePath -v --tb=short 2>&1 | tail -15
```

预期：4 个测试全部 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/document_processor.py backend/tests/test_chunking_strategy.py
git commit -m "feat: add title hierarchy path builder for chunk metadata"
```

---

## Task 4: 结构感知递归切分

**Files:**
- Modify: `backend/app/services/document_processor.py`
- Test: `backend/tests/test_chunking_strategy.py`

- [ ] **Step 1: 编写结构感知切分测试**

在 `backend/tests/test_chunking_strategy.py` 末尾添加：

```python
class TestSplitByStructure:
    """_split_by_structure 函数测试"""

    def test_splits_at_header_boundary(self):
        """应在标题处分割"""
        from app.services.document_processor import _split_by_structure

        text = "第一章 内容一。\n\n第二章 内容二。"
        chunks = _split_by_structure(text, chunk_size=100)

        assert len(chunks) == 2
        assert "第一章" in chunks[0]["text"]
        assert "第二章" in chunks[1]["text"]

    def test_returns_metadata(self):
        """每个 chunk 应包含 text、title_path、char_offset"""
        from app.services.document_processor import _split_by_structure

        text = "# 标题\n\n段落内容。"
        chunks = _split_by_structure(text, chunk_size=100)

        assert len(chunks) >= 1
        chunk = chunks[0]
        assert "text" in chunk
        assert "title_path" in chunk
        assert "char_offset" in chunk

    def test_long_section_splits_by_paragraph(self):
        """标题下的长段落应继续按段落/句子切分"""
        from app.services.document_processor import _split_by_structure

        text = "第一章\n\n" + "很长的内容。" * 50
        chunks = _split_by_structure(text, chunk_size=50)

        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk["text"]) <= 50

    def test_no_headers_falls_back(self):
        """无标题时退化为普通段落切分"""
        from app.services.document_processor import _split_by_structure

        text = "段落一。\n\n段落二。\n\n段落三。"
        chunks = _split_by_structure(text, chunk_size=100)

        assert len(chunks) == 3
        for chunk in chunks:
            assert chunk["title_path"] == ""
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd F:/IntraAI && python -m pytest backend/tests/test_chunking_strategy.py::TestSplitByStructure -v --tb=short 2>&1 | tail -15
```

预期：`AttributeError`

- [ ] **Step 3: 实现结构感知切分**

在 `backend/app/services/document_processor.py` 中，在 `_build_title_path` 之后添加：

```python
def _split_by_structure(
    text: str, chunk_size: int = 500, overlap: int = 50
) -> list[dict]:
    """
    结构感知递归切分：按标题→段落→句子逐级切割。

    返回：
        [{"text": str, "title_path": str, "char_offset": int}, ...]
    """
    headers = _detect_headers(text)

    if not headers:
        # 无标题，退化为普通切分
        plain_chunks = split_text(text, chunk_size=chunk_size, overlap=overlap)
        result = []
        offset = 0
        for chunk in plain_chunks:
            idx = text.find(chunk, offset)
            actual_offset = idx if idx >= 0 else offset
            result.append({
                "text": chunk,
                "title_path": "",
                "char_offset": actual_offset,
            })
            offset = actual_offset + len(chunk)
        return result

    # 按标题分割文本为 sections
    sections = []
    for i, (offset, title) in enumerate(headers):
        end = headers[i + 1][0] if i + 1 < len(headers) else len(text)
        section_text = text[offset:end].strip()
        if section_text:
            sections.append((offset, title, section_text))

    # 处理标题之前的内容（前言）
    first_header_offset = headers[0][0]
    if first_header_offset > 0:
        preamble = text[:first_header_offset].strip()
        if preamble:
            sections.insert(0, (0, "", preamble))

    # 对每个 section 进行段落/句子级切分
    result = []
    for section_offset, _title, section_text in sections:
        sub_chunks = split_text(section_text, chunk_size=chunk_size, overlap=overlap)
        for chunk in sub_chunks:
            idx = section_text.find(chunk)
            actual_offset = section_offset + (idx if idx >= 0 else 0)
            title_path = _build_title_path(text, actual_offset, headers)
            result.append({
                "text": chunk,
                "title_path": title_path,
                "char_offset": actual_offset,
            })

    return result
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd F:/IntraAI && python -m pytest backend/tests/test_chunking_strategy.py::TestSplitByStructure -v --tb=short 2>&1 | tail -15
```

预期：4 个测试全部 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/document_processor.py backend/tests/test_chunking_strategy.py
git commit -m "feat: add structure-aware recursive document splitting"
```

---

## Task 5: 语义切分

**Files:**
- Modify: `backend/app/services/document_processor.py`
- Test: `backend/tests/test_chunking_strategy.py`

- [ ] **Step 1: 编写语义切分测试**

在 `backend/tests/test_chunking_strategy.py` 末尾添加：

```python
class TestSplitBySemantics:
    """_split_by_semantics 函数测试"""

    @patch("app.services.document_processor.get_embeddings")
    def test_splits_at_semantic_boundary(self, mock_embeddings):
        """语义差异大的相邻句子应在边界处切分"""
        from app.services.document_processor import _split_by_semantics

        # 模拟：前两句相似（薪酬相关），后两句相似（考勤相关），中间差异大
        def fake_embed(texts):
            result = []
            for t in texts:
                if "薪" in t or "工资" in t:
                    result.append([1.0] + [0.0] * 767)
                elif "考勤" in t or "打卡" in t:
                    result.append([0.0, 1.0] + [0.0] * 766)
                else:
                    result.append([0.5] * 768)
            return result

        mock_embeddings.side_effect = fake_embed

        sentences = [
            "基本工资按月发放。",
            "绩效工资根据考核结果确定。",
            "员工应每日打卡考勤。",
            "迟到早退将按制度处理。",
        ]
        text = "".join(sentences)
        chunks = _split_by_semantics(text, chunk_size=200)

        assert len(chunks) >= 2
        mock_embeddings.assert_called_once()

    @patch("app.services.document_processor.get_embeddings")
    def test_short_text_returns_single_chunk(self, mock_embeddings):
        """只有一个句子时返回单个 chunk"""
        from app.services.document_processor import _split_by_semantics

        mock_embeddings.return_value = [[0.1] * 768]

        chunks = _split_by_semantics("单句文本。", chunk_size=200)
        assert len(chunks) == 1
        assert chunks[0]["text"] == "单句文本。"

    @patch("app.services.document_processor.get_embeddings")
    def test_returns_metadata(self, mock_embeddings):
        """每个 chunk 应包含 text、title_path、char_offset"""
        from app.services.document_processor import _split_by_semantics

        mock_embeddings.return_value = [[0.1] * 768, [0.2] * 768]

        chunks = _split_by_semantics("句子一。句子二。", chunk_size=200)
        for chunk in chunks:
            assert "text" in chunk
            assert "title_path" in chunk
            assert "char_offset" in chunk
            assert chunk["title_path"] == ""

    @patch("app.services.document_processor.get_embeddings")
    def test_empty_text(self, mock_embeddings):
        """空文本返回空列表"""
        from app.services.document_processor import _split_by_semantics

        chunks = _split_by_semantics("", chunk_size=200)
        assert chunks == []
        mock_embeddings.assert_not_called()
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd F:/IntraAI && python -m pytest backend/tests/test_chunking_strategy.py::TestSplitBySemantics -v --tb=short 2>&1 | tail -15
```

预期：`AttributeError`

- [ ] **Step 3: 实现语义切分**

在 `backend/app/services/document_processor.py` 顶部添加 import，在 `_split_by_structure` 之后添加函数：

文件顶部新增 import：
```python
import numpy as np
from app.services.embedding import get_embeddings
```

函数实现：
```python
def _split_by_semantics(
    text: str, chunk_size: int = 500, threshold_percentile: float = 25
) -> list[dict]:
    """
    语义切分：基于相邻句子的 embedding 相似度骤降处切分。

    参数：
        text: 待切分文本
        chunk_size: 单个 chunk 最大字符数
        threshold_percentile: 相似度阈值百分位，低于此百分位的相似度处切分

    返回：
        [{"text": str, "title_path": "", "char_offset": int}, ...]
    """
    if not text.strip():
        return []

    # 按句子切分
    sentences = [s.strip() for s in _SENTENCE_ENDINGS.split(text) if s.strip()]
    if len(sentences) <= 1:
        return [{"text": text.strip(), "title_path": "", "char_offset": 0}]

    # 计算每个句子的 embedding
    embeddings = get_embeddings(sentences)
    embeddings_np = np.array(embeddings)

    # 计算相邻句子的余弦相似度
    similarities = []
    for i in range(len(embeddings_np) - 1):
        a, b = embeddings_np[i], embeddings_np[i + 1]
        dot = np.dot(a, b)
        norm = np.linalg.norm(a) * np.linalg.norm(b)
        sim = dot / norm if norm > 0 else 0.0
        similarities.append(sim)

    if not similarities:
        return [{"text": " ".join(sentences), "title_path": "", "char_offset": 0}]

    # 在相似度低于阈值处切分
    threshold = np.percentile(similarities, threshold_percentile)
    split_indices = [i for i, sim in enumerate(similarities) if sim < threshold]

    # 按切分点分组句子
    groups = []
    prev = 0
    for idx in split_indices:
        groups.append(sentences[prev : idx + 1])
        prev = idx + 1
    if prev < len(sentences):
        groups.append(sentences[prev:])

    # 合并过短的组，拆分过长的组
    result = []
    current_offset = 0
    for group in groups:
        chunk_text = "".join(group)
        # 如果超长，用普通切分兜底
        if len(chunk_text) > chunk_size:
            sub_chunks = split_text(chunk_text, chunk_size=chunk_size)
            for sc in sub_chunks:
                idx = text.find(sc, current_offset)
                actual_offset = idx if idx >= 0 else current_offset
                result.append({"text": sc, "title_path": "", "char_offset": actual_offset})
                current_offset = actual_offset + len(sc)
        else:
            idx = text.find(chunk_text, current_offset)
            actual_offset = idx if idx >= 0 else current_offset
            result.append({"text": chunk_text, "title_path": "", "char_offset": actual_offset})
            current_offset = actual_offset + len(chunk_text)

    return result
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd F:/IntraAI && python -m pytest backend/tests/test_chunking_strategy.py::TestSplitBySemantics -v --tb=short 2>&1 | tail -15
```

预期：4 个测试全部 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/document_processor.py backend/tests/test_chunking_strategy.py
git commit -m "feat: add semantic chunking based on embedding similarity"
```

---

## Task 6: 混合切分策略入口

**Files:**
- Modify: `backend/app/services/document_processor.py`
- Test: `backend/tests/test_chunking_strategy.py`

- [ ] **Step 1: 编写混合策略测试**

在 `backend/tests/test_chunking_strategy.py` 末尾添加：

```python
class TestSplitDocument:
    """split_document 统一入口测试"""

    def test_returns_list_of_dicts(self):
        """返回值应为 dict 列表，包含 text、title_path、char_offset、page"""
        from app.services.document_processor import split_document

        text = "段落一。\n\n段落二。"
        result = split_document(text, file_type="txt", chunk_size=100)

        assert isinstance(result, list)
        assert len(result) >= 1
        for chunk in result:
            assert "text" in chunk
            assert "title_path" in chunk
            assert "char_offset" in chunk
            assert "page" in chunk

    def test_uses_structure_when_headers_present(self):
        """有标题时应使用结构切分"""
        from app.services.document_processor import split_document

        text = "# 第一章\n\n内容一。\n\n# 第二章\n\n内容二。"
        result = split_document(text, file_type="md", chunk_size=100)

        title_paths = [c["title_path"] for c in result]
        assert any("第一章" in p for p in title_paths)

    def test_short_text_no_semantic(self):
        """短文本不应触发语义切分"""
        from app.services.document_processor import split_document

        text = "这是一段短文本。"
        result = split_document(text, file_type="txt", chunk_size=500)

        assert len(result) == 1
        assert result[0]["text"] == "这是一段短文本。"

    def test_page_metadata_propagated(self):
        """页码元数据应正确传递到 chunk 中"""
        from app.services.document_processor import split_document

        pages = [("第一页内容。", 1), ("第二页内容。", 2)]
        result = split_document("", file_type="pdf", chunk_size=100, pages=pages)

        pages_in_result = [c["page"] for c in result]
        assert 1 in pages_in_result
        assert 2 in pages_in_result

    def test_empty_text(self):
        """空文本返回空列表"""
        from app.services.document_processor import split_document

        result = split_document("", file_type="txt", chunk_size=100)
        assert result == []
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd F:/IntraAI && python -m pytest backend/tests/test_chunking_strategy.py::TestSplitDocument -v --tb=short 2>&1 | tail -15
```

预期：`AttributeError`

- [ ] **Step 3: 实现 split_document 统一入口**

在 `backend/app/services/document_processor.py` 中，在 `_split_by_semantics` 之后添加：

```python
# 混合策略阈值：低于此字符数的文档使用简单切分
_SHORT_DOC_THRESHOLD = 1000


def split_document(
    text: str,
    file_type: str = "txt",
    chunk_size: int = 500,
    overlap: int = 50,
    pages: list[tuple[str, int]] | None = None,
) -> list[dict]:
    """
    统一文档切分入口，根据文档特征自动选择切分策略。

    策略选择逻辑：
      1. 有标题结构 → 结构感知切分
      2. 无标题 + 短文档（< 1000字）→ 普通段落/句子切分
      3. 无标题 + 长文档 → 语义切分

    参数：
        text: 完整文本（当传入 pages 时可为空字符串）
        file_type: 文件类型
        chunk_size: chunk 最大字符数
        overlap: 重叠字符数
        pages: PDF 页面数据 [(页文本, 页码), ...]，为 None 时从 text 切分

    返回：
        [{"text": str, "title_path": str, "char_offset": int, "page": int}, ...]
    """
    if pages:
        return _split_pages(pages, chunk_size=chunk_size, overlap=overlap)

    if not text.strip():
        return []

    headers = _detect_headers(text)

    if headers:
        chunks = _split_by_structure(text, chunk_size=chunk_size, overlap=overlap)
        # 结构切分时，通过 char_offset 回推页码（非 PDF 统一为 1）
        for chunk in chunks:
            chunk["page"] = 1
        return chunks

    if len(text) < _SHORT_DOC_THRESHOLD:
        plain_chunks = split_text(text, chunk_size=chunk_size, overlap=overlap)
        result = []
        offset = 0
        for chunk in plain_chunks:
            idx = text.find(chunk, offset)
            actual_offset = idx if idx >= 0 else offset
            result.append({
                "text": chunk,
                "title_path": "",
                "char_offset": actual_offset,
                "page": 1,
            })
            offset = actual_offset + len(chunk)
        return result

    # 长文档无标题 → 语义切分
    chunks = _split_by_semantics(text, chunk_size=chunk_size)
    for chunk in chunks:
        chunk["page"] = 1
    return chunks


def _split_pages(
    pages: list[tuple[str, int]], chunk_size: int = 500, overlap: int = 50
) -> list[dict]:
    """按页面分割，每页独立走切分策略。"""
    result = []
    for page_text, page_num in pages:
        if not page_text.strip():
            continue
        headers = _detect_headers(page_text)
        if headers:
            chunks = _split_by_structure(page_text, chunk_size=chunk_size, overlap=overlap)
        elif len(page_text) < _SHORT_DOC_THRESHOLD:
            plain = split_text(page_text, chunk_size=chunk_size, overlap=overlap)
            chunks = [{"text": c, "title_path": "", "char_offset": 0} for c in plain]
        else:
            chunks = _split_by_semantics(page_text, chunk_size=chunk_size)
        for chunk in chunks:
            chunk["page"] = page_num
        result.extend(chunks)
    return result
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd F:/IntraAI && python -m pytest backend/tests/test_chunking_strategy.py::TestSplitDocument -v --tb=short 2>&1 | tail -15
```

预期：5 个测试全部 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/document_processor.py backend/tests/test_chunking_strategy.py
git commit -m "feat: add unified document splitting with hybrid strategy"
```

---

## Task 7: 更新上传流水线

**Files:**
- Modify: `backend/app/api/documents.py`
- Test: `backend/tests/api/test_documents.py`

- [ ] **Step 1: 编写上传流水线增强测试**

在 `backend/tests/api/test_documents.py` 中添加新测试类（在文件末尾）：

```python
class TestUploadDocumentMetadata:
    """上传文档的元数据增强测试"""

    @patch("app.api.documents.add_documents")
    @patch("app.api.documents.get_embeddings")
    @patch("app.api.documents.extract_text_with_pages")
    def test_upload_passes_metadata_to_vector_store(
        self, mock_extract, mock_embeddings, mock_add,
        client, user_headers, db_session
    ):
        """上传文档时应将增强元数据传递给 ChromaDB"""
        from app.models.knowledge_base import KnowledgeBase

        mock_extract.return_value = [("文件内容。", 1)]
        mock_embeddings.return_value = [[0.1] * 768]
        mock_add.return_value = 1

        kb = KnowledgeBase(name="测试", description="测试", owner_id=1)
        db_session.add(kb)
        db_session.commit()

        import io
        res = client.post(
            f"/api/documents/upload/{kb.id}",
            files={"file": ("test.txt", io.BytesIO(b"content"), "text/plain")},
            headers=user_headers,
        )

        assert res.status_code == 200
        # 验证 add_documents 被调用时带有增强元数据
        call_kwargs = mock_add.call_args
        metadatas = call_kwargs[1].get("metadatas") or call_kwargs[0][3] if len(call_kwargs[0]) > 3 else None
        if metadatas is None:
            # 检查关键字参数
            metadatas = call_kwargs[1].get("metadatas")
        assert metadatas is not None
        meta = metadatas[0]
        assert "source" in meta
        assert "page" in meta
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd F:/IntraAI && python -m pytest backend/tests/api/test_documents.py::TestUploadDocumentMetadata -v --tb=short 2>&1 | tail -20
```

预期：测试失败（当前 upload 端点不调用 `extract_text_with_pages`）

- [ ] **Step 3: 修改上传端点**

修改 `backend/app/api/documents.py`：

1. 更新 import：
```python
from app.services.document_processor import extract_text_with_pages, split_document
```
（替换原来的 `from app.services.document_processor import extract_text, split_text`）

2. 替换上传函数中的文档处理流水线（约第 145-173 行）：

```python
    # 步骤 1：提取文本（带页码信息）
    pages = extract_text_with_pages(filepath, ext)

    # 步骤 2：智能切分（自动选择策略）
    all_chunks_meta = []
    for page_text, page_num in pages:
        page_chunks = split_document(
            page_text, file_type=ext, chunk_size=500, overlap=50
        )
        for chunk in page_chunks:
            chunk["page"] = page_num
        all_chunks_meta.extend(page_chunks)

    chunk_count = 0
    if all_chunks_meta:
        chunks = [c["text"] for c in all_chunks_meta]

        # 步骤 3：分批向量化
        all_embeddings = []
        for i in range(0, len(chunks), 100):
            batch = chunks[i : i + 100]
            embs = get_embeddings(batch)
            all_embeddings.extend(embs)

        # 步骤 4：构建增强元数据并存入 ChromaDB
        metadatas = []
        for c in all_chunks_meta:
            metadatas.append({
                "source": file.filename,
                "page": c.get("page", 1),
                "title_path": c.get("title_path", ""),
                "char_offset": c.get("char_offset", 0),
                "file_type": ext,
            })
        chunk_count = add_documents(kb_id, chunks, all_embeddings, metadatas)
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd F:/IntraAI && python -m pytest backend/tests/api/test_documents.py -v --tb=short 2>&1 | tail -30
```

预期：所有文档相关测试 PASSED

- [ ] **Step 5: 运行全量测试确认无回归**

```bash
cd F:/IntraAI && python -m pytest backend/tests/ -v --tb=short 2>&1 | tail -30
```

预期：所有测试 PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/documents.py backend/tests/api/test_documents.py
git commit -m "feat: integrate enhanced chunking and metadata into upload pipeline"
```

---

## Task 8: 全量验证与覆盖率检查

**Files:**
- None（验证步骤）

- [ ] **Step 1: 运行完整测试套件**

```bash
cd F:/IntraAI && python -m pytest backend/tests/ -v --tb=short 2>&1 | tail -30
```

预期：所有测试 PASSED

- [ ] **Step 2: 检查覆盖率**

```bash
cd F:/IntraAI && python -m pytest backend/tests/ --cov=backend/app --cov-report=term-missing 2>&1 | tail -20
```

预期：覆盖率 >= 95%

- [ ] **Step 3: 代码检查**

```bash
cd F:/IntraAI/backend && ruff check app/services/document_processor.py app/api/documents.py
```

预期：无错误

- [ ] **Step 4: 最终 Commit**

```bash
git add -A
git commit -m "feat: complete RAG chunking optimization with hybrid strategy and metadata"
```

---

## Self-Review Checklist

- [ ] `extract_text` 保持向后兼容（返回 str 不变）
- [ ] `split_text` 保持向后兼容（返回 list[str] 不变）
- [ ] 新增函数有完整的测试覆盖
- [ ] 语义切分使用 mock 隔离 embedding 模型依赖
- [ ] 页码追踪对 PDF 精确到页，其他文件类型为 1
- [ ] 标题检测支持中文章节、数字编号、Markdown 三种格式
- [ ] 混合策略自动选择，无需用户手动配置
- [ ] chunk 元数据包含 source、page、title_path、char_offset、file_type
- [ ] 上传端点将增强元数据写入 ChromaDB
- [ ] 所有现有测试无回归
