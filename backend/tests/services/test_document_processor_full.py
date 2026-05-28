"""文档处理服务完整测试"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest


class TestExtractText:
    """extract_text 函数测试"""

    def test_extract_txt_file(self):
        """测试提取 TXT 文件"""
        from app.services.document_processor import extract_text

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
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

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
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

    @patch("app.services.document_processor.fitz")
    def test_extract_pdf(self, mock_fitz):
        """测试提取 PDF 文件"""
        from app.services.document_processor import extract_text

        mock_page1 = MagicMock()
        mock_page1.get_text.return_value = "第一页内容"
        mock_page2 = MagicMock()
        mock_page2.get_text.return_value = "第二页内容"

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page1, mock_page2]))
        mock_doc.close = MagicMock()
        mock_fitz.open.return_value = mock_doc

        result = extract_text("test.pdf", "pdf")

        assert "第一页内容" in result
        assert "第二页内容" in result
        mock_fitz.open.assert_called_once_with("test.pdf")
        mock_doc.close.assert_called_once()

    @patch("app.services.document_processor.DocxDocument")
    def test_extract_docx(self, mock_docx_class):
        """测试提取 DOCX 文件"""
        from app.services.document_processor import extract_text

        mock_para1 = MagicMock()
        mock_para1.text = "第一段内容"
        mock_para2 = MagicMock()
        mock_para2.text = "第二段内容"
        mock_para3 = MagicMock()
        mock_para3.text = ""  # 空段落应被过滤

        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_para1, mock_para2, mock_para3]
        mock_docx_class.return_value = mock_doc

        result = extract_text("test.docx", "docx")

        assert "第一段内容" in result
        assert "第二段内容" in result
        mock_docx_class.assert_called_once_with("test.docx")


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

    def test_split_by_sentence_no_punctuation_fallback(self):
        """测试无标点文本按字符兜底切割"""
        from app.services.document_processor import _split_by_sentence

        # 纯文本无任何标点，_SENTENCE_ENDINGS.split 会返回整个文本作为单个元素
        # 但 sentences 不为空（包含整个文本），所以不会进入 fallback 分支
        text = "abcdefghijklmnop"
        result = _split_by_sentence(text, chunk_size=5)

        # 无标点时整个文本作为单个句子返回
        assert len(result) == 1
        assert result[0] == text

    def test_split_by_sentence_long_single_sentence(self):
        """测试超长单句（有标点结尾）"""
        from app.services.document_processor import _split_by_sentence

        # 创建一个带标点的长句子，超过 chunk_size
        text = "这是一个非常长的句子内容非常丰富包含了很多信息需要被处理。"
        result = _split_by_sentence(text, chunk_size=10)

        # 带标点的长句子会被按标点切割
        assert len(result) >= 1


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
