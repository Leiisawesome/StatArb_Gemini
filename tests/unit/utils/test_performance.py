"""
Unit tests for utils module
"""

import pytest
import asyncio
import time
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

# Import all utils modules
from core_engine.utils.performance import (
    PerformanceMetric, PerformanceSnapshot, OperationProfile,
    PerformanceMonitor, get_performance_monitor, record_performance_metric,
    profile_operation, get_performance_metrics
)
from core_engine.utils.health import (
    HealthStatus, HealthCheckResult, HealthCheck, DatabaseHealthCheck,
    BrokerHealthCheck, ComponentHealthCheck, MemoryHealthCheck,
    HealthMonitor, get_health_monitor, add_health_check,
    create_database_health_check, create_broker_health_check,
    create_component_health_check, create_memory_health_check
)

class TestPerformance:
    """Test performance monitoring utilities"""

    def test_performance_metric_creation(self):
        """Test PerformanceMetric dataclass"""
        timestamp = datetime.now()
        metric = PerformanceMetric(
            name="test_metric",
            value=100.5,
            unit="ms",
            timestamp=timestamp,
            metadata={"key": "value"},
            component="test_comp",
            operation="test_op"
        )

        assert metric.name == "test_metric"
        assert metric.value == 100.5
        assert metric.unit == "ms"
        assert metric.timestamp == timestamp
        assert metric.metadata["key"] == "value"
        assert metric.component == "test_comp"
        assert metric.operation == "test_op"

    def test_performance_snapshot_creation(self):
        """Test PerformanceSnapshot dataclass"""
        timestamp = datetime.now()
        snapshot = PerformanceSnapshot(
            timestamp=timestamp,
            cpu_percent=45.2,
            memory_mb=512.5,
            memory_percent=25.1,
            disk_usage_percent=60.0,
            network_connections=150,
            thread_count=8,
            open_files=45,
            metadata={"note": "test"}
        )

        assert snapshot.timestamp == timestamp
        assert snapshot.cpu_percent == 45.2
        assert snapshot.memory_mb == 512.5
        assert snapshot.memory_percent == 25.1
        assert snapshot.disk_usage_percent == 60.0
        assert snapshot.network_connections == 150
        assert snapshot.thread_count == 8
        assert snapshot.open_files == 45
        assert snapshot.metadata["note"] == "test"

    def test_operation_profile_creation(self):
        """Test OperationProfile dataclass"""
        timestamp = datetime.now()
        profile = OperationProfile(
            operation_name="test_operation",
            call_count=10,
            total_time=5.5,
            avg_time=0.55,
            min_time=0.3,
            max_time=1.2,
            last_called=timestamp,
            error_count=1
        )

        assert profile.operation_name == "test_operation"
        assert profile.call_count == 10
        assert profile.total_time == 5.5
        assert profile.avg_time == 0.55
        assert profile.min_time == 0.3
        assert profile.max_time == 1.2
        assert profile.last_called == timestamp
        assert profile.error_count == 1

    @patch('core_engine.utils.performance.psutil')
    @patch('core_engine.utils.performance.threading.active_count', return_value=12)
    def test_performance_monitor_take_snapshot(self, mock_threading_active_count, mock_psutil):
        """Test PerformanceMonitor take_snapshot"""
        # Mock psutil
        mock_process = Mock()
        mock_process.memory_info.return_value.rss = 256 * 1024 * 1024  # 256MB
        mock_process.open_files.return_value = [Mock()] * 10

        mock_psutil.cpu_percent.return_value = 30.5
        mock_psutil.virtual_memory.return_value = Mock(
            used=512 * 1024 * 1024,  # 512MB
            percent=25.6
        )
        mock_psutil.disk_usage.return_value = Mock(percent=45.2)
        mock_psutil.net_connections.return_value = [Mock()] * 20
        mock_psutil.Process.return_value = mock_process

        monitor = PerformanceMonitor()
        snapshot = monitor.take_snapshot()

        assert snapshot.cpu_percent == 30.5
        assert snapshot.memory_mb == 512.0  # 512MB
        assert snapshot.memory_percent == 25.6
        assert snapshot.disk_usage_percent == 45.2
        assert snapshot.network_connections == 20
        assert snapshot.thread_count == 12
        assert snapshot.open_files == 10

    def test_performance_monitor_record_metric(self):
        """Test PerformanceMonitor record_metric"""
        monitor = PerformanceMonitor()

        monitor.record_metric("test_metric", 42.0, "units", "test_comp", "test_op", {"meta": "data"})

        assert len(monitor.metrics) == 1
        metric = monitor.metrics[0]
        assert metric.name == "test_metric"
        assert metric.value == 42.0
        assert metric.unit == "units"
        assert metric.component == "test_comp"
        assert metric.operation == "test_op"
        assert metric.metadata["meta"] == "data"

    @pytest.mark.asyncio
    async def test_performance_monitor_alerts(self):
        """Test PerformanceMonitor alert system"""
        monitor = PerformanceMonitor()

        # Set alert threshold
        monitor.set_alert_threshold("test_metric", 50.0)

        # Mock alert callback
        alert_calls = []
        async def mock_callback(metric):
            alert_calls.append(metric)

        monitor.add_alert_callback(mock_callback)

        # Record metric that should trigger alert
        monitor.record_metric("test_metric", 75.0)

        # Wait a bit for async alert to be processed
        await asyncio.sleep(0.01)

        assert len(alert_calls) == 1
        assert alert_calls[0].name == "test_metric"
        assert alert_calls[0].value == 75.0

    @patch('core_engine.utils.performance.psutil')
    def test_performance_monitor_profile_operation(self, mock_psutil):
        """Test PerformanceMonitor profile_operation context manager"""
        mock_process = Mock()
        mock_process.memory_info.return_value.rss = 100 * 1024 * 1024  # 100MB initially
        mock_psutil.Process.return_value = mock_process

        monitor = PerformanceMonitor()

        with monitor.profile_operation("test_operation", "test_component"):
            time.sleep(0.01)  # Small delay
            mock_process.memory_info.return_value.rss = 105 * 1024 * 1024  # 105MB after

        # Check that metrics were recorded
        duration_metrics = [m for m in monitor.metrics if "duration" in m.name]
        memory_metrics = [m for m in monitor.metrics if "memory_delta" in m.name]

        assert len(duration_metrics) == 1
        assert len(memory_metrics) == 1

        assert duration_metrics[0].component == "test_component"
        assert duration_metrics[0].operation == "test_operation"
        assert duration_metrics[0].unit == "ms"

        assert memory_metrics[0].component == "test_component"
        assert memory_metrics[0].operation == "test_operation"
        assert memory_metrics[0].unit == "MB"

    def test_performance_monitor_get_operation_profile(self):
        """Test PerformanceMonitor operation profiling"""
        monitor = PerformanceMonitor()

        # Update profile manually
        monitor._update_operation_profile("test_op", 0.1)
        monitor._update_operation_profile("test_op", 0.2)
        monitor._update_operation_profile("test_op", 0.3)

        profile = monitor.get_operation_profile("test_op")

        assert profile.operation_name == "test_op"
        assert profile.call_count == 3
        assert abs(profile.total_time - 0.6) < 0.001  # Use approximate comparison for floating point
        assert abs(profile.avg_time - 0.2) < 0.001
        assert profile.min_time == 0.1
        assert profile.max_time == 0.3

    def test_performance_monitor_memory_tracing(self):
        """Test PerformanceMonitor memory tracing"""
        monitor = PerformanceMonitor()

        # Start memory tracing
        monitor.start_memory_tracing()
        assert monitor.memory_tracing is True

        # Get memory snapshot
        snapshot = monitor.get_memory_snapshot()
        assert "total_blocks" in snapshot
        assert "total_size_mb" in snapshot
        assert "top_allocations" in snapshot

        # Stop memory tracing
        monitor.stop_memory_tracing()
        assert monitor.memory_tracing is False

    def test_performance_monitor_cpu_profiling(self):
        """Test PerformanceMonitor CPU profiling"""
        monitor = PerformanceMonitor()

        # Start CPU profiling
        monitor.start_cpu_profiling()
        assert monitor.cpu_profiling is True

        # Simulate some work
        for i in range(1000):
            _ = i * i

        # Stop CPU profiling
        profile_output = monitor.stop_cpu_profiling()
        assert profile_output is not None
        assert "function calls" in profile_output.lower() or len(profile_output) > 0
        assert monitor.cpu_profiling is False

    def test_global_performance_functions(self):
        """Test global performance monitoring functions"""
        # Test record_performance_metric
        record_performance_metric("global_test", 123.0, "units")

        # Test get_performance_metrics
        metrics = get_performance_metrics()
        assert "current_snapshot" in metrics
        assert "operation_profiles" in metrics
        assert "alert_thresholds" in metrics

    def test_profile_function_decorator(self):
        """Test profile_function decorator"""
        monitor = PerformanceMonitor()

        @monitor.profile_function("test_component")
        def test_function():
            time.sleep(0.01)
            return "result"

        result = test_function()
        assert result == "result"

        # Check that metrics were recorded
        duration_metrics = [m for m in monitor.metrics if "duration" in m.name]
        assert len(duration_metrics) >= 1

    def test_profile_operation_context_manager(self):
        """Test profile_operation context manager"""
        with profile_operation("global_test_op", "global_test_comp"):
            time.sleep(0.01)

        # Check that global monitor recorded the operation
        monitor = get_performance_monitor()
        profile = monitor.get_operation_profile("global_test_op")
        assert profile is not None
        assert profile.call_count >= 1

