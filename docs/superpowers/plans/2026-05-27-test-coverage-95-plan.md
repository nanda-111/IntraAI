# 测试覆盖率提升至 95% 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将后端测试覆盖率从 61% 提升至 95%，确保代码质量和可靠性

**Architecture:** 采用分层测试策略，针对覆盖率不足的模块逐一补充单元测试和集成测试。使用 mock 隔离外部依赖（LLM API、ChromaDB、sentence-transformers），确保测试可在 CI 环境稳定运行。

**Tech Stack:** pytest, pytest-cov, unittest.mock, FastAPI TestClient, SQLAlchemy SQLite 内存数据库

---

## 覆盖率现状分析

| 文件 | 当前覆盖率 | 缺失行数 | 目标覆盖率 |
|------|-----------|----------|-----------|
| app/api/chat.py | 16% | 122 | 95% |
| app/api/documents.py | 31% | 52 | 95% |
| app/services/langchain_agent.py | 0% | 41 | 95% |
| app/services/langchain_llm.py | 0% | 37 | 95% |
| app/services/langchain_tools.py | 0% | 61 | 95% |
| app/services/rag.py | 18% | 32 | 95% |
| app/services/document_processor.py | 74% | 23 | 95% |
| app/services/llm.py | 66% | 11 | 95% |
| app/core/database.py | 67% | 4 | 95% |
| app/main.py | 90% | 3 | 95% |
| app/services/embedding.py | 83% | 2 | 95% |
| app/services/vector_store.py | 95% | 1 | 95% |
| app/api/deps.py | 92% | 2 | 95% |
| app/api/knowledge_bases.py | 98% | 1 | 95% |

**总计需覆盖:** 约 342 行代码

---

## File Structure

### 新增测试文件
- `backend/tests/services/test_langchain_agent.py` - LangChain Agent 测试
- `backend/tests/services/test_langchain_llm.py` - LangChain LLM 封装测试
- `backend/tests/services/test_langchain_tools.py` - Agent 工具测试
- `backend/tests/services/test_rag.py` - RAG 服务测试
- `backend/tests/services/test_llm.py` - LLM 服务测试
- `backend/tests/services/test_document_processor.py` - 文档处理测试（扩展现有）
- `backend/tests/services/test_embedding.py` - 向量化服务测试
- `backend/tests/services/test_vector_store.py` - 向量存储测试（扩展现有）
- `backend/tests/api/test_chat.py` - 对话 API 测试
- `backend/tests/api/test_documents.py` - 文档 API 测试
- `backend/tests/test_main.py` - 应用入口测试

### 修改文件
- `backend/tests/conftest.py` - 添加通用 fixtures

---

## Task 1: 扩展 conftest.py 添加通用 fixtures

**Files:**
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: 添加 mock fixtures**

```python
# 在 conftest.py 末尾添加

@pytest.fixture
def mock_llm(monkeypatch):
    """Mock LLM 调用，返回固定响应"""
    from unittest.mock import MagicMock

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "测试回答"
    mock_response.choices[0].message.reasoning_content = ""
    mock_client.chat.completions.create.return_value = mock_response

    def _mock_chat_completion(messages, model=None):
        return "", "测试回答"

    def _mock_chat_completion_stream(messages, model=None):
        yield {"type": "answer", "content": "测试"}
        yield {"type": "answer", "content": "回答"}

    return mock_client, _mock_chat_completion, _mock_chat_completion_stream


@pytest.fixture
def mock_embeddings(monkeypatch):
    """Mock 向量化服务"""
    from unittest.mock import patch

    def _get_embeddings(texts):
        return [[0.1] * 768 for _ in texts]

    with patch("app.services.embedding.get_embeddings", side_effect=_get_embeddings):
        yield _get_embeddings


@pytest.fixture
def mock_vector_store(monkeypatch):
    """Mock 向量存储服务"""
    from unittest.mock import patch

    mock_results = [
        ("测试文档内容", {"source": "test.pdf"}),
    ]

    with patch("app.services.vector_store.search", return_value=mock_results):
        with patch("app.services.vector_store.add_documents", return_value=2):
            yield mock_results


@pytest.fixture
def mock_document_processor(monkeypatch):
    """Mock 文档处理服务"""
    from unittest.mock import patch

    with patch("app.services.document_processor.extract_text", return_value="测试文本内容"):
        with patch("app.services.document_processor.split_text", return_value=["切片1", "切片2"]):
            yield
```

- [ ] **Step 2: 运行测试验证 fixtures 不影响现有测试**

Run: `cd F:/IntraAI/backend && python -m pytest tests/ -v --tb=short 2>&1 | tail -20`
Expected: 所有现有测试通过

- [ ] **Step 3: Commit**

```bash
git add backend/tests/conftest.py
git commit -m "test: add common test fixtures for mocking LLM, embeddings, and vector store"
```

---

## Task 2: 测试 LLM 服务模块 (app/services/llm.py)

**Files:**
- Create: `backend/tests/services/__init__.py`
- Create: `backend/tests/services/test_llm.py`

- [ ] **Step 1: 创建测试文件目录结构**

```bash
mkdir -p backend/tests/services
touch backend/tests/services/__init__.py
```

- [ ] **Step 2: 编写 LLM 服务测试**

