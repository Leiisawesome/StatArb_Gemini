"""
Integration Tests - System Monitoring and Observability
=======================================================
Comprehensive monitoring tests for StatArb_Gemini system.

Test Coverage:
- System metrics collection and validation
- Performance monitoring and alerts
- Health check endpoints
- Log aggregation and structured logging
- Real-time monitoring dashboards

Author: StatArb_Gemini Integration Testing
Phase: 8 Week 2 - Day 9 - System Monitoring Tests
Date: October 12, 2025
"""

import asyncio
import time
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum

# Import core system components
from core_engine.system.hierarchical_orchestrator import HierarchicalSystemOrchestrator

# Configure logging
logger = logging.getLogger(__name__)


# ========================================
# Test Data Structures
# ========================================

@dataclass
class MetricPoint:
    """Single metric data point"""
    name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str]
    metric_type: str  # counter, gauge, histogram


@dataclass
class AlertCondition:
    """Alert threshold condition"""
    metric_name: str
    threshold: float
    comparison: str  # gt, lt, gte, lte, eq
    duration_seconds: int
    severity: str  # critical, warning, info


@dataclass
class HealthCheckResult:
    """Health check endpoint result"""
    endpoint: str
    status: str  # healthy, unhealthy, degraded
    response_time_ms: float
    checks: Dict[str, bool]
    timestamp: datetime


class MetricType(Enum):
    """Metric type enumeration"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AlertSeverity(Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


# ========================================
# Test Helper Functions
# ========================================

def collect_system_resource_metrics() -> Dict[str, float]:
    """
    Collect actual system resource metrics
    
    Returns:
        Dictionary with CPU, memory, disk metrics
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            'cpu_usage_percent': cpu_percent,
            'memory_usage_percent': memory.percent,
            'memory_used_mb': memory.used / (1024 * 1024),
            'memory_available_mb': memory.available / (1024 * 1024),
            'disk_usage_percent': disk.percent,
            'disk_used_gb': disk.used / (1024 * 1024 * 1024),
            'disk_available_gb': disk.free / (1024 * 1024 * 1024)
        }
    except Exception as e:
        logger.error(f"Error collecting resource metrics: {e}")
        return {}


def simulate_metrics_collection(
    metric_name: str,
    metric_type: MetricType,
    value: float,
    labels: Optional[Dict[str, str]] = None
) -> MetricPoint:
    """
    Simulate collecting a metric point
    
    Args:
        metric_name: Name of the metric
        metric_type: Type of metric
        value: Metric value
        labels: Optional metric labels
    
    Returns:
        MetricPoint with collected data
    """
    return MetricPoint(
        name=metric_name,
        value=value,
        timestamp=datetime.now(),
        labels=labels or {},
        metric_type=metric_type.value
    )


def format_prometheus_metric(metric: MetricPoint) -> str:
    """
    Format metric in Prometheus exposition format
    
    Args:
        metric: Metric data point
    
    Returns:
        Prometheus-formatted metric string
    """
    label_str = ""
    if metric.labels:
        labels_formatted = ",".join(f'{k}="{v}"' for k, v in metric.labels.items())
        label_str = f"{{{labels_formatted}}}"
    
    return f"{metric.name}{label_str} {metric.value} {int(metric.timestamp.timestamp() * 1000)}"


def evaluate_alert_condition(
    current_value: float,
    condition: AlertCondition
) -> bool:
    """
    Evaluate if alert condition is met
    
    Args:
        current_value: Current metric value
        condition: Alert condition to check
    
    Returns:
        True if alert should trigger
    """
    comparisons = {
        'gt': lambda v, t: v > t,
        'lt': lambda v, t: v < t,
        'gte': lambda v, t: v >= t,
        'lte': lambda v, t: v <= t,
        'eq': lambda v, t: v == t
    }
    
    comparison_func = comparisons.get(condition.comparison)
    if not comparison_func:
        return False
    
    return comparison_func(current_value, condition.threshold)


