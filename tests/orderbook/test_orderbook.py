"""
Comprehensive test suite for the OrderBook class.

Tests cover:
- OrderBook initialization with various configurations
- Process limit orders (full fill, partial fill, resting orders)
- Process market orders (with/without liquidity)
- Order cancellation (valid and invalid scenarios)
- Order modification (price/quantity changes, priority changes)
- Order retrieval and listing
- Book summary and statistics
- Volume calculations at different price levels
- Best/worst bid/ask price queries
- Edge cases and error conditions
- Time management
- Trade recording
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from src.orderbook.orderbook import (
    OrderBook,
    SIDE_BID,
    SIDE_ASK,
    ORDER_TYPE_LIMIT,
    ORDER_TYPE_MARKET,
    DEFAULT_TICK_SIZE,
)
from src.exceptions import OrderNotFoundError, OrderTypeError, QuantityError


# Helper functions for creating orders
def make_limit_order(
    book: OrderBook, side: str, qty: str, price: str, trade_id: str, verbose: bool = False
):
    """Helper to process a limit order."""
    data = {
        "side": side,
        "type": ORDER_TYPE_LIMIT,
        "quantity": qty,
        "price": price,
        "trade_id": trade_id,
    }
    return book.process_order(data, from_data=False, verbose=verbose)


def make_market_order(book: OrderBook, side: str, qty: str, trade_id: str, verbose: bool = False):
    """Helper to process a market order."""
    data = {
        "side": side,
        "type": ORDER_TYPE_MARKET,
        "quantity": qty,
        "trade_id": trade_id,
    }
    trades, order = book.process_order(data, from_data=False, verbose=verbose)
    return trades


class TestOrderBookInitialization:
    """Test OrderBook initialization scenarios."""

    def test_default_initialization(self):
        """Test creating an OrderBook with default parameters."""
        book = OrderBook()
        
        assert book.tick_size == DEFAULT_TICK_SIZE
        assert book.market_name == "UNKNOWN/PAIR"
        assert book.time == 0
        assert book.next_order_id == 0
        assert book.last_tick is None
        assert book.last_timestamp == 0
        assert book.is_closed is False
        assert book.closed_reason is None
        assert book.bids is not None
        assert book.asks is not None
        assert book.trade_df is not None

    def test_initialization_with_custom_tick_size(self):
        """Test creating an OrderBook with custom tick size."""
        book = OrderBook(tick_size=0.01)
        
        assert book.tick_size == 0.01

    def test_initialization_with_market_name(self):
        """Test creating an OrderBook with custom market name."""
        book = OrderBook(market_name="BTC/USD")
        
        assert book.market_name == "BTC/USD"

    def test_initialization_with_all_parameters(self):
        """Test creating an OrderBook with all parameters specified."""
        book = OrderBook(tick_size=0.001, market_name="ETH/USD")
        
        assert book.tick_size == 0.001
        assert book.market_name == "ETH/USD"


class TestTimeManagement:
    """Test time-related functionality."""

    def test_update_time(self):
        """Test that update_time increments the time counter."""
        book = OrderBook()
        initial_time = book.time
        
        book.update_time()
        assert book.time == initial_time + 1
        
        book.update_time()
        assert book.time == initial_time + 2

    def test_time_increments_on_order_processing(self):
        """Test that time increments when processing orders."""
        book = OrderBook()
        assert book.time == 0
        
        make_limit_order(book, SIDE_BID, "10", "100", "B1")
        assert book.time == 1
        
        make_limit_order(book, SIDE_ASK, "5", "101", "A1")
        assert book.time == 2

    def test_time_from_data_mode(self):
        """Test that time is set from data when from_data=True."""
        book = OrderBook()
        data = {
            "side": SIDE_BID,
            "type": ORDER_TYPE_LIMIT,
            "quantity": "10",
            "price": "100",
            "trade_id": "B1",
            "timestamp": 12345,
            "order_id": 999,
        }
        
        book.process_order(data, from_data=True, verbose=False)
        assert book.time == 12345


class TestLimitOrderProcessing:
    """Test limit order processing scenarios."""

    def test_limit_order_rests_on_empty_book(self):
        """Test that a limit order rests when there's no matching order."""
        book = OrderBook()
        
        trades, order = make_limit_order(book, SIDE_BID, "10", "100", "B1")
        
        assert len(trades) == 0
        assert order is not None
        assert order["quantity"] == Decimal("10")
        assert order["price"] == Decimal("100")
        assert book.bids.volume == Decimal("10")
        assert book.asks.volume == Decimal("0")

    def test_limit_order_full_fill_immediate(self):
        """Test limit order that fully fills immediately."""
        book = OrderBook()
        make_limit_order(book, SIDE_ASK, "5", "100", "A1")
        
        trades, order = make_limit_order(book, SIDE_BID, "5", "101", "B1")
        
        assert order is None  # Fully consumed
        assert len(trades) == 1
        assert trades[0]["quantity"] == Decimal("5")
        assert trades[0]["price"] == Decimal("100")
        assert trades[0]["party1"]["side"] == SIDE_ASK
        assert trades[0]["party2"]["side"] == SIDE_BID
        assert book.asks.volume == Decimal("0")
        assert book.bids.volume == Decimal("0")

    def test_limit_order_partial_fill_of_resting(self):
        """Test limit order that partially fills a resting order."""
        book = OrderBook()
        make_limit_order(book, SIDE_ASK, "10", "100", "A1")
        
        trades, order = make_limit_order(book, SIDE_BID, "4", "101", "B1")
        
        assert order is None
        assert len(trades) == 1
        assert trades[0]["quantity"] == Decimal("4")
        assert trades[0]["party1"]["new_book_quantity"] == Decimal("6")
        assert book.asks.volume == Decimal("6")

    def test_limit_order_partial_fill_then_rest(self):
        """Test limit order that partially fills and remainder rests."""
        book = OrderBook()
        make_limit_order(book, SIDE_ASK, "6", "100", "A1")
        
        trades, order = make_limit_order(book, SIDE_BID, "10", "101", "B1")
        
        assert len(trades) == 1
        assert trades[0]["quantity"] == Decimal("6")
        assert order is not None
        assert order["quantity"] == Decimal("4")
        assert book.asks.volume == Decimal("0")
        assert book.bids.volume == Decimal("4")

    def test_limit_order_multiple_matches(self):
        """Test limit order matching against multiple resting orders."""
        book = OrderBook()
        make_limit_order(book, SIDE_ASK, "3", "100", "A1")
        make_limit_order(book, SIDE_ASK, "4", "100", "A2")
        make_limit_order(book, SIDE_ASK, "5", "101", "A3")
        
        trades, order = make_limit_order(book, SIDE_BID, "10", "101", "B1")
        
        assert len(trades) == 3
        assert trades[0]["quantity"] == Decimal("3")
        assert trades[1]["quantity"] == Decimal("4")
        assert trades[2]["quantity"] == Decimal("3")
        assert order is None  # All consumed: 3+4+3=10
        assert book.asks.volume == Decimal("2")  # 5-3=2 remaining

    def test_limit_order_no_match_wrong_price(self):
        """Test limit order that doesn't match due to price."""
        book = OrderBook()
        make_limit_order(book, SIDE_ASK, "5", "105", "A1")
        
        trades, order = make_limit_order(book, SIDE_BID, "5", "100", "B1")
        
        assert len(trades) == 0
        assert order is not None
        assert book.bids.volume == Decimal("5")
        assert book.asks.volume == Decimal("5")

    def test_limit_order_price_improvement(self):
        """Test limit order gets best available price."""
        book = OrderBook()
        make_limit_order(book, SIDE_ASK, "5", "95", "A1")  # Better price
        
        trades, order = make_limit_order(book, SIDE_BID, "5", "100", "B1")
        
        assert len(trades) == 1
        assert trades[0]["price"] == Decimal("95")  # Got better price

    def test_limit_order_with_wage_field(self):
        """Test limit order with wage information."""
        book = OrderBook()
        data = {
            "side": SIDE_BID,
            "type": ORDER_TYPE_LIMIT,
            "quantity": "10",
            "price": "100",
            "trade_id": "B1",
            "wage": {"fee": "0.1%"},
        }
        
        trades, order = book.process_order(data, from_data=False, verbose=False)
        
        assert order is not None
        assert order["wage"] == {"fee": "0.1%"}

    def test_ask_limit_order_matches_bids(self):
        """Test ask limit order matching against bid orders."""
        book = OrderBook()
        make_limit_order(book, SIDE_BID, "5", "100", "B1")
        
        trades, order = make_limit_order(book, SIDE_ASK, "5", "99", "A1")
        
        assert len(trades) == 1
        assert trades[0]["price"] == Decimal("100")
        assert trades[0]["party1"]["side"] == SIDE_BID
        assert trades[0]["party2"]["side"] == SIDE_ASK


