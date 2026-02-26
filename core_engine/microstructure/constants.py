"""
Frozen diagnostic constants for the Flow Alpha Hypothesis Set (FAHS v1.5).

These constants are derived from FAHS v1.5 and multiple rounds of expert review.
They are frozen BEFORE any data is examined. No post-hoc modification permitted.

Governing documents:
    - docs/flow_alpha_hypothesis_set.md (FAHS v1.5 SEALED)
    - docs/phase_1_2_implementation_blueprint.md (v1.6-FINAL LOCKED)

Every JSON gate output MUST include: "constants_version": CONSTANTS_VERSION
Every CSV diagnostic MUST include a header row: # constants_version=v1.6-FINAL
If constants_version in stored results != current CONSTANTS_VERSION, halt and report.
"""

from typing import List

# ============================================================================
# CONSTANTS VERSION — embedded in every diagnostic output for audit trail
# ============================================================================
CONSTANTS_VERSION: str = "v1.6-FINAL"

# ============================================================================
# FAHS-DERIVED REJECTION THRESHOLDS (from Section 8.3)
# ============================================================================

# R1: Continuation probability
CONTINUATION_K3_POINT_MIN: float = 0.55
CONTINUATION_K3_CI_LOWER_MIN: float = 0.50
CONTINUATION_K3_CI_WIDTH_MAX: float = 0.06

# R2: Net edge
NET_EDGE_POINT_MIN_BPS: float = 1.5
NET_EDGE_CI_LOWER_MIN_BPS: float = 0.0
ESTIMATION_ERROR_BUFFER_BPS: float = 0.5

# R3: Micro-burst
MICRO_BURST_MAX_FRACTION: float = 0.60

# R4: Slippage
SLIPPAGE_MAX_RATIO_BACKTEST: float = 1.20

# R5: Elasticity separability (minimum monotonicity)
ELASTICITY_MIN_SPEARMAN_RHO: float = 0.3

# R6: Self-impact
SELF_IMPACT_MAX_DIVERGENT_EVENTS: float = 0.20

# ============================================================================
# PERSISTENCE ANALYSIS CONSTANTS (Round 1 review)
# ============================================================================

IMBALANCE_THRESHOLDS: List[float] = [0.05, 0.10, 0.15, 0.20, 0.25]
THRESHOLD_STABILITY_MIN_PASSING: int = 3

# Magnitude monotonicity (two-part gate — Round 2 review)
MAGNITUDE_MONOTONICITY_MIN_RHO: float = 0.3
MAGNITUDE_D10_D1_MIN_SPREAD_PP: int = 8
MAGNITUDE_ADJACENT_MONOTONIC_MIN: int = 7

# Regime conditioning
VOL_REGIME_TERTILES: List[float] = [0.33, 0.67]

# ============================================================================
# CLASSIFICATION CONSTANTS
# ============================================================================

QUOTE_LAG_THRESHOLD_MS: int = 50
CLASSIFICATION_REGIME_DEGRADATION_PP: int = 5
TICK_RULE_FALLBACK_MAX_PCT: float = 0.20

# ============================================================================
# ECONOMIC ANALYSIS CONSTANTS (Round 1 review)
# ============================================================================

EDGE_MEDIAN_NEGATIVE_FLAG_PCT: float = 0.60

# Capacity
DIRECTIONAL_CAP_PCT: float = 0.10
MAX_ENTRIES_PER_HOUR: int = 8
MAX_ROUNDTRIPS_PER_DAY: int = 60
CAPACITY_UTILIZATION_MIN: float = 0.40

# ============================================================================
# PROMOTION CRITERIA (FAHS v1.5 Section 14.1)
# ============================================================================

PROMOTION_NET_EDGE_MIN_BPS: float = 1.8
PROMOTION_CI_LOWER_MIN_BPS: float = 0.5
PROMOTION_SYMBOL_STABILITY_MIN: float = 0.60
PROMOTION_REGIME_STABILITY_MIN: int = 2
PROMOTION_TOD_BREADTH_MIN: int = 2
PROMOTION_COST_MODEL_ACCURACY: float = 1.20