```python
"""LLM 服务模块测试"""

from unittest.mock import MagicMock, patch

import pytest


class TestChatCompletion:
    """chat_completion 函数测试"""

    @patch("app.services.llm.client")
    def test_chat_completion_success(self, mock_client):
        """测试普通对话调用成功"""
        from app.services.llm import chat_completion

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "你好"
        mock_response.choices[0].message.reasoning_content = "思考过程"
        mock_client.chat.completions.create.return_value = mock_response

        reasoning, answer = chat_completion([{"role": "user", "content": "你好"}])

        assert answer == "你好"
        assert reasoning == "思考过程"
        mock_client.chat.completions.create.assert_called_once()

    @patch("app.services.llm.client")
    def test_chat_completion_no_reasoning(self, mock_client):
        """测试没有 reasoning_content 的情况"""
        from app.services.llm import chat_completion

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "回答"
        mock_response.choices[0].message.reasoning_content = None
        mock_client.chat.completions.create.return_value = mock_response

        reasoning, answer = chat_completion([{"role": "user", "content": "测试"}])

        assert answer == "回答"
        assert reasoning == ""

    @patch("app.services.llm.client")
    def test_chat_completion_custom_model(self, mock_client):
        """测试使用自定义模型"""
        from app.services.llm import chat_completion

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "回答"
        mock_response.choices[0].message.reasoning_content = ""
        mock_client.chat.completions.create.return_value = mock_response

        chat_completion([{"role": "user", "content": "测试"}], model="custom-model")

        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "custom-model"


class TestChatCompletionStream:
    """chat_completion_stream 函数测试"""

    @patch("app.services.llm.client")
    def test_stream_success(self, mock_client):
        """测试流式调用成功"""
        from app.services.llm import chat_completion_stream

        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [MagicMock()]
        mock_chunk1.choices[0].delta.content = "你好"
        mock_chunk1.choices[0].delta.reasoning_content = None

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [MagicMock()]
        mock_chunk2.choices[0].delta.content = None
        mock_chunk2.choices[0].delta.reasoning_content = "思考"

        mock_client.chat.completions.create.return_value = [mock_chunk1, mock_chunk2]

        chunks = list(chat_completion_stream([{"role": "user", "content": "你好"}]))

        assert len(chunks) == 2
        assert chunks[0] == {"type": "answer", "content": "你好"}
        assert chunks[1] == {"type": "reasoning", "content": "思考"}

    @patch("app.services.llm.client")
    def test_stream_empty_choices(self, mock_client):
        """测试空 choices 的情况"""
        from app.services.llm import chat_completion_stream

        mock_chunk = MagicMock()
        mock_chunk.choices = []

        mock_client.chat.completions.create.return_value = [mock_chunk]

        chunks = list(chat_completion_stream([{"role": "user", "content": "测试"}]))

        assert len(chunks) == 0


class TestGenerateTitle:
    """generate_title 函数测试"""

    @patch("app.services.llm.chat_completion")
    def test_generate_title_success(self, mock_chat):
        """测试标题生成成功"""
        from app.services.llm import generate_title

        mock_chat.return_value = ("", "公司请假制度说明")

        title = generate_title("公司的请假制度是什么？", "根据公司规定...")

        assert title == "公司请假制度说明"

    @patch("app.services.llm.chat_completion")
    def test_generate_title_with_quotes(self, mock_chat):
        """测试标题去除引号"""
        from app.services.llm import generate_title

        mock_chat.return_value = ("", '"公司请假制度"')

        title = generate_title("请假制度", "回答")

        assert '"' not in title
        assert "'" not in title


class TestGenerateSummary:
    """generate_summary 函数测试"""

    @patch("app.services.llm.chat_completion")
    def test_generate_summary_success(self, mock_chat):
        """测试摘要生成成功"""
        from app.services.llm import generate_summary

        mock_chat.return_value = ("", "用户询问了请假制度，AI进行了解答")

        conversations = [
            {"role": "user", "content": "请假制度是什么？"},
            {"role": "assistant", "content": "根据公司规定..."},
        ]

        summary = generate_summary(conversations)

        assert summary == "用户询问了请假制度，AI进行了解答"
```

- [ ] **Step 3: 运行测试验证**

Run: `cd F:/IntraAI/backend && python -m pytest tests/services/test_llm.py -v --tb=short`
Expected: 所有测试通过

- [ ] **Step 4: Commit**

```bash
git add backend/tests/services/__init__.py backend/tests/services/test_llm.py
git commit -m "test: add comprehensive tests for LLM service module"
```

---

## Task 3: 测试 RAG 服务模块 (app/services/rag.py)

**Files:**
- Create: `backend/tests/services/test_rag.py`

- [ ] **Step 1: 编写 RAG 服务测试**

```python
"""RAG 服务模块测试"""

from unittest.mock import patch

import pytest


class TestBuildContext:
    """_build_context 函数测试"""

    def test_build_context_with_results(self):
        """测试有检索结果时构建上下文"""
        from app.services.rag import _build_context

        results = [
            ("文档内容1", {"source": "doc1.pdf"}),
            ("文档内容2", {"source": "doc2.pdf"}),
        ]

        context = _build_context(results)

        assert "文档内容1" in context
        assert "文档内容2" in context
        assert "[来源: doc1.pdf]" in context
        assert "[来源: doc2.pdf]" in context

    def test_build_context_empty_results(self):
        """测试无检索结果时返回默认文本"""
        from app.services.rag import _build_context

        context = _build_context([])

        assert context == "（无相关资料）"

    def test_build_context_no_source(self):
        """测试没有来源信息的情况"""
        from app.services.rag import _build_context

        results = [("文档内容", {})]

        context = _build_context(results)

        assert "文档内容" in context
        assert "[来源:" not in context


class TestAskWithRag:
    """ask_with_rag 函数测试"""

    @patch("app.services.rag.chat_completion")
    @patch("app.services.rag.search")
    @patch("app.services.rag.get_embeddings")
    def test_ask_with_rag_basic(self, mock_embeddings, mock_search, mock_chat):
        """测试基本 RAG 问答"""
        from app.services.rag import ask_with_rag

        mock_embeddings.return_value = [[0.1] * 768]
        mock_search.return_value = [
            ("公司规定每年有10天年假", {"source": "员工手册.pdf"}),
        ]
        mock_chat.return_value = ("", "根据公司规定，每年有10天年假。")

        answer = ask_with_rag("年假有多少天？", kb_id=1)

        assert answer == "根据公司规定，每年有10天年假。"
        mock_embeddings.assert_called_once()
        mock_search.assert_called_once()

    @patch("app.services.rag.chat_completion")
    @patch("app.services.rag.search")
    @patch("app.services.rag.get_embeddings")
    def test_ask_with_rag_with_history(self, mock_embeddings, mock_search, mock_chat):
        """测试带历史对话的 RAG 问答"""
        from app.services.rag import ask_with_rag

        mock_embeddings.return_value = [[0.1] * 768]
        mock_search.return_value = [("文档内容", {"source": "test.pdf"})]
        mock_chat.return_value = ("", "回答")

        history = [
            {"role": "user", "content": "之前的问题"},
            {"role": "assistant", "content": "之前的回答"},
        ]

        answer = ask_with_rag("新问题", kb_id=1, history=history)

        assert answer == "回答"
        call_args = mock_chat.call_args[0][0]
        assert len(call_args) > 2  # system + history + user

    @patch("app.services.rag.chat_completion")
    @patch("app.services.rag.search")
    @patch("app.services.rag.get_embeddings")
    def test_ask_with_rag_with_summary(self, mock_embeddings, mock_search, mock_chat):
        """测试带摘要的 RAG 问答"""
        from app.services.rag import ask_with_rag

        mock_embeddings.return_value = [[0.1] * 768]
        mock_search.return_value = [("文档内容", {"source": "test.pdf"})]
        mock_chat.return_value = ("", "回答")

        answer = ask_with_rag("问题", kb_id=1, summary="之前的对话摘要")

        assert answer == "回答"
        call_args = mock_chat.call_args[0][0]
        summary_msg = [m for m in call_args if "摘要" in m.get("content", "")]
        assert len(summary_msg) > 0


class TestAskWithRagStream:
    """ask_with_rag_stream 函数测试"""

    @patch("app.services.rag.chat_completion_stream")
    @patch("app.services.rag.search")
    @patch("app.services.rag.get_embeddings")
    def test_stream_basic(self, mock_embeddings, mock_search, mock_stream):
        """测试流式 RAG 问答"""
        from app.services.rag import ask_with_rag_stream

        mock_embeddings.return_value = [[0.1] * 768]
        mock_search.return_value = [("文档内容", {"source": "test.pdf"})]
        mock_stream.return_value = iter([
            {"type": "answer", "content": "回答"},
        ])

        chunks = list(ask_with_rag_stream("问题", kb_id=1))

        assert len(chunks) == 1
        assert chunks[0]["content"] == "回答"
```

