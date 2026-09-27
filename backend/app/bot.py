import logging
import re
from datetime import datetime, timedelta, timezone

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Message,
    WebAppInfo,
)
from sqlalchemy import delete, select

from .config import settings
from .db import SessionLocal
from .models import Expense, Task
from .parser import guess_category, parse_expense
from .services import add_expense, as_utc, ensure_user, to_db, user_categories, user_zone

log = logging.getLogger(__name__)
router = Router()


def fmt_money(v: float) -> str:
    s = f"{v:,.2f}".rstrip("0").rstrip(".").replace(",", " ")
    return f"{s} {settings.currency}"


def allowed(user_id: int) -> bool:
    return not settings.allowed_ids or user_id in settings.allowed_ids


def app_button(text: str = "📱 Открыть") -> InlineKeyboardMarkup | None:
    if not settings.webapp_url:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=text, web_app=WebAppInfo(url=settings.webapp_url))]]
    )


# ---------- команды ----------

@router.message(CommandStart())
async def start(msg: Message):
    if not allowed(msg.from_user.id):
        return await msg.answer("Это приватный бот 🙂")
    async with SessionLocal() as s:
        await ensure_user(s, msg.from_user.id, msg.from_user.first_name, msg.from_user.username)
    await msg.answer(
        "Привет! Я <b>Pocket</b> — траты и задачи в одном окне.\n\n"
        "💸 Просто напиши трату: <code>500 кофе</code>, <code>такси 1.5к</code>\n"
        "✅ Задача: <code>/task Купить молоко 18:30</code>\n"
        "📊 <code>/today</code>, <code>/week</code>, <code>/month</code> — сводка\n\n"
        "Графики, категории и напоминания — в приложении 👇",
        reply_markup=app_button(),
    )


async def summary(msg: Message, days: int | None, title: str):
    async with SessionLocal() as s:
        user = await ensure_user(s, msg.from_user.id, msg.from_user.first_name)
        tz = user_zone(user)
        now = datetime.now(tz)
        if days == 0:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif days == 7:
            start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        res = await s.execute(
            select(Expense).where(Expense.user_id == user.id, Expense.spent_at >= to_db(start))
        )
        items = list(res.scalars())
    if not items:
        return await msg.answer(f"{title}: трат нет 🎉", reply_markup=app_button("📊 Открыть графики"))
    total = sum(float(e.amount) for e in items)
    cats: dict[str, float] = {}
    for e in items:
        key = f"{e.category.emoji} {e.category.name}" if e.category else "❔ Без категории"
        cats[key] = cats.get(key, 0) + float(e.amount)
    lines = [f"<b>{title}: {fmt_money(total)}</b>", ""]
    for k, v in sorted(cats.items(), key=lambda x: -x[1]):
        lines.append(f"{k} — {fmt_money(v)} ({v / total:.0%})")
    await msg.answer("\n".join(lines), reply_markup=app_button("📊 Открыть графики"))


@router.message(Command("today"))
async def today(msg: Message):
    if allowed(msg.from_user.id):
        await summary(msg, 0, "Сегодня")


@router.message(Command("week"))
async def week(msg: Message):
    if allowed(msg.from_user.id):
        await summary(msg, 7, "Эта неделя")


@router.message(Command("month"))
async def month(msg: Message):
    if allowed(msg.from_user.id):
        await summary(msg, None, "Этот месяц")


TIME_RE = re.compile(r"\s+(?:(завтра)\s+)?(?:в\s+)?(\d{1,2})[:.](\d{2})\s*$", re.I)


@router.message(Command("task"))
async def add_task(msg: Message, command: CommandObject):
    if not allowed(msg.from_user.id):
        return
    text = (command.args or "").strip()
    if not text:
        return await msg.answer("Формат: <code>/task Купить молоко</code> или <code>/task Позвонить маме завтра 10:00</code>")
    async with SessionLocal() as s:
        user = await ensure_user(s, msg.from_user.id, msg.from_user.first_name)
        tz = user_zone(user)
        remind_at = None
        m = TIME_RE.search(" " + text)
        if m:
            now = datetime.now(tz)
            h, mi = int(m.group(2)), int(m.group(3))
            if h < 24 and mi < 60:
                remind_at = now.replace(hour=h, minute=mi, second=0, microsecond=0)
                if m.group(1):
                    remind_at += timedelta(days=1)
                elif remind_at <= now:
                    remind_at += timedelta(days=1)
                text = (" " + text)[: m.start()].strip()
        task = Task(user_id=user.id, title=text[:256], remind_at=to_db(remind_at))
        s.add(task)
        await s.commit()
    when = f"\n⏰ {remind_at:%d.%m %H:%M}" if remind_at else ""
    await msg.answer(f"✅ Задача добавлена: <b>{task.title}</b>{when}")


