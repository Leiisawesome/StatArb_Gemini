#!/usr/bin/env python3
"""
Stress Testing Framework
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

class StressTester:
    """Stress testing framework for portfolio analysis"""
    
    def __init__(self):
        self.stress_test_results = {}
        self.scenario_results = {}
        
        logger.info("Initialized StressTester")
    
    def run_market_stress_test(self, portfolio_weights: pd.Series,
                             historical_returns: pd.DataFrame,
                             stress_scenarios: Dict[str, Dict[str, float]] = None) -> Dict:
        """Run market stress tests"""
        
        if len(historical_returns) < 30:
            logger.warning(f"Insufficient data for stress testing: {len(historical_returns)} observations")
            return {}
        
        # Default stress scenarios if none provided
        if stress_scenarios is None:
            stress_scenarios = {
                'market_crash': {
                    'description': 'Severe market crash scenario',
                    'market_shock': -0.20,  # 20% market decline
                    'volatility_multiplier': 2.0,
                    'correlation_increase': 0.3
                },
                'flash_crash': {
                    'description': 'Flash crash scenario',
                    'market_shock': -0.10,  # 10% sudden decline
                    'volatility_multiplier': 3.0,
                    'correlation_increase': 0.5
                },
                'volatility_spike': {
                    'description': 'Volatility spike scenario',
                    'market_shock': -0.05,  # 5% decline
                    'volatility_multiplier': 2.5,
                    'correlation_increase': 0.2
                },
                'liquidity_crisis': {
                    'description': 'Liquidity crisis scenario',
                    'market_shock': -0.15,  # 15% decline
                    'volatility_multiplier': 2.0,
                    'correlation_increase': 0.4
                }
            }
        
        try:
            logger.info(f"Starting market stress tests: {len(stress_scenarios)} scenarios")
            
            stress_results = {}
            
            for scenario_name, scenario_params in stress_scenarios.items():
                logger.info(f"Running stress test: {scenario_name}")
                
                # Apply stress scenario to returns
                stressed_returns = self._apply_market_stress(
                    historical_returns, scenario_params
                )
                
                # Calculate portfolio performance under stress
                portfolio_performance = self._calculate_stress_performance(
                    portfolio_weights, stressed_returns, scenario_params
                )
                
                stress_results[scenario_name] = {
                    'scenario_params': scenario_params,
                    'portfolio_performance': portfolio_performance,
                    'stressed_returns_summary': {
                        'mean_return': stressed_returns.mean().mean(),
                        'volatility': stressed_returns.std().mean(),
                        'worst_day': stressed_returns.min().min(),
                        'best_day': stressed_returns.max().max()
                    }
                }
            
            # Store results
            test_id = f"market_stress_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.stress_test_results[test_id] = stress_results
            
            logger.info(f"Market stress tests completed: {len(stress_scenarios)} scenarios")
            return stress_results
            
        except Exception as e:
            logger.error(f"Market stress test failed: {e}")
            return {}
    
    def _apply_market_stress(self, historical_returns: pd.DataFrame,
                           scenario_params: Dict) -> pd.DataFrame:
        """Apply market stress scenario to historical returns"""
        
        stressed_returns = historical_returns.copy()
        
        # Apply market shock
        market_shock = scenario_params.get('market_shock', 0)
        if market_shock != 0:
            # Add market shock to all assets
            stressed_returns = stressed_returns + market_shock / 252  # Daily shock
        
        # Apply volatility multiplier
        volatility_multiplier = scenario_params.get('volatility_multiplier', 1.0)
        if volatility_multiplier != 1.0:
            # Scale returns by volatility multiplier
            stressed_returns = stressed_returns * volatility_multiplier
        
        # Apply correlation increase (simplified)
        correlation_increase = scenario_params.get('correlation_increase', 0)
        if correlation_increase > 0:
            # Add systematic component to increase correlations
            systematic_component = np.random.normal(0, correlation_increase * 0.02, len(stressed_returns))
            for col in stressed_returns.columns:
                stressed_returns[col] = stressed_returns[col] + systematic_component
        
        return stressed_returns
    
    def _calculate_stress_performance(self, portfolio_weights: pd.Series,
                                    stressed_returns: pd.DataFrame,
                                    scenario_params: Dict) -> Dict:
        """Calculate portfolio performance under stress"""
        
        # Calculate portfolio returns
        portfolio_returns = (stressed_returns * portfolio_weights).sum(axis=1)
        
        # Calculate performance metrics
        total_return = portfolio_returns.sum()
        volatility = portfolio_returns.std() * np.sqrt(252)
        sharpe_ratio = portfolio_returns.mean() / portfolio_returns.std() * np.sqrt(252) if portfolio_returns.std() > 0 else 0
        
        # Calculate drawdown
        cumulative_returns = (1 + portfolio_returns).cumprod()
        peak = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - peak) / peak
        max_drawdown = np.min(drawdown)
        
        # Calculate VaR and CVaR
        var_95 = np.percentile(portfolio_returns, 5)
        cvar_95 = np.mean(portfolio_returns[portfolio_returns <= var_95])
        
        performance = {
            'total_return': total_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'var_95': var_95,
            'cvar_95': cvar_95,
            'worst_day_return': portfolio_returns.min(),
            'best_day_return': portfolio_returns.max(),
            'negative_days_ratio': np.mean(portfolio_returns < 0)
        }
        
        return performance
    
    def run_factor_stress_test(self, portfolio_weights: pd.Series,
                             factor_loadings: pd.DataFrame,
                             factor_returns: pd.DataFrame,
                             stress_scenarios: Dict[str, Dict[str, float]] = None) -> Dict:
        """Run factor-based stress tests"""
        
        if factor_loadings.empty or factor_returns.empty:
            logger.warning("Factor data not available for stress testing")
            return {}
        
        # Default factor stress scenarios
        if stress_scenarios is None:
            stress_scenarios = {
                'momentum_crash': {
                    'description': 'Momentum factor crash',
                    'factor_shocks': {'momentum': -0.15, 'value': 0.05, 'size': 0.02},
                    'volatility_multiplier': 1.5
                },
                'value_rally': {
                    'description': 'Value factor rally',
                    'factor_shocks': {'momentum': -0.05, 'value': 0.10, 'size': -0.02},
                    'volatility_multiplier': 1.2
                },
                'size_premium_reversal': {
                    'description': 'Size premium reversal',
                    'factor_shocks': {'momentum': 0.02, 'value': -0.03, 'size': -0.08},
                    'volatility_multiplier': 1.3
                }
            }
        
        try:
            logger.info(f"Starting factor stress tests: {len(stress_scenarios)} scenarios")
            
            factor_stress_results = {}
            
            for scenario_name, scenario_params in stress_scenarios.items():
                logger.info(f"Running factor stress test: {scenario_name}")
                
                # Apply factor stress
                stressed_factor_returns = self._apply_factor_stress(
                    factor_returns, scenario_params
                )
                
                # Calculate portfolio performance under factor stress
                portfolio_performance = self._calculate_factor_stress_performance(
                    portfolio_weights, factor_loadings, stressed_factor_returns, scenario_params
                )
                
                factor_stress_results[scenario_name] = {
                    'scenario_params': scenario_params,
                    'portfolio_performance': portfolio_performance,
                    'factor_exposures': self._calculate_factor_exposures(portfolio_weights, factor_loadings)
                }
            
            # Store results
            test_id = f"factor_stress_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.stress_test_results[test_id] = factor_stress_results
            
            logger.info(f"Factor stress tests completed: {len(stress_scenarios)} scenarios")
            return factor_stress_results
            
        except Exception as e:
            logger.error(f"Factor stress test failed: {e}")
            return {}
    
    def _apply_factor_stress(self, factor_returns: pd.DataFrame,
                           scenario_params: Dict) -> pd.DataFrame:
        """Apply factor stress scenario"""
        
        stressed_factor_returns = factor_returns.copy()
        
        # Apply factor shocks
        factor_shocks = scenario_params.get('factor_shocks', {})
        for factor, shock in factor_shocks.items():
            if factor in stressed_factor_returns.columns:
                stressed_factor_returns[factor] = stressed_factor_returns[factor] + shock / 252
        
        # Apply volatility multiplier
        volatility_multiplier = scenario_params.get('volatility_multiplier', 1.0)
        if volatility_multiplier != 1.0:
            stressed_factor_returns = stressed_factor_returns * volatility_multiplier
        
        return stressed_factor_returns
    
    def _calculate_factor_stress_performance(self, portfolio_weights: pd.Series,
                                           factor_loadings: pd.DataFrame,
                                           stressed_factor_returns: pd.DataFrame,
                                           scenario_params: Dict) -> Dict:
        """Calculate portfolio performance under factor stress"""
        
        # Calculate portfolio factor exposures
        portfolio_exposures = (factor_loadings.T * portfolio_weights).sum(axis=1)
        
        # Calculate portfolio returns from factor returns
        portfolio_returns = (stressed_factor_returns * portfolio_exposures).sum(axis=1)
        
        # Calculate performance metrics (similar to market stress)
        total_return = portfolio_returns.sum()
        volatility = portfolio_returns.std() * np.sqrt(252)
        sharpe_ratio = portfolio_returns.mean() / portfolio_returns.std() * np.sqrt(252) if portfolio_returns.std() > 0 else 0
        
        # Calculate drawdown
        cumulative_returns = (1 + portfolio_returns).cumprod()
        peak = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - peak) / peak
        max_drawdown = np.min(drawdown)
        
        performance = {
            'total_return': total_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'worst_day_return': portfolio_returns.min(),
            'best_day_return': portfolio_returns.max(),
            'factor_contribution': portfolio_exposures.to_dict()
        }
        
        return performance
    
    def _calculate_factor_exposures(self, portfolio_weights: pd.Series,
                                  factor_loadings: pd.DataFrame) -> Dict:
        """Calculate portfolio factor exposures"""
        
        portfolio_exposures = (factor_loadings.T * portfolio_weights).sum(axis=1)
        return portfolio_exposures.to_dict()
    
    def get_stress_test_summary(self) -> Dict:
        """Get stress testing summary"""
        return {
            'total_stress_tests': len(self.stress_test_results),
            'test_types': list(set('market' if 'market_stress' in k else 'factor' for k in self.stress_test_results.keys())),
            'available_tests': list(self.stress_test_results.keys())
        }
