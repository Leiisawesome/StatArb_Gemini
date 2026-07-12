# L1 Microstructure State Machine

`l1_microstructure` is the standalone successor architecture for intraday alpha research and execution on Polygon L1 equity quote and trade data.

The package is intentionally isolated from any legacy engine. The goal is to keep the microstructure model, its artifact lifecycle, and its paper or routed-live execution paths self-contained so they can be evaluated without inheriting unrelated infrastructure assumptions.

## Core idea

The package models short-horizon intraday opportunity as a sequence of state transitions rather than as a collection of independent feature thresholds.

Each normalized market event updates an observable state:

`X_t = (S_t, Q_t, I_t, F_t, V_t)`

where the framework tracks spread, quote pressure, signed trade imbalance, flicker intensity, and realized microprice volatility.

That state is then used to:

1. infer a slower latent regime
2. detect whether a transition edge has occurred
3. register forward outcomes for delayed drift measurement
4. estimate edge-conditioned posterior drift
5. generate a trade intent only when the edge signal is sufficiently supported
6. apply risk and portfolio constraints before execution

## Runtime flow

The runtime loop implemented by `L1MicrostructureStateMachine` in `l1_microstructure/pipeline.py` is:

1. normalize and ingest a market event
2. update the observable state through the feature engine
3. update the latent regime posterior
4. resolve any pending forward outcomes whose horizons have matured
5. process pending or external execution reports
6. test whether the new state is a transition from the prior state
7. if a transition occurs, update transition statistics and diagnostics
8. convert the edge into a posterior trade decision
9. pass the decision through risk and portfolio sizing
10. either enqueue simulator execution or emit external execution requests

This same core is used by replay, simulator-backed paper runs, source-backed paper runs, and routed-live runs.

## Package layout

The package now contains both stable interfaces and concrete implementations.

`l1_microstructure/config.py`
Defines the control surface for features, regimes, transitions, decisions, execution, risk, and portfolio allocation.

`l1_microstructure/events.py`
Defines the canonical normalized quote and trade contracts used throughout the package.

`l1_microstructure/features.py`
Projects the incoming event stream into the observable microstructure state.

`l1_microstructure/regime.py`
Infers slower contextual regimes that modulate confidence, holding-time expectations, and transition interpretation.

`l1_microstructure/transitions.py`
Implements the regularized semi-Markov transition kernel, Mahalanobis transition detection, Dirichlet smoothing, and edge diagnostics.

`l1_microstructure/decision.py`
Turns edge-conditioned drift samples into posterior trade intents using cost-aware and confidence-aware thresholds.

`l1_microstructure/execution.py`
Implements latency-shifted execution requests, alignment checks, fill modeling, and adverse-selection penalties.

`l1_microstructure/risk.py`
Applies volatility-scaled sizing, exposure checks, beta-aware controls, and intraday kill-switch logic.

`l1_microstructure/portfolio.py`
Provides portfolio-aware allocation with covariance shrinkage and sector caps when cross-symbol context exists.

`l1_microstructure/pipeline.py`
Hosts `L1MicrostructureStateMachine`, the shared orchestration core.

`l1_microstructure/ingest/`
Contains market-data interfaces plus concrete Polygon REST and WebSocket data sources, payload normalization, and session filters.

`l1_microstructure/replay/`
Contains deterministic replay interfaces and the concrete replay engine.

`l1_microstructure/labeling/`
Contains forward-drift labeling contracts and implementations used for transition outcomes.

`l1_microstructure/datasets/`
Builds state and transition panels used by calibration, training, and validation.

`l1_microstructure/calibration/`
Contains calibration interfaces plus concrete state, regime, and execution calibrators.

`l1_microstructure/training/`
Contains training interfaces plus the empirical transition trainer.

`l1_microstructure/artifacts/`
Contains artifact metadata contracts, the local artifact store, runtime bundle selection, and bundle loading.

`l1_microstructure/validation/`
Contains validation interfaces plus the rolling out-of-sample validation harness.

`l1_microstructure/monitoring/`
Contains monitoring interfaces plus in-memory and JSONL sinks and the runtime monitor.

`l1_microstructure/live/`
Contains the simulator-backed paper runner, source-backed paper runner, routed-live runner, and IBKR router boundary.

`l1_microstructure/workflow.py`
Defines the artifact-producing research workflow that fits artifacts, validates, replays, and persists a run manifest.

`l1_microstructure/cli.py`
Exposes the operator-facing command surface used by the README and operator guide.

## Artifact lifecycle

The framework is now explicitly artifact-driven.

`ArtifactDrivenResearchWorkflow` currently performs these steps:

1. build full state and transition panels
2. fit state calibration, regime calibration, and execution calibration artifacts
3. train the transition model for the configured runtime horizon
4. run rolling out-of-sample validation with retraining
5. replay the resulting runtime bundle through the paper runner
6. save validation output, monitored replay output, and a run manifest

The runtime bundle selected later by `paper-historical`, `paper-live`, or `live-routed` includes the calibrated and trained artifacts needed to reproduce the trading path consistently.

## Operational boundary

The current operator-facing CLI is source-backed rather than file-backed.

That means:

1. `workflow` and `paper-historical` resolve historical data through the configured historical source using `--symbol` and `--trade-date`
2. `paper-live` and `live-routed` use the live subscription source
3. `ibkr-live-smoke` and `ibkr-live-order-smoke` exercise the Interactive Brokers routing boundary

The earlier payload-file oriented documentation is no longer the current CLI contract.

The current routed-live CLI also does not expose the deterministic test routers. Those behaviors exist in tests and lower-level APIs, but the CLI path routes through the IBKR router boundary.

## Migration boundary

The repository now retains only the successor-package path.

Immediate implications:

1. no legacy engine changes are required to evaluate the model
2. all new contracts and implementations live inside `l1_microstructure`
3. broker integration remains an outer-shell boundary instead of a core pipeline dependency

Recommended migration sequence:

1. build artifacts with `workflow`
2. inspect saved manifests with `list-runs`
3. replay selected bundles with `paper-historical` and `paper-live`
4. verify broker health with `ibkr-live-smoke`
5. use paper-account `live-routed` or `ibkr-live-order-smoke` only after the artifact path and broker boundary are stable
6. use `trading-daemon` as the canonical supervised live-capital runtime

## Current limitations

The package is a clean implementation of the thesis, not a claim of complete market microstructure observability.

The main limits remain unchanged:

1. hidden liquidity is modeled as uncertainty rather than directly observed truth
2. direct-feed timing advantages are not fully represented in an L1-only setup
3. explicit cross-venue queue inference remains outside the current data scope
4. real broker routing still depends on external credentials, connectivity, and operator safeguards

## See also

For document roles and reading order, use the documentation map in `README.md`.
