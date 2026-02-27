# Momentum Signal Intent Resolution Plan — Implementation Guide

**Version**: 2.1 (SSOT)  
**Goal**: Signal intent that is **effective**, **edge-rigorous**, and **at the right time**.  
**Status**: Single source of truth for implementation. Incorporates AQR-style scrub (v2.0).

---

## 1. Scope

| In scope | Out of scope |
|----------|--------------|
| Pre-ADS signal generation (Level 1–3 composite, state machine, confirmation) | ADS gates (SMS, ERAR) — revalidated only |
| `engineer.py` composite construction | Transition Supervisor (VoV, VPIN, BVC, MQS) |
| `enhanced_momentum.py` entry logic | CRM, PositionBook, execution pipeline |

---

## 2. Implementation Roadmap

Execute in order. Do not skip steps.

```
Step 0   Pre-flight (audit, baseline, feature flag)
Step 1   Lock hypothesis
Step 2   Factor decomposition (engineer.py)
Step 3   Threshold calibration
Step 4   Inflection spec
Step 5   Right-time filters
Step 6   Confirmation alignment
Step 7   ADS revalidation + exit compatibility
Step 8   Validation & merge
Step 9   Cross-sectional (optional, requires multi-symbol)
```

---

## 3. Step-by-Step Execution Guide

### Step 0: Pre-Flight

**Prerequisites**: None.

**Actions**:

1. **Data source checklist** — Document in `docs/momentum_pipeline_audit.md`:

   | Item | Definition / Constraint |
   |------|-------------------------|
   | Data type | Polygon OHLCV 1-min (or tick-level if available) |
   | `buy_volume_pct` | BVC from indicators engine: Φ(ΔP/σ) on bar returns. **Always a proxy** for OHLCV (no aggressor side). |
   | **Option C viable** | **No** for Polygon OHLCV. Reject Option C at Step 1 without further analysis. |
   | `spread_proxy_bps` | `(high - low) / close * 10000`. Not bid-ask; range-based proxy. |
   | `spread_baseline` | Rolling median of `spread_proxy_bps` over `spread_baseline_window` bars (default 20). Config: `spread_baseline_window`. |
   | `volume_ratio` | `volume / volume_sma`. SMA window from indicators engine (document in audit). |
   | `composite_acceleration` warm-up | First 50 bars (or velocity window + 1) may have NaN. **Block entry until valid.** |

2. **Pipeline audit** — Document:
   - Columns guaranteed for momentum: `composite_z`, `composite_pct`, `momentum_10/20/50`, `volume_ratio`, `buy_volume_pct`, `composite_acceleration`, `composite_velocity`, `atr`, `adx`
   - Warm-up bars: 50 (for momentum_50)
   - `volume_ratio` SMA window (from indicators engine)
   - If `buy_volume_pct` is proxy only (OHLCV) → **reject Option C** in Step 1

4. **Baseline capture**:
   ```bash
   PYTHONPATH=. python backtest/experiments/smoke_test.py --config backtest/configs/smoke_test_mom.yaml
   ```
   Save to `results/baseline_momentum_v1.json`: `{sharpe, trade_count, win_rate, max_dd}`

5. **Feature flag** — Add to `smoke_test_mom.yaml` (or strategy config):
   ```yaml
   enable_momentum_v2_signal: false
   ```

**Deliverables**: `docs/momentum_pipeline_audit.md`, `results/baseline_momentum_v1.json`, config flag.

**Acceptance**: Audit doc exists; baseline file exists; flag defaults to false.

---

### Step 1: Lock Hypothesis

**Prerequisites**: Step 0 complete.

**Actions**:

1. **Decision matrix** — Evaluate options:

   | Option | Mechanism | Data need | Reject if |
   |--------|-----------|-----------|-----------|
   | A | Underreaction: acceleration + flow | composite_acceleration, buy_volume_pct | acceleration noisy (rolling std > 0.5) |
   | B | Breakout: vol compression → expansion | atr, volume, high/low | — |
   | C | Flow-driven continuation | BVC/tick-level flow | **Reject for Polygon OHLCV** — buy_volume_pct is always proxy (Step 0 audit) |

   **Data constraint**: If data is Polygon OHLCV (no tick-level flow), Option C is **infeasible**. Reject without further analysis.

2. **Choose one** using: (1) Data availability, (2) Architectural fit (A→composite path, B→state machine), (3) External review if available.

3. **Write hypothesis doc** (`docs/momentum_hypothesis_v2.md`):
   - Causal mechanism
   - Edge source
   - "Right time" (operational definition)
   - Invalidation conditions
   - Data requirements
   - **Expected half-life of edge** (from literature or empirical decay; if unknown, state assumption)

