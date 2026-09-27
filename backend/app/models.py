from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Telegram user id
    first_name: Mapped[str] = mapped_column(String(128), default="")
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tz: Mapped[str] = mapped_column(String(64), default="Asia/Almaty")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    emoji: Mapped[str] = mapped_column(String(16), default="💸")
    color: Mapped[str] = mapped_column(String(16), default="#8E8E93")
    archived: Mapped[bool] = mapped_column(Boolean, default=False)


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    amount: Mapped[float] = mapped_column(Numeric(14, 2))
    note: Mapped[str] = mapped_column(String(256), default="")
    spent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    category: Mapped[Category | None] = relationship(lazy="joined")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(256))
    remind_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    reminded: Mapped[bool] = mapped_column(Boolean, default=False)
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


DEFAULT_CATEGORIES = [
    ("Еда", "🍔", "#FF9500"),
    ("Продукты", "🛒", "#34C759"),
    ("Транспорт", "🚕", "#007AFF"),
    ("Дом", "🏠", "#AF52DE"),
    ("Развлечения", "🎮", "#FF2D55"),
    ("Одежда", "👕", "#5AC8FA"),
    ("Здоровье", "💊", "#FF3B30"),
    ("Подписки", "📱", "#5856D6"),
    ("Подарки", "🎁", "#FFCC00"),
    ("Другое", "💸", "#8E8E93"),
]
