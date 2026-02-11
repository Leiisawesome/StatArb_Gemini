"""
SES Pairs Trading Strategy - Spread Exhaustion Scoring Framework
================================================================

Professional pairs trading strategy using multi-dimensional Spread Exhaustion
Scoring (SES) for institutional-grade alpha generation.

Key Innovation:
The spread between cointegrated assets is treated as a synthetic mean-reverting
asset. All sophisticated mean-reversion analysis (half-life, Hurst, EWMA,
exhaustion scoring) is applied to the SPREAD itself, not just Z-scores.

SES Framework (6 Dimensions):
1. SPREAD DISLOCATION QUALITY (25%): Multi-timeframe Z-score analysis
2. INDIVIDUAL STOCK ANALYSIS (20%): Leverage enriched indicators on each leg
3. REGIME COMPATIBILITY (15%): Market regime appropriateness for pairs trading
4. VOLUME CONFIRMATION (15%): Volume exhaustion and conviction patterns
5. MEAN REVERSION SPEED (15%): OU half-life, Hurst exponent, EWMA Z-score
6. LEAD-LAG EXPLOITATION (10%): Information transfer between legs

Academic Foundations:
- Gatev et al. (2006) - Pairs trading strategies
- Avellaneda & Lee (2010) - Statistical arbitrage half-life estimation
- Hurst (1951) - Long-term storage capacity (Hurst exponent)
- Uhlenbeck & Ornstein (1930) - Theory of Brownian motion
- Engle & Granger (1987) - Cointegration analysis

Author: StatArb_Gemini Quant Team
Version: 2.0.0 (SES Framework)
Date: December 2024
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from statsmodels.tsa.stattools import coint

# Import enhanced base strategy
from ...base_strategy_enhanced import EnhancedBaseStrategy
from ...contracts import StrategySignal
from core_engine.type_definitions.strategy import SignalType

# Import centralized configuration
from core_engine.config import PairsConfig

logger = logging.getLogger(__name__)

# ============================================================================
# ENUMS AND DATA CLASSES
# ============================================================================

class PairStatus(Enum):
    """Pair trading status"""
    NEUTRAL = "neutral"
    LONG_SPREAD = "long_spread"      # Long stock1, short stock2
    SHORT_SPREAD = "short_spread"    # Short stock1, long stock2
    MONITORING = "monitoring"

class SpreadDirection(Enum):
    """Spread trade direction"""
    LONG = "long_spread"    # Spread is LOW, expect to rise
    SHORT = "short_spread"  # Spread is HIGH, expect to fall
    NEUTRAL = "neutral"

@dataclass
class PairMetrics:
    """Comprehensive metrics for a trading pair"""

    # Identity
    stock1: str
    stock2: str
    pair_id: str = ""

    # Cointegration metrics
    correlation: float = 0.0
    cointegration_pvalue: float = 1.0
    hedge_ratio: float = 1.0

    # Spread statistics (rolling)
    spread_mean: float = 0.0
    spread_std: float = 1.0
    current_zscore: float = 0.0
    ewma_zscore: float = 0.0

    # Mean reversion metrics (Dimension 5)
    half_life: float = float('inf')
    hurst_exponent: float = 0.5

    # SES scores
    ses_score: float = 0.0
    ses_breakdown: Dict[str, float] = field(default_factory=dict)

    # Trading state
    status: PairStatus = PairStatus.NEUTRAL
    entry_time: Optional[datetime] = None
    entry_zscore: float = 0.0
    entry_ses_score: float = 0.0

    # Performance tracking
    trades_count: int = 0
    winning_trades: int = 0
    total_pnl: float = 0.0

    # Timestamps
    last_update: Optional[datetime] = None

    def __post_init__(self):
        if not self.pair_id:
            self.pair_id = f"{self.stock1}_{self.stock2}"

@dataclass
class SESScoreBreakdown:
    """Detailed breakdown of SES score components"""

    # Dimension scores (0-100 each)
    dislocation_quality: float = 50.0
    individual_stocks: float = 50.0
    regime_compatibility: float = 50.0
    volume_confirmation: float = 50.0
    mean_reversion_speed: float = 50.0
    lead_lag: float = 50.0

    # Sub-component details
    zscore_20: float = 0.0
    zscore_60: float = 0.0
    zscore_120: float = 0.0
    half_life: float = float('inf')
    hurst_exponent: float = 0.5
    ewma_zscore: float = 0.0
    spread_velocity: float = 0.0

    # Composite
    total_score: float = 50.0
    confidence: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            'd1_dislocation_quality': self.dislocation_quality,
            'd2_individual_stocks': self.individual_stocks,
            'd3_regime_compatibility': self.regime_compatibility,
            'd4_volume_confirmation': self.volume_confirmation,
            'd5_mean_reversion_speed': self.mean_reversion_speed,
            'd6_lead_lag': self.lead_lag,
            'half_life': self.half_life,
            'hurst_exponent': self.hurst_exponent,
            'ewma_zscore': self.ewma_zscore,
            'total_score': self.total_score,
            'confidence': self.confidence
        }

# ============================================================================
# MEAN REVERSION CORE (Shared Logic from MR Strategy)
# ============================================================================

class MeanReversionCore:
    """
    Core mean-reversion analysis logic shared with Mean Reversion strategy.

    Applied to SPREAD series for pairs trading.
    Based on Avellaneda & Lee (2010), Hurst (1951), Ornstein-Uhlenbeck.
    """

    @staticmethod
    def calculate_half_life(series: pd.Series, max_lag: int = 1) -> float:
        """
        Calculate OU process half-life for spread series.

        Half-life = time (in bars) for spread to revert halfway to mean.
        Shorter half-life = faster mean reversion = higher confidence.

        Method:
        1. Compute log prices (or use raw spread)
        2. Run AR(1) regression: Δy_t = α + β*y_{t-1} + ε_t
        3. Half-life = -ln(2) / β

        Returns:
            Half-life in bars (inf if not mean-reverting)
        """
        try:
            if len(series) < 30:
                return float('inf')

            series_clean = series.dropna()
            if len(series_clean) < 30:
                return float('inf')

            # For spreads, use raw values (already stationary if cointegrated)
            y = series_clean.values
            y_lag = np.roll(y, 1)[1:]
            y_diff = np.diff(y)

            # Ensure same length
            y_lag = y_lag[:len(y_diff)]

            # AR(1) regression: Δy = α + β*y_{t-1}
            X = np.column_stack([np.ones(len(y_lag)), y_lag])
            try:
                beta = np.linalg.lstsq(X, y_diff, rcond=None)[0]
                slope = beta[1]
            except np.linalg.LinAlgError:
                return float('inf')

            # Half-life calculation
            if slope >= 0:
                # Not mean-reverting
                return float('inf')

            half_life = -np.log(2) / slope

            # Sanity check
            if half_life <= 0 or half_life > len(series):
                return float('inf')

            return half_life

        except Exception as e:
            logger.debug(f"Half-life calculation failed: {e}")
            return float('inf')

    @staticmethod
    def calculate_hurst_exponent(series: pd.Series, max_lag: int = 20) -> float:
        """
        Calculate Hurst exponent for spread series.

        Interpretation:
        - H < 0.5: Mean-reverting (anti-persistent) - GOOD for pairs trading
        - H = 0.5: Random walk (no memory)
        - H > 0.5: Trending (persistent) - BAD for pairs trading

        Method: Rescaled Range (R/S) analysis

        Returns:
            Hurst exponent (0 to 1)
        """
        try:
            if len(series) < 50:
                return 0.5

            returns = series.pct_change().dropna().values

            if len(returns) < 50:
                return 0.5

            # R/S analysis at different scales
            lags = range(10, min(max_lag + 1, len(returns) // 4))
            rs_values = []

            for lag in lags:
                n_windows = len(returns) // lag
                if n_windows < 2:
                    continue

                rs_for_lag = []
                for i in range(n_windows):
                    window = returns[i * lag:(i + 1) * lag]

                    # Mean-adjusted cumulative sum
                    mean_adj = window - np.mean(window)
                    cumsum = np.cumsum(mean_adj)

                    # Range
                    R = np.max(cumsum) - np.min(cumsum)

                    # Standard deviation
                    S = np.std(window, ddof=1)

                    if S > 0:
                        rs_for_lag.append(R / S)

                if rs_for_lag:
                    rs_values.append((np.log(lag), np.log(np.mean(rs_for_lag))))

            if len(rs_values) < 3:
                return 0.5

            # Linear regression on log-log plot
            x = np.array([v[0] for v in rs_values])
            y = np.array([v[1] for v in rs_values])

            slope, _ = np.polyfit(x, y, 1)

            return np.clip(slope, 0.0, 1.0)

        except Exception as e:
            logger.debug(f"Hurst exponent calculation failed: {e}")
            return 0.5

    @staticmethod
    def calculate_ewma_zscore(
        series: pd.Series,
        span: int = 20,
        min_periods: int = 10
    ) -> float:
        """
        Calculate EWMA z-score for spread series.

        More responsive to regime changes than rolling z-score.
        Gives more weight to recent observations.

        Returns:
            EWMA z-score
        """
        try:
            if len(series) < min_periods:
                return 0.0

            ewma_mean = series.ewm(span=span, min_periods=min_periods).mean()
            ewma_std = series.ewm(span=span, min_periods=min_periods).std()

            current_value = series.iloc[-1]
            current_mean = ewma_mean.iloc[-1]
            current_std = ewma_std.iloc[-1]

            if pd.isna(current_std) or current_std <= 0:
                return 0.0

            return (current_value - current_mean) / current_std

        except Exception as e:
            logger.debug(f"EWMA z-score calculation failed: {e}")
            return 0.0

# ============================================================================
# SPREAD EXHAUSTION SCORER
# ============================================================================

class SpreadExhaustionScorer:
    """
    Spread Exhaustion Scoring (SES) Engine

    Calculates multi-dimensional exhaustion score for spread mean reversion.
    Leverages mean reversion alpha logic applied to the synthetic spread asset.

    6 Dimensions:
    1. Spread Dislocation Quality (25%)
    2. Individual Stock Analysis (20%)
    3. Regime Compatibility (15%)
    4. Volume Confirmation (15%)
    5. Mean Reversion Speed (15%) - Enhanced with MR strategy logic
    6. Lead-Lag Exploitation (10%)
    """

    # Dimension weights (must sum to 1.0)
    WEIGHTS = {
        'dislocation_quality': 0.25,
        'individual_stocks': 0.20,
        'regime_compatibility': 0.15,
        'volume_confirmation': 0.15,
        'mean_reversion_speed': 0.15,
        'lead_lag': 0.10
    }

    # Default thresholds (can be overridden by config)
    DEFAULT_SES_ENTRY_THRESHOLD = 65  # Minimum SES for entry
    DEFAULT_SES_HIGH_CONFIDENCE = 80  # High confidence threshold

    def __init__(self, config: Optional[PairsConfig] = None):
        self.config = config or PairsConfig()
        self.mr_core = MeanReversionCore()

        # Use config thresholds if provided, otherwise use defaults
        self.SES_ENTRY_THRESHOLD = getattr(self.config, 'ses_entry_threshold', self.DEFAULT_SES_ENTRY_THRESHOLD)
        self.SES_HIGH_CONFIDENCE = getattr(self.config, 'ses_high_confidence_threshold', self.DEFAULT_SES_HIGH_CONFIDENCE)

    def calculate_ses(
        self,
        spread_series: pd.Series,
        stock1_data: pd.DataFrame,
        stock2_data: pd.DataFrame,
        spread_direction: SpreadDirection,
        regime_context: Optional[Any] = None,
        pair_correlation: float = 0.8
    ) -> Tuple[float, SESScoreBreakdown]:
        """
        Calculate complete Spread Exhaustion Score.

        Args:
            spread_series: Historical spread values
            stock1_data: Enriched DataFrame for stock1
            stock2_data: Enriched DataFrame for stock2
            spread_direction: Expected reversion direction
            regime_context: Current market regime
            pair_correlation: Current pair correlation

        Returns:
            Tuple of (total_score, detailed_breakdown)
        """
        breakdown = SESScoreBreakdown()

        if len(spread_series) < 30:
            return 0.0, breakdown

        current_spread = spread_series.iloc[-1]

        # =========================================
        # DIMENSION 1: Spread Dislocation Quality (25%)
        # =========================================
        breakdown.dislocation_quality, d1_details = self._calculate_dislocation_quality(
            spread_series, current_spread
        )
        breakdown.zscore_20 = d1_details.get('zscore_20', 0)
        breakdown.zscore_60 = d1_details.get('zscore_60', 0)
        breakdown.zscore_120 = d1_details.get('zscore_120', 0)

        # =========================================
        # DIMENSION 2: Individual Stock Analysis (20%)
        # =========================================
        breakdown.individual_stocks = self._analyze_individual_stocks(
            stock1_data, stock2_data, spread_direction
        )

        # =========================================
        # DIMENSION 3: Regime Compatibility (15%)
        # =========================================
        breakdown.regime_compatibility = self._calculate_regime_compatibility(
            regime_context, pair_correlation
        )

        # =========================================
        # DIMENSION 4: Volume Confirmation (15%)
        # =========================================
        breakdown.volume_confirmation = self._analyze_volume_dynamics(
            stock1_data, stock2_data, spread_direction
        )

        # =========================================
        # DIMENSION 5: Mean Reversion Speed (15%) - ENHANCED
        # =========================================
        d5_score, d5_details = self._analyze_mean_reversion_speed(
            spread_series, stock1_data, stock2_data
        )
        breakdown.mean_reversion_speed = d5_score
        breakdown.half_life = d5_details.get('half_life', float('inf'))
        breakdown.hurst_exponent = d5_details.get('hurst_exponent', 0.5)
        breakdown.ewma_zscore = d5_details.get('ewma_zscore', 0.0)
        breakdown.spread_velocity = d5_details.get('spread_velocity', 0.0)

        # =========================================
        # DIMENSION 6: Lead-Lag Exploitation (10%)
        # =========================================
        breakdown.lead_lag = self._analyze_lead_lag(stock1_data, stock2_data)

        # =========================================
        # COMPOSITE SCORE
        # =========================================
        breakdown.total_score = (
            self.WEIGHTS['dislocation_quality'] * breakdown.dislocation_quality +
            self.WEIGHTS['individual_stocks'] * breakdown.individual_stocks +
            self.WEIGHTS['regime_compatibility'] * breakdown.regime_compatibility +
            self.WEIGHTS['volume_confirmation'] * breakdown.volume_confirmation +
            self.WEIGHTS['mean_reversion_speed'] * breakdown.mean_reversion_speed +
            self.WEIGHTS['lead_lag'] * breakdown.lead_lag
        )

        # Calculate confidence from score
        breakdown.confidence = self._score_to_confidence(breakdown.total_score)

        return breakdown.total_score, breakdown

    def _calculate_dislocation_quality(
        self,
        spread_series: pd.Series,
        current_spread: float
    ) -> Tuple[float, Dict[str, float]]:
        """
        Dimension 1: Multi-timeframe Z-score analysis.

        High quality dislocation:
        - Large on short timeframe (recent move)
        - Moderate on medium timeframe (not structural)
        - Small on long timeframe (in line with long-term mean)

        This pattern suggests NOISE, not INFORMATION.
        """
        details = {}

        # Multi-timeframe Z-scores
        if len(spread_series) >= 20:
            window_20 = spread_series.iloc[-20:]
            details['zscore_20'] = (current_spread - window_20.mean()) / max(window_20.std(), 1e-8)
        else:
            details['zscore_20'] = 0.0

        if len(spread_series) >= 60:
            window_60 = spread_series.iloc[-60:]
            details['zscore_60'] = (current_spread - window_60.mean()) / max(window_60.std(), 1e-8)
        else:
            details['zscore_60'] = details['zscore_20']

        if len(spread_series) >= 120:
            window_120 = spread_series.iloc[-120:]
            details['zscore_120'] = (current_spread - window_120.mean()) / max(window_120.std(), 1e-8)
        else:
            details['zscore_120'] = details['zscore_60']

        z20, z60, z120 = abs(details['zscore_20']), abs(details['zscore_60']), abs(details['zscore_120'])

        # Quality pattern scoring
        if z20 > 2.0 and z120 < 1.5:
            # Strong short-term, weak long-term = likely noise (high quality)
            score = 90
        elif z20 > 1.5 and z120 < 1.2:
            score = 80
        elif z20 > z60 > z120:
            # Diminishing with timeframe = good pattern
            score = 70 + 10 * (z20 - z120) / max(z20, 1)
        elif z20 > z60:
            score = 60
        elif z20 > 1.5:
            # Just use absolute dislocation
            score = 40 + min(z20 * 10, 30)
        else:
            score = 30

        return np.clip(score, 0, 100), details

    def _analyze_individual_stocks(
        self,
        stock1_data: pd.DataFrame,
        stock2_data: pd.DataFrame,
        spread_direction: SpreadDirection
    ) -> float:
        """
        Dimension 2: Analyze individual stock signals from enriched data.

        Best case: Both stocks showing exhaustion signals supporting reversion.
        Worst case: One stock trending strongly against reversion.
        """
        score = 50  # Baseline

        if stock1_data.empty or stock2_data.empty:
            return score

        try:
            # Get enriched indicators
            rsi1 = self._safe_get(stock1_data, 'rsi', 50)
            rsi2 = self._safe_get(stock2_data, 'rsi', 50)
            momentum1 = self._safe_get(stock1_data, 'momentum_10', 0)
            momentum2 = self._safe_get(stock2_data, 'momentum_10', 0)
            trend1 = self._safe_get(stock1_data, 'trend_strength', 0)
            self._safe_get(stock2_data, 'trend_strength', 0)
            comp_z1 = self._safe_get(stock1_data, 'composite_z', 0)
            comp_z2 = self._safe_get(stock2_data, 'composite_z', 0)

            if spread_direction == SpreadDirection.LONG:
                # Spread LOW → expect stock1 UP, stock2 DOWN

                # RSI alignment
                if rsi1 < 40 and rsi2 > 60:
                    score += 25  # Perfect alignment
                elif rsi1 < 50 and rsi2 > 50:
                    score += 12

                # Momentum alignment
                if momentum1 > 0 and momentum2 < 0:
                    score += 15

                # Trend penalty (if stock1 trending down strongly)
                if trend1 < -0.5 and momentum1 < -0.02:
                    score -= 20

                # Composite Z divergence
                if comp_z1 < -1 and comp_z2 > 1:
                    score += 15

            elif spread_direction == SpreadDirection.SHORT:
                # Spread HIGH → expect stock1 DOWN, stock2 UP

                if rsi1 > 60 and rsi2 < 40:
                    score += 25
                elif rsi1 > 50 and rsi2 < 50:
                    score += 12

                if momentum1 < 0 and momentum2 > 0:
                    score += 15

                if trend1 > 0.5 and momentum1 > 0.02:
                    score -= 20

                if comp_z1 > 1 and comp_z2 < -1:
                    score += 15

            # MACD histogram exhaustion on either leg
            for stock_data in [stock1_data, stock2_data]:
                if len(stock_data) >= 2:
                    macd_hist = self._safe_get(stock_data, 'macd_histogram', 0)
                    macd_hist_prev = self._safe_get(stock_data, 'macd_histogram', 0, offset=-1)

                    # Histogram turning = momentum exhaustion
                    if macd_hist * macd_hist_prev < 0:  # Sign change
                        score += 5

        except Exception as e:
            logger.debug(f"Individual stock analysis failed: {e}")

        return np.clip(score, 0, 100)

    def _calculate_regime_compatibility(
        self,
        regime_context: Optional[Any],
        pair_correlation: float
    ) -> float:
        """
        Dimension 3: Market regime appropriateness for pairs trading.

        Best regimes: sideways, range_bound, low_volatility
        Worst regimes: trending, crisis, extreme_volatility
        """
        regime_scores = {
            'range_bound': 95,
            'sideways': 90,
            'choppy': 75,
            'low_volatility': 85,
            'normal_volatility': 70,
            'high_volatility': 45,
            'extreme_volatility': 20,
            'bull_low_volatility': 65,
            'bull_high_volatility': 40,
            'bear_low_volatility': 60,
            'bear_high_volatility': 30,
            'crisis': 10,
        }

        if regime_context is None:
            base_score = 60  # Neutral default
        else:
            try:
                regime_name = regime_context.primary_regime.value if hasattr(regime_context, 'primary_regime') else 'normal_volatility'
                base_score = regime_scores.get(regime_name, 50)
            except Exception:  # Avoid catching SystemExit, KeyboardInterrupt, etc.
                base_score = 60

        # Correlation adjustment
        if pair_correlation > 0.95:
            # Too correlated - spread barely moves
            base_score *= 0.7
        elif pair_correlation < 0.5:
            # Correlation breaking down
            base_score *= 0.8

        return np.clip(base_score, 0, 100)

    def _analyze_volume_dynamics(
        self,
        stock1_data: pd.DataFrame,
        stock2_data: pd.DataFrame,
        spread_direction: SpreadDirection
    ) -> float:
        """
        Dimension 4: Volume exhaustion and conviction patterns.

        Best for reversion:
        - Declining volume on spread expansion (exhaustion)
        - Volume spike at entry point (capitulation)
        """
        score = 50  # Baseline

        if stock1_data.empty or stock2_data.empty:
            return score

        try:
            # Volume ratios
            vol_ratio1 = self._safe_get(stock1_data, 'volume_ratio', 1.0)
            vol_ratio2 = self._safe_get(stock2_data, 'volume_ratio', 1.0)

            # Volume trends
            vol_change1 = self._safe_get(stock1_data, 'volume_change', 0)
            vol_change2 = self._safe_get(stock2_data, 'volume_change', 0)

            # Capitulation volume (spike)
            if vol_ratio1 > 1.5 or vol_ratio2 > 1.5:
                score += 20

            # Declining volume = fading conviction
            if vol_change1 < 0 and vol_change2 < 0:
                score += 15

            # OBV divergence (price without volume support)
            obv_mom1 = self._safe_get(stock1_data, 'obv_momentum', 0)
            obv_mom2 = self._safe_get(stock2_data, 'obv_momentum', 0)
            price_mom1 = self._safe_get(stock1_data, 'momentum_10', 0)
            price_mom2 = self._safe_get(stock2_data, 'momentum_10', 0)

            # Price up, OBV down = unsustainable (reversion likely)
            if np.sign(price_mom1) != np.sign(obv_mom1) and abs(obv_mom1) > 0.01:
                score += 10
            if np.sign(price_mom2) != np.sign(obv_mom2) and abs(obv_mom2) > 0.01:
                score += 10

            # Volume breakout pattern
            vol_breakout1 = self._safe_get(stock1_data, 'volume_breakout', False)
            vol_breakout2 = self._safe_get(stock2_data, 'volume_breakout', False)

            if vol_breakout1 or vol_breakout2:
                # High volume breakout might indicate information, not noise
                score -= 10

        except Exception as e:
            logger.debug(f"Volume dynamics analysis failed: {e}")

        return np.clip(score, 0, 100)

    def _analyze_mean_reversion_speed(
        self,
        spread_series: pd.Series,
        stock1_data: pd.DataFrame,
        stock2_data: pd.DataFrame
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Dimension 5: Full mean reversion analysis using MR strategy logic.

        Components:
        1. Half-life estimation (OU process)
        2. Hurst exponent validation
        3. EWMA Z-score confirmation
        4. Spread velocity analysis
        5. Spread exhaustion patterns

        This is the ENHANCED dimension leveraging EnhancedMeanReversionStrategy logic.
        """
        details = {}
        score = 50  # Baseline

        # =========================================
        # 5A. HALF-LIFE ESTIMATION (OU Process)
        # =========================================
        half_life = MeanReversionCore.calculate_half_life(spread_series)
        details['half_life'] = half_life

        if half_life == float('inf'):
            score -= 25  # Not mean reverting
            details['half_life_score'] = 0
        elif half_life < 5:
            score += 25  # Very fast reversion
            details['half_life_score'] = 100
        elif half_life < 10:
            score += 20
            details['half_life_score'] = 85
        elif half_life < 20:
            score += 10
            details['half_life_score'] = 65
        elif half_life < 40:
            score += 0
            details['half_life_score'] = 45
        else:
            score -= 10
            details['half_life_score'] = 25

        # =========================================
        # 5B. HURST EXPONENT VALIDATION
        # =========================================
        hurst = MeanReversionCore.calculate_hurst_exponent(spread_series)
        details['hurst_exponent'] = hurst

        if hurst < 0.4:
            score += 20  # Strong mean reversion
            details['hurst_score'] = 100
        elif hurst < 0.45:
            score += 15
            details['hurst_score'] = 80
        elif hurst < 0.5:
            score += 5
            details['hurst_score'] = 60
        elif hurst < 0.55:
            score += 0  # Random walk zone
            details['hurst_score'] = 40
        else:
            score -= 15  # Trending - bad for MR
            details['hurst_score'] = 10

        # =========================================
        # 5C. EWMA Z-SCORE CONFIRMATION
        # =========================================
        ewma_zscore = MeanReversionCore.calculate_ewma_zscore(spread_series)
        rolling_zscore = (spread_series.iloc[-1] - spread_series.mean()) / max(spread_series.std(), 1e-8)
        details['ewma_zscore'] = ewma_zscore
        details['rolling_zscore'] = rolling_zscore

        # EWMA and rolling should agree in direction
        if np.sign(ewma_zscore) == np.sign(rolling_zscore):
            if abs(ewma_zscore) >= abs(rolling_zscore) * 0.8:
                score += 10  # Strong confirmation
                details['zscore_agreement'] = 'strong'
            else:
                score += 5
                details['zscore_agreement'] = 'moderate'
        else:
            score -= 5  # Disagreement - regime transition?
            details['zscore_agreement'] = 'divergent'

        # =========================================
        # 5D. SPREAD VELOCITY ANALYSIS
        # =========================================
        spread_diff = spread_series.diff()
        if len(spread_diff) >= 20:
            velocity_5 = spread_diff.iloc[-5:].mean()
            velocity_20 = spread_diff.iloc[-20:].mean()
            details['spread_velocity'] = velocity_5
            details['velocity_ratio'] = abs(velocity_5) / max(abs(velocity_20), 1e-8)

            # Deceleration = exhaustion
            if abs(velocity_5) < abs(velocity_20) * 0.5:
                score += 10  # Decelerating
                details['velocity_pattern'] = 'decelerating'
            elif abs(velocity_5) > abs(velocity_20) * 1.5:
                score -= 5  # Accelerating
                details['velocity_pattern'] = 'accelerating'
            else:
                details['velocity_pattern'] = 'stable'

        # =========================================
        # 5E. SPREAD EXHAUSTION PATTERNS
        # =========================================
        # Volatility compression (consolidation before reversal)
        if len(spread_series) >= 20:
            spread_vol_5 = spread_series.iloc[-5:].std()
            spread_vol_20 = spread_series.iloc[-20:].std()

            if spread_vol_5 < spread_vol_20 * 0.7:
                score += 5  # Volatility compression
                details['vol_pattern'] = 'compression'
            else:
                details['vol_pattern'] = 'normal'

        return np.clip(score, 0, 100), details

    def _analyze_lead_lag(
        self,
        stock1_data: pd.DataFrame,
        stock2_data: pd.DataFrame,
        lookback: int = 20
    ) -> float:
        """
        Dimension 6: Detect lead-lag relationships for timing.

        If one stock consistently leads the other, we can exploit
        the information transfer for better entry timing.
        """
        score = 50  # Baseline

        if stock1_data.empty or stock2_data.empty:
            return score

        try:
            if len(stock1_data) < lookback or len(stock2_data) < lookback:
                return score

            returns1 = stock1_data['close'].pct_change().iloc[-lookback:].values
            returns2 = stock2_data['close'].pct_change().iloc[-lookback:].values

            # Remove NaNs
            mask = ~(np.isnan(returns1) | np.isnan(returns2))
            returns1 = returns1[mask]
            returns2 = returns2[mask]

            if len(returns1) < 10:
                return score

            # Cross-correlation at different lags
            correlations = {}
            for lag in range(-3, 4):
                if lag < 0:
                    if len(returns1) + lag > 0:
                        corr = np.corrcoef(returns1[:lag], returns2[-lag:])[0, 1]
                    else:
                        corr = 0
                elif lag > 0:
                    if len(returns1) - lag > 0:
                        corr = np.corrcoef(returns1[lag:], returns2[:-lag])[0, 1]
                    else:
                        corr = 0
                else:
                    corr = np.corrcoef(returns1, returns2)[0, 1]

                correlations[lag] = corr if not np.isnan(corr) else 0

            # Find optimal lag
            optimal_lag = max(correlations, key=lambda k: abs(correlations[k]))

            # Exploitable lead-lag relationship
            if optimal_lag != 0 and abs(correlations[optimal_lag]) > abs(correlations[0]) + 0.05:
                score += 20

        except Exception as e:
            logger.debug(f"Lead-lag analysis failed: {e}")

        return np.clip(score, 0, 100)

    def _safe_get(
        self,
        data: pd.DataFrame,
        column: str,
        default: Any = 0.0,
        offset: int = 0
    ) -> Any:
        """Safely get a value from DataFrame"""
        try:
            if column in data.columns:
                idx = -1 + offset
                if abs(idx) <= len(data):
                    return data[column].iloc[idx]
            return default
        except Exception:  # Avoid catching SystemExit, KeyboardInterrupt, etc.
            return default

    def _score_to_confidence(self, score: float) -> float:
        """Convert SES score to confidence level"""
        if score >= 80:
            return 0.90
        elif score >= 70:
            return 0.80
        elif score >= 60:
            return 0.70
        elif score >= 50:
            return 0.60
        else:
            return 0.50

