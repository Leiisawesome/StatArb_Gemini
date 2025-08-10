"""
Grid Search Optimizer

Grid search implementation for parameter optimization.

Author: Pro Quant Desk Trader
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple, Callable
import itertools

from .parameter_optimizer import ParameterOptimizer, OptimizationConfig, OptimizationResult
from strategy_layer.base import StrategyError


class GridSearchOptimizer(ParameterOptimizer):
    """Grid search optimizer for parameter optimization"""
    
    def __init__(self, config: OptimizationConfig):
        super().__init__(config)
        self.parameter_grid: Dict[str, List[float]] = {}
        self._validate_grid_config()
    
    def _validate_grid_config(self):
        """Validate grid search configuration"""
        if not self.config.parameter_bounds:
            raise StrategyError("Parameter bounds are required for grid search")
        
        # Generate parameter grid from bounds
        self._generate_parameter_grid()
        
        # Check grid size
        total_combinations = 1
        for param_name, values in self.parameter_grid.items():
            total_combinations *= len(values)
        
        if total_combinations > 1000:
            self.logger.warning(f"Large grid size: {total_combinations} combinations")
    
    def _generate_parameter_grid(self):
        """Generate parameter grid from bounds"""
        self.parameter_grid = {}
        
        for param_name, (min_val, max_val) in self.config.parameter_bounds.items():
            # Generate grid points (default: 5 points per parameter)
            n_points = min(5, int((max_val - min_val) / 0.1) + 1)  # Adaptive grid size
            values = np.linspace(min_val, max_val, n_points)
            self.parameter_grid[param_name] = values.tolist()
    
    def set_parameter_grid(self, parameter_grid: Dict[str, List[float]]):
        """Set custom parameter grid"""
        self.parameter_grid = parameter_grid
        self.logger.info(f"Parameter grid set: {list(parameter_grid.keys())}")
    
    def optimize(self, objective_function: Callable, initial_parameters: Dict[str, float]) -> OptimizationResult:
        """Optimize parameters using grid search"""
        try:
            self.logger.info("Starting grid search optimization")
            
            # Generate all parameter combinations
            param_names = list(self.parameter_grid.keys())
            param_values = list(self.parameter_grid.values())
            combinations = list(itertools.product(*param_values))
            
            self.logger.info(f"Grid search: {len(combinations)} combinations to evaluate")
            
            # Optimization history
            history = []
            best_objective = float('-inf')
            best_parameters = initial_parameters.copy()
            
            # Evaluate all combinations
            for i, combination in enumerate(combinations):
                # Create parameter dictionary
                parameters = dict(zip(param_names, combination))
                
                # Add any missing parameters from initial_parameters
                for param_name, value in initial_parameters.items():
                    if param_name not in parameters:
                        parameters[param_name] = value
                
                # Evaluate objective function
                try:
                    objective_value = objective_function(parameters)
                except Exception as e:
                    self.logger.warning(f"Failed to evaluate parameters: {e}")
                    objective_value = float('-inf')
                
                # Update best
                if objective_value > best_objective:
                    best_objective = objective_value
                    best_parameters = parameters.copy()
                
                # Log progress
                if (i + 1) % max(1, len(combinations) // 10) == 0:
                    progress = (i + 1) / len(combinations) * 100
                    self.logger.info(f"Progress: {progress:.1f}% - Best objective: {best_objective:.6f}")
                
                # Record history
                history.append({
                    'iteration': i,
                    'objective': best_objective,
                    'best_parameters': best_parameters.copy(),
                    'current_parameters': parameters,
                    'current_objective': objective_value
                })
            
            # Create result
            result = OptimizationResult(
                best_parameters=best_parameters,
                best_objective=best_objective,
                history=history,
                converged=True,  # Grid search always converges
                iterations=len(combinations)
            )
            
            self.logger.info(f"Grid search completed. Best objective: {best_objective:.6f}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in grid search optimization: {e}")
            raise StrategyError(f"Grid search optimization failed: {e}")
    
    def get_grid_info(self) -> Dict[str, Any]:
        """Get information about the parameter grid"""
        total_combinations = 1
        grid_info = {}
        
        for param_name, values in self.parameter_grid.items():
            total_combinations *= len(values)
            grid_info[param_name] = {
                'n_points': len(values),
                'min_value': min(values),
                'max_value': max(values),
                'step_size': (max(values) - min(values)) / (len(values) - 1) if len(values) > 1 else 0
            }
        
        return {
            'total_combinations': total_combinations,
            'parameter_grid': grid_info,
            'estimated_time': total_combinations * 0.1  # Rough estimate: 0.1 seconds per evaluation
        }
    
    def refine_grid(self, best_parameters: Dict[str, float], refinement_factor: float = 0.5):
        """Refine grid around best parameters"""
        refined_grid = {}
        
        for param_name, best_value in best_parameters.items():
            if param_name in self.parameter_grid:
                current_values = self.parameter_grid[param_name]
                min_val, max_val = min(current_values), max(current_values)
                
                # Calculate refined range around best value
                range_val = max_val - min_val
                refined_range = range_val * refinement_factor
                
                new_min = max(min_val, best_value - refined_range / 2)
                new_max = min(max_val, best_value + refined_range / 2)
                
                # Generate refined grid
                n_points = len(current_values)
                refined_values = np.linspace(new_min, new_max, n_points)
                refined_grid[param_name] = refined_values.tolist()
            else:
                refined_grid[param_name] = [best_value]
        
        self.parameter_grid = refined_grid
        self.logger.info(f"Grid refined around best parameters. New grid size: {self.get_grid_info()['total_combinations']}")
    
    def add_parameter_points(self, param_name: str, additional_points: List[float]):
        """Add additional points to parameter grid"""
        if param_name not in self.parameter_grid:
            self.parameter_grid[param_name] = []
        
        # Add new points and remove duplicates
        all_points = self.parameter_grid[param_name] + additional_points
        self.parameter_grid[param_name] = sorted(list(set(all_points)))
        
        self.logger.info(f"Added {len(additional_points)} points to parameter {param_name}")
    
    def remove_parameter_points(self, param_name: str, points_to_remove: List[float]):
        """Remove specific points from parameter grid"""
        if param_name in self.parameter_grid:
            original_points = self.parameter_grid[param_name]
            filtered_points = [p for p in original_points if p not in points_to_remove]
            self.parameter_grid[param_name] = filtered_points
            
            self.logger.info(f"Removed {len(original_points) - len(filtered_points)} points from parameter {param_name}")
    
    def get_parameter_importance(self, history: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate parameter importance based on optimization history"""
        if not history:
            return {}
        
        param_names = list(self.parameter_grid.keys())
        importance_scores = {}
        
        for param_name in param_names:
            # Calculate correlation between parameter values and objective values
            param_values = []
            objective_values = []
            
            for record in history:
                if 'current_parameters' in record and 'current_objective' in record:
                    param_values.append(record['current_parameters'].get(param_name, 0))
                    objective_values.append(record['current_objective'])
            
            if len(param_values) > 1:
                # Calculate correlation coefficient
                correlation = np.corrcoef(param_values, objective_values)[0, 1]
                importance_scores[param_name] = abs(correlation) if not np.isnan(correlation) else 0.0
            else:
                importance_scores[param_name] = 0.0
        
        return importance_scores
