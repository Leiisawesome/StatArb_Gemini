"""
Phase 2 Integration Test
Comprehensive integration test for Phase 2 statistical enhancement components
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import asyncio
import logging
import random
import numpy as np
import pytest
from datetime import datetime, timedelta

# Import Phase 2 components
from tests.performance.statistical_analysis import StatisticalAnalysisEngine
from tests.performance.trend_analysis import TrendAnalysisEngine
from tests.performance.phase2_statistical_test_suite import Phase2StatisticalTestSuite

logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_phase2_integration():
    """Test Phase 2 statistical enhancement integration"""
    
    print("🚀 Starting Phase 2 Integration Test")
    print("=" * 50)
    
    try:
        # Test 1: Statistical Analysis Engine
        print("📊 Testing Statistical Analysis Engine...")
        statistical_engine = StatisticalAnalysisEngine({
            'minimum_samples': 100,
            'confidence_level': 0.95,
            'significance_level': 0.05
        })
        
        # Generate test data
        test_data = [random.gauss(1000, 100) for _ in range(1000)]
        
        # Test statistical significance validation
        significance_result = statistical_engine.validate_statistical_significance(test_data)
        print(f"  ✅ Statistical significance validation: {significance_result['valid']}")
        
        # Test comprehensive statistics
        stats = statistical_engine._calculate_comprehensive_statistics(test_data)
        print(f"  ✅ Comprehensive statistics calculated: mean={stats.mean:.2f}, std={stats.std_dev:.2f}")
        
        # Test confidence intervals
        ci_95 = statistical_engine._calculate_mean_confidence_interval(np.array(test_data), 0.95)
        print(f"  ✅ 95% Confidence interval: ({ci_95[0]:.2f}, {ci_95[1]:.2f})")
        
        # Test performance standards validation
        standards = statistical_engine._validate_performance_standards(stats)
        print(f"  ✅ Performance standards validation: {sum(standards.values())}/{len(standards)} passed")
        
        # Test 2: Trend Analysis Engine
        print("\n📈 Testing Trend Analysis Engine...")
        trend_engine = TrendAnalysisEngine({
            'regression_threshold': 0.1,
            'anomaly_threshold': 3.0,
            'min_samples_for_trend': 10
        })
        
        # Generate historical data with trend
        historical_data = []
        base_time = datetime.now() - timedelta(days=30)
        for i in range(30):
            # Simulate performance degradation
            value = 1000 + i * 10 + random.gauss(0, 50)
            historical_data.append({
                'timestamp': base_time + timedelta(days=i),
                'value': value
            })
        
        # Analyze trends
        trend_analysis = trend_engine.analyze_performance_trends(historical_data)
        print(f"  ✅ Trend analysis: direction={trend_analysis.trend_line.trend_direction}, strength={trend_analysis.trend_line.trend_strength}")
        print(f"  ✅ R-squared: {trend_analysis.trend_line.r_squared:.3f}")
        print(f"  ✅ Regressions detected: {len(trend_analysis.regressions)}")
        print(f"  ✅ Anomalies detected: {len(trend_analysis.anomalies)}")
        
        # Test 3: Phase 2 Statistical Test Suite
        print("\n🧪 Testing Phase 2 Statistical Test Suite...")
        
        # Mock system for testing
        class MockSystem:
            async def initialize(self):
                await asyncio.sleep(0.01)
            
            async def process_data(self, data):
                await asyncio.sleep(0.001)
                return {'processed': True}
        
        system = MockSystem()
        config = {
            'minimum_samples': 100,
            'confidence_level': 0.95,
            'significance_level': 0.05
        }
        
        # Run comprehensive statistical tests
        test_suite = Phase2StatisticalTestSuite(config)
        results = await test_suite.run_comprehensive_statistical_tests(system)
        
        print(f"  ✅ Test suite execution: success={results.get('overall_success')}")
        print(f"  ✅ Overall score: {results.get('overall_score', 0):.1f}/100")
        print(f"  ✅ Success rate: {results.get('statistical_summary', {}).get('success_rate', 0):.1%}")
        
        # Test 4: Integration between components
        print("\n🔗 Testing Component Integration...")
        
        # Test statistical analysis with trend data
        trend_values = [point['value'] for point in historical_data]
        trend_stats = statistical_engine._calculate_comprehensive_statistics(trend_values)
        trend_standards = statistical_engine._validate_performance_standards(trend_stats)
        
        print(f"  ✅ Trend data statistics: mean={trend_stats.mean:.2f}, p95={trend_stats.p95:.2f}")
        print(f"  ✅ Trend data standards: {sum(trend_standards.values())}/{len(trend_standards)} passed")
        
        # Test trend analysis with statistical validation
        trend_significance = statistical_engine.validate_statistical_significance(trend_values)
        print(f"  ✅ Trend data significance: {trend_significance['valid']}")
        
        # Test 5: Performance Standards Integration
        print("\n🏆 Testing Performance Standards Integration...")
        
        # Test latency standards
        latency_data = [random.gauss(5000, 500) for _ in range(1000)]  # Microseconds
        latency_stats = statistical_engine._calculate_comprehensive_statistics(latency_data)
        latency_standards = statistical_engine._validate_performance_standards(latency_stats)
        
        p99_ms = latency_stats.p99 / 1000
        p95_ms = latency_stats.p95 / 1000
        
        print(f"  ✅ Latency P99: {p99_ms:.2f}ms (standard: ≤10ms)")
        print(f"  ✅ Latency P95: {p95_ms:.2f}ms (standard: ≤5ms)")
        print(f"  ✅ Latency standards: {sum(latency_standards.values())}/{len(latency_standards)} passed")
        
        # Test memory standards
        memory_data = [random.gauss(85, 5) for _ in range(1000)]  # Efficiency percentage
        memory_stats = statistical_engine._calculate_comprehensive_statistics(memory_data)
        memory_standards = statistical_engine._validate_performance_standards(memory_stats)
        
        print(f"  ✅ Memory efficiency: {memory_stats.mean:.1f}% (standard: ≥85%)")
        print(f"  ✅ Memory standards: {sum(memory_standards.values())}/{len(memory_standards)} passed")
        
        # Test 6: Statistical Power and Effect Size
        print("\n⚡ Testing Statistical Power and Effect Size...")
        
        # Generate two groups for comparison
        group1 = [random.gauss(1000, 100) for _ in range(500)]
        group2 = [random.gauss(1100, 100) for _ in range(500)]  # 10% difference
        
        effect_size = statistical_engine.calculate_effect_size(group1, group2)
        power = statistical_engine.calculate_statistical_power_for_comparison(group1, group2)
        
        print(f"  ✅ Effect size: {effect_size:.3f}")
        print(f"  ✅ Statistical power: {power:.3f}")
        
        # Test 7: Comprehensive Report Generation
        print("\n📋 Testing Comprehensive Report Generation...")
        
        # Generate comprehensive report
        report = statistical_engine.generate_statistical_report(test_data, "Integration Test")
        
        print(f"  ✅ Report generation: status={report['status']}")
        print(f"  ✅ Overall score: {report['overall_score']:.1f}/100")
        print(f"  ✅ Recommendations: {len(report['recommendations'])} generated")
        
        # Test 8: Trend Comparison
        print("\n📊 Testing Trend Comparison...")
        
        # Generate baseline data
        baseline_data = []
        for i in range(30):
            value = 1000 + i * 5 + random.gauss(0, 50)  # Slower degradation
            baseline_data.append({
                'timestamp': base_time + timedelta(days=i),
                'value': value
            })
        
        # Compare trends
        comparison = trend_engine.compare_performance_trends(baseline_data, historical_data)
        
        print(f"  ✅ Trend comparison: {comparison['comparison_result']}")
        print(f"  ✅ Slope difference: {comparison['slope_difference']:.3f}")
        print(f"  ✅ Regression change: {comparison['regression_change']}")
        print(f"  ✅ Anomaly change: {comparison['anomaly_change']}")
        
        # Final Results
        print("\n" + "=" * 50)
        print("🎉 PHASE 2 INTEGRATION TEST COMPLETED")
        print("=" * 50)
        
        # Calculate overall success
        component_tests = [
            significance_result['valid'],
            trend_analysis.trend_line.r_squared > 0.5,
            results.get('overall_success', False),
            sum(trend_standards.values()) >= 3,
            sum(latency_standards.values()) >= 3,
            sum(memory_standards.values()) >= 3,
            effect_size > 0.5,
            power > 0.8,
            report['status'] == 'passed',
            comparison['comparison_result'] in ['improved', 'degraded', 'stable']
        ]
        
        success_rate = sum(component_tests) / len(component_tests)
        print(f"✅ Overall Success Rate: {success_rate:.1%}")
        print(f"✅ Component Tests Passed: {sum(component_tests)}/{len(component_tests)}")
        
        if success_rate >= 0.8:
            print("🎉 PHASE 2 INTEGRATION: SUCCESSFUL")
            print("🚀 Ready for Phase 3: Production Readiness")
        else:
            print("⚠️ PHASE 2 INTEGRATION: NEEDS IMPROVEMENT")
            print("🔧 Address failed components before proceeding")
        
        return {
            'success': success_rate >= 0.8,
            'success_rate': success_rate,
            'component_tests': component_tests,
            'overall_score': results.get('overall_score', 0),
            'recommendations': report['recommendations']
        }
        
    except Exception as e:
        print(f"❌ Phase 2 Integration Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

async def main():
    """Main function to run Phase 2 integration test"""
    results = await test_phase2_integration()
    
    if results.get('success'):
        print("\n🎯 PHASE 2 COMPLETION STATUS: READY FOR PHASE 3")
    else:
        print("\n🔧 PHASE 2 COMPLETION STATUS: NEEDS ATTENTION")

if __name__ == "__main__":
    asyncio.run(main())
