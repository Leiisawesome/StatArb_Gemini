#!/usr/bin/env python3
"""
Phase 4.2: Comprehensive Backtesting Validation Runner
====================================================

This script runs comprehensive validation of the backtesting framework
with multiple strategies, time periods, and market conditions.

Usage:
    python3 run_phase4_comprehensive_validation.py [options]

Options:
    --strategies STRATEGIES    Comma-separated list of strategies to test
    --symbols SYMBOLS         Comma-separated list of symbols to test
    --time-periods PERIODS    Comma-separated list of time periods (1M,3M,6M,1Y,2Y)
    --regimes REGIMES         Comma-separated list of market regimes (bull,bear,sideways)
    --min-sharpe RATIO        Minimum Sharpe ratio threshold (default: 0.5)
    --max-drawdown RATIO      Maximum drawdown threshold (default: 0.20)
    --min-win-rate RATE       Minimum win rate threshold (default: 0.45)
    --min-trades COUNT        Minimum number of trades (default: 50)
    --results-dir DIR         Results directory (default: results/phase4)
    --verbose                 Enable verbose output
    --help                    Show this help message

Examples:
    # Run with default settings
    python3 run_phase4_comprehensive_validation.py
    
    # Run with specific strategies and symbols
    python3 run_phase4_comprehensive_validation.py --strategies momentum,multi_factor --symbols SPY,AAPL,MSFT
    
    # Run with custom thresholds
    python3 run_phase4_comprehensive_validation.py --min-sharpe 0.7 --max-drawdown 0.15
    
    # Run with verbose output
    python3 run_phase4_comprehensive_validation.py --verbose
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backtesting_framework.tests.phase_tests.test_phase4_comprehensive_backtesting import (
    ComprehensiveBacktestValidator, 
    BacktestValidationConfig
)


def parse_arguments():
    """Parse command line arguments"""
    
    parser = argparse.ArgumentParser(
        description="Phase 4.2: Comprehensive Backtesting Validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Strategy options
    parser.add_argument(
        '--strategies',
        type=str,
        default='momentum,multi_factor,pairs_trading',
        help='Comma-separated list of strategies to test (default: momentum,multi_factor,pairs_trading)'
    )
    
    # Symbol options
    parser.add_argument(
        '--symbols',
        type=str,
        default='SPY,AAPL,MSFT,GOOGL,AMZN,TSLA,NVDA,META',
        help='Comma-separated list of symbols to test (default: SPY,AAPL,MSFT,GOOGL,AMZN,TSLA,NVDA,META)'
    )
    
    # Time period options
    parser.add_argument(
        '--time-periods',
        type=str,
        default='1M,3M,6M,1Y,2Y',
        help='Comma-separated list of time periods to test (default: 1M,3M,6M,1Y,2Y)'
    )
    
    # Market regime options
    parser.add_argument(
        '--regimes',
        type=str,
        default='bull,bear,sideways',
        help='Comma-separated list of market regimes to test (default: bull,bear,sideways)'
    )
    
    # Performance threshold options
    parser.add_argument(
        '--min-sharpe',
        type=float,
        default=0.5,
        help='Minimum Sharpe ratio threshold (default: 0.5)'
    )
    
    parser.add_argument(
        '--max-drawdown',
        type=float,
        default=0.20,
        help='Maximum drawdown threshold (default: 0.20)'
    )
    
    parser.add_argument(
        '--min-win-rate',
        type=float,
        default=0.45,
        help='Minimum win rate threshold (default: 0.45)'
    )
    
    parser.add_argument(
        '--min-trades',
        type=int,
        default=50,
        help='Minimum number of trades (default: 50)'
    )
    
    # Output options
    parser.add_argument(
        '--results-dir',
        type=str,
        default='results/phase4',
        help='Results directory (default: results/phase4)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    return parser.parse_args()


def create_config_from_args(args):
    """Create configuration from command line arguments"""
    
    # Parse comma-separated lists
    strategies = [s.strip() for s in args.strategies.split(',') if s.strip()]
    symbols = [s.strip() for s in args.symbols.split(',') if s.strip()]
    time_periods = [p.strip() for p in args.time_periods.split(',') if p.strip()]
    regimes = [r.strip() for r in args.regimes.split(',') if r.strip()]
    
    # Create configuration
    config = BacktestValidationConfig()
    
    # Update configuration with command line arguments
    config.strategies = strategies
    config.symbols = symbols
    config.market_regimes = regimes
    config.min_sharpe_ratio = args.min_sharpe
    config.max_drawdown = args.max_drawdown
    config.min_win_rate = args.min_win_rate
    config.min_trades = args.min_trades
    config.results_dir = args.results_dir
    config.save_detailed_results = True
    
    # Update time periods based on command line arguments
    from datetime import datetime, timedelta
    
    end_date = datetime.now()
    period_mapping = {
        '1M': 30,
        '3M': 90,
        '6M': 180,
        '1Y': 365,
        '2Y': 730
    }
    
    config.time_periods = []
    for period_name in time_periods:
        if period_name in period_mapping:
            days = period_mapping[period_name]
            config.time_periods.append({
                'name': period_name,
                'start': end_date - timedelta(days=days),
                'end': end_date
            })
    
    return config


def print_configuration(config):
    """Print configuration summary"""
    
    print("🔧 Phase 4.2 Configuration:")
    print("=" * 50)
    print(f"📊 Strategies: {', '.join(config.strategies)}")
    print(f"🎯 Symbols: {', '.join(config.symbols)}")
    print(f"⏰ Time Periods: {', '.join([p['name'] for p in config.time_periods])}")
    print(f"📈 Market Regimes: {', '.join(config.market_regimes)}")
    print(f"📊 Performance Thresholds:")
    print(f"   • Min Sharpe Ratio: {config.min_sharpe_ratio}")
    print(f"   • Max Drawdown: {config.max_drawdown}")
    print(f"   • Min Win Rate: {config.min_win_rate}")
    print(f"   • Min Trades: {config.min_trades}")
    print(f"📁 Results Directory: {config.results_dir}")
    print("=" * 50)


async def main():
    """Main execution function"""
    
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Create configuration
        config = create_config_from_args(args)
        
        # Print configuration
        print_configuration(config)
        
        # Create validator
        validator = ComprehensiveBacktestValidator(config)
        
        # Run comprehensive validation
        print("\n🚀 Starting Phase 4.2: Comprehensive Backtesting Validation...")
        success = await validator.run_comprehensive_validation()
        
        if success:
            print("\n🎉 Phase 4.2: Comprehensive Backtesting Validation - COMPLETED SUCCESSFULLY!")
            return 0
        else:
            print("\n⚠️  Phase 4.2: Comprehensive Backtesting Validation - COMPLETED WITH ISSUES")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️  Validation interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error running Phase 4.2 validation: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 