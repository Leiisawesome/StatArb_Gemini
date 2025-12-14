---
name: Paper Trading Evolution
overview: Complete plan to evolve core_engine from backtest-only to dual-mode (backtest + paper trading) using the replay engine as market data source. Covers infrastructure, streaming pipeline, risk authorization, execution, and operations.
todos:
  - id: p1-timesource
    content: "Phase 1: Implement TimeSource with market_now(), wall_now(), wall_monotonic()"
    status: completed
  - id: p1-dispatcher
    content: "Phase 1: Implement DeterministicEventDispatcher with bounded queues and backpressure"
    status: completed
  - id: p1-validator
    content: "Phase 1: Implement StreamingDataValidator with OHLCV checks and gap detection"
    status: completed
  - id: p2-buffer
    content: "Phase 2: Implement StreamingBufferManager with per-symbol rolling DataFrames"
    status: completed
  - id: p2-indicator
    content: "Phase 2: Implement StreamingIndicatorAdapter wrapping batch indicators"
    status: completed
  - id: p2-feature
    content: "Phase 2: Add transform_single() to EnhancedFeatureEngineer (no fit in streaming)"
    status: completed
  - id: p2-signal
    content: "Phase 2: Implement StreamingSignalManager with BarPolicy enforcement"
    status: completed
  - id: p3-regime
    content: "Phase 3: Modify RegimeEngine for causal-only mode with confirmation state machine"
    status: completed
  - id: p3-session
    content: "Phase 3: Implement TradingSessionGate for RTH/extended hours control"
    status: completed
  - id: p3-risk-gates
    content: "Phase 3: Enhance CentralRiskManager with 6-gate authorization pipeline"
    status: completed
  - id: p3-risk-budget
    content: "Phase 3: Implement RiskBudgetState tracking (daily/per-trade limits)"
    status: completed
  - id: p3-pending
    content: "Phase 3: Add pending order exposure to OMS and risk checks"
    status: completed
  - id: p4-paper-broker
    content: "Phase 4: Implement PaperBrokerAdapter with realistic fills/rejects/costs"
    status: completed
  - id: p4-mode-routing
    content: "Phase 4: Add ExecutionMode routing in UnifiedExecutionEngine"
    status: completed
  - id: p5-journal
    content: "Phase 5: Implement EventJournal for audit trail"
    status: completed
  - id: p5-checkpoint
    content: "Phase 5: Implement PaperSessionStateManager with atomic checkpoints"
    status: completed
  - id: p5-idempotency
    content: "Phase 5: Add idempotency layer (event_id/fill_id dedup)"
    status: completed
  - id: p5-watchdog
    content: "Phase 5: Implement PaperTradingWatchdog with wall-time stall detection"
    status: completed
  - id: p6-engine
    content: "Phase 6: Implement PaperTradingEngine main event loop"
    status: completed
  - id: p6-test-parity
    content: "Phase 6: Create parity tests (backtest vs paper signals)"
    status: completed
  - id: p6-test-determinism
    content: "Phase 6: Create determinism tests (reproducible runs)"
    status: completed
  - id: p6-test-recovery
    content: "Phase 6: Create recovery tests (crash + restore)"
    status: completed
---

# Paper Trading Evolution Plan

## Executive Summary

Evolve `core_engine` to support **paper trading mode** alongside existing backtest mode, using `core_engine/data/replay` as the simulated real-time data source. The architecture must ensure **parity** (same logic produces same results), **determinism** (reproducible runs), **operational safety** (circuit breakers, watchdogs), and **auditability** (event journal).

---

## Section 1: Architecture Principles

### 1.1 Core Design Decisions

| Decision | Choice | Rationale |

|----------|--------|-----------|

| Data source | Replay engine (`core_engine/data/replay/`) | Simulates real-time from historical data |

| Processing model | Rolling buffer + batch code reuse | Preserves parity with backtest; no indicator rewrite |

| Position SSOT | `PositionBook` (fills-only writes) | Already designed for this; enforces consistency |

| Regime detection | Causal probabilities only | No look-ahead; paper/backtest parity |

