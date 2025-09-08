#!/usr/bin/env python3
"""
Unified Market Regime Detection System
=====================================

A comprehensive market regime detection system that provides shared
market intelligence across all trading strategies.

Features:
- Multi-factor regime classification
- Confidence scoring for regime detection
- Strategy-specific regime suitability scoring
- Real-time regime monitoring and alerts

Author: Professional Trading System Architecture
Version: 1.0.0
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class MarketRegime(Enum):
    """Market regime classifications"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    MEAN_REVERTING = "mean_reverting"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    SIDEWAYS = "sideways"
    BREAKOUT = "breakout"
    UNKNOWN = "unknown"

@dataclass
class RegimeDetectionResult:
    """Result of regime detection analysis"""
    primary_regime: MarketRegime
    secondary_regime: Optional[MarketRegime]
    confidence: float
    regime_strength: float
    regime_persistence: float
    strategy_suitability: Dict[str, float]
    regime_factors: Dict[str, float]
    timestamp: datetime
    
class UnifiedRegimeDetector:
    """
    Unified market regime detection system for all trading strategies.
    
    Uses multiple indicators and statistical measures to classify
    market conditions and provide strategy-specific guidance.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Detection parameters
        self.lookback_short = self.config.get('lookback_short', 20)
        self.lookback_medium = self.config.get('lookback_medium', 50)
        self.lookback_long = self.config.get('lookback_long', 100)
        
        # Regime thresholds
        self.trend_threshold = self.config.get('trend_threshold', 0.02)
        self.volatility_threshold_high = self.config.get('volatility_threshold_high', 1.5)
        self.volatility_threshold_low = self.config.get('volatility_threshold_low', 0.7)
        self.mean_reversion_threshold = self.config.get('mean_reversion_threshold', -0.15)
        
        # State tracking
        self.regime_history = []
        self.confidence_history = []
        self.regime_transitions = []
        
        logger.info("Unified regime detector initialized")
    
    def detect_regime(self, market_data: pd.DataFrame) -> RegimeDetectionResult:
        """
        Detect current market regime using comprehensive analysis.
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            RegimeDetectionResult with comprehensive regime analysis
        """
        try:
            if len(market_data) < self.lookback_short:
                return self._create_default_result()
            
            # Calculate all regime factors
            regime_factors = self._calculate_regime_factors(market_data)
            
            # Classify primary regime
            primary_regime = self._classify_primary_regime(regime_factors)
            
            # Detect secondary regime characteristics
            secondary_regime = self._detect_secondary_regime(regime_factors, primary_regime)
            
            # Calculate confidence and strength
            confidence = self._calculate_regime_confidence(regime_factors, primary_regime)
            regime_strength = self._calculate_regime_strength(regime_factors, primary_regime)
            regime_persistence = self._calculate_regime_persistence(primary_regime)
            
            # Calculate strategy suitability scores
            strategy_suitability = self._calculate_strategy_suitability(
                primary_regime, secondary_regime, regime_factors
            )
            
            # Create result
            result = RegimeDetectionResult(
                primary_regime=primary_regime,
                secondary_regime=secondary_regime,
                confidence=confidence,
                regime_strength=regime_strength,
                regime_persistence=regime_persistence,
                strategy_suitability=strategy_suitability,
                regime_factors=regime_factors,
                timestamp=datetime.now()
            )
            
            # Update history
            self._update_regime_history(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Regime detection failed: {e}")
            return self._create_default_result()
    
    def _calculate_regime_factors(self, market_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate all factors used for regime detection"""
        try:
            prices = market_data['close']
            returns = prices.pct_change().dropna()
            
            factors = {}
            
            # 1. Trend Analysis
            factors.update(self._calculate_trend_factors(prices, returns))
            
            # 2. Volatility Analysis
            factors.update(self._calculate_volatility_factors(returns))
            
            # 3. Mean Reversion Analysis
            factors.update(self._calculate_mean_reversion_factors(prices, returns))
            
            # 4. Momentum Analysis
            factors.update(self._calculate_momentum_factors(prices, returns))
            
            # 5. Volume Analysis (if available)
            if 'volume' in market_data.columns:
                factors.update(self._calculate_volume_factors(market_data))
            
            # 6. Market Microstructure
            factors.update(self._calculate_microstructure_factors(market_data))
            
            return factors
            
        except Exception as e:
            logger.error(f"Regime factor calculation failed: {e}")
            return {}
    
    def _calculate_trend_factors(self, prices: pd.Series, returns: pd.Series) -> Dict[str, float]:
        """Calculate trend-related factors"""
        factors = {}
        
        try:
            # Short, medium, long-term trends
            for period, name in [(self.lookback_short, 'short'), 
                               (self.lookback_medium, 'medium'), 
                               (self.lookback_long, 'long')]:
                if len(prices) >= period:
                    # Linear trend strength
                    recent_prices = prices.iloc[-period:]
                    x = np.arange(len(recent_prices))
                    slope, intercept = np.polyfit(x, recent_prices.values, 1)
                    trend_strength = slope / recent_prices.mean() * period  # Normalize
                    factors[f'trend_strength_{name}'] = trend_strength
                    
                    # Moving average position
                    ma = recent_prices.mean()
                    current_price = prices.iloc[-1]
                    ma_position = (current_price - ma) / ma
                    factors[f'ma_position_{name}'] = ma_position
            
            # Trend consistency (how often price is above/below MA)
            if len(prices) >= self.lookback_medium:
                ma_medium = prices.rolling(self.lookback_medium).mean()
                above_ma = (prices > ma_medium).astype(int)
                trend_consistency = abs(above_ma.iloc[-self.lookback_short:].mean() - 0.5) * 2
                factors['trend_consistency'] = trend_consistency
            
            # Directional movement strength
            if len(returns) >= self.lookback_short:
                positive_returns = (returns > 0).astype(int)
                directional_bias = abs(positive_returns.iloc[-self.lookback_short:].mean() - 0.5) * 2
                factors['directional_bias'] = directional_bias
            
        except Exception as e:
            logger.error(f"Trend factor calculation failed: {e}")
        
        return factors
    
    def _calculate_volatility_factors(self, returns: pd.Series) -> Dict[str, float]:
        """Calculate volatility-related factors"""
        factors = {}
        
        try:
            if len(returns) < 10:
                return factors
            
            # Current vs historical volatility
            current_vol = returns.iloc[-self.lookback_short:].std() if len(returns) >= self.lookback_short else returns.std()
            historical_vol = returns.std()
            vol_ratio = current_vol / historical_vol if historical_vol > 0 else 1.0
            factors['volatility_ratio'] = vol_ratio
            factors['current_volatility'] = current_vol
            factors['historical_volatility'] = historical_vol
            
            # Volatility clustering (GARCH-like effect)
            if len(returns) >= 20:
                vol_series = returns.rolling(5).std().dropna()
                vol_autocorr = vol_series.autocorr(lag=1) if len(vol_series) > 1 else 0
                factors['volatility_clustering'] = max(0, vol_autocorr)
            
            # Volatility regime classification
            if vol_ratio > self.volatility_threshold_high:
                factors['volatility_regime'] = 1.0  # High vol
            elif vol_ratio < self.volatility_threshold_low:
                factors['volatility_regime'] = -1.0  # Low vol
            else:
                factors['volatility_regime'] = 0.0  # Normal vol
            
            # Extreme move frequency
            if len(returns) >= self.lookback_medium:
                std_threshold = returns.std() * 2
                extreme_moves = (abs(returns) > std_threshold).sum()
                extreme_frequency = extreme_moves / len(returns)
                factors['extreme_move_frequency'] = extreme_frequency
            
        except Exception as e:
            logger.error(f"Volatility factor calculation failed: {e}")
        
        return factors
    
    def _calculate_mean_reversion_factors(self, prices: pd.Series, returns: pd.Series) -> Dict[str, float]:
        """Calculate mean reversion factors"""
        factors = {}
        
        try:
            # Autocorrelation of returns (negative = mean reverting)
            if len(returns) >= 20:
                autocorr_1 = returns.autocorr(lag=1) if len(returns) > 1 else 0
                factors['return_autocorr_1'] = autocorr_1
                
                # Multi-lag autocorrelation
                autocorr_sum = 0
                for lag in range(1, min(6, len(returns)//4)):
                    autocorr_lag = returns.autocorr(lag=lag)
                    if not pd.isna(autocorr_lag):
                        autocorr_sum += autocorr_lag
                factors['return_autocorr_sum'] = autocorr_sum
            
            # Price mean reversion tendency
            if len(prices) >= self.lookback_medium:
                # Distance from long-term mean
                long_mean = prices.iloc[-self.lookback_medium:].mean()
                current_price = prices.iloc[-1]
                mean_distance = (current_price - long_mean) / long_mean
                factors['mean_distance'] = mean_distance
                
                # Mean reversion speed (how quickly price returns to mean)
                deviations = prices - prices.rolling(self.lookback_short).mean()
                deviations = deviations.dropna()
                if len(deviations) > 1:
                    # Simple AR(1) coefficient as proxy for mean reversion speed
                    lag_deviations = deviations.iloc[:-1].values
                    current_deviations = deviations.iloc[1:].values
                    if len(lag_deviations) > 0:
                        correlation = np.corrcoef(lag_deviations, current_deviations)[0, 1]
                        if not np.isnan(correlation):
                            factors['mean_reversion_speed'] = -correlation  # Negative correlation = mean reversion
            
            # Bollinger Band position
            if len(prices) >= self.lookback_short:
                rolling_mean = prices.rolling(self.lookback_short).mean()
                rolling_std = prices.rolling(self.lookback_short).std()
                current_price = prices.iloc[-1]
                current_mean = rolling_mean.iloc[-1]
                current_std = rolling_std.iloc[-1]
                
                if current_std > 0:
                    bb_position = (current_price - current_mean) / (2 * current_std)
                    factors['bollinger_position'] = bb_position
                    factors['bollinger_extreme'] = abs(bb_position)
            
        except Exception as e:
            logger.error(f"Mean reversion factor calculation failed: {e}")
        
        return factors
    
    def _calculate_momentum_factors(self, prices: pd.Series, returns: pd.Series) -> Dict[str, float]:
        """Calculate momentum factors"""
        factors = {}
        
        try:
            # Multi-period momentum
            for period, name in [(self.lookback_short, 'short'), 
                               (self.lookback_medium, 'medium'), 
                               (self.lookback_long, 'long')]:
                if len(prices) >= period:
                    momentum = (prices.iloc[-1] - prices.iloc[-period]) / prices.iloc[-period]
                    factors[f'momentum_{name}'] = momentum
            
            # Momentum consistency
            if len(returns) >= self.lookback_short:
                # What percentage of recent returns are in the same direction?
                recent_returns = returns.iloc[-self.lookback_short:]
                if len(recent_returns) > 0:
                    total_return = recent_returns.sum()
                    direction = 1 if total_return > 0 else -1
                    consistent_returns = (recent_returns * direction > 0).sum()
                    momentum_consistency = consistent_returns / len(recent_returns)
                    factors['momentum_consistency'] = momentum_consistency
            
            # Momentum acceleration
            if len(prices) >= self.lookback_medium:
                # Compare recent momentum to earlier momentum
                half_period = self.lookback_medium // 2
                early_momentum = (prices.iloc[-half_period] - prices.iloc[-self.lookback_medium]) / prices.iloc[-self.lookback_medium]
                recent_momentum = (prices.iloc[-1] - prices.iloc[-half_period]) / prices.iloc[-half_period]
                
                if abs(early_momentum) > 0.001:  # Avoid division by very small numbers
                    momentum_acceleration = recent_momentum / early_momentum
                    factors['momentum_acceleration'] = momentum_acceleration
            
        except Exception as e:
            logger.error(f"Momentum factor calculation failed: {e}")
        
        return factors
    
    def _calculate_volume_factors(self, market_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate volume-related factors"""
        factors = {}
        
        try:
            volume = market_data['volume']
            prices = market_data['close']
            
            if len(volume) < 10:
                return factors
            
            # Volume trend
            recent_volume = volume.iloc[-self.lookback_short:].mean() if len(volume) >= self.lookback_short else volume.mean()
            historical_volume = volume.mean()
            volume_ratio = recent_volume / historical_volume if historical_volume > 0 else 1.0
            factors['volume_ratio'] = volume_ratio
            
            # Price-volume relationship
            if len(prices) >= 10 and len(volume) >= 10:
                price_changes = prices.pct_change().iloc[-10:]
                volume_changes = volume.pct_change().iloc[-10:]
                
                # Remove NaN values
                valid_data = ~(price_changes.isna() | volume_changes.isna())
                if valid_data.sum() >= 5:
                    clean_price_changes = price_changes[valid_data]
                    clean_volume_changes = volume_changes[valid_data]
                    
                    pv_correlation = clean_price_changes.corr(clean_volume_changes)
                    if not pd.isna(pv_correlation):
                        factors['price_volume_correlation'] = pv_correlation
            
            # Volume breakout detection
            if len(volume) >= self.lookback_medium:
                volume_std = volume.iloc[-self.lookback_medium:].std()
                volume_mean = volume.iloc[-self.lookback_medium:].mean()
                current_volume = volume.iloc[-1]
                
                if volume_std > 0:
                    volume_zscore = (current_volume - volume_mean) / volume_std
                    factors['volume_breakout'] = max(0, volume_zscore - 2)  # Only positive breakouts
            
        except Exception as e:
            logger.error(f"Volume factor calculation failed: {e}")
        
        return factors
    
    def _calculate_microstructure_factors(self, market_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate market microstructure factors"""
        factors = {}
        
        try:
            if 'high' not in market_data.columns or 'low' not in market_data.columns:
                return factors
            
            high = market_data['high']
            low = market_data['low']
            close = market_data['close']
            
            # True Range and ATR
            if len(market_data) >= 2:
                prev_close = close.shift(1)
                true_range = pd.DataFrame({
                    'hl': high - low,
                    'hc': abs(high - prev_close),
                    'lc': abs(low - prev_close)
                }).max(axis=1)
                
                atr = true_range.rolling(self.lookback_short).mean()
                current_atr = atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else 0
                historical_atr = atr.mean() if len(atr.dropna()) > 0 else current_atr
                
                if historical_atr > 0:
                    atr_ratio = current_atr / historical_atr
                    factors['atr_ratio'] = atr_ratio
            
            # Intraday range analysis
            if len(high) >= self.lookback_short:
                intraday_range = (high - low) / close
                avg_range = intraday_range.iloc[-self.lookback_short:].mean()
                historical_range = intraday_range.mean()
                
                if historical_range > 0:
                    range_ratio = avg_range / historical_range
                    factors['intraday_range_ratio'] = range_ratio
            
        except Exception as e:
            logger.error(f"Microstructure factor calculation failed: {e}")
        
        return factors
    
    def _classify_primary_regime(self, factors: Dict[str, float]) -> MarketRegime:
        """Classify the primary market regime based on factors"""
        try:
            # Get key factors with defaults
            trend_strength_short = factors.get('trend_strength_short', 0)
            trend_strength_medium = factors.get('trend_strength_medium', 0)
            volatility_ratio = factors.get('volatility_ratio', 1.0)
            return_autocorr_1 = factors.get('return_autocorr_1', 0)
            momentum_consistency = factors.get('momentum_consistency', 0.5)
            
            # Classification logic
            
            # 1. High Volatility Regime (overrides other classifications)
            if volatility_ratio > self.volatility_threshold_high:
                return MarketRegime.HIGH_VOLATILITY
            
            # 2. Strong Trending Regimes
            avg_trend_strength = (abs(trend_strength_short) + abs(trend_strength_medium)) / 2
            if avg_trend_strength > self.trend_threshold:
                if trend_strength_short > 0 and trend_strength_medium > 0:
                    return MarketRegime.TRENDING_UP
                elif trend_strength_short < 0 and trend_strength_medium < 0:
                    return MarketRegime.TRENDING_DOWN
            
            # 3. Mean Reverting Regime
            if return_autocorr_1 < self.mean_reversion_threshold:
                return MarketRegime.MEAN_REVERTING
            
            # 4. Low Volatility Regime
            if volatility_ratio < self.volatility_threshold_low:
                return MarketRegime.LOW_VOLATILITY
            
            # 5. Breakout Detection
            volume_breakout = factors.get('volume_breakout', 0)
            atr_ratio = factors.get('atr_ratio', 1.0)
            if volume_breakout > 1 and atr_ratio > 1.3:
                return MarketRegime.BREAKOUT
            
            # 6. Default to Sideways
            return MarketRegime.SIDEWAYS
            
        except Exception as e:
            logger.error(f"Primary regime classification failed: {e}")
            return MarketRegime.UNKNOWN
    
    def _detect_secondary_regime(self, factors: Dict[str, float], primary_regime: MarketRegime) -> Optional[MarketRegime]:
        """Detect secondary regime characteristics"""
        try:
            # Look for secondary characteristics that don't match primary
            volatility_ratio = factors.get('volatility_ratio', 1.0)
            return_autocorr_1 = factors.get('return_autocorr_1', 0)
            
            secondary_regimes = []
            
            # Check for volatility characteristics
            if primary_regime != MarketRegime.HIGH_VOLATILITY and volatility_ratio > 1.2:
                secondary_regimes.append(MarketRegime.HIGH_VOLATILITY)
            elif primary_regime != MarketRegime.LOW_VOLATILITY and volatility_ratio < 0.8:
                secondary_regimes.append(MarketRegime.LOW_VOLATILITY)
            
            # Check for mean reversion characteristics
            if primary_regime != MarketRegime.MEAN_REVERTING and return_autocorr_1 < -0.1:
                secondary_regimes.append(MarketRegime.MEAN_REVERTING)
            
            # Return the strongest secondary regime
            return secondary_regimes[0] if secondary_regimes else None
            
        except Exception as e:
            logger.error(f"Secondary regime detection failed: {e}")
            return None
    
    def _calculate_regime_confidence(self, factors: Dict[str, float], regime: MarketRegime) -> float:
        """Calculate confidence in the regime classification"""
        try:
            confidence_factors = []
            
            # Factor-specific confidence calculations
            if regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
                trend_consistency = factors.get('trend_consistency', 0)
                momentum_consistency = factors.get('momentum_consistency', 0.5)
                confidence_factors.extend([trend_consistency, momentum_consistency])
            
            elif regime == MarketRegime.MEAN_REVERTING:
                autocorr_strength = abs(factors.get('return_autocorr_1', 0))
                bollinger_extreme = factors.get('bollinger_extreme', 0)
                confidence_factors.extend([autocorr_strength * 2, bollinger_extreme])
            
            elif regime in [MarketRegime.HIGH_VOLATILITY, MarketRegime.LOW_VOLATILITY]:
                vol_ratio = factors.get('volatility_ratio', 1.0)
                vol_deviation = abs(vol_ratio - 1.0)
                confidence_factors.append(min(1.0, vol_deviation))
            
            # Base confidence
            if confidence_factors:
                confidence = sum(confidence_factors) / len(confidence_factors)
            else:
                confidence = 0.5
            
            # Adjust based on data quality
            data_quality = min(1.0, len(factors) / 15)  # Expect ~15 factors
            confidence *= data_quality
            
            return max(0.1, min(0.95, confidence))
            
        except Exception as e:
            logger.error(f"Regime confidence calculation failed: {e}")
            return 0.5
    
    def _calculate_regime_strength(self, factors: Dict[str, float], regime: MarketRegime) -> float:
        """Calculate the strength of the current regime"""
        try:
            if regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
                trend_strength = abs(factors.get('trend_strength_medium', 0))
                return min(1.0, trend_strength / self.trend_threshold)
            
            elif regime == MarketRegime.MEAN_REVERTING:
                autocorr_strength = abs(factors.get('return_autocorr_1', 0))
                return min(1.0, autocorr_strength / abs(self.mean_reversion_threshold))
            
            elif regime == MarketRegime.HIGH_VOLATILITY:
                vol_ratio = factors.get('volatility_ratio', 1.0)
                return min(1.0, (vol_ratio - 1.0) / (self.volatility_threshold_high - 1.0))
            
            elif regime == MarketRegime.LOW_VOLATILITY:
                vol_ratio = factors.get('volatility_ratio', 1.0)
                return min(1.0, (1.0 - vol_ratio) / (1.0 - self.volatility_threshold_low))
            
            else:
                return 0.5
                
        except Exception as e:
            logger.error(f"Regime strength calculation failed: {e}")
            return 0.5
    
    def _calculate_regime_persistence(self, current_regime: MarketRegime) -> float:
        """Calculate how persistent the current regime has been"""
        try:
            if len(self.regime_history) < 2:
                return 0.5
            
            # Count consecutive occurrences of current regime
            consecutive_count = 0
            for result in reversed(self.regime_history[-10:]):  # Look at last 10
                if result.primary_regime == current_regime:
                    consecutive_count += 1
                else:
                    break
            
            # Normalize to 0-1 scale
            persistence = min(1.0, consecutive_count / 5)  # 5+ consecutive = max persistence
            return persistence
            
        except Exception as e:
            logger.error(f"Regime persistence calculation failed: {e}")
            return 0.5
    
    def _calculate_strategy_suitability(self, 
                                      primary_regime: MarketRegime,
                                      secondary_regime: Optional[MarketRegime],
                                      factors: Dict[str, float]) -> Dict[str, float]:
        """Calculate suitability scores for each trading strategy"""
        try:
            suitability = {
                'momentum': 0.5,
                'mean_reversion': 0.5,
                'pairs_trading': 0.5
            }
            
            # Momentum strategy suitability
            if primary_regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
                suitability['momentum'] = 0.9
            elif primary_regime == MarketRegime.BREAKOUT:
                suitability['momentum'] = 0.8
            elif primary_regime == MarketRegime.HIGH_VOLATILITY:
                suitability['momentum'] = 0.3  # High volatility can cause whipsaws
            elif primary_regime == MarketRegime.MEAN_REVERTING:
                suitability['momentum'] = 0.2  # Poor for momentum
            
            # Mean reversion strategy suitability
            if primary_regime == MarketRegime.MEAN_REVERTING:
                suitability['mean_reversion'] = 0.9
            elif primary_regime == MarketRegime.LOW_VOLATILITY:
                suitability['mean_reversion'] = 0.7
            elif primary_regime == MarketRegime.SIDEWAYS:
                suitability['mean_reversion'] = 0.6
            elif primary_regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
                suitability['mean_reversion'] = 0.1  # Poor in strong trends
            elif primary_regime == MarketRegime.HIGH_VOLATILITY:
                suitability['mean_reversion'] = 0.4  # Moderate in high vol
            
            # Pairs trading suitability (generally more stable)
            if primary_regime == MarketRegime.MEAN_REVERTING:
                suitability['pairs_trading'] = 0.9
            elif primary_regime == MarketRegime.LOW_VOLATILITY:
                suitability['pairs_trading'] = 0.8
            elif primary_regime == MarketRegime.SIDEWAYS:
                suitability['pairs_trading'] = 0.8
            elif primary_regime == MarketRegime.HIGH_VOLATILITY:
                suitability['pairs_trading'] = 0.6  # Correlations can break down
            else:
                suitability['pairs_trading'] = 0.7  # Generally robust
            
            # Adjust based on secondary regime
            if secondary_regime:
                # Reduce suitability if conflicting regimes
                for strategy in suitability:
                    suitability[strategy] *= 0.9
            
            # Ensure all scores are in valid range
            for strategy in suitability:
                suitability[strategy] = max(0.1, min(0.95, suitability[strategy]))
            
            return suitability
            
        except Exception as e:
            logger.error(f"Strategy suitability calculation failed: {e}")
            return {'momentum': 0.5, 'mean_reversion': 0.5, 'pairs_trading': 0.5}
    
    def _update_regime_history(self, result: RegimeDetectionResult):
        """Update regime history for persistence tracking"""
        try:
            self.regime_history.append(result)
            self.confidence_history.append(result.confidence)
            
            # Keep history manageable
            max_history = 100
            if len(self.regime_history) > max_history:
                self.regime_history = self.regime_history[-max_history:]
                self.confidence_history = self.confidence_history[-max_history:]
            
            # Track regime transitions
            if len(self.regime_history) >= 2:
                prev_regime = self.regime_history[-2].primary_regime
                current_regime = result.primary_regime
                
                if prev_regime != current_regime:
                    transition = {
                        'from': prev_regime,
                        'to': current_regime,
                        'timestamp': result.timestamp,
                        'confidence': result.confidence
                    }
                    self.regime_transitions.append(transition)
                    
                    # Keep transition history manageable
                    if len(self.regime_transitions) > 50:
                        self.regime_transitions = self.regime_transitions[-50:]
            
        except Exception as e:
            logger.error(f"Regime history update failed: {e}")
    
    def _create_default_result(self) -> RegimeDetectionResult:
        """Create a default result when detection fails"""
        return RegimeDetectionResult(
            primary_regime=MarketRegime.UNKNOWN,
            secondary_regime=None,
            confidence=0.5,
            regime_strength=0.5,
            regime_persistence=0.5,
            strategy_suitability={'momentum': 0.5, 'mean_reversion': 0.5, 'pairs_trading': 0.5},
            regime_factors={},
            timestamp=datetime.now()
        )
    
    def get_regime_summary(self) -> Dict[str, Any]:
        """Get a summary of recent regime analysis"""
        try:
            if not self.regime_history:
                return {'status': 'no_data'}
            
            latest = self.regime_history[-1]
            
            # Recent regime distribution
            recent_regimes = [r.primary_regime for r in self.regime_history[-10:]]
            regime_counts = {}
            for regime in recent_regimes:
                regime_counts[regime.value] = regime_counts.get(regime.value, 0) + 1
            
            # Average confidence
            avg_confidence = sum(self.confidence_history[-10:]) / len(self.confidence_history[-10:])
            
            return {
                'status': 'active',
                'current_regime': latest.primary_regime.value,
                'secondary_regime': latest.secondary_regime.value if latest.secondary_regime else None,
                'confidence': latest.confidence,
                'regime_strength': latest.regime_strength,
                'persistence': latest.regime_persistence,
                'strategy_suitability': latest.strategy_suitability,
                'recent_regime_distribution': regime_counts,
                'average_confidence': avg_confidence,
                'recent_transitions': len(self.regime_transitions[-5:]),
                'timestamp': latest.timestamp.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Regime summary generation failed: {e}")
            return {'status': 'error', 'message': str(e)}

# Global regime detector instance
_global_regime_detector = None

def get_regime_detector(config: Optional[Dict[str, Any]] = None) -> UnifiedRegimeDetector:
    """Get the global regime detector instance"""
    global _global_regime_detector
    
    if _global_regime_detector is None:
        _global_regime_detector = UnifiedRegimeDetector(config)
    
    return _global_regime_detector

def detect_market_regime(market_data: pd.DataFrame) -> RegimeDetectionResult:
    """Convenience function to detect market regime"""
    detector = get_regime_detector()
    return detector.detect_regime(market_data)
