"""会话 API 集成测试"""

import pytest


class TestCreateSession:
    def test_create_session(self, client, user_headers):
        res = client.post("/api/sessions/", headers=user_headers)
        assert res.status_code == 200
        assert "id" in res.json()

    def test_create_session_no_auth(self, client):
        res = client.post("/api/sessions/")
        assert res.status_code == 401


class TestListSessions:
    def test_list_sessions(self, client, user_headers):
        client.post("/api/sessions/", headers=user_headers)
        res = client.get("/api/sessions/", headers=user_headers)
        assert res.status_code == 200
        assert isinstance(res.json(), list)
        assert len(res.json()) >= 1


class TestGetSession:
    def test_get_own_session(self, client, user_headers):
        create_res = client.post("/api/sessions/", headers=user_headers)
        session_id = create_res.json()["id"]
        res = client.get(f"/api/sessions/{session_id}", headers=user_headers)
        assert res.status_code == 200
        assert res.json()["id"] == session_id

    def test_get_nonexistent_session(self, client, user_headers):
        res = client.get("/api/sessions/99999", headers=user_headers)
        assert res.status_code == 404

    def test_get_others_session_forbidden(self, client, user_headers, admin_headers):
        create_res = client.post("/api/sessions/", headers=admin_headers)
        session_id = create_res.json()["id"]
        res = client.get(f"/api/sessions/{session_id}", headers=user_headers)
        assert res.status_code == 403


class TestDeleteSession:
    def test_delete_own_session(self, client, user_headers):
        create_res = client.post("/api/sessions/", headers=user_headers)
        session_id = create_res.json()["id"]
        res = client.delete(f"/api/sessions/{session_id}", headers=user_headers)
        assert res.status_code == 200

    def test_delete_nonexistent_session(self, client, user_headers):
        res = client.delete("/api/sessions/99999", headers=user_headers)
        assert res.status_code == 404

    def test_delete_others_session_forbidden(self, client, user_headers, admin_headers):
        create_res = client.post("/api/sessions/", headers=admin_headers)
        session_id = create_res.json()["id"]
        res = client.delete(f"/api/sessions/{session_id}", headers=user_headers)
        assert res.status_code == 403
