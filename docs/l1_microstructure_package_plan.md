# L1 Microstructure Package Plan

This document defines the successor package tree for the standalone L1 microstructure framework. It is intentionally independent of legacy core_engine. The goal is to give the new package enough internal structure to support both research workflows and paper/live execution without importing or adapting legacy components.

## Guardrail

No new component in this plan may depend on core_engine.

That means:

1. No legacy adapters.
2. No shared data contracts imported from core_engine.
3. No execution, regime, risk, replay, or monitoring bridge code from core_engine.
4. All successor interfaces must be defined inside l1_microstructure.

## Package Tree

```text
l1_microstructure/
  __init__.py
  config.py
  events.py
  features.py
  regime.py
  transitions.py
  decision.py
  execution.py
  risk.py
  portfolio.py
  pipeline.py
  ingest/
    __init__.py
    interfaces.py
  replay/
    __init__.py
    interfaces.py
  calibration/
    __init__.py
    interfaces.py
  training/
    __init__.py
    interfaces.py
  labeling/
    __init__.py
    interfaces.py
  datasets/
    __init__.py
    interfaces.py
  artifacts/
    __init__.py
    interfaces.py
  validation/
    __init__.py
    interfaces.py
  monitoring/
    __init__.py
    interfaces.py
  live/
    __init__.py
    interfaces.py
```

## Responsibilities

`ingest/`
Defines source-side contracts for historical and live Polygon ingestion, payload normalization, and session filtering.

`replay/`
Defines deterministic replay control, checkpointing, and event-time cursor semantics.

`calibration/`
Defines offline state and regime calibration interfaces. This is where symbol-specific quantizers and prior parameters should be fitted.

`training/`
Defines transition-kernel training interfaces for edge probabilities, holding times, and drift posteriors.

`labeling/`
Defines forward-outcome labeling interfaces for drift horizons and censoring.

`datasets/`
Defines builders for state panels and transition panels used in research and validation.

`artifacts/`
Defines storage contracts for all calibrated and trained artifacts.

`validation/`
Defines the harness for OOS testing, regime splits, stability checks, and decay monitoring.

`monitoring/`
Defines how runtime diagnostics are emitted without coupling monitoring to the trading loop.

`live/`
Defines the standalone paper/live runner shell that should eventually drive the successor package end to end.

## Implementation Order

If the goal is research-first, the next concrete implementations should be:

1. `ingest` historical Polygon adapters.
2. `replay` deterministic event runner.
3. `labeling` forward drift resolver.
4. `datasets` transition panel builder.
5. `calibration` offline quantile and prior fitting.
6. `training` transition-kernel trainer.
7. `validation` robustness harness.

If the goal is paper/live-first, the next concrete implementations should be:

1. `ingest` live Polygon stream adapter.
2. `monitoring` runtime sink.
3. `live` paper runner.
4. `artifacts` model loader.
5. `calibration` and `training` artifact consumers.
6. `execution` calibration extensions.

## Pre-Implementation Review Todo List

Use this checklist before building deeper implementations behind the successor-package interfaces.

### Architecture Decisions

- [ ] Confirm the hard boundary that all new functionality remains inside `l1_microstructure` with no dependency on `core_engine`.
- [ ] Confirm that `events.py` is the only canonical L1 event contract for quotes, trades, timestamps, and ordering semantics.
- [ ] Confirm that replay, research, paper, and live paths will share the same pipeline core in `pipeline.py` rather than separate logic forks.
- [ ] Confirm that calibration and training artifacts are mandatory runtime inputs once those components exist, rather than optional sidecars.
- [ ] Confirm whether the first production target is research replay only, paper trading only, or both in parallel.

### Data and Market-Structure Assumptions

- [ ] Approve the exact Polygon data scope for phase 1: quotes only, trades only, or quotes plus trades together.
- [ ] Approve the session scope for phase 1: RTH only or RTH plus explicit premarket and after-hours handling.
- [ ] Approve event ordering policy when quote and trade timestamps collide.
- [ ] Approve whether SIP corrections, late prints, and trade-condition filtering are handled immediately in ingestion phase 1 or deferred to a later pass.
- [ ] Approve which structural exclusions are phase-1 requirements: auctions, halts, earnings windows, macro-news windows, or none initially.

### Research Methodology Decisions

- [ ] Approve the first drift horizons to support in labeling and training.
- [ ] Approve the minimum sample thresholds for edge activation, posterior estimation, and validation inclusion.
- [ ] Approve whether state quantization remains symbol-specific only or symbol-plus-regime specific.
- [ ] Approve whether regime inference is purely online in phase 1 or whether offline-fitted priors are required before any serious replay study.
- [ ] Approve the first validation standard: rolling OOS only, rolling plus regime-stratified, or full bootstrap plus decay diagnostics.

### Execution and Risk Decisions

- [ ] Approve the latency model for early replay studies.
- [ ] Approve the initial fill model complexity: touch-fill proxy, alignment-gated fill probability, or queue-penalized fill surface.
- [ ] Approve the adverse-selection penalty model for phase 1.
- [ ] Approve the initial risk posture: single-symbol sizing only or portfolio-aware sizing from the start.
- [ ] Approve whether paper trading in phase 1 is simulator-only or should include broker-routing abstractions inside `l1_microstructure/live`.

### Artifact and Operations Decisions

