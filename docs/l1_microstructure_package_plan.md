# L1 Microstructure Package Plan

This document describes the current structure of the standalone `l1_microstructure` package and the boundary rules that still govern future work.

It is no longer just a scaffold plan. The package now contains both abstract contracts and concrete implementations for ingestion, replay, calibration, training, artifact persistence, monitoring, validation, paper execution, and routed-live execution.

## Guardrail

The architectural guardrail is unchanged:

No new component in this package may depend on a legacy engine.

That means:

1. no legacy adapters imported into `l1_microstructure`
2. no shared contracts pulled from an older engine
3. no replay, risk, execution, monitoring, or broker bridge code imported from outside the package boundary
4. all successor interfaces and implementations live inside `l1_microstructure`

## Current package tree

```text
l1_microstructure/
  __init__.py
  __main__.py
  cli.py
  config.py
  decision.py
  events.py
  execution.py
  features.py
  pipeline.py
  recovery.py
  retry.py
  portfolio.py
  regime.py
  risk.py
  transitions.py
  workflow.py
  artifacts/
    __init__.py
    interfaces.py
    runtime.py
    store.py
  calibration/
    __init__.py
    fitters.py
    interfaces.py
  datasets/
    __init__.py
    builders.py
    interfaces.py
  ingest/
    __init__.py
    _massive_support.py
    interfaces.py
    massive.py
  labeling/
    __init__.py
    drift.py
    interfaces.py
  live/
    __init__.py
    _ibkr_native.py
    broker_models.py
    execution_session.py
    interfaces.py
    paper.py
    recovery.py
    routed.py
    router_adapters.py
    source.py
  monitoring/
    __init__.py
    alerts.py
    interfaces.py
    runtime.py
  production/
    __init__.py
    alerts.py
    api.py
    config.py
    console.py
    daemon.py
    ledger.py
    lifecycle.py
    migrate.py
    preflight.py
    runtime.py
    secret_cli.py
    secrets.py
  replay/
    __init__.py
    engine.py
    interfaces.py
  training/
    __init__.py
    interfaces.py
    trainer.py
  validation/
    __init__.py
    harness.py
    interfaces.py
```

## What is implemented now

The package has already moved beyond the original scaffold stage.

Concrete implementations now exist for:

1. Polygon historical and live data sources
2. payload normalization and session filtering
3. deterministic replay
4. forward-drift labeling
5. state and transition dataset building
6. state, regime, and execution calibration
7. empirical transition training
8. local artifact storage and runtime bundle resolution
9. rolling out-of-sample validation
10. in-memory and JSONL runtime monitoring
11. simulator-backed paper execution
12. source-backed paper execution
13. routed-live execution through an order-router boundary
14. Interactive Brokers routing and smoke-command support
15. artifact-producing research workflow and CLI commands
16. a supervised fail-closed production daemon and authenticated control API
17. durable operational recovery, alerts, and bounded dependency retries
18. typed liveness, readiness, and redacted startup preflight
19. deterministic offline safety qualification
20. durable regular-hours paper-session qualification

The package is now at the controlled-paper release-candidate boundary described
below. Further refinement is justified by qualification evidence, not by a
standing architecture-cleanup roadmap.

## Responsibilities by subpackage

`ingest/`
Defines source-side interfaces and currently implements Polygon REST and WebSocket sources, event normalization, and session filters.

`replay/`
Defines replay contracts and implements deterministic replay for event-time reconstruction and reproducible sequencing.

`labeling/`
Defines forward-outcome labeling contracts and implements drift labeling used by transition outcomes.

`datasets/`
Defines dataset-builder contracts and implements state-panel and transition-panel construction.

`calibration/`
Defines calibrator contracts and implements empirical state, regime, and execution calibration.

`training/`
Defines transition-training contracts and implements the empirical transition trainer.

`artifacts/`
Defines artifact-store contracts and implements local storage, runtime bundle loading, run-manifest selection, and quality-gate filtering.

`validation/`
Defines validation contracts and implements the rolling out-of-sample validation harness.

`monitoring/`
Defines runtime snapshots plus typed operational alerts with severity,
categories, bounded history, and time-window deduplication. In-memory, JSONL,
routed-live, and supervised production paths share this contract. Alert history
and deduplication updates are isolated from potentially slow sink delivery;
delivery failures remain non-fatal and are exposed as bounded diagnostics.
The monitoring layer accepts an alert-store contract; supervised production
adapts that contract to the existing SQLite audit ledger so bounded history,
deduplication state, and delivery diagnostics survive daemon restarts without
redelivering historical notifications.

`production/`
Defines the supervised operator runtime, durable ledger, authenticated controls,
local alerts, secrets, and daemon lifecycle. `preflight.py` performs read-only,
redacted checks for required credentials, promoted artifacts, filesystem
readiness, broker account mode, and retry configuration before infrastructure
clients or runtime threads are created. The daemon exposes the identical gate as
`--preflight`, emitting redacted JSON with stable success/failure exit codes and
returning before all runtime infrastructure construction.
`readiness.py` defines stable typed liveness and entry-readiness reports.
Authenticated `/health`, `/ready`, and `/status` endpoints keep daemon
availability, fail-closed trading eligibility, and the detailed operator view as
separate contracts.
`qualification.py` runs deterministic offline safety drills against the real
production lifecycle and audit ledger, emitting a versioned JSON report with
stable success/failure exit codes and no external infrastructure construction.
`paper_qualification.py` evaluates append-only regular-hours session evidence
from the production ledger. Automatic start/close markers make missing sessions
visible, and a versioned report enforces ten trailing passing paper sessions
across order, fill, position, incident, and audit-completeness checks.

