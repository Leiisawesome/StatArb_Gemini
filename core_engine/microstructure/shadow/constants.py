"""
Shadow Trading Constants — v1.8-SHADOW-SHOCK FROZEN

v1.7 → v1.8 changelog (approved by external quant, Step 7 findings):
    - Competitive sub-strategy REMOVED (negative expectancy in sequential sim)
    - SHOCK_ONLY = True (only spread_ratio > 2.0 entries)
    - KILL_DRAWDOWN_5D_MAX_BPS: 50 → 115 (aligned to empirical weekly variance)
    - KILL_ROLLING_30D_PNL_MIN_BPS: 0.5 → -1.0 (kill structural negative only;
      0.0 still triggered on holiday compression noise at -0.73 bps/day)
    - BACKTEST_DRAWDOWN_5D_MAX_BPS: 50 → 115 (matched to kill threshold)
    - DAILY_LOSS_STOP_BPS: -25 → -40 (backtest worst=-31; -25 truncates shock
      lumpiness; -40 allows realized variance + catches genuine blow-ups)
    - Rolling 30d P&L kill made compound (requires M1 degradation + active freq)
    - Added EVENT_FREQ_COLLAPSE_PCT for opportunity flow monitoring
    - Added CROSS_SYMBOL_CORR_ALERT for intra-universe clustering detection
    - Added REPLAY_STRESS_* constants for live-realism replay validation
    - Added REPLAY_BURST_* for adversarial replay (burst freeze, deep reorder,
      quote/trade desync) per final quant review
    - Added LOSS_VELOCITY_* for fast structural break detection
    - Added SHOCK_CLUSTER_* for forward-looking cross-symbol shock correlation
    - Added SHADOW_CI_* for pre-committed statistical acceptance rule
    - Compound frequency collapse now checks Q5 distribution shift
    - Baselines updated from Step 7 shock-only results

This file is the single source of truth for all operational parameters.
NO modifications during the 30-day shadow period.

Any change requires:
    1. Written justification
    2. External quant approval
    3. New version number (v1.9+)
    4. Restart of 30-day shadow period

Anti-drift clause: every log entry, ClickHouse insert, and report MUST embed
SHADOW_CONSTANTS_VERSION for audit trail.
"""

from typing import Dict, List

# ============================================================================
# VERSION — embedded in every output for audit trail
# ============================================================================
SHADOW_CONSTANTS_VERSION: str = "v1.8-SHADOW-SHOCK"

# ============================================================================
# STRATEGY IDENTITY
# ============================================================================
STRATEGY_NAME: str = "Liquidity Shock Normalization"
SYMBOLS: List[str] = ["MSFT", "NVDA", "TSLA", "WMT"]
PORTFOLIO_VALUE: float = 200_000.0

# ============================================================================
# ENTRY RULES
# ============================================================================
SHOCK_ONLY: bool = True
ENTRY_DELAY_MS: int = 200
SPREAD_RATIO_COMPETITIVE_MAX: float = 1.0
SPREAD_RATIO_SHOCK_MIN: float = 2.0
CLIP_SIZE: int = 100

# Frozen imbalance thresholds (p95 from research)
IMBALANCE_THRESHOLDS: Dict[str, float] = {
    "MSFT": 0.786,
    "NVDA": 0.363,
    "TSLA": 0.350,
    "WMT": 0.871,
}

# ADV for bucket sizing (shares, from universe.yaml frozen classification)
ADV_SHARES: Dict[str, int] = {
    "MSFT": 44_186_534,
    "NVDA": 175_991_947,
    "TSLA": 61_284_964,
    "WMT": 44_632_016,
}

TARGET_BUCKETS_PER_DAY: int = 200

# ============================================================================
# EXIT RULES (three-way, first triggered wins)
# ============================================================================
SPREAD_NORMAL_FACTOR: float = 1.05
STOP_LOSS_BPS: float = 3.0
TIMEOUT_S: int = 30
MIN_HOLD_MS: int = 500

# ============================================================================
# RISK RULES
# ============================================================================
NET_INVENTORY_CAP_BPS: float = 6.0
MAX_POSITIONS_PER_SYMBOL: int = 1
PER_SYMBOL_RISK_CAP_PCT: float = 0.25
DAILY_LOSS_STOP_BPS: float = -40.0

