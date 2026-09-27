"""Смоук-тест хендлеров бота: апдейты через Dispatcher, запросы к Telegram перехватываются."""
import asyncio
import os
from datetime import datetime

os.environ.setdefault("BOT_TOKEN", "123456:TEST")
os.environ.setdefault("RUN_BOT", "false")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./data/test.db")

from aiogram import Bot  # noqa: E402
from aiogram.client.session.base import BaseSession  # noqa: E402
from aiogram.methods import EditMessageText, SendMessage, TelegramMethod  # noqa: E402
from aiogram.types import Chat, Message, Update  # noqa: E402

from app import bot as botmod  # noqa: E402
from app.db import init_db  # noqa: E402

CHAT = Chat(id=77, type="private")


class FakeSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.calls: list[TelegramMethod] = []

    async def make_request(self, bot, method, timeout=None):
        self.calls.append(method)
        if isinstance(method, (SendMessage, EditMessageText)):
            return Message(message_id=len(self.calls), date=datetime.now(), chat=CHAT, text=method.text)
        return True

    async def close(self):
        pass

    async def stream_content(self, *a, **k):  # pragma: no cover
        yield b""


def upd(n: int, text: str) -> Update:
    return Update.model_validate(
        {
            "update_id": n,
            "message": {
                "message_id": n,
                "date": int(datetime.now().timestamp()),
                "chat": {"id": 77, "type": "private"},
                "from": {"id": 77, "is_bot": False, "first_name": "Ars"},
                "text": text,
                **({"entities": [{"type": "bot_command", "offset": 0, "length": len(text.split()[0])}]} if text.startswith("/") else {}),
            },
        }
    )


def cb(n: int, data: str) -> Update:
    return Update.model_validate(
        {
            "update_id": n,
            "callback_query": {
                "id": str(n),
                "from": {"id": 77, "is_bot": False, "first_name": "Ars"},
                "chat_instance": "x",
                "data": data,
                "message": {"message_id": 1, "date": 0, "chat": {"id": 77, "type": "private"}, "text": "💸 500 ₸"},
            },
        }
    )


def test_bot_flow():
    async def run():
        await init_db()
        session = FakeSession()
        bot = Bot("123456:TEST", session=session)
        _, dp = botmod.build()

        async def send(u):
            session.calls.clear()
            await dp.feed_update(bot, u)
            return [c for c in session.calls if isinstance(c, SendMessage)]

        out = await send(upd(1, "/start"))
        assert "Pocket" in out[0].text

        out = await send(upd(2, "такси 1.5к"))
        assert "1 500" in out[0].text and "Транспорт" in out[0].text
        undo_data = out[0].reply_markup.inline_keyboard[0][0].callback_data

        out = await send(upd(3, "/today"))
        assert "1 500" in out[0].text

        await send(cb(4, undo_data))
        assert any(isinstance(c, EditMessageText) for c in session.calls)
        out = await send(upd(5, "/today"))
        assert "трат нет" in out[0].text

        out = await send(upd(6, "/task Позвонить маме завтра 10:00"))
        assert "Позвонить маме" in out[0].text and "10:00" in out[0].text

        out = await send(upd(7, "/tasks"))
        assert "Позвонить маме" in out[0].text

        out = await send(upd(8, "привет"))
        assert "Не понял" in out[0].text

    asyncio.run(run())
