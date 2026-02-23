# Phase 1 + Phase 2 Implementation Blueprint

**Purpose**: Operational engineering specification for Phase 1 (Data Ingestion) and Phase 2 (Foundation Diagnostics) as defined in FAHS v1.5.

**Scope**: This document maps the sealed hypothesis requirements to the EXISTING codebase architecture. Every module, class, table, and config is specified relative to what already exists. No architectural fantasies — only what integrates with the production codebase.

**Governing Document**: `docs/flow_alpha_hypothesis_set.md` (FAHS v1.5 SEALED). All rejection criteria, thresholds, and gates are imported from FAHS — not re-derived here. This blueprint is the HOW. FAHS is the WHAT and WHY.

**Review History**:
- v1.0 — Initial draft from codebase audit + FAHS v1.5 mapping
- v1.1 — Round 1 expert review (regime-conditioned persistence, Lee-Ready quality, elasticity Phase 2e, conditional slippage, edge distribution shape)
- v1.2 — Round 2 expert review (elasticity causality, confidence regimes, economic monotonicity, cross-symbol correlation, depth multipliers, temporal stability)
- v1.3 — Round 3 final review (hierarchical gate ordering, volume-clock causality, baseline-adaptive monotonicity, state-dependent cost model, event beta, constrained P&L simulation, hash audit trail, parallelism ordering, constants versioning)
- v1.4 — Pre-implementation review (Week 0 feasibility probe, universe liquidity guardrails, resequenced execution plan, data quality report deliverable, Polygon API confirmation checklist, deterministic replay gate enforcement)
- v1.4.1 — Final go/no-go review (ClickHouse storage/query performance hardening, Polygon timestamp semantics verification, anti-rationalization discipline clause, compression codec recommendations, INSERT-only immutability rule)
- v1.5 — Storage-constrained revision (initial dataset sizing)
- v1.6-FINAL LOCKED — Expert-validated storage math (10 symbols × 130 days, 220GB target / 250GB kill / 300GB cap, 3×43-day temporal blocks, per-tier row estimates, statistical power safeguards, data minimization rules, pre-download storage audit, storage projection in probe)

---

## 0. WHAT ALREADY EXISTS (Codebase Audit)

Before building anything, understand what we're starting from:

### 0.1 Existing Infrastructure We WILL Reuse

| Component | Location | Capability | Reuse |
|-----------|----------|------------|-------|
| Polygon REST client | `core_engine/data/feeds/polygon_rest.py` | `get_historical_trades()`, `get_historical_quotes()` — paginated v3 endpoints, nanosecond timestamps | Direct reuse for tick/quote ingestion |
| Polygon WebSocket | `core_engine/data/feeds/polygon_realtime.py` | Real-time trades (`T.*`), quotes (`Q.*`) — Advanced tier | Reuse for live shadow-mode (Phase 4+) |
| ClickHouse connection | `core_engine/data/manager.py` | `_execute_query()` via aiohttp, ArrowStream/TSV formats | Reuse for new table queries |
| Data validation | `core_engine/data/validation/validator.py` | Quality scoring, anomaly detection, completeness checks | Extend for tick-level validation |
| Experiment framework | `backtest/experiments/base_experiment.py` | Standardized experiment execution, results, config-driven | Extend with new diagnostic experiment type |
| YAML config system | `core_engine/config/yaml_loader.py` | Includes, deep-merge, cycle detection | Reuse for Phase 1/2 config |
| Market calendar | `core_engine/data/market_calendar.py` | RTH filtering, session boundaries | Reuse for trade/quote filtering |

### 0.2 Existing Infrastructure We CANNOT Reuse

| Component | Why | What Replaces It |
|-----------|-----|------------------|
| `polygon_data.ticks` table | Stores aggregated OHLCV bars (1-min), not raw trades/quotes | New `polygon_data.trades` and `polygon_data.quotes` tables |
| Feature engineer (`processing/features/engineer.py`) | Entirely bar-based. Computes momentum, RSI, MACD from OHLCV. Wrong data granularity. | New `core_engine/microstructure/` module |
| VPIN calculation (`processing/indicators/engine.py`) | BVC-based from 1-min bars. Not true order flow. | Recomputed from Lee-Ready classified tick data in volume-clock buckets |
| Pipeline orchestrator (`processing/pipeline_orchestrator.py`) | Phase 1→4 pipeline assumes bar data. | New microstructure pipeline (parallel, not replacement) |

### 0.3 What Must Be Built NEW

| Module | Purpose | Dependencies |
|--------|---------|--------------|
| `core_engine/microstructure/` | New top-level module for tick/quote processing | Polygon REST, ClickHouse |
| `core_engine/microstructure/ingestion/` | Bulk historical download + ClickHouse load | Polygon REST client |
| `core_engine/microstructure/classification/` | Lee-Ready trade classifier | Raw trades + quotes from ClickHouse |
| `core_engine/microstructure/bucketing/` | Volume-clock bucket engine | Classified trades |
| `core_engine/microstructure/metrics/` | Flow metric computation (signed_volume, imbalance, VPIN, elasticity) | Volume buckets |
| `core_engine/microstructure/diagnostics/` | Phase 2 gate computations | Flow metrics |
| `backtest/experiments/foundation_diagnostic.py` | New experiment type for Phase 2 gates | Diagnostics module |
| ClickHouse DDL | New tables for trades, quotes, volume buckets, diagnostic results | ClickHouse server |
| Config YAML | `core_engine/config/catalog/microstructure/` | YAML loader |

---

## 0.5 FALSIFICATION DATASET SPECIFICATION (Frozen)

The dataset is designed to **kill the hypothesis cheaply**, not prove it. It is the smallest
dataset that can stress persistence, monotonicity, cost fragility, cross-symbol correlation,
and regime instability — within a 300GB storage budget.

```
FALSIFICATION_DATASET_v1 (FINAL):

  symbols:      10 (3 Tier A / 3 Tier B / 4 Tier C)
                adjustable down to 9 or up to 12 after Week 0 probe storage math
  sectors:      ≥ 5 GICS sectors
  period:       130 trading days (~6 calendar months)
  data:         full trades + NBBO quotes (Polygon Stock Advanced)
  compression:  ZSTD (with Delta/DoubleDelta/T64 codecs per column type)
  partition:    by trading_date
  order_by:     (symbol, sip_timestamp)
  storage_target: 220 GB compressed
  storage_kill:   250 GB (halt ingest immediately)
  storage_hard_cap: 300 GB (absolute maximum including indices + diagnostics)
  mutability:   INSERT only — no UPDATEs
```

**Storage math (expert-validated)**:

Per-symbol per-day raw data (blended across tiers):
```
  Component   | Rows/day   | Compressed bytes/row | MB/day
  ------------|------------|---------------------|--------
  Trades      | ~250k avg  | ~45 bytes           | ~11 MB
  Quotes      | ~1.5M avg  | ~50 bytes           | ~75 MB
  ------------|------------|---------------------|--------
  Total       | ~1.75M     |                     | ~86 MB
```

Tier-specific breakdown:
```
  Tier | Trades/day  | Quotes/day  | Total/day
  -----|-------------|-------------|----------
  A    | 300k–800k   | 2M–5M      | ~140 MB
  B    | 100k–300k   | 800k–2M    | ~80 MB
  C    | 50k–100k    | 300k–800k  | ~40 MB
```

Total projection for recommended configuration:
```
  Config              | Raw estimate | +overhead (buckets, diag, indices) | Total
  --------------------|--------------|-----------------------------------|---------
  10 sym × 130 days   | ~112 GB      | +25-35 GB                         | ~140-150 GB
  12 sym × 130 days   | ~134 GB      | +30-40 GB                         | ~165-175 GB
  9 sym × 130 days    | ~100 GB      | +22-30 GB                         | ~125-130 GB
```

Conclusion: 300GB is safe for 12 symbols. 10 symbols is the clean target under constraint.

**What this dataset CAN falsify**:
- Persistence half-life viability
- Monotonicity substance (decile analysis with ≥200 events per symbol)
- Elasticity regime conditioning
- Slippage realism (conditional spread model)
- Cross-symbol return correlation
- Temporal stability across 3 × ~43-day blocks
- 1 full earnings cycle exposure

**What this dataset CANNOT yet validate**:
- Extreme regime robustness (would need 12+ months)
- Long-horizon decay (would need multi-year)
- Full capacity scaling (would need 20+ symbols)
- Rare-event behavior (would need multi-year data)

That is acceptable. Phase 1 is about survival, not scaling.

**Statistical power safeguards** (downsizing mitigation):
- Minimum 200 imbalance events per symbol before running full decile tests
- If event count < 200 for a symbol: merge deciles to quintiles (5 bins instead of 10)
- If Tier C produces < 200 events per symbol across 130 days → flag as underpowered,
  report quintile results only, note limitation in decision report
- Monotonicity gate adapts: if using quintiles, require 3/4 adjacent pairs monotonic
  (instead of 7/9 for deciles)

**Data minimization rules** (storage discipline):
- Drop raw API JSON payloads immediately after parsing into typed columns
- Do NOT store unused condition codes — extract only trade condition flags needed
  for odd-lot / irregular detection, discard raw array if not needed
- Do NOT store redundant timestamps (if exchange_timestamp = sip_timestamp, store only one)
- Do NOT create debug/temp tables in ClickHouse — use local files for debugging
- Use `LowCardinality(String)` for all string columns (symbol, metric_name)
- Use appropriate codecs (see DDL section)
- Partition by month (not day) if part count exceeds 1000

**Execution discipline**:
- Do NOT expand beyond 12 symbols under any circumstance
- Do NOT extend beyond 130 days mid-process
- Do NOT add names after seeing results
- If storage exceeds 250GB during ingest → HALT immediately, assess
- Freeze it. Run it. Accept outcome.

---

## 1. PHASE 1 — DATA INGESTION

### 1.1 Universe Construction

**Config**: `core_engine/config/catalog/microstructure/universe.yaml`

```yaml
universe:
  # Tier definitions — frozen after 20-day observation period
  tiers:
    A:
      label: "Mega-cap, tight spread"
      median_spread_bps_max: 3.0
      min_daily_trades: 50000
      min_daily_dollar_volume: 500_000_000
      symbols: []  # Populated by universe scanner
    B:
      label: "Large-cap, moderate spread"
      median_spread_bps_max: 8.0
      min_daily_trades: 20000
      min_daily_dollar_volume: 100_000_000
      symbols: []
    C:
      label: "Mid-cap, wider spread"
      median_spread_bps_max: 15.0
      min_daily_trades: 10000
      min_daily_dollar_volume: 50_000_000
      symbols: []

  # Diversity constraints (final falsification dataset)
  min_sectors: 5  # Minimum distinct GICS sectors
  symbols_per_tier:
    A: 3            # Tier A: high liquidity, tight spreads
    B: 3            # Tier B: moderate liquidity
    C: 4            # Tier C: thin / wider spread — extra symbol for fragility testing
  target_symbols: 10        # 3A + 3B + 4C; adjustable 9-12 after probe
  max_symbols_total: 12     # Hard cap — do not expand beyond this

  # Observation period for tier classification
  classification_observation_days: 20
  classification_freeze: true  # Once classified, no reclassification during study

  # Hard liquidity guardrails (pre-implementation review — applied to ALL tiers)
  liquidity_filters:
    min_nbbo_size_multiple: 5     # Exclude if median NBBO quoted size < 5× intended clip
    min_daily_trades_floor: 50000 # Tier A/B floor (Tier C uses tier-specific min above)
    tier_c_min_daily_trades: 50000 # Tier C absolute floor — no thin names
    max_odd_lot_only_day_pct: 0.03 # Exclude if >3% of days are odd-lot-only
    # These prevent diagnosing microstructure artifacts from illiquid names.
    # Universe selection must be mechanical and logged.

  # Required statistics logged per symbol (frozen in universe_classification.json)
  logged_stats:
    - median_quoted_size_at_nbbo    # Shares at best bid/ask
    - median_spread_bps             # Realized spread
    - median_intraday_trade_count   # Total trades per day
    - spread_volatility_bps         # σ of spread
    - intraday_volume_ushape_score  # Concentration at open/close
    - gics_sector                   # For diversity constraint

  # Tier C feasibility gate
  participation_feasibility:
    max_pct_of_3min_volume: 0.5  # 0.5% rolling 3-min volume
    min_feasible_hours_per_day: 4  # Must be feasible for at least 4 RTH hours
    # If Tier C name fails this → removed from universe. No romantic attachment.
```

**Implementation**: `core_engine/microstructure/ingestion/universe_scanner.py`

```
class UniverseScanner:
    """
    Scans candidate symbols over a 20-day observation window.
    Computes: median spread, spread volatility, 3-min volume distribution,
    intraday volume U-shape, daily trade count, GICS sector.
    Outputs frozen tier classification.
    """
    Dependencies:
      - PolygonRestService (for ticker details, historical bars)
      - ClickHouseDataManager (for existing 1-min bar data if available)

    Methods:
      async scan_candidates(candidates: List[str], observation_start: date, observation_end: date) -> UniverseClassification
      _compute_spread_profile(symbol, trades_df, quotes_df) -> SpreadProfile
      _compute_volume_profile(symbol, trades_df) -> VolumeProfile
      _check_participation_feasibility(symbol, volume_profile, tier) -> bool
      _assign_tier(spread_profile, volume_profile) -> Tier

    Output:
      UniverseClassification dataclass:
        - tier_assignments: Dict[str, Tier]  # symbol → tier
        - spread_profiles: Dict[str, SpreadProfile]
        - volume_profiles: Dict[str, VolumeProfile]
        - excluded_symbols: List[Tuple[str, str]]  # (symbol, reason)
        - sectors: Dict[str, str]  # symbol → GICS sector
        - observation_period: Tuple[date, date]
        - frozen: bool = True
```

**Process**:
1. Start with ~30-40 candidate symbols (large-cap + selected mid-caps).
2. Download 20 days of 1-min bars (already in ClickHouse if available) + sample tick/quote data (2-3 days) for spread profiling.
3. Compute per-symbol: median spread (bps), spread σ, median 3-min volume, daily trade count, intraday volume curve.
4. Assign tiers. Remove Tier C names that fail participation feasibility.
5. Verify ≥5 GICS sectors represented.
6. Freeze classification. Output `universe_classification.json`.

---

### 1.2 ClickHouse Schema — Raw Tick/Quote Storage

**DDL file**: `core_engine/microstructure/schema/clickhouse_ddl.sql`

