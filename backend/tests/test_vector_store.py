"""
测试 vector_store 的元数据功能
"""

import pytest

from app.services.vector_store import _client, add_documents, search


@pytest.fixture(autouse=True)
def clean_collection():
    """每个测试前后清理测试用的 collection"""
    try:
        _client.delete_collection("kb_9999")
    except Exception:
        pass
    yield
    try:
        _client.delete_collection("kb_9999")
    except Exception:
        pass


class TestMetadataStorage:
    """元数据存储测试"""

    def test_add_documents_with_metadata(self):
        """add_documents 应该接受并存储 metadata"""
        chunks = ["这是测试内容"]
        embeddings = [[0.1] * 768]
        metadatas = [{"source": "test.pdf"}]
        count = add_documents(kb_id=9999, chunks=chunks, embeddings=embeddings, metadatas=metadatas)
        assert count == 1

    def test_search_returns_metadata(self):
        """search 应该返回每个 chunk 的 metadata"""
        chunks = ["员工手册第一章", "考勤制度第二条"]
        embeddings = [[0.1] * 768, [0.2] * 768]
        metadatas = [
            {"source": "员工手册.pdf"},
            {"source": "考勤制度.docx"},
        ]
        add_documents(kb_id=9999, chunks=chunks, embeddings=embeddings, metadatas=metadatas)

        results = search(kb_id=9999, query_embedding=[0.1] * 768, top_k=2)
        assert len(results) == 2
        # 每个结果应该是 (text, metadata) 元组
        for text, meta in results:
            assert isinstance(text, str)
            assert isinstance(meta, dict)
            assert "source" in meta

    def test_metadata_source_is_correct(self):
        """返回的 metadata source 应该与存入时一致"""
        chunks = ["测试内容A", "测试内容B"]
        embeddings = [[0.1] * 768, [0.9] * 768]
        metadatas = [
            {"source": "文件A.pdf"},
            {"source": "文件B.docx"},
        ]
        add_documents(kb_id=9999, chunks=chunks, embeddings=embeddings, metadatas=metadatas)

        results = search(kb_id=9999, query_embedding=[0.1] * 768, top_k=2)
        sources = {meta["source"] for _, meta in results}
        assert "文件A.pdf" in sources
        assert "文件B.docx" in sources


class TestMetadataOptional:
    """metadata 参数应该可选（向后兼容）"""

    def test_add_without_metadata_still_works(self):
        """不传 metadata 时应该正常工作（向后兼容）"""
        chunks = ["无元数据的切片"]
        embeddings = [[0.3] * 768]
        count = add_documents(kb_id=9999, chunks=chunks, embeddings=embeddings)
        assert count == 1

    def test_search_without_metadata_returns_empty_dict(self):
        """没有 metadata 的记录，search 返回空 dict"""
        chunks = ["无元数据的切片"]
        embeddings = [[0.3] * 768]
        add_documents(kb_id=9999, chunks=chunks, embeddings=embeddings)

        results = search(kb_id=9999, query_embedding=[0.3] * 768, top_k=1)
        assert len(results) == 1
        text, meta = results[0]
        assert text == "无元数据的切片"
        assert meta == {}
