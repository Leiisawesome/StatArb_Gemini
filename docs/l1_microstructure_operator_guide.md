# L1 Microstructure Operator Guide

This guide is the practical runbook for operating the `l1_microstructure` package in this repository.

It is intentionally narrower than the architecture notes in `docs/l1_microstructure_state_machine.md`. The goal here is to explain what an operator can run today, what each command expects, and what the current safety boundaries are.

## 1. Important scope note

The current CLI is source-backed:

1. `workflow` and `paper-historical` load data through the Polygon REST source using `--symbol` and `--trade-date`.
2. `paper-live` and `live-routed` consume the Polygon WebSocket-style live subscription path.
3. The CLI does not currently expose the older `--payload-file` workflow documented in previous versions of this guide.
4. The CLI also does not currently expose test-only deterministic router options such as `immediate-fill`, `latency-buffered`, or `rejecting`.

Those deterministic flows still exist in tests and lower-level runner APIs, but they are not current operator-facing CLI entrypoints.

## 2. What this guide covers

Use this guide when you want to:

1. build artifacts for a symbol and trade date
2. inspect saved run manifests
3. replay historical or live-style paper flows from stored artifacts
4. run the routed-live shell against the broker routing boundary
5. run Interactive Brokers smoke checks under paper-only safeguards

## 3. Environment and prerequisites

Repository root:

```text
C:\Users\cheng.lei\OneDrive\Documents\GitHub\StatArb_Gemini
```

Recommended Python environment:

```powershell
.\.venv\Scripts\Activate.ps1
python --version
pip install -r requirements.txt
```

External runtime requirements:

1. Polygon or Massive credentials for source-backed market data access
2. network connectivity to the chosen market-data source
3. IBKR Gateway or TWS plus broker configuration if you intend to use broker smoke commands or routed-live broker routing

For broker routing, this repository includes `broker.env` as the expected environment-file pattern.

## 3.1 Required credentials and environment variables

### Polygon or Massive API key

The historical and live source-backed commands require a Massive API key.

The runtime resolves the key in this order:

1. an explicit API key passed into the Massive config object
2. `MASSIVE_API_KEY` from the process environment
3. `MASSIVE_API_KEY` from a repository-root `.env` file

Practical recommendation:

1. set `MASSIVE_API_KEY` in the active shell for manual operation, or
2. place the key in a repository `.env` file for local development

Example PowerShell setup:

```powershell
$env:MASSIVE_API_KEY = "your_api_key"
```

Minimal repository `.env` example:

```text
MASSIVE_API_KEY=your_api_key
```

### IBKR environment file

Broker-backed commands use the Interactive Brokers router boundary and expect IBKR connection settings.

This repository already includes `broker.env` with the current pattern:

```text
ACTIVE_BROKER=interactive_brokers
IBKR_HOST=127.0.0.1
IBKR_PORT=4002
IBKR_CLIENT_ID=1
IBKR_PAPER_TRADING=true
IBKR_OUTSIDE_RTH=true
```

Optional broker keys:

1. `IBKR_ACCOUNT_ID`
2. `IBKR_ACCOUNT`

Lookup behavior for broker config:

1. when `--broker-env-file` is provided, that file is loaded first
2. process environment variables then fill in any missing keys

Operational recommendation:

1. keep `IBKR_PAPER_TRADING=true` for smoke and rehearsal flows
2. do not pass `--allow-live-broker-routing` unless you explicitly intend to bypass the paper-only safeguard

## 4. How the current workflow operates

The operator path is artifact-driven.

The usual sequence is:

1. run `workflow` for a symbol and trade date
2. inspect the resulting manifest with `list-runs`
3. replay the chosen bundle with `paper-historical` or `paper-live`
4. use `live-routed` with a paper broker account to qualify the routing boundary
5. use `trading-daemon` for any supervised live-capital operation
6. use IBKR smoke paths only after the broker boundary is configured and healthy

Commands emit JSON to stdout. That JSON is the primary operational output.

## 5. First-run quick start

For a first live system check, use a single liquid symbol and one known trading day.

