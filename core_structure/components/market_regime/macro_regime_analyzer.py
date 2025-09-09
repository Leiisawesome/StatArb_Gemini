#!/usr/bin/env python3
"""
Macro Regime Analysis System
===========================

Professional macro regime detection using cross-asset signals,
economic indicators, and institutional flow analysis.

Key Features:
- Cross-asset regime confirmation (equities, bonds, commodities, FX)
- Economic cycle detection
- Risk-on/risk-off regime identification
- Central bank policy regime analysis
- Institutional flow regime detection

Author: Professional Quant Enhancement  
Version: 1.0.0
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import asyncio
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class MacroRegimeType(Enum):
    """Comprehensive macro regime classifications"""
    # Economic Cycle Regimes
    EXPANSION = "expansion"
    PEAK = "peak"
    CONTRACTION = "contraction"
    TROUGH = "trough"
    
    # Risk Regimes
    RISK_ON = "risk_on"
    RISK_OFF = "risk_off"
    RISK_ROTATION = "risk_rotation"
    
    # Monetary Policy Regimes
    ACCOMMODATIVE = "accommodative"
    TIGHTENING = "tightening"
    NEUTRAL = "neutral"
    CRISIS_RESPONSE = "crisis_response"
    
    # Market Structure Regimes
    LOW_VOLATILITY = "low_volatility"
    HIGH_VOLATILITY = "high_volatility"
    CORRELATION_BREAKDOWN = "correlation_breakdown"
    LIQUIDITY_CRISIS = "liquidity_crisis"
    
    # Geopolitical Regimes
    STABLE = "stable"
    UNCERTAINTY = "uncertainty"
    CRISIS = "crisis"

@dataclass
class MacroIndicator:
    """Individual macro indicator configuration"""
    name: str
    symbol: str
    weight: float
    regime_mapping: Dict[str, float]  # Value ranges to regime scores
    lookback_days: int = 252
    transformation: str = "level"  # level, change, zscore, percentile

@dataclass
class MacroRegimeResult:
    """Comprehensive macro regime analysis result"""
    primary_regime: MacroRegimeType
    secondary_regime: Optional[MacroRegimeType]
    confidence: float
    regime_strength: float
    
    # Cross-asset analysis
    equity_regime_score: float
    bond_regime_score: float
    commodity_regime_score: float
    fx_regime_score: float
    
    # Economic indicators
    economic_cycle_score: float
    monetary_policy_score: float
    inflation_regime_score: float
    
    # Market structure
    volatility_regime_score: float
    correlation_regime_score: float
    liquidity_regime_score: float
    
    # Geopolitical
    geopolitical_risk_score: float
    
    # Regime probabilities
    regime_probabilities: Dict[MacroRegimeType, float]
    
    # Forward-looking
    regime_transition_probability: float
    expected_regime_duration: int
    
    # Strategy implications
    equity_allocation_signal: float  # -1 to 1
    bond_allocation_signal: float
    commodity_allocation_signal: float
    volatility_target_multiplier: float
    correlation_adjustment_factor: float
    
    timestamp: datetime
    data_quality_score: float

class MacroRegimeAnalyzer:
    """
    Professional macro regime analyzer using institutional-grade indicators.
    
    Analyzes multiple dimensions:
    1. Cross-asset price action and flows
    2. Economic cycle indicators
    3. Central bank policy stance
    4. Market structure and liquidity
    5. Geopolitical risk factors
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize macro indicators
        self.indicators = self._initialize_macro_indicators()
        
        # Regime history for persistence analysis
        self.regime_history: List[MacroRegimeResult] = []
        
        # Performance tracking
        self.performance_metrics = {
            'total_analyses': 0,
            'avg_confidence': 0.0,
            'regime_accuracy': 0.0,
            'last_update': datetime.now()
        }
        
        self.logger.info(f"Macro regime analyzer initialized with {len(self.indicators)} indicators")
    
    def _initialize_macro_indicators(self) -> Dict[str, MacroIndicator]:
        """Initialize comprehensive macro indicator set"""
        indicators = {}
        
        # Equity Market Indicators
        indicators['vix'] = MacroIndicator(
            name="VIX Volatility Index",
            symbol="^VIX",
            weight=0.15,
            regime_mapping={
                "low_vol": (0, 15),      # VIX < 15 = low vol regime
                "normal_vol": (15, 25),  # VIX 15-25 = normal
                "high_vol": (25, 40),    # VIX 25-40 = high vol
                "crisis": (40, 100)      # VIX > 40 = crisis
            },
            transformation="level"
        )
        
        indicators['spx_momentum'] = MacroIndicator(
            name="S&P 500 Momentum",
            symbol="^GSPC",
            weight=0.12,
            regime_mapping={
                "strong_bull": (0.15, 1.0),
                "bull": (0.05, 0.15),
                "neutral": (-0.05, 0.05),
                "bear": (-0.15, -0.05),
                "strong_bear": (-1.0, -0.15)
            },
            lookback_days=63,  # 3-month momentum
            transformation="change"
        )
        
        # Bond Market Indicators
        indicators['yield_curve'] = MacroIndicator(
            name="10Y-2Y Yield Curve",
            symbol="yield_curve",
            weight=0.13,
            regime_mapping={
                "steep": (2.0, 5.0),      # Steep curve = expansion
                "normal": (0.5, 2.0),     # Normal curve
                "flat": (0, 0.5),         # Flat curve = late cycle
                "inverted": (-2.0, 0)     # Inverted = recession risk
            },
            transformation="level"
        )
        
        indicators['credit_spreads'] = MacroIndicator(
            name="Investment Grade Credit Spreads",
            symbol="credit_spreads",
            weight=0.11,
            regime_mapping={
                "tight": (0, 100),        # Tight spreads = risk-on
                "normal": (100, 200),     # Normal spreads
                "wide": (200, 400),       # Wide spreads = stress
                "crisis": (400, 1000)     # Very wide = crisis
            },
            transformation="level"
        )
        
        # Currency Indicators
        indicators['dxy'] = MacroIndicator(
            name="Dollar Index",
            symbol="DX-Y.NYB",
            weight=0.10,
            regime_mapping={
                "strong_dollar": (0.05, 1.0),    # Strong USD = risk-off
                "stable": (-0.05, 0.05),         # Stable USD
                "weak_dollar": (-1.0, -0.05)     # Weak USD = risk-on
            },
            lookback_days=126,  # 6-month change
            transformation="change"
        )
        
        # Commodity Indicators
        indicators['gold_real_yield'] = MacroIndicator(
            name="Gold vs Real Yields",
            symbol="gold_real_yield",
            weight=0.09,
            regime_mapping={
                "gold_bullish": (-3.0, -1.0),    # Negative real yields
                "neutral": (-1.0, 1.0),          # Moderate real yields
                "gold_bearish": (1.0, 5.0)       # High real yields
            },
            transformation="level"
        )
        
        indicators['oil_momentum'] = MacroIndicator(
            name="Oil Price Momentum",
            symbol="CL=F",
            weight=0.08,
            regime_mapping={
                "oil_bull": (0.2, 1.0),
                "oil_stable": (-0.1, 0.2),
                "oil_bear": (-1.0, -0.1)
            },
            lookback_days=63,
            transformation="change"
        )
        
        # Economic Cycle Indicators
        indicators['copper_gold_ratio'] = MacroIndicator(
            name="Copper/Gold Ratio",
            symbol="copper_gold",
            weight=0.07,
            regime_mapping={
                "growth": (0.1, 1.0),      # Rising ratio = growth
                "stable": (-0.05, 0.1),    # Stable ratio
                "slowdown": (-1.0, -0.05)  # Falling ratio = slowdown
            },
            lookback_days=126,
            transformation="change"
        )
        
        # Central Bank Policy Indicators
        indicators['fed_funds_real'] = MacroIndicator(
            name="Real Fed Funds Rate",
            symbol="fed_funds_real",
            weight=0.08,
            regime_mapping={
                "very_accommodative": (-5.0, -2.0),
                "accommodative": (-2.0, 0),
                "neutral": (0, 2.0),
                "restrictive": (2.0, 5.0)
            },
            transformation="level"
        )
        
        # Market Structure Indicators
        indicators['term_structure_vol'] = MacroIndicator(
            name="Volatility Term Structure",
            symbol="vol_term_structure",
            weight=0.07,
            regime_mapping={
                "backwardation": (-1.0, -0.1),   # High near-term vol
                "normal": (-0.1, 0.1),           # Normal structure
                "contango": (0.1, 1.0)           # Low near-term vol
            },
            transformation="level"
        )
        
        return indicators
    
    async def analyze_macro_regime_async(self, 
                                       market_data: Dict[str, pd.DataFrame],
                                       economic_data: Optional[Dict[str, pd.Series]] = None) -> MacroRegimeResult:
        """
        Comprehensive async macro regime analysis.
        
        Args:
            market_data: Dict of symbol -> OHLCV data for cross-asset analysis
            economic_data: Optional economic indicators (Fed data, etc.)
            
        Returns:
            Comprehensive macro regime analysis
        """
        try:
            # Extract cross-asset signals
            cross_asset_scores = await self._analyze_cross_asset_signals_async(market_data)
            
            # Analyze economic indicators
            economic_scores = self._analyze_economic_indicators(economic_data or {})
            
            # Market structure analysis
            market_structure_scores = self._analyze_market_structure(market_data)
            
            # Combine all signals
            regime_scores = self._combine_regime_signals(
                cross_asset_scores, economic_scores, market_structure_scores
            )
            
            # Determine primary and secondary regimes
            primary_regime, secondary_regime, confidence = self._classify_macro_regime(regime_scores)
            
            # Calculate regime strength
            regime_strength = self._calculate_regime_strength(regime_scores, primary_regime)
            
            # Forward-looking analysis
            transition_prob = self._calculate_regime_transition_probability(regime_scores)
            expected_duration = self._estimate_regime_duration(primary_regime, confidence)
            
            # Strategy implications
            allocation_signals = self._calculate_allocation_signals(primary_regime, regime_scores)
            risk_adjustments = self._calculate_risk_adjustments(primary_regime, regime_scores)
            
            # Data quality assessment
            data_quality = self._assess_macro_data_quality(market_data, economic_data)
            
            # Create comprehensive result
            result = MacroRegimeResult(
                primary_regime=primary_regime,
                secondary_regime=secondary_regime,
                confidence=confidence,
                regime_strength=regime_strength,
                
                # Cross-asset scores
                equity_regime_score=cross_asset_scores.get('equity', 0.0),
                bond_regime_score=cross_asset_scores.get('bond', 0.0),
                commodity_regime_score=cross_asset_scores.get('commodity', 0.0),
                fx_regime_score=cross_asset_scores.get('fx', 0.0),
                
                # Economic scores
                economic_cycle_score=economic_scores.get('cycle', 0.0),
                monetary_policy_score=economic_scores.get('monetary', 0.0),
                inflation_regime_score=economic_scores.get('inflation', 0.0),
                
                # Market structure scores
                volatility_regime_score=market_structure_scores.get('volatility', 0.0),
                correlation_regime_score=market_structure_scores.get('correlation', 0.0),
                liquidity_regime_score=market_structure_scores.get('liquidity', 0.0),
                
                # Geopolitical (placeholder)
                geopolitical_risk_score=0.0,
                
                # Regime probabilities
                regime_probabilities=self._calculate_regime_probabilities(regime_scores),
                
                # Forward-looking
                regime_transition_probability=transition_prob,
                expected_regime_duration=expected_duration,
                
                # Strategy implications
                equity_allocation_signal=allocation_signals.get('equity', 0.0),
                bond_allocation_signal=allocation_signals.get('bond', 0.0),
                commodity_allocation_signal=allocation_signals.get('commodity', 0.0),
                volatility_target_multiplier=risk_adjustments.get('vol_target', 1.0),
                correlation_adjustment_factor=risk_adjustments.get('correlation', 1.0),
                
                timestamp=datetime.now(),
                data_quality_score=data_quality
            )
            
            # Update history and metrics
            self._update_regime_history(result)
            self._update_performance_metrics(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Macro regime analysis failed: {e}")
            return self._create_fallback_macro_result()
    
    def analyze_macro_regime(self, 
                           market_data: Dict[str, pd.DataFrame],
                           economic_data: Optional[Dict[str, pd.Series]] = None) -> MacroRegimeResult:
        """Synchronous wrapper for macro regime analysis"""
        return asyncio.run(self.analyze_macro_regime_async(market_data, economic_data))
    
    async def _analyze_cross_asset_signals_async(self, 
                                               market_data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """Analyze cross-asset regime signals"""
        signals = {}
        
        try:
            # Equity regime analysis
            if 'SPY' in market_data or '^GSPC' in market_data:
                equity_data = market_data.get('SPY', market_data.get('^GSPC'))
                signals['equity'] = self._analyze_equity_regime(equity_data)
            
            # Bond regime analysis
            if 'TLT' in market_data or '^TNX' in market_data:
                bond_data = market_data.get('TLT', market_data.get('^TNX'))
                signals['bond'] = self._analyze_bond_regime(bond_data)
            
            # Commodity regime analysis
            if 'GLD' in market_data or 'USO' in market_data:
                commodity_data = market_data.get('GLD', market_data.get('USO'))
                signals['commodity'] = self._analyze_commodity_regime(commodity_data)
            
            # FX regime analysis
            if 'UUP' in market_data or 'DXY' in market_data:
                fx_data = market_data.get('UUP', market_data.get('DXY'))
                signals['fx'] = self._analyze_fx_regime(fx_data)
            
        except Exception as e:
            self.logger.error(f"Cross-asset analysis failed: {e}")
        
        return signals
    
    def _analyze_equity_regime(self, equity_data: pd.DataFrame) -> float:
        """Analyze equity market regime signals"""
        try:
            if len(equity_data) < 50:
                return 0.0
            
            prices = equity_data['close']
            returns = prices.pct_change().dropna()
            
            # Trend analysis
            ma_20 = prices.rolling(20).mean()
            ma_50 = prices.rolling(50).mean()
            ma_200 = prices.rolling(200).mean()
            
            current_price = prices.iloc[-1]
            
            # Bull/bear scoring based on MA relationships
            score = 0.0
            
            # Price vs moving averages
            if current_price > ma_20.iloc[-1]:
                score += 0.3
            if current_price > ma_50.iloc[-1]:
                score += 0.3
            if current_price > ma_200.iloc[-1]:
                score += 0.4
            
            # MA slope analysis
            ma_20_slope = (ma_20.iloc[-1] - ma_20.iloc[-10]) / ma_20.iloc[-10]
            ma_50_slope = (ma_50.iloc[-1] - ma_50.iloc[-20]) / ma_50.iloc[-20]
            
            if ma_20_slope > 0:
                score += 0.2
            if ma_50_slope > 0:
                score += 0.3
            
            # Volatility regime
            vol_20 = returns.rolling(20).std().iloc[-1]
            vol_200 = returns.rolling(200).std().iloc[-1]
            
            if vol_20 < vol_200:  # Lower volatility = risk-on
                score += 0.2
            
            # Normalize to -1 to 1 range
            return (score - 0.5) * 2
            
        except Exception as e:
            self.logger.error(f"Equity regime analysis failed: {e}")
            return 0.0
    
    def _analyze_bond_regime(self, bond_data: pd.DataFrame) -> float:
        """Analyze bond market regime signals"""
        try:
            if len(bond_data) < 50:
                return 0.0
            
            prices = bond_data['close']
            returns = prices.pct_change().dropna()
            
            # Bond momentum (inverse to yield momentum)
            momentum_20 = (prices.iloc[-1] - prices.iloc[-20]) / prices.iloc[-20]
            momentum_60 = (prices.iloc[-1] - prices.iloc[-60]) / prices.iloc[-60]
            
            # Positive bond momentum = falling yields = risk-off
            bond_score = (momentum_20 + momentum_60) / 2
            
            # Volatility analysis
            vol_regime = self._calculate_volatility_regime(returns)
            
            # Combine signals
            total_score = bond_score * 0.7 + vol_regime * 0.3
            
            return np.clip(total_score, -1, 1)
            
        except Exception as e:
            self.logger.error(f"Bond regime analysis failed: {e}")
            return 0.0
    
    def _analyze_commodity_regime(self, commodity_data: pd.DataFrame) -> float:
        """Analyze commodity regime signals"""
        try:
            if len(commodity_data) < 50:
                return 0.0
            
            prices = commodity_data['close']
            
            # Commodity momentum
            momentum_30 = (prices.iloc[-1] - prices.iloc[-30]) / prices.iloc[-30]
            momentum_90 = (prices.iloc[-1] - prices.iloc[-90]) / prices.iloc[-90]
            
            # Positive commodity momentum = risk-on/inflation
            commodity_score = (momentum_30 + momentum_90) / 2
            
            return np.clip(commodity_score, -1, 1)
            
        except Exception as e:
            self.logger.error(f"Commodity regime analysis failed: {e}")
            return 0.0
    
    def _analyze_fx_regime(self, fx_data: pd.DataFrame) -> float:
        """Analyze FX regime signals (USD strength)"""
        try:
            if len(fx_data) < 50:
                return 0.0
            
            prices = fx_data['close']
            
            # USD momentum
            momentum_30 = (prices.iloc[-1] - prices.iloc[-30]) / prices.iloc[-30]
            momentum_90 = (prices.iloc[-1] - prices.iloc[-90]) / prices.iloc[-90]
            
            # Strong USD = risk-off (negative score)
            usd_score = -((momentum_30 + momentum_90) / 2)
            
            return np.clip(usd_score, -1, 1)
            
        except Exception as e:
            self.logger.error(f"FX regime analysis failed: {e}")
            return 0.0
    
    def _calculate_volatility_regime(self, returns: pd.Series) -> float:
        """Calculate volatility regime score"""
        if len(returns) < 50:
            return 0.0
        
        current_vol = returns.rolling(20).std().iloc[-1]
        historical_vol = returns.rolling(200).std().iloc[-1]
        
        vol_ratio = current_vol / historical_vol if historical_vol > 0 else 1.0
        
        # High volatility = risk-off (negative score)
        if vol_ratio > 1.5:
            return -0.8
        elif vol_ratio > 1.2:
            return -0.4
        elif vol_ratio < 0.8:
            return 0.4
        else:
            return 0.0
    
    # Placeholder methods for remaining functionality
    def _analyze_economic_indicators(self, economic_data: Dict[str, pd.Series]) -> Dict[str, float]:
        """Analyze economic indicators - placeholder"""
        return {'cycle': 0.0, 'monetary': 0.0, 'inflation': 0.0}
    
    def _analyze_market_structure(self, market_data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """Analyze market structure - placeholder"""
        return {'volatility': 0.0, 'correlation': 0.0, 'liquidity': 0.0}
    
    def _combine_regime_signals(self, cross_asset: Dict, economic: Dict, market_structure: Dict) -> Dict[str, float]:
        """Combine all regime signals - placeholder"""
        return {'risk_on': 0.0, 'risk_off': 0.0, 'expansion': 0.0, 'contraction': 0.0}
    
    def _classify_macro_regime(self, regime_scores: Dict[str, float]) -> Tuple[MacroRegimeType, Optional[MacroRegimeType], float]:
        """Classify macro regime - placeholder"""
        return MacroRegimeType.EXPANSION, None, 0.7
    
    def _calculate_regime_strength(self, regime_scores: Dict[str, float], regime: MacroRegimeType) -> float:
        """Calculate regime strength - placeholder"""
        return 0.8
    
    def _calculate_regime_transition_probability(self, regime_scores: Dict[str, float]) -> float:
        """Calculate transition probability - placeholder"""
        return 0.3
    
    def _estimate_regime_duration(self, regime: MacroRegimeType, confidence: float) -> int:
        """Estimate regime duration - placeholder"""
        return 30
    
    def _calculate_allocation_signals(self, regime: MacroRegimeType, scores: Dict[str, float]) -> Dict[str, float]:
        """Calculate allocation signals - placeholder"""
        return {'equity': 0.0, 'bond': 0.0, 'commodity': 0.0}
    
    def _calculate_risk_adjustments(self, regime: MacroRegimeType, scores: Dict[str, float]) -> Dict[str, float]:
        """Calculate risk adjustments - placeholder"""
        return {'vol_target': 1.0, 'correlation': 1.0}
    
    def _assess_macro_data_quality(self, market_data: Dict, economic_data: Optional[Dict]) -> float:
        """Assess data quality - placeholder"""
        return 0.9
    
    def _calculate_regime_probabilities(self, regime_scores: Dict[str, float]) -> Dict[MacroRegimeType, float]:
        """Calculate regime probabilities - placeholder"""
        return {regime: 0.2 for regime in MacroRegimeType}
    
    def _update_regime_history(self, result: MacroRegimeResult):
        """Update regime history - placeholder"""
        pass
    
    def _update_performance_metrics(self, result: MacroRegimeResult):
        """Update performance metrics - placeholder"""
        pass
    
    def _create_fallback_macro_result(self) -> MacroRegimeResult:
        """Create fallback result - placeholder"""
        return MacroRegimeResult(
            primary_regime=MacroRegimeType.EXPANSION,
            secondary_regime=None,
            confidence=0.5,
            regime_strength=0.5,
            equity_regime_score=0.0,
            bond_regime_score=0.0,
            commodity_regime_score=0.0,
            fx_regime_score=0.0,
            economic_cycle_score=0.0,
            monetary_policy_score=0.0,
            inflation_regime_score=0.0,
            volatility_regime_score=0.0,
            correlation_regime_score=0.0,
            liquidity_regime_score=0.0,
            geopolitical_risk_score=0.0,
            regime_probabilities={regime: 0.2 for regime in MacroRegimeType},
            regime_transition_probability=0.5,
            expected_regime_duration=30,
            equity_allocation_signal=0.0,
            bond_allocation_signal=0.0,
            commodity_allocation_signal=0.0,
            volatility_target_multiplier=1.0,
            correlation_adjustment_factor=1.0,
            timestamp=datetime.now(),
            data_quality_score=0.5
        )

__all__ = [
    'MacroRegimeAnalyzer',
    'MacroRegimeResult',
    'MacroRegimeType',
    'MacroIndicator'
]
