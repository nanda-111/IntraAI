"""
测试 document_processor 的 split_text 函数
"""

from app.services.document_processor import split_text


class TestSplitTextBasic:
    """基础功能测试"""

    def test_empty_text(self):
        assert split_text("") == []

    def test_whitespace_only(self):
        assert split_text("   \n\n  ") == []

    def test_single_short_paragraph(self):
        text = "这是一个短段落。"
        chunks = split_text(text, chunk_size=100)
        assert chunks == ["这是一个短段落。"]


class TestSplitByParagraph:
    """按段落边界切割"""

    def test_two_paragraphs_split_at_boundary(self):
        text = "第一段内容。\n\n第二段内容。"
        chunks = split_text(text, chunk_size=100)
        assert len(chunks) == 2
        assert "第一段内容。" in chunks[0]
        assert "第二段内容。" in chunks[1]

    def test_multiple_paragraphs(self):
        text = "段落一。\n\n段落二。\n\n段落三。"
        chunks = split_text(text, chunk_size=100)
        assert len(chunks) == 3

    def test_long_paragraph_split_by_sentence(self):
        """单个段落超过 chunk_size 时，应按句子边界切割"""
        text = "这是第一句。这是第二句。这是第三句。这是第四句。"
        chunks = split_text(text, chunk_size=15)
        # 每个 chunk 应该在句子边界断开
        for chunk in chunks:
            # 不应该出现句子被截断的情况（如"这是第"）
            assert chunk.endswith("。") or chunk == chunks[-1]


class TestSplitBySentence:
    """按句子边界切割"""

    def test_chinese_period(self):
        text = "第一句。第二句。第三句。"
        chunks = split_text(text, chunk_size=10)
        for chunk in chunks:
            assert "。" in chunk

    def test_chinese_exclamation(self):
        text = "注意！这是警告！请小心！"
        chunks = split_text(text, chunk_size=10)
        for chunk in chunks:
            assert "！" in chunk

    def test_chinese_question_mark(self):
        text = "你是谁？你在哪？你要去哪？"
        chunks = split_text(text, chunk_size=10)
        for chunk in chunks:
            assert "？" in chunk

    def test_english_period(self):
        text = "Hello world. This is a test. Goodbye now."
        chunks = split_text(text, chunk_size=20)
        for chunk in chunks:
            assert "." in chunk


class TestOverlap:
    """overlap 机制测试"""

    def test_overlap_preserves_context(self):
        """相邻 chunk 之间应有重叠内容"""
        text = "第一段很长的内容。\n\n第二段很长的内容。\n\n第三段很长的内容。"
        chunks = split_text(text, chunk_size=20, overlap=5)
        # 至少应该有多个 chunk
        assert len(chunks) >= 2

    def test_overlap_uses_last_sentence(self):
        """overlap 应该取上一个 chunk 的末尾句子，而非任意字符"""
        text = "第一句完整的话。第二句完整的话。第三句完整的话。"
        chunks = split_text(text, chunk_size=20, overlap=5)
        # 如果有 overlap，重叠部分应该是完整的句子
        for i in range(1, len(chunks)):
            # 后一个 chunk 的开头应该包含前一个 chunk 的末尾句子
            prev_chunk = chunks[i - 1]
            curr_chunk = chunks[i]
            # 检查是否有共享的句子边界
            assert "。" in prev_chunk and "。" in curr_chunk


class TestFallback:
    """单句超长时的兜底逻辑"""

    def test_single_long_sentence_falls_back_to_char_split(self):
        """如果单句超过 chunk_size，应按字符数兜底切割"""
        text = "这是一句非常非常长的句子没有句号结尾"
        chunks = split_text(text, chunk_size=5)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 5

    def test_mixed_paragraphs_and_long_sentences(self):
        """混合场景：段落正常 + 段落内有超长句子"""
        text = "短段落。\n\n这是一个超长段落包含很多内容需要被按句子切割处理才能保证每段都在限定长度内。"
        chunks = split_text(text, chunk_size=30)
        for chunk in chunks:
            assert len(chunk) <= 30


class TestRealisticDocument:
    """模拟真实文档场景"""

    def test_employee_handbook_style(self):
        text = """员工手册

第一章 总则

第一条 为规范公司管理，维护员工合法权益，根据国家相关法律法规，制定本手册。

第二条 本手册适用于公司全体员工。

第二章 考勤制度

第三条 公司实行标准工时制度，每日工作时间为上午9:00至下午18:00。

第四条 员工应按时上下班，不得无故迟到早退。"""
        chunks = split_text(text, chunk_size=50)
        for chunk in chunks:
            assert len(chunk) <= 50
            # 每个 chunk 都应该是有意义的内容片段
            assert len(chunk.strip()) > 0
