-- Performance Analytics Table Schema
-- For storing strategy and portfolio performance metrics

CREATE TABLE performance_analytics (
    id UInt64,
    timestamp DateTime64(3) CODEC(DoubleDelta, LZ4),
    entity_type LowCardinality(String), -- 'PORTFOLIO', 'STRATEGY', 'MODEL'
    entity_id LowCardinality(String),
    period LowCardinality(String), -- 'DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY'
    total_return Float64 CODEC(T64, LZ4),
    sharpe_ratio Float64 CODEC(T64, LZ4),
    sortino_ratio Float64 CODEC(T64, LZ4),
    max_drawdown Float64 CODEC(T64, LZ4),
    volatility Float64 CODEC(T64, LZ4),
    alpha Float64 CODEC(T64, LZ4),
    beta Float64 CODEC(T64, LZ4),
    var_95 Float64 CODEC(T64, LZ4),
    var_99 Float64 CODEC(T64, LZ4),
    win_rate Float64 CODEC(T64, LZ4),
    profit_factor Float64 CODEC(T64, LZ4),
    avg_win Float64 CODEC(T64, LZ4),
    avg_loss Float64 CODEC(T64, LZ4),
    total_trades UInt32 CODEC(T64, LZ4),
    winning_trades UInt32 CODEC(T64, LZ4),
    losing_trades UInt32 CODEC(T64, LZ4),
    benchmark_return Float64 CODEC(T64, LZ4),
    tracking_error Float64 CODEC(T64, LZ4),
    information_ratio Float64 CODEC(T64, LZ4),
    calmar_ratio Float64 CODEC(T64, LZ4),
    metrics Map(String, Float64),
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY (toYYYYMM(timestamp), entity_type)
ORDER BY (entity_type, entity_id, period, timestamp)
TTL timestamp + INTERVAL 5 YEAR
SETTINGS 
    index_granularity = 8192;
