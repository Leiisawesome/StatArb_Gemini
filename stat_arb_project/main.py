#!/usr/bin/env python3
"""
Professional Statistical Arbitrage Trading System
Main entry point with advanced features and production-ready implementation.
"""
import argparse
import logging
import sys
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd

from data_loader import DataLoader
from strategy.pair_trading import ProfessionalPairTradingStrategy
from backtesting.walk_forward import WalkForwardAnalyzer
from evaluation.performance import PerformanceEvaluator
from utils.config import load_config
from utils.logging_setup import setup_logging

def main():
    """Main entry point for the statistical arbitrage system."""
    parser = argparse.ArgumentParser(description='Professional Statistical Arbitrage Trading System')
    parser.add_argument('--config', type=str, default='config.yaml', help='Configuration file path')
    parser.add_argument('--mode', choices=['backtest', 'live', 'walk_forward'], default='backtest', 
                       help='Operation mode')
    parser.add_argument('--assets', nargs=2, help='Asset symbols (e.g., AAPL MSFT)')
    parser.add_argument('--start_date', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end_date', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--log_level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(level=getattr(logging, args.log_level))
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        config = load_config(args.config)
        logger.info("Configuration loaded successfully")
        
        # Override config with command line arguments
        if args.assets:
            config['trading']['asset1'] = args.assets[0]
            config['trading']['asset2'] = args.assets[1]
        
        if args.start_date:
            config['data']['start_date'] = args.start_date
        
        if args.end_date:
            config['data']['end_date'] = args.end_date
        
        # Validate configuration
        _validate_config(config)
        
        # Run selected mode
        if args.mode == 'backtest':
            run_backtest(config)
        elif args.mode == 'live':
            run_live_trading(config)
        elif args.mode == 'walk_forward':
            run_walk_forward_analysis(config)
        else:
            logger.error(f"Unknown mode: {args.mode}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"System error: {e}")
        sys.exit(1)

def _validate_config(config: Dict[str, Any]):
    """Validate configuration parameters."""
    required_sections = ['data', 'trading', 'risk_management']
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required configuration section: {section}")
    
    required_trading_params = ['asset1', 'asset2']
    for param in required_trading_params:
        if param not in config['trading']:
            raise ValueError(f"Missing required trading parameter: {param}")

def run_backtest(config: Dict[str, Any]):
    """Run backtesting with professional strategy."""
    logger = logging.getLogger(__name__)
    logger.info("Starting professional backtesting")
    
    # Load data
    data_loader = DataLoader(config['data'])
    data = data_loader.load_data([config['trading']['asset1'], config['trading']['asset2']])
    
    if data is None or data.empty:
        logger.error("Failed to load data")
        return
    
    logger.info(f"Loaded {len(data)} observations")
    
    # Initialize professional strategy
    strategy = ProfessionalPairTradingStrategy(
        asset1=config['trading']['asset1'],
        asset2=config['trading']['asset2'],
        kalman_params=config.get('kalman_filter', {}),
        cointegration_params=config.get('cointegration', {}),
        risk_params=config.get('risk_management', {}),
        signal_params=config.get('signal_generation', {})
    )
    
    # Run backtest
    results = []
    for i in range(len(data)):
        current_data = data.iloc[:i+1]
        result = strategy.update(current_data)
        results.append(result)
        
        # Log progress
        if i % 100 == 0:
            logger.info(f"Processed {i}/{len(data)} observations")
    
    # Evaluate performance
    evaluator = PerformanceEvaluator()
    performance = evaluator.evaluate_strategy(results, data)
    
    # Print results
    _print_backtest_results(performance, strategy)
    
    logger.info("Backtesting completed")

def run_live_trading(config: Dict[str, Any]):
    """Run live trading simulation."""
    logger = logging.getLogger(__name__)
    logger.info("Starting live trading simulation")
    
    # Initialize strategy
    strategy = ProfessionalPairTradingStrategy(
        asset1=config['trading']['asset1'],
        asset2=config['trading']['asset2'],
        kalman_params=config.get('kalman_filter', {}),
        cointegration_params=config.get('cointegration', {}),
        risk_params=config.get('risk_management', {}),
        signal_params=config.get('signal_generation', {})
    )
    
    # Load historical data for initialization
    data_loader = DataLoader(config['data'])
    historical_data = data_loader.load_data([config['trading']['asset1'], config['trading']['asset2']])
    
    if historical_data is None or historical_data.empty:
        logger.error("Failed to load historical data")
        return
    
    # Initialize strategy with historical data
    logger.info("Initializing strategy with historical data")
    for i in range(len(historical_data)):
        current_data = historical_data.iloc[:i+1]
        strategy.update(current_data)
    
    # Live trading loop (simulation)
    logger.info("Starting live trading loop")
    try:
        while True:
            # In a real implementation, this would fetch live data
            # For now, we'll simulate with the last historical data point
            current_data = historical_data.iloc[-1:]
            result = strategy.update(current_data)
            
            # Log trading activity
            if result.get('trades'):
                for trade in result['trades']:
                    logger.info(f"Trade executed: {trade}")
            
            # Check risk limits
            if result.get('risk_actions'):
                logger.warning(f"Risk actions: {result['risk_actions']}")
            
            # Print status periodically
            if len(strategy.daily_pnl) % 10 == 0:
                summary = strategy.get_strategy_summary()
                logger.info(f"Strategy status: {summary['performance']}")
            
            # Simulate time delay
            import time
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Live trading stopped by user")
    
    # Print final results
    summary = strategy.get_strategy_summary()
    _print_live_results(summary)

def run_walk_forward_analysis(config: Dict[str, Any]):
    """Run walk-forward analysis."""
    logger = logging.getLogger(__name__)
    logger.info("Starting walk-forward analysis")
    
    # Load data
    data_loader = DataLoader(config['data'])
    data = data_loader.load_data([config['trading']['asset1'], config['trading']['asset2']])
    
    if data is None or data.empty:
        logger.error("Failed to load data")
        return
    
    # Strategy factory function
    def strategy_factory(**kwargs):
        return ProfessionalPairTradingStrategy(
            asset1=config['trading']['asset1'],
            asset2=config['trading']['asset2'],
            kalman_params=config.get('kalman_filter', {}),
            cointegration_params=config.get('cointegration', {}),
            risk_params=config.get('risk_management', {}),
            signal_params={**config.get('signal_generation', {}), **kwargs}
        )
    
    # Parameter grid for optimization
    parameter_grid = config.get('walk_forward', {}).get('parameter_grid', {
        'entry_threshold': [1.5, 2.0, 2.5],
        'exit_threshold': [0.3, 0.5, 0.7],
        'stop_loss': [2.5, 3.0, 3.5]
    })
    
    # Run walk-forward analysis
    analyzer = WalkForwardAnalyzer(
        training_window=config.get('walk_forward', {}).get('training_window', 252),
        testing_window=config.get('walk_forward', {}).get('testing_window', 63),
        step_size=config.get('walk_forward', {}).get('step_size', 21)
    )
    
    results = analyzer.run_walk_forward_analysis(data, strategy_factory, parameter_grid)
    
    # Print results
    _print_walk_forward_results(results)
    
    logger.info("Walk-forward analysis completed")

def _print_backtest_results(performance: Dict[str, Any], strategy):
    """Print backtest results."""
    print("\n" + "="*60)
    print("BACKTEST RESULTS")
    print("="*60)
    
    print(f"Assets: {strategy.asset1} / {strategy.asset2}")
    print(f"Total P&L: ${performance.get('total_pnl', 0):,.2f}")
    print(f"Sharpe Ratio: {performance.get('sharpe_ratio', 0):.3f}")
    print(f"Max Drawdown: {performance.get('max_drawdown', 0):.2%}")
    print(f"Win Rate: {performance.get('win_rate', 0):.2%}")
    print(f"Total Trades: {performance.get('total_trades', 0)}")
    
    # Strategy-specific metrics
    summary = strategy.get_strategy_summary()
    print(f"\nKalman Filter:")
    print(f"  Hedge Ratio: {summary['kalman_state']['hedge_ratio']:.4f}")
    print(f"  Volatility: {summary['kalman_state']['volatility']:.4f}")
    print(f"  Observations: {summary['kalman_state']['observations']}")
    
    print(f"\nCointegration:")
    print(f"  Is Cointegrated: {summary['cointegration']['is_cointegrated']}")
    print(f"  Confidence: {summary['cointegration']['confidence']:.3f}")

def _print_live_results(summary: Dict[str, Any]):
    """Print live trading results."""
    print("\n" + "="*60)
    print("LIVE TRADING RESULTS")
    print("="*60)
    
    print(f"Assets: {summary['assets'][0]} / {summary['assets'][1]}")
    print(f"Current Position: {summary['position']['current']}")
    print(f"Total P&L: ${summary['performance'].get('total_pnl', 0):,.2f}")
    print(f"Sharpe Ratio: {summary['performance'].get('sharpe_ratio', 0):.3f}")
    print(f"Total Trades: {summary['performance'].get('total_trades', 0)}")

def _print_walk_forward_results(results: Dict[str, Any]):
    """Print walk-forward analysis results."""
    print("\n" + "="*60)
    print("WALK-FORWARD ANALYSIS RESULTS")
    print("="*60)
    
    summary = results.get('summary', {})
    print(f"Total Windows: {summary.get('total_windows', 0)}")
    print(f"Valid Windows: {summary.get('valid_windows', 0)}")
    print(f"Average Training Sharpe: {summary.get('avg_train_sharpe', 0):.3f}")
    print(f"Average Testing Sharpe: {summary.get('avg_test_sharpe', 0):.3f}")
    print(f"Average Performance Degradation: {summary.get('avg_performance_degradation', 0):.2%}")
    
    param_stability = summary.get('parameter_stability', {})
    print(f"Overall Parameter Stability: {param_stability.get('overall_stability', 0):.3f}")

if __name__ == "__main__":
    main() 