"""Backward-compatible re-exports for calibration fitters.

Prefer importing from the focused modules:
  state_calibrator, regime_calibrator, diffusion_prior, execution_calibrator.
"""

from __future__ import annotations

from .diffusion_prior import SwitchingDiffusionPriorCalibrator
from .execution_calibrator import EmpiricalExecutionCalibrator
from .regime_calibrator import REGIME_EMISSION_FEATURES, EmpiricalRegimeCalibrator
from .state_calibrator import QuantileStateCalibrator

__all__ = [
    "EmpiricalExecutionCalibrator",
    "EmpiricalRegimeCalibrator",
    "QuantileStateCalibrator",
    "REGIME_EMISSION_FEATURES",
    "SwitchingDiffusionPriorCalibrator",
]
