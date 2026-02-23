# Branch B — Final Validation Report

**Constants**: v1.6-FINAL
**Symbols**: MSFT, NVDA, TSLA, WMT
**Events**: 1049
**Entry delay**: 200ms (validation baseline)

## Verdict: **PROCEED TO SHADOW TRADING**

All 4 validations passed. Edge survives regime, correlation, capacity, and execution stress.


| Validation | Result |
|------------|--------|
| V1: Cross-regime | PASS |
| V2: Correlation stress | PASS |
| V3: Capacity (500 shares) | PASS |
| V4: Execution realism | PASS |

---

## V1: Cross-Regime Slice

Split 1049 events by daily spread volatility (median=1.90 bps).

| Regime | N Filled | Mean PnL | Hit Rate | Positive |
|--------|----------|----------|----------|----------|
| High-vol (65d) | 455 | 1.77 | 57.1% | Yes |
| Low-vol (65d) | 353 | 0.42 | 49.9% | Yes |

WMT big wins (>5bps): 35 total, 29 in high-vol (CLUSTERED)

## V2: Correlation Stress

**Pairwise daily PnL correlations:**

- MSFT-NVDA: 0.042
- MSFT-TSLA: -0.017
- MSFT-WMT: -0.010
- NVDA-TSLA: -0.040
- NVDA-WMT: 0.119
- TSLA-WMT: -0.023

- **Mean pairwise correlation**: 0.012
- **Portfolio Sharpe**: 3.79
- **Worst day**: -20.81 bps (2025-10-30)
- **Max drawdown**: -33.07 bps
- **Event clustering (5-min window)**: 31.1%
- **Worst day acceptable (> -30 bps)**: Yes

## V3: Capacity Sweep

| Clip Size | Fill% | N Filled | Mean PnL | Hit Rate | Queue Ahead |
|-----------|-------|----------|----------|----------|-------------|
| 100 | 77.0% | 808 | 1.18 | 54.0% | 475 |
| 500 | 73.5% | 771 | 0.96 | 49.2% | 885 |
| 1000 | 71.6% | 751 | 0.75 | 46.3% | 1381 |
| 2000 | 69.6% | 730 | 0.66 | 41.8% | 2387 |
| 5000 | 64.6% | 678 | 0.36 | 36.0% | 5401 |

## V4: Execution Realism

Ugly simulation: +1 bps stop slippage, +200ms cancel lag on exits.

- **Baseline mean**: 1.18 bps
- **Ugly mean**: 1.01 bps
- **Degradation**: 14.2%
- **Ugly hit rate**: 53.1%
- **Stop exits**: baseline=162, ugly=162
- **Edge survives**: Yes

## Quote Fade Diagnostic

- **Spread still widened (>110% baseline) at entry**: 525/1030 (51.0%)
- **Mean spread ratio at entry**: 4.47x baseline
- **Median spread ratio at entry**: 1.13x baseline
- **P25/P75 ratio**: 0.90 / 2.65
