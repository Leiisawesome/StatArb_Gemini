"""
Comprehensive Load Testing Suite for StatArb_Gemini - Week 3
Tests system behavior under high load (1000s requests/second)
"""

import pytest
import asyncio
import time
import statistics
from typing import Dict, List, Any
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core_engine.system.central_risk_manager import CentralRiskManager
from core_engine.system.hierarchical_orchestrator import HierarchicalSystemOrchestrator
from core_engine.trading.strategies.manager import StrategyManager


class LoadTestMetrics:
    """Collects and analyzes load test metrics"""
    
    def __init__(self):
        self.requests_sent = 0
        self.requests_completed = 0
        self.requests_failed = 0
        self.latencies = []
        self.start_time = None
        self.end_time = None
    
    def record_request(self, latency: float, success: bool):
        """Record a single request result"""
        self.requests_completed += 1
        if success:
            self.latencies.append(latency)
        else:
            self.requests_failed += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Calculate and return load test metrics"""
        duration = (self.end_time - self.start_time) if self.end_time and self.start_time else 0
        
        if not self.latencies:
            return {
                "duration_seconds": duration,
                "total_requests": self.requests_sent,
                "completed_requests": self.requests_completed,
                "failed_requests": self.requests_failed,
                "success_rate": 0.0,
                "throughput_rps": 0.0
            }
        
        return {
            "duration_seconds": duration,
            "total_requests": self.requests_sent,
            "completed_requests": self.requests_completed,
            "failed_requests": self.requests_failed,
            "success_rate": (self.requests_completed - self.requests_failed) / self.requests_completed * 100,
            "throughput_rps": self.requests_completed / duration if duration > 0 else 0,
            "latency_p50_ms": statistics.median(self.latencies) * 1000,
            "latency_p95_ms": statistics.quantiles(self.latencies, n=20)[18] * 1000 if len(self.latencies) > 20 else max(self.latencies) * 1000,
            "latency_p99_ms": statistics.quantiles(self.latencies, n=100)[98] * 1000 if len(self.latencies) > 100 else max(self.latencies) * 1000,
            "latency_avg_ms": statistics.mean(self.latencies) * 1000,
            "latency_min_ms": min(self.latencies) * 1000,
            "latency_max_ms": max(self.latencies) * 1000
        }


@pytest.mark.asyncio
class TestHighLoadPerformance:
    """Test system performance under high load conditions"""
    
    async def test_risk_manager_high_load(self):
        """Test CentralRiskManager under 1000+ requests/second load"""
        risk_manager = CentralRiskManager()
        await risk_manager.initialize()
        
        metrics = LoadTestMetrics()
        
        async def make_risk_check():
            """Single risk check operation"""
            start = time.perf_counter()
            try:
                result = await risk_manager.check_position_risk(
                    symbol="AAPL",
                    quantity=100,
                    side="buy",
                    price=150.0
                )
                latency = time.perf_counter() - start
                metrics.record_request(latency, result.get("approved", False))
            except Exception:
                latency = time.perf_counter() - start
                metrics.record_request(latency, False)
        
        # Run load test: 10,000 requests
        num_requests = 10000
        batch_size = 100  # 100 concurrent requests
        
        metrics.start_time = time.perf_counter()
        metrics.requests_sent = num_requests
        
        for batch_start in range(0, num_requests, batch_size):
            batch_end = min(batch_start + batch_size, num_requests)
            tasks = [make_risk_check() for _ in range(batch_end - batch_start)]
            await asyncio.gather(*tasks)
        
        metrics.end_time = time.perf_counter()
        
        # Get results
        results = metrics.get_metrics()
        
        # Print detailed results
        print("\n" + "="*60)
        print("RISK MANAGER HIGH LOAD TEST RESULTS")
        print("="*60)
        print(f"Total Requests:     {results['total_requests']:,}")
        print(f"Completed:          {results['completed_requests']:,}")
        print(f"Failed:             {results['failed_requests']:,}")
        print(f"Success Rate:       {results['success_rate']:.2f}%")
        print(f"Duration:           {results['duration_seconds']:.2f}s")
        print(f"Throughput:         {results['throughput_rps']:.2f} req/s")
        print(f"Latency P50:        {results['latency_p50_ms']:.2f}ms")
        print(f"Latency P95:        {results['latency_p95_ms']:.2f}ms")
        print(f"Latency P99:        {results['latency_p99_ms']:.2f}ms")
        print(f"Latency Avg:        {results['latency_avg_ms']:.2f}ms")
        print("="*60)
        
        # Assertions
        assert results['success_rate'] >= 95.0, f"Success rate {results['success_rate']:.2f}% below 95%"
        assert results['throughput_rps'] >= 500, f"Throughput {results['throughput_rps']:.2f} req/s below 500 req/s"
        assert results['latency_p99_ms'] < 100, f"P99 latency {results['latency_p99_ms']:.2f}ms exceeds 100ms"
        
        await risk_manager.shutdown()
    
    async def test_orchestrator_high_concurrency(self):
        """Test HierarchicalSystemOrchestrator with high concurrent operations"""
        orchestrator = HierarchicalSystemOrchestrator()
        await orchestrator.initialize()
        
        metrics = LoadTestMetrics()
        
        async def execute_workflow():
            """Execute a workflow operation"""
            start = time.perf_counter()
            try:
                # Simulate workflow execution
                result = await orchestrator.get_component("risk_manager")
                latency = time.perf_counter() - start
                metrics.record_request(latency, result is not None)
            except Exception:
                latency = time.perf_counter() - start
                metrics.record_request(latency, False)
        
        # Run 5,000 concurrent workflow executions
        num_workflows = 5000
        batch_size = 50
        
        metrics.start_time = time.perf_counter()
        metrics.requests_sent = num_workflows
        
        for batch_start in range(0, num_workflows, batch_size):
            batch_end = min(batch_start + batch_size, num_workflows)
            tasks = [execute_workflow() for _ in range(batch_end - batch_start)]
            await asyncio.gather(*tasks)
        
        metrics.end_time = time.perf_counter()
        
        results = metrics.get_metrics()
        
        print("\n" + "="*60)
        print("ORCHESTRATOR HIGH CONCURRENCY TEST RESULTS")
        print("="*60)
        print(f"Total Workflows:    {results['total_requests']:,}")
        print(f"Completed:          {results['completed_requests']:,}")
        print(f"Success Rate:       {results['success_rate']:.2f}%")
        print(f"Throughput:         {results['throughput_rps']:.2f} workflows/s")
        print(f"Latency P95:        {results['latency_p95_ms']:.2f}ms")
        print("="*60)
        
        assert results['success_rate'] >= 90.0
        assert results['throughput_rps'] >= 200
        
        await orchestrator.shutdown()
    
    async def test_sustained_load_30_seconds(self):
        """Test system under sustained load for 30 seconds"""
        risk_manager = CentralRiskManager()
        await risk_manager.initialize()
        
        metrics = LoadTestMetrics()
        test_duration = 30  # seconds
        target_rps = 1000  # target 1000 requests per second
        
        async def continuous_load():
            """Generate continuous load"""
            while True:
                start = time.perf_counter()
                try:
                    await risk_manager.check_position_risk(
                        symbol="AAPL",
                        quantity=100,
                        side="buy",
                        price=150.0
                    )
                    latency = time.perf_counter() - start
                    metrics.record_request(latency, True)
                except Exception:
                    latency = time.perf_counter() - start
                    metrics.record_request(latency, False)
                
                # Sleep to maintain target RPS
                sleep_time = max(0, (1.0 / target_rps) - latency)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
        
        metrics.start_time = time.perf_counter()
        
        # Run for specified duration
        try:
            await asyncio.wait_for(continuous_load(), timeout=test_duration)
        except asyncio.TimeoutError:
            pass  # Expected - test duration reached
        
        metrics.end_time = time.perf_counter()
        metrics.requests_sent = metrics.requests_completed + metrics.requests_failed
        
        results = metrics.get_metrics()
        
        print("\n" + "="*60)
        print("SUSTAINED LOAD TEST RESULTS (30s)")
        print("="*60)
        print(f"Duration:           {results['duration_seconds']:.2f}s")
        print(f"Total Requests:     {results['total_requests']:,}")
        print(f"Avg Throughput:     {results['throughput_rps']:.2f} req/s")
        print(f"Success Rate:       {results['success_rate']:.2f}%")
        print(f"Latency Avg:        {results['latency_avg_ms']:.2f}ms")
        print(f"Latency P99:        {results['latency_p99_ms']:.2f}ms")
        print("="*60)
        
        # System should maintain stable performance for 30 seconds
        assert results['success_rate'] >= 95.0
        assert results['throughput_rps'] >= 500  # Should handle at least 500 req/s
        
        await risk_manager.shutdown()
    
    async def test_burst_traffic_handling(self):
        """Test system handling of burst traffic patterns"""
        risk_manager = CentralRiskManager()
        await risk_manager.initialize()
        
        burst_results = []
        
        # Simulate 5 bursts of traffic
        for burst_num in range(5):
            metrics = LoadTestMetrics()
            
            # Each burst: 2000 requests as fast as possible
            burst_size = 2000
            batch_size = 200
            
            metrics.start_time = time.perf_counter()
            metrics.requests_sent = burst_size
            
            for batch_start in range(0, burst_size, batch_size):
                batch_end = min(batch_start + batch_size, burst_size)
                
                async def make_request():
                    start = time.perf_counter()
                    try:
                        await risk_manager.check_position_risk(
                            symbol="AAPL",
                            quantity=100,
                            side="buy",
                            price=150.0
                        )
                        latency = time.perf_counter() - start
                        metrics.record_request(latency, True)
                    except Exception:
                        latency = time.perf_counter() - start
                        metrics.record_request(latency, False)
                
                tasks = [make_request() for _ in range(batch_end - batch_start)]
                await asyncio.gather(*tasks)
            
            metrics.end_time = time.perf_counter()
            burst_results.append(metrics.get_metrics())
            
            # Small pause between bursts
            await asyncio.sleep(1)
        
        print("\n" + "="*60)
        print("BURST TRAFFIC TEST RESULTS")
        print("="*60)
        
        for i, results in enumerate(burst_results, 1):
            print(f"\nBurst #{i}:")
            print(f"  Throughput:       {results['throughput_rps']:.2f} req/s")
            print(f"  Success Rate:     {results['success_rate']:.2f}%")
            print(f"  Latency P95:      {results['latency_p95_ms']:.2f}ms")
        
        # All bursts should be handled successfully
        for results in burst_results:
            assert results['success_rate'] >= 90.0, "Burst handling degraded"
        
        # Performance should remain stable across bursts
        throughputs = [r['throughput_rps'] for r in burst_results]
        avg_throughput = statistics.mean(throughputs)
        std_dev = statistics.stdev(throughputs) if len(throughputs) > 1 else 0
        
        print(f"\nOverall:")
        print(f"  Avg Throughput:   {avg_throughput:.2f} req/s")
        print(f"  Std Dev:          {std_dev:.2f} req/s")
        print(f"  Stability Score:  {100 - (std_dev/avg_throughput*100):.2f}%")
        print("="*60)
        
        # Standard deviation should be low (< 20% of mean)
        assert std_dev / avg_throughput < 0.20, "Throughput too variable across bursts"
        
        await risk_manager.shutdown()


@pytest.mark.asyncio
class TestScalabilityLimits:
    """Test system scalability and identify bottlenecks"""
    
    async def test_find_max_throughput(self):
        """Progressively increase load to find maximum stable throughput"""
        risk_manager = CentralRiskManager()
        await risk_manager.initialize()
        
        load_levels = [100, 500, 1000, 2000, 5000, 10000]
        results_by_load = []
        
        for num_requests in load_levels:
            metrics = LoadTestMetrics()
            
            metrics.start_time = time.perf_counter()
            metrics.requests_sent = num_requests
            
            async def make_request():
                start = time.perf_counter()
                try:
                    await risk_manager.check_position_risk(
                        symbol="AAPL",
                        quantity=100,
                        side="buy",
                        price=150.0
                    )
                    latency = time.perf_counter() - start
                    metrics.record_request(latency, True)
                except Exception:
                    latency = time.perf_counter() - start
                    metrics.record_request(latency, False)
            
            # Execute all requests with batch processing
            batch_size = min(100, num_requests)
            for batch_start in range(0, num_requests, batch_size):
                batch_end = min(batch_start + batch_size, num_requests)
                tasks = [make_request() for _ in range(batch_end - batch_start)]
                await asyncio.gather(*tasks)
            
            metrics.end_time = time.perf_counter()
            results_by_load.append((num_requests, metrics.get_metrics()))
        
        print("\n" + "="*60)
        print("SCALABILITY TEST RESULTS")
        print("="*60)
        print(f"{'Load Level':<15} {'Throughput':<15} {'P95 Latency':<15} {'Success Rate'}")
        print("-"*60)
        
        for load, results in results_by_load:
            print(f"{load:<15,} {results['throughput_rps']:<15.2f} "
                  f"{results['latency_p95_ms']:<15.2f} {results['success_rate']:.2f}%")
        
        print("="*60)
        
        # Find maximum stable throughput (>95% success rate, <100ms P95 latency)
        max_stable_throughput = 0
        for load, results in results_by_load:
            if results['success_rate'] >= 95.0 and results['latency_p95_ms'] < 100:
                max_stable_throughput = results['throughput_rps']
        
        print(f"\nMax Stable Throughput: {max_stable_throughput:.2f} req/s")
        print("="*60)
        
        # System should handle at least 500 req/s stably
        assert max_stable_throughput >= 500
        
        await risk_manager.shutdown()


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "-s"])
