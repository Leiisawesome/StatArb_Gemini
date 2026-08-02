# L1 Microstructure Thesis: Edge from State Change and the State Vector

This document summarizes the core thesis of `l1_microstructure`: how short-horizon trading edge is defined from the continuous state vector, discrete state transitions, and edge-conditioned forward drift.

For package structure and operator commands, see:

1. `docs/l1_microstructure_state_machine.md` — runtime architecture overview
2. `docs/l1_microstructure_package_plan.md` — package boundaries and contracts
3. `docs/l1_microstructure_operator_guide.md` — CLI runbook

## Core claim

The system does **not** treat edge as a static feature threshold such as “trade when imbalance is high.”

Instead:

> Short-horizon price drift is conditional on which microstructure neighborhood the book just left and which one it just entered, under the current latent regime. The continuous vector decides whether a real change happened. The discrete edge identity names what kind of change it was. Historical outcomes of that edge estimate whether that change has tended to pay.

In one sentence:

**Edge is the historically regularized, cost-adjusted conditional expectation of short-horizon microprice drift given a noise-filtered transition of the five-dimensional L1 state vector, identified by the discrete from→to cell pair under the current latent regime — not by any single feature threshold on the vector itself.**

## Two representations of the same state

Every L1 event that has a book produces an `ObservedState` with two parallel encodings:

| Layer | Object | Role |
| --- | --- | --- |
| Continuous | \(X_t = (S_t, Q_t, I_t, F_t, V_t)\) | Geometry: how much the market moved |
| Discrete | `label` = `spread\|quote\|trade\|flicker\|vol` | Topology: which cell of the state space is active |

Implemented in `l1_microstructure/features.py` as `ObservedState.vector` and `ObservedState.label`.

Why both are required:

1. Continuous \(\Delta X\) answers: was this a meaningful reconfiguration or just noise?
2. Discrete labels answer: which type of transition is this, so historical outcomes can be pooled?
3. Without the continuous vector, every tiny tick would redefine state.
4. Without discrete labels, a sparse transition kernel over continuous points is not estimable.

## The continuous state vector

The vector components are L1-observable proxies for liquidity and pressure, not generic ML features.

### \(S_t\) — normalized spread (`spread_norm`)

\[
S_t = \frac{\text{ask} - \text{bid}}{\max(\sigma^{\text{micro}}_t, \sigma_{\min})}
\]

Spread is measured relative to microprice volatility so “wide” means wide for the current noise environment, not wide in absolute cents.

**Economic content:** cost of immediacy / liquidity thickness.

### \(Q_t\) — quote pressure

Built from a short quote history (default last five updates). Bid/ask size increases and price improvements add buy evidence; the opposite adds sell evidence. Mapped to roughly \([-1, 1]\).

**Economic content:** resting interest and book-building path, not executed prints.

### \(I_t\) — trade pressure / imbalance

Signed trade volume over a short window (default about 10 seconds), normalized by gross volume:

\[
I_t = \frac{\sum v^{\text{signed}}}{\sum |v|}
\]

Aggressor side is inferred from the book when the feed does not tag it.

**Economic content:** executed flow; often the more aggressive short-horizon directional force than quote pressure.

### \(F_t\) — flicker intensity

Quote-event intensity with mean reversion to a baseline. Each quote jumps intensity upward; between quotes it decays. High \(F\) means competitive, unstable top-of-book activity.

**Economic content:** adversarial or high-frequency competition around the touch; useful for adverse-selection risk.

### \(V_t\) — realized microprice volatility

Standard deviation of log microprice returns over a longer window (default about 600 seconds).

**Economic content:** local noise scale; also feeds decision cost thresholds and risk sizing.

## Continuous to discrete projection

Each continuous coordinate is bucketed into a coarse cell:

| Continuous | Discrete buckets |
| --- | --- |
| \(S\) | tight / normal / wide |
| \(Q\), \(I\) | sell_heavy / neutral / buy_heavy |
| \(F\) | stable / competitive / chaotic |
| \(V\) | quiet / normal / stressed |

