"""管理后台 API 集成测试"""



class TestAdminUsers:
    def test_list_users(self, client, admin_headers, test_user):
        res = client.get("/api/admin/users", headers=admin_headers)
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_list_users_forbidden(self, client, user_headers):
        res = client.get("/api/admin/users", headers=user_headers)
        assert res.status_code == 403

    def test_toggle_user(self, client, admin_headers, test_user):
        res = client.put(
            f"/api/admin/users/{test_user.id}/toggle",
            headers=admin_headers,
        )
        assert res.status_code == 200
        assert res.json()["id"] == test_user.id

    def test_toggle_user_not_found(self, client, admin_headers):
        res = client.put("/api/admin/users/99999/toggle", headers=admin_headers)
        assert res.status_code == 404

    def test_toggle_admin(self, client, admin_headers, test_user):
        res = client.put(
            f"/api/admin/users/{test_user.id}/admin",
            headers=admin_headers,
        )
        assert res.status_code == 200

    def test_toggle_admin_not_found(self, client, admin_headers):
        res = client.put("/api/admin/users/99999/admin", headers=admin_headers)
        assert res.status_code == 404


class TestAdminKBs:
    def test_list_all_kbs(self, client, admin_headers):
        # 先创建一个知识库，确保 admin_list_kbs 的循环体被执行
        client.post(
            "/api/knowledge-bases/",
            json={"name": "测试KB", "description": "用于测试"},
            headers=admin_headers,
        )
        res = client.get("/api/admin/knowledge-bases", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["name"] == "测试KB"


class TestAdminStats:
    def test_get_stats(self, client, admin_headers):
        res = client.get("/api/admin/stats", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert "user_count" in data
        assert "kb_count" in data
        assert "doc_count" in data
        assert "chat_count" in data
        assert "active_user_count" in data


class TestAdminUsageLogs:
    def test_get_usage_logs(self, client, admin_headers, db_session):
        # 先插入一条日志，确保 get_usage_logs 的循环体被执行
        from app.models.usage_log import UsageLog
        from app.models.user import User
        user = db_session.query(User).first()
        if user:
            log = UsageLog(user_id=user.id, action="test_action", tokens_used=100)
            db_session.add(log)
            db_session.commit()
        res = client.get("/api/admin/usage-logs", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert "total" in data
        assert "items" in data

    def test_get_usage_logs_pagination(self, client, admin_headers):
        res = client.get("/api/admin/usage-logs?page=1&size=5", headers=admin_headers)
        assert res.status_code == 200