`recovery.py`
Defines the typed, versioned state-machine recovery schema and owns validation,
snapshot capture, and restoration. `pipeline.py` retains compatibility facade
methods without serializing subordinate engine internals itself.

`retry.py`
Defines the dependency-free retry policy, exception classification, capped
exponential backoff with optional jitter, and deterministic executor contracts.
Infrastructure integrations inject waiting, clocks, and randomness; the retry
core does not sleep or decide which operations are safe to repeat.

Production applies operation-specific policies only to market-data subscription
reconnects, broker connections and health checks, and read-only reconciliation
queries. Order submission and cancellation remain single-attempt operations;
ambiguous outcomes halt for reconciliation instead of being replayed.

`live/`
Defines paper and routed-live runner contracts and implements the simulator-backed paper runner, source-backed paper runner, routed-live runner, and IBKR router boundary.

`live/recovery.py`
Defines versioned routed-live and broker recovery envelopes. Recovery validates
the full machine/router snapshot before runner mutation, stages broker lookups
before replacing tracked orders, and exposes explicit open, missing, terminal,
and mismatched reconciliation outcomes.

## Stable contract layer

The package still relies on explicit internal interfaces, and those contracts remain important because they separate research logic from runtime wiring.

Examples of contract surfaces already used in tests and implementations include:

1. `MarketDataSource` in `ingest/interfaces.py`
2. `ReplayController` in `replay/interfaces.py`
3. `StateCalibrator` in `calibration/interfaces.py`
4. `TransitionTrainer` in `training/interfaces.py`
5. `TransitionDatasetBuilder` in `datasets/interfaces.py`
6. `ArtifactStore` in `artifacts/interfaces.py`
7. `ValidationHarness` in `validation/interfaces.py`
8. `MonitoringSink` and `AlertSink` in `monitoring/interfaces.py`
9. `PaperTradingRunner` and `OrderRouter` in `live/interfaces.py`

These interfaces are not theoretical placeholders anymore. They are the package’s internal seams for substitution, testing, and operational hardening.

The root, `ingest`, and `live` package facades resolve exports lazily. Importing
domain events, replay, research workflows, ingestion contracts, or routing
contracts therefore does not initialize Massive, IBKR, FastAPI, Textual, or
keyring integrations. Concrete infrastructure remains available through its
explicit subpackage exports.

## Current execution model

The execution stack is now split into three distinct layers:

1. `pipeline.py` contains the model and decision loop
2. `live/paper.py` and `live/source.py` run simulator-backed paper execution
3. `live/routed.py` and `live/router_adapters.py` handle external routing and broker integration boundaries

This is the intended architecture: the state machine remains independent of the concrete data source and independent of the external router implementation.

## Current artifact model

The artifact model is also now concrete rather than aspirational.

Current artifact-driven flows include:

1. fitting calibrations and transition models in `workflow.py`
2. saving artifacts through `LocalArtifactStore`
3. selecting bundles with `ArtifactBundleSelector`
4. loading bundles with `ArtifactBundleLoader`
5. filtering candidate runs through validation status and quality gates

This means runtime components no longer need to reconstruct model state from ad hoc inputs. They can resolve a bundle by symbol, trade date, or run id.

## Current CLI and operator boundary

The package now has a concrete operator-facing CLI in `cli.py`.

Current commands are:

1. `workflow`
2. `list-runs`
3. `paper-historical`
4. `paper-live`
5. `live-routed`
6. `ibkr-live-smoke`
7. `ibkr-live-order-smoke`

Two points matter for future documentation and implementation work:

1. the current CLI is source-backed rather than payload-file based
2. deterministic test routers exist in tests and lower-level APIs, but are not currently exposed as CLI router flags

## Release-candidate boundary

The current overhaul targets controlled paper-trading qualification, not an
open-ended production rewrite. Its architectural work is complete when a clean
installation passes the automated suite, daemon preflight, and deterministic
offline safety qualification. After that point, the only release gate is
empirical evidence from ten trailing regular-hours paper sessions plus the
documented external broker and workstation drills.

Do not extend this overhaul to pursue:

1. new alpha or improved backtest returns;
2. venue-specific execution or queue-position realism;
3. broader symbol-universe optimization;
4. convenience CLI surfaces that do not close a qualification gap; or
5. live-capital enablement before paper qualification passes.

Those are separate, evidence-driven projects. A failed paper session may justify
a narrowly scoped reliability fix, but it does not reopen general architecture
cleanup.

## Immediate next phase

Operate the supervised daemon in paper mode and collect the qualification
evidence described in `docs/production_operator_guide.md`. Promote a change during
this phase only when it fixes an observed safety, recovery, audit, or operational
failure. Reset the ten-session trailing gate after any failed or missing session
evaluation.

## Review checklist for future changes

Use this checklist when extending the package:

1. confirm the change stays inside `l1_microstructure`
2. confirm it uses existing contracts or introduces a new one deliberately
3. confirm replay, paper, and live paths still share the same pipeline core
4. confirm artifacts remain the primary runtime handoff where applicable
5. confirm new CLI examples match the implemented flags in `cli.py`
6. confirm tests cover the new behavior at the appropriate unit or integration level

## Approved defaults that still hold

The following defaults remain consistent with the current implementation direction:

1. quotes plus trades are the default phase-1 data scope
2. the package remains research-first, then paper, then routed-live
3. replay, research, paper, and live flows share the same pipeline core
4. artifact-backed runtime execution is preferred over ad hoc runtime fitting
5. monitoring is a required part of serious paper or routed-live operation

Some older defaults from the original plan have already evolved in implementation. Most notably, portfolio-aware sizing and routed broker abstractions already exist in the package, so those topics are no longer future-only.

## See also

For document roles and reading order, use the documentation map in `README.md`.