class TestMarketOrderProcessing:
    """Test market order processing scenarios."""

    def test_market_order_no_liquidity(self):
        """Test market order when there's no liquidity."""
        book = OrderBook()
        
        trades = make_market_order(book, SIDE_BID, "5", "M1")
        
        assert len(trades) == 0
        assert book.bids.volume == Decimal("0")
        assert book.asks.volume == Decimal("0")

    def test_market_order_full_fill(self):
        """Test market order that fully fills."""
        book = OrderBook()
        make_limit_order(book, SIDE_ASK, "10", "100", "A1")
        
        trades = make_market_order(book, SIDE_BID, "5", "M1")
        
        assert len(trades) == 1
        assert trades[0]["quantity"] == Decimal("5")
        assert book.asks.volume == Decimal("5")

    def test_market_order_partial_liquidity(self):
        """Test market order with insufficient liquidity."""
        book = OrderBook()
        make_limit_order(book, SIDE_ASK, "3", "100", "A1")
        
        trades = make_market_order(book, SIDE_BID, "10", "M1")
        
        assert len(trades) == 1
        assert trades[0]["quantity"] == Decimal("3")
        assert book.asks.volume == Decimal("0")

    def test_market_order_multiple_price_levels(self):
        """Test market order consuming multiple price levels."""
        book = OrderBook()
        make_limit_order(book, SIDE_ASK, "5", "100", "A1")
        make_limit_order(book, SIDE_ASK, "5", "101", "A2")
        make_limit_order(book, SIDE_ASK, "5", "102", "A3")
        
        trades = make_market_order(book, SIDE_BID, "12", "M1")
        
        assert len(trades) == 3
        assert trades[0]["price"] == Decimal("100")
        assert trades[1]["price"] == Decimal("101")
        assert trades[2]["price"] == Decimal("102")
        assert trades[0]["quantity"] == Decimal("5")
        assert trades[1]["quantity"] == Decimal("5")
        assert trades[2]["quantity"] == Decimal("2")

    def test_market_sell_order(self):
        """Test market sell order against bids."""
        book = OrderBook()
        make_limit_order(book, SIDE_BID, "10", "100", "B1")
        
        trades = make_market_order(book, SIDE_ASK, "5", "M1")
        
        assert len(trades) == 1
        assert trades[0]["quantity"] == Decimal("5")
        assert book.bids.volume == Decimal("5")


