import calendar
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import current_user
from .config import settings
from .db import get_session
from .models import Category, Expense, Task, User
from .schemas import (
    CategoryIn,
    CategoryOut,
    CategoryStat,
    DayStat,
    ExpenseIn,
    ExpenseOut,
    Me,
    Stats,
    TaskIn,
    TaskOut,
    TaskPatch,
)
from .services import add_expense, as_utc, to_db, user_categories, user_zone

router = APIRouter(prefix="/api")


# ---------- helpers ----------

def expense_out(e: Expense) -> ExpenseOut:
    return ExpenseOut(
        id=e.id,
        amount=float(e.amount),
        note=e.note,
        spent_at=as_utc(e.spent_at),
        category=CategoryOut.model_validate(e.category) if e.category else None,
    )


def task_out(t: Task) -> TaskOut:
    return TaskOut(
        id=t.id,
        title=t.title,
        remind_at=as_utc(t.remind_at),
        reminded=t.reminded,
        done=t.done,
        created_at=as_utc(t.created_at),
    )


def period_range(period: str, offset: int, today: date) -> tuple[date, date]:
    """Возвращает [start, end] включительно в локальных датах пользователя."""
    if period == "week":
        start = today - timedelta(days=today.weekday()) - timedelta(weeks=offset)
        return start, start + timedelta(days=6)
    # month
    y, m = today.year, today.month - offset
    while m <= 0:
        m += 12
        y -= 1
    last = calendar.monthrange(y, m)[1]
    return date(y, m, 1), date(y, m, last)


def local_bounds(start: date, end: date, tz) -> tuple[datetime, datetime]:
    lo = datetime.combine(start, time.min, tzinfo=tz).astimezone(timezone.utc)
    hi = datetime.combine(end + timedelta(days=1), time.min, tzinfo=tz).astimezone(timezone.utc)
    return lo, hi


async def own_or_404(session: AsyncSession, model, obj_id: int, user: User):
    obj = await session.get(model, obj_id)
    if obj is None or obj.user_id != user.id:
        raise HTTPException(404, "not found")
    return obj


# ---------- me ----------

@router.get("/me", response_model=Me)
async def me(user: User = Depends(current_user)):
    return Me(id=user.id, first_name=user.first_name, tz=user.tz, currency=settings.currency)


# ---------- categories ----------

@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    return await user_categories(session, user.id)


@router.post("/categories", response_model=CategoryOut, status_code=201)
async def create_category(
    body: CategoryIn, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    cat = Category(user_id=user.id, **body.model_dump())
    session.add(cat)
    await session.commit()
    return cat


@router.delete("/categories/{cat_id}", status_code=204)
async def archive_category(
    cat_id: int, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    cat = await own_or_404(session, Category, cat_id, user)
    cat.archived = True  # старые траты сохраняют категорию
    await session.commit()


# ---------- expenses ----------

@router.get("/expenses", response_model=list[ExpenseOut])
async def list_expenses(
    period: Literal["week", "month"] = "month",
    offset: int = Query(0, ge=0, le=120),
    limit: int = Query(200, ge=1, le=1000),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    tz = user_zone(user)
    start, end = period_range(period, offset, datetime.now(tz).date())
    lo, hi = local_bounds(start, end, tz)
    res = await session.execute(
        select(Expense)
        .where(Expense.user_id == user.id, Expense.spent_at >= lo, Expense.spent_at < hi)
        .order_by(Expense.spent_at.desc(), Expense.id.desc())
        .limit(limit)
    )
    return [expense_out(e) for e in res.scalars()]


@router.post("/expenses", response_model=ExpenseOut, status_code=201)
async def create_expense(
    body: ExpenseIn, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    if body.category_id is not None:
        await own_or_404(session, Category, body.category_id, user)
    exp = await add_expense(session, user.id, body.amount, body.category_id, body.note, body.spent_at)
    return expense_out(exp)


@router.delete("/expenses/{exp_id}", status_code=204)
async def delete_expense(
    exp_id: int, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    await own_or_404(session, Expense, exp_id, user)
    await session.execute(delete(Expense).where(Expense.id == exp_id))
    await session.commit()


# ---------- stats ----------

@router.get("/stats", response_model=Stats)
async def stats(
    period: Literal["week", "month"] = "month",
    offset: int = Query(0, ge=0, le=120),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    tz = user_zone(user)
    today = datetime.now(tz).date()
    start, end = period_range(period, offset, today)
    lo, hi = local_bounds(start, end, tz)

    res = await session.execute(
        select(Expense).where(Expense.user_id == user.id, Expense.spent_at >= lo, Expense.spent_at < hi)
    )
    expenses = list(res.scalars())

    by_cat: dict[int | None, CategoryStat] = {}
    by_day: dict[date, float] = defaultdict(float)
    total = 0.0
    for e in expenses:
        amt = float(e.amount)
        total += amt
        by_day[as_utc(e.spent_at).astimezone(tz).date()] += amt
        key = e.category_id
        if key not in by_cat:
            c = e.category
            by_cat[key] = CategoryStat(
                id=key,
                name=c.name if c else "Без категории",
                emoji=c.emoji if c else "❔",
                color=c.color if c else "#8E8E93",
                total=0,
                count=0,
            )
        by_cat[key].total += amt
        by_cat[key].count += 1

    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]

    # прошлый период для сравнения
    p_start, p_end = period_range(period, offset + 1, today)
    p_lo, p_hi = local_bounds(p_start, p_end, tz)
    prev_total = await session.scalar(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.user_id == user.id, Expense.spent_at >= p_lo, Expense.spent_at < p_hi
        )
    )

    elapsed = (min(today, end) - start).days + 1 if offset == 0 else len(days)
    return Stats(
        period=period,
        start=start,
        end=end,
        total=round(total, 2),
        prev_total=float(prev_total or 0),
        avg_per_day=round(total / max(elapsed, 1), 2),
        by_category=sorted(by_cat.values(), key=lambda s: s.total, reverse=True),
        by_day=[DayStat(date=d, total=round(by_day.get(d, 0.0), 2)) for d in days],
    )


# ---------- tasks ----------

@router.get("/tasks", response_model=list[TaskOut])
async def list_tasks(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    res = await session.execute(
        select(Task)
        .where(Task.user_id == user.id)
        .order_by(Task.done, Task.remind_at.is_(None), Task.remind_at, Task.id.desc())
    )
    return [task_out(t) for t in res.scalars()]


@router.post("/tasks", response_model=TaskOut, status_code=201)
async def create_task(body: TaskIn, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    t = Task(user_id=user.id, title=body.title.strip(), remind_at=to_db(body.remind_at))
    session.add(t)
    await session.commit()
    return task_out(t)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: int, body: TaskPatch, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    t: Task = await own_or_404(session, Task, task_id, user)
    if body.title is not None:
        t.title = body.title.strip()
    if body.done is not None:
        t.done = body.done
    if body.clear_remind:
        t.remind_at, t.reminded = None, False
    elif body.remind_at is not None:
        t.remind_at, t.reminded = to_db(body.remind_at), False
    await session.commit()
    return task_out(t)


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: int, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    await own_or_404(session, Task, task_id, user)
    await session.execute(delete(Task).where(Task.id == task_id))
    await session.commit()
