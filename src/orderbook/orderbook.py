from decimal import Decimal
from typing import Any, Literal, Optional

from src.exceptions import OrderNotFoundError, OrderTypeError, QuantityError
from src.orderbook.ordertree import OrderTree
from src.orderbook.trade import TradeDataFrame

Side = Literal["bid", "ask"]


# Constants
SIDE_BID: Side = "bid"
SIDE_ASK: Side = "ask"
ORDER_TYPE_LIMIT = "limit"
ORDER_TYPE_MARKET = "market"
VALID_SIDES = {SIDE_BID, SIDE_ASK}
VALID_ORDER_TYPES = {ORDER_TYPE_LIMIT, ORDER_TYPE_MARKET}
DEFAULT_TICK_SIZE = 0.0001


class OrderBook:
    def __init__(
        self, tick_size: float = DEFAULT_TICK_SIZE, market_name: Optional[str] = None
    ):
        self.trade_df = TradeDataFrame(self)
        self.bids = OrderTree()
        self.asks = OrderTree()
        self.last_tick = None
        self.last_timestamp = 0
        self.tick_size = tick_size
        self.time = 0
        self.next_order_id = 0
        self.market_name = market_name or "UNKNOWN/PAIR"
        self.is_closed = False
        self.closed_reason = None

    def update_time(self) -> None:
        self.time += 1

    def process_order(
        self, data: dict[str, Any], from_data: bool, verbose: bool
    ) -> tuple[list[dict[str, Any]], Optional[dict[str, Any]]]:
        # Convert to Decimal before validation so numeric comparisons work
        self._prepare_quote_types(data)
        self._validate_order(data)
        self._update_timestamp(data, from_data)

        if not from_data:
            self.next_order_id += 1
            data["order_id"] = self.next_order_id

        order_type = data["type"]
        if order_type == ORDER_TYPE_MARKET:
            return self.process_market_order(data, verbose), None

        return self.process_limit_order(data, from_data, verbose)

    def process_market_order(
        self, data: dict[str, Any], verbose: bool
    ) -> list[dict[str, Any]]:
        self._validate_side(data["side"])

        quantity_to_trade = data["quantity"]
        side = data["side"]

        return (
            self._execute_market_order_against_asks(data, quantity_to_trade, verbose)
            if side == SIDE_BID
            else self._execute_market_order_against_bids(
                data, quantity_to_trade, verbose
            )
        )

    def process_limit_order(
        self, data: dict[str, Any], from_data: bool, verbose: bool
    ) -> tuple[list[dict[str, Any]], Optional[dict[str, Any]]]:
        self._validate_side(data["side"])

        quantity_to_trade = data["quantity"]
        side = data["side"]
        price = data["price"]

        if side == SIDE_BID:
            quantity_to_trade, trades = self._match_bid_order(
                data, price, quantity_to_trade, verbose
            )
        else:
            quantity_to_trade, trades = self._match_ask_order(
                data, price, quantity_to_trade, verbose
            )

        order_in_book = self._add_remaining_to_book(
            data, quantity_to_trade, side, from_data
        )
        return trades, order_in_book

    def cancel_order(
        self, side: str, order_id: int, time: Optional[int] = None
    ) -> None:
        self._validate_side(side)
        self._update_time_if_needed(time)

        order_tree = self._get_order_tree(side)
        if not order_tree.order_exists(order_id):
            raise OrderNotFoundError(
                f"Order with id: {order_id} and side: {side} not found"
            )

        order_tree.remove_order_by_id(order_id)

    def modify_order(
        self, order_id: int, order_update: dict[str, Any], time: Optional[int] = None
    ) -> None:
        self._validate_side(order_update["side"])
        self._update_time_if_needed(time)

        order_update["order_id"] = order_id
        order_update["timestamp"] = self.time

        order_tree = self._get_order_tree(order_update["side"])
        if not order_tree.order_exists(order_id):
            raise OrderNotFoundError(
                f"Order with id: {order_id} and side: {order_update['side']} not found"
            )

        # ensure decimals
        order_update["quantity"] = Decimal(str(order_update["quantity"]))
        order_update["price"] = Decimal(str(order_update["price"]))
        order_tree.update_order(order_update)

    # --- Added helper methods for API layer ---
    def get_order(self, side: str, order_id: int) -> dict[str, Any]:
        """Return single order data as dict or raise."""
        self._validate_side(side)
        tree = self._get_order_tree(side)
        if not tree.order_exists(order_id):
            raise OrderNotFoundError(f"Order {order_id} not found on side {side}")
        return tree.get_order(order_id).to_dict()  # type: ignore[return-value]

    def list_orders(self, side: str) -> list[dict[str, Any]]:
        """Return all orders for the side ordered by price then time."""
        self._validate_side(side)
        tree = self._get_order_tree(side)
        # Iterate prices (sorted) then each order list
        results: list[dict[str, Any]] = []
        for price in tree.prices:
            order_list = tree.get_price_list(price)
            for order in order_list:
                results.append(order.to_dict())
        return results

    def summary(self) -> dict[str, Any]:
        return {
            "best_bid": self.get_best_bid(),
            "best_ask": self.get_best_ask(),
            "bid_volume": self.bids.volume,
            "ask_volume": self.asks.volume,
            "time": self.time,
        }

    def get_volume_at_price(self, side: str, price: float) -> Decimal:
        self._validate_side(side)

        # price = Decimal(str(price))
        order_tree = self._get_order_tree(side)

        if order_tree.price_exists(price):
            return order_tree.get_price_list(price).volume
        return Decimal(0)

    def get_best_bid(self) -> Optional[Decimal]:
        return self.bids.max_price()

    def get_worst_bid(self) -> Optional[Decimal]:
        return self.bids.min_price()

    def get_best_ask(self) -> Optional[Decimal]:
        return self.asks.min_price()

    def get_worst_ask(self) -> Optional[Decimal]:
        return self.asks.max_price()

    @staticmethod
    def _validate_order(data: dict[str, Any]) -> None:
        if data["quantity"] <= 0:
            raise QuantityError(f"Order quantity must be > 0, got: {data['quantity']}")

        if data["type"] not in VALID_ORDER_TYPES:
            raise OrderTypeError(
                f"Order type must be one of {VALID_ORDER_TYPES}, got: {data['type']}"
            )

    @staticmethod
    def _validate_side(side: str) -> None:
        if side not in VALID_SIDES:
            raise OrderTypeError(f"Side must be one of {VALID_SIDES}, got: {side}")

    @staticmethod
    def _prepare_quote_types(quote: dict[str, Any]) -> None:
        quote["quantity"] = Decimal(str(quote["quantity"]))
        if quote["type"] == ORDER_TYPE_LIMIT:
            if quote.get("price") is None:
                raise OrderTypeError("Price is required for limit orders")
            quote["price"] = Decimal(str(quote["price"]))

    def _update_timestamp(self, data: dict[str, Any], from_data: bool) -> None:
        if from_data:
            self.time = data["timestamp"]
        else:
            self.update_time()
            data["timestamp"] = self.time

    def _update_time_if_needed(self, time: Optional[int]) -> None:
        if time:
            self.time = time
        else:
            self.update_time()

    def _get_order_tree(self, side: str) -> OrderTree:
        return self.bids if side == SIDE_BID else self.asks

    @staticmethod
    def _get_opposite_side(side: str) -> str:
        return SIDE_ASK if side == SIDE_BID else SIDE_BID

    def _execute_market_order_against_asks(
        self, data: dict[str, Any], quantity_to_trade: Decimal, verbose: bool
    ) -> list[dict[str, Any]]:
        trades = []
        while quantity_to_trade > 0 and self.asks:
            best_price_asks = self.asks.min_price_list()
            quantity_to_trade, new_trades = self._process_order_list(
                SIDE_ASK, best_price_asks, quantity_to_trade, data, verbose
            )
            trades.extend(new_trades)
        return trades

    def _execute_market_order_against_bids(
        self, data: dict[str, Any], quantity_to_trade: Decimal, verbose: bool
    ) -> list[dict[str, Any]]:
        trades = []
        while quantity_to_trade > 0 and self.bids:
            best_price_bids = self.bids.max_price_list()
            quantity_to_trade, new_trades = self._process_order_list(
                SIDE_BID, best_price_bids, quantity_to_trade, data, verbose
            )
            trades.extend(new_trades)
        return trades

    def _match_bid_order(
        self,
        data: dict[str, Any],
        price: Decimal,
        quantity_to_trade: Decimal,
        verbose: bool,
    ) -> tuple[Decimal, list[dict[str, Any]]]:
        trades = []
        while self.asks and price >= self.asks.min_price() and quantity_to_trade > 0:
            best_price_asks = self.asks.min_price_list()
            quantity_to_trade, new_trades = self._process_order_list(
                SIDE_ASK, best_price_asks, quantity_to_trade, data, verbose
            )
            trades.extend(new_trades)
        return quantity_to_trade, trades

    def _match_ask_order(
        self,
        data: dict[str, Any],
        price: Decimal,
        quantity_to_trade: Decimal,
        verbose: bool,
    ) -> tuple[Decimal, list[dict[str, Any]]]:
        trades = []
        while self.bids and price <= self.bids.max_price() and quantity_to_trade > 0:
            best_price_bids = self.bids.max_price_list()
            quantity_to_trade, new_trades = self._process_order_list(
                SIDE_BID, best_price_bids, quantity_to_trade, data, verbose
            )
            trades.extend(new_trades)
        return quantity_to_trade, trades

    def _add_remaining_to_book(
        self,
        data: dict[str, Any],
        quantity_to_trade: Decimal,
        side: str,
        from_data: bool,
    ) -> Optional[dict[str, Any]]:
        if quantity_to_trade <= 0:
            return None

        if not from_data:
            data["order_id"] = self.next_order_id

        data["quantity"] = quantity_to_trade
        order_tree = self._get_order_tree(side)
        order_tree.insert_order(data)

        return data

    def _process_order_list(
        self,
        side: Side,
        order_list: Any,
        quantity_still_to_trade: Decimal,
        data: dict[str, Any],
        verbose: bool,
    ) -> tuple[Decimal, list[dict[str, Any]]]:
        trades = []
        quantity_to_trade = quantity_still_to_trade

        while len(order_list) > 0 and quantity_to_trade > 0:
            head_order = order_list.get_head_order()
            traded_quantity, new_book_quantity = self._calculate_trade_quantities(
                quantity_to_trade, head_order
            )

            self._update_or_remove_order(side, head_order, new_book_quantity)

            transaction = self._create_transaction_record(
                head_order, traded_quantity, new_book_quantity, side, data
            )

            self._record_trade(transaction, side, verbose)
            trades.append(transaction)

            quantity_to_trade -= traded_quantity

        return quantity_to_trade, trades

    @staticmethod
    def _calculate_trade_quantities(
        quantity_to_trade: Decimal, head_order: Any
    ) -> tuple[Decimal, Optional[Decimal]]:
        if quantity_to_trade < head_order.quantity:
            return quantity_to_trade, head_order.quantity - quantity_to_trade
        return min(quantity_to_trade, head_order.quantity), None

    def _update_or_remove_order(
        self,
        side: str,
        head_order: Any,
        new_book_quantity: Optional[Decimal],
    ) -> None:
        order_tree = self._get_order_tree(side)
        if new_book_quantity is not None:
            old_qty = head_order.quantity
            head_order.update_quantity(new_book_quantity, head_order.timestamp)
            # Adjust global tree volume by the traded amount
            order_tree._volume -= old_qty - new_book_quantity  # type: ignore[attr-defined]
        else:
            order_tree.remove_order_by_id(head_order.order_id)

    def _create_transaction_record(
        self,
        head_order: Any,
        traded_quantity: Decimal,
        new_book_quantity: Optional[Decimal],
        side: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "timestamp": self.time,
            "price": head_order.price,
            "quantity": traded_quantity,
            "time": self.time,
            "party1": {
                "trade_id": head_order.trade_id,
                "side": side,
                "order_id": head_order.order_id,
                "new_book_quantity": new_book_quantity,
                "wage": head_order.wage,
            },
            "party2": {
                "trade_id": data.get("trade_id", str(data["order_id"])),
                "side": self._get_opposite_side(side),
                "order_id": data["order_id"],
                "new_book_quantity": None,
                "wage": data.get("wage"),
            },
        }

    def _record_trade(
        self, transaction: dict[str, Any], side: Side, verbose: bool
    ) -> None:
        self.trade_df.append(transaction["price"], transaction["quantity"], side)

        if verbose:
            print(
                f"TRADE: Time - {self.time}, Price - {transaction['price']}, "
                f"Quantity - {transaction['quantity']}, "
                f"TradeID - {transaction['party1']['trade_id']}, "
                f"Matching TradeID - {transaction['party2']['trade_id']}"
            )