| Event ordering | Single-threaded deterministic dispatcher | Reproducibility across runs |

| Time model | Dual clock (market time + wall time) | Market time for signals; wall time for operational controls |

### 1.2 Existing Components to Leverage

| Component | Location | Role in Paper Trading |

|-----------|----------|----------------------|

| PositionBook | `trading/position_book.py` | SSOT for positions |

| CentralRiskManager | `system/central_risk_manager.py` | Authorization pipeline |

| TradingCircuitBreakers | `system/circuit_breakers.py` | Emergency controls |

| RealTimePnLTracker | `system/realtime_pnl_tracker.py` | MTM and P&L |

| OrderManagementSystem | `system/order_management_system.py` | Order lifecycle |

| UnifiedExecutionEngine | `system/unified_execution_engine.py` | Execution algorithms |

| HistoricalReplayAdapter | `data/replay/adapter.py` | Market data source |

| FeedMessage | `data/feeds/adapters.py` | Standardized bar/quote format |

---

## Section 2: Infrastructure Layer

### 2.1 TimeSource (Dual Clock)

**Problem**: Replay uses historical timestamps; some controls need real time.

**Design**:

```
TimeSource
├── market_now() → datetime    # Current replay timestamp (event time)
├── wall_now() → datetime      # Real system time
└── wall_monotonic() → float   # Monotonic for timeouts
```

**Usage Rules**:

- Signal age, bar alignment, regime evaluation → `market_now()`
- Watchdog, IO timeouts, rate limiting, SLAs → `wall_monotonic()`

**Integration**: Inject via dependency injection into all components.

---

### 2.2 DeterministicEventDispatcher

**Problem**: Async handlers can process out of order; results not reproducible.

**Design**:

- Priority queue ordered by `(market_timestamp, sequence_number)`
- Single-threaded sequential processing (no concurrent handlers per bar)
- Bounded queue with explicit backpressure policy

**Backpressure Policy**:

| Message Type | Policy |

|--------------|--------|

| Bar | Never drop; slow ingestion if behind |

| Quote/Trade | Conflate (keep latest per symbol) |

---

### 2.3 StreamingDataValidator

**Problem**: No validation between replay and processing; bad data propagates silently.

**Checks**:

- OHLCV sanity: `High >= Low`, `Close` within `[Low, High]`, `Volume >= 0`
- Gap detection: flag if gap > 2× expected interval
- Emit `DataQualityEvent` for monitoring; reject on hard errors

---

## Section 3: Streaming Processing Pipeline

### 3.1 StreamingBufferManager

**Purpose**: Maintain per-symbol rolling DataFrames for batch indicator reuse.

**Design**:

```
StreamingBufferManager
├── buffers: Dict[symbol, DataFrame]  # Rolling window per symbol
├── buffer_size: int                  # e.g., 500 bars
├── warmup_required: int              # e.g., 200 bars
└── methods:
    ├── update(symbol, bar) → None
    ├── get_buffer(symbol) → DataFrame
    ├── is_warmed_up(symbol) → bool
    └── load_warmup_data(symbol, historical_df) → None
```

**Warmup**: Load 1-2 RTH sessions before trading starts.

---

### 3.2 StreamingIndicatorAdapter

**Purpose**: Wrap existing batch indicators; extract last row only.

**Design**:

```
StreamingIndicatorAdapter
├── indicator_engine: EnhancedIndicatorEngine
└── compute_indicators(buffer: DataFrame) → Dict[str, float]
    # Runs batch compute, returns only last row as dict
```

---

### 3.3 StreamingFeatureAdapter

**Purpose**: Apply pre-trained scalers to single rows; no fitting in streaming.

**Design**:

```
EnhancedFeatureEngineer (extended)
├── fit_scalers(historical_df) → None          # Offline: 30 RTH days
├── save_scalers(path) → None
├── load_scalers(path) → None
├── transform_single(row: Dict) → Dict[str, float]  # Online: no fit
```

---

### 3.4 BarPolicy (Signal/Action Semantics)

**Purpose**: Enforce consistent compute/act timing for parity.

**Definition**:

