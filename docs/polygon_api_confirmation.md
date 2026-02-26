# Polygon API Confirmation — Pre-Flight Checklist

**Date**: February 14, 2026
**Blueprint Reference**: `docs/phase_1_2_implementation_blueprint.md` v1.6-FINAL, Section 4 Pre-Flight

---

## 1. Plan Tier

| Item | Status | Detail |
|------|--------|--------|
| Current plan | **CONFIRMED** | **Stock Advanced** ($199/mo) — trades + quotes access available |
| Upgrade needed? | **NO** | Already on correct plan |

---

## 2. Historical Data Retention

| Item | Required | Confirmed | Detail |
|------|----------|-----------|--------|
| Historical trade retention | ≥ 130 trading days (~6 months) | **YES** | Polygon provides 20+ years of historical data on Advanced plan |
| Historical quote retention | Same (NBBO quotes) | **YES** | Same retention as trades on Advanced plan |

Polygon Advanced plan provides historical trades and quotes going back to 2003+. Our requirement of 130 trading days (~July 2025 - Jan 2026) is well within retention.

---

## 3. API Rate Limits

| Item | Required | Confirmed | Detail |
|------|----------|-----------|--------|
| Rate limits | Unlimited preferred | **YES** | Advanced plan: unlimited API calls |
| Per-request limit | 50,000 results/page | **YES** | v3 endpoints support `limit` up to 50,000 |
| Pagination | next_url based | **YES** | Existing `_fetch_paginated_v3()` already implements this |

Existing codebase (`PolygonRestConfig`) uses `rate_limit_calls=500` per second as a self-imposed throttle. This is conservative and safe.

---

## 4. Timestamp Fields

| Field | Available | Format | Detail |
|-------|-----------|--------|--------|
| `sip_timestamp` (trades) | **YES** | Int64 nanoseconds | SIP receipt time |
| `participant_timestamp` (trades) | **YES** | Int64 nanoseconds | Exchange-generated time |
| `trf_timestamp` (trades) | **YES** | Int64 nanoseconds | TRF receipt time |
| `sip_timestamp` (quotes) | **YES** | Int64 nanoseconds | SIP receipt time for NBBO |
| `participant_timestamp` (quotes) | **YES** | Int64 nanoseconds | Exchange-generated time |

**CRITICAL NOTE**: The existing `get_historical_trades()` and `get_historical_quotes()` methods in `polygon_rest.py` convert nanosecond timestamps to Python `datetime` objects via `_parse_event_timestamp()`. This **loses nanosecond precision** (Python datetime has microsecond resolution). The new `bulk_downloader.py` must preserve raw `Int64` nanosecond values for ClickHouse storage.

**Resolution**: The new downloader will use `_fetch_paginated_v3()` directly (which returns raw JSON dicts with integer timestamps) rather than the higher-level `get_historical_trades()`/`get_historical_quotes()` methods. This preserves full nanosecond precision.

---

## 5. Response Fields

### Trades (`/v3/trades/{ticker}`)

| Field | Type | Available | Needed for |
|-------|------|-----------|------------|
| `sip_timestamp` | int (ns) | YES | Primary timestamp (ClickHouse `Int64`) |
| `participant_timestamp` | int (ns) | YES | Exchange timestamp |
| `price` | float | YES | Trade price |
| `size` | int | YES | Trade size |
| `exchange` | int | YES | Exchange ID |
| `conditions` | array[int] | YES | Odd-lot detection, validation |
| `tape` | int | YES | Tape A/B/C |
| `id` | string | YES | Dedup (trade_id) |

### Quotes (`/v3/quotes/{ticker}`)

| Field | Type | Available | Needed for |
|-------|------|-----------|------------|
| `sip_timestamp` | int (ns) | YES | Primary timestamp |
| `bid_price` | float | YES | NBBO bid |
| `ask_price` | float | YES | NBBO ask |
| `bid_size` | int | YES | Quoted depth at best bid |
| `ask_size` | int | YES | Quoted depth at best ask |
| `bid_exchange` | int | YES | Bid exchange ID |
| `ask_exchange` | int | YES | Ask exchange ID |
| `conditions` | array[int] | YES | Quote conditions |
| `sequence_number` | int | YES | Ordering verification |

All blueprint-required fields are present in Polygon v3 response.

---

## 6. Condition Codes

