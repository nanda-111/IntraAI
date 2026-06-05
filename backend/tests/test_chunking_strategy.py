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
        assert text[offset : offset + 4] == "第一章 "

    def test_no_headers(self):
        """无标题文本应返回空列表"""
        from app.services.document_processor import _detect_headers

        text = "普通段落一。\n\n普通段落二。"
        headers = _detect_headers(text)
        assert headers == []


class TestBuildTitlePath:
    """_build_title_path 函数测试"""

    def test_single_header(self):
        """单个标题应返回自身"""
        from app.services.document_processor import _build_title_path

        headers = [(0, "第一章 总则")]
        path = _build_title_path(10, headers)
        assert path == "第一章 总则"

    def test_nested_headers(self):
        """嵌套标题应返回层级路径"""
        from app.services.document_processor import _build_title_path

        headers = [(0, "第二章 薪酬"), (15, "2.1 基本工资")]
        path = _build_title_path(25, headers)
        assert "第二章 薪酬" in path
        assert "2.1 基本工资" in path

    def test_content_before_any_header(self):
        """第一个标题之前的内容，路径为空字符串"""
        from app.services.document_processor import _build_title_path

        headers = [(10, "第一章 标题")]
        path = _build_title_path(2, headers)
        assert path == ""

    def test_no_headers(self):
        """无标题时返回空字符串"""
        from app.services.document_processor import _build_title_path

        path = _build_title_path(0, [])
        assert path == ""


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

    def test_preamble_before_first_header(self):
        """标题之前的前言内容应正确处理"""
        from app.services.document_processor import _split_by_structure

        text = "前言内容在此。\n\n第一章 正式内容。"
        chunks = _split_by_structure(text, chunk_size=100)

        assert len(chunks) >= 2
        # 前言的 title_path 应为空
        preamble_chunks = [c for c in chunks if "前言" in c["text"]]
        assert len(preamble_chunks) == 1
        assert preamble_chunks[0]["title_path"] == ""


class TestSplitBySemantics:
    """_split_by_semantics 函数测试"""

    @patch("app.services.embedding.get_embeddings")
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

    @patch("app.services.embedding.get_embeddings")
    def test_short_text_returns_single_chunk(self, mock_embeddings):
        """只有一个句子时返回单个 chunk"""
        from app.services.document_processor import _split_by_semantics

        mock_embeddings.return_value = [[0.1] * 768]

        chunks = _split_by_semantics("单句文本。", chunk_size=200)
        assert len(chunks) == 1
        assert chunks[0]["text"] == "单句文本。"

    @patch("app.services.embedding.get_embeddings")
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

    @patch("app.services.embedding.get_embeddings")
    def test_empty_text(self, mock_embeddings):
        """空文本返回空列表"""
        from app.services.document_processor import _split_by_semantics

        chunks = _split_by_semantics("", chunk_size=200)
        assert chunks == []
        mock_embeddings.assert_not_called()


class TestSplitDocument:
    """split_document 统一入口测试"""

    def test_returns_list_of_dicts(self):
        """返回值应为 dict 列表，包含 text、title_path、char_offset、page"""
        from app.services.document_processor import split_document

        text = "段落一。\n\n段落二。"
        result = split_document(text, chunk_size=100)

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
        result = split_document(text, chunk_size=100)

        title_paths = [c["title_path"] for c in result]
        assert any("第一章" in p for p in title_paths)

    def test_short_text_no_semantic(self):
        """短文本不应触发语义切分"""
        from app.services.document_processor import split_document

        text = "这是一段短文本。"
        result = split_document(text, chunk_size=500)

        assert len(result) == 1
        assert result[0]["text"] == "这是一段短文本。"

    def test_page_metadata_propagated(self):
        """页码元数据应正确传递到 chunk 中"""
        from app.services.document_processor import split_document

        pages = [("第一页内容。", 1), ("第二页内容。", 2)]
        result = split_document("", chunk_size=100, pages=pages)

        pages_in_result = [c["page"] for c in result]
        assert 1 in pages_in_result
        assert 2 in pages_in_result

    def test_empty_text(self):
        """空文本返回空列表"""
        from app.services.document_processor import split_document

        result = split_document("", chunk_size=100)
        assert result == []

    @patch("app.services.embedding.get_embeddings")
    def test_long_text_without_headers_uses_semantic(self, mock_embeddings):
        """长文本无标题应触发语义切分"""
        from app.services.document_processor import _SHORT_DOC_THRESHOLD, split_document

        def fake_embed(texts):
            result = []
            for i in range(len(texts)):
                if i < len(texts) - 1:
                    result.append([1.0] + [0.0] * 767)
                else:
                    result.append([0.0, 1.0] + [0.0] * 766)
            return result

        mock_embeddings.side_effect = fake_embed

        # 构造超过阈值的长文本，无标题（每段8字，150段=1200字 > 1000）
        text = "这是第一段内容。" * 150
        assert len(text) > _SHORT_DOC_THRESHOLD
        result = split_document(text, chunk_size=200)

        assert len(result) >= 1
        for chunk in result:
            assert chunk["page"] == 1
        mock_embeddings.assert_called_once()

    def test_split_pages_with_empty_page(self):
        """空页面应被跳过"""
        from app.services.document_processor import split_document

        pages = [("", 1), ("第二页内容。", 2)]
        result = split_document("", chunk_size=100, pages=pages)

        # 空页应被跳过，只有第二页的内容
        assert all(c["page"] == 2 for c in result)

    def test_split_pages_with_headers_in_page(self):
        """页面内有标题应使用结构切分"""
        from app.services.document_processor import split_document

        pages = [("# 标题\n\n内容。", 1)]
        result = split_document("", chunk_size=100, pages=pages)

        assert len(result) >= 1
        assert result[0]["page"] == 1


class TestSplitBySentenceEdgeCases:
    """_split_by_sentence 边界测试"""

    def test_empty_sentences_fallback(self):
        """空段落按字符兜底切割"""
        from app.services.document_processor import _split_by_sentence

        result = _split_by_sentence("", chunk_size=5)
        assert result == []

    def test_long_single_sentence_with_punctuation(self):
        """带标点的超长单句应按标点切割后处理"""
        from app.services.document_processor import _split_by_sentence

        # 超长单句带标点，会被拆分成多个句子
        text = "这是一个很长的句子。" * 20
        result = _split_by_sentence(text, chunk_size=10)

        assert len(result) > 1
        for chunk in result:
            assert len(chunk) <= 10


class TestSplitBySemanticsEdgeCases:
    """_split_by_semantics 边界测试"""

    @patch("app.services.embedding.get_embeddings")
    def test_single_sentence_returns_single_chunk(self, mock_embeddings):
        """单句文本返回单个 chunk（不调用 embedding）"""
        from app.services.document_processor import _split_by_semantics

        chunks = _split_by_semantics("一句完整的话。", chunk_size=200)
        assert len(chunks) == 1
        assert chunks[0]["text"] == "一句完整的话。"
        mock_embeddings.assert_not_called()

    @patch("app.services.embedding.get_embeddings")
    def test_chunk_exceeds_size_falls_back(self, mock_embeddings):
        """语义分组超长时应退化为普通切分"""
        from app.services.document_processor import _split_by_semantics

        # 所有句子相似（不会在语义边界切分），但合并后超长
        mock_embeddings.return_value = [[1.0] + [0.0] * 768] * 10

        sentences = ["这是很长的句子内容。"] * 10
        text = "".join(sentences)
        chunks = _split_by_semantics(text, chunk_size=50)

        # 应被切分成多个 chunk
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk["text"]) <= 50