Example sequence:

### Step 1: Build a workflow run

```powershell
python -m l1_microstructure workflow `
  --artifact-root output/l1_microstructure_artifacts `
  --symbol AAPL `
  --trade-date 2024-03-11 `
  --transition-threshold 0.0
```

Focus on these output fields:

1. `run_id`
2. `state_panel_rows`
3. `transition_panel_rows`
4. `validation_passed`
5. `validation_failures`
6. `replay_summary`

### Step 2: List saved runs

```powershell
python -m l1_microstructure list-runs `
  --artifact-root output/l1_microstructure_artifacts `
  --symbol AAPL `
  --trade-date 2024-03-11
```

Use this to confirm that the run manifest exists and to inspect any quality metrics captured in metadata.

### Step 3: Replay the saved bundle historically

```powershell
python -m l1_microstructure paper-historical `
  --artifact-root output/l1_microstructure_artifacts `
  --symbol AAPL `
  --trade-date 2024-03-11 `
  --require-validation-passed `
  --transition-threshold 0.0
```

Focus on these output fields:

1. `update_count`
2. `monitoring_rows`
3. `artifact_bundle`
4. `runtime_metadata`
5. `quality_metrics`

## 6. Command reference

## 6.1 `workflow`

Purpose:

1. load historical events for one symbol and trade date
2. build state and transition panels
3. calibrate runtime artifacts
4. train the transition model
5. run rolling out-of-sample validation
6. run monitored replay
7. persist a run manifest and artifact ids

Base form:

```powershell
python -m l1_microstructure workflow `
  --artifact-root <artifact-folder> `
  --symbol <ticker> `
  --trade-date <yyyy-mm-dd> `
  [--transition-threshold <float>]
```

Operational notes:

1. `--trade-date` is required.
2. The command uses the historical source, not a local payload file.
3. `--transition-threshold 0.0` is useful for smoke tests and tiny datasets because it forces observable transitions.
4. A full-day workflow run can take materially longer than broker smoke commands or single-quote checks because it paginates historical quotes and trades before artifact generation begins.

## 6.2 `list-runs`

Purpose:

1. inspect saved run manifests for a symbol
2. filter by trade date
3. restrict to validation-passing runs
4. apply quality-gate filters

Examples:

```powershell
python -m l1_microstructure list-runs `
  --artifact-root output/l1_microstructure_artifacts `
  --symbol AAPL
```

```powershell
python -m l1_microstructure list-runs `
  --artifact-root output/l1_microstructure_artifacts `
  --symbol AAPL `
  --trade-date 2024-03-11 `
  --passing-only
```

```powershell
python -m l1_microstructure list-runs `
  --artifact-root output/l1_microstructure_artifacts `
  --symbol AAPL `
  --passing-only `
  --max-drift-tracking-error-bps 3.0 `
  --max-unseen-edge-rate 0.3
```

## 6.3 `paper-historical`

Purpose:

1. load historical events for one symbol and trade date
2. resolve a stored artifact bundle by latest eligible run or explicit `run_id`
3. run the simulator-backed paper path against those historical events

Examples:

Use the latest eligible bundle for a date:

```powershell
python -m l1_microstructure paper-historical `
  --artifact-root output/l1_microstructure_artifacts `
  --symbol AAPL `
  --trade-date 2024-03-11 `
  --transition-threshold 0.0
```

Use a specific run id:

```powershell
python -m l1_microstructure paper-historical `
  --artifact-root output/l1_microstructure_artifacts `
  --symbol AAPL `
  --trade-date 2024-03-11 `
  --run-id <run_id> `
  --transition-threshold 0.0
```

Require a validation-passing bundle and apply quality gates:

```powershell
python -m l1_microstructure paper-historical `
  --artifact-root output/l1_microstructure_artifacts `
  --symbol AAPL `
  --trade-date 2024-03-11 `
  --require-validation-passed `
  --max-drift-tracking-error-bps 3.0 `
  --max-unseen-edge-rate 0.3 `
  --transition-threshold 0.0
