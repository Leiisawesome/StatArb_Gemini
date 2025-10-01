#!/usr/bin/env python3
"""
Quick Start: End-to-End Functional Testing

This script provides a quick way to run functional tests on the StatArb_Gemini core engine.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.functional.run_functional_tests import (
    run_functional_test_example,
    run_single_scenario_test,
    run_data_flow_validation_only
)

def main():
    """Main entry point for functional testing"""
    
    print("🎯 StatArb_Gemini End-to-End Functional Testing")
    print("=" * 55)
    print()
    print("This framework validates complete trading logic flow using real data")
    print("through all integrated core engine components ('Lego bricks').")
    print()
    print("Available Tests:")
    print("1. 🏢 Conservative Institutional Trading")
    print("2. 🚀 Aggressive Momentum Trading") 
    print("3. 🔥 Crisis Market Stress Test")
    print("4. 🌍 Multi-Asset Diversified Portfolio")
    print("5. 🔍 Data Flow Validation Only")
    print("6. 📊 All Scenarios (Comprehensive)")
    print()
    
    while True:
        try:
            choice = input("Select test to run (1-6, or 'q' to quit): ").strip().lower()
            
            if choice == 'q' or choice == 'quit':
                print("👋 Goodbye!")
                break
            
            if choice == '1':
                print("\n🏢 Running Conservative Institutional Trading Test...")
                asyncio.run(run_single_scenario_test('conservative_institutional'))
                
            elif choice == '2':
                print("\n🚀 Running Aggressive Momentum Trading Test...")
                asyncio.run(run_single_scenario_test('aggressive_momentum'))
                
            elif choice == '3':
                print("\n🔥 Running Crisis Market Stress Test...")
                asyncio.run(run_single_scenario_test('crisis_stress_test'))
                
            elif choice == '4':
                print("\n🌍 Running Multi-Asset Diversified Portfolio Test...")
                asyncio.run(run_single_scenario_test('multi_asset_diversified'))
                
            elif choice == '5':
                print("\n🔍 Running Data Flow Validation Only...")
                asyncio.run(run_data_flow_validation_only())
                
            elif choice == '6':
                print("\n📊 Running All Scenarios (Comprehensive Testing)...")
                asyncio.run(run_functional_test_example())
                
            else:
                print("❌ Invalid choice. Please select 1-6 or 'q' to quit.")
                continue
            
            print("\n" + "=" * 55)
            continue_choice = input("Run another test? (y/n): ").strip().lower()
            if continue_choice not in ['y', 'yes']:
                print("👋 Testing completed!")
                break
                
        except KeyboardInterrupt:
            print("\n\n👋 Testing interrupted by user. Goodbye!")
            break
        except EOFError:
            print("\n\n⚠️  No interactive terminal available.")
            print("For non-interactive testing, use:")
            print("  python tests/functional/demo_functional_testing.py")
            print("👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Please try again or contact support.")

if __name__ == "__main__":
    main()
