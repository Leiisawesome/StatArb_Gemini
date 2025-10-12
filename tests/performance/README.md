# Performance Testing & Analysis Tools

**Comprehensive performance testing, profiling, and benchmarking infrastructure for the StatArb_Gemini trading system.**

---

## Overview

This directory contains organized tools for performance testing, profiling, benchmarking, stress testing, validation, and analysis of the core trading engine. All tools are organized into clear subdirectories by purpose.

**Test Count:** 1388 tests (all collecting successfully)  
**Organization Grade:** A  
**Structure:** 7 subdirectories, 33 organized files

---

## Directory Structure

```
tests/performance/
├── benchmarks/         # Performance benchmarking tools (4 files)
├── profiling/          # Code profiling and analysis (5 files)
├── stress_tests/       # System stress testing (4 files)
├── tests/              # Pytest test files (5 files)
├── validation/         # Core engine validation (5 files)
├── utilities/          # Analysis and utility tools (5 files)
└── runners/            # Test execution scripts (5 files)
```

---

## Subdirectories

### 📊 `benchmarks/` (4 files)

**Purpose:** Performance benchmarking and measurement tools

**Files:**
- `benchmark_suite.py` - Comprehensive benchmark suite for all components
- `database_benchmarks.py` - Database operation performance benchmarks
- `latency_testing.py` - Latency profiling and measurement framework
- `throughput_benchmarking.py` - Throughput testing and analysis tools

**Features:**
- **Nanosecond precision** timing measurements
- **Statistical analysis** with percentiles (P50, P90, P95, P99, P99.9)
- **Jitter analysis** and outlier detection
- **Async/sync operation** support
- **Context managers** and decorators for easy integration
- **Component-specific** test suites

**Use Cases:**
- Measure system latency and response times
- Benchmark database operations
- Test throughput under various loads
- Compare performance across versions

**Example Usage:**
```python
from tests.performance.benchmarks.latency_testing import LatencyProfiler
from tests.performance.benchmarks.throughput_benchmarking import ThroughputBenchmarker

# Measure latency
latency_profiler = LatencyProfiler()
async with latency_profiler.measure_latency("operation"):
    await perform_operation()

# Measure throughput
throughput_benchmarker = ThroughputBenchmarker()
result = await throughput_benchmarker.benchmark_throughput(
    operation,
    target_rate=1000,
    duration=60
)
print(f"Throughput: {result.operations_per_second:.2f} ops/sec")
```

---

### 🔍 `profiling/` (5 files)

**Purpose:** Code profiling and performance analysis tools

**Files:**
- `analyze_bottlenecks.py` - Identify performance bottlenecks in code
- `memory_profiler.py` - Memory profiling tool for leak detection
- `memory_profiling.py` - Memory profiling utilities and helpers
- `profile_trading_system.py` - Complete trading system profiler
- `profiler.py` - General profiling utilities and framework

**Features:**
- **Real-time memory** usage tracking
- **Memory leak detection** using statistical analysis
- **Garbage collection** pressure monitoring
- **Large object tracking** (>1MB objects)
- **Memory efficiency scoring** (0-100 scale)
- **Optimization recommendations**

**Use Cases:**
- Identify performance bottlenecks
- Detect memory leaks
- Profile memory usage patterns
- Analyze CPU-intensive operations
- Optimize hot code paths

**Example Usage:**
```python
from tests.performance.profiling.memory_profiling import MemoryProfiler, MemoryMonitoringContext

# Initialize memory profiler
memory_profiler = MemoryProfiler()

# Monitor memory usage
with MemoryMonitoringContext(memory_profiler, "MyComponent", "memory_test"):
    # Your memory-intensive code here
    data = allocate_large_data()

# Get memory analysis
analysis = memory_profiler.get_memory_analysis("MyComponent", "memory_test")
print(f"Peak memory: {analysis.peak_mb:.2f} MB")
print(f"Memory leak detected: {analysis.leak_detected}")
```

---

### 💥 `stress_tests/` (4 files)

**Purpose:** System stress testing under adverse conditions

**Files:**
- `data_corruption_testing.py` - Test behavior with corrupted data
- `memory_pressure_testing.py` - Test under memory constraints
- `network_failure_testing.py` - Test network failure scenarios
- `stress_testing.py` - General stress testing framework

**Use Cases:**
- Test system resilience
- Validate error handling
- Test recovery mechanisms
- Identify failure modes
- Ensure graceful degradation

**Example Usage:**
```python
from tests.performance.stress_tests.stress_testing import StressTest
from tests.performance.stress_tests.network_failure_testing import NetworkFailureTester

# Run stress test
stress_test = StressTest(config)
results = stress_test.run_stress_scenarios()

# Test network failures
network_tester = NetworkFailureTester()
recovery_time = network_tester.test_network_failure()
```

---

### ✅ `tests/` (5 files)

**Purpose:** Pytest test files for performance testing

**Files:**
- `test_market_conditions.py` - Market condition performance tests
- `test_memory_leak_detection.py` - Memory leak detection tests (5 tests)
- `test_performance_suite.py` - Comprehensive performance test suite
- `test_statistical_suite.py` - Statistical analysis tests
- `test_stress_suite.py` - Stress testing suite

**Use Cases:**
- Run automated performance tests
- Regression testing for performance
- CI/CD integration
- Performance validation

**Example Usage:**
```bash
# Run all performance tests
pytest tests/performance/tests/ -v

# Run specific test file
pytest tests/performance/tests/test_memory_leak_detection.py -v

# Run with markers
pytest tests/performance/tests/ -m "slow" -v
```

---

### 🔬 `validation/` (5 files)

**Purpose:** Core engine validation and verification scripts

**Files:**
- `final_validation.py` - Final comprehensive validation suite
- `improvements_validation.py` - Validate performance improvements
- `validate_core_engine_market_conditions.py` - Market condition validation
- `validate_core_engine_performance.py` - Performance validation
- `validate_core_engine_stress.py` - Stress test validation

**Use Cases:**
- Validate core engine behavior
- Verify performance improvements
- Check system correctness
- Pre-deployment validation

---

### 🛠️ `utilities/` (5 files)

**Purpose:** Analysis and utility tools

**Files:**
- `async_database.py` - Async database utilities and helpers
- `compare_performance.py` - Performance comparison tools
- `optimized_trading_system.py` - Optimized system utilities
- `statistical_analysis.py` - Statistical analysis engine
- `trend_analysis.py` - Trend analysis tools

**Use Cases:**
- Compare performance across versions
- Analyze performance trends
- Statistical analysis of results
- Generate performance reports

---

### 🏃 `runners/` (5 files)

**Purpose:** Test execution and orchestration scripts

**Files:**
- `example_performance_test.py` - Example performance test template
- `integration_test.py` - Integration test runner
- `run_demo.py` - Demo runner script
- `run_performance_tests.py` - Main performance test runner
- `test_runner.py` - General test runner framework

**Use Cases:**
- Run comprehensive test suites
- Orchestrate multiple tests
- Generate test reports
- CI/CD integration

---

## � Quick Start

### Running Performance Tests

```bash
# Run all performance tests
pytest tests/performance/tests/ -v

# Run comprehensive performance suite
python tests/performance/runners/run_performance_tests.py

# Run quick tests (reduced iterations)
python tests/performance/runners/run_performance_tests.py --quick

# Test specific component
python tests/performance/runners/run_performance_tests.py --component data_manager

# Enable verbose logging
python tests/performance/runners/run_performance_tests.py --verbose

# Run example tests
python tests/performance/runners/example_performance_test.py
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
