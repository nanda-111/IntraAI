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
