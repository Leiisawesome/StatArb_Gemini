#!/usr/bin/env python3
"""
Phase 4.3: Academic Research Validation - Command Line Interface
================================================================

This script provides a command-line interface for running academic research validation
on trading strategies, validating them against established financial theory and research.

Usage:
    python3 run_phase4_academic_validation.py [options]

Examples:
    # Run basic academic validation
    python3 run_phase4_academic_validation.py

    # Run with specific strategies and symbols
    python3 run_phase4_academic_validation.py --strategies momentum,multi_factor --symbols SPY,AAPL,MSFT

    # Run with custom academic thresholds
    python3 run_phase4_academic_validation.py --min-momentum-persistence 0.7 --min-statistical-significance 0.01

    # Run with verbose output
    python3 run_phase4_academic_validation.py --verbose
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

from tests.phase_tests.test_phase4_academic_validation import AcademicResearchValidator, AcademicValidationConfig


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Phase 4.3: Academic Research Validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --strategies momentum,multi_factor --symbols SPY,AAPL
  %(prog)s --min-momentum-persistence 0.7 --verbose
  %(prog)s --academic-factors momentum_factor,market_efficiency
        """
    )
    
    # Strategy configuration
    parser.add_argument(
        '--strategies',
        type=str,
        default='momentum,multi_factor',
        help='Comma-separated list of strategies to test (default: momentum,multi_factor)'
    )
    
    parser.add_argument(
        '--symbols',
        type=str,
        default='SPY,AAPL,MSFT,GOOGL,AMZN,TSLA,NVDA,META',
        help='Comma-separated list of symbols to test (default: SPY,AAPL,MSFT,GOOGL,AMZN,TSLA,NVDA,META)'
    )
    
    # Academic factors
    parser.add_argument(
        '--academic-factors',
        type=str,
        default='momentum_factor,market_efficiency,risk_adjusted_returns,statistical_significance,factor_analysis',
        help='Comma-separated list of academic factors to test'
    )
    
    # Time periods
    parser.add_argument(
        '--time-periods',
        type=str,
        default='1Y,2Y,3Y',
        help='Comma-separated list of time periods to test (default: 1Y,2Y,3Y)'
    )
    
    # Academic thresholds
    parser.add_argument(
        '--min-momentum-persistence',
        type=float,
        default=0.6,
        help='Minimum momentum persistence threshold (default: 0.6)'
    )
    
    parser.add_argument(
        '--max-market-efficiency-deviation',
        type=float,
        default=0.1,
        help='Maximum deviation from market efficiency (default: 0.1)'
    )
    
    parser.add_argument(
        '--min-statistical-significance',
        type=float,
        default=0.05,
        help='Minimum statistical significance p-value (default: 0.05)'
    )
    
    parser.add_argument(
        '--min-factor-loading',
        type=float,
        default=0.3,
        help='Minimum factor loading significance (default: 0.3)'
    )
    
    # Performance thresholds
    parser.add_argument(
        '--min-sharpe-ratio',
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
    
    # Output settings
    parser.add_argument(
        '--results-dir',
        type=str,
        default='results/phase4',
        help='Results directory (default: results/phase4)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Run in demo mode with limited data'
    )
    
    return parser.parse_args()


def create_config_from_args(args):
    """Create AcademicValidationConfig from command line arguments"""
    
    # Parse comma-separated lists
    strategies = [s.strip() for s in args.strategies.split(',')]
    symbols = [s.strip() for s in args.symbols.split(',')]
    academic_factors = [f.strip() for f in args.academic_factors.split(',')]
    
    # Parse time periods
    time_periods = []
    for period in args.time_periods.split(','):
        period = period.strip()
        if period == '1Y':
            time_periods.append({'name': '1Y', 'months': 12})
        elif period == '2Y':
            time_periods.append({'name': '2Y', 'months': 24})
        elif period == '3Y':
            time_periods.append({'name': '3Y', 'months': 36})
        elif period == '6M':
            time_periods.append({'name': '6M', 'months': 6})
        else:
            print(f"⚠️  Unknown time period: {period}, skipping...")
    
    # Demo mode adjustments
    if args.demo:
        print("🎮 Running in DEMO mode with limited data...")
        symbols = symbols[:3]  # Limit to 3 symbols
        time_periods = time_periods[:1]  # Limit to 1 time period
        academic_factors = academic_factors[:2]  # Limit to 2 factors
    
    config = AcademicValidationConfig(
        strategies=strategies,
        symbols=symbols,
        academic_factors=academic_factors,
        time_periods=time_periods,
        min_momentum_persistence=args.min_momentum_persistence,
        max_market_efficiency_deviation=args.max_market_efficiency_deviation,
        min_statistical_significance=args.min_statistical_significance,
        min_factor_loading=args.min_factor_loading,
        min_sharpe_ratio=args.min_sharpe_ratio,
        max_drawdown=args.max_drawdown,
        min_win_rate=args.min_win_rate,
        results_dir=args.results_dir
    )
    
    return config


def print_configuration(config):
    """Print the configuration summary"""
    print("\n🔧 Phase 4.3 Configuration:")
    print("=" * 50)
    print(f"📊 Strategies: {', '.join(config.strategies)}")
    print(f"🎯 Symbols: {', '.join(config.symbols)}")
    print(f"📚 Academic Factors: {', '.join(config.academic_factors)}")
    print(f"⏰ Time Periods: {', '.join([p['name'] for p in config.time_periods])}")
    
    print(f"\n📊 Academic Thresholds:")
    print(f"   • Min Momentum Persistence: {config.min_momentum_persistence}")
    print(f"   • Max Market Efficiency Deviation: {config.max_market_efficiency_deviation}")
    print(f"   • Min Statistical Significance: {config.min_statistical_significance}")
    print(f"   • Min Factor Loading: {config.min_factor_loading}")
    
    print(f"\n📈 Performance Thresholds:")
    print(f"   • Min Sharpe Ratio: {config.min_sharpe_ratio}")
    print(f"   • Max Drawdown: {config.max_drawdown}")
    print(f"   • Min Win Rate: {config.min_win_rate}")
    
    print(f"📁 Results Directory: {config.results_dir}")
    print("=" * 50)


async def main():
    """Main execution function"""
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Set up logging
        if args.verbose:
            logging.basicConfig(level=logging.INFO)
        else:
            logging.basicConfig(level=logging.WARNING)
        
        # Create configuration
        config = create_config_from_args(args)
        
        # Print configuration
        print_configuration(config)
        
        # Create and run validator
        print(f"\n🔍 Academic Research Validator Initialized")
        print(f"📊 Strategies: {config.strategies}")
        print(f"⏰ Time Periods: {[p['name'] for p in config.time_periods]}")
        print(f"📚 Academic Factors: {config.academic_factors}")
        print(f"🎯 Symbols: {config.symbols}")
        
        validator = AcademicResearchValidator(config)
        
        print(f"\n🚀 Starting Phase 4.3: Academic Research Validation...")
        
        # Run academic validation
        success = await validator.run_academic_validation()
        
        if success:
            print(f"\n🎉 Phase 4.3: Academic Research Validation - COMPLETED SUCCESSFULLY!")
            return 0
        else:
            print(f"\n⚠️  Phase 4.3: Academic Research Validation - COMPLETED WITH ISSUES")
            return 1
            
    except KeyboardInterrupt:
        print(f"\n⏹️  Academic validation interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error during academic validation: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 