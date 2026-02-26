# Shadow Trading System — Build Plan

**Spec**: v1.7-SHADOW (frozen)  
**Target**: 30-day paper trading with mechanism monitoring  
**Revision**: v4-FINAL — incorporates final quant review (baseline governance, absolute caps, spread baseline, kill horizon alignment, drawdown precision, inventory stress, depth logging)

---

## Pre-Requisite: Time & Latency Infrastructure (Non-Negotiable)

Before any component is built, verify:
- System clock synced via NTP, offset < 10ms
- All timestamps use `exchange_timestamp` from Polygon, not system clock
- The 200ms entry delay is measured from `exchange_timestamp`, making it robust to receive latency

### Clock Synchronization (offset)
- Log `exchange_ts - system_receive_ts` for every quote
- Track median receive latency per symbol per 5-minute window
- Alert if median > 100ms or P95 > 200ms
- If clock drift detected, auto-pause (timing is mechanism-critical)

### Latency Variance Monitoring (three distinct paths)
Clock drift measures systematic offset. Latency variance measures stochastic jitter — and it's variance, not mean, that kills passive strategies.

| Path | What it measures | Failure mode |
|------|-----------------|--------------|
| **Polygon → ingest** (market data arrival) | Time from exchange_ts to system_receive_ts | Stale spread_ratio at entry; 200ms delay becomes 200ms + unknown lag |
| **Engine → IBKR** (order submission RTT) | Time from submit call to IBKR acknowledgment | Limit order arrives at different market state than computed |
| **IBKR → cancel ack** (cancel round trip) | Time from cancel request to confirmation | Exit exposure extends beyond modeled hold time |

Track p50 / p95 / p99 for each path.

**Baseline governance** (v4 — eliminates small-sample anchoring risk):
- Primary baseline: latency distributions from Step 7 historical replay (130 days, statistically robust across volatility regimes)
- Live comparison: rolling 10-day minimum window (not 5)
- Both relative and absolute triggers enforce independently:

**Relative drift triggers** (catches sudden degradation):
- Alert if any path's p95 > 2× rolling 10-day baseline

**Absolute caps** (catches slow creep where baseline normalizes itself):

| Path | Absolute p95 ceiling | Action |
|------|---------------------|--------|
| Ingest (Polygon → system) | 250ms | Auto-pause — 200ms delay becomes unreliable |
| Order RTT (system → IBKR) | 400ms | Auto-pause — limit order arrives at stale state |
| Cancel ack (IBKR → system) | 500ms median | Auto-pause — exit exposure extends beyond modeled |

