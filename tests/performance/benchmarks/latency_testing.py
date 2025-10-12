"""
Advanced Latency Testing Framework for Core Engine Components

This module provides comprehensive latency measurement and analysis for critical
trading system components, focusing on sub-millisecond precision and statistical
analysis of performance characteristics.
"""

import asyncio
import time
import statistics
import logging
from typing import Dict, List, Any, Callable, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import numpy as np
import threading
import psutil

logger = logging.getLogger(__name__)

@dataclass
class LatencyMeasurement:
    """Single latency measurement with context"""
    component_name: str
    operation_name: str
    latency_ns: int  # Nanosecond precision
    timestamp: datetime
    thread_id: int
    cpu_usage: float
    memory_usage_mb: float
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class LatencyStatistics:
    """Statistical analysis of latency measurements"""
    component_name: str
    operation_name: str
    sample_count: int
    
    # Core statistics (in microseconds for readability)
    mean_us: float
    median_us: float
    std_dev_us: float
    min_us: float
    max_us: float
    
    # Percentiles
    p50_us: float
    p90_us: float
    p95_us: float
    p99_us: float
    p99_9_us: float
    
    # Performance indicators
    outlier_count: int
    outlier_threshold_us: float
    jitter_us: float  # Standard deviation of consecutive differences
    
    # Timing analysis
    measurement_period: timedelta
    throughput_ops_per_sec: float

