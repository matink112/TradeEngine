from decimal import Decimal

from src.orderbook.orderbook import OrderBook, SIDE_BID, SIDE_ASK, ORDER_TYPE_LIMIT, ORDER_TYPE_MARKET
from src.exceptions import OrderNotFoundError


def make_limit(book: OrderBook, side: str, qty: str, price: str, trade_id: str):
    data = {"side": side, "type": ORDER_TYPE_LIMIT, "quantity": qty, "price": price, "trade_id": trade_id}
    trades, order = book.process_order(data, from_data=False, verbose=False)
    return trades, order


def make_market(book: OrderBook, side: str, qty: str, trade_id: str):
    data = {"side": side, "type": ORDER_TYPE_MARKET, "quantity": qty, "trade_id": trade_id}
    trades = book.process_order(data, from_data=False, verbose=False)[0]
    return trades


def test_limit_order_full_fill_immediate():
    book = OrderBook()
    # Resting ask
    make_limit(book, SIDE_ASK, "5", "100", "A1")
    # Aggressing bid crosses and fully fills ask
    data = {"side": SIDE_BID, "type": ORDER_TYPE_LIMIT, "quantity": "5", "price": "101", "trade_id": "B1"}
    trades, order = book.process_order(data, from_data=False, verbose=False)
    assert order is None  # incoming fully consumed (pure taker)
    assert len(trades) == 1
    t = trades[0]
    assert t["party1"]["side"] == SIDE_ASK
    assert t["party2"]["side"] == SIDE_BID
    assert t["party1"]["new_book_quantity"] is None  # resting order fully consumed
    assert book.asks.volume == 0


def test_limit_order_partial_fill_of_resting():
    book = OrderBook()
    make_limit(book, SIDE_ASK, "10", "100", "A1")
    # Incoming bid smaller than resting ask
    data = {"side": SIDE_BID, "type": ORDER_TYPE_LIMIT, "quantity": "4", "price": "101", "trade_id": "B1"}
    trades, order = book.process_order(data, from_data=False, verbose=False)
    assert order is None  # incoming fully matched, no remainder
    assert len(trades) == 1
    t = trades[0]
    assert t["quantity"] == Decimal("4")
    # Resting ask partially remains
    assert t["party1"]["new_book_quantity"] == Decimal("6")
    # Book should show remaining volume 6 on asks side
    assert book.asks.volume == Decimal("6")


def test_limit_order_partial_fill_then_rest():
    book = OrderBook()
    make_limit(book, SIDE_ASK, "6", "100", "A1")
    # Incoming bid larger than resting ask; remainder should rest as bid
    data = {"side": SIDE_BID, "type": ORDER_TYPE_LIMIT, "quantity": "10", "price": "101", "trade_id": "B1"}
    trades, order = book.process_order(data, from_data=False, verbose=False)
    assert len(trades) == 1
    assert order is not None
    assert order["quantity"] == Decimal("4")
    # Ask book emptied
    assert book.asks.volume == 0
    # Bid book now has new resting order quantity 4
    assert book.bids.volume == Decimal("4")


def test_market_order_no_opposite_side():
    book = OrderBook()
    trades = make_market(book, SIDE_ASK, "3", "M1")  # no bids to match
    assert trades == []
    assert book.bids.volume == 0 and book.asks.volume == 0


def test_modify_order_price_change_loses_priority():
    book = OrderBook()
    # Two bid orders same price
    make_limit(book, SIDE_BID, "5", "100", "B1")
    make_limit(book, SIDE_BID, "5", "100", "B2")
    # Modify first order price to new level
    order_id = 1  # first assigned id
    book.modify_order(order_id, {"side": SIDE_BID, "quantity": "5", "price": "101"})
    # Old price level should now only have second order
    assert book.bids.price_exists(Decimal("100"))
    price_list_old = book.bids.get_price_list(Decimal("100"))
    assert len(price_list_old) == 1
    # New price level has modified order
    assert book.bids.price_exists(Decimal("101"))
    price_list_new = book.bids.get_price_list(Decimal("101"))
    assert price_list_new.get_head_order().order_id == order_id


def test_modify_order_quantity_increase_moves_to_tail():
    book = OrderBook()
    make_limit(book, SIDE_BID, "2", "100", "B1")  # id 1 head
    make_limit(book, SIDE_BID, "2", "100", "B2")  # id 2 tail
    price_list = book.bids.get_price_list(Decimal("100"))
    assert price_list.head_order.order_id == 1
    book.modify_order(1, {"side": SIDE_BID, "quantity": "5", "price": "100"})
    # Order 1 should now be tail due to quantity increase
    assert price_list.tail_order.order_id == 1


def test_cancel_order_not_found():
    book = OrderBook()
    try:
        book.cancel_order(SIDE_BID, 999)
    except OrderNotFoundError:
        pass
    else:
        assert False, "Expected OrderNotFoundError"


def test_summary_after_trades():
    book = OrderBook()
    make_limit(book, SIDE_BID, "2", "100", "B1")
    make_limit(book, SIDE_ASK, "3", "105", "A1")
    summary = book.summary()
    assert summary["best_bid"] == Decimal("100")
    assert summary["best_ask"] == Decimal("105")
    assert summary["bid_volume"] == Decimal("2")
    assert summary["ask_volume"] == Decimal("3")


def test_trade_dataframe_ohlc_via_book_trades():
    book = OrderBook()
    # Create crossing orders to generate a trade
    make_limit(book, SIDE_ASK, "1", "100", "A1")
    make_limit(book, SIDE_BID, "1", "100", "B1")  # executes trade
    # DataFrame should now have > initial synthetic trade
    assert len(book.trade_df.df) >= 2
    # Latest price should be 100
    assert book.trade_df.get_short_info()["price"] == 100.0
