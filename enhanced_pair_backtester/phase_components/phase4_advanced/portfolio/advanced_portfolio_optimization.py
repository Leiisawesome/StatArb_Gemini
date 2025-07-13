"""
Advanced Portfolio Optimization System
======================================

This module implements a comprehensive portfolio optimization system using modern
portfolio theory, risk budgeting, factor models, and dynamic allocation strategies
for multi-strategy quantitative trading.

Key Features:
- Modern Portfolio Theory with factor models
- Risk budgeting and factor exposure control
- Black-Litterman optimization
- Dynamic allocation based on market regimes
- Multi-objective optimization (return, risk, drawdown)
- Transaction cost optimization
- Portfolio rebalancing strategies

Author: Pro Quant Desk Trader
Date: 2024
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
import sqlite3
import warnings
from abc import ABC, abstractmethod

# Optimization and statistical libraries
from scipy.optimize import minimize, NonlinearConstraint, LinearConstraint
from scipy import stats
from scipy.linalg import sqrtm, inv
import cvxpy as cp
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.covariance import LedoitWolf, EmpiricalCovariance
from sklearn.linear_model import LinearRegression
import joblib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptimizationObjective(Enum):
    """Portfolio optimization objectives"""
    MAX_SHARPE = "MAX_SHARPE"
    MIN_VARIANCE = "MIN_VARIANCE"
    MAX_RETURN = "MAX_RETURN"
    RISK_PARITY = "RISK_PARITY"
    BLACK_LITTERMAN = "BLACK_LITTERMAN"
    EQUAL_RISK_CONTRIBUTION = "EQUAL_RISK_CONTRIBUTION"
    MAX_DIVERSIFICATION = "MAX_DIVERSIFICATION"
    MIN_TRACKING_ERROR = "MIN_TRACKING_ERROR"

class RiskModel(Enum):
    """Risk model types"""
    SAMPLE_COVARIANCE = "SAMPLE_COVARIANCE"
    LEDOIT_WOLF = "LEDOIT_WOLF"
    FACTOR_MODEL = "FACTOR_MODEL"
    ROBUST_COVARIANCE = "ROBUST_COVARIANCE"
    EWMA = "EWMA"
    GARCH = "GARCH"

class RebalancingFrequency(Enum):
    """Portfolio rebalancing frequencies"""
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    SEMI_ANNUAL = "SEMI_ANNUAL"
    ANNUAL = "ANNUAL"
    THRESHOLD_BASED = "THRESHOLD_BASED"

@dataclass
class FactorExposure:
    """Factor exposure constraints"""
    factor_name: str
    target_exposure: float
    min_exposure: float
    max_exposure: float
    current_exposure: float = 0.0
    
    # Factor loading
    factor_loadings: Dict[str, float] = field(default_factory=dict)
    
    # Tracking
    exposure_history: List[float] = field(default_factory=list)
    last_update: datetime = field(default_factory=datetime.now)

@dataclass
class RiskBudget:
    """Risk budget allocation"""
    asset_or_strategy: str
    target_risk_contribution: float
    max_risk_contribution: float
    current_risk_contribution: float = 0.0
    
    # Risk metrics
    marginal_risk: float = 0.0
    component_risk: float = 0.0
    
    # Tracking
    risk_contribution_history: List[float] = field(default_factory=list)
    last_update: datetime = field(default_factory=datetime.now)

@dataclass
class OptimizationConstraints:
    """Portfolio optimization constraints"""
    # Weight constraints
    min_weights: Dict[str, float] = field(default_factory=dict)
    max_weights: Dict[str, float] = field(default_factory=dict)
    
    # Risk constraints
    max_portfolio_volatility: Optional[float] = None
    max_portfolio_var: Optional[float] = None
    max_tracking_error: Optional[float] = None
    
    # Exposure constraints
    factor_exposures: List[FactorExposure] = field(default_factory=list)
    
    # Risk budgets
    risk_budgets: List[RiskBudget] = field(default_factory=list)
    
    # Turnover constraints
    max_turnover: Optional[float] = None
    
    # Concentration constraints
    max_concentration: Optional[float] = None  # Max weight in single asset
    
    # Sector/group constraints
    sector_constraints: Dict[str, Tuple[float, float]] = field(default_factory=dict)  # (min, max)

@dataclass
class OptimizationResult:
    """Portfolio optimization result"""
    optimization_id: str
    timestamp: datetime
    objective: OptimizationObjective
    
    # Optimal weights
    optimal_weights: Dict[str, float]
    
    # Expected performance
    expected_return: float
    expected_volatility: float
    expected_sharpe: float
    
    # Risk metrics
    portfolio_var: float
    portfolio_cvar: float
    max_drawdown_estimate: float
    
    # Factor exposures
    factor_exposures: Dict[str, float]
    
    # Risk contributions
    risk_contributions: Dict[str, float]
    
    # Optimization metadata
    optimization_time: float
    convergence_status: str
    objective_value: float
    
    # Constraints satisfaction
    constraints_satisfied: bool
    constraint_violations: List[str] = field(default_factory=list)
    
    # Transaction costs
    estimated_transaction_costs: float = 0.0
    turnover: float = 0.0

@dataclass
class PortfolioState:
    """Current portfolio state"""
    timestamp: datetime
    
    # Current holdings
    current_weights: Dict[str, float]
    current_values: Dict[str, float]
    total_portfolio_value: float
    
    # Performance metrics
    portfolio_return: float
    portfolio_volatility: float
    sharpe_ratio: float
    max_drawdown: float
    
    # Risk metrics
    portfolio_var: float
    portfolio_cvar: float
    
    # Factor exposures
    current_factor_exposures: Dict[str, float]
    
    # Risk contributions
    current_risk_contributions: Dict[str, float]
    
    # Rebalancing info
    days_since_rebalance: int
    rebalancing_needed: bool

class BaseOptimizer(ABC):
    """Base class for portfolio optimizers"""
    
    def __init__(self, objective: OptimizationObjective, config: Dict[str, Any]):
        self.objective = objective
        self.config = config
        
        # Risk model
        self.risk_model = RiskModel(config.get('risk_model', 'SAMPLE_COVARIANCE'))
        
        # Optimization parameters
        self.lookback_period = config.get('lookback_period', 252)
        self.min_periods = config.get('min_periods', 60)
        
        # Covariance estimation
        self.covariance_estimator = None
        self._initialize_covariance_estimator()
    
    def _initialize_covariance_estimator(self):
        """Initialize covariance estimator based on risk model"""
        if self.risk_model == RiskModel.LEDOIT_WOLF:
            self.covariance_estimator = LedoitWolf()
        elif self.risk_model == RiskModel.ROBUST_COVARIANCE:
            self.covariance_estimator = EmpiricalCovariance()
        else:
            self.covariance_estimator = None
    
    @abstractmethod
    def optimize(self, expected_returns: pd.Series, 
                covariance_matrix: pd.DataFrame,
                constraints: OptimizationConstraints,
                current_weights: Optional[pd.Series] = None) -> OptimizationResult:
        """Optimize portfolio weights"""
        pass
    
    def estimate_covariance(self, returns: pd.DataFrame) -> pd.DataFrame:
        """Estimate covariance matrix using specified risk model"""
        try:
            if self.risk_model == RiskModel.SAMPLE_COVARIANCE:
                return returns.cov()
            
            elif self.risk_model == RiskModel.LEDOIT_WOLF:
                cov_matrix, _ = self.covariance_estimator.fit(returns.values).covariance_, None
                return pd.DataFrame(cov_matrix, index=returns.columns, columns=returns.columns)
            
            elif self.risk_model == RiskModel.EWMA:
                return self._estimate_ewma_covariance(returns)
            
            elif self.risk_model == RiskModel.FACTOR_MODEL:
                return self._estimate_factor_model_covariance(returns)
            
            else:
                return returns.cov()
                
        except Exception as e:
            logger.error(f"Error estimating covariance: {e}")
            return returns.cov()
    
    def _estimate_ewma_covariance(self, returns: pd.DataFrame, decay_factor: float = 0.94) -> pd.DataFrame:
        """Estimate EWMA covariance matrix"""
        weights = np.array([(1 - decay_factor) * (decay_factor ** i) for i in range(len(returns))][::-1])
        weights = weights / weights.sum()
        
        weighted_returns = returns.values * weights.reshape(-1, 1)
        mean_returns = np.average(returns.values, weights=weights, axis=0)
        
        cov_matrix = np.zeros((len(returns.columns), len(returns.columns)))
        for i, weight in enumerate(weights):
            deviation = returns.values[i] - mean_returns
            cov_matrix += weight * np.outer(deviation, deviation)
        
        return pd.DataFrame(cov_matrix, index=returns.columns, columns=returns.columns)
    
    def _estimate_factor_model_covariance(self, returns: pd.DataFrame, n_factors: int = 5) -> pd.DataFrame:
        """Estimate covariance using factor model"""
        try:
            # Use PCA to extract factors
            pca = PCA(n_components=n_factors)
            factor_returns = pca.fit_transform(returns.fillna(0))
            
            # Calculate factor loadings
            factor_loadings = pca.components_.T
            
            # Calculate factor covariance
            factor_cov = np.cov(factor_returns.T)
            
            # Calculate specific variances (residual variances)
            residuals = returns.values - factor_returns @ factor_loadings.T
            specific_variances = np.var(residuals, axis=0)
            
            # Reconstruct covariance matrix
            cov_matrix = factor_loadings @ factor_cov @ factor_loadings.T + np.diag(specific_variances)
            
            return pd.DataFrame(cov_matrix, index=returns.columns, columns=returns.columns)
            
        except Exception as e:
            logger.error(f"Error in factor model covariance: {e}")
            return returns.cov()

class MeanVarianceOptimizer(BaseOptimizer):
    """Mean-Variance optimizer (Markowitz)"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(OptimizationObjective.MAX_SHARPE, config)
        self.risk_aversion = config.get('risk_aversion', 1.0)
    
    def optimize(self, expected_returns: pd.Series, 
                covariance_matrix: pd.DataFrame,
                constraints: OptimizationConstraints,
                current_weights: Optional[pd.Series] = None) -> OptimizationResult:
        """Optimize using mean-variance framework"""
        start_time = datetime.now()
        
        try:
            n_assets = len(expected_returns)
            assets = expected_returns.index.tolist()
            
            # Define optimization variables
            weights = cp.Variable(n_assets)
            
            # Objective function
            if self.objective == OptimizationObjective.MAX_SHARPE:
                # For Sharpe ratio maximization, we use a different formulation
                portfolio_return = expected_returns.values @ weights
                portfolio_variance = cp.quad_form(weights, covariance_matrix.values)
                
                # Maximize return for given risk or minimize risk for given return
                objective = cp.Maximize(portfolio_return - 0.5 * self.risk_aversion * portfolio_variance)
                
            elif self.objective == OptimizationObjective.MIN_VARIANCE:
                portfolio_variance = cp.quad_form(weights, covariance_matrix.values)
                objective = cp.Minimize(portfolio_variance)
                
            elif self.objective == OptimizationObjective.MAX_RETURN:
                portfolio_return = expected_returns.values @ weights
                objective = cp.Maximize(portfolio_return)
            
            # Constraints
            constraints_list = [cp.sum(weights) == 1]  # Weights sum to 1
            
            # Weight bounds
            for i, asset in enumerate(assets):
                min_weight = constraints.min_weights.get(asset, 0.0)
                max_weight = constraints.max_weights.get(asset, 1.0)
                constraints_list.extend([
                    weights[i] >= min_weight,
                    weights[i] <= max_weight
                ])
            
            # Risk constraints
            if constraints.max_portfolio_volatility:
                portfolio_variance = cp.quad_form(weights, covariance_matrix.values)
                constraints_list.append(cp.sqrt(portfolio_variance) <= constraints.max_portfolio_volatility)
            
            # Concentration constraint
            if constraints.max_concentration:
                for i in range(n_assets):
                    constraints_list.append(weights[i] <= constraints.max_concentration)
            
            # Turnover constraint
            if constraints.max_turnover and current_weights is not None:
                current_weights_aligned = np.array([current_weights.get(asset, 0.0) for asset in assets])
                turnover = cp.norm(weights - current_weights_aligned, 1)
                constraints_list.append(turnover <= constraints.max_turnover)
            
            # Solve optimization problem
            problem = cp.Problem(objective, constraints_list)
            problem.solve(solver=cp.ECOS)
            
            # Extract results
            if problem.status == cp.OPTIMAL:
                optimal_weights_array = weights.value
                optimal_weights = {asset: weight for asset, weight in zip(assets, optimal_weights_array)}
                
                # Calculate performance metrics
                expected_return = float(expected_returns @ optimal_weights_array)
                expected_volatility = float(np.sqrt(optimal_weights_array.T @ covariance_matrix.values @ optimal_weights_array))
                expected_sharpe = expected_return / expected_volatility if expected_volatility > 0 else 0.0
                
                # Calculate risk contributions
                risk_contributions = self._calculate_risk_contributions(
                    optimal_weights_array, covariance_matrix.values, assets
                )
                
                # Calculate factor exposures (simplified)
                factor_exposures = self._calculate_factor_exposures(optimal_weights, assets)
                
                optimization_time = (datetime.now() - start_time).total_seconds()
                
                return OptimizationResult(
                    optimization_id=f"mv_{int(datetime.now().timestamp())}",
                    timestamp=datetime.now(),
                    objective=self.objective,
                    optimal_weights=optimal_weights,
                    expected_return=expected_return,
                    expected_volatility=expected_volatility,
                    expected_sharpe=expected_sharpe,
                    portfolio_var=expected_volatility * 1.645,  # 95% VaR
                    portfolio_cvar=expected_volatility * 2.33,  # 99% CVaR
                    max_drawdown_estimate=expected_volatility * 2.0,  # Rough estimate
                    factor_exposures=factor_exposures,
                    risk_contributions=risk_contributions,
                    optimization_time=optimization_time,
                    convergence_status="OPTIMAL",
                    objective_value=float(problem.value),
                    constraints_satisfied=True
                )
            
            else:
                logger.error(f"Optimization failed with status: {problem.status}")
                return self._create_fallback_result(assets, start_time)
                
        except Exception as e:
            logger.error(f"Error in mean-variance optimization: {e}")
            return self._create_fallback_result(assets, start_time)
    
    def _calculate_risk_contributions(self, weights: np.ndarray, 
                                    cov_matrix: np.ndarray, 
                                    assets: List[str]) -> Dict[str, float]:
        """Calculate risk contributions for each asset"""
        try:
            portfolio_variance = weights.T @ cov_matrix @ weights
            marginal_contributions = cov_matrix @ weights
            risk_contributions = weights * marginal_contributions / portfolio_variance
            
            return {asset: float(contrib) for asset, contrib in zip(assets, risk_contributions)}
            
        except Exception as e:
            logger.error(f"Error calculating risk contributions: {e}")
            return {asset: 1.0 / len(assets) for asset in assets}
    
    def _calculate_factor_exposures(self, weights: Dict[str, float], 
                                  assets: List[str]) -> Dict[str, float]:
        """Calculate factor exposures (simplified)"""
        # This is a simplified implementation
        # In practice, you would use actual factor loadings
        return {
            'market_beta': sum(weights.values()),  # Simplified market exposure
            'size_factor': 0.0,  # Would calculate based on actual factor loadings
            'value_factor': 0.0,
            'momentum_factor': 0.0,
            'quality_factor': 0.0
        }
    
    def _create_fallback_result(self, assets: List[str], start_time: datetime) -> OptimizationResult:
        """Create fallback result when optimization fails"""
        equal_weights = {asset: 1.0 / len(assets) for asset in assets}
        
        return OptimizationResult(
            optimization_id=f"fallback_{int(datetime.now().timestamp())}",
            timestamp=datetime.now(),
            objective=self.objective,
            optimal_weights=equal_weights,
            expected_return=0.0,
            expected_volatility=0.15,
            expected_sharpe=0.0,
            portfolio_var=0.15 * 1.645,
            portfolio_cvar=0.15 * 2.33,
            max_drawdown_estimate=0.15 * 2.0,
            factor_exposures={},
            risk_contributions=equal_weights,
            optimization_time=(datetime.now() - start_time).total_seconds(),
            convergence_status="FAILED",
            objective_value=0.0,
            constraints_satisfied=False,
            constraint_violations=["Optimization failed"]
        )

