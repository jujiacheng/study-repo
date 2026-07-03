"""
test_app.py — FastAPI 测试示例
=============================

学习要点:
- TestClient:基于 requests 的同步测试客户端,最简单直接
- httpx.AsyncClient:异步测试客户端,适合测 async 路由 / 并发场景
- 测试受保护端点:先调 /token 拿 token,再带 Bearer 头访问
- 测异常路径:401、422 等错误用例也要覆盖,不只测 happy path

运行方式:
    cd fastapi/07_testing
    uv run pytest -v

注意:pyproject.toml 里配了 asyncio_mode = "auto",
所以 async def 测试函数不需要加 @pytest.mark.asyncio 标记,会被自动收集。
"""

from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app import app


# ---------------------------------------------------------------------------
# 1. 用 TestClient 做同步测试(最常用)
# ---------------------------------------------------------------------------
# TestClient 会把对 FastAPI 的调用「在进程内」转发,不发真实网络包,
# 所以测试很快、很干净,不需要起服务器。
client = TestClient(app)


def test_root():
    """最简单的 happy path 测试:GET / 返回 200 和预期 JSON。"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "hello"}


def test_public():
    response = client.get("/public")
    assert response.status_code == 200
    assert response.json()["visibility"] == "public"


def test_protected_without_token_returns_401():
    """没带 token 访问受保护端点,应该返回 401。"""
    response = client.get("/me")
    assert response.status_code == 401


def test_protected_with_valid_token():
    """完整流程:登录拿 token -> 带 token 访问 /me -> 返回 200。"""
    # 1. 登录拿 token(用 OAuth2 标准的表单格式)
    login_resp = client.post(
        "/token",
        data={"username": "alice", "password": "secret123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    # 2. 带 Bearer token 访问受保护端点
    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"username": "alice"}


def test_login_with_wrong_password_returns_401():
    """错误路径:密码错应该 401,不能放行。"""
    response = client.post(
        "/token",
        data={"username": "alice", "password": "wrong"},
    )
    assert response.status_code == 401


def test_invalid_token_returns_401():
    """错误路径:乱编的 token 也应该 401。"""
    response = client.get("/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# 2. 用 httpx.AsyncClient 做异步测试
# ---------------------------------------------------------------------------
# 异步测试适合:需要并发调多个请求、或者要复用 async 生态的依赖。
# 用 ASGITransport 把 httpx 直接接到 FastAPI 的 ASGI app 上,不走真实网络。

async def test_async_root():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "hello"}


async def test_async_protected_flow():
    """异步版本的完整鉴权流程测试。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 登录
        login = await ac.post(
            "/token",
            data={"username": "alice", "password": "secret123"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]

        # 访问受保护端点
        me = await ac.get(
            "/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me.status_code == 200
        assert me.json() == {"username": "alice"}
