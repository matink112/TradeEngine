# TradeEngine

A lightweight, high-performance in-memory limit order book implementation with a FastAPI HTTP interface. This trading engine supports limit and market orders with price-time priority matching, real-time trade analytics, and OHLC data generation.

## Features

- **Order Types**: Support for limit and market orders (bid/ask)
- **Matching Engine**: Price-time priority matching algorithm
- **Real-time Analytics**: OHLC (Open, High, Low, Close) data, price changes, and trade history
- **RESTful API**: FastAPI-based HTTP interface with automatic OpenAPI documentation
- **Efficient Data Structures**: Uses sorted containers for O(log n) price-level operations
- **Trade Recording**: Comprehensive trade event tracking with pandas DataFrames
- **Chart Generation**: Automatic trade chart generation using matplotlib

## Technology Stack

- **Python** >= 3.13
- **FastAPI** - Modern web framework for building APIs
- **Pydantic** - Data validation using Python type annotations
- **sortedcontainers** - High-performance sorted collections
- **pandas** - Trade data analytics and manipulation
- **matplotlib** - Chart generation
- **pytest** - Testing framework
- **uvicorn** - ASGI server

## Installation

### Prerequisites

- Python 3.13 or higher
- [uv](https://github.com/astral-sh/uv) package manager (recommended) or pip

### Using uv (Recommended)

```bash
# Install dependencies
make install

# Or sync with lock file
make sync
```

### Using pip

```bash
pip install -r requirements.txt
```

## Quick Start

### Running the Server

```bash
# Development mode with auto-reload
make dev

# Or production mode
make run

# Or manually with uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

### API Documentation

Once the server is running, access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

All endpoints are prefixed with `/api`

### Create Order
```http
POST /api/orders
```
Create and process a limit or market order.

**Request Body:**
```json
{
  "side": "bid",
  "type": "limit",
  "quantity": 100.0,
  "price": 50.5,
  "trade_id": "optional-external-id",
  "wage": "optional-wage-field"
}
```

**Response:**
```json
{
  "trades": [
    {
      "timestamp": 1,
      "price": 50.5,
      "quantity": 50.0,
      "party1": {"trade_id": "seller-1", "side": "ask", "order_id": 1},
      "party2": {"trade_id": "buyer-1", "side": "bid", "order_id": 2}
    }
  ],
  "order": {
    "order_id": 2,
    "side": "bid",
    "quantity": 50.0,
    "price": 50.5,
    "timestamp": 1,
    "trade_id": "optional-external-id",
    "wage": null
  }
}
```

### List Orders
```http
GET /api/orders/{side}
```
List all resting orders on a given side (bid or ask).

### Get Order
```http
GET /api/orders/{side}/{order_id}
```
Retrieve a specific order by side and order ID.

### Modify Order
```http
PATCH /api/orders/{side}/{order_id}
```
Modify the quantity and/or price of an existing order.

**Request Body:**
```json
{
  "quantity": 150.0,
  "price": 51.0
}
```

### Cancel Order
```http
DELETE /api/orders/{side}/{order_id}
```
Remove an order from the book.

### Get Market Summary
```http
GET /api/summary
```
Get current market summary including best bid/ask prices and volumes.

**Response:**
```json
{
  "best_bid": 50.0,
  "best_ask": 51.0,
  "bid_volume": 1000.0,
  "ask_volume": 800.0,
  "num_bids": 5,
  "num_asks": 3
}
```

### Health Check
```http
GET /health
```
Simple health check endpoint.

## Architecture

### Core Components

#### OrderBook
The main orchestrator that manages the matching engine. Contains separate order trees for bids and asks, coordinates order matching, and maintains trade history.

#### OrderTree
Price-ordered collection using `SortedDict` that maps price levels to order lists. Provides O(log n) price navigation and O(1) order lookup.

#### OrderList
Doubly-linked list maintaining FIFO order of all orders at a specific price level. Ensures time-priority ordering.

#### Order
Individual order node in the linked list containing order details (price, quantity, timestamp, order_id).

#### TradeDataFrame
Pandas-based trade record storage providing analytics capabilities including OHLC sampling, price change calculations, and chart generation.

### Matching Algorithm

1. **Order Reception**: Incoming orders are normalized (quantities and prices converted to Decimal)
2. **Order ID Assignment**: Internal order_id and timestamp assigned
3. **Market Orders**: Consume opposite side best prices until filled or book exhausted (never rest in book)
4. **Limit Orders**: 
   - First, match against opposite side while price crosses the spread
   - Consume orders in FIFO order at each price level
   - Any remaining quantity rests in the order book
5. **Trade Generation**: Each match creates a trade record with party1 (resting) and party2 (aggressor)
6. **Order Updates**: Partially filled orders have quantity reduced; fully filled orders are removed

### Time & Priority

- `OrderBook.time` increments for each operation (order processing, modifications, cancellations)
- Orders at the same price level are prioritized by timestamp (FIFO)
- Increasing quantity during modification moves the order to the end of the queue (loses time priority)

## Development

### Running Tests

```bash
# Run all tests
make test

# Run tests with coverage
make test-cov

# Run tests with verbose output
make test-verbose
```

### Code Quality

```bash
# Run linter
make lint

# Format code
make format

# Run lint and tests
make check
```

### Project Structure

```
TradeEngine/
├── main.py                 # FastAPI application entry point
├── conf.py                 # Configuration (output directories)
├── src/
│   ├── api/
│   │   ├── __init__.py    # API router and endpoints
│   │   └── schemas.py     # Pydantic models for validation
│   ├── orderbook/
│   │   ├── orderbook.py   # Main OrderBook class
│   │   ├── ordertree.py   # Price-level container
│   │   ├── orderlist.py   # Time-priority linked list
│   │   ├── order.py       # Individual order node
│   │   └── trade.py       # Trade analytics and storage
│   └── exceptions.py      # Custom exception types
├── tests/                  # Test suite
│   ├── api/
│   └── orderbook/
├── Makefile               # Development commands
├── pyproject.toml         # Project metadata and dependencies
└── README.md              # This file
```

## Error Handling

The API returns standardized error responses:

- **400 Bad Request**: Invalid order parameters (negative quantity, invalid side/type)
- **404 Not Found**: Order not found
- **422 Unprocessable Entity**: Validation errors (e.g., missing price for limit order)

Example error response:
```json
{
  "detail": "Order not found: side=bid, order_id=999"
}
```

## Limitations

- **In-Memory Only**: No persistence; all data is lost when the process terminates
- **Single Market**: Currently supports only one market pair per process
- **No Authentication**: No user authentication or authorization
- **No Multi-Threading**: Single-threaded execution model

## Use Cases

- **Educational**: Learn about order book mechanics and matching engines
- **Testing**: Test trading strategies against a realistic order book
- **Prototyping**: Rapid prototyping of trading systems
- **Backtesting**: Historical trade replay and analysis


