# PositionBook Architecture

## Overview

**PositionBook** is the **Single Source of Truth (SSOT)** for all position state in the StatArb_Gemini trading system. It implements a CQRS (Command Query Responsibility Segregation) pattern where reads are separated from writes.

## Design Principles

| Principle | Description |
|-----------|-------------|
| **SSOT** | Only PositionBook holds authoritative position data |
| **Thread-Safe** | All operations protected by `threading.RLock` |
| **Event-Driven** | Subscribers notified on position changes |
| **Immutable Reads** | Position queries return copies, not references |
| **Audit Trail** | Complete fill history maintained |

---

## Architecture Diagram

```
                     ┌─────────────────────────────┐
                     │      POSITION BOOK          │
                     │  (Single Source of Truth)   │
                     └─────────────┬───────────────┘
                                   │
       ┌───────────────────────────┼───────────────────────────┐
       │ READ                      │ READ                      │ WRITE
       ▼                           ▼                           ▼
┌─────────────┐           ┌─────────────┐            ┌─────────────┐
│ RISK ENGINE │           │  ANALYTICS  │            │  EXECUTION  │
│  (query)    │           │  (query)    │            │ (on_fill)   │
└─────────────┘           └─────────────┘            └─────────────┘
```

---

## Data Flow

### Backtest Flow

```
Signal Generated
       │
       ▼
┌─────────────────────────────────┐
│   CentralRiskManager            │
│   - authorize_trade()           │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│   UnifiedExecutionEngine        │
│   - execute()                   │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│   HistoricalExecutionSimulator  │
│   - simulate_fill()             │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│   CentralRiskManager            │
│   - update_position()           │  ─────────────┐
└───────────────┬─────────────────┘               │
                │                                  │
                ▼                                  ▼
┌─────────────────────────────────┐     ┌─────────────────┐
│   PositionBook.on_fill()        │────▶│  Subscribers    │
│   - Update position             │     │  (notified)     │
│   - Calculate P&L               │     └─────────────────┘
│   - Adjust cash balance         │
└─────────────────────────────────┘
```

---

## Core Components

### 1. PositionBook Class

```python
from core_engine.trading import PositionBook, Fill, FillSide

# Initialize
position_book = PositionBook(initial_cash=1_000_000)

# Process fill (WRITE - only entry point)
fill = Fill.create(
    symbol='AAPL',
    side=FillSide.BUY,
    quantity=100,
    price=150.00,
    commission=1.00
)
update = position_book.on_fill(fill)

# Query position (READ)
position = position_book.get_position('AAPL')
all_positions = position_book.get_all_positions()

# Query cash
cash = position_book.get_cash_balance()

# Subscribe to updates
def on_position_change(update):
    print(f"{update.symbol}: {update.event_type}")
    
position_book.subscribe(on_position_change)
```

### 2. Key Data Classes

| Class | Purpose |
|-------|---------|
| `Fill` | Execution record from broker/exchange |
| `BookPosition` | Complete position state (qty, cost basis, P&L) |
| `PositionUpdate` | Result of processing a fill |
| `PortfolioSnapshot` | Point-in-time portfolio state |

### 3. Enums

| Enum | Values | Purpose |
|------|--------|---------|
| `FillSide` | BUY, SELL | Direction of execution |
| `PositionSide` | FLAT, LONG, SHORT | Position direction |
| `PositionStatus` | OPEN, CLOSING, CLOSED | Lifecycle state |
| `PositionEventType` | OPENED, UPDATED, CLOSED, PRICE_UPDATED | Event types |

---

## Thread Safety

PositionBook uses a reentrant lock (`threading.RLock`) for thread safety:

```python
# All mutations are protected
def on_fill(self, fill: Fill) -> PositionUpdate:
    with self._lock:
        # ... position updates ...

# All reads return copies
def get_position(self, symbol: str) -> Optional[BookPosition]:
    with self._lock:
        pos = self._positions.get(symbol)
        return copy.deepcopy(pos) if pos else None
```

**Guarantees:**
- No race conditions on position reads/writes
- Subscribers called within lock (synchronous)
- Fill history is append-only

---

## Integration with CentralRiskManager

CentralRiskManager delegates to PositionBook when available:

