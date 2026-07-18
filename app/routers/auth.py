from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.database import get_db
from app.dependencies import get_current_user
from app.models.profile import Profile
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    ProfileUpdateRequest,
    ResetPasswordRequest,
    SignupRequest,
    UserResponse,
)
from app.security import clear_auth_cookie, set_auth_cookie, set_csrf_cookie
from app.services import auth_service

router =APIRouter(prefix="/auth",tags=["auth"])


@router.post("/signup", response_model=UserResponse)
@limiter.limit("5/minute")
async def signup(
    request: Request, data: SignupRequest, response: Response, db: AsyncSession = Depends(get_db)
):
    profile = await auth_service.signup(db, data)
    token, _ = await auth_service.login(db, data.email, data.password)
    set_auth_cookie(response, token)
    set_csrf_cookie(response)
    return profile


@router.post("/login", response_model=UserResponse)
@limiter.limit("5/minute")
async def login(
    request: Request, data: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)
):
    token, profile = await auth_service.login(db, data.email, data.password)
    set_auth_cookie(response, token)
    set_csrf_cookie(response)
    return profile



@router.get("/me", response_model=UserResponse)
async def me(user: Profile = Depends(get_current_user)):
    return user


@router.post("/logout")
async def logout(response: Response):
    clear_auth_cookie(response)
    return {"success": True}

@router.put("/profile", response_model=UserResponse)
async def update_profile(
    data: ProfileUpdateRequest,
    user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await auth_service.update_profile(db, user, data)

@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(request: Request, data: ForgotPasswordRequest):
    await auth_service.forgot_password(data.email)
    # Always return success — don't reveal whether the email exists
    return {"message": "If that email is registered, a reset link has been sent."}


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(request: Request, data: ResetPasswordRequest):
    await auth_service.reset_password(data.access_token, data.new_password)
    return {"success": True}