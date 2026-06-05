"""应用配置，通过 pydantic-settings 从环境变量和 .env 文件自动读取。"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DB: str = "intraai"

    SECRET_KEY: str = "dev-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://token-plan-cn.xiaomimimo.com/v1"
    OPENAI_MODEL: str = "mimo-v2-pro"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    UPLOAD_DIR: str = "./uploads"
    CHROMA_DIR: str = "./chroma_data"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
        )

    class Config:
        env_file = ".env"


settings = Settings()