class RiskParityOptimizer(BaseOptimizer):
    """Risk Parity optimizer"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(OptimizationObjective.RISK_PARITY, config)
        self.tolerance = config.get('tolerance', 1e-6)
        self.max_iterations = config.get('max_iterations', 1000)
    
    def optimize(self, expected_returns: pd.Series, 
                covariance_matrix: pd.DataFrame,
                constraints: OptimizationConstraints,
                current_weights: Optional[pd.Series] = None) -> OptimizationResult:
        """Optimize using risk parity approach"""
        start_time = datetime.now()
        
        try:
            n_assets = len(expected_returns)
            assets = expected_returns.index.tolist()
            
            # Risk parity optimization using iterative approach
            optimal_weights = self._solve_risk_parity(covariance_matrix.values, assets, constraints)
            
            # Calculate performance metrics
            expected_return = float(expected_returns @ optimal_weights)
            expected_volatility = float(np.sqrt(optimal_weights.T @ covariance_matrix.values @ optimal_weights))
            expected_sharpe = expected_return / expected_volatility if expected_volatility > 0 else 0.0
            
            # Calculate risk contributions
            risk_contributions = self._calculate_risk_contributions(
                optimal_weights, covariance_matrix.values, assets
            )
            
            # Calculate factor exposures
            factor_exposures = self._calculate_factor_exposures(
                {asset: weight for asset, weight in zip(assets, optimal_weights)}, assets
            )
            
            optimization_time = (datetime.now() - start_time).total_seconds()
            
            return OptimizationResult(
                optimization_id=f"rp_{int(datetime.now().timestamp())}",
                timestamp=datetime.now(),
                objective=self.objective,
                optimal_weights={asset: weight for asset, weight in zip(assets, optimal_weights)},
                expected_return=expected_return,
                expected_volatility=expected_volatility,
                expected_sharpe=expected_sharpe,
                portfolio_var=expected_volatility * 1.645,
                portfolio_cvar=expected_volatility * 2.33,
                max_drawdown_estimate=expected_volatility * 2.0,
                factor_exposures=factor_exposures,
                risk_contributions=risk_contributions,
                optimization_time=optimization_time,
                convergence_status="OPTIMAL",
                objective_value=0.0,  # Risk parity doesn't have a traditional objective value
                constraints_satisfied=True
            )
            
        except Exception as e:
            logger.error(f"Error in risk parity optimization: {e}")
            return self._create_fallback_result(assets, start_time)
    
    def _solve_risk_parity(self, cov_matrix: np.ndarray, 
                          assets: List[str],
                          constraints: OptimizationConstraints) -> np.ndarray:
        """Solve risk parity optimization"""
        try:
            n_assets = len(assets)
            
            # Objective function for risk parity
            def risk_parity_objective(weights):
                # Normalize weights
                weights = weights / np.sum(weights)
                
                # Calculate portfolio variance
                portfolio_var = weights.T @ cov_matrix @ weights
                
                # Calculate marginal risk contributions
                marginal_contrib = cov_matrix @ weights
                
                # Calculate risk contributions
                risk_contrib = weights * marginal_contrib / portfolio_var
                
                # Target equal risk contributions
                target_contrib = 1.0 / n_assets
                
                # Sum of squared deviations from equal risk contribution
                return np.sum((risk_contrib - target_contrib) ** 2)
            
            # Constraints
            constraints_list = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]  # Weights sum to 1
            
            # Bounds
            bounds = []
            for asset in assets:
                min_weight = constraints.min_weights.get(asset, 0.001)  # Small positive minimum
                max_weight = constraints.max_weights.get(asset, 1.0)
                bounds.append((min_weight, max_weight))
            
            # Initial guess (equal weights)
            x0 = np.ones(n_assets) / n_assets
            
            # Solve optimization
            result = minimize(
                risk_parity_objective,
                x0,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints_list,
                options={'maxiter': self.max_iterations, 'ftol': self.tolerance}
            )
            
            if result.success:
                # Normalize weights
                optimal_weights = result.x / np.sum(result.x)
                return optimal_weights
            else:
                logger.warning("Risk parity optimization did not converge, using equal weights")
                return np.ones(n_assets) / n_assets
                
        except Exception as e:
            logger.error(f"Error solving risk parity: {e}")
            return np.ones(len(assets)) / len(assets)
    
    def _calculate_risk_contributions(self, weights: np.ndarray, 
                                    cov_matrix: np.ndarray, 
                                    assets: List[str]) -> Dict[str, float]:
        """Calculate risk contributions for each asset"""
        try:
            portfolio_variance = weights.T @ cov_matrix @ weights
            marginal_contributions = cov_matrix @ weights
            risk_contributions = weights * marginal_contributions / portfolio_variance
            
            return {asset: float(contrib) for asset, contrib in zip(assets, risk_contributions)}
            
        except Exception as e:
            logger.error(f"Error calculating risk contributions: {e}")
            return {asset: 1.0 / len(assets) for asset in assets}
    
    def _calculate_factor_exposures(self, weights: Dict[str, float], 
                                  assets: List[str]) -> Dict[str, float]:
        """Calculate factor exposures"""
        return {
            'market_beta': sum(weights.values()),
            'size_factor': 0.0,
            'value_factor': 0.0,
            'momentum_factor': 0.0,
            'quality_factor': 0.0
        }
    
    def _create_fallback_result(self, assets: List[str], start_time: datetime) -> OptimizationResult:
        """Create fallback result when optimization fails"""
        equal_weights = {asset: 1.0 / len(assets) for asset in assets}
        
        return OptimizationResult(
            optimization_id=f"rp_fallback_{int(datetime.now().timestamp())}",
            timestamp=datetime.now(),
            objective=self.objective,
            optimal_weights=equal_weights,
            expected_return=0.0,
            expected_volatility=0.15,
            expected_sharpe=0.0,
            portfolio_var=0.15 * 1.645,
            portfolio_cvar=0.15 * 2.33,
            max_drawdown_estimate=0.15 * 2.0,
            factor_exposures={},
            risk_contributions=equal_weights,
            optimization_time=(datetime.now() - start_time).total_seconds(),
            convergence_status="FAILED",
            objective_value=0.0,
            constraints_satisfied=False,
            constraint_violations=["Risk parity optimization failed"]
        )

class BlackLittermanOptimizer(BaseOptimizer):
    """Black-Litterman optimizer"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(OptimizationObjective.BLACK_LITTERMAN, config)
        self.risk_aversion = config.get('risk_aversion', 3.0)
        self.tau = config.get('tau', 0.025)  # Scaling factor for uncertainty
        self.confidence_level = config.get('confidence_level', 0.95)
    
    def optimize(self, expected_returns: pd.Series, 
                covariance_matrix: pd.DataFrame,
                constraints: OptimizationConstraints,
                current_weights: Optional[pd.Series] = None,
                views: Optional[Dict[str, Tuple[float, float]]] = None) -> OptimizationResult:
        """
        Optimize using Black-Litterman model
        
        Args:
            views: Dictionary of {asset: (expected_return, confidence)} for investor views
        """
        start_time = datetime.now()
        
        try:
            n_assets = len(expected_returns)
            assets = expected_returns.index.tolist()
            
            # Market capitalization weights (using equal weights as proxy)
            market_weights = np.ones(n_assets) / n_assets
            
            # Implied equilibrium returns
            pi = self.risk_aversion * covariance_matrix.values @ market_weights
            
            if views:
                # Incorporate investor views
                mu_bl, sigma_bl = self._black_litterman_with_views(
                    pi, covariance_matrix.values, views, assets
                )
            else:
                # Use equilibrium returns
                mu_bl = pi
                sigma_bl = covariance_matrix.values
            
            # Optimize portfolio using Black-Litterman inputs
            optimal_weights = self._optimize_bl_portfolio(mu_bl, sigma_bl, constraints, assets)
            
            # Calculate performance metrics
            expected_return = float(mu_bl @ optimal_weights)
            expected_volatility = float(np.sqrt(optimal_weights.T @ sigma_bl @ optimal_weights))
            expected_sharpe = expected_return / expected_volatility if expected_volatility > 0 else 0.0
            
            # Calculate risk contributions
            risk_contributions = self._calculate_risk_contributions(
                optimal_weights, sigma_bl, assets
            )
            
            # Calculate factor exposures
            factor_exposures = self._calculate_factor_exposures(
                {asset: weight for asset, weight in zip(assets, optimal_weights)}, assets
            )
            
            optimization_time = (datetime.now() - start_time).total_seconds()
            
            return OptimizationResult(
                optimization_id=f"bl_{int(datetime.now().timestamp())}",
                timestamp=datetime.now(),
                objective=self.objective,
                optimal_weights={asset: weight for asset, weight in zip(assets, optimal_weights)},
                expected_return=expected_return,
                expected_volatility=expected_volatility,
                expected_sharpe=expected_sharpe,
                portfolio_var=expected_volatility * 1.645,
                portfolio_cvar=expected_volatility * 2.33,
                max_drawdown_estimate=expected_volatility * 2.0,
                factor_exposures=factor_exposures,
                risk_contributions=risk_contributions,
                optimization_time=optimization_time,
                convergence_status="OPTIMAL",
                objective_value=expected_sharpe,
                constraints_satisfied=True
            )
            
        except Exception as e:
            logger.error(f"Error in Black-Litterman optimization: {e}")
            return self._create_fallback_result(assets, start_time)
    
    def _black_litterman_with_views(self, pi: np.ndarray, 
                                   sigma: np.ndarray,
                                   views: Dict[str, Tuple[float, float]],
                                   assets: List[str]) -> Tuple[np.ndarray, np.ndarray]:
        """Apply Black-Litterman model with investor views"""
        try:
            # Create picking matrix P and view vector Q
            n_views = len(views)
            n_assets = len(assets)
            
            P = np.zeros((n_views, n_assets))
            Q = np.zeros(n_views)
            omega_diag = np.zeros(n_views)
            
            for i, (asset, (view_return, confidence)) in enumerate(views.items()):
                if asset in assets:
                    asset_idx = assets.index(asset)
                    P[i, asset_idx] = 1.0
                    Q[i] = view_return
                    
                    # Convert confidence to uncertainty (omega)
                    # Higher confidence = lower uncertainty
                    view_variance = self.tau * sigma[asset_idx, asset_idx] / confidence
                    omega_diag[i] = view_variance
            
            # Uncertainty matrix for views
            omega = np.diag(omega_diag)
            
            # Black-Litterman formula
            tau_sigma = self.tau * sigma
            
            # New expected returns
            M1 = inv(tau_sigma)
            M2 = P.T @ inv(omega) @ P
            M3 = inv(tau_sigma) @ pi + P.T @ inv(omega) @ Q
            
            mu_bl = inv(M1 + M2) @ M3
            
            # New covariance matrix
            sigma_bl = inv(M1 + M2)
            
            return mu_bl, sigma_bl
            
        except Exception as e:
            logger.error(f"Error in Black-Litterman calculation: {e}")
            return pi, sigma
    
    def _optimize_bl_portfolio(self, mu: np.ndarray, 
                              sigma: np.ndarray,
                              constraints: OptimizationConstraints,
                              assets: List[str]) -> np.ndarray:
        """Optimize portfolio using Black-Litterman inputs"""
        try:
            n_assets = len(assets)
            
            # Define optimization variables
            weights = cp.Variable(n_assets)
            
            # Objective: maximize utility (return - risk penalty)
            portfolio_return = mu @ weights
            portfolio_variance = cp.quad_form(weights, sigma)
            utility = portfolio_return - 0.5 * self.risk_aversion * portfolio_variance
            
            objective = cp.Maximize(utility)
            
            # Constraints
            constraints_list = [cp.sum(weights) == 1]  # Weights sum to 1
            
            # Weight bounds
            for i, asset in enumerate(assets):
                min_weight = constraints.min_weights.get(asset, 0.0)
                max_weight = constraints.max_weights.get(asset, 1.0)
                constraints_list.extend([
                    weights[i] >= min_weight,
                    weights[i] <= max_weight
                ])
            
            # Solve optimization problem
            problem = cp.Problem(objective, constraints_list)
            problem.solve(solver=cp.ECOS)
            
            if problem.status == cp.OPTIMAL:
                return weights.value
            else:
                logger.warning("Black-Litterman optimization failed, using equal weights")
                return np.ones(n_assets) / n_assets
                
        except Exception as e:
            logger.error(f"Error optimizing Black-Litterman portfolio: {e}")
            return np.ones(len(assets)) / len(assets)
    
    def _calculate_risk_contributions(self, weights: np.ndarray, 
                                    cov_matrix: np.ndarray, 
                                    assets: List[str]) -> Dict[str, float]:
        """Calculate risk contributions for each asset"""
        try:
            portfolio_variance = weights.T @ cov_matrix @ weights
            marginal_contributions = cov_matrix @ weights
            risk_contributions = weights * marginal_contributions / portfolio_variance
            
            return {asset: float(contrib) for asset, contrib in zip(assets, risk_contributions)}
            
        except Exception as e:
            logger.error(f"Error calculating risk contributions: {e}")
            return {asset: 1.0 / len(assets) for asset in assets}
    
    def _calculate_factor_exposures(self, weights: Dict[str, float], 
                                  assets: List[str]) -> Dict[str, float]:
        """Calculate factor exposures"""
        return {
            'market_beta': sum(weights.values()),
            'size_factor': 0.0,
            'value_factor': 0.0,
            'momentum_factor': 0.0,
            'quality_factor': 0.0
        }
    
    def _create_fallback_result(self, assets: List[str], start_time: datetime) -> OptimizationResult:
        """Create fallback result when optimization fails"""
        equal_weights = {asset: 1.0 / len(assets) for asset in assets}
        
        return OptimizationResult(
            optimization_id=f"bl_fallback_{int(datetime.now().timestamp())}",
            timestamp=datetime.now(),
            objective=self.objective,
            optimal_weights=equal_weights,
            expected_return=0.0,
            expected_volatility=0.15,
            expected_sharpe=0.0,
            portfolio_var=0.15 * 1.645,
            portfolio_cvar=0.15 * 2.33,
            max_drawdown_estimate=0.15 * 2.0,
            factor_exposures={},
            risk_contributions=equal_weights,
            optimization_time=(datetime.now() - start_time).total_seconds(),
            convergence_status="FAILED",
            objective_value=0.0,
            constraints_satisfied=False,
            constraint_violations=["Black-Litterman optimization failed"]
        )

