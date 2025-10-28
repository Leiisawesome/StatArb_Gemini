#!/usr/bin/env python3
"""
Momentum Strategy Backtest Prototype Launcher
==============================================

Simple launcher to wire the momentum strategy into the institutional backtest engine.
This prototype demonstrates desk integration without Phase 7 components.

Features:
- Registers momentum strategy in backtest mode
- Uses existing core_engine infrastructure
- Provides basic CLI for running backtests
- Separates strategy logic from desk wiring

Usage:
    python momentum_backtest_launcher.py --start-date 2023-01-01 --end-date 2023-12-31

Author: StatArb_Gemini Prototype
Version: 1.0.0
"""

import asyncio
import logging
import argparse
from typing import Dict, Any

# Import institutional backtest engine
from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine
from core_engine.config.system_config import BacktestConfig, BacktestMode

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MomentumBacktestLauncher:
    """Launcher for momentum strategy backtest prototype using institutional backtest engine"""

    def __init__(self):
        self.backtest_engine = None

    async def initialize(self, start_date: str, end_date: str) -> bool:
        """Initialize the institutional backtest engine with momentum strategy"""
        try:
            logger.info("🚀 Initializing Institutional Backtest Engine with Momentum Strategy...")

            # Create backtest configuration
            backtest_config = BacktestConfig(
                backtest_name="Momentum Strategy Prototype",
                backtest_mode=BacktestMode.SINGLE_STRATEGY,
                symbols=["SPY", "QQQ"],  # Example symbols for momentum trading
                start_date=start_date,
                end_date=end_date,
                initial_capital=1000000.0,
                commission_per_trade=0.001,
                enable_realistic_fills=True,
                enable_liquidity_filtering=True,
                strategies=[{
                    'type': 'momentum',
                    'name': 'enhanced_momentum',
                    'allocation_pct': 1.0,
                    'max_positions': 5,
                    'risk_limit': 0.05,
                    'lookback_period': 20,
                    'momentum_threshold': 0.02,
                    'adx_threshold': 25.0,
                    'volume_threshold': 1.2
                }]
            )

            # Create and initialize the institutional backtest engine
            self.backtest_engine = InstitutionalBacktestEngine(backtest_config)
            success = await self.backtest_engine.initialize()

            if not success:
                logger.error("Failed to initialize institutional backtest engine")
                return False

            logger.info("✅ Institutional backtest engine initialized successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            return False

    async def run_backtest(self) -> Dict[str, Any]:
        """Run the momentum strategy backtest using institutional backtest engine"""
        try:
            logger.info("🏃 Running backtest using Institutional Backtest Engine...")

            # Run the backtest using the institutional engine
            results = await self.backtest_engine.run_backtest()

            logger.info("✅ Backtest completed successfully")
            return results

        except Exception as e:
            logger.error(f"❌ Backtest failed: {e}")
            raise

    def print_results(self, results: Dict[str, Any]):
        """Print backtest results"""
        print("\n" + "="*50)
        print("📊 MOMENTUM STRATEGY BACKTEST RESULTS")
        print("="*50)
        print(f"Total Return: {results['total_return']:.2%}")
        print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
        print(f"Max Drawdown: {results['max_drawdown']:.2%}")
        print(f"Total Trades: {results['total_trades']}")
        print(f"Winning Trades: {results['winning_trades']}")
        print(f"Signals Generated: {results['signals_generated']}")
        print("="*50)


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Momentum Strategy Backtest Prototype')
    parser.add_argument('--start-date', type=str, default='2023-01-01',
                       help='Backtest start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default='2023-12-31',
                       help='Backtest end date (YYYY-MM-DD)')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create and run launcher
    launcher = MomentumBacktestLauncher()

    try:
        # Initialize
        success = await launcher.initialize(args.start_date, args.end_date)
        if not success:
            return 1

        # Run backtest
        results = await launcher.run_backtest()

        # Print results
        launcher.print_results(results)

        return 0

    except Exception as e:
        logger.error(f"Launcher failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)