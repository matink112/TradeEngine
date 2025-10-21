from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

import matplotlib.pyplot as plt
import pandas as pd

from conf import RESULT_DIR

# Type aliases
Side = Literal["bid", "ask"]


class TradeDataFrame:
    """Manages and analyzes trade data for a limit order book.

    This class handles trade recording, OHLC calculations, chart generation,
    and statistical analysis of trading data.
    """

    # Constants
    SIDE_BID: Side = "bid"
    SIDE_ASK: Side = "ask"

    # Column names
    COL_PRICE = "price"
    COL_VOLUME = "volume"
    COL_IS_BID = "is_bid"

    # Time periods
    PERIOD_1_HOUR = "1H"
    PERIOD_1_DAY = "1D"
    PERIOD_1_WEEK = "1W"

    # Chart settings
    DEFAULT_CHART_COLOR = "#46bbb7"
    CHART_RESAMPLE_INTERVAL = "1h"
    CHART_INTERPOLATION_FREQUENCY = "1min"
    SYNTHETIC_DATA_INTERVALS = [6, 12, 18]  # hours

    def __init__(self, book) -> None:
        """Initialize trade dataframe with empty data.

        Args:
            book: The limit order book instance this dataframe tracks.
        """
        self.book = book
        self.df = self._create_empty_dataframe()

        # TODO: fix the bug and remove this
        self._add_initial_trade()

    def _create_empty_dataframe(self) -> pd.DataFrame:
        """Create an empty dataframe with proper schema."""
        df = pd.DataFrame(
            columns=[self.COL_PRICE, self.COL_VOLUME, self.COL_IS_BID], dtype=float
        )
        df[self.COL_IS_BID] = df[self.COL_IS_BID].astype(bool)
        return df

    def _add_initial_trade(self) -> None:
        """Add initial trade to prevent empty table errors."""
        self.append(0, 0, self.SIDE_BID)

    def append(
        self,
        price: float,
        volume: float,
        side: Side,
        date_time: Optional[datetime] = None,
    ) -> None:
        """Append a new trade record to the dataframe.

        Args:
            price: Trade execution price.
            volume: Trade volume.
            side: Trade side (bid or ask).
            date_time: Trade timestamp. Defaults to current time.
        """
        if date_time is None:
            date_time = datetime.now()

        new_row = self._create_trade_row(price, volume, side, date_time)
        self.df = pd.concat([self.df, new_row])

    def _create_trade_row(
        self, price: float, volume: float, side: Side, date_time: datetime
    ) -> pd.DataFrame:
        """Create a single trade row as a dataframe."""
        is_bid = side == self.SIDE_BID
        return pd.DataFrame(
            [[float(price), float(volume), is_bid]],
            index=[date_time],
            columns=[self.COL_PRICE, self.COL_VOLUME, self.COL_IS_BID],
        )

    def get_ohlc_data(
        self, from_time: pd.Timestamp, to_time: pd.Timestamp, interval: str
    ) -> pd.DataFrame:
        """Get OHLC (Open, High, Low, Close) data for the specified time range.

        Args:
            from_time: Start timestamp.
            to_time: End timestamp.
            interval: Resampling interval (e.g., '1h', '1d').

        Returns:
            DataFrame with OHLC price data and volume sum.
        """
        return (
            self.df.loc[from_time:to_time]
            .resample(interval)
            .agg({self.COL_PRICE: "ohlc", self.COL_VOLUME: "sum"})
            .fillna(0)
        )

    def save_24h_kline_png(self, color: str = DEFAULT_CHART_COLOR) -> None:
        """Generate and save a 24-hour candlestick (kline) chart.

        Creates both PNG image and CSV data file with hourly price data
        interpolated to minute resolution.

        Args:
            color: Chart line color in hex format.
        """
        prices = self._get_hourly_prices()
        prices = self._ensure_sufficient_data(prices)
        interpolated_prices = self._interpolate_prices(prices)

        self._save_chart_files(interpolated_prices, color)

    def _get_hourly_prices(self) -> pd.Series:
        """Extract hourly prices from the last 24 hours."""
        return (
            self.df.last(self.PERIOD_1_DAY)
            .resample(self.CHART_RESAMPLE_INTERVAL)
            .agg({self.COL_PRICE: "last"})[self.COL_PRICE]
        )

    def _ensure_sufficient_data(self, prices: pd.Series) -> pd.Series:
        """Add synthetic data points if insufficient data exists."""
        if len(prices) < 4:
            self._add_synthetic_data_points(prices)
        return prices.ffill()

    def _interpolate_prices(self, prices: pd.Series) -> pd.Series:
        """Interpolate prices to minute resolution using cubic interpolation."""
        time_range = pd.date_range(
            prices.index.min(),
            prices.index.max(),
            freq=self.CHART_INTERPOLATION_FREQUENCY,
        )
        return prices.reindex(time_range).interpolate("cubic")

    def _save_chart_files(self, data: pd.Series, color: str) -> None:
        """Save chart data as CSV and PNG image."""
        data.to_csv(self.kline_csv_path)

        plot = data.plot(color=color)
        plot.axis("off")
        plot.get_figure().savefig(self.kline_png_path, transparent=True)
        plt.clf()

    def _add_synthetic_data_points(self, prices: pd.Series) -> None:
        """Add synthetic data points to ensure smooth interpolation.

        Args:
            prices: Series of prices to augment with synthetic points.
        """
        if prices.empty:
            return

        last_time = prices.index[-1] + pd.Timedelta(days=1)
        last_price = prices.iloc[-1]

        for hours in self.SYNTHETIC_DATA_INTERVALS:
            synthetic_time = last_time + pd.Timedelta(hours=hours)
            prices.loc[synthetic_time] = last_price

    @property
    def kline_png_path(self) -> Path:
        """Get the file path for kline PNG chart."""
        return self._get_kline_path("png")

    @property
    def kline_csv_path(self) -> Path:
        """Get the file path for kline CSV data."""
        return self._get_kline_path("csv")

    def _get_kline_path(self, extension: str) -> Path:
        """Generate file path for kline files.

        Args:
            extension: File extension without dot (e.g., 'png', 'csv').

        Returns:
            Full path to the kline file.
        """
        kline_dir = RESULT_DIR / "kline"
        kline_dir.mkdir(parents=True, exist_ok=True)

        market_filename = self._format_market_name()
        return kline_dir / f"{market_filename}.{extension}"

    def _format_market_name(self) -> str:
        """Format market name for use in filenames."""
        return "-".join(self.book.market_name.split("/"))

    def get_short_info(self) -> dict[str, float | str]:
        """Get summarized trade information with price changes.

        Returns:
            Dictionary with current price and percentage changes.
        """
        return {
            "price": self._get_latest_price(),
            "1h_change": self._get_price_change(self.PERIOD_1_HOUR),
            "1d_change": self._get_price_change(self.PERIOD_1_DAY),
            "1w_change": self._get_price_change(self.PERIOD_1_WEEK),
        }

    def get_long_info(self) -> dict[str, float | bool | str]:
        """Get detailed trade information including OHLC data.

        Returns:
            Dictionary with comprehensive market data or closure information.
        """
        if self.book.is_closed:
            return self._get_closed_market_info()

        return self._get_open_market_info()

    def _get_closed_market_info(self) -> dict[str, bool | str]:
        """Get information for a closed market."""
        return {"close": True, "reason": self.book.closed_reason}

    def _get_open_market_info(self) -> dict[str, float | bool | str]:
        """Get comprehensive information for an active market."""
        open_price, high, low, close = self._get_day_ohlc()

        return {
            "best_buy": self.book.get_best_bid(),
            "best_sell": self.book.get_best_ask(),
            "close": False,
            "day_high": high,
            "day_low": low,
            "day_open": open_price,
            "day_close": close,
            "latest": self._get_latest_price(),
            "day_change": self._get_price_change(self.PERIOD_1_DAY),
        }

    def get_last_trades(self, count: int) -> pd.DataFrame:
        """Get the most recent trades.

        Args:
            count: Number of recent trades to retrieve.

        Returns:
            DataFrame containing the last N trades.
        """
        return self.df.tail(count)

    def _get_day_ohlc(self) -> tuple[float, float, float, float]:
        """Calculate the day's Open, High, Low, Close prices.

        Returns:
            Tuple of (open, high, low, close) prices. Returns zeros if no data.
        """
        try:
            ohlc_df = self._resample_daily_ohlc()
            return (
                ohlc_df["open"].iloc[0],
                ohlc_df["high"].iloc[0],
                ohlc_df["low"].iloc[0],
                ohlc_df["close"].iloc[0],
            )
        except (IndexError, KeyError):
            return 0.0, 0.0, 0.0, 0.0

    def _resample_daily_ohlc(self) -> pd.DataFrame:
        """Resample last day's data into daily OHLC format."""
        return (
            self.df.last(self.PERIOD_1_DAY)
            .resample(self.PERIOD_1_DAY)
            .agg({self.COL_PRICE: "ohlc", self.COL_VOLUME: "sum"})
            .tail(1)[self.COL_PRICE]
        )

    def _get_latest_price(self) -> float:
        """Get the most recent trade price.

        Returns:
            Latest price or 0.0 if no trades exist.
        """
        try:
            return self.df[self.COL_PRICE].iloc[-1]
        except IndexError:
            return 0.0

    def _get_price_change(self, time_period: str) -> float | str:
        """Calculate percentage price change over specified period.

        Args:
            time_period: Time period string (e.g., '1H', '1D', '1W').

        Returns:
            Percentage change rounded to 2 decimals, or '-' if unavailable.
        """
        try:
            change = self._calculate_period_change(time_period)
            return round(change, 2) if not pd.isna(change) else "-"
        except (IndexError, KeyError):
            return "-"

    def _calculate_period_change(self, time_period: str) -> float:
        """Calculate raw percentage change for a time period."""
        return (
            self.df.last(time_period)
            .resample(time_period)
            .agg({self.COL_PRICE: "last"})
            .pct_change()
            .tail(1)[self.COL_PRICE]
            .iloc[0]
        )

    def dump_data_frame(self, path: str | Path) -> None:
        """Save dataframe to CSV file.

        Args:
            path: Destination file path.
        """
        self.df.to_csv(path)

    def read_from_csv(self, path: str | Path) -> None:
        """Load dataframe from CSV file.

        Args:
            path: Source file path.
        """
        try:
            self.df = pd.read_csv(path, index_col=0, parse_dates=True)
        except FileNotFoundError:
            print(f"Error: File not found at {path}")
        except pd.errors.EmptyDataError:
            print(f"Error: CSV file at {path} is empty")
        except Exception as e:
            print(f"Error reading CSV from {path}: {e}")
