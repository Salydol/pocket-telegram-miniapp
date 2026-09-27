"""Разбор быстрых сообщений вида «500 кофе», «такси 1.5к», «2 500 продукты»."""
import re
from dataclasses import dataclass

KEYWORDS: dict[str, list[str]] = {
    "Еда": ["кофе", "обед", "ужин", "завтрак", "кафе", "ресторан", "бургер", "пицц", "шаурм", "доставк", "еда", "перекус"],
    "Продукты": ["продукт", "магазин", "магнум", "small", "смолл", "супермаркет", "молоко", "хлеб", "овощ", "фрукт"],
    "Транспорт": ["такси", "яндекс", "автобус", "метро", "бензин", "заправк", "парковк", "проезд", "транспорт"],
    "Дом": ["коммунал", "аренд", "квартир", "интернет", "свет", "газ", "дом", "ремонт"],
    "Развлечения": ["кино", "игр", "бар", "клуб", "концерт", "развлеч", "боулинг", "steam"],
    "Одежда": ["одежд", "обув", "кроссов", "футбол", "куртк", "джинс"],
    "Здоровье": ["аптек", "лекарств", "врач", "стомат", "анализ", "здоров", "спорт", "зал"],
    "Подписки": ["подписк", "spotify", "netflix", "youtube", "icloud", "chatgpt", "claude", "яндекс плюс"],
    "Подарки": ["подар", "цвет", "букет"],
}

AMOUNT_RE = re.compile(r"(?<![\w.])(\d{1,3}(?:[  ]\d{3})+|\d+(?:[.,]\d+)?)\s*(к|k|тыс|т)?(?![\w])", re.I)


@dataclass
class ParsedExpense:
    amount: float
    note: str


def parse_expense(text: str) -> ParsedExpense | None:
    text = text.strip()
    if not text or text.startswith("/"):
        return None
    m = AMOUNT_RE.search(text)
    if not m:
        return None
    raw = m.group(1).replace(" ", "").replace(" ", "").replace(",", ".")
    try:
        amount = float(raw)
    except ValueError:
        return None
    if m.group(2):
        amount *= 1000
    if amount <= 0:
        return None
    note = (text[: m.start()] + " " + text[m.end():]).strip(" -—:,.")
    note = re.sub(r"\s+", " ", re.sub(r"(?i)(?<!\w)(тг|тенге|₸)(?!\w)", "", note)).strip()
    return ParsedExpense(amount=round(amount, 2), note=note[:256])


def guess_category(note: str, categories: list) -> int | None:
    """categories — объекты с .id и .name. Сначала точное совпадение с именем, потом ключевые слова."""
    low = note.lower()
    by_name = {c.name.lower(): c.id for c in categories}
    for name, cid in by_name.items():
        if name and name in low:
            return cid
    for cat_name, words in KEYWORDS.items():
        if any(w in low for w in words) and cat_name.lower() in by_name:
            return by_name[cat_name.lower()]
    return by_name.get("другое")
