# Shadow Execution Plan — v1.8-SHADOW-SHOCK

**Spec**: v1.8-SHADOW-SHOCK (frozen)  
**Universe**: MSFT, NVDA, TSLA, WMT (validated large-cap)  
**Step 7 result**: ALL PASSED — 619 trades, 757.73 bps, zero kills  
**Objective**: Measure live execution drift against validated backtest baseline  
**Revision**: v3-FINAL — incorporates all external quant reviews:
- v2: replay stress, compound kill, intraday recalibration, cross-symbol correlation
- v3: adversarial burst replay, loss velocity monitor, shock event clustering,
  nuanced frequency collapse (Q5-aware), CI acceptance rule, latency decomposition

---

## Current State Assessment

### Completed (Steps 0-7)

| Component | File | Status |
|-----------|------|--------|
| Constants v1.8 | `shadow/constants.py` | Frozen |
| Type system | `shadow/types.py` | Complete |
| ClickHouse schema | `shadow/schema/shadow_ddl.sql` | Deployed |
| Streaming bucketer | `shadow/streaming_bucketer.py` | Complete + tested |
| Event filter | `shadow/event_filter.py` | Complete + tested (shock-only) |
| Order manager | `shadow/order_manager.py` | Complete + tested |
| Mechanism monitor (M1-M9) | `shadow/mechanism_monitor.py` | Complete + tested |
| Shadow logger | `shadow/shadow_logger.py` | Complete |
| Latency monitor | `shadow/infra_latency_monitor.py` | Complete |
| Engine orchestrator | `shadow/engine.py` | Complete (needs integration wiring) |
| Historical backtest | `shadow/historical_backtest.py` | ALL PASSED |

### Infrastructure Available

| Component | File | Status |
|-----------|------|--------|
| Polygon WebSocket | `core_engine/data/feeds/polygon_realtime.py` | Production-ready |
| IBKR Adapter | `core_engine/broker/adapters/ibkr_adapter.py` | Production-ready |
| IBKR Paper Facade | `livepapertest/broker/ibkr_paper_facade.py` | Reference available |
| Polygon Live Bridge | `livepapertest/engine/polygon_live_bridge.py` | Reference available |

### Remaining Build (Steps 8-10)

| Step | Description | Effort |
|------|-------------|--------|
| 8 | Historical replay validation | ~1 day |
| 9 | Paper trading integration test | ~1 day |
| 10 | 30-day shadow execution | 30 trading days |

---

## Step 8: Historical Replay Validation

**Purpose**: Prove the streaming bucketer produces identical results to the
offline pipeline that Step 7 used. If streaming diverges, live trading
will detect different events than the backtest validated.

### 8A: Bucket Boundary Match (20 symbol-days)

**What**: Feed raw trades from ClickHouse through `StreamingVolumeBucketer`
and compare bucket boundaries against pre-computed `microstructure_buckets`.

**Symbol-day selection** (per symbol: 2 highest-vol, 2 lowest-vol, 1 median):

| Symbol | Days to select |
|--------|---------------|
| MSFT   | 5 |
| NVDA   | 5 |
| TSLA   | 5 |
| WMT    | 5 |

**Validation criteria**:
- 100% bucket boundary match (start/end timestamps)
- ≤0.1% flow_imbalance divergence per bucket
- ≤5% imbalance distribution p95 divergence across all 20 days

### 8B: Replay Stress Mode — IID Noise

**Why**: Historical replay validates determinism, NOT live determinism.
Polygon historical trades are perfectly ordered. Live WebSocket feeds
deliver out-of-order trades, duplicates, and delayed corrections.

**Stress perturbations** (applied to historical trade stream):
- Randomly shuffle trades within ±50ms window
- Inject 0.5% duplicate trade prints
- Drop 0.1% of trades randomly

**Validation criteria under stress**:
- Bucket boundaries still stable (≤1 bucket boundary shift per symbol-day)
- Imbalance divergence within ±5% of clean replay
- Event detection count within ±10% of clean replay

