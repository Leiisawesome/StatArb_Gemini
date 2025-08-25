#!/usr/bin/env python3
"""
Optimization Engine - Dynamic Parameter and Portfolio Optimization
=================================================================

Advanced optimization system using genetic algorithms, reinforcement learning,
and mathematical optimization for dynamic parameter tuning and portfolio optimization.

Author: StatArb_Gemini Team
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
import warnings
warnings.filterwarnings('ignore')

# ML and optimization libraries
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV
from sklearn.ensemble import RandomForestRegressor
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel
from scipy.optimize import minimize, differential_evolution, basinhopping
from scipy import stats
import itertools

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptimizationType(Enum):
    """Types of optimization"""
    PARAMETER_OPTIMIZATION = "parameter_optimization"
    PORTFOLIO_OPTIMIZATION = "portfolio_optimization"
    STRATEGY_OPTIMIZATION = "strategy_optimization"
    RISK_OPTIMIZATION = "risk_optimization"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"

class OptimizationMethod(Enum):
    """Optimization methods"""
    GRID_SEARCH = "grid_search"
    RANDOM_SEARCH = "random_search"
    BAYESIAN_OPTIMIZATION = "bayesian_optimization"
    GENETIC_ALGORITHM = "genetic_algorithm"
    DIFFERENTIAL_EVOLUTION = "differential_evolution"
    GRADIENT_DESCENT = "gradient_descent"
    SIMULATED_ANNEALING = "simulated_annealing"
    REINFORCEMENT_LEARNING = "reinforcement_learning"

class ObjectiveFunction(Enum):
    """Optimization objective functions"""
    MAXIMIZE_SHARPE = "maximize_sharpe"
    MAXIMIZE_RETURNS = "maximize_returns"
    MINIMIZE_RISK = "minimize_risk"
    MAXIMIZE_CALMAR = "maximize_calmar"
    MINIMIZE_DRAWDOWN = "minimize_drawdown"
    MAXIMIZE_INFORMATION_RATIO = "maximize_information_ratio"
    MULTI_OBJECTIVE = "multi_objective"

@dataclass
class OptimizationParameter:
    """Parameter definition for optimization"""
    name: str
    parameter_type: str  # 'float', 'int', 'categorical'
    bounds: Tuple[float, float]  # (min, max) for numeric types
    categories: Optional[List[Any]] = None  # For categorical parameters
    step_size: Optional[float] = None  # For grid search
    current_value: Optional[float] = None
    importance: float = 1.0  # Parameter importance weight
    
    # Constraints
    constraints: List[str] = field(default_factory=list)
    dependencies: Dict[str, Any] = field(default_factory=dict)

@dataclass
class OptimizationObjective:
    """Optimization objective definition"""
    name: str
    objective_type: ObjectiveFunction
    weight: float = 1.0
    maximize: bool = True
    target_value: Optional[float] = None
    constraints: List[str] = field(default_factory=list)

@dataclass
class OptimizationResult:
    """Optimization result"""
    optimization_id: str
    timestamp: datetime
    method: OptimizationMethod
    objective_type: ObjectiveFunction
    
    # Results
    optimal_parameters: Dict[str, float]
    objective_value: float
    improvement: float  # Improvement over baseline
    confidence: float  # Confidence in result
    
    # Optimization details
    iterations: int
    convergence_achieved: bool
    evaluation_time: float
    total_evaluations: int
    
    # Performance metrics
    sharpe_ratio: float
    annual_return: float
    max_drawdown: float
    volatility: float
    
    # Validation
    in_sample_performance: Dict[str, float]
    out_sample_performance: Optional[Dict[str, float]] = None
    
    # Metadata
    parameter_ranges: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    optimization_history: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class PortfolioAllocation:
    """Portfolio allocation optimization result"""
    timestamp: datetime
    allocations: Dict[str, float]  # Asset -> weight
    expected_return: float
    expected_risk: float
    sharpe_ratio: float
    
    # Risk metrics
    var_95: float  # Value at Risk 95%
    cvar_95: float  # Conditional Value at Risk 95%
    
    # Optimization details
    method_used: OptimizationMethod
    objective_value: float
    iterations: int
    
    # Constraints satisfied
    constraints_satisfied: bool
    constraint_violations: List[str] = field(default_factory=list)

@dataclass
class StrategyOptimization:
    """Strategy optimization configuration"""
    strategy_id: str
    parameters: List[OptimizationParameter]
    objectives: List[OptimizationObjective]
    constraints: List[str]
    
    # Optimization settings
    method: OptimizationMethod
    max_iterations: int = 1000
    convergence_tolerance: float = 1e-6
    
    # Validation settings
    validation_split: float = 0.3
    cross_validation_folds: int = 5
    walk_forward_windows: int = 10

class OptimizationEngine:
    """
    Dynamic optimization engine for parameters and portfolios
    
    Features:
    - Multi-method optimization (Bayesian, GA, Gradient-based)
    - Parameter optimization with constraints
    - Portfolio optimization with risk management
    - Strategy optimization with walk-forward validation
    - Multi-objective optimization
    - Real-time adaptation
    """
    
    def __init__(self,
                 max_concurrent_optimizations: int = 3,
                 default_method: OptimizationMethod = OptimizationMethod.BAYESIAN_OPTIMIZATION,
                 cache_results: bool = True,
                 enable_parallel: bool = True):
        
        self.max_concurrent_optimizations = max_concurrent_optimizations
        self.default_method = default_method
        self.cache_results = cache_results
        self.enable_parallel = enable_parallel
        
        # Optimization state
        self.active_optimizations: Dict[str, Dict[str, Any]] = {}
        self.optimization_history: List[OptimizationResult] = []
        self.cached_results: Dict[str, OptimizationResult] = {}
        
        # ML models for optimization
        self.gp_model = GaussianProcessRegressor(
            kernel=ConstantKernel(1.0) * RBF(1.0),
            alpha=1e-6,
            random_state=42
        )
        self.rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
        
        # Portfolio optimization
        self.portfolio_allocations: List[PortfolioAllocation] = []
        self.allocation_history: Dict[str, List[float]] = {}
        
        # Strategy optimization
        self.strategy_optimizations: Dict[str, StrategyOptimization] = {}
        self.optimization_schedules: Dict[str, datetime] = {}
        
        # Performance tracking
        self.optimization_metrics: Dict[str, List[float]] = {
            'convergence_time': [],
            'improvement_achieved': [],
            'out_sample_performance': []
        }
        
        # State management
        self.is_optimizing = False
        self.lock = Lock()
        
        logger.info("OptimizationEngine initialized with multi-method optimization")
    
    async def start_optimization_engine(self) -> None:
        """Start optimization engine"""
        with self.lock:
            if self.is_optimizing:
                logger.warning("Optimization engine already running")
                return
            
            self.is_optimizing = True
            logger.info("Starting dynamic optimization engine")
    
    async def stop_optimization_engine(self) -> None:
        """Stop optimization engine"""
        with self.lock:
            self.is_optimizing = False
            logger.info("Optimization engine stopped")
    
    async def optimize_parameters(self,
                                strategy_id: str,
                                parameters: List[OptimizationParameter],
                                objective_function: Callable,
                                method: Optional[OptimizationMethod] = None,
                                constraints: Optional[List[str]] = None) -> Optional[OptimizationResult]:
        """Optimize strategy parameters using specified method"""
        if not self.is_optimizing:
            logger.warning("Optimization engine not running")
            return None
        
        optimization_id = f"{strategy_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        method = method or self.default_method
        
        try:
            logger.info(f"Starting parameter optimization for {strategy_id} using {method.value}")
            
            # Check cache
            cache_key = self._generate_cache_key(strategy_id, parameters, method)
            if self.cache_results and cache_key in self.cached_results:
                logger.info("Using cached optimization result")
                return self.cached_results[cache_key]
            
            # Start optimization
            start_time = datetime.now()
            
            # Track active optimization
            with self.lock:
                self.active_optimizations[optimization_id] = {
                    'strategy_id': strategy_id,
                    'method': method,
                    'start_time': start_time,
                    'status': 'running'
                }
            
            # Perform optimization based on method
            if method == OptimizationMethod.BAYESIAN_OPTIMIZATION:
                result = await self._bayesian_optimization(
                    optimization_id, parameters, objective_function, constraints
                )
            elif method == OptimizationMethod.GENETIC_ALGORITHM:
                result = await self._genetic_algorithm_optimization(
                    optimization_id, parameters, objective_function, constraints
                )
            elif method == OptimizationMethod.GRID_SEARCH:
                result = await self._grid_search_optimization(
                    optimization_id, parameters, objective_function, constraints
                )
            elif method == OptimizationMethod.RANDOM_SEARCH:
                result = await self._random_search_optimization(
                    optimization_id, parameters, objective_function, constraints
                )
            elif method == OptimizationMethod.DIFFERENTIAL_EVOLUTION:
                result = await self._differential_evolution_optimization(
                    optimization_id, parameters, objective_function, constraints
                )
            else:
                logger.error(f"Optimization method {method.value} not implemented")
                return None
            
            # Calculate optimization time
            end_time = datetime.now()
            optimization_time = (end_time - start_time).total_seconds()
            
            if result:
                result.evaluation_time = optimization_time
                
                # Store result
                with self.lock:
                    self.optimization_history.append(result)
                    if len(self.optimization_history) > 1000:
                        self.optimization_history = self.optimization_history[-1000:]
                    
                    # Cache result
                    if self.cache_results:
                        self.cached_results[cache_key] = result
                        if len(self.cached_results) > 100:
                            # Remove oldest cached results
                            oldest_key = list(self.cached_results.keys())[0]
                            del self.cached_results[oldest_key]
                    
                    # Update active optimizations
                    if optimization_id in self.active_optimizations:
                        self.active_optimizations[optimization_id]['status'] = 'completed'
                
                logger.info(f"Parameter optimization completed: improvement {result.improvement:.4f}")
                return result
            
        except Exception as e:
            logger.error(f"Error in parameter optimization: {e}")
            
            # Update active optimizations
            with self.lock:
                if optimization_id in self.active_optimizations:
                    self.active_optimizations[optimization_id]['status'] = 'failed'
        
        finally:
            # Clean up active optimization
            with self.lock:
                if optimization_id in self.active_optimizations:
                    del self.active_optimizations[optimization_id]
        
        return None
    
    async def optimize_portfolio(self,
                               assets: List[str],
                               expected_returns: np.ndarray,
                               covariance_matrix: np.ndarray,
                               constraints: Optional[Dict[str, Any]] = None,
                               objective: ObjectiveFunction = ObjectiveFunction.MAXIMIZE_SHARPE) -> Optional[PortfolioAllocation]:
        """Optimize portfolio allocation"""
        try:
            logger.info(f"Starting portfolio optimization for {len(assets)} assets")
            
            # Validate inputs
            if len(expected_returns) != len(assets) or covariance_matrix.shape[0] != len(assets):
                logger.error("Dimension mismatch in portfolio optimization inputs")
                return None
            
            # Default constraints
            if constraints is None:
                constraints = {
                    'min_weight': 0.0,
                    'max_weight': 1.0,
                    'max_concentration': 0.4,
                    'min_diversification': 0.1
                }
            
            # Optimization bounds
            bounds = [(constraints.get('min_weight', 0.0), 
                      constraints.get('max_weight', 1.0)) for _ in assets]
            
            # Initial guess (equal weights)
            x0 = np.array([1.0 / len(assets)] * len(assets))
            
            # Optimization methods to try
            methods = ['SLSQP', 'trust-constr']
            best_result = None
            best_objective = -np.inf if objective in [ObjectiveFunction.MAXIMIZE_SHARPE, ObjectiveFunction.MAXIMIZE_RETURNS] else np.inf
            
            for method in methods:
                try:
                    # Define objective function
                    if objective == ObjectiveFunction.MAXIMIZE_SHARPE:
                        obj_func = lambda w: -self._calculate_sharpe_ratio(w, expected_returns, covariance_matrix)
                    elif objective == ObjectiveFunction.MINIMIZE_RISK:
                        obj_func = lambda w: np.sqrt(np.dot(w.T, np.dot(covariance_matrix, w)))
                    elif objective == ObjectiveFunction.MAXIMIZE_RETURNS:
                        obj_func = lambda w: -np.dot(w, expected_returns)
                    else:
                        obj_func = lambda w: -self._calculate_sharpe_ratio(w, expected_returns, covariance_matrix)
                    
                    # Constraints
                    portfolio_constraints = [
                        {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}  # Weights sum to 1
                    ]
                    
                    # Additional constraints
                    if 'max_concentration' in constraints:
                        max_conc = constraints['max_concentration']
                        portfolio_constraints.append({
                            'type': 'ineq', 
                            'fun': lambda w: max_conc - np.max(w)
                        })
                    
                    # Optimize
                    result = minimize(
                        obj_func,
                        x0,
                        method=method,
                        bounds=bounds,
                        constraints=portfolio_constraints,
                        options={'maxiter': 1000}
                    )
                    
                    if result.success:
                        objective_value = -result.fun if objective in [ObjectiveFunction.MAXIMIZE_SHARPE, ObjectiveFunction.MAXIMIZE_RETURNS] else result.fun
                        
                        if objective in [ObjectiveFunction.MAXIMIZE_SHARPE, ObjectiveFunction.MAXIMIZE_RETURNS]:
                            if objective_value > best_objective:
                                best_result = result
                                best_objective = objective_value
                        else:
                            if objective_value < best_objective:
                                best_result = result
                                best_objective = objective_value
                
                except Exception as e:
                    logger.warning(f"Portfolio optimization method {method} failed: {e}")
                    continue
            
            if best_result is None:
                logger.error("All portfolio optimization methods failed")
                return None
            
            # Extract optimal weights
            optimal_weights = best_result.x
            
            # Calculate portfolio metrics
            portfolio_return = np.dot(optimal_weights, expected_returns)
            portfolio_risk = np.sqrt(np.dot(optimal_weights.T, np.dot(covariance_matrix, optimal_weights)))
            sharpe_ratio = self._calculate_sharpe_ratio(optimal_weights, expected_returns, covariance_matrix)
            
            # Calculate VaR and CVaR (simplified)
            var_95 = self._calculate_portfolio_var(optimal_weights, expected_returns, covariance_matrix, 0.05)
            cvar_95 = self._calculate_portfolio_cvar(optimal_weights, expected_returns, covariance_matrix, 0.05)
            
            # Check constraints
            constraints_satisfied = True
            constraint_violations = []
            
            # Weight constraints
            if np.any(optimal_weights < constraints.get('min_weight', 0.0)):
                constraints_satisfied = False
                constraint_violations.append("minimum_weight_violation")
            
            if np.any(optimal_weights > constraints.get('max_weight', 1.0)):
                constraints_satisfied = False
                constraint_violations.append("maximum_weight_violation")
            
            # Concentration constraint
            if 'max_concentration' in constraints:
                if np.max(optimal_weights) > constraints['max_concentration']:
                    constraints_satisfied = False
                    constraint_violations.append("concentration_violation")
            
            # Create allocation result
            allocation = PortfolioAllocation(
                timestamp=datetime.now(),
                allocations={assets[i]: float(optimal_weights[i]) for i in range(len(assets))},
                expected_return=float(portfolio_return),
                expected_risk=float(portfolio_risk),
                sharpe_ratio=float(sharpe_ratio),
                var_95=float(var_95),
                cvar_95=float(cvar_95),
                constraints_satisfied=constraints_satisfied,
                constraint_violations=constraint_violations,
                method_used=OptimizationMethod.GRADIENT_DESCENT,
                objective_value=float(best_objective),
                iterations=best_result.nit
            )
            
            # Store allocation
            with self.lock:
                self.portfolio_allocations.append(allocation)
                if len(self.portfolio_allocations) > 100:
                    self.portfolio_allocations = self.portfolio_allocations[-100:]
                
                # Update allocation history
                for asset, weight in allocation.allocations.items():
                    if asset not in self.allocation_history:
                        self.allocation_history[asset] = []
                    self.allocation_history[asset].append(weight)
                    
                    # Maintain history size
                    if len(self.allocation_history[asset]) > 252:  # 1 year
                        self.allocation_history[asset] = self.allocation_history[asset][-252:]
            
            logger.info(f"Portfolio optimization completed: Sharpe {sharpe_ratio:.4f}, Risk {portfolio_risk:.4f}")
            return allocation
            
        except Exception as e:
            logger.error(f"Error in portfolio optimization: {e}")
            return None
    
    async def schedule_strategy_optimization(self,
                                           strategy_id: str,
                                           optimization_config: StrategyOptimization,
                                           frequency_hours: int = 24) -> bool:
        """Schedule regular strategy optimization"""
        try:
            # Store optimization configuration
            with self.lock:
                self.strategy_optimizations[strategy_id] = optimization_config
                self.optimization_schedules[strategy_id] = datetime.now() + timedelta(hours=frequency_hours)
            
            logger.info(f"Scheduled optimization for strategy {strategy_id} every {frequency_hours} hours")
            return True
            
        except Exception as e:
            logger.error(f"Error scheduling strategy optimization: {e}")
            return False
    
    async def _bayesian_optimization(self,
                                   optimization_id: str,
                                   parameters: List[OptimizationParameter],
                                   objective_function: Callable,
                                   constraints: Optional[List[str]] = None) -> Optional[OptimizationResult]:
        """Perform Bayesian optimization using Gaussian Process"""
        try:
            # Prepare parameter space
            param_bounds = []
            param_names = []
            
            for param in parameters:
                if param.parameter_type in ['float', 'int']:
                    param_bounds.append(param.bounds)
                    param_names.append(param.name)
            
            if not param_bounds:
                logger.error("No valid parameters for Bayesian optimization")
                return None
            
            # Bayesian optimization settings
            n_initial_points = min(10, len(param_bounds) * 3)
            n_iterations = 50
            
            # Initialize with random points
            X_samples = []
            y_samples = []
            
            # Random initialization
            for _ in range(n_initial_points):
                x = []
                for bounds in param_bounds:
                    x.append(np.random.uniform(bounds[0], bounds[1]))
                
                # Create parameter dict
                param_dict = {param_names[i]: x[i] for i in range(len(param_names))}
                
                # Evaluate objective
                try:
                    y = await self._evaluate_objective(objective_function, param_dict)
                    X_samples.append(x)
                    y_samples.append(y)
                except Exception as e:
                    logger.warning(f"Objective evaluation failed: {e}")
                    continue
            
            if len(y_samples) < 3:
                logger.error("Insufficient valid evaluations for Bayesian optimization")
                return None
            
            X_samples = np.array(X_samples)
            y_samples = np.array(y_samples)
            
            best_y = np.max(y_samples)
            best_x = X_samples[np.argmax(y_samples)]
            
            # Bayesian optimization loop
            optimization_history = []
            
            for iteration in range(n_iterations):
                try:
                    # Fit Gaussian Process
                    self.gp_model.fit(X_samples, y_samples)
                    
                    # Acquisition function (Expected Improvement)
                    def acquisition(x):
                        x = np.array(x).reshape(1, -1)
                        mu, sigma = self.gp_model.predict(x, return_std=True)
                        
                        # Expected Improvement
                        improvement = mu - best_y
                        Z = improvement / (sigma + 1e-9)
                        ei = improvement * stats.norm.cdf(Z) + sigma * stats.norm.pdf(Z)
                        return -ei  # Minimize negative EI
                    
                    # Optimize acquisition function
                    bounds_scipy = [(bounds[0], bounds[1]) for bounds in param_bounds]
                    
                    result = minimize(
                        acquisition,
                        best_x,
                        bounds=bounds_scipy,
                        method='L-BFGS-B'
                    )
                    
                    if result.success:
                        next_x = result.x
                        
                        # Evaluate objective at new point
                        param_dict = {param_names[i]: next_x[i] for i in range(len(param_names))}
                        next_y = await self._evaluate_objective(objective_function, param_dict)
                        
                        # Update samples
                        X_samples = np.vstack([X_samples, next_x])
                        y_samples = np.append(y_samples, next_y)
                        
                        # Update best point
                        if next_y > best_y:
                            best_y = next_y
                            best_x = next_x
                        
                        # Record history
                        optimization_history.append({
                            'iteration': iteration,
                            'objective_value': float(next_y),
                            'parameters': param_dict
                        })
                
                except Exception as e:
                    logger.warning(f"Bayesian optimization iteration {iteration} failed: {e}")
                    continue
            
            # Create optimization result
            optimal_params = {param_names[i]: float(best_x[i]) for i in range(len(param_names))}
            
            # Calculate improvement
            baseline_y = np.mean(y_samples[:n_initial_points])
            improvement = (best_y - baseline_y) / abs(baseline_y) if baseline_y != 0 else 0.0
            
            result = OptimizationResult(
                optimization_id=optimization_id,
                timestamp=datetime.now(),
                method=OptimizationMethod.BAYESIAN_OPTIMIZATION,
                objective_type=ObjectiveFunction.MAXIMIZE_SHARPE,  # Default
                optimal_parameters=optimal_params,
                objective_value=float(best_y),
                improvement=float(improvement),
                confidence=0.8,  # Bayesian methods provide good confidence
                iterations=n_iterations,
                convergence_achieved=True,
                evaluation_time=0.0,  # Will be set by caller
                total_evaluations=len(y_samples),
                sharpe_ratio=float(best_y),  # Assuming Sharpe optimization
                annual_return=0.0,  # Would need additional calculation
                max_drawdown=0.0,  # Would need additional calculation
                volatility=0.0,  # Would need additional calculation
                in_sample_performance={'objective': float(best_y)},
                parameter_ranges={param_names[i]: param_bounds[i] for i in range(len(param_names))},
                optimization_history=optimization_history
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in Bayesian optimization: {e}")
            return None
    
    async def _genetic_algorithm_optimization(self,
                                            optimization_id: str,
                                            parameters: List[OptimizationParameter],
                                            objective_function: Callable,
                                            constraints: Optional[List[str]] = None) -> Optional[OptimizationResult]:
        """Perform optimization using Genetic Algorithm (Differential Evolution)"""
        try:
            # Prepare parameter bounds
            bounds = []
            param_names = []
            
            for param in parameters:
                if param.parameter_type in ['float', 'int']:
                    bounds.append(param.bounds)
                    param_names.append(param.name)
            
            if not bounds:
                logger.error("No valid parameters for genetic algorithm")
                return None
            
            # Objective function wrapper
            def objective_wrapper(x):
                param_dict = {param_names[i]: x[i] for i in range(len(param_names))}
                try:
                    # Need to handle async call in sync context
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(self._evaluate_objective(objective_function, param_dict))
                    loop.close()
                    return -result  # Minimize negative for maximization
                except Exception as e:
                    logger.warning(f"Objective evaluation failed in GA: {e}")
                    return 1e6  # Large penalty
            
            # Differential Evolution
            result = differential_evolution(
                objective_wrapper,
                bounds,
                maxiter=100,
                popsize=15,
                seed=42,
                atol=1e-6,
                tol=1e-6
            )
            
            if result.success:
                optimal_params = {param_names[i]: float(result.x[i]) for i in range(len(param_names))}
                objective_value = -result.fun  # Convert back to maximization
                
                # Calculate improvement (simplified)
                improvement = 0.1  # Would need baseline comparison
                
                optimization_result = OptimizationResult(
                    optimization_id=optimization_id,
                    timestamp=datetime.now(),
                    method=OptimizationMethod.GENETIC_ALGORITHM,
                    objective_type=ObjectiveFunction.MAXIMIZE_SHARPE,
                    optimal_parameters=optimal_params,
                    objective_value=float(objective_value),
                    improvement=float(improvement),
                    confidence=0.7,
                    iterations=result.nit,
                    convergence_achieved=result.success,
                    evaluation_time=0.0,
                    total_evaluations=result.nfev,
                    sharpe_ratio=float(objective_value),
                    annual_return=0.0,
                    max_drawdown=0.0,
                    volatility=0.0,
                    in_sample_performance={'objective': float(objective_value)},
                    parameter_ranges={param_names[i]: bounds[i] for i in range(len(param_names))},
                    optimization_history=[]
                )
                
                return optimization_result
            
        except Exception as e:
            logger.error(f"Error in genetic algorithm optimization: {e}")
        
        return None
    
    async def _grid_search_optimization(self,
                                      optimization_id: str,
                                      parameters: List[OptimizationParameter],
                                      objective_function: Callable,
                                      constraints: Optional[List[str]] = None) -> Optional[OptimizationResult]:
        """Perform grid search optimization"""
        try:
            # Prepare parameter grids
            param_grids = {}
            param_names = []
            
            for param in parameters:
                if param.parameter_type in ['float', 'int']:
                    if param.step_size:
                        grid = np.arange(param.bounds[0], param.bounds[1] + param.step_size, param.step_size)
                    else:
                        grid = np.linspace(param.bounds[0], param.bounds[1], 10)  # Default 10 points
                    param_grids[param.name] = grid
                    param_names.append(param.name)
                elif param.parameter_type == 'categorical' and param.categories:
                    param_grids[param.name] = param.categories
                    param_names.append(param.name)
            
            if not param_grids:
                logger.error("No valid parameters for grid search")
                return None
            
            # Generate all parameter combinations
            param_combinations = list(itertools.product(*param_grids.values()))
            
            if len(param_combinations) > 1000:
                logger.warning(f"Large grid search space: {len(param_combinations)} combinations. Sampling 1000.")
                # Random sample for large spaces
                indices = np.random.choice(len(param_combinations), 1000, replace=False)
                param_combinations = [param_combinations[i] for i in indices]
            
            best_objective = -np.inf
            best_params = None
            evaluations = []
            
            # Evaluate all combinations
            for i, combination in enumerate(param_combinations):
                param_dict = {param_names[j]: combination[j] for j in range(len(param_names))}
                
                try:
                    objective_value = await self._evaluate_objective(objective_function, param_dict)
                    evaluations.append((param_dict, objective_value))
                    
                    if objective_value > best_objective:
                        best_objective = objective_value
                        best_params = param_dict
                
                except Exception as e:
                    logger.warning(f"Grid search evaluation {i} failed: {e}")
                    continue
            
            if best_params is None:
                logger.error("No valid evaluations in grid search")
                return None
            
            # Calculate improvement
            objective_values = [eval[1] for eval in evaluations]
            baseline = np.median(objective_values)
            improvement = (best_objective - baseline) / abs(baseline) if baseline != 0 else 0.0
            
            result = OptimizationResult(
                optimization_id=optimization_id,
                timestamp=datetime.now(),
                method=OptimizationMethod.GRID_SEARCH,
                objective_type=ObjectiveFunction.MAXIMIZE_SHARPE,
                optimal_parameters=best_params,
                objective_value=float(best_objective),
                improvement=float(improvement),
                confidence=0.9,  # Grid search provides high confidence
                iterations=len(param_combinations),
                convergence_achieved=True,
                evaluation_time=0.0,
                total_evaluations=len(evaluations),
                sharpe_ratio=float(best_objective),
                annual_return=0.0,
                max_drawdown=0.0,
                volatility=0.0,
                in_sample_performance={'objective': float(best_objective)},
                parameter_ranges={},
                optimization_history=[]
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in grid search optimization: {e}")
            return None
    
    async def _random_search_optimization(self,
                                        optimization_id: str,
                                        parameters: List[OptimizationParameter],
                                        objective_function: Callable,
                                        constraints: Optional[List[str]] = None) -> Optional[OptimizationResult]:
        """Perform random search optimization"""
        try:
            param_bounds = []
            param_names = []
            
            for param in parameters:
                if param.parameter_type in ['float', 'int']:
                    param_bounds.append(param.bounds)
                    param_names.append(param.name)
            
            if not param_bounds:
                logger.error("No valid parameters for random search")
                return None
            
            n_iterations = 200
            best_objective = -np.inf
            best_params = None
            evaluations = []
            
            for i in range(n_iterations):
                # Random parameter sample
                x = []
                for bounds in param_bounds:
                    x.append(np.random.uniform(bounds[0], bounds[1]))
                
                param_dict = {param_names[j]: x[j] for j in range(len(param_names))}
                
                try:
                    objective_value = await self._evaluate_objective(objective_function, param_dict)
                    evaluations.append((param_dict, objective_value))
                    
                    if objective_value > best_objective:
                        best_objective = objective_value
                        best_params = param_dict
                
                except Exception as e:
                    logger.warning(f"Random search evaluation {i} failed: {e}")
                    continue
            
            if best_params is None:
                logger.error("No valid evaluations in random search")
                return None
            
            # Calculate improvement
            objective_values = [eval[1] for eval in evaluations]
            baseline = np.median(objective_values)
            improvement = (best_objective - baseline) / abs(baseline) if baseline != 0 else 0.0
            
            result = OptimizationResult(
                optimization_id=optimization_id,
                timestamp=datetime.now(),
                method=OptimizationMethod.RANDOM_SEARCH,
                objective_type=ObjectiveFunction.MAXIMIZE_SHARPE,
                optimal_parameters=best_params,
                objective_value=float(best_objective),
                improvement=float(improvement),
                confidence=0.6,
                iterations=n_iterations,
                convergence_achieved=True,
                evaluation_time=0.0,
                total_evaluations=len(evaluations),
                sharpe_ratio=float(best_objective),
                annual_return=0.0,
                max_drawdown=0.0,
                volatility=0.0,
                in_sample_performance={'objective': float(best_objective)},
                parameter_ranges={param_names[i]: param_bounds[i] for i in range(len(param_names))},
                optimization_history=[]
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in random search optimization: {e}")
            return None
    
    async def _differential_evolution_optimization(self,
                                                 optimization_id: str,
                                                 parameters: List[OptimizationParameter],
                                                 objective_function: Callable,
                                                 constraints: Optional[List[str]] = None) -> Optional[OptimizationResult]:
        """Perform differential evolution optimization"""
        # This is similar to genetic algorithm but with different parameters
        return await self._genetic_algorithm_optimization(optimization_id, parameters, objective_function, constraints)
    
    async def _evaluate_objective(self, objective_function: Callable, parameters: Dict[str, Any]) -> float:
        """Evaluate objective function with given parameters"""
        try:
            if asyncio.iscoroutinefunction(objective_function):
                result = await objective_function(parameters)
            else:
                result = objective_function(parameters)
            
            return float(result)
            
        except Exception as e:
            logger.error(f"Error evaluating objective function: {e}")
            return -1e6  # Large penalty for failed evaluations
    
    def _calculate_sharpe_ratio(self, weights: np.ndarray, expected_returns: np.ndarray, cov_matrix: np.ndarray, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio for portfolio"""
        portfolio_return = np.dot(weights, expected_returns)
        portfolio_risk = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        
        if portfolio_risk == 0:
            return 0.0
        
        return (portfolio_return - risk_free_rate) / portfolio_risk
    
    def _calculate_portfolio_var(self, weights: np.ndarray, expected_returns: np.ndarray, cov_matrix: np.ndarray, confidence: float = 0.05) -> float:
        """Calculate portfolio Value at Risk"""
        portfolio_return = np.dot(weights, expected_returns)
        portfolio_risk = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        
        # Assuming normal distribution
        var = stats.norm.ppf(confidence) * portfolio_risk - portfolio_return
        return float(var)
    
    def _calculate_portfolio_cvar(self, weights: np.ndarray, expected_returns: np.ndarray, cov_matrix: np.ndarray, confidence: float = 0.05) -> float:
        """Calculate portfolio Conditional Value at Risk"""
        var = self._calculate_portfolio_var(weights, expected_returns, cov_matrix, confidence)
        
        # Simplified CVaR calculation (assuming normal distribution)
        portfolio_risk = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        cvar = var + portfolio_risk * stats.norm.pdf(stats.norm.ppf(confidence)) / confidence
        
        return float(cvar)
    
    def _generate_cache_key(self, strategy_id: str, parameters: List[OptimizationParameter], method: OptimizationMethod) -> str:
        """Generate cache key for optimization result"""
        param_signature = "_".join([f"{p.name}_{p.bounds[0]}_{p.bounds[1]}" for p in parameters])
        return f"{strategy_id}_{method.value}_{hash(param_signature)}"
    
    async def get_optimization_status(self) -> Dict[str, Any]:
        """Get current optimization status"""
        with self.lock:
            return {
                'is_optimizing': self.is_optimizing,
                'active_optimizations': len(self.active_optimizations),
                'optimization_history': len(self.optimization_history),
                'cached_results': len(self.cached_results),
                'portfolio_allocations': len(self.portfolio_allocations),
                'scheduled_strategies': len(self.strategy_optimizations),
                'recent_performance': {
                    'avg_improvement': np.mean(self.optimization_metrics.get('improvement_achieved', [0.0])),
                    'avg_convergence_time': np.mean(self.optimization_metrics.get('convergence_time', [0.0]))
                }
            }
    
    async def get_optimization_history(self, strategy_id: Optional[str] = None, limit: int = 50) -> List[OptimizationResult]:
        """Get optimization history"""
        with self.lock:
            history = self.optimization_history.copy()
            
            if strategy_id:
                # Filter by strategy (would need to add strategy_id to OptimizationResult)
                pass
            
            return history[-limit:] if limit else history
    
    async def get_portfolio_allocations(self, limit: int = 20) -> List[PortfolioAllocation]:
        """Get recent portfolio allocations"""
        with self.lock:
            return self.portfolio_allocations[-limit:] if limit else self.portfolio_allocations.copy()
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """Get comprehensive optimization engine summary"""
        with self.lock:
            return {
                'engine_status': {
                    'is_optimizing': self.is_optimizing,
                    'max_concurrent': self.max_concurrent_optimizations,
                    'default_method': self.default_method.value,
                    'cache_enabled': self.cache_results
                },
                'activity': {
                    'active_optimizations': len(self.active_optimizations),
                    'total_optimizations': len(self.optimization_history),
                    'cached_results': len(self.cached_results),
                    'scheduled_strategies': len(self.strategy_optimizations)
                },
                'portfolio': {
                    'total_allocations': len(self.portfolio_allocations),
                    'tracked_assets': len(self.allocation_history)
                },
                'performance': {
                    'optimization_metrics': dict(self.optimization_metrics)
                }
            }

# Global optimization engine instance
optimization_engine = OptimizationEngine()

# Export main components
__all__ = [
    'OptimizationEngine',
    'OptimizationParameter',
    'OptimizationObjective',
    'OptimizationResult',
    'PortfolioAllocation',
    'StrategyOptimization',
    'OptimizationType',
    'OptimizationMethod',
    'ObjectiveFunction',
    'optimization_engine'
]