Relative drift catches spikes. Absolute caps catch regimes where the baseline itself was too optimistic. Both are necessary.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                  LiquidityShadowEngine                  │
│                                                         │
│  ┌──────────────┐    ┌──────────────┐                   │
│  │ PolygonQuote  │    │ PolygonTrade │                   │
│  │   Stream      │    │   Stream     │                   │
│  └──────┬───────┘    └──────┬───────┘                   │
│         │                   │                            │
│         ▼                   ▼                            │
│  ┌──────────────────────────────────┐                   │
│  │     StreamingVolumeBucketer      │                   │
│  │  (in-memory, per-symbol)         │                   │
│  │  → detects bucket completion     │                   │
│  │  → computes flow_imbalance       │                   │
│  │  → checks p95 threshold          │                   │
│  └──────────────┬───────────────────┘                   │
│                 │ (extreme event)                        │
│                 ▼                                        │
│  ┌──────────────────────────────────┐                   │
│  │       EventLevelFilter           │                   │
│  │  → 200ms delay timer             │                   │
│  │  → compute spread_ratio          │                   │
│  │  → accept if <1.0 or >2.0       │                   │
│  │  → check inventory cap           │                   │
│  └──────────────┬───────────────────┘                   │
│                 │ (accepted event)                       │
│                 ▼                                        │
│  ┌──────────────────────────────────┐                   │
│  │       OrderManager               │                   │
│  │  → place limit order (IBKR)      │                   │
│  │  → track fill status             │                   │
│  │  → manage 3-way exit             │                   │
│  │  → log fill vs model comparison  │                   │
│  └──────────────┬───────────────────┘                   │
│                 │ (trade outcomes)                       │
│                 ▼                                        │
│  ┌──────────────────────────────────┐                   │
│  │       MechanismMonitor           │                   │
│  │  → M1: mechanism health surface  │                   │
│  │  → M2: sub-strategy split        │                   │
│  │  → M3: fill vs modeled (DUAL)    │                   │
│  │  → M4: net inventory beta        │                   │
│  │  → M5: throughput                 │                   │
│  │  → M6: spread_ratio distribution │                   │
│  │  → M7: slippage decomposition    │                   │
│  │  → M8: NBBO integrity            │                   │
│  │  → kill condition enforcement     │                   │
│  └──────────────────────────────────┘                   │
│                                                         │
│  ┌──────────────────────────────────┐                   │
│  │   InfrastructureLatencyMonitor   │                   │
│  │  → clock sync (exchange vs sys)  │                   │
│  │  → ingest latency p50/p95/p99   │                   │
│  │  → order RTT p50/p95/p99        │                   │
│  │  → cancel ack p50/p95/p99       │                   │
│  │  → NBBO integrity (locked/cross)│                   │
│  │  → relative drift (2× 10-day)   │                   │
│  │  → absolute caps (250/400/500ms)│                   │
│  └──────────────────────────────────┘                   │
│                                                         │
│  ┌──────────────────────────────────┐                   │
│  │       ClickHouse Logger          │                   │
│  │  → every event, order, fill      │                   │
│  │  → mechanism metrics per trade   │                   │
│  │  → daily/weekly report tables    │                   │
│  └──────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────┘
```

---

## Build Sequence (10 Steps)

### Step 0: v1.7 Constants + Schema (Day 1)
**What**: Freeze all constants, create ClickHouse tables for shadow logging.

- `core_engine/microstructure/shadow/constants.py` — all v1.7 frozen parameters
- ClickHouse DDL for:
  - `shadow_events` — every detected imbalance event (with NBBO integrity flags)
  - `shadow_orders` — every order placed (with modeled expectations, expected prices for slippage)
  - `shadow_fills` — fill outcomes + mechanism metrics + slippage decomposition fields:
    - `expected_entry_price`, `actual_entry_price`, `entry_slippage_bps`
    - `expected_exit_price`, `actual_exit_price`, `exit_slippage_bps`
    - `cancel_delay_ms`, `partial_fill_ratio`
  - `shadow_daily` — daily aggregates for all 8 KPIs (M1-M8)
  - `shadow_latency` — per-quote latency observations (exchange_ts, receive_ts, path)
  - `shadow_state_log` — transactional order state persistence for crash recovery

**Depends on**: Nothing  
**Validates**: Schema matches spec exactly, includes all forensic fields

---

### Step 1: StreamingVolumeBucketer (Days 2-3)
**What**: Real-time volume-clock bucketing from streaming trades.

Reuses the offline `volume_clock.py` logic but operates on a streaming trade-by-trade basis:
- Maintains per-symbol state: cumulative volume, OHLCV, flow metrics
- When cumulative volume reaches ADV/200 → bucket complete
- Computes flow_imbalance on completed bucket
- Emits event if |imbalance| exceeds frozen p95 threshold

**Key difference from offline**: no look-ahead, processes one trade at a time.

**Streaming Lee-Ready classification risk** (per external review):
- Streaming classification can diverge from offline due to missing micro-quotes, out-of-order messages, and quote update lag
- If aggressor_side classification drifts → imbalance threshold shifts → event detection frequency changes
- Validation: replay **30 full days** (not 5) through streaming path during Step 8 validation
- Measure streaming vs offline imbalance distribution; confirm p95 threshold stability within 3% (hard pass), 3-5% triggers investigation
- During live operation: track `classification_confidence` per bucket (% clearly above/below midpoint vs ambiguous)

**Interface**:
```python
class StreamingVolumeBucketer:
    def __init__(self, symbol: str, adv_shares: int, imbalance_threshold: float)
    def on_trade(self, timestamp_ns: int, price: float, size: int, 
                 aggressor_side: int) -> Optional[ImbalanceEvent]
    def on_quote(self, timestamp_ns: int, bid: float, ask: float,
                 bid_size: int, ask_size: int) -> None
    def get_classification_confidence(self) -> float
