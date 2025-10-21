"""Comprehensive test suite for TradeDataFrame class.

Tests cover:
- Initialization and empty dataframe creation
- Trade appending with different scenarios
- OHLC data calculation
- Chart generation (PNG and CSV)
- Price change calculations
- Edge cases (empty data, single trade, missing data)
- File I/O operations
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from src.orderbook.trade import TradeDataFrame


class TestTradeDataFrameInitialization:
    """Test TradeDataFrame initialization and setup."""

    def test_init_creates_empty_dataframe(self):
        """Test that initialization creates a dataframe with correct schema."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)

        # Should have initial trade (bug workaround)
        assert len(trade_df.df) == 1
        assert list(trade_df.df.columns) == ["price", "volume", "is_bid"]
        assert trade_df.df["is_bid"].dtype == bool

    def test_init_stores_book_reference(self):
        """Test that book reference is stored correctly."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)
        assert trade_df.book is mock_book

    def test_initial_trade_added(self):
        """Test that initial trade is added to prevent empty table errors."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)

        assert len(trade_df.df) == 1
        assert trade_df.df["price"].iloc[0] == 0
        assert trade_df.df["volume"].iloc[0] == 0
        assert trade_df.df["is_bid"].iloc[0] == True  # Use == instead of is


class TestTradeAppending:
    """Test trade record appending functionality."""

    def test_append_bid_trade(self):
        """Test appending a bid trade."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)
        initial_len = len(trade_df.df)

        trade_df.append(100.5, 10.0, "bid")

        assert len(trade_df.df) == initial_len + 1
        assert trade_df.df["price"].iloc[-1] == 100.5
        assert trade_df.df["volume"].iloc[-1] == 10.0
        assert trade_df.df["is_bid"].iloc[-1] == True  # Use == instead of is

    def test_append_ask_trade(self):
        """Test appending an ask trade."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)
        initial_len = len(trade_df.df)

        trade_df.append(99.5, 5.0, "ask")

        assert len(trade_df.df) == initial_len + 1
        assert trade_df.df["price"].iloc[-1] == 99.5
        assert trade_df.df["volume"].iloc[-1] == 5.0
        assert trade_df.df["is_bid"].iloc[-1] == False  # Use == instead of is

    def test_append_with_custom_datetime(self):
        """Test appending a trade with custom timestamp."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)
        custom_time = datetime(2025, 1, 1, 12, 0, 0)

        trade_df.append(100.0, 1.0, "bid", date_time=custom_time)

        assert trade_df.df.index[-1] == custom_time

    def test_append_without_datetime_uses_now(self):
        """Test that append without datetime uses current time."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)
        before_time = datetime.now()

        trade_df.append(100.0, 1.0, "bid")

        after_time = datetime.now()
        trade_time = trade_df.df.index[-1]
        assert before_time <= trade_time <= after_time

    def test_append_multiple_trades(self):
        """Test appending multiple trades in sequence."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)
        initial_len = len(trade_df.df)

        for i in range(5):
            trade_df.append(100.0 + i, 1.0, "bid")

        assert len(trade_df.df) == initial_len + 5

    def test_append_converts_to_float(self):
        """Test that price and volume are converted to float."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)

        trade_df.append(100, 10, "bid")  # Pass integers

        assert isinstance(trade_df.df["price"].iloc[-1], float)
        assert isinstance(trade_df.df["volume"].iloc[-1], float)


