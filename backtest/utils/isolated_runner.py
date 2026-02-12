"""
Isolated Strategy Runner Utilities
====================================

Reusable aggregation logic for running multiple strategies in isolation
and combining results with proper capital weighting.

Used by smoke_test, and any experiment needing per-strategy isolated backtests.

Author: StatArb_Gemini Core Engine
"""

from typing import Any, Dict, List

from backtest.utils import trade_timestamp_key
from backtest.utils.statistics import compute_hypothesis_tests, compute_oos_validation


class RunAggregator:
    """
    Accumulates results from multiple isolated strategy backtest runs
    and builds a combined summary.

    Usage:
        agg = RunAggregator(initial_capital=100000)
        agg.add_run(strategy_name, engine_results, metrics, alloc_weight, execution_history)
        ...
        result = agg.build_combined(experiment_name, include_hypothesis_tests=True)
    """

    def __init__(self, initial_capital: float = 100_000.0):
        self.initial_capital = initial_capital
        self.isolated_runs: List[Dict[str, Any]] = []
        self.combined_execution_history: List[Dict[str, Any]] = []
        self.total_return = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.max_drawdown_pct = 0.0
        self.max_drawdown = 0.0
        self.sharpe_weighted_sum = 0.0
        self.sharpe_weight = 0.0
        self.bars_processed = 0

    def add_run(
        self,
        strategy_name: str,
        engine_results: Dict[str, Any],
        metrics: Dict[str, Any],
        alloc_weight: float,
        execution_history: List[Dict[str, Any]],
    ) -> None:
        """
        Record a single strategy run.

        Args:
            strategy_name: Label for this strategy run
            engine_results: Raw engine output dict
            metrics: Extracted performance metrics (from _extract_performance_metrics)
            alloc_weight: Capital weight [0..1] for this run
            execution_history: List of fill/trade dicts from engine
        """
        run_summary = (engine_results.get('summary') or {}) if engine_results else {}

        # Weighted return
        run_total_return = run_summary.get('total_return', metrics['total_return_pct'] / 100.0)
        self.total_return += run_total_return * alloc_weight

        # Trades
        run_total_trades = run_summary.get('total_trades', metrics['total_trades'])
        self.total_trades += int(run_total_trades or 0)

        run_wins = run_summary.get('winning_trades', 0) or 0
        run_losses = run_summary.get('losing_trades', 0) or 0
        self.winning_trades += int(run_wins)
        self.losing_trades += int(run_losses)

        # Drawdown (take worst across runs)
        run_max_dd_pct = run_summary.get('max_drawdown_pct', 0.0) or 0.0
        run_max_dd = run_summary.get('max_drawdown', 0.0) or 0.0
        self.max_drawdown_pct = max(self.max_drawdown_pct, float(run_max_dd_pct))
        self.max_drawdown = max(self.max_drawdown, float(run_max_dd))

        # Sharpe (capital-weighted)
        run_sharpe = run_summary.get('sharpe_ratio', metrics['sharpe_ratio']) or 0.0
        self.sharpe_weighted_sum += float(run_sharpe) * alloc_weight
        self.sharpe_weight += alloc_weight

        # Execution history with strategy label
        for trade in execution_history:
            trade_copy = dict(trade)
            trade_copy['strategy_run'] = strategy_name
            self.combined_execution_history.append(trade_copy)

        # Bars processed (take max across runs)
        self.bars_processed = max(
            self.bars_processed,
            engine_results.get('total_bars', 0) if engine_results else 0,
        )

        self.isolated_runs.append({
            'strategy_name': strategy_name,
            'engine_results': engine_results,
            'metrics': metrics,
        })

    def build_combined(
        self,
        experiment_name: str,
        include_hypothesis_tests: bool = False,
    ) -> Dict[str, Any]:
        """
        Build the final combined result dict.

        Args:
            experiment_name: Name prefix for the combined summary
            include_hypothesis_tests: If True, compute paired t-tests and OOS validation

        Returns:
            Combined result dict compatible with ExperimentResult expectations
        """
        # Sort execution history for deterministic output
        self.combined_execution_history.sort(key=trade_timestamp_key)

        combined_final_capital = self.initial_capital + (self.initial_capital * self.total_return)
        combined_win_rate = (self.winning_trades / self.total_trades) if self.total_trades > 0 else 0.0
        combined_sharpe = (self.sharpe_weighted_sum / self.sharpe_weight) if self.sharpe_weight > 0 else 0.0

        combined_summary: Dict[str, Any] = {
            "backtest_name": f"{experiment_name}_isolated_combined",
            "total_bars_processed": self.bars_processed,
            "total_trades": self.total_trades,
            "total_executions": self.total_trades,
            "initial_capital": self.initial_capital,
            "final_capital": combined_final_capital,
            "total_return": self.total_return,
            "sharpe_ratio": combined_sharpe,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_pct": self.max_drawdown_pct,
            "win_rate": combined_win_rate,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "execution_history": self.combined_execution_history,
            "position_history": [],
        }

        if include_hypothesis_tests:
            combined_summary["hypothesis_tests"] = compute_hypothesis_tests(self.isolated_runs)
            combined_summary["oos_validation"] = compute_oos_validation(self.isolated_runs)

        return {
            'success': all(
                r.get('engine_results', {}).get('success', True)
                for r in self.isolated_runs
            ),
            'summary': combined_summary,
            'execution_history': self.combined_execution_history,
            'total_bars': self.bars_processed,
            'bars_processed': self.bars_processed,
            'total_trades': self.total_trades,
            'final_capital': combined_final_capital,
            'isolated_runs': self.isolated_runs,
        }
