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
class RegimeCalibrationArtifact:
    symbol: str
    regime_priors: dict[str, float]
    holding_time_seconds: dict[str, float]
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