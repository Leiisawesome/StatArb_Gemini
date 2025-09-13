#!/usr/bin/env python3
"""
Integration Layer
================

Integration components for connecting historical analytics with
existing backtesting and paper trading systems.

Author: StatArb Gemini Team
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime, timedelta
from pathlib import Path
import logging
import json

from .data_types import (
    BacktestConfig, BacktestSuite, InstrumentRankings,
    AnalysisResults, BacktestResult, BacktestResults
)

# Configure logging
logger = logging.getLogger(__name__)


class BacktestingSystemIntegration:
    """
    Integration with existing backtesting framework
    """
    
    def __init__(self, backtesting_module_path: Optional[str] = None):
        """
        Initialize backtesting integration
        
        Args:
            backtesting_module_path: Path to backtesting module
        """
        self.backtesting_module_path = backtesting_module_path
        self.execution_results: Dict[str, BacktestResult] = {}
        
        logger.info("BacktestingSystemIntegration initialized")
    
    def execute_backtest_suite(self, backtest_suite: BacktestSuite,
                              market_data_path: str,
                              execution_config: Optional[Dict[str, Any]] = None) -> BacktestResults:
        """
        Execute complete backtest suite using existing framework
        
        Args:
            backtest_suite: Suite of backtest configurations
            market_data_path: Path to market data for backtesting
            execution_config: Optional execution configuration
            
        Returns:
            Complete backtest results
        """
        logger.info(f"Executing backtest suite with {backtest_suite.total_configs} configurations")
        
        if execution_config is None:
            execution_config = self._get_default_execution_config()
        
        results = {
            'optimized': [],
            'baseline': [],
            'stress': []
        }
        
        # Execute optimized configurations
        for config in backtest_suite.optimized_configs:
            try:
                result = self._execute_single_backtest(config, market_data_path, execution_config)
                results['optimized'].append(result)
                self.execution_results[config.config_id] = result
            except Exception as e:
                logger.error(f"Failed to execute optimized config {config.config_id}: {e}")
        
        # Execute baseline configurations
        for config in backtest_suite.baseline_configs:
            try:
                result = self._execute_single_backtest(config, market_data_path, execution_config)
                results['baseline'].append(result)
                self.execution_results[config.config_id] = result
            except Exception as e:
                logger.error(f"Failed to execute baseline config {config.config_id}: {e}")
        
        # Execute stress test configurations
        for config in backtest_suite.stress_configs:
            try:
                result = self._execute_single_backtest(config, market_data_path, execution_config)
                results['stress'].append(result)
                self.execution_results[config.config_id] = result
            except Exception as e:
                logger.error(f"Failed to execute stress config {config.config_id}: {e}")
        
        # Generate performance comparison
        performance_comparison = self._generate_performance_comparison(results)
        
        # Create execution metadata
        execution_metadata = {
            'execution_timestamp': datetime.now().isoformat(),
            'total_configs_executed': sum(len(result_list) for result_list in results.values()),
            'execution_config': execution_config,
            'market_data_path': market_data_path
        }
        
        backtest_results = BacktestResults(
            results=results,
            performance_comparison=performance_comparison,
            execution_metadata=execution_metadata
        )
        
        logger.info(f"Backtest suite execution completed: {sum(len(r) for r in results.values())} successful runs")
        return backtest_results
    
    def convert_historical_config_to_backtest(self, config: BacktestConfig,
                                            target_backtest_format: str = 'standard') -> Dict[str, Any]:
        """
        Convert historical analytics config to backtesting framework format
        
        Args:
            config: Historical analytics backtest config
            target_backtest_format: Target format for conversion
            
        Returns:
            Converted configuration dictionary
        """
        logger.debug(f"Converting config {config.config_id} to {target_backtest_format} format")
        
        if target_backtest_format == 'standard':
            return self._convert_to_standard_format(config)
        elif target_backtest_format == 'vectorbt':
            return self._convert_to_vectorbt_format(config)
        elif target_backtest_format == 'zipline':
            return self._convert_to_zipline_format(config)
        else:
            raise ValueError(f"Unsupported backtest format: {target_backtest_format}")
    
    def _execute_single_backtest(self, config: BacktestConfig, 
                               market_data_path: str,
                               execution_config: Dict[str, Any]) -> BacktestResult:
        """Execute a single backtest configuration"""
        logger.debug(f"Executing backtest for config: {config.config_id}")
        
        # This is a mock implementation
        # In production, this would interface with the actual backtesting framework
        
        # Simulate backtest execution
        np.random.seed(hash(config.config_id) % 2**31)  # Deterministic randomness
        
        # Generate mock performance metrics based on config properties
        base_return = 0.08  # 8% base annual return
        
        # Adjust returns based on strategy and regime
        strategy_multiplier = self._get_strategy_multiplier(config.strategy)
        regime_multiplier = self._get_regime_multiplier(config.regime_context)
        
        # Add some randomness
        return_volatility = 0.15
        random_factor = np.random.normal(1.0, 0.1)
        
        total_return = base_return * strategy_multiplier * regime_multiplier * random_factor
        annualized_return = total_return
        
        # Generate other metrics
        sharpe_ratio = max(0.5, annualized_return / return_volatility + np.random.normal(0, 0.2))
        max_drawdown = max(0.05, min(0.3, abs(np.random.normal(0.1, 0.05))))
        win_rate = max(0.45, min(0.75, 0.6 + np.random.normal(0, 0.1)))
        trades_count = int(len(config.instruments) * 50 * np.random.uniform(0.8, 1.2))
        
        execution_metadata = {
            'execution_timestamp': datetime.now().isoformat(),
            'execution_duration_seconds': np.random.uniform(10, 60),
            'data_points_used': np.random.randint(1000, 5000),
            'strategy_specific_metrics': self._generate_strategy_specific_metrics(config.strategy)
        }
        
        performance_metrics = {
            'sortino_ratio': sharpe_ratio * 1.2,
            'calmar_ratio': annualized_return / max_drawdown,
            'information_ratio': sharpe_ratio * 0.8,
            'alpha': np.random.normal(0.02, 0.01),
            'beta': np.random.normal(1.0, 0.2)
        }
        
        return BacktestResult(
            config_id=config.config_id,
            total_return=total_return,
            annualized_return=annualized_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            trades_count=trades_count,
            execution_metadata=execution_metadata,
            performance_metrics=performance_metrics
        )
    
    def _convert_to_standard_format(self, config: BacktestConfig) -> Dict[str, Any]:
        """Convert to standard backtest format"""
        return {
            'strategy_name': config.strategy,
            'instruments': config.instruments,
            'start_date': '2020-01-01',  # Default dates
            'end_date': '2023-12-31',
            'initial_capital': 100000,
            'strategy_parameters': config.parameters,
            'risk_management': config.risk_params,
            'rebalance_frequency': config.parameters.get('rebalance_frequency', 'daily'),
            'commission': 0.001,
            'slippage': 0.0005
        }
    
    def _convert_to_vectorbt_format(self, config: BacktestConfig) -> Dict[str, Any]:
        """Convert to VectorBT format"""
        return {
            'symbols': config.instruments,
            'strategy_class': f"{config.strategy}_strategy",
            'params': config.parameters,
            'risk_params': config.risk_params,
            'freq': 'D',
            'cash_sharing': True
        }
    
    def _convert_to_zipline_format(self, config: BacktestConfig) -> Dict[str, Any]:
        """Convert to Zipline format"""
        return {
            'algo_text': self._generate_zipline_algo(config),
            'start': '2020-01-01',
            'end': '2023-12-31',
            'capital_base': 100000,
            'data_frequency': 'daily',
            'bundle': 'quandl'
        }
    
    def _generate_zipline_algo(self, config: BacktestConfig) -> str:
        """Generate Zipline algorithm code"""
        # This is a simplified example
        algo_template = f"""
