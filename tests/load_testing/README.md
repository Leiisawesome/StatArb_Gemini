# Load Testing Framework

**Production-Level Load Testing for StatArb_Gemini Trading System**

## Overview

This load testing framework validates the system's readiness for production deployment by simulating realistic trading workloads and failure scenarios.

### Performance Targets

- **Throughput**: 10,000+ orders per day
- **Latency**: <100ms average, <200ms P99
- **Reliability**: 95%+ success rate
- **Stability**: 72+ hour continuous operation
- **Recovery**: <5 second failover time

## Components

### 1. Order Generator (`order_generator.py`)

Generates realistic trading orders following production patterns.

**Features**:
- Multiple order patterns (steady, burst, market hours, stress)
- Multi-strategy simulation (momentum, mean reversion, pairs trading)
- Realistic order sizes (log-normal distribution)
- Configurable symbols and rates

**Usage**:
```python
from tests.load_testing.order_generator import OrderGenerator, OrderGeneratorConfig, OrderPattern

# Quick test - generate 100 orders
orders = await generate_test_orders(100, OrderPattern.STEADY)

# Custom configuration
config = OrderGeneratorConfig(
    target_orders_per_day=10000,
    pattern=OrderPattern.MARKET_HOURS,
    strategy_weights={'momentum': 0.4, 'mean_reversion': 0.35, 'pairs_trading': 0.25}
)
generator = OrderGenerator(config)
await generator.generate_orders(duration_seconds=3600)
```

### 2. Performance Monitor (`performance_monitor.py`)

Real-time performance tracking and metrics collection.

**Metrics Tracked**:
- Order latency (avg, P50, P95, P99, max, min)
- Throughput (orders/second)
- System resources (CPU, memory)
- Network I/O
- Error rates and types

**Usage**:
```python
from tests.load_testing.performance_monitor import PerformanceMonitor, PerformanceMonitorConfig

monitor = PerformanceMonitor()
await monitor.start()

# Record orders
monitor.record_order_submission(order_id)
# ... process order ...
monitor.record_order_completion(order_id, success=True)

await monitor.stop()  # Prints final report
```

### 3. Load Test Runner (`load_test_runner.py`)

Main orchestrator for running load tests.

**Test Types**:
- **Quick Test**: 1,000 orders in 1 minute
- **Standard Test**: 10,000 orders over 6.5 hours (market hours)
- **Stress Test**: Maximum sustained load (30+ minutes)

**Usage**:
```bash
# Quick validation test
python tests/load_testing/load_test_runner.py quick

# Full production simulation
python tests/load_testing/load_test_runner.py standard

# Stress test (30 minutes)
python tests/load_testing/load_test_runner.py stress --duration 30
```

### 4. Continuous Test (`continuous_test.py`)

72-hour continuous operation test for long-term stability validation.

**Features**:
- Memory leak detection (growth rate monitoring)
- Performance degradation detection
- Periodic health checks
- Auto-recovery on failures
- State persistence and resume capability

**Usage**:
```bash
# Start 72-hour test
python tests/load_testing/continuous_test.py --duration 72

# Resume from checkpoint
python tests/load_testing/continuous_test.py --resume

# Shorter duration for testing
python tests/load_testing/continuous_test.py --duration 24 --orders-per-day 5000
```

**Health Checks**:
- Every 15 minutes by default
- Monitors memory growth (<10MB/hour threshold)
- Detects performance degradation (>20% slowdown)
- Validates error rates (<5%)

### 5. Failover Tester (`failover_test.py`)

Tests system resilience under various failure scenarios.

**Failure Scenarios**:
1. **Broker Failover**: Primary broker disconnection → backup failover
2. **Database Failover**: Primary database failure → replica promotion
3. **Redis Failure**: Cache unavailable → graceful degradation
4. **Network Partition**: Network split → operation queueing → recovery

**Usage**:
```bash
# Run all failover tests
python tests/load_testing/failover_test.py
```

**Success Criteria**:
- Detection time: <1 second
- Recovery time: <5 seconds
- Zero data loss
- 100% state consistency

## Quick Start

### 1. Setup Environment

```bash
# Activate virtual environment
source ai_integration_env/bin/activate

# Install dependencies (already included in project)
pip install psutil asyncio
```

### 2. Run Quick Validation

```bash
# Test order generator
python tests/load_testing/order_generator.py

# Test performance monitor
python tests/load_testing/performance_monitor.py

# Run quick load test (1 minute)
python tests/load_testing/load_test_runner.py quick
```

### 3. Run Standard Load Test

```bash
# Full production simulation (6.5 hours)
python tests/load_testing/load_test_runner.py standard
```

### 4. Run Failover Tests

```bash
# Test all failover scenarios
python tests/load_testing/failover_test.py
```

### 5. Run Continuous Test

```bash
# 72-hour stability test
python tests/load_testing/continuous_test.py --duration 72
```

## Test Execution Order

For complete production readiness validation:

1. **Quick Test** (1 minute) - Verify basic functionality
2. **Stress Test** (30 minutes) - Validate performance under load
3. **Failover Tests** (15 minutes) - Verify resilience
4. **Standard Test** (6.5 hours) - Simulate production day
5. **Continuous Test** (72 hours) - Long-term stability

## Metrics and Reports

### Output Files

All tests generate metrics files:
- `metrics_quick_*.jsonl` - Quick test metrics
- `metrics_standard_*.jsonl` - Standard test metrics
- `metrics_stress_*.jsonl` - Stress test metrics
- `continuous_test_metrics_*.jsonl` - 72-hour test metrics
- `failover_test_report_*.json` - Failover test results
- `continuous_test_*.log` - Detailed 72-hour test logs

