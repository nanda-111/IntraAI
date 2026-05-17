"""用户 API 集成测试（/me）"""

import pytest


class TestGetMe:
    """获取当前用户信息"""

    def test_get_me_success(self, client, user_headers):
        res = client.get("/api/users/me", headers=user_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"

    def test_get_me_no_token(self, client):
        res = client.get("/api/users/me")
        assert res.status_code == 401

    def test_get_me_invalid_token(self, client):
        res = client.get(
            "/api/users/me",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert res.status_code == 401


class TestHealthCheck:
    """健康检查"""

    def test_health(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"


class TestAdminCheck:
    """管理员权限检查"""

    def test_admin_route_forbidden_for_normal_user(self, client, user_headers):
        res = client.get("/api/admin/users", headers=user_headers)
        assert res.status_code == 403
        assert "管理员权限" in res.json()["detail"]

    def test_admin_route_allowed_for_admin(self, client, admin_headers):
        res = client.get("/api/admin/users", headers=admin_headers)
        assert res.status_code == 200
