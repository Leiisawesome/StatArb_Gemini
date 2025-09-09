#!/usr/bin/env python3
"""
Centralized Backtest Runner
===========================

Simple script to run backtests using the centralized configuration system.
This eliminates hardcoded dates and provides flexible testing options.

Usage Examples:
  python run_centralized_backtests.py                    # Default test
  python run_centralized_backtests.py --scenario feb_2025_test  # February 2025
  python run_centralized_backtests.py --period jan_2025 --universe tech_stocks  # Custom

Author: StatArb Gemini Team
Version: 1.0.0
"""

import asyncio
import argparse
import sys
from pathlib import Path
import logging

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from configs.backtest_config_loader import BacktestConfigLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_momentum_backtest(config_loader: BacktestConfigLoader, **kwargs):
    """Run momentum backtest with centralized configuration"""
    try:
        config = config_loader.build_backtest_config("momentum", **kwargs)
        
        logger.info("🚀 MOMENTUM BACKTEST - CENTRALIZED CONFIGURATION")
        logger.info("=" * 60)
        logger.info(f"📊 Period: {config.trading_period.start_date} to {config.trading_period.end_date}")
        logger.info(f"📊 Universe: {config.universe.symbols}")
        logger.info(f"📊 Frequency: {config.data_config.frequency}")
        logger.info(f"📊 Capital: ${config.capital:,.2f}")
        logger.info(f"📊 Description: {config.trading_period.description}")
        logger.info("")
        
        # Here you would integrate with the actual momentum backtest
        # For now, we'll simulate the configuration being used
        logger.info("✅ Configuration loaded successfully")
        logger.info("📈 Momentum backtest would run with these parameters")
        logger.info("   (Integration with existing backtest pending)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Momentum backtest failed: {e}")
        return False

async def run_mean_reversion_backtest(config_loader: BacktestConfigLoader, **kwargs):
    """Run mean reversion backtest with centralized configuration"""
    try:
        config = config_loader.build_backtest_config("mean_reversion", **kwargs)
        
        logger.info("🚀 MEAN REVERSION BACKTEST - CENTRALIZED CONFIGURATION")
        logger.info("=" * 60)
        logger.info(f"📊 Period: {config.trading_period.start_date} to {config.trading_period.end_date}")
        logger.info(f"📊 Universe: {config.universe.symbols}")
        logger.info(f"📊 Frequency: {config.data_config.frequency}")
        logger.info(f"📊 Capital: ${config.capital:,.2f}")
        logger.info(f"📊 OU Process: {config.strategy_params.get('ou_process', True)}")
        logger.info("")
        
        logger.info("✅ Configuration loaded successfully")
        logger.info("📈 Mean reversion backtest would run with these parameters")
        logger.info("   (Integration with existing backtest pending)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Mean reversion backtest failed: {e}")
        return False

async def run_pairs_trading_backtest(config_loader: BacktestConfigLoader, **kwargs):
    """Run pairs trading backtest with centralized configuration"""
    try:
        config = config_loader.build_backtest_config("pairs_trading", **kwargs)
        
        logger.info("🚀 PAIRS TRADING BACKTEST - CENTRALIZED CONFIGURATION")
        logger.info("=" * 60)
        logger.info(f"📊 Period: {config.trading_period.start_date} to {config.trading_period.end_date}")
        logger.info(f"📊 Pairs: {config.universe.pairs}")
        logger.info(f"📊 Frequency: {config.data_config.frequency}")
        logger.info(f"📊 Capital: ${config.capital:,.2f}")
        logger.info(f"📊 Hedge Ratio Method: {config.strategy_params.get('hedge_ratio_method', 'kalman')}")
        logger.info("")
        
        logger.info("✅ Configuration loaded successfully")
        logger.info("📈 Pairs trading backtest would run with these parameters")
        logger.info("   (Integration with existing backtest pending)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Pairs trading backtest failed: {e}")
        return False

async def run_all_strategies(config_loader: BacktestConfigLoader, **kwargs):
    """Run all three strategies with the same configuration"""
    
    logger.info("🎯 RUNNING ALL STRATEGIES WITH CENTRALIZED CONFIGURATION")
    logger.info("=" * 80)
    
    results = {}
    
    # Run momentum
    logger.info("1️⃣ Running Momentum Strategy...")
    results['momentum'] = await run_momentum_backtest(config_loader, **kwargs)
    
    logger.info("")
    
    # Run mean reversion
    logger.info("2️⃣ Running Mean Reversion Strategy...")
    results['mean_reversion'] = await run_mean_reversion_backtest(config_loader, **kwargs)
    
    logger.info("")
    
    # Run pairs trading
    logger.info("3️⃣ Running Pairs Trading Strategy...")
    results['pairs_trading'] = await run_pairs_trading_backtest(config_loader, **kwargs)
    
    logger.info("")
    logger.info("📋 RESULTS SUMMARY:")
    logger.info("=" * 40)
    for strategy, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        logger.info(f"  {strategy.replace('_', ' ').title()}: {status}")
    
    return results

async def main():
    """Main function with command line argument parsing"""
    
    parser = argparse.ArgumentParser(
        description="Run backtests with centralized configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Default configuration
  %(prog)s --scenario feb_2025_test          # February 2025 test
  %(prog)s --period jan_2025 --universe tech_stocks  # Custom config
  %(prog)s --strategy momentum --period one_week     # Single strategy
  %(prog)s --all-strategies --scenario extended_test # All strategies
        """
    )
    
    parser.add_argument('--strategy', 
                       choices=['momentum', 'mean_reversion', 'pairs_trading', 'all'],
                       default='all',
                       help='Strategy to run (default: all)')
    
    parser.add_argument('--scenario',
                       help='Predefined scenario name')
    
    parser.add_argument('--period',
                       help='Trading period name')
    
    parser.add_argument('--universe',
                       help='Universe name')
    
    parser.add_argument('--frequency',
                       help='Data frequency')
    
    parser.add_argument('--capital',
                       type=float,
                       help='Capital amount')
    
    parser.add_argument('--all-strategies',
                       action='store_true',
                       help='Run all strategies')
    
    parser.add_argument('--list-options',
                       action='store_true',
                       help='List available configuration options')
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config_loader = BacktestConfigLoader()
        
        # List options if requested
        if args.list_options:
            logger.info("📋 AVAILABLE CONFIGURATION OPTIONS:")
            logger.info("=" * 50)
            logger.info(f"Periods: {config_loader.list_available_periods()}")
            logger.info(f"Universes: {config_loader.list_available_universes()}")
            logger.info(f"Scenarios: {config_loader.list_available_scenarios()}")
            return
        
        # Build configuration parameters
        config_params = {}
        if args.scenario:
            config_params['scenario'] = args.scenario
        if args.period:
            config_params['period'] = args.period
        if args.universe:
            config_params['universe'] = args.universe
        if args.frequency:
            config_params['frequency'] = args.frequency
        if args.capital:
            config_params['capital'] = args.capital
        
        # Run backtests
        if args.strategy == 'all' or args.all_strategies:
            await run_all_strategies(config_loader, **config_params)
        elif args.strategy == 'momentum':
            await run_momentum_backtest(config_loader, **config_params)
        elif args.strategy == 'mean_reversion':
            await run_mean_reversion_backtest(config_loader, **config_params)
        elif args.strategy == 'pairs_trading':
            await run_pairs_trading_backtest(config_loader, **config_params)
        
        logger.info("")
        logger.info("🎉 Centralized backtest execution completed!")
        
    except Exception as e:
        logger.error(f"❌ Execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
