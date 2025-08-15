"""
Continuous Optimizer
===================

Provides continuous optimization of component parameters based on
real-time performance feedback and adaptive tuning algorithms.

Author: Pro Quant Desk Trader
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
    exploration_rate: float = 0.1
    
    # Safety settings
    max_parameter_change_per_iteration: float = 0.2  # 20% max change
    enable_rollback_on_degradation: bool = True
    degradation_threshold: float = 0.1  # 10% performance degradation
    
    # Targeting
    target_latency_improvement: float = 0.1  # 10% improvement target
    target_throughput_improvement: float = 0.15  # 15% improvement target

@dataclass
class Parameter:
    """Optimizable parameter definition"""
    name: str
    param_type: ParameterType
    current_value: Any
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    choices: Optional[List[Any]] = None
    step_size: Optional[float] = None

@dataclass
class OptimizationResult:
    """Result of optimization iteration"""
    timestamp: datetime
    component: str
    parameter: str
    old_value: Any
    new_value: Any
    performance_before: float
    performance_after: float
    improvement: float
    strategy_used: OptimizationStrategy

class PerformanceTracker:
    """Tracks performance metrics for optimization"""
    
    def __init__(self, history_size: int = 1000):
        self.history_size = history_size
        self.performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=history_size))
        self.parameter_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=history_size))
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def record_performance(self, component: str, metric_name: str, value: float, 
                          parameters: Dict[str, Any]):
        """Record performance measurement with current parameters"""
        timestamp = datetime.now()
        
        # Store performance
        perf_key = f"{component}_{metric_name}"
        self.performance_history[perf_key].append((timestamp, value))
        
        # Store parameters
        param_key = f"{component}_params"
        self.parameter_history[param_key].append((timestamp, parameters.copy()))
    
    def get_recent_performance(self, component: str, metric_name: str, 
                             duration_seconds: int = 300) -> List[Tuple[datetime, float]]:
        """Get recent performance measurements"""
        perf_key = f"{component}_{metric_name}"
        if perf_key not in self.performance_history:
            return []
        
        cutoff_time = datetime.now() - timedelta(seconds=duration_seconds)
        return [(ts, val) for ts, val in self.performance_history[perf_key] if ts >= cutoff_time]
    
    def calculate_performance_trend(self, component: str, metric_name: str,
                                   duration_seconds: int = 300) -> Dict[str, float]:
        """Calculate performance trend and statistics"""
        recent_perf = self.get_recent_performance(component, metric_name, duration_seconds)
        
        if len(recent_perf) < 2:
            return {}
        
        values = [val for _, val in recent_perf]
        timestamps = [(ts - recent_perf[0][0]).total_seconds() for ts, _ in recent_perf]
        
        # Calculate trend using linear regression
        if len(values) > 1:
            trend_slope = np.polyfit(timestamps, values, 1)[0] if len(set(timestamps)) > 1 else 0.0
        else:
            trend_slope = 0.0
        
        return {
            'mean': statistics.mean(values),
            'std_dev': statistics.stdev(values) if len(values) > 1 else 0.0,
            'trend_slope': trend_slope,
            'improvement_rate': -trend_slope if metric_name.endswith('latency') else trend_slope,
            'recent_value': values[-1],
            'baseline_value': values[0],
            'relative_change': (values[-1] - values[0]) / values[0] if values[0] != 0 else 0.0
        }

class OptimizationStrategy:
    """Base class for optimization strategies"""
    
    def __init__(self, config: OptimizerConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def suggest_parameter_change(self, parameter: Parameter, performance_trend: Dict[str, float],
                                optimization_history: List[OptimizationResult]) -> Any:
        """Suggest new parameter value based on performance trend"""
        raise NotImplementedError

class AdaptiveStrategy(OptimizationStrategy):
    """Adaptive optimization strategy that combines multiple approaches"""
    
    def suggest_parameter_change(self, parameter: Parameter, performance_trend: Dict[str, float],
                                optimization_history: List[OptimizationResult]) -> Any:
        """Adaptive parameter suggestion based on performance characteristics"""
        
        if not performance_trend:
            return parameter.current_value
        
        # Determine if we're improving or degrading
        improvement_rate = performance_trend.get('improvement_rate', 0.0)
        relative_change = performance_trend.get('relative_change', 0.0)
        
        # Get recent optimization history for this parameter
        recent_optimizations = [opt for opt in optimization_history[-10:] 
                              if opt.parameter == parameter.name]
        
        # Adaptive decision making
        if improvement_rate > 0:
            # Performance is improving - continue in same direction
            return self._continue_direction(parameter, recent_optimizations)
        elif improvement_rate < -0.05:  # Significant degradation
            # Performance is degrading - reverse direction or try different approach
            return self._reverse_direction(parameter, recent_optimizations)
        else:
            # Performance is stable - explore nearby values
            return self._explore_nearby(parameter)
    
    def _continue_direction(self, parameter: Parameter, recent_optimizations: List[OptimizationResult]) -> Any:
        """Continue optimization in current direction"""
        if not recent_optimizations:
            return self._explore_nearby(parameter)
        
        # Determine direction from recent changes
        last_opt = recent_optimizations[-1]
        
        if parameter.param_type == ParameterType.INTEGER:
            direction = 1 if last_opt.new_value > last_opt.old_value else -1
            step = max(1, int(abs(last_opt.new_value - last_opt.old_value) * 1.2))
            new_value = parameter.current_value + (direction * step)
            
            # Apply bounds
            if parameter.min_value is not None:
                new_value = max(parameter.min_value, new_value)
            if parameter.max_value is not None:
                new_value = min(parameter.max_value, new_value)
            
            return new_value
            
        elif parameter.param_type == ParameterType.FLOAT:
            direction = 1 if last_opt.new_value > last_opt.old_value else -1
            step = abs(last_opt.new_value - last_opt.old_value) * 1.2
            new_value = parameter.current_value + (direction * step)
            
            # Apply bounds
            if parameter.min_value is not None:
                new_value = max(parameter.min_value, new_value)
            if parameter.max_value is not None:
                new_value = min(parameter.max_value, new_value)
            
            return new_value
        
        return parameter.current_value
    
    def _reverse_direction(self, parameter: Parameter, recent_optimizations: List[OptimizationResult]) -> Any:
        """Reverse optimization direction"""
        if not recent_optimizations:
            return parameter.current_value
        
        # Go back towards previous good value
        good_optimizations = [opt for opt in recent_optimizations if opt.improvement > 0]
        
        if good_optimizations:
            target_value = good_optimizations[-1].new_value
            
            if parameter.param_type == ParameterType.INTEGER:
                direction = 1 if target_value > parameter.current_value else -1
                step = max(1, int(abs(target_value - parameter.current_value) * 0.5))
                return parameter.current_value + (direction * step)
                
            elif parameter.param_type == ParameterType.FLOAT:
                step = abs(target_value - parameter.current_value) * 0.5
                direction = 1 if target_value > parameter.current_value else -1
                return parameter.current_value + (direction * step)
        
        return parameter.current_value
    
    def _explore_nearby(self, parameter: Parameter) -> Any:
        """Explore nearby parameter values"""
        if parameter.param_type == ParameterType.INTEGER:
            if parameter.step_size:
                step = max(1, int(parameter.step_size))
            else:
                range_size = (parameter.max_value - parameter.min_value) if (parameter.min_value is not None and parameter.max_value is not None) else 10
                step = max(1, int(range_size * 0.05))  # 5% of range
            
            # Randomly choose direction
            direction = np.random.choice([-1, 1])
            new_value = parameter.current_value + (direction * step)
            
            # Apply bounds
            if parameter.min_value is not None:
                new_value = max(parameter.min_value, new_value)
            if parameter.max_value is not None:
                new_value = min(parameter.max_value, new_value)
            
            return new_value
            
        elif parameter.param_type == ParameterType.FLOAT:
            if parameter.step_size:
                step = parameter.step_size
            else:
                range_size = (parameter.max_value - parameter.min_value) if (parameter.min_value is not None and parameter.max_value is not None) else parameter.current_value
                step = range_size * 0.05  # 5% of range or current value
            
            # Randomly choose direction
            direction = np.random.choice([-1, 1])
            new_value = parameter.current_value + (direction * step)
            
            # Apply bounds
            if parameter.min_value is not None:
                new_value = max(parameter.min_value, new_value)
            if parameter.max_value is not None:
                new_value = min(parameter.max_value, new_value)
            
            return new_value
            
        elif parameter.param_type == ParameterType.BOOLEAN:
            return not parameter.current_value
            
        elif parameter.param_type == ParameterType.CHOICE:
            if parameter.choices:
                current_index = parameter.choices.index(parameter.current_value) if parameter.current_value in parameter.choices else 0
                new_index = (current_index + np.random.choice([-1, 1])) % len(parameter.choices)
                return parameter.choices[new_index]
        
        return parameter.current_value

class ContinuousOptimizer:
    """
    Continuous optimizer that automatically tunes component parameters
    based on real-time performance feedback.
    """
    
    def __init__(self, config: Optional[OptimizerConfig] = None):
        self.config = config or OptimizerConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Optimization components
        self.performance_tracker = PerformanceTracker()
        self.optimization_strategy = AdaptiveStrategy(self.config)
        
        # Optimization state
        self.is_optimizing = False
        self.optimizer_thread: Optional[threading.Thread] = None
        self.registered_components: Dict[str, Dict[str, Any]] = {}
        self.optimization_history: List[OptimizationResult] = []
        
        # Performance tracking
        self.optimization_start_time: Optional[datetime] = None
        self.total_optimizations = 0
        self.successful_optimizations = 0
        
        self.logger.info(f"ContinuousOptimizer initialized - Interval: {self.config.optimization_interval_seconds}s")
    
    def register_component(self, component_name: str, component: Any, 
                          parameters: Dict[str, Parameter]):
        """Register a component for continuous optimization"""
        self.registered_components[component_name] = {
            'component': component,
            'parameters': parameters,
            'last_optimization': None,
            'consecutive_failures': 0
        }
        
        self.logger.info(f"Registered component for optimization: {component_name} "
                        f"with {len(parameters)} parameters")
    
    def start_optimization(self):
        """Start continuous optimization"""
        if self.is_optimizing:
            self.logger.warning("Optimization is already running")
            return
        
        self.is_optimizing = True
        self.optimization_start_time = datetime.now()
        self.optimizer_thread = threading.Thread(target=self._optimization_loop, daemon=True)
        self.optimizer_thread.start()
        
        self.logger.info("Continuous optimization started")
    
    def stop_optimization(self):
        """Stop continuous optimization"""
        self.is_optimizing = False
        
        if self.optimizer_thread:
            self.optimizer_thread.join(timeout=1.0)
        
        self.logger.info("Continuous optimization stopped")
    
    def record_performance(self, component_name: str, metric_name: str, value: float):
        """Record performance measurement for optimization"""
        if component_name in self.registered_components:
            # Get current parameters
            component_info = self.registered_components[component_name]
            current_params = {}
            
            for param_name, parameter in component_info['parameters'].items():
                if hasattr(component_info['component'], param_name):
                    current_params[param_name] = getattr(component_info['component'], param_name)
                elif hasattr(component_info['component'], 'config') and hasattr(component_info['component'].config, param_name):
                    current_params[param_name] = getattr(component_info['component'].config, param_name)
            
            self.performance_tracker.record_performance(component_name, metric_name, value, current_params)
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """Get current optimization status"""
        uptime = (datetime.now() - self.optimization_start_time).total_seconds() if self.optimization_start_time else 0
        
        return {
            'optimization_active': self.is_optimizing,
            'uptime_seconds': uptime,
            'registered_components': list(self.registered_components.keys()),
            'total_optimizations': self.total_optimizations,
            'successful_optimizations': self.successful_optimizations,
            'success_rate': (self.successful_optimizations / max(1, self.total_optimizations)) * 100,
            'optimizations_per_hour': (self.total_optimizations / max(1, uptime / 3600)),
            'recent_optimizations': self.optimization_history[-10:]  # Last 10 optimizations
        }
    
    def _optimization_loop(self):
        """Main optimization loop"""
        self.logger.info("Starting optimization loop")
        
        while self.is_optimizing:
            try:
                start_time = time.perf_counter()
                
                # Optimize all registered components
                for component_name in self.registered_components.keys():
                    self._optimize_component(component_name)
                
                # Calculate loop timing
                loop_time = time.perf_counter() - start_time
                
                # Sleep for remaining interval time
                sleep_time = max(0, self.config.optimization_interval_seconds - loop_time)
                time.sleep(sleep_time)
                
            except Exception as e:
                self.logger.error(f"Optimization loop error: {e}")
                time.sleep(5.0)  # Error recovery delay
    
    def _optimize_component(self, component_name: str):
        """Optimize a specific component"""
        try:
            component_info = self.registered_components[component_name]
            component = component_info['component']
            parameters = component_info['parameters']
            
            # Check if we have enough performance data
            performance_data = {}
            for metric_name in ['latency', 'throughput', 'processing_time_ms', 'ops_per_second']:
                trend = self.performance_tracker.calculate_performance_trend(component_name, metric_name)
                if trend:
                    performance_data[metric_name] = trend
            
            if not performance_data:
                self.logger.debug(f"Insufficient performance data for {component_name}")
                return
            
            # Select primary metric for optimization
            primary_metric = self._select_primary_metric(performance_data)
            if not primary_metric:
                return
            
            primary_trend = performance_data[primary_metric]
            
            # Check if optimization is needed
            if not self._needs_optimization(primary_trend):
                return
            
            # Select parameter to optimize
            parameter_to_optimize = self._select_parameter_to_optimize(component_name, parameters, primary_trend)
            if not parameter_to_optimize:
                return
            
            # Get performance baseline
            performance_before = primary_trend['recent_value']
            
            # Suggest new parameter value
            new_value = self.optimization_strategy.suggest_parameter_change(
                parameter_to_optimize, primary_trend, self.optimization_history
            )
            
            if new_value == parameter_to_optimize.current_value:
                return  # No change suggested
            
            # Apply parameter change
            old_value = parameter_to_optimize.current_value
            success = self._apply_parameter_change(component, parameter_to_optimize.name, new_value)
            
            if success:
                # Update parameter tracking
                parameter_to_optimize.current_value = new_value
                
                # Wait a bit for performance to stabilize
                time.sleep(2.0)
                
                # Record optimization attempt
                self.total_optimizations += 1
                
                # We'll measure improvement in the next cycle
                # For now, record the optimization attempt
                result = OptimizationResult(
                    timestamp=datetime.now(),
                    component=component_name,
                    parameter=parameter_to_optimize.name,
                    old_value=old_value,
                    new_value=new_value,
                    performance_before=performance_before,
                    performance_after=performance_before,  # Will be updated later
                    improvement=0.0,  # Will be calculated later
                    strategy_used=self.config.default_strategy
                )
                
                self.optimization_history.append(result)
                
                self.logger.info(f"Optimized {component_name}.{parameter_to_optimize.name}: "
                               f"{old_value} → {new_value}")
                
                component_info['last_optimization'] = datetime.now()
                component_info['consecutive_failures'] = 0
                self.successful_optimizations += 1
            else:
                component_info['consecutive_failures'] += 1
                
        except Exception as e:
            self.logger.error(f"Component optimization failed for {component_name}: {e}")
    
    def _select_primary_metric(self, performance_data: Dict[str, Dict[str, float]]) -> Optional[str]:
        """Select the primary metric to optimize"""
        # Prioritize latency metrics first, then throughput
        priority_order = ['latency', 'processing_time_ms', 'throughput', 'ops_per_second']
        
        for metric in priority_order:
            if metric in performance_data:
                return metric
        
        # Return any available metric
        return next(iter(performance_data.keys())) if performance_data else None
    
    def _needs_optimization(self, performance_trend: Dict[str, float]) -> bool:
        """Determine if optimization is needed based on performance trend"""
        improvement_rate = performance_trend.get('improvement_rate', 0.0)
        relative_change = performance_trend.get('relative_change', 0.0)
        
        # Optimize if performance is degrading or stagnating
        return improvement_rate <= 0 or abs(relative_change) < 0.01
    
    def _select_parameter_to_optimize(self, component_name: str, parameters: Dict[str, Parameter],
                                    performance_trend: Dict[str, float]) -> Optional[Parameter]:
        """Select which parameter to optimize"""
        # For simplicity, cycle through parameters
        # In a more sophisticated implementation, we could use correlation analysis
        
        param_names = list(parameters.keys())
        if not param_names:
            return None
        
        # Use component's consecutive failures to determine parameter selection
        component_info = self.registered_components[component_name]
        failure_count = component_info.get('consecutive_failures', 0)
        
        # Cycle through parameters based on failure count
        param_index = failure_count % len(param_names)
        param_name = param_names[param_index]
        
        return parameters[param_name]
    
    def _apply_parameter_change(self, component: Any, parameter_name: str, new_value: Any) -> bool:
        """Apply parameter change to component"""
        try:
            # Try direct attribute access first
            if hasattr(component, parameter_name):
                setattr(component, parameter_name, new_value)
                return True
            
            # Try config attribute access
            if hasattr(component, 'config') and hasattr(component.config, parameter_name):
                setattr(component.config, parameter_name, new_value)
                return True
            
            # Try parameter update method
            if hasattr(component, 'update_parameter'):
                component.update_parameter(parameter_name, new_value)
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to apply parameter change {parameter_name}={new_value}: {e}")
            return False
