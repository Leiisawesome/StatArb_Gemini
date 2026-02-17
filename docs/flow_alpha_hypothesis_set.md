# Flow Alpha Hypothesis Set (FAHS v1.0)

**Purpose**: Define the precise microstructure hypotheses that the new flow alpha module is permitted to express. This is not implementation. It is the boundary specification for what the alpha is allowed to test, trade on, and exit from.

**Status**: FINAL v1.5 — Hypothesis design phase SEALED. Incorporating Round 1 (structural) + Round 2 (economic) + Round 3 (empirical feasibility) + Round 3 Final (reflexivity, rejection criteria, strategic intent) + Final Audit (statistical precision, economic realism, operational fragility) critiques. All gates frozen.

**Relationship to ADS v3.1**: The ADS specification defines constraints (SMS, ERAR, regime, sizing, exits, cooldown). This document defines the *edge hypotheses* that the ADS gates will govern. ADS tells you when to reject a trade. This document tells you why you considered it in the first place.

**Data Contract**: Polygon.io Stock Advanced — SIP consolidated tick trades + NBBO quotes. No native aggressor flags. No full depth of book. No options surface. No order-level data.

---

## 1. THE CAUSAL CHAIN REQUIREMENT

Every hypothesis in this document must complete this transmission chain:

```
Participant Constraint        (who is forced to trade, and why)
  → Directional Order Flow    (observable in signed trade data)
    → Liquidity Imbalance     (observable in spread/depth dynamics)
      → Price Acceleration    (measurable in tick-level returns)
        → Persistence Window  (duration the edge survives, in minutes)
```

If any link cannot be specified with observable data from the Polygon Stock Advanced contract, the hypothesis is not permitted.

If the persistence window is shorter than the minimum holding period required to cover transaction costs, the hypothesis is not tradeable.

**Critical constraint (post-Round-1 review)**: The persistence window is NOT assumed. It is measured empirically in Phase 2 of the falsification protocol via the signed imbalance autocorrelation decay curve. The 10-60 minute range stated in hypothesis observable chains is a working hypothesis, not a given. Modern adaptive execution algos (TWAP, Implementation Shortfall) and fast liquidity provider reversion may compress exploitable persistence to 3-10 minutes in highly liquid names. If the measured half-life of cumulative_imbalance autocorrelation is shorter than the cost-covering holding period, the hypothesis is not viable on that symbol — regardless of statistical significance at longer horizons. The holding horizon is DATA-DRIVEN, not pre-specified.

**What is the leading variable? (post-Round-2 review)**: The edge mechanism is NOT prediction of a future event. It is detection of an ONGOING event whose completion has not yet been fully priced. Specifically:

1. A mandate-driven participant creates sustained one-directional flow across multiple volume buckets.
2. We detect this after K buckets (there IS a detection lag — we are not first).
3. The prediction: the mandate is NOT YET COMPLETE, so flow WILL CONTINUE beyond our detection point.
4. Price has not fully reflected the cumulative imbalance because price impact is gradual (Kyle 1985 — partial price discovery; Bouchaud et al. 2004 — concave impact function).

The "leading variable" is `cumulative_imbalance` — not because it precedes the event, but because it measures an event-in-progress whose price impact is incomplete. The testable prediction is: `price_impact_per_volume` (price change per unit of signed volume) is < 1.0 during the detection window, meaning residual unpriced imbalance exists. If impact is already fully reflected at the time of detection, there is no edge. Phase 2b validates this.

**Forced participant identification is NOT required**: The hypotheses detect the FLOW SIGNATURE of any price-insensitive participant, without identifying which type (gamma hedger, VWAP algo, index rebalancer, liquidator). This is deliberate. The signal is the aggregate flow pattern in signed trade data. Identifying the specific participant would require data we don't have (options OI for gamma, benchmark schedules for VWAP, basket compositions for ETFs) and would create fragility if the participant mix changes. If the flow pattern is present and persistent, the source is irrelevant to the trade.

---

## 2. OBSERVABLE PRIMITIVES

These are the atomic measurements available from tick + NBBO quote data. All hypotheses must be expressed in terms of these primitives — not in terms of derived indicators, smoothed composites, or bar-aggregated proxies.

### 2.1 From Trade Data

| Primitive | Definition | Derivation |
|-----------|-----------|------------|
| `trade_price` | Execution price of each trade | Direct from SIP |
| `trade_size` | Share quantity per trade | Direct from SIP |
| `trade_exchange` | Venue of execution | Direct from SIP |
| `trade_timestamp` | Nanosecond SIP timestamp | Direct from SIP |
| `trade_conditions` | Condition codes (regular, crossing, etc.) | Direct from SIP |
| `trade_sign` | Inferred aggressor direction (+1 buy, -1 sell, 0 indeterminate) | Lee-Ready classification (see below) |

**Lee-Ready Classification Rule**:
1. If `trade_price > midpoint` → `trade_sign = +1` (buyer-initiated)
2. If `trade_price < midpoint` → `trade_sign = -1` (seller-initiated)
3. If `trade_price == midpoint` → apply **tick test**: compare to previous different trade price. If current > previous → +1, if current < previous → -1, otherwise → 0 (indeterminate).

Trades classified as indeterminate (0) are excluded from signed volume calculations. This is conservative — it reduces sample size but avoids injecting noise from the tick test's lowest-accuracy regime. Approximately 20-30% of trades fall at the midpoint; of these, the tick test correctly classifies ~60-75% (Chakrabarty et al. 2007). Overall Lee-Ready accuracy: ~85-93% for non-midpoint trades, ~60-75% for midpoint trades.

**Important**: When computing `flow_imbalance = signed_volume / total_volume`, `total_volume` includes ONLY trades with `trade_sign ∈ {-1, +1}`. Indeterminate trades are excluded from both numerator and denominator to avoid biasing imbalance toward zero.

**Partial calibration (NOT ground truth)**: Polygon trade conditions include Intermarket Sweep Order (ISO) flags. ISO trades are by definition aggressive routing, but they do NOT represent all aggressive flow — they are a biased subset. ISO flags cannot validate the claimed 85% overall accuracy. Instead, Lee-Ready quality is assessed indirectly via three-way comparison protocol (Phase 2):
1. Tick-rule only (baseline)
2. Lee-Ready with midpoint exclusion (current default)
3. Lee-Ready with probabilistic midpoint assignment (50/50 buy/sell weight for midpoint trades)

Evaluate each via correlation between `signed_volume` and 1-minute forward returns. The method with highest predictive correlation is the most operationally accurate (revealed preference — we measure what matters for the alpha, not classification purity).

**Midpoint clustering risk (post-Round-1 review)**: Midpoint prints are increasing due to internalization and dark pool midpoint pegging. Their exclusion changes the imbalance distribution nonlinearly. If midpoint trades cluster during institutional crossing regimes, we are systematically dropping flow from potentially the most informed participants. Phase 2 must measure: `midpoint_trade_fraction` by volatility quintile and by time-of-day. If midpoint fraction > 40% in any regime, the probabilistic assignment variant (method 3 above) must be tested as the default.

**Noise injection test (REQUIRED in Phase 2)**: Inject 10%, 15%, 20% random misclassification into `trade_sign`. Recompute H1 cumulative_imbalance signal. If the t-stat drops below 2.0 at 15% noise injection, the edge is classification-fragile. This is a program-level gate: if the signal cannot tolerate realistic classification error, no hypothesis testing proceeds.

### 2.2 From Quote Data

| Primitive | Definition | Derivation |
|-----------|-----------|------------|
| `bid_price` | National best bid | Direct from NBBO |
| `ask_price` | National best ask | Direct from NBBO |
| `bid_size` | Shares available at best bid | Direct from NBBO (in shares, post Nov 2025 MDI) |
| `ask_size` | Shares available at best ask | Direct from NBBO |
| `midpoint` | `(bid + ask) / 2` | Computed |
| `spread` | `ask - bid` | Computed |
| `spread_bps` | `spread / midpoint * 10000` | Computed |
| `quote_timestamp` | Nanosecond SIP timestamp | Direct from NBBO |

### 2.3 Derived Flow Metrics (permitted)

These are minimal, justified derivations from the primitives. Each must be computed in **volume-clock** (per N shares traded), not time-clock, unless explicitly noted.

| Metric | Definition | Clock |
|--------|-----------|-------|
| `signed_volume` | `Σ(trade_sign × trade_size)` per volume bucket | Volume |
| `flow_imbalance` | `signed_volume / total_volume` per bucket, range [-1, +1] | Volume |
| `cumulative_imbalance` | Running sum of `signed_volume` over K buckets | Volume |
| `trade_arrival_rate` | Trades per second (Poisson intensity estimate) | Time (exception) |
| `vpin` | `Σ|buy_volume - sell_volume| / (2 × bucket_volume)` over N buckets | Volume |
| `spread_ma` | Exponential moving average of `spread_bps` over M quote updates | Quote event |
| `depth_imbalance` | `(bid_size - ask_size) / (bid_size + ask_size)` at NBBO | Quote event |
| `quote_intensity` | NBBO updates per second | Time (exception) |
| `effective_spread` | `2 × |trade_price - midpoint_at_trade_time|` in bps | Per trade |
| `price_impact_per_volume` | `Δmidpoint / signed_volume` per bucket (bps per unit imbalance) | Volume |

`price_impact_per_volume` is the impact elasticity: how much price moves per unit of directional flow, measurable from tick data without L2 depth. This directly addresses the "state transition" detection problem.

**Critical interpretive note (post-Round-3 review)**: Impact elasticity is NOT a simple directional signal. It is ambiguous between two states:
- **Low/stable elasticity during sustained imbalance** = price absorbing flow, mandate ongoing, room for continuation → FAVORABLE for H1 entry
- **Rising/spiking elasticity during sustained imbalance** = liquidity thinning, potentially TERMINAL phase → AMBIGUOUS for entry. Could mean either (a) cascade beginning (H2 — more flow coming) or (b) exhaustion (mandate nearly complete, liquidity providers retreating ahead of reversal)

Phase 3 must include a conditional event study to determine which interpretation dominates empirically: separate imbalance events into continuation vs reversion, then compare the impact elasticity distribution at entry for each group. If the distributions are not statistically separable, impact elasticity is not informative about direction — only about volatility.

**Self-impact reflexivity (post-Round-3 final review)**: Even at 0.25-0.5% rolling 3-min participation, in Tier B/C during thin windows our fills may meaningfully affect Δmidpoint. This contaminates the elasticity statistic used for entry gating and ex-post classification. In live trading, compute:

`impact_ex_self = Δmidpoint / (signed_volume - our_signed_fills)`

In backtesting, simulate self-impact by adding our hypothetical order to each bucket's volume and recomputing elasticity. If the adjusted value differs by >10% from the raw value, the trade is flagged as self-impactful and excluded from elasticity calibration. This prevents inflated backtest continuation probabilities from contaminating live parameter estimates.

**Volume Bucket Sizing**: Volume buckets are sized structurally per-symbol, not optimized. Target: each bucket fills in approximately 1-3 minutes on average, so that 5-10 buckets fit within the detection window. Formula: `bucket_size = ADV / target_buckets_per_day` where `target_buckets_per_day ≈ 200`. For TSLA (~100M shares/day ADV), this is ~500,000 shares per bucket (~2 min average fill). For a lower-volume stock (5M shares/day ADV), ~25,000 shares per bucket. Bucket size is recalibrated weekly using trailing 20-day ADV. This is a structural parameter — it is NOT tuned for performance.

