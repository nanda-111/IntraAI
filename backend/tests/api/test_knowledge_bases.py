"""知识库 API 集成测试"""


class TestCreateKB:
    def test_create_kb(self, client, user_headers):
        res = client.post(
            "/api/knowledge-bases/",
            json={"name": "测试知识库", "description": "描述"},
            headers=user_headers,
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


class TestListKBs:
    def test_list_kbs_user_sees_own(self, client, user_headers):
        client.post(
            "/api/knowledge-bases/",
            json={"name": "我的知识库", "description": ""},
            headers=user_headers,
        )
        res = client.get("/api/knowledge-bases/", headers=user_headers)
        assert res.status_code == 200
        assert len(res.json()) >= 1

    def test_list_kbs_admin_sees_all(self, client, user_headers, admin_headers):
        client.post(
            "/api/knowledge-bases/",
            json={"name": "用户的知识库", "description": ""},
            headers=user_headers,
        )
        res = client.get("/api/knowledge-bases/", headers=admin_headers)
        assert res.status_code == 200


class TestGetKB:
    def test_get_own_kb(self, client, user_headers):
        create_res = client.post(
            "/api/knowledge-bases/",
            json={"name": "我的", "description": ""},
            headers=user_headers,
        )
        kb_id = create_res.json()["id"]
        res = client.get(f"/api/knowledge-bases/{kb_id}", headers=user_headers)
        assert res.status_code == 200
        assert res.json()["name"] == "我的"

    def test_get_nonexistent_kb(self, client, user_headers):
        res = client.get("/api/knowledge-bases/99999", headers=user_headers)
        assert res.status_code == 404

    def test_get_others_kb_forbidden(self, client, user_headers, admin_headers):
        create_res = client.post(
            "/api/knowledge-bases/",
            json={"name": "管理员的", "description": ""},
            headers=admin_headers,
        )
        kb_id = create_res.json()["id"]
        res = client.get(f"/api/knowledge-bases/{kb_id}", headers=user_headers)
        assert res.status_code == 403


class TestUpdateKB:
    def test_update_own_kb(self, client, user_headers):
        create_res = client.post(
            "/api/knowledge-bases/",
            json={"name": "旧名称", "description": "旧描述"},
            headers=user_headers,
        )
        kb_id = create_res.json()["id"]
        res = client.put(
            f"/api/knowledge-bases/{kb_id}",
            json={"name": "新名称"},
            headers=user_headers,
        )
        assert res.status_code == 200
        assert res.json()["name"] == "新名称"
        assert res.json()["description"] == "旧描述"

    def test_update_description_only(self, client, user_headers):
        create_res = client.post(
            "/api/knowledge-bases/",
            json={"name": "不变", "description": "旧描述"},
            headers=user_headers,
        )
        kb_id = create_res.json()["id"]
        res = client.put(
            f"/api/knowledge-bases/{kb_id}",
            json={"description": "新描述"},
            headers=user_headers,
        )
        assert res.status_code == 200
        assert res.json()["name"] == "不变"
        assert res.json()["description"] == "新描述"

    def test_update_nonexistent_kb(self, client, user_headers):
        res = client.put(
            "/api/knowledge-bases/99999",
            json={"name": "不存在"},
            headers=user_headers,
        )
        assert res.status_code == 404

    def test_update_others_kb_forbidden(self, client, user_headers, admin_headers):
        """非管理员修改他人知识库应被拒绝"""
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
    def test_delete_own_kb(self, client, user_headers):
        create_res = client.post(
            "/api/knowledge-bases/",
            json={"name": "待删除", "description": ""},
            headers=user_headers,
        )
        kb_id = create_res.json()["id"]
        res = client.delete(f"/api/knowledge-bases/{kb_id}", headers=user_headers)
        assert res.status_code == 200

    def test_delete_nonexistent_kb(self, client, user_headers):
        res = client.delete("/api/knowledge-bases/99999", headers=user_headers)
        assert res.status_code == 404

    def test_delete_others_kb_forbidden(self, client, user_headers, admin_headers):
        create_res = client.post(
            "/api/knowledge-bases/",
            json={"name": "管理员的", "description": ""},
            headers=admin_headers,
        )
        kb_id = create_res.json()["id"]
        res = client.delete(f"/api/knowledge-bases/{kb_id}", headers=user_headers)
        assert res.status_code == 403
