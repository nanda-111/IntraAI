"""认证 API 集成测试（register / login）"""



class TestRegister:
    """注册接口测试"""

    def test_register_success(self, client):
        res = client.post(
            "/api/auth/register",
            json={"username": "newuser", "email": "new@test.com", "password": "pass123"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@test.com"
        assert data["is_active"] is True
        assert "hashed_password" not in data

    def test_first_user_is_admin(self, client):
        res = client.post(
            "/api/auth/register",
            json={"username": "first", "email": "first@test.com", "password": "pass123"},
        )
        assert res.json()["is_admin"] is True

    def test_second_user_not_admin(self, client):
        client.post(
            "/api/auth/register",
            json={"username": "first", "email": "first@test.com", "password": "pass123"},
        )
        res = client.post(
            "/api/auth/register",
            json={"username": "second", "email": "second@test.com", "password": "pass123"},
        )
        assert res.json()["is_admin"] is False

    def test_duplicate_username(self, client):
        client.post(
            "/api/auth/register",
            json={"username": "dup", "email": "dup1@test.com", "password": "pass123"},
        )
        res = client.post(
            "/api/auth/register",
            json={"username": "dup", "email": "dup2@test.com", "password": "pass123"},
        )
        assert res.status_code == 400
        assert "用户名已存在" in res.json()["detail"]

    def test_duplicate_email(self, client):
        client.post(
            "/api/auth/register",
            json={"username": "user1", "email": "same@test.com", "password": "pass123"},
        )
        res = client.post(
            "/api/auth/register",
            json={"username": "user2", "email": "same@test.com", "password": "pass123"},
        )
        assert res.status_code == 400
        assert "邮箱已注册" in res.json()["detail"]


class TestLogin:
    """登录接口测试"""

    def _register(self, client):
        client.post(
            "/api/auth/register",
            json={"username": "logintest", "email": "login@test.com", "password": "pass123"},
        )

    def test_login_success(self, client):
        self._register(client)
        res = client.post(
            "/api/auth/login",
            json={"username": "logintest", "password": "pass123"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "logintest"

    def test_login_wrong_password(self, client):
        self._register(client)
        res = client.post(
            "/api/auth/login",
            json={"username": "logintest", "password": "wrongpass"},
        )
        assert res.status_code == 401

    def test_login_nonexistent_user(self, client):
        res = client.post(
            "/api/auth/login",
            json={"username": "nobody", "password": "pass123"},
        )
        assert res.status_code == 401

    def test_login_disabled_user(self, client, db_session):
        self._register(client)
        from app.models.user import User

        user = db_session.query(User).filter(User.username == "logintest").first()
        user.is_active = False
        db_session.commit()
        res = client.post(
            "/api/auth/login",
            json={"username": "logintest", "password": "pass123"},
        )
        assert res.status_code == 403
