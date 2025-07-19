-- Trading Signals Table Schema
-- For storing generated trading signals and their metadata

CREATE TABLE trading_signals (
    id UInt64,
    timestamp DateTime64(3) CODEC(DoubleDelta, LZ4),
    symbol LowCardinality(String),
    signal_type LowCardinality(String), -- 'BUY', 'SELL', 'HOLD'
    strength Float64 CODEC(T64, LZ4), -- Signal strength 0.0 to 1.0
    price Float64 CODEC(T64, LZ4),
    target_price Float64 CODEC(T64, LZ4),
    stop_loss Float64 CODEC(T64, LZ4),
    confidence Float64 CODEC(T64, LZ4),
    model_name LowCardinality(String),
    model_version String,
    features Map(String, Float64),
    metadata Map(String, String),
    executed Bool DEFAULT false,
    execution_price Nullable(Float64),
    execution_time Nullable(DateTime64(3)),
    pnl Nullable(Float64),
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY (toYYYYMM(timestamp), signal_type)
ORDER BY (symbol, timestamp, model_name)
TTL timestamp + INTERVAL 1 YEAR
SETTINGS 
    index_granularity = 8192;
