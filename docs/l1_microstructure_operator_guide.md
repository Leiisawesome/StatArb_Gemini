# L1 Microstructure Operator Guide

This guide is the concrete runbook for operating the `l1_microstructure` successor package inside this repository.

It is written for this workspace:

- Repo root: `C:\Users\cheng.lei\OneDrive\Documents\GitHub\StatArb_Gemini`
- Python environment: `.venv`
- Main CLI entrypoint: `python -m l1_microstructure`

## 1. What this runbook covers

Use this guide when you want to:

1. build artifacts from L1 payload files
2. inspect saved runs
3. replay paper-historical or paper-live flows
4. run the routed-live shell with a test router
5. run IBKR smoke checks under paper-trading safeguards

This guide does **not** replace the architectural notes in `docs/l1_microstructure_state_machine.md`; it is the practical operator layer.

## 2. Known-good files already in this repo

Use these files for first runs:

- research/replay fixture payloads: `tests/fixtures/l1_state_machine/golden_payloads.json`
- small IBKR smoke payload sample: `l1_microstructure/examples/ibkr_order_smoke_payloads.json`

The fixture payload date is `2024-03-11`, so historical commands in this guide use that trade date.

## 3. Recommended operating conventions

From the repo root, use these conventions consistently:

- artifact root: `output/l1_microstructure_artifacts`
- symbol for first-run smoke tests: `AAPL`
- transition threshold for deterministic fixture runs: `0.0`

Why `0.0` for the fixture? The test suite uses it to force observable transitions on a tiny synthetic dataset.

## 4. Environment setup

### Windows PowerShell

From the repo root:

```powershell
.\.venv\Scripts\Activate.ps1
python --version
```

Install dependencies if needed:

```powershell
pip install -r requirements.txt
```

## 5. First-run quick start

If you only do one sequence, do this exact sequence.

### Step 1: Build artifacts from the fixture payloads

```powershell
python -m l1_microstructure workflow `
  --payload-file tests/fixtures/l1_state_machine/golden_payloads.json `
  --artifact-root output/l1_microstructure_artifacts `
  --symbol AAPL `
  --transition-threshold 0.0
```

Expected result:

- JSON printed to stdout
- non-zero `state_panel_rows`
- non-zero `transition_panel_rows`
- populated `artifact_ids`
- `run_id` generated for this run

Important output fields:

- `run_id`
- `artifact_ids.transition_model_id`
- `validation_passed`
- `validation_failures`
- `replay_summary`

### Step 2: List persisted runs

```powershell
python -m l1_microstructure list-runs `
  --artifact-root output/l1_microstructure_artifacts `
  --symbol AAPL `
  --trade-date 2024-03-11
```

Use this to verify that the run manifest was saved.

### Step 3: Replay the saved bundle in historical paper mode

```powershell
python -m l1_microstructure paper-historical `
  --payload-file tests/fixtures/l1_state_machine/golden_payloads.json `
  --artifact-root output/l1_microstructure_artifacts `
  --symbol AAPL `
  --trade-date 2024-03-11 `
  --transition-threshold 0.0
```

Expected result:

- JSON printed to stdout
- `update_count > 0`
- `monitoring_rows > 0`
- `artifact_bundle.transition_model` populated

## 6. Command reference for operators

## 6.1 `workflow`

Purpose:

- build state and transition panels
- calibrate state/regime/execution artifacts
- train the transition model
- run monitored replay
- validate the run
- persist a run manifest

Base form:

```powershell
python -m l1_microstructure workflow `
  --payload-file <json-or-jsonl-file> `
  --artifact-root <artifact-folder> `
  --symbol <ticker> `
  [--transition-threshold <float>]
```

Use when:

- a new payload file arrives
- you want to regenerate runtime artifacts
- you want a new run manifest for a symbol/date

## 6.2 `list-runs`

Purpose:

- inspect saved run manifests
- filter by date
- filter to validation-passing runs only
- filter by quality gate

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

