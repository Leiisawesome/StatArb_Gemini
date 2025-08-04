"""
Performance and Reliability Tests - Batch 10

This module tests performance benchmarking, reliability testing, scalability validation,
and performance monitoring.
"""

import pytest
import asyncio
import time
import random
import math
import statistics
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from tests.integration.conftest import TestConfig
from tests.integration.mock_services import (
    MockSignalGenerator, MockExecutionEngine, MockRiskManager, MockPortfolioManager,
    MockSignal, MockOrder, MockExecution
)
from tests.integration.test_data_scenarios import TestDataScenarios
from tests.integration.test_logging import monitoring_context, log_test_event


@dataclass
class PerformanceMetrics:
    """Performance metrics structure for testing."""
    operation_type: str
    duration_ms: float
    throughput_per_second: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float
    error_rate: float
    timestamp: datetime


@dataclass
class ReliabilityMetrics:
    """Reliability metrics structure for testing."""
    uptime_percent: float
    mean_time_between_failures_seconds: float
    mean_time_to_recovery_seconds: float
    failure_rate_per_hour: float
    availability_score: float
    error_count: int
    total_operations: int
    timestamp: datetime


@dataclass
class ScalabilityMetrics:
    """Scalability metrics structure for testing."""
    load_level: str  # 'LOW', 'MEDIUM', 'HIGH', 'EXTREME'
    concurrent_operations: int
    throughput_per_second: float
    response_time_ms: float
    resource_utilization_percent: float
    bottleneck_detected: bool
    scaling_factor: float
    timestamp: datetime


