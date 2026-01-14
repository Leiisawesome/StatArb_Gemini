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
from typing import Dict, Any
import time
import os

from backtest.experiments.base_experiment import BaseExperiment, ExperimentResult
from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine
from core_engine.config import BacktestConfig
from backtest.utils.paths import backtest_results_dir

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

        try:
            self.logger.info(f"🔧 Starting smoke test: {experiment_name}")

            # Create minimal backtest config
            backtest_config = self._create_backtest_config()

            # Initialize engine (ORCHESTRATION ONLY - no logic re-implementation)
            self.logger.info("   Initializing InstitutionalBacktestEngine...")
            engine = InstitutionalBacktestEngine(backtest_config)
            await engine.initialize()

            # Run backtest (black box)
            self.logger.info("   Running backtest...")
            engine_results = await engine.run_backtest()

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

            # Shutdown engine to release resources (Rule 1 compliance)
            await engine.shutdown()

            self.logger.info(f"✅ Smoke test completed in {duration:.2f}s")
            return result

        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"❌ Smoke test failed: {e}")

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

    def _create_backtest_config(self) -> BacktestConfig:
        """Create backtest config from YAML configuration"""
        # Build config from YAML (prefer YAML over defaults)
        config_dict = {
            'backtest_name': self.config.get('experiment_name', 'Smoke_Test'),
            'symbols': self.config.get('symbols', ['AAPL']),
            'interval': self.config.get('interval', '1min'),
            'start_date': self.config.get('start_date', '2024-01-02'),
            'end_date': self.config.get('end_date', '2024-01-02'),
            'warmup_bars': self.config.get('warmup_bars', None),
            'initial_capital': self.config.get('initial_capital', 100000),
            'allow_shorts': self.config.get('allow_shorts', False),
            'max_position_size': self.config.get('max_position_size', 0.10),
            'max_position_pct': self.config.get('max_position_pct', None),
            'max_concentration': self.config.get('max_concentration', 0.20),
            'min_signal_confidence': self.config.get('min_signal_confidence', 0.60),
            # v5.0: Strategy aggregator minimum confidence threshold
            'min_confidence_threshold': self.config.get('min_confidence_threshold', 0.60),
            # Canonicalize all backtest outputs under backtest/results/ regardless of CWD
            'output_directory': str(backtest_results_dir()),
        }

        # Add regime risk multipliers if provided
        if 'regime_risk_multipliers' in self.config:
            config_dict['regime_risk_multipliers'] = self.config['regime_risk_multipliers']
        else:
            config_dict['regime_risk_multipliers'] = {
                'low_volatility': 1.0,
                'normal_volatility': 1.0,
                'high_volatility': 0.7
            }

        # Add strategies from YAML if provided
        if 'strategies' in self.config:
            config_dict['strategies'] = self.config['strategies']
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
            print(f"✅ Loaded configuration from {config_path}")
            print(f"   Symbols: {config.get('symbols', [])}")
            print(f"   Period: {config.get('start_date')} → {config.get('end_date')}")
        except Exception as e:
            print(f"⚠️  Could not load smoke_test.yaml: {e}")
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