4. **Unify entry path** — If A: composite path. If B: state machine path. If C: new flow path. Remove the other path or gate it behind a config flag.

**Deliverables**: `docs/momentum_hypothesis_v2.md`, architecture decision (one path).

**Acceptance**: One hypothesis doc; single active entry path.

---

### Step 2: Factor Decomposition

**Prerequisites**: Step 1 complete.

**Files**: `core_engine/processing/features/engineer.py`

**Actions**:

1. **Correlation analysis** — Pairwise correlations of 10 composite inputs over 252 days × N symbols. Identify clusters.

2. **Choose construction**:
   - **PCA**: Top 2–3 PCs. Note: unsupervised; still needs calibration.
   - **IC**: Rolling IC vs forward return (next 5 bars). No look-ahead: forward return must not overlap indicator window.
   - **Theory**: 3–4 factors: momentum, trend_strength, flow/volume, vol_regime. Drop redundant (e.g., roc_10 if momentum_10 exists).

3. **Implement** — Add `composite_z_v2` (and `composite_pct_v2`) in `engineer.py`. Multiplicative or min-gate across factors (ADS-compliant). Define fallback when data insufficient: `composite_z_v2 = 0.0`, `composite_pct_v2 = 50.0`.

4. **Wire strategy** — When `enable_momentum_v2_signal: true`, strategy reads `composite_z_v2` / `composite_pct_v2` instead of `composite_z` / `composite_pct`.

**Deliverables**: New composite spec, `engineer.py` changes, unit tests.

**Acceptance**: Smoke test passes with v2 enabled; composite values non-trivial.

---

### Step 3: Threshold Calibration

**Prerequisites**: Step 2 complete.

**Actions**:

1. **Data check** — Count train-period trades. If < 100:
   - **Sparse branch**: Skip grid search. Use theory-based: `composite_z > 0.7`, `composite_pct > 60` (exploratory; see Appendix D). Run sensitivity ±15%. Report.
   - **Rationale**: 100 trades ≈ minimum for ~30% OOS Sharpe std error; if fewer, theory-based only with explicit sensitivity report.
   - **Else**: Proceed with grid search.

2. **Grid search** (if sufficient data):
   - **Single split**: Train 60% of history, validate 40%. Report bootstrap 90% CI on validation Sharpe.
   - **Walk-forward** (preferred): 5 rolling windows (e.g., train 6 months, validate 1 month). Report mean and std of Sharpe across folds.
   - Grid: (z_threshold, pct_threshold), steps (0.1, 5). Metric: Sharpe.
   - **Multiplicity**: Report best Sharpe; if multiple thresholds achieve similar Sharpe, prefer simpler (higher z, higher pct). Consider Bonferroni or permutation-based p-value for robustness.

3. **Regime split** — If data allows, calibrate in low-vol vs high-vol. Use bootstrap difference in Sharpe; if 90% CI excludes 0, use regime-adaptive thresholds.

4. **Config** — Add `composite_z_entry_calibrated`, `composite_pct_entry_calibrated` with `_date` suffix.

**Deliverables**: Calibrated thresholds, calibration report (with CI / walk-forward stats).

**Acceptance**: Thresholds documented; backtest vs baseline shows ΔSharpe.

---

### Step 4: Inflection Spec

**Prerequisites**: Step 1 complete.

**Files**: `core_engine/trading/strategies/implementations/momentum/enhanced_momentum.py`

**Actions**:

1. **Define inflection** — (a) `composite_acceleration > 0` AND `composite_velocity` sign matches direction, OR (b) `momentum_10` crossed zero in last 3 bars with `volume_ratio > 1.0`. (3 bars ≈ 3 min at 1-min; sensitivity ±1 bar — see Appendix D.)

2. **Logic change** — Inflection is *required* for early entry (lower thresholds). No inflection → require full thresholds. Remove 80%/90% multiplier heuristic.

3. **Config** — `inflection_required_for_early_entry: true`.

4. **Backtest** — With/without inflection filter. Report ΔSharpe, Δdrawdown.

**Deliverables**: Inflection spec in code, config key, backtest comparison.

**Acceptance**: No arbitrary threshold reduction; inflection is a gate.

---

### Step 5: Right-Time Filters

**Prerequisites**: Step 1 complete.

**Files**: `enhanced_momentum.py`, `momentum_state_machine.py` — see code map below.

**Actions** (hypothesis-specific):

