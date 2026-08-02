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

Calibration and directional hit rate score the probabilistic forecast, while
net-drift economics score the executable action. These are deliberately
separate: a conservative utility HOLD must not make a weak forecast look
well-calibrated. For a detected transition, validation passes all configured
horizon posteriors to the utility layer once and scores only its selected
horizon, matching runtime behavior. Shadow disagreement counts are exact;
serialized comparison examples and latency samples are deterministically
bounded so a full-day report remains operationally reviewable.

Promotion also has absolute actionability gates. By default, a candidate must
select at least 100 actions, act on at least 0.01% of shared opportunities,
achieve at least a 52% hit rate on those selected actions, and produce
non-negative mean net drift per selected action (net of modeled execution cost).
The full-opportunity net-drift comparison remains useful, but cannot be diluted
by HOLD observations to make an inert or loss-making candidate pass. Expected
utility weights forecast drift by transition confidence and applies a fractional
predictive-std uncertainty penalty so strong hierarchical edges remain
actionable without disabling the actionability floors. Validation reports
created before these decision-level metrics and thresholds existed are
intentionally rejected and must be regenerated from held-out data.

Selected-action net drift subtracts the execution cost used by the utility
decision for the selected horizon. The directional label threshold remains a
separate classification boundary and cannot substitute for modeled execution
cost in the economic gate.

A v2 run contains state and execution calibration, state-vector, semi-Markov regime, hierarchical transition, and utility artifacts. The validation report binds the SHA-256 payload hash of every model artifact. Published run IDs are immutable, and selection fails closed if an artifact, report, version, symbol, or run association changes.

## Research workflow

Use `TransparentArtifactDrivenWorkflow` with at least two non-overlapping rolling splits. Promotion thresholds must be declared before the run. Production-candidate evidence must span complete sessions: the CLI accepts repeated `--trade-date` values and, with at least six dates, creates two expanding splits with four and five training sessions followed by one untouched session each. All feature, vector, regime, transition, and label state resets at each session boundary. A single-date run is an intraday diagnostic, not cross-session promotion evidence.

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

```powershell
uv run l1-microstructure transparent-workflow `
  --artifact-root var/artifacts `
  --symbol AAPL `
  --trade-date 2026-07-15 `
  --trade-date 2026-07-16 `
  --trade-date 2026-07-17 `
  --trade-date 2026-07-20 `
  --trade-date 2026-07-21 `
  --trade-date 2026-07-22
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