class TestOrderCancellation:
    """Test order cancellation functionality."""

    def test_cancel_existing_bid_order(self):
        """Test cancelling an existing bid order."""
        book = OrderBook()
        trades, order = make_limit_order(book, SIDE_BID, "10", "100", "B1")
        order_id = order["order_id"]
        
        book.cancel_order(SIDE_BID, order_id)
        
        assert book.bids.volume == Decimal("0")
        assert not book.bids.order_exists(order_id)

    def test_cancel_existing_ask_order(self):
        """Test cancelling an existing ask order."""
        book = OrderBook()
        trades, order = make_limit_order(book, SIDE_ASK, "5", "100", "A1")
        order_id = order["order_id"]
        
        book.cancel_order(SIDE_ASK, order_id)
        
        assert book.asks.volume == Decimal("0")
        assert not book.asks.order_exists(order_id)

    def test_cancel_nonexistent_order(self):
        """Test cancelling an order that doesn't exist."""
        book = OrderBook()
        
        with pytest.raises(OrderNotFoundError) as exc_info:
            book.cancel_order(SIDE_BID, 999)
        
        assert "Order with id: 999 and side: bid not found" in str(exc_info.value)

    def test_cancel_order_wrong_side(self):
        """Test cancelling an order on the wrong side."""
        book = OrderBook()
        trades, order = make_limit_order(book, SIDE_BID, "10", "100", "B1")
        order_id = order["order_id"]
        
        with pytest.raises(OrderNotFoundError):
            book.cancel_order(SIDE_ASK, order_id)

    def test_cancel_order_with_custom_time(self):
        """Test cancelling an order with custom timestamp."""
        book = OrderBook()
        trades, order = make_limit_order(book, SIDE_BID, "10", "100", "B1")
        order_id = order["order_id"]
        
        book.cancel_order(SIDE_BID, order_id, time=5000)
        
        assert book.time == 5000

    def test_cancel_order_from_middle_of_list(self):
        """Test cancelling an order from the middle of order list."""
        book = OrderBook()
        trades, order1 = make_limit_order(book, SIDE_BID, "5", "100", "B1")
        trades, order2 = make_limit_order(book, SIDE_BID, "5", "100", "B2")
        trades, order3 = make_limit_order(book, SIDE_BID, "5", "100", "B3")
        
        book.cancel_order(SIDE_BID, order2["order_id"])
        
        assert book.bids.volume == Decimal("10")
        assert book.bids.num_orders == 2