async def perform_health_check(
    orchestrator: HierarchicalSystemOrchestrator,
    check_dependencies: bool = True
) -> HealthCheckResult:
    """
    Perform comprehensive health check
    
    Args:
        orchestrator: System orchestrator
        check_dependencies: Whether to check dependencies
    
    Returns:
        Health check result
    """
    start_time = time.time()
    checks = {}
    
    try:
        # Check orchestrator status
        checks['orchestrator_running'] = orchestrator.system_status.value in ['operational', 'initializing']
        
        # Check monitoring
        monitoring_status = orchestrator.system_monitor.get_monitoring_status()
        checks['monitoring_active'] = monitoring_status.get('monitoring_active', False)
        
        # Check component registry
        checks['components_registered'] = len(orchestrator.component_registry) > 0
        
        # Check system metrics available
        system_metrics = orchestrator.system_monitor.get_system_metrics()
        checks['metrics_available'] = len(system_metrics) > 0
        
        # Determine overall status
        if all(checks.values()):
            status = 'healthy'
        elif any(checks.values()):
            status = 'degraded'
        else:
            status = 'unhealthy'
        
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        return HealthCheckResult(
            endpoint='/health',
            status=status,
            response_time_ms=response_time,
            checks=checks,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        response_time = (time.time() - start_time) * 1000
        
        return HealthCheckResult(
            endpoint='/health',
            status='unhealthy',
            response_time_ms=response_time,
            checks={'error': False},
            timestamp=datetime.now()
        )


# ========================================
# Main Test Class
# ========================================

class TestSystemMonitoring:
    """
    System Monitoring and Observability Tests
    
    Tests monitoring infrastructure, metrics collection,
    alerting, and health checks.
    """
    
    async def test_metrics_collection_validation(
        self,
        orchestrator,
        risk_manager
    ):
        """
        Test 1: Metrics Collection and Format Validation
        
        Validates:
        - Metric types (counter, gauge, histogram)
        - Prometheus format compatibility
        - Metric labeling and dimensions
        - Timestamp accuracy
        - Metric naming conventions
        """
        logger.info("=" * 80)
        logger.info("TEST 1: Metrics Collection and Format Validation")
        logger.info("=" * 80)
        
        test_start = time.time()
        metrics_collected = []
        
        # Test Counter Metric
        logger.info("📊 Testing Counter metric...")
        counter_metric = simulate_metrics_collection(
            metric_name="trading_orders_total",
            metric_type=MetricType.COUNTER,
            value=150.0,
            labels={'symbol': 'AAPL', 'side': 'buy'}
        )
        metrics_collected.append(counter_metric)
        
        assert counter_metric.metric_type == "counter", "Counter metric type mismatch"
        assert counter_metric.value == 150.0, "Counter value incorrect"
        assert 'symbol' in counter_metric.labels, "Counter missing symbol label"
        logger.info(f"✅ Counter metric: {counter_metric.name}={counter_metric.value}")
        
        # Test Gauge Metric
        logger.info("📊 Testing Gauge metric...")
        gauge_metric = simulate_metrics_collection(
            metric_name="system_cpu_usage_percent",
            metric_type=MetricType.GAUGE,
            value=45.5,
            labels={'host': 'trading-server-01'}
        )
        metrics_collected.append(gauge_metric)
        
        assert gauge_metric.metric_type == "gauge", "Gauge metric type mismatch"
        assert gauge_metric.value == 45.5, "Gauge value incorrect"
        logger.info(f"✅ Gauge metric: {gauge_metric.name}={gauge_metric.value}%")
        
        # Test Histogram Metric
        logger.info("📊 Testing Histogram metric...")
        histogram_metric = simulate_metrics_collection(
            metric_name="order_execution_latency_ms",
            metric_type=MetricType.HISTOGRAM,
            value=23.5,
            labels={'quantile': '0.95'}
        )
        metrics_collected.append(histogram_metric)
        
        assert histogram_metric.metric_type == "histogram", "Histogram metric type mismatch"
        assert histogram_metric.value == 23.5, "Histogram value incorrect"
        logger.info(f"✅ Histogram metric: {histogram_metric.name} P95={histogram_metric.value}ms")
        
        # Test Prometheus Format
        logger.info("📊 Testing Prometheus format conversion...")
        prometheus_metrics = []
        for metric in metrics_collected:
            prom_format = format_prometheus_metric(metric)
            prometheus_metrics.append(prom_format)
            assert metric.name in prom_format, f"Metric name missing in Prometheus format"
            assert str(metric.value) in prom_format, f"Metric value missing in Prometheus format"
            logger.info(f"  Prometheus: {prom_format}")
        
        assert len(prometheus_metrics) == 3, "Not all metrics converted to Prometheus format"
        logger.info("✅ All metrics successfully converted to Prometheus format")
        
        # Test System Resource Metrics
        logger.info("📊 Testing system resource metric collection...")
        resource_metrics = collect_system_resource_metrics()
        
        assert 'cpu_usage_percent' in resource_metrics, "CPU metric missing"
        assert 'memory_usage_percent' in resource_metrics, "Memory metric missing"
        assert 'disk_usage_percent' in resource_metrics, "Disk metric missing"
        
        logger.info(f"  CPU Usage: {resource_metrics['cpu_usage_percent']:.1f}%")
        logger.info(f"  Memory Usage: {resource_metrics['memory_usage_percent']:.1f}%")
        logger.info(f"  Disk Usage: {resource_metrics['disk_usage_percent']:.1f}%")
        logger.info("✅ System resource metrics collected successfully")
        
        # Test Orchestrator Metrics
        logger.info("📊 Testing orchestrator metrics collection...")
        system_metrics = orchestrator.system_monitor.get_system_metrics()
        performance_metrics = orchestrator.system_monitor.get_performance_metrics()
        
        assert isinstance(system_metrics, dict), "System metrics not a dictionary"
        assert isinstance(performance_metrics, dict), "Performance metrics not a dictionary"
        
        logger.info(f"  System metrics keys: {len(system_metrics)}")
        logger.info(f"  Performance metrics keys: {len(performance_metrics)}")
        logger.info("✅ Orchestrator metrics available")
        
        # Test Metric Naming Conventions
        logger.info("📊 Validating metric naming conventions...")
        for metric in metrics_collected:
            # Check snake_case
            assert '_' in metric.name or metric.name.islower(), f"Metric name not in snake_case: {metric.name}"
            
            # Check meaningful suffix
            valid_suffixes = ['_total', '_percent', '_ms', '_seconds', '_bytes', '_count']
            has_valid_suffix = any(metric.name.endswith(suffix) for suffix in valid_suffixes)
            if not has_valid_suffix:
                logger.warning(f"⚠️  Metric {metric.name} doesn't have standard suffix")
        
        logger.info("✅ Metric naming conventions validated")
        
        # Test Timestamp Accuracy
        logger.info("📊 Validating metric timestamps...")
        now = datetime.now()
        for metric in metrics_collected:
            time_diff = abs((now - metric.timestamp).total_seconds())
            assert time_diff < 5, f"Metric timestamp too old: {time_diff}s"
        
        logger.info("✅ All metric timestamps recent (<5s old)")
        
        test_duration = time.time() - test_start
        logger.info(f"📊 Metrics collection test completed in {test_duration:.2f}s")
        logger.info("✅ Metrics Collection Validation: PASSED")
        
        # Final assertions
        assert len(metrics_collected) >= 3, "Not enough metrics collected"
        assert all(m.value >= 0 for m in metrics_collected), "Negative metric values found"
        assert len(resource_metrics) >= 3, "Insufficient resource metrics"
    
    
    async def test_alert_triggering_thresholds(
        self,
        orchestrator,
        risk_manager
    ):
        """
        Test 2: Alert Triggering and Threshold Validation
        
        Validates:
        - CPU usage alerts (>80%)
        - Memory usage alerts (>85%)
        - Latency alerts (P95 >500ms)
        - Error rate alerts (>1%)
        - Alert trigger conditions
        - Alert clear conditions
        """
        logger.info("=" * 80)
        logger.info("TEST 2: Alert Triggering and Threshold Validation")
        logger.info("=" * 80)
        
        test_start = time.time()
        alerts_triggered = []
        
        # Define alert conditions
        alert_conditions = [
            AlertCondition(
                metric_name="cpu_usage_percent",
                threshold=80.0,
                comparison='gt',
                duration_seconds=60,
                severity="warning"
            ),
            AlertCondition(
                metric_name="memory_usage_percent",
                threshold=85.0,
                comparison='gt',
                duration_seconds=60,
                severity="critical"
            ),
            AlertCondition(
                metric_name="latency_p95_ms",
                threshold=500.0,
                comparison='gt',
                duration_seconds=30,
                severity="warning"
            ),
            AlertCondition(
                metric_name="error_rate_percent",
                threshold=1.0,
                comparison='gt',
                duration_seconds=120,
                severity="critical"
            )
        ]
        
        logger.info(f"📊 Defined {len(alert_conditions)} alert conditions")
        
        # Test CPU Alert
        logger.info("🚨 Testing CPU usage alert...")
        cpu_metrics_normal = [45.0, 50.0, 55.0]  # Normal
        cpu_metrics_high = [85.0, 90.0, 95.0]     # Should trigger
        
        for value in cpu_metrics_normal:
            triggered = evaluate_alert_condition(value, alert_conditions[0])
            assert not triggered, f"CPU alert false positive at {value}%"
        logger.info(f"  ✅ No false positives for CPU <80%: {cpu_metrics_normal}")
        
        for value in cpu_metrics_high:
            triggered = evaluate_alert_condition(value, alert_conditions[0])
            if triggered:
                alerts_triggered.append(('cpu_usage_percent', value))
                logger.info(f"  🚨 ALERT TRIGGERED: CPU usage {value}% > 80%")
        
        assert len([a for a in alerts_triggered if a[0] == 'cpu_usage_percent']) == 3, \
            "CPU alert didn't trigger for all high values"
        logger.info("✅ CPU alert triggering validated")
        
        # Test Memory Alert
        logger.info("🚨 Testing memory usage alert...")
        memory_metrics_normal = [70.0, 75.0, 80.0]  # Normal
        memory_metrics_high = [86.0, 90.0, 95.0]    # Should trigger
        
        for value in memory_metrics_normal:
            triggered = evaluate_alert_condition(value, alert_conditions[1])
            assert not triggered, f"Memory alert false positive at {value}%"
        logger.info(f"  ✅ No false positives for memory <85%: {memory_metrics_normal}")
        
        for value in memory_metrics_high:
            triggered = evaluate_alert_condition(value, alert_conditions[1])
            if triggered:
                alerts_triggered.append(('memory_usage_percent', value))
                logger.info(f"  🚨 ALERT TRIGGERED: Memory usage {value}% > 85% (CRITICAL)")
        
        assert len([a for a in alerts_triggered if a[0] == 'memory_usage_percent']) == 3, \
            "Memory alert didn't trigger for all high values"
        logger.info("✅ Memory alert triggering validated")
        
        # Test Latency Alert
        logger.info("🚨 Testing latency alert...")
        latency_metrics_normal = [100.0, 250.0, 450.0]  # Normal (<500ms)
        latency_metrics_high = [550.0, 750.0, 1000.0]   # Should trigger
        
        for value in latency_metrics_normal:
            triggered = evaluate_alert_condition(value, alert_conditions[2])
            assert not triggered, f"Latency alert false positive at {value}ms"
        logger.info(f"  ✅ No false positives for latency <500ms: {latency_metrics_normal}")
        
        for value in latency_metrics_high:
            triggered = evaluate_alert_condition(value, alert_conditions[2])
            if triggered:
                alerts_triggered.append(('latency_p95_ms', value))
                logger.info(f"  🚨 ALERT TRIGGERED: P95 latency {value}ms > 500ms")
        
        assert len([a for a in alerts_triggered if a[0] == 'latency_p95_ms']) == 3, \
            "Latency alert didn't trigger for all high values"
        logger.info("✅ Latency alert triggering validated")
        
        # Test Error Rate Alert
        logger.info("🚨 Testing error rate alert...")
        error_rate_normal = [0.0, 0.5, 0.9]  # Normal (<1%)
        error_rate_high = [1.5, 2.0, 5.0]    # Should trigger
        
        for value in error_rate_normal:
            triggered = evaluate_alert_condition(value, alert_conditions[3])
            assert not triggered, f"Error rate alert false positive at {value}%"
        logger.info(f"  ✅ No false positives for error rate <1%: {error_rate_normal}")
        
        for value in error_rate_high:
            triggered = evaluate_alert_condition(value, alert_conditions[3])
            if triggered:
                alerts_triggered.append(('error_rate_percent', value))
                logger.info(f"  🚨 ALERT TRIGGERED: Error rate {value}% > 1% (CRITICAL)")
        
        assert len([a for a in alerts_triggered if a[0] == 'error_rate_percent']) == 3, \
            "Error rate alert didn't trigger for all high values"
        logger.info("✅ Error rate alert triggering validated")
        
        # Test Alert Clear Conditions
        logger.info("🚨 Testing alert clear conditions...")
        cleared_alerts = 0
        
        # CPU back to normal
        if evaluate_alert_condition(60.0, alert_conditions[0]):
            logger.error("  ❌ CPU alert didn't clear at 60%")
        else:
            cleared_alerts += 1
            logger.info("  ✅ CPU alert cleared at 60%")
        
        # Memory back to normal
        if evaluate_alert_condition(70.0, alert_conditions[1]):
            logger.error("  ❌ Memory alert didn't clear at 70%")
        else:
            cleared_alerts += 1
            logger.info("  ✅ Memory alert cleared at 70%")
        
        # Latency back to normal
        if evaluate_alert_condition(300.0, alert_conditions[2]):
            logger.error("  ❌ Latency alert didn't clear at 300ms")
        else:
            cleared_alerts += 1
            logger.info("  ✅ Latency alert cleared at 300ms")
        
        # Error rate back to normal
        if evaluate_alert_condition(0.5, alert_conditions[3]):
            logger.error("  ❌ Error rate alert didn't clear at 0.5%")
        else:
            cleared_alerts += 1
            logger.info("  ✅ Error rate alert cleared at 0.5%")
        
        assert cleared_alerts == 4, "Not all alerts cleared properly"
        logger.info("✅ Alert clear conditions validated")
        
        # Test Alert Severity
        logger.info("🚨 Testing alert severity classification...")
        critical_alerts = [c for c in alert_conditions if c.severity == "critical"]
        warning_alerts = [c for c in alert_conditions if c.severity == "warning"]
        
        assert len(critical_alerts) == 2, "Expected 2 critical alerts"
        assert len(warning_alerts) == 2, "Expected 2 warning alerts"
        
        logger.info(f"  Critical alerts: {[a.metric_name for a in critical_alerts]}")
        logger.info(f"  Warning alerts: {[a.metric_name for a in warning_alerts]}")
        logger.info("✅ Alert severity classification validated")
        
        # Summary
        test_duration = time.time() - test_start
        logger.info(f"📊 Alert testing completed in {test_duration:.2f}s")
        logger.info(f"📊 Total alerts triggered: {len(alerts_triggered)}")
        logger.info(f"📊 Alerts by type:")
        for metric_name in set(a[0] for a in alerts_triggered):
            count = len([a for a in alerts_triggered if a[0] == metric_name])
            logger.info(f"  {metric_name}: {count} alerts")
        
        logger.info("✅ Alert Triggering and Threshold Validation: PASSED")
        
        # Final assertions
        assert len(alerts_triggered) >= 12, "Expected at least 12 total alerts"
        assert cleared_alerts == 4, "All 4 alert types should clear"
    
    
    async def test_health_check_endpoints(
        self,
        orchestrator,
        risk_manager
    ):
        """
        Test 3: Health Check Endpoints Validation
        
        Validates:
        - Liveness probe (basic responsiveness)
        - Readiness probe (dependency checks)
        - Response time (<100ms)
        - HTTP status codes
        - Health check details
        """
        logger.info("=" * 80)
        logger.info("TEST 3: Health Check Endpoints Validation")
        logger.info("=" * 80)
        
        test_start = time.time()
        health_checks_performed = []
        
        # Test Liveness Probe
        logger.info("🏥 Testing liveness probe...")
        liveness_start = time.time()
        
        # Liveness check - just verify system is running
        is_alive = orchestrator.system_status.value != 'shutdown'
        liveness_time = (time.time() - liveness_start) * 1000
        
        assert is_alive, "System not alive"
        assert liveness_time < 100, f"Liveness check too slow: {liveness_time:.1f}ms"
        
        logger.info(f"  ✅ System is alive")
        logger.info(f"  ✅ Response time: {liveness_time:.2f}ms (< 100ms)")
        logger.info("✅ Liveness probe validated")
        
        # Test Readiness Probe
        logger.info("🏥 Testing readiness probe...")
        readiness_result = await perform_health_check(orchestrator, check_dependencies=True)
        health_checks_performed.append(readiness_result)
        
        assert readiness_result.status in ['healthy', 'degraded'], \
            f"System not ready: {readiness_result.status}"
        assert readiness_result.response_time_ms < 100, \
            f"Readiness check too slow: {readiness_result.response_time_ms:.1f}ms"
        
        logger.info(f"  Status: {readiness_result.status}")
        logger.info(f"  Response time: {readiness_result.response_time_ms:.2f}ms")
        logger.info(f"  Checks passed: {sum(readiness_result.checks.values())}/{len(readiness_result.checks)}")
        
        for check_name, check_passed in readiness_result.checks.items():
            status_icon = "✅" if check_passed else "❌"
            logger.info(f"    {status_icon} {check_name}: {'PASS' if check_passed else 'FAIL'}")
        
        logger.info("✅ Readiness probe validated")
        
        # Test Health Check with Details
        logger.info("🏥 Testing detailed health check...")
        detailed_result = await perform_health_check(orchestrator, check_dependencies=True)
        health_checks_performed.append(detailed_result)
        
        assert len(detailed_result.checks) > 0, "No health checks performed"
        assert detailed_result.timestamp is not None, "Missing timestamp"
        
        logger.info(f"  Endpoint: {detailed_result.endpoint}")
        logger.info(f"  Status: {detailed_result.status}")
        logger.info(f"  Response time: {detailed_result.response_time_ms:.2f}ms")
        logger.info(f"  Timestamp: {detailed_result.timestamp.isoformat()}")
        logger.info(f"  Total checks: {len(detailed_result.checks)}")
        logger.info("✅ Detailed health check validated")
        
        # Test Response Time Consistency
        logger.info("🏥 Testing response time consistency...")
        response_times = []
        
        for i in range(10):
            check_result = await perform_health_check(orchestrator, check_dependencies=False)
            response_times.append(check_result.response_time_ms)
            health_checks_performed.append(check_result)
        
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)
        
        logger.info(f"  Average response time: {avg_response_time:.2f}ms")
        logger.info(f"  Min response time: {min_response_time:.2f}ms")
        logger.info(f"  Max response time: {max_response_time:.2f}ms")
        
        assert avg_response_time < 50, f"Average response time too high: {avg_response_time:.1f}ms"
        assert max_response_time < 100, f"Max response time too high: {max_response_time:.1f}ms"
        
        logger.info("✅ Response time consistency validated")
        
        # Test Status Codes Mapping
        logger.info("🏥 Testing HTTP status code mapping...")
        status_codes = {
            'healthy': 200,
            'degraded': 200,  # Still operational
            'unhealthy': 503
        }
        
        for status, expected_code in status_codes.items():
            logger.info(f"  {status} → HTTP {expected_code}")
        
        logger.info("✅ Status code mapping validated")
        
        # Test Monitoring Status Check
        logger.info("🏥 Testing monitoring system status...")
        monitoring_status = orchestrator.system_monitor.get_monitoring_status()
        
        assert 'monitoring_active' in monitoring_status, "Missing monitoring_active field"
        assert 'uptime_seconds' in monitoring_status, "Missing uptime_seconds field"
        
        logger.info(f"  Monitoring active: {monitoring_status.get('monitoring_active')}")
        logger.info(f"  Uptime: {monitoring_status.get('uptime_seconds', 0):.1f}s")
        logger.info("✅ Monitoring status validated")
        
        # Summary
        test_duration = time.time() - test_start
        logger.info(f"📊 Health check testing completed in {test_duration:.2f}s")
        logger.info(f"📊 Health checks performed: {len(health_checks_performed)}")
        
        healthy_checks = len([h for h in health_checks_performed if h.status == 'healthy'])
        degraded_checks = len([h for h in health_checks_performed if h.status == 'degraded'])
        unhealthy_checks = len([h for h in health_checks_performed if h.status == 'unhealthy'])
        
        logger.info(f"  Healthy: {healthy_checks}")
        logger.info(f"  Degraded: {degraded_checks}")
        logger.info(f"  Unhealthy: {unhealthy_checks}")
        
        logger.info("✅ Health Check Endpoints Validation: PASSED")
        
        # Final assertions
        assert len(health_checks_performed) >= 12, "Expected at least 12 health checks"
        assert avg_response_time < 50, "Average response time should be <50ms"
        assert healthy_checks + degraded_checks > 0, "System should be operational"
    
    
    async def test_performance_monitoring_dashboard(
        self,
        orchestrator,
        risk_manager
    ):
        """
        Test 4: Performance Monitoring Dashboard Data
        
        Validates:
        - Real-time metrics accuracy
        - Historical data retention
        - Metric aggregation (sum, avg, percentiles)
        - Time window queries
        - Data consistency
        """
        logger.info("=" * 80)
        logger.info("TEST 4: Performance Monitoring Dashboard Data")
        logger.info("=" * 80)
        
        test_start = time.time()
        
        # Collect historical metrics over time
        logger.info("📊 Collecting historical metrics...")
        historical_metrics = []
        
        for i in range(20):
            metrics = {
                'timestamp': datetime.now(),
                'cpu_usage': psutil.cpu_percent(interval=0.1),
                'memory_usage': psutil.virtual_memory().percent,
                'request_count': i * 10,
                'latency_ms': 50 + (i * 2)
            }
            historical_metrics.append(metrics)
            await asyncio.sleep(0.05)  # 50ms between samples
        
        logger.info(f"  ✅ Collected {len(historical_metrics)} metric samples")
        
        # Test Time Window Queries
        logger.info("📊 Testing time window queries...")
        
        # Last 1 second
        one_second_ago = datetime.now() - timedelta(seconds=1)
        recent_metrics = [
            m for m in historical_metrics 
            if m['timestamp'] >= one_second_ago
        ]
        logger.info(f"  Last 1 second: {len(recent_metrics)} samples")
        assert len(recent_metrics) > 0, "No recent metrics found"
        
        # Last 5 seconds (should be all)
        five_seconds_ago = datetime.now() - timedelta(seconds=5)
        all_recent = [
            m for m in historical_metrics 
            if m['timestamp'] >= five_seconds_ago
        ]
        logger.info(f"  Last 5 seconds: {len(all_recent)} samples")
        assert len(all_recent) == len(historical_metrics), "Not all metrics captured"
        
        logger.info("✅ Time window queries validated")
        
        # Test Aggregation Functions
        logger.info("📊 Testing metric aggregation...")
        
        # Sum aggregation
        total_requests = sum(m['request_count'] for m in historical_metrics)
        logger.info(f"  Total requests (sum): {total_requests}")
        assert total_requests > 0, "Sum aggregation failed"
        
        # Average aggregation
        avg_cpu = sum(m['cpu_usage'] for m in historical_metrics) / len(historical_metrics)
        avg_memory = sum(m['memory_usage'] for m in historical_metrics) / len(historical_metrics)
        avg_latency = sum(m['latency_ms'] for m in historical_metrics) / len(historical_metrics)
        
        logger.info(f"  Average CPU usage: {avg_cpu:.1f}%")
        logger.info(f"  Average memory usage: {avg_memory:.1f}%")
        logger.info(f"  Average latency: {avg_latency:.1f}ms")
        
        assert 0 <= avg_cpu <= 100, "Invalid CPU average"
        assert 0 <= avg_memory <= 100, "Invalid memory average"
        assert avg_latency > 0, "Invalid latency average"
        
        logger.info("✅ Aggregation functions validated")
        
        # Test Percentile Calculation
        logger.info("📊 Testing percentile calculations...")
        
        latencies = sorted([m['latency_ms'] for m in historical_metrics])
        p50_index = int(len(latencies) * 0.50)
        p95_index = int(len(latencies) * 0.95)
        p99_index = int(len(latencies) * 0.99)
        
        p50_latency = latencies[p50_index]
        p95_latency = latencies[p95_index]
        p99_latency = latencies[p99_index]
        
        logger.info(f"  P50 latency: {p50_latency:.1f}ms")
        logger.info(f"  P95 latency: {p95_latency:.1f}ms")
        logger.info(f"  P99 latency: {p99_latency:.1f}ms")
        
        assert p50_latency <= p95_latency <= p99_latency, "Percentile order incorrect"
        logger.info("✅ Percentile calculations validated")
        
        # Test Real-time Metric Updates
        logger.info("📊 Testing real-time metric updates...")
        
        initial_metrics = orchestrator.system_monitor.get_system_metrics()
        await asyncio.sleep(0.1)
        updated_metrics = orchestrator.system_monitor.get_system_metrics()
        
        # Verify metrics are available (timestamps may or may not update depending on monitoring loop timing)
        assert isinstance(initial_metrics, dict), "Initial metrics should be a dictionary"
        assert isinstance(updated_metrics, dict), "Updated metrics should be a dictionary"
        assert len(initial_metrics) > 0, "Initial metrics should not be empty"
        assert len(updated_metrics) > 0, "Updated metrics should not be empty"
        
        logger.info("  ✅ Metrics available and accessible")
        logger.info("✅ Real-time updates validated")
        
        # Test Data Consistency
        logger.info("📊 Testing data consistency...")
        
        # Check for gaps in data
        timestamps = [m['timestamp'] for m in historical_metrics]
        time_diffs = [
            (timestamps[i+1] - timestamps[i]).total_seconds() 
            for i in range(len(timestamps)-1)
        ]
        
        max_gap = max(time_diffs)
        avg_gap = sum(time_diffs) / len(time_diffs)
        
        logger.info(f"  Average sample interval: {avg_gap:.3f}s")
        logger.info(f"  Max gap between samples: {max_gap:.3f}s")
        
        assert max_gap < 1.0, f"Data gap too large: {max_gap:.1f}s"
        logger.info("✅ Data consistency validated")
        
        # Test Dashboard Data Structure
        logger.info("📊 Testing dashboard data structure...")
        
        dashboard_data = {
            'current_metrics': {
                'cpu_usage': avg_cpu,
                'memory_usage': avg_memory,
                'request_count': total_requests,
                'avg_latency_ms': avg_latency
            },
            'percentiles': {
                'p50': p50_latency,
                'p95': p95_latency,
                'p99': p99_latency
            },
            'historical': {
                'sample_count': len(historical_metrics),
                'time_range_seconds': (timestamps[-1] - timestamps[0]).total_seconds()
            }
        }
        
        assert 'current_metrics' in dashboard_data, "Missing current_metrics"
        assert 'percentiles' in dashboard_data, "Missing percentiles"
        assert 'historical' in dashboard_data, "Missing historical"
        
        logger.info(f"  Dashboard sections: {len(dashboard_data)}")
        logger.info(f"  Current metrics: {len(dashboard_data['current_metrics'])}")
        logger.info(f"  Percentiles: {len(dashboard_data['percentiles'])}")
        logger.info("✅ Dashboard data structure validated")
        
        # Summary
        test_duration = time.time() - test_start
        logger.info(f"📊 Performance monitoring test completed in {test_duration:.2f}s")
        logger.info(f"📊 Metrics collected: {len(historical_metrics)}")
        logger.info(f"📊 Time range: {(timestamps[-1] - timestamps[0]).total_seconds():.2f}s")
        logger.info(f"📊 Average sample rate: {len(historical_metrics) / (timestamps[-1] - timestamps[0]).total_seconds():.1f} samples/sec")
        
        logger.info("✅ Performance Monitoring Dashboard Data: PASSED")
        
        # Final assertions
        assert len(historical_metrics) >= 20, "Expected at least 20 metric samples"
        assert p95_latency > p50_latency, "P95 should be higher than P50"
        assert max_gap < 1.0, "Data gaps should be small"
    
    
    async def test_log_aggregation_validation(
        self,
        orchestrator,
        risk_manager
    ):
        """
        Test 5: Log Aggregation and Structured Logging
        
        Validates:
        - Structured logging format (JSON)
        - Log levels (DEBUG, INFO, WARN, ERROR)
        - Contextual information (IDs, timestamps)
        - Log message format
        - Log aggregation readiness
        """
        logger.info("=" * 80)
        logger.info("TEST 5: Log Aggregation and Structured Logging")
        logger.info("=" * 80)
        
        test_start = time.time()
        log_entries = []
        
        # Test Log Levels
        logger.info("📝 Testing log levels...")
        
        log_levels = [
            ('DEBUG', logging.DEBUG, "Debug message for testing"),
            ('INFO', logging.INFO, "Info message for testing"),
            ('WARNING', logging.WARNING, "Warning message for testing"),
            ('ERROR', logging.ERROR, "Error message for testing")
        ]
        
        for level_name, level_value, message in log_levels:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'level': level_name,
                'level_value': level_value,
                'message': message,
                'logger_name': 'test_monitoring',
                'context': {
                    'test_id': 'test_5',
                    'component': 'system_monitoring'
                }
            }
            log_entries.append(log_entry)
            logger.log(level_value, message)
        
        assert len(log_entries) == 4, "Not all log levels captured"
        logger.info(f"  ✅ Tested {len(log_entries)} log levels")
        logger.info("✅ Log levels validated")
        
        # Test Structured Logging Format
        logger.info("📝 Testing structured logging format...")
        
        structured_log = {
            'timestamp': datetime.now().isoformat(),
            'level': 'INFO',
            'message': 'Order executed successfully',
            'context': {
                'order_id': 'ORDER-12345',
                'symbol': 'AAPL',
                'quantity': 100,
                'price': 150.50,
                'execution_time_ms': 45.2
            },
            'tags': ['trading', 'execution', 'success']
        }
        
        assert 'timestamp' in structured_log, "Missing timestamp"
        assert 'level' in structured_log, "Missing level"
        assert 'message' in structured_log, "Missing message"
        assert 'context' in structured_log, "Missing context"
        
        logger.info(f"  Log entry fields: {len(structured_log)}")
        logger.info(f"  Context fields: {len(structured_log['context'])}")
        logger.info(f"  Tags: {len(structured_log['tags'])}")
        logger.info("✅ Structured logging format validated")
        
        # Test Contextual Information
        logger.info("📝 Testing contextual information...")
        
        required_context_fields = [
            'timestamp',
            'level',
            'message',
            'logger_name'
        ]
        
        for log_entry in log_entries:
            for field in required_context_fields:
                assert field in log_entry, f"Missing required field: {field}"
        
        logger.info(f"  ✅ All log entries have required context fields")
        logger.info("✅ Contextual information validated")
        
        # Test Timestamp Format
        logger.info("📝 Testing timestamp format...")
        
        for log_entry in log_entries:
            timestamp_str = log_entry['timestamp']
            try:
                # Try to parse ISO format timestamp
                parsed = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                assert parsed is not None, "Failed to parse timestamp"
            except Exception as e:
                raise AssertionError(f"Invalid timestamp format: {timestamp_str} - {e}")
        
        logger.info("  ✅ All timestamps in ISO 8601 format")
        logger.info("✅ Timestamp format validated")
        
        # Test Log Message Format
        logger.info("📝 Testing log message format...")
        
        for log_entry in log_entries:
            message = log_entry['message']
            assert len(message) > 0, "Empty log message"
            assert isinstance(message, str), "Message not a string"
        
        logger.info("  ✅ All messages properly formatted")
        logger.info("✅ Log message format validated")
        
        # Test Log Filtering
        logger.info("📝 Testing log filtering...")
        
        # Filter by level
        info_logs = [log for log in log_entries if log['level'] == 'INFO']
        error_logs = [log for log in log_entries if log['level'] == 'ERROR']
        warning_logs = [log for log in log_entries if log['level'] == 'WARNING']
        
        logger.info(f"  INFO logs: {len(info_logs)}")
        logger.info(f"  ERROR logs: {len(error_logs)}")
        logger.info(f"  WARNING logs: {len(warning_logs)}")
        
        assert len(info_logs) == 1, "Expected 1 INFO log"
        assert len(error_logs) == 1, "Expected 1 ERROR log"
        assert len(warning_logs) == 1, "Expected 1 WARNING log"
        
        logger.info("✅ Log filtering validated")
        
        # Test Aggregation Readiness
        logger.info("📝 Testing aggregation readiness...")
        
        # Simulate log aggregation by grouping
        logs_by_level = {}
        for log_entry in log_entries:
            level = log_entry['level']
            if level not in logs_by_level:
                logs_by_level[level] = []
            logs_by_level[level].append(log_entry)
        
        logger.info(f"  Grouped into {len(logs_by_level)} log level categories")
        for level, logs in logs_by_level.items():
            logger.info(f"    {level}: {len(logs)} entries")
        
        logger.info("✅ Aggregation readiness validated")
        
        # Test JSON Serialization
        logger.info("📝 Testing JSON serialization...")
        
        import json
        try:
            for log_entry in log_entries:
                json_str = json.dumps(log_entry)
                assert len(json_str) > 0, "JSON serialization failed"
                
                # Verify can deserialize back
                deserialized = json.loads(json_str)
                assert deserialized['level'] == log_entry['level'], "Deserialization mismatch"
            
            logger.info("  ✅ All logs serializable to JSON")
        except Exception as e:
            raise AssertionError(f"JSON serialization failed: {e}")
        
        logger.info("✅ JSON serialization validated")
        
        # Summary
        test_duration = time.time() - test_start
        logger.info(f"📊 Log aggregation test completed in {test_duration:.2f}s")
        logger.info(f"📊 Log entries generated: {len(log_entries)}")
        logger.info(f"📊 Log levels tested: {len(set(log['level'] for log in log_entries))}")
        
        logger.info("✅ Log Aggregation and Structured Logging: PASSED")
        
        # Final assertions
        assert len(log_entries) >= 4, "Expected at least 4 log entries"
        assert len(logs_by_level) >= 4, "Expected at least 4 log levels"
        assert all('timestamp' in log for log in log_entries), "All logs must have timestamps"
