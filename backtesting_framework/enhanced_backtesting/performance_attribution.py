#!/usr/bin/env python3
"""
Performance Attribution Analysis
Phase 3: Advanced Analytics & Optimization - Batch 4
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class PerformanceAttribution:
    """Performance attribution analysis"""
    
    def __init__(self):
        self.attribution_results = {}
        self.attribution_history = []
        
        logger.info("Initialized PerformanceAttribution")
    
    def calculate_brinson_attribution(self, portfolio_weights: pd.Series,
                                    benchmark_weights: pd.Series,
                                    asset_returns: pd.Series,
                                    benchmark_returns: pd.Series) -> Dict:
        """Calculate Brinson attribution analysis"""
        
        if len(portfolio_weights) != len(benchmark_weights):
            logger.error("Portfolio and benchmark weights must have same length")
            return {}
        
        try:
            # Calculate portfolio and benchmark returns
            portfolio_return = (portfolio_weights * asset_returns).sum()
            benchmark_return = (benchmark_weights * benchmark_returns).sum()
            
            # Calculate excess return
            excess_return = portfolio_return - benchmark_return
            
            # Calculate attribution components
            allocation_effect = self._calculate_allocation_effect(
                portfolio_weights, benchmark_weights, benchmark_returns
            )
            
            selection_effect = self._calculate_selection_effect(
                portfolio_weights, benchmark_weights, asset_returns, benchmark_returns
            )
            
            interaction_effect = self._calculate_interaction_effect(
                portfolio_weights, benchmark_weights, asset_returns, benchmark_returns
            )
            
            # Verify attribution
            total_attribution = allocation_effect + selection_effect + interaction_effect
            attribution_error = excess_return - total_attribution
            
            results = {
                'portfolio_return': portfolio_return,
                'benchmark_return': benchmark_return,
                'excess_return': excess_return,
                'attribution_components': {
                    'allocation_effect': allocation_effect,
                    'selection_effect': selection_effect,
                    'interaction_effect': interaction_effect,
                    'total_attribution': total_attribution,
                    'attribution_error': attribution_error
                },
                'attribution_percentages': {
                    'allocation_pct': allocation_effect / excess_return * 100 if excess_return != 0 else 0,
                    'selection_pct': selection_effect / excess_return * 100 if excess_return != 0 else 0,
                    'interaction_pct': interaction_effect / excess_return * 100 if excess_return != 0 else 0
                },
                'analysis_date': datetime.now().isoformat()
            }
            
            # Store results
            attribution_id = f"brinson_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.attribution_results[attribution_id] = results
            
            logger.info(f"Brinson attribution completed: {excess_return:.4f} excess return")
            return results
            
        except Exception as e:
            logger.error(f"Brinson attribution failed: {e}")
            return {}
    
    def _calculate_allocation_effect(self, portfolio_weights: pd.Series,
                                   benchmark_weights: pd.Series,
                                   benchmark_returns: pd.Series) -> float:
        """Calculate allocation effect"""
        
        allocation_effect = ((portfolio_weights - benchmark_weights) * benchmark_returns).sum()
        return allocation_effect
    
    def _calculate_selection_effect(self, portfolio_weights: pd.Series,
                                  benchmark_weights: pd.Series,
                                  asset_returns: pd.Series,
                                  benchmark_returns: pd.Series) -> float:
        """Calculate selection effect"""
        
        selection_effect = (benchmark_weights * (asset_returns - benchmark_returns)).sum()
        return selection_effect
    
    def _calculate_interaction_effect(self, portfolio_weights: pd.Series,
                                    benchmark_weights: pd.Series,
                                    asset_returns: pd.Series,
                                    benchmark_returns: pd.Series) -> float:
        """Calculate interaction effect"""
        
        interaction_effect = ((portfolio_weights - benchmark_weights) * 
                             (asset_returns - benchmark_returns)).sum()
        return interaction_effect
    
    def calculate_factor_attribution(self, portfolio_weights: pd.Series,
                                   factor_loadings: pd.DataFrame,
                                   factor_returns: pd.Series,
                                   benchmark_weights: pd.Series = None) -> Dict:
        """Calculate factor attribution analysis"""
        
        if factor_loadings.empty or factor_returns.empty:
            logger.error("Factor data required for factor attribution")
            return {}
        
        try:
            # Calculate portfolio factor exposures
            portfolio_exposures = (factor_loadings.T * portfolio_weights).sum(axis=1)
            
            # Calculate benchmark factor exposures if provided
            if benchmark_weights is not None:
                benchmark_exposures = (factor_loadings.T * benchmark_weights).sum(axis=1)
                excess_exposures = portfolio_exposures - benchmark_exposures
            else:
                benchmark_exposures = pd.Series(0, index=portfolio_exposures.index)
                excess_exposures = portfolio_exposures
            
            # Calculate factor contributions
            factor_contributions = {}
            total_factor_contribution = 0
            
            for factor in factor_returns.index:
                if factor in excess_exposures.index:
                    factor_contribution = excess_exposures[factor] * factor_returns[factor]
                    factor_contributions[factor] = {
                        'exposure': excess_exposures[factor],
                        'factor_return': factor_returns[factor],
                        'contribution': factor_contribution
                    }
                    total_factor_contribution += factor_contribution
            
            # Calculate total portfolio return
            portfolio_return = (portfolio_exposures * factor_returns).sum()
            
            # Calculate residual return
            if benchmark_weights is not None:
                benchmark_return = (benchmark_exposures * factor_returns).sum()
                residual_return = portfolio_return - benchmark_return - total_factor_contribution
            else:
                residual_return = portfolio_return - total_factor_contribution
            
            results = {
                'portfolio_return': portfolio_return,
                'factor_contributions': factor_contributions,
                'total_factor_contribution': total_factor_contribution,
                'residual_return': residual_return,
                'portfolio_exposures': portfolio_exposures.to_dict(),
                'benchmark_exposures': benchmark_exposures.to_dict() if benchmark_weights is not None else None,
                'excess_exposures': excess_exposures.to_dict(),
                'analysis_date': datetime.now().isoformat()
            }
            
            # Store results
            attribution_id = f"factor_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.attribution_results[attribution_id] = results
            
            logger.info(f"Factor attribution completed: {len(factor_contributions)} factors")
            return results
            
        except Exception as e:
            logger.error(f"Factor attribution failed: {e}")
            return {}
    
    def calculate_risk_attribution(self, portfolio_weights: pd.Series,
                                 covariance_matrix: pd.DataFrame,
                                 factor_loadings: pd.DataFrame = None) -> Dict:
        """Calculate risk attribution analysis"""
        
        if covariance_matrix.empty:
            logger.error("Covariance matrix required for risk attribution")
            return {}
        
        try:
            # Calculate portfolio volatility
            portfolio_volatility = np.sqrt(
                np.dot(portfolio_weights.T, np.dot(covariance_matrix, portfolio_weights))
            )
            
            # Calculate marginal contributions to risk
            marginal_contributions = np.dot(covariance_matrix, portfolio_weights) / portfolio_volatility
            
            # Calculate risk contributions
            risk_contributions = portfolio_weights * marginal_contributions
            
            # Calculate percentage contributions
            percentage_contributions = risk_contributions / portfolio_volatility * 100
            
            # Factor risk attribution if factor loadings provided
            factor_risk_attribution = {}
            if factor_loadings is not None and not factor_loadings.empty:
                factor_risk_attribution = self._calculate_factor_risk_attribution(
                    portfolio_weights, covariance_matrix, factor_loadings
                )
            
            results = {
                'portfolio_volatility': portfolio_volatility,
                'marginal_contributions': dict(zip(covariance_matrix.index, marginal_contributions)),
                'risk_contributions': dict(zip(covariance_matrix.index, risk_contributions)),
                'percentage_contributions': dict(zip(covariance_matrix.index, percentage_contributions)),
                'factor_risk_attribution': factor_risk_attribution,
                'concentration_analysis': {
                    'herfindahl_index': np.sum(percentage_contributions ** 2),
                    'max_contribution': np.max(percentage_contributions),
                    'min_contribution': np.min(percentage_contributions),
                    'contribution_std': np.std(percentage_contributions)
                },
                'analysis_date': datetime.now().isoformat()
            }
            
            # Store results
            attribution_id = f"risk_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.attribution_results[attribution_id] = results
            
            logger.info(f"Risk attribution completed: {portfolio_volatility:.4f} portfolio volatility")
            return results
            
        except Exception as e:
            logger.error(f"Risk attribution failed: {e}")
            return {}
    
    def _calculate_factor_risk_attribution(self, portfolio_weights: pd.Series,
                                         covariance_matrix: pd.DataFrame,
                                         factor_loadings: pd.DataFrame) -> Dict:
        """Calculate factor risk attribution"""
        
        # Calculate portfolio factor exposures
        portfolio_exposures = (factor_loadings.T * portfolio_weights).sum(axis=1)
        
        # Calculate factor covariance matrix (simplified)
        factor_covariance = factor_loadings.T @ covariance_matrix @ factor_loadings
        
        # Calculate factor risk contributions
        factor_risk_contributions = {}
        for factor in portfolio_exposures.index:
            factor_contribution = portfolio_exposures[factor] * np.sqrt(factor_covariance.loc[factor, factor])
            factor_risk_contributions[factor] = factor_contribution
        
        return factor_risk_contributions
    
    def calculate_style_attribution(self, portfolio_weights: pd.Series,
                                  style_factors: pd.DataFrame,
                                  style_returns: pd.Series) -> Dict:
        """Calculate style attribution analysis"""
        
        if style_factors.empty or style_returns.empty:
            logger.error("Style factor data required for style attribution")
            return {}
        
        try:
            # Calculate portfolio style exposures
            portfolio_style_exposures = (style_factors.T * portfolio_weights).sum(axis=1)
            
            # Calculate style contributions
            style_contributions = {}
            total_style_contribution = 0
            
            for style in style_returns.index:
                if style in portfolio_style_exposures.index:
                    style_contribution = portfolio_style_exposures[style] * style_returns[style]
                    style_contributions[style] = {
                        'exposure': portfolio_style_exposures[style],
                        'style_return': style_returns[style],
                        'contribution': style_contribution
                    }
                    total_style_contribution += style_contribution
            
            # Calculate total portfolio return
            portfolio_return = (portfolio_style_exposures * style_returns).sum()
            
            # Calculate residual return
            residual_return = portfolio_return - total_style_contribution
            
            results = {
                'portfolio_return': portfolio_return,
                'style_contributions': style_contributions,
                'total_style_contribution': total_style_contribution,
                'residual_return': residual_return,
                'portfolio_style_exposures': portfolio_style_exposures.to_dict(),
                'style_analysis': {
                    'dominant_style': max(style_contributions.items(), key=lambda x: abs(x[1]['contribution']))[0] if style_contributions else None,
                    'style_concentration': np.sum(np.array(list(portfolio_style_exposures.values())) ** 2),
                    'style_diversification': 1 / np.sum(np.array(list(portfolio_style_exposures.values())) ** 2) if np.sum(np.array(list(portfolio_style_exposures.values())) ** 2) > 0 else 0
                },
                'analysis_date': datetime.now().isoformat()
            }
            
            # Store results
            attribution_id = f"style_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.attribution_results[attribution_id] = results
            
            logger.info(f"Style attribution completed: {len(style_contributions)} styles")
            return results
            
        except Exception as e:
            logger.error(f"Style attribution failed: {e}")
            return {}
    
    def get_attribution_summary(self) -> Dict:
        """Get performance attribution summary"""
        return {
            'total_attributions': len(self.attribution_results),
            'attribution_types': list(set('brinson' if 'brinson' in k else 'factor' if 'factor' in k else 'risk' if 'risk' in k else 'style' for k in self.attribution_results.keys())),
            'available_attributions': list(self.attribution_results.keys())
        }