class TestOrderModification:
    """Test order modification functionality."""

    def test_modify_order_quantity_increase(self):
        """Test modifying order with quantity increase."""
        book = OrderBook()
        trades, order = make_limit_order(book, SIDE_BID, "5", "100", "B1")
        order_id = order["order_id"]
        
        book.modify_order(order_id, {"side": SIDE_BID, "quantity": "10", "price": "100"})
        
        assert book.bids.volume == Decimal("10")

    def test_modify_order_quantity_decrease(self):
        """Test modifying order with quantity decrease."""
        book = OrderBook()
        trades, order = make_limit_order(book, SIDE_BID, "10", "100", "B1")
        order_id = order["order_id"]
        
        book.modify_order(order_id, {"side": SIDE_BID, "quantity": "5", "price": "100"})
        
        assert book.bids.volume == Decimal("5")

    def test_modify_order_price_change(self):
        """Test modifying order with price change."""
        book = OrderBook()
        trades, order = make_limit_order(book, SIDE_BID, "5", "100", "B1")
        order_id = order["order_id"]
        
        book.modify_order(order_id, {"side": SIDE_BID, "quantity": "5", "price": "101"})
        
        assert not book.bids.price_exists(Decimal("100"))
        assert book.bids.price_exists(Decimal("101"))

    def test_modify_order_loses_priority_on_price_change(self):
        """Test that modifying price loses time priority."""
        book = OrderBook()
        trades, order1 = make_limit_order(book, SIDE_BID, "5", "100", "B1")
        trades, order2 = make_limit_order(book, SIDE_BID, "5", "100", "B2")
        
        book.modify_order(order1["order_id"], {"side": SIDE_BID, "quantity": "5", "price": "101"})
        
        price_list = book.bids.get_price_list(Decimal("100"))
        assert price_list.get_head_order().order_id == order2["order_id"]

    def test_modify_order_quantity_increase_moves_to_tail(self):
        """Test that increasing quantity moves order to tail."""
        book = OrderBook()
        trades, order1 = make_limit_order(book, SIDE_BID, "2", "100", "B1")
        trades, order2 = make_limit_order(book, SIDE_BID, "2", "100", "B2")
        
        price_list = book.bids.get_price_list(Decimal("100"))
        assert price_list.head_order.order_id == order1["order_id"]
        
        book.modify_order(order1["order_id"], {"side": SIDE_BID, "quantity": "5", "price": "100"})
        
        assert price_list.tail_order.order_id == order1["order_id"]
        assert price_list.head_order.order_id == order2["order_id"]

    def test_modify_nonexistent_order(self):
        """Test modifying an order that doesn't exist."""
        book = OrderBook()
        
        with pytest.raises(OrderNotFoundError):
            book.modify_order(999, {"side": SIDE_BID, "quantity": "5", "price": "100"})

    def test_modify_order_with_custom_time(self):
        """Test modifying order with custom timestamp."""
        book = OrderBook()
        trades, order = make_limit_order(book, SIDE_BID, "5", "100", "B1")
        
        book.modify_order(order["order_id"], {"side": SIDE_BID, "quantity": "10", "price": "100"}, time=5000)
        
        assert book.time == 5000


class TestOrderRetrieval:
    """Test order retrieval and listing functionality."""

    def test_get_order_existing(self):
        """Test retrieving an existing order."""
        book = OrderBook()
        trades, order = make_limit_order(book, SIDE_BID, "10", "100", "B1")
        order_id = order["order_id"]
        
        retrieved = book.get_order(SIDE_BID, order_id)
        
        assert retrieved["order_id"] == order_id
        assert retrieved["quantity"] == "10"
        assert retrieved["price"] == "100"

    def test_get_order_nonexistent(self):
        """Test retrieving a non-existent order."""
        book = OrderBook()
        
        with pytest.raises(OrderNotFoundError):
            book.get_order(SIDE_BID, 999)

    def test_list_orders_empty_book(self):
        """Test listing orders on empty book."""
        book = OrderBook()
        
        orders = book.list_orders(SIDE_BID)
        
        assert len(orders) == 0

    def test_list_orders_single_price_level(self):
        """Test listing orders at single price level."""
        book = OrderBook()
        make_limit_order(book, SIDE_BID, "5", "100", "B1")
        make_limit_order(book, SIDE_BID, "3", "100", "B2")
        
        orders = book.list_orders(SIDE_BID)
        
        assert len(orders) == 2
        assert orders[0]["quantity"] == "5"
        assert orders[1]["quantity"] == "3"

    def test_list_orders_multiple_price_levels(self):
        """Test listing orders across multiple price levels."""
        book = OrderBook()
        make_limit_order(book, SIDE_BID, "5", "100", "B1")
        make_limit_order(book, SIDE_BID, "3", "101", "B2")
        make_limit_order(book, SIDE_BID, "2", "99", "B3")
        
        orders = book.list_orders(SIDE_BID)
        
        assert len(orders) == 3
        # Should be sorted by price
        assert orders[0]["price"] == "99"
        assert orders[1]["price"] == "100"
        assert orders[2]["price"] == "101"

    def test_list_orders_asks(self):
        """Test listing ask orders."""
        book = OrderBook()
        make_limit_order(book, SIDE_ASK, "5", "100", "A1")
        make_limit_order(book, SIDE_ASK, "3", "101", "A2")
        
        orders = book.list_orders(SIDE_ASK)
        
        assert len(orders) == 2