### Metrics Format

JSON Lines format, one metric snapshot per line:
```json
{
  "timestamp": "2025-10-10T10:30:00",
  "orders": {"total": 1000, "successful": 980, "failed": 20, "rate": 5.5},
  "latency_ms": {"avg": 45.2, "p50": 42.0, "p95": 85.0, "p99": 120.0},
  "system": {"cpu_percent": 45.2, "memory_mb": 512.3, "memory_percent": 6.4},
  "errors": {"rate": 0.02, "by_type": {"timeout": 15, "rejected": 5}}
}
```

### Performance Assessment

Tests automatically assess performance against targets:

```
✅ Performance Assessment:
   Latency (P99 < 100ms):       ✅ PASS
   Error Rate (< 1.0%):         ✅ PASS
   Throughput (>= 0.12 orders/sec): ✅ PASS

🎉 OVERALL: PASS
```

## Configuration

### Order Generator Configuration

```python
OrderGeneratorConfig(
    target_orders_per_day=10000,        # Total orders per day
    pattern=OrderPattern.MARKET_HOURS,   # Order pattern
    strategy_weights={                   # Strategy distribution
        "momentum": 0.35,
        "mean_reversion": 0.35,
        "pairs_trading": 0.30
    },
    min_order_size=100,                  # Minimum order size
    max_order_size=10000,                # Maximum order size
    avg_order_size=1000                  # Average order size
)
```

### Performance Monitor Configuration

```python
PerformanceMonitorConfig(
    metrics_collection_interval_sec=1.0,   # Metrics update frequency
    metrics_display_interval_sec=10.0,     # Console display frequency
    latency_threshold_ms=100.0,            # Latency alert threshold
    error_rate_threshold=0.01,             # Error rate alert (1%)
    memory_threshold_mb=2048.0,            # Memory alert (2GB)
    cpu_threshold_percent=80.0             # CPU alert (80%)
)
```

### Continuous Test Configuration

```python
ContinuousTestConfig(
    target_duration_hours=72.0,                    # Test duration
    orders_per_day=10000,                          # Order rate
    health_check_interval_minutes=15,              # Health check frequency
    memory_leak_threshold_mb_per_hour=10.0,        # Memory leak detection
    performance_degradation_threshold_percent=20.0, # Performance degradation
    enable_auto_recovery=True                      # Auto-recover on failures
)
```

## Troubleshooting

### High Error Rates

If seeing >5% error rates:
1. Check broker connections
2. Verify network stability
3. Review system logs
4. Reduce order rate temporarily

### Memory Leaks

If continuous test detects memory growth:
1. Review `continuous_test_*.log` for details
2. Check for unclosed connections
3. Verify async cleanup in fixtures
4. Use memory profiler: `python -m memory_profiler script.py`

### Performance Degradation

If throughput degrades over time:
1. Check CPU/memory usage trends
2. Review database query performance
3. Check for connection pool exhaustion
4. Monitor disk I/O

### Failover Failures

If failover tests fail:
1. Verify backup broker/database configured
2. Check network connectivity
3. Review failover logic in broker manager
4. Test recovery procedures manually

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Load Testing

on:
  schedule:
    - cron: '0 2 * * *'  # Nightly at 2 AM
  workflow_dispatch:

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          python -m venv ai_integration_env
          source ai_integration_env/bin/activate
          pip install -r requirements.txt
      - name: Run Quick Load Test
        run: |
          source ai_integration_env/bin/activate
          python tests/load_testing/load_test_runner.py quick
      - name: Run Failover Tests
        run: |
          source ai_integration_env/bin/activate
          python tests/load_testing/failover_test.py
      - name: Upload Metrics
        uses: actions/upload-artifact@v2
        with:
          name: load-test-metrics
          path: metrics_*.jsonl
```

## Performance Benchmarks

### Expected Performance (Production Hardware)

| Metric | Target | Good | Excellent |
|--------|--------|------|-----------|
| Avg Latency | <100ms | <50ms | <20ms |
| P99 Latency | <200ms | <100ms | <50ms |
| Throughput | 10k orders/day | 25k orders/day | 50k orders/day |
| Error Rate | <1% | <0.1% | <0.01% |
| CPU Usage | <80% | <60% | <40% |
| Memory | <2GB | <1GB | <500MB |
| Recovery Time | <5s | <2s | <1s |

### Baseline Performance (Development Hardware)

Results from test environment (MacBook Pro, M1, 16GB RAM):
- **Order Generation**: 100-500 orders/second
- **Average Latency**: 10-20ms (simulated)
- **P99 Latency**: 50-100ms (simulated)
- **Memory Usage**: ~30MB baseline
- **CPU Usage**: <5% during steady load

## Next Steps

After completing load tests:

1. **Analyze Results**: Review all metrics files
2. **Identify Bottlenecks**: Focus on slowest components
3. **Optimize**: Apply performance improvements
4. **Retest**: Verify improvements
5. **Document**: Update benchmarks and thresholds
6. **Deploy**: Proceed with production deployment

## Support

For issues or questions:
1. Check logs in `tests/load_testing/*.log`
2. Review metrics in `metrics_*.jsonl` files
3. Consult `docs/phase4/` for detailed documentation
4. Refer to `CHANGELOG_PHASE4.md` for recent changes

## License

Part of StatArb_Gemini Trading System
