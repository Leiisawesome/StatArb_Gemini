#!/usr/bin/env python3
"""
Unified Momentum Strategy - Consolidated Implementation
======================================================

Consolidated momentum strategy combining functionality from:
- trade_engine/strategies/momentum_strategy.py
- trade_engine/templates/momentum_template.py
- Enhanced with unified strategy system features

This implementation provides comprehensive momentum-based trading
with template support and enhanced configuration management.

Author: Professional Trading System Architecture
Version: 2.0.0 (Unified)
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import unified strategy framework
from .unified_strategy_system import (
    EnhancedBaseStrategy, TemplateBasedStrategy, StrategyParameters,
    UnifiedStrategyConfig, StrategyResult, StrategyStatus
)

# Import base interfaces
from ..interfaces.strategy_interfaces import StrategyType, StrategyContext, StrategyMetrics

# Import signal types
from ..components.signal_generation import TradingSignal, SignalType, SignalStrength

# Import regime detection
from ..components.market_regime import detect_market_regime, MarketRegime

logger = logging.getLogger(__name__)

# ================================================================================
# MOMENTUM STRATEGY IMPLEMENTATION
# ================================================================================

class MomentumStrategy(EnhancedBaseStrategy):
    """
    Unified momentum strategy implementation.
    
    Features:
    - Multi-period momentum analysis
    - Confidence-based signal generation
    - Dynamic position sizing
    - Template configuration support
    - Enhanced risk management integration
    """
    
    # Class metadata
    SUPPORTED_MODES = ["backtest", "paper_trading", "live_trading"]
    STRATEGY_VERSION = "2.0.0"
    
    def __init__(self, strategy_id: str, config: UnifiedStrategyConfig):
        super().__init__(strategy_id, config)
        
        # Momentum-specific parameters
        self.lookback_periods = getattr(self.parameters, 'lookback_periods', [10, 20, 50])
        self.momentum_threshold = getattr(self.parameters, 'momentum_threshold', 0.02)
        self.confidence_threshold = getattr(self.parameters, 'confidence_threshold', 0.6)
        self.volume_threshold = getattr(self.parameters, 'volume_threshold', 1.2)
        
        # Enhanced momentum parameters
        self.momentum_weights = getattr(self.parameters, 'momentum_weights', [0.5, 0.3, 0.2])
        self.trend_filter = getattr(self.parameters, 'trend_filter', True)
        self.volatility_adjustment = getattr(self.parameters, 'volatility_adjustment', True)
        
        # Advanced optimization features
        self.regime_awareness = getattr(self.parameters, 'regime_awareness', True)
        self.adaptive_thresholds = getattr(self.parameters, 'adaptive_thresholds', True)
        self.ml_enhancement = getattr(self.parameters, 'ml_enhancement', False)
        self.kalman_filter = getattr(self.parameters, 'kalman_filter', False)
        
        # Enhanced signal quality features
        self.signal_quality_filter = getattr(self.parameters, 'signal_quality_filter', True)
        self.min_signal_quality = getattr(self.parameters, 'min_signal_quality', 0.6)
        self.cross_timeframe_confirmation = getattr(self.parameters, 'cross_timeframe_confirmation', True)
        
        # Dynamic stop-loss features
        self.dynamic_stops = getattr(self.parameters, 'dynamic_stops', True)
        self.atr_stop_multiplier = getattr(self.parameters, 'atr_stop_multiplier', 2.0)
        self.regime_based_stops = getattr(self.parameters, 'regime_based_stops', True)
        
        # Dynamic parameter optimization
        self.parameter_history = []
        self.performance_history = []
        self.optimization_frequency = getattr(self.parameters, 'optimization_frequency', 50)  # Every 50 signals
        
        # Regime detection parameters
        self.regime_lookback = getattr(self.parameters, 'regime_lookback', 252)
        self.current_regime = 'unknown'
        self.regime_confidence = 0.5
        
        logger.info(f"Momentum strategy initialized: {strategy_id}")
    
    def _calculate_volatility_adjusted_position_size(self, market_data: pd.DataFrame, 
                                                   base_size: float, confidence: float) -> float:
        """Calculate position size adjusted for volatility with enhanced logic"""
        try:
            if len(market_data) < 20:
                return base_size * confidence
            
            returns = market_data['close'].pct_change().dropna()
            if len(returns) < 10:
                return base_size * confidence
            
            # Current volatility (20-day)
            current_vol = returns.iloc[-20:].std() if len(returns) >= 20 else returns.std()
            
            # Historical volatility (longer period for comparison)
            historical_vol = returns.std() if len(returns) >= 50 else current_vol
            
            # Target volatility (2% daily)
            target_vol = 0.02
            
            # Volatility ratio adjustment
            if historical_vol > 0:
                vol_ratio = current_vol / historical_vol
                
                # More conservative in high volatility, more aggressive in low volatility
                if vol_ratio > 1.5:  # High volatility regime
                    vol_adjustment = max(0.4, target_vol / current_vol)
                elif vol_ratio < 0.7:  # Low volatility regime  
                    vol_adjustment = min(1.5, target_vol / current_vol)
                else:  # Normal volatility
                    vol_adjustment = target_vol / current_vol
                
                # Cap the adjustment to reasonable bounds
                vol_adjustment = max(0.3, min(2.0, vol_adjustment))
            else:
                vol_adjustment = 1.0
            
            # Apply confidence and volatility adjustments
            adjusted_size = base_size * vol_adjustment * confidence
            
            # Additional momentum-specific adjustment based on trend strength
            momentum_adjustment = min(1.2, max(0.8, confidence * 1.5))
            adjusted_size *= momentum_adjustment
            
            return adjusted_size
            
        except Exception as e:
            logger.error(f"Volatility adjustment calculation failed: {e}")
            return base_size * confidence
    
    def _calculate_momentum_quality(self, prices: pd.Series, period: int) -> Dict[str, float]:
        """Calculate momentum quality metrics (consistency and strength)"""
        try:
            if len(prices) < period:
                return {'consistency': 0.0, 'strength': 0.0, 'acceleration': 0.0}
            
            # Calculate returns for the period
            returns = prices.pct_change().dropna()
            recent_returns = returns.tail(period)
            
            if len(recent_returns) < 5:
                return {'consistency': 0.0, 'strength': 0.0, 'acceleration': 0.0}
            
            # Momentum direction
            total_momentum = (prices.iloc[-1] - prices.iloc[-period]) / prices.iloc[-period]
            momentum_direction = 1 if total_momentum > 0 else -1
            
            # Consistency: % of returns in the same direction as overall momentum
            consistent_returns = (recent_returns * momentum_direction > 0).sum()
            consistency = consistent_returns / len(recent_returns)
            
            # Strength: magnitude of average return
            avg_return = abs(recent_returns.mean())
            strength = min(1.0, avg_return * 100)  # Scale to 0-1
            
            # Acceleration: is momentum increasing?
            half_period = max(1, period // 2)
            if len(prices) >= period:
                early_momentum = (prices.iloc[-half_period] - prices.iloc[-period]) / prices.iloc[-period]
                recent_momentum = (prices.iloc[-1] - prices.iloc[-half_period]) / prices.iloc[-half_period]
                acceleration = 1.0 if recent_momentum > early_momentum else 0.5
            else:
                acceleration = 0.5
            
            return {
                'consistency': consistency,
                'strength': strength,
                'acceleration': acceleration
            }
            
        except Exception as e:
            logger.error(f"Momentum quality calculation failed: {e}")
            return {'consistency': 0.0, 'strength': 0.0, 'acceleration': 0.0}
    
    def _check_volume_confirmation(self, market_data: pd.DataFrame, momentum_signal: float) -> bool:
        """Check if volume confirms the momentum signal"""
        try:
            if 'volume' not in market_data.columns or len(market_data) < 20:
                return True  # No volume data available, don't filter
            
            volume = market_data['volume']
            prices = market_data['close']
            
            # Calculate volume trend (recent vs historical average)
            recent_volume = volume.iloc[-5:].mean()  # Last 5 periods
            historical_volume = volume.iloc[-20:].mean()  # Last 20 periods
            
            if historical_volume <= 0:
                return True  # Avoid division by zero
            
            volume_ratio = recent_volume / historical_volume
            
            # Calculate price-volume relationship
            recent_returns = prices.pct_change().iloc[-5:]
            recent_volume_changes = volume.pct_change().iloc[-5:]
            
            # Remove NaN values
            valid_data = ~(recent_returns.isna() | recent_volume_changes.isna())
            if valid_data.sum() < 3:
                return True  # Not enough data
            
            clean_returns = recent_returns[valid_data]
            clean_volume_changes = recent_volume_changes[valid_data]
            
            # Volume confirmation criteria
            volume_threshold = self.volume_threshold  # From parameters (default 1.2)
            
            # 1. Volume should be above average for strong momentum
            if abs(momentum_signal) > self.momentum_threshold * 1.5:
                if volume_ratio < volume_threshold:
                    logger.debug(f"Strong momentum signal rejected: insufficient volume {volume_ratio:.2f} < {volume_threshold}")
                    return False
            
            # 2. Price and volume should move in the same direction (for momentum)
            if len(clean_returns) >= 3:
                avg_return = clean_returns.mean()
                avg_volume_change = clean_volume_changes.mean()
                
                # For momentum strategies, we want volume to increase with price moves
                if abs(avg_return) > 0.01:  # Significant price movement
                    if momentum_signal > 0 and avg_return > 0:  # Upward momentum
                        if avg_volume_change < -0.1:  # But volume is decreasing significantly
                            logger.debug("Upward momentum rejected: decreasing volume")
                            return False
                    elif momentum_signal < 0 and avg_return < 0:  # Downward momentum
                        if avg_volume_change < -0.1:  # But volume is decreasing significantly
                            logger.debug("Downward momentum rejected: decreasing volume")
                            return False
            
            # 3. Check for volume spikes that might indicate false breakouts
            max_recent_volume = volume.iloc[-5:].max()
            if max_recent_volume > historical_volume * 3:  # Volume spike > 3x average
                # This could be a false breakout, be more cautious
                if abs(momentum_signal) < self.momentum_threshold * 2:
                    logger.debug("Momentum signal rejected: potential false breakout (volume spike)")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Volume confirmation check failed: {e}")
            return True  # Don't filter on error
    
    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.MOMENTUM
    
    @property
    def required_indicators(self) -> List[str]:
        return ['close', 'volume', 'high', 'low']
    
    def _get_required_parameters(self) -> List[str]:
        return [
            'momentum_threshold', 'confidence_threshold', 'position_size',
            'lookback_periods', 'momentum_weights'
        ]
    
    async def _generate_strategy_signals(self, context: StrategyContext) -> List[TradingSignal]:
        """Generate momentum-based trading signals"""
        signals = []
        
        try:
            market_data = context.market_data
            
            if len(market_data) < max(self.lookback_periods):
                logger.debug(f"Insufficient data for momentum analysis: {len(market_data)} < {max(self.lookback_periods)}")
                return signals
            
            # Calculate multi-period momentum
            momentum_scores = self._calculate_momentum_scores(market_data)
            
            # Calculate confidence score
            confidence = self._calculate_confidence(market_data, momentum_scores)
            
            # Apply filters
            if not self._passes_filters(market_data, momentum_scores, confidence):
                return signals
            
            # Enhanced signal quality filter
            if self.signal_quality_filter:
                signal_quality = self._calculate_signal_quality(market_data, momentum_scores)
                if signal_quality < self.min_signal_quality:
                    logger.debug(f"Signal filtered out due to low quality: {signal_quality:.2f} < {self.min_signal_quality}")
                    return signals
            
            # Generate signal
            signal = self._create_momentum_signal(
                context, momentum_scores, confidence, market_data
            )
            
            if signal:
                signals.append(signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"Momentum signal generation failed: {e}")
            return []
    
    def _calculate_momentum_scores(self, market_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate enhanced multi-period momentum scores with advanced features"""
        try:
            prices = market_data['close']
            momentum_scores = {}
            
            # Detect current market regime
            if self.regime_awareness:
                regime_info = self._detect_market_regime(market_data)
                self.current_regime = regime_info['regime']
                self.regime_confidence = regime_info['confidence']
                momentum_scores.update(regime_info)
            
            # Calculate adaptive thresholds based on volatility
            if self.adaptive_thresholds:
                adaptive_threshold = self._calculate_adaptive_threshold(market_data)
                momentum_scores['adaptive_threshold'] = adaptive_threshold
            
            # Enhanced momentum calculation with quality assessment
            for i, period in enumerate(self.lookback_periods):
                if len(prices) >= period:
                    # Basic momentum
                    momentum = (prices.iloc[-1] - prices.iloc[-period]) / prices.iloc[-period]
                    
                    # Calculate momentum quality (consistency and acceleration)
                    quality_metrics = self._calculate_momentum_quality(prices, period)
                    
                    # Adjust momentum based on quality
                    quality_factor = (quality_metrics['consistency'] * 0.6 + 
                                    quality_metrics['strength'] * 0.4)
                    adjusted_momentum = momentum * quality_factor
                    
                    # Apply Kalman filter if enabled
                    if self.kalman_filter:
                        adjusted_momentum = self._apply_kalman_filter(adjusted_momentum, f'momentum_{period}')
                    
                    # Regime adjustment
                    if self.regime_awareness:
                        adjusted_momentum = self._adjust_for_regime(adjusted_momentum, self.current_regime)
                    
                    momentum_scores[f'momentum_{period}'] = adjusted_momentum
                    momentum_scores[f'quality_{period}'] = quality_factor
                else:
                    momentum_scores[f'momentum_{period}'] = 0.0
                    momentum_scores[f'quality_{period}'] = 0.0
            
            # Calculate weighted average momentum with dynamic weights
            if self.adaptive_thresholds:
                weights = self._calculate_dynamic_weights(market_data)
            else:
                weights = self.momentum_weights
            
            total_momentum = 0.0
            total_weight = 0.0
            
            for i, period in enumerate(self.lookback_periods):
                if i < len(weights):
                    weight = weights[i]
                    momentum = momentum_scores.get(f'momentum_{period}', 0.0)
                    total_momentum += momentum * weight
                    total_weight += weight
            
            if total_weight > 0:
                momentum_scores['weighted_momentum'] = total_momentum / total_weight
            else:
                momentum_scores['weighted_momentum'] = 0.0
            
            # Add ML enhancement if enabled
            if self.ml_enhancement:
                ml_score = self._calculate_ml_momentum_score(market_data, momentum_scores)
                momentum_scores['ml_enhanced_momentum'] = ml_score
                # Use ML score as primary if available
                if ml_score != 0.0:
                    momentum_scores['weighted_momentum'] = ml_score
            
            return momentum_scores
            
        except Exception as e:
            logger.error(f"Enhanced momentum calculation failed: {e}")
            return {'weighted_momentum': 0.0}
    
    def _calculate_confidence(self, market_data: pd.DataFrame, momentum_scores: Dict[str, float]) -> float:
        """Calculate confidence score for momentum signal"""
        try:
            confidence_factors = []
            
            # Factor 1: Momentum consistency across periods
            momentum_values = [
                momentum_scores.get(f'momentum_{period}', 0.0)
                for period in self.lookback_periods
            ]
            
            if momentum_values:
                # Check if all momentum values have same sign (consistent direction)
                signs = [1 if m > 0 else -1 if m < 0 else 0 for m in momentum_values]
                consistency = abs(sum(signs)) / len(signs) if signs else 0
                confidence_factors.append(consistency)
            
            # Factor 2: Volume confirmation
            if 'volume' in market_data.columns and len(market_data) >= 20:
                recent_volume = market_data['volume'].iloc[-5:].mean()
                avg_volume = market_data['volume'].iloc[-20:].mean()
                volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1.0
                volume_confidence = min(volume_ratio / self.volume_threshold, 1.0)
                confidence_factors.append(volume_confidence)
            
            # Factor 3: Volatility consideration
            if len(market_data) >= 20:
                returns = market_data['close'].pct_change().dropna()
                if len(returns) >= 10:
                    recent_vol = returns.iloc[-10:].std()
                    avg_vol = returns.iloc[-20:].std()
                    vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 1.0
                    # Lower volatility increases confidence
                    vol_confidence = max(0.1, 1.0 - (vol_ratio - 1.0))
                    confidence_factors.append(vol_confidence)
            
            # Calculate overall confidence
            if confidence_factors:
                confidence = sum(confidence_factors) / len(confidence_factors)
                return min(max(confidence, 0.0), 1.0)
            else:
                return 0.5  # Default confidence
                
        except Exception as e:
            logger.error(f"Confidence calculation failed: {e}")
            return 0.5
    
    def _passes_filters(self, market_data: pd.DataFrame, momentum_scores: Dict[str, float], confidence: float) -> bool:
        """Apply filters to determine if signal should be generated"""
        try:
            # Check momentum threshold
            weighted_momentum = momentum_scores.get('weighted_momentum', 0.0)
            if abs(weighted_momentum) < self.momentum_threshold:
                return False
            
            # Check confidence threshold
            if confidence < self.confidence_threshold:
                return False
            
            # Volume confirmation filter
            volume_confirmation = self._check_volume_confirmation(market_data, weighted_momentum)
            if not volume_confirmation:
                return False
            
            # Trend filter (optional)
            if self.trend_filter and len(market_data) >= 50:
                # Check if price is above/below long-term moving average
                prices = market_data['close']
                long_ma = prices.iloc[-50:].mean()
                current_price = prices.iloc[-1]
                
                # For buy signals, price should be above long MA
                # For sell signals, price should be below long MA
                if weighted_momentum > 0 and current_price < long_ma:
                    return False
                elif weighted_momentum < 0 and current_price > long_ma:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Filter application failed: {e}")
            return False
    
    def _create_momentum_signal(self, 
                               context: StrategyContext,
                               momentum_scores: Dict[str, float],
                               confidence: float,
                               market_data: pd.DataFrame) -> Optional[TradingSignal]:
        """Create momentum trading signal"""
        try:
            weighted_momentum = momentum_scores.get('weighted_momentum', 0.0)
            
            # Determine signal direction
            if weighted_momentum > self.momentum_threshold:
                signal_type = SignalType.BUY
            elif weighted_momentum < -self.momentum_threshold:
                signal_type = SignalType.SELL
            else:
                return None
            
            # Determine signal strength
            momentum_strength = abs(weighted_momentum)
            if momentum_strength > self.momentum_threshold * 3:
                strength = SignalStrength.STRONG
            elif momentum_strength > self.momentum_threshold * 2:
                strength = SignalStrength.MEDIUM
            else:
                strength = SignalStrength.WEAK
            
            # Calculate enhanced volatility-adjusted position size
            base_position_size = self.parameters.position_size
            adjusted_position_size = self._calculate_volatility_adjusted_position_size(
                market_data, base_position_size, confidence
            )
            
            # Ensure position size is within limits
            adjusted_position_size = min(adjusted_position_size, self.parameters.max_position_size)
            
            # Calculate dynamic stop-loss levels
            stop_loss_data = self._calculate_dynamic_stop_loss(market_data, signal_type) if self.dynamic_stops else {}
            
            # Create signal
            signal = TradingSignal(
                symbol=getattr(context, 'symbol', 'UNKNOWN'),
                signal_type=signal_type,
                strength=strength,
                confidence=confidence,
                timestamp=context.timestamp or datetime.now(),
                quantity=adjusted_position_size,
                metadata={
                    'strategy_type': 'momentum',
                    'strategy_id': self.strategy_id,
                    'weighted_momentum': weighted_momentum,
                    'momentum_scores': momentum_scores,
                    'momentum_threshold': self.momentum_threshold,
                    'confidence_threshold': self.confidence_threshold,
                    'lookback_periods': self.lookback_periods,
                    'stop_loss_data': stop_loss_data,
                    'filters_applied': {
                        'trend_filter': self.trend_filter,
                        'volatility_adjustment': self.volatility_adjustment,
                        'signal_quality_filter': self.signal_quality_filter
                    }
                }
            )
            
            # Store performance data for optimization
            self._store_signal_for_optimization(signal, market_data)
            
            # Check if parameter optimization is needed
            if len(self.performance_history) % self.optimization_frequency == 0 and len(self.performance_history) > 0:
                self._optimize_parameters()
            
            return signal
            
        except Exception as e:
            logger.error(f"Signal creation failed: {e}")
            return None
    
    def _detect_market_regime(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Detect current market regime using multiple indicators"""
        try:
            prices = market_data['close']
            
            if len(prices) < 50:
                return {'regime': 'unknown', 'confidence': 0.5}
            
            # Calculate regime indicators
            returns = prices.pct_change().dropna()
            
            # Volatility regime
            short_vol = returns.iloc[-20:].std() if len(returns) >= 20 else 0
            long_vol = returns.iloc[-60:].std() if len(returns) >= 60 else short_vol
            vol_ratio = short_vol / long_vol if long_vol > 0 else 1.0
            
            # Trend regime
            short_ma = prices.iloc[-20:].mean() if len(prices) >= 20 else prices.iloc[-1]
            long_ma = prices.iloc[-50:].mean() if len(prices) >= 50 else short_ma
            trend_strength = (short_ma - long_ma) / long_ma if long_ma > 0 else 0
            
            # Mean reversion tendency
            autocorr = returns.iloc[-30:].autocorr() if len(returns) >= 30 else 0
            
            # Determine regime
            if abs(trend_strength) > 0.02 and vol_ratio < 1.2:
                regime = 'trending'
                confidence = min(0.9, 0.6 + abs(trend_strength) * 10)
            elif autocorr < -0.1:
                regime = 'mean_reverting'
                confidence = min(0.9, 0.6 + abs(autocorr) * 2)
            elif vol_ratio > 1.5:
                regime = 'volatile'
                confidence = min(0.9, 0.5 + (vol_ratio - 1.0) * 0.3)
            else:
                regime = 'sideways'
                confidence = 0.6
            
            return {
                'regime': regime,
                'confidence': confidence,
                'vol_ratio': vol_ratio,
                'trend_strength': trend_strength,
                'autocorr': autocorr
            }
            
        except Exception as e:
            logger.error(f"Regime detection failed: {e}")
            return {'regime': 'unknown', 'confidence': 0.5}
    
    def _calculate_adaptive_threshold(self, market_data: pd.DataFrame) -> float:
        """Calculate enhanced adaptive momentum threshold based on market conditions"""
        try:
            returns = market_data['close'].pct_change().dropna()
            
            if len(returns) < 20:
                return self.momentum_threshold
            
            # 1. Volatility-based adjustment
            recent_vol = returns.iloc[-20:].std()
            long_term_vol = returns.std() if len(returns) >= 50 else recent_vol
            
            vol_ratio = recent_vol / long_term_vol if long_term_vol > 0 else 1.0
            
            # 2. Market regime adjustment
            regime_adjustment = 1.0
            if hasattr(self, 'current_regime'):
                if self.current_regime == 'high_volatility':
                    regime_adjustment = 1.4  # Higher threshold in volatile markets
                elif self.current_regime == 'trending':
                    regime_adjustment = 0.8  # Lower threshold in trending markets
                elif self.current_regime == 'sideways':
                    regime_adjustment = 1.2  # Higher threshold in sideways markets
            
            # 3. Recent performance adjustment
            if hasattr(self, 'signal_history') and len(self.signal_history) >= 10:
                recent_success_rate = sum(1 for s in self.signal_history[-10:] if s.get('success', False)) / 10
                if recent_success_rate < 0.4:  # Poor recent performance
                    performance_adjustment = 1.3  # Raise threshold
                elif recent_success_rate > 0.7:  # Good recent performance
                    performance_adjustment = 0.9  # Lower threshold slightly
                else:
                    performance_adjustment = 1.0
            else:
                performance_adjustment = 1.0
            
            # Combine all adjustments
            total_adjustment = vol_ratio * regime_adjustment * performance_adjustment
            adaptive_threshold = self.momentum_threshold * total_adjustment
            
            # Keep within reasonable bounds (0.3x to 2.5x original)
            min_threshold = self.momentum_threshold * 0.3
            max_threshold = self.momentum_threshold * 2.5
            
            return max(min_threshold, min(adaptive_threshold, max_threshold))
            
        except Exception as e:
            logger.error(f"Enhanced adaptive threshold calculation failed: {e}")
            return self.momentum_threshold
    
    def _adjust_for_regime(self, momentum: float, regime: str) -> float:
        """Adjust momentum signal based on detected regime"""
        try:
            if regime == 'trending':
                # Boost momentum signals in trending markets
                return momentum * 1.2
            elif regime == 'mean_reverting':
                # Dampen momentum signals in mean-reverting markets
                return momentum * 0.7
            elif regime == 'volatile':
                # Reduce momentum signals in volatile markets
                return momentum * 0.8
            else:
                return momentum
                
        except Exception:
            return momentum
    
    def _calculate_dynamic_weights(self, market_data: pd.DataFrame) -> List[float]:
        """Calculate dynamic weights based on recent performance of different periods"""
        try:
            # Simplified dynamic weighting based on recent volatility
            returns = market_data['close'].pct_change().dropna()
            
            if len(returns) < 50:
                return self.momentum_weights
            
            # Calculate effectiveness of different periods
            weights = []
            for period in self.lookback_periods:
                if len(returns) >= period:
                    # Simple effectiveness measure: inverse of volatility
                    period_returns = returns.iloc[-period:]
                    effectiveness = 1.0 / (period_returns.std() + 0.001)  # Add small constant to avoid division by zero
                    weights.append(effectiveness)
                else:
                    weights.append(1.0)
            
            # Normalize weights
            total_weight = sum(weights)
            if total_weight > 0:
                weights = [w / total_weight for w in weights]
            else:
                weights = self.momentum_weights
            
            return weights
            
        except Exception as e:
            logger.error(f"Dynamic weight calculation failed: {e}")
            return self.momentum_weights
    
    def _apply_kalman_filter(self, value: float, series_name: str) -> float:
        """Apply simple Kalman filter to smooth momentum values"""
        try:
            # Simple Kalman filter implementation
            if not hasattr(self, '_kalman_states'):
                self._kalman_states = {}
            
            if series_name not in self._kalman_states:
                self._kalman_states[series_name] = {
                    'estimate': value,
                    'error_covariance': 1.0,
                    'process_noise': 0.01,
                    'measurement_noise': 0.1
                }
                return value
            
            state = self._kalman_states[series_name]
            
            # Prediction step
            predicted_estimate = state['estimate']
            predicted_error_covariance = state['error_covariance'] + state['process_noise']
            
            # Update step
            kalman_gain = predicted_error_covariance / (predicted_error_covariance + state['measurement_noise'])
            updated_estimate = predicted_estimate + kalman_gain * (value - predicted_estimate)
            updated_error_covariance = (1 - kalman_gain) * predicted_error_covariance
            
            # Store updated state
            state['estimate'] = updated_estimate
            state['error_covariance'] = updated_error_covariance
            
            return updated_estimate
            
        except Exception as e:
            logger.error(f"Kalman filter failed: {e}")
            return value
    
    def _calculate_ml_momentum_score(self, market_data: pd.DataFrame, momentum_scores: Dict[str, float]) -> float:
        """Calculate ML-enhanced momentum score (placeholder for future ML integration)"""
        try:
            # Placeholder for ML model integration
            # In a full implementation, this would use trained models
            
            # For now, return a composite score based on multiple factors
            weighted_momentum = momentum_scores.get('weighted_momentum', 0.0)
            regime_confidence = momentum_scores.get('confidence', 0.5)
            
            # Simple enhancement: boost signal if regime confidence is high
            ml_score = weighted_momentum * (1.0 + regime_confidence * 0.2)
            
            return ml_score
            
        except Exception as e:
            logger.error(f"ML momentum calculation failed: {e}")
            return 0.0
    
    def _store_signal_for_optimization(self, signal: TradingSignal, market_data: pd.DataFrame):
        """Store signal data for parameter optimization"""
        try:
            signal_data = {
                'timestamp': signal.timestamp,
                'confidence': signal.confidence,
                'strength': signal.strength.name,
                'regime': self.current_regime,
                'regime_confidence': self.regime_confidence,
                'parameters': {
                    'momentum_threshold': self.momentum_threshold,
                    'confidence_threshold': self.confidence_threshold,
                    'lookback_periods': self.lookback_periods.copy(),
                    'momentum_weights': self.momentum_weights.copy()
                }
            }
            
            self.parameter_history.append(signal_data)
            
            # Keep history manageable
            if len(self.parameter_history) > 1000:
                self.parameter_history = self.parameter_history[-1000:]
                
        except Exception as e:
            logger.error(f"Signal storage failed: {e}")
    
    def _optimize_parameters(self):
        """Optimize strategy parameters based on recent performance"""
        try:
            if len(self.parameter_history) < 20:
                return
            
            # Simple parameter optimization based on confidence scores
            recent_signals = self.parameter_history[-50:]
            avg_confidence = sum(s['confidence'] for s in recent_signals) / len(recent_signals)
            
            # If confidence is low, adjust parameters
            if avg_confidence < 0.6:
                # Reduce momentum threshold to generate more signals
                self.momentum_threshold *= 0.95
                self.momentum_threshold = max(self.momentum_threshold, 0.005)  # Minimum threshold
                
                logger.info(f"Momentum strategy parameter optimization: threshold adjusted to {self.momentum_threshold:.4f}")
            elif avg_confidence > 0.8:
                # Increase momentum threshold for higher quality signals
                self.momentum_threshold *= 1.05
                self.momentum_threshold = min(self.momentum_threshold, 0.05)  # Maximum threshold
                
                logger.info(f"Momentum strategy parameter optimization: threshold adjusted to {self.momentum_threshold:.4f}")
            
        except Exception as e:
            logger.error(f"Parameter optimization failed: {e}")
    
    def _calculate_signal_quality(self, market_data: pd.DataFrame, momentum_scores: Dict[str, float]) -> float:
        """Calculate comprehensive signal quality score"""
        try:
            quality_factors = []
            
            # 1. Trend Consistency Factor
            trend_consistency = self._check_trend_consistency(market_data)
            quality_factors.append(('trend_consistency', trend_consistency, 0.25))
            
            # 2. Volume-Momentum Alignment
            volume_alignment = self._check_volume_momentum_alignment(market_data, momentum_scores)
            quality_factors.append(('volume_alignment', volume_alignment, 0.20))
            
            # 3. Volatility Regime Suitability
            volatility_suitability = self._check_volatility_suitability(market_data)
            quality_factors.append(('volatility_suitability', volatility_suitability, 0.20))
            
            # 4. Cross-Timeframe Confirmation
            if self.cross_timeframe_confirmation:
                timeframe_confirmation = self._check_cross_timeframe_confirmation(market_data)
                quality_factors.append(('timeframe_confirmation', timeframe_confirmation, 0.20))
            
            # 5. Market Regime Suitability
            regime_suitability = self._check_regime_suitability(market_data)
            quality_factors.append(('regime_suitability', regime_suitability, 0.15))
            
            # Calculate weighted quality score
            total_score = 0.0
            total_weight = 0.0
            
            for name, score, weight in quality_factors:
                if score is not None:
                    total_score += score * weight
                    total_weight += weight
            
            if total_weight > 0:
                final_quality = total_score / total_weight
            else:
                final_quality = 0.5  # Default quality
            
            return max(0.0, min(1.0, final_quality))
            
        except Exception as e:
            logger.error(f"Signal quality calculation failed: {e}")
            return 0.5
    
    def _check_trend_consistency(self, market_data: pd.DataFrame) -> float:
        """Check trend consistency across multiple timeframes"""
        try:
            prices = market_data['close']
            
            if len(prices) < 50:
                return 0.5
            
            # Calculate trends for different periods
            trends = []
            for period in [10, 20, 50]:
                if len(prices) >= period:
                    start_price = prices.iloc[-period]
                    end_price = prices.iloc[-1]
                    trend = 1 if end_price > start_price else -1
                    trends.append(trend)
            
            if not trends:
                return 0.5
            
            # Calculate consistency (all trends in same direction = 1.0)
            consistency = abs(sum(trends)) / len(trends)
            return consistency
            
        except Exception as e:
            logger.error(f"Trend consistency check failed: {e}")
            return 0.5
    
    def _check_volume_momentum_alignment(self, market_data: pd.DataFrame, momentum_scores: Dict[str, float]) -> float:
        """Check if volume supports momentum direction"""
        try:
            if 'volume' not in market_data.columns or len(market_data) < 20:
                return 0.7  # Neutral score if no volume data
            
            volume = market_data['volume']
            prices = market_data['close']
            weighted_momentum = momentum_scores.get('weighted_momentum', 0.0)
            
            # Recent volume trend
            recent_volume = volume.iloc[-10:].mean()
            historical_volume = volume.iloc[-20:].mean()
            volume_trend = recent_volume / historical_volume if historical_volume > 0 else 1.0
            
            # Price momentum direction
            momentum_direction = 1 if weighted_momentum > 0 else -1 if weighted_momentum < 0 else 0
            
            # Volume should increase with momentum
            if momentum_direction != 0:
                if volume_trend > 1.1:  # Volume increasing
                    alignment = 0.8  # Good alignment
                elif volume_trend > 0.9:  # Volume stable
                    alignment = 0.6  # Moderate alignment
                else:  # Volume decreasing
                    alignment = 0.3  # Poor alignment
            else:
                alignment = 0.5  # Neutral
            
            return alignment
            
        except Exception as e:
            logger.error(f"Volume-momentum alignment check failed: {e}")
            return 0.5
    
    def _check_volatility_suitability(self, market_data: pd.DataFrame) -> float:
        """Check if current volatility regime is suitable for momentum trading"""
        try:
            returns = market_data['close'].pct_change().dropna()
            
            if len(returns) < 20:
                return 0.5
            
            # Current vs historical volatility
            current_vol = returns.iloc[-10:].std()
            historical_vol = returns.std()
            vol_ratio = current_vol / historical_vol if historical_vol > 0 else 1.0
            
            # Momentum works best in moderate volatility
            if 0.8 <= vol_ratio <= 1.3:  # Moderate volatility
                suitability = 0.9
            elif 0.6 <= vol_ratio <= 1.6:  # Acceptable volatility
                suitability = 0.7
            elif vol_ratio > 2.0:  # Very high volatility (whipsaws)
                suitability = 0.2
            elif vol_ratio < 0.5:  # Very low volatility (no momentum)
                suitability = 0.3
            else:
                suitability = 0.5
            
            return suitability
            
        except Exception as e:
            logger.error(f"Volatility suitability check failed: {e}")
            return 0.5
    
    def _check_cross_timeframe_confirmation(self, market_data: pd.DataFrame) -> float:
        """Check momentum confirmation across multiple timeframes"""
        try:
            prices = market_data['close']
            
            if len(prices) < 100:
                return 0.5
            
            # Calculate momentum for different timeframes
            timeframes = [5, 10, 20, 50]
            momentum_signals = []
            
            for tf in timeframes:
                if len(prices) >= tf:
                    momentum = (prices.iloc[-1] - prices.iloc[-tf]) / prices.iloc[-tf]
                    signal = 1 if momentum > 0.01 else -1 if momentum < -0.01 else 0
                    momentum_signals.append(signal)
            
            if not momentum_signals:
                return 0.5
            
            # Calculate confirmation (agreement across timeframes)
            if len(set(momentum_signals)) == 1 and momentum_signals[0] != 0:
                confirmation = 1.0  # Perfect agreement
            else:
                # Partial agreement
                positive_signals = sum(1 for s in momentum_signals if s > 0)
                negative_signals = sum(1 for s in momentum_signals if s < 0)
                total_signals = len(momentum_signals)
                
                max_agreement = max(positive_signals, negative_signals)
                confirmation = max_agreement / total_signals
            
            return confirmation
            
        except Exception as e:
            logger.error(f"Cross-timeframe confirmation check failed: {e}")
            return 0.5
    
    def _check_regime_suitability(self, market_data: pd.DataFrame) -> float:
        """Check if current market regime is suitable for momentum trading"""
        try:
            # Use unified regime detection
            regime_result = detect_market_regime(market_data)
            
            # Get momentum strategy suitability from regime detector
            momentum_suitability = regime_result.strategy_suitability.get('momentum', 0.5)
            
            return momentum_suitability
            
        except Exception as e:
            logger.error(f"Regime suitability check failed: {e}")
            return 0.5
    
    def _calculate_dynamic_stop_loss(self, market_data: pd.DataFrame, signal_type: SignalType) -> Dict[str, Any]:
        """Calculate dynamic stop-loss levels based on market conditions"""
        try:
            if len(market_data) < 20:
                return {}
            
            prices = market_data['close']
            current_price = prices.iloc[-1]
            
            # Calculate ATR for volatility-based stops
            atr = self._calculate_atr(market_data)
            
            # Get market regime for regime-based adjustments
            regime_multiplier = 1.0
            if self.regime_based_stops:
                regime_result = detect_market_regime(market_data)
                regime_multiplier = self._get_regime_stop_multiplier(regime_result.primary_regime)
            
            # Calculate stop-loss distance
            base_stop_distance = atr * self.atr_stop_multiplier * regime_multiplier
            
            # Adjust for signal direction
            if signal_type == SignalType.BUY:
                stop_loss_price = current_price - base_stop_distance
                take_profit_price = current_price + (base_stop_distance * 2)  # 2:1 reward:risk
            else:  # SELL
                stop_loss_price = current_price + base_stop_distance
                take_profit_price = current_price - (base_stop_distance * 2)
            
            return {
                'stop_loss_price': stop_loss_price,
                'take_profit_price': take_profit_price,
                'atr': atr,
                'stop_distance': base_stop_distance,
                'regime_multiplier': regime_multiplier,
                'risk_reward_ratio': 2.0
            }
            
        except Exception as e:
            logger.error(f"Dynamic stop-loss calculation failed: {e}")
            return {}
    
    def _calculate_atr(self, market_data: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range"""
        try:
            if len(market_data) < period or 'high' not in market_data.columns:
                # Fallback to price-based volatility
                returns = market_data['close'].pct_change().dropna()
                return returns.std() * market_data['close'].iloc[-1] if len(returns) > 0 else 0.02
            
            high = market_data['high']
            low = market_data['low']
            close = market_data['close']
            prev_close = close.shift(1)
            
            # True Range calculation
            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            
            true_range = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
            atr = true_range.rolling(window=period).mean().iloc[-1]
            
            return atr if not pd.isna(atr) else 0.02
            
        except Exception as e:
            logger.error(f"ATR calculation failed: {e}")
            return 0.02
    
    def _get_regime_stop_multiplier(self, regime: MarketRegime) -> float:
        """Get stop-loss multiplier based on market regime"""
        try:
            multipliers = {
                MarketRegime.TRENDING_UP: 0.8,      # Tighter stops in trends
                MarketRegime.TRENDING_DOWN: 0.8,    # Tighter stops in trends
                MarketRegime.HIGH_VOLATILITY: 1.5,  # Wider stops in high vol
                MarketRegime.LOW_VOLATILITY: 1.2,   # Slightly wider in low vol
                MarketRegime.MEAN_REVERTING: 1.3,   # Wider stops (momentum less reliable)
                MarketRegime.SIDEWAYS: 1.1,         # Slightly wider stops
                MarketRegime.BREAKOUT: 0.9,         # Tighter stops on breakouts
            }
            
            return multipliers.get(regime, 1.0)
            
        except Exception as e:
            logger.error(f"Regime stop multiplier calculation failed: {e}")
            return 1.0

# ================================================================================
# TEMPLATE-BASED MOMENTUM STRATEGY
# ================================================================================

class TemplateMomentumStrategy(TemplateBasedStrategy):
    """
    Template-based momentum strategy.
    
    Integrates template configuration from the legacy template system
    while using the unified strategy framework.
    """
    
    def __init__(self, strategy_id: str, config: UnifiedStrategyConfig, template_config: Dict[str, Any]):
        super().__init__(strategy_id, config, template_config)
        
        # Parse momentum-specific template config
        self._parse_momentum_template()
        
        logger.info(f"Template momentum strategy initialized: {strategy_id}")
    
    def _parse_momentum_template(self):
        """Parse momentum-specific template configuration"""
        try:
            # Extract momentum parameters from template
            momentum_config = self.template_config.get('momentum', {})
            
            # Set momentum-specific parameters
            if 'lookback_periods' in momentum_config:
                self.parameters.custom_indicators.extend(['momentum_' + str(p) for p in momentum_config['lookback_periods']])
            
            if 'signal_conditions' in momentum_config:
                self.parameters.signal_conditions.extend(momentum_config['signal_conditions'])
            
            # Set threshold parameters
            for param in ['momentum_threshold', 'confidence_threshold', 'volume_threshold']:
                if param in momentum_config:
                    setattr(self.parameters, param, momentum_config[param])
            
        except Exception as e:
            logger.error(f"Momentum template parsing failed: {e}")
    
    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.MOMENTUM
    
    @property
    def required_indicators(self) -> List[str]:
        base_indicators = ['close', 'volume', 'high', 'low']
        return base_indicators + self.parameters.custom_indicators

# ================================================================================
# STRATEGY REGISTRATION
# ================================================================================

def register_momentum_strategies():
    """Register momentum strategy variants"""
    try:
        from .unified_strategy_registry import register_strategy
        
        # Register main momentum strategy
        register_strategy(
            strategy_type=StrategyType.MOMENTUM,
            strategy_class=MomentumStrategy,
            name="Momentum Strategy",
            description="Multi-period momentum strategy with confidence scoring",
            version="2.0.0",
            author="Professional Trading System Architecture"
        )
        
        # Register template-based variant
        register_strategy(
            strategy_type=StrategyType.MOMENTUM,  # Same type, different implementation
            strategy_class=TemplateMomentumStrategy,
            name="Template Momentum Strategy", 
            description="Template-based momentum strategy with configurable parameters",
            version="2.0.0",
            author="Professional Trading System Architecture"
        )
        
        logger.info("Momentum strategies registered successfully")
        return True
        
    except Exception as e:
        logger.error(f"Momentum strategy registration failed: {e}")
        return False

# Auto-register on module import
_registration_success = register_momentum_strategies()

logger.info("Unified Momentum Strategy loaded successfully")
