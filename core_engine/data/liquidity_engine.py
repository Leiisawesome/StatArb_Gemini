#!/usr/bin/env python3
"""
Liquidity Assessment Engine - Volume-Based Implementation
=========================================================

Real liquidity assessment using 1-minute OHLCV data.

Computes liquidity metrics from available data:
- Volume ratio (current vs average)
- Spread proxy from High-Low range
- Kyle's lambda (market impact coefficient)
- Liquidity regime classification

Supports ADS v3.0 compliance:
- §3 ERAR: Provides Kyle's λ and spread for cost modeling
- §4 SRI: Provides liquidity fragility metrics
- §7 Sizing: Provides liquidity factor for position sizing

Author: StatArb_Gemini
Version: 2.0.0 (Volume-Based Implementation)
Date: December 3, 2025
"""

import logging
import uuid
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

# Import JIT utilities
try:
    from ..utils.jit_utils import (
        jit_calculate_spread_proxy,
        jit_calculate_spread_history,
        jit_calculate_overall_score,
        jit_calculate_percentile
    )
except ImportError:
    # Fallback to pure Python if JIT utils not available
    jit_calculate_spread_proxy = None
    jit_calculate_spread_history = None
    jit_calculate_overall_score = None
    jit_calculate_percentile = None

# Import ISystemComponent for orchestrator integration (Rule 1)
try:
    from ..system.interfaces import ISystemComponent
except ImportError:
    # Fallback for testing
    from abc import ABC, abstractmethod
    class ISystemComponent(ABC):
        @abstractmethod
        async def initialize(self) -> bool: pass
        @abstractmethod
        async def start(self) -> bool: pass
        @abstractmethod
        async def stop(self) -> bool: pass
        @abstractmethod
        async def health_check(self) -> Dict[str, Any]: pass
        @abstractmethod
        def get_status(self) -> Dict[str, Any]: pass

logger = logging.getLogger(__name__)

class LiquidityRegime(Enum):
    """Liquidity regime classification"""
    HIGH_LIQUIDITY = "high_liquidity"
    NORMAL_LIQUIDITY = "normal_liquidity"
    LOW_LIQUIDITY = "low_liquidity"
    ILLIQUID = "illiquid"
    CRISIS_LIQUIDITY = "crisis_liquidity"

@dataclass
class LiquidityScore:
    """
    Comprehensive liquidity scoring metrics.

    Used by:
    - ADS §3 ERAR: cost model (kyle_lambda, spread_bps)
    - ADS §7: position sizing (liquidity_factor)
    - Rule 7: execution algorithm selection
    """

    # Identity
    symbol: str
    timestamp: datetime

    # Core scores
    overall_score: float           # 0-100 composite liquidity score
    liquidity_regime: LiquidityRegime
    confidence: float              # 0-1 confidence in assessment

    # Volume metrics
    avg_daily_volume: float        # 20-bar average volume
    current_volume: float          # Current bar volume
    volume_ratio: float            # current / average
    volume_percentile: float       # Percentile vs historical

    # Spread metrics (estimated from High-Low)
    spread_proxy_bps: float        # (H-L)/C * 10000
    effective_spread_bps: float    # Spread + slippage estimate
    spread_percentile: float       # Percentile vs historical

    # Market impact (Kyle's lambda)
    kyle_lambda: float             # Price impact per unit volume
    market_impact_bps: float       # Estimated impact for 1% ADV

    # Risk metrics
    liquidity_risk_score: float    # 0-100 (higher = more risk)
    slippage_estimate_bps: float   # Expected slippage in bps

    # ADS §7: Position sizing factor
    liquidity_factor: float        # 1/(1 + (φ/φ0)²) for sizing

    # Metadata
    bars_analyzed: int = 0
    data_quality: str = "good"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'overall_score': self.overall_score,
            'liquidity_regime': self.liquidity_regime.value,
            'confidence': self.confidence,
            'avg_daily_volume': self.avg_daily_volume,
            'current_volume': self.current_volume,
            'volume_ratio': self.volume_ratio,
            'volume_percentile': self.volume_percentile,
            'spread_proxy_bps': self.spread_proxy_bps,
            'effective_spread_bps': self.effective_spread_bps,
            'spread_percentile': self.spread_percentile,
            'kyle_lambda': self.kyle_lambda,
            'market_impact_bps': self.market_impact_bps,
            'liquidity_risk_score': self.liquidity_risk_score,
            'slippage_estimate_bps': self.slippage_estimate_bps,
            'liquidity_factor': self.liquidity_factor,
            'bars_analyzed': self.bars_analyzed,
            'data_quality': self.data_quality
        }

