"""
models.py — ORM 模型
====================

学习要点:
- DeclarativeBase 子类 + Mapped[...] / mapped_column(...) 声明表结构
- 主键、字符串长度、唯一约束
- __tablename__ 指定表名

注意:这是 SQLAlchemy 2.x 的「新风格」写法,和 1.x 的 Column(...) 不太一样。
"""

from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Item(Base):
    """商品表 ORM 模型。"""

    __tablename__ = "items"

    # mapped_column(primary_key=True) 声明主键。
    # Integer 类型会被 SQLAlchemy 自动推断(Mapped[int] -> Integer)。
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # String(50) 限制名字长度,nullable=False 表示非空。
    # 用 mapped_column(String(50), unique=True) 加唯一约束。
    name: Mapped[str] = mapped_column(String(50), unique=True)

    # Float 类型存价格;nullable=False 表示必填。
    price: Mapped[float] = mapped_column(nullable=False)

    # 用 server_default=func.now() 让数据库在 INSERT 时自动填当前时间。
    # 注意是 server_default(数据库层)而不是 default(Python 层)。
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