### 8B2: Adversarial Burst Replay (v3)

**Why**: Real WebSocket failure modes are NOT IID noise. They are bursty
and state-corrupting. The IID stress mode above catches fragility to
random noise. This mode catches fragility to correlated failures.

**Three adversarial scenarios**:

**A. Burst packet delay**:
- Simulate 200-400ms freeze, then replay all queued trades instantly
- Targets: shock regime events where 300ms burst collapse during
  spread_ratio > 2.0 may flip entry logic entirely
- Validates: bucketer handles trade bursts without creating phantom buckets

**B. Deep out-of-order delivery**:
- 0.2% of trades shuffled 150-300ms beyond normal window
- Lee-Ready classification is order-sensitive; deep reorder during
  volatility can cluster classification drift
- Validates: imbalance stability under extreme reordering

**C. Quote/trade desync**:
- Inject scenarios where trades arrive 100-200ms before quote update
- Strategy is heavily dependent on NBBO structural integrity
- Validates: engine safely rejects (not silently degrades into false
  spread_ratio spikes)

**Validation criteria under adversarial stress**:
- No phantom bucket creation during burst replay
- Imbalance divergence within ±8% of clean replay
- NBBO rejection rate increases (expected) but no silent false positives
- Lee-Ready drift within 5% even under deep reorder

### 8C: Lee-Ready Classification Drift (30 symbol-days)

**What**: Compare aggressor classification distribution from streaming
path vs offline path. Streaming receives trades one-by-one without
the context that batch processing has.

**Validation criteria**:
- ≤3% p95 divergence = hard pass
- 3-5% = investigation zone (root cause required)
- >5% = hard fail — streaming path unreliable

**Segmentation** (a 3% global average can hide 8% drift in volatile windows):
- Drift by symbol
- Drift by time-of-day (opening hour, midday, closing hour)
- Drift by spread regime (Q1-Q5)

Flag if ANY segment exceeds 5% even when global average < 3%.

### Deliverable

`core_engine/microstructure/shadow/replay_validator.py` with CLI:
```bash
python -m core_engine.microstructure.shadow.replay_validator
```

---

## Step 9: Paper Trading Integration Test (1 trading day)

**Purpose**: Smoke test that all live components connect and function.
This is NOT about P&L — it's about plumbing.

### 9A: Pre-requisites (before market open)

1. **IBKR Gateway/TWS** running in paper mode (port 7497 or 4002)
2. **Polygon API key** configured (Stock Advanced tier for quotes)
3. **ClickHouse** running with shadow tables deployed
4. **NTP** synced (offset < 10ms)

### 9B: Integration wiring — `run_shadow.py`

Create the main entry point that connects:

```
Polygon WS (trades + quotes for MSFT, NVDA, TSLA, WMT)
  ↓
LiquidityShadowEngine.on_trade() / on_quote()
  ↓
OrderManager ← wired to IBKRAdapter.submit_limit_order / cancel_order
  ↓
MechanismMonitor → ShadowLogger → ClickHouse
```

**Implementation checklist**:

| Task | Detail |
|------|--------|
| Config loader | YAML config with API keys, IBKR host/port, ClickHouse URL, portfolio value |
| Polygon → Engine bridge | Map Polygon WS trade/quote messages to `engine.on_trade()` / `engine.on_quote()` |
| Engine → IBKR bridge | Wire `broker_submit` and `broker_cancel` callbacks from `IBKRAdapter` |
| IBKR → Engine fill bridge | Map IBKR fill callbacks to `order_manager.on_fill()` |
| Market hours scheduler | Start engine at 9:45 ET, run `run_daily_close()` at 15:45 ET, stop at 16:00 |
| Graceful shutdown | SIGINT/SIGTERM → cancel open orders, flatten positions, flush logs |
| Logging | File + stdout, include version string in every log line |