- [ ] **Step 2: 运行测试验证**

Run: `cd F:/IntraAI/backend && python -m pytest tests/services/test_rag.py -v --tb=short`
Expected: 所有测试通过

- [ ] **Step 3: Commit**

```bash
git add backend/tests/services/test_rag.py
git commit -m "test: add comprehensive tests for RAG service module"
```

---

## Task 4: 测试文档处理服务 (app/services/document_processor.py)

**Files:**
- Create: `backend/tests/services/test_document_processor_full.py`

- [ ] **Step 1: 编写文档处理服务测试**

```python
"""文档处理服务完整测试"""

import os
import tempfile

import pytest


class TestExtractText:
    """extract_text 函数测试"""

    def test_extract_txt_file(self):
        """测试提取 TXT 文件"""
        from app.services.document_processor import extract_text

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("测试文本内容")
            filepath = f.name

        try:
            result = extract_text(filepath, "txt")
            assert result == "测试文本内容"
        finally:
            os.unlink(filepath)

    def test_extract_md_file(self):
        """测试提取 Markdown 文件"""
        from app.services.document_processor import extract_text

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("# 标题\n\n内容")
            filepath = f.name

        try:
            result = extract_text(filepath, "md")
            assert "标题" in result
            assert "内容" in result
        finally:
            os.unlink(filepath)

    def test_extract_unsupported_type(self):
        """测试不支持的文件类型"""
        from app.services.document_processor import extract_text

        with pytest.raises(ValueError, match="不支持的文件类型"):
            extract_text("test.xyz", "xyz")


class TestSplitText:
    """split_text 函数测试"""

    def test_split_empty_text(self):
        """测试空文本"""
        from app.services.document_processor import split_text

        result = split_text("")
        assert result == []

    def test_split_short_text(self):
        """测试短文本不切割"""
        from app.services.document_processor import split_text

        result = split_text("短文本", chunk_size=100)
        assert result == ["短文本"]

    def test_split_by_paragraph(self):
        """测试按段落切割"""
        from app.services.document_processor import split_text

        text = "段落一\n\n段落二\n\n段落三"
        result = split_text(text, chunk_size=100)

        assert len(result) == 3
        assert "段落一" in result[0]
        assert "段落二" in result[1]
        assert "段落三" in result[2]

    def test_split_long_paragraph(self):
        """测试超长段落按句子切割"""
        from app.services.document_processor import split_text

        text = "第一句话。第二句话。第三句话。第四句话。"
        result = split_text(text, chunk_size=10)

        assert len(result) > 1

    def test_split_with_overlap(self):
        """测试重叠切割"""
        from app.services.document_processor import split_text

        text = "第一段内容。\n\n第二段内容。\n\n第三段内容。"
        result = split_text(text, chunk_size=50, overlap=10)

        assert len(result) >= 2

    def test_split_overlap_adjustment(self):
        """测试 overlap 自动调整"""
        from app.services.document_processor import split_text

        text = "内容"
        result = split_text(text, chunk_size=10, overlap=20)

        assert len(result) == 1


class TestSplitBySentence:
    """_split_by_sentence 函数测试"""

    def test_split_by_sentence_basic(self):
        """测试基本句子切割"""
        from app.services.document_processor import _split_by_sentence

        text = "第一句。第二句。第三句。"
        result = _split_by_sentence(text, chunk_size=20)

        assert len(result) >= 1

    def test_split_by_sentence_no_punctuation(self):
        """测试无标点的文本"""
        from app.services.document_processor import _split_by_sentence

        text = "没有标点的长文本内容需要按字符切割"
        result = _split_by_sentence(text, chunk_size=5)

        assert len(result) > 1

    def test_split_by_sentence_long_sentence(self):
        """测试超长句子按字符切割"""
        from app.services.document_processor import _split_by_sentence

        text = "这是一个非常非常长的句子需要被切割成多个小片段。"
        result = _split_by_sentence(text, chunk_size=10)

        for chunk in result:
            assert len(chunk) <= 10


class TestExtractTail:
    """_extract_tail 函数测试"""

    def test_extract_tail_short_text(self):
        """测试短文本返回全部"""
        from app.services.document_processor import _extract_tail

        result = _extract_tail("短文本", max_len=100)
        assert result == "短文本"

    def test_extract_tail_with_sentence_ending(self):
        """测试从句子边界提取"""
        from app.services.document_processor import _extract_tail

        result = _extract_tail("第一句。第二句。第三句", max_len=10)

        assert len(result) <= 10

    def test_extract_tail_no_ending(self):
        """测试没有句子结束符"""
        from app.services.document_processor import _extract_tail

        result = _extract_tail("abcdefghijklmnop", max_len=5)
        assert len(result) == 5
```

- [ ] **Step 2: 运行测试验证**

Run: `cd F:/IntraAI/backend && python -m pytest tests/services/test_document_processor_full.py -v --tb=short`
Expected: 所有测试通过

- [ ] **Step 3: Commit**

```bash
git add backend/tests/services/test_document_processor_full.py
git commit -m "test: add comprehensive tests for document processor service"
```

---

## Task 5: 测试 LangChain LLM 封装 (app/services/langchain_llm.py)

**Files:**
- Create: `backend/tests/services/test_langchain_llm.py`

- [ ] **Step 1: 编写 LangChain LLM 测试**

