"""密码哈希（bcrypt）和 JWT 令牌（jose）工具模块。"""

from datetime import UTC, datetime, timedelta

import bcrypt
from jose import jwt

from app.core.config import settings

BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    """将明文密码转换为 bcrypt 哈希值。"""
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """验证明文密码是否与哈希值匹配。"""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict) -> str:
    """生成 JWT 访问令牌，有效期由 ACCESS_TOKEN_EXPIRE_MINUTES 控制。"""
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    """解码并验证 JWT 令牌，返回 payload。无效或过期时抛出 JWTError。"""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