```

**Depends on**: Step 0  
**Tests**: Feed recorded trades, verify identical bucket boundaries to offline, verify classification confidence tracking

---

### Step 2: EventLevelFilter (Day 3)
**What**: Applies spread_ratio filter, NBBO integrity check, and inventory check on detected events.

- Receives ImbalanceEvent from bucketer
- Starts 200ms timer measured from `exchange_timestamp` (not system clock)
- At timer expiry, reads current NBBO quote
- **Staleness check**: reject if `quote_age_at_entry > 200ms` (tightened from 500ms)
- **NBBO integrity checks** (spread_ratio is garbage if NBBO is broken):
  - Reject if bid >= ask (locked/crossed market)
  - Reject if quote update count in 200ms window < 2 (flickering/stale)
  - Log odd-lot share % per symbol; flag for review if > 30% in recent window
  - Track % locked/crossed events per symbol per day
- Computes spread_ratio = current_spread / baseline_spread
- **Spread baseline governance** (v4 — prevents circular monitoring):
  - `baseline_spread` = rolling 20-day median of inside spread during regular hours (9:45-15:45 ET), per symbol
  - Updated and stored daily in ClickHouse
  - Q1/Q2/Q3/Q4/Q5 quintile boundaries = frozen from research (never updated during shadow)
  - M6 distribution monitoring classifies events against frozen research quintile boundaries
  - This dual-track design means: spread_ratio adapts to current market structure (no stale baseline inflation), but classification of competitive vs shock remains frozen. If market structure shifts enough that all events migrate quintiles, M6 catches it as distribution drift.
- Accepts if spread_ratio < 1.0 OR > 2.0
- Checks net inventory cap (±6 bps)
- Tags sub-strategy: "competitive" or "shock"
- Logs `quote_age_at_entry` and spread trajectory (at event_end, +100ms, +200ms) for every evaluation

**Interface**:
```python
class EventLevelFilter:
    def __init__(self, inventory_tracker: InventoryTracker)
    async def evaluate(self, event: ImbalanceEvent, 
                       current_quote: Quote) -> Optional[TradeSignal]
    def get_nbbo_integrity_stats(self) -> NBBOIntegrityReport
```

**Depends on**: Step 1  
**Tests**: Verify spread_ratio computation, dead zone rejection, inventory cap, staleness rejection, locked/crossed rejection

---

### Step 3: OrderManager (Days 4-5)
**What**: Places and manages limit orders through IBKR adapter. Runs dual accounting with slippage decomposition.

- Receives TradeSignal from filter
- Places limit order via `IBKRAdapter.submit_limit_order()`
- Monitors fill status (callback from IBKR)
- On fill, starts exit monitoring:
  - Checks spread normalization every quote update
  - Checks timeout (30s timer)
  - Checks stop-loss (midpoint adverse > 3 bps)
- On exit, computes trade outcome + mechanism metrics + slippage breakdown
- Logs to ClickHouse

**Dual accounting** (addresses IBKR paper fill optimism):
- **Paper P&L**: actual IBKR paper fills (what the broker reports)
- **Model P&L**: simultaneously compute pessimistic queue model result for same event using live trade/quote data
- Model P&L is the authoritative number for success criteria
- Track `fill_optimism_ratio = paper_fill_rate / model_fill_rate`
- Queue model calibration: after 30-day shadow, segment `fill_optimism_ratio` by Q1/Q2 vs Q5, spread regime, and time-of-day to calibrate model for production

**Slippage decomposition** (forensic tooling — when drift occurs, you must know WHERE):

Per-trade fields logged:
```
expected_entry_price    # midpoint ± half-spread at signal time
actual_entry_price      # IBKR fill price
expected_exit_price     # midpoint at exit trigger time
actual_exit_price       # IBKR fill price
cancel_delay_ms         # time from cancel request to acknowledgment
partial_fill_ratio      # filled_size / requested_size
```

Computed:
```
entry_slippage_bps  = (actual_entry - expected_entry) / mid × 10000
exit_slippage_bps   = (actual_exit - expected_exit) / mid × 10000
total_slippage_bps  = entry_slippage_bps + exit_slippage_bps
```

Weekly report decomposes total slippage into entry, exit, cancel, and partial fill components.

**Net inventory calculation** (normalized by portfolio value):
```
net_inventory_bps = Σ (direction_i × shares_i × price_i / portfolio_value × 10000)
```
Updated per quote tick (mark-to-midpoint). 100 shares MSFT (~$430) weighs ~4.5x more than 100 shares WMT (~$95).

**Transactional crash recovery** (persists at every state transition, not just fills):

| State Transition | Persisted Data |
|------------------|----------------|
| Order submitted | `{order_id, symbol, side, intent: ENTRY, size, limit_price, timestamp}` |
| Entry filled | `{order_id, fill_price, fill_size, intent: MONITORING_EXIT, stop_attached: bool}` |
| Exit order submitted | `{exit_order_id, intent: EXIT_PENDING}` |
| Exit filled | `{intent: CLOSED, pnl_bps}` |

On restart:
1. Load persisted transaction log from disk
2. Query IBKR for status of ALL outstanding order_ids
3. For ENTRY orders: if filled → resume exit monitoring; if unfilled → cancel
4. For EXIT_PENDING: if filled → mark closed; if unfilled → resubmit
5. For positions without exit orders → immediately place exit with current market state

This prevents the gap where engine crashes after order submit but before fill — leaving unprotected exposure.

**Depth logging for scaling calibration** (v4 — queue model lacks real depth data):
- Log for every entry: `nbbo_bid_size`, `nbbo_ask_size` at entry moment
- Compute `order_size / relevant_side_size` ratio (clip as % of visible depth)
- If ratio > 50% for any trade, flag as "capacity-constrained"
- This gives real depth data to calibrate scaling estimates post-shadow (Polygon doesn't provide depth, but live IBKR market data does)

**State per open order**:
- entry_price, entry_time, our_side, baseline_spread
- filled: bool, fill_time
- exit_price, exit_time, exit_reason
- spread_ratio, sub_strategy, imbalance_magnitude
- quote_age_at_entry (staleness check)
- expected_entry_price, expected_exit_price (for slippage decomposition)
- nbbo_bid_size, nbbo_ask_size at entry (for depth logging)

**Interface**:
```python
class OrderManager:
    def __init__(self, broker: IBKRAdapter, logger: ShadowLogger,
                 portfolio_value: float)
    async def place_order(self, signal: TradeSignal) -> str  # order_id
    def on_quote_update(self, symbol: str, quote: Quote) -> None
    def on_fill(self, order_id: str, fill_price: float, fill_size: int) -> None
    def get_net_inventory_bps(self) -> float
    def get_open_positions(self) -> List[OpenPosition]
    async def recover_state(self) -> None  # transactional crash recovery
    def get_slippage_decomposition(self) -> SlippageReport