```

## 6.4 `paper-live`

Purpose:

1. subscribe to the live source for one symbol
2. resolve a stored artifact bundle by latest eligible run or explicit `run_id`
3. run the simulator-backed paper path using live-style subscription semantics

Example:

```powershell
python -m l1_microstructure paper-live `
  --artifact-root output/l1_microstructure_artifacts `
  --symbol AAPL `
  --require-validation-passed
```

Operational notes:

1. This command uses the live subscription source, so external connectivity and credentials must be working.
2. It does not require `--trade-date` because it is not resolving historical events.

## 6.5 `live-routed`

This command is a lightweight embedding and paper-account qualification path,
not the production trading runtime. It rejects live-capital routing. Use
`trading-daemon` with the production operator guide for supervised operation.

Purpose:

1. subscribe to the live source for one symbol
2. resolve a stored artifact bundle by latest eligible run or explicit `run_id`
3. route generated execution requests through the broker routing boundary instead of the internal simulator

Example:

```powershell
python -m l1_microstructure live-routed `
  --artifact-root output/l1_microstructure_artifacts `
  --symbol AAPL `
  --require-validation-passed `
  --broker-env-file broker.env
```

More explicit example with order-mode settings:

```powershell
python -m l1_microstructure live-routed `
  --artifact-root output/l1_microstructure_artifacts `
  --symbol AAPL `
  --require-validation-passed `
  --broker-env-file broker.env `
  --broker-order-mode limit `
  --broker-limit-offset-bps 0.0
```

Safety notes:

1. The current CLI routes through the IBKR broker router boundary.
2. `--allow-live-broker-routing` lifts the paper-only safeguard and should be treated as a separate operational risk tier.
3. If you need deterministic immediate-fill or rejecting routers, use the lower-level runner APIs or the test harness, not the CLI.

## 6.6 `ibkr-live-smoke`

Purpose:

1. verify broker connectivity and health
2. return current open order ids
3. avoid order submission

Example:

```powershell
python -m l1_microstructure ibkr-live-smoke `
  --broker-env-file broker.env
```

Only use `--allow-live-broker-routing` if you explicitly intend to bypass the paper-only safeguard.

## 6.7 `ibkr-live-order-smoke`

Purpose:

1. derive a deterministic request from the latest observed L1 quote state
2. submit an order through the IBKR broker router
3. poll order status
4. cancel the order if it remains open

Example:

```powershell
python -m l1_microstructure ibkr-live-order-smoke `
  --symbol AAPL `
  --quantity 1 `
  --action buy `
  --broker-env-file broker.env `
  --broker-order-mode limit `
  --broker-limit-offset-bps 0.0 `
  --poll-attempts 3 `
  --poll-interval-ms 250