```python
# In InstitutionalBacktestEngine.__init__
self.position_book = PositionBook(initial_cash=self.config.initial_capital)

# In _initialize_risk_manager()
self.risk_manager.set_position_book(self.position_book)
```

CRM methods delegate to PositionBook:
- `get_current_position(symbol)` → `position_book.get_position(symbol).quantity`
- `get_all_positions()` → `position_book.get_all_positions()`
- `update_position()` → `position_book.on_fill(fill)`

Legacy fields (`current_positions`, `available_cash`) are kept in sync via subscription callback for backward compatibility.

---

## P&L Calculations

### Realized P&L
Calculated when reducing or closing a position:

```python
realized_pnl = (exit_price - avg_entry_price) * closed_quantity
# For shorts: (avg_entry_price - exit_price) * closed_quantity
```

### Unrealized P&L
Calculated from current market price:

```python
unrealized_pnl = (current_price - avg_entry_price) * open_quantity
# For shorts: (avg_entry_price - current_price) * open_quantity
```

### Average Cost Basis
Weighted average on position additions:

```python
new_avg = (old_qty * old_avg + new_qty * new_price) / (old_qty + new_qty)
```

---

## Cash Balance Management

Cash is adjusted on every fill:

| Action | Cash Change |
|--------|-------------|
| BUY | `- (quantity × price) - commission - slippage` |
| SELL | `+ (quantity × price) - commission - slippage` |

```python
if fill.side == FillSide.BUY:
    cash_change = -(notional + costs)
else:
    cash_change = notional - costs
```

---

## Event Subscription

Components can subscribe to position updates:

```python
def my_handler(update: PositionUpdate):
    if update.event_type == PositionEventType.CLOSED:
        print(f"Closed {update.symbol}, P&L: {update.realized_pnl}")

position_book.subscribe(my_handler)
```

**Event Types:**
- `OPENED` - New position created
- `UPDATED` - Position quantity changed
- `CLOSED` - Position fully closed
- `PRICE_UPDATED` - MTM price changed

---

## Snapshot & Serialization

```python
# Get point-in-time snapshot
snapshot = position_book.get_snapshot()

# Snapshot contains:
# - timestamp
# - cash_balance
# - positions (dict)
# - total_market_value
# - total_realized_pnl
# - total_unrealized_pnl

# Convert to dict for serialization
snapshot_dict = snapshot.to_dict()
```

---

## Migration Guide

### From Legacy CRM Position Tracking

**Before (deprecated):**
```python
# Direct access - DEPRECATED
position = risk_manager.current_positions.get('AAPL', 0.0)
cash = risk_manager.available_cash
```

**After (recommended):**
```python
# Via CRM delegation
position = risk_manager.get_current_position('AAPL')

# Or direct PositionBook access
position = position_book.get_position('AAPL')
cash = position_book.get_cash_balance()
```

---

## File Locations

| File | Purpose |
|------|---------|
| `core_engine/trading/position_book.py` | Core implementation |
| `core_engine/trading/__init__.py` | Exports PositionBook, Fill, etc. |
| `tests/unit/trading/test_position_book.py` | 52 unit tests |
| `tests/integration/test_position_book_integration.py` | 13 CRM integration tests |
| `tests/integration/test_position_book_backtest_flow.py` | 10 backtest flow tests |

---

## Test Coverage

| Category | Tests | Coverage |
|----------|-------|----------|
| Position Opening | 4 | Long, Short, Cash update |
| Position Updates | 6 | Add, Reduce, Avg cost |
| Position Closing | 4 | Full close, Realized P&L |
| Position Flipping | 2 | Long→Short, Short→Long |
| Cash Balance | 4 | Buy, Sell, Costs |
| P&L Calculations | 5 | Realized, Unrealized, MTM |
| Thread Safety | 3 | Concurrent R/W |
| Events | 3 | Subscribe, Publish |
| Serialization | 3 | Snapshot, Dict |
| CRM Integration | 13 | Delegation, Sync |
| Backtest Flow | 10 | End-to-end |
| **Total** | **75** | |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | Nov 2025 | Initial implementation |
| 1.1.0 | Nov 2025 | CRM integration (Phase 2) |
| 1.2.0 | Nov 2025 | Deprecation notices (Phase 4) |