```python
"""LangChain LLM 封装模块测试"""

from unittest.mock import MagicMock, patch

import pytest


class TestConvertDictToMessageWithReasoning:
    """_convert_dict_to_message_with_reasoning 函数测试"""

    def test_assistant_with_reasoning(self):
        """测试 assistant 消息带 reasoning_content"""
        from app.services.langchain_llm import _convert_dict_to_message_with_reasoning

        _dict = {
            "role": "assistant",
            "content": "回答内容",
            "reasoning_content": "思考过程",
        }

        with patch("app.services.langchain_llm._orig_convert_dict") as mock_orig:
            mock_msg = MagicMock()
            mock_msg.additional_kwargs = {}
            mock_orig.return_value = mock_msg

            result = _convert_dict_to_message_with_reasoning(_dict)

            assert result.additional_kwargs["reasoning_content"] == "思考过程"

    def test_assistant_without_reasoning(self):
        """测试 assistant 消息不带 reasoning_content"""
        from app.services.langchain_llm import _convert_dict_to_message_with_reasoning

        _dict = {
            "role": "assistant",
            "content": "回答内容",
        }

        with patch("app.services.langchain_llm._orig_convert_dict") as mock_orig:
            mock_msg = MagicMock()
            mock_msg.additional_kwargs = {}
            mock_orig.return_value = mock_msg

            result = _convert_dict_to_message_with_reasoning(_dict)

            assert "reasoning_content" not in result.additional_kwargs

    def test_non_assistant_message(self):
        """测试非 assistant 消息"""
        from app.services.langchain_llm import _convert_dict_to_message_with_reasoning

        _dict = {
            "role": "user",
            "content": "用户问题",
        }

        with patch("app.services.langchain_llm._orig_convert_dict") as mock_orig:
            mock_msg = MagicMock()
            mock_msg.additional_kwargs = {}
            mock_orig.return_value = mock_msg

            result = _convert_dict_to_message_with_reasoning(_dict)

            assert "reasoning_content" not in result.additional_kwargs


class TestConvertDeltaToMessageChunkWithReasoning:
    """_convert_delta_to_message_chunk_with_reasoning 函数测试"""

    def test_delta_with_reasoning(self):
        """测试 delta 带 reasoning_content"""
        from app.services.langchain_llm import _convert_delta_to_message_chunk_with_reasoning

        _dict = {"reasoning_content": "流式思考"}

        with patch("app.services.langchain_llm._orig_convert_delta") as mock_orig:
            mock_chunk = MagicMock()
            mock_chunk.additional_kwargs = {}
            mock_orig.return_value = mock_chunk

            result = _convert_delta_to_message_chunk_with_reasoning(_dict, MagicMock())

            assert result.additional_kwargs["reasoning_content"] == "流式思考"

    def test_delta_without_reasoning(self):
        """测试 delta 不带 reasoning_content"""
        from app.services.langchain_llm import _convert_delta_to_message_chunk_with_reasoning

        _dict = {"content": "内容"}

        with patch("app.services.langchain_llm._orig_convert_delta") as mock_orig:
            mock_chunk = MagicMock()
            mock_chunk.additional_kwargs = {}
            mock_orig.return_value = mock_chunk

            result = _convert_delta_to_message_chunk_with_reasoning(_dict, MagicMock())

            assert "reasoning_content" not in result.additional_kwargs


class TestInjectReasoning:
    """_inject_reasoning 函数测试"""

    def test_inject_reasoning_to_ai_message(self):
        """测试注入 reasoning 到 AIMessage"""
        from langchain_core.messages import AIMessage

        from app.services.langchain_llm import _inject_reasoning

        msg = AIMessage(content="回答")
        msg.additional_kwargs["reasoning_content"] = "思考过程"

        msg_dict = {"role": "assistant", "content": "回答"}

        result = _inject_reasoning(msg_dict, msg)

        assert result["reasoning_content"] == "思考过程"

    def test_skip_non_ai_message(self):
        """测试跳过非 AIMessage"""
        from langchain_core.messages import HumanMessage

        from app.services.langchain_llm import _inject_reasoning

        msg = HumanMessage(content="问题")
        msg_dict = {"role": "user", "content": "问题"}

        result = _inject_reasoning(msg_dict, msg)

        assert "reasoning_content" not in result

    def test_skip_existing_reasoning(self):
        """测试跳过已有 reasoning 的消息"""
        from langchain_core.messages import AIMessage

        from app.services.langchain_llm import _inject_reasoning

        msg = AIMessage(content="回答")
        msg.additional_kwargs["reasoning_content"] = "思考"

        msg_dict = {"role": "assistant", "content": "回答", "reasoning_content": "已有"}

        result = _inject_reasoning(msg_dict, msg)

        assert result["reasoning_content"] == "已有"


class TestChatMiMo:
    """ChatMiMo 类测试"""

    @patch("app.services.langchain_llm.settings")
    def test_get_mimo_llm(self, mock_settings):
        """测试获取 MiMo LLM 实例"""
        from app.services.langchain_llm import ChatMiMo, get_mimo_llm

        mock_settings.OPENAI_MODEL = "test-model"
        mock_settings.OPENAI_API_KEY = "test-key"
        mock_settings.OPENAI_BASE_URL = "http://test.com"

        llm = get_mimo_llm(temperature=0.5, streaming=True)

        assert isinstance(llm, ChatMiMo)
        assert llm.temperature == 0.5
        assert llm.streaming is True

    def test_llm_type(self):
        """测试 LLM 类型属性"""
        from app.services.langchain_llm import ChatMiMo

        with patch("app.services.langchain_llm.settings") as mock_settings:
            mock_settings.OPENAI_MODEL = "test"
            mock_settings.OPENAI_API_KEY = "test"
            mock_settings.OPENAI_BASE_URL = "http://test"

            llm = ChatMiMo()
            assert llm._llm_type == "chat-mimo"
```

- [ ] **Step 2: 运行测试验证**

Run: `cd F:/IntraAI/backend && python -m pytest tests/services/test_langchain_llm.py -v --tb=short`
Expected: 所有测试通过

- [ ] **Step 3: Commit**

```bash
git add backend/tests/services/test_langchain_llm.py
git commit -m "test: add comprehensive tests for LangChain LLM wrapper"
```

---

## Task 6: 测试 LangChain 工具 (app/services/langchain_tools.py)

**Files:**
- Create: `backend/tests/services/test_langchain_tools.py`

- [ ] **Step 1: 编写 LangChain 工具测试**

