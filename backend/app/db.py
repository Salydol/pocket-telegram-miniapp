import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from .config import settings


def normalize_db_url(url: str) -> tuple[str, dict]:
    """Строку от Neon/Supabase (postgresql://...?sslmode=require) можно вставлять как есть:
    asyncpg не понимает sslmode/channel_binding, SSL передаём через connect_args."""
    if url.startswith(("postgres://", "postgresql://")):
        url = "postgresql+asyncpg://" + url.split("://", 1)[1]
    if not url.startswith("postgresql+asyncpg://"):
        return url, {}
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    sslmode = query.pop("sslmode", None)
    query.pop("channel_binding", None)
    connect_args = {"ssl": "require"} if sslmode and sslmode != "disable" else {}
    return urlunsplit(parts._replace(query=urlencode(query))), connect_args


db_url, connect_args = normalize_db_url(settings.database_url)

if db_url.startswith("sqlite"):
    path = db_url.split("///", 1)[-1]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    engine = create_async_engine(db_url, pool_pre_ping=True)

    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_fk(dbapi_conn, _):
        # SQLite по умолчанию не проверяет внешние ключи — включаем, чтобы вести себя как Postgres
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()
else:
    # Без пула: открытые простаивающие соединения не дают бесплатному Neon уснуть
    engine = create_async_engine(db_url, poolclass=NullPool, connect_args=connect_args)
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
