"""数据库模块测试"""

from unittest.mock import MagicMock, patch

from app.core.database import get_db


class TestGetDb:
    """get_db 生成器函数测试"""

    @patch("app.core.database.SessionLocal")
    def test_get_db_yields_session(self, mock_session_local):
        """测试 get_db 返回数据库会话"""
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session

        gen = get_db()
        db = next(gen)

        assert db is mock_session
        mock_session_local.assert_called_once()

    @patch("app.core.database.SessionLocal")
    def test_get_db_closes_session_on_normal_exit(self, mock_session_local):
        """测试正常退出时关闭会话"""
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session

        gen = get_db()
        next(gen)
        try:
            gen.send(None)
        except StopIteration:
            pass

        mock_session.close.assert_called_once()

    @patch("app.core.database.SessionLocal")
    def test_get_db_closes_session_on_exception(self, mock_session_local):
        """测试异常时也会关闭会话"""
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session

        gen = get_db()
        next(gen)
        try:
            gen.throw(RuntimeError, "测试异常")
        except RuntimeError:
            pass

        mock_session.close.assert_called_once()