Example label:

```text
tight|buy_heavy|buy_heavy|competitive|normal
```

Cutpoints may come from rolling quantiles or from calibrated regime surfaces (`StateRegimeSurface`), so “tight under shock” can differ from “tight in calm.”

## When a move becomes a transition

Not every event is a tradeable edge. Decision logic only runs when the continuous move is large in a noise-aware metric.

With \(\delta = X_t - X_{t-1}\) and precision estimated from recent increment history:

\[
d_t = \delta^\top \hat\Sigma^{-1} \delta > \tau
\]

Default Mahalanobis threshold \(\tau = 2.75\) (`TransitionConfig.mahalanobis_threshold`). Early in a session, with few increments, Euclidean norm is used as a bootstrap.

Interpretation:

1. Habitual co-movement of coordinates is down-weighted.
2. Unusual joint moves are up-weighted.
3. Edge is associated with material reconfigurations of the microstructure field, not every tick.

Implemented in `TransitionKernel.mahalanobis_distance` / `is_transition` in `l1_microstructure/transitions.py`.

Only after that gate fires does the runtime form an edge key:

\[
e = (s_{\text{from}},\; s_{\text{to}},\; R_t)
\]

where:

1. \(s_{\text{from}}\) and \(s_{\text{to}}\) are discrete labels
2. \(R_t\) is the dominant slow regime (calm, execution flow, liquidity shock, competitive liquidity)

Holding time in the prior cell is recorded as well (semi-Markov flavor).

## Where edge comes from economically

At a transition time \(t^*\):

1. Snapshot microprice \(P_{t^*}\) as the reference price.
2. Wait a forward horizon \(H\) (runtime default 3000 ms; research also labels longer horizons such as 15s and 60s).
3. Realized drift in basis points:

\[
d_{e,H} = 10^4 \cdot \frac{P_{t^*+H} - P_{t^*}}{P_{t^*}}
\]

That sample is attached to the **edge identity**, not to a raw feature level. The predictive object is therefore:

\[
\mathbb{E}[d_H \mid e = (s_{\text{from}}, s_{\text{to}}, R)]
\]

not

\[
\mathbb{E}[d_H \mid Q_t > 0.25].
\]

### Why transitions rather than levels

A level such as “buy-heavy trade pressure” can mean many different things depending on path and climate:

1. Entering buy-heavy from sell-heavy after a shock may mark absorption or reversal.
2. Remaining buy-heavy after already being buy-heavy may be continuation or exhaustion.
3. The same pressure under liquidity shock versus calm liquidity has different fill risk and mean drift.

Conditioning on the edge encodes path and context. Conditioning only on the destination state discards “from where” and “under which regime.”

## Kernel diagnostics that turn edges into scores

For each edge the transition kernel maintains:

1. Observation count, holding times, and drift samples
2. Dirichlet-smoothed transition probability from `(from_state, regime)` to `to_state`
3. Entropy of the outgoing distribution from that cell
4. Drift signal-to-noise: \(|\mu| / \sigma\)
5. Alpha score: \(\text{SNR} / (1 + \text{entropy})\)
6. Adversarially decayed drift mean (older evidence loses weight as the market adapts)

High SNR alone is insufficient if the outgoing graph is chaotic. Prefer edges that are both directional and concentrated. Dirichlet smoothing and minimum observation counts regularize rare edges.

## Decision path from edge to trade intent

`DecisionEngine.decide` runs only on detected transitions. It does not trade the raw vector directly.

Typical gates:

1. Minimum edge observations (default 200)
2. Minimum alpha concentration score (default 0.15)
3. Observation confidence blending regime confidence, directional posterior strength, posterior tightness, and sample size
4. Bayesian posterior over historical edge drift samples versus a cost threshold

Cost threshold scales with local volatility:

\[
\text{threshold} = \text{cost}_{bps} + \text{risk\_premium} \cdot \max(10^4 V_t, 0.1)
\]

