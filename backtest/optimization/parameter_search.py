"""
Parameter Search Engine

Advanced parameter search algorithms for strategy optimization.

Features:
- Grid search (exhaustive)
- Random search (sampling)
- Bayesian optimization (efficient)
- Search space validation
"""

import logging
from typing import Dict, Any, List, Callable, Optional, Tuple
import itertools
import numpy as np
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class SearchSpace:
    """Parameter search space definition"""
    parameters: Dict[str, List[Any]]
    
    def get_size(self) -> int:
        """Calculate total number of combinations"""
        size = 1
        for values in self.parameters.values():
            size *= len(values)
        return size
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate search space"""
        if not self.parameters:
            return False, "Search space is empty"
        
        for param_name, values in self.parameters.items():
            if not values:
                return False, f"Parameter '{param_name}' has no values"
            
            if not isinstance(values, list):
                return False, f"Parameter '{param_name}' values must be a list"
        
        return True, None


class ParameterSearchEngine:
    """
    Advanced parameter search algorithms.
    
    Supports multiple search strategies for finding optimal parameters.
    """
    
    def __init__(self):
        """Initialize parameter search engine"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("ParameterSearchEngine initialized")
    
    def grid_search(
        self,
        search_space: SearchSpace,
        objective_function: Callable[[Dict[str, Any]], float],
        maximize: bool = True
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Exhaustive grid search.
        
        Tests all possible parameter combinations.
        
        Args:
            search_space: Parameter search space
            objective_function: Function to optimize (returns score)
            maximize: Whether to maximize (True) or minimize (False)
        
        Returns:
            List of (parameters, score) tuples sorted by score
        """
        # Validate search space
        is_valid, error_msg = search_space.validate()
        if not is_valid:
            self.logger.error(f"Invalid search space: {error_msg}")
            return []
        
        # Generate all combinations
        combinations = self._generate_combinations(search_space)
        total = len(combinations)
        
        self.logger.info(f"Grid search: testing {total} combinations")
        
        # Evaluate each combination
        results = []
        for i, params in enumerate(combinations, 1):
            try:
                score = objective_function(params)
                results.append((params, score))
                
                # Log progress
                if i % max(1, total // 10) == 0:
                    self.logger.info(f"Progress: {i}/{total} ({i/total*100:.1f}%)")
                    
            except Exception as e:
                self.logger.error(f"Evaluation failed for combination {i}: {e}")
        
        # Sort results
        results.sort(key=lambda x: x[1], reverse=maximize)
        
        self.logger.info(f"Grid search complete: {len(results)} valid results")
        
        return results
    
    def random_search(
        self,
        search_space: SearchSpace,
        objective_function: Callable[[Dict[str, Any]], float],
        n_iterations: int = 100,
        maximize: bool = True,
        seed: Optional[int] = None
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Random search sampling.
        
        Randomly samples parameter combinations.
        
        Args:
            search_space: Parameter search space
            objective_function: Function to optimize
            n_iterations: Number of random samples
            maximize: Whether to maximize or minimize
            seed: Random seed for reproducibility
        
        Returns:
            List of (parameters, score) tuples sorted by score
        """
        # Validate search space
        is_valid, error_msg = search_space.validate()
        if not is_valid:
            self.logger.error(f"Invalid search space: {error_msg}")
            return []
        
        if seed is not None:
            np.random.seed(seed)
        
        self.logger.info(f"Random search: {n_iterations} iterations")
        
        # Generate random combinations
        results = []
        for i in range(n_iterations):
            try:
                # Sample random parameters
                params = self._sample_random_parameters(search_space)
                
                # Evaluate
                score = objective_function(params)
                results.append((params, score))
                
                # Log progress
                if (i + 1) % max(1, n_iterations // 10) == 0:
                    self.logger.info(f"Progress: {i+1}/{n_iterations} ({(i+1)/n_iterations*100:.1f}%)")
                    
            except Exception as e:
                self.logger.error(f"Evaluation failed for iteration {i+1}: {e}")
        
        # Sort results
        results.sort(key=lambda x: x[1], reverse=maximize)
        
        self.logger.info(f"Random search complete: {len(results)} valid results")
        
        return results
    
    def bayesian_optimization(
        self,
        search_space: SearchSpace,
        objective_function: Callable[[Dict[str, Any]], float],
        n_iterations: int = 50,
        n_initial_points: int = 10,
        maximize: bool = True
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Bayesian optimization (simplified implementation).
        
        Uses past evaluations to guide search toward promising regions.
        
        Note: This is a simplified implementation. For production use,
        consider libraries like scikit-optimize or Optuna.
        
        Args:
            search_space: Parameter search space
            objective_function: Function to optimize
            n_iterations: Number of optimization iterations
            n_initial_points: Number of random initial points
            maximize: Whether to maximize or minimize
        
        Returns:
            List of (parameters, score) tuples sorted by score
        """
        # Validate search space
        is_valid, error_msg = search_space.validate()
        if not is_valid:
            self.logger.error(f"Invalid search space: {error_msg}")
            return []
        
        self.logger.info(
            f"Bayesian optimization: {n_iterations} iterations "
            f"({n_initial_points} initial points)"
        )
        
        results = []
        
        # Phase 1: Random initialization
        self.logger.info("Phase 1: Random initialization")
        for i in range(n_initial_points):
            try:
                params = self._sample_random_parameters(search_space)
                score = objective_function(params)
                results.append((params, score))
                
            except Exception as e:
                self.logger.error(f"Initial evaluation {i+1} failed: {e}")
        
        # Phase 2: Bayesian optimization iterations
        self.logger.info("Phase 2: Bayesian optimization")
        for i in range(n_iterations - n_initial_points):
            try:
                # Select next point based on past results
                # Simplified: sample near best results with some exploration
                if results:
                    # Get top 3 results
                    top_results = sorted(results, key=lambda x: x[1], reverse=maximize)[:3]
                    
                    # Sample near one of the top results
                    base_params, _ = top_results[np.random.randint(0, len(top_results))]
                    params = self._perturb_parameters(search_space, base_params)
                else:
                    # Fallback to random
                    params = self._sample_random_parameters(search_space)
                
                # Evaluate
                score = objective_function(params)
                results.append((params, score))
                
                # Log progress
                total = n_initial_points + i + 1
                if total % max(1, n_iterations // 10) == 0:
                    self.logger.info(f"Progress: {total}/{n_iterations} ({total/n_iterations*100:.1f}%)")
                    
            except Exception as e:
                self.logger.error(f"Bayesian iteration {i+1} failed: {e}")
        
        # Sort results
        results.sort(key=lambda x: x[1], reverse=maximize)
        
        self.logger.info(f"Bayesian optimization complete: {len(results)} valid results")
        
        return results
    
    def _generate_combinations(self, search_space: SearchSpace) -> List[Dict[str, Any]]:
        """Generate all parameter combinations for grid search"""
        param_names = list(search_space.parameters.keys())
        param_values = [search_space.parameters[name] for name in param_names]
        
        combinations = []
        for combo in itertools.product(*param_values):
            param_dict = dict(zip(param_names, combo))
            combinations.append(param_dict)
        
        return combinations
    
    def _sample_random_parameters(self, search_space: SearchSpace) -> Dict[str, Any]:
        """Sample random parameters from search space"""
        params = {}
        for param_name, values in search_space.parameters.items():
            params[param_name] = np.random.choice(values)
        return params
    
    def _perturb_parameters(
        self,
        search_space: SearchSpace,
        base_params: Dict[str, Any],
        perturbation_prob: float = 0.3
    ) -> Dict[str, Any]:
        """
        Perturb parameters for Bayesian optimization.
        
        With some probability, change each parameter to a nearby value.
        
        Args:
            search_space: Search space
            base_params: Base parameters to perturb
            perturbation_prob: Probability of perturbing each parameter
        
        Returns:
            Perturbed parameters
        """
        perturbed = base_params.copy()
        
        for param_name, values in search_space.parameters.items():
            if np.random.random() < perturbation_prob:
                # Find current value index
                current_value = base_params.get(param_name, values[0])
                try:
                    current_idx = values.index(current_value)
                except ValueError:
                    current_idx = 0
                
                # Select nearby index
                max_offset = min(2, len(values) - 1)
                offset = np.random.randint(-max_offset, max_offset + 1)
                new_idx = np.clip(current_idx + offset, 0, len(values) - 1)
                
                perturbed[param_name] = values[new_idx]
        
        return perturbed
    
    def estimate_search_time(
        self,
        search_space: SearchSpace,
        evaluation_time_seconds: float,
        method: str = "grid_search",
        n_iterations: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Estimate time required for parameter search.
        
        Args:
            search_space: Search space
            evaluation_time_seconds: Time per evaluation
            method: Search method
            n_iterations: Iterations (for random/Bayesian)
        
        Returns:
            Time estimate dictionary
        """
        if method == "grid_search":
            n_evaluations = search_space.get_size()
        elif method in ["random_search", "bayesian"]:
            if n_iterations is None:
                n_evaluations = 100  # Default
            else:
                n_evaluations = n_iterations
        else:
            return {'error': f'Unknown method: {method}'}
        
        total_seconds = n_evaluations * evaluation_time_seconds
        hours = total_seconds / 3600
        
        return {
            'method': method,
            'n_evaluations': n_evaluations,
            'evaluation_time_seconds': evaluation_time_seconds,
            'total_seconds': total_seconds,
            'total_hours': hours,
            'total_minutes': total_seconds / 60,
            'search_space_size': search_space.get_size()
        }