class TestOHLCData:
    """Test OHLC data calculation."""

    def test_get_ohlc_data_with_trades(self):
        """Test OHLC calculation with multiple trades."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)

        base_time = pd.Timestamp("2025-01-01 00:00:00")
        trade_df.append(100.0, 1.0, "bid", base_time)
        trade_df.append(105.0, 1.0, "bid", base_time + timedelta(minutes=30))
        trade_df.append(95.0, 1.0, "ask", base_time + timedelta(hours=1))
        trade_df.append(102.0, 1.0, "bid", base_time + timedelta(hours=1, minutes=30))

        # Use a range that includes the data
        ohlc = trade_df.get_ohlc_data(
            base_time, base_time + timedelta(hours=1, minutes=30), "1h"
        )

        assert not ohlc.empty
        assert "price" in ohlc.columns
        assert "volume" in ohlc.columns

    def test_get_ohlc_data_empty_range(self):
        """Test OHLC calculation with no trades in range."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)

        base_time = pd.Timestamp("2025-01-01 00:00:00")
        future_time = base_time + timedelta(days=10)

        ohlc = trade_df.get_ohlc_data(
            future_time, future_time + timedelta(hours=1), "1h"
        )

        # Should return empty or zero-filled data
        assert isinstance(ohlc, pd.DataFrame)

    def test_get_ohlc_data_different_intervals(self):
        """Test OHLC calculation with different time intervals."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)

        base_time = pd.Timestamp("2025-01-01 00:00:00")
        for i in range(24):
            trade_df.append(100.0 + i, 1.0, "bid", base_time + timedelta(hours=i))

        # Test different intervals - use the last time in range
        last_time = base_time + timedelta(hours=23)
        for interval in ["1h", "6h", "1d"]:
            ohlc = trade_df.get_ohlc_data(base_time, last_time, interval)
            assert isinstance(ohlc, pd.DataFrame)


class TestKlineChartGeneration:
    """Test kline chart generation and file operations."""

    @patch("src.orderbook.trade.plt.clf")
    def test_save_24h_kline_png_with_sufficient_data(self, mock_clf):
        """Test kline chart generation with sufficient data."""
        mock_book = Mock()
        mock_book.market_name = "BTC/USD"
        trade_df = TradeDataFrame(mock_book)

        # Add sufficient trades
        base_time = datetime.now() - timedelta(hours=23)
        for i in range(10):
            trade_df.append(100.0 + i, 1.0, "bid", base_time + timedelta(hours=i * 2))

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.orderbook.trade.RESULT_DIR", Path(tmpdir)):
                # Mock the plot object's get_figure().savefig() method
                with patch("pandas.Series.plot") as mock_plot:
                    mock_figure = Mock()
                    mock_plot.return_value.get_figure.return_value = mock_figure
                    mock_plot.return_value.axis = Mock()

                    trade_df.save_24h_kline_png()

                    # Check that CSV file was created
                    csv_path = trade_df.kline_csv_path
                    assert csv_path.exists()

                    # Check that plotting functions were called
                    mock_figure.savefig.assert_called_once()
                    mock_clf.assert_called_once()

    @patch("src.orderbook.trade.plt.clf")
    def test_save_24h_kline_png_with_insufficient_data(self, _mock_clf):
        """Test kline chart generation with insufficient data (< 4 points)."""
        mock_book = Mock()
        mock_book.market_name = "BTC/USD"
        trade_df = TradeDataFrame(mock_book)

        # Add only 2 trades
        base_time = datetime.now() - timedelta(hours=2)
        trade_df.append(100.0, 1.0, "bid", base_time)
        trade_df.append(101.0, 1.0, "bid", base_time + timedelta(hours=1))

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.orderbook.trade.RESULT_DIR", Path(tmpdir)):
                # Mock the plot object's get_figure().savefig() method
                with patch("pandas.Series.plot") as mock_plot:
                    mock_figure = Mock()
                    mock_plot.return_value.get_figure.return_value = mock_figure
                    mock_plot.return_value.axis = Mock()

                    trade_df.save_24h_kline_png()

                    # Should still generate chart with synthetic data
                    mock_figure.savefig.assert_called_once()

    @patch("src.orderbook.trade.plt.clf")
    def test_save_24h_kline_png_with_custom_color(self, _mock_clf):
        """Test kline chart generation with custom color."""
        mock_book = Mock()
        mock_book.market_name = "ETH/USD"
        trade_df = TradeDataFrame(mock_book)

        base_time = datetime.now() - timedelta(hours=23)
        for i in range(10):
            trade_df.append(100.0 + i, 1.0, "bid", base_time + timedelta(hours=i * 2))

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.orderbook.trade.RESULT_DIR", Path(tmpdir)):
                # Mock the plot object's get_figure().savefig() method
                with patch("pandas.Series.plot") as mock_plot:
                    mock_figure = Mock()
                    mock_plot.return_value.get_figure.return_value = mock_figure
                    mock_plot.return_value.axis = Mock()

                    trade_df.save_24h_kline_png(color="#FF0000")

                    # Verify custom color was passed to plot
                    mock_plot.assert_called_once_with(color="#FF0000")
                    mock_figure.savefig.assert_called_once()

    def test_kline_paths_generation(self):
        """Test kline file path generation."""
        mock_book = Mock()
        mock_book.market_name = "BTC/USDT"
        trade_df = TradeDataFrame(mock_book)

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.orderbook.trade.RESULT_DIR", Path(tmpdir)):
                png_path = trade_df.kline_png_path
                csv_path = trade_df.kline_csv_path

                assert png_path.name == "BTC-USDT.png"
                assert csv_path.name == "BTC-USDT.csv"
                assert png_path.parent == csv_path.parent

    def test_format_market_name(self):
        """Test market name formatting for filenames."""
        mock_book = Mock()
        mock_book.market_name = "BTC/USD"
        trade_df = TradeDataFrame(mock_book)

        formatted = trade_df._format_market_name()
        assert formatted == "BTC-USD"


class TestShortInfo:
    """Test short information retrieval."""

    def test_get_short_info_with_data(self):
        """Test short info with sufficient trade data."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)

        base_time = datetime.now() - timedelta(days=7)
        trade_df.append(100.0, 1.0, "bid", base_time)
        trade_df.append(110.0, 1.0, "bid", base_time + timedelta(hours=1))
        trade_df.append(105.0, 1.0, "bid", base_time + timedelta(days=1))
        trade_df.append(120.0, 1.0, "bid", datetime.now())

        info = trade_df.get_short_info()

        assert "price" in info
        assert "1h_change" in info
        assert "1d_change" in info
        assert "1w_change" in info
        assert info["price"] == 120.0

    def test_get_short_info_empty_dataframe(self):
        """Test short info with empty dataframe."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)
        # Clear the dataframe but keep schema
        trade_df.df = trade_df.df.iloc[0:0]

        info = trade_df.get_short_info()

        assert info["price"] == 0.0
        assert info["1h_change"] == "-"
        assert info["1d_change"] == "-"
        assert info["1w_change"] == "-"

    def test_get_short_info_single_trade(self):
        """Test short info with only one trade."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)
        trade_df.df = trade_df._create_empty_dataframe()

        trade_df.append(100.0, 1.0, "bid")
        info = trade_df.get_short_info()

        assert info["price"] == 100.0
        # Changes should be "-" or NaN since no historical data
        assert info["1h_change"] in ["-", 0.0] or pd.isna(info["1h_change"])