class LiquidityAssessmentEngine(ISystemComponent):
    """
    Volume-Based Liquidity Assessment Engine

    Computes real liquidity metrics from 1-minute OHLCV data:
    - Volume ratio: current volume vs 20-bar average
    - Spread proxy: (High - Low) / Close as spread estimate
    - Kyle's lambda: σ / √ADV for market impact
    - Liquidity regime: Classification based on metrics

    Implements ISystemComponent for orchestrator integration (Rule 1).

    Supports ADS v3.0:
    - §3 ERAR: Provides cost model inputs (kyle_lambda, spread_bps)
    - §7 Sizing: Provides liquidity factor for position sizing
    """

    # NOT a stub anymore
    IS_STUB_IMPLEMENTATION = False

    # Class-level flag to show init message only once
    _init_logged = False

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize liquidity assessment engine.

        Args:
            config: Configuration dict with optional parameters:
                - volume_lookback: Bars for volume average (default: 20)
                - spread_lookback: Bars for spread analysis (default: 20)
                - high_liquidity_threshold: Score for high liquidity (default: 75)
                - low_liquidity_threshold: Score for low liquidity (default: 40)
                - participation_threshold: φ0 for liquidity factor (default: 0.05)
        """
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self.component_id = str(uuid.uuid4())
        self.is_initialized = False
        self.is_operational = False
        self.orchestrator: Optional[Any] = None

        # Configuration
        self.volume_lookback = self.config.get('volume_lookback', 20)
        self.spread_lookback = self.config.get('spread_lookback', 20)
        self.high_liquidity_threshold = self.config.get('high_liquidity_threshold', 75)
        self.low_liquidity_threshold = self.config.get('low_liquidity_threshold', 40)
        self.illiquid_threshold = self.config.get('illiquid_threshold', 25)
        self.participation_threshold = self.config.get('participation_threshold', 0.05)  # φ0

        # Cache for historical metrics
        self._volume_cache: Dict[str, List[float]] = {}
        self._spread_cache: Dict[str, List[float]] = {}

        # Log initialization once
        if not LiquidityAssessmentEngine._init_logged:
            LiquidityAssessmentEngine._init_logged = True
            self.logger.info("✅ LiquidityAssessmentEngine initialized (Volume-Based v2.0)")

    def register_with_orchestrator(self, orchestrator) -> str:
        """Register with orchestrator (Rule 1)."""
        self.orchestrator = orchestrator
        self.logger.info(f"✅ LiquidityAssessmentEngine registered: {self.component_id}")
        return self.component_id

    async def initialize(self) -> bool:
        """Initialize component."""
        try:
            self.is_initialized = True
            self.logger.debug("LiquidityAssessmentEngine initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"❌ Initialization failed: {e}")
            return False

    async def start(self) -> bool:
        """Start component."""
        try:
            if not self.is_initialized:
                return False
            self.is_operational = True
            self.logger.debug("LiquidityAssessmentEngine started successfully")
            return True
        except Exception as e:
            self.logger.error(f"❌ Start failed: {e}")
            return False

    async def stop(self) -> bool:
        """Stop component."""
        try:
            self.is_operational = False
            self.logger.debug("LiquidityAssessmentEngine stopped successfully")
            return True
        except Exception as e:
            self.logger.error(f"❌ Stop failed: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Health check."""
        return {
            'healthy': self.is_operational and self.is_initialized,
            'initialized': self.is_initialized,
            'operational': self.is_operational,
            'component_id': self.component_id,
            'component_type': 'LiquidityAssessmentEngine',
            'version': '2.0.0',
            'is_stub': False
        }

    def get_status(self) -> Dict[str, Any]:
        """Get component status."""
        return {
            'initialized': self.is_initialized,
            'operational': self.is_operational,
            'component_id': self.component_id,
            'symbols_cached': len(self._volume_cache),
            'version': '2.0.0'
        }

    # =========================================================================
    # CORE LIQUIDITY ASSESSMENT
    # =========================================================================

    def assess_liquidity(
        self,
        symbol: str,
        data: pd.DataFrame,
        current_idx: int = -1
    ) -> LiquidityScore:
        """
        Assess liquidity from OHLCV DataFrame.

        This is the main entry point for liquidity assessment.

        Args:
            symbol: Trading symbol
            data: DataFrame with columns: open, high, low, close, volume
            current_idx: Index to evaluate at (-1 for latest)

        Returns:
            LiquidityScore with all metrics
        """
        try:
            # Normalize index
            if current_idx < 0:
                current_idx = len(data) + current_idx

            if current_idx < self.volume_lookback:
                # Not enough data for proper assessment
                return self._create_default_score(symbol, "insufficient_data")

            # Extract data window
            window_start = max(0, current_idx - self.volume_lookback + 1)
            window = data.iloc[window_start:current_idx + 1]

            # Get current values
            current_row = data.iloc[current_idx]
            current_close = current_row.get('close', current_row.get('Close', 100.0))
            current_high = current_row.get('high', current_row.get('High', current_close))
            current_low = current_row.get('low', current_row.get('Low', current_close))
            current_volume = current_row.get('volume', current_row.get('Volume', 10000))

            # Calculate volume metrics
            volume_col = 'volume' if 'volume' in window.columns else 'Volume'
            volumes = window[volume_col].values if volume_col in window.columns else np.ones(len(window)) * 10000
            avg_volume = np.mean(volumes)
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            volume_percentile = self._calculate_percentile(current_volume, volumes)

            # Calculate spread proxy from High-Low range
            spread_proxy_bps = self._calculate_spread_proxy(current_high, current_low, current_close)

            # Historical spread analysis
            spread_history = self._calculate_spread_history(window)
            np.mean(spread_history) if len(spread_history) > 0 else spread_proxy_bps
            spread_percentile = self._calculate_percentile(spread_proxy_bps, spread_history)

            # Calculate volatility for Kyle's lambda
            close_col = 'close' if 'close' in window.columns else 'Close'
            if close_col in window.columns:
                returns = window[close_col].pct_change().dropna().values
                volatility = np.std(returns) if len(returns) > 5 else 0.02
            else:
                volatility = 0.02

            # Kyle's lambda: σ / √ADV (normalized)
            kyle_lambda = self._calculate_kyle_lambda(volatility, avg_volume)

            # Market impact estimate for 1% of ADV
            market_impact_bps = kyle_lambda * 0.01 * 10000

            # Effective spread (spread + half impact)
            effective_spread_bps = spread_proxy_bps + market_impact_bps * 0.5

            # Slippage estimate (based on spread and volume)
            slippage_estimate_bps = self._estimate_slippage(
                spread_proxy_bps, volume_ratio, volatility
            )

            # Calculate overall liquidity score (0-100)
            overall_score = self._calculate_overall_score(
                volume_ratio, spread_proxy_bps, volatility
            )

            # Determine liquidity regime
            liquidity_regime = self._classify_regime(overall_score)

            # Calculate liquidity factor for position sizing (ADS §7)
            # LF = 1 / (1 + (φ/φ0)²) where φ = participation rate proxy
            participation_proxy = 1.0 / volume_ratio if volume_ratio > 0 else 1.0
            liquidity_factor = 1.0 / (1.0 + (participation_proxy / self.participation_threshold) ** 2)

            # Liquidity risk score (inverse of liquidity)
            liquidity_risk_score = 100.0 - overall_score

            # Confidence based on data quality
            confidence = min(1.0, len(window) / self.volume_lookback)

            # Get timestamp
            timestamp = current_row.get('timestamp', datetime.now())
            if isinstance(timestamp, str):
                try:
                    timestamp = pd.to_datetime(timestamp)
                except:
                    timestamp = datetime.now()
            elif isinstance(timestamp, pd.Timestamp):
                timestamp = timestamp.to_pydatetime()
            elif not isinstance(timestamp, datetime):
                timestamp = datetime.now()

            return LiquidityScore(
                symbol=symbol,
                timestamp=timestamp,
                overall_score=overall_score,
                liquidity_regime=liquidity_regime,
                confidence=confidence,
                avg_daily_volume=avg_volume,
                current_volume=current_volume,
                volume_ratio=volume_ratio,
                volume_percentile=volume_percentile,
                spread_proxy_bps=spread_proxy_bps,
                effective_spread_bps=effective_spread_bps,
                spread_percentile=spread_percentile,
                kyle_lambda=kyle_lambda,
                market_impact_bps=market_impact_bps,
                liquidity_risk_score=liquidity_risk_score,
                slippage_estimate_bps=slippage_estimate_bps,
                liquidity_factor=liquidity_factor,
                bars_analyzed=len(window),
                data_quality="good"
            )

        except Exception as e:
            self.logger.error(f"Liquidity assessment failed for {symbol}: {e}")
            return self._create_default_score(symbol, f"error: {str(e)}")

    def assess_liquidity_score(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        historical_data: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Legacy API: Assess liquidity from market_data dict.

        For backward compatibility with existing code.

        Args:
            symbol: Trading symbol
            market_data: Dict with 'volume', 'high', 'low', 'close', etc.
            historical_data: Optional DataFrame with historical OHLCV

        Returns:
            Dict with liquidity metrics
        """
        if historical_data is not None and len(historical_data) >= self.volume_lookback:
            # Use DataFrame-based assessment
            score = self.assess_liquidity(symbol, historical_data)
            return score.to_dict()

        # Fallback: Use market_data dict only (limited assessment)
        current_volume = market_data.get('volume', 10000)
        current_close = market_data.get('close', market_data.get('price', 100.0))
        current_high = market_data.get('high', current_close * 1.001)
        current_low = market_data.get('low', current_close * 0.999)

        # Calculate basic metrics
        spread_proxy_bps = self._calculate_spread_proxy(current_high, current_low, current_close)

        # Use cached average if available
        avg_volume = self._volume_cache.get(symbol, [current_volume])
        avg_volume = np.mean(avg_volume) if avg_volume else current_volume
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0

        # Update cache
        if symbol not in self._volume_cache:
            self._volume_cache[symbol] = []
        self._volume_cache[symbol].append(current_volume)
        if len(self._volume_cache[symbol]) > self.volume_lookback:
            self._volume_cache[symbol] = self._volume_cache[symbol][-self.volume_lookback:]

        # Basic liquidity score
        overall_score = self._calculate_overall_score(volume_ratio, spread_proxy_bps, 0.02)
        liquidity_regime = self._classify_regime(overall_score)

        return {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'overall_score': overall_score,
            'liquidity_regime': liquidity_regime,
            'confidence': 0.5,  # Low confidence without historical data
            'avg_daily_volume': avg_volume,
            'current_volume': current_volume,
            'volume_ratio': volume_ratio,
            'volume_percentile': 50.0,
            'spread_proxy_bps': spread_proxy_bps,
            'effective_spread_bps': spread_proxy_bps * 1.5,
            'spread_percentile': 50.0,
            'kyle_lambda': 0.0001,
            'market_impact_bps': 1.0,
            'liquidity_risk_score': 100.0 - overall_score,
            'slippage_estimate_bps': spread_proxy_bps * 0.5,
            'liquidity_factor': 0.8,
            'bars_analyzed': len(self._volume_cache.get(symbol, [])),
            'data_quality': 'limited'
        }

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _calculate_spread_proxy(
        self,
        high: float,
        low: float,
        close: float
    ) -> float:
        """
        Calculate spread proxy from High-Low range.

        Spread ≈ (High - Low) / Close * 10000 (in bps)
        This tends to overestimate actual bid-ask spread but provides
        a reasonable proxy for illiquidity cost.
        """
        if jit_calculate_spread_proxy:
            return jit_calculate_spread_proxy(high, low, close)

        if close <= 0:
            return 10.0  # Default 10 bps

        range_pct = (high - low) / close
        spread_bps = range_pct * 10000

        # Clamp to reasonable range (0.5 to 500 bps)
        return np.clip(spread_bps, 0.5, 500.0)

    def _calculate_spread_history(self, window: pd.DataFrame) -> np.ndarray:
        """Calculate spread proxy for historical window."""
        high_col = 'high' if 'high' in window.columns else 'High'
        low_col = 'low' if 'low' in window.columns else 'Low'
        close_col = 'close' if 'close' in window.columns else 'Close'

        if high_col in window.columns and low_col in window.columns and close_col in window.columns:
            if jit_calculate_spread_history:
                return jit_calculate_spread_history(
                    window[high_col].values,
                    window[low_col].values,
                    window[close_col].values
                )

            spreads = []
            for _, row in window.iterrows():
                spread = self._calculate_spread_proxy(
                    row[high_col], row[low_col], row[close_col]
                )
                spreads.append(spread)
            return np.array(spreads) if spreads else np.array([10.0])

        return np.array([10.0])

    def _calculate_kyle_lambda(
        self,
        volatility: float,
        avg_volume: float
    ) -> float:
        """
        Calculate Kyle's lambda (market impact coefficient).

        λ = σ / √ADV

        This measures price impact per unit of volume traded.
        Higher λ = more price impact = less liquid.
        """
        if avg_volume <= 0:
            return 0.001  # Default for missing data

        kyle_lambda = volatility / np.sqrt(avg_volume)

        # Clamp to reasonable range
        return np.clip(kyle_lambda, 0.000001, 0.01)

    def _estimate_slippage(
        self,
        spread_bps: float,
        volume_ratio: float,
        volatility: float
    ) -> float:
        """
        Estimate expected slippage in basis points.

        Slippage = half_spread + volatility_impact + volume_penalty
        """
        # Base: half the spread
        half_spread = spread_bps / 2.0

        # Volatility impact (higher vol = more slippage)
        vol_impact = volatility * 10000 * 0.1  # 10% of vol in bps

        # Volume penalty (low volume = more slippage)
        if volume_ratio > 1.5:
            vol_penalty = 0.0  # High liquidity
        elif volume_ratio > 0.5:
            vol_penalty = 1.0  # Normal liquidity
        else:
            vol_penalty = 5.0 * (1.0 - volume_ratio)  # Low liquidity penalty

        slippage = half_spread + vol_impact + vol_penalty

        return np.clip(slippage, 0.1, 100.0)

    def _calculate_overall_score(
        self,
        volume_ratio: float,
        spread_bps: float,
        volatility: float
    ) -> float:
        """
        Calculate overall liquidity score (0-100).

        Higher score = more liquid.

        Components:
        - Volume score (40%): Based on volume ratio
        - Spread score (40%): Based on spread proxy
        - Volatility score (20%): Based on volatility
        """
        if jit_calculate_overall_score:
            return jit_calculate_overall_score(volume_ratio, spread_bps, volatility)

        # Volume score (0-100)
        if volume_ratio >= 2.0:
            volume_score = 100.0
        elif volume_ratio >= 1.0:
            volume_score = 50.0 + 50.0 * (volume_ratio - 1.0)
        elif volume_ratio >= 0.5:
            volume_score = 25.0 + 50.0 * (volume_ratio - 0.5)
        else:
            volume_score = 50.0 * volume_ratio

        # Spread score (0-100, lower spread = higher score)
        if spread_bps <= 5.0:
            spread_score = 100.0
        elif spread_bps <= 20.0:
            spread_score = 100.0 - (spread_bps - 5.0) * 2.0
        elif spread_bps <= 50.0:
            spread_score = 70.0 - (spread_bps - 20.0) * 1.0
        else:
            spread_score = max(0.0, 40.0 - (spread_bps - 50.0) * 0.5)

        # Volatility score (0-100, lower vol = higher score)
        vol_pct = volatility * 100  # Convert to percentage
        if vol_pct <= 1.0:
            vol_score = 100.0
        elif vol_pct <= 3.0:
            vol_score = 100.0 - (vol_pct - 1.0) * 15.0
        else:
            vol_score = max(0.0, 70.0 - (vol_pct - 3.0) * 10.0)

        # Weighted combination
        overall = (
            volume_score * 0.40 +
            spread_score * 0.40 +
            vol_score * 0.20
        )

        return np.clip(overall, 0.0, 100.0)

    def _classify_regime(self, overall_score: float) -> LiquidityRegime:
        """Classify liquidity regime from overall score."""
        if overall_score >= self.high_liquidity_threshold:
            return LiquidityRegime.HIGH_LIQUIDITY
        elif overall_score >= self.low_liquidity_threshold:
            return LiquidityRegime.NORMAL_LIQUIDITY
        elif overall_score >= self.illiquid_threshold:
            return LiquidityRegime.LOW_LIQUIDITY
        else:
            return LiquidityRegime.ILLIQUID

    def _calculate_percentile(self, value: float, history: np.ndarray) -> float:
        """Calculate percentile of value within history."""
        if len(history) == 0:
            return 50.0

        if jit_calculate_percentile:
            return jit_calculate_percentile(value, history)

        return float(np.sum(history <= value) / len(history) * 100.0)

    def _create_default_score(
        self,
        symbol: str,
        data_quality: str
    ) -> LiquidityScore:
        """Create default liquidity score when assessment fails."""
        return LiquidityScore(
            symbol=symbol,
            timestamp=datetime.now(),
            overall_score=50.0,  # Neutral
            liquidity_regime=LiquidityRegime.NORMAL_LIQUIDITY,
            confidence=0.3,  # Low confidence
            avg_daily_volume=0.0,
            current_volume=0.0,
            volume_ratio=1.0,
            volume_percentile=50.0,
            spread_proxy_bps=10.0,
            effective_spread_bps=15.0,
            spread_percentile=50.0,
            kyle_lambda=0.0001,
            market_impact_bps=1.0,
            liquidity_risk_score=50.0,
            slippage_estimate_bps=5.0,
            liquidity_factor=0.5,
            bars_analyzed=0,
            data_quality=data_quality
        )

    # =========================================================================
    # ADS INTEGRATION HELPERS
    # =========================================================================

    def get_kyle_lambda(
        self,
        symbol: str,
        data: Optional[pd.DataFrame] = None
    ) -> float:
        """
        Get Kyle's lambda for ERAR cost model (ADS §3).

        Args:
            symbol: Trading symbol
            data: Optional OHLCV DataFrame

        Returns:
            Kyle's lambda coefficient
        """
        if data is not None and len(data) >= self.volume_lookback:
            score = self.assess_liquidity(symbol, data)
            return score.kyle_lambda

        # Return cached or default
        return 0.0001

    def get_spread_bps(
        self,
        symbol: str,
        data: Optional[pd.DataFrame] = None
    ) -> float:
        """
        Get spread estimate for ERAR cost model (ADS §3).

        Args:
            symbol: Trading symbol
            data: Optional OHLCV DataFrame

        Returns:
            Effective spread in basis points
        """
        if data is not None and len(data) >= self.volume_lookback:
            score = self.assess_liquidity(symbol, data)
            return score.effective_spread_bps

        # Return default
        return 5.0

    def get_liquidity_factor(
        self,
        symbol: str,
        data: Optional[pd.DataFrame] = None
    ) -> float:
        """
        Get liquidity factor for position sizing (ADS §7).

        LF = 1 / (1 + (φ/φ0)²)

        Args:
            symbol: Trading symbol
            data: Optional OHLCV DataFrame

        Returns:
            Liquidity factor [0, 1]
        """
        if data is not None and len(data) >= self.volume_lookback:
            score = self.assess_liquidity(symbol, data)
            return score.liquidity_factor

        # Return default
        return 0.8
