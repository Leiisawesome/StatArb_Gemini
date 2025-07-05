"""
Professional Multi-Pair Portfolio Optimization System
Implements correlation-based position sizing, dynamic rebalancing, and cross-asset risk allocation.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import logging
from scipy.optimize import minimize
from scipy.stats import pearsonr
import warnings

logger = logging.getLogger(__name__)

@dataclass
class PairInfo:
    """Information about a trading pair."""
    symbol1: str
    symbol2: str
    hedge_ratio: float
    spread_volatility: float
    correlation: float
    signal_strength: float
    current_spread: float
    z_score: float
    last_update: pd.Timestamp

@dataclass
class PortfolioConstraints:
    """Portfolio optimization constraints."""
    max_position_size: float = 0.15  # 15% max per position
    max_leverage: float = 2.0        # 2x max leverage
    target_volatility: float = 0.12  # 12% target vol
    min_correlation_threshold: float = 0.3  # Minimum correlation for pairs
    max_pairs: int = 10              # Maximum number of pairs
    rebalance_threshold: float = 0.05  # 5% rebalance threshold

class PortfolioOptimizer:
    """
    Professional portfolio optimizer for multi-pair statistical arbitrage.
    """
    
    def __init__(self, constraints: Optional[PortfolioConstraints] = None):
        self.constraints = constraints or PortfolioConstraints()
        self.pairs: Dict[str, PairInfo] = {}
        self.correlation_matrix = pd.DataFrame()
        self.volatility_estimates = {}
        self.position_weights = {}
        self.risk_metrics = {}
        
    def add_pair(self, pair_id: str, pair_info: PairInfo):
        """Add a trading pair to the portfolio."""
        self.pairs[pair_id] = pair_info
        logger.info(f"Added pair {pair_id}: {pair_info.symbol1}-{pair_info.symbol2}")
    
    def update_pair_info(self, pair_id: str, updates: Dict[str, Any]):
        """Update pair information."""
        if pair_id in self.pairs:
            pair = self.pairs[pair_id]
            for key, value in updates.items():
                if hasattr(pair, key):
                    setattr(pair, key, value)
            pair.last_update = pd.Timestamp.now()
    
    def calculate_correlation_matrix(self, returns_data: pd.DataFrame, lookback: int = 252):
        """
        Calculate rolling correlation matrix for all symbols.
        
        Args:
            returns_data: DataFrame with symbol returns
            lookback: Lookback period for correlation calculation
        """
        # Calculate rolling correlations
        symbols = returns_data.columns
        corr_matrix = pd.DataFrame(index=symbols, columns=symbols)
        
        for i, symbol1 in enumerate(symbols):
            for j, symbol2 in enumerate(symbols):
                if i == j:
                    corr_matrix.loc[symbol1, symbol2] = 1.0
                else:
                    # Calculate rolling correlation
                    rolling_corr = returns_data[symbol1].rolling(lookback).corr(returns_data[symbol2])
                    corr_matrix.loc[symbol1, symbol2] = rolling_corr.iloc[-1] if not pd.isna(rolling_corr.iloc[-1]) else 0.0
        
        self.correlation_matrix = corr_matrix
        logger.info(f"Updated correlation matrix for {len(symbols)} symbols")
    
    def update_volatility_estimates(self, returns_data: pd.DataFrame, lookback: int = 60):
        """
        Update volatility estimates for all symbols.
        
        Args:
            returns_data: DataFrame with symbol returns
            lookback: Lookback period for volatility calculation
        """
        for symbol in returns_data.columns:
            returns = returns_data[symbol].dropna()
            if len(returns) >= lookback:
                # Calculate rolling volatility (annualized)
                volatility = returns.rolling(lookback).std().iloc[-1] * np.sqrt(252)
                self.volatility_estimates[symbol] = volatility
        
        logger.info(f"Updated volatility estimates for {len(self.volatility_estimates)} symbols")
    
    def optimize_portfolio(self, 
                          target_return: float = 0.08,
                          risk_free_rate: float = 0.02) -> Dict[str, Any]:
        """
        Optimize portfolio weights using mean-variance optimization.
        
        Args:
            target_return: Target annual return
            risk_free_rate: Risk-free rate
            
        Returns:
            Optimization results
        """
        if not self.pairs:
            logger.warning("No pairs available for optimization")
            return {}
        
        # Prepare optimization inputs
        pair_ids = list(self.pairs.keys())
        n_pairs = len(pair_ids)
        
        # Calculate expected returns and risks for each pair
        expected_returns = []
        pair_volatilities = []
        
        for pair_id in pair_ids:
            pair = self.pairs[pair_id]
            
            # Expected return based on signal strength and spread
            expected_return = pair.signal_strength * pair.spread_volatility * 252
            expected_returns.append(expected_return)
            
            # Pair volatility
            pair_vol = pair.spread_volatility * np.sqrt(252)
            pair_volatilities.append(pair_vol)
        
        # Create covariance matrix
        covariance_matrix = self._create_covariance_matrix(pair_ids)
        
        # Optimization constraints
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},  # Weights sum to 1
            {'type': 'ineq', 'fun': lambda x: np.dot(expected_returns, x) - target_return}  # Target return
        ]
        
        # Bounds for weights
        bounds = [(0, self.constraints.max_position_size) for _ in range(n_pairs)]
        
        # Initial weights (equal weight)
        initial_weights = np.array([1.0 / n_pairs] * n_pairs)
        
        # Optimize
        try:
            result = minimize(
                fun=self._portfolio_variance,
                x0=initial_weights,
                args=(covariance_matrix,),
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'maxiter': 1000}
            )
            
            if result.success:
                optimal_weights = result.x
                portfolio_vol = np.sqrt(self._portfolio_variance(optimal_weights, covariance_matrix))
                portfolio_return = np.dot(expected_returns, optimal_weights)
                sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_vol
                
                # Store results
                self.position_weights = dict(zip(pair_ids, optimal_weights))
                
                return {
                    'optimal_weights': self.position_weights,
                    'portfolio_return': portfolio_return,
                    'portfolio_volatility': portfolio_vol,
                    'sharpe_ratio': sharpe_ratio,
                    'optimization_success': True,
                    'message': result.message
                }
            else:
                logger.warning(f"Optimization failed: {result.message}")
                return {'optimization_success': False, 'message': result.message}
                
        except Exception as e:
            logger.error(f"Optimization error: {str(e)}")
            return {'optimization_success': False, 'message': str(e)}
    
    def calculate_correlation_based_weights(self) -> Dict[str, float]:
        """
        Calculate position weights based on correlation structure.
        
        Returns:
            Correlation-based weights
        """
        if not self.pairs:
            return {}
        
        pair_ids = list(self.pairs.keys())
        weights = {}
        
        # Calculate correlation penalties
        correlation_penalties = {}
        for pair_id in pair_ids:
            pair = self.pairs[pair_id]
            
            # Calculate average correlation with other pairs
            correlations = []
            for other_id in pair_ids:
                if other_id != pair_id:
                    other_pair = self.pairs[other_id]
                    # Use correlation between the pair spreads
                    corr = abs(pair.correlation - other_pair.correlation)
                    correlations.append(corr)
            
            if correlations:
                avg_correlation = np.mean(correlations)
                # Higher correlation = lower weight
                correlation_penalties[pair_id] = 1.0 - avg_correlation * 0.5
            else:
                correlation_penalties[pair_id] = 1.0
        
        # Calculate base weights from signal strength
        total_signal = sum(abs(self.pairs[pid].signal_strength) for pid in pair_ids)
        
        for pair_id in pair_ids:
            pair = self.pairs[pair_id]
            base_weight = abs(pair.signal_strength) / total_signal if total_signal > 0 else 1.0 / len(pair_ids)
            
            # Apply correlation penalty
            correlation_weight = base_weight * correlation_penalties[pair_id]
            
            # Apply volatility adjustment
            volatility_adjustment = 1.0 / (pair.spread_volatility * np.sqrt(252)) if pair.spread_volatility > 0 else 1.0
            final_weight = correlation_weight * volatility_adjustment
            
            weights[pair_id] = final_weight
        
        # Normalize weights
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        
        # Apply position size constraints
        weights = self._apply_position_constraints(weights)
        
        self.position_weights = weights
        return weights
    
    def calculate_dynamic_rebalancing(self, 
                                    current_weights: Dict[str, float],
                                    price_changes: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate dynamic rebalancing adjustments.
        
        Args:
            current_weights: Current portfolio weights
            price_changes: Price changes for each pair
            
        Returns:
            Rebalancing adjustments
        """
        if not current_weights:
            return {}
        
        # Calculate new weights after price changes
        new_weights = {}
        total_value = 0
        
        for pair_id, current_weight in current_weights.items():
            price_change = price_changes.get(pair_id, 1.0)
            new_weight = current_weight * price_change
            new_weights[pair_id] = new_weight
            total_value += new_weight
        
        # Normalize new weights
        if total_value > 0:
            new_weights = {k: v / total_value for k, v in new_weights.items()}
        
        # Calculate rebalancing needs
        rebalancing = {}
        for pair_id in current_weights:
            weight_diff = new_weights.get(pair_id, 0) - current_weights[pair_id]
            
            # Only rebalance if difference exceeds threshold
            if abs(weight_diff) > self.constraints.rebalance_threshold:
                rebalancing[pair_id] = -weight_diff  # Negative to reverse the drift
        
        return rebalancing
    
    def calculate_risk_metrics(self) -> Dict[str, Any]:
        """
        Calculate comprehensive risk metrics for the portfolio.
        
        Returns:
            Risk metrics
        """
        if not self.position_weights:
            return {}
        
        # Calculate portfolio-level metrics
        total_weight = sum(self.position_weights.values())
        weighted_vol = 0
        weighted_return = 0
        
        for pair_id, weight in self.position_weights.items():
            pair = self.pairs[pair_id]
            weighted_vol += weight * pair.spread_volatility * np.sqrt(252)
            weighted_return += weight * pair.signal_strength * pair.spread_volatility * 252
        
        # Calculate diversification ratio
        diversification_ratio = self._calculate_diversification_ratio()
        
        # Calculate maximum drawdown estimate
        max_drawdown_estimate = self._estimate_max_drawdown()
        
        # Calculate VaR and CVaR
        var_95, cvar_95 = self._calculate_var_cvar(confidence_level=0.95)
        
        self.risk_metrics = {
            'portfolio_volatility': weighted_vol,
            'portfolio_return': weighted_return,
            'sharpe_ratio': weighted_return / weighted_vol if weighted_vol > 0 else 0,
            'diversification_ratio': diversification_ratio,
            'max_drawdown_estimate': max_drawdown_estimate,
            'var_95': var_95,
            'cvar_95': cvar_95,
            'concentration_risk': self._calculate_concentration_risk(),
            'correlation_risk': self._calculate_correlation_risk()
        }
        
        return self.risk_metrics
    
    def _create_covariance_matrix(self, pair_ids: List[str]) -> np.ndarray:
        """Create covariance matrix for pairs."""
        n_pairs = len(pair_ids)
        covariance_matrix = np.zeros((n_pairs, n_pairs))
        
        for i, pair_id1 in enumerate(pair_ids):
            for j, pair_id2 in enumerate(pair_ids):
                if i == j:
                    # Diagonal: variance of the pair
                    pair1 = self.pairs[pair_id1]
                    covariance_matrix[i, j] = (pair1.spread_volatility * np.sqrt(252)) ** 2
                else:
                    # Off-diagonal: covariance between pairs
                    pair1 = self.pairs[pair_id1]
                    pair2 = self.pairs[pair_id2]
                    
                    # Estimate covariance using correlation and volatilities
                    vol1 = pair1.spread_volatility * np.sqrt(252)
                    vol2 = pair2.spread_volatility * np.sqrt(252)
                    
                    # Use correlation between the pair spreads
                    correlation = abs(pair1.correlation - pair2.correlation)
                    covariance_matrix[i, j] = correlation * vol1 * vol2
        
        return covariance_matrix
    
    def _portfolio_variance(self, weights: np.ndarray, covariance_matrix: np.ndarray) -> float:
        """Calculate portfolio variance."""
        return np.dot(weights.T, np.dot(covariance_matrix, weights))
    
    def _apply_position_constraints(self, weights: Dict[str, float]) -> Dict[str, float]:
        """Apply position size constraints."""
        constrained_weights = {}
        
        for pair_id, weight in weights.items():
            constrained_weight = min(weight, self.constraints.max_position_size)
            constrained_weights[pair_id] = constrained_weight
        
        # Renormalize if needed
        total_weight = sum(constrained_weights.values())
        if total_weight > 0:
            constrained_weights = {k: v / total_weight for k, v in constrained_weights.items()}
        
        return constrained_weights
    
    def _calculate_diversification_ratio(self) -> float:
        """Calculate portfolio diversification ratio."""
        if not self.position_weights:
            return 0.0
        
        # Calculate weighted average volatility
        weighted_avg_vol = sum(
            weight * self.pairs[pair_id].spread_volatility * np.sqrt(252)
            for pair_id, weight in self.position_weights.items()
        )
        
        # Calculate portfolio volatility
        portfolio_vol = self._calculate_portfolio_volatility()
        
        return weighted_avg_vol / portfolio_vol if portfolio_vol > 0 else 0.0
    
    def _calculate_portfolio_volatility(self) -> float:
        """Calculate portfolio volatility."""
        if not self.position_weights:
            return 0.0
        
        # Simplified calculation - in practice, use full covariance matrix
        total_variance = 0
        for pair_id, weight in self.position_weights.items():
            pair_vol = self.pairs[pair_id].spread_volatility * np.sqrt(252)
            total_variance += (weight * pair_vol) ** 2
        
        return np.sqrt(total_variance)
    
    def _estimate_max_drawdown(self) -> float:
        """Estimate maximum drawdown using historical simulation."""
        if not self.position_weights:
            return 0.0
        
        # Simplified estimation based on volatility
        portfolio_vol = self._calculate_portfolio_volatility()
        # Rough estimate: max drawdown ≈ 2 * volatility
        return 2.0 * portfolio_vol
    
    def _calculate_var_cvar(self, confidence_level: float = 0.95) -> Tuple[float, float]:
        """Calculate Value at Risk and Conditional VaR."""
        if not self.position_weights:
            return 0.0, 0.0
        
        portfolio_vol = self._calculate_portfolio_volatility()
        
        # Assuming normal distribution
        from scipy.stats import norm
        z_score = norm.ppf(confidence_level)
        
        var = z_score * portfolio_vol
        cvar = norm.pdf(z_score) / (1 - confidence_level) * portfolio_vol
        
        return var, cvar
    
    def _calculate_concentration_risk(self) -> float:
        """Calculate concentration risk using Herfindahl index."""
        if not self.position_weights:
            return 0.0
        
        weights = list(self.position_weights.values())
        herfindahl = sum(w ** 2 for w in weights)
        
        # Normalize to 0-1 scale
        n_positions = len(weights)
        normalized_herfindahl = (herfindahl - 1/n_positions) / (1 - 1/n_positions) if n_positions > 1 else 0
        
        return normalized_herfindahl
    
    def _calculate_correlation_risk(self) -> float:
        """Calculate correlation risk."""
        if len(self.position_weights) < 2:
            return 0.0
        
        # Calculate average pairwise correlation
        pair_ids = list(self.position_weights.keys())
        correlations = []
        
        for i, pair_id1 in enumerate(pair_ids):
            for j, pair_id2 in enumerate(pair_ids):
                if i < j:
                    pair1 = self.pairs[pair_id1]
                    pair2 = self.pairs[pair_id2]
                    corr = abs(pair1.correlation - pair2.correlation)
                    correlations.append(corr)
        
        return np.mean(correlations) if correlations else 0.0