```

**Depends on**: Step 2, existing IBKRAdapter  
**Tests**: Mock broker, verify 3-way exit logic, inventory tracking, transactional crash recovery (mid-submit crash), slippage decomposition accuracy

---

### Step 4: MechanismMonitor (Day 6)
**What**: Tracks all 8 KPIs from filled trades + market data.

Receives trade outcomes from OrderManager. Computes:

- **M1**: Mechanism health surface (multi-dimensional, replaces single half-life):
  1. Median `spread_ratio` amplitude at entry (baseline from research)
  2. Median `time_to_normalization` (compression speed)
  3. Event frequency per symbol per day (activation rate)
  - Trigger auto-review if any 2 of 3 degrade > 30% from rolling 30-day baseline
  - Trigger auto-pause if all 3 degrade > 30% simultaneously
  - Half-life drift alone is one-dimensional; mechanism can decay via lower amplitude (weaker shocks), fewer events (tighter market), or faster normalization (HFTs)
- **M2**: Split PnL by sub-strategy (competitive vs shock)
- **M3**: Fill rate — dual accounting:
  - Paper fill rate (actual IBKR fills)
  - Model fill rate (pessimistic queue model on same events)
  - `fill_optimism_ratio = paper / model` (alert if > 1.5)
  - Model P&L is the authoritative success metric
  - Segmented by Q1/Q2 vs Q5 for queue model calibration
- **M4**: Net inventory beta to SPY (precisely specified):
  - Daily: regress `net_inventory_bps` vs SPY 1-min returns (intraday)
  - Track rolling 20-day beta coefficient
  - Alert if |beta| > 0.25 (flow alpha is partially disguised index momentum)
  - Requires SPY 1-min data via Polygon
- **M5**: Daily fill count, event count, utilization rate
- **M6**: Spread ratio distribution (leading structural indicator):
  - Rolling 30-day distribution of `spread_ratio` at entry for all detected events
  - Track: % events in Q1/Q2 (competitive), Q3/Q4 (dead zone), Q5 (shock)
  - Baseline from research
  - Alert if Q5 frequency drops > 40% from baseline (shock mechanism weakening)
  - Alert if Q1/Q2 frequency drops > 30% from baseline (competitive mechanism weakening)
- **M7**: Slippage decomposition (from OrderManager forensic fields):
  - Rolling mean entry_slippage_bps, exit_slippage_bps, cancel_delay_ms
  - Baseline anchored to Step 7 historical distributions (not first-week live data)
  - Alert if any component drifts > 50% from historical baseline
  - Weekly report breaks total slippage into entry/exit/cancel/partial components
- **M8**: NBBO integrity (from EventLevelFilter):
  - % locked/crossed rejections per day
  - Quote update frequency per symbol
  - Odd-lot dominance ratio
  - Alert if locked/crossed rate > 2% or quote frequency drops > 30%

Kill condition enforcement (v4 — horizon-aligned to prevent false positives):

**Per-trade checks** (acute risk, checked on every trade completion):
- Net inventory cap breach (±6 bps)
- Absolute latency cap breach (ingest/order/cancel)
- Intraday loss limit

**Daily close checks** (structural risk, evaluated once at end of day):
- M1 mechanism health surface (2-of-3 degradation)
- Rolling 30-day mean PnL < 0.5 bps
- Live fill rate < 60% of modeled baseline
- High-vol pairwise correlation > 0.30 sustained 5 days
- Compression half-life drift > 100% for 10 consecutive days
- Rolling 5-day peak-to-trough drawdown > 50 bps (see definition below)

Mixing per-trade evaluation with structural metrics that need longer windows causes sparse-sample false positives during low-activity weeks.

- Auto-pauses engine if any condition triggered
- Logs kill event to ClickHouse

**Interface**:
```python
class MechanismMonitor:
    def __init__(self, baselines: ResearchBaselines)
    def on_trade_complete(self, outcome: TradeOutcome) -> None
    def on_daily_close(self) -> DailyReport
    def on_weekly_close(self) -> WeeklyReport
    def check_kill_conditions(self) -> Optional[KillCondition]
    def check_mechanism_health(self) -> MechanismHealthReport
    def get_spread_ratio_distribution(self) -> SpreadRatioReport
