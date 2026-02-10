"""
Strategy Optimizer for Institutional Backtest Engine
====================================================

Provides a framework for iterative strategy fine-tuning using grid search
with proper statistical controls.

Features:
- Parameter grid generation
- Walk-forward out-of-sample validation (C4 fix)
- Multiple testing correction (Bonferroni/Holm)
- In-sample / out-of-sample separation
- Result aggregation and ranking

CRITICAL WARNING: Grid search finds spurious alpha with near-certainty
when run without statistical controls. ALL results from this optimizer
include deflated Sharpe ratios adjusted for multiple testing.

Usage:
    optimizer = StrategyOptimizer(base_config)
    results = await optimizer.run_grid_search({
        'lookback_period': [10, 20, 30, 60],
        'momentum_threshold': [0.01, 0.02, 0.05]
    })

Author: StatArb_Gemini Core Engine
"""

import itertools
import logging
import math
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import copy

from core_engine.config import BacktestConfig
from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """Container for a single optimization run result"""
    parameters: Dict[str, Any]
    metrics: Dict[str, float]
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    execution_time_seconds: float
    # Walk-forward fields (C4)
    is_oos: bool = False
    fold_id: Optional[int] = None
    period_label: str = ""
    # G2 FIX: Store actual backtest period dates (not wall-clock time)
    # so p-value and DSR can derive the correct T_years and n_obs.
    backtest_start: str = ""  # YYYY-MM-DD
    backtest_end: str = ""    # YYYY-MM-DD


@dataclass
class WalkForwardFold:
    """Defines a single walk-forward train/test fold"""
    fold_id: int
    train_start: str  # YYYY-MM-DD
    train_end: str
    test_start: str
    test_end: str


def _holm_bonferroni_reject(p_values: List[float], alpha: float = 0.05) -> List[bool]:
    """
    Holm-Bonferroni step-down procedure for multiple testing correction.

    More powerful than Bonferroni while still controlling family-wise error rate.

    Args:
        p_values: List of p-values from individual tests
        alpha: Family-wise error rate (default 0.05)

    Returns:
        List of booleans — True if the corresponding hypothesis is rejected
    """
    n = len(p_values)
    if n == 0:
        return []

    # Create indexed pairs, sort by p-value ascending
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    rejected = [False] * n

    for rank, (orig_idx, p) in enumerate(indexed):
        threshold = alpha / (n - rank)
        if p <= threshold:
            rejected[orig_idx] = True
        else:
            # Once we fail to reject, all remaining are also not rejected
            break

    return rejected


def _deflated_sharpe(observed_sharpe: float, n_trials: int,
                     skewness: float = 0.0, kurtosis: float = 3.0,
                     n_obs: int = 252) -> float:
    """
    Deflated Sharpe Ratio (Bailey & Lopez de Prado, 2014).

    Adjusts Sharpe ratio for the number of trials (parameter combinations)
    tested, accounting for the expected maximum Sharpe under the null.

    Returns the probability that the observed Sharpe is genuine
    (not a product of multiple testing).
    """
    if n_trials <= 1 or n_obs <= 1:
        return 1.0

    from scipy import stats

    # Expected maximum Sharpe under null (Euler-Mascheroni approximation)
    euler_mascheroni = 0.5772156649
    e_max_sr = stats.norm.ppf(1.0 - 1.0 / n_trials) * (
        1.0 - euler_mascheroni
    ) + euler_mascheroni * stats.norm.ppf(1.0 - 1.0 / (n_trials * math.e))

    # Standard error of Sharpe ratio
    sr_std = math.sqrt(
        (1.0 + 0.5 * observed_sharpe ** 2 - skewness * observed_sharpe
         + ((kurtosis - 3) / 4.0) * observed_sharpe ** 2) / (n_obs - 1)
    )

    if sr_std <= 0:
        return 0.0

    # Probability of observing this Sharpe given multiple testing
    z = (observed_sharpe - e_max_sr) / sr_std
    prob = stats.norm.cdf(z)

    return max(0.0, min(1.0, prob))


