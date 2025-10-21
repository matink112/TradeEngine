# LLM Project Context: TradeEngine

This document gives a language model all essential, high-signal knowledge about the TradeEngine codebase so it can answer questions, generate features, and reason about the system safely. Keep answers grounded in these details.

## 1. Purpose & Scope
TradeEngine is a lightweight in‑memory limit order book with a FastAPI HTTP interface. It supports:
- Limit and market orders (bid / ask)
- Matching engine with price/time priority
- Trade event recording & basic analytics (OHLC, recent trades, price changes)
- Simple summary endpoint for best bid/ask and volume

Persistence, authentication, and multi‑market management are NOT implemented (single market instance lives in memory for the life of the process).

## 2. Technology Stack
- Python >= 3.13
- FastAPI (web API)
- Pydantic (request/response schemas & validation)
- sortedcontainers (price-sorted maps)
- pandas + matplotlib (trade data analytics & simple chart generation)
- pytest + httpx/TestClient (tests)
- Uvicorn (ASGI server)

## 3. Runtime Layout
```
main.py              # FastAPI app factory & /health endpoint
src/api/__init__.py  # API router + endpoints (CRUD + matching + summary)
src/api/schemas.py   # Pydantic models (OrderCreate, OrderModify, OrderOut, TradeOut, SummaryOut)
src/orderbook/       # Core matching & data structures
  orderbook.py       # OrderBook orchestrates matching logic
  order.py           # Order node (doubly linked list element)
  orderlist.py       # OrderList (time-priority linked list per price level)
  ordertree.py       # OrderTree (price-level container using SortedDict)
  trade.py           # TradeDataFrame (analytics & file export / chart generation)
src/exceptions.py    # Domain exception types
conf.py              # RESULT_DIR constant used for chart/data output paths
```
Single global OrderBook instance: created in `src/api/__init__.py` as `book = OrderBook(market_name="TEST/PAIR")`.

## 4. Core Data Structures & Responsibilities
### Order
Represents a single limit order in a per‑price doubly-linked list.
Fields: timestamp, quantity (Decimal), price (Decimal), order_id (int), trade_id (optional external identifier), wage (aux field). Maintains `_next` and `_prev` pointers for time-priority ordering.

### OrderList
Doubly-linked list for one price level. Head = highest time priority (earliest timestamp). Supports append, remove, move_to_tail (when quantity increases losing priority). Tracks aggregate `volume` and `length`.

### OrderTree
Price-ordered collection (`SortedDict`) mapping price -> OrderList. Also keeps `order_id -> Order`. Provides O(log n) price navigation and O(1) order lookup. Volume & num_orders tracked globally.

### OrderBook
Coordinates matching. Contains two OrderTrees: `bids` and `asks`. Manages time counter (`time` increments per book event) and monotonically increasing `next_order_id` for newly created orders. Matching logic produces trade records stored in TradeDataFrame.

### TradeDataFrame
Pandas DataFrame holding sequential trades. Each append adds (price, volume, is_bid). Provides OHLC sampling, price change percentages, synthetic padding & chart export.

## 5. Matching Algorithm Overview
1. Incoming order normalized: quantity -> Decimal, price -> Decimal if limit.
2. Assign internal `order_id` and `timestamp` (book `time` increments).
3. If MARKET: iteratively consume opposite side best price list until quantity filled or book side empty. Market orders NEVER rest in book.
4. If LIMIT: attempt immediate matching while the price crosses the spread (for bids: price >= best ask; for asks: price <= best bid), consuming head orders at best price lists in FIFO order until quantity depleted or no more crossing.
5. Any remaining quantity of a LIMIT order is inserted into its side’s OrderTree.
6. Each trade generates record with party1 = resting order (original side), party2 = aggressing incoming order.
7. If a resting order partially fills, its quantity decreases; if fully filled it is removed. Increasing quantity during modification can move order to tail (lose priority).

## 6. Time & Ordering Semantics
- `OrderBook.time` increments per processed operation (`process_order`, modifications, cancellations)
- `timestamp` on orders = book time at insertion or modification
- FIFO within same price level maintained by linked list (head oldest)

## 7. API Endpoints
Base prefix: `/api`

Endpoint | Method | Purpose | Request Model | Response Model
---------|-------|---------|---------------|---------------
`/api/orders` | POST | Create and process limit/market order | OrderCreate | OrderProcessResult (trades + optional resting order)
`/api/orders/{side}` | GET | List all resting orders on side (price ascending for asks, descending for bids via iteration of sorted prices) | side path ("bid" or "ask") | List[OrderOut]
`/api/orders/{side}/{order_id}` | GET | Retrieve single order | path | OrderOut
`/api/orders/{side}/{order_id}` | PATCH | Modify quantity and/or price of existing order | OrderModify | OrderOut
`/api/orders/{side}/{order_id}` | DELETE | Cancel order | path | 204 No Content
`/api/summary` | GET | Summary best bid/ask & volumes | - | SummaryOut
`/health` | GET | Basic health check | - | {"status": "ok"}

Notes:
- MARKET order request omits price (validation enforces presence for LIMIT).
- Response quantities & prices are Decimals serialized by FastAPI/Pydantic (may appear as number or string across versions). Tests accommodate this by casting to Decimal(str(value)).

## 8. Validation & Errors
Exceptions mapped to HTTP responses via FastAPI exception handlers:
- QuantityError -> 400 (quantity <= 0)
- OrderTypeError -> 400 (invalid side or type)
- OrderNotFoundError -> 404

