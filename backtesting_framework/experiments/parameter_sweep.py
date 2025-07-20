"""
Parameter Optimization for Backtesting Framework

Provides tools for optimizing strategy parameters using grid search,
random search, and other optimization techniques.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging
import itertools
import json
from pathlib import Path
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed

from .experiment_runner import ExperimentRunner, ExperimentConfig, ExperimentResult
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

@dataclass
class OptimizationConfig:
    """Configuration for parameter optimization"""
    # Optimization parameters
    optimization_metric: str = "sharpe_ratio"  # Metric to optimize
    optimization_direction: str = "maximize"   # maximize or minimize
    
    # Search parameters
    search_method: str = "grid_search"  # grid_search, random_search, bayesian
    max_iterations: int = 100
    n_jobs: int = -1  # Number of parallel jobs (-1 for all cores)
    
    # Parameter ranges
    parameter_ranges: Dict[str, List[Any]] = field(default_factory=dict)
    
    # Output configuration
    output_dir: str = "results/optimization"
    save_all_results: bool = True
    save_best_config: bool = True

@dataclass
class OptimizationResult:
    """Results from parameter optimization"""
    # Optimization metadata
    config: OptimizationConfig
    start_time: datetime
    end_time: datetime
    duration: float
    
    # Results
    best_params: Dict[str, Any]
    best_metric: float
    best_result: ExperimentResult
    
    # All results
    all_results: List[Tuple[Dict[str, Any], float, ExperimentResult]]
    
    # Summary statistics
    total_combinations: int
    completed_combinations: int
    success_rate: float

class ParameterSweep:
    """
    Parameter optimization tool for backtesting strategies
    
    Supports multiple optimization methods and parallel execution.
    """
    
    def __init__(self, base_config: ExperimentConfig, opt_config: OptimizationConfig):
        """
        Initialize parameter sweep
        
        Args:
            base_config: Base experiment configuration
            opt_config: Optimization configuration
        """
        self.base_config = base_config
        self.opt_config = opt_config
        self.logger = logging.getLogger(__name__)
        
        # Set number of jobs
        if self.opt_config.n_jobs == -1:
            self.opt_config.n_jobs = mp.cpu_count()
        
        self.logger.info(f"Initialized ParameterSweep with {self.opt_config.n_jobs} parallel jobs")
    
    def optimize(self, strategy_class: type) -> OptimizationResult:
        """
        Run parameter optimization
        
        Args:
            strategy_class: Strategy class to optimize
            
        Returns:
            OptimizationResult with optimization results
        """
        start_time = datetime.now()
        self.logger.info(f"Starting parameter optimization for {strategy_class.__name__}")
        
        # Generate parameter combinations
        param_combinations = self._generate_parameter_combinations()
        total_combinations = len(param_combinations)
        
        self.logger.info(f"Generated {total_combinations} parameter combinations")
        
        # Run optimization
        if self.opt_config.search_method == "grid_search":
            results = self._grid_search(param_combinations, strategy_class)
        elif self.opt_config.search_method == "random_search":
            results = self._random_search(param_combinations, strategy_class)
        else:
            raise ValueError(f"Unknown search method: {self.opt_config.search_method}")
        
        # Find best result
        best_params, best_metric, best_result = self._find_best_result(results)
        
        # Create optimization result
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        opt_result = OptimizationResult(
            config=self.opt_config,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            best_params=best_params,
            best_metric=best_metric,
            best_result=best_result,
            all_results=results,
            total_combinations=total_combinations,
            completed_combinations=len(results),
            success_rate=len(results) / total_combinations
        )
        
        # Save results
        self._save_optimization_results(opt_result)
        
        self.logger.info(f"Optimization completed in {duration:.2f} seconds")
        self.logger.info(f"Best {self.opt_config.optimization_metric}: {best_metric:.4f}")
        self.logger.info(f"Best parameters: {best_params}")
        
        return opt_result
    
    def _generate_parameter_combinations(self) -> List[Dict[str, Any]]:
        """
        Generate all parameter combinations for grid search
        
        Returns:
            List of parameter dictionaries
        """
        if not self.opt_config.parameter_ranges:
            return [{}]
        
        # Get all parameter names and their values
        param_names = list(self.opt_config.parameter_ranges.keys())
        param_values = list(self.opt_config.parameter_ranges.values())
        
        # Generate all combinations
        combinations = list(itertools.product(*param_values))
        
        # Convert to list of dictionaries
        param_combinations = []
        for combo in combinations:
            param_dict = dict(zip(param_names, combo))
            param_combinations.append(param_dict)
        
        return param_combinations
    
    def _grid_search(self, param_combinations: List[Dict[str, Any]], 
                    strategy_class: type) -> List[Tuple[Dict[str, Any], float, ExperimentResult]]:
        """
        Perform grid search optimization
        
        Args:
            param_combinations: List of parameter combinations
            strategy_class: Strategy class to test
            
        Returns:
            List of (params, metric, result) tuples
        """
        self.logger.info(f"Starting grid search with {len(param_combinations)} combinations")
        
        results = []
        
        if self.opt_config.n_jobs > 1:
            # Parallel execution
            results = self._parallel_search(param_combinations, strategy_class)
        else:
            # Sequential execution
            for i, params in enumerate(param_combinations):
                self.logger.info(f"Testing combination {i+1}/{len(param_combinations)}: {params}")
                
                try:
                    result = self._test_parameters(params, strategy_class)
                    if result is not None:
                        metric = self._extract_metric(result)
                        results.append((params, metric, result))
                except Exception as e:
                    self.logger.error(f"Failed to test parameters {params}: {e}")
        
        return results
    
    def _random_search(self, param_combinations: List[Dict[str, Any]], 
                      strategy_class: type) -> List[Tuple[Dict[str, Any], float, ExperimentResult]]:
        """
        Perform random search optimization
        
        Args:
            param_combinations: List of parameter combinations
            strategy_class: Strategy class to test
            
        Returns:
            List of (params, metric, result) tuples
        """
        self.logger.info(f"Starting random search with max {self.opt_config.max_iterations} iterations")
        
        # Randomly sample parameter combinations
        if len(param_combinations) > self.opt_config.max_iterations:
            indices = np.random.choice(len(param_combinations), 
                                     self.opt_config.max_iterations, 
                                     replace=False)
            sampled_combinations = [param_combinations[i] for i in indices]
        else:
            sampled_combinations = param_combinations
        
        return self._grid_search(sampled_combinations, strategy_class)
    
    def _parallel_search(self, param_combinations: List[Dict[str, Any]], 
                        strategy_class: type) -> List[Tuple[Dict[str, Any], float, ExperimentResult]]:
        """
        Perform parallel parameter search
        
        Args:
            param_combinations: List of parameter combinations
            strategy_class: Strategy class to test
            
        Returns:
            List of (params, metric, result) tuples
        """
        results = []
        
        with ProcessPoolExecutor(max_workers=self.opt_config.n_jobs) as executor:
            # Submit all jobs
            future_to_params = {
                executor.submit(self._test_parameters_worker, params, strategy_class, self.base_config): params
                for params in param_combinations
            }
            
            # Collect results
            for i, future in enumerate(as_completed(future_to_params)):
                params = future_to_params[future]
                self.logger.info(f"Completed {i+1}/{len(param_combinations)}: {params}")
                
                try:
                    result = future.result()
                    if result is not None:
                        metric = self._extract_metric(result)
                        results.append((params, metric, result))
                except Exception as e:
                    self.logger.error(f"Failed to test parameters {params}: {e}")
        
        return results
    
    def _test_parameters(self, params: Dict[str, Any], strategy_class: type) -> Optional[ExperimentResult]:
        """
        Test a single parameter combination
        
        Args:
            params: Parameter dictionary
            strategy_class: Strategy class to test
            
        Returns:
            ExperimentResult or None if failed
        """
        try:
            # Create configuration with new parameters
            config = self._create_config_with_params(params)
            
            # Run experiment
            runner = ExperimentRunner()
            result = runner.run_experiment(config)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to test parameters {params}: {e}")
            return None
    
    def _test_parameters_worker(self, params: Dict[str, Any], strategy_class: type, 
                              base_config: ExperimentConfig) -> Optional[ExperimentResult]:
        """
        Worker function for parallel parameter testing
        
        Args:
            params: Parameter dictionary
            strategy_class: Strategy class to test
            base_config: Base experiment configuration
            
        Returns:
            ExperimentResult or None if failed
        """
        try:
            # Create configuration with new parameters
            config = self._create_config_with_params(params, base_config)
            
            # Run experiment
            runner = ExperimentRunner()
            result = runner.run_experiment(config)
            
            return result
            
        except Exception as e:
            return None
    
    def _create_config_with_params(self, params: Dict[str, Any], 
                                 base_config: Optional[ExperimentConfig] = None) -> ExperimentConfig:
        """
        Create experiment configuration with given parameters
        
        Args:
            params: Parameter dictionary
            base_config: Base configuration (optional)
            
        Returns:
            Modified ExperimentConfig
        """
        config = base_config or self.base_config
        
        # Create new config with updated parameters
        new_config = ExperimentConfig(
            name=f"{config.name}_opt_{hash(str(params))}",
            symbols=config.symbols,
            start_date=config.start_date,
            end_date=config.end_date,
            strategy_class=config.strategy_class,
            strategy_params={**config.strategy_params, **params},
            initial_capital=config.initial_capital,
            commission_rate=config.commission_rate,
            slippage_rate=config.slippage_rate,
            max_position_size=config.max_position_size,
            stop_loss=config.stop_loss,
            take_profit=config.take_profit,
            output_dir=f"{self.opt_config.output_dir}/combination_{hash(str(params))}",
            save_trades=False,  # Disable saving for optimization
            save_signals=False,
            generate_plots=False,
            benchmark_symbol=config.benchmark_symbol,
            risk_free_rate=config.risk_free_rate
        )
        
        return new_config
    
    def _extract_metric(self, result: ExperimentResult) -> float:
        """
        Extract optimization metric from experiment result
        
        Args:
            result: Experiment result
            
        Returns:
            Metric value
        """
        metric = result.strategy_metrics.get(self.opt_config.optimization_metric, 0.0)
        
        # Handle NaN values
        if np.isnan(metric):
            return -np.inf if self.opt_config.optimization_direction == "maximize" else np.inf
        
        return metric
    
    def _find_best_result(self, results: List[Tuple[Dict[str, Any], float, ExperimentResult]]) -> Tuple[Dict[str, Any], float, ExperimentResult]:
        """
        Find the best result based on optimization metric
        
        Args:
            results: List of (params, metric, result) tuples
            
        Returns:
            Best (params, metric, result) tuple
        """
        if not results:
            raise ValueError("No valid results found")
        
        # Sort by metric
        if self.opt_config.optimization_direction == "maximize":
            results.sort(key=lambda x: x[1], reverse=True)
        else:
            results.sort(key=lambda x: x[1])
        
        return results[0]
    
    def _save_optimization_results(self, opt_result: OptimizationResult):
        """Save optimization results to files"""
        output_dir = Path(self.opt_config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save best configuration
        if self.opt_config.save_best_config:
            best_config_file = output_dir / "best_config.json"
            with open(best_config_file, 'w') as f:
                json.dump(opt_result.best_params, f, indent=2)
        
        # Save all results
        if self.opt_config.save_all_results:
            results_file = output_dir / "all_results.json"
            
            # Convert results to serializable format
            serializable_results = []
            for params, metric, result in opt_result.all_results:
                serializable_results.append({
                    'parameters': params,
                    'metric': metric,
                    'result_summary': {
                        'total_return': result.strategy_metrics.get('total_return', 0),
                        'sharpe_ratio': result.strategy_metrics.get('sharpe_ratio', 0),
                        'max_drawdown': result.strategy_metrics.get('max_drawdown', 0),
                        'total_trades': len(result.trades)
                    }
                })
            
            with open(results_file, 'w') as f:
                json.dump(serializable_results, f, indent=2)
        
        # Save optimization summary
        summary_file = output_dir / "optimization_summary.json"
        summary = {
            'optimization_config': {
                'optimization_metric': self.opt_config.optimization_metric,
                'optimization_direction': self.opt_config.optimization_direction,
                'search_method': self.opt_config.search_method,
                'max_iterations': self.opt_config.max_iterations,
                'n_jobs': self.opt_config.n_jobs
            },
            'results': {
                'best_params': opt_result.best_params,
                'best_metric': opt_result.best_metric,
                'total_combinations': opt_result.total_combinations,
                'completed_combinations': opt_result.completed_combinations,
                'success_rate': opt_result.success_rate,
                'duration_seconds': opt_result.duration
            }
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        self.logger.info(f"Optimization results saved to {output_dir}")
    
    def create_parameter_ranges(self, **ranges) -> Dict[str, List[Any]]:
        """
        Create parameter ranges for optimization
        
        Args:
            **ranges: Parameter ranges as keyword arguments
            
        Returns:
            Dictionary of parameter ranges
        """
        self.opt_config.parameter_ranges.update(ranges)
        return self.opt_config.parameter_ranges 