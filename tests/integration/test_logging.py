"""
Test logging and monitoring for integration tests.

This module provides comprehensive logging and monitoring capabilities for integration tests.
"""

import logging
import logging.handlers
import time
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import threading
import psutil
import gc
from contextlib import contextmanager


@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring."""
    timestamp: datetime
    test_name: str
    duration_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_io_mb: float
    gc_collections: int
    gc_time_ms: float
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TestMetrics:
    """Test execution metrics."""
    test_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    success: Optional[bool] = None
    error_message: Optional[str] = None
    performance_metrics: List[PerformanceMetrics] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.performance_metrics is None:
            self.performance_metrics = []
        if self.metadata is None:
            self.metadata = {}


class PerformanceMonitor:
    """Monitors system performance during test execution."""
    
    def __init__(self):
        self.start_time = None
        self.start_memory = None
        self.start_cpu = None
        self.start_disk_io = None
        self.start_network_io = None
        self.start_gc_stats = None
        
        # Get initial system stats
        self._initialize_baseline()
    
    def _initialize_baseline(self):
        """Initialize baseline system statistics."""
        self.start_time = time.time()
        self.start_memory = psutil.virtual_memory()
        self.start_cpu = psutil.cpu_percent(interval=0.1)
        self.start_disk_io = psutil.disk_io_counters()
        self.start_network_io = psutil.net_io_counters()
        self.start_gc_stats = gc.get_stats()
    
    def get_current_metrics(self, test_name: str) -> PerformanceMetrics:
        """Get current performance metrics."""
        current_time = time.time()
        current_memory = psutil.virtual_memory()
        current_cpu = psutil.cpu_percent(interval=0.1)
        current_disk_io = psutil.disk_io_counters()
        current_network_io = psutil.net_io_counters()
        current_gc_stats = gc.get_stats()
        
        # Calculate deltas
        duration_ms = (current_time - self.start_time) * 1000
        memory_usage_mb = (current_memory.used - self.start_memory.used) / (1024 * 1024)
        cpu_usage_percent = current_cpu
        
        # Calculate disk I/O
        disk_read_mb = 0
        disk_write_mb = 0
        if current_disk_io and self.start_disk_io:
            disk_read_mb = (current_disk_io.read_bytes - self.start_disk_io.read_bytes) / (1024 * 1024)
            disk_write_mb = (current_disk_io.write_bytes - self.start_disk_io.write_bytes) / (1024 * 1024)
        
        # Calculate network I/O
        network_io_mb = 0
        if current_network_io and self.start_network_io:
            network_io_mb = (current_network_io.bytes_sent + current_network_io.bytes_recv - 
                           self.start_network_io.bytes_sent - self.start_network_io.bytes_recv) / (1024 * 1024)
        
        # Calculate GC metrics
        gc_collections = sum(stat.get('collections', 0) for stat in current_gc_stats) - sum(stat.get('collections', 0) for stat in self.start_gc_stats)
        gc_time_ms = sum(stat.get('collections', 0) * stat.get('collections_time', 0) for stat in current_gc_stats) - \
                    sum(stat.get('collections', 0) * stat.get('collections_time', 0) for stat in self.start_gc_stats)
        
        return PerformanceMetrics(
            timestamp=datetime.now(),
            test_name=test_name,
            duration_ms=duration_ms,
            memory_usage_mb=memory_usage_mb,
            cpu_usage_percent=cpu_usage_percent,
            disk_io_read_mb=disk_read_mb,
            disk_io_write_mb=disk_write_mb,
            network_io_mb=network_io_mb,
            gc_collections=gc_collections,
            gc_time_ms=gc_time_ms,
            metadata={
                'monitor_type': 'performance',
                'baseline_initialized': True
            }
        )
    
    def reset_baseline(self):
        """Reset baseline measurements."""
        self._initialize_baseline()


class TestLogger:
    """Comprehensive test logging system."""
    
    def __init__(self, log_dir: str = "test_logs", log_level: str = "INFO"):
        self.log_dir = Path(log_dir)
        self.log_level = getattr(logging, log_level.upper())
        
        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize loggers
        self._setup_loggers()
        
        # Performance monitoring
        self.performance_monitor = PerformanceMonitor()
        
        # Test metrics tracking
        self.test_metrics: Dict[str, TestMetrics] = {}
        self.current_test = None
        
        # Thread safety
        self._lock = threading.Lock()
    
    def _setup_loggers(self):
        """Set up different loggers for different purposes."""
        # Main test logger
        self.logger = logging.getLogger('integration_tests')
        self.logger.setLevel(self.log_level)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler for general logs
        general_log_file = self.log_dir / "integration_tests.log"
        file_handler = logging.handlers.RotatingFileHandler(
            general_log_file, maxBytes=10*1024*1024, backupCount=5
        )
        file_handler.setLevel(self.log_level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # Performance logger
        self.performance_logger = logging.getLogger('integration_tests.performance')
        self.performance_logger.setLevel(logging.INFO)
        
        performance_log_file = self.log_dir / "performance.log"
        performance_handler = logging.handlers.RotatingFileHandler(
            performance_log_file, maxBytes=10*1024*1024, backupCount=5
        )
        performance_handler.setLevel(logging.INFO)
        performance_formatter = logging.Formatter(
            '%(asctime)s - %(message)s'
        )
        performance_handler.setFormatter(performance_formatter)
        self.performance_logger.addHandler(performance_handler)
        
        # Error logger
        self.error_logger = logging.getLogger('integration_tests.errors')
        self.error_logger.setLevel(logging.ERROR)
        
        error_log_file = self.log_dir / "errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file, maxBytes=5*1024*1024, backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        error_handler.setFormatter(error_formatter)
        self.error_logger.addHandler(error_handler)
    
    def start_test(self, test_name: str, metadata: Dict[str, Any] = None):
        """Start monitoring a test."""
        with self._lock:
            self.current_test = test_name
            self.test_metrics[test_name] = TestMetrics(
                test_name=test_name,
                start_time=datetime.now(),
                metadata=metadata or {}
            )
            
            # Reset performance baseline
            self.performance_monitor.reset_baseline()
            
            self.logger.info(f"Starting test: {test_name}")
            if metadata:
                self.logger.info(f"Test metadata: {json.dumps(metadata, indent=2)}")
    
    def end_test(self, test_name: str, success: bool, error_message: str = None):
        """End monitoring a test."""
        with self._lock:
            if test_name not in self.test_metrics:
                self.logger.warning(f"Test {test_name} not found in metrics")
                return
            
            metrics = self.test_metrics[test_name]
            metrics.end_time = datetime.now()
            metrics.duration_ms = (metrics.end_time - metrics.start_time).total_seconds() * 1000
            metrics.success = success
            metrics.error_message = error_message
            
            # Get final performance metrics
            final_metrics = self.performance_monitor.get_current_metrics(test_name)
            metrics.performance_metrics.append(final_metrics)
            
            # Log test completion
            status = "PASSED" if success else "FAILED"
            self.logger.info(f"Test {test_name} {status} in {metrics.duration_ms:.2f}ms")
            
            if error_message:
                self.error_logger.error(f"Test {test_name} failed: {error_message}")
            
            # Log performance metrics
            self.performance_logger.info(
                f"Test: {test_name} | Duration: {metrics.duration_ms:.2f}ms | "
                f"Memory: {final_metrics.memory_usage_mb:.2f}MB | "
                f"CPU: {final_metrics.cpu_usage_percent:.1f}%"
            )
            
            self.current_test = None
    
    def log_performance_metrics(self, test_name: str = None):
        """Log current performance metrics."""
        if test_name is None:
            test_name = self.current_test
        
        if test_name is None:
            return
        
        metrics = self.performance_monitor.get_current_metrics(test_name)
        
        # Add to test metrics if test is active
        if test_name in self.test_metrics:
            self.test_metrics[test_name].performance_metrics.append(metrics)
        
        # Log to performance logger
        self.performance_logger.info(
            f"Performance - Test: {test_name} | "
            f"Memory: {metrics.memory_usage_mb:.2f}MB | "
            f"CPU: {metrics.cpu_usage_percent:.1f}% | "
            f"Disk Read: {metrics.disk_io_read_mb:.2f}MB | "
            f"Disk Write: {metrics.disk_io_write_mb:.2f}MB | "
            f"Network: {metrics.network_io_mb:.2f}MB"
        )
    
    def log_test_event(self, event: str, data: Dict[str, Any] = None):
        """Log a test event."""
        if self.current_test is None:
            self.logger.warning("No active test for event logging")
            return
        
        message = f"Test {self.current_test}: {event}"
        if data:
            message += f" - {json.dumps(data, indent=2)}"
        
        self.logger.info(message)
    
    def log_error(self, error: Exception, context: str = None):
        """Log an error with context."""
        error_message = f"Error in {context or 'unknown context'}: {str(error)}"
        self.error_logger.error(error_message, exc_info=True)
        
        if self.current_test:
            self.logger.error(f"Test {self.current_test} encountered error: {error_message}")
    
    def get_test_metrics(self, test_name: str) -> Optional[TestMetrics]:
        """Get metrics for a specific test."""
        return self.test_metrics.get(test_name)
    
    def get_all_metrics(self) -> Dict[str, TestMetrics]:
        """Get all test metrics."""
        return self.test_metrics.copy()
    
    def save_metrics_to_file(self, filename: str = None):
        """Save all metrics to a JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_metrics_{timestamp}.json"
        
        metrics_file = self.log_dir / filename
        
        # Convert metrics to serializable format
        serializable_metrics = {}
        for test_name, metrics in self.test_metrics.items():
            serializable_metrics[test_name] = asdict(metrics)
        
        with open(metrics_file, 'w') as f:
            json.dump(serializable_metrics, f, indent=2, default=str)
        
        self.logger.info(f"Test metrics saved to: {metrics_file}")
        return metrics_file
    
    def generate_test_report(self) -> Dict[str, Any]:
        """Generate a comprehensive test report."""
        total_tests = len(self.test_metrics)
        passed_tests = sum(1 for metrics in self.test_metrics.values() if metrics.success)
        failed_tests = total_tests - passed_tests
        
        total_duration = sum(metrics.duration_ms or 0 for metrics in self.test_metrics.values())
        avg_duration = total_duration / total_tests if total_tests > 0 else 0
        
        # Aggregate performance metrics
        all_performance_metrics = []
        for metrics in self.test_metrics.values():
            all_performance_metrics.extend(metrics.performance_metrics)
        
        avg_memory_usage = sum(m.memory_usage_mb for m in all_performance_metrics) / len(all_performance_metrics) if all_performance_metrics else 0
        avg_cpu_usage = sum(m.cpu_usage_percent for m in all_performance_metrics) / len(all_performance_metrics) if all_performance_metrics else 0
        
        report = {
            'summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                'total_duration_ms': total_duration,
                'avg_duration_ms': avg_duration
            },
            'performance': {
                'avg_memory_usage_mb': avg_memory_usage,
                'avg_cpu_usage_percent': avg_cpu_usage,
                'total_performance_measurements': len(all_performance_metrics)
            },
            'tests': {
                test_name: {
                    'success': metrics.success,
                    'duration_ms': metrics.duration_ms,
                    'error_message': metrics.error_message,
                    'performance_measurements': len(metrics.performance_metrics)
                }
                for test_name, metrics in self.test_metrics.items()
            },
            'generated_at': datetime.now().isoformat()
        }
        
        return report
    
    def save_test_report(self, filename: str = None):
        """Save test report to file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_report_{timestamp}.json"
        
        report_file = self.log_dir / filename
        report = self.generate_test_report()
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"Test report saved to: {report_file}")
        return report_file


# Global test logger instance
test_logger = TestLogger()


@contextmanager
def monitoring_context(test_name: str, metadata: Dict[str, Any] = None):
    """Context manager for test monitoring."""
    test_logger.start_test(test_name, metadata)
    try:
        yield test_logger
    except Exception as e:
        test_logger.end_test(test_name, False, str(e))
        raise
    else:
        test_logger.end_test(test_name, True)


def log_test_event(event: str, data: Dict[str, Any] = None):
    """Log a test event using the global logger."""
    test_logger.log_test_event(event, data)


def log_error(error: Exception, context: str = None):
    """Log an error using the global logger."""
    test_logger.log_error(error, context)


def get_test_metrics(test_name: str) -> Optional[TestMetrics]:
    """Get test metrics using the global logger."""
    return test_logger.get_test_metrics(test_name)


def save_test_report(filename: str = None):
    """Save test report using the global logger."""
    return test_logger.save_test_report(filename)


if __name__ == "__main__":
    # Test the logging system
    with monitoring_context("test_logging_system", {"test_type": "logging"}) as logger:
        logger.log_test_event("Test event 1", {"data": "value1"})
        logger.log_test_event("Test event 2", {"data": "value2"})
        
        # Simulate some work
        import time
        time.sleep(1)
        
        logger.log_performance_metrics()
    
    # Save report
    save_test_report()
    print("Test logging system test completed.") 