"""
03_dependency_injection — 依赖注入
==================================

学习要点:
- Depends():把公共逻辑(查参数、获取用户、取 db 连接)抽成可复用的「依赖」
- yield 依赖:用 yield 而不是 return,可以做「请求后的清理」(关连接、回滚事务)
- 嵌套依赖:依赖本身也可以有自己的依赖
- 类作为依赖:用类做依赖时,FastAPI 会调用 __init__ 解析查询参数
- dependency_overrides:在测试里把真依赖替换成 mock,不用改业务代码

运行方式:
    cd fastapi/03_dependency_injection
    uvicorn main:app --reload
"""

from fastapi import Depends, FastAPI, Header, HTTPException


app = FastAPI(title="03_dependency_injection 示例", version="0.1.0")


# ---------------------------------------------------------------------------
# 1. 最简单的依赖:函数依赖
# ---------------------------------------------------------------------------
# 依赖就是一个普通函数,FastAPI 会像解析路由参数一样解析它的参数(从 query/path 取)。
# 路由函数用 Depends(common_parameters) 声明「我需要这个依赖的结果」,
# FastAPI 会在调用路由前先调用依赖,把返回值传给路由。
def common_parameters(q: str | None = None, page: int = 1):
    # 把多个路由都需要的「分页 + 关键词」逻辑抽出来复用。
    return {"q": q, "page": page}


@app.get("/search/")
async def search(commons: dict = Depends(common_parameters)):
    # 这里 commons 就是上面函数返回的 dict。
    return commons


@app.get("/list/")
async def list_items(commons: dict = Depends(common_parameters)):
    # 同一个依赖可以在多个路由里复用,DRY。
    return {"message": "list", **commons}


# ---------------------------------------------------------------------------
# 2. yield 依赖:做请求后的清理(类似上下文管理器)
# ---------------------------------------------------------------------------
# 用 yield 而不是 return:yield 之前的代码在请求前执行,yield 出来的值传给路由,
# yield 之后的代码在路由返回后执行(无论成功还是异常都会执行,用于清理)。
# 这对数据库连接、文件句柄等需要「用完关掉」的资源非常合适。
def get_db():
    print("  [get_db] 打开连接")
    db = {"connection": "open"}  # 这里假装是一个数据库连接
    try:
        yield db  # 把 db 交给路由使用
    finally:
        # 无论路由成功返回还是抛异常,这里都会执行,确保资源被释放。
        print("  [get_db] 关闭连接")


@app.get("/items-db/")
async def read_items_db(db: dict = Depends(get_db)):
    # 拿到的 db 就是上面 yield 出来的那个 dict。
    return {"db_state": db["connection"], "items": []}


# ---------------------------------------------------------------------------
# 3. 嵌套依赖:依赖里再依赖
# ---------------------------------------------------------------------------
# 依赖函数自己也可以声明依赖,形成依赖链。
# 例如:从 Authorization header 解析出 token,再用 token 查用户。
def extract_token(authorization: str = Header(...)):
    # 用 Header(...) 声明从请求头取;参数名 authorization 会被 FastAPI
    # 自动映射到大小写不敏感的 Authorization 头(连字符 / 下划线自动转换)。
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="invalid token format")
    return authorization[len("Bearer ") :]


def get_current_user(token: str = Depends(extract_token)):
    # 这个依赖自己依赖了 extract_token,FastAPI 会自动解析整条链。
    # 实际项目里这里会去解码 JWT、查数据库,这里用一个假的映射演示。
    users = {"abc123": "alice", "def456": "bob"}
    user = users.get(token)
    if user is None:
        raise HTTPException(status_code=401, detail="user not found")
    return user


@app.get("/me/")
async def me(user: str = Depends(get_current_user)):
    # 路由只需要声明「我要 current_user」,不用关心 token 是怎么来的。
    # 这就是依赖注入的核心价值:把横切关注点(鉴权)从业务路由里剥离出去。
    return {"user": user}


# ---------------------------------------------------------------------------
# 4. 类作为依赖
# ---------------------------------------------------------------------------
# 类作为依赖时,FastAPI 会调用它的 __init__,并把 __init__ 的参数当作
# 查询参数 / 路径参数 / 请求体来解析(和路由函数的规则一样)。
class Pagination:
    def __init__(self, page: int = 1, size: int = 10):
        # 校验逻辑放在 __init__ 里,依赖被复用时校验也跟着复用。
        if page < 1:
            raise HTTPException(status_code=400, detail="page must >= 1")
        if size < 1 or size > 100:
            raise HTTPException(status_code=400, detail="size must be 1-100")
        self.page = page
        self.size = size

    def offset(self) -> int:
        return (self.page - 1) * self.size


@app.get("/paged/")
async def paged(p: Pagination = Depends()):
    # Depends() 不传参数时,FastAPI 会自动用类型注解 Pagination 来构造。
    # 这样写更简洁,IDE 也能补全。
    return {"page": p.page, "size": p.size, "offset": p.offset()}


# ---------------------------------------------------------------------------
# 5. dependency_overrides:测试时替换依赖
# ---------------------------------------------------------------------------
# app.dependency_overrides 是一个 dict,key 是原依赖函数,value 是替换函数。
# 测试时把「真的会连数据库 / 调外部服务」的依赖替换成 mock,业务代码一行都不用改。
# 这里只是演示如何注册,真正的测试用法见 07_testing。
def get_settings():
    return {"env": "prod"}


@app.get("/env/")
async def env(settings: dict = Depends(get_settings)):
    return settings


# dependency_overrides 通常只在测试代码里用(见 07_testing),这里注释掉作示例:
# app.dependency_overrides[get_settings] = lambda: {"env": "test_override"}
