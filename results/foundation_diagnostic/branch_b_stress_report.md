# Branch B — Stress Test Report

**Constants**: v1.6-FINAL
**Symbols**: MSFT, NVDA, TSLA, WMT
**Events**: 1049 across 130 trading days

## Verdict: **PROCEED**

5/5 stress tests passed including critical 300ms+1.5x stress. 4/4 symbols positive. Edge is structurally robust. Proceed to strategy design.

---

## 1. Mean PnL Confidence Interval

- **Mean**: 1.229 bps
- **SE**: 0.199 bps
- **95% CI**: [0.839, 1.619] bps
- **Lower bound > 0**: Yes

## 2. True Sharpe (with zero-event days)

- **Annualized Sharpe**: 4.01
- **Daily mean**: 7.659 bps
- **Daily std**: 30.295 bps
- **Active days**: 128 / 130
- **Passes ≥ 0.8**: Yes

## 3. Delay × Queue Stress Grid

| Delay (ms) | Queue Mult | Fill% | N Filled | Mean PnL | Hit Rate | Edge+ |
|------------|------------|-------|----------|----------|----------|-------|
| 100 | 1.0x | 77.2% | 810 | 1.23 | 54.9% | Yes |
| 100 | 1.5x | 76.4% | 801 | 1.12 | 52.3% | Yes |
| 100 | 2.0x | 75.3% | 790 | 1.08 | 51.3% | No |
| 200 | 1.0x | 77.9% | 817 | 1.24 | 56.4% | Yes |
| 200 | 1.5x | 77.2% | 810 | 1.24 | 54.3% | Yes |
| 200 | 2.0x | 76.0% | 797 | 1.13 | 53.5% | Yes |
| 300 | 1.0x | 78.0% | 818 | 1.33 | 56.0% | Yes |
| 300 | 1.5x | 77.1% | 809 | 1.27 | 53.5% | Yes |
| 300 | 2.0x | 76.3% | 800 | 1.22 | 52.5% | Yes |
| 500 | 1.0x | 78.3% | 821 | 1.40 | 58.1% | Yes |
| 500 | 1.5x | 77.2% | 810 | 1.31 | 55.3% | Yes |
| 500 | 2.0x | 76.6% | 804 | 1.27 | 54.0% | Yes |

**Critical stress point (300ms + 1.5x queue)**: fill=77.1%, mean=1.27 bps, hit=53.5% → **SURVIVES**

## 4. Tail Risk

- **P5 (5th percentile)**: -3.63 bps
- **CVaR5 (mean of worst 5%)**: -5.69 bps
- **Worst single trade**: -14.00 bps
- **Acceptable (CVaR5 > -10 bps)**: Yes

## 5. Temporal Stability (3 blocks)

| Block | Period | N Filled | Mean PnL | Hit Rate | Positive |
|-------|--------|----------|----------|----------|----------|
| 1 | 2025-08-11 to 2025-10-09 | 281 | 1.22 | 57.3% | Yes |
| 2 | 2025-10-10 to 2025-12-10 | 273 | 0.37 | 51.6% | Yes |
| 3 | 2025-12-11 to 2026-02-13 | 256 | 2.15 | 55.9% | Yes |

**Stable**: 3/3 blocks positive → STABLE

## 6. Per-Symbol Breakdown (baseline: 100ms, 1.0x queue)

| Symbol | Events | Filled | Fill% | Mean PnL | Median PnL | Hit Rate | Hold (ms) |
|--------|--------|--------|-------|----------|------------|----------|-----------|
| MSFT | 255 | 169 | 66.3% | 1.56 | 0.54 | 60.9% | 2223 |
| NVDA | 274 | 260 | 94.9% | 0.56 | 0.26 | 53.8% | 741 |
| TSLA | 285 | 260 | 91.2% | 0.55 | 0.23 | 56.2% | 1044 |
| WMT | 235 | 121 | 51.5% | 3.67 | -0.00 | 46.3% | 2915 |

## 7. Verdict Summary

| Check | Result |
|-------|--------|
| ci_lower_above_zero | PASS |
| true_sharpe_above_0_8 | PASS |
| tail_cvar5_above_neg10 | PASS |
| stress_300ms_1_5x_survives | PASS |
| temporal_2_of_3_stable | PASS |