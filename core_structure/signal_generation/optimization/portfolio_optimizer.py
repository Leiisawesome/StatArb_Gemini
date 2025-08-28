"""
Consolidated Portfolio Optimization Engine
=========================================

Unified portfolio optimization combining:
- Position sizing and portfolio optimization
- Risk management and constraints
- Multi-strategy allocation
- Dynamic optimization algorithms

This module consolidates optimization functionality from:
- portfolio_optimizer.py
- position_sizer.py
- multi_strategy_allocator.py

Author: GitHub Copilot Architecture Simplification
Version: 4.0 (Consolidated)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
import time
import json
from collections import defaultdict

# Core infrastructure imports
try:
    from ...infrastructure.config import UnifiedConfigManager as ConfigManager
    from ...infrastructure.message_bus import MessageBus
    from ...infrastructure.metrics_collector import MetricsCollector
except ImportError:
    ConfigManager = None
    MessageBus = None
    MetricsCollector = None

# Scientific computing with graceful fallback
try:
    from scipy import optimize
    from scipy.linalg import LinAlgError
    import cvxpy as cp
    SCIPY_AVAILABLE = True
    CVXPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    CVXPY_AVAILABLE = False

# Optional advanced optimization
try:
    import pyportfolioopt as ppo
    PYPORTFOLIOOPT_AVAILABLE = True
except ImportError:
    PYPORTFOLIOOPT_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)

class OptimizationMethod(Enum):
    """Portfolio optimization methods"""
    EQUAL_WEIGHT = "equal_weight"
    MEAN_VARIANCE = "mean_variance"
    RISK_PARITY = "risk_parity"
    MIN_VARIANCE = "min_variance"
    MAX_SHARPE = "max_sharpe"
    BLACK_LITTERMAN = "black_litterman"
    KELLY = "kelly"
    CVaR = "cvar"

class PositionSizeMethod(Enum):
    """Position sizing methods"""
    FIXED = "fixed"
    PERCENT_RISK = "percent_risk"
    VOLATILITY_TARGET = "volatility_target"
    KELLY_CRITERION = "kelly_criterion"
    ATR_BASED = "atr_based"
    VaR_BASED = "var_based"

@dataclass
class OptimizationConfig:
    """Configuration for portfolio optimization"""
    # Core optimization settings
    optimization_method: OptimizationMethod = OptimizationMethod.MEAN_VARIANCE
    position_size_method: PositionSizeMethod = PositionSizeMethod.PERCENT_RISK
    rebalance_frequency: str = "daily"  # daily, weekly, monthly
    
    # Risk management
    max_position_size: float = 0.1  # 10% max position
    max_sector_exposure: float = 0.3  # 30% max sector
    max_portfolio_leverage: float = 1.0  # No leverage by default
    target_volatility: float = 0.15  # 15% annualized
    
    # Optimization constraints
    min_weight: float = 0.0
    
    def __post_init__(self):
        """Convert string optimization method to enum if needed"""
        if isinstance(self.optimization_method, str):
            self.optimization_method = OptimizationMethod(self.optimization_method)
        if isinstance(self.position_size_method, str):
            # Handle position size method conversion if needed
            position_size_map = {
                'fixed': PositionSizeMethod.FIXED,
                'percent_risk': PositionSizeMethod.PERCENT_RISK,
                'kelly': PositionSizeMethod.KELLY,
                'volatility_target': PositionSizeMethod.VOLATILITY_TARGET
            }
            self.position_size_method = position_size_map.get(self.position_size_method, PositionSizeMethod.PERCENT_RISK)
    max_weight: float = 0.1
    transaction_cost_bps: float = 5.0  # 5 basis points
    
    # Risk model
    lookback_days: int = 252
    min_correlation_observations: int = 60
    shrinkage_factor: float = 0.2
    
    # Performance settings
    max_optimization_time_ms: int = 100
    enable_parallel_optimization: bool = True
    cache_covariance_matrix: bool = True

@dataclass
class AllocationResult:
    """Portfolio allocation result"""
    weights: Dict[str, float]
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    optimization_method: OptimizationMethod
    constraints_satisfied: bool
    optimization_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'weights': self.weights,
            'expected_return': self.expected_return,
            'expected_volatility': self.expected_volatility,
            'sharpe_ratio': self.sharpe_ratio,
            'optimization_method': self.optimization_method.value,
            'constraints_satisfied': self.constraints_satisfied,
            'optimization_time': self.optimization_time,
            'metadata': self.metadata
        }

@dataclass
class PositionSize:
    """Position sizing result"""
    symbol: str
    size: float
    max_size: float
    risk_contribution: float
    method: PositionSizeMethod
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)

class PortfolioOptimizationEngine:
    """
    Consolidated Portfolio Optimization Engine
    
    Unified portfolio optimization combining allocation,
    position sizing, and risk management.
    """
    
    def __init__(self, config: Optional[OptimizationConfig] = None):
        """Initialize portfolio optimization engine"""
        self.config = config or OptimizationConfig()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # State management
        self._current_allocation = {}
        self._covariance_cache = {}
        self._expected_returns_cache = {}
        self._last_optimization = None
        self._lock = threading.Lock()
        
        # Performance tracking
        self.performance_metrics = {
            'optimizations_completed': 0,
            'avg_optimization_time': 0.0,
            'successful_allocations': 0,
            'constraint_violations': 0,
            'avg_sharpe_ratio': 0.0,
            'last_update': datetime.now()
        }
        
        self.logger.info(f"PortfolioOptimizationEngine initialized with method: {self.config.optimization_method.value}")
    
    def optimize_portfolio(self, 
                          symbols: List[str],
                          expected_returns: Optional[Dict[str, float]] = None,
                          price_data: Optional[pd.DataFrame] = None,
                          risk_data: Optional[Dict[str, float]] = None) -> Optional[AllocationResult]:
        """
        Optimize portfolio allocation
        
        Args:
            symbols: List of symbols to optimize
            expected_returns: Expected returns for each symbol
            price_data: Historical price data for covariance estimation
            risk_data: Risk metrics for each symbol
            
        Returns:
            Optimal allocation or None if optimization fails
        """
        start_time = time.time()
        
        try:
            if not symbols:
                self.logger.warning("No symbols provided for optimization")
                return None
            
            # Prepare optimization inputs
            returns_vector, covariance_matrix = self._prepare_optimization_inputs(
                symbols, expected_returns, price_data
            )
            
            if returns_vector is None or covariance_matrix is None:
                return None
            
            # Perform optimization based on method
            weights = self._optimize_weights(
                returns_vector, covariance_matrix, symbols
            )
            
            if weights is None:
                return None
            
            # Calculate portfolio metrics
            portfolio_return = np.dot(weights, returns_vector)
            portfolio_variance = np.dot(weights, np.dot(covariance_matrix, weights))
            portfolio_volatility = np.sqrt(portfolio_variance)
            sharpe_ratio = portfolio_return / portfolio_volatility if portfolio_volatility > 0 else 0.0
            
            # Check constraints
            constraints_satisfied = self._check_constraints(weights, symbols)
            
            # Create allocation result
            allocation = AllocationResult(
                weights={symbol: float(weights[i]) for i, symbol in enumerate(symbols)},
                expected_return=float(portfolio_return),
                expected_volatility=float(portfolio_volatility),
                sharpe_ratio=float(sharpe_ratio),
                optimization_method=self.config.optimization_method,
                constraints_satisfied=constraints_satisfied,
                optimization_time=time.time() - start_time,
                metadata={
                    'n_assets': len(symbols),
                    'max_weight': float(np.max(weights)),
                    'min_weight': float(np.min(weights)),
                    'concentration': float(np.sum(weights**2))  # Herfindahl index
                }
            )
            
            # Update state and metrics
            with self._lock:
                self._current_allocation = allocation.weights
                self._last_optimization = datetime.now()
            
            self._update_optimization_metrics(allocation)
            
            self.logger.info(f"Portfolio optimization completed: Sharpe={sharpe_ratio:.3f}, "
                           f"Vol={portfolio_volatility:.3f}, Time={allocation.optimization_time:.3f}s")
            
            return allocation
            
        except Exception as e:
            self.logger.error(f"Error in portfolio optimization: {e}")
            self._update_optimization_metrics(None, failed=True)
            return None
    
    def _prepare_optimization_inputs(self,
                                   symbols: List[str],
                                   expected_returns: Optional[Dict[str, float]],
                                   price_data: Optional[pd.DataFrame]) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Prepare expected returns vector and covariance matrix"""
        try:
            n_assets = len(symbols)
            
            # Prepare expected returns
            if expected_returns:
                returns_vector = np.array([expected_returns.get(symbol, 0.0) for symbol in symbols])
            else:
                # Use historical returns if available
                if price_data is not None and not price_data.empty:
                    returns_data = price_data.pct_change().dropna()
                    returns_vector = np.array([
                        returns_data[symbol].mean() if symbol in returns_data.columns else 0.0
                        for symbol in symbols
                    ])
                else:
                    # Equal expected returns assumption
                    returns_vector = np.ones(n_assets) * 0.001  # 0.1% daily return assumption
            
            # Prepare covariance matrix
            covariance_matrix = self._estimate_covariance_matrix(symbols, price_data)
            
            if covariance_matrix is None:
                # Use identity matrix as fallback
                covariance_matrix = np.eye(n_assets) * 0.01  # 1% variance assumption
            
            return returns_vector, covariance_matrix
            
        except Exception as e:
            self.logger.error(f"Error preparing optimization inputs: {e}")
            return None, None
    
    def _estimate_covariance_matrix(self, symbols: List[str], 
                                   price_data: Optional[pd.DataFrame]) -> Optional[np.ndarray]:
        """Estimate covariance matrix for assets"""
        try:
            n_assets = len(symbols)
            
            # Check cache first
            cache_key = tuple(sorted(symbols))
            if self.config.cache_covariance_matrix and cache_key in self._covariance_cache:
                cached_time, cached_matrix = self._covariance_cache[cache_key]
                if datetime.now() - cached_time < timedelta(hours=1):  # 1-hour cache
                    return cached_matrix
            
            if price_data is None or price_data.empty:
                # Return diagonal matrix as fallback
                return np.eye(n_assets) * 0.01
            
            # Calculate returns
            returns_data = price_data.pct_change().dropna()
            
            # Filter for available symbols
            available_symbols = [s for s in symbols if s in returns_data.columns]
            if len(available_symbols) < len(symbols):
                self.logger.warning(f"Missing price data for some symbols: {set(symbols) - set(available_symbols)}")
            
            if len(available_symbols) == 0:
                return np.eye(n_assets) * 0.01
            
            # Estimate covariance matrix
            if len(returns_data) >= self.config.min_correlation_observations:
                symbol_returns = returns_data[available_symbols]
                cov_matrix = symbol_returns.cov().values
                
                # Apply shrinkage if enabled
                if self.config.shrinkage_factor > 0:
                    target_matrix = np.eye(len(available_symbols)) * np.trace(cov_matrix) / len(available_symbols)
                    cov_matrix = (1 - self.config.shrinkage_factor) * cov_matrix + self.config.shrinkage_factor * target_matrix
                
                # Expand to full size if needed
                if len(available_symbols) < len(symbols):
                    full_matrix = np.eye(n_assets) * 0.01
                    symbol_indices = [symbols.index(s) for s in available_symbols]
                    for i, idx_i in enumerate(symbol_indices):
                        for j, idx_j in enumerate(symbol_indices):
                            full_matrix[idx_i, idx_j] = cov_matrix[i, j]
                    cov_matrix = full_matrix
                
                # Cache result
                if self.config.cache_covariance_matrix:
                    self._covariance_cache[cache_key] = (datetime.now(), cov_matrix)
                
                return cov_matrix
            else:
                self.logger.warning(f"Insufficient data for covariance estimation: {len(returns_data)} < {self.config.min_correlation_observations}")
                return np.eye(n_assets) * 0.01
                
        except Exception as e:
            self.logger.error(f"Error estimating covariance matrix: {e}")
            return np.eye(len(symbols)) * 0.01
    
    def _optimize_weights(self, returns_vector: np.ndarray,
                         covariance_matrix: np.ndarray,
                         symbols: List[str]) -> Optional[np.ndarray]:
        """Optimize portfolio weights based on selected method"""
        try:
            n_assets = len(symbols)
            
            if self.config.optimization_method == OptimizationMethod.EQUAL_WEIGHT:
                return np.ones(n_assets) / n_assets
            
            elif self.config.optimization_method == OptimizationMethod.MEAN_VARIANCE:
                return self._mean_variance_optimization(returns_vector, covariance_matrix)
            
            elif self.config.optimization_method == OptimizationMethod.MIN_VARIANCE:
                return self._min_variance_optimization(covariance_matrix)
            
            elif self.config.optimization_method == OptimizationMethod.MAX_SHARPE:
                return self._max_sharpe_optimization(returns_vector, covariance_matrix)
            
            elif self.config.optimization_method == OptimizationMethod.RISK_PARITY:
                return self._risk_parity_optimization(covariance_matrix)
            
            else:
                self.logger.warning(f"Unsupported optimization method: {self.config.optimization_method}")
                return np.ones(n_assets) / n_assets
                
        except Exception as e:
            self.logger.error(f"Error in weight optimization: {e}")
            return None
    
    def _mean_variance_optimization(self, returns_vector: np.ndarray,
                                  covariance_matrix: np.ndarray) -> Optional[np.ndarray]:
        """Mean-variance optimization"""
        try:
            n_assets = len(returns_vector)
            
            if CVXPY_AVAILABLE:
                # Use CVXPY for robust optimization
                w = cp.Variable(n_assets)
                
                # Objective: maximize return - risk penalty
                portfolio_return = w.T @ returns_vector
                portfolio_risk = cp.quad_form(w, covariance_matrix)
                
                # Risk aversion parameter (higher = more risk-averse)
                risk_aversion = 1.0 / (self.config.target_volatility ** 2)
                objective = cp.Maximize(portfolio_return - 0.5 * risk_aversion * portfolio_risk)
                
                # Constraints
                constraints = [
                    cp.sum(w) == 1,  # Fully invested
                    w >= self.config.min_weight,
                    w <= self.config.max_weight
                ]
                
                # Solve
                problem = cp.Problem(objective, constraints)
                problem.solve(solver=cp.OSQP, verbose=False)
                
                if w.value is not None:
                    return np.array(w.value)
            
            # Fallback to scipy optimization
            if SCIPY_AVAILABLE:
                return self._scipy_mean_variance_optimization(returns_vector, covariance_matrix)
            
            # Last resort: equal weights
            return np.ones(n_assets) / n_assets
            
        except Exception as e:
            self.logger.error(f"Error in mean-variance optimization: {e}")
            return None
    
    def _scipy_mean_variance_optimization(self, returns_vector: np.ndarray,
                                        covariance_matrix: np.ndarray) -> Optional[np.ndarray]:
        """Mean-variance optimization using scipy"""
        try:
            n_assets = len(returns_vector)
            
            # Objective function: minimize -return + risk_penalty * variance
            def objective(weights):
                portfolio_return = np.dot(weights, returns_vector)
                portfolio_variance = np.dot(weights, np.dot(covariance_matrix, weights))
                risk_aversion = 1.0 / (self.config.target_volatility ** 2)
                return -(portfolio_return - 0.5 * risk_aversion * portfolio_variance)
            
            # Constraints
            constraints = [
                {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}  # Fully invested
            ]
            
            # Bounds
            bounds = [(self.config.min_weight, self.config.max_weight) for _ in range(n_assets)]
            
            # Initial guess
            x0 = np.ones(n_assets) / n_assets
            
            # Optimize
            result = optimize.minimize(
                objective, x0, method='SLSQP',
                bounds=bounds, constraints=constraints,
                options={'maxiter': 1000, 'ftol': 1e-9}
            )
            
            if result.success:
                return result.x
            else:
                self.logger.warning("Scipy optimization failed, using equal weights")
                return np.ones(n_assets) / n_assets
                
        except Exception as e:
            self.logger.error(f"Error in scipy mean-variance optimization: {e}")
            return np.ones(n_assets) / n_assets
    
    def _min_variance_optimization(self, covariance_matrix: np.ndarray) -> Optional[np.ndarray]:
        """Minimum variance optimization"""
        try:
            n_assets = covariance_matrix.shape[0]
            
            if CVXPY_AVAILABLE:
                w = cp.Variable(n_assets)
                objective = cp.Minimize(cp.quad_form(w, covariance_matrix))
                constraints = [
                    cp.sum(w) == 1,
                    w >= self.config.min_weight,
                    w <= self.config.max_weight
                ]
                
                problem = cp.Problem(objective, constraints)
                problem.solve(solver=cp.OSQP, verbose=False)
                
                if w.value is not None:
                    return np.array(w.value)
            
            # Analytical solution for unconstrained case
            try:
                inv_cov = np.linalg.inv(covariance_matrix)
                ones = np.ones((n_assets, 1))
                weights = inv_cov @ ones / (ones.T @ inv_cov @ ones)
                weights = weights.flatten()
                
                # Check bounds
                if np.all(weights >= self.config.min_weight) and np.all(weights <= self.config.max_weight):
                    return weights
            except LinAlgError:
                pass
            
            # Fallback
            return np.ones(n_assets) / n_assets
            
        except Exception as e:
            self.logger.error(f"Error in min variance optimization: {e}")
            return None
    
    def _max_sharpe_optimization(self, returns_vector: np.ndarray,
                               covariance_matrix: np.ndarray) -> Optional[np.ndarray]:
        """Maximum Sharpe ratio optimization"""
        try:
            n_assets = len(returns_vector)
            
            if CVXPY_AVAILABLE:
                # Transform to linear problem: maximize return / sqrt(variance)
                # Using the approach of maximizing return subject to variance = 1
                w = cp.Variable(n_assets)
                objective = cp.Maximize(w.T @ returns_vector)
                constraints = [
                    cp.quad_form(w, covariance_matrix) <= 1,
                    w >= self.config.min_weight / 1000,  # Relaxed for numerical stability
                ]
                
                problem = cp.Problem(objective, constraints)
                problem.solve(solver=cp.OSQP, verbose=False)
                
                if w.value is not None:
                    weights = np.array(w.value)
                    # Normalize to sum to 1
                    weights = weights / np.sum(weights)
                    
                    # Check bounds and adjust if necessary
                    weights = np.clip(weights, self.config.min_weight, self.config.max_weight)
                    weights = weights / np.sum(weights)  # Re-normalize
                    
                    return weights
            
            # Fallback to equal weights
            return np.ones(n_assets) / n_assets
            
        except Exception as e:
            self.logger.error(f"Error in max Sharpe optimization: {e}")
            return None
    
    def _risk_parity_optimization(self, covariance_matrix: np.ndarray) -> Optional[np.ndarray]:
        """Risk parity optimization"""
        try:
            n_assets = covariance_matrix.shape[0]
            
            # Risk parity: equal risk contribution from each asset
            def risk_budget_objective(weights):
                portfolio_vol = np.sqrt(np.dot(weights, np.dot(covariance_matrix, weights)))
                marginal_contrib = np.dot(covariance_matrix, weights) / portfolio_vol
                contrib = weights * marginal_contrib
                target_contrib = np.ones(n_assets) / n_assets
                return np.sum((contrib - target_contrib) ** 2)
            
            # Constraints
            constraints = [
                {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
            ]
            
            bounds = [(self.config.min_weight, self.config.max_weight) for _ in range(n_assets)]
            x0 = np.ones(n_assets) / n_assets
            
            if SCIPY_AVAILABLE:
                result = optimize.minimize(
                    risk_budget_objective, x0, method='SLSQP',
                    bounds=bounds, constraints=constraints,
                    options={'maxiter': 1000}
                )
                
                if result.success:
                    return result.x
            
            # Fallback: inverse volatility weighting
            vol_weights = 1.0 / np.sqrt(np.diag(covariance_matrix))
            vol_weights = vol_weights / np.sum(vol_weights)
            return vol_weights
            
        except Exception as e:
            self.logger.error(f"Error in risk parity optimization: {e}")
            return np.ones(n_assets) / n_assets
    
    def _check_constraints(self, weights: np.ndarray, symbols: List[str]) -> bool:
        """Check if allocation satisfies constraints"""
        try:
            # Weight bounds
            if np.any(weights < self.config.min_weight - 1e-6):
                return False
            if np.any(weights > self.config.max_weight + 1e-6):
                return False
            
            # Sum to 1 (fully invested)
            if abs(np.sum(weights) - 1.0) > 1e-4:
                return False
            
            # Long-only check
            if np.any(weights < -1e-6):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking constraints: {e}")
            return False
    
    def calculate_position_size(self, symbol: str, signal_strength: float,
                              current_price: float, account_value: float,
                              volatility: Optional[float] = None,
                              atr: Optional[float] = None) -> Optional[PositionSize]:
        """Calculate position size for individual symbol"""
        try:
            base_allocation = self._current_allocation.get(symbol, 0.0)
            
            if self.config.position_size_method == PositionSizeMethod.FIXED:
                size = base_allocation * account_value
                
            elif self.config.position_size_method == PositionSizeMethod.PERCENT_RISK:
                risk_per_trade = 0.02  # 2% risk per trade
                size = (account_value * risk_per_trade * signal_strength) / current_price
                
            elif self.config.position_size_method == PositionSizeMethod.VOLATILITY_TARGET:
                if volatility is None:
                    volatility = 0.2  # Default 20% volatility
                
                target_vol_contribution = self.config.target_volatility * base_allocation
                size = (account_value * target_vol_contribution) / (current_price * volatility)
                
            elif self.config.position_size_method == PositionSizeMethod.ATR_BASED:
                if atr is None:
                    atr = current_price * 0.02  # Default 2% ATR
                
                risk_per_trade = 0.02  # 2% risk per trade
                size = (account_value * risk_per_trade * signal_strength) / atr
                
            else:
                # Default to allocation-based sizing
                size = base_allocation * account_value / current_price
            
            # Apply position limits
            max_position_value = account_value * self.config.max_position_size
            max_size = max_position_value / current_price
            
            final_size = min(abs(size), max_size) * np.sign(size)
            
            return PositionSize(
                symbol=symbol,
                size=final_size,
                max_size=max_size,
                risk_contribution=abs(final_size * current_price) / account_value,
                method=self.config.position_size_method,
                confidence=abs(signal_strength),
                metadata={
                    'base_allocation': base_allocation,
                    'account_value': account_value,
                    'current_price': current_price,
                    'volatility': volatility,
                    'atr': atr
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating position size for {symbol}: {e}")
            return None
    
    def _update_optimization_metrics(self, allocation: Optional[AllocationResult], failed: bool = False):
        """Update optimization performance metrics"""
        self.performance_metrics['optimizations_completed'] += 1
        
        if failed:
            self.performance_metrics['constraint_violations'] += 1
        elif allocation:
            self.performance_metrics['successful_allocations'] += 1
            
            # Update rolling averages
            total_successful = self.performance_metrics['successful_allocations']
            
            old_avg_time = self.performance_metrics['avg_optimization_time']
            self.performance_metrics['avg_optimization_time'] = (
                (old_avg_time * (total_successful - 1) + allocation.optimization_time) / total_successful
            )
            
            old_avg_sharpe = self.performance_metrics['avg_sharpe_ratio']
            self.performance_metrics['avg_sharpe_ratio'] = (
                (old_avg_sharpe * (total_successful - 1) + allocation.sharpe_ratio) / total_successful
            )
        
        self.performance_metrics['last_update'] = datetime.now()
    
    def get_current_allocation(self) -> Dict[str, float]:
        """Get current portfolio allocation"""
        with self._lock:
            return self._current_allocation.copy()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get optimization performance metrics"""
        return self.performance_metrics.copy()
    
    def reset_allocation(self):
        """Reset current allocation"""
        with self._lock:
            self._current_allocation.clear()
            self._last_optimization = None
        
        self.logger.info("Portfolio allocation reset")

# Backward compatibility aliases
PositionSizer = PortfolioOptimizationEngine
MultiStrategyAllocator = PortfolioOptimizationEngine
PortfolioOptimizer = PortfolioOptimizationEngine

__all__ = [
    'PortfolioOptimizationEngine',
    'PositionSizer',  # Backward compatibility
    'MultiStrategyAllocator',  # Backward compatibility
    'PortfolioOptimizer',  # Backward compatibility
    'AllocationResult',
    'PositionSize',
    'OptimizationMethod',
    'PositionSizeMethod',
    'OptimizationConfig'
]
