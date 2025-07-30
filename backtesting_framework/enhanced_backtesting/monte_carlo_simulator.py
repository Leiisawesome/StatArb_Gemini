#!/usr/bin/env python3
"""
Monte Carlo Simulation
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

class MonteCarloSimulator:
    """Monte Carlo simulation for strategy analysis"""
    
    def __init__(self):
        self.simulation_results = {}
        self.scenario_analysis = {}
        
        logger.info("Initialized MonteCarloSimulator")
    
    def run_monte_carlo_simulation(self, historical_returns: pd.Series,
                                 n_simulations: int = 1000,
                                 simulation_horizon: int = 252,
                                 initial_capital: float = 100000) -> Dict:
        """Run Monte Carlo simulation"""
        
        if len(historical_returns) < 30:
            logger.warning(f"Insufficient data for Monte Carlo: {len(historical_returns)} observations")
            return {}
        
        try:
            logger.info(f"Starting Monte Carlo simulation: {n_simulations} simulations, {simulation_horizon} days")
            
            # Calculate historical statistics
            mean_return = historical_returns.mean()
            std_return = historical_returns.std()
            
            # Generate simulations
            simulation_paths = []
            final_values = []
            max_drawdowns = []
            sharpe_ratios = []
            
            for sim in range(n_simulations):
                # Generate random returns
                random_returns = np.random.normal(mean_return, std_return, simulation_horizon)
                
                # Calculate cumulative returns
                cumulative_returns = np.cumprod(1 + random_returns)
                portfolio_values = initial_capital * cumulative_returns
                
                # Calculate metrics
                final_value = portfolio_values[-1]
                total_return = (final_value - initial_capital) / initial_capital
                
                # Calculate drawdown
                peak = np.maximum.accumulate(portfolio_values)
                drawdown = (portfolio_values - peak) / peak
                max_drawdown = np.min(drawdown)
                
                # Calculate Sharpe ratio
                sharpe_ratio = np.mean(random_returns) / np.std(random_returns) * np.sqrt(252) if np.std(random_returns) > 0 else 0
                
                # Store results
                simulation_paths.append(portfolio_values)
                final_values.append(final_value)
                max_drawdowns.append(max_drawdown)
                sharpe_ratios.append(sharpe_ratio)
            
            # Calculate statistics
            final_values = np.array(final_values)
            max_drawdowns = np.array(max_drawdowns)
            sharpe_ratios = np.array(sharpe_ratios)
            
            # Calculate percentiles
            percentiles = [5, 10, 25, 50, 75, 90, 95]
            
            results = {
                'simulation_parameters': {
                    'n_simulations': n_simulations,
                    'simulation_horizon': simulation_horizon,
                    'initial_capital': initial_capital,
                    'historical_mean_return': mean_return,
                    'historical_std_return': std_return
                },
                'final_value_statistics': {
                    'mean': np.mean(final_values),
                    'std': np.std(final_values),
                    'min': np.min(final_values),
                    'max': np.max(final_values),
                    'percentiles': {f'p{p}': np.percentile(final_values, p) for p in percentiles}
                },
                'return_statistics': {
                    'mean_total_return': np.mean((final_values - initial_capital) / initial_capital),
                    'std_total_return': np.std((final_values - initial_capital) / initial_capital),
                    'positive_return_probability': np.mean(final_values > initial_capital),
                    'return_percentiles': {f'p{p}': np.percentile((final_values - initial_capital) / initial_capital, p) for p in percentiles}
                },
                'risk_statistics': {
                    'mean_max_drawdown': np.mean(max_drawdowns),
                    'std_max_drawdown': np.std(max_drawdowns),
                    'worst_drawdown': np.min(max_drawdowns),
                    'drawdown_percentiles': {f'p{p}': np.percentile(max_drawdowns, p) for p in percentiles}
                },
                'performance_statistics': {
                    'mean_sharpe_ratio': np.mean(sharpe_ratios),
                    'std_sharpe_ratio': np.std(sharpe_ratios),
                    'positive_sharpe_probability': np.mean(sharpe_ratios > 0),
                    'sharpe_percentiles': {f'p{p}': np.percentile(sharpe_ratios, p) for p in percentiles}
                },
                'simulation_paths': simulation_paths[:10],  # Store first 10 paths for visualization
                'simulation_date': datetime.now().isoformat()
            }
            
            # Store results
            simulation_id = f"monte_carlo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.simulation_results[simulation_id] = results
            
            logger.info(f"Monte Carlo simulation completed: {n_simulations} simulations")
            return results
            
        except Exception as e:
            logger.error(f"Monte Carlo simulation failed: {e}")
            return {}
    
    def run_bootstrap_simulation(self, historical_returns: pd.Series,
                               n_simulations: int = 1000,
                               simulation_horizon: int = 252,
                               initial_capital: float = 100000,
                               block_size: int = 21) -> Dict:
        """Run bootstrap simulation using historical data"""
        
        if len(historical_returns) < block_size:
            logger.warning(f"Insufficient data for bootstrap: {len(historical_returns)} < {block_size}")
            return {}
        
        try:
            logger.info(f"Starting bootstrap simulation: {n_simulations} simulations, block size {block_size}")
            
            # Generate bootstrap simulations
            simulation_paths = []
            final_values = []
            max_drawdowns = []
            sharpe_ratios = []
            
            for sim in range(n_simulations):
                # Generate bootstrap returns
                bootstrap_returns = []
                n_blocks = simulation_horizon // block_size
                
                for _ in range(n_blocks):
                    # Randomly select a block of returns
                    start_idx = np.random.randint(0, len(historical_returns) - block_size + 1)
                    block_returns = historical_returns.iloc[start_idx:start_idx + block_size]
                    bootstrap_returns.extend(block_returns)
                
                # Pad if necessary
                while len(bootstrap_returns) < simulation_horizon:
                    bootstrap_returns.append(historical_returns.iloc[np.random.randint(0, len(historical_returns))])
                
                bootstrap_returns = bootstrap_returns[:simulation_horizon]
                
                # Calculate cumulative returns
                cumulative_returns = np.cumprod(1 + np.array(bootstrap_returns))
                portfolio_values = initial_capital * cumulative_returns
                
                # Calculate metrics
                final_value = portfolio_values[-1]
                total_return = (final_value - initial_capital) / initial_capital
                
                # Calculate drawdown
                peak = np.maximum.accumulate(portfolio_values)
                drawdown = (portfolio_values - peak) / peak
                max_drawdown = np.min(drawdown)
                
                # Calculate Sharpe ratio
                sharpe_ratio = np.mean(bootstrap_returns) / np.std(bootstrap_returns) * np.sqrt(252) if np.std(bootstrap_returns) > 0 else 0
                
                # Store results
                simulation_paths.append(portfolio_values)
                final_values.append(final_value)
                max_drawdowns.append(max_drawdown)
                sharpe_ratios.append(sharpe_ratio)
            
            # Calculate statistics (similar to Monte Carlo)
            final_values = np.array(final_values)
            max_drawdowns = np.array(max_drawdowns)
            sharpe_ratios = np.array(sharpe_ratios)
            
            percentiles = [5, 10, 25, 50, 75, 90, 95]
            
            results = {
                'simulation_parameters': {
                    'n_simulations': n_simulations,
                    'simulation_horizon': simulation_horizon,
                    'initial_capital': initial_capital,
                    'block_size': block_size,
                    'method': 'bootstrap'
                },
                'final_value_statistics': {
                    'mean': np.mean(final_values),
                    'std': np.std(final_values),
                    'min': np.min(final_values),
                    'max': np.max(final_values),
                    'percentiles': {f'p{p}': np.percentile(final_values, p) for p in percentiles}
                },
                'return_statistics': {
                    'mean_total_return': np.mean((final_values - initial_capital) / initial_capital),
                    'std_total_return': np.std((final_values - initial_capital) / initial_capital),
                    'positive_return_probability': np.mean(final_values > initial_capital),
                    'return_percentiles': {f'p{p}': np.percentile((final_values - initial_capital) / initial_capital, p) for p in percentiles}
                },
                'risk_statistics': {
                    'mean_max_drawdown': np.mean(max_drawdowns),
                    'std_max_drawdown': np.std(max_drawdowns),
                    'worst_drawdown': np.min(max_drawdowns),
                    'drawdown_percentiles': {f'p{p}': np.percentile(max_drawdowns, p) for p in percentiles}
                },
                'performance_statistics': {
                    'mean_sharpe_ratio': np.mean(sharpe_ratios),
                    'std_sharpe_ratio': np.std(sharpe_ratios),
                    'positive_sharpe_probability': np.mean(sharpe_ratios > 0),
                    'sharpe_percentiles': {f'p{p}': np.percentile(sharpe_ratios, p) for p in percentiles}
                },
                'simulation_paths': simulation_paths[:10],
                'simulation_date': datetime.now().isoformat()
            }
            
            # Store results
            simulation_id = f"bootstrap_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.simulation_results[simulation_id] = results
            
            logger.info(f"Bootstrap simulation completed: {n_simulations} simulations")
            return results
            
        except Exception as e:
            logger.error(f"Bootstrap simulation failed: {e}")
            return {}
    
    def calculate_var_cvar(self, final_values: List[float],
                          confidence_levels: List[float] = [0.95, 0.99]) -> Dict:
        """Calculate Value at Risk (VaR) and Conditional Value at Risk (CVaR)"""
        
        if not final_values:
            return {}
        
        final_values = np.array(final_values)
        returns = (final_values - final_values[0]) / final_values[0]
        
        var_cvar_results = {}
        
        for confidence_level in confidence_levels:
            alpha = 1 - confidence_level
            
            # Calculate VaR
            var = np.percentile(returns, alpha * 100)
            
            # Calculate CVaR (Expected Shortfall)
            cvar = np.mean(returns[returns <= var])
            
            var_cvar_results[f'confidence_{int(confidence_level*100)}'] = {
                'var': var,
                'cvar': cvar,
                'var_absolute': var * final_values[0],
                'cvar_absolute': cvar * final_values[0]
            }
        
        return var_cvar_results
    
    def get_monte_carlo_summary(self) -> Dict:
        """Get Monte Carlo simulation summary"""
        return {
            'total_simulations': len(self.simulation_results),
            'simulation_types': list(set('monte_carlo' if 'monte_carlo' in k else 'bootstrap' for k in self.simulation_results.keys())),
            'available_simulations': list(self.simulation_results.keys())
        }