### 9C: 1-Day Verification Checklist

Run for 1 full trading day (9:45-15:45 ET). Verify:

| Check | Expected | Action if fails |
|-------|----------|----------------|
| Polygon WS connects | Auth success, heartbeat stable | Check API key, tier |
| IBKR connects | Paper account, positions queryable | Check Gateway running |
| Buckets produced | ~200/symbol/day (varies by volume) | Check ADV constants |
| Events detected | ~20-30 per symbol (based on backtest) | Check imbalance thresholds |
| Orders placed | At least 1 order placed via IBKR | Check broker wiring |
| Fill callback received | At least 1 fill (paper is generous) | Check fill handler |
| Exit triggered | At least 1 exit (spread norm or timeout) | Check exit logic |
| ClickHouse logged | Rows in shadow_events, shadow_fills | Check logger flush |
| Latency healthy | Ingest p95 < 250ms | Check network |
| No crash/hang | Engine runs full session without crash | Check error handling |
| Daily close runs | Reports generated, counters reset | Check scheduler |
| **Fill rate gap** | Paper vs model fill rate divergence | Document gap for calibration |

### 9D: Fill Rate Sanity Check (mandatory after Day 1)

Paper fills are NOT neutral. IBKR paper fills faster, deeper, ignores
queue priority. Dual accounting helps — but after Day 1, explicitly compare:

- Paper fill rate
- Model fill rate (pessimistic queue)

**If paper > model by >20%**: Document the gap. This is expected but
psychologically important. Live production will be closer to the model
number, not the paper number. Do not wait 30 days to discover this
emotionally.

**If model > paper by >15%** (v3): Queue model is too optimistic in shock
regime. This is the worst failure mode: model says 1.2 bps, paper fills
degrade to 0.6, you rationalize it as noise. If detected, recalibrate
queue model pessimism before continuing shadow.

### Deliverable

`core_engine/microstructure/shadow/run_shadow.py` + `configs/shadow_config.yaml`

---

## Step 10: 30-Day Shadow Execution

**Purpose**: The only remaining unknown is live execution drift.
Does the 1.224 bps/trade edge survive real market friction?

### 10A: Pre-launch Checklist

| Item | Verified |
|------|----------|
| Step 7 ALL PASSED | Yes (v1.8-SHADOW-SHOCK) |
| Step 8 replay validation passed | Pending |
| Step 9 integration test passed (1 day) | Pending |
| IBKR paper account funded ($200K) | Verify |
| Polygon Stock Advanced active | Verify |
| ClickHouse running with shadow tables | Verify |
| NTP sync verified | Verify |
| `constants.py` version = v1.8-SHADOW-SHOCK | Yes |
| No code changes during 30 days (frozen) | Commit hash logged |
| Crash recovery tested | Step 9 |

### 10B: Daily Operating Procedure

**Pre-market (before 9:30 ET)**:

1. Verify IBKR Gateway running, connected to paper account
2. Verify ClickHouse accessible
3. Start shadow engine: `python -m core_engine.microstructure.shadow.run_shadow`
4. Confirm pre-flight passes (NTP, ClickHouse, crash recovery)
5. Confirm Polygon WS connected and streaming

**During session (9:45-15:45 ET)**:

- Engine runs autonomously — no manual intervention
- If kill condition fires → engine auto-pauses, log the event
- If M9 event frequency collapse alert → note it, do NOT intervene

**Post-market (after 16:00 ET)**:

1. Check daily report in `results/shadow/`
2. Review dashboard items:

| Monitor | What to check | Alert threshold |
|---------|--------------|-----------------|
| M1: Mechanism health | Amplitude, normalization speed, event frequency | Any 2/3 degraded >30% |
| M3: Fill accounting | Paper vs model fill rate, fill_optimism_ratio | Ratio > 1.5 |
| M7: Slippage | Entry/exit/cancel decomposition | Any component drift >50% |
| M8: NBBO integrity | Locked/crossed rate, quote frequency | >2% locked/crossed |
| M9: Event frequency | Events/day vs 20-day average | >50% collapse + negative P&L |
| M10a: Cross-symbol corr | Rolling 5-day pairwise P&L correlation | >0.50 avg |
| M10b: Shock clustering | Symbols firing shocks same day | ≥3 symbols |
| Loss velocity | Intraday drawdown within 30min | >25 bps + M1 weakening |
| Latency (decomposed) | Entry/cancel/fill/exit latency **by spread regime + TOD** | Absolute caps breached |
| Dual accounting | Paper P&L vs Model P&L | Divergence growing |

**Latency decomposition** (v3): Average latency during calm markets is
meaningless. Log ALL FOUR latency components with context:
1. **Entry decision latency**: event detection → order submit
2. **Cancel latency**: cancel request → acknowledgment
3. **Fill latency**: order submit → fill confirmation
4. **Exit reaction latency**: exit condition → exit order submit

Each segmented by:
- Spread ratio bucket (does latency spike during shocks?)
- Time-of-day (opening vs closing vs midday)

Shock-only strategy lives inside ~2 seconds. If shock regime latency
inflates by 40%, mean hold time balloons and stop-loss rate rises.
Latency asymmetry is a silent killer.

**Shock clustering** (v3): Correlation of *spread_ratio shock events* per
day is a forward-looking proxy. If NVDA/MSFT/TSLA all fire shocks
simultaneously, exposure clustering increases before P&L correlation
materializes. Inventory cap protects single-symbol stacking but NOT
correlated cross-symbol shock stacking.

3. Log daily observation (1-2 sentences) in `results/shadow/daily_log.md`
4. **No-change affirmation**: Log "No code/parameter/threshold changes today"
   in daily log. This sounds theatrical but enforces freeze discipline.
   Shadow fails most often because humans interfere after flat weeks or
   bad days.

### 10C: Weekly Review Protocol

Every Friday after close:

1. **Performance**: Weekly P&L, cumulative P&L, comparison to backtest trajectory
2. **Mechanism stability**: M1 3-variable surface trend over week
3. **Fill quality**: M3 fill_optimism_ratio trend, segmented by spread regime
4. **Slippage decomposition**: M7 weekly breakdown — is execution drift appearing?
5. **Spread distribution**: M6 quintile migration — is the opportunity set shifting?
6. **Latency evolution**: Are infrastructure metrics stable or degrading?
7. **Scaling estimates**: Hypothetical P&L at 500/1000 shares (from live depth data).
   **Caveat**: Paper depth ≠ real depth. IBKR paper does not simulate true queue
   priority. These estimates are directional only. Backtest already proved scaling
   death. Shadow will not resurrect it.
8. **SPY beta**: Rolling 20-day |beta| (should stay < 0.25)
9. **Event frequency**: M9 daily frequency trend — seasonal or structural?
10. **Cross-symbol P&L correlation**: M10a rolling 5-day pairwise — clustered risk?
11. **Shock event clustering**: M10b — are multiple symbols firing shocks
    simultaneously? Forward-looking exposure risk proxy
12. **Latency decomposition by regime**: Entry/cancel/fill/exit p95 during Q5
    shock events vs calm periods, segmented by spread_ratio bucket and TOD
13. **Loss velocity incidents**: Any intraday drawdown >25 bps + M1 weakening
14. **Portfolio shock stress**: Max concurrent positions, worst simultaneous
    stop-loss scenario, realized loss under correlated stops

Generate weekly markdown report: `results/shadow/week_N_report.md`

### 10D: Kill Conditions (Auto-Enforced)

These fire automatically and pause the engine:

**Per-trade (immediate)**:
- Net inventory > ±6 bps
- Ingest p95 > 250ms
- Order RTT p95 > 400ms
- Cancel ack median > 500ms
- Intraday loss > -40 bps (v1.8: raised from -25; backtest worst=-31,
  shock systems are lumpy — this is a "broken" signal, not a "bad day" signal)

**Daily close (structural)**:
- M1: all 3 dimensions degraded >30%
- Rolling 30-day mean P&L < -1.0 bps/day — **COMPOUND with two paths** (v3):
  - **Path A**: P&L negative + M1 degraded + frequency active → structural decay
  - **Path B**: P&L negative + frequency collapsed + Q5 distribution shifted
    >40% → regime death (structural liquidity change, not seasonal quiet)
  - **No kill**: P&L negative + frequency collapsed + Q5 stable → seasonal
    compression (holiday quiet), mechanism intact
  (Frequency collapse alone is NOT benign — it depends on distribution shift.)
- Fill rate < 60% of 77% baseline (< 46.2%)
- Pairwise correlation > 0.30 sustained 5 days
- 5-day peak-to-trough drawdown > 115 bps

**Alerts (operational, not auto-kill)**:
- M9: Event frequency collapsed >50% from 20-day avg AND P&L negative
- M10a: Cross-symbol pairwise P&L correlation >0.50 over 5-day window
  (lagging indicator — correlated stop-loss days)
- M10b: Shock event clustering — ≥3 symbols fire shocks on same day
  (forward-looking — exposure clusters before P&L correlation materializes)
- Loss velocity: >25 bps intraday drawdown + M1 amplitude weakening
  (catches fast structural breaks before daily -40 bps threshold hits)

**If a kill fires**: Do NOT restart until root cause identified.
Log the kill event, preserve state, and bring to quant review.

**Pre-commitment on threshold geometry**: Thresholds were calibrated on
backtest variance. Live variance may widen slightly. If a kill fires due
to threshold geometry (not structural decay), analyze the distribution
shift FIRST. Do NOT reflexively "fix" thresholds. Otherwise shadow
becomes iterative tuning, not empirical validation.

### 10E: What NOT to Do During Shadow

- DO NOT change code
- DO NOT change constants
- DO NOT adjust thresholds
- DO NOT add symbols
- DO NOT increase clip size
- DO NOT intervene on live trades
- DO NOT restart after a kill without investigation

The entire point of shadow is observing the frozen system under real friction.
Any modification invalidates the 30-day measurement window.

### 10F: End-of-Shadow Deliverable

After 30 trading days, compile comprehensive report for external quant:

1. **Executive summary**: Live P&L vs backtest baseline, edge compression estimate
2. **Mechanism health**: M1 surface evolution over 30 days (3 charts)
3. **Fill quality**: Paper vs model P&L divergence (is IBKR paper optimistic?)
4. **Slippage forensics**: M7 decomposition — where does execution friction land?
5. **Latency profile**: 30-day infrastructure stability report, decomposed by
   entry/cancel/fill/exit latency, segmented by spread regime and TOD
6. **Capacity data**: Live depth measurements → scaling model calibration
7. **SPY beta**: Did we inadvertently load index exposure?
8. **Event frequency trend**: Structural or seasonal variation?
9. **Shock clustering analysis**: M10b frequency, correlation with P&L drawdowns
10. **NBBO quality**: Data integrity over 30 days
11. **Kill condition log**: Any fires, causes, resolution
12. **Loss velocity incidents**: Timestamp, magnitude, M1 state at time
13. **Portfolio shock stress**: Worst concurrent exposure, correlated stop scenario

**Key decision metric**:

| Live mean P&L | Interpretation | Action |
|---------------|---------------|--------|
| > 1.0 bps | Edge survived live friction | Proceed to production sizing |
| 0.8 - 1.0 bps | Compressed but viable | Review slippage, consider optimization |
| 0.6 - 0.8 bps | Marginal — friction is material | Deep M7 analysis, execution improvement needed |
| < 0.6 bps | Too thin — friction kills the edge | Strategy pause, rearchitect execution |