```sql
-- Raw trades table
CREATE TABLE IF NOT EXISTS polygon_data.trades (
    symbol         LowCardinality(String),
    sip_timestamp  Int64,              -- Nanoseconds since epoch (SIP receipt time)
    exchange_timestamp Int64,          -- Nanoseconds (exchange report time, if available)
    price          Float64,
    size           UInt32,
    exchange_id    UInt8,              -- Polygon exchange code
    conditions     Array(Int32),       -- Trade condition codes
    tape           UInt8,              -- Tape A/B/C
    trade_id       String,            -- Polygon trade ID for dedup
    ingestion_date Date               -- Partition key
) ENGINE = MergeTree()
PARTITION BY ingestion_date
ORDER BY (symbol, sip_timestamp)
SETTINGS index_granularity = 8192;

-- Raw NBBO quotes table
CREATE TABLE IF NOT EXISTS polygon_data.quotes (
    symbol         LowCardinality(String),
    sip_timestamp  Int64,              -- Nanoseconds since epoch
    bid_price      Float64,
    ask_price      Float64,
    bid_size       UInt32,
    ask_size       UInt32,
    bid_exchange   UInt8,
    ask_exchange   UInt8,
    conditions     Array(Int32),
    ingestion_date Date
) ENGINE = MergeTree()
PARTITION BY ingestion_date
ORDER BY (symbol, sip_timestamp)
SETTINGS index_granularity = 8192;

-- Volume-clock buckets (computed, not raw)
CREATE TABLE IF NOT EXISTS polygon_data.volume_buckets (
    symbol             LowCardinality(String),
    bucket_id          UInt64,             -- Sequential bucket number per symbol per day
    bucket_start_ns    Int64,              -- First trade nanosecond timestamp
    bucket_end_ns      Int64,              -- Last trade nanosecond timestamp
    bucket_volume      UInt64,             -- Target bucket volume (ADV / target_buckets)
    actual_volume      UInt64,             -- Actual volume in bucket
    num_trades         UInt32,
    open_price         Float64,
    close_price        Float64,
    high_price         Float64,
    low_price          Float64,
    vwap               Float64,
    -- Lee-Ready classified flow
    signed_volume      Int64,              -- Net signed volume (buy - sell)
    unsigned_volume    UInt64,             -- Total volume
    buy_volume         UInt64,
    sell_volume        UInt64,
    indeterminate_volume UInt64,           -- Midpoint trades (unclassified)
    -- Classification quality
    classification_confidence Float32,     -- % unambiguously classified
    tick_rule_fallback_pct    Float32,     -- % classified by tick rule
    -- Quote context at bucket boundaries
    bid_at_start       Float64,
    ask_at_start       Float64,
    bid_at_end         Float64,
    ask_at_end         Float64,
    median_spread_bps  Float32,
    -- Derived metrics (computed during bucketing)
    flow_imbalance     Float32,            -- signed_volume / unsigned_volume [-1, +1]
    effective_spread_bps Float32,          -- Median 2×|trade_price - midpoint| in bps
    price_impact_per_volume Float32,       -- Δmidpoint / signed_volume
    -- Metadata
    bucket_date        Date,               -- Partition key
    fill_duration_ms   UInt32              -- Wall-clock milliseconds to fill bucket
) ENGINE = MergeTree()
PARTITION BY bucket_date
ORDER BY (symbol, bucket_date, bucket_id)
SETTINGS index_granularity = 4096;

-- Diagnostic results (Phase 2 outputs)
CREATE TABLE IF NOT EXISTS polygon_data.diagnostic_results (
    run_id         String,                 -- UUID for each diagnostic run
    symbol         LowCardinality(String),
    metric_name    LowCardinality(String), -- e.g., 'persistence_half_life', 'continuation_prob_k3'
    metric_value   Float64,
    metric_metadata String,                -- JSON blob for additional context
    computed_at    DateTime,
    run_date       Date
) ENGINE = MergeTree()
PARTITION BY run_date
ORDER BY (run_id, symbol, metric_name)
SETTINGS index_granularity = 8192;
```

**Key design decisions**:
- `sip_timestamp` as Int64 nanoseconds: matches existing `polygon_data.ticks` convention. No precision loss.
- Partitioned by date: enables efficient range queries and easy data management (drop old partitions).
- `volume_buckets` is a COMPUTED table, not raw data. It's the output of the bucketing engine, stored for reproducibility.
- `diagnostic_results` stores ALL Phase 2 gate outputs for auditability.
- `LowCardinality(String)` for symbol: ClickHouse dictionary encoding. Critical at billion-row scale.
- No UPDATEs allowed. All tables are INSERT-only (append). Immutability protects audit integrity.

