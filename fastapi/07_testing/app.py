"""
app.py — 被测的 FastAPI 应用
============================

这是 07_testing 目录里「被测」的小应用,包含一个公开端点和一个受保护端点。
test_app.py 会用 TestClient 和 httpx.AsyncClient 两种方式测它。

设计成自包含(不依赖 06_auth),方便单独跑 pytest。
"""

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm


app = FastAPI(title="07_testing 被测应用", version="0.1.0")


# ---------------------------------------------------------------------------
# 极简的内存「用户库」+ token 签发
# ---------------------------------------------------------------------------
# 这里只是为了 demo,认证逻辑极简化(不做密码哈希、不做 JWT)。
# 真实项目里的认证见 06_auth。
_USERS = {"alice": "secret123"}
_TOKENS = {"alice": "alice-token"}  # 用户名 -> token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """从 token 反查用户名。token 不对就 401。"""
    for username, t in _TOKENS.items():
        if t == token:
            return username
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid token",
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.post("/token")
async def login(form: OAuth2PasswordRequestForm = Depends()):
    """登录拿 token。用 alice / secret123。"""
    if _USERS.get(form.username) != form.password:
        raise HTTPException(status_code=401, detail="bad credentials")
    return {"access_token": _TOKENS[form.username], "token_type": "bearer"}


# ---------------------------------------------------------------------------
# 被测的业务端点
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    return {"message": "hello"}


@app.get("/public")
async def public():
    return {"visibility": "public"}


@app.get("/me")
async def me(current_user: str = Depends(get_current_user)):
    """受保护端点:需要带 Bearer token 才能访问。"""
    return {"username": current_user}
