"""
安全工具模块

提供密码哈希/验证和 JWT 令牌的生成/解码功能。

核心原理说明：
================

【为什么不能存储明文密码】
  如果数据库中的密码以明文形式存储，一旦数据库泄露（如 SQL 注入、服务器入侵），
  攻击者可以直接获取所有用户的密码。更严重的是，很多用户会在多个网站使用相同的密码，
  所以一个站点的密码泄露可能导致用户在其他站点的账户也被入侵。
  因此，密码必须经过不可逆的哈希处理后才能存储。

【bcrypt 算法原理】
  bcrypt 是一种专门用于密码哈希的算法，具有以下特点：
  1. 单向哈希（One-way Hash）：bcrypt 通过多次迭代的 Blowfish 加密算法，
     将明文密码转换为固定长度的哈希字符串，这个过程是不可逆的。
     即使攻击者拿到哈希值，也无法还原出原始密码。
  2. 加盐（Salt）：在哈希之前，bcrypt 会自动生成一个随机的"盐值"（salt），
     并将其混入密码中。这意味着即使两个用户使用相同的密码，
     它们的哈希值也会不同（因为盐值不同），有效防止了彩虹表攻击。
  3. 可配置的工作因子（Cost Factor）：bcrypt 允许调整计算复杂度，
     随着硬件性能的提升，可以增加迭代次数来保持安全性。

  本模块直接使用 bcrypt 库进行密码哈希（而非 passlib），
  因为 passlib 与 bcrypt 5.x 存在兼容性问题，且 passlib 已停止维护。
  直接调用 bcrypt 库更加可靠，接口也更简洁。

【JWT（JSON Web Token）结构】
  JWT 是一种用于在网络应用间安全传递信息的令牌格式，由三部分组成：
  header.payload.signature
  - Header（头部）：描述令牌的类型（JWT）和签名算法（如 HS256），
    经过 Base64 编码后作为第一部分。
  - Payload（载荷）：包含实际的声明信息（Claims），
    如 "sub"（主题/用户名）、"exp"（过期时间）等。
    注意：Payload 只是 Base64 编码，并非加密，任何人都可以解码查看内容，
    所以绝不能在 Payload 中放入密码等敏感信息。
  - Signature（签名）：将 Header 和 Payload 用指定算法（如 HS256）
    配合密钥（SECRET_KEY）进行签名，用于验证令牌是否被篡改。
    只有持有密钥的服务端才能生成有效的签名。

【HS256 算法的作用】
  HS256（HMAC-SHA256）是一种对称签名算法：
  - 使用同一个 SECRET_KEY 进行签名和验签。
  - 签名过程：将 header + "." + payload 与 SECRET_KEY 一起进行 HMAC-SHA256 运算，
    得到签名值。
  - 验签过程：用同样的方式重新计算签名，与令牌中的签名对比，
    如果一致说明令牌未被篡改。
  - 由于是"对称"算法，签名和验签使用相同的密钥，因此 SECRET_KEY 必须严格保密。

【"sub" 字段的含义】
  "sub" 是 JWT 标准中 Registered Claim（注册声明）之一，全称 Subject（主题）。
  在 IntraAI 中，我们将用户名（username）作为 sub 的值，
  这样在解码 token 后，可以通过 payload["sub"] 获取当前登录的用户名。
"""

from datetime import UTC, datetime, timedelta

import bcrypt
from jose import jwt

from app.core.config import settings

# ==================== bcrypt 常量 ====================
# bcrypt 的 rounds（轮次）参数，控制哈希计算的复杂度。
# 2^12 = 4096 次迭代，这是目前业界推荐的默认值，
# 在安全性和性能之间取得平衡（更高的值更安全但更慢）。
BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    """
    将明文密码转换为 bcrypt 哈希值。

    用于用户注册时：
      1. 用户提交明文密码
      2. 调用此函数生成哈希值
      3. 将哈希值存入数据库（绝不存储明文）

    bcrypt 内部会自动生成随机盐值，混入密码后进行多轮迭代哈希。
    返回的哈希字符串中已经包含了算法标识、工作因子、盐值和哈希结果，
    例如：$2b$12$LJ3m4ys3BqG9Q8z5X2eKOeKq6v8JxZ1Y2W3X4V5B6N7M8A9S0D1G

    处理流程：
      1. bcrypt.gensalt() 生成随机盐值（包含算法版本和 cost 因子）
      2. bcrypt.hashpw() 将密码与盐值结合，进行指定轮次的哈希运算
      3. 返回的 bytes 需要解码为 UTF-8 字符串才能存入数据库

    Args:
        password: 用户输入的明文密码

    Returns:
        bcrypt 哈希后的字符串，可直接存入数据库
    """
    # 生成随机盐值（salt），其中包含了算法版本（2b）和 cost 因子（12）
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    # hashpw 要求密码为 bytes 类型，使用 UTF-8 编码
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    # 将 bytes 转为字符串，便于存入数据库的 VARCHAR 字段
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """
    验证明文密码是否与数据库中存储的哈希值匹配。

    用于用户登录时：
      1. 用户提交明文密码
      2. 从数据库取出该用户的密码哈希值
      3. 调用此函数验证两者是否匹配

    验证过程：
      bcrypt.checkpw() 会从 hashed 字符串中提取出盐值和 cost 因子，
      用同样的参数对 plain 进行哈希运算，然后比较结果是否一致。
      比较使用常量时间算法（constant-time comparison），
      防止通过测量响应时间来推断密码信息（时序攻击）。

    Args:
        plain: 用户输入的明文密码
        hashed: 数据库中存储的 bcrypt 哈希值

    Returns:
        True 表示密码正确，False 表示密码错误
    """
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict) -> str:
    """
    生成 JWT 访问令牌。

    调用方式示例：
      token = create_access_token({"sub": "zhangsan"})
      # 生成的 JWT 中 payload 为：{"sub": "zhangsan", "exp": 1700000000}

    处理流程：
      1. 复制传入的 data 字典，避免修改原始数据
      2. 计算过期时间 = 当前 UTC 时间 + ACCESS_TOKEN_EXPIRE_MINUTES 分钟
      3. 将过期时间（exp）添加到 payload 中
      4. 使用 jose.jwt.encode() 进行签名编码，生成 JWT 字符串

    关于 exp 声明：
      exp 是 JWT 标准中的 Registered Claim，表示令牌的过期时间（Unix 时间戳）。
      令牌过期后，客户端必须重新登录获取新令牌。
      有效期由配置项 ACCESS_TOKEN_EXPIRE_MINUTES 控制（默认 1440 分钟 = 24 小时）。

    Args:
        data: 要编码到 token 中的数据，通常为 {"sub": username}

    Returns:
        编码后的 JWT 字符串，格式为 "header.payload.signature"
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    """
    解码并验证 JWT 令牌，返回 payload 数据。

    调用方式示例：
      payload = decode_access_token(token)
      username = payload["sub"]  # 获取用户名

    处理流程：
      1. jose.jwt.decode() 会自动用 SECRET_KEY 验证签名
      2. 检查令牌是否过期（exp 字段）
      3. 验证通过后返回解码后的 payload 字典

    异常处理：
      - 如果令牌签名不匹配（被篡改），抛出 JWTError
      - 如果令牌已过期，抛出 ExpiredSignatureError（JWTError 的子类）
      - 调用方应捕获这些异常并返回 401 未授权响应

    Args:
        token: 客户端传来的 JWT 字符串

    Returns:
        解码后的 payload 字典，如 {"sub": "zhangsan", "exp": 1700000000}
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
