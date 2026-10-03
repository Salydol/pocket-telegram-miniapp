import asyncio
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .models import DEFAULT_CATEGORIES, Category, Expense, User

# Будит цикл напоминаний, когда у задач меняется время: в остальное время он спит
# до ближайшего напоминания и не трогает БД (бесплатный Neon засыпает без запросов).
reminders_event = asyncio.Event()


def reminders_changed() -> None:
    reminders_event.set()


def as_utc(dt: datetime | None) -> datetime | None:
    """SQLite теряет tzinfo — всё храним в UTC и возвращаем aware-datetime."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def to_db(dt: datetime | None) -> datetime | None:
    """Приводит к aware-UTC перед записью/сравнением в БД (SQLite сохранит wall-time UTC)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def user_zone(user: User) -> ZoneInfo:
    try:
        return ZoneInfo(user.tz)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo(settings.default_tz)


async def ensure_user(
    session: AsyncSession,
    user_id: int,
    first_name: str = "",
    username: str | None = None,
    tz: str | None = None,
) -> User:
    user = await session.get(User, user_id)
    changed = False
    if user is None:
        user = User(id=user_id, first_name=first_name, username=username, tz=settings.default_tz)
        session.add(user)
        await session.flush()  # сначала users: категории ссылаются на него внешним ключом
        for name, emoji, color in DEFAULT_CATEGORIES:
            session.add(Category(user_id=user_id, name=name, emoji=emoji, color=color))
        changed = True
    if tz and tz != user.tz:
        try:
            ZoneInfo(tz)
            user.tz = tz
            changed = True
        except (ZoneInfoNotFoundError, ValueError):
            pass
    if first_name and first_name != user.first_name:
        user.first_name = first_name
        changed = True
    if changed:
        await session.commit()
    return user


async def user_categories(session: AsyncSession, user_id: int) -> list[Category]:
    res = await session.execute(
        select(Category)
        .where(Category.user_id == user_id, Category.archived.is_(False))
        .order_by(Category.id)
    )
    return list(res.scalars())


async def add_expense(
    session: AsyncSession,
    user_id: int,
    amount: float,
    category_id: int | None,
    note: str = "",
    spent_at: datetime | None = None,
) -> Expense:
    exp = Expense(
        user_id=user_id,
        amount=amount,
        category_id=category_id,
        note=note,
        spent_at=to_db(spent_at or datetime.now(timezone.utc)),
    )
    session.add(exp)
    await session.commit()
    await session.refresh(exp, ["category"])
    return exp
