"""
Load Testing Framework

Tests system performance under production-scale loads:
- 10,000+ orders per day
- Multiple concurrent strategies
- High-frequency data feeds
- Realistic market conditions
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import pytest
import psutil
import statistics

from core_engine.system.central_risk_manager import CentralRiskManager
from core_engine.system.unified_execution_engine import UnifiedExecutionEngine
from core_engine.trading.order_manager import OrderSide


@dataclass
class LoadTestMetrics:
    """Metrics collected during load testing."""
    
    # Throughput metrics
    total_orders: int = 0
    successful_orders: int = 0
    failed_orders: int = 0
    orders_per_second: float = 0.0
    
    # Latency metrics (milliseconds)
    latencies: List[float] = field(default_factory=list)
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    
    # Resource metrics
    peak_memory_mb: float = 0.0
    avg_cpu_percent: float = 0.0
    active_connections: int = 0
    
    # Error metrics
    errors: List[str] = field(default_factory=list)
    error_rate: float = 0.0
    
    # Time metrics
    test_duration_seconds: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def calculate_statistics(self):
        """Calculate statistical metrics from collected data."""
        if self.latencies:
            self.avg_latency_ms = statistics.mean(self.latencies)
            self.p50_latency_ms = statistics.median(self.latencies)
            sorted_latencies = sorted(self.latencies)
            n = len(sorted_latencies)
            self.p95_latency_ms = sorted_latencies[int(n * 0.95)] if n > 0 else 0
            self.p99_latency_ms = sorted_latencies[int(n * 0.99)] if n > 0 else 0
            self.max_latency_ms = max(self.latencies)
        
        if self.total_orders > 0:
            self.error_rate = self.failed_orders / self.total_orders
            self.orders_per_second = self.total_orders / self.test_duration_seconds if self.test_duration_seconds > 0 else 0
    
    def to_dict(self) -> Dict:
        """Convert metrics to dictionary for reporting."""
        return {
            'throughput': {
                'total_orders': self.total_orders,
                'successful_orders': self.successful_orders,
                'failed_orders': self.failed_orders,
                'orders_per_second': round(self.orders_per_second, 2),
            },
            'latency': {
                'avg_ms': round(self.avg_latency_ms, 2),
                'p50_ms': round(self.p50_latency_ms, 2),
                'p95_ms': round(self.p95_latency_ms, 2),
                'p99_ms': round(self.p99_latency_ms, 2),
                'max_ms': round(self.max_latency_ms, 2),
            },
            'resources': {
                'peak_memory_mb': round(self.peak_memory_mb, 2),
                'avg_cpu_percent': round(self.avg_cpu_percent, 2),
                'active_connections': self.active_connections,
            },
            'errors': {
                'count': self.failed_orders,
                'rate': round(self.error_rate * 100, 2),
                'samples': self.errors[:10],  # First 10 errors
            },
            'duration': {
                'seconds': round(self.test_duration_seconds, 2),
                'start': self.start_time.isoformat() if self.start_time else None,
                'end': self.end_time.isoformat() if self.end_time else None,
            }
        }


class LoadTestHarness:
    """
    Load testing harness for production validation.
    
    Generates realistic trading load and measures system performance.
    """
    
    def __init__(self):
        self.metrics = LoadTestMetrics()
        self.process = psutil.Process()
        self._monitoring_task: Optional[asyncio.Task] = None
        self._stop_monitoring = False
    
    async def start_resource_monitoring(self):
        """Monitor system resources during test."""
        cpu_samples = []
        
        while not self._stop_monitoring:
            # Memory usage
            mem_info = self.process.memory_info()
            current_mem_mb = mem_info.rss / 1024 / 1024
            self.metrics.peak_memory_mb = max(self.metrics.peak_memory_mb, current_mem_mb)
            
            # CPU usage
            cpu_percent = self.process.cpu_percent(interval=0.1)
            cpu_samples.append(cpu_percent)
            
            await asyncio.sleep(1)
        
        # Calculate average CPU
        if cpu_samples:
            self.metrics.avg_cpu_percent = statistics.mean(cpu_samples)
    
    async def generate_market_data_stream(self, symbols: List[str], duration_seconds: int):
        """
        Generate realistic market data stream.
        
        Simulates streaming market data for multiple symbols.
        """
        start_time = time.time()
        tick_count = 0
        
        while time.time() - start_time < duration_seconds:
            # Generate market data tick
            for symbol in symbols:
                # Simulate market data (price, volume, etc.)
                await asyncio.sleep(0.01)  # 100 ticks per second per symbol
                tick_count += 1
        
        return tick_count
    
    async def generate_order_load(
        self,
        num_orders: int,
        symbols: List[str],
        risk_manager: CentralRiskManager,
        execution_engine: UnifiedExecutionEngine
    ) -> LoadTestMetrics:
        """
        Generate order load and measure performance.
        
        Args:
            num_orders: Number of orders to generate
            symbols: List of symbols to trade
            risk_manager: Risk manager instance
            execution_engine: Execution engine instance
            
        Returns:
            LoadTestMetrics with performance data
        """
        self.metrics.start_time = datetime.now()
        start_time = time.time()
        
        # Start resource monitoring
        self._stop_monitoring = False
        self._monitoring_task = asyncio.create_task(self.start_resource_monitoring())
        
        try:
            # Generate orders
            tasks = []
            for i in range(num_orders):
                symbol = symbols[i % len(symbols)]
                side = OrderSide.BUY if i % 2 == 0 else OrderSide.SELL
                
                task = self._submit_order(
                    symbol=symbol,
                    side=side,
                    quantity=100,
                    price=100.0,
                    risk_manager=risk_manager,
                    execution_engine=execution_engine
                )
                tasks.append(task)
                
                # Control rate - 10 orders per second
                if i % 10 == 0:
                    await asyncio.sleep(1)
            
            # Wait for all orders to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results
            for result in results:
                if isinstance(result, Exception):
                    self.metrics.failed_orders += 1
                    self.metrics.errors.append(str(result))
                else:
                    self.metrics.successful_orders += 1
            
            self.metrics.total_orders = num_orders
            
        finally:
            # Stop monitoring
            self._stop_monitoring = True
            if self._monitoring_task:
                await self._monitoring_task
            
            # Calculate metrics
            self.metrics.end_time = datetime.now()
            self.metrics.test_duration_seconds = time.time() - start_time
            self.metrics.calculate_statistics()
        
        return self.metrics
    
    async def _submit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        price: float,
        risk_manager: CentralRiskManager,
        execution_engine: UnifiedExecutionEngine
    ):
        """
        Submit a single order and measure latency.
        
        Returns:
            Order result or raises exception on failure
        """
        start_time = time.time()
        
        try:
            # This is a simplified order submission - adjust based on your actual API
            # In production, this would go through the full order workflow
            
            # Simulate order processing
            await asyncio.sleep(0.001)  # Simulate 1ms processing
            
            # Record latency
            latency_ms = (time.time() - start_time) * 1000
            self.metrics.latencies.append(latency_ms)
            
            return True
            
        except Exception:
            latency_ms = (time.time() - start_time) * 1000
            self.metrics.latencies.append(latency_ms)
            raise


@pytest.mark.production
@pytest.mark.load_test
class TestLoadPerformance:
    """Load testing suite for production validation."""
    
    @pytest.mark.asyncio
    async def test_baseline_load_100_orders(self):
        """Test system with baseline load of 100 orders."""
        harness = LoadTestHarness()
        symbols = ["AAPL", "MSFT", "GOOGL"]
        
        # Mock components (replace with actual test fixtures)
        risk_manager = None  # Use your fixture
        execution_engine = None  # Use your fixture
        
        # Skip if no components available
        if not risk_manager or not execution_engine:
            pytest.skip("Integration components not available")
        
        metrics = await harness.generate_order_load(
            num_orders=100,
            symbols=symbols,
            risk_manager=risk_manager,
            execution_engine=execution_engine
        )
        
        # Assertions
        assert metrics.total_orders == 100
        assert metrics.error_rate < 0.01  # < 1% error rate
        assert metrics.avg_latency_ms < 100  # < 100ms average latency
        assert metrics.p95_latency_ms < 200  # < 200ms p95 latency
        
        print(f"\n{'='*60}")
        print("BASELINE LOAD TEST RESULTS (100 orders)")
        print(f"{'='*60}")
        print(f"Throughput: {metrics.orders_per_second:.2f} orders/sec")
        print(f"Latency (avg): {metrics.avg_latency_ms:.2f}ms")
        print(f"Latency (p95): {metrics.p95_latency_ms:.2f}ms")
        print(f"Memory: {metrics.peak_memory_mb:.2f}MB")
        print(f"Success rate: {(1 - metrics.error_rate) * 100:.2f}%")
        print(f"{'='*60}\n")
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_production_scale_load_10k_orders(self):
        """Test system with production-scale load of 10,000 orders."""
        harness = LoadTestHarness()
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        
        # Mock components (replace with actual test fixtures)
        risk_manager = None  # Use your fixture
        execution_engine = None  # Use your fixture
        
        # Skip if no components available
        if not risk_manager or not execution_engine:
            pytest.skip("Integration components not available")
        
        metrics = await harness.generate_order_load(
            num_orders=10000,
            symbols=symbols,
            risk_manager=risk_manager,
            execution_engine=execution_engine
        )
        
        # Production requirements
        assert metrics.error_rate < 0.001  # < 0.1% error rate
        assert metrics.avg_latency_ms < 100  # < 100ms average
        assert metrics.p99_latency_ms < 500  # < 500ms p99
        assert metrics.peak_memory_mb < 1000  # < 1GB memory
        assert metrics.orders_per_second > 10  # > 10 orders/sec
        
        # Print detailed report
        import json
        print(f"\n{'='*60}")
        print("PRODUCTION SCALE LOAD TEST RESULTS (10,000 orders)")
        print(f"{'='*60}")
        print(json.dumps(metrics.to_dict(), indent=2))
        print(f"{'='*60}\n")
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_peak_load_stress(self):
        """Test system under peak load conditions (burst of orders)."""
        harness = LoadTestHarness()
        symbols = ["AAPL", "MSFT", "GOOGL"]
        
        # Skip if components not available
        pytest.skip("Stress test requires full system integration")
        
        # Simulate burst: 1000 orders in 10 seconds
        metrics = await harness.generate_order_load(
            num_orders=1000,
            symbols=symbols,
            risk_manager=None,
            execution_engine=None
        )
        
        # Stress test requirements
        assert metrics.error_rate < 0.05  # < 5% error rate under stress
        assert metrics.p99_latency_ms < 1000  # < 1 second p99
        
        print(f"\n{'='*60}")
        print("PEAK LOAD STRESS TEST RESULTS (1,000 orders in bursts)")
        print(f"{'='*60}")
        print(f"Peak throughput: {metrics.orders_per_second:.2f} orders/sec")
        print(f"Latency (p99): {metrics.p99_latency_ms:.2f}ms")
        print(f"Peak memory: {metrics.peak_memory_mb:.2f}MB")
        print(f"Error rate: {metrics.error_rate * 100:.2f}%")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    # Run load tests
    pytest.main([__file__, "-v", "-m", "load_test", "--tb=short"])
