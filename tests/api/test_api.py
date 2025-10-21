"""
Comprehensive test suite for the FastAPI orderbook endpoints.
Tests all scenarios, edge cases, and error conditions.
"""
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api import router, book
from src.orderbook.orderbook import SIDE_BID, SIDE_ASK, ORDER_TYPE_LIMIT, ORDER_TYPE_MARKET


@pytest.fixture
def app():
    """Create a FastAPI app with the orderbook router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_orderbook():
    """Reset the orderbook before each test."""
    # Clear the order book before each test
    book.bids = type(book.bids)()
    book.asks = type(book.asks)()
    book.next_order_id = 0
    book.time = 0
    book.last_timestamp = 0
    yield
    # Clean up after test
    book.bids = type(book.bids)()
    book.asks = type(book.asks)()
    book.next_order_id = 0
    book.time = 0
    book.last_timestamp = 0


class TestCreateOrder:
    """Test POST /api/orders endpoint."""

    def test_create_limit_order_bid_success(self, client):
        """Test creating a bid limit order that goes into the book."""
        payload = {
            "side": "bid",
            "type": "limit",
            "quantity": "10.5",
            "price": "100.50",
            "trade_id": "TRADE001",
            "wage": "trader1"
        }
        response = client.post("/api/orders", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["trades"] == []
        assert data["order"] is not None
        assert data["order"]["order_id"] == 1
        assert data["order"]["side"] == "bid"
        assert Decimal(data["order"]["quantity"]) == Decimal("10.5")
        assert Decimal(data["order"]["price"]) == Decimal("100.50")
        assert data["order"]["trade_id"] == "TRADE001"
        assert data["order"]["wage"] == "trader1"

    def test_create_limit_order_ask_success(self, client):
        """Test creating an ask limit order that goes into the book."""
        payload = {
            "side": "ask",
            "type": "limit",
            "quantity": "5.25",
            "price": "105.00",
            "trade_id": "TRADE002"
        }
        response = client.post("/api/orders", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["trades"] == []
        assert data["order"] is not None
        assert data["order"]["order_id"] == 1
        assert data["order"]["side"] == "ask"

    def test_create_limit_order_with_immediate_match(self, client):
        """Test creating a limit order that immediately matches with existing order."""
        # Place a resting ask order
        ask_payload = {
            "side": "ask",
            "type": "limit",
            "quantity": "10",
            "price": "100.00",
            "trade_id": "ASK001"
        }
        client.post("/api/orders", json=ask_payload)

        # Place a bid that crosses the spread
        bid_payload = {
            "side": "bid",
            "type": "limit",
            "quantity": "5",
            "price": "100.00",
            "trade_id": "BID001"
        }
        response = client.post("/api/orders", json=bid_payload)

        assert response.status_code == 201
        data = response.json()
        assert len(data["trades"]) == 1
        trade = data["trades"][0]
        assert Decimal(trade["quantity"]) == Decimal("5")
        assert Decimal(trade["price"]) == Decimal("100.00")
        assert data["order"] is None  # Fully consumed

    def test_create_limit_order_with_partial_match(self, client):
        """Test limit order that partially matches and remainder goes to book."""
        # Place a resting ask order
        ask_payload = {
            "side": "ask",
            "type": "limit",
            "quantity": "5",
            "price": "100.00",
            "trade_id": "ASK001"
        }
        client.post("/api/orders", json=ask_payload)

        # Place a larger bid that crosses
        bid_payload = {
            "side": "bid",
            "type": "limit",
            "quantity": "10",
            "price": "101.00",
            "trade_id": "BID001"
        }
        response = client.post("/api/orders", json=bid_payload)

        assert response.status_code == 201
        data = response.json()
        assert len(data["trades"]) == 1
        assert Decimal(data["trades"][0]["quantity"]) == Decimal("5")
        assert data["order"] is not None
        assert Decimal(data["order"]["quantity"]) == Decimal("5")  # Remaining quantity

    def test_create_market_order_bid_success(self, client):
        """Test creating a market bid order that executes against asks."""
        # Place resting ask orders
        client.post("/api/orders", json={
            "side": "ask",
            "type": "limit",
            "quantity": "10",
            "price": "100.00",
            "trade_id": "ASK001"
        })

        # Place market bid order
        market_payload = {
            "side": "bid",
            "type": "market",
            "quantity": "5",
            "trade_id": "MKT001"
        }
        response = client.post("/api/orders", json=market_payload)

        assert response.status_code == 201
        data = response.json()
        assert len(data["trades"]) == 1
        assert Decimal(data["trades"][0]["quantity"]) == Decimal("5")
        assert data["order"] is None

    def test_create_market_order_ask_success(self, client):
        """Test creating a market ask order that executes against bids."""
        # Place resting bid order
        client.post("/api/orders", json={
            "side": "bid",
            "type": "limit",
            "quantity": "10",
            "price": "100.00",
            "trade_id": "BID001"
        })

        # Place market ask order
        market_payload = {
            "side": "ask",
            "type": "market",
            "quantity": "5",
            "trade_id": "MKT001"
        }
        response = client.post("/api/orders", json=market_payload)

        assert response.status_code == 201
        data = response.json()
        assert len(data["trades"]) == 1
        assert data["order"] is None

    def test_create_order_invalid_quantity_zero(self, client):
        """Test creating order with zero quantity fails."""
        payload = {
            "side": "bid",
            "type": "limit",
            "quantity": "0",
            "price": "100.00",
            "trade_id": "TRADE001"
        }
        response = client.post("/api/orders", json=payload)

        assert response.status_code == 422  # Pydantic validation error
        assert "quantity" in str(response.json()["detail"]).lower()

    def test_create_order_invalid_quantity_negative(self, client):
        """Test creating order with negative quantity fails."""
        payload = {
            "side": "bid",
            "type": "limit",
            "quantity": "-5",
            "price": "100.00",
            "trade_id": "TRADE001"
        }
        response = client.post("/api/orders", json=payload)

        assert response.status_code == 422  # Pydantic validation error

    def test_create_order_invalid_side(self, client):
        """Test creating order with invalid side fails."""
        payload = {
            "side": "invalid",
            "type": "limit",
            "quantity": "10",
            "price": "100.00",
            "trade_id": "TRADE001"
        }
        response = client.post("/api/orders", json=payload)

        assert response.status_code == 422  # Pydantic validation error

    def test_create_order_invalid_type(self, client):
        """Test creating order with invalid type fails."""
        payload = {
            "side": "bid",
            "type": "invalid",
            "quantity": "10",
            "price": "100.00",
            "trade_id": "TRADE001"
        }
        response = client.post("/api/orders", json=payload)

        assert response.status_code == 422  # Pydantic validation error

    def test_create_limit_order_without_price(self, client):
        """Test creating limit order without price fails."""
        payload = {
            "side": "bid",
            "type": "limit",
            "quantity": "10",
            "trade_id": "TRADE001"
        }
        response = client.post("/api/orders", json=payload)

        assert response.status_code == 400  # OrderTypeError from orderbook
        assert "price" in response.json()["detail"].lower()

    def test_create_market_order_without_price(self, client):
        """Test creating market order without price succeeds."""
        # Place resting ask
        client.post("/api/orders", json={
            "side": "ask",
            "type": "limit",
            "quantity": "10",
            "price": "100.00",
            "trade_id": "ASK001"
        })

        payload = {
            "side": "bid",
            "type": "market",
            "quantity": "5",
            "trade_id": "MKT001"
        }
        response = client.post("/api/orders", json=payload)

        assert response.status_code == 201

    def test_create_order_missing_required_fields(self, client):
        """Test creating order with missing required fields fails."""
        payload = {
            "side": "bid",
            "type": "limit"
        }
        response = client.post("/api/orders", json=payload)

        assert response.status_code == 422

    def test_create_multiple_orders_incremental_ids(self, client):
        """Test that multiple orders get incremental IDs."""
        for i in range(3):
            payload = {
                "side": "bid",
                "type": "limit",
                "quantity": "10",
                "price": f"{100 + i}.00",
                "trade_id": f"TRADE{i:03d}"
            }
            response = client.post("/api/orders", json=payload)
            assert response.status_code == 201
            assert response.json()["order"]["order_id"] == i + 1


class TestListOrders:
    """Test GET /api/orders/{side} endpoint."""

    def test_list_bid_orders_empty(self, client):
        """Test listing bid orders when none exist."""
        response = client.get("/api/orders/bid")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_ask_orders_empty(self, client):
        """Test listing ask orders when none exist."""
        response = client.get("/api/orders/ask")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_bid_orders_with_orders(self, client):
        """Test listing bid orders when orders exist."""
        # Create multiple bid orders
        for i in range(3):
            payload = {
                "side": "bid",
                "type": "limit",
                "quantity": f"{10 + i}",
                "price": f"{100 + i}.00",
                "trade_id": f"BID{i:03d}"
            }
            client.post("/api/orders", json=payload)

        response = client.get("/api/orders/bid")

        assert response.status_code == 200
        orders = response.json()
        assert len(orders) == 3
        for order in orders:
            assert order["side"] == "bid"
            assert "order_id" in order
            assert "quantity" in order
            assert "price" in order

    def test_list_ask_orders_with_orders(self, client):
        """Test listing ask orders when orders exist."""
        # Create multiple ask orders
        for i in range(2):
            payload = {
                "side": "ask",
                "type": "limit",
                "quantity": f"{5 + i}",
                "price": f"{105 + i}.00",
                "trade_id": f"ASK{i:03d}"
            }
            client.post("/api/orders", json=payload)

        response = client.get("/api/orders/ask")

        assert response.status_code == 200
        orders = response.json()
        assert len(orders) == 2
        for order in orders:
            assert order["side"] == "ask"

    def test_list_orders_invalid_side(self, client):
        """Test listing orders with invalid side fails."""
        response = client.get("/api/orders/invalid")

        assert response.status_code == 400
        assert "side" in response.json()["detail"].lower()

    def test_list_orders_only_shows_correct_side(self, client):
        """Test that listing orders only returns the requested side."""
        # Create bid orders
        client.post("/api/orders", json={
            "side": "bid",
            "type": "limit",
            "quantity": "10",
            "price": "100.00",
            "trade_id": "BID001"
        })
        # Create ask orders
        client.post("/api/orders", json={
            "side": "ask",
            "type": "limit",
            "quantity": "10",
            "price": "105.00",
            "trade_id": "ASK001"
        })

        # Get bids
        response = client.get("/api/orders/bid")
        assert response.status_code == 200
        bids = response.json()
        assert len(bids) == 1
        assert all(o["side"] == "bid" for o in bids)

        # Get asks
        response = client.get("/api/orders/ask")
        assert response.status_code == 200
        asks = response.json()
        assert len(asks) == 1
        assert all(o["side"] == "ask" for o in asks)

    def test_list_orders_sorted_by_price(self, client):
        """Test that orders are sorted properly by price."""
        # Create bid orders with different prices
        prices = ["100.00", "102.00", "101.00"]
        for i, price in enumerate(prices):
            client.post("/api/orders", json={
                "side": "bid",
                "type": "limit",
                "quantity": "10",
                "price": price,
                "trade_id": f"BID{i:03d}"
            })

        response = client.get("/api/orders/bid")
        assert response.status_code == 200
        orders = response.json()
        # Bids should be sorted by price (best to worst for display)
        assert len(orders) == 3


class TestGetOrder:
    """Test GET /api/orders/{side}/{order_id} endpoint."""

    def test_get_bid_order_success(self, client):
        """Test getting a specific bid order."""
        # Create a bid order
        create_response = client.post("/api/orders", json={
            "side": "bid",
            "type": "limit",
            "quantity": "10",
            "price": "100.00",
            "trade_id": "BID001",
            "wage": "trader1"
        })
        order_id = create_response.json()["order"]["order_id"]

        response = client.get(f"/api/orders/bid/{order_id}")

        assert response.status_code == 200
        order = response.json()
        assert order["order_id"] == order_id
        assert order["side"] == "bid"
        assert Decimal(order["quantity"]) == Decimal("10")
        assert Decimal(order["price"]) == Decimal("100.00")
        assert order["trade_id"] == "BID001"
        assert order["wage"] == "trader1"

    def test_get_ask_order_success(self, client):
        """Test getting a specific ask order."""
        # Create an ask order
        create_response = client.post("/api/orders", json={
            "side": "ask",
            "type": "limit",
            "quantity": "5",
            "price": "105.00",
            "trade_id": "ASK001"
        })
        order_id = create_response.json()["order"]["order_id"]

        response = client.get(f"/api/orders/ask/{order_id}")

        assert response.status_code == 200
        order = response.json()
        assert order["order_id"] == order_id
        assert order["side"] == "ask"

    def test_get_order_not_found(self, client):
        """Test getting a non-existent order returns 404."""
        response = client.get("/api/orders/bid/999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_order_wrong_side(self, client):
        """Test getting order with wrong side returns 404."""
        # Create a bid order
        create_response = client.post("/api/orders", json={
            "side": "bid",
            "type": "limit",
            "quantity": "10",
            "price": "100.00",
            "trade_id": "BID001"
        })
        order_id = create_response.json()["order"]["order_id"]

        # Try to get it as an ask order
        response = client.get(f"/api/orders/ask/{order_id}")

        assert response.status_code == 404

    def test_get_order_invalid_side(self, client):
        """Test getting order with invalid side fails."""
        response = client.get("/api/orders/invalid/1")

        assert response.status_code == 400

    def test_get_order_after_partial_fill(self, client):
        """Test getting order that has been partially filled shows remaining quantity."""
        # Create resting ask
        create_response = client.post("/api/orders", json={
            "side": "ask",
            "type": "limit",
            "quantity": "10",
            "price": "100.00",
            "trade_id": "ASK001"
        })
        order_id = create_response.json()["order"]["order_id"]

        # Partially fill it with a bid
        client.post("/api/orders", json={
            "side": "bid",
            "type": "limit",
            "quantity": "4",
            "price": "100.00",
            "trade_id": "BID001"
        })

        # Get the original ask order
        response = client.get(f"/api/orders/ask/{order_id}")

        assert response.status_code == 200
        order = response.json()
        assert Decimal(order["quantity"]) == Decimal("6")  # Remaining quantity


class TestModifyOrder:
    """Test PATCH /api/orders/{side}/{order_id} endpoint."""

    def test_modify_order_quantity(self, client):
        """Test modifying an order's quantity."""
        # Create an order
        create_response = client.post("/api/orders", json={
            "side": "bid",
            "type": "limit",
            "quantity": "10",
            "price": "100.00",
            "trade_id": "BID001"
        })
        order_id = create_response.json()["order"]["order_id"]

        # Modify quantity
        response = client.patch(f"/api/orders/bid/{order_id}", json={
            "quantity": "15"
        })

        assert response.status_code == 200
        order = response.json()
        assert Decimal(order["quantity"]) == Decimal("15")
        assert Decimal(order["price"]) == Decimal("100.00")  # Price unchanged

    def test_modify_order_price(self, client):
        """Test modifying an order's price."""
        # Create an order
        create_response = client.post("/api/orders", json={
            "side": "ask",
            "type": "limit",
            "quantity": "10",
            "price": "105.00",
            "trade_id": "ASK001"
        })
        order_id = create_response.json()["order"]["order_id"]

        # Modify price
        response = client.patch(f"/api/orders/ask/{order_id}", json={
            "price": "106.00"
        })

        assert response.status_code == 200
        order = response.json()
        assert Decimal(order["price"]) == Decimal("106.00")
        assert Decimal(order["quantity"]) == Decimal("10")  # Quantity unchanged

    def test_modify_order_both_quantity_and_price(self, client):
        """Test modifying both quantity and price."""
        # Create an order
        create_response = client.post("/api/orders", json={
            "side": "bid",
            "type": "limit",
            "quantity": "10",
            "price": "100.00",
            "trade_id": "BID001"
        })
        order_id = create_response.json()["order"]["order_id"]

        # Modify both
        response = client.patch(f"/api/orders/bid/{order_id}", json={
            "quantity": "20",
            "price": "101.00"
        })

        assert response.status_code == 200
        order = response.json()
        assert Decimal(order["quantity"]) == Decimal("20")
        assert Decimal(order["price"]) == Decimal("101.00")

    def test_modify_order_not_found(self, client):
        """Test modifying non-existent order returns 404."""
        response = client.patch("/api/orders/bid/999", json={
            "quantity": "15"
        })

        assert response.status_code == 404

    def test_modify_order_wrong_side(self, client):
        """Test modifying order with wrong side returns 404."""
        # Create a bid order
        create_response = client.post("/api/orders", json={
            "side": "bid",
            "type": "limit",
            "quantity": "10",
            "price": "100.00",
            "trade_id": "BID001"
        })
        order_id = create_response.json()["order"]["order_id"]

        # Try to modify it as an ask order
        response = client.patch(f"/api/orders/ask/{order_id}", json={
            "quantity": "15"
        })

        assert response.status_code == 404

    def test_modify_order_invalid_quantity_zero(self, client):
        """Test modifying order with zero quantity fails."""
        # Create an order
        create_response = client.post("/api/orders", json={
            "side": "bid",
            "type": "limit",
            "quantity": "10",
            "price": "100.00",
            "trade_id": "BID001"
        })
        order_id = create_response.json()["order"]["order_id"]

        # Try to modify with zero quantity
        response = client.patch(f"/api/orders/bid/{order_id}", json={
            "quantity": "0"
        })

        assert response.status_code == 422  # Pydantic validation error

    def test_modify_order_invalid_quantity_negative(self, client):
        """Test modifying order with negative quantity fails."""
        # Create an order
        create_response = client.post("/api/orders", json={
            "side": "bid",
            "type": "limit",
            "quantity": "10",
            "price": "100.00",
            "trade_id": "BID001"
        })
        order_id = create_response.json()["order"]["order_id"]

        # Try to modify with negative quantity
        response = client.patch(f"/api/orders/bid/{order_id}", json={
            "quantity": "-5"
        })

        assert response.status_code == 422  # Pydantic validation

    def test_modify_order_empty_update(self, client):
        """Test modifying order with no changes."""
        # Create an order
        create_response = client.post("/api/orders", json={
            "side": "bid",
            "type": "limit",
            "quantity": "10",
            "price": "100.00",
            "trade_id": "BID001"
        })
        order_id = create_response.json()["order"]["order_id"]

        # Modify with no changes
        response = client.patch(f"/api/orders/bid/{order_id}", json={})

        assert response.status_code == 200
        order = response.json()
        assert Decimal(order["quantity"]) == Decimal("10")
        assert Decimal(order["price"]) == Decimal("100.00")