| Hypothesis | Filter | Location | Config |
|------------|--------|----------|--------|
| A | `composite_acceleration > 0` at entry; block if `< -0.2` | `_check_composite_entry` or new gate | — |
| A/B | `(close - MA) / ATR > max_extension_atr` → block | **Both paths** (see below) | `max_extension_atr: 1.5` |
| B | Entry only within first N bars of breakout | `momentum_state_machine.evaluate()` | `max_bars_since_breakout: 3` |
| All | `spread_proxy_bps > baseline × multiplier` → block | Before entry | `spread_baseline_window: 20`, `spread_bps_block_multiplier: 2.0` |

**Extension filter (A/B) — must apply in BOTH paths**:
- **State machine**: Already in `momentum_state_machine.evaluate()` breakout branch.
- **Composite path**: Implement `(close - MA) / ATR > max_extension_atr` → block in `_check_composite_entry` (or equivalent) before entry. **Verify both paths apply when enabled.**

**Spread block**:
- `spread_proxy_bps = (high - low) / close * 10000`
- `baseline = rolling_median(spread_proxy_bps, spread_baseline_window)`
- Block if `spread_proxy_bps > baseline * spread_bps_block_multiplier`

**Regime override** — If `regime_detector.confidence` (or `regime_manager.trend_conf` — document which) < 0.5, use neutral thresholds (no regime adjustment). Config: `regime_confidence_source`.

**Document** — Add "Right time checklist" in code comments.

**Deliverables**: Filters implemented, code map updated, config keys.

**Acceptance**: Each entry passes right-time checklist.

---

### Step 6: Confirmation Alignment

**Prerequisites**: Step 1 complete.

**Actions**:

1. **Map to hypothesis**:
   - A: Primary = flow (buy_volume_pct, volume_ratio). Secondary = price structure.
   - B: Primary = volume surge. Secondary = vol expansion.
   - C: Primary = flow. (**Rejected for OHLCV** — requires tick-level BVC.)

2. **Primary required** — No entry without primary confirmation. Remove "unconfirmed requires 2× threshold".

3. **Calibrate** — If profitable vs unprofitable entries ≥ 20 each: derive `volume_ratio > X`, `buy_volume_pct > Y` from data. Else: theory-based (volume_ratio 1.0 = neutral/no expansion; buy_volume_pct 0.52 from Lee-Ready/BVC literature or data-derived — see Appendix D) + sensitivity.

4. **Config** — `confirmation_primary_required: true`.

**Deliverables**: Confirmation spec, config.

**Acceptance**: No entry without primary confirmation.

---

### Step 7: ADS Revalidation & Exit Compatibility

**Prerequisites**: Steps 2–6 complete.

**Actions**:

1. **Backtest** — Run with v2 enabled. Inspect SMS scores at entry, ERAR values.

2. **ADS gates** — If signal quality distribution shifted: consider tau/gamma adjustment ±0.05. Document rationale; run sensitivity before deploying.

3. **Exit logic** — CRM exits use `composite_z`. If we changed to `composite_z_v2`:
   - Option A: Update CRM exit formulas to use `composite_z_v2`.
   - Option B: Keep `composite_z` for exits during transition; add `composite_z_v2` for entry only. Migrate exits after validation.

4. **Verify** — Exits still fire when thesis invalid; no excessive early exit.

**Deliverables**: ADS revalidation note, exit compatibility confirmed.

**Acceptance**: No exit misfire; ADS gates still appropriate.

---

### Step 8: Validation & Merge

**Prerequisites**: Steps 0–7 complete.

**Actions**:

1. **Unit tests** — Factor construction, threshold logic, inflection, confirmation.

2. **Smoke test** — Must pass. No funnel regression.

3. **Backtest report** — Same period + extended if available. Include: vs baseline (ΔSharpe, Δtrades, Δwin_rate). **Report gross and net of config execution costs** (commission + slippage). Report turnover: trades per period × avg position size / capital.

4. **Milestones** (all apply to **net** Sharpe unless noted):
   - M1: Net Sharpe > 0 (proceed)
   - M2: Net Sharpe > 0.3, win rate ≥ 50%, max DD < 2% (ship)
   - M3: Net Sharpe ≥ 0.5, ≥ 20 trades, **and** bootstrap 90% CI for Sharpe > 0.2 (scale)

5. **Merge** — Enable v2 by default or keep behind flag for staged rollout.

**Deliverables**: Test suite, backtest report, milestone status.

**Acceptance**: M1 passed; smoke test green.

---

### Step 9: Cross-Sectional (Optional)

**Prerequisites**: Steps 0–8 complete. **Requires**: Multi-symbol pipeline. **Minimum universe size**: N ≥ 10 symbols (with N < 10, rank thresholds are unstable).

**Actions**:

1. **Pipeline check** — Verify strategy receives `universe_df` (all symbols, same timestamp). If not, pipeline change first.

