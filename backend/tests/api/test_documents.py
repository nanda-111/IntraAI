"""文档 API 集成测试"""

import io
from unittest.mock import patch


class TestSearchKb:
    """POST /api/documents/search/{kb_id} 测试"""

    @patch("app.api.documents.search")
    @patch("app.api.documents.get_embeddings")
    def test_search_success(self, mock_embeddings, mock_search, client, user_headers, db_session):
        """测试知识库搜索成功"""
        from app.models.knowledge_base import KnowledgeBase

        mock_embeddings.return_value = [[0.1] * 768]
        mock_search.return_value = [("文档内容", {"source": "test.pdf"})]

        kb = KnowledgeBase(name="测试", description="测试", owner_id=1)
        db_session.add(kb)
        db_session.commit()

        res = client.post(
            f"/api/documents/search/{kb.id}?query=测试问题",
            headers=user_headers,
        )

        assert res.status_code == 200
        data = res.json()
        assert data["query"] == "测试问题"
        assert len(data["results"]) > 0

    def test_search_kb_not_found(self, client, user_headers):
        """测试知识库不存在"""
        res = client.post(
            "/api/documents/search/999?query=测试",
            headers=user_headers,
        )

        assert res.status_code == 404

    def test_search_no_auth(self, client):
        """测试未认证搜索"""
        res = client.post("/api/documents/search/1?query=测试")

        assert res.status_code == 401


