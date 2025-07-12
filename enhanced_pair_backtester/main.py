#!/usr/bin/env python3
"""
Enhanced Pair Backtesting System - Final Integrated Main Entry Point
===================================================================

Complete, production-ready backtesting framework for statistical arbitrage pair trading.
Integrates all components through the BacktestOrchestrator for comprehensive analysis.

Features:
- Complete model ensemble (Kalman, HMM, Ensemble Filter, Signal Generator)
- Realistic execution with costs and slippage
- Comprehensive performance and risk analysis
- Professional visualization and reporting
- Walk-forward analysis capabilities
- Production-ready command-line interface

Usage:
    python main_integrated.py --pair TLT_TMF
    python main_integrated.py --pair QQQ_TQQQ --training-start 2023-01-01 --training-end 2024-12-31
    python main_integrated.py --symbols TLT TMF --walk-forward --save-all
    python main_integrated.py --config production_config.json

Author: Pro Quant Desk Trader
"""

import argparse
import sys
import os
import logging
import time
from datetime import datetime
from typing import Dict, Any
import json

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.backtest_config import BacktestConfig, get_pair_config
from backtesting.orchestrator import BacktestOrchestrator


def setup_logging(log_level: str = "INFO", log_file: str = "integrated_backtest.log"):
    """Setup comprehensive logging configuration."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set specific loggers to appropriate levels
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)


def parse_arguments():
    """Parse command line arguments with comprehensive options."""
    parser = argparse.ArgumentParser(
        description="Enhanced Pair Backtesting System - Complete Integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic backtest with TLT/TMF pair
  python main_integrated.py --pair TLT_TMF
  
  # Custom symbols with specific date range
  python main_integrated.py --symbols TLT TMF --training-start 2023-01-01 --testing-end 2024-12-31
  
  # Full analysis with all features
  python main_integrated.py --pair QQQ_TQQQ --use-all-models --walk-forward --save-all
  
  # Production configuration
  python main_integrated.py --config production_config.json --verbose
  
  # Quick test mode
  python main_integrated.py --pair TLT_TMF --quick-test
        """
    )
    
    # Pair specification
    pair_group = parser.add_mutually_exclusive_group(required=True)
    pair_group.add_argument('--pair', type=str, help='Pair name (e.g., TLT_TMF, QQQ_TQQQ)')
    pair_group.add_argument('--symbols', nargs=2, metavar=('SYMBOL1', 'SYMBOL2'), 
                           help='Two symbols to trade (e.g., TLT TMF)')
    
    # Time periods
    parser.add_argument('--training-start', type=str, default='2023-01-01',
                       help='Training start date (YYYY-MM-DD)')
    parser.add_argument('--training-end', type=str, default='2024-12-31',
                       help='Training end date (YYYY-MM-DD)')
    parser.add_argument('--testing-start', type=str, default='2025-01-01',
                       help='Testing start date (YYYY-MM-DD)')
    parser.add_argument('--testing-end', type=str, default='2025-06-30',
                       help='Testing end date (YYYY-MM-DD)')
    
    # Model configuration
    parser.add_argument('--use-kalman', action='store_true', default=True,
                       help='Use Kalman filter for dynamic hedge ratios')
    parser.add_argument('--use-hmm', action='store_true', default=True,
                       help='Use HMM for regime detection')
    parser.add_argument('--use-ensemble', action='store_true', default=True,
                       help='Use ensemble classifier for trade filtering')
    parser.add_argument('--use-all-models', action='store_true', default=False,
                       help='Enable all advanced models (Kalman + HMM + Ensemble)')
    
    # Strategy parameters
    parser.add_argument('--capital', type=float, default=1000000,
                       help='Initial capital ($)')
    parser.add_argument('--entry-threshold', type=float, default=2.0,
                       help='Z-score threshold for entry')
    parser.add_argument('--exit-threshold', type=float, default=0.5,
                       help='Z-score threshold for exit')
    parser.add_argument('--lookback-window', type=int, default=60,
                       help='Lookback window for calculations')
    
    # Analysis options
    parser.add_argument('--walk-forward', action='store_true', default=False,
                       help='Enable walk-forward analysis')
    parser.add_argument('--performance-analysis', action='store_true', default=True,
                       help='Enable detailed performance analysis')
    parser.add_argument('--risk-analysis', action='store_true', default=True,
                       help='Enable comprehensive risk analysis')
    
    # Configuration file
    parser.add_argument('--config', type=str,
                       help='Path to configuration JSON file')
    
    # Output options
    parser.add_argument('--output-dir', type=str, default='results',
                       help='Output directory for results')
    parser.add_argument('--save-plots', action='store_true', default=True,
                       help='Save visualization plots')
    parser.add_argument('--save-all', action='store_true', default=False,
                       help='Save all possible outputs (plots, CSVs, reports)')
    parser.add_argument('--no-plots', action='store_true', default=False,
                       help='Disable plot generation for faster execution')
    
    # Execution options
    parser.add_argument('--quick-test', action='store_true', default=False,
                       help='Quick test mode with reduced data and simplified models')
    parser.add_argument('--parallel', action='store_true', default=False,
                       help='Enable parallel processing where possible')
    
    # Debugging and logging
    parser.add_argument('--verbose', action='store_true', default=False,
                       help='Enable verbose logging')
    parser.add_argument('--debug', action='store_true', default=False,
                       help='Enable debug mode with detailed logging')
    parser.add_argument('--log-level', type=str, default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    parser.add_argument('--log-file', type=str, default='integrated_backtest.log',
                       help='Log file name')
    
    return parser.parse_args()


def create_config_from_args(args) -> BacktestConfig:
    """Create comprehensive configuration from command line arguments."""
    
    # Determine symbols
    if args.pair:
        if args.pair in ['TLT_TMF', 'QQQ_TQQQ', 'IWM_TNA', 'UVIX_UVXY']:
            # Use pre-defined configuration
            config = get_pair_config(args.pair)
        else:
            # Parse custom pair
            symbols = args.pair.split('_')
            if len(symbols) != 2:
                raise ValueError(f"Invalid pair format: {args.pair}. Use SYMBOL1_SYMBOL2")
            config = BacktestConfig(symbol1=symbols[0], symbol2=symbols[1])
    else:
        # Use provided symbols
        config = BacktestConfig(symbol1=args.symbols[0], symbol2=args.symbols[1])
    
    # Override with command line arguments
    config.training_start = args.training_start
    config.training_end = args.training_end
    config.testing_start = args.testing_start
    config.testing_end = args.testing_end
    
    # Model configuration
    if args.use_all_models:
        config.use_kalman_filter = True
        config.use_hmm_regime = True
        config.use_ensemble_filter = True
    else:
        config.use_kalman_filter = args.use_kalman
        config.use_hmm_regime = args.use_hmm
        config.use_ensemble_filter = args.use_ensemble
    
    # Strategy parameters
    config.initial_capital = args.capital
    config.entry_threshold = args.entry_threshold
    config.exit_threshold = args.exit_threshold
    config.lookback_window = args.lookback_window
    
    # Analysis options
    config.use_walk_forward = args.walk_forward
    config.performance_analysis = args.performance_analysis
    config.risk_analysis = args.risk_analysis
    
    # Output options
    config.output_dir = args.output_dir
    config.save_plots = args.save_plots and not args.no_plots
    config.save_all = args.save_all
    
    # Execution options
    config.quick_test = args.quick_test
    config.parallel = args.parallel
    
    # Debugging
    config.verbose = args.verbose or args.debug
    config.debug = args.debug
    config.log_level = 'DEBUG' if args.debug else args.log_level
    
    # Quick test mode adjustments
    if args.quick_test:
        config.use_kalman_filter = False  # Disable Kalman for speed
        config.use_hmm_regime = False     # Disable HMM for speed
        config.use_ensemble_filter = False # Disable ensemble for speed
        config.lookback_window = 30       # Shorter lookback
        config.save_plots = False         # No plots for speed
        print("⚡ Quick test mode enabled - using simplified models for faster execution")
    
    return config


def load_config_from_file(config_path: str) -> BacktestConfig:
    """Load configuration from JSON file."""
    try:
        return BacktestConfig.load_config(config_path)
    except Exception as e:
        print(f"Error loading configuration file: {e}")
        sys.exit(1)


def validate_config(config: BacktestConfig) -> bool:
    """Validate configuration parameters."""
    try:
        # Validate dates
        train_start = datetime.strptime(config.training_start, "%Y-%m-%d")
        train_end = datetime.strptime(config.training_end, "%Y-%m-%d")
        test_start = datetime.strptime(config.testing_start, "%Y-%m-%d")
        test_end = datetime.strptime(config.testing_end, "%Y-%m-%d")
        
        if not (train_start < train_end <= test_start < test_end):
            print("Error: Dates must be in order: training_start < training_end <= testing_start < testing_end")
            return False
        
        # Validate symbols
        if not config.symbol1 or not config.symbol2:
            print("Error: Both symbols must be specified")
            return False
        
        if config.symbol1 == config.symbol2:
            print("Error: Symbols must be different")
            return False
        
        # Validate parameters
        if config.initial_capital <= 0:
            print("Error: Initial capital must be positive")
            return False
        
        if config.entry_threshold <= 0:
            print("Error: Entry threshold must be positive")
            return False
        
        if config.lookback_window < 10:
            print("Error: Lookback window must be at least 10 days")
            return False
        
        return True
        
    except Exception as e:
        print(f"Configuration validation error: {e}")
        return False


def print_config_summary(config: BacktestConfig):
    """Print comprehensive configuration summary."""
    print("\n" + "="*80)
    print("ENHANCED PAIR BACKTESTING SYSTEM - COMPLETE INTEGRATION")
    print("="*80)
    print(f"📊 Trading Pair: {config.symbol1} / {config.symbol2}")
    print(f"📅 Training Period: {config.training_start} to {config.training_end}")
    print(f"📅 Testing Period: {config.testing_start} to {config.testing_end}")
    print(f"💰 Initial Capital: ${config.initial_capital:,.2f}")
    print(f"📈 Entry Threshold: ±{config.entry_threshold}")
    print(f"📉 Exit Threshold: ±{config.exit_threshold}")
    print(f"🔍 Lookback Window: {config.lookback_window} days")
    print()
    print("🤖 MODEL CONFIGURATION:")
    print(f"  • Kalman Filter: {'✅ Enabled' if config.use_kalman_filter else '❌ Disabled'}")
    print(f"  • HMM Regime Detection: {'✅ Enabled' if config.use_hmm_regime else '❌ Disabled'}")
    print(f"  • Ensemble Filter: {'✅ Enabled' if config.use_ensemble_filter else '❌ Disabled'}")
    print()
    print("📊 ANALYSIS OPTIONS:")
    print(f"  • Walk-Forward Analysis: {'✅ Enabled' if config.use_walk_forward else '❌ Disabled'}")
    print(f"  • Performance Analysis: {'✅ Enabled' if config.performance_analysis else '❌ Disabled'}")
    print(f"  • Risk Analysis: {'✅ Enabled' if config.risk_analysis else '❌ Disabled'}")
    print()
    print("💾 OUTPUT OPTIONS:")
    print(f"  • Output Directory: {config.output_dir}")
    print(f"  • Save Plots: {'✅ Enabled' if config.save_plots else '❌ Disabled'}")
    print(f"  • Save All: {'✅ Enabled' if config.save_all else '❌ Disabled'}")
    print()
    print("⚙️ EXECUTION OPTIONS:")
    print(f"  • Quick Test Mode: {'✅ Enabled' if config.quick_test else '❌ Disabled'}")
    print(f"  • Parallel Processing: {'✅ Enabled' if config.parallel else '❌ Disabled'}")
    print(f"  • Verbose Logging: {'✅ Enabled' if config.verbose else '❌ Disabled'}")
    print("="*80)


def run_integrated_backtest(config: BacktestConfig) -> bool:
    """Run the complete integrated backtesting process."""
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize orchestrator
        logger.info("Initializing backtesting orchestrator...")
        orchestrator = BacktestOrchestrator(config)
        
        # Record start time
        start_time = time.time()
        
        # Run complete backtest
        logger.info("Starting complete backtesting process...")
        success = orchestrator.run_complete_simple_backtest()
        
        # Record end time
        end_time = time.time()
        execution_time = end_time - start_time
        
        if success:
            logger.info(f"✅ Backtesting completed successfully in {execution_time:.1f} seconds")
            
            # Print summary results
            if orchestrator.backtest_results:
                results = orchestrator.backtest_results
                
                print("\n" + "="*80)
                print("BACKTESTING RESULTS SUMMARY")
                print("="*80)
                print(f"📊 Pair: {results.pair_name}")
                print(f"📅 Period: {results.start_date} to {results.end_date} ({results.total_days} days)")
                print(f"⏱️  Execution Time: {execution_time:.1f} seconds")
                print()
                print("💰 PERFORMANCE METRICS:")
                print(f"  • Total Return: {results.total_return:.2%}")
                print(f"  • Annualized Return: {results.annualized_return:.2%}")
                print(f"  • Volatility: {results.volatility:.2%}")
                print(f"  • Sharpe Ratio: {results.sharpe_ratio:.3f}")
                print(f"  • Maximum Drawdown: {results.max_drawdown:.2%}")
                print(f"  • Calmar Ratio: {results.calmar_ratio:.3f}")
                print()
                print("📈 TRADING STATISTICS:")
                print(f"  • Total Trades: {results.total_trades}")
                print(f"  • Win Rate: {results.win_rate:.1%}")
                print(f"  • Profit Factor: {results.profit_factor:.3f}")
                print()
                print("⚠️  RISK METRICS:")
                print(f"  • Value at Risk (95%): {results.var_95:.2%}")
                print(f"  • Conditional VaR (95%): {results.cvar_95:.2%}")
                print()
                print("🤖 MODEL PERFORMANCE:")
                print(f"  • Signal Accuracy: {results.signal_accuracy:.1%}")
                print(f"  • Ensemble Accuracy: {results.ensemble_accuracy:.1%}")
                print()
                print("💸 EXECUTION COSTS:")
                print(f"  • Total Costs: ${results.total_costs:,.2f}")
                print(f"  • Cost Ratio: {results.cost_ratio:.2%}")
                print()
                
                # Regime distribution
                if results.regime_distribution:
                    print("🎯 REGIME DISTRIBUTION:")
                    for regime, freq in results.regime_distribution.items():
                        print(f"  • {regime}: {freq:.1%}")
                    print()
                
                # Files created
                if results.chart_paths:
                    print("📊 VISUALIZATIONS CREATED:")
                    for chart_type, path in results.chart_paths.items():
                        print(f"  • {chart_type}: {path}")
                    print()
                
                print("="*80)
                
                # Performance assessment
                if results.sharpe_ratio > 1.0:
                    print("🎉 EXCELLENT: Sharpe ratio > 1.0 indicates strong risk-adjusted returns")
                elif results.sharpe_ratio > 0.5:
                    print("👍 GOOD: Sharpe ratio > 0.5 indicates decent risk-adjusted returns")
                elif results.sharpe_ratio > 0:
                    print("⚠️  CAUTION: Low Sharpe ratio indicates poor risk-adjusted returns")
                else:
                    print("❌ WARNING: Negative Sharpe ratio indicates losses")
                
                if results.max_drawdown < -0.2:
                    print("⚠️  HIGH RISK: Maximum drawdown > 20% indicates high risk")
                elif results.max_drawdown < -0.1:
                    print("⚠️  MODERATE RISK: Maximum drawdown > 10% indicates moderate risk")
                else:
                    print("✅ LOW RISK: Maximum drawdown < 10% indicates controlled risk")
                
                print("="*80)
            
            return True
            
        else:
            logger.error("❌ Backtesting failed")
            return False
            
    except Exception as e:
        logger.error(f"Integrated backtesting failed: {e}")
        return False


def main():
    """Main entry point for integrated backtesting system."""
    args = parse_arguments()
    
    # Setup logging
    setup_logging(args.log_level, args.log_file)
    logger = logging.getLogger(__name__)
    
    try:
        # Print banner
        print("\n🚀 Enhanced Pair Backtesting System - Complete Integration")
        print("   Professional Statistical Arbitrage Framework")
        print("   Author: Pro Quant Desk Trader")
        
        # Create configuration
        if args.config:
            config = load_config_from_file(args.config)
            logger.info(f"Configuration loaded from: {args.config}")
        else:
            config = create_config_from_args(args)
            logger.info("Configuration created from command line arguments")
        
        # Validate configuration
        if not validate_config(config):
            logger.error("Configuration validation failed")
            sys.exit(1)
        
        # Print configuration summary
        print_config_summary(config)
        
        # Create output directory
        os.makedirs(config.output_dir, exist_ok=True)
        
        # Save configuration for reference
        config_path = os.path.join(config.output_dir, f"{config.pair_name}_config.json")
        config.save_config(config_path)
        logger.info(f"Configuration saved to: {config_path}")
        
        # Run integrated backtest
        print(f"\n🔄 Starting integrated backtesting process...")
        success = run_integrated_backtest(config)
        
        if success:
            print(f"\n✅ BACKTESTING COMPLETED SUCCESSFULLY!")
            print(f"📁 All results saved to: {config.output_dir}")
            print(f"📋 Configuration saved to: {config_path}")
            print(f"📊 Check the output directory for detailed results and visualizations")
            
            # Final recommendations
            print(f"\n💡 NEXT STEPS:")
            print(f"   1. Review the comprehensive report: {config.output_dir}/{config.pair_name}_backtest_report.txt")
            print(f"   2. Analyze the visualizations in: {config.output_dir}")
            print(f"   3. Examine the trade log: {config.output_dir}/{config.pair_name}_trades.csv")
            print(f"   4. Consider walk-forward analysis for robustness testing")
            print(f"   5. Optimize parameters based on performance metrics")
            
        else:
            print(f"\n❌ BACKTESTING FAILED!")
            print(f"📋 Check the log file for details: {args.log_file}")
            print(f"💡 Common issues:")
            print(f"   - Data availability problems")
            print(f"   - Configuration errors")
            print(f"   - Model initialization failures")
            print(f"   - Insufficient memory or processing power")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Backtesting interrupted by user")
        logger.info("Backtesting interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\n❌ Unexpected error: {e}")
        print(f"📋 Check the log file for details: {args.log_file}")
        sys.exit(1)


if __name__ == "__main__":
    main() 