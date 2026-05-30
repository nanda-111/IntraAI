"""LangChain 工具模块测试"""

import sys
from unittest.mock import MagicMock, patch

# ---- 模块级 Mock：在 langchain_tools 首次导入前拦截外部依赖 ----
# 1. DuckDuckGoSearchRun 需要 ddgs 包，CI 可能未安装
# 2. sentence_transformers 需要额外安装，CI 可能未安装

_mock_ddg_instance = MagicMock()
_mock_ddg_instance.run.return_value = ""

_ddg_patcher = patch(
    "langchain_community.tools.DuckDuckGoSearchRun",
    return_value=_mock_ddg_instance,
)
_ddg_patcher.start()

# Mock sentence_transformers（CI 中可能未安装）
if "sentence_transformers" not in sys.modules:
    sys.modules["sentence_transformers"] = MagicMock()

# 如果模块之前已因导入失败而缓存了残留状态，清除后重新加载
if "app.services.langchain_tools" in sys.modules:
    del sys.modules["app.services.langchain_tools"]

from app.services.langchain_tools import db_query, rag_search, web_search  # noqa: E402


class TestRagSearchTool:
    """rag_search 工具测试"""

    @patch("app.services.langchain_tools.vector_search")
    @patch("app.services.langchain_tools.get_embeddings")
    def test_rag_search_success(self, mock_embeddings, mock_search):
        """测试知识库搜索成功"""
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
        mock_embeddings.return_value = []

        result = rag_search.invoke({"query": "测试"})

        assert "向量化失败" in result

    @patch("app.services.langchain_tools.vector_search")
    @patch("app.services.langchain_tools.get_embeddings")
    def test_rag_search_no_results(self, mock_embeddings, mock_search):
        """测试搜索无结果"""
        mock_embeddings.return_value = [[0.1] * 768]
        mock_search.return_value = []

        result = rag_search.invoke({"query": "测试"})

        assert "没有找到相关内容" in result

    @patch("app.services.langchain_tools.get_embeddings")
    def test_rag_search_exception(self, mock_embeddings):
        """测试搜索异常"""
        mock_embeddings.side_effect = Exception("测试异常")

        result = rag_search.invoke({"query": "测试"})

        assert "出错" in result


class TestDbQueryTool:
    """db_query 工具测试"""

    def test_db_query_select_success(self):
        """测试 SELECT 查询成功"""
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
        result = db_query.invoke({"sql": "DELETE FROM users"})

        assert "只允许 SELECT" in result

    def test_db_query_reject_dangerous_keywords(self):
        """测试拒绝危险关键词"""
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
        mock_search.run.return_value = "搜索结果内容"

        result = web_search.invoke({"query": "测试搜索"})

        assert result == "搜索结果内容"

    @patch("app.services.langchain_tools._ddg_search")
    def test_web_search_no_results(self, mock_search):
        """测试网页搜索无结果"""
        mock_search.run.return_value = ""

        result = web_search.invoke({"query": "未知搜索"})

        assert "未找到" in result

    @patch("app.services.langchain_tools._ddg_search")
    def test_web_search_exception(self, mock_search):
        """测试网页搜索异常"""
        mock_search.run.side_effect = Exception("网络错误")

        result = web_search.invoke({"query": "测试"})

        assert "出错" in result
