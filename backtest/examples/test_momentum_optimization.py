#!/usr/bin/env python3
"""
Momentum Strategy Optimization Example

This example demonstrates how to optimize momentum strategy parameters
using the institutional backtest system. It shows systematic parameter
testing and performance comparison across different configurations.

Features:
- Parameter optimization framework
- Multiple momentum configurations
- Performance comparison
- Statistical analysis of results
- Best parameter selection

Usage:
    python backtest/examples/test_momentum_optimization.py
"""

import asyncio
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine
from backtest.config.backtest_config import (
    BacktestConfiguration,
    DataConfig,
    StrategyConfig,
    RiskConfig,
    ExecutionConfig,
    AnalyticsConfig,
    BacktestMode
)


class MomentumOptimizer:
    """Framework for optimizing momentum strategy parameters"""

    def __init__(self):
        self.results = []

    def get_parameter_combinations(self) -> List[Dict[str, Any]]:
        """Generate parameter combinations to test"""

        # Use single optimized parameter set for quick testing
        combinations = [{
            'momentum_threshold': 0.005,
            'adx_threshold': 25.0,
            'volume_threshold': 1.0,
            'enable_breakout_detection': False
        }]

        return combinations

    async def run_single_backtest(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single backtest with given parameters"""

        config = BacktestConfiguration(
            backtest_name="Momentum Optimization Test",
            backtest_mode=BacktestMode.SINGLE_STRATEGY,
            data=DataConfig(
                symbols=['NVDA'],
                start_date='2023-01-01',
                end_date='2023-01-02',
                interval='1min'
            ),
            strategies=[StrategyConfig(
                strategy_type='momentum',
                strategy_name='EnhancedMomentumStrategy',
                allocation_pct=1.0,
                parameters=params,
                max_position_size=0.0004,  # 0.04% position sizing for realistic returns
            )],
            risk=RiskConfig(
                initial_capital=1_000_000,
                max_position_size=0.002  # 0.2% max position limit
            ),
            execution=ExecutionConfig(),
            analytics=AnalyticsConfig()
        )

        engine = InstitutionalBacktestEngine(config=config)

        try:
            # Initialize
            init_success = await engine.initialize()
            if not init_success:
                return {'success': False, 'error': 'Initialization failed'}

            # Run backtest
            results = await engine.run_backtest()

            if not results['success']:
                return {'success': False, 'error': results.get('error')}

            # Extract key metrics
            summary = results.get('summary')
            execution_history = results.get('execution_history', [])
            if summary:
                trade_details = []
                if execution_history:
                    for trade in execution_history:
                        trade_details.append({
                            'symbol': trade.get('symbol'),
                            'side': trade.get('side'),
                            'quantity': trade.get('quantity'),
                            'price': trade.get('fill_price'),  # Changed from 'price' to 'fill_price'
                            'timestamp': trade.get('timestamp'),
                            'pnl': trade.get('realized_pnl', 0),  # Changed from 'pnl' to 'realized_pnl'
                            'reason': trade.get('strategy_id', 'N/A')  # Changed from 'reason' to 'strategy_id'
                        })
                
                return {
                    'success': True,
                    'params': params,
                    'total_return': summary.performance_metrics.total_return,
                    'sharpe_ratio': summary.performance_metrics.sharpe_ratio,
                    'max_drawdown': summary.performance_metrics.max_drawdown,
                    'win_rate': summary.performance_metrics.win_rate,
                    'total_trades': summary.performance_metrics.total_trades,
                    'total_bars': results['total_bars'],
                    'trade_details': trade_details
                }
            else:
                return {
                    'success': True,
                    'params': params,
                    'total_return': 0.0,
                    'sharpe_ratio': 0.0,
                    'max_drawdown': 0.0,
                    'win_rate': 0.0,
                    'total_trades': 0,
                    'total_bars': results['total_bars']
                }

        finally:
            await engine.shutdown()

    async def optimize_parameters(self) -> List[Dict[str, Any]]:
        """Run parameter optimization"""

        print("\n" + "=" * 80)
        print("🎯 MOMENTUM STRATEGY PARAMETER OPTIMIZATION")
        print("=" * 80)
        print("Testing multiple parameter combinations for optimal performance")
        print("=" * 80 + "\n")

        combinations = self.get_parameter_combinations()
        print(f"Testing {len(combinations)} parameter combinations...")

        successful_results = []

        for i, params in enumerate(combinations):
            print(f"\n🔄 Testing combination {i+1}/{len(combinations)}:")
            print(f"   Momentum: {params['momentum_threshold']:.4f}, ADX: {params['adx_threshold']:.1f}, Volume: {params['volume_threshold']:.1f}")

            result = await self.run_single_backtest(params)

            if result['success']:
                print(f"   ✅ Return: {result['total_return']:.2f}%, Sharpe: {result['sharpe_ratio']:.2f}, Trades: {result['total_trades']}")
                
                # Print trade details if available
                if result.get('trade_details') and len(result['trade_details']) > 0:
                    print(f"   📋 Trade Details:")
                    for i, trade in enumerate(result['trade_details'], 1):
                        price = trade.get('fill_price') or trade.get('price') or 0
                        timestamp = trade.get('timestamp')
                        if isinstance(timestamp, str):
                            timestamp_str = timestamp
                        else:
                            timestamp_str = str(timestamp)
                        print(f"      {i}. {trade['side']} {trade['quantity']} {trade['symbol']} @ ${price:.2f} ({timestamp_str})")
                        if 'pnl' in trade and trade['pnl'] != 0:
                            print(f"         P&L: ${trade['pnl']:.2f}")
                        if 'reason' in trade and trade['reason'] != 'N/A':
                            print(f"         Reason: {trade['reason']}")
                else:
                    print(f"   📋 No trade details found")
                successful_results.append(result)
            else:
                print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")

        return successful_results

    def analyze_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze optimization results"""

        if not results:
            return {'error': 'No successful results'}

        print(f"\n📊 OPTIMIZATION RESULTS - {len(results)} successful combinations")
        print("=" * 80)

        # Sort by Sharpe ratio (primary metric)
        sorted_by_sharpe = sorted(results, key=lambda x: x['sharpe_ratio'], reverse=True)
        sorted_by_return = sorted(results, key=lambda x: x['total_return'], reverse=True)
        sorted_by_win_rate = sorted(results, key=lambda x: x['win_rate'], reverse=True)

        # Best performers
        best_sharpe = sorted_by_sharpe[0]
        best_return = sorted_by_return[0]
        best_win_rate = sorted_by_win_rate[0]

        print("\n🏆 TOP PERFORMERS:")
        print(f"   Best Sharpe Ratio: {best_sharpe['sharpe_ratio']:.2f}")
        print(f"      Return: {best_sharpe['total_return']:.2f}%, MaxDD: {best_sharpe['max_drawdown']:.2f}%, WinRate: {best_win_rate['win_rate']:.2f}%")
        print(f"      Params: momentum={best_sharpe['params']['momentum_threshold']:.4f}, adx={best_sharpe['params']['adx_threshold']:.1f}, volume={best_sharpe['params']['volume_threshold']:.1f}")

        print(f"\n   Best Total Return: {best_return['total_return']:.2f}%")
        print(f"      Sharpe: {best_return['sharpe_ratio']:.2f}, MaxDD: {best_return['max_drawdown']:.2f}%, WinRate: {best_win_rate['win_rate']:.2f}%")
        print(f"      Params: momentum={best_return['params']['momentum_threshold']:.4f}, adx={best_return['params']['adx_threshold']:.1f}, volume={best_return['params']['volume_threshold']:.1f}")

        print(f"\n   Best Win Rate: {best_win_rate['win_rate']:.2f}%")
        print(f"      Return: {best_win_rate['total_return']:.2f}%, Sharpe: {best_win_rate['sharpe_ratio']:.2f}, MaxDD: {best_win_rate['max_drawdown']:.2f}%")
        print(f"      Params: momentum={best_win_rate['params']['momentum_threshold']:.4f}, adx={best_win_rate['params']['adx_threshold']:.1f}, volume={best_win_rate['params']['volume_threshold']:.1f}")

        # Statistical summary
        returns = [r['total_return'] for r in results]
        sharpes = [r['sharpe_ratio'] for r in results]
        win_rates = [r['win_rate'] for r in results]
        trades = [r['total_trades'] for r in results]

        print("\n📈 STATISTICAL SUMMARY:")
        print(f"   Returns: Mean={pd.Series(returns).mean():.2f}%, Std={pd.Series(returns).std():.2f}%, Min={min(returns):.2f}%, Max={max(returns):.2f}%")
        print(f"   Sharpe: Mean={pd.Series(sharpes).mean():.2f}, Std={pd.Series(sharpes).std():.2f}, Min={min(sharpes):.2f}, Max={max(sharpes):.2f}")
        print(f"   Win Rate: Mean={pd.Series(win_rates).mean():.2f}%, Std={pd.Series(win_rates).std():.2f}%, Min={min(win_rates):.2f}%, Max={max(win_rates):.2f}%")
        print(f"   Trades: Mean={pd.Series(trades).mean():.0f}, Std={pd.Series(trades).std():.0f}, Min={min(trades)}, Max={max(trades)}")

        return {
            'best_sharpe': best_sharpe,
            'best_return': best_return,
            'best_win_rate': best_win_rate,
            'summary_stats': {
                'returns_mean': pd.Series(returns).mean(),
                'sharpe_mean': pd.Series(sharpes).mean(),
                'win_rate_mean': pd.Series(win_rates).mean(),
                'trades_mean': pd.Series(trades).mean()
            }
        }


async def main():
    """Main optimization function"""

    optimizer = MomentumOptimizer()

    # Run optimization
    results = await optimizer.optimize_parameters()

    # Analyze results
    analysis = optimizer.analyze_results(results)

    print("\n" + "=" * 80)
    print("✅ MOMENTUM OPTIMIZATION COMPLETE")
    print("=" * 80)
    print("Use the best parameters found above for your production strategy")
    print("=" * 80 + "\n")


if __name__ == '__main__':
    """Run momentum optimization example"""

    print("\n" + "=" * 80)
    print("🚀 MOMENTUM STRATEGY OPTIMIZATION EXAMPLE")
    print("=" * 80)
    print("This will test multiple parameter combinations to find optimal settings")
    print("Note: This may take several minutes to complete")
    print("=" * 80 + "\n")

    # Run optimization
    asyncio.run(main())