class LatencyProfiler:
    """High-precision latency profiler for trading system components"""
    
    def __init__(self, max_samples: int = 10000):
        self.measurements: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_samples))
        self.active_measurements: Dict[str, float] = {}
        self.lock = threading.Lock()
        self.max_samples = max_samples
        
    def start_measurement(self, component_name: str, operation_name: str, 
                         context: Dict[str, Any] = None) -> str:
        """Start a latency measurement"""
        measurement_id = f"{component_name}::{operation_name}::{time.time_ns()}"
        start_time = time.perf_counter_ns()
        
        with self.lock:
            self.active_measurements[measurement_id] = start_time
            
        return measurement_id
    
    def end_measurement(self, measurement_id: str, context: Dict[str, Any] = None) -> Optional[LatencyMeasurement]:
        """End a latency measurement and record results"""
        end_time = time.perf_counter_ns()
        
        with self.lock:
            start_time = self.active_measurements.pop(measurement_id, None)
            
        if start_time is None:
            logger.warning(f"No active measurement found for ID: {measurement_id}")
            return None
            
        # Parse measurement ID
        parts = measurement_id.split("::")
        component_name, operation_name = parts[0], parts[1]
        
        # Calculate latency
        latency_ns = end_time - start_time
        
        # Get system metrics
        cpu_usage = psutil.cpu_percent()
        memory_usage_mb = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Create measurement
        measurement = LatencyMeasurement(
            component_name=component_name,
            operation_name=operation_name,
            latency_ns=latency_ns,
            timestamp=datetime.now(),
            thread_id=threading.get_ident(),
            cpu_usage=cpu_usage,
            memory_usage_mb=memory_usage_mb,
            context=context or {}
        )
        
        # Store measurement
        key = f"{component_name}::{operation_name}"
        with self.lock:
            self.measurements[key].append(measurement)
            
        return measurement
    
    def measure_sync_operation(self, component_name: str, operation_name: str, 
                              operation: Callable, *args, **kwargs) -> Tuple[Any, LatencyMeasurement]:
        """Measure a synchronous operation"""
        measurement_id = self.start_measurement(component_name, operation_name)
        
        try:
            result = operation(*args, **kwargs)
            measurement = self.end_measurement(measurement_id)
            return result, measurement
        except Exception as e:
            self.end_measurement(measurement_id, {"error": str(e)})
            raise
    
    async def measure_async_operation(self, component_name: str, operation_name: str,
                                    operation: Callable, *args, **kwargs) -> Tuple[Any, LatencyMeasurement]:
        """Measure an asynchronous operation"""
        measurement_id = self.start_measurement(component_name, operation_name)
        
        try:
            result = await operation(*args, **kwargs)
            measurement = self.end_measurement(measurement_id)
            return result, measurement
        except Exception as e:
            self.end_measurement(measurement_id, {"error": str(e)})
            raise
    
    def get_statistics(self, component_name: str, operation_name: str) -> Optional[LatencyStatistics]:
        """Calculate comprehensive statistics for a component operation"""
        key = f"{component_name}::{operation_name}"
        
        with self.lock:
            measurements = list(self.measurements.get(key, []))
            
        if not measurements:
            return None
            
        # Extract latencies in microseconds
        latencies_us = [m.latency_ns / 1000 for m in measurements]
        
        if len(latencies_us) < 2:
            return None
            
        # Calculate basic statistics
        mean_us = statistics.mean(latencies_us)
        median_us = statistics.median(latencies_us)
        std_dev_us = statistics.stdev(latencies_us)
        min_us = min(latencies_us)
        max_us = max(latencies_us)
        
        # Calculate percentiles
        p50_us = np.percentile(latencies_us, 50)
        p90_us = np.percentile(latencies_us, 90)
        p95_us = np.percentile(latencies_us, 95)
        p99_us = np.percentile(latencies_us, 99)
        p99_9_us = np.percentile(latencies_us, 99.9)
        
        # Calculate outliers (using IQR method)
        q1 = np.percentile(latencies_us, 25)
        q3 = np.percentile(latencies_us, 75)
        iqr = q3 - q1
        outlier_threshold_us = q3 + 1.5 * iqr
        outlier_count = sum(1 for lat in latencies_us if lat > outlier_threshold_us)
        
        # Calculate jitter (consecutive differences)
        if len(latencies_us) > 1:
            consecutive_diffs = [abs(latencies_us[i] - latencies_us[i-1]) 
                               for i in range(1, len(latencies_us))]
            jitter_us = statistics.stdev(consecutive_diffs) if len(consecutive_diffs) > 1 else 0.0
        else:
            jitter_us = 0.0
            
        # Calculate throughput
        time_span = measurements[-1].timestamp - measurements[0].timestamp
        throughput_ops_per_sec = len(measurements) / max(time_span.total_seconds(), 0.001)
        
        return LatencyStatistics(
            component_name=component_name,
            operation_name=operation_name,
            sample_count=len(measurements),
            mean_us=mean_us,
            median_us=median_us,
            std_dev_us=std_dev_us,
            min_us=min_us,
            max_us=max_us,
            p50_us=p50_us,
            p90_us=p90_us,
            p95_us=p95_us,
            p99_us=p99_us,
            p99_9_us=p99_9_us,
            outlier_count=outlier_count,
            outlier_threshold_us=outlier_threshold_us,
            jitter_us=jitter_us,
            measurement_period=time_span,
            throughput_ops_per_sec=throughput_ops_per_sec
        )
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_measurements': sum(len(measurements) for measurements in self.measurements.values()),
            'components': {}
        }
        
        for key, measurements in self.measurements.items():
            if not measurements:
                continue
                
            component_name, operation_name = key.split("::", 1)
            stats = self.get_statistics(component_name, operation_name)
            
            if stats:
                if component_name not in report['components']:
                    report['components'][component_name] = {}
                    
                report['components'][component_name][operation_name] = {
                    'sample_count': stats.sample_count,
                    'latency_statistics_us': {
                        'mean': round(stats.mean_us, 2),
                        'median': round(stats.median_us, 2),
                        'std_dev': round(stats.std_dev_us, 2),
                        'min': round(stats.min_us, 2),
                        'max': round(stats.max_us, 2)
                    },
                    'percentiles_us': {
                        'p50': round(stats.p50_us, 2),
                        'p90': round(stats.p90_us, 2),
                        'p95': round(stats.p95_us, 2),
                        'p99': round(stats.p99_us, 2),
                        'p99.9': round(stats.p99_9_us, 2)
                    },
                    'performance_indicators': {
                        'outlier_count': stats.outlier_count,
                        'outlier_percentage': round((stats.outlier_count / stats.sample_count) * 100, 2),
                        'jitter_us': round(stats.jitter_us, 2),
                        'throughput_ops_per_sec': round(stats.throughput_ops_per_sec, 2)
                    }
                }
        
        return report

