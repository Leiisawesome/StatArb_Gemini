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
        
        # Dynamic parameter optimization
        self.parameter_history = []
        self.performance_history = []
        self.optimization_frequency = getattr(self.parameters, 'optimization_frequency', 50)  # Every 50 signals
        
        # Regime detection parameters
        self.regime_lookback = getattr(self.parameters, 'regime_lookback', 252)
        self.current_regime = 'unknown'
        self.regime_confidence = 0.5
        
        logger.info(f"Momentum strategy initialized: {strategy_id}")
    
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
            
            # Enhanced momentum calculation with regime adjustment
            for i, period in enumerate(self.lookback_periods):
                if len(prices) >= period:
                    # Basic momentum
                    momentum = (prices.iloc[-1] - prices.iloc[-period]) / prices.iloc[-period]
                    
                    # Apply Kalman filter if enabled
                    if self.kalman_filter:
                        momentum = self._apply_kalman_filter(momentum, f'momentum_{period}')
                    
                    # Regime adjustment
                    if self.regime_awareness:
                        momentum = self._adjust_for_regime(momentum, self.current_regime)
                    
                    momentum_scores[f'momentum_{period}'] = momentum
                else:
                    momentum_scores[f'momentum_{period}'] = 0.0
            
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
            
            # Calculate position size with volatility adjustment
            base_position_size = self.parameters.position_size
            
            if self.volatility_adjustment and len(market_data) >= 20:
                returns = market_data['close'].pct_change().dropna()
                if len(returns) >= 10:
                    volatility = returns.iloc[-10:].std()
                    # Reduce position size for higher volatility
                    vol_adjustment = max(0.5, 1.0 - (volatility * 10))  # Scale volatility
                    adjusted_position_size = base_position_size * vol_adjustment * confidence
                else:
                    adjusted_position_size = base_position_size * confidence
            else:
                adjusted_position_size = base_position_size * confidence
            
            # Ensure position size is within limits
            adjusted_position_size = min(adjusted_position_size, self.parameters.max_position_size)
            
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
                    'filters_applied': {
                        'trend_filter': self.trend_filter,
                        'volatility_adjustment': self.volatility_adjustment
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
        """Calculate adaptive momentum threshold based on market conditions"""
        try:
            returns = market_data['close'].pct_change().dropna()
            
            if len(returns) < 20:
                return self.momentum_threshold
            
            # Base threshold on recent volatility
            recent_vol = returns.iloc[-20:].std()
            avg_vol = returns.std()
            
            vol_adjustment = recent_vol / avg_vol if avg_vol > 0 else 1.0
            
            # Adjust threshold: higher volatility = higher threshold
            adaptive_threshold = self.momentum_threshold * vol_adjustment
            
            # Keep within reasonable bounds
            return max(min(adaptive_threshold, self.momentum_threshold * 2), self.momentum_threshold * 0.5)
            
        except Exception as e:
            logger.error(f"Adaptive threshold calculation failed: {e}")
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
