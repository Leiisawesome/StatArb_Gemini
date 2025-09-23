"""
Institutional Backtest Engine Demonstration
==========================================

This script demonstrates the enhanced institutional-grade backtest engine
with the complete 13-phase workflow implementation.

Features demonstrated:
- System orchestration and component registration
- CentralRiskManager authorization flow
- Regime-aware backtesting
- Multi-strategy support
- Advanced performance attribution
- Institutional-grade reporting

Usage:
    python examples/institutional_backtest_demo.py

Author: StatArb_Gemini Professional Quant Team
Version: 1.0.0 (Demo Implementation)
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core_engine.trading.strategies import (
    InstitutionalBacktestEngine, InstitutionalBacktestConfig
)
from core_engine.trading.strategies.implementations.momentum.advanced_momentum import (
    AdvancedMomentumStrategy, MomentumConfig
)
from core_engine.trading.strategies.strategy_engine import StrategyType
from datetime import datetime
import pandas as pd
import numpy as np


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('institutional_backtest_demo.log')
        ]
    )


def create_sample_market_data(symbols, start_date, end_date):
    """Create sample market data for demonstration"""
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    np.random.seed(42)  # For reproducible results
    
    market_data = {}
    
    for i, symbol in enumerate(symbols):
        # Create realistic price movements with different characteristics per symbol
        n_periods = len(dates)
        base_price = 100 + i * 50  # Different starting prices
        
        # Generate returns with different volatilities and trends
        if symbol == 'AAPL':
            returns = np.random.normal(0.0008, 0.018, n_periods)  # Tech stock
        elif symbol == 'MSFT':
            returns = np.random.normal(0.0006, 0.016, n_periods)  # Stable tech
        elif symbol == 'TSLA':
            returns = np.random.normal(0.0010, 0.035, n_periods)  # High volatility
        elif symbol == 'NVDA':
            returns = np.random.normal(0.0012, 0.028, n_periods)  # AI boom
        else:  # GOOGL
            returns = np.random.normal(0.0007, 0.020, n_periods)  # Search giant
        
        # Generate price series
        prices = [base_price]
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        # Create OHLCV data
        market_data[symbol] = pd.DataFrame({
            'open': [p * (1 + np.random.normal(0, 0.002)) for p in prices],
            'high': [p * (1 + abs(np.random.normal(0.003, 0.005))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0.003, 0.005))) for p in prices],
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, n_periods)
        }, index=dates)
    
    return market_data


def create_sample_benchmark_data(start_date, end_date):
    """Create sample benchmark data (SPY)"""
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    np.random.seed(123)  # Different seed for benchmark
    
    n_periods = len(dates)
    base_price = 400  # SPY starting price
    
    # Market returns (lower volatility than individual stocks)
    returns = np.random.normal(0.0005, 0.012, n_periods)
    
    prices = [base_price]
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    benchmark_data = pd.DataFrame({
        'open': [p * (1 + np.random.normal(0, 0.001)) for p in prices],
        'high': [p * (1 + abs(np.random.normal(0.002, 0.003))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0.002, 0.003))) for p in prices],
        'close': prices,
        'volume': np.random.randint(50000000, 200000000, n_periods)
    }, index=dates)
    
    return {'SPY': benchmark_data}


async def demonstrate_institutional_backtest():
    """Demonstrate the institutional backtest engine capabilities"""
    
    logger = logging.getLogger(__name__)
    logger.info("🚀 Starting Institutional Backtest Engine Demonstration")
    
    try:
        # Step 1: Create market data
        logger.info("📊 Creating sample market data...")
        market_data = create_sample_market_data(
            symbols=["AAPL", "MSFT", "TSLA", "NVDA", "GOOGL"],
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31)
        )
        
        benchmark_data = create_sample_benchmark_data(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31)
        )
        
        logger.info(f"✅ Created data for {len(market_data)} symbols with {len(market_data['AAPL'])} periods each")
        
        # Step 2: Configure institutional backtest
        logger.info("⚙️ Configuring institutional backtest engine...")
        config = InstitutionalBacktestConfig(
            # Basic backtest settings
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            initial_capital=5000000.0,  # $5M institutional capital
            benchmark_symbol="SPY",
            
            # Institutional features
            enable_system_orchestration=True,
            enable_risk_authorization=True,
            enable_regime_awareness=True,
            enable_multi_strategy=False,  # Single strategy for this demo
            
            # Transaction costs (institutional rates)
            commission_rate=0.0005,  # 5 bps
            slippage_rate=0.0003,    # 3 bps
            
            # Advanced analytics
            enable_regime_attribution=True,
            enable_factor_attribution=True,
            enable_risk_attribution=True,
            enable_transaction_cost_analysis=True,
            enable_market_impact_modeling=True,
            
            # Reporting
            generate_institutional_report=True,
            save_detailed_logs=True,
            output_directory="institutional_backtest_results"
        )
        
        logger.info("✅ Institutional configuration created")
        
        # Step 3: Create advanced momentum strategy
        logger.info("🎯 Creating advanced momentum strategy...")
        momentum_config = MomentumConfig(
            strategy_id="institutional_momentum",
            strategy_type=StrategyType.MOMENTUM,
            
            # Momentum parameters
            lookback_periods=[1, 3, 6, 12],  # 1, 3, 6, 12 months
            skip_period=1,  # Skip most recent month
            signal_threshold=0.15,  # Higher threshold for institutional grade
            
            # Risk management
            max_position_size=0.08,  # 8% max position
            volatility_target=0.12,  # 12% vol target
            max_drawdown_limit=0.15,  # 15% max drawdown
            
            # Advanced features
            use_volatility_scaling=True,
            use_risk_parity=True,
            use_adaptive_lookback=True,
            enable_stop_loss=True,
            enable_take_profit=True,
            
            # Stop loss and take profit
            stop_loss_pct=0.08,      # 8% stop loss
            take_profit_pct=0.20,    # 20% take profit
            trailing_stop_pct=0.05,  # 5% trailing stop
            
            # Performance monitoring
            enable_monitoring=True
        )
        
        momentum_strategy = AdvancedMomentumStrategy(momentum_config)
        logger.info("✅ Advanced momentum strategy created")
        
        # Step 4: Initialize institutional backtest engine
        logger.info("🏗️ Initializing institutional backtest engine...")
        backtest_engine = InstitutionalBacktestEngine(config)
        logger.info("✅ Institutional backtest engine initialized successfully")
        
        # Step 5: Run institutional backtest with 13-phase workflow
        logger.info("🚀 Running institutional backtest with 13-phase workflow...")
        logger.info("This will execute all phases:")
        logger.info("  Phase 1: System Initialization & Configuration")
        logger.info("  Phase 2: Data Loading & Market Preparation")
        logger.info("  Phase 3: Regime Analysis & Market Context")
        logger.info("  Phases 4-12: Main Trading Loop")
        logger.info("  Phase 13: Backtest Completion & Final Reporting")
        
        result = await backtest_engine.run_institutional_backtest(
            strategy=momentum_strategy,
            market_data=market_data
        )
        
        logger.info("✅ Institutional backtest completed successfully!")
        
        # Step 6: Display comprehensive results
        logger.info("\n" + "="*80)
        logger.info("📈 INSTITUTIONAL BACKTEST RESULTS")
        logger.info("="*80)
        
        if result:
            # Basic performance metrics
            logger.info(f"💰 Initial Capital: ${config.initial_capital:,.0f}")
            logger.info(f"📊 Total Return: {getattr(result, 'total_return', 0):.2%}")
            logger.info(f"📊 Annualized Return: {getattr(result, 'annualized_return', 0):.2%}")
            logger.info(f"📊 Volatility: {getattr(result, 'volatility', 0):.2%}")
            logger.info(f"📊 Sharpe Ratio: {getattr(result, 'sharpe_ratio', 0):.3f}")
            logger.info(f"📊 Max Drawdown: {getattr(result, 'max_drawdown', 0):.2%}")
            
            # Trading statistics
            logger.info(f"\n📋 TRADING STATISTICS")
            logger.info(f"🔢 Total Trades: {getattr(result, 'total_trades', 0)}")
            logger.info(f"✅ Winning Trades: {getattr(result, 'winning_trades', 0)}")
            logger.info(f"❌ Losing Trades: {getattr(result, 'losing_trades', 0)}")
            logger.info(f"🎯 Win Rate: {getattr(result, 'win_rate', 0):.2%}")
            
            # Phase execution summary
            logger.info(f"\n🔄 PHASE EXECUTION SUMMARY")
            if hasattr(backtest_engine, 'phase_results') and backtest_engine.phase_results:
                total_phases = len(backtest_engine.phase_results)
                successful_phases = sum(1 for r in backtest_engine.phase_results.values() 
                                      if getattr(r, 'success', False))
                logger.info(f"📊 Total Phases: {total_phases}")
                logger.info(f"✅ Successful Phases: {successful_phases}")
                logger.info(f"📈 Success Rate: {successful_phases/total_phases:.1%}")
            
            logger.info("✅ Institutional backtest demonstration completed successfully!")
        else:
            logger.warning("⚠️  Backtest returned no results")
        
        logger.info("\n" + "="*80)
        logger.info("🎉 INSTITUTIONAL BACKTEST DEMONSTRATION COMPLETED SUCCESSFULLY!")
        logger.info("="*80)
        
        return result, backtest_engine
        
    except Exception as e:
        logger.error(f"❌ Institutional backtest demonstration failed: {e}")
        raise


async def main():
    """Main demonstration function"""
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🚀 Starting Institutional Backtest Engine Demonstration")
        logger.info("This demonstration showcases the enhanced 13-phase institutional workflow")
        
        # Run the demonstration
        result, engine = await demonstrate_institutional_backtest()
        
        # Final summary
        logger.info(f"\n🎯 FINAL SUMMARY")
        logger.info(f"✅ Demonstration completed successfully")
        if result:
            logger.info(f"📊 Final Return: {getattr(result, 'total_return', 0):.2%}")
            logger.info(f"📊 Sharpe Ratio: {getattr(result, 'sharpe_ratio', 0):.3f}")
            logger.info(f"🔢 Total Trades: {getattr(result, 'total_trades', 0)}")
            
            if engine and hasattr(engine, 'phase_results') and engine.phase_results:
                total_phases = len(engine.phase_results)
                successful_phases = sum(1 for r in engine.phase_results.values() 
                                      if getattr(r, 'success', False))
                success_rate = successful_phases / total_phases if total_phases > 0 else 0
                logger.info(f"✅ Phase Success Rate: {success_rate:.1%}")
        
        logger.info("\n🎉 Thank you for using the Institutional Backtest Engine!")
        
    except Exception as e:
        logger.error(f"❌ Demonstration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(main())
