# Branch B — Pessimistic Liquidity Provision Simulation

**Constants**: v1.6-FINAL
**Symbols**: MSFT, NVDA
**Entry delay**: 100ms | **Stop-loss**: 3.0 bps | **Timeout**: 30s
**Queue model**: Last in visible queue (pessimistic)

## Decision: **PROCEED**

4/5 gates passed. Passive liquidity provision shows edge under pessimistic assumptions. Proceed to full strategy design.

---

## Gate Results

| Gate | Name | Result | Value | Threshold |
|------|------|--------|-------|-----------|
| B1 | Fill probability > 30% | **PASS** | 0.7117 | 0.3000 |
| B2 | Mean spread capture > 1 bps | **FAIL** | 0.9374 | 1.0000 |
| B3 | Hit rate > 55% | **PASS** | 0.5644 | 0.5500 |
| B4 | Portfolio daily edge > 0.5 bps | **PASS** | 3.0791 | 0.5000 |
| B5 | Annualized Sharpe ≥ 0.8 | **PASS** | 7.7905 | 0.8000 |

## P&L Distribution (filled trades only)

- **Mean**: 0.94 bps
- **Median**: 0.27 bps
- **Std**: 3.84 bps
- **P10/P90**: -3.16 / 5.76 bps
- **Skew**: 1.53 | **Kurtosis**: 3.57
- **Hit rate**: 56.4%
- **Mean hold**: 1332 ms | **Median hold**: 540 ms

## Exit Reasons

- **end_of_data**: 12 (2.8%) — mean PnL: 4.07 bps
- **spread_normal**: 345 (80.8%) — mean PnL: 1.73 bps
- **stop_loss**: 70 (16.4%) — mean PnL: -3.52 bps

## Per-Symbol Breakdown

| Symbol | Total | Filled | Fill% | Mean PnL | Median PnL | Hit Rate | Hold (ms) | Queue |
|--------|-------|--------|-------|----------|------------|----------|-----------|-------|
| MSFT | 300 | 168 | 56.0% | 1.52 | 0.52 | 60.7% | 2235 | 669 |
| NVDA | 300 | 259 | 86.3% | 0.56 | 0.26 | 53.7% | 746 | 2422 |