class TestHealth:
    """Test health monitoring utilities"""

    def test_health_status_enum(self):
        """Test HealthStatus enum values"""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"

    def test_health_check_result_creation(self):
        """Test HealthCheckResult creation and properties"""
        timestamp = datetime.now()
        result = HealthCheckResult(
            component="test_component",
            status=HealthStatus.HEALTHY,
            message="All good",
            details={"metric": "value"},
            timestamp=timestamp,
            response_time_ms=150.5,
            last_success=timestamp,
            consecutive_failures=0
        )

        assert result.component == "test_component"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "All good"
        assert result.details["metric"] == "value"
        assert result.timestamp == timestamp
        assert result.response_time_ms == 150.5
        assert result.last_success == timestamp
        assert result.consecutive_failures == 0
        assert result.is_healthy is True
        assert result.is_degraded is False

    def test_health_check_result_properties(self):
        """Test HealthCheckResult computed properties"""
        healthy_result = HealthCheckResult("comp", HealthStatus.HEALTHY, "ok")
        degraded_result = HealthCheckResult("comp", HealthStatus.DEGRADED, "slow")
        unhealthy_result = HealthCheckResult("comp", HealthStatus.UNHEALTHY, "error")
        unknown_result = HealthCheckResult("comp", HealthStatus.UNKNOWN, "unknown")

        assert healthy_result.is_healthy is True
        assert healthy_result.is_degraded is False

        assert degraded_result.is_healthy is False
        assert degraded_result.is_degraded is True

        assert unhealthy_result.is_healthy is False
        assert unhealthy_result.is_degraded is False

        assert unknown_result.is_healthy is False
        assert unknown_result.is_degraded is False

    @pytest.mark.asyncio
    async def test_database_health_check_success(self):
        """Test DatabaseHealthCheck with successful connection"""
        async def mock_check():
            return True

        check = DatabaseHealthCheck("test_db", mock_check)
        result = await check.check()

        assert result.component == "test_db"
        assert result.status == HealthStatus.HEALTHY
        assert "successful" in result.message
        assert result.details["connection_status"] == "connected"
        assert result.response_time_ms >= 0

    @pytest.mark.asyncio
    async def test_database_health_check_failure(self):
        """Test DatabaseHealthCheck with failed connection"""
        async def mock_check():
            return False

        check = DatabaseHealthCheck("test_db", mock_check)
        result = await check.check()

        assert result.component == "test_db"
        assert result.status == HealthStatus.UNHEALTHY
        assert "failed" in result.message
        assert result.details["connection_status"] == "disconnected"

    @pytest.mark.asyncio
    async def test_database_health_check_timeout(self):
        """Test DatabaseHealthCheck with timeout"""
        async def slow_check():
            await asyncio.sleep(2)  # Longer than timeout
            return True

        check = DatabaseHealthCheck("test_db", slow_check, timeout_seconds=1.0)  # Set timeout to 1 second
        result = await check.check()

        assert result.component == "test_db"
        assert result.status == HealthStatus.UNHEALTHY
        assert "timed out" in result.message

    @pytest.mark.asyncio
    async def test_broker_health_check(self):
        """Test BrokerHealthCheck"""
        async def mock_check():
            return True

        check = BrokerHealthCheck("test_broker", mock_check)
        result = await check.check()

        assert result.component == "test_broker"
        assert result.status == HealthStatus.HEALTHY
        assert "successful" in result.message

    @pytest.mark.asyncio
    async def test_component_health_check(self):
        """Test ComponentHealthCheck"""
        async def mock_check():
            return {
                "status": "healthy",
                "version": "1.0.0",
                "uptime": 3600
            }

        check = ComponentHealthCheck("test_comp", mock_check)
        result = await check.check()

        assert result.component == "test_comp"
        assert result.status == HealthStatus.HEALTHY
        assert result.details["version"] == "1.0.0"
        assert result.details["uptime"] == 3600

    @pytest.mark.asyncio
    async def test_component_health_check_degraded(self):
        """Test ComponentHealthCheck with degraded status"""
        async def mock_check():
            return {
                "status": "degraded",
                "cpu_usage": 95.0
            }

        check = ComponentHealthCheck("test_comp", mock_check)
        result = await check.check()

        assert result.component == "test_comp"
        assert result.status == HealthStatus.DEGRADED
        assert "degraded" in result.message

    @patch('psutil.Process')
    @pytest.mark.asyncio
    async def test_memory_health_check_healthy(self, mock_process_class):
        """Test MemoryHealthCheck healthy state"""
        # Mock process memory usage
        mock_process = Mock()
        mock_process.memory_info.return_value.rss = 500 * 1024 * 1024  # 500MB
        mock_process_class.return_value = mock_process

        check = MemoryHealthCheck("test_comp", max_memory_mb=1000.0)
        result = await check.check()

        assert result.component == "test_comp"
        assert result.status == HealthStatus.HEALTHY
        assert "normal" in result.message
        assert result.details["memory_mb"] == 500.0
        assert result.details["max_memory_mb"] == 1000.0

    @patch('psutil.Process')
    @pytest.mark.asyncio
    async def test_memory_health_check_degraded(self, mock_process_class):
        """Test MemoryHealthCheck degraded state"""
        # Mock high memory usage
        mock_process = Mock()
        mock_process.memory_info.return_value.rss = 900 * 1024 * 1024  # 900MB
        mock_process_class.return_value = mock_process

        check = MemoryHealthCheck("test_comp", max_memory_mb=1000.0)
        result = await check.check()

        assert result.component == "test_comp"
        assert result.status == HealthStatus.DEGRADED
        assert "high" in result.message

    @patch('psutil.Process')
    @pytest.mark.asyncio
    async def test_memory_health_check_unhealthy(self, mock_process_class):
        """Test MemoryHealthCheck unhealthy state"""
        # Mock excessive memory usage
        mock_process = Mock()
        mock_process.memory_info.return_value.rss = 1200 * 1024 * 1024  # 1200MB
        mock_process_class.return_value = mock_process

        check = MemoryHealthCheck("test_comp", max_memory_mb=1000.0)
        result = await check.check()

        assert result.component == "test_comp"
        assert result.status == HealthStatus.UNHEALTHY
        assert "too high" in result.message

    def test_health_monitor_initialization(self):
        """Test HealthMonitor initialization"""
        monitor = HealthMonitor()

        assert monitor.checks == {}
        assert monitor.results == {}
        assert monitor.alert_callbacks == []
        assert monitor.is_monitoring is False
        assert monitor.check_interval == 30.0

    def test_health_monitor_add_check(self):
        """Test HealthMonitor add_check"""
        monitor = HealthMonitor()

        # Create a mock health check
        check = Mock(spec=HealthCheck)
        check.name = "test_check"
        check.component = "test_comp"

        monitor.add_check(check)

        assert "test_check" in monitor.checks
        assert monitor.checks["test_check"] == check

    def test_health_monitor_remove_check(self):
        """Test HealthMonitor remove_check"""
        monitor = HealthMonitor()

        # Add a check
        check = Mock(spec=HealthCheck)
        check.name = "test_check"
        check.component = "test_comp"
        monitor.add_check(check)

        # Remove it
        monitor.remove_check("test_check")

        assert "test_check" not in monitor.checks

    @pytest.mark.asyncio
    async def test_health_monitor_run_check(self):
        """Test HealthMonitor run_check"""
        monitor = HealthMonitor()

        # Create a mock check that returns a result
        check = Mock(spec=HealthCheck)
        check.name = "test_check"
        check.component = "test_comp"

        result = HealthCheckResult("test_comp", HealthStatus.HEALTHY, "OK")
        check.check = AsyncMock(return_value=result)

        monitor.add_check(check)

        returned_result = await monitor.run_check("test_check")

        assert returned_result == result
        assert "test_check" in monitor.results
        assert monitor.results["test_check"] == result

    @pytest.mark.asyncio
    async def test_health_monitor_run_all_checks(self):
        """Test HealthMonitor run_all_checks"""
        monitor = HealthMonitor()

        # Add multiple checks
        check1 = Mock(spec=HealthCheck)
        check1.name = "check1"
        check1.component = "comp1"
        check1.check = AsyncMock(return_value=HealthCheckResult("comp1", HealthStatus.HEALTHY, "OK"))

        check2 = Mock(spec=HealthCheck)
        check2.name = "check2"
        check2.component = "comp2"
        check2.check = AsyncMock(return_value=HealthCheckResult("comp2", HealthStatus.DEGRADED, "Slow"))

        monitor.add_check(check1)
        monitor.add_check(check2)

        results = await monitor.run_all_checks()

        assert len(results) == 2
        assert results["check1"].status == HealthStatus.HEALTHY
        assert results["check2"].status == HealthStatus.DEGRADED

    def test_health_monitor_get_status(self):
        """Test HealthMonitor get_status"""
        monitor = HealthMonitor()

        # No results
        status = monitor.get_status()
        assert status["overall_status"] == HealthStatus.UNKNOWN.value
        assert status["total_checks"] == 0

        # Add some results
        monitor.results = {
            "check1": HealthCheckResult("comp1", HealthStatus.HEALTHY, "OK"),
            "check2": HealthCheckResult("comp2", HealthStatus.DEGRADED, "Slow"),
            "check3": HealthCheckResult("comp3", HealthStatus.UNHEALTHY, "Error")
        }

        status = monitor.get_status()
        assert status["overall_status"] == HealthStatus.UNHEALTHY.value
        assert status["total_checks"] == 3
        assert status["healthy_checks"] == 1
        assert status["degraded_checks"] == 1
        assert status["unhealthy_checks"] == 1

    def test_health_monitor_get_component_status(self):
        """Test HealthMonitor get_component_status"""
        monitor = HealthMonitor()

        # Add results for different components
        monitor.results = {
            "db_check": HealthCheckResult("database", HealthStatus.HEALTHY, "OK"),
            "api_check": HealthCheckResult("api", HealthStatus.DEGRADED, "Slow"),
            "cache_check": HealthCheckResult("cache", HealthStatus.UNHEALTHY, "Down")
        }

        # Get status for specific component
        db_status = monitor.get_component_status("database")
        assert db_status["status"] == HealthStatus.HEALTHY.value
        assert len(db_status["checks"]) == 1

        # Get status for component with mixed results
        api_status = monitor.get_component_status("api")
        assert api_status["status"] == HealthStatus.DEGRADED.value

        # Get status for unknown component
        unknown_status = monitor.get_component_status("unknown")
        assert unknown_status["status"] == HealthStatus.UNKNOWN.value

    def test_global_health_functions(self):
        """Test global health monitoring functions"""
        # Test get_health_monitor
        monitor = get_health_monitor()
        assert isinstance(monitor, HealthMonitor)

        # Test create functions
        async def mock_db_check():
            return True

        async def mock_broker_check():
            return True

        async def mock_comp_check():
            return {"status": "healthy"}

        db_check = create_database_health_check("test", mock_db_check)
        broker_check = create_broker_health_check("test", mock_broker_check)
        comp_check = create_component_health_check("test", mock_comp_check)
        mem_check = create_memory_health_check("test", 500.0)

        assert isinstance(db_check, DatabaseHealthCheck)
        assert isinstance(broker_check, BrokerHealthCheck)
        assert isinstance(comp_check, ComponentHealthCheck)
        assert isinstance(mem_check, MemoryHealthCheck)

        # Test add_health_check
        add_health_check(db_check)
        assert "database" in get_health_monitor().checks

