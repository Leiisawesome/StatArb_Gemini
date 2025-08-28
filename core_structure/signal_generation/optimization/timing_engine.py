"""
Consolidated Timing Engine
=========================

Unified market timing and execution timing combining:
- Market timing and regime-based timing
- Execution timing optimization
- Liquidity timing and volume analysis
- Event-driven timing strategies

This module consolidates timing functionality from:
- timing_optimizer.py
- execution_timer.py
- liquidity_timing.py

Author: GitHub Copilot Architecture Simplification
Version: 4.0 (Consolidated)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta, time as dt_time
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
import time
import json
from collections import defaultdict, deque

# Core infrastructure imports
try:
    from ...infrastructure.config import UnifiedConfigManager as ConfigManager
    from ...infrastructure.message_bus import MessageBus
    from ...infrastructure.metrics_collector import MetricsCollector
except ImportError:
    ConfigManager = None
    MessageBus = None
    MetricsCollector = None

# Scientific computing with graceful fallback
try:
    from scipy import stats
    from scipy.optimize import minimize
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

# Time series analysis
try:
    from statsmodels.tsa.seasonal import seasonal_decompose
    from statsmodels.tsa.arima.model import ARIMA
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)

class TimingStrategy(Enum):
    """Market timing strategies"""
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    REGIME_BASED = "regime_based"
    VOLUME_WEIGHTED = "volume_weighted"
    VOLATILITY_BASED = "volatility_based"
    EVENT_DRIVEN = "event_driven"
    LIQUIDITY_BASED = "liquidity_based"

class ExecutionTiming(Enum):
    """Execution timing methods"""
    IMMEDIATE = "immediate"
    VWAP = "vwap"
    TWAP = "twap"
    MARKET_OPEN = "market_open"
    MARKET_CLOSE = "market_close"
    OPTIMAL_LIQUIDITY = "optimal_liquidity"
    LOW_VOLATILITY = "low_volatility"

class TimingConfidence(Enum):
    """Timing confidence levels"""
    VERY_HIGH = 4  # >90%
    HIGH = 3       # 75-90%
    MEDIUM = 2     # 50-75%
    LOW = 1        # 25-50%
    VERY_LOW = 0   # <25%

@dataclass
class TimingConfig:
    """Configuration for timing engine"""
    # Core timing settings
    timing_strategy: TimingStrategy = TimingStrategy.REGIME_BASED
    execution_timing: ExecutionTiming = ExecutionTiming.VWAP
    lookback_window: int = 20
    
    # Market timing
    enable_momentum_timing: bool = True
    momentum_window: int = 10
    mean_reversion_threshold: float = 2.0  # Standard deviations
    
    # Execution timing
    vwap_window_minutes: int = 30
    twap_slices: int = 10
    max_execution_delay_minutes: int = 60
    
    # Liquidity timing
    min_volume_threshold: float = 0.1  # 10% of average daily volume
    liquidity_impact_threshold: float = 0.001  # 10 bps
    volume_participation_limit: float = 0.2  # 20% of volume
    
    # Risk management
    max_timing_delay_hours: int = 4
    
    def __post_init__(self):
        """Convert string timing strategy to enum if needed"""
        if isinstance(self.timing_strategy, str):
            self.timing_strategy = TimingStrategy(self.timing_strategy)
        if isinstance(self.execution_timing, str):
            execution_timing_map = {
                'immediate': ExecutionTiming.IMMEDIATE,
                'vwap': ExecutionTiming.VWAP,
                'twap': ExecutionTiming.TWAP,
                'market_open': ExecutionTiming.MARKET_OPEN,
                'market_close': ExecutionTiming.MARKET_CLOSE,
                'optimal_liquidity': ExecutionTiming.OPTIMAL_LIQUIDITY,
                'low_volatility': ExecutionTiming.LOW_VOLATILITY
            }
            self.execution_timing = execution_timing_map.get(self.execution_timing, ExecutionTiming.VWAP)
    min_confidence_threshold: float = 0.5
    enable_overnight_timing: bool = False
    
    # Performance settings
    update_frequency_seconds: int = 30
    enable_real_time_timing: bool = True
    cache_timing_signals: bool = True

@dataclass
class TimingSignal:
    """Market timing signal"""
    signal_type: TimingStrategy
    strength: float  # -1 to 1, negative = wait, positive = execute
    confidence: float  # 0 to 1
    confidence_level: TimingConfidence
    optimal_time: Optional[datetime]
    execution_method: ExecutionTiming
    expected_impact: float  # Expected market impact
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'signal_type': self.signal_type.value,
            'strength': self.strength,
            'confidence': self.confidence,
            'confidence_level': self.confidence_level.value,
            'optimal_time': self.optimal_time.isoformat() if self.optimal_time else None,
            'execution_method': self.execution_method.value,
            'expected_impact': self.expected_impact,
            'metadata': self.metadata
        }

@dataclass
class ExecutionWindow:
    """Optimal execution window"""
    start_time: datetime
    end_time: datetime
    expected_volume: float
    expected_volatility: float
    liquidity_score: float
    impact_estimate: float
    confidence: float
    
    def duration_minutes(self) -> int:
        """Get window duration in minutes"""
        return int((self.end_time - self.start_time).total_seconds() / 60)

class TimingEngine:
    """
    Consolidated Timing Engine
    
    Unified market timing combining execution optimization,
    liquidity timing, and regime-based timing strategies.
    """
    
    def __init__(self, config: Optional[TimingConfig] = None):
        """Initialize timing engine"""
        self.config = config or TimingConfig()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # State management
        self._timing_signals_cache = {}
        self._volume_profiles = {}
        self._liquidity_patterns = {}
        self._lock = threading.Lock()
        
        # Market hours (can be customized)
        self.market_open = dt_time(9, 30)  # 9:30 AM
        self.market_close = dt_time(16, 0)  # 4:00 PM
        
        # Performance tracking
        self.performance_metrics = {
            'signals_generated': 0,
            'successful_timings': 0,
            'avg_execution_quality': 0.0,
            'avg_market_impact': 0.0,
            'timing_accuracy': 0.0,
            'last_update': datetime.now()
        }
        
        self.logger.info(f"TimingEngine initialized with strategy: {self.config.timing_strategy.value}")
    
    def generate_timing_signal(self, 
                              symbol: str,
                              market_data: pd.DataFrame,
                              target_quantity: float,
                              current_regime: Optional[str] = None) -> Optional[TimingSignal]:
        """
        Generate market timing signal
        
        Args:
            symbol: Trading symbol
            market_data: Historical market data
            target_quantity: Target order quantity
            current_regime: Current market regime
            
        Returns:
            Timing signal or None if generation fails
        """
        try:
            if not self._validate_market_data(market_data):
                return None
            
            # Generate timing signal based on strategy
            signal_strength, confidence = self._calculate_timing_signal(
                market_data, current_regime
            )
            
            # Determine optimal execution method
            execution_method = self._select_execution_method(
                symbol, market_data, target_quantity
            )
            
            # Calculate expected market impact
            expected_impact = self._estimate_market_impact(
                symbol, market_data, target_quantity
            )
            
            # Determine optimal execution time
            optimal_time = self._find_optimal_execution_time(
                symbol, market_data, execution_method
            )
            
            # Create timing signal
            timing_signal = TimingSignal(
                signal_type=self.config.timing_strategy,
                strength=signal_strength,
                confidence=confidence,
                confidence_level=self._get_confidence_level(confidence),
                optimal_time=optimal_time,
                execution_method=execution_method,
                expected_impact=expected_impact,
                metadata={
                    'symbol': symbol,
                    'target_quantity': target_quantity,
                    'current_regime': current_regime,
                    'generation_time': datetime.now(),
                    'market_data_points': len(market_data)
                }
            )
            
            # Cache signal if enabled
            if self.config.cache_timing_signals:
                with self._lock:
                    self._timing_signals_cache[symbol] = timing_signal
            
            # Update performance metrics
            self._update_timing_metrics(timing_signal)
            
            self.logger.debug(f"Generated timing signal for {symbol}: strength={signal_strength:.3f}, "
                            f"confidence={confidence:.3f}, method={execution_method.value}")
            
            return timing_signal
            
        except Exception as e:
            self.logger.error(f"Error generating timing signal for {symbol}: {e}")
            return None
    
    def _validate_market_data(self, market_data: pd.DataFrame) -> bool:
        """Validate market data for timing analysis"""
        if market_data.empty:
            return False
        
        if len(market_data) < self.config.lookback_window:
            self.logger.debug(f"Insufficient data: {len(market_data)} < {self.config.lookback_window}")
            return False
        
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in market_data.columns for col in required_columns):
            self.logger.warning("Missing required OHLCV columns")
            return False
        
        return True
    
    def _calculate_timing_signal(self, 
                               market_data: pd.DataFrame,
                               current_regime: Optional[str] = None) -> Tuple[float, float]:
        """Calculate timing signal strength and confidence"""
        try:
            signal_strength = 0.0
            confidence = 0.0
            
            if self.config.timing_strategy == TimingStrategy.MOMENTUM:
                signal_strength, confidence = self._momentum_timing_signal(market_data)
            
            elif self.config.timing_strategy == TimingStrategy.MEAN_REVERSION:
                signal_strength, confidence = self._mean_reversion_timing_signal(market_data)
            
            elif self.config.timing_strategy == TimingStrategy.REGIME_BASED:
                signal_strength, confidence = self._regime_based_timing_signal(market_data, current_regime)
            
            elif self.config.timing_strategy == TimingStrategy.VOLUME_WEIGHTED:
                signal_strength, confidence = self._volume_weighted_timing_signal(market_data)
            
            elif self.config.timing_strategy == TimingStrategy.VOLATILITY_BASED:
                signal_strength, confidence = self._volatility_based_timing_signal(market_data)
            
            elif self.config.timing_strategy == TimingStrategy.LIQUIDITY_BASED:
                signal_strength, confidence = self._liquidity_based_timing_signal(market_data)
            
            else:
                signal_strength, confidence = 0.0, 0.5  # Neutral signal
            
            # Ensure signal is in valid range
            signal_strength = np.clip(signal_strength, -1.0, 1.0)
            confidence = np.clip(confidence, 0.0, 1.0)
            
            return signal_strength, confidence
            
        except Exception as e:
            self.logger.error(f"Error calculating timing signal: {e}")
            return 0.0, 0.0
    
    def _momentum_timing_signal(self, market_data: pd.DataFrame) -> Tuple[float, float]:
        """Generate momentum-based timing signal"""
        try:
            close = market_data['close']
            volume = market_data['volume']
            
            # Price momentum
            if len(close) >= self.config.momentum_window:
                price_momentum = (close.iloc[-1] - close.iloc[-self.config.momentum_window]) / close.iloc[-self.config.momentum_window]
                
                # Volume momentum
                vol_ma = volume.rolling(self.config.momentum_window).mean()
                volume_momentum = volume.iloc[-1] / vol_ma.iloc[-1] if vol_ma.iloc[-1] > 0 else 1.0
                
                # Combined momentum signal
                signal_strength = np.tanh(price_momentum * 10) * min(volume_momentum, 2.0) / 2.0
                
                # Confidence based on consistency
                price_changes = close.pct_change().dropna()
                if len(price_changes) >= 5:
                    recent_changes = price_changes.tail(5)
                    consistency = np.sum(np.sign(recent_changes) == np.sign(price_momentum)) / len(recent_changes)
                    confidence = min(0.9, 0.3 + consistency * 0.6)
                else:
                    confidence = 0.5
                
                return signal_strength, confidence
            
            return 0.0, 0.5
            
        except Exception as e:
            self.logger.warning(f"Error in momentum timing signal: {e}")
            return 0.0, 0.5
    
    def _mean_reversion_timing_signal(self, market_data: pd.DataFrame) -> Tuple[float, float]:
        """Generate mean reversion timing signal"""
        try:
            close = market_data['close']
            
            if len(close) >= self.config.lookback_window:
                # Calculate z-score
                rolling_mean = close.rolling(self.config.lookback_window).mean()
                rolling_std = close.rolling(self.config.lookback_window).std()
                
                current_price = close.iloc[-1]
                z_score = (current_price - rolling_mean.iloc[-1]) / rolling_std.iloc[-1] if rolling_std.iloc[-1] > 0 else 0.0
                
                # Mean reversion signal (negative z-score = buy signal for mean reversion)
                signal_strength = -np.tanh(z_score / self.config.mean_reversion_threshold)
                
                # Confidence based on z-score magnitude
                confidence = min(0.9, abs(z_score) / self.config.mean_reversion_threshold)
                
                return signal_strength, confidence
            
            return 0.0, 0.5
            
        except Exception as e:
            self.logger.warning(f"Error in mean reversion timing signal: {e}")
            return 0.0, 0.5
    
    def _regime_based_timing_signal(self, 
                                  market_data: pd.DataFrame,
                                  current_regime: Optional[str] = None) -> Tuple[float, float]:
        """Generate regime-based timing signal"""
        try:
            # If no regime provided, estimate it
            if current_regime is None:
                current_regime = self._estimate_current_regime(market_data)
            
            # Regime-specific timing signals
            if current_regime in ['trending', 'momentum']:
                # In trending regimes, follow momentum
                return self._momentum_timing_signal(market_data)
            
            elif current_regime in ['mean_reverting', 'stable']:
                # In mean reverting regimes, use mean reversion
                return self._mean_reversion_timing_signal(market_data)
            
            elif current_regime in ['volatile', 'crisis']:
                # In volatile regimes, wait for stability
                volatility = market_data['close'].pct_change().std()
                signal_strength = -min(1.0, volatility * 50)  # Wait signal
                confidence = min(0.8, volatility * 25)
                return signal_strength, confidence
            
            else:
                # Unknown regime, use neutral signal
                return 0.0, 0.5
                
        except Exception as e:
            self.logger.warning(f"Error in regime-based timing signal: {e}")
            return 0.0, 0.5
    
    def _volume_weighted_timing_signal(self, market_data: pd.DataFrame) -> Tuple[float, float]:
        """Generate volume-weighted timing signal"""
        try:
            volume = market_data['volume']
            
            if len(volume) >= 10:
                # Volume profile analysis
                avg_volume = volume.rolling(20).mean().iloc[-1] if len(volume) >= 20 else volume.mean()
                current_volume = volume.iloc[-1]
                
                # High volume = good timing for execution
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
                
                # Signal strength based on volume
                if volume_ratio > 1.5:
                    signal_strength = min(1.0, (volume_ratio - 1.0) * 2.0)
                    confidence = min(0.9, volume_ratio / 3.0)
                elif volume_ratio < 0.5:
                    signal_strength = -0.5  # Wait for higher volume
                    confidence = 0.7
                else:
                    signal_strength = (volume_ratio - 1.0) * 0.5
                    confidence = 0.6
                
                return signal_strength, confidence
            
            return 0.0, 0.5
            
        except Exception as e:
            self.logger.warning(f"Error in volume-weighted timing signal: {e}")
            return 0.0, 0.5
    
    def _volatility_based_timing_signal(self, market_data: pd.DataFrame) -> Tuple[float, float]:
        """Generate volatility-based timing signal"""
        try:
            returns = market_data['close'].pct_change().dropna()
            
            if len(returns) >= 10:
                # Current vs historical volatility
                current_vol = returns.tail(5).std()
                historical_vol = returns.std()
                
                vol_ratio = current_vol / historical_vol if historical_vol > 0 else 1.0
                
                # Lower volatility = better timing for execution
                if vol_ratio < 0.8:
                    signal_strength = min(1.0, (0.8 - vol_ratio) * 5.0)
                    confidence = min(0.9, (0.8 - vol_ratio) * 3.0)
                elif vol_ratio > 1.5:
                    signal_strength = -min(1.0, (vol_ratio - 1.5) * 2.0)  # Wait signal
                    confidence = min(0.8, (vol_ratio - 1.0) * 0.5)
                else:
                    signal_strength = (0.8 - vol_ratio) * 2.0
                    confidence = 0.6
                
                return signal_strength, confidence
            
            return 0.0, 0.5
            
        except Exception as e:
            self.logger.warning(f"Error in volatility-based timing signal: {e}")
            return 0.0, 0.5
    
    def _liquidity_based_timing_signal(self, market_data: pd.DataFrame) -> Tuple[float, float]:
        """Generate liquidity-based timing signal"""
        try:
            # Liquidity proxy: volume / price_range
            high = market_data['high']
            low = market_data['low']
            volume = market_data['volume']
            close = market_data['close']
            
            if len(market_data) >= 10:
                price_range = (high - low) / close
                liquidity_proxy = volume / (price_range * close)
                
                # Current vs average liquidity
                avg_liquidity = liquidity_proxy.rolling(10).mean().iloc[-1] if len(liquidity_proxy) >= 10 else liquidity_proxy.mean()
                current_liquidity = liquidity_proxy.iloc[-1]
                
                liquidity_ratio = current_liquidity / avg_liquidity if avg_liquidity > 0 else 1.0
                
                # Higher liquidity = better timing
                if liquidity_ratio > 1.2:
                    signal_strength = min(1.0, (liquidity_ratio - 1.0) * 2.0)
                    confidence = min(0.9, liquidity_ratio / 2.0)
                elif liquidity_ratio < 0.7:
                    signal_strength = -0.6  # Wait for better liquidity
                    confidence = 0.7
                else:
                    signal_strength = (liquidity_ratio - 1.0) * 1.0
                    confidence = 0.6
                
                return signal_strength, confidence
            
            return 0.0, 0.5
            
        except Exception as e:
            self.logger.warning(f"Error in liquidity-based timing signal: {e}")
            return 0.0, 0.5
    
    def _estimate_current_regime(self, market_data: pd.DataFrame) -> str:
        """Estimate current market regime from data"""
        try:
            returns = market_data['close'].pct_change().dropna()
            
            if len(returns) >= 10:
                volatility = returns.std()
                
                # Autocorrelation for mean reversion
                if len(returns) > 1:
                    autocorr = np.corrcoef(returns[:-1], returns[1:])[0, 1] if len(returns) > 1 else 0.0
                else:
                    autocorr = 0.0
                
                # Simple regime classification
                if volatility > 0.03:
                    return 'volatile'
                elif autocorr < -0.1:
                    return 'mean_reverting'
                elif abs(returns.mean()) > volatility:
                    return 'trending'
                else:
                    return 'stable'
            
            return 'unknown'
            
        except Exception as e:
            self.logger.warning(f"Error estimating regime: {e}")
            return 'unknown'
    
    def _select_execution_method(self, 
                               symbol: str,
                               market_data: pd.DataFrame,
                               target_quantity: float) -> ExecutionTiming:
        """Select optimal execution method"""
        try:
            # Default method from config
            if self.config.execution_timing != ExecutionTiming.OPTIMAL_LIQUIDITY:
                return self.config.execution_timing
            
            # Analyze market conditions to select method
            volume = market_data['volume']
            volatility = market_data['close'].pct_change().std()
            
            avg_volume = volume.mean()
            quantity_as_volume_pct = abs(target_quantity) / avg_volume if avg_volume > 0 else 0.1
            
            # Large orders in low volatility -> VWAP
            if quantity_as_volume_pct > 0.05 and volatility < 0.02:
                return ExecutionTiming.VWAP
            
            # Small orders in high volatility -> Immediate
            elif quantity_as_volume_pct < 0.01 or volatility > 0.04:
                return ExecutionTiming.IMMEDIATE
            
            # Medium orders -> TWAP
            else:
                return ExecutionTiming.TWAP
                
        except Exception as e:
            self.logger.warning(f"Error selecting execution method: {e}")
            return ExecutionTiming.IMMEDIATE
    
    def _estimate_market_impact(self, 
                              symbol: str,
                              market_data: pd.DataFrame,
                              target_quantity: float) -> float:
        """Estimate expected market impact"""
        try:
            volume = market_data['volume']
            close = market_data['close']
            
            if len(volume) == 0:
                return 0.01  # Default 1% impact
            
            avg_volume = volume.mean()
            avg_price = close.mean()
            
            # Simple impact model: impact proportional to order size relative to volume
            volume_participation = abs(target_quantity) / avg_volume if avg_volume > 0 else 0.1
            
            # Square root impact model
            base_impact = np.sqrt(volume_participation) * 0.01  # 1% per 100% volume participation
            
            # Adjust for volatility
            volatility = close.pct_change().std()
            volatility_adjustment = min(2.0, volatility * 50)  # Higher volatility = higher impact
            
            total_impact = base_impact * volatility_adjustment
            
            return min(0.05, total_impact)  # Cap at 5%
            
        except Exception as e:
            self.logger.warning(f"Error estimating market impact: {e}")
            return 0.01
    
    def _find_optimal_execution_time(self, 
                                   symbol: str,
                                   market_data: pd.DataFrame,
                                   execution_method: ExecutionTiming) -> Optional[datetime]:
        """Find optimal execution time"""
        try:
            current_time = datetime.now()
            
            if execution_method == ExecutionTiming.IMMEDIATE:
                return current_time
            
            elif execution_method == ExecutionTiming.MARKET_OPEN:
                # Next market open
                next_open = current_time.replace(
                    hour=self.market_open.hour,
                    minute=self.market_open.minute,
                    second=0, microsecond=0
                )
                if next_open <= current_time:
                    next_open += timedelta(days=1)
                return next_open
            
            elif execution_method == ExecutionTiming.MARKET_CLOSE:
                # Next market close
                next_close = current_time.replace(
                    hour=self.market_close.hour,
                    minute=self.market_close.minute,
                    second=0, microsecond=0
                )
                if next_close <= current_time:
                    next_close += timedelta(days=1)
                return next_close
            
            elif execution_method in [ExecutionTiming.VWAP, ExecutionTiming.TWAP]:
                # Start execution within next hour
                return current_time + timedelta(minutes=30)
            
            elif execution_method == ExecutionTiming.OPTIMAL_LIQUIDITY:
                # Find time with historically high liquidity
                return self._find_high_liquidity_time(market_data)
            
            else:
                return current_time + timedelta(minutes=15)  # Default delay
                
        except Exception as e:
            self.logger.warning(f"Error finding optimal execution time: {e}")
            return datetime.now()
    
    def _find_high_liquidity_time(self, market_data: pd.DataFrame) -> datetime:
        """Find time with historically high liquidity"""
        try:
            # Simple heuristic: market open + 30 minutes typically has high liquidity
            current_time = datetime.now()
            optimal_time = current_time.replace(
                hour=10, minute=0, second=0, microsecond=0
            )
            
            # If already past optimal time, use current time
            if optimal_time <= current_time:
                return current_time + timedelta(minutes=5)
            
            return optimal_time
            
        except Exception as e:
            self.logger.warning(f"Error finding high liquidity time: {e}")
            return datetime.now()
    
    def _get_confidence_level(self, confidence: float) -> TimingConfidence:
        """Convert numeric confidence to confidence level"""
        if confidence >= 0.9:
            return TimingConfidence.VERY_HIGH
        elif confidence >= 0.75:
            return TimingConfidence.HIGH
        elif confidence >= 0.5:
            return TimingConfidence.MEDIUM
        elif confidence >= 0.25:
            return TimingConfidence.LOW
        else:
            return TimingConfidence.VERY_LOW
    
    def _update_timing_metrics(self, timing_signal: TimingSignal):
        """Update timing performance metrics"""
        self.performance_metrics['signals_generated'] += 1
        
        # Update rolling averages would be implemented here
        # This would track actual execution results vs predictions
        
        self.performance_metrics['last_update'] = datetime.now()
    
    def get_execution_window(self, 
                           symbol: str,
                           market_data: pd.DataFrame,
                           target_quantity: float,
                           max_duration_minutes: int = 60) -> Optional[ExecutionWindow]:
        """Get optimal execution window"""
        try:
            current_time = datetime.now()
            
            # Simple execution window based on market hours
            start_time = current_time
            end_time = min(
                current_time + timedelta(minutes=max_duration_minutes),
                current_time.replace(hour=16, minute=0, second=0, microsecond=0)  # Market close
            )
            
            # Estimate window characteristics
            avg_volume = market_data['volume'].mean() if len(market_data) > 0 else 1000000
            expected_volume = avg_volume * (max_duration_minutes / (6.5 * 60))  # Pro-rated for market hours
            
            volatility = market_data['close'].pct_change().std() if len(market_data) > 0 else 0.02
            
            # Simple liquidity score
            liquidity_score = min(1.0, expected_volume / abs(target_quantity)) if target_quantity != 0 else 1.0
            
            # Impact estimate
            impact_estimate = self._estimate_market_impact(symbol, market_data, target_quantity)
            
            return ExecutionWindow(
                start_time=start_time,
                end_time=end_time,
                expected_volume=expected_volume,
                expected_volatility=volatility,
                liquidity_score=liquidity_score,
                impact_estimate=impact_estimate,
                confidence=0.7  # Default confidence
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating execution window: {e}")
            return None
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get timing performance metrics"""
        return self.performance_metrics.copy()

# Backward compatibility aliases
TimingOptimizer = TimingEngine
ExecutionTimer = TimingEngine
LiquidityTimer = TimingEngine

__all__ = [
    'TimingEngine',
    'TimingOptimizer',  # Backward compatibility
    'ExecutionTimer',  # Backward compatibility
    'LiquidityTimer',  # Backward compatibility
    'TimingSignal',
    'ExecutionWindow',
    'TimingStrategy',
    'ExecutionTiming',
    'TimingConfidence',
    'TimingConfig'
]
