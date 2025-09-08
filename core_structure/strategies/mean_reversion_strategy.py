#!/usr/bin/env python3
"""
Unified Mean Reversion Strategy - Consolidated Implementation
============================================================

Consolidated mean reversion strategy combining functionality from:
- trade_engine/strategies/mean_reversion_strategy.py
- trade_engine/templates/mean_reversion_template.py
- Enhanced with unified strategy system features

This implementation provides comprehensive mean reversion trading
with statistical analysis, Bollinger Bands, RSI, and Z-score analysis.

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
# MEAN REVERSION STRATEGY IMPLEMENTATION
# ================================================================================

class MeanReversionStrategy(EnhancedBaseStrategy):
    """
    Unified mean reversion strategy implementation.
    
    Features:
    - Z-score based mean reversion analysis
    - Bollinger Bands integration
    - RSI confirmation
    - Statistical significance testing
    - Dynamic position sizing based on deviation magnitude
    """
    
    # Class metadata
    SUPPORTED_MODES = ["backtest", "paper_trading", "live_trading"]
    STRATEGY_VERSION = "2.0.0"
    
    def __init__(self, strategy_id: str, config: UnifiedStrategyConfig):
        super().__init__(strategy_id, config)
        
        # Mean reversion specific parameters
        self.lookback_period = getattr(self.parameters, 'lookback_period', 20)
        self.z_score_threshold = getattr(self.parameters, 'z_score_threshold', 2.0)
        self.exit_z_score = getattr(self.parameters, 'exit_z_score', 0.5)
        self.bollinger_std = getattr(self.parameters, 'bollinger_std', 2.0)
        
        # Enhanced parameters
        self.rsi_period = getattr(self.parameters, 'rsi_period', 14)
        self.rsi_oversold = getattr(self.parameters, 'rsi_oversold', 30)
        self.rsi_overbought = getattr(self.parameters, 'rsi_overbought', 70)
        self.volume_confirmation = getattr(self.parameters, 'volume_confirmation', True)
        self.min_volume_ratio = getattr(self.parameters, 'min_volume_ratio', 0.8)
        
        # Advanced mean reversion features
        self.ornstein_uhlenbeck = getattr(self.parameters, 'ornstein_uhlenbeck', True)
        self.adaptive_windows = getattr(self.parameters, 'adaptive_windows', True)
        self.regime_detection = getattr(self.parameters, 'regime_detection', True)
        self.statistical_tests = getattr(self.parameters, 'statistical_tests', True)
        
        # OU process parameters
        self.ou_theta = 0.1  # Mean reversion speed
        self.ou_mu = 0.0     # Long-term mean
        self.ou_sigma = 0.1  # Volatility
        
        # Adaptive parameters
        self.adaptive_lookback = self.lookback_period
        self.volatility_regime = 'normal'
        self.mean_reversion_strength = 0.5
        
        # Performance tracking for optimization
        self.signal_history = []
        self.performance_metrics = {'accuracy': 0.0, 'sharpe': 0.0, 'max_dd': 0.0}
        
        # Adaptive threshold parameters
        self.adaptive_thresholds = getattr(self.parameters, 'adaptive_thresholds', True)
        self.base_z_threshold = self.z_score_threshold  # Store original threshold
        
        # Market condition filtering
        self.market_condition_filter = getattr(self.parameters, 'market_condition_filter', True)
        self.max_trend_strength = getattr(self.parameters, 'max_trend_strength', 0.7)
        self.min_mean_reversion_strength = getattr(self.parameters, 'min_mean_reversion_strength', 0.3)
        
        # Relative strength analysis
        self.relative_strength_analysis = getattr(self.parameters, 'relative_strength_analysis', True)
        self.sector_relative_trading = getattr(self.parameters, 'sector_relative_trading', False)
        
        logger.info(f"Mean reversion strategy initialized: {strategy_id}")
    
    def _calculate_volatility_adjusted_position_size(self, market_data: pd.DataFrame, 
                                                   base_size: float, z_score: float) -> float:
        """Calculate position size adjusted for volatility and mean reversion strength"""
        try:
            if len(market_data) < 20:
                return base_size
            
            returns = market_data['close'].pct_change().dropna()
            if len(returns) < 10:
                return base_size
            
            # Current volatility
            current_vol = returns.iloc[-20:].std() if len(returns) >= 20 else returns.std()
            
            # Historical volatility for comparison
            historical_vol = returns.std() if len(returns) >= 50 else current_vol
            
            # Target volatility for mean reversion (typically lower than momentum)
            target_vol = 0.015  # 1.5% daily target
            
            # Volatility adjustment
            if historical_vol > 0:
                vol_ratio = current_vol / historical_vol
                
                # Mean reversion works better in stable markets
                if vol_ratio > 1.3:  # High volatility - reduce size
                    vol_adjustment = max(0.5, target_vol / current_vol)
                elif vol_ratio < 0.8:  # Low volatility - can increase size
                    vol_adjustment = min(1.3, target_vol / current_vol)
                else:  # Normal volatility
                    vol_adjustment = target_vol / current_vol
                
                vol_adjustment = max(0.4, min(1.8, vol_adjustment))
            else:
                vol_adjustment = 1.0
            
            # Z-score strength adjustment (stronger mean reversion = larger position)
            z_score_strength = min(abs(z_score) / 3.0, 1.0)  # Normalize to max 1.0
            z_score_adjustment = 0.7 + (z_score_strength * 0.6)  # Range: 0.7 to 1.3
            
            # Combine adjustments
            adjusted_size = base_size * vol_adjustment * z_score_adjustment
            
            return adjusted_size
            
        except Exception as e:
            logger.error(f"Mean reversion volatility adjustment failed: {e}")
            return base_size
    
    def _calculate_multi_timeframe_zscore(self, prices: pd.Series) -> Dict[str, Any]:
        """Calculate z-scores across multiple timeframes for robust mean reversion signals"""
        try:
            # Multiple lookback windows for different timeframes
            windows = [20, 50, 100]  # Short, medium, long-term
            weights = [0.5, 0.3, 0.2]  # Higher weight for shorter-term (more responsive)
            
            z_scores = {}
            valid_z_scores = []
            valid_weights = []
            
            current_price = prices.iloc[-1]
            
            # Calculate z-score for each timeframe
            for i, window in enumerate(windows):
                if len(prices) >= window:
                    mean = prices.rolling(window).mean().iloc[-1]
                    std = prices.rolling(window).std().iloc[-1]
                    
                    if std > 0:
                        z_score = (current_price - mean) / std
                        z_scores[f'z_{window}'] = z_score
                        valid_z_scores.append(z_score)
                        valid_weights.append(weights[i])
                    else:
                        z_scores[f'z_{window}'] = 0.0
                else:
                    z_scores[f'z_{window}'] = 0.0
            
            # Calculate composite z-score (weighted average)
            if valid_z_scores:
                total_weight = sum(valid_weights)
                composite_z_score = sum(z * w for z, w in zip(valid_z_scores, valid_weights)) / total_weight
                
                # Calculate z-score strength (agreement across timeframes)
                z_score_signs = [1 if z > 0 else -1 if z < 0 else 0 for z in valid_z_scores]
                agreement = abs(sum(z_score_signs)) / len(z_score_signs) if z_score_signs else 0
                
                # Strength is combination of magnitude and agreement
                avg_magnitude = sum(abs(z) for z in valid_z_scores) / len(valid_z_scores)
                z_score_strength = agreement * min(1.0, avg_magnitude / 2.0)
            else:
                composite_z_score = 0.0
                z_score_strength = 0.0
            
            return {
                'composite_z_score': composite_z_score,
                'z_score_strength': z_score_strength,
                'individual_z_scores': z_scores,
                'timeframe_agreement': agreement if valid_z_scores else 0.0
            }
            
        except Exception as e:
            logger.error(f"Multi-timeframe z-score calculation failed: {e}")
            return {
                'composite_z_score': 0.0,
                'z_score_strength': 0.0,
                'individual_z_scores': {},
                'timeframe_agreement': 0.0
            }
    
    def _calculate_adaptive_z_threshold(self, market_data: pd.DataFrame) -> float:
        """Calculate adaptive z-score threshold based on market conditions"""
        try:
            if not self.adaptive_thresholds:
                return self.base_z_threshold
            
            returns = market_data['close'].pct_change().dropna()
            
            if len(returns) < 20:
                return self.base_z_threshold
            
            # 1. Volatility regime adjustment
            recent_vol = returns.iloc[-20:].std()
            long_term_vol = returns.std() if len(returns) >= 50 else recent_vol
            
            vol_ratio = recent_vol / long_term_vol if long_term_vol > 0 else 1.0
            
            # Mean reversion works better in stable markets
            if vol_ratio > 1.5:  # High volatility
                vol_adjustment = 1.3  # Higher threshold (more conservative)
            elif vol_ratio < 0.7:  # Low volatility
                vol_adjustment = 0.8  # Lower threshold (more aggressive)
            else:
                vol_adjustment = 1.0
            
            # 2. Mean reversion strength adjustment
            if hasattr(self, 'mean_reversion_strength'):
                if self.mean_reversion_strength > 0.7:  # Strong mean reversion
                    strength_adjustment = 0.9  # Lower threshold
                elif self.mean_reversion_strength < 0.3:  # Weak mean reversion
                    strength_adjustment = 1.4  # Higher threshold
                else:
                    strength_adjustment = 1.0
            else:
                strength_adjustment = 1.0
            
            # 3. Recent performance adjustment
            if hasattr(self, 'signal_history') and len(self.signal_history) >= 10:
                recent_signals = self.signal_history[-10:]
                success_rate = sum(1 for s in recent_signals if s.get('success', False)) / len(recent_signals)
                
                if success_rate < 0.4:  # Poor performance
                    performance_adjustment = 1.2  # Raise threshold
                elif success_rate > 0.7:  # Good performance
                    performance_adjustment = 0.9  # Lower threshold
                else:
                    performance_adjustment = 1.0
            else:
                performance_adjustment = 1.0
            
            # 4. Market regime adjustment
            regime_adjustment = 1.0
            if hasattr(self, 'volatility_regime'):
                if self.volatility_regime == 'high_volatility':
                    regime_adjustment = 1.3
                elif self.volatility_regime == 'low_volatility':
                    regime_adjustment = 0.8
                elif self.volatility_regime == 'trending':
                    regime_adjustment = 1.4  # Mean reversion less effective in trends
            
            # Combine all adjustments
            total_adjustment = vol_adjustment * strength_adjustment * performance_adjustment * regime_adjustment
            adaptive_threshold = self.base_z_threshold * total_adjustment
            
            # Keep within reasonable bounds (0.5x to 3.0x original)
            min_threshold = self.base_z_threshold * 0.5
            max_threshold = self.base_z_threshold * 3.0
            
            return max(min_threshold, min(adaptive_threshold, max_threshold))
            
        except Exception as e:
            logger.error(f"Adaptive z-score threshold calculation failed: {e}")
            return self.base_z_threshold
    
    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.MEAN_REVERSION
    
    @property
    def required_indicators(self) -> List[str]:
        return ['close', 'volume', 'high', 'low']
    
    def _get_required_parameters(self) -> List[str]:
        return [
            'z_score_threshold', 'exit_z_score', 'lookback_period',
            'bollinger_std', 'position_size'
        ]
    
    async def _generate_strategy_signals(self, context: StrategyContext) -> List[TradingSignal]:
        """Generate mean reversion trading signals"""
        signals = []
        
        try:
            market_data = context.market_data
            
            if len(market_data) < max(self.lookback_period, self.rsi_period):
                logger.debug(f"Insufficient data for mean reversion analysis: {len(market_data)}")
                return signals
            
            # Calculate mean reversion indicators
            indicators = self._calculate_indicators(market_data)
            
            # Market condition filter
            if self.market_condition_filter:
                if not self._should_trade_mean_reversion(market_data, indicators):
                    logger.debug("Mean reversion trading filtered out due to unfavorable market conditions")
                    return signals
            
            # Check for mean reversion signal
            signal = self._evaluate_mean_reversion(context, market_data, indicators)
            
            if signal:
                signals.append(signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"Mean reversion signal generation failed: {e}")
            return []
    
    def _calculate_indicators(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate enhanced indicators for advanced mean reversion analysis"""
        try:
            prices = market_data['close']
            indicators = {}
            
            # Adaptive window calculation
            if self.adaptive_windows:
                self.adaptive_lookback = self._calculate_adaptive_window(market_data)
            
            # Calculate rolling statistics with adaptive window
            window = self.adaptive_lookback
            rolling_mean = prices.rolling(window=window).mean()
            rolling_std = prices.rolling(window=window).std()
            
            # Multi-timeframe Z-score calculation
            z_scores = self._calculate_multi_timeframe_zscore(prices)
            
            # Primary z-score (main timeframe)
            current_price = prices.iloc[-1]
            current_mean = rolling_mean.iloc[-1]
            current_std = rolling_std.iloc[-1]
            
            if current_std > 0:
                z_score = (current_price - current_mean) / current_std
            else:
                z_score = 0.0
            
            # Composite z-score from multiple timeframes
            composite_z_score = z_scores['composite_z_score']
            z_score_strength = z_scores['z_score_strength']
            
            indicators['z_score'] = z_score
            indicators['composite_z_score'] = composite_z_score
            indicators['z_score_strength'] = z_score_strength
            indicators['multi_timeframe_z_scores'] = z_scores['individual_z_scores']
            indicators['rolling_mean'] = current_mean
            indicators['rolling_std'] = current_std
            indicators['adaptive_window'] = window
            
            # Ornstein-Uhlenbeck process analysis
            if self.ornstein_uhlenbeck and len(prices) >= 50:
                ou_params = self._estimate_ou_parameters(prices)
                indicators.update(ou_params)
                
                # OU-based mean reversion signal
                ou_signal = self._calculate_ou_signal(prices, ou_params)
                indicators['ou_signal'] = ou_signal
            
            # Regime detection
            if self.regime_detection:
                regime_info = self._detect_volatility_regime(market_data)
                indicators.update(regime_info)
                self.volatility_regime = regime_info.get('regime', 'normal')
            
            # Enhanced Bollinger Bands with regime adjustment
            regime_multiplier = self._get_regime_multiplier()
            adjusted_std = self.bollinger_std * regime_multiplier
            
            upper_band = current_mean + (adjusted_std * current_std)
            lower_band = current_mean - (adjusted_std * current_std)
            
            indicators['bollinger_upper'] = upper_band
            indicators['bollinger_lower'] = lower_band
            indicators['bollinger_position'] = (current_price - lower_band) / (upper_band - lower_band) if upper_band != lower_band else 0.5
            indicators['regime_multiplier'] = regime_multiplier
            
            # Advanced RSI with multiple periods
            rsi_values = {}
            for period in [14, 21, 30]:  # Multiple RSI periods
                if len(prices) >= period:
                    rsi = self._calculate_rsi(prices, period)
                    rsi_values[f'rsi_{period}'] = rsi
                    indicators[f'rsi_{period}'] = rsi
            
            # Composite RSI
            if rsi_values:
                indicators['rsi_composite'] = sum(rsi_values.values()) / len(rsi_values)
            else:
                indicators['rsi_composite'] = 50.0
            
            # Statistical tests for mean reversion
            if self.statistical_tests and len(prices) >= 50:
                stat_tests = self._perform_statistical_tests(prices)
                indicators.update(stat_tests)
            
            # Enhanced volume analysis
            if 'volume' in market_data.columns and len(market_data) >= 10:
                volume_analysis = self._analyze_volume_profile(market_data)
                indicators.update(volume_analysis)
            else:
                indicators['volume_ratio'] = 1.0
                indicators['volume_trend'] = 'neutral'
            
            # Mean reversion strength indicator
            if len(prices) >= 30:
                mr_strength = self._calculate_mean_reversion_strength(prices)
                indicators['mean_reversion_strength'] = mr_strength
                self.mean_reversion_strength = mr_strength
            
            return indicators
            
        except Exception as e:
            logger.error(f"Enhanced indicator calculation failed: {e}")
            return {}
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> float:
        """Calculate RSI (Relative Strength Index)"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50.0
            
        except Exception as e:
            logger.error(f"RSI calculation failed: {e}")
            return 50.0
    
    def _evaluate_mean_reversion(self, 
                                context: StrategyContext,
                                market_data: pd.DataFrame,
                                indicators: Dict[str, Any]) -> Optional[TradingSignal]:
        """Evaluate mean reversion conditions and generate signal"""
        try:
            # Use composite z-score for more robust signals
            z_score = indicators.get('z_score', 0.0)
            composite_z_score = indicators.get('composite_z_score', z_score)
            z_score_strength = indicators.get('z_score_strength', 0.5)
            
            rsi = indicators.get('rsi', 50.0)
            bollinger_position = indicators.get('bollinger_position', 0.5)
            volume_ratio = indicators.get('volume_ratio', 1.0)
            
            # Use composite z-score for signal generation (more robust)
            primary_z_score = composite_z_score if abs(composite_z_score) > abs(z_score) * 0.8 else z_score
            
            # Calculate adaptive threshold
            adaptive_threshold = self._calculate_adaptive_z_threshold(market_data)
            
            # Check for extreme deviations using adaptive threshold
            signal_type = None
            confidence = 0.0
            
            # Oversold conditions (potential buy signal)
            if (primary_z_score <= -adaptive_threshold and 
                rsi <= self.rsi_oversold and
                bollinger_position <= 0.1):
                
                signal_type = SignalType.BUY
                # Enhanced confidence with z-score strength and adaptive threshold
                base_confidence = 0.6 + (abs(primary_z_score) - adaptive_threshold) * 0.1
                confidence = min(0.95, base_confidence * (0.7 + z_score_strength * 0.3))
                
            # Overbought conditions (potential sell signal)
            elif (primary_z_score >= adaptive_threshold and
                  rsi >= self.rsi_overbought and
                  bollinger_position >= 0.9):
                
                signal_type = SignalType.SELL
                base_confidence = 0.6 + (abs(primary_z_score) - adaptive_threshold) * 0.1
                confidence = min(0.95, base_confidence * (0.7 + z_score_strength * 0.3))
            
            # No signal if conditions not met
            if signal_type is None:
                return None
            
            # Volume confirmation
            if self.volume_confirmation and volume_ratio < self.min_volume_ratio:
                logger.debug(f"Signal filtered out due to low volume: {volume_ratio:.2f}")
                return None
            
            # Market condition filtering (enhanced)
            if self.market_condition_filter:
                if not self._check_market_condition_filter(market_data, confidence):
                    logger.debug("Signal filtered out by enhanced market condition filter")
                    return None
            
            # Relative strength analysis
            relative_strength = self._calculate_relative_strength(market_data)
            
            # Adjust confidence based on relative strength
            if signal_type == SignalType.BUY:
                # For buy signals, lower relative strength (oversold) increases confidence
                rs_adjustment = (1.0 - relative_strength) * 0.2  # Up to 20% boost
            else:  # SELL
                # For sell signals, higher relative strength (overbought) increases confidence
                rs_adjustment = relative_strength * 0.2  # Up to 20% boost
            
            confidence = min(0.95, confidence + rs_adjustment)
            
            # Determine signal strength based on deviation magnitude
            deviation_magnitude = abs(z_score)
            if deviation_magnitude > self.z_score_threshold * 2:
                strength = SignalStrength.STRONG
            elif deviation_magnitude > self.z_score_threshold * 1.5:
                strength = SignalStrength.MEDIUM
            else:
                strength = SignalStrength.WEAK
            
            # Calculate enhanced volatility-adjusted position size
            base_position_size = self.parameters.position_size
            adjusted_position_size = self._calculate_volatility_adjusted_position_size(
                market_data, base_position_size, z_score
            )
            # Apply confidence factor
            adjusted_position_size *= confidence
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
                    'strategy_type': 'mean_reversion',
                    'strategy_id': self.strategy_id,
                    'z_score': z_score,
                    'composite_z_score': composite_z_score,
                    'z_score_strength': z_score_strength,
                    'adaptive_threshold': adaptive_threshold,
                    'rsi': rsi,
                    'bollinger_position': bollinger_position,
                    'volume_ratio': volume_ratio,
                    'indicators': indicators,
                    'thresholds': {
                        'z_score_threshold': self.z_score_threshold,
                        'exit_z_score': self.exit_z_score,
                        'rsi_oversold': self.rsi_oversold,
                        'rsi_overbought': self.rsi_overbought
                    },
                    'filters_applied': {
                        'market_condition_filter': self.market_condition_filter,
                        'relative_strength_analysis': self.relative_strength_analysis
                    }
                }
            )
            
            # Enhance signal with relative strength analysis
            if self.relative_strength_analysis:
                signal = self._enhance_signal_with_relative_strength(signal, market_data, context)
            
            return signal
            
        except Exception as e:
            logger.error(f"Mean reversion evaluation failed: {e}")
            return None
    
    def _calculate_adaptive_window(self, market_data: pd.DataFrame) -> int:
        """Calculate adaptive lookback window based on market conditions"""
        try:
            prices = market_data['close']
            returns = prices.pct_change().dropna()
            
            if len(returns) < 20:
                return self.lookback_period
            
            # Calculate volatility
            recent_vol = returns.iloc[-20:].std()
            long_vol = returns.std()
            
            # Adjust window based on volatility regime
            vol_ratio = recent_vol / long_vol if long_vol > 0 else 1.0
            
            if vol_ratio > 1.5:  # High volatility - shorter window
                adaptive_window = int(self.lookback_period * 0.7)
            elif vol_ratio < 0.7:  # Low volatility - longer window
                adaptive_window = int(self.lookback_period * 1.3)
            else:
                adaptive_window = self.lookback_period
            
            # Keep within reasonable bounds
            return max(min(adaptive_window, 100), 10)
            
        except Exception as e:
            logger.error(f"Adaptive window calculation failed: {e}")
            return self.lookback_period
    
    def _estimate_ou_parameters(self, prices: pd.Series) -> Dict[str, float]:
        """Estimate Ornstein-Uhlenbeck process parameters"""
        try:
            log_prices = np.log(prices)
            returns = log_prices.diff().dropna()
            
            if len(returns) < 30:
                return {'ou_theta': self.ou_theta, 'ou_mu': self.ou_mu, 'ou_sigma': self.ou_sigma}
            
            # Simple OU parameter estimation
            # theta (mean reversion speed)
            lag_prices = log_prices.iloc[:-1].values
            current_prices = log_prices.iloc[1:].values
            
            if len(lag_prices) > 0:
                # Linear regression: dX = theta * (mu - X) * dt + sigma * dW
                # Simplified: X(t+1) = a + b * X(t) + error
                from scipy import stats
                slope, intercept, r_value, p_value, std_err = stats.linregress(lag_prices, current_prices)
                
                theta = -np.log(slope) if slope > 0 and slope < 1 else 0.1
                mu = intercept / (1 - slope) if slope != 1 else log_prices.mean()
                sigma = returns.std()
                
                # Keep parameters within reasonable bounds
                theta = max(min(theta, 2.0), 0.01)
                sigma = max(min(sigma, 0.5), 0.01)
                
                return {
                    'ou_theta': theta,
                    'ou_mu': mu,
                    'ou_sigma': sigma,
                    'ou_half_life': np.log(2) / theta if theta > 0 else 100
                }
            
        except Exception as e:
            logger.error(f"OU parameter estimation failed: {e}")
        
        return {'ou_theta': self.ou_theta, 'ou_mu': self.ou_mu, 'ou_sigma': self.ou_sigma}
    
    def _calculate_ou_signal(self, prices: pd.Series, ou_params: Dict[str, float]) -> float:
        """Calculate OU process-based mean reversion signal"""
        try:
            current_log_price = np.log(prices.iloc[-1])
            ou_mu = ou_params.get('ou_mu', 0)
            ou_theta = ou_params.get('ou_theta', 0.1)
            
            # OU signal: how far are we from the long-term mean
            deviation = current_log_price - ou_mu
            
            # Normalize by expected reversion speed
            ou_signal = -deviation * ou_theta
            
            return ou_signal
            
        except Exception as e:
            logger.error(f"OU signal calculation failed: {e}")
            return 0.0
    
    def _detect_volatility_regime(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Detect current volatility regime"""
        try:
            returns = market_data['close'].pct_change().dropna()
            
            if len(returns) < 30:
                return {'regime': 'normal', 'regime_confidence': 0.5}
            
            # Calculate volatility measures
            short_vol = returns.iloc[-10:].std() if len(returns) >= 10 else 0
            medium_vol = returns.iloc[-30:].std() if len(returns) >= 30 else short_vol
            long_vol = returns.std()
            
            # Regime classification
            vol_ratio_short = short_vol / medium_vol if medium_vol > 0 else 1.0
            vol_ratio_long = medium_vol / long_vol if long_vol > 0 else 1.0
            
            if vol_ratio_short > 1.5 and vol_ratio_long > 1.2:
                regime = 'high_volatility'
                confidence = min(0.9, 0.5 + (vol_ratio_short - 1.0) * 0.3)
            elif vol_ratio_short < 0.7 and vol_ratio_long < 0.8:
                regime = 'low_volatility'
                confidence = min(0.9, 0.5 + (1.0 - vol_ratio_short) * 0.3)
            else:
                regime = 'normal'
                confidence = 0.6
            
            return {
                'regime': regime,
                'regime_confidence': confidence,
                'vol_ratio_short': vol_ratio_short,
                'vol_ratio_long': vol_ratio_long
            }
            
        except Exception as e:
            logger.error(f"Volatility regime detection failed: {e}")
            return {'regime': 'normal', 'regime_confidence': 0.5}
    
    def _get_regime_multiplier(self) -> float:
        """Get Bollinger Band multiplier based on volatility regime"""
        if self.volatility_regime == 'high_volatility':
            return 1.5  # Wider bands in high volatility
        elif self.volatility_regime == 'low_volatility':
            return 0.8  # Tighter bands in low volatility
        else:
            return 1.0  # Normal bands
    
    def _perform_statistical_tests(self, prices: pd.Series) -> Dict[str, float]:
        """Perform statistical tests for mean reversion"""
        try:
            from scipy import stats
            
            log_prices = np.log(prices)
            returns = log_prices.diff().dropna()
            
            results = {}
            
            # Augmented Dickey-Fuller test (simplified)
            if len(returns) >= 20:
                # Simple autocorrelation test as proxy for ADF
                autocorr_1 = returns.autocorr(lag=1) if len(returns) > 1 else 0
                results['adf_proxy'] = autocorr_1
                results['mean_reverting'] = autocorr_1 < -0.1
            
            # Variance ratio test (simplified)
            if len(returns) >= 30:
                var_1 = returns.var()
                var_2 = returns.rolling(2).sum().var() / 2 if len(returns) >= 4 else var_1
                variance_ratio = var_2 / var_1 if var_1 > 0 else 1.0
                results['variance_ratio'] = variance_ratio
                results['random_walk'] = abs(variance_ratio - 1.0) < 0.1
            
            # Hurst exponent (simplified)
            if len(returns) >= 50:
                hurst = self._calculate_hurst_exponent(returns)
                results['hurst_exponent'] = hurst
                results['mean_reverting_hurst'] = hurst < 0.5
            
            return results
            
        except Exception as e:
            logger.error(f"Statistical tests failed: {e}")
            return {}
    
    def _calculate_hurst_exponent(self, returns: pd.Series) -> float:
        """Calculate simplified Hurst exponent"""
        try:
            # Simplified R/S analysis
            n = len(returns)
            if n < 20:
                return 0.5
            
            # Calculate cumulative deviations
            mean_return = returns.mean()
            cumulative_deviations = (returns - mean_return).cumsum()
            
            # Calculate range
            R = cumulative_deviations.max() - cumulative_deviations.min()
            
            # Calculate standard deviation
            S = returns.std()
            
            if S > 0 and R > 0:
                # Simplified Hurst calculation
                hurst = np.log(R/S) / np.log(n)
                return max(min(hurst, 1.0), 0.0)
            else:
                return 0.5
                
        except Exception as e:
            logger.error(f"Hurst exponent calculation failed: {e}")
            return 0.5
    
    def _analyze_volume_profile(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze volume profile for mean reversion confirmation"""
        try:
            volume = market_data['volume']
            prices = market_data['close']
            
            if len(volume) < 10:
                return {'volume_ratio': 1.0, 'volume_trend': 'neutral'}
            
            # Volume statistics
            recent_volume = volume.iloc[-5:].mean()
            avg_volume = volume.iloc[-20:].mean() if len(volume) >= 20 else recent_volume
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1.0
            
            # Volume trend
            if len(volume) >= 10:
                volume_slope = np.polyfit(range(10), volume.iloc[-10:].values, 1)[0]
                if volume_slope > avg_volume * 0.01:
                    volume_trend = 'increasing'
                elif volume_slope < -avg_volume * 0.01:
                    volume_trend = 'decreasing'
                else:
                    volume_trend = 'neutral'
            else:
                volume_trend = 'neutral'
            
            # Price-volume relationship
            if len(prices) >= 10 and len(volume) >= 10:
                price_changes = prices.pct_change().iloc[-10:]
                volume_changes = volume.pct_change().iloc[-10:]
                
                # Correlation between price and volume changes
                try:
                    pv_correlation = price_changes.corr(volume_changes)
                    if pd.isna(pv_correlation):
                        pv_correlation = 0.0
                except:
                    pv_correlation = 0.0
            else:
                pv_correlation = 0.0
            
            return {
                'volume_ratio': volume_ratio,
                'volume_trend': volume_trend,
                'price_volume_correlation': pv_correlation,
                'volume_confirmation': volume_ratio > self.min_volume_ratio
            }
            
        except Exception as e:
            logger.error(f"Volume profile analysis failed: {e}")
            return {'volume_ratio': 1.0, 'volume_trend': 'neutral'}
    
    def _calculate_mean_reversion_strength(self, prices: pd.Series) -> float:
        """Calculate overall mean reversion strength"""
        try:
            returns = prices.pct_change().dropna()
            
            if len(returns) < 20:
                return 0.5
            
            # Multiple measures of mean reversion
            measures = []
            
            # Autocorrelation (negative = mean reverting)
            autocorr = returns.autocorr(lag=1)
            if not pd.isna(autocorr):
                measures.append(max(0, -autocorr))  # Convert to positive scale
            
            # Variance ratio (< 1 = mean reverting)
            if len(returns) >= 10:
                var_1 = returns.var()
                var_2 = returns.rolling(2).sum().var() / 2 if len(returns) >= 4 else var_1
                variance_ratio = var_2 / var_1 if var_1 > 0 else 1.0
                measures.append(max(0, 2 - variance_ratio))  # Convert to strength scale
            
            # Half-life of mean reversion
            if len(returns) >= 30:
                try:
                    # Simple AR(1) model
                    lag_returns = returns.iloc[:-1].values
                    current_returns = returns.iloc[1:].values
                    
                    if len(lag_returns) > 0:
                        correlation = np.corrcoef(lag_returns, current_returns)[0, 1]
                        if not np.isnan(correlation) and correlation < 0:
                            half_life = -np.log(2) / np.log(1 + correlation)
                            # Normalize: shorter half-life = stronger mean reversion
                            strength = max(0, min(1, 30 / half_life)) if half_life > 0 else 0
                            measures.append(strength)
                except:
                    pass
            
            # Average of all measures
            if measures:
                return sum(measures) / len(measures)
            else:
                return 0.5
                
        except Exception as e:
            logger.error(f"Mean reversion strength calculation failed: {e}")
            return 0.5
    
    def _should_trade_mean_reversion(self, market_data: pd.DataFrame, indicators: Dict[str, Any]) -> bool:
        """Determine if market conditions are suitable for mean reversion trading"""
        try:
            # 1. Check trend strength - avoid mean reversion in strong trends
            trend_strength = self._calculate_trend_strength(market_data)
            if trend_strength > self.max_trend_strength:
                logger.debug(f"Mean reversion filtered: trend too strong ({trend_strength:.2f} > {self.max_trend_strength})")
                return False
            
            # 2. Check mean reversion strength - need sufficient mean reversion tendency
            mr_strength = indicators.get('mean_reversion_strength', 0.5)
            if mr_strength < self.min_mean_reversion_strength:
                logger.debug(f"Mean reversion filtered: insufficient MR strength ({mr_strength:.2f} < {self.min_mean_reversion_strength})")
                return False
            
            # 3. Market regime suitability check
            regime_result = detect_market_regime(market_data)
            mr_suitability = regime_result.strategy_suitability.get('mean_reversion', 0.5)
            
            if mr_suitability < 0.4:  # Low suitability threshold
                logger.debug(f"Mean reversion filtered: poor regime suitability ({mr_suitability:.2f})")
                return False
            
            # 4. Volatility regime check - avoid extreme volatility
            if regime_result.primary_regime == MarketRegime.HIGH_VOLATILITY:
                # Allow trading in high vol only if confidence is high
                if regime_result.confidence > 0.8 and mr_strength > 0.6:
                    return True
                else:
                    logger.debug("Mean reversion filtered: high volatility regime with low confidence")
                    return False
            
            # 5. Check for breakout conditions - avoid mean reversion during breakouts
            if regime_result.primary_regime == MarketRegime.BREAKOUT:
                logger.debug("Mean reversion filtered: breakout regime detected")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Market condition filter failed: {e}")
            return True  # Default to allowing trading on error
    
    def _calculate_trend_strength(self, market_data: pd.DataFrame) -> float:
        """Calculate overall trend strength to avoid mean reversion in strong trends"""
        try:
            prices = market_data['close']
            
            if len(prices) < 50:
                return 0.0
            
            trend_factors = []
            
            # 1. Multiple moving average alignment
            ma_short = prices.rolling(20).mean().iloc[-1]
            ma_medium = prices.rolling(50).mean().iloc[-1]
            current_price = prices.iloc[-1]
            
            # Check if MAs are aligned (trending)
            if ma_short > ma_medium > current_price * 0.98:  # Uptrend with tolerance
                ma_alignment = 1.0
            elif ma_short < ma_medium < current_price * 1.02:  # Downtrend with tolerance
                ma_alignment = 1.0
            else:
                ma_alignment = 0.0
            
            trend_factors.append(ma_alignment)
            
            # 2. Linear trend strength
            recent_prices = prices.iloc[-30:]
            x = np.arange(len(recent_prices))
            slope, _ = np.polyfit(x, recent_prices.values, 1)
            normalized_slope = abs(slope) / recent_prices.mean() * 30  # Normalize by price and period
            linear_trend = min(1.0, normalized_slope / 0.05)  # 5% over 30 periods = strong trend
            
            trend_factors.append(linear_trend)
            
            # 3. Directional consistency
            returns = prices.pct_change().dropna()
            if len(returns) >= 20:
                recent_returns = returns.iloc[-20:]
                positive_returns = (recent_returns > 0).sum()
                directional_consistency = abs(positive_returns - 10) / 10  # Deviation from 50/50
                trend_factors.append(directional_consistency)
            
            # 4. Momentum persistence
            if len(prices) >= 60:
                short_momentum = (prices.iloc[-1] - prices.iloc[-20]) / prices.iloc[-20]
                medium_momentum = (prices.iloc[-1] - prices.iloc[-40]) / prices.iloc[-40]
                
                # Check if momentum is persistent (same direction)
                if short_momentum * medium_momentum > 0:  # Same sign
                    momentum_persistence = min(1.0, abs(short_momentum) / 0.1)  # 10% = strong momentum
                else:
                    momentum_persistence = 0.0
                
                trend_factors.append(momentum_persistence)
            
            # Calculate overall trend strength
            if trend_factors:
                trend_strength = sum(trend_factors) / len(trend_factors)
            else:
                trend_strength = 0.0
            
            return max(0.0, min(1.0, trend_strength))
            
        except Exception as e:
            logger.error(f"Trend strength calculation failed: {e}")
            return 0.0
    
    def _calculate_relative_strength_signal(self, market_data: pd.DataFrame, context) -> Optional[Dict[str, Any]]:
        """Calculate relative strength vs sector/market for enhanced mean reversion"""
        try:
            if not self.relative_strength_analysis:
                return None
            
            # This is a simplified implementation
            # In practice, you'd need sector/market index data
            prices = market_data['close']
            
            if len(prices) < 50:
                return None
            
            # Calculate relative performance metrics
            # For now, use price relative to its own moving averages as proxy
            
            # Short-term relative strength
            ma_20 = prices.rolling(20).mean().iloc[-1]
            ma_50 = prices.rolling(50).mean().iloc[-1]
            current_price = prices.iloc[-1]
            
            # Relative strength vs short-term average
            rs_short = (current_price - ma_20) / ma_20
            
            # Relative strength vs medium-term average
            rs_medium = (current_price - ma_50) / ma_50
            
            # Calculate relative strength score
            # Negative RS = underperforming (good for mean reversion longs)
            # Positive RS = outperforming (good for mean reversion shorts)
            
            relative_strength_score = (rs_short + rs_medium) / 2
            
            # Determine if relative strength supports mean reversion signal
            rs_signal_strength = abs(relative_strength_score)
            
            return {
                'relative_strength_score': relative_strength_score,
                'rs_signal_strength': rs_signal_strength,
                'rs_short_term': rs_short,
                'rs_medium_term': rs_medium,
                'supports_long': relative_strength_score < -0.02,  # Underperforming
                'supports_short': relative_strength_score > 0.02   # Outperforming
            }
            
        except Exception as e:
            logger.error(f"Relative strength calculation failed: {e}")
            return None
    
    def _enhance_signal_with_relative_strength(self, 
                                             signal: TradingSignal, 
                                             market_data: pd.DataFrame,
                                             context) -> TradingSignal:
        """Enhance mean reversion signal with relative strength analysis"""
        try:
            if not self.relative_strength_analysis:
                return signal
            
            rs_data = self._calculate_relative_strength_signal(market_data, context)
            
            if rs_data is None:
                return signal
            
            # Check if relative strength supports the signal
            signal_supported = False
            
            if signal.signal_type == SignalType.BUY and rs_data['supports_long']:
                signal_supported = True
            elif signal.signal_type == SignalType.SELL and rs_data['supports_short']:
                signal_supported = True
            
            # Adjust confidence based on relative strength support
            if signal_supported:
                # Boost confidence
                rs_boost = min(0.2, rs_data['rs_signal_strength'] * 0.5)
                signal.confidence = min(0.95, signal.confidence + rs_boost)
            else:
                # Reduce confidence if relative strength doesn't support
                rs_penalty = min(0.15, rs_data['rs_signal_strength'] * 0.3)
                signal.confidence = max(0.1, signal.confidence - rs_penalty)
            
            # Add relative strength data to metadata
            if 'relative_strength' not in signal.metadata:
                signal.metadata['relative_strength'] = rs_data
            
            return signal
            
        except Exception as e:
            logger.error(f"Relative strength enhancement failed: {e}")
            return signal
    
    def _check_market_condition_filter(self, market_data: pd.DataFrame, signal_strength: float) -> bool:
        """
        Enhanced market condition filtering for mean reversion signals
        
        Args:
            market_data: Historical price data
            signal_strength: Strength of the mean reversion signal
            
        Returns:
            bool: True if market conditions are favorable for mean reversion
        """
        try:
            if len(market_data) < 50:
                return True  # Not enough data for filtering
            
            prices = market_data['close']
            current_price = prices.iloc[-1]
            
            # 1. Trend Strength Analysis
            ma_20 = prices.rolling(20).mean().iloc[-1]
            ma_50 = prices.rolling(50).mean().iloc[-1]
            
            # Calculate trend strength
            trend_strength = abs(ma_20 - ma_50) / ma_50
            
            # Strong trends are unfavorable for mean reversion
            if trend_strength > 0.025:  # 2.5% threshold
                logger.debug(f"Strong trend detected (strength: {trend_strength:.3f}), filtering mean reversion signal")
                return False
            
            # 2. Market Regime Check
            try:
                regime_result = detect_market_regime(market_data)
                mean_reversion_suitability = regime_result.strategy_suitability.get('mean_reversion', 0.5)
                
                # Require minimum regime suitability
                if mean_reversion_suitability < 0.4:
                    logger.debug(f"Unfavorable market regime for mean reversion (suitability: {mean_reversion_suitability:.3f})")
                    return False
                    
            except Exception as e:
                logger.warning(f"Regime detection failed in market condition filter: {e}")
            
            # 3. Volatility Regime Analysis
            returns = prices.pct_change().dropna()
            if len(returns) >= 20:
                volatility = returns.rolling(20).std().iloc[-1] * np.sqrt(252)
                
                # Extremely high volatility can lead to false mean reversion signals
                if volatility > 0.5:  # 50% annualized volatility threshold
                    logger.debug(f"High volatility regime detected ({volatility:.3f}), filtering signal")
                    return False
            
            # 4. Signal Strength Requirement
            # Require stronger signals in uncertain conditions
            min_signal_strength = 0.6
            if signal_strength < min_signal_strength:
                logger.debug(f"Signal strength too low ({signal_strength:.3f} < {min_signal_strength})")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Market condition filter failed: {e}")
            return True  # Default to allowing signal
    
    def _calculate_relative_strength(self, market_data: pd.DataFrame) -> float:
        """
        Calculate relative strength of the asset compared to its moving averages
        
        Args:
            market_data: Historical price data
            
        Returns:
            float: Relative strength score (0.0 to 1.0)
        """
        try:
            if len(market_data) < 50:
                return 0.5  # Neutral if insufficient data
            
            prices = market_data['close']
            current_price = prices.iloc[-1]
            
            # Calculate multiple moving averages
            ma_10 = prices.rolling(10).mean().iloc[-1]
            ma_20 = prices.rolling(20).mean().iloc[-1] 
            ma_50 = prices.rolling(50).mean().iloc[-1]
            
            # Calculate relative positions
            rel_10 = (current_price - ma_10) / ma_10
            rel_20 = (current_price - ma_20) / ma_20
            rel_50 = (current_price - ma_50) / ma_50
            
            # Weight shorter-term MAs more heavily
            weighted_relative_strength = (
                rel_10 * 0.5 +  # 50% weight on 10-day MA
                rel_20 * 0.3 +  # 30% weight on 20-day MA
                rel_50 * 0.2    # 20% weight on 50-day MA
            )
            
            # Normalize to 0-1 scale (assuming ±10% is extreme)
            normalized_strength = (weighted_relative_strength + 0.1) / 0.2
            normalized_strength = max(0.0, min(1.0, normalized_strength))
            
            return normalized_strength
            
        except Exception as e:
            logger.error(f"Relative strength calculation failed: {e}")
            return 0.5

# ================================================================================
# TEMPLATE-BASED MEAN REVERSION STRATEGY
# ================================================================================

class TemplateMeanReversionStrategy(TemplateBasedStrategy):
    """
    Template-based mean reversion strategy.
    
    Integrates template configuration from the legacy template system
    while using the unified strategy framework.
    """
    
    def __init__(self, strategy_id: str, config: UnifiedStrategyConfig, template_config: Dict[str, Any]):
        super().__init__(strategy_id, config, template_config)
        
        # Parse mean reversion specific template config
        self._parse_mean_reversion_template()
        
        logger.info(f"Template mean reversion strategy initialized: {strategy_id}")
    
    def _parse_mean_reversion_template(self):
        """Parse mean reversion specific template configuration"""
        try:
            # Extract mean reversion parameters from template
            mr_config = self.template_config.get('mean_reversion', {})
            
            # Set mean reversion specific parameters
            for param in ['z_score_threshold', 'exit_z_score', 'lookback_period', 'bollinger_std']:
                if param in mr_config:
                    setattr(self.parameters, param, mr_config[param])
            
            # Set RSI parameters
            rsi_config = mr_config.get('rsi', {})
            for param in ['rsi_period', 'rsi_oversold', 'rsi_overbought']:
                if param in rsi_config:
                    setattr(self.parameters, param, rsi_config[param])
            
            # Set volume parameters
            volume_config = mr_config.get('volume', {})
            for param in ['volume_confirmation', 'min_volume_ratio']:
                if param in volume_config:
                    setattr(self.parameters, param, volume_config[param])
            
        except Exception as e:
            logger.error(f"Mean reversion template parsing failed: {e}")
    
    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.MEAN_REVERSION
    
    @property
    def required_indicators(self) -> List[str]:
        base_indicators = ['close', 'volume', 'high', 'low']
        return base_indicators + self.parameters.custom_indicators

# ================================================================================
# STRATEGY REGISTRATION
# ================================================================================

def register_mean_reversion_strategies():
    """Register mean reversion strategy variants"""
    try:
        from .unified_strategy_registry import register_strategy
        
        # Register main mean reversion strategy
        register_strategy(
            strategy_type=StrategyType.MEAN_REVERSION,
            strategy_class=MeanReversionStrategy,
            name="Mean Reversion Strategy",
            description="Statistical mean reversion strategy with Z-score, Bollinger Bands, and RSI",
            version="2.0.0",
            author="Professional Trading System Architecture"
        )
        
        # Register template-based variant
        register_strategy(
            strategy_type=StrategyType.MEAN_REVERSION,
            strategy_class=TemplateMeanReversionStrategy,
            name="Template Mean Reversion Strategy",
            description="Template-based mean reversion strategy with configurable parameters",
            version="2.0.0",
            author="Professional Trading System Architecture"
        )
        
        logger.info("Mean reversion strategies registered successfully")
        return True
        
    except Exception as e:
        logger.error(f"Mean reversion strategy registration failed: {e}")
        return False

# Auto-register on module import
_registration_success = register_mean_reversion_strategies()

logger.info("Unified Mean Reversion Strategy loaded successfully")
