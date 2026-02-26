# Event-Driven State Transition Experiment

**Constants**: v1.6-FINAL
**Timestamp**: 2026-02-21T10:11:59.049033+00:00
**Events**: 844 extreme + 999 control

## Decision: **PROCEED**

3/4 gates passed. State transitions are detectable and potentially exploitable. Proceed to event-driven strategy design.

---

## Gate Results

| Gate | Name | Result | Detail |
|------|------|--------|--------|
| G1 | Spread widens after extreme imbalance | **PASS** | Significant widening at: ['1s', '5s', '10s'] |
| G2 | Midpoint trajectory is directionally biased | **PASS** | Significant correlation at: ['1s', '5s'] |
| G3 | Spread recovery predictable from imbalance | **PASS** | corr(|imb|, recovery_ms) = 0.3504, p = 0.0000 |
| G4 | Depth asymmetry after extreme imbalance | **FAIL** | Depleted side change: 80.9%, p = 0.0231 |

---

## Spread Trajectory (Extreme vs Control)

| Time | Extreme Δ (bps) | Control Δ (bps) | Difference | t-stat | p-value |
|------|-----------------|-----------------|------------|--------|---------|
| 10s | 0.79 | -2.02 | 2.81 | 2.72 | 0.0067 |
| 1s | 4.43 | -1.67 | 6.10 | 4.24 | 0.0000 |
| 30s | -1.40 | -1.80 | 0.41 | 0.42 | 0.6740 |
| 5s | 1.08 | -1.89 | 2.97 | 3.01 | 0.0027 |
| 60s | -2.09 | -2.50 | 0.41 | 0.48 | 0.6308 |

## Midpoint Trajectory After Extreme Events

| Time | Corr(imb, mid) | p-value | Rev Mean (bps) | Rev Hit Rate |
|------|---------------|---------|----------------|--------------|
| 10s | 0.0155 | 0.7112 | -0.31 | 49.1% |
| 1s | 0.1824 | 0.0000 | -2.21 | 41.0% |
| 30s | 0.0280 | 0.5475 | -0.78 | 48.8% |
| 5s | 0.1077 | 0.0084 | -1.67 | 45.7% |
| 60s | -0.0354 | 0.4809 | 0.48 | 51.1% |

## Spread Recovery

- **extreme_median_ms**: 34.54
- **extreme_mean_ms**: 10094.13
- **extreme_p10_ms**: 0.04
- **extreme_p90_ms**: 60000.00
- **control_median_ms**: 9.47
- **control_mean_ms**: 2101.11
- **corr_imb_recovery**: 0.35
- **p_value**: 0.00

## Depth Analysis

- **extreme_bid_change_pct**: 51.16
- **extreme_ask_change_pct**: 55.29
- **control_bid_change_pct**: 22.25
- **control_ask_change_pct**: 21.95
- **mean_depleted_side_change_pct**: 80.94
- **depletion_t_stat**: 2.28
- **depletion_p_value**: 0.02

---

## Per-Symbol Breakdown

| Symbol | Tier | Spread Δ 5s | Rev 5s (bps) | Rev Hit | Recovery (ms) |
|--------|------|-------------|--------------|---------|---------------|
| AMD | ? | 1.84 | 1.55 | 52.9% | 5 |
| CRWD | ? | 4.55 | 0.69 | 47.4% | 35 |
| HOOD | ? | 0.71 | -3.69 | 41.9% | 46 |
| META | ? | 3.54 | -1.03 | 54.0% | 293 |
| MSFT | ? | 0.07 | 4.33 | 53.8% | 163 |
| NET | ? | 11.55 | -6.02 | 37.9% | 632 |
| NVDA | ? | 0.21 | -1.59 | 37.6% | 1 |
| SNOW | ? | 6.14 | -10.85 | 41.7% | 824 |
| TSLA | ? | 0.35 | -0.64 | 42.9% | 11 |
| WMT | ? | -6.86 | -7.90 | 40.6% | 690 |

## Per-Tier Breakdown

| Tier | N | Spread Δ 5s | Rev 5s (bps) | Rev Hit 5s |
|------|---|-------------|--------------|------------|
| A | 329 | -0.61 | -0.60 | 43.6% |
| B | 267 | 2.02 | -0.77 | 50.0% |
| C | 248 | 6.22 | -5.82 | 42.6% |