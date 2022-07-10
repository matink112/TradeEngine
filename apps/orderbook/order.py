from decimal import Decimal


class Order:
    """
    Orders represent the core piece of the exchange. Every bid/ask is an Order.
    Orders are doubly linked and have helper functions (next_order, prev_order)
    to help the exchange full fill orders with quantities larger than a single
    existing Order.
    """

    def __init__(self, data, order_list):
        self.timestamp = int(data['timestamp'])  # integer representing the timestamp of order creation
        self.quantity = Decimal(data['quantity'])  # decimal representing amount of thing - can be partial amounts
        self.price = Decimal(data['price'])  # decimal representing price (currency)
        self.order_id = int(data['order_id'])
        self.trade_id = data['trade_id']
        self.wage = data['wage']

        # doubly linked list to make it easier to re-order Orders for a particular price point
        self.next_order = None
        self.prev_order = None
        self.order_list = order_list

    # helper functions in linked list
    def next_order(self):
        return self.next_order

    def prev_order(self):
        return self.prev_order

    def update_quantity(self, new_quantity, new_timestamp):
        # check to see that the order is not the last order in list and the quantity is more
        if new_quantity > self.quantity and self.order_list.tail_order != self:
            self.order_list.move_to_tail(self)  # move to the end to loses time priority

        # if new_new_quantity > self.quantity result of (self.quantity - new_quantity)
        # is a negative number and volume increase
        self.order_list.volume -= (self.quantity - new_quantity)  # update volume
        self.timestamp = new_timestamp
        self.quantity = new_quantity

    def __str__(self):
        return f'quantity: {self.quantity}@ price: {self.price} / trade_id: {self.trade_id} - time: {self.timestamp}'
