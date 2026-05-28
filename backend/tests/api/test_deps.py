"""依赖注入模块测试"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from jose import JWTError

from app.api.deps import get_current_user


class TestGetCurrentUser:
    """get_current_user 函数测试"""

    def test_get_current_user_no_sub_in_token(self):
        """测试 token 中没有 sub 字段"""
        mock_db = MagicMock()

        with patch("app.api.deps.decode_access_token", return_value={}):
            with pytest.raises(HTTPException) as exc_info:
                get_current_user("fake_token", mock_db)

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "无效的令牌"

    def test_get_current_user_invalid_token(self):
        """测试无效 token"""
        mock_db = MagicMock()

        with patch("app.api.deps.decode_access_token", side_effect=JWTError("invalid")):
            with pytest.raises(HTTPException) as exc_info:
                get_current_user("invalid_token", mock_db)

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "无效的令牌"

    def test_get_current_user_user_not_found(self):
        """测试用户不存在"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch("app.api.deps.decode_access_token", return_value={"sub": "nonexistent"}):
            with pytest.raises(HTTPException) as exc_info:
                get_current_user("fake_token", mock_db)

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "用户不存在或已禁用"

    def test_get_current_user_inactive_user(self):
        """测试用户已被禁用"""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.is_active = False
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        with patch("app.api.deps.decode_access_token", return_value={"sub": "testuser"}):
            with pytest.raises(HTTPException) as exc_info:
                get_current_user("fake_token", mock_db)

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "用户不存在或已禁用"
