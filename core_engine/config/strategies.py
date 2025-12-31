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

    # Multi-timeframe analysis
    confirmation_timeframes: List[str] = field(default_factory=lambda: ["15min", "1h"])
    """Confirmation timeframes. Default: ['15min', '1h']"""

    # Position sizing (inherited from BaseStrategyConfig but can override)
    base_position_pct: float = 0.03
    """Base position size. Default: 3%"""

    max_position_pct: float = 0.08
    """Maximum position size. Default: 8%"""

    momentum_scaling: bool = True
    """Scale position by momentum strength. Default: True"""

    # Risk management
    momentum_stop_pct: float = 0.03
    """Stop loss percentage. Default: 3%"""

    trailing_stop_pct: float = 0.02
    """Trailing stop percentage. Default: 2%"""

    max_holding_period: int = 20
    """Maximum holding period in bars. Default: 20"""

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

    # Price-aware exit parameters (NEW)
    stop_loss_pct: float = -5.0
    """Stop loss percentage. Exit if unrealized P&L drops below this. Default: -5%"""

    take_profit_pct: float = 10.0
    """Take profit percentage. Exit if unrealized P&L exceeds this. Default: +10%"""

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

    # =========================================
    # v5.0 SIMPLIFIED PARAMETERS (Expert Review)
    # =========================================
    # Per expert review: "If it can't make money without stacked filters, there is no real edge."
    # Simplified to 4 orthogonal features: Stretch, Exhaustion, Flow, Volatility

    use_simplified_strategy: bool = False
    """Use SimplifiedMeanReversionStrategy (v5.0) instead of EnhancedMeanReversionStrategy (v4.0). 
    Default: False (backwards compatible)"""

    # Unified Reversal Score threshold (replaces SMS + 5-factor + ERAR)
    unified_threshold: float = 0.5
    """Unified reversal score threshold for trade. Default: 0.5
    Score = w_stretch × stretch + w_exhaustion × exhaustion + w_flow × flow + w_vol × vol"""

    # Structure confirmation (for entry)
    enable_structure_confirmation: bool = True
    """Require higher low (long) or lower high (short) before entry. 
    Loses 10% of move but improves win rate by 15-20%. Default: True"""

    # Edge ratio tracking (simple alternative to ERAR)
    enable_edge_ratio_check: bool = False
    """Check simple edge ratio before trading. Default: False (insufficient history initially)"""

    min_edge_ratio: float = 1.2
    """Minimum edge ratio (avg_win × win_rate) / (avg_loss × loss_rate). Default: 1.2"""

    # Thesis invalidation exits (replaces PnL-based stops)
    max_hold_bars: int = 20
    """Maximum bars to hold position before time-based exit. Default: 20"""

    trend_acceleration_threshold: float = 1.5
    """ADX increase threshold to trigger thesis invalidation. Default: 1.5"""

    regime_shift_threshold: float = 2.0
    """Vol ratio change threshold to trigger thesis invalidation. Default: 2.0"""

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
class TrendFollowingConfig(BaseStrategyConfig):
    """
    Trend following strategy configuration

    Consolidated from: trading/strategies/implementations/trend_following/enhanced_trend_following.py
    """
    strategy_type: StrategyType = StrategyType.TREND_FOLLOWING

    # Trend parameters
    fast_ma_period: int = 12
    """Fast moving average period. Default: 12"""

    slow_ma_period: int = 26
    """Slow moving average period. Default: 26"""

    signal_ma_period: int = 9
    """Signal line period. Default: 9"""

    ma_type: str = "EMA"
    """Moving average type: 'SMA', 'EMA', 'TEMA'. Default: 'EMA'"""

    # MACD parameters
    macd_fast: int = 12
    """MACD fast period. Default: 12"""

    macd_slow: int = 26
    """MACD slow period. Default: 26"""

    macd_signal: int = 9
    """MACD signal period. Default: 9"""

    adx_period: int = 14
    """ADX period for trend strength. Default: 14"""

    adx_threshold: float = 25.0
    """Minimum ADX for strong trend. Default: 25"""

    # Position sizing
    base_position_pct: float = 0.04
    """Base position size. Default: 4%"""

    max_position_pct: float = 0.10
    """Maximum position size. Default: 10%"""

    trend_scaling: bool = True
    """Scale position by trend strength. Default: True"""

    # Risk management
    atr_period: int = 14
    """ATR period for stops. Default: 14"""

    atr_stop_multiplier: float = 2.0
    """Stop loss ATR multiple. Default: 2.0"""

    atr_multiplier: float = 2.0
    """ATR multiplier for stop loss (alias for atr_stop_multiplier). Default: 2.0"""

    trailing_stop_pct: float = 0.02
    """Trailing stop percentage. Default: 2%"""

    profit_target_ratio: float = 3.0
    """Profit target vs stop ratio. Default: 3.0"""

    max_holding_period: int = 50
    """Maximum holding period in bars. Default: 50"""

    # Trend filtering
    enable_trend_filter: bool = True
    """Enable trend filtering. Default: True"""

    min_trend_duration: int = 5
    """Minimum trend duration in bars. Default: 5"""

    trend_reversal_threshold: float = 0.02
    """Trend reversal threshold. Default: 0.02"""

    # Volatility filtering
    enable_volatility_filter: bool = True
    """Enable volatility filtering. Default: True"""

    volatility_lookback: int = 20
    """Volatility calculation period. Default: 20"""

    max_volatility_percentile: float = 0.8
    """Maximum volatility percentile. Default: 0.8"""

    # Position sizing multipliers (moved from hardcoded values)
    trend_multiplier_cap: float = 2.0
    """Maximum trend multiplier for position scaling. Default: 2.0"""

    adx_multiplier_cap: float = 2.0
    """Maximum ADX multiplier for position scaling. Default: 2.0"""

    volatility_adjustment_min: float = 0.5
    """Minimum volatility adjustment floor. Default: 0.5"""

    volatility_adjustment_cap: float = 2.0
    """Maximum volatility adjustment cap. Default: 2.0"""

    duration_confidence_multiplier: float = 2.0
    """Multiplier for trend duration confidence calculation. Default: 2.0"""