Entry requires both posterior mass beyond costs and agreement from decay-shrunk mean drift:

1. BUY when \(P(\text{drift} > \text{threshold})\) is high enough and shrunk mean drift is positive
2. SELL when \(P(\text{drift} < -\text{threshold})\) is high enough and shrunk mean drift is negative
3. Otherwise HOLD

Important sequencing fact: at decision time the current transition’s own drift is still unknown. The trade uses the empirical distribution of earlier outcomes of the same edge class. You trade the conditional expectation of that edge type, not the realized path that has just started.

## Soft regime mixture (decision readout)

Kernel **training** still hard-assigns each observed transition to the MAP regime:

\[
e^{\text{train}} = (s_{\text{from}}, s_{\text{to}}, R^{\star}),\quad R^{\star} = \arg\max_R P(R \mid \text{history}).
\]

Decision **readout** can mix across regimes using the full posterior (opt-in via `DecisionConfig.soft_regime_mixture`; default off until OOS promotion):

\[
\mathbb{E}[d_H \mid s_{\text{from}}, s_{\text{to}}, \text{history}]
=
\sum_R P(R \mid \text{history})\, \mathbb{E}[d_H \mid s_{\text{from}}, s_{\text{to}}, R].
\]

Operationally:

1. Drop regimes with mass below `soft_regime_min_weight`, renormalize survivors.
2. Gate on **effective** counts and stability metrics: \(\sum_R w_R \cdot \text{metric}_R\).
3. Form a mixture of per-regime NI-Gamma posteriors (mean, variance, directional probabilities).
4. Require agreement from the mixture shrunk drift \(\sum_R w_R \mu^{\text{shrunk}}_R\).

This keeps discrete edge tables identifiable while avoiding hard MAP flips when the regime filter is uncertain. Trade intents still log the primary (MAP) edge identity for auditability.

## Fitted regime emissions (EM)

The regime layer is a continuous-time HMM-style filter: predict with holding-time transitions, update with emissions. Hand-scored emissions remain the cold-start default. When a state panel is available, `EmpiricalRegimeCalibrator` fits diagonal-Gaussian emissions:

\[
P(x_t \mid R) = \prod_{d=1}^{D} \mathcal{N}(x_{t,d}; \mu_{R,d}, \sigma_{R,d}^{2})
\]

on continuous features \((S, Q, I, F, V)\). EM iterates:

1. **E-step:** sequential responsibilities \(\gamma_t(R)\) via the same predict–update filter used online (timestamps when present).
2. **M-step:** weighted means and stds per regime.

Runtime `RegimeInferencer` prefers fitted emissions when `RegimeCalibrationArtifact.emission_model` is present (`RegimeConfig.use_fitted_emissions`). Optional `emission_heuristic_blend` mixes hand scores back in for regularization. Priors and holding times continue to be estimated from the panel as before.

## HSMM holding times (Weibull sojourns)

The memoryless exponential filter uses stay probability \(\mathrm{e}^{-\Delta t / \mu_R}\). Real regimes often show **duration dependence**: early exits are less likely than a constant hazard implies.

`EmpiricalRegimeCalibrator` fits a **Weibull HSMM** sojourn model from MAP regime runs:

1. Segment consecutive identical `dominant_regime` stretches (session gaps excluded).
2. Mean sojourn \(\mu_R\) → `holding_time_seconds`.
3. Shape \(k_R\) from the coefficient of variation (same moment map as the transparent semi-Markov trainer). \(k=1\) recovers exponential; \(k>1\) is more persistent.

At runtime the predict step uses conditional Weibull survival given dwell in the current MAP regime:

\[
P(T > d+\Delta t \mid T > d)
=
\exp\!\Big(-\big[((d+\Delta t)/s)^k - (d/s)^k\big]\Big),
\quad s = \mu / \Gamma(1+1/k).
\]

Enabled when `RegimeDurationModel` is present and `RegimeConfig.use_hsmm_durations` is true. Recovery snapshots store `dominant_regime` and `regime_started_at_ns` so dwell is restart-safe.

