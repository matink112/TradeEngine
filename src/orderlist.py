class OrderList:
    """
    A doubly linked list of Orders. Used to iterate through Orders when
    a price match is found. Each OrderList is associated with a single
    price. Since a single price match can have more quantity than a single
    Order, we may need multiple Orders to full fill a transaction. The
    OrderList makes this easy to do. OrderList is naturally arranged by time.
    Orders at the front of the list have priority.
    """

    def __init__(self):
        self.head_order = None
        self.tail_order = None
        self.length = 0
        self.volume = 0  # sum of Order quantity in the list
        self.last = None  # helper for iterating

    def __len__(self):
        return self.length

    def __iter__(self):
        self.last = self.head_order
        return self

    def __next__(self):
        """
        Get the next order in the list.

        Set self.last as the next order. If there is no next order, stop
        iterating through list.
        """
        if self.last is None:
            raise StopIteration
        else:
            value = self.last
            self.last = self.last.next_order
            return value

    def get_head_order(self):
        return self.head_order

    def append_order(self, order):
        if len(self) == 0:
            order.next_order = order.prev_order = None
            self.head_order = self.tail_order = order
        else:
            order.prev_order = self.tail_order
            order.next_order = None
            self.tail_order.next_order = self.tail_order = order
        self.length += 1
        self.volume += order.quantity

    def remove_order(self, order):
        self.volume -= order.quantity
        self.length -= 1
        if len(self) != 0:
            # remove and relink orders
            next_order, prev_order = order.next_order, order.prev_order
            if next_order is not None and prev_order is not None:
                next_order.prev_order, prev_order.next_order = prev_order, next_order

            elif next_order is None:  # There is no next order
                # The previous order becomes the last order in the OrderList after this Order is removed
                prev_order.next_order, self.tail_order = None, prev_order

            elif prev_order is None:  # There is no previous order
                # The next order becomes the first order in the OrderList after this Order is removed
                next_order.prev_order, self.head_order = None, next_order

    def move_to_tail(self, order):
        """
        After updating the quantity of an existing Order, move it to the tail of the OrderList
        Check to see that the quantity is larger than existing, update the quantities,
        then move to tail to loss priority.
        """

        if order.prev_order is not None:  # This Order is not the first Order in the OrderList
            # Link the previous Order to the next Order, then move the Order to tail
            order.prev_order.next_order = order.next_order
        else:  # This Order is the first Order in the OrderList
            self.head_order = order.next_order  # Make next order the first

        order.next_order.prev_order = order.prev_order

        order.prev_order = self.tail_order
        order.next_order = None

        # Move Order to the last position. Link up the previous last position Order.
        self.tail_order.next_order = self.tail_order = order

    def __str__(self):
        return ', '.join(f'{order.order_id} /{order.quantity}/ {order.price} ' for order in self)
