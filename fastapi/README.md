# FastAPI 学习模块

用 FastAPI 学习现代 Python Web API 开发,从基础路由到鉴权、测试,共 7 个主题。

## 学习路径

| 目录 | 主题 | 学习要点 |
|------|------|----------|
| `01_basics/` | 基础路由 | `FastAPI()` 实例、路径参数、查询参数、`response_model`、`HTTPException` |
| `02_request_body/` | 请求体校验 | Pydantic v2 `BaseModel`、嵌套模型、`Field` 校验、响应模型裁剪 |
| `03_dependency_injection/` | 依赖注入 | `Depends`、`yield` 依赖(资源清理)、嵌套依赖、类依赖、`dependency_overrides` |
| `04_async/` | 异步处理 | `async def` 路由、`BackgroundTasks`、`asyncio.gather` 并发 vs 串行 |
| `05_database/` | 数据库集成 | SQLAlchemy 2.x async + aiosqlite,完整 CRUD |
| `06_auth/` | 鉴权 | OAuth2 Password Flow + JWT,受保护路由 |
| `07_testing/` | 测试 | pytest + `TestClient` + `httpx.AsyncClient` |
| `utils/` | 工具函数 | (预留) |

## 准备(用 uv 管理依赖)

本模块是一个独立的 uv 项目(根 `pyproject.toml` 在 `fastapi/` 下)。先[安装 uv](https://docs.astral.sh/uv/getting-started/installation/),然后在 `fastapi/` 目录里同步依赖:

```bash
cd fastapi
uv sync
```

`uv sync` 会自动:
- 创建 `.venv/` 虚拟环境
- 按 `pyproject.toml` 安装所有依赖
- 生成 / 更新 `uv.lock` 锁文件

之后所有命令(`uvicorn`、`pytest`)都要在 `.venv` 里跑,最简单的方式是用 `uv run` 前缀,它会自动用项目的虚拟环境:

```bash
uv run uvicorn main:app --reload   # 跑示例
uv run pytest -v                    # 跑测试
```

## 运行某个示例

每个示例目录都是**自包含**的,从该目录内启动(不要从仓库根目录启动,因为数字前缀目录名不能作为 Python 包导入):

```bash
cd fastapi/01_basics
uv run uvicorn main:app --reload
```

然后浏览器访问:

- http://localhost:8000/ — API 根路径
- http://localhost:8000/docs — Swagger UI(交互式文档,可直接试接口)
- http://localhost:8000/redoc — ReDoc 文档

## 运行测试

```bash
cd fastapi/07_testing
uv run pytest -v
```

## 关于目录命名

目录用 `01_basics` 这种数字前缀是为了和 `algorithms/` 模块风格一致、方便排序。但 Python 标识符不能以数字开头,所以这些目录**不能被当作包导入**(例如 `import fastapi.01_basics` 是非法的)。每个示例因此设计成自包含 —— 从该目录内 `uvicorn main:app` 启动,模块名就是 `main`,不涉及跨目录导入。
