import os
import asyncio

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.profile import Profile
from app.schemas.auth import SignupRequest
from app.services.auth_service import signup


async def main():
    admin_password = os.environ.get("ADMIN_PASSWORD", "ChangeMeNow123!")
    async with AsyncSessionLocal() as db:
        await signup(db, SignupRequest(
            first_name="Hashim Ali", last_name="Khan", email="admin@frill.pk",
            phone="03001234567", password=admin_password,
        ))
        result = await db.execute(select(Profile).where(Profile.email == "admin@frill.pk"))
        profile = result.scalar_one()
        # FIX: per Q3 answer — first admin is super_admin who can manage other admins
        profile.role = "super_admin"
        await db.commit()
        print("Super admin created:", profile.email, "— change that password immediately.")


if __name__ == "__main__":
    asyncio.run(main())