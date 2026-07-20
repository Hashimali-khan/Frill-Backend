from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.profile import Profile
from app.schemas.design import DesignCreate, DesignOut, PaginatedDesigns
from app.services import design_service

router = APIRouter(prefix="/api/designs", tags=["designs"])


@router.post("", response_model=DesignOut)
async def save_design(
    data: DesignCreate, db: AsyncSession = Depends(get_db),
    user: Profile = Depends(get_current_user),
):
    return await design_service.create_design(db, user, data)


@router.get("", response_model=PaginatedDesigns)
async def list_designs(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db), user: Profile = Depends(get_current_user),
):
    items, total = await design_service.get_designs(db, user, page, page_size)
    return PaginatedDesigns(
        items=[DesignOut.model_validate(d) for d in items], total=total, page=page, page_size=page_size,
    )


@router.delete("/{design_id}")
async def delete_design(
    design_id: UUID, db: AsyncSession = Depends(get_db),
    user: Profile = Depends(get_current_user),
):
    await design_service.delete_design(db, user, design_id)
    return {"success": True}

from app.dependencies import get_current_admin
from app.schemas.design import DesignStatusUpdate

@router.patch("/{design_id}/status", response_model=DesignOut, dependencies=[Depends(get_current_admin)])
async def update_design_status(
    design_id: UUID, data: DesignStatusUpdate, db: AsyncSession = Depends(get_db)
):
    return await design_service.update_status(db, design_id, data.status)