class TestBookSummary:
    """Test order book summary functionality."""

    def test_summary_empty_book(self):
        """Test summary on empty book."""
        book = OrderBook()
        
        summary = book.summary()
        
        assert summary["best_bid"] is None
        assert summary["best_ask"] is None
        assert summary["bid_volume"] == 0
        assert summary["ask_volume"] == 0
        assert summary["time"] == 0

    def test_summary_with_orders(self):
        """Test summary with orders."""
        book = OrderBook()
        make_limit_order(book, SIDE_BID, "10", "99", "B1")
        make_limit_order(book, SIDE_BID, "5", "98", "B2")
        make_limit_order(book, SIDE_ASK, "8", "101", "A1")
        make_limit_order(book, SIDE_ASK, "3", "102", "A2")
        
        summary = book.summary()
        
        assert summary["best_bid"] == Decimal("99")
        assert summary["best_ask"] == Decimal("101")
        assert summary["bid_volume"] == Decimal("15")
        assert summary["ask_volume"] == Decimal("11")

    def test_summary_after_trades(self):
        """Test summary after trades have occurred."""
        book = OrderBook()
        make_limit_order(book, SIDE_ASK, "10", "100", "A1")
        make_limit_order(book, SIDE_BID, "5", "100", "B1")
        
        summary = book.summary()
        
        assert summary["ask_volume"] == Decimal("5")
        assert summary["bid_volume"] == Decimal("0")


class TestVolumeQueries:
    """Test volume-related queries."""

    def test_get_volume_at_price_no_orders(self):
        """Test volume at price with no orders."""
        book = OrderBook()
        
        volume = book.get_volume_at_price(SIDE_BID, 100.0)
        
        assert volume == Decimal("0")

    def test_get_volume_at_price_with_orders(self):
        """Test volume at price with orders."""
        book = OrderBook()
        make_limit_order(book, SIDE_BID, "5", "100", "B1")
        make_limit_order(book, SIDE_BID, "3", "100", "B2")
        
        volume = book.get_volume_at_price(SIDE_BID, 100.0)
        
        assert volume == Decimal("8")

    def test_get_volume_at_price_different_level(self):
        """Test volume at non-existent price level."""
        book = OrderBook()
        make_limit_order(book, SIDE_BID, "5", "100", "B1")
        
        volume = book.get_volume_at_price(SIDE_BID, 99.0)
        
        assert volume == Decimal("0")

    def test_get_volume_at_price_after_partial_fill(self):
        """Test volume at price after partial fill."""
        book = OrderBook()
        make_limit_order(book, SIDE_ASK, "10", "100", "A1")
        make_limit_order(book, SIDE_BID, "4", "100", "B1")
        
        volume = book.get_volume_at_price(SIDE_ASK, 100.0)
        
        assert volume == Decimal("6")


class TestBestAndWorstPrices:
    """Test best/worst price queries."""

    def test_get_best_bid_empty_book(self):
        """Test best bid on empty book."""
        book = OrderBook()
        
        assert book.get_best_bid() is None

    def test_get_best_bid_with_orders(self):
        """Test best bid with orders."""
        book = OrderBook()
        make_limit_order(book, SIDE_BID, "5", "100", "B1")
        make_limit_order(book, SIDE_BID, "3", "99", "B2")
        make_limit_order(book, SIDE_BID, "2", "101", "B3")
        
        assert book.get_best_bid() == Decimal("101")

    def test_get_worst_bid_empty_book(self):
        """Test worst bid on empty book."""
        book = OrderBook()
        
        assert book.get_worst_bid() is None

    def test_get_worst_bid_with_orders(self):
        """Test worst bid with orders."""
        book = OrderBook()
        make_limit_order(book, SIDE_BID, "5", "100", "B1")
        make_limit_order(book, SIDE_BID, "3", "99", "B2")
        make_limit_order(book, SIDE_BID, "2", "101", "B3")
        
        assert book.get_worst_bid() == Decimal("99")

    def test_get_best_ask_empty_book(self):
        """Test best ask on empty book."""
        book = OrderBook()
        
        assert book.get_best_ask() is None

    def test_get_best_ask_with_orders(self):
        """Test best ask with orders."""
        book = OrderBook()
        make_limit_order(book, SIDE_ASK, "5", "100", "A1")
        make_limit_order(book, SIDE_ASK, "3", "99", "A2")
        make_limit_order(book, SIDE_ASK, "2", "101", "A3")
        
        assert book.get_best_ask() == Decimal("99")

    def test_get_worst_ask_empty_book(self):
        """Test worst ask on empty book."""
        book = OrderBook()
        
        assert book.get_worst_ask() is None

    def test_get_worst_ask_with_orders(self):
        """Test worst ask with orders."""
        book = OrderBook()
        make_limit_order(book, SIDE_ASK, "5", "100", "A1")
        make_limit_order(book, SIDE_ASK, "3", "99", "A2")
        make_limit_order(book, SIDE_ASK, "2", "101", "A3")
        
        assert book.get_worst_ask() == Decimal("101")