Client should expect standardized JSON: {"detail": "message"}.

## 9. Trade Records Structure
Each trade record (in `OrderProcessResult.trades`):
```
{
  "timestamp": <int book time>,
  "price": <Decimal>,
  "quantity": <Decimal traded>,
  "time": <int book time>,
  "party1": { trade_id, side, order_id, new_book_quantity, wage },  # resting order
  "party2": { trade_id, side, order_id, new_book_quantity: null, wage }  # incoming order
}
```
If resting order fully consumed, `new_book_quantity` is null. Otherwise shows remaining quantity after partial fill.

## 10. Invariants & Edge Cases
- Book volumes (`bids.volume`, `asks.volume`) are sum of resting order quantities (Decimal). Must remain >= 0.
- When modifying order: price change triggers removal & reinsertion at new price level (loses previous time priority). Quantity increase triggers move to tail within same price level.
- MARKET orders never produce an `order` in result (always null). LIMIT may return null if fully filled immediately (pure taker).
- If opposite side empty or price not crossing, LIMIT order rests entirely.
- Zero or negative quantity: rejected early.
- Removing last order at a price cleans up that price level from `SortedDict`.
- TradeDataFrame inserts a synthetic (0,0) initial row to avoid empty DataFrame operations (TODO noted to remove after fixing related bug). LLM should mention this if asked why a zero trade exists.

## 11. Decimal Handling
Inputs treat `quantity` and `price` as strings or numbers; they are converted using `Decimal(str(value))` for determinism. External responses might show them as numbers or strings depending on FastAPI/Pydantic version. Internal computations always use Decimal until trade records append floats to pandas.

## 12. Performance Characteristics
- Intended for small scale / demonstration: O(log n) price access via sortedcontainers, linked-list O(1) head/tail operations.
- No batching, multi-threading, or persistence; all state lost on process restart.
- Not safe for concurrent writes without external synchronization (FastAPI’s default single-worker event loop mitigates but scaling with multiple workers would require shared state management).

## 13. Extensibility Guidelines
To add features:
- New order types: extend validation sets & implement processing function (e.g., stop orders -> add trigger evaluation before `process_order`).
- Persistence: wrap mutations (insert/remove/update) to emit events to a queue or database.
- Multiple markets: replace singleton with dependency-provided registry keyed by symbol.
- Authentication: add dependencies/routers for user scopes; trade_id could map to account.
- Metrics: instrument functions in `OrderBook` for Prometheus counters (trades executed, volume, latency). 

## 14. Common User Queries & Suggested Answer Outlines
Query: "How do I place a market order?" -> Mention POST /api/orders with type=market, side, quantity; price omitted. Response contains trades list, no resting order.
Query: "Why does my LIMIT order not show in list?" -> It was fully matched; `order` returned null because remaining quantity = 0.
Query: "How is time priority enforced?" -> Linked list per price level; increasing quantity moves order to tail (loss of priority).
Query: "Can I modify an order’s price?" -> Use PATCH; price change triggers removal & reinsertion – new timestamp and lost previous FIFO position.
Query: "What is new_book_quantity in trades?" -> Remaining quantity of resting order post partial fill; null when fully filled.
Query: "Why is there a zero trade in analytics?" -> Synthetic initial row to avoid empty DataFrame operations (TODO removal).

## 15. Safety & Reliability Considerations for LLM
When generating code:
- Preserve Decimal conversions to avoid floating precision issues.
- Do not expose internal data structures directly; use provided getters/API endpoints.
- Validate sides and order types against existing literals before processing.
- Avoid introducing race conditions (if suggesting async features, centralize state management).

When answering architectural questions:
- Clarify single in-memory instance limit.
- Mention lack of persistence & multi-user features unless added.

## 16. Quick Start (Local)
```
# Install deps
pip install -e .
# Run server
uvicorn main:app --reload
# Place an order
curl -X POST http://localhost:8000/api/orders \
  -H 'Content-Type: application/json' \
  -d '{"side":"bid","type":"limit","quantity":"5","price":"100"}'
# Run tests
pytest -q
```

## 17. Testing Strategy
`tests/test_api.py` covers:
- CRUD lifecycle for a limit order (create, read, modify, list, delete, not-found)
- Market order execution (ensures trades produced, market order not retained)
- Summary endpoint
- Health endpoint

Recommended future tests:
- Partial fill scenarios
- Price change modification
- Volume invariants
- Concurrent requests (if concurrency introduced)

## 18. Glossary
- Bid: Order to buy at or below a given price.
- Ask: Order to sell at or above a given price.
- Limit Order: Order with specified price; can rest in book.
- Market Order: Order to execute immediately at best available prices.
- Spread: Difference between best ask and best bid.
- FIFO: First-In, First-Out time priority within same price level.
- OHLC: Open, High, Low, Close price summary for interval.

## 19. Known Gaps / TODOs
- Synthetic zero trade hack in TradeDataFrame
- No persistence, auth, multi-market support
- DockerFile references requirements.txt (now added) but not integrated with pyproject build
- No formal licensing

## 20. Answer Style Guidance for LLM
When replying:
- Cite relevant modules/functions (e.g., "process_market_order in orderbook.py")
- Prefer concise bullet points for workflows
- Provide minimal code snippets focusing on changed lines when modifying logic
- Highlight invariants & side-effects when suggesting changes

---
End of LLM context. Use this as authoritative reference unless repository changes introduce new patterns.

