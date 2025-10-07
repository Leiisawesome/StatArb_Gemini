"""
Trend Following Strategy Testing Script
========================================

Professional backtesting framework for Trend Following strategy.

Test Configurations:
1. BASELINE: Moderate parameters for testing
2. CONSERVATIVE: Strict filters, fewer signals, better quality
3. AGGRESSIVE: Relaxed filters, more signals, more active trading

Author: StatArb_Gemini Phase 5 Assessment
Version: 1.0.0
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime
from typing import Dict, Any
import logging

# Import testing framework
from tests.strategy_assessment.strategy_tester import ComprehensiveStrategyTester, StrategyTestConfig
from tests.strategy_assessment.strategy_config_factory import StrategyConfigFactory
from core_engine.type_definitions.strategy import StrategyType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_trend_following_config(
    tester: ComprehensiveStrategyTester,
    config_name: str,
    strategy_params: Dict[str, Any],
    base_params: Dict[str, Any]
) -> Dict[str, Any]:
    """Test a specific Trend Following configuration"""
    
    logger.info(f"\n{'='*80}")
    logger.info(f"🧪 Testing Trend Following - {config_name}")
    logger.info(f"{'='*80}\n")
    
    # Create test configuration
    test_config = StrategyTestConfig(
        strategy_type='trend_following',
        strategy_name=f'Trend_Following_{config_name}',
        symbols=base_params['symbols'],
        start_date=base_params['start_date'],
        end_date=base_params['end_date'],
        initial_capital=base_params['initial_capital'],
        data_interval=base_params['data_interval'],
        strategy_config=strategy_params  # Pass Trend Following-specific params
    )
    
    # Run backtest
    results = await tester.test_strategy(test_config)
    
    # Display results
    if results:
        logger.info(f"\n📊 {config_name} Results:")
        logger.info(f"  Total Return: {results.performance_metrics.total_return_pct:.2f}%")
        logger.info(f"  Sharpe Ratio: {results.performance_metrics.sharpe_ratio:.2f}")
        logger.info(f"  Max Drawdown: {results.performance_metrics.max_drawdown_pct:.2f}%")
        logger.info(f"  Win Rate: {results.trading_stats.win_rate*100:.2f}%")
        logger.info(f"  Total Trades: {results.trading_stats.total_trades}")
        logger.info(f"  Profit Factor: {results.trading_stats.profit_factor:.2f}")
    
    return results


async def main():
    """Run comprehensive Trend Following strategy tests"""
    
    logger.info("="*80)
    logger.info("🚀 Starting Trend Following Strategy Assessment")
    logger.info("="*80)
    
    # Initialize tester
    output_dir = "tests/strategy_assessment/results/trend_following"
    tester = ComprehensiveStrategyTester(output_dir=output_dir)
    
    # Test parameters (SHORT PERIOD for quick testing)
    symbols = ['NVDA', 'TSLA', 'AAPL']
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
    logger.info(f"  Symbols: {', '.join(symbols)}")
    logger.info(f"  Period: {start_date} to {end_date}")
    logger.info(f"  Data Interval: {base_params['data_interval']}")
    logger.info(f"  Initial Capital: ${initial_capital:,.0f}")
    
    results = {}
    
    # Test 1: BASELINE (Moderate parameters)
    baseline_config = {
        'fast_ma_period': 12,           # Standard fast MA
        'slow_ma_period': 26,           # Standard slow MA
        'ma_type': 'EMA',               # Exponential MA
        'adx_threshold': 25.0,          # Standard ADX threshold
        'base_position_pct': 0.04,      # 4% base position
        'enable_trend_filter': True,    # Filter for quality
        'enable_volatility_filter': True,  # Volatility aware
        'min_trend_duration': 5,        # Minimum 5 bars
        'atr_stop_multiplier': 2.0,     # 2x ATR stop
        'profit_target_ratio': 3.0      # 3:1 reward/risk
    }
    results['baseline'] = await test_trend_following_config(
        tester, 'BASELINE', baseline_config, base_params
    )
    
    # Test 2: CONSERVATIVE (Strict filters, fewer signals)
    conservative_config = {
        'fast_ma_period': 12,
        'slow_ma_period': 26,
        'ma_type': 'EMA',
        'adx_threshold': 30.0,          # Higher ADX = stronger trends only
        'base_position_pct': 0.03,      # Smaller positions
        'enable_trend_filter': True,
        'enable_volatility_filter': True,
        'min_trend_duration': 8,        # Longer trends only
        'atr_stop_multiplier': 2.5,     # Wider stops
        'profit_target_ratio': 4.0      # Higher profit targets
    }
    results['conservative'] = await test_trend_following_config(
        tester, 'CONSERVATIVE', conservative_config, base_params
    )
    
    # Test 3: AGGRESSIVE (Relaxed filters, more signals)
    aggressive_config = {
        'fast_ma_period': 8,            # Faster MA = quicker signals
        'slow_ma_period': 20,           # Shorter slow MA
        'ma_type': 'EMA',
        'adx_threshold': 20.0,          # Lower threshold = more signals
        'base_position_pct': 0.05,      # Larger positions
        'enable_trend_filter': False,   # No filters = more trades
        'enable_volatility_filter': False,
        'min_trend_duration': 3,        # Shorter trends OK
        'atr_stop_multiplier': 1.5,     # Tighter stops
        'profit_target_ratio': 2.0      # Lower targets
    }
    results['aggressive'] = await test_trend_following_config(
        tester, 'AGGRESSIVE', aggressive_config, base_params
    )
    
    # Summary comparison
    logger.info(f"\n{'='*80}")
    logger.info("📊 TREND FOLLOWING STRATEGY COMPARISON")
    logger.info(f"{'='*80}\n")
    
    logger.info(f"{'Config':<15} {'Return %':<12} {'Sharpe':<10} {'MaxDD %':<12} {'Trades':<10} {'Win Rate %':<12}")
    logger.info(f"{'-'*80}")
    
    for config_name, result in results.items():
        if result:
            return_pct = result.performance_metrics.total_return_pct
            sharpe = result.performance_metrics.sharpe_ratio
            maxdd = result.performance_metrics.max_drawdown_pct
            trades = result.trading_stats.total_trades
            win_rate = result.trading_stats.win_rate * 100
            
            logger.info(f"{config_name.upper():<15} {return_pct:>10.2f}% {sharpe:>9.2f} {maxdd:>10.2f}% {trades:>9} {win_rate:>10.2f}%")
    
    logger.info(f"\n{'='*80}")
    logger.info("✅ Trend Following Strategy Assessment Complete!")
    logger.info(f"{'='*80}\n")
    
    # Identify best configuration
    best_config = None
    best_sharpe = -999
    
    for config_name, result in results.items():
        if result:
            sharpe = result.performance_metrics.sharpe_ratio
            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_config = config_name
    
    if best_config:
        logger.info(f"🏆 Best Configuration: {best_config.upper()} (Sharpe: {best_sharpe:.2f})")
        
        best_result = results[best_config]
        logger.info(f"\n📈 Best Configuration Details:")
        logger.info(f"  Total Return: {best_result.performance_metrics.total_return_pct:.2f}%")
        logger.info(f"  Sharpe Ratio: {best_result.performance_metrics.sharpe_ratio:.2f}")
        logger.info(f"  Max Drawdown: {best_result.performance_metrics.max_drawdown_pct:.2f}%")
        logger.info(f"  Win Rate: {best_result.trading_stats.win_rate*100:.2f}%")
        logger.info(f"  Total Trades: {best_result.trading_stats.total_trades}")
        logger.info(f"  Profit Factor: {best_result.trading_stats.profit_factor:.2f}")
    
    logger.info(f"\n📁 Results saved to: {output_dir}")


if __name__ == "__main__":
    asyncio.run(main())

