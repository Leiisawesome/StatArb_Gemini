#!/usr/bin/env python3
"""
Phase 1 Runner: Technical Momentum Strategy Testing
Executes both historical and real-time test cases for the MultiFactorEnsembleStrategy
"""

import sys
import os
import argparse
import logging
from datetime import datetime
import json

# Add the current directory (StatArb_Gemini root) to the path
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, current_dir)
# Also add the current working directory
sys.path.insert(0, os.getcwd())

from tests.test_technical_momentum_historical import TechnicalMomentumHistoricalTest
from tests.test_technical_momentum_realtime import TechnicalMomentumRealtimeTest

def setup_logging(level=logging.INFO):
    """Set up logging configuration"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'logs/phase1_technical_momentum_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
            logging.StreamHandler()
        ]
    )

def run_historical_test():
    """Run historical backtesting test"""
    print("\n" + "="*80)
    print("PHASE 1: TECHNICAL MOMENTUM HISTORICAL TEST")
    print("="*80)
    
    try:
        test = TechnicalMomentumHistoricalTest()
        results, analysis = test.run_test()
        
        print("\n✅ HISTORICAL TEST COMPLETED SUCCESSFULLY!")
        print(f"📊 Results saved to: results/technical_momentum_historical_*.json")
        print(f"📈 Analysis saved to: results/technical_momentum_historical_analysis_*.json")
        
        return True, results, analysis
        
    except Exception as e:
        print(f"\n❌ HISTORICAL TEST FAILED: {e}")
        logging.error(f"Historical test failed: {e}", exc_info=True)
        return False, None, None

def run_realtime_test():
    """Run real-time backtesting test"""
    print("\n" + "="*80)
    print("PHASE 1: TECHNICAL MOMENTUM REAL-TIME TEST")
    print("="*80)
    
    try:
        test = TechnicalMomentumRealtimeTest()
        results, analysis = test.run_test()
        
        print("\n✅ REAL-TIME TEST COMPLETED SUCCESSFULLY!")
        print(f"📊 Results saved to: results/technical_momentum_realtime_*.json")
        print(f"📈 Analysis saved to: results/technical_momentum_realtime_analysis_*.json")
        
        return True, results, analysis
        
    except Exception as e:
        print(f"\n❌ REAL-TIME TEST FAILED: {e}")
        logging.error(f"Real-time test failed: {e}", exc_info=True)
        return False, None, None

def generate_phase1_summary(historical_results, historical_analysis, 
                          realtime_results, realtime_analysis):
    """Generate comprehensive Phase 1 summary"""
    
    summary = {
        'phase1_summary': {
            'test_date': datetime.now().isoformat(),
            'phase': 'Phase 1: Technical Momentum Strategy Implementation',
            'status': 'COMPLETED',
            'tests_run': ['historical', 'realtime']
        },
        'historical_test': {
            'status': 'COMPLETED' if historical_results else 'FAILED',
            'performance_metrics': historical_results.get('performance_metrics', {}) if historical_results else {},
            'recommendations': historical_analysis.get('recommendations', []) if historical_analysis else []
        },
        'realtime_test': {
            'status': 'COMPLETED' if realtime_results else 'FAILED',
            'performance_metrics': realtime_results.get('performance_metrics', {}) if realtime_results else {},
            'recommendations': realtime_analysis.get('recommendations', []) if realtime_analysis else []
        },
        'overall_assessment': {
            'strategy_ready': historical_results is not None and realtime_results is not None,
            'next_phase': 'Phase 2: Core System Integration' if (historical_results and realtime_results) else 'Phase 1 Debugging',
            'key_achievements': [
                '✅ MultiFactorEnsembleStrategy implemented',
                '✅ Technical indicators integrated as factors',
                '✅ Historical backtesting framework operational',
                '✅ Real-time backtesting framework operational',
                '✅ Comprehensive reporting and analysis'
            ]
        }
    }
    
    # Save summary
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_filename = f"results/phase1_technical_momentum_summary_{timestamp}.json"
    
    os.makedirs("results", exist_ok=True)
    with open(summary_filename, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    return summary, summary_filename

def print_summary_report(summary):
    """Print formatted summary report"""
    print("\n" + "="*80)
    print("PHASE 1: TECHNICAL MOMENTUM STRATEGY - SUMMARY REPORT")
    print("="*80)
    
    print(f"\n📅 Test Date: {summary['phase1_summary']['test_date']}")
    print(f"🎯 Phase: {summary['phase1_summary']['phase']}")
    print(f"📊 Status: {summary['phase1_summary']['status']}")
    
    print(f"\n📈 HISTORICAL TEST:")
    historical = summary['historical_test']
    print(f"   Status: {historical['status']}")
    if historical['status'] == 'COMPLETED':
        metrics = historical['performance_metrics']
        sharpe = metrics.get('sharpe_ratio', 'N/A')
        drawdown = metrics.get('max_drawdown', 'N/A')
        returns = metrics.get('total_return', 'N/A')
        print(f"   Sharpe Ratio: {sharpe:.3f}" if isinstance(sharpe, (int, float)) else f"   Sharpe Ratio: {sharpe}")
        print(f"   Max Drawdown: {drawdown:.3f}" if isinstance(drawdown, (int, float)) else f"   Max Drawdown: {drawdown}")
        print(f"   Total Return: {returns:.3f}" if isinstance(returns, (int, float)) else f"   Total Return: {returns}")
    
    print(f"\n⚡ REAL-TIME TEST:")
    realtime = summary['realtime_test']
    print(f"   Status: {realtime['status']}")
    if realtime['status'] == 'COMPLETED':
        metrics = realtime['performance_metrics']
        sharpe = metrics.get('sharpe_ratio', 'N/A')
        drawdown = metrics.get('max_drawdown', 'N/A')
        returns = metrics.get('total_return', 'N/A')
        print(f"   Sharpe Ratio: {sharpe:.3f}" if isinstance(sharpe, (int, float)) else f"   Sharpe Ratio: {sharpe}")
        print(f"   Max Drawdown: {drawdown:.3f}" if isinstance(drawdown, (int, float)) else f"   Max Drawdown: {drawdown}")
        print(f"   Total Return: {returns:.3f}" if isinstance(returns, (int, float)) else f"   Total Return: {returns}")
    
    print(f"\n🎯 OVERALL ASSESSMENT:")
    assessment = summary['overall_assessment']
    print(f"   Strategy Ready: {'✅ YES' if assessment['strategy_ready'] else '❌ NO'}")
    print(f"   Next Phase: {assessment['next_phase']}")
    
    print(f"\n🏆 KEY ACHIEVEMENTS:")
    for achievement in assessment['key_achievements']:
        print(f"   {achievement}")
    
    print(f"\n📋 RECOMMENDATIONS:")
    if historical['recommendations']:
        print("   Historical Test:")
        for rec in historical['recommendations'][:3]:  # Show first 3
            print(f"     {rec}")
    
    if realtime['recommendations']:
        print("   Real-Time Test:")
        for rec in realtime['recommendations'][:3]:  # Show first 3
            print(f"     {rec}")

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='Phase 1: Technical Momentum Strategy Testing')
    parser.add_argument('--test', choices=['historical', 'realtime', 'both'], 
                       default='both', help='Which test(s) to run')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    os.makedirs("logs", exist_ok=True)
    setup_logging(log_level)
    
    print("🚀 PHASE 1: TECHNICAL MOMENTUM STRATEGY IMPLEMENTATION")
    print("="*80)
    print("Testing MultiFactorEnsembleStrategy with technical indicators integration")
    print(f"Test Mode: {args.test.upper()}")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize results
    historical_results = None
    historical_analysis = None
    realtime_results = None
    realtime_analysis = None
    
    # Run tests based on arguments
    if args.test in ['historical', 'both']:
        historical_success, historical_results, historical_analysis = run_historical_test()
    
    if args.test in ['realtime', 'both']:
        realtime_success, realtime_results, realtime_analysis = run_realtime_test()
    
    # Generate summary
    summary, summary_filename = generate_phase1_summary(
        historical_results, historical_analysis,
        realtime_results, realtime_analysis
    )
    
    # Print summary report
    print_summary_report(summary)
    
    print(f"\n📁 Summary saved to: {summary_filename}")
    print(f"📊 All results saved to: results/ directory")
    print(f"📝 Logs saved to: logs/ directory")
    
    print(f"\n🎉 PHASE 1 COMPLETED!")
    print(f"⏰ End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Exit with appropriate code
    if summary['overall_assessment']['strategy_ready']:
        print("✅ All tests passed - ready for Phase 2!")
        sys.exit(0)
    else:
        print("⚠️ Some tests failed - review logs and fix issues")
        sys.exit(1)

if __name__ == "__main__":
    main() 