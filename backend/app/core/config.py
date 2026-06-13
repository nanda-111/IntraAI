"""应用配置，通过 pydantic-settings 从环境变量和 .env 文件自动读取。"""

import logging
import warnings

from pydantic import field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

_INSECURE_DEFAULTS = {"dev-secret-key", "dev-secret-key-please-change", ""}


class Settings(BaseSettings):
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DB: str = "intraai"

    SECRET_KEY: str = "dev-secret-key-please-change"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://token-plan-cn.xiaomimimo.com/v1"
    OPENAI_MODEL: str = "mimo-v2-pro"
    UPLOAD_DIR: str = "./uploads"
    CHROMA_DIR: str = "./chroma_data"

    @field_validator("SECRET_KEY")
    @classmethod
    def _check_secret_key(cls, v: str) -> str:
        if v in _INSECURE_DEFAULTS:
            warnings.warn(
                "SECRET_KEY 使用了不安全的默认值，请在 .env 或环境变量中设置随机密钥。",
                stacklevel=2,
            )
        return v

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
        )

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
