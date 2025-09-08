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
        
        logger.info(f"Mean reversion strategy initialized: {strategy_id}")
    
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
            
            # Enhanced Z-score calculation
            current_price = prices.iloc[-1]
            current_mean = rolling_mean.iloc[-1]
            current_std = rolling_std.iloc[-1]
            
            if current_std > 0:
                z_score = (current_price - current_mean) / current_std
            else:
                z_score = 0.0
            
            indicators['z_score'] = z_score
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
            z_score = indicators.get('z_score', 0.0)
            rsi = indicators.get('rsi', 50.0)
            bollinger_position = indicators.get('bollinger_position', 0.5)
            volume_ratio = indicators.get('volume_ratio', 1.0)
            
            # Check for extreme deviations
            signal_type = None
            confidence = 0.0
            
            # Oversold conditions (potential buy signal)
            if (z_score <= -self.z_score_threshold and 
                rsi <= self.rsi_oversold and
                bollinger_position <= 0.1):
                
                signal_type = SignalType.BUY
                # Confidence increases with more extreme values
                confidence = min(0.95, 0.6 + (abs(z_score) - self.z_score_threshold) * 0.1)
                
            # Overbought conditions (potential sell signal)
            elif (z_score >= self.z_score_threshold and
                  rsi >= self.rsi_overbought and
                  bollinger_position >= 0.9):
                
                signal_type = SignalType.SELL
                confidence = min(0.95, 0.6 + (abs(z_score) - self.z_score_threshold) * 0.1)
            
            # No signal if conditions not met
            if signal_type is None:
                return None
            
            # Volume confirmation
            if self.volume_confirmation and volume_ratio < self.min_volume_ratio:
                logger.debug(f"Signal filtered out due to low volume: {volume_ratio:.2f}")
                return None
            
            # Determine signal strength based on deviation magnitude
            deviation_magnitude = abs(z_score)
            if deviation_magnitude > self.z_score_threshold * 2:
                strength = SignalStrength.STRONG
            elif deviation_magnitude > self.z_score_threshold * 1.5:
                strength = SignalStrength.MEDIUM
            else:
                strength = SignalStrength.WEAK
            
            # Calculate position size based on confidence and deviation
            base_position_size = self.parameters.position_size
            deviation_factor = min(2.0, deviation_magnitude / self.z_score_threshold)
            adjusted_position_size = base_position_size * confidence * (deviation_factor / 2.0)
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
                    'rsi': rsi,
                    'bollinger_position': bollinger_position,
                    'volume_ratio': volume_ratio,
                    'indicators': indicators,
                    'thresholds': {
                        'z_score_threshold': self.z_score_threshold,
                        'exit_z_score': self.exit_z_score,
                        'rsi_oversold': self.rsi_oversold,
                        'rsi_overbought': self.rsi_overbought
                    }
                }
            )
            
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