class ComponentLatencyTester:
    """Specialized latency tester for core engine components"""
    
    def __init__(self, profiler: LatencyProfiler):
        self.profiler = profiler
        
    async def test_data_manager_latency(self, data_manager, symbols: List[str], iterations: int = 1000):
        """Test DataManager latency for various operations"""
        logger.info(f"🔍 Testing DataManager latency with {iterations} iterations...")
        
        for i in range(iterations):
            for symbol in symbols:
                # Test market data retrieval
                _, measurement = self.profiler.measure_sync_operation(
                    "DataManager", "get_market_data",
                    data_manager.get_market_data, symbol
                )
                
                # Test historical data query
                from datetime import datetime, timedelta
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)  # 7 days of data
                _, measurement = self.profiler.measure_sync_operation(
                    "DataManager", "get_historical_data",
                    data_manager.get_historical_data, symbol, start_date, end_date, "1min"
                )
                
                if i % 100 == 0:
                    logger.info(f"  Completed {i}/{iterations} DataManager tests")
    
    async def test_risk_manager_latency(self, risk_manager, iterations: int = 1000):
        """Test CentralRiskManager latency for authorization operations"""
        logger.info(f"🔍 Testing RiskManager latency with {iterations} iterations...")
        
        from core_engine.system.central_risk_manager import TradingDecisionRequest, TradingDecisionType
        
        for i in range(iterations):
            # Create test request
            request = TradingDecisionRequest(
                decision_type=TradingDecisionType.POSITION_ENTRY,
                symbol="AAPL",
                side="buy",
                quantity=100,
                strategy_id="test_strategy",
                confidence=0.8
            )
            
            # Test authorization
            _, measurement = await self.profiler.measure_async_operation(
                "RiskManager", "authorize_trading_decision",
                risk_manager.authorize_trading_decision, request
            )
            
            if i % 100 == 0:
                logger.info(f"  Completed {i}/{iterations} RiskManager tests")
    
    async def test_execution_engine_latency(self, execution_engine, iterations: int = 500):
        """Test ExecutionEngine latency for trade execution"""
        logger.info(f"🔍 Testing ExecutionEngine latency with {iterations} iterations...")
        
        # Note: This would test execution planning, not actual trades
        for i in range(iterations):
            # Test execution plan creation
            _, measurement = await self.profiler.measure_async_operation(
                "ExecutionEngine", "create_execution_plan",
                execution_engine.create_execution_plan, "AAPL", "buy", 100
            )
            
            if i % 50 == 0:
                logger.info(f"  Completed {i}/{iterations} ExecutionEngine tests")
    
    async def test_strategy_manager_latency(self, strategy_manager, symbols: List[str], iterations: int = 500):
        """Test StrategyManager latency for signal generation"""
        logger.info(f"🔍 Testing StrategyManager latency with {iterations} iterations...")
        
        for i in range(iterations):
            # Test signal generation
            _, measurement = await self.profiler.measure_async_operation(
                "StrategyManager", "generate_signals",
                strategy_manager.generate_signals, symbols
            )
            
            if i % 50 == 0:
                logger.info(f"  Completed {i}/{iterations} StrategyManager tests")

# Context manager for easy latency measurement
class LatencyContext:
    """Context manager for measuring operation latency"""
    
    def __init__(self, profiler: LatencyProfiler, component_name: str, operation_name: str):
        self.profiler = profiler
        self.component_name = component_name
        self.operation_name = operation_name
        self.measurement_id = None
        
    def __enter__(self):
        self.measurement_id = self.profiler.start_measurement(
            self.component_name, self.operation_name
        )
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        context = {}
        if exc_type:
            context['error'] = str(exc_val)
        self.profiler.end_measurement(self.measurement_id, context)

# Decorator for automatic latency measurement
def measure_latency(component_name: str, operation_name: str, profiler: LatencyProfiler):
    """Decorator to automatically measure function latency"""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                _, measurement = await profiler.measure_async_operation(
                    component_name, operation_name, func, *args, **kwargs
                )
                return _
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                result, measurement = profiler.measure_sync_operation(
                    component_name, operation_name, func, *args, **kwargs
                )
                return result
            return sync_wrapper
    return decorator

if __name__ == "__main__":
    # Example usage
    async def example_latency_test():
        profiler = LatencyProfiler()
        
        # Simulate some operations
        for i in range(100):
            with LatencyContext(profiler, "TestComponent", "test_operation"):
                await asyncio.sleep(0.001)  # Simulate 1ms operation
                
        # Generate report
        report = profiler.generate_performance_report()
        print("Latency Test Report:")
        print(f"Total measurements: {report['total_measurements']}")
        
        for component, operations in report['components'].items():
            print(f"\n{component}:")
            for operation, stats in operations.items():
                print(f"  {operation}:")
                print(f"    Mean: {stats['latency_statistics_us']['mean']} μs")
                print(f"    P99: {stats['percentiles_us']['p99']} μs")
                print(f"    Throughput: {stats['performance_indicators']['throughput_ops_per_sec']} ops/sec")
    
    asyncio.run(example_latency_test())
