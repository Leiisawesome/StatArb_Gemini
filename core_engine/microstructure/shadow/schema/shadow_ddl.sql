-- ============================================================================
-- Shadow Trading System — ClickHouse DDL
-- Spec: v1.7-SHADOW (frozen)
-- Build Plan: v4-FINAL
--
-- RULES:
--   - INSERT only. No UPDATEs. Immutability protects audit integrity.
--   - All timestamps are Int64 nanoseconds since epoch unless noted.
--   - LowCardinality(String) for all symbol/category columns.
--   - Every table embeds constants_version for audit trail.
-- ============================================================================

CREATE DATABASE IF NOT EXISTS shadow_trading;

-- ============================================================================
-- shadow_events: every detected imbalance event (accepted or rejected)
-- ============================================================================
CREATE TABLE IF NOT EXISTS shadow_trading.shadow_events (
    event_id            String,
    constants_version   LowCardinality(String),
    symbol              LowCardinality(String),
    event_date          Date,
    event_timestamp_ns  Int64 CODEC(Delta, ZSTD(3)),

    -- Bucket context
    bucket_id           UInt64,
    flow_imbalance      Float32,
    bucket_volume       UInt64,
    num_trades          UInt32,
    vwap                Float64,

    -- Quote at event
    bid_at_event        Float64,
    ask_at_event        Float64,
    spread_bps_at_event Float32,

    -- Entry evaluation (200ms later)
    spread_ratio        Float32,
    baseline_spread     Float64,
    quote_age_ms        Float32,
    spread_at_entry_bps Float32,

    -- Spread trajectory (at event_end, +100ms, +200ms)
    spread_t0_bps       Float32,
    spread_t100_bps     Float32,
    spread_t200_bps     Float32,

    -- NBBO integrity flags
    nbbo_locked         UInt8,      -- 1 = rejected due to locked
    nbbo_crossed        UInt8,      -- 1 = rejected due to crossed
    nbbo_stale          UInt8,      -- 1 = rejected due to staleness
    nbbo_flickering     UInt8,      -- 1 = rejected due to too few updates
    quote_updates_in_window UInt16,

    -- Decision
    accepted            UInt8,      -- 1 = accepted for order
    rejection_reason    LowCardinality(String),  -- 'deadzone', 'inventory', 'position', 'nbbo', 'staleness', ''
    sub_strategy        LowCardinality(String),  -- 'competitive', 'shock', ''

    -- Classification quality
    classification_confidence Float32,
    tick_rule_fallback_pct    Float32,

    -- Odd-lot tracking
    odd_lot_pct         Float32

) ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (symbol, event_date, event_timestamp_ns)
SETTINGS index_granularity = 8192;


-- ============================================================================
-- shadow_orders: every order placed (entry or exit)
-- ============================================================================
CREATE TABLE IF NOT EXISTS shadow_trading.shadow_orders (
    order_id            String,
    constants_version   LowCardinality(String),
    symbol              LowCardinality(String),
    order_date          Date,
    order_timestamp_ns  Int64 CODEC(Delta, ZSTD(3)),

    -- Order details
    side                LowCardinality(String),  -- 'BUY' or 'SELL'
    order_type          LowCardinality(String),  -- 'LIMIT'
    limit_price         Float64,
    size                UInt32,
    intent              LowCardinality(String),  -- 'entry', 'exit'

    -- Context
    event_id            String,
    sub_strategy        LowCardinality(String),
    spread_ratio        Float32,
    flow_imbalance      Float32,

    -- Expected prices (for slippage decomposition)
    expected_fill_price Float64,

    -- Depth at order time
    nbbo_bid_size       UInt32,
    nbbo_ask_size       UInt32,
    order_depth_ratio   Float32,    -- order_size / relevant_side_size

    -- IBKR response
    ack_timestamp_ns    Int64 CODEC(Delta, ZSTD(3)),
    ack_latency_ms      Float32

) ENGINE = MergeTree()
PARTITION BY toYYYYMM(order_date)
ORDER BY (symbol, order_date, order_timestamp_ns)
SETTINGS index_granularity = 8192;


