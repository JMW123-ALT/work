from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.resource import ResourceCategory
from app.repositories.base import BaseRepository
from app.services.resource_library.taxonomy import ResourceCategoryService


class ResourceCategoryRepository(BaseRepository[ResourceCategory]):
    model = ResourceCategory

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_code(self, code: str) -> ResourceCategory | None:
        result = await self.session.execute(
            select(ResourceCategory).where(ResourceCategory.code == code)
        )
        return result.scalar_one_or_none()

    async def list_children(self, parent_id: str | None) -> list[ResourceCategory]:
        result = await self.session.execute(
            select(ResourceCategory)
            .where(ResourceCategory.parent_id == parent_id)
            .order_by(ResourceCategory.sort_order, ResourceCategory.code)
        )
        return list(result.scalars().all())

    async def seed_defaults(self) -> int:
        rows = ResourceCategoryService().flatten()
        created = 0
        by_code: dict[str, ResourceCategory] = {}
        for row in rows:
            existing = await self.get_by_code(row["code"])
            if existing:
                by_code[row["code"]] = existing
                continue
            parent = by_code.get(row["parent_code"] or "")
            category = ResourceCategory(
                parent_id=parent.id if parent else None,
                code=row["code"],
                name=row["name"],
                sort_order=row["sort_order"],
                is_active=row["is_active"],
            )
            self.session.add(category)
            await self.session.flush()
            by_code[row["code"]] = category
            created += 1
        return created