**Storage & query performance risk** (final review — operational risk #1):

At 10 symbols × 130 trading days (falsification dataset):
- Tier A (3): ~140 MB/day × 130 days × 3 = ~55 GB
- Tier B (3): ~80 MB/day × 130 days × 3 = ~31 GB
- Tier C (4): ~40 MB/day × 130 days × 4 = ~21 GB
- Raw total: ~107 GB + overhead (buckets, diagnostics, indices) ≈ 140-150 GB

Storage budget: 220GB target, 250GB kill-switch, 300GB hard cap.
Well within budget. See Section 0.5 for detailed math.

If schema is not properly tuned, Week 3 diagnostic queries will time out.

Required ClickHouse hardening (verified in Week 0 probe):
- Compression codecs: `CODEC(Delta, ZSTD(3))` on timestamp columns for ~10× compression
- `CODEC(DoubleDelta, ZSTD(1))` on price columns
- `CODEC(T64, ZSTD(1))` on size/volume columns
- Verify MergeTree background merges keep part count manageable
- Monitor `system.parts` table during probe ingestion
- If single-symbol full-range query exceeds 2 seconds → investigate index granularity

These codec recommendations should be validated during the probe and added to the
final DDL before bulk ingestion begins.

---

### 1.3 Bulk Historical Ingestion

**Implementation**: `core_engine/microstructure/ingestion/bulk_downloader.py`

```
class BulkTickQuoteDownloader:
    """
    Downloads 130 trading days of historical tick + quote data from Polygon v3 endpoints.
    Loads directly into ClickHouse. Handles pagination, rate limiting, resume-on-failure.
    """
    Dependencies:
      - PolygonRestService (existing — reuse get_historical_trades/quotes)
      - ClickHouse connection (existing — reuse _execute_query pattern)

    Config:
      - symbols: List[str] (from frozen universe)
      - start_date: date
      - end_date: date
      - polygon_rate_limit: int (500 calls/sec for Stock Advanced)
      - max_concurrent_symbols: int (5 — conservative to avoid rate limit)
      - batch_insert_size: int (100_000 rows per ClickHouse insert)
      - resume_from: Optional[Tuple[str, date]] (symbol, date for resume on failure)

    Methods:
      async download_all(universe: UniverseClassification) -> IngestionReport
      async _download_symbol_day(symbol: str, day: date) -> Tuple[int, int]  # trade_count, quote_count
      async _insert_trades_batch(symbol: str, trades: List[Dict]) -> int
      async _insert_quotes_batch(symbol: str, quotes: List[Dict]) -> int
      _validate_day_completeness(symbol: str, day: date) -> DayValidation

    Concurrency model:
      - Semaphore-controlled (max 5 concurrent symbol-day downloads)
      - Per-symbol sequential day processing (ensures timestamp ordering)
      - Cross-symbol parallel (different symbols download simultaneously)
      - Resume-safe: tracks (symbol, date) completion in a manifest table

    Output:
      IngestionReport:
        - total_trades: int
        - total_quotes: int
        - symbols_completed: List[str]
        - symbols_failed: List[Tuple[str, str]]  # (symbol, error)
        - days_per_symbol: Dict[str, int]
        - data_size_gb: float
        - elapsed_hours: float
```

**Polygon API considerations**:
- Stock Advanced plan: 500 requests/second, unlimited historical data.
- v3 trades endpoint: paginated, max 50,000 per page. A liquid symbol like AAPL has ~500K-1M trades/day → 10-20 pages/day.
- v3 quotes endpoint: similar pagination. NBBO updates can be 5-10M/day for active names → 100-200 pages/day.
- **Estimated download time**: 10 symbols × 130 trading days × ~30 seconds/symbol-day ≈ 10.8 hours. Parallelized at 5 concurrent: ~2-2.5 hours.
- **Estimated storage**: ~140-150 GB compressed for 10 symbols × 130 days. Target: 220GB. Kill-switch: 250GB.

**Rate limit management**:
- Reuse existing `PolygonRestConfig.rate_limit_calls` (500) and `rate_limit_period` (1.0s).
- Add exponential backoff on 429 responses (existing retry logic in `_make_request`).

---

### 1.4 Data Quality Validation (Ingestion-Time)

**Implementation**: `core_engine/microstructure/ingestion/tick_validator.py`

```
class TickDataValidator:
    """
    Validates raw tick/quote data at ingestion time.
    Catches problems BEFORE they contaminate downstream computation.
    """

    Validation rules (per symbol-day):
      1. Timestamp ordering: sip_timestamp[i+1] >= sip_timestamp[i] (monotonicity)
         - Count violations. If > 0.1% of trades → flag day as potentially misordered.
      2. Duplicate detection: same (sip_timestamp, price, size, exchange) → deduplicate.
      3. Price sanity: price > 0, price < 10 × previous_close, no NaN.
      4. Size sanity: size > 0, size < 1_000_000 (flag mega-blocks separately).
      5. Spread sanity (quotes): ask > bid, (ask - bid) < 5% of midpoint.
      6. Quote completeness: bid_size > 0, ask_size > 0.
      7. RTH filtering: only 9:30:00-16:00:00 ET (pre/post-market excluded from study).
      8. Condition code filtering: exclude trades with condition codes indicating
         non-standard execution (odd lots if size < 100, out-of-sequence, etc.).
         Polygon condition codes reference: https://polygon.io/glossary/us/stocks/conditions-indicators
      9. Completeness: if trade_count < expected_min_trades_per_day → flag as thin day.
     10. Gap detection: if no trades for > 5 minutes during RTH → flag gap.

    Output:
      DayValidation dataclass:
        - symbol: str
        - date: date
        - trade_count_raw: int
        - trade_count_valid: int
        - quote_count_raw: int
        - quote_count_valid: int
        - monotonicity_violations: int
        - duplicates_removed: int
        - condition_filtered: int
        - gaps: List[Tuple[datetime, datetime]]  # (gap_start, gap_end)
        - quality_score: float  # 0-1
        - is_valid: bool  # quality_score > 0.9
```

**Hard rule (from FAHS v1.5 Section 8.1)**:
If >5% of daily buckets are invalid → that day excluded from study.

---

### 1.5 Lee-Ready Trade Classifier

**Implementation**: `core_engine/microstructure/classification/lee_ready.py`

```
class LeeReadyClassifier:
    """
    Classifies each trade as buyer-initiated (+1), seller-initiated (-1),
    or indeterminate (0) using the Lee-Ready algorithm.

    Three-step rule (from FAHS v1.5 Section 2.2):
      1. Compare trade price to NBBO midpoint at time of trade.
         - trade_price > midpoint → buy (+1)
         - trade_price < midpoint → sell (-1)
         - trade_price == midpoint → go to step 2
      2. Tick rule: compare to previous trade price.
         - trade_price > prev_price → buy (+1)
         - trade_price < prev_price → sell (-1)
         - trade_price == prev_price → go to step 3
      3. Classify as indeterminate (0). Exclude from signed_volume.
    """

    Dependencies:
      - Trades DataFrame (from ClickHouse polygon_data.trades)
      - Quotes DataFrame (from ClickHouse polygon_data.quotes)

    Methods:
      classify_day(symbol: str, date: date) -> ClassifiedTrades
      _match_quotes_to_trades(trades_df, quotes_df) -> pd.DataFrame
      _apply_lee_ready(matched_df) -> pd.Series  # trade_sign column
      _compute_quality_metrics(classified_df) -> ClassificationQuality

    Quote-Trade Matching:
      - For each trade, find the most recent NBBO quote with sip_timestamp <= trade.sip_timestamp.
      - Use searchsorted on the sorted quote timestamp array (O(log n) per trade).
      - If no quote within 50ms → flag as stale-quote trade.
      - Record quote_age_ns for each matched pair.

    Output:
      ClassifiedTrades dataclass:
        - trades: pd.DataFrame  # Original trades + trade_sign, midpoint, quote_age_ns columns
        - quality: ClassificationQuality
          - total_trades: int
          - buy_count: int
          - sell_count: int
          - indeterminate_count: int
          - midpoint_fraction: float  # % trades at midpoint
          - tick_rule_fallback_pct: float  # % classified by tick rule (not Lee-Ready midpoint)
          - stale_quote_pct: float  # % with quote_age > 50ms
          - mean_quote_age_ms: float

    Performance target:
      - Must classify 1M trades in < 30 seconds (vectorized numpy, no row-level loops).
      - Quote matching via np.searchsorted on pre-sorted arrays.

    Memory management — chunked processing (Round 1 review):
      Tier A names (AAPL, TSLA, NVDA) can produce 5-10M NBBO quotes/day.
      Loading a full day into a Pandas DataFrame: ~8-12 GB transient RAM.
      This exceeds typical workstation memory if processing multiple symbols.

      Strategy: hour-level chunking with quote carry-forward.
        1. Load quotes in 1-hour chunks from ClickHouse (6.5 chunks per RTH day).
        2. Load ALL trades for the same hour (trades are smaller — ~500K/day).
        3. Classify trades in that hour against the hourly quote chunk.
        4. Carry forward the last quote from each hour to the next chunk
           (ensures the first trade of the next hour has a valid NBBO match).
        5. Concatenate classified trades across hours. Verify no gaps.

      Peak memory per chunk: ~1-2 GB (manageable on 16 GB workstation).
      Slight I/O overhead vs full-day load, but prevents OOM.

      Alternative: if ClickHouse server has sufficient RAM, do classification
      in a ClickHouse UDF or use Arrow-native processing via PyArrow
      (zero-copy, memory-mapped). Evaluate during implementation based on
      actual data sizes for the chosen universe.
```

**Implementation notes**:
- The quote-trade join is the performance-critical operation. With 500K trades and 5M quotes per day, naive merge is O(n²). Use `np.searchsorted` on sorted quote timestamps for O(n log m).
- Midpoint = (bid_price + ask_price) / 2.0. Handle zero-bid or zero-ask quotes (shouldn't occur for NBBO, but defensive).
- Polygon condition codes: filter out `condition_codes` that indicate non-regular trades before classification.

**Regime-conditioned classification accuracy (Round 1 review)**:

SIP can backlog trades and quotes differently during volatility bursts. If quote lag correlates with volatility regime, Lee-Ready accuracy becomes regime-dependent — and that contaminates persistence statistics silently.

Required additions to `ClassifiedTrades.quality`:
- `quote_age_ns_distribution`: full distribution per bucket (stored in volume_buckets table), not just mean.
- `regime_conditioned_accuracy`: for each volatility quintile (daily realized vol), report:
  - median quote_age_ms
  - tick_rule_fallback_pct
  - midpoint_fraction
  - signed_volume → forward_return correlation

Explicit test added to Phase 2c:
```
P(correct_sign | quote_age > 50ms) vs P(correct_sign | quote_age ≤ 50ms)
```
If classification accuracy degrades by >5 percentage points in high-quote-lag states, continuation statistics measured in those states must be flagged as potentially biased. Phase 2b persistence analysis must then be reported BOTH pooled and excluding high-lag buckets.

This prevents a scenario where persistence appears to exist only because classification noise in high-vol regimes creates phantom autocorrelation.

---

### 1.6 Volume-Clock Bucketing Engine

**Implementation**: `core_engine/microstructure/bucketing/volume_clock.py`

```
class VolumeClockBucketer:
    """
    Aggregates classified trades into fixed-volume buckets.

    Bucket size (from FAHS v1.5 Section 2.4):
      bucket_volume = ADV / target_buckets_per_day
      target_buckets_per_day ≈ 200

    Each bucket fills with exactly bucket_volume shares (last trade may spill).
    """

    Config:
      target_buckets_per_day: int = 200
      adv_lookback_days: int = 20  # For computing ADV

    Methods:
      bucket_day(symbol: str, date: date, classified_trades: ClassifiedTrades,
                 adv: float) -> List[VolumeBucket]
      _compute_bucket_metrics(bucket_trades: pd.DataFrame, quotes_context: pd.DataFrame) -> VolumeBucket
      _compute_effective_spread(bucket_trades: pd.DataFrame) -> float
      _compute_price_impact(bucket_trades: pd.DataFrame) -> float

    Bucket computation:
      1. Compute bucket_volume = ADV / 200.
      2. Iterate through classified trades sequentially.
      3. Accumulate volume until bucket_volume reached.
      4. For each completed bucket, compute:
         - OHLCV (from trade prices)
         - signed_volume = sum(trade_sign × trade_size)
         - flow_imbalance = signed_volume / total_volume
         - effective_spread_bps = median(2 × |trade_price - midpoint| / midpoint × 10000)
         - price_impact_per_volume = (midpoint_end - midpoint_start) / signed_volume
         - classification_confidence = (buy_volume + sell_volume) / total_volume
         - tick_rule_fallback_pct (from classifier output)
         - fill_duration_ms (wall-clock time from first to last trade in bucket)
         - bid/ask at bucket boundaries

    Output:
      List[VolumeBucket] → inserted into polygon_data.volume_buckets table

    Performance target:
      - Must bucket 1M trades in < 10 seconds.
      - Vectorized accumulation using numpy cumsum + searchsorted for bucket boundaries.
```

**Bucket boundary algorithm (vectorized, integer-safe — Round 1 review)**:

The expert correctly identifies a hidden floating-point risk: `np.cumsum` on float volumes can produce order-dependent accumulation. If symbol-days are ever parallelized or chunked, bucket boundaries may drift across hardware architectures.

Solution: ALL volume accumulation uses integer arithmetic (UInt64). Trade sizes from Polygon are already integers (share counts). Bucket volume is an integer (ADV / 200, rounded to nearest integer). No float conversion until after bucket indices are fixed.

```python
# Integer-safe bucket boundary computation
trade_sizes_int = trade_sizes.astype(np.uint64)  # Already integers from Polygon
cumulative_volume = np.cumsum(trade_sizes_int)     # Integer cumsum — deterministic
bucket_volume_int = np.uint64(round(adv / target_buckets_per_day))
bucket_boundaries = np.arange(bucket_volume_int, cumulative_volume[-1] + bucket_volume_int,
                               bucket_volume_int, dtype=np.uint64)
bucket_indices = np.searchsorted(cumulative_volume, bucket_boundaries)
# Float conversion happens ONLY after bucket_indices are fixed
```
This avoids row-level iteration entirely and guarantees deterministic replay across any hardware.

---

### 1.7 Ingestion Pipeline Orchestration

**Implementation**: `core_engine/microstructure/ingestion/pipeline.py`

```
class MicrostructureIngestionPipeline:
    """
    Orchestrates the full Phase 1 pipeline:
      Universe scan → Download → Validate → Classify → Bucket → Store

    Deterministic replay guarantee: given the same raw data and config,
    produces identical volume buckets. No randomness, no floating-point
    order-dependence.
    """

    Pipeline stages:
      Stage 0: Universe construction (UniverseScanner)
        Input: Candidate symbols, 20-day observation window
        Output: Frozen tier classification
        Gate: ≥5 sectors, ≥5 symbols per tier, Tier C feasibility checked

      Stage 1: Bulk download (BulkTickQuoteDownloader)
        Input: Frozen universe, date range (130 trading days)
        Output: Raw trades + quotes in ClickHouse
        Gate: All symbol-days downloaded, completeness > 95%

      Stage 2: Validation (TickDataValidator)
        Input: Raw trades + quotes per symbol-day
        Output: Validation report, invalid days flagged
        Gate: < 5% of days flagged invalid per symbol

      Stage 3: Classification (LeeReadyClassifier)
        Input: Valid trades + quotes per symbol-day
        Output: Classified trades (trade_sign column)
        Gate: tick_rule_fallback_pct < 20% per symbol (FAHS 13.4)

      Stage 4: Bucketing (VolumeClockBucketer)
        Input: Classified trades + ADV per symbol
        Output: Volume buckets in ClickHouse
        Gate: Bucket count within 20% of target (200/day)

      Stage 5: Integrity verification
        Input: Stored volume buckets
        Output: Deterministic replay test result
        Test: Re-bucket a random 5 symbol-days. Compare to stored buckets.
              If ANY difference → pipeline has non-determinism. Fix before proceeding.

      Stage 6: Hash logging (Round 3 — audit trail)
        For each symbol-day, after all stages complete, compute and store:
          - trades_hash:  SHA256 of raw trades (sorted by timestamp, all fields)
          - quotes_hash:  SHA256 of raw quotes (sorted by timestamp, all fields)
          - buckets_hash: SHA256 of volume bucket output (all fields, row-ordered)
        Store in `polygon_data.diagnostic_results` table:
          symbol, date, pipeline_stage='hash_audit', metric_name IN
          ('trades_sha256', 'quotes_sha256', 'buckets_sha256'), metric_value=hex_string

        Purpose: If any future re-run diverges, hash comparison instantly localizes
        whether the cause is:
          (a) API data changed (trades_hash differs) — Polygon backfill correction
          (b) Classification logic changed (quotes_hash same, buckets_hash differs)
          (c) Bucketing logic changed (trades_hash + quotes_hash same, buckets_hash differs)
        Without hashing, you detect divergence. With hashing, you LOCALIZE it.

        Implementation: hashlib.sha256 over pd.DataFrame.to_csv(index=False).encode()
        after sorting by timestamp. Deterministic because data is sorted and all fields
        are included.

    Config: core_engine/config/catalog/microstructure/ingestion.yaml
```

**Config**: `core_engine/config/catalog/microstructure/ingestion.yaml`

```yaml
ingestion:
  # Date range — 130 trading days (~6 calendar months)
  # Compute: most recent 130 completed trading days from execution date
  start_date: "2025-07-01"    # ~130 trading days (adjust to actual calendar)
  end_date: "2026-01-31"
  trading_days_target: 130    # Hard target — do not extend
  
  # Polygon API
  polygon:
    rate_limit_calls: 500
    rate_limit_period: 1.0
    max_concurrent_symbols: 5
    max_pages_per_request: 100  # Higher for quotes (more data)
    batch_insert_size: 100000
  
  # Volume bucketing
  bucketing:
    target_buckets_per_day: 200
    adv_lookback_days: 20
  
  # Validation
  validation:
    min_quality_score: 0.9
    max_invalid_day_pct: 0.05      # 5% of days
    max_tick_rule_fallback_pct: 0.20
    max_stale_quote_pct: 0.10
    monotonicity_violation_threshold: 0.001
    min_trades_per_day: 5000        # Below this → day excluded (FAHS 9.1.5)
  
  # Deterministic replay
  replay_test:
    num_random_symbol_days: 5
    tolerance: 0.0                  # Exact match required
```

---

## 2. PHASE 2 — FOUNDATION DIAGNOSTICS

Phase 2 is a PROGRAM GATE. It answers: "Is the information layer viable?" If the answer is no, the entire program terminates. There is no Phase 3.

### 2.0 Hierarchical Gate Ordering (Round 3 final review)

The diagnostic framework produces many conditional views (5 thresholds × 3 vol regimes × 3 confidence regimes × 3 temporal blocks × 25 heatmap cells × ...). Even with frozen constants, combinatorial search risk exists. To prevent interpretation drift — where Tier 2 nuance is debated on a Tier 1 failure — gates are explicitly ranked and executed in strict order.

**TIER 1 — EXISTENCE (does the edge exist at all?)**

These are evaluated FIRST. If ANY Tier 1 gate fails, STOP. Do not run Tier 2 or Tier 3. Do not discuss elasticity conditioning or concurrency. The signal does not exist.

| Gate | Criterion | Source |
|------|-----------|--------|
| T1.1 | Continuation prob > 50% (CI lower, ALL buckets) | Phase 2b, confidence regime (1) |
| T1.2 | Net edge > 0 bp after FULL penalized cost (tier multiplier × elasticity multiplier) | Phase 2 economics |
| T1.3 | Temporal stability: edge positive in ≥ 2 of 3 blocks | Phase 2b temporal |
| T1.4 | Classification correlation > 0.05 with forward returns | Phase 2c |

**TIER 2 — STRUCTURE (is the edge caused or accidental?)**

Evaluated ONLY if all Tier 1 gates pass. These determine whether the edge has causal structure or is noise clustering.

| Gate | Criterion | Source |
|------|-----------|--------|
| T2.1 | Magnitude monotonicity (both parts: rho + economic spread) | Phase 2b monotonicity |
| T2.2 | Regime conditioning: edge survives in ≥ 2 of 3 vol regimes | Phase 2b regime |
| T2.3 | Threshold sweep: continuation stable at ≥ 3 of 5 thresholds | Phase 2b threshold |
| T2.4 | Elasticity × volume heatmap shows separability | Phase 2e |
| T2.5 | Noise injection: t-stat > 2.0 at 15% misclassification | Phase 2c |

**TIER 3 — PORTFOLIO REALITY (does it survive implementation?)**

Evaluated ONLY if all Tier 1 and Tier 2 gates pass. These determine whether the edge is tradeable under real constraints.

| Gate | Criterion | Source |
|------|-----------|--------|
| T3.1 | Conditional slippage: edge positive in high-imbalance/high-elasticity cell | Phase 2 economics |
| T3.2 | Capacity utilization: ≥ 40% of signals tradeable after portfolio constraints | Phase 2 economics |
| T3.3 | Cross-event correlation: median pairwise < 0.4 | Phase 2 economics |
| T3.4 | Event beta: median event beta to SPY < 0.6 | Phase 2 economics |
| T3.5 | Self-impact: ≤ 20% events with > 10% divergence | Phase 2 self-impact |
| T3.6 | Edge distribution: median net edge > 0 (not outlier-dependent) | Phase 2 economics |

**Execution rule**: If a Tier 1 gate fails mid-sequence, remaining Tier 1 gates still run (to provide complete failure diagnostics). But Tier 2 and 3 are skipped entirely. Time is capital.

---

### 2.1 Diagnostic Framework Architecture

**Implementation**: `core_engine/microstructure/diagnostics/foundation.py`

```
class FoundationDiagnosticEngine:
    """
    Runs all Phase 2 diagnostic gates defined in FAHS v1.5 Section 8.1.
    Produces decision tables, not dashboards. Every output maps directly
    to a frozen rejection criterion.
    """

    Dependencies:
      - ClickHouse (volume_buckets table, raw trades/quotes)
      - UniverseClassification (frozen tier assignments)
      - FAHS rejection criteria (hardcoded as constants — not configurable)

    Methods:
      async run_all_diagnostics(universe: UniverseClassification) -> FoundationReport
      async run_2a_primitive_computation(symbol: str) -> PrimitiveReport
      async run_2b_persistence_decay(symbol: str) -> PersistenceReport
      async run_2c_lee_ready_quality(symbol: str) -> ClassificationReport
      async run_2d_volume_bucket_diagnostics(symbol: str) -> BucketReport

    Output:
      FoundationReport:
        - per_symbol_reports: Dict[str, SymbolDiagnosticReport]
        - program_gates: ProgramGateResults
          - persistence_gate: GateResult  # PASS/FAIL + evidence
          - classification_gate: GateResult
          - noise_injection_gate: GateResult
        - decision: ProgramDecision  # PROCEED / TERMINATE / MICRO_BURST_CONTINGENCY
        - decision_evidence: str  # Human-readable justification
```

### 2.2 Phase 2a: Primitive Computation

**Implementation**: `core_engine/microstructure/metrics/flow_metrics.py`

```
class FlowMetricsComputer:
    """
    Computes all observable primitives and derived metrics from volume buckets.
    Maps directly to FAHS v1.5 Section 2.
    """

    Computed per volume bucket:
      Already stored in volume_buckets table:
        - signed_volume, flow_imbalance, effective_spread_bps, price_impact_per_volume

      Computed as rolling/cumulative over bucket sequences:
        - cumulative_imbalance: running sum of signed_volume over K trailing buckets
        - vpin: |buy_volume - sell_volume| / total_volume over rolling N-bucket window
        - trade_arrival_rate: num_trades / fill_duration_ms
        - spread_expansion_rate: Δmedian_spread_bps / Δbucket_id (rate of spread change)

    Statistical characterization (per symbol, full history):
      - Distribution of each metric (mean, std, skew, kurtosis, percentiles)
      - Autocorrelation at lags 1, 2, 5, 10, 20, 50 buckets
      - Stationarity test (ADF) on flow_imbalance series
      - Cross-correlation between metrics (e.g., flow_imbalance vs effective_spread)

    Output:
      PrimitiveReport:
        - distributions: Dict[str, DistributionStats]
        - autocorrelations: Dict[str, Dict[int, float]]  # metric → lag → acf value
        - stationarity: Dict[str, ADFResult]
        - cross_correlations: pd.DataFrame  # Correlation matrix of derived metrics
```

### 2.3 Phase 2b: Persistence Decay Curve (PROGRAM GATE)

**Implementation**: `core_engine/microstructure/diagnostics/persistence.py`

```
class PersistenceAnalyzer:
    """
    Measures the half-life of flow imbalance persistence.
    This is the FIRST program gate. If persistence is too short,
    the entire flow alpha thesis collapses.

    Directly implements FAHS v1.5 Section 8.1 Phase 2b.
    """

    Methods:
      analyze_persistence(symbol: str, buckets: pd.DataFrame) -> PersistenceResult
      _compute_autocorrelation_curve(imbalance_series: np.ndarray, max_lag: int) -> np.ndarray
      _estimate_half_life(acf_curve: np.ndarray) -> float
      _compute_cost_covering_period(symbol: str, buckets: pd.DataFrame) -> float
      _compute_continuation_probabilities(imbalance_series: np.ndarray, k_values: List[int]) -> Dict[int, ContinuationResult]
      _categorize_events(imbalance_series: np.ndarray) -> EventCategorization
      _compute_survival_curve(events: List[ImbalanceEvent]) -> np.ndarray

    Continuation probability computation:
      For each k in [1, 2, 3, 5, 10]:
        1. Identify all "imbalance events" = sequences of k consecutive buckets
           with same-sign flow_imbalance (above a minimum threshold, e.g., |flow_imbalance| > 0.1).
        2. Check if bucket k+1 continues in the same direction.
        3. continuation_prob = count(continued) / count(events)
        4. Compute 95% CI using Wilson score interval (not normal approximation — better for proportions).
        5. Report: point estimate, CI lower, CI upper, CI width, event count.

    Event categorization:
      For each detected imbalance event (consecutive same-sign buckets):
        - Duration in buckets
        - Classify: micro-burst (<3), intermediate (3-10), mandate (>10)
        - Report distribution: % micro-burst, % intermediate, % mandate

    Three-confidence-regime persistence reporting (Round 2 review):
      Excluding low-confidence buckets (high quote lag, ambiguous classification) from
      persistence analysis is correct for signal quality. But if high-lag correlates with
      volatility regime, excluding them unintentionally selects "clean regimes" only —
      creating survivorship bias at the bucket level.

      Therefore, report persistence under THREE regimes:
        1. ALL BUCKETS: No filtering. Raw persistence including noisy buckets.
           This is the conservative, real-world estimate.
        2. HIGH-CONFIDENCE ONLY: Exclude buckets where classification_confidence < 0.60
           or quote_age > 50ms. This is the "clean signal" estimate.
        3. REGIME-FREQUENCY WEIGHTED: High-confidence persistence, but weighted by the
           fraction of total trading time each confidence regime occupies.
           If high-confidence buckets are only 60% of total → the weighted estimate
           reflects that 40% of trading time produces unreliable signals.

      The PRIMARY gate decision uses regime (1) — ALL BUCKETS.
      Regime (2) is diagnostic: if it materially exceeds (1), we know classification
      noise degrades persistence. That's useful information but NOT a reason to
      use the inflated number for gating.
      Regime (3) estimates realistic live performance: strong signal when available,
      degraded signal (or no signal) during noisy windows.

      If regime (1) fails but regime (2) passes → edge exists but is classification-
      dependent. Flag for potential improvement via better data (direct feeds), but
      do NOT promote on regime (2) alone.

    Rejection criteria (from FAHS v1.5 Section 8.3):
      R1: continuation_prob_k3.ci_lower < 0.50 OR continuation_prob_k3.point < 0.55
          OR continuation_prob_k3.ci_width > 0.06
          NOTE: Applied to regime (1) — ALL BUCKETS. Not the clean subset.
      R3: micro_burst_pct > 0.60

    Cost-covering period:
      - Regress: forward_return(k buckets) = α + β × signed_volume + ε
      - Find minimum k where E[forward_return] > effective_spread + commission
      - If half_life < cost_covering_period on > 80% symbols → ABORT PROGRAM

    Dual half-life measurement (Round 1 review):
      ADV shifts across the 130-day ingestion window (vol regime changes). If ADV spikes,
      bucket_volume stays on lagging ADV → buckets fill faster → shorter wall-clock duration.
      Persistence measured in bucket-units shifts mechanically.

      Therefore compute BOTH:
        - half_life_buckets: ACF-based, in volume-clock bucket units
        - half_life_minutes: ACF of imbalance resampled to 1-minute wall-clock intervals
        - half_life_normalized: half_life_buckets × median_fill_duration_minutes
          (regime-normalized — converts bucket persistence to time persistence)

      Compare: if half_life_buckets is short but half_life_minutes is acceptable, the
      bucket sizing is too small in high-ADV periods, not the persistence itself.
      Conversely, if both are short → genuine lack of persistence.

    Regime-conditioned persistence (Round 1 review — Vulnerability 1):
      ALL primary gates must be checked regime-conditioned, not just economics.
      Compute persistence separately for:
        - Low-vol days (bottom tertile of daily realized vol)
        - Mid-vol days (middle tertile)
        - High-vol days (top tertile)
      Report: half_life, continuation_prob_k3, event_categorization per regime.
      Flag: if persistence exists in low-vol but collapses in high-vol, the strategy
      is structurally unstable — it works only when it's least needed.

    Imbalance-magnitude monotonicity test (Round 1 + Round 2 review):
      Persistence is meaningful only if stronger imbalances produce stronger continuation.
      If small and large imbalances have identical continuation probability, we are
      measuring noise clustering, not mandate behavior.
      Compute:
        P(continuation | |flow_imbalance| decile) for deciles 1-10

      TWO-PART monotonicity gate (strengthened Round 2):
        Part A — Statistical: Spearman rho between decile and continuation probability.
          If rho < 0.3 → weak monotonicity signal.
        Part B — Economic: Decile 10 (strongest imbalance) continuation probability must
          exceed Decile 1 (weakest) by ≥ 8 percentage points. AND monotonicity must hold
          in at least 7 of 9 adjacent decile comparisons (i.e., decile k+1 continuation
          ≥ decile k continuation for 7 of 9 pairs).

      BOTH parts must pass. Rationale: Spearman rho alone can pass noisy but
      economically irrelevant slopes. A rho of 0.35 with only a 3pp spread between
      D1 and D10 is statistically "monotonic" but economically meaningless — the
      magnitude of the imbalance doesn't matter enough to differentiate entry quality.

      Baseline-adaptive spread requirement (Round 3 refinement):
      If baseline continuation is low (e.g., 52% in high-vol regime), the theoretical
      maximum D10-D1 spread narrows. A fixed 8pp requirement would reject economically
      meaningful monotonicity in structurally tighter regimes.

      Adaptive rule:
        required_spread = max(MAGNITUDE_D10_D1_MIN_SPREAD_PP, MAGNITUDE_D10_D1_SCALE × baseline_continuation)

      Examples:
        - Baseline 60% → required spread = max(8, 9.0) = 9.0pp
        - Baseline 54% → required spread = max(8, 8.1) = 8.1pp
        - Baseline 52% → required spread = max(8, 7.8) = 8.0pp (floor applies)

      The 8pp floor prevents acceptance of trivially flat curves. The 15% scaling
      prevents rejection of genuinely monotonic but compressed distributions.
      Both constants frozen in `constants.py`.

    Temporal stability requirement (Round 2 review, finalized):
      All diagnostics use a 130-trading-day window. But microstructure regimes change.
      If flow persistence exists in only 1 of 3 blocks, pooled statistics pass
      while the alpha is regime-fragile.

      Compute rolling ~43-day sub-analysis:
        - Split the 130-day window into 3 non-overlapping ~43-trading-day blocks.
        - For each block: compute continuation_prob_k3, net_edge, half_life.
        - STABILITY CRITERION: edge must be positive (net_edge > 0) in ≥ 2 of 3 blocks.
          AND continuation_prob_k3 > 50% in ≥ 2 of 3 blocks.
        - If edge concentrates in 1 block only → regime-fragile alpha. Flag.

      Additionally, compute 1-month rolling persistence (sliding window, 1-month stride):
        - 6 overlapping windows. Report trend: is persistence decaying, stable, or growing?
        - If the most recent 2 months show persistence BELOW the first 2 months by > 20%
          → potential edge decay already in historical data. Flag for manual review.

      This prevents a scenario where a single 43-day block of strong flow (e.g., a
      macro volatility event or earnings season) dominates the 130-day average and
      creates the illusion of stable alpha.

    Imbalance threshold sensitivity sweep (Round 1 review — Vulnerability 2):
      The event detection threshold |flow_imbalance| > X shapes everything.
      Sweep X = [0.05, 0.10, 0.15, 0.20, 0.25]:
        - For each threshold: report event count, continuation_prob_k3, net edge, CI
        - If results flip sign across adjacent thresholds → edge is parameter-sensitive noise
        - STABILITY CRITERION: continuation_prob_k3 > 55% for at least 3 of 5 thresholds.
          If not → H1 is fragile to threshold choice.
      This sweep is frozen in constants.py. Not configurable. Not optional.

    Output:
      PersistenceResult:
        - half_life_buckets: float
        - half_life_minutes: float  # Independent wall-clock measurement
        - half_life_normalized: float  # bucket half-life × median fill duration
        - acf_curve: np.ndarray
        - continuation_probs: Dict[int, ContinuationResult]  # k → (point, ci_lower, ci_upper, ci_width, n_events)
        - event_categorization: EventCategorization  # micro_burst_pct, intermediate_pct, mandate_pct
        - cost_covering_period_buckets: float
        - survival_curve: np.ndarray
        - regime_persistence: Dict[str, PersistenceResult]  # 'low_vol' / 'mid_vol' / 'high_vol'
        - confidence_regime_persistence: Dict[str, PersistenceResult]  # 'all' / 'high_conf' / 'weighted'
        - magnitude_monotonicity: MonotonicityResult  # decile probs + Spearman rho + D10-D1 spread + adjacent pairs
        - threshold_sensitivity: Dict[float, ThresholdResult]  # threshold → (event_count, continuation, net_edge)
        - temporal_stability: TemporalStabilityResult  # per-block persistence + decay trend
        - gate_result: GateResult  # PASS/FAIL + which criterion triggered
```

### 2.4 Phase 2c: Lee-Ready Quality Assessment (PROGRAM GATE)

**Implementation**: `core_engine/microstructure/diagnostics/classification_quality.py`

```
class ClassificationQualityAssessor:
    """
    Assesses whether Lee-Ready classification is good enough
    to support the flow hypothesis.

    Directly implements FAHS v1.5 Section 8.1 Phase 2c.
    """

    Methods:
      assess_quality(symbol: str) -> ClassificationAssessment
      _three_way_comparison(symbol: str) -> ComparisonResult
      _noise_injection_test(symbol: str, noise_levels: List[float]) -> NoiseTestResult
      _forward_return_correlation(classified_buckets: pd.DataFrame) -> float

    Three-way comparison:
      For each symbol-day, classify using:
        a. Tick rule only (compare each trade to previous trade price)
        b. Lee-Ready with midpoint exclusion (indeterminate = 0)
        c. Lee-Ready with probabilistic midpoint (random ±1 for midpoint trades)
      Compare signed_volume from each method with 1-minute forward returns.
      Best method = highest correlation.

    Noise injection test (FAHS v1.5 Section 8.1 Phase 2c):
      For noise_level in [0.10, 0.15, 0.20]:
        1. Randomly flip trade_sign for noise_level fraction of trades.
        2. Recompute flow_imbalance and cumulative_imbalance.
        3. Recompute H1 signal detection events.
        4. Compute t-statistic of forward returns for detected events.
        5. If t-stat < 2.0 at noise_level = 0.15 → EDGE IS CLASSIFICATION-FRAGILE.

    Rejection criterion (FAHS v1.5 Section 8.2):
      - Best classifier correlation with forward returns < 0.05 → ABORT PROGRAM
      - H1 t-stat < 2.0 at 15% noise → ABORT PROGRAM (classification-fragile edge)

    Regime-conditioned classification (Round 1 review — Vulnerability 1):
      Classification quality must also be checked per volatility regime:
        - For each vol tertile: correlation, noise_test, midpoint_fraction
        - If correlation drops below 0.03 in high-vol regime specifically →
          persistence statistics from high-vol days are unreliable.
          Flag for separate treatment in Phase 2b.

    Output:
      ClassificationAssessment:
        - best_method: str  # 'tick_rule', 'lee_ready_exclude', 'lee_ready_probabilistic'
        - correlations: Dict[str, float]  # method → correlation with forward returns
        - correlations_by_regime: Dict[str, Dict[str, float]]  # regime → method → correlation
        - noise_test: NoiseTestResult  # t-stats at each noise level
        - midpoint_fraction_by_quintile: Dict[str, float]  # volatility quintile → midpoint %
        - quote_lag_accuracy: Dict[str, float]  # 'high_lag' vs 'low_lag' → accuracy
        - gate_result: GateResult
```

### 2.5 Phase 2d: Volume Bucket Diagnostics

**Implementation**: `core_engine/microstructure/diagnostics/bucket_quality.py`

```
class BucketQualityAnalyzer:
    """
    Validates that volume-clock bucketing produces approximately stationary metrics.

    Directly implements FAHS v1.5 Section 8.1 Phase 2d.
    """

    Methods:
      analyze_buckets(symbol: str) -> BucketQualityResult
      _fill_duration_analysis(buckets: pd.DataFrame) -> FillDurationStats
      _stationarity_tests(buckets: pd.DataFrame) -> StationarityResult
      _time_of_day_analysis(buckets: pd.DataFrame) -> TimeOfDayResult

    Fill duration analysis:
      - Distribution of fill_duration_ms (wall-clock)
      - CV (coefficient of variation) = std / mean
      - If CV > 2.0: flag and test time-of-day-adjusted bucketing

    Stationarity:
      - Autocorrelation of flow_imbalance across buckets
      - Breusch-Pagan heteroskedasticity test on per-bucket flow_imbalance
      - ADF stationarity test

    Time-of-day:
      - Segment buckets by intraday regime (9:45-10:15, 11:30-13:30, 14:00-15:45)
      - Report fill_duration, flow_imbalance distribution, effective_spread per regime
      - Flag if any regime has < 10% of daily buckets (structurally thin)

    Output:
      BucketQualityResult:
        - fill_duration_cv: float
        - needs_tod_adjustment: bool  # CV > 2.0
        - stationarity: StationarityResult
        - time_of_day: TimeOfDayResult
```

### 2.6 Phase 2e: Elasticity × Volume Conditioning (Round 1 review)

**Implementation**: `core_engine/microstructure/diagnostics/elasticity_conditioning.py`

This was originally planned for Phase 3 only. The expert correctly identifies it as a Phase 2 requirement: without it, we can pass persistence while still misinterpreting liquidity states. Low elasticity could mean institutional absorption (good), terminal exhaustion (bad), or dead tape (irrelevant). The 2D heatmap disambiguates.

```
class ElasticityConditioningAnalyzer:
    """
    Computes the 2D continuation heatmap required by FAHS v1.5 Section 8.1.
    Moved from Phase 3 to Phase 2 because elasticity interpretation directly
    affects whether persistence measurements are meaningful.
    """

    Methods:
      analyze_conditioning(symbol: str, buckets: pd.DataFrame) -> ElasticityReport
      _build_2d_heatmap(events: pd.DataFrame) -> ContinuationHeatmap
      _build_3d_heatmap_by_tod(events: pd.DataFrame) -> Dict[str, ContinuationHeatmap]
      _test_monotonicity(heatmap: ContinuationHeatmap) -> MonotonicityResult

    CAUSAL ORDERING CONSTRAINT (Round 2 review — frozen before implementation):
      Elasticity is Δprice / Δsigned_volume. This is endogenous — if the signal triggers
      on imbalance in bucket t and elasticity is measured in the same bucket, we are
      conditioning on a statistic partially driven by our entry condition. This creates
      circular inference.

      RULE: Elasticity measurement window MUST strictly precede the trigger window.
        - Elasticity = median(price_impact_per_volume) over buckets [t-3, t-1]
        - Imbalance trigger evaluated at bucket t
        - Volume percentile = rolling 3-min volume at bucket t-1 close

      This 3-bucket lookback is frozen. It ensures elasticity characterizes the
      MARKET STATE BEFORE the event, not the event itself. Without this separation,
      the 2D heatmap would conflate "elasticity during the move" with "elasticity
      of the environment" — and every continuation statistic would be contaminated.

      IMPORTANT — Volume-clock vs time-clock causality (Round 3 acknowledgment):
      Because buckets are volume-based, a 3-bucket lookback represents different
      wall-clock durations across regimes:
        - Quiet midday: 3 buckets ≈ 25-40 minutes
        - Volatile open: 3 buckets ≈ 3-8 minutes
      We are conditioning on pre-trigger VOLUME state, not pre-trigger TIME state.
      This is defensible — volume-clock captures the relevant microstructure state
      regardless of wall-clock duration. But we do not claim temporal causality.

      Sensitivity test (Round 3): In addition to the 3-bucket lookback, compute
      elasticity using a FIXED 10-minute wall-clock lookback for comparison.
      If predictive power (continuation probability in favorable heatmap cells)
      diverges materially (>5pp) between volume-clock and time-clock elasticity,
      the choice of measurement clock matters — report both and note which
      produces stronger separability. This is diagnostic, not a gate.

    2D Heatmap construction:
      1. For each imbalance event at bucket t, record:
         - elasticity = median(price_impact_per_volume) over [t-3, t-1] (PRECEDING window)
         - volume_percentile = rolling 3-min volume at bucket t-1 close (PRECEDING state)
      2. Partition into 5 elasticity bins × 5 volume bins (25 cells).
      3. Per cell: continuation probability, mean forward return, event count, CI.
      4. Test monotonicity along both axes (Spearman rank correlation).

    Time-of-day stratification (FAHS v1.5 Phase 3 step l):
      Compute heatmap separately for three intraday regimes:
        - Opening absorption: 9:45-10:15
        - Midday thinning: 11:30-13:30
        - Closing imbalance: 14:00-15:45
      If signal exists in only ONE regime → effective capacity is ~2 hrs/day.
      Report: fraction of daily edge per regime.

    Critical disambiguation:
      - Low elasticity + high volume = absorption → FAVORABLE
      - Low elasticity + low volume = dead tape → NO EDGE
      - High elasticity + high volume = fragile liquidity → RISKY BUT TRADEABLE
      - High elasticity + low volume = exhaustion → ADVERSE
      If the heatmap cannot separate these quadrants, elasticity is uninformative
      for entry timing — demote to monitoring only (per FAHS v1.5 R5).

    Output:
      ElasticityReport:
        - heatmap: ContinuationHeatmap  # 5×5 grid with continuation probs, returns, counts
        - heatmap_by_tod: Dict[str, ContinuationHeatmap]  # per intraday regime
        - elasticity_monotonicity: float  # Spearman rho along elasticity axis
        - volume_monotonicity: float  # Spearman rho along volume axis
        - edge_concentration_by_tod: Dict[str, float]  # % of total edge per regime
        - gate_result: GateResult  # R5: separability exists or not
```

This analyzer is NON-OPTIONAL. If it cannot distinguish the four quadrants above, the flow hypothesis operates blind on liquidity state — which means every entry decision is a guess about whether absorption or exhaustion is occurring.

---

### 2.7 Phase 2 Supplementary: Friction Accounting & Capacity

**Implementation**: `core_engine/microstructure/diagnostics/economics.py`

```
class EconomicViabilityAnalyzer:
    """
    Computes the economic reality check: does the measured edge
    survive friction?

    Not a formal FAHS gate, but provides the data needed to evaluate
    rejection criteria R2 (net edge < 1.5 bp) and promotion criteria P1.
    """

    Methods:
      analyze_economics(symbol: str, buckets: pd.DataFrame, tier: Tier) -> EconomicReport
      _compute_net_edge_distribution(buckets: pd.DataFrame) -> EdgeDistribution
      _compute_capacity(symbol: str, volume_profile: VolumeProfile) -> CapacityEstimate
      _regime_segmented_edge(buckets: pd.DataFrame) -> Dict[str, EdgeDistribution]

    Net edge computation (enhanced Round 1 review):
      For each imbalance event detected:
        1. Entry cost = effective_spread_bps at entry bucket / 2  (half-spread per side)
        2. Forward return = price change over persistence horizon (from Phase 2b)
        3. gross_edge = forward_return (bps)
        4. net_edge = gross_edge - effective_spread_bps (full round-trip)
        5. Add 0.5 bp estimation error buffer (FAHS v1.5 Section 14.1 P1)

      Depth-blind cost adjustment (Round 2 review):
        Even the conditional spread model uses historical trade prints — which reflect
        execution at or near NBBO. But our strategy follows imbalance, which means we
        may need to LIFT offers or HIT bids beyond top-of-book. Polygon SIP data gives
        us NBBO only, not full depth. We are structurally blind to depth beyond the
        best quote.

        Mitigation (frozen before Phase 1):
          - Tier A (mega-cap): No adjustment. Top-of-book depth typically sufficient
            for our clip sizes (0.5% of 3-min volume ≈ 50-200 shares).
          - Tier B (large-cap): Apply 1.3× multiplier to conditional effective spread.
            Quoted depth is thinner; our clip may walk 1-2 levels beyond NBBO.
          - Tier C (mid-cap): Apply 1.5× multiplier to conditional effective spread.
            Depth is structurally sparse; walking the book is probable.

          Additionally, EXCLUDE any symbol-day where median NBBO quoted size (bid_size
          or ask_size) < 3× our intended clip size for that symbol. If the best quote
          cannot absorb our full order 3 times over, we are likely to walk the book
          every entry — and our cost model is blind to that depth depletion.

        State-dependent elasticity multiplier (Round 3 refinement):
          Depth stress is not only symbol-tier dependent — it is state-dependent.
          In the high-elasticity + high-imbalance quadrant (fragile liquidity), the
          book is thinnest precisely when we need to trade. A static tier multiplier
          under-penalizes exactly this quadrant.

          Compound cost formula:
            penalized_cost = effective_spread_bps × tier_multiplier × elasticity_multiplier

          Where elasticity_multiplier (based on elasticity decile of the specific event):
            - Decile 1-3 (thick liquidity): ×1.0
            - Decile 4-7 (moderate):        ×1.2
            - Decile 8-10 (fragile):        ×1.5

          Example — Tier B name in elasticity decile 9:
            penalized_cost = spread × 1.3 × 1.5 = spread × 1.95

          This compound multiplier flows into ALL net edge calculations, including:
            - Tier 1 gate T1.2 (existence)
            - Tier 3 gate T3.1 (conditional slippage per cell)
            - Capacity math (annual return projection)

          All multiplier values frozen in `constants.py`.

        Additionally, EXCLUDE any symbol-day where median NBBO quoted size (bid_size
        or ask_size) < 3× our intended clip size for that symbol. If the best quote
        cannot absorb our full order 3 times over, we are likely to walk the book
        every entry — and our cost model is blind to that depth depletion.

        These multipliers and the quoted-size filter are frozen in constants.py.
        They are conservative estimates. Live shadow-mode (Phase 4) will calibrate
        them against actual execution, but we do NOT use the optimistic NBBO-only
        cost in Phase 2 gate decisions.

      Regime-conditioned slippage model (Round 1 review):
        Historical effective_spread underestimates REALIZED spread for liquidity-taking
        strategies because it ignores adverse selection conditional on signal strength.
        When we enter on strong imbalance, the other side knows something — our effective
        cost is WORSE than the average trade's effective cost.

        Compute: realized_cost = f(|flow_imbalance|, elasticity_decile, spread_regime)
        - Segment events by |flow_imbalance| tercile × elasticity tercile (9 cells)
        - For each cell: measure actual effective_spread at entry vs trailing median spread
        - If high-imbalance + high-elasticity cell shows spread > 2× median → adverse
          selection is real. Adjust net edge for that cell using the CONDITIONAL spread,
          not the unconditional median.
        - Flag: if net edge collapses specifically in high-elasticity states (where
          signal fires most aggressively), the strategy fails live even if aggregate
          net edge > 1.5 bp. This is the most dangerous form of backtest overstating.

    Edge distribution shape analysis (Round 1 review — Vulnerability 3):
      Mean net edge and CI are necessary but insufficient. The SHAPE matters.
      If 80% of events are slightly negative and 20% are large positive, the mean
      looks good but implementation may miss the tail events due to participation
      constraint, latency, or signal lag.

      For each symbol, report the FULL net edge distribution:
        - Percentiles: P10, P25, P50, P75, P90
        - Skewness and kurtosis
        - Fraction of events with net_edge > 0 (hit rate)
        - Fraction of events with net_edge > 2× effective_spread (strong events)
        - Ratio: mean(positive events) / |mean(negative events)| (win/loss asymmetry)

      RED FLAG: If P50 (median) < 0 but mean > 0 → edge depends on rare outliers.
      A thin-edge strategy CANNOT rely on rare positive outliers because:
        - Participation constraints may prevent full position on large moves
        - Signal detection may lag the fastest-moving events
        - Live slippage is worst during the largest moves (adverse selection)
      If P50 < 0 on >60% of symbols → edge distribution is adversarial. Flag for review.

    Capacity with clustered entry stress test (Round 1 review):
      Per-symbol participation caps are correct, but portfolio capital may cluster
      directionally during macro events when imbalance signals fire simultaneously.

      Compute:
        - Cross-symbol signal concurrency: for each bucket timestamp, count how many
          symbols have active imbalance events simultaneously.
        - Distribution of concurrent signals: median, P90, P95, max.
        - Worst-case directional exposure: if P95 concurrent signals = 8 symbols, all
          same direction, at 2% allocation each → 16% directional exposure (exceeds
          the 10% cap from FAHS Section 12.1).
        - Simulate: with FAHS portfolio controls (10% directional cap, 3 per sector,
          8 entries/hour throttle), what fraction of qualified signals are actually
          tradeable? This is the CAPACITY UTILIZATION RATE.
        - If utilization < 40% during high-opportunity periods → capacity constraint
          dominates, and daily P&L estimates must be revised downward.

        Constrained P&L simulation (Round 3 — replaces linear scaling):
          Linear utilization scaling (e.g., "35% utilization → multiply P&L by 0.35") assumes
          the signals that survive portfolio constraints are statistically identical to those
          that don't. That assumption is false. The 35% that survive may be the LEAST
          correlated or STRONGEST signals, or the weakest ones that happen not to overlap.

          Required approach — simulate, don't scale:
            1. Take the full event timeline across all symbols.
            2. Apply actual FAHS portfolio constraints sequentially in real time:
               - 10% aggregate directional cap
               - 3 per sector limit
               - 8 entries/hour throttle
               - 2% per-symbol allocation cap
               - Participation constraint (0.5% of rolling 3-min volume)
            3. Accept/reject each event in chronological order based on portfolio state.
            4. Compute the REALIZED sequence P&L path (not independent-event sum).
            5. Compare:
               - Naive P&L (sum of all event returns, unconstrained)
               - Constrained P&L (events that actually survived portfolio gate)
               - Utilization-scaled naive P&L (linear scaling baseline)
            6. Report:
               - constrained_sharpe vs naive_sharpe
               - constrained_annual_return vs utilization_adjusted_return
               - Signal quality differential: mean edge of accepted vs rejected events

          Deterministic replay already exists — this is a natural extension.
          Use it. Linear scaling is lazy and potentially misleading.

      Cross-symbol event return correlation (Round 2 review):
        Signal concurrency counts miss the deeper risk: if event RETURNS are correlated,
        portfolio-level Sharpe and Kelly sizing overestimate stability.
        Compute:
          - For all pairs of symbols with overlapping imbalance events (within same hour),
            compute: corr(event_return_i, event_return_j)
          - Aggregate: median pairwise correlation, and sector-level average correlation.
          - If median pairwise event return correlation > 0.4 → diversification is illusory.
            Portfolio Sharpe estimate must be deflated by sqrt(1 + (N-1)*rho) / sqrt(N)
            instead of the naive 1/sqrt(N) scaling.
          - Report: correlation matrix of event returns, sector-aggregated correlation,
            diversification-adjusted Sharpe estimate.

      Directional clustering & event beta (Round 3 refinement):
        Pairwise correlation may be modest yet the portfolio structurally long beta.
        Example: 8 symbols fire long imbalance in the same macro hour, 6 are tech —
        pairwise corr is moderate but portfolio is a disguised index momentum bet.

        Required additional metrics:
          1. Event beta to SPY:
             - For each imbalance event, compute SPY intraday return over the same
               event window (entry bucket to persistence horizon).
             - Regress: event_return_i = α + β × SPY_event_return + ε
             - Report: median event β, distribution of β, fraction of events with |β| > 0.6
             - Tier 3 gate T3.4: if median |event_β| > 0.6, "flow alpha" is partially
               disguised index momentum. Must be disclosed and separated before sizing.

          2. Sector-concentration-weighted beta during event windows:
             - When events cluster, compute portfolio-level beta weighted by
               actual position sizes (clip_size × signal direction).
             - If sector (GICS 2-digit) concentration exceeds 60% of active signals,
               flag as sector crowding.
             - Report: max_sector_concentration_during_cluster, portfolio_beta_during_cluster.

        These metrics do NOT kill the program — but they determine whether portfolio-level
        sizing must include explicit beta hedging or sector caps.

        This addresses a structural gap: per-symbol edge can look independent while
        returns are driven by common macro flow. If event returns cluster, the portfolio
        behaves as a single concentrated bet during drawdowns — exactly when
        diversification is most needed.

      - At 0.5% of rolling 3-min volume: max position size per entry
      - At 2% of NAV: max position size per allocation
      - Binding constraint = min(participation, allocation, directional_room)
      - Daily capacity = binding_constraint × expected_entries_per_day × utilization_rate

    Regime segmentation:
      - Segment trading days by realized volatility regime (low/mid/high tertiles)
      - Compute edge per regime — INCLUDING regime-conditioned slippage
      - Flag if edge collapses in high-vol regime

    Output:
      EconomicReport:
        - net_edge_mean_bps: float
        - net_edge_ci_lower: float  # 95% CI lower bound
        - net_edge_ci_upper: float
        - net_edge_median_bps: float  # P50 — critical for distribution shape
        - gross_edge_mean_bps: float
        - effective_spread_mean_bps: float
        - edge_distribution: EdgeDistributionStats  # percentiles, skew, kurtosis, hit_rate
        - conditional_spread: Dict[str, float]  # imbalance×elasticity cell → realized spread
        - daily_capacity_dollars: float
        - capacity_utilization_rate: float  # Fraction of signals actually tradeable
        - signal_concurrency: ConcurrencyStats  # concurrent signal distribution
        - event_beta_to_spy: BetaStats        # median, distribution, frac > 0.6 (Round 3)
        - sector_concentration_during_cluster: float  # max sector % when events cluster
        - portfolio_beta_during_cluster: float
        - annual_return_estimate_pct: float
        - sharpe_estimate: float
        - regime_edges: Dict[str, EdgeDistributionStats]  # per regime, full distribution
        - edge_positive_symbol_pct: float  # % of symbols with positive MEDIAN net edge
```

### 2.7 Phase 2 Supplementary: Self-Impact Analysis

**Implementation**: `core_engine/microstructure/diagnostics/self_impact.py`

```
class SelfImpactAnalyzer:
    """
    Simulates our hypothetical participation and measures whether
    it contaminates the elasticity signal.

    Implements FAHS v1.5 impact_ex_self requirement.
    """

    Methods:
      analyze_self_impact(symbol: str, buckets: pd.DataFrame,
                          participation_levels: List[float] = [0.0025, 0.005]) -> SelfImpactReport

    For each participation level:
      1. For each bucket, add our hypothetical signed volume:
         our_volume = bucket.actual_volume × participation_level
         (Direction matches the detected imbalance — we're following the flow)
      2. Recompute price_impact_per_volume excluding our volume:
         impact_ex_self = Δmidpoint / (signed_volume - our_signed_volume)
      3. Compare raw vs ex-self elasticity.
      4. If divergence > 10% on > 15% of events → symbol cannot support our size.

    Elasticity-conditioned self-impact (Round 1 review):
      Impact is nonlinear. Aggregate divergence may pass while specific conditions fail.
      The expert correctly identifies that we might pass aggregate self-impact but fail
      in thin states — exactly where signal triggers most.

      Segment self-impact analysis by elasticity decile:
        - For each elasticity quintile, compute:
          - mean divergence %
          - fraction of events with divergence > 10%
          - adjusted continuation probability
        - If HIGH elasticity quintile (Q5) shows divergence > 10% on > 25% of events,
          even if aggregate is fine → that elasticity regime is contaminated.
        - Entries in high-elasticity states must then carry a self-impact penalty
          in net edge calculation (Phase 2 economics).

      This catches the nonlinearity the expert identifies: in thin regimes (high elasticity),
      even 0.25% participation may represent 2-5% of actual bucket volume, creating
      outsized impact that doesn't show up in the aggregate.

    Output:
      SelfImpactReport:
        - participation_level: float
        - events_with_divergence_gt_10pct: float  # Fraction (aggregate)
        - mean_divergence_pct: float
        - divergence_by_elasticity_quintile: Dict[int, DivergenceStats]  # Q1-Q5
        - symbols_excluded: List[str]  # Cannot support our participation
        - adjusted_continuation_probs: Dict[int, ContinuationResult]  # R6 check
        - elasticity_contaminated_quintiles: List[int]  # Quintiles where divergence > threshold
```

---

### 2.8 Diagnostic Runner (Experiment Integration)

**Implementation**: `backtest/experiments/foundation_diagnostic.py`

```
class FoundationDiagnosticExperiment(BaseExperiment):
    """
    Integrates Phase 2 diagnostics into the existing experiment framework.
    Produces structured ExperimentResult for automated evaluation.

    Run via: python -m backtest.run_suite --experiment foundation_diagnostic
                --config microstructure/diagnostic.yaml
    """

    Extends: BaseExperiment (existing)

    Methods:
      async run() -> ExperimentResult
      _evaluate_program_gates(report: FoundationReport) -> Dict[str, Any]
      _generate_decision_tables(report: FoundationReport) -> Dict[str, pd.DataFrame]

    Output structure (in backtest/results/foundation_diagnostic/):
      foundation_diagnostic_YYYYMMDD_HHMMSS/
        ├── summary.json              # Program decision + gate results
        ├── persistence/
        │   ├── half_life_by_symbol.csv
        │   ├── continuation_table.csv    # P(continuation | k) per symbol
        │   ├── event_categorization.csv  # % micro-burst / intermediate / mandate
        │   └── survival_curves.csv
        ├── classification/
        │   ├── three_way_comparison.csv
        │   ├── noise_injection.csv
        │   ├── quality_by_symbol.csv
        │   ├── regime_conditioned_quality.csv  # Per vol-regime classification accuracy
        │   └── quote_lag_accuracy.csv          # Accuracy vs quote_age
        ├── buckets/
        │   ├── fill_duration_stats.csv
        │   ├── stationarity_tests.csv
        │   └── time_of_day_analysis.csv
        ├── elasticity/                          # NEW: Phase 2e
        │   ├── continuation_heatmap_5x5.csv     # Elasticity × volume grid
        │   ├── heatmap_by_tod.csv               # Per intraday regime
        │   └── monotonicity_tests.csv
        ├── economics/
        │   ├── net_edge_distribution.csv
        │   ├── edge_distribution_shape.csv      # Percentiles, skew, kurtosis
        │   ├── conditional_spread.csv           # Imbalance × elasticity → realized spread
        │   ├── capacity_estimates.csv
        │   ├── signal_concurrency.csv           # Cross-symbol clustering analysis
        │   ├── event_beta_to_spy.csv           # Per-event β regression results (Round 3)
        │   ├── sector_clustering.csv           # Sector concentration during event windows
        │   └── regime_breakdown.csv
        ├── self_impact/
        │   ├── impact_analysis.csv
        │   └── elasticity_conditioned_impact.csv # Per quintile divergence
        ├── hash_audit.json            # SHA256 hashes per symbol-day (Round 3)
        └── gate_decisions.json       # Each gate: PASS/FAIL + evidence + constants_version
```

---

## 3. MODULE STRUCTURE (Final)

```
core_engine/microstructure/
├── __init__.py
├── types.py                          # Dataclasses: VolumeBucket, ClassifiedTrade, etc.
├── constants.py                      # FAHS-derived constants (thresholds, gates)
│
├── ingestion/
│   ├── __init__.py
│   ├── universe_scanner.py           # Universe construction + tier classification
│   ├── bulk_downloader.py            # Polygon historical tick/quote download
│   ├── tick_validator.py             # Raw data quality validation
│   └── pipeline.py                   # Orchestrates the full ingestion pipeline
│
├── classification/
│   ├── __init__.py
│   └── lee_ready.py                  # Lee-Ready trade classifier
│
├── bucketing/
│   ├── __init__.py
│   └── volume_clock.py               # Volume-clock bucket engine
│
├── metrics/
│   ├── __init__.py
│   └── flow_metrics.py               # Derived flow metrics computation
│
├── diagnostics/
│   ├── __init__.py
│   ├── foundation.py                 # Master diagnostic engine (Phase 2 orchestrator)
│   ├── persistence.py                # Phase 2b: Persistence + regime + monotonicity + threshold sweep
│   ├── classification_quality.py     # Phase 2c: Lee-Ready quality + regime conditioning
│   ├── bucket_quality.py             # Phase 2d: Volume bucket stationarity
│   ├── elasticity_conditioning.py    # Phase 2e: Elasticity × volume 2D heatmap
│   ├── economics.py                  # Net edge + capacity + distribution shape + concurrency
│   └── self_impact.py                # Self-impact simulation + elasticity conditioning
│
└── schema/
    └── clickhouse_ddl.sql            # Table definitions

backtest/experiments/
    └── foundation_diagnostic.py      # Phase 2 experiment (extends BaseExperiment)

core_engine/config/catalog/microstructure/
    ├── universe.yaml                 # Universe construction config
    ├── ingestion.yaml                # Ingestion pipeline config
    └── diagnostic.yaml               # Phase 2 diagnostic config
```

---

## 4. EXECUTION SEQUENCE

### Pre-Flight: Polygon API Confirmation (before any code)

Before writing code, confirm these Polygon Stock Advanced plan parameters:

| Item | What to verify | Impact if wrong |
|------|---------------|-----------------|
| Historical trade retention | How far back can you pull tick data? Need ≥ 130 trading days (~6 calendar months). | Shorter retention → compressed study window |
| Historical quote retention | Same for NBBO quotes. | Missing quotes = broken Lee-Ready |
| API rate limits | Calls/min on Stock Advanced tier. Confirm ≥ unlimited or know the cap. | Week 1 bulk download timeline depends on this |
| Backfill bandwidth | Data volume per symbol-day (trades + quotes). Estimate total GB for 10 symbols × 130 days. | Storage planning, ClickHouse disk. Target: 220GB. Kill: 250GB. |
| Nanosecond timestamps | Confirm `sip_timestamp` field is available and in nanoseconds. | UInt64 schema assumption; if microseconds, adjust |
| Condition codes | Confirm trade condition codes are included in response. | Needed for odd-lot filtering, validation |
| Quote conflation | Are NBBO quote updates conflated (batched) or individual? | Conflation degrades quote_age_ns accuracy |

**Timestamp semantics risk** (final review — operational risk #2):
Everything downstream depends on trade-quote timestamp alignment. The Week 0 probe
MUST explicitly verify:
- Distribution of (trade_timestamp - nearest_quote_timestamp) deltas
- Presence of negative deltas (quote arriving after trade it should precede)
- Whether quote update timestamps cluster at millisecond boundaries
- If millisecond clustering is observed, we are NOT operating at nanosecond precision
  regardless of API field labeling. Adjust `quote_age_ns` thresholds accordingly.

This is a hard dependency for Lee-Ready validity. If timestamps are silently rounded
or SIP-conflated, classification accuracy degrades in exactly the volatile regimes
where it matters most.

**Pre-download storage audit** (required before any ingestion):

Existing ClickHouse data may span 2+ years. Before allocating storage for the
falsification dataset, measure actual current usage:

```sql
SELECT sum(bytes_on_disk) / 1e9 AS used_gb FROM system.parts WHERE active = 1;
SELECT sum(total_bytes) / 1e9 AS total_capacity_gb FROM system.disks;
```

Storage allocation rule:
- Available = total_capacity - current_usage
- Allocate: 60% of available as hard ceiling for falsification dataset
- Reserve: 20% buffer for compaction spikes, temporary merge files
- Reserve: 20% emergency headroom

If allocated ceiling < 220GB → reduce symbol count or period.
Do NOT assume ClickHouse won't eat your disk. Enforce the ceiling.

Log results in `docs/polygon_api_confirmation.md`. If any item fails → reassess timeline.

---

### Week 0: Feasibility Probe (3-5 days)

**Purpose**: Pipeline validation on minimal data. Discover breakage at 3 symbol-days, not 3 terabytes. This is NOT research — it is engineering proof.

**Probe scope**: 3 symbols (1 per tier) × 3 trading days.

| Day | Task | Gate |
|-----|------|------|
| 0 | Select 3 probe symbols (1 Tier A, 1 Tier B, 1 Tier C). No optimization — pick representatively. | Symbols selected |
| 1 | Universe YAML frozen (full candidate list, tier defs, liquidity guardrails, logged stats). | YAML committed to repo |
| 1 | ClickHouse DDL created and executed (`trades`, `quotes`, `volume_buckets`, `diagnostic_results`). | Tables exist, constraints verified |
| 1 | Module scaffolding: `core_engine/microstructure/` tree, `types.py`, `constants.py` with `CONSTANTS_VERSION`. | Module imports clean |
| 2 | Implement `BulkTickQuoteDownloader` (minimal — single symbol-day capable). Download 3 symbols × 3 days. | Data in ClickHouse. Confirm: timestamp alignment, quote-trade matching, field completeness |
| 2-3 | Implement `LeeReadyClassifier`. Run on probe data. | Classification matches manual spot-check on 10 trades. Midpoint accuracy > 85% |
| 3 | Implement `VolumeClockBucketer`. Run on classified probe data. | ~200 buckets/day ±20%. Integer cumsum confirmed. |
| 3-4 | SHA256 hash verification: re-run bucketing on same data. Hashes must match exactly. | Deterministic replay passes |
| 4 | Measure: memory footprint per symbol-day, ClickHouse ingest speed, real bucket counts vs ADV assumptions. | Documented in probe report |
| 4-5 | Run Tier 1 diagnostics ONLY on probe data (continuation, net edge, temporal — even on 3 days, compute the metrics to verify code paths). | Diagnostic pipeline executes end-to-end without errors |

**Probe deliverable**: `docs/feasibility_probe_report.md`

Section A — Polygon Data Quality:
- Timestamp alignment: [USABLE / PROBLEMATIC]
- Quote-trade match rate: X%
- Trade-quote delta distribution: P10/P50/P90/P99 in microseconds
- Negative delta count: X (should be ~0)
- Millisecond clustering observed: [YES / NO]
- Classification spot-check (10 manual trades): [PASS / FAIL]

Section B — ClickHouse Performance (operational risk #1):
- Insert throughput: X rows/sec (trades), Y rows/sec (quotes)
- Disk usage per symbol-day: trades X MB, quotes Y MB, total Z MB
- Projected total disk for 10 symbols × 130 days: X GB (target: 220GB, kill: 250GB)
- Bucket aggregation query latency (single symbol-day): X ms
- Bucket aggregation query latency (single symbol, full 130 days): X ms
- MergeTree compaction observed: [YES — healthy / NO — investigate]
- Compression ratio: X:1

Section B.2 — Storage Projection (MANDATORY):
- Exact bytes per symbol-day (measured, not estimated): X MB
- Compression ratio achieved: X:1
- `Estimated_total_bytes = bytes_per_symbol_day × N_symbols × N_days`
- Projected total for 10 symbols × 130 days: X GB
- Verdict: [WITHIN TARGET / REDUCE SYMBOLS / REDUCE DAYS]
- If projected > 220GB → reduce to 9 symbols. If still > 220GB → reduce to 8.
- Do NOT "hope" compression improves.

Section C — Pipeline Validation:
- Memory per symbol-day (peak RSS): X MB
- Bucket count vs ADV/200 expectation: [WITHIN 20% / OUTLIER]
- Deterministic replay (SHA256 match on re-run): [PASS / FAIL]
- Tier 1 diagnostic code paths: [ALL EXECUTE / ERRORS]
- Blocking issues discovered: [list or NONE]

**Gate**: If probe reveals blocking issues (broken timestamps, unacceptable memory, non-deterministic replay, classification < 80% accuracy), fix BEFORE proceeding. Do NOT scale a broken pipeline.

If probe passes cleanly → greenlight bulk ingestion (Week 1).

---

### Week 1: Universe Freeze + Bulk Ingestion

Correct sequence: YAML → DDL → scaffold → probe → bulk. The probe already built the core components. Week 1 scales them.

| Day | Task | Gate |
|-----|------|------|
| 1 | Implement full `UniverseScanner`. Run on ~30-40 candidates with 20-day observation window. Select 10 (3A/3B/4C). | Frozen tier classification with ≥5 sectors, liquidity guardrails enforced |
| 1 | Verify all hard liquidity filters pass: NBBO size ≥ 5× clip, ≥ 50k trades/day, ≤ 3% odd-lot-only days. | Exclusion log committed |
| 2-3 | Scale `BulkTickQuoteDownloader` for full universe. Handle pagination, rate limiting, resume-on-failure. Begin bulk download. | Download running, progress tracking |
| 3-5 | Monitor download. Validate incoming data incrementally (spot-check 1 symbol-day per tier). | All symbol-days downloaded, completeness > 95% |

---

### Week 2: Classification + Bucketing + Data Quality Report

| Day | Task | Gate |
|-----|------|------|
| 1-2 | Scale `LeeReadyClassifier` across full universe. Run on all downloaded data. | tick_rule_fallback_pct < 20% per symbol |
| 2-3 | Scale `VolumeClockBucketer` across full universe. | ~200 buckets/day ±20% per symbol |
| 3-4 | Implement `TickDataValidator`. Run on all data. Flag invalid days. | Quality report generated, < 5% invalid days per symbol |
| 4 | Implement `MicrostructureIngestionPipeline` (Stages 0-6 including SHA256 hash audit). Run full pipeline. | All symbols bucketed, hashes logged |
| 4-5 | **DETERMINISTIC REPLAY GATE**: Re-run pipeline on 5 random symbol-days. Compare hashes. | Bitwise identical. If not → fix before Week 3. No exceptions. |

**Week 2 Deliverable: Data Quality Report** (`results/data_quality_report/`)

Generated BEFORE any diagnostic code runs. This is your audit shield.

| Metric | Per-Symbol Output |
|--------|-------------------|
| Missing quote % | % of trade timestamps with no matching quote within 1 second |
| Trade-to-quote match rate | % of trades successfully matched to NBBO |
| Median quote age at classification | Milliseconds — staleness of quote used for Lee-Ready |
| % high-lag buckets | Buckets where median quote_age > 50ms |
| Bucket fill time distribution | P10, P50, P90 of fill_duration_ms |
| Classification confidence | Mean classification_confidence per symbol |
| Odd-lot day count | Days flagged as odd-lot-dominant |
| Deterministic replay result | PASS/FAIL + hash values |

**Gate**: If data quality is structurally uneven across tiers (e.g., Tier C quote match rate < 70% while Tier A > 95%), downstream economics conclusions for Tier C are suspect. Flag and note in decision report.

Week 2 ends ONLY when the pipeline is bitwise stable and the data quality report is clean.

---

### Week 3: Diagnostics (Phase 2)

**CRITICAL DISCIPLINE**: Execute hierarchical gates in strict order. Tier 1 ONLY first.

| Day | Task | Gate |
|-----|------|------|
| 1 | Implement `FlowMetricsComputer` (Phase 2a). | Distributions, autocorrelations, stationarity for all symbols |
| 2 | Implement `PersistenceAnalyzer` (Phase 2b) — regime conditioning, magnitude monotonicity, threshold sweep, temporal stability, three confidence regimes. | Continuation table, dual half-life, event categorization |
| 2 | **RUN TIER 1 GATES IMMEDIATELY.** T1.1 (continuation), T1.2 (net edge), T1.3 (temporal stability), T1.4 (classification correlation). | **If ANY Tier 1 gate fails → STOP. Do not proceed to Tier 2. Do not look at elasticity heatmaps "out of curiosity."** |
| 3 | Only if Tier 1 passes: Implement `ClassificationQualityAssessor` (Phase 2c) + `BucketQualityAnalyzer` (Phase 2d) + `ElasticityConditioningAnalyzer` (Phase 2e). | Three-way comparison, noise injection, heatmap, monotonicity |
| 3 | **RUN TIER 2 GATES.** T2.1-T2.5. | If ≥ 2 Tier 2 gates fail → TERMINATE |
| 4-5 | Only if Tier 2 passes: Implement `EconomicViabilityAnalyzer` (conditional slippage, edge shape, concurrency, event beta, constrained P&L simulation) + `SelfImpactAnalyzer`. | Full Tier 3 economics |
| 5 | **RUN TIER 3 GATES.** T3.1-T3.6. | If ≥ 2 Tier 3 gates fail → TERMINATE |

No cherry-picking. No "let me just check one more thing." The hierarchy is law.

---

### Week 4: Integration + Decision

| Day | Task | Gate |
|-----|------|------|
| 1-2 | Implement `FoundationDiagnosticEngine` + `FoundationDiagnosticExperiment`. | Full diagnostic run produces structured output |
| 3 | Run full Phase 2 diagnostic suite. | Decision tables generated with `CONSTANTS_VERSION` embedded |
| 4 | Evaluate program gates against frozen FAHS criteria. | PROCEED / TERMINATE / MICRO_BURST_CONTINGENCY |
| 5 | Document results. Submit to external quant for adversarial review. | Decision report ready |

**Submission package for external review** (not just passing tables):
- `constants.py` (frozen thresholds)
- SHA256 hash logs (per symbol-day)
- Data quality report
- ALL gate results (including failures and near-misses)
- Decision tables with full evidence
- Feasibility probe report
- Known limitations and caveats

---

## 5. DECISION TABLE OUTPUT FORMAT

The final output of Phase 2 is NOT a dashboard. It is a decision table.

### Gate 1: Persistence (FAHS R1, R3) — Regime-Conditioned

| Symbol | Tier | HL (buckets) | HL (min) | HL (norm) | P(cont\|k=3) | CI Lower | CI Width | Micro-Burst % | Mag. Mono. ρ | Threshold Stable? | GATE |
|--------|------|-------------|---------|-----------|--------------|----------|----------|---------------|-------------|-------------------|------|
| AAPL | A | ... | ... | ... | ... | ... | ... | ... | ... | Y/N | PASS/FAIL |
| TSLA | A | ... | ... | ... | ... | ... | ... | ... | ... | Y/N | PASS/FAIL |
| ... | | | | | | | | | | | |
| **AGG** | | | | | | | | | | | **PROCEED/ABORT** |

Per-regime sub-table (for each symbol):
| Regime | HL (min) | P(cont\|k=3) | Net Edge (bps) | Event Count | GATE |
|--------|---------|--------------|----------------|-------------|------|
| Low-Vol | ... | ... | ... | ... | ... |
| Mid-Vol | ... | ... | ... | ... | ... |
| High-Vol | ... | ... | ... | ... | ... |

Aggregate decision rules:
- If >80% of symbols fail persistence gate → ABORT PROGRAM.
- If >60% of events are micro-burst across universe → MICRO_BURST_CONTINGENCY.
- If persistence exists in low-vol but collapses in high-vol → FLAG: structurally unstable.
- If magnitude monotonicity fails BOTH parts (rho + economic spread) on >60% of symbols → noise clustering.
- If threshold stability fails (cont. > 55% at < 3 of 5 thresholds) on >60% of symbols → edge is parameter-sensitive.
- If temporal stability fails (edge positive in < 2 of 3 blocks) on >60% of symbols → regime-fragile alpha.
- If all-bucket persistence (regime 1) fails but high-confidence (regime 2) passes → classification-dependent. Flag.

### Gate 2: Classification (FAHS Phase 2c gate) — Regime-Conditioned

| Symbol | Best Method | Corr (all) | Corr (hi-vol) | t-stat @ 15% Noise | Tick Fallback % | Quote-Lag Degrad? | GATE |
|--------|-------------|-----------|---------------|--------------------|--------------------|-------------------|------|
| AAPL | lee_ready | ... | ... | ... | ... | Y/N | PASS/FAIL |
| ... | | | | | | | |
| **AGG** | | | | | | | **PROCEED/ABORT** |

- If high-vol correlation drops >5pp below all-regime correlation → persistence from high-vol days is flagged as potentially biased.

### Gate 3: Elasticity Conditioning (FAHS R5) — NEW

| Symbol | Elasticity Monotonicity ρ | Volume Monotonicity ρ | Edge Concentration (single TOD) | Separability | GATE |
|--------|--------------------------|----------------------|--------------------------------|-------------|------|
| AAPL | ... | ... | ... | Y/N | PASS/FAIL |
| ... | | | | | |
| **AGG** | | | | | **PROCEED/ABORT** |

- If no monotonic structure on >60% of symbols → elasticity is uninformative. Demote to monitoring.
- If >70% of edge concentrates in single TOD window → capacity-constrained. Revise P&L estimates.

### Gate 4: Economics (FAHS R2) — Enhanced

| Symbol | Tier | Gross Edge | Eff. Spread | Net Edge (mean) | Net Edge (P50) | CI Lower | Hit Rate | Skew | Cond. Spread (hi-elas) | GATE |
|--------|------|-----------|------------|----------------|---------------|----------|----------|------|----------------------|------|
| AAPL | A | ... | ... | ... | ... | ... | ... | ... | ... | PASS/FAIL |
| ... | | | | | | | | | | |
| **AGG** | | | | | | | | | | **PROCEED/ABORT** |

- **RED FLAG**: If P50 < 0 but mean > 0 on >60% of symbols → edge depends on rare outliers. Strategy is adversarial.
- **RED FLAG**: If net edge collapses in high-elasticity cells → adverse selection is real. Live trading will be worse.
- Capacity utilization rate: X% of qualified signals are tradeable after portfolio constraints.

### Gate 5: Self-Impact (FAHS R6) — Elasticity-Conditioned

| Symbol | Agg. Divergence | Q5 (hi-elas) Divergence | Symbols Excluded | Adj. Cont. Prob | GATE |
|--------|----------------|------------------------|-----------------|----------------|------|
| AAPL | ... | ... | — | ... | PASS/FAIL |
| ... | | | | | |

### Final Program Decision

```
PROGRAM DECISION: [PROCEED / TERMINATE / MICRO_BURST_CONTINGENCY]
CONSTANTS_VERSION: v1.6-FINAL
HIERARCHICAL GATE EXECUTION ORDER: Tier 1 → Tier 2 → Tier 3

═══════════════════════════════════════════════════════
TIER 1 — EXISTENCE (any failure = TERMINATE, skip Tier 2+3)
═══════════════════════════════════════════════════════
  T1.1 Continuation: [PASS/FAIL]
    - P(cont|k=3) all-buckets = X%, CI lower = Y%
    - Confidence regimes: all-bucket=[X%] high-conf=[Y%] weighted=[Z%]
  T1.2 Net edge: [PASS/FAIL]
    - Net edge after penalized cost (tier × elasticity multiplier) = X bps
    - Penalized cost model: Tier A ×1.0, B ×1.3, C ×1.5 × elasticity mult
  T1.3 Temporal stability: [PASS/FAIL]
    - Block results: [+/−, +/−, +/−] → X of 3 positive
  T1.4 Classification correlation: [PASS/FAIL]
    - Forward return correlation = X

  Tier 1 verdict: [ALL PASS → continue] / [ANY FAIL → TERMINATE]

═══════════════════════════════════════════════════════
TIER 2 — STRUCTURE (evaluated only if Tier 1 passes)
═══════════════════════════════════════════════════════
  T2.1 Magnitude monotonicity: [PASS/FAIL]
    - Spearman rho = X, D10-D1 spread = Ypp (required: max(8, 0.15×baseline))
    - Adjacent monotonic: Z of 9
  T2.2 Regime conditioning: [PASS/FAIL]
    - Edge positive in X of 3 vol regimes
  T2.3 Threshold sweep: [PASS/FAIL]
    - Continuation stable at X of 5 thresholds
  T2.4 Elasticity separability: [PASS/FAIL]
    - Heatmap monotonicity: ρ = X (volume), Y (elasticity)
    - Time-clock vs volume-clock divergence: Zpp
  T2.5 Noise resilience: [PASS/FAIL]
    - t-stat at 15% misclassification = X

  Tier 2 verdict: [ALL PASS → continue] / [≥2 FAIL → TERMINATE]

═══════════════════════════════════════════════════════
TIER 3 — PORTFOLIO REALITY (evaluated only if Tier 1+2 pass)
═══════════════════════════════════════════════════════
  T3.1 Conditional slippage: [PASS/FAIL]
    - High-imbalance/high-elasticity cell net edge = X bps
  T3.2 Capacity utilization: [PASS/FAIL]
    - Constrained P&L simulation:
      Naive Sharpe = X, Constrained Sharpe = Y, Utilization = Z%
  T3.3 Cross-event correlation: [PASS/FAIL]
    - Median pairwise corr = X, Sharpe deflation factor = Y
  T3.4 Event beta: [PASS/FAIL]
    - Median |event_β to SPY| = X
    - Max sector concentration during clusters = Y%
  T3.5 Self-impact: [PASS/FAIL]
    - Z symbols excluded, Q5 contamination: [NONE / MODERATE / SEVERE]
  T3.6 Edge distribution: [PASS/FAIL]
    - Median net edge = X bps, mean = Y bps
    - Shape: [HEALTHY / OUTLIER-DEPENDENT]

  Tier 3 verdict: [ALL PASS → PROCEED] / [≥2 FAIL → TERMINATE]

═══════════════════════════════════════════════════════
FINAL DECISION
═══════════════════════════════════════════════════════

If TERMINATE:
  - Tier that failed: [1 / 2 / 3]
  - Specific gates: [list with numbers]
  - Action: Archive infrastructure. Signal is dead.

If MICRO_BURST_CONTINGENCY:
  - Trigger Section 8.3.1 of FAHS v1.5
  - Redesign with revised economics before Phase 3

If PROCEED:
  - Proceed to Phase 3 (Hypothesis Testing)
  - Carry forward: persistence horizon, net edge estimates, tier viability,
    regime stability assessment, elasticity operating regime, capacity utilization,
    event beta characterization, constrained Sharpe estimate
  - Known limitations: [list any regime/TOD/elasticity constraints discovered]
  - Beta hedging required: [YES/NO based on T3.4]
```

---

## 6. NON-NEGOTIABLE ENGINEERING CONSTRAINTS

1. **Deterministic replay**: Given the same raw data + config, the pipeline produces IDENTICAL volume buckets. No random seeds, no floating-point order-dependence, no race conditions. Integer cumsum for volume accumulation. Verified in Stage 5 of ingestion pipeline.

2. **No parameter drift**: All thresholds in `constants.py` are imported from FAHS v1.5. They are not configurable. They do not change.

3. **No identity drift**: If Phase 2 shows micro-burst dominance, we do NOT quietly adapt. We trigger the formal contingency protocol.

4. **Kill fast**: If 2 of 3 primary gates (persistence, classification, economics) fail during Phase 2, stop immediately. Do not complete remaining diagnostics. Time is capital.

5. **No visualization theater**: Output is CSV decision tables and JSON gate results. Plots are optional diagnostic aids, not deliverables.

6. **Auditability**: Every diagnostic result is stored in `polygon_data.diagnostic_results` with a run_id. Any result can be reproduced and traced to the exact data and code version.

7. **Regime conditioning on ALL gates**: No gate is evaluated pooled-only. Every primary gate (persistence, classification, economics) must also pass regime-conditioned analysis. An edge that exists only in low-vol regime is structurally unstable.

8. **Integer volume arithmetic**: All volume accumulation, bucket boundary computation, and signed volume summation uses integer types (UInt64). Float conversion happens ONLY after bucket indices are fixed.

9. **Chunked processing**: No single-day quote load exceeds 2 GB resident memory. Hour-level chunking with quote carry-forward for Tier A names.

10. **Sequential processing with deterministic ordering** (Round 3): All symbol-days are processed SEQUENTIALLY, or if parallelized, merged in a deterministic order (sorted by symbol ASC, date ASC, timestamp ASC — stable merge). Parallel chunk aggregation without fixed merge order is PROHIBITED. If any future optimization introduces parallelism, it MUST produce output identical to sequential processing. All downstream analytics operate on fully sorted arrays. This prevents float non-determinism from creeping in through processing-order-dependence, especially in aggregate statistics (mean, variance) where summation order affects floating-point results.

11. **Hash-verified audit trail** (Round 3): Every symbol-day produces SHA256 hashes of raw trades, raw quotes, and final volume buckets. Stored in `diagnostic_results`. Any future re-run with hash mismatch halts and reports which stage diverged. Capital allocators require audit trails — this is not optional.

12. **Anti-rationalization discipline** (final review — operational risk #3): The biggest non-technical risk is human drift under load. Week 2 ends, data quality looks "mostly fine," one tier is slightly noisy, momentum pressure says "proceed." The discipline clauses above are not aspirational — they are hard stops. Specifically:
    - If deterministic replay fails → **STOP**. Fix pipeline. Do not proceed.
    - If data quality is structurally asymmetric across tiers → **STOP**. Flag and assess.
    - If Tier 1 fails → **STOP**. Do not look at Tier 2 "out of curiosity."
    - If constants need widening to "salvage signal" → the signal is dead. Do not modify.
    - If the probe reveals blocking issues → do not scale. Fix at probe scale first.
    Most research dies not from bad math, but from small rationalizations compounding.
    The hypothesis may die in Week 3. That is an acceptable and professionally sound outcome. Killing a bad hypothesis quickly is more valuable than sustaining a weak one slowly.

---

## 7. FROZEN DIAGNOSTIC CONSTANTS (`constants.py`)

These constants are derived from FAHS v1.5 and the expert's Round 1 review. They are frozen BEFORE any data is examined. No post-hoc modification permitted.

```python
# ============================================================================
# CONSTANTS VERSION — embedded in every diagnostic output for audit trail
# ============================================================================
CONSTANTS_VERSION = "v1.6-FINAL"  # Increment on ANY threshold change. Stored in every gate result.

# ============================================================================
# FAHS-DERIVED REJECTION THRESHOLDS (from Section 8.3)
# ============================================================================

# R1: Continuation probability
CONTINUATION_K3_POINT_MIN = 0.55          # Point estimate minimum
CONTINUATION_K3_CI_LOWER_MIN = 0.50       # 95% CI lower bound minimum
CONTINUATION_K3_CI_WIDTH_MAX = 0.06       # Maximum CI width (sample size gate)

# R2: Net edge
NET_EDGE_POINT_MIN_BPS = 1.5             # Point estimate minimum (includes 0.5 bp buffer)
NET_EDGE_CI_LOWER_MIN_BPS = 0.0          # 95% CI lower bound must be positive
ESTIMATION_ERROR_BUFFER_BPS = 0.5         # Added to all edge calculations

# R3: Micro-burst
MICRO_BURST_MAX_FRACTION = 0.60           # If >60% micro-burst → identity shift

# R4: Slippage
SLIPPAGE_MAX_RATIO_BACKTEST = 1.20        # 120% of modeled in 30-trade window

# R5: Elasticity separability (minimum monotonicity)
ELASTICITY_MIN_SPEARMAN_RHO = 0.3         # Along at least one axis

# R6: Self-impact
SELF_IMPACT_MAX_DIVERGENT_EVENTS = 0.20   # 20% of events with >10% divergence

# ============================================================================
# PERSISTENCE ANALYSIS CONSTANTS (Round 1 review additions)
# ============================================================================

# Imbalance threshold sensitivity sweep
IMBALANCE_THRESHOLDS = [0.05, 0.10, 0.15, 0.20, 0.25]
THRESHOLD_STABILITY_MIN_PASSING = 3       # Must pass at ≥3 of 5 thresholds

# Magnitude monotonicity (two-part gate — Round 2 review)
MAGNITUDE_MONOTONICITY_MIN_RHO = 0.3      # Part A: Spearman rho
MAGNITUDE_D10_D1_MIN_SPREAD_PP = 8        # Part B: D10 - D1 ≥ 8 percentage points
MAGNITUDE_ADJACENT_MONOTONIC_MIN = 7      # Part B: ≥ 7 of 9 adjacent pairs monotonic

# Regime conditioning
VOL_REGIME_TERTILES = [0.33, 0.67]        # Low / Mid / High vol split points

# ============================================================================
# CLASSIFICATION CONSTANTS
# ============================================================================

QUOTE_LAG_THRESHOLD_MS = 50               # Quote-trade matching staleness threshold
CLASSIFICATION_REGIME_DEGRADATION_PP = 5  # >5 pp correlation drop in high-vol → flag
TICK_RULE_FALLBACK_MAX_PCT = 0.20         # >20% tick rule fallback → data quality concern

# ============================================================================
# ECONOMIC ANALYSIS CONSTANTS (Round 1 review additions)
# ============================================================================

# Edge distribution shape
EDGE_MEDIAN_NEGATIVE_FLAG_PCT = 0.60      # If P50 < 0 on >60% symbols → outlier-dependent

# Capacity
DIRECTIONAL_CAP_PCT = 0.10               # 10% max directional exposure
MAX_ENTRIES_PER_HOUR = 8
MAX_ROUNDTRIPS_PER_DAY = 60
CAPACITY_UTILIZATION_MIN = 0.40           # If <40% signals tradeable → capacity-constrained

# ============================================================================
# PROMOTION CRITERIA (FAHS v1.5 Section 14.1)
# ============================================================================

PROMOTION_NET_EDGE_MIN_BPS = 1.8          # Point estimate
PROMOTION_CI_LOWER_MIN_BPS = 0.5          # 95% CI lower bound
PROMOTION_SYMBOL_STABILITY_MIN = 0.60     # Edge positive on ≥60% of symbols
PROMOTION_REGIME_STABILITY_MIN = 2        # Edge positive in ≥2 of 3 regimes
PROMOTION_TOD_BREADTH_MIN = 2             # Edge in ≥2 of 3 intraday regimes
PROMOTION_COST_MODEL_ACCURACY = 1.20      # Slippage within 120% on ≥80% trades

# ============================================================================
# ROUND 2 REVIEW ADDITIONS
# ============================================================================

# Elasticity causal ordering
ELASTICITY_LOOKBACK_BUCKETS = 3           # Elasticity measured over [t-3, t-1], trigger at t

# Depth-blind cost multipliers (tier-level)
DEPTH_COST_MULTIPLIER_TIER_A = 1.0        # No adjustment — sufficient top-of-book depth
DEPTH_COST_MULTIPLIER_TIER_B = 1.3        # 30% markup for thinner depth
DEPTH_COST_MULTIPLIER_TIER_C = 1.5        # 50% markup for sparse depth
QUOTED_SIZE_MIN_MULTIPLE = 3              # Exclude if median NBBO size < 3× clip size

# State-dependent elasticity multiplier (Round 3 — cost is state-conditional, not just cross-sectional)
ELASTICITY_COST_MULT_LOW = 1.0            # Elasticity decile 1-3: normal depth
ELASTICITY_COST_MULT_MID = 1.2            # Elasticity decile 4-7: moderate fragility
ELASTICITY_COST_MULT_HIGH = 1.5           # Elasticity decile 8-10: fragile liquidity

# Temporal stability
TEMPORAL_BLOCKS = 3                       # Non-overlapping ~43-day blocks in 130-day window
TEMPORAL_STABILITY_MIN_POSITIVE = 2       # Edge positive in ≥2 of 3 blocks
TEMPORAL_DECAY_ALERT_PCT = 0.20           # Flag if recent 2mo persistence < 80% of first 2mo

# Cross-symbol correlation
EVENT_RETURN_CORRELATION_MAX = 0.40       # If median pairwise corr > 0.4 → deflate Sharpe

# ============================================================================
# ROUND 3 REVIEW ADDITIONS
# ============================================================================

# Baseline-adaptive monotonicity
MAGNITUDE_D10_D1_SCALE = 0.15            # required_spread = max(MIN_SPREAD_PP, SCALE × baseline)

# Event beta to SPY
EVENT_BETA_TO_SPY_MAX = 0.60             # If median |event_β| > 0.6 → disguised index momentum
SECTOR_CONCENTRATION_ALERT = 0.60        # Flag if >60% of concurrent signals from one sector

# Elasticity sensitivity comparison
ELASTICITY_TIME_LOOKBACK_MINUTES = 10    # Fixed time-clock lookback for sensitivity test
ELASTICITY_DIVERGENCE_MATERIAL_PP = 5    # >5pp difference = material divergence

# ============================================================================
# PRE-IMPLEMENTATION REVIEW ADDITIONS (universe liquidity guardrails)
# ============================================================================

# Hard liquidity filters (applied to ALL tiers during universe construction)
UNIVERSE_MIN_NBBO_SIZE_MULTIPLE = 5      # Exclude if median NBBO size < 5× clip
UNIVERSE_TIER_C_MIN_DAILY_TRADES = 50000 # Tier C absolute floor
UNIVERSE_MAX_ODD_LOT_DAY_PCT = 0.03      # Exclude if >3% odd-lot-only days

# Feasibility probe parameters
PROBE_SYMBOLS_PER_TIER = 1               # 1 symbol per tier for probe
PROBE_DAYS = 3                           # 3 trading days for probe
PROBE_MIN_CLASSIFICATION_ACCURACY = 0.85 # Midpoint accuracy threshold for probe pass

# Data quality report thresholds
DATA_QUALITY_MIN_QUOTE_MATCH_RATE = 0.90 # Flag if trade-to-quote match < 90%
DATA_QUALITY_HIGH_LAG_BUCKET_MAX = 0.15  # Flag if >15% of buckets have quote_age > 50ms

# ============================================================================
# FALSIFICATION DATASET SPEC (storage-constrained revision)
# ============================================================================

DATASET_TARGET_SYMBOLS = 10              # 3A + 3B + 4C; adjustable 9-12 after probe
DATASET_MAX_SYMBOLS = 12                 # Hard cap — no expansion beyond this
DATASET_TIER_A_COUNT = 3
DATASET_TIER_B_COUNT = 3
DATASET_TIER_C_COUNT = 4                 # Extra Tier C for fragility testing
DATASET_MIN_SECTORS = 5
DATASET_TRADING_DAYS = 130               # Most recent 130 completed trading days
DATASET_STORAGE_TARGET_GB = 220          # Target storage ceiling
DATASET_STORAGE_KILL_GB = 250            # Halt ingest immediately if exceeded
DATASET_STORAGE_HARD_CAP_GB = 300        # Absolute max including all overhead
MIN_IMBALANCE_EVENTS_PER_SYMBOL = 200    # Below this → use quintiles instead of deciles
QUINTILE_ADJACENT_MONOTONIC_MIN = 3      # 3 of 4 pairs when using quintiles

# Constants version embedding rule:
# Every JSON gate output MUST include: "constants_version": CONSTANTS_VERSION
# Every CSV diagnostic MUST include a header row: # constants_version=v1.6-FINAL
# If constants_version in stored results ≠ current CONSTANTS_VERSION, halt and report.
```

---

**Last Updated**: February 14, 2026
**Governing Document**: `docs/flow_alpha_hypothesis_set.md` (FAHS v1.5 SEALED)
**Constants Version**: v1.6-FINAL
**Status**: LOCKED v1.6-FINAL — Falsification dataset: 10 symbols (3A/3B/4C) × 130 days, 220GB target, 250GB kill-switch. All structural, pre-implementation, go/no-go, and storage reviews incorporated. External quant approved. No further refinement. This is a controlled experiment, not an ambition project. Next action: Polygon API confirmation → ClickHouse storage audit → Universe YAML → DDL → Module scaffolding → Week 0 probe. Build.
