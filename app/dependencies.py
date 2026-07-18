from typing import Annotated
from uuid import UUID

from fastapi import Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError,InvalidTokenError
from app.database import get_db
from app.models.profile import Profile
from app.security import AUTH_COOKIE_NAME,verify_supabase_jwt



async def get_current_user(request:Request,db:AsyncSession=Depends(get_db)  )->Profile:
    """
    1. Get Token from Cookie
    2. Verify JWT
    3. Find Profile in DB
    4. Return Profile
    """
    # 1. Get Token from Cookie
    token = request.cookies.get(AUTH_COOKIE_NAME)

    if not token:
        raise InvalidTokenError("No token found")

    # 2. Verify JWT via Supabase API
    import asyncio
    from app.services.auth_service import _supabase
    try:
        res = await asyncio.to_thread(_supabase.auth.get_user, token)
        user_id = res.user.id
    except Exception as exc:
        raise InvalidTokenError("Invalid token") from exc
    
    if not user_id:
        raise InvalidTokenError("No user ID found")
    

    # 3. Find Profile in DB
    result =await db.execute(select(Profile).where(Profile.id==user_id))
    profile=result.scalar_one_or_none()
    
    if not profile:
        raise ForbiddenError("Profile not found")
    # 4. Return Profile
    return profile
    

async def get_current_user_optional (
    request:Request,
    db:AsyncSession=Depends(get_db)
) ->Profile | None:
    try:
        return await get_current_user(request,db)
    except (InvalidTokenError,ForbiddenError):
        return None


async def get_current_admin(user:Profile=Depends(get_current_user))->Profile:
    if user.role not in ["admin","super_admin"]:
        raise ForbiddenError("Admin only")
    return user

async def get_current_super_admin(user:Profile=Depends(get_current_user))->Profile:
    if user.role != "super_admin":
        raise ForbiddenError("Super Admin only")
    return user


class Pagination:
    def __init__ (
        self,
        page: Annotated[int,Query(ge=1)]=1,
        page_size:Annotated[int,Query(ge=1,le=100)]=20,    
    ):

        self.page=page
        self.page_size=page_size
        self.offset=(page-1)*page_size
        
        
    
   
    
    
    