```
BarPolicy:
  compute_on: "bar_close"      # Indicators/features computed at close
  signal_on: "bar_close"       # Signal generated at close
  act_on: "next_bar_open"      # Order submitted at next open
  fill_price: "next_bar_open"  # For paper/backtest alignment
```

**Enforcement**: Both backtest engine and paper engine use this policy.

---

## Section 4: Regime Detection (Causal-Only)

### 4.1 Streaming Regime Evaluation

**Problem**: Backtest uses smoothed probabilities (future data); paper cannot.

**Solution**:

- Use `filtered_marginal_probabilities` only (causal)
- Modify backtest to match (ensures parity)

**Evaluation Schedule**:

- Every 5 minutes (not every bar)
- 2-step confirmation: `PENDING → CONFIRMED` after 2 consecutive agreeing evaluations

---

## Section 5: Risk Authorization Pipeline (6 Gates)

### 5.1 Signal Input Contract (Required Fields)

**Schema**:

```
EnhancedTradingSignal:
  # === REQUIRED FIELDS (signal REJECTED if missing) ===
  symbol: str
  side: 'buy' | 'sell'
  requested_quantity: float
  signal_strength: float        # 0.0 - 1.0
  strategy_id: str
  signal_timestamp: datetime    # Market time when generated
  arrival_price: float          # Price at signal generation

  # === STOP SPECIFICATION (at least one required) ===
  # Risk budget calculation (Gate 5) depends on knowing max loss.
  # Signal MUST include at least one of:
  stop_price: Optional[float]       # Absolute price (e.g., 148.50)
  stop_loss_pct: Optional[float]    # Relative to arrival_price (e.g., 0.02 = 2%)
  # If both provided: stop_price takes precedence
  # If neither provided: use config.default_stop_loss_pct (default: 0.02)
  #                      AND flag signal with WARNING for audit

  # === OPTIONAL FIELDS (defaults applied if absent) ===
  take_profit_price: Optional[float]  # Absolute price
  take_profit_pct: Optional[float]    # Relative to arrival_price
  # If absent: no take-profit order placed (position exits only via stop or strategy exit)
```

**Stop Resolution Logic**:

```python
def resolve_stop(signal: EnhancedTradingSignal, config: Config) -> float:
    """Returns effective stop_price. Called at Gate 5."""
    if signal.stop_price is not None:
        return signal.stop_price
    
    stop_pct = signal.stop_loss_pct or config.default_stop_loss_pct
    
    if signal.side == 'buy':
        return signal.arrival_price * (1 - stop_pct)
    else:  # sell/short
        return signal.arrival_price * (1 + stop_pct)
```

**Validation at Signal Generation** (StreamingSignalManager):

- If `stop_price` and `stop_loss_pct` both absent → apply default, emit `SignalDefaultApplied` event
- If `stop_price` is on wrong side of arrival_price → REJECT signal with reason
- If `stop_loss_pct > 0.10` (10%) → emit WARNING (unusually wide stop)

### 5.2 Gate 0: Circuit Breakers (Existing)

**Checks**:

- Kill switch active?
- Daily loss limit breached? (default: -2%)
- Drawdown from high breached? (default: -5%)
- Order rate limit exceeded? (default: 10/sec)

**Action**: REJECT if any breaker tripped.

---

### 5.3 Gate 1: Session Gate (New)

**Checks**:

- Is symbol's market open?
- Are we in allowed trading hours (RTH vs extended)?
- Is symbol halted (LULD, news)?

**Action**: REJECT if outside allowed session.

---

### 5.4 Gate 2: Price-Aware Validation (New)

#### PriceSource Definition

The system operates in one of two modes, configured at initialization:

| Mode | Data Available | Use Case |

|------|----------------|----------|

| BAR_ONLY | OHLCV bars | Replay from historical daily/minute data |

| QUOTE_ENABLED | Bars + BBO quotes | Real-time feeds with quote data |

**Spread Estimation by Mode**:

```
# BAR_ONLY mode: Estimate from bar data
intrabar_range = (high - low) / close
estimated_spread_bps = max(
    intrabar_range * 0.1 * 10000,      # 10% of intrabar range
    symbol_spread_table[symbol],       # Lookup default (median historical spread)
    config.min_spread_bps              # Floor: 1 bps for liquid, 5 bps for illiquid
)

# QUOTE_ENABLED mode: Use actual quotes
mid = (bid + ask) / 2
spread_bps = (ask - bid) / mid * 10000
```

**ADV (Average Daily Volume) Source**:

```
# Pre-computed offline and loaded at startup:
adv_table: Dict[symbol, float]  # 20-day trailing ADV in shares
# Updated daily in overnight batch process
# Fallback: if missing, use config.default_adv (1M shares for equities)

# Spread table loaded at startup (parallel to ADV):
symbol_spread_table: Dict[symbol, float]  # 60-day median spread in bps (per symbol)
```

**Inputs**:

- `arrival_price` (from signal)
- `current_price` (from latest bar close if BAR_ONLY; `mid` if QUOTE_ENABLED)
- `spread_bps` (computed per mode above)
- `adv` (from `adv_table[symbol]`)

**Calculations**:

```
spread_cost_bps = spread_bps / 2
impact_cost_bps = sqrt(qty / adv) × impact_coefficient  # impact_coefficient default: 10
slippage_bps = spread_cost_bps + impact_cost_bps
estimated_fill_price = current_price × (1 + slippage_bps / 10000) [for BUY]
                     = current_price × (1 - slippage_bps / 10000) [for SELL]
price_move_pct = |current_price - arrival_price| / arrival_price
```

**Checks**:

- `price_move_pct > stale_signal_threshold` (e.g., 1%) → REJECT
- `slippage_bps > max_acceptable_slippage` → REJECT or RESIZE

---

### 5.5 Gate 3: Position-Aware Validation (Enhanced)

#### OMS Read API for Pending Exposure

The OMS must expose the following read API for risk calculations:

**Required OMS Query Methods**:

```python
class OrderManagementSystem:
    def get_working_orders(
        self,
        symbol: Optional[str] = None,
        side: Optional[Literal['buy', 'sell']] = None
    ) -> List[WorkingOrder]:
        """
        Returns all orders in states: PENDING_NEW, NEW, PARTIALLY_FILLED
        Optional filters: symbol, side
        """

    def get_pending_exposure(self, symbol: Optional[str] = None) -> PendingExposure:
        """
        Pre-computed aggregate exposure for fast access.
        Called on every risk check; must be O(1) or cached.
        """

    def get_pending_risk_at_price(
        self,
        symbol: str,
        price: float
    ) -> PendingRiskAtPrice:
        """
        Returns exposure if orders fill at given price.
        Used for what-if analysis in Gate 3.
        """
```

**WorkingOrder Fields** (returned by `get_working_orders`):

```
WorkingOrder:
  order_id: str                 # Unique order identifier
  symbol: str
  side: 'buy' | 'sell'
  order_type: 'market' | 'limit' | 'stop' | 'stop_limit'
  quantity: float               # Original order quantity
  filled_quantity: float        # Already filled (for partial fills)
  remaining_quantity: float     # quantity - filled_quantity
  limit_price: Optional[float]  # For limit orders
  stop_price: Optional[float]   # For stop orders
  status: 'pending_new' | 'new' | 'partially_filled'
  submit_time: datetime         # Market time of submission
  strategy_id: str              # Source strategy
```

**PendingExposure Fields** (returned by `get_pending_exposure`):

```
PendingExposure:
  # Per-symbol aggregates
  by_symbol: Dict[str, SymbolPendingExposure]
  
  # Portfolio-level aggregates
  total_pending_buy_notional: float     # Sum of (remaining_qty × limit_price) for buys
  total_pending_sell_notional: float    # Sum of (remaining_qty × limit_price) for sells
  total_pending_buy_count: int          # Number of pending buy orders
  total_pending_sell_count: int         # Number of pending sell orders

SymbolPendingExposure:
  symbol: str
  pending_buy_qty: float                # Sum of remaining_qty for buy orders
  pending_sell_qty: float               # Sum of remaining_qty for sell orders
  pending_buy_notional: float           # Sum of (remaining_qty × price) for buys
  pending_sell_notional: float          # Sum of (remaining_qty × price) for sells
  # For market orders: use arrival_price from order; for limit: use limit_price
```

