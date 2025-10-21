from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from src.orderbook.orderlist import OrderList


class Order:
    """
    Represents a bid or ask order in the exchange.

    Orders are organized in a doubly-linked list structure to maintain
    time priority and enable efficient traversal when fulfilling large orders.
    """

    def __init__(self, data: dict[str, Any], order_list: "OrderList") -> None:
        """
        Initialize an order from raw data.

        Args:
            data: Dictionary containing order details (timestamp, quantity, price, etc.)
            order_list: Reference to the parent OrderList containing this order
        """
        self.timestamp: int = int(data["timestamp"])
        self.quantity: Decimal = Decimal(data["quantity"])
        self.price: Decimal = Decimal(data["price"])
        self.order_id: int = int(data["order_id"])
        self.trade_id: str = data.get("trade_id", str(self.order_id))
        self.wage: Any = data.get("wage")

        # Internal linked list pointers
        self._next: Optional["Order"] = None
        self._prev: Optional["Order"] = None
        self.order_list: "OrderList" = order_list

    # Compatibility attributes expected by OrderList / OrderTree
    @property
    def next_order(self) -> Optional["Order"]:
        return self._next

    @next_order.setter
    def next_order(self, order: Optional["Order"]) -> None:
        self._next = order

    @property
    def prev_order(self) -> Optional["Order"]:
        return self._prev

    @prev_order.setter
    def prev_order(self, order: Optional["Order"]) -> None:
        self._prev = order

    # Original API kept for completeness
    @property
    def next(self) -> Optional["Order"]:
        return self._next

    @next.setter
    def next(self, order: Optional["Order"]) -> None:  # type: ignore[override]
        self._next = order

    @property
    def prev(self) -> Optional["Order"]:
        return self._prev

    @prev.setter
    def prev(self, order: Optional["Order"]) -> None:  # type: ignore[override]
        self._prev = order

    def update_quantity(self, new_quantity: Decimal, new_timestamp: int) -> None:
        """
        Update the order quantity and timestamp.

        If quantity increases and this isn't the tail order, the order loses
        time priority and moves to the end of the list.

        Args:
            new_quantity: The new quantity for this order
            new_timestamp: The timestamp of the update
        """
        should_move_to_tail = (
            new_quantity > self.quantity and self.order_list.tail_order != self
        )

        if should_move_to_tail:
            self.order_list.move_to_tail(self)

        quantity_delta = self.quantity - new_quantity
        self.order_list.volume -= quantity_delta

        self.timestamp = new_timestamp
        self.quantity = new_quantity

    def to_dict(self) -> dict[str, Any]:
        return {
            "order_id": self.order_id,
            "timestamp": self.timestamp,
            "quantity": str(self.quantity),
            "price": str(self.price),
            "trade_id": self.trade_id,
            "wage": self.wage,
        }

    def __str__(self) -> str:
        """Return a human-readable string representation of the order."""
        return (
            f"quantity: {self.quantity} @ price: {self.price} / "
            f"trade_id: {self.trade_id} - time: {self.timestamp}"
        )
