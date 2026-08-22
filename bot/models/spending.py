import datetime

from bot.models.category import Category
from bot.models.receipt import CamelModel


class Spending(Category, CamelModel):
    amount: int
    recipient: str
    date: datetime.date
    description: str
    amount_usd: float | None = None
