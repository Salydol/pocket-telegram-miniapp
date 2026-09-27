import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings

if settings.database_url.startswith("sqlite"):
    path = settings.database_url.split("///", 1)[-1]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_session():
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    from . import models  # noqa: F401  регистрирует модели

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
