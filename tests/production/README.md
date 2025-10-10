# Production Testing Suite

This directory contains production-level testing infrastructure for validating the StatArb_Gemini trading system before deployment.

## Overview

The production testing suite ensures the system is ready for live trading by validating:
- Performance under production-scale loads
- Stability during continuous operation
- Resilience to failures
- Recovery capabilities
- Resource efficiency

## Test Categories

### 1. Load Testing (`test_load_testing.py`)

Tests system performance under realistic production loads.

**Key Tests:**
- `test_baseline_load_100_orders`: Baseline performance with 100 orders
- `test_production_scale_load_10k_orders`: Production scale with 10,000 orders
- `test_peak_load_stress`: Peak load burst scenarios

**Metrics Collected:**
- Throughput (orders/second)
- Latency (avg, p50, p95, p99, max)
- Memory usage
- CPU usage
- Error rates

**Running Load Tests:**
```bash
# Activate environment
source ai_integration_env/bin/activate

# Run all load tests
pytest tests/production/test_load_testing.py -v -m load_test

# Run specific test
pytest tests/production/test_load_testing.py::TestLoadPerformance::test_baseline_load_100_orders -v
```

**Production Requirements:**
- Average latency: <100ms
- P99 latency: <500ms
- Throughput: >10 orders/second
- Error rate: <0.1%
- Memory usage: <2GB

### 2. Stress Testing (`test_stress_testing.py`)

Tests system stability during continuous operation.

**Key Tests:**
- `test_short_stress_test_1_hour`: 1-hour validation test
- `test_full_stress_test_72_hours`: Full 72-hour production readiness test

**Monitoring:**
- Memory leak detection
- Performance degradation tracking
- Connection stability
- Resource usage trends
- Error accumulation

**Running Stress Tests:**
```bash
# Short stress test (1 hour)
pytest tests/production/test_stress_testing.py::TestStressTest::test_short_stress_test_1_hour -v

# Full 72-hour test (manual execution recommended)
pytest tests/production/test_stress_testing.py::TestStressTest::test_full_stress_test_72_hours -v

# Standalone runner (with custom duration)
python tests/production/test_stress_testing.py
```

**Checkpoints:**
- Hourly system snapshots
- Memory usage tracking
- Performance metrics
- Health status validation

**Output:**
- JSON report: `stress_test_report.json`
- Checkpoint data for trend analysis
- Memory leak detection results
- Performance degradation alerts

### 3. Failover & Recovery Testing (`test_failover_recovery.py`)

Tests system resilience and recovery capabilities.

**Test Categories:**

#### Broker Failover
- Primary broker connection loss
- Automatic failover to backup
- Reconnection after recovery
- Order routing during failover

#### Database Failover
- Connection pool exhaustion
- Connection timeout handling
- Failover to replica database
- Recovery and synchronization

#### Redis Failover
- Cache connection failure
- Graceful degradation
- Reconnection and warmup

#### Network Partition
- Partition detection
- Recovery procedures
- Split-brain prevention

#### Crash Recovery
- State recovery from persistent storage
- In-flight order recovery
- Partial execution handling
- Data corruption detection

**Running Failover Tests:**
```bash
# All failover tests
pytest tests/production/test_failover_recovery.py -v -m failover

# Specific category
pytest tests/production/test_failover_recovery.py::TestBrokerFailover -v
```

**Note:** Most failover tests are currently marked as `skip` and require:
- Actual broker adapters
- Database replication setup
- Distributed system configuration
- State persistence implementation

These are designed as templates to implement when infrastructure is ready.

## Production Readiness Checklist

Before deploying to production, ensure:

### Testing
- [x] Load testing framework created
- [ ] Baseline load test (100 orders) passes
- [ ] Production scale test (10,000 orders) passes
- [ ] Peak load stress test passes
- [ ] 1-hour stress test passes
- [ ] 72-hour stress test passes
- [ ] Failover tests implemented for your infrastructure

### Performance
- [ ] Average latency <100ms
- [ ] P99 latency <500ms
- [ ] Throughput >10 orders/second
- [ ] Error rate <0.1%
- [ ] Memory usage <2GB

### Reliability
- [ ] No memory leaks detected
- [ ] No performance degradation over time
- [ ] Failover scenarios tested
- [ ] Recovery procedures validated

