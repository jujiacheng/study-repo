"""
schemas.py — Pydantic 入参 / 出参模型
=====================================

学习要点:
- 入参模型(ItemCreate)和出参模型(ItemOut、ItemRead)分开
- 用 model_config 的 from_attributes=True 让 ORM 对象能直接转 Pydantic
- 字段约束复用(Field 的 gt、min_length 等)

这是「API 层」的模型,和 models.py 里的「ORM 层」模型是分离的:
- models.py 描述「数据库里的数据长什么样」
- schemas.py 描述「客户端能传什么、能看到什么」
分开的好处是:数据库改字段不一定影响 API,反之亦然。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ItemBase(BaseModel):
    """ItemCreate 和 ItemOut 的公共字段。"""

    name: str = Field(min_length=1, max_length=50)
    price: float = Field(gt=0)


class ItemCreate(ItemBase):
    """创建商品时的入参(客户端传)。"""

    pass


class ItemOut(ItemBase):
    """创建 / 更新后的出参(返回给客户端)。"""

    id: int
    created_at: datetime

    # from_attributes=True(老版本叫 from_orm=True)允许从 ORM 对象直接构造。
    # 用法:ItemOut.model_validate(orm_obj),不用手动转 dict 再构造。
    model_config = ConfigDict(from_attributes=True)


class ItemRead(ItemOut):
    """查询时的出参。这里和 ItemOut 一样,留作未来扩展(比如可以加 owner 字段)。"""

    pass