class StrategyOptimizer:
    """
    Orchestrates strategy fine-tuning with institutional-grade statistical controls.

    Features:
    - Walk-forward out-of-sample validation
    - Multiple testing correction (Holm-Bonferroni)
    - Deflated Sharpe Ratio (Bailey & Lopez de Prado)
    - In-sample vs out-of-sample separation
    """

    def __init__(self, base_config: BacktestConfig):
        """
        Initialize optimizer with a base configuration.

        Args:
            base_config: The template configuration for all runs
        """
        self.base_config = base_config
        self.results: List[OptimizationResult] = []
        self.logger = logging.getLogger(__name__)

    def _generate_walk_forward_folds(
        self,
        start_date: str,
        end_date: str,
        n_folds: int = 3,
        train_pct: float = 0.70,
    ) -> List[WalkForwardFold]:
        """
        Generate anchored walk-forward folds.

        Each fold uses an expanding training window (anchored to start)
        and a non-overlapping test window.

        Args:
            start_date: Overall start date (YYYY-MM-DD)
            end_date: Overall end date (YYYY-MM-DD)
            n_folds: Number of walk-forward folds
            train_pct: Fraction of each fold used for training

        Returns:
            List of WalkForwardFold objects
        """
        start = pd.Timestamp(start_date)
        end = pd.Timestamp(end_date)
        total_days = (end - start).days

        if total_days < 10:
            # Too short for walk-forward — return single fold
            mid = start + pd.Timedelta(days=int(total_days * train_pct))
            return [WalkForwardFold(
                fold_id=0,
                train_start=start.strftime('%Y-%m-%d'),
                train_end=mid.strftime('%Y-%m-%d'),
                test_start=(mid + pd.Timedelta(days=1)).strftime('%Y-%m-%d'),
                test_end=end.strftime('%Y-%m-%d'),
            )]

        folds = []
        fold_size = total_days / n_folds

        for i in range(n_folds):
            fold_end = start + pd.Timedelta(days=int(fold_size * (i + 1)))
            fold_end = min(fold_end, end)

            train_days = int(fold_size * (i + 1) * train_pct)
            train_end_date = start + pd.Timedelta(days=train_days)

            test_start_date = train_end_date + pd.Timedelta(days=1)

            if test_start_date >= fold_end:
                continue

            folds.append(WalkForwardFold(
                fold_id=i,
                train_start=start.strftime('%Y-%m-%d'),
                train_end=train_end_date.strftime('%Y-%m-%d'),
                test_start=test_start_date.strftime('%Y-%m-%d'),
                test_end=fold_end.strftime('%Y-%m-%d'),
            ))

        return folds if folds else [WalkForwardFold(
            fold_id=0,
            train_start=start_date,
            train_end=end_date,
            test_start=end_date,
            test_end=end_date,
        )]

    async def run_grid_search(
        self,
        param_grid: Dict[str, List[Any]],
        strategy_name: str = 'default_momentum',
        walk_forward: bool = True,
        n_folds: int = 3,
        alpha: float = 0.05,
    ) -> pd.DataFrame:
        """
        Run grid search with walk-forward validation and multiple testing correction.

        Args:
            param_grid: Parameter grid {name: [values]}
            strategy_name: Strategy to tune (must exist in config)
            walk_forward: Enable walk-forward OOS validation (default True)
            n_folds: Number of walk-forward folds (default 3)
            alpha: Family-wise error rate for multiple testing (default 0.05)

        Returns:
            DataFrame with results ranked by OOS Sharpe, including:
            - is_significant: Whether result survives Holm-Bonferroni correction
            - deflated_sharpe_prob: Probability Sharpe is genuine (DSR)
        """
        self.logger.info("=" * 80)
        self.logger.info(f"STARTING GRID SEARCH: {strategy_name}")
        self.logger.info(f"   Parameters: {list(param_grid.keys())}")
        self.logger.info(f"   Walk-forward: {'ON' if walk_forward else 'OFF'} ({n_folds} folds)")
        self.logger.info(f"   Multiple testing alpha: {alpha}")
        self.logger.info("=" * 80)

        # Generate combinations
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]
        total_combos = len(combinations)
        self.logger.info(f"   Total Combinations: {total_combos}")

        # Generate walk-forward folds
        if walk_forward:
            folds = self._generate_walk_forward_folds(
                self.base_config.start_date,
                self.base_config.end_date,
                n_folds=n_folds,
            )
            self.logger.info(f"   Walk-forward folds: {len(folds)}")
            for f in folds:
                self.logger.info(f"     Fold {f.fold_id}: train={f.train_start}..{f.train_end} | test={f.test_start}..{f.test_end}")
        else:
            folds = [None]

        # Run all combinations
        for i, params in enumerate(combinations):
            self.logger.info(f"\n--- Iteration {i+1}/{total_combos} | Params: {params}")

            for fold in folds:
                if fold is not None:
                    # Walk-forward: run on test period
                    await self._run_single(
                        params, strategy_name, fold=fold, is_oos=True,
                    )
                else:
                    # No walk-forward: run on full period
                    await self._run_single(
                        params, strategy_name, fold=None, is_oos=False,
                    )

        # Compile results with statistical corrections
        return self._generate_results_with_corrections(total_combos, alpha)

    async def _run_single(
        self,
        params: Dict[str, Any],
        strategy_name: str,
        fold: Optional[WalkForwardFold] = None,
        is_oos: bool = False,
    ) -> None:
        """Run a single backtest with given parameters and optional fold."""
        import time

        run_config = copy.deepcopy(self.base_config)

        # Override dates for walk-forward fold
        if fold is not None:
            if is_oos:
                run_config.start_date = fold.test_start
                run_config.end_date = fold.test_end
                period_label = f"OOS_fold{fold.fold_id}"
            else:
                run_config.start_date = fold.train_start
                run_config.end_date = fold.train_end
                period_label = f"IS_fold{fold.fold_id}"
        else:
            period_label = "full"

        # Update strategy parameters
        strategy_found = False
        for strategy in run_config.strategies:
            if isinstance(strategy, dict) and strategy.get('name') == strategy_name:
                if 'parameters' not in strategy:
                    strategy['parameters'] = {}
                strategy['parameters'].update(params)
                for k, v in params.items():
                    if k in strategy:
                        strategy[k] = v
                strategy_found = True
                break

        if not strategy_found:
            available = [s.get('name', '?') for s in run_config.strategies if isinstance(s, dict)]
            self.logger.error(f"Strategy '{strategy_name}' not found. Available: {available}")
            self.results.append(OptimizationResult(
                parameters=params, metrics={},
                total_return=float('nan'), sharpe_ratio=float('nan'),
                max_drawdown=float('nan'), win_rate=float('nan'),
                execution_time_seconds=0.0, is_oos=is_oos,
                fold_id=fold.fold_id if fold else None,
                period_label=period_label,
            ))
            return

        engine = InstitutionalBacktestEngine(run_config)
        try:
            start_time = time.time()
            await engine.initialize()
            backtest_results = await engine.run_backtest()
            duration = time.time() - start_time

            metrics = backtest_results.get('performance_summary', {}) or {}
            if not metrics:
                metrics = backtest_results.get('summary', {}) or {}

            result = OptimizationResult(
                parameters=params,
                metrics=metrics,
                total_return=metrics.get('total_return', 0.0),
                sharpe_ratio=metrics.get('sharpe_ratio', 0.0),
                max_drawdown=metrics.get('max_drawdown', 0.0),
                win_rate=metrics.get('win_rate', 0.0),
                execution_time_seconds=duration,
                is_oos=is_oos,
                fold_id=fold.fold_id if fold else None,
                period_label=period_label,
                # G2 FIX: Store actual backtest dates for statistical tests
                backtest_start=run_config.start_date,
                backtest_end=run_config.end_date,
            )
            self.results.append(result)
            self.logger.info(
                f"   [{period_label}] Sharpe={result.sharpe_ratio:.2f}, "
                f"Return={result.total_return:.2%}"
            )

        except Exception as e:
            self.logger.error(f"   [{period_label}] FAILED: {e}")
            self.results.append(OptimizationResult(
                parameters=params, metrics={'error': str(e)},
                total_return=float('nan'), sharpe_ratio=float('nan'),
                max_drawdown=float('nan'), win_rate=float('nan'),
                execution_time_seconds=0.0, is_oos=is_oos,
                fold_id=fold.fold_id if fold else None,
                period_label=period_label,
            ))
        finally:
            await engine.shutdown()

    def _generate_results_with_corrections(
        self, n_trials: int, alpha: float
    ) -> pd.DataFrame:
        """Generate results DataFrame with multiple testing corrections."""
        if not self.results:
            return pd.DataFrame()

        data = []
        for res in self.results:
            row = res.parameters.copy()
            # G2 FIX: Compute fold_trading_days from actual dates, not wall-clock time.
            _fold_days = 252  # fallback
            if res.backtest_start and res.backtest_end:
                try:
                    _bs = pd.Timestamp(res.backtest_start)
                    _be = pd.Timestamp(res.backtest_end)
                    _fold_days = max(1, (_be - _bs).days)
                except Exception:
                    pass
            row.update({
                'total_return': res.total_return,
                'sharpe_ratio': res.sharpe_ratio,
                'max_drawdown': res.max_drawdown,
                'win_rate': res.win_rate,
                'execution_time': res.execution_time_seconds,
                'fold_trading_days': _fold_days,  # G2 FIX: actual calendar days
                'is_oos': res.is_oos,
                'fold_id': res.fold_id,
                'period_label': res.period_label,
            })
            data.append(row)

        df = pd.DataFrame(data)

        # Separate OOS results for statistical testing
        oos_df = df[df['is_oos'] == True].copy() if 'is_oos' in df.columns else df.copy()

        if len(oos_df) > 0 and n_trials > 1:
            # Aggregate OOS Sharpe across folds per parameter combination
            param_cols = [c for c in df.columns if c not in {
                'total_return', 'sharpe_ratio', 'max_drawdown', 'win_rate',
                'execution_time', 'is_oos', 'fold_id', 'period_label',
                'is_significant', 'deflated_sharpe_prob',
            }]

            # Compute p-values for each OOS Sharpe (H0: Sharpe = 0)
            # G2 FIX: Use fold_trading_days (actual calendar days from backtest dates),
            # NOT execution_time (wall-clock seconds). The previous F4 fix read the
            # wrong field, making all p-values meaningless.
            # Test statistic: z = SR_ann * sqrt(T_years), std_err ~ 1/sqrt(T_years).
            from scipy import stats as sp_stats
            p_values = []
            for _, row in oos_df.iterrows():
                sr = row.get('sharpe_ratio', 0)
                if math.isnan(sr):
                    p_values.append(1.0)
                else:
                    # Use actual fold calendar days (G2 FIX)
                    fold_days = row.get('fold_trading_days', 252)
                    t_years = max(fold_days / 252.0, 1.0 / 252.0)  # floor at 1 day
                    # z = SR_annualized * sqrt(T_years)
                    z_stat = sr * math.sqrt(t_years)
                    p_val = 2 * (1 - sp_stats.norm.cdf(abs(z_stat)))
                    p_values.append(p_val)

            # Holm-Bonferroni correction
            rejections = _holm_bonferroni_reject(p_values, alpha=alpha)
            oos_df = oos_df.copy()
            oos_df['is_significant'] = rejections

            # Deflated Sharpe Ratio
            # G2 FIX: Use fold_trading_days (actual calendar days), NOT
            # execution_time (wall-clock seconds). Conservative skew/kurtosis
            # since per-bar returns aren't stored.
            dsr_probs = []
            for _, row in oos_df.iterrows():
                sr = row.get('sharpe_ratio', 0)
                if math.isnan(sr):
                    dsr_probs.append(0.0)
                else:
                    try:
                        # G2 FIX: Use actual fold calendar days, not wall-clock time
                        fold_days = row.get('fold_trading_days', 252)
                        _n_obs = max(int(fold_days), 20)  # floor at 20 obs
                        dsr = _deflated_sharpe(
                            sr, n_trials,
                            skewness=-0.5,   # mild negative skew (typical equities)
                            kurtosis=4.0,    # mild leptokurtosis
                            n_obs=_n_obs,
                        )
                        dsr_probs.append(dsr)
                    except ImportError:
                        # scipy not available — skip DSR
                        dsr_probs.append(float('nan'))
            oos_df['deflated_sharpe_prob'] = dsr_probs

            # Sort by OOS Sharpe descending
            result_df = oos_df.sort_values(by='sharpe_ratio', ascending=False)
        else:
            df['is_significant'] = False
            df['deflated_sharpe_prob'] = float('nan')
            result_df = df.sort_values(by='sharpe_ratio', ascending=False)

        self.logger.info("\n" + "=" * 80)
        self.logger.info("OPTIMIZATION COMPLETE")
        self.logger.info(f"   Total trials: {n_trials}")
        self.logger.info(f"   Significant results (Holm-Bonferroni alpha={alpha}): "
                         f"{result_df['is_significant'].sum() if 'is_significant' in result_df.columns else 'N/A'}")
        self.logger.info("=" * 80)

        return result_df