class TestUploadDocument:
    """POST /api/documents/upload/{kb_id} 测试"""

    @patch("app.api.documents.add_documents")
    @patch("app.api.documents.get_embeddings")
    @patch("app.api.documents.split_text")
    @patch("app.api.documents.extract_text")
    def test_upload_txt_success(
        self, mock_extract, mock_split, mock_embeddings, mock_add,
        client, user_headers, db_session
    ):
        """测试上传 TXT 文件成功"""
        from app.models.knowledge_base import KnowledgeBase

        mock_extract.return_value = "文件内容"
        mock_split.return_value = ["切片1", "切片2"]
        mock_embeddings.return_value = [[0.1] * 768, [0.2] * 768]
        mock_add.return_value = 2

        kb = KnowledgeBase(name="测试", description="测试", owner_id=1)
        db_session.add(kb)
        db_session.commit()

        file_content = b"test file content"
        res = client.post(
            f"/api/documents/upload/{kb.id}",
            files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")},
            headers=user_headers,
        )

        assert res.status_code == 200
        data = res.json()
        assert data["filename"] == "test.txt"
        assert data["chunk_count"] == 2

    @patch("app.api.documents.add_documents")
    @patch("app.api.documents.get_embeddings")
    @patch("app.api.documents.split_text")
    @patch("app.api.documents.extract_text")
    def test_upload_md_success(
        self, mock_extract, mock_split, mock_embeddings, mock_add,
        client, user_headers, db_session
    ):
        """测试上传 Markdown 文件成功"""
        from app.models.knowledge_base import KnowledgeBase

        mock_extract.return_value = "# 标题"
        mock_split.return_value = ["切片1"]
        mock_embeddings.return_value = [[0.1] * 768]
        mock_add.return_value = 1

        kb = KnowledgeBase(name="测试", description="测试", owner_id=1)
        db_session.add(kb)
        db_session.commit()

        res = client.post(
            f"/api/documents/upload/{kb.id}",
            files={"file": ("readme.md", io.BytesIO(b"# Hello"), "text/markdown")},
            headers=user_headers,
        )

        assert res.status_code == 200
        assert res.json()["file_type"] == "md"

    def test_upload_unsupported_type(self, client, user_headers, db_session):
        """测试上传不支持的文件类型"""
        from app.models.knowledge_base import KnowledgeBase

        kb = KnowledgeBase(name="测试", description="测试", owner_id=1)
        db_session.add(kb)
        db_session.commit()

        res = client.post(
            f"/api/documents/upload/{kb.id}",
            files={"file": ("test.xyz", io.BytesIO(b"content"), "application/octet-stream")},
            headers=user_headers,
        )

        assert res.status_code == 400
        assert "不支持" in res.json()["detail"]

    def test_upload_exe_rejected(self, client, user_headers, db_session):
        """测试上传可执行文件被拒绝"""
        from app.models.knowledge_base import KnowledgeBase

        kb = KnowledgeBase(name="测试", description="测试", owner_id=1)
        db_session.add(kb)
        db_session.commit()

        res = client.post(
            f"/api/documents/upload/{kb.id}",
            files={"file": ("malware.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
            headers=user_headers,
        )

        assert res.status_code == 400

    def test_upload_kb_not_found(self, client, user_headers):
        """测试上传到不存在的知识库"""
        res = client.post(
            "/api/documents/upload/999",
            files={"file": ("test.txt", io.BytesIO(b"content"), "text/plain")},
            headers=user_headers,
        )

        assert res.status_code == 404

    def test_upload_no_permission(self, client, user_headers, db_session, test_user):
        """测试无权限上传"""
        from app.models.knowledge_base import KnowledgeBase
        from app.models.user import User

        # 创建其他用户的知识库
        other_user = User(
            username="other",
            email="other@test.com",
            hashed_password="hash",
            is_admin=False,
            is_active=True,
        )
        db_session.add(other_user)
        db_session.commit()

        kb = KnowledgeBase(name="其他用户的知识库", description="测试", owner_id=other_user.id)
        db_session.add(kb)
        db_session.commit()

        res = client.post(
            f"/api/documents/upload/{kb.id}",
            files={"file": ("test.txt", io.BytesIO(b"content"), "text/plain")},
            headers=user_headers,
        )

        assert res.status_code == 403

    def test_upload_no_auth(self, client, db_session):
        """测试未认证上传"""
        from app.models.knowledge_base import KnowledgeBase

        kb = KnowledgeBase(name="测试", description="测试", owner_id=1)
        db_session.add(kb)
        db_session.commit()

        res = client.post(
            f"/api/documents/upload/{kb.id}",
            files={"file": ("test.txt", io.BytesIO(b"content"), "text/plain")},
        )

        assert res.status_code == 401

    @patch("app.api.documents.add_documents")
    @patch("app.api.documents.get_embeddings")
    @patch("app.api.documents.split_text")
    @patch("app.api.documents.extract_text")
    def test_upload_admin_can_upload_to_others_kb(
        self, mock_extract, mock_split, mock_embeddings, mock_add,
        client, admin_headers, db_session
    ):
        """测试管理员可以上传到他人的知识库"""
        from app.models.knowledge_base import KnowledgeBase

        mock_extract.return_value = "内容"
        mock_split.return_value = ["切片"]
        mock_embeddings.return_value = [[0.1] * 768]
        mock_add.return_value = 1

        kb = KnowledgeBase(name="用户的知识库", description="测试", owner_id=999)
        db_session.add(kb)
        db_session.commit()

        res = client.post(
            f"/api/documents/upload/{kb.id}",
            files={"file": ("test.txt", io.BytesIO(b"content"), "text/plain")},
            headers=admin_headers,
        )

        assert res.status_code == 200


class TestListDocuments:
    """GET /api/documents/list/{kb_id} 测试"""

    def test_list_documents_success(self, client, user_headers, db_session):
        """测试获取文档列表成功"""
        from app.models.document import Document
        from app.models.knowledge_base import KnowledgeBase

        kb = KnowledgeBase(name="测试", description="测试", owner_id=1)
        db_session.add(kb)
        db_session.commit()

        doc = Document(
            filename="test.txt",
            filepath="/path/to/test.txt",
            file_type="txt",
            file_size=100,
            chunk_count=5,
            kb_id=kb.id,
            uploaded_by=1,
        )
        db_session.add(doc)
        db_session.commit()

        res = client.get(
            f"/api/documents/list/{kb.id}",
            headers=user_headers,
        )

        assert res.status_code == 200
        assert len(res.json()) == 1

    def test_list_documents_empty(self, client, user_headers, db_session):
        """测试知识库无文档时返回空列表"""
        from app.models.knowledge_base import KnowledgeBase

        kb = KnowledgeBase(name="测试", description="测试", owner_id=1)
        db_session.add(kb)
        db_session.commit()

        res = client.get(
            f"/api/documents/list/{kb.id}",
            headers=user_headers,
        )

        assert res.status_code == 200
        assert res.json() == []

    def test_list_documents_kb_not_found(self, client, user_headers):
        """测试知识库不存在"""
        res = client.get(
            "/api/documents/list/999",
            headers=user_headers,
        )

        assert res.status_code == 404

    def test_list_documents_no_permission(self, client, user_headers, db_session):
        """测试无权限查看他人知识库的文档"""
        from app.models.knowledge_base import KnowledgeBase
        from app.models.user import User

        other_user = User(
            username="other",
            email="other@test.com",
            hashed_password="hash",
            is_admin=False,
            is_active=True,
        )
        db_session.add(other_user)
        db_session.commit()

        kb = KnowledgeBase(name="其他用户的知识库", description="测试", owner_id=other_user.id)
        db_session.add(kb)
        db_session.commit()

        res = client.get(
            f"/api/documents/list/{kb.id}",
            headers=user_headers,
        )

        assert res.status_code == 403

    def test_list_documents_no_auth(self, client):
        """测试未认证获取文档列表"""
        res = client.get("/api/documents/list/1")

        assert res.status_code == 401


class TestDeleteDocument:
    """DELETE /api/documents/{doc_id} 测试"""

    @patch("app.api.documents.os.path.exists")
    @patch("app.api.documents.os.remove")
    def test_delete_document_success(self, mock_remove, mock_exists, client, user_headers, db_session):
        """测试删除文档成功"""
        from app.models.document import Document
        from app.models.knowledge_base import KnowledgeBase

        mock_exists.return_value = True

        kb = KnowledgeBase(name="测试", description="测试", owner_id=1)
        db_session.add(kb)
        db_session.commit()

        doc = Document(
            filename="test.txt",
            filepath="/path/to/test.txt",
            file_type="txt",
            file_size=100,
            chunk_count=5,
            kb_id=kb.id,
            uploaded_by=1,
        )
        db_session.add(doc)
        db_session.commit()

        res = client.delete(
            f"/api/documents/{doc.id}",
            headers=user_headers,
        )

        assert res.status_code == 200
        assert "已删除" in res.json()["message"]

    @patch("app.api.documents.os.path.exists")
    @patch("app.api.documents.os.remove")
    def test_delete_document_file_already_removed(self, mock_remove, mock_exists, client, user_headers, db_session):
        """测试文件已被手动删除时仍可删除记录"""
        from app.models.document import Document
        from app.models.knowledge_base import KnowledgeBase

        mock_exists.return_value = False

        kb = KnowledgeBase(name="测试", description="测试", owner_id=1)
        db_session.add(kb)
        db_session.commit()

        doc = Document(
            filename="test.txt",
            filepath="/path/to/test.txt",
            file_type="txt",
            file_size=100,
            chunk_count=5,
            kb_id=kb.id,
            uploaded_by=1,
        )
        db_session.add(doc)
        db_session.commit()

        res = client.delete(
            f"/api/documents/{doc.id}",
            headers=user_headers,
        )

        assert res.status_code == 200
        mock_remove.assert_not_called()

    def test_delete_document_not_found(self, client, user_headers):
        """测试删除不存在的文档"""
        res = client.delete(
            "/api/documents/999",
            headers=user_headers,
        )

        assert res.status_code == 404

    @patch("app.api.documents.os.path.exists")
    def test_delete_document_no_permission(self, mock_exists, client, user_headers, db_session):
        """测试无权限删除他人文档"""
        from app.models.document import Document
        from app.models.knowledge_base import KnowledgeBase
        from app.models.user import User

        mock_exists.return_value = True

        other_user = User(
            username="other",
            email="other@test.com",
            hashed_password="hash",
            is_admin=False,
            is_active=True,
        )
        db_session.add(other_user)
        db_session.commit()

        kb = KnowledgeBase(name="测试", description="测试", owner_id=other_user.id)
        db_session.add(kb)
        db_session.commit()

        doc = Document(
            filename="test.txt",
            filepath="/path/to/test.txt",
            file_type="txt",
            file_size=100,
            chunk_count=5,
            kb_id=kb.id,
            uploaded_by=other_user.id,
        )
        db_session.add(doc)
        db_session.commit()

        res = client.delete(
            f"/api/documents/{doc.id}",
            headers=user_headers,
        )

        assert res.status_code == 403

    def test_delete_document_no_auth(self, client):
        """测试未认证删除文档"""
        res = client.delete("/api/documents/1")

        assert res.status_code == 401
