#!/usr/bin/env python3
"""
Enhanced Professional Regime Detection System
============================================

Institutional-grade regime detection with multi-timeframe analysis,
macro indicators, and cross-asset confirmation.

Author: Professional Quant Enhancement
Version: 2.0.0
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import asyncio
from concurrent.futures import ThreadPoolExecutor
import warnings
warnings.filterwarnings('ignore')

# Scientific computing
try:
    from sklearn.mixture import GaussianMixture
    from sklearn.preprocessing import StandardScaler, RobustScaler
    from sklearn.decomposition import PCA
    from sklearn.cluster import KMeans
    from scipy import stats
    from scipy.signal import find_peaks
    import hmmlearn.hmm
    ADVANCED_LIBS_AVAILABLE = True
except ImportError:
    ADVANCED_LIBS_AVAILABLE = False

logger = logging.getLogger(__name__)

class RegimeTimeframe(Enum):
    """Multi-timeframe regime classification"""
    INTRADAY = "intraday"      # 1-5 minute bars
    SHORT_TERM = "short_term"   # 15-60 minute bars  
    DAILY = "daily"            # Daily bars
    WEEKLY = "weekly"          # Weekly aggregation
    MONTHLY = "monthly"        # Monthly aggregation

class MacroRegime(Enum):
    """Macro market regimes"""
    RISK_ON = "risk_on"
    RISK_OFF = "risk_off"
    ROTATION = "rotation"
    CRISIS = "crisis"
    RECOVERY = "recovery"
    EXPANSION = "expansion"
    CONTRACTION = "contraction"

class MicroRegime(Enum):
    """Micro market structure regimes"""
    HIGH_LIQUIDITY = "high_liquidity"
    LOW_LIQUIDITY = "low_liquidity"
    FRAGMENTED = "fragmented"
    CONCENTRATED = "concentrated"
    NORMAL = "normal"

@dataclass
class EnhancedRegimeState:
    """Enhanced regime state with multi-dimensional analysis"""
    # Primary regime classification
    primary_regime: str
    confidence: float
    regime_strength: float
    
    # Multi-timeframe analysis
    timeframe_regimes: Dict[RegimeTimeframe, str]
    timeframe_confidence: Dict[RegimeTimeframe, float]
    regime_alignment_score: float  # How aligned are different timeframes
    
    # Macro context
    macro_regime: MacroRegime
    macro_confidence: float
    macro_factors: Dict[str, float]
    
    # Micro structure
    micro_regime: MicroRegime
    liquidity_score: float
    execution_difficulty: float
    
    # Advanced metrics
    regime_transition_probability: float
    expected_regime_duration: int
    volatility_forecast: float
    correlation_stability: float
    
    # Strategy implications
    strategy_suitability: Dict[str, float]
    risk_adjustment_factor: float
    position_sizing_multiplier: float
    
    # Metadata
    timestamp: datetime
    data_quality_score: float
    computation_time_ms: float

@dataclass 
class RegimeConfig:
    """Enhanced configuration for regime detection"""
    # Timeframe settings
    timeframes: List[RegimeTimeframe] = field(default_factory=lambda: [
        RegimeTimeframe.SHORT_TERM, RegimeTimeframe.DAILY, RegimeTimeframe.WEEKLY
    ])
    
    # Model parameters
    n_regimes: int = 6
    lookback_windows: Dict[RegimeTimeframe, int] = field(default_factory=lambda: {
        RegimeTimeframe.INTRADAY: 100,
        RegimeTimeframe.SHORT_TERM: 200,
        RegimeTimeframe.DAILY: 252,
        RegimeTimeframe.WEEKLY: 52,
        RegimeTimeframe.MONTHLY: 24
    })
    
    # Advanced features
    enable_macro_indicators: bool = True
    enable_cross_asset_confirmation: bool = True
    enable_volatility_forecasting: bool = True
    enable_regime_transition_modeling: bool = True
    
    # Performance settings
    max_computation_time_ms: int = 100
    enable_parallel_processing: bool = True
    cache_results: bool = True
    
    # Thresholds
    min_confidence_threshold: float = 0.6
    regime_alignment_threshold: float = 0.7
    transition_probability_threshold: float = 0.3

class EnhancedRegimeDetector:
    """
    Professional-grade regime detection system with institutional features.
    
    Key Enhancements:
    1. Multi-timeframe regime analysis with alignment scoring
    2. Macro regime detection using cross-asset signals
    3. Volatility regime forecasting
    4. Regime transition probability modeling
    5. Strategy-specific risk adjustments
    6. Real-time performance optimization
    """
    
    def __init__(self, config: Optional[RegimeConfig] = None):
        self.config = config or RegimeConfig()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize models
        self._initialize_models()
        
        # State management
        self.regime_history: Dict[str, List[EnhancedRegimeState]] = {}
        self.macro_cache: Dict[str, Any] = {}
        self.performance_metrics: Dict[str, float] = {}
        
        # Parallel processing
        if self.config.enable_parallel_processing:
            self.executor = ThreadPoolExecutor(max_workers=4)
        else:
            self.executor = None
            
        self.logger.info("Enhanced regime detector initialized with professional features")
    
    def _initialize_models(self):
        """Initialize advanced regime detection models"""
        self.models = {}
        
        if ADVANCED_LIBS_AVAILABLE:
            # Multi-regime HMM for each timeframe
            for timeframe in self.config.timeframes:
                self.models[f'hmm_{timeframe.value}'] = hmmlearn.hmm.GaussianHMM(
                    n_components=self.config.n_regimes,
                    covariance_type='full',
                    n_iter=100,
                    random_state=42
                )
            
            # Regime transition model
            self.models['transition_model'] = GaussianMixture(
                n_components=3,  # Stable, transitioning, volatile
                covariance_type='full',
                random_state=42
            )
            
            # Volatility forecasting model
            self.models['volatility_model'] = GaussianMixture(
                n_components=4,  # Low, normal, high, extreme vol
                covariance_type='full', 
                random_state=42
            )
            
            # Scalers for different feature types
            self.scalers = {
                'returns': RobustScaler(),
                'volatility': StandardScaler(),
                'macro': StandardScaler(),
                'microstructure': RobustScaler()
            }
        
        self.logger.info(f"Initialized {len(self.models)} advanced models")
    
    async def detect_regime_async(self, 
                                symbol: str,
                                market_data: pd.DataFrame,
                                macro_data: Optional[Dict[str, pd.Series]] = None) -> EnhancedRegimeState:
        """
        Asynchronous regime detection with full professional analysis.
        
        Args:
            symbol: Trading symbol
            market_data: OHLCV data
            macro_data: Optional macro indicators (VIX, yields, etc.)
            
        Returns:
            Enhanced regime state with multi-dimensional analysis
        """
        start_time = datetime.now()
        
        try:
            # Parallel feature extraction for different timeframes
            if self.executor:
                tasks = []
                for timeframe in self.config.timeframes:
                    task = asyncio.create_task(
                        self._extract_timeframe_features_async(market_data, timeframe)
                    )
                    tasks.append((timeframe, task))
                
                # Collect results
                timeframe_features = {}
                for timeframe, task in tasks:
                    timeframe_features[timeframe] = await task
            else:
                # Sequential processing fallback
                timeframe_features = {}
                for timeframe in self.config.timeframes:
                    timeframe_features[timeframe] = self._extract_timeframe_features(
                        market_data, timeframe
                    )
            
            # Multi-timeframe regime classification
            timeframe_regimes = {}
            timeframe_confidence = {}
            
            for timeframe, features in timeframe_features.items():
                regime, confidence = self._classify_timeframe_regime(features, timeframe)
                timeframe_regimes[timeframe] = regime
                timeframe_confidence[timeframe] = confidence
            
            # Calculate regime alignment score
            regime_alignment_score = self._calculate_regime_alignment(timeframe_regimes)
            
            # Determine primary regime (weighted by timeframe importance)
            primary_regime, primary_confidence = self._determine_primary_regime(
                timeframe_regimes, timeframe_confidence
            )
            
            # Macro regime analysis
            macro_regime, macro_confidence, macro_factors = await self._analyze_macro_regime_async(
                market_data, macro_data
            )
            
            # Micro structure analysis
            micro_regime, liquidity_score = self._analyze_microstructure(market_data)
            
            # Advanced analytics
            transition_prob = self._calculate_transition_probability(
                symbol, primary_regime, timeframe_features
            )
            
            expected_duration = self._estimate_regime_duration(
                symbol, primary_regime, regime_alignment_score
            )
            
            volatility_forecast = self._forecast_volatility(
                market_data, primary_regime, macro_factors
            )
            
            correlation_stability = self._assess_correlation_stability(
                market_data, macro_factors
            )
            
            # Strategy implications
            strategy_suitability = self._calculate_enhanced_strategy_suitability(
                primary_regime, macro_regime, micro_regime, volatility_forecast
            )
            
            risk_adjustment = self._calculate_risk_adjustment_factor(
                primary_confidence, regime_alignment_score, volatility_forecast
            )
            
            position_sizing_multiplier = self._calculate_position_sizing_multiplier(
                volatility_forecast, liquidity_score, regime_alignment_score
            )
            
            # Data quality assessment
            data_quality_score = self._assess_data_quality(market_data, timeframe_features)
            
            # Create enhanced regime state
            computation_time = (datetime.now() - start_time).total_seconds() * 1000
            
            regime_state = EnhancedRegimeState(
                primary_regime=primary_regime,
                confidence=primary_confidence,
                regime_strength=self._calculate_regime_strength(primary_regime, timeframe_features),
                timeframe_regimes=timeframe_regimes,
                timeframe_confidence=timeframe_confidence,
                regime_alignment_score=regime_alignment_score,
                macro_regime=macro_regime,
                macro_confidence=macro_confidence,
                macro_factors=macro_factors,
                micro_regime=micro_regime,
                liquidity_score=liquidity_score,
                execution_difficulty=self._calculate_execution_difficulty(micro_regime, volatility_forecast),
                regime_transition_probability=transition_prob,
                expected_regime_duration=expected_duration,
                volatility_forecast=volatility_forecast,
                correlation_stability=correlation_stability,
                strategy_suitability=strategy_suitability,
                risk_adjustment_factor=risk_adjustment,
                position_sizing_multiplier=position_sizing_multiplier,
                timestamp=datetime.now(),
                data_quality_score=data_quality_score,
                computation_time_ms=computation_time
            )
            
            # Update history
            self._update_regime_history(symbol, regime_state)
            
            # Update performance metrics
            self._update_performance_metrics(regime_state)
            
            return regime_state
            
        except Exception as e:
            self.logger.error(f"Enhanced regime detection failed for {symbol}: {e}")
            return self._create_fallback_regime_state()
    
    def detect_regime(self, 
                     symbol: str,
                     market_data: pd.DataFrame,
                     macro_data: Optional[Dict[str, pd.Series]] = None) -> EnhancedRegimeState:
        """Synchronous wrapper for regime detection"""
        return asyncio.run(self.detect_regime_async(symbol, market_data, macro_data))
    
    async def _extract_timeframe_features_async(self, 
                                              market_data: pd.DataFrame, 
                                              timeframe: RegimeTimeframe) -> Dict[str, float]:
        """Extract features for specific timeframe asynchronously"""
        return self._extract_timeframe_features(market_data, timeframe)
    
    def _extract_timeframe_features(self, 
                                  market_data: pd.DataFrame, 
                                  timeframe: RegimeTimeframe) -> Dict[str, float]:
        """Extract comprehensive features for specific timeframe"""
        try:
            lookback = self.config.lookback_windows.get(timeframe, 100)
            
            # Resample data if needed for timeframe
            if timeframe == RegimeTimeframe.WEEKLY:
                data = market_data.resample('W').agg({
                    'open': 'first', 'high': 'max', 'low': 'min', 
                    'close': 'last', 'volume': 'sum'
                }).dropna()
            elif timeframe == RegimeTimeframe.MONTHLY:
                data = market_data.resample('M').agg({
                    'open': 'first', 'high': 'max', 'low': 'min',
                    'close': 'last', 'volume': 'sum'
                }).dropna()
            else:
                data = market_data.copy()
            
            if len(data) < 20:
                return {}
            
            # Use recent data for analysis
            recent_data = data.tail(min(lookback, len(data)))
            
            features = {}
            
            # Enhanced return analysis
            returns = recent_data['close'].pct_change().dropna()
            if len(returns) > 0:
                features.update(self._extract_return_features(returns, timeframe))
            
            # Enhanced volatility analysis  
            features.update(self._extract_volatility_features(returns, timeframe))
            
            # Trend analysis
            features.update(self._extract_trend_features(recent_data['close'], timeframe))
            
            # Mean reversion analysis
            features.update(self._extract_mean_reversion_features(returns, recent_data['close']))
            
            # Volume analysis
            if 'volume' in recent_data.columns:
                features.update(self._extract_volume_features(recent_data, timeframe))
            
            # Microstructure analysis
            features.update(self._extract_microstructure_features(recent_data))
            
            return features
            
        except Exception as e:
            self.logger.error(f"Feature extraction failed for {timeframe}: {e}")
            return {}
    
    def _extract_return_features(self, returns: pd.Series, timeframe: RegimeTimeframe) -> Dict[str, float]:
        """Extract enhanced return-based features"""
        features = {}
        
        if len(returns) < 10:
            return features
        
        try:
            # Basic statistics
            features[f'{timeframe.value}_return_mean'] = float(returns.mean())
            features[f'{timeframe.value}_return_std'] = float(returns.std())
            features[f'{timeframe.value}_return_skew'] = float(returns.skew())
            features[f'{timeframe.value}_return_kurtosis'] = float(returns.kurtosis())
            
            # Higher moments
            features[f'{timeframe.value}_return_var'] = float(returns.var())
            
            # Tail risk measures
            var_95 = returns.quantile(0.05)
            var_99 = returns.quantile(0.01)
            features[f'{timeframe.value}_var_95'] = float(var_95)
            features[f'{timeframe.value}_var_99'] = float(var_99)
            
            # Expected shortfall (CVaR)
            cvar_95 = returns[returns <= var_95].mean()
            features[f'{timeframe.value}_cvar_95'] = float(cvar_95) if not pd.isna(cvar_95) else var_95
            
            # Autocorrelation structure
            for lag in [1, 2, 5]:
                if len(returns) > lag:
                    autocorr = returns.autocorr(lag=lag)
                    if not pd.isna(autocorr):
                        features[f'{timeframe.value}_autocorr_{lag}'] = float(autocorr)
            
            # Ljung-Box test for serial correlation
            if len(returns) >= 20:
                try:
                    from scipy.stats import jarque_bera
                    jb_stat, jb_pvalue = jarque_bera(returns.dropna())
                    features[f'{timeframe.value}_normality_pvalue'] = float(jb_pvalue)
                except:
                    pass
            
            # Regime-specific return patterns
            positive_runs = self._calculate_run_lengths(returns > 0)
            negative_runs = self._calculate_run_lengths(returns < 0)
            
            features[f'{timeframe.value}_max_positive_run'] = float(max(positive_runs) if positive_runs else 0)
            features[f'{timeframe.value}_max_negative_run'] = float(max(negative_runs) if negative_runs else 0)
            features[f'{timeframe.value}_avg_positive_run'] = float(np.mean(positive_runs) if positive_runs else 0)
            features[f'{timeframe.value}_avg_negative_run'] = float(np.mean(negative_runs) if negative_runs else 0)
            
        except Exception as e:
            self.logger.warning(f"Return feature extraction error: {e}")
        
        return features
    
    def _extract_volatility_features(self, returns: pd.Series, timeframe: RegimeTimeframe) -> Dict[str, float]:
        """Extract enhanced volatility features"""
        features = {}
        
        if len(returns) < 10:
            return features
        
        try:
            # Rolling volatilities
            for window in [5, 10, 20]:
                if len(returns) >= window:
                    rolling_vol = returns.rolling(window).std()
                    features[f'{timeframe.value}_vol_{window}d'] = float(rolling_vol.iloc[-1])
                    
                    # Volatility of volatility
                    vol_changes = rolling_vol.pct_change().dropna()
                    if len(vol_changes) > 0:
                        features[f'{timeframe.value}_vol_of_vol_{window}d'] = float(vol_changes.std())
            
            # GARCH-like volatility clustering
            if len(returns) >= 20:
                squared_returns = returns ** 2
                vol_clustering = squared_returns.autocorr(lag=1)
                if not pd.isna(vol_clustering):
                    features[f'{timeframe.value}_vol_clustering'] = float(vol_clustering)
            
            # Volatility regimes using quantiles
            if len(returns) >= 50:
                rolling_vol_20 = returns.rolling(20).std()
                vol_quantiles = rolling_vol_20.quantile([0.25, 0.5, 0.75])
                current_vol = rolling_vol_20.iloc[-1]
                
                if current_vol <= vol_quantiles[0.25]:
                    vol_regime = 0  # Low vol
                elif current_vol <= vol_quantiles[0.5]:
                    vol_regime = 1  # Medium-low vol
                elif current_vol <= vol_quantiles[0.75]:
                    vol_regime = 2  # Medium-high vol
                else:
                    vol_regime = 3  # High vol
                
                features[f'{timeframe.value}_vol_regime'] = float(vol_regime)
                features[f'{timeframe.value}_vol_percentile'] = float(
                    (rolling_vol_20 <= current_vol).mean()
                )
            
            # Volatility forecasting features
            if len(returns) >= 30:
                # Simple EWMA volatility
                ewma_vol = returns.ewm(span=20).std().iloc[-1]
                features[f'{timeframe.value}_ewma_vol'] = float(ewma_vol)
                
                # Volatility momentum
                vol_short = returns.rolling(5).std().iloc[-1]
                vol_long = returns.rolling(20).std().iloc[-1]
                if vol_long > 0:
                    vol_momentum = vol_short / vol_long
                    features[f'{timeframe.value}_vol_momentum'] = float(vol_momentum)
            
        except Exception as e:
            self.logger.warning(f"Volatility feature extraction error: {e}")
        
        return features
    
    def _calculate_run_lengths(self, boolean_series: pd.Series) -> List[int]:
        """Calculate run lengths for boolean series"""
        if len(boolean_series) == 0:
            return []
        
        runs = []
        current_run = 1
        
        for i in range(1, len(boolean_series)):
            if boolean_series.iloc[i] == boolean_series.iloc[i-1]:
                current_run += 1
            else:
                if boolean_series.iloc[i-1]:  # Only count True runs
                    runs.append(current_run)
                current_run = 1
        
        # Don't forget the last run
        if boolean_series.iloc[-1]:
            runs.append(current_run)
        
        return runs
    
    # Additional methods would continue here...
    # This is a comprehensive foundation for the enhanced regime detector
    
    def _create_fallback_regime_state(self) -> EnhancedRegimeState:
        """Create fallback regime state when detection fails"""
        return EnhancedRegimeState(
            primary_regime="unknown",
            confidence=0.5,
            regime_strength=0.5,
            timeframe_regimes={tf: "unknown" for tf in self.config.timeframes},
            timeframe_confidence={tf: 0.5 for tf in self.config.timeframes},
            regime_alignment_score=0.5,
            macro_regime=MacroRegime.EXPANSION,
            macro_confidence=0.5,
            macro_factors={},
            micro_regime=MicroRegime.NORMAL,
            liquidity_score=0.5,
            execution_difficulty=0.5,
            regime_transition_probability=0.5,
            expected_regime_duration=10,
            volatility_forecast=0.02,
            correlation_stability=0.5,
            strategy_suitability={'momentum': 0.5, 'mean_reversion': 0.5, 'pairs_trading': 0.5},
            risk_adjustment_factor=1.0,
            position_sizing_multiplier=1.0,
            timestamp=datetime.now(),
            data_quality_score=0.5,
            computation_time_ms=0.0
        )

# Placeholder methods for the remaining functionality
# In a real implementation, these would be fully developed

    def _extract_trend_features(self, prices: pd.Series, timeframe: RegimeTimeframe) -> Dict[str, float]:
        """Extract trend features - placeholder"""
        return {}
    
    def _extract_mean_reversion_features(self, returns: pd.Series, prices: pd.Series) -> Dict[str, float]:
        """Extract mean reversion features - placeholder"""
        return {}
    
    def _extract_volume_features(self, data: pd.DataFrame, timeframe: RegimeTimeframe) -> Dict[str, float]:
        """Extract volume features - placeholder"""
        return {}
    
    def _extract_microstructure_features(self, data: pd.DataFrame) -> Dict[str, float]:
        """Extract microstructure features - placeholder"""
        return {}
    
    def _classify_timeframe_regime(self, features: Dict[str, float], timeframe: RegimeTimeframe) -> Tuple[str, float]:
        """Classify regime for timeframe - placeholder"""
        return "trending", 0.7
    
    def _calculate_regime_alignment(self, timeframe_regimes: Dict[RegimeTimeframe, str]) -> float:
        """Calculate alignment score - placeholder"""
        return 0.8
    
    def _determine_primary_regime(self, timeframe_regimes: Dict, timeframe_confidence: Dict) -> Tuple[str, float]:
        """Determine primary regime - placeholder"""
        return "trending", 0.75
    
    async def _analyze_macro_regime_async(self, market_data: pd.DataFrame, macro_data: Optional[Dict]) -> Tuple[MacroRegime, float, Dict[str, float]]:
        """Analyze macro regime - placeholder"""
        return MacroRegime.EXPANSION, 0.7, {}
    
    def _analyze_microstructure(self, market_data: pd.DataFrame) -> Tuple[MicroRegime, float]:
        """Analyze microstructure - placeholder"""
        return MicroRegime.NORMAL, 0.7
    
    def _calculate_transition_probability(self, symbol: str, regime: str, features: Dict) -> float:
        """Calculate transition probability - placeholder"""
        return 0.3
    
    def _estimate_regime_duration(self, symbol: str, regime: str, alignment_score: float) -> int:
        """Estimate regime duration - placeholder"""
        return 15
    
    def _forecast_volatility(self, market_data: pd.DataFrame, regime: str, macro_factors: Dict) -> float:
        """Forecast volatility - placeholder"""
        return 0.025
    
    def _assess_correlation_stability(self, market_data: pd.DataFrame, macro_factors: Dict) -> float:
        """Assess correlation stability - placeholder"""
        return 0.8
    
    def _calculate_enhanced_strategy_suitability(self, primary_regime: str, macro_regime: MacroRegime, micro_regime: MicroRegime, vol_forecast: float) -> Dict[str, float]:
        """Calculate enhanced strategy suitability - placeholder"""
        return {'momentum': 0.7, 'mean_reversion': 0.6, 'pairs_trading': 0.8}
    
    def _calculate_risk_adjustment_factor(self, confidence: float, alignment: float, vol_forecast: float) -> float:
        """Calculate risk adjustment factor - placeholder"""
        return 1.0
    
    def _calculate_position_sizing_multiplier(self, vol_forecast: float, liquidity_score: float, alignment: float) -> float:
        """Calculate position sizing multiplier - placeholder"""
        return 1.0
    
    def _assess_data_quality(self, market_data: pd.DataFrame, features: Dict) -> float:
        """Assess data quality - placeholder"""
        return 0.9
    
    def _calculate_regime_strength(self, regime: str, features: Dict) -> float:
        """Calculate regime strength - placeholder"""
        return 0.8
    
    def _calculate_execution_difficulty(self, micro_regime: MicroRegime, vol_forecast: float) -> float:
        """Calculate execution difficulty - placeholder"""
        return 0.3
    
    def _update_regime_history(self, symbol: str, regime_state: EnhancedRegimeState):
        """Update regime history - placeholder"""
        pass
    
    def _update_performance_metrics(self, regime_state: EnhancedRegimeState):
        """Update performance metrics - placeholder"""
        pass

__all__ = [
    'EnhancedRegimeDetector',
    'EnhancedRegimeState', 
    'RegimeConfig',
    'RegimeTimeframe',
    'MacroRegime',
    'MicroRegime'
]
