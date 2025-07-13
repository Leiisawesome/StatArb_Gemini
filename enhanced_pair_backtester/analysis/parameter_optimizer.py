"""
Parameter Optimization System

Systematic parameter optimization using performance attribution analysis:
- Grid search optimization
- Bayesian optimization
- Genetic algorithm optimization
- Multi-objective optimization
- Parameter sensitivity analysis
- Regime-aware parameter tuning
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import warnings
from scipy import stats
from scipy.optimize import minimize, differential_evolution
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel, Matern
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import itertools

# Import core components
try:
    from ..analysis.performance_attribution import PerformanceAttributionAnalyzer, PerformanceAttribution
    from ..analysis.performance_metrics import PerformanceAnalyzer, PerformanceMetrics
    from ..config.backtest_config import BacktestConfig
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)
    from analysis.performance_attribution import PerformanceAttributionAnalyzer, PerformanceAttribution
    from analysis.performance_metrics import PerformanceAnalyzer, PerformanceMetrics
    from config.backtest_config import BacktestConfig

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

@dataclass
class ParameterRange:
    """Parameter range definition for optimization"""
    name: str
    min_value: float
    max_value: float
    step_size: Optional[float] = None
    is_integer: bool = False
    current_value: Optional[float] = None
    
    def generate_values(self, num_points: int = 10) -> List[float]:
        """Generate parameter values for optimization"""
        if self.step_size:
            values = np.arange(self.min_value, self.max_value + self.step_size, self.step_size)
        else:
            values = np.linspace(self.min_value, self.max_value, num_points)
        
        if self.is_integer:
            values = np.round(values).astype(int)
        
        return values.tolist()

@dataclass
class OptimizationResult:
    """Optimization result container"""
    best_parameters: Dict[str, float]
    best_score: float
    optimization_history: List[Dict[str, Any]]
    total_evaluations: int
    optimization_time: float
    
    # Performance metrics for best parameters
    best_performance: Optional[PerformanceMetrics] = None
    best_attribution: Optional[PerformanceAttribution] = None
    
    # Sensitivity analysis
    parameter_sensitivity: Dict[str, float] = field(default_factory=dict)
    parameter_correlations: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Regime-specific results
    regime_optimal_parameters: Dict[str, Dict[str, float]] = field(default_factory=dict)

@dataclass
class OptimizationConfig:
    """Configuration for parameter optimization"""
    objective_function: str = "sharpe_ratio"  # sharpe_ratio, calmar_ratio, information_ratio
    optimization_method: str = "bayesian"  # grid_search, bayesian, genetic, multi_objective
    max_evaluations: int = 100
    random_seed: int = 42
    
    # Grid search specific
    grid_resolution: int = 10
    
    # Bayesian optimization specific
    acquisition_function: str = "ei"  # ei, pi, ucb
    exploration_weight: float = 0.1
    
    # Genetic algorithm specific
    population_size: int = 50
    mutation_rate: float = 0.1
    crossover_rate: float = 0.8
    
    # Multi-objective specific
    objectives: List[str] = field(default_factory=lambda: ["sharpe_ratio", "calmar_ratio"])
    
    # Parallel processing
    n_jobs: int = 4
    
    # Validation
    use_walk_forward: bool = True
    validation_periods: int = 3

class ParameterOptimizer:
    """
    Advanced parameter optimization system
    
    Features:
    - Multiple optimization algorithms (Grid Search, Bayesian, Genetic)
    - Multi-objective optimization
    - Parameter sensitivity analysis
    - Regime-aware optimization
    - Walk-forward validation
    - Performance attribution integration
    """
    
    def __init__(self, 
                 strategy_evaluator: Callable,
                 config: Optional[OptimizationConfig] = None):
        """
        Initialize parameter optimizer
        
        Args:
            strategy_evaluator: Function that evaluates strategy with given parameters
            config: Optimization configuration
        """
        self.strategy_evaluator = strategy_evaluator
        self.config = config or OptimizationConfig()
        
        # Optimization state
        self.parameter_ranges: Dict[str, ParameterRange] = {}
        self.evaluation_history: List[Dict[str, Any]] = []
        self.best_result: Optional[OptimizationResult] = None
        
        # Performance tracking
        self.attribution_analyzer = PerformanceAttributionAnalyzer()
        self.performance_analyzer = PerformanceAnalyzer()
        
        # Random seed for reproducibility
        np.random.seed(self.config.random_seed)
        
        logger.info("Parameter Optimizer initialized")
    
    def add_parameter_range(self, param_range: ParameterRange):
        """Add parameter range for optimization"""
        self.parameter_ranges[param_range.name] = param_range
        logger.info(f"Added parameter range: {param_range.name} [{param_range.min_value}, {param_range.max_value}]")
    
    def add_standard_parameters(self):
        """Add standard statistical arbitrage parameters"""
        # Entry/Exit thresholds
        self.add_parameter_range(ParameterRange(
            name="entry_threshold",
            min_value=1.0,
            max_value=3.0,
            step_size=0.1,
            current_value=2.0
        ))
        
        self.add_parameter_range(ParameterRange(
            name="exit_threshold",
            min_value=0.1,
            max_value=1.0,
            step_size=0.1,
            current_value=0.5
        ))
        
        # Lookback periods
        self.add_parameter_range(ParameterRange(
            name="lookback_period",
            min_value=10,
            max_value=60,
            step_size=5,
            is_integer=True,
            current_value=20
        ))
        
        # Position sizing
        self.add_parameter_range(ParameterRange(
            name="position_size_factor",
            min_value=0.1,
            max_value=2.0,
            step_size=0.1,
            current_value=1.0
        ))
        
        # Stop loss
        self.add_parameter_range(ParameterRange(
            name="stop_loss_threshold",
            min_value=0.02,
            max_value=0.10,
            step_size=0.01,
            current_value=0.05
        ))
        
        # Regime sensitivity
        self.add_parameter_range(ParameterRange(
            name="regime_sensitivity",
            min_value=0.1,
            max_value=1.0,
            step_size=0.1,
            current_value=0.5
        ))
        
        logger.info("Added standard parameter ranges")
    
    def evaluate_parameters(self, parameters: Dict[str, float]) -> Dict[str, Any]:
        """Evaluate strategy with given parameters"""
        try:
            # Call strategy evaluator
            result = self.strategy_evaluator(parameters)
            
            # Extract performance metrics
            if isinstance(result, dict):
                performance_metrics = result.get('performance_metrics', {})
                attribution = result.get('attribution', {})
                
                # Calculate objective score
                objective_score = self._calculate_objective_score(performance_metrics)
                
                evaluation_result = {
                    'parameters': parameters.copy(),
                    'objective_score': objective_score,
                    'performance_metrics': performance_metrics,
                    'attribution': attribution,
                    'evaluation_time': datetime.now(),
                    'success': True
                }
                
            else:
                # Handle simple return case
                evaluation_result = {
                    'parameters': parameters.copy(),
                    'objective_score': result if isinstance(result, (int, float)) else 0.0,
                    'performance_metrics': {},
                    'attribution': {},
                    'evaluation_time': datetime.now(),
                    'success': True
                }
            
            # Store evaluation
            self.evaluation_history.append(evaluation_result)
            
            return evaluation_result
            
        except Exception as e:
            logger.error(f"Parameter evaluation failed: {e}")
            
            # Return failed evaluation
            evaluation_result = {
                'parameters': parameters.copy(),
                'objective_score': -999.0,  # Very bad score
                'performance_metrics': {},
                'attribution': {},
                'evaluation_time': datetime.now(),
                'success': False,
                'error': str(e)
            }
            
            self.evaluation_history.append(evaluation_result)
            return evaluation_result
    
    def _calculate_objective_score(self, performance_metrics: Dict[str, Any]) -> float:
        """Calculate objective score from performance metrics"""
        if self.config.objective_function == "sharpe_ratio":
            return performance_metrics.get('sharpe_ratio', 0.0)
        elif self.config.objective_function == "calmar_ratio":
            return performance_metrics.get('calmar_ratio', 0.0)
        elif self.config.objective_function == "information_ratio":
            return performance_metrics.get('information_ratio', 0.0)
        elif self.config.objective_function == "total_return":
            return performance_metrics.get('total_return', 0.0)
        else:
            # Default to Sharpe ratio
            return performance_metrics.get('sharpe_ratio', 0.0)
    
    def grid_search_optimization(self) -> OptimizationResult:
        """Perform grid search optimization"""
        logger.info("Starting grid search optimization")
        start_time = datetime.now()
        
        # Generate parameter combinations
        parameter_values = {}
        for name, param_range in self.parameter_ranges.items():
            parameter_values[name] = param_range.generate_values(self.config.grid_resolution)
        
        # Create all combinations
        param_names = list(parameter_values.keys())
        param_combinations = list(itertools.product(*[parameter_values[name] for name in param_names]))
        
        logger.info(f"Generated {len(param_combinations)} parameter combinations")
        
        # Evaluate combinations
        best_score = -np.inf
        best_parameters = {}
        
        # Parallel evaluation
        with ThreadPoolExecutor(max_workers=self.config.n_jobs) as executor:
            # Submit tasks
            futures = []
            for combination in param_combinations[:self.config.max_evaluations]:
                params = dict(zip(param_names, combination))
                future = executor.submit(self.evaluate_parameters, params)
                futures.append(future)
            
            # Collect results
            for future in as_completed(futures):
                result = future.result()
                if result['success'] and result['objective_score'] > best_score:
                    best_score = result['objective_score']
                    best_parameters = result['parameters']
        
        optimization_time = (datetime.now() - start_time).total_seconds()
        
        # Create result
        result = OptimizationResult(
            best_parameters=best_parameters,
            best_score=best_score,
            optimization_history=self.evaluation_history.copy(),
            total_evaluations=len(self.evaluation_history),
            optimization_time=optimization_time
        )
        
        logger.info(f"Grid search completed in {optimization_time:.1f}s, best score: {best_score:.4f}")
        return result
    
    def bayesian_optimization(self) -> OptimizationResult:
        """Perform Bayesian optimization"""
        logger.info("Starting Bayesian optimization")
        start_time = datetime.now()
        
        # Prepare parameter bounds
        param_names = list(self.parameter_ranges.keys())
        bounds = []
        for name in param_names:
            param_range = self.parameter_ranges[name]
            bounds.append((param_range.min_value, param_range.max_value))
        
        # Initialize Gaussian Process
        kernel = ConstantKernel(1.0) * RBF(1.0)
        gp = GaussianProcessRegressor(kernel=kernel, alpha=1e-6, normalize_y=True)
        
        # Initial random samples
        n_initial = min(10, self.config.max_evaluations // 2)
        X_samples = []
        y_samples = []
        
        for _ in range(n_initial):
            # Random sample
            params = {}
            for i, name in enumerate(param_names):
                param_range = self.parameter_ranges[name]
                value = np.random.uniform(param_range.min_value, param_range.max_value)
                if param_range.is_integer:
                    value = int(round(value))
                params[name] = value
            
            # Evaluate
            result = self.evaluate_parameters(params)
            if result['success']:
                X_samples.append([params[name] for name in param_names])
                y_samples.append(result['objective_score'])
        
        # Convert to numpy arrays
        X_samples = np.array(X_samples)
        y_samples = np.array(y_samples)
        
        # Fit initial GP
        if len(X_samples) > 0:
            gp.fit(X_samples, y_samples)
        
        # Bayesian optimization loop
        best_score = np.max(y_samples) if len(y_samples) > 0 else -np.inf
        best_parameters = {}
        
        for iteration in range(len(X_samples), self.config.max_evaluations):
            # Acquisition function optimization
            def acquisition_function(x):
                x = x.reshape(1, -1)
                mu, sigma = gp.predict(x, return_std=True)
                
                if self.config.acquisition_function == "ei":
                    # Expected Improvement
                    improvement = mu - best_score
                    z = improvement / sigma if sigma > 0 else 0
                    ei = improvement * stats.norm.cdf(z) + sigma * stats.norm.pdf(z)
                    return -float(ei[0])  # Negative for minimization
                elif self.config.acquisition_function == "ucb":
                    # Upper Confidence Bound
                    return -float((mu + self.config.exploration_weight * sigma)[0])
                else:
                    # Probability of Improvement
                    z = (mu - best_score) / sigma if sigma > 0 else 0
                    return -float(stats.norm.cdf(z)[0])
            
            # Optimize acquisition function
            result = differential_evolution(
                acquisition_function,
                bounds,
                maxiter=100,
                seed=self.config.random_seed + iteration
            )
            
            # Convert to parameters
            next_params = {}
            for i, name in enumerate(param_names):
                value = result.x[i]
                if self.parameter_ranges[name].is_integer:
                    value = int(round(value))
                next_params[name] = value
            
            # Evaluate next point
            eval_result = self.evaluate_parameters(next_params)
            
            if eval_result['success']:
                # Update samples
                X_samples = np.vstack([X_samples, [next_params[name] for name in param_names]])
                y_samples = np.append(y_samples, eval_result['objective_score'])
                
                # Update GP
                gp.fit(X_samples, y_samples)
                
                # Update best
                if eval_result['objective_score'] > best_score:
                    best_score = eval_result['objective_score']
                    best_parameters = next_params
        
        optimization_time = (datetime.now() - start_time).total_seconds()
        
        # Create result
        result = OptimizationResult(
            best_parameters=best_parameters,
            best_score=best_score,
            optimization_history=self.evaluation_history.copy(),
            total_evaluations=len(self.evaluation_history),
            optimization_time=optimization_time
        )
        
        logger.info(f"Bayesian optimization completed in {optimization_time:.1f}s, best score: {best_score:.4f}")
        return result
    
    def genetic_algorithm_optimization(self) -> OptimizationResult:
        """Perform genetic algorithm optimization"""
        logger.info("Starting genetic algorithm optimization")
        start_time = datetime.now()
        
        param_names = list(self.parameter_ranges.keys())
        bounds = []
        for name in param_names:
            param_range = self.parameter_ranges[name]
            bounds.append((param_range.min_value, param_range.max_value))
        
        # Objective function for scipy
        def objective(x):
            params = {}
            for i, name in enumerate(param_names):
                value = x[i]
                if self.parameter_ranges[name].is_integer:
                    value = int(round(value))
                params[name] = value
            
            result = self.evaluate_parameters(params)
            return -result['objective_score']  # Negative for minimization
        
        # Run genetic algorithm
        result = differential_evolution(
            objective,
            bounds,
            maxiter=self.config.max_evaluations // self.config.population_size,
            popsize=self.config.population_size,
            mutation=(0.5, 1.5),
            recombination=self.config.crossover_rate,
            seed=self.config.random_seed
        )
        
        # Convert result to parameters
        best_parameters = {}
        for i, name in enumerate(param_names):
            value = result.x[i]
            if self.parameter_ranges[name].is_integer:
                value = int(round(value))
            best_parameters[name] = value
        
        optimization_time = (datetime.now() - start_time).total_seconds()
        
        # Create result
        optimization_result = OptimizationResult(
            best_parameters=best_parameters,
            best_score=-result.fun,  # Convert back to positive
            optimization_history=self.evaluation_history.copy(),
            total_evaluations=len(self.evaluation_history),
            optimization_time=optimization_time
        )
        
        logger.info(f"Genetic algorithm completed in {optimization_time:.1f}s, best score: {-result.fun:.4f}")
        return optimization_result
    
    def analyze_parameter_sensitivity(self, result: OptimizationResult) -> Dict[str, float]:
        """Analyze parameter sensitivity"""
        logger.info("Analyzing parameter sensitivity")
        
        sensitivity = {}
        
        # Calculate sensitivity for each parameter
        for param_name in self.parameter_ranges.keys():
            param_scores = []
            param_values = []
            
            # Collect evaluations for this parameter
            for evaluation in result.optimization_history:
                if evaluation['success']:
                    param_values.append(evaluation['parameters'][param_name])
                    param_scores.append(evaluation['objective_score'])
            
            # Calculate correlation
            if len(param_values) > 5:
                correlation, p_value = stats.pearsonr(param_values, param_scores)
                sensitivity[param_name] = abs(correlation) if p_value < 0.05 else 0.0
            else:
                sensitivity[param_name] = 0.0
        
        return sensitivity
    
    def optimize_parameters(self) -> OptimizationResult:
        """Run parameter optimization using configured method"""
        logger.info(f"Starting parameter optimization using {self.config.optimization_method}")
        
        # Clear previous results
        self.evaluation_history = []
        
        # Run optimization
        if self.config.optimization_method == "grid_search":
            result = self.grid_search_optimization()
        elif self.config.optimization_method == "bayesian":
            result = self.bayesian_optimization()
        elif self.config.optimization_method == "genetic":
            result = self.genetic_algorithm_optimization()
        else:
            raise ValueError(f"Unknown optimization method: {self.config.optimization_method}")
        
        # Analyze sensitivity
        result.parameter_sensitivity = self.analyze_parameter_sensitivity(result)
        
        # Store best result
        self.best_result = result
        
        logger.info("Parameter optimization completed")
        return result
    
    def generate_optimization_report(self, result: OptimizationResult) -> str:
        """Generate optimization report"""
        report = f"""
