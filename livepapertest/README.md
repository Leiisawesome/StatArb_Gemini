## livepapertest (production-ready live paper)

Runs the full `core_engine.paper.PaperTradingEngine` loop on **live (delayed) Polygon minute bars + trades** and routes orders to an **IBKR paper account** via IB Gateway.

### What “production-ready” means here
- **Safe-by-default**: orders are blocked unless **both** config + CLI keys are enabled.
- **External SSOT vs internal SSOT**:
  - **External SSOT**: IBKR (positions, cash, order status)
  - **Internal SSOT**: `core_engine.trading.PositionBook` (used by engine/risk); reconciled to IBKR periodically
- **Warmup**: startup warmup via Polygon REST (required for indicators/features).
- **Health + reconciliation**: periodic health log + IBKR/PositionBook reconciliation with optional “pause trading”.

### Prereqs
- **Polygon API key** in env:
  - `POLYGON_API_KEY=...`
- **IB Gateway** running and logged in (paper):
  - default port is `4002` (paper) for IB Gateway, or `7497` for TWS paper.

### Config
- Default config: `livepapertest/configs/live_paper.yaml`
- Key knobs:
  - `livepapertest.execution.enable_orders`: default `false` (first key)
  - `--enable-orders`: required (second key)
  - `LIVEPAPER_KILL_SWITCH=1`: hard override to block orders

### Run (dry run / no orders)

```bash
cd /Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini
export POLYGON_API_KEY="..."
python3 livepapertest/run_live_paper.py --config livepapertest/configs/live_paper.yaml --dry-run
```

### Run (orders enabled)

```bash
cd /Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini
export POLYGON_API_KEY="..."
python3 livepapertest/run_live_paper.py --config livepapertest/configs/live_paper.yaml --enable-orders
```

### Emergency stop (kill switch)

```bash
export LIVEPAPER_KILL_SWITCH=1
```

This blocks order submission immediately (engine still runs signals/risk).

### Output artifacts
- Journals: `livepapertest/results/journals/`
- Checkpoints: `livepapertest/results/checkpoints/`

Both are git-ignored.

### Acceptance checklist
- **Warmup** completes and engine enters RUNNING state.
- **Health logs** print every minute with non-null bar/price ages.
- **Reconciliation** runs periodically; if mismatches occur, a journal event `reconcile_mismatch` appears and orders are blocked if `pause_on_mismatch: true`.
- With `enable_orders: true` + `--enable-orders`, an IBKR paper market order can be submitted and fills update `PositionBook` via `CentralRiskManager.update_position()`.


