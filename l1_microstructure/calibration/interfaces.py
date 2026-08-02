"""Calibration protocols for symbol-specific state fitting."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

import pandas as pd


@dataclass(frozen=True, slots=True)
class StateRegimeSurface:
    spread_quantiles: tuple[float, float]
    volatility_quantiles: tuple[float, float]
    flicker_baseline: float
    quote_pressure_scale: float
    sample_count: int


@dataclass(frozen=True, slots=True)
class CalibrationDataset:
    symbol: str
    features: pd.DataFrame
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExecutionCalibrationDataset:
    symbol: str
    state_features: pd.DataFrame
    transition_features: pd.DataFrame
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StateCalibrationArtifact:
    symbol: str
    spread_quantiles: tuple[float, float]
    volatility_quantiles: tuple[float, float]
    flicker_baseline: float
    quote_pressure_scale: float
    regime_surfaces: dict[str, StateRegimeSurface] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RegimeEmissionModel:
    """
    Diagonal-Gaussian emission densities P(x | R) for continuous L1 features.

    Means and stds are aligned with ``feature_names``. Empty models are treated as
    absent so older artifacts without emissions keep the heuristic score path.
    """

    feature_names: tuple[str, ...]
    means: dict[str, tuple[float, ...]]
    stds: dict[str, tuple[float, ...]]
    effective_weight: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RegimeDurationModel:
    """
    HSMM sojourn model: Weibull duration shapes per regime.

    Mean sojourn times live on ``RegimeCalibrationArtifact.holding_time_seconds``.
    Shape ``k = 1`` recovers the memoryless exponential (CTMC) special case.
    Shape ``k > 1`` makes early exits less likely (more persistent regimes).
    """

    family: str = "weibull"
    shapes: dict[str, float] = field(default_factory=dict)
    run_count: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SwitchingDiffusionPrior:
    """
    Low-dimensional regime-switching diffusion prior for short-horizon mid drift.

    Structural model (per regime R):

        dm_t = μ_R dt + σ_R dW_t

    Horizon-H integrated drift in bps is treated as approximately

        d_H ~ Normal(μ_R · H, σ_R² · H)

    and mapped into NI-Gamma prior hyperparameters for edge posteriors. This
    regularizes sparse edges without replacing the discrete edge identity.
    """

    reference_horizon_ns: int
    drift_rate_bps_per_sec: dict[str, float]
    volatility_bps_per_sqrt_sec: dict[str, float]
    sample_count: dict[str, int] = field(default_factory=dict)
    global_drift_rate_bps_per_sec: float = 0.0
    global_volatility_bps_per_sqrt_sec: float = 1.0
    prior_strength: float = 2.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def mean_bps(self, regime: str, horizon_ns: int | None = None) -> float:
        seconds = self._horizon_seconds(horizon_ns)
        rate = self.drift_rate_bps_per_sec.get(regime, self.global_drift_rate_bps_per_sec)
        return float(rate) * seconds

    def variance_bps2(self, regime: str, horizon_ns: int | None = None) -> float:
        seconds = self._horizon_seconds(horizon_ns)
        vol = self.volatility_bps_per_sqrt_sec.get(
            regime,
            self.global_volatility_bps_per_sqrt_sec,
        )
        return max(float(vol) ** 2 * seconds, 1e-12)

    def _horizon_seconds(self, horizon_ns: int | None) -> float:
        ns = int(horizon_ns) if horizon_ns is not None else int(self.reference_horizon_ns)
        return max(ns, 1) / 1_000_000_000.0


@dataclass(frozen=True, slots=True)
class RegimeCalibrationArtifact:
    symbol: str
    regime_priors: dict[str, float]
    holding_time_seconds: dict[str, float]
    emission_model: RegimeEmissionModel | None = None
    duration_model: RegimeDurationModel | None = None
    diffusion_prior: SwitchingDiffusionPrior | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExecutionCalibrationArtifact:
    symbol: str
    fill_probability_intercept: float
    alignment_weight: float
    spread_penalty: float
    slippage_intercept_bps: float
    spread_slippage_weight: float
    adverse_selection_weight: float
    regime_fill_multipliers: dict[str, float]
    regime_slippage_multipliers: dict[str, float]
    metadata: dict[str, Any] = field(default_factory=dict)


class StateCalibrator(Protocol):
    def fit(self, dataset: CalibrationDataset) -> StateCalibrationArtifact:
        """Fit observable-state quantization parameters for a symbol."""


class RegimeCalibrator(Protocol):
    def fit(self, dataset: CalibrationDataset) -> RegimeCalibrationArtifact:
        """Fit slower regime priors and holding-time parameters for a symbol."""


class ExecutionCalibrator(Protocol):
    def fit(self, dataset: ExecutionCalibrationDataset) -> ExecutionCalibrationArtifact:
        """Fit execution-aware fill and slippage surfaces for a symbol."""