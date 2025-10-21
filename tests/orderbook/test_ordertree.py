from decimal import Decimal

from src.orderbook.ordertree import OrderTree


def _insert(
    tree: OrderTree,
    order_id: int,
    price: str,
    qty: str,
    ts: int = 1,
    trade_id: str | None = None,
):
    tree.insert_order(
        {
            "order_id": order_id,
            "price": Decimal(price),
            "quantity": Decimal(qty),
            "timestamp": ts,
            "trade_id": trade_id or str(order_id),
        }
    )


def test_ordertree_insert_and_price_navigation():
    tree = OrderTree()
    _insert(tree, 1, "100", "2")
    _insert(tree, 2, "101", "3")
    assert tree.depth == 2
    assert tree.min_price() == Decimal("100")
    assert tree.max_price() == Decimal("101")
    assert tree.volume == Decimal("5")
    assert tree.num_orders == 2


def test_ordertree_multiple_orders_same_price_volume_accumulates():
    tree = OrderTree()
    _insert(tree, 1, "100", "2")
    _insert(tree, 2, "100", "3")
    price_list = tree.get_price_list(Decimal("100"))
    assert len(price_list) == 2
    assert tree.depth == 1
    assert tree.volume == Decimal("5")


def test_ordertree_update_quantity_moves_to_tail_and_adjusts_volume():
    tree = OrderTree()
    _insert(tree, 1, "100", "2", ts=1)
    _insert(tree, 2, "100", "3", ts=2)
    price_list = tree.get_price_list(Decimal("100"))
    # Order 1 is head, 2 tail
    tree.update_order(
        {
            "order_id": 1,
            "price": Decimal("100"),
            "quantity": Decimal("5"),  # increase triggers move to tail
            "timestamp": 3,
        }
    )
    # after increase, order 1 should be tail
    assert price_list.tail_order.order_id == 1
    assert tree.volume == Decimal("8")


def test_ordertree_update_price_reinserts_and_cleans_old_level():
    tree = OrderTree()
    _insert(tree, 1, "100", "2")
    assert tree.depth == 1
    tree.update_order(
        {
            "order_id": 1,
            "price": Decimal("101"),
            "quantity": Decimal("2"),
            "timestamp": 2,
        }
    )
    assert tree.depth == 1  # moved, still one level but different price
    assert tree.min_price() == Decimal("101")
    assert not tree.price_exists(Decimal("100"))


def test_ordertree_remove_order_cleans_price_level():
    tree = OrderTree()
    _insert(tree, 1, "100", "2")
    tree.remove_order_by_id(1)
    assert tree.depth == 0
    assert tree.volume == 0
    assert tree.num_orders == 0


def test_ordertree_reinsert_same_id_replaces_order():
    tree = OrderTree()
    _insert(tree, 1, "100", "2")
    # inserting again with same id different qty should replace
    _insert(tree, 1, "100", "5")
    assert tree.num_orders == 1
    price_list = tree.get_price_list(Decimal("100"))
    head = price_list.get_head_order()
    assert head.quantity == Decimal("5")
