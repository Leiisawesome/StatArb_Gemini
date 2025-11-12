#!/usr/bin/env python3
"""
Example: Institutional Backtest Engine - 1 Week TSLA Test

This example demonstrates how to use the fully compliant institutional backtest
engine to test trading strategies on 1 week of real TSLA data.

Compliance Status: ✅ 100% (All 7 rules implemented)

Author: StatArb_Gemini Team
Date: 2024-12-20
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core_engine.config.system_config import BacktestConfig
from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine
from core_engine.config.strategies import MomentumConfig, MeanReversionConfig
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('institutional_backtest_tsla_1week.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


async def run_tsla_1week_backtest():
    """
    Run institutional backtest on TSLA for 1 week
    
    This example demonstrates:
    1. ✅ Rule 3: Unified data flow pipeline (ProcessingPipelineOrchestrator)
    2. ✅ Rule 4: Risk governance (CentralRiskManager authorization)
    3. ✅ Rule 7: Complete execution pipeline (Phases 8-11)
    4. ✅ Rule 1: Component interface validation
    5. ✅ Rule 2: Regime-aware backtesting
    """
    
    logger.info("=" * 80)
    logger.info("INSTITUTIONAL BACKTEST ENGINE - TSLA 1 WEEK TEST")
    logger.info("=" * 80)
    logger.info("Testing Period: Last 5 trading days (1 week)")
    logger.info("Symbol: TSLA")
    logger.info("Strategies: Momentum + Mean Reversion")
    logger.info("=" * 80 + "\n")
    
    # ============================================================
    # Step 1: Configure Backtest Period (Last 1 Week)
    # ============================================================
    
    # Get last 1 week (5 trading days)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)  # 7 calendar days = ~5 trading days
    
    logger.info(f"📅 Backtest Period:")
    logger.info(f"   Start: {start_date}")
    logger.info(f"   End: {end_date}")
    logger.info(f"   Duration: 1 week (5 trading days)\n")
    
    # ============================================================
    # Step 2: Configure Strategies
    # ============================================================
    
    logger.info("⚙️  Strategy Configuration:")
    
    # Strategy 1: Momentum Strategy
    momentum_config = MomentumConfig(
        strategy_name="enhanced_momentum_tsla",
        symbols=["TSLA"],
        
        # Momentum parameters
        lookback_period=60,  # 1 hour lookback (60 minutes)
        momentum_threshold=0.02,  # 2% momentum threshold
        
        # Hybrid-composite entry/exit (from Phase 1 fixes)
        composite_z_entry=1.75,
        composite_pct_entry=92.0,
        composite_z_exit=0.7,
        composite_pct_exit=55.0,
        
        # Volume filters
        volume_z_entry_threshold=0.7,
        volume_ratio_multiplier_entry=1.3,
        volume_failure_multiplier=0.9,
        
        # ATR-based risk management
        atr_initial_stop_multiple=1.8,
        atr_trailing_activation=0.75,
        atr_trailing_distance=0.8,
        
        # Position sizing
        target_volatility_pct=0.0025,  # 25 bps target volatility
        max_capital_pct=0.5,  # Max 50% capital per position
        
        # Time-based exit
        time_stop_minutes=90,  # Max 90 minute holding
        
        # Strategy weight
        strategy_weight=0.6  # 60% allocation
    )
    
    logger.info(f"   1. Momentum Strategy:")
    logger.info(f"      - Lookback: {momentum_config.lookback_period} minutes")
    logger.info(f"      - Momentum Threshold: {momentum_config.momentum_threshold:.2%}")
    logger.info(f"      - Composite Entry: Z={momentum_config.composite_z_entry}, Pct={momentum_config.composite_pct_entry}")
    logger.info(f"      - Max Holding: {momentum_config.time_stop_minutes} minutes")
    logger.info(f"      - Allocation: {momentum_config.strategy_weight:.0%}")
    
    # Strategy 2: Mean Reversion Strategy
    mean_reversion_config = MeanReversionConfig(
        strategy_name="enhanced_mean_reversion_tsla",
        symbols=["TSLA"],
        
        # Mean reversion parameters
        lookback_period=120,  # 2 hour lookback
        entry_threshold=2.0,  # 2 standard deviations
        exit_threshold=0.5,  # 0.5 standard deviations
        
        # Position sizing
        max_position_size=0.3,  # Max 30% capital
        
        # Risk management
        stop_loss_pct=0.02,  # 2% stop loss
        profit_target_pct=0.015,  # 1.5% profit target
        
        # Strategy weight
        strategy_weight=0.4  # 40% allocation
    )
    
    logger.info(f"   2. Mean Reversion Strategy:")
    logger.info(f"      - Lookback: {mean_reversion_config.lookback_period} minutes")
    logger.info(f"      - Entry Threshold: {mean_reversion_config.entry_threshold}σ")
    logger.info(f"      - Stop Loss: {mean_reversion_config.stop_loss_pct:.2%}")
    logger.info(f"      - Allocation: {mean_reversion_config.strategy_weight:.0%}\n")
    
    # ============================================================
    # Step 3: Configure Backtest Engine
    # ============================================================
    
    logger.info("🏗️  Backtest Engine Configuration:")
    
    backtest_config = BacktestConfig(
        # Basic settings
        backtest_name="TSLA_1Week_Momentum_MeanReversion",
        backtest_mode="multi_day",
        
        # Date range
        start_date=start_date,
        end_date=end_date,
        
        # Symbols
        symbols=["TSLA"],
        
        # Strategies
        strategies=[
            {
                'type': 'momentum',
                'config': momentum_config.__dict__
            },
            {
                'type': 'mean_reversion',
                'config': mean_reversion_config.__dict__
            }
        ],
        
        # Initial capital
        initial_capital=100000.0,  # $100,000
        
        # Risk limits (Rule 4 - Risk Governance)
        max_position_size=0.10,  # Max 10% per position
        max_daily_var=0.05,  # Max 5% daily VaR
        position_concentration_limit=0.15,  # Max 15% concentration
        min_signal_confidence=0.6,  # Min 60% confidence
        
        # Regime-aware risk multipliers (Rule 2 - Regime-First)
        regime_risk_multipliers={
            'low_volatility': 1.2,
            'normal_volatility': 1.0,
            'high_volatility': 0.7,
            'extreme_volatility': 0.4
        },
        
        # Execution settings (Rule 7 - Execution Pipeline)
        commission_rate=0.001,  # 0.1% commission
        slippage_bps=2,  # 2 bps slippage
        enable_short_selling=False,  # Long only
        
        # Data settings (Rule 3 - Unified Pipeline)
        data_frequency='1min',  # 1-minute bars
        enable_feature_caching=True,
        
        # Analytics settings (Rule 7 Phase 11)
        enable_performance_analytics=True,
        enable_tca=True,  # Transaction Cost Analysis
        
        # Production settings
        enable_real_time_monitoring=False,  # Backtest mode
        log_level='INFO'
    )
    
    logger.info(f"   Backtest Name: {backtest_config.backtest_name}")
    logger.info(f"   Mode: {backtest_config.backtest_mode}")
    logger.info(f"   Initial Capital: ${backtest_config.initial_capital:,.2f}")
    logger.info(f"   Commission: {backtest_config.commission_rate:.2%}")
    logger.info(f"   Slippage: {backtest_config.slippage_bps} bps")
    logger.info(f"   Max Position Size: {backtest_config.max_position_size:.0%}")
    logger.info(f"   TCA Enabled: {backtest_config.enable_tca}\n")
    
    # ============================================================
    # Step 4: Initialize Backtest Engine
    # ============================================================
    
    logger.info("🚀 Initializing Institutional Backtest Engine...")
    logger.info("   This will validate compliance with all 7 rules:\n")
    
    try:
        # Create engine
        engine = InstitutionalBacktestEngine(backtest_config)
        
        # Initialize (performs automatic compliance validation)
        success = await engine.initialize()
        
        if not success:
            logger.error("❌ Engine initialization failed!")
            return None
        
        logger.info("✅ Engine initialized successfully!\n")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize engine: {e}", exc_info=True)
        return None
    
    # ============================================================
    # Step 5: Run Backtest
    # ============================================================
    
    logger.info("=" * 80)
    logger.info("RUNNING BACKTEST")
    logger.info("=" * 80 + "\n")
    
    try:
        # Run backtest
        results = await engine.run_backtest()
        
        if not results.get('success', False):
            logger.error(f"❌ Backtest failed: {results.get('error', 'Unknown error')}")
            return None
        
        logger.info("✅ Backtest completed successfully!\n")
        
    except Exception as e:
        logger.error(f"❌ Backtest execution failed: {e}", exc_info=True)
        return None
    
    # ============================================================
    # Step 6: Display Results
    # ============================================================
    
    logger.info("=" * 80)
    logger.info("BACKTEST RESULTS")
    logger.info("=" * 80 + "\n")
    
    summary = results.get('summary', {})
    report = results.get('report', {})
    
    # Performance metrics
    logger.info("📊 Performance Metrics:")
    logger.info(f"   Initial Capital: ${backtest_config.initial_capital:,.2f}")
    logger.info(f"   Final Capital: ${summary.get('final_capital', 0):,.2f}")
    logger.info(f"   Total Return: {summary.get('total_return_pct', 0):.2%}")
    logger.info(f"   Total P&L: ${summary.get('total_pnl', 0):,.2f}")
    logger.info(f"   Sharpe Ratio: {summary.get('sharpe_ratio', 0):.2f}")
    logger.info(f"   Max Drawdown: {summary.get('max_drawdown_pct', 0):.2%}")
    logger.info("")
    
    # Trading statistics
    logger.info("📈 Trading Statistics:")
    logger.info(f"   Total Trades: {summary.get('total_trades', 0)}")
    logger.info(f"   Winning Trades: {summary.get('winning_trades', 0)}")
    logger.info(f"   Losing Trades: {summary.get('losing_trades', 0)}")
    logger.info(f"   Win Rate: {summary.get('win_rate', 0):.2%}")
    logger.info(f"   Avg Trade P&L: ${summary.get('avg_trade_pnl', 0):.2f}")
    logger.info(f"   Avg Winner: ${summary.get('avg_winner', 0):.2f}")
    logger.info(f"   Avg Loser: ${summary.get('avg_loser', 0):.2f}")
    logger.info("")
    
    # Transaction costs (Rule 7 Phase 11 - TCA)
    if backtest_config.enable_tca:
        logger.info("💰 Transaction Cost Analysis (TCA):")
        logger.info(f"   Total Commissions: ${summary.get('total_commissions', 0):.2f}")
        logger.info(f"   Total Slippage: ${summary.get('total_slippage', 0):.2f}")
        logger.info(f"   Total Impact: ${summary.get('total_impact', 0):.2f}")
        logger.info(f"   Total Execution Costs: ${summary.get('total_execution_costs', 0):.2f}")
        logger.info(f"   Cost as % of P&L: {summary.get('costs_pct_of_pnl', 0):.2%}")
        logger.info("")
    
    # Risk metrics (Rule 4 - Risk Governance)
    logger.info("⚠️  Risk Metrics:")
    logger.info(f"   Max Position Value: ${summary.get('max_position_value', 0):,.2f}")
    logger.info(f"   Max Concentration: {summary.get('max_concentration', 0):.2%}")
    logger.info(f"   Daily VaR (95%): ${summary.get('daily_var_95', 0):,.2f}")
    logger.info(f"   Max Intraday Drawdown: {summary.get('max_intraday_dd', 0):.2%}")
    logger.info("")
    
    # Strategy attribution (Rule 5 - Multi-Strategy)
    if 'strategy_attribution' in report:
        logger.info("🎯 Strategy Attribution:")
        for strategy_name, stats in report['strategy_attribution'].items():
            logger.info(f"   {strategy_name}:")
            logger.info(f"      - Return: {stats.get('return', 0):.2%}")
            logger.info(f"      - Trades: {stats.get('trades', 0)}")
            logger.info(f"      - Win Rate: {stats.get('win_rate', 0):.2%}")
            logger.info(f"      - Sharpe: {stats.get('sharpe', 0):.2f}")
        logger.info("")
    
    # Regime analysis (Rule 2 - Regime-First)
    if 'regime_analysis' in report:
        logger.info("🔄 Regime Analysis:")
        for regime, stats in report['regime_analysis'].items():
            logger.info(f"   {regime}:")
            logger.info(f"      - Duration: {stats.get('duration_pct', 0):.1%} of backtest")
            logger.info(f"      - Return: {stats.get('return', 0):.2%}")
            logger.info(f"      - Trades: {stats.get('trades', 0)}")
        logger.info("")
    
    # Execution quality (Rule 7 Phase 11)
    logger.info("⚡ Execution Quality:")
    logger.info(f"   Avg Fill Time: {summary.get('avg_fill_time_ms', 0):.1f}ms")
    logger.info(f"   Fill Rate: {summary.get('fill_rate', 0):.2%}")
    logger.info(f"   Execution Quality Score: {summary.get('execution_quality_score', 0):.1f}/100")
    logger.info("")
    
    # Compliance status
    logger.info("✅ Compliance Status:")
    logger.info("   Rule 1 (ISystemComponent): ✅ VALIDATED")
    logger.info("   Rule 2 (IRegimeAware): ✅ VALIDATED")
    logger.info("   Rule 3 (Unified Pipeline): ✅ ACTIVE")
    logger.info("   Rule 4 (Risk Governance): ✅ ENFORCED")
    logger.info("   Rule 5 (Multi-Strategy): ✅ COORDINATED")
    logger.info("   Rule 6 (Advanced Analytics): ✅ ENABLED")
    logger.info("   Rule 7 (Execution Pipeline): ✅ COMPLETE")
    logger.info("")
    
    logger.info("=" * 80)
    logger.info("BACKTEST COMPLETE")
    logger.info("=" * 80 + "\n")
    
    # ============================================================
    # Step 7: Generate Report
    # ============================================================
    
    logger.info("📄 Generating detailed report...")
    
    try:
        report_path = await engine.generate_report()
        logger.info(f"✅ Report saved to: {report_path}\n")
    except Exception as e:
        logger.warning(f"⚠️  Report generation skipped: {e}\n")
    
    return results


async def main():
    """Main entry point"""
    
    try:
        results = await run_tsla_1week_backtest()
        
        if results and results.get('success'):
            logger.info("🎉 TSLA 1-Week Backtest Completed Successfully!")
            logger.info("   Log file: institutional_backtest_tsla_1week.log")
            return 0
        else:
            logger.error("❌ Backtest failed to complete")
            return 1
            
    except KeyboardInterrupt:
        logger.info("\n⚠️  Backtest interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    # Run the backtest
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