| Item | Status | Detail |
|------|--------|--------|
| Trade condition codes | **YES** | Array of integers per trade. Needed for odd-lot filtering, irregular trade detection |
| Condition code reference API | **YES** | `/v3/reference/conditions` endpoint available for mapping codes to descriptions |

---

## 7. Quote Conflation

| Item | Status | Detail |
|------|--------|--------|
| Quote conflation | **REQUIRES WEEK 0 VERIFICATION** | Polygon delivers SIP-level NBBO updates. SIP may conflate rapid quote changes. Must verify in probe by checking timestamp clustering patterns |

**Week 0 probe must verify**:
- Distribution of (trade_timestamp - nearest_quote_timestamp) deltas
- Presence of negative deltas
- Whether quote timestamps cluster at millisecond boundaries
- If millisecond clustering observed → adjust `quote_age_ns` thresholds

---

## 8. Backfill Bandwidth Estimate

| Metric | Estimate | Detail |
|--------|----------|--------|
| Trades per symbol-day (blended) | ~250k avg | Tier A: 300-800k, Tier B: 100-300k, Tier C: 50-100k |
| Quotes per symbol-day (blended) | ~1.5M avg | Tier A: 2-5M, Tier B: 800k-2M, Tier C: 300-800k |
| Pages per symbol-day (trades) | ~5-16 pages | At 50k results/page |
| Pages per symbol-day (quotes) | ~6-100 pages | Highly variable by tier |
| Time per symbol-day | ~30 seconds | Including rate limiting overhead |
| Total for 10 sym × 130 days | ~1,300 symbol-days | ~10.8 hours serial, ~2-2.5 hours at 5 concurrent |

---

## 9. ClickHouse Storage Audit

**Existing usage**:
```
Used disk:      25.32 GB
Total capacity: 494.38 GB
Free space:     354.86 GB
```

**Existing data**:
- Table: `polygon_data.ticks` — 956M rows, 25.32 GB (1-min OHLCV bars)
- Date range: 2023-01-03 to 2025-06-30
- Unique tickers: 15,539
- Other tables: negligible (<1 KB each, materialized views)

**Storage allocation for falsification dataset**:
```
Available:    354.86 GB (free space)
Allocated:    212.92 GB (60% of available — hard ceiling)
Buffer:        70.97 GB (20% for compaction/merge)
Emergency:     70.97 GB (20% headroom)
```

**Verdict**: Allocated ceiling of ~213 GB exceeds the 220 GB target. Storage is **SAFE** for 10 symbols × 130 days (estimated 140-150 GB).

The 220 GB target and 250 GB kill-switch are well within available capacity. No reduction in symbols or period needed.

---

## 10. Existing Codebase Integration Points

| Component | Reusable? | Notes |
|-----------|-----------|-------|
| `_fetch_paginated_v3()` | **YES** | Returns raw JSON dicts — preserves nanosecond timestamps. Use this directly. |
| `_rate_limit()` | **YES** | Token bucket rate limiter. Self-imposed 500 calls/sec. |
| `_event_timestamp_to_ns()` | **YES** | Converts datetime → nanoseconds for query params. |
| `get_historical_trades()` | **NO** | Loses nanosecond precision by converting to datetime. Use `_fetch_paginated_v3()` instead. |
| `get_historical_quotes()` | **NO** | Same issue — loses nanosecond precision. |
| `ClickHouseDataManager._execute_query()` | **YES** | HTTP POST to ClickHouse. ArrowStream/TSV formats. |
| `PolygonRestConfig` | **YES** | API key, rate limits, base URL. |
| `MarketCalendar` / `filter_bars_to_rth()` | **YES** | RTH filtering for trade/quote data. |

---

## 11. Pre-Flight Verdict

| Check | Status |
|-------|--------|
| Plan tier confirmed (Stock Advanced) | **PASS** (confirmed by user 2026-02-14) |
| Historical retention sufficient | **PASS** (20+ years) |
| API rate limits acceptable | **PASS** (unlimited on Advanced) |
| Nanosecond timestamps available | **PASS** (all sip/participant/trf) |
| All required fields present | **PASS** |
| Condition codes available | **PASS** |
| Quote conflation | **DEFERRED TO WEEK 0 PROBE** |
| ClickHouse storage | **PASS** (213 GB allocated, 140-150 GB projected) |
| Existing codebase reuse path clear | **PASS** |

**All checks PASS.** No blocking items. Pre-Flight complete.

---

**Next step**: Proceed to Step 1 (Scaffolding) — `constants.py`, `types.py`, DDL, YAML configs, module structure.