```

**Depends on**: Step 3  
**Tests**: Verify multi-dimensional mechanism health detection, kill condition logic, M6/M7/M8 tracking

---

### Step 5: ShadowLogger (Day 6)
**What**: Logs everything to ClickHouse + generates reports.

- Every detected event → `shadow_events`
- Every order placed → `shadow_orders`
- Every fill + exit → `shadow_fills` (with all mechanism metrics)
- Daily aggregates → `shadow_daily`
- Weekly markdown reports → `results/shadow/`

**Depends on**: Step 0  
**Tests**: Verify ClickHouse inserts, report generation

---

### Step 6: LiquidityShadowEngine (Days 7-8)
**What**: Main orchestrator that connects all components.

- Connects to Polygon WebSocket (trades + quotes for MSFT, NVDA, TSLA, WMT)
- Connects to IBKR paper trading
- Creates per-symbol StreamingVolumeBucketer
- Routes events through filter → order manager → monitor
- Handles lifecycle: start, pause, resume, stop
- Respects market hours (9:30-16:00 ET, skip first/last 15 min)
- **Pre-flight checks** on startup:
  - NTP clock sync verification (offset < 10ms)
  - IBKR connectivity + position query
  - Polygon WebSocket connectivity
  - ClickHouse connectivity
  - If any pre-flight fails → refuse to start
- **Crash recovery**: on startup, calls `OrderManager.recover_state()` — transactional recovery handles mid-submit crashes, not just post-fill
- **InfrastructureLatencyMonitor** (replaces TimeSyncMonitor): runs continuously, tracks:
  - Clock sync (exchange_ts vs system_ts)
  - Ingest latency p50/p95/p99 (Polygon → system)
  - Order submission RTT p50/p95/p99 (system → IBKR)
  - Cancel acknowledgment p50/p95/p99 (IBKR → system)
  - Baselines anchored to Step 7 historical distributions; live rolling 10-day window for drift detection
  - **Relative**: auto-pause if any path's p95 > 2× rolling 10-day baseline
  - **Absolute**: auto-pause if ingest p95 > 250ms, order RTT p95 > 400ms, or cancel ack median > 500ms
- **NBBO integrity monitoring**: per-symbol locked/crossed rate, quote update frequency, odd-lot dominance

**Interface**:
```python
class LiquidityShadowEngine:
    def __init__(self, config: ShadowConfig)
    async def initialize(self) -> None  # pre-flight checks + crash recovery
    async def run(self) -> None  # main event loop
    async def pause(self) -> None
    async def resume(self) -> None
    async def stop(self) -> None  # cancel open orders, flatten positions