**Cache Update Rules**:

- `PendingExposure` is recomputed on: order submit, fill, cancel, reject, expire
- OMS emits `PendingExposureChanged` event after recomputation
- Risk manager subscribes to `PendingExposureChanged` to invalidate its cache

**Inputs** (all from SSOT):

- `current_position` = PositionBook.get_position(symbol)
- `pending_orders` = OMS.get_working_orders(symbol)
- `pending_exposure` = OMS.get_pending_exposure(symbol)
- `available_cash` = PositionBook.get_cash_balance() - pending_exposure.total_pending_buy_notional

**Calculations**:

```
pending_qty = pending_exposure.by_symbol[symbol].pending_buy_qty 
            - pending_exposure.by_symbol[symbol].pending_sell_qty
post_trade_position = current_position + pending_qty + (side × requested_qty)
post_trade_value = |post_trade_position| × current_price
position_pct = post_trade_value / portfolio_value
```

**Checks**:

- `position_pct > max_position_size` → RESIZE to fit
- `position_pct > max_concentration` → RESIZE to fit
- SELL: `requested_qty > current_position + pending_exposure.by_symbol[symbol].pending_buy_qty` → CAP at sellable
- BUY: `required_cash > available_cash` → RESIZE to affordable

---

### 5.6 Gate 4: Regime-Aware Adjustment (Enhanced)

**Inputs**:

- `market_regime` = RegimeEngine.get_current_regime() [causal]
- `volatility_regime` = 'low' | 'normal' | 'high' | 'crisis'
- `strategy_type` = signal.strategy_id → lookup strategy characteristics

**Regime Scaling**:

| Volatility Regime | Size Multiplier |

|-------------------|-----------------|

| low | 1.10 |

| normal | 1.00 |

| high | 0.50 - 0.70 |

| crisis | 0.30 or REJECT |

**Strategy-Regime Compatibility**:

- Mean-reversion strategy + trending regime → reduce by 50%
- Momentum strategy + mean-reverting regime → reduce by 50%

---

### 5.7 Gate 5: P&L-Aware Risk Budget Check (New)

**Inputs**:

- `effective_stop_price` (resolved from signal via Section 5.1 `resolve_stop()`)
- `estimated_fill_price` (from Gate 2 output)
- `candidate_quantity` (quantity under review at this gate; starts as `requested_quantity` and may be resized)
- `portfolio_value` (from PositionBook)
- `daily_risk_budget_pct` (config, e.g., 1%)
- `per_trade_risk_pct` (config, e.g., 0.5%)

**Calculations**:

```
per_share_loss = max(0, estimated_fill_price - effective_stop_price)   # for BUY (long)
              = max(0, effective_stop_price - estimated_fill_price)   # for SELL (short)

max_loss_this_trade = candidate_quantity × per_share_loss
daily_risk_budget = portfolio_value × daily_risk_budget_pct
used_risk_budget = sum(max_loss for open positions with effective stops)
available_risk = daily_risk_budget - used_risk_budget
per_trade_limit = portfolio_value × per_trade_risk_pct
```

**Checks**:

- `max_loss_this_trade > available_risk` → RESIZE
- `max_loss_this_trade > per_trade_limit` → RESIZE

**Optional Kelly Sizing**:

```
kelly_fraction = (win_prob × reward/risk - lose_prob) / (reward/risk)
fractional_kelly = kelly_fraction × 0.25  # Conservative
max_kelly_qty = fractional_kelly × portfolio_value / estimated_fill_price
candidate_quantity = min(candidate_quantity, max_kelly_qty)
```

---

### 5.8 Gate 6: Final Authorization

**Output**:

```
TradingAuthorization:
  authorization_id: str
  authorized_quantity: float        # After all resizing
  estimated_fill_price: float
  max_loss_estimate: float
  risk_budget_consumed: float
  regime_at_authorization: str
  authorization_level: AUTOMATIC | STANDARD | ELEVATED
  expires_at: datetime              # e.g., 60 seconds
  monitoring_requirements: List[str]
```

