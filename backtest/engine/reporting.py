"""
Reporting Mixin for InstitutionalBacktestEngine
=================================================

Contains performance report generation and summary methods.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ReportingMixin:
    """Performance reporting methods for InstitutionalBacktestEngine."""

    # ============================================================
    # SPRINT 0.3: REJECTION STATISTICS REPORTING
    # ============================================================

    # ============================================================
    # REPORT GENERATION METHODS
    # ============================================================

    def generate_performance_report(self,
                                   format: str = 'console',
                                   export: bool = False) -> str:
        """
        Generate comprehensive performance report from backtest results

        This method aggregates results from:
        - execution_history: Executed trades with costs
        - position_tracker: Portfolio positions and P&L
        - analytics_manager: Performance metrics

        Args:
            format: Report format ('console', 'json', 'csv', 'markdown')
            export: Whether to export report to file

        Returns:
            Formatted report string
        """
        logger.info("\n" + "=" * 80)
        logger.info("📊 GENERATING BACKTEST PERFORMANCE REPORT")
        logger.info("=" * 80)

        try:
            # Check if we have execution history
            if not self.execution_history:
                logger.warning("⚠️ No execution history available")
                return "No trades executed - cannot generate report"

            # Get basic performance data
            total_trades = len(self.execution_history)
            total_bars = len(self.historical_data) if self.historical_data is not None else 0

            # Get initial and final capital
            initial_capital = getattr(self.config, 'initial_capital', 1_000_000.0)

            # Use RiskManager for final capital (Rule 4)
            final_capital = initial_capital
            if self.risk_manager and hasattr(self.risk_manager, 'portfolio_value'):
                final_capital = self.risk_manager.portfolio_value

            # Calculate basic metrics
            total_return = (final_capital - initial_capital) / initial_capital if initial_capital > 0 else 0

            # Generate basic report
            report_lines = [
                "# Backtest Performance Report",
                f"## Backtest: {self.backtest_name}",
                f"## Period: {self.config.start_date} to {self.config.end_date}",
                f"## Symbol: {', '.join(self.config.symbols) if hasattr(self.config, 'symbols') else 'N/A'}",
                "",
                "## Summary Statistics",
                f"- **Total Bars Processed**: {total_bars}",
                f"- **Total Trades**: {total_trades}",
                f"- **Initial Capital**: ${initial_capital:,.2f}",
                f"- **Final Capital**: ${final_capital:,.2f}",
                f"- **Total Return**: {total_return:.2%}",
                "",
                "## Trade Details"
            ]

            # Add trade details if available
            if self.execution_history:
                report_lines.append("| Timestamp | Symbol | Side | Quantity | Price | Value |")
                report_lines.append("|-----------|--------|------|----------|-------|-------|")

                for trade in self.execution_history[:10]:  # Show first 10 trades
                    timestamp = trade.get('timestamp', 'N/A')
                    symbol = trade.get('symbol', 'N/A')
                    side = trade.get('side', 'N/A')
                    quantity = trade.get('quantity', 0)
                    # Check for 'fill_price' (standard) or 'price' (legacy)
                    price = trade.get('fill_price', trade.get('price', 0))
                    value = quantity * price
                    report_lines.append(f"| {timestamp} | {symbol} | {side} | {quantity} | ${price:.2f} | ${value:.2f} |")

                if len(self.execution_history) > 10:
                    report_lines.append(f"\n*... and {len(self.execution_history) - 10} more trades*")

            report = "\n".join(report_lines)

            # Export if requested
            if export:
                from pathlib import Path
                from backtest.utils.paths import backtest_results_dir
                output_dir = Path(self.config.output_directory) if hasattr(self.config, 'output_directory') else backtest_results_dir()
                output_dir.mkdir(parents=True, exist_ok=True)

                if format.lower() == 'json':
                    import json
                    json_data = {
                        "backtest_name": self.backtest_name,
                        "total_bars": total_bars,
                        "total_trades": total_trades,
                        "initial_capital": initial_capital,
                        "final_capital": final_capital,
                        "total_return": total_return,
                        "trades": self.execution_history
                    }
                    filepath = output_dir / "backtest_report.json"
                    with open(filepath, 'w') as f:
                        json.dump(json_data, f, indent=2, default=str)
                else:
                    # Default to markdown
                    filepath = output_dir / "backtest_report.md"
                    with open(filepath, 'w') as f:
                        f.write(report)

                logger.info(f"✅ Report exported to: {filepath}")

            return report

        except Exception as e:
            logger.error(f"❌ Failed to generate performance report: {e}", exc_info=True)
            return f"Error generating report: {str(e)}"

    def get_performance_summary(self) -> Optional[Any]:
        """
        Get performance summary object (for programmatic access)

        Returns:
            Dict with basic performance metrics or None if not available
        """
        try:
            if not self.execution_history:
                return None

            # Get basic performance data
            total_executions = len(self.execution_history)
            total_bars = len(self.historical_data) if self.historical_data is not None else 0

            # Get initial and final capital
            initial_capital = getattr(self.config, 'initial_capital', 1_000_000.0)

            # Use RiskManager for final capital (Rule 4)
            final_capital = initial_capital
            if self.risk_manager and hasattr(self.risk_manager, 'portfolio_value'):
                final_capital = self.risk_manager.portfolio_value

            # Calculate basic metrics
            total_return = (final_capital - initial_capital) / initial_capital if initial_capital > 0 else 0

            # Win rate: only count trades with realized P&L (closed positions)
            winning_trades = 0
            losing_trades = 0
            for trade in self.execution_history:
                pnl = trade.get('realized_pnl', 0.0) or trade.get('pnl', 0.0)
                if pnl > 0:
                    winning_trades += 1
                elif pnl < 0:
                    losing_trades += 1

            # Win rate = wins / (wins + losses), not wins / total_trades
            # This excludes open positions (entries without exits)
            closed_trades = winning_trades + losing_trades
            win_rate = winning_trades / closed_trades if closed_trades > 0 else 0.0

            # Calculate max drawdown from position history
            max_drawdown = 0.0
            max_drawdown_pct = 0.0
            # Filter position_history to exclude warmup period
            _filtered_history = self.position_history
            if _filtered_history and hasattr(self, 'simulation_start_dt'):
                _sim_start = pd.Timestamp(self.simulation_start_dt)
                if _sim_start.tzinfo is not None:
                    _sim_start = _sim_start.tz_localize(None)
                _filtered = []
                for snap in self.position_history:
                    snap_ts = pd.Timestamp(snap.get('timestamp', datetime.min))
                    if snap_ts.tzinfo is not None:
                        snap_ts = snap_ts.tz_localize(None)
                    if snap_ts >= _sim_start:
                        _filtered.append(snap)
                _filtered_history = _filtered if _filtered else self.position_history

            # Track max drawdown duration (bars in drawdown)
            max_dd_duration_bars = 0
            if _filtered_history:
                equity_values = [snap.get('equity', initial_capital) for snap in _filtered_history]
                if equity_values:
                    peak = equity_values[0]
                    current_dd_start = 0  # bar index where current drawdown began
                    in_drawdown = False
                    for i, equity in enumerate(equity_values):
                        if equity > peak:
                            if in_drawdown:
                                dd_len = i - current_dd_start
                                max_dd_duration_bars = max(max_dd_duration_bars, dd_len)
                                in_drawdown = False
                            peak = equity
                        else:
                            if not in_drawdown and peak > 0:
                                dd_pct = (peak - equity) / peak
                                if dd_pct > self.EPSILON:
                                    in_drawdown = True
                                    current_dd_start = i
                        drawdown = (peak - equity) / peak if peak > 0 else 0
                        if drawdown > max_drawdown_pct:
                            max_drawdown_pct = drawdown
                            max_drawdown = peak - equity
                    # Close out any open drawdown at end
                    if in_drawdown:
                        dd_len = len(equity_values) - current_dd_start
                        max_dd_duration_bars = max(max_dd_duration_bars, dd_len)

            # Calculate Sharpe ratio from position history returns
            sharpe_ratio = 0.0
            if _filtered_history and len(_filtered_history) > 1:
                equity_values = [snap.get('equity', initial_capital) for snap in _filtered_history]
                if len(equity_values) > 1:
                    import numpy as np
                    # Calculate returns
                    returns = []
                    for i in range(1, len(equity_values)):
                        if equity_values[i-1] > 0:
                            ret = (equity_values[i] - equity_values[i-1]) / equity_values[i-1]
                            returns.append(ret)

                    if returns:
                        returns_arr = np.array(returns)
                        mean_return = np.mean(returns_arr)
                        std_return = np.std(returns_arr)

                        # Annualize Sharpe: SR_ann = (mean/std) * sqrt(N_bars_per_year)
                        # For short backtests the result is noisy, but at least it's on the
                        # same scale as longer backtests, enabling valid comparison.
                        if std_return > 0:
                            n_bars = len(returns)
                            # Derive bars_per_day from interval
                            _interval = getattr(self.config, 'interval', '1min')
                            _interval_lower = _interval.lower()
                            _interval_map = {
                                '1min': 390, '5min': 78, '15min': 26,
                                '30min': 13, '1h': 7, '1d': 1,
                            }
                            bars_per_day = _interval_map.get(_interval_lower, 390)
                            trading_days = max(1, n_bars / bars_per_day)

                            # Subtract risk-free rate per bar before computing Sharpe
                            rf_annual = getattr(self.config, 'risk_free_rate', 0.0)
                            bars_per_year = 252 * bars_per_day
                            rf_per_bar = rf_annual / bars_per_year if bars_per_year > 0 else 0.0
                            excess_returns = returns_arr - rf_per_bar
                            mean_excess = np.mean(excess_returns)
                            # Use ddof=1 (sample std) — unbiased estimator
                            std_excess = np.std(excess_returns, ddof=1)

                            if std_excess > 0:
                                raw_sharpe = mean_excess / std_excess
                                # Single annualization: sqrt(bars_per_year), always
                                annualization_factor = np.sqrt(bars_per_year)
                                sharpe_ratio = raw_sharpe * annualization_factor

            # AXIS1 FIX: Sanitize all computed metrics to prevent Inf/NaN
            # from propagating into reports, optimizers, or downstream analytics.
            import math as _math
            def _safe(v, default=0.0):
                return v if isinstance(v, (int, float)) and _math.isfinite(v) else default

            total_return = _safe(total_return)
            sharpe_ratio = _safe(sharpe_ratio)
            max_drawdown = _safe(max_drawdown)
            max_drawdown_pct = _safe(max_drawdown_pct)
            win_rate = _safe(win_rate)
            final_capital = _safe(final_capital, initial_capital)

            # Create summary dict
            summary = {
                "backtest_name": self.backtest_name,
                "total_bars_processed": total_bars,
                "total_trades": closed_trades,
                "total_executions": total_executions,
                "initial_capital": initial_capital,
                "final_capital": final_capital,
                "total_return": total_return,
                "sharpe_ratio": sharpe_ratio,
                "max_drawdown": max_drawdown,
                "max_drawdown_pct": max_drawdown_pct,
                "max_drawdown_duration_bars": max_dd_duration_bars,
                "win_rate": win_rate,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "execution_history": self.execution_history,
                "position_history": self.position_history
            }

            return summary

        except Exception as e:
            logger.error(f"❌ Failed to get performance summary: {e}")
            return None