# ============================================================================
# MARKET HOURS
# ============================================================================
MARKET_OPEN_HOUR: int = 9
MARKET_OPEN_MINUTE: int = 45
MARKET_CLOSE_HOUR: int = 15
MARKET_CLOSE_MINUTE: int = 45

# ============================================================================
# NBBO INTEGRITY
# ============================================================================
QUOTE_STALENESS_MAX_MS: int = 500
MIN_QUOTE_UPDATES_IN_WINDOW: int = 2
ODD_LOT_DOMINANCE_FLAG_PCT: float = 0.30
LOCKED_CROSSED_ALERT_RATE: float = 0.02

# ============================================================================
# SPREAD BASELINE GOVERNANCE
# ============================================================================
SPREAD_BASELINE_WINDOW_DAYS: int = 20

# Frozen research quintile boundaries for M6 classification
# These NEVER update during shadow — only baseline_spread (rolling 20d) adapts
RESEARCH_QUINTILE_BOUNDARIES: Dict[str, List[float]] = {
    "MSFT": [0.8, 1.0, 1.5, 2.0],
    "NVDA": [0.8, 1.0, 1.5, 2.0],
    "TSLA": [0.8, 1.0, 1.5, 2.0],
    "WMT": [0.8, 1.0, 1.5, 2.0],
}

# ============================================================================
# LATENCY MONITORING
# ============================================================================
NTP_MAX_OFFSET_MS: int = 10
LATENCY_BASELINE_WINDOW_DAYS: int = 10
LATENCY_RELATIVE_DRIFT_MULT: float = 2.0

# Absolute caps (auto-pause if breached)
INGEST_P95_CAP_MS: int = 250
ORDER_RTT_P95_CAP_MS: int = 400
CANCEL_ACK_MEDIAN_CAP_MS: int = 500

# ============================================================================
# MECHANISM MONITOR — M1 HEALTH SURFACE
# ============================================================================
M1_DEGRADATION_THRESHOLD_PCT: float = 0.30
M1_REVIEW_MIN_DEGRADED: int = 2
M1_PAUSE_MIN_DEGRADED: int = 3

# ============================================================================
# MECHANISM MONITOR — M3 FILL ACCOUNTING
# ============================================================================
FILL_OPTIMISM_RATIO_ALERT: float = 1.5

# ============================================================================
# MECHANISM MONITOR — M4 SPY BETA
# ============================================================================
SPY_BETA_ALERT_THRESHOLD: float = 0.25
SPY_BETA_WINDOW_DAYS: int = 20

# ============================================================================
# MECHANISM MONITOR — M6 SPREAD RATIO DISTRIBUTION
# ============================================================================
M6_Q5_DROP_ALERT_PCT: float = 0.40
M6_Q12_DROP_ALERT_PCT: float = 0.30

# ============================================================================
# MECHANISM MONITOR — M7 SLIPPAGE
# ============================================================================
SLIPPAGE_DRIFT_ALERT_PCT: float = 0.50

# ============================================================================
# MECHANISM MONITOR — M8 NBBO INTEGRITY
# ============================================================================
NBBO_QUOTE_FREQ_DROP_ALERT_PCT: float = 0.30

# ============================================================================
# MECHANISM MONITOR — M9 EVENT FREQUENCY COLLAPSE
# ============================================================================
EVENT_FREQ_COLLAPSE_PCT: float = 0.50
EVENT_FREQ_BASELINE_DAYS: int = 20

# ============================================================================
# MECHANISM MONITOR — M10 CROSS-SYMBOL CORRELATION
# ============================================================================
CROSS_SYMBOL_CORR_ALERT: float = 0.50
CROSS_SYMBOL_CORR_WINDOW: int = 5

# ============================================================================
# KILL CONDITIONS — PER-TRADE (acute, checked on every trade)
# ============================================================================
# Net inventory cap, absolute latency cap, intraday loss limit
# (thresholds defined above: NET_INVENTORY_CAP_BPS, DAILY_LOSS_STOP_BPS,
#  INGEST_P95_CAP_MS, ORDER_RTT_P95_CAP_MS, CANCEL_ACK_MEDIAN_CAP_MS)