class MockPerformanceBenchmark:
    """Mock performance benchmark system for testing."""
    
    def __init__(self):
        self.benchmark_results = {}
        self.performance_history = []
        self.reliability_metrics = {}
        self.scalability_results = {}
        self.performance_alerts = []
        
    async def run_performance_benchmark(self, operation_type: str, iterations: int = 100) -> PerformanceMetrics:
        """Run performance benchmark for specific operation type."""
        start_time = time.time()
        
        try:
            # Simulate benchmark execution
            await asyncio.sleep(random.uniform(0.050, 0.100))  # 50-100ms
            
            # Generate performance data
            durations = []
            for _ in range(iterations):
                # Simulate operation duration with realistic variation
                if operation_type == 'SIGNAL_GENERATION':
                    duration = random.uniform(1, 5)  # 1-5ms
                elif operation_type == 'RISK_VALIDATION':
                    duration = random.uniform(2, 8)  # 2-8ms
                elif operation_type == 'ORDER_EXECUTION':
                    duration = random.uniform(5, 15)  # 5-15ms
                elif operation_type == 'PORTFOLIO_UPDATE':
                    duration = random.uniform(3, 10)  # 3-10ms
                else:
                    duration = random.uniform(1, 10)  # 1-10ms
                
                durations.append(duration)
                await asyncio.sleep(duration / 1000)  # Convert to seconds
            
            # Calculate performance metrics
            total_duration = time.time() - start_time
            throughput = iterations / total_duration if total_duration > 0 else 0
            
            # Calculate percentiles
            durations_sorted = sorted(durations)
            p50_idx = int(0.5 * len(durations_sorted))
            p95_idx = int(0.95 * len(durations_sorted))
            p99_idx = int(0.99 * len(durations_sorted))
            
            latency_p50 = durations_sorted[p50_idx] if durations_sorted else 0
            latency_p95 = durations_sorted[p95_idx] if durations_sorted else 0
            latency_p99 = durations_sorted[p99_idx] if durations_sorted else 0
            
            # Simulate resource usage
            memory_usage = random.uniform(50, 200)  # 50-200MB
            cpu_usage = random.uniform(5, 25)  # 5-25%
            error_rate = random.uniform(0, 0.05)  # 0-5%
            
            metrics = PerformanceMetrics(
                operation_type=operation_type,
                duration_ms=total_duration * 1000,
                throughput_per_second=throughput,
                latency_p50_ms=latency_p50,
                latency_p95_ms=latency_p95,
                latency_p99_ms=latency_p99,
                memory_usage_mb=memory_usage,
                cpu_usage_percent=cpu_usage,
                error_rate=error_rate,
                timestamp=datetime.now()
            )
            
            # Store results
            self.benchmark_results[operation_type] = metrics
            self.performance_history.append(metrics)
            
            # Generate alerts for poor performance
            if latency_p95 > 10:  # High latency alert
                self.performance_alerts.append({
                    'type': 'high_latency',
                    'operation': operation_type,
                    'latency_p95_ms': latency_p95,
                    'timestamp': datetime.now(),
                    'severity': 'WARNING'
                })
            
            if error_rate > 0.02:  # High error rate alert
                self.performance_alerts.append({
                    'type': 'high_error_rate',
                    'operation': operation_type,
                    'error_rate': error_rate,
                    'timestamp': datetime.now(),
                    'severity': 'ERROR'
                })
            
            return metrics
            
        except Exception as e:
            # Return failed metrics
            return PerformanceMetrics(
                operation_type=operation_type,
                duration_ms=(time.time() - start_time) * 1000,
                throughput_per_second=0.0,
                latency_p50_ms=0.0,
                latency_p95_ms=0.0,
                latency_p99_ms=0.0,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
                error_rate=1.0,
                timestamp=datetime.now()
            )
    
    async def test_reliability(self, test_duration_minutes: int = 5) -> ReliabilityMetrics:
        """Test system reliability over extended period."""
        start_time = time.time()
        
        try:
            # Simulate reliability testing
            await asyncio.sleep(random.uniform(0.100, 0.200))  # 100-200ms
            
            # Simulate reliability metrics
            uptime_percent = random.uniform(99.5, 99.99)  # 99.5-99.99%
            mtbf_seconds = random.uniform(3600, 86400)  # 1-24 hours
            mttr_seconds = random.uniform(30, 300)  # 30 seconds to 5 minutes
            failure_rate = random.uniform(0.001, 0.01)  # 0.1-1% per hour
            
            # Calculate availability score
            availability_score = uptime_percent / 100
            
            # Simulate operations and errors
            total_operations = random.randint(1000, 10000)
            error_count = int(total_operations * (1 - availability_score))
            
            reliability_metrics = ReliabilityMetrics(
                uptime_percent=uptime_percent,
                mean_time_between_failures_seconds=mtbf_seconds,
                mean_time_to_recovery_seconds=mttr_seconds,
                failure_rate_per_hour=failure_rate,
                availability_score=availability_score,
                error_count=error_count,
                total_operations=total_operations,
                timestamp=datetime.now()
            )
            
            # Store reliability metrics
            self.reliability_metrics['latest'] = reliability_metrics
            
            # Generate alerts for poor reliability
            if uptime_percent < 99.9:
                self.performance_alerts.append({
                    'type': 'low_uptime',
                    'uptime_percent': uptime_percent,
                    'timestamp': datetime.now(),
                    'severity': 'CRITICAL'
                })
            
            if mttr_seconds > 300:  # Recovery time > 5 minutes
                self.performance_alerts.append({
                    'type': 'slow_recovery',
                    'mttr_seconds': mttr_seconds,
                    'timestamp': datetime.now(),
                    'severity': 'WARNING'
                })
            
            return reliability_metrics
            
        except Exception as e:
            # Return failed reliability metrics
            return ReliabilityMetrics(
                uptime_percent=0.0,
                mean_time_between_failures_seconds=0.0,
                mean_time_to_recovery_seconds=0.0,
                failure_rate_per_hour=1.0,
                availability_score=0.0,
                error_count=1000,
                total_operations=1000,
                timestamp=datetime.now()
            )
    
    async def test_scalability(self, load_levels: List[str] = None) -> Dict[str, ScalabilityMetrics]:
        """Test system scalability under different load levels."""
        if load_levels is None:
            load_levels = ['LOW', 'MEDIUM', 'HIGH', 'EXTREME']
        
        scalability_results = {}
        
        try:
            for load_level in load_levels:
                # Simulate scalability testing for each load level
                await asyncio.sleep(random.uniform(0.050, 0.100))  # 50-100ms
                
                # Define load characteristics
                if load_level == 'LOW':
                    concurrent_ops = random.randint(10, 50)
                    expected_throughput = random.uniform(100, 500)
                    expected_response_time = random.uniform(1, 5)
                elif load_level == 'MEDIUM':
                    concurrent_ops = random.randint(50, 200)
                    expected_throughput = random.uniform(500, 2000)
                    expected_response_time = random.uniform(5, 15)
                elif load_level == 'HIGH':
                    concurrent_ops = random.randint(200, 1000)
                    expected_throughput = random.uniform(2000, 5000)
                    expected_response_time = random.uniform(15, 30)
                else:  # EXTREME
                    concurrent_ops = random.randint(1000, 5000)
                    expected_throughput = random.uniform(5000, 10000)
                    expected_response_time = random.uniform(30, 60)
                
                # Simulate resource utilization (ensure it's always >= 0)
                base_utilization = (concurrent_ops / 1000) * 100
                variation = random.uniform(-10, 10)
                resource_utilization = max(0, min(100, base_utilization + variation))
                
                # Detect bottlenecks
                bottleneck_detected = resource_utilization > 85 or expected_response_time > 50
                
                # Calculate scaling factor
                scaling_factor = expected_throughput / concurrent_ops if concurrent_ops > 0 else 0
                
                scalability_metrics = ScalabilityMetrics(
                    load_level=load_level,
                    concurrent_operations=concurrent_ops,
                    throughput_per_second=expected_throughput,
                    response_time_ms=expected_response_time,
                    resource_utilization_percent=resource_utilization,
                    bottleneck_detected=bottleneck_detected,
                    scaling_factor=scaling_factor,
                    timestamp=datetime.now()
                )
                
                scalability_results[load_level] = scalability_metrics
                
                # Generate alerts for bottlenecks
                if bottleneck_detected:
                    self.performance_alerts.append({
                        'type': 'bottleneck_detected',
                        'load_level': load_level,
                        'resource_utilization': resource_utilization,
                        'response_time_ms': expected_response_time,
                        'timestamp': datetime.now(),
                        'severity': 'WARNING'
                    })
            
            # Store scalability results
            self.scalability_results = scalability_results
            
            return scalability_results
            
        except Exception as e:
            # Return failed scalability results
            return {
                'error': str(e),
                'timestamp': datetime.now()
            }
    
    async def monitor_performance(self, monitoring_duration_seconds: int = 60) -> List[PerformanceMetrics]:
        """Monitor performance over time."""
        monitoring_results = []
        start_time = time.time()
        
        try:
            # Simulate continuous monitoring
            while time.time() - start_time < monitoring_duration_seconds:
                # Generate performance snapshot with properly ordered percentiles
                latency_p50 = random.uniform(1, 10)
                latency_p95 = random.uniform(latency_p50, 25)  # Ensure P95 >= P50
                latency_p99 = random.uniform(latency_p95, 50)  # Ensure P99 >= P95
                
                snapshot = PerformanceMetrics(
                    operation_type='MONITORING_SNAPSHOT',
                    duration_ms=random.uniform(100, 500),
                    throughput_per_second=random.uniform(1000, 5000),
                    latency_p50_ms=latency_p50,
                    latency_p95_ms=latency_p95,
                    latency_p99_ms=latency_p99,
                    memory_usage_mb=random.uniform(100, 500),
                    cpu_usage_percent=random.uniform(10, 40),
                    error_rate=random.uniform(0, 0.02),
                    timestamp=datetime.now()
                )
                
                monitoring_results.append(snapshot)
                
                # Simulate monitoring interval
                await asyncio.sleep(random.uniform(0.010, 0.030))  # 10-30ms
                
                # Check if we should continue
                if time.time() - start_time >= monitoring_duration_seconds:
                    break
            
            return monitoring_results
            
        except Exception as e:
            # Return empty results on error
            return []
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        try:
            # Calculate aggregate metrics
            if self.performance_history:
                avg_throughput = statistics.mean([m.throughput_per_second for m in self.performance_history])
                avg_latency_p95 = statistics.mean([m.latency_p95_ms for m in self.performance_history])
                avg_error_rate = statistics.mean([m.error_rate for m in self.performance_history])
            else:
                avg_throughput = 0.0
                avg_latency_p95 = 0.0
                avg_error_rate = 0.0
            
            # Get latest reliability metrics
            latest_reliability = self.reliability_metrics.get('latest')
            
            # Get scalability summary
            scalability_summary = {}
            for load_level, metrics in self.scalability_results.items():
                scalability_summary[load_level] = {
                    'throughput': metrics.throughput_per_second,
                    'response_time_ms': metrics.response_time_ms,
                    'bottleneck_detected': metrics.bottleneck_detected
                }
            
            report = {
                'timestamp': datetime.now(),
                'performance_summary': {
                    'avg_throughput_per_second': avg_throughput,
                    'avg_latency_p95_ms': avg_latency_p95,
                    'avg_error_rate': avg_error_rate,
                    'total_benchmarks': len(self.benchmark_results)
                },
                'reliability_summary': {
                    'uptime_percent': latest_reliability.uptime_percent if latest_reliability else 0.0,
                    'availability_score': latest_reliability.availability_score if latest_reliability else 0.0,
                    'mtbf_seconds': latest_reliability.mean_time_between_failures_seconds if latest_reliability else 0.0
                },
                'scalability_summary': scalability_summary,
                'performance_alerts': self.performance_alerts[-10:],  # Last 10 alerts
                'benchmark_results_count': len(self.benchmark_results),
                'performance_history_count': len(self.performance_history)
            }
            
            return report
            
        except Exception as e:
            return {'error': str(e)}
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return {
            'benchmark_results_count': len(self.benchmark_results),
            'performance_history_count': len(self.performance_history),
            'reliability_metrics_count': len(self.reliability_metrics),
            'scalability_results_count': len(self.scalability_results),
            'performance_alerts_count': len(self.performance_alerts)
        }


