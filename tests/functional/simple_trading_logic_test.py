#!/usr/bin/env python3
"""
Simple Trading Logic Test
Test the trading logic validator without heavy dependencies
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core_engine.system.integration_manager import SystemIntegrationManager, SystemConfiguration

async def test_trading_logic_validator():
    """Test the trading logic validator with simple scenarios"""
    
    print("🧠 Testing Trading Logic Validator")
    print("=" * 50)
    
    try:
        # Initialize system
        config = SystemConfiguration()
        integration_manager = SystemIntegrationManager(config)
        
        print("🔧 Initializing core engine...")
        await integration_manager.initialize()
        
        # Import the validator after system is initialized
        from tests.functional.trading_logic_validator import TradingLogicValidator
        
        # Create validator
        validator = TradingLogicValidator(integration_manager)
        
        # Define simple test scenarios
        test_scenarios = [
            {
                'name': 'Conservative Trading',
                'symbols': ['AAPL', 'MSFT'],
                'strategy_type': 'mean_reversion',
                'risk_level': 'low',
                'expected_performance': 75.0
            },
            {
                'name': 'Momentum Trading',
                'symbols': ['TSLA', 'NVDA'],
                'strategy_type': 'momentum',
                'risk_level': 'medium',
                'expected_performance': 80.0
            }
        ]
        
        print(f"📊 Testing {len(test_scenarios)} trading scenarios...")
        
        # Run validation
        result = await validator.validate_trading_logic(test_scenarios)
        
        # Display results
        print("\n📈 TRADING LOGIC VALIDATION RESULTS:")
        print("-" * 40)
        print(f"Success: {'✅ YES' if result.success else '❌ NO'}")
        print(f"Accuracy Score: {result.accuracy_score:.1f}%")
        print(f"Issues Found: {len(result.issues_found)}")
        
        if result.strategy_performance:
            print(f"\n📊 Strategy Performance:")
            for scenario, score in result.strategy_performance.items():
                print(f"   {scenario}: {score:.1f}%")
        
        if result.signal_quality_metrics:
            print(f"\n🎯 Signal Quality:")
            for scenario, score in result.signal_quality_metrics.items():
                print(f"   {scenario}: {score:.1f}%")
        
        if result.execution_efficiency:
            print(f"\n⚡ Execution Efficiency:")
            for scenario, score in result.execution_efficiency.items():
                print(f"   {scenario}: {score:.1f}%")
        
        if result.risk_management_effectiveness:
            print(f"\n🛡️ Risk Management:")
            for scenario, score in result.risk_management_effectiveness.items():
                print(f"   {scenario}: {score:.1f}%")
        
        if result.issues_found:
            print(f"\n⚠️ Issues Found:")
            for issue in result.issues_found:
                print(f"   • {issue}")
        
        if result.recommendations:
            print(f"\n💡 Recommendations:")
            for rec in result.recommendations:
                print(f"   • {rec}")
        
        print(f"\n⏱️ Validation completed in {result.detailed_results.get('validation_duration_seconds', 0):.2f} seconds")
        
        # Cleanup
        print("\n🧹 Cleaning up...")
        await integration_manager.stop()
        
        print("✅ Trading logic validation test completed!")
        return result.success
        
    except Exception as e:
        print(f"❌ Trading logic validation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_trading_logic_validator())
    sys.exit(0 if success else 1)
