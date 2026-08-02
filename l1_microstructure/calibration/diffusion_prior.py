"""Switching-diffusion prior calibration from transition panels."""

from __future__ import annotations

from math import sqrt

import pandas as pd

from l1_microstructure.regime import MicrostructureRegime

from .interfaces import SwitchingDiffusionPrior


class SwitchingDiffusionPriorCalibrator:
    """
    Fit regime-switching diffusion rates from transition-panel realized drifts.

    For each regime R, with horizon H and sample drifts d_i:

        μ_R = mean(d) / H_seconds
        σ_R = std(d) / sqrt(H_seconds)

    corresponding to dm = μ dt + σ dW in bps units.
    """

    def __init__(
        self,
        *,
        reference_horizon_ns: int,
        prior_strength: float = 2.0,
        min_volatility_bps_per_sqrt_sec: float = 0.25,
        min_regime_samples: int = 8,
    ):
        self.reference_horizon_ns = max(int(reference_horizon_ns), 1)
        self.prior_strength = max(float(prior_strength), 1e-6)
        self.min_volatility = max(float(min_volatility_bps_per_sqrt_sec), 1e-9)
        self.min_regime_samples = max(int(min_regime_samples), 2)

    def fit(self, transition_frame: pd.DataFrame) -> SwitchingDiffusionPrior:
        self._require_columns(transition_frame, ("regime", "realized_drift_bps"))
        frame = transition_frame
        if "horizon_ns" in frame.columns and not frame.empty:
            # Prefer rows at the runtime reference horizon when multi-horizon panels exist.
            matched = frame[frame["horizon_ns"] == self.reference_horizon_ns]
            if not matched.empty:
                frame = matched
            else:
                # Nearest horizon bucket.
                nearest = int(
                    min(
                        frame["horizon_ns"].unique(),
                        key=lambda value: abs(int(value) - self.reference_horizon_ns),
                    )
                )
                frame = frame[frame["horizon_ns"] == nearest]

        rates: dict[str, float] = {}
        vols: dict[str, float] = {}
        counts: dict[str, int] = {}
        all_drifts = [float(value) for value in frame["realized_drift_bps"].tolist()]
        global_rate, global_vol = self._moments(all_drifts, self._seconds_for_frame(frame))

        for regime in MicrostructureRegime:
            regime_frame = frame[frame["regime"] == regime.value]
            drifts = [float(value) for value in regime_frame["realized_drift_bps"].tolist()]
            counts[regime.value] = len(drifts)
            if len(drifts) < self.min_regime_samples:
                rates[regime.value] = global_rate
                vols[regime.value] = max(global_vol, self.min_volatility)
                continue
            rate, vol = self._moments(drifts, self._seconds_for_frame(regime_frame))
            rates[regime.value] = rate
            vols[regime.value] = max(vol, self.min_volatility)

        return SwitchingDiffusionPrior(
            reference_horizon_ns=self.reference_horizon_ns,
            drift_rate_bps_per_sec=rates,
            volatility_bps_per_sqrt_sec=vols,
            sample_count=counts,
            global_drift_rate_bps_per_sec=global_rate,
            global_volatility_bps_per_sqrt_sec=max(global_vol, self.min_volatility),
            prior_strength=self.prior_strength,
            metadata={
                "method": "switching_diffusion_moments",
                "row_count": int(len(frame)),
                "min_regime_samples": self.min_regime_samples,
            },
        )

    def _seconds_for_frame(self, frame: pd.DataFrame) -> float:
        if "horizon_ns" in frame.columns and not frame.empty:
            median_ns = float(frame["horizon_ns"].median())
            return max(median_ns, 1.0) / 1_000_000_000.0
        return max(self.reference_horizon_ns, 1) / 1_000_000_000.0

    def _moments(self, drifts: list[float], horizon_seconds: float) -> tuple[float, float]:
        seconds = max(float(horizon_seconds), 1e-9)
        if not drifts:
            return 0.0, self.min_volatility
        mean_drift = sum(drifts) / len(drifts)
        if len(drifts) < 2:
            return mean_drift / seconds, self.min_volatility
        variance = sum((value - mean_drift) ** 2 for value in drifts) / (len(drifts) - 1)
        std_drift = sqrt(max(variance, 0.0))
        rate = mean_drift / seconds
        vol = std_drift / sqrt(seconds)
        return float(rate), float(max(vol, self.min_volatility))

    @staticmethod
    def _require_columns(frame: pd.DataFrame, columns: tuple[str, ...]) -> None:
        missing = [column for column in columns if column not in frame.columns]
        if missing:
            raise ValueError(f"diffusion prior calibration is missing required columns: {missing}")