# ============================================================================
# ROUND 2 REVIEW ADDITIONS
# ============================================================================

ELASTICITY_LOOKBACK_BUCKETS: int = 3

# Depth-blind cost multipliers (tier-level)
DEPTH_COST_MULTIPLIER_TIER_A: float = 1.0
DEPTH_COST_MULTIPLIER_TIER_B: float = 1.3
DEPTH_COST_MULTIPLIER_TIER_C: float = 1.5
QUOTED_SIZE_MIN_MULTIPLE: int = 3

# State-dependent elasticity multiplier (Round 3)
ELASTICITY_COST_MULT_LOW: float = 1.0
ELASTICITY_COST_MULT_MID: float = 1.2
ELASTICITY_COST_MULT_HIGH: float = 1.5

# Temporal stability
TEMPORAL_BLOCKS: int = 3
TEMPORAL_STABILITY_MIN_POSITIVE: int = 2
TEMPORAL_DECAY_ALERT_PCT: float = 0.20

# Cross-symbol correlation
EVENT_RETURN_CORRELATION_MAX: float = 0.40

# ============================================================================
# ROUND 3 REVIEW ADDITIONS
# ============================================================================

MAGNITUDE_D10_D1_SCALE: float = 0.15

# Event beta to SPY
EVENT_BETA_TO_SPY_MAX: float = 0.60
SECTOR_CONCENTRATION_ALERT: float = 0.60

# Elasticity sensitivity comparison
ELASTICITY_TIME_LOOKBACK_MINUTES: int = 10
ELASTICITY_DIVERGENCE_MATERIAL_PP: int = 5

# ============================================================================
# PRE-IMPLEMENTATION REVIEW (universe liquidity guardrails)
# ============================================================================

UNIVERSE_MIN_NBBO_SIZE_MULTIPLE: int = 5
UNIVERSE_TIER_C_MIN_DAILY_TRADES: int = 50000
UNIVERSE_MAX_ODD_LOT_DAY_PCT: float = 0.03

# Feasibility probe parameters
PROBE_SYMBOLS_PER_TIER: int = 1
PROBE_DAYS: int = 3
PROBE_MIN_CLASSIFICATION_ACCURACY: float = 0.85

# Data quality report thresholds
DATA_QUALITY_MIN_QUOTE_MATCH_RATE: float = 0.90
DATA_QUALITY_HIGH_LAG_BUCKET_MAX: float = 0.15

# ============================================================================
# FALSIFICATION DATASET SPEC (storage-constrained)
# ============================================================================

DATASET_TARGET_SYMBOLS: int = 10
DATASET_MAX_SYMBOLS: int = 12
DATASET_TIER_A_COUNT: int = 3
DATASET_TIER_B_COUNT: int = 3
DATASET_TIER_C_COUNT: int = 4
DATASET_MIN_SECTORS: int = 5
DATASET_TRADING_DAYS: int = 130
DATASET_STORAGE_TARGET_GB: int = 220
DATASET_STORAGE_KILL_GB: int = 250
DATASET_STORAGE_HARD_CAP_GB: int = 300
MIN_IMBALANCE_EVENTS_PER_SYMBOL: int = 200
QUINTILE_ADJACENT_MONOTONIC_MIN: int = 3

# ============================================================================
# INGESTION PIPELINE CONSTANTS
# ============================================================================

TARGET_BUCKETS_PER_DAY: int = 200
ADV_LOOKBACK_DAYS: int = 20
MAX_INVALID_DAY_PCT: float = 0.05
MIN_TRADES_PER_DAY: int = 5000
MAX_STALE_QUOTE_PCT: float = 0.10
MONOTONICITY_VIOLATION_THRESHOLD: float = 0.001
REPLAY_TEST_SYMBOL_DAYS: int = 5