# ============================================================================
# KILL CONDITIONS — DAILY CLOSE (structural, evaluated once per day)
# ============================================================================
KILL_ROLLING_30D_PNL_MIN_BPS: float = -1.0
KILL_FILL_RATE_MIN_PCT_OF_BASELINE: float = 0.60
KILL_CORRELATION_MAX: float = 0.30
KILL_CORRELATION_SUSTAINED_DAYS: int = 5
KILL_HALFLIFE_DRIFT_PCT: float = 1.0
KILL_HALFLIFE_SUSTAINED_DAYS: int = 10
KILL_DRAWDOWN_5D_MAX_BPS: float = 115.0

# ============================================================================
# RESEARCH BASELINES (from validation/stress/mechanism reports, frozen)
# ============================================================================
BASELINE_FILL_RATE: float = 0.77
BASELINE_MEAN_PNL_BPS: float = 1.18
BASELINE_HIT_RATE: float = 0.54
BASELINE_MEAN_HOLD_S: float = 1.946
BASELINE_CVAR5_BPS: float = -5.69
BASELINE_TRUE_SHARPE: float = 4.01
BASELINE_DAILY_PNL_BPS: float = 5.82
BASELINE_PAIRWISE_CORR: float = 0.012
BASELINE_WORST_DAY_BPS: float = -20.81
BASELINE_BETA_SPREAD: float = 0.410

# ============================================================================
# STEP 7 PASS CRITERIA
# ============================================================================
BACKTEST_PNL_TOLERANCE_PCT: float = 0.15
BACKTEST_FILL_TOLERANCE_PCT: float = 0.10
BACKTEST_HIT_TOLERANCE_PCT: float = 0.08
BACKTEST_DRAWDOWN_5D_MAX_BPS: float = 115.0
BACKTEST_M6_TOLERANCE_PCT: float = 0.20

# ============================================================================
# STEP 8 REPLAY VALIDATION
# ============================================================================
REPLAY_SYMBOL_DAYS: int = 20
REPLAY_LR_DRIFT_SYMBOL_DAYS: int = 30
REPLAY_IMBALANCE_DIVERGENCE_MAX_PCT: float = 0.12
REPLAY_LR_DRIFT_HARD_PASS_PCT: float = 0.03
REPLAY_LR_DRIFT_INVESTIGATE_PCT: float = 0.05
REPLAY_FLOW_DIVERGENCE_MAX_PCT: float = 0.001

# ============================================================================
# SCALING SIMULATION
# ============================================================================
SCALING_CLIP_SIZES: List[int] = [100, 500, 1000]
DEPTH_CAPACITY_FLAG_RATIO: float = 0.50

# ============================================================================
# STEP 8 REPLAY STRESS MODE — IID noise (simulates live WS imperfections)
# ============================================================================
REPLAY_STRESS_JITTER_MS: int = 50
REPLAY_STRESS_DUPLICATE_PCT: float = 0.005
REPLAY_STRESS_DROP_PCT: float = 0.001
REPLAY_LR_DRIFT_SEGMENT_THRESHOLD: float = 0.05

# ============================================================================
# STEP 8 REPLAY STRESS MODE — ADVERSARIAL (bursty, state-corrupting)
# ============================================================================
REPLAY_BURST_FREEZE_MS: int = 300
REPLAY_BURST_FREEZE_PCT: float = 0.002
REPLAY_DEEP_REORDER_MS: int = 200
REPLAY_DEEP_REORDER_PCT: float = 0.002
REPLAY_QUOTE_TRADE_DESYNC_MS: int = 150
REPLAY_QUOTE_TRADE_DESYNC_PCT: float = 0.002

# ============================================================================
# LOSS VELOCITY MONITOR (fast structural break detection)
# ============================================================================
LOSS_VELOCITY_WINDOW_MIN: int = 30
LOSS_VELOCITY_THRESHOLD_BPS: float = 25.0

# ============================================================================
# SHOCK EVENT CLUSTERING (forward-looking M10 proxy)
# ============================================================================
SHOCK_CLUSTER_MIN_SYMBOLS: int = 3
SHOCK_CLUSTER_WINDOW_MIN: int = 5

# ============================================================================
# SHADOW STATISTICAL ACCEPTANCE (pre-committed CI rule)
# ============================================================================
SHADOW_CI_VIABLE_LOWER_BPS: float = 0.5
SHADOW_CI_DEAD_LOWER_BPS: float = 0.0
SHADOW_CI_CONFIDENCE: float = 0.95
