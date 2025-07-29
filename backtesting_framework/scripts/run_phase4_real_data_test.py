#!/usr/bin/env python3
"""
Phase 4.1: Real Historical Data Testing Runner
Execute comprehensive testing with ClickHouse data
"""

import asyncio
import sys
import os
import argparse
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

from tests.phase_tests.test_phase4_real_historical_data import RealHistoricalDataTester

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Phase 4.1: Real Historical Data Testing')
    
    parser.add_argument(
        '--symbols',
        nargs='+',
        default=['SPY', 'AAPL', 'MSFT', 'GOOGL'],
        help='Symbols to test (default: SPY AAPL MSFT GOOGL)'
    )
    
    parser.add_argument(
        '--start-date',
        default='2023-01-01',
        help='Start date for testing (default: 2023-01-01)'
    )
    
    parser.add_argument(
        '--end-date',
        default='2025-06-30',
        help='End date for testing (default: 2025-06-30)'
    )
    
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Run in demo mode with simulated data if ClickHouse unavailable'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser.parse_args()

async def run_phase4_testing():
    """Run Phase 4.1 testing with command line arguments"""
    
    args = parse_arguments()
    
    print("🚀 Phase 4.1: Real Historical Data Testing")
    print("=" * 50)
    print(f"Symbols: {', '.join(args.symbols)}")
    print(f"Date Range: {args.start_date} to {args.end_date}")
    print(f"Demo Mode: {args.demo}")
    print(f"Verbose: {args.verbose}")
    print("=" * 50)
    
    try:
        # Initialize tester
        tester = RealHistoricalDataTester()
        
        # Update configuration based on arguments
        tester.test_symbols = args.symbols
        tester.start_date = args.start_date
        tester.end_date = args.end_date
        
        # Run the test
        start_time = datetime.now()
        success = await tester.test_with_real_data()
        end_time = datetime.now()
        
        # Report results
        duration = end_time - start_time
        print(f"\n⏱️  Test Duration: {duration}")
        
        if success:
            print("\n🎉 Phase 4.1: Real Historical Data Testing - COMPLETED SUCCESSFULLY!")
            print("✅ All validation checks passed")
            print("✅ Enhanced backtesting completed")
            print("✅ Results saved and analyzed")
            return 0
        else:
            print("\n❌ Phase 4.1: Real Historical Data Testing - FAILED!")
            print("❌ One or more validation checks failed")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return 1

def main():
    """Main entry point"""
    
    try:
        exit_code = asyncio.run(run_phase4_testing())
        sys.exit(exit_code)
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 