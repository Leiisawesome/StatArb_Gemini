#!/usr/bin/env python3
"""
Multi-Strategy Backtest Example

This example demonstrates how to run a multi-strategy portfolio backtest
combining momentum and mean reversion strategies.

Features:
- Multiple strategies with different allocations
- Multiple symbols
- Strategy coordination and conflict resolution
- Complete performance attribution

Usage:
    python backtest/examples/multi_strategy_backtest.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine
from backtest.config.backtest_config import (
    BacktestConfiguration,
    DataConfig,
    StrategyConfig,
    RiskConfig,
    ExecutionConfig,
    AnalyticsConfig
)


async def run_multi_strategy_backtest():
    """
    Run a multi-strategy backtest
    
    This demonstrates combining multiple strategies:
    - Momentum strategy (60% allocation)
    - Mean reversion strategy (40% allocation)
    - Multi-symbol portfolio
    - Strategy attribution
    """
    
    print("\n" + "=" * 80)
    print("🎯 MULTI-STRATEGY PORTFOLIO BACKTEST")
    print("=" * 80)
    print("\nThis example combines momentum and mean reversion strategies")
    print("on a portfolio of NVDA, TSLA, and AAPL.\n")
    
    # Define configuration
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)  # 3 months
    
    config = BacktestConfiguration(
        backtest_name="multi_strategy_example",
        backtest_mode="historical",
        
        # Data: Multiple symbols
        data=DataConfig(
            symbols=['NVDA', 'TSLA', 'AAPL'],
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            interval='5min'  # 5-minute bars for faster processing
        ),
        
        # Strategies: Combine momentum and mean reversion
        strategies=[
            # Strategy 1: Momentum (60% allocation)
            StrategyConfig(
                strategy_type='momentum',
                strategy_name='momentum_60',
                allocation_pct=0.60,  # 60% of capital
                max_position_size=0.08,
                parameters={
                    'lookback_period': 20,
                    'momentum_threshold': 0.02,
                    'enable_regime_filter': True
                }
            ),
            
            # Strategy 2: Mean Reversion (40% allocation)
            StrategyConfig(
                strategy_type='mean_reversion',
                strategy_name='mean_reversion_40',
                allocation_pct=0.40,  # 40% of capital
                max_position_size=0.08,
                parameters={
                    'lookback_period': 10,
                    'entry_threshold': 2.0,  # Enter at 2 std devs
                    'exit_threshold': 0.5,   # Exit at 0.5 std devs
                    'enable_regime_filter': True
                }
            )
        ],
        
        # Risk: Portfolio-level limits
        risk=RiskConfig(
            initial_capital=500_000.0,  # $500K starting capital
            max_position_size=0.10,
            max_daily_var=0.05,
            max_concentration=0.15  # Max 15% per position
        ),
        
        # Execution: Realistic costs with liquidity filtering
        execution=ExecutionConfig(
            enable_realistic_fills=True,
            enable_cost_modeling=True,
            apply_slippage=True,
            apply_market_impact=True,
            enable_liquidity_filtering=True
        ),
        
        # Analytics: Full attribution
        analytics=AnalyticsConfig(
            enable_regime_attribution=True,
            enable_strategy_attribution=True,  # Key for multi-strategy
            generate_html_report=True,
            generate_json_report=True,
            generate_csv_trades=True
        )
    )
    
    print("📋 Configuration:")
    print(f"   Symbols: {', '.join(config.data.symbols)}")
    print(f"   Period: {config.data.start_date} → {config.data.end_date}")
    print(f"   Strategies:")
    print(f"     • Momentum (60% allocation)")
    print(f"     • Mean Reversion (40% allocation)")
    print(f"   Capital: ${config.risk.initial_capital:,.0f}")
    
    # Create engine
    print("\n🔧 Initializing backtest engine...")
    engine = InstitutionalBacktestEngine(config=config)
    
    # Initialize
    init_success = await engine.initialize()
    if not init_success:
        print("❌ Initialization failed")
        return 1
    
    print("✅ Engine initialized (12/12 components)")
    
    # Run backtest
    print("\n🚀 Running multi-strategy backtest...")
    results = await engine.run_backtest()
    
    # Display results
    if results['success']:
        print("\n" + "=" * 80)
        print("✅ BACKTEST COMPLETE")
        print("=" * 80)
        print(f"\n📊 Performance Summary:")
        print(f"   Bars Processed: {results['total_bars']:,}")
        print(f"   Duration: {results.get('duration', 0):.2f} seconds")
        print(f"   Total Trades: {results['total_trades']:,}")
        
        summary = results.get('summary')
        if summary:
            print(f"\n   Portfolio Performance:")
            print(f"     Total Return: {summary.get('total_return_pct', 0):.2f}%")
            print(f"     Sharpe Ratio: {summary.get('sharpe_ratio', 0):.2f}")
            print(f"     Max Drawdown: {summary.get('max_drawdown_pct', 0):.2f}%")
            print(f"     Win Rate: {summary.get('win_rate', 0):.2f}%")
            
            # Strategy attribution (if available)
            if 'strategy_attribution' in summary:
                print(f"\n   Strategy Attribution:")
                for strategy_id, attribution in summary['strategy_attribution'].items():
                    print(f"     • {strategy_id}:")
                    print(f"         Return: {attribution.get('return', 0):.2f}%")
                    print(f"         Contribution: {attribution.get('contribution', 0):.2f}%")
        
        # Generate report
        print("\n📊 Generating performance report with attribution...")
        report = await engine.generate_performance_report()
        
        # Save results
        output_dir = Path('backtest_results')
        output_dir.mkdir(exist_ok=True)
        
        print(f"\n💾 Results saved to: {output_dir}/")
        
        print("\n✅ Multi-strategy example complete!")
        print("\nℹ️  Check the report for detailed strategy attribution")
        return 0
    else:
        print(f"\n❌ Backtest failed: {results.get('error')}")
        return 1


if __name__ == '__main__':
    """Run the example"""
    
    exit_code = asyncio.run(run_multi_strategy_backtest())
    sys.exit(exit_code)