**Statistical confidence** (v3 — pre-committed acceptance rule):

After 30 days (~150-180 trades), compute:
- Standard error of mean P&L: `SE = stdev(pnl) / sqrt(N)`
- 95% confidence interval: `mean ± 1.96 × SE`

Realistic expectation (quant calibration):
With σ ≈ 7 bps per trade (fat-tailed shock distribution) and N ≈ 160:
`SE ≈ 7 / √160 ≈ 0.55 bps → 95% CI ≈ ±1.1 bps`

This means if shadow mean prints 0.9 bps, statistically it may not differ
from 1.2 bps. The CI is wide. Accept this ex ante.

**Pre-committed acceptance rule** (FROZEN — defined before shadow starts):

| CI Lower Bound | Interpretation | Action |
|----------------|---------------|--------|
| > 0.5 bps | Edge statistically viable | Proceed to production |
| 0.0 - 0.5 bps | Marginal — insufficient confidence | Extend shadow 15 days |
| < 0.0 bps | Edge statistically dead | Strategy pause |

This rule is NOT negotiable during shadow. Define it now, apply it later.
If the distribution speaks, obey it.

**Portfolio shock clustering stress report** (weekly, v3):

In addition to per-symbol metrics, compute weekly:
- Max concurrent open positions (across all symbols)
- Max correlated stop-loss cluster (worst-case simultaneous stops)
- Realized loss under simultaneous stop scenario
- Average daily shock event correlation (spread_ratio > 2.0 clustering)

Even if per-symbol cap is 5 bps, portfolio-level exposure during high
correlation may exceed intended risk. Shock regimes rarely respect
independence.

---

## Build Sequence Summary

| Day | Task | Deliverable | Gate |
|-----|------|-------------|------|
| 1 | Step 8: Replay validator | `replay_validator.py` | 100% bucket match, ≤3% LR drift |
| 2 | Step 9A: Integration wiring | `run_shadow.py` + config | Compiles, pre-flight passes |
| 3 | Step 9B: 1-day smoke test | Integration checklist | All 11 checks pass |
| 4-33 | Step 10: 30-day shadow | Daily/weekly reports | No unresolved kills |
| 34 | Step 10F: Final report | `shadow_30d_report.md` | Quant review |

**Critical constraint**: Step 10 cannot start until Steps 8 and 9 pass.
No code changes once Step 10 begins.

---

## Risk Register (Shadow-Specific)

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| IBKR Gateway disconnects mid-session | Medium | Lost trading hours | Auto-reconnect + crash recovery |
| Polygon WS drops during volatile period | Medium | Missed events | Reconnect with backfill check |
| Paper fills unrealistically generous | High | False confidence | Dual accounting (model P&L authoritative) |
| Holiday/low-vol weeks distort metrics | Medium | Misleading averages | M9 frequency monitor, exclude from structural assessment |
| ClickHouse disk fills | Low | Logging stops | Buffer in memory, alert on disk usage |
| NTP drift during session | Low | Entry timing off | Continuous monitoring, auto-pause |
| Kill condition fires on day 2 | Low | 30-day window restarts | Investigate, fix root cause, restart window |

---

## Configuration Template

```yaml
# configs/shadow_config.yaml
version: "v1.8-SHADOW-SHOCK"

polygon:
  api_key: "${POLYGON_API_KEY}"
  subscription_tier: "advanced"

ibkr:
  host: "127.0.0.1"
  port: 7497            # TWS paper
  client_id: 10         # dedicated client ID for shadow
  paper_trading: true

clickhouse:
  url: "http://localhost:8123"
  database: "default"

portfolio:
  value: 200000.0

paths:
  state_log: "data/shadow_state.json"
  output_dir: "results/shadow"
  daily_log: "results/shadow/daily_log.md"

logging:
  level: "INFO"
  file: "logs/shadow_trading.log"
```