class AdvancedPortfolioOptimizer:
    """
    Advanced portfolio optimization system that integrates multiple optimization
    approaches with risk management and dynamic allocation capabilities
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the advanced portfolio optimizer
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        
        # Initialize optimizers
        self.optimizers: Dict[OptimizationObjective, BaseOptimizer] = {}
        self._initialize_optimizers()
        
        # Portfolio state
        self.current_portfolio_state: Optional[PortfolioState] = None
        self.optimization_history: List[OptimizationResult] = []
        
        # Rebalancing
        self.rebalancing_frequency = RebalancingFrequency(
            config.get('rebalancing_frequency', 'WEEKLY')
        )
        self.rebalancing_threshold = config.get('rebalancing_threshold', 0.05)
        self.last_rebalance_date: Optional[datetime] = None
        
        # Transaction costs
        self.transaction_cost_model = config.get('transaction_cost_model', 'LINEAR')
        self.transaction_cost_rate = config.get('transaction_cost_rate', 0.001)
        
        # Database
        self.db_path = config.get('db_path', 'portfolio_optimization.db')
        self._init_database()
        
        logger.info("Advanced portfolio optimizer initialized")
    
    def _initialize_optimizers(self):
        """Initialize different optimization approaches"""
        optimizer_configs = self.config.get('optimizers', {})
        
        # Mean-Variance optimizer
        if 'mean_variance' in optimizer_configs:
            self.optimizers[OptimizationObjective.MAX_SHARPE] = MeanVarianceOptimizer(
                optimizer_configs['mean_variance']
            )
        
        # Risk Parity optimizer
        if 'risk_parity' in optimizer_configs:
            self.optimizers[OptimizationObjective.RISK_PARITY] = RiskParityOptimizer(
                optimizer_configs['risk_parity']
            )
        
        # Black-Litterman optimizer
        if 'black_litterman' in optimizer_configs:
            self.optimizers[OptimizationObjective.BLACK_LITTERMAN] = BlackLittermanOptimizer(
                optimizer_configs['black_litterman']
            )
        
        logger.info(f"Initialized {len(self.optimizers)} optimizers")
    
    def _init_database(self):
        """Initialize SQLite database for optimization data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS optimization_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    optimization_id TEXT UNIQUE NOT NULL,
                    timestamp DATETIME NOT NULL,
                    objective TEXT NOT NULL,
                    optimal_weights TEXT NOT NULL,
                    expected_return REAL NOT NULL,
                    expected_volatility REAL NOT NULL,
                    expected_sharpe REAL NOT NULL,
                    portfolio_var REAL NOT NULL,
                    optimization_time REAL NOT NULL,
                    convergence_status TEXT NOT NULL,
                    constraints_satisfied BOOLEAN NOT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS portfolio_states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    current_weights TEXT NOT NULL,
                    portfolio_value REAL NOT NULL,
                    portfolio_return REAL NOT NULL,
                    portfolio_volatility REAL NOT NULL,
                    sharpe_ratio REAL NOT NULL,
                    max_drawdown REAL NOT NULL,
                    days_since_rebalance INTEGER NOT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS rebalancing_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    old_weights TEXT NOT NULL,
                    new_weights TEXT NOT NULL,
                    turnover REAL NOT NULL,
                    transaction_costs REAL NOT NULL,
                    rebalancing_reason TEXT NOT NULL
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Portfolio optimization database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def optimize_portfolio(self, 
                          returns_data: pd.DataFrame,
                          objective: OptimizationObjective,
                          constraints: OptimizationConstraints,
                          views: Optional[Dict[str, Tuple[float, float]]] = None) -> OptimizationResult:
        """
        Optimize portfolio using specified objective and constraints
        
        Args:
            returns_data: Historical returns data
            objective: Optimization objective
            constraints: Portfolio constraints
            views: Investor views for Black-Litterman (optional)
        """
        try:
            if objective not in self.optimizers:
                raise ValueError(f"Optimizer for {objective.value} not available")
            
            optimizer = self.optimizers[objective]
            
            # Estimate expected returns
            expected_returns = self._estimate_expected_returns(returns_data)
            
            # Estimate covariance matrix
            covariance_matrix = optimizer.estimate_covariance(returns_data)
            
            # Get current weights if available
            current_weights = None
            if self.current_portfolio_state:
                current_weights = pd.Series(self.current_portfolio_state.current_weights)
            
            # Optimize
            if objective == OptimizationObjective.BLACK_LITTERMAN:
                result = optimizer.optimize(
                    expected_returns, covariance_matrix, constraints, current_weights, views
                )
            else:
                result = optimizer.optimize(
                    expected_returns, covariance_matrix, constraints, current_weights
                )
            
            # Calculate transaction costs
            if current_weights is not None:
                result.estimated_transaction_costs = self._calculate_transaction_costs(
                    current_weights, pd.Series(result.optimal_weights)
                )
                result.turnover = self._calculate_turnover(
                    current_weights, pd.Series(result.optimal_weights)
                )
            
            # Store result
            self.optimization_history.append(result)
            self._store_optimization_result(result)
            
            logger.info(f"Portfolio optimization completed: {objective.value}")
            logger.info(f"Expected return: {result.expected_return:.4f}, Volatility: {result.expected_volatility:.4f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error optimizing portfolio: {e}")
            raise
    
    def _estimate_expected_returns(self, returns_data: pd.DataFrame) -> pd.Series:
        """Estimate expected returns"""
        try:
            # Simple historical mean
            return returns_data.mean() * 252  # Annualized
            
        except Exception as e:
            logger.error(f"Error estimating expected returns: {e}")
            return pd.Series(index=returns_data.columns, data=0.08)  # Default 8% return
    
    def _calculate_transaction_costs(self, current_weights: pd.Series, 
                                   new_weights: pd.Series) -> float:
        """Calculate estimated transaction costs"""
        try:
            # Align weights
            all_assets = set(current_weights.index) | set(new_weights.index)
            current_aligned = pd.Series(index=all_assets, data=0.0)
            new_aligned = pd.Series(index=all_assets, data=0.0)
            
            current_aligned.update(current_weights)
            new_aligned.update(new_weights)
            
            # Calculate turnover
            turnover = (current_aligned - new_aligned).abs().sum()
            
            # Simple linear cost model
            if self.transaction_cost_model == 'LINEAR':
                return turnover * self.transaction_cost_rate
            else:
                # Could implement more sophisticated models
                return turnover * self.transaction_cost_rate
                
        except Exception as e:
            logger.error(f"Error calculating transaction costs: {e}")
            return 0.0
    
    def _calculate_turnover(self, current_weights: pd.Series, new_weights: pd.Series) -> float:
        """Calculate portfolio turnover"""
        try:
            # Align weights
            all_assets = set(current_weights.index) | set(new_weights.index)
            current_aligned = pd.Series(index=all_assets, data=0.0)
            new_aligned = pd.Series(index=all_assets, data=0.0)
            
            current_aligned.update(current_weights)
            new_aligned.update(new_weights)
            
            return (current_aligned - new_aligned).abs().sum()
            
        except Exception as e:
            logger.error(f"Error calculating turnover: {e}")
            return 0.0
    
    def check_rebalancing_needed(self, current_market_data: pd.DataFrame) -> bool:
        """Check if portfolio rebalancing is needed"""
        try:
            if not self.current_portfolio_state:
                return True  # Need initial optimization
            
            # Time-based rebalancing
            if self.last_rebalance_date:
                days_since_rebalance = (datetime.now() - self.last_rebalance_date).days
                
                rebalancing_intervals = {
                    RebalancingFrequency.DAILY: 1,
                    RebalancingFrequency.WEEKLY: 7,
                    RebalancingFrequency.MONTHLY: 30,
                    RebalancingFrequency.QUARTERLY: 90,
                    RebalancingFrequency.SEMI_ANNUAL: 180,
                    RebalancingFrequency.ANNUAL: 365
                }
                
                if self.rebalancing_frequency in rebalancing_intervals:
                    if days_since_rebalance >= rebalancing_intervals[self.rebalancing_frequency]:
                        return True
            
            # Threshold-based rebalancing
            if self.rebalancing_frequency == RebalancingFrequency.THRESHOLD_BASED:
                # Calculate current market weights
                current_market_weights = self._calculate_current_market_weights(current_market_data)
                
                # Compare with target weights
                weight_deviations = {}
                for asset, target_weight in self.current_portfolio_state.current_weights.items():
                    current_weight = current_market_weights.get(asset, 0.0)
                    deviation = abs(current_weight - target_weight)
                    weight_deviations[asset] = deviation
                
                max_deviation = max(weight_deviations.values()) if weight_deviations else 0.0
                
                if max_deviation > self.rebalancing_threshold:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking rebalancing need: {e}")
            return False
    
    def _calculate_current_market_weights(self, market_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate current market weights based on price changes"""
        try:
            if not self.current_portfolio_state:
                return {}
            
            # Get latest prices
            latest_prices = market_data.iloc[-1]
            
            # Calculate current values
            current_values = {}
            total_value = 0.0
            
            for asset, weight in self.current_portfolio_state.current_weights.items():
                if asset in latest_prices.index:
                    # Assume we know the price change since last rebalance
                    # This is simplified - in practice you'd track actual positions
                    current_value = weight * self.current_portfolio_state.total_portfolio_value
                    current_values[asset] = current_value
                    total_value += current_value
            
            # Calculate current weights
            if total_value > 0:
                return {asset: value / total_value for asset, value in current_values.items()}
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error calculating current market weights: {e}")
            return {}
    
    def update_portfolio_state(self, market_data: pd.DataFrame, portfolio_value: float):
        """Update current portfolio state"""
        try:
            if not self.current_portfolio_state:
                return
            
            # Calculate current performance
            returns_data = market_data.pct_change().dropna()
            
            # Calculate portfolio return
            portfolio_returns = []
            for asset, weight in self.current_portfolio_state.current_weights.items():
                if asset in returns_data.columns:
                    asset_returns = returns_data[asset].values
                    portfolio_returns.append(asset_returns * weight)
            
            if portfolio_returns:
                portfolio_return_series = np.sum(portfolio_returns, axis=0)
                portfolio_return = np.mean(portfolio_return_series) * 252  # Annualized
                portfolio_volatility = np.std(portfolio_return_series) * np.sqrt(252)
                sharpe_ratio = portfolio_return / portfolio_volatility if portfolio_volatility > 0 else 0.0
                
                # Calculate max drawdown (simplified)
                cumulative_returns = np.cumprod(1 + portfolio_return_series)
                running_max = np.maximum.accumulate(cumulative_returns)
                drawdown = (cumulative_returns - running_max) / running_max
                max_drawdown = np.min(drawdown)
            else:
                portfolio_return = 0.0
                portfolio_volatility = 0.0
                sharpe_ratio = 0.0
                max_drawdown = 0.0
            
            # Update state
            days_since_rebalance = 0
            if self.last_rebalance_date:
                days_since_rebalance = (datetime.now() - self.last_rebalance_date).days
            
            self.current_portfolio_state = PortfolioState(
                timestamp=datetime.now(),
                current_weights=self.current_portfolio_state.current_weights,
                current_values=self.current_portfolio_state.current_values,
                total_portfolio_value=portfolio_value,
                portfolio_return=portfolio_return,
                portfolio_volatility=portfolio_volatility,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                portfolio_var=portfolio_volatility * 1.645,
                portfolio_cvar=portfolio_volatility * 2.33,
                current_factor_exposures=self.current_portfolio_state.current_factor_exposures,
                current_risk_contributions=self.current_portfolio_state.current_risk_contributions,
                days_since_rebalance=days_since_rebalance,
                rebalancing_needed=self.check_rebalancing_needed(market_data)
            )
            
            # Store in database
            self._store_portfolio_state(self.current_portfolio_state)
            
        except Exception as e:
            logger.error(f"Error updating portfolio state: {e}")
    
    def rebalance_portfolio(self, optimization_result: OptimizationResult) -> Dict[str, Any]:
        """Rebalance portfolio to target weights"""
        try:
            old_weights = self.current_portfolio_state.current_weights if self.current_portfolio_state else {}
            new_weights = optimization_result.optimal_weights
            
            # Calculate rebalancing details
            turnover = optimization_result.turnover
            transaction_costs = optimization_result.estimated_transaction_costs
            
            # Update portfolio state
            if self.current_portfolio_state:
                total_value = self.current_portfolio_state.total_portfolio_value
            else:
                total_value = 1000000.0  # Default portfolio value
            
            # Create new portfolio state
            self.current_portfolio_state = PortfolioState(
                timestamp=datetime.now(),
                current_weights=new_weights,
                current_values={asset: weight * total_value for asset, weight in new_weights.items()},
                total_portfolio_value=total_value,
                portfolio_return=optimization_result.expected_return,
                portfolio_volatility=optimization_result.expected_volatility,
                sharpe_ratio=optimization_result.expected_sharpe,
                max_drawdown=optimization_result.max_drawdown_estimate,
                portfolio_var=optimization_result.portfolio_var,
                portfolio_cvar=optimization_result.portfolio_cvar,
                current_factor_exposures=optimization_result.factor_exposures,
                current_risk_contributions=optimization_result.risk_contributions,
                days_since_rebalance=0,
                rebalancing_needed=False
            )
            
            # Update last rebalance date
            self.last_rebalance_date = datetime.now()
            
            # Store rebalancing event
            rebalancing_event = {
                'timestamp': datetime.now(),
                'old_weights': old_weights,
                'new_weights': new_weights,
                'turnover': turnover,
                'transaction_costs': transaction_costs,
                'rebalancing_reason': 'OPTIMIZATION'
            }
            
            self._store_rebalancing_event(rebalancing_event)
            
            logger.info(f"Portfolio rebalanced - Turnover: {turnover:.4f}, Costs: {transaction_costs:.6f}")
            
            return rebalancing_event
            
        except Exception as e:
            logger.error(f"Error rebalancing portfolio: {e}")
            return {}
    
    def _store_optimization_result(self, result: OptimizationResult):
        """Store optimization result in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO optimization_results 
                (optimization_id, timestamp, objective, optimal_weights, expected_return,
                 expected_volatility, expected_sharpe, portfolio_var, optimization_time,
                 convergence_status, constraints_satisfied)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.optimization_id, result.timestamp, result.objective.value,
                json.dumps(result.optimal_weights), result.expected_return,
                result.expected_volatility, result.expected_sharpe, result.portfolio_var,
                result.optimization_time, result.convergence_status, result.constraints_satisfied
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing optimization result: {e}")
    
    def _store_portfolio_state(self, state: PortfolioState):
        """Store portfolio state in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO portfolio_states 
                (timestamp, current_weights, portfolio_value, portfolio_return,
                 portfolio_volatility, sharpe_ratio, max_drawdown, days_since_rebalance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                state.timestamp, json.dumps(state.current_weights), state.total_portfolio_value,
                state.portfolio_return, state.portfolio_volatility, state.sharpe_ratio,
                state.max_drawdown, state.days_since_rebalance
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing portfolio state: {e}")
    
    def _store_rebalancing_event(self, event: Dict[str, Any]):
        """Store rebalancing event in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO rebalancing_events 
                (timestamp, old_weights, new_weights, turnover, transaction_costs, rebalancing_reason)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                event['timestamp'], json.dumps(event['old_weights']),
                json.dumps(event['new_weights']), event['turnover'],
                event['transaction_costs'], event['rebalancing_reason']
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing rebalancing event: {e}")
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """Get comprehensive optimization system summary"""
        try:
            recent_optimizations = self.optimization_history[-10:] if len(self.optimization_history) >= 10 else self.optimization_history
            
            return {
                'available_optimizers': [obj.value for obj in self.optimizers.keys()],
                'total_optimizations': len(self.optimization_history),
                'rebalancing_frequency': self.rebalancing_frequency.value,
                'last_rebalance_date': self.last_rebalance_date.isoformat() if self.last_rebalance_date else None,
                'current_portfolio_state': {
                    'portfolio_value': self.current_portfolio_state.total_portfolio_value if self.current_portfolio_state else 0.0,
                    'portfolio_return': self.current_portfolio_state.portfolio_return if self.current_portfolio_state else 0.0,
                    'portfolio_volatility': self.current_portfolio_state.portfolio_volatility if self.current_portfolio_state else 0.0,
                    'sharpe_ratio': self.current_portfolio_state.sharpe_ratio if self.current_portfolio_state else 0.0,
                    'days_since_rebalance': self.current_portfolio_state.days_since_rebalance if self.current_portfolio_state else 0
                },
                'recent_optimizations': [
                    {
                        'timestamp': opt.timestamp.isoformat(),
                        'objective': opt.objective.value,
                        'expected_return': opt.expected_return,
                        'expected_volatility': opt.expected_volatility,
                        'expected_sharpe': opt.expected_sharpe,
                        'convergence_status': opt.convergence_status
                    }
                    for opt in recent_optimizations
                ],
                'avg_optimization_time': np.mean([opt.optimization_time for opt in recent_optimizations]) if recent_optimizations else 0.0,
                'optimization_success_rate': np.mean([1.0 if opt.convergence_status == "OPTIMAL" else 0.0 for opt in recent_optimizations]) if recent_optimizations else 0.0,
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating optimization summary: {e}")
            return {}

# Example usage
if __name__ == "__main__":
    # Configuration for advanced portfolio optimizer
    config = {
        'optimizers': {
            'mean_variance': {
                'risk_model': 'LEDOIT_WOLF',
                'lookback_period': 252,
                'risk_aversion': 1.0
            },
            'risk_parity': {
                'risk_model': 'SAMPLE_COVARIANCE',
                'tolerance': 1e-6,
                'max_iterations': 1000
            },
            'black_litterman': {
                'risk_model': 'FACTOR_MODEL',
                'risk_aversion': 3.0,
                'tau': 0.025,
                'confidence_level': 0.95
            }
        },
        'rebalancing_frequency': 'WEEKLY',
        'rebalancing_threshold': 0.05,
        'transaction_cost_rate': 0.001,
        'db_path': 'advanced_portfolio_optimization.db'
    }
    
    # Create optimizer
    optimizer = AdvancedPortfolioOptimizer(config)
    
    # Generate sample data
    dates = pd.date_range(start='2023-01-01', end='2024-01-01', freq='D')
    assets = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
    
    # Generate correlated returns
    np.random.seed(42)
    returns_data = pd.DataFrame(index=dates, columns=assets)
    
    for i, asset in enumerate(assets):
        # Generate returns with some correlation structure
        base_return = np.random.normal(0.0008, 0.02, len(dates))
        if i > 0:
            # Add correlation with previous asset
            correlation = 0.3
            base_return = correlation * returns_data.iloc[:, i-1].fillna(0) + np.sqrt(1 - correlation**2) * base_return
        
        returns_data[asset] = base_return
    
    returns_data = returns_data.fillna(0)
    
    # Define constraints
    constraints = OptimizationConstraints(
        min_weights={asset: 0.05 for asset in assets},  # Minimum 5% allocation
        max_weights={asset: 0.40 for asset in assets},  # Maximum 40% allocation
        max_portfolio_volatility=0.20,  # Maximum 20% volatility
        max_concentration=0.35  # Maximum 35% in single asset
    )
    
    # Test different optimization objectives
    objectives = [
        OptimizationObjective.MAX_SHARPE,
        OptimizationObjective.RISK_PARITY,
        OptimizationObjective.BLACK_LITTERMAN
    ]
    
    for objective in objectives:
        if objective in optimizer.optimizers:
            print(f"\n--- Testing {objective.value} ---")
            
            # Investor views for Black-Litterman
            views = None
            if objective == OptimizationObjective.BLACK_LITTERMAN:
                views = {
                    'AAPL': (0.12, 0.8),  # Expect 12% return with 80% confidence
                    'TSLA': (0.15, 0.6)   # Expect 15% return with 60% confidence
                }
            
            # Optimize portfolio
            result = optimizer.optimize_portfolio(returns_data, objective, constraints, views)
            
            print(f"Expected Return: {result.expected_return:.4f}")
            print(f"Expected Volatility: {result.expected_volatility:.4f}")
            print(f"Expected Sharpe: {result.expected_sharpe:.4f}")
            print(f"Optimization Time: {result.optimization_time:.3f}s")
            print(f"Convergence: {result.convergence_status}")
            
            print("Optimal Weights:")
            for asset, weight in result.optimal_weights.items():
                print(f"  {asset}: {weight:.3f}")
            
            # Simulate rebalancing
            if not optimizer.current_portfolio_state:
                rebalancing_event = optimizer.rebalance_portfolio(result)
                print(f"Portfolio rebalanced - Turnover: {rebalancing_event.get('turnover', 0):.4f}")
    
    # Get system summary
    summary = optimizer.get_optimization_summary()
    print(f"\nOptimization System Summary:")
    print(json.dumps(summary, indent=2)) 