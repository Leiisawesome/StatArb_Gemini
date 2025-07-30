#!/usr/bin/env python3
"""
Scenario Analysis
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

class ScenarioAnalyzer:
    """Scenario analysis for portfolio evaluation"""
    
    def __init__(self):
        self.scenario_results = {}
        self.scenario_analysis = {}
        
        logger.info("Initialized ScenarioAnalyzer")
    
    def run_economic_scenarios(self, portfolio_weights: pd.Series,
                             historical_data: pd.DataFrame,
                             scenarios: Dict[str, Dict] = None) -> Dict:
        """Run economic scenario analysis"""
        
        if len(historical_data) < 30:
            logger.warning(f"Insufficient data for scenario analysis: {len(historical_data)} observations")
            return {}
        
        # Default economic scenarios
        if scenarios is None:
            scenarios = {
                'recession': {
                    'description': 'Economic recession scenario',
                    'market_impact': -0.25,
                    'volatility_increase': 1.8,
                    'correlation_increase': 0.4,
                    'liquidity_reduction': 0.3
                },
                'inflation_shock': {
                    'description': 'Inflation shock scenario',
                    'market_impact': -0.15,
                    'volatility_increase': 1.5,
                    'correlation_increase': 0.2,
                    'liquidity_reduction': 0.2
                },
                'interest_rate_hike': {
                    'description': 'Interest rate hike scenario',
                    'market_impact': -0.10,
                    'volatility_increase': 1.3,
                    'correlation_increase': 0.1,
                    'liquidity_reduction': 0.1
                },
                'growth_acceleration': {
                    'description': 'Economic growth acceleration',
                    'market_impact': 0.20,
                    'volatility_increase': 1.2,
                    'correlation_increase': 0.1,
                    'liquidity_reduction': -0.1
                },
                'deflation': {
                    'description': 'Deflation scenario',
                    'market_impact': -0.20,
                    'volatility_increase': 1.6,
                    'correlation_increase': 0.3,
                    'liquidity_reduction': 0.2
                }
            }
        
        try:
            logger.info(f"Starting economic scenario analysis: {len(scenarios)} scenarios")
            
            scenario_results = {}
            
            for scenario_name, scenario_params in scenarios.items():
                logger.info(f"Running scenario: {scenario_name}")
                
                # Apply economic scenario
                scenario_data = self._apply_economic_scenario(
                    historical_data, scenario_params
                )
                
                # Calculate portfolio performance under scenario
                portfolio_performance = self._calculate_scenario_performance(
                    portfolio_weights, scenario_data, scenario_params
                )
                
                scenario_results[scenario_name] = {
                    'scenario_params': scenario_params,
                    'portfolio_performance': portfolio_performance,
                    'scenario_impact': self._calculate_scenario_impact(
                        historical_data, scenario_data
                    )
                }
            
            # Store results
            analysis_id = f"economic_scenarios_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.scenario_results[analysis_id] = scenario_results
            
            logger.info(f"Economic scenario analysis completed: {len(scenarios)} scenarios")
            return scenario_results
            
        except Exception as e:
            logger.error(f"Economic scenario analysis failed: {e}")
            return {}
    
    def _apply_economic_scenario(self, historical_data: pd.DataFrame,
                               scenario_params: Dict) -> pd.DataFrame:
        """Apply economic scenario to historical data"""
        
        scenario_data = historical_data.copy()
        
        # Apply market impact
        market_impact = scenario_params.get('market_impact', 0)
        if market_impact != 0:
            # Apply market impact to returns
            if 'returns' in scenario_data.columns:
                scenario_data['returns'] = scenario_data['returns'] + market_impact / 252
            else:
                # Apply to price data
                scenario_data = scenario_data * (1 + market_impact / 252)
        
        # Apply volatility increase
        volatility_increase = scenario_params.get('volatility_increase', 1.0)
        if volatility_increase != 1.0:
            # Scale returns by volatility multiplier
            if 'returns' in scenario_data.columns:
                scenario_data['returns'] = scenario_data['returns'] * volatility_increase
            else:
                # Apply to price changes
                price_changes = scenario_data.pct_change()
                scenario_data = scenario_data * (1 + price_changes * (volatility_increase - 1))
        
        # Apply correlation increase (simplified)
        correlation_increase = scenario_params.get('correlation_increase', 0)
        if correlation_increase > 0:
            # Add systematic component
            systematic_component = np.random.normal(0, correlation_increase * 0.02, len(scenario_data))
            for col in scenario_data.columns:
                if col != 'returns':
                    scenario_data[col] = scenario_data[col] + systematic_component
        
        return scenario_data
    
    def _calculate_scenario_performance(self, portfolio_weights: pd.Series,
                                      scenario_data: pd.DataFrame,
                                      scenario_params: Dict) -> Dict:
        """Calculate portfolio performance under scenario"""
        
        # Calculate portfolio returns under scenario
        if 'returns' in scenario_data.columns:
            portfolio_returns = scenario_data['returns'] * portfolio_weights.sum()
        else:
            # Calculate returns from price data
            returns = scenario_data.pct_change().dropna()
            portfolio_returns = (returns * portfolio_weights).sum(axis=1)
        
        # Calculate performance metrics
        total_return = portfolio_returns.sum()
        volatility = portfolio_returns.std() * np.sqrt(252)
        sharpe_ratio = portfolio_returns.mean() / portfolio_returns.std() * np.sqrt(252) if portfolio_returns.std() > 0 else 0
        
        # Calculate drawdown
        cumulative_returns = (1 + portfolio_returns).cumprod()
        peak = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - peak) / peak
        max_drawdown = np.min(drawdown)
        
        # Calculate scenario-specific metrics
        liquidity_reduction = scenario_params.get('liquidity_reduction', 0)
        transaction_cost_impact = liquidity_reduction * 0.01  # 1% transaction cost impact
        
        performance = {
            'total_return': total_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'worst_day_return': portfolio_returns.min(),
            'best_day_return': portfolio_returns.max(),
            'transaction_cost_impact': transaction_cost_impact,
            'net_return': total_return - transaction_cost_impact
        }
        
        return performance
    
    def _calculate_scenario_impact(self, historical_data: pd.DataFrame,
                                 scenario_data: pd.DataFrame) -> Dict:
        """Calculate impact of scenario on data"""
        
        impact = {}
        
        # Calculate return impact
        if 'returns' in historical_data.columns and 'returns' in scenario_data.columns:
            impact['return_impact'] = scenario_data['returns'].mean() - historical_data['returns'].mean()
            impact['volatility_impact'] = scenario_data['returns'].std() - historical_data['returns'].std()
        
        # Calculate price impact
        price_impact = (scenario_data.iloc[-1] - historical_data.iloc[-1]) / historical_data.iloc[-1]
        impact['price_impact'] = price_impact.mean()
        
        return impact
    
    def run_regime_scenarios(self, portfolio_weights: pd.Series,
                           historical_data: pd.DataFrame,
                           regime_scenarios: Dict[str, Dict] = None) -> Dict:
        """Run regime-based scenario analysis"""
        
        if len(historical_data) < 30:
            logger.warning(f"Insufficient data for regime scenario analysis")
            return {}
        
        # Default regime scenarios
        if regime_scenarios is None:
            regime_scenarios = {
                'bull_market': {
                    'description': 'Bull market regime',
                    'return_multiplier': 1.5,
                    'volatility_multiplier': 0.8,
                    'correlation_decrease': 0.1
                },
                'bear_market': {
                    'description': 'Bear market regime',
                    'return_multiplier': 0.5,
                    'volatility_multiplier': 1.5,
                    'correlation_increase': 0.2
                },
                'sideways_market': {
                    'description': 'Sideways market regime',
                    'return_multiplier': 0.8,
                    'volatility_multiplier': 1.2,
                    'correlation_increase': 0.05
                },
                'crisis_regime': {
                    'description': 'Financial crisis regime',
                    'return_multiplier': 0.3,
                    'volatility_multiplier': 2.0,
                    'correlation_increase': 0.4
                }
            }
        
        try:
            logger.info(f"Starting regime scenario analysis: {len(regime_scenarios)} scenarios")
            
            regime_results = {}
            
            for regime_name, regime_params in regime_scenarios.items():
                logger.info(f"Running regime scenario: {regime_name}")
                
                # Apply regime scenario
                regime_data = self._apply_regime_scenario(
                    historical_data, regime_params
                )
                
                # Calculate portfolio performance under regime
                portfolio_performance = self._calculate_regime_performance(
                    portfolio_weights, regime_data, regime_params
                )
                
                regime_results[regime_name] = {
                    'regime_params': regime_params,
                    'portfolio_performance': portfolio_performance,
                    'regime_characteristics': self._calculate_regime_characteristics(regime_data)
                }
            
            # Store results
            analysis_id = f"regime_scenarios_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.scenario_results[analysis_id] = regime_results
            
            logger.info(f"Regime scenario analysis completed: {len(regime_scenarios)} scenarios")
            return regime_results
            
        except Exception as e:
            logger.error(f"Regime scenario analysis failed: {e}")
            return {}
    
    def _apply_regime_scenario(self, historical_data: pd.DataFrame,
                             regime_params: Dict) -> pd.DataFrame:
        """Apply regime scenario to historical data"""
        
        regime_data = historical_data.copy()
        
        # Apply return multiplier
        return_multiplier = regime_params.get('return_multiplier', 1.0)
        if return_multiplier != 1.0:
            if 'returns' in regime_data.columns:
                regime_data['returns'] = regime_data['returns'] * return_multiplier
            else:
                # Apply to price changes
                price_changes = regime_data.pct_change()
                regime_data = regime_data * (1 + price_changes * (return_multiplier - 1))
        
        # Apply volatility multiplier
        volatility_multiplier = regime_params.get('volatility_multiplier', 1.0)
        if volatility_multiplier != 1.0:
            if 'returns' in regime_data.columns:
                regime_data['returns'] = regime_data['returns'] * volatility_multiplier
            else:
                price_changes = regime_data.pct_change()
                regime_data = regime_data * (1 + price_changes * (volatility_multiplier - 1))
        
        return regime_data
    
    def _calculate_regime_performance(self, portfolio_weights: pd.Series,
                                    regime_data: pd.DataFrame,
                                    regime_params: Dict) -> Dict:
        """Calculate portfolio performance under regime"""
        
        # Similar to scenario performance calculation
        if 'returns' in regime_data.columns:
            portfolio_returns = regime_data['returns'] * portfolio_weights.sum()
        else:
            returns = regime_data.pct_change().dropna()
            portfolio_returns = (returns * portfolio_weights).sum(axis=1)
        
        # Calculate performance metrics
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
            'regime_multiplier': regime_params.get('return_multiplier', 1.0)
        }
        
        return performance
    
    def _calculate_regime_characteristics(self, regime_data: pd.DataFrame) -> Dict:
        """Calculate regime characteristics"""
        
        characteristics = {}
        
        if 'returns' in regime_data.columns:
            characteristics['mean_return'] = regime_data['returns'].mean()
            characteristics['volatility'] = regime_data['returns'].std()
            characteristics['skewness'] = regime_data['returns'].skew()
            characteristics['kurtosis'] = regime_data['returns'].kurtosis()
        
        return characteristics
    
    def get_scenario_summary(self) -> Dict:
        """Get scenario analysis summary"""
        return {
            'total_scenarios': len(self.scenario_results),
            'scenario_types': list(set('economic' if 'economic_scenarios' in k else 'regime' for k in self.scenario_results.keys())),
            'available_scenarios': list(self.scenario_results.keys())
        }
