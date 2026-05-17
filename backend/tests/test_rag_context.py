"""
测试 RAG 上下文中的来源标记
"""


class TestRagContextFormat:
    """RAG 上下文应包含来源信息"""

    def _build_context(self, results):
        """模拟 rag.py 中拼接 context 的逻辑"""
        if not results:
            return "（无相关资料）"
        parts = []
        for text, meta in results:
            source = meta.get("source", "")
            if source:
                parts.append(f"[来源: {source}]\n{text}")
            else:
                parts.append(text)
        return "\n\n---\n\n".join(parts)

    def test_single_source_with_metadata(self):
        results = [("员工享有年假5天", {"source": "员工手册.pdf"})]
        ctx = self._build_context(results)
        assert "[来源: 员工手册.pdf]" in ctx
        assert "员工享有年假5天" in ctx

    def test_multiple_sources(self):
        results = [
            ("年假5天", {"source": "员工手册.pdf"}),
            ("迟到扣款20元", {"source": "考勤制度.docx"}),
        ]
        ctx = self._build_context(results)
        assert "[来源: 员工手册.pdf]" in ctx
        assert "[来源: 考勤制度.docx]" in ctx
        assert "---" in ctx

    def test_no_metadata_shows_plain_text(self):
        results = [("无来源的内容", {})]
        ctx = self._build_context(results)
        assert "[来源:" not in ctx
        assert "无来源的内容" in ctx

    def test_empty_results(self):
        ctx = self._build_context([])
        assert ctx == "（无相关资料）"
