"""
Experiment 2: Baseline Backtest
================================

Full-period baseline backtest to establish performance benchmarks.

Purpose:
- Run strategy over extended period (weeks/months)
- Generate baseline performance metrics
- Identify profitable periods vs drawdown periods
- Validate strategy logic with real signal generation

Expected Duration: 2-5 minutes (depends on period length)

Author: StatArb_Gemini Core Engine
"""

import asyncio
from datetime import datetime
from typing import Dict, Any
import time

from backtest.experiments.base_experiment import BaseExperiment, ExperimentResult
from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine

class BaselineBacktest(BaseExperiment):
    """
    Baseline backtest experiment.

    Tests:
    - Full period backtest (configurable duration)
    - Complete strategy performance
    - Risk metrics calculation
    - Trade execution simulation
    """

    def get_description(self) -> str:
        return f"Baseline backtest: {self.config.get('symbols', ['N/A'])[0]}, {self.config.get('start_date')} to {self.config.get('end_date')}"

    async def run(self) -> ExperimentResult:
        """Run baseline backtest"""
        start_time = time.time()
        experiment_name = self.config.get('experiment_name', 'Baseline_Backtest')

        try:
            self.logger.info(f"🚀 Starting baseline backtest: {experiment_name}")

            # Create backtest config
            backtest_config = self._create_backtest_config()

            # Initialize engine
            self.logger.info("   Initializing InstitutionalBacktestEngine...")
            engine = InstitutionalBacktestEngine(backtest_config)
            await engine.initialize()

            # Run backtest
            self.logger.info("   Running full backtest...")
            engine_results = await engine.run_backtest()

            # Extract metrics
            duration = time.time() - start_time
            metrics = self._extract_performance_metrics(engine_results)

            # Extract additional custom metrics
            custom_metrics = {
                'bars_processed': engine_results.get('total_bars', 0),
                'bars_with_signals': engine_results.get('bars_with_signals', 0),
                'bars_with_trades': engine_results.get('bars_with_trades', 0),
                'signal_to_trade_ratio': (
                    engine_results.get('bars_with_trades', 0) /
                    max(1, engine_results.get('bars_with_signals', 0))
                ),
                'avg_trade_size': (
                    engine_results.get('total_trades', 0) /
                    max(1, engine_results.get('bars_with_trades', 0))
                ),
                'initialization_time_s': engine_results.get('initialization_time', 0.0),
                'execution_time_s': duration,
                'processing_speed_bars_per_sec': (
                    engine_results.get('total_bars', 0) / max(0.001, duration)
                ),
            }

            # Create result
            result = ExperimentResult(
                experiment_name=experiment_name,
                experiment_type="baseline_backtest",
                run_timestamp=datetime.now(),
                duration_seconds=duration,
                engine_results=engine_results,
                total_return_pct=metrics['total_return_pct'],
                sharpe_ratio=metrics['sharpe_ratio'],
                max_drawdown_pct=metrics['max_drawdown_pct'],
                total_trades=metrics['total_trades'],
                win_rate=metrics['win_rate'],
                custom_metrics=custom_metrics,
                success=True
            )

            # Shutdown engine to release resources (Rule 1 compliance)
            await engine.shutdown()

            self.logger.info(f"✅ Baseline backtest completed in {duration:.2f}s")
            return result

        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"❌ Baseline backtest failed: {e}", exc_info=True)

            return ExperimentResult(
                experiment_name=experiment_name,
                experiment_type="baseline_backtest",
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

# Standalone run function
async def run_baseline_backtest(config: Dict[str, Any] = None):
    """
    Run baseline backtest experiment.

    Args:
        config: Optional config dict. If None, loads from baseline_backtest.yaml
    """
    if config is None:
        # Load from YAML configuration file
        from backtest.utils.config_loader import load_config
        from pathlib import Path

        try:
            # Get path to baseline_backtest.yaml
            config_path = Path(__file__).parent.parent / 'configs' / 'baseline_backtest.yaml'
            config = load_config(str(config_path))
            print(f"✅ Loaded configuration from baseline_backtest.yaml")
            print(f"   Experiment: {config.get('experiment_name')}")
            print(f"   Symbols: {config.get('symbols', [])}")
            print(f"   Period: {config.get('start_date')} → {config.get('end_date')}")
        except Exception as e:
            print(f"⚠️  Could not load baseline_backtest.yaml: {e}")
            print(f"   Using default configuration")
        config = {
            'experiment_name': 'Baseline_Backtest_Default',
            'symbols': ['AAPL'],
            'start_date': '2024-01-01',
            'end_date': '2024-01-31',  # 1 month for reasonable runtime
            'interval': '1min'
        }

    experiment = BaselineBacktest(config)
    result = await experiment.run()

    # Print summary
    experiment.print_summary(result)

    # Save results
    experiment.save_results(result)

    return result

if __name__ == "__main__":
    # Run baseline backtest directly
    result = asyncio.run(run_baseline_backtest())
    exit(0 if result.success else 1)

