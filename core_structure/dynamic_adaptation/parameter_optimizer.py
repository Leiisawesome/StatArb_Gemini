"""
Parameter Optimizer - Template-Aware Parameter Optimization
==========================================================

Template-aware parameter optimization with inheritance bounds and category-specific optimization.
Provides intelligent parameter tuning within template constraints.

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple, Callable
import scipy.optimize as scipy_opt
from collections import defaultdict

from strategy_templates.base import TemplateRegistry, TemplateCategory, TemplateInheritanceManager


class OptimizationMethod(Enum):
    """Optimization algorithms available"""
    GRID_SEARCH = "grid_search"
    RANDOM_SEARCH = "random_search"
    BAYESIAN = "bayesian"
    GENETIC = "genetic"
    GRADIENT_DESCENT = "gradient_descent"
    SIMULATED_ANNEALING = "simulated_annealing"
    PARTICLE_SWARM = "particle_swarm"


class ParameterBounds(Enum):
    """Types of parameter bounds"""
    HARD_BOUNDS = "hard_bounds"      # Cannot be violated
    SOFT_BOUNDS = "soft_bounds"      # Can be violated with penalty
    ADAPTIVE_BOUNDS = "adaptive_bounds"  # Bounds adapt based on performance
    TEMPLATE_BOUNDS = "template_bounds"  # Bounds from template inheritance


@dataclass
class OptimizationConfig:
    """Configuration for parameter optimization"""
    # Optimization method settings
    primary_method: OptimizationMethod = OptimizationMethod.BAYESIAN
    fallback_method: OptimizationMethod = OptimizationMethod.RANDOM_SEARCH
    max_iterations: int = 100
    convergence_tolerance: float = 1e-6
    
    # Template category optimization settings
    category_optimization_intensity: Dict[TemplateCategory, float] = field(default_factory=lambda: {
        TemplateCategory.BASE: 0.5,      # Conservative optimization
        TemplateCategory.SPECIFIC: 0.8,  # Standard optimization
        TemplateCategory.COMPOSITE: 1.0  # Aggressive optimization
    })
    
    # Bounds and constraints
    parameter_bounds_type: ParameterBounds = ParameterBounds.TEMPLATE_BOUNDS
    safety_margin: float = 0.1  # 10% safety margin from hard bounds
    adaptive_bounds_factor: float = 0.8  # Factor for adaptive bounds adjustment
    
    # Performance criteria
    objective_weights: Dict[str, float] = field(default_factory=lambda: {
        'sharpe_ratio': 0.30,
        'total_return': 0.25,
        'max_drawdown': -0.20,  # Negative weight (minimize)
        'volatility': -0.15,    # Negative weight (minimize)
        'win_rate': 0.10
    })
    
    # Optimization constraints
    max_parameter_change_per_iteration: float = 0.1  # 10% max change
    min_improvement_threshold: float = 0.01  # 1% minimum improvement
    stability_check_periods: int = 5  # Periods to check for stability


@dataclass
class OptimizationResult:
    """Result of parameter optimization"""
    success: bool
    optimal_parameters: Dict[str, Any]
    optimization_score: float
    improvement_percentage: float
    method_used: OptimizationMethod
    iterations_used: int
    convergence_achieved: bool
    template_bounds_respected: bool
    execution_time_seconds: float
    confidence_score: float
    error_message: Optional[str] = None
    optimization_history: List[Dict[str, Any]] = field(default_factory=list)


class ParameterOptimizer:
    """
    Template-aware parameter optimization with inheritance bounds
    """
    
    def __init__(self, 
                 template_registry: TemplateRegistry,
                 config: Optional[OptimizationConfig] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.template_registry = template_registry
        self.config = config or OptimizationConfig()
        
        # Initialize components
        self.inheritance_manager = TemplateInheritanceManager(template_registry)
        
        # Optimization state
        self.current_template_id: Optional[str] = None
        self.current_template_category: Optional[TemplateCategory] = None
        self.template_bounds: Dict[str, Tuple[float, float]] = {}
        self.optimization_history: List[OptimizationResult] = []
        
        # Performance tracking
        self.objective_function: Optional[Callable] = None
        self.best_parameters: Dict[str, Any] = {}
        self.best_score: float = float('-inf')
        
        self.logger.info("Parameter Optimizer initialized")
    
    def initialize_for_template(self, template_id: str, objective_function: Callable):
        """Initialize optimizer for a specific template"""
        try:
            template = self.template_registry.get_template(template_id)
            if not template:
                raise ValueError(f"Template {template_id} not found")
            
            self.current_template_id = template_id
            self.current_template_category = template.metadata.category
            self.objective_function = objective_function
            
            # Calculate template bounds from inheritance chain
            self.template_bounds = self._calculate_template_bounds(template_id)
            
            # Reset optimization state
            self.best_parameters.clear()
            self.best_score = float('-inf')
            
            self.logger.info(f"Parameter optimizer initialized for template {template_id} (category: {self.current_template_category.value})")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize parameter optimizer: {e}")
            raise
    
    async def optimize_parameters(self, 
                                 current_parameters: Dict[str, Any],
                                 market_data: Dict[str, Any],
                                 performance_metrics: Dict[str, float]) -> OptimizationResult:
        """
        Optimize parameters based on current conditions and performance
        """
        try:
            if not self.current_template_id or not self.objective_function:
                raise ValueError("Optimizer not initialized for template")
            
            start_time = datetime.now()
            
            # Prepare optimization context
            optimization_context = {
                'market_data': market_data,
                'performance_metrics': performance_metrics,
                'template_category': self.current_template_category,
                'template_bounds': self.template_bounds
            }
            
            # Select optimization method based on template category
            method = self._select_optimization_method()
            
            # Execute optimization
            result = await self._execute_optimization(
                current_parameters, optimization_context, method
            )
            
            # Post-process results
            result.execution_time_seconds = (datetime.now() - start_time).total_seconds()
            result.confidence_score = self._calculate_confidence_score(result)
            
            # Record in history
            self.optimization_history.append(result)
            
            # Update best parameters if improved
            if result.success and result.optimization_score > self.best_score:
                self.best_parameters = result.optimal_parameters.copy()
                self.best_score = result.optimization_score
            
            self.logger.info(f"Parameter optimization completed: {method.value}, score: {result.optimization_score:.4f}")
            return result
            
        except Exception as e:
            error_msg = f"Parameter optimization failed: {e}"
            self.logger.error(error_msg)
            
            return OptimizationResult(
                success=False,
                optimal_parameters=current_parameters,
                optimization_score=0.0,
                improvement_percentage=0.0,
                method_used=self.config.primary_method,
                iterations_used=0,
                convergence_achieved=False,
                template_bounds_respected=False,
                execution_time_seconds=0.0,
                confidence_score=0.0,
                error_message=error_msg
            )
    
    def get_optimization_recommendations(self, 
                                       current_parameters: Dict[str, Any],
                                       performance_metrics: Dict[str, float]) -> Dict[str, Any]:
        """Get specific optimization recommendations"""
        if not self.current_template_category:
            return {}
        
        recommendations = {
            'template_category': self.current_template_category.value,
            'current_performance_score': self._calculate_performance_score(performance_metrics),
            'parameter_analysis': self._analyze_parameters(current_parameters),
            'optimization_suggestions': self._generate_optimization_suggestions(current_parameters, performance_metrics),
            'risk_assessment': self._assess_optimization_risk(current_parameters),
            'expected_improvement': self._estimate_improvement_potential(current_parameters, performance_metrics)
        }
        
        return recommendations
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """Get comprehensive optimization summary"""
        if not self.optimization_history:
            return {
                'total_optimizations': 0,
                'success_rate': 0.0,
                'average_improvement': 0.0,
                'best_score': 0.0,
                'optimization_trend': 'no_data'
            }
        
        successful_optimizations = [r for r in self.optimization_history if r.success]
        
        return {
            'total_optimizations': len(self.optimization_history),
            'success_rate': len(successful_optimizations) / len(self.optimization_history),
            'average_improvement': np.mean([r.improvement_percentage for r in successful_optimizations]) if successful_optimizations else 0.0,
            'best_score': self.best_score,
            'best_parameters': self.best_parameters.copy(),
            'optimization_trend': self._analyze_optimization_trend(),
            'method_performance': self._analyze_method_performance(),
            'convergence_statistics': self._analyze_convergence_statistics()
        }
    
    # Private helper methods
    def _calculate_template_bounds(self, template_id: str) -> Dict[str, Tuple[float, float]]:
        """Calculate parameter bounds from template inheritance chain"""
        try:
            # Get inheritance chain
            inheritance_chain = self.inheritance_manager.get_inheritance_chain(template_id)
            
            # Default bounds for common parameters
            default_bounds = {
                'signal_threshold': (0.1, 1.0),
                'max_position_size': (0.01, 0.5),
                'risk_per_trade': (0.005, 0.05),
                'stop_loss_pct': (0.01, 0.30),
                'take_profit_pct': (0.05, 1.0),
                'rsi_period': (5, 50),
                'rsi_oversold': (10, 40),
                'rsi_overbought': (60, 90),
                'macd_fast': (5, 20),
                'macd_slow': (20, 50),
                'macd_signal': (5, 15)
            }
            
            # Apply template category adjustments
            category_adjustments = {
                TemplateCategory.BASE: 0.8,      # More conservative bounds
                TemplateCategory.SPECIFIC: 1.0,  # Standard bounds
                TemplateCategory.COMPOSITE: 1.2  # More flexible bounds
            }
            
            adjustment_factor = category_adjustments.get(self.current_template_category, 1.0)
            
            # Adjust bounds based on template category
            adjusted_bounds = {}
            for param, (min_val, max_val) in default_bounds.items():
                range_size = max_val - min_val
                center = (min_val + max_val) / 2
                
                new_range_size = range_size * adjustment_factor
                new_min = max(0, center - new_range_size / 2)
                new_max = center + new_range_size / 2
                
                adjusted_bounds[param] = (new_min, new_max)
            
            return adjusted_bounds
            
        except Exception as e:
            self.logger.error(f"Error calculating template bounds: {e}")
            return {}
    
    def _select_optimization_method(self) -> OptimizationMethod:
        """Select optimization method based on template category and context"""
        # Category-specific method preferences
        category_methods = {
            TemplateCategory.BASE: [OptimizationMethod.GRID_SEARCH, OptimizationMethod.BAYESIAN],
            TemplateCategory.SPECIFIC: [OptimizationMethod.BAYESIAN, OptimizationMethod.GENETIC],
            TemplateCategory.COMPOSITE: [OptimizationMethod.GENETIC, OptimizationMethod.PARTICLE_SWARM]
        }
        
        preferred_methods = category_methods.get(self.current_template_category, [self.config.primary_method])
        
        # Select based on optimization history performance
        if len(self.optimization_history) > 5:
            method_performance = self._analyze_method_performance()
            best_performing_method = max(method_performance.items(), key=lambda x: x[1]['avg_score'])[0]
            
            # Use best performing method if it's in preferred methods
            if OptimizationMethod(best_performing_method) in preferred_methods:
                return OptimizationMethod(best_performing_method)
        
        # Default to first preferred method
        return preferred_methods[0] if preferred_methods else self.config.primary_method
    
    async def _execute_optimization(self, 
                                   current_parameters: Dict[str, Any],
                                   context: Dict[str, Any],
                                   method: OptimizationMethod) -> OptimizationResult:
        """Execute optimization using specified method"""
        
        # Get optimizable parameters (only those with bounds)
        optimizable_params = {k: v for k, v in current_parameters.items() if k in self.template_bounds}
        
        if not optimizable_params:
            return OptimizationResult(
                success=False,
                optimal_parameters=current_parameters,
                optimization_score=0.0,
                improvement_percentage=0.0,
                method_used=method,
                iterations_used=0,
                convergence_achieved=False,
                template_bounds_respected=True,
                execution_time_seconds=0.0,
                confidence_score=0.0,
                error_message="No optimizable parameters found"
            )
        
        try:
            if method == OptimizationMethod.BAYESIAN:
                return await self._bayesian_optimization(optimizable_params, context)
            elif method == OptimizationMethod.GENETIC:
                return await self._genetic_optimization(optimizable_params, context)
            elif method == OptimizationMethod.GRID_SEARCH:
                return await self._grid_search_optimization(optimizable_params, context)
            elif method == OptimizationMethod.RANDOM_SEARCH:
                return await self._random_search_optimization(optimizable_params, context)
            else:
                # Fallback to random search
                return await self._random_search_optimization(optimizable_params, context)
                
        except Exception as e:
            self.logger.error(f"Optimization method {method.value} failed: {e}")
            # Try fallback method
            if method != self.config.fallback_method:
                return await self._execute_optimization(current_parameters, context, self.config.fallback_method)
            else:
                raise
    
    async def _bayesian_optimization(self, 
                                   parameters: Dict[str, Any],
                                   context: Dict[str, Any]) -> OptimizationResult:
        """Bayesian optimization implementation"""
        
        # Simplified Bayesian optimization using random sampling with Gaussian process approximation
        best_params = parameters.copy()
        best_score = await self._evaluate_parameters(best_params, context)
        initial_score = best_score
        
        iterations = min(self.config.max_iterations, 50)  # Limit for Bayesian
        evaluation_history = []
        
        for iteration in range(iterations):
            # Generate candidate parameters using exploration-exploitation balance
            candidate_params = self._generate_bayesian_candidate(parameters, evaluation_history)
            
            # Evaluate candidate
            candidate_score = await self._evaluate_parameters(candidate_params, context)
            evaluation_history.append((candidate_params.copy(), candidate_score))
            
            # Update best if improved
            if candidate_score > best_score:
                best_params = candidate_params.copy()
                best_score = candidate_score
            
            # Check convergence
            if len(evaluation_history) > 5:
                recent_scores = [score for _, score in evaluation_history[-5:]]
                if np.std(recent_scores) < self.config.convergence_tolerance:
                    break
        
        improvement = ((best_score - initial_score) / abs(initial_score)) * 100 if initial_score != 0 else 0
        
        return OptimizationResult(
            success=best_score > initial_score,
            optimal_parameters={**parameters, **best_params},
            optimization_score=best_score,
            improvement_percentage=improvement,
            method_used=OptimizationMethod.BAYESIAN,
            iterations_used=len(evaluation_history),
            convergence_achieved=len(evaluation_history) < iterations,
            template_bounds_respected=self._check_bounds_compliance(best_params),
            execution_time_seconds=0.0,
            confidence_score=0.0,
            optimization_history=evaluation_history
        )
    
    async def _genetic_optimization(self, 
                                  parameters: Dict[str, Any],
                                  context: Dict[str, Any]) -> OptimizationResult:
        """Genetic algorithm optimization implementation"""
        
        population_size = 20
        generations = min(self.config.max_iterations // population_size, 10)
        mutation_rate = 0.1
        crossover_rate = 0.8
        
        # Initialize population
        population = []
        for _ in range(population_size):
            individual = self._generate_random_parameters(parameters)
            score = await self._evaluate_parameters(individual, context)
            population.append((individual, score))
        
        best_individual = max(population, key=lambda x: x[1])
        initial_score = await self._evaluate_parameters(parameters, context)
        
        for generation in range(generations):
            # Selection (tournament selection)
            new_population = []
            
            for _ in range(population_size):
                # Tournament selection
                tournament_size = 3
                tournament = np.random.choice(len(population), tournament_size, replace=False)
                winner = max([population[i] for i in tournament], key=lambda x: x[1])
                
                # Crossover and mutation
                if np.random.random() < crossover_rate and len(new_population) > 0:
                    parent1 = winner[0]
                    parent2 = np.random.choice(new_population)[0]
                    child = self._crossover_parameters(parent1, parent2)
                else:
                    child = winner[0].copy()
                
                if np.random.random() < mutation_rate:
                    child = self._mutate_parameters(child)
                
                # Evaluate child
                child_score = await self._evaluate_parameters(child, context)
                new_population.append((child, child_score))
            
            population = new_population
            
            # Update best
            generation_best = max(population, key=lambda x: x[1])
            if generation_best[1] > best_individual[1]:
                best_individual = generation_best
        
        improvement = ((best_individual[1] - initial_score) / abs(initial_score)) * 100 if initial_score != 0 else 0
        
        return OptimizationResult(
            success=best_individual[1] > initial_score,
            optimal_parameters={**parameters, **best_individual[0]},
            optimization_score=best_individual[1],
            improvement_percentage=improvement,
            method_used=OptimizationMethod.GENETIC,
            iterations_used=generations * population_size,
            convergence_achieved=False,  # GA doesn't have explicit convergence
            template_bounds_respected=self._check_bounds_compliance(best_individual[0]),
            execution_time_seconds=0.0,
            confidence_score=0.0
        )
    
    async def _random_search_optimization(self, 
                                        parameters: Dict[str, Any],
                                        context: Dict[str, Any]) -> OptimizationResult:
        """Random search optimization implementation"""
        
        best_params = parameters.copy()
        best_score = await self._evaluate_parameters(best_params, context)
        initial_score = best_score
        
        iterations = min(self.config.max_iterations, 100)
        
        for iteration in range(iterations):
            # Generate random candidate
            candidate_params = self._generate_random_parameters(parameters)
            
            # Evaluate candidate
            candidate_score = await self._evaluate_parameters(candidate_params, context)
            
            # Update best if improved
            if candidate_score > best_score:
                best_params = candidate_params.copy()
                best_score = candidate_score
        
        improvement = ((best_score - initial_score) / abs(initial_score)) * 100 if initial_score != 0 else 0
        
        return OptimizationResult(
            success=best_score > initial_score,
            optimal_parameters={**parameters, **best_params},
            optimization_score=best_score,
            improvement_percentage=improvement,
            method_used=OptimizationMethod.RANDOM_SEARCH,
            iterations_used=iterations,
            convergence_achieved=False,
            template_bounds_respected=self._check_bounds_compliance(best_params),
            execution_time_seconds=0.0,
            confidence_score=0.0
        )
    
    async def _grid_search_optimization(self, 
                                      parameters: Dict[str, Any],
                                      context: Dict[str, Any]) -> OptimizationResult:
        """Grid search optimization implementation"""
        
        # Limit grid search to most important parameters to avoid combinatorial explosion
        important_params = ['signal_threshold', 'max_position_size', 'stop_loss_pct']
        grid_params = {k: v for k, v in parameters.items() if k in important_params and k in self.template_bounds}
        
        if not grid_params:
            # Fallback to random search
            return await self._random_search_optimization(parameters, context)
        
        # Create grid
        grid_points = []
        grid_size_per_param = max(3, int(self.config.max_iterations ** (1/len(grid_params))))
        
        for param_name in grid_params:
            if param_name in self.template_bounds:
                min_val, max_val = self.template_bounds[param_name]
                grid_points.append(np.linspace(min_val, max_val, grid_size_per_param))
        
        # Evaluate grid points
        best_params = parameters.copy()
        best_score = await self._evaluate_parameters(best_params, context)
        initial_score = best_score
        
        evaluations = 0
        param_names = list(grid_params.keys())
        
        # Generate all combinations
        import itertools
        for combination in itertools.product(*grid_points):
            if evaluations >= self.config.max_iterations:
                break
            
            candidate_params = parameters.copy()
            for i, param_name in enumerate(param_names):
                candidate_params[param_name] = combination[i]
            
            candidate_score = await self._evaluate_parameters(candidate_params, context)
            evaluations += 1
            
            if candidate_score > best_score:
                best_params = candidate_params.copy()
                best_score = candidate_score
        
        improvement = ((best_score - initial_score) / abs(initial_score)) * 100 if initial_score != 0 else 0
        
        return OptimizationResult(
            success=best_score > initial_score,
            optimal_parameters=best_params,
            optimization_score=best_score,
            improvement_percentage=improvement,
            method_used=OptimizationMethod.GRID_SEARCH,
            iterations_used=evaluations,
            convergence_achieved=True,  # Grid search always completes
            template_bounds_respected=self._check_bounds_compliance(best_params),
            execution_time_seconds=0.0,
            confidence_score=0.0
        )
    
    async def _evaluate_parameters(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> float:
        """Evaluate parameter set using objective function"""
        try:
            # Call the objective function
            if asyncio.iscoroutinefunction(self.objective_function):
                performance_metrics = await self.objective_function(parameters, context)
            else:
                performance_metrics = self.objective_function(parameters, context)
            
            # Calculate weighted score
            score = self._calculate_performance_score(performance_metrics)
            
            # Apply penalties for bound violations
            if not self._check_bounds_compliance(parameters):
                score *= 0.5  # 50% penalty for bound violations
            
            return score
            
        except Exception as e:
            self.logger.error(f"Error evaluating parameters: {e}")
            return float('-inf')
    
    def _calculate_performance_score(self, performance_metrics: Dict[str, float]) -> float:
        """Calculate weighted performance score"""
        score = 0.0
        total_weight = 0.0
        
        for metric, weight in self.config.objective_weights.items():
            if metric in performance_metrics:
                value = performance_metrics[metric]
                
                # Normalize metrics to 0-1 scale (simplified)
                if metric == 'sharpe_ratio':
                    normalized_value = min(1.0, max(0.0, (value + 2) / 4))  # -2 to 2 range
                elif metric == 'total_return':
                    normalized_value = min(1.0, max(0.0, (value + 0.5) / 1.5))  # -0.5 to 1.0 range
                elif metric == 'max_drawdown':
                    normalized_value = min(1.0, max(0.0, 1 - abs(value)))  # Lower is better
                elif metric == 'volatility':
                    normalized_value = min(1.0, max(0.0, 1 - value / 0.5))  # Lower is better
                elif metric == 'win_rate':
                    normalized_value = min(1.0, max(0.0, value))  # 0-1 range
                else:
                    normalized_value = min(1.0, max(0.0, value))
                
                score += normalized_value * abs(weight)
                total_weight += abs(weight)
        
        return score / total_weight if total_weight > 0 else 0.0
    
    def _generate_random_parameters(self, base_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate random parameter variations within bounds"""
        random_params = {}
        
        for param_name, current_value in base_parameters.items():
            if param_name in self.template_bounds:
                min_val, max_val = self.template_bounds[param_name]
                random_params[param_name] = np.random.uniform(min_val, max_val)
            else:
                random_params[param_name] = current_value
        
        return random_params
    
    def _generate_bayesian_candidate(self, 
                                   base_parameters: Dict[str, Any],
                                   evaluation_history: List[Tuple[Dict[str, Any], float]]) -> Dict[str, Any]:
        """Generate candidate using Bayesian-inspired exploration-exploitation"""
        
        if len(evaluation_history) < 3:
            # Not enough data, use random exploration
            return self._generate_random_parameters(base_parameters)
        
        # Find best performing parameters
        best_params = max(evaluation_history, key=lambda x: x[1])[0]
        
        # Generate candidate by perturbing best parameters
        candidate_params = {}
        exploration_factor = 0.2  # 20% exploration
        
        for param_name, current_value in base_parameters.items():
            if param_name in self.template_bounds and param_name in best_params:
                min_val, max_val = self.template_bounds[param_name]
                best_value = best_params[param_name]
                
                # Exploration around best value
                param_range = max_val - min_val
                exploration_range = param_range * exploration_factor
                
                new_value = np.random.normal(best_value, exploration_range / 3)
                new_value = np.clip(new_value, min_val, max_val)
                
                candidate_params[param_name] = new_value
            else:
                candidate_params[param_name] = current_value
        
        return candidate_params
    
    def _crossover_parameters(self, parent1: Dict[str, Any], parent2: Dict[str, Any]) -> Dict[str, Any]:
        """Crossover operation for genetic algorithm"""
        child = {}
        
        for param_name in parent1:
            if param_name in parent2:
                # Random selection from parents
                if np.random.random() < 0.5:
                    child[param_name] = parent1[param_name]
                else:
                    child[param_name] = parent2[param_name]
            else:
                child[param_name] = parent1[param_name]
        
        return child
    
    def _mutate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Mutation operation for genetic algorithm"""
        mutated = parameters.copy()
        mutation_strength = 0.1  # 10% mutation strength
        
        for param_name, value in parameters.items():
            if param_name in self.template_bounds:
                if np.random.random() < 0.3:  # 30% chance to mutate each parameter
                    min_val, max_val = self.template_bounds[param_name]
                    param_range = max_val - min_val
                    
                    # Add random noise
                    noise = np.random.normal(0, param_range * mutation_strength)
                    new_value = value + noise
                    new_value = np.clip(new_value, min_val, max_val)
                    
                    mutated[param_name] = new_value
        
        return mutated
    
    def _check_bounds_compliance(self, parameters: Dict[str, Any]) -> bool:
        """Check if parameters comply with template bounds"""
        for param_name, value in parameters.items():
            if param_name in self.template_bounds:
                min_val, max_val = self.template_bounds[param_name]
                if value < min_val or value > max_val:
                    return False
        return True
    
    def _calculate_confidence_score(self, result: OptimizationResult) -> float:
        """Calculate confidence score for optimization result"""
        confidence_factors = []
        
        # Improvement factor
        if result.improvement_percentage > 0:
            confidence_factors.append(min(1.0, result.improvement_percentage / 10))  # 10% improvement = 1.0 confidence
        else:
            confidence_factors.append(0.0)
        
        # Convergence factor
        if result.convergence_achieved:
            confidence_factors.append(0.9)
        else:
            confidence_factors.append(0.5)
        
        # Bounds compliance factor
        if result.template_bounds_respected:
            confidence_factors.append(1.0)
        else:
            confidence_factors.append(0.3)
        
        # Method reliability factor
        method_reliability = {
            OptimizationMethod.BAYESIAN: 0.9,
            OptimizationMethod.GENETIC: 0.8,
            OptimizationMethod.GRID_SEARCH: 0.95,
            OptimizationMethod.RANDOM_SEARCH: 0.6
        }
        confidence_factors.append(method_reliability.get(result.method_used, 0.5))
        
        # Calculate weighted confidence
        return np.mean(confidence_factors)
    
    def _analyze_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze current parameters relative to bounds and history"""
        analysis = {}
        
        for param_name, value in parameters.items():
            if param_name in self.template_bounds:
                min_val, max_val = self.template_bounds[param_name]
                normalized_position = (value - min_val) / (max_val - min_val)
                
                analysis[param_name] = {
                    'current_value': value,
                    'bounds': (min_val, max_val),
                    'normalized_position': normalized_position,
                    'adjustment_room': {
                        'increase': max_val - value,
                        'decrease': value - min_val
                    }
                }
        
        return analysis
    
    def _generate_optimization_suggestions(self, 
                                         parameters: Dict[str, Any],
                                         performance_metrics: Dict[str, float]) -> List[str]:
        """Generate specific optimization suggestions"""
        suggestions = []
        
        current_score = self._calculate_performance_score(performance_metrics)
        
        if current_score < 0.5:
            suggestions.append("Overall performance is below average - consider comprehensive optimization")
        
        # Parameter-specific suggestions
        for param_name, value in parameters.items():
            if param_name in self.template_bounds:
                min_val, max_val = self.template_bounds[param_name]
                normalized_pos = (value - min_val) / (max_val - min_val)
                
                if param_name == 'signal_threshold':
                    if normalized_pos > 0.8:
                        suggestions.append("Signal threshold is very high - may be missing opportunities")
                    elif normalized_pos < 0.2:
                        suggestions.append("Signal threshold is very low - may be taking excessive risk")
                
                elif param_name == 'max_position_size':
                    if normalized_pos > 0.8:
                        suggestions.append("Position sizes are large - consider reducing for better risk management")
                    elif normalized_pos < 0.2:
                        suggestions.append("Position sizes are small - may be underutilizing capital")
        
        return suggestions
    
    def _assess_optimization_risk(self, parameters: Dict[str, Any]) -> str:
        """Assess risk level of parameter optimization"""
        risk_factors = 0
        
        # Check parameter positions relative to bounds
        for param_name, value in parameters.items():
            if param_name in self.template_bounds:
                min_val, max_val = self.template_bounds[param_name]
                normalized_pos = (value - min_val) / (max_val - min_val)
                
                # Risk factors for extreme positions
                if normalized_pos > 0.9 or normalized_pos < 0.1:
                    risk_factors += 1
        
        # Template category risk assessment
        if self.current_template_category == TemplateCategory.COMPOSITE:
            risk_factors += 1  # More complex templates have higher optimization risk
        
        # Map risk factors to risk level
        if risk_factors >= 3:
            return 'high'
        elif risk_factors >= 2:
            return 'medium'
        elif risk_factors >= 1:
            return 'low'
        else:
            return 'minimal'
    
    def _estimate_improvement_potential(self, 
                                      parameters: Dict[str, Any],
                                      performance_metrics: Dict[str, float]) -> float:
        """Estimate potential improvement from optimization"""
        current_score = self._calculate_performance_score(performance_metrics)
        
        # Base improvement potential on current score
        if current_score > 0.8:
            return 0.05  # 5% potential improvement for high-performing strategies
        elif current_score > 0.6:
            return 0.15  # 15% potential improvement for moderate performers
        elif current_score > 0.4:
            return 0.30  # 30% potential improvement for poor performers
        else:
            return 0.50  # 50% potential improvement for very poor performers
    
    def _analyze_optimization_trend(self) -> str:
        """Analyze trend in optimization results"""
        if len(self.optimization_history) < 3:
            return 'insufficient_data'
        
        recent_scores = [r.optimization_score for r in self.optimization_history[-5:]]
        
        if len(recent_scores) > 1:
            trend_slope = np.polyfit(range(len(recent_scores)), recent_scores, 1)[0]
            
            if trend_slope > 0.01:
                return 'improving'
            elif trend_slope < -0.01:
                return 'declining'
            else:
                return 'stable'
        
        return 'stable'
    
    def _analyze_method_performance(self) -> Dict[str, Dict[str, float]]:
        """Analyze performance of different optimization methods"""
        method_stats = defaultdict(lambda: {'scores': [], 'improvements': [], 'success_rate': 0})
        
        for result in self.optimization_history:
            method = result.method_used.value
            method_stats[method]['scores'].append(result.optimization_score)
            method_stats[method]['improvements'].append(result.improvement_percentage)
        
        # Calculate statistics
        performance_analysis = {}
        for method, stats in method_stats.items():
            if stats['scores']:
                performance_analysis[method] = {
                    'avg_score': np.mean(stats['scores']),
                    'avg_improvement': np.mean(stats['improvements']),
                    'success_rate': len([i for i in stats['improvements'] if i > 0]) / len(stats['improvements']),
                    'total_uses': len(stats['scores'])
                }
        
        return performance_analysis
    
    def _analyze_convergence_statistics(self) -> Dict[str, float]:
        """Analyze convergence statistics across optimizations"""
        if not self.optimization_history:
            return {}
        
        convergence_rates = [r.convergence_achieved for r in self.optimization_history]
        avg_iterations = np.mean([r.iterations_used for r in self.optimization_history])
        avg_execution_time = np.mean([r.execution_time_seconds for r in self.optimization_history])
        
        return {
            'convergence_rate': sum(convergence_rates) / len(convergence_rates),
            'average_iterations': avg_iterations,
            'average_execution_time_seconds': avg_execution_time,
            'fastest_convergence': min([r.iterations_used for r in self.optimization_history if r.convergence_achieved], default=0),
            'slowest_convergence': max([r.iterations_used for r in self.optimization_history if r.convergence_achieved], default=0)
        }
