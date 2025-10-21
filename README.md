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


## Limitations

- **In-Memory Only**: No persistence; all data is lost when the process terminates
- **Single Market**: Currently supports only one market pair per process
- **No Authentication**: No user authentication or authorization
- **No Multi-Threading**: Single-threaded execution model


## Future Roadmap

The following enhancements are planned to evolve TradeEngine into a production-grade trading system:

### 1. CAP Server with Sequencer Architecture

Replace the REST API with a CAP (Client Application Protocol) server implementing a sequencer architecture for deterministic order processing:

- **Sequencer**: Central component that assigns monotonically increasing sequence numbers to all incoming orders
- **Deterministic Execution**: Guaranteed order processing sequence regardless of arrival time variance
- **Total Order Broadcast**: All nodes receive and process orders in the same sequence
- **Benefits**: 
  - Ultra-low latency (microsecond range)
  - Eliminates race conditions in distributed scenarios
  - Supports replay and recovery from sequence logs
  - Better suited for high-frequency trading

### 2. Metrics & Observability

Implement comprehensive monitoring and metrics exposure:

- **Prometheus Metrics**: 
  - Order processing latency (p50, p95, p99)
  - Throughput (orders/sec, trades/sec)
  - Order book depth at various price levels
  - Match rate and fill ratios
  - Queue depths and processing times
- **Health Checks**: Enhanced health endpoints with dependency checks
- **Tracing**: Distributed tracing with OpenTelemetry for order lifecycle tracking
- **Performance Profiling**: Built-in profiling endpoints for production debugging

### 3. Real-time Event Streaming

Integrate message broker for real-time order book events and market data distribution:

- **Kafka Integration**: 
  - Publish trade executions to dedicated topics
  - Stream order book snapshots and deltas
  - Level 2 market data feeds (full depth)
  - Level 1 market data (best bid/ask, last trade)
- **Event Types**:
  - `OrderCreated`, `OrderModified`, `OrderCancelled`
  - `TradeExecuted` with full match details
  - `OrderBookSnapshot` at configurable intervals
  - `PriceLevelUpdate` for depth changes
- **Consumer Support**: Multiple consumers can subscribe to different event streams
- **Event Sourcing**: Complete audit trail of all order book state changes

### 4. Multi-Market Support

Extend the system to handle multiple trading pairs simultaneously:

- **Market Registry**: Central registry for managing multiple order books
- **Symbol Management**: Support for various trading pairs (BTC/USD, ETH/USD, etc.)
- **Market-Specific Configuration**: 
  - Custom tick sizes per market
  - Trading hours and circuit breakers
- **Cross-Market Analytics**: Aggregated statistics across all markets
- **Market Isolation**: Independent order books with no cross-contamination
- **Dynamic Market Creation**: Runtime addition/removal of markets

### 5. Concurrent Processing Across Multi-Market

Enable parallel processing for improved throughput:

- **Lock-Free Design**: Per-market order books operate independently
- **Work Stealing**: Load balancing across markets during high activity periods
- **NUMA-Aware Scheduling**: CPU affinity for optimal cache utilization
- **Shared-Nothing Architecture**: Each market runs in isolation to avoid contention
- **Benefits**:
  - Linear scalability with number of markets
  - No global locks or serialization points

### 6. Cythonization & Performance Optimization

Compile performance-critical paths to native code:

- **Cython Compilation**:
  - OrderBook matching engine compiled to C
  - OrderTree and OrderList operations
  - Price level traversal and order matching logic
- **Expected Performance Gains**:
  - 10-50x faster order processing
  - Reduced memory allocations
  - Better CPU cache utilization
- **Hybrid Approach**: Keep API layer in Python, optimize core matching engine
- **Type Annotations**: Static typing for optimal C code generation
- **Profiling-Guided Optimization**: Focus on hot paths identified through profiling

### 7. Additional Planned Features

- **Persistence Layer**: 
  - PostgreSQL/TimescaleDB for historical trade data
  - Redis for order book snapshots and fast recovery
  - Write-ahead logging (WAL) for crash recovery
  
- **Advanced Order Types**:
  - Stop-loss and take-profit orders
  - Iceberg orders (hidden liquidity)
  - Time-in-force options (IOC, FOK, GTC, GTD)
  - Post-only orders (maker-only)
  
- **Authentication & Authorization**:
  - API key management
  
- **Market Data APIs**:
  - Historical OHLCV data export
  - Trade tape downloads
  - Order book replay functionality
  - Market depth charts and visualization

### 8. Infrastructure & Deployment

- **Containerization**: Docker images with optimized builds
- **Kubernetes**: Deployment manifests for cloud-native orchestration
- **Service Mesh**: Istio integration for traffic management
- **Auto-scaling**: Horizontal scaling based on order flow
- **Multi-region Deployment**: Geographic distribution for low latency
- **Disaster Recovery**: Automated backup and failover mechanisms


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


## Technology Stack

- **Python** >= 3.13
- **FastAPI** - Modern web framework for building APIs
- **Pydantic** - Data validation using Python type annotations
- **sortedcontainers** - High-performance sorted collections
- **pandas** - Trade data analytics and manipulation
- **matplotlib** - Chart generation
- **pytest** - Testing framework
- **uvicorn** - ASGI server


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

## Use Cases

- **Educational**: Learn about order book mechanics and matching engines
- **Testing**: Test trading strategies against a realistic order book
- **Prototyping**: Rapid prototyping of trading systems
- **Backtesting**: Historical trade replay and analysis


## Contributing

Contributions are welcome! Please ensure:

1. All tests pass: `make test`
2. Code is formatted: `make format`
3. Linting passes: `make lint`
