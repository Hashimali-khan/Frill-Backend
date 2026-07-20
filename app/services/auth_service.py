from httpcore import TrioBackend
from pydantic_core.core_schema import tuple_positional_schema
import email
from sqlalchemy.engine import create
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import Client, create_client

from app.config import settings
from app.core.exceptions import ConflictError, InvalidTokenError, ValidationAppError
from app.models.profile import Profile
from app.schemas.auth import ProfileUpdateRequest, SignupRequest

_supabase: Client =create_client(settings.supabase_url,settings.supabase_service_role_key)

async def signup(db:AsyncSession, data:SignupRequest)->Profile:
    existing = await db.execute(select(Profile).where(Profile.email == data.email))
    if existing.scalar_one_or_none():
        raise ConflictError("Email already registered")
    
    auth_response = _supabase.auth.admin.create_user({
        "email":data.email,
        "password": data.password,
        "email_confirm": True,
    })

    user_id= auth_response.user.id

    import uuid
    profile= Profile(
        id=uuid.UUID(user_id), email=data.email, first_name=data.first_name,
        last_name=data.last_name, phone=data.phone, role="customer",
    )

    db.add(profile)
    try:
        await db.commit()
    except Exception:
        # Two systems, one logical transaction: if the local insert fails,
        # don't leave an orphaned Supabase Auth user behind.
        _supabase.auth.admin.delete_user(user_id)
        raise
    await db.refresh(profile)
    return profile


async def login(db: AsyncSession, email:str, password:str)-> tuple[str,Profile]:
    try:
        auth_response= _supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
    except Exception as exc:
        raise InvalidTokenError("Invalid email or password") from exc
    
    token = auth_response.session.access_token
    result = await db.execute(select(Profile).where(Profile.email == email))
    profile = result.scalar_one_or_none()
    if not profile:
        raise InvalidTokenError("Account exists in auth but has no profile")
    return token, profile


async def update_profile(db:AsyncSession, profile: Profile, data: ProfileUpdateRequest)-> Profile:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    await db.commit()
    await db.refresh(profile)
    return profile


async def forgot_password(email: str) -> None:
    """Triggers Supabase's built-in password reset email."""
    try:
        _supabase.auth.reset_password_email(email)
    except Exception:
        # Don't reveal whether the email exists — always return success
        pass


async def reset_password(access_token: str, new_password: str) -> None:
    """Uses the Supabase admin API to update the user's password."""
    try:
        # Verify the token to get the user ID
        from app.security import verify_supabase_jwt
        payload = verify_supabase_jwt(access_token)
        user_id = payload.get("sub")
        if not user_id:
            raise InvalidTokenError("Invalid reset token")
        _supabase.auth.admin.update_user_by_id(user_id, {"password": new_password})
    except InvalidTokenError:
        raise
    except Exception as exc:
        raise ValidationAppError("Password reset failed") from exc