"""
01_basics — FastAPI 基础路由
============================

学习要点:
- 创建 FastAPI 应用实例
- 用 @app.get / @app.post 注册路由
- 路径参数(/items/{item_id})与类型转换
- 查询参数(?skip=0&limit=10)与默认值、可选参数
- 用 response_model 控制响应结构(过滤掉不想暴露的字段)
- 用 HTTPException 主动抛错(自动变成标准 JSON 错误响应)

运行方式:
    cd fastapi/01_basics
    uvicorn main:app --reload
然后访问 http://localhost:8000/docs 看交互式文档。
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# 1. 创建应用实例
# ---------------------------------------------------------------------------
# FastAPI() 接收很多可选参数,这里只设置了 title/description,
# 这些信息会出现在自动生成的 /docs Swagger 文档里,方便团队协作。
app = FastAPI(
    title="01_basics 示例",
    description="学习 FastAPI 的基础路由、路径参数、查询参数。",
    version="0.1.0",
)


# ---------------------------------------------------------------------------
# 2. 一个最简单的路由:Hello World
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    # 路由函数可以是 async def 或普通 def,FastAPI 都能处理。
    # async def 适合内部有 IO(await)的场景;纯计算用普通 def 即可。
    return {"message": "Hello, FastAPI!"}


# ---------------------------------------------------------------------------
# 3. 路径参数
# ---------------------------------------------------------------------------
# 路径顺序很重要:更具体的路径要写在更通用的路径前面。
# /items/me 必须在 /items/{item_id} 之前注册,否则请求 /items/me 时会先命中
# {item_id} 路由,"me" 转 int 失败 → 422,read_current_user 永远不会被调用。
@app.get("/items/me")
async def read_current_user():
    return {"user": "current user"}


@app.get("/items/{item_id}")
async def read_item(item_id: int):
    # 加 int 类型注解后,FastAPI 会自动把路径里的字符串转成 int;
    # 转不过来就返回 422(Unprocessable Entity),无需手写校验。
    return {"item_id": item_id, "doubled": item_id * 2}


# ---------------------------------------------------------------------------
# 4. 查询参数
# ---------------------------------------------------------------------------
# 函数里不是路径变量的参数,都会被当作查询参数。
# skip: int = 0  —— 有默认值,客户端不传就用默认值。
# limit: int | None = None  —— 用 None 表示「可选」(不传时为 None)。
@app.get("/search")
async def search(skip: int = 0, limit: int | None = None):
    # 这里只是示意,返回一个模拟的分页结果。
    return {"skip": skip, "limit": limit, "results": []}


# 用 Query(...) 给查询参数加更精细的校验和文档。
# ge=0 表示 >= 0,le=100 表示 <= 100,description 会出现在 /docs 里。
@app.get("/search-validated")
async def search_validated(
    skip: int = Query(0, ge=0, description="跳过多少条记录"),
    limit: int = Query(10, ge=1, le=100, description="最多返回多少条"),
):
    return {"skip": skip, "limit": limit}


# ---------------------------------------------------------------------------
# 5. response_model:控制响应只暴露指定字段
# ---------------------------------------------------------------------------
# 定义一个内部数据模型(用 Pydantic),包含一个「敏感」字段。
class ItemDB(BaseModel):
    id: int
    name: str
    secret: str  # 假设这是不想返回给客户端的字段


# 内部用的「完整」对象(模拟从数据库取出来的)。
_internal_items = {
    1: ItemDB(id=1, name="苹果", secret="this-is-secret"),
    2: ItemDB(id=2, name="香蕉", secret="another-secret"),
}


# response_model=ItemPublic 让 FastAPI 自动把返回值按 ItemPublic 的字段裁剪,
# 即使函数返回的是包含 secret 的完整对象,响应里也不会泄露 secret。
# 这是一个很常见的「出参过滤」技巧,比手写 dict 转换更安全。
class ItemPublic(BaseModel):
    id: int
    name: str


@app.get("/items-public/{item_id}", response_model=ItemPublic)
async def read_item_public(item_id: int):
    item = _internal_items.get(item_id)
    if item is None:
        # HTTPException 会让 FastAPI 直接返回指定状态码的 JSON 错误,
        # 不用自己拼 Response,也不用 try/except 往外抛。
        raise HTTPException(status_code=404, detail="item not found")
    return item  # 返回完整对象,但 response_model 会裁掉 secret 字段
