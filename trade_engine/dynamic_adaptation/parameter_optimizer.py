"""
Real-time parameter optimization for trading strategies.
"""

import numpy as np
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import logging
import asyncio

from .adaptation_config import AdaptationConfig, AdaptationMode
from .adaptation_metrics import AdaptationMetrics, PerformanceSnapshot
from .parameter_validator import ParameterValidator, ValidationResult
from .adaptation_rollback import AdaptationRollbackManager, AdaptationSnapshot
from ..templates.base_template import template_registry


@dataclass
class ParameterOptimizationResult:
    """Result of parameter optimization attempt."""
    
    success: bool
    parameters_changed: Dict[str, Any]
    validation_result: ValidationResult
    optimization_reason: str
    confidence_score: float
    expected_improvement: float
    snapshot_id: Optional[str] = None
    error_message: Optional[str] = None
    
    def __str__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        return (f"ParameterOptimization({status}, changed={len(self.parameters_changed)} params, "
                f"confidence={self.confidence_score:.2f})")


class RealTimeParameterOptimizer:
    """
    Real-time parameter optimization based on actual performance metrics.
    
    This class implements intelligent parameter adaptation that:
    1. Monitors actual trading performance
    2. Detects when adaptation is needed
    3. Calculates optimal parameter adjustments
    4. Validates changes against template bounds
    5. Manages rollback if performance degrades
    """
    
    def __init__(self, 
                 strategy_id: str, 
                 template_id: str,
                 adaptation_config: Optional[AdaptationConfig] = None):
        """
        Initialize parameter optimizer.
        
        Args:
            strategy_id: Unique identifier for strategy instance
            template_id: Template identifier for parameter bounds
            adaptation_config: Configuration for adaptation behavior
        """
        self.strategy_id = strategy_id
        self.template_id = template_id
        self.config = adaptation_config or AdaptationConfig()
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.metrics = AdaptationMetrics(strategy_id)
        self.validator = ParameterValidator(template_id)
        self.rollback_manager = AdaptationRollbackManager(strategy_id)
        
        # State tracking
        self.current_parameters: Dict[str, Any] = {}
        self.last_adaptation_time: Optional[datetime] = None
        self.adaptation_count_today = 0
        self.optimization_history: List[ParameterOptimizationResult] = []
        
        # Performance tracking
        self.baseline_performance: Optional[PerformanceSnapshot] = None
        self.last_performance_snapshot: Optional[PerformanceSnapshot] = None
        
    async def optimize_parameters(self,
                                current_parameters: Dict[str, Any],
                                market_conditions: Dict[str, float],
                                force_optimization: bool = False) -> ParameterOptimizationResult:
        """
        Main optimization method - evaluates if adaptation is needed and executes it.
        
        Args:
            current_parameters: Current strategy parameters
            market_conditions: Current market condition metrics
            force_optimization: Force optimization regardless of triggers
            
        Returns:
            ParameterOptimizationResult with changes and metadata
        """
        try:
            self.current_parameters = current_parameters.copy()
            
            # Update performance metrics
            current_performance = self.metrics.calculate_performance_snapshot()
            self.last_performance_snapshot = current_performance
            
            # Check if adaptation is enabled and allowed
            if not self._should_attempt_optimization(force_optimization):
                return ParameterOptimizationResult(
                    success=True,
                    parameters_changed={},
                    validation_result=ValidationResult(valid=True),
                    optimization_reason="No optimization needed",
                    confidence_score=0.0,
                    expected_improvement=0.0
                )
            
            # Calculate adaptation signal strength
            adaptation_signal = self.metrics.get_adaptation_signal_strength()
            
            # Check adaptation triggers
            trigger_result = self._evaluate_adaptation_triggers(current_performance, market_conditions)
            
            if not trigger_result['should_adapt'] and not force_optimization:
                return ParameterOptimizationResult(
                    success=True,
                    parameters_changed={},
                    validation_result=ValidationResult(valid=True),
                    optimization_reason=trigger_result['reason'],
                    confidence_score=adaptation_signal,
                    expected_improvement=0.0
                )
            
            # Calculate optimal parameter adjustments
            optimization_result = await self._calculate_parameter_adjustments(
                current_parameters,
                current_performance,
                market_conditions,
                adaptation_signal
            )
            
            if not optimization_result.success:
                return optimization_result
            
            # Create snapshot before applying changes
            snapshot_id = None
            if optimization_result.parameters_changed:
                snapshot_id = self.rollback_manager.create_adaptation_snapshot(
                    parameters_before=current_parameters,
                    parameters_after={**current_parameters, **optimization_result.parameters_changed},
                    performance_before=current_performance,
                    market_conditions=market_conditions,
                    adaptation_reason=optimization_result.optimization_reason,
                    adaptation_confidence=optimization_result.confidence_score,
                    expected_improvement=optimization_result.expected_improvement
                )
                optimization_result.snapshot_id = snapshot_id
            
            # Update tracking
            self.last_adaptation_time = datetime.now()
            self.adaptation_count_today += 1
            self.optimization_history.append(optimization_result)
            
            self.logger.info(f"Parameter optimization completed: {optimization_result}")
            
            return optimization_result
            
        except Exception as e:
            error_msg = f"Parameter optimization failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return ParameterOptimizationResult(
                success=False,
                parameters_changed={},
                validation_result=ValidationResult(valid=False, errors=[error_msg]),
                optimization_reason="Optimization error",
                confidence_score=0.0,
                expected_improvement=0.0,
                error_message=error_msg
            )
    
    async def monitor_adaptation_performance(self, snapshot_id: str) -> bool:
        """
        Monitor performance after adaptation and rollback if needed.
        
        Args:
            snapshot_id: ID of adaptation snapshot to monitor
            
        Returns:
            True if adaptation is performing well, False if rolled back
        """
        try:
            current_performance = self.metrics.calculate_performance_snapshot()
            current_market_conditions = {}  # Would get from market data feed
            
            # Evaluate rollback decision
            rollback_decision = self.rollback_manager.evaluate_rollback_decision(
                snapshot_id,
                current_performance,
                current_market_conditions
            )
            
            if rollback_decision.should_rollback:
                self.logger.warning(f"Initiating rollback for {snapshot_id}: {rollback_decision.reason}")
                
                # Execute rollback (would need parameter setter callback)
                # rollback_result = await self.rollback_manager.execute_rollback(
                #     snapshot_id, parameter_setter_callback
                # )
                
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error monitoring adaptation performance: {e}")
            return False
    
    def add_trade_data(self, trade_data: Dict[str, Any]) -> None:
        """Add trade data for performance tracking."""
        self.metrics.add_trade(trade_data)
    
    def add_market_data(self, market_return: float, volatility: float) -> None:
        """Add market data for performance comparison."""
        self.metrics.add_market_data(market_return, volatility)
    
    def get_optimization_history(self) -> List[ParameterOptimizationResult]:
        """Get history of parameter optimizations."""
        return self.optimization_history.copy()
    
    def _should_attempt_optimization(self, force: bool = False) -> bool:
        """Check if optimization should be attempted."""
        if force:
            return True
        
        if not self.config.should_adapt():
            return False
        
        # Check daily limit
        if self.adaptation_count_today >= self.config.max_adaptations_per_day:
            return False
        
        # Check minimum time between adaptations
        if self.last_adaptation_time:
            time_since_last = datetime.now() - self.last_adaptation_time
            min_interval = timedelta(hours=self.config.triggers.min_hours_between_adaptations)
            if time_since_last < min_interval:
                return False
        
        # Check sufficient data
        if not self.metrics.trade_history or len(self.metrics.trade_history) < self.config.triggers.min_trades_for_adaptation:
            return False
        
        return True
    
    def _evaluate_adaptation_triggers(self,
                                    performance: PerformanceSnapshot,
                                    market_conditions: Dict[str, float]) -> Dict[str, Any]:
        """Evaluate if adaptation triggers are met."""
        triggers = self.config.triggers
        reasons = []
        
        # Performance-based triggers
        performance_triggers = {
            'low_sharpe': performance.sharpe_ratio < triggers.min_sharpe_ratio,
            'high_drawdown': performance.max_drawdown > triggers.max_drawdown_threshold,
            'low_win_rate': performance.win_rate < triggers.min_win_rate,
            'low_profit_factor': performance.profit_factor < triggers.min_profit_factor
        }
        
        # Market condition triggers (if baseline exists)
        market_triggers = {}
        if hasattr(self, 'baseline_market_conditions'):
            for key, current_value in market_conditions.items():
                if key in self.baseline_market_conditions:
                    baseline_value = self.baseline_market_conditions[key]
                    if baseline_value != 0:
                        change = abs(current_value - baseline_value) / abs(baseline_value)
                        market_triggers[f'{key}_change'] = change > triggers.volatility_change_threshold
        
        # Evaluate triggers
        triggered_performance = [name for name, triggered in performance_triggers.items() if triggered]
        triggered_market = [name for name, triggered in market_triggers.items() if triggered]
        
        should_adapt = len(triggered_performance) >= 2 or len(triggered_market) >= 1
        
        if triggered_performance:
            reasons.extend([f"performance: {', '.join(triggered_performance)}"])
        if triggered_market:
            reasons.extend([f"market: {', '.join(triggered_market)}"])
        
        return {
            'should_adapt': should_adapt,
            'reason': '; '.join(reasons) if reasons else 'all triggers satisfied',
            'performance_triggers': triggered_performance,
            'market_triggers': triggered_market
        }
    
    async def _calculate_parameter_adjustments(self,
                                             current_parameters: Dict[str, Any],
                                             performance: PerformanceSnapshot,
                                             market_conditions: Dict[str, float],
                                             signal_strength: float) -> ParameterOptimizationResult:
        """Calculate optimal parameter adjustments."""
        
        # Get template bounds for safety
        template = template_registry.get_template(self.template_id)
        if not template:
            return ParameterOptimizationResult(
                success=False,
                parameters_changed={},
                validation_result=ValidationResult(valid=False, errors=["Template not found"]),
                optimization_reason="Template error",
                confidence_score=0.0,
                expected_improvement=0.0,
                error_message="Template not found"
            )
        
        proposed_changes = {}
        optimization_reasons = []
        
        # Adaptive step size based on signal strength and configuration
        step_size = self.config.get_adaptation_step_size() * signal_strength
        max_change = self.config.get_max_parameter_change()
        
        # Parameter-specific optimization logic
        proposed_changes.update(self._optimize_momentum_parameters(
            current_parameters, performance, step_size, max_change
        ))
        
        proposed_changes.update(self._optimize_risk_parameters(
            current_parameters, performance, step_size, max_change
        ))
        
        proposed_changes.update(self._optimize_position_sizing(
            current_parameters, performance, market_conditions, step_size, max_change
        ))
        
        # Validate all proposed changes
        validation_result = self.validator.validate_parameter_set(
            proposed_changes, current_parameters
        )
        
        # Also validate adaptation magnitude
        magnitude_validation = self.validator.validate_adaptation_magnitude(
            proposed_changes, current_parameters, max_change
        )
        
        # Combine validation results
        if not magnitude_validation.valid:
            validation_result.errors.extend(magnitude_validation.errors)
            validation_result.warnings.extend(magnitude_validation.warnings)
            validation_result.valid = False
        
        # Calculate expected improvement
        expected_improvement = self._estimate_performance_improvement(
            proposed_changes, performance, signal_strength
        )
        
        # Calculate confidence score
        confidence_score = self._calculate_optimization_confidence(
            proposed_changes, validation_result, signal_strength, expected_improvement
        )
        
        return ParameterOptimizationResult(
            success=validation_result.valid and bool(proposed_changes),
            parameters_changed=proposed_changes if validation_result.valid else {},
            validation_result=validation_result,
            optimization_reason=f"Adaptive optimization: {', '.join(optimization_reasons) if optimization_reasons else 'performance improvement'}",
            confidence_score=confidence_score,
            expected_improvement=expected_improvement
        )
    
    def _optimize_momentum_parameters(self,
                                    current_params: Dict[str, Any],
                                    performance: PerformanceSnapshot,
                                    step_size: float,
                                    max_change: float) -> Dict[str, Any]:
        """Optimize momentum-related parameters."""
        changes = {}
        
        # Adjust momentum threshold based on win rate
        if 'momentum_threshold' in current_params:
            current_threshold = current_params['momentum_threshold']
            
            if performance.win_rate < 0.4:  # Low win rate - be more selective
                new_threshold = current_threshold * (1 + step_size)
                changes['momentum_threshold'] = min(
                    current_threshold * (1 + max_change),
                    new_threshold
                )
            elif performance.win_rate > 0.7:  # High win rate - be less selective  
                new_threshold = current_threshold * (1 - step_size)
                changes['momentum_threshold'] = max(
                    current_threshold * (1 - max_change),
                    new_threshold
                )
        
        # Adjust confidence threshold based on Sharpe ratio
        if 'confidence_threshold' in current_params and performance.sharpe_ratio < 1.0:
            current_confidence = current_params['confidence_threshold']
            # Increase confidence threshold when Sharpe is low
            new_confidence = current_confidence * (1 + step_size * 0.5)
            changes['confidence_threshold'] = min(
                current_confidence * (1 + max_change),
                new_confidence
            )
        
        return changes
    
    def _optimize_risk_parameters(self,
                                current_params: Dict[str, Any],
                                performance: PerformanceSnapshot,
                                step_size: float,
                                max_change: float) -> Dict[str, Any]:
        """Optimize risk management parameters."""
        changes = {}
        
        # Adjust stop loss based on max drawdown
        if 'stop_loss_pct' in current_params and performance.max_drawdown > 0.10:
            current_stop = current_params['stop_loss_pct']
            # Tighten stop loss if experiencing high drawdown
            new_stop = current_stop * (1 - step_size * 0.5)
            changes['stop_loss_pct'] = max(
                current_stop * (1 - max_change),
                new_stop
            )
        
        # Adjust take profit based on profit factor
        if 'take_profit_pct' in current_params:
            current_take_profit = current_params['take_profit_pct']
            
            if performance.profit_factor < 1.2:  # Low profit factor
                # Reduce take profit target for more frequent wins
                new_take_profit = current_take_profit * (1 - step_size * 0.3)
                changes['take_profit_pct'] = max(
                    current_take_profit * (1 - max_change),
                    new_take_profit
                )
        
        return changes
    
    def _optimize_position_sizing(self,
                                current_params: Dict[str, Any],
                                performance: PerformanceSnapshot,
                                market_conditions: Dict[str, float],
                                step_size: float,
                                max_change: float) -> Dict[str, Any]:
        """Optimize position sizing parameters."""
        changes = {}
        
        # Adjust position size based on volatility and performance
        if 'position_size' in current_params:
            current_size = current_params['position_size']
            
            # Reduce size if high volatility or poor performance
            volatility_factor = market_conditions.get('volatility', 0.2)
            performance_factor = min(performance.sharpe_ratio / 2.0, 1.0)  # Cap at 1.0
            
            if volatility_factor > 0.3 or performance.max_drawdown > 0.15:
                # Reduce position size
                new_size = current_size * (1 - step_size * 0.5)
                changes['position_size'] = max(
                    current_size * (1 - max_change),
                    new_size
                )
            elif performance_factor > 0.8 and volatility_factor < 0.2:
                # Increase position size for good performance in low volatility
                new_size = current_size * (1 + step_size * 0.3)
                changes['position_size'] = min(
                    current_size * (1 + max_change),
                    new_size
                )
        
        return changes
    
    def _estimate_performance_improvement(self,
                                        parameter_changes: Dict[str, Any],
                                        current_performance: PerformanceSnapshot,
                                        signal_strength: float) -> float:
        """Estimate expected performance improvement from parameter changes."""
        if not parameter_changes:
            return 0.0
        
        # Simple heuristic based on signal strength and number of parameters changed
        base_improvement = signal_strength * 0.1  # Base 10% improvement expectation
        
        # Adjust based on current performance quality
        if current_performance.sharpe_ratio < 0.5:
            base_improvement *= 1.5  # More improvement potential if currently poor
        elif current_performance.sharpe_ratio > 2.0:
            base_improvement *= 0.5  # Less improvement potential if already good
        
        # Adjust based on number of parameters changed
        param_factor = min(len(parameter_changes) / 3.0, 1.0)  # More changes = more potential
        
        return base_improvement * param_factor
    
    def _calculate_optimization_confidence(self,
                                         parameter_changes: Dict[str, Any],
                                         validation_result: ValidationResult,
                                         signal_strength: float,
                                         expected_improvement: float) -> float:
        """Calculate confidence in optimization."""
        if not validation_result.valid:
            return 0.0
        
        confidence_factors = {
            'signal_strength': signal_strength * 0.4,
            'validation_clean': 0.3 if not validation_result.errors else 0.0,
            'expected_improvement': min(expected_improvement * 2, 0.2),  # Cap at 0.2
            'parameter_count': min(len(parameter_changes) / 5.0, 0.1)  # More changes = slightly more confident
        }
        
        return sum(confidence_factors.values())
