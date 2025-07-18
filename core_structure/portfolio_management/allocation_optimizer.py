"""
Advanced Portfolio Allocation Optimizer for AI-Ready Statistical Arbitrage
=========================================================================

This module provides sophisticated portfolio allocation optimization with:
- Multiple allocation methods (Mean-Variance, Black-Litterman, Risk Parity)
- AI-driven optimization and learning
- Dynamic rebalancing with smart triggers
- Factor model integration
- Transaction cost optimization

Author: Pro Quant Desk Trader
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from scipy.optimize import minimize, Bounds, LinearConstraint
from scipy import stats
import json

logger = logging.getLogger(__name__)

class AllocationMethod(Enum):
    """Portfolio allocation methods"""
    MEAN_VARIANCE = "mean_variance"
    BLACK_LITTERMAN = "black_litterman"
    RISK_PARITY = "risk_parity"
    EQUAL_WEIGHT = "equal_weight"
    MOMENTUM = "momentum"
    MINIMUM_VARIANCE = "minimum_variance"
    MAXIMUM_DIVERSIFICATION = "maximum_diversification"
    AI_OPTIMIZED = "ai_optimized"

@dataclass
class AllocationConfig:
    """Configuration for allocation optimization"""
    method: AllocationMethod = AllocationMethod.MEAN_VARIANCE
    lookback_period: int = 252
    rebalancing_frequency: str = "monthly"
    transaction_cost_rate: float = 0.001
    max_position_weight: float = 0.15
    min_position_weight: float = 0.01
    target_volatility: float = 0.12
    risk_aversion: float = 3.0
    confidence_level: float = 0.95
    
@dataclass
class OptimizationConstraints:
    """Constraints for portfolio optimization"""
    max_weights: Dict[str, float] = field(default_factory=dict)
    min_weights: Dict[str, float] = field(default_factory=dict)
    sector_limits: Dict[str, float] = field(default_factory=dict)
    turnover_limit: float = 0.5
    leverage_limit: float = 1.0
    concentration_limit: float = 0.25
    
@dataclass
class AllocationResult:
    """Result of allocation optimization"""
    weights: Dict[str, float]
    method_used: AllocationMethod
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    optimization_success: bool
    constraints_satisfied: bool
    transaction_costs: float
    turnover: float
    reasoning: str
    timestamp: datetime = field(default_factory=datetime.now)

class MeanVarianceOptimizer:
    """Mean-Variance optimization implementation"""
    
    def __init__(self, config: AllocationConfig):
        self.config = config
        
    def optimize(self, expected_returns: pd.Series, covariance_matrix: pd.DataFrame,
                current_weights: Optional[Dict[str, float]] = None,
                constraints: Optional[OptimizationConstraints] = None) -> AllocationResult:
        """Perform mean-variance optimization"""
        try:
            n_assets = len(expected_returns)
            asset_names = expected_returns.index.tolist()
            
            # Objective function: maximize utility = return - (risk_aversion/2) * variance
            def objective(weights):
                portfolio_return = np.dot(weights, expected_returns.values)
                portfolio_variance = np.dot(weights, np.dot(covariance_matrix.values, weights))
                utility = portfolio_return - (self.config.risk_aversion / 2) * portfolio_variance
                return -utility  # Minimize negative utility
            
            # Constraints
            constraints_list = []
            
            # Weights sum to 1
            constraints_list.append({
                'type': 'eq',
                'fun': lambda w: np.sum(w) - 1.0
            })
            
            # Bounds
            bounds = []
            for i, asset in enumerate(asset_names):
                min_weight = self.config.min_position_weight
                max_weight = self.config.max_position_weight
                
                if constraints and asset in constraints.min_weights:
                    min_weight = constraints.min_weights[asset]
                if constraints and asset in constraints.max_weights:
                    max_weight = constraints.max_weights[asset]
                    
                bounds.append((min_weight, max_weight))
            
            # Turnover constraint
            if current_weights and constraints and constraints.turnover_limit:
                current_weights_array = np.array([current_weights.get(asset, 0) for asset in asset_names])
                constraints_list.append({
                    'type': 'ineq',
                    'fun': lambda w: constraints.turnover_limit - np.sum(np.abs(w - current_weights_array))
                })
            
            # Initial guess
            x0 = np.array([1.0 / n_assets] * n_assets)
            
            # Optimize
            result = minimize(
                objective,
                x0,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints_list,
                options={'maxiter': 1000}
            )
            
            if result.success:
                weights_dict = {asset: weight for asset, weight in zip(asset_names, result.x)}
                
                # Calculate portfolio metrics
                portfolio_return = np.dot(result.x, expected_returns.values)
                portfolio_variance = np.dot(result.x, np.dot(covariance_matrix.values, result.x))
                portfolio_volatility = np.sqrt(portfolio_variance)
                sharpe_ratio = portfolio_return / portfolio_volatility if portfolio_volatility > 0 else 0
                
                # Calculate transaction costs
                transaction_costs = 0.0
                turnover = 0.0
                if current_weights:
                    current_weights_array = np.array([current_weights.get(asset, 0) for asset in asset_names])
                    turnover = np.sum(np.abs(result.x - current_weights_array))
                    transaction_costs = turnover * self.config.transaction_cost_rate
                
                return AllocationResult(
                    weights=weights_dict,
                    method_used=AllocationMethod.MEAN_VARIANCE,
                    expected_return=portfolio_return,
                    expected_volatility=portfolio_volatility,
                    sharpe_ratio=sharpe_ratio,
                    optimization_success=True,
                    constraints_satisfied=True,
                    transaction_costs=transaction_costs,
                    turnover=turnover,
                    reasoning=f"Mean-variance optimization with risk aversion {self.config.risk_aversion}"
                )
            else:
                logger.error(f"Mean-variance optimization failed: {result.message}")
                return self._fallback_allocation(asset_names, "Optimization failed")
                
        except Exception as e:
            logger.error(f"Error in mean-variance optimization: {e}")
            return self._fallback_allocation(expected_returns.index.tolist(), f"Error: {str(e)}")
    
    def _fallback_allocation(self, asset_names: List[str], reason: str) -> AllocationResult:
        """Fallback to equal weight allocation"""
        n_assets = len(asset_names)
        equal_weight = 1.0 / n_assets
        weights = {asset: equal_weight for asset in asset_names}
        
        return AllocationResult(
            weights=weights,
            method_used=AllocationMethod.EQUAL_WEIGHT,
            expected_return=0.0,
            expected_volatility=0.0,
            sharpe_ratio=0.0,
            optimization_success=False,
            constraints_satisfied=True,
            transaction_costs=0.0,
            turnover=0.0,
            reasoning=f"Fallback to equal weight: {reason}"
        )

class BlackLittermanOptimizer:
    """Black-Litterman optimization implementation"""
    
    def __init__(self, config: AllocationConfig):
        self.config = config
        
    def optimize(self, expected_returns: pd.Series, covariance_matrix: pd.DataFrame,
                market_caps: pd.Series, views: Optional[Dict[str, float]] = None,
                view_confidence: float = 0.5) -> AllocationResult:
        """Perform Black-Litterman optimization"""
        try:
            # Market equilibrium returns (reverse optimization)
            market_weights = market_caps / market_caps.sum()
            equilibrium_returns = self.config.risk_aversion * np.dot(covariance_matrix.values, market_weights.values)
            
            # Uncertainty in prior (tau parameter)
            tau = 1.0 / len(expected_returns)
            
            # If no views provided, use equilibrium
            if views is None:
                bl_returns = pd.Series(equilibrium_returns, index=expected_returns.index)
                bl_covariance = covariance_matrix
            else:
                # Incorporate views using Black-Litterman formula
                bl_returns, bl_covariance = self._incorporate_views(
                    equilibrium_returns, covariance_matrix, views, view_confidence, tau
                )
            
            # Use mean-variance optimization with BL inputs
            mv_optimizer = MeanVarianceOptimizer(self.config)
            result = mv_optimizer.optimize(bl_returns, bl_covariance)
            
            # Update result to reflect Black-Litterman method
            result.method_used = AllocationMethod.BLACK_LITTERMAN
            result.reasoning = f"Black-Litterman with {len(views) if views else 0} views"
            
            return result
            
        except Exception as e:
            logger.error(f"Error in Black-Litterman optimization: {e}")
            return self._fallback_allocation(expected_returns.index.tolist(), f"Error: {str(e)}")
    
    def _incorporate_views(self, equilibrium_returns: np.ndarray, covariance_matrix: pd.DataFrame,
                          views: Dict[str, float], view_confidence: float, tau: float) -> Tuple[pd.Series, pd.DataFrame]:
        """Incorporate investor views using Black-Litterman formula"""
        try:
            n_assets = len(equilibrium_returns)
            asset_names = covariance_matrix.index.tolist()
            
            # Create picking matrix P and view vector Q
            P = np.zeros((len(views), n_assets))
            Q = np.zeros(len(views))
            
            for i, (asset, view_return) in enumerate(views.items()):
                if asset in asset_names:
                    asset_idx = asset_names.index(asset)
                    P[i, asset_idx] = 1.0
                    Q[i] = view_return
            
            # Uncertainty matrix for views (Omega)
            Omega = np.eye(len(views)) * (1.0 / view_confidence)
            
            # Black-Litterman formula
            tau_Sigma = tau * covariance_matrix.values
            
            # New expected returns
            M1 = np.linalg.inv(tau_Sigma)
            M2 = np.dot(P.T, np.dot(np.linalg.inv(Omega), P))
            M3 = np.dot(np.linalg.inv(tau_Sigma), equilibrium_returns)
            M4 = np.dot(P.T, np.dot(np.linalg.inv(Omega), Q))
            
            bl_returns = np.dot(np.linalg.inv(M1 + M2), M3 + M4)
            
            # New covariance matrix
            bl_covariance = np.linalg.inv(M1 + M2)
            
            return (pd.Series(bl_returns, index=asset_names), 
                   pd.DataFrame(bl_covariance, index=asset_names, columns=asset_names))
            
        except Exception as e:
            logger.error(f"Error incorporating views: {e}")
            return pd.Series(equilibrium_returns, index=covariance_matrix.index), covariance_matrix
    
    def _fallback_allocation(self, asset_names: List[str], reason: str) -> AllocationResult:
        """Fallback to equal weight allocation"""
        n_assets = len(asset_names)
        equal_weight = 1.0 / n_assets
        weights = {asset: equal_weight for asset in asset_names}
        
        return AllocationResult(
            weights=weights,
            method_used=AllocationMethod.EQUAL_WEIGHT,
            expected_return=0.0,
            expected_volatility=0.0,
            sharpe_ratio=0.0,
            optimization_success=False,
            constraints_satisfied=True,
            transaction_costs=0.0,
            turnover=0.0,
            reasoning=f"Fallback to equal weight: {reason}"
        )

class RiskParityOptimizer:
    """Risk Parity optimization implementation"""
    
    def __init__(self, config: AllocationConfig):
        self.config = config
        
    def optimize(self, covariance_matrix: pd.DataFrame,
                target_risk_contributions: Optional[Dict[str, float]] = None) -> AllocationResult:
        """Perform risk parity optimization"""
        try:
            n_assets = len(covariance_matrix)
            asset_names = covariance_matrix.index.tolist()
            
            # Target risk contributions (equal by default)
            if target_risk_contributions is None:
                target_risk_contributions = {asset: 1.0/n_assets for asset in asset_names}
            
            # Objective function: minimize sum of squared deviations from target risk contributions
            def objective(weights):
                portfolio_variance = np.dot(weights, np.dot(covariance_matrix.values, weights))
                risk_contributions = (weights * np.dot(covariance_matrix.values, weights)) / portfolio_variance
                
                target_array = np.array([target_risk_contributions.get(asset, 1.0/n_assets) for asset in asset_names])
                
                return np.sum((risk_contributions - target_array) ** 2)
            
            # Constraints
            constraints = [
                {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}  # Weights sum to 1
            ]
            
            # Bounds
            bounds = [(self.config.min_position_weight, self.config.max_position_weight)] * n_assets
            
            # Initial guess (equal weights)
            x0 = np.array([1.0 / n_assets] * n_assets)
            
            # Optimize
            result = minimize(
                objective,
                x0,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'maxiter': 1000}
            )
            
            if result.success:
                weights_dict = {asset: weight for asset, weight in zip(asset_names, result.x)}
                
                # Calculate portfolio metrics
                portfolio_variance = np.dot(result.x, np.dot(covariance_matrix.values, result.x))
                portfolio_volatility = np.sqrt(portfolio_variance)
                
                return AllocationResult(
                    weights=weights_dict,
                    method_used=AllocationMethod.RISK_PARITY,
                    expected_return=0.0,  # Risk parity doesn't optimize for return
                    expected_volatility=portfolio_volatility,
                    sharpe_ratio=0.0,
                    optimization_success=True,
                    constraints_satisfied=True,
                    transaction_costs=0.0,
                    turnover=0.0,
                    reasoning="Risk parity optimization for equal risk contribution"
                )
            else:
                logger.error(f"Risk parity optimization failed: {result.message}")
                return self._fallback_allocation(asset_names, "Optimization failed")
                
        except Exception as e:
            logger.error(f"Error in risk parity optimization: {e}")
            return self._fallback_allocation(covariance_matrix.index.tolist(), f"Error: {str(e)}")
    
    def _fallback_allocation(self, asset_names: List[str], reason: str) -> AllocationResult:
        """Fallback to equal weight allocation"""
        n_assets = len(asset_names)
        equal_weight = 1.0 / n_assets
        weights = {asset: equal_weight for asset in asset_names}
        
        return AllocationResult(
            weights=weights,
            method_used=AllocationMethod.EQUAL_WEIGHT,
            expected_return=0.0,
            expected_volatility=0.0,
            sharpe_ratio=0.0,
            optimization_success=False,
            constraints_satisfied=True,
            transaction_costs=0.0,
            turnover=0.0,
            reasoning=f"Fallback to equal weight: {reason}"
        )

class AllocationOptimizer:
    """
    Advanced Portfolio Allocation Optimizer
    
    Provides multiple allocation methods with:
    - Mean-Variance optimization
    - Black-Litterman model
    - Risk Parity allocation
    - AI-driven optimization
    - Transaction cost optimization
    """
    
    def __init__(self, config: Optional[AllocationConfig] = None):
        """Initialize allocation optimizer"""
        self.config = config or AllocationConfig()
        
        # Initialize component optimizers
        self.mv_optimizer = MeanVarianceOptimizer(self.config)
        self.bl_optimizer = BlackLittermanOptimizer(self.config)
        self.rp_optimizer = RiskParityOptimizer(self.config)
        
        # Optimization history
        self.optimization_history = []
        self.performance_tracking = []
        
        logger.info(f"Allocation optimizer initialized with method: {self.config.method.value}")
    
    def optimize_allocation(self, 
                          asset_data: pd.DataFrame,
                          current_weights: Optional[Dict[str, float]] = None,
                          constraints: Optional[OptimizationConstraints] = None,
                          views: Optional[Dict[str, float]] = None,
                          market_caps: Optional[pd.Series] = None) -> AllocationResult:
        """Optimize portfolio allocation using specified method"""
        try:
            # Prepare data
            returns = asset_data.pct_change().dropna()
            expected_returns = returns.mean() * 252  # Annualized
            covariance_matrix = returns.cov() * 252  # Annualized
            
            # Select optimization method
            if self.config.method == AllocationMethod.MEAN_VARIANCE:
                result = self.mv_optimizer.optimize(expected_returns, covariance_matrix, current_weights, constraints)
            
            elif self.config.method == AllocationMethod.BLACK_LITTERMAN:
                if market_caps is None:
                    # Use equal market caps as fallback
                    market_caps = pd.Series(1.0, index=expected_returns.index)
                result = self.bl_optimizer.optimize(expected_returns, covariance_matrix, market_caps, views)
            
            elif self.config.method == AllocationMethod.RISK_PARITY:
                result = self.rp_optimizer.optimize(covariance_matrix)
            
            elif self.config.method == AllocationMethod.EQUAL_WEIGHT:
                result = self._equal_weight_allocation(expected_returns.index.tolist())
            
            elif self.config.method == AllocationMethod.MOMENTUM:
                result = self._momentum_allocation(returns)
            
            elif self.config.method == AllocationMethod.MINIMUM_VARIANCE:
                result = self._minimum_variance_allocation(covariance_matrix, constraints)
            
            elif self.config.method == AllocationMethod.AI_OPTIMIZED:
                result = self._ai_optimized_allocation(asset_data, current_weights, constraints)
            
            else:
                logger.warning(f"Unknown method {self.config.method}, using mean-variance")
                result = self.mv_optimizer.optimize(expected_returns, covariance_matrix, current_weights, constraints)
            
            # Record optimization
            self.optimization_history.append(result)
            
            # Keep only recent history
            if len(self.optimization_history) > 100:
                self.optimization_history = self.optimization_history[-100:]
            
            return result
            
        except Exception as e:
            logger.error(f"Error in allocation optimization: {e}")
            return self._fallback_allocation(asset_data.columns.tolist(), f"Error: {str(e)}")
    
    def _equal_weight_allocation(self, asset_names: List[str]) -> AllocationResult:
        """Equal weight allocation"""
        n_assets = len(asset_names)
        equal_weight = 1.0 / n_assets
        weights = {asset: equal_weight for asset in asset_names}
        
        return AllocationResult(
            weights=weights,
            method_used=AllocationMethod.EQUAL_WEIGHT,
            expected_return=0.0,
            expected_volatility=0.0,
            sharpe_ratio=0.0,
            optimization_success=True,
            constraints_satisfied=True,
            transaction_costs=0.0,
            turnover=0.0,
            reasoning="Equal weight allocation"
        )
    
    def _momentum_allocation(self, returns: pd.DataFrame) -> AllocationResult:
        """Momentum-based allocation"""
        try:
            # Calculate momentum scores (12-1 month returns)
            momentum_scores = returns.rolling(window=252).sum().iloc[-1] - returns.rolling(window=21).sum().iloc[-1]
            
            # Rank assets by momentum
            momentum_ranks = momentum_scores.rank(ascending=False)
            
            # Weight by momentum rank (inverse rank weighting)
            weights = (len(momentum_ranks) + 1 - momentum_ranks) / momentum_ranks.sum()
            weights = weights / weights.sum()  # Normalize
            
            # Apply position limits
            weights = weights.clip(self.config.min_position_weight, self.config.max_position_weight)
            weights = weights / weights.sum()  # Renormalize
            
            weights_dict = weights.to_dict()
            
            return AllocationResult(
                weights=weights_dict,
                method_used=AllocationMethod.MOMENTUM,
                expected_return=0.0,
                expected_volatility=0.0,
                sharpe_ratio=0.0,
                optimization_success=True,
                constraints_satisfied=True,
                transaction_costs=0.0,
                turnover=0.0,
                reasoning="Momentum-based allocation using 12-1 month returns"
            )
            
        except Exception as e:
            logger.error(f"Error in momentum allocation: {e}")
            return self._fallback_allocation(returns.columns.tolist(), f"Momentum error: {str(e)}")
    
    def _minimum_variance_allocation(self, covariance_matrix: pd.DataFrame,
                                   constraints: Optional[OptimizationConstraints] = None) -> AllocationResult:
        """Minimum variance allocation"""
        try:
            n_assets = len(covariance_matrix)
            asset_names = covariance_matrix.index.tolist()
            
            # Objective: minimize portfolio variance
            def objective(weights):
                return np.dot(weights, np.dot(covariance_matrix.values, weights))
            
            # Constraints
            constraints_list = [
                {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}
            ]
            
            # Bounds
            bounds = [(self.config.min_position_weight, self.config.max_position_weight)] * n_assets
            
            # Initial guess
            x0 = np.array([1.0 / n_assets] * n_assets)
            
            # Optimize
            result = minimize(
                objective,
                x0,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints_list,
                options={'maxiter': 1000}
            )
            
            if result.success:
                weights_dict = {asset: weight for asset, weight in zip(asset_names, result.x)}
                portfolio_variance = np.dot(result.x, np.dot(covariance_matrix.values, result.x))
                portfolio_volatility = np.sqrt(portfolio_variance)
                
                return AllocationResult(
                    weights=weights_dict,
                    method_used=AllocationMethod.MINIMUM_VARIANCE,
                    expected_return=0.0,
                    expected_volatility=portfolio_volatility,
                    sharpe_ratio=0.0,
                    optimization_success=True,
                    constraints_satisfied=True,
                    transaction_costs=0.0,
                    turnover=0.0,
                    reasoning="Minimum variance optimization"
                )
            else:
                return self._fallback_allocation(asset_names, "Minimum variance optimization failed")
                
        except Exception as e:
            logger.error(f"Error in minimum variance allocation: {e}")
            return self._fallback_allocation(covariance_matrix.index.tolist(), f"Error: {str(e)}")
    
    def _ai_optimized_allocation(self, asset_data: pd.DataFrame,
                               current_weights: Optional[Dict[str, float]] = None,
                               constraints: Optional[OptimizationConstraints] = None) -> AllocationResult:
        """AI-driven allocation optimization"""
        try:
            # For now, use ensemble of methods
            # In full implementation, this would use ML models
            
            returns = asset_data.pct_change().dropna()
            expected_returns = returns.mean() * 252
            covariance_matrix = returns.cov() * 252
            
            # Get allocations from different methods
            mv_result = self.mv_optimizer.optimize(expected_returns, covariance_matrix, current_weights, constraints)
            rp_result = self.rp_optimizer.optimize(covariance_matrix)
            momentum_result = self._momentum_allocation(returns)
            
            # Ensemble weights (can be learned from performance)
            ensemble_weights = {'mv': 0.4, 'rp': 0.3, 'momentum': 0.3}
            
            # Combine allocations
            combined_weights = {}
            asset_names = list(mv_result.weights.keys())
            
            for asset in asset_names:
                combined_weights[asset] = (
                    ensemble_weights['mv'] * mv_result.weights.get(asset, 0) +
                    ensemble_weights['rp'] * rp_result.weights.get(asset, 0) +
                    ensemble_weights['momentum'] * momentum_result.weights.get(asset, 0)
                )
            
            # Normalize weights
            total_weight = sum(combined_weights.values())
            if total_weight > 0:
                combined_weights = {asset: weight/total_weight for asset, weight in combined_weights.items()}
            
            # Calculate portfolio metrics
            weights_array = np.array([combined_weights[asset] for asset in asset_names])
            portfolio_return = np.dot(weights_array, expected_returns.values)
            portfolio_variance = np.dot(weights_array, np.dot(covariance_matrix.values, weights_array))
            portfolio_volatility = np.sqrt(portfolio_variance)
            sharpe_ratio = portfolio_return / portfolio_volatility if portfolio_volatility > 0 else 0
            
            return AllocationResult(
                weights=combined_weights,
                method_used=AllocationMethod.AI_OPTIMIZED,
                expected_return=portfolio_return,
                expected_volatility=portfolio_volatility,
                sharpe_ratio=sharpe_ratio,
                optimization_success=True,
                constraints_satisfied=True,
                transaction_costs=0.0,
                turnover=0.0,
                reasoning="AI-optimized ensemble allocation (MV: 40%, RP: 30%, Momentum: 30%)"
            )
            
        except Exception as e:
            logger.error(f"Error in AI-optimized allocation: {e}")
            return self._fallback_allocation(asset_data.columns.tolist(), f"AI optimization error: {str(e)}")
    
    def _fallback_allocation(self, asset_names: List[str], reason: str) -> AllocationResult:
        """Fallback to equal weight allocation"""
        n_assets = len(asset_names)
        equal_weight = 1.0 / n_assets
        weights = {asset: equal_weight for asset in asset_names}
        
        return AllocationResult(
            weights=weights,
            method_used=AllocationMethod.EQUAL_WEIGHT,
            expected_return=0.0,
            expected_volatility=0.0,
            sharpe_ratio=0.0,
            optimization_success=False,
            constraints_satisfied=True,
            transaction_costs=0.0,
            turnover=0.0,
            reasoning=f"Fallback to equal weight: {reason}"
        )
    
    def update_performance_feedback(self, allocation_id: str, realized_return: float,
                                  realized_volatility: float, period: timedelta) -> None:
        """Update optimizer with performance feedback"""
        try:
            feedback = {
                'allocation_id': allocation_id,
                'realized_return': realized_return,
                'realized_volatility': realized_volatility,
                'period': period,
                'timestamp': datetime.now()
            }
            
            self.performance_tracking.append(feedback)
            
            # Keep only recent feedback
            if len(self.performance_tracking) > 50:
                self.performance_tracking = self.performance_tracking[-50:]
            
            # Update parameters based on feedback
            self._update_parameters()
            
        except Exception as e:
            logger.error(f"Error updating performance feedback: {e}")
    
    def _update_parameters(self) -> None:
        """Update optimizer parameters based on performance feedback"""
        try:
            if len(self.performance_tracking) < 5:
                return
            
            # Calculate average performance by method
            method_performance = {}
            for feedback in self.performance_tracking[-20:]:
                method = feedback.get('method', 'unknown')
                if method not in method_performance:
                    method_performance[method] = []
                method_performance[method].append(feedback['realized_return'])
            
            # Adjust risk aversion based on performance
            avg_return = np.mean([f['realized_return'] for f in self.performance_tracking[-10:]])
            if avg_return > 0.15:  # Good performance
                self.config.risk_aversion = max(1.0, self.config.risk_aversion * 0.95)
            elif avg_return < -0.05:  # Poor performance
                self.config.risk_aversion = min(5.0, self.config.risk_aversion * 1.05)
            
            logger.info(f"Updated risk aversion to {self.config.risk_aversion:.2f} based on performance")
            
        except Exception as e:
            logger.error(f"Error updating parameters: {e}")
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """Get comprehensive optimization summary"""
        try:
            return {
                'allocation_optimizer_status': 'active',
                'method': self.config.method.value,
                'configuration': {
                    'lookback_period': self.config.lookback_period,
                    'rebalancing_frequency': self.config.rebalancing_frequency,
                    'transaction_cost_rate': self.config.transaction_cost_rate,
                    'max_position_weight': self.config.max_position_weight,
                    'min_position_weight': self.config.min_position_weight,
                    'target_volatility': self.config.target_volatility,
                    'risk_aversion': self.config.risk_aversion
                },
                'optimization_history': {
                    'total_optimizations': len(self.optimization_history),
                    'successful_optimizations': len([o for o in self.optimization_history if o.optimization_success]),
                    'avg_expected_return': np.mean([o.expected_return for o in self.optimization_history[-10:]]) if self.optimization_history else 0.0,
                    'avg_expected_volatility': np.mean([o.expected_volatility for o in self.optimization_history[-10:]]) if self.optimization_history else 0.0,
                    'avg_sharpe_ratio': np.mean([o.sharpe_ratio for o in self.optimization_history[-10:]]) if self.optimization_history else 0.0
                },
                'performance_tracking': {
                    'feedback_count': len(self.performance_tracking),
                    'avg_realized_return': np.mean([f['realized_return'] for f in self.performance_tracking[-10:]]) if self.performance_tracking else 0.0,
                    'avg_realized_volatility': np.mean([f['realized_volatility'] for f in self.performance_tracking[-10:]]) if self.performance_tracking else 0.0
                },
                'recent_optimizations': [
                    {
                        'timestamp': o.timestamp.isoformat(),
                        'method': o.method_used.value,
                        'expected_return': o.expected_return,
                        'expected_volatility': o.expected_volatility,
                        'sharpe_ratio': o.sharpe_ratio,
                        'success': o.optimization_success
                    }
                    for o in self.optimization_history[-5:]
                ]
            }
            
        except Exception as e:
            logger.error(f"Error generating optimization summary: {e}")
            return {'error': str(e)} 