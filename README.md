# StatArb_Gemini

StatArb_Gemini is now centered on `l1_microstructure`, a standalone L1 market microstructure research and execution framework for Massive equity quote and trade data.

The package replaces an older, more tightly coupled design with a successor architecture built around a finite partially observed state machine. It is intentionally isolated from legacy trading infrastructure so the microstructure model can be calibrated, validated, replayed, and operated on its own terms.

## Documentation map

Use the repository documents by role:

1. `README.md` gives the repository-level overview, setup, and main command surface.
2. `docs/l1_microstructure_operator_guide.md` is the operator runbook for the current CLI.
3. `docs/l1_microstructure_state_machine.md` explains the model and runtime architecture.
4. `docs/l1_microstructure_thesis_edge_and_state_vector.md` explains how edge comes from the state vector and transitions.
5. `docs/l1_microstructure_package_plan.md` describes the implemented package structure, contract seams, and remaining roadmap.
6. `docs/production_operator_guide.md` covers the supervised daemon, terminal console, safety controls, and paper qualification.
7. `docs/transparent_engine_v2.md` defines the stronger transparent engine, promotion gates, and frozen paper shadow campaign.

## What `l1_microstructure` is

At a high level, the package turns a stream of L1 quote and trade events into:

1. an observed microstructure state
2. a slower latent regime estimate
3. a regularized transition graph between states
4. edge-conditioned forward-drift estimates
5. trade intents, sizing decisions, and execution outcomes

The design thesis is that short-horizon intraday alpha is better expressed through state transitions than through feature thresholds alone. The framework therefore centers on a semi-Markov transition kernel with drift diagnostics, confidence controls, and execution-aware decision rules.

## What it does

The package supports three main use cases:

1. Research workflows that build datasets, calibrate artifacts, train a transition model, run rolling out-of-sample validation, and persist run manifests.
2. Replay and paper-trading flows that load stored artifact bundles and evaluate the state machine on historical or live-style market data.
3. Routed-live shells and broker smoke paths that keep broker integration at the outer boundary rather than inside the core model.

In practical terms, it gives you a reproducible path from raw L1 events to a saved artifact bundle and a monitored execution summary.

## Core model flow

The runtime loop implemented by `L1MicrostructureStateMachine` is:

1. Ingest a normalized market event.
2. Update observable state features.
3. Infer the current latent regime.
4. Detect whether the new observation constitutes a state transition.
5. Register pending forward outcomes for later drift resolution.
6. Score the transition edge and produce a posterior trade intent.
7. Apply risk limits and portfolio-aware sizing.
8. Simulate or route execution.
9. Track fills, open positions, and monitoring snapshots.

The current state vector is described in the design notes as:

`X_t = (S_t, Q_t, I_t, F_t, V_t)`

where the package models spread, quote pressure, trade imbalance, flicker intensity, and realized microprice volatility.

## Architecture

The package is organized as a set of narrow modules with explicit boundaries.

| Module | Responsibility |
| --- | --- |
| `l1_microstructure/events.py` | Normalized quote and trade event contracts |
| `l1_microstructure/features.py` | Event-to-state projection |
| `l1_microstructure/regime.py` | Regime inference over slower context windows |
| `l1_microstructure/transitions.py` | Transition detection, Dirichlet smoothing, entropy, drift diagnostics |
| `l1_microstructure/decision.py` | Posterior trade decision logic |
| `l1_microstructure/execution.py` | Latency-shifted execution and fill modeling |
| `l1_microstructure/risk.py` | Sizing constraints, drawdown protection, exposure controls |
| `l1_microstructure/portfolio.py` | Cross-sectional allocation with shrinkage and sector caps |
| `l1_microstructure/pipeline.py` | Runtime orchestration of the state machine |
| `l1_microstructure/workflow.py` | Artifact-producing research workflow |
| `l1_microstructure/artifacts/` | Persistent artifact storage, bundle loading, run selection |
| `l1_microstructure/validation/` | Rolling out-of-sample validation harness |
| `l1_microstructure/live/` | Paper runners, routed-live runner, router adapters |
| `l1_microstructure/ingest/` | Massive REST/WebSocket sources and payload normalization |

## Artifact-driven workflow

The research workflow in `l1_microstructure/workflow.py` builds and persists a complete runtime bundle. A typical run does the following:

1. Build full state and transition panels from normalized market events.
2. Fit state calibration, regime calibration, and execution calibration artifacts.
3. Train the empirical transition model at the configured runtime horizon.
4. Run rolling out-of-sample validation with retraining.
5. Replay the resulting runtime bundle through the paper runner.
6. Persist a run manifest and all artifact identifiers.

Artifacts are stored under the selected artifact root and include:

1. state calibration
2. regime calibration
3. execution calibration
4. transition model
5. validation report
6. monitored replay
7. run manifest

CLI commands print JSON to stdout. For the full operational runbook and command interpretation, use `docs/l1_microstructure_operator_guide.md`.

## Command-line interface

The main entrypoint is:

```powershell
python -m l1_microstructure <command> [options]
```

Current commands implemented by `l1_microstructure/cli.py` are:

| Command | Purpose |
| --- | --- |
| `workflow` | Load historical data, build artifacts, validate, replay, and persist a run manifest |
| `transparent-workflow` | Build and validate a transparent v2 shadow candidate from historical data |
| `list-runs` | Inspect saved run manifests and filter by date, pass/fail, or quality gates |
| `list-transparent-runs` | Inspect transparent v2 manifests and filter to validation-approved runs |
| `paper-historical` | Load a stored artifact bundle and run the paper path against historical data |
| `paper-live` | Load a stored artifact bundle and run the paper path against the live subscription flow |
| `live-routed` | Exercise the lightweight routed boundary against a paper broker account |
| `ibkr-live-smoke` | Check broker health and list open order ids |
| `ibkr-live-order-smoke` | Submit, poll, and cancel a paper-safe routed broker order |

### Example commands

Build a leakage-safe expanding walk-forward run by repeating `--trade-date` for completed sessions:

```powershell
python -m l1_microstructure workflow `
  --artifact-root output/l1_microstructure_artifacts `
  --symbol AAPL `
  --trade-date 2024-03-06 `
  --trade-date 2024-03-07 `
  --trade-date 2024-03-08 `
  --trade-date 2024-03-11 `
  --trade-date 2024-03-12
```

After the configured minimum of four training sessions, each later session is
evaluated against prior sessions only. Edge direction uses equal-weighted
per-session means and abstains when session support, sign consensus, or
leave-one-session-out directional reliability is weak.
Feature, regime, transition, and replay state reset at every session boundary. A single
`--trade-date` remains available for smoke testing and uses the legacy intraday
half split.

Inspect saved runs:

```powershell
python -m l1_microstructure list-runs `
  --artifact-root output/l1_microstructure_artifacts `
  --symbol AAPL `
  --trade-date 2024-03-11
```

Replay the latest eligible historical bundle:

```powershell
python -m l1_microstructure paper-historical `
  --artifact-root output/l1_microstructure_artifacts `
  --symbol AAPL `
  --trade-date 2024-03-11 `
  --require-validation-passed `
  --transition-threshold 0.0
```

Run the live subscription path in paper mode:

```powershell
python -m l1_microstructure paper-live `
  --artifact-root output/l1_microstructure_artifacts `
  --symbol AAPL `
  --require-validation-passed
```

Run the routed-live shell:

```powershell
python -m l1_microstructure live-routed `
  --artifact-root output/l1_microstructure_artifacts `
  --symbol AAPL `
  --require-validation-passed `
  --broker-env-file broker.env
```

`live-routed` is an embedding and paper-account qualification shell. It rejects
live-capital routing. Use `trading-daemon` for supervised live operation.

Check IBKR connectivity at the routing boundary:

```powershell
python -m l1_microstructure ibkr-live-smoke --broker-env-file broker.env
```

Submit a paper-safe broker smoke order:

```powershell
python -m l1_microstructure ibkr-live-order-smoke `
  --symbol AAPL `
  --quantity 1 `
  --action buy `
  --broker-env-file broker.env
```

## Runtime assumptions

The current CLI is source-backed:

1. `workflow` and `paper-historical` use the historical Massive REST path.
2. `paper-live` and `live-routed` use the live subscription path.
3. broker smoke commands operate through the IBKR router boundary.

That means local setup is not complete until market-data credentials and, when needed, broker configuration are present.

For broker-backed commands, a reachable IBKR Gateway or TWS session is also assumed.

## Configuration defaults

The framework control surface is defined in `l1_microstructure/config.py`. Important defaults include:

| Area | Example defaults |
| --- | --- |
| Features | 10 second trade window, 600 second micro-vol window, 1800 second slow context window |
| Regimes | Holding-time priors for calm, execution flow, liquidity shock, and competitive liquidity |
| Transitions | Mahalanobis threshold `2.75`, Dirichlet alpha `0.25`, runtime drift horizon `3000 ms` |
| Decisions | Entry probability threshold `0.62`, transaction cost `1.2 bps`, minimum alpha score `0.15` |
| Execution | Latency `100 ms`, base fill probability `0.7`, adverse selection penalty `0.4` |
| Risk | Starting equity `1,000,000`, daily drawdown limit `3%`, max position fraction `5%` |
| Portfolio | Shrinkage `0.20`, max weight `10%`, sector cap `25%` |

For deterministic small-sample tests, the suite commonly sets `--transition-threshold 0.0` to force observable transitions.

## Repository layout

The repository is now primarily a single-package workspace:

```text
StatArb_Gemini/
├── l1_microstructure/
│   ├── artifacts/
│   ├── calibration/
│   ├── datasets/
│   ├── ingest/
│   ├── labeling/
│   ├── live/
│   ├── monitoring/
│   ├── replay/
│   ├── training/
│   ├── validation/
│   ├── cli.py
│   ├── config.py
│   ├── pipeline.py
│   └── workflow.py
├── docs/
├── tests/
├── requirements.txt
└── broker.env
```

## Setup

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

The runtime dependencies include `pandas`, `numpy`, `scikit-learn`, `statsmodels`, `websockets`, `aiohttp`, `massive`, `ibapi`, and `pytest`.

## Required credentials and environment

The current package is source-backed, so setup is not complete until market-data and, if needed, broker credentials are available.

### Massive API key

Historical and live market-data paths require a Massive API key.

The runtime resolves the API key in this order:

1. an explicit API key passed into the Massive config object
2. `MASSIVE_API_KEY` from the process environment
3. `MASSIVE_API_KEY` from a repository-root `.env` file

Example PowerShell setup:

```powershell
$env:MASSIVE_API_KEY = "your_api_key"
```

Or use a repository `.env` file:

```text
MASSIVE_API_KEY=your_api_key
```

### IBKR broker configuration

Broker-backed commands such as `live-routed`, `ibkr-live-smoke`, and `ibkr-live-order-smoke` use the Interactive Brokers router boundary.

