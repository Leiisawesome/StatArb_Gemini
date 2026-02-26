# Momentum Signal Intent Resolution Plan

**Goal**: Make signal intent **effective**, **edge-rigorous**, and **at the right time**.

**Scope**: Pre-ADS signal generation (Level 1–3 composite logic, state machine, confirmation hierarchy). ADS gates (SMS, ERAR) and downstream risk/execution remain unchanged.

**Principle**: Problem → Conjecture → Criticism → Implementation → Test (scientific process).

---

## Phase 0: Lock the Causal Hypothesis (Before Any Code)

### 0.1 Choose One Primary Mechanism

Pick **one** causal story and design around it. Options:

| Option | Mechanism | Signal Logic | Timing Implication |
|--------|-----------|--------------|--------------------|
| **A** | Underreaction to information | Momentum acceleration + flow confirmation | Enter when acceleration is *increasing*, not when already extended |
| **B** | Breakout from consolidation | Vol compression → expansion + volume surge | Enter at breakout *initiation*, not chase |
| **C** | Flow-driven continuation | Order flow imbalance + price alignment | Enter when flow and price agree and flow is *recent* |

**Recommendation**: Option A (underreaction) or B (breakout) — both have clearer "right time" definitions than the current composite confluence.

**Deliverable**: One-page hypothesis document stating:
- Causal mechanism
- Why it produces edge
- What "right time" means (operational definition)
- What invalidates the thesis immediately

### 0.2 Unify Entry Paths

- **Current**: Two disjoint paths (state machine vs composite) selected by config.
- **Target**: Single path driven by the chosen hypothesis.
  - If A (underreaction): Composite path, but refactored around acceleration/flow.
  - If B (breakout): State machine path, but with explicit causal checks.
  - If C (flow): New path; requires flow data (BVC, OFI proxy).

**Deliverable**: Architecture decision — one entry path, one hypothesis.

---

## Phase 1: Statistical Rigor (Indicator Construction)

### 1.1 Factor Decomposition (Replace Equal-Weight Composite)

**Problem**: 10 indicators, equal weights, many correlated (momentum_10/20/50, roc_10).

**Resolution**:

1. **Correlation analysis**: Compute pairwise correlations of all 10 inputs over a representative sample (e.g., 252 days × N symbols). Identify clusters.
2. **Dimensionality reduction**:
   - **Option 1**: PCA on z-scored inputs; use top 2–3 PCs as factors. Weights are data-driven, not arbitrary.
   - **Option 2**: IC-based weighting — compute rolling information coefficient of each indicator vs. forward return; weight by |IC|.
   - **Option 3**: Keep 3–4 *theoretically distinct* factors: (a) momentum, (b) trend strength, (c) flow/volume, (d) volatility regime. Drop redundant indicators.
3. **Composite construction**: Multiplicative or min-gate across factors (ADS-compliant), not linear sum.

**Deliverable**: New `composite_z` / `composite_pct` spec with explicit factor list and weights (or PCA loadings). Fallback when data is insufficient.

### 1.2 Threshold Calibration (Out-of-Sample)

**Problem**: `composite_z_entry = 0.8`, `composite_pct_entry = 65` — no empirical basis.

**Resolution**:

1. **Train period**: Use 60% of available history (e.g., first 150 days of 250).
2. **Grid search**: Over (z_threshold, pct_threshold) with step sizes (0.1, 5). Metric: Sharpe or risk-adjusted return, not raw PnL.
3. **Validation period**: Remaining 40%. Apply best thresholds. Report:
   - In-sample vs out-of-sample Sharpe
   - Threshold stability (sensitivity analysis)
4. **Regime splits**: Repeat calibration in low-vol vs high-vol regimes. If optimal thresholds differ >20%, use regime-adaptive thresholds (already partially in place).

**Deliverable**: Calibrated thresholds with confidence intervals. Document in config with `_calibrated` suffix and date.

### 1.3 Inflection / Acceleration Definition

**Problem**: "Inflection boost" reduces thresholds when "inflection detected" — definition is vague.

**Resolution**:

