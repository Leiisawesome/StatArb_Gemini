#!/usr/bin/env python3
"""
Volatility Strategy Assessment
Test the Enhanced Volatility Strategy on 1-minute data
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

async def test_volatility_config(tester, config_name, strategy_config, base_params):
    """Test a specific Volatility configuration"""
    
    logger.info(f"\n{'='*60}")
    logger.info(f"🧪 Testing {config_name} Configuration")
    logger.info(f"{'='*60}")
    
    # Create test configuration
    from tests.strategy_assessment.strategy_tester import StrategyTestConfig
    
    test_config = StrategyTestConfig(
        strategy_name="Enhanced Volatility Strategy",
        strategy_type="volatility",
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
        if isinstance(result, dict):
            logger.info(f"  Total Return: {result.get('total_return_pct', 0.0):.2f}%")
            logger.info(f"  Sharpe Ratio: {result.get('sharpe_ratio', 0.0):.2f}")
            logger.info(f"  Max Drawdown: {result.get('max_drawdown_pct', 0.0):.2f}%")
            logger.info(f"  Total Trades: {result.get('total_trades', 0)}")
            logger.info(f"  Win Rate: {result.get('win_rate', 0.0)*100:.2f}%")
            logger.info(f"  Profit Factor: {result.get('profit_factor', 0.0):.2f}")
        else:
            logger.info(f"  Result type: {type(result)}")
            logger.info(f"  Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        
        # Parse results - handle both dict and StrategyTestResult types
        if isinstance(result, dict):
            # Handle dict results
            total_return = result.get('total_return_pct', 0.0)
            sharpe_ratio = result.get('sharpe_ratio', 0.0)
            max_drawdown = result.get('max_drawdown_pct', 0.0)
            win_rate = result.get('win_rate_pct', 0.0)
            profit_factor = result.get('profit_factor', 0.0)
            total_trades = result.get('total_trades', 0)
        elif hasattr(result, 'performance_metrics') and result.performance_metrics:
            # Handle StrategyTestResult with performance_metrics (could be dict or object)
            if isinstance(result.performance_metrics, dict):
                total_return = result.performance_metrics.get('total_return_pct', 0.0)
                sharpe_ratio = result.performance_metrics.get('sharpe_ratio', 0.0)
                max_drawdown = result.performance_metrics.get('max_drawdown_pct', 0.0)
                win_rate = result.performance_metrics.get('win_rate_pct', 0.0)
                profit_factor = result.performance_metrics.get('profit_factor', 0.0)
                total_trades = result.performance_metrics.get('total_trades', 0)
            else:
                total_return = result.performance_metrics.total_return_pct
                sharpe_ratio = result.performance_metrics.sharpe_ratio
                max_drawdown = result.performance_metrics.max_drawdown_pct
                win_rate = result.performance_metrics.win_rate_pct
                profit_factor = result.performance_metrics.profit_factor
                total_trades = result.performance_metrics.total_trades
        elif hasattr(result, 'trading_stats') and result.trading_stats:
            # Handle StrategyTestResult with trading_stats (could be dict or object)
            if isinstance(result.trading_stats, dict):
                total_return = result.trading_stats.get('total_return_pct', 0.0)
                sharpe_ratio = result.trading_stats.get('sharpe_ratio', 0.0)
                max_drawdown = result.trading_stats.get('max_drawdown_pct', 0.0)
                win_rate = result.trading_stats.get('win_rate_pct', 0.0)
                profit_factor = result.trading_stats.get('profit_factor', 0.0)
                total_trades = result.trading_stats.get('total_trades', 0)
            else:
                total_return = result.trading_stats.total_return_pct
                sharpe_ratio = result.trading_stats.sharpe_ratio
                max_drawdown = result.trading_stats.max_drawdown_pct
                win_rate = result.trading_stats.win_rate_pct
                profit_factor = result.trading_stats.profit_factor
                total_trades = result.trading_stats.total_trades
        else:
            # Fallback for unknown types
            total_return = 0.0
            sharpe_ratio = 0.0
            max_drawdown = 0.0
            win_rate = 0.0
            profit_factor = 0.0
            total_trades = 0
        
        # Grade the result
        if sharpe_ratio > 1.0:
            grade = "A"
        elif sharpe_ratio > 0.5:
            grade = "B"
        elif sharpe_ratio > 0.0:
            grade = "C"
        else:
            grade = "F"
        
        logger.info(f"  Grade: {grade}")
        return result
    else:
        logger.error(f"❌ {config_name} backtest failed")
        return None

async def main():
    """Run comprehensive Volatility strategy tests"""
    
    logger.info("="*80)
    logger.info("🚀 Starting Volatility Strategy Assessment")
    logger.info("="*80)
    
    # Initialize tester
    output_dir = "tests/strategy_assessment/results/volatility"
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
    
    # Test 1: BASELINE - Volatility trading strategy
    baseline_config = {
        'volatility_lookback': 60,        # 60 periods for volatility calculation
        'volatility_threshold': 0.02,      # 2% volatility threshold
        'regime_detection': True,          # Enable volatility regime detection
        'base_position_pct': 0.03,         # 3% base position size
        'max_position_pct': 0.08,          # 8% maximum position size
        'volatility_scaling': True,        # Scale positions by volatility
    }
    results['baseline'] = await test_volatility_config(
        tester, 'BASELINE', baseline_config, base_params
    )
    
    # Test 2: CONSERVATIVE - Higher thresholds, lower risk
    conservative_config = {
        'volatility_lookback': 80,         # Longer lookback for stability
        'volatility_threshold': 0.025,     # Higher volatility threshold
        'regime_detection': True,          # Enable volatility regime detection
        'base_position_pct': 0.02,         # 2% base position size
        'max_position_pct': 0.06,          # 6% maximum position size
        'volatility_scaling': True,        # Scale positions by volatility
    }
    results['conservative'] = await test_volatility_config(
        tester, 'CONSERVATIVE', conservative_config, base_params
    )
    
    # Test 3: AGGRESSIVE - Lower thresholds, more signals
    aggressive_config = {
        'volatility_lookback': 40,         # Shorter lookback for responsiveness
        'volatility_threshold': 0.015,     # Lower volatility threshold
        'regime_detection': True,          # Enable volatility regime detection
        'base_position_pct': 0.04,         # 4% base position size
        'max_position_pct': 0.10,          # 10% maximum position size
        'volatility_scaling': True,        # Scale positions by volatility
    }
    results['aggressive'] = await test_volatility_config(
        tester, 'AGGRESSIVE', aggressive_config, base_params
    )
    
    logger.info(f"\n{'='*80}")
    logger.info("📊 VOLATILITY STRATEGY COMPARISON")
    logger.info(f"{'='*80}\n")
    
    logger.info(f"{'Config':<15} {'Return %':<12} {'Sharpe':<10} {'MaxDD %':<12} {'Trades':<10} {'Win Rate %':<12}")
    logger.info(f"{'-'*80}")
    
    for config_name, result in results.items():
        if result:
            if hasattr(result, 'performance_metrics') and result.performance_metrics:
                # Handle StrategyTestResult with performance_metrics (could be dict or object)
                if isinstance(result.performance_metrics, dict):
                    return_pct = result.performance_metrics.get('total_return_pct', 0.0)
                    sharpe = result.performance_metrics.get('sharpe_ratio', 0.0)
                    maxdd = result.performance_metrics.get('max_drawdown_pct', 0.0)
                else:
                    return_pct = result.performance_metrics.total_return_pct
                    sharpe = result.performance_metrics.sharpe_ratio
                    maxdd = result.performance_metrics.max_drawdown_pct
                
                # Handle trading_stats (could be dict or object)
                if hasattr(result, 'trading_stats') and result.trading_stats:
                    if isinstance(result.trading_stats, dict):
                        trades = result.trading_stats.get('total_trades', 0)
                        win_rate = result.trading_stats.get('win_rate', 0.0) * 100
                    else:
                        trades = result.trading_stats.total_trades
                        win_rate = result.trading_stats.win_rate * 100
                else:
                    trades = 0
                    win_rate = 0.0
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
    logger.info("✅ Volatility Strategy Assessment Complete!")
    logger.info(f"{'='*80}\n")
    
    # Identify best configuration
    best_config = None
    best_sharpe = -999
    
    for config_name, result in results.items():
        if result:
            if hasattr(result, 'performance_metrics') and result.performance_metrics:
                # Handle StrategyTestResult with performance_metrics (could be dict or object)
                if isinstance(result.performance_metrics, dict):
                    sharpe = result.performance_metrics.get('sharpe_ratio', 0.0)
                else:
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
        if hasattr(best_result, 'performance_metrics') and best_result.performance_metrics:
            # Handle nested dictionary structure - performance_metrics contains all metrics
            if isinstance(best_result.performance_metrics, dict):
                total_return = best_result.performance_metrics.get('total_return_pct', 0.0)
                sharpe_ratio = best_result.performance_metrics.get('sharpe_ratio', 0.0)
                max_drawdown = best_result.performance_metrics.get('max_drawdown_pct', 0.0)
                win_rate = best_result.performance_metrics.get('win_rate', 0.0) * 100
                total_trades = best_result.performance_metrics.get('total_trades', 0)
                profit_factor = best_result.performance_metrics.get('profit_factor', 0.0)
            else:
                total_return = getattr(best_result.performance_metrics, 'total_return_pct', 0.0)
                sharpe_ratio = getattr(best_result.performance_metrics, 'sharpe_ratio', 0.0)
                max_drawdown = getattr(best_result.performance_metrics, 'max_drawdown_pct', 0.0)
                win_rate = getattr(best_result.performance_metrics, 'win_rate', 0.0) * 100
                total_trades = getattr(best_result.performance_metrics, 'total_trades', 0)
                profit_factor = getattr(best_result.performance_metrics, 'profit_factor', 0.0)
            
            logger.info(f"  Total Return: {total_return:.2f}%")
            logger.info(f"  Sharpe Ratio: {sharpe_ratio:.2f}")
            logger.info(f"  Max Drawdown: {max_drawdown:.2f}%")
            logger.info(f"  Win Rate: {win_rate:.2f}%")
            logger.info(f"  Total Trades: {total_trades}")
            logger.info(f"  Profit Factor: {profit_factor:.2f}")
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
