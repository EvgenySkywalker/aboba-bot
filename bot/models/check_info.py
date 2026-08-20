import datetime
from typing import Literal, Annotated, Union

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class ReceiptItem(CamelModel):
    name: str
    price_with_vat: int
    category: str
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
    currency: str
    total_amount_usd: float | None = None


CheckInfo = Annotated[
    Union[ValidReceipt, NonReceipt], Field(discriminator='is_readable')
]