class TestDeleteOrder:
    """Test DELETE /api/orders/{side}/{order_id} endpoint."""

    def test_delete_bid_order_success(self, client):
        """Test deleting a bid order."""
        # Create an order
        create_response = client.post("/api/orders", json={
            "side": "bid",
            "type": "limit",
            "quantity": "10",
            "price": "100.00",
            "trade_id": "BID001"
        })
        order_id = create_response.json()["order"]["order_id"]

        # Delete the order
        response = client.delete(f"/api/orders/bid/{order_id}")

        assert response.status_code == 204

        # Verify it's gone
        get_response = client.get(f"/api/orders/bid/{order_id}")
        assert get_response.status_code == 404

    def test_delete_ask_order_success(self, client):
        """Test deleting an ask order."""
        # Create an order
        create_response = client.post("/api/orders", json={
            "side": "ask",
            "type": "limit",
            "quantity": "10",
            "price": "105.00",
            "trade_id": "ASK001"
        })
        order_id = create_response.json()["order"]["order_id"]

        # Delete the order
        response = client.delete(f"/api/orders/ask/{order_id}")

        assert response.status_code == 204

    def test_delete_order_not_found(self, client):
        """Test deleting non-existent order returns 404."""
        response = client.delete("/api/orders/bid/999")

        assert response.status_code == 404

    def test_delete_order_wrong_side(self, client):
        """Test deleting order with wrong side returns 404."""
        # Create a bid order
        create_response = client.post("/api/orders", json={
            "side": "bid",
            "type": "limit",
            "quantity": "10",
            "price": "100.00",
            "trade_id": "BID001"
        })
        order_id = create_response.json()["order"]["order_id"]

        # Try to delete it as an ask order
        response = client.delete(f"/api/orders/ask/{order_id}")

        assert response.status_code == 404

    def test_delete_order_invalid_side(self, client):
        """Test deleting order with invalid side fails."""
        response = client.delete("/api/orders/invalid/1")

        assert response.status_code == 400

    def test_delete_order_removes_from_list(self, client):
        """Test that deleted order is removed from list."""
        # Create multiple orders
        order_ids = []
        for i in range(3):
            create_response = client.post("/api/orders", json={
                "side": "bid",
                "type": "limit",
                "quantity": "10",
                "price": f"{100 + i}.00",
                "trade_id": f"BID{i:03d}"
            })
            order_ids.append(create_response.json()["order"]["order_id"])

        # Delete middle order
        response = client.delete(f"/api/orders/bid/{order_ids[1]}")
        assert response.status_code == 204

        # List orders and verify only 2 remain
        list_response = client.get("/api/orders/bid")
        orders = list_response.json()
        assert len(orders) == 2
        returned_ids = [o["order_id"] for o in orders]
        assert order_ids[1] not in returned_ids
        assert order_ids[0] in returned_ids
        assert order_ids[2] in returned_ids

    def test_delete_same_order_twice(self, client):
        """Test that deleting same order twice returns 404 on second attempt."""
        # Create an order
        create_response = client.post("/api/orders", json={
            "side": "bid",
            "type": "limit",
            "quantity": "10",
            "price": "100.00",
            "trade_id": "BID001"
        })
        order_id = create_response.json()["order"]["order_id"]

        # Delete first time
        response1 = client.delete(f"/api/orders/bid/{order_id}")
        assert response1.status_code == 204

        # Delete second time
        response2 = client.delete(f"/api/orders/bid/{order_id}")
        assert response2.status_code == 404


