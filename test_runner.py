#!/usr/bin/env python3
"""
Test Runner for Market Condition Analytics System
=================================================

Simple script to run all tests for the MarketCondition Analytics system
and provide a summary of results.
"""

import subprocess
import sys
import os
from datetime import datetime


def run_tests():
    """Run all tests for the Market Condition Analytics system"""
    
    print("🧪 Market Condition Analytics Test Suite")
    print("=" * 60)
    print(f"📅 Test Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Change to project directory - use current working directory
    project_dir = os.getcwd()
    print(f"📂 Running tests from: {project_dir}")
    
    test_suites = [
        {
            'name': 'Unit Tests (Simplified)',
            'path': 'tests/unit/test_market_condition_analytics_simplified.py',
            'description': 'Core functionality and data structure tests'
        },
        {
            'name': 'Integration Tests',
            'path': 'tests/integration/test_market_condition_analytics_integration.py',
            'description': 'End-to-end system integration tests'
        }
    ]
    
    results = {}
    
    for suite in test_suites:
        print(f"🔍 Running {suite['name']}")
        print(f"   {suite['description']}")
        print(f"   Path: {suite['path']}")
        
        try:
            # Run pytest with verbose output
            result = subprocess.run([
                sys.executable, '-m', 'pytest', suite['path'], 
                '-v', '--tb=short', '--no-header'
            ], 
            capture_output=True, 
            text=True,
            timeout=120
            )
            
            results[suite['name']] = {
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            # Parse test results
            lines = result.stdout.split('\n')
            
            # Find summary line
            summary_line = None
            for line in reversed(lines):
                if 'passed' in line and ('failed' in line or 'error' in line or line.strip().endswith('passed')):
                    summary_line = line.strip()
                    break
            
            if result.returncode == 0:
                print(f"   ✅ {summary_line or 'Tests passed'}")
            else:
                print(f"   ❌ {summary_line or 'Tests failed'}")
                
        except subprocess.TimeoutExpired:
            print(f"   ⏰ Tests timed out after 120 seconds")
            results[suite['name']] = {'returncode': -1, 'stdout': '', 'stderr': 'Timeout'}
        except Exception as e:
            print(f"   💥 Error running tests: {e}")
            results[suite['name']] = {'returncode': -1, 'stdout': '', 'stderr': str(e)}
        
        print()
    
    # Overall summary
    print("📊 Test Summary")
    print("-" * 30)
    
    total_suites = len(test_suites)
    passed_suites = sum(1 for r in results.values() if r['returncode'] == 0)
    
    print(f"Total test suites: {total_suites}")
    print(f"Passed: {passed_suites}")
    print(f"Failed: {total_suites - passed_suites}")
    
    if passed_suites == total_suites:
        print("\n🎉 All test suites passed!")
        return True
    else:
        print(f"\n⚠️ {total_suites - passed_suites} test suite(s) failed")
        
        # Show failure details
        for suite_name, result in results.items():
            if result['returncode'] != 0:
                print(f"\n❌ {suite_name} failures:")
                if result['stderr']:
                    print(result['stderr'][:500] + "..." if len(result['stderr']) > 500 else result['stderr'])
        
        return False


def run_specific_test(test_path: str):
    """Run a specific test file"""
    print(f"🧪 Running specific test: {test_path}")
    print("=" * 60)
    
    project_dir = "/Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini"
    os.chdir(project_dir)
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pytest', test_path, 
            '-v', '--tb=short'
        ])
        return result.returncode == 0
    except Exception as e:
        print(f"💥 Error running test: {e}")
        return False


def main():
    """Main test runner"""
    if len(sys.argv) > 1:
        # Run specific test
        test_path = sys.argv[1]
        success = run_specific_test(test_path)
    else:
        # Run all tests
        success = run_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()