from django.utils import timezone

import matplotlib as plt
import pandas as pd

from LimitOrderBook.settings import MEDIA_ROOT


class TradeDataFrame:
    def __init__(self, book):
        self.book = book
        self.df = pd.DataFrame(columns=['price', 'volume', 'is_bid'], dtype=float)
        self.df['is_bid'] = self.df['is_bid'].astype(bool)

        # for prevent table empty error when server in cold start
        # and user try to get data from changes and price
        self.append(0, 0, 'bid')

    def append(self, price, volume, side, date_time=None):
        if date_time is None:
            date_time = timezone.now()
        is_bid = True if side == 'bid' else False
        df = pd.DataFrame([[float(price), float(volume), is_bid]], index=[date_time], columns=['price', 'volume', 'is_bid'])
        self.df = pd.concat([self.df, df])

    def get_ohlc_data(self, from_time, to_time, interval):
        return self.df.loc[from_time: to_time].resample(interval).agg({'price': 'ohlc', 'volume': 'sum'}).fillna(0)

    def save_24h_kline_png(self, color='#46bbb7'):
        prices = self.df.last('1d').resample('1h').agg({'price': 'last'})['price']
        if len(prices) < 4:
            last_time = prices.tail(1).index[0] + pd.Timedelta(days=1)
            last_price = prices.tail(1)[0]
            prices.loc[last_time + pd.Timedelta(hours=6)] = last_price
            prices.loc[last_time + pd.Timedelta(hours=12)] = last_price
            prices.loc[last_time + pd.Timedelta(hours=18)] = last_price
        prices = prices.fillna(method='ffill')
        x_new = pd.date_range(prices.index.min(), prices.index.max(), freq='1min')
        interpolated_data = prices.reindex(x_new).interpolate('cubic')
        interpolated_data.to_csv(self.kline_csv_path)
        plot = interpolated_data.plot(color=color)
        plot.axis('off')
        plot.get_figure().savefig(self.kline_png_path, transparent=True)
        plt.clf()

    @property
    def kline_png_path(self):
        path = MEDIA_ROOT / 'kline'
        path.mkdir(parents=True, exist_ok=True)
        return path / f"{'-'.join(self.book.market_name.split('/'))}.png"

    @property
    def kline_csv_path(self):
        path = MEDIA_ROOT / 'kline'
        path.mkdir(parents=True, exist_ok=True)
        return path / f"{'-'.join(self.book.market_name.split('/'))}.csv"

    def get_short_info(self):
        return {
            'price': self._get_latest(),
            '1h_change': self._get_change('1H'),
            '1d_change': self._get_change('1D'),
            '1w_change': self._get_change('1W'),
        }

    def get_long_info(self):
        if self.book.is_closed:
            return {
                'close': True,
                'reason': self.book.closed_reason
            }
        else:
            o, h, l, c = self._get_day_ohlc()
            return {
                'best_buy': self.book.get_best_bid(),
                'best_sell': self.book.get_best_ask(),
                'close': False,
                'day_high': h,
                'day_low': l,
                'day_open': o,
                'day_close': c,
                'latest': self._get_latest(),
                'day_change': self._get_change('1D'),
            }

    def get_last_trades(self, count):
        return self.df.tail(count)

    def _get_day_ohlc(self):
        df = self.df.last('1d').resample('1D').agg({'price': 'ohlc', 'volume': 'sum'}).tail(1)['price']
        return df['open'][0], df['high'][0], df['low'][0], df['close'][0]

    def _get_latest(self):
        return self.df.tail(1)['price'][0]

    def _get_change(self, time):
        c = self.df.last(time).resample(time).agg({'price': 'last'}).pct_change().tail(1)['price'][0]
        return round(c, 2) if not pd.isna(c) else '-'

    def dump_data_frame(self, path):
        self.df.to_csv(path)

    def read_from_csv(self, path):
        self.df.from_csv(path)
