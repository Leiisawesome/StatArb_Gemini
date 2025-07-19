-- Portfolio Positions Table Schema
-- For tracking current and historical portfolio positions

CREATE TABLE portfolio_positions (
    id UInt64,
    timestamp DateTime64(3) CODEC(DoubleDelta, LZ4),
    portfolio_id LowCardinality(String),
    symbol LowCardinality(String),
    position_type LowCardinality(String), -- 'LONG', 'SHORT'
    quantity Float64 CODEC(T64, LZ4),
    entry_price Float64 CODEC(T64, LZ4),
    current_price Float64 CODEC(T64, LZ4),
    market_value Float64 CODEC(T64, LZ4),
    unrealized_pnl Float64 CODEC(T64, LZ4),
    realized_pnl Float64 CODEC(T64, LZ4),
    cost_basis Float64 CODEC(T64, LZ4),
    weight Float64 CODEC(T64, LZ4), -- Portfolio weight percentage
    risk_metrics Map(String, Float64),
    entry_signal_id Nullable(UInt64),
    status LowCardinality(String), -- 'ACTIVE', 'CLOSED', 'PARTIAL'
    created_at DateTime DEFAULT now(),
    updated_at DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY (toYYYYMM(timestamp), portfolio_id)
ORDER BY (portfolio_id, symbol, timestamp)
TTL timestamp + INTERVAL 3 YEAR
SETTINGS 
    index_granularity = 8192;