```python
"""LangChain 工具模块测试"""

from unittest.mock import MagicMock, patch

import pytest


class TestRagSearchTool:
    """rag_search 工具测试"""

    @patch("app.services.langchain_tools.vector_search")
    @patch("app.services.langchain_tools.get_embeddings")
    def test_rag_search_success(self, mock_embeddings, mock_search):
        """测试知识库搜索成功"""
        from app.services.langchain_tools import rag_search

        mock_embeddings.return_value = [[0.1] * 768]
        mock_search.return_value = [
            ("文档内容", {"source": "test.pdf"}),
        ]

        result = rag_search.invoke({"query": "测试问题"})

        assert "文档内容" in result
        assert "test.pdf" in result

    @patch("app.services.langchain_tools.get_embeddings")
    def test_rag_search_embedding_failure(self, mock_embeddings):
        """测试向量化失败"""
        from app.services.langchain_tools import rag_search

        mock_embeddings.return_value = []

        result = rag_search.invoke({"query": "测试"})

        assert "向量化失败" in result

    @patch("app.services.langchain_tools.vector_search")
    @patch("app.services.langchain_tools.get_embeddings")
    def test_rag_search_no_results(self, mock_embeddings, mock_search):
        """测试搜索无结果"""
        from app.services.langchain_tools import rag_search

        mock_embeddings.return_value = [[0.1] * 768]
        mock_search.return_value = []

        result = rag_search.invoke({"query": "测试"})

        assert "没有找到相关内容" in result

    @patch("app.services.langchain_tools.get_embeddings")
    def test_rag_search_exception(self, mock_embeddings):
        """测试搜索异常"""
        from app.services.langchain_tools import rag_search

        mock_embeddings.side_effect = Exception("测试异常")

        result = rag_search.invoke({"query": "测试"})

        assert "出错" in result


class TestDbQueryTool:
    """db_query 工具测试"""

    def test_db_query_select_success(self):
        """测试 SELECT 查询成功"""
        from app.services.langchain_tools import db_query

        with patch("app.services.langchain_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db

            mock_result = MagicMock()
            mock_result.keys.return_value = ["id", "name"]
            mock_result.fetchall.return_value = [(1, "test")]
            mock_db.execute.return_value = mock_result

            result = db_query.invoke({"sql": "SELECT id, name FROM users"})

            assert "id" in result
            assert "name" in result
            assert "1" in result
            assert "test" in result

    def test_db_query_reject_non_select(self):
        """测试拒绝非 SELECT 语句"""
        from app.services.langchain_tools import db_query

        result = db_query.invoke({"sql": "DELETE FROM users"})

        assert "只允许 SELECT" in result

    def test_db_query_reject_dangerous_keywords(self):
        """测试拒绝危险关键词"""
        from app.services.langchain_tools import db_query

        dangerous_queries = [
            "SELECT * FROM users; DROP TABLE users",
            "SELECT * FROM users; DELETE FROM users",
            "SELECT * FROM users; UPDATE users SET name='hack'",
            "SELECT * FROM users; INSERT INTO users VALUES(1)",
        ]

        for sql in dangerous_queries:
            result = db_query.invoke({"sql": sql})
            assert "禁止" in result or "错误" in result

    def test_db_query_empty_result(self):
        """测试空查询结果"""
        from app.services.langchain_tools import db_query

        with patch("app.services.langchain_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db

            mock_result = MagicMock()
            mock_result.keys.return_value = ["id"]
            mock_result.fetchall.return_value = []
            mock_db.execute.return_value = mock_result

            result = db_query.invoke({"sql": "SELECT id FROM users WHERE id = 999"})

            assert "查询结果为空" in result

    def test_db_query_exception(self):
        """测试查询异常"""
        from app.services.langchain_tools import db_query

        with patch("app.services.langchain_tools.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db
            mock_db.execute.side_effect = Exception("数据库错误")

            result = db_query.invoke({"sql": "SELECT * FROM nonexistent"})

            assert "出错" in result


class TestWebSearchTool:
    """web_search 工具测试"""

    @patch("app.services.langchain_tools._ddg_search")
    def test_web_search_success(self, mock_search):
        """测试网页搜索成功"""
        from app.services.langchain_tools import web_search

        mock_search.run.return_value = "搜索结果内容"

        result = web_search.invoke({"query": "测试搜索"})

        assert result == "搜索结果内容"

    @patch("app.services.langchain_tools._ddg_search")
    def test_web_search_no_results(self, mock_search):
        """测试网页搜索无结果"""
        from app.services.langchain_tools import web_search

        mock_search.run.return_value = ""

        result = web_search.invoke({"query": "未知搜索"})

        assert "未找到" in result

    @patch("app.services.langchain_tools._ddg_search")
    def test_web_search_exception(self, mock_search):
        """测试网页搜索异常"""
        from app.services.langchain_tools import web_search

        mock_search.run.side_effect = Exception("网络错误")

        result = web_search.invoke({"query": "测试"})

        assert "出错" in result
```

- [ ] **Step 2: 运行测试验证**

Run: `cd F:/IntraAI/backend && python -m pytest tests/services/test_langchain_tools.py -v --tb=short`
Expected: 所有测试通过

- [ ] **Step 3: Commit**

```bash
git add backend/tests/services/test_langchain_tools.py
git commit -m "test: add comprehensive tests for LangChain tools"
```

---

## Task 7: 测试 LangChain Agent (app/services/langchain_agent.py)

**Files:**
- Create: `backend/tests/services/test_langchain_agent.py`

- [ ] **Step 1: 编写 LangChain Agent 测试**

```python
"""LangChain Agent 模块测试"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestConvertHistory:
    """_convert_history 函数测试"""

    def test_convert_empty_history(self):
        """测试空历史"""
        from app.services.langchain_agent import _convert_history

        result = _convert_history(None)
        assert result == []

        result = _convert_history([])
        assert result == []

    def test_convert_history_with_messages(self):
        """测试转换历史消息"""
        from langchain_core.messages import AIMessage, HumanMessage

        from app.services.langchain_agent import _convert_history

        history = [
            {"role": "user", "content": "问题1"},
            {"role": "assistant", "content": "回答1"},
            {"role": "user", "content": "问题2"},
        ]

        result = _convert_history(history)

        assert len(result) == 3
        assert isinstance(result[0], HumanMessage)
        assert result[0].content == "问题1"
        assert isinstance(result[1], AIMessage)
        assert result[1].content == "回答1"
        assert isinstance(result[2], HumanMessage)


class TestGetAgent:
    """_get_agent 函数测试"""

    @patch("app.services.langchain_agent.create_agent")
    @patch("app.services.langchain_agent.get_mimo_llm")
    def test_get_agent_creates_once(self, mock_llm, mock_create):
        """测试 Agent 只创建一次"""
        import app.services.langchain_agent as module

        # 清除缓存
        module._agent_cache = None

        mock_agent = MagicMock()
        mock_create.return_value = mock_agent

        agent1 = module._get_agent()
        agent2 = module._get_agent()

        assert agent1 is agent2
        mock_create.assert_called_once()

        # 清理
        module._agent_cache = None


class TestRunAgent:
    """run_agent 函数测试"""

    @patch("app.services.langchain_agent._get_agent")
    def test_run_agent_basic(self, mock_get_agent):
        """测试基本 Agent 调用"""
        from app.services.langchain_agent import run_agent

        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.messages = [MagicMock(content="Agent 回答")]
        mock_agent.invoke.return_value = mock_result
        mock_get_agent.return_value = mock_agent

        result = run_agent("测试问题")

        assert result == "Agent 回答"

    @patch("app.services.langchain_agent._get_agent")
    def test_run_agent_with_history(self, mock_get_agent):
        """测试带历史的 Agent 调用"""
        from app.services.langchain_agent import run_agent

        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.messages = [MagicMock(content="回答")]
        mock_agent.invoke.return_value = mock_result
        mock_get_agent.return_value = mock_agent

        history = [
            {"role": "user", "content": "之前的问题"},
            {"role": "assistant", "content": "之前的回答"},
        ]

        result = run_agent("新问题", history=history)

        assert result == "回答"


class TestRunAgentStream:
    """run_agent_stream 函数测试"""

    @pytest.mark.asyncio
    @patch("app.services.langchain_agent._get_agent")
    async def test_run_agent_stream(self, mock_get_agent):
        """测试流式 Agent 调用"""
        from app.services.langchain_agent import run_agent_stream

        mock_agent = MagicMock()

        async def mock_astream(*args, **kwargs):
            yield ("messages", [MagicMock(content="流式")])
            yield ("messages", [MagicMock(content="回答")])

        mock_agent.astream = mock_astream
        mock_get_agent.return_value = mock_agent

        chunks = []
        async for chunk in run_agent_stream("测试"):
            chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0]["content"] == "流式"
```

