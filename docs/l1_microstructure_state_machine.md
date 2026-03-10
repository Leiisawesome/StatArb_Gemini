# L1 Microstructure State Machine

This package is the successor architecture for intraday alpha research on Polygon.io Advanced Stocks L1 data. It is intentionally isolated from the legacy core_engine so the new framework can be evaluated, replayed, and productionized without inheriting the monolith's assumptions.

## Package Layout

`l1_microstructure/config.py`
Defines the research and production control surface: feature windows, regime priors, transition regularization, execution frictions, risk limits, and portfolio shrinkage.

`l1_microstructure/events.py`
Defines normalized quote and trade events plus book snapshots. L1 is treated as a projection of latent depth, not a direct observation of queue priority.

`l1_microstructure/features.py`
Projects each event stream into the observable state

`X_t = (S_t, Q_t, I_t, F_t, V_t)`

using volatility-normalized spread, Bayesian quote-pressure proxy, signed trade imbalance, stochastic flicker intensity, and realized microprice volatility.

`l1_microstructure/regime.py`
Infers slower contextual regimes from fast states using separated time scales. Regimes modulate expected holding times and posterior confidence rather than hand-coded trade triggers.

`l1_microstructure/transitions.py`
Centers the framework on the regularized semi-Markov transition kernel. State changes are registered only when Mahalanobis distance exceeds threshold. Outgoing transition probabilities are Dirichlet-smoothed, and entropy plus edge-conditioned drift signal-to-noise form the alpha diagnostic.

`l1_microstructure/decision.py`
Converts edge-conditioned drift samples into posterior trade decisions with minimum-observation safeguards and transaction-cost-aware thresholds.

`l1_microstructure/execution.py`
Forward-shifts signals by latency, performs a state-alignment check, and penalizes fills for adverse selection and queue uncertainty.

`l1_microstructure/risk.py`
Imposes volatility-scaled sizing and intraday drawdown kill-switch logic.

`l1_microstructure/portfolio.py`
Provides a cross-sectional allocator with diagonal shrinkage and sector caps.

`l1_microstructure/pipeline.py`
Orchestrates replay or live event flow: feature update, regime inference, transition registration, delayed drift resolution, Bayesian entry, portfolio-aware incremental sizing, latency-shifted execution, and hazard-based exit invalidation.

`l1_microstructure/live/router_adapters.py`
Provides deterministic concrete router adapters for routed-live testing and shell validation, plus broker-backed router boundaries including an Interactive Brokers convenience adapter.

`l1_microstructure/*/interfaces.py`
Defines successor-package internal contracts for ingestion, replay, calibration, training, labeling, datasets, artifact storage, validation, monitoring, and paper/live runners. These are standalone boundaries and do not import legacy core_engine.

## Migration Boundary

The legacy core_engine remains in place and untouched for now. The new framework is standalone by design.

Immediate implication:
No core_engine behavior changes are required to evaluate the new model.

Current routed-live shell support:

1. Artifact-selected routed-live execution is available through `python -m l1_microstructure live-routed`.
2. Live runner recovery snapshots can capture and restore machine state between routed-live sessions, including broker-backed open-order context that a fresh router instance can rehydrate from the broker after restart.
3. Queue-aware execution penalties and portfolio-aware incremental sizing are implemented inside the successor package and remain isolated from the legacy broker stack.
4. Real broker routing can be introduced at the outer shell via `--router-type ibkr-live`, keeping legacy broker integration outside the core state-machine pipeline.
5. Interactive Brokers operator smoke paths now include both a health-only `ibkr-live-smoke` command and an order-lifecycle `ibkr-live-order-smoke` command that submits, polls, and cancels under paper-trading safety guards.

Recommended migration sequence:

1. Replay historical Polygon quote and trade files through `L1MicrostructureStateMachine`.
2. Compare edge diagnostics and execution-adjusted alpha to legacy strategy outputs.
3. Add a thin adapter only after the successor package proves stable out of sample.
4. Retire legacy microstructure-specific paths after parity, monitoring, and operational sign-off.

## Current Limitations

The package is mathematically aligned with the thesis, but it is still a first clean implementation rather than a full production deployment. Hidden midpoint liquidity, direct-feed timing advantages, and explicit cross-venue queue inference remain modeled as uncertainty rather than observed truth. That is deliberate under an L1-only research constraint.

The concrete successor package tree and interface roadmap are documented in `docs/l1_microstructure_package_plan.md`.