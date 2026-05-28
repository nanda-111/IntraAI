"""向量化服务测试"""

from unittest.mock import patch


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
