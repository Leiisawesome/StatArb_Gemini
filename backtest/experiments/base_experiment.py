"""
Base Experiment Framework
=========================

Abstract base class for all backtest experiments.
Enforces consistent interface and zero re-implementation principle.

Author: StatArb_Gemini Core Engine
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Type
from datetime import datetime
import asyncio
import json
import logging
import sys
from pathlib import Path

from core_engine.config import BacktestConfig
from backtest.utils.paths import backtest_results_dir
from backtest.utils import trade_timestamp_key

logger = logging.getLogger(__name__)

@dataclass
class ExperimentResult:
    """Structured experiment result"""

    # Experiment metadata
    experiment_name: str
    experiment_type: str
    run_timestamp: datetime
    duration_seconds: float

    # Engine results (pass-through from InstitutionalBacktestEngine)
    engine_results: Dict[str, Any]

    # Performance summary (extracted from engine_results)
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    total_trades: int
    win_rate: float

    # Additional metrics (experiment-specific)
    custom_metrics: Dict[str, Any] = field(default_factory=dict)

    # Status
    success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'experiment_name': self.experiment_name,
            'experiment_type': self.experiment_type,
            'run_timestamp': self.run_timestamp.isoformat(),
            'duration_seconds': self.duration_seconds,
            'performance': {
                'total_return_pct': self.total_return_pct,
                'sharpe_ratio': self.sharpe_ratio,
                'max_drawdown_pct': self.max_drawdown_pct,
                'total_trades': self.total_trades,
                'win_rate': self.win_rate,
            },
            'custom_metrics': self.custom_metrics,
            'engine_results': self.engine_results,
            'success': self.success,
            'error_message': self.error_message,
        }

class BaseExperiment(ABC):
    """
    Abstract base for all backtest experiments.

    Enforces:
    - Consistent interface
    - Zero re-implementation (use engine as black box)
    - Structured results
    - Config-driven execution
    """

    def __init__(self, config: Dict[str, Any], output_dir: Optional[str] = None):
        """
        Initialize experiment.

        Args:
            config: Experiment configuration (loaded from YAML)
            output_dir: Directory for results output
        """
        self.config = config
        # Canonicalize output location to a single backtest/results/ directory
        # regardless of current working directory.
        self.output_dir = Path(output_dir) if output_dir else backtest_results_dir()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def run(self) -> ExperimentResult:
        """
        Run experiment.

        MUST:
        - Use InstitutionalBacktestEngine (import from backtest.engine)
        - Not re-implement any engine logic
        - Return ExperimentResult

        Returns:
            ExperimentResult with structured results
        """

    @abstractmethod
    def get_description(self) -> str:
        """
        Get one-line experiment description.

        Returns:
            Human-readable description
        """

    def _create_backtest_config(self, source_config: Optional[Dict[str, Any]] = None) -> BacktestConfig:
        """
        Create BacktestConfig from flat YAML configuration dict.

        This is the canonical config builder used by all experiments.
        Override only if you need fundamentally different logic (e.g. parameter sweep).

        Args:
            source_config: Optional config dict override. Defaults to self.config.

        Returns:
            BacktestConfig ready for InstitutionalBacktestEngine
        """
        config_source = source_config or self.config

        config_dict = {
            'backtest_name': config_source.get('experiment_name', 'Experiment'),
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
            'min_confidence_threshold': config_source.get('min_confidence_threshold', 0.60),
            'enable_multi_strategy_coordination': config_source.get('enable_multi_strategy_coordination', True),
            'enable_signal_aggregation': config_source.get('enable_signal_aggregation', True),
            'enable_conflict_resolution': config_source.get('enable_conflict_resolution', True),
            'enable_dynamic_weighting': config_source.get('enable_dynamic_weighting', True),
            'output_directory': str(backtest_results_dir()),
        }

        # Regime risk multipliers
        if 'regime_risk_multipliers' in config_source:
            config_dict['regime_risk_multipliers'] = config_source['regime_risk_multipliers']
        else:
            config_dict['regime_risk_multipliers'] = {
                'low_volatility': 1.0,
                'normal_volatility': 1.0,
                'high_volatility': 0.7,
            }

        # Strategies (prefer list, support singular 'strategy' key)
        if 'strategies' in config_source:
            config_dict['strategies'] = config_source['strategies']
        elif 'strategy' in config_source:
            config_dict['strategies'] = [config_source['strategy']]
        else:
            config_dict['strategies'] = [{
                'type': 'mean_reversion',
                'name': 'MR_Simple',
                'allocation_pct': 1.0,
                'parameters': {
                    'lookback': 20,
                    'z_entry': 2.0,
                    'z_exit': 0.5,
                },
            }]

        backtest_config = BacktestConfig(**config_dict)
        is_valid, errors = backtest_config.validate()
        if not is_valid:
            error_message = "; ".join(errors)
            raise ValueError(
                f"Invalid BacktestConfig generated by {self.__class__.__name__}: {error_message}"
            )
        return backtest_config

    def print_summary(self, result: ExperimentResult):
        """
        Print concise run summary to console.

        Args:
            result: Experiment result to summarize
        """
        print("\n" + "="*80)
        print(f"[SUMMARY] EXPERIMENT SUMMARY: {result.experiment_name}")
        print("="*80)
        print(f"Type:           {result.experiment_type}")
        print(f"Status:         {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Duration:       {result.duration_seconds:.2f}s")
        print()

        if result.success:
            print("Performance Metrics:")
            print(f"  Total Return:    {result.total_return_pct:>8.2f}%")
            print(f"  Sharpe Ratio:    {result.sharpe_ratio:>8.2f}")
            print(f"  Max Drawdown:    {result.max_drawdown_pct:>8.2f}%")
            print(f"  Total Trades:    {result.total_trades:>8}")
            print(f"  Win Rate:        {result.win_rate:>8.1f}%")

            if result.custom_metrics:
                print()
                print("Custom Metrics:")
                for key, value in result.custom_metrics.items():
                    if isinstance(value, float):
                        print(f"  {key:<20} {value:>10.4f}")
                    elif isinstance(value, dict):
                        print(f"  {key:<20} {json.dumps(value, default=str)}")
                    else:
                        print(f"  {key:<20} {value!s:>10}")

            # Print trade list if available
            if result.engine_results and 'execution_history' in result.engine_results:
                trades = result.engine_results['execution_history']
                if trades:
                    print()
                    print("Trade List:")
                    print(f"  {'#':<3} {'Timestamp':<20} {'Strat':<8} {'Symbol':<8} {'Action':<6} {'Str':>4} {'Conf':>6} {'Qty':>8} {'Price':>10} {'P&L':>12}")
                    print("  " + "-"*92)

                    # Track inventory per strategy_run + symbol using FIFO lots with signed quantities.
                    #
                    # - Long lot:  +qty at entry_price
                    # - Short lot: -qty at entry_price
                    #
                    # Realized P&L is computed when trades CLOSE existing lots:
                    # - Sell closes long:  pnl += closed_qty * (sell_price - entry_price)
                    # - Buy  covers short: pnl += closed_qty * (entry_price - buy_price)
                    #
                    # Any residual quantity beyond closing becomes a new lot (opening/reversing).
                    positions: Dict[str, Dict[str, List[tuple[float, float]]]] = {}  # strategy_run -> symbol -> lots

                    for i, trade in enumerate(sorted(trades, key=trade_timestamp_key), 1):
                        strategy_run = trade.get('strategy_run', trade.get('strategy_id', 'default'))
                        if strategy_run not in positions:
                            positions[strategy_run] = {}

                        timestamp = str(trade.get('timestamp', 'N/A'))[:19]
                        symbol = trade.get('symbol', 'N/A')
                        action = trade.get('action', trade.get('side', 'N/A'))
                        quantity = trade.get('quantity', trade.get('qty', 0))
                        price = trade.get('price', trade.get('fill_price', 0))

                        # Extract signal strength and confidence
                        strength = trade.get('signal_strength', trade.get('strength', 0))
                        confidence = trade.get('confidence', 0)

                        # Format strength (0-1 scale)
                        if isinstance(strength, (int, float)) and strength > 0:
                            str_display = f"{strength:>4.2f}"
                        else:
                            str_display = "  - "

                        # Format confidence as percentage
                        if confidence > 0:
                            conf_display = f"{confidence*100:>5.1f}%" if confidence <= 1 else f"{confidence:>5.1f}%"
                        else:
                            conf_display = "    - "

                        # Realized P&L: Use engine's calculated P&L (Rule 4 SSOT)
                        # This ensures accuracy by including commissions, slippage, and correct cost basis.
                        pnl = trade.get('realized_pnl', 0.0)
                        pnl_str = " " * 12
                        
                        try:
                            pnl_val = float(pnl)
                            if abs(pnl_val) > 1e-6:
                                pnl_str = f"${pnl_val:>+11.2f}"
                        except (ValueError, TypeError):
                            pass

                        def _strategy_label(raw: str) -> str:
                            low = str(raw).lower()
                            if "mom" in low:
                                return "MOM"
                            if "mr" in low or "mean_reversion" in low:
                                return "MR"
                            if "eod" in low:
                                return "EOD"
                            if low == "default":
                                return "DEF"
                            return str(raw)[:8]

                        strat_label = _strategy_label(strategy_run)
                        print(f"  {i:<3} {timestamp:<20} {strat_label:<8} {symbol:<8} {action:<6} {str_display} {conf_display} {quantity:>8.2f} ${price:>9.2f} {pnl_str}")
        else:
            print(f"[ERROR] Error: {result.error_message}")

        print("="*80)

    # ------------------------------------------------------------------
    # Convenience entry point for experiment scripts
    # ------------------------------------------------------------------

    @classmethod
    def main(cls, default_config_path: str, **kwargs):
        """
        Standard __main__ entry point for any experiment subclass.

        Usage in an experiment file::

            if __name__ == "__main__":
                MyExperiment.main("backtest/configs/my_experiment.yaml")

        This replaces the duplicated async-def-run_example boilerplate that
        was copy-pasted across every experiment script.

        Args:
            default_config_path: Path to the default YAML config file.
            **kwargs: Extra keyword arguments forwarded to the constructor.
        """
        import asyncio
        from backtest.utils.config_loader import load_config

        config = load_config(default_config_path)
        experiment = cls(config, **kwargs)

        async def _run():
            result = await experiment.run()
            experiment.print_summary(result)
            experiment.save_results(result)
            return result

        result = asyncio.run(_run())
        raise SystemExit(0 if result.success else 1)

    def save_results(self, result: ExperimentResult):
        """
        Write structured results to disk.

        Saves:
        - JSON file with full results
        - CSV file with key metrics (if applicable)

        Args:
            result: Experiment result to save
        """
        timestamp = result.run_timestamp.strftime("%Y%m%d_%H%M%S")
        experiment_slug = result.experiment_name.replace(" ", "_").lower()

        # Save JSON
        json_path = self.output_dir / f"{experiment_slug}_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump(result.to_dict(), f, indent=2, default=str)

        self.logger.info(f"Results saved to: {json_path}")

        # Save summary CSV (for easy comparison across runs)
        csv_path = self.output_dir / "experiment_summary.csv"
        self._append_to_summary_csv(result, csv_path)

    def _append_to_summary_csv(self, result: ExperimentResult, csv_path: Path):
        """Append result to summary CSV"""
        import csv

        # Check if file exists to determine if we need header
        file_exists = csv_path.exists()

        with open(csv_path, 'a', newline='') as f:
            writer = csv.writer(f)

            # Write header if new file
            if not file_exists:
                writer.writerow([
                    'timestamp', 'experiment_name', 'experiment_type',
                    'total_return_pct', 'sharpe_ratio', 'max_drawdown_pct',
                    'total_trades', 'win_rate', 'duration_seconds', 'success'
                ])

            # Write data row
            writer.writerow([
                result.run_timestamp.isoformat(),
                result.experiment_name,
                result.experiment_type,
                result.total_return_pct,
                result.sharpe_ratio,
                result.max_drawdown_pct,
                result.total_trades,
                result.win_rate,
                result.duration_seconds,
                result.success
            ])

    def _extract_performance_metrics(self, engine_results: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract standard performance metrics from engine results.

        Args:
            engine_results: Raw results from InstitutionalBacktestEngine

        Returns:
            Dict with standard metrics
        """
        # Extract from engine results structure
        # Try 'performance' nested dict first, then 'summary', then fall back to top-level keys
        # Note: Use 'or {}' to handle None values (get() returns None if key exists with None value)
        performance = engine_results.get('performance', {}) or {}
        summary = engine_results.get('summary', {}) or {}

        # H2 fix: Use explicit `is not None` checks instead of `or`-chains
        # to avoid treating 0.0 (a valid metric value) as falsy/missing.

        def _first_not_none(*values):
            """Return the first value that is not None, or 0.0 as fallback."""
            for v in values:
                if v is not None:
                    return v
            return 0.0

        # Handle total_trades - check all locations
        total_trades = _first_not_none(
            performance.get('total_trades'),
            summary.get('total_trades'),
            engine_results.get('total_trades', 0),
        )

        # Handle total_return - check summary first (it stores as decimal, convert to %)
        # summary['total_return'] is 0.00597 meaning 0.597%
        perf_return = performance.get('total_return_pct')
        summary_return = summary.get('total_return')
        if perf_return is not None:
            total_return_pct = perf_return
        elif summary_return is not None:
            total_return_pct = summary_return * 100  # Convert decimal to percentage
        else:
            total_return_pct = engine_results.get('total_return_pct', 0.0)

        # Handle sharpe_ratio - check summary first
        sharpe_ratio = _first_not_none(
            performance.get('sharpe_ratio'),
            summary.get('sharpe_ratio'),
            engine_results.get('sharpe_ratio', 0.0),
        )

        # Handle max_drawdown_pct - check summary first (stored as decimal, convert to %)
        perf_dd = performance.get('max_drawdown_pct')
        summary_dd = summary.get('max_drawdown_pct')
        if perf_dd is not None:
            max_drawdown_pct = perf_dd
        elif summary_dd is not None:
            max_drawdown_pct = summary_dd * 100  # Convert decimal to percentage
        else:
            max_drawdown_pct = engine_results.get('max_drawdown_pct', 0.0)

        # Handle win_rate - check summary first (stored as decimal, convert to %)
        win_rate_decimal = _first_not_none(
            performance.get('win_rate'),
            summary.get('win_rate'),
            engine_results.get('win_rate', 0.0),
        )
        win_rate = win_rate_decimal * 100 if win_rate_decimal <= 1.0 else win_rate_decimal

        return {
            'total_return_pct': total_return_pct,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown_pct': max_drawdown_pct,
            'total_trades': total_trades,
            'win_rate': win_rate,
        }

