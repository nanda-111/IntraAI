"""知识库 API 集成测试"""


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
