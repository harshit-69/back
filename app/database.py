from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings
from typing import AsyncGenerator

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    future=True
)

async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that yields database sessions.
    Properly handles session cleanup.
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()  # Commit if no exceptions
        except Exception:
            await session.rollback()  # Rollback on errors
            raise