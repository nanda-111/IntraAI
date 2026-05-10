"""
配置管理模块

使用 pydantic-settings 库统一管理 IntraAI 后端的所有配置项。

工作原理：
  - pydantic-settings 的 BaseSettings 类会自动从以下来源读取配置（按优先级排序）：
    1. 传入的关键字参数（构造时手动指定）
    2. 环境变量（操作系统级别的变量）
    3. .env 文件（项目根目录下的 dotenv 文件）
    4. 类属性的默认值
  - 每个字段都有类型标注（如 str、int），pydantic 会自动进行类型转换和校验
  - 如果某个配置项没有设置也没有默认值，启动时会抛出 ValidationError

使用方式：
  from app.core.config import settings
  print(settings.DATABASE_URL)  # 获取数据库连接字符串
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    IntraAI 后端的配置类。

    继承自 pydantic-settings 的 BaseSettings，能够自动从环境变量和 .env 文件中
    读取与字段名同名的配置值。如果环境变量中没有对应的值，则使用类中定义的默认值。
    """

    # ==================== MySQL 数据库配置 ====================
    # 这些配置项用于连接 MySQL 数据库，供 SQLAlchemy ORM 使用

    MYSQL_HOST: str = "localhost"      # MySQL 服务器地址，默认为本机（localhost）
    MYSQL_PORT: int = 3306             # MySQL 服务端口号，默认 3306
    MYSQL_USER: str = "root"           # 数据库用户名，默认 root
    MYSQL_PASSWORD: str = ""           # 数据库密码，默认为空（开发环境）
    MYSQL_DB: str = "intraai"          # 要连接的数据库名称

    # ==================== JWT 认证配置 ====================
    # JWT（JSON Web Token）用于用户身份认证，配合 python-jose 库使用

    SECRET_KEY: str = "dev-secret-key"  # JWT 签名密钥，生产环境必须更换为随机生成的强密钥
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 访问令牌有效期（分钟），1440 分钟 = 24 小时

    # ==================== OpenAI API 配置 ====================
    # 用于调用 OpenAI 的大语言模型 API（聊天、向量嵌入等）

    OPENAI_API_KEY: str = ""                          # OpenAI API 密钥，必须在 .env 中配置
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"  # API 基础地址，可替换为兼容的第三方服务
    OPENAI_MODEL: str = "gpt-4o-mini"                 # 默认使用的聊天模型
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"  # 默认使用的文本向量嵌入模型

    # ==================== 文件存储路径配置 ====================
    # 本地文件系统的存储目录

    UPLOAD_DIR: str = "./uploads"       # 用户上传文件的存储目录
    CHROMA_DIR: str = "./chroma_data"   # ChromaDB 向量数据库的数据持久化目录

    @property
    def DATABASE_URL(self) -> str:
        """
        拼接 MySQL 连接字符串，供 SQLAlchemy 使用。

        连接字符串格式：mysql+pymysql://用户名:密码@主机:端口/数据库名
        例如：mysql+pymysql://root:123456@localhost:3306/intraai

        使用 @property 装饰器，使其像属性一样访问（settings.DATABASE_URL），
        每次访问时动态拼接，确保使用最新的配置值。
        """
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
        )

    class Config:
        """
        pydantic-settings 的内部配置类。

        env_file 指定从哪个 .env 文件加载环境变量。
        pydantic-settings 会在项目运行时自动读取这个文件，
        将其中的 KEY=VALUE 映射到 Settings 类的对应字段上。
        """
        env_file = ".env"


# 创建全局单例实例
# 整个应用共享这一个 Settings 实例，避免重复创建和配置不一致的问题
# 其他模块通过以下方式使用：
#   from app.core.config import settings
#   db_url = settings.DATABASE_URL
settings = Settings()
