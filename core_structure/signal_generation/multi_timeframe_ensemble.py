"""
Multi-Timeframe Signal Ensemble Module - Phase 3 Enhancement
Implements signal combination from multiple timeframes for enhanced signal quality
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TimeframeType(Enum):
    """Supported timeframes for signal generation"""
    M1 = "1min"
    M5 = "5min"
    M15 = "15min"
    M30 = "30min"
    H1 = "1hour"
    H4 = "4hour"
    D1 = "1day"

@dataclass
class EnsembleConfig:
    """Configuration for multi-timeframe signal ensemble"""
    # Timeframe settings
    primary_timeframe: str = "1hour"
    secondary_timeframes: List[str] = None
    ensemble_method: str = "weighted_average"  # weighted_average, voting, kalman
    
    # Weight settings
    primary_weight: float = 0.4
    secondary_weights: Dict[str, float] = None
    
    # Consensus settings
    min_agreement_threshold: float = 0.6  # 60% agreement required
    consensus_boost: float = 1.2  # 20% boost for consensus signals
    
    # Signal alignment settings
    max_signal_delay_minutes: int = 30  # Maximum delay between timeframes
    alignment_tolerance: float = 0.1  # 10% tolerance for signal alignment
    
    def __post_init__(self):
        if self.secondary_timeframes is None:
            self.secondary_timeframes = ["15min", "4hour"]
        
        if self.secondary_weights is None:
            self.secondary_weights = {
                "15min": 0.3,
                "4hour": 0.3
            }

class MultiTimeframeEnsemble:
    """Multi-timeframe signal ensemble for enhanced signal quality"""
    
    def __init__(self, config: Optional[EnsembleConfig] = None):
        self.config = config or EnsembleConfig()
        self.signal_history = {}
        self.ensemble_stats = {
            'signals_generated': 0,
            'consensus_signals': 0,
            'timeframe_agreement_rate': 0.0,
            'ensemble_improvement': 0.0
        }
    
    def generate_ensemble_signal(
        self,
        symbol: str,
        market_data: Dict[str, pd.DataFrame],
        base_signal: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate ensemble signal from multiple timeframes
        
        Args:
            symbol: Trading symbol
            market_data: Dictionary of market data by timeframe
            base_signal: Base signal from primary timeframe
        
        Returns:
            Ensemble signal with enhanced confidence and metadata
        """
        try:
            # Generate signals for each timeframe
            timeframe_signals = {}
            
            for timeframe in [self.config.primary_timeframe] + self.config.secondary_timeframes:
                if timeframe in market_data and len(market_data[timeframe]) > 0:
                    signal = self._generate_timeframe_signal(
                        symbol, market_data[timeframe], timeframe
                    )
                    if signal:
                        timeframe_signals[timeframe] = signal
            
            if not timeframe_signals:
                logger.warning(f"No valid signals generated for {symbol}")
                return base_signal
            
            # Combine signals using ensemble method
            if self.config.ensemble_method == "weighted_average":
                ensemble_signal = self._weighted_average_ensemble(timeframe_signals)
            elif self.config.ensemble_method == "voting":
                ensemble_signal = self._voting_ensemble(timeframe_signals)
            elif self.config.ensemble_method == "kalman":
                ensemble_signal = self._kalman_ensemble(timeframe_signals)
            else:
                ensemble_signal = self._weighted_average_ensemble(timeframe_signals)
            
            # Check for consensus
            consensus_level = self._calculate_consensus(timeframe_signals)
            if consensus_level >= self.config.min_agreement_threshold:
                ensemble_signal['confidence'] *= self.config.consensus_boost
                ensemble_signal['metadata']['consensus'] = True
                ensemble_signal['metadata']['consensus_level'] = consensus_level
                self.ensemble_stats['consensus_signals'] += 1
            
            # Update statistics
            self.ensemble_stats['signals_generated'] += 1
            self.ensemble_stats['timeframe_agreement_rate'] = (
                self.ensemble_stats['consensus_signals'] / self.ensemble_stats['signals_generated']
            )
            
            # Store signal history
            self.signal_history[symbol] = {
                'timestamp': datetime.now(),
                'ensemble_signal': ensemble_signal,
                'timeframe_signals': timeframe_signals,
                'consensus_level': consensus_level
            }
            
            logger.debug(f"Ensemble signal generated for {symbol}: "
                        f"confidence={ensemble_signal['confidence']:.3f}, "
                        f"consensus={consensus_level:.3f}")
            
            return ensemble_signal
            
        except Exception as e:
            logger.error(f"Ensemble signal generation failed for {symbol}: {e}")
            return base_signal
    
    def _generate_timeframe_signal(
        self,
        symbol: str,
        market_data: pd.DataFrame,
        timeframe: str
    ) -> Optional[Dict[str, Any]]:
        """Generate signal for a specific timeframe"""
        try:
            if len(market_data) < 20:
                return None
            
            # Calculate basic signal components
            close_prices = market_data['close'].values
            returns = np.diff(close_prices) / close_prices[:-1]
            
            # Calculate momentum indicators
            momentum_5 = (close_prices[-1] / close_prices[-5] - 1) if len(close_prices) >= 5 else 0
            momentum_10 = (close_prices[-1] / close_prices[-10] - 1) if len(close_prices) >= 10 else 0
            momentum_20 = (close_prices[-1] / close_prices[-20] - 1) if len(close_prices) >= 20 else 0
            
            # Calculate volatility
            volatility = np.std(returns[-20:]) if len(returns) >= 20 else 0.02
            
            # Calculate trend strength
            trend_strength = self._calculate_trend_strength(close_prices)
            
            # Determine signal type and confidence
            signal_type, confidence = self._determine_signal_type(
                momentum_5, momentum_10, momentum_20, trend_strength, volatility
            )
            
            # Adjust confidence based on timeframe
            timeframe_confidence = self._adjust_confidence_for_timeframe(confidence, timeframe)
            
            return {
                'timeframe': timeframe,
                'signal_type': signal_type,
                'confidence': timeframe_confidence,
                'momentum_5': momentum_5,
                'momentum_10': momentum_10,
                'momentum_20': momentum_20,
                'trend_strength': trend_strength,
                'volatility': volatility,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Timeframe signal generation failed for {timeframe}: {e}")
            return None
    
    def _weighted_average_ensemble(
        self,
        timeframe_signals: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Combine signals using weighted average method"""
        try:
            # Initialize ensemble signal
            ensemble_signal = {
                'signal_type': 'HOLD',
                'confidence': 0.0,
                'metadata': {
                    'ensemble_method': 'weighted_average',
                    'timeframes_used': list(timeframe_signals.keys()),
                    'phase3_enhanced': True
                }
            }
            
            # Calculate weighted confidence
            total_weight = 0.0
            weighted_confidence = 0.0
            signal_types = []
            
            for timeframe, signal in timeframe_signals.items():
                # Get weight for this timeframe
                if timeframe == self.config.primary_timeframe:
                    weight = self.config.primary_weight
                else:
                    weight = self.config.secondary_weights.get(timeframe, 0.1)
                
                weighted_confidence += signal['confidence'] * weight
                total_weight += weight
                signal_types.append(signal['signal_type'])
            
            if total_weight > 0:
                ensemble_signal['confidence'] = weighted_confidence / total_weight
            
            # Determine ensemble signal type (majority vote)
            signal_type_counts = {}
            for signal_type in signal_types:
                signal_type_counts[signal_type] = signal_type_counts.get(signal_type, 0) + 1
            
            # Get most common signal type
            if signal_type_counts:
                ensemble_signal['signal_type'] = max(signal_type_counts, key=signal_type_counts.get)
            
            return ensemble_signal
            
        except Exception as e:
            logger.error(f"Weighted average ensemble failed: {e}")
            return {'signal_type': 'HOLD', 'confidence': 0.0}
    
    def _voting_ensemble(
        self,
        timeframe_signals: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Combine signals using voting method"""
        try:
            # Count votes for each signal type
            votes = {'LONG': 0, 'SHORT': 0, 'HOLD': 0}
            total_confidence = 0.0
            
            for signal in timeframe_signals.values():
                signal_type = signal['signal_type']
                confidence = signal['confidence']
                
                if signal_type in votes:
                    votes[signal_type] += confidence
                total_confidence += confidence
            
            # Determine winning signal type
            winning_signal = max(votes, key=votes.get)
            
            # Calculate ensemble confidence
            ensemble_confidence = votes[winning_signal] / total_confidence if total_confidence > 0 else 0.0
            
            return {
                'signal_type': winning_signal,
                'confidence': ensemble_confidence,
                'metadata': {
                    'ensemble_method': 'voting',
                    'votes': votes,
                    'phase3_enhanced': True
                }
            }
            
        except Exception as e:
            logger.error(f"Voting ensemble failed: {e}")
            return {'signal_type': 'HOLD', 'confidence': 0.0}
    
    def _kalman_ensemble(
        self,
        timeframe_signals: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Combine signals using Kalman filter method (simplified)"""
        try:
            # Simplified Kalman filter implementation
            # In a full implementation, this would track signal state over time
            
            # Calculate weighted average with uncertainty
            total_weight = 0.0
            weighted_confidence = 0.0
            signal_types = []
            
            for timeframe, signal in timeframe_signals.items():
                # Higher weight for more recent timeframes
                if timeframe == self.config.primary_timeframe:
                    weight = self.config.primary_weight
                else:
                    weight = self.config.secondary_weights.get(timeframe, 0.1)
                
                # Adjust weight based on signal uncertainty (inverse of volatility)
                uncertainty = signal.get('volatility', 0.02)
                adjusted_weight = weight / (1 + uncertainty * 10)
                
                weighted_confidence += signal['confidence'] * adjusted_weight
                total_weight += adjusted_weight
                signal_types.append(signal['signal_type'])
            
            ensemble_confidence = weighted_confidence / total_weight if total_weight > 0 else 0.0
            
            # Determine signal type
            signal_type_counts = {}
            for signal_type in signal_types:
                signal_type_counts[signal_type] = signal_type_counts.get(signal_type, 0) + 1
            
            ensemble_signal_type = max(signal_type_counts, key=signal_type_counts.get) if signal_type_counts else 'HOLD'
            
            return {
                'signal_type': ensemble_signal_type,
                'confidence': ensemble_confidence,
                'metadata': {
                    'ensemble_method': 'kalman',
                    'phase3_enhanced': True
                }
            }
            
        except Exception as e:
            logger.error(f"Kalman ensemble failed: {e}")
            return {'signal_type': 'HOLD', 'confidence': 0.0}
    
    def _calculate_consensus(
        self,
        timeframe_signals: Dict[str, Dict[str, Any]]
    ) -> float:
        """Calculate consensus level across timeframes"""
        try:
            if len(timeframe_signals) < 2:
                return 0.0
            
            # Count signal types
            signal_types = [signal['signal_type'] for signal in timeframe_signals.values()]
            signal_type_counts = {}
            
            for signal_type in signal_types:
                signal_type_counts[signal_type] = signal_type_counts.get(signal_type, 0) + 1
            
            # Calculate consensus as percentage of most common signal type
            max_count = max(signal_type_counts.values())
            consensus = max_count / len(timeframe_signals)
            
            return consensus
            
        except Exception as e:
            logger.error(f"Consensus calculation failed: {e}")
            return 0.0
    
    def _calculate_trend_strength(self, prices: np.ndarray) -> float:
        """Calculate trend strength using linear regression"""
        try:
            if len(prices) < 10:
                return 0.0
            
            # Use recent prices for trend calculation
            recent_prices = prices[-10:]
            x = np.arange(len(recent_prices))
            
            # Linear regression
            slope, intercept = np.polyfit(x, recent_prices, 1)
            y_pred = slope * x + intercept
            
            # Calculate R-squared
            ss_res = np.sum((recent_prices - y_pred) ** 2)
            ss_tot = np.sum((recent_prices - np.mean(recent_prices)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
            
            return max(0.0, min(1.0, r_squared))
            
        except Exception as e:
            logger.error(f"Trend strength calculation failed: {e}")
            return 0.0
    
    def _determine_signal_type(
        self,
        momentum_5: float,
        momentum_10: float,
        momentum_20: float,
        trend_strength: float,
        volatility: float
    ) -> Tuple[str, float]:
        """Determine signal type and confidence based on momentum indicators"""
        try:
            # Calculate overall momentum score
            momentum_score = (momentum_5 * 0.5 + momentum_10 * 0.3 + momentum_20 * 0.2)
            
            # Adjust for volatility
            volatility_adjustment = 1.0 / (1.0 + volatility * 10)
            adjusted_score = momentum_score * volatility_adjustment
            
            # Determine signal type
            if adjusted_score > 0.02:  # 2% positive momentum
                signal_type = 'LONG'
                confidence = min(0.9, abs(adjusted_score) * 10 + trend_strength * 0.3)
            elif adjusted_score < -0.02:  # 2% negative momentum
                signal_type = 'SHORT'
                confidence = min(0.9, abs(adjusted_score) * 10 + trend_strength * 0.3)
            else:
                signal_type = 'HOLD'
                confidence = 0.5
            
            return signal_type, confidence
            
        except Exception as e:
            logger.error(f"Signal type determination failed: {e}")
            return 'HOLD', 0.5
    
    def _adjust_confidence_for_timeframe(self, confidence: float, timeframe: str) -> float:
        """Adjust confidence based on timeframe characteristics"""
        try:
            # Higher timeframes generally have more reliable signals
            timeframe_multipliers = {
                '1min': 0.7,
                '5min': 0.8,
                '15min': 0.9,
                '30min': 1.0,
                '1hour': 1.1,
                '4hour': 1.2,
                '1day': 1.3
            }
            
            multiplier = timeframe_multipliers.get(timeframe, 1.0)
            adjusted_confidence = confidence * multiplier
            
            return min(1.0, adjusted_confidence)
            
        except Exception as e:
            logger.error(f"Confidence adjustment failed: {e}")
            return confidence
    
    def get_ensemble_summary(self) -> Dict[str, Any]:
        """Get current ensemble statistics summary"""
        return {
            'signals_generated': self.ensemble_stats['signals_generated'],
            'consensus_signals': self.ensemble_stats['consensus_signals'],
            'timeframe_agreement_rate': self.ensemble_stats['timeframe_agreement_rate'],
            'ensemble_improvement': self.ensemble_stats['ensemble_improvement'],
            'total_timeframes': len(self.config.secondary_timeframes) + 1,
            'ensemble_method': self.config.ensemble_method
        }
