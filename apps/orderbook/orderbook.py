from decimal import Decimal

from apps.orderbook.exceptions import OrderTypeError, OrderNotFoundError, QuantityError
from apps.orderbook.ordertree import OrderTree
from apps.orderbook.trade import TradeDataFrame


class OrderBook(object):
    def __init__(self, tick_size=0.0001, market_name=None):
        self.trade_df = TradeDataFrame(self)
        self.bids = OrderTree()
        self.asks = OrderTree()
        self.last_tick = None
        self.last_timestamp = 0
        self.tick_size = tick_size
        self.time = 0
        self.next_order_id = 0
        self.market_name = market_name
        self.is_closed = False
        self.closed_reason = None

    def update_time(self):
        self.time += 1

    def process_order(self, data, from_data, verbose):
        order_type = data['type']
        order_in_book = None

        self._prepare_quote_types(data)

        if data['quantity'] <= 0:
            raise QuantityError(f'process_order() given order of quantity <= 0 with data: {data}')

        if order_type != 'limit' and order_type != 'market':
            raise OrderTypeError(f"order_type for process_order() is neither 'market' or 'limit' with data: {data}")

        if from_data:
            self.time = data['timestamp']
        else:
            self.update_time()
            data['timestamp'] = self.time
        if not from_data:
            self.next_order_id += 1
        if order_type == 'market':
            trades = self.process_market_order(data, verbose)
        elif order_type == 'limit':
            trades, order_in_book = self.process_limit_order(data, from_data, verbose)
        return trades, order_in_book

    def process_order_list(self, side, order_list, quantity_still_to_trade, data, verbose):
        """
        Takes an OrderList (stack of orders at one price) and an incoming order and matches
        appropriate trades given the order's quantity.
        """
        trades = []
        quantity_to_trade = quantity_still_to_trade
        while len(order_list) > 0 and quantity_to_trade > 0:
            head_order = order_list.get_head_order()
            traded_price = head_order.price
            counter_party = head_order.trade_id
            party_wage = head_order.wage
            new_book_quantity = None
            if quantity_to_trade < head_order.quantity:
                traded_quantity = quantity_to_trade
                # Do the transaction
                new_book_quantity = head_order.quantity - quantity_to_trade
                head_order.update_quantity(new_book_quantity, head_order.timestamp)
                quantity_to_trade = 0
            elif quantity_to_trade == head_order.quantity:
                traded_quantity = quantity_to_trade
                if side == 'bid':
                    self.bids.remove_order_by_id(head_order.order_id)
                else:
                    self.asks.remove_order_by_id(head_order.order_id)
                quantity_to_trade = 0
            else:  # quantity to trade is larger than the head order
                traded_quantity = head_order.quantity
                if side == 'bid':
                    self.bids.remove_order_by_id(head_order.order_id)
                else:
                    self.asks.remove_order_by_id(head_order.order_id)
                quantity_to_trade -= traded_quantity
            if verbose:
                print((f"TRADE: Time - {self.time}, Price - {traded_price}, Quantity - {traded_quantity}, \
                        TradeID - {counter_party}, Matching TradeID - {data['trade_id']}"))

            transaction_record = {
                'timestamp': self.time,
                'price': traded_price,
                'quantity': traded_quantity,
                'time': self.time,
                'party1': {
                    'trade_id': counter_party,
                    'side': side,
                    'order_id': head_order.order_id,
                    'new_book_quantity': new_book_quantity,
                    'wage': party_wage,
                },
                'party2': {
                    'trade_id': data['trade_id'],
                    'side': 'ask' if side == 'bid' else 'bid',
                    'order_id': data['order_id'],
                    'new_book_quantity': None,
                    'wage': data['wage'],
                }}

            self.trade_df.append(transaction_record['price'], transaction_record['quantity'], side)
            trades.append(transaction_record)
        return quantity_to_trade, trades

    def process_market_order(self, data, verbose):
        trades = []
        quantity_to_trade = data['quantity']
        side = data['side']

        if side != 'ask' and side != 'bid':
            raise OrderTypeError(f'process_market_order() received neither "bid" nor "ask" with data: {data}')

        if side == 'bid':
            while quantity_to_trade > 0 and self.asks:
                best_price_asks = self.asks.min_price_list()
                quantity_to_trade, new_trades = self.process_order_list('ask', best_price_asks, quantity_to_trade,
                                                                        data, verbose)
                trades += new_trades
        elif side == 'ask':
            while quantity_to_trade > 0 and self.bids:
                best_price_bids = self.bids.max_price_list()
                quantity_to_trade, new_trades = self.process_order_list('bid', best_price_bids, quantity_to_trade,
                                                                        data, verbose)
                trades += new_trades
        return trades

    def process_limit_order(self, data, from_data, verbose):
        order_in_book = None
        trades = []
        quantity_to_trade = data['quantity']
        side = data['side']
        price = data['price']

        if side != 'ask' and side != 'bid':
            raise OrderTypeError(f'process_limit_order() received neither "bid" nor "ask" with data: {data}')

        if side == 'bid':
            while self.asks and price >= self.asks.min_price() and quantity_to_trade > 0:
                best_price_asks = self.asks.min_price_list()
                quantity_to_trade, new_trades = self.process_order_list('ask', best_price_asks, quantity_to_trade,
                                                                        data, verbose)
                trades += new_trades

        elif side == 'ask':
            while self.bids and price <= self.bids.max_price() and quantity_to_trade > 0:
                best_price_bids = self.bids.max_price_list()
                quantity_to_trade, new_trades = self.process_order_list('bid', best_price_bids, quantity_to_trade,
                                                                        data, verbose)
                trades += new_trades

        # If volume remains, need to update the book with new quantity
        if quantity_to_trade > 0:
            if not from_data:
                data['order_id'] = self.next_order_id
            data['quantity'] = quantity_to_trade

            if side == 'ask':
                self.asks.insert_order(data)
            else:
                self.bids.insert_order(data)

            order_in_book = data
        return trades, order_in_book

    def cancel_order(self, side, order_id, time=None):
        if side != 'ask' and side != 'bid':
            raise OrderTypeError(f'cancel_order() received neither "bid" nor \
            "ask" with orderid: {order_id}, side: {side}')

        if time:
            self.time = time
        else:
            self.update_time()

        if side == 'bid' and self.bids.order_exists(order_id):
            self.bids.remove_order_by_id(order_id)
        elif side == 'ask' and self.asks.order_exists(order_id):
            self.asks.remove_order_by_id(order_id)
        else:
            raise OrderNotFoundError(f'in cancel_order() order with id: {order_id} and side: {side} not found')

    def _prepare_quote_types(self, quote):
        quote['quantity'] = Decimal(str(quote['quantity']))
        quote['price'] = Decimal(str(quote['price']))

    def modify_order(self, order_id, order_update, time=None):
        if time:
            self.time = time
        else:
            self.update_time()

        side = order_update['side']
        order_update['order_id'] = order_id
        order_update['timestamp'] = self.time

        if side != 'ask' and side != 'bid':
            raise OrderTypeError(f'modify_order() received neither "bid" nor \
            "ask" with orderid: {order_id}, side: {side}')

        if side == 'bid' and self.bids.order_exists(order_update['order_id']):
            self.bids.update_order(order_update)
        elif side == 'ask' and self.asks.order_exists(order_update['order_id']):
            self.asks.update_order(order_update)
        else:
            raise OrderNotFoundError(f'in modify_order() order with id: {order_id} and side: {side} not found')

    def get_volume_at_price(self, side, price):
        if side != 'ask' and side != 'bid':
            raise OrderTypeError(f'get_volume_at_price() received neither "bid" nor \
            "ask" with side: {side}')

        price = Decimal(price)
        volume = 0
        if side == 'bid':
            if self.bids.price_exists(price):
                volume = self.bids.get_price(price).volume
            return volume

        elif side == 'ask':
            if self.asks.price_exists(price):
                volume = self.asks.get_price(price).volume
            return volume

    def get_best_bid(self):
        return self.bids.max_price()

    def get_worst_bid(self):
        return self.bids.min_price()

    def get_best_ask(self):
        return self.asks.min_price()

    def get_worst_ask(self):
        return self.asks.max_price()

    def tape_dump(self, filename, filemode, tapemode):
        # TODO: dump dataframe
        # dumpfile = open(filename, filemode)
        # for tapeitem in self.tape:
        #     dumpfile.write('Time: %s, Price: %s, Quantity: %s\n' % (tapeitem['time'],
        #                                                             tapeitem['price'],
        #                                                             tapeitem['quantity']))
        # dumpfile.close()
        # if tapemode == 'wipe':
        #     self.tape = []
        pass