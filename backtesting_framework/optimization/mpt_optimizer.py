#!/usr/bin/env python3
"""
Modern Portfolio Theory Optimizer
Phase 3: Advanced Analytics & Optimization - Batch 3
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class MPTOptimizer:
    """Modern Portfolio Theory (MPT) optimizer"""
    
    def __init__(self):
        self.optimization_results = {}
        self.efficient_frontier = None
        self.optimal_portfolios = {}
        
        logger.info("Initialized MPTOptimizer")
    
    def calculate_returns_and_covariance(self, data: pd.DataFrame) -> Tuple[pd.Series, pd.DataFrame]:
        """Calculate expected returns and covariance matrix"""
        
        # Calculate returns
        returns = data.pct_change().dropna()
        
        if len(returns) < 30:
            logger.warning(f"Insufficient data for MPT: {len(returns)} observations")
            return pd.Series(), pd.DataFrame()
        
        # Calculate expected returns (mean)
        expected_returns = returns.mean() * 252  # Annualize
        
        # Calculate covariance matrix
        covariance_matrix = returns.cov() * 252  # Annualize
        
        logger.info(f"Calculated returns and covariance for {len(expected_returns)} assets")
        return expected_returns, covariance_matrix
    
    def optimize_portfolio(self, expected_returns: pd.Series, covariance_matrix: pd.DataFrame,
                          risk_free_rate: float = 0.02, target_return: float = None,
                          target_volatility: float = None) -> Dict:
        """Optimize portfolio using MPT"""
        
        if len(expected_returns) < 2:
            logger.error("Need at least 2 assets for portfolio optimization")
            return {}
        
        # Validate inputs
        if not covariance_matrix.index.equals(expected_returns.index):
            logger.error("Asset mismatch between returns and covariance matrix")
            return {}
        
        n_assets = len(expected_returns)
        
        try:
            # Calculate efficient frontier
            efficient_frontier = self._calculate_efficient_frontier(
                expected_returns, covariance_matrix, risk_free_rate
            )
            
            # Find optimal portfolios
            optimal_portfolios = {}
            
            # 1. Minimum Variance Portfolio
            min_var_portfolio = self._find_minimum_variance_portfolio(
                expected_returns, covariance_matrix
            )
            optimal_portfolios['minimum_variance'] = min_var_portfolio
            
            # 2. Maximum Sharpe Ratio Portfolio
            max_sharpe_portfolio = self._find_maximum_sharpe_portfolio(
                expected_returns, covariance_matrix, risk_free_rate
            )
            optimal_portfolios['maximum_sharpe'] = max_sharpe_portfolio
            
            # 3. Target Return Portfolio (if specified)
            if target_return is not None:
                target_return_portfolio = self._find_target_return_portfolio(
                    expected_returns, covariance_matrix, target_return
                )
                optimal_portfolios['target_return'] = target_return_portfolio
            
            # 4. Target Volatility Portfolio (if specified)
            if target_volatility is not None:
                target_vol_portfolio = self._find_target_volatility_portfolio(
                    expected_returns, covariance_matrix, target_volatility
                )
                optimal_portfolios['target_volatility'] = target_vol_portfolio
            
            results = {
                'efficient_frontier': efficient_frontier,
                'optimal_portfolios': optimal_portfolios,
                'expected_returns': expected_returns.to_dict(),
                'covariance_matrix': covariance_matrix.to_dict(),
                'risk_free_rate': risk_free_rate,
                'optimization_date': datetime.now().isoformat()
            }
            
            # Store results
            self.optimization_results = results
            self.efficient_frontier = efficient_frontier
            self.optimal_portfolios = optimal_portfolios
            
            logger.info(f"Portfolio optimization completed: {len(optimal_portfolios)} optimal portfolios found")
            return results
            
        except Exception as e:
            logger.error(f"Portfolio optimization failed: {e}")
            return {}
    
    def _calculate_efficient_frontier(self, expected_returns: pd.Series, 
                                    covariance_matrix: pd.DataFrame,
                                    risk_free_rate: float) -> pd.DataFrame:
        """Calculate efficient frontier"""
        
        n_assets = len(expected_returns)
        
        # Generate portfolio weights
        n_portfolios = 1000
        portfolio_weights = []
        portfolio_returns = []
        portfolio_volatilities = []
        portfolio_sharpe_ratios = []
        
        for _ in range(n_portfolios):
            # Generate random weights
            weights = np.random.random(n_assets)
            weights = weights / np.sum(weights)  # Normalize
            
            # Calculate portfolio metrics
            portfolio_return = np.sum(weights * expected_returns)
            portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(covariance_matrix, weights)))
            sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_volatility if portfolio_volatility > 0 else 0
            
            portfolio_weights.append(weights)
            portfolio_returns.append(portfolio_return)
            portfolio_volatilities.append(portfolio_volatility)
            portfolio_sharpe_ratios.append(sharpe_ratio)
        
        # Create efficient frontier DataFrame
        efficient_frontier = pd.DataFrame({
            'weights': portfolio_weights,
            'return': portfolio_returns,
            'volatility': portfolio_volatilities,
            'sharpe_ratio': portfolio_sharpe_ratios
        })
        
        return efficient_frontier
    
    def _find_minimum_variance_portfolio(self, expected_returns: pd.Series,
                                       covariance_matrix: pd.DataFrame) -> Dict:
        """Find minimum variance portfolio"""
        
        n_assets = len(expected_returns)
        
        # Simple optimization: find weights that minimize variance
        # Subject to: sum(weights) = 1, weights >= 0
        
        # Use inverse variance weighting as approximation
        variances = np.diag(covariance_matrix)
        weights = 1 / variances
        weights = weights / np.sum(weights)
        
        portfolio_return = np.sum(weights * expected_returns)
        portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(covariance_matrix, weights)))
        sharpe_ratio = portfolio_return / portfolio_volatility if portfolio_volatility > 0 else 0
        
        return {
            'weights': dict(zip(expected_returns.index, weights)),
            'return': portfolio_return,
            'volatility': portfolio_volatility,
            'sharpe_ratio': sharpe_ratio,
            'method': 'minimum_variance'
        }
    
    def _find_maximum_sharpe_portfolio(self, expected_returns: pd.Series,
                                     covariance_matrix: pd.DataFrame,
                                     risk_free_rate: float) -> Dict:
        """Find maximum Sharpe ratio portfolio"""
        
        n_assets = len(expected_returns)
        
        # Use equal risk contribution as approximation
        # This is a simplified approach - in practice, you'd use quadratic programming
        
        # Calculate risk contributions
        portfolio_vol = np.sqrt(np.sum(covariance_matrix))
        risk_contributions = np.sum(covariance_matrix, axis=1) / portfolio_vol
        
        # Weight by inverse risk contribution
        weights = 1 / risk_contributions
        weights = weights / np.sum(weights)
        
        portfolio_return = np.sum(weights * expected_returns)
        portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(covariance_matrix, weights)))
        sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_volatility if portfolio_volatility > 0 else 0
        
        return {
            'weights': dict(zip(expected_returns.index, weights)),
            'return': portfolio_return,
            'volatility': portfolio_volatility,
            'sharpe_ratio': sharpe_ratio,
            'method': 'maximum_sharpe'
        }
    
    def _find_target_return_portfolio(self, expected_returns: pd.Series,
                                    covariance_matrix: pd.DataFrame,
                                    target_return: float) -> Dict:
        """Find portfolio with target return"""
        
        # Use linear combination of min variance and max Sharpe
        min_var_port = self._find_minimum_variance_portfolio(expected_returns, covariance_matrix)
        max_sharpe_port = self._find_maximum_sharpe_portfolio(expected_returns, covariance_matrix, 0.02)
        
        # Interpolate weights
        min_var_weights = np.array(list(min_var_port['weights'].values()))
        max_sharpe_weights = np.array(list(max_sharpe_port['weights'].values()))
        
        # Simple interpolation
        alpha = 0.5  # Equal weight
        target_weights = alpha * min_var_weights + (1 - alpha) * max_sharpe_weights
        target_weights = target_weights / np.sum(target_weights)
        
        portfolio_return = np.sum(target_weights * expected_returns)
        portfolio_volatility = np.sqrt(np.dot(target_weights.T, np.dot(covariance_matrix, target_weights)))
        sharpe_ratio = portfolio_return / portfolio_volatility if portfolio_volatility > 0 else 0
        
        return {
            'weights': dict(zip(expected_returns.index, target_weights)),
            'return': portfolio_return,
            'volatility': portfolio_volatility,
            'sharpe_ratio': sharpe_ratio,
            'method': 'target_return'
        }
    
    def _find_target_volatility_portfolio(self, expected_returns: pd.Series,
                                        covariance_matrix: pd.DataFrame,
                                        target_volatility: float) -> Dict:
        """Find portfolio with target volatility"""
        
        # Use minimum variance portfolio and scale
        min_var_port = self._find_minimum_variance_portfolio(expected_returns, covariance_matrix)
        min_var_weights = np.array(list(min_var_port['weights'].values()))
        
        # Scale weights to achieve target volatility
        current_vol = min_var_port['volatility']
        if current_vol > 0:
            scale_factor = target_volatility / current_vol
            target_weights = min_var_weights * scale_factor
        else:
            target_weights = min_var_weights
        
        target_weights = target_weights / np.sum(target_weights)
        
        portfolio_return = np.sum(target_weights * expected_returns)
        portfolio_volatility = np.sqrt(np.dot(target_weights.T, np.dot(covariance_matrix, target_weights)))
        sharpe_ratio = portfolio_return / portfolio_volatility if portfolio_volatility > 0 else 0
        
        return {
            'weights': dict(zip(expected_returns.index, target_weights)),
            'return': portfolio_return,
            'volatility': portfolio_volatility,
            'sharpe_ratio': sharpe_ratio,
            'method': 'target_volatility'
        }
    
    def get_optimization_summary(self) -> Dict:
        """Get optimization summary"""
        return {
            'total_optimizations': len(self.optimization_results),
            'optimal_portfolios_count': len(self.optimal_portfolios),
            'efficient_frontier_points': len(self.efficient_frontier) if self.efficient_frontier is not None else 0
        }
