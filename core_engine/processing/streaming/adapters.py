"""
Streaming Adapters - Indicator and Feature Adapters for Streaming Mode
======================================================================

StreamingIndicatorAdapter: Wraps batch indicators; extracts last row only.
StreamingFeatureAdapter: Applies pre-trained scalers to single rows (no fit).

Design (from plan Section 3.2 & 3.3):
- StreamingIndicatorAdapter wraps EnhancedIndicatorEngine
- StreamingFeatureAdapter wraps EnhancedFeatureEngineer with transform_single()

Author: StatArb_Gemini Core Engine
Version: 1.0.0 (Paper Trading Evolution - Phase 2)
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING
import logging
import pandas as pd
import numpy as np

if TYPE_CHECKING:
    from ..indicators.engine import EnhancedTechnicalIndicators
    from ..features.engineer import EnhancedFeatureEngineer

logger = logging.getLogger(__name__)

class StreamingIndicatorAdapter:
    """
    Wraps batch indicator engine for streaming use.

    Runs batch compute on buffer, returns only the last row as a dict.
    This allows reuse of existing batch indicator code without rewrite.

    Usage:
        adapter = StreamingIndicatorAdapter(indicator_engine)
        indicators = adapter.compute_indicators(buffer_df)
        # indicators is Dict[str, float] for the most recent bar
    """

    def __init__(
        self,
        indicator_engine: 'EnhancedTechnicalIndicators',
        indicator_groups: Optional[List[str]] = None,
    ):
        """
        Initialize streaming indicator adapter.

        Args:
            indicator_engine: The batch indicator engine to wrap
            indicator_groups: Which indicator groups to compute (None = all)
        """
        self._engine = indicator_engine
        self._indicator_groups = indicator_groups

        # Cache of column names to extract
        self._indicator_columns: Optional[List[str]] = None

        # Stats
        self._stats = {
            'compute_calls': 0,
            'avg_compute_ms': 0.0,
        }

    def compute_indicators(self, buffer: pd.DataFrame) -> Dict[str, float]:
        """
        Compute indicators on buffer and return last row values.

        Args:
            buffer: DataFrame with OHLCV data (full buffer)

        Returns:
            Dict of indicator_name -> value for the last row
        """
        import time
        start = time.perf_counter()

        if buffer is None or len(buffer) == 0:
            return {}

        try:
            # Run batch computation
            result_df = self._engine.calculate_indicators(buffer.copy())

            if result_df is None or len(result_df) == 0:
                return {}

            # Extract last row
            last_row = result_df.iloc[-1]

            # Convert to dict, filtering to numeric indicator columns only
            indicators = {}
            for col in result_df.columns:
                if col not in ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'symbol']:
                    value = last_row[col]
                    if pd.notna(value) and np.isfinite(value):
                        indicators[col] = float(value)

            # Update stats
            elapsed_ms = (time.perf_counter() - start) * 1000
            self._stats['compute_calls'] += 1
            n = self._stats['compute_calls']
            self._stats['avg_compute_ms'] = (
                self._stats['avg_compute_ms'] * (n - 1) + elapsed_ms
            ) / n

            return indicators

        except Exception as e:
            logger.error(f"Indicator computation error: {e}", exc_info=True)
            return {}

    def compute_indicators_batch(
        self,
        buffer: pd.DataFrame,
        last_n: int = 1,
    ) -> pd.DataFrame:
        """
        Compute indicators and return last N rows as DataFrame.

        Useful when you need a small window of indicator values.

        Args:
            buffer: DataFrame with OHLCV data
            last_n: Number of rows to return from end

        Returns:
            DataFrame with indicator values for last N rows
        """
        if buffer is None or len(buffer) == 0:
            return pd.DataFrame()

        try:
            result_df = self._engine.calculate_indicators(buffer.copy())
            return result_df.tail(last_n).copy()
        except Exception as e:
            logger.error(f"Batch indicator computation error: {e}", exc_info=True)
            return pd.DataFrame()

    def get_supported_indicators(self) -> List[str]:
        """Get list of indicators the engine can compute."""
        return self._engine.get_supported_indicators()

    def get_stats(self) -> Dict[str, Any]:
        """Get adapter statistics."""
        return dict(self._stats)

class StreamingFeatureAdapter:
    """
    Wraps feature engineer for streaming use with pre-trained scalers.

    Key constraints:
    - NO fitting in streaming mode (scalers must be pre-trained)
    - Applies transform_single() for single-row transformation
    - Validates that scalers are loaded before transform

    Usage:
        # Offline: train and save scalers
        engineer.fit_scalers(historical_df)
        engineer.save_scalers('scalers.pkl')

        # Online: load and transform
        adapter = StreamingFeatureAdapter(engineer)
        adapter.load_scalers('scalers.pkl')
        features = adapter.transform_single(indicator_dict)
    """

    def __init__(
        self,
        feature_engineer: 'EnhancedFeatureEngineer',
    ):
        """
        Initialize streaming feature adapter.

        Args:
            feature_engineer: The feature engineer to wrap
        """
        self._engineer = feature_engineer
        self._scalers_loaded = False

        # Stats
        self._stats = {
            'transform_calls': 0,
            'avg_transform_ms': 0.0,
            'transform_errors': 0,
        }

    def load_scalers(self, path: str) -> bool:
        """
        Load pre-trained scalers from file.

        Args:
            path: Path to saved scalers

        Returns:
            True if loaded successfully
        """
        try:
            self._engineer.load_scalers(path)
            self._scalers_loaded = True
            logger.info(f"Loaded scalers from {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load scalers: {e}")
            return False

    def transform_single(self, row: Dict[str, float]) -> Dict[str, float]:
        """
        Transform a single row of indicator values to features.

        Args:
            row: Dict of indicator_name -> value

        Returns:
            Dict of feature_name -> transformed_value

        Raises:
            RuntimeError: If scalers not loaded
        """
        if not self._scalers_loaded:
            raise RuntimeError(
                "Scalers not loaded. Call load_scalers() before transform_single()"
            )

        import time
        start = time.perf_counter()

        try:
            # Use the engineer's transform_single method
            result = self._engineer.transform_single(row)

            # Update stats
            elapsed_ms = (time.perf_counter() - start) * 1000
            self._stats['transform_calls'] += 1
            n = self._stats['transform_calls']
            self._stats['avg_transform_ms'] = (
                self._stats['avg_transform_ms'] * (n - 1) + elapsed_ms
            ) / n

            return result

        except Exception as e:
            logger.error(f"Feature transform error: {e}", exc_info=True)
            self._stats['transform_errors'] += 1
            return {}

    def transform_single_unsafe(self, row: Dict[str, float]) -> Dict[str, float]:
        """
        Transform without scaler check (faster, for when you're sure).

        Only use if you have verified scalers are loaded.
        """
        try:
            return self._engineer.transform_single(row)
        except Exception as e:
            logger.error(f"Feature transform error: {e}")
            return {}

    def are_scalers_loaded(self) -> bool:
        """Check if scalers have been loaded."""
        return self._scalers_loaded

    def get_feature_names(self) -> List[str]:
        """Get list of feature names the engineer produces."""
        if hasattr(self._engineer, 'get_feature_names'):
            return self._engineer.get_feature_names()
        return []

    def get_stats(self) -> Dict[str, Any]:
        """Get adapter statistics."""
        return dict(self._stats)

