# Week 2 — Data Quality Report

**Generated**: 2026-02-21 07:22 UTC
**Constants Version**: v1.6-FINAL
**Total symbol-days**: 1300
**Valid symbol-days**: 1300

---

## Per-Symbol Summary

| Symbol | Tier | Days | Valid | Quote Match | Tick Rule % | Stale % | High-Lag % | Med Age (ms) | Buckets/Day | Confidence |
|--------|------|------|-------|-------------|-------------|---------|------------|--------------|-------------|------------|
| AMD | B | 130 | 130 | 99.7% | 23.7% | 37.2% | 12.8% | 162.3 | 194 | 99.7% |
| CRWD | C | 130 | 130 | 100.0% | 23.3% | 57.5% | 72.2% | 2142.4 | 136 | 100.0% |
| HOOD | B | 130 | 130 | 99.6% | 26.1% | 37.6% | 10.5% | 296.1 | 155 | 99.5% |
| META | B | 130 | 130 | 99.9% | 20.0% | 51.8% | 59.4% | 570.2 | 132 | 99.9% |
| MSFT | A | 130 | 130 | 99.8% | 22.6% | 44.1% | 30.0% | 304.4 | 82 | 99.7% |
| NET | C | 130 | 130 | 100.0% | 24.7% | 59.3% | 77.0% | 3657.2 | 76 | 99.9% |
| NVDA | A | 130 | 130 | 96.9% | 19.2% | 17.9% | 1.0% | 32.5 | 171 | 96.4% |
| SNOW | C | 130 | 130 | 99.9% | 26.3% | 51.5% | 55.6% | 1536.9 | 133 | 99.9% |
| TSLA | A | 130 | 130 | 99.9% | 16.8% | 33.8% | 7.1% | 83.6 | 232 | 99.8% |
| WMT | A | 130 | 130 | 96.8% | 30.3% | 40.5% | 21.2% | 352.0 | 63 | 96.5% |

## Bucket Fill Time Distribution

| Symbol | Tier | Fill P10 (ms) | Fill P50 (ms) | Fill P90 (ms) | Non-Regular % | Odd-Lot Days |
|--------|------|---------------|---------------|---------------|---------------|--------------|
| AMD | B | 16701 | 119914 | 434644 | 2.8% | 0 |
| CRWD | C | 17120 | 164861 | 585902 | 2.8% | 0 |
| HOOD | B | 28960 | 147923 | 518137 | 3.3% | 0 |
| META | B | 27270 | 183787 | 617665 | 3.5% | 0 |
| MSFT | A | 29824 | 316704 | 937388 | 4.0% | 0 |
| NET | C | 24034 | 355656 | 1220154 | 3.6% | 0 |
| NVDA | A | 27842 | 129771 | 351281 | 2.4% | 0 |
| SNOW | C | 18006 | 194785 | 694373 | 4.4% | 0 |
| TSLA | A | 26016 | 95952 | 260971 | 1.6% | 0 |
| WMT | A | 31819 | 419739 | 1110044 | 7.4% | 0 |

## Performance

| Symbol | Tier | Total Buckets | Classify (min) | Bucket (min) |
|--------|------|---------------|----------------|--------------|
| AMD | B | 25,184 | 1.4 | 0.0 |
| CRWD | C | 17,725 | 0.2 | 0.0 |
| HOOD | B | 20,119 | 0.8 | 0.0 |
| META | B | 17,196 | 0.9 | 0.0 |
| MSFT | A | 10,649 | 1.4 | 0.0 |
| NET | C | 9,832 | 0.1 | 0.0 |
| NVDA | A | 22,282 | 5.8 | 0.1 |
| SNOW | C | 17,308 | 0.3 | 0.0 |
| TSLA | A | 30,147 | 3.6 | 0.1 |
| WMT | A | 8,175 | 0.6 | 0.0 |

## Cross-Tier Quality Comparison

- **Tier A** (4 symbols): Quote match=98.3%, Stale=34.1%, Confidence=98.1%
- **Tier B** (3 symbols): Quote match=99.7%, Stale=42.2%, Confidence=99.7%
- **Tier C** (3 symbols): Quote match=100.0%, Stale=56.1%, Confidence=99.9%

---

## Quality Issues

- **WARNING**: AMD: tick rule fallback 23.7% > 20%
- **WARNING**: AMD: stale quote % 37.2% > 10%
- **WARNING**: CRWD: tick rule fallback 23.3% > 20%
- **WARNING**: CRWD: stale quote % 57.5% > 10%
- **WARNING**: HOOD: tick rule fallback 26.1% > 20%
- **WARNING**: HOOD: stale quote % 37.6% > 10%
- **WARNING**: META: tick rule fallback 20.0% > 20%
- **WARNING**: META: stale quote % 51.8% > 10%
- **WARNING**: MSFT: tick rule fallback 22.6% > 20%
- **WARNING**: MSFT: stale quote % 44.1% > 10%
- **WARNING**: NET: tick rule fallback 24.7% > 20%
- **WARNING**: NET: stale quote % 59.3% > 10%
- **WARNING**: NVDA: stale quote % 17.9% > 10%
- **WARNING**: SNOW: tick rule fallback 26.3% > 20%
- **WARNING**: SNOW: stale quote % 51.5% > 10%
- **WARNING**: TSLA: stale quote % 33.8% > 10%
- **WARNING**: WMT: tick rule fallback 30.3% > 20%
- **WARNING**: WMT: stale quote % 40.5% > 10%

---

**Gate**: Week 2 data quality report generated. Review issues before proceeding.

