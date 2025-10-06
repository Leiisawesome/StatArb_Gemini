#!/usr/bin/env python3
"""
Phase 1: Comprehensive Strategy Assessment - Test Runner
========================================================

Main entry point for executing Phase 1 comprehensive strategy assessment.
Tests all 10 enhanced strategies and generates optimization priority ranking.

Usage:
    python run_phase1_assessment.py [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD]

Author: StatArb_Gemini Strategy Optimization
Version: 1.0.0 (Phase 1 Implementation)
Date: October 2025
"""

import logging
import asyncio
import argparse
from datetime import datetime
from pathlib import Path
import sys
import os

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '../../')
sys.path.insert(0, project_root)

# Import testing framework
from tests.strategy_assessment import ComprehensiveStrategyTester, StrategyTestConfig
from core_engine.data.manager import ClickHouseDataConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Phase 1: Comprehensive Strategy Assessment',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run assessment for 2022-2024
  python run_phase1_assessment.py --start-date 2022-01-01 --end-date 2024-12-31
  
  # Run assessment for 2024 only
  python run_phase1_assessment.py --start-date 2024-01-01 --end-date 2024-12-31
  
  # Run with custom symbols
  python run_phase1_assessment.py --symbols NVDA TSLA AAPL --start-date 2023-01-01
        """
    )
    
    parser.add_argument(
        '--start-date',
        type=str,
        default='2022-01-01',
        help='Start date for backtesting (YYYY-MM-DD). Default: 2022-01-01'
    )
    
    parser.add_argument(
        '--end-date',
        type=str,
        default='2024-12-31',
        help='End date for backtesting (YYYY-MM-DD). Default: 2024-12-31'
    )
    
    parser.add_argument(
        '--symbols',
        nargs='+',
        default=['NVDA', 'TSLA', 'AAPL', 'MSFT', 'GOOGL'],
        help='Symbols to test. Default: NVDA TSLA AAPL MSFT GOOGL'
    )
    
    parser.add_argument(
        '--initial-capital',
        type=float,
        default=100000.0,
        help='Initial capital for backtesting. Default: $100,000'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='tests/strategy_assessment/results',
        help='Output directory for results. Default: tests/strategy_assessment/results'
    )
    
    parser.add_argument(
        '--test-single-strategy',
        type=str,
        default=None,
        choices=['statistical_arbitrage', 'momentum', 'mean_reversion', 'pairs_trading',
                'breakout', 'trend_following', 'volatility', 'arbitrage', 'factor', 'multi_asset'],
        help='Test only a single strategy (optional)'
    )
    
    parser.add_argument(
        '--skip-data-preparation',
        action='store_true',
        help='Skip data preparation (use cached data if available)'
    )
    
    return parser.parse_args()


async def run_phase1_assessment(args):
    """
    Run Phase 1 comprehensive strategy assessment
    
    This function orchestrates the complete Phase 1 testing:
    1. Initialize testing framework
    2. Load and prepare market data
    3. Test all 10 strategies (or single strategy if specified)
    4. Generate performance rankings
    5. Create optimization priority list
    """
    
    logger.info("="*80)
    logger.info("PHASE 1: COMPREHENSIVE STRATEGY ASSESSMENT")
    logger.info("="*80)
    logger.info(f"Start Date:      {args.start_date}")
    logger.info(f"End Date:        {args.end_date}")
    logger.info(f"Symbols:         {', '.join(args.symbols)}")
    logger.info(f"Initial Capital: ${args.initial_capital:,.2f}")
    logger.info(f"Output Dir:      {args.output_dir}")
    logger.info("="*80 + "\n")
    
    try:
        # Step 1: Initialize Comprehensive Strategy Tester
        logger.info("Step 1: Initializing Comprehensive Strategy Tester...")
        tester = ComprehensiveStrategyTester(output_dir=args.output_dir)
        
        # Step 2: Configure data manager
        logger.info("\nStep 2: Configuring Data Manager...")
        data_config = ClickHouseDataConfig(
            symbols=args.symbols,
            start_date=args.start_date,
            end_date=args.end_date,
            interval='1min',
            clickhouse_host='localhost',
            clickhouse_port=8123,
            clickhouse_database='polygon_data',
            enable_caching=True
        )
        
        # Step 3: Initialize core engine components
        logger.info("\nStep 3: Initializing Core Engine Components...")
        initialized = await tester.initialize_components(data_config)
        
        if not initialized:
            logger.error("❌ Failed to initialize core engine components")
            logger.error("Please ensure:")
            logger.error("  1. ClickHouse is running (brew services start clickhouse)")
            logger.error("  2. Database 'polygon_data' exists")
            logger.error("  3. Market data is ingested for the specified date range")
            return False
        
        # Step 4: Configure base strategy config
        logger.info("\nStep 4: Configuring Strategy Parameters...")
        base_config = {
            'symbols': args.symbols,
            'start_date': args.start_date,
            'end_date': args.end_date,
            'initial_capital': args.initial_capital,
            'max_position_size': 0.10,  # 10% max per position
            'max_daily_loss': 0.02,     # 2% max daily loss
            'paper_trading_mode': True   # Backtest mode
        }
        
        # Step 5: Run strategy tests
        if args.test_single_strategy:
            # Test single strategy
            logger.info(f"\nStep 5: Testing Single Strategy: {args.test_single_strategy}")
            
            strategy_configs = {
                args.test_single_strategy: {
                    'strategy_type': args.test_single_strategy,
                    'strategy_name': f"Enhanced {' '.join(args.test_single_strategy.split('_')).title()}",
                    'strategy_config': base_config
                }
            }
            
            test_config = StrategyTestConfig(
                **strategy_configs[args.test_single_strategy],
                symbols=args.symbols,
                start_date=args.start_date,
                end_date=args.end_date,
                initial_capital=args.initial_capital
            )
            
            result = await tester.test_strategy(test_config)
            
            if result:
                logger.info(f"\n✅ Strategy testing completed successfully")
                results = {args.test_single_strategy: result}
            else:
                logger.error(f"\n❌ Strategy testing failed")
                return False
                
        else:
            # Test all strategies
            logger.info("\nStep 5: Testing All 10 Enhanced Strategies...")
            logger.info("This may take 15-30 minutes depending on data volume...\n")
            
            results = await tester.test_all_strategies(base_config)
            
            if not results:
                logger.error("\n❌ No strategies were successfully tested")
                return False
            
            logger.info(f"\n✅ Successfully tested {len(results)}/10 strategies")
        
        # Step 6: Generate Phase 1 Summary Report
        logger.info("\nStep 6: Generating Phase 1 Summary Report...")
        generate_phase1_summary(results, args.output_dir)
        
        # Step 7: Print completion summary
        logger.info("\n" + "="*80)
        logger.info("PHASE 1 ASSESSMENT COMPLETED")
        logger.info("="*80)
        logger.info(f"Total Strategies Tested: {len(results)}")
        logger.info(f"Results Directory: {args.output_dir}")
        logger.info("\nNext Steps:")
        logger.info("  1. Review strategy performance rankings")
        logger.info("  2. Analyze regime-specific performance")
        logger.info("  3. Prioritize strategies for Phase 3-7 optimization")
        logger.info("  4. Proceed to Phase 2: Data Infrastructure Enhancement")
        logger.info("="*80 + "\n")
        
        return True
        
    except Exception as e:
        logger.error(f"\n❌ Phase 1 assessment failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_phase1_summary(results: dict, output_dir: str):
    """Generate Phase 1 summary report"""
    
    from datetime import datetime
    import json
    
    # Sort strategies by performance
    sorted_strategies = sorted(
        results.items(),
        key=lambda x: x[1].optimization_priority
    )
    
    # Create summary report
    summary = {
        'phase': 'Phase 1 - Comprehensive Strategy Assessment',
        'assessment_date': datetime.now().isoformat(),
        'total_strategies_tested': len(results),
        'strategy_rankings': []
    }
    
    print("\n" + "="*80)
    print("PHASE 1 ASSESSMENT SUMMARY")
    print("="*80 + "\n")
    
    print("📊 Strategy Performance Rankings:\n")
    print(f"{'Rank':<6} {'Strategy':<35} {'Grade':<8} {'Alpha':<15} {'Sharpe':<10} {'Return':<12} {'Max DD':<10}")
    print("-"*100)
    
    for rank, (strategy_type, result) in enumerate(sorted_strategies, 1):
        metrics = result.performance_metrics
        
        print(f"{rank:<6} {result.strategy_name:<35} {result.overall_grade:<8} "
              f"{result.alpha_potential:<15} {metrics.get('sharpe_ratio', 0):>8.2f} "
              f"{metrics.get('annualized_return', 0)*100:>10.2f}% {metrics.get('max_drawdown', 0)*100:>8.2f}%")
        
        summary['strategy_rankings'].append({
            'rank': rank,
            'strategy_type': strategy_type,
            'strategy_name': result.strategy_name,
            'grade': result.overall_grade,
            'alpha_potential': result.alpha_potential,
            'optimization_priority': result.optimization_priority,
            'sharpe_ratio': metrics.get('sharpe_ratio', 0),
            'annualized_return': metrics.get('annualized_return', 0),
            'max_drawdown': metrics.get('max_drawdown', 0),
            'win_rate': metrics.get('win_rate', 0),
            'profit_factor': metrics.get('profit_factor', 0)
        })
    
    print("\n" + "="*80 + "\n")
    
    # Save summary report
    output_path = Path(output_dir)
    summary_file = output_path / 'phase1_summary_report.json'
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"📄 Phase 1 summary report saved: {summary_file}")
    
    # Print optimization priorities
    print("\n🎯 OPTIMIZATION PRIORITY LIST (for Phases 3-7):\n")
    
    for rank, (strategy_type, result) in enumerate(sorted_strategies[:5], 1):
        print(f"{rank}. {result.strategy_name} ({result.alpha_potential} potential)")
        print(f"   Current Sharpe: {result.performance_metrics.get('sharpe_ratio', 0):.2f}")
        print(f"   Top Recommendation: {result.optimization_recommendations[0] if result.optimization_recommendations else 'TBD'}")
        print()
    
    print("="*80 + "\n")


def main():
    """Main entry point"""
    
    # Parse arguments
    args = parse_arguments()
    
    # Run Phase 1 assessment
    success = asyncio.run(run_phase1_assessment(args))
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