### Documentation
- [x] Production deployment checklist created
- [x] Incident response playbook created
- [ ] Team trained on procedures
- [ ] On-call rotation established

## Reports & Artifacts

### Load Test Reports
- Console output with detailed metrics
- JSON format available for automation
- Throughput, latency, and resource metrics

### Stress Test Reports
- `stress_test_report.json`: Complete test report
- Checkpoint data with timestamps
- Memory leak detection results
- Performance trend analysis

### Recommended Analysis
```python
import json

# Load stress test report
with open('stress_test_report.json') as f:
    report = json.load(f)

# Analyze memory trend
checkpoints = report['checkpoints']
memory_values = [cp['memory']['rss_mb'] for cp in checkpoints]

# Plot trends (if matplotlib available)
import matplotlib.pyplot as plt
plt.plot(memory_values)
plt.xlabel('Checkpoint')
plt.ylabel('Memory (MB)')
plt.title('Memory Usage Over Time')
plt.show()
```

## Integration with CI/CD

### Automated Testing
```yaml
# Example GitHub Actions workflow
name: Production Readiness Tests

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 0 * * 0'  # Weekly

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run load tests
        run: |
          source ai_integration_env/bin/activate
          pytest tests/production/test_load_testing.py -v -m load_test
  
  stress-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run 1-hour stress test
        run: |
          source ai_integration_env/bin/activate
          pytest tests/production/test_stress_testing.py::TestStressTest::test_short_stress_test_1_hour -v
```

### Pre-Deployment Gates
- All load tests must pass
- 1-hour stress test must pass
- No memory leaks detected
- Performance within acceptable limits

## Manual Testing Procedures

### Running Full 72-Hour Test

**Preparation:**
1. Deploy to staging environment identical to production
2. Load production-scale data
3. Configure production-equivalent infrastructure
4. Clear all logs and metrics
5. Notify team of long-running test

**Execution:**
```bash
# Start test in tmux/screen session (so it survives disconnection)
tmux new -s stress-test

# Activate environment
source ai_integration_env/bin/activate

# Run test
pytest tests/production/test_stress_testing.py::TestStressTest::test_full_stress_test_72_hours -v \
  2>&1 | tee stress_test_72h.log

# Detach: Ctrl+B, D
```

**Monitoring:**
```bash
# Reattach to session
tmux attach -t stress-test

# Check progress
tail -f stress_test_72h.log

# Monitor report
watch -n 300 "cat stress_test_72h_report.json | jq '.summary'"
```

**After Completion:**
1. Review report: `stress_test_72h_report.json`
2. Analyze checkpoints for trends
3. Verify no memory leaks
4. Verify no performance degradation
5. Document any issues
6. Sign off on production readiness

## Troubleshooting

### Test Hangs
- Check for infinite loops
- Verify timeout settings
- Check resource availability
- Review application logs

### High Memory Usage
- Check for memory leaks
- Review object lifecycles
- Verify proper cleanup
- Consider increasing limits

### High Error Rates
- Review error logs
- Check configuration
- Verify test data validity
- Investigate root causes

### Performance Issues
- Profile hot paths
- Check database queries
- Review network latency
- Optimize bottlenecks

## Best Practices

1. **Run tests in staging first** - Never run production-level load tests in production
2. **Monitor continuously** - Watch metrics throughout tests
3. **Start small** - Begin with short tests, scale up gradually
4. **Document everything** - Record all observations and issues
5. **Automate when possible** - Integrate tests into CI/CD
6. **Review regularly** - Update tests as system evolves

## Next Steps

After completing production testing:

1. **Review Results**: Analyze all test reports
2. **Address Issues**: Fix any problems discovered
3. **Document Changes**: Update documentation
4. **Train Team**: Ensure team understands procedures
5. **Deploy to Production**: Follow deployment checklist
6. **Monitor Closely**: Watch production metrics carefully
7. **Iterate**: Continuously improve based on production data

## Support

For questions or issues:
- Review documentation: `docs/PRODUCTION_DEPLOYMENT_CHECKLIST.md`
- Review playbook: `docs/INCIDENT_RESPONSE_PLAYBOOK.md`
- Contact: [Your team's contact info]

---

**Last Updated:** October 8, 2025  
**Maintained By:** StatArb_Gemini Team
