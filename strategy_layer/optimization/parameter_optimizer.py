"""
Parameter Optimizer Base Class

Base class for parameter optimization algorithms.

Author: Pro Quant Desk Trader
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from strategy_layer.base import StrategyError


@dataclass
class OptimizationConfig:
    """Configuration for parameter optimization"""
    # Optimization parameters
    max_iterations: int = 100
    population_size: int = 50
    crossover_rate: float = 0.8
    mutation_rate: float = 0.1
    elite_size: int = 5
    
    # Convergence parameters
    tolerance: float = 1e-6
    patience: int = 10
    
    # Parameter bounds
    parameter_bounds: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    
    # Objective function weights
    objective_weights: Dict[str, float] = field(default_factory=dict)
    
    # Validation parameters
    validation_split: float = 0.2
    min_trades: int = 10
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'max_iterations': self.max_iterations,
            'population_size': self.population_size,
            'crossover_rate': self.crossover_rate,
            'mutation_rate': self.mutation_rate,
            'elite_size': self.elite_size,
            'tolerance': self.tolerance,
            'patience': self.patience,
            'parameter_bounds': self.parameter_bounds,
            'objective_weights': self.objective_weights,
            'validation_split': self.validation_split,
            'min_trades': self.min_trades
        }


@dataclass
class OptimizationResult:
    """Result of parameter optimization"""
    # Best parameters found
    best_parameters: Dict[str, float]
    
    # Best objective value
    best_objective: float
    
    # Optimization history
    history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Convergence info
    converged: bool = False
    iterations: int = 0
    
    # Performance metrics
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    
    # Validation metrics
    validation_metrics: Dict[str, float] = field(default_factory=dict)
    
    # Timestamp
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'best_parameters': self.best_parameters,
            'best_objective': self.best_objective,
            'history': self.history,
            'converged': self.converged,
            'iterations': self.iterations,
            'performance_metrics': self.performance_metrics,
            'validation_metrics': self.validation_metrics,
            'timestamp': self.timestamp.isoformat()
        }


class ParameterOptimizer(ABC):
    """Base class for parameter optimization algorithms"""
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self._validate_config()
    
    @abstractmethod
    def optimize(self, objective_function: Callable, initial_parameters: Dict[str, float]) -> OptimizationResult:
        """Optimize parameters using the objective function"""
        pass
    
    def _validate_config(self):
        """Validate optimization configuration"""
        if self.config.max_iterations <= 0:
            raise StrategyError("Max iterations must be positive")
        
        if self.config.population_size <= 0:
            raise StrategyError("Population size must be positive")
        
        if not (0 <= self.config.crossover_rate <= 1):
            raise StrategyError("Crossover rate must be between 0 and 1")
        
        if not (0 <= self.config.mutation_rate <= 1):
            raise StrategyError("Mutation rate must be between 0 and 1")
        
        if self.config.elite_size >= self.config.population_size:
            raise StrategyError("Elite size must be less than population size")
    
    def _validate_parameters(self, parameters: Dict[str, float]) -> bool:
        """Validate parameters against bounds"""
        for param_name, param_value in parameters.items():
            if param_name in self.config.parameter_bounds:
                min_val, max_val = self.config.parameter_bounds[param_name]
                if not (min_val <= param_value <= max_val):
                    self.logger.warning(f"Parameter {param_name} = {param_value} outside bounds [{min_val}, {max_val}]")
                    return False
        return True
    
    def _clip_parameters(self, parameters: Dict[str, float]) -> Dict[str, float]:
        """Clip parameters to bounds"""
        clipped_params = parameters.copy()
        for param_name, param_value in clipped_params.items():
            if param_name in self.config.parameter_bounds:
                min_val, max_val = self.config.parameter_bounds[param_name]
                clipped_params[param_name] = np.clip(param_value, min_val, max_val)
        return clipped_params
    
    def _calculate_objective(self, objective_values: Dict[str, float]) -> float:
        """Calculate weighted objective value"""
        if not self.config.objective_weights:
            # If no weights specified, use equal weights
            return np.mean(list(objective_values.values()))
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for metric, value in objective_values.items():
            weight = self.config.objective_weights.get(metric, 1.0)
            weighted_sum += weight * value
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _check_convergence(self, history: List[Dict[str, Any]], patience: int = None) -> bool:
        """Check if optimization has converged"""
        if patience is None:
            patience = self.config.patience
        
        if len(history) < patience:
            return False
        
        # Check if objective value has improved significantly in recent iterations
        recent_objectives = [h['objective'] for h in history[-patience:]]
        improvement = abs(recent_objectives[-1] - recent_objectives[0])
        
        return improvement < self.config.tolerance
    
    def _log_progress(self, iteration: int, best_objective: float, best_parameters: Dict[str, float]):
        """Log optimization progress"""
        self.logger.info(f"Iteration {iteration}: Best objective = {best_objective:.6f}")
        self.logger.debug(f"Best parameters: {best_parameters}")
    
    def get_optimization_summary(self, result: OptimizationResult) -> Dict[str, Any]:
        """Get summary of optimization results"""
        return {
            'converged': result.converged,
            'iterations': result.iterations,
            'best_objective': result.best_objective,
            'best_parameters': result.best_parameters,
            'performance_metrics': result.performance_metrics,
            'validation_metrics': result.validation_metrics,
            'optimization_time': (result.timestamp - datetime.now()).total_seconds()
        }