2. **Universe construction** — Symbols passing liquidity filter (volume, spread). Consider sector-neutral rank (within-sector) if factor exposure is a concern.

3. **Rank** — Each bar, rank `composite_z_v2` across symbols. Entry: long if rank ≥ 0.75, short if rank ≤ 0.25.

4. **Config** — `enable_cross_sectional_rank: false` (default). Use multi-symbol config for validation.

**Deliverables**: Rank feature, config. Cannot validate with 1-symbol smoke test.

**Acceptance**: Multi-symbol backtest shows rank filter effect.

---

## 4. Success Criteria

| Criterion | Measure |
|-----------|---------|
| Effective | M1: Net Sharpe > 0; M2: Net Sharpe > 0.3, win rate ≥ 50%, max DD < 2% |
| Edge-rigorous | Factor construction justified; thresholds calibrated or theory-based; constants cited or labeled (Appendix D) |
| Right time | Right-time checklist enforced; extension filter in both paths; chase filters block late entries |

---

## 5. Appendices

### A. Config Keys

| Key | Default | Step |
|-----|---------|------|
| `enable_momentum_v2_signal` | false | 0 |
| `composite_z_entry_calibrated` | — | 3 |
| `composite_pct_entry_calibrated` | — | 3 |
| `inflection_required_for_early_entry` | true | 4 |
| `max_extension_atr` | 1.5 | 5 |
| `max_bars_since_breakout` | 3 | 5 |
| `spread_baseline_window` | 20 | 5 |
| `spread_bps_block_multiplier` | 2.0 | 5 |
| `regime_confidence_source` | — | 5 (document: regime_detector.confidence or regime_manager.trend_conf) |
| `confirmation_primary_required` | true | 6 |
| `enable_cross_sectional_rank` | false | 9 |

### B. Code Map (Right-Time Filters)

| Filter | File | Method | Notes |
|--------|------|--------|-------|
| Extension | `enhanced_momentum.py` | `_check_composite_entry` | **Implement** — composite path currently lacks this |
| Extension | `momentum_state_machine.py` | `evaluate()` breakout branch | Already present |
| Acceleration | `enhanced_momentum.py` | New gate or `_passes_transition_supervisor_gate` | — |
| Bar-since-trigger | `momentum_state_machine.py` | `evaluate()` breakout branch | — |
| Spread block | `enhanced_momentum.py` | Before `place_order` or in `_check_composite_entry` | Use spread_proxy_bps, baseline from Step 0 |

### C. Fallback Spec (ADS-Aligned)

For each new gate: define "If X missing → block" or "If X missing → use Y".

| Input | Missing behavior |
|-------|------------------|
| composite_z_v2 | Use 0.0 (neutral) |
| composite_pct_v2 | Use 50.0 |
| composite_acceleration | Block entry (inflection unknown) |
| buy_volume_pct | Use 0.5 (neutral) if proxy; block if primary confirmation |
| volume_ratio | Use 1.0 (neutral) |
| regime confidence < 0.5 | Use neutral thresholds (no regime adjustment) |
| composite_acceleration NaN (warm-up) | Block entry until valid (first 50 bars) |

### D. Constant Justification Table

| Constant | Value | Source |
|----------|-------|--------|
| composite_z sparse | 0.7 | Exploratory; sensitivity ±0.15 |
| composite_pct sparse | 60 | Exploratory; sensitivity ±5 |
| buy_volume_pct | 0.52 | Lee-Ready / BVC literature; or data-derived |
| volume_ratio | 1.0 | Neutral (no expansion) |
| inflection bars | 3 | 1-min bars; sensitivity ±1 bar |
| tau/gamma adjustment | ±0.05 | Document rationale; sensitivity before deploy |

---

## 6. Pre-Implementation Checklist

Before starting Step 0:

- [ ] Plan v2.1 (SSOT) approved
- [ ] Backtest environment runnable (`smoke_test_mom.yaml`)
- [ ] Access to `engineer.py`, `enhanced_momentum.py`, `momentum_state_machine.py`
- [ ] Data source confirmed (Polygon OHLCV vs tick-level) — Option C viability
- [ ] Spread proxy and baseline defined (Step 0)
- [ ] Extension filter will be wired to composite path (Step 5)
- [ ] Net-of-cost validation in milestones (Step 8)
- [ ] All constants either cited or labeled exploratory (Appendix D)

---

## 7. Changelog

| Version | Change |
|---------|--------|
| 2.0 | Initial implementation guide |
| 2.1 (SSOT) | AQR scrub: data source constraints, extension filter composite path, spread baseline, regime source, statistical rigor (walk-forward, multiplicity, bootstrap CI), net-of-cost milestones, turnover, constant justification table, pre-implementation checklist |
