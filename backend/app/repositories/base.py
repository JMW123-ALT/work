from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, id_: str) -> ModelT | None:
        return await self.session.get(self.model, id_)

    async def list(self, limit: int = 100, offset: int = 0) -> list[ModelT]:
        result = await self.session.execute(
            select(self.model).offset(offset).limit(min(limit, 500))
        )
        return list(result.scalars().all())

    async def add(self, item: ModelT) -> ModelT:
        self.session.add(item)
        await self.session.flush()
        return item
