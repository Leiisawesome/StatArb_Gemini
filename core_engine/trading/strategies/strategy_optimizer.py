"""
Strategy Engine - Strategy Optimizer
Advanced parameter optimization and strategy tuning system
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
import warnings
from collections import defaultdict
import copy
import random
import json
from abc import ABC, abstractmethod
import scipy.optimize as opt
from scipy.stats import norm
import itertools

# Import strategy components
from .strategy_engine import BaseStrategy, StrategyConfig, StrategyMetrics

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class OptimizationObjective(Enum):
    """Optimization objectives"""
    MAXIMIZE_RETURN = "maximize_return"
    MAXIMIZE_SHARPE = "maximize_sharpe"
    MAXIMIZE_SORTINO = "maximize_sortino"
    MINIMIZE_DRAWDOWN = "minimize_drawdown"
    MAXIMIZE_PROFIT_FACTOR = "maximize_profit_factor"
    MINIMIZE_VOLATILITY = "minimize_volatility"
    MAXIMIZE_CALMAR = "maximize_calmar"
    CUSTOM = "custom"


class OptimizationMethod(Enum):
    """Optimization methods"""
    GRID_SEARCH = "grid_search"
    RANDOM_SEARCH = "random_search"
    BAYESIAN = "bayesian"
    GENETIC_ALGORITHM = "genetic_algorithm"
    PARTICLE_SWARM = "particle_swarm"
    DIFFERENTIAL_EVOLUTION = "differential_evolution"
    SIMULATED_ANNEALING = "simulated_annealing"
    TREE_PARZEN_ESTIMATOR = "tree_parzen_estimator"


class ParameterType(Enum):
    """Parameter types for optimization"""
    INTEGER = "integer"
    FLOAT = "float"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"
    LOG_UNIFORM = "log_uniform"


@dataclass
class ParameterRange:
    """Parameter range specification for optimization"""
    
    parameter_name: str = ""
    parameter_type: ParameterType = ParameterType.FLOAT
    
    # Numeric ranges
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step_size: Optional[float] = None
    
    # Categorical choices
    choices: Optional[List[Any]] = None
    
    # Distribution settings
    log_scale: bool = False
    
    # Constraints
    constraints: List[str] = field(default_factory=list)  # e.g., ["> 0", "< max_positions"]


@dataclass
class OptimizationConfig:
    """Configuration for strategy optimization"""
    
    # Optimization settings
    objective: OptimizationObjective = OptimizationObjective.MAXIMIZE_SHARPE
    method: OptimizationMethod = OptimizationMethod.BAYESIAN
    max_iterations: int = 100
    max_time: float = 3600.0  # 1 hour
    
    # Parameter ranges
    parameter_ranges: List[ParameterRange] = field(default_factory=list)
    
    # Cross-validation settings
    use_cross_validation: bool = True
    cv_folds: int = 5
    train_test_split: float = 0.8
    purge_gap: int = 0  # Gap between train and test data
    
    # Bayesian optimization settings
    n_initial_points: int = 10
    acquisition_function: str = "EI"  # Expected Improvement
    kappa: float = 2.576  # Exploration parameter
    xi: float = 0.01      # Exploration parameter
    
    # Genetic algorithm settings
    population_size: int = 50
    mutation_rate: float = 0.1
    crossover_rate: float = 0.8
    elitism_rate: float = 0.1
    
    # Particle swarm settings
    swarm_size: int = 30
    inertia_weight: float = 0.9
    cognitive_weight: float = 2.0
    social_weight: float = 2.0
    
    # Performance settings
    parallel_evaluation: bool = True
    max_workers: int = 4
    early_stopping: bool = True
    patience: int = 20  # Early stopping patience
    
    # Validation settings
    min_trades: int = 10
    min_periods: int = 100
    out_of_sample_validation: bool = True
    
    # Custom objective function
    custom_objective: Optional[Callable[[StrategyMetrics], float]] = None


@dataclass
class OptimizationResult:
    """Result of strategy optimization"""
    
    # Best parameters
    best_parameters: Dict[str, Any] = field(default_factory=dict)
    best_score: float = 0.0
    best_metrics: Optional[StrategyMetrics] = None
    
    # Optimization history
    parameter_history: List[Dict[str, Any]] = field(default_factory=list)
    score_history: List[float] = field(default_factory=list)
    
    # Cross-validation results
    cv_scores: List[float] = field(default_factory=list)
    cv_mean: float = 0.0
    cv_std: float = 0.0
    
    # Out-of-sample validation
    oos_score: Optional[float] = None
    oos_metrics: Optional[StrategyMetrics] = None
    
    # Optimization metadata
    optimization_time: float = 0.0
    total_evaluations: int = 0
    successful_evaluations: int = 0
    failed_evaluations: int = 0
    convergence_iteration: Optional[int] = None
    
    # Statistical significance
    significance_test: Optional[Dict[str, Any]] = None
    
    # Performance analysis
    parameter_importance: Dict[str, float] = field(default_factory=dict)
    parameter_correlations: Optional[pd.DataFrame] = None
    
    # Optimization details
    method_used: OptimizationMethod = OptimizationMethod.BAYESIAN
    objective_used: OptimizationObjective = OptimizationObjective.MAXIMIZE_SHARPE
    
    # Results metadata
    optimization_date: datetime = field(default_factory=datetime.now)
    data_period: Optional[Tuple[datetime, datetime]] = None


class BaseOptimizer(ABC):
    """Abstract base class for optimization algorithms"""
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        
        # Optimization state
        self.best_score = float('-inf') if self._is_maximization() else float('inf')
        self.best_parameters = {}
        self.evaluation_history = []
        
        # Performance tracking
        self.total_evaluations = 0
        self.successful_evaluations = 0
        self.failed_evaluations = 0
        
        logger.info(f"Optimizer initialized: {self.__class__.__name__}")
    
    @abstractmethod
    def optimize(self, objective_function: Callable[[Dict[str, Any]], float]) -> OptimizationResult:
        """Perform optimization - must be implemented by subclasses"""
        pass
    
    def _is_maximization(self) -> bool:
        """Check if objective should be maximized"""
        maximization_objectives = {
            OptimizationObjective.MAXIMIZE_RETURN,
            OptimizationObjective.MAXIMIZE_SHARPE,
            OptimizationObjective.MAXIMIZE_SORTINO,
            OptimizationObjective.MAXIMIZE_PROFIT_FACTOR,
            OptimizationObjective.MAXIMIZE_CALMAR
        }
        return self.config.objective in maximization_objectives
    
    def _evaluate_parameters(self, parameters: Dict[str, Any], 
                           objective_function: Callable[[Dict[str, Any]], float]) -> float:
        """Evaluate parameters and track results"""
        
        try:
            self.total_evaluations += 1
            score = objective_function(parameters)
            
            if np.isfinite(score):
                self.successful_evaluations += 1
                
                # Update best if better
                is_better = (score > self.best_score if self._is_maximization() 
                           else score < self.best_score)
                
                if is_better:
                    self.best_score = score
                    self.best_parameters = parameters.copy()
                
                # Record history
                self.evaluation_history.append({
                    'parameters': parameters.copy(),
                    'score': score,
                    'evaluation': self.total_evaluations
                })
                
                return score
            else:
                self.failed_evaluations += 1
                return float('-inf') if self._is_maximization() else float('inf')
                
        except Exception as e:
            logger.error(f"Error evaluating parameters: {e}")
            self.failed_evaluations += 1
            return float('-inf') if self._is_maximization() else float('inf')
    
    def _generate_random_parameters(self) -> Dict[str, Any]:
        """Generate random parameters within specified ranges"""
        
        parameters = {}
        
        for param_range in self.config.parameter_ranges:
            name = param_range.parameter_name
            param_type = param_range.parameter_type
            
            if param_type == ParameterType.FLOAT:
                if param_range.log_scale:
                    value = np.exp(np.random.uniform(
                        np.log(param_range.min_value),
                        np.log(param_range.max_value)
                    ))
                else:
                    value = np.random.uniform(param_range.min_value, param_range.max_value)
                parameters[name] = value
                
            elif param_type == ParameterType.INTEGER:
                value = np.random.randint(param_range.min_value, param_range.max_value + 1)
                parameters[name] = value
                
            elif param_type == ParameterType.CATEGORICAL:
                value = np.random.choice(param_range.choices)
                parameters[name] = value
                
            elif param_type == ParameterType.BOOLEAN:
                value = np.random.choice([True, False])
                parameters[name] = value
                
            elif param_type == ParameterType.LOG_UNIFORM:
                log_min = np.log10(param_range.min_value)
                log_max = np.log10(param_range.max_value)
                value = 10 ** np.random.uniform(log_min, log_max)
                parameters[name] = value
        
        return parameters


class GridSearchOptimizer(BaseOptimizer):
    """Grid search optimization algorithm"""
    
    def optimize(self, objective_function: Callable[[Dict[str, Any]], float]) -> OptimizationResult:
        """Perform grid search optimization"""
        
        start_time = datetime.now()
        
        try:
            # Generate parameter grid
            parameter_grid = self._generate_parameter_grid()
            total_combinations = len(parameter_grid)
            
            logger.info(f"Starting grid search with {total_combinations} combinations")
            
            # Evaluate all combinations
            if self.config.parallel_evaluation:
                scores = self._evaluate_parallel(parameter_grid, objective_function)
            else:
                scores = self._evaluate_sequential(parameter_grid, objective_function)
            
            # Create optimization result
            optimization_time = (datetime.now() - start_time).total_seconds()
            
            result = OptimizationResult(
                best_parameters=self.best_parameters,
                best_score=self.best_score,
                parameter_history=[h['parameters'] for h in self.evaluation_history],
                score_history=[h['score'] for h in self.evaluation_history],
                optimization_time=optimization_time,
                total_evaluations=self.total_evaluations,
                successful_evaluations=self.successful_evaluations,
                failed_evaluations=self.failed_evaluations,
                method_used=OptimizationMethod.GRID_SEARCH,
                objective_used=self.config.objective
            )
            
            logger.info(f"Grid search completed: best score = {self.best_score:.6f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in grid search optimization: {e}")
            return OptimizationResult()
    
    def _generate_parameter_grid(self) -> List[Dict[str, Any]]:
        """Generate grid of parameters to test"""
        
        parameter_lists = {}
        
        for param_range in self.config.parameter_ranges:
            name = param_range.parameter_name
            param_type = param_range.parameter_type
            
            if param_type in [ParameterType.FLOAT, ParameterType.INTEGER]:
                if param_range.step_size:
                    values = np.arange(param_range.min_value, 
                                     param_range.max_value + param_range.step_size,
                                     param_range.step_size)
                else:
                    # Default to 10 points
                    values = np.linspace(param_range.min_value, param_range.max_value, 10)
                
                if param_type == ParameterType.INTEGER:
                    values = [int(v) for v in values]
                
                parameter_lists[name] = values
                
            elif param_type == ParameterType.CATEGORICAL:
                parameter_lists[name] = param_range.choices
                
            elif param_type == ParameterType.BOOLEAN:
                parameter_lists[name] = [True, False]
        
        # Generate all combinations
        keys = parameter_lists.keys()
        values = parameter_lists.values()
        combinations = itertools.product(*values)
        
        parameter_grid = [dict(zip(keys, combination)) for combination in combinations]
        
        return parameter_grid
    
    def _evaluate_parallel(self, parameter_grid: List[Dict[str, Any]],
                         objective_function: Callable[[Dict[str, Any]], float]) -> List[float]:
        """Evaluate parameters in parallel"""
        
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = []
            
            for parameters in parameter_grid:
                future = executor.submit(self._evaluate_parameters, parameters, objective_function)
                futures.append(future)
            
            scores = []
            for future in as_completed(futures):
                try:
                    score = future.result()
                    scores.append(score)
                except Exception as e:
                    logger.error(f"Error in parallel evaluation: {e}")
                    scores.append(float('-inf') if self._is_maximization() else float('inf'))
        
        return scores
    
    def _evaluate_sequential(self, parameter_grid: List[Dict[str, Any]],
                           objective_function: Callable[[Dict[str, Any]], float]) -> List[float]:
        """Evaluate parameters sequentially"""
        
        scores = []
        
        for parameters in parameter_grid:
            score = self._evaluate_parameters(parameters, objective_function)
            scores.append(score)
        
        return scores


class RandomSearchOptimizer(BaseOptimizer):
    """Random search optimization algorithm"""
    
    def optimize(self, objective_function: Callable[[Dict[str, Any]], float]) -> OptimizationResult:
        """Perform random search optimization"""
        
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting random search with {self.config.max_iterations} iterations")
            
            # Early stopping tracking
            best_iteration = 0
            no_improvement_count = 0
            
            for iteration in range(self.config.max_iterations):
                # Generate random parameters
                parameters = self._generate_random_parameters()
                
                # Evaluate parameters
                score = self._evaluate_parameters(parameters, objective_function)
                
                # Check for improvement
                is_better = (score > self.best_score if self._is_maximization() 
                           else score < self.best_score)
                
                if is_better:
                    best_iteration = iteration
                    no_improvement_count = 0
                else:
                    no_improvement_count += 1
                
                # Early stopping
                if (self.config.early_stopping and 
                    no_improvement_count >= self.config.patience):
                    logger.info(f"Early stopping at iteration {iteration}")
                    break
                
                # Time limit check
                elapsed_time = (datetime.now() - start_time).total_seconds()
                if elapsed_time > self.config.max_time:
                    logger.info(f"Time limit reached at iteration {iteration}")
                    break
            
            # Create optimization result
            optimization_time = (datetime.now() - start_time).total_seconds()
            
            result = OptimizationResult(
                best_parameters=self.best_parameters,
                best_score=self.best_score,
                parameter_history=[h['parameters'] for h in self.evaluation_history],
                score_history=[h['score'] for h in self.evaluation_history],
                optimization_time=optimization_time,
                total_evaluations=self.total_evaluations,
                successful_evaluations=self.successful_evaluations,
                failed_evaluations=self.failed_evaluations,
                convergence_iteration=best_iteration,
                method_used=OptimizationMethod.RANDOM_SEARCH,
                objective_used=self.config.objective
            )
            
            logger.info(f"Random search completed: best score = {self.best_score:.6f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in random search optimization: {e}")
            return OptimizationResult()


class BayesianOptimizer(BaseOptimizer):
    """Bayesian optimization algorithm using Gaussian Process"""
    
    def __init__(self, config: OptimizationConfig):
        super().__init__(config)
        
        # Gaussian Process components (simplified implementation)
        self.X_observed = []  # Observed parameter sets
        self.y_observed = []  # Observed scores
        
        logger.info("Bayesian optimizer initialized")
    
    def optimize(self, objective_function: Callable[[Dict[str, Any]], float]) -> OptimizationResult:
        """Perform Bayesian optimization"""
        
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting Bayesian optimization with {self.config.max_iterations} iterations")
            
            # Initial random exploration
            for i in range(self.config.n_initial_points):
                parameters = self._generate_random_parameters()
                score = self._evaluate_parameters(parameters, objective_function)
                
                # Store for GP
                param_vector = self._parameters_to_vector(parameters)
                self.X_observed.append(param_vector)
                self.y_observed.append(score)
            
            # Bayesian optimization loop
            no_improvement_count = 0
            best_iteration = 0
            
            for iteration in range(self.config.n_initial_points, self.config.max_iterations):
                # Find next parameters using acquisition function
                next_parameters = self._acquire_next_parameters()
                
                # Evaluate next parameters
                score = self._evaluate_parameters(next_parameters, objective_function)
                
                # Update GP
                param_vector = self._parameters_to_vector(next_parameters)
                self.X_observed.append(param_vector)
                self.y_observed.append(score)
                
                # Check for improvement
                is_better = (score > self.best_score if self._is_maximization() 
                           else score < self.best_score)
                
                if is_better:
                    best_iteration = iteration
                    no_improvement_count = 0
                else:
                    no_improvement_count += 1
                
                # Early stopping
                if (self.config.early_stopping and 
                    no_improvement_count >= self.config.patience):
                    logger.info(f"Early stopping at iteration {iteration}")
                    break
                
                # Time limit check
                elapsed_time = (datetime.now() - start_time).total_seconds()
                if elapsed_time > self.config.max_time:
                    logger.info(f"Time limit reached at iteration {iteration}")
                    break
            
            # Create optimization result
            optimization_time = (datetime.now() - start_time).total_seconds()
            
            result = OptimizationResult(
                best_parameters=self.best_parameters,
                best_score=self.best_score,
                parameter_history=[h['parameters'] for h in self.evaluation_history],
                score_history=[h['score'] for h in self.evaluation_history],
                optimization_time=optimization_time,
                total_evaluations=self.total_evaluations,
                successful_evaluations=self.successful_evaluations,
                failed_evaluations=self.failed_evaluations,
                convergence_iteration=best_iteration,
                method_used=OptimizationMethod.BAYESIAN,
                objective_used=self.config.objective
            )
            
            logger.info(f"Bayesian optimization completed: best score = {self.best_score:.6f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in Bayesian optimization: {e}")
            return OptimizationResult()
    
    def _parameters_to_vector(self, parameters: Dict[str, Any]) -> List[float]:
        """Convert parameters dictionary to vector for GP"""
        
        vector = []
        
        for param_range in self.config.parameter_ranges:
            name = param_range.parameter_name
            value = parameters.get(name, 0)
            
            # Normalize to [0, 1] range
            if param_range.parameter_type == ParameterType.CATEGORICAL:
                # One-hot encoding for categorical
                choices = param_range.choices
                index = choices.index(value) if value in choices else 0
                normalized_value = index / (len(choices) - 1) if len(choices) > 1 else 0
            elif param_range.parameter_type == ParameterType.BOOLEAN:
                normalized_value = 1.0 if value else 0.0
            else:
                # Numeric normalization
                min_val = param_range.min_value
                max_val = param_range.max_value
                normalized_value = (value - min_val) / (max_val - min_val) if max_val > min_val else 0
            
            vector.append(normalized_value)
        
        return vector
    
    def _vector_to_parameters(self, vector: List[float]) -> Dict[str, Any]:
        """Convert vector back to parameters dictionary"""
        
        parameters = {}
        
        for i, param_range in enumerate(self.config.parameter_ranges):
            name = param_range.parameter_name
            normalized_value = vector[i]
            
            if param_range.parameter_type == ParameterType.CATEGORICAL:
                # Decode categorical
                choices = param_range.choices
                index = int(normalized_value * (len(choices) - 1))
                index = max(0, min(index, len(choices) - 1))
                value = choices[index]
            elif param_range.parameter_type == ParameterType.BOOLEAN:
                value = normalized_value > 0.5
            else:
                # Denormalize numeric
                min_val = param_range.min_value
                max_val = param_range.max_value
                value = min_val + normalized_value * (max_val - min_val)
                
                if param_range.parameter_type == ParameterType.INTEGER:
                    value = int(round(value))
            
            parameters[name] = value
        
        return parameters
    
    def _acquire_next_parameters(self) -> Dict[str, Any]:
        """Acquire next parameters using acquisition function (simplified)"""
        
        # Simplified acquisition: random search with some bias toward promising regions
        best_candidates = []
        
        # Generate candidates
        n_candidates = 1000
        for _ in range(n_candidates):
            candidate = self._generate_random_parameters()
            
            # Simple acquisition function: bias toward unexplored regions
            # In a full implementation, this would use GP predictions
            acquisition_score = random.random()  # Placeholder
            
            best_candidates.append((acquisition_score, candidate))
        
        # Select best candidate
        best_candidates.sort(key=lambda x: x[0], reverse=True)
        
        return best_candidates[0][1]


class GeneticAlgorithmOptimizer(BaseOptimizer):
    """Genetic algorithm optimization"""
    
    def optimize(self, objective_function: Callable[[Dict[str, Any]], float]) -> OptimizationResult:
        """Perform genetic algorithm optimization"""
        
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting genetic algorithm with population size {self.config.population_size}")
            
            # Initialize population
            population = []
            fitness_scores = []
            
            for _ in range(self.config.population_size):
                individual = self._generate_random_parameters()
                fitness = self._evaluate_parameters(individual, objective_function)
                population.append(individual)
                fitness_scores.append(fitness)
            
            # Evolution loop
            best_iteration = 0
            no_improvement_count = 0
            
            for generation in range(self.config.max_iterations):
                # Selection
                selected_parents = self._tournament_selection(population, fitness_scores)
                
                # Crossover and mutation
                new_population = []
                new_fitness = []
                
                for i in range(0, len(selected_parents), 2):
                    parent1 = selected_parents[i]
                    parent2 = selected_parents[i + 1] if i + 1 < len(selected_parents) else selected_parents[0]
                    
                    # Crossover
                    if random.random() < self.config.crossover_rate:
                        child1, child2 = self._crossover(parent1, parent2)
                    else:
                        child1, child2 = parent1.copy(), parent2.copy()
                    
                    # Mutation
                    if random.random() < self.config.mutation_rate:
                        child1 = self._mutate(child1)
                    if random.random() < self.config.mutation_rate:
                        child2 = self._mutate(child2)
                    
                    # Evaluate children
                    fitness1 = self._evaluate_parameters(child1, objective_function)
                    fitness2 = self._evaluate_parameters(child2, objective_function)
                    
                    new_population.extend([child1, child2])
                    new_fitness.extend([fitness1, fitness2])
                
                # Elitism: keep best individuals
                combined_population = population + new_population
                combined_fitness = fitness_scores + new_fitness
                
                # Sort by fitness
                sorted_indices = sorted(range(len(combined_fitness)), 
                                      key=lambda i: combined_fitness[i], 
                                      reverse=self._is_maximization())
                
                # Select next generation
                population = [combined_population[i] for i in sorted_indices[:self.config.population_size]]
                fitness_scores = [combined_fitness[i] for i in sorted_indices[:self.config.population_size]]
                
                # Check for improvement
                current_best = max(fitness_scores) if self._is_maximization() else min(fitness_scores)
                is_better = (current_best > self.best_score if self._is_maximization() 
                           else current_best < self.best_score)
                
                if is_better:
                    best_iteration = generation
                    no_improvement_count = 0
                else:
                    no_improvement_count += 1
                
                # Early stopping
                if (self.config.early_stopping and 
                    no_improvement_count >= self.config.patience):
                    logger.info(f"Early stopping at generation {generation}")
                    break
                
                # Time limit check
                elapsed_time = (datetime.now() - start_time).total_seconds()
                if elapsed_time > self.config.max_time:
                    logger.info(f"Time limit reached at generation {generation}")
                    break
            
            # Create optimization result
            optimization_time = (datetime.now() - start_time).total_seconds()
            
            result = OptimizationResult(
                best_parameters=self.best_parameters,
                best_score=self.best_score,
                parameter_history=[h['parameters'] for h in self.evaluation_history],
                score_history=[h['score'] for h in self.evaluation_history],
                optimization_time=optimization_time,
                total_evaluations=self.total_evaluations,
                successful_evaluations=self.successful_evaluations,
                failed_evaluations=self.failed_evaluations,
                convergence_iteration=best_iteration,
                method_used=OptimizationMethod.GENETIC_ALGORITHM,
                objective_used=self.config.objective
            )
            
            logger.info(f"Genetic algorithm completed: best score = {self.best_score:.6f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in genetic algorithm optimization: {e}")
            return OptimizationResult()
    
    def _tournament_selection(self, population: List[Dict[str, Any]], 
                            fitness_scores: List[float], tournament_size: int = 3) -> List[Dict[str, Any]]:
        """Tournament selection for genetic algorithm"""
        
        selected = []
        
        for _ in range(len(population)):
            # Random tournament
            tournament_indices = random.sample(range(len(population)), 
                                             min(tournament_size, len(population)))
            
            # Select best from tournament
            best_index = max(tournament_indices, key=lambda i: fitness_scores[i])
            selected.append(population[best_index].copy())
        
        return selected
    
    def _crossover(self, parent1: Dict[str, Any], parent2: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Crossover operation for genetic algorithm"""
        
        child1 = {}
        child2 = {}
        
        for param_range in self.config.parameter_ranges:
            name = param_range.parameter_name
            
            if random.random() < 0.5:
                child1[name] = parent1.get(name, 0)
                child2[name] = parent2.get(name, 0)
            else:
                child1[name] = parent2.get(name, 0)
                child2[name] = parent1.get(name, 0)
        
        return child1, child2
    
    def _mutate(self, individual: Dict[str, Any]) -> Dict[str, Any]:
        """Mutation operation for genetic algorithm"""
        
        mutated = individual.copy()
        
        for param_range in self.config.parameter_ranges:
            name = param_range.parameter_name
            
            if random.random() < 0.1:  # 10% chance to mutate each parameter
                if param_range.parameter_type in [ParameterType.FLOAT, ParameterType.INTEGER]:
                    # Add Gaussian noise
                    current_value = mutated.get(name, 0)
                    noise_std = (param_range.max_value - param_range.min_value) * 0.1
                    noise = np.random.normal(0, noise_std)
                    
                    new_value = current_value + noise
                    new_value = max(param_range.min_value, min(param_range.max_value, new_value))
                    
                    if param_range.parameter_type == ParameterType.INTEGER:
                        new_value = int(round(new_value))
                    
                    mutated[name] = new_value
                    
                elif param_range.parameter_type == ParameterType.CATEGORICAL:
                    # Random choice
                    mutated[name] = random.choice(param_range.choices)
                    
                elif param_range.parameter_type == ParameterType.BOOLEAN:
                    # Flip boolean
                    mutated[name] = not mutated.get(name, False)
        
        return mutated


