"""
Trade Timing Optimization Module - Phase 3 Enhancement
Implements optimal trade timing based on market microstructure and volatility patterns
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@dataclass
class TimingConfig:
    """Configuration for trade timing optimization"""
    # Volatility timing settings
    volatility_lookback: int = 20
    volatility_threshold: float = 0.03  # 3% volatility threshold
    low_volatility_multiplier: float = 1.2  # 20% boost for low volatility
    
    # Volume timing settings
    volume_lookback: int = 10
    volume_threshold: float = 0.5  # 50% of average volume
    high_volume_multiplier: float = 1.1  # 10% boost for high volume
    
    # Time-based timing settings
    market_hours_boost: float = 1.15  # 15% boost during market hours
    pre_market_penalty: float = 0.8  # 20% penalty for pre-market
    after_hours_penalty: float = 0.7  # 30% penalty for after-hours
    
    # Momentum timing settings
    momentum_lookback: int = 5
    momentum_threshold: float = 0.01  # 1% momentum threshold
    momentum_boost: float = 1.1  # 10% boost for momentum alignment
    
    # Spread timing settings
    max_spread_threshold: float = 0.002  # 0.2% max spread
    spread_penalty: float = 0.9  # 10% penalty for wide spreads

class TradeTimingOptimizer:
    """Optimize trade timing based on market microstructure"""
    
    def __init__(self, config: Optional[TimingConfig] = None):
        self.config = config or TimingConfig()
        self.timing_history = []
        self.timing_stats = {
            'timing_optimizations': 0,
            'timing_improvements': 0,
            'avg_timing_boost': 0.0,
            'best_timing_windows': {}
        }
    
    def optimize_trade_timing(
        self,
        signal: Dict[str, Any],
        market_data: pd.DataFrame,
        current_time: datetime
    ) -> Dict[str, Any]:
        """
        Optimize trade timing based on market conditions
        
        Args:
            signal: Original trading signal
            market_data: Historical market data
            current_time: Current market time
        
        Returns:
            Optimized signal with timing adjustments
        """
        try:
            optimized_signal = signal.copy()
            
            # Calculate timing factors
            volatility_factor = self._calculate_volatility_timing(market_data)
            volume_factor = self._calculate_volume_timing(market_data)
            time_factor = self._calculate_time_based_timing(current_time)
            momentum_factor = self._calculate_momentum_timing(market_data, signal)
            spread_factor = self._calculate_spread_timing(market_data)
            
            # Combine timing factors
            timing_multiplier = (
                volatility_factor * 
                volume_factor * 
                time_factor * 
                momentum_factor * 
                spread_factor
            )
            
            # Apply timing optimization
            original_confidence = signal.get('confidence', 0.5)
            optimized_confidence = original_confidence * timing_multiplier
            
            # Ensure confidence stays within bounds
            optimized_confidence = max(0.1, min(1.0, optimized_confidence))
            
            # Update signal
            optimized_signal['confidence'] = optimized_confidence
            optimized_signal['timing_multiplier'] = timing_multiplier
            optimized_signal['timing_factors'] = {
                'volatility': volatility_factor,
                'volume': volume_factor,
                'time': time_factor,
                'momentum': momentum_factor,
                'spread': spread_factor
            }
            
            # Add timing metadata
            metadata = optimized_signal.get('metadata', {})
            metadata.update({
                'timing_optimized': True,
                'timing_boost': timing_multiplier - 1.0,
                'phase3_enhanced': True
            })
            optimized_signal['metadata'] = metadata
            
            # Update statistics
            self.timing_stats['timing_optimizations'] += 1
            if timing_multiplier > 1.0:
                self.timing_stats['timing_improvements'] += 1
            
            # Update average timing boost
            current_avg = self.timing_stats['avg_timing_boost']
            total_optimizations = self.timing_stats['timing_optimizations']
            self.timing_stats['avg_timing_boost'] = (
                (current_avg * (total_optimizations - 1) + (timing_multiplier - 1.0)) / total_optimizations
            )
            
            # Store timing history
            self.timing_history.append({
                'timestamp': current_time,
                'original_confidence': original_confidence,
                'optimized_confidence': optimized_confidence,
                'timing_multiplier': timing_multiplier,
                'timing_factors': optimized_signal['timing_factors']
            })
            
            logger.debug(f"Trade timing optimized: multiplier={timing_multiplier:.3f}, "
                        f"confidence: {original_confidence:.3f}→{optimized_confidence:.3f}")
            
            return optimized_signal
            
        except Exception as e:
            logger.error(f"Trade timing optimization failed: {e}")
            return signal
    
    def _calculate_volatility_timing(self, market_data: pd.DataFrame) -> float:
        """Calculate volatility-based timing factor"""
        try:
            if len(market_data) < self.config.volatility_lookback:
                return 1.0
            
            # Calculate recent volatility
            returns = market_data['close'].pct_change().dropna()
            recent_volatility = returns.tail(self.config.volatility_lookback).std()
            
            # Calculate historical volatility for comparison
            historical_volatility = returns.std()
            
            # Determine volatility factor
            if recent_volatility < self.config.volatility_threshold:
                # Low volatility - good for trading
                volatility_factor = self.config.low_volatility_multiplier
            elif recent_volatility > historical_volatility * 1.5:
                # High volatility - reduce trading
                volatility_factor = 0.8
            else:
                # Normal volatility
                volatility_factor = 1.0
            
            return volatility_factor
            
        except Exception as e:
            logger.error(f"Volatility timing calculation failed: {e}")
            return 1.0
    
    def _calculate_volume_timing(self, market_data: pd.DataFrame) -> float:
        """Calculate volume-based timing factor"""
        try:
            if 'volume' not in market_data.columns or len(market_data) < self.config.volume_lookback:
                return 1.0
            
            # Calculate recent volume
            recent_volume = market_data['volume'].tail(self.config.volume_lookback).mean()
            historical_volume = market_data['volume'].mean()
            
            # Determine volume factor
            if recent_volume > historical_volume * (1 + self.config.volume_threshold):
                # High volume - good for trading
                volume_factor = self.config.high_volume_multiplier
            elif recent_volume < historical_volume * (1 - self.config.volume_threshold):
                # Low volume - reduce trading
                volume_factor = 0.9
            else:
                # Normal volume
                volume_factor = 1.0
            
            return volume_factor
            
        except Exception as e:
            logger.error(f"Volume timing calculation failed: {e}")
            return 1.0
    
    def _calculate_time_based_timing(self, current_time: datetime) -> float:
        """Calculate time-based timing factor"""
        try:
            # Extract hour and minute
            hour = current_time.hour
            minute = current_time.minute
            
            # Define market hours (9:30 AM - 4:00 PM ET)
            market_open = 9.5  # 9:30 AM
            market_close = 16.0  # 4:00 PM
            
            # Convert current time to decimal hours
            current_hour = hour + minute / 60.0
            
            # Determine time factor
            if market_open <= current_hour <= market_close:
                # Market hours - optimal for trading
                time_factor = self.config.market_hours_boost
            elif 8.0 <= current_hour < market_open:
                # Pre-market - reduced trading
                time_factor = self.config.pre_market_penalty
            elif market_close < current_hour <= 18.0:
                # After-hours - further reduced trading
                time_factor = self.config.after_hours_penalty
            else:
                # Off-hours - minimal trading
                time_factor = 0.5
            
            return time_factor
            
        except Exception as e:
            logger.error(f"Time-based timing calculation failed: {e}")
            return 1.0
    
    def _calculate_momentum_timing(
        self,
        market_data: pd.DataFrame,
        signal: Dict[str, Any]
    ) -> float:
        """Calculate momentum-based timing factor"""
        try:
            if len(market_data) < self.config.momentum_lookback:
                return 1.0
            
            # Calculate recent momentum
            close_prices = market_data['close'].values
            recent_momentum = (close_prices[-1] / close_prices[-self.config.momentum_lookback] - 1)
            
            # Get signal direction
            signal_type = signal.get('signal_type', 'HOLD')
            
            # Determine momentum alignment
            if signal_type == 'LONG' and recent_momentum > self.config.momentum_threshold:
                # Positive momentum for long signal - good alignment
                momentum_factor = self.config.momentum_boost
            elif signal_type == 'SHORT' and recent_momentum < -self.config.momentum_threshold:
                # Negative momentum for short signal - good alignment
                momentum_factor = self.config.momentum_boost
            elif signal_type == 'LONG' and recent_momentum < -self.config.momentum_threshold:
                # Negative momentum for long signal - poor alignment
                momentum_factor = 0.9
            elif signal_type == 'SHORT' and recent_momentum > self.config.momentum_threshold:
                # Positive momentum for short signal - poor alignment
                momentum_factor = 0.9
            else:
                # Neutral momentum
                momentum_factor = 1.0
            
            return momentum_factor
            
        except Exception as e:
            logger.error(f"Momentum timing calculation failed: {e}")
            return 1.0
    
    def _calculate_spread_timing(self, market_data: pd.DataFrame) -> float:
        """Calculate spread-based timing factor"""
        try:
            # Check if we have bid/ask data
            if 'bid' not in market_data.columns or 'ask' not in market_data.columns:
                return 1.0
            
            # Calculate recent spread
            recent_data = market_data.tail(5)
            spreads = (recent_data['ask'] - recent_data['bid']) / recent_data['bid']
            avg_spread = spreads.mean()
            
            # Determine spread factor
            if avg_spread > self.config.max_spread_threshold:
                # Wide spread - reduce trading
                spread_factor = self.config.spread_penalty
            elif avg_spread < self.config.max_spread_threshold * 0.5:
                # Tight spread - good for trading
                spread_factor = 1.05
            else:
                # Normal spread
                spread_factor = 1.0
            
            return spread_factor
            
        except Exception as e:
            logger.error(f"Spread timing calculation failed: {e}")
            return 1.0
    
    def get_optimal_trading_windows(self) -> Dict[str, Any]:
        """Analyze timing history to identify optimal trading windows"""
        try:
            if not self.timing_history:
                return {}
            
            # Group by hour
            hourly_performance = {}
            for entry in self.timing_history:
                hour = entry['timestamp'].hour
                boost = entry['timing_multiplier'] - 1.0
                
                if hour not in hourly_performance:
                    hourly_performance[hour] = []
                hourly_performance[hour].append(boost)
            
            # Calculate average boost by hour
            optimal_hours = {}
            for hour, boosts in hourly_performance.items():
                avg_boost = np.mean(boosts)
                optimal_hours[f"{hour:02d}:00"] = avg_boost
            
            # Sort by performance
            sorted_hours = sorted(optimal_hours.items(), key=lambda x: x[1], reverse=True)
            
            # Update best timing windows
            self.timing_stats['best_timing_windows'] = {
                'top_hours': sorted_hours[:3],
                'worst_hours': sorted_hours[-3:],
                'overall_avg_boost': self.timing_stats['avg_timing_boost']
            }
            
            return self.timing_stats['best_timing_windows']
            
        except Exception as e:
            logger.error(f"Optimal trading windows analysis failed: {e}")
            return {}
    
    def get_timing_summary(self) -> Dict[str, Any]:
        """Get current timing optimization statistics"""
        optimal_windows = self.get_optimal_trading_windows()
        
        return {
            'timing_optimizations': self.timing_stats['timing_optimizations'],
            'timing_improvements': self.timing_stats['timing_improvements'],
            'avg_timing_boost': self.timing_stats['avg_timing_boost'],
            'improvement_rate': (
                self.timing_stats['timing_improvements'] / self.timing_stats['timing_optimizations']
                if self.timing_stats['timing_optimizations'] > 0 else 0.0
            ),
            'best_timing_windows': optimal_windows,
            'total_history_entries': len(self.timing_history)
        }
