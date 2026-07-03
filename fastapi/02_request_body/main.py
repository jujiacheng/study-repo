"""
02_request_body — 请求体与 Pydantic 校验
=========================================

学习要点:
- 用 Pydantic v2 BaseModel 声明请求体结构
- 字段类型校验(嵌套模型、list、可选字段)
- Field(...) 加更细的约束(min_length、ge、gt、正则等)
- 用 response_model 裁剪响应(exclude_unset 等高级用法)
- example / json_schema_extra 在文档里给出示例

运行方式:
    cd fastapi/02_request_body
    uvicorn main:app --reload
访问 http://localhost:8000/docs 可以直接试 POST 接口。
"""

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, EmailStr, Field


app = FastAPI(title="02_request_body 示例", version="0.1.0")


# ---------------------------------------------------------------------------
# 1. 最简单的请求体模型
# ---------------------------------------------------------------------------
# Pydantic v2 里,继承 BaseModel 就行。
# 类型注解就是校验规则:int 就是 int,str 就是 str,错了自动 422。
class ItemCreate(BaseModel):
    name: str
    price: float
    # 用 Field(...) 给字段加额外约束。
    # ... 表示「必填」(没有默认值);也可以给默认值,如 Field(0, ge=0)。
    # gt=0 表示价格必须 > 0;description 会出现在 /docs。
    tags: list[str] = Field(default_factory=list, description="商品标签列表")


# 路径函数的参数,如果类型是 BaseModel,FastAPI 会把它当作「请求体」;
# 而路径参数(像 item_id)和查询参数则分别由路径和查询字符串解析。
@app.post("/items/", response_model=ItemCreate)
async def create_item(item: ItemCreate):
    # 这里直接把入参原样返回,实际项目里会写库 / 调下游。
    return item


# ---------------------------------------------------------------------------
# 2. 嵌套模型:模型里套模型
# ---------------------------------------------------------------------------
class Address(BaseModel):
    city: str = Field(min_length=1, description="城市名")
    # pattern 用正则约束格式,这里限制邮编是 6 位数字。
    zip_code: str = Field(pattern=r"^\d{6}$", description="6 位邮编")


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    # EmailStr 会校验是否是合法邮箱格式(需要 pydantic[email])。
    email: EmailStr
    # 嵌套:UserCreate 里包含一个 Address 类型的字段。
    # 客户端传的 JSON 里 address 必须符合 Address 的结构,否则 422。
    address: Address
    # str | None = None 表示「可选,不传时为 None」(Python 3.10+ 语法)。
    # 注意:「不传」和「显式传 null」在这种写法下结果都是 None。
    nickname: str | None = None


@app.post("/users/", response_model=UserCreate)
async def create_user(user: UserCreate):
    return user


# ---------------------------------------------------------------------------
# 3. 响应模型裁剪:出参与入参分离
# ---------------------------------------------------------------------------
# 实际项目里,入参模型和出参模型通常不一样:出参可能多 id、多 created_at,
# 也可能少一些敏感字段。这里演示「出参模型」。
class ItemOut(BaseModel):
    id: int
    name: str
    price: float
    tags: list[str] = Field(default_factory=list)


# 假装的数据库:用一个递增计数器模拟分配 id。
_next_id = 1


@app.post("/items/out", response_model=ItemOut)
async def create_item_with_id(item: ItemCreate):
    global _next_id
    # 入参模型 ItemCreate 没有 id 字段,出参模型 ItemOut 有。
    # 这里手动构造出参对象;response_model 会再做一次校验+裁剪。
    out = ItemOut(id=_next_id, **item.model_dump())
    _next_id += 1
    return out


# ---------------------------------------------------------------------------
# 4. 高级:response_model_exclude_unset
# ---------------------------------------------------------------------------
# 客户端「没传」的字段 vs「显式传了默认值」的字段,默认情况下响应里都会带上。
# 加 response_model_exclude_unset=True 后,客户端没传的字段不会出现在响应里。
# 这对「部分更新」场景很有用 —— 客户端只改了哪些字段,就只返回哪些字段。
class ItemPatch(BaseModel):
    name: str | None = None
    price: float | None = None


@app.patch("/items/{item_id}", response_model=ItemPatch, response_model_exclude_unset=True)
async def patch_item(item_id: int, patch: ItemPatch):
    # 这里只是把客户端传的字段原样回显,演示 exclude_unset 的效果。
    # 试一下:PATCH /items/1 {"price": 9.9}
    #   -> 响应只有 {"price": 9.9},不会带 "name": null
    return patch


# ---------------------------------------------------------------------------
# 5. 给文档加示例:json_schema_extra
# ---------------------------------------------------------------------------
# 在 /docs 里,每个接口都会显示一个 Request body 示例。
# 用 model_config 的 json_schema_extra 可以自定义这个示例,方便前端联调。
# 注意:v2 推荐用 ConfigDict(...) 而不是裸 dict,有类型检查与补全。
class ProductCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "无线鼠标",
                    "price": 99.0,
                    "tags": ["数码", "外设"],
                }
            ]
        }
    )

    name: str = Field(min_length=1)
    price: float = Field(gt=0)
    tags: list[str] = Field(default_factory=list)


@app.post("/products/", response_model=ProductCreate)
async def create_product(product: ProductCreate):
    return product