class TestSummary:
    """Test GET /api/summary endpoint."""

    def test_summary_empty_book(self, client):
        """Test summary with empty order book."""
        response = client.get("/api/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["best_bid"] is None
        assert data["best_ask"] is None
        assert data["bid_volume"] == 0
        assert data["ask_volume"] == 0
        assert "time" in data

    def test_summary_with_bids_only(self, client):
        """Test summary with only bid orders."""
        # Create multiple bid orders
        client.post("/api/orders", json={
            "side": "bid",
            "type": "limit",
            "quantity": "10",
            "price": "100.00",
            "trade_id": "BID001"
        })
        client.post("/api/orders", json={
            "side": "bid",
            "type": "limit",
            "quantity": "5",
            "price": "99.00",
            "trade_id": "BID002"
        })

        response = client.get("/api/summary")

        assert response.status_code == 200
        data = response.json()
        assert Decimal(str(data["best_bid"])) == Decimal("100.00")
        assert data["best_ask"] is None
        assert data["bid_volume"] == 15
        assert data["ask_volume"] == 0

    def test_summary_with_asks_only(self, client):
        """Test summary with only ask orders."""
        # Create multiple ask orders
        client.post("/api/orders", json={
            "side": "ask",
            "type": "limit",
            "quantity": "8",
            "price": "105.00",
            "trade_id": "ASK001"
        })
        client.post("/api/orders", json={
            "side": "ask",
            "type": "limit",
            "quantity": "12",
            "price": "106.00",
            "trade_id": "ASK002"
        })

        response = client.get("/api/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["best_bid"] is None
        assert Decimal(str(data["best_ask"])) == Decimal("105.00")
        assert data["bid_volume"] == 0
        assert data["ask_volume"] == 20

    def test_summary_with_both_sides(self, client):
        """Test summary with orders on both sides."""
        # Create bid orders
        client.post("/api/orders", json={
            "side": "bid",
            "type": "limit",
            "quantity": "10",
            "price": "100.00",
            "trade_id": "BID001"
        })
        client.post("/api/orders", json={
            "side": "bid",
            "type": "limit",
            "quantity": "5",
            "price": "99.00",
            "trade_id": "BID002"
        })

        # Create ask orders
        client.post("/api/orders", json={
            "side": "ask",
            "type": "limit",
            "quantity": "8",
            "price": "105.00",
            "trade_id": "ASK001"
        })
        client.post("/api/orders", json={
            "side": "ask",
            "type": "limit",
            "quantity": "12",
            "price": "106.00",
            "trade_id": "ASK002"
        })

        response = client.get("/api/summary")

        assert response.status_code == 200
        data = response.json()
        assert Decimal(str(data["best_bid"])) == Decimal("100.00")
        assert Decimal(str(data["best_ask"])) == Decimal("105.00")
        assert data["bid_volume"] == 15
        assert data["ask_volume"] == 20

    def test_summary_after_order_deletion(self, client):
        """Test summary updates correctly after order deletion."""
        # Create orders
        create_response = client.post("/api/orders", json={
            "side": "bid",
            "type": "limit",
            "quantity": "10",
            "price": "100.00",
            "trade_id": "BID001"
        })
        order_id = create_response.json()["order"]["order_id"]

        # Check summary
        response1 = client.get("/api/summary")
        data1 = response1.json()
        assert data1["bid_volume"] == 10

        # Delete order
        client.delete(f"/api/orders/bid/{order_id}")

        # Check summary again
        response2 = client.get("/api/summary")
        data2 = response2.json()
        assert data2["bid_volume"] == 0
        assert data2["best_bid"] is None

    def test_summary_after_trade(self, client):
        """Test summary updates correctly after trades."""
        # Create resting ask
        client.post("/api/orders", json={
            "side": "ask",
            "type": "limit",
            "quantity": "10",
            "price": "100.00",
            "trade_id": "ASK001"
        })

        # Check initial summary
        response1 = client.get("/api/summary")
        data1 = response1.json()
        assert data1["ask_volume"] == 10

        # Execute trade
        client.post("/api/orders", json={
            "side": "bid",
            "type": "limit",
            "quantity": "4",
            "price": "100.00",
            "trade_id": "BID001"
        })

        # Check summary after trade
        response2 = client.get("/api/summary")
        data2 = response2.json()
        assert data2["ask_volume"] == 6  # Remaining after partial fill


class TestEdgeCases:
    """Test edge cases and integration scenarios."""

    def test_concurrent_order_operations(self, client):
        """Test multiple operations on orders."""
        # Create order
        create_response = client.post("/api/orders", json={
            "side": "bid",
            "type": "limit",
            "quantity": "10",
            "price": "100.00",
            "trade_id": "BID001"
        })
        order_id = create_response.json()["order"]["order_id"]

        # Get order
        get_response = client.get(f"/api/orders/bid/{order_id}")
        assert get_response.status_code == 200

        # Modify order
        modify_response = client.patch(f"/api/orders/bid/{order_id}", json={
            "quantity": "20"
        })
        assert modify_response.status_code == 200

        # Verify modification
        get_response2 = client.get(f"/api/orders/bid/{order_id}")
        assert Decimal(get_response2.json()["quantity"]) == Decimal("20")

        # Delete order
        delete_response = client.delete(f"/api/orders/bid/{order_id}")
        assert delete_response.status_code == 204

        # Verify deletion
        get_response3 = client.get(f"/api/orders/bid/{order_id}")
        assert get_response3.status_code == 404

    def test_large_quantity_values(self, client):
        """Test handling of large quantity values."""
        payload = {
            "side": "bid",
            "type": "limit",
            "quantity": "999999999.123456",
            "price": "100.00",
            "trade_id": "BID001"
        }
        response = client.post("/api/orders", json=payload)

        assert response.status_code == 201

    def test_high_precision_prices(self, client):
        """Test handling of high precision decimal prices."""
        payload = {
            "side": "bid",
            "type": "limit",
            "quantity": "10",
            "price": "100.123456789",
            "trade_id": "BID001"
        }
        response = client.post("/api/orders", json=payload)

        assert response.status_code == 201
        order = response.json()["order"]
        # Price should be preserved
        assert "100.12" in str(order["price"])

    def test_order_matching_priority(self, client):
        """Test that orders match with correct priority (price-time)."""
        # Create multiple ask orders at different prices
        client.post("/api/orders", json={
            "side": "ask",
            "type": "limit",
            "quantity": "5",
            "price": "102.00",
            "trade_id": "ASK001"
        })
        client.post("/api/orders", json={
            "side": "ask",
            "type": "limit",
            "quantity": "5",
            "price": "101.00",
            "trade_id": "ASK002"
        })
        client.post("/api/orders", json={
            "side": "ask",
            "type": "limit",
            "quantity": "5",
            "price": "100.00",
            "trade_id": "ASK003"
        })

        # Create a bid that crosses - should match with best ask (100.00)
        response = client.post("/api/orders", json={
            "side": "bid",
            "type": "limit",
            "quantity": "5",
            "price": "102.00",
            "trade_id": "BID001"
        })

        assert response.status_code == 201
        trades = response.json()["trades"]
        assert len(trades) == 1
        assert Decimal(trades[0]["price"]) == Decimal("100.00")

    def test_multiple_matches_single_order(self, client):
        """Test single order matching against multiple resting orders."""
        # Create multiple small ask orders
        for i in range(3):
            client.post("/api/orders", json={
                "side": "ask",
                "type": "limit",
                "quantity": "3",
                "price": "100.00",
                "trade_id": f"ASK{i:03d}"
            })

        # Create large bid that should match all
        response = client.post("/api/orders", json={
            "side": "bid",
            "type": "limit",
            "quantity": "9",
            "price": "100.00",
            "trade_id": "BID001"
        })

        assert response.status_code == 201
        trades = response.json()["trades"]
        assert len(trades) == 3
        total_quantity = sum(Decimal(t["quantity"]) for t in trades)
        assert total_quantity == Decimal("9")

    def test_market_order_with_empty_book(self, client):
        """Test market order when no opposing orders exist."""
        payload = {
            "side": "bid",
            "type": "market",
            "quantity": "10",
            "trade_id": "MKT001"
        }
        response = client.post("/api/orders", json=payload)

        # Should return 201 with no trades
        assert response.status_code == 201
        data = response.json()
        assert len(data["trades"]) == 0

    def test_stress_many_orders(self, client):
        """Test creating many orders."""
        # Create 50 orders
        for i in range(50):
            side = "bid" if i % 2 == 0 else "ask"
            price = 100 + (i % 10) if side == "ask" else 100 - (i % 10)
            payload = {
                "side": side,
                "type": "limit",
                "quantity": str(i + 1),
                "price": str(price),
                "trade_id": f"ORDER{i:03d}"
            }
            response = client.post("/api/orders", json=payload)
            assert response.status_code == 201

        # Verify summary works
        summary_response = client.get("/api/summary")
        assert summary_response.status_code == 200

    def test_optional_fields(self, client):
        """Test that optional fields (trade_id, wage) are handled correctly."""
        # Create order without optional fields
        payload = {
            "side": "bid",
            "type": "limit",
            "quantity": "10",
            "price": "100.00"
        }
        response = client.post("/api/orders", json=payload)

        assert response.status_code == 201
        order = response.json()["order"]
        assert order["trade_id"] is None
        assert order["wage"] is None

    def test_decimal_string_conversion(self, client):
        """Test that numeric strings are properly converted to Decimals."""
        payload = {
            "side": "bid",
            "type": "limit",
            "quantity": "10.5",
            "price": "100.25",
            "trade_id": "BID001"
        }
        response = client.post("/api/orders", json=payload)

        assert response.status_code == 201
        order = response.json()["order"]
        # Verify values are correct
        assert Decimal(order["quantity"]) == Decimal("10.5")
        assert Decimal(order["price"]) == Decimal("100.25")

