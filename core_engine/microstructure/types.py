"""
Type definitions for the microstructure module.

All dataclasses align with the ClickHouse schema in schema/clickhouse_ddl.sql
and the blueprint specification (v1.6-FINAL).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional, Tuple


# ============================================================================
# Enums
# ============================================================================

class Tier(enum.Enum):
    """Universe tier classification based on liquidity characteristics."""
    A = "A"  # Mega-cap, tight spread
    B = "B"  # Large-cap, moderate spread
    C = "C"  # Mid-cap, wider spread


class TradeSign(enum.IntEnum):
    """Lee-Ready trade classification result."""
    SELL = -1
    INDETERMINATE = 0
    BUY = 1


class ClassificationMethod(enum.Enum):
    """Method used to classify a trade."""
    QUOTE_RULE = "quote_rule"       # Price vs midpoint
    TICK_RULE = "tick_rule"         # Price vs previous trade
    INDETERMINATE = "indeterminate" # At midpoint, no tick history


class ProgramDecision(enum.Enum):
    """Phase 2 program-level decision outcome."""
    PROCEED = "PROCEED"
    TERMINATE = "TERMINATE"
    MICRO_BURST_CONTINGENCY = "MICRO_BURST_CONTINGENCY"


class GateResult(enum.Enum):
    """Individual gate pass/fail result."""
    PASS = "PASS"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"  # Tier 2/3 skipped due to prior tier failure


# ============================================================================
# Raw data types (aligned with ClickHouse schema)
# ============================================================================

@dataclass(frozen=True)
class RawTrade:
    """Single trade record as stored in polygon_data.trades."""
    symbol: str
    sip_timestamp: int          # Nanoseconds since epoch
    exchange_timestamp: int     # Nanoseconds (exchange report time)
    price: float
    size: int
    exchange_id: int
    conditions: List[int]
    tape: int
    trade_id: str
    ingestion_date: date


@dataclass(frozen=True)
class RawQuote:
    """Single NBBO quote record as stored in polygon_data.quotes."""
    symbol: str
    sip_timestamp: int          # Nanoseconds since epoch
    bid_price: float
    ask_price: float
    bid_size: int
    ask_size: int
    bid_exchange: int
    ask_exchange: int
    conditions: List[int]
    ingestion_date: date


# ============================================================================
# Classification output
# ============================================================================

@dataclass(frozen=True)
class ClassifiedTrade:
    """Trade with Lee-Ready classification applied."""
    sip_timestamp: int
    price: float
    size: int
    exchange_id: int
    trade_sign: TradeSign
    method: ClassificationMethod
    midpoint: float             # NBBO midpoint at time of trade
    quote_age_ns: int           # Nanoseconds since last quote update
    spread_bps: float           # Bid-ask spread in basis points


# ============================================================================
# Volume bucket types (aligned with polygon_data.volume_buckets)
# ============================================================================

@dataclass
class VolumeBucket:
    """Single volume-clock bucket as stored in ClickHouse."""
    symbol: str
    bucket_id: int
    bucket_start_ns: int
    bucket_end_ns: int
    bucket_volume: int          # Target volume (ADV / target_buckets)
    actual_volume: int
    num_trades: int

    # OHLCV
    open_price: float
    close_price: float
    high_price: float
    low_price: float
    vwap: float

    # Lee-Ready classified flow
    signed_volume: int          # Net signed volume (buy - sell)
    unsigned_volume: int
    buy_volume: int
    sell_volume: int
    indeterminate_volume: int

    # Classification quality
    classification_confidence: float
    tick_rule_fallback_pct: float

    # Quote context
    bid_at_start: float
    ask_at_start: float
    bid_at_end: float
    ask_at_end: float
    median_spread_bps: float

    # Derived metrics
    flow_imbalance: float       # signed_volume / unsigned_volume [-1, +1]
    effective_spread_bps: float
    price_impact_per_volume: float

    # Metadata
    bucket_date: date
    fill_duration_ms: int


# ============================================================================
# Universe construction types
# ============================================================================

@dataclass
class SpreadProfile:
    """Spread characteristics for a symbol over the observation window."""
    symbol: str
    median_spread_bps: float
    spread_std_bps: float
    median_quoted_size_bid: float
    median_quoted_size_ask: float
    pct_time_locked: float      # % of time bid == ask


@dataclass
class VolumeProfile:
    """Volume characteristics for a symbol over the observation window."""
    symbol: str
    median_daily_trades: int
    median_daily_dollar_volume: float
    median_3min_volume: float
    intraday_ushape_score: float
    adv_shares: int             # Average daily volume in shares


@dataclass
class UniverseClassification:
    """Frozen output of the universe scanner."""
    tier_assignments: Dict[str, Tier]
    spread_profiles: Dict[str, SpreadProfile]
    volume_profiles: Dict[str, VolumeProfile]
    excluded_symbols: List[Tuple[str, str]]  # (symbol, exclusion_reason)
    sectors: Dict[str, str]     # symbol → GICS sector
    observation_start: date
    observation_end: date
    frozen: bool = True


# ============================================================================
# Diagnostic output types
# ============================================================================

@dataclass
class GateEvidence:
    """Evidence for a single gate evaluation."""
    gate_id: str                # e.g. "T1.1", "T2.3"
    gate_name: str
    tier: int                   # 1, 2, or 3
    result: GateResult
    metric_value: float
    threshold: float
    detail: str                 # Human-readable explanation
    constants_version: str


@dataclass
class PersistenceResult:
    """Output of persistence analysis for a single symbol."""
    symbol: str
    tier: Tier
    half_life_buckets: float
    half_life_minutes: float
    half_life_normalized: float
    continuation_prob_k3: float
    continuation_ci_lower: float
    continuation_ci_upper: float
    micro_burst_pct: float
    intermediate_pct: float
    mandate_pct: float
    magnitude_rho: float
    magnitude_d10_d1_spread_pp: float
    magnitude_adjacent_monotonic: int
    threshold_passing_count: int
    temporal_block_results: List[float]  # Net edge per block


@dataclass
class EconomicResult:
    """Output of economic viability analysis for a single symbol."""
    symbol: str
    tier: Tier
    net_edge_mean_bps: float
    net_edge_median_bps: float
    net_edge_ci_lower: float
    net_edge_ci_upper: float
    gross_edge_mean_bps: float
    effective_spread_mean_bps: float
    hit_rate: float
    edge_skew: float
    edge_kurtosis: float
    penalized_cost_bps: float   # After tier × elasticity multiplier
    daily_capacity_dollars: float
    capacity_utilization_rate: float
    annual_return_estimate_pct: float
    sharpe_estimate: float


@dataclass
class FoundationReport:
    """Complete Phase 2 diagnostic output."""
    run_id: str
    constants_version: str
    dataset_spec: Dict[str, Any]
    gate_results: List[GateEvidence]
    persistence_results: Dict[str, PersistenceResult]
    economic_results: Dict[str, EconomicResult]
    program_decision: ProgramDecision
    decision_detail: str
    data_quality_summary: Dict[str, Any]
    hash_audit: Dict[str, Dict[str, str]]  # symbol-day → {trades, quotes, buckets}


# ============================================================================
# Pipeline tracking types
# ============================================================================

@dataclass
class SymbolDayStatus:
    """Tracks ingestion status for a single symbol-day."""
    symbol: str
    trading_date: date
    trades_downloaded: bool = False
    quotes_downloaded: bool = False
    trades_row_count: int = 0
    quotes_row_count: int = 0
    classified: bool = False
    bucketed: bool = False
    validated: bool = False
    trades_hash: str = ""
    quotes_hash: str = ""
    buckets_hash: str = ""


@dataclass
class ProbeReport:
    """Week 0 feasibility probe results."""
    # Section A — Polygon Data Quality
    timestamp_alignment: str    # "USABLE" or "PROBLEMATIC"
    quote_trade_match_rate: float
    trade_quote_delta_p10_us: float
    trade_quote_delta_p50_us: float
    trade_quote_delta_p90_us: float
    trade_quote_delta_p99_us: float
    negative_delta_count: int
    millisecond_clustering: bool
    classification_spot_check: str  # "PASS" or "FAIL"

    # Section B — ClickHouse Performance
    insert_throughput_trades_per_sec: float
    insert_throughput_quotes_per_sec: float
    disk_per_symbol_day_mb: float
    projected_total_gb: float
    bucket_query_latency_ms: float
    full_range_query_latency_ms: float
    compression_ratio: float

    # Section C — Pipeline Validation
    memory_peak_rss_mb: float
    bucket_count_within_20pct: bool
    deterministic_replay_pass: bool
    tier1_code_paths_execute: bool
    blocking_issues: List[str]

    @property
    def all_pass(self) -> bool:
        return (
            self.timestamp_alignment == "USABLE"
            and self.deterministic_replay_pass
            and self.classification_spot_check == "PASS"
            and self.projected_total_gb <= 220
            and not self.blocking_issues
        )
