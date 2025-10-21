from typing import Optional

from sortedcontainers import SortedDict, SortedKeysView

from src.order import Order
from src.orderlist import OrderList


class OrderTree:
    """
    A price-ordered tree structure for managing order books.

    This class maintains orders organized by price level using a sorted dictionary,
    enabling efficient order matching for bid/ask sides of an exchange.
    """

    def __init__(self) -> None:
        self._price_map: SortedDict = SortedDict()
        self._order_map: dict[str, Order] = {}
        self._volume: int = 0
        self._num_orders: int = 0

    def __len__(self) -> int:
        """Return the total number of orders in the tree."""
        return len(self._order_map)

    @property
    def volume(self) -> int:
        """Total quantity from all orders in the tree."""
        return self._volume

    @property
    def num_orders(self) -> int:
        """Total count of orders in the tree."""
        return self._num_orders

    @property
    def depth(self) -> int:
        """Number of different price levels in the tree."""
        return len(self._price_map)

    @property
    def prices(self) -> SortedKeysView:
        """View of all price levels in sorted order."""
        return self._price_map.keys()

    def get_price_list(self, price: float) -> OrderList:
        """
        Retrieve the order list at a specific price level.

        Args:
            price: The price level to retrieve

        Returns:
            OrderList at the specified price

        Raises:
            KeyError: If the price level doesn't exist
        """
        return self._price_map[price]

    def get_order(self, order_id: str) -> Order:
        """
        Retrieve an order by its ID.

        Returns:
            Order object with the specified ID

        Raises:
            KeyError: If the order doesn't exist
        """
        return self._order_map[order_id]

    def price_exists(self, price: float) -> bool:
        """Check if a price level exists in the tree."""
        return price in self._price_map

    def order_exists(self, order_id: str) -> bool:
        """Check if an order exists in the tree."""
        return order_id in self._order_map

    def trade_id_exists(self, trade_id: str) -> bool:
        """Check if any order with the given trade ID exists."""
        return any(order.trade_id == trade_id for order in self._order_map.values())

    def insert_order(self, order_data: dict) -> None:
        """
        Insert a new order into the tree.

        If an order with the same ID exists, it will be replaced.

        Args:
            order_data: Dictionary containing order details (order_id, price, quantity, etc.)
        """
        order_id = order_data["order_id"]
        price = order_data["price"]

        if self.order_exists(order_id):
            self.remove_order_by_id(order_id)

        self._ensure_price_level_exists(price)
        order = self._create_and_add_order(order_data, price)

        self._order_map[order_id] = order
        self._num_orders += 1
        self._volume += order.quantity

    def update_order(self, updated_data: dict) -> None:
        """
        Update an existing order with new data.

        Args:
            updated_data: Dictionary containing updated order details

        Raises:
            KeyError: If the order doesn't exist
        """
        order_id = updated_data["order_id"]
        order = self._order_map[order_id]
        original_quantity = order.quantity

        if self._is_price_changed(updated_data["price"], order.price):
            self._handle_price_change(order, updated_data)
        else:
            self._handle_quantity_change(order, updated_data)

        self._volume += order.quantity - original_quantity

    def remove_order_by_id(self, order_id: str) -> None:
        """
        Remove an order from the tree by its ID.

        Args:
            order_id: The unique identifier of the order to remove

        Raises:
            KeyError: If the order doesn't exist
        """
        order = self._order_map[order_id]

        self._remove_order_from_list(order)
        self._cleanup_empty_price_level(order.price, order.order_list)

        del self._order_map[order_id]
        self._num_orders -= 1
        self._volume -= order.quantity

    def max_price(self) -> Optional[float]:
        """Return the highest price level, or None if tree is empty."""
        if self.depth == 0:
            return None
        return self.prices[-1]

    def min_price(self) -> Optional[float]:
        """Return the lowest price level, or None if tree is empty."""
        if self.depth == 0:
            return None
        return self.prices[0]

    def max_price_list(self) -> Optional[OrderList]:
        """Return the order list at the highest price level, or None if tree is empty."""
        max_price = self.max_price()
        return self.get_price_list(max_price) if max_price is not None else None

    def min_price_list(self) -> Optional[OrderList]:
        """Return the order list at the lowest price level, or None if tree is empty."""
        min_price = self.min_price()
        return self.get_price_list(min_price) if min_price is not None else None

    def _ensure_price_level_exists(self, price: float) -> None:
        """Create a price level if it doesn't exist."""
        if price not in self._price_map:
            self._price_map[price] = OrderList()

    def _create_and_add_order(self, order_data: dict, price: float) -> Order:
        """Create an order and add it to the appropriate price level."""
        price_list = self._price_map[price]
        order = Order(order_data, price_list)
        price_list.append_order(order)
        return order

    @staticmethod
    def _is_price_changed(new_price: float, old_price: float) -> bool:
        """Check if the price has changed."""
        return new_price != old_price

    def _handle_price_change(self, order: Order, updated_data: dict) -> None:
        """Handle order update when price changes."""
        self._remove_order_from_list(order)
        self._cleanup_empty_price_level(order.price, order.order_list)
        self.insert_order(updated_data)

    @staticmethod
    def _handle_quantity_change(order: Order, updated_data: dict) -> None:
        """Handle order update when only quantity changes."""
        order.update_quantity(updated_data["quantity"], updated_data["timestamp"])

    @staticmethod
    def _remove_order_from_list(order: Order) -> None:
        """Remove an order from its order list."""
        order.order_list.remove_order(order)

    def _cleanup_empty_price_level(self, price: float, order_list: OrderList) -> None:
        """Remove a price level if it has no orders."""
        if len(order_list) == 0:
            del self._price_map[price]