**Final Checks**:

- `authorized_quantity < min_order_size` → REJECT
- Generate unique `authorization_id` for idempotency

---

### 5.9 Post-Authorization Monitoring

**While authorization is active**:

- If regime changes significantly → CANCEL pending order
- If price moves beyond threshold → CANCEL pending order
- If authorization expires → CANCEL pending order

**On fill**:

- Update `RiskBudgetState` (used_risk_budget)
- Update `PositionBook` (via fill event)
- Update `RealTimePnLTracker`

---

## Section 6: Execution Layer

### 6.1 PaperBrokerAdapter

**Implements**: `BaseBrokerAdapter` interface

**Realistic Behaviors**:

| Behavior | Implementation |

|----------|----------------|

| Latency | Configurable delay (e.g., 50-200ms simulated) |

| Partial fills | Based on order size vs ADV participation |

| Spread cost | Half spread applied to fill price |

| Market impact | sqrt(participation) model |

| Slippage | Random within configured bounds |

| Commissions | Per-share or per-trade fee |

| Rejects | Insufficient cash, halted symbol, no liquidity |

**Order Lifecycle**:

```
PENDING_NEW → NEW → [PARTIALLY_FILLED] → FILLED | CANCELLED | REJECTED
```

---

### 6.2 Mode-Aware Execution Routing

**In UnifiedExecutionEngine**:

```python
if execution_mode == ExecutionMode.PAPER:
    result = await self.paper_broker.execute(order)
elif execution_mode == ExecutionMode.LIVE:
    result = await self.live_broker.execute(order)
```

---

## Section 7: Operations Layer

### 7.1 EventJournal (Audit Trail)

**Purpose**: Append-only log for audit and deterministic replay.

**Events Logged**:

- Market data (normalized bars)
- Derived state (features, regime)
- Signals generated
- Risk decisions (approve/reject/resize + reasons)
- Orders (submit, fill, cancel, reject)
- Position updates

**Format**: JSON lines or Parquet, one file per session.

---

### 7.2 PaperSessionStateManager (Checkpoints)

**Saved State**:

- Replay position (symbol, timestamp, row_index)
- PositionBook snapshot
- Buffer states (per-symbol DataFrames)
- Regime engine state
- OMS state (pending orders)
- Risk budget state
- `last_event_id` processed

**Checkpoint Triggers**:

- Every N bars (configurable, e.g., 1000)
- On manual pause
- On graceful shutdown
- On circuit breaker halt

**Atomicity**: Save state + last_event_id together; restore resumes exactly-once.

---

### 7.3 Idempotency (Exactly-Once Processing)

#### ID Generation Ownership

Each component generates IDs for events it creates, using deterministic formulas:

| ID Type | Generated By | Formula | Example |

|---------|--------------|---------|---------|

| `event_id` | DeterministicEventDispatcher | `SHA256(session_id + event_type + market_ts_ns + symbol + seq)[:16] `| `"a1b2c3d4e5f67890"` |

| `signal_id` | StreamingSignalManager | `f"{strategy_id}:{symbol}:{market_ts_iso}:{seq}"` | `"mr_bonds:AAPL:2025-01-15T10:30:00:001"` |

| `authorization_id` | CentralRiskManager | `f"auth:{signal_id}:{gate_passed}"` | `"auth:mr_bonds:AAPL:...:G5"` |

| `order_id` | OrderManagementSystem | `f"{session_id}:{seq:08d}"` | `"paper-20250115-0001:00000042"` |

| `fill_id` | PaperBrokerAdapter / Broker | `f"{order_id}:{fill_seq:03d}"` | `"paper-...-0001:00000042:001"` |

**Component Sequence Counters**:

```python
class IdGenerator:
    """Thread-safe deterministic ID generation. One per component."""
    
    def __init__(self, component_name: str, session_id: str):
        self.component = component_name
        self.session_id = session_id
        self._seq = 0  # Monotonic counter, reset at session start
        self._lock = threading.Lock()
    
    def next_seq(self) -> int:
        with self._lock:
            self._seq += 1
            return self._seq
    
    @property
    def current_seq(self) -> int:
        """For checkpoint serialization."""
        return self._seq
    
    def restore_seq(self, seq: int) -> None:
        """On recovery, restore to last checkpointed value."""
        self._seq = seq
```

