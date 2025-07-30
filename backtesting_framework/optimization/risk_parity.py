#!/usr/bin/env python3
"""
Risk Parity Portfolio Optimization
Phase 3: Advanced Analytics & Optimization - Batch 3
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class RiskParity:
    """Risk Parity portfolio optimization"""
    
    def __init__(self):
        self.risk_parity_portfolios = {}
        self.optimization_history = []
        
        logger.info("Initialized RiskParity")
    
    def calculate_risk_parity_weights(self, covariance_matrix: pd.DataFrame,
                                    target_risk_contribution: float = None) -> Dict:
        """Calculate risk parity weights"""
        
        if len(covariance_matrix) < 2:
            logger.error("Need at least 2 assets for risk parity")
            return {}
        
        try:
            # Calculate asset volatilities
            asset_volatilities = np.sqrt(np.diag(covariance_matrix))
            
            # Initial weights: inverse volatility
            initial_weights = 1 / asset_volatilities
            initial_weights = initial_weights / np.sum(initial_weights)
            
            # Calculate risk contributions
            risk_contributions = self._calculate_risk_contributions(initial_weights, covariance_matrix)
            
            # Optimize weights to equalize risk contributions
            optimized_weights = self._optimize_risk_parity(initial_weights, covariance_matrix)
            
            # Calculate final portfolio metrics
            portfolio_volatility = np.sqrt(np.dot(optimized_weights.T, np.dot(covariance_matrix, optimized_weights)))
            final_risk_contributions = self._calculate_risk_contributions(optimized_weights, covariance_matrix)
            
            # Calculate diversification ratio
            diversification_ratio = self._calculate_diversification_ratio(optimized_weights, covariance_matrix)
            
            results = {
                'weights': dict(zip(covariance_matrix.index, optimized_weights)),
                'portfolio_volatility': portfolio_volatility,
                'risk_contributions': dict(zip(covariance_matrix.index, final_risk_contributions)),
                'diversification_ratio': diversification_ratio,
                'target_risk_contribution': target_risk_contribution or (portfolio_volatility / len(covariance_matrix)),
                'optimization_date': datetime.now().isoformat()
            }
            
            # Store results
            portfolio_id = f"risk_parity_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.risk_parity_portfolios[portfolio_id] = results
            
            # Store optimization history
            self.optimization_history.append({
                'timestamp': datetime.now(),
                'portfolio_id': portfolio_id,
                'n_assets': len(covariance_matrix),
                'portfolio_volatility': portfolio_volatility,
                'diversification_ratio': diversification_ratio
            })
            
            logger.info(f"Risk parity optimization completed: {len(covariance_matrix)} assets")
            return results
            
        except Exception as e:
            logger.error(f"Risk parity optimization failed: {e}")
            return {}
    
    def _calculate_risk_contributions(self, weights: np.ndarray, 
                                   covariance_matrix: pd.DataFrame) -> np.ndarray:
        """Calculate risk contributions for each asset"""
        
        portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(covariance_matrix, weights)))
        
        if portfolio_volatility == 0:
            return np.zeros(len(weights))
        
        # Risk contribution = weight * (covariance * weights) / portfolio_volatility
        risk_contributions = weights * (np.dot(covariance_matrix, weights)) / portfolio_volatility
        
        return risk_contributions
    
    def _optimize_risk_parity(self, initial_weights: np.ndarray,
                            covariance_matrix: pd.DataFrame,
                            max_iterations: int = 100,
                            tolerance: float = 1e-6) -> np.ndarray:
        """Optimize weights to achieve risk parity"""
        
        n_assets = len(initial_weights)
        weights = initial_weights.copy()
        
        for iteration in range(max_iterations):
            # Calculate current risk contributions
            risk_contributions = self._calculate_risk_contributions(weights, covariance_matrix)
            
            # Calculate target risk contribution (equal for all assets)
            target_risk_contribution = np.mean(risk_contributions)
            
            # Check convergence
            risk_contribution_std = np.std(risk_contributions)
            if risk_contribution_std < tolerance:
                break
            
            # Update weights based on risk contribution ratios
            for i in range(n_assets):
                if risk_contributions[i] > 0:
                    adjustment_factor = target_risk_contribution / risk_contributions[i]
                    weights[i] *= adjustment_factor
            
            # Normalize weights
            weights = weights / np.sum(weights)
        
        logger.debug(f"Risk parity optimization converged in {iteration + 1} iterations")
        return weights
    
    def _calculate_diversification_ratio(self, weights: np.ndarray,
                                      covariance_matrix: pd.DataFrame) -> float:
        """Calculate diversification ratio"""
        
        # Weighted average volatility
        asset_volatilities = np.sqrt(np.diag(covariance_matrix))
        weighted_avg_vol = np.sum(weights * asset_volatilities)
        
        # Portfolio volatility
        portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(covariance_matrix, weights)))
        
        # Diversification ratio = weighted_avg_vol / portfolio_volatility
        if portfolio_volatility > 0:
            diversification_ratio = weighted_avg_vol / portfolio_volatility
        else:
            diversification_ratio = 1.0
        
        return diversification_ratio
    
    def calculate_risk_budget_weights(self, covariance_matrix: pd.DataFrame,
                                   risk_budgets: Dict[str, float]) -> Dict:
        """Calculate weights based on risk budget allocation"""
        
        if len(risk_budgets) != len(covariance_matrix):
            logger.error("Risk budgets must match number of assets")
            return {}
        
        # Normalize risk budgets
        total_budget = sum(risk_budgets.values())
        normalized_budgets = {k: v / total_budget for k, v in risk_budgets.items()}
        
        # Initial weights based on risk budgets
        initial_weights = np.array([normalized_budgets[asset] for asset in covariance_matrix.index])
        
        # Optimize weights to match risk budgets
        optimized_weights = self._optimize_risk_budget(initial_weights, covariance_matrix, normalized_budgets)
        
        # Calculate portfolio metrics
        portfolio_volatility = np.sqrt(np.dot(optimized_weights.T, np.dot(covariance_matrix, optimized_weights)))
        risk_contributions = self._calculate_risk_contributions(optimized_weights, covariance_matrix)
        
        results = {
            'weights': dict(zip(covariance_matrix.index, optimized_weights)),
            'portfolio_volatility': portfolio_volatility,
            'risk_contributions': dict(zip(covariance_matrix.index, risk_contributions)),
            'target_risk_budgets': normalized_budgets,
            'optimization_date': datetime.now().isoformat()
        }
        
        logger.info(f"Risk budget optimization completed: {len(covariance_matrix)} assets")
        return results
    
    def _optimize_risk_budget(self, initial_weights: np.ndarray,
                            covariance_matrix: pd.DataFrame,
                            target_risk_budgets: Dict[str, float],
                            max_iterations: int = 100,
                            tolerance: float = 1e-6) -> np.ndarray:
        """Optimize weights to match target risk budgets"""
        
        n_assets = len(initial_weights)
        weights = initial_weights.copy()
        
        for iteration in range(max_iterations):
            # Calculate current risk contributions
            risk_contributions = self._calculate_risk_contributions(weights, covariance_matrix)
            
            # Calculate total portfolio risk
            total_risk = np.sum(risk_contributions)
            
            # Check convergence
            max_deviation = 0
            for i, asset in enumerate(covariance_matrix.index):
                target_contribution = target_risk_budgets[asset] * total_risk
                current_contribution = risk_contributions[i]
                deviation = abs(current_contribution - target_contribution) / total_risk
                max_deviation = max(max_deviation, deviation)
            
            if max_deviation < tolerance:
                break
            
            # Update weights based on risk budget ratios
            for i, asset in enumerate(covariance_matrix.index):
                if risk_contributions[i] > 0:
                    target_contribution = target_risk_budgets[asset] * total_risk
                    adjustment_factor = target_contribution / risk_contributions[i]
                    weights[i] *= adjustment_factor
            
            # Normalize weights
            weights = weights / np.sum(weights)
        
        logger.debug(f"Risk budget optimization converged in {iteration + 1} iterations")
        return weights
    
    def get_risk_parity_summary(self) -> Dict:
        """Get risk parity optimization summary"""
        return {
            'total_portfolios': len(self.risk_parity_portfolios),
            'optimization_history_count': len(self.optimization_history),
            'average_diversification_ratio': np.mean([h['diversification_ratio'] for h in self.optimization_history]) if self.optimization_history else 0
        }
