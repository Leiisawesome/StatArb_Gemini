"""
Performance Comparison Benchmark
=================================

Compare baseline vs optimized trading system performance.

Compares:
1. Component-level latency
2. End-to-end throughput
3. Memory usage
4. Batch processing efficiency
"""

import asyncio
import time
import sys
from pathlib import Path
from typing import Dict, Any, List
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.performance.profiler import benchmark_function
from tests.performance.memory_profiler import MemoryProfiler
from tests.load_testing.mock_trading_system import (
    MockTradingSystem as BaselineTradingSystem
)
from tests.performance.optimized_trading_system import (
    OptimizedTradingSystem
)


class PerformanceComparison:
    """Compare baseline vs optimized performance"""
    
    def __init__(self):
        self.results = {
            'baseline': {},
            'optimized': {},
            'improvements': {}
        }
    
    async def benchmark_single_order_latency(self, system, system_name: str, iterations: int = 100):
        """Benchmark single order processing latency"""
        print(f"\n📊 Benchmarking {system_name}: Single Order Latency...")
        
        latencies = []
        
        for i in range(iterations):
            order = {
                'order_id': f'BENCH{i:04d}',
                'symbol': 'AAPL',
                'side': 'BUY',
                'quantity': 100,
                'price': 150.0,
                'order_type': 'LIMIT'
            }
            
            start = time.perf_counter()
            result = await system.submit_order(order)
            end = time.perf_counter()
            
            latencies.append((end - start) * 1000)  # Convert to ms
        
        latencies_sorted = sorted(latencies)
        n = len(latencies_sorted)
        
        return {
            'avg_ms': sum(latencies) / n,
            'min_ms': min(latencies),
            'max_ms': max(latencies),
            'p50_ms': latencies_sorted[int(n * 0.50)],
            'p95_ms': latencies_sorted[int(n * 0.95)],
            'p99_ms': latencies_sorted[int(n * 0.99)],
        }
    
    async def benchmark_batch_throughput(self, system, system_name: str, batch_size: int = 50):
        """Benchmark batch processing throughput"""
        print(f"📊 Benchmarking {system_name}: Batch Throughput...")
        
        orders = [
            {
                'order_id': f'BATCH{i:04d}',
                'symbol': 'AAPL',
                'side': 'BUY',
                'quantity': 100,
                'price': 150.0,
                'order_type': 'LIMIT'
            }
            for i in range(batch_size)
        ]
        
        start = time.perf_counter()
        
        if hasattr(system, 'submit_orders_batch'):
            # Optimized system with batch support
            results = await system.submit_orders_batch(orders)
        else:
            # Baseline system - sequential processing
            results = []
            for order in orders:
                result = await system.submit_order(order)
                results.append(result)
        
        end = time.perf_counter()
        duration = end - start
        
        filled = sum(1 for r in results if r.status == 'FILLED')
        
        return {
            'orders': len(results),
            'filled': filled,
            'fill_rate': filled / len(results) if results else 0,
            'duration_ms': duration * 1000,
            'throughput_ops_sec': len(results) / duration if duration > 0 else 0,
            'avg_latency_per_order_ms': duration * 1000 / len(results) if results else 0
        }
    
    async def run_comparison(self):
        """Run comprehensive comparison"""
        print("\n" + "="*80)
        print("PERFORMANCE COMPARISON: BASELINE vs OPTIMIZED")
        print("="*80)
        print(f"\nTimestamp: {datetime.now().isoformat()}")
        
        # Initialize systems
        print("\n🚀 Initializing systems...")
        baseline_system = BaselineTradingSystem()
        optimized_system = OptimizedTradingSystem()
        
        # Benchmark 1: Single order latency
        print("\n" + "-"*80)
        print("TEST 1: Single Order Latency (100 iterations)")
        print("-"*80)
        
        baseline_latency = await self.benchmark_single_order_latency(
            baseline_system, "BASELINE", iterations=100
        )
        self.results['baseline']['single_order'] = baseline_latency
        
        optimized_latency = await self.benchmark_single_order_latency(
            optimized_system, "OPTIMIZED", iterations=100
        )
        self.results['optimized']['single_order'] = optimized_latency
        
        # Calculate improvement
        latency_improvement = (
            (baseline_latency['avg_ms'] - optimized_latency['avg_ms']) / 
            baseline_latency['avg_ms'] * 100
        )
        self.results['improvements']['latency_reduction_pct'] = latency_improvement
        
        print(f"\n📈 Results:")
        print(f"   Baseline:  {baseline_latency['avg_ms']:.2f}ms avg, {baseline_latency['p99_ms']:.2f}ms P99")
        print(f"   Optimized: {optimized_latency['avg_ms']:.2f}ms avg, {optimized_latency['p99_ms']:.2f}ms P99")
        print(f"   Improvement: {latency_improvement:+.1f}%")
        
        # Benchmark 2: Batch throughput
        print("\n" + "-"*80)
        print("TEST 2: Batch Throughput (50 orders)")
        print("-"*80)
        
        baseline_batch = await self.benchmark_batch_throughput(
            baseline_system, "BASELINE", batch_size=50
        )
        self.results['baseline']['batch'] = baseline_batch
        
        optimized_batch = await self.benchmark_batch_throughput(
            optimized_system, "OPTIMIZED", batch_size=50
        )
        self.results['optimized']['batch'] = optimized_batch
        
        # Calculate improvement
        throughput_improvement = (
            (optimized_batch['throughput_ops_sec'] - baseline_batch['throughput_ops_sec']) / 
            baseline_batch['throughput_ops_sec'] * 100
        )
        self.results['improvements']['throughput_increase_pct'] = throughput_improvement
        
        print(f"\n📈 Results:")
        print(f"   Baseline:  {baseline_batch['throughput_ops_sec']:.1f} orders/sec, {baseline_batch['duration_ms']:.1f}ms total")
        print(f"   Optimized: {optimized_batch['throughput_ops_sec']:.1f} orders/sec, {optimized_batch['duration_ms']:.1f}ms total")
        print(f"   Improvement: {throughput_improvement:+.1f}%")
        
        # Benchmark 3: Large batch (stress test)
        print("\n" + "-"*80)
        print("TEST 3: Large Batch Stress Test (200 orders)")
        print("-"*80)
        
        baseline_stress = await self.benchmark_batch_throughput(
            baseline_system, "BASELINE", batch_size=200
        )
        self.results['baseline']['stress'] = baseline_stress
        
        optimized_stress = await self.benchmark_batch_throughput(
            optimized_system, "OPTIMIZED", batch_size=200
        )
        self.results['optimized']['stress'] = optimized_stress
        
        stress_improvement = (
            (optimized_stress['throughput_ops_sec'] - baseline_stress['throughput_ops_sec']) / 
            baseline_stress['throughput_ops_sec'] * 100
        )
        
        print(f"\n📈 Results:")
        print(f"   Baseline:  {baseline_stress['throughput_ops_sec']:.1f} orders/sec, {baseline_stress['duration_ms']:.1f}ms total")
        print(f"   Optimized: {optimized_stress['throughput_ops_sec']:.1f} orders/sec, {optimized_stress['duration_ms']:.1f}ms total")
        print(f"   Improvement: {stress_improvement:+.1f}%")
        
        # Summary
        self.print_summary()
        
        # Save results
        self.save_results()
    
    def print_summary(self):
        """Print comparison summary"""
        print("\n" + "="*80)
        print("SUMMARY: PERFORMANCE IMPROVEMENTS")
        print("="*80)
        
        baseline = self.results['baseline']
        optimized = self.results['optimized']
        improvements = self.results['improvements']
        
        print("\n📊 KEY METRICS:")
        print("-"*80)
        
        # Latency
        print(f"\n⏱️  LATENCY:")
        print(f"   Baseline:   {baseline['single_order']['avg_ms']:.2f}ms avg, {baseline['single_order']['p99_ms']:.2f}ms P99")
        print(f"   Optimized:  {optimized['single_order']['avg_ms']:.2f}ms avg, {optimized['single_order']['p99_ms']:.2f}ms P99")
        print(f"   Improvement: {improvements['latency_reduction_pct']:+.1f}%")
        
        # Throughput
        print(f"\n⚡ THROUGHPUT (50 orders):")
        print(f"   Baseline:   {baseline['batch']['throughput_ops_sec']:.1f} orders/sec")
        print(f"   Optimized:  {optimized['batch']['throughput_ops_sec']:.1f} orders/sec")
        print(f"   Improvement: {improvements['throughput_increase_pct']:+.1f}%")
        
        # Stress test
        print(f"\n🔥 STRESS TEST (200 orders):")
        print(f"   Baseline:   {baseline['stress']['throughput_ops_sec']:.1f} orders/sec")
        print(f"   Optimized:  {optimized['stress']['throughput_ops_sec']:.1f} orders/sec")
        stress_improvement = (
            (optimized['stress']['throughput_ops_sec'] - baseline['stress']['throughput_ops_sec']) / 
            baseline['stress']['throughput_ops_sec'] * 100
        )
        print(f"   Improvement: {stress_improvement:+.1f}%")
        
        # Overall assessment
        print("\n🎯 TARGETS vs ACHIEVED:")
        print("-"*80)
        
        target_latency_reduction = 50  # 50% target
        target_throughput_increase = 100  # 2x = 100% increase
        
        latency_status = "✅ MET" if improvements['latency_reduction_pct'] >= target_latency_reduction else "🔶 PARTIAL"
        throughput_status = "✅ MET" if improvements['throughput_increase_pct'] >= target_throughput_increase else "🔶 PARTIAL"
        
        print(f"   Latency Reduction:    Target: {target_latency_reduction}%, Achieved: {improvements['latency_reduction_pct']:+.1f}% {latency_status}")
        print(f"   Throughput Increase:  Target: {target_throughput_increase}%, Achieved: {improvements['throughput_increase_pct']:+.1f}% {throughput_status}")
        
        print("\n" + "="*80 + "\n")
    
    def save_results(self):
        """Save comparison results"""
        output_dir = Path(__file__).parent.parent.parent / "benchmark_results"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = output_dir / f"optimization_comparison_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'results': self.results
            }, f, indent=2)
        
        print(f"✅ Results saved to {filename}")


async def main():
    """Run performance comparison"""
    comparison = PerformanceComparison()
    await comparison.run_comparison()
    
    print("\n💡 OPTIMIZATION SUMMARY:")
    print("-"*80)
    print("✅ Converted CPU-bound operations from async to sync")
    print("✅ Implemented caching for market data and risk limits")
    print("✅ Added batch processing with asyncio.gather()")
    print("✅ Implemented object pooling for Position objects")
    print("✅ Reduced async overhead in hot paths")
    
    print("\n🎯 NEXT STEPS:")
    improvements = comparison.results['improvements']
    
    if improvements['latency_reduction_pct'] >= 50 and improvements['throughput_increase_pct'] >= 100:
        print("   ✅ All targets met! Ready for production.")
    else:
        print("   🔶 Partial improvements achieved. Consider:")
        if improvements['latency_reduction_pct'] < 50:
            print("      • Further optimize integration layer")
            print("      • Profile remaining hot paths")
        if improvements['throughput_increase_pct'] < 100:
            print("      • Increase batch size")
            print("      • Add more parallelization")
    
    print("\n" + "="*80)


if __name__ == '__main__':
    asyncio.run(main())