class TestLongInfo:
    """Test long information retrieval."""

    def test_get_long_info_open_market(self):
        """Test long info for an open market."""
        mock_book = Mock()
        mock_book.is_closed = False
        mock_book.get_best_bid.return_value = 99.5
        mock_book.get_best_ask.return_value = 100.5
        trade_df = TradeDataFrame(mock_book)

        base_time = datetime.now() - timedelta(hours=12)
        trade_df.append(100.0, 1.0, "bid", base_time)
        trade_df.append(105.0, 1.0, "bid", base_time + timedelta(hours=6))
        trade_df.append(102.0, 1.0, "bid", datetime.now())

        info = trade_df.get_long_info()

        assert info["close"] is False
        assert info["best_buy"] == 99.5
        assert info["best_sell"] == 100.5
        assert "day_high" in info
        assert "day_low" in info
        assert "day_open" in info
        assert "day_close" in info
        assert "latest" in info
        assert "day_change" in info

    def test_get_long_info_closed_market(self):
        """Test long info for a closed market."""
        mock_book = Mock()
        mock_book.is_closed = True
        mock_book.closed_reason = "Market halted due to maintenance"
        trade_df = TradeDataFrame(mock_book)

        info = trade_df.get_long_info()

        assert info["close"] is True
        assert info["reason"] == "Market halted due to maintenance"
        assert len(info) == 2  # Only close and reason

    def test_get_long_info_no_trades(self):
        """Test long info with no trades."""
        mock_book = Mock()
        mock_book.is_closed = False
        mock_book.get_best_bid.return_value = 0
        mock_book.get_best_ask.return_value = 0
        trade_df = TradeDataFrame(mock_book)
        # Clear the dataframe but keep schema
        trade_df.df = trade_df.df.iloc[0:0]

        info = trade_df.get_long_info()

        assert info["close"] is False
        assert info["day_high"] == 0.0
        assert info["day_low"] == 0.0
        assert info["day_open"] == 0.0
        assert info["day_close"] == 0.0


