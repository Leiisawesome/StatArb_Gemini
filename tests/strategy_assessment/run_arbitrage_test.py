#!/usr/bin/env python3
"""
Arbitrage Strategy Testing Script
===============================

Tests the Enhanced Arbitrage Strategy with multiple configurations
to assess viability on 1-minute data.

Author: StatArb_Gemini Strategy Assessment
Date: October 7, 2025
"""

import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.strategy_assessment.strategy_tester import ComprehensiveStrategyTester, StrategyTestConfig
from tests.strategy_assessment.strategy_config_factory import StrategyConfigFactory
from core_engine.data.manager import ClickHouseDataConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_arbitrage_config(tester, config_name, strategy_config, base_params):
    """Test a specific arbitrage configuration"""
    logger.info(f"🧪 Testing {config_name} configuration...")
    
    test_config = StrategyTestConfig(
        strategy_name="Enhanced Arbitrage Strategy",
        strategy_type="arbitrage",
        symbols=base_params['symbols'],
        start_date=base_params['start_date'].strftime('%Y-%m-%d'),
        end_date=base_params['end_date'].strftime('%Y-%m-%d'),
        data_interval=base_params['data_interval'],
        initial_capital=base_params['initial_capital'],
        strategy_config=strategy_config
    )
    
    try:
        result = await tester.test_strategy(test_config)
        
        # Handle result parsing
        if hasattr(result, 'performance_metrics') and result.performance_metrics:
            if isinstance(result.performance_metrics, dict):
                total_return = result.performance_metrics.get('total_return_pct', 0.0)
                sharpe_ratio = result.performance_metrics.get('sharpe_ratio', 0.0)
                max_drawdown = result.performance_metrics.get('max_drawdown_pct', 0.0)
                total_trades = result.performance_metrics.get('total_trades', 0)
                win_rate = result.performance_metrics.get('win_rate', 0.0) * 100
                profit_factor = result.performance_metrics.get('profit_factor', 0.0)
            else:
                total_return = getattr(result.performance_metrics, 'total_return_pct', 0.0)
                sharpe_ratio = getattr(result.performance_metrics, 'sharpe_ratio', 0.0)
                max_drawdown = getattr(result.performance_metrics, 'max_drawdown_pct', 0.0)
                total_trades = getattr(result.performance_metrics, 'total_trades', 0)
                win_rate = getattr(result.performance_metrics, 'win_rate', 0.0) * 100
                profit_factor = getattr(result.performance_metrics, 'profit_factor', 0.0)
        else:
            total_return = 0.0
            sharpe_ratio = 0.0
            max_drawdown = 0.0
            total_trades = 0
            win_rate = 0.0
            profit_factor = 0.0
        
        logger.info(f"✅ {config_name} backtest completed")
        logger.info(f"📊 Results:")
        logger.info(f"  Result type: {type(result)}")
        logger.info(f"  Result keys: {'Not a dict' if not isinstance(result, dict) else 'Dict'}")
        logger.info(f"  Grade: {getattr(result, 'overall_grade', 'N/A')}")
        logger.info(f"  Total Return: {total_return:.2f}%")
        logger.info(f"  Sharpe Ratio: {sharpe_ratio:.2f}")
        logger.info(f"  Max Drawdown: {max_drawdown:.2f}%")
        logger.info(f"  Total Trades: {total_trades}")
        logger.info(f"  Win Rate: {win_rate:.1f}%")
        logger.info(f"  Profit Factor: {profit_factor:.2f}")
        
        return {
            'config_name': config_name,
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'result': result
        }
        
    except Exception as e:
        logger.error(f"❌ {config_name} test failed: {e}")
        return {
            'config_name': config_name,
            'total_return': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'total_trades': 0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'result': None,
            'error': str(e)
        }

async def main():
    """Main testing function"""
    logger.info("🚀 Starting Arbitrage Strategy Assessment")
    logger.info("=" * 80)
    
    # Test parameters
    base_params = {
        'symbols': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA'],
        'start_date': datetime(2024, 1, 2),
        'end_date': datetime(2024, 1, 5),
        'data_interval': '1min',
        'initial_capital': 100000.0
    }
    
    # Initialize tester
    tester = ComprehensiveStrategyTester(output_dir="tests/strategy_assessment/results/arbitrage")
    
    # Initialize data manager
    data_config = ClickHouseDataConfig(
        symbols=base_params['symbols'],
        start_date=base_params['start_date'].strftime('%Y-%m-%d'),
        end_date=base_params['end_date'].strftime('%Y-%m-%d'),
        enable_caching=True
    )
    
    await tester.initialize_components(data_config)
    
    # Define test configurations
    baseline_config = {
        'min_spread': 0.001,
        'max_execution_time': 5.0,
        'confidence_threshold': 0.8,
        'base_position_size': 0.05,
        'transaction_cost_threshold': 0.0005,
        'opportunity_timeout': 10.0,
        'price_update_frequency': 1.0
    }
    
    conservative_config = {
        'min_spread': 0.002,  # Higher threshold
        'max_execution_time': 3.0,  # Faster execution
        'confidence_threshold': 0.9,  # Higher confidence
        'base_position_size': 0.03,  # Smaller positions
        'transaction_cost_threshold': 0.0003,  # Lower cost threshold
        'opportunity_timeout': 5.0,  # Shorter timeout
        'price_update_frequency': 0.5  # More frequent updates
    }
    
    aggressive_config = {
        'min_spread': 0.0005,  # Lower threshold
        'max_execution_time': 10.0,  # Longer execution time
        'confidence_threshold': 0.7,  # Lower confidence
        'base_position_size': 0.08,  # Larger positions
        'transaction_cost_threshold': 0.001,  # Higher cost threshold
        'opportunity_timeout': 15.0,  # Longer timeout
        'price_update_frequency': 2.0  # Less frequent updates
    }
    
    # Test configurations
    configs = [
        ('BASELINE', baseline_config),
        ('CONSERVATIVE', conservative_config),
        ('AGGRESSIVE', aggressive_config)
    ]
    
    results = {}
    
    for config_name, config_params in configs:
        # Create strategy config
        strategy_config = StrategyConfigFactory.create_arbitrage_config(
            symbols=base_params['symbols'],
            **config_params
        )
        
        # Test configuration
        result = await test_arbitrage_config(tester, config_name, strategy_config, base_params)
        results[config_name] = result
    
    # Display comparison table
    logger.info(f"\n{'='*80}")
    logger.info("📊 ARBITRAGE STRATEGY COMPARISON")
    logger.info(f"{'='*80}")
    logger.info(f"{'Config':<12} {'Return %':<10} {'Sharpe':<8} {'MaxDD %':<8} {'Trades':<8} {'Win Rate %':<10}")
    logger.info("-" * 80)
    
    for config_name, result in results.items():
        logger.info(f"{config_name:<12} {result['total_return']:>8.2f}% {result['sharpe_ratio']:>7.2f} "
                   f"{result['max_drawdown']:>7.2f}% {result['total_trades']:>7} {result['win_rate']:>9.1f}%")
    
    logger.info(f"\n{'='*80}")
    logger.info("✅ Arbitrage Strategy Assessment Complete!")
    logger.info(f"{'='*80}")
    
    # Find best configuration
    best_config = None
    best_sharpe = -float('inf')
    
    for config_name, result in results.items():
        if result['result'] is not None:
            sharpe = result['sharpe_ratio']
            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_config = config_name
    
    if best_config:
        logger.info(f"🏆 Best Configuration: {best_config.upper()} (Sharpe: {best_sharpe:.2f})")
        
        best_result = results[best_config]
        logger.info(f"\n📈 Best Configuration Details:")
        if hasattr(best_result['result'], 'performance_metrics') and best_result['result'].performance_metrics:
            # Handle nested dictionary structure - performance_metrics contains all metrics
            if isinstance(best_result['result'].performance_metrics, dict):
                total_return = best_result['result'].performance_metrics.get('total_return_pct', 0.0)
                sharpe_ratio = best_result['result'].performance_metrics.get('sharpe_ratio', 0.0)
                max_drawdown = best_result['result'].performance_metrics.get('max_drawdown_pct', 0.0)
                win_rate = best_result['result'].performance_metrics.get('win_rate', 0.0) * 100
                total_trades = best_result['result'].performance_metrics.get('total_trades', 0)
                profit_factor = best_result['result'].performance_metrics.get('profit_factor', 0.0)
            else:
                total_return = getattr(best_result['result'].performance_metrics, 'total_return_pct', 0.0)
                sharpe_ratio = getattr(best_result['result'].performance_metrics, 'sharpe_ratio', 0.0)
                max_drawdown = getattr(best_result['result'].performance_metrics, 'max_drawdown_pct', 0.0)
                win_rate = getattr(best_result['result'].performance_metrics, 'win_rate', 0.0) * 100
                total_trades = getattr(best_result['result'].performance_metrics, 'total_trades', 0)
                profit_factor = getattr(best_result['result'].performance_metrics, 'profit_factor', 0.0)
            
            logger.info(f"  Total Return: {total_return:.2f}%")
            logger.info(f"  Sharpe Ratio: {sharpe_ratio:.2f}")
            logger.info(f"  Max Drawdown: {max_drawdown:.2f}%")
            logger.info(f"  Win Rate: {win_rate:.2f}%")
            logger.info(f"  Total Trades: {total_trades}")
            logger.info(f"  Profit Factor: {profit_factor:.2f}")
        elif isinstance(best_result['result'], dict):
            logger.info(f"  Total Return: {best_result['result'].get('total_return_pct', 0.0):.2f}%")
            logger.info(f"  Sharpe Ratio: {best_result['result'].get('sharpe_ratio', 0.0):.2f}")
            logger.info(f"  Max Drawdown: {best_result['result'].get('max_drawdown_pct', 0.0):.2f}%")
            logger.info(f"  Win Rate: {best_result['result'].get('win_rate', 0.0)*100:.2f}%")
            logger.info(f"  Total Trades: {best_result['result'].get('total_trades', 0)}")
            logger.info(f"  Profit Factor: {best_result['result'].get('profit_factor', 0.0):.2f}")
        else:
            logger.info("  No performance data available")
    else:
        logger.info("⚠️ No viable configuration found (0 trades or negative Sharpe for all).")
    
    logger.info(f"\n📁 Results saved to: {tester.output_dir}")

if __name__ == "__main__":
    asyncio.run(main())
