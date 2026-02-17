# Mechanical Description: Enhanced Momentum Strategy (MOM)

**Purpose**: Factual, no-interpretation trace of what the strategy does from bar arrival to position close. This document describes the actual code paths, formulas, and thresholds — not what they are intended to do or designed to capture.

**Data source**: 1-minute OHLCV bars from Polygon.io (TSLA, Dec 16-20, 2024 in the smoke test run).

**Evidence base**: 10 trades (5 round-trips), -$20 net P&L, 60% win rate, Sharpe -4.43.

---

## 1. WHAT ARRIVES AT THE STRATEGY

Each bar, the strategy receives an `EnrichedMarketData` DataFrame containing:

**Raw**: `open`, `high`, `low`, `close`, `volume`, `timestamp`

**Indicators (29+)**: `sma_10/20/50/200`, `ema_9/21/50`, `rsi` (14-period), `macd/macd_signal/macd_histogram`, `stoch_k/stoch_d`, `bb_upper/middle/lower/width/percent`, `atr` (14-period), `adx`, `volume_ratio`, `vpin`, `vpin_percentile`, `buy_volume_pct`

**Engineered Features (50+)**: `momentum_10/20/50`, `composite_z`, `composite_pct`, `directional_coherence`, `vol_of_vol`, `transition_score`, `vol_expansion`, liquidity metrics, return series

**Regime Context**: `primary_regime`, `volatility_regime`, `regime_confidence` (continuous vector mapped from these)

---

## 2. COMPOSITE SIGNAL COMPUTATION (upstream, in feature pipeline)

### 2.1 composite_z

Ten indicators are each converted to a MAD-based z-score over a rolling window of min(252, N) bars:

| # | Indicator | Source |
|---|-----------|--------|
| 1 | `momentum_10` | `close / close.shift(10) - 1` |
| 2 | `momentum_20` | `close / close.shift(20) - 1` |
| 3 | `momentum_50` | `close / close.shift(50) - 1` |
| 4 | `rsi_normalized` | `(RSI_14 - 50) / 50` |
| 5 | `macd_normalized` | `(macd - macd_signal) / rolling_std(macd - macd_signal, 20)` |
| 6 | `stoch_k_centered` | `(stoch_k - 50) / 50` |
| 7 | `roc_10` | `roc_10 / 100` |
| 8 | `adx_normalized` | `adx / 100` |
| 9 | `trend_strength` | `|sum(returns, 20) / sum(|returns|, 20)|` |
| 10 | `volume_ratio_centered` | `volume_ratio - 1.0` |

**Per-indicator z-score**: `z_i = (X_i - median(X_i, window)) / (1.4826 * MAD(X_i, window))` where `MAD = median(|X - median(X)|)`

**Aggregation**: `composite_z = (1/N) * sum(z_i)` where N = number of available indicators (equal weights).

### 2.2 composite_pct

Rolling percentile rank of `composite_z` over min(252, N) bars, scaled to [0, 100].

`composite_pct = rolling_rank(composite_z, window) * 100`

Default fill: 50.0 (neutral) for NaN values.

### 2.3 composite_velocity and composite_acceleration

Derivatives of `composite_z`, normalized by rolling standard deviation:

```
velocity = diff(composite_z)                              # 1st derivative (bar-to-bar change)
acceleration = diff(velocity)                              # 2nd derivative (phase-transition detector)
composite_velocity = velocity / rolling_std(composite_z, 20)
composite_acceleration = acceleration / rolling_std(composite_z, 20)
composite_velocity_norm = clip(composite_velocity / 3.0, -1.0, 1.0)
composite_accel_norm = clip(composite_acceleration / 3.0, -1.0, 1.0)
```

