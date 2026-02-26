# Branch B — Mechanism Confirmation + Deployment Readiness

**Constants**: v1.6-FINAL

## 1. Mechanism Regression: What Drives PnL?

N = 809 filled trades

### Univariate

- **PnL ~ spread_ratio**: slope=0.480, r=0.423, p=0.0000
- **PnL ~ |imbalance|**: slope=3.463, r=0.146, p=0.0000

### Multivariate OLS

- **R²**: 0.1837
- **β_spread**: 0.465 (t=12.66, p=0.0000)
- **β_imbalance**: 1.723 (t=2.24, p=0.0252)
- **Standardized β_spread**: 0.410
- **Standardized β_imbalance**: 0.073
- **Dominant factor**: **spread_ratio**

### PnL by Spread Ratio Quintile

| Quintile | Spread Ratio | N | Mean PnL | Hit Rate |
|----------|-------------|---|----------|----------|
| Q1 | 0.02-0.71 | 162 | 1.48 | 51.2% |
| Q2 | 0.71-1.00 | 162 | 1.46 | 63.0% |
| Q3 | 1.00-1.13 | 161 | 0.47 | 62.1% |
| Q4 | 1.13-2.00 | 162 | 0.54 | 57.4% |
| Q5 | 2.00-70.11 | 162 | 2.36 | 50.0% |

## 2. Conditional Correlation (Does risk concentrate in high-vol?)

| Regime | Mean Pairwise Corr | N Days |
|--------|--------------------|--------|
| All | 0.005 | 130 |
| High-vol | -0.033 | 65 |
| Low-vol | 0.026 | 65 |

**Correlation spike in high-vol**: -0.038 (Not significant — diversification holds)

**Pairwise detail (high-vol only):**

- MSFT-NVDA: -0.084
- MSFT-TSLA: -0.014
- MSFT-WMT: -0.067
- NVDA-TSLA: -0.151
- NVDA-WMT: 0.135
- TSLA-WMT: -0.020

## 3. Intraday Inventory Stacking

- **Max concurrent positions**: 11
- **Mean concurrent**: 1.3
- **P95 concurrent**: 3
- **Worst 5-min rolling PnL**: -16.33 bps
- **Worst 30-min rolling PnL**: -16.33 bps
