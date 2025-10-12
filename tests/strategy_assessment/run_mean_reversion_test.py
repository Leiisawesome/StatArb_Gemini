#!/usr/bin/env python3
"""
Phase 5: Mean Reversion Strategy Testing
=========================================

Test Mean Reversion strategy using the established testing framework.

Author: StatArb_Gemini Phase 5
Date: October 6, 2025
"""

import logging
import asyncio
import sys
import os

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '../../')
sys.path.insert(0, project_root)

# Import testing framework (THE RIGHT WAY)
from tests.strategy_assessment.strategy_tester import ComprehensiveStrategyTester, StrategyTestConfig
from core_engine.data.manager import ClickHouseDataConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


async def test_mean_reversion_config(tester, config_name, config_params, base_params):
    """Test a single Mean Reversion configuration"""
    
    logger.info(f"\n{'='*80}")
    logger.info(f"Testing {config_name} Configuration")
    logger.info(f"{'='*80}")
    
    # Merge base params with specific config
    strategy_config = {**base_params, **config_params}
    
    # Create test config using framework structure
    test_config = StrategyTestConfig(
        strategy_type='mean_reversion',
        strategy_name=f'Mean Reversion {config_name}',
        strategy_config=strategy_config,
        symbols=base_params['symbols'],
        start_date=base_params['start_date'],
        end_date=base_params['end_date'],
        initial_capital=base_params['initial_capital'],
        data_interval='1min'  # Phase 5: Testing on 1-min data
    )
    
    # Run test using framework
    result = await tester.test_strategy(test_config)
    
    if result:
        metrics = result.performance_metrics
        logger.info(f"\n{config_name} Results:")
        logger.info(f"  Total Trades: {metrics.get('total_trades', 0)} ({metrics.get('total_trades', 0)/30:.1f}/day)")
        logger.info(f"  Total Return: {metrics.get('total_return', 0)*100:.2f}%")
        logger.info(f"  Win Rate: {metrics.get('win_rate', 0)*100:.2f}%")
        logger.info(f"  Profit Factor: {metrics.get('profit_factor', 0):.2f}")
        logger.info(f"  Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
        logger.info(f"  Max Drawdown: {metrics.get('max_drawdown', 0)*100:.2f}%")
        logger.info(f"  Total Costs: ${metrics.get('total_cost', 0):.2f}")
    
    return result


async def main():
    """Main test runner"""
    
    logger.info("\n" + "🚀"*40)
    logger.info("PHASE 5: MEAN REVERSION STRATEGY OPTIMIZATION")
    logger.info("🚀"*40 + "\n")
    
    # Test parameters (SHORT PERIOD for quick testing)
    symbols = ['NVDA', 'TSLA', 'AAPL']
    start_date = "2024-01-02"
    end_date = "2024-01-05"  # Just 3 trading days for FAST testing
    initial_capital = 100000.0
    
    logger.info(f"Test Configuration:")
    logger.info(f"  Symbols: {', '.join(symbols)}")
    logger.info(f"  Period: {start_date} to {end_date}")
    logger.info(f"  Data: 1-minute bars")
    logger.info(f"  Initial Capital: ${initial_capital:,.0f}\n")
    
    try:
        # Step 1: Initialize tester (USING FRAMEWORK)
        logger.info("Initializing testing framework...")
        tester = ComprehensiveStrategyTester(
            output_dir="tests/strategy_assessment/results/mean_reversion"
        )
        
        # Step 2: Configure data manager (USING FRAMEWORK)
        logger.info("Configuring data manager...")
        data_config = ClickHouseDataConfig(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            interval='1min',
            clickhouse_host='localhost',
            clickhouse_port=8123,
            clickhouse_database='polygon_data',
            enable_caching=True
        )
        
        # Step 3: Initialize components (USING FRAMEWORK)
        logger.info("Initializing core engine components...")
        initialized = await tester.initialize_components(data_config)
        
        if not initialized:
            logger.error("❌ Failed to initialize components!")
            return False
        
        logger.info("✅ Framework initialized successfully\n")
        
        # Base parameters for all tests
        base_params = {
            'symbols': symbols,
            'start_date': start_date,
            'end_date': end_date,
            'initial_capital': initial_capital,
            'max_position_size': 0.10,
            'paper_trading_mode': True
        }
        
        results = {}
        
        # Test 1: BASELINE (with REGIME FILTER ENABLED)
        baseline_config = {
            'lookback_period': 20,
            'zscore_entry_threshold': 1.5,  # RELAXED for more signals
            'zscore_exit_threshold': 0.5,
            'rsi_oversold': 40.0,  # RELAXED
            'rsi_overbought': 60.0,  # RELAXED
            'bollinger_std': 2.0,
            'base_position_pct': 0.03,
            'enable_regime_filter': True  # ENABLE to filter bad trades
        }
        results['baseline'] = await test_mean_reversion_config(
            tester, 'BASELINE', baseline_config, base_params
        )
        
        # Test 2: CONSERVATIVE (with REGIME FILTER ENABLED)
        conservative_config = {
            'lookback_period': 20,
            'zscore_entry_threshold': 2.5,  # WIDER
            'zscore_exit_threshold': 0.5,
            'rsi_oversold': 25.0,  # STRICTER
            'rsi_overbought': 75.0,
            'bollinger_std': 2.5,  # WIDER
            'base_position_pct': 0.03,
            'enable_regime_filter': True  # ENABLE to filter bad trades
        }
        results['conservative'] = await test_mean_reversion_config(
            tester, 'CONSERVATIVE', conservative_config, base_params
        )
        
        # Test 3: AGGRESSIVE (with REGIME FILTER ENABLED)
        aggressive_config = {
            'lookback_period': 20,
            'zscore_entry_threshold': 1.5,  # TIGHTER
            'zscore_exit_threshold': 0.5,
            'rsi_oversold': 35.0,  # RELAXED
            'rsi_overbought': 65.0,
            'bollinger_std': 1.5,  # TIGHTER
            'base_position_pct': 0.03,
            'enable_regime_filter': True  # ENABLE to filter bad trades
        }
        results['aggressive'] = await test_mean_reversion_config(
            tester, 'AGGRESSIVE', aggressive_config, base_params
        )
        
        # Summary
        logger.info("\n" + "="*80)
        logger.info("COMPARISON SUMMARY")
        logger.info("="*80)
        logger.info(f"\n{'Config':<15} | {'Trades/Day':<12} | {'Return %':<10} | {'Win Rate %':<12} | {'Sharpe':<8}")
        logger.info("-"*80)
        
        for name, result in results.items():
            if result:
                m = result.performance_metrics
                trades_per_day = m.get('total_trades', 0) / 30
                total_return = m.get('total_return', 0) * 100
                win_rate = m.get('win_rate', 0) * 100
                sharpe = m.get('sharpe_ratio', 0)
                
                logger.info(f"{name.upper():<15} | {trades_per_day:>11.1f} | {total_return:>9.2f} | {win_rate:>11.2f} | {sharpe:>7.2f}")
        
        logger.info("\n" + "="*80)
        logger.info("✅ Phase 5 Mean Reversion testing complete!\n")
        
        return True
        
    except Exception as e:
        logger.error(f"\n❌ Test failed with error: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
