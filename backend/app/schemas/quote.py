from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class NightPriceRead(BaseModel):
    night: date
    price: Decimal


class StayQuoteRead(BaseModel):
    check_in: date
    check_out: date
    nights_count: int
    nights: list[NightPriceRead]
    total: Decimal
    currency: str = "EUR"
