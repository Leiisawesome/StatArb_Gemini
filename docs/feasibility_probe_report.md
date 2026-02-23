# Feasibility Probe Report (Week 0)

**Date**: 2026-02-20 15:01
**Constants Version**: v1.6-FINAL
**Elapsed**: 6.7 minutes
**Verdict**: **ALL PASS** — greenlight bulk ingestion

---

## Section A — Polygon Data Quality

| Symbol | Tier | Date | Trades | Quotes | Confidence | Tick Rule % | Stale Quote % | Mean Age (ms) |
|--------|------|------|--------|--------|------------|-------------|---------------|---------------|
| AAPL | A | 2026-02-11 | 773,169 | 760,252 | 99.4% | 23.1% | 31.0% | 98.5 |
| AAPL | A | 2026-02-12 | 1,006,345 | 1,121,987 | 99.0% | 25.2% | 25.7% | 57.8 |
| AAPL | A | 2026-02-13 | 735,434 | 602,658 | 99.5% | 22.6% | 37.8% | 131.7 |
| AMD | B | 2026-02-11 | 425,888 | 373,105 | 99.9% | 23.0% | 38.0% | 168.5 |
| AMD | B | 2026-02-12 | 403,015 | 384,426 | 99.9% | 22.9% | 39.5% | 168.4 |
| AMD | B | 2026-02-13 | 323,116 | 351,224 | 99.9% | 22.1% | 39.6% | 185.7 |
| ROKU | C | 2026-02-11 | 55,819 | 30,490 | 99.9% | 23.1% | 41.1% | 1550.7 |
| ROKU | C | 2026-02-12 | 133,142 | 66,389 | 99.9% | 24.1% | 37.6% | 925.0 |
| ROKU | C | 2026-02-13 | 182,779 | 89,406 | 99.9% | 21.0% | 35.6% | 496.1 |

### Timestamp Alignment

| Symbol | Date | δ P10 (μs) | δ P50 (μs) | δ P90 (μs) | δ P99 (μs) | Neg. deltas | ms clustering |
|--------|------|------------|------------|------------|------------|-------------|---------------|
| AAPL | 2026-02-11 | 3 | 1916 | 293047 | 1162711 | 0 | NO |
| AAPL | 2026-02-12 | 2 | 932 | 173295 | 652270 | 0 | NO |
| AAPL | 2026-02-13 | 4 | 9476 | 392847 | 1353566 | 0 | NO |
| AMD | 2026-02-11 | 6 | 7878 | 510553 | 1855849 | 0 | NO |
| AMD | 2026-02-12 | 7 | 11895 | 510206 | 1796512 | 0 | NO |
| AMD | 2026-02-13 | 6 | 11954 | 549214 | 2076625 | 0 | NO |
| ROKU | 2026-02-11 | 3 | 2601 | 4905902 | 18971441 | 0 | NO |
| ROKU | 2026-02-12 | 3 | 1502 | 2910800 | 12376026 | 0 | NO |
| ROKU | 2026-02-13 | 4 | 1200 | 1524407 | 6485907 | 0 | NO |

**Timestamp alignment verdict**: USABLE
**Millisecond clustering**: NO — nanosecond precision confirmed

---

## Section B — ClickHouse Performance

| Metric | Value |
|--------|-------|
| Insert throughput (trades) | 10,381 rows/sec |
| Insert throughput (quotes) | 9,715 rows/sec |
| Single symbol-day query | 12 ms |
| Compression ratio | 8.3:1 |

### Storage per symbol-day

| Symbol | Date | Trades | Quotes | Disk (MB) |
|--------|------|--------|--------|-----------|
| AAPL | 2026-02-11 | 773,169 | 760,252 | 10.0 |
| AAPL | 2026-02-12 | 1,006,345 | 1,121,987 | 10.0 |
| AAPL | 2026-02-13 | 735,434 | 602,658 | 10.0 |
| AMD | 2026-02-11 | 425,888 | 373,105 | 10.0 |
| AMD | 2026-02-12 | 403,015 | 384,426 | 10.0 |
| AMD | 2026-02-13 | 323,116 | 351,224 | 10.0 |
| ROKU | 2026-02-11 | 55,819 | 30,490 | 10.0 |
| ROKU | 2026-02-12 | 133,142 | 66,389 | 10.0 |
| ROKU | 2026-02-13 | 182,779 | 89,406 | 10.0 |

### Section B.2 — Storage Projection (MANDATORY)

| Metric | Value |
|--------|-------|
| Avg MB per symbol-day | 10.0 |
| Target symbols | 10 |
| Target trading days | 130 |
| **Projected total** | **12.7 GB** |
| Target ceiling | 220 GB |
| Kill-switch | 250 GB |
| **Verdict** | **WITHIN TARGET** |

---

## Section C — Pipeline Validation

| Symbol | Date | Buckets | Target ~200 | Classify (s) | Bucket (s) | RSS (MB) |
|--------|------|---------|-------------|--------------|------------|----------|
| AAPL | 2026-02-11 | 159 | OUTLIER | 0.9 | 0.02 | 1107 |
| AAPL | 2026-02-12 | 143 | OUTLIER | 1.2 | 0.03 | 1421 |
| AAPL | 2026-02-13 | 144 | OUTLIER | 0.9 | 0.02 | 1421 |
| AMD | 2026-02-11 | 177 | OK | 0.5 | 0.02 | 1421 |
| AMD | 2026-02-12 | 164 | OK | 0.5 | 0.01 | 1421 |
| AMD | 2026-02-13 | 176 | OK | 0.4 | 0.01 | 1421 |
| ROKU | 2026-02-11 | 163 | OK | 0.1 | 0.01 | 1421 |
| ROKU | 2026-02-12 | 184 | OK | 0.2 | 0.02 | 1421 |
| ROKU | 2026-02-13 | 186 | OK | 0.2 | 0.01 | 1421 |

**Deterministic replay (SHA256)**: PASS
**Tier 1 diagnostic code paths**: ALL EXECUTE

### Blocking Issues

**NONE** — pipeline is ready for bulk ingestion.

---

## Hash Audit Trail

| Symbol | Date | Trades Hash | Quotes Hash | Buckets Hash |
|--------|------|-------------|-------------|--------------|
| AAPL | 2026-02-11 | `5abf0c4cb5fc...` | `78c818ac783e...` | `f9cc000cb9de...` |
| AAPL | 2026-02-12 | `c19895ea5dbc...` | `2e71b0ba244a...` | `31dfee2d4db6...` |
| AAPL | 2026-02-13 | `dd343865054e...` | `414e89656e89...` | `6427ff321761...` |
| AMD | 2026-02-11 | `67c14fcf868f...` | `84bbf26b237a...` | `d19c6554693f...` |
| AMD | 2026-02-12 | `1861c0e42656...` | `857d8b223fda...` | `06ae87fdef81...` |
| AMD | 2026-02-13 | `d0edb4e82dc2...` | `ff4ca880e4cf...` | `4d22eb5274e2...` |
| ROKU | 2026-02-11 | `57f179c2677e...` | `1ebc2338dfee...` | `6a0c53921eba...` |
| ROKU | 2026-02-12 | `de4d805550da...` | `a46f85f52fe2...` | `864b239837bd...` |
| ROKU | 2026-02-13 | `d4ac92831973...` | `38b1d85cd033...` | `d649df0c0156...` |

---

**Next step**: Proceed to Week 1 — Universe Freeze + Bulk Ingestion
