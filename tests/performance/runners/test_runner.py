"""
Performance Test Runner for StatArb_Gemini Core Engine
Enhanced performance test execution framework with comprehensive error handling
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import traceback

# Core engine imports
from core_engine.system.integration_manager import SystemIntegrationManager
from core_engine.system.hierarchical_orchestrator import HierarchicalSystemOrchestrator

# Performance testing imports
from tests.performance.latency_testing import LatencyProfiler, LatencyContext
from tests.performance.memory_profiling import MemoryProfiler, MemoryMonitoringContext
from tests.performance.throughput_benchmarking import ThroughputBenchmarker, LoadTestConfiguration
from tests.performance.performance_test_suite import PerformanceTestSuite

logger = logging.getLogger(__name__)

@dataclass
class PerformanceTestResult:
    """Result of a performance test execution"""
    test_name: str
    success: bool
    duration_seconds: float
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metrics is None:
            self.metrics = {}

class PerformanceTestRunner:
    """Enhanced performance test execution framework"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.test_results = {}
        self.execution_errors = []
        self.system = None
        self.orchestrator = None
        
        # Initialize performance testing components
        self.latency_profiler = LatencyProfiler(max_samples=50000)
        self.memory_profiler = MemoryProfiler(snapshot_interval=0.5, max_snapshots=20000)
        self.throughput_benchmarker = ThroughputBenchmarker(max_measurements=10000)
        self.performance_suite = PerformanceTestSuite()
        
        # Test execution configuration
        self.test_timeout = self.config.get('test_timeout', 300)  # 5 minutes
        self.retry_attempts = self.config.get('retry_attempts', 3)
        self.parallel_tests = self.config.get('parallel_tests', False)
    
    async def run_all_performance_tests(self) -> Dict[str, Any]:
        """Run all performance tests with proper error handling"""
        test_start_time = datetime.now()
        logger.info("🚀 Starting comprehensive performance test execution")
        
        try:
            # Initialize test system
            await self._initialize_test_system()
            
            # Run performance test phases
            test_phases = {
                'latency_testing': self._run_latency_tests,
                'memory_profiling': self._run_memory_tests,
                'throughput_benchmarking': self._run_throughput_tests,
                'performance_suite': self._run_performance_suite_tests
            }
            
            phase_results = {}
            
            for phase_name, phase_func in test_phases.items():
                logger.info(f"📊 Running {phase_name}...")
                try:
                    phase_result = await self._execute_test_phase(phase_name, phase_func)
                    phase_results[phase_name] = phase_result
                    logger.info(f"✅ {phase_name} completed successfully")
                except Exception as e:
                    logger.error(f"❌ {phase_name} failed: {e}")
                    phase_results[phase_name] = {
                        'success': False,
                        'error': str(e),
                        'traceback': traceback.format_exc()
                    }
                    self.execution_errors.append(f"{phase_name}: {e}")
            
            # Calculate overall results
            total_duration = (datetime.now() - test_start_time).total_seconds()
            overall_success = all(result.get('success', False) for result in phase_results.values())
            
            return {
                'overall_success': overall_success,
                'total_duration_seconds': total_duration,
                'phase_results': phase_results,
                'execution_errors': self.execution_errors,
                'test_summary': self._generate_test_summary(phase_results),
                'recommendations': self._generate_recommendations(phase_results)
            }
            
        except Exception as e:
            logger.error(f"💥 Critical error in performance test execution: {e}")
            return {
                'overall_success': False,
                'error': str(e),
                'traceback': traceback.format_exc(),
                'execution_errors': self.execution_errors
            }
        finally:
            # Cleanup
            await self._cleanup_test_system()
    
    async def _initialize_test_system(self):
        """Initialize test system for performance testing"""
        try:
            logger.info("🔧 Initializing test system...")
            
            # Initialize orchestrator
            self.orchestrator = HierarchicalSystemOrchestrator()
            
            # Initialize system integration manager with config
            system_config = {
                'test_mode': True,
                'performance_testing': True,
                'mock_components': True
            }
            self.system = SystemIntegrationManager(system_config)
            await self.system.initialize()
            
            # Register core components
            await self._register_test_components()
            
            logger.info("✅ Test system initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize test system: {e}")
            raise
    
    async def _register_test_components(self):
        """Register test components with orchestrator"""
        try:
            # Register performance testing components
            test_components = {
                'LatencyProfiler': self.latency_profiler,
                'MemoryProfiler': self.memory_profiler,
                'ThroughputBenchmarker': self.throughput_benchmarker,
                'PerformanceTestSuite': self.performance_suite
            }
            
            for name, component in test_components.items():
                if hasattr(component, 'register_with_orchestrator'):
                    component.register_with_orchestrator(self.orchestrator)
                logger.info(f"📝 Registered {name} with orchestrator")
                
        except Exception as e:
            logger.error(f"❌ Failed to register test components: {e}")
            raise
    
    async def _execute_test_phase(self, phase_name: str, phase_func) -> Dict[str, Any]:
        """Execute a test phase with error handling and retries"""
        for attempt in range(self.retry_attempts):
            try:
                start_time = time.time()
                result = await phase_func()
                duration = time.time() - start_time
                
                return {
                    'success': True,
                    'duration_seconds': duration,
                    'attempt': attempt + 1,
                    'result': result
                }
                
            except Exception as e:
                logger.warning(f"⚠️ {phase_name} attempt {attempt + 1} failed: {e}")
                if attempt == self.retry_attempts - 1:
                    raise
                await asyncio.sleep(1)  # Brief pause before retry
    
    async def _run_latency_tests(self) -> Dict[str, Any]:
        """Run latency testing with comprehensive analysis"""
        try:
            logger.info("⏱️ Running latency tests...")
            
            # Test critical operations
            operations = ['initialize', 'process_data', 'generate_signals', 'cleanup']
            latency_results = {}
            
            for operation in operations:
                if hasattr(self.system, operation):
                    operation_func = getattr(self.system, operation)
                    
                    # Measure latency with statistical analysis
                    for _ in range(1000):  # 1000 samples for statistical significance
                        with LatencyContext(self.latency_profiler, 'system', operation):
                            if asyncio.iscoroutinefunction(operation_func):
                                await operation_func()
                            else:
                                operation_func()
                    
                    # Get statistical analysis
                    stats = self.latency_profiler.get_statistics('system', operation)
                    latency_results[operation] = {
                        'mean_us': stats.mean_us,
                        'median_us': stats.median_us,
                        'p95_us': stats.p95_us,
                        'p99_us': stats.p99_us,
                        'p999_us': stats.p999_us,
                        'max_us': stats.max_us,
                        'jitter_us': stats.jitter_us,
                        'throughput_ops_per_sec': stats.throughput_ops_per_sec
                    }
            
            return {
                'latency_results': latency_results,
                'overall_latency_score': self._calculate_latency_score(latency_results),
                'meets_standards': self._validate_latency_standards(latency_results)
            }
            
        except Exception as e:
            logger.error(f"❌ Latency testing failed: {e}")
            raise
    
    async def _run_memory_tests(self) -> Dict[str, Any]:
        """Run memory profiling and leak detection"""
        try:
            logger.info("🧠 Running memory tests...")
            
            # Memory usage monitoring
            with MemoryMonitoringContext(self.memory_profiler, 'system', 'memory_test'):
                # Simulate typical workload
                for i in range(100):
                    if hasattr(self.system, 'process_data'):
                        await self.system.process_data(self._generate_test_data())
            
            # Analyze memory usage
            memory_analysis = self.memory_profiler.analyze_memory_usage('system', 'memory_test')
            
            # Detect memory leaks
            memory_leaks = self.memory_profiler.detect_memory_leaks(
                'system', 'memory_test', min_samples=50
            )
            
            return {
                'peak_memory_mb': memory_analysis.peak_memory_mb,
                'average_memory_mb': memory_analysis.average_memory_mb,
                'memory_growth_mb': memory_analysis.memory_growth_mb,
                'memory_volatility': memory_analysis.memory_volatility,
                'memory_efficiency_score': memory_analysis.memory_efficiency_score,
                'memory_leaks_detected': len(memory_leaks),
                'leak_details': [vars(leak) for leak in memory_leaks],
                'meets_standards': self._validate_memory_standards(memory_analysis)
            }
            
        except Exception as e:
            logger.error(f"❌ Memory testing failed: {e}")
            raise
    
    async def _run_throughput_tests(self) -> Dict[str, Any]:
        """Run throughput benchmarking"""
        try:
            logger.info("🚀 Running throughput tests...")
            
            # Test different load levels
            load_levels = [100, 500, 1000, 2000, 5000]  # operations per second
            throughput_results = {}
            
            for load_level in load_levels:
                config = LoadTestConfiguration(
                    target_ops_per_sec=load_level,
                    duration_seconds=60,
                    ramp_up_seconds=10
                )
                
                result = await self.throughput_benchmarker.run_load_test(
                    self.system, config
                )
                
                throughput_results[f'{load_level}_ops_per_sec'] = {
                    'target_ops_per_sec': load_level,
                    'actual_ops_per_sec': result.actual_ops_per_sec,
                    'success_rate': result.success_rate,
                    'error_rate': result.error_rate,
                    'avg_response_time_ms': result.avg_response_time_ms,
                    'p95_response_time_ms': result.p95_response_time_ms,
                    'p99_response_time_ms': result.p99_response_time_ms
                }
            
            return {
                'throughput_results': throughput_results,
                'max_sustainable_throughput': self._calculate_max_throughput(throughput_results),
                'meets_standards': self._validate_throughput_standards(throughput_results)
            }
            
        except Exception as e:
            logger.error(f"❌ Throughput testing failed: {e}")
            raise
    
    async def _run_performance_suite_tests(self) -> Dict[str, Any]:
        """Run comprehensive performance test suite"""
        try:
            logger.info("📊 Running performance test suite...")
            
            # Run comprehensive performance analysis
            suite_results = await self.performance_suite.run_comprehensive_analysis(self.system)
            
            return {
                'suite_results': suite_results,
                'overall_performance_score': suite_results.get('overall_score', 0),
                'performance_grade': self._get_performance_grade(suite_results.get('overall_score', 0)),
                'meets_standards': suite_results.get('overall_score', 0) >= 85.0
            }
            
        except Exception as e:
            logger.error(f"❌ Performance suite testing failed: {e}")
            raise
    
    def _generate_test_data(self) -> Dict[str, Any]:
        """Generate test data for performance testing"""
        return {
            'timestamp': datetime.now(),
            'symbol': 'TEST',
            'price': 100.0,
            'volume': 1000,
            'data_type': 'test_data'
        }
    
    def _calculate_latency_score(self, latency_results: Dict[str, Any]) -> float:
        """Calculate overall latency performance score"""
        if not latency_results:
            return 0.0
        
        # Weight different operations
        weights = {
            'initialize': 0.1,
            'process_data': 0.4,
            'generate_signals': 0.3,
            'cleanup': 0.2
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for operation, results in latency_results.items():
            weight = weights.get(operation, 0.1)
            
            # Score based on P99 latency (lower is better)
            p99_latency = results.get('p99_us', 0)
            if p99_latency > 0:
                # Score: 100 - (latency_ms * 10), capped at 0
                score = max(0, 100 - (p99_latency / 1000) * 10)
                total_score += score * weight
                total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def _validate_latency_standards(self, latency_results: Dict[str, Any]) -> bool:
        """Validate latency meets institutional standards"""
        standards_met = True
        
        for operation, results in latency_results.items():
            p99_latency_ms = results.get('p99_us', 0) / 1000
            p95_latency_ms = results.get('p95_us', 0) / 1000
            
            # Standards: P99 < 10ms, P95 < 5ms
            if p99_latency_ms > 10.0 or p95_latency_ms > 5.0:
                standards_met = False
                logger.warning(f"⚠️ {operation} exceeds latency standards: P99={p99_latency_ms:.2f}ms, P95={p95_latency_ms:.2f}ms")
        
        return standards_met
    
    def _validate_memory_standards(self, memory_analysis) -> bool:
        """Validate memory meets institutional standards"""
        # Standards: Efficiency score > 85%, zero leaks
        efficiency_ok = memory_analysis.memory_efficiency_score > 85.0
        leaks_ok = memory_analysis.memory_leaks_detected == 0
        
        if not efficiency_ok:
            logger.warning(f"⚠️ Memory efficiency below standard: {memory_analysis.memory_efficiency_score:.1f}% < 85%")
        
        if not leaks_ok:
            logger.warning(f"⚠️ Memory leaks detected: {memory_analysis.memory_leaks_detected}")
        
        return efficiency_ok and leaks_ok
    
    def _validate_throughput_standards(self, throughput_results: Dict[str, Any]) -> bool:
        """Validate throughput meets institutional standards"""
        # Standard: > 1000 ops/sec
        max_throughput = self._calculate_max_throughput(throughput_results)
        meets_standard = max_throughput >= 1000.0
        
        if not meets_standard:
            logger.warning(f"⚠️ Throughput below standard: {max_throughput:.0f} ops/sec < 1000")
        
        return meets_standard
    
    def _calculate_max_throughput(self, throughput_results: Dict[str, Any]) -> float:
        """Calculate maximum sustainable throughput"""
        max_throughput = 0.0
        
        for test_name, results in throughput_results.items():
            actual_ops = results.get('actual_ops_per_sec', 0)
            success_rate = results.get('success_rate', 0)
            
            # Only count tests with > 95% success rate
            if success_rate >= 0.95:
                max_throughput = max(max_throughput, actual_ops)
        
        return max_throughput
    
    def _get_performance_grade(self, score: float) -> str:
        """Get performance grade based on score"""
        if score >= 90:
            return "Excellent"
        elif score >= 80:
            return "Good"
        elif score >= 70:
            return "Fair"
        elif score >= 60:
            return "Poor"
        else:
            return "Unacceptable"
    
    def _generate_test_summary(self, phase_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive test summary"""
        total_tests = len(phase_results)
        successful_tests = sum(1 for result in phase_results.values() if result.get('success', False))
        
        return {
            'total_tests': total_tests,
            'successful_tests': successful_tests,
            'failed_tests': total_tests - successful_tests,
            'success_rate': successful_tests / total_tests if total_tests > 0 else 0,
            'execution_errors': len(self.execution_errors)
        }
    
    def _generate_recommendations(self, phase_results: Dict[str, Any]) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        for phase_name, result in phase_results.items():
            if not result.get('success', False):
                recommendations.append(f"Fix {phase_name} execution issues")
            
            if 'result' in result:
                phase_data = result['result']
                
                # Latency recommendations
                if 'latency_results' in phase_data:
                    latency_results = phase_data['latency_results']
                    for operation, metrics in latency_results.items():
                        p99_ms = metrics.get('p99_us', 0) / 1000
                        if p99_ms > 10:
                            recommendations.append(f"Optimize {operation} latency (P99: {p99_ms:.1f}ms)")
                
                # Memory recommendations
                if 'memory_efficiency_score' in phase_data:
                    efficiency = phase_data['memory_efficiency_score']
                    if efficiency < 85:
                        recommendations.append(f"Improve memory efficiency ({efficiency:.1f}% < 85%)")
                
                # Throughput recommendations
                if 'max_sustainable_throughput' in phase_data:
                    throughput = phase_data['max_sustainable_throughput']
                    if throughput < 1000:
                        recommendations.append(f"Increase throughput capacity ({throughput:.0f} < 1000 ops/sec)")
        
        return recommendations
    
    async def _cleanup_test_system(self):
        """Cleanup test system resources"""
        try:
            if self.system:
                await self.system.shutdown()
            logger.info("🧹 Test system cleanup completed")
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")

# Convenience function for running tests
async def run_performance_tests(config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Convenience function to run all performance tests"""
    runner = PerformanceTestRunner(config)
    return await runner.run_all_performance_tests()

# Test functions for pytest discovery
def test_performance_runner_import():
    """Test that performance test runner can be imported"""
    from tests.performance.test_runner import PerformanceTestRunner
    assert PerformanceTestRunner is not None

def test_performance_runner_initialization():
    """Test that performance test runner can be initialized"""
    from tests.performance.test_runner import PerformanceTestRunner
    config = {'test_timeout': 300}
    runner = PerformanceTestRunner(config)
    assert runner is not None
    assert runner.test_timeout == 300

def test_performance_runner_config():
    """Test performance test runner configuration"""
    from tests.performance.test_runner import PerformanceTestRunner
    config = {
        'test_timeout': 600,
        'retry_attempts': 5,
        'parallel_tests': True
    }
    runner = PerformanceTestRunner(config)
    assert runner.test_timeout == 600
    assert runner.retry_attempts == 5
    assert runner.parallel_tests == True

if __name__ == "__main__":
    # Run performance tests when executed directly
    async def main():
        config = {
            'test_timeout': 300,
            'retry_attempts': 3,
            'parallel_tests': False
        }
        
        results = await run_performance_tests(config)
        
        print("\n" + "="*60)
        print("📊 PERFORMANCE TEST RESULTS")
        print("="*60)
        print(f"Overall Success: {'✅' if results.get('overall_success') else '❌'}")
        print(f"Total Duration: {results.get('total_duration_seconds', 0):.2f} seconds")
        print(f"Execution Errors: {len(results.get('execution_errors', []))}")
        
        if results.get('test_summary'):
            summary = results['test_summary']
            print(f"Success Rate: {summary.get('success_rate', 0):.1%}")
        
        if results.get('recommendations'):
            print("\n🔧 RECOMMENDATIONS:")
            for rec in results['recommendations']:
                print(f"  • {rec}")
    
    asyncio.run(main())
