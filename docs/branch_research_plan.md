# Branch Research Plan — Post Event-Transition Discovery

**Status**: ACTIVE  
**Constants**: v1.6-FINAL  
**Date**: 2026-02-21  
**Prerequisite**: Event-transition experiment passed 3/4 gates (G1-G3)

---

## Context

Three experiments completed on 178,617 volume-clock buckets (10 symbols × 130 days):

| Experiment | Result | Key Finding |
|---|---|---|
| H1: Bucket continuation | **TERMINATE** (0/4 gates) | Gross edge negative. Imbalance predicts reversal at bucket scale. |
| H1-R: Bucket reversal | **TERMINATE** (0/4 gates) | Hit rate 49%. Cost scales with extremity. Net ≈ -3.5 bps at every τ. |
| H2: Event transition | **PROCEED** (3/4 gates) | Spread widens +6 bps at 1s (p<0.0001). Midpoint continues 1-5s. Recovery corr=0.35. |

**Structural insight**: Imbalance is a **liquidity shock indicator**, not a return predictor. The signal lives in spread dynamics at the 1-30 second timescale, not in bucketed directional returns.

---

## Branch A — Latency-Sensitive Continuation (Secondary / Ceiling Check)

**Per external quant**: This is economically irrelevant without colocation/direct feed.
Time-boxed to 1 day max. Strictly informational. No additional modeling complexity.

### Hypothesis
After extreme imbalance, midpoint continues in the imbalance direction for 1-5 seconds. An aggressive entry within 100-300ms can capture 1-2 bps of continuation before the spread fully widens.

### What We Already Know
- Midpoint continuation at 1s: corr=0.18, hit rate=59% (reversal hit=41%)
- But spread widens +6 bps simultaneously
- Continuation magnitude ≈ 2 bps; spread widening ≈ 6 bps
- Net: crossing the spread costs more than the continuation delivers

### Purpose
Ceiling check only. Determine if the continuation opportunity is physically possible at any latency, and what latency would be required. This informs infrastructure decisions, nothing more.

### Experiment Design
- Tier A only (MSFT, NVDA) — tightest spreads, least distortion
- 200 extreme events per symbol
- For each event, query raw quotes from ClickHouse
- Sweep latencies: [50, 100, 200, 500, 1000, 2000, 5000ms]
- At each latency: continuation bps vs half-spread at that instant
- Net = continuation - half_spread_at_entry
- Viable = net > 0 AND hit rate > 52%

### Kill Criteria
- If net > 0 requires latency < 50ms → **infeasible** (no colocation)
- If net > 0 only at <200ms with hit rate <55% → **not robust**
- If net > 0 at ≥500ms with hit rate >55% → **viable for non-HFT** (unlikely)
- Regardless of outcome, does not change Branch B priority

---

## Branch B — Pessimistic Liquidity Provision (Primary / Decisive)

**Per external quant**: This is the ONLY path aligned with our infrastructure.
Must include queue modeling. Must be pessimistic. Must be Tier A first.

### Hypothesis
After extreme imbalance, the spread widens beyond equilibrium. The recovery (spread compression) is predictable from imbalance magnitude (corr=0.35). A passive liquidity provider can:
1. Post limit orders at the widened spread level
2. Capture spread compression as the market normalizes
3. Exit when spread returns to baseline

This is **not directional alpha**. This is **liquidity regime alpha**.

### What We Already Know
- Spread widens +6 bps at 1s, decays to baseline by 30s
- Recovery time: median=35ms but mean=10,094ms (heavy right tail)
- Recovery corr with |imbalance| = 0.35 → predictable
- Depth result (G4) showed quotes refreshing rapidly → not a structural crisis, just temporary adjustment

### Pessimistic Assumptions (per quant review)

1. **100ms order entry delay**: We do not act until 100ms after event detection. All modeling starts from this delayed timestamp.

2. **Last in visible queue**: When we post at widened best bid/ask, we assume all visible size at that level is ahead of us. We are filled ONLY after cumulative trade volume through our level exceeds the queue_ahead size. This biases against us because:
   - Hidden liquidity is not modeled (real queue may be deeper)
   - Our fill model ignores dark pool prints that don't count