```

**Depends on**: Steps 1-5  
**Tests**: End-to-end with mock Polygon + mock IBKR, crash recovery scenario

---

### Step 7: Full Historical Backtest (Days 9-11)
**What**: Run the complete shadow engine against all 130 days of ClickHouse data as a sequential trading simulation. This is NOT the per-event research analysis — it is the full pipeline operating as a trading system with state.

**Why this exists**: Research experiments (Branch B) computed per-event statistics independently. They never ran the full pipeline sequentially with:
- Inventory state carrying forward between trades
- The spread_ratio filter actually rejecting events in real time
- Position limits binding and blocking new entries
- Daily P&L accumulating including zero-event periods
- Kill conditions being evaluated continuously
- The two sub-strategies (competitive/shock) mixing in the real event stream

This layer catches bugs, calibration errors, and structural discrepancies between "pooled statistics" and "sequential operation."

**Implementation**: `core_engine/microstructure/shadow/historical_backtest.py`

**Data source**: ClickHouse `microstructure_trades`, `microstructure_quotes`, `microstructure_buckets`

**Architecture**:
```
For each trading day (chronological):
  1. Load pre-computed buckets for all 4 symbols
  2. Identify extreme imbalance events (same p95 thresholds)
  3. For each event (chronological across symbols):
     a. Wait 200ms (simulated) → read quote state from ClickHouse
     b. Compute spread_ratio → apply event-level filter
     c. Check inventory cap (±6 bps net) → skip if exceeded
     d. Check per-symbol position limit (max 1 open) → skip if exceeded
     e. Simulate fill using pessimistic queue model (last in queue)
     f. If filled → manage exit (spread normal / timeout / stop)
     g. Update inventory state, daily P&L
  4. At day end:
     a. Compute daily mechanism metrics (M1-M5)
     b. Check kill conditions
     c. Log to shadow_backtest tables
  5. Generate comprehensive report