class TestValidation:
    """Test order validation and error handling."""

    def test_invalid_side_process_order(self):
        """Test processing order with invalid side."""
        book = OrderBook()
        data = {
            "side": "invalid",
            "type": ORDER_TYPE_LIMIT,
            "quantity": "10",
            "price": "100",
            "trade_id": "X1",
        }
        
        with pytest.raises(OrderTypeError):
            book.process_order(data, from_data=False, verbose=False)

    def test_invalid_order_type(self):
        """Test processing order with invalid type."""
        book = OrderBook()
        data = {
            "side": SIDE_BID,
            "type": "invalid_type",
            "quantity": "10",
            "price": "100",
            "trade_id": "X1",
        }
        
        with pytest.raises(OrderTypeError):
            book.process_order(data, from_data=False, verbose=False)

    def test_zero_quantity(self):
        """Test processing order with zero quantity."""
        book = OrderBook()
        data = {
            "side": SIDE_BID,
            "type": ORDER_TYPE_LIMIT,
            "quantity": "0",
            "price": "100",
            "trade_id": "X1",
        }
        
        with pytest.raises(QuantityError):
            book.process_order(data, from_data=False, verbose=False)

    def test_negative_quantity(self):
        """Test processing order with negative quantity."""
        book = OrderBook()
        data = {
            "side": SIDE_BID,
            "type": ORDER_TYPE_LIMIT,
            "quantity": "-5",
            "price": "100",
            "trade_id": "X1",
        }
        
        with pytest.raises(QuantityError):
            book.process_order(data, from_data=False, verbose=False)

    def test_invalid_side_cancel_order(self):
        """Test cancelling order with invalid side."""
        book = OrderBook()
        
        with pytest.raises(OrderTypeError):
            book.cancel_order("invalid", 1)

    def test_invalid_side_modify_order(self):
        """Test modifying order with invalid side."""
        book = OrderBook()
        
        with pytest.raises(OrderTypeError):
            book.modify_order(1, {"side": "invalid", "quantity": "10", "price": "100"})

    def test_invalid_side_get_order(self):
        """Test getting order with invalid side."""
        book = OrderBook()
        
        with pytest.raises(OrderTypeError):
            book.get_order("invalid", 1)

    def test_invalid_side_list_orders(self):
        """Test listing orders with invalid side."""
        book = OrderBook()
        
        with pytest.raises(OrderTypeError):
            book.list_orders("invalid")

    def test_invalid_side_get_volume(self):
        """Test getting volume with invalid side."""
        book = OrderBook()
        
        with pytest.raises(OrderTypeError):
            book.get_volume_at_price("invalid", 100.0)


class TestTradeRecording:
    """Test trade recording functionality."""

    def test_trade_recorded_on_match(self):
        """Test that trades are recorded when orders match."""
        book = OrderBook()
        make_limit_order(book, SIDE_ASK, "5", "100", "A1")
        
        with patch.object(book.trade_df, 'append') as mock_append:
            make_limit_order(book, SIDE_BID, "5", "100", "B1")
            
            mock_append.assert_called_once()
            args = mock_append.call_args[0]
            assert args[0] == Decimal("100")  # price
            assert args[1] == Decimal("5")    # quantity
            assert args[2] == SIDE_ASK        # side

    def test_verbose_mode_prints_trade(self):
        """Test that verbose mode prints trade information."""
        book = OrderBook()
        make_limit_order(book, SIDE_ASK, "5", "100", "A1")
        
        with patch('builtins.print') as mock_print:
            make_limit_order(book, SIDE_BID, "5", "100", "B1", verbose=True)
            
            mock_print.assert_called()
            call_args = str(mock_print.call_args)
            assert "TRADE" in call_args
            assert "100" in call_args  # price