**Session ID Generation**:

```python
# At paper trading session start:
session_id = f"paper-{date.today().strftime('%Y%m%d')}-{run_seq:04d}"
# run_seq: incremented per run, persisted in session metadata
# Example: "paper-20250115-0003" (third run on Jan 15)
```

#### Processed ID Tracking

**IdempotencyTracker** maintains sets of processed IDs:

```python
class IdempotencyTracker:
    """Tracks processed IDs to prevent duplicate processing."""
    
    def __init__(self, max_history: int = 100_000):
        self.processed_event_ids: Set[str] = set()
        self.processed_fill_ids: Set[str] = set()
        self.max_history = max_history
        self._lru: Deque[Tuple[str, str]] = deque()  # (id_type, id_value) for correct eviction
    
    def is_processed(self, id_type: str, id_value: str) -> bool:
        """Check if ID was already processed."""
        if id_type == 'event':
            return id_value in self.processed_event_ids
        elif id_type == 'fill':
            return id_value in self.processed_fill_ids
        return False
    
    def mark_processed(self, id_type: str, id_value: str) -> None:
        """Mark ID as processed. Evict oldest if at capacity."""
        target = self.processed_event_ids if id_type == 'event' else self.processed_fill_ids
        target.add(id_value)
        self._lru.append((id_type, id_value))
        
        if len(self._lru) > self.max_history:
            oldest_type, oldest_value = self._lru.popleft()
            oldest_target = self.processed_event_ids if oldest_type == 'event' else self.processed_fill_ids
            oldest_target.discard(oldest_value)
```

#### Checkpoint Persistence

**Saved in checkpoint** (see Section 7.2):

```yaml
idempotency_state:
  # Sequence counters per component (for deterministic ID generation on resume)
  sequence_counters:
    dispatcher: 145230
    signal_manager: 892
    risk_manager: 891
    oms: 156
    paper_broker: 203
  
  # Recently processed IDs (last N, for dedup on recovery)
  recent_processed:
    event_ids: ["a1b2c3...", "d4e5f6...", ...]  # Last 10,000
    fill_ids: ["paper-...:001", ...]            # Last 1,000
  
  # High-water marks (alternative to full ID sets)
  high_water_marks:
    last_event_market_ts: "2025-01-15T14:30:00.123456Z"
    last_order_seq: 156
    last_fill_seq: 203
```

#### Recovery Protocol

On session restore:

```python
def restore_idempotency(checkpoint: Checkpoint) -> None:
    # 1. Restore sequence counters (deterministic ID generation resumes correctly)
    for component, seq in checkpoint.idempotency_state.sequence_counters.items():
        get_id_generator(component).restore_seq(seq)
    
    # 2. Rebuild processed ID sets
    tracker = IdempotencyTracker()
    for eid in checkpoint.idempotency_state.recent_processed.event_ids:
        tracker.mark_processed('event', eid)
    for fid in checkpoint.idempotency_state.recent_processed.fill_ids:
        tracker.mark_processed('fill', fid)
    
    # 3. On replay, skip events before high-water mark
    replay_adapter.seek_after(checkpoint.idempotency_state.high_water_marks.last_event_market_ts)
    
    # 4. For any event that slips through, dedup via tracker
    #    (handles edge case where checkpoint was taken mid-batch)
```

**Guarantees**:

- No duplicate signal generation (signal_id is deterministic from inputs)
- No duplicate order submission (authorization_id checked before OMS submit)
- No duplicate fill application (fill_id checked before PositionBook update)
- Deterministic recovery (same sequence counters → same IDs on re-run)

---

### 7.4 PaperTradingWatchdog

**Purpose**: Detect stalls and trigger recovery.

**Monitors** (using wall/monotonic time):

- Time since last processed bar
- Processing rate (bars/second)
- Queue depth

**Actions**:

- Warning at 50% of max stall threshold
- Save checkpoint at 80%
- Trigger recovery at 100%