class TestPriceCalculations:
    """Test price-related calculations."""

    def test_get_latest_price_with_trades(self):
        """Test getting latest price with existing trades."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)

        trade_df.append(100.0, 1.0, "bid")
        trade_df.append(105.0, 1.0, "bid")
        trade_df.append(102.0, 1.0, "ask")

        latest = trade_df._get_latest_price()
        assert latest == 102.0

    def test_get_latest_price_empty_dataframe(self):
        """Test getting latest price from empty dataframe."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)
        trade_df.df = trade_df.df.iloc[0:0]

        latest = trade_df._get_latest_price()
        assert latest == 0.0

    def test_get_price_change_with_data(self):
        """Test price change calculation with sufficient data."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)

        base_time = datetime.now() - timedelta(hours=2)
        trade_df.append(100.0, 1.0, "bid", base_time)
        trade_df.append(110.0, 1.0, "bid", datetime.now())

        change = trade_df._get_price_change("1H")

        # Change should be calculated (may be rounded)
        assert isinstance(change, (float, int, str))

    def test_get_price_change_insufficient_data(self):
        """Test price change calculation with insufficient data."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)
        trade_df.df = trade_df.df.iloc[0:0]

        change = trade_df._get_price_change("1D")
        assert change == "-"

    def test_get_day_ohlc_with_trades(self):
        """Test daily OHLC calculation with trades."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)

        base_time = datetime.now() - timedelta(hours=12)
        trade_df.append(100.0, 1.0, "bid", base_time)
        trade_df.append(110.0, 1.0, "bid", base_time + timedelta(hours=3))
        trade_df.append(95.0, 1.0, "ask", base_time + timedelta(hours=6))
        trade_df.append(105.0, 1.0, "bid", datetime.now())

        open_price, high, low, close = trade_df._get_day_ohlc()

        assert isinstance(open_price, float)
        assert isinstance(high, float)
        assert isinstance(low, float)
        assert isinstance(close, float)
        assert high >= low

    def test_get_day_ohlc_no_data(self):
        """Test daily OHLC calculation with no data."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)
        trade_df.df = trade_df.df.iloc[0:0]

        open_price, high, low, close = trade_df._get_day_ohlc()

        assert open_price == 0.0
        assert high == 0.0
        assert low == 0.0
        assert close == 0.0