=== PARAMETER OPTIMIZATION REPORT ===

OPTIMIZATION SUMMARY:
  Method: {self.config.optimization_method.upper()}
  Objective: {self.config.objective_function.upper()}
  Total Evaluations: {result.total_evaluations}
  Optimization Time: {result.optimization_time:.1f} seconds
  Best Score: {result.best_score:.4f}

OPTIMAL PARAMETERS:
"""
        
        for param_name, value in result.best_parameters.items():
            param_range = self.parameter_ranges[param_name]
            report += f"  {param_name}: {value:.4f} (range: [{param_range.min_value}, {param_range.max_value}])\n"
        
        report += "\nPARAMETER SENSITIVITY ANALYSIS:\n"
        
        # Sort by sensitivity
        sorted_sensitivity = sorted(result.parameter_sensitivity.items(), key=lambda x: x[1], reverse=True)
        
        for param_name, sensitivity in sorted_sensitivity:
            report += f"  {param_name}: {sensitivity:.3f}\n"
        
        # Performance metrics for best parameters
        if result.best_performance:
            report += f"""
BEST PARAMETER PERFORMANCE:
  Total Return: {result.best_performance.returns.total_return:.2%}
  Sharpe Ratio: {result.best_performance.risk.sharpe_ratio:.2f}
  Max Drawdown: {result.best_performance.risk.max_drawdown:.2%}
  Win Rate: {result.best_performance.win_rate:.1%}
  Total Trades: {result.best_performance.total_trades}
