"""向量存储服务完整测试"""

from unittest.mock import MagicMock, patch


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