**Bucket stationarity diagnostics (REQUIRED in Phase 2, post-Round-1 review)**:
The intraday U-shape volume curve means fixed bucket_size produces highly non-uniform fill times: seconds near open/close, minutes during midday, sub-second during news shocks. Phase 2 must measure:
1. Distribution of bucket fill durations (in wall-clock seconds). Report coefficient of variation (CV).
2. If CV > 2.0: test time-of-day-adjusted bucketing (use trailing 5-day ADV per 30-min window instead of daily ADV). This respects the U-shape without introducing optimization.
3. Autocorrelation of `flow_imbalance` across consecutive buckets — verify no artificial structure from non-uniform fill times.
4. Heteroskedasticity test (Breusch-Pagan) on `flow_imbalance` per bucket. If heteroskedastic, normalize via time-of-day empirical CDF (not rolling z-score, per Prohibition #1).
5. When bucket duration compresses to < 5 seconds during events, report persistence in BOTH bucket-time and wall-clock-time. Falsification tests must use **wall-clock-time persistence** (costs and holding periods are in wall-clock time, not bucket-time).

### 2.4 What Is NOT an Observable Primitive

The following are explicitly **not available** and must not be assumed, proxied, or fabricated:

- Full depth of book (levels 2-10+)
- True aggressor flags (Lee-Ready is an inference, not ground truth)
- Queue position or queue depletion rate
- Hidden/iceberg order volume
- Order cancellation rate
- Gamma exposure of options market makers
- ETF creation/redemption basket flow
- Dark pool routing intent (TRF prints visible, but intent is not)

If a hypothesis requires any of the above to be valid, it is not permitted under this data contract.

---

## 3. HYPOTHESIS SET

### H1: Sustained Directional Execution Pressure

**Participant Constraint**: A price-insensitive participant (institutional VWAP/TWAP algorithm, index rebalancer, margin-forced liquidator) is executing a mandate larger than what can be completed in a single burst. Their remaining order creates continued directional pressure.

**Observable Chain**:
```
Mandate-driven participant
  → Sustained one-sided trade_sign over K volume buckets
    → cumulative_imbalance significantly deviates from zero
      → midpoint drifts in imbalance direction
        → Persistence: until mandate completes (typically 10-60 minutes)
```

**Entry Signal**:
- `|cumulative_imbalance|` over K consecutive volume buckets exceeds threshold T
- `flow_imbalance` in most recent bucket is aligned with cumulative direction
- `spread_bps` is not expanding (liquidity absorbing, not fleeing)

**Entry Side**: Direction of cumulative_imbalance.

**Exit Triggers**:
1. **Flow dissipation**: `|flow_imbalance|` in most recent L buckets drops below neutral threshold
2. **Counter-flow**: `flow_imbalance` reverses sign for M consecutive buckets
3. **Thesis invalidation stop**: Price reverses beyond N × current_spread against entry (tight)
4. **Time circuit-breaker**: Maximum holding period reached

**No take-profit target.** Position held as long as flow persists.

**Falsification Criteria**:
- Null hypothesis: Forward returns at the empirically-determined persistence horizon (from Phase 2 decay curve) conditional on `|cumulative_imbalance| > T` are not statistically different from zero.
- Test: One-sided t-test with Newey-West standard errors (autocorrelation-robust). Minimum 200 independent events (events separated by at least the target holding period to avoid overlapping return windows).
- Reject hypothesis if p > 0.05 or if mean return < 2× estimated round-trip cost (using `effective_spread` at entry, not quoted spread).

**Impact elasticity conditional study (REQUIRED in Phase 3, post-Round-3 review)**: The impact elasticity distribution must be measured conditional on event outcome:
1. Align time at imbalance detection (cumulative_imbalance crossing threshold T).
2. Classify events by outcome: continuation (flow persists ≥ X additional buckets) vs reversion (flow reverses within Y buckets).
3. For each group, compute the distribution of `price_impact_per_volume` at the time of detection.
4. Plot forward returns conditional on impact elasticity percentile at entry.
5. Plot continuation probability as a function of elasticity decile.
6. **If the continuation and reversion elasticity distributions are not statistically separable (Wilcoxon p > 0.05)**: impact elasticity is not informative for entry timing. H1 proceeds without it; H2 is degraded.
7. **If LOW elasticity predicts continuation and HIGH elasticity predicts reversion**: H1 entry should PREFER low/stable elasticity (confirming "mandate still absorbing"). High elasticity should DISQUALIFY entry (exhaustion risk). This inverts the naive interpretation.

**Economic viability test (post-Round-1 review)**: The most likely failure mode is "high t-stat, low net edge after costs." Phase 3 must report the Pareto frontier of threshold T vs {event frequency, net edge per event}. The primary economic metric is **daily expected PnL** = frequency × net_edge_per_trade, not per-trade statistics alone. A rare but strong signal (T = high, frequency = 0.5/day, edge = 30 bps) may be more valuable than a frequent but thin signal (T = low, frequency = 5/day, edge = 3 bps). Report the full frontier and let the economic test adjudicate. Additionally, test across liquidity tiers: mega-caps (top-10 by dollar volume) face the most HFT competition and fastest reversion; stocks ranked 50-200 may offer materially better persistence. Symbol selection is part of the edge.

---

### H2: Liquidity-Fragility Amplified Flow

**Participant Constraint**: When aggressive flow encounters thinning liquidity (market makers stepping back, spread widening), each trade moves price further. This triggers stop-loss orders from other participants — creating forced secondary flow in the same direction (cascade).

**Observable Chain**:
```
Initial aggressive flow
  → Liquidity providers widen spread / reduce depth
    → spread_bps increases AND depth_imbalance shifts against passive side
      → Price accelerates (move per unit volume increases)
        → Stop cascades trigger (detectable as sudden burst of same-direction trades)
          → Persistence: until new liquidity arrives or stops exhausted (5-30 minutes)
```

**Entry Signal**:
- `flow_imbalance` directionally significant AND
- `spread_bps` expansion rate is elevated OR `price_impact_per_volume` is rising (either indicator detects liquidity thinning; `price_impact_per_volume` is the more direct measure — it answers "is each unit of flow moving price further?")

**Optional confirming indicators** (not required for entry): `depth_imbalance` shifts against the passive side (noisy under SIP — sizing modifier only); `spread_bps - spread_ma` rate of change (how fast spread is widening).

**Entry Side**: Direction of flow_imbalance.

**Exit Triggers**:
1. **Spread normalization**: `spread_bps` returns below `spread_ma` (new liquidity arriving)
2. **Flow reversal**: Signed flow reverses direction
3. **Thesis invalidation stop**: Price reversal beyond N × entry_spread

**No take-profit target.**

**Falsification Criteria**:
- Null hypothesis: Flow imbalance during spread expansion does NOT produce larger forward returns than flow imbalance during spread compression.
- Test: Compare conditional return distributions using Wilcoxon rank-sum test. Minimum 100 events in each condition.
- Reject hypothesis if p > 0.05 or if the conditional return difference < 1× transaction cost.

**Volatility regime segmentation (REQUIRED, post-Round-1 review)**: H2 must be tested separately across low-vol, mid-vol, and high-vol terciles (defined by trailing 20-day realized volatility). If H2 only fires profitably during high-vol periods (where spread widens mechanically during any volatility spike), it is a volatility proxy, not a liquidity fragility signal — kill it. The thesis is genuine only if it works during mid-vol regimes with sudden, anomalous spread expansion.

**Relationship to H1**: H2 is a conditional modifier of H1. H1 detects the flow. H2 asks: "Is the flow hitting fragile liquidity?" They may fire independently or jointly.

---

### H3: Volume-Synchronized Toxic Flow

**Participant Constraint**: Informed traders (those with private information about imminent news, earnings, or structural events) trade aggressively before information becomes public. Their trading creates toxic flow that is detectable via VPIN before the information is fully priced.

**Observable Chain**:
```
Informed participant trading on private information
  → Elevated buy-sell volume imbalance per volume bucket
    → VPIN rises (volume-synchronized probability of informed trading)
      → Direction of imbalance predicts price continuation
        → Persistence: until information is publicly incorporated (10-60+ minutes)
```

**Entry Signal**:
- `vpin` exceeds elevated threshold (e.g., 80th percentile of recent distribution) AND
- `flow_imbalance` is directionally significant (VPIN is unsigned — the direction comes from `flow_imbalance`, not from VPIN itself) AND
- `spread_bps` is not at extreme levels (market is still tradeable)

**Entry Side**: Direction of dominant flow within elevated VPIN window.

**Exit Triggers**:
1. **VPIN normalization**: `vpin` returns below neutral threshold (information incorporated)
2. **Flow reversal**: Dominant flow direction reverses
3. **Spread blowout**: `spread_bps` exceeds maximum tradeable threshold (market broken)
4. **Thesis invalidation stop**: Price reversal beyond threshold

**No take-profit target.**

**Falsification Criteria**:
- Null hypothesis: VPIN-conditioned directional flow does NOT predict forward returns better than unconditional directional flow.
- Test: Compare Sharpe ratio of trades taken during elevated VPIN vs trades taken during normal VPIN (same flow imbalance threshold). Paired comparison.
- Reject hypothesis if the VPIN-conditioned Sharpe is not statistically higher (bootstrap confidence interval for Sharpe difference excludes zero).

**Volatility contamination test (REQUIRED, post-Round-1 review)**: VPIN has a controversial empirical record — most published evidence shows it correlates with realized volatility, not directional predictability. This must be explicitly controlled for. Run:

`forward_return ~ flow_imbalance + vpin + realized_vol + vpin × flow_imbalance`

If the VPIN coefficient and interaction term are insignificant after controlling for `realized_vol`, kill H3 immediately. VPIN that only predicts volatility, not direction, is a volatility clustering proxy — not toxic flow detection. It would then be reclassified as a regime indicator (sent to ADS §2 regime layer) rather than an alpha signal. Additionally: compare H1-only outcomes vs H1+H3 joint outcomes. If H3 adds < 0.2 incremental Sharpe (annualized) to H1 alone, it is not providing economically meaningful information.

---

### H4: Price-Level Sweep Urgency

**Participant Constraint**: A participant sweeping through multiple price levels in rapid succession reveals extreme urgency — they value speed over price improvement. This urgency implies a mandate or information advantage that has not yet been fully executed.

**Observable Chain**:
```
Urgent participant with large mandate
  → Rapid sequence of trades at progressively worse prices
    → Visible top-of-book depth consumed at each level
      → Price jumps multiple spread-widths in seconds
        → Persistence: urgency implies remaining mandate (5-20 minutes)
```

**Entry Signal**:
- Detection of N trades within T seconds at predominantly worsening prices (≥80% of trades in sweep direction; ascending for buys, descending for sells)
- Total swept volume exceeds threshold (not a single small order)
- Price displacement during sweep > M × pre-sweep spread

**Entry Side**: Direction of the sweep.

**Exit Triggers**:
1. **Sweep exhaustion**: No further sweep patterns detected in subsequent windows
2. **Counter-sweep**: Sweep detected in opposite direction
3. **Flow normalization**: `trade_arrival_rate` returns to baseline
4. **Thesis invalidation stop**: Price reversal beyond threshold

**No take-profit target.**

**Falsification Criteria**:
- Null hypothesis: Forward 10-30 minute returns after detected sweeps are not statistically different from zero.
- Test: Event study methodology. Mean and median post-sweep returns at 5, 10, 15, 30 minute horizons. Bootstrapped confidence intervals.
- Reject hypothesis if mean return at target horizon < 2× transaction cost, or if p > 0.05.

**Frequency exception (post-Round-1 review)**: H4 is the hypothesis most likely to produce convex payoff (rare but large wins). The kill criterion for H4 is relaxed: accept ≥ 0.5 events/day per liquid symbol (every other day) IF per-event net edge > 5× round-trip cost AND P&L skewness > 1.0. Rare high-skew signals can anchor portfolio tail performance even at low frequency.

**TRF filter**: Exclude Trade Reporting Facility (TRF) venue prints from sweep detection. TRF prints represent internalized/dark pool executions and do not reflect public market urgency. Including them contaminates the signal with broker-dealer internalization artifacts that are not indicative of a sweep through displayed liquidity.

---

### H5: Quote-Driven Information Asymmetry

**Participant Constraint**: Market makers and liquidity providers see order flow before it executes. When they detect informed flow (or anticipate it from correlated signals), they adjust quotes asymmetrically — pulling one side while maintaining the other. This quote adjustment precedes and predicts the direction of impending trades.

**Observable Chain**:
```
Liquidity provider detects information arrival
  → Asymmetric quote adjustment (bid pulled down faster than ask, or vice versa)
    → Midpoint shifts directionally
      → Trade flow follows in the direction of the shift
        → Persistence: quote shift leads trade flow by seconds to minutes
```

**Entry Signal**:
- `midpoint` drift rate exceeds threshold (directional quote pressure) AND
- Quote update asymmetry: one side of NBBO updating significantly more frequently than the other AND
- `trade_arrival_rate` has not yet spiked (the information is in quotes, not yet in trades)

**Entry Side**: Direction of midpoint drift.

**Exit Triggers**:
1. **Trade arrival spike**: `trade_arrival_rate` normalizes after spiking (information has been traded)
2. **Quote symmetry restoration**: Both sides of NBBO updating at similar rates
3. **Midpoint stabilization**: Drift rate returns to noise level
4. **Thesis invalidation stop**: Price reversal beyond threshold

**No take-profit target.**

**Falsification Criteria**:
- Null hypothesis: Asymmetric quote adjustment does NOT lead trade-level price movement.
- Test: Granger causality test from quote midpoint changes to trade-level returns. Minimum 500 events.
- Reject hypothesis if Granger test p > 0.05, or if the lead-time is < 1 second (too fast to trade on SIP latency).

**Risk note**: This hypothesis is the most latency-sensitive. If the information in quotes is incorporated within milliseconds, it is not tradeable on SIP data. The falsification test explicitly checks for this.

**Priority and early-kill protocol (post-Round-1 review)**: H5 has the lowest expected survival probability (~10-20%). It is the last hypothesis tested in Phase 3. Maximum allocated testing time: 1 week. Early-kill rule: if Granger test on the first 2-3 symbols shows lead-time < 1 second, terminate H5 testing immediately without completing the full universe. Redirect saved research time to deeper H1/H4 analysis. Do not emotionally defend this hypothesis.

---

## 4. HYPOTHESIS INTERACTION MODEL

The five hypotheses are not mutually exclusive. They can fire independently or jointly.

```
                    ┌──── H5: Quote Information ────┐
                    │         (leading)              │
                    ▼                                │
            ┌── H1: Sustained Flow ──┐              │
            │    (primary signal)     │              │
            │                        │              │
            ▼                        ▼              │
    H2: Fragile Liquidity    H3: Toxic Flow         │
    (amplifier: H1 in        (qualifier: is H1      │
     thin conditions)          informed?)            │
            │                        │              │
            ▼                        │              │
    H4: Sweep Detection              │
    (extreme urgency                 │
     within H2 regime)               │
            │                        │
            ▼                        ▼
        [Entry Decision: strongest thesis wins]
```

**Combination rules**:
- H1 alone is sufficient for entry (sustained flow is the primary signal)
- H2 without H1 is NOT sufficient (fragile liquidity without directional flow is not a thesis)
- H3 without H1 is NOT sufficient (elevated VPIN without directional flow is ambiguous)
- H4 implies H1 (a sweep IS aggressive directional flow — it's a subset)
- H5 may fire before H1 (quotes lead trades) — earliest possible entry

**Confidence ordering**: When multiple hypotheses fire simultaneously:
- H1 + H2 (flow in fragile liquidity) > H1 alone
- H1 + H3 (informed flow) > H1 alone
- H1 + H2 + H3 (informed flow in fragile liquidity) = highest conviction
- H5 alone (quote-only, no trade confirmation yet) = lowest conviction entry

Position sizing should scale with the number of confirming hypotheses **at entry time**, subject to ADS §7 constraints.

**Conflict resolution**: If H5 (quotes) and H1 (trades) fire in opposite directions, **H1 supersedes**. Trade flow is the realized expression of intent; quote adjustment may reflect hedging or repositioning that does not translate to directional price movement. Do not enter on H5 alone if H1 contradicts.

**No pyramiding rule**: Once a position is open on a symbol, additional hypothesis confirmations do NOT increase position size. They may extend the holding decision (hold longer if additional hypotheses confirm) or affect the exit path (tighter invalidation if fewer hypotheses remain active), but the position is sized once at entry. Adding to a winning position on flow continuation reintroduces concavity (larger exposure at worse prices).

**Primary commitment: H1 (post-Round-2 review)**: H1 (Sustained Directional Execution Pressure) is the core engine of the program. All other hypotheses are conditional extensions:
- H2 = amplifier of H1 (flow in thin liquidity)
- H3 = qualifier of H1 (is the flow informed?)
- H4 = extreme subset of H1 (sweep = aggressive flow burst)
- H5 = potential leading indicator for H1 (quotes lead trades)

**If H1 fails Phase 3 testing, the program has a fundamental problem** regardless of H2-H5 outcomes. H1 is tested first, with the full Phase 2 → Phase 3 pipeline. Only after H1 validation do H2-H4 testing begin. H5 remains lowest priority. Do not attempt to validate all five simultaneously. Build from the core outward.

---

## 5. PROHIBITED PATTERNS

These are absolute prohibitions to prevent identity drift — the reintroduction of statistical momentum logic under flow terminology.

### 5.1 Signal Construction Prohibitions

1. **No rolling z-scores with lookback > 5 volume buckets on flow metrics.** Flow is event-driven. Extended smoothing recreates the lag structure of bar-based indicators. If you need to normalize, use the empirical distribution of the metric over a recent calibration window, not a rolling z-score.

2. **No composite scores.** Each hypothesis generates its own entry signal. Signals are NOT aggregated into a weighted sum, composite index, or "flow_z" score. If H1 says enter and H3 says don't, record the disagreement — do not average them into a half-signal.

3. **No bar-aggregated features as primary signals.** OHLCV bars (1-minute or otherwise) may be used for regime context (ADS §2) and risk management, but NOT for alpha generation. The alpha layer operates on tick and quote primitives.

4. **No reintroduction of momentum indicators as flow proxies.** RSI, MACD, stochastic, ADX, Bollinger Bands, and similar bar-derived indicators are not flow signals. They may exist in the regime detection layer (existing infrastructure) but must not appear in the flow alpha's entry logic.

5. **No time-bucketed VPIN.** VPIN must be computed using volume-synchronized buckets with Lee-Ready classification. Computing VPIN from time-bucketed bars collapses it to a volatility proxy (the exact failure mode of the legacy system).

### 5.2 Exit Prohibitions

6. **No decaying take-profit.** The expression `TP(t) = TP_0 * exp(-t/τ) + TP_floor` is prohibited. This caps upside and creates concave payoff geometry. If the flow thesis is still active, the position is held. Period.

7. **No volatility-expanding stops.** The expression `stop = k * σ * sqrt(1 + κ * Δρ)` is prohibited for the flow alpha. Stops must be thesis-invalidation events (flow reversal, spread regime change), not scaled to realized volatility. Wider stops in stress = larger losses in the worst regime = concavity.

8. **No exit on statistical reversal of entry indicators.** The legacy system exits when "composite_z flips sign." The flow alpha must exit when the *flow condition* that justified entry dissipates — not when a smoothed indicator crosses zero.

### 5.2.1 Timing Prohibitions

9a. **No trading during the opening rotation (9:30-9:45 ET).** The first 15 minutes after open have structurally different microstructure: opening auction imbalances, accumulated overnight order flow, and wide spreads create signals that look like H1/H2 events but are actually structural, non-repeating phenomena. The flow alpha must wait for the market to establish a post-open equilibrium before evaluating hypotheses. (This aligns with the legacy ORB filter concept but is justified on microstructure grounds, not statistical pattern grounds.)

9b. **No new entries after 15:45 ET.** The final 15 minutes before close have their own structural dynamics (MOC order flow, index rebalancing). These create genuine flow events, but the holding period is too constrained for the alpha to express. Combined with EOD forced exit, late entries create guaranteed concavity.

### 5.2.2 Hard Pre-Entry Invalidation Conditions (post-Round-2 review)

These are absolute rejection criteria evaluated BEFORE any hypothesis trigger. If any condition is true, no entry is permitted regardless of signal strength.

12. **Spread regime degraded**: If `spread_bps` > P90 of that symbol's trailing 5-day intraday distribution → no entry. Liquidity has dried up; effective spread cost will overwhelm any edge.

13. **Execution quality degraded**: If `effective_spread` of the most recent 10 trades > 2× the symbol's trailing median → no entry. The market is too adverse for entry.

14. **LULD proximity**: If price is within 2% of a LULD band → no entry. Halt risk is elevated and the flow thesis cannot survive a halt (Section 6.1).

15. **Scheduled event imminent**: If a known scheduled event (FOMC, CPI, earnings for that symbol) occurs within 30 minutes → no new H1/H2/H4 entries. H3 (toxic flow) MAY be permitted for that symbol only, as it is designed to detect pre-announcement informed flow. Post-event, normal operations resume after a 5-minute cooldown.

16. **Impact elasticity inverted**: If `price_impact_per_volume` is declining (price absorbing flow more easily despite rising imbalance) → no entry. The flow is being met with counter-liquidity, invalidating the persistence thesis.

### 5.3 Architecture Prohibitions

10. **No shared alpha state with legacy momentum module.** The flow alpha is a separate module under Rule 7 skeleton. It does not read legacy alpha signals, composite_z, transition_score, or SMS from the old module. Clean separation.

11. **No more than 3 entry conditions per hypothesis.** Each hypothesis has a clear trigger. Over-gating recreates the confirmation engine problem. If you need more than 3 conditions to feel confident in the signal, the hypothesis is too weak.

---

## 6. EXIT CONVEXITY SPECIFICATION

The exit structure must produce **positive skew**: many small losses, fewer but larger wins.

### 6.1 Stop Design (Bounded Downside)

**Thesis invalidation stop**: For each hypothesis, the stop is defined by the specific condition that falsifies the entry thesis:

| Hypothesis | Invalidation Condition |
|------------|----------------------|
| H1 | `flow_imbalance` reverses sign for M consecutive volume buckets |
| H2 | `spread_bps` returns below `spread_ma` (spread normalization = liquidity restored) |
| H3 | `vpin` drops below neutral threshold |
| H4 | No further sweep detected within N seconds |
| H5 | Quote asymmetry normalizes |

**Price-based emergency stop**: If price moves against entry by more than `max_adverse_spread_multiple × entry_spread`, exit immediately regardless of flow state. This is a circuit breaker, not a primary exit. It should trigger rarely (< 10% of exits in backtesting).

**The stop is TIGHT.** It is not 2σ volatility-based. It is: "the thing I entered for is no longer happening." When a thesis-invalidation condition triggers, the resulting price loss is expected to be small (the flow reversed before significant adverse move). The price-based emergency stop (separate from thesis invalidation) is set at `max_adverse_spread_multiple × entry_spread` — expected range: 5-15× entry spread. This emergency stop should trigger on < 10% of exits; if it triggers more frequently, the thesis-invalidation conditions are too slow.

**Halt risk**: If a stock is halted (LULD or regulatory) while a position is open, the flow thesis is structurally invalidated — the halt itself disrupts the flow state. Exit at first available price after resumption. Do not attempt to re-evaluate the hypothesis post-halt; treat as a forced exit.

**Intraday-only constraint**: All flow alpha positions must be flat before EOD (consistent with existing `EODGuard`). No overnight holding. The flow thesis has no persistence across sessions — overnight gap risk is unbounded and unrelated to intraday flow dynamics.

### 6.1.1 Adverse Selection on Entry

The flow alpha buys INTO detected buy flow (or sells into detected sell flow). By definition, entry is directionally aligned with recent price movement. This means:
- Entry price is inherently adverse: the alpha is chasing short-term momentum
- Expected entry slippage > prevailing quoted spread (we are competing with the same aggressive flow we detected)
- Cost model must use `effective_spread` at entry time (actual realized cost), not quoted spread

This is the fundamental cost of flow-following strategies. The edge must exceed this adverse cost. If the expected forward return conditional on the signal does not exceed `effective_spread + commission`, the signal is not tradeable — regardless of statistical significance. This is explicitly tested in Phase 3 of the falsification protocol (Section 8.1, step e).

### 6.2 Continuation Design (Unbounded Upside)

**No take-profit target.** The position is held as long as the entry thesis remains active:
- Flow imbalance persists → hold
- Spread remains favorable → hold
- VPIN remains elevated (for H3) → hold
- Sweeps continue (for H4) → hold

**Partial exit on diminishing flow (VARIANT, not default — post-Round-1 review)**: The default exit is FULL exit on thesis invalidation (simplicity). In Phase 5, three variants are tested:
- (a) Full exit on thesis invalidation (simplest — THIS IS THE DEFAULT)
- (b) Partial exit: reduce position by 50% when flow weakens from "strong" to "moderate" (not reversed), full exit on reversal
- (c) Trailing exit: scale out proportionally to flow intensity decline

Only adopt (b) or (c) if out-of-sample Sharpe improves by > 0.2 versus (a). If improvement is marginal, use (a). Partial exits introduce complexity and can reintroduce concavity if not carefully calibrated. Simplicity is the default; complexity must earn its place.

**Time circuit-breaker**: Maximum holding period (configurable, expected 30-60 minutes). This is NOT a primary exit — it is a safety valve. If it triggers on >20% of trades, the holding period is too short or the flow persistence model is wrong.

### 6.3 Expected Payoff Geometry

If the system is correctly implemented:
- **Hit rate**: 35-50% (low is expected and acceptable)
- **Win/loss ratio**: 2-5× (winners must be larger than losers)
- **Skewness**: Positive (right tail fatter than left)
- **Per-trade max loss**: Bounded by thesis invalidation stop (small)
- **Per-trade max win**: Unbounded by design (no TP cap)

This is the opposite of the legacy system's geometry (60% hit rate, 0.5× win/loss ratio, negative skew).

---

## 7. ADS v3.1 COMPATIBILITY

### What Changes

| ADS Section | Legacy Momentum | Flow Alpha |
|------------|----------------|------------|
| §1 SMS | Composite z-scores, statistical maturity | **Replaced**: Flow event detection is the maturity signal. If the flow event has not occurred, there is no signal — no pending queue needed. |
| §3 ERAR | Expected PnL from ATR-based expected move; CVaR normal approximation; holding period = 90 min (fantasy) | **Redesigned**: Expected PnL from flow-conditioned return distribution (empirical, not model). CVaR from empirical tail. Holding period = actual median holding from backtest. Cost model uses realized fill data, not hardcoded participation. |
| §5 Stop-Loss | Volatility-scaled expanding stop | **Replaced**: Thesis invalidation stop (Section 6.1 above). Vol-stop retained only as circuit breaker at extreme levels, not as primary exit. |
| §9 Multi-Exit | 7-priority exit with decaying TP | **Simplified**: (1) Thesis invalidation stop, (2) Flow dissipation exit, (3) Liquidity regime exit, (4) Time circuit-breaker. No decaying TP. No statistical reversal exit. |

### What Stays

| ADS Section | Application to Flow Alpha |
|------------|--------------------------|
| §2 Regime Vector | Unchanged. Flow alpha consumes R for regime context. May trade less aggressively in high-vol or low-confidence regimes. |
| §4 Shift Detection (SRI) | Unchanged. Market shift detection is independent of alpha identity. |
| §6 Trend Avoidance (TPI) | Adapted. Flow alpha should NOT avoid counter-trend entries if the flow thesis is valid — a forced seller creates real flow regardless of trend. TPI used as sizing modifier, not entry veto. |
| §7 Position Sizing | Adapted. Size scales with number of confirming hypotheses and flow intensity, not composite confidence score. Kelly inputs calibrated from flow-conditioned trade outcomes. |
| §8 Cooldown (PVSI) | Unchanged. Cooldown after abnormal loss patterns applies regardless of alpha identity. |
| §10 Meta-Learning | Unchanged. Edge decay detection applies. PHT input = risk-normalized trade outcome conditioned on flow regime. |

---

## 8. FALSIFICATION PROTOCOL

Before writing any production code, each hypothesis must pass a **historical evidence gate** using Polygon Stock Advanced historical tick + quote data.

### 8.1 Test Sequence

```
Phase 1: Data Ingestion (2 weeks)
  - Ingest 6+ months of tick + quote data for target universe
  - Implement Lee-Ready classifier
  - Implement volume-clock bucketing
  - Validate data quality (gaps, duplicates, timestamp ordering)

Phase 2: Foundation Diagnostics — PROGRAM GATE (2 weeks)
  This phase determines whether the program proceeds. It answers: "Is the
  information layer viable before we test any hypothesis?"

  2a. Primitive Computation
    - Compute all observable primitives (Section 2)
    - Compute derived flow metrics (Section 2.3)
    - Statistical characterization: distributions, autocorrelations, stationarity

  2b. PERSISTENCE DECAY CURVE (program-level gate)
    - Compute autocorrelation of cumulative_imbalance at 1, 2, 5, 10, 15, 30, 60 minute lags
    - Estimate the half-life per symbol (time for autocorrelation to drop to 50%)
    - Compute "cost-covering holding period" = time needed for expected return to exceed
      effective_spread + commission (estimated from unconditional signed_volume → return regression)
    - GATE: If half-life < cost-covering holding period on > 80% of symbols, abort program
    - OUTPUT: per-symbol exploitable persistence window (replaces the assumed 10-60 min range)
    - PERSISTENCE CATEGORIZATION (post-Round-3 review):
      * Half-life > 10 buckets (~20 min): MANDATE REGIME → H1 as designed, lower frequency, larger per-trade edge expected
      * Half-life 3-10 buckets (~6-20 min): INTERMEDIATE → viable but requires faster execution, tighter thesis-invalidation, higher frequency to compensate for smaller per-trade edge
      * Half-life < 3 buckets (< 6 min): MICRO-BURST REGIME → strategy identity shifts to micro-burst scalping, not sustained execution pressure. This is still legitimate flow alpha, but the holding period, sizing, and exit logic must adapt. Be honest about which regime the data reveals.
    - PRE-COMMITMENT (post-Round-3 final review): If >60% of detected imbalance events across
      the target universe fall into the micro-burst category (half-life < 3 buckets), H1 as
      "sustained mandate detection" is falsified. Trigger Section 8.3.1 (Micro-Burst Contingency
      Protocol). This threshold is frozen before testing. No post-hoc reclassification permitted.
    - MINIMUM HALF-LIFE THRESHOLD: If median imbalance half-life across the target universe < 3
      buckets, H1 is rejected outright (per Section 8.3 criterion R3). The "sustained" qualifier
      in H1's thesis statement requires that the TYPICAL event, not just outliers, exhibits
      multi-bucket persistence.
    - Additionally, measure: conditional continuation probability after k consecutive imbalance buckets (k=1,2,3,5,10). This directly determines whether "sustained" flow exists at all, or whether imbalance is just noise with short autocorrelation.

  2c. LEE-READY QUALITY ASSESSMENT (program-level gate)
    - Three-way comparison: tick-rule vs Lee-Ready (midpoint exclusion) vs Lee-Ready (probabilistic)
    - Correlation of each signed_volume method with 1-minute forward returns
    - Midpoint trade fraction by volatility quintile and time-of-day
    - NOISE INJECTION: inject 10%, 15%, 20% random misclassification into trade_sign.
      Recompute H1 signal. If t-stat < 2.0 at 15% noise: edge is classification-fragile
    - GATE: If best classifier shows < 0.05 correlation with forward returns, abort program

  2d. VOLUME BUCKET DIAGNOSTICS
    - Distribution of bucket fill durations (wall-clock seconds), report CV
    - If CV > 2.0: test time-of-day-adjusted bucketing as alternative
    - Autocorrelation of flow_imbalance across buckets
    - Breusch-Pagan heteroskedasticity test on per-bucket flow_imbalance
    - Report persistence in both bucket-time and wall-clock-time

Phase 3: Hypothesis Testing (2-3 weeks per hypothesis; parallelizable across hypotheses)
  Testing order: H1 (core) → H4 (convexity) → H2 (amplifier) → H3 (VPIN) → H5 (quotes, last)

  PRE-REGISTRATION REQUIREMENT: Before examining any return data, define a coarse
  parameter grid for each hypothesis (3-5 values per parameter, chosen on structural
  grounds). The grid is frozen before testing. No local optimization, no gradient descent.

  For each H1-H5:
    a. Define event detection rules precisely (using pre-registered parameter grid)
    b. Identify all events in historical data for ALL grid points
    c. Split data: 60% in-sample (train), 40% out-of-sample (test), chronological split
    d. Compute forward returns at the persistence horizons identified in Phase 2b (in-sample first)
    e. Apply falsification test (Section 3, per hypothesis) on in-sample data across ALL grid points
    f. Report FULL sensitivity surface (t-stat across entire grid), not just optimal point
    g. ROBUSTNESS CHECK: hypothesis passes in-sample only if t-stat > threshold for > 50% of grid
       points. A single optimal point surrounded by failure = overfitting
    h. Estimate transaction cost impact using effective_spread at entry, not quoted spread
    i. If in-sample passes: apply same test on out-of-sample data WITHOUT parameter changes
    j. Record: event count, mean return, t-statistic, Sharpe, max drawdown, skewness,
       daily expected PnL (frequency × net edge)
    k. SELF-IMPACT TEST (H1 required, all hypotheses recommended): For each detected event,
       compute impact_ex_self by removing our hypothetical order size from the bucket's
       signed volume and recomputing Δmidpoint/adjusted_signed_volume. If >20% of events
       show self-impact divergence >10%, report adjusted continuation statistics separately.
       The PRIMARY result for H1 must use the self-impact-adjusted elasticity, not raw.
    l. 2D CONTINUATION HEATMAP (H1 required): For all imbalance events, compute:
       P(continuation | elasticity_decile, volume_percentile)
       Partition events into 5 elasticity bins × 5 volume bins (25 cells). Report
       continuation probability, mean return, and event count per cell. If no separability
       exists (continuation probability does not vary monotonically across either axis),
       then elasticity is not informative for entry timing — demote to monitoring only.
       TIME-OF-DAY STRATIFICATION (post-Round-3 final audit): Microstructure regimes are
       NOT stationary across the trading day. The heatmap must be computed separately for
       three intraday regimes:
         - Opening absorption: 9:45-10:15 (auction spillover, high variance)
         - Midday thinning: 11:30-13:30 (liquidity drought, wide spreads, low volume)
         - Closing imbalance: 14:00-15:45 (portfolio rebalancing, index tracking, MOC flow)
       If the signal exists in only ONE time-of-day regime, effective trading capacity shrinks
       to that window (~2 hrs/day instead of ~6). Report the fraction of daily edge
       attributable to each regime. If >70% of edge concentrates in a single window, flag
       as capacity-constrained and revise daily P&L estimates accordingly.
  - Test on minimum 5-10 liquid symbols across different sectors and liquidity tiers
  - Test across different market regimes (trending, choppy, volatile)
  - Exclude first 15 minutes post-open and last 15 minutes pre-close from event detection
  - Exclude dates with major corporate events (earnings, splits, index changes) from primary analysis;
    test separately on event dates to determine if hypotheses are amplified or distorted
  - Multiple testing correction: effective hypothesis count = N_hypotheses × mean(grid_points_per_hypothesis).
    Apply Holm-Bonferroni to the effective count (e.g., 5 hypotheses × 5 grid combos = 25 effective tests).
    Report both corrected and uncorrected p-values.

Phase 4: Interaction Testing + Endogenous Decay Testing (2-3 weeks)
  - Test hypothesis combinations (H1+H2, H1+H3, etc.)
  - Verify that combinations improve, not degrade, performance
  - Check for overfitting (in-sample vs out-of-sample split)
  - ENDOGENOUS DECAY TEST (post-Round-3 final audit): Second-order reflexivity cannot be
    backtested — other participants may detect the same imbalance pattern and alter their
    response function when our live volume appears. To bound this risk:
    a. Participation randomization: replay Phase 3 best-performing events at 3 participation
       levels (0.1%, 0.25%, 0.5%). Simulate our order injected into each bucket's volume.
       If continuation probability degrades monotonically with our participation → edge has
       endogenous decay component. Report the participation level at which edge drops below
       the R2 threshold (1.5 bp net). This becomes the LIVE participation ceiling.
    b. Shadow-mode design (pre-Phase 6 live deployment): Before committing real capital,
       run 2-4 weeks of shadow-mode — full signal generation, simulated fills against live
       quotes, NO actual orders. Compare shadow continuation probability to Phase 3 backtest.
       If shadow continuation < 90% of backtest continuation → endogenous decay is real.
       Reduce participation ceiling or abort.
    c. Live A/B throttling (Phase 6): Once live, randomly suppress 20% of qualifying trades
       (coin-flip before entry). Compare suppressed-window continuation to traded-window
       continuation. If traded windows show statistically lower continuation (t > 2.0, N > 100
       paired comparisons) → our footprint is distorting the microstructure. Reduce size
       until the effect disappears.

Phase 5: Exit Geometry Verification (1 week)
  - Simulate entry+exit rules from Section 6
  - Test three exit variants: (a) full exit, (b) partial exit, (c) trailing exit
  - Default to (a) unless (b) or (c) improves OOS Sharpe by > 0.2
  - Verify positive skew in P&L distribution
  - Verify win/loss ratio > 1.5
  - Verify hit rate is realistic (35-50%)
  - Verify maximum drawdown is survivable
```

### 8.2 Kill Criteria

**Abort the hypothesis if:**
- Fewer than 50 events detected in 6 months on a liquid name → insufficient frequency (exception: H4 threshold is ≥ 0.5 events/day if per-event edge > 5× cost and skewness > 1.0)
- Mean forward return at target horizon is negative → wrong direction
- Mean forward return < 2× estimated round-trip cost → insufficient edge after costs
- Holm-Bonferroni corrected p-value (using effective hypothesis count including grid search) > 0.05 → not statistically distinguishable from noise
- Robustness test fails: t-stat > threshold for < 50% of pre-registered parameter grid points → overfitted to specific parameterization
- Out-of-sample Sharpe < 0.5 (annualized) → insufficient risk-adjusted return
- P&L skewness is negative → payoff geometry is wrong (concave, not convex)

**Abort the entire program at Phase 2 if:**
- Persistence half-life < cost-covering holding period on > 80% of target universe symbols (Phase 2b gate)
- Best Lee-Ready variant shows < 0.05 correlation between signed_volume and 1-min forward returns (Phase 2c gate)
- H1 t-stat drops below 2.0 under 15% noise injection (Phase 2c gate — classification-fragile edge)

**Abort the entire program at Phase 3 if:**
- None of H1-H5 pass Phase 3 testing on any symbol
- Volume-clock VPIN does not statistically outperform time-clock VPIN (H3-specific, but indicates data infrastructure problem)

### 8.3 PRE-DEFINED H1 REJECTION CRITERIA (post-Round-3 final review)

These thresholds are defined BEFORE any empirical testing begins. They are non-negotiable and prevent post-hoc rationalization. H1 is the primary commitment of this program; if H1 fails these gates, the program identity must change or terminate.

**H1 is REJECTED if ANY of the following hold after Phase 2b + Phase 3 testing:**

| # | Criterion | Threshold | Rationale |
|---|-----------|-----------|-----------|
| R1 | Conditional continuation probability after 3 buckets | Lower bound of 95% CI < 50%, OR point estimate < 55%, OR CI width > 6% (insufficient sample size) | A point estimate of 55% is useless if the CI spans 48-62%. Thin-edge measurement requires statistical discipline beyond point thresholds. The CI-based gate prevents termination on sampling noise while still rejecting genuinely insufficient autocorrelation. |
| R2 | Net edge after modeled effective spread + commission + 0.5 bp estimation error buffer | Lower bound of 95% CI < 0 bp, OR point estimate < 1.5 bp | The 0.5 bp buffer accounts for irreducible estimation uncertainty in edge measurement. If the lower CI bound is near zero, we do not have an institutional strategy — we have noise. The 1.5 bp point estimate (up from 1 bp) reflects the expert's correct observation that estimation error must be treated as a cost. |
| R3 | Majority event classification | > 60% of imbalance events are micro-burst (half-life < 3 buckets) | H1 claims "sustained execution pressure." If the majority of detectable events are micro-bursts, the causal thesis is wrong — the data shows impulse, not mandate. |
| R4 | Slippage divergence | Realized slippage > 120% of modeled in rolling 30-trade window during Phase 3 replay | Cost model is unrealistic. If we cannot model friction accurately in historical replay, live trading will be worse. |
| R5 | Volume-conditioned elasticity separability | 2D continuation heatmap (Phase 3, step l) shows no monotonic variation across either elasticity or volume axis | Elasticity is not informative for entry timing. The core gating variable is noise. |
| R6 | Self-impact contamination | > 20% of events show self-impact divergence > 10% AND self-impact-adjusted continuation probability drops below R1 threshold | Our own participation distorts the measurement. The edge is reflexive, not real. |

**If R1, R2, or R3 triggers**: The entire H1 thesis is invalid. Do not attempt to salvage by parameter tuning. Either:
- Redesign into a micro-burst strategy (fundamentally different identity — see Section 8.3.1 below), OR
- Abandon flow alpha entirely and return to Option B (statistical cross-sectional momentum).

**If R4, R5, or R6 triggers**: The thesis may be valid but the measurement infrastructure is inadequate. Investigate root cause before declaring H1 dead. R4 may indicate a cost model error (fixable). R5 and R6 require deeper analysis of whether the signal exists but is unmeasurable, or simply doesn't exist.

#### 8.3.1 Micro-Burst Contingency Protocol

If Phase 2b reveals >60% micro-burst events (R3 triggered), the program does NOT automatically terminate. Instead:

1. **Identity shift declaration**: Publicly acknowledge that the strategy is micro-burst scalping, NOT sustained mandate detection. All documentation, naming, and mental models must update.
2. **Holding period redesign**: Target holding period drops from 10-30 min to 1-5 min. Exit logic becomes time-dominant (hard exit after N buckets), not flow-dissipation-dominant.
3. **Turnover recalculation**: Expected round-trips/day/symbol may increase from 2-6 to 10-30. Transaction cost becomes the dominant constraint.
4. **Kelly re-estimation**: Edge per trade is smaller; variance per trade may also be smaller. New Kelly fraction must be computed from micro-burst return distribution.
5. **Minimum net edge threshold**: Increases from 1.5 bp to 2.5 bp for Tier A, 3.0 bp for Tier B/C (micro-burst pays spread more frequently AND faces faster adverse selection from HFT participants who detect the same impulse patterns).
6. **GATE**: If micro-burst net edge after spread < 2.5 bp on Tier A symbols OR < 3.0 bp on Tier B/C symbols, on >80% of the respective tier → program terminates.
7. **Crowding assessment (post-Round-3 final audit)**: Impulse detection at 1-5 minute horizons is the MOST crowded microstructure strategy class. Before committing to the micro-burst path, conduct a simple crowding diagnostic: measure the autocorrelation of micro-burst events across symbols. If >40% of micro-burst events cluster within the same 5-minute window across 3+ symbols, the signal is likely driven by common macro flow (not symbol-specific edge) and is being competed away by faster participants.

This prevents drifting into "almost works" territory. The micro-burst path is a legitimate alternative, but it must be entered deliberately with revised economics. Micro-burst at SIP latency competes directly with HFTs — we must demonstrate clearly superior edge, not marginal edge.

### 8.4 What Success Looks Like

A hypothesis is considered validated and ready for implementation when:
- Event frequency: > 2 per day per liquid symbol (H4 exception: > 0.5/day if high skew)
- Net mean return (after costs using effective_spread): > 0 at empirically-determined persistence horizon
- t-statistic: > 2.5 (to survive Holm-Bonferroni correction across effective hypothesis count)
- Robustness: t-stat > threshold for > 50% of pre-registered parameter grid points
- Out-of-sample Sharpe: > 1.0 (annualized, on the strategy returns)
- P&L skewness: > 0.5 (positive)
- Maximum drawdown: < 5% of capital in any 20-day window
- Win/loss ratio: > 1.5×
- Daily expected PnL (frequency × net edge) is positive on > 60% of trading days in OOS period

---

## 9. DATA DEPENDENCIES AND ASSUMPTIONS

### 9.1 Critical Assumptions

1. **Lee-Ready classification accuracy ≥ 85%** on the target universe. If classification accuracy drops below 80% (measurable via known trade direction events such as exchange-reported imbalances), H1 and H2 are degraded.

2. **NBBO is representative of true best prices.** In practice, dark pools and internalization may create better prices not visible in NBBO. This means our spread measurements may overstate true spread, making our cost estimates conservative (acceptable).

3. **SIP latency does not destroy signal.** For 10-30 minute holding periods, SIP consolidation delay (typically 1-15ms; >15ms indicates data quality issue) is negligible. This assumption would fail for sub-second strategies. H5 (quote-driven) is the most latency-sensitive hypothesis and has an explicit falsification criterion to verify this (lead-time must exceed 1 second).

4. **Volume-clock bucketing produces approximately stationary flow metrics.** This is a testable assumption. If the distribution of `flow_imbalance` per volume bucket is non-stationary, calibration windows must be adaptive.

5. **The target universe has sufficient tick activity.** Hypotheses require meaningful trade flow to detect. Minimum: > 5,000 trades/day for H1/H3, > 10,000 trades/day for H4 (sweeps require dense trade sequences), > 20,000 NBBO updates/day for H5 (quote asymmetry requires active quoting). Symbols below these thresholds are excluded from the respective hypotheses.

6. **Regular hours only (9:30-16:00 ET, excluding 9:30-9:45 and 15:45-16:00 per Section 5.2.1).** Pre-market and after-hours have structurally different microstructure: wider spreads, sparse depth, different participant mix (more retail via extended-hours brokers). Flow patterns detected outside regular hours do not generalize.

7. **Corporate events are regime variables, not alpha inputs.** Earnings announcements, stock splits, index additions/deletions, and dividend ex-dates create structural flow that may amplify or distort the hypotheses. These events are flagged in the data and analyzed separately (Phase 3) — they are not filtered out, but the alpha is NOT designed to trade earnings flow specifically.

### 9.2 What Is NOT Assumed

- That Lee-Ready perfectly classifies every trade (it doesn't — ~7-15% error rate)
- That NBBO depth represents total available liquidity (it doesn't — hidden orders exist)
- That flow persistence is guaranteed (it isn't — which is why we have tight stops)
- That any individual hypothesis will be profitable (which is why we have a falsification protocol)
- That the legacy system's parameters or thresholds are relevant (they aren't — clean break)
- That entry cost equals quoted spread (it doesn't — adverse selection means effective spread at entry exceeds quoted spread)
- That all five hypotheses will survive testing (they may not — the falsification protocol is designed to kill weak hypotheses)
- That signals are tradeable during the open/close rotations (they aren't — structural microstructure differences invalidate the hypotheses during these windows)

---

## 10. WHAT THIS DOCUMENT DOES NOT CONTAIN

- Implementation details (data structures, class hierarchies, function signatures)
- Parameter values (thresholds, bucket sizes, lookback windows) — these emerge from Phase 3 testing
- Code
- Performance projections
- Comparisons to the legacy momentum alpha

Those belong in subsequent documents:
- **Implementation Specification** (after hypotheses are validated)
- **Backtest Results** (after implementation)
- **Production Deployment Plan** (after backtest validation)

---

## 11. ECONOMIC CONSTRAINTS (Round 2 Preparation)

These parameters constrain the economic viability of the program. They are not aspirational — they reflect realistic operating conditions.

### 11.1 Target Universe

**Liquidity tiers** (test across both, select based on Phase 2/3 results):

| Tier | ADV ($ volume) | Trades/day | Examples | HFT Competition |
|------|----------------|------------|----------|----------------|
| A: Mega-cap liquid | > $2B/day | > 200K | TSLA, NVDA, AAPL, AMD, META | Extreme — fastest reversion, tightest spreads |
| B: High-cap liquid | $200M-$2B/day | 50K-200K | MU, ANET, PANW, DASH, COIN | High — but potentially better persistence |
| C: Mid-cap liquid | $50M-$200M/day | 20K-50K | Various | Moderate — more persistence, wider spreads |

**Initial test universe**: 20-30 symbols spanning Tiers A-B, across at least 5 sectors (tech, financials, energy, healthcare, consumer). Tier C is tested in Phase 3 extension if Tier A/B shows persistence.

**Exclusions**: Symbols with ADV < $50M/day or < 20K trades/day. Symbols with > 50% of volume in dark pools (TRF fraction too high to observe flow). Symbols with recent corporate events during test window are flagged, not excluded.

**Key insight from Round 1 critique**: The edge is likely LARGER in Tier B/C (less HFT competition, slower reversion) but signal quality is LOWER (fewer trades, noisier Lee-Ready). The optimal tier is where signal quality × persistence > cost. This is empirically determined in Phase 3.

### 11.2 Per-Trade Capital Allocation

- **Maximum per-position**: 2% of portfolio capital
- **Participation constraint**: Order size < 0.5% of rolling 3-minute volume (not daily ADV — see Section 12.6 for rationale). Halved to 0.25% when spread > median + 1σ. This ensures our order does not move the market or contribute to the very imbalance we detected.
- **Minimum viable portfolio**: ~$200K. Below this, fixed costs (data feed, infrastructure) dominate returns. Above $5M, participation constraints begin binding on Tier B/C names.

For a $500K portfolio trading a Tier A name (TSLA at $250/share):
- Max position: $10K = 40 shares
- Rolling 3-min volume (active period): ~800K shares
- Participation: 40 / 800,000 = 0.005% — well within constraint
- Rolling 3-min volume (midday thin): ~200K shares
- Participation: 40 / 200,000 = 0.02% — still safe

For a $500K portfolio trading a Tier B name ($100 stock, 100K trades/day):
- Max position: $10K = 100 shares
- Rolling 3-min volume (active period): ~5K shares
- Participation: 100 / 5,000 = 2.0% — **EXCEEDS 0.5% cap → position capped at 25 shares ($2.5K)**
- Rolling 3-min volume (midday thin): ~1.5K shares
- Participation at 25 shares: 25 / 1,500 = 1.7% — **still exceeds → further reduction needed**
- **Tier B names during thin periods may be untradeable at meaningful size.** This is a structural constraint, not an error.

### 11.3 Acceptable Turnover

- **Per symbol**: 2-6 round-trips per day (if persistence supports it; may be lower if threshold T is high)
- **Across portfolio** (10-15 active symbols): 20-60 round-trips per day
- **Annual turnover**: 5,000-15,000× (very high — this is an intraday strategy, turnover is inherently high)
- **Commission sensitivity**: At IBKR tiered pricing (~$0.005/share), commission is ~0.1-0.2 bps on a $100-250 stock. Negligible relative to effective spread (2-5 bps). **The binding cost is effective spread, not commission.**
- **Tax efficiency**: N/A for intraday (no overnight positions, all short-term capital gains regardless). This is an operating cost, not a design constraint.

### 11.4 Implied Constraints on Hypothesis Testing

The above parameters create hard constraints on what constitutes a viable hypothesis:

| Constraint | Derived Requirement |
|-----------|-------------------|
| 2% position size | Edge must survive at small notional (no market impact) |
| 0.5% rolling 3-min participation | Limits position size dynamically — Tier B/C may be untradeable during thin periods |
| 2-6 trades/day/symbol | Event frequency > 2/day is needed for economic viability (H4 exception: 0.5/day if high skew) |
| $200K minimum portfolio | Minimum ~$4K per position (at 2%). At TSLA $250, that's 16 shares. P&L per trade is small — high Sharpe needed |
| Effective spread 2-5 bps | Net edge per trade must exceed ~4-10 bps round-trip |

### 11.5 Capital Utilization Math (post-Round-3 review)

Turnover numbers can create illusions of high returns. The honest math on capital efficiency:

**Scenario: $500K portfolio, Tier A names, 40 round-trips/day**

```
Average position size:     2% × $500K = $10K
Simultaneous positions:    5-8 average
Average capital deployed:  $50K-$80K = 10-16% of NAV
Capital idle:              84-90% of NAV (earning risk-free rate)

Per-trade:
  Gross edge:              5-10 bps
  Round-trip cost:         4-8 bps (effective spread)
  Net edge per trade:      1-3 bps
  Dollar P&L per trade:    $10K × 1-3 bps = $1-$3

Per-day:
  Round-trips:             40
  Daily gross P&L:         40 × $1-$3 = $40-$120
  Daily return on NAV:     0.8-2.4 bps

Per-year (250 days):
  Annual return on NAV:    2-6%
  Annual return on deployed capital: 12-40%
  Strategy Sharpe (est):   1.5-3.0 (low vol, consistent small gains)
```

**Honest interpretation**: This is a LOW ABSOLUTE RETURN, HIGH SHARPE RATIO strategy at $500K scale. The value is in risk-adjusted return (Sharpe), not in absolute percentage. It is most valuable as:
- A sub-strategy in a multi-strategy portfolio (capital-efficient when combined with other uncorrelated strategies)
- A scalability test (if edge survives, increase position size or symbol count)

**Paths to higher absolute return**:
1. More symbols (expand from 10 to 20-30 active) → more trades/day → higher deployment
2. Larger portfolio ($2M+) → same percentage, larger dollar P&L
3. Larger per-trade edge (if Phase 3 finds > 5 bps net) → scales linearly
4. Higher frequency (if persistence supports > 6 trades/day/symbol) → more turnover

**What this strategy is NOT**: A stand-alone high-return vehicle at small scale. It is infrastructure for a flow-aware trading capability that may scale if the edge is real.

### 11.5 Strategic Intent Declaration (post-Round-3 final review)

The expert correctly asks: what is this? The answer must be honest and pre-committed, because it determines how we evaluate success.

**This strategy is:**

1. **A research program first** — the primary output of Phase 1-3 is knowledge: does tradable flow persistence exist in SIP data at horizons compatible with our infrastructure? That knowledge has value regardless of immediate P&L.

2. **Infrastructure proof second** — if H1 survives the empirical gates, we have demonstrated the ability to ingest tick/quote data, classify trade aggressor side, detect flow events, and execute on them. That capability is the foundation for any future microstructure strategy.

3. **A building block in a multi-strategy portfolio third** — at $200K-$500K, this strategy produces $10K-$30K/year if edge holds. That is economically marginal as a standalone vehicle. But as one of 3-5 uncorrelated sub-strategies in a portfolio, it contributes high-Sharpe, low-correlation returns that improve the portfolio's overall risk-adjusted performance.

**This strategy is NOT:**
- A capital deployment vehicle at current scale. $500K deployed at 2-6% does not justify the engineering effort unless it scales.
- A latency-sensitive HFT strategy. We are not competing for queue priority or microsecond execution.
- A permanent fixture. If the edge does not survive Phase 3 testing, the program terminates cleanly. No "almost works" drift.

**The gating question for economic viability**: Is this worth building if the ONLY outcome is a validated 1-3 bps edge on 20-60 trades/day across 10-15 symbols? Answer: YES, if and only if at least one scaling path (more symbols, larger capital, multi-strat integration) is credible. If all scaling paths are blocked after Phase 3, we reassess the entire program's ROI.

This declaration prevents two failure modes:
- **Over-ambition**: expecting standalone fund-level returns from a $500K research portfolio.
- **Under-ambition**: building excellent infrastructure that never produces economic output because nobody committed to scaling.

---

## 12. PORTFOLIO-LEVEL RISK CONTROLS (post-Round-2 review)

Per-hypothesis entry/exit rules (Sections 3, 6) govern individual positions. This section governs the PORTFOLIO — the aggregate behavior of multiple simultaneous positions across symbols.

**Core problem**: 10-15 simultaneous momentum-following positions become a single correlated bet during macro shocks, correlation spikes, or volatility events. Without portfolio-level controls, diversification is illusory.

### 12.1 Aggregate Directional Exposure Cap

- **Maximum net directional exposure**: 10% of portfolio notional long or short at any time. If all active signals point in the same direction and total notional would exceed 10%, the weakest-conviction positions are not opened (or are closed first-in-first-out).
- **Rationale**: Flow signals across multiple symbols may correlate during macro events (e.g., broad market sell-off triggers aggressive selling across all names simultaneously). A 10% cap limits the portfolio's exposure to a directional market move.
- **Measurement**: Sum of signed notional across all open positions / total portfolio NAV. Updated in real-time.

### 12.2 Sector Concentration Limit

- **Maximum same-sector positions**: 3 active positions in the same GICS sector at any time.
- **If a 4th signal fires in the same sector**: Only permitted if the new signal's conviction exceeds the weakest existing same-sector position AND total sector exposure does not exceed 5% of portfolio notional. Otherwise, rejected.
- **Rationale**: Sector-specific events (earnings season clustering, regulatory news, sector rotation) create correlated flow across names in the same sector. Concentration limits prevent sector crowding.

### 12.3 Correlation Monitoring and Cap

- **Real-time rolling correlation**: Compute 20-day rolling pairwise correlation of intraday returns across all active symbols.
- **Eigenvalue spike detection**: Compute the first principal component of the intraday return covariance matrix across active positions. If PC1 explains > 60% of variance, trigger correlation alert.
- **Action on alert**: Reduce ALL position sizes by 50% until PC1 drops below 50%. This is automatic, not discretionary.
- **Rationale**: When correlations spike, effective portfolio risk is far higher than the sum of individual position risks. Reducing size preserves the portfolio during regime transitions.
- **PC1 conditional calibration (post-Round-3 final review, refined Round-3 final audit)**: Flow-based strategies may exhibit the HIGHEST opportunity exactly when correlations spike — sector rotation days, macro shocks drive strong directional flow across many names simultaneously. Automatic size reduction may therefore suppress peak P&L days. However, PC1 > 60% does NOT distinguish between structurally different environments. Therefore, calibrate separately:
  - **PC1 high + VIX low** (VIX < 20 or VIX 1-day change < +2 pts): Likely sector rotation / trend day. Flow persistence may be strongest here. During Phase 3, compute: `P(positive_day | PC1 > 60%, VIX_low)`.
  - **PC1 high + VIX high** (VIX > 25 or VIX 1-day change > +3 pts): Likely liquidity crisis / stress compression. Cross-asset liquidity collapses. Flow signals may fire but fills degrade.
  - **Calibrated response**:
    - If `P(positive_day | PC1 high, VIX low) > 60%`: soften to 25% size reduction during PC1+VIX_low events. Retain 50% reduction during PC1+VIX_high events.
    - If `P(positive_day | PC1 high, VIX low) ≤ 60%`: full 50% reduction for ALL PC1 > 60% events regardless of VIX.
    - PC1 high + VIX high: ALWAYS 50% reduction, non-negotiable. Tail control must be orthogonal to signal performance. Never allow empirical P(positive | PC1 high) alone to override systemic fragility constraints.
  - This is calibrated once during Phase 3 backtesting and frozen for live deployment. Not adaptive in real-time (would be prone to overfitting).
  - **Hard floor**: Even in the softened regime, maximum aggregate directional exposure during PC1 > 60% is capped at 7.5% of NAV (75% of the normal 10% cap). This ensures tail protection is never fully disabled.

### 12.4 Trade Throttle

- **Maximum new entries per hour**: 8 across the entire portfolio.
- **Maximum round-trips per day**: 60 across the entire portfolio.
- **Priority under throttle**: When the throttle is binding, only the highest-conviction signals are permitted (H1+H2 or H1+H3 confirmations only; H1-alone and H5-alone are deferred).
- **Rationale**: Overlapping signals during volatile periods cause micro-impact stacking. Spread widens exactly when we trade most. The throttle prevents overtrading in adverse conditions.

### 12.5 Dynamic Hedge Overlay

- **Sector ETF hedge**: When 3 positions from the same sector are active, hedge with the corresponding sector ETF (XLK, XLF, XLE, etc.) at 50% of total sector notional. This neutralizes sector beta while preserving alpha-specific exposure.
- **Index hedge**: When aggregate portfolio beta to SPY (estimated from rolling 20-day regression) exceeds 1.5, hedge with SPY short at the excess beta amount. Remove hedge when beta drops below 1.0.
- **Cost**: Hedging costs money (spread on ETF/index). The hedge is only justified if the portfolio has > 5 active positions (below that, individual stop-losses are sufficient).
- **Implementation note**: Hedges are passive (held until trigger reverses). They are NOT alpha trades — they are portfolio insurance.

### 12.6 Position Sizing Derivation (post-Round-2 review, revised Round-3 final audit)

Position sizing uses a **volatility-targeted drawdown control** framework, NOT pure Kelly optimization. Kelly provides a theoretical ceiling, but operational sizing is governed by realized risk.

**Sizing framework (two layers)**:

**Layer 1: Volatility-targeted base size**
```
base_size = (target_daily_vol × portfolio_NAV) / (realized_per_trade_vol × price)
```
Where:
- `target_daily_vol` = maximum acceptable daily P&L standard deviation per position. Set to 0.15% of NAV (i.e., $300 on $200K). This is a drawdown control parameter, not an edge optimization parameter.
- `realized_per_trade_vol` = rolling standard deviation of per-trade dollar returns for this symbol, computed over trailing 30 trades.

**Layer 2: Kelly ceiling (hard cap, never operational driver)**
```
kelly_ceiling = 0.25 × (edge_estimate / variance_estimate) × portfolio_NAV
```

**Combined sizing**:
```
position_size = min(
    base_size,                                                    # vol-targeted drawdown control
    kelly_ceiling,                                                # quarter-Kelly hard cap
    portfolio_NAV × 0.02,                                         # 2% max per position
    rolling_3min_volume × participation_cap × price               # dynamic participation cap
)
```

**Why vol-targeted, not Kelly-driven (post-Round-3 final audit)**: In thin-edge environments (1-3 bps), edge volatility dominates edge mean. Kelly assumes stationary mean and variance — we have neither. Variance estimation error alone exceeds the edge magnitude. A volatility-targeted model sizes off REALIZED risk (which we can measure accurately) rather than ESTIMATED edge (which we cannot). Kelly serves as a ceiling to prevent oversizing when vol is temporarily low, but never as the primary driver.

Where:
- `edge_estimate` = rolling median of net return (after effective_spread + 0.5 bp estimation buffer) for the triggering hypothesis, from the most recent N trades. Used ONLY for the Kelly ceiling and for the entry gate (if negative over trailing 20 trades, sizing collapses to minimum lot).
- `variance_estimate` = rolling variance of per-trade returns for the triggering hypothesis. Used for Kelly ceiling.
- Both estimates are updated daily from realized trade outcomes (not from backtest parameters).
- `rolling_3min_volume` = trailing 3-minute traded volume for the specific symbol at the moment of entry (not daily ADV). This measures CURRENT liquidity, not average liquidity.
- `participation_cap` = 0.5% when `spread_bps` ≤ median; 0.25% when `spread_bps` > median + 1σ (halved during wide spread regimes to avoid impactful entry during thin conditions).

**Real-time slippage feedback throttle (post-Round-3 final review)**: The participation cap alone does not guarantee acceptable impact. In high-elasticity states, even small participation can cause disproportionate slippage. Therefore, in addition to the static participation cap, a live feedback throttle operates continuously:

```
slippage_ratio = realized_slippage_per_share / expected_slippage_per_share
```

**Two-speed feedback (post-Round-3 final audit)**: In thin-edge systems, 10 fills may already represent material P&L damage during rapid adverse selection. A single-speed throttle reacts too slowly. Therefore, two concurrent windows:

**Fast defense (5-fill window)**:
- `slippage_ratio_fast > 1.3` → participation cap halves immediately for next 3 minutes
- `slippage_ratio_fast > 1.8` → no new entries for that symbol for 5 minutes
- Purpose: rapid response to sudden regime shifts (e.g., news-driven liquidity withdrawal)

**Slow confirmation (20-fill window)**:
- `slippage_ratio_slow > 1.2` → participation cap halves for next 10 minutes
- `slippage_ratio_slow > 1.5` → participation cap quarters AND no new entries for that symbol for 15 minutes
- Purpose: detect persistent degradation that the fast window might miss as noise

- Expected slippage is derived from the trailing 30-trade median for that symbol+liquidity tier
- Both windows operate concurrently; the MORE restrictive action applies

This catches degradation BEFORE the kill-switch triggers. Kill switches (Section 13) are last-resort binary actions. The two-speed throttle provides both fast protection against sudden shocks and stable detection of persistent drift. Thin-edge systems die from delay, not from magnitude — the fast window ensures we don't accumulate 10 fills of damage before responding.

**Why rolling 3-min volume, not daily ADV (post-Round-3 review)**: Daily ADV averages over the entire session, masking the intraday volume U-shape. At midday, actual 3-minute volume may be 50% of the session average. A 0.5% daily ADV cap that looks safe could represent 4-8% of actual bucket volume during thin periods. At that participation level, we are no longer riding flow — we ARE the flow. The rolling 3-min cap ensures participation is measured against the liquidity available RIGHT NOW.

**If realized edge turns negative over trailing 20 trades**: sizing collapses to minimum lot size until edge recovery is confirmed. This is automatic edge decay detection at the sizing level.

**Fractional Kelly cap (post-Round-3 final review)**: For thin-edge strategies (1-3 bps net), full Kelly is mathematically optimal only with perfect knowledge of edge and variance distributions — which we never have. Estimation error in both parameters is large relative to the edge itself. Therefore: **Kelly fraction is permanently capped at 25% of theoretical**, regardless of regime, confidence, or signal strength. This is non-negotiable.

The mathematical justification: if edge estimation error is ±50% (realistic for 20-trade rolling windows), full Kelly has a ~25% probability of oversizing by 2x, which on a 2 bps edge means the expected cost from sizing error exceeds the expected gain. Quarter-Kelly reduces this risk to negligible levels while retaining ~75% of the growth rate. For thin-edge strategies, survival dominates growth.

**Regime-conditional sizing (post-Round-3 review)**: Rolling edge estimates over 20-trade windows (3-10 days per symbol) may lag regime shifts. To prevent pro-cyclical Kelly sizing:
- If the current volatility regime (from ADS §2 regime vector) differs from the regime during which the trailing 20 trades were executed, apply a 50% regime discount to the Kelly fraction.
- If the current regime is "high-vol" and the trailing edge was measured during "low-vol," the Kelly fraction is halved until 10+ trades in the current regime establish a new baseline.
- Edge and variance estimates are segmented by regime: maintain separate running estimates for low-vol, mid-vol, and high-vol regimes. Use the estimate from the CURRENT regime, not the pooled estimate.

---

## 13. KILL-SWITCH RULES & MONITORING (post-Round-2 review)

Hard, automated, non-discretionary. These rules override ALL entry signals.

### 13.1 Per-Symbol Kill Switches

| Trigger | Action | Reset Condition |
|---------|--------|----------------|
| 3 consecutive losses on same symbol within 60 minutes | Disable symbol for remainder of day | Next trading day |
| Realized effective_spread > 2× trailing 5-day median for that symbol | Disable symbol until spread normalizes | spread returns below 1.5× median for 10 consecutive minutes |
| Symbol halted (LULD or regulatory) | Close position at first available price; disable symbol for 15 minutes post-resumption | 15 minutes post-resumption with normal spread |
| Symbol's intraday P&L < -0.5% of portfolio NAV | Disable symbol for remainder of day | Next trading day |

### 13.2 Per-Strategy Kill Switches

| Trigger | Action | Reset Condition |
|---------|--------|----------------|
| Portfolio net drawdown > 1% of NAV for the day | Disable ALL new entries for remainder of day | Next trading day |
| Cumulative P&L for current hour < -0.3% of NAV | Disable ALL new entries for 30 minutes | 30-minute cooldown |
| Rolling 5-day Sharpe < -1.0 | Disable strategy entirely pending manual review | Manual override after investigation |
| 5 consecutive losing trades across any symbols | Reduce all position sizes by 50% for next 10 trades | 3 consecutive winning trades restores full sizing |
| Realized slippage > 120% of modeled for 20 consecutive trades (across all symbols) | Reduce ALL position sizes by 50% | Slippage returns below 110% of modeled for 10 trades |
| Realized slippage > 150% of modeled for 30 consecutive trades | Disable ALL entries for remainder of day | Next trading day |

### 13.3 Market-Wide Kill Switches

| Trigger | Action | Reset Condition |
|---------|--------|----------------|
| VIX > 40 or VIX jumps > 5 points in 30 minutes | Disable ALL entries; hold existing positions only | VIX returns below 35 for 30 minutes |
| 5+ symbols in universe simultaneously halted | Disable ALL entries; flatten weakest-conviction positions | Halted symbols resume; wait 15 minutes |
| Average bid-ask spread across universe > 3× trailing median | Disable ALL entries | Spread normalizes to < 2× median |
| Market-wide circuit breaker (Level 1/2/3) | Flatten ALL positions at first available price | Manual restart only |

### 13.4 Monitoring Dashboard Requirements

The following must be computed and displayed in real-time. Drift beyond thresholds triggers alerts.

**Per-Trade Metrics** (updated after each trade):
- Realized net return vs predicted net return (from Phase 3 calibration)
- Realized effective_spread vs expected effective_spread
- Realized holding period vs expected holding period
- Exit trigger type (thesis invalidation / emergency stop / time circuit-breaker / EOD)

**Portfolio Metrics** (updated every minute):
- Aggregate directional exposure (long vs short notional)
- Sector concentration (positions per GICS sector)
- Cross-sectional correlation (PC1 explanatory %)
- Turnover rate (round-trips today / target)
- Cumulative intraday P&L curve

**Data Integrity Metrics (post-Round-3 review)** (updated every minute):
- `quote_staleness`: time since last NBBO update at each trade timestamp. Median and P95 per symbol. If P95 > 100ms, NBBO alignment is degraded.
- `midpoint_trade_fraction`: % of trades classified as indeterminate (at midpoint). Rolling 30-min window. Spike above trailing mean + 2σ indicates internalization regime shift.
- `trade_quote_desync_rate`: % of trades where the matched NBBO quote timestamp is > 50ms older than the trade timestamp. If > 10%, classification quality is degraded.
- **Gate**: If `trade_quote_desync_rate` > 15% for 5 consecutive minutes → disable trading for that symbol until rate drops below 10%. The strategy CANNOT operate with stale quotes — it misclassifies aggressor direction, which corrupts the imbalance signal at the foundation.
- **Classification confidence metric**: For each volume bucket, report the fraction of signed volume that came from unambiguous classifications (trade_price clearly above or below midpoint). If < 60% of bucket volume is unambiguously classified, flag the bucket as low-confidence. Thesis-invalidation and entry decisions should down-weight low-confidence buckets.
- **Trade reporting delay distribution (post-Round-3 final review)**: Polygon tick feeds may show microsecond timestamps, but underlying reporting can cluster during volatility. Monitor:
  - Inter-trade timestamp intervals: compute rolling CV of consecutive trade timestamp gaps. CV > 3.0 indicates bursty reporting (timestamps bunched, not uniformly spaced).
  - Timestamp monotonicity violations: count instances where `trade_timestamp[i+1] < trade_timestamp[i]` per minute. Should be 0 in normal operation; >0 indicates SIP sequencing issues.
  - Reporting backlog detection: if >50 trades arrive within a 10ms window AND those trades span >500ms of exchange timestamps, the SIP is delivering a backlog. Flag all affected buckets as potentially misordered.
  - **Impact**: During reporting backlogs, trade signing via Lee-Ready is unreliable (quotes and trades are misaligned in time). Imbalance calculations in affected buckets should be excluded from signal computation. If >5% of daily buckets are affected, escalate to data quality review.
- **Tick-rule fallback rate (post-Round-3 final audit)**: Lee-Ready classification uses the NBBO midpoint as the primary classifier. When the trade price equals the midpoint, the algorithm falls back to the tick rule (comparing to previous trade price). Track daily:
  - `tick_rule_fallback_pct`: % of trades classified by tick rule rather than Lee-Ready midpoint comparison. If this exceeds 15-20%, the imbalance signal becomes structurally less reliable (tick rule has lower accuracy than midpoint comparison, especially during fast markets).
  - `quote_trade_mismatch_pct`: % of trades where no contemporaneous NBBO quote can be matched within 50ms. High mismatch forces tick-rule fallback and degrades classification quality.
  - **Daily log**: Both metrics logged per symbol per day. If `tick_rule_fallback_pct` > 20% for any symbol for 3 consecutive days → trigger data quality review for that symbol. Potential causes: excessive internalization (midpoint-priced dark pool prints), exchange clock drift vs SIP, or stale NBBO during fast markets.

**Edge Decay Detection** (updated daily):
- Rolling 20-trade mean net return per hypothesis (H1, H2, H3, H4)
- Rolling 20-trade Sharpe per hypothesis
- Rolling 20-day win rate
- Classification quality: signed_volume → 1-min return correlation (monthly)
- Persistence half-life rolling estimate (monthly)

**Alert Thresholds**:
- Realized edge < 50% of calibrated edge for 5 consecutive trading days → manual review
- Realized slippage > 120% of modeled for 3 consecutive days → manual review (for thin-edge strategies, 30% persistent slippage drift already erodes majority of edge)
- Persistence half-life decreases by > 30% from calibration → hypothesis may be degraded
- Lee-Ready classification correlation drops below 0.03 → data quality issue

### 13.5 Explicit Cost Hurdle Per Tier (post-Round-2 review)

The expert correctly demands quantification of the economic threshold:

| Tier | Typical Effective Spread (per side) | Round-Trip Cost | Required Gross Edge (2× cost) | Required Net Edge |
|------|-------------------------------------|-----------------|-------------------------------|-------------------|
| A: Mega-cap | 1-3 bps | 2-6 bps | 4-12 bps | > 0 after spread |
| B: High-cap | 3-8 bps | 6-16 bps | 12-32 bps | > 0 after spread |
| C: Mid-cap | 5-15 bps | 10-30 bps | 20-60 bps | > 0 after spread |

**Honest assessment**: Academic benchmarks (Cont et al. 2014) suggest 5-15 bps gross predictability at 5-minute horizons in liquid names using order flow imbalance. After effective spread costs, the net edge for Tier A is marginal (0-5 bps per trade). For Tier B, gross edge may be larger (15-30 bps) but costs are also higher. **The economic viability of this program is uncertain and must be determined empirically.** This is not a weakness of the hypothesis — it is the honest state of knowledge. Phase 3 determines whether the edge exists in practice.

---

## 14. PROMOTION CRITERIA — FROM RESEARCH TO PRODUCTION (post-Round-3 final audit)

This section defines the explicit, pre-committed criteria for promoting H1 from research to production alpha module. These thresholds are frozen before Phase 1 begins.

### 14.1 Promotion Gate (ALL must hold)

| # | Criterion | Threshold | Measurement |
|---|-----------|-----------|-------------|
| P1 | Net post-cost edge | ≥ 1.8 bp point estimate, lower 95% CI > 0.5 bp | Phase 3 OOS, including 0.5 bp estimation error buffer |
| P2 | Symbol stability | Edge positive on ≥ 60% of target universe symbols | Phase 3 OOS per-symbol results |
| P3 | Participation robustness | No edge collapse under simulated 1% participation | Phase 4 endogenous decay test |
| P4 | Shadow-mode validation | Shadow continuation ≥ 90% of backtest continuation | Phase 4 shadow-mode (2-4 weeks live quotes, no fills) |
| P5 | Regime stability | Edge positive in ≥ 2 of 3 volatility regimes (low/mid/high) | Phase 3 regime-segmented analysis |
| P6 | Time-of-day breadth | Edge exists in ≥ 2 of 3 intraday regimes | Phase 3 heatmap time-of-day stratification |
| P7 | Cost model accuracy | Backtest slippage within 120% of modeled on ≥ 80% of trades | Phase 3 + Phase 5 replay |

### 14.2 Conditional Promotion (infrastructure useful, standalone alpha insufficient)

If Phase 3 produces:
- 1.0-1.7 bp net edge
- Highly regime-dependent (passes in 1 of 3 regimes only)
- Sensitive to small friction increases

**Decision**: Keep the infrastructure. Archive the signal as a research finding. Do NOT promote to production. Reassess if:
- Data quality improves (direct exchange feeds, better classification)
- Additional uncorrelated hypotheses (H2-H5) provide combinatorial edge
- Capital scales to make marginal edge economically meaningful

### 14.3 Termination Gate

If Phase 3 produces:
- < 1.0 bp net edge across all symbols
- OR lower CI bound ≤ 0 bp
- OR edge exists on < 40% of symbols
- OR micro-burst contingency also fails (Section 8.3.1)

**Decision**: Terminate the flow alpha program. No drift. No narrative rescue. The infrastructure (tick ingestion, Lee-Ready, volume-clock) has value for future research programs, but THIS hypothesis is dead.

### 14.4 Required Sample Size for Statistical Confidence

For a 2 bp edge with 10 bp per-trade standard deviation (realistic for intraday flow):
- Required N for 95% CI width < 2 bp: N ≈ (2 × 1.96 × 10 / 2)² ≈ 384 events per symbol
- At 3 events/day/symbol: ~130 trading days (~6 months) per symbol
- At 10 symbols: ~3,840 total events (pooled analysis with symbol fixed effects)

This confirms that the 6-month historical data requirement (Phase 1) and the Phase 3 testing period are appropriately sized. Shorter periods risk terminating on sampling noise (per R1 CI-width criterion).

### 14.5 Economic Decision Framework

The expert correctly asks: is this worth the engineering?

**Answer**: The program is justified if and only if at least ONE of these conditions holds after Phase 3:

1. **Standalone viability**: Net edge ≥ 2.0 bp, ≥ 10 symbols, ≥ 30 round-trips/day → ~$10K-$30K/year at $500K → viable as one leg of a multi-strategy portfolio
2. **Scaling path credible**: Edge survives simulated 1% participation → room to scale capital from $500K to $2M+ → absolute return becomes meaningful
3. **Infrastructure ROI**: Tick/quote ingestion pipeline, Lee-Ready classifier, volume-clock engine become reusable components for future strategies → engineering cost is amortized

If NONE of these hold → the rational decision is: terminate. The engineering is elegant but economically inconsequential.

This decision will be made explicitly at the end of Phase 5, documented, and not revisited without new evidence.

---

**Last Updated**: February 14, 2026
**Status**: FINAL v1.5 — Hypothesis design phase SEALED. Incorporating 3 rounds of external quant critique + 1 final audit (statistical precision, economic realism, operational fragility). All rejection criteria, promotion criteria, and termination gates are frozen.

**The empirical question (sharpened)**: Does tradable continuation survive effective spread + adverse selection + participation impact + estimation error buffer? Not whether imbalance predicts continuation — but whether continuation exceeds ALL friction layers simultaneously.

**Next Step**: BEGIN PHASE 1 (Data Ingestion) + PHASE 2 (Foundation Diagnostics). All criteria (Sections 8.3, 14.1, 14.3) are frozen before testing. If H1 survives, promote per Section 14.1. If it doesn't, terminate per Section 14.3 or pivot per Section 8.3.1. No drift permitted.
