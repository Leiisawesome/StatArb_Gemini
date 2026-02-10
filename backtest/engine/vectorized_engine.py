"""
Vectorized Backtest Engine (Skeleton)
=====================================

High-performance backtest engine for rapid strategy fine-tuning.
Uses vectorized operations (Pandas/Numpy) instead of event loop.

Status: PROTOTYPE / SKELETON
Future Work: Implement full vectorized logic for all strategies.

WARNING: This engine bypasses the full pipeline (no regime detection, no risk
authorization, no compliance checks, no realistic cost modeling). Results from
this engine MUST NOT be compared with InstitutionalBacktestEngine output or
used for capital allocation decisions. Use only for rapid screening.

Author: StatArb_Gemini Core Engine
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, Optional
from core_engine.config import BacktestConfig

# Annualization factors by interval
_ANNUALIZATION_FACTORS = {
    '1min': np.sqrt(252 * 390),  # 390 1-min bars per trading day
    '5min': np.sqrt(252 * 78),
    '15min': np.sqrt(252 * 26),
    '30min': np.sqrt(252 * 13),
    '1H': np.sqrt(252 * 6.5),
    '1D': np.sqrt(252),
}

class VectorizedBacktestEngine:
    """
    Vectorized backtest engine for rapid strategy screening.
    Trade-off: Speed >> Fidelity.

    WARNING: Bypasses regime detection, risk authorization, compliance checks,
    and realistic cost modeling. Use for screening only.
    """

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

    async def run(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Run vectorized backtest on provided dataframe.

        Args:
            data: OHLCV DataFrame

        Returns:
            Dict with performance metrics
        """
        self.logger.warning(
            "VectorizedBacktestEngine: No regime/risk/compliance checks. "
            "Results are for rapid screening only — not for capital decisions."
        )
        self.logger.info("Starting Vectorized Backtest...")

        # Extract strategy parameters from config (M7 fix — was hardcoded SMA 20/50)
        fast_window = 20
        slow_window = 50
        if self.config.strategies:
            params = self.config.strategies[0].get('parameters', {})
            fast_window = params.get('fast_window', params.get('lookback', 20))
            slow_window = params.get('slow_window', 50)

        df = data.copy()
        df['sma_fast'] = df['close'].rolling(window=fast_window).mean()
        df['sma_slow'] = df['close'].rolling(window=slow_window).mean()

        df['signal'] = 0
        df.loc[df['sma_fast'] > df['sma_slow'], 'signal'] = 1   # Long
        df.loc[df['sma_fast'] < df['sma_slow'], 'signal'] = -1  # Short

        # Calculate Returns
        df['returns'] = df['close'].pct_change()
        df['strategy_returns'] = df['signal'].shift(1) * df['returns']

        # Drop warmup NaN rows before computing metrics
        strategy_returns = df['strategy_returns'].dropna()

        # Calculate Metrics with proper annualization based on interval
        total_return = (1 + strategy_returns).prod() - 1
        annualization = _ANNUALIZATION_FACTORS.get(self.config.interval, np.sqrt(252))
        std = strategy_returns.std()
        sharpe = (strategy_returns.mean() / std * annualization) if std > 0 else 0.0

        return {
            'total_return': total_return,
            'sharpe_ratio': sharpe,
            '_warning': 'Vectorized engine — no risk/regime/compliance checks applied',
        }

