"""混合检索 + 重排序服务测试"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest


class TestHybridSearch:
    """hybrid_search 函数测试"""

    @patch("app.services.vector_store._client")
    def test_hybrid_search_empty_collection(self, mock_client):
        """测试空集合返回空结果"""
        from app.services.vector_store import hybrid_search

        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        mock_client.get_or_create_collection.return_value = mock_collection

        results = hybrid_search(1, "测试", [0.1] * 768, top_k=50)

        assert results == []

    @patch("app.services.vector_store._client")
    def test_hybrid_search_merges_results(self, mock_client):
        """测试向量和 BM25 结果合并去重"""
        from app.services.vector_store import hybrid_search

        mock_collection = MagicMock()
        mock_collection.count.return_value = 2

        # 向量检索返回
        mock_collection.query.return_value = {
            "documents": [["文档A", "文档B"]],
            "metadatas": [[{"source": "a.pdf"}, {"source": "b.pdf"}]],
            "distances": [[0.1, 0.3]],
        }

        # 全量文档（用于 BM25）
        mock_collection.get.return_value = {
            "documents": ["文档A", "文档B"],
            "metadatas": [{"source": "a.pdf"}, {"source": "b.pdf"}],
        }

        mock_client.get_or_create_collection.return_value = mock_collection

        results = hybrid_search(1, "测试查询", [0.1] * 768, top_k=50)

        assert len(results) > 0
        # 每个结果应有 4 个元素: (text, meta, vec_score, bm25_score)
        assert len(results[0]) == 4

    @patch("app.services.vector_store._client")
    def test_hybrid_search_returns_top_k(self, mock_client):
        """测试返回数量不超过 top_k"""
        from app.services.vector_store import hybrid_search

        mock_collection = MagicMock()
        mock_collection.count.return_value = 5

        docs = [f"文档{i}" for i in range(5)]
        metas = [{"source": f"{i}.pdf"} for i in range(5)]

        mock_collection.query.return_value = {
            "documents": [docs[:3]],
            "metadatas": [metas[:3]],
            "distances": [[0.1, 0.2, 0.3]],
        }
        mock_collection.get.return_value = {
            "documents": docs,
            "metadatas": metas,
        }
        mock_client.get_or_create_collection.return_value = mock_collection

        results = hybrid_search(1, "测试", [0.1] * 768, top_k=2)

        assert len(results) <= 2

    @patch("app.services.vector_store._client")
    def test_hybrid_search_score_range(self, mock_client):
        """测试分数在合理范围内"""
        from app.services.vector_store import hybrid_search

        mock_collection = MagicMock()
        mock_collection.count.return_value = 1

        mock_collection.query.return_value = {
            "documents": [["测试文档"]],
            "metadatas": [[{"source": "test.pdf"}]],
            "distances": [[0.5]],
        }
        mock_collection.get.return_value = {
            "documents": ["测试文档"],
            "metadatas": [{"source": "test.pdf"}],
        }
        mock_client.get_or_create_collection.return_value = mock_collection

        results = hybrid_search(1, "测试", [0.1] * 768, top_k=50)

        assert len(results) == 1
        _, _, vec_score, bm25_score = results[0]
        assert 0 <= vec_score <= 1
        assert 0 <= bm25_score <= 1


class TestReranker:
    """reranker 服务测试"""

    @patch("app.services.reranker._get_reranker")
    def test_rerank_basic(self, mock_get_reranker):
        """测试基本重排序功能"""
        from app.services.reranker import rerank

        mock_model = MagicMock()
        # 模拟 CrossEncoder.predict 返回 logits
        mock_model.predict.return_value = np.array([2.0, -1.0, 0.5])
        mock_get_reranker.return_value = mock_model

        candidates = [
            ("文档A", {"source": "a.pdf"}),
            ("文档B", {"source": "b.pdf"}),
            ("文档C", {"source": "c.pdf"}),
        ]

        results = rerank("测试问题", candidates, top_k=2)

        assert len(results) == 2
        # 每个结果应有 3 个元素: (text, meta, score)
        assert len(results[0]) == 3
        # 结果应按分数降序排列
        assert results[0][2] >= results[1][2]
        # 最高分应对应 logit=2.0 的文档
        assert results[0][0] == "文档A"

    @patch("app.services.reranker._get_reranker")
    def test_rerank_empty_candidates(self, mock_get_reranker):
        """测试空候选列表"""
        from app.services.reranker import rerank

        results = rerank("问题", [], top_k=5)

        assert results == []

    @patch("app.services.reranker._get_reranker")
    def test_rerank_score_normalization(self, mock_get_reranker):
        """测试分数归一化到 [0, 1]"""
        from app.services.reranker import rerank

        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([10.0, -10.0])
        mock_get_reranker.return_value = mock_model

        candidates = [
            ("高分文档", {}),
            ("低分文档", {}),
        ]

        results = rerank("问题", candidates, top_k=2)

        for _, _, score in results:
            assert 0 <= score <= 1

    @patch("app.services.reranker._get_reranker")
    def test_rerank_top_k_limit(self, mock_get_reranker):
        """测试 top_k 限制返回数量"""
        from app.services.reranker import rerank

        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        mock_get_reranker.return_value = mock_model

        candidates = [(f"文档{i}", {}) for i in range(5)]

        results = rerank("问题", candidates, top_k=3)

        assert len(results) == 3
