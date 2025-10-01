# Performance Testing Framework for StatArb_Gemini Core Engine

This comprehensive performance testing framework provides advanced capabilities for measuring, analyzing, and optimizing the performance of the StatArb_Gemini core engine components.

## 🎯 Overview

The framework consists of three main testing modules:

1. **Latency Testing** - Sub-millisecond precision latency measurement and analysis
2. **Memory Profiling** - Memory usage monitoring, leak detection, and optimization
3. **Throughput Benchmarking** - High-frequency operation throughput and scalability testing

## 📊 Features

### Latency Testing (`latency_testing.py`)
- **Nanosecond precision** timing measurements
- **Statistical analysis** with percentiles (P50, P90, P95, P99, P99.9)
- **Jitter analysis** and outlier detection
- **Async/sync operation** support
- **Context managers** and decorators for easy integration
- **Component-specific** test suites

### Memory Profiling (`memory_profiling.py`)
- **Real-time memory** usage tracking
- **Memory leak detection** using statistical analysis
- **Garbage collection** pressure monitoring
- **Large object tracking** (>1MB objects)
- **Memory efficiency scoring** (0-100 scale)
- **Optimization recommendations**

### Throughput Benchmarking (`throughput_benchmarking.py`)
- **Concurrent load testing** with configurable worker counts
- **Scalability analysis** and optimal concurrency detection
- **Resource efficiency** metrics (CPU/memory per operation)
- **Error rate monitoring** and reliability scoring
- **Warmup and cooldown** phases for accurate measurements
- **Performance degradation** detection under load

## 🚀 Quick Start

### Basic Usage

```python
import asyncio
from tests.performance import LatencyProfiler, MemoryProfiler, ThroughputBenchmarker

async def basic_performance_test():
    # Initialize profilers
    latency_profiler = LatencyProfiler()
    memory_profiler = MemoryProfiler()
    throughput_benchmarker = ThroughputBenchmarker()
    
    # Test your operation
    async def my_operation():
        await asyncio.sleep(0.001)  # Your actual operation
        return "result"
    
    # Measure latency
    result, measurement = await latency_profiler.measure_async_operation(
        "MyComponent", "my_operation", my_operation
    )
    
    # Get statistics
    stats = latency_profiler.get_statistics("MyComponent", "my_operation")
    print(f"Mean latency: {stats.mean_us:.2f} μs")
```

### Using Context Managers

```python
from tests.performance import LatencyContext, MemoryMonitoringContext

# Latency measurement
with LatencyContext(latency_profiler, "MyComponent", "operation"):
    # Your code here
    result = perform_operation()

# Memory monitoring
with MemoryMonitoringContext(memory_profiler, "MyComponent", "memory_test"):
    # Your memory-intensive code here
    data = allocate_large_data()
```

### Comprehensive Component Testing

```python
from tests.performance import PerformanceTestSuite

async def test_my_component():
    # Initialize test suite
    test_suite = PerformanceTestSuite()
    
    # Run comprehensive tests
    results = await test_suite.run_comprehensive_performance_tests(integration_manager)
    
    # Results include latency, memory, and throughput analysis
    print(f"Overall performance score: {results['performance_summary']['overall_performance_score']:.1f}/100")
```

## 🛠️ Running Tests

### Command Line Interface

```bash
# Run comprehensive performance tests
python tests/performance/run_performance_tests.py

# Run quick tests (reduced iterations)
python tests/performance/run_performance_tests.py --quick

# Test specific component
python tests/performance/run_performance_tests.py --component data_manager

# Enable verbose logging
python tests/performance/run_performance_tests.py --verbose

# Specify output directory
python tests/performance/run_performance_tests.py --output-dir /path/to/results
```

### Example Tests

```bash
# Run example performance tests
python tests/performance/example_performance_test.py
```

## 📈 Performance Metrics

### Latency Metrics
- **Mean/Median/Min/Max** latency in microseconds
- **Percentiles**: P50, P90, P95, P99, P99.9
- **Jitter**: Standard deviation of consecutive differences
- **Outlier detection** using IQR method
- **Throughput**: Operations per second

### Memory Metrics
- **Peak/Average** memory usage in MB
- **Memory growth** over time
- **Memory volatility** (standard deviation)
- **Leak detection** with confidence scoring
- **GC pressure** and efficiency
- **Memory efficiency score** (0-100)

### Throughput Metrics
- **Peak/Average/Min** throughput in ops/sec
- **Scalability factor** (linear regression vs worker count)
- **Optimal worker count** for maximum throughput
- **Resource efficiency** (ops per CPU%, ops per MB)
- **Error rate** and reliability scoring
- **Performance stability** under load

## 📊 Reports and Analysis

### Generated Reports

The framework generates several types of reports:

1. **JSON Results** (`performance_results_YYYYMMDD_HHMMSS.json`)
   - Complete raw data and statistics
   - Machine-readable format for further analysis

