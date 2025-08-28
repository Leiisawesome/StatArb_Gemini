"""
Optimization System for StatArb Trading System
==============================================

Phase 5B Infrastructure Consolidation - Monitoring Module
Consolidates optimization functionality into a unified system.

Consolidated from:
- continuous_optimizer.py (560 lines) - Strategy optimization and parameter tuning
- auto_tuner.py (508 lines) - Automated parameter adjustment system

This module provides comprehensive optimization capabilities including:
- Continuous parameter optimization with multiple strategies
- Automated performance tuning with rollback protection
- Real-time parameter adjustment based on performance feedback
- Bayesian optimization and adaptive learning algorithms
"""

import asyncio
import logging
import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime, timedelta
from enum import Enum
import statistics
import numpy as np

logger = logging.getLogger(__name__)

# =============================================================================
# Core Optimization Enums and Types
# =============================================================================

class OptimizationStrategy(Enum):
    """Optimization strategies"""
    GRADIENT_DESCENT = "gradient_descent"
    HILL_CLIMBING = "hill_climbing"
    SIMULATED_ANNEALING = "simulated_annealing"
    BAYESIAN = "bayesian"
    ADAPTIVE = "adaptive"


class ParameterType(Enum):
    """Types of parameters that can be optimized"""
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    CHOICE = "choice"


class TuningMode(Enum):
    """Auto-tuning modes"""
    CONSERVATIVE = "conservative"  # Small, safe changes
    AGGRESSIVE = "aggressive"     # Larger optimization steps
    EXPLORATORY = "exploratory"   # Wide parameter exploration
    RECOVERY = "recovery"         # Focus on stability recovery


class TuningPhase(Enum):
    """Auto-tuning phases"""
    BASELINE = "baseline"         # Establishing baseline performance
    OPTIMIZATION = "optimization" # Active optimization
    VALIDATION = "validation"     # Validating improvements
    MAINTENANCE = "maintenance"   # Maintaining optimal performance


