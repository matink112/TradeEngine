from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from src.orderbook.orderbook import OrderBook
from src.api.schemas import (
    OrderCreate,
    OrderModify,
    OrderOut,
    OrderProcessResult,
    SummaryOut,
)
from src.exceptions import QuantityError, OrderTypeError, OrderNotFoundError

# Singleton order book
book = OrderBook(market_name="TEST/PAIR")

router = APIRouter(prefix="/api", tags=["orderbook"])


def get_book() -> OrderBook:
    return book


@router.post(
    "/orders", response_model=OrderProcessResult, status_code=status.HTTP_201_CREATED
)
def create_order(payload: OrderCreate, book: OrderBook = Depends(get_book)):
    data = payload.dict()
    try:
        trades, order = book.process_order(data, from_data=False, verbose=False)
    except (QuantityError, OrderTypeError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    order_out = None
    if order:
        order_out = OrderOut(
            order_id=order["order_id"],
            side=payload.side,
            quantity=order["quantity"],
            price=order["price"],
            timestamp=order["timestamp"],
            trade_id=order.get("trade_id"),
            wage=order.get("wage"),
        )
    return {"trades": trades, "order": order_out}


@router.get("/orders/{side}", response_model=list[OrderOut])
def list_orders(side: str, book: OrderBook = Depends(get_book)):
    try:
        orders = book.list_orders(side)
    except OrderTypeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return [
        OrderOut(
            order_id=o["order_id"],
            side=side,  # type: ignore[arg-type]
            quantity=o["quantity"],
            price=o["price"],
            timestamp=o["timestamp"],
            trade_id=o.get("trade_id"),
            wage=o.get("wage"),
        )
        for o in orders
    ]


@router.get("/orders/{side}/{order_id}", response_model=OrderOut)
def get_order(side: str, order_id: int, book: OrderBook = Depends(get_book)):
    try:
        order = book.get_order(side, order_id)
    except (OrderTypeError, OrderNotFoundError) as e:
        code = 404 if isinstance(e, OrderNotFoundError) else 400
        raise HTTPException(status_code=code, detail=str(e)) from e
    return OrderOut(
        order_id=order["order_id"],
        side=side,  # type: ignore[arg-type]
        quantity=order["quantity"],
        price=order["price"],
        timestamp=order["timestamp"],
        trade_id=order.get("trade_id"),
        wage=order.get("wage"),
    )


@router.patch("/orders/{side}/{order_id}", response_model=OrderOut)
def modify_order(
    side: str, order_id: int, updates: OrderModify, book: OrderBook = Depends(get_book)
):
    try:
        existing = book.get_order(side, order_id)
    except (OrderTypeError, OrderNotFoundError) as e:
        code = 404 if isinstance(e, OrderNotFoundError) else 400
        raise HTTPException(status_code=code, detail=str(e)) from e

    merged = updates.apply(
        {
            "order_id": existing["order_id"],
            "side": side,
            "quantity": existing["quantity"],
            "price": existing["price"],
        }
    )
    try:
        book.modify_order(order_id, merged)
    except (OrderTypeError, OrderNotFoundError, QuantityError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    updated = book.get_order(side, order_id)
    return OrderOut(
        order_id=updated["order_id"],
        side=side,  # type: ignore[arg-type]
        quantity=updated["quantity"],
        price=updated["price"],
        timestamp=updated["timestamp"],
        trade_id=updated.get("trade_id"),
        wage=updated.get("wage"),
    )


@router.delete("/orders/{side}/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(side: str, order_id: int, book: OrderBook = Depends(get_book)):
    try:
        book.cancel_order(side, order_id)
    except (OrderTypeError, OrderNotFoundError) as e:
        code = 404 if isinstance(e, OrderNotFoundError) else 400
        raise HTTPException(status_code=code, detail=str(e)) from e
    return JSONResponse(status_code=204, content=None)


@router.get("/summary", response_model=SummaryOut)
def summary(book: OrderBook = Depends(get_book)):
    try:
        return book.summary()
    except Exception as e:  # broad catch to avoid unhandled errors
        raise HTTPException(status_code=500, detail=str(e)) from e