1. **Operational definition**: Inflection = (a) `composite_acceleration > 0` and `composite_velocity` sign matches direction, OR (b) momentum_10 crossed zero in last 3 bars with volume expansion.
2. **No threshold reduction**: Instead of lowering z/pct thresholds, use inflection as a *required* condition for early entry. If no inflection, require higher thresholds (current behavior). This inverts the logic: inflection = permission to enter at lower bar, not permission to use weaker signals.
3. **Empirical check**: Backtest with/without inflection filter. Does it improve Sharpe or reduce drawdown?

**Deliverable**: Clear inflection spec. Remove arbitrary 80%/90% multiplier.

---

## Phase 2: Right Time (Timing Discipline)

### 2.1 Define "Right Time" Operationally

For the chosen hypothesis, specify:

| Hypothesis | Right Time | Wrong Time |
|------------|------------|------------|
| Underreaction | Acceleration increasing, flow confirming, not yet extended | Momentum already high, price far from MA, chasing |
| Breakout | First bar(s) after breakout with volume | Late breakout, already extended |
| Flow | Flow and price aligned, flow is recent (not stale) | Stale flow, price already moved |

**Resolution**: Add explicit "too late" / "chase" filters:

- **Extension filter** (already exists partially): `(close - MA) / ATR > max_extension_atr` → block. Ensure this is applied consistently.
- **Acceleration filter**: For underreaction, require `composite_acceleration > 0` at entry. Block when `composite_acceleration < -0.2` (exhaustion).
- **Bar-since-trigger**: For breakout, allow entry only within first N bars after trigger (e.g., N=3). Beyond that, treat as chase.

**Deliverable**: "Right time" checklist in code comments and config. Each entry must pass.

### 2.2 ORB and Time-of-Day

**Current**: ORB blocks first 15 minutes. No other time filters.

**Resolution**:

1. **ORB**: Keep. Document rationale (overnight imbalance clearing).
2. **Power hour / lunch**: Optional filters — e.g., reduce size or block 11:45–13:00 if evidence shows lower edge. Calibrate with time-of-day PnL breakdown.
3. **End-of-day**: Already handled by EOD liquidation. No change.

**Deliverable**: Time-of-day analysis report. Config flags for optional filters.

---

## Phase 3: Cross-Sectional Component (Optional but High-Impact)

### 3.1 Relative Strength

**Problem**: Pure time-series. No cross-sectional ranking.

**Resolution**:

1. **Universe**: Use existing symbol list (e.g., TSLA in smoke test; expand to 5–10 names for proper cross-section).
2. **Rank**: Each bar, compute `composite_z` (or new factor score) for all symbols. Rank 0–1.
3. **Entry condition**: Only enter when symbol is in top quartile (long) or bottom quartile (short). This filters "strongest in universe" vs "strong in isolation."
4. **Data requirement**: Need multi-symbol data in same bar. Pipeline may need to pass universe-level context.

**Deliverable**: Cross-sectional rank feature. Gate: `rank >= 0.75` for long, `rank <= 0.25` for short. Config flag `enable_cross_sectional_rank`.

---

## Phase 4: Confirmation Hierarchy (Causal Alignment)

### 4.1 Align Confirmation to Hypothesis

**Current**: Volume expansion, price structure, volatility breakout — ad hoc hierarchy.

**Resolution**:

1. **Map to hypothesis**:
   - Underreaction: Flow confirmation (buy_volume_pct, volume_ratio) is primary. Price structure secondary.
   - Breakout: Volume surge is primary. Volatility expansion secondary. Price structure (higher lows) is setup, not confirmation.
2. **Single primary confirmation**: Define one confirmation type that *must* be present for the chosen hypothesis. Others are optional boosts.
3. **Calibrate thresholds**: `volume_ratio > X`, `buy_volume_pct > Y` — derive from data (e.g., median volume_ratio on profitable entries vs unprofitable).

**Deliverable**: Confirmation spec aligned to hypothesis. Remove "unconfirmed requires 2x threshold" heuristic; replace with "no primary confirmation → no entry."

---

## Phase 5: Validation Discipline

### 5.1 Pre-Implementation Checks

Before merging any change:

1. **Unit tests**: New factor construction, threshold logic, inflection definition.
2. **Smoke test**: Must pass. No regression in pipeline funnel.
3. **Backtest**: Same period (Dec 16–20, 2024) + extended period if available. Report:
   - Trade count, win rate, Sharpe, max DD
   - Comparison to baseline (current logic)

### 5.2 Post-Implementation Monitoring

1. **Sensitivity**: Vary thresholds ±10%. Document impact on Sharpe.
2. **Regime stability**: Performance in low-vol vs high-vol periods.
3. **Decay check**: If 30+ days of live/paper data, test for edge decay (rolling Sharpe degradation).

---

## Execution Order

| Phase | Dependency | Effort | Impact |
|-------|-------------|--------|--------|
| 0 | None | 1–2 days | Critical — locks direction |
| 1 | Phase 0 | 3–5 days | High — fixes statistical flaws |
| 2 | Phase 0 | 1–2 days | High — fixes timing |
| 3 | Phase 0, 1 | 2–3 days | Medium–High (needs multi-symbol) |
| 4 | Phase 0 | 1–2 days | Medium |
| 5 | All | Ongoing | Required |

**Recommended sequence**: 0 → 1 → 2 → 4 → 5. Phase 3 (cross-sectional) can follow once multi-symbol pipeline is stable.

---

## Success Criteria

Signal intent is **effective** when:
- Out-of-sample Sharpe ≥ 0.5 (or positive and stable over 20+ trades)
- Win rate and payoff structure are consistent with the causal hypothesis

Signal intent is **edge-rigorous** when:
- Factor construction has explicit justification (PCA, IC, or theory)
- Thresholds are calibrated with train/validation split
- No arbitrary magic numbers without documentation

Signal intent is **at the right time** when:
- "Right time" is operationally defined and enforced
- Chase/extension filters block late entries
- Time-of-day filters (if any) are evidence-based

---

## Round 2: Deeper Review (Missed Spots & Hotspot Improvements)

### A. Missed Spots

#### A1. ADS Gate Recalibration (Downstream Ripple)

**Miss**: Plan states "ADS gates remain unchanged." Changing signal distribution (fewer, higher-quality signals) can make existing SMS tau and ERAR gamma mis-calibrated.

**Add**: After Phase 1–4, add **Phase 5.0: ADS Gate Revalidation**:
- Re-run backtest with new signal logic. Inspect SMS scores at entry and ERAR values.
- If signal quality distribution has shifted, consider minor tau/gamma adjustment (e.g., ±0.05). Document any change.
- Exit logic (DIRECTION_REVERSAL, ALIGNMENT_BREAKDOWN) uses `composite_z` — if we change its construction, verify these exits still fire correctly. May need to add `composite_z_legacy` for exit compatibility during transition.

#### A2. Statistical Power & Minimum Data Requirements

**Miss**: Phase 1.2 assumes 250 days of 1-min bars. Smoke test has 5 days. With ~1–2 trades/day, train set has ~10–20 trades — insufficient for reliable grid search.

**Add**:
- **Minimum data**: Require ≥ 100 trades in train period. If unavailable, use **Option 2**: theory-based thresholds (e.g., from literature) + sensitivity analysis instead of grid search.
- **Multiple comparisons**: Grid search over K thresholds = multiple testing. Use Bonferroni or single validation set; report confidence intervals, not point estimates.
- **Overfitting guard**: When N_trades < 50, prefer simpler models (fewer factors, coarser grid). Add explicit "sparse data" branch in Phase 1.2.

#### A3. Data Availability & Fallbacks

**Miss**: Plan assumes `buy_volume_pct`, `volume_ratio`, `composite_z` exist. Pipeline may not provide them consistently (warm-up, missing columns, different data sources).

**Add**:
- **Pre-Phase 0**: Audit pipeline — which columns are guaranteed for momentum strategy? Document warm-up bars (e.g., 50 for momentum_50).
- **Fallback spec**: For each new logic block, define: "If X missing → block entry" vs "If X missing → use fallback Y". Align with ADS § "Missing data: every gate must define fallback."
- **Confirmation data**: `buy_volume_pct` requires BVC/Lee-Ready. In 1-min bar pipeline, is it a proxy (e.g., close vs open heuristic)? If unreliable, Option C (flow) may be infeasible; Option A/B preferred.