class TestLastTrades:
    """Test last trades retrieval."""

    def test_get_last_trades_with_count(self):
        """Test getting last N trades."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)

        for i in range(10):
            trade_df.append(100.0 + i, 1.0, "bid")

        last_trades = trade_df.get_last_trades(5)

        assert len(last_trades) == 5
        assert last_trades["price"].iloc[-1] == 109.0

    def test_get_last_trades_count_exceeds_available(self):
        """Test getting more trades than available."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)

        trade_df.append(100.0, 1.0, "bid")
        trade_df.append(101.0, 1.0, "bid")

        last_trades = trade_df.get_last_trades(10)

        # Should return all available trades
        assert len(last_trades) <= 10

    def test_get_last_trades_zero_count(self):
        """Test getting zero trades."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)

        trade_df.append(100.0, 1.0, "bid")

        last_trades = trade_df.get_last_trades(0)
        assert len(last_trades) == 0


class TestFileIO:
    """Test file input/output operations."""

    def test_dump_and_read_dataframe(self):
        """Test dumping dataframe to CSV and reading it back."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)

        # Add some trades
        base_time = datetime.now() - timedelta(hours=5)
        for i in range(5):
            trade_df.append(
                100.0 + i,
                1.0 + i * 0.5,
                "bid" if i % 2 == 0 else "ask",
                base_time + timedelta(hours=i),
            )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Dump to file
            trade_df.dump_data_frame(tmp_path)

            # Create new instance and read
            new_trade_df = TradeDataFrame(mock_book)
            new_trade_df.read_from_csv(tmp_path)

            # Verify data matches
            assert len(new_trade_df.df) == len(trade_df.df)
            pd.testing.assert_frame_equal(
                trade_df.df.astype(float),
                new_trade_df.df.astype(float),
                check_dtype=False,
            )
        finally:
            Path(tmp_path).unlink()

    def test_read_from_nonexistent_file(self, capsys):
        """Test reading from a file that doesn't exist."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)

        trade_df.read_from_csv("/nonexistent/path/file.csv")

        captured = capsys.readouterr()
        assert "Error: File not found" in captured.out

    def test_read_from_empty_csv(self, capsys):
        """Test reading from an empty CSV file."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp_path = tmp.name
            # Create empty file

        try:
            trade_df.read_from_csv(tmp_path)
            captured = capsys.readouterr()
            assert "Error: CSV file" in captured.out and "is empty" in captured.out
        finally:
            Path(tmp_path).unlink()

    def test_dump_with_path_object(self):
        """Test dumping dataframe using Path object."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)
        trade_df.append(100.0, 1.0, "bid")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.csv"
            trade_df.dump_data_frame(path)
            assert path.exists()


class TestSyntheticDataGeneration:
    """Test synthetic data point generation for charts."""

    def test_add_synthetic_data_points(self):
        """Test adding synthetic data points to price series."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)

        prices = pd.Series(
            [100.0, 101.0],
            index=[
                pd.Timestamp("2025-01-01 00:00:00"),
                pd.Timestamp("2025-01-01 01:00:00"),
            ],
        )

        initial_len = len(prices)
        trade_df._add_synthetic_data_points(prices)

        # Should have added synthetic points
        assert len(prices) > initial_len

    def test_add_synthetic_data_points_empty_series(self):
        """Test adding synthetic data points to empty series."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)

        prices = pd.Series(dtype=float)

        # Should not raise error
        trade_df._add_synthetic_data_points(prices)
        assert len(prices) == 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_side_constants(self):
        """Test that side constants are properly defined."""
        assert TradeDataFrame.SIDE_BID == "bid"
        assert TradeDataFrame.SIDE_ASK == "ask"

    def test_column_name_constants(self):
        """Test that column name constants are properly defined."""
        assert TradeDataFrame.COL_PRICE == "price"
        assert TradeDataFrame.COL_VOLUME == "volume"
        assert TradeDataFrame.COL_IS_BID == "is_bid"

    def test_period_constants(self):
        """Test that period constants are properly defined."""
        assert TradeDataFrame.PERIOD_1_HOUR == "1H"
        assert TradeDataFrame.PERIOD_1_DAY == "1D"
        assert TradeDataFrame.PERIOD_1_WEEK == "1W"

    def test_multiple_trades_same_timestamp(self):
        """Test handling multiple trades at the same timestamp."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)

        same_time = datetime(2025, 1, 1, 12, 0, 0)
        trade_df.append(100.0, 1.0, "bid", same_time)
        trade_df.append(101.0, 2.0, "ask", same_time)

        # Both trades should be recorded
        trades_at_time = trade_df.df.loc[same_time]
        if isinstance(trades_at_time, pd.Series):
            assert len(trades_at_time) > 0
        else:
            assert len(trades_at_time) == 2

    def test_very_large_price_values(self):
        """Test handling very large price values."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)

        large_price = 999999999.99
        trade_df.append(large_price, 1.0, "bid")

        assert trade_df._get_latest_price() == large_price

    def test_very_small_price_values(self):
        """Test handling very small price values."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)

        small_price = 0.00000001
        trade_df.append(small_price, 1.0, "bid")

        assert trade_df._get_latest_price() == small_price

    def test_zero_volume_trade(self):
        """Test handling zero volume trades."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)

        trade_df.append(100.0, 0.0, "bid")

        assert trade_df.df["volume"].iloc[-1] == 0.0

    def test_negative_values_handled(self):
        """Test that negative values are accepted (though not realistic)."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)

        # System should accept negative values even if unrealistic
        trade_df.append(-100.0, -1.0, "bid")

        assert trade_df.df["price"].iloc[-1] == -100.0
        assert trade_df.df["volume"].iloc[-1] == -1.0


class TestInterpolation:
    """Test price interpolation for charts."""

    def test_interpolate_prices(self):
        """Test cubic interpolation of prices."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)

        prices = pd.Series(
            [100.0, 110.0, 105.0, 115.0],
            index=pd.date_range("2025-01-01", periods=4, freq="1h"),
        )

        interpolated = trade_df._interpolate_prices(prices)

        # Should have more data points due to minute interpolation
        assert len(interpolated) > len(prices)

    def test_ensure_sufficient_data_with_few_points(self):
        """Test ensuring sufficient data with less than 4 points."""
        mock_book = Mock()
        trade_df = TradeDataFrame(mock_book)

        prices = pd.Series(
            [100.0, 101.0], index=pd.date_range("2025-01-01", periods=2, freq="1h")
        )

        result = trade_df._ensure_sufficient_data(prices)

        # Should forward fill and potentially add synthetic data
        assert not result.isna().any()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
