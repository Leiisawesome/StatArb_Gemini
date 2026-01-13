"""
Skeleton utilities for strategy enriched-data consumption (Rule 7).

These helpers centralize schema-compatibility glue (column resolution, basic indicator
extraction) so strategy implementations can stay core-alpha focused.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set

import pandas as pd


@dataclass(frozen=True)
class IndicatorSeriesBundle:
    """A small container for extracted indicator series."""

    adx: pd.Series
    volume_ratio: pd.Series
    trend_strength: pd.Series


def resolve_first_present_column(data: pd.DataFrame, candidates: Iterable[str]) -> Optional[str]:
    """
    Return the first candidate column name that exists in the DataFrame, else None.
    """
    for name in candidates:
        if name in data.columns:
            return name
    return None


def resolve_expected_or_mapped_column(
    *,
    data: pd.DataFrame,
    expected_name: str,
    mapping: Dict[str, str],
) -> str:
    """
    Resolve an expected column name to an actual column in `data`, using a mapping.

    Behavior intentionally matches historical strategy helper patterns:
    - If `expected_name` exists in `data.columns`, return it.
    - Else if mapping provides an alternative and that exists, return the mapped name.
    - Else return `expected_name` (caller may choose to error later).
    """
    if expected_name in data.columns:
        return expected_name

    mapped = mapping.get(expected_name)
    if mapped and mapped in data.columns:
        return mapped

    return expected_name


def momentum_default_column_mapping() -> Dict[str, str]:
    """
    Default expected->actual column mapping for momentum-style strategies.

    This centralizes a commonly-used compatibility map between "expected" indicator names
    and the processing pipeline's typical output names.
    """
    return {
        # Moving averages
        "SMA_10": "sma_10",  # May not exist if not configured
        "SMA_20": "sma_20",
        "SMA_50": "sma_50",
        # Momentum indicators
        "RSI_14": "rsi",  # Period is config-dependent upstream; we map canonical name to column.
        "ADX_14": "adx",
        "MACD": "macd",
        "ATR_14": "atr",
        # Volume
        "volume_ratio": "volume_ratio",
    }


def extract_momentum_indicator_series(
    *,
    data: pd.DataFrame,
    adx_candidates: List[str],
    volume_ratio_candidates: List[str],
    trend_strength_candidates: Optional[List[str]] = None,
    default_adx: float = 25.0,
    default_volume_ratio: float = 1.0,
    default_trend_strength: float = 0.0,
) -> IndicatorSeriesBundle:
    """
    Skeleton-grade extraction for a minimal set of indicator Series used by momentum-style alphas.

    - Keeps index aligned via reindex(data.index)
    - Fills missing / NaN values deterministically
    """
    trend_strength_candidates = trend_strength_candidates or ["trend_strength"]

    adx_col = resolve_first_present_column(data, adx_candidates)
    vr_col = resolve_first_present_column(data, volume_ratio_candidates)
    ts_col = resolve_first_present_column(data, trend_strength_candidates)

    if adx_col is not None:
        adx = data[adx_col].reindex(data.index).ffill().fillna(default_adx)
    else:
        adx = pd.Series([default_adx] * len(data), index=data.index)

    if vr_col is not None:
        volume_ratio = data[vr_col].reindex(data.index).ffill().fillna(default_volume_ratio)
    else:
        volume_ratio = pd.Series([default_volume_ratio] * len(data), index=data.index)

    if ts_col is not None:
        trend_strength = data[ts_col].reindex(data.index).ffill().fillna(default_trend_strength)
    else:
        trend_strength = pd.Series([default_trend_strength] * len(data), index=data.index)

    return IndicatorSeriesBundle(adx=adx, volume_ratio=volume_ratio, trend_strength=trend_strength)


def validate_required_indicator_columns(
    enriched_data: Dict[str, pd.DataFrame],
    *,
    required_indicators: Dict[str, List[str]],
    optional_expected: Optional[Set[str]] = None,
    mapping_suggestions: Optional[Dict[str, str]] = None,
    cols_preview: int = 20,
    logger=None,
) -> None:
    """
    Skeleton helper: validate that each symbol's enriched DataFrame contains required indicators.

    Rule 7: strategies MUST validate required features at the boundary, but the mechanics
    (looping, error formatting, suggestion mapping) should live in skeleton utilities.
    """
    optional_expected = optional_expected or set()

    for symbol, data in enriched_data.items():
        if data.empty:
            raise ValueError(f"{symbol} has empty DataFrame")

        missing: List[str] = []
        for expected_name, possible_names in required_indicators.items():
            found = any(name in data.columns for name in possible_names)
            if not found and expected_name not in optional_expected:
                missing.append(expected_name)

        if missing:
            available_cols = list(data.columns[: max(30, cols_preview)])
            similar: Dict[str, str] = {}
            if mapping_suggestions:
                for missing_col in missing:
                    mapped = mapping_suggestions.get(missing_col)
                    if mapped:
                        similar[missing_col] = mapped

            raise ValueError(
                f"{symbol} missing required indicators: {missing}. "
                f"Expected mappings: {similar}. "
                f"Data must be enriched via ProcessingPipelineOrchestrator (Rule 3). "
                f"Available columns: {available_cols[:cols_preview]}..."
            )

        if logger is not None:
            logger.debug(
                f"  {symbol} enriched data validated: {len(required_indicators)} indicators present"
            )