Use when:

- selecting a `run_id`
- checking whether a run passed validation
- checking execution quality metrics before paper/live replay

## 6.3 `paper-historical`

Purpose:

- load historical payload input
- resolve artifacts from the artifact store
- run the paper path against a historical trade date

Example using latest eligible bundle:

```powershell
python -m l1_microstructure paper-historical `
  --payload-file tests/fixtures/l1_state_machine/golden_payloads.json `
  --artifact-root output/l1_microstructure_artifacts `
  --symbol AAPL `
  --trade-date 2024-03-11 `
  --transition-threshold 0.0
```

Example using a specific run:

```powershell
python -m l1_microstructure paper-historical `
  --payload-file tests/fixtures/l1_state_machine/golden_payloads.json `
  --artifact-root output/l1_microstructure_artifacts `
  --symbol AAPL `
  --trade-date 2024-03-11 `
  --run-id <run_id> `
  --transition-threshold 0.0
```

Safer example requiring a validation-passing bundle:

```powershell
python -m l1_microstructure paper-historical `
  --payload-file tests/fixtures/l1_state_machine/golden_payloads.json `
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

- use live-style subscription semantics against file-backed payload input
- resolve the latest or specified artifact bundle

Example:

```powershell
python -m l1_microstructure paper-live `
  --payload-file tests/fixtures/l1_state_machine/golden_payloads.json `
  --artifact-root output/l1_microstructure_artifacts `
  --symbol AAPL `
  --require-validation-passed `
  --transition-threshold 0.0
```

Use when:

- you want live-style runner semantics without external routing
- you want to check runtime monitoring and execution summary against stored artifacts

## 6.5 `live-routed`

Purpose:

- route generated execution requests through a router boundary
- test external-routing behavior
- use recovery-capable runner logic

### Immediate-fill router

```powershell
python -m l1_microstructure live-routed `
  --payload-file tests/fixtures/l1_state_machine/golden_payloads.json `
  --artifact-root output/l1_microstructure_artifacts `
  --symbol AAPL `
  --require-validation-passed `
  --router-type immediate-fill `
  --transition-threshold 0.0
```

### Latency-buffered router

```powershell
python -m l1_microstructure live-routed `
  --payload-file tests/fixtures/l1_state_machine/golden_payloads.json `
  --artifact-root output/l1_microstructure_artifacts `
  --symbol AAPL `
  --require-validation-passed `
  --router-type latency-buffered `
  --router-poll-delay 1 `
  --transition-threshold 0.0
```

### Rejecting router

```powershell
python -m l1_microstructure live-routed `
  --payload-file tests/fixtures/l1_state_machine/golden_payloads.json `
  --artifact-root output/l1_microstructure_artifacts `
  --symbol AAPL `
  --require-validation-passed `
  --router-type rejecting `
  --transition-threshold 0.0
```

Use these three router types first. They are the safest operational entrypoints.

## 6.6 `ibkr-live-smoke`

Purpose:

- verify broker connectivity and health
- do **not** submit an order

Paper-safe example:

```powershell
python -m l1_microstructure ibkr-live-smoke `
  --broker-env-file .env.ibkr
```

Only use `--allow-live-broker-routing` if you explicitly intend to lift the paper-only safeguard.

## 6.7 `ibkr-live-order-smoke`

Purpose:

- build a deterministic L1-based request from payload-backed quote state
- submit an order through the IBKR router
- poll status
- cancel it if still open

Paper-safe example:

```powershell
python -m l1_microstructure ibkr-live-order-smoke `
  --payload-file l1_microstructure/examples/ibkr_order_smoke_payloads.json `
  --symbol AAPL `
  --quantity 1 `
  --action buy `
  --broker-env-file .env.ibkr `
  --broker-order-mode limit `
  --broker-limit-offset-bps 0.0 `
  --poll-attempts 3 `
  --poll-interval-ms 250
```