```

Operational notes:

1. This command no longer consumes a local payload file.
2. It constructs the request from the latest quote returned by the REST path.
3. Do not use it until `ibkr-live-smoke` is healthy.

Expected healthy outcome:

1. `acknowledgement.status` is `accepted`
2. `cancel_attempted` is `true` when the order remains open long enough to be polled
3. `cancel_succeeded` is `true`
4. at least one execution report ends in `cancelled`
5. `final_open_order_ids` is empty
6. `health.connected` is `true` and `health.status` is `healthy`

Example success signature:

```json
{
  "acknowledgement": {
    "external_order_id": "4",
    "reason": "accepted",
    "status": "accepted"
  },
  "cancel_attempted": true,
  "cancel_succeeded": true,
  "diagnostics": null,
  "execution_reports": [
    {
      "status": "cancelled",
      "reason": "broker order cancelled",
      "symbol": "AAPL"
    }
  ],
  "final_open_order_ids": [],
  "health": {
    "connected": true,
    "status": "healthy",
    "open_order_count": 0,
    "last_error": null
  },
  "open_order_ids_before_cancel": ["4"],
  "router_type": "ibkr-live"
}
```

Operational interpretation:

1. the broker accepted the smoke order submission
2. the order stayed open long enough for the smoke path to observe and cancel it
3. the router finished with no tracked open orders and no active connectivity error

## 7. How to read command output

Most commands print one JSON object.

Common fields:

1. `update_count`: number of processed state updates
2. `monitoring_rows`: number of runtime-monitor rows captured
3. `artifact_bundle`: artifact ids loaded at runtime
4. `runtime_metadata`: manifest metadata associated with the loaded run
5. `quality_metrics`: summarized validation and execution-quality metrics
6. `route_acknowledgement_count`: number of routed submissions acknowledged

For `workflow`, focus on:

1. `run_id`
2. `validation_passed`
3. `validation_failures`
4. `validation_summary`
5. `replay_summary`

For `list-runs`, focus on:

1. `run_count`
2. `runs[].run_id`
3. `runs[].trade_date`
4. `runs[].quality_metrics`

## 8. Recommended operating sequence

For a conservative operator workflow:

1. activate `.venv`
2. run `workflow`
3. inspect `validation_passed` and `validation_failures`
4. inspect `list-runs --passing-only`
5. run `paper-historical`
6. run `paper-live`
7. run `ibkr-live-smoke`
8. only then consider paper-account `live-routed` or `ibkr-live-order-smoke`

## 9. Safety rules

1. Prefer `--require-validation-passed` whenever `--run-id` is omitted.
2. Prefer explicit quality gates when selecting bundles for paper or live operation.
3. Treat `live-routed` as a paper-account qualification shell, not a production runtime.
4. Use `trading-daemon` for live capital; it owns reconciliation, lifecycle controls,
   persistent audit state, exposure gates, and flattening.
5. Use `--allow-live-broker-routing` only with explicitly controlled broker smoke
   commands; `live-routed` rejects this flag.
6. Do not use `ibkr-live-order-smoke` before `ibkr-live-smoke` succeeds cleanly.

## 10. Troubleshooting

### Error: no events supplied for symbol

Cause:

1. the historical source returned no events for the requested symbol and trade date
2. the requested market session was empty or unavailable
3. credentials or connectivity prevented data retrieval

Action:

1. verify the symbol and date you passed to the CLI
2. verify Polygon or Massive credentials are configured
3. start with a liquid symbol such as `AAPL`
4. start with a known regular trading day such as `2024-03-11`

### Error: state panel is empty or transition panel is empty

Cause:

1. the retrieved data was too sparse
2. thresholds were too strict for the available sample
3. the quote and trade sequence did not produce a usable panel

Action:

1. retry with `--transition-threshold 0.0`
2. choose a more liquid symbol or fuller session
3. verify the upstream source is returning both quotes and trades

### Error: no validation-passing run manifest found

Cause:

1. no prior workflow run passed validation
2. the selected quality gate is too strict
3. there is no saved run for the requested symbol or date

Action:

1. run `list-runs` without `--passing-only`
2. relax the quality gate temporarily
3. specify `--run-id` explicitly if you want a known bundle

### Error: massive client is required for IBKR smoke request construction

Cause:

1. the `massive` package is not installed in the active environment

Action:

1. install dependencies from `requirements.txt`
2. confirm the active environment is the repository `.venv`

### Error: `MASSIVE_API_KEY` is required for IBKR smoke request construction

Cause:

1. the latest quote lookup has no usable API key configured

Action:

1. export `MASSIVE_API_KEY`
2. retry the smoke command after verifying the environment is active

### Error: `IBKR error 502: Couldn't connect to TWS`

Cause:

1. IBKR Gateway or TWS is not running
2. API socket access is not enabled in TWS or Gateway
3. the configured host or port does not match the running broker endpoint
4. the command is pointed at paper port `4002`, but the local broker process is listening on a different port

Action:

1. start IBKR Gateway or TWS
2. confirm `Enable ActiveX and Socket EClients` is enabled in the IBKR API settings
3. confirm the socket port matches the values in `broker.env`
4. for paper trading, verify the expected port for your installation, commonly `4002` for IB Gateway or `7497` for TWS
5. rerun `python -m l1_microstructure ibkr-live-smoke --broker-env-file broker.env` before attempting any broker order smoke

