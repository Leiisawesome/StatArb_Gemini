"""Quantile-based state surface calibration."""

from __future__ import annotations

import pandas as pd

from .interfaces import CalibrationDataset, StateCalibrationArtifact, StateRegimeSurface


class QuantileStateCalibrator:
    def __init__(self, minimum_regime_surface_rows: int = 5):
        self.minimum_regime_surface_rows = minimum_regime_surface_rows

    def fit(self, dataset: CalibrationDataset) -> StateCalibrationArtifact:
        frame = dataset.features
        self._require_columns(frame, ("spread_norm", "realized_volatility", "flicker_intensity", "quote_pressure"))

        spread_quantiles = self._tertiles(frame["spread_norm"])
        volatility_quantiles = self._tertiles(frame["realized_volatility"])
        flicker_baseline = float(frame["flicker_intensity"].median())
        quote_pressure_scale = max(float(frame["quote_pressure"].abs().quantile(0.75)), 1e-6)
        regime_surfaces: dict[str, StateRegimeSurface] = {}
        regime_surface_rows: dict[str, int] = {}
        if "dominant_regime" in frame.columns:
            for regime_value, regime_frame in frame.groupby("dominant_regime"):
                regime_sample_count = int(len(regime_frame))
                regime_surface_rows[str(regime_value)] = regime_sample_count
                if regime_sample_count < self.minimum_regime_surface_rows:
                    continue
                regime_surfaces[str(regime_value)] = StateRegimeSurface(
                    spread_quantiles=self._tertiles(regime_frame["spread_norm"]),
                    volatility_quantiles=self._tertiles(regime_frame["realized_volatility"]),
                    flicker_baseline=float(regime_frame["flicker_intensity"].median()),
                    quote_pressure_scale=max(float(regime_frame["quote_pressure"].abs().quantile(0.75)), 1e-6),
                    sample_count=regime_sample_count,
                )

        metadata = {
            "row_count": int(len(frame)),
            "columns": tuple(frame.columns),
            "method": "empirical_tertiles",
            "minimum_regime_surface_rows": self.minimum_regime_surface_rows,
            "regime_surface_row_counts": regime_surface_rows,
            "regime_surface_count": len(regime_surfaces),
            **dataset.metadata,
        }
        return StateCalibrationArtifact(
            symbol=dataset.symbol,
            spread_quantiles=spread_quantiles,
            volatility_quantiles=volatility_quantiles,
            flicker_baseline=flicker_baseline,
            quote_pressure_scale=quote_pressure_scale,
            regime_surfaces=regime_surfaces,
            metadata=metadata,
        )

    @staticmethod
    def _tertiles(series: pd.Series) -> tuple[float, float]:
        return float(series.quantile(1.0 / 3.0)), float(series.quantile(2.0 / 3.0))

    @staticmethod
    def _require_columns(frame: pd.DataFrame, columns: tuple[str, ...]) -> None:
        missing = [column for column in columns if column not in frame.columns]
        if missing:
            raise ValueError(f"calibration dataset is missing required columns: {missing}")