# ============================================================================
# MAIN STRATEGY CLASS
# ============================================================================

class SESPairsTradingStrategy(EnhancedBaseStrategy):
    """
    SES Pairs Trading Strategy

    Advanced pairs trading using Spread Exhaustion Scoring (SES) framework.
    Applies sophisticated mean-reversion analysis to spread series.

    Key Features:
    - 6-dimensional SES scoring for entry decisions
    - Mean reversion core logic (half-life, Hurst, EWMA)
    - Individual stock exhaustion analysis
    - Regime-aware position sizing
    - Dynamic confidence scaling
    """

    def __init__(self, config: PairsConfig):
        """Initialize SES Pairs Trading Strategy"""
        super().__init__(config)
        self.config: PairsConfig = config

        # SES Engine
        self.ses_scorer = SpreadExhaustionScorer(config)

        # Data tracking
        self.market_data: Dict[str, pd.DataFrame] = {}
        self.spread_cache: Dict[str, pd.Series] = {}

        # Pair tracking
        self.selected_pairs: Dict[str, PairMetrics] = {}
        self.active_pairs: Dict[str, PairMetrics] = {}

        # Cointegration cache
        self.correlation_matrix: Optional[pd.DataFrame] = None
        self.cointegration_results: Dict[Tuple[str, str], Dict[str, Any]] = {}

        # Performance
        self.trade_history: List[Dict[str, Any]] = []

        logger.info(f"🧠 SES Pairs Trading Strategy {self.strategy_id} initialized")

    # ========================================
    # LIFECYCLE METHODS
    # ========================================

    async def _initialize_strategy_components(self) -> bool:
        """Initialize strategy components"""
        try:
            logger.info(f"🔄 Initializing SES Pairs Trading for {self.strategy_id}...")

            if len(self.config.asset_universe) < 2:
                logger.error("❌ Asset universe must contain at least 2 assets")
                return False

            self._initialize_data_structures()

            logger.info(f"✅ SES Pairs Trading initialized for {len(self.config.asset_universe)} assets")
            return True

        except Exception as e:
            logger.error(f"❌ SES initialization failed: {e}")
            return False

    async def _start_strategy_operations(self) -> bool:
        """Start strategy operations"""
        logger.info(f"🚀 Starting SES Pairs Trading operations...")
        return True

    async def _stop_strategy_operations(self) -> None:
        """Stop strategy operations"""
        logger.info(f"🔄 Stopping SES Pairs Trading operations...")
        await self._close_all_pairs()
        logger.info(f"✅ SES Pairs Trading stopped")

    async def _check_strategy_health(self) -> Dict[str, Any]:
        """Check strategy health"""
        return {
            'strategy_healthy': True,
            'selected_pairs': len(self.selected_pairs),
            'active_pairs': len(self.active_pairs),
            'avg_ses_score': self._calculate_avg_ses_score()
        }

    def _get_strategy_config_summary(self) -> Dict[str, Any]:
        """Get strategy configuration summary"""
        return {
            'strategy_type': 'SES Pairs Trading',
            'asset_universe_size': len(self.config.asset_universe),
            'ses_entry_threshold': self.ses_scorer.SES_ENTRY_THRESHOLD,
            'entry_zscore': self.config.entry_zscore,
            'exit_zscore': self.config.exit_zscore,
            'max_pairs': self.config.max_pairs
        }

    def _validate_strategy_config(self) -> bool:
        """Validate strategy configuration"""
        if self.config.entry_zscore <= self.config.exit_zscore:
            logger.error("Entry Z-score must be greater than exit Z-score")
            return False
        return True

    def _validate_enriched_data(self, enriched_data: Dict[str, pd.DataFrame]) -> None:
        """Validate enriched data has required columns"""
        required = ['close', 'volume']
        for symbol, data in enriched_data.items():
            if symbol not in self.config.asset_universe:
                continue
            missing = [c for c in required if c not in data.columns]
            if missing:
                raise ValueError(f"{symbol} missing required columns: {missing}")

    # ========================================
    # MAIN SIGNAL GENERATION
    # ========================================

    async def generate_signals(self, enriched_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
        """
        Generate pairs trading signals using SES framework.

        Args:
            enriched_data: Dict[symbol, enriched DataFrame]

        Returns:
            List of trading signals
        """
        start_time = datetime.now()
        signals = []

        try:
            self._validate_enriched_data(enriched_data)
            self._update_market_data(enriched_data)

            # Update pair selection and calculations
            await self._update_pair_selection()
            self._update_spread_calculations()
            self._update_ses_scores(enriched_data)

            # Generate entry signals using SES
            entry_signals = await self._generate_entry_signals_ses(enriched_data)
            signals.extend(entry_signals)

            # Generate exit signals
            exit_signals = await self._generate_exit_signals(enriched_data)
            signals.extend(exit_signals)

            generation_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"📊 SES Generated {len(signals)} signals in {generation_time:.3f}s")

            return signals

        except Exception as e:
            logger.error(f"SES signal generation failed: {e}")
            return []

    async def _generate_entry_signals_ses(
        self,
        enriched_data: Dict[str, pd.DataFrame]
    ) -> List[StrategySignal]:
        """Generate entry signals using SES framework"""
        signals = []

        for pair_id, pair_metrics in self.selected_pairs.items():
            # Skip if already active
            if pair_id in self.active_pairs:
                continue

            # Skip if max pairs reached
            if len(self.active_pairs) >= self.config.max_pairs:
                break

            zscore = pair_metrics.current_zscore
            ses_score = pair_metrics.ses_score

            # Determine direction
            if zscore < -self.config.entry_zscore:
                spread_direction = SpreadDirection.LONG
            elif zscore > self.config.entry_zscore:
                spread_direction = SpreadDirection.SHORT
            else:
                logger.debug(
                    f"⏸️ {pair_id} zscore not extreme: {zscore:.4f} not outside ±{self.config.entry_zscore:.2f}"
                )
                continue  # No entry condition

            # Check SES threshold (use configurable threshold)
            ses_threshold = self.ses_scorer.SES_ENTRY_THRESHOLD
            if ses_score < ses_threshold:
                logger.debug(
                    f"⏸️ {pair_id} SES too low: {ses_score:.1f} < {ses_threshold}"
                )
                continue

            # Calculate confidence from SES
            confidence = pair_metrics.ses_breakdown.get('confidence', 0.7)

            # Create pair entry signals
            pair_signals = self._create_pair_entry_signals(
                pair_metrics,
                zscore,
                spread_direction,
                confidence,
                ses_score
            )
            signals.extend(pair_signals)

            # Mark pair as active
            pair_metrics.status = PairStatus.LONG_SPREAD if spread_direction == SpreadDirection.LONG else PairStatus.SHORT_SPREAD
            pair_metrics.entry_time = datetime.now()
            pair_metrics.entry_zscore = zscore
            pair_metrics.entry_ses_score = ses_score
            self.active_pairs[pair_id] = pair_metrics

            logger.info(
                f"🎯 SES ENTRY: {pair_id} | SES={ses_score:.1f} | Z={zscore:.2f} | "
                f"Dir={spread_direction.value} | Conf={confidence:.2%} | "
                f"HL={pair_metrics.half_life:.1f}"
            )

        return signals

    async def _generate_exit_signals(
        self,
        enriched_data: Dict[str, pd.DataFrame]
    ) -> List[StrategySignal]:
        """Generate exit signals for active pairs"""
        signals = []
        pairs_to_close = []

        for pair_id, pair_metrics in self.active_pairs.items():
            zscore = pair_metrics.current_zscore
            should_exit = False
            exit_reason = ""

            # Mean reversion complete
            if abs(zscore) <= self.config.exit_zscore:
                should_exit = True
                exit_reason = "mean_reversion_complete"

            # Stop loss
            elif abs(zscore) >= self.config.stop_loss_zscore:
                should_exit = True
                exit_reason = "stop_loss"

            # Half-life timeout
            elif pair_metrics.entry_time and pair_metrics.half_life < float('inf'):
                elapsed_minutes = (datetime.now() - pair_metrics.entry_time).total_seconds() / 60
                timeout = pair_metrics.half_life * 3  # 3x half-life
                if elapsed_minutes > timeout:
                    should_exit = True
                    exit_reason = "half_life_timeout"

            # Max holding period
            elif pair_metrics.entry_time:
                holding_days = (datetime.now() - pair_metrics.entry_time).days
                if holding_days >= self.config.max_holding_period:
                    should_exit = True
                    exit_reason = "max_holding_period"

            # Correlation breakdown
            elif abs(pair_metrics.correlation) < self.config.correlation_threshold:
                should_exit = True
                exit_reason = "correlation_breakdown"

            # Hurst regime change (became trending)
            elif pair_metrics.hurst_exponent > 0.55:
                should_exit = True
                exit_reason = "regime_trending"

            if should_exit:
                exit_signals = self._create_pair_exit_signals(pair_metrics, exit_reason)
                signals.extend(exit_signals)
                pairs_to_close.append(pair_id)

                logger.info(
                    f"📉 SES EXIT: {pair_id} | Reason={exit_reason} | Z={zscore:.2f}"
                )

        # Clean up
        for pair_id in pairs_to_close:
            if pair_id in self.active_pairs:
                del self.active_pairs[pair_id]

        return signals

    # ========================================
    # SIGNAL CREATION
    # ========================================

    def _create_pair_entry_signals(
        self,
        pair_metrics: PairMetrics,
        zscore: float,
        spread_direction: SpreadDirection,
        confidence: float,
        ses_score: float
    ) -> List[StrategySignal]:
        """Create entry signals for a pair"""

        stock1, stock2 = pair_metrics.stock1, pair_metrics.stock2

        if spread_direction == SpreadDirection.LONG:
            # Spread LOW → Long stock1, Short stock2
            signal1_type = SignalType.BUY
            signal2_type = SignalType.SELL
        else:
            # Spread HIGH → Short stock1, Long stock2
            signal1_type = SignalType.SELL
            signal2_type = SignalType.BUY

        signal1 = StrategySignal(
            strategy_id=self.strategy_id,
            symbol=stock1,
            signal_type=signal1_type,
            strength=min(abs(zscore) / self.config.entry_zscore, 1.0),
            confidence=confidence,
            target_weight=self.config.position_size_pct,
            quantity_type="PERCENTAGE",
            timestamp=datetime.now(),
            additional_data={
                'pair_id': pair_metrics.pair_id,
                'pair_stock': stock2,
                'zscore': zscore,
                'ses_score': ses_score,
                'hedge_ratio': pair_metrics.hedge_ratio,
                'spread_direction': spread_direction.value,
                'half_life': pair_metrics.half_life,
                'hurst_exponent': pair_metrics.hurst_exponent,
                'ses_breakdown': pair_metrics.ses_breakdown
            }
        )

        signal2 = StrategySignal(
            strategy_id=self.strategy_id,
            symbol=stock2,
            signal_type=signal2_type,
            strength=min(abs(zscore) / self.config.entry_zscore, 1.0),
            confidence=confidence,
            target_weight=self.config.position_size_pct * abs(pair_metrics.hedge_ratio),
            quantity_type="PERCENTAGE",
            timestamp=datetime.now(),
            additional_data={
                'pair_id': pair_metrics.pair_id,
                'pair_stock': stock1,
                'zscore': zscore,
                'ses_score': ses_score,
                'hedge_ratio': pair_metrics.hedge_ratio,
                'spread_direction': spread_direction.value,
                'half_life': pair_metrics.half_life,
                'hurst_exponent': pair_metrics.hurst_exponent
            }
        )

        return [signal1, signal2]

    def _create_pair_exit_signals(
        self,
        pair_metrics: PairMetrics,
        exit_reason: str
    ) -> List[StrategySignal]:
        """Create exit signals for a pair"""

        stock1, stock2 = pair_metrics.stock1, pair_metrics.stock2

        # Reverse of entry
        if pair_metrics.status == PairStatus.LONG_SPREAD:
            signal1_type = SignalType.SELL
            signal2_type = SignalType.BUY
        else:
            signal1_type = SignalType.BUY
            signal2_type = SignalType.SELL

        signal1 = StrategySignal(
            strategy_id=self.strategy_id,
            symbol=stock1,
            signal_type=signal1_type,
            strength=1.0,
            confidence=0.9,
            target_weight=self.config.position_size_pct,
            quantity_type="PERCENTAGE",
            timestamp=datetime.now(),
            additional_data={
                'pair_id': pair_metrics.pair_id,
                'action': 'exit',
                'exit_reason': exit_reason,
                'spread_direction': pair_metrics.status.value
            }
        )

        signal2 = StrategySignal(
            strategy_id=self.strategy_id,
            symbol=stock2,
            signal_type=signal2_type,
            strength=1.0,
            confidence=0.9,
            target_weight=self.config.position_size_pct * abs(pair_metrics.hedge_ratio),
            quantity_type="PERCENTAGE",
            timestamp=datetime.now(),
            additional_data={
                'pair_id': pair_metrics.pair_id,
                'action': 'exit',
                'exit_reason': exit_reason,
                'spread_direction': pair_metrics.status.value
            }
        )

        return [signal1, signal2]

    # ========================================
    # PAIR SELECTION AND CALCULATIONS
    # ========================================

    async def _update_pair_selection(self) -> None:
        """Update pair selection based on current data"""
        try:
            self._calculate_correlation_matrix()
            await self._test_cointegration()
            self._select_trading_pairs()
        except Exception as e:
            logger.error(f"Pair selection failed: {e}")

    def _calculate_correlation_matrix(self) -> None:
        """Calculate correlation matrix"""
        price_data = {}

        for symbol in self.config.asset_universe:
            if symbol in self.market_data and len(self.market_data[symbol]) >= self.config.lookback_period:
                data = self.market_data[symbol]
                # Ensure timestamp index for proper alignment
                if 'timestamp' in data.columns and not isinstance(data.index, pd.DatetimeIndex):
                    data = data.set_index('timestamp')
                prices = data['close'].tail(self.config.lookback_period)
                price_data[symbol] = prices

        if len(price_data) >= 2:
            df = pd.DataFrame(price_data)
            self.correlation_matrix = df.corr()

    async def _test_cointegration(self) -> None:
        """Test cointegration for correlated pairs"""
        if self.correlation_matrix is None:
            return

        for i, stock1 in enumerate(self.correlation_matrix.index):
            for j, stock2 in enumerate(self.correlation_matrix.columns):
                if i < j:
                    correlation = self.correlation_matrix.loc[stock1, stock2]

                    if abs(correlation) >= self.config.min_correlation:
                        coint_result = await self._test_pair_cointegration(stock1, stock2)
                        if coint_result:
                            self.cointegration_results[(stock1, stock2)] = coint_result

    async def _test_pair_cointegration(self, stock1: str, stock2: str) -> Optional[Dict[str, Any]]:
        """Test cointegration between two stocks"""
        try:
            if stock1 not in self.market_data or stock2 not in self.market_data:
                return None

            # Ensure timestamp index for proper alignment
            data1 = self.market_data[stock1]
            data2 = self.market_data[stock2]

            if 'timestamp' in data1.columns and not isinstance(data1.index, pd.DatetimeIndex):
                data1 = data1.set_index('timestamp')
            if 'timestamp' in data2.columns and not isinstance(data2.index, pd.DatetimeIndex):
                data2 = data2.set_index('timestamp')

            prices1 = data1['close'].tail(self.config.lookback_period)
            prices2 = data2['close'].tail(self.config.lookback_period)

            aligned_data = pd.concat([prices1, prices2], axis=1, join='inner')
            aligned_data.columns = [stock1, stock2]

            if len(aligned_data) < 50:
                return None

            # Cointegration test
            score, p_value, _ = coint(aligned_data[stock1], aligned_data[stock2])

            if p_value <= self.config.cointegration_threshold:
                # Calculate hedge ratio
                from sklearn.linear_model import LinearRegression

                X = aligned_data[stock1].values.reshape(-1, 1)
                y = aligned_data[stock2].values

                reg = LinearRegression().fit(X, y)
                hedge_ratio = reg.coef_[0]

                # Calculate spread
                spread = aligned_data[stock2] - hedge_ratio * aligned_data[stock1]

                return {
                    'p_value': p_value,
                    'hedge_ratio': hedge_ratio,
                    'spread_mean': spread.mean(),
                    'spread_std': spread.std(),
                    'correlation': self.correlation_matrix.loc[stock1, stock2],
                    'last_updated': datetime.now()
                }

            return None

        except Exception as e:
            logger.error(f"Cointegration test failed for {stock1}-{stock2}: {e}")
            return None

    def _select_trading_pairs(self) -> None:
        """Select best pairs for trading"""
        self.selected_pairs.clear()

        sorted_pairs = sorted(
            self.cointegration_results.items(),
            key=lambda x: (abs(x[1]['correlation']), -x[1]['p_value'])
        )

        for (stock1, stock2), coint_data in sorted_pairs[:self.config.max_pairs * 2]:
            pair_id = f"{stock1}_{stock2}"

            pair_metrics = PairMetrics(
                stock1=stock1,
                stock2=stock2,
                pair_id=pair_id,
                correlation=coint_data['correlation'],
                cointegration_pvalue=coint_data['p_value'],
                hedge_ratio=coint_data['hedge_ratio'],
                spread_mean=coint_data['spread_mean'],
                spread_std=coint_data['spread_std'],
                last_update=datetime.now()
            )

            self.selected_pairs[pair_id] = pair_metrics

        logger.info(f"📈 Selected {len(self.selected_pairs)} pairs for SES trading")

    def _update_spread_calculations(self) -> None:
        """Update spread calculations and statistics"""
        for pair_id, pair_metrics in self.selected_pairs.items():
            spread_series = self._calculate_spread_series(pair_metrics)

            if spread_series is not None and len(spread_series) > 0:
                self.spread_cache[pair_id] = spread_series

                # Update rolling statistics
                current_spread = spread_series.iloc[-1]
                pair_metrics.spread_mean = spread_series.mean()
                pair_metrics.spread_std = spread_series.std()
                pair_metrics.current_zscore = (current_spread - pair_metrics.spread_mean) / max(pair_metrics.spread_std, 1e-8)

                # Update EWMA Z-score
                pair_metrics.ewma_zscore = MeanReversionCore.calculate_ewma_zscore(spread_series)

                # Update mean reversion metrics
                pair_metrics.half_life = MeanReversionCore.calculate_half_life(spread_series)
                pair_metrics.hurst_exponent = MeanReversionCore.calculate_hurst_exponent(spread_series)

                pair_metrics.last_update = datetime.now()

    def _update_ses_scores(self, enriched_data: Dict[str, pd.DataFrame]) -> None:
        """Update SES scores for all pairs"""
        for pair_id, pair_metrics in self.selected_pairs.items():
            spread_series = self.spread_cache.get(pair_id)

            if spread_series is None or len(spread_series) < 30:
                continue

            stock1_data = enriched_data.get(pair_metrics.stock1, pd.DataFrame())
            stock2_data = enriched_data.get(pair_metrics.stock2, pd.DataFrame())

            # Determine direction
            zscore = pair_metrics.current_zscore
            if zscore < -self.config.entry_zscore:
                spread_direction = SpreadDirection.LONG
            elif zscore > self.config.entry_zscore:
                spread_direction = SpreadDirection.SHORT
            else:
                spread_direction = SpreadDirection.NEUTRAL

            # Calculate SES
            ses_score, breakdown = self.ses_scorer.calculate_ses(
                spread_series=spread_series,
                stock1_data=stock1_data,
                stock2_data=stock2_data,
                spread_direction=spread_direction,
                regime_context=getattr(self, 'current_regime', None),
                pair_correlation=pair_metrics.correlation
            )

            pair_metrics.ses_score = ses_score
            pair_metrics.ses_breakdown = breakdown.to_dict()

    def _calculate_spread_series(self, pair_metrics: PairMetrics) -> Optional[pd.Series]:
        """Calculate spread series for a pair"""
        stock1, stock2 = pair_metrics.stock1, pair_metrics.stock2

        if stock1 not in self.market_data or stock2 not in self.market_data:
            return None

        data1 = self.market_data[stock1]
        data2 = self.market_data[stock2]

        # Ensure timestamp index for alignment
        if 'timestamp' in data1.columns and not isinstance(data1.index, pd.DatetimeIndex):
            data1 = data1.set_index('timestamp')
        if 'timestamp' in data2.columns and not isinstance(data2.index, pd.DatetimeIndex):
            data2 = data2.set_index('timestamp')

        prices1 = data1['close']
        prices2 = data2['close']

        aligned = pd.concat([prices1, prices2], axis=1, join='inner')
        aligned.columns = ['p1', 'p2']

        if len(aligned) == 0:
            logger.debug(f"No aligned data for {stock1}/{stock2}")
            return None

        spread = aligned['p2'] - pair_metrics.hedge_ratio * aligned['p1']

        return spread

    # ========================================
    # HELPER METHODS
    # ========================================

    def _update_market_data(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update market data cache"""
        for symbol, data in market_data.items():
            if symbol in self.config.asset_universe:
                self.market_data[symbol] = data

    def _initialize_data_structures(self) -> None:
        """Initialize data structures"""
        self.market_data.clear()
        self.spread_cache.clear()
        self.selected_pairs.clear()
        self.active_pairs.clear()
        self.cointegration_results.clear()

    def _calculate_avg_ses_score(self) -> float:
        """Calculate average SES score of selected pairs"""
        if not self.selected_pairs:
            return 0.0
        return np.mean([p.ses_score for p in self.selected_pairs.values()])

    async def _close_all_pairs(self) -> None:
        """Close all active pairs"""
        logger.info(f"🔄 Closing {len(self.active_pairs)} active pairs")
        self.active_pairs.clear()

    async def update_positions(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update existing positions"""
        self._update_market_data(market_data)
        self._update_spread_calculations()

    def get_ses_summary(self) -> Dict[str, Any]:
        """Get comprehensive SES strategy summary"""
        return {
            'strategy_id': self.strategy_id,
            'strategy_type': 'SES Pairs Trading',
            'selected_pairs': len(self.selected_pairs),
            'active_pairs': len(self.active_pairs),
            'avg_ses_score': self._calculate_avg_ses_score(),
            'ses_entry_threshold': self.ses_scorer.SES_ENTRY_THRESHOLD,
            'pair_details': {
                pair_id: {
                    'stock1': p.stock1,
                    'stock2': p.stock2,
                    'ses_score': p.ses_score,
                    'zscore': p.current_zscore,
                    'half_life': p.half_life,
                    'hurst': p.hurst_exponent,
                    'correlation': p.correlation,
                    'status': p.status.value,
                    'ses_breakdown': p.ses_breakdown
                }
                for pair_id, p in self.selected_pairs.items()
            }
        }