-- ============================================================================
-- shadow_fills: fill outcomes + mechanism metrics + slippage decomposition
-- ============================================================================
CREATE TABLE IF NOT EXISTS shadow_trading.shadow_fills (
    fill_id             String,
    order_id            String,
    event_id            String,
    constants_version   LowCardinality(String),
    symbol              LowCardinality(String),
    fill_date           Date,

    -- Entry
    entry_timestamp_ns  Int64 CODEC(Delta, ZSTD(3)),
    entry_price         Float64,
    entry_side          LowCardinality(String),
    sub_strategy        LowCardinality(String),
    spread_ratio        Float32,
    flow_imbalance      Float32,

    -- Exit
    exit_timestamp_ns   Int64 CODEC(Delta, ZSTD(3)),
    exit_price          Float64,
    exit_reason         LowCardinality(String),
    hold_time_ms        Float32,

    -- P&L
    pnl_bps             Float32,
    pnl_dollars         Float64,

    -- Slippage decomposition
    expected_entry_price Float64,
    actual_entry_price   Float64,
    entry_slippage_bps   Float32,

    expected_exit_price  Float64,
    actual_exit_price    Float64,
    exit_slippage_bps    Float32,

    cancel_delay_ms      Float32,
    partial_fill_ratio   Float32,
    total_slippage_bps   Float32,

    -- Depth at entry
    nbbo_bid_size       UInt32,
    nbbo_ask_size       UInt32,
    order_depth_ratio   Float32,

    -- Dual accounting (model result for same event)
    model_fill          UInt8,      -- 1 = pessimistic model says filled
    model_pnl_bps       Float32,

    -- Mechanism context
    spread_at_entry_bps Float32,
    baseline_spread_bps Float32,
    classification_confidence Float32,
    quote_age_at_entry_ms Float32,
    time_to_normalization_ms Float32,

    -- Inventory state at fill
    net_inventory_bps_at_fill Float32

) ENGINE = MergeTree()
PARTITION BY toYYYYMM(fill_date)
ORDER BY (symbol, fill_date, entry_timestamp_ns)
SETTINGS index_granularity = 4096;


-- ============================================================================
-- shadow_daily: daily aggregates for all KPIs (M1-M8)
-- ============================================================================
CREATE TABLE IF NOT EXISTS shadow_trading.shadow_daily (
    report_date         Date,
    constants_version   LowCardinality(String),

    -- Throughput
    events_detected     UInt32,
    events_accepted     UInt32,
    events_rejected_deadzone  UInt32,
    events_rejected_inventory UInt32,
    events_rejected_position  UInt32,
    events_rejected_nbbo      UInt32,
    events_rejected_staleness UInt32,
    orders_placed       UInt32,
    fills_received      UInt32,

    -- P&L
    daily_pnl_bps       Float32,
    daily_pnl_dollars   Float64,
    cumulative_pnl_bps  Float32,

    -- Sub-strategy split (M2)
    competitive_pnl_bps Float32,
    shock_pnl_bps       Float32,
    competitive_fills   UInt32,
    shock_fills         UInt32,

    -- Mechanism health surface (M1)
    m1_spread_amplitude     Float32,
    m1_normalization_speed_ms Float32,
    m1_event_frequency      Float32,
    m1_amplitude_degraded   UInt8,
    m1_speed_degraded       UInt8,
    m1_frequency_degraded   UInt8,

    -- Fill accounting (M3)
    paper_fill_rate     Float32,
    model_fill_rate     Float32,
    fill_optimism_ratio Float32,

    -- SPY beta (M4)
    spy_beta_20d        Float32,

    -- Throughput (M5)
    utilization_rate    Float32,    -- fills / events_accepted

    -- Spread ratio distribution (M6) — against frozen quintiles
    m6_q1_pct           Float32,
    m6_q2_pct           Float32,
    m6_q3_pct           Float32,
    m6_q4_pct           Float32,
    m6_q5_pct           Float32,

    -- Slippage decomposition (M7)
    m7_entry_slippage_bps   Float32,
    m7_exit_slippage_bps    Float32,
    m7_cancel_delay_ms      Float32,

    -- NBBO integrity (M8)
    m8_locked_crossed_rate  Float32,
    m8_quote_frequency      Float32,
    m8_odd_lot_ratio        Float32,

    -- Latency
    ingest_p95_ms       Float32,
    order_rtt_p95_ms    Float32,
    cancel_ack_p95_ms   Float32,

    -- Kill status
    kill_triggered      UInt8,
    kill_condition      LowCardinality(String),

    -- Rolling metrics (for kill evaluation)
    rolling_30d_pnl_bps Float32,
    rolling_5d_drawdown_bps Float32

) ENGINE = MergeTree()
PARTITION BY toYYYYMM(report_date)
ORDER BY (report_date)
SETTINGS index_granularity = 8192;