## Switching-diffusion prior on post-edge drift

Edges remain the tradable atoms. The continuous complement is a low-dimensional regime-switching diffusion prior for short-horizon mid drift:

\[
\mathrm{d}m_t = \mu_R\,\mathrm{d}t + \sigma_R\,\mathrm{d}W_t
\]

Integrated over the decision horizon \(H\):

\[
d_H \;\approx\; \mathcal{N}(\mu_R H,\; \sigma_R^2 H)
\]

`SwitchingDiffusionPriorCalibrator` estimates \((\mu_R, \sigma_R)\) from transition-panel `realized_drift_bps` (per regime, at the runtime horizon). At decision time those moments become the NI-Gamma prior \((\mu_0, \kappa_0, \alpha_0, \beta_0)\) for `DecisionEngine.estimate_posterior`, so sparse edges shrink toward a regime-structural mean rather than toward zero. Soft-regime mixture uses each component’s own regime prior before mixing posteriors.

This is **not** a full LOB SPDE. It is a structural regularizer for \(\mathbb{E}[d_H \mid e]\) and multi-horizon consistency. Disable with `DecisionConfig.use_switching_diffusion_prior = False`.

## End-to-end flow

```text
L1 quote/trade
      │
      ▼
 continuous vector X = (S, Q, I, F, V)     ← current book geometry
      │
      ├── discretize → label s               ← state-space cell
      └── slow filter → regime posterior P(R)  ← market climate
      │
      ▼
 Mahalanobis(X_prev, X_now) > τ ?
      │ no  → observe only; no decision
      │ yes
      ▼
 train on e* = (s_prev → s_now | R_MAP)
 decide with soft mixture over R of same (s_prev, s_now)
      │
      ├── schedule microprice drift over horizon H
      ├── update kernel stats for e*
      └── mix historical {d | e_R} + diagnostics by P(R)
              │
              ▼
        posterior: P(d clears costs | soft edge)
              │
              ▼
        BUY / SELL / HOLD → risk → execution
```

Primary implementation points:

1. Vector and labels: `l1_microstructure/features.py`
2. Regime: `l1_microstructure/regime.py`
3. Transition detection and edge diagnostics: `l1_microstructure/transitions.py`
4. Forward drift labeling (research path): `l1_microstructure/labeling/drift.py`
5. Pending online drift resolution: `L1MicrostructureStateMachine._resolve_pending_outcomes` in `pipeline.py`
6. Trade intent: `l1_microstructure/decision.py`

## What the thesis is not saying

| Claim | Status in this design |
| --- | --- |
| Buy when imbalance is high | Too weak; ignores path, regime, costs, concentration |
| Continuous \(X\) is the signal | \(X\) detects transitions and scales cost/risk; the signal is edge-conditioned drift |
| Every label change is a transition | No; Mahalanobis gate filters noise |
| Edge is arbitrage-free | No; L1-only limits, adverse selection, adversarial decay, execution uncertainty |
| Same edge is universal across symbols | Structure is portable; distributions of \(d_e\) are per-name artifacts |

## Symbol portability note

The algorithm structure is symbol-agnostic: the same vector, transition geometry, and decision gates apply to any equity L1 stream.

Operationally, calibrations and transition models are still fitted and promoted per symbol. The code path is portable; the learned conditional drift of each edge is not assumed identical across names.

## Related configuration defaults

From `l1_microstructure/config.py` (illustrative defaults):

| Area | Defaults that matter for this thesis |
| --- | --- |
| Features | Trade window 10s; micro-vol window 600s; slow context 1800s |
| Transitions | Mahalanobis threshold 2.75; Dirichlet alpha 0.25; runtime drift horizon 3000 ms |
| Decisions | Entry probability 0.62; transaction cost 1.2 bps; min alpha score 0.15 |
| Regimes | Distinct holding-time priors for calm, execution flow, liquidity shock, competitive liquidity |
