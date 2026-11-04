"""应用入口模块测试"""

from unittest.mock import patch

from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import StaticPool


class TestHealthCheck:
    """健康检查接口测试"""

    def test_health_check(self, client):
        """测试健康检查返回正常"""
        res = client.get("/health")

        assert res.status_code == 200
        assert res.json() == {"status": "ok"}


class TestStartup:
    """启动事件测试：SQLite 建表、全新 MySQL 建表+stamp、已有库升级。"""

    def _prepare(self, monkeypatch):
        from app.core import database
        from app.core.config import settings

        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        monkeypatch.setattr(database, "engine", engine)
        monkeypatch.setattr(settings, "SEED_DEMO_DATA", False)
        return engine

    @patch("app.main.command")
    @patch("app.main.Config")
    def test_startup_sqlite_creates_tables(self, mock_config, mock_command, monkeypatch):
        from app.core.config import settings
        from app.main import startup

        engine = self._prepare(monkeypatch)
        monkeypatch.setattr(settings, "DATABASE_URL", "sqlite:///./test.db")

        startup()

        assert "users" in inspect(engine).get_table_names()
        mock_command.upgrade.assert_not_called()
        mock_command.stamp.assert_not_called()

    @patch("app.main.command")
    @patch("app.main.Config")
    def test_startup_fresh_mysql_creates_tables_and_stamps(
        self, mock_config, mock_command, monkeypatch
    ):
        from app.core.config import settings
        from app.main import startup

        engine = self._prepare(monkeypatch)
        monkeypatch.setattr(settings, "DATABASE_URL", "mysql+pymysql://user:pass@host/db")

        startup()

        assert "users" in inspect(engine).get_table_names()
        mock_command.stamp.assert_called_once()
        mock_command.upgrade.assert_not_called()

    @patch("app.main.command")
    @patch("app.main.Config")
    def test_startup_existing_mysql_upgrades(self, mock_config, mock_command, monkeypatch):
        from app.core.config import settings
        from app.core.database import Base
        from app.main import startup

        engine = self._prepare(monkeypatch)
        Base.metadata.create_all(engine)
        monkeypatch.setattr(settings, "DATABASE_URL", "mysql+pymysql://user:pass@host/db")

        startup()

        mock_command.upgrade.assert_called_once()
        mock_command.stamp.assert_not_called()
