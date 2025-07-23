import asyncio
from sqlalchemy import select
from app.database import async_session  # This is your session factory
from app.models.user import User
from app.core.config import settings
from app.utils.auth import get_password_hash

async def create_superuser():
    async with async_session() as session:  # ✅ Create a session from the factory
        # ✅ Correct way to query using SQLAlchemy ORM, not raw string
        result = await session.execute(
            select(User).where(User.email == settings.FIRST_SUPERUSER)
        )
        existing_user = result.scalars().first()
        if existing_user:
            print(f"Superuser {settings.FIRST_SUPERUSER} already exists.")
            return

        # ✅ Create the new superuser object
        superuser = User(
            email=settings.FIRST_SUPERUSER,
            hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
            is_active=True,
            is_verified=True,
            role="admin"
        )

        session.add(superuser)
        await session.commit()
        print(f"✅ Superuser {settings.FIRST_SUPERUSER} created successfully.")

if __name__ == "__main__":
    asyncio.run(create_superuser())