class OptimizationStatus(Enum):
    """Status of optimization process"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"


# =============================================================================
# Configuration Classes
# =============================================================================

@dataclass
class OptimizerConfig:
    """Configuration for continuous optimizer"""
    # Optimization settings
    optimization_interval_seconds: int = 30
    min_samples_for_optimization: int = 10
    optimization_patience: int = 5  # Iterations without improvement
    
    # Strategy settings
    default_strategy: OptimizationStrategy = OptimizationStrategy.ADAPTIVE
    learning_rate: float = 0.1
    momentum: float = 0.9
    
    # Performance criteria
    improvement_threshold: float = 0.01  # 1% minimum improvement
    max_optimization_time_seconds: int = 300  # 5 minutes
    max_iterations: int = 100
    
    # Safety settings
    enable_rollback: bool = True
    max_parameter_change_percent: float = 0.20  # 20% max change per iteration
    stability_check_window: int = 10  # Samples to check for stability


@dataclass
class AutoTunerConfig:
    """Configuration for auto-tuner"""
    # Tuning behavior
    tuning_mode: TuningMode = TuningMode.CONSERVATIVE
    enable_automatic_tuning: bool = True
    enable_rollback_protection: bool = True
    
    # Performance targets
    target_latency_ms: float = 1.0
    target_throughput_improvement: float = 0.2  # 20% improvement
    target_error_rate: float = 0.01  # 1%
    target_sharpe_ratio: float = 2.0
    
    # Tuning intervals
    baseline_duration_minutes: int = 30
    optimization_duration_minutes: int = 120
    validation_duration_minutes: int = 60
    maintenance_check_interval_minutes: int = 15
    
    # Safety limits
    max_drawdown_during_tuning: float = 0.02  # 2%
    performance_degradation_threshold: float = 0.05  # 5%
    rollback_threshold: float = 0.10  # 10% performance drop triggers rollback


# =============================================================================
# Parameter Management System
# =============================================================================

@dataclass
class Parameter:
    """Represents a tunable parameter"""
    name: str
    param_type: ParameterType
    current_value: Any
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    choices: Optional[List[Any]] = None
    step_size: Optional[float] = None
    importance: float = 1.0  # Relative importance for optimization
    
    def __post_init__(self):
        """Validate parameter configuration"""
        if self.param_type == ParameterType.CHOICE and not self.choices:
            raise ValueError(f"Parameter {self.name} of type CHOICE must have choices defined")
        
        if self.param_type in [ParameterType.INTEGER, ParameterType.FLOAT]:
            if self.min_value is None or self.max_value is None:
                raise ValueError(f"Parameter {self.name} of type {self.param_type} must have min/max values")
    
    def get_random_value(self) -> Any:
        """Generate a random value within parameter bounds"""
        if self.param_type == ParameterType.INTEGER:
            return np.random.randint(self.min_value, self.max_value + 1)
        elif self.param_type == ParameterType.FLOAT:
            return np.random.uniform(self.min_value, self.max_value)
        elif self.param_type == ParameterType.BOOLEAN:
            return np.random.choice([True, False])
        elif self.param_type == ParameterType.CHOICE:
            return np.random.choice(self.choices)
    
    def perturb_value(self, magnitude: float = 0.1) -> Any:
        """Perturb current value by a small amount"""
        if self.param_type == ParameterType.INTEGER:
            change = int(magnitude * (self.max_value - self.min_value))
            new_value = self.current_value + np.random.randint(-change, change + 1)
            return max(self.min_value, min(self.max_value, new_value))
        elif self.param_type == ParameterType.FLOAT:
            change = magnitude * (self.max_value - self.min_value)
            new_value = self.current_value + np.random.uniform(-change, change)
            return max(self.min_value, min(self.max_value, new_value))
        elif self.param_type == ParameterType.BOOLEAN:
            return not self.current_value if np.random.random() < magnitude else self.current_value
        elif self.param_type == ParameterType.CHOICE:
            if np.random.random() < magnitude:
                available_choices = [c for c in self.choices if c != self.current_value]
                return np.random.choice(available_choices) if available_choices else self.current_value
            return self.current_value


@dataclass
class OptimizationResult:
    """Results from an optimization run"""
    parameter_values: Dict[str, Any]
    performance_score: float
    iteration: int
    timestamp: datetime
    strategy_used: OptimizationStrategy
    improvement_over_baseline: float
    
    
@dataclass
class TuningResult:
    """Results from auto-tuning process"""
    phase: TuningPhase
    performance_metrics: Dict[str, float]
    parameter_changes: Dict[str, Dict[str, Any]]  # param_name -> {old_value, new_value}
    improvement_achieved: float
    duration_seconds: float
    success: bool
    rollback_triggered: bool = False


# =============================================================================
# Continuous Optimizer System
# =============================================================================

class ContinuousOptimizer:
    """
    Continuous optimization system that adapts parameters based on performance feedback
    """
    
    def __init__(self, config: OptimizerConfig):
        self.config = config
        self.parameters: Dict[str, Parameter] = {}
        self.performance_history: deque = deque(maxlen=1000)
        self.optimization_history: List[OptimizationResult] = []
        
        # State tracking
        self.status = OptimizationStatus.IDLE
        self.current_iteration = 0
        self.best_performance = float('-inf')
        self.best_parameters: Dict[str, Any] = {}
        self.baseline_performance: Optional[float] = None
        
        # Performance tracking
        self.performance_callback: Optional[Callable[[], float]] = None
        self.parameter_update_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        
        # Threading
        self._optimization_thread: Optional[threading.Thread] = None
        self._stop_optimization = threading.Event()
        
        logger.info("ContinuousOptimizer initialized")
    
    def register_parameter(self, parameter: Parameter) -> None:
        """Register a parameter for optimization"""
        self.parameters[parameter.name] = parameter
        logger.info(f"Registered parameter: {parameter.name} ({parameter.param_type.value})")
    
    def set_performance_callback(self, callback: Callable[[], float]) -> None:
        """Set callback to get current performance score"""
        self.performance_callback = callback
    
    def set_parameter_update_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Set callback to update parameters in the target system"""
        self.parameter_update_callback = callback
    
    def start_optimization(self) -> None:
        """Start continuous optimization process"""
        if self.status == OptimizationStatus.RUNNING:
            logger.warning("Optimization already running")
            return
        
        if not self.performance_callback:
            raise ValueError("Performance callback must be set before starting optimization")
        
        self.status = OptimizationStatus.RUNNING
        self._stop_optimization.clear()
        
        # Establish baseline
        self._establish_baseline()
        
        # Start optimization thread
        self._optimization_thread = threading.Thread(target=self._optimization_loop)
        self._optimization_thread.daemon = True
        self._optimization_thread.start()
        
        logger.info("Started continuous optimization")
    
    def stop_optimization(self) -> None:
        """Stop continuous optimization process"""
        self._stop_optimization.set()
        if self._optimization_thread and self._optimization_thread.is_alive():
            self._optimization_thread.join(timeout=10)
        
        self.status = OptimizationStatus.IDLE
        logger.info("Stopped continuous optimization")
    
    def _establish_baseline(self) -> None:
        """Establish baseline performance with current parameters"""
        logger.info("Establishing baseline performance...")
        
        # Collect multiple samples for stable baseline
        baseline_samples = []
        for _ in range(self.config.min_samples_for_optimization):
            if self.performance_callback:
                score = self.performance_callback()
                baseline_samples.append(score)
                time.sleep(1)  # Small delay between samples
        
        self.baseline_performance = statistics.mean(baseline_samples)
        self.best_performance = self.baseline_performance
        
        # Store current parameters as best
        self.best_parameters = {name: param.current_value for name, param in self.parameters.items()}
        
        logger.info(f"Baseline performance established: {self.baseline_performance:.4f}")
    
    def _optimization_loop(self) -> None:
        """Main optimization loop"""
        patience_counter = 0
        
        while not self._stop_optimization.is_set() and self.status == OptimizationStatus.RUNNING:
            try:
                # Wait for optimization interval
                if self._stop_optimization.wait(self.config.optimization_interval_seconds):
                    break
                
                # Check if we have enough samples
                if len(self.performance_history) < self.config.min_samples_for_optimization:
                    continue
                
                # Perform optimization step
                improvement = self._optimization_step()
                
                # Check for improvement
                if improvement > self.config.improvement_threshold:
                    patience_counter = 0
                    logger.info(f"Optimization improvement: {improvement:.4f}")
                else:
                    patience_counter += 1
                    logger.debug(f"No significant improvement, patience: {patience_counter}/{self.config.optimization_patience}")
                
                # Check patience
                if patience_counter >= self.config.optimization_patience:
                    logger.info("Optimization patience exceeded, pausing")
                    self.status = OptimizationStatus.PAUSED
                    time.sleep(60)  # Wait before resuming
                    patience_counter = 0
                    self.status = OptimizationStatus.RUNNING
                
                self.current_iteration += 1
                
                # Check iteration limit
                if self.current_iteration >= self.config.max_iterations:
                    logger.info("Maximum iterations reached")
                    break
                    
            except Exception as e:
                logger.error(f"Error in optimization loop: {e}")
                self.status = OptimizationStatus.ERROR
                break
        
        self.status = OptimizationStatus.COMPLETED
        logger.info("Optimization loop completed")
    
    def _optimization_step(self) -> float:
        """Perform single optimization step"""
        strategy = self.config.default_strategy
        
        if strategy == OptimizationStrategy.ADAPTIVE:
            return self._adaptive_optimization()
        elif strategy == OptimizationStrategy.HILL_CLIMBING:
            return self._hill_climbing_step()
        elif strategy == OptimizationStrategy.BAYESIAN:
            return self._bayesian_optimization()
        else:
            return self._gradient_descent_step()
    
    def _adaptive_optimization(self) -> float:
        """Adaptive optimization strategy"""
        # Analyze recent performance trend
        recent_performance = list(self.performance_history)[-10:]
        if len(recent_performance) < 5:
            return self._hill_climbing_step()
        
        trend = np.polyfit(range(len(recent_performance)), recent_performance, 1)[0]
        
        if trend > 0:
            # Performance improving, continue with small steps
            return self._hill_climbing_step(magnitude=0.05)
        else:
            # Performance declining, try larger exploration
            return self._random_search_step(magnitude=0.15)
    
    def _hill_climbing_step(self, magnitude: float = 0.1) -> float:
        """Hill climbing optimization step"""
        # Select parameter to optimize (weighted by importance)
        weights = [param.importance for param in self.parameters.values()]
        param_names = list(self.parameters.keys())
        selected_param_name = np.random.choice(param_names, p=np.array(weights)/sum(weights))
        
        # Perturb selected parameter
        param = self.parameters[selected_param_name]
        old_value = param.current_value
        new_value = param.perturb_value(magnitude)
        
        # Test new parameter value
        param.current_value = new_value
        if self.parameter_update_callback:
            self.parameter_update_callback({selected_param_name: new_value})
        
        # Measure performance
        time.sleep(2)  # Allow system to stabilize
        new_performance = self.performance_callback() if self.performance_callback else 0
        
        # Decide whether to keep change
        if new_performance > self.best_performance:
            # Keep the change
            self.best_performance = new_performance
            self.best_parameters[selected_param_name] = new_value
            improvement = new_performance - (self.baseline_performance or 0)
            
            # Record result
            result = OptimizationResult(
                parameter_values={selected_param_name: new_value},
                performance_score=new_performance,
                iteration=self.current_iteration,
                timestamp=datetime.now(),
                strategy_used=OptimizationStrategy.HILL_CLIMBING,
                improvement_over_baseline=improvement
            )
            self.optimization_history.append(result)
            
            return improvement
        else:
            # Revert the change
            param.current_value = old_value
            if self.parameter_update_callback:
                self.parameter_update_callback({selected_param_name: old_value})
            return 0.0
    
    def _random_search_step(self, magnitude: float = 0.2) -> float:
        """Random search optimization step"""
        # Select multiple parameters to perturb
        num_params = min(3, len(self.parameters))
        selected_params = np.random.choice(list(self.parameters.keys()), num_params, replace=False)
        
        # Store old values
        old_values = {}
        new_values = {}
        
        # Perturb selected parameters
        for param_name in selected_params:
            param = self.parameters[param_name]
            old_values[param_name] = param.current_value
            new_values[param_name] = param.perturb_value(magnitude)
            param.current_value = new_values[param_name]
        
        # Update parameters
        if self.parameter_update_callback:
            self.parameter_update_callback(new_values)
        
        # Measure performance
        time.sleep(3)  # Allow system to stabilize
        new_performance = self.performance_callback() if self.performance_callback else 0
        
        # Decide whether to keep changes
        if new_performance > self.best_performance:
            # Keep the changes
            self.best_performance = new_performance
            self.best_parameters.update(new_values)
            improvement = new_performance - (self.baseline_performance or 0)
            
            # Record result
            result = OptimizationResult(
                parameter_values=new_values.copy(),
                performance_score=new_performance,
                iteration=self.current_iteration,
                timestamp=datetime.now(),
                strategy_used=OptimizationStrategy.HILL_CLIMBING,
                improvement_over_baseline=improvement
            )
            self.optimization_history.append(result)
            
            return improvement
        else:
            # Revert all changes
            for param_name in selected_params:
                self.parameters[param_name].current_value = old_values[param_name]
            
            if self.parameter_update_callback:
                self.parameter_update_callback(old_values)
            
            return 0.0
    
    def _bayesian_optimization(self) -> float:
        """Simplified Bayesian optimization step"""
        # This is a simplified version - in production, use a proper Bayesian optimization library
        return self._hill_climbing_step(magnitude=0.08)
    
    def _gradient_descent_step(self) -> float:
        """Simplified gradient descent step"""
        # This is a placeholder - proper gradient descent would require gradient computation
        return self._hill_climbing_step(magnitude=self.config.learning_rate)
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """Get summary of optimization progress"""
        return {
            'status': self.status.value,
            'current_iteration': self.current_iteration,
            'baseline_performance': self.baseline_performance,
            'best_performance': self.best_performance,
            'best_parameters': self.best_parameters.copy(),
            'total_improvement': (self.best_performance - (self.baseline_performance or 0)) if self.baseline_performance else 0,
            'optimization_history_length': len(self.optimization_history)
        }


