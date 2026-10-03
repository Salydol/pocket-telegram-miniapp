"""Проверка подписи Telegram WebApp initData.

https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .db import get_session
from .models import User
from .services import ensure_user

MAX_AGE_SECONDS = 7 * 24 * 3600


def validate_init_data(init_data: str, bot_token: str, max_age: int = MAX_AGE_SECONDS) -> dict:
    pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise ValueError("no hash")
    # signature (Ed25519 для сторонних сервисов) в HMAC участвует наравне с остальными полями

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calc_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calc_hash, received_hash):
        raise ValueError("bad hash")

    auth_date = int(pairs.get("auth_date", "0"))
    if max_age and time.time() - auth_date > max_age:
        raise ValueError("expired")

    return json.loads(pairs["user"])


async def current_user(
    authorization: str | None = Header(default=None),
    x_timezone: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> User:
    tg_user: dict | None = None

    if authorization and authorization.startswith("tma "):
        try:
            tg_user = validate_init_data(authorization[4:], settings.bot_token)
        except (ValueError, KeyError) as e:
            raise HTTPException(401, f"invalid initData: {e}")
    elif settings.dev_user_id:
        tg_user = {"id": settings.dev_user_id, "first_name": "Dev"}
    else:
        raise HTTPException(401, "open the app from Telegram")

    if settings.allowed_ids and tg_user["id"] not in settings.allowed_ids:
        raise HTTPException(403, "access denied")

    return await ensure_user(
        session,
        tg_user["id"],
        first_name=tg_user.get("first_name", ""),
        username=tg_user.get("username"),
        tz=x_timezone,
    )
