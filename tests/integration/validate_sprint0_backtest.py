"""
Sprint 0 Simple Backtest Validation
===================================

Simple validation that runs existing backtest tests to verify Sprint 0 components.
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and capture output"""
    print(f"\n{'='*80}")
    print(f"Running: {description}")
    print(f"{'='*80}\n")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"❌ Test timed out after 300 seconds")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def main():
    """Run Sprint 0 validation tests"""
    
    print("=" * 80)
    print("SPRINT 0 FULL BACKTEST VALIDATION")
    print("=" * 80)
    print("\nThis will run existing backtest tests to validate Sprint 0 components:\n")
    print("1. Phase 4 End-to-End Test (validates complete pipeline)")
    print("2. Phase 5 Execution Flow Test (validates execution with Sprint 0)")
    print()
    
    results = {}
    
    # Test 1: Phase 4 End-to-End (validates complete pipeline)
    results['Phase 4 E2E'] = run_command(
        "cd /Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini && python -m pytest backtest/tests/test_phase4_end_to_end.py -v -s --tb=short",
        "Phase 4 End-to-End Test (Complete Pipeline)"
    )
    
    # Test 2: Phase 5 Execution Flow (validates execution)
    results['Phase 5 Execution'] = run_command(
        "cd /Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini && python -m pytest backtest/tests/test_phase5_execution_flow.py -v -s --tb=short",
        "Phase 5 Execution Flow Test (With Rejection Handling)"
    )
    
    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    passed_count = sum(1 for p in results.values() if p)
    total_count = len(results)
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed ({passed_count/total_count*100:.0f}%)")
    
    if passed_count == total_count:
        print("\n🎉 Sprint 0 validation: SUCCESSFUL")
        print("All backtest tests passed with Sprint 0 components integrated")
        return 0
    else:
        print(f"\n⚠️ Sprint 0 validation: PARTIAL ({total_count - passed_count} failures)")
        print("Review test output above for details")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)

