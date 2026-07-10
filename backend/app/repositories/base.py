# app/repositories/base.py

"""
Generic Base Repository for SQLAlchemy 2.0 Async ORM.
"""

from typing import Any, Generic, Optional, Type, TypeVar, Union
from sqlalchemy import select, exists, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Base repository class providing generic CRUD and utility operations.
    """

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, id: Any) -> Optional[ModelType]:
        return await self.session.get(self.model, id)

    async def require(self, id: Any) -> ModelType:
        """Retrieve an entity or raise a ValueError if not found."""
        obj = await self.get_by_id(id)
        if not obj:
            raise ValueError(f"{self.model.__name__} with id {id} not found.")
        return obj

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[ModelType]:
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def first(self, **filter_by: Any) -> Optional[ModelType]:
        stmt = select(self.model).filter_by(**filter_by).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by(self, **filter_by: Any) -> list[ModelType]:
        stmt = select(self.model).filter_by(**filter_by)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, obj_in: Union[dict[str, Any], Any]) -> ModelType:
        if hasattr(obj_in, "model_dump"):
            data = obj_in.model_dump()
        else:
            data = obj_in

        db_obj = self.model(**data)
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def update(
        self, db_obj: ModelType, obj_in: Union[dict[str, Any], Any]
    ) -> ModelType:
        if hasattr(obj_in, "model_dump"):
            update_data = obj_in.model_dump(exclude_unset=True)
        else:
            update_data = obj_in

        for key, value in update_data.items():
            setattr(db_obj, key, value)

        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def delete(self, entity: ModelType) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def count(self, **filter_by: Any) -> int:
        stmt = select(func.count()).select_from(self.model).filter_by(**filter_by)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def exists(self, **filter_by: Any) -> bool:
        if not filter_by:
            raise ValueError("exists() requires at least one filter criterion.")
        stmt = select(
            exists().where(*[getattr(self.model, k) == v for k, v in filter_by.items()])
        )
        result = await self.session.execute(stmt)
        return result.scalar() or False
