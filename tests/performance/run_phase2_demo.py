#!/usr/bin/env python3
"""
Phase 2 Stress Testing Framework Demo

This script demonstrates the Phase 2 stress testing capabilities by running
a comprehensive stress test suite against a mock system.

Usage:
    python tests/performance/run_phase2_demo.py
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.performance import (
    Phase2StressTestSuite, 
    Phase2TestConfiguration,
    MarketCondition,
    FailureMode
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class MockTradingSystem:
    """Mock trading system for Phase 2 stress testing demonstration"""
    
    def __init__(self):
        self.is_operational = True
        self.components = {
            'data_manager': self,
            'risk_manager': self,
            'strategy_manager': self,
            'execution_engine': self,
            'portfolio_manager': self
        }
        self.data_cache = {}
        self.operation_count = 0
        
    async def process_market_data(self, data):
        """Process market data (simulated)"""
        self.operation_count += 1
        
        # Simulate processing time based on data complexity
        if isinstance(data, dict):
            processing_time = 0.001 + len(str(data)) * 0.00001
        else:
            processing_time = 0.001
            
        await asyncio.sleep(processing_time)
        
        # Simulate occasional processing errors under stress
        if self.operation_count % 1000 == 0:  # Every 1000th operation
            if np.random.random() < 0.01:  # 1% chance
                raise RuntimeError("Simulated processing error under stress")
        
        return {'processed': True, 'timestamp': datetime.now()}
    
    async def process_operation(self, data):
        """Process general operations (simulated)"""
        self.operation_count += 1
        
        # Store in cache (potential memory usage)
        operation_id = f"op_{self.operation_count}"
        self.data_cache[operation_id] = {
            'data': data,
            'timestamp': datetime.now(),
            'processed': True
        }
        
        # Simulate processing
        await asyncio.sleep(0.0005)
        
        # Simulate memory cleanup every 100 operations
        if len(self.data_cache) > 100:
            # Remove oldest entries
            oldest_keys = list(self.data_cache.keys())[:50]
            for key in oldest_keys:
                del self.data_cache[key]
        
        return {'result': 'success', 'operation_id': operation_id}
    
    async def process_data(self, data):
        """Process and validate data (simulated)"""
        self.operation_count += 1
        
        # Validate data integrity
        if isinstance(data, dict):
            # Check for common data corruption issues
            for key, value in data.items():
                if isinstance(value, (int, float)):
                    if np.isnan(value) or np.isinf(value):
                        raise ValueError(f"Invalid {key}: {value}")
                    if 'price' in key.lower() and value <= 0:
                        raise ValueError(f"Invalid price: {value}")
                    if 'volume' in key.lower() and value < 0:
                        raise ValueError(f"Invalid volume: {value}")
        
        await asyncio.sleep(0.001)
        return {'validated': True, 'data_quality': 'good'}
    
    async def health_check(self):
        """System health check"""
        return {
            'healthy': self.is_operational,
            'operation_count': self.operation_count,
            'cache_size': len(self.data_cache),
            'components_operational': len(self.components)
        }

async def run_phase2_demo():
    """Run Phase 2 stress testing demonstration"""
    
    logger.info("🚀 Starting Phase 2 Stress Testing Framework Demo")
    logger.info("="*60)
    
    # Create mock trading system
    target_system = MockTradingSystem()
    logger.info("✅ Mock trading system initialized")
    
    # Configure Phase 2 testing (moderate intensity for demo)
    config = Phase2TestConfiguration(
        # Test selection (enable key tests for demo)
        enable_market_stress=True,
        enable_component_failure=True,
        enable_load_stress=True,
        enable_network_failure=True,
        enable_data_corruption=True,
        enable_memory_pressure=True,
        
        # Test parameters (moderate for demo)
        test_intensity=1.5,              # 1.5x normal intensity
        test_duration_seconds=90,        # 1.5 minutes per category
        enable_baseline_comparison=True,
        
        # Specific scenarios for demo
        market_scenarios=[
            MarketCondition.HIGH_VOLATILITY,
            MarketCondition.FLASH_CRASH
        ],
        failure_modes=[
            FailureMode.GRACEFUL_SHUTDOWN,
            FailureMode.MEMORY_LEAK
        ],
        
        # Stress parameters
        max_operations_per_second=2000,
        memory_limit_mb=200,
        corruption_rate=0.03,  # 3% corruption
        network_latency_ms=100,
        packet_loss_rate=0.05,  # 5% packet loss
        
        # Reporting
        generate_detailed_reports=True,
        save_raw_data=True
    )
    
    logger.info("✅ Phase 2 test configuration created")
    logger.info(f"   Test Intensity: {config.test_intensity}x")
    logger.info(f"   Duration per category: {config.test_duration_seconds} seconds")
    logger.info(f"   Market scenarios: {len(config.market_scenarios)}")
    logger.info(f"   Failure modes: {len(config.failure_modes)}")
    
    # Create and run comprehensive stress test suite
    suite = Phase2StressTestSuite()
    logger.info("✅ Phase 2 stress test suite initialized")
    
    try:
        # Run comprehensive stress testing
        logger.info("🔥 Starting comprehensive stress testing...")
        results = await suite.run_comprehensive_stress_test(target_system, config)
        
        # Display results
        logger.info("="*60)
        logger.info("📊 PHASE 2 STRESS TESTING RESULTS")
        logger.info("="*60)
        
        print(f"\\n🎯 Overall Results:")
        print(f"   Resilience Score: {results.overall_resilience_score:.1f}/100")
        print(f"   Tests Run: {results.total_tests_run}")
        print(f"   Success Rate: {(results.successful_tests/results.total_tests_run*100):.1f}%")
        print(f"   Duration: {results.total_duration_seconds:.1f} seconds")
        
        print(f"\\n📈 Category Scores:")
        for category, score in results.category_scores.items():
            status = "✅" if score >= 70 else "⚠️" if score >= 50 else "❌"
            print(f"   {status} {category.replace('_', ' ').title()}: {score:.1f}/100")
        
        if results.recovery_capabilities:
            print(f"\\n🔄 Recovery Capabilities:")
            for metric, value in results.recovery_capabilities.items():
                print(f"   {metric.replace('_', ' ').title()}: {value:.2f}")
        
        if results.performance_degradations:
            print(f"\\n📉 Performance Degradations:")
            for category, degradation in results.performance_degradations.items():
                print(f"   {category.replace('_', ' ').title()}: {degradation:.1f}%")
        
        if results.critical_failures:
            print(f"\\n⚠️ Critical Findings ({len(results.critical_failures)} total):")
            for i, failure in enumerate(results.critical_failures[:3], 1):  # Show first 3
                print(f"   {i}. {failure}")
            if len(results.critical_failures) > 3:
                print(f"   ... and {len(results.critical_failures) - 3} more")
        
        # Overall assessment
        print(f"\\n🏆 Overall Assessment:")
        if results.overall_resilience_score >= 80:
            print("   🟢 EXCELLENT - System shows high resilience under stress")
        elif results.overall_resilience_score >= 60:
            print("   🟡 GOOD - System handles stress well with minor issues")
        elif results.overall_resilience_score >= 40:
            print("   🟠 FAIR - System shows some stress-related degradation")
        else:
            print("   🔴 POOR - System requires significant resilience improvements")
        
        logger.info("✅ Phase 2 stress testing demonstration completed successfully")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Phase 2 stress testing failed: {e}")
        raise

async def main():
    """Main demo function"""
    try:
        results = await run_phase2_demo()
        
        print(f"\\n" + "="*60)
        print("🎉 PHASE 2 DEMO COMPLETED SUCCESSFULLY")
        print("="*60)
        print(f"Final Score: {results.overall_resilience_score:.1f}/100")
        print(f"Check 'tests/performance/phase2_results/' for detailed reports")
        
    except KeyboardInterrupt:
        print("\\n⚠️ Demo interrupted by user")
    except Exception as e:
        print(f"\\n❌ Demo failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