- [ ] **Step 2: 运行测试验证**

Run: `cd F:/IntraAI/backend && python -m pytest tests/services/test_langchain_agent.py -v --tb=short`
Expected: 所有测试通过

- [ ] **Step 3: Commit**

```bash
git add backend/tests/services/test_langchain_agent.py
git commit -m "test: add comprehensive tests for LangChain Agent"
```

---

## Task 8: 测试对话 API (app/api/chat.py)

**Files:**
- Create: `backend/tests/api/test_chat.py`

- [ ] **Step 1: 编写对话 API 测试**

```python
"""对话 API 集成测试"""

from unittest.mock import patch

import pytest


class TestChatEndpoint:
    """POST /api/chat/ 测试"""

    @patch("app.api.chat.chat_completion")
    def test_chat_basic(self, mock_chat, client, user_headers, db_session):
        """测试基本对话"""
        from app.models.knowledge_base import KnowledgeBase

        mock_chat.return_value = ("", "测试回答")

        res = client.post(
            "/api/chat/",
            json={"question": "你好"},
            headers=user_headers,
        )

        assert res.status_code == 200
        assert res.json()["answer"] == "测试回答"

    @patch("app.api.chat.ask_with_rag")
    def test_chat_with_kb(self, mock_rag, client, user_headers, db_session):
        """测试带知识库的对话"""
        from app.models.knowledge_base import KnowledgeBase

        kb = KnowledgeBase(name="测试知识库", description="测试", owner_id=1)
        db_session.add(kb)
        db_session.commit()

        mock_rag.return_value = "RAG 回答"

        res = client.post(
            "/api/chat/",
            json={"question": "问题", "kb_id": kb.id},
            headers=user_headers,
        )

        assert res.status_code == 200
        assert res.json()["answer"] == "RAG 回答"

    @patch("app.api.chat.chat_completion")
    def test_chat_with_session(self, mock_chat, client, user_headers, db_session):
        """测试带会话的对话"""
        from app.models.session import Session

        mock_chat.return_value = ("", "回答")

        session = Session(user_id=1, title="新对话")
        db_session.add(session)
        db_session.commit()

        res = client.post(
            "/api/chat/",
            json={"question": "你好", "session_id": session.id},
            headers=user_headers,
        )

        assert res.status_code == 200

    @patch("app.services.langchain_agent.run_agent")
    def test_chat_agent_mode(self, mock_agent, client, user_headers):
        """测试 Agent 模式对话"""
        mock_agent.return_value = "Agent 回答"

        res = client.post(
            "/api/chat/",
            json={"question": "问题", "mode": "agent"},
            headers=user_headers,
        )

        assert res.status_code == 200
        assert res.json()["answer"] == "Agent 回答"


class TestChatStreamEndpoint:
    """POST /api/chat/stream 测试"""

    @patch("app.api.chat.chat_completion_stream")
    def test_chat_stream_basic(self, mock_stream, client, user_headers):
        """测试基本流式对话"""
        mock_stream.return_value = iter([
            {"type": "answer", "content": "你好"},
            {"type": "answer", "content": "世界"},
        ])

        res = client.post(
            "/api/chat/stream",
            json={"question": "你好"},
            headers=user_headers,
        )

        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]


class TestLoadSessionHistory:
    """_load_session_history 函数测试"""

    def test_load_existing_session(self, db_session):
        """测试加载存在的会话"""
        from app.api.chat import _load_session_history
        from app.models.session import Session

        session = Session(user_id=1, title="测试会话")
        db_session.add(session)
        db_session.commit()

        loaded_session, summary, history = _load_session_history(session.id, db_session)

        assert loaded_session.id == session.id
        assert summary is None
        assert history is None

    def test_load_nonexistent_session(self, db_session):
        """测试加载不存在的会话"""
        from fastapi import HTTPException

        from app.api.chat import _load_session_history

        with pytest.raises(HTTPException) as exc_info:
            _load_session_history(999, db_session)

        assert exc_info.value.status_code == 404


class TestMaybeCompress:
    """_maybe_compress 函数测试"""

    @patch("app.api.chat.generate_summary")
    def test_compress_when_count_reaches_20(self, mock_summary, db_session):
        """测试对话数量达到 20 时触发压缩"""
        from app.api.chat import _maybe_compress
        from app.models.conversation import Conversation
        from app.models.session import Session

        mock_summary.return_value = "对话摘要"

        session = Session(user_id=1, title="测试")
        db_session.add(session)
        db_session.commit()

        # 创建 20 条对话
        for i in range(20):
            conv = Conversation(
                user_id=1,
                session_id=session.id,
                question=f"问题{i}",
                answer=f"回答{i}",
            )
            db_session.add(conv)
        db_session.commit()

        _maybe_compress(session.id, db_session)

        # 验证对话被压缩
        remaining = db_session.query(Conversation).filter(
            Conversation.session_id == session.id
        ).count()
        assert remaining < 20

    def test_no_compress_when_count_below_20(self, db_session):
        """测试对话数量不足 20 时不压缩"""
        from app.api.chat import _maybe_compress
        from app.models.conversation import Conversation
        from app.models.session import Session

        session = Session(user_id=1, title="测试")
        db_session.add(session)
        db_session.commit()

        # 创建 5 条对话
        for i in range(5):
            conv = Conversation(
                user_id=1,
                session_id=session.id,
                question=f"问题{i}",
                answer=f"回答{i}",
            )
            db_session.add(conv)
        db_session.commit()

        _maybe_compress(session.id, db_session)

        # 验证对话未被压缩
        remaining = db_session.query(Conversation).filter(
            Conversation.session_id == session.id
        ).count()
        assert remaining == 5
```

- [ ] **Step 2: 运行测试验证**

Run: `cd F:/IntraAI/backend && python -m pytest tests/api/test_chat.py -v --tb=short`
Expected: 所有测试通过

