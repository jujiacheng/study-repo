"""
database.py — 数据库引擎与 Session 工厂
======================================

学习要点:
- create_async_engine:创建异步引擎(基于 aiosqlite,真正异步)
- async_sessionmaker:创建异步 Session 工厂
- DeclarativeBase:所有 ORM 模型的基类
- 启动时建表 + 应用退出时清理(用 lifespan)

这个文件只放「基础设施」,不放任何业务逻辑。
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


# SQLite 文件会生成在运行目录下(demo.sqlite3)。
# check_same_thread=False 是 SQLite 在多线程/异步下必需的设置。
# echo=False 关掉 SQL 日志(调试时可以改成 True 看每条 SQL)。
DB_URL = "sqlite+aiosqlite:///./demo.sqlite3"

engine = create_async_engine(DB_URL, echo=False)

# async_sessionmaker 是个「Session 工厂」,每次调用它会创建一个新的 AsyncSession。
# expire_on_commit=False:commit 后对象不再过期(默认会过期,重新访问会触发查库,
# 在异步里容易踩坑,所以这里关掉)。
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。模型定义在 models.py。"""

    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """yield 依赖:每个请求拿一个 session,请求结束后自动关掉。"""
    async with AsyncSessionLocal() as session:
        # async with 退出时会自动 close session,不需要 finally 手动关。
        yield session


async def init_db() -> None:
    """启动时建表。生产里通常用 Alembic 管理迁移,这里为了演示直接 create_all。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