class TestEdgeCases:
    """Test edge cases and corner scenarios."""

    def test_order_id_auto_increment(self):
        """Test that order IDs are auto-incremented."""
        book = OrderBook()
        
        _, order1 = make_limit_order(book, SIDE_BID, "5", "100", "B1")
        _, order2 = make_limit_order(book, SIDE_BID, "5", "100", "B2")
        _, order3 = make_limit_order(book, SIDE_BID, "5", "100", "B3")
        
        assert order1["order_id"] == 1
        assert order2["order_id"] == 2
        assert order3["order_id"] == 3

    def test_order_id_provided_when_from_data(self):
        """Test that order ID is used from data when from_data=True."""
        book = OrderBook()
        data = {
            "side": SIDE_BID,
            "type": ORDER_TYPE_LIMIT,
            "quantity": "10",
            "price": "100",
            "trade_id": "B1",
            "timestamp": 1000,
            "order_id": 999,
        }
        
        _, order = book.process_order(data, from_data=True, verbose=False)
        
        assert order["order_id"] == 999

    def test_very_small_quantities(self):
        """Test handling very small decimal quantities."""
        book = OrderBook()
        make_limit_order(book, SIDE_ASK, "0.00001", "100", "A1")
        
        trades, order = make_limit_order(book, SIDE_BID, "0.00001", "100", "B1")
        
        assert len(trades) == 1
        assert trades[0]["quantity"] == Decimal("0.00001")

    def test_very_large_quantities(self):
        """Test handling very large quantities."""
        book = OrderBook()
        make_limit_order(book, SIDE_ASK, "999999999", "100", "A1")
        
        trades, order = make_limit_order(book, SIDE_BID, "999999999", "100", "B1")
        
        assert len(trades) == 1
        assert trades[0]["quantity"] == Decimal("999999999")

    def test_decimal_precision(self):
        """Test that decimal precision is maintained."""
        book = OrderBook()
        make_limit_order(book, SIDE_ASK, "3.333333", "100.12345", "A1")
        
        orders = book.list_orders(SIDE_ASK)
        
        assert orders[0]["quantity"] == "3.333333"
        assert orders[0]["price"] == "100.12345"

    def test_multiple_orders_same_price_time_priority(self):
        """Test that orders at same price maintain time priority."""
        book = OrderBook()
        _, order1 = make_limit_order(book, SIDE_BID, "5", "100", "B1")
        _, order2 = make_limit_order(book, SIDE_BID, "3", "100", "B2")
        _, order3 = make_limit_order(book, SIDE_BID, "2", "100", "B3")
        
        # Consume orders and verify time priority
        make_limit_order(book, SIDE_ASK, "1", "100", "A1")
        
        orders = book.list_orders(SIDE_BID)
        # First order should have been partially filled
        assert orders[0]["order_id"] == order1["order_id"]
        assert orders[0]["quantity"] == "4"

    def test_empty_book_operations(self):
        """Test various operations on empty book."""
        book = OrderBook()
        
        assert book.get_best_bid() is None
        assert book.get_best_ask() is None
        assert book.get_worst_bid() is None
        assert book.get_worst_ask() is None
        assert book.list_orders(SIDE_BID) == []
        assert book.list_orders(SIDE_ASK) == []
        assert book.bids.volume == 0
        assert book.asks.volume == 0

    def test_cross_order_exhausts_multiple_levels(self):
        """Test crossing order that exhausts multiple price levels."""
        book = OrderBook()
        make_limit_order(book, SIDE_ASK, "2", "100", "A1")
        make_limit_order(book, SIDE_ASK, "3", "101", "A2")
        make_limit_order(book, SIDE_ASK, "4", "102", "A3")
        
        trades, order = make_limit_order(book, SIDE_BID, "20", "105", "B1")
        
        # Should fill all asks and leave remainder
        assert len(trades) == 3
        assert sum(t["quantity"] for t in trades) == Decimal("9")
        assert order is not None
        assert order["quantity"] == Decimal("11")
        assert book.asks.volume == Decimal("0")

    def test_modify_order_to_same_values(self):
        """Test modifying order to same quantity and price."""
        book = OrderBook()
        _, order = make_limit_order(book, SIDE_BID, "10", "100", "B1")
        
        book.modify_order(order["order_id"], {"side": SIDE_BID, "quantity": "10", "price": "100"})
        
        assert book.bids.volume == Decimal("10")
        assert book.bids.order_exists(order["order_id"])

    def test_transaction_record_structure(self):
        """Test that transaction records have correct structure."""
        book = OrderBook()
        make_limit_order(book, SIDE_ASK, "5", "100", "A1")
        
        trades, _ = make_limit_order(book, SIDE_BID, "5", "100", "B1")
        
        trade = trades[0]
        assert "timestamp" in trade
        assert "price" in trade
        assert "quantity" in trade
        assert "time" in trade
        assert "party1" in trade
        assert "party2" in trade
        assert "trade_id" in trade["party1"]
        assert "side" in trade["party1"]
        assert "order_id" in trade["party1"]
        assert "new_book_quantity" in trade["party1"]
        assert "wage" in trade["party1"]

    def test_string_numeric_conversion(self):
        """Test that string numerics are properly converted."""
        book = OrderBook()
        data = {
            "side": SIDE_BID,
            "type": ORDER_TYPE_LIMIT,
            "quantity": "10.5",
            "price": "100.25",
            "trade_id": "B1",
        }
        
        _, order = book.process_order(data, from_data=False, verbose=False)
        
        assert order["quantity"] == Decimal("10.5")
        assert order["price"] == Decimal("100.25")

    def test_integer_numeric_conversion(self):
        """Test that integer numerics are properly converted."""
        book = OrderBook()
        data = {
            "side": SIDE_BID,
            "type": ORDER_TYPE_LIMIT,
            "quantity": 10,
            "price": 100,
            "trade_id": "B1",
        }
        
        _, order = book.process_order(data, from_data=False, verbose=False)
        
        assert order["quantity"] == Decimal("10")
        assert order["price"] == Decimal("100")


