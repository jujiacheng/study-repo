"""
main.py — OAuth2 Password Flow + JWT 受保护路由
==============================================

学习要点:
- /token 端点:接收用户名密码,验证通过后签发 JWT
- OAuth2PasswordRequestForm:FastAPI 提供的「标准 OAuth2 登录表单」格式
- 用 Depends(get_current_user) 给路由加鉴权
- /docs 里的「Authorize」按钮能直接登录试接口

运行方式:
    cd fastapi/06_auth
    uvicorn main:app --reload
然后访问 http://localhost:8000/docs,点 Authorize,用 alice / secret123 登录。
"""

from datetime import timedelta

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)


app = FastAPI(title="06_auth 示例", version="0.1.0")


# ---------------------------------------------------------------------------
# 假装的用户数据库
# ---------------------------------------------------------------------------
# 生产里用户数据存数据库,这里用 dict 演示。
# 注意:存的是密码哈希(hash_password 出来的),不是明文。
# 即使数据库泄露,攻击者也无法反推出明文密码(argon2 是单向的)。
_users = {
    "alice": {
        "username": "alice",
        "hashed_password": hash_password("secret123"),
        "disabled": False,
    },
    "bob": {
        "username": "bob",
        "hashed_password": hash_password("bobpass"),
        "disabled": True,
    },
}


def authenticate_user(username: str, password: str) -> dict | None:
    """验证用户名 + 密码,成功返回用户记录,失败返回 None。"""
    user = _users.get(username)
    if user is None:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


# ---------------------------------------------------------------------------
# /token:登录端点(标准 OAuth2 Password Flow)
# ---------------------------------------------------------------------------
# OAuth2PasswordRequestForm 是 FastAPI 提供的特殊表单,
# 它会从 application/x-www-form-urlencoded 请求体里取出 username / password 等字段。
# 这就是标准 OAuth2 登录的格式,不是 JSON。
@app.post("/token")
async def login(form: OAuth2PasswordRequestForm = Depends()):
    # 1. 验证用户
    user = authenticate_user(form.username, form.password)
    if user is None:
        # 用 401 + WWW-Authenticate 头是 OAuth2 规范要求。
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user["disabled"]:
        raise HTTPException(status_code=400, detail="user is disabled")

    # 2. 签发 JWT:把 username 放进 sub,设过期时间。
    access_token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    # 3. 返回标准 OAuth2 token 响应格式(access_token / token_type)。
    return {"access_token": access_token, "token_type": "bearer"}


# ---------------------------------------------------------------------------
# 受保护路由:用 Depends(get_current_user) 强制鉴权
# ---------------------------------------------------------------------------
@app.get("/users/me")
async def read_users_me(current_user: str = Depends(get_current_user)):
    # 没带 token 或 token 无效时,get_current_user 会抛 401,路由根本到不了这里。
    # 能到这里说明 token 已验证,current_user 是从 token payload 里解出的 username。
    return {"username": current_user}


@app.get("/me/items")
async def read_own_items(current_user: str = Depends(get_current_user)):
    # 任何需要「知道当前用户是谁」的路由,都加 Depends(get_current_user)。
    return {"username": current_user, "items": ["thing1", "thing2"]}


# ---------------------------------------------------------------------------
# 注册端点(演示注册时如何哈希密码存库)
# ---------------------------------------------------------------------------
@app.post("/register")
async def register(username: str, password: str):
    # 简化演示:实际项目里 username/password 应该用 Pydantic 模型校验长度 / 复杂度,
    # 而不是直接从查询字符串取。这里只是演示 hash_password 的用法。
    if username in _users:
        raise HTTPException(status_code=400, detail="username already taken")
    _users[username] = {
        "username": username,
        "hashed_password": hash_password(password),
        "disabled": False,
    }
    return {"username": username, "registered": True}
