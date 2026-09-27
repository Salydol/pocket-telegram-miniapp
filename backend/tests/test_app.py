import asyncio
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

os.environ["BOT_TOKEN"] = "123456:TEST"
os.environ["RUN_BOT"] = "false"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./data/test.db"
os.environ["STATIC_DIR"] = "/nonexistent"
if os.path.exists("data/test.db"):
    os.remove("data/test.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.auth import validate_init_data  # noqa: E402
from app.main import app  # noqa: E402
from app.parser import parse_expense  # noqa: E402


def make_init_data(user_id: int, token: str = "123456:TEST", auth_date: int | None = None) -> str:
    fields = {
        "auth_date": str(auth_date or int(time.time())),
        "query_id": "AAH",
        "user": json.dumps({"id": user_id, "first_name": f"U{user_id}"}, separators=(",", ":")),
    }
    dcs = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, dcs.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


def hdr(uid: int):
    return {"Authorization": f"tma {make_init_data(uid)}", "X-Timezone": "Asia/Almaty"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_init_data_validation():
    assert validate_init_data(make_init_data(1), "123456:TEST")["id"] == 1
    with pytest.raises(ValueError):
        validate_init_data(make_init_data(1, token="999:OTHER"), "123456:TEST")
    with pytest.raises(ValueError):
        validate_init_data(make_init_data(1, auth_date=1), "123456:TEST")


def test_auth_required(client):
    assert client.get("/api/me").status_code == 401
    bad = {"Authorization": "tma " + make_init_data(1, token="1:x")}
    assert client.get("/api/me", headers=bad).status_code == 401


def test_expenses_flow_and_isolation(client):
    me = client.get("/api/me", headers=hdr(10)).json()
    assert me["tz"] == "Asia/Almaty"
    cats = client.get("/api/categories", headers=hdr(10)).json()
    assert len(cats) == 10
    food = next(c for c in cats if c["name"] == "Еда")

    r = client.post("/api/expenses", headers=hdr(10), json={"amount": 1500, "category_id": food["id"], "note": "обед"})
    assert r.status_code == 201, r.text
    client.post("/api/expenses", headers=hdr(10), json={"amount": 500.5, "category_id": cats[2]["id"]})

    st = client.get("/api/stats?period=week", headers=hdr(10)).json()
    assert st["total"] == 2000.5
    assert st["by_category"][0]["name"] == "Еда"
    assert len(st["by_day"]) == 7
    assert client.get("/api/stats?period=month", headers=hdr(10)).json()["total"] == 2000.5

    # другой пользователь не видит и не может удалить
    assert client.get("/api/expenses", headers=hdr(20)).json() == []
    exp_id = r.json()["id"]
    assert client.delete(f"/api/expenses/{exp_id}", headers=hdr(20)).status_code == 404
    # и не может использовать чужую категорию
    assert client.post("/api/expenses", headers=hdr(20), json={"amount": 1, "category_id": food["id"]}).status_code == 404

    assert client.delete(f"/api/expenses/{exp_id}", headers=hdr(10)).status_code == 204
    assert len(client.get("/api/expenses", headers=hdr(10)).json()) == 1


def test_categories_crud(client):
    r = client.post("/api/categories", headers=hdr(10), json={"name": "Кот", "emoji": "🐈", "color": "#123456"})
    assert r.status_code == 201
    cid = r.json()["id"]
    assert client.delete(f"/api/categories/{cid}", headers=hdr(10)).status_code == 204
    assert all(c["id"] != cid for c in client.get("/api/categories", headers=hdr(10)).json())


def test_tasks_and_reminders(client):
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    t1 = client.post("/api/tasks", headers=hdr(10), json={"title": "Купить молоко", "remind_at": past}).json()
    client.post("/api/tasks", headers=hdr(10), json={"title": "Позже", "remind_at": future})
    client.post("/api/tasks", headers=hdr(10), json={"title": "Без времени"})
    tasks = client.get("/api/tasks", headers=hdr(10)).json()
    assert [t["title"] for t in tasks] == ["Купить молоко", "Позже", "Без времени"]

    from app.bot import send_due_reminders

    sent = []

    class FakeBot:
        async def send_message(self, chat_id, text, **kw):
            sent.append((chat_id, text))

    n = asyncio.run(send_due_reminders(FakeBot()))
    assert n == 1 and sent[0][0] == 10 and "Купить молоко" in sent[0][1]
    assert asyncio.run(send_due_reminders(FakeBot())) == 0  # второй раз не шлём

    r = client.patch(f"/api/tasks/{t1['id']}", headers=hdr(10), json={"done": True})
    assert r.json()["done"] is True
    assert client.get("/api/tasks", headers=hdr(10)).json()[-1]["title"] == "Купить молоко"


@pytest.mark.parametrize(
    "text,amount,note",
    [
        ("500 кофе", 500, "кофе"),
        ("такси 1.5к", 1500, "такси"),
        ("2 500 продукты", 2500, "продукты"),
        ("обед 3200 тг", 3200, "обед"),
        ("1200,50", 1200.5, ""),
    ],
)
def test_parser(text, amount, note):
    p = parse_expense(text)
    assert p and p.amount == amount and p.note == note


def test_parser_rejects():
    assert parse_expense("привет") is None
    assert parse_expense("/start") is None
