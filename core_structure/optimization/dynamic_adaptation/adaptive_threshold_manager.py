"""
Adaptive Threshold Manager for Dynamic Trading Strategy Thresholds.

This module implements regime-aware, performance-based adaptive thresholds
that replace all fixed threshold values in the trading system.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
import logging
from enum import Enum

from .adaptation_config import AdaptationConfig, AdaptationMode
from .parameter_optimizer import RealTimeParameterOptimizer
from ..memory import CacheManager


class ThresholdType(Enum):
    """Types of adaptive thresholds"""
    TECHNICAL_INDICATOR = "technical_indicator"
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    PAIRS_TRADING = "pairs_trading"
    RISK_MANAGEMENT = "risk_management"
    VOLUME = "volume"


@dataclass
class ThresholdBounds:
    """Bounds for adaptive threshold values"""
    min_value: float
    max_value: float
    default_value: float
    step_size: float = 0.01
    
    def __post_init__(self):
        if not (self.min_value <= self.default_value <= self.max_value):
            raise ValueError("Default value must be within bounds")


@dataclass
class AdaptiveThreshold:
    """Individual adaptive threshold configuration"""
    name: str
    threshold_type: ThresholdType
    bounds: ThresholdBounds
    current_value: float = field(init=False)
    last_updated: Optional[datetime] = None
    update_count: int = 0
    performance_history: List[float] = field(default_factory=list)
    market_condition_history: List[Dict[str, float]] = field(default_factory=list)
    
    def __post_init__(self):
        self.current_value = self.bounds.default_value
    
    def update_value(self, new_value: float, performance_score: float, 
                    market_conditions: Dict[str, float]) -> bool:
        """Update threshold value with validation and history tracking"""
        # Validate bounds
        if not (self.bounds.min_value <= new_value <= self.bounds.max_value):
            return False
        
        # Update value and history
        self.current_value = new_value
        self.last_updated = datetime.now()
        self.update_count += 1
        self.performance_history.append(performance_score)
        self.market_condition_history.append(market_conditions.copy())
        
        # Keep history manageable
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-50:]
            self.market_condition_history = self.market_condition_history[-50:]
        
        return True
    
    def get_value_with_regime_adjustment(self, regime_multiplier: float = 1.0) -> float:
        """Get current value adjusted for market regime"""
        adjusted_value = self.current_value * regime_multiplier
        return max(min(adjusted_value, self.bounds.max_value), self.bounds.min_value)


class AdaptiveThresholdManager:
    """
    Comprehensive adaptive threshold management system.
    
    This system replaces all fixed thresholds with intelligent, regime-aware,
    performance-based adaptive thresholds.
    """
    
    def __init__(self, 
                 strategy_id: str,
                 adaptation_config: Optional[AdaptationConfig] = None,
                 regime_engine: Optional[Any] = None):
        """
        Initialize adaptive threshold manager.
        
        Args:
            strategy_id: Unique identifier for strategy
            adaptation_config: Configuration for adaptation behavior
            regime_engine: Reference to regime detection engine
        """
        self.strategy_id = strategy_id
        self.config = adaptation_config or AdaptationConfig()
        self.regime_engine = regime_engine
        
        self.logger = logging.getLogger(__name__)
        self.cache_manager = CacheManager(f"thresholds_{strategy_id}")
        
        # Initialize threshold registry
        self.thresholds: Dict[str, AdaptiveThreshold] = {}
        self._initialize_default_thresholds()
        
        # Performance tracking
        self.performance_history: List[Dict[str, float]] = []
        self.last_performance_evaluation: Optional[datetime] = None
        
        # Market condition tracking
        self.current_market_conditions: Dict[str, float] = {}
        self.regime_multipliers: Dict[str, Dict[str, float]] = {}
        
        self._setup_regime_multipliers()
    
    def _initialize_default_thresholds(self) -> None:
        """Initialize all adaptive thresholds with sensible defaults"""
        
        # Technical indicator thresholds
        self._register_threshold("rsi_overbought", ThresholdType.TECHNICAL_INDICATOR,
                                ThresholdBounds(60.0, 90.0, 70.0, 1.0))
        self._register_threshold("rsi_oversold", ThresholdType.TECHNICAL_INDICATOR,
                                ThresholdBounds(10.0, 40.0, 30.0, 1.0))
        self._register_threshold("rsi_momentum_upper", ThresholdType.MOMENTUM,
                                ThresholdBounds(60.0, 80.0, 70.0, 1.0))
        self._register_threshold("rsi_momentum_lower", ThresholdType.MOMENTUM,
                                ThresholdBounds(30.0, 60.0, 50.0, 1.0))
        self._register_threshold("rsi_bearish_upper", ThresholdType.MOMENTUM,
                                ThresholdBounds(40.0, 60.0, 50.0, 1.0))
        self._register_threshold("rsi_bearish_lower", ThresholdType.MOMENTUM,
                                ThresholdBounds(20.0, 40.0, 30.0, 1.0))
        
        # Stochastic thresholds
        self._register_threshold("stoch_overbought", ThresholdType.TECHNICAL_INDICATOR,
                                ThresholdBounds(70.0, 95.0, 80.0, 1.0))
        self._register_threshold("stoch_oversold", ThresholdType.TECHNICAL_INDICATOR,
                                ThresholdBounds(5.0, 30.0, 20.0, 1.0))
        
        # Bollinger Band parameters
        self._register_threshold("bb_period", ThresholdType.TECHNICAL_INDICATOR,
                                ThresholdBounds(10.0, 50.0, 20.0, 1.0))
        self._register_threshold("bb_std_multiplier", ThresholdType.TECHNICAL_INDICATOR,
                                ThresholdBounds(1.0, 3.0, 2.0, 0.1))
        
        # MACD parameters
        self._register_threshold("macd_fast_period", ThresholdType.TECHNICAL_INDICATOR,
                                ThresholdBounds(8.0, 20.0, 12.0, 1.0))
        self._register_threshold("macd_slow_period", ThresholdType.TECHNICAL_INDICATOR,
                                ThresholdBounds(20.0, 40.0, 26.0, 1.0))
        self._register_threshold("macd_signal_period", ThresholdType.TECHNICAL_INDICATOR,
                                ThresholdBounds(5.0, 15.0, 9.0, 1.0))
        
        # Momentum strategy thresholds
        self._register_threshold("momentum_threshold_base", ThresholdType.MOMENTUM,
                                ThresholdBounds(0.5, 5.0, 2.0, 0.1))
        self._register_threshold("momentum_price_change_threshold", ThresholdType.MOMENTUM,
                                ThresholdBounds(-5.0, -1.0, -2.0, 0.1))
        
        # Volume confirmation thresholds
        self._register_threshold("volume_confirmation_ratio", ThresholdType.VOLUME,
                                ThresholdBounds(1.0, 2.5, 1.2, 0.05))
        
        # Mean reversion thresholds
        self._register_threshold("z_score_entry_threshold", ThresholdType.MEAN_REVERSION,
                                ThresholdBounds(1.0, 3.5, 2.0, 0.1))
        self._register_threshold("z_score_exit_threshold", ThresholdType.MEAN_REVERSION,
                                ThresholdBounds(0.1, 1.0, 0.5, 0.05))
        self._register_threshold("mean_reversion_confidence_base", ThresholdType.MEAN_REVERSION,
                                ThresholdBounds(2.0, 5.0, 3.0, 0.1))
        self._register_threshold("mean_reversion_confidence_offset", ThresholdType.MEAN_REVERSION,
                                ThresholdBounds(0.1, 0.5, 0.3, 0.02))
        
        # Pairs trading thresholds
        self._register_threshold("pairs_entry_threshold", ThresholdType.PAIRS_TRADING,
                                ThresholdBounds(1.0, 4.0, 2.0, 0.1))
        self._register_threshold("pairs_exit_threshold", ThresholdType.PAIRS_TRADING,
                                ThresholdBounds(0.1, 1.0, 0.5, 0.05))
        self._register_threshold("pairs_confidence_base", ThresholdType.PAIRS_TRADING,
                                ThresholdBounds(2.0, 5.0, 3.0, 0.1))
        self._register_threshold("pairs_confidence_offset", ThresholdType.PAIRS_TRADING,
                                ThresholdBounds(0.2, 0.6, 0.4, 0.02))
        
        # Risk management thresholds
        self._register_threshold("stop_loss_base_pct", ThresholdType.RISK_MANAGEMENT,
                                ThresholdBounds(0.01, 0.05, 0.02, 0.001))
        self._register_threshold("take_profit_base_pct", ThresholdType.RISK_MANAGEMENT,
                                ThresholdBounds(0.02, 0.08, 0.04, 0.001))
        self._register_threshold("position_size_base_pct", ThresholdType.RISK_MANAGEMENT,
                                ThresholdBounds(0.05, 0.15, 0.08, 0.005))
        self._register_threshold("confidence_strength_threshold", ThresholdType.RISK_MANAGEMENT,
                                ThresholdBounds(0.5, 0.9, 0.7, 0.02))
        
        self.logger.info(f"✅ Initialized {len(self.thresholds)} adaptive thresholds")
    
    def _register_threshold(self, name: str, threshold_type: ThresholdType, 
                          bounds: ThresholdBounds) -> None:
        """Register a new adaptive threshold"""
        threshold = AdaptiveThreshold(
            name=name,
            threshold_type=threshold_type,
            bounds=bounds
        )
        self.thresholds[name] = threshold
    
    def _setup_regime_multipliers(self) -> None:
        """Setup regime-specific multipliers for each threshold"""
        self.regime_multipliers = {
            # High volatility regime - more conservative thresholds
            "high_volatility": {
                "rsi_overbought": 0.95,  # Lower overbought (68 vs 70)
                "rsi_oversold": 1.05,    # Higher oversold (32 vs 30)
                "momentum_threshold_base": 1.5,  # Higher momentum threshold
                "z_score_entry_threshold": 1.2,  # Higher z-score threshold
                "volume_confirmation_ratio": 1.3,  # Higher volume requirement
                "stop_loss_base_pct": 1.4,       # Wider stops
                "position_size_base_pct": 0.7,   # Smaller positions
            },
            
            # Low volatility regime - more aggressive thresholds
            "stable": {
                "rsi_overbought": 1.02,  # Higher overbought (71 vs 70)
                "rsi_oversold": 0.98,    # Lower oversold (29 vs 30)
                "momentum_threshold_base": 0.8,  # Lower momentum threshold
                "z_score_entry_threshold": 0.9,  # Lower z-score threshold
                "volume_confirmation_ratio": 0.9,  # Lower volume requirement
                "stop_loss_base_pct": 0.8,       # Tighter stops
                "position_size_base_pct": 1.2,   # Larger positions
            },
            
            # Trending regime - momentum-favoring
            "trending": {
                "momentum_threshold_base": 0.9,  # Easier momentum triggers
                "rsi_momentum_upper": 0.95,      # Lower momentum zone
                "volume_confirmation_ratio": 0.95,  # Lower volume requirement
                "mean_reversion_confidence_base": 1.2,  # Higher MR threshold
                "stop_loss_base_pct": 1.1,       # Slightly wider stops
            },
            
            # Mean reverting regime - reversion-favoring
            "mean_reverting": {
                "z_score_entry_threshold": 0.85,    # Easier MR entry
                "momentum_threshold_base": 1.3,     # Harder momentum entry
                "mean_reversion_confidence_base": 0.9,  # Lower MR threshold
                "bb_std_multiplier": 0.9,           # Tighter Bollinger Bands
            },
            
            # Crisis/volatile regime - very conservative
            "crisis": {
                "rsi_overbought": 0.9,   # Much lower overbought (63 vs 70)
                "rsi_oversold": 1.1,     # Much higher oversold (33 vs 30)
                "momentum_threshold_base": 2.0,  # Much higher momentum threshold
                "z_score_entry_threshold": 1.5,  # Much higher z-score threshold
                "volume_confirmation_ratio": 1.5,  # Much higher volume requirement
                "stop_loss_base_pct": 1.8,       # Much wider stops
                "position_size_base_pct": 0.5,   # Much smaller positions
                "confidence_strength_threshold": 1.1,  # Higher confidence required
            }
        }
        
        # Default multiplier of 1.0 for all thresholds not specifically listed
        for regime_name, multipliers in self.regime_multipliers.items():
            for threshold_name in self.thresholds.keys():
                if threshold_name not in multipliers:
                    multipliers[threshold_name] = 1.0
    
    def get_threshold_value(self, threshold_name: str, 
                          regime_name: Optional[str] = None) -> float:
        """
        Get current threshold value with optional regime adjustment.
        
        Args:
            threshold_name: Name of threshold to retrieve
            regime_name: Current market regime for adjustment
            
        Returns:
            Adjusted threshold value
        """
        if threshold_name not in self.thresholds:
            self.logger.warning(f"Unknown threshold: {threshold_name}")
            return 0.0
        
        threshold = self.thresholds[threshold_name]
        
        # Apply regime multiplier if regime is provided
        regime_multiplier = 1.0
        if regime_name and regime_name in self.regime_multipliers:
            regime_multiplier = self.regime_multipliers[regime_name].get(threshold_name, 1.0)
        
        return threshold.get_value_with_regime_adjustment(regime_multiplier)
    
    def get_adaptive_rsi_thresholds(self, regime_name: Optional[str] = None) -> Dict[str, float]:
        """Get adaptive RSI thresholds for different use cases"""
        return {
            'overbought': self.get_threshold_value('rsi_overbought', regime_name),
            'oversold': self.get_threshold_value('rsi_oversold', regime_name),
            'momentum_upper': self.get_threshold_value('rsi_momentum_upper', regime_name),
            'momentum_lower': self.get_threshold_value('rsi_momentum_lower', regime_name),
            'bearish_upper': self.get_threshold_value('rsi_bearish_upper', regime_name),
            'bearish_lower': self.get_threshold_value('rsi_bearish_lower', regime_name),
        }
    
    def get_adaptive_momentum_thresholds(self, regime_name: Optional[str] = None) -> Dict[str, float]:
        """Get adaptive momentum strategy thresholds"""
        return {
            'momentum_threshold': self.get_threshold_value('momentum_threshold_base', regime_name),
            'price_change_threshold': self.get_threshold_value('momentum_price_change_threshold', regime_name),
            'volume_ratio': self.get_threshold_value('volume_confirmation_ratio', regime_name),
        }
    
    def get_adaptive_mean_reversion_thresholds(self, regime_name: Optional[str] = None) -> Dict[str, float]:
        """Get adaptive mean reversion strategy thresholds"""
        return {
            'z_score_entry': self.get_threshold_value('z_score_entry_threshold', regime_name),
            'z_score_exit': self.get_threshold_value('z_score_exit_threshold', regime_name),
            'confidence_base': self.get_threshold_value('mean_reversion_confidence_base', regime_name),
            'confidence_offset': self.get_threshold_value('mean_reversion_confidence_offset', regime_name),
            'bb_period': int(self.get_threshold_value('bb_period', regime_name)),
            'bb_std_multiplier': self.get_threshold_value('bb_std_multiplier', regime_name),
        }
    
    def get_adaptive_pairs_trading_thresholds(self, regime_name: Optional[str] = None) -> Dict[str, float]:
        """Get adaptive pairs trading strategy thresholds"""
        return {
            'entry_threshold': self.get_threshold_value('pairs_entry_threshold', regime_name),
            'exit_threshold': self.get_threshold_value('pairs_exit_threshold', regime_name),
            'confidence_base': self.get_threshold_value('pairs_confidence_base', regime_name),
            'confidence_offset': self.get_threshold_value('pairs_confidence_offset', regime_name),
        }
    
    def get_adaptive_risk_thresholds(self, regime_name: Optional[str] = None) -> Dict[str, float]:
        """Get adaptive risk management thresholds"""
        return {
            'stop_loss_pct': self.get_threshold_value('stop_loss_base_pct', regime_name),
            'take_profit_pct': self.get_threshold_value('take_profit_base_pct', regime_name),
            'position_size_pct': self.get_threshold_value('position_size_base_pct', regime_name),
            'confidence_threshold': self.get_threshold_value('confidence_strength_threshold', regime_name),
        }
    
    def get_adaptive_technical_indicator_params(self, regime_name: Optional[str] = None) -> Dict[str, Union[int, float]]:
        """Get adaptive technical indicator parameters"""
        return {
            'rsi_period': 14,  # Keep RSI period fixed for now
            'bb_period': int(self.get_threshold_value('bb_period', regime_name)),
            'bb_std_multiplier': self.get_threshold_value('bb_std_multiplier', regime_name),
            'macd_fast': int(self.get_threshold_value('macd_fast_period', regime_name)),
            'macd_slow': int(self.get_threshold_value('macd_slow_period', regime_name)),
            'macd_signal': int(self.get_threshold_value('macd_signal_period', regime_name)),
        }
    
    async def update_thresholds_based_on_performance(self,
                                                   performance_metrics: Dict[str, float],
                                                   market_conditions: Dict[str, float],
                                                   recent_signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Update thresholds based on recent performance and market conditions.
        
        Args:
            performance_metrics: Recent strategy performance metrics
            market_conditions: Current market condition metrics
            recent_signals: Recent trading signals for analysis
            
        Returns:
            Dictionary with update results and changes made
        """
        try:
            self.current_market_conditions = market_conditions.copy()
            update_results = {
                'thresholds_updated': [],
                'performance_score': 0.0,
                'adaptation_reason': '',
                'changes_made': {}
            }
            
            # Calculate overall performance score
            performance_score = self._calculate_performance_score(performance_metrics)
            update_results['performance_score'] = performance_score
            
            # Determine if adaptation is needed
            if not self._should_adapt_thresholds(performance_score, market_conditions):
                update_results['adaptation_reason'] = 'No adaptation needed - performance satisfactory'
                return update_results
            
            # Analyze recent signals for threshold effectiveness
            signal_analysis = self._analyze_signal_effectiveness(recent_signals, performance_metrics)
            
            # Update thresholds based on analysis
            changes_made = {}
            
            # Update technical indicator thresholds
            technical_changes = await self._update_technical_indicator_thresholds(
                performance_score, signal_analysis, market_conditions
            )
            changes_made.update(technical_changes)
            
            # Update strategy-specific thresholds
            strategy_changes = await self._update_strategy_thresholds(
                performance_score, signal_analysis, market_conditions
            )
            changes_made.update(strategy_changes)
            
            # Update risk management thresholds
            risk_changes = await self._update_risk_thresholds(
                performance_score, market_conditions
            )
            changes_made.update(risk_changes)
            
            update_results['changes_made'] = changes_made
            update_results['thresholds_updated'] = list(changes_made.keys())
            update_results['adaptation_reason'] = f"Performance-based adaptation (score: {performance_score:.2f})"
            
            # Log updates
            if changes_made:
                self.logger.info(f"🔄 Updated {len(changes_made)} adaptive thresholds based on performance")
                for threshold_name, change_info in changes_made.items():
                    self.logger.info(f"   📊 {threshold_name}: {change_info['old_value']:.3f} → {change_info['new_value']:.3f}")
            
            return update_results
            
        except Exception as e:
            self.logger.error(f"❌ Threshold update failed: {e}")
            return {'error': str(e)}
    
    def _calculate_performance_score(self, performance_metrics: Dict[str, float]) -> float:
        """Calculate overall performance score from metrics"""
        weights = {
            'sharpe_ratio': 0.3,
            'win_rate': 0.25,
            'profit_factor': 0.2,
            'max_drawdown': -0.15,  # Negative weight (lower is better)
            'total_return': 0.1
        }
        
        # Normalize metrics to 0-1 scale
        normalized_metrics = {}
        for metric, value in performance_metrics.items():
            if metric == 'sharpe_ratio':
                normalized_metrics[metric] = max(0, min(1, (value + 1) / 3))  # -1 to 2 range
            elif metric == 'win_rate':
                normalized_metrics[metric] = max(0, min(1, value))  # Already 0-1
            elif metric == 'profit_factor':
                normalized_metrics[metric] = max(0, min(1, value / 2))  # 0-2 range
            elif metric == 'max_drawdown':
                normalized_metrics[metric] = max(0, min(1, 1 - abs(value)))  # Invert (lower dd = higher score)
            elif metric == 'total_return':
                normalized_metrics[metric] = max(0, min(1, (value + 0.2) / 0.4))  # -20% to 20% range
        
        # Calculate weighted score
        score = 0.0
        total_weight = 0.0
        for metric, weight in weights.items():
            if metric in normalized_metrics:
                score += normalized_metrics[metric] * weight
                total_weight += abs(weight)
        
        return score / total_weight if total_weight > 0 else 0.5
    
    def _should_adapt_thresholds(self, performance_score: float, 
                               market_conditions: Dict[str, float]) -> bool:
        """Determine if threshold adaptation is needed"""
        # Adapt if performance is poor or market conditions have changed significantly
        if performance_score < 0.6:  # Poor performance
            return True
        
        # Check for significant market condition changes
        if hasattr(self, '_last_market_conditions'):
            volatility_change = abs(
                market_conditions.get('volatility', 0.2) - 
                self._last_market_conditions.get('volatility', 0.2)
            )
            if volatility_change > 0.05:  # 5% volatility change
                return True
        
        self._last_market_conditions = market_conditions.copy()
        return False
    
    def _analyze_signal_effectiveness(self, recent_signals: List[Dict[str, Any]], 
                                   performance_metrics: Dict[str, float]) -> Dict[str, float]:
        """Analyze effectiveness of recent signals"""
        if not recent_signals:
            return {'signal_accuracy': 0.5, 'false_positive_rate': 0.5}
        
        # Simple analysis - in practice this would be more sophisticated
        total_signals = len(recent_signals)
        profitable_signals = sum(1 for signal in recent_signals 
                               if signal.get('outcome', 0) > 0)
        
        signal_accuracy = profitable_signals / total_signals if total_signals > 0 else 0.5
        false_positive_rate = 1 - signal_accuracy
        
        return {
            'signal_accuracy': signal_accuracy,
            'false_positive_rate': false_positive_rate,
            'signal_frequency': len([s for s in recent_signals if s.get('timestamp', 0) > 0])
        }
    
    async def _update_technical_indicator_thresholds(self,
                                                   performance_score: float,
                                                   signal_analysis: Dict[str, float],
                                                   market_conditions: Dict[str, float]) -> Dict[str, Dict[str, float]]:
        """Update technical indicator thresholds"""
        changes = {}
        
        # RSI threshold adjustments
        if signal_analysis['false_positive_rate'] > 0.6:  # Too many false signals
            # Make RSI thresholds more restrictive
            rsi_ob_threshold = self.thresholds['rsi_overbought']
            new_ob_value = min(rsi_ob_threshold.current_value - 2.0, rsi_ob_threshold.bounds.max_value)
            if rsi_ob_threshold.update_value(new_ob_value, performance_score, market_conditions):
                changes['rsi_overbought'] = {
                    'old_value': rsi_ob_threshold.current_value + 2.0,
                    'new_value': new_ob_value,
                    'reason': 'Reduce false positives'
                }
            
            rsi_os_threshold = self.thresholds['rsi_oversold']
            new_os_value = max(rsi_os_threshold.current_value + 2.0, rsi_os_threshold.bounds.min_value)
            if rsi_os_threshold.update_value(new_os_value, performance_score, market_conditions):
                changes['rsi_oversold'] = {
                    'old_value': rsi_os_threshold.current_value - 2.0,
                    'new_value': new_os_value,
                    'reason': 'Reduce false positives'
                }
        
        elif signal_analysis['signal_accuracy'] > 0.8 and signal_analysis.get('signal_frequency', 0) < 5:
            # High accuracy but low frequency - relax thresholds
            rsi_ob_threshold = self.thresholds['rsi_overbought']
            new_ob_value = max(rsi_ob_threshold.current_value + 1.0, rsi_ob_threshold.bounds.min_value)
            if rsi_ob_threshold.update_value(new_ob_value, performance_score, market_conditions):
                changes['rsi_overbought'] = {
                    'old_value': rsi_ob_threshold.current_value - 1.0,
                    'new_value': new_ob_value,
                    'reason': 'Increase signal frequency'
                }
        
        # Bollinger Band period adjustment based on volatility
        volatility = market_conditions.get('volatility', 0.2)
        bb_period_threshold = self.thresholds['bb_period']
        
        if volatility > 0.3:  # High volatility - use shorter period
            new_bb_period = max(bb_period_threshold.current_value - 2, bb_period_threshold.bounds.min_value)
        elif volatility < 0.1:  # Low volatility - use longer period
            new_bb_period = min(bb_period_threshold.current_value + 3, bb_period_threshold.bounds.max_value)
        else:
            new_bb_period = bb_period_threshold.current_value
        
        if new_bb_period != bb_period_threshold.current_value:
            if bb_period_threshold.update_value(new_bb_period, performance_score, market_conditions):
                changes['bb_period'] = {
                    'old_value': bb_period_threshold.current_value,
                    'new_value': new_bb_period,
                    'reason': f'Volatility adjustment ({volatility:.2f})'
                }
        
        return changes
    
    async def _update_strategy_thresholds(self,
                                        performance_score: float,
                                        signal_analysis: Dict[str, float],
                                        market_conditions: Dict[str, float]) -> Dict[str, Dict[str, float]]:
        """Update strategy-specific thresholds"""
        changes = {}
        
        # Momentum threshold adjustments
        momentum_threshold = self.thresholds['momentum_threshold_base']
        if performance_score < 0.5:  # Poor performance - be more selective
            new_momentum = min(momentum_threshold.current_value + 0.3, momentum_threshold.bounds.max_value)
            if momentum_threshold.update_value(new_momentum, performance_score, market_conditions):
                changes['momentum_threshold_base'] = {
                    'old_value': momentum_threshold.current_value - 0.3,
                    'new_value': new_momentum,
                    'reason': 'Performance improvement'
                }
        
        # Z-score threshold adjustments for mean reversion
        z_threshold = self.thresholds['z_score_entry_threshold']
        if signal_analysis['false_positive_rate'] > 0.7:  # Too many false mean reversion signals
            new_z = min(z_threshold.current_value + 0.2, z_threshold.bounds.max_value)
            if z_threshold.update_value(new_z, performance_score, market_conditions):
                changes['z_score_entry_threshold'] = {
                    'old_value': z_threshold.current_value - 0.2,
                    'new_value': new_z,
                    'reason': 'Reduce false mean reversion signals'
                }
        
        # Volume confirmation adjustments
        volume_threshold = self.thresholds['volume_confirmation_ratio']
        if signal_analysis['signal_accuracy'] < 0.4:  # Poor signal quality
            new_volume = min(volume_threshold.current_value + 0.1, volume_threshold.bounds.max_value)
            if volume_threshold.update_value(new_volume, performance_score, market_conditions):
                changes['volume_confirmation_ratio'] = {
                    'old_value': volume_threshold.current_value - 0.1,
                    'new_value': new_volume,
                    'reason': 'Improve signal quality'
                }
        
        return changes
    
    async def _update_risk_thresholds(self,
                                    performance_score: float,
                                    market_conditions: Dict[str, float]) -> Dict[str, Dict[str, float]]:
        """Update risk management thresholds"""
        changes = {}
        
        # Stop loss adjustments based on market volatility
        volatility = market_conditions.get('volatility', 0.2)
        stop_loss_threshold = self.thresholds['stop_loss_base_pct']
        
        # Adjust stop loss based on volatility
        if volatility > 0.3:  # High volatility - wider stops
            new_stop_loss = min(stop_loss_threshold.current_value + 0.005, stop_loss_threshold.bounds.max_value)
        elif volatility < 0.1:  # Low volatility - tighter stops
            new_stop_loss = max(stop_loss_threshold.current_value - 0.003, stop_loss_threshold.bounds.min_value)
        else:
            new_stop_loss = stop_loss_threshold.current_value
        
        if new_stop_loss != stop_loss_threshold.current_value:
            if stop_loss_threshold.update_value(new_stop_loss, performance_score, market_conditions):
                changes['stop_loss_base_pct'] = {
                    'old_value': stop_loss_threshold.current_value,
                    'new_value': new_stop_loss,
                    'reason': f'Volatility adjustment ({volatility:.2f})'
                }
        
        # Position size adjustments based on performance
        position_size_threshold = self.thresholds['position_size_base_pct']
        if performance_score < 0.4:  # Poor performance - reduce position sizes
            new_position_size = max(position_size_threshold.current_value - 0.01, position_size_threshold.bounds.min_value)
            if position_size_threshold.update_value(new_position_size, performance_score, market_conditions):
                changes['position_size_base_pct'] = {
                    'old_value': position_size_threshold.current_value + 0.01,
                    'new_value': new_position_size,
                    'reason': 'Performance-based risk reduction'
                }
        elif performance_score > 0.8:  # Excellent performance - can increase slightly
            new_position_size = min(position_size_threshold.current_value + 0.005, position_size_threshold.bounds.max_value)
            if position_size_threshold.update_value(new_position_size, performance_score, market_conditions):
                changes['position_size_base_pct'] = {
                    'old_value': position_size_threshold.current_value - 0.005,
                    'new_value': new_position_size,
                    'reason': 'Performance-based position increase'
                }
        
        return changes
    
    def get_all_current_thresholds(self, regime_name: Optional[str] = None) -> Dict[str, float]:
        """Get all current threshold values with optional regime adjustment"""
        return {
            name: self.get_threshold_value(name, regime_name)
            for name in self.thresholds.keys()
        }
    
    def export_threshold_configuration(self) -> Dict[str, Any]:
        """Export current threshold configuration for backup/analysis"""
        return {
            'strategy_id': self.strategy_id,
            'timestamp': datetime.now().isoformat(),
            'thresholds': {
                name: {
                    'current_value': threshold.current_value,
                    'bounds': {
                        'min': threshold.bounds.min_value,
                        'max': threshold.bounds.max_value,
                        'default': threshold.bounds.default_value
                    },
                    'type': threshold.threshold_type.value,
                    'update_count': threshold.update_count,
                    'last_updated': threshold.last_updated.isoformat() if threshold.last_updated else None
                }
                for name, threshold in self.thresholds.items()
            },
            'regime_multipliers': self.regime_multipliers
        }
    
    def import_threshold_configuration(self, config: Dict[str, Any]) -> bool:
        """Import threshold configuration from backup"""
        try:
            for name, threshold_config in config.get('thresholds', {}).items():
                if name in self.thresholds:
                    self.thresholds[name].current_value = threshold_config['current_value']
                    self.thresholds[name].update_count = threshold_config.get('update_count', 0)
                    if threshold_config.get('last_updated'):
                        self.thresholds[name].last_updated = datetime.fromisoformat(
                            threshold_config['last_updated']
                        )
            
            if 'regime_multipliers' in config:
                self.regime_multipliers = config['regime_multipliers']
            
            self.logger.info("✅ Threshold configuration imported successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to import threshold configuration: {e}")
            return False
    
    def backup_configuration(self, backup_path: Optional[str] = None) -> str:
        """
        Backup current threshold configuration to file.
        
        Args:
            backup_path: Optional path for backup file
            
        Returns:
            Path to created backup file
        """
        import json
        import os
        
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"adaptive_thresholds_backup_{self.strategy_id}_{timestamp}.json"
        
        config = self.export_threshold_configuration()
        
        try:
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            with open(backup_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            self.logger.info(f"✅ Threshold configuration backed up to: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"❌ Failed to backup configuration: {e}")
            raise
    
    def restore_configuration(self, backup_path: str) -> bool:
        """
        Restore threshold configuration from backup file.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True if successful, False otherwise
        """
        import json
        
        try:
            with open(backup_path, 'r') as f:
                config = json.load(f)
            
            return self.import_threshold_configuration(config)
            
        except Exception as e:
            self.logger.error(f"❌ Failed to restore configuration from {backup_path}: {e}")
            return False
    
    def validate_thresholds(self) -> Dict[str, List[str]]:
        """
        Validate all thresholds for consistency and bounds.
        
        Returns:
            Dictionary with validation results
        """
        validation_results = {
            'valid': [],
            'warnings': [],
            'errors': []
        }
        
        for name, threshold in self.thresholds.items():
            # Check bounds
            if not (threshold.bounds.min_value <= threshold.current_value <= threshold.bounds.max_value):
                validation_results['errors'].append(
                    f"{name}: Value {threshold.current_value:.3f} outside bounds "
                    f"[{threshold.bounds.min_value:.3f}, {threshold.bounds.max_value:.3f}]"
                )
            else:
                validation_results['valid'].append(name)
            
            # Check for extreme values
            value_range = threshold.bounds.max_value - threshold.bounds.min_value
            distance_from_default = abs(threshold.current_value - threshold.bounds.default_value)
            
            if distance_from_default > value_range * 0.8:  # More than 80% from default
                validation_results['warnings'].append(
                    f"{name}: Value {threshold.current_value:.3f} significantly different from "
                    f"default {threshold.bounds.default_value:.3f}"
                )
        
        return validation_results
    
    def get_threshold_statistics(self) -> Dict[str, Any]:
        """Get statistics about threshold usage and updates"""
        stats = {
            'total_thresholds': len(self.thresholds),
            'categories': {},
            'update_statistics': {
                'total_updates': 0,
                'recently_updated': 0,
                'never_updated': 0
            },
            'value_distribution': {},
            'regime_coverage': len(self.regime_multipliers)
        }
        
        # Category statistics
        for threshold in self.thresholds.values():
            category = threshold.threshold_type.value
            if category not in stats['categories']:
                stats['categories'][category] = 0
            stats['categories'][category] += 1
        
        # Update statistics
        now = datetime.now()
        recent_threshold = timedelta(hours=24)
        
        for threshold in self.thresholds.values():
            stats['update_statistics']['total_updates'] += threshold.update_count
            
            if threshold.last_updated is None:
                stats['update_statistics']['never_updated'] += 1
            elif now - threshold.last_updated <= recent_threshold:
                stats['update_statistics']['recently_updated'] += 1
        
        # Value distribution (how far from defaults)
        for name, threshold in self.thresholds.items():
            deviation = abs(threshold.current_value - threshold.bounds.default_value)
            range_size = threshold.bounds.max_value - threshold.bounds.min_value
            normalized_deviation = deviation / range_size if range_size > 0 else 0
            
            if normalized_deviation < 0.1:
                category = 'near_default'
            elif normalized_deviation < 0.3:
                category = 'moderately_adjusted'
            else:
                category = 'significantly_adjusted'
            
            if category not in stats['value_distribution']:
                stats['value_distribution'][category] = 0
            stats['value_distribution'][category] += 1
        
        return stats
