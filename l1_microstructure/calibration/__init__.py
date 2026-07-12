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
    StateCalibrationArtifact,
    StateCalibrator,
    StateRegimeSurface,
)

_LAZY_FITTERS = {
    "EmpiricalExecutionCalibrator",
    "EmpiricalRegimeCalibrator",
    "QuantileStateCalibrator",
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_FITTERS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(".fitters", __name__), name)
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
    "StateCalibrationArtifact",
    "StateCalibrator",
    "StateRegimeSurface",
]