class TestPerformanceReliabilityInfrastructure:
    """Test performance and reliability infrastructure."""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_performance_benchmarking(self):
        """Test performance benchmarking for different operation types."""
        with monitoring_context("performance_benchmarking") as logger:
            logger.log_test_event("Testing performance benchmarking")
            
            # Create test components
            benchmark_system = MockPerformanceBenchmark()
            
            # Test different operation types
            operation_types = ['SIGNAL_GENERATION', 'RISK_VALIDATION', 'ORDER_EXECUTION', 'PORTFOLIO_UPDATE']
            benchmark_results = []
            
            for operation_type in operation_types:
                # Run benchmark with 50 iterations
                metrics = await benchmark_system.run_performance_benchmark(operation_type, iterations=50)
                benchmark_results.append(metrics)
                
                # Validate metrics
                assert metrics.operation_type == operation_type
                assert metrics.duration_ms > 0
                assert metrics.throughput_per_second > 0
                assert metrics.latency_p50_ms > 0
                assert metrics.latency_p95_ms >= metrics.latency_p50_ms
                assert metrics.latency_p99_ms >= metrics.latency_p95_ms
                assert 0 <= metrics.error_rate <= 1
                assert metrics.memory_usage_mb > 0
                assert 0 <= metrics.cpu_usage_percent <= 100
            
            # Get performance stats
            stats = benchmark_system.get_performance_stats()
            
            logger.log_test_event("Performance benchmarking validated", {
                'operation_types_tested': len(operation_types),
                'benchmark_results': len(benchmark_results),
                'avg_throughput': statistics.mean([m.throughput_per_second for m in benchmark_results]),
                'avg_latency_p95': statistics.mean([m.latency_p95_ms for m in benchmark_results]),
                'performance_alerts': len(benchmark_system.performance_alerts)
            })
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_reliability_testing(self):
        """Test system reliability over extended period."""
        with monitoring_context("reliability_testing") as logger:
            logger.log_test_event("Testing reliability")
            
            # Create test components
            benchmark_system = MockPerformanceBenchmark()
            
            # Test reliability for 5 minutes (simulated)
            reliability_metrics = await benchmark_system.test_reliability(test_duration_minutes=5)
            
            # Validate reliability metrics
            assert 0 <= reliability_metrics.uptime_percent <= 100
            assert reliability_metrics.mean_time_between_failures_seconds > 0
            assert reliability_metrics.mean_time_to_recovery_seconds > 0
            assert 0 <= reliability_metrics.failure_rate_per_hour <= 1
            assert 0 <= reliability_metrics.availability_score <= 1
            assert reliability_metrics.error_count >= 0
            assert reliability_metrics.total_operations > 0
            assert reliability_metrics.error_count <= reliability_metrics.total_operations
            
            # Validate relationships
            calculated_availability = reliability_metrics.uptime_percent / 100
            assert abs(reliability_metrics.availability_score - calculated_availability) < 0.01
            
            # Get performance stats
            stats = benchmark_system.get_performance_stats()
            
            logger.log_test_event("Reliability testing validated", {
                'uptime_percent': reliability_metrics.uptime_percent,
                'availability_score': reliability_metrics.availability_score,
                'mtbf_seconds': reliability_metrics.mean_time_between_failures_seconds,
                'mttr_seconds': reliability_metrics.mean_time_to_recovery_seconds,
                'failure_rate_per_hour': reliability_metrics.failure_rate_per_hour,
                'total_operations': reliability_metrics.total_operations,
                'error_count': reliability_metrics.error_count,
                'performance_alerts': len(benchmark_system.performance_alerts)
            })
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_scalability_validation(self):
        """Test system scalability under different load levels."""
        with monitoring_context("scalability_validation") as logger:
            logger.log_test_event("Testing scalability validation")
            
            # Create test components
            benchmark_system = MockPerformanceBenchmark()
            
            # Test scalability under different load levels
            load_levels = ['LOW', 'MEDIUM', 'HIGH', 'EXTREME']
            scalability_results = await benchmark_system.test_scalability(load_levels)
            
            # Validate scalability results
            assert len(scalability_results) == len(load_levels)
            
            for load_level, metrics in scalability_results.items():
                assert metrics.load_level == load_level
                assert metrics.concurrent_operations > 0
                assert metrics.throughput_per_second > 0
                assert metrics.response_time_ms > 0
                assert 0 <= metrics.resource_utilization_percent <= 100
                assert isinstance(metrics.bottleneck_detected, bool)
                assert metrics.scaling_factor > 0
            
            # Validate load progression
            load_progression = []
            for load_level in load_levels:
                if load_level in scalability_results:
                    metrics = scalability_results[load_level]
                    load_progression.append({
                        'load_level': load_level,
                        'concurrent_ops': metrics.concurrent_operations,
                        'throughput': metrics.throughput_per_second,
                        'response_time': metrics.response_time_ms
                    })
            
            # Get performance stats
            stats = benchmark_system.get_performance_stats()
            
            logger.log_test_event("Scalability validation validated", {
                'load_levels_tested': len(load_levels),
                'scalability_results': len(scalability_results),
                'bottlenecks_detected': sum(1 for m in scalability_results.values() if m.bottleneck_detected),
                'avg_scaling_factor': statistics.mean([m.scaling_factor for m in scalability_results.values()]),
                'performance_alerts': len(benchmark_system.performance_alerts)
            })
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_performance_monitoring(self):
        """Test continuous performance monitoring."""
        with monitoring_context("performance_monitoring") as logger:
            logger.log_test_event("Testing performance monitoring")
            
            # Create test components
            benchmark_system = MockPerformanceBenchmark()
            
            # Monitor performance for 30 seconds (simulated)
            monitoring_results = await benchmark_system.monitor_performance(monitoring_duration_seconds=30)
            
            # Validate monitoring results
            assert len(monitoring_results) > 0
            
            for snapshot in monitoring_results:
                assert snapshot.operation_type == 'MONITORING_SNAPSHOT'
                assert snapshot.duration_ms > 0
                assert snapshot.throughput_per_second > 0
                assert snapshot.latency_p50_ms > 0
                assert snapshot.latency_p95_ms >= snapshot.latency_p50_ms
                assert snapshot.latency_p99_ms >= snapshot.latency_p95_ms
                assert snapshot.memory_usage_mb > 0
                assert 0 <= snapshot.cpu_usage_percent <= 100
                assert 0 <= snapshot.error_rate <= 1
            
            # Calculate monitoring statistics
            if monitoring_results:
                avg_throughput = statistics.mean([m.throughput_per_second for m in monitoring_results])
                avg_latency_p95 = statistics.mean([m.latency_p95_ms for m in monitoring_results])
                avg_memory_usage = statistics.mean([m.memory_usage_mb for m in monitoring_results])
                avg_cpu_usage = statistics.mean([m.cpu_usage_percent for m in monitoring_results])
                avg_error_rate = statistics.mean([m.error_rate for m in monitoring_results])
            else:
                avg_throughput = avg_latency_p95 = avg_memory_usage = avg_cpu_usage = avg_error_rate = 0.0
            
            # Get performance stats
            stats = benchmark_system.get_performance_stats()
            
            logger.log_test_event("Performance monitoring validated", {
                'monitoring_snapshots': len(monitoring_results),
                'avg_throughput_per_second': avg_throughput,
                'avg_latency_p95_ms': avg_latency_p95,
                'avg_memory_usage_mb': avg_memory_usage,
                'avg_cpu_usage_percent': avg_cpu_usage,
                'avg_error_rate': avg_error_rate,
                'monitoring_duration_seconds': 30
            })
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_performance_thresholds(self):
        """Test performance threshold monitoring and alerting."""
        with monitoring_context("performance_thresholds") as logger:
            logger.log_test_event("Testing performance thresholds")
            
            # Create test components
            benchmark_system = MockPerformanceBenchmark()
            
            # Run benchmarks that may trigger alerts
            operation_types = ['SIGNAL_GENERATION', 'ORDER_EXECUTION']
            
            for operation_type in operation_types:
                # Run benchmark with higher chance of poor performance
                metrics = await benchmark_system.run_performance_benchmark(operation_type, iterations=100)
                
                # Validate metrics
                assert metrics.operation_type == operation_type
                assert metrics.duration_ms > 0
                assert metrics.throughput_per_second > 0
            
            # Check for performance alerts
            performance_alerts = benchmark_system.performance_alerts
            
            # Validate alert structure
            for alert in performance_alerts:
                assert 'type' in alert
                assert 'timestamp' in alert
                assert 'severity' in alert
                assert alert['severity'] in ['WARNING', 'ERROR', 'CRITICAL']
            
            # Categorize alerts
            alert_types = {}
            for alert in performance_alerts:
                alert_type = alert['type']
                if alert_type not in alert_types:
                    alert_types[alert_type] = 0
                alert_types[alert_type] += 1
            
            # Get performance stats
            stats = benchmark_system.get_performance_stats()
            
            logger.log_test_event("Performance thresholds validated", {
                'operation_types_tested': len(operation_types),
                'total_alerts': len(performance_alerts),
                'alert_types': alert_types,
                'benchmark_results': stats['benchmark_results_count']
            })
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_comprehensive_performance_analysis(self):
        """Test comprehensive performance analysis and reporting."""
        with monitoring_context("comprehensive_performance_analysis") as logger:
            logger.log_test_event("Testing comprehensive performance analysis")
            
            # Create test components
            benchmark_system = MockPerformanceBenchmark()
            
            # Run comprehensive performance tests
            # 1. Performance benchmarks
            operation_types = ['SIGNAL_GENERATION', 'RISK_VALIDATION', 'ORDER_EXECUTION']
            for operation_type in operation_types:
                await benchmark_system.run_performance_benchmark(operation_type, iterations=50)
            
            # 2. Reliability testing
            reliability_metrics = await benchmark_system.test_reliability(test_duration_minutes=5)
            
            # 3. Scalability testing
            scalability_results = await benchmark_system.test_scalability(['LOW', 'MEDIUM', 'HIGH'])
            
            # 4. Performance monitoring
            monitoring_results = await benchmark_system.monitor_performance(monitoring_duration_seconds=30)
            
            # Generate comprehensive performance report
            performance_report = benchmark_system.generate_performance_report()
            
            # Validate performance report
            assert 'timestamp' in performance_report
            assert 'performance_summary' in performance_report
            assert 'reliability_summary' in performance_report
            assert 'scalability_summary' in performance_report
            assert 'performance_alerts' in performance_report
            
            # Validate performance summary
            perf_summary = performance_report['performance_summary']
            assert 'avg_throughput_per_second' in perf_summary
            assert 'avg_latency_p95_ms' in perf_summary
            assert 'avg_error_rate' in perf_summary
            assert 'total_benchmarks' in perf_summary
            
            # Validate reliability summary
            rel_summary = performance_report['reliability_summary']
            assert 'uptime_percent' in rel_summary
            assert 'availability_score' in rel_summary
            assert 'mtbf_seconds' in rel_summary
            
            # Validate scalability summary
            scal_summary = performance_report['scalability_summary']
            assert len(scal_summary) > 0
            
            # Get performance stats
            stats = benchmark_system.get_performance_stats()
            
            logger.log_test_event("Comprehensive performance analysis validated", {
                'benchmark_results': stats['benchmark_results_count'],
                'performance_history': stats['performance_history_count'],
                'reliability_metrics': stats['reliability_metrics_count'],
                'scalability_results': stats['scalability_results_count'],
                'performance_alerts': stats['performance_alerts_count'],
                'monitoring_snapshots': len(monitoring_results),
                'uptime_percent': rel_summary['uptime_percent'],
                'avg_throughput': perf_summary['avg_throughput_per_second']
            })


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s", "-m", "performance"]) 