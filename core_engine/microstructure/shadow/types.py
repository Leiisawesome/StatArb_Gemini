"""
Shadow trading type definitions.

All dataclasses align with the ClickHouse schema in schema/shadow_ddl.sql
and the shadow_trading_spec_v1.7.md + shadow_trading_build_plan.md v4-FINAL.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional


# ============================================================================
# Enums
# ============================================================================

class SubStrategy(enum.Enum):
    COMPETITIVE = "competitive"   # spread_ratio < 1.0
    SHOCK = "shock"               # spread_ratio > 2.0


class ExitReason(enum.Enum):
    SPREAD_NORMALIZATION = "spread_normalization"
    TIMEOUT = "timeout"
    STOP_LOSS = "stop_loss"
    MANUAL_CLOSE = "manual_close"      # crash recovery / EOD flatten


class OrderIntent(enum.Enum):
    """Transactional state for crash recovery."""
    ENTRY_SUBMITTED = "entry_submitted"
    MONITORING_EXIT = "monitoring_exit"
    EXIT_PENDING = "exit_pending"
    CLOSED = "closed"


class KillConditionType(enum.Enum):
    INVENTORY_BREACH = "inventory_breach"
    LATENCY_BREACH = "latency_breach"
    INTRADAY_LOSS = "intraday_loss"
    M1_MECHANISM_PAUSE = "m1_mechanism_pause"
    ROLLING_PNL_LOW = "rolling_pnl_low"
    FILL_RATE_LOW = "fill_rate_low"
    CORRELATION_HIGH = "correlation_high"
    HALFLIFE_DRIFT = "halflife_drift"
    DRAWDOWN_5D = "drawdown_5d"


class LatencyPath(enum.Enum):
    INGEST = "ingest"           # Polygon → system
    ORDER_RTT = "order_rtt"     # system → IBKR ack
    CANCEL_ACK = "cancel_ack"   # IBKR cancel → confirmation


class NBBOIssue(enum.Enum):
    LOCKED = "locked"           # bid == ask
    CROSSED = "crossed"         # bid > ask
    STALE = "stale"             # quote_age > threshold
    FLICKERING = "flickering"   # too few updates in window


# ============================================================================
# Core event / signal / outcome types
# ============================================================================

@dataclass
class ImbalanceEvent:
    """Emitted by StreamingVolumeBucketer when |imbalance| exceeds p95."""
    symbol: str
    bucket_id: int
    event_timestamp_ns: int         # exchange_timestamp of last trade in bucket
    flow_imbalance: float           # signed_volume / unsigned_volume [-1, +1]
    bucket_volume: int
    num_trades: int
    vwap: float

    bid_at_end: float
    ask_at_end: float
    median_spread_bps: float

    classification_confidence: float
    tick_rule_fallback_pct: float

    bucket_date: date


@dataclass
class Quote:
    """Current NBBO quote snapshot."""
    symbol: str
    timestamp_ns: int               # exchange_timestamp
    bid_price: float
    ask_price: float
    bid_size: int
    ask_size: int

    @property
    def midpoint(self) -> float:
        return (self.bid_price + self.ask_price) / 2.0

    @property
    def spread(self) -> float:
        return self.ask_price - self.bid_price

    @property
    def spread_bps(self) -> float:
        mid = self.midpoint
        if mid <= 0:
            return 0.0
        return (self.spread / mid) * 10_000

    @property
    def is_locked(self) -> bool:
        return abs(self.bid_price - self.ask_price) < 1e-10 and self.bid_price > 0

    @property
    def is_crossed(self) -> bool:
        return self.bid_price > self.ask_price and self.bid_price > 0


@dataclass
class TradeSignal:
    """Output of EventLevelFilter — accepted event ready for order placement."""
    symbol: str
    event: ImbalanceEvent
    sub_strategy: SubStrategy
    side: str                       # "BUY" or "SELL"
    limit_price: float
    spread_ratio: float
    baseline_spread: float
    quote_at_entry: Quote
    quote_age_ms: float             # age of quote used for spread_ratio
    entry_timestamp_ns: int         # exchange_ts + 200ms delay
    spread_trajectory: List[float]  # spread at event_end, +100ms, +200ms


@dataclass
class SlippageBreakdown:
    """Per-trade slippage decomposition for M7 forensics."""
    expected_entry_price: float
    actual_entry_price: float
    entry_slippage_bps: float

    expected_exit_price: float
    actual_exit_price: float
    exit_slippage_bps: float

    cancel_delay_ms: float
    partial_fill_ratio: float       # filled_size / requested_size

    @property
    def total_slippage_bps(self) -> float:
        return self.entry_slippage_bps + self.exit_slippage_bps


@dataclass
class TradeOutcome:
    """Complete trade result logged to ClickHouse."""
    symbol: str
    trade_date: date
    sub_strategy: SubStrategy
    side: str

    # Entry
    entry_time_ns: int
    entry_price: float
    entry_spread_ratio: float
    entry_imbalance: float

    # Exit
    exit_time_ns: int
    exit_price: float
    exit_reason: ExitReason
    hold_time_ms: float

    # P&L
    pnl_bps: float
    pnl_dollars: float

    # Slippage
    slippage: SlippageBreakdown

    # Depth at entry
    nbbo_bid_size: int
    nbbo_ask_size: int
    order_depth_ratio: float        # order_size / relevant_side_size

    # Queue model (dual accounting)
    model_fill: bool                # pessimistic queue model result
    model_pnl_bps: float

    # Mechanism context
    spread_at_entry_bps: float
    baseline_spread_bps: float
    classification_confidence: float
    quote_age_at_entry_ms: float


@dataclass
class OpenPosition:
    """Tracks a single open position for inventory management."""
    order_id: str
    symbol: str
    side: str                       # "BUY" or "SELL"
    entry_price: float
    entry_time_ns: int
    size: int
    baseline_spread: float
    spread_ratio: float
    sub_strategy: SubStrategy
    imbalance_magnitude: float
    quote_age_at_entry_ms: float

    # Slippage reference points
    expected_entry_price: float
    expected_exit_price: Optional[float] = None

    # Depth at entry
    nbbo_bid_size: int = 0
    nbbo_ask_size: int = 0

    filled: bool = False
    fill_time_ns: Optional[int] = None
    fill_price: Optional[float] = None
    broker_fill_price: Optional[float] = None

    exit_order_id: Optional[str] = None
    exit_price: Optional[float] = None
    exit_time_ns: Optional[int] = None
    exit_reason: Optional[ExitReason] = None


@dataclass
class OrderStateRecord:
    """Persisted at every state transition for crash recovery."""
    order_id: str
    symbol: str
    side: str
    intent: OrderIntent
    size: int
    limit_price: float
    timestamp_ns: int

    fill_price: Optional[float] = None
    fill_size: Optional[int] = None
    stop_attached: bool = False

    exit_order_id: Optional[str] = None
    pnl_bps: Optional[float] = None


# ============================================================================
# Monitor / report types
# ============================================================================

@dataclass
class MechanismHealthSurface:
    """M1: Three-variable mechanism health."""
    median_spread_amplitude: float      # median spread_ratio at entry
    median_time_to_normalization_ms: float
    events_per_symbol_per_day: float

    baseline_amplitude: float
    baseline_normalization_ms: float
    baseline_event_frequency: float

    amplitude_degraded: bool = False
    speed_degraded: bool = False
    frequency_degraded: bool = False

    @property
    def degraded_count(self) -> int:
        return sum([self.amplitude_degraded, self.speed_degraded,
                    self.frequency_degraded])


@dataclass
class SpreadRatioDistribution:
    """M6: Rolling spread_ratio distribution against frozen quintile boundaries."""
    q1_pct: float   # < Q1 boundary
    q2_pct: float   # Q1-Q2
    q3_pct: float   # Q2-Q3 (dead zone lower)
    q4_pct: float   # Q3-Q4 (dead zone upper)
    q5_pct: float   # > Q4 boundary

    baseline_q1_pct: float = 0.0
    baseline_q2_pct: float = 0.0
    baseline_q5_pct: float = 0.0


@dataclass
class SlippageReport:
    """M7: Aggregated slippage decomposition."""
    rolling_mean_entry_slippage_bps: float
    rolling_mean_exit_slippage_bps: float
    rolling_mean_cancel_delay_ms: float
    rolling_mean_partial_fill_ratio: float

    baseline_entry_slippage_bps: float = 0.0
    baseline_exit_slippage_bps: float = 0.0
    baseline_cancel_delay_ms: float = 0.0


@dataclass
class NBBOIntegrityReport:
    """M8: NBBO integrity statistics."""
    locked_crossed_rate: float          # % of evaluations rejected
    quote_update_frequency: float       # updates per second per symbol
    odd_lot_dominance_ratio: float      # % of quotes with odd-lot
    locked_crossed_by_symbol: Dict[str, float] = field(default_factory=dict)


@dataclass
class LatencySnapshot:
    """Per-path latency statistics for InfrastructureLatencyMonitor."""
    path: LatencyPath
    p50_ms: float
    p95_ms: float
    p99_ms: float
    sample_count: int
    baseline_p95_ms: Optional[float] = None
    absolute_cap_ms: Optional[int] = None

    @property
    def relative_breach(self) -> bool:
        if self.baseline_p95_ms is None or self.baseline_p95_ms <= 0:
            return False
        return self.p95_ms > 2.0 * self.baseline_p95_ms

    @property
    def absolute_breach(self) -> bool:
        if self.absolute_cap_ms is None:
            return False
        return self.p95_ms > self.absolute_cap_ms


@dataclass
class KillEvent:
    """Logged when a kill condition triggers."""
    condition: KillConditionType
    triggered_at: datetime
    metric_value: float
    threshold: float
    detail: str
    horizon: str                    # "per_trade" or "daily_close"


@dataclass
class DailyReport:
    """End-of-day aggregation for shadow_daily table."""
    report_date: date
    constants_version: str

    # Throughput
    events_detected: int
    events_accepted: int
    events_rejected_deadzone: int
    events_rejected_inventory: int
    events_rejected_position: int
    events_rejected_nbbo: int
    events_rejected_staleness: int
    orders_placed: int
    fills_received: int

    # P&L
    daily_pnl_bps: float
    daily_pnl_dollars: float
    cumulative_pnl_bps: float

    # Sub-strategy
    competitive_pnl_bps: float
    shock_pnl_bps: float
    competitive_fills: int
    shock_fills: int

    # Mechanism health (M1)
    mechanism_health: MechanismHealthSurface

    # Fill accounting (M3)
    paper_fill_rate: float
    model_fill_rate: float
    fill_optimism_ratio: float

    # Latency
    ingest_p95_ms: float
    order_rtt_p95_ms: float
    cancel_ack_p95_ms: float

    # NBBO integrity (M8)
    nbbo_integrity: NBBOIntegrityReport

    # Kill status
    kill_triggered: bool = False
    kill_event: Optional[KillEvent] = None


@dataclass
class WeeklyReport:
    """Weekly structured review."""
    week_number: int
    daily_reports: List[DailyReport]
    constants_version: str

    # Aggregated M1-M8
    mechanism_health: MechanismHealthSurface
    spread_ratio_distribution: SpreadRatioDistribution
    slippage_report: SlippageReport
    nbbo_integrity: NBBOIntegrityReport

    # SPY beta (M4)
    spy_beta_20d: float
    spy_beta_alert: bool

    # Scaling simulation
    scaling_pnl_500: float
    scaling_pnl_1000: float

    # Depth profile
    mean_depth_ratio: float
    capacity_constrained_pct: float


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class ShadowConfig:
    """Configuration bundle for LiquidityShadowEngine."""
    polygon_api_key: str
    ibkr_host: str = "127.0.0.1"
    ibkr_port: int = 7497
    ibkr_client_id: int = 1

    clickhouse_url: str = "http://localhost:8123"
    clickhouse_db: str = "shadow_trading"

    portfolio_value: float = 200_000.0
    state_log_path: str = "data/shadow_state.json"

    # Research baselines loaded at init, frozen
    baselines_path: str = "results/shadow_backtest/baselines.json"
