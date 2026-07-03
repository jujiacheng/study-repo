"""
main.py — FastAPI 路由 + 数据库集成
==================================

学习要点:
- 用 lifespan 在应用启动 / 退出时做初始化(建表、关引擎)
- 用 Depends(get_db) 把 session 注入路由
- SQLAlchemy 2.x async 的 select / insert / update / delete 语法
- 用 response_model 控制出参,内部用 ORM 对象,返回时自动转成 Pydantic

运行方式:
    cd fastapi/05_database
    uvicorn main:app --reload
访问 http://localhost:8000/docs 试 CRUD。
"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database import engine, get_db, init_db
from models import Item
from schemas import ItemCreate, ItemOut, ItemRead


# ---------------------------------------------------------------------------
# lifespan:应用启动 / 退出时的钩子
# ---------------------------------------------------------------------------
# 旧版 FastAPI 用 @app.on_event("startup"),新版推荐用 lifespan。
# lifespan 是一个 async context manager:yield 之前是启动逻辑,yield 之后是退出逻辑。
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时建表(生产用 Alembic,这里 demo 用 create_all)。
    await init_db()
    yield
    # 退出时关掉引擎,释放连接池。
    await engine.dispose()


app = FastAPI(title="05_database 示例", version="0.1.0", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
@app.post("/items/", response_model=ItemOut, status_code=201)
async def create_item(payload: ItemCreate, db: AsyncSession = Depends(get_db)):
    # 先构造 ORM 对象,加到 session,commit,refresh 拿到数据库生成的 id 和 created_at。
    item = Item(name=payload.name, price=payload.price)
    db.add(item)
    try:
        await db.commit()
    except IntegrityError:
        # name 有 unique 约束,重名会触发 IntegrityError。
        await db.rollback()
        raise HTTPException(status_code=409, detail="item name already exists")
    # refresh 让数据库回填的 id / created_at 同步到 Python 对象。
    await db.refresh(item)
    # 返回 ORM 对象,response_model=ItemOut 会用 ItemOut.model_validate 转换
    # (依赖 schemas.py 里配置的 from_attributes=True)。
    return item


# ---------------------------------------------------------------------------
# Read all
# ---------------------------------------------------------------------------
@app.get("/items/", response_model=list[ItemRead])
async def list_items(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db)):
    # select(Item) 构造一条 SELECT 语句;.offset/.limit 做分页。
    result = await db.execute(select(Item).offset(skip).limit(limit))
    # .scalars().all() 把行展开成 Item 对象列表。
    return result.scalars().all()


# ---------------------------------------------------------------------------
# Read one
# ---------------------------------------------------------------------------
@app.get("/items/{item_id}", response_model=ItemRead)
async def read_item(item_id: int, db: AsyncSession = Depends(get_db)):
    # select(Item).where(Item.id == item_id) 构造带条件的查询。
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    return item


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------
@app.put("/items/{item_id}", response_model=ItemOut)
async def update_item(
    item_id: int, payload: ItemCreate, db: AsyncSession = Depends(get_db)
):
    item = await db.scalar(select(Item).where(Item.id == item_id))
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    # 直接改 ORM 对象的字段,commit 后数据库会被 UPDATE。
    item.name = payload.name
    item.price = payload.price
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="item name already exists")
    await db.refresh(item)
    return item


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------
@app.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: int, db: AsyncSession = Depends(get_db)):
    item = await db.scalar(select(Item).where(Item.id == item_id))
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    await db.delete(item)
    await db.commit()
    # status_code=204 表示「成功但无响应体」,路由不 return 任何东西。


# ---------------------------------------------------------------------------
# 辅助:清空所有 item(方便测试)
# ---------------------------------------------------------------------------
@app.delete("/items/")
async def delete_all_items(db: AsyncSession = Depends(get_db)):
    # 用一条 DELETE 语句清空全表,生产里绝对不要这么做。
    result = await db.execute(delete(Item))
    await db.commit()
    return {"deleted": result.rowcount}
