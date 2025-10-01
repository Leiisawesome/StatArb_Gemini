"""
Example: Running End-to-End Functional Tests

This script demonstrates how to run comprehensive functional tests that validate
the complete trading logic flow using real market data.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path

# Core engine imports
from core_engine.system.integration_manager import SystemConfiguration
from tests.functional.end_to_end_functional_tester import EndToEndFunctionalTester

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_functional_test_example():
    """Example of running end-to-end functional tests"""
    
    print("🚀 StatArb_Gemini End-to-End Functional Testing")
    print("=" * 60)
    
    try:
        # Initialize system configuration
        config = SystemConfiguration()
        
        # Initialize functional tester
        functional_tester = EndToEndFunctionalTester(config)
        
        # Run comprehensive functional tests
        print("\n📊 Running Comprehensive Functional Tests...")
        results = await functional_tester.run_comprehensive_functional_tests()
        
        # Display results summary
        print("\n" + "=" * 60)
        print("📈 FUNCTIONAL TEST RESULTS SUMMARY")
        print("=" * 60)
        
        if 'overall_summary' in results:
            summary = results['overall_summary']
            print(f"Overall Success Rate: {summary.get('success_rate', 0):.1%}")
            print(f"Total Scenarios Tested: {summary.get('total_scenarios', 0)}")
            print(f"Total Trades Executed: {summary.get('total_trades', 0):,}")
            print(f"Total P&L: ${summary.get('total_pnl', 0):,.2f}")
            print(f"Average Sharpe Ratio: {summary.get('avg_sharpe_ratio', 0):.2f}")
            print(f"Data Flow Integrity: {summary.get('avg_data_flow_integrity', 0):.1f}%")
            print(f"Trading Logic Accuracy: {summary.get('avg_trading_logic_accuracy', 0):.1f}%")
            print(f"Risk Compliance Score: {summary.get('avg_risk_compliance', 0):.1f}%")
            print(f"System Reliability: {summary.get('avg_system_reliability', 0):.1f}%")
        
        # Display individual scenario results
        if 'test_scenarios' in results:
            print(f"\n📋 Individual Scenario Results:")
            print("-" * 60)
            
            for scenario_name, scenario_result in results['test_scenarios'].items():
                status = "✅ PASS" if scenario_result.success else "❌ FAIL"
                print(f"{status} {scenario_result.test_name}")
                print(f"   Duration: {scenario_result.duration_seconds:.1f}s")
                print(f"   Trades: {scenario_result.total_trades_executed}")
                print(f"   P&L: ${scenario_result.total_pnl:,.2f}")
                print(f"   Sharpe: {scenario_result.sharpe_ratio:.2f}")
                print(f"   Data Flow: {scenario_result.data_flow_integrity:.1f}%")
                print(f"   Risk Compliance: {scenario_result.risk_compliance_score:.1f}%")
                
                if scenario_result.recommendations:
                    print(f"   Recommendations: {len(scenario_result.recommendations)}")
                print()
        
        # Display validation test results
        validation_tests = [
            ('data_flow_validation', 'Data Flow Validation'),
            ('trading_logic_validation', 'Trading Logic Validation'),
            ('risk_compliance_validation', 'Risk Compliance Validation'),
            ('system_reliability_validation', 'System Reliability Validation')
        ]
        
        print("🔍 Specialized Validation Tests:")
        print("-" * 60)
        
        for test_key, test_name in validation_tests:
            if test_key in results:
                test_result = results[test_key]
                overall_score = test_result.get('overall_score', 0)
                status = "✅ PASS" if overall_score >= 80 else "❌ FAIL"
                print(f"{status} {test_name}: {overall_score:.1f}%")
        
        # Overall assessment
        print("\n" + "=" * 60)
        if results.get('overall_summary', {}).get('success_rate', 0) >= 0.8:
            print("🎉 OVERALL ASSESSMENT: SYSTEM READY FOR PRODUCTION")
            print("   All functional tests passed with acceptable scores")
        else:
            print("⚠️  OVERALL ASSESSMENT: SYSTEM NEEDS IMPROVEMENT")
            print("   Some functional tests failed or scored below threshold")
        
        print("=" * 60)
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Functional testing failed: {e}")
        print(f"\n❌ Functional testing failed: {e}")
        return None

async def run_single_scenario_test(scenario_name: str = 'conservative_institutional'):
    """Example of running a single trading scenario test"""
    
    print(f"🎯 Running Single Scenario Test: {scenario_name}")
    print("=" * 50)
    
    try:
        # Initialize system configuration
        config = SystemConfiguration()
        
        # Initialize functional tester
        functional_tester = EndToEndFunctionalTester(config)
        await functional_tester._initialize_core_engine_for_testing()
        
        # Get scenario configuration
        if scenario_name not in functional_tester.test_scenarios:
            print(f"❌ Scenario '{scenario_name}' not found")
            return None
        
        scenario_config = functional_tester.test_scenarios[scenario_name]
        
        # Run single scenario test
        print(f"📊 Testing: {scenario_config.scenario_name}")
        print(f"   Symbols: {', '.join(scenario_config.symbols)}")
        print(f"   Date Range: {scenario_config.start_date} to {scenario_config.end_date}")
        print(f"   Initial Capital: ${scenario_config.initial_capital:,.2f}")
        print(f"   Strategies: {', '.join(scenario_config.strategies)}")
        print()
        
        result = await functional_tester._run_trading_scenario_test(scenario_config)
        
        # Display results
        print("📈 SCENARIO TEST RESULTS:")
        print("-" * 30)
        print(f"Success: {'✅ YES' if result.success else '❌ NO'}")
        print(f"Duration: {result.duration_seconds:.1f} seconds")
        print(f"Total Trades: {result.total_trades_executed}")
        print(f"Total P&L: ${result.total_pnl:,.2f}")
        print(f"Max Drawdown: {result.max_drawdown:.2%}")
        print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"Data Flow Integrity: {result.data_flow_integrity:.1f}%")
        print(f"Trading Logic Accuracy: {result.trading_logic_accuracy:.1f}%")
        print(f"Risk Compliance Score: {result.risk_compliance_score:.1f}%")
        print(f"System Reliability: {result.system_reliability_score:.1f}%")
        print(f"Errors: {result.error_count}")
        print(f"Warnings: {result.warnings_count}")
        
        if result.recommendations:
            print(f"\n💡 Recommendations:")
            for i, rec in enumerate(result.recommendations, 1):
                print(f"   {i}. {rec}")
        
        await functional_tester._cleanup_test_environment()
        return result
        
    except Exception as e:
        logger.error(f"❌ Single scenario test failed: {e}")
        print(f"\n❌ Single scenario test failed: {e}")
        return None

async def run_data_flow_validation_only():
    """Example of running only data flow validation tests"""
    
    print("🔍 Running Data Flow Validation Tests Only")
    print("=" * 45)
    
    try:
        # Initialize system configuration
        config = SystemConfiguration()
        
        # Initialize functional tester
        functional_tester = EndToEndFunctionalTester(config)
        await functional_tester._initialize_core_engine_for_testing()
        
        # Run data flow validation tests
        validation_results = await functional_tester._run_data_flow_validation_tests()
        
        # Display results
        print("📊 DATA FLOW VALIDATION RESULTS:")
        print("-" * 35)
        print(f"Data Consistency Score: {validation_results['data_consistency_score']:.1f}%")
        print(f"Pipeline Integrity Score: {validation_results['pipeline_integrity_score']:.1f}%")
        print(f"Cross-Component Validation: {validation_results['cross_component_validation_score']:.1f}%")
        print(f"Audit Trail Completeness: {validation_results['audit_trail_completeness_score']:.1f}%")
        print(f"Overall Data Flow Score: {validation_results['overall_data_flow_score']:.1f}%")
        
        if validation_results['issues_found']:
            print(f"\n⚠️  Issues Found:")
            for issue in validation_results['issues_found']:
                print(f"   • {issue}")
        
        if validation_results['recommendations']:
            print(f"\n💡 Recommendations:")
            for rec in validation_results['recommendations']:
                print(f"   • {rec}")
        
        overall_score = validation_results['overall_data_flow_score']
        if overall_score >= 90:
            print(f"\n✅ EXCELLENT: Data flow validation passed with high score")
        elif overall_score >= 80:
            print(f"\n✅ GOOD: Data flow validation passed")
        else:
            print(f"\n⚠️  NEEDS IMPROVEMENT: Data flow validation needs attention")
        
        await functional_tester._cleanup_test_environment()
        return validation_results
        
    except Exception as e:
        logger.error(f"❌ Data flow validation failed: {e}")
        print(f"\n❌ Data flow validation failed: {e}")
        return None

if __name__ == "__main__":
    print("🎯 StatArb_Gemini Functional Testing Examples")
    print("Choose a test to run:")
    print("1. Comprehensive Functional Tests (All Scenarios)")
    print("2. Single Scenario Test")
    print("3. Data Flow Validation Only")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        asyncio.run(run_functional_test_example())
    elif choice == "2":
        scenario = input("Enter scenario name (conservative_institutional/aggressive_momentum/crisis_stress_test/multi_asset_diversified): ").strip()
        if not scenario:
            scenario = "conservative_institutional"
        asyncio.run(run_single_scenario_test(scenario))
    elif choice == "3":
        asyncio.run(run_data_flow_validation_only())
    else:
        print("Invalid choice. Running comprehensive tests by default.")
        asyncio.run(run_functional_test_example())
