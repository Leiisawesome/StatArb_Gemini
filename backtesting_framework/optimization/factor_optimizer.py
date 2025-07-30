#!/usr/bin/env python3
"""
Factor-Based Portfolio Optimization
Phase 3: Advanced Analytics & Optimization - Batch 3
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class FactorOptimizer:
    """Factor-based portfolio optimization"""
    
    def __init__(self):
        self.factor_portfolios = {}
        self.factor_exposures = {}
        self.optimization_history = []
        
        logger.info("Initialized FactorOptimizer")
    
    def optimize_factor_portfolio(self, factor_loadings: pd.DataFrame,
                                factor_returns: pd.DataFrame,
                                target_factor_exposures: Dict[str, float] = None,
                                risk_budget: Dict[str, float] = None) -> Dict:
        """Optimize portfolio based on factor exposures"""
        
        if len(factor_loadings) < 2:
            logger.error("Need at least 2 assets for factor optimization")
            return {}
        
        try:
            n_assets = len(factor_loadings)
            n_factors = len(factor_loadings.columns)
            
            # Calculate factor covariance matrix
            factor_covariance = factor_returns.cov() * 252  # Annualize
            
            # Calculate asset covariance matrix from factors
            asset_covariance = factor_loadings @ factor_covariance @ factor_loadings.T
            
            # Initial weights based on factor exposures
            if target_factor_exposures:
                weights = self._calculate_weights_from_target_exposures(
                    factor_loadings, target_factor_exposures
                )
            else:
                # Equal weight starting point
                weights = np.ones(n_assets) / n_assets
            
            # Optimize weights
            optimized_weights = self._optimize_factor_weights(
                weights, factor_loadings, factor_covariance, risk_budget
            )
            
            # Calculate portfolio metrics
            portfolio_factor_exposures = self._calculate_portfolio_factor_exposures(
                optimized_weights, factor_loadings
            )
            
            portfolio_volatility = np.sqrt(
                np.dot(optimized_weights.T, np.dot(asset_covariance, optimized_weights))
            )
            
            # Calculate factor contribution to risk
            factor_risk_contribution = self._calculate_factor_risk_contribution(
                optimized_weights, factor_loadings, factor_covariance
            )
            
            results = {
                'weights': dict(zip(factor_loadings.index, optimized_weights)),
                'portfolio_factor_exposures': portfolio_factor_exposures,
                'factor_risk_contribution': factor_risk_contribution,
                'portfolio_volatility': portfolio_volatility,
                'target_factor_exposures': target_factor_exposures,
                'risk_budget': risk_budget,
                'optimization_date': datetime.now().isoformat()
            }
            
            # Store results
            portfolio_id = f"factor_portfolio_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.factor_portfolios[portfolio_id] = results
            self.factor_exposures[portfolio_id] = portfolio_factor_exposures
            
            # Store optimization history
            self.optimization_history.append({
                'timestamp': datetime.now(),
                'portfolio_id': portfolio_id,
                'n_assets': n_assets,
                'n_factors': n_factors,
                'portfolio_volatility': portfolio_volatility
            })
            
            logger.info(f"Factor optimization completed: {n_assets} assets, {n_factors} factors")
            return results
            
        except Exception as e:
            logger.error(f"Factor optimization failed: {e}")
            return {}
    
    def _calculate_weights_from_target_exposures(self, factor_loadings: pd.DataFrame,
                                               target_exposures: Dict[str, float]) -> np.ndarray:
        """Calculate weights to achieve target factor exposures"""
        
        n_assets = len(factor_loadings)
        n_factors = len(factor_loadings.columns)
        
        # Create target exposure vector
        target_vector = np.array([target_exposures.get(factor, 0) for factor in factor_loadings.columns])
        
        # Solve for weights using least squares
        # factor_loadings * weights = target_exposures
        try:
            weights = np.linalg.lstsq(factor_loadings, target_vector, rcond=None)[0]
            weights = np.maximum(weights, 0)  # Ensure non-negative weights
            weights = weights / np.sum(weights)  # Normalize
        except:
            # Fallback to equal weights
            weights = np.ones(n_assets) / n_assets
        
        return weights
    
    def _optimize_factor_weights(self, initial_weights: np.ndarray,
                               factor_loadings: pd.DataFrame,
                               factor_covariance: pd.DataFrame,
                               risk_budget: Dict[str, float] = None) -> np.ndarray:
        """Optimize weights considering factor risk budget"""
        
        weights = initial_weights.copy()
        
        if risk_budget is None:
            # Equal risk budget
            n_factors = len(factor_loadings.columns)
            risk_budget = {factor: 1.0/n_factors for factor in factor_loadings.columns}
        
        # Simple iterative optimization
        max_iterations = 50
        tolerance = 1e-6
        
        for iteration in range(max_iterations):
            # Calculate current factor risk contributions
            factor_risk_contrib = self._calculate_factor_risk_contribution(
                weights, factor_loadings, factor_covariance
            )
            
            # Check convergence
            max_deviation = 0
            for factor, current_risk in factor_risk_contrib.items():
                target_risk = risk_budget.get(factor, 0)
                deviation = abs(current_risk - target_risk)
                max_deviation = max(max_deviation, deviation)
            
            if max_deviation < tolerance:
                break
            
            # Update weights based on risk budget ratios
            for i in range(len(weights)):
                adjustment = 1.0
                for factor in factor_loadings.columns:
                    current_risk = factor_risk_contrib.get(factor, 0)
                    target_risk = risk_budget.get(factor, 0)
                    
                    if current_risk > 0 and target_risk > 0:
                        factor_loading = factor_loadings.iloc[i][factor]
                        if factor_loading != 0:
                            adjustment *= (target_risk / current_risk) ** (factor_loading / abs(factor_loading))
                
                weights[i] *= adjustment
            
            # Normalize weights
            weights = np.maximum(weights, 0)
            weights = weights / np.sum(weights)
        
        return weights
    
    def _calculate_portfolio_factor_exposures(self, weights: np.ndarray,
                                           factor_loadings: pd.DataFrame) -> Dict[str, float]:
        """Calculate portfolio factor exposures"""
        
        portfolio_exposures = {}
        for factor in factor_loadings.columns:
            exposure = np.sum(weights * factor_loadings[factor])
            portfolio_exposures[factor] = exposure
        
        return portfolio_exposures
    
    def _calculate_factor_risk_contribution(self, weights: np.ndarray,
                                         factor_loadings: pd.DataFrame,
                                         factor_covariance: pd.DataFrame) -> Dict[str, float]:
        """Calculate factor contribution to portfolio risk"""
        
        # Calculate portfolio factor exposures
        portfolio_exposures = self._calculate_portfolio_factor_exposures(weights, factor_loadings)
        
        # Calculate portfolio volatility
        portfolio_volatility = np.sqrt(
            np.dot(np.array(list(portfolio_exposures.values())).T,
                  np.dot(factor_covariance, np.array(list(portfolio_exposures.values()))))
        )
        
        if portfolio_volatility == 0:
            return {factor: 0 for factor in factor_loadings.columns}
        
        # Calculate factor risk contributions
        factor_risk_contrib = {}
        for factor in factor_loadings.columns:
            # Marginal contribution of factor to portfolio risk
            marginal_contribution = np.dot(factor_covariance.loc[factor], 
                                         np.array(list(portfolio_exposures.values()))) / portfolio_volatility
            
            # Factor risk contribution = exposure * marginal contribution
            factor_risk_contrib[factor] = portfolio_exposures[factor] * marginal_contribution
        
        return factor_risk_contrib
    
    def optimize_factor_tilt(self, base_weights: pd.Series,
                           factor_loadings: pd.DataFrame,
                           factor_views: Dict[str, float],
                           tilt_strength: float = 0.1) -> Dict:
        """Optimize factor tilt while maintaining base weights"""
        
        try:
            n_assets = len(base_weights)
            
            # Calculate factor exposures of base portfolio
            base_exposures = self._calculate_portfolio_factor_exposures(
                base_weights.values, factor_loadings
            )
            
            # Calculate target exposures based on views
            target_exposures = {}
            for factor in factor_loadings.columns:
                base_exposure = base_exposures.get(factor, 0)
                factor_view = factor_views.get(factor, 0)
                target_exposures[factor] = base_exposure + tilt_strength * factor_view
            
            # Calculate tilt weights
            tilt_weights = self._calculate_weights_from_target_exposures(
                factor_loadings, target_exposures
            )
            
            # Blend with base weights
            final_weights = 0.8 * base_weights.values + 0.2 * tilt_weights
            final_weights = np.maximum(final_weights, 0)
            final_weights = final_weights / np.sum(final_weights)
            
            # Calculate portfolio metrics
            portfolio_exposures = self._calculate_portfolio_factor_exposures(
                final_weights, factor_loadings
            )
            
            results = {
                'base_weights': base_weights.to_dict(),
                'tilt_weights': dict(zip(factor_loadings.index, tilt_weights)),
                'final_weights': dict(zip(factor_loadings.index, final_weights)),
                'portfolio_factor_exposures': portfolio_exposures,
                'factor_views': factor_views,
                'tilt_strength': tilt_strength,
                'optimization_date': datetime.now().isoformat()
            }
            
            logger.info(f"Factor tilt optimization completed: {len(factor_views)} factor views")
            return results
            
        except Exception as e:
            logger.error(f"Factor tilt optimization failed: {e}")
            return {}
    
    def get_factor_optimization_summary(self) -> Dict:
        """Get factor optimization summary"""
        return {
            'total_portfolios': len(self.factor_portfolios),
            'optimization_history_count': len(self.optimization_history),
            'average_volatility': np.mean([h['portfolio_volatility'] for h in self.optimization_history]) if self.optimization_history else 0
        }