@router.message(Command("tasks"))
async def list_tasks(msg: Message):
    if not allowed(msg.from_user.id):
        return
    async with SessionLocal() as s:
        user = await ensure_user(s, msg.from_user.id, msg.from_user.first_name)
        tz = user_zone(user)
        res = await s.execute(
            select(Task).where(Task.user_id == user.id, Task.done.is_(False)).order_by(Task.remind_at, Task.id).limit(20)
        )
        tasks = list(res.scalars())
    if not tasks:
        return await msg.answer("Открытых задач нет 🙌", reply_markup=app_button())
    kb = []
    lines = ["<b>Задачи:</b>"]
    for t in tasks:
        when = f" — ⏰ {as_utc(t.remind_at).astimezone(tz):%d.%m %H:%M}" if t.remind_at else ""
        lines.append(f"• {t.title}{when}")
        kb.append([InlineKeyboardButton(text=f"✔ {t.title[:30]}", callback_data=f"done:{t.id}")])
    await msg.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


# ---------- быстрый ввод траты ----------

@router.message(F.text & ~F.text.startswith("/"))
async def quick_expense(msg: Message):
    if not allowed(msg.from_user.id):
        return
    parsed = parse_expense(msg.text)
    if not parsed:
        return await msg.answer(
            "Не понял 🤔 Напиши сумму и описание: <code>500 кофе</code>", reply_markup=app_button()
        )
    async with SessionLocal() as s:
        user = await ensure_user(s, msg.from_user.id, msg.from_user.first_name)
        cats = await user_categories(s, user.id)
        cat_id = guess_category(parsed.note, cats)
        exp = await add_expense(s, user.id, parsed.amount, cat_id, parsed.note)
        cat = exp.category
    label = f"{cat.emoji} {cat.name}" if cat else "❔"
    note = f" · {parsed.note}" if parsed.note else ""
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="↩️ Отменить", callback_data=f"undo:{exp.id}")]]
    )
    await msg.answer(f"💸 <b>{fmt_money(parsed.amount)}</b> — {label}{note}", reply_markup=kb)


# ---------- callbacks ----------

@router.callback_query(F.data.startswith("undo:"))
async def undo(cb: CallbackQuery):
    exp_id = int(cb.data.split(":")[1])
    async with SessionLocal() as s:
        res = await s.execute(delete(Expense).where(Expense.id == exp_id, Expense.user_id == cb.from_user.id))
        await s.commit()
    if res.rowcount:
        await cb.message.edit_text(f"<s>{cb.message.html_text}</s>\nОтменено")
    await cb.answer()


@router.callback_query(F.data.startswith("done:"))
async def done(cb: CallbackQuery):
    task_id = int(cb.data.split(":")[1])
    async with SessionLocal() as s:
        t = await s.get(Task, task_id)
        if t and t.user_id == cb.from_user.id:
            t.done = True
            await s.commit()
            await cb.answer("Готово ✅")
            if cb.message and "⏰" in (cb.message.text or ""):
                await cb.message.edit_text(f"✅ <s>{t.title}</s>")
            return
    await cb.answer("Не найдено")


@router.callback_query(F.data.startswith("snooze:"))
async def snooze(cb: CallbackQuery):
    _, task_id, minutes = cb.data.split(":")
    async with SessionLocal() as s:
        t = await s.get(Task, int(task_id))
        if not t or t.user_id != cb.from_user.id:
            return await cb.answer("Не найдено")
        t.remind_at = to_db(datetime.now(timezone.utc) + timedelta(minutes=int(minutes)))
        t.reminded = False
        await s.commit()
    label = f"{int(minutes) // 60} ч" if int(minutes) >= 60 else f"{minutes} мин"
    await cb.message.edit_text(f"⏰ {t.title}\n<i>Отложено на {label}</i>")
    await cb.answer()


# ---------- напоминания ----------

async def send_due_reminders(bot: Bot) -> int:
    now = datetime.now(timezone.utc)
    async with SessionLocal() as s:
        res = await s.execute(
            select(Task).where(
                Task.done.is_(False), Task.reminded.is_(False), Task.remind_at.is_not(None), Task.remind_at <= to_db(now)
            ).limit(50)
        )
        tasks = list(res.scalars())
        for t in tasks:
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ Готово", callback_data=f"done:{t.id}"),
                        InlineKeyboardButton(text="⏳ 15 мин", callback_data=f"snooze:{t.id}:15"),
                        InlineKeyboardButton(text="⏳ 1 ч", callback_data=f"snooze:{t.id}:60"),
                    ]
                ]
            )
            try:
                await bot.send_message(t.user_id, f"⏰ <b>Напоминание</b>\n{t.title}", reply_markup=kb)
            except Exception as e:  # пользователь заблокировал бота и т.п.
                log.warning("reminder %s failed: %s", t.id, e)
            t.reminded = True
        await s.commit()
    return len(tasks)


# ---------- сборка ----------

def build() -> tuple[Bot, Dispatcher]:
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    return bot, dp


async def setup_bot_ui(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Открыть приложение"),
            BotCommand(command="today", description="Траты за сегодня"),
            BotCommand(command="week", description="Траты за неделю"),
            BotCommand(command="month", description="Траты за месяц"),
            BotCommand(command="task", description="Добавить задачу"),
            BotCommand(command="tasks", description="Список задач"),
        ]
    )
    if settings.webapp_url:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="Pocket", web_app=WebAppInfo(url=settings.webapp_url))
        )
