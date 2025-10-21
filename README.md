# TradeEngine (FastAPI Limit Order Book)

In-memory limit order book with a lightweight REST API for experimenting with order matching, trade event capture, and simple market analytics.

## Key Features
- Limit & market orders (bid / ask)
- Price/time priority matching (FIFO within price level)
- Trade recording (price, volume, side) with pandas
- Basic analytics: OHLC sampling, percentage changes, 24h synthetic kline export
- Clean FastAPI endpoints for CRUD + summary
- Ready for extension (multi-market, persistence, auth)

## Technology Stack
Python 3.13+, FastAPI, Pydantic, sortedcontainers, pandas, matplotlib, uvicorn, pytest.

## Quick Start
```bash
# Install (editable for development)
pip install -e .

# Run API
uvicorn main:app --reload

# Health check
curl http://localhost:8000/health

# Place limit order
curl -X POST http://localhost:8000/api/orders \
  -H 'Content-Type: application/json' \
  -d '{"side":"bid","type":"limit","quantity":"5","price":"100","trade_id":"ABC"}'

# Place market order (no price)
curl -X POST http://localhost:8000/api/orders \
  -H 'Content-Type: application/json' \
  -d '{"side":"ask","type":"market","quantity":"2"}'

# Summary
curl http://localhost:8000/api/summary
```

## Project Layout
```
main.py               # FastAPI app & /health
src/api/              # Routers + schemas
src/orderbook/        # Matching engine + data structures
conf.py               # RESULT_DIR constant
llm-context.md        # High-signal context for LLMs
```

## Endpoints (Prefix /api)
- POST /orders : process limit/market order -> trades + optional resting order
- GET /orders/{side} : list resting orders ("bid" or "ask")
- GET /orders/{side}/{order_id} : fetch single order
- PATCH /orders/{side}/{order_id} : modify quantity/price
- DELETE /orders/{side}/{order_id} : cancel
- GET /summary : best bid/ask + volumes + time
- GET /health (root) : service status

## Testing
```bash
pytest -q
```

## LLM Usage
See `llm-context.md` for authoritative architectural, data model, and reasoning guidance when generating code or answering questions.

## Extensibility Ideas
- Persistence layer (database or event sourcing)
- Multi-market registry & per-symbol isolation
- Authentication / user attribution via trade_id
- Advanced analytics (VWAP, depth snapshots, latency metrics)

## Notes
- All state is in memory; restart clears book & trades.
- Decimal logic retained for matching precision; analytics cast to float for pandas.
- Synthetic zero trade row exists (TODO removal) to avoid empty DataFrame edge cases.

## License
No license specified. Add one before external distribution.

