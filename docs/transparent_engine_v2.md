# Transparent statistical engine v2

## Goal and non-goals

The v2 overhaul has one measurable goal: improve held-out calibration and sparse-edge coverage while preserving net drift, bounded memory, bounded latency, interpretability, and all existing hard risk controls. It is not a neural-network rewrite and it does not receive order-routing authority during technical validation.

The implementation is organized as nine completed engineering phases:

1. Frozen v1/v2 artifact and metric contracts.
2. Robust median/MAD state vectors with fitted shrinkage covariance, censored-target exclusion, and monotone probability calibration.
3. Bounded global → regime → source-state → exact-edge drift statistics with predictive-variance floors.
4. Restart-safe multi-horizon outcome resolution.
5. A fitted, semantically anchored semi-Markov regime model with data-fitted Weibull duration shapes.
6. An explainable expected-utility decision layer using regime-conditioned fill, slippage, fixed cost, transition, uncertainty, and risk terms.
7. Failure-isolated v1/v2 shadow execution.
8. Split-local OOS promotion and immutable, validation-bound artifacts.
9. A version-frozen paper shadow campaign and qualification command.

Empirical promotion and the ten-session campaign remain evidence gates. Implementing the engine does not make a candidate qualified.

## Leakage and artifact guarantees

Every rolling split rebuilds the feature engine, vector runtime, regime runtime, and outcome tracker. No pre-window state enters a training or held-out window. Training transition rows are retained only when `end_timestamp_ns` is present and no later than the training boundary. Unresolved vector targets are censored rather than mislabeled as negative.

V2 state quantization uses one fitted global surface. It does not feed an inferred regime back into feature scaling, avoiding a cyclic train/runtime dependency. OOS comparison uses the union of v1- and v2-detected transitions on the same held-out state stream. A non-triggering engine records HOLD on the shared opportunity; v1 is never evaluated only on transitions selected by v2. Directional scoring is three-way—up, down, or neutral—so low probability of an upward move is not incorrectly treated as a sell forecast.

A v2 run contains state and execution calibration, state-vector, semi-Markov regime, hierarchical transition, and utility artifacts. The validation report binds the SHA-256 payload hash of every model artifact. Published run IDs are immutable, and selection fails closed if an artifact, report, version, symbol, or run association changes.

## Research workflow

Use `TransparentArtifactDrivenWorkflow` with at least two non-overlapping rolling splits. Promotion thresholds must be declared before the run.

```python
from l1_microstructure.transparent import (
    PromotionThresholds,
    TransparentArtifactDrivenWorkflow,
)

workflow = TransparentArtifactDrivenWorkflow(
    "var/artifacts",
    promotion_thresholds=PromotionThresholds(),
)
result = workflow.run(symbol="AAPL", events=events, splits=splits)
print(result.validation_report.to_dict())
```

Failed runs remain available for audit but `TransparentArtifactSelector(...).resolve(...)` will not load them with its default `passing_only=True` policy.

## Controlled paper shadow campaign

Keep the approved v1 engine as the routing engine. Add the validation-approved v2 run for every configured symbol:

```json
{
  "symbols": ["AAPL"],
  "promoted_run_ids": {"AAPL": "approved-v1-run"},
  "transparent_shadow_run_ids": {"AAPL": "approved-v2-run"}
}
```

Startup preflight validates both bundles. The daemon routes only v1 decisions and runs v2 in a failure-isolated sidecar. At session close it records the frozen artifact/config fingerprint, candidate errors, activity, action disagreement, and bounded-window p95 latency.

After each closed regular-hours paper session, finalize and inspect the v2 campaign:

```powershell
uv run trading-transparent-qualify --database var/trading.sqlite3 --finalize 2026-07-14
uv run trading-transparent-qualify --database var/trading.sqlite3
```

Qualification requires ten consecutive passing sessions with the same v1 and v2 run IDs, payload hashes, framework configuration, production risk/session configuration, and standard paper-safety evidence. Any candidate exception, missing or unresolved outcome evidence, mid-session restart, failed technical validation, latency breach, or fingerprint change resets the trailing streak.

The v2 engine remains shadow-only after this gate in the current codebase. Giving it routing authority is a separate, explicit safety change and should occur only after reviewing the completed campaign evidence.