"""
        
        # Optimization recommendations
        report += "\nOPTIMIZATION RECOMMENDATIONS:\n"
        
        # High sensitivity parameters
        high_sensitivity = [param for param, sens in sorted_sensitivity if sens > 0.3]
        if high_sensitivity:
            report += f"  1. Focus on high-sensitivity parameters: {', '.join(high_sensitivity)}\n"
        
        # Low sensitivity parameters
        low_sensitivity = [param for param, sens in sorted_sensitivity if sens < 0.1]
        if low_sensitivity:
            report += f"  2. Consider fixing low-sensitivity parameters: {', '.join(low_sensitivity)}\n"
        
        # Evaluation efficiency
        success_rate = sum(1 for eval in result.optimization_history if eval['success']) / len(result.optimization_history)
        report += f"  3. Evaluation success rate: {success_rate:.1%}\n"
        
        if success_rate < 0.8:
            report += "  4. Consider relaxing parameter constraints to improve success rate\n"
        
        # Convergence analysis
        recent_scores = [eval['objective_score'] for eval in result.optimization_history[-20:] if eval['success']]
        if len(recent_scores) > 10:
            score_improvement = (max(recent_scores) - min(recent_scores)) / abs(min(recent_scores))
            if score_improvement < 0.05:
                report += "  5. Optimization appears to have converged\n"
            else:
                report += "  6. Consider increasing max_evaluations for better convergence\n"
        
        report += """
