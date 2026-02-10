"""
Phase 0 Configuration — Constants and tunables.

Design principle: coarse-correct, not finely optimized.
If any constant here requires surgical precision to produce signal, the signal is noise.
"""

from datetime import datetime
from typing import List

# ═══════════════════════════════════════════════
# Universe & Date Range
# ═══════════════════════════════════════════════
UNIVERSE: List[str] = [
    # Core equity (high-ADV, institutional flow)
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'AMD',
    # Market proxies (REQUIRED for RPS decomposition)
    'SPY', 'QQQ', 'IWM'
]

EQUITY_SYMBOLS: List[str] = [s for s in UNIVERSE if s not in ['SPY', 'QQQ']]
MARKET_PROXY: str = 'SPY'

# Minimum 6 months, preferred 9-12. Must span multiple vol regimes.
# Adjust to available data in ClickHouse.
START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2024, 12, 31)

# ═══════════════════════════════════════════════
# Feature Parameters (DO NOT TUNE — use defaults)
# ═══════════════════════════════════════════════

# PathEff multi-scale windows (bars)
PATHEFF_WINDOWS: List[int] = [5, 15, 45]

# Normalization: trailing window in RTH bars (~5 trading days)
NORM_WINDOW: int = 1950

# CounterFail
COUNTERFAIL_TREND_WINDOW: int = 15
COUNTERFAIL_MIN_COUNTER_BARS: int = 2
COUNTERFAIL_LOOKBACKS: List[int] = [20, 40]

# VolStore
VOLSTORE_SHORT_SPAN: int = 5
VOLSTORE_LONG_SPAN: int = 45
VOLSTORE_COMPRESSION_THRESHOLD: float = 0.7
VOLSTORE_RELEASE_RATIO: float = 1.5
VOLSTORE_MIN_COMPRESSION_BARS: int = 10
VOLSTORE_RELEASE_WINDOW: int = 10

# PropAccel
PROPACCEL_BASE_K: int = 5
PROPACCEL_VOL_REF_WINDOW: int = 100

# PS aggregation
VOLSTORE_FLOOR: float = 0.3  # allows continuation trades without compression
SIGMOID_SCALE: float = 5.0   # sigmoid steepness for PropAccel mapping

# Propagation direction
DIRECTION_WINDOW: int = 15
DIRECTION_SMOOTH_SPAN: int = 5

# RPS
RPS_BETA_WINDOW: int = 1950

# ═══════════════════════════════════════════════
# Transaction Costs (from existing base_config.yaml)
# ═══════════════════════════════════════════════

# Round-trip: spread (5 bps one-way) + slippage (2 bps) + commission (~0.5 bps)
ROUND_TRIP_COST_BPS: float = 15.0

# ═══════════════════════════════════════════════
# Forward Returns
# ═══════════════════════════════════════════════
FORWARD_HORIZONS: List[int] = [5, 15, 30]
PRIMARY_HORIZON: int = 15  # primary horizon for kill criteria

# ═══════════════════════════════════════════════
# Statistical Tests
# ═══════════════════════════════════════════════
MIN_OBSERVATIONS_PER_CELL: int = 50
BLOCK_SIZE: int = 30         # block-bootstrap block size (bars)
N_PERMUTATIONS: int = 5000   # permutation test iterations
SIGNIFICANCE_LEVEL: float = 0.05

# ═══════════════════════════════════════════════
# Kill Criteria Thresholds
# ═══════════════════════════════════════════════
KILL_MAE_IMPROVEMENT_PCT: float = 15.0     # ≥15% reduction in 95th-pctile MAE
KILL_ECONOMIC_IMPROVEMENT_PCT: float = 15.0  # ≥15% improvement in risk-adj return
KILL_MAX_INVERSIONS: int = 1               # monotonicity: ≤1 adjacent inversion
KILL_MIN_REGIMES_PASS: int = 2             # regime invariance: ≥2 of 3 regimes

# ═══════════════════════════════════════════════
# Data Validation
# ═══════════════════════════════════════════════
MAX_MISSING_RATE: float = 0.005      # 0.5%
MIN_TRADING_DAYS: int = 120
EXPECTED_BARS_PER_DAY: int = 390     # 9:30 AM to 4:00 PM
PRICE_ANOMALY_THRESHOLD: float = 0.10  # 10% single-bar move
SESSION_GAP_SECONDS: int = 300       # 5-minute gap = session break

# ═══════════════════════════════════════════════
# Parameter Perturbation Sets
# ═══════════════════════════════════════════════
PERTURBATION_WINDOW_SETS: List[List[int]] = [
    [3, 10, 30],
    [5, 15, 45],   # default
    [8, 20, 60],
    [5, 13, 34],   # Fibonacci-like
    [4, 12, 40],
]

# ═══════════════════════════════════════════════
# Output
# ═══════════════════════════════════════════════
OUTPUT_DIR: str = 'backtest/results/phase0'
