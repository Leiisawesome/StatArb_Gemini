# Branch A — Continuation Ceiling Check

**Constants**: v1.6-FINAL
**Symbols**: MSFT, NVDA
**Events**: 400

## Conclusion: No latency yields positive net edge. Continuation is absorbed by spread widening at all tested latencies.

## Latency Sweep

| Latency (ms) | N | Continuation (bps) | Half-Spread (bps) | Net (bps) | Hit Rate | Viable |
|-------------|---|---------------------|-------------------|-----------|----------|--------|
| 50 | 325 | -0.87 | 1.37 | -2.23 | 29.2% | No |
| 100 | 327 | -0.89 | 1.47 | -2.36 | 29.7% | No |
| 200 | 327 | -1.07 | 1.54 | -2.61 | 28.4% | No |
| 500 | 325 | -1.00 | 1.55 | -2.55 | 33.5% | No |
| 1000 | 314 | -0.97 | 1.44 | -2.41 | 30.6% | No |
| 2000 | 304 | -0.44 | 1.37 | -1.81 | 33.9% | No |
| 5000 | 297 | -0.34 | 1.60 | -1.94 | 37.0% | No |