from decimal import Decimal
import pandas as pd

from src.orderbook.orderbook import OrderBook, SIDE_BID, SIDE_ASK, ORDER_TYPE_LIMIT


def test_trade_dataframe_initial_synthetic_row_present():
    book = OrderBook()
    # Synthetic initial trade expected
    assert len(book.trade_df.df) == 1
    row = book.trade_df.df.iloc[0]
    assert row['price'] == 0.0 and row['volume'] == 0.0


def test_trade_append_and_latest_price():
    book = OrderBook()
    # Create crossing orders to generate trade at price 100
    book.process_order({'side': SIDE_ASK, 'type': ORDER_TYPE_LIMIT, 'quantity': '1', 'price': '100'}, False, False)
    book.process_order({'side': SIDE_BID, 'type': ORDER_TYPE_LIMIT, 'quantity': '1', 'price': '100'}, False, False)
    assert book.trade_df.get_short_info()['price'] == 100.0
    assert book.trade_df._get_latest_price() == 100.0


def test_trade_get_ohlc_data_handles_empty_range():
    book = OrderBook()
    now = pd.Timestamp.now()
    from_time = now - pd.Timedelta(seconds=1)
    ohlc = book.trade_df.get_ohlc_data(from_time, now + pd.Timedelta(hours=1), '1h')
    # Should return frame with one row (resample fillna(0))
    assert not ohlc.empty
    assert {'open', 'high', 'low', 'close'} <= set(ohlc['price'].columns)


def test_trade_price_change_returns_dash_if_insufficient_data():
    book = OrderBook()
    change = book.trade_df.get_short_info()['1h_change']
    assert change == '-'  # only synthetic row present


def test_trade_get_long_info_open_and_closed_market():
    book = OrderBook()
    open_info = book.trade_df.get_long_info()
    assert open_info['close'] is False
    # Close market and check
    book.is_closed = True
    book.closed_reason = 'MAINT'
    closed_info = book.trade_df.get_long_info()
    assert closed_info['close'] is True and closed_info['reason'] == 'MAINT'


def test_trade_get_last_trades_count():
    book = OrderBook()
    # generate some trades
    for i in range(3):
        book.process_order({'side': SIDE_ASK, 'type': ORDER_TYPE_LIMIT, 'quantity': '1', 'price': str(100 + i)}, False, False)
        book.process_order({'side': SIDE_BID, 'type': ORDER_TYPE_LIMIT, 'quantity': '1', 'price': str(100 + i)}, False, False)
    recent = book.trade_df.get_last_trades(2)
    assert len(recent) == 2
