"""
Strategy Configurations
======================

Consolidated strategy configurations for all 10 enhanced strategy types.
Follows composition pattern with reusable sub-configs.

Author: StatArb_Gemini Configuration Consolidation (Phase 4)
Date: October 21, 2025
Version: 2.0.0 (Consolidated Architecture)
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple

# Import sub-configs from component_config
try:
    from .component_config import PositionLimits, RiskLimits, TimingConfig
except ImportError:
    # Fallback for development
    from core_engine.config.component_config import PositionLimits, RiskLimits, TimingConfig

# ============================================================================
# STRATEGY TYPE ENUM - Import from canonical source
# ============================================================================

# Import StrategyType from type_definitions (Single Source of Truth)
from core_engine.type_definitions.strategy import StrategyType

# StrategyType is now imported from type_definitions.strategy

# ============================================================================
# BASE STRATEGY CONFIG
# ============================================================================

@dataclass
class BaseStrategyConfig:
    """
    Base configuration for all strategies (using composition pattern)

    Provides common parameters using reusable sub-configs to eliminate duplication.
    """
    # Identity
    name: str = "strategy"
    """Strategy name"""

    strategy_id: Optional[str] = None
    """Strategy unique identifier. Default: Auto-generated"""

    strategy_type: Optional[StrategyType] = None
    """Strategy type"""

    # Composition - reuse common configs (DRY principle)
    position_limits: PositionLimits = field(default_factory=PositionLimits)
    """Position management limits"""

    risk_limits: RiskLimits = field(default_factory=RiskLimits)
    """Risk management limits"""

    timing: TimingConfig = field(default_factory=TimingConfig)
    """Timing and frequency configuration"""

    # Common strategy parameters
    symbols: List[str] = field(default_factory=lambda: ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'])
    """Symbols to trade. Default: Top 5 tech stocks"""

    profit_target_ratio: float = 2.0
    """Profit target as ratio of risk. Default: 2:1 risk/reward"""

    # Multi-timeframe
    enable_multi_timeframe: bool = False
    """Enable multi-timeframe analysis. Default: False"""

    primary_timeframe: str = '1min'
    """Primary timeframe. Default: '1min'"""

    secondary_timeframes: List[str] = field(default_factory=lambda: ['5min', '15min'])
    """Secondary timeframes. Default: ['5min', '15min']"""

    # Execution
    execution_timeout: float = 30.0
    """Execution timeout in seconds. Default: 30.0s"""

# ============================================================================
# HYBRID RECOMBINATION CONFIG (MOM/MR)
# ============================================================================

@dataclass
class HybridRecombinationConfig:
    """
    Hybrid MOM/MR recombination configuration.

    Controls regime-aware dynamic weighting, stability bounds, and
    statistical blending options for portfolio-layer signal recombination.
    """
    enable_hybrid_recombination: bool = False
    """Enable hybrid MOM/MR recombination. Default: False"""

    hybrid_only: bool = False
    """If True, emit only hybrid signal (suppress other signals). Default: False"""

    mom_base_weight: float = 0.5
    """Base MOM weight before adjustments. Default: 0.5"""

    mr_base_weight: float = 0.5
    """Base MR weight before adjustments. Default: 0.5"""

    weight_min: float = 0.2
    """Minimum weight per strategy. Default: 0.2"""

    weight_max: float = 0.8
    """Maximum weight per strategy. Default: 0.8"""

    weight_stability_threshold: float = 0.05
    """Minimum delta to rebalance weights. Default: 0.05"""

    conflict_penalty_factor: float = 0.5
    """Penalty factor for conflicting directions. Default: 0.5"""

    rolling_sharpe_window: int = 60
    """Lookback window (bars/days) for rolling Sharpe. Default: 60"""

    use_probabilistic_regime: bool = True
    """Use probabilistic regime weights. Default: True"""

    use_covariance_blend: bool = True
    """Enable covariance-aware blending when history sufficient. Default: True"""

    expected_holding_period_mom: int = 5
    """Expected holding period for MOM (bars). Default: 5"""

    expected_holding_period_mr: int = 2
    """Expected holding period for MR (bars). Default: 2"""

    regime_weight_map: Dict[str, Tuple[float, float]] = field(default_factory=lambda: {
        "trending": (0.7, 0.3),
        "range_bound": (0.3, 0.7),
        "volatile": (0.55, 0.45),
        "unknown": (0.5, 0.5)
    })
    """Regime to (MOM, MR) weight mapping. Default: balanced presets"""

    def __post_init__(self) -> None:
        if not 0.0 <= self.weight_min <= self.weight_max <= 1.0:
            raise ValueError("weight_min and weight_max must satisfy 0<=min<=max<=1")
        if not 0.0 <= self.mom_base_weight <= 1.0 or not 0.0 <= self.mr_base_weight <= 1.0:
            raise ValueError("mom_base_weight and mr_base_weight must be within [0,1]")
        if self.weight_stability_threshold < 0:
            raise ValueError("weight_stability_threshold must be >= 0")
        if self.rolling_sharpe_window <= 0:
            raise ValueError("rolling_sharpe_window must be > 0")
        if self.expected_holding_period_mom <= 0 or self.expected_holding_period_mr <= 0:
            raise ValueError("expected holding periods must be > 0")

# ============================================================================
# SPECIFIC STRATEGY CONFIGS
# ============================================================================

@dataclass
class MomentumConfig(BaseStrategyConfig):
    """
    Momentum strategy configuration

    Consolidated from: trading/strategies/implementations/momentum/enhanced_momentum.py
    Enhanced with all parameters for institutional-grade momentum trading.
    """
    strategy_type: StrategyType = StrategyType.MOMENTUM

    # State Machine (Professional re-architecture)
    enable_state_machine: bool = False
    """Enable stage-based state machine for entries/exits. Default: False"""

    orb_minutes: int = 15
    """Opening Range Breakout filter (ignore first N bars). Default: 15"""

    tightness_threshold: float = 0.75
    """Volatility tightness threshold (VCP). Default: 0.75"""

    max_extension_atr: float = 1.5
    """Maximum extension from anchor (in ATRs) to avoid chasing. Default: 1.5"""

    setup_expiry_bars: int = 10
    """Maximum bars a setup remains valid. Default: 10"""

    # Core momentum parameters
    lookback_period: int = 60
    """Momentum lookback period. Default: 60 bars"""

    short_period: int = 10
    """Short-term momentum period. Default: 10"""

    medium_period: int = 20
    """Medium-term momentum period. Default: 20"""

    long_period: int = 50
    """Long-term momentum period. Default: 50"""

    momentum_threshold: float = 0.02
    """Minimum momentum threshold. Default: 2%"""

    # Trend quality indicators
    rsi_period: int = 14
    """RSI period for momentum confirmation. Default: 14"""

    rsi_overbought: float = 70.0
    """RSI overbought level. Default: 70"""

    rsi_oversold: float = 30.0
    """RSI oversold level. Default: 30"""

    adx_period: int = 14
    """ADX period for trend strength. Default: 14"""

    adx_threshold: float = 25.0
    """Minimum ADX for trend confirmation. Default: 25"""

    # Volume confirmation
    volume_ma_period: int = 20
    """Volume moving average period. Default: 20"""

    volume_threshold: float = 1.2
    """Volume confirmation threshold. Default: 1.2x average"""

    # Transactions confirmation
    enable_transactions_confirm: bool = False
    """Enable transaction-based confirmation. Default: False"""

    txn_ratio_min: float = 1.1
    """Minimum txn_ratio for confirmation. Default: 1.1"""

    txn_rank_min: float = 0.7
    """Minimum txn_ratio_cs_rank for leader check. Default: 0.7"""

    avg_trade_size_ratio_max: float = 2.0
    """Max avg_trade_size_ratio before penalizing entries. Default: 2.0"""

    # Multi-timeframe analysis
    confirmation_timeframes: List[str] = field(default_factory=lambda: ["15min", "1h"])
    """Confirmation timeframes. Default: ['15min', '1h']"""

    # Position sizing (inherited from BaseStrategyConfig but can override)
    base_position_pct: float = 0.03
    """Base position size. Default: 3%"""

    max_position_pct: float = 0.08
    """Maximum position size. Default: 8%"""

    enable_regime_adaptive_sizing: bool = False
    """Enable sizing scaling based on continuous regime vector R. Default: False"""

    momentum_scaling: bool = True
    """Scale position by momentum strength. Default: True"""

    # Risk management
    momentum_stop_pct: float = 0.03
    """Stop loss percentage. Default: 3%"""

    trailing_stop_pct: float = 0.02
    """Trailing stop percentage. Default: 2%"""

    max_holding_period: int = 20
    """Maximum holding period in bars. Default: 20"""

    expected_holding_period_bars: int = 5
    """Expected holding period (for hybrid blending). Default: 5"""

    # Signal confidence
    min_signal_confidence: float = 0.30
    """Minimum signal confidence threshold. Default: 0.30 (lowered for composite signals)"""

    # Breakout detection
    enable_breakout_detection: bool = True
    """Enable breakout detection. Default: True"""

    breakout_lookback: int = 20
    """Lookback for breakout detection. Default: 20"""

    breakout_threshold: float = 0.02
    """Breakout threshold. Default: 2%"""

    # Position sizing multipliers (moved from hardcoded values)
    position_base_multiplier: float = 0.5
    """Base position multiplier for initial sizing. Default: 0.5"""

    momentum_multiplier_cap: float = 2.0
    """Maximum momentum multiplier for position scaling. Default: 2.0"""

    trend_multiplier_cap: float = 1.5
    """Maximum trend (ADX) multiplier for position scaling. Default: 1.5"""

    acceleration_scaling_factor: float = 10.0
    """Acceleration confidence scaling factor. Default: 10.0"""

    momentum_strength_weight_short: float = 0.5
    """Weight for short-term momentum in strength calculation. Default: 0.5"""

    momentum_strength_weight_medium: float = 0.3
    """Weight for medium-term momentum in strength calculation. Default: 0.3"""

    momentum_strength_weight_long: float = 0.2
    """Weight for long-term momentum in strength calculation. Default: 0.2"""

    trend_confidence_adx_multiplier: float = 1.5
    """ADX multiplier for trend confidence calculation. Default: 1.5"""

    momentum_threshold_low_multiplier: float = 0.5
    """Multiplier for low momentum threshold (exhaustion detection). Default: 0.5"""

    # Historical scanning mode (for backtesting)
    scan_all_bars: bool = False
    """Scan all bars in historical data when True (backtesting mode). Default: False (live mode - evaluates current bar only).
    Set to True for backtesting to scan entire historical dataset."""

    scan_interval: int = 1
    """Evaluate every N bars when scanning (1 = every bar, 5 = every 5 bars). Default: 1"""

    # Regime-adjusted thresholds
    enable_regime_adjusted_thresholds: bool = True
    """Enable regime-adjusted thresholds. Default: True"""

    regime_adjustment_factor: float = 0.8
    """Multiplier for thresholds in unfavorable regimes (0.8 = 20% reduction). Default: 0.8"""

    # ADS v3.1 SMS flow blend
    enable_txn_sms_flow_blend: bool = False
    """Enable txn_ratio blend in SMS flow support. Default: False"""

    txn_sms_flow_weight: float = 0.3
    """Txn ratio weight in SMS flow blend. Default: 0.3"""

    # ATR-based risk management (Exit Logic)
    atr_initial_stop_multiple: float = 1.8
    """ATR multiple for initial stop loss. Default: 1.8x ATR (hard stop to limit losses)"""

    atr_trailing_activation: float = 0.75
    """Profit in ATR multiples to activate trailing stop. Default: 0.75x ATR (lock in profits when position moves favorably)"""

    atr_trailing_distance: float = 0.8
    """Trailing stop distance in ATR multiples. Default: 0.8x ATR (protect profits while allowing breathing room)"""

    # Composite signal exits (Exit Logic)
    composite_z_exit: float = 0.7
    """Composite Z-score threshold to trigger exit. Default: 0.7 (momentum deterioration signal)"""

    composite_pct_exit: float = 55.0
    """Composite percentile threshold to trigger exit. Default: 55.0 (relative weakness signal)"""

    # Volume-based exits (Exit Logic)
    volume_failure_multiplier: float = 0.9
    """Volume ratio to trigger volume-failure exit. Default: 0.9x average (no follow-through)"""

    volume_failure_window: int = 20
    """Lookback window for volume failure check. Default: 20 bars"""

    # Time-based exits (Exit Logic)
    time_stop_minutes: int = 90
    """Maximum holding period in minutes. Default: 90 minutes (1.5 hours max hold)"""

    # Composite signal entry thresholds
    composite_z_entry: float = 0.5
    """Entry Z-score threshold for composite momentum signal. Default: 0.5 (requires moderate momentum strength for entry)."""

    composite_pct_entry: float = 70.0
    """Entry percentile threshold for composite momentum signal. Default: 70.0 (top 30% momentum required for entry).
    Format: 0-100 percentage scale (70.0 = 70th percentile)."""

    # Trend persistence filter (Entry Logic)
    enable_trend_persistence_filter: bool = False
    """Require recent return sign consistency before entry. Default: False"""

    trend_persistence_lookback: int = 10
    """Lookback bars for trend persistence check. Default: 10"""

    trend_persistence_min_ratio: float = 0.6
    """Minimum fraction of favorable return signs required. Default: 0.6"""

    # =====================================================================
    # ADS v3.1 (Core): SMS pending/stale + tau(R) + ERAR gate (strategy-side)
    # =====================================================================
    enable_ads_gates: bool = True
    """Enable ADS gates (SMS + ERAR) for momentum. Default: True"""

    sms_mode: str = "multiplicative"
    """SMS mode: 'multiplicative' or 'bayes_log_odds'. Default: 'multiplicative'"""

    sms_max_pending: int = 50
    """Maximum bars to keep a pending signal before stale-kill. Default: 50"""

    # Bayesian-lite SMS (hand-tuned bridge, no live ML inference)
    sms_min_info_to_mature: float = 0.5
    """Minimum information-time required before a pending signal is allowed to mature. Default: 0.5"""

    sms_max_info: float = 12.0
    """Maximum information-time before stale-kill. Default: 12.0"""

    sms_prior_p0: float = 0.55
    """Base prior probability used to initialize log-odds when signal first fires. Default: 0.55"""

    sms_prior_strength_coef: float = 0.10
    """How much to tilt the prior by raw_signal_strength. Default: 0.10"""

    sms_delay_penalty_per_bar: float = 0.02
    """Per-bar opportunity-cost penalty applied in log-odds space. Default: 0.02"""

    sms_w_setup_maturity: float = 1.10
    sms_w_setup_validity: float = 1.25
    sms_w_flow_support: float = 0.80
    sms_w_vol_compression: float = 0.60
    """Evidence weights (hand-tuned) for sequential log-odds updates."""

    sms_info_w_volume: float = 0.55
    sms_info_w_volatility: float = 0.45
    sms_info_cap: float = 3.0
    """Information-time clock weights/cap for event-time maturation."""

    tau_0: float = 0.50
    """Base SMS threshold used in tau(R) calculation. Default: 0.50"""

    erar_gamma: float = 0.5
    """Minimum ERAR threshold for trade. Default: 0.5"""

    spread_bps: float = 2.0
    """Assumed half-spread cost in basis points. Default: 2.0"""

    alt_return_bps: float = 0.5
    """Opportunity cost proxy in bps/day. Default: 0.5"""

    erar_tail_lambda: float = 1.0
    """Tail-risk penalty multiplier for ERAR CVaR term. Default: 1.0"""

    # =====================================================================
    # Transition Supervisor (Phase 1)
    # Gating layer that detects participant synchronisation phase changes.
    # Wraps existing SMS/ERAR pipeline — does NOT replace risk stack.
    # =====================================================================
    enable_transition_supervisor: bool = True
    """Enable Transition Supervisor gating on entry. Default: True"""

    transition_threshold: float = 0.15
    """Minimum transition_score required to allow entry.
    Score is multiplicative (coherence × accel × expansion × vov_gate).
    Lower = more permissive. Range recommendation: [0.05, 0.40].
    Default: 0.15 (moderate — allows entry when features weakly align)."""

    transition_threshold_strict: float = 0.30
    """Stricter threshold used in adverse regimes (high vol, low liq).
    Default: 0.30"""

    vov_block_threshold: float = 0.85
    """Vol-of-vol percentile above which entries are hard-blocked.
    Prevents entry during volatility mirages (pre-news, macro uncertainty).
    Default: 0.85 (top 15% vol instability)."""

    # --- VPIN / Flow Toxicity Gate (v3.2) ---
    # Easley-Lopez de Prado-O'Hara (2012) VPIN integration.
    # Three integration points:
    #   1. Transition Supervisor hard block (vpin_block_threshold)
    #   2. ERAR adverse_prob dynamic adjustment (vpin_adverse_sensitivity)
    #   3. SMS tau(R) hardening (vpin_tau_sensitivity)

    enable_vpin_gate: bool = True
    """Enable VPIN flow toxicity gating. Default: True"""

    vpin_block_threshold: float = 0.85
    """VPIN percentile above which entries are hard-blocked.
    Prevents entry during high informed-trading probability regimes.
    Default: 0.85 (top 15% toxicity)."""

    erar_base_adverse_prob: float = 0.10
    """Base adverse selection probability for ERAR cost model.
    Default: 0.10 (10% baseline)."""

    vpin_adverse_sensitivity: float = 0.40
    """Sensitivity of ERAR adverse_prob to VPIN percentile excess.
    adverse_prob = base + sensitivity × max(0, vpin_pct - 0.50).
    At vpin_pct=0.85: adverse_prob = 0.10 + 0.40×0.35 = 0.24.
    Default: 0.40."""

    vpin_tau_sensitivity: float = 0.15
    """Sensitivity of SMS tau(R) to VPIN percentile excess.
    Higher VPIN → higher maturity threshold → signals must bake longer.
    Default: 0.15."""

    # --- Microstructure Quality Score (MQS) v3.3 ---
    # Multiplicative quality score that combines multiple microstructure
    # signals into a single confidence penalty, rather than independent
    # hard blocks which over-kill due to feature overlap.
    # MQS = coherence_f × flow_alignment_f × liquidity_f
    # Applied as: confidence *= 1 - penalty_weight * (1 - MQS)

    enable_microstructure_quality: bool = True
    """Enable MQS-based confidence penalty for entries.
    Default: True."""

    bvc_hard_block: float = 0.15
    """Hard block BUY when buy_volume_pct < this (or SELL when sell_vol_pct < this).
    Only catches egregious contra-flow (Kyle 1985 adverse selection).
    Default: 0.15."""

    mqs_coherence_ref: float = 0.15
    """Reference coherence for MQS normalization. Coherence at this value -> factor=1.0.
    Calibrated to 1-min bar data where typical coherence is 0.01-0.20.
    Default: 0.15."""

    mqs_bvc_ref: float = 0.45
    """Reference aligned BVC pct for MQS normalization.
    Default: 0.45."""

    mqs_vol_floor: float = -0.50
    """Normalized volume_ratio at which liquidity factor hits 0.
    volume_ratio is centered at 0 (negative = below average).
    -0.50 means 50% below average volume → zero liquidity score.
    Default: -0.50."""

    mqs_vol_range: float = 0.50
    """Range from vol_floor over which liquidity factor goes 0→1.
    With floor=-0.50, range=0.50: liquidity_f=1.0 at volume_ratio>=0.
    Default: 0.50."""

    mqs_penalty_weight: float = 0.25
    """Maximum fraction of confidence removed by MQS.
    0.25 means perfect microstructure (MQS=1) -> no penalty,
    worst microstructure (MQS=0) -> 25% confidence reduction.
    Gentle to avoid killing all signals in low-coherence regimes.
    Default: 0.25."""

    # --- Transition Lifecycle Exit Model ---
    # Replaces the single coherence_decay threshold with a multi-dimensional
    # transition health framework that mirrors entry logic.

    health_critical_threshold: float = 0.15
    """Transition health below this → TRANSITION_EXHAUSTION exit.
    Health = accel_health × coherence_health × vov_health.
    Range recommendation: [0.05, 0.30]. Default: 0.15"""

    accel_exhaustion_threshold: float = -0.3
    """Signed acceleration (in entry direction) below this triggers
    TRANSITION_TAKE_PROFIT when in profit.  Detects wave cresting.
    Range: [-0.8, -0.1]. Default: -0.3"""

    tp_initial_pct: float = 2.0
    """Dynamic take-profit initial target (percent).
    TP(t) = tp_initial * exp(-t/tp_decay_minutes) + tp_floor.
    Default: 2.0%"""

    tp_floor_pct: float = 0.3
    """Dynamic take-profit floor (percent).  The minimum TP target
    as time progresses.  Default: 0.3%"""

    tp_decay_minutes: float = 30.0
    """Time constant (minutes) for TP target decay.
    Default: 30.0 (TP halves roughly every 21 minutes)."""

    health_tp_trigger: float = 0.7
    """Health must be below this fraction for dynamic TP to fire.
    Prevents premature profit-taking when thesis is still strong.
    Default: 0.7"""

    transition_pending_stale_bars: int = 15
    """Max bars to keep a pending signal waiting for transition confirmation.
    Shorter than SMS stale-kill (50) because transitions are ephemeral.
    Default: 15"""

    # --- Causal Entry Chain (priority-based entry timing) ---
    enable_causal_entry_chain: bool = True
    """Enable strict causal-chain scoring for entry timing. Default: True"""

    min_alignment_score: float = 0.55
    """Minimum L1 alignment score required. Default: 0.55"""

    min_trigger_score: float = 0.55
    """Minimum L2 trigger score required. Default: 0.55"""

    min_confirmation_score: float = 0.55
    """Minimum L3 confirmation score required. Default: 0.55"""

    entry_score_threshold: float = 0.62
    """Minimum overall causal-chain score required for entry. Default: 0.62"""

    trigger_slope_ref: float = 0.0025
    """Reference slope used to normalize trigger momentum slope score. Default: 0.0025"""

    trigger_inflection_bonus: float = 0.10
    """Bonus added to L2 trigger score on matching inflection. Default: 0.10"""

    # --- Expected return estimation from causal chain ---
    expected_return_base_bps: float = 12.0
    """Base expected return (bps) for valid entries. Default: 12.0"""

    expected_return_max_bps: float = 80.0
    """Maximum expected return (bps) cap. Default: 80.0"""

    expected_return_alignment_weight: float = 0.20
    """Weight of L1 alignment in expected return estimate. Default: 0.20"""

    expected_return_trigger_weight: float = 0.45
    """Weight of L2 trigger in expected return estimate. Default: 0.45"""

    expected_return_confirmation_weight: float = 0.35
    """Weight of L3 confirmation in expected return estimate. Default: 0.35"""

    def __post_init__(self):
        """Validate momentum configuration parameters"""
        if self.lookback_period <= 0:
            raise ValueError(f"lookback_period must be positive, got {self.lookback_period}")
        if self.rsi_period <= 0:
            raise ValueError(f"rsi_period must be positive, got {self.rsi_period}")
        if self.adx_period <= 0:
            raise ValueError(f"adx_period must be positive, got {self.adx_period}")
        if not 0 < self.momentum_threshold <= 1.0:
            raise ValueError(f"momentum_threshold must be (0, 1.0], got {self.momentum_threshold}")
        if not 0 < self.position_base_multiplier <= 1.0:
            raise ValueError(f"position_base_multiplier must be (0, 1.0], got {self.position_base_multiplier}")
        if not 0 < self.momentum_multiplier_cap <= 5.0:
            raise ValueError(f"momentum_multiplier_cap must be (0, 5.0], got {self.momentum_multiplier_cap}")

        # Validate exit logic parameters
        if self.atr_initial_stop_multiple <= 0:
            raise ValueError(f"atr_initial_stop_multiple must be positive, got {self.atr_initial_stop_multiple}")
        if self.atr_trailing_activation <= 0:
            raise ValueError(f"atr_trailing_activation must be positive, got {self.atr_trailing_activation}")
        if self.atr_trailing_distance <= 0:
            raise ValueError(f"atr_trailing_distance must be positive, got {self.atr_trailing_distance}")
        if self.composite_z_exit < 0:
            raise ValueError(f"composite_z_exit must be non-negative, got {self.composite_z_exit}")
        if not 0 <= self.composite_pct_exit <= 100:
            raise ValueError(f"composite_pct_exit must be [0, 100], got {self.composite_pct_exit}")
        if self.volume_failure_multiplier <= 0:
            raise ValueError(f"volume_failure_multiplier must be positive, got {self.volume_failure_multiplier}")
        if self.volume_failure_window <= 0:
            raise ValueError(f"volume_failure_window must be positive, got {self.volume_failure_window}")
        if self.time_stop_minutes <= 0:
            raise ValueError(f"time_stop_minutes must be positive, got {self.time_stop_minutes}")

        # Validate entry logic parameters
        if self.composite_z_entry < 0:
            raise ValueError(f"composite_z_entry must be non-negative, got {self.composite_z_entry}")
        if not 0 <= self.composite_pct_entry <= 100:
            raise ValueError(f"composite_pct_entry must be [0, 100], got {self.composite_pct_entry}")
        if self.trend_persistence_lookback <= 1:
            raise ValueError(f"trend_persistence_lookback must be > 1, got {self.trend_persistence_lookback}")
        if not 0.0 <= self.trend_persistence_min_ratio <= 1.0:
            raise ValueError(f"trend_persistence_min_ratio must be [0, 1], got {self.trend_persistence_min_ratio}")

        if self.sms_max_pending <= 0:
            raise ValueError(f"sms_max_pending must be positive, got {self.sms_max_pending}")
        if str(self.sms_mode).lower() not in {"multiplicative", "bayes", "bayes_log_odds", "log_odds", "sequential_log_odds"}:
            raise ValueError(f"sms_mode must be 'multiplicative' or 'bayes_log_odds', got {self.sms_mode!r}")
        if self.sms_min_info_to_mature < 0:
            raise ValueError(f"sms_min_info_to_mature must be >= 0, got {self.sms_min_info_to_mature}")
        if self.sms_max_info <= 0:
            raise ValueError(f"sms_max_info must be > 0, got {self.sms_max_info}")
        if not 0.0 < self.sms_prior_p0 < 1.0:
            raise ValueError(f"sms_prior_p0 must be (0, 1), got {self.sms_prior_p0}")
        if self.sms_delay_penalty_per_bar < 0:
            raise ValueError(f"sms_delay_penalty_per_bar must be >= 0, got {self.sms_delay_penalty_per_bar}")
        if self.sms_info_w_volume < 0 or self.sms_info_w_volatility < 0:
            raise ValueError("sms_info_w_volume and sms_info_w_volatility must be >= 0")
        if self.sms_info_cap <= 0:
            raise ValueError(f"sms_info_cap must be > 0, got {self.sms_info_cap}")
        if not 0.0 < self.tau_0 <= 1.0:
            raise ValueError(f"tau_0 must be (0, 1.0], got {self.tau_0}")
        if self.spread_bps < 0:
            raise ValueError(f"spread_bps must be >= 0, got {self.spread_bps}")
        if self.erar_gamma < 0:
            raise ValueError(f"erar_gamma must be >= 0, got {self.erar_gamma}")
        if self.erar_tail_lambda < 0:
            raise ValueError(f"erar_tail_lambda must be >= 0, got {self.erar_tail_lambda}")

        # Transition Supervisor validation
        if not 0.0 <= self.transition_threshold <= 1.0:
            raise ValueError(f"transition_threshold must be [0, 1], got {self.transition_threshold}")
        if not 0.0 <= self.transition_threshold_strict <= 1.0:
            raise ValueError(f"transition_threshold_strict must be [0, 1], got {self.transition_threshold_strict}")
        if not 0.0 <= self.vov_block_threshold <= 1.0:
            raise ValueError(f"vov_block_threshold must be [0, 1], got {self.vov_block_threshold}")
        if not 0.0 <= self.vpin_block_threshold <= 1.0:
            raise ValueError(f"vpin_block_threshold must be [0, 1], got {self.vpin_block_threshold}")
        if self.erar_base_adverse_prob < 0 or self.erar_base_adverse_prob > 1.0:
            raise ValueError(f"erar_base_adverse_prob must be [0, 1], got {self.erar_base_adverse_prob}")
        if self.vpin_adverse_sensitivity < 0:
            raise ValueError(f"vpin_adverse_sensitivity must be >= 0, got {self.vpin_adverse_sensitivity}")
        if self.vpin_tau_sensitivity < 0:
            raise ValueError(f"vpin_tau_sensitivity must be >= 0, got {self.vpin_tau_sensitivity}")
        if not 0.0 <= self.bvc_hard_block <= 0.50:
            raise ValueError(f"bvc_hard_block must be [0, 0.50], got {self.bvc_hard_block}")
        if self.mqs_coherence_ref <= 0:
            raise ValueError(f"mqs_coherence_ref must be > 0, got {self.mqs_coherence_ref}")
        if self.mqs_bvc_ref <= 0:
            raise ValueError(f"mqs_bvc_ref must be > 0, got {self.mqs_bvc_ref}")
        if self.mqs_vol_range <= 0:
            raise ValueError(f"mqs_vol_range must be > 0, got {self.mqs_vol_range}")
        if not 0.0 <= self.mqs_penalty_weight <= 1.0:
            raise ValueError(f"mqs_penalty_weight must be [0, 1], got {self.mqs_penalty_weight}")
        if not 0.0 < self.health_critical_threshold <= 1.0:
            raise ValueError(f"health_critical_threshold must be (0, 1], got {self.health_critical_threshold}")
        if not -1.0 <= self.accel_exhaustion_threshold <= 0.0:
            raise ValueError(f"accel_exhaustion_threshold must be [-1, 0], got {self.accel_exhaustion_threshold}")
        if self.tp_initial_pct < 0:
            raise ValueError(f"tp_initial_pct must be >= 0, got {self.tp_initial_pct}")
        if self.tp_floor_pct < 0:
            raise ValueError(f"tp_floor_pct must be >= 0, got {self.tp_floor_pct}")
        if self.tp_decay_minutes <= 0:
            raise ValueError(f"tp_decay_minutes must be > 0, got {self.tp_decay_minutes}")
        if not 0.0 < self.health_tp_trigger <= 1.0:
            raise ValueError(f"health_tp_trigger must be (0, 1], got {self.health_tp_trigger}")
        if self.transition_pending_stale_bars <= 0:
            raise ValueError(f"transition_pending_stale_bars must be > 0, got {self.transition_pending_stale_bars}")
        if not 0.0 <= self.min_alignment_score <= 1.0:
            raise ValueError(f"min_alignment_score must be [0, 1], got {self.min_alignment_score}")
        if not 0.0 <= self.min_trigger_score <= 1.0:
            raise ValueError(f"min_trigger_score must be [0, 1], got {self.min_trigger_score}")
        if not 0.0 <= self.min_confirmation_score <= 1.0:
            raise ValueError(f"min_confirmation_score must be [0, 1], got {self.min_confirmation_score}")
        if not 0.0 <= self.entry_score_threshold <= 1.0:
            raise ValueError(f"entry_score_threshold must be [0, 1], got {self.entry_score_threshold}")
        if self.trigger_slope_ref <= 0:
            raise ValueError(f"trigger_slope_ref must be > 0, got {self.trigger_slope_ref}")
        if self.trigger_inflection_bonus < 0:
            raise ValueError(f"trigger_inflection_bonus must be >= 0, got {self.trigger_inflection_bonus}")
        if self.expected_return_base_bps < 0:
            raise ValueError(f"expected_return_base_bps must be >= 0, got {self.expected_return_base_bps}")
        if self.expected_return_max_bps <= 0:
            raise ValueError(f"expected_return_max_bps must be > 0, got {self.expected_return_max_bps}")
        if self.expected_return_max_bps < self.expected_return_base_bps:
            raise ValueError(
                f"expected_return_max_bps must be >= expected_return_base_bps, "
                f"got {self.expected_return_max_bps} < {self.expected_return_base_bps}"
            )
        if self.expected_return_alignment_weight < 0 or self.expected_return_trigger_weight < 0 or self.expected_return_confirmation_weight < 0:
            raise ValueError("expected_return_*_weight values must be >= 0")

@dataclass
class MeanReversionConfig(BaseStrategyConfig):
    """
    Mean reversion strategy configuration

    Consolidated from: trading/strategies/implementations/mean_reversion/enhanced_mean_reversion.py
    Enhanced with all parameters for institutional-grade mean reversion trading.
    """
    strategy_type: StrategyType = StrategyType.MEAN_REVERSION

    # Mean reversion parameters
    lookback_period: int = 20
    """Lookback for mean calculation. Default: 20 bars"""

    zscore_entry_threshold: float = 2.0
    """Z-score for entry. Default: 2.0 std devs"""

    zscore_exit_threshold: float = 0.5
    """Z-score for exit. Default: 0.5 std devs"""

    # Technical indicators
    bollinger_period: int = 20
    """Bollinger Bands period. Default: 20"""

    bollinger_std: float = 2.0
    """Bollinger Bands standard deviation. Default: 2.0"""

    rsi_period: int = 14
    """RSI period. Default: 14"""

    rsi_oversold: float = 30.0
    """RSI oversold threshold. Default: 30"""

    rsi_overbought: float = 70.0
    """RSI overbought threshold. Default: 70"""

    # Multi-timeframe analysis
    confirmation_timeframe: str = "15min"
    """Confirmation timeframe. Default: '15min'"""

    # Position sizing
    atr_period: int = 14
    """ATR period for volatility. Default: 14"""

    base_position_pct: float = 0.02
    """Base position size. Default: 2%"""

    max_position_pct: float = 0.05
    """Maximum position size. Default: 5%"""

    volatility_target: float = 0.15
    """Target volatility. Default: 15%"""

    # Risk management
    stop_loss_atr_multiple: float = 2.0
    """Stop loss as multiple of ATR. Default: 2.0"""

    max_holding_period: int = 10
    """Maximum holding period in bars. Default: 10"""

    expected_holding_period_bars: int = 2
    """Expected holding period (for hybrid blending). Default: 2"""

    # Price-aware exit parameters (NEW)
    stop_loss_pct: float = -5.0
    """Stop loss percentage. Exit if unrealized P&L drops below this. Default: -5%"""

    take_profit_pct: float = 10.0
    """Take profit percentage. Exit if unrealized P&L exceeds this. Default: +10%"""

    enable_fixed_take_profit: bool = False
    """Enable fixed take-profit exits (legacy). Default: False (ADS v3.1 prefers dynamic/multi-exit)."""

    min_profit_to_exit: float = -2.0
    """Minimum P&L % to allow z-score based exit. Prevents selling at big loss. Default: -2%"""

    # Momentum-aware exit parameters (NEW)
    enable_momentum_exit: bool = True
    """Enable momentum-aware exit logic. Default: True"""

    momentum_adx_threshold: float = 20.0
    """ADX threshold for trend strength. If ADX < this, trend is weak → OK to exit. Default: 20"""

    momentum_rsi_overbought: float = 70.0
    """RSI overbought threshold. If RSI > this, momentum exhausted → OK to exit. Default: 70"""

    momentum_rsi_oversold: float = 30.0
    """RSI oversold threshold. If RSI < this, momentum exhausted → OK to exit. Default: 30"""

    momentum_volume_ratio: float = 0.7
    """Volume ratio threshold. If volume < avg * ratio, momentum fading → OK to exit. Default: 0.7"""

    momentum_extended_zscore: float = 3.0
    """Extended z-score threshold. Always exit if |z| > this regardless of momentum. Default: 3.0"""

    # Volume climax detection (NEW)
    volume_climax_threshold: float = 2.5
    """Volume ratio threshold for climax detection. Default: 2.5"""

    volume_climax_price_threshold: float = 0.5
    """Price change % threshold for climax detection. Default: 0.5%"""

    # Transaction exhaustion (NEW)
    enable_transactions_exhaustion: bool = False
    """Enable transaction-based exhaustion signals. Default: False"""

    txn_spike_threshold: float = 1.5
    """Txn ratio threshold for exhaustion spikes. Default: 1.5"""

    txn_climax_threshold: float = 2.0
    """Txn ratio threshold for climax validation. Default: 2.0"""

    # Momentum-aware entry parameters (NEW)
    enable_momentum_entry: bool = True
    """Enable momentum-aware entry logic. Prevents buying into falling knives. Default: True"""

    extended_zscore_entry_threshold: float = -3.0
    """Z-score threshold for guaranteed entry. Always enter if z <= this. Default: -3.0"""

    momentum_volume_ratio_threshold: float = 0.7
    """Volume ratio threshold for entry/exit decisions. Default: 0.7"""

    # Regime filtering
    enable_regime_filter: bool = True
    """Enable regime filtering. Default: True"""

    min_trend_strength: float = 0.3
    """Minimum trend strength for filtering. Default: 0.3"""

    volatility_regime_threshold: float = 0.02
    """Volatility threshold. Default: 0.02"""

    # Confidence parameters (moved from hardcoded values)
    regime_confidence_favorable: float = 0.8
    """Regime confidence when regime is favorable. Default: 0.8"""

    regime_confidence_unfavorable: float = 0.3
    """Regime confidence when regime is unfavorable. Default: 0.3"""

    # Confidence weighting (for signal confidence calculation)
    confidence_weight_zscore: float = 0.4
    """Weight for z-score confidence. Default: 0.4"""

    confidence_weight_rsi: float = 0.3
    """Weight for RSI confidence. Default: 0.3"""

    confidence_weight_bollinger: float = 0.2
    """Weight for Bollinger Band confidence. Default: 0.2"""

    confidence_weight_regime: float = 0.1
    """Weight for regime confidence. Default: 0.1"""

    # Historical scanning mode (for backtesting)
    scan_all_bars: bool = False
    """Scan all bars in historical data (for backtesting). Default: False (live mode - current bar only)"""

    scan_interval: int = 1
    """Evaluate every N bars when scanning (1 = every bar, 5 = every 5 bars). Default: 1"""

    # Regime-adjusted thresholds
    enable_regime_adjusted_thresholds: bool = True
    """Enable regime-adjusted thresholds. Default: True"""

    regime_adjustment_factor: float = 0.85
    """Multiplier for thresholds in unfavorable regimes (0.85 = 15% reduction). Default: 0.85"""

    min_signal_confidence: float = 0.85
    """Minimum signal confidence threshold for strategy-level filtering. Default: 0.85"""

    # ADS v3.1 SMS flow blend
    enable_txn_sms_flow_blend: bool = False
    """Enable txn_ratio blend in SMS flow support. Default: False"""

    txn_sms_flow_weight: float = 0.3
    """Txn ratio weight in SMS flow blend. Default: 0.3"""

    # =========================================
    # EXHAUSTION-BASED SCORING SYSTEM (v3.0)
    # =========================================
    # Based on professional quant alpha logic:
    # "Mean reversion works when directional moves show exhaustion"

    # Score thresholds for signal generation
    exhaustion_score_strong: float = 70.0
    """Score threshold for strong signals (high confidence). Default: 70"""

    exhaustion_score_moderate: float = 60.0
    """Score threshold for moderate signals (lower confidence). Default: 60"""

    # Factor weights for exhaustion scoring
    weight_dislocation: float = 0.25
    """Weight for dislocation factor (distance from fair value). Default: 0.25"""

    weight_exhaustion: float = 0.30
    """Weight for exhaustion signals (RSI momentum, volume, MACD). Default: 0.30"""

    weight_candle_structure: float = 0.15
    """Weight for candle structure (wick rejection, body size). Default: 0.15"""

    weight_regime_penalty: float = 0.15
    """Weight for regime penalty (ADX, volatility, breakout). Default: 0.15"""

    weight_confluence: float = 0.15
    """Weight for supporting indicator confluence. Default: 0.15"""

    weight_txn_exhaustion: float = 0.10
    """Weight for transaction exhaustion factor. Default: 0.10"""

    # Dislocation thresholds
    dislocation_strong: float = 2.0
    """Z-score for strong dislocation signal. Default: 2.0"""

    dislocation_moderate: float = 1.5
    """Z-score for moderate dislocation signal. Default: 1.5"""

    dislocation_minimum: float = 1.0
    """Minimum z-score to consider (below = no trade). Default: 1.0"""

    # Exhaustion signal thresholds
    volume_exhaustion_threshold: float = 1.0
    """Volume ratio below which move is considered 'weak' (noise). Default: 1.0"""

    volume_conviction_threshold: float = 2.0
    """Volume ratio above which move is considered 'conviction' (don't fade). Default: 2.0"""

    # Candle structure thresholds
    wick_rejection_threshold: float = 0.4
    """Wick ratio (vs range) for rejection signal. Default: 0.4 (40%)"""

    doji_body_threshold: float = 0.003
    """Body size (vs price) for doji detection. Default: 0.003 (0.3%)"""

    # Regime penalty thresholds
    adx_strong_trend: float = 30.0
    """ADX level indicating strong trend (penalize mean reversion). Default: 30"""

    adx_moderate_trend: float = 25.0
    """ADX level indicating moderate trend. Default: 25"""

    volatility_spike_threshold: float = 2.0
    """Volatility ratio above which to penalize. Default: 2.0"""

    # =========================================
    # v4.0 PROFESSIONAL QUANT ALPHA PARAMETERS
    # =========================================
    # Advanced statistical methods for alpha validation

    enable_alpha_quality_scoring: bool = True
    """Enable v4.0 alpha quality scoring (half-life, Hurst, EWMA). Default: True"""

    weight_alpha_quality: float = 0.10
    """Weight for alpha quality factor in scoring. Default: 0.10 (10%)"""

    # Half-life parameters (Ornstein-Uhlenbeck)
    half_life_min: float = 3.0
    """Minimum acceptable half-life in bars. Default: 3"""

    half_life_max: float = 50.0
    """Maximum acceptable half-life in bars. Default: 50"""

    half_life_ideal_min: float = 5.0
    """Ideal half-life lower bound. Default: 5"""

    half_life_ideal_max: float = 20.0
    """Ideal half-life upper bound. Default: 20"""

    # Hurst exponent parameters
    hurst_mean_reverting_threshold: float = 0.5
    """Hurst exponent threshold for mean-reversion. H < this = mean-reverting. Default: 0.5"""

    hurst_strong_mr_threshold: float = 0.4
    """Hurst exponent for strong mean-reversion. Default: 0.4"""

    hurst_trending_threshold: float = 0.55
    """Hurst exponent above which is considered trending (avoid). Default: 0.55"""

    # EWMA z-score parameters
    ewma_span: int = 20
    """EWMA span for z-score calculation. Default: 20"""

    ewma_min_periods: int = 10
    """Minimum periods for valid EWMA. Default: 10"""

    # Volatility adjustment parameters
    vol_adj_lookback: int = 60
    """Lookback for historical volatility comparison. Default: 60"""

    vol_adj_min_multiplier: float = 0.7
    """Minimum threshold adjustment multiplier. Default: 0.7"""

    vol_adj_max_multiplier: float = 1.5
    """Maximum threshold adjustment multiplier. Default: 1.5"""

    # =========================================
    # ADS v3.0 COMPLIANCE PARAMETERS
    # =========================================
    # Per alpha_design_philosophy.mdc (Critical fixes)

    # §1: Signal Maturity Score (SMS)
    enable_ads_gates: bool = True
    """Enable ADS v3.0 SMS and ERAR gates. Default: True"""

    sms_threshold: float = 0.5
    """Minimum SMS score to consider signal mature. Default: 0.5
    SMS uses multiplicative formula: E^α × P_rev^β × (1+ΔOFI)^γ × VC^(-δ) × e^(-λt)"""

    # ADS v3.1: dynamic SMS threshold base (tau(R))
    tau_0: float = 0.50
    """Base SMS threshold for ADS v3.1 tau(R) computation. Default: 0.50
    tau = clip(tau0 + 0.15*R_vol + 0.10*(1-R_liq) + 0.10*(1-Conf), 0.35, 0.80)"""

    sms_max_pending: int = 50
    """Maximum bars a signal can be pending before considered stale. Default: 50"""

    # §3: Expected Risk-Adjusted Return (ERAR)
    erar_gamma: float = 0.5
    """Minimum ERAR threshold for trade. Default: 0.5
    ERAR = (E[PnL] - λ × CVaR95) / Cost × Ω_adj ≥ gamma"""

    spread_bps: float = 2.0
    """Assumed spread cost in basis points. Default: 2.0"""

    # §8: Cooldown (PVSI)
    pvsi_threshold: float = 2.0
    """PVSI threshold to trigger cooldown. Default: 2.0"""

    pvsi_cooldown_bars: int = 50
    """Bars to wait during cooldown. Default: 50"""

    # Backward compatibility aliases
    @property
    def entry_zscore_threshold(self) -> float:
        """Alias for zscore_entry_threshold"""
        return self.zscore_entry_threshold

    @property
    def exit_zscore_threshold(self) -> float:
        """Alias for zscore_exit_threshold"""
        return self.zscore_exit_threshold

@dataclass
class StatisticalArbitrageConfig(BaseStrategyConfig):
    """
    Statistical arbitrage strategy configuration

    Consolidated from: trading/strategies/implementations/statistical_arbitrage/enhanced_statistical_arbitrage.py
    """
    strategy_type: StrategyType = StrategyType.STATISTICAL_ARBITRAGE

    # Cointegration parameters
    cointegration_lookback: int = 252
    """Cointegration lookback period. Default: 252 days (1 year)"""

    cointegration_threshold: float = 0.05
    """Cointegration p-value threshold. Default: 0.05"""

    min_correlation: float = 0.7
    """Minimum correlation for pair selection. Default: 0.7"""

    # Entry/exit
    entry_zscore_threshold: float = 2.0
    """Entry z-score threshold. Default: 2.0"""

    exit_zscore_threshold: float = 0.5
    """Exit z-score threshold. Default: 0.5"""

    stop_loss_zscore: float = 3.5
    """Stop loss z-score threshold. Default: 3.5"""

    # Position sizing
    max_spread_positions: int = 5
    """Maximum concurrent spread positions. Default: 5"""

    position_size_method: str = "risk_parity"
    """Position sizing method ('fixed', 'volatility_adjusted', 'risk_parity'). Default: 'risk_parity'"""

    base_position_size: float = 0.02
    """Base position size as fraction of portfolio. Default: 0.02"""

    # Risk management
    max_holding_period: int = 20
    """Maximum days to hold position. Default: 20"""

    # Rebalancing
    rebalance_frequency: str = 'daily'
    """Rebalance frequency. Default: 'daily'"""

    hedge_ratio_method: str = 'ols'
    """Hedge ratio calculation method ('ols', 'tls'). Default: 'ols'"""

    # Model parameters
    kalman_filter_enabled: bool = True
    """Use Kalman filter for hedge ratios. Default: True"""

    ou_process_modeling: bool = True
    """Ornstein-Uhlenbeck process modeling. Default: True"""

    error_correction_model: bool = True
    """Use ECM for spread dynamics. Default: True"""

    # Asset universe
    asset_universe: List[str] = field(default_factory=lambda: [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX'
    ])
    """Asset universe for statistical arbitrage. Default: Major tech stocks"""

    # Position sizing parameters (moved from hardcoded values)
    min_intraday_bars: int = 20
    """Minimum bars required for intraday statistics. Default: 20"""

    target_volatility: float = 0.15
    """Target volatility for volatility-adjusted position sizing. Default: 0.15 (15%)"""

    min_volatility_floor: float = 0.05
    """Minimum volatility floor for position sizing calculations. Default: 0.05 (5%)"""

    target_risk_per_position: float = 0.02
    """Target risk per position for risk parity sizing. Default: 0.02 (2%)"""

@dataclass
class FactorConfig(BaseStrategyConfig):
    """
    Factor strategy configuration

    Consolidated from: trading/strategies/implementations/factor/enhanced_factor.py
    """
    strategy_type: StrategyType = StrategyType.FACTOR

    # Factor parameters
    factors: List[str] = field(default_factory=lambda: ['momentum', 'value', 'quality', 'size'])
    """Factors to use. Default: ['momentum', 'value', 'quality', 'size']"""

    factor_weights: Dict[str, float] = field(default_factory=lambda: {
        'momentum': 0.3, 'value': 0.3, 'quality': 0.2, 'size': 0.2
    })
    """Factor weights. Default: Equal-ish weighting"""

    rebalance_frequency: int = 20
    """Rebalance every N days. Default: 20 days"""

    factor_lookback: int = 60
    """Factor calculation lookback. Default: 60 days"""

    min_factor_score: float = 0.5
    """Minimum composite factor score. Default: 0.5"""

    # Additional parameters from local config
    base_position_pct: float = 0.02
    """Base position size. Default: 0.02 (2%)"""

    max_position_pct: float = 0.06
    """Maximum position size. Default: 0.06 (6%)"""

@dataclass
class MultiAssetConfig(BaseStrategyConfig):
    """
    Multi-asset strategy configuration

    Consolidated from: trading/strategies/implementations/multi_asset/enhanced_multi_asset.py
    """
    strategy_type: StrategyType = StrategyType.MULTI_ASSET

    # Asset allocation
    # Note: asset_classes is a Dict mapping class names to symbol lists (from local config merge)
    # The original List[str] version is replaced by this Dict for more flexibility
    asset_classes: Dict[str, List[str]] = field(default_factory=lambda: {
        'equities': [],  # Can be populated with equity symbols
        'bonds': [],     # Can be populated with bond symbols
        'commodities': [],  # Can be populated with commodity symbols
        'tech': ['AAPL', 'MSFT', 'GOOGL'],
        'growth': ['AMZN', 'TSLA', 'NVDA'],
        'value': ['BRK.B', 'JPM', 'JNJ']
    })
    """Asset classes with their symbols. Default: Tech, Growth, Value + standard classes"""

    target_allocations: Dict[str, float] = field(default_factory=lambda: {
        'equities': 0.6, 'bonds': 0.3, 'commodities': 0.1
    })
    """Target allocations. Default: 60/30/10"""

    rebalance_frequency: int = 10
    """Rebalance every N days. Default: 10 days"""

    rebalance_threshold: float = 0.05
    """Rebalance if drift exceeds threshold. Default: 5%"""

    correlation_lookback: int = 60
    """Correlation calculation lookback. Default: 60 days"""

    # Additional parameters from local config
    max_correlation: float = 0.8
    """Maximum correlation threshold. Default: 0.8"""

    portfolio_vol_target: float = 0.12
    """Target portfolio volatility (12%). Default: 0.12"""

    max_asset_weight: float = 0.3
    """Maximum weight per asset (30%). Default: 0.3"""

    min_asset_weight: float = 0.05
    """Minimum weight per asset (5%). Default: 0.05"""

    equal_weight_baseline: bool = True
    """Start with equal weights. Default: True"""

@dataclass
class PairsConfig(BaseStrategyConfig):
    """
    Pairs trading strategy configuration

    Consolidated from: trading/strategies/implementations/pairs_trading/enhanced_pairs_trading.py
    """
    strategy_type: StrategyType = StrategyType.PAIRS_TRADING

    # Pairs selection
    lookback_period: int = 252
    """Lookback for pair selection. Default: 252 days (1 year)"""

    correlation_threshold: float = 0.5
    """Minimum correlation to maintain pair. Default: 0.5"""

    cointegration_threshold: float = 0.05
    """Cointegration p-value threshold. Default: 0.05"""

    # Entry/exit
    entry_zscore_threshold: float = 2.0
    """Entry z-score threshold. Default: 2.0"""

    exit_zscore_threshold: float = 0.5
    """Exit z-score threshold. Default: 0.5"""

    # Pair management
    max_pairs: int = 5
    """Maximum concurrent pairs. Default: 5"""

    pair_reselection_frequency: int = 20
    """Reselect pairs every N days. Default: 20 days"""

    # Additional parameters from local config
    min_correlation: float = 0.7
    """Minimum correlation for pair selection. Default: 0.7"""

    entry_zscore: float = 2.0
    """Entry z-score threshold (alias for entry_zscore_threshold). Default: 2.0"""

    exit_zscore: float = 0.5
    """Exit z-score threshold (alias for exit_zscore_threshold). Default: 0.5"""

    stop_loss_zscore: float = 3.5
    """Stop loss Z-score. Default: 3.5"""

    position_size_pct: float = 0.02
    """Position size per pair. Default: 0.02 (2%)"""

    max_holding_period: int = 30
    """Maximum holding period in days. Default: 30"""

    # Asset universe (required for pair selection)
    asset_universe: List[str] = field(default_factory=lambda: [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX'
    ])
    """Asset universe for pairs trading. Default: Major tech stocks"""

    # SES (Spread Exhaustion Scoring) thresholds
    ses_entry_threshold: float = 65.0
    """Minimum SES score for entry. Default: 65.0"""

    ses_high_confidence_threshold: float = 80.0
    """SES threshold for high confidence entries. Default: 80.0"""

@dataclass
class VolatilityConfig(BaseStrategyConfig):
    """
    Volatility strategy configuration

    Consolidated from: trading/strategies/implementations/volatility/enhanced_volatility.py
    """
    strategy_type: StrategyType = StrategyType.VOLATILITY

    # Volatility parameters
    volatility_lookback: int = 20
    """Volatility calculation period. Default: 20 bars"""

    volatility_threshold: float = 0.02
    """Volatility threshold (2%). Default: 2%"""

    regime_detection: bool = True
    """Enable volatility regime detection. Default: True"""

    # Position sizing
    base_position_pct: float = 0.025
    """Base position size (2.5%). Default: 2.5%"""

    max_position_pct: float = 0.07
    """Maximum position size (7%). Default: 7%"""

    volatility_scaling: bool = True
    """Scale positions by volatility. Default: True"""

    # Risk management
    vol_target: float = 0.15
    """Target portfolio volatility (15%). Default: 15%"""

@dataclass
class ArbitrageConfig(BaseStrategyConfig):
    """
    Arbitrage strategy configuration

    Consolidated from: trading/strategies/implementations/arbitrage/enhanced_arbitrage.py
    """
    strategy_type: StrategyType = StrategyType.ARBITRAGE

    # Arbitrage parameters
    min_spread_bps: float = 5.0
    """Minimum spread in basis points. Default: 5 bps"""

    max_spread_bps: float = 50.0
    """Maximum spread in basis points. Default: 50 bps"""

    confidence_threshold: float = 0.8
    """Minimum confidence for execution. Default: 80%"""

    execution_speed: str = 'fast'
    """Execution speed requirement ('fast', 'normal'). Default: 'fast'"""

    max_execution_time: float = 5.0
    """Maximum execution time in seconds. Default: 5.0s"""

    # Additional parameters from local config
    min_price_discrepancy: float = 0.001
    """Minimum price discrepancy (0.1%). Default: 0.001"""

    max_position_pct: float = 0.05
    """Maximum position size (5%). Default: 0.05"""

    transaction_cost_threshold: float = 0.0005
    """Max transaction cost (0.05%). Default: 0.0005"""

    arbitrage_pairs: List[Tuple[str, str]] = field(default_factory=lambda: [
        ('AAPL', 'MSFT'), ('GOOGL', 'AMZN'), ('TSLA', 'NVDA')
    ])
    """Asset pairs for arbitrage. Default: Tech stock pairs"""

    opportunity_timeout: float = 10.0
    """Opportunity timeout in seconds. Default: 10.0s"""

    price_update_frequency: float = 1.0
    """Price update frequency in seconds. Default: 1.0s"""

    # Venues
    enable_multi_venue: bool = True
    """Enable multi-venue arbitrage. Default: True"""

# ============================================================================
# STRATEGY FACTORY
# ============================================================================

def create_strategy_config(strategy_type: StrategyType, **kwargs) -> BaseStrategyConfig:
    """
    Factory function to create strategy configs

    Args:
        strategy_type: Type of strategy
        **kwargs: Additional configuration parameters

    Returns:
        Strategy configuration instance
    """
    config_map = {
        StrategyType.MOMENTUM: MomentumConfig,
        StrategyType.MEAN_REVERSION: MeanReversionConfig,
        StrategyType.STATISTICAL_ARBITRAGE: StatisticalArbitrageConfig,
        StrategyType.FACTOR: FactorConfig,
        StrategyType.MULTI_ASSET: MultiAssetConfig,
        StrategyType.PAIRS_TRADING: PairsConfig,
        StrategyType.VOLATILITY: VolatilityConfig,
        StrategyType.ARBITRAGE: ArbitrageConfig,
    }

    config_class = config_map.get(strategy_type)
    if not config_class:
        raise ValueError(f"Unknown strategy type: {strategy_type}")

    return config_class(**kwargs)

def get_all_strategy_configs() -> Dict[StrategyType, BaseStrategyConfig]:
    """
    Get default configurations for all strategy types

    Returns:
        Dictionary mapping strategy types to default configs
    """
    # NOTE: StrategyType enum may include values whose implementations/configs
    # are not present in this codebase (e.g., strategies deliberately removed).
    # We only return configs for strategy types supported by create_strategy_config().
    supported: Dict[StrategyType, BaseStrategyConfig] = {}
    for strategy_type in (
        StrategyType.MOMENTUM,
        StrategyType.MEAN_REVERSION,
        StrategyType.STATISTICAL_ARBITRAGE,
        StrategyType.FACTOR,
        StrategyType.MULTI_ASSET,
        StrategyType.PAIRS_TRADING,
        StrategyType.VOLATILITY,
        StrategyType.ARBITRAGE,
    ):
        supported[strategy_type] = create_strategy_config(strategy_type)
    return supported

# ============================================================================
# BACKWARD COMPATIBILITY
# ============================================================================

# Maintain backward compatibility with old names
StrategyConfig = BaseStrategyConfig

