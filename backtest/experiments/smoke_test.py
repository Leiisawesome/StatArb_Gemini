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
from typing import Dict, Any, List
import time
import os

from backtest.experiments.base_experiment import BaseExperiment, ExperimentResult
from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine

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

            # --- Finalize pipeline tracer + automatic audit ---
            if self.config.get('enable_pipeline_trace', False):
                from core_engine.utils.pipeline_trace import get_tracer
                _tracer = get_tracer()
                if _tracer.enabled:
                    _tracer.print_funnel()
                    result.custom_metrics['trace_funnel'] = _tracer.get_funnel_summary()
                    result.custom_metrics['trace_stats'] = _tracer.stats

                    # --- Pipeline Audit: automatic plumbing verification ---
                    try:
                        from core_engine.utils.pipeline_auditor import PipelineAuditor
                        _initial_capital = float(self.config.get('initial_capital', 1_000_000))
                        _auditor = PipelineAuditor.from_tracer()
                        _audit_report = _auditor.run_all(initial_capital=_initial_capital)
                        _audit_report.print_summary()
                        result.custom_metrics['audit_passed'] = _audit_report.passed
                        result.custom_metrics['audit_errors'] = _audit_report.error_count
                        result.custom_metrics['audit_warnings'] = _audit_report.warning_count
                    except Exception as _audit_err:
                        self.logger.warning(f"Pipeline audit failed (non-fatal): {_audit_err}")
                        result.custom_metrics['audit_passed'] = None

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

    # _create_backtest_config inherited from BaseExperiment

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
        from backtest.utils.isolated_runner import RunAggregator

        external_configs = self.config.get('external_strategy_configs', []) or []
        if external_configs:
            return await self._run_external_config_backtests(experiment_name, external_configs)

        initial_capital = float(self.config.get('initial_capital', 1_000_000))
        agg = RunAggregator(initial_capital=initial_capital)

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
            alloc_weight = alloc_pct / total_alloc
            strategy_capital = initial_capital * alloc_weight

            run_config = dict(self.config)
            run_config['experiment_name'] = isolated_name
            run_config['strategies'] = [strategy]
            run_config['initial_capital'] = strategy_capital

            backtest_config = self._create_backtest_config(run_config)

            self.logger.info(f"   Isolated run: {strategy_name}")
            engine = InstitutionalBacktestEngine(backtest_config)
            try:
                await engine.initialize()
                engine_results = await engine.run_backtest()
            finally:
                await engine.shutdown()

            run_metrics = self._extract_performance_metrics(engine_results or {})
            exec_history = engine_results.get('execution_history', []) if engine_results else []

            agg.add_run(strategy_name, engine_results, run_metrics, alloc_weight, exec_history)

        return agg.build_combined(experiment_name, include_hypothesis_tests=True)

    async def _run_external_config_backtests(
        self,
        experiment_name: str,
        config_paths: List[str],
    ) -> Dict[str, Any]:
        """Run isolated backtests from explicit config paths and aggregate results."""
        from pathlib import Path
        from backtest.utils.config_loader import load_config
        from backtest.utils.isolated_runner import RunAggregator

        initial_capital = float(self.config.get('initial_capital', 1_000_000))
        agg = RunAggregator(initial_capital=initial_capital)

        # G7 FIX: Equal allocation (1/N) for external configs
        ext_alloc_weight = 1.0 / len(config_paths)

        for raw_path in config_paths:
            cfg_path = Path(raw_path).expanduser()
            self.logger.info(f"   External isolated run: {cfg_path}")
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
            strategy_name = run_summary.get('backtest_name', cfg_path.name)
            exec_history = engine_results.get('execution_history', []) if engine_results else []

            agg.add_run(strategy_name, engine_results, run_metrics, ext_alloc_weight, exec_history)

        return agg.build_combined(experiment_name, include_hypothesis_tests=False)

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

