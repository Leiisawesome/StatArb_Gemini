# Shadow Trading Specification v1.7 — FROZEN

**Status**: LOCKED — No modifications during 30-day shadow period  
**Strategy Identity**: Liquidity Shock Normalization  
**Capital Target**: $200–500K  
**Infrastructure**: Polygon SIP (WebSocket) + IBKR Paper  

---

## 1. Strategy Mechanism

**What it is**: Compensation for warehousing short-term inventory risk during temporary spread over-extension after liquidity shocks.

**What it is not**: Directional alpha. Return prediction. Flow continuation.

**Mechanism confirmed by regression**: PnL is dominated by spread_ratio (standardized β=0.410, p<0.0001). Imbalance magnitude is secondary (β=0.073).

---

## 2. Entry Rules (Event-Level Filter)

### 2.1 Event Detection
- Volume-clock bucketing: same logic as research (ADV/200 bucket size)
- Extreme imbalance: |flow_imbalance| in top 5% (thresholds frozen per symbol from research)

### 2.2 Spread Ratio Filter
At event detection + 200ms entry delay, compute:

```
spread_ratio = spread_at_entry / baseline_spread_20_bucket_median
```

- **spread_ratio < 1.0** → ENTER (Competitive Provision sub-strategy)
- **spread_ratio > 2.0** → ENTER (Shock Compression sub-strategy)
- **1.0 ≤ spread_ratio ≤ 2.0** → SKIP (Q3/Q4 dead zone)

### 2.3 Frozen Imbalance Thresholds (from research)

| Symbol | |imbalance| threshold (p95) |
|--------|---------------------------|
| MSFT   | 0.786                     |
| NVDA   | 0.363                     |
| TSLA   | 0.350                     |
| WMT    | 0.871                     |

### 2.4 Order Placement
- **Side**: Provide liquidity AGAINST the imbalance direction
  - Buy pressure (imb > 0) → SELL at widened ask
  - Sell pressure (imb < 0) → BUY at widened bid
- **Price**: Current best bid/ask at entry time (200ms after event)
- **Type**: Limit order (passive)
- **Size**: 100 shares (flat, no scaling)

---

## 3. Exit Rules (Three-Way, First Triggered Wins)

1. **Spread Normalization**: Exit when spread ≤ 105% of pre-event baseline
   - Minimum hold: 500ms after fill (prevents churn)
   - Exit at midpoint (conservative)

2. **Timeout**: Hard exit at 30 seconds after fill
   - Exit at midpoint

3. **Stop-Loss**: Exit if midpoint moves against position by > 3 bps
   - Exit at midpoint (model assumes crossing cost)

---

## 4. Risk Rules

### 4.1 Inventory Control
- **Net inventory cap**: ±6 bps aggregate across all open positions
- **Computation**: sum of (position_direction × current_spread_bps) for all open positions
- **Enforcement**: If placing new order would exceed cap → SKIP event

### 4.2 Per-Symbol Allocation
- Max 25% of daily risk budget per symbol
- No more than 1 open position per symbol at any time

### 4.3 Daily Loss Stop
- Auto-pause if daily realized P&L < -25 bps
- Resume next trading day

---

## 5. Kill Conditions (Automatic, No Discretionary Override)

| Condition | Threshold | Action |
|-----------|-----------|--------|
| Compression half-life drift | +100% from research baseline for 10 consecutive days | AUTO-PAUSE |
| Rolling 30-day mean PnL | < 0.5 bps | AUTO-PAUSE |
| Live fill rate | < 60% of modeled baseline | AUTO-PAUSE |
| High-vol pairwise correlation | > 0.30 sustained 5 days | REDUCE to 1 concurrent |
| Compression half-life drift | +50% for 10 days | ALERT (no action) |

---

## 6. Monitoring KPIs (5 Mechanism Monitors)