2. **Markdown Report** (`performance_report_YYYYMMDD_HHMMSS.md`)
   - Human-readable performance summary
   - Key findings and recommendations
   - Component-by-component analysis

3. **Performance Logs** (`performance_tests.log`)
   - Detailed execution logs
   - Error messages and debugging information

### Sample Report Structure

```
# Core Engine Performance Test Report

## Performance Summary
- Overall Score: 87.3/100
- System Readiness: Production Ready

## Key Findings

### Latency Performance
**DataManager:**
- get_market_data: 2.34ms avg, 8.91ms P99
- get_historical_data: 5.67ms avg, 15.23ms P99

### Memory Usage
**StrategyManager:**
- signal_generation: 89.2% efficiency, 0 leaks detected

### Throughput Performance
**RiskManager:**
- authorize_trading_decision: 1,247 ops/sec peak, 98.5% reliability

## Optimization Recommendations
1. **DataManager - get_market_data**
   - Issue: High P95 latency: 6.7ms
   - Recommendation: Consider async optimization or caching
   - Priority: Medium
```

## 🔧 Configuration

### Test Configuration

```python
from tests.performance import LoadTestConfiguration

config = LoadTestConfiguration(
    component_name="MyComponent",
    operation_name="my_operation",
    target_operations=1000,
    concurrent_workers=[1, 2, 4, 8, 16],  # Test different concurrency levels
    duration_seconds=30,
    ramp_up_seconds=5,
    max_cpu_percent=90.0,
    max_memory_mb=8192.0,
    max_error_rate=0.05,
    enable_warmup=True,
    warmup_operations=100
)
```

### Profiler Configuration

```python
# Latency profiler
latency_profiler = LatencyProfiler(max_samples=10000)

# Memory profiler
memory_profiler = MemoryProfiler(
    snapshot_interval=1.0,  # seconds
    max_snapshots=10000
)

# Throughput benchmarker
throughput_benchmarker = ThroughputBenchmarker(max_measurements=10000)
```

## 🎯 Best Practices

### 1. Test Environment
- Run tests on dedicated hardware when possible
- Minimize background processes during testing
- Use consistent system configuration across test runs
- Monitor system resources during testing

### 2. Test Design
- Start with quick tests to validate setup
- Use appropriate iteration counts for statistical significance
- Test multiple concurrency levels for scalability analysis
- Include warmup phases for JIT compilation effects

### 3. Result Interpretation
- Focus on percentiles (P95, P99) rather than just averages
- Look for performance degradation under load
- Monitor memory efficiency and leak detection
- Consider error rates in throughput analysis

### 4. Optimization Workflow
1. **Baseline** - Establish current performance metrics
2. **Identify** - Find bottlenecks using integrated analysis
3. **Optimize** - Apply recommended optimizations
4. **Validate** - Re-run tests to measure improvements
5. **Iterate** - Repeat until performance targets are met

## 🔍 Advanced Features

### Custom Decorators

```python
from tests.performance import measure_latency

@measure_latency("MyComponent", "decorated_operation", latency_profiler)
async def my_async_function():
    # Function automatically measured
    await asyncio.sleep(0.001)
    return "result"
```

### Memory Leak Detection

```python
# Automatic leak detection
leaks = memory_profiler.detect_memory_leaks("MyComponent", "operation", min_samples=100)

for leak in leaks:
    print(f"Leak detected: {leak.object_type}")
    print(f"Leak rate: {leak.leak_rate_mb_per_sec:.4f} MB/sec")
    print(f"Confidence: {leak.detection_confidence:.2f}")
```

### Performance Correlations

```python
# Analyze correlations between metrics
analysis = test_suite._analyze_performance_correlations()
print(f"Latency-Memory correlation: {analysis['latency_memory_correlation']:.2f}")
```

## 📋 Requirements

- Python 3.8+
- numpy
- pandas
- psutil
- asyncio
- Core engine components (for integration tests)

## 🤝 Contributing

When adding new performance tests:

1. Follow the existing patterns for component testing
2. Include appropriate error handling and logging
3. Add statistical analysis for new metrics
4. Update documentation and examples
5. Ensure tests are deterministic and repeatable

## 📚 API Reference

### Core Classes

- `LatencyProfiler` - Main latency measurement class
- `MemoryProfiler` - Memory usage and leak detection
- `ThroughputBenchmarker` - Throughput and scalability testing
- `PerformanceTestSuite` - Integrated testing framework

### Data Classes

- `LatencyMeasurement` - Single latency measurement
- `LatencyStatistics` - Statistical analysis of latency data
- `MemorySnapshot` - Memory usage at a point in time
- `MemoryAnalysis` - Comprehensive memory analysis
- `ThroughputMeasurement` - Single throughput measurement
- `ThroughputStatistics` - Throughput analysis and scalability metrics

### Configuration Classes

- `LoadTestConfiguration` - Throughput test configuration
- `MemoryLeak` - Memory leak detection results

For detailed API documentation, see the docstrings in each module.