class CrossAssetRiskAllocator:
    """
    Cross-asset risk allocation system for multi-strategy portfolios.
    """
    
    def __init__(self, risk_budget: Dict[str, float]):
        self.risk_budget = risk_budget
        self.asset_volatilities = {}
        self.asset_correlations = pd.DataFrame()
        
    def allocate_risk_budget(self, 
                           asset_volatilities: Dict[str, float],
                           asset_correlations: pd.DataFrame) -> Dict[str, float]:
        """
        Allocate risk budget across assets using risk parity approach.
        
        Args:
            asset_volatilities: Volatility estimates for each asset
            asset_correlations: Correlation matrix between assets
            
        Returns:
            Risk-allocated weights
        """
        self.asset_volatilities = asset_volatilities
        self.asset_correlations = asset_correlations
        
        assets = list(asset_volatilities.keys())
        n_assets = len(assets)
        
        # Create covariance matrix
        covariance_matrix = np.zeros((n_assets, n_assets))
        for i, asset1 in enumerate(assets):
            for j, asset2 in enumerate(assets):
                if i == j:
                    covariance_matrix[i, j] = asset_volatilities[asset1] ** 2
                else:
                    corr = asset_correlations.loc[asset1, asset2] if asset2 in asset_correlations.columns else 0
                    covariance_matrix[i, j] = corr * asset_volatilities[asset1] * asset_volatilities[asset2]
        
        # Risk parity optimization
        def risk_parity_objective(weights):
            portfolio_risk = np.sqrt(np.dot(weights.T, np.dot(covariance_matrix, weights)))
            risk_contributions = weights * (np.dot(covariance_matrix, weights)) / portfolio_risk
            return np.sum((risk_contributions - portfolio_risk / n_assets) ** 2)
        
        # Constraints
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}  # Weights sum to 1
        ]
        
        # Bounds
        bounds = [(0, 1) for _ in range(n_assets)]
        
        # Initial weights
        initial_weights = np.array([1.0 / n_assets] * n_assets)
        
        # Optimize
        try:
            result = minimize(
                fun=risk_parity_objective,
                x0=initial_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints
            )
            
            if result.success:
                weights = dict(zip(assets, result.x))
                return weights
            else:
                logger.warning("Risk parity optimization failed, using equal weights")
                return {asset: 1.0 / n_assets for asset in assets}
                
        except Exception as e:
            logger.error(f"Risk allocation error: {str(e)}")
            return {asset: 1.0 / n_assets for asset in assets} 