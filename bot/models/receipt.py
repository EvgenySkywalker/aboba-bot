import datetime
from typing import Literal, Annotated, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from bot.models.category import Category


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class ReceiptItem(Category, CamelModel):
    name: str
    price_with_vat: int
    price_with_vat_usd: float | None = None
    count: int


class ValidReceipt(CamelModel):
    is_readable: Literal[True]
    store_name: str
    store_name_jp: str
    date: datetime.date
    items: list[ReceiptItem]
    total_amount: int
    total_amount_usd: float | None = None
    currency: str


class NonReceipt(CamelModel):
    is_readable: Literal[False]
    store_name: str | None = None
    store_name_jp: str | None = None
    date: datetime.date | None = None
    items: list[ReceiptItem] = Field(default_factory=list)
    total_amount: int | None = None
    currency: str | None = None
    total_amount_usd: float | None = None


Receipt = Annotated[
    Union[ValidReceipt, NonReceipt], Field(discriminator='is_readable')
]
