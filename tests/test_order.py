from decimal import Decimal

from src.orderbook.order import Order
from src.orderbook.orderlist import OrderList


def test_order_update_quantity_moves_to_tail():
    order_list = OrderList()
    # Create two orders at same price
    o1 = Order({"timestamp": 1, "quantity": "5", "price": "100", "order_id": 1}, order_list)
    order_list.append_order(o1)
    o2 = Order({"timestamp": 2, "quantity": "5", "price": "100", "order_id": 2}, order_list)
    order_list.append_order(o2)
    assert order_list.head_order is o1
    assert order_list.tail_order is o2

    # Increase quantity of head (o1) should move it to tail
    o1.update_quantity(Decimal("10"), new_timestamp=3)
    assert order_list.tail_order is o1
    assert order_list.head_order is o2


def test_order_update_quantity_reduces_volume_and_stays_if_not_increase():
    order_list = OrderList()
    o1 = Order({"timestamp": 1, "quantity": "5", "price": "100", "order_id": 1}, order_list)
    order_list.append_order(o1)
    start_volume = order_list.volume
    # Decrease quantity (no move to tail logic triggered)
    o1.update_quantity(Decimal("2"), new_timestamp=2)
    assert order_list.head_order is o1
    assert order_list.volume == start_volume - (Decimal("5") - Decimal("2"))


def test_order_to_dict_contains_expected_fields():
    order_list = OrderList()
    o1 = Order({"timestamp": 1, "quantity": "5", "price": "100", "order_id": 42, "trade_id": "T42", "wage": "W"}, order_list)
    order_list.append_order(o1)
    d = o1.to_dict()
    assert d["order_id"] == 42
    assert d["trade_id"] == "T42"
    assert d["price"] == "100"
    assert d["quantity"] == "5"
    assert d["wage"] == "W"