The repository includes [broker.env](broker.env#L1) as the expected environment-file pattern. Current keys include:

1. `ACTIVE_BROKER=interactive_brokers`
2. `IBKR_HOST=127.0.0.1`
3. `IBKR_PORT=4002`
4. `IBKR_CLIENT_ID=1`
5. `IBKR_PAPER_TRADING=true`
6. `IBKR_OUTSIDE_RTH=true`
7. optional `IBKR_ACCOUNT_ID` or `IBKR_ACCOUNT`

When `--broker-env-file` is used, values from that file are loaded first and process environment variables fill in any missing keys.

### Minimal local setup example

For first-time local setup, the simplest arrangement is:

Repository `.env` for market data:

```text
MASSIVE_API_KEY=your_api_key
```

Repository `broker.env` for broker routing:

```text
ACTIVE_BROKER=interactive_brokers
IBKR_HOST=127.0.0.1
IBKR_PORT=4002
IBKR_CLIENT_ID=1
IBKR_PAPER_TRADING=true
IBKR_OUTSIDE_RTH=true
```

Example broker smoke command:

```powershell
python -m l1_microstructure ibkr-live-smoke --broker-env-file broker.env
```

`--allow-live-broker-routing` disables the paper-only safeguard and should be treated as a separate operational risk decision.

## Supervised production runtime

The production path is a separate daemon and terminal console. It runs one state
machine per symbol, records lifecycle and order state in SQLite, reconciles IBKR
before enabling entries, and binds its authenticated API to localhost only.

Initial setup:

```bash
uv sync --extra dev
trading-secret MASSIVE_API_KEY
trading-secret MASSIVE_API_KEY --validate
trading-secret TRADING_CONSOLE_TOKEN --generate
cp config/production.example.json config/production.json
```

After replacing the promoted run ids in `config/production.json`, start paper mode:

```bash
trading-daemon --config config/production.json
trading-console
```

The daemon performs a read-only, redacted configuration preflight before it
constructs market-data or broker clients. Missing credentials, unavailable or
unapproved artifacts, unwritable ledger paths, and paper/live account-mode
mismatches fail startup before any routing boundary is opened.

Run only that gate with machine-readable JSON output:

```bash
trading-daemon --config config/production.json --preflight
```

The command exits `0` on success or `2` on a failed check and never constructs
runtime infrastructure.

The authenticated daemon API separates `/health` liveness from `/ready` trading
eligibility. `/ready` returns HTTP `503` with stable machine-readable check codes
until lifecycle, kill-switch, model, warmup, market-data, broker, and
reconciliation requirements pass. `/status` retains the detailed operator view
used by `trading-console`.

Run the deterministic offline production safety drills before paper-session
qualification:

```bash
trading-qualify
```

The command exercises restart fail-closed behavior, broker disconnect, stale
feed, order rejection, and flatten timeout handling against temporary ledgers
and in-process infrastructure boundaries. It emits one JSON report and exits `0`
when every drill passes or `2` when any drill fails. It does not load production
configuration, credentials, artifacts, market-data clients, or broker clients.

Follow the complete
[paper-trading qualification runbook](docs/paper_trading_qualification_runbook.md)
for the frozen ten-session campaign, daily evidence capture, failure rules, and
separate broker-recovery drills.

Before session 1, the read-only `trading-paper-ready` command combines the
production preflight with clean-commit, fresh-ledger, pinned v1/v2 artifact,
conservative-risk, and counted/drill isolation checks. Its JSON freeze record
contains only a hash of the configured paper account.

After every attempted regular-hours paper session, finalize its durable ledger
evidence:

```bash
trading-paper-qualify --database var/trading.sqlite3 --finalize 2026-07-13
trading-transparent-qualify --database var/trading.sqlite3 --finalize 2026-07-13
```

Run the same command without `--finalize` to inspect the accumulated gate. The
reports become `qualified` only after ten trailing passing sessions. Automatic
session-start markers ensure an attempted but unfinalized or incompletely closed
session breaks the streak. The evaluator checks paper mode, regular close
evidence, market activity, unique order IDs, terminal orders, reconciled fills,
flat closing positions, complete decision/acknowledgement audit links, and zero
runtime-halt incidents. It emits one JSON report and uses exit code `0` only when
the ten-session gate is qualified; `2` means more evidence or remediation is
required.

The transparent report additionally requires a frozen validation-approved v2
shadow bundle, resolved candidate outcomes, zero candidate errors or restarts,
and bounded shadow latency. The v1 engine remains the only routing authority.

Production configuration defaults to regular-hours operation, stops entries at
15:50 ET, flattens at 15:58 ET, and rejects live mode unless the configuration
contains `"live_risk_acknowledgement": "I_ACCEPT_LIVE_CAPITAL_RISK"`.

External integration tests are disabled by default. Run them only against an
intended Massive account and IBKR paper session:

```bash
pytest --run-external -m external
```

## Testing

The test suite is concentrated in `tests/unit/l1_state_machine/` and covers:

1. CLI behavior
2. panel construction and replay determinism
3. calibration, training, and artifact persistence
4. validation harness behavior
5. monitoring and live runner flows
6. router adapters and recovery behavior

Run the tests with:

```powershell
pytest
```

Run the dedicated IBKR functionality slice with:

```powershell
pytest tests/unit/l1_state_machine/test_ibkr_functionality.py -q
```

Run the dedicated workflow and market-data preflight slice with:

```powershell
pytest tests/unit/l1_state_machine/test_workflow_preflight.py -q
```

Run the real source-backed Massive smoke slice with:

```powershell
pytest tests/integration/l1_state_machine/test_massive_source_smoke.py -q
```

Run the bounded real source-backed workflow smoke slice with:

```powershell
pytest tests/integration/l1_state_machine/test_massive_workflow_smoke.py -q
```

Run the bounded broker-backed routed-live smoke slice with:

```powershell
pytest tests/integration/l1_state_machine/test_ibkr_routed_live_smoke.py -q
```

## Important docs

Start with these documents if you want the design rationale or operating context:

1. `docs/l1_microstructure_state_machine.md`
2. `docs/l1_microstructure_thesis_edge_and_state_vector.md`
3. `docs/l1_microstructure_package_plan.md`
4. `docs/l1_microstructure_operator_guide.md`

## Current scope and limitations

This package is a clean successor implementation, not a claim of fully solved microstructure execution. The design deliberately accepts L1-only limitations: hidden liquidity, direct-feed advantages, and explicit cross-venue queue inference are treated as uncertainty rather than directly observed truth.

Broker routing is also kept at the edge of the system. The routed-live shell exists, but real deployment still depends on an external adapter and operator safeguards.
