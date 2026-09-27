from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class Me(BaseModel):
    id: int
    first_name: str
    tz: str
    currency: str


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    emoji: str = Field(default="💸", max_length=16)
    color: str = Field(default="#8E8E93", pattern=r"^#[0-9A-Fa-f]{6}$")


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    emoji: str
    color: str


class ExpenseIn(BaseModel):
    amount: float = Field(gt=0, lt=1e12)
    category_id: int | None = None
    note: str = Field(default="", max_length=256)
    spent_at: datetime | None = None


class ExpenseOut(BaseModel):
    id: int
    amount: float
    note: str
    spent_at: datetime
    category: CategoryOut | None


class CategoryStat(BaseModel):
    id: int | None
    name: str
    emoji: str
    color: str
    total: float
    count: int


class DayStat(BaseModel):
    date: date
    total: float


class Stats(BaseModel):
    period: str
    start: date
    end: date  # включительно
    total: float
    prev_total: float
    avg_per_day: float
    by_category: list[CategoryStat]
    by_day: list[DayStat]


class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    remind_at: datetime | None = None


class TaskPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=256)
    remind_at: datetime | None = None
    clear_remind: bool = False
    done: bool | None = None


class TaskOut(BaseModel):
    id: int
    title: str
    remind_at: datetime | None
    reminded: bool
    done: bool
    created_at: datetime
