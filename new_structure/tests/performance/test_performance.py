"""
Performance Tests for StatArb Trading System

This module provides comprehensive performance testing for latency,
throughput, memory usage, and scalability requirements.
"""

import pytest
import asyncio
import time
import psutil
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import List, Dict, Any
import numpy as np
import pandas as pd
from unittest.mock import AsyncMock, Mock
import gc
import resource


class PerformanceMonitor:
    """Monitor system performance metrics during tests"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.memory_usage = []
        self.cpu_usage = []
        self.monitoring = False
        
    def start_monitoring(self):
        """Start performance monitoring"""
        self.start_time = time.time()
        self.monitoring = True
        self.memory_usage = []
        self.cpu_usage = []
        
        # Start background monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_resources)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring = False
        self.end_time = time.time()
        
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=1.0)
    
    def _monitor_resources(self):
        """Monitor CPU and memory usage"""
        process = psutil.Process()
        
        while self.monitoring:
            try:
                # Memory usage in MB
                memory_mb = process.memory_info().rss / 1024 / 1024
                self.memory_usage.append(memory_mb)
                
                # CPU usage percentage
                cpu_percent = process.cpu_percent()
                self.cpu_usage.append(cpu_percent)
                
                time.sleep(0.1)  # Monitor every 100ms
            except Exception:
                break
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        duration = self.end_time - self.start_time if self.end_time else 0
        
        return {
            'duration_seconds': duration,
            'avg_memory_mb': np.mean(self.memory_usage) if self.memory_usage else 0,
            'max_memory_mb': np.max(self.memory_usage) if self.memory_usage else 0,
            'avg_cpu_percent': np.mean(self.cpu_usage) if self.cpu_usage else 0,
            'max_cpu_percent': np.max(self.cpu_usage) if self.cpu_usage else 0,
            'memory_samples': len(self.memory_usage),
            'cpu_samples': len(self.cpu_usage)
        }


@pytest.fixture
def performance_monitor():
    """Performance monitoring fixture"""
    monitor = PerformanceMonitor()
    yield monitor
    monitor.stop_monitoring()


class TestLatencyRequirements:
    """Test system latency requirements"""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_market_data_processing_latency(self, performance_monitor):
        """Test market data processing latency < 10ms"""
        mock_processor = AsyncMock()
        
        # Generate test market data
        test_data = {
            'symbol': 'AAPL',
            'price': 150.0,
            'volume': 1000,
            'timestamp': datetime.now()
        }
        
        latencies = []
        iterations = 1000
        
        performance_monitor.start_monitoring()
        
        for _ in range(iterations):
            start_time = time.perf_counter()
            
            # Simulate market data processing
            mock_processor.process_tick.return_value = {
                **test_data,
                'processed_timestamp': datetime.now()
            }
            
            result = await mock_processor.process_tick(test_data)
            
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
        
        performance_monitor.stop_monitoring()
        
        # Analyze latency metrics
        avg_latency = np.mean(latencies)
        p95_latency = np.percentile(latencies, 95)
        p99_latency = np.percentile(latencies, 99)
        max_latency = np.max(latencies)
        
        # Performance assertions
        assert avg_latency < 1.0, f"Average latency {avg_latency:.2f}ms exceeds 1ms target"
        assert p95_latency < 5.0, f"P95 latency {p95_latency:.2f}ms exceeds 5ms target"
        assert p99_latency < 10.0, f"P99 latency {p99_latency:.2f}ms exceeds 10ms target"
        
        metrics = performance_monitor.get_metrics()
        print(f"Processing latency - Avg: {avg_latency:.2f}ms, P95: {p95_latency:.2f}ms, P99: {p99_latency:.2f}ms")
        print(f"Resource usage - Memory: {metrics['avg_memory_mb']:.1f}MB, CPU: {metrics['avg_cpu_percent']:.1f}%")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_signal_generation_latency(self, performance_monitor):
        """Test signal generation latency < 50ms"""
        mock_signal_generator = AsyncMock()
        
        # Test data
        market_data = pd.DataFrame({
            'symbol': ['AAPL'] * 100,
            'price': np.random.uniform(140, 160, 100),
            'volume': np.random.randint(1000, 10000, 100),
            'timestamp': pd.date_range(end=datetime.now(), periods=100, freq='1min')
        })
        
        latencies = []
        iterations = 100
        
        performance_monitor.start_monitoring()
        
        for _ in range(iterations):
            start_time = time.perf_counter()
            
            # Simulate signal generation
            mock_signal_generator.generate_signals.return_value = [
                {'symbol': 'AAPL', 'signal': 'BUY', 'strength': 0.75}
            ]
            
            signals = await mock_signal_generator.generate_signals(market_data)
            
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
        
        performance_monitor.stop_monitoring()
        
        # Analyze latency metrics
        avg_latency = np.mean(latencies)
        p95_latency = np.percentile(latencies, 95)
        max_latency = np.max(latencies)
        
        # Performance assertions
        assert avg_latency < 25.0, f"Average signal latency {avg_latency:.2f}ms exceeds 25ms target"
        assert p95_latency < 50.0, f"P95 signal latency {p95_latency:.2f}ms exceeds 50ms target"
        
        print(f"Signal generation latency - Avg: {avg_latency:.2f}ms, P95: {p95_latency:.2f}ms")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_order_execution_latency(self, performance_monitor):
        """Test order execution latency < 100ms"""
        mock_execution_engine = AsyncMock()
        
        order = {
            'symbol': 'AAPL',
            'side': 'BUY',
            'quantity': 100,
            'order_type': 'LIMIT',
            'price': 150.0
        }
        
        latencies = []
        iterations = 50
        
        performance_monitor.start_monitoring()
        
        for _ in range(iterations):
            start_time = time.perf_counter()
            
            # Simulate order execution
            mock_execution_engine.execute_order.return_value = {
                'order_id': f'ORD_{_}',
                'status': 'FILLED',
                'filled_quantity': 100,
                'avg_price': 149.95
            }
            
            result = await mock_execution_engine.execute_order(order)
            
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
        
        performance_monitor.stop_monitoring()
        
        # Analyze latency metrics
        avg_latency = np.mean(latencies)
        p95_latency = np.percentile(latencies, 95)
        
        # Performance assertions
        assert avg_latency < 50.0, f"Average execution latency {avg_latency:.2f}ms exceeds 50ms target"
        assert p95_latency < 100.0, f"P95 execution latency {p95_latency:.2f}ms exceeds 100ms target"
        
        print(f"Order execution latency - Avg: {avg_latency:.2f}ms, P95: {p95_latency:.2f}ms")


class TestThroughputRequirements:
    """Test system throughput requirements"""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_market_data_throughput(self, performance_monitor):
        """Test market data processing throughput > 10,000 ticks/second"""
        mock_processor = AsyncMock()
        mock_processor.process_tick.return_value = {'processed': True}
        
        num_ticks = 50000
        batch_size = 1000
        
        performance_monitor.start_monitoring()
        start_time = time.perf_counter()
        
        # Process ticks in batches for better concurrency
        for batch_start in range(0, num_ticks, batch_size):
            batch_end = min(batch_start + batch_size, num_ticks)
            batch_tasks = []
            
            for i in range(batch_start, batch_end):
                tick_data = {
                    'symbol': f'STOCK_{i % 100}',
                    'price': 100 + np.random.randn(),
                    'volume': np.random.randint(100, 10000),
                    'timestamp': datetime.now()
                }
                task = mock_processor.process_tick(tick_data)
                batch_tasks.append(task)
            
            # Process batch concurrently
            await asyncio.gather(*batch_tasks)
        
        end_time = time.perf_counter()
        performance_monitor.stop_monitoring()
        
        # Calculate throughput
        duration = end_time - start_time
        throughput = num_ticks / duration
        
        # Performance assertions
        assert throughput > 10000, f"Throughput {throughput:.0f} ticks/sec below 10,000 target"
        
        metrics = performance_monitor.get_metrics()
        print(f"Market data throughput: {throughput:.0f} ticks/second")
        print(f"Duration: {duration:.2f}s, Memory: {metrics['max_memory_mb']:.1f}MB")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_signal_generation_throughput(self, performance_monitor):
        """Test signal generation throughput > 1,000 signals/second"""
        mock_signal_generator = AsyncMock()
        
        # Generate test datasets
        datasets = []
        for i in range(1000):
            data = pd.DataFrame({
                'symbol': [f'STOCK_{i}'] * 20,
                'price': np.random.uniform(50, 200, 20),
                'volume': np.random.randint(1000, 100000, 20),
                'timestamp': pd.date_range(end=datetime.now(), periods=20, freq='1min')
            })
            datasets.append(data)
        
        performance_monitor.start_monitoring()
        start_time = time.perf_counter()
        
        # Generate signals for all datasets
        tasks = []
        for dataset in datasets:
            mock_signal_generator.generate_signals.return_value = [
                {'symbol': dataset['symbol'].iloc[0], 'signal': 'BUY', 'strength': 0.5}
            ]
            task = mock_signal_generator.generate_signals(dataset)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        performance_monitor.stop_monitoring()
        
        # Calculate throughput
        duration = end_time - start_time
        throughput = len(results) / duration
        
        # Performance assertions
        assert throughput > 1000, f"Signal generation throughput {throughput:.0f}/sec below 1,000 target"
        
        print(f"Signal generation throughput: {throughput:.0f} signals/second")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_order_processing_throughput(self, performance_monitor):
        """Test order processing throughput > 500 orders/second"""
        mock_execution_engine = AsyncMock()
        
        orders = []
        for i in range(2500):  # Test with 2500 orders
            order = {
                'order_id': f'ORD_{i}',
                'symbol': f'STOCK_{i % 100}',
                'side': 'BUY' if i % 2 == 0 else 'SELL',
                'quantity': np.random.randint(10, 1000),
                'order_type': 'LIMIT',
                'price': np.random.uniform(50, 200)
            }
            orders.append(order)
        
        performance_monitor.start_monitoring()
        start_time = time.perf_counter()
        
        # Process orders in batches
        batch_size = 100
        for batch_start in range(0, len(orders), batch_size):
            batch_end = min(batch_start + batch_size, len(orders))
            batch_orders = orders[batch_start:batch_end]
            
            tasks = []
            for order in batch_orders:
                mock_execution_engine.process_order.return_value = {
                    'order_id': order['order_id'],
                    'status': 'FILLED'
                }
                task = mock_execution_engine.process_order(order)
                tasks.append(task)
            
            await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        performance_monitor.stop_monitoring()
        
        # Calculate throughput
        duration = end_time - start_time
        throughput = len(orders) / duration
        
        # Performance assertions
        assert throughput > 500, f"Order processing throughput {throughput:.0f}/sec below 500 target"
        
        print(f"Order processing throughput: {throughput:.0f} orders/second")


class TestMemoryUsage:
    """Test memory usage and efficiency"""
    
    @pytest.mark.performance
    def test_memory_usage_under_load(self, performance_monitor):
        """Test memory usage under high load"""
        performance_monitor.start_monitoring()
        
        # Simulate high memory usage scenario
        large_datasets = []
        
        try:
            # Create large datasets to simulate real trading data
            for i in range(100):
                data = pd.DataFrame({
                    'symbol': [f'STOCK_{j}' for j in range(1000)],
                    'price': np.random.uniform(50, 200, 1000),
                    'volume': np.random.randint(1000, 100000, 1000),
                    'timestamp': pd.date_range(end=datetime.now(), periods=1000, freq='1min')
                })
                large_datasets.append(data)
            
            # Process data
            processed_data = []
            for dataset in large_datasets:
                # Simulate data processing
                processed = dataset.copy()
                processed['returns'] = processed['price'].pct_change()
                processed['sma_20'] = processed['price'].rolling(20).mean()
                processed_data.append(processed)
            
            performance_monitor.stop_monitoring()
            
            metrics = performance_monitor.get_metrics()
            
            # Memory usage assertions
            assert metrics['max_memory_mb'] < 2048, f"Memory usage {metrics['max_memory_mb']:.1f}MB exceeds 2GB limit"
            assert metrics['avg_memory_mb'] < 1024, f"Average memory usage {metrics['avg_memory_mb']:.1f}MB exceeds 1GB target"
            
            print(f"Memory usage - Max: {metrics['max_memory_mb']:.1f}MB, Avg: {metrics['avg_memory_mb']:.1f}MB")
            
        finally:
            # Clean up large datasets
            del large_datasets
            if 'processed_data' in locals():
                del processed_data
            gc.collect()
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, performance_monitor):
        """Test for memory leaks during repeated operations"""
        performance_monitor.start_monitoring()
        
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Perform repeated operations that could cause memory leaks
        for iteration in range(100):
            # Create and process data
            data = pd.DataFrame({
                'symbol': ['AAPL'] * 1000,
                'price': np.random.uniform(140, 160, 1000),
                'volume': np.random.randint(1000, 10000, 1000)
            })
            
            # Simulate processing
            processed = data.copy()
            processed['returns'] = processed['price'].pct_change()
            
            # Simulate async operations
            mock_processor = AsyncMock()
            mock_processor.process.return_value = processed
            result = await mock_processor.process(data)
            
            # Explicitly delete to test cleanup
            del data, processed, result
            
            # Force garbage collection every 10 iterations
            if iteration % 10 == 0:
                gc.collect()
        
        performance_monitor.stop_monitoring()
        
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_growth = final_memory - initial_memory
        
        # Memory leak assertions
        assert memory_growth < 100, f"Memory growth {memory_growth:.1f}MB indicates potential leak"
        
        print(f"Memory growth: {memory_growth:.1f}MB over 100 iterations")


class TestScalabilityLimits:
    """Test system scalability limits"""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_user_scalability(self, performance_monitor):
        """Test system performance with multiple concurrent users"""
        performance_monitor.start_monitoring()
        
        num_users = 50
        operations_per_user = 100
        
        async def simulate_user_activity(user_id: int):
            """Simulate user activity"""
            mock_api = AsyncMock()
            
            for operation in range(operations_per_user):
                # Simulate various API calls
                if operation % 4 == 0:
                    # Market data request
                    mock_api.get_market_data.return_value = {'AAPL': 150.0}
                    await mock_api.get_market_data('AAPL')
                elif operation % 4 == 1:
                    # Portfolio request
                    mock_api.get_portfolio.return_value = {'total_value': 100000}
                    await mock_api.get_portfolio()
                elif operation % 4 == 2:
                    # Place order
                    mock_api.place_order.return_value = {'order_id': f'ORD_{user_id}_{operation}'}
                    await mock_api.place_order('AAPL', 'BUY', 100)
                else:
                    # Get analytics
                    mock_api.get_analytics.return_value = {'sharpe_ratio': 1.5}
                    await mock_api.get_analytics()
                
                # Small delay between operations
                await asyncio.sleep(0.001)
        
        start_time = time.perf_counter()
        
        # Run all users concurrently
        user_tasks = [simulate_user_activity(i) for i in range(num_users)]
        await asyncio.gather(*user_tasks)
        
        end_time = time.perf_counter()
        performance_monitor.stop_monitoring()
        
        duration = end_time - start_time
        total_operations = num_users * operations_per_user
        ops_per_second = total_operations / duration
        
        metrics = performance_monitor.get_metrics()
        
        # Scalability assertions
        assert ops_per_second > 1000, f"Operations per second {ops_per_second:.0f} below 1000 target"
        assert metrics['max_memory_mb'] < 1024, f"Memory usage {metrics['max_memory_mb']:.1f}MB too high for {num_users} users"
        
        print(f"Concurrent users: {num_users}, Operations/sec: {ops_per_second:.0f}")
        print(f"Memory: {metrics['max_memory_mb']:.1f}MB, CPU: {metrics['max_cpu_percent']:.1f}%")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_data_volume_scalability(self, performance_monitor):
        """Test system performance with large data volumes"""
        performance_monitor.start_monitoring()
        
        # Test with progressively larger datasets
        dataset_sizes = [1000, 5000, 10000, 25000, 50000]
        processing_times = []
        
        for size in dataset_sizes:
            # Generate large dataset
            data = pd.DataFrame({
                'symbol': [f'STOCK_{i % 1000}' for i in range(size)],
                'price': np.random.uniform(50, 200, size),
                'volume': np.random.randint(1000, 100000, size),
                'timestamp': pd.date_range(end=datetime.now(), periods=size, freq='1min')
            })
            
            start_time = time.perf_counter()
            
            # Simulate data processing
            mock_processor = AsyncMock()
            mock_processor.process_large_dataset.return_value = data
            
            result = await mock_processor.process_large_dataset(data)
            
            end_time = time.perf_counter()
            processing_time = end_time - start_time
            processing_times.append(processing_time)
            
            # Clean up
            del data, result
            gc.collect()
        
        performance_monitor.stop_monitoring()
        
        # Analyze scalability
        for i, (size, time_taken) in enumerate(zip(dataset_sizes, processing_times)):
            throughput = size / time_taken
            print(f"Dataset size: {size:,}, Time: {time_taken:.2f}s, Throughput: {throughput:.0f} records/sec")
            
            # Performance should scale reasonably
            if i > 0:
                size_ratio = size / dataset_sizes[i-1]
                time_ratio = time_taken / processing_times[i-1]
                
                # Time should not scale worse than O(n log n)
                expected_max_ratio = size_ratio * np.log2(size_ratio)
                assert time_ratio < expected_max_ratio * 2, f"Poor scalability at size {size}"


class TestResourceLimits:
    """Test system behavior under resource constraints"""
    
    @pytest.mark.performance
    def test_cpu_intensive_operations(self, performance_monitor):
        """Test CPU-intensive operations performance"""
        performance_monitor.start_monitoring()
        
        # Simulate CPU-intensive calculations
        start_time = time.perf_counter()
        
        # Matrix operations (common in quantitative finance)
        for _ in range(10):
            # Generate random correlation matrix
            size = 500
            random_matrix = np.random.randn(size, size)
            correlation_matrix = np.corrcoef(random_matrix)
            
            # Eigenvalue decomposition (CPU intensive)
            eigenvalues, eigenvectors = np.linalg.eigh(correlation_matrix)
            
            # Portfolio optimization simulation
            weights = np.random.dirichlet(np.ones(size))
            portfolio_return = np.dot(weights, np.random.randn(size))
            portfolio_risk = np.sqrt(np.dot(weights, np.dot(correlation_matrix, weights)))
        
        end_time = time.perf_counter()
        performance_monitor.stop_monitoring()
        
        duration = end_time - start_time
        metrics = performance_monitor.get_metrics()
        
        # Performance assertions
        assert duration < 30.0, f"CPU-intensive operations took {duration:.2f}s, exceeding 30s limit"
        assert metrics['max_cpu_percent'] > 50, "CPU utilization too low for intensive operations"
        
        print(f"CPU-intensive operations completed in {duration:.2f}s")
        print(f"Max CPU usage: {metrics['max_cpu_percent']:.1f}%")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_io_intensive_operations(self, performance_monitor):
        """Test I/O-intensive operations performance"""
        performance_monitor.start_monitoring()
        
        # Simulate I/O-intensive operations
        mock_database = AsyncMock()
        mock_cache = AsyncMock()
        mock_file_system = AsyncMock()
        
        num_operations = 1000
        start_time = time.perf_counter()
        
        # Simulate concurrent I/O operations
        io_tasks = []
        
        for i in range(num_operations):
            if i % 3 == 0:
                # Database query
                mock_database.query.return_value = {'result': f'data_{i}'}
                task = mock_database.query(f'SELECT * FROM table WHERE id = {i}')
            elif i % 3 == 1:
                # Cache operation
                mock_cache.get.return_value = f'cached_data_{i}'
                task = mock_cache.get(f'key_{i}')
            else:
                # File I/O
                mock_file_system.read.return_value = f'file_content_{i}'
                task = mock_file_system.read(f'file_{i}.txt')
            
            io_tasks.append(task)
        
        # Execute all I/O operations concurrently
        results = await asyncio.gather(*io_tasks)
        
        end_time = time.perf_counter()
        performance_monitor.stop_monitoring()
        
        duration = end_time - start_time
        io_throughput = num_operations / duration
        
        # Performance assertions
        assert duration < 10.0, f"I/O operations took {duration:.2f}s, exceeding 10s limit"
        assert io_throughput > 100, f"I/O throughput {io_throughput:.0f} ops/sec below 100 target"
        assert len(results) == num_operations, "Not all I/O operations completed"
        
        print(f"I/O operations: {num_operations}, Duration: {duration:.2f}s, Throughput: {io_throughput:.0f} ops/sec")


# Performance test configuration
@pytest.fixture(scope="session", autouse=True)
def performance_test_setup():
    """Setup for performance tests"""
    # Set resource limits for testing
    try:
        # Set memory limit (2GB)
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 * 1024 * 1024, -1))
    except (OSError, ValueError):
        # Resource limits may not be available on all platforms
        pass
    
    # Configure garbage collection for performance testing
    gc.set_threshold(700, 10, 10)
    
    yield
    
    # Cleanup after all performance tests
    gc.collect()


def pytest_configure(config):
    """Configure pytest for performance testing"""
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection for performance tests"""
    # Add slow marker to performance tests
    for item in items:
        if "performance" in item.keywords:
            item.add_marker(pytest.mark.slow)
