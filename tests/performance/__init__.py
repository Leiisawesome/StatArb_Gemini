"""
Performance Testing Framework for StatArb_Gemini Core Engine

This package provides comprehensive performance and stress testing capabilities including:

Phase 1 - Performance & Scalability Testing:
- Latency profiling and analysis
- Memory usage monitoring and leak detection  
- Throughput benchmarking and scalability testing
- Integrated performance analysis and optimization recommendations

Phase 2 - Stress Testing & Failure Scenarios:
- Market stress testing (bull/bear/sideways scenarios)
- Component failure and recovery testing
- Load stress testing (high-volume operations)
- Network failure and resilience testing
- Data corruption and validation testing
- Memory pressure and resource exhaustion testing

Usage:
    # Phase 1: Performance Testing
    from tests.performance import PerformanceTestSuite
    test_suite = PerformanceTestSuite()
    results = await test_suite.run_comprehensive_performance_tests(integration_manager)
    
    # Phase 2: Stress Testing
    from tests.performance import Phase2StressTestSuite, Phase2TestConfiguration
    stress_suite = Phase2StressTestSuite()
    config = Phase2TestConfiguration(test_intensity=2.0)
    results = await stress_suite.run_comprehensive_stress_test(target_system, config)
"""

from .latency_testing import (
    LatencyProfiler,
    ComponentLatencyTester,
    LatencyMeasurement,
    LatencyStatistics,
    LatencyContext,
    measure_latency
)

from .memory_profiling import (
    MemoryProfiler,
    ComponentMemoryTester,
    MemorySnapshot,
    MemoryLeak,
    MemoryAnalysis,
    MemoryMonitoringContext
)

from .throughput_benchmarking import (
    ThroughputBenchmarker,
    ComponentThroughputTester,
    ThroughputMeasurement,
    ThroughputStatistics,
    LoadTestConfiguration
)

from .performance_test_suite import (
    PerformanceTestSuite,
    run_performance_tests
)

# Phase 2: Stress Testing & Failure Scenarios Framework
from .stress_testing import (
    StressTestSuite,
    StressTestConfiguration,
    StressTestResult,
    StressTestType,
    MarketStressTester,
    ComponentFailureTester,
    LoadStressTester,
    MarketCondition,
    FailureMode
)

from .network_failure_testing import (
    NetworkFailureTester,
    ConnectionResilienceTester,
    LatencySpikeTester
)

from .data_corruption_testing import (
    DataCorruptionTester,
    DataValidationTester,
    RecoveryMechanismTester
)

from .memory_pressure_testing import (
    MemoryPressureTester,
    ResourceExhaustionTester,
    GarbageCollectionTester
)

from .phase2_stress_test_suite import (
    Phase2StressTestSuite,
    Phase2TestConfiguration,
    Phase2TestResults
)

__all__ = [
    # Latency testing
    'LatencyProfiler',
    'ComponentLatencyTester', 
    'LatencyMeasurement',
    'LatencyStatistics',
    'LatencyContext',
    'measure_latency',
    
    # Memory profiling
    'MemoryProfiler',
    'ComponentMemoryTester',
    'MemorySnapshot',
    'MemoryLeak', 
    'MemoryAnalysis',
    'MemoryMonitoringContext',
    
    # Throughput benchmarking
    'ThroughputBenchmarker',
    'ComponentThroughputTester',
    'ThroughputMeasurement',
    'ThroughputStatistics',
    'LoadTestConfiguration',
    
    # Integrated test suite
    'PerformanceTestSuite',
    'run_performance_tests',
    
    # Phase 2 - Stress Testing
    'StressTestSuite',
    'StressTestConfiguration',
    'StressTestResult',
    'StressTestType',
    'MarketStressTester',
    'ComponentFailureTester',
    'LoadStressTester',
    'MarketCondition',
    'FailureMode',
    'NetworkFailureTester',
    'ConnectionResilienceTester',
    'LatencySpikeTester',
    'DataCorruptionTester',
    'DataValidationTester',
    'RecoveryMechanismTester',
    'MemoryPressureTester',
    'ResourceExhaustionTester',
    'GarbageCollectionTester',
    'Phase2StressTestSuite',
    'Phase2TestConfiguration',
    'Phase2TestResults'
]

__version__ = "2.0.0"  # Updated to Phase 2
__author__ = "StatArb_Gemini Performance Team"