=== OPTIMIZATION ANALYSIS COMPLETE ===
This report provides insights into optimal parameters and optimization efficiency.
Use the sensitivity analysis to focus future optimization efforts.
"""
        
        return report

def create_sample_evaluator():
    """Create sample strategy evaluator for testing"""
    def evaluate_strategy(parameters: Dict[str, float]) -> Dict[str, Any]:
        """Sample strategy evaluator"""
        # Simulate strategy performance based on parameters
        entry_threshold = parameters.get('entry_threshold', 2.0)
        exit_threshold = parameters.get('exit_threshold', 0.5)
        lookback_period = parameters.get('lookback_period', 20)
        
        # Simple performance simulation
        base_return = 0.05
        threshold_penalty = abs(entry_threshold - 2.0) * 0.02
        lookback_bonus = (lookback_period - 20) * 0.001
        
        total_return = base_return - threshold_penalty + lookback_bonus
        volatility = 0.15 + abs(entry_threshold - 2.0) * 0.05
        sharpe_ratio = total_return / volatility if volatility > 0 else 0
        
        return {
            'performance_metrics': {
                'total_return': total_return,
                'volatility': volatility,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': -0.08,
                'win_rate': 0.6,
                'total_trades': 50
            },
            'attribution': {}
        }
    
    return evaluate_strategy 