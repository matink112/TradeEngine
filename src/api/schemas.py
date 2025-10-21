from typing import Optional, Literal, List
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator

Side = Literal['bid', 'ask']
OrderType = Literal['limit', 'market']

class OrderCreate(BaseModel):
    side: Side
    type: OrderType
    quantity: Decimal = Field(gt=0)
    price: Optional[Decimal] = Field(default=None, gt=0)
    trade_id: Optional[str] = None
    wage: Optional[str] = None

    @field_validator('price')
    def price_required_for_limit(cls, v, info):  # noqa: D417
        # info.data contains other field values already validated
        if info.data.get('type') == 'limit' and v is None:
            raise ValueError('price is required for limit orders')
        return v

class OrderModify(BaseModel):
    quantity: Optional[Decimal] = Field(default=None, gt=0)
    price: Optional[Decimal] = Field(default=None, gt=0)

    def apply(self, existing: dict) -> dict:
        data = existing.copy()
        if self.quantity is not None:
            data['quantity'] = self.quantity
        if self.price is not None:
            data['price'] = self.price
        return data

class OrderOut(BaseModel):
    order_id: int
    side: Side
    quantity: Decimal
    price: Decimal
    timestamp: int
    trade_id: Optional[str]
    wage: Optional[str]

class TradeParty(BaseModel):
    trade_id: str
    side: Side
    order_id: int
    new_book_quantity: Optional[Decimal]
    wage: Optional[str]

class TradeOut(BaseModel):
    timestamp: int
    price: Decimal
    quantity: Decimal
    time: int
    party1: TradeParty
    party2: TradeParty

class OrderProcessResult(BaseModel):
    trades: List[TradeOut]
    order: Optional[OrderOut]

class SummaryOut(BaseModel):
    best_bid: Optional[Decimal]
    best_ask: Optional[Decimal]
    bid_volume: int
    ask_volume: int
    time: int
