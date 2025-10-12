#!/usr/bin/env python3
"""
Pairs Trading Strategy Assessment - GLD-GDX Pair
Test the Enhanced Pairs Trading Strategy with GLD-GDX on 1-minute data
"""

import asyncio
import logging
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.strategy_assessment.strategy_tester import ComprehensiveStrategyTester

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_pairs_trading_gld_gdx_config(tester, config_name, strategy_config, base_params):
    """Test a specific Pairs Trading configuration with GLD-GDX"""
    
    logger.info(f"\n{'='*60}")
    logger.info(f"🧪 Testing {config_name} Configuration (GLD-GDX)")
    logger.info(f"{'='*60}")
    
    # Create test configuration
    from tests.strategy_assessment.strategy_tester import StrategyTestConfig
    
    test_config = StrategyTestConfig(
        strategy_name="Enhanced Pairs Trading (GLD-GDX)",
        strategy_type="pairs_trading",
        symbols=base_params['symbols'],
        start_date=base_params['start_date'],
        end_date=base_params['end_date'],
        initial_capital=base_params['initial_capital'],
        data_interval=base_params['data_interval'],
        strategy_config=strategy_config
    )
    
    # Run backtest
    logger.info(f"🚀 Starting {config_name} backtest...")
    result = await tester.test_strategy(test_config)
    
    if result:
        logger.info(f"✅ {config_name} backtest completed")
        logger.info(f"📊 Results:")
        if hasattr(result, 'performance_metrics'):
            logger.info(f"  Total Return: {result.performance_metrics.total_return_pct:.2f}%")
            logger.info(f"  Sharpe Ratio: {result.performance_metrics.sharpe_ratio:.2f}")
            logger.info(f"  Max Drawdown: {result.performance_metrics.max_drawdown_pct:.2f}%")
            logger.info(f"  Total Trades: {result.trading_stats.total_trades}")
            logger.info(f"  Win Rate: {result.trading_stats.win_rate*100:.2f}%")
            logger.info(f"  Profit Factor: {result.trading_stats.profit_factor:.2f}")
        elif isinstance(result, dict):
            logger.info(f"  Total Return: {result.get('total_return_pct', 0.0):.2f}%")
            logger.info(f"  Sharpe Ratio: {result.get('sharpe_ratio', 0.0):.2f}")
            logger.info(f"  Max Drawdown: {result.get('max_drawdown_pct', 0.0):.2f}%")
            logger.info(f"  Total Trades: {result.get('total_trades', 0)}")
            logger.info(f"  Win Rate: {result.get('win_rate', 0.0)*100:.2f}%")
            logger.info(f"  Profit Factor: {result.get('profit_factor', 0.0):.2f}")
        else:
            logger.info(f"  Result type: {type(result)}")
            logger.info(f"  Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        
        # Grade the result
        if hasattr(result, 'performance_metrics'):
            if result.performance_metrics.sharpe_ratio > 1.0:
                grade = "A"
            elif result.performance_metrics.sharpe_ratio > 0.5:
                grade = "B"
            elif result.performance_metrics.sharpe_ratio > 0.0:
                grade = "C"
            else:
                grade = "F"
            
            logger.info(f"  Grade: {grade}")
        
        return result
    else:
        logger.error(f"❌ {config_name} backtest failed")
        return None

async def main():
    """Run comprehensive Pairs Trading strategy tests with GLD-GDX"""
    
    logger.info("="*80)
    logger.info("🚀 Starting Pairs Trading Strategy Assessment - GLD-GDX Pair")
    logger.info("="*80)
    
    # Initialize tester
    output_dir = "tests/strategy_assessment/results/pairs_trading_gld_gdx"
    tester = ComprehensiveStrategyTester(output_dir=output_dir)
    
    # Test parameters - GLD-GDX pair (classic gold correlation)
    symbols = ['GLD', 'GDX']  # Gold ETF and Gold Miners ETF
    start_date = "2024-01-02"
    end_date = "2024-01-05"  # Just 3 trading days for FAST testing
    initial_capital = 100000.0
    
    base_params = {
        'symbols': symbols,
        'start_date': start_date,
        'end_date': end_date,
        'initial_capital': initial_capital,
        'data_interval': '1min'  # 1-minute data
    }
    
    # Initialize core engine components
    from core_engine.data.manager import ClickHouseDataConfig
    data_config = ClickHouseDataConfig(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        enable_caching=True
    )
    
    await tester.initialize_components(data_config)
    
    logger.info(f"\n📋 Test Configuration:")
    logger.info(f"  Symbols: {', '.join(symbols)} (GLD-GDX Gold Pair)")
    logger.info(f"  Period: {start_date} to {end_date}")
    logger.info(f"  Data Interval: {base_params['data_interval']}")
    logger.info(f"  Initial Capital: ${initial_capital:,.0f}")
    logger.info(f"\n{'='*80}")
    
    results = {}
    
    # Test 1: BASELINE - Optimized for GLD-GDX correlation
    baseline_config = {
        'lookback_period': 60,        # 60 periods for distance calculation
        'entry_zscore': 1.5,          # Lower threshold for gold pair
        'exit_zscore': 0.3,           # Tighter exit for gold pair
        'stop_loss_zscore': 2.5,      # Tighter stop loss
        'min_correlation': 0.6,        # Lower correlation requirement for gold
        'position_size_pct': 0.04,    # 4% position size
        'max_pairs': 1,               # Single pair focus
    }
    results['baseline'] = await test_pairs_trading_gld_gdx_config(
        tester, 'BASELINE', baseline_config, base_params
    )
    
    # Test 2: CONSERVATIVE - Higher thresholds
    conservative_config = {
        'lookback_period': 80,        # Longer lookback for stability
        'entry_zscore': 2.0,         # Higher threshold for entry
        'exit_zscore': 0.2,          # Lower threshold for exit
        'stop_loss_zscore': 3.0,     # Wider stop loss
        'min_correlation': 0.7,       # Higher correlation requirement
        'position_size_pct': 0.03,   # Smaller position
        'max_pairs': 1,              # Single pair focus
    }
    results['conservative'] = await test_pairs_trading_gld_gdx_config(
        tester, 'CONSERVATIVE', conservative_config, base_params
    )
    
    # Test 3: AGGRESSIVE - Lower thresholds for more signals
    aggressive_config = {
        'lookback_period': 40,        # Shorter lookback for responsiveness
        'entry_zscore': 1.0,         # Much lower threshold for more signals
        'exit_zscore': 0.5,          # Higher threshold for exit
        'stop_loss_zscore': 2.0,     # Tighter stop loss
        'min_correlation': 0.5,       # Lower correlation requirement
        'position_size_pct': 0.05,   # Larger position
        'max_pairs': 1,              # Single pair focus
    }
    results['aggressive'] = await test_pairs_trading_gld_gdx_config(
        tester, 'AGGRESSIVE', aggressive_config, base_params
    )
    
    logger.info(f"\n{'='*80}")
    logger.info("📊 PAIRS TRADING STRATEGY COMPARISON - GLD-GDX")
    logger.info(f"{'='*80}\n")
    
    logger.info(f"{'Config':<15} {'Return %':<12} {'Sharpe':<10} {'MaxDD %':<12} {'Trades':<10} {'Win Rate %':<12}")
    logger.info(f"{'-'*80}")
    
    for config_name, result in results.items():
        if result:
            if hasattr(result, 'performance_metrics'):
                return_pct = result.performance_metrics.total_return_pct
                sharpe = result.performance_metrics.sharpe_ratio
                maxdd = result.performance_metrics.max_drawdown_pct
                trades = result.trading_stats.total_trades
                win_rate = result.trading_stats.win_rate * 100
            elif isinstance(result, dict):
                return_pct = result.get('total_return_pct', 0.0)
                sharpe = result.get('sharpe_ratio', 0.0)
                maxdd = result.get('max_drawdown_pct', 0.0)
                trades = result.get('total_trades', 0)
                win_rate = result.get('win_rate', 0.0) * 100
            else:
                return_pct = sharpe = maxdd = win_rate = 0.0
                trades = 0
            
            logger.info(f"{config_name.upper():<15} {return_pct:>10.2f}% {sharpe:>9.2f} {maxdd:>10.2f}% {trades:>9} {win_rate:>10.2f}%")
    
    logger.info(f"\n{'='*80}")
    logger.info("✅ Pairs Trading Strategy Assessment Complete - GLD-GDX!")
    logger.info(f"{'='*80}\n")
    
    # Identify best configuration
    best_config = None
    best_sharpe = -999
    
    for config_name, result in results.items():
        if result:
            if hasattr(result, 'performance_metrics'):
                sharpe = result.performance_metrics.sharpe_ratio
            elif isinstance(result, dict):
                sharpe = result.get('sharpe_ratio', 0.0)
            else:
                sharpe = 0.0
                
            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_config = config_name
    
    if best_config:
        logger.info(f"🏆 Best Configuration: {best_config.upper()} (Sharpe: {best_sharpe:.2f})")
        
        best_result = results[best_config]
        logger.info(f"\n📈 Best Configuration Details:")
        if hasattr(best_result, 'performance_metrics'):
            logger.info(f"  Total Return: {best_result.performance_metrics.total_return_pct:.2f}%")
            logger.info(f"  Sharpe Ratio: {best_result.performance_metrics.sharpe_ratio:.2f}")
            logger.info(f"  Max Drawdown: {best_result.performance_metrics.max_drawdown_pct:.2f}%")
            logger.info(f"  Win Rate: {best_result.trading_stats.win_rate*100:.2f}%")
            logger.info(f"  Total Trades: {best_result.trading_stats.total_trades}")
            logger.info(f"  Profit Factor: {best_result.trading_stats.profit_factor:.2f}")
        elif isinstance(best_result, dict):
            logger.info(f"  Total Return: {best_result.get('total_return_pct', 0.0):.2f}%")
            logger.info(f"  Sharpe Ratio: {best_result.get('sharpe_ratio', 0.0):.2f}")
            logger.info(f"  Max Drawdown: {best_result.get('max_drawdown_pct', 0.0):.2f}%")
            logger.info(f"  Win Rate: {best_result.get('win_rate', 0.0)*100:.2f}%")
            logger.info(f"  Total Trades: {best_result.get('total_trades', 0)}")
            logger.info(f"  Profit Factor: {best_result.get('profit_factor', 0.0):.2f}")
    
    logger.info(f"\n📁 Results saved to: {output_dir}")

if __name__ == "__main__":
    asyncio.run(main())