- [ ] **Step 3: Commit**

```bash
git add backend/tests/api/test_chat.py
git commit -m "test: add comprehensive tests for chat API endpoints"
```

---

## Task 9: 测试文档 API (app/api/documents.py)

**Files:**
- Create: `backend/tests/api/test_documents.py`

- [ ] **Step 1: 编写文档 API 测试**

```python
"""文档 API 集成测试"""

import io
from unittest.mock import patch

import pytest


class TestSearchKb:
    """POST /api/documents/search/{kb_id} 测试"""

    @patch("app.api.documents.search")
    @patch("app.api.documents.get_embeddings")
    def test_search_success(self, mock_embeddings, mock_search, client, user_headers, db_session):
        """测试知识库搜索成功"""
        from app.models.knowledge_base import KnowledgeBase

        mock_embeddings.return_value = [[0.1] * 768]
        mock_search.return_value = [("文档内容", {"source": "test.pdf"})]

        kb = KnowledgeBase(name="测试", description="测试", owner_id=1)
        db_session.add(kb)
        db_session.commit()

        res = client.post(
            f"/api/documents/search/{kb.id}?query=测试问题",
            headers=user_headers,
        )

        assert res.status_code == 200
        data = res.json()
        assert data["query"] == "测试问题"
        assert len(data["results"]) > 0

    def test_search_kb_not_found(self, client, user_headers):
        """测试知识库不存在"""
        res = client.post(
            "/api/documents/search/999?query=测试",
            headers=user_headers,
        )

        assert res.status_code == 404


class TestUploadDocument:
    """POST /api/documents/upload/{kb_id} 测试"""

    @patch("app.api.documents.add_documents")
    @patch("app.api.documents.get_embeddings")
    @patch("app.api.documents.split_text")
    @patch("app.api.documents.extract_text")
    def test_upload_txt_success(
        self, mock_extract, mock_split, mock_embeddings, mock_add,
        client, user_headers, db_session
    ):
        """测试上传 TXT 文件成功"""
        from app.models.knowledge_base import KnowledgeBase

        mock_extract.return_value = "文件内容"
        mock_split.return_value = ["切片1", "切片2"]
        mock_embeddings.return_value = [[0.1] * 768, [0.2] * 768]
        mock_add.return_value = 2

        kb = KnowledgeBase(name="测试", description="测试", owner_id=1)
        db_session.add(kb)
        db_session.commit()

        file_content = b"test file content"
        res = client.post(
            f"/api/documents/upload/{kb.id}",
            files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")},
            headers=user_headers,
        )

        assert res.status_code == 200
        data = res.json()
        assert data["filename"] == "test.txt"
        assert data["chunk_count"] == 2

    def test_upload_unsupported_type(self, client, user_headers, db_session):
        """测试上传不支持的文件类型"""
        from app.models.knowledge_base import KnowledgeBase

        kb = KnowledgeBase(name="测试", description="测试", owner_id=1)
        db_session.add(kb)
        db_session.commit()

        res = client.post(
            f"/api/documents/upload/{kb.id}",
            files={"file": ("test.xyz", io.BytesIO(b"content"), "application/octet-stream")},
            headers=user_headers,
        )

        assert res.status_code == 400
        assert "不支持" in res.json()["detail"]

    def test_upload_kb_not_found(self, client, user_headers):
        """测试上传到不存在的知识库"""
        res = client.post(
            "/api/documents/upload/999",
            files={"file": ("test.txt", io.BytesIO(b"content"), "text/plain")},
            headers=user_headers,
        )

        assert res.status_code == 404

    def test_upload_no_permission(self, client, user_headers, db_session, test_user):
        """测试无权限上传"""
        from app.models.knowledge_base import KnowledgeBase
        from app.models.user import User

        # 创建其他用户的知识库
        other_user = User(
            username="other",
            email="other@test.com",
            hashed_password="hash",
            is_admin=False,
        )
        db_session.add(other_user)
        db_session.commit()

        kb = KnowledgeBase(name="其他用户的知识库", description="测试", owner_id=other_user.id)
        db_session.add(kb)
        db_session.commit()

        res = client.post(
            f"/api/documents/upload/{kb.id}",
            files={"file": ("test.txt", io.BytesIO(b"content"), "text/plain")},
            headers=user_headers,
        )

        assert res.status_code == 403


class TestListDocuments:
    """GET /api/documents/list/{kb_id} 测试"""

    def test_list_documents_success(self, client, user_headers, db_session):
        """测试获取文档列表成功"""
        from app.models.document import Document
        from app.models.knowledge_base import KnowledgeBase

        kb = KnowledgeBase(name="测试", description="测试", owner_id=1)
        db_session.add(kb)
        db_session.commit()

        doc = Document(
            filename="test.txt",
            filepath="/path/to/test.txt",
            file_type="txt",
            file_size=100,
            chunk_count=5,
            kb_id=kb.id,
            uploaded_by=1,
        )
        db_session.add(doc)
        db_session.commit()

        res = client.get(
            f"/api/documents/list/{kb.id}",
            headers=user_headers,
        )

        assert res.status_code == 200
        assert len(res.json()) == 1

    def test_list_documents_kb_not_found(self, client, user_headers):
        """测试知识库不存在"""
        res = client.get(
            "/api/documents/list/999",
            headers=user_headers,
        )

        assert res.status_code == 404


class TestDeleteDocument:
    """DELETE /api/documents/{doc_id} 测试"""

    @patch("app.api.documents.os.path.exists")
    @patch("app.api.documents.os.remove")
    def test_delete_document_success(self, mock_remove, mock_exists, client, user_headers, db_session):
        """测试删除文档成功"""
        from app.models.document import Document
        from app.models.knowledge_base import KnowledgeBase

        mock_exists.return_value = True

        kb = KnowledgeBase(name="测试", description="测试", owner_id=1)
        db_session.add(kb)
        db_session.commit()

        doc = Document(
            filename="test.txt",
            filepath="/path/to/test.txt",
            file_type="txt",
            file_size=100,
            chunk_count=5,
            kb_id=kb.id,
            uploaded_by=1,
        )
        db_session.add(doc)
        db_session.commit()

        res = client.delete(
            f"/api/documents/{doc.id}",
            headers=user_headers,
        )

        assert res.status_code == 200
        assert "已删除" in res.json()["message"]

    def test_delete_document_not_found(self, client, user_headers):
        """测试删除不存在的文档"""
        res = client.delete(
            "/api/documents/999",
            headers=user_headers,
        )

        assert res.status_code == 404
```

- [ ] **Step 2: 运行测试验证**

Run: `cd F:/IntraAI/backend && python -m pytest tests/api/test_documents.py -v --tb=short`
Expected: 所有测试通过