3. **Three-way exit** (first triggered wins):
   - **Spread normalization**: exit when spread ≤ 105% of pre-event baseline
   - **Timeout**: hard exit at 30 seconds regardless
   - **Stop-loss**: exit if midpoint moves against position by > 3 bps
   
4. **Exit at midpoint**: Conservative assumption that we must cross to exit (not passive). Actual implementation could be better, but we model the worst case.

5. **Tier A only first**: MSFT + NVDA. Tightest spreads, deepest books. If it fails here, it fails everywhere. Tier B/C expansion ONLY after Tier A passes.

6. **Regime conditioning**: Exclude obvious noise regimes (first/last 15 min RTH proxied by spread volatility days).

### Gate Criteria (Updated)
- **B1**: Fill probability > 30% (if we never get filled, strategy is theoretical)
- **B2**: Mean spread capture > 1 bps
- **B3**: Hit rate > 55%
- **B4**: Net edge × daily event count > 0.5 bps/day portfolio-level
- **B5**: Daily Sharpe equivalent ≥ 0.8 (annualized). Liquidity provision dies from tail risk, not mean. (Added per quant)

### Kill Criteria (Unchanged)
- Fill probability < 15% → strategy infeasible
- Adverse selection > spread capture in > 60% of filled events → picked off
- Net edge < 0 → signal descriptive, not tradable
- Only works in < 1 symbol → not viable

### Queue Modeling Detail
At each event:
1. Record visible size at our posting level at entry_time (event_end + 100ms)
2. Walk forward through raw trades
3. Accumulate volume of trades at or through our price level
4. We are filled when cum_volume > queue_ahead
5. Fill time recorded for hold-time calculation

This is measurable from our existing trade + quote data.

### Implementation
- Scope: Tier A only (MSFT, NVDA) — 300 extreme events per symbol
- Data: Raw trades AND quotes from ClickHouse (both already ingested)
- Concurrent ClickHouse queries per event (quotes + trades, 40s window each)
- Full P&L computed per simulated trade

---

## Execution Order (Revised per Quant)

```
Step 1: Branch A ceiling check (fast, Tier A only, MSFT+NVDA)
        → Informational only. Time-boxed 1 hour.
        → Sets theoretical ceiling. Does NOT inform Branch B decision.

Step 2: Branch B — Tier A pessimistic simulation (MSFT+NVDA)
        → Decisive test. Pessimistic queue model.
        → If ALL 5 gates pass → proceed to Tier B/C expansion
        → If <3 gates pass → TERMINATE imbalance program

Step 3: Decision
        → If B passes all 5 gates → design event-driven liquidity strategy
        → If B passes 3-4 gates → targeted investigation of failing gates
        → If B fails → conclude: SIP-derived microstructure is descriptive
           but economically unexploitable. Research program ends.
```

**No external review until Branch B result is in.**

---

## What We Must NOT Do

- Do not expand the universe
- Do not add more days
- Do not relax gate criteria
- Do not conflate spread widening with directional alpha
- Do not assume fill probability is 100%
- Do not ignore adverse selection
- Do not submit for external review until both branches are tested

---

## Infrastructure Reality Check

| Capability | Current State | Required for A | Required for B |
|---|---|---|---|
| Data resolution | SIP tick+quote (nanosecond) | ✅ Sufficient | ✅ Sufficient |
| Execution latency | ~500ms (REST API, Python) | ❌ Too slow | ⚠️ Marginal |
| Order types | Market + Limit via IBKR | ❌ No smart routing | ✅ Limit orders work |
| Colocation | None | ❌ Required for <100ms | ✅ Not required |
| Direct feeds | None (SIP only) | ❌ Degraded signal | ✅ SIP sufficient for 5-30s horizon |

**Branch B is infrastructure-compatible. Branch A likely is not.**

---

## Anti-Rationalization Discipline

The event transition result is statistically real but economically unproven. The spread widening is a *description* of what happens; it is not yet an *exploitable* phenomenon. The difference between "we can measure it" and "we can trade it" is the fill probability × adverse selection test.

If Branch B fails, the honest conclusion is: **SIP-derived imbalance data at any resolution provides diagnostic but not tradable information for our infrastructure class.**

That would be a legitimate and valuable conclusion.
