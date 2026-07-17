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

    # 2. Verify JWT
    payload=verify_supabase_jwt(token)
    user_id=payload.get("sub")
    
    if not user_id:
        raise InvalidTokenError("No user ID found")
    

    # 3. Find Profile in DB
    result =await db.execute(select(Profile).where(Profile.id==user_id))
    profile=result.scalar_one_or_none()
    
    if not profile:
        raise ForbiddenError("Profile not found")
    # 4. Return Profile
    return profile
    
    
    