"""
auth.py — 鉴权工具:密码哈希 + JWT
==================================

学习要点:
- OAuth2PasswordBearer:声明「本项目的鉴权方式是 Bearer Token」
- pwdlib:用 argon2 哈希密码,不可逆,抗彩虹表(2025 起 FastAPI 官方推荐,
  取代已停止维护、且与 bcrypt 5.x 不兼容的 passlib)
- PyJWT:签发和验证 JWT(JSON Web Token)
- JWT 的 payload 结构(sub、exp 等标准「保留字段」)

安全提醒:
- SECRET_KEY 必须保密,生产里用环境变量或密钥管理服务,不要写死在代码里。
- 这里的 SECRET_KEY 只是 demo 用,不要拿去生产。
"""

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError, decode, encode
from pwdlib import PasswordHash


# ---------------------------------------------------------------------------
# 配置(生产里从环境变量 / 配置中心读取)
# ---------------------------------------------------------------------------
SECRET_KEY = "a-very-insecure-demo-key-replace-me-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


# ---------------------------------------------------------------------------
# 密码哈希:pwdlib + argon2
# ---------------------------------------------------------------------------
# PasswordHash.recommended() 会选当前推荐的算法(默认 argon2)。
# hash/verify 是对称的:hash 存库,verify 比对。
_password_hash = PasswordHash.recommended()


def hash_password(plain: str) -> str:
    """注册时用:把明文密码转成不可逆的哈希存库。"""
    return _password_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """登录时用:用明文和哈希比对,匹配返回 True。"""
    return _password_hash.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT 签发与解析
# ---------------------------------------------------------------------------
# 复用同一个 401 异常,避免每个错误点都手写一遍 headers。
_credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def create_access_token(
    data: dict, expires_delta: timedelta | None = None
) -> str:
    """签发一个 JWT。

    data 是要写进 token 的 payload(比如 {"sub": "alice"}),
    我们会再加一个 exp(过期时间),然后用 SECRET_KEY 签名。
    """
    to_encode = data.copy()
    # exp 是 JWT 的标准「保留字段」,表示「过期时间」,过期的 token 应该被拒绝。
    # 没传 expires_delta 时,用模块级常量 ACCESS_TOKEN_EXPIRE_MINUTES 兜底。
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str:
    """解析 JWT,返回 payload 里的 sub(用户名)。

    解析失败(签名错、过期、缺 sub 等)统一抛 401。
    """
    try:
        payload = decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            # 缺 sub 也算认证失败,直接抛 401,不再绕一层异常。
            raise _credentials_exception
        return username
    except InvalidTokenError as e:
        # 签名错 / 过期 / 格式错都会抛 InvalidTokenError 的子类。
        raise _credentials_exception from e


# ---------------------------------------------------------------------------
# OAuth2PasswordBearer:FastAPI 的鉴权声明
# ---------------------------------------------------------------------------
# tokenUrl 指向「获取 token 的端点」(这里是 /token),FastAPI 会用它生成 /docs 里的登录按钮。
# 把这个对象当依赖用,会自动从 Authorization: Bearer <token> 头里取出 token。
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """受保护路由用 Depends(get_current_user) 来强制鉴权。"""
    return decode_access_token(token)
