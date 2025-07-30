#!/usr/bin/env python3
"""
Black-Litterman Model
Phase 3: Advanced Analytics & Optimization - Batch 3
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class BlackLitterman:
    """Black-Litterman portfolio optimization model"""
    
    def __init__(self):
        self.bl_portfolios = {}
        self.view_history = []
        
        logger.info("Initialized BlackLitterman")
    
    def calculate_equilibrium_returns(self, covariance_matrix: pd.DataFrame,
                                   market_cap_weights: pd.Series,
                                   risk_aversion: float = 2.5) -> pd.Series:
        """Calculate equilibrium returns using reverse optimization"""
        
        if len(covariance_matrix) != len(market_cap_weights):
            logger.error("Market cap weights must match covariance matrix dimensions")
            return pd.Series()
        
        try:
            # Equilibrium returns = risk_aversion * covariance_matrix * market_cap_weights
            equilibrium_returns = risk_aversion * np.dot(covariance_matrix, market_cap_weights)
            
            # Convert to Series
            equilibrium_returns = pd.Series(equilibrium_returns, index=covariance_matrix.index)
            
            logger.info(f"Calculated equilibrium returns for {len(equilibrium_returns)} assets")
            return equilibrium_returns
            
        except Exception as e:
            logger.error(f"Error calculating equilibrium returns: {e}")
            return pd.Series()
    
    def incorporate_views(self, equilibrium_returns: pd.Series,
                         covariance_matrix: pd.DataFrame,
                         views: Dict[str, float],
                         view_confidences: Dict[str, float] = None,
                         tau: float = 0.05) -> Dict:
        """Incorporate investor views into the model"""
        
        if not views:
            logger.warning("No views provided, returning equilibrium returns")
            return {
                'posterior_returns': equilibrium_returns,
                'posterior_covariance': covariance_matrix,
                'views_incorporated': 0
            }
        
        try:
            n_assets = len(equilibrium_returns)
            n_views = len(views)
            
            # Create view matrix P and view vector Q
            P = np.zeros((n_views, n_assets))
            Q = np.zeros(n_views)
            
            # Set default confidence if not provided
            if view_confidences is None:
                view_confidences = {view: 0.5 for view in views.keys()}
            
            # Build view matrices
            for i, (view_asset, view_return) in enumerate(views.items()):
                if view_asset in equilibrium_returns.index:
                    asset_idx = equilibrium_returns.index.get_loc(view_asset)
                    P[i, asset_idx] = 1.0
                    Q[i] = view_return
            
            # Create view confidence matrix Omega
            Omega = np.diag([1/view_confidences.get(view, 0.5) for view in views.keys()])
            
            # Calculate posterior returns and covariance
            posterior_returns, posterior_covariance = self._calculate_posterior(
                equilibrium_returns, covariance_matrix, P, Q, Omega, tau
            )
            
            results = {
                'posterior_returns': posterior_returns,
                'posterior_covariance': posterior_covariance,
                'equilibrium_returns': equilibrium_returns,
                'views': views,
                'view_confidences': view_confidences,
                'tau': tau,
                'views_incorporated': n_views,
                'optimization_date': datetime.now().isoformat()
            }
            
            # Store view history
            self.view_history.append({
                'timestamp': datetime.now(),
                'views': views,
                'view_confidences': view_confidences,
                'n_views': n_views
            })
            
            logger.info(f"Black-Litterman views incorporated: {n_views} views")
            return results
            
        except Exception as e:
            logger.error(f"Error incorporating views: {e}")
            return {}
    
    def _calculate_posterior(self, equilibrium_returns: pd.Series,
                           covariance_matrix: pd.DataFrame,
                           P: np.ndarray, Q: np.ndarray,
                           Omega: np.ndarray, tau: float) -> Tuple[pd.Series, pd.DataFrame]:
        """Calculate posterior returns and covariance"""
        
        # Scale covariance matrix
        scaled_covariance = tau * covariance_matrix
        
        # Calculate posterior covariance
        M1 = np.linalg.inv(scaled_covariance)
        M2 = P.T @ np.linalg.inv(Omega) @ P
        posterior_covariance = np.linalg.inv(M1 + M2)
        
        # Calculate posterior returns
        M3 = np.linalg.inv(scaled_covariance) @ equilibrium_returns
        M4 = P.T @ np.linalg.inv(Omega) @ Q
        posterior_returns_array = posterior_covariance @ (M3 + M4)
        
        # Convert to Series and DataFrame
        posterior_returns = pd.Series(posterior_returns_array, index=equilibrium_returns.index)
        posterior_covariance = pd.DataFrame(posterior_covariance, 
                                          index=covariance_matrix.index,
                                          columns=covariance_matrix.columns)
        
        return posterior_returns, posterior_covariance
    
    def optimize_portfolio(self, posterior_returns: pd.Series,
                         posterior_covariance: pd.DataFrame,
                         target_return: float = None,
                         target_volatility: float = None) -> Dict:
        """Optimize portfolio using Black-Litterman posterior estimates"""
        
        try:
            # Use simple optimization approach
            n_assets = len(posterior_returns)
            
            # Calculate asset volatilities
            asset_volatilities = np.sqrt(np.diag(posterior_covariance))
            
            # Initial weights based on Sharpe ratios
            sharpe_ratios = posterior_returns / asset_volatilities
            sharpe_ratios = sharpe_ratios.replace([np.inf, -np.inf], 0)
            
            # Weight by Sharpe ratios
            weights = sharpe_ratios / np.sum(sharpe_ratios)
            weights = np.maximum(weights, 0)  # Ensure non-negative weights
            weights = weights / np.sum(weights)  # Normalize
            
            # Calculate portfolio metrics
            portfolio_return = np.sum(weights * posterior_returns)
            portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(posterior_covariance, weights)))
            sharpe_ratio = portfolio_return / portfolio_volatility if portfolio_volatility > 0 else 0
            
            # Adjust for target return if specified
            if target_return is not None:
                weights = self._adjust_for_target_return(weights, posterior_returns, posterior_covariance, target_return)
                portfolio_return = np.sum(weights * posterior_returns)
                portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(posterior_covariance, weights)))
                sharpe_ratio = portfolio_return / portfolio_volatility if portfolio_volatility > 0 else 0
            
            # Adjust for target volatility if specified
            if target_volatility is not None:
                weights = self._adjust_for_target_volatility(weights, posterior_returns, posterior_covariance, target_volatility)
                portfolio_return = np.sum(weights * posterior_returns)
                portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(posterior_covariance, weights)))
                sharpe_ratio = portfolio_return / portfolio_volatility if portfolio_volatility > 0 else 0
            
            results = {
                'weights': dict(zip(posterior_returns.index, weights)),
                'portfolio_return': portfolio_return,
                'portfolio_volatility': portfolio_volatility,
                'sharpe_ratio': sharpe_ratio,
                'target_return': target_return,
                'target_volatility': target_volatility,
                'optimization_date': datetime.now().isoformat()
            }
            
            # Store portfolio
            portfolio_id = f"bl_portfolio_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.bl_portfolios[portfolio_id] = results
            
            logger.info(f"Black-Litterman portfolio optimization completed")
            return results
            
        except Exception as e:
            logger.error(f"Black-Litterman optimization failed: {e}")
            return {}
    
    def _adjust_for_target_return(self, weights: np.ndarray,
                                returns: pd.Series,
                                covariance: pd.DataFrame,
                                target_return: float) -> np.ndarray:
        """Adjust weights to achieve target return"""
        
        current_return = np.sum(weights * returns)
        
        if abs(current_return - target_return) < 1e-6:
            return weights
        
        # Simple scaling approach
        if current_return > 0:
            scale_factor = target_return / current_return
            adjusted_weights = weights * scale_factor
            adjusted_weights = np.maximum(adjusted_weights, 0)
            adjusted_weights = adjusted_weights / np.sum(adjusted_weights)
            return adjusted_weights
        
        return weights
    
    def _adjust_for_target_volatility(self, weights: np.ndarray,
                                    returns: pd.Series,
                                    covariance: pd.DataFrame,
                                    target_volatility: float) -> np.ndarray:
        """Adjust weights to achieve target volatility"""
        
        current_volatility = np.sqrt(np.dot(weights.T, np.dot(covariance, weights)))
        
        if abs(current_volatility - target_volatility) < 1e-6:
            return weights
        
        # Simple scaling approach
        if current_volatility > 0:
            scale_factor = target_volatility / current_volatility
            adjusted_weights = weights * scale_factor
            adjusted_weights = np.maximum(adjusted_weights, 0)
            adjusted_weights = adjusted_weights / np.sum(adjusted_weights)
            return adjusted_weights
        
        return weights
    
    def get_black_litterman_summary(self) -> Dict:
        """Get Black-Litterman model summary"""
        return {
            'total_portfolios': len(self.bl_portfolios),
            'view_history_count': len(self.view_history),
            'average_views_per_optimization': np.mean([h['n_views'] for h in self.view_history]) if self.view_history else 0
        }
