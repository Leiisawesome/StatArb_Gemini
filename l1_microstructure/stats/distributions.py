"""Shared probability primitives used by regime filter, EM, and transparent path."""

from __future__ import annotations

from math import exp, gamma, log, pi


def conditional_weibull_survival(
    dwell_ns: int,
    dt_ns: int,
    mean_ns: int,
    shape: float,
    *,
    floor: float = 1e-9,
) -> float:
    """
    Conditional survival P(T > dwell+dt | T > dwell) for a Weibull sojourn.

    Shape ``k = 1`` reduces to the exponential stay probability
    ``exp(-dt / mean)`` used by the memoryless CTMC filter.
    """
    if dt_ns <= 0:
        return 1.0
    safe_shape = max(float(shape), 1e-6)
    safe_mean = max(float(mean_ns), 1.0)
    # E[T] = scale * Gamma(1 + 1/k)  ⇒  scale = mean / Gamma(1 + 1/k)
    scale = max(safe_mean / gamma(1.0 + 1.0 / safe_shape), 1.0)
    start = (max(float(dwell_ns), 0.0) / scale) ** safe_shape
    end = ((max(float(dwell_ns), 0.0) + float(dt_ns)) / scale) ** safe_shape
    return float(min(max(exp(-(end - start)), floor), 1.0))


def diagonal_gaussian_log_likelihood(
    observation: tuple[float, ...],
    mean: tuple[float, ...],
    std: tuple[float, ...],
) -> float:
    """Log density of a diagonal multivariate normal (independent coordinates)."""
    if not mean or not std or len(mean) != len(observation) or len(std) != len(observation):
        return float("-inf")
    log_likelihood = 0.0
    log_two_pi = log(2.0 * pi)
    for value, mu, sigma in zip(observation, mean, std):
        safe_sigma = max(float(sigma), 1e-12)
        residual = (float(value) - float(mu)) / safe_sigma
        log_likelihood += -0.5 * (residual * residual + 2.0 * log(safe_sigma) + log_two_pi)
    return float(log_likelihood)
