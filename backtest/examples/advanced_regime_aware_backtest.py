#!/usr/bin/env python3
"""
Advanced Regime-Aware Backtest Example

This example demonstrates the most advanced features of the backtest system:
- Regime-first principle (Rule 13)
- Regime-aware strategy selection
- Multiple strategies optimized for different market conditions
- Complete performance attribution by regime and strategy

Features:
- 3 strategies optimized for different regimes
- Regime detection and adaptation
- Multi-symbol portfolio
- Institutional-grade risk management
- Complete analytics

Usage:
    python backtest/examples/advanced_regime_aware_backtest.py
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


async def run_advanced_regime_aware_backtest():
    """
    Run an advanced regime-aware backtest
    
    This demonstrates the full power of the institutional backtest system:
    - Regime detection (Rule 13: Regime-First Principle)
    - Multiple strategies optimized for different market conditions
    - Regime-based strategy weighting
    - Complete performance attribution by regime
    """
    
    print("\n" + "=" * 80)
    print("🌐 ADVANCED REGIME-AWARE BACKTEST")
    print("=" * 80)
    print("\nThis example demonstrates advanced regime-aware trading:")
    print("• Momentum strategy (favors trending regimes)")
    print("• Mean reversion strategy (favors range-bound regimes)")
    print("• Trend following strategy (adapts to regime transitions)")
    print("\nThe system automatically detects market regimes and adjusts")
    print("strategy weights accordingly.\n")
    
    # Define configuration
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)  # 6 months for regime diversity
    
    config = BacktestConfiguration(
        backtest_name="regime_aware_example",
        backtest_mode="historical",
        
        # Data: Large portfolio for regime diversity
        data=DataConfig(
            symbols=['NVDA', 'TSLA', 'AAPL', 'MSFT', 'GOOGL'],
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            interval='5min'
        ),
        
        # Strategies: Diversified across regime types
        strategies=[
            # Strategy 1: Momentum (favors trending regimes)
            StrategyConfig(
                strategy_type='momentum',
                strategy_name='momentum_trending',
                allocation_pct=0.40,  # Base 40% allocation
                max_position_size=0.06,
                parameters={
                    'lookback_period': 20,
                    'momentum_threshold': 0.02,
                    'enable_regime_filter': True,  # CRITICAL for regime awareness
                    'min_adx': 25.0,  # Require strong trend
                    'volume_factor': 1.5
                }
            ),
            
            # Strategy 2: Mean Reversion (favors range-bound regimes)
            StrategyConfig(
                strategy_type='mean_reversion',
                strategy_name='mean_reversion_rangebound',
                allocation_pct=0.30,  # Base 30% allocation
                max_position_size=0.06,
                parameters={
                    'lookback_period': 10,
                    'entry_threshold': 2.0,
                    'exit_threshold': 0.5,
                    'enable_regime_filter': True  # CRITICAL for regime awareness
                }
            ),
            
            # Strategy 3: Trend Following (adapts to regime transitions)
            StrategyConfig(
                strategy_type='trend_following',
                strategy_name='trend_adaptive',
                allocation_pct=0.30,  # Base 30% allocation
                max_position_size=0.06,
                parameters={
                    'short_window': 10,
                    'long_window': 30,
                    'trend_threshold': 0.015
                }
            )
        ],
        
        # Risk: Institutional-grade limits
        risk=RiskConfig(
            initial_capital=1_000_000.0,  # $1M capital
            max_position_size=0.08,  # Conservative 8% max
            max_daily_var=0.04,      # Tight 4% VaR limit
            max_concentration=0.12,  # Low 12% concentration
            min_signal_confidence=0.60  # Higher confidence threshold
        ),
        
        # Execution: Full institutional-grade simulation
        execution=ExecutionConfig(
            enable_realistic_fills=True,
            enable_cost_modeling=True,
            apply_spread_cost=True,
            apply_market_impact=True,
            apply_slippage=True,
            enable_liquidity_filtering=True
        ),
        
        # Analytics: Complete regime and strategy attribution
        analytics=AnalyticsConfig(
            enable_regime_attribution=True,      # CRITICAL for regime analysis
            enable_strategy_attribution=True,    # Strategy performance breakdown
            generate_html_report=True,
            generate_json_report=True,
            generate_csv_trades=True
        )
    )
    
    print("📋 Configuration:")
    print(f"   Symbols: {', '.join(config.data.symbols)}")
    print(f"   Period: {config.data.start_date} → {config.data.end_date} (6 months)")
    print(f"   Strategies:")
    for strategy in config.strategies:
        print(f"     • {strategy.strategy_name}: {strategy.allocation_pct:.0%} allocation")
    print(f"   Capital: ${config.risk.initial_capital:,.0f}")
    print(f"\n   Regime-Aware Features:")
    print(f"     • Regime detection per bar (Rule 13)")
    print(f"     • Dynamic strategy weighting by regime")
    print(f"     • Regime-adjusted risk limits")
    print(f"     • Complete regime attribution")
    
    # Create engine
    print("\n🔧 Initializing backtest engine...")
    engine = InstitutionalBacktestEngine(config=config)
    
    # Initialize
    init_success = await engine.initialize()
    if not init_success:
        print("❌ Initialization failed")
        return 1
    
    print("✅ Engine initialized (12/12 components)")
    print("   🌐 EnhancedRegimeEngine active (Rule 13)")
    
    # Run backtest
    print("\n🚀 Running regime-aware backtest...")
    print("   Regime detection will run on every bar...")
    results = await engine.run_backtest()
    
    # Display results
    if results['success']:
        print("\n" + "=" * 80)
        print("✅ REGIME-AWARE BACKTEST COMPLETE")
        print("=" * 80)
        print(f"\n📊 Overall Performance:")
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
            
            # Regime attribution (if available)
            if 'regime_attribution' in summary:
                print(f"\n   Performance by Regime:")
                for regime, attribution in summary['regime_attribution'].items():
                    print(f"     • {regime}:")
                    print(f"         Return: {attribution.get('return', 0):.2f}%")
                    print(f"         Trades: {attribution.get('trades', 0)}")
                    print(f"         Win Rate: {attribution.get('win_rate', 0):.1f}%")
            
            # Strategy attribution
            if 'strategy_attribution' in summary:
                print(f"\n   Performance by Strategy:")
                for strategy_id, attribution in summary['strategy_attribution'].items():
                    print(f"     • {strategy_id}:")
                    print(f"         Return: {attribution.get('return', 0):.2f}%")
                    print(f"         Contribution: {attribution.get('contribution', 0):.2f}%")
                    print(f"         Sharpe: {attribution.get('sharpe', 0):.2f}")
        
        # Generate report
        print("\n📊 Generating comprehensive regime analysis report...")
        report = await engine.generate_performance_report()
        
        # Save results
        output_dir = Path('backtest_results')
        output_dir.mkdir(exist_ok=True)
        
        print(f"\n💾 Results saved to: {output_dir}/")
        
        print("\n✅ Advanced regime-aware example complete!")
        print("\nℹ️  Key Insights:")
        print("   • Check regime attribution to see which regimes were most profitable")
        print("   • Compare strategy performance across different regimes")
        print("   • Analyze how strategies adapted to regime changes")
        print("   • Review the HTML report for complete visual analysis")
        
        return 0
    else:
        print(f"\n❌ Backtest failed: {results.get('error')}")
        return 1


if __name__ == '__main__':
    """Run the example"""
    
    exit_code = asyncio.run(run_advanced_regime_aware_backtest())
    sys.exit(exit_code)