-- ============================================================================
-- shadow_latency: per-quote/per-order latency observations
-- ============================================================================
CREATE TABLE IF NOT EXISTS shadow_trading.shadow_latency (
    observation_date    Date,
    observation_ns      Int64 CODEC(Delta, ZSTD(3)),
    symbol              LowCardinality(String),
    path                LowCardinality(String),  -- 'ingest', 'order_rtt', 'cancel_ack'
    latency_ms          Float32,

    -- For ingest path
    exchange_ts_ns      Int64 CODEC(Delta, ZSTD(3)),
    system_receive_ns   Int64 CODEC(Delta, ZSTD(3))

) ENGINE = MergeTree()
PARTITION BY toYYYYMM(observation_date)
ORDER BY (symbol, path, observation_date, observation_ns)
TTL observation_date + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;


-- ============================================================================
-- shadow_state_log: transactional order state for crash recovery
-- ============================================================================
CREATE TABLE IF NOT EXISTS shadow_trading.shadow_state_log (
    log_id              String,
    log_timestamp_ns    Int64 CODEC(Delta, ZSTD(3)),
    log_date            Date,

    order_id            String,
    symbol              LowCardinality(String),
    side                LowCardinality(String),
    intent              LowCardinality(String),  -- 'entry_submitted', 'monitoring_exit', 'exit_pending', 'closed'
    size                UInt32,
    limit_price         Float64,

    -- Optional fields (populated as state progresses)
    fill_price          Nullable(Float64),
    fill_size           Nullable(UInt32),
    stop_attached       UInt8 DEFAULT 0,

    exit_order_id       Nullable(String),
    pnl_bps             Nullable(Float32),

    -- Depth at entry (for scaling calibration)
    nbbo_bid_size       Nullable(UInt32),
    nbbo_ask_size       Nullable(UInt32),

    constants_version   LowCardinality(String)

) ENGINE = MergeTree()
PARTITION BY toYYYYMM(log_date)
ORDER BY (order_id, log_timestamp_ns)
SETTINGS index_granularity = 8192;


-- ============================================================================
-- shadow_spread_baselines: daily rolling 20-day median spread per symbol
-- ============================================================================
CREATE TABLE IF NOT EXISTS shadow_trading.shadow_spread_baselines (
    baseline_date       Date,
    symbol              LowCardinality(String),
    baseline_spread     Float64,    -- rolling 20-day median of inside spread
    sample_count        UInt32,     -- number of quotes in computation
    constants_version   LowCardinality(String)

) ENGINE = ReplacingMergeTree()
PARTITION BY toYYYYMM(baseline_date)
ORDER BY (symbol, baseline_date)
SETTINGS index_granularity = 8192;