@dataclass
class BreakoutConfig(BaseStrategyConfig):
    """
    Breakout strategy configuration

    Consolidated from: trading/strategies/implementations/breakout/enhanced_breakout.py
    """
    strategy_type: StrategyType = StrategyType.BREAKOUT

    # Breakout parameters
    lookback_period: int = 20
    """Lookback for support/resistance. Default: 20 bars"""

    breakout_threshold: float = 0.02
    """Breakout confirmation threshold. Default: 2%"""

    volume_confirmation: float = 1.5
    """Volume confirmation multiplier. Default: 1.5"""

    volume_confirmation_enabled: bool = True
    """Require volume confirmation. Default: True"""

    volume_multiplier: float = 1.5
    """Volume must exceed average by this factor. Default: 1.5x"""

    consolidation_periods: int = 10
    """Periods for consolidation detection. Default: 10"""

    # Position sizing
    base_position_pct: float = 0.03
    """Base position size. Default: 3%"""

    max_position_pct: float = 0.08
    """Maximum position size. Default: 8%"""

    # Risk management
    stop_loss_pct: float = 0.03
    """Stop loss percentage. Default: 3%"""

    profit_target_ratio: float = 2.0
    """Profit target vs stop loss ratio. Default: 2.0"""

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
        StrategyType.TREND_FOLLOWING: TrendFollowingConfig,
        StrategyType.BREAKOUT: BreakoutConfig,
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
    return {
        strategy_type: create_strategy_config(strategy_type)
        for strategy_type in StrategyType
    }

# ============================================================================
# BACKWARD COMPATIBILITY
# ============================================================================

# Maintain backward compatibility with old names
StrategyConfig = BaseStrategyConfig

