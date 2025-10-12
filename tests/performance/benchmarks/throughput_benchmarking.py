"""
Advanced Throughput Benchmarking Framework for Core Engine Components

This module provides comprehensive throughput measurement and analysis for
high-frequency trading operations, focusing on operations per second, 
concurrent processing capabilities, and scalability characteristics.
"""

import asyncio
import time
import threading
import multiprocessing
import sys
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict, deque
import logging
import statistics
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil

logger = logging.getLogger(__name__)

@dataclass
class ThroughputMeasurement:
    """Single throughput measurement"""
    component_name: str
    operation_name: str
    timestamp: datetime
    
    # Core throughput metrics
    operations_completed: int
    duration_seconds: float
    throughput_ops_per_sec: float
    
    # Concurrency metrics
    concurrent_workers: int
    queue_depth: int
    
    # Resource utilization
    cpu_usage_percent: float
    memory_usage_mb: float
    
    # Performance characteristics
    average_latency_ms: float
    p95_latency_ms: float
    error_rate: float
    
    # Context information
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ThroughputStatistics:
    """Statistical analysis of throughput measurements"""
    component_name: str
    operation_name: str
    measurement_count: int
    
    # Throughput statistics
    peak_throughput_ops_per_sec: float
    average_throughput_ops_per_sec: float
    min_throughput_ops_per_sec: float
    throughput_std_dev: float
    
    # Scalability metrics
    linear_scalability_factor: float  # How well it scales with workers
    optimal_worker_count: int
    efficiency_at_optimal: float
    
    # Performance consistency
    throughput_stability: float  # Lower std dev = more stable
    performance_degradation: float  # Performance loss under load
    
    # Resource efficiency
    cpu_efficiency: float  # Ops per CPU percent
    memory_efficiency: float  # Ops per MB
    
    # Quality metrics
    average_error_rate: float
    reliability_score: float

@dataclass
class LoadTestConfiguration:
    """Configuration for load testing scenarios"""
    component_name: str
    operation_name: str
    
    # Load parameters
    target_operations: int
    concurrent_workers: List[int]  # Different concurrency levels to test
    duration_seconds: int
    ramp_up_seconds: int
    
    # Test data
    test_data_generator: Optional[Callable] = None
    operation_function: Optional[Callable] = None
    
    # Constraints
    max_cpu_percent: float = 90.0
    max_memory_mb: float = 8192.0
    max_error_rate: float = 0.05
    
    # Advanced options
    enable_warmup: bool = True
    warmup_operations: int = 100
    enable_cooldown: bool = True
    cooldown_seconds: int = 5

