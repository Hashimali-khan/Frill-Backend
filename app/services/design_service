from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.design import SavedDesign
from app.models.profile import Profile
from app.schemas.design import DesignCreate


async def create_design(db: AsyncSession, user: Profile, data: DesignCreate) -> SavedDesign:
    design = SavedDesign(
        user_id=user.id, name=data.name, design_json=data.design_json,
        product_id=UUID(data.product_id), color_id=data.color_id,
        view_id=data.view_id, mockup_url=data.mockup_url,
    )
    db.add(design)
    await db.commit()
    await db.refresh(design)
    return design


async def get_designs(
    db: AsyncSession, user: Profile, page: int, page_size: int
) -> tuple[list[SavedDesign], int]:
    query = select(SavedDesign)
    count_query = select(func.count(SavedDesign.id))

    # Admin sees all designs; regular user sees only their own
    if user.role not in ("admin", "super_admin"):
        query = query.where(SavedDesign.user_id == user.id)
        count_query = count_query.where(SavedDesign.user_id == user.id)

    total = (await db.execute(count_query)).scalar_one()
    query = query.order_by(SavedDesign.created_at.desc()).limit(page_size).offset((page - 1) * page_size)
    items = (await db.execute(query)).scalars().all()
    return list(items), total


async def delete_design(db: AsyncSession, user: Profile, design_id: UUID) -> None:
    design = await db.get(SavedDesign, design_id)
    if not design:
        raise NotFoundError("Design not found")
    if user.role not in ("admin", "super_admin") and design.user_id != user.id:
        raise ForbiddenError("You can only delete your own designs")
    await db.delete(design)
    await db.commit()