### M1: Compression Half-Life
- **What**: Median time from fill to spread normalization exit
- **Baseline**: Research median (from shadow trading week 1)
- **Tracking**: Daily value, 20-day rolling median
- **Alert**: +50% drift for 10 days
- **Kill**: +100% drift for 10 days

### M2: Sub-Strategy Split
- **What**: Rolling 30-day mean PnL, hit rate, fill rate for:
  - Competitive (spread_ratio < 1.0)
  - Shock (spread_ratio > 2.0)
- **Purpose**: Identify which mechanism is degrading

### M3: Live Fill vs Modeled Fill
- **What**: For every order placed:
  - Modeled queue ahead (from research model)
  - Actual fill outcome (filled/not, time-to-fill)
  - Slippage (entry price vs intended price)
  - Stop slippage (exit price vs intended stop level)
- **Tracking**: Weekly fill delta %, slippage delta
- **Kill**: Fill rate < 60% of modeled

### M4: Net Inventory Beta
- **What**: Intraday net_inventory_bps correlation vs SPY 1-min returns
- **Purpose**: Detect drift from liquidity provider to directional exposure
- **Alert**: |correlation| > 0.3 sustained 5 days

### M5: Throughput
- **What**: Daily fills, active events, inventory cap utilization
- **Purpose**: Edge per trade is modest; frequency drives returns
- **Alert**: Fills/day drops below 50% of research baseline (3 fills/day)

---

## 7. Shadow Trading Protocol

### Duration
- 30 trading days minimum
- No early termination unless kill condition triggers

### Capital
- IBKR paper trading account
- $200K simulated capital

### Parameter Discipline
- NO parameter changes during shadow period
- NO additional filters or logic
- NO dynamic sizing
- NO discretionary overrides of kill conditions

### Weekly Review Structure
1. Mechanism metrics (M1-M5)
2. Live vs modeled drift
3. Correlation change
4. Compression drift
5. Sub-strategy health

### Success Criteria
- Live mean PnL ≥ 0.8 bps → VALIDATED
- Live mean PnL 0.5–0.8 bps → INVESTIGATE
- Live mean PnL < 0.5 bps → MODEL OPTIMISM DETECTED

### Graduation Criteria (to live capital)
- All 5 mechanism monitors within ±20% of research baseline
- No kill condition triggered
- ≥ 20 trading days of stable operation
- External quant review of shadow results

---

## 8. Research Baselines (from backtest, frozen)

| Metric | Baseline Value | Source |
|--------|---------------|--------|
| Fill rate (100 shares, 200ms delay) | 77.0% | Validation report |
| Mean PnL per fill | 1.18 bps | Validation report |
| Hit rate | 54.0% | Validation report |
| Mean hold time | ~1.3s | Stress report |
| CVaR5 | -5.69 bps | Stress report |
| True Sharpe (with zero days) | 4.01 | Stress report |
| Daily PnL mean | 7.66 bps | Stress report |
| Mean pairwise correlation | 0.012 | Validation report |
| High-vol correlation | -0.033 | Mechanism report |
| Worst day | -20.81 bps | Validation report |
| β_spread (mechanism) | 0.410 | Mechanism report |

---

## 9. Constants

```
CONSTANTS_VERSION = "v1.7-SHADOW"

ENTRY_DELAY_MS = 200
SPREAD_RATIO_COMPETITIVE_MAX = 1.0
SPREAD_RATIO_SHOCK_MIN = 2.0
STOP_LOSS_BPS = 3.0
SPREAD_NORMAL_FACTOR = 1.05
TIMEOUT_S = 30
MIN_HOLD_MS = 500
CLIP_SIZE = 100
NET_INVENTORY_CAP_BPS = 6.0
DAILY_LOSS_STOP_BPS = -25.0
MAX_POSITIONS_PER_SYMBOL = 1
PER_SYMBOL_RISK_CAP_PCT = 0.25
```

---

## Anti-Drift Clause

This specification is frozen. Any modification requires:
1. Written justification
2. External quant approval
3. New version number (v1.8+)
4. Restart of 30-day shadow period

No exception.
