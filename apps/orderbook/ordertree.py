from sortedcontainers import SortedDict

from apps.orderbook.order import Order
from apps.orderbook.orderlist import OrderList


class OrderTree:
    """
    A tree used to store OrderLists in price order

    The exchange will be using the OrderTree to hold bid and ask data (one OrderTree for each side).
    Keeping the information in a red black tree makes it easier/faster to detect a match.
    """

    def __init__(self):
        self.price_map = SortedDict()  # Dictionary containing price : OrderList object
        self.prices = self.price_map.keys()
        self.order_map = {}  # Dictionary containing order_id : Order object
        self.volume = 0  # Contains total quantity from all Orders in tree
        self.num_orders = 0  # Contains count of Orders in tree
        self.depth = 0  # Number of different prices in tree

    def __len__(self):
        return len(self.order_map)

    def get_price_list(self, price):
        return self.price_map[price]

    def get_order(self, order_id):
        return self.order_map[order_id]

    def create_price(self, price):
        self.depth += 1  # Add a price depth level to the tree
        new_list = OrderList()
        self.price_map[price] = new_list

    def remove_price(self, price):
        self.depth -= 1  # Remove a price depth level
        del self.price_map[price]

    def price_exists(self, price):
        return price in self.price_map

    def order_exists(self, order):
        return order in self.order_map

    def trade_id_exists(self, trade_id):
        return any(order.trade_id == trade_id for order in self.order_map.values())

    def insert_order(self, data):
        if self.order_exists(data['order_id']):
            self.remove_order_by_id(data['order_id'])
        self.num_orders += 1
        if data['price'] not in self.price_map:
            self.create_price(data['price'])  # If price not in Price Map, create a node in RBtree
        order = Order(data, self.price_map[data['price']])  # Create an order
        self.price_map[order.price].append_order(order)  # Add the order to the OrderList in Price Map
        self.order_map[order.order_id] = order
        self.volume += order.quantity

    def update_order(self, new_data):
        order = self.order_map[new_data['order_id']]
        original_quantity = order.quantity
        if new_data['price'] != order.price:
            # Price changed. Remove order and update tree.
            order_list = self.price_map[order.price]
            order_list.remove_order(order)
            if len(order_list) == 0:  # If there is nothing else in the OrderList, remove the price from RBtree
                self.remove_price(order.price)
            self.insert_order(new_data)
        else:
            # Quantity changed. Price is the same.
            order.update_quantity(new_data['quantity'], new_data['timestamp'])
        self.volume += (order.quantity - original_quantity)

    def remove_order_by_id(self, order_id):
        self.num_orders -= 1
        order = self.order_map[order_id]
        self.volume -= order.quantity
        order.order_list.remove_order(order)
        if len(order.order_list) == 0:
            self.remove_price(order.price)
        del self.order_map[order_id]

    def max_price(self):
        return self.prices[-1] if self.depth > 0 else None

    def min_price(self):
        return self.prices[0] if self.depth > 0 else None

    def max_price_list(self):
        return self.get_price_list(self.max_price()) if self.depth > 0 else None

    def min_price_list(self):
        return self.get_price_list(self.min_price()) if self.depth > 0 else None
