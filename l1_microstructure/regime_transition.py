"""
Shared continuous-time regime transition predict step.

Used by the online RegimeInferencer and offline EM E-step so train and serve
cannot drift apart.
"""

from __future__ import annotations

from math import exp
from typing import Mapping, Sequence

from .stats.distributions import conditional_weibull_survival


def stay_probability(
    *,
    dwell_ns: int,
    dt_ns: int,
    mean_holding_ns: int,
    duration_shape: float,
    use_hsmm: bool,
    floor: float,
) -> float:
    """P(remain in regime over dt | current dwell)."""
    holding = max(int(mean_holding_ns), 1)
    if use_hsmm:
        return conditional_weibull_survival(
            max(int(dwell_ns), 0),
            max(int(dt_ns), 0),
            holding,
            float(duration_shape),
            floor=floor,
        )
    return min(max(exp(-max(int(dt_ns), 0) / holding), floor), 1.0)


def predict_regime_probabilities(
    previous: Mapping[str, float],
    *,
    regime_order: Sequence[str],
    dt_ns: int,
    holding_times_ns: Mapping[str, int] | Sequence[int],
    duration_shapes: Mapping[str, float] | Sequence[float],
    leave_weights: Mapping[str, Sequence[float]],
    dominant_regime: str | None,
    dwell_ns: int,
    use_hsmm: bool,
    floor: float,
) -> dict[str, float]:
    """
    One-step predict for a continuous-time Markov / semi-Markov regime chain.

    ``leave_weights[from_regime]`` is a length-K row of off-diagonal leave
    masses that already sum to 1 over destinations (diagonal entry ignored).
    """
    order = tuple(regime_order)
    if dt_ns <= 0:
        return {regime: max(float(previous.get(regime, floor)), floor) for regime in order}

    def _holding(regime: str, index: int) -> int:
        if isinstance(holding_times_ns, Mapping):
            return max(int(holding_times_ns.get(regime, 1)), 1)
        return max(int(holding_times_ns[index]), 1)

    def _shape(regime: str, index: int) -> float:
        if isinstance(duration_shapes, Mapping):
            return max(float(duration_shapes.get(regime, 1.0)), 1e-6)
        return max(float(duration_shapes[index]), 1e-6)

    predicted = {regime: 0.0 for regime in order}
    for row_index, from_regime in enumerate(order):
        previous_probability = max(float(previous.get(from_regime, floor)), floor)
        current_dwell = dwell_ns if from_regime == dominant_regime else 0
        stay = stay_probability(
            dwell_ns=current_dwell,
            dt_ns=dt_ns,
            mean_holding_ns=_holding(from_regime, row_index),
            duration_shape=_shape(from_regime, row_index),
            use_hsmm=use_hsmm,
            floor=floor,
        )
        predicted[from_regime] += previous_probability * stay
        leave_mass = previous_probability * max(1.0 - stay, 0.0)
        weights = leave_weights[from_regime]
        for column_index, to_regime in enumerate(order):
            predicted[to_regime] += leave_mass * float(weights[column_index])

    predicted = {regime: max(value, floor) for regime, value in predicted.items()}
    total = sum(predicted.values())
    if total <= 0.0:
        uniform = 1.0 / max(len(order), 1)
        return {regime: uniform for regime in order}
    return {regime: value / total for regime, value in predicted.items()}


def leave_weight_rows(
    priors: Mapping[str, float],
    regime_order: Sequence[str],
    *,
    floor: float,
) -> dict[str, tuple[float, ...]]:
    """Build per-origin leave distributions proportional to destination priors."""
    order = tuple(regime_order)
    result: dict[str, tuple[float, ...]] = {}
    for row_index, from_regime in enumerate(order):
        weights = [
            0.0 if column_index == row_index else max(float(priors.get(to_regime, floor)), floor)
            for column_index, to_regime in enumerate(order)
        ]
        total = sum(weights)
        if total <= 0.0:
            denominator = max(len(order) - 1, 1)
            weights = [
                0.0 if index == row_index else 1.0 / denominator
                for index in range(len(order))
            ]
        else:
            weights = [weight / total for weight in weights]
        result[from_regime] = tuple(weights)
    return result