#### A4. Exit Logic Alignment

**Miss**: Exits (DIRECTION_REVERSAL, ALIGNMENT_BREAKDOWN) consume `composite_z` and momentum_10/20. If we change their construction, exit triggers may misfire.

**Add**:
- **Exit compatibility check**: After Phase 1.1 (new composite), run backtest and inspect: Do exits still trigger when thesis is invalid? Do they trigger too early (false positive)?
- **Transition period**: Consider keeping `composite_z_legacy` for exit logic until new composite is validated. Or: explicitly update exit formulas to use new factors.

#### A5. Regime Vector Consistency

**Miss**: Regime-adaptive thresholds (R.volatility, R.trend, R.liquidity) come from regime detector. If regime is stale or misaligned with momentum hypothesis, adjustments can hurt.

**Add**:
- **Regime audit**: Document regime detector source and update frequency. Is it bar-synchronous or lagged?
- **Regime override**: If regime confidence < 0.5, use neutral thresholds (no adjustment). Avoid amplifying noise.

#### A6. Cost Structure of "Right Time"

**Miss**: Early vs late entries may have different slippage/cost. Early breakout may face wider spread; late chase may face worse fill.

**Add**:
- **Cost awareness**: In Phase 2, add a check: "If estimated spread_bps > 2× baseline, block". ERAR already models cost; ensure "right time" filters don't force entries into high-cost regimes.
- **Optional**: Time-of-day cost analysis — are certain hours systematically more expensive?

#### A7. Operational Safety & Rollback

**Miss**: No feature flag or rollback path if new logic is worse.

**Add**:
- **Feature flag**: `enable_momentum_v2_signal` (or similar). When False, use current logic. When True, use new logic. Allows A/B comparison and instant rollback.
- **Baseline capture**: Before any change, capture baseline metrics (Sharpe, trade count, win rate) for the same period. Store in `results/baseline_momentum_*.json`.

#### A8. Hypothesis Selection Criteria

**Miss**: Phase 0 says "choose one" but doesn't specify how to decide.

**Add**:
- **Decision framework**:
  1. **Data availability**: Does pipeline provide required inputs? (A/B: yes; C: needs tick/BVC)
  2. **Empirical support**: Does any option have prior backtest evidence in this codebase?
  3. **Architectural fit**: Which path (state machine vs composite) has less refactor? B favors state machine; A favors composite.
  4. **External review**: If available, get hypothesis choice validated by external quant before locking.

---

### B. Hotspot Improvements

#### B1. Phase 0 — Decision Framework (Strengthen)

**Current**: "Pick one" with table. Vague.

**Improvement**:
- Add explicit decision matrix (see A8).
- Add **rejection criteria** for each option: e.g., "Reject A if acceleration data is noisy (check rolling std of composite_acceleration)."
- Add **one-page hypothesis** template: mechanism, edge source, right time, invalidation, data requirements.

#### B2. Phase 1.1 — Factor Construction (Look-Ahead & Bias)

**Current**: PCA and IC options. IC is supervised.

**Improvement**:
- **IC look-ahead**: When computing IC(indicator, forward_return), use forward return over *next* N bars. Ensure no overlap with indicator computation window. Document: "Forward return = close[t+1] / close[t] - 1 over next 5 bars" (or similar).
- **PCA**: Unsupervised — may not align with returns. Add: "PCA factors are for dimensionality reduction only; final signal alignment with returns still requires empirical calibration."
- **Option 3 (theory-based)**: Add explicit factor definitions and rationale. E.g., "Momentum factor = mean(momentum_10, momentum_20, momentum_50) — captures multi-horizon trend."

#### B3. Phase 1.2 — Calibration (Sparse Data & Overfitting)

**Current**: 60/40 split, grid search.

