"""
Bayesian Optimizer

Bayesian optimization implementation for parameter optimization.

Author: Pro Quant Desk Trader
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass
import random

from .parameter_optimizer import ParameterOptimizer, OptimizationConfig, OptimizationResult
from strategy_layer.base import StrategyError


@dataclass
class Observation:
    """Observation in Bayesian optimization"""
    parameters: Dict[str, float]
    objective: float
    timestamp: float


class BayesianOptimizer(ParameterOptimizer):
    """Bayesian optimization for parameter optimization"""
    
    def __init__(self, config: OptimizationConfig):
        super().__init__(config)
        self.observations: List[Observation] = []
        self.acquisition_function = 'ucb'  # Upper Confidence Bound
        self.kernel_length_scale = 1.0
    
    def optimize(self, objective_function: Callable, initial_parameters: Dict[str, float]) -> OptimizationResult:
        """Optimize parameters using Bayesian optimization"""
        try:
            self.logger.info("Starting Bayesian optimization")
            
            # Initialize with random points
            self._initialize_observations(objective_function, initial_parameters)
            
            # Optimization history
            history = []
            best_objective = float('-inf')
            best_parameters = initial_parameters.copy()
            
            # Main optimization loop
            for iteration in range(self.config.max_iterations):
                # Find next point to evaluate
                next_parameters = self._suggest_next_point()
                
                # Evaluate objective function
                try:
                    objective_value = objective_function(next_parameters)
                    # Ensure we have a valid number
                    if objective_value is None:
                        objective_value = float('-inf')
                    else:
                        objective_value = float(objective_value)
                except Exception as e:
                    self.logger.warning(f"Failed to evaluate parameters: {e}")
                    objective_value = float('-inf')
                
                # Add observation
                observation = Observation(
                    parameters=next_parameters,
                    objective=objective_value,
                    timestamp=iteration
                )
                self.observations.append(observation)
                
                # Update best
                if objective_value is not None and not np.isnan(objective_value) and objective_value > best_objective:
                    best_objective = objective_value
                    best_parameters = next_parameters.copy()
                
                # Log progress
                self._log_progress(iteration, best_objective, best_parameters)
                
                # Record history
                history.append({
                    'iteration': iteration,
                    'objective': best_objective,
                    'best_parameters': best_parameters.copy(),
                    'next_parameters': next_parameters,
                    'next_objective': objective_value
                })
                
                # Check convergence
                if self._check_convergence(history):
                    self.logger.info(f"Optimization converged at iteration {iteration}")
                    break
            
            # Create result
            result = OptimizationResult(
                best_parameters=best_parameters,
                best_objective=best_objective,
                history=history,
                converged=self._check_convergence(history),
                iterations=len(history)
            )
            
            self.logger.info(f"Bayesian optimization completed. Best objective: {best_objective:.6f}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in Bayesian optimization: {e}")
            raise StrategyError(f"Bayesian optimization failed: {e}")
    
    def _initialize_observations(self, objective_function: Callable, initial_parameters: Dict[str, float]):
        """Initialize observations with random points"""
        self.observations = []
        
        # Add initial point
        try:
            initial_objective = objective_function(initial_parameters)
            # Ensure we have a valid number
            if initial_objective is None:
                initial_objective = float('-inf')
            else:
                initial_objective = float(initial_objective)
            self.observations.append(Observation(
                parameters=initial_parameters,
                objective=initial_objective,
                timestamp=0
            ))
        except Exception as e:
            self.logger.warning(f"Failed to evaluate initial parameters: {e}")
            self.observations.append(Observation(
                parameters=initial_parameters,
                objective=float('-inf'),
                timestamp=0
            ))
        
        # Add random points
        n_random = min(5, self.config.max_iterations // 4)
        for i in range(n_random):
            random_params = self._generate_random_parameters(initial_parameters)
            try:
                objective_value = objective_function(random_params)
                # Ensure we have a valid number
                if objective_value is None:
                    objective_value = float('-inf')
                else:
                    objective_value = float(objective_value)
            except Exception as e:
                self.logger.warning(f"Failed to evaluate random parameters: {e}")
                objective_value = float('-inf')
            
            self.observations.append(Observation(
                parameters=random_params,
                objective=objective_value,
                timestamp=i + 1
            ))
    
    def _generate_random_parameters(self, base_parameters: Dict[str, float]) -> Dict[str, float]:
        """Generate random parameters within bounds"""
        parameters = {}
        
        for param_name, base_value in base_parameters.items():
            if param_name in self.config.parameter_bounds:
                min_val, max_val = self.config.parameter_bounds[param_name]
                parameters[param_name] = random.uniform(min_val, max_val)
            else:
                # Use base value with random perturbation
                perturbation = random.uniform(0.5, 1.5)
                parameters[param_name] = base_value * perturbation
        
        return parameters
    
    def _suggest_next_point(self) -> Dict[str, float]:
        """Suggest next point to evaluate using acquisition function"""
        if len(self.observations) < 2:
            # Not enough observations, generate random point
            return self._generate_random_parameters(self.observations[0].parameters)
        
        # Convert observations to arrays for optimization
        param_names = list(self.observations[0].parameters.keys())
        X = np.array([[obs.parameters[name] for name in param_names] for obs in self.observations])
        y = np.array([obs.objective if obs.objective is not None and not np.isnan(obs.objective) else float('-inf') for obs in self.observations])
        
        # Simple acquisition function: Upper Confidence Bound
        best_candidates = self._generate_candidates(param_names)
        
        best_acquisition = float('-inf')
        best_candidate = None
        
        for candidate in best_candidates:
            acquisition_value = self._acquisition_function(candidate, X, y, param_names)
            if acquisition_value > best_acquisition:
                best_acquisition = acquisition_value
                best_candidate = candidate
        
        if best_candidate is None:
            # Fallback to random generation
            return self._generate_random_parameters(self.observations[0].parameters)
        
        # Convert back to dictionary
        return {name: value for name, value in zip(param_names, best_candidate)}
    
    def _generate_candidates(self, param_names: List[str], n_candidates: int = 100) -> List[np.ndarray]:
        """Generate candidate points for acquisition function optimization"""
        candidates = []
        
        for _ in range(n_candidates):
            candidate = []
            for param_name in param_names:
                if param_name in self.config.parameter_bounds:
                    min_val, max_val = self.config.parameter_bounds[param_name]
                    candidate.append(random.uniform(min_val, max_val))
                else:
                    # Use range based on observed values
                    values = [obs.parameters[param_name] for obs in self.observations]
                    min_val, max_val = min(values), max(values)
                    range_val = max_val - min_val
                    candidate.append(random.uniform(min_val - range_val * 0.1, max_val + range_val * 0.1))
            
            candidates.append(np.array(candidate))
        
        return candidates
    
    def _acquisition_function(self, candidate: np.ndarray, X: np.ndarray, y: np.ndarray, param_names: List[str]) -> float:
        """Calculate acquisition function value for a candidate point"""
        if self.acquisition_function == 'ucb':
            return self._upper_confidence_bound(candidate, X, y)
        elif self.acquisition_function == 'ei':
            return self._expected_improvement(candidate, X, y)
        else:
            return self._probability_improvement(candidate, X, y)
    
    def _upper_confidence_bound(self, candidate: np.ndarray, X: np.ndarray, y: np.ndarray) -> float:
        """Upper Confidence Bound acquisition function"""
        # Simple implementation using distance-based surrogate
        distances = np.linalg.norm(X - candidate, axis=1)
        weights = np.exp(-distances / self.kernel_length_scale)
        
        if np.sum(weights) == 0:
            return 0.0
        
        # Mean prediction
        mean_pred = np.sum(weights * y) / np.sum(weights)
        
        # Uncertainty (inverse of weight sum)
        uncertainty = 1.0 / (1.0 + np.sum(weights))
        
        # UCB = mean + exploration_weight * uncertainty
        exploration_weight = 2.0
        return mean_pred + exploration_weight * uncertainty
    
    def _expected_improvement(self, candidate: np.ndarray, X: np.ndarray, y: np.ndarray) -> float:
        """Expected Improvement acquisition function"""
        best_observed = np.max(y)
        
        # Simple surrogate prediction
        distances = np.linalg.norm(X - candidate, axis=1)
        weights = np.exp(-distances / self.kernel_length_scale)
        
        if np.sum(weights) == 0:
            return 0.0
        
        mean_pred = np.sum(weights * y) / np.sum(weights)
        
        # Simple uncertainty estimate
        uncertainty = 1.0 / (1.0 + np.sum(weights))
        
        # Expected improvement
        improvement = mean_pred - best_observed
        if improvement > 0:
            return improvement + uncertainty
        else:
            return uncertainty * 0.1  # Small exploration bonus
    
    def _probability_improvement(self, candidate: np.ndarray, X: np.ndarray, y: np.ndarray) -> float:
        """Probability of Improvement acquisition function"""
        best_observed = np.max(y)
        
        # Simple surrogate prediction
        distances = np.linalg.norm(X - candidate, axis=1)
        weights = np.exp(-distances / self.kernel_length_scale)
        
        if np.sum(weights) == 0:
            return 0.0
        
        mean_pred = np.sum(weights * y) / np.sum(weights)
        uncertainty = 1.0 / (1.0 + np.sum(weights))
        
        # Probability of improvement (simplified)
        if uncertainty > 0:
            z_score = (mean_pred - best_observed) / uncertainty
            # Approximate probability using normal distribution
            prob_improvement = 0.5 * (1 + np.tanh(z_score))
            return prob_improvement
        else:
            return 0.5  # Neutral probability
    
    def get_surrogate_model(self) -> Dict[str, Any]:
        """Get current surrogate model information"""
        if len(self.observations) < 2:
            return {'status': 'insufficient_data'}
        
        param_names = list(self.observations[0].parameters.keys())
        X = np.array([[obs.parameters[name] for name in param_names] for obs in self.observations])
        y = np.array([obs.objective if obs.objective is not None and not np.isnan(obs.objective) else float('-inf') for obs in self.observations])
        
        return {
            'n_observations': len(self.observations),
            'best_objective': np.max(y),
            'mean_objective': np.mean(y),
            'std_objective': np.std(y),
            'parameter_names': param_names,
            'acquisition_function': self.acquisition_function
        }
    
    def set_acquisition_function(self, acquisition_function: str):
        """Set acquisition function type"""
        valid_functions = ['ucb', 'ei', 'pi']
        if acquisition_function not in valid_functions:
            raise StrategyError(f"Invalid acquisition function. Must be one of: {valid_functions}")
        
        self.acquisition_function = acquisition_function
        self.logger.info(f"Acquisition function set to: {acquisition_function}")
    
    def set_kernel_length_scale(self, length_scale: float):
        """Set kernel length scale for surrogate model"""
        if length_scale <= 0:
            raise StrategyError("Kernel length scale must be positive")
        
        self.kernel_length_scale = length_scale
        self.logger.info(f"Kernel length scale set to: {length_scale}")