class TestComplexScenarios:
    """Test complex multi-step scenarios."""

    def test_full_trading_session(self):
        """Test a full trading session with multiple operations."""
        book = OrderBook(market_name="BTC/USD")
        
        # Place initial orders
        _, order1 = make_limit_order(book, SIDE_BID, "10", "99", "B1")
        _, order2 = make_limit_order(book, SIDE_BID, "5", "98", "B2")
        _, order3 = make_limit_order(book, SIDE_ASK, "8", "101", "A1")
        _, order4 = make_limit_order(book, SIDE_ASK, "3", "102", "A2")
        
        # Execute a crossing trade
        trades, _ = make_limit_order(book, SIDE_BID, "5", "101", "B3")
        assert len(trades) == 1
        
        # Modify an order
        book.modify_order(order1["order_id"], {"side": SIDE_BID, "quantity": "15", "price": "99"})
        
        # Cancel an order
        book.cancel_order(SIDE_BID, order2["order_id"])
        
        # Check final state
        summary = book.summary()
        assert summary["best_bid"] == Decimal("99")
        assert summary["best_ask"] == Decimal("101")

    def test_market_maker_scenario(self):
        """Test a market maker scenario with tight spread."""
        book = OrderBook()
        
        # Market maker places orders
        make_limit_order(book, SIDE_BID, "100", "99.99", "MM_BID_1")
        make_limit_order(book, SIDE_ASK, "100", "100.01", "MM_ASK_1")
        
        # Taker hits the bid
        trades = make_market_order(book, SIDE_ASK, "50", "TAKER_1")
        assert len(trades) == 1
        assert trades[0]["price"] == Decimal("99.99")
        
        # Taker lifts the offer
        trades = make_market_order(book, SIDE_BID, "30", "TAKER_2")
        assert len(trades) == 1
        assert trades[0]["price"] == Decimal("100.01")
        
        # Verify remaining liquidity
        assert book.bids.volume == Decimal("50")
        assert book.asks.volume == Decimal("70")

    def test_iceberg_order_simulation(self):
        """Test simulation of iceberg order behavior."""
        book = OrderBook()
        
        # Place large order split into multiple smaller orders
        for i in range(5):
            make_limit_order(book, SIDE_BID, "20", "100", f"ICEBERG_{i}")
        
        # Execute against iceberg
        trades, _ = make_limit_order(book, SIDE_ASK, "75", "100", "SELLER")
        
        assert len(trades) == 4  # First 3 full (60) + partial 4th (15)
        assert sum(t["quantity"] for t in trades) == Decimal("75")
        assert book.bids.volume == Decimal("25")

    def test_stop_loss_trigger_simulation(self):
        """Test simulation of stop loss execution."""
        book = OrderBook()
        
        # Establish market price
        make_limit_order(book, SIDE_ASK, "10", "100", "A1")
        make_limit_order(book, SIDE_BID, "10", "99", "B1")
        
        # Price drops, simulating stop loss trigger
        trades = make_market_order(book, SIDE_ASK, "10", "STOP_LOSS")
        
        assert len(trades) == 1
        assert trades[0]["price"] == Decimal("99")

    def test_order_book_depth_analysis(self):
        """Test order book depth across multiple levels."""
        book = OrderBook()
        
        # Build depth
        for i in range(10):
            make_limit_order(book, SIDE_BID, "10", str(100 - i), f"B{i}")
            make_limit_order(book, SIDE_ASK, "10", str(101 + i), f"A{i}")
        
        assert book.bids.depth == 10
        assert book.asks.depth == 10
        assert book.bids.volume == Decimal("100")
        assert book.asks.volume == Decimal("100")
        
        # Check spread
        spread = book.get_best_ask() - book.get_best_bid()
        assert spread == Decimal("1")