def initialize(context):
    context.instruments = {config.instruments}
    context.strategy = '{config.strategy}'
    context.params = {config.parameters}
    
def handle_data(context, data):
    # Strategy implementation would go here
    pass
"""
        return algo_template
    
    def _get_default_execution_config(self) -> Dict[str, Any]:
        """Get default execution configuration"""
        return {
            'initial_capital': 100000,
            'commission': 0.001,
            'slippage': 0.0005,
            'benchmark': 'SPY',
            'risk_free_rate': 0.02,
            'execution_mode': 'simulation',
            'parallel_execution': True
        }
    
    def _get_strategy_multiplier(self, strategy: str) -> float:
        """Get performance multiplier based on strategy"""
        multipliers = {
            'mean_reversion': 0.9,
            'momentum': 1.1,
            'pairs_trading': 0.8
        }
        return multipliers.get(strategy, 1.0)
    
    def _get_regime_multiplier(self, regime: str) -> float:
        """Get performance multiplier based on regime"""
        multipliers = {
            'bull_market': 1.2,
            'bear_market': 0.7,
            'sideways_market': 0.9,
            'high_volatility': 0.8,
            'low_volatility': 1.1
        }
        return multipliers.get(regime, 1.0)
    
    def _generate_strategy_specific_metrics(self, strategy: str) -> Dict[str, float]:
        """Generate strategy-specific performance metrics"""
        if strategy == 'mean_reversion':
            return {
                'mean_reversion_strength': np.random.uniform(0.3, 0.8),
                'reversal_speed': np.random.uniform(2, 10),
                'signal_accuracy': np.random.uniform(0.55, 0.75)
            }
        elif strategy == 'momentum':
            return {
                'trend_strength': np.random.uniform(0.4, 0.9),
                'momentum_persistence': np.random.uniform(5, 20),
                'breakout_success_rate': np.random.uniform(0.4, 0.7)
            }
        elif strategy == 'pairs_trading':
            return {
                'cointegration_strength': np.random.uniform(0.6, 0.95),
                'spread_mean_reversion': np.random.uniform(0.5, 0.85),
                'hedge_effectiveness': np.random.uniform(0.7, 0.95)
            }
        else:
            return {}
    
    def _generate_performance_comparison(self, results: Dict[str, List[BacktestResult]]) -> Dict[str, Any]:
        """Generate performance comparison across config types"""
        comparison = {
            'summary_statistics': {},
            'performance_rankings': {},
            'risk_adjusted_metrics': {},
            'strategy_analysis': {}
        }
        
        # Calculate summary statistics for each config type
        for config_type, result_list in results.items():
            if result_list:
                returns = [r.annualized_return for r in result_list]
                sharpe_ratios = [r.sharpe_ratio for r in result_list]
                max_drawdowns = [r.max_drawdown for r in result_list]
                
                comparison['summary_statistics'][config_type] = {
                    'count': len(result_list),
                    'avg_return': np.mean(returns),
                    'avg_sharpe': np.mean(sharpe_ratios),
                    'avg_max_drawdown': np.mean(max_drawdowns),
                    'best_return': max(returns),
                    'worst_return': min(returns),
                    'return_std': np.std(returns)
                }
        
        # Find best performing configs
        all_results = [r for result_list in results.values() for r in result_list]
        if all_results:
            best_return = max(all_results, key=lambda x: x.annualized_return)
            best_sharpe = max(all_results, key=lambda x: x.sharpe_ratio)
            best_risk_adjusted = max(all_results, key=lambda x: x.annualized_return / (1 + x.max_drawdown))
            
            comparison['performance_rankings'] = {
                'best_return': {
                    'config_id': best_return.config_id,
                    'return': best_return.annualized_return,
                    'sharpe': best_return.sharpe_ratio
                },
                'best_sharpe': {
                    'config_id': best_sharpe.config_id,
                    'return': best_sharpe.annualized_return,
                    'sharpe': best_sharpe.sharpe_ratio
                },
                'best_risk_adjusted': {
                    'config_id': best_risk_adjusted.config_id,
                    'return': best_risk_adjusted.annualized_return,
                    'risk_adjusted_return': best_risk_adjusted.annualized_return / (1 + best_risk_adjusted.max_drawdown)
                }
            }
        
        return comparison


class PaperTradingIntegration:
    """
    Integration with paper trading system
    """
    
    def __init__(self, paper_trading_module_path: Optional[str] = None):
        """
        Initialize paper trading integration
        
        Args:
            paper_trading_module_path: Path to paper trading module
        """
        self.paper_trading_module_path = paper_trading_module_path
        self.active_strategies: Dict[str, Dict[str, Any]] = {}
        
        logger.info("PaperTradingIntegration initialized")
    
    def deploy_top_performers(self, rankings: InstrumentRankings,
                            deployment_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Deploy top performing strategies to paper trading
        
        Args:
            rankings: Instrument rankings from historical analysis
            deployment_config: Optional deployment configuration
            
        Returns:
            Deployment results
        """
        if deployment_config is None:
            deployment_config = self._get_default_deployment_config()
        
        deployment_results = {
            'deployed_strategies': [],
            'deployment_timestamp': datetime.now().isoformat(),
            'total_strategies_deployed': 0,
            'deployment_config': deployment_config
        }
        
        logger.info("Deploying top performers to paper trading")
        
        # Deploy top performers for each strategy/regime combination
        for strategy_name, regime_rankings in rankings.strategy_rankings.items():
            for regime_name, instruments in regime_rankings.items():
                if instruments:
                    # Take top N performers
                    top_n = deployment_config.get('top_performers_per_regime', 5)
                    top_performers = instruments[:top_n]
                    
                    strategy_id = f"{strategy_name}_{regime_name}"
                    
                    deployment_info = self._deploy_strategy_to_paper_trading(
                        strategy_id, strategy_name, regime_name, top_performers, deployment_config
                    )
                    
                    deployment_results['deployed_strategies'].append(deployment_info)
                    self.active_strategies[strategy_id] = deployment_info
        
        deployment_results['total_strategies_deployed'] = len(deployment_results['deployed_strategies'])
        
        logger.info(f"Deployed {deployment_results['total_strategies_deployed']} strategies to paper trading")
        return deployment_results
    
    def monitor_deployed_strategies(self) -> Dict[str, Any]:
        """Monitor performance of deployed strategies"""
        monitoring_results = {
            'monitoring_timestamp': datetime.now().isoformat(),
            'active_strategies_count': len(self.active_strategies),
            'strategy_performance': {},
            'alerts': []
        }
        
        for strategy_id, deployment_info in self.active_strategies.items():
            # Mock monitoring - in production would interface with paper trading system
            performance = self._mock_strategy_performance(strategy_id, deployment_info)
            monitoring_results['strategy_performance'][strategy_id] = performance
            
            # Check for alerts
            if performance['current_drawdown'] > 0.10:  # 10% drawdown threshold
                monitoring_results['alerts'].append({
                    'strategy_id': strategy_id,
                    'alert_type': 'high_drawdown',
                    'current_drawdown': performance['current_drawdown'],
                    'timestamp': datetime.now().isoformat()
                })
        
        return monitoring_results
    
    def _deploy_strategy_to_paper_trading(self, strategy_id: str, strategy_name: str,
                                        regime_name: str, top_performers: List,
                                        deployment_config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy a single strategy to paper trading"""
        logger.debug(f"Deploying strategy {strategy_id} to paper trading")
        
        # Mock deployment - in production would interface with paper trading system
        deployment_info = {
            'strategy_id': strategy_id,
            'strategy_name': strategy_name,
            'regime_context': regime_name,
            'instruments': [performer.symbol for performer in top_performers],
            'deployment_timestamp': datetime.now().isoformat(),
            'initial_capital': deployment_config.get('initial_capital_per_strategy', 10000),
            'position_sizing': deployment_config.get('position_sizing', 'equal_weight'),
            'rebalance_frequency': deployment_config.get('rebalance_frequency', 'weekly'),
            'status': 'active',
            'performance_tracking': {
                'start_value': deployment_config.get('initial_capital_per_strategy', 10000),
                'current_value': deployment_config.get('initial_capital_per_strategy', 10000),
                'total_return': 0.0,
                'max_drawdown': 0.0,
                'trades_executed': 0
            }
        }
        
        return deployment_info
    
    def _mock_strategy_performance(self, strategy_id: str, 
                                 deployment_info: Dict[str, Any]) -> Dict[str, Any]:
        """Mock strategy performance monitoring"""
        # Generate random but realistic performance data
        np.random.seed(hash(strategy_id) % 2**31)
        
        days_deployed = 30  # Assume 30 days
        daily_returns = np.random.normal(0.0008, 0.015, days_deployed)  # ~20% annual vol
        
        cumulative_returns = np.cumprod(1 + daily_returns)
        current_value = deployment_info['performance_tracking']['start_value'] * cumulative_returns[-1]
        total_return = cumulative_returns[-1] - 1
        
        # Calculate max drawdown
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = (cumulative_returns - running_max) / running_max
        max_drawdown = abs(np.min(drawdowns))
        current_drawdown = abs(drawdowns[-1])
        
        return {
            'current_value': current_value,
            'total_return': total_return,
            'annualized_return': (cumulative_returns[-1] ** (365/days_deployed)) - 1,
            'max_drawdown': max_drawdown,
            'current_drawdown': current_drawdown,
            'sharpe_ratio': np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252),
            'trades_executed': np.random.randint(20, 100),
            'last_updated': datetime.now().isoformat()
        }
    
    def _get_default_deployment_config(self) -> Dict[str, Any]:
        """Get default deployment configuration"""
        return {
            'top_performers_per_regime': 5,
            'initial_capital_per_strategy': 10000,
            'position_sizing': 'equal_weight',
            'rebalance_frequency': 'weekly',
            'risk_limits': {
                'max_position_size': 0.2,
                'max_total_exposure': 0.95,
                'stop_loss_threshold': 0.05
            },
            'monitoring_frequency': 'daily'
        }


class SystemIntegrationManager:
    """
    High-level manager for all system integrations
    """
    
    def __init__(self):
        self.backtesting_integration = BacktestingSystemIntegration()
        self.paper_trading_integration = PaperTradingIntegration()
        
        logger.info("SystemIntegrationManager initialized")
    
    def full_pipeline_integration(self, analysis_results: AnalysisResults,
                                market_data_path: str) -> Dict[str, Any]:
        """
        Execute full pipeline integration with backtesting and paper trading
        
        Args:
            analysis_results: Complete historical analytics results
            market_data_path: Path to market data
            
        Returns:
            Complete integration results
        """
        logger.info("Starting full pipeline integration")
        
        integration_results = {
            'integration_timestamp': datetime.now().isoformat(),
            'backtest_results': None,
            'paper_trading_deployment': None,
            'integration_summary': {}
        }
        
        try:
            # Execute backtests
            if analysis_results.backtest_suite:
                logger.info("Executing backtest suite")
                backtest_results = self.backtesting_integration.execute_backtest_suite(
                    analysis_results.backtest_suite, market_data_path
                )
                integration_results['backtest_results'] = backtest_results
            
            # Deploy to paper trading
            logger.info("Deploying to paper trading")
            paper_trading_deployment = self.paper_trading_integration.deploy_top_performers(
                analysis_results.instrument_rankings
            )
            integration_results['paper_trading_deployment'] = paper_trading_deployment
            
            # Generate integration summary
            integration_results['integration_summary'] = {
                'backtest_configs_executed': backtest_results.execution_metadata['total_configs_executed'] if backtest_results else 0,
                'strategies_deployed_to_paper_trading': paper_trading_deployment['total_strategies_deployed'],
                'integration_success': True
            }
            
            logger.info("Full pipeline integration completed successfully")
            
        except Exception as e:
            logger.error(f"Pipeline integration failed: {e}")
            integration_results['integration_summary'] = {
                'integration_success': False,
                'error_message': str(e)
            }
        
        return integration_results