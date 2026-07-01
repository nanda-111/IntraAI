"""知识库 API 集成测试"""

import os


class TestCreateKB:
    def test_create_kb(self, client, admin_headers):
        res = client.post(
            "/api/knowledge-bases/",
            json={"name": "测试知识库", "description": "描述"},
            headers=admin_headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "测试知识库"
        assert data["description"] == "描述"
        assert "id" in data

    def test_create_kb_no_auth(self, client):
        res = client.post(
            "/api/knowledge-bases/",
            json={"name": "测试", "description": ""},
        )
        assert res.status_code == 401

    def test_create_kb_normal_user_forbidden(self, client, user_headers):
        res = client.post(
            "/api/knowledge-bases/",
            json={"name": "测试", "description": ""},
            headers=user_headers,
        )
        assert res.status_code == 403


class TestListKBs:
    def test_list_kbs_admin(self, client, admin_headers):
        client.post(
            "/api/knowledge-bases/",
            json={"name": "知识库A", "description": ""},
            headers=admin_headers,
        )
        res = client.get("/api/knowledge-bases/", headers=admin_headers)
        assert res.status_code == 200
        assert len(res.json()) >= 1

    def test_list_kbs_user_sees_all(self, client, admin_headers, user_headers):
        client.post(
            "/api/knowledge-bases/",
            json={"name": "知识库B", "description": ""},
            headers=admin_headers,
        )
        res = client.get("/api/knowledge-bases/", headers=user_headers)
        assert res.status_code == 200
        assert len(res.json()) >= 1

    def test_list_kbs_search(self, client, admin_headers):
        client.post(
            "/api/knowledge-bases/",
            json={"name": "搜索测试XYZ", "description": ""},
            headers=admin_headers,
        )
        res = client.get("/api/knowledge-bases/?q=XYZ", headers=admin_headers)
        assert res.status_code == 200
        assert any("XYZ" in kb["name"] for kb in res.json())


class TestGetKB:
    def test_get_kb(self, client, admin_headers):
        create_res = client.post(
            "/api/knowledge-bases/",
            json={"name": "详情测试", "description": ""},
            headers=admin_headers,
        )
        kb_id = create_res.json()["id"]
        res = client.get(f"/api/knowledge-bases/{kb_id}", headers=admin_headers)
        assert res.status_code == 200
        assert res.json()["name"] == "详情测试"

    def test_get_nonexistent_kb(self, client, admin_headers):
        res = client.get("/api/knowledge-bases/99999", headers=admin_headers)
        assert res.status_code == 404

    def test_get_kb_user_can_view(self, client, admin_headers, user_headers):
        create_res = client.post(
            "/api/knowledge-bases/",
            json={"name": "用户可见", "description": ""},
            headers=admin_headers,
        )
        kb_id = create_res.json()["id"]
        res = client.get(f"/api/knowledge-bases/{kb_id}", headers=user_headers)
        assert res.status_code == 200


class TestUpdateKB:
    def test_update_kb(self, client, admin_headers):
        create_res = client.post(
            "/api/knowledge-bases/",
            json={"name": "旧名称", "description": "旧描述"},
            headers=admin_headers,
        )
        kb_id = create_res.json()["id"]
        res = client.put(
            f"/api/knowledge-bases/{kb_id}",
            json={"name": "新名称"},
            headers=admin_headers,
        )
        assert res.status_code == 200
        assert res.json()["name"] == "新名称"
        assert res.json()["description"] == "旧描述"

    def test_update_description_only(self, client, admin_headers):
        create_res = client.post(
            "/api/knowledge-bases/",
            json={"name": "不变", "description": "旧描述"},
            headers=admin_headers,
        )
        kb_id = create_res.json()["id"]
        res = client.put(
            f"/api/knowledge-bases/{kb_id}",
            json={"description": "新描述"},
            headers=admin_headers,
        )
        assert res.status_code == 200
        assert res.json()["name"] == "不变"
        assert res.json()["description"] == "新描述"

    def test_update_nonexistent_kb(self, client, admin_headers):
        res = client.put(
            "/api/knowledge-bases/99999",
            json={"name": "不存在"},
            headers=admin_headers,
        )
        assert res.status_code == 404

    def test_update_kb_normal_user_forbidden(self, client, admin_headers, user_headers):
        create_res = client.post(
            "/api/knowledge-bases/",
            json={"name": "管理员的", "description": ""},
            headers=admin_headers,
        )
        kb_id = create_res.json()["id"]
        res = client.put(
            f"/api/knowledge-bases/{kb_id}",
            json={"name": "尝试修改"},
            headers=user_headers,
        )
        assert res.status_code == 403


class TestDeleteKB:
    def test_delete_kb(self, client, admin_headers):
        create_res = client.post(
            "/api/knowledge-bases/",
            json={"name": "待删除", "description": ""},
            headers=admin_headers,
        )
        kb_id = create_res.json()["id"]
        res = client.delete(f"/api/knowledge-bases/{kb_id}", headers=admin_headers)
        assert res.status_code == 200

    def test_delete_nonexistent_kb(self, client, admin_headers):
        res = client.delete("/api/knowledge-bases/99999", headers=admin_headers)
        assert res.status_code == 404

    def test_delete_kb_normal_user_forbidden(self, client, admin_headers, user_headers):
        create_res = client.post(
            "/api/knowledge-bases/",
            json={"name": "管理员的", "description": ""},
            headers=admin_headers,
        )
        kb_id = create_res.json()["id"]
        res = client.delete(f"/api/knowledge-bases/{kb_id}", headers=user_headers)
        assert res.status_code == 403

    def test_delete_kb_with_documents(self, client, admin_headers, db_session, monkeypatch):
        """测试删除有文档的知识库时清理物理文件和目录"""
        from unittest.mock import patch

        from app.models.document import Document

        # 创建知识库
        create_res = client.post(
            "/api/knowledge-bases/",
            json={"name": "带文档的知识库", "description": ""},
            headers=admin_headers,
        )
        kb_id = create_res.json()["id"]

        # 创建一个关联文档
        doc = Document(
            filename="test.pdf",
            filepath="/fake/path/test.pdf",
            file_type="pdf",
            file_size=1024,
            chunk_count=3,
            kb_id=kb_id,
            uploaded_by=1,
        )
        db_session.add(doc)
        db_session.commit()

        mock_remove = monkeypatch.setattr("os.remove", lambda p: None)
        mock_exists = monkeypatch.setattr("os.path.exists", lambda p: True)
        mock_isdir = monkeypatch.setattr("os.path.isdir", lambda p: True)
        mock_rmtree = monkeypatch.setattr("shutil.rmtree", lambda p, **kw: None)

        with patch("app.api.knowledge_bases.delete_collection"):
            res = client.delete(f"/api/knowledge-bases/{kb_id}", headers=admin_headers)
        assert res.status_code == 200
        assert res.json()["message"] == "已删除"


class TestCleanupOrphanKBs:
    def test_cleanup_orphan_no_dir(self, client, admin_headers, monkeypatch):
        """测试清理数据库中存在但目录不存在的知识库"""
        from unittest.mock import patch

        # 创建一个知识库
        create_res = client.post(
            "/api/knowledge-bases/",
            json={"name": "孤儿知识库", "description": ""},
            headers=admin_headers,
        )
        kb_id = create_res.json()["id"]

        # Mock 目录不存在
        monkeypatch.setattr("os.path.isdir", lambda p: False)

        with patch("app.api.knowledge_bases.delete_collection"):
            res = client.post("/api/knowledge-bases/cleanup", headers=admin_headers)
        assert res.status_code == 200
        assert kb_id in res.json()["removed"]
        assert res.json()["count"] >= 1

    def test_cleanup_no_orphans(self, client, admin_headers, monkeypatch):
        """测试没有孤儿知识库时返回空列表"""
        # 所有目录都存在
        monkeypatch.setattr("os.path.isdir", lambda p: True)

        res = client.post("/api/knowledge-bases/cleanup", headers=admin_headers)
        assert res.status_code == 200
        assert res.json()["removed"] == []

    def test_cleanup_forbidden_for_normal_user(self, client, user_headers):
        """普通用户不能执行清理"""
        res = client.post("/api/knowledge-bases/cleanup", headers=user_headers)
        assert res.status_code == 403


class TestProcessFile:
    def test_process_file_basic(self, db_session, monkeypatch):
        """测试 _process_file 基本流程"""
        from unittest.mock import patch

        from app.api.knowledge_bases import _process_file

        # Mock extract_text_with_pages
        monkeypatch.setattr(
            "app.api.knowledge_bases.extract_text_with_pages",
            lambda path, ext: [{"text": "页面内容", "page": 1}],
        )
        # Mock split_document
        monkeypatch.setattr(
            "app.api.knowledge_bases.split_document",
            lambda text, chunk_size, overlap, pages: [
                {"text": "切片1", "page": 1, "title_path": "", "char_offset": 0},
                {"text": "切片2", "page": 1, "title_path": "", "char_offset": 100},
            ],
        )
        # Mock get_embeddings
        monkeypatch.setattr(
            "app.api.knowledge_bases.get_embeddings",
            lambda texts: [[0.1] * 768 for _ in texts],
        )
        # Mock os.path.getsize and getmtime
        monkeypatch.setattr("os.path.getsize", lambda p: 2048)
        monkeypatch.setattr("os.path.getmtime", lambda p: 1234567890.0)

        with patch("app.api.knowledge_bases.add_documents", return_value=2):
            count = _process_file("/fake/test.pdf", "test.pdf", "pdf", 1, 1, db_session)
            assert count == 2

    def test_process_file_empty_pages(self, db_session, monkeypatch):
        """测试文件无文本内容时返回 0"""
        from app.api.knowledge_bases import _process_file

        monkeypatch.setattr(
            "app.api.knowledge_bases.extract_text_with_pages",
            lambda path, ext: [],
        )

        count = _process_file("/fake/empty.pdf", "empty.pdf", "pdf", 1, 1, db_session)
        assert count == 0

    def test_process_file_empty_chunks(self, db_session, monkeypatch):
        """测试切片为空时返回 0"""
        from app.api.knowledge_bases import _process_file

        monkeypatch.setattr(
            "app.api.knowledge_bases.extract_text_with_pages",
            lambda path, ext: [{"text": "短文本", "page": 1}],
        )
        monkeypatch.setattr(
            "app.api.knowledge_bases.split_document",
            lambda text, chunk_size, overlap, pages: [],
        )

        count = _process_file("/fake/short.pdf", "short.pdf", "pdf", 1, 1, db_session)
        assert count == 0


class TestSyncFromUploads:
    def test_sync_no_upload_dir(self, client, admin_headers, monkeypatch):
        """测试 uploads 目录不存在时返回全零"""
        monkeypatch.setattr("os.path.isdir", lambda p: False)

        res = client.post("/api/knowledge-bases/sync", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["created"] == 0
        assert data["updated"] == 0
        assert data["removed"] == 0

    def test_sync_new_directory_creates_kb(self, client, admin_headers, db_session, monkeypatch):
        """测试新目录自动创建知识库"""
        from unittest.mock import patch
        from pathlib import Path

        # Mock upload_root exists
        # We need to mock carefully: upload_root isdir=True, but subdir kb_id isdir also True
        # But the KB doesn't exist in DB yet
        original_isdir = os.path.isdir

        def mock_isdir(path):
            p = str(path)
            # upload root exists
            if p.endswith("uploads"):
                return True
            # The kb_id subdirectory
            if "uploads" in p:
                return True
            return original_isdir(path)

        monkeypatch.setattr("os.path.isdir", mock_isdir)
        monkeypatch.setattr("os.listdir", lambda p: ["5"] if p.endswith("uploads") else [])
        monkeypatch.setattr("os.path.isfile", lambda p: False)

        with patch("app.api.knowledge_bases.delete_collection"):
            res = client.post("/api/knowledge-bases/sync", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["created"] >= 1

    def test_sync_new_files_import(self, client, admin_headers, db_session, monkeypatch):
        """测试同步时导入新文件"""
        from unittest.mock import patch

        # 创建知识库
        from app.models.knowledge_base import KnowledgeBase

        kb = KnowledgeBase(
            id=10,
            name="知识库 10",
            description="",
            owner_id=1,
        )
        db_session.add(kb)
        db_session.commit()

        file_seen = []

        def mock_listdir(path):
            p = str(path)
            if p.endswith("uploads"):
                return ["10"]
            if "10" in p:
                return ["new_doc.txt"]
            return []

        def mock_isfile(path):
            return True

        monkeypatch.setattr("os.path.isdir", lambda p: True)
        monkeypatch.setattr("os.listdir", mock_listdir)
        monkeypatch.setattr("os.path.isfile", mock_isfile)
        monkeypatch.setattr("os.path.getsize", lambda p: 1024)
        monkeypatch.setattr("os.path.getmtime", lambda p: 1234567890.0)

        # Mock process_file dependencies
        monkeypatch.setattr(
            "app.api.knowledge_bases.extract_text_with_pages",
            lambda path, ext: [{"text": "内容", "page": 1}],
        )
        monkeypatch.setattr(
            "app.api.knowledge_bases.split_document",
            lambda text, chunk_size, overlap, pages: [
                {"text": "切片1", "page": 1, "title_path": "", "char_offset": 0},
            ],
        )
        monkeypatch.setattr(
            "app.api.knowledge_bases.get_embeddings",
            lambda texts: [[0.1] * 768 for _ in texts],
        )

        with patch("app.api.knowledge_bases.add_documents", return_value=1):
            with patch("app.api.knowledge_bases.delete_collection"):
                res = client.post("/api/knowledge-bases/sync", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["updated"] >= 1

    def test_sync_deleted_files_cleanup(self, client, admin_headers, db_session, monkeypatch):
        """测试同步时清理磁盘上已删除的文件"""
        from unittest.mock import patch

        from app.models.document import Document
        from app.models.knowledge_base import KnowledgeBase

        # 创建知识库
        kb = KnowledgeBase(id=11, name="知识库 11", description="", owner_id=1)
        db_session.add(kb)
        db_session.commit()

        # 创建文档（DB有但磁盘没有）
        doc = Document(
            filename="deleted_file.txt",
            filepath="/fake/deleted_file.txt",
            file_type="txt",
            file_size=100,
            chunk_count=2,
            kb_id=11,
            uploaded_by=1,
        )
        db_session.add(doc)
        db_session.commit()

        def mock_listdir(path):
            p = str(path)
            if p.endswith("uploads"):
                return ["11"]
            if "11" in p:
                return []  # 磁盘上无文件
            return []

        monkeypatch.setattr("os.path.isdir", lambda p: True)
        monkeypatch.setattr("os.listdir", mock_listdir)
        monkeypatch.setattr("os.path.isfile", lambda p: False)

        with patch("app.api.knowledge_bases.delete_by_source") as mock_del:
            with patch("app.api.knowledge_bases.delete_collection"):
                res = client.post("/api/knowledge-bases/sync", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["removed"] >= 1

    def test_sync_modified_files_reimport(self, client, admin_headers, db_session, monkeypatch):
        """测试同步时重新导入已修改的文件"""
        from unittest.mock import patch

        from app.models.document import Document
        from app.models.knowledge_base import KnowledgeBase

        kb = KnowledgeBase(id=12, name="知识库 12", description="", owner_id=1)
        db_session.add(kb)
        db_session.commit()

        # 创建一个旧记录（old mtime）
        doc = Document(
            filename="modified.txt",
            filepath="/fake/modified.txt",
            file_type="txt",
            file_size=100,
            file_mtime=1000.0,  # 比磁盘文件旧很多
            chunk_count=1,
            kb_id=12,
            uploaded_by=1,
        )
        db_session.add(doc)
        db_session.commit()

        def mock_listdir(path):
            p = str(path)
            if p.endswith("uploads"):
                return ["12"]
            if "12" in p:
                return ["modified.txt"]
            return []

        def mock_isfile(path):
            return True

        monkeypatch.setattr("os.path.isdir", lambda p: True)
        monkeypatch.setattr("os.listdir", mock_listdir)
        monkeypatch.setattr("os.path.isfile", mock_isfile)
        monkeypatch.setattr("os.path.getsize", lambda p: 100)  # same size
        monkeypatch.setattr("os.path.getmtime", lambda p: 9999999.0)  # new mtime

        # Mock process_file dependencies
        monkeypatch.setattr(
            "app.api.knowledge_bases.extract_text_with_pages",
            lambda path, ext: [{"text": "新内容", "page": 1}],
        )
        monkeypatch.setattr(
            "app.api.knowledge_bases.split_document",
            lambda text, chunk_size, overlap, pages: [
                {"text": "切片1", "page": 1, "title_path": "", "char_offset": 0},
            ],
        )
        monkeypatch.setattr(
            "app.api.knowledge_bases.get_embeddings",
            lambda texts: [[0.1] * 768 for _ in texts],
        )

        with patch("app.api.knowledge_bases.add_documents", return_value=1):
            with patch("app.api.knowledge_bases.delete_by_source") as mock_del:
                with patch("app.api.knowledge_bases.delete_collection"):
                    res = client.post("/api/knowledge-bases/sync", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["updated"] >= 1

    def test_sync_orphan_kb_cleanup(self, client, admin_headers, db_session, monkeypatch):
        """测试同步清理数据库中但目录不存在的知识库"""
        from unittest.mock import patch

        from app.models.knowledge_base import KnowledgeBase

        # 创建知识库（其目录不会出现在 listdir 结果中）
        kb = KnowledgeBase(id=99, name="要清理的", description="", owner_id=1)
        db_session.add(kb)
        db_session.commit()

        def mock_listdir(path):
            p = str(path)
            if p.endswith("uploads"):
                return ["1"]  # 不包含 99
            return []

        monkeypatch.setattr("os.path.isdir", lambda p: True)
        monkeypatch.setattr("os.listdir", mock_listdir)
        monkeypatch.setattr("os.path.isfile", lambda p: False)

        with patch("app.api.knowledge_bases.delete_collection") as mock_del_col:
            res = client.post("/api/knowledge-bases/sync", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["removed"] >= 1

    def test_sync_forbidden_for_normal_user(self, client, user_headers):
        """普通用户不能执行同步"""
        res = client.post("/api/knowledge-bases/sync", headers=user_headers)
        assert res.status_code == 403
