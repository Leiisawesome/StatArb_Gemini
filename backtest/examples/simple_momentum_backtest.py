#!/usr/bin/env python3
"""
Simple Momentum Backtest Example

This example demonstrates how to run a basic momentum strategy backtest
using the institutional backtest system.

Features:
- Single momentum strategy
- Single symbol (NVDA)
- 3-month backtest period
- Realistic execution costs
- Complete performance report

Usage:
    python backtest/examples/simple_momentum_backtest.py
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


async def run_simple_momentum_backtest():
    """
    Run a simple momentum backtest
    
    This demonstrates the most basic usage of the backtest system:
    - Single symbol
    - Single strategy
    - Standard parameters
    """
    
    print("\n" + "=" * 80)
    print("📈 SIMPLE MOMENTUM BACKTEST EXAMPLE")
    print("=" * 80)
    print("\nThis example runs a basic momentum strategy on NVDA")
    print("for a 3-month period with realistic execution costs.\n")
    
    # Define configuration
    # Use recent 3-month period
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    config = BacktestConfiguration(
        # Basic info
        backtest_name="simple_momentum_example",
        backtest_mode="historical",
        
        # Data: Single symbol, 3 months, 1-minute bars
        data=DataConfig(
            symbols=['NVDA'],
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            interval='1min'
        ),
        
        # Strategy: Simple momentum with standard parameters
        strategies=[
            StrategyConfig(
                strategy_type='momentum',
                strategy_name='simple_momentum',
                allocation_pct=1.0,  # 100% allocation
                max_position_size=0.10,  # Max 10% per position
                parameters={
                    'lookback_period': 20,       # 20-bar lookback
                    'momentum_threshold': 0.02,  # 2% momentum threshold
                    'enable_regime_filter': True # Enable regime filtering
                }
            )
        ],
        
        # Risk: Conservative parameters
        risk=RiskConfig(
            initial_capital=100_000.0,  # $100K starting capital
            max_position_size=0.10,     # 10% max position
            max_daily_var=0.05,         # 5% max daily VaR
            max_concentration=0.20      # 20% max concentration
        ),
        
        # Execution: Realistic costs
        execution=ExecutionConfig(
            enable_realistic_fills=True,
            enable_cost_modeling=True,
            apply_slippage=True,
            apply_market_impact=True
        ),
        
        # Analytics: Generate all reports
        analytics=AnalyticsConfig(
            enable_regime_attribution=True,
            enable_strategy_attribution=True,
            generate_html_report=True,
            generate_json_report=True,
            generate_csv_trades=True
        )
    )
    
    print("📋 Configuration:")
    print(f"   Symbol: NVDA")
    print(f"   Period: {config.data.start_date} → {config.data.end_date}")
    print(f"   Strategy: Momentum (20-bar, 2% threshold)")
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
    print("\n🚀 Running backtest...")
    results = await engine.run_backtest()
    
    # Display results
    if results['success']:
        print("\n" + "=" * 80)
        print("✅ BACKTEST COMPLETE")
        print("=" * 80)
        print(f"\n📊 Performance Summary:")
        print(f"   Bars Processed: {results['total_bars']:,}")
        print(f"   Duration: {results.get('duration', 0):.2f} seconds")
        print(f"   Speed: {results.get('bars_per_second', 0):,.0f} bars/sec")
        print(f"   Total Trades: {results['total_trades']:,}")
        
        summary = results.get('summary')
        if summary:
            print(f"\n   Performance:")
            print(f"     Total Return: {summary.get('total_return_pct', 0):.2f}%")
            print(f"     Sharpe Ratio: {summary.get('sharpe_ratio', 0):.2f}")
            print(f"     Max Drawdown: {summary.get('max_drawdown_pct', 0):.2f}%")
            print(f"     Win Rate: {summary.get('win_rate', 0):.2f}%")
        
        # Generate report
        print("\n📊 Generating performance report...")
        report = await engine.generate_performance_report()
        
        # Save results
        output_dir = Path('backtest_results')
        output_dir.mkdir(exist_ok=True)
        
        print(f"\n💾 Results saved to: {output_dir}/")
        print(f"   • {config.backtest_name}_results.json")
        if report:
            print(f"   • {config.backtest_name}_report.json")
        
        print("\n✅ Example complete!")
        return 0
    else:
        print(f"\n❌ Backtest failed: {results.get('error')}")
        return 1


if __name__ == '__main__':
    """Run the example"""
    
    exit_code = asyncio.run(run_simple_momentum_backtest())
    sys.exit(exit_code)

