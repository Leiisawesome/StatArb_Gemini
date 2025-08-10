"""
Genetic Algorithm Optimizer

Genetic algorithm implementation for parameter optimization.

Author: Pro Quant Desk Trader
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
import random

from .parameter_optimizer import ParameterOptimizer, OptimizationConfig, OptimizationResult
from strategy_layer.base import StrategyError


@dataclass
class Individual:
    """Individual in genetic algorithm population"""
    parameters: Dict[str, float]
    fitness: float = field(default=float('-inf'))
    
    def __post_init__(self):
        if self.fitness is None or self.fitness == 0.0:
            self.fitness = float('-inf')


class GeneticOptimizer(ParameterOptimizer):
    """Genetic algorithm optimizer for parameter optimization"""
    
    def __init__(self, config: OptimizationConfig):
        super().__init__(config)
        self.population: List[Individual] = []
        self.best_individual: Optional[Individual] = None
    
    def optimize(self, objective_function: Callable, initial_parameters: Dict[str, float]) -> OptimizationResult:
        """Optimize parameters using genetic algorithm"""
        try:
            self.logger.info("Starting genetic algorithm optimization")
            
            # Initialize population
            self._initialize_population(initial_parameters)
            
            # Optimization history
            history = []
            best_objective = float('-inf')
            best_parameters = initial_parameters.copy()
            
            # Main optimization loop
            for iteration in range(self.config.max_iterations):
                # Evaluate fitness for all individuals
                self._evaluate_population(objective_function)
                
                # Update best individual
                valid_individuals = [ind for ind in self.population if ind.fitness is not None and not np.isnan(ind.fitness)]
                if valid_individuals:
                    current_best = max(valid_individuals, key=lambda x: x.fitness)
                    if current_best.fitness > best_objective:
                        best_objective = current_best.fitness
                        best_parameters = current_best.parameters.copy()
                        self.best_individual = current_best
                
                # Log progress
                self._log_progress(iteration, best_objective, best_parameters)
                
                # Record history
                history.append({
                    'iteration': iteration,
                    'objective': best_objective,
                    'best_parameters': best_parameters.copy(),
                    'population_fitness': [ind.fitness if ind.fitness is not None else float('-inf') for ind in self.population]
                })
                
                # Check convergence
                if self._check_convergence(history):
                    self.logger.info(f"Optimization converged at iteration {iteration}")
                    break
                
                # Create new population
                self._evolve_population()
            
            # Create result
            result = OptimizationResult(
                best_parameters=best_parameters,
                best_objective=best_objective,
                history=history,
                converged=self._check_convergence(history),
                iterations=len(history)
            )
            
            self.logger.info(f"Genetic algorithm optimization completed. Best objective: {best_objective:.6f}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in genetic algorithm optimization: {e}")
            raise StrategyError(f"Genetic algorithm optimization failed: {e}")
    
    def _initialize_population(self, initial_parameters: Dict[str, float]):
        """Initialize genetic algorithm population"""
        self.population = []
        
        # Add initial individual
        initial_individual = Individual(initial_parameters.copy())
        self.population.append(initial_individual)
        
        # Generate random individuals
        for _ in range(self.config.population_size - 1):
            individual = self._generate_random_individual(initial_parameters)
            self.population.append(individual)
        
        # Ensure all individuals have valid fitness values
        for individual in self.population:
            if individual.fitness is None:
                individual.fitness = float('-inf')
    
    def _generate_random_individual(self, base_parameters: Dict[str, float]) -> Individual:
        """Generate a random individual"""
        parameters = {}
        
        for param_name, base_value in base_parameters.items():
            if param_name in self.config.parameter_bounds:
                min_val, max_val = self.config.parameter_bounds[param_name]
                # Generate random value within bounds
                parameters[param_name] = random.uniform(min_val, max_val)
            else:
                # Use base value with some random perturbation
                perturbation = random.uniform(0.8, 1.2)
                parameters[param_name] = base_value * perturbation
        
        return Individual(parameters)
    
    def _evaluate_population(self, objective_function: Callable):
        """Evaluate fitness for all individuals in population"""
        for i, individual in enumerate(self.population):
            try:
                # Evaluate objective function
                objective_value = objective_function(individual.parameters)
                # Ensure we have a valid number
                if objective_value is None:
                    individual.fitness = float('-inf')
                else:
                    individual.fitness = float(objective_value)
                
                # Debug: check if fitness is None
                if individual.fitness is None:
                    self.logger.error(f"Individual {i} has None fitness after evaluation")
                    individual.fitness = float('-inf')
                    
            except Exception as e:
                self.logger.warning(f"Failed to evaluate individual {i}: {e}")
                individual.fitness = float('-inf')
    
    def _evolve_population(self):
        """Evolve population using genetic operators"""
        new_population = []
        
        # Elitism: keep best individuals
        valid_individuals = [ind for ind in self.population if ind.fitness is not None and not np.isnan(ind.fitness)]
        if valid_individuals:
            sorted_population = sorted(valid_individuals, key=lambda x: x.fitness, reverse=True)
            elite_individuals = sorted_population[:self.config.elite_size]
            new_population.extend(elite_individuals)
        else:
            # If no valid individuals, keep some random ones
            new_population.extend(self.population[:self.config.elite_size])
        
        # Generate rest of population through crossover and mutation
        while len(new_population) < self.config.population_size:
            # Selection
            parent1 = self._tournament_selection()
            parent2 = self._tournament_selection()
            
            # Crossover
            if random.random() < self.config.crossover_rate:
                child_params = self._crossover(parent1.parameters, parent2.parameters)
            else:
                child_params = parent1.parameters.copy()
            
            # Mutation
            if random.random() < self.config.mutation_rate:
                child_params = self._mutate(child_params)
            
            # Create new individual
            child = Individual(child_params)
            new_population.append(child)
        
        self.population = new_population[:self.config.population_size]
    
    def _tournament_selection(self, tournament_size: int = 3) -> Individual:
        """Tournament selection"""
        tournament = random.sample(self.population, min(tournament_size, len(self.population)))
        
        # Debug: check tournament fitness values
        for i, ind in enumerate(tournament):
            if ind.fitness is None:
                self.logger.error(f"Tournament individual {i} has None fitness")
                ind.fitness = float('-inf')
        
        valid_tournament = [ind for ind in tournament if ind.fitness is not None and not np.isnan(ind.fitness)]
        if valid_tournament:
            return max(valid_tournament, key=lambda x: x.fitness)
        else:
            return tournament[0]  # Return first individual if none are valid
    
    def _crossover(self, parent1_params: Dict[str, float], parent2_params: Dict[str, float]) -> Dict[str, float]:
        """Crossover two parent parameter sets"""
        child_params = {}
        
        for param_name in parent1_params.keys():
            if random.random() < 0.5:
                child_params[param_name] = parent1_params[param_name]
            else:
                child_params[param_name] = parent2_params[param_name]
        
        return child_params
    
    def _mutate(self, parameters: Dict[str, float]) -> Dict[str, float]:
        """Mutate parameters"""
        mutated_params = parameters.copy()
        
        for param_name, param_value in mutated_params.items():
            if random.random() < 0.1:  # 10% chance of mutation per parameter
                if param_name in self.config.parameter_bounds:
                    min_val, max_val = self.config.parameter_bounds[param_name]
                    # Gaussian mutation
                    mutation_strength = (max_val - min_val) * 0.1
                    mutation = random.gauss(0, mutation_strength)
                    mutated_params[param_name] = np.clip(param_value + mutation, min_val, max_val)
                else:
                    # Random perturbation
                    perturbation = random.uniform(0.9, 1.1)
                    mutated_params[param_name] = param_value * perturbation
        
        return mutated_params
    
    def get_population_statistics(self) -> Dict[str, float]:
        """Get statistics about current population"""
        if not self.population:
            return {}
        
        fitness_values = [ind.fitness for ind in self.population if ind.fitness is not None and not np.isnan(ind.fitness)]
        
        if not fitness_values:
            return {
                'mean_fitness': float('-inf'),
                'std_fitness': 0.0,
                'min_fitness': float('-inf'),
                'max_fitness': float('-inf'),
                'population_size': len(self.population)
            }
        
        return {
            'mean_fitness': np.mean(fitness_values),
            'std_fitness': np.std(fitness_values),
            'min_fitness': np.min(fitness_values),
            'max_fitness': np.max(fitness_values),
            'population_size': len(self.population)
        }
    
    def get_best_individual(self) -> Optional[Individual]:
        """Get the best individual from current population"""
        if not self.population:
            return None
        
        valid_individuals = [ind for ind in self.population if ind.fitness is not None and not np.isnan(ind.fitness)]
        if valid_individuals:
            return max(valid_individuals, key=lambda x: x.fitness)
        else:
            return None
