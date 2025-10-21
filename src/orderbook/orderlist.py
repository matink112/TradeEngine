from typing import Optional

from src.orderbook.order import Order


class OrderList:
    """
    Doubly linked list of Orders organized by time priority.

    Orders at the head have the highest priority (earliest timestamp).
    Used for matching orders at a specific price level.
    """

    def __init__(self) -> None:
        self.head_order: Optional[Order] = None
        self.tail_order: Optional[Order] = None
        self.length: int = 0
        self.volume: int = 0
        self._current: Optional[Order] = None

    def __len__(self) -> int:
        return self.length

    def __iter__(self):
        self._current = self.head_order
        return self

    def __next__(self) -> Order:
        if self._current is None:
            raise StopIteration

        current_order = self._current
        self._current = self._current.next_order
        return current_order

    def get_head_order(self) -> Optional[Order]:
        return self.head_order

    def is_empty(self) -> bool:
        return self.length == 0

    def append_order(self, order: Order) -> None:
        """Add order to the end of the list (lowest priority)."""
        if self.is_empty():
            self._set_as_only_order(order)
        else:
            self._append_to_tail(order)

        self._update_metrics_on_add(order)

    def remove(self, order: Order) -> None:
        """Remove order from the list and relink neighbors."""
        self._update_metrics_on_remove(order)

        # If now empty, clear head/tail and return
        if self.is_empty():
            self.head_order = None
            self.tail_order = None
            return

        self._relink_after_removal(order)

    # Alias used by OrderTree
    def remove_order(self, order: Order) -> None:
        self.remove(order)

    def move_to_tail(self, order: Order) -> None:
        """Move order to end of list (loses time priority)."""
        if self._is_only_order(order):
            return

        self._unlink_from_current_position(order)
        self._append_to_tail(order)

    def _set_as_only_order(self, order: Order) -> None:
        """Initialize list with a single order."""
        order.next_order = None
        order.prev_order = None
        self.head_order = order
        self.tail_order = order

    def _append_to_tail(self, order: Order) -> None:
        """Append order to the end of the list."""
        order.prev_order = self.tail_order
        order.next_order = None
        self.tail_order.next_order = order  # type: ignore[union-attr]
        self.tail_order = order

    def _update_metrics_on_add(self, order: Order) -> None:
        """Update length and volume when adding order."""
        self.length += 1
        self.volume += order.quantity

    def _update_metrics_on_remove(self, order: Order) -> None:
        """Update length and volume when removing order."""
        self.volume -= order.quantity
        self.length -= 1

    def _relink_after_removal(self, order: Order) -> None:
        """Relink neighboring orders after removing an order."""
        if self._is_middle_order(order):
            self._link_neighbors(order)
        elif self._is_tail_order(order):
            self._remove_tail_order(order)
        elif self._is_head_order(order):
            self._remove_head_order(order)

    @staticmethod
    def _is_middle_order(order: Order) -> bool:
        """Check if order has both neighbors."""
        return order.next_order is not None and order.prev_order is not None

    @staticmethod
    def _is_tail_order(order: Order) -> bool:
        """Check if order is at the tail."""
        return order.next_order is None and order.prev_order is not None

    @staticmethod
    def _is_head_order(order: Order) -> bool:
        """Check if order is at the head."""
        return order.prev_order is None and order.next_order is not None

    @staticmethod
    def _is_only_order(order: Order) -> bool:
        """Check if this is the only order in the list."""
        return order.prev_order is None and order.next_order is None

    @staticmethod
    def _link_neighbors(order: Order) -> None:
        """Link the neighbors of an order together."""
        order.next_order.prev_order = order.prev_order  # type: ignore[union-attr]
        order.prev_order.next_order = order.next_order  # type: ignore[union-attr]

    def _remove_tail_order(self, order: Order) -> None:
        """Remove order from tail position."""
        order.prev_order.next_order = None  # type: ignore[union-attr]
        self.tail_order = order.prev_order

    def _remove_head_order(self, order: Order) -> None:
        """Remove order from head position."""
        order.next_order.prev_order = None  # type: ignore[union-attr]
        self.head_order = order.next_order

    def _unlink_from_current_position(self, order: Order) -> None:
        """Remove order from its current position without updating metrics."""
        if order.prev_order is not None:
            order.prev_order.next_order = order.next_order
        else:
            self.head_order = order.next_order

        if order.next_order is not None:
            order.next_order.prev_order = order.prev_order

    def __str__(self) -> str:
        order_strings = [
            f'{order.order_id}/{order.quantity}/{order.price}'
            for order in self
        ]
        return ', '.join(order_strings)
