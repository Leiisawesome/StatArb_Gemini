"""Portfolio allocation utilities for cross-sectional microstructure signals."""

from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from .config import PortfolioConfig


class PortfolioAllocator:
    def __init__(self, config: PortfolioConfig | None = None):
        self.config = config or PortfolioConfig()

    def allocate(
        self,
        expected_returns: dict[str, float],
        covariance: pd.DataFrame,
        sector_map: dict[str, str] | None = None,
    ) -> dict[str, float]:
        if not expected_returns:
            return {}
        sector_map = sector_map or {}
        symbols = list(expected_returns)
        covariance = covariance.loc[symbols, symbols].astype(float)
        sample = covariance.to_numpy()
        diagonal = np.diag(np.diag(sample))
        shrunk = (1.0 - self.config.covariance_shrinkage) * sample + self.config.covariance_shrinkage * diagonal
        shrunk += np.eye(len(symbols)) * self.config.ridge
        mu = np.array([expected_returns[symbol] for symbol in symbols], dtype=float)
        raw_weights = np.linalg.pinv(shrunk) @ mu
        gross = np.sum(np.abs(raw_weights))
        if gross <= 0:
            return {symbol: 0.0 for symbol in symbols}
        normalized = raw_weights / gross

        clipped = {symbol: float(np.clip(weight, -self.config.max_weight, self.config.max_weight)) for symbol, weight in zip(symbols, normalized)}
        return self._apply_sector_caps(clipped, sector_map)

    def _apply_sector_caps(self, weights: dict[str, float], sector_map: dict[str, str]) -> dict[str, float]:
        sector_totals: dict[str, float] = defaultdict(float)
        adjusted = dict(weights)
        for symbol, weight in adjusted.items():
            sector = sector_map.get(symbol)
            if sector is None:
                continue
            proposed = sector_totals[sector] + abs(weight)
            if proposed > self.config.sector_cap and abs(weight) > 0:
                scale = max(self.config.sector_cap - sector_totals[sector], 0.0) / abs(weight)
                adjusted[symbol] = float(weight * scale)
            sector_totals[sector] += abs(adjusted[symbol])
        return adjusted