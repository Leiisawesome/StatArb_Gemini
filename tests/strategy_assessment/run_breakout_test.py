#!/usr/bin/env python3
"""
Breakout Strategy Assessment
Test the Enhanced Breakout Strategy on 1-minute data
"""

import asyncio
import logging
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.strategy_assessment.strategy_tester import ComprehensiveStrategyTester
from core_engine.data.manager import ClickHouseDataConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_breakout_config(tester, config_name, strategy_config, base_params):
    """Test a specific Breakout configuration"""
    
    logger.info(f"\n{'='*60}")
    logger.info(f"🧪 Testing {config_name} Configuration")
    logger.info(f"{'='*60}")
    
    # Create test configuration
    from tests.strategy_assessment.strategy_tester import StrategyTestConfig
    
    test_config = StrategyTestConfig(
        strategy_name="Enhanced Breakout",
        strategy_type="breakout",
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
        else:
            logger.info(f"  Result type: {type(result)}")
            logger.info(f"  Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        
        # Grade the result
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
    """Run comprehensive Breakout strategy tests"""
    
    logger.info("="*80)
    logger.info("🚀 Starting Breakout Strategy Assessment")
    logger.info("="*80)
    
    # Initialize tester
    output_dir = "tests/strategy_assessment/results/breakout"
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
    logger.info(f"\n{'='*80}")
    
    results = {}
    
    # Test 1: BASELINE
    baseline_config = {
        'lookback_period': 20,
        'breakout_threshold': 0.02,  # 2% breakout
        'volume_confirmation': 1.5,   # 50% above average volume
        'base_position_pct': 0.04,
        'max_position_pct': 0.10,
        'stop_loss_pct': 0.03,
        'profit_target_ratio': 2.0,
    }
    results['baseline'] = await test_breakout_config(
        tester, 'BASELINE', baseline_config, base_params
    )
    
    # Test 2: CONSERVATIVE
    conservative_config = {
        'lookback_period': 30,
        'breakout_threshold': 0.03,  # 3% breakout (higher threshold)
        'volume_confirmation': 2.0,   # 100% above average volume
        'base_position_pct': 0.02,    # Smaller position
        'max_position_pct': 0.08,
        'stop_loss_pct': 0.04,       # Wider stops
        'profit_target_ratio': 2.0,
    }
    results['conservative'] = await test_breakout_config(
        tester, 'CONSERVATIVE', conservative_config, base_params
    )
    
    # Test 3: AGGRESSIVE
    aggressive_config = {
        'lookback_period': 15,
        'breakout_threshold': 0.015, # 1.5% breakout (lower threshold)
        'volume_confirmation': 1.2,   # 20% above average volume
        'base_position_pct': 0.06,    # Larger position
        'max_position_pct': 0.12,
        'stop_loss_pct': 0.02,       # Tighter stops
        'profit_target_ratio': 2.0,
    }
    results['aggressive'] = await test_breakout_config(
        tester, 'AGGRESSIVE', aggressive_config, base_params
    )
    
    logger.info(f"\n{'='*80}")
    logger.info("📊 BREAKOUT STRATEGY COMPARISON")
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
    logger.info("✅ Breakout Strategy Assessment Complete!")
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