# =============================================================================
# Auto-Tuner System
# =============================================================================

class AutoTuner:
    """
    Automated performance tuning system that combines monitoring with optimization
    """
    
    def __init__(self, auto_config: AutoTunerConfig, optimizer_config: OptimizerConfig):
        self.auto_config = auto_config
        self.optimizer = ContinuousOptimizer(optimizer_config)
        
        # State tracking
        self.current_phase = TuningPhase.BASELINE
        self.phase_start_time = datetime.now()
        self.tuning_history: List[TuningResult] = []
        
        # Performance tracking
        self.baseline_metrics: Dict[str, float] = {}
        self.current_metrics: Dict[str, float] = {}
        self.performance_trend = deque(maxlen=100)
        
        # Safety tracking
        self.rollback_checkpoint: Optional[Dict[str, Any]] = None
        self.performance_degradation_count = 0
        
        # Callbacks
        self.metrics_callback: Optional[Callable[[], Dict[str, float]]] = None
        
        logger.info(f"AutoTuner initialized in {self.auto_config.tuning_mode.value} mode")
    
    def set_metrics_callback(self, callback: Callable[[], Dict[str, float]]) -> None:
        """Set callback to get current performance metrics"""
        self.metrics_callback = callback
    
    def start_auto_tuning(self) -> None:
        """Start automated tuning process"""
        if not self.auto_config.enable_automatic_tuning:
            logger.info("Automatic tuning is disabled")
            return
        
        logger.info("Starting automated tuning process")
        
        # Set up optimizer callbacks
        self.optimizer.set_performance_callback(self._get_performance_score)
        self.optimizer.set_parameter_update_callback(self._update_parameters)
        
        # Start with baseline phase
        self._start_baseline_phase()
    
    def _get_performance_score(self) -> float:
        """Get current performance score for optimization"""
        if not self.metrics_callback:
            return 0.0
        
        metrics = self.metrics_callback()
        
        # Combine multiple metrics into single score
        score = 0.0
        
        # Latency component (lower is better)
        if 'latency_ms' in metrics:
            latency_score = max(0, 1 - metrics['latency_ms'] / (self.auto_config.target_latency_ms * 2))
            score += latency_score * 0.3
        
        # Throughput component (higher is better)
        if 'throughput' in metrics:
            baseline_throughput = self.baseline_metrics.get('throughput', 1.0)
            throughput_score = metrics['throughput'] / baseline_throughput
            score += throughput_score * 0.3
        
        # Error rate component (lower is better)
        if 'error_rate' in metrics:
            error_score = max(0, 1 - metrics['error_rate'] / (self.auto_config.target_error_rate * 2))
            score += error_score * 0.2
        
        # Sharpe ratio component (higher is better)
        if 'sharpe_ratio' in metrics:
            sharpe_score = metrics['sharpe_ratio'] / self.auto_config.target_sharpe_ratio
            score += sharpe_score * 0.2
        
        return score
    
    def _update_parameters(self, parameter_updates: Dict[str, Any]) -> None:
        """Update parameters in the target system"""
        logger.info(f"Updating parameters: {parameter_updates}")
        # This would interface with the actual system to update parameters
        
        # Check for safety violations
        if self._check_safety_violations():
            logger.warning("Safety violation detected, considering rollback")
            self._handle_safety_violation()
    
    def _start_baseline_phase(self) -> None:
        """Start baseline performance measurement phase"""
        self.current_phase = TuningPhase.BASELINE
        self.phase_start_time = datetime.now()
        
        logger.info("Starting baseline phase")
        
        # Collect baseline metrics
        self._collect_baseline_metrics()
        
        # Set rollback checkpoint
        self.rollback_checkpoint = self.optimizer.best_parameters.copy()
        
        # Schedule transition to optimization phase
        threading.Timer(
            self.auto_config.baseline_duration_minutes * 60,
            self._transition_to_optimization
        ).start()
    
    def _collect_baseline_metrics(self) -> None:
        """Collect baseline performance metrics"""
        if not self.metrics_callback:
            return
        
        # Collect multiple samples
        samples = []
        for _ in range(10):
            metrics = self.metrics_callback()
            samples.append(metrics)
            time.sleep(5)
        
        # Average the samples
        for key in samples[0].keys():
            self.baseline_metrics[key] = statistics.mean([s[key] for s in samples])
        
        logger.info(f"Baseline metrics: {self.baseline_metrics}")
    
    def _transition_to_optimization(self) -> None:
        """Transition to optimization phase"""
        if self.current_phase != TuningPhase.BASELINE:
            return
        
        self.current_phase = TuningPhase.OPTIMIZATION
        self.phase_start_time = datetime.now()
        
        logger.info("Transitioning to optimization phase")
        
        # Start continuous optimization
        self.optimizer.start_optimization()
        
        # Schedule transition to validation phase
        threading.Timer(
            self.auto_config.optimization_duration_minutes * 60,
            self._transition_to_validation
        ).start()
    
    def _transition_to_validation(self) -> None:
        """Transition to validation phase"""
        if self.current_phase != TuningPhase.OPTIMIZATION:
            return
        
        self.current_phase = TuningPhase.VALIDATION
        self.phase_start_time = datetime.now()
        
        logger.info("Transitioning to validation phase")
        
        # Stop optimization for validation
        self.optimizer.stop_optimization()
        
        # Validate improvements
        self._validate_improvements()
        
        # Schedule transition to maintenance phase
        threading.Timer(
            self.auto_config.validation_duration_minutes * 60,
            self._transition_to_maintenance
        ).start()
    
    def _validate_improvements(self) -> None:
        """Validate that optimizations actually improved performance"""
        if not self.metrics_callback:
            return
        
        # Collect validation metrics
        validation_samples = []
        for _ in range(20):
            metrics = self.metrics_callback()
            validation_samples.append(metrics)
            time.sleep(3)
        
        # Average validation metrics
        validation_metrics = {}
        for key in validation_samples[0].keys():
            validation_metrics[key] = statistics.mean([s[key] for s in validation_samples])
        
        # Compare with baseline
        improvement_achieved = self._calculate_improvement(validation_metrics)
        
        if improvement_achieved < 0:
            logger.warning(f"Performance degraded by {-improvement_achieved:.2%}, triggering rollback")
            self._trigger_rollback()
        else:
            logger.info(f"Performance improved by {improvement_achieved:.2%}")
            
        # Record tuning result
        result = TuningResult(
            phase=TuningPhase.VALIDATION,
            performance_metrics=validation_metrics.copy(),
            parameter_changes=self._get_parameter_changes(),
            improvement_achieved=improvement_achieved,
            duration_seconds=(datetime.now() - self.phase_start_time).total_seconds(),
            success=improvement_achieved > 0,
            rollback_triggered=improvement_achieved < 0
        )
        self.tuning_history.append(result)
    
    def _transition_to_maintenance(self) -> None:
        """Transition to maintenance phase"""
        self.current_phase = TuningPhase.MAINTENANCE
        self.phase_start_time = datetime.now()
        
        logger.info("Transitioning to maintenance phase")
        
        # Schedule periodic maintenance checks
        self._schedule_maintenance_checks()
    
    def _schedule_maintenance_checks(self) -> None:
        """Schedule periodic maintenance checks"""
        def maintenance_check():
            if self.current_phase == TuningPhase.MAINTENANCE:
                self._perform_maintenance_check()
                # Schedule next check
                threading.Timer(
                    self.auto_config.maintenance_check_interval_minutes * 60,
                    maintenance_check
                ).start()
        
        maintenance_check()
    
    def _perform_maintenance_check(self) -> None:
        """Perform periodic maintenance check"""
        if not self.metrics_callback:
            return
        
        current_metrics = self.metrics_callback()
        current_performance = self._calculate_improvement(current_metrics)
        
        # Check if performance has degraded
        if current_performance < -self.auto_config.performance_degradation_threshold:
            logger.warning("Performance degradation detected in maintenance phase")
            self.performance_degradation_count += 1
            
            if self.performance_degradation_count >= 3:
                logger.info("Multiple performance degradations, restarting optimization")
                self._restart_optimization_cycle()
        else:
            self.performance_degradation_count = 0
    
    def _calculate_improvement(self, current_metrics: Dict[str, float]) -> float:
        """Calculate overall improvement compared to baseline"""
        if not self.baseline_metrics:
            return 0.0
        
        total_improvement = 0.0
        weight_sum = 0.0
        
        # Latency improvement (lower is better)
        if 'latency_ms' in self.baseline_metrics and 'latency_ms' in current_metrics:
            latency_improvement = (self.baseline_metrics['latency_ms'] - current_metrics['latency_ms']) / self.baseline_metrics['latency_ms']
            total_improvement += latency_improvement * 0.3
            weight_sum += 0.3
        
        # Throughput improvement (higher is better)
        if 'throughput' in self.baseline_metrics and 'throughput' in current_metrics:
            throughput_improvement = (current_metrics['throughput'] - self.baseline_metrics['throughput']) / self.baseline_metrics['throughput']
            total_improvement += throughput_improvement * 0.3
            weight_sum += 0.3
        
        # Error rate improvement (lower is better)
        if 'error_rate' in self.baseline_metrics and 'error_rate' in current_metrics:
            error_improvement = (self.baseline_metrics['error_rate'] - current_metrics['error_rate']) / self.baseline_metrics['error_rate']
            total_improvement += error_improvement * 0.2
            weight_sum += 0.2
        
        # Sharpe ratio improvement (higher is better)
        if 'sharpe_ratio' in self.baseline_metrics and 'sharpe_ratio' in current_metrics:
            sharpe_improvement = (current_metrics['sharpe_ratio'] - self.baseline_metrics['sharpe_ratio']) / self.baseline_metrics['sharpe_ratio']
            total_improvement += sharpe_improvement * 0.2
            weight_sum += 0.2
        
        return total_improvement / weight_sum if weight_sum > 0 else 0.0
    
    def _check_safety_violations(self) -> bool:
        """Check for safety violations that require intervention"""
        if not self.metrics_callback:
            return False
        
        current_metrics = self.metrics_callback()
        
        # Check drawdown limit
        if 'drawdown' in current_metrics:
            if current_metrics['drawdown'] > self.auto_config.max_drawdown_during_tuning:
                return True
        
        # Check error rate limit
        if 'error_rate' in current_metrics:
            if current_metrics['error_rate'] > self.auto_config.target_error_rate * 3:
                return True
        
        return False
    
    def _handle_safety_violation(self) -> None:
        """Handle safety violation"""
        logger.warning("Handling safety violation")
        
        if self.auto_config.enable_rollback_protection:
            self._trigger_rollback()
        else:
            # Just stop optimization
            self.optimizer.stop_optimization()
    
    def _trigger_rollback(self) -> None:
        """Trigger rollback to safe parameters"""
        if not self.rollback_checkpoint:
            logger.error("No rollback checkpoint available")
            return
        
        logger.info("Triggering parameter rollback")
        
        # Restore parameters
        if self.optimizer.parameter_update_callback:
            self.optimizer.parameter_update_callback(self.rollback_checkpoint)
        
        # Update optimizer state
        for param_name, value in self.rollback_checkpoint.items():
            if param_name in self.optimizer.parameters:
                self.optimizer.parameters[param_name].current_value = value
    
    def _get_parameter_changes(self) -> Dict[str, Dict[str, Any]]:
        """Get parameter changes from baseline"""
        changes = {}
        
        for param_name, param in self.optimizer.parameters.items():
            if self.rollback_checkpoint and param_name in self.rollback_checkpoint:
                old_value = self.rollback_checkpoint[param_name]
                new_value = param.current_value
                
                if old_value != new_value:
                    changes[param_name] = {
                        'old_value': old_value,
                        'new_value': new_value
                    }
        
        return changes
    
    def _restart_optimization_cycle(self) -> None:
        """Restart the entire optimization cycle"""
        logger.info("Restarting optimization cycle")
        
        # Stop current optimization
        self.optimizer.stop_optimization()
        
        # Reset state
        self.performance_degradation_count = 0
        
        # Start over with baseline phase
        self._start_baseline_phase()
    
    def get_tuning_summary(self) -> Dict[str, Any]:
        """Get summary of auto-tuning progress"""
        return {
            'current_phase': self.current_phase.value,
            'tuning_mode': self.auto_config.tuning_mode.value,
            'phase_duration_minutes': (datetime.now() - self.phase_start_time).total_seconds() / 60,
            'baseline_metrics': self.baseline_metrics.copy(),
            'current_metrics': self.current_metrics.copy(),
            'tuning_history_length': len(self.tuning_history),
            'performance_degradation_count': self.performance_degradation_count,
            'optimizer_summary': self.optimizer.get_optimization_summary()
        }


