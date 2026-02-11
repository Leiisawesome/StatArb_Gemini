"""
Experiment 1: Smoke Test
=========================

Minimal sanity check to verify engine initialization and basic functionality.

Purpose:
- Verify engine can initialize without errors
- Run on single symbol, short period, simple strategy
- Validate output structure

Expected Duration: < 30 seconds

Author: StatArb_Gemini Core Engine
"""

import asyncio
import argparse
from datetime import datetime
from typing import Dict, Any, List, Optional
import time
import os

from backtest.experiments.base_experiment import BaseExperiment, ExperimentResult
from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine
from core_engine.config import BacktestConfig
from backtest.utils.paths import backtest_results_dir
from backtest.utils import trade_timestamp_key
import numpy as np

class SmokeTest(BaseExperiment):
    """
    Smoke test experiment.

    Tests:
    - Engine initialization
    - Single symbol, 1-day backtest
    - Simple mean reversion strategy
    - Result generation
    """

    def get_description(self) -> str:
        return "Smoke test: Single symbol, 1-day, simple strategy"

    async def run(self) -> ExperimentResult:
        """Run smoke test"""
        start_time = time.time()
        experiment_name = self.config.get('experiment_name', 'Smoke_Test')

        # --- Configure pipeline tracer if enabled in config ---
        if self.config.get('enable_pipeline_trace', False):
            from core_engine.utils.pipeline_trace import get_tracer
            _tracer = get_tracer()
            _tracer.configure(
                enabled=True,
                output_dir=str(self.output_dir),
                session_id=f"trace-{experiment_name.lower().replace(' ', '_')}",
            )
            self.logger.info("Pipeline trace enabled: checkpoints will be recorded")

        try:
            self.logger.info(f"[SETUP] Starting smoke test: {experiment_name}")

            isolate_strategy_backtests = bool(self.config.get('isolate_strategy_backtests', False))
            strategies = self.config.get('strategies', []) or []

            if isolate_strategy_backtests and len(strategies) > 1:
                self.logger.info("   Isolated strategy backtests enabled (per-strategy runs).")
                engine_results = await self._run_isolated_strategy_backtests(experiment_name, strategies)
            else:
                # Create minimal backtest config
                backtest_config = self._create_backtest_config()

                # Initialize engine (ORCHESTRATION ONLY - no logic re-implementation)
                self.logger.info("   Initializing InstitutionalBacktestEngine...")
                engine = InstitutionalBacktestEngine(backtest_config)
                try:
                    await engine.initialize()

                    # Run backtest (black box)
                    self.logger.info("   Running backtest...")
                    engine_results = await engine.run_backtest()
                finally:
                    # Shutdown engine to release resources (Rule 1 compliance)
                    await engine.shutdown()

            # Extract metrics
            duration = time.time() - start_time
            metrics = self._extract_performance_metrics(engine_results)

            # Create result
            result = ExperimentResult(
                experiment_name=experiment_name,
                experiment_type="smoke_test",
                run_timestamp=datetime.now(),
                duration_seconds=duration,
                engine_results=engine_results,
                total_return_pct=metrics['total_return_pct'],
                sharpe_ratio=metrics['sharpe_ratio'],
                max_drawdown_pct=metrics['max_drawdown_pct'],
                total_trades=metrics['total_trades'],
                win_rate=metrics['win_rate'],
                custom_metrics={
                    'bars_processed': engine_results.get('total_bars', 0),
                    'initialization_time_s': engine_results.get('initialization_time', 0.0),
                },
                success=True
            )

            # --- Finalize pipeline tracer ---
            if self.config.get('enable_pipeline_trace', False):
                from core_engine.utils.pipeline_trace import get_tracer
                _tracer = get_tracer()
                if _tracer.enabled:
                    _tracer.print_funnel()
                    result.custom_metrics['trace_funnel'] = _tracer.get_funnel_summary()
                    result.custom_metrics['trace_stats'] = _tracer.stats
                    _tracer.close()

            self.logger.info(f"[OK] Smoke test completed in {duration:.2f}s")
            return result

        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"[FAIL] Smoke test failed: {e}")

            return ExperimentResult(
                experiment_name=experiment_name,
                experiment_type="smoke_test",
                run_timestamp=datetime.now(),
                duration_seconds=duration,
                engine_results={},
                total_return_pct=0.0,
                sharpe_ratio=0.0,
                max_drawdown_pct=0.0,
                total_trades=0,
                win_rate=0.0,
                success=False,
                error_message=str(e)
            )

    def _create_backtest_config(self, source_config: Optional[Dict[str, Any]] = None) -> BacktestConfig:
        """Create backtest config from YAML configuration"""
        config_source = source_config or self.config
        # Build config from YAML (prefer YAML over defaults)
        config_dict = {
            'backtest_name': config_source.get('experiment_name', 'Smoke_Test'),
            'symbols': config_source.get('symbols', ['AAPL']),
            'interval': config_source.get('interval', '1min'),
            'start_date': config_source.get('start_date', '2024-01-02'),
            'end_date': config_source.get('end_date', '2024-01-02'),
            'warmup_bars': config_source.get('warmup_bars', None),
            'initial_capital': config_source.get('initial_capital', 100000),
            'allow_shorts': config_source.get('allow_shorts', False),
            'max_position_size': config_source.get('max_position_size', 0.10),
            'max_position_pct': config_source.get('max_position_pct', None),
            'max_concentration': config_source.get('max_concentration', 0.20),
            'min_signal_confidence': config_source.get('min_signal_confidence', 0.60),
            # v5.0: Strategy aggregator minimum confidence threshold
            'min_confidence_threshold': config_source.get('min_confidence_threshold', 0.60),
            # v5.1: Strategy manager coordination/aggregation toggles
            'enable_multi_strategy_coordination': config_source.get('enable_multi_strategy_coordination', True),
            'enable_signal_aggregation': config_source.get('enable_signal_aggregation', True),
            'enable_conflict_resolution': config_source.get('enable_conflict_resolution', True),
            'enable_dynamic_weighting': config_source.get('enable_dynamic_weighting', True),
            # Canonicalize all backtest outputs under backtest/results/ regardless of CWD
            'output_directory': str(backtest_results_dir()),
        }

        # Add regime risk multipliers if provided
        if 'regime_risk_multipliers' in config_source:
            config_dict['regime_risk_multipliers'] = config_source['regime_risk_multipliers']
        else:
            config_dict['regime_risk_multipliers'] = {
                'low_volatility': 1.0,
                'normal_volatility': 1.0,
                'high_volatility': 0.7
            }

        # Add strategies from YAML if provided
        if 'strategies' in config_source:
            config_dict['strategies'] = config_source['strategies']
        else:
            # Fallback minimal strategy
            config_dict['strategies'] = [{
                'type': 'mean_reversion',
                'name': 'MR_Simple',
                'allocation_pct': 1.0,
                'parameters': {
                    'lookback': 20,
                    'z_entry': 2.0,
                    'z_exit': 0.5
                }
            }]

        # Note: save_trade_log and save_regime_log are not BacktestConfig params
        # They would be handled at engine level if needed

        return BacktestConfig(**config_dict)

    async def _run_isolated_strategy_backtests(
        self,
        experiment_name: str,
        strategies: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Run each strategy in isolation and aggregate results proportionally.

        H3 FIX: Each strategy receives capital proportional to its allocation_pct
        (defaults to equal split). Combined returns are weighted accordingly,
        preventing the unrealistic scenario of 100% capital per strategy.
        """
        external_configs = self.config.get('external_strategy_configs', []) or []
        if external_configs:
            return await self._run_external_config_backtests(experiment_name, external_configs)

        isolated_runs = []
        combined_execution_history = []

        total_return = 0.0
        total_trades = 0
        winning_trades = 0
        losing_trades = 0
        max_drawdown_pct = 0.0
        max_drawdown = 0.0

        sharpe_weighted_sum = 0.0
        sharpe_weight = 0

        initial_capital = float(self.config.get('initial_capital', 100000))
        bars_processed = 0

        # H3 FIX: Compute capital allocation weights
        total_alloc = sum(s.get('allocation_pct', 1.0 / len(strategies)) for s in strategies)

        # C7 R3 FIX: Validate allocation sums to ~1.0 when explicitly set
        has_explicit_alloc = any('allocation_pct' in s for s in strategies)
        if has_explicit_alloc and abs(total_alloc - 1.0) > 0.05:
            self.logger.warning(
                f"[WARN] allocation_pct values sum to {total_alloc:.3f} (expected ~1.0). "
                f"Capital will be normalized but results may not match expectations."
            )

        for idx, strategy in enumerate(strategies, start=1):
            strategy_name = strategy.get('name', f"strategy_{idx}")
            isolated_name = f"{experiment_name}_{strategy_name}"

            # H3 FIX: Allocate capital proportionally
            alloc_pct = strategy.get('allocation_pct', 1.0 / len(strategies))
            strategy_capital = initial_capital * (alloc_pct / total_alloc)

            run_config = dict(self.config)
            run_config['experiment_name'] = isolated_name
            run_config['strategies'] = [strategy]
            run_config['initial_capital'] = strategy_capital

            backtest_config = self._create_backtest_config(run_config)

            self.logger.info(f"   ▶️  Isolated run: {strategy_name}")
            engine = InstitutionalBacktestEngine(backtest_config)
            try:
                await engine.initialize()
                engine_results = await engine.run_backtest()
            finally:
                await engine.shutdown()

            run_summary = (engine_results.get('summary') or {}) if engine_results else {}
            run_metrics = self._extract_performance_metrics(engine_results or {})

            # H3 FIX: Weight return by allocation fraction so combined return
            # reflects actual capital deployment (not 100% per strategy).
            alloc_weight = alloc_pct / total_alloc
            run_total_return = run_summary.get('total_return', run_metrics['total_return_pct'] / 100.0)
            total_return += run_total_return * alloc_weight

            run_total_trades = run_summary.get('total_trades', run_metrics['total_trades'])
            total_trades += int(run_total_trades or 0)

            run_wins = run_summary.get('winning_trades', 0) or 0
            run_losses = run_summary.get('losing_trades', 0) or 0
            winning_trades += int(run_wins)
            losing_trades += int(run_losses)

            run_max_dd_pct = run_summary.get('max_drawdown_pct', 0.0) or 0.0
            run_max_dd = run_summary.get('max_drawdown', 0.0) or 0.0
            max_drawdown_pct = max(max_drawdown_pct, float(run_max_dd_pct))
            max_drawdown = max(max_drawdown, float(run_max_dd))

            run_sharpe = run_summary.get('sharpe_ratio', run_metrics['sharpe_ratio']) or 0.0
            # G6 FIX: Weight Sharpe by capital allocation, not trade count.
            # Trade-count weighting biases toward high-turnover strategies.
            sharpe_weighted_sum += float(run_sharpe) * alloc_weight
            sharpe_weight += alloc_weight

            run_execution_history = engine_results.get('execution_history', []) if engine_results else []
            for trade in run_execution_history:
                trade_copy = dict(trade)
                trade_copy['strategy_run'] = strategy_name
                combined_execution_history.append(trade_copy)

            bars_processed = max(bars_processed, engine_results.get('total_bars', 0) if engine_results else 0)

            isolated_runs.append({
                'strategy_name': strategy_name,
                'engine_results': engine_results,
                'metrics': run_metrics,
            })

        hypothesis_tests = self._compute_hypothesis_tests(isolated_runs)
        oos_validation = self._compute_oos_validation(isolated_runs)

        # Sort by timestamp for deterministic trade list output (M4 fix — use shared utility)
        combined_execution_history.sort(key=trade_timestamp_key)

        combined_final_capital = initial_capital + (initial_capital * total_return)
        combined_win_rate = (winning_trades / total_trades) if total_trades > 0 else 0.0
        combined_sharpe = (sharpe_weighted_sum / sharpe_weight) if sharpe_weight > 0 else 0.0

        combined_summary = {
            "backtest_name": f"{experiment_name}_isolated_combined",
            "total_bars_processed": bars_processed,
            "total_trades": total_trades,
            "total_executions": total_trades,
            "initial_capital": initial_capital,
            "final_capital": combined_final_capital,
            "total_return": total_return,
            "sharpe_ratio": combined_sharpe,
            "max_drawdown": max_drawdown,
            "max_drawdown_pct": max_drawdown_pct,
            "win_rate": combined_win_rate,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "execution_history": combined_execution_history,
            "position_history": [],
            "hypothesis_tests": hypothesis_tests,
            "oos_validation": oos_validation,
        }

        return {
            'success': all(r.get('engine_results', {}).get('success', True) for r in isolated_runs),
            'summary': combined_summary,
            'execution_history': combined_execution_history,
            'total_bars': bars_processed,
            'bars_processed': bars_processed,
            'total_trades': total_trades,
            'final_capital': combined_final_capital,
            'isolated_runs': isolated_runs,
        }

    def _extract_equity_returns(self, engine_results: Dict[str, Any]) -> List[float]:
        """Extract per-bar returns from position history."""
        summary = engine_results.get("summary") if engine_results else {}
        position_history = summary.get("position_history", []) if summary else []
        if not position_history:
            return []
        equities = [snap.get("equity") for snap in position_history if snap.get("equity") is not None]
        returns = []
        for i in range(1, len(equities)):
            prev = equities[i - 1]
            curr = equities[i]
            if prev and prev != 0:
                returns.append((curr - prev) / prev)
        return returns

    def _paired_t_test(self, a: List[float], b: List[float]) -> Dict[str, Any]:
        """Paired t-test using proper t-distribution (not normal approximation).

        F13 FIX: The normal approximation inflates significance for small
        samples (n < 30). Using scipy's t-distribution with (n-1) degrees
        of freedom gives the correct p-value.
        """
        n = min(len(a), len(b))
        if n < 2:
            return {"p_value": None, "t_stat": None, "n": n}
        diffs = np.array(a[:n]) - np.array(b[:n])
        mean_diff = float(np.mean(diffs))
        std_diff = float(np.std(diffs, ddof=1))
        if std_diff == 0:
            return {"p_value": 1.0, "t_stat": 0.0, "n": n}
        t_stat = mean_diff / (std_diff / np.sqrt(n))
        # Use t-distribution with n-1 degrees of freedom
        try:
            from scipy import stats as sp_stats
            p_value = float(2.0 * sp_stats.t.sf(abs(t_stat), df=n - 1))
        except ImportError:
            # Fallback: normal approximation if scipy unavailable
            p_value = float(2.0 * (1.0 - 0.5 * (1.0 + np.math.erf(abs(t_stat) / np.sqrt(2)))))
        return {"p_value": p_value, "t_stat": float(t_stat), "n": n}

    def _compute_hypothesis_tests(self, isolated_runs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute paired t-tests for hybrid vs MOM/MR if available."""
        returns_by_name = {}
        for run in isolated_runs:
            name = str(run.get("strategy_name", "")).lower()
            returns_by_name[name] = self._extract_equity_returns(run.get("engine_results", {}) or {})

        hybrid = next((v for k, v in returns_by_name.items() if "hybrid" in k), None)
        mom = next((v for k, v in returns_by_name.items() if "mom" in k), None)
        mr = next((v for k, v in returns_by_name.items() if "mr" in k), None)

        results = {}
        if hybrid and mom:
            results["hybrid_vs_mom"] = self._paired_t_test(hybrid, mom)
        if hybrid and mr:
            results["hybrid_vs_mr"] = self._paired_t_test(hybrid, mr)
        return results

    def _compute_oos_validation(self, isolated_runs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Simple train/test split validation from equity returns."""
        oos = {}
        for run in isolated_runs:
            name = str(run.get("strategy_name", "")).lower()
            returns = self._extract_equity_returns(run.get("engine_results", {}) or {})
            if len(returns) < 4:
                continue
            split = len(returns) // 2
            train = returns[:split]
            test = returns[split:]
            oos[name] = {
                "train_mean_return": float(np.mean(train)) if train else 0.0,
                "test_mean_return": float(np.mean(test)) if test else 0.0,
                "train_std_return": float(np.std(train)) if train else 0.0,
                "test_std_return": float(np.std(test)) if test else 0.0,
                "n_train": len(train),
                "n_test": len(test),
            }
        return oos

    async def _run_external_config_backtests(
        self,
        experiment_name: str,
        config_paths: List[str],
    ) -> Dict[str, Any]:
        """Run isolated backtests from explicit config paths and aggregate results."""
        from pathlib import Path
        from backtest.utils.config_loader import load_config

        isolated_runs = []
        combined_execution_history = []

        total_return = 0.0
        total_trades = 0
        winning_trades = 0
        losing_trades = 0
        max_drawdown_pct = 0.0
        max_drawdown = 0.0

        sharpe_weighted_sum = 0.0
        sharpe_weight = 0

        initial_capital = float(self.config.get('initial_capital', 100000))
        bars_processed = 0

        for raw_path in config_paths:
            cfg_path = Path(raw_path).expanduser()
            self.logger.info(f"   ▶️  External isolated run: {cfg_path}")
            cfg = load_config(str(cfg_path))

            backtest_config = self._create_backtest_config(cfg)

            engine = InstitutionalBacktestEngine(backtest_config)
            try:
                await engine.initialize()
                engine_results = await engine.run_backtest()
            finally:
                await engine.shutdown()

            run_summary = (engine_results.get('summary') or {}) if engine_results else {}
            run_metrics = self._extract_performance_metrics(engine_results or {})

            # G7 FIX: Weight returns/Sharpe by equal allocation (1/N) for external configs,
            # matching the isolated-strategy path. Without this, summing raw returns
            # from N configs each using 100% capital overstates combined performance.
            _ext_alloc_weight = 1.0 / len(config_paths)

            run_total_return = run_summary.get('total_return', run_metrics['total_return_pct'] / 100.0)
            total_return += run_total_return * _ext_alloc_weight

            run_total_trades = run_summary.get('total_trades', run_metrics['total_trades'])
            total_trades += int(run_total_trades or 0)

            run_wins = run_summary.get('winning_trades', 0) or 0
            run_losses = run_summary.get('losing_trades', 0) or 0
            winning_trades += int(run_wins)
            losing_trades += int(run_losses)

            run_max_dd_pct = run_summary.get('max_drawdown_pct', 0.0) or 0.0
            run_max_dd = run_summary.get('max_drawdown', 0.0) or 0.0
            max_drawdown_pct = max(max_drawdown_pct, float(run_max_dd_pct))
            max_drawdown = max(max_drawdown, float(run_max_dd))

            run_sharpe = run_summary.get('sharpe_ratio', run_metrics['sharpe_ratio']) or 0.0
            # G6/G7 FIX: Weight by allocation, not trade count
            sharpe_weighted_sum += float(run_sharpe) * _ext_alloc_weight
            sharpe_weight += _ext_alloc_weight

            run_execution_history = engine_results.get('execution_history', []) if engine_results else []
            for trade in run_execution_history:
                trade_copy = dict(trade)
                trade_copy['strategy_run'] = str(cfg_path)
                combined_execution_history.append(trade_copy)

            bars_processed = max(bars_processed, engine_results.get('total_bars', 0) if engine_results else 0)

            isolated_runs.append({
                'strategy_name': run_summary.get('backtest_name', cfg_path.name),
                'engine_results': engine_results,
                'metrics': run_metrics,
            })

        combined_execution_history.sort(key=trade_timestamp_key)

        combined_final_capital = initial_capital + (initial_capital * total_return)
        combined_win_rate = (winning_trades / total_trades) if total_trades > 0 else 0.0
        combined_sharpe = (sharpe_weighted_sum / sharpe_weight) if sharpe_weight > 0 else 0.0

        combined_summary = {
            "backtest_name": f"{experiment_name}_isolated_combined",
            "total_bars_processed": bars_processed,
            "total_trades": total_trades,
            "total_executions": total_trades,
            "initial_capital": initial_capital,
            "final_capital": combined_final_capital,
            "total_return": total_return,
            "sharpe_ratio": combined_sharpe,
            "max_drawdown": max_drawdown,
            "max_drawdown_pct": max_drawdown_pct,
            "win_rate": combined_win_rate,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "execution_history": combined_execution_history,
            "position_history": [],
        }

        return {
            'success': all(r.get('engine_results', {}).get('success', True) for r in isolated_runs),
            'summary': combined_summary,
            'execution_history': combined_execution_history,
            'total_bars': bars_processed,
            'bars_processed': bars_processed,
            'total_trades': total_trades,
            'final_capital': combined_final_capital,
            'isolated_runs': isolated_runs,
        }

# Standalone run function
async def run_smoke_test(config: Dict[str, Any] = None):
    """
    Run smoke test experiment.

    Args:
        config: Optional config dict. If None, loads from YAML.
    """
    if config is None:
        # Load from YAML configuration file
        from backtest.utils.config_loader import load_config
        from pathlib import Path

        try:
            # Allow override without changing defaults:
            # - CLI:   python backtest/experiments/smoke_test.py --config /abs/path.yaml
            # - ENV:   SMOKE_TEST_CONFIG=/abs/path.yaml python backtest/experiments/smoke_test.py
            override = os.environ.get("SMOKE_TEST_CONFIG")
            config_path = Path(override) if override else (Path(__file__).parent.parent / 'configs' / 'smoke_test.yaml')
            config = load_config(str(config_path))
            print(f"[OK] Loaded configuration from {config_path}")
            print(f"   Symbols: {config.get('symbols', [])}")
            print(f"   Period: {config.get('start_date')} → {config.get('end_date')}")
        except Exception as e:
            print(f"[WARN] Could not load smoke_test.yaml: {e}")
            print(f"   Using default configuration")
            config = {
                'experiment_name': 'Smoke_Test_Default',
                'symbols': ['AAPL'],
                'start_date': '2024-01-02',
                'end_date': '2024-01-02'
            }

    experiment = SmokeTest(config)
    result = await experiment.run()

    # Print summary
    experiment.print_summary(result)

    # Save results
    experiment.save_results(result)

    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the backtest smoke test experiment.")
    parser.add_argument(
        "--config",
        dest="config_path",
        default=None,
        help="Path to YAML config (supports canonical papertest-suite schema). Overrides SMOKE_TEST_CONFIG.",
    )
    parser.add_argument(
        "--base-config",
        dest="base_config_path",
        default=None,
        help="Optional base YAML config to merge first (papertest schema only).",
    )
    args = parser.parse_args()

    # Run smoke test directly
    if args.config_path:
        # Keep all existing behavior in run_smoke_test (including conversion adapters) by
        # simply setting the existing override pathway.
        os.environ["SMOKE_TEST_CONFIG"] = args.config_path
    if args.base_config_path:
        # Backwards compatible extension point: config_loader supports base merges via API.
        # We intentionally do not add new global env vars here; keep CLI simple.
        from backtest.utils.config_loader import load_config
        from pathlib import Path
        cfg_path = Path(os.environ.get("SMOKE_TEST_CONFIG") or (Path(__file__).parent.parent / 'configs' / 'smoke_test.yaml'))
        cfg = load_config(str(cfg_path), base_config_path=args.base_config_path)
        result = asyncio.run(run_smoke_test(cfg))
    else:
        result = asyncio.run(run_smoke_test())
    exit(0 if result.success else 1)