class StrategyOptimizer:
    """
    Comprehensive Strategy Optimization System
    
    Provides advanced parameter optimization capabilities for trading strategies
    using multiple optimization algorithms and cross-validation techniques.
    """
    
    def __init__(self):
        """Initialize strategy optimizer"""
        
        # Optimizer implementations
        self._optimizers = {
            OptimizationMethod.GRID_SEARCH: GridSearchOptimizer,
            OptimizationMethod.RANDOM_SEARCH: RandomSearchOptimizer,
            OptimizationMethod.BAYESIAN: BayesianOptimizer,
            OptimizationMethod.GENETIC_ALGORITHM: GeneticAlgorithmOptimizer
        }
        
        # Optimization history
        self._optimization_history: List[OptimizationResult] = []
        
        # Performance tracking
        self._optimizer_stats = {
            'optimizations_run': 0,
            'successful_optimizations': 0,
            'failed_optimizations': 0,
            'total_evaluations': 0,
            'average_optimization_time': 0.0
        }
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info("Strategy optimizer initialized")
    
    def optimize_strategy(self, strategy_class: type, base_config: StrategyConfig,
                         data: pd.DataFrame, optimization_config: OptimizationConfig) -> OptimizationResult:
        """Optimize strategy parameters"""
        
        start_time = datetime.now()
        
        try:
            with self._lock:
                self._optimizer_stats['optimizations_run'] += 1
                
                logger.info(f"Starting strategy optimization: {optimization_config.method.value}")
                
                # Create objective function
                objective_function = self._create_objective_function(
                    strategy_class, base_config, data, optimization_config
                )
                
                # Select and create optimizer
                optimizer_class = self._optimizers.get(optimization_config.method)
                if not optimizer_class:
                    raise ValueError(f"Unsupported optimization method: {optimization_config.method}")
                
                optimizer = optimizer_class(optimization_config)
                
                # Perform optimization
                result = optimizer.optimize(objective_function)
                
                # Add cross-validation if enabled
                if optimization_config.use_cross_validation:
                    cv_results = self._cross_validate(
                        strategy_class, base_config, data, 
                        result.best_parameters, optimization_config
                    )
                    result.cv_scores = cv_results['scores']
                    result.cv_mean = cv_results['mean']
                    result.cv_std = cv_results['std']
                
                # Out-of-sample validation
                if optimization_config.out_of_sample_validation:
                    oos_results = self._out_of_sample_validation(
                        strategy_class, base_config, data,
                        result.best_parameters, optimization_config
                    )
                    result.oos_score = oos_results['score']
                    result.oos_metrics = oos_results['metrics']
                
                # Statistical significance testing
                if len(result.score_history) > 10:
                    result.significance_test = self._test_significance(result.score_history)
                
                # Parameter importance analysis
                result.parameter_importance = self._analyze_parameter_importance(result)
                
                # Store result
                self._optimization_history.append(result)
                
                # Update statistics
                optimization_time = (datetime.now() - start_time).total_seconds()
                self._optimizer_stats['successful_optimizations'] += 1
                self._optimizer_stats['total_evaluations'] += result.total_evaluations
                
                # Update average time
                total_time = (self._optimizer_stats['average_optimization_time'] * 
                            (self._optimizer_stats['successful_optimizations'] - 1) + optimization_time)
                self._optimizer_stats['average_optimization_time'] = (
                    total_time / self._optimizer_stats['successful_optimizations']
                )
                
                logger.info(f"Strategy optimization completed: best score = {result.best_score:.6f}")
                
                return result
                
        except Exception as e:
            logger.error(f"Error in strategy optimization: {e}")
            self._optimizer_stats['failed_optimizations'] += 1
            return OptimizationResult()
    
    def _create_objective_function(self, strategy_class: type, base_config: StrategyConfig,
                                 data: pd.DataFrame, opt_config: OptimizationConfig) -> Callable[[Dict[str, Any]], float]:
        """Create objective function for optimization"""
        
        def objective_function(parameters: Dict[str, Any]) -> float:
            try:
                # Create strategy config with optimized parameters
                config = copy.deepcopy(base_config)
                
                # Apply parameters
                for param_name, param_value in parameters.items():
                    if hasattr(config, param_name):
                        setattr(config, param_name, param_value)
                    else:
                        config.strategy_parameters[param_name] = param_value
                
                # Create and run strategy
                strategy = strategy_class(config)
                
                # Initialize strategy
                if not strategy.initialize():
                    return float('-inf') if self._is_maximization(opt_config.objective) else float('inf')
                
                # Simulate strategy on data
                metrics = self._simulate_strategy(strategy, data)
                
                # Calculate objective score
                score = self._calculate_objective_score(metrics, opt_config.objective, opt_config.custom_objective)
                
                return score
                
            except Exception as e:
                logger.error(f"Error in objective function: {e}")
                return float('-inf') if self._is_maximization(opt_config.objective) else float('inf')
        
        return objective_function
    
    def _simulate_strategy(self, strategy: BaseStrategy, data: pd.DataFrame) -> StrategyMetrics:
        """Simulate strategy execution on historical data"""
        
        try:
            # Convert data to required format
            market_data = {"default": data}
            
            # Run strategy simulation
            for i in range(len(data)):
                # Get data up to current point
                current_data = {"default": data.iloc[:i+1]}
                
                # Update strategy
                signals = strategy.update(current_data)
                
                # In a real implementation, this would execute trades
                # and update positions based on signals
            
            # Return final metrics
            return strategy.get_metrics()
            
        except Exception as e:
            logger.error(f"Error simulating strategy: {e}")
            return StrategyMetrics()
    
    def _calculate_objective_score(self, metrics: StrategyMetrics, 
                                 objective: OptimizationObjective,
                                 custom_objective: Optional[Callable[[StrategyMetrics], float]]) -> float:
        """Calculate objective score from strategy metrics"""
        
        try:
            if objective == OptimizationObjective.MAXIMIZE_RETURN:
                return metrics.total_return
            elif objective == OptimizationObjective.MAXIMIZE_SHARPE:
                return metrics.sharpe_ratio
            elif objective == OptimizationObjective.MAXIMIZE_SORTINO:
                return metrics.sortino_ratio if hasattr(metrics, 'sortino_ratio') else 0.0
            elif objective == OptimizationObjective.MINIMIZE_DRAWDOWN:
                return -abs(metrics.max_drawdown)
            elif objective == OptimizationObjective.MAXIMIZE_PROFIT_FACTOR:
                return metrics.profit_factor
            elif objective == OptimizationObjective.MINIMIZE_VOLATILITY:
                return -metrics.volatility
            elif objective == OptimizationObjective.MAXIMIZE_CALMAR:
                if metrics.max_drawdown != 0:
                    return metrics.total_return / abs(metrics.max_drawdown)
                else:
                    return metrics.total_return
            elif objective == OptimizationObjective.CUSTOM and custom_objective:
                return custom_objective(metrics)
            else:
                return metrics.sharpe_ratio  # Default to Sharpe ratio
                
        except Exception as e:
            logger.error(f"Error calculating objective score: {e}")
            return 0.0
    
    def _is_maximization(self, objective: OptimizationObjective) -> bool:
        """Check if objective should be maximized"""
        maximization_objectives = {
            OptimizationObjective.MAXIMIZE_RETURN,
            OptimizationObjective.MAXIMIZE_SHARPE,
            OptimizationObjective.MAXIMIZE_SORTINO,
            OptimizationObjective.MAXIMIZE_PROFIT_FACTOR,
            OptimizationObjective.MAXIMIZE_CALMAR
        }
        return objective in maximization_objectives
    
    def _cross_validate(self, strategy_class: type, base_config: StrategyConfig,
                       data: pd.DataFrame, parameters: Dict[str, Any],
                       opt_config: OptimizationConfig) -> Dict[str, Any]:
        """Perform cross-validation"""
        
        try:
            cv_scores = []
            
            # Simple time series split
            fold_size = len(data) // opt_config.cv_folds
            
            for fold in range(opt_config.cv_folds):
                # Create train/test split
                start_idx = fold * fold_size
                end_idx = min((fold + 1) * fold_size, len(data))
                
                if end_idx - start_idx < opt_config.min_periods:
                    continue
                
                fold_data = data.iloc[start_idx:end_idx]
                
                # Create and test strategy
                config = copy.deepcopy(base_config)
                for param_name, param_value in parameters.items():
                    if hasattr(config, param_name):
                        setattr(config, param_name, param_value)
                    else:
                        config.strategy_parameters[param_name] = param_value
                
                strategy = strategy_class(config)
                if strategy.initialize():
                    metrics = self._simulate_strategy(strategy, fold_data)
                    score = self._calculate_objective_score(metrics, opt_config.objective, opt_config.custom_objective)
                    cv_scores.append(score)
            
            if cv_scores:
                return {
                    'scores': cv_scores,
                    'mean': np.mean(cv_scores),
                    'std': np.std(cv_scores)
                }
            else:
                return {'scores': [], 'mean': 0.0, 'std': 0.0}
                
        except Exception as e:
            logger.error(f"Error in cross-validation: {e}")
            return {'scores': [], 'mean': 0.0, 'std': 0.0}
    
    def _out_of_sample_validation(self, strategy_class: type, base_config: StrategyConfig,
                                data: pd.DataFrame, parameters: Dict[str, Any],
                                opt_config: OptimizationConfig) -> Dict[str, Any]:
        """Perform out-of-sample validation"""
        
        try:
            # Split data
            split_point = int(len(data) * opt_config.train_test_split)
            oos_data = data.iloc[split_point:]
            
            if len(oos_data) < opt_config.min_periods:
                return {'score': None, 'metrics': None}
            
            # Create and test strategy on out-of-sample data
            config = copy.deepcopy(base_config)
            for param_name, param_value in parameters.items():
                if hasattr(config, param_name):
                    setattr(config, param_name, param_value)
                else:
                    config.strategy_parameters[param_name] = param_value
            
            strategy = strategy_class(config)
            if strategy.initialize():
                metrics = self._simulate_strategy(strategy, oos_data)
                score = self._calculate_objective_score(metrics, opt_config.objective, opt_config.custom_objective)
                return {'score': score, 'metrics': metrics}
            
            return {'score': None, 'metrics': None}
            
        except Exception as e:
            logger.error(f"Error in out-of-sample validation: {e}")
            return {'score': None, 'metrics': None}
    
    def _test_significance(self, scores: List[float]) -> Dict[str, Any]:
        """Test statistical significance of optimization results"""
        
        try:
            if len(scores) < 10:
                return {}
            
            # Basic statistical tests
            mean_score = np.mean(scores)
            std_score = np.std(scores)
            
            # T-test against zero (no improvement)
            t_stat = mean_score / (std_score / np.sqrt(len(scores))) if std_score > 0 else 0
            
            # Simple p-value approximation
            p_value = 2 * (1 - norm.cdf(abs(t_stat)))
            
            return {
                'mean': mean_score,
                'std': std_score,
                't_statistic': t_stat,
                'p_value': p_value,
                'significant': p_value < 0.05
            }
            
        except Exception as e:
            logger.error(f"Error in significance testing: {e}")
            return {}
    
    def _analyze_parameter_importance(self, result: OptimizationResult) -> Dict[str, float]:
        """Analyze parameter importance from optimization history"""
        
        try:
            if len(result.parameter_history) < 10:
                return {}
            
            importance = {}
            
            # Simple correlation-based importance
            for param_name in result.parameter_history[0].keys():
                param_values = [params.get(param_name, 0) for params in result.parameter_history]
                scores = result.score_history
                
                if len(set(param_values)) > 1:  # Parameter varies
                    correlation = np.corrcoef(param_values, scores)[0, 1]
                    importance[param_name] = abs(correlation) if not np.isnan(correlation) else 0.0
                else:
                    importance[param_name] = 0.0
            
            return importance
            
        except Exception as e:
            logger.error(f"Error analyzing parameter importance: {e}")
            return {}
    
    def get_optimization_history(self) -> List[OptimizationResult]:
        """Get optimization history"""
        
        with self._lock:
            return self._optimization_history.copy()
    
    def get_optimizer_stats(self) -> Dict[str, Any]:
        """Get optimizer statistics"""
        
        with self._lock:
            return self._optimizer_stats.copy()