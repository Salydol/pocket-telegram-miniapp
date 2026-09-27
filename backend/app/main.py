import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import router as api_router
from .config import settings
from .db import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("pocket")

REMINDER_INTERVAL = 20  # сек


async def reminder_loop(bot):
    from .bot import send_due_reminders

    while True:
        try:
            sent = await send_due_reminders(bot)
            if sent:
                log.info("sent %d reminders", sent)
        except Exception:
            log.exception("reminder loop error")
        await asyncio.sleep(REMINDER_INTERVAL)


async def tunnel_watch(bot) -> None:
    """cloudflared quick tunnel выдаёт случайный *.trycloudflare.com и меняет его при рестарте.
    Периодически спрашиваем /quicktunnel и, если адрес поменялся, обновляем кнопку меню бота."""
    import aiohttp

    from .bot import setup_bot_ui

    url = settings.tunnel_metrics_url.rstrip("/") + "/quicktunnel"
    async with aiohttp.ClientSession() as http:
        while True:
            try:
                async with http.get(url, timeout=aiohttp.ClientTimeout(total=3)) as r:
                    host = (await r.json(content_type=None)).get("hostname")
                if host and settings.webapp_url != f"https://{host}":
                    settings.webapp_url = f"https://{host}"
                    await setup_bot_ui(bot)
                    log.info("tunnel url: %s", settings.webapp_url)
            except Exception as e:
                log.debug("tunnel not ready: %s", e)
            await asyncio.sleep(5 if not settings.webapp_url else 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    tasks: list[asyncio.Task] = []
    bot = None
    if settings.run_bot and settings.bot_token:
        from .bot import build, setup_bot_ui

        bot, dp = build()
        try:
            await setup_bot_ui(bot)
        except Exception:
            log.exception("setup_bot_ui failed")
        await bot.delete_webhook(drop_pending_updates=False)
        tasks.append(asyncio.create_task(dp.start_polling(bot, handle_signals=False)))
        tasks.append(asyncio.create_task(reminder_loop(bot)))
        if settings.tunnel_metrics_url:
            tasks.append(asyncio.create_task(tunnel_watch(bot)))
        log.info("bot started (polling), webapp_url=%s", settings.webapp_url or "—")
    else:
        log.warning("bot disabled (no BOT_TOKEN or RUN_BOT=false) — API only")
    yield
    for t in tasks:
        t.cancel()
    for t in tasks:
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await t
    if bot:
        await bot.session.close()


app = FastAPI(title="Pocket", lifespan=lifespan)
app.include_router(api_router)


@app.get("/health")
async def health():
    return {"ok": True}


# Отдаём собранный React (frontend/dist) с того же домена — не нужен CORS
static = Path(settings.static_dir).resolve()
if static.is_dir():
    app.mount("/assets", StaticFiles(directory=static / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str):
        file = (static / path).resolve()
        if path and file.is_file() and static in file.parents:
            return FileResponse(file)
        return FileResponse(static / "index.html")
