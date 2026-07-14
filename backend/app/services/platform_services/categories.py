from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.resource_categories import ResourceCategoryRepository


class CategoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = ResourceCategoryRepository(session)

    async def seed_defaults(self) -> int:
        return await self.repository.seed_defaults()

    async def list_tree_rows(self) -> list[dict]:
        categories = await self.repository.list(limit=500)
        by_id = {category.id: category for category in categories}
        rows = []
        for category in sorted(categories, key=lambda item: (item.parent_id or "", item.sort_order)):
            rows.append(
                {
                    "id": category.id,
                    "code": category.code,
                    "name": category.name,
                    "parent_id": category.parent_id,
                    "parent_code": by_id[category.parent_id].code if category.parent_id else None,
                    "sort_order": category.sort_order,
                    "is_active": category.is_active,
                }
            )
        return rows
