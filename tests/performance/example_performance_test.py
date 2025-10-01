"""
Example Performance Test for StatArb_Gemini Core Engine

This example demonstrates how to use the performance testing framework
to measure latency, memory usage, and throughput of core engine components.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.performance import (
    LatencyProfiler, MemoryProfiler, ThroughputBenchmarker,
    LatencyContext, MemoryMonitoringContext, LoadTestConfiguration
)

logger = logging.getLogger(__name__)

async def example_latency_test():
    """Example of latency profiling"""
    logger.info("🔍 Example Latency Test")
    
    profiler = LatencyProfiler(max_samples=1000)
    
    # Method 1: Using context manager
    for i in range(100):
        with LatencyContext(profiler, "ExampleComponent", "context_operation"):
            await asyncio.sleep(0.001)  # Simulate 1ms operation
    
    # Method 2: Using direct measurement
    async def test_operation():
        await asyncio.sleep(0.002)  # Simulate 2ms operation
        return "result"
    
    for i in range(100):
        result, measurement = await profiler.measure_async_operation(
            "ExampleComponent", "direct_operation", test_operation
        )
    
    # Get statistics
    stats1 = profiler.get_statistics("ExampleComponent", "context_operation")
    stats2 = profiler.get_statistics("ExampleComponent", "direct_operation")
    
    if stats1:
        logger.info(f"Context operation - Mean: {stats1.mean_us:.2f}μs, P99: {stats1.p99_us:.2f}μs")
    
    if stats2:
        logger.info(f"Direct operation - Mean: {stats2.mean_us:.2f}μs, P99: {stats2.p99_us:.2f}μs")
    
    # Generate report
    report = profiler.generate_performance_report()
    logger.info(f"Total measurements: {report['total_measurements']}")

async def example_memory_test():
    """Example of memory profiling"""
    logger.info("🧠 Example Memory Test")
    
    profiler = MemoryProfiler(snapshot_interval=0.1, max_snapshots=1000)
    
    # Method 1: Using context manager
    data_storage = []
    
    with MemoryMonitoringContext(profiler, "ExampleComponent", "memory_growth"):
        for i in range(200):
            # Simulate memory allocation
            data_storage.append([i] * 1000)
            
            if i % 50 == 0:
                profiler.take_snapshot("ExampleComponent", "allocation", {"iteration": i})
    
    # Analyze memory usage
    analysis = profiler.analyze_memory_usage("ExampleComponent", "memory_growth")
    if analysis:
        logger.info(f"Peak memory: {analysis.peak_memory_mb:.2f} MB")
        logger.info(f"Memory growth: {analysis.memory_growth_mb:.2f} MB")
        logger.info(f"Efficiency score: {analysis.memory_efficiency_score:.1f}%")
        logger.info(f"Detected leaks: {len(analysis.detected_leaks)}")
        
        if analysis.optimization_recommendations:
            logger.info("Recommendations:")
            for rec in analysis.optimization_recommendations:
                logger.info(f"  - {rec}")
    
    # Generate report
    report = profiler.generate_memory_report()
    logger.info(f"Components analyzed: {report['summary']['total_components_analyzed']}")

async def example_throughput_test():
    """Example of throughput benchmarking"""
    logger.info("🚀 Example Throughput Test")
    
    benchmarker = ThroughputBenchmarker(max_measurements=1000)
    
    # Define test operation
    async def test_operation(data=None):
        await asyncio.sleep(0.001)  # Simulate 1ms operation
        return f"processed_{data}"
    
    def generate_test_data():
        import random
        return f"data_{random.randint(1, 1000)}"
    
    # Configure load test
    config = LoadTestConfiguration(
        component_name="ExampleComponent",
        operation_name="throughput_test",
        target_operations=500,
        concurrent_workers=[1, 2, 4, 8],  # Test different concurrency levels
        duration_seconds=10,
        ramp_up_seconds=2,
        test_data_generator=generate_test_data,
        operation_function=test_operation,
        enable_warmup=True,
        warmup_operations=50
    )
    
    # Run benchmark
    measurements = await benchmarker.benchmark_async_operation(config)
    
    # Analyze results
    stats = benchmarker.calculate_statistics("ExampleComponent", "throughput_test")
    if stats:
        logger.info(f"Peak throughput: {stats.peak_throughput_ops_per_sec:.1f} ops/sec")
        logger.info(f"Optimal workers: {stats.optimal_worker_count}")
        logger.info(f"Scalability factor: {stats.linear_scalability_factor:.2f}")
        logger.info(f"Reliability score: {stats.reliability_score:.1f}%")
    
    # Generate report
    report = benchmarker.generate_throughput_report()
    logger.info(f"System info: {report['system_info']['cpu_count']} CPUs")

async def example_integrated_test():
    """Example of integrated performance testing"""
    logger.info("🎯 Example Integrated Performance Test")
    
    # Initialize all profilers
    latency_profiler = LatencyProfiler()
    memory_profiler = MemoryProfiler()
    throughput_benchmarker = ThroughputBenchmarker()
    
    # Simulate a complex operation that we want to analyze comprehensively
    async def complex_operation(data_size: int = 1000):
        """Simulate a complex operation with memory allocation and processing"""
        
        # Allocate some memory
        data = list(range(data_size))
        
        # Simulate processing time
        await asyncio.sleep(0.002)
        
        # Simulate some computation
        result = sum(x * x for x in data[:100])
        
        return result
    
    # Test with different data sizes
    data_sizes = [500, 1000, 2000, 5000]
    
    for data_size in data_sizes:
        logger.info(f"Testing with data size: {data_size}")
        
        # Start memory monitoring
        memory_id = memory_profiler.start_monitoring("IntegratedTest", f"data_size_{data_size}")
        
        # Run operations with latency measurement
        for i in range(50):
            result, latency_measurement = await latency_profiler.measure_async_operation(
                "IntegratedTest", f"complex_op_{data_size}", complex_operation, data_size
            )
            
            # Take memory snapshot periodically
            if i % 10 == 0:
                memory_profiler.take_snapshot("IntegratedTest", f"operation_{data_size}", {
                    "iteration": i,
                    "data_size": data_size,
                    "result": result
                })
        
        # Stop memory monitoring
        memory_profiler.stop_monitoring(memory_id)
    
    # Analyze results for each data size
    for data_size in data_sizes:
        logger.info(f"\nResults for data size {data_size}:")
        
        # Latency analysis
        latency_stats = latency_profiler.get_statistics("IntegratedTest", f"complex_op_{data_size}")
        if latency_stats:
            logger.info(f"  Latency - Mean: {latency_stats.mean_us:.2f}μs, P95: {latency_stats.p95_us:.2f}μs")
        
        # Memory analysis
        memory_analysis = memory_profiler.analyze_memory_usage("IntegratedTest", f"data_size_{data_size}")
        if memory_analysis:
            logger.info(f"  Memory - Peak: {memory_analysis.peak_memory_mb:.2f}MB, "
                       f"Efficiency: {memory_analysis.memory_efficiency_score:.1f}%")
    
    logger.info("\n📊 Generating comprehensive reports...")
    
    # Generate all reports
    latency_report = latency_profiler.generate_performance_report()
    memory_report = memory_profiler.generate_memory_report()
    
    logger.info(f"Latency measurements: {latency_report['total_measurements']}")
    logger.info(f"Memory components analyzed: {memory_report['summary']['total_components_analyzed']}")

async def main():
    """Run all example tests"""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logger.info("🎯 Starting Performance Testing Examples")
    logger.info("=" * 50)
    
    try:
        # Run individual examples
        await example_latency_test()
        logger.info("")
        
        await example_memory_test()
        logger.info("")
        
        await example_throughput_test()
        logger.info("")
        
        await example_integrated_test()
        
        logger.info("\n✅ All performance testing examples completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Example tests failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())
