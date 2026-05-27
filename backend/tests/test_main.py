"""应用入口模块测试"""

from unittest.mock import patch

import pytest


class TestHealthCheck:
    """健康检查接口测试"""

    def test_health_check(self, client):
        """测试健康检查返回正常"""
        res = client.get("/health")

        assert res.status_code == 200
        assert res.json() == {"status": "ok"}


class TestStartup:
    """启动事件测试"""

    @patch("app.main.command")
    @patch("app.main.Config")
    def test_startup_runs_migration(self, mock_config, mock_command):
        """测试启动时执行数据库迁移"""
        from app.main import startup

        startup()

        mock_command.upgrade.assert_called_once()
