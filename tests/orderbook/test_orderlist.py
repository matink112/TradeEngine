from decimal import Decimal

from src.orderbook.order import Order
from src.orderbook.orderlist import OrderList


def _make(order_list, oid, ts, qty="5", price="100"):
    o = Order({"timestamp": ts, "quantity": qty, "price": price, "order_id": oid}, order_list)
    order_list.append_order(o)
    return o


def test_orderlist_append_and_iteration_order():
    ol = OrderList()
    o1 = _make(ol, 1, 1)
    o2 = _make(ol, 2, 2)
    assert list(ol)[0] is o1
    assert list(ol)[1] is o2
    assert ol.length == 2
    assert ol.head_order is o1
    assert ol.tail_order is o2


def test_orderlist_remove_head():
    ol = OrderList()
    o1 = _make(ol, 1, 1)
    o2 = _make(ol, 2, 2)
    vol_before = ol.volume
    ol.remove(o1)
    assert ol.head_order is o2
    assert ol.length == 1
    assert ol.volume == vol_before - Decimal("5")


def test_orderlist_remove_tail():
    ol = OrderList()
    o1 = _make(ol, 1, 1)
    o2 = _make(ol, 2, 2)
    vol_before = ol.volume
    ol.remove(o2)
    assert ol.tail_order is o1
    assert ol.length == 1
    assert ol.volume == vol_before - Decimal("5")


def test_orderlist_remove_middle():
    ol = OrderList()
    o1 = _make(ol, 1, 1)
    o2 = _make(ol, 2, 2)
    o3 = _make(ol, 3, 3)
    vol_before = ol.volume
    ol.remove(o2)
    assert ol.length == 2
    assert o1.next_order is o3
    assert o3.prev_order is o1
    assert ol.volume == vol_before - Decimal("5")


def test_orderlist_move_to_tail_priority_loss():
    ol = OrderList()
    o1 = _make(ol, 1, 1)
    o2 = _make(ol, 2, 2)
    ol.move_to_tail(o1)
    assert ol.tail_order is o1
    assert ol.head_order is o2


def test_orderlist_only_order_remove():
    ol = OrderList()
    o1 = _make(ol, 1, 1)
    vol_before = ol.volume
    ol.remove(o1)
    assert ol.length == 0
    # volume decreased by quantity
    assert vol_before - Decimal("5") == ol.volume
    assert ol.head_order is None and ol.tail_order is None

