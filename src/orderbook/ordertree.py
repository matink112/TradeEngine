from typing import Optional

from sortedcontainers import SortedDict, SortedKeysView

from src.orderbook.order import Order
from src.orderbook.orderlist import OrderList


class OrderTree:
    """Price-ordered tree of order lists keyed by price."""

    def __init__(self) -> None:
        self._price_map: SortedDict = SortedDict()
        self._order_map: dict[int, Order] = {}
        self._volume: int = 0
        self._num_orders: int = 0

    def __len__(self) -> int:
        return len(self._order_map)

    @property
    def volume(self) -> int:
        return self._volume

    @property
    def num_orders(self) -> int:
        return self._num_orders

    @property
    def depth(self) -> int:
        return len(self._price_map)

    @property
    def prices(self) -> SortedKeysView:
        return self._price_map.keys()

    def get_price_list(self, price: float) -> OrderList:
        return self._price_map[price]

    def get_order(self, order_id: int) -> Order:
        return self._order_map[order_id]

    def price_exists(self, price: float) -> bool:
        return price in self._price_map

    def order_exists(self, order_id: int) -> bool:
        return order_id in self._order_map

    def trade_id_exists(self, trade_id: str) -> bool:
        return any(order.trade_id == trade_id for order in self._order_map.values())

    def insert_order(self, order_data: dict) -> None:
        order_id = int(order_data["order_id"])
        price = order_data["price"]
        if self.order_exists(order_id):
            self.remove_order_by_id(order_id)

        self._ensure_price_level_exists(price)
        order = self._create_and_add_order(order_data, price)
        self._order_map[order_id] = order
        self._num_orders += 1
        self._volume += order.quantity

    def update_order(self, updated_data: dict) -> None:
        order_id = int(updated_data["order_id"])
        order = self._order_map[order_id]
        original_quantity = order.quantity

        if self._is_price_changed(updated_data["price"], order.price):
            self._handle_price_change(order, updated_data)
        else:
            self._handle_quantity_change(order, updated_data)

        self._volume += order.quantity - original_quantity

    def remove_order_by_id(self, order_id: int) -> None:
        order = self._order_map[order_id]
        self._remove_order_from_list(order)
        self._cleanup_empty_price_level(order.price, order.order_list)
        del self._order_map[order_id]
        self._num_orders -= 1
        self._volume -= order.quantity

    def max_price(self) -> Optional[float]:
        if self.depth == 0:
            return None
        return self.prices[-1]

    def min_price(self) -> Optional[float]:
        if self.depth == 0:
            return None
        return self.prices[0]

    def max_price_list(self) -> Optional[OrderList]:
        max_price = self.max_price()
        return self.get_price_list(max_price) if max_price is not None else None

    def min_price_list(self) -> Optional[OrderList]:
        min_price = self.min_price()
        return self.get_price_list(min_price) if min_price is not None else None

    def _ensure_price_level_exists(self, price: float) -> None:
        if price not in self._price_map:
            self._price_map[price] = OrderList()

    def _create_and_add_order(self, order_data: dict, price: float) -> Order:
        price_list = self._price_map[price]
        order_data["order_id"] = int(order_data["order_id"])
        order = Order(order_data, price_list)
        price_list.append_order(order)
        return order

    @staticmethod
    def _is_price_changed(new_price: float, old_price: float) -> bool:
        return new_price != old_price

    def _handle_price_change(self, order: Order, updated_data: dict) -> None:
        # Remove order from its current price list and clean that level if empty
        self._remove_order_from_list(order)
        self._cleanup_empty_price_level(order.price, order.order_list)
        # Remove from order map and adjust global counters/volume
        del self._order_map[order.order_id]
        self._num_orders -= 1
        self._volume -= order.quantity
        # Reinsert with updated price (and quantity unchanged for now)
        self.insert_order(updated_data)

    @staticmethod
    def _handle_quantity_change(order: Order, updated_data: dict) -> None:
        order.update_quantity(updated_data["quantity"], updated_data["timestamp"])

    @staticmethod
    def _remove_order_from_list(order: Order) -> None:
        order.order_list.remove_order(order)

    def _cleanup_empty_price_level(self, price: float, order_list: OrderList) -> None:
        if len(order_list) == 0:
            del self._price_map[price]