---

### 7.5 TradingSessionGate

**Purpose**: Prevent trading outside allowed windows.

**Configuration**:

```yaml
allowed_sessions:
  - type: RTH
    start: "09:30"
    end: "16:00"
    timezone: "America/New_York"
no_trade_windows:
  - "09:30:00-09:30:30"  # Opening auction
  - "15:59:30-16:00:00"  # Closing auction
holidays: [...calendar...]
```

---

## Section 8: Implementation Phases

### Phase 1: Infrastructure (Week 1)

1. `TimeSource` with market/wall time
2. `DeterministicEventDispatcher` with bounded queues
3. `StreamingDataValidator`

### Phase 2: Processing Pipeline (Week 2)

4. `StreamingBufferManager`
5. `StreamingIndicatorAdapter`
6. `EnhancedFeatureEngineer.transform_single()`
7. `StreamingSignalManager` with BarPolicy

### Phase 3: Regime + Risk (Week 3)

8. Causal-only regime evaluation + confirmation state machine
9. `TradingSessionGate`
10. Enhanced `CentralRiskManager` (6 gates, risk budget, pending orders)
11. `RiskBudgetState` tracking

### Phase 4: Execution (Week 4)

12. `PaperBrokerAdapter` with realistic behaviors
13. Mode-aware routing in `UnifiedExecutionEngine`
14. OMS integration for pending order tracking

### Phase 5: Operations (Week 5)

15. `EventJournal`
16. `PaperSessionStateManager` with atomic checkpoints
17. Idempotency layer
18. `PaperTradingWatchdog`

### Phase 6: Integration + Testing (Week 6)

19. `PaperTradingEngine` main event loop
20. Parity tests (backtest vs paper)
21. Determinism tests (same run twice)
22. Recovery tests (crash + restore)
23. Stress tests (fast replay)

---

## Section 9: Test Plan

### 9.1 Parity Tests

- Same historical day: backtest vs paper produce identical signals
- Feature values match to 6 decimal places
- Regime transitions occur at same timestamps

### 9.2 Determinism Tests

- Run same session twice → identical fills, positions, P&L
- Verify event ordering is consistent

### 9.3 Idempotency Tests

- Simulate crash after fill generated, before checkpoint
- Restore → verify no double-applied fills

### 9.4 Risk Control Tests

- Verify circuit breaker halts trading correctly
- Verify daily risk budget caps trade size
- Verify session gate blocks off-hours signals

### 9.5 Stress Tests

- 1000x replay speed with watchdog monitoring
- Large buffer sizes with memory profiling
- High signal frequency with queue backpressure

---

## Section 10: Key Files to Create/Modify

### New Files

| File | Purpose |

|------|---------|

| `core_engine/system/time_source.py` | Dual clock implementation |

| `core_engine/system/event_dispatcher.py` | Deterministic ordering |

| `core_engine/data/validation/streaming_validator.py` | Data quality gate |

| `core_engine/processing/streaming/buffer_manager.py` | Rolling buffers |

| `core_engine/processing/streaming/adapters.py` | Indicator/feature adapters |

| `core_engine/processing/signals/streaming_manager.py` | Signal lifecycle |

| `core_engine/system/session_gate.py` | Trading hours control |

| `core_engine/system/risk_budget.py` | Risk budget tracking |

| `core_engine/broker/adapters/paper_adapter.py` | Paper broker |

| `core_engine/system/event_journal.py` | Audit log |

| `core_engine/system/paper_state_manager.py` | Checkpoints |

| `core_engine/system/paper_watchdog.py` | Stall detection |

| `core_engine/paper/engine.py` | Main paper trading engine |

### Modified Files

| File | Changes |

|------|---------|

| `core_engine/system/central_risk_manager.py` | Add 6-gate pipeline, risk budget |

| `core_engine/regime/engine.py` | Causal-only mode flag |

| `core_engine/processing/features/engineer.py` | Add `transform_single()` |

| `core_engine/system/unified_execution_engine.py` | Mode-aware routing |

| `core_engine/system/order_management_system.py` | Pending order queries |