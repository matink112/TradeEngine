"""
Comprehensive test suite for the Order class.

Tests cover:
- Order initialization with various data types
- Property accessors (next/prev and next_order/prev_order)
- Quantity updates with time priority logic
- Dictionary serialization
- String representation
- Edge cases and error conditions
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, MagicMock
from src.orderbook.order import Order
from src.orderbook.orderlist import OrderList


class TestOrderInitialization:
    """Test Order initialization with various input scenarios."""

    def test_basic_initialization(self):
        """Test creating an order with minimal required fields."""
        order_list = OrderList()
        data = {
            "timestamp": 1234567890,
            "quantity": "100.5",
            "price": "50.25",
            "order_id": 42
        }
        order = Order(data, order_list)

        assert order.timestamp == 1234567890
        assert order.quantity == Decimal("100.5")
        assert order.price == Decimal("50.25")
        assert order.order_id == 42
        assert order.trade_id == "42"  # Defaults to str(order_id)
        assert order.wage is None
        assert order.order_list is order_list

    def test_initialization_with_trade_id(self):
        """Test creating an order with explicit trade_id."""
        order_list = OrderList()
        data = {
            "timestamp": 1234567890,
            "quantity": "100",
            "price": "50",
            "order_id": 42,
            "trade_id": "TRADE-XYZ-123"
        }
        order = Order(data, order_list)

        assert order.trade_id == "TRADE-XYZ-123"
        assert order.order_id == 42

    def test_initialization_with_wage(self):
        """Test creating an order with wage field."""
        order_list = OrderList()
        data = {
            "timestamp": 1234567890,
            "quantity": "100",
            "price": "50",
            "order_id": 42,
            "wage": {"type": "maker", "fee": "0.1"}
        }
        order = Order(data, order_list)

        assert order.wage == {"type": "maker", "fee": "0.1"}

    def test_initialization_with_string_timestamp(self):
        """Test that string timestamp is converted to int."""
        order_list = OrderList()
        data = {
            "timestamp": "1234567890",
            "quantity": "100",
            "price": "50",
            "order_id": "99"
        }
        order = Order(data, order_list)

        assert order.timestamp == 1234567890
        assert isinstance(order.timestamp, int)
        assert order.order_id == 99
        assert isinstance(order.order_id, int)

    def test_initialization_with_integer_quantities(self):
        """Test that integer quantities are converted to Decimal."""
        order_list = OrderList()
        data = {
            "timestamp": 1234567890,
            "quantity": 100,
            "price": 50,
            "order_id": 42
        }
        order = Order(data, order_list)

        assert order.quantity == Decimal("100")
        assert order.price == Decimal("50")
        assert isinstance(order.quantity, Decimal)
        assert isinstance(order.price, Decimal)

    def test_initialization_linked_list_pointers_are_none(self):
        """Test that linked list pointers are initialized to None."""
        order_list = OrderList()
        data = {
            "timestamp": 1234567890,
            "quantity": "100",
            "price": "50",
            "order_id": 42
        }
        order = Order(data, order_list)

        assert order._next is None
        assert order._prev is None
        assert order.next_order is None
        assert order.prev_order is None

    def test_initialization_with_decimal_objects(self):
        """Test creating an order with Decimal objects directly."""
        order_list = OrderList()
        data = {
            "timestamp": 1234567890,
            "quantity": Decimal("100.123"),
            "price": Decimal("50.456"),
            "order_id": 42
        }
        order = Order(data, order_list)

        assert order.quantity == Decimal("100.123")
        assert order.price == Decimal("50.456")

    def test_initialization_with_zero_values(self):
        """Test creating an order with zero timestamp, quantity, and price."""
        order_list = OrderList()
        data = {
            "timestamp": 0,
            "quantity": "0",
            "price": "0",
            "order_id": 0
        }
        order = Order(data, order_list)

        assert order.timestamp == 0
        assert order.quantity == Decimal("0")
        assert order.price == Decimal("0")
        assert order.order_id == 0

    def test_initialization_with_large_values(self):
        """Test creating an order with very large values."""
        order_list = OrderList()
        data = {
            "timestamp": 9999999999999,
            "quantity": "999999999999.999999",
            "price": "888888888888.888888",
            "order_id": 999999999
        }
        order = Order(data, order_list)

        assert order.timestamp == 9999999999999
        assert order.quantity == Decimal("999999999999.999999")
        assert order.price == Decimal("888888888888.888888")


class TestOrderPropertyAccessors:
    """Test property accessors for linked list navigation."""

    def test_next_order_getter(self):
        """Test getting next_order property."""
        order_list = OrderList()
        order1 = Order({"timestamp": 1, "quantity": "10", "price": "100", "order_id": 1}, order_list)
        order2 = Order({"timestamp": 2, "quantity": "10", "price": "100", "order_id": 2}, order_list)

        order1._next = order2
        assert order1.next_order is order2

    def test_next_order_setter(self):
        """Test setting next_order property."""
        order_list = OrderList()
        order1 = Order({"timestamp": 1, "quantity": "10", "price": "100", "order_id": 1}, order_list)
        order2 = Order({"timestamp": 2, "quantity": "10", "price": "100", "order_id": 2}, order_list)

        order1.next_order = order2
        assert order1._next is order2
        assert order1.next_order is order2

    def test_prev_order_getter(self):
        """Test getting prev_order property."""
        order_list = OrderList()
        order1 = Order({"timestamp": 1, "quantity": "10", "price": "100", "order_id": 1}, order_list)
        order2 = Order({"timestamp": 2, "quantity": "10", "price": "100", "order_id": 2}, order_list)

        order2._prev = order1
        assert order2.prev_order is order1

    def test_prev_order_setter(self):
        """Test setting prev_order property."""
        order_list = OrderList()
        order1 = Order({"timestamp": 1, "quantity": "10", "price": "100", "order_id": 1}, order_list)
        order2 = Order({"timestamp": 2, "quantity": "10", "price": "100", "order_id": 2}, order_list)

        order2.prev_order = order1
        assert order2._prev is order1
        assert order2.prev_order is order1

    def test_next_property_getter(self):
        """Test getting next property (legacy API)."""
        order_list = OrderList()
        order1 = Order({"timestamp": 1, "quantity": "10", "price": "100", "order_id": 1}, order_list)
        order2 = Order({"timestamp": 2, "quantity": "10", "price": "100", "order_id": 2}, order_list)

        order1._next = order2
        assert order1.next is order2

    def test_next_property_setter(self):
        """Test setting next property (legacy API)."""
        order_list = OrderList()
        order1 = Order({"timestamp": 1, "quantity": "10", "price": "100", "order_id": 1}, order_list)
        order2 = Order({"timestamp": 2, "quantity": "10", "price": "100", "order_id": 2}, order_list)

        order1.next = order2
        assert order1._next is order2
        assert order1.next is order2

    def test_prev_property_getter(self):
        """Test getting prev property (legacy API)."""
        order_list = OrderList()
        order1 = Order({"timestamp": 1, "quantity": "10", "price": "100", "order_id": 1}, order_list)
        order2 = Order({"timestamp": 2, "quantity": "10", "price": "100", "order_id": 2}, order_list)

        order2._prev = order1
        assert order2.prev is order1

    def test_prev_property_setter(self):
        """Test setting prev property (legacy API)."""
        order_list = OrderList()
        order1 = Order({"timestamp": 1, "quantity": "10", "price": "100", "order_id": 1}, order_list)
        order2 = Order({"timestamp": 2, "quantity": "10", "price": "100", "order_id": 2}, order_list)

        order2.prev = order1
        assert order2._prev is order1
        assert order2.prev is order1

    def test_properties_can_be_set_to_none(self):
        """Test that all linked list properties can be set to None."""
        order_list = OrderList()
        order = Order({"timestamp": 1, "quantity": "10", "price": "100", "order_id": 1}, order_list)
        order2 = Order({"timestamp": 2, "quantity": "10", "price": "100", "order_id": 2}, order_list)

        order.next_order = order2
        order.next_order = None
        assert order.next_order is None

        order.prev_order = order2
        order.prev_order = None
        assert order.prev_order is None

    def test_next_and_next_order_are_synchronized(self):
        """Test that next and next_order properties access the same underlying attribute."""
        order_list = OrderList()
        order1 = Order({"timestamp": 1, "quantity": "10", "price": "100", "order_id": 1}, order_list)
        order2 = Order({"timestamp": 2, "quantity": "10", "price": "100", "order_id": 2}, order_list)

        order1.next = order2
        assert order1.next_order is order2

        order1.next_order = None
        assert order1.next is None

    def test_prev_and_prev_order_are_synchronized(self):
        """Test that prev and prev_order properties access the same underlying attribute."""
        order_list = OrderList()
        order1 = Order({"timestamp": 1, "quantity": "10", "price": "100", "order_id": 1}, order_list)
        order2 = Order({"timestamp": 2, "quantity": "10", "price": "100", "order_id": 2}, order_list)

        order2.prev = order1
        assert order2.prev_order is order1

        order2.prev_order = None
        assert order2.prev is None


class TestOrderUpdateQuantity:
    """Test update_quantity method with various scenarios."""

    def test_update_quantity_decrease_no_move(self):
        """Test decreasing quantity does not move order in list."""
        order_list = OrderList()
        order = Order({"timestamp": 1000, "quantity": "100", "price": "50", "order_id": 1}, order_list)
        order_list.append_order(order)

        initial_volume = order_list.volume
        order.update_quantity(Decimal("80"), 2000)

        assert order.quantity == Decimal("80")
        assert order.timestamp == 2000
        assert order_list.volume == initial_volume - Decimal("20")

    def test_update_quantity_increase_when_tail(self):
        """Test increasing quantity when order is tail does not move it."""
        order_list = OrderList()
        order1 = Order({"timestamp": 1000, "quantity": "100", "price": "50", "order_id": 1}, order_list)
        order2 = Order({"timestamp": 2000, "quantity": "50", "price": "50", "order_id": 2}, order_list)
        order_list.append_order(order1)
        order_list.append_order(order2)

        # order2 is tail
        assert order_list.tail_order == order2

        order2.update_quantity(Decimal("75"), 3000)

        assert order2.quantity == Decimal("75")
        assert order2.timestamp == 3000
        assert order_list.tail_order == order2

    def test_update_quantity_increase_when_not_tail_moves_to_tail(self):
        """Test increasing quantity when not tail moves order to tail."""
        order_list = OrderList()
        order1 = Order({"timestamp": 1000, "quantity": "100", "price": "50", "order_id": 1}, order_list)
        order2 = Order({"timestamp": 2000, "quantity": "50", "price": "50", "order_id": 2}, order_list)
        order3 = Order({"timestamp": 3000, "quantity": "75", "price": "50", "order_id": 3}, order_list)

        order_list.append_order(order1)
        order_list.append_order(order2)
        order_list.append_order(order3)

        # order1 is head, order3 is tail
        assert order_list.head_order == order1
        assert order_list.tail_order == order3

        # Increase order1's quantity (should move to tail)
        order1.update_quantity(Decimal("150"), 4000)

        assert order1.quantity == Decimal("150")
        assert order1.timestamp == 4000
        assert order_list.tail_order == order1
        assert order_list.head_order == order2

    def test_update_quantity_same_quantity_updates_timestamp(self):
        """Test updating with same quantity only updates timestamp."""
        order_list = OrderList()
        order = Order({"timestamp": 1000, "quantity": "100", "price": "50", "order_id": 1}, order_list)
        order_list.append_order(order)

        initial_volume = order_list.volume
        order.update_quantity(Decimal("100"), 2000)

        assert order.quantity == Decimal("100")
        assert order.timestamp == 2000
        assert order_list.volume == initial_volume

    def test_update_quantity_to_zero(self):
        """Test updating quantity to zero."""
        order_list = OrderList()
        order = Order({"timestamp": 1000, "quantity": "100", "price": "50", "order_id": 1}, order_list)
        order_list.append_order(order)

        order.update_quantity(Decimal("0"), 2000)

        assert order.quantity == Decimal("0")
        assert order.timestamp == 2000
        assert order_list.volume == Decimal("0")

    def test_update_quantity_small_increase_not_tail(self):
        """Test small quantity increase when not tail moves order."""
        order_list = OrderList()
        order1 = Order({"timestamp": 1000, "quantity": "100", "price": "50", "order_id": 1}, order_list)
        order2 = Order({"timestamp": 2000, "quantity": "50", "price": "50", "order_id": 2}, order_list)

        order_list.append_order(order1)
        order_list.append_order(order2)

        # order1 is head, order2 is tail
        assert order_list.head_order == order1
        assert order_list.tail_order == order2

        # Small increase in order1
        order1.update_quantity(Decimal("100.01"), 3000)

        assert order_list.tail_order == order1
        assert order_list.head_order == order2

    def test_update_quantity_volume_calculation(self):
        """Test that volume is correctly calculated during updates."""
        order_list = OrderList()
        order1 = Order({"timestamp": 1000, "quantity": "100", "price": "50", "order_id": 1}, order_list)
        order2 = Order({"timestamp": 2000, "quantity": "50", "price": "50", "order_id": 2}, order_list)

        order_list.append_order(order1)
        order_list.append_order(order2)

        assert order_list.volume == Decimal("150")

        order1.update_quantity(Decimal("120"), 3000)
        assert order_list.volume == Decimal("170")

        order2.update_quantity(Decimal("30"), 4000)
        assert order_list.volume == Decimal("150")

    def test_update_quantity_single_order_in_list(self):
        """Test updating quantity when order is the only one in list."""
        order_list = OrderList()
        order = Order({"timestamp": 1000, "quantity": "100", "price": "50", "order_id": 1}, order_list)
        order_list.append_order(order)

        # Single order is both head and tail
        assert order_list.head_order == order
        assert order_list.tail_order == order

        # Increase quantity (should not move since it's already tail)
        order.update_quantity(Decimal("150"), 2000)

        assert order.quantity == Decimal("150")
        assert order_list.head_order == order
        assert order_list.tail_order == order

    def test_update_quantity_with_negative_delta(self):
        """Test updating quantity with a decrease (negative delta)."""
        order_list = OrderList()
        order = Order({"timestamp": 1000, "quantity": "100", "price": "50", "order_id": 1}, order_list)
        order_list.append_order(order)

        order.update_quantity(Decimal("40"), 2000)

        assert order.quantity == Decimal("40")
        assert order_list.volume == Decimal("40")

    def test_update_quantity_with_decimal_precision(self):
        """Test updating quantity with high decimal precision."""
        order_list = OrderList()
        order = Order({"timestamp": 1000, "quantity": "100.123456", "price": "50", "order_id": 1}, order_list)
        order_list.append_order(order)

        order.update_quantity(Decimal("100.654321"), 2000)

        assert order.quantity == Decimal("100.654321")
        # Volume delta: 100.123456 - 100.654321 = -0.530865
        expected_volume = Decimal("100.654321")
        assert order_list.volume == expected_volume


class TestOrderToDictAndStringMethods:
    """Test serialization and string representation methods."""

    def test_to_dict_basic(self):
        """Test converting order to dictionary."""
        order_list = OrderList()
        order = Order({
            "timestamp": 1234567890,
            "quantity": "100.5",
            "price": "50.25",
            "order_id": 42,
            "trade_id": "TRADE-123"
        }, order_list)

        result = order.to_dict()

        assert result["order_id"] == 42
        assert result["timestamp"] == 1234567890
        assert result["quantity"] == "100.5"
        assert result["price"] == "50.25"
        assert result["trade_id"] == "TRADE-123"

    def test_to_dict_with_wage(self):
        """Test to_dict includes wage field."""
        order_list = OrderList()
        wage_data = {"type": "maker", "fee": "0.1"}
        order = Order({
            "timestamp": 1234567890,
            "quantity": "100",
            "price": "50",
            "order_id": 42,
            "wage": wage_data
        }, order_list)

        result = order.to_dict()

        assert result["wage"] == wage_data

    def test_to_dict_without_wage(self):
        """Test to_dict with None wage."""
        order_list = OrderList()
        order = Order({
            "timestamp": 1234567890,
            "quantity": "100",
            "price": "50",
            "order_id": 42
        }, order_list)

        result = order.to_dict()

        assert result["wage"] is None

    def test_to_dict_default_trade_id(self):
        """Test to_dict with default trade_id (from order_id)."""
        order_list = OrderList()
        order = Order({
            "timestamp": 1234567890,
            "quantity": "100",
            "price": "50",
            "order_id": 99
        }, order_list)

        result = order.to_dict()

        assert result["trade_id"] == "99"
        assert result["order_id"] == 99

    def test_to_dict_preserves_decimal_string_format(self):
        """Test that to_dict converts Decimals back to strings."""
        order_list = OrderList()
        order = Order({
            "timestamp": 1234567890,
            "quantity": "100.123456789",
            "price": "50.987654321",
            "order_id": 42
        }, order_list)

        result = order.to_dict()

        assert isinstance(result["quantity"], str)
        assert isinstance(result["price"], str)
        assert result["quantity"] == "100.123456789"
        assert result["price"] == "50.987654321"

    def test_str_representation(self):
        """Test string representation of order."""
        order_list = OrderList()
        order = Order({
            "timestamp": 1234567890,
            "quantity": "100.5",
            "price": "50.25",
            "order_id": 42,
            "trade_id": "TRADE-XYZ"
        }, order_list)

        result = str(order)

        assert "100.5" in result
        assert "50.25" in result
        assert "TRADE-XYZ" in result
        assert "1234567890" in result
        assert "quantity:" in result
        assert "price:" in result
        assert "trade_id:" in result
        assert "time:" in result

    def test_str_representation_with_default_trade_id(self):
        """Test string representation with default trade_id."""
        order_list = OrderList()
        order = Order({
            "timestamp": 1000,
            "quantity": "10",
            "price": "5",
            "order_id": 123
        }, order_list)

        result = str(order)

        assert "10" in result
        assert "5" in result
        assert "123" in result
        assert "1000" in result

    def test_str_representation_format(self):
        """Test exact format of string representation."""
        order_list = OrderList()
        order = Order({
            "timestamp": 1234567890,
            "quantity": "100",
            "price": "50",
            "order_id": 42,
            "trade_id": "T1"
        }, order_list)

        result = str(order)
        expected = "quantity: 100 @ price: 50 / trade_id: T1 - time: 1234567890"

        assert result == expected


class TestOrderEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_order_with_very_large_timestamp(self):
        """Test order with timestamp at maximum practical value."""
        order_list = OrderList()
        large_timestamp = 9999999999999
        order = Order({
            "timestamp": large_timestamp,
            "quantity": "100",
            "price": "50",
            "order_id": 1
        }, order_list)

        assert order.timestamp == large_timestamp

    def test_order_with_negative_order_id(self):
        """Test order with negative order_id."""
        order_list = OrderList()
        order = Order({
            "timestamp": 1000,
            "quantity": "100",
            "price": "50",
            "order_id": -1
        }, order_list)

        assert order.order_id == -1
        assert order.trade_id == "-1"

    def test_order_with_very_small_decimal_values(self):
        """Test order with very small decimal quantities and prices."""
        order_list = OrderList()
        order = Order({
            "timestamp": 1000,
            "quantity": "0.00000001",
            "price": "0.00000001",
            "order_id": 1
        }, order_list)

        assert order.quantity == Decimal("0.00000001")
        assert order.price == Decimal("0.00000001")

    def test_order_list_reference_is_maintained(self):
        """Test that order maintains reference to its order_list."""
        order_list = OrderList()
        order = Order({
            "timestamp": 1000,
            "quantity": "100",
            "price": "50",
            "order_id": 1
        }, order_list)

        assert order.order_list is order_list
        # Reference should remain even after modifications
        order.update_quantity(Decimal("50"), 2000)
        assert order.order_list is order_list

    def test_multiple_orders_same_orderlist(self):
        """Test multiple orders can reference the same order_list."""
        order_list = OrderList()
        order1 = Order({"timestamp": 1000, "quantity": "100", "price": "50", "order_id": 1}, order_list)
        order2 = Order({"timestamp": 2000, "quantity": "50", "price": "50", "order_id": 2}, order_list)
        order3 = Order({"timestamp": 3000, "quantity": "75", "price": "50", "order_id": 3}, order_list)

        assert order1.order_list is order_list
        assert order2.order_list is order_list
        assert order3.order_list is order_list
        assert order1.order_list is order2.order_list is order3.order_list

    def test_order_with_empty_string_trade_id(self):
        """Test order with empty string trade_id."""
        order_list = OrderList()
        order = Order({
            "timestamp": 1000,
            "quantity": "100",
            "price": "50",
            "order_id": 42,
            "trade_id": ""
        }, order_list)

        assert order.trade_id == ""

    def test_order_wage_can_be_any_type(self):
        """Test that wage field can store various types."""
        order_list = OrderList()

        # Dictionary wage
        order1 = Order({
            "timestamp": 1000, "quantity": "100", "price": "50", "order_id": 1,
            "wage": {"fee": 0.1}
        }, order_list)
        assert order1.wage == {"fee": 0.1}

        # String wage
        order2 = Order({
            "timestamp": 1000, "quantity": "100", "price": "50", "order_id": 2,
            "wage": "fixed_fee"
        }, order_list)
        assert order2.wage == "fixed_fee"

        # Numeric wage
        order3 = Order({
            "timestamp": 1000, "quantity": "100", "price": "50", "order_id": 3,
            "wage": 5.5
        }, order_list)
        assert order3.wage == 5.5

        # None wage
        order4 = Order({
            "timestamp": 1000, "quantity": "100", "price": "50", "order_id": 4
        }, order_list)
        assert order4.wage is None

    def test_update_quantity_preserves_other_attributes(self):
        """Test that update_quantity doesn't modify other attributes."""
        order_list = OrderList()
        order = Order({
            "timestamp": 1000,
            "quantity": "100",
            "price": "50.25",
            "order_id": 42,
            "trade_id": "TRADE-123",
            "wage": {"fee": 0.1}
        }, order_list)
        order_list.append_order(order)

        order.update_quantity(Decimal("75"), 2000)

        # These should remain unchanged
        assert order.price == Decimal("50.25")
        assert order.order_id == 42
        assert order.trade_id == "TRADE-123"
        assert order.wage == {"fee": 0.1}
        assert order.order_list is order_list

    def test_order_linked_list_chain(self):
        """Test that orders can be properly chained in a linked list."""
        order_list = OrderList()
        order1 = Order({"timestamp": 1000, "quantity": "100", "price": "50", "order_id": 1}, order_list)
        order2 = Order({"timestamp": 2000, "quantity": "50", "price": "50", "order_id": 2}, order_list)
        order3 = Order({"timestamp": 3000, "quantity": "75", "price": "50", "order_id": 3}, order_list)

        # Manually chain them
        order1.next_order = order2
        order2.prev_order = order1
        order2.next_order = order3
        order3.prev_order = order2

        # Verify forward traversal
        assert order1.next_order is order2
        assert order2.next_order is order3
        assert order3.next_order is None

        # Verify backward traversal
        assert order3.prev_order is order2
        assert order2.prev_order is order1
        assert order1.prev_order is None

    def test_to_dict_immutability(self):
        """Test that to_dict returns a new dict each time."""
        order_list = OrderList()
        order = Order({
            "timestamp": 1000,
            "quantity": "100",
            "price": "50",
            "order_id": 1
        }, order_list)

        dict1 = order.to_dict()
        dict2 = order.to_dict()

        # Should be equal but not the same object
        assert dict1 == dict2
        assert dict1 is not dict2

        # Modifying one should not affect the other
        dict1["order_id"] = 999
        assert dict2["order_id"] == 1


class TestOrderIntegrationWithOrderList:
    """Test Order's interaction with OrderList during operations."""

    def test_order_appended_to_list_maintains_reference(self):
        """Test that appending order to list maintains proper references."""
        order_list = OrderList()
        order = Order({"timestamp": 1000, "quantity": "100", "price": "50", "order_id": 1}, order_list)

        order_list.append_order(order)

        assert order.order_list is order_list
        assert order_list.head_order is order
        assert order_list.tail_order is order

    def test_update_quantity_affects_orderlist_volume(self):
        """Test that quantity updates properly affect OrderList volume."""
        order_list = OrderList()
        order1 = Order({"timestamp": 1000, "quantity": "100", "price": "50", "order_id": 1}, order_list)
        order2 = Order({"timestamp": 2000, "quantity": "50", "price": "50", "order_id": 2}, order_list)

        order_list.append_order(order1)
        order_list.append_order(order2)

        initial_volume = Decimal("150")
        assert order_list.volume == initial_volume

        # Decrease order1
        order1.update_quantity(Decimal("80"), 3000)
        assert order_list.volume == Decimal("130")

        # Increase order2 (should move to tail)
        order2.update_quantity(Decimal("60"), 4000)
        assert order_list.volume == Decimal("140")

    def test_order_removal_and_readd(self):
        """Test removing and re-adding an order."""
        order_list = OrderList()
        order = Order({"timestamp": 1000, "quantity": "100", "price": "50", "order_id": 1}, order_list)

        order_list.append_order(order)
        assert order_list.length == 1

        order_list.remove_order(order)
        assert order_list.length == 0
        assert order_list.head_order is None

        # Re-add the same order
        order_list.append_order(order)
        assert order_list.length == 1
        assert order_list.head_order is order

    def test_multiple_quantity_updates_in_sequence(self):
        """Test multiple sequential quantity updates."""
        order_list = OrderList()
        order = Order({"timestamp": 1000, "quantity": "100", "price": "50", "order_id": 1}, order_list)
        order_list.append_order(order)

        # Multiple updates
        order.update_quantity(Decimal("90"), 1100)
        assert order.quantity == Decimal("90")
        assert order.timestamp == 1100

        order.update_quantity(Decimal("95"), 1200)
        assert order.quantity == Decimal("95")
        assert order.timestamp == 1200

        order.update_quantity(Decimal("85"), 1300)
        assert order.quantity == Decimal("85")
        assert order.timestamp == 1300

        assert order_list.volume == Decimal("85")

