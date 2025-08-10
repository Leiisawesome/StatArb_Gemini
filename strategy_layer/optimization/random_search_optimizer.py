"""
Random Search Optimizer

Random search implementation for parameter optimization.

Author: Pro Quant Desk Trader
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple, Callable
import random

from .parameter_optimizer import ParameterOptimizer, OptimizationConfig, OptimizationResult
from strategy_layer.base import StrategyError


class RandomSearchOptimizer(ParameterOptimizer):
    """Random search optimizer for parameter optimization"""
    
    def __init__(self, config: OptimizationConfig):
        super().__init__(config)
        self.search_history: List[Dict[str, Any]] = []
        self._validate_random_config()
    
    def _validate_random_config(self):
        """Validate random search configuration"""
        if self.config.max_iterations <= 0:
            raise StrategyError("Max iterations must be positive for random search")
    
    def optimize(self, objective_function: Callable, initial_parameters: Dict[str, float]) -> OptimizationResult:
        """Optimize parameters using random search"""
        try:
            self.logger.info("Starting random search optimization")
            
            # Optimization history
            history = []
            best_objective = float('-inf')
            best_parameters = initial_parameters.copy()
            
            # Evaluate initial parameters
            try:
                initial_objective = objective_function(initial_parameters)
                best_objective = initial_objective
                self.logger.info(f"Initial objective: {initial_objective:.6f}")
            except Exception as e:
                self.logger.warning(f"Failed to evaluate initial parameters: {e}")
                initial_objective = float('-inf')
            
            # Main optimization loop
            for iteration in range(self.config.max_iterations):
                # Generate random parameters
                random_parameters = self._generate_random_parameters(initial_parameters)
                
                # Evaluate objective function
                try:
                    objective_value = objective_function(random_parameters)
                except Exception as e:
                    self.logger.warning(f"Failed to evaluate parameters: {e}")
                    objective_value = float('-inf')
                
                # Update best
                if objective_value > best_objective:
                    best_objective = objective_value
                    best_parameters = random_parameters.copy()
                    self.logger.info(f"New best found at iteration {iteration}: {best_objective:.6f}")
                
                # Log progress
                if (iteration + 1) % max(1, self.config.max_iterations // 10) == 0:
                    progress = (iteration + 1) / self.config.max_iterations * 100
                    self.logger.info(f"Progress: {progress:.1f}% - Best objective: {best_objective:.6f}")
                
                # Record history
                history.append({
                    'iteration': iteration,
                    'objective': best_objective,
                    'best_parameters': best_parameters.copy(),
                    'current_parameters': random_parameters,
                    'current_objective': objective_value
                })
                
                # Store in search history
                self.search_history.append({
                    'iteration': iteration,
                    'parameters': random_parameters,
                    'objective': objective_value,
                    'improvement': objective_value - initial_objective
                })
            
            # Create result
            result = OptimizationResult(
                best_parameters=best_parameters,
                best_objective=best_objective,
                history=history,
                converged=False,  # Random search doesn't converge in the traditional sense
                iterations=self.config.max_iterations
            )
            
            self.logger.info(f"Random search completed. Best objective: {best_objective:.6f}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in random search optimization: {e}")
            raise StrategyError(f"Random search optimization failed: {e}")
    
    def _generate_random_parameters(self, base_parameters: Dict[str, float]) -> Dict[str, float]:
        """Generate random parameters"""
        parameters = {}
        
        for param_name, base_value in base_parameters.items():
            if param_name in self.config.parameter_bounds:
                min_val, max_val = self.config.parameter_bounds[param_name]
                # Uniform random sampling within bounds
                parameters[param_name] = random.uniform(min_val, max_val)
            else:
                # Use base value with random perturbation
                perturbation = random.uniform(0.5, 1.5)
                parameters[param_name] = base_value * perturbation
        
        return parameters
    
    def _generate_latin_hypercube_parameters(self, base_parameters: Dict[str, float], n_samples: int = 1) -> List[Dict[str, float]]:
        """Generate parameters using Latin Hypercube Sampling"""
        parameters_list = []
        
        for param_name, base_value in base_parameters.items():
            if param_name in self.config.parameter_bounds:
                min_val, max_val = self.config.parameter_bounds[param_name]
                # Generate Latin hypercube samples
                samples = np.random.uniform(min_val, max_val, n_samples)
                parameters_list.append(samples)
            else:
                # Use base value with random perturbation
                perturbation = np.random.uniform(0.5, 1.5, n_samples)
                parameters_list.append(base_value * perturbation)
        
        # Convert to list of dictionaries
        result = []
        for i in range(n_samples):
            param_dict = {}
            for j, param_name in enumerate(base_parameters.keys()):
                param_dict[param_name] = parameters_list[j][i]
            result.append(param_dict)
        
        return result
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """Get statistics about the random search"""
        if not self.search_history:
            return {}
        
        objectives = [record['objective'] for record in self.search_history]
        improvements = [record['improvement'] for record in self.search_history]
        
        return {
            'n_evaluations': len(self.search_history),
            'best_objective': max(objectives) if objectives else float('-inf'),
            'worst_objective': min(objectives) if objectives else float('-inf'),
            'mean_objective': np.mean(objectives) if objectives else 0.0,
            'std_objective': np.std(objectives) if objectives else 0.0,
            'mean_improvement': np.mean(improvements) if improvements else 0.0,
            'positive_improvements': sum(1 for imp in improvements if imp > 0),
            'improvement_rate': sum(1 for imp in improvements if imp > 0) / len(improvements) if improvements else 0.0
        }
    
    def get_parameter_distributions(self) -> Dict[str, Dict[str, float]]:
        """Get parameter value distributions from search history"""
        if not self.search_history:
            return {}
        
        param_names = list(self.search_history[0]['parameters'].keys())
        distributions = {}
        
        for param_name in param_names:
            values = [record['parameters'][param_name] for record in self.search_history]
            
            distributions[param_name] = {
                'mean': np.mean(values),
                'std': np.std(values),
                'min': np.min(values),
                'max': np.max(values),
                'median': np.median(values),
                'q25': np.percentile(values, 25),
                'q75': np.percentile(values, 75)
            }
        
        return distributions
    
    def get_best_parameters_history(self) -> List[Dict[str, Any]]:
        """Get history of best parameters found"""
        if not self.search_history:
            return []
        
        best_history = []
        best_objective = float('-inf')
        
        for record in self.search_history:
            if record['objective'] > best_objective:
                best_objective = record['objective']
                best_history.append({
                    'iteration': record['iteration'],
                    'parameters': record['parameters'],
                    'objective': record['objective']
                })
        
        return best_history
    
    def suggest_parameter_ranges(self, confidence_level: float = 0.95) -> Dict[str, Tuple[float, float]]:
        """Suggest parameter ranges based on search history"""
        if not self.search_history:
            return {}
        
        # Get top performing parameters
        sorted_history = sorted(self.search_history, key=lambda x: x['objective'], reverse=True)
        n_top = max(1, int(len(sorted_history) * (1 - confidence_level)))
        top_performers = sorted_history[:n_top]
        
        param_names = list(top_performers[0]['parameters'].keys())
        suggested_ranges = {}
        
        for param_name in param_names:
            values = [record['parameters'][param_name] for record in top_performers]
            suggested_ranges[param_name] = (np.min(values), np.max(values))
        
        return suggested_ranges
    
    def restart_search(self, new_bounds: Optional[Dict[str, Tuple[float, float]]] = None):
        """Restart search with new parameter bounds"""
        if new_bounds:
            self.config.parameter_bounds.update(new_bounds)
            self.logger.info(f"Updated parameter bounds: {list(new_bounds.keys())}")
        
        self.search_history = []
        self.logger.info("Random search restarted")
    
    def add_custom_parameters(self, parameters_list: List[Dict[str, float]]):
        """Add custom parameter sets to search history"""
        for i, parameters in enumerate(parameters_list):
            self.search_history.append({
                'iteration': len(self.search_history),
                'parameters': parameters,
                'objective': float('-inf'),  # Will be evaluated later
                'improvement': 0.0,
                'custom': True
            })
        
        self.logger.info(f"Added {len(parameters_list)} custom parameter sets")
