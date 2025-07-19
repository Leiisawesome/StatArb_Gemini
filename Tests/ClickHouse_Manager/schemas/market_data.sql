-- Market Data Table Schema
-- Optimized for high-frequency trading data storage and retrieval

CREATE TABLE market_data (
    timestamp DateTime64(3) CODEC(DoubleDelta, LZ4),
    symbol LowCardinality(String),
    open Float64 CODEC(T64, LZ4),
    high Float64 CODEC(T64, LZ4),
    low Float64 CODEC(T64, LZ4),
    close Float64 CODEC(T64, LZ4),
    volume UInt64 CODEC(T64, LZ4),
    vwap Float64 CODEC(T64, LZ4),
    trade_count UInt32 CODEC(T64, LZ4),
    bid Float64 CODEC(T64, LZ4),
    ask Float64 CODEC(T64, LZ4),
    bid_size UInt32 CODEC(T64, LZ4),
    ask_size UInt32 CODEC(T64, LZ4),
    updated_at DateTime DEFAULT now()
) 
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (symbol, timestamp)
TTL timestamp + INTERVAL 2 YEAR
SETTINGS 
    index_granularity = 8192,
    storage_policy = 'default';