- [ ] Approve the artifact versioning policy for calibrations, kernels, and validation reports.
- [ ] Approve whether artifacts should be human-readable on disk, binary-serialized, or both.
- [ ] Approve the minimum runtime monitoring set for the first paper runner.
- [ ] Approve the first CLI or batch workflows that must exist before implementation is considered usable.
- [ ] Approve the test standard for each component: unit only, unit plus integration, or unit plus replay-based golden tests.

### Sequencing Decisions

- [ ] Confirm that the first concrete implementation wave is `ingest` + `replay` + `labeling` + `datasets`.
- [ ] Confirm whether `calibration` should start immediately after dataset generation or wait until a minimal replay study is complete.
- [ ] Confirm whether `validation` should be implemented before the paper runner or after the first artifact-training cycle.
- [ ] Confirm whether `monitoring` is required before any paper-runner work begins.
- [ ] Approve the cutoff criterion for moving from scaffold to production-grade implementation in each subpackage.

## Approved Defaults

These are the current phase-1 default policies for the successor package. They are intentionally conservative and research-first. If any item is later overridden, the override should be recorded explicitly rather than silently changing implementation behavior.

### Architecture Decisions

- Hard boundary inside `l1_microstructure`: Approved default: All new functionality remains inside `l1_microstructure` with no dependency on `core_engine`.
- `events.py` as the sole canonical L1 contract: Approved default: `events.py` remains the only canonical contract for quotes, trades, timestamps, and deterministic ordering semantics.
- Shared pipeline core for replay, research, paper, and live: Approved default: Replay, research, paper, and live paths share the same pipeline core in `pipeline.py`.
- Calibration and training artifacts as mandatory runtime inputs once available: Approved default: Calibrations and trained artifacts become mandatory runtime inputs as soon as those components exist.
- First production target: Approved default: Research replay first, then paper trading.

### Data and Market-Structure Assumptions

- Phase-1 Polygon data scope: Approved default: Quotes plus trades together.
- Phase-1 session scope: Approved default: RTH only.
- Ordering policy for timestamp collisions: Approved default: Use stable total ordering by timestamp, then vendor sequence when present, then quotes before trades only as a final deterministic fallback.
- SIP corrections, late prints, and trade-condition filtering: Approved default: Handle basic trade-condition filtering in phase 1 and defer richer correction handling to phase 2.
- Structural exclusions in phase 1: Approved default: Exclude open auction, close auction, halts, and known scheduled macro-news windows; defer earnings-window filtering unless the initial symbol universe is highly concentrated.

### Research Methodology Decisions

- First drift horizons: Approved default: Support multiple short horizons immediately, centered on sub-5-second and sub-60-second windows.
- Minimum sample thresholds: Approved default: Keep edge activation conservative, with research labels allowed at lower counts and trading activation requiring materially higher counts.
- State quantization scope: Approved default: Use symbol-specific calibration in phase 1, with symbol-plus-regime calibration added after sample depth is demonstrated.
- Regime inference in phase 1: Approved default: Allow online inference initially, but do not treat replay conclusions as serious until offline-fitted priors exist.
- First validation standard: Approved default: Use rolling OOS plus regime-stratified evaluation first; add bootstrap and decay diagnostics after the first trained artifact cycle.

### Execution and Risk Decisions

- Early replay latency model: Approved default: Use configurable fixed latency buckets first.
- Initial fill model complexity: Approved default: Use an alignment-gated fill probability model, not naive touch-fill and not a full queue surface yet.
- Adverse-selection penalty model: Approved default: Use a simple calibrated penalty surface keyed by spread and volatility regime.
- Initial risk posture: Approved default: Start with single-symbol sizing and add portfolio-aware sizing after dataset and calibration infrastructure stabilize.
- Paper-trading phase-1 scope: Approved default: Simulator-only inside `l1_microstructure/live`.

### Artifact and Operations Decisions

- Artifact versioning policy: Approved default: Version every calibration, kernel, and validation report with immutable IDs and metadata hashes.
- Artifact storage format: Approved default: Store both human-readable metadata and machine-efficient serialized payloads.
- Minimum monitoring set for first paper runner: Approved default: Capture state label, dominant regime, edge activation count, cancel rate, fill rate, realized-versus-expected drift, and kill-switch status.
- First CLI or batch workflows: Approved default: Provide historical ingest/replay, labeling, dataset build, calibration, training, validation, and paper-runner launch workflows.
- Test standard per component: Approved default: Require unit plus targeted integration tests, with replay-based golden tests for replay, labeling, and artifact-driven flows.

### Sequencing Decisions

- First implementation wave: Approved default: `ingest` + `replay` + `labeling` + `datasets`.
- Start `calibration`: Approved default: Begin after the first minimal replay study proves dataset integrity.
- Start `validation`: Approved default: Begin after the first artifact-training cycle and before serious paper-runner expansion.
- Is `monitoring` required before paper runner: Approved default: Yes, at least a minimal runtime diagnostics layer is required.
- Cutoff criterion for production-grade status: Approved default: A subpackage is not production-grade until it has stable interfaces, focused tests, reproducible artifacts where relevant, and at least one end-to-end path exercising it under realistic assumptions.

## Interface Intent

## Override Log

Record any decision that overrides the approved defaults above.

Use one entry per override with this format:

```text
- Date:
  Section:
  Default overridden:
  New decision:
  Reason:
  Approved by:
```

Current overrides:

- None.

These modules currently define contracts, not production implementations. That is deliberate.

The reason is architectural discipline: the successor package should stabilize its internal boundaries before large amounts of code are written behind them. In a partially observed microstructure system, unclear contracts become hidden assumptions, and hidden assumptions are where curve-fit infrastructure starts.