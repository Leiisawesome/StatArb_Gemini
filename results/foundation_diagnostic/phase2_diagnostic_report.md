# Phase 2 Foundation Diagnostic Report

**Run ID**: b0428318
**Constants**: v1.6-FINAL
**Timestamp**: 2026-02-21T08:23:30.549409+00:00
**Symbols**: AMD, CRWD, HOOD, META, MSFT, NET, NVDA, SNOW, TSLA, WMT

## Program Decision: **TERMINATE**

TERMINATED at Tier 1. Failed gates: T1.1, T1.2, T1.3, T1.4. No Tier 2/3 analysis performed per hierarchy discipline.

---

## Tier 1 — Existence

| Gate | Name | Result | Value | Threshold | Detail |
|------|------|--------|-------|-----------|--------|
| T1.1 | Continuation k=3 | **FAIL** | 0.4661 | 0.5500 | Pooled: point=0.4661 (req≥0.55), CI=[0.4557,0.4766] (req lower≥0.5), width=0.0209 (req≤0.06), N=8777 |
| T1.2 | Net edge after cost | **FAIL** | -4.6689 | 0.0000 | Mean net edge across symbols: -4.67 bps (req > 0.0 bps). Per-symbol: AMD=-2.53, CRWD=-7.99, HOOD=-3.21, META=-3.26, MSFT |
| T1.3 | Temporal stability | **FAIL** | 0.0000 | 0.5000 | 0/10 symbols stable (≥2/3 blocks positive). Per-symbol: AMD=0/3, CRWD=0/3, HOOD=0/3, META=0/3, MSFT=0/3, NET=0/3, NVDA=0 |
| T1.4 | Classification correlation | **FAIL** | -0.0315 | 0.0500 | Median correlation(flow_imbalance, forward_return) = -0.0315 (req > 0.05). Per-symbol: AMD=-0.0352, CRWD=-0.0147, HOOD=- |

## Per-Symbol Persistence Summary

| Symbol | Tier | k3 Point | k3 CI Low | Half-life (buckets) | Micro% | Rho | Temporal | Sweep |
|--------|------|----------|-----------|---------------------|--------|-----|----------|-------|
| AMD | B | 0.3990 | 0.3689 | 9.2 | 88% | -0.236 | 0/3 | 0/5 |
| CRWD | C | 0.4631 | 0.4362 | 9.0 | 82% | 0.115 | 0/3 | 0/5 |
| HOOD | B | 0.4442 | 0.4116 | 8.5 | 87% | 0.079 | 0/3 | 0/5 |
| META | B | 0.4995 | 0.4689 | 9.2 | 83% | -0.673 | 0/3 | 1/5 |
| MSFT | A | 0.5074 | 0.4624 | 7.8 | 84% | -0.588 | 0/3 | 1/5 |
| NET | C | 0.4929 | 0.4560 | 13.9 | 83% | -0.624 | 0/3 | 0/5 |
| NVDA | A | 0.5332 | 0.4975 | 29.7 | 86% | -0.467 | 0/3 | 1/5 |
| SNOW | C | 0.4602 | 0.4326 | 10.1 | 81% | -0.103 | 0/3 | 0/5 |
| TSLA | A | 0.4238 | 0.3945 | 11.4 | 88% | -0.236 | 0/3 | 0/5 |
| WMT | A | 0.5198 | 0.4678 | 3.1 | 84% | -0.770 | 0/3 | 0/5 |

## Per-Symbol Economics Summary

| Symbol | Tier | Gross (bps) | Cost (bps) | Net Mean | Net Median | Hit Rate | Corr |
|--------|------|-------------|------------|----------|------------|----------|------|
| AMD | B | -0.31 | 2.22 | -2.53 | -1.21 | 46.4% | -0.0352 |
| CRWD | C | -0.10 | 7.88 | -7.99 | -5.76 | 32.6% | -0.0147 |
| HOOD | B | -0.40 | 2.81 | -3.21 | -1.50 | 46.8% | -0.0278 |
| META | B | -0.71 | 2.54 | -3.26 | -2.19 | 40.9% | -0.0689 |
| MSFT | A | -1.14 | 1.09 | -2.22 | -1.29 | 43.6% | -0.0898 |
| NET | C | -0.62 | 13.22 | -13.84 | -9.59 | 31.2% | -0.0257 |
| NVDA | A | -0.77 | 0.74 | -1.51 | -0.79 | 46.4% | -0.0508 |
| SNOW | C | -0.89 | 7.41 | -8.29 | -5.08 | 35.1% | -0.0479 |
| TSLA | A | -0.43 | 1.17 | -1.61 | -0.59 | 48.2% | -0.0187 |
| WMT | A | -0.50 | 1.73 | -2.24 | -1.43 | 42.3% | -0.0257 |
