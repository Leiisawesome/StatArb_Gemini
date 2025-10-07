#!/usr/bin/env python3
"""
Multi-Asset Strategy Assessment
Test the Enhanced Multi-Asset Strategy on 1-minute data
"""

import asyncio
import logging
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.strategy_assessment.strategy_tester import ComprehensiveStrategyTester
from tests.strategy_assessment.strategy_config_factory import StrategyConfigFactory
from core_engine.data.manager import ClickHouseDataConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_multi_asset_config(tester, config_name, strategy_config, base_params):
    """Test a specific Multi-Asset configuration"""
    
    logger.info(f"\n{'='*60}")
    logger.info(f"🧪 Testing {config_name} Configuration")
    logger.info(f"{'='*60}")
    
    # Create test configuration
    from tests.strategy_assessment.strategy_tester import StrategyTestConfig
    
    test_config = StrategyTestConfig(
        strategy_name="Enhanced Multi-Asset Strategy",
        strategy_type="multi_asset",
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
        if hasattr(result, 'performance_metrics') and result.performance_metrics:
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
    """Run comprehensive Multi-Asset strategy tests"""
    
    logger.info("="*80)
    logger.info("🚀 Starting Multi-Asset Strategy Assessment")
    logger.info("="*80)
    
    # Initialize tester
    output_dir = "tests/strategy_assessment/results/multi_asset"
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
    logger.info(f"\n{'='*80}")
    
    results = {}
    
    # Test 1: BASELINE - Cross-asset correlation strategy
    baseline_config = {
        'rebalance_frequency': 5,          # Rebalance every 5 periods
        'correlation_lookback': 60,        # 60 periods for correlation calculation
        'max_correlation': 0.6,            # Maximum correlation threshold
        'portfolio_vol_target': 0.10,      # 10% target portfolio volatility
        'max_asset_weight': 0.25,           # 25% maximum weight per asset
        'min_asset_weight': 0.05,           # 5% minimum weight per asset
    }
    results['baseline'] = await test_multi_asset_config(
        tester, 'BASELINE', baseline_config, base_params
    )
    
    # Test 2: CONSERVATIVE - Higher thresholds, lower risk
    conservative_config = {
        'rebalance_frequency': 10,         # Less frequent rebalancing
        'correlation_lookback': 80,        # Longer lookback for stability
        'max_correlation': 0.7,            # Higher correlation threshold
        'portfolio_vol_target': 0.08,      # 8% target portfolio volatility
        'max_asset_weight': 0.20,           # 20% maximum weight per asset
        'min_asset_weight': 0.10,           # 10% minimum weight per asset
    }
    results['conservative'] = await test_multi_asset_config(
        tester, 'CONSERVATIVE', conservative_config, base_params
    )
    
    # Test 3: AGGRESSIVE - Lower thresholds, more signals
    aggressive_config = {
        'rebalance_frequency': 3,          # More frequent rebalancing
        'correlation_lookback': 40,         # Shorter lookback for responsiveness
        'max_correlation': 0.5,            # Lower correlation threshold
        'portfolio_vol_target': 0.15,      # 15% target portfolio volatility
        'max_asset_weight': 0.35,           # 35% maximum weight per asset
        'min_asset_weight': 0.03,           # 3% minimum weight per asset
    }
    results['aggressive'] = await test_multi_asset_config(
        tester, 'AGGRESSIVE', aggressive_config, base_params
    )
    
    logger.info(f"\n{'='*80}")
    logger.info("📊 MULTI-ASSET STRATEGY COMPARISON")
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
    logger.info("✅ Multi-Asset Strategy Assessment Complete!")
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
    else:
        logger.info("⚠️ No viable configuration found (0 trades or negative Sharpe for all).")
    
    logger.info(f"\n📁 Results saved to: {output_dir}")

if __name__ == "__main__":
    asyncio.run(main())