- [ ] **Step 3: Commit**

```bash
git add backend/tests/api/test_documents.py
git commit -m "test: add comprehensive tests for documents API endpoints"
```

---

## Task 10: 测试应用入口和其他模块

**Files:**
- Create: `backend/tests/test_main.py`
- Create: `backend/tests/services/test_embedding.py`
- Create: `backend/tests/services/test_vector_store_full.py`

- [ ] **Step 1: 编写应用入口测试**

```python
"""应用入口模块测试"""

from unittest.mock import patch

import pytest


class TestHealthCheck:
    """健康检查接口测试"""

    def test_health_check(self, client):
        """测试健康检查返回正常"""
        res = client.get("/health")

        assert res.status_code == 200
        assert res.json() == {"status": "ok"}


class TestStartup:
    """启动事件测试"""

    @patch("app.main.command")
    @patch("app.main.Config")
    def test_startup_runs_migration(self, mock_config, mock_command):
        """测试启动时执行数据库迁移"""
        from app.main import startup

        startup()

        mock_command.upgrade.assert_called_once()
```

- [ ] **Step 2: 编写向量化服务测试**

```python
"""向量化服务测试"""

from unittest.mock import MagicMock, patch

import pytest


class TestGetEmbeddings:
    """get_embeddings 函数测试"""

    @patch("app.services.embedding._model")
    def test_get_embeddings_success(self, mock_model):
        """测试向量化成功"""
        import numpy as np

        from app.services.embedding import get_embeddings

        mock_model.encode.return_value = np.array([[0.1] * 768, [0.2] * 768])

        result = get_embeddings(["文本1", "文本2"])

        assert len(result) == 2
        assert len(result[0]) == 768

    @patch("app.services.embedding._model")
    def test_get_embeddings_empty_list(self, mock_model):
        """测试空列表"""
        import numpy as np

        from app.services.embedding import get_embeddings

        mock_model.encode.return_value = np.array([])

        result = get_embeddings([])

        assert len(result) == 0
```

- [ ] **Step 3: 编写向量存储完整测试**

```python
"""向量存储服务完整测试"""

from unittest.mock import MagicMock, patch

import pytest


class TestGetCollection:
    """get_collection 函数测试"""

    @patch("app.services.vector_store._client")
    def test_get_collection_success(self, mock_client):
        """测试获取集合成功"""
        from app.services.vector_store import get_collection

        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        result = get_collection(1)

        assert result is mock_collection
        mock_client.get_or_create_collection.assert_called_once_with(
            name="kb_1",
            metadata={"hnsw:space": "cosine"},
        )


class TestAddDocuments:
    """add_documents 函数测试"""

    @patch("app.services.vector_store.get_collection")
    def test_add_documents_success(self, mock_get_collection):
        """测试添加文档成功"""
        from app.services.vector_store import add_documents

        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        mock_get_collection.return_value = mock_collection

        chunks = ["切片1", "切片2"]
        embeddings = [[0.1] * 768, [0.2] * 768]
        metadatas = [{"source": "test.pdf"}, {"source": "test.pdf"}]

        result = add_documents(1, chunks, embeddings, metadatas)

        assert result == 2
        mock_collection.add.assert_called_once()

    @patch("app.services.vector_store.get_collection")
    def test_add_documents_without_metadata(self, mock_get_collection):
        """测试添加文档不带元数据"""
        from app.services.vector_store import add_documents

        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        mock_get_collection.return_value = mock_collection

        result = add_documents(1, ["切片"], [[0.1] * 768])

        assert result == 1


class TestSearch:
    """search 函数测试"""

    @patch("app.services.vector_store.get_collection")
    def test_search_success(self, mock_get_collection):
        """测试搜索成功"""
        from app.services.vector_store import search

        mock_collection = MagicMock()
        mock_collection.count.return_value = 5
        mock_collection.query.return_value = {
            "documents": [["文档内容"]],
            "metadatas": [[{"source": "test.pdf"}]],
        }
        mock_get_collection.return_value = mock_collection

        result = search(1, [0.1] * 768, top_k=3)

        assert len(result) == 1
        assert result[0][0] == "文档内容"
        assert result[0][1]["source"] == "test.pdf"

    @patch("app.services.vector_store.get_collection")
    def test_search_empty_collection(self, mock_get_collection):
        """测试空集合搜索"""
        from app.services.vector_store import search

        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        mock_get_collection.return_value = mock_collection

        result = search(1, [0.1] * 768)

        assert result == []

    @patch("app.services.vector_store.get_collection")
    def test_search_no_metadata(self, mock_get_collection):
        """测试无元数据的搜索结果"""
        from app.services.vector_store import search

        mock_collection = MagicMock()
        mock_collection.count.return_value = 1
        mock_collection.query.return_value = {
            "documents": [["文档内容"]],
            "metadatas": [[None]],
        }
        mock_get_collection.return_value = mock_collection

        result = search(1, [0.1] * 768)

        assert len(result) == 1
        assert result[0][1] == {}
```

- [ ] **Step 4: 运行所有测试验证**

Run: `cd F:/IntraAI/backend && python -m pytest tests/ -v --tb=short 2>&1 | tail -30`
Expected: 所有测试通过

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_main.py backend/tests/services/test_embedding.py backend/tests/services/test_vector_store_full.py
git commit -m "test: add tests for main module, embedding service, and vector store"
```

---

## Task 11: 运行完整测试套件并验证覆盖率

**Files:**
- None (验证步骤)

- [ ] **Step 1: 运行完整测试套件并生成覆盖率报告**

Run: `cd F:/IntraAI/backend && python -m pytest --cov=app --cov-report=term-missing --cov-fail-under=95 2>&1 | tail -50`
Expected: 所有测试通过，覆盖率 >= 95%

- [ ] **Step 2: 如果覆盖率不足，分析缺失的行并补充测试**

根据覆盖率报告中的 Missing 列，针对性地补充测试用例。

- [ ] **Step 3: 最终验证**

Run: `cd F:/IntraAI/backend && python -m pytest --cov=app --cov-report=term-missing --cov-fail-under=95 -v 2>&1 | grep -E "(PASSED|FAILED|TOTAL|coverage)"
Expected: 所有测试通过，TOTAL 覆盖率 >= 95%

- [ ] **Step 4: Commit 最终版本**

```bash
git add -A
git commit -m "test: achieve 95% test coverage target"
```

---

## Self-Review Checklist

- [ ] 所有覆盖率不足的文件都有对应的测试
- [ ] 测试使用 mock 隔离外部依赖（LLM API、ChromaDB、sentence-transformers）
- [ ] 测试覆盖正常流程和异常流程
- [ ] 测试可在 CI 环境稳定运行
- [ ] 覆盖率达到 95% 目标
- [ ] 所有测试文件都有清晰的注释和文档
