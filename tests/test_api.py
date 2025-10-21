from decimal import Decimal
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_limit_order_crud():
    # Create limit order
    resp = client.post(
        "/api/orders",
        json={"side": "bid", "type": "limit", "quantity": "5", "price": "100", "trade_id": "T1"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["order"] is not None
    order_id = body["order"]["order_id"]

    # Get order
    get_resp = client.get(f"/api/orders/bid/{order_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["order_id"] == order_id

    # Modify order quantity
    patch_resp = client.patch(f"/api/orders/bid/{order_id}", json={"quantity": "7"})
    assert patch_resp.status_code == 200
    patched = patch_resp.json()
    # Quantity may be serialized as number or string depending on pydantic version
    assert Decimal(str(patched["quantity"])) == Decimal("7")

    # List orders
    list_resp = client.get("/api/orders/bid")
    assert list_resp.status_code == 200
    assert any(o["order_id"] == order_id for o in list_resp.json())

    # Delete order
    del_resp = client.delete(f"/api/orders/bid/{order_id}")
    assert del_resp.status_code == 204

    # Ensure gone
    missing_resp = client.get(f"/api/orders/bid/{order_id}")
    assert missing_resp.status_code == 404


def test_market_order_execution():
    # Create ask limit order so market bid can match
    limit_resp = client.post(
        "/api/orders",
        json={"side": "ask", "type": "limit", "quantity": "3", "price": "101", "trade_id": "A1"},
    )
    assert limit_resp.status_code == 201

    # Market bid should trade against ask
    market_resp = client.post(
        "/api/orders",
        json={"side": "bid", "type": "market", "quantity": "2", "trade_id": "MB1"},
    )
    assert market_resp.status_code == 201
    data = market_resp.json()
    assert data["order"] is None  # market order not retained
    assert len(data["trades"]) >= 1
    trade = data["trades"][0]
    assert trade["party2"]["trade_id"] == "MB1"  # party2 is incoming order


def test_summary_endpoint():
    resp = client.get("/api/summary")
    assert resp.status_code == 200
    summary = resp.json()
    assert "bid_volume" in summary and "ask_volume" in summary


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