`composite_accel_norm` is consumed by `transition_score` (section 2.6) and the multi-exit engine (section 6, exit #5).

### 2.4 directional_coherence

Measures sign and magnitude agreement across all z-scored indicators:

```
sign_agreement = |mean(sign(z_matrix), axis=columns)|
magnitude_ratio = |mean(z_matrix, axis=columns)| / (std(z_matrix, axis=columns) + 1e-8)
directional_coherence = clip(sign_agreement * magnitude_ratio / 3.0, 0.0, 1.0)
```

### 2.5 vol_of_vol

Coefficient of variation of ATR-based volatility, percentile-ranked:

```
vol = atr / close
vov_raw = rolling_std(vol, 10) / (rolling_mean(vol, 10) + 1e-10)
vol_of_vol = rolling_rank(vov_raw, min(252, N))    # [0, 1]
```

High values (→1.0) indicate unstable volatility regime; low values (→0.0) indicate stable.

### 2.6 transition_score

Multiplicative gate of five components (any zero kills the score):

```
transition_score = EMA_3(coherence * clip(composite_accel_norm, 0, 1) * vol_expansion * (1 - vol_of_vol) * (1 - vpin_percentile))
```

Where `vol_expansion = clip(atr / rolling_mean(atr, 20) - 1.0, 0.0, 1.0)`.

EMA smoothing: span=3, α=0.5. Range: [0, 1].

---

## 3. ENTRY SIGNAL GENERATION (in EnhancedMomentumStrategy)

Method chain: `generate_signals()` → `_generate_symbol_signals()` → `_evaluate_bar_at_index()`

### 3.0 Pre-checks

1. **Position check**: If already holding a position in the symbol, return None (entry-only strategy; exits handled by CentralRiskManager).
2. **State machine**: If `enable_state_machine=False` (our config), skip state machine and use composite entry logic below.
3. **ORB filter**: If bar timestamp is within 15 minutes of 09:30 market open, return None. No entries during opening range.

### 3.1 Level 1: Multi-Horizon Momentum Alignment

Reads `momentum_10`, `momentum_20`, `momentum_50` from enriched data.

**Noise floor**: 0.001 (config `momentum_noise_floor`)

**LONG aligned**: `momentum_10 > 0.001 AND momentum_20 > 0.001`
**SHORT aligned**: `momentum_10 < -0.001 AND momentum_20 < -0.001`

**Gate**: If neither long_aligned nor short_aligned → return None. (No entry.)

### 3.2 Level 2: Composite Threshold Check

**Base thresholds** (from YAML config):
- `composite_z_entry = 0.8`
- `composite_pct_entry = 65.0`

**Regime adjustment** via ADS regime vector R:
- Trend alignment: long_mult = 0.9 if R.trend >= 0.3, 1.2 if R.trend <= -0.3, 1.1 otherwise
- Volatility: vol_mult = 1.1 if R.volatility >= 0.75, 0.95 if R.volatility <= 0.25
- Liquidity: liq_mult = 1.1 and pct_bump +5 if R.liquidity <= 0.4
- Confidence: conf_mult = 1.05 if R.confidence <= 0.5

**Threshold floors**: `z_floor = 0.5`, `pct_floor = 60.0` (hard minimums regardless of regime adjustment)

**Momentum slope**: Ordinary least-squares regression slope of `momentum_10` over the last 3 bars (not a first difference). Computed as `slope = Σ((x - x̄)(y - ȳ)) / Σ((x - x̄)²)` where x = [0, 1, 2] and y = momentum_10 values. Falls back to `composite_z` slope or close-price returns if `momentum_10` is unavailable.

**LONG entry condition**:
```
composite_z > adjusted_long_threshold AND
composite_pct > adjusted_pct_threshold AND
momentum_slope > 0
```

**SHORT entry condition**:
```
composite_z < -adjusted_short_threshold AND
composite_pct < (100 - adjusted_pct_threshold) AND
momentum_slope < 0
```

**Inflection boost** (if detected — momentum sign flip or rapid acceleration): Reduces thresholds to 80% (z) and 90% (pct).

### 3.3 Level 3: Structural Confirmation

Three confirmation types checked in hierarchy:

**Volume expansion**: `volume_ratio > 0.3 AND buy_volume_pct > 0.55` (for BUY). Source: BVC-classified buy volume fraction from pipeline.

**Price structure**: Higher lows / lower highs / pivot / basing pattern over 5-bar lookback.

**Volatility breakout**: `std(returns, last 5) / std(returns, prior 15) > 1.3` with direction alignment check.

**Confirmation hierarchy**:
- Volume expansion present → confirmed (flow-based)
- Price structure present (without volume) → confirmed (structural)
- Volatility breakout alone → NOT confirmed

**If unconfirmed**: Entry requires `composite_z > threshold * 2.0` (unconfirmed_z_multiplier).

**Momentum stall guard**: If no flow confirmation AND momentum_slope < 0.0003 → blocked.

### 3.4 Transition Supervisor Gate

Sequential hard blocks:

1. **VoV mirage**: If `vol_of_vol > 0.98` → blocked.
2. **VPIN toxicity**: If `vpin_percentile > 0.85` → blocked.
3. **BVC adverse selection**: If `buy_volume_pct < 0.15` (for BUY side) → blocked.
4. **MQS computation** (thresholds from YAML config; code defaults differ):
   ```
   coherence_f = min(1, coherence / 0.15)         # YAML: mqs_coherence_ref=0.15 (code default: 0.30)
   flow_alignment_f = min(1, aligned_bvc / 0.45)  # YAML: mqs_bvc_ref=0.45
   liquidity_f = min(1, (volume_ratio + 0.50) / 0.50)  # YAML: mqs_vol_floor=-0.50, mqs_vol_range=0.50
   MQS = coherence_f * flow_alignment_f * liquidity_f
   MQS_penalty = 1.0 - 0.25 * (1.0 - MQS)        # YAML: mqs_penalty_weight=0.25 (code default: 0.40)
   ```
   Applied later as confidence multiplier.
5. **Transition threshold**: If `transition_score < 0.0` (YAML: `transition_threshold=0.0`, code default: 0.15) or in strict mode `< 0.001` (YAML: `transition_threshold_strict=0.001`, code default: 0.30) when `R.vol > 0.7 or R.liq < 0.3` → blocked.

### 3.5 Trend Persistence Filter

If enabled (`enable_trend_persistence_filter=True`):
- Over the last 10 bars, count close-to-close returns in the intended direction.
- If favorable ratio < 0.6 → blocked.

### 3.5b Pending Signal Duplicate Check

Before computing SMS, the strategy checks if a pending signal already exists for this symbol and side in the `PendingSignalQueue`. If so, return None — this prevents flooding the queue with duplicate entries while a prior signal is still maturing.

### 3.6 SMS Gate (Signal Maturity Score)

**Inputs computed in `_calculate_ads_context()`**:

```
z_margin = max(0, (|composite_z| - z_threshold) / z_threshold)
z_maturity = 1 - exp(-2 * z_margin)

pct_margin = max(0, (composite_pct - pct_threshold) / (100 - pct_threshold))
pct_maturity = 1 - exp(-2 * pct_margin)

structure_quality = detected from _detect_price_structure() [0, 1]

setup_maturity = (max(z_maturity, 0.001) * max(pct_maturity, 0.001) * (0.5 + 0.5 * structure_quality))^(1/3)
```

**Setup validity probability**:
```
p_rev_rsi = 1 / (1 + exp(-(RSI - 70) / 5))    # for BUY
setup_validity_prob = clip(1 - p_rev_rsi, 0.001, 1.0)
```

**Flow support proxy**:
```
signed_flow_support = clip((volume_ratio - 1.0) * direction_sign, -1.0, 1.0)
```
Source: `volume_ratio` column. No tick data, no L2 data. This is `current_bar_volume / SMA(volume, 20) - 1`, signed by trade direction.

**Volatility compression**:
```
short_vol = std(returns, last 5 bars)
long_vol = std(returns, last 20 bars)
vol_compression = clip(short_vol / long_vol, 0.5, 2.0)
```

**SMS mode = "multiplicative"** (our config):
```
SMS = setup_maturity^α * setup_validity_prob^β * exp(γ * signed_flow_support) * vol_compression^(-δ) * exp(-λ * pending_bars)
```

With regime-adaptive exponents (e.g., Normal: α=0.35, β=0.35, γ=0.20, δ=0.10), λ=0.05.

**Threshold tau(R)** (from `compute_sms_tau` in `ads_regime_vector.py`):
```
base = tau_0                                         # 0.40 from YAML (code default: 0.50)
base += 0.12 * max(0, R.volatility - 0.50)          # only penalizes when vol > 0.50
base += 0.06 * max(0, 0.70 - R.liquidity)           # only penalizes when liq < 0.70
base += 0.06 * max(0, 0.70 - R.confidence)          # only penalizes when conf < 0.70

# High-vol hardening (trend headwind × vol acceleration):
vol_accel = max(0, R.d_volatility)
base += 0.20 * vol_accel
base += 0.25 * trend_headwind * vol_accel            # trend_headwind: max(0, -R.trend) for LONG
base += 0.10 * dtrend_headwind * vol_accel           # dtrend_headwind: max(0, -R.d_trend) for LONG

# Fallback penalties:
base += 0.02 if ofi_proxy_used                       # always True in this strategy (hardcoded)
base += 0.02 if bb_missing                           # True when bb_position/bb_upper absent

# VPIN toxicity hardening:
base += 0.15 * max(0, vpin_pct - 0.50)              # vpin_tau_sensitivity = 0.15

tau = clip(base, 0.35, 0.80)
```

With `tau_0 = 0.40` from YAML and `ofi_proxy_used` always True, the baseline starts at 0.42 before regime adjustments. In practice, tau ranges roughly 0.42 – 0.65 depending on regime conditions.

**Gate**: If `SMS < tau` → signal enqueued in pending queue for maturation (up to 50 bars). If still below threshold after 50 bars → discarded.

**Pending signal maturation** (`_try_emit_matured_pending`, called each bar before new signal evaluation):
1. For each pending signal (BUY checked first, then SELL):
   - **Thesis validation**: If `composite_z` has flipped sign against the pending direction → discard immediately.
   - **Refresh SMS inputs**: Recompute `setup_maturity`, `setup_validity_prob`, `signed_flow_support`, `vol_compression` from current bar data via `_calculate_ads_context()`.
   - **Increment pending bars**: `pending_bars += 1`. If `pending_bars > max_pending (50)` → discard (stale).
   - **Recompute SMS**: With updated inputs and incremented pending_bars, compute SMS score.
   - **Check maturation**: If `SMS >= tau(R)` (recomputed for current regime):
     - **ERAR gate**: Must also pass `ERAR >= gamma`. If ERAR fails, signal stays pending (not discarded).
     - If both pass: emit as `StrategySignal` with `signal_reason: "ads_sms_matured_pending"`.
     - Matured signal confidence: `min(0.95, max(0.55, 0.50 + sms_score * 0.45))`.

### 3.7 ERAR Gate (Expected Risk-Adjusted Return)

**Holding period assumption**:
```
holding_minutes = time_stop_minutes  # 90 (code default; not overridden in YAML)
holding_days = clip(holding_minutes / 390, 0.05, 1.0)  # ≈ 0.23 days
```
Note: This differs from the CRM's actual `max_holding_minutes = 30` time stop (section 6). The ERAR calculation uses a more conservative (longer) holding assumption.

**Volatility estimate**: `volatility = atr / price` (ATR-based, not returns-based). Fallback: 0.02 if ATR or price unavailable.

**Expected PnL**:
```
edge_strength = clip(0.6 * raw_strength + 0.4 * max(z_maturity, pct_maturity), 0, 1)
expected_move = ATR * (0.35 + 0.95 * edge_strength)
expected_pnl_bps = (expected_move / price) * 10000
```

**CVaR 95** (Normal approximation):
```
period_vol = volatility * sqrt(holding_days)
cvar_95_bps = -period_vol * 2.06 * 10000           # negative (represents loss)
```
Where 2.06 is the normal distribution CVaR95 constant: `E[Z | Z < -1.645] ≈ -2.06`.

**Cost model** (from `_compute_erar_cost_core`):
```
c_spread   = spread_bps                                              # 2.0 bps (half-spread)
c_slip     = volatility * sqrt(max(participation, 0.001)) * 10000    # participation = 0.01 (hardcoded)
c_adverse  = adverse_prob * kyle_lambda * 10000                      # kyle_lambda = 0.0001
c_opp      = alt_return_bps * holding_days                           # alt_return_bps = 0.5

total_cost = c_spread + c_slip * participation^0.6 + c_adverse + c_opp
total_cost = max(total_cost, 0.1)                                    # floor at 0.1 bps
```

With smoke test typical values (vol ≈ 0.02, participation = 0.01): `c_slip ≈ 20 bps`, `c_slip * 0.01^0.6 ≈ 1.3 bps`, `c_adverse ≈ 0.1 bps`, `c_opp ≈ 0.04 bps`. Total ≈ 3.4 bps round-trip.

**Adverse probability** (VPIN-adjusted):
```
adverse_prob = clip(0.10 + 0.40 * max(0, vpin_pct - 0.50), 0.01, 0.50)
```

**ERAR computation**:
```
omega_adj = clip(1 + 0.1 * skewness, 0.5, 1.5)   # skewness = 0.0, so omega = 1.0
ERAR = (expected_pnl_bps - tail_lambda * |cvar_95_bps|) / total_cost_bps * omega_adj
```

**Gate**: If `ERAR < gamma` (gamma = 0.10 from config) → blocked. No entry.

### 3.8 Confidence Computation

**Base confidence** (weighted average):
```
strength_confidence = min(momentum_strength / (momentum_threshold * 2), 1.0)    * 0.30
consistency_confidence = momentum_consistency                                     * 0.20
trend_confidence = min(adx / (adx_threshold * 1.5), 1.0)                        * 0.20
volume_confidence = min(volume_ratio / volume_threshold, 1.0)                    * 0.15
acceleration_confidence = clip(accel * 10.0, 0, 1)                                * 0.15
```

`acceleration_scaling_factor` defaults to 10.0. For bullish signals, uses positive acceleration; for bearish, uses negative acceleration inverted.

**Condition bonuses**: +0.05 each for: momentum > threshold, ADX > 80% threshold, volume_ratio > 95% threshold, trend_strength > 0. Max total bonus: +0.20.

**MQS penalty**: `confidence *= MQS_penalty` (from section 3.4).

**Final gate**: If confidence < 0.40 → no signal emitted.

### 3.9 Target Weight (Strategy-Side Sizing Hint)

```
weight = base_position_pct                              # 0.20 from config
weight *= (0.7 + 0.6 * R.confidence)                   # confidence scaling [0.7, 1.3]
vol_penalty = R.volatility                              # [0, 1]
weight *= (0.7 + 0.4 * R.liquidity)                    # liquidity scaling [0.7, 1.1]
If R.trend >= 0.2 and BUY: weight *= 1.5, vol_penalty *= 0.5  (trend confirms)
If R.trend <= -0.2 and BUY: weight *= 0.5                     (trend headwind)
weight *= (1.5 - vol_penalty)                           # volatility scaling [0.5, 1.5]
weight = clip(weight, 0.0, max_position_pct)            # 0.20 cap from config
```

This `target_weight` is a **hint** — CentralRiskManager has final authority.

### 3.10 Signal Emission

If all gates pass: a `StrategySignal` is emitted with:
- `signal_type`: LONG_ENTRY or SHORT_ENTRY
- `strength`: `min(|momentum_strength| / momentum_threshold, 1.0)`
- `confidence`: from section 3.8
- `target_weight`: from section 3.9
- `additional_data`: full diagnostics (composite_z, composite_pct, SMS, ERAR, regime vector, transition state, entry diagnostics)

---

## 4. RISK AUTHORIZATION (CentralRiskManager Authorization Pipeline)

The signal enters `authorize_signal_6gate()`. Despite the method name, the pipeline actually has 8 gates (0 through 7).

### Gate 0: Circuit Breakers
- If circuit breaker at HALT or EMERGENCY → reject.

### Gate 1: Session Gate
- If outside trading hours → reject.

### Gate 2: Price Validation
- Computes `estimated_fill_price` using slippage model.
- If price stale (> 1% drift from signal price) → reject.
- If estimated slippage > 50 bps → reject.

### Gate 3: Position Constraints
- Cash cap: `max_affordable = available_cash / price`
- Concentration cap: `(portfolio_value * max_position_pct - existing_position_value) / price`
  (Accounts for existing position + pending orders in the same symbol.)
- `capped_quantity = min(requested, cash_cap, concentration_cap)`

### Gate 4: Multi-Factor Sizing
This is where the actual position size is determined. Five scaling phases:

1. **Risk impact**: If `(qty * price / portfolio_value) * vol > 0.01` → reduce by up to 50%.
2. **Regime scaling**: low_vol=1.10, normal=1.00, high_vol=0.60, extreme=0.30, crisis=0.0.
3. **Volatility scaling**: vol > 0.40 → 0.5x, vol > 0.25 → 0.8x, vol < 0.10 → 1.1x.
4. **Confidence scaling**: conf < 0.6 → 0.5x, conf > 0.9 → 1.2x.
5. **Combined**: `qty *= regime * vol * confidence` (capped at 1.25x).

Additional: ADS cooldown scaling, fractional Kelly cap (if trade count > 30).

### Gate 5: Risk Budget
- Per-trade loss limit: `per_trade_risk_pct * portfolio_value` (0.5% = $500 on $100k).
- Daily loss limit: `daily_risk_budget_pct * portfolio_value` (1.0% = $1,000 on $100k).
- Caps quantity if stop-loss distance would exceed budget.

### Gate 6: Cost Awareness (Almgren-Chriss)
- Computes round-trip cost in bps (spread + impact + slippage + commission).
- Computes expected edge bps: `signal_strength * 20 bps`.
- If `round_trip_cost / expected_edge > 1.0` → reject (negative expectancy).
- If ratio > 0.80 → warning but pass.

### Gate 7: Final
- If `authorized_quantity < min_order_size` (1 share) → reject.
- Otherwise → authorized.

### Order Execution
Authorization → `ExecutionRequest` → `UnifiedExecutionEngine` → `Fill` → `PositionBook.on_fill()`.

**In smoke test config**: `fill_probability=1.0`, `partial_fill_probability=0.0`, `slippage_bps_max=5.0`, `commission_per_share=0.005`, `seed=42`.

---

## 5. POSITION TRACKING

`PositionBook.on_fill(fill)`:
- Creates `BookPosition` with `avg_entry_price`, `quantity`, `side`, `opened_at`, `metadata` (includes entry diagnostics).
- Updates `cash_balance` by `-(quantity * price + costs)` for buys.
- Tracks `realized_pnl` and `unrealized_pnl` per position.

**Price updates**: Each bar, `on_price_update()` marks positions to market and updates unrealized P&L.

---

## 6. EXIT EVALUATION (CentralRiskManager, each bar)

Method: `_monitor_positions()` → `decide_exit()` for each open position.

Controlled by config flag `enable_ads_multi_exit` (YAML: `enable_ads_multi_exit: true` in strategy parameters). If disabled, the multi-exit engine does not run and positions are only closed by EOD liquidation or manual intervention.

### Exit Priority Order

**1. VOL_STOP** (hard circuit breaker):
```
sigma_eff = max(realized_vol, forecast_vol)
stop_distance_pct = k * sigma_eff * sqrt(1 + kappa * max(0, delta_rho))    # k=2.0, kappa=0.5
If pnl_pct <= -stop_distance_pct → EXIT
```
`delta_rho` = correlation shift (clamped to non-negative; only widens stop, never tightens).

**2. DIRECTION_REVERSAL** (thesis invalidation):
```
signed_z = current_composite_z * entry_direction_sign
direction_health = 1 / (1 + exp(-steepness * (signed_z + 0.3)))    # steepness = 5/0.3 ≈ 16.7
If direction_health < 0.2 → EXIT
```
This triggers when composite_z moves ~0.3 z-scores against the entry direction.

**3. ALIGNMENT_BREAKDOWN** (L1 causal chain inverse):
```
If BOTH short and medium momentum reversed against entry → alignment_health = 0.1 → EXIT
```

**4. TRANSITION_EXHAUSTION** (geometric mean health < 0.15):
```
health = (direction_health * accel_health * coherence_health * vov_health * alignment_health * flow_health)^(1/6)
If health < 0.15 → EXIT
```

**5. TRANSITION_TAKE_PROFIT**:
- Sub-A: `signed_accel < -0.3 AND pnl_pct > 0` → EXIT (acceleration exhaustion)
- Sub-B: Dynamic TP: `pnl_pct >= tp_initial * exp(-held_mins/tp_decay) + tp_floor` AND `health < 0.7` → EXIT
  - `tp_initial_pct = 2.0` (code default; not overridden in YAML)
  - `tp_floor_pct = 0.3` (code default)
  - `tp_decay_minutes = 30.0` (code default)

**6. LIQUIDITY_STOP**:
- If `effective_spread_bps > 80` or liquidity_regime in (crisis, illiquid) → EXIT.

**7. TIME_STOP**:
- `held_minutes >= base_max_holding_minutes * (1 + entry_transition_score)`.
- YAML config: `max_holding_minutes = 30` (code default: 1440, i.e. full trading day). So in the smoke test, time stop triggers at ~30-60 minutes depending on entry `transition_score`.

### EOD Liquidation (separate mechanism, NOT part of CRM exit priorities)

EOD liquidation is handled by `InstitutionalBacktestEngine._check_eod_liquidation()` via the `EODGuard` helper class, not by the CentralRiskManager multi-exit engine. It runs as a separate check after each bar's processing.

- Config: `enable_eod_liquidation = true`, `eod_close_time = "15:55"`.
- At each bar, `EODGuard.should_liquidate_position()` checks if current time >= `eod_close_time` for each position's owning strategy.
- If triggered, positions are closed via the execution simulator with realistic costs.
- Idempotency: `EODGuard.mark_liquidated(date)` prevents double-liquidation.
- The EOD guard also proactively blocks new entry signals once eod_close_time is reached via `EODGuard.is_active()`.

### Exit Execution
Exit signals from the multi-exit engine bypass Gate 4 (sizing) and Gate 6 (cost awareness) in the authorization pipeline. EOD liquidation bypasses the CRM entirely — it goes directly through the execution simulator.

---

## 7. SMOKE TEST EVIDENCE (TSLA, Dec 16-20, 2024)

### Pipeline Funnel
```
1,919 bar feature slices processed (CP1s)
   15 signals generated by strategy (CP2)
   20 risk authorization events (CP3) = 15 strategy signals + 5 exit requests
      → 10 authorized, 10 rejected
   10 orders created (CP4) = 5 entry orders + 5 exit orders
   10 fills (CP5)
   10 position book updates (CP6)
   10 PnL calculations (CP7)
```

The 5 additional risk authorization events beyond the 15 strategy signals are exit requests generated by the CentralRiskManager multi-exit engine. Of the 15 strategy entry signals, 5 were authorized and 10 were rejected at various gates.

### Actual Trades

| # | Date | Time | Side | Qty | Entry $ | Exit $ | Hold | P&L |
|---|------|------|------|-----|---------|--------|------|-----|
| 1 | Dec 16 | 11:15→11:21 | BUY | 35.61 | 455.57 | 455.47 | 6 min | -$3.38 |
| 2 | Dec 17 | 10:50→11:05 | BUY | 16.89 | 480.17 | 477.20 | 15 min | -$50.22 |
| 3 | Dec 19 | 13:14→13:15 | BUY | 18.69 | 433.67 | 434.19 | 1 min | +$9.68 |
| 4 | Dec 19 | 13:16→13:27 | BUY | 18.72 | 433.13 | 433.16 | 11 min | +$0.61 |
| 5 | Dec 20 | 10:33→10:57 | BUY | 18.51 | 438.04 | 439.30 | 24 min | +$23.39 |

Note: Per-trade exit reasons (which of the 7 exit priorities triggered) are not captured in the smoke test output. The exit signals show as `sell` with `confidence=100%` and `strength=1.0`, indicating CRM-initiated exits, but the specific exit trigger is not logged to the trade list.

**All 5 entries were BUY signals.** No short entries fired across 5 trading days. Dec 18 (Wednesday) produced no trades at all.

**Net P&L**: -$19.92 on $100,000 initial capital (-0.02%).

### Observable Patterns
- Average hold time: 11.4 minutes
- Median hold time: 11 minutes
- Position sizes: 16-36 shares ($7k-$16k notional, 7-16% of capital)
- The largest loss (Trade 2, -$50.22) is 2.1x the largest win (Trade 5, +$23.39)
- 3 of 5 trades held 1-11 minutes; 2 held 15-24 minutes

---

## 8. WHAT THIS DOCUMENT DOES NOT CONTAIN

- Interpretation of whether the strategy has edge
- Claims about what signals "capture" or "detect"
- Comparisons to what the ADS specification intends
- Suggestions for improvement

Those belong in the Problem Statement, not here.
