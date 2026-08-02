"""Offline calibration contracts and implementations for state and regime fitting."""

from importlib import import_module
from typing import Any

from .interfaces import (
    CalibrationDataset,
    ExecutionCalibrationArtifact,
    ExecutionCalibrationDataset,
    ExecutionCalibrator,
    RegimeCalibrationArtifact,
    RegimeCalibrator,
    RegimeDurationModel,
    RegimeEmissionModel,
    StateCalibrationArtifact,
    StateCalibrator,
    StateRegimeSurface,
    SwitchingDiffusionPrior,
)

_LAZY_FITTERS = {
    "EmpiricalExecutionCalibrator": ".execution_calibrator",
    "EmpiricalRegimeCalibrator": ".regime_calibrator",
    "QuantileStateCalibrator": ".state_calibrator",
    "SwitchingDiffusionPriorCalibrator": ".diffusion_prior",
    "REGIME_EMISSION_FEATURES": ".regime_calibrator",
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_FITTERS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(_LAZY_FITTERS[name], __name__), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))


__all__ = [
    "CalibrationDataset",
    "EmpiricalExecutionCalibrator",
    "EmpiricalRegimeCalibrator",
    "ExecutionCalibrationArtifact",
    "ExecutionCalibrationDataset",
    "ExecutionCalibrator",
    "QuantileStateCalibrator",
    "RegimeCalibrationArtifact",
    "RegimeCalibrator",
    "RegimeDurationModel",
    "RegimeEmissionModel",
    "StateCalibrationArtifact",
    "StateCalibrator",
    "StateRegimeSurface",
    "SwitchingDiffusionPrior",
    "SwitchingDiffusionPriorCalibrator",
]
