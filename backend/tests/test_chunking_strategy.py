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
