-- ============================================================================
-- Microstructure Module — ClickHouse DDL
-- Blueprint: docs/phase_1_2_implementation_blueprint.md v1.6-FINAL
-- Constants: v1.6-FINAL
--
-- RULES:
--   - INSERT only. No UPDATEs. Immutability protects audit integrity.
--   - All timestamps are Int64 nanoseconds since epoch.
--   - LowCardinality(String) for all symbol/category columns.
--   - Compression codecs tuned per column type for 50-65 bytes/row target.
-- ============================================================================

CREATE DATABASE IF NOT EXISTS polygon_data;

-- ============================================================================
-- Raw trades table
-- ============================================================================
CREATE TABLE IF NOT EXISTS polygon_data.microstructure_trades (
    symbol              LowCardinality(String),
    sip_timestamp       Int64 CODEC(Delta, ZSTD(3)),
    exchange_timestamp  Int64 CODEC(Delta, ZSTD(3)),
    price               Float64 CODEC(DoubleDelta, ZSTD(1)),
    size                UInt32 CODEC(T64, ZSTD(1)),
    exchange_id         UInt8,
    conditions          Array(Int32),
    tape                UInt8,
    trade_id            String CODEC(ZSTD(3)),
    ingestion_date      Date
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(ingestion_date)
ORDER BY (symbol, sip_timestamp)
SETTINGS index_granularity = 8192;


-- ============================================================================
-- Raw NBBO quotes table
-- ============================================================================
CREATE TABLE IF NOT EXISTS polygon_data.microstructure_quotes (
    symbol              LowCardinality(String),
    sip_timestamp       Int64 CODEC(Delta, ZSTD(3)),
    bid_price           Float64 CODEC(DoubleDelta, ZSTD(1)),
    ask_price           Float64 CODEC(DoubleDelta, ZSTD(1)),
    bid_size            UInt32 CODEC(T64, ZSTD(1)),
    ask_size            UInt32 CODEC(T64, ZSTD(1)),
    bid_exchange        UInt8,
    ask_exchange        UInt8,
    conditions          Array(Int32),
    ingestion_date      Date
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(ingestion_date)
ORDER BY (symbol, sip_timestamp)
SETTINGS index_granularity = 8192;


-- ============================================================================
-- Volume-clock buckets (computed output, not raw data)
-- ============================================================================
CREATE TABLE IF NOT EXISTS polygon_data.microstructure_buckets (
    symbol                  LowCardinality(String),
    bucket_id               UInt64,
    bucket_start_ns         Int64 CODEC(Delta, ZSTD(3)),
    bucket_end_ns           Int64 CODEC(Delta, ZSTD(3)),
    bucket_volume           UInt64 CODEC(T64, ZSTD(1)),
    actual_volume           UInt64 CODEC(T64, ZSTD(1)),
    num_trades              UInt32,
    -- OHLCV
    open_price              Float64 CODEC(DoubleDelta, ZSTD(1)),
    close_price             Float64 CODEC(DoubleDelta, ZSTD(1)),
    high_price              Float64 CODEC(DoubleDelta, ZSTD(1)),
    low_price               Float64 CODEC(DoubleDelta, ZSTD(1)),
    vwap                    Float64,
    -- Lee-Ready classified flow
    signed_volume           Int64 CODEC(T64, ZSTD(1)),
    unsigned_volume         UInt64 CODEC(T64, ZSTD(1)),
    buy_volume              UInt64 CODEC(T64, ZSTD(1)),
    sell_volume             UInt64 CODEC(T64, ZSTD(1)),
    indeterminate_volume    UInt64 CODEC(T64, ZSTD(1)),
    -- Classification quality
    classification_confidence Float32,
    tick_rule_fallback_pct    Float32,
    -- Quote context at bucket boundaries
    bid_at_start            Float64,
    ask_at_start            Float64,
    bid_at_end              Float64,
    ask_at_end              Float64,
    median_spread_bps       Float32,
    -- Derived metrics
    flow_imbalance          Float32,
    effective_spread_bps    Float32,
    price_impact_per_volume Float32,
    -- Metadata
    bucket_date             Date,
    fill_duration_ms        UInt32
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(bucket_date)
ORDER BY (symbol, bucket_date, bucket_id)
SETTINGS index_granularity = 4096;


-- ============================================================================
-- Diagnostic results (Phase 2 outputs — append-only audit trail)
-- ============================================================================
CREATE TABLE IF NOT EXISTS polygon_data.microstructure_diagnostics (
    run_id              String,
    constants_version   LowCardinality(String),
    symbol              LowCardinality(String),
    metric_name         LowCardinality(String),
    metric_value        Float64,
    metric_metadata     String,     -- JSON blob for additional context
    computed_at         DateTime,
    run_date            Date
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(run_date)
ORDER BY (run_id, symbol, metric_name)
SETTINGS index_granularity = 8192;