### Error: `IBKR error 321 ... The API interface is currently in Read-Only mode.`

Cause:

1. IBKR Gateway or TWS is reachable and accepting API connections
2. the API configuration is still set to read-only, so market-data and account checks work but order placement is rejected

Action:

1. open IBKR Gateway or TWS API settings
2. disable `Read-Only API`
3. keep socket clients enabled and keep the configured host and port aligned with `broker.env`
4. rerun `python -m l1_microstructure ibkr-live-smoke --broker-env-file broker.env`
5. rerun `python -m l1_microstructure ibkr-live-order-smoke --symbol AAPL --quantity 1 --action buy --broker-env-file broker.env --broker-order-mode limit --broker-limit-offset-bps 0.0 --poll-attempts 3 --poll-interval-ms 250`

Operational note:

1. the CLI now emits a `diagnostics` field for this case so the smoke JSON explicitly identifies `read_only_api_mode` and points to the required remediation

### Error: `KeyboardInterrupt` during `workflow`

Cause:

1. the workflow was interrupted while the historical source was still paginating quote or trade data
2. the command was treated like a quick smoke test even though it performs full-session historical retrieval before fitting artifacts
3. vendor or network latency made the historical fetch noticeably slower than expected

Action:

1. retry the command and allow more time for the historical fetch to complete
2. verify the market-data path with a lighter check before retrying, such as a single REST quote lookup
3. do not treat this interruption alone as evidence that Polygon credentials are missing if simple quote retrieval already works

## 11. Minimal readiness checklist

Before treating a symbol or dataset as operationally ready:

1. `workflow` completes successfully
2. `state_panel_rows > 0`
3. `transition_panel_rows > 0`
4. a run manifest exists in the artifact store
5. `paper-historical` succeeds
6. `paper-live` succeeds
7. `ibkr-live-smoke` succeeds before any broker order smoke

## 12. Test-slice command

When changing package code, runner behavior, artifact logic, or CLI flags, validate the main successor-package slice with:

```powershell
pytest tests/unit/l1_state_machine -q
```

When you need an IBKR-only pre-flight check before broader workflow or live work, run:

```powershell
pytest tests/unit/l1_state_machine/test_ibkr_functionality.py -q
```

When you need a fixture-backed workflow and historical replay pre-flight check before broader end-to-end work, run:

```powershell
pytest tests/unit/l1_state_machine/test_workflow_preflight.py -q
```

When you need a real source-backed Polygon connectivity pre-flight check before a full historical workflow run, run:

```powershell
pytest tests/integration/l1_state_machine/test_massive_source_smoke.py -q
```

When you need a bounded real source-backed workflow pre-flight check before the full-day `workflow` command, run:

```powershell
pytest tests/integration/l1_state_machine/test_massive_workflow_smoke.py -q
```

When you need a bounded broker-backed routed-live pre-flight check after `ibkr-live-order-smoke` is already healthy, run:

```powershell
pytest tests/integration/l1_state_machine/test_ibkr_routed_live_smoke.py -q
```

This slice uses fixture events plus the real IBKR router, confirms at least one routed order is accepted, and then cancels the open order so the entire path stays finite.

Expected healthy outcome:

1. the test passes as a single integration slice
2. at least one routed acknowledgement is `accepted`
3. at least one routed execution report ends in `cancelled`
4. final router health remains connected with `open_order_count == 0`

Example success signature:

```text
tests/integration/l1_state_machine/test_ibkr_routed_live_smoke.py .                                 [100%]

1 passed in ~2.5s
```

Operational interpretation:

1. the real IBKR router accepted a routed order from the live runner
2. the test was able to cancel the open routed order cleanly
3. no routed order remained open when the bounded smoke finished

## 13. Practical next step

For this repository, the shortest supported operator path is:

1. run `workflow`
2. capture the emitted `run_id`
3. run `list-runs`
4. run `paper-historical`
5. verify broker health with `ibkr-live-smoke`

That sequence gives you the fastest route from raw source-backed ingestion to an artifact-backed replay and a broker-boundary health check.