**Improvement**:
- **Sparse-data branch**: If train trades < 100: (a) skip grid search; (b) use theory-based thresholds (e.g., composite_z > 0.7 from literature); (c) run sensitivity ±15% and report.
- **Regularization**: Use coarser grid (e.g., z_step=0.2, pct_step=10) when data is sparse. Avoid overfitting to noise.
- **Walk-forward**: If data ≥ 1 year, consider walk-forward calibration (train on months 1–6, validate on 7, roll forward). More robust than single split.

#### B4. Phase 2 — Code Location Mapping

**Current**: "Add explicit filters" — conceptual.

**Improvement**:
- **Code map**: Add table mapping each "right time" filter to the exact method/location in `enhanced_momentum.py`:
  | Filter | Method | Location |
  |--------|--------|-----------|
  | Extension | `_check_composite_entry` or state machine | `max_extension_atr` |
  | Acceleration | `_passes_transition_supervisor_gate` or new | TBD |
  | Bar-since-trigger | State machine `evaluate()` | `breakout_acceleration` branch |
- Ensures implementation traceability.

#### B5. Phase 3 — Pipeline Architecture Check

**Current**: "Need multi-symbol data in same bar."

**Improvement**:
- **Pre-Phase 3 check**: Verify pipeline can pass `universe_df` (all symbols, same timestamp) to strategy. If not, Phase 3 requires pipeline change first.

#### B6. Phase 4 — Confirmation Data Reliability

**Current**: "Flow confirmation primary for underreaction."

**Improvement**:
- **Data audit**: Before Phase 4, confirm `buy_volume_pct` source. Is it BVC from tick data, or a bar-level proxy (e.g., (close - open) / (high - low) heuristic)?
- **If proxy**: Document that proxy is imperfect; consider lowering confidence when flow confirmation is primary.

#### B7. Success Criteria — Graduated Milestones

**Current**: Sharpe ≥ 0.5. Current is -4.43 — huge jump.

**Improvement**:
- **Milestone 1**: Sharpe > 0 (positive risk-adjusted return). Must pass before proceeding.
- **Milestone 2**: Sharpe > 0.3, win rate ≥ 50%, max DD < 2%.
- **Milestone 3**: Sharpe ≥ 0.5, stable over 20+ trades.
- **Milestone 2** is the "ship" gate; **Milestone 3** is the "scale" gate.

#### B8. Phase 5 — Baseline & Comparison Protocol

**Current**: "Comparison to baseline."

**Improvement**:
- **Baseline capture**: Before Phase 1, run: `python backtest/experiments/smoke_test.py --config smoke_test_mom.yaml` and save to `results/baseline_momentum_v1.json` (metrics: Sharpe, trades, win rate, DD).
- **Comparison protocol**: Every phase deliverable must include: "vs baseline: ΔSharpe, Δtrades, Δwin_rate."

---

### C. Revised Execution Order (with Dependencies)

```
Phase 0     → Lock hypothesis, unify paths
    ↓
Pre-phase   → Pipeline audit, baseline capture, data availability check
    ↓
Phase 1.1   → Factor decomposition (new composite)
    ↓
Phase 1.2   → Threshold calibration (with sparse-data branch)
    ↓
Phase 1.3   → Inflection spec
    ↓
Phase 2     → Right-time filters (with code map)
    ↓
Phase 4     → Confirmation alignment
    ↓
Phase 5.0   → ADS gate revalidation
    ↓
Phase 5.1   → Pre-implementation checks
    ↓
Phase 5.2   → Post-implementation monitoring
    ↓
Phase 3     → Cross-sectional (optional, after pipeline supports)
```

---

### D. Summary of Additions

| Category | Additions |
|----------|-----------|
| **Missed** | ADS recalibration, statistical power, data fallbacks, exit alignment, regime consistency, cost structure, rollback, hypothesis selection criteria |
| **Hotspots** | Decision framework, look-ahead guard, sparse-data branch, code map, pipeline check, confirmation reliability, graduated milestones, baseline protocol |
| **New** | Phase 5.0 (ADS revalidation), Pre-phase (audit + baseline), feature flag, `composite_z_legacy` for exit compatibility |

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-26 | — | Initial plan |
| 1.1 | 2026-02-26 | — | Round 2: missed spots, hotspot improvements, revised execution order |