# =============================================================================
# Optimization System Factory
# =============================================================================

class OptimizationSystemFactory:
    """Factory for creating optimization system components"""
    
    @staticmethod
    def create_conservative_optimizer() -> ContinuousOptimizer:
        """Create optimizer with conservative settings"""
        config = OptimizerConfig(
            optimization_interval_seconds=60,
            learning_rate=0.05,
            max_parameter_change_percent=0.10,
            improvement_threshold=0.005
        )
        return ContinuousOptimizer(config)
    
    @staticmethod
    def create_aggressive_optimizer() -> ContinuousOptimizer:
        """Create optimizer with aggressive settings"""
        config = OptimizerConfig(
            optimization_interval_seconds=15,
            learning_rate=0.2,
            max_parameter_change_percent=0.30,
            improvement_threshold=0.02
        )
        return ContinuousOptimizer(config)
    
    @staticmethod
    def create_production_auto_tuner() -> AutoTuner:
        """Create auto-tuner for production environment"""
        auto_config = AutoTunerConfig(
            tuning_mode=TuningMode.CONSERVATIVE,
            enable_automatic_tuning=True,
            enable_rollback_protection=True,
            baseline_duration_minutes=60,
            optimization_duration_minutes=240,
            validation_duration_minutes=120
        )
        
        optimizer_config = OptimizerConfig(
            optimization_interval_seconds=30,
            learning_rate=0.1,
            max_parameter_change_percent=0.15
        )
        
        return AutoTuner(auto_config, optimizer_config)
    
    @staticmethod
    def create_production_optimization_system() -> Tuple[ContinuousOptimizer, AutoTuner, 'OptimizationSystemFactory']:
        """Create complete optimization system for production environment"""
        # Production optimizer config
        optimizer_config = OptimizerConfig(
            optimization_interval_seconds=30,
            learning_rate=0.1,
            max_parameter_change_percent=0.15,
            improvement_threshold=0.01,
            default_strategy=OptimizationStrategy.ADAPTIVE,
            enable_rollback=True,
            max_optimization_time_seconds=300
        )
        
        # Production auto-tuner config
        auto_tuner_config = AutoTunerConfig(
            tuning_mode=TuningMode.CONSERVATIVE,
            enable_automatic_tuning=True,
            enable_rollback_protection=True,
            baseline_duration_minutes=60,
            optimization_duration_minutes=240,
            validation_duration_minutes=120,
            target_throughput_improvement=0.05
        )
        
        optimizer = ContinuousOptimizer(optimizer_config)
        auto_tuner = AutoTuner(auto_tuner_config, optimizer_config)
        factory = OptimizationSystemFactory()
        
        return optimizer, auto_tuner, factory
    
    @staticmethod
    def create_development_optimization_system() -> Tuple[ContinuousOptimizer, AutoTuner, 'OptimizationSystemFactory']:
        """Create optimization system for development environment"""
        # Development optimizer config
        optimizer_config = OptimizerConfig(
            optimization_interval_seconds=60,
            learning_rate=0.05,
            max_parameter_change_percent=0.20,
            improvement_threshold=0.02,
            default_strategy=OptimizationStrategy.HILL_CLIMBING,
            enable_rollback=True,
            max_optimization_time_seconds=180
        )
        
        # Development auto-tuner config
        auto_tuner_config = AutoTunerConfig(
            tuning_mode=TuningMode.EXPLORATORY,
            enable_automatic_tuning=False,
            enable_rollback_protection=True,
            baseline_duration_minutes=30,
            optimization_duration_minutes=60,
            validation_duration_minutes=30
        )
        
        optimizer = ContinuousOptimizer(optimizer_config)
        auto_tuner = AutoTuner(auto_tuner_config, optimizer_config)
        factory = OptimizationSystemFactory()
        
        return optimizer, auto_tuner, factory


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    # Enums
    'OptimizationStrategy',
    'ParameterType', 
    'TuningMode',
    'TuningPhase',
    'OptimizationStatus',
    
    # Configuration classes
    'OptimizerConfig',
    'AutoTunerConfig',
    
    # Data classes
    'Parameter',
    'OptimizationResult',
    'TuningResult',
    
    # Core systems
    'ContinuousOptimizer',
    'AutoTuner',
    
    # Factory
    'OptimizationSystemFactory'
]
