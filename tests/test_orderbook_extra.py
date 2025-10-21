from decimal import Decimal

import pytest

from src.exceptions import OrderNotFoundError, OrderTypeError, QuantityError
from src.orderbook.orderbook import (
    ORDER_TYPE_LIMIT,
    ORDER_TYPE_MARKET,
    SIDE_ASK,
    SIDE_BID,
    OrderBook,
)


def test_timestamp_increments_each_operation():
    book = OrderBook()
    start_time = book.time
    book.process_order(
        {"side": SIDE_BID, "type": ORDER_TYPE_LIMIT, "quantity": "1", "price": "10"},
        False,
        False,
    )
    first_time = book.time
    book.process_order(
        {"side": SIDE_ASK, "type": ORDER_TYPE_LIMIT, "quantity": "1", "price": "11"},
        False,
        False,
    )
    second_time = book.time
    assert first_time == start_time + 1
    assert second_time == first_time + 1


def test_market_order_crosses_multiple_price_levels():
    book = OrderBook()
    # Set up two ask levels
    book.process_order(
        {"side": SIDE_ASK, "type": ORDER_TYPE_LIMIT, "quantity": "2", "price": "10"},
        False,
        False,
    )
    book.process_order(
        {"side": SIDE_ASK, "type": ORDER_TYPE_LIMIT, "quantity": "3", "price": "11"},
        False,
        False,
    )
    # Market bid with quantity spanning both levels (total 5)
    trades, _ = book.process_order(
        {"side": SIDE_BID, "type": ORDER_TYPE_MARKET, "quantity": "5"}, False, False
    )
    assert len(trades) == 2
    assert book.asks.volume == 0


def test_modify_order_decrease_quantity_no_tail_move():
    book = OrderBook()
    # Two bids same price
    book.process_order(
        {"side": SIDE_BID, "type": ORDER_TYPE_LIMIT, "quantity": "5", "price": "10"},
        False,
        False,
    )
    book.process_order(
        {"side": SIDE_BID, "type": ORDER_TYPE_LIMIT, "quantity": "5", "price": "10"},
        False,
        False,
    )
    price_list = book.bids.get_price_list(Decimal("10"))
    head_before = price_list.head_order.order_id
    # Decrease quantity of head
    book.modify_order(head_before, {"side": SIDE_BID, "quantity": "3", "price": "10"})
    assert price_list.head_order.order_id == head_before  # still head


def test_volume_invariants_never_negative():
    book = OrderBook()
    book.process_order(
        {"side": SIDE_BID, "type": ORDER_TYPE_LIMIT, "quantity": "2", "price": "10"},
        False,
        False,
    )
    book.process_order(
        {"side": SIDE_ASK, "type": ORDER_TYPE_LIMIT, "quantity": "2", "price": "10"},
        False,
        False,
    )  # trade occurs
    assert book.bids.volume >= 0 and book.asks.volume >= 0


def test_quantity_error_on_zero():
    book = OrderBook()
    with pytest.raises(QuantityError):
        book.process_order(
            {"side": SIDE_BID, "type": ORDER_TYPE_LIMIT, "quantity": 0, "price": "10"},
            False,
            False,
        )


def test_order_type_error_on_invalid_side():
    book = OrderBook()
    with pytest.raises(OrderTypeError):
        book.process_order(
            {"side": "bad", "type": ORDER_TYPE_LIMIT, "quantity": "1", "price": "10"},
            False,
            False,
        )


def test_cancel_order_not_found_raises():
    book = OrderBook()
    with pytest.raises(OrderNotFoundError):
        book.cancel_order(SIDE_BID, 999)