```

**Key differences from research Branch B**:
- Events processed **sequentially** with carry-forward state (not independently)
- Inventory cap actively **blocks** trades when saturated
- Spread_ratio filter **rejects** Q3/Q4 events (not computed for all)
- Position limits **prevent** overlapping trades in same symbol
- Kill conditions checked daily — verifies they don't fire during research period
- Sub-strategy tagging (competitive vs shock) tracked per trade

**Capital scaling simulation** (run alongside primary backtest):
- Run the full 130-day backtest at 3 clip sizes: 100, 500, 1000 shares
- Queue model already parameterizes size; larger clips = lower fill probability, more impact
- Report scaling elasticity: PnL per clip, fill rate per clip, edge degradation curve
- This gives scaling data before shadow, not after green-light

**Inventory clustering stress test** (v4 — synthetic pathological scenario):
- Inject synthetic day: 10 Q5 events within 2 minutes across all 4 symbols simultaneously
- Verify net_inventory cap correctly blocks directional stacking
- Verify kill logic doesn't over-trigger from sparse-sample noise
- Verify no unprotected directional exposure exceeds ±6 bps
- This tests the scenario live markets will eventually create; better to test it now

**Report output**: `results/shadow_backtest/`
- Full equity curve (daily cumulative bps)
- Mechanism KPIs per day (M1-M8)
- Events detected vs filtered vs filled
- Filter rejection breakdown (dead zone, inventory cap, position limit, NBBO integrity)
- **Acceptance rate by quintile under inventory constraint** (v4 — checks whether sequential blocking accidentally suppresses Q5 shock sub-strategy)
- Sub-strategy P&L split
- Kill condition status per day (none should fire)
- Comparison table: backtest results vs research pooled statistics
- Scaling elasticity table (100 / 500 / 1000 shares)
- Slippage decomposition summary
- Inventory clustering stress test result

**Pass criteria** (tightened per external review — frozen logic should not drift):
1. Total P&L within ±15% of research expectation
2. Fill rate within ±10% of research baseline (77%)
3. Hit rate within ±8% of research baseline (54%)
4. No kill condition fires during the 130-day period
5. Sub-strategy split shows both competitive and shock contributing
6. **Drawdown**: no rolling 5-day peak-to-trough > 50 bps (precisely defined; a single bad day ≠ kill, sustained bleed over a week = kill)
7. Spread ratio distribution (M6) matches research baseline within 20%
8. Inventory stress test passes: cap correctly blocks stacking, no exposure breach

**Fail actions**:
- If P&L drift > 15% → investigate filter/inventory blocking logic; sequential state is changing economics
- If kill condition fires → recalibrate threshold (requires v1.8 and quant review)
- If fill rate diverges → queue model mismatch in sequential vs independent simulation
- If Q5 acceptance rate disproportionately low → inventory cap interacting asymmetrically with volatility clustering

**Depends on**: Steps 1-6  
**This is the hard gate**: If the backtest doesn't pass, the shadow engine has a bug. Do not proceed to live paper until this passes.

---

### Step 8: Historical Replay Validation (Day 12)
**What**: Feed raw recorded trades/quotes through the StreamingVolumeBucketer (not pre-computed buckets) and verify the streaming engine produces identical bucket boundaries to offline processing.

- Replay **20 symbol-days** (expanded from 5 per external review):
  - 5 per symbol (MSFT, NVDA, TSLA, WMT)
  - Selection: 2 highest-volume days, 2 lowest-volume days, 1 median day per symbol
  - Must include at least 1 day from each temporal block
- Compare: bucket start/end timestamps, flow_imbalance values, event detection
- Verify deterministic: same input → same output
- **Additional validation**: Compare imbalance distribution from streaming vs offline across all 20 days
  - p95 threshold divergence ≤ 5% (if streaming produces different p95, event detection frequency shifts)

**Purpose**: Proves the streaming bucketer matches the offline bucketer exactly. The backtest (Step 7) used pre-computed buckets. This step validates that the live streaming path produces those same buckets. The expanded scope catches edge cases in high-vol (trade bursts, quote flicker) and low-vol (sparse events, opening auction spillover) regimes.

**Additional: Streaming Lee-Ready classification drift test** (per external review):
- Replay 30 full symbol-days (extending beyond the 20-day bucket test above)
- Compare aggressor classification distribution: streaming vs offline
- **Tightened threshold** (v3): 3% p95 divergence = hard pass; 3-5% = investigation zone (root cause analysis required); >5% = hard fail
- At thin edge, even 5% classification error can shift sub-strategy attribution and Q1/Q2 vs Q5 boundaries

**Depends on**: Step 7  
**Pass criteria**: 100% bucket boundary match, ≤0.1% flow_imbalance divergence, ≤5% imbalance distribution divergence, ≤3% Lee-Ready classification drift (3-5% triggers investigation)

---

### Step 9: Paper Trading Integration Test (Day 13)
**What**: Connect to live Polygon WebSocket + IBKR paper. Run for 1 trading day.

- Verify WebSocket connection stability
- Verify bucketing produces reasonable event counts
- Verify orders placed successfully via IBKR paper
- Verify fill callbacks received
- Verify ClickHouse logging working
- Verify mechanism monitors computing

**Purpose**: Smoke test before 30-day shadow.  
**Depends on**: Step 8

---

### Step 10: 30-Day Shadow Execution (Days 14-43)
**What**: Run the frozen system for 30 trading days. No code changes.

- Daily: check mechanism dashboard (M1-M8), verify no kill conditions
- Daily: verify InfrastructureLatencyMonitor healthy — no clock drift, no latency variance spikes
- Daily: check dual accounting — compare paper fills vs model fills
- Daily: check NBBO integrity stats — locked/crossed rate, quote frequency
- Weekly: structured review of all monitors, spread_ratio distribution trend, slippage decomposition
- Weekly: compute hypothetical model P&L at 500/1000 shares (scaling elasticity tracking)
- End of period: comprehensive report for external quant review, including:
  - Queue model calibration data (fill_optimism_ratio segmented by sub-strategy/regime/TOD)
  - Slippage decomposition summary (entry vs exit vs cancel vs partial)
  - Latency distribution evolution (did infrastructure degrade over 30 days?)
  - Scaling elasticity estimates at 500/1000 shares
  - Depth profile: distribution of `order_size / nbbo_side_size` ratios; % capacity-constrained trades
  - SPY beta evolution (rolling 20-day |beta|, confirm < 0.25)

**Comparison baseline**: The backtest (Step 7) provides the exact numbers shadow must replicate. If shadow diverges from the backtest, the divergence is from execution reality, not from logic — which is exactly what we want to measure.

**Do not over-engineer**: Shadow's purpose is measuring live execution drift. If Step 7 passes, the only unknown is execution. Don't add features, monitors, or optimizations during the 30-day period. Simplicity is the feature.

---

## File Structure

```
core_engine/microstructure/shadow/
├── __init__.py
├── constants.py              # v1.7 frozen parameters
├── types.py                  # ImbalanceEvent, TradeSignal, TradeOutcome, SlippageBreakdown, etc.
├── streaming_bucketer.py     # Step 1
├── event_filter.py           # Step 2 (NBBO integrity checks)
├── order_manager.py          # Step 3 (dual accounting, slippage decomposition, transactional recovery)
├── mechanism_monitor.py      # Step 4 (M1-M8: mechanism surface, slippage, NBBO integrity)
├── shadow_logger.py          # Step 5
├── infra_latency_monitor.py  # Pre-requisite (clock sync + 3-path latency variance tracking)
├── engine.py                 # Step 6 (pre-flight, transactional recovery, latency monitor)
├── historical_backtest.py    # Step 7 (full sequential backtest + scaling simulation)
└── replay_validator.py       # Step 8 (20+30 symbol-days, Lee-Ready drift ≤3%)
```

---

## Dependencies

| Component | Depends On | Existing? |
|-----------|-----------|-----------|
| Polygon WebSocket | `core_engine/data/feeds/polygon_realtime.py` | Yes |
| IBKR Adapter | `core_engine/broker/adapters/ibkr_adapter.py` | Yes |
| Volume-clock logic | `core_engine/microstructure/pipeline/volume_clock.py` | Yes (offline) |
| Lee-Ready classification | `core_engine/microstructure/pipeline/lee_ready.py` | Yes (offline) |
| ClickHouse client | aiohttp (same as research) | Yes |

**New dependencies**: None. Everything builds on existing infrastructure.

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| WebSocket disconnection | Reconnection with exponential backoff (existing in PolygonRealtimeFeedAdapter) |
| IBKR disconnection | OrderManager pauses, transactional recovery on reconnect |
| Crash with open orders | Transactional state log: persists at submit/fill/exit transitions; restart queries IBKR for all outstanding order_ids |
| Crash between submit and fill | Transaction log records intent state; restart detects unprotected exposure, cancels or resumes |
| ClickHouse unavailable | Buffer logs in memory, flush when available |
| Stale quotes | Track quote_age, skip events with stale NBBO (>200ms) |
| Locked/crossed markets | NBBO integrity check rejects entries; tracked in M8 |
| Quote flickering | Require ≥2 quote updates in 200ms window; reject if insufficient |
| Market hours | Hard gate: no events processed outside 9:45-15:45 ET |
| Parameter drift | All constants in frozen constants.py, loaded once at startup |
| Clock drift (offset) | NTP pre-flight, continuous exchange_ts vs system_ts tracking, auto-pause on drift |
| Latency variance (jitter) | InfrastructureLatencyMonitor: p50/p95/p99; relative (2× rolling 10-day) AND absolute caps (250/400/500ms) |
| Paper fill optimism | Dual accounting: model P&L (pessimistic queue) is authoritative; calibrate model from 30-day shadow data |
| Lee-Ready streaming drift | 30-day replay at ≤3% hard pass threshold; continuous classification_confidence monitoring |
| Structural regime drift | M6 spread_ratio distribution (frozen research quintile boundaries) + M1 mechanism health surface (3-variable) |
| Spread baseline inflation | Rolling 20-day median baseline per symbol; Q quintile boundaries frozen from research |
| Baseline anchoring bias | All baselines (latency, slippage, mechanism) anchored to Step 7 historical distributions, not first-week live data |
| Kill false positives | Horizon-aligned: per-trade checks for acute risk only; structural kills at daily close |
| Inventory clustering bias | Synthetic stress test in Step 7; acceptance rate by quintile in backtest report |
| Depth-blind scaling | Live NBBO depth logged per entry; order_size/depth ratio tracked for capacity calibration |
| Slippage attribution gap | M7 slippage decomposition: entry/exit/cancel/partial components tracked per trade |
| Odd-lot distortion | Track odd-lot share % per symbol; flag if >30% |
| Capacity unknown | Scaling simulation at 100/500/1000 shares in Step 7; hypothetical scaling tracked during shadow |

---

## Timeline

| Day | Deliverable |
|-----|------------|
| 1 | Step 0: Constants + ClickHouse schema |
| 2-3 | Step 1: StreamingVolumeBucketer + tests |
| 3 | Step 2: EventLevelFilter + tests |
| 4-5 | Step 3: OrderManager + tests |
| 6 | Step 4-5: MechanismMonitor + ShadowLogger |
| 7-8 | Step 6: LiquidityShadowEngine |
| 9-11 | **Step 7: Full Historical Backtest (THE HARD GATE)** |
| 12 | Step 8: Streaming replay validation |
| 13 | Step 9: Paper trading integration test (1-day smoke) |
| 14-43 | Step 10: 30-day shadow execution |

**Critical path**: Step 7 is the gate. If the backtest doesn't match research within tolerance, Steps 8-10 are blocked until the discrepancy is resolved.