class ThroughputBenchmarker:
    """Advanced throughput benchmarking system"""
    
    def __init__(self, max_measurements: int = 10000):
        self.measurements: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_measurements))
        self.active_tests: Dict[str, datetime] = {}
        self.lock = threading.Lock()
        self.max_measurements = max_measurements
        
    def _get_system_metrics(self) -> Dict[str, float]:
        """Get current system resource metrics"""
        process = psutil.Process()
        return {
            'cpu_percent': process.cpu_percent(),
            'memory_mb': process.memory_info().rss / 1024 / 1024,
            'system_cpu_percent': psutil.cpu_percent(),
            'system_memory_percent': psutil.virtual_memory().percent
        }
    
    async def benchmark_async_operation(self, config: LoadTestConfiguration) -> List[ThroughputMeasurement]:
        """Benchmark an asynchronous operation with various concurrency levels"""
        logger.info(f"🚀 Benchmarking {config.component_name}::{config.operation_name}")
        logger.info(f"   Target operations: {config.target_operations}")
        logger.info(f"   Concurrency levels: {config.concurrent_workers}")
        
        measurements = []
        
        for worker_count in config.concurrent_workers:
            logger.info(f"   Testing with {worker_count} concurrent workers...")
            
            # Warmup if enabled
            if config.enable_warmup:
                await self._warmup_async(config, worker_count)
            
            # Run the actual benchmark
            measurement = await self._run_async_benchmark(config, worker_count)
            measurements.append(measurement)
            
            # Cooldown if enabled
            if config.enable_cooldown:
                await asyncio.sleep(config.cooldown_seconds)
                
            # Check if we should stop due to resource constraints
            if (measurement.cpu_usage_percent > config.max_cpu_percent or
                measurement.memory_usage_mb > config.max_memory_mb or
                measurement.error_rate > config.max_error_rate):
                logger.warning(f"   Stopping benchmark due to resource constraints")
                break
        
        # Store measurements
        key = f"{config.component_name}::{config.operation_name}"
        with self.lock:
            self.measurements[key].extend(measurements)
            
        return measurements
    
    async def _warmup_async(self, config: LoadTestConfiguration, worker_count: int):
        """Perform warmup operations"""
        logger.info(f"     Warming up with {config.warmup_operations} operations...")
        
        semaphore = asyncio.Semaphore(worker_count)
        
        async def warmup_operation():
            async with semaphore:
                if config.test_data_generator:
                    test_data = config.test_data_generator()
                    await config.operation_function(test_data)
                else:
                    await config.operation_function()
        
        # Run warmup operations
        warmup_tasks = [warmup_operation() for _ in range(config.warmup_operations)]
        await asyncio.gather(*warmup_tasks, return_exceptions=True)
    
    async def _run_async_benchmark(self, config: LoadTestConfiguration, worker_count: int) -> ThroughputMeasurement:
        """Run async benchmark with specified worker count"""
        start_time = time.perf_counter()
        start_timestamp = datetime.now()
        
        # Track metrics
        completed_operations = 0
        error_count = 0
        latencies = []
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(worker_count)
        
        async def benchmark_operation():
            nonlocal completed_operations, error_count
            
            async with semaphore:
                operation_start = time.perf_counter()
                
                try:
                    if config.test_data_generator:
                        test_data = config.test_data_generator()
                        await config.operation_function(test_data)
                    else:
                        await config.operation_function()
                        
                    operation_end = time.perf_counter()
                    latency_ms = (operation_end - operation_start) * 1000
                    latencies.append(latency_ms)
                    completed_operations += 1
                    
                except Exception as e:
                    error_count += 1
                    logger.debug(f"Operation error: {e}")
        
        # Create and run benchmark tasks
        tasks = [benchmark_operation() for _ in range(config.target_operations)]
        
        # Run with timeout if duration is specified
        if config.duration_seconds > 0:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=config.duration_seconds
                )
            except asyncio.TimeoutError:
                logger.info(f"     Benchmark timed out after {config.duration_seconds} seconds")
        else:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Calculate metrics
        end_time = time.perf_counter()
        duration_seconds = end_time - start_time
        throughput_ops_per_sec = completed_operations / duration_seconds if duration_seconds > 0 else 0
        
        # Get system metrics
        system_metrics = self._get_system_metrics()
        
        # Calculate latency statistics
        average_latency_ms = statistics.mean(latencies) if latencies else 0
        p95_latency_ms = np.percentile(latencies, 95) if latencies else 0
        
        # Calculate error rate
        error_rate = error_count / config.target_operations if config.target_operations > 0 else 0
        
        measurement = ThroughputMeasurement(
            component_name=config.component_name,
            operation_name=config.operation_name,
            timestamp=start_timestamp,
            operations_completed=completed_operations,
            duration_seconds=duration_seconds,
            throughput_ops_per_sec=throughput_ops_per_sec,
            concurrent_workers=worker_count,
            queue_depth=0,  # Not applicable for async
            cpu_usage_percent=system_metrics['cpu_percent'],
            memory_usage_mb=system_metrics['memory_mb'],
            average_latency_ms=average_latency_ms,
            p95_latency_ms=p95_latency_ms,
            error_rate=error_rate,
            context={
                'target_operations': config.target_operations,
                'actual_operations': completed_operations,
                'error_count': error_count
            }
        )
        
        logger.info(f"     Completed: {throughput_ops_per_sec:.1f} ops/sec "
                   f"(errors: {error_rate:.2%}, latency: {average_latency_ms:.2f}ms)")
        
        return measurement
    
    def benchmark_sync_operation(self, config: LoadTestConfiguration) -> List[ThroughputMeasurement]:
        """Benchmark a synchronous operation using thread pool"""
        logger.info(f"🚀 Benchmarking sync {config.component_name}::{config.operation_name}")
        
        measurements = []
        
        for worker_count in config.concurrent_workers:
            logger.info(f"   Testing with {worker_count} threads...")
            
            # Warmup if enabled
            if config.enable_warmup:
                self._warmup_sync(config, worker_count)
            
            # Run the actual benchmark
            measurement = self._run_sync_benchmark(config, worker_count)
            measurements.append(measurement)
            
            # Cooldown if enabled
            if config.enable_cooldown:
                time.sleep(config.cooldown_seconds)
        
        # Store measurements
        key = f"{config.component_name}::{config.operation_name}"
        with self.lock:
            self.measurements[key].extend(measurements)
            
        return measurements
    
    def _warmup_sync(self, config: LoadTestConfiguration, worker_count: int):
        """Perform warmup operations for sync functions"""
        logger.info(f"     Warming up with {config.warmup_operations} operations...")
        
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = []
            
            for _ in range(config.warmup_operations):
                if config.test_data_generator:
                    test_data = config.test_data_generator()
                    future = executor.submit(config.operation_function, test_data)
                else:
                    future = executor.submit(config.operation_function)
                futures.append(future)
            
            # Wait for completion
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    pass  # Ignore warmup errors
    
    def _run_sync_benchmark(self, config: LoadTestConfiguration, worker_count: int) -> ThroughputMeasurement:
        """Run sync benchmark with specified thread count"""
        start_time = time.perf_counter()
        start_timestamp = datetime.now()
        
        # Track metrics
        completed_operations = 0
        error_count = 0
        latencies = []
        
        # Use thread pool for concurrency
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = []
            
            # Submit all operations
            for _ in range(config.target_operations):
                if config.test_data_generator:
                    test_data = config.test_data_generator()
                    future = executor.submit(self._timed_operation, config.operation_function, test_data)
                else:
                    future = executor.submit(self._timed_operation, config.operation_function)
                futures.append(future)
            
            # Collect results
            for future in as_completed(futures, timeout=config.duration_seconds if config.duration_seconds > 0 else None):
                try:
                    latency_ms = future.result()
                    latencies.append(latency_ms)
                    completed_operations += 1
                except Exception as e:
                    error_count += 1
                    logger.debug(f"Operation error: {e}")
        
        # Calculate metrics
        end_time = time.perf_counter()
        duration_seconds = end_time - start_time
        throughput_ops_per_sec = completed_operations / duration_seconds if duration_seconds > 0 else 0
        
        # Get system metrics
        system_metrics = self._get_system_metrics()
        
        # Calculate latency statistics
        average_latency_ms = statistics.mean(latencies) if latencies else 0
        p95_latency_ms = np.percentile(latencies, 95) if latencies else 0
        
        # Calculate error rate
        error_rate = error_count / config.target_operations if config.target_operations > 0 else 0
        
        measurement = ThroughputMeasurement(
            component_name=config.component_name,
            operation_name=config.operation_name,
            timestamp=start_timestamp,
            operations_completed=completed_operations,
            duration_seconds=duration_seconds,
            throughput_ops_per_sec=throughput_ops_per_sec,
            concurrent_workers=worker_count,
            queue_depth=len(futures) if 'futures' in locals() else 0,
            cpu_usage_percent=system_metrics['cpu_percent'],
            memory_usage_mb=system_metrics['memory_mb'],
            average_latency_ms=average_latency_ms,
            p95_latency_ms=p95_latency_ms,
            error_rate=error_rate,
            context={
                'target_operations': config.target_operations,
                'actual_operations': completed_operations,
                'error_count': error_count
            }
        )
        
        logger.info(f"     Completed: {throughput_ops_per_sec:.1f} ops/sec "
                   f"(errors: {error_rate:.2%}, latency: {average_latency_ms:.2f}ms)")
        
        return measurement
    
    def _timed_operation(self, operation_func: Callable, *args, **kwargs) -> float:
        """Execute operation and return latency in milliseconds"""
        start_time = time.perf_counter()
        operation_func(*args, **kwargs)
        end_time = time.perf_counter()
        return (end_time - start_time) * 1000
    
    def calculate_statistics(self, component_name: str, operation_name: str) -> Optional[ThroughputStatistics]:
        """Calculate comprehensive throughput statistics"""
        key = f"{component_name}::{operation_name}"
        
        with self.lock:
            measurements = list(self.measurements.get(key, []))
            
        if len(measurements) < 2:
            return None
            
        # Extract throughput values
        throughputs = [m.throughput_ops_per_sec for m in measurements]
        worker_counts = [m.concurrent_workers for m in measurements]
        cpu_usages = [m.cpu_usage_percent for m in measurements]
        memory_usages = [m.memory_usage_mb for m in measurements]
        error_rates = [m.error_rate for m in measurements]
        
        # Basic throughput statistics
        peak_throughput = max(throughputs)
        average_throughput = statistics.mean(throughputs)
        min_throughput = min(throughputs)
        throughput_std_dev = statistics.stdev(throughputs) if len(throughputs) > 1 else 0
        
        # Find optimal worker count (highest throughput)
        optimal_idx = throughputs.index(peak_throughput)
        optimal_worker_count = worker_counts[optimal_idx]
        
        # Calculate scalability factor (linear regression of throughput vs workers)
        if len(set(worker_counts)) > 1:
            correlation = np.corrcoef(worker_counts, throughputs)[0, 1]
            linear_scalability_factor = max(0, correlation)
        else:
            linear_scalability_factor = 0.0
        
        # Calculate efficiency at optimal point
        efficiency_at_optimal = peak_throughput / optimal_worker_count if optimal_worker_count > 0 else 0
        
        # Calculate performance stability
        throughput_stability = 100 - min(100, (throughput_std_dev / average_throughput) * 100) if average_throughput > 0 else 0
        
        # Calculate performance degradation (compare first vs last measurement)
        if len(throughputs) > 1:
            performance_degradation = max(0, (throughputs[0] - throughputs[-1]) / throughputs[0] * 100)
        else:
            performance_degradation = 0
        
        # Calculate resource efficiency
        avg_cpu = statistics.mean(cpu_usages) if cpu_usages else 1
        avg_memory = statistics.mean(memory_usages) if memory_usages else 1
        cpu_efficiency = average_throughput / avg_cpu if avg_cpu > 0 else 0
        memory_efficiency = average_throughput / avg_memory if avg_memory > 0 else 0
        
        # Calculate quality metrics
        average_error_rate = statistics.mean(error_rates) if error_rates else 0
        reliability_score = max(0, 100 - (average_error_rate * 100))
        
        return ThroughputStatistics(
            component_name=component_name,
            operation_name=operation_name,
            measurement_count=len(measurements),
            peak_throughput_ops_per_sec=peak_throughput,
            average_throughput_ops_per_sec=average_throughput,
            min_throughput_ops_per_sec=min_throughput,
            throughput_std_dev=throughput_std_dev,
            linear_scalability_factor=linear_scalability_factor,
            optimal_worker_count=optimal_worker_count,
            efficiency_at_optimal=efficiency_at_optimal,
            throughput_stability=throughput_stability,
            performance_degradation=performance_degradation,
            cpu_efficiency=cpu_efficiency,
            memory_efficiency=memory_efficiency,
            average_error_rate=average_error_rate,
            reliability_score=reliability_score
        )
    
    def generate_throughput_report(self) -> Dict[str, Any]:
        """Generate comprehensive throughput analysis report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'system_info': {
                'cpu_count': multiprocessing.cpu_count(),
                'memory_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024,
                'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            },
            'components': {}
        }
        
        total_measurements = 0
        peak_throughputs = []
        
        for key in self.measurements.keys():
            component_name, operation_name = key.split("::", 1)
            stats = self.calculate_statistics(component_name, operation_name)
            
            if stats:
                if component_name not in report['components']:
                    report['components'][component_name] = {}
                    
                report['components'][component_name][operation_name] = {
                    'throughput_statistics': {
                        'peak_ops_per_sec': round(stats.peak_throughput_ops_per_sec, 1),
                        'average_ops_per_sec': round(stats.average_throughput_ops_per_sec, 1),
                        'min_ops_per_sec': round(stats.min_throughput_ops_per_sec, 1),
                        'std_dev': round(stats.throughput_std_dev, 1)
                    },
                    'scalability_metrics': {
                        'linear_scalability_factor': round(stats.linear_scalability_factor, 2),
                        'optimal_worker_count': stats.optimal_worker_count,
                        'efficiency_at_optimal': round(stats.efficiency_at_optimal, 1),
                        'throughput_stability': round(stats.throughput_stability, 1)
                    },
                    'resource_efficiency': {
                        'cpu_efficiency': round(stats.cpu_efficiency, 2),
                        'memory_efficiency': round(stats.memory_efficiency, 2),
                        'performance_degradation': round(stats.performance_degradation, 1)
                    },
                    'quality_metrics': {
                        'average_error_rate': round(stats.average_error_rate, 4),
                        'reliability_score': round(stats.reliability_score, 1)
                    },
                    'measurement_count': stats.measurement_count
                }
                
                total_measurements += stats.measurement_count
                peak_throughputs.append(stats.peak_throughput_ops_per_sec)
        
        # Add summary statistics
        report['summary'] = {
            'total_measurements': total_measurements,
            'components_tested': len(report['components']),
            'highest_throughput_ops_per_sec': max(peak_throughputs) if peak_throughputs else 0,
            'average_peak_throughput': round(statistics.mean(peak_throughputs), 1) if peak_throughputs else 0
        }
        
        return report

class ComponentThroughputTester:
    """Specialized throughput tester for core engine components"""
    
    def __init__(self, benchmarker: ThroughputBenchmarker):
        self.benchmarker = benchmarker
        
    async def test_data_manager_throughput(self, data_manager, symbols: List[str]):
        """Test DataManager throughput for data retrieval operations"""
        logger.info("🚀 Testing DataManager throughput...")
        
        # Test market data retrieval throughput
        def generate_test_data():
            return np.random.choice(symbols)
        
        async def get_market_data_operation(symbol):
            return data_manager.get_market_data(symbol)
        
        config = LoadTestConfiguration(
            component_name="DataManager",
            operation_name="get_market_data",
            target_operations=1000,
            concurrent_workers=[1, 2, 4, 8, 16],
            duration_seconds=30,
            ramp_up_seconds=5,
            test_data_generator=generate_test_data,
            operation_function=get_market_data_operation
        )
        
        measurements = await self.benchmarker.benchmark_async_operation(config)
        return measurements
    
    async def test_risk_manager_throughput(self, risk_manager):
        """Test RiskManager throughput for authorization operations"""
        logger.info("🚀 Testing RiskManager throughput...")
        
        from core_engine.system.central_risk_manager import TradingDecisionRequest, TradingDecisionType
        
        def generate_test_request():
            return TradingDecisionRequest(
                decision_type=TradingDecisionType.POSITION_ENTRY,
                symbol=np.random.choice(["AAPL", "MSFT", "GOOGL", "TSLA"]),
                side=np.random.choice(["buy", "sell"]),
                quantity=np.random.randint(100, 1000),
                strategy_id="throughput_test",
                confidence=np.random.uniform(0.6, 0.9)
            )
        
        async def authorize_operation(request):
            return await risk_manager.authorize_trading_decision(request)
        
        config = LoadTestConfiguration(
            component_name="RiskManager",
            operation_name="authorize_trading_decision",
            target_operations=2000,
            concurrent_workers=[1, 2, 4, 8],
            duration_seconds=20,
            ramp_up_seconds=3,
            test_data_generator=generate_test_request,
            operation_function=authorize_operation
        )
        
        measurements = await self.benchmarker.benchmark_async_operation(config)
        return measurements
    
    async def test_strategy_manager_throughput(self, strategy_manager, symbols: List[str]):
        """Test StrategyManager throughput for signal generation"""
        logger.info("🚀 Testing StrategyManager throughput...")
        
        async def generate_signals_operation():
            return await strategy_manager.generate_signals(symbols)
        
        config = LoadTestConfiguration(
            component_name="StrategyManager",
            operation_name="generate_signals",
            target_operations=500,
            concurrent_workers=[1, 2, 4],
            duration_seconds=60,
            ramp_up_seconds=10,
            operation_function=generate_signals_operation
        )
        
        measurements = await self.benchmarker.benchmark_async_operation(config)
        return measurements

if __name__ == "__main__":
    # Example usage
    import sys
    
    async def example_throughput_test():
        benchmarker = ThroughputBenchmarker()
        
        # Simulate a simple async operation
        async def test_operation(data=None):
            await asyncio.sleep(0.001)  # Simulate 1ms operation
            return "result"
        
        def generate_test_data():
            return f"test_data_{np.random.randint(1000)}"
        
        config = LoadTestConfiguration(
            component_name="TestComponent",
            operation_name="test_operation",
            target_operations=1000,
            concurrent_workers=[1, 2, 4, 8, 16],
            duration_seconds=10,
            ramp_up_seconds=2,
            test_data_generator=generate_test_data,
            operation_function=test_operation
        )
        
        measurements = await benchmarker.benchmark_async_operation(config)
        
        # Generate report
        report = benchmarker.generate_throughput_report()
        print("Throughput Test Report:")
        print(f"System: {report['system_info']['cpu_count']} CPUs, {report['system_info']['memory_gb']:.1f} GB RAM")
        
        for component, operations in report['components'].items():
            print(f"\n{component}:")
            for operation, stats in operations.items():
                print(f"  {operation}:")
                print(f"    Peak throughput: {stats['throughput_statistics']['peak_ops_per_sec']} ops/sec")
                print(f"    Optimal workers: {stats['scalability_metrics']['optimal_worker_count']}")
                print(f"    Reliability: {stats['quality_metrics']['reliability_score']}%")
    
    asyncio.run(example_throughput_test())