Do not use this command until the health-only smoke command succeeds.

## 7. Recommended operator workflows

## 7.1 Daily research / validation workflow

1. activate `.venv`
2. run `workflow` on the target payload file
3. inspect `validation_passed`
4. inspect `list-runs --passing-only`
5. if needed, rerun `paper-historical` against the chosen `run_id`

## 7.2 Pre-paper-live workflow

1. confirm a passing bundle exists
2. run `paper-live --require-validation-passed`
3. review:
   - `execution_summary`
   - `monitoring_rows`
   - `quality_metrics`
4. only then move to `live-routed`

## 7.3 Routed-live dress rehearsal

1. start with `--router-type immediate-fill`
2. then test `--router-type latency-buffered`
3. then test `--router-type rejecting`
4. use `ibkr-live-smoke`
5. only after that, use `ibkr-live-order-smoke`

## 8. How to read command output

Most commands print a JSON object.

Common fields:

- `update_count`: number of processed state updates
- `monitoring_rows`: rows captured by the runtime monitor
- `artifact_bundle`: ids of the artifacts loaded at runtime
- `runtime_metadata`: manifest-level metadata for the loaded run
- `quality_metrics`: summarized validation/execution metrics
- `route_acknowledgement_count`: number of routed submissions

For `workflow`, focus on:

- `run_id`
- `validation_passed`
- `validation_failures`
- `replay_summary`

For `list-runs`, focus on:

- `run_count`
- `runs[].run_id`
- `runs[].trade_date`
- `runs[].quality_metrics`

## 9. Safety rules

1. Treat `live-routed --router-type ibkr-live` as a separate risk tier from simulator-backed runs.
2. Do not pass `--allow-live-broker-routing` unless you intentionally want to bypass the paper-only safety requirement.
3. Do not use IBKR order smoke until the health-only smoke path is clean.
4. Prefer `--require-validation-passed` when `run-id` is omitted.
5. Prefer quality gates when selecting bundles for paper/live flows.

## 10. Troubleshooting

### Error: no events supplied for symbol

Cause:

- payload file does not contain the symbol you requested
- session filtering removed all events

Action:

- verify `sym` / `symbol` fields
- verify the symbol passed to the CLI
- start with `AAPL` and `tests/fixtures/l1_state_machine/golden_payloads.json`

### Error: state panel is empty or transition panel is empty

Cause:

- payload file too small
- thresholds too strict
- no usable quote/trade sequence

Action:

- use the fixture payload first
- set `--transition-threshold 0.0` for smoke tests

### Error: no validation-passing run manifest found

Cause:

- no prior workflow run passed validation
- quality gate is too strict

Action:

- run `list-runs` without `--passing-only`
- relax the quality gate temporarily
- specify `--run-id` explicitly if needed

### Error: payload file did not produce any observable state

Cause:

- file lacks enough quote data to create a current book

Action:

- ensure the payload contains quotes with bid/ask/size fields

## 11. Minimal validation checklist before operational use

Before treating any new dataset or symbol as ready:

- `workflow` completes successfully
- run manifest exists
- `state_panel_rows > 0`
- `transition_panel_rows > 0`
- `paper-historical` succeeds
- `paper-live` succeeds
- `live-routed` succeeds with `immediate-fill`
- `live-routed` succeeds with `latency-buffered`
- IBKR health-only smoke succeeds before any order smoke

## 12. Repo-specific test command

To validate the successor package test slice directly:

```powershell
pytest tests/unit/l1_state_machine -q
```

Use this when changing package code, router behavior, artifact logic, or CLI flags.

## 13. Suggested next operational step

For this repo, the most practical next action is:

1. run the exact `workflow` command in Section 5
2. capture the emitted `run_id`
3. run `paper-historical`
4. then move to `live-routed` with `immediate-fill`

That sequence is the shortest supported path from fixture data to end-to-end operator confidence.
