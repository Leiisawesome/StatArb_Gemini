"""
Papertest Experiment Framework
==============================

Mirrors backtest/experiments/base_experiment.py:
- Orchestrate a papertest engine as a black box
- Config-driven execution
- Structured results and persistence
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class PapertestResult:
    # Metadata
    experiment_name: str
    experiment_type: str
    run_timestamp: datetime
    duration_seconds: float

    # Engine stats / outputs (pass-through)
    engine_stats: Dict[str, Any] = field(default_factory=dict)
    replay_stats: Dict[str, Any] = field(default_factory=dict)
    risk_stats: Dict[str, Any] = field(default_factory=dict)
    execution_stats: Dict[str, Any] = field(default_factory=dict)

    # High-level performance (best-effort; depends on broker / risk book integration)
    total_pnl: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    max_drawdown: float = 0.0

    # Status
    success: bool = True
    error_message: Optional[str] = None

    # Experiment-specific
    custom_metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_name": self.experiment_name,
            "experiment_type": self.experiment_type,
            "run_timestamp": self.run_timestamp.isoformat(),
            "duration_seconds": self.duration_seconds,
            "engine_stats": self.engine_stats,
            "replay_stats": self.replay_stats,
            "risk_stats": self.risk_stats,
            "execution_stats": self.execution_stats,
            "performance": {
                "total_pnl": self.total_pnl,
                "realized_pnl": self.realized_pnl,
                "unrealized_pnl": self.unrealized_pnl,
                "max_drawdown": self.max_drawdown,
            },
            "custom_metrics": self.custom_metrics,
            "success": self.success,
            "error_message": self.error_message,
        }


class BasePapertestExperiment(ABC):
    def __init__(self, config: Dict[str, Any], output_dir: str = "papertest/results"):
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def run(self) -> PapertestResult: ...

    @abstractmethod
    def get_description(self) -> str: ...

    def print_summary(self, result: PapertestResult) -> None:
        print("\n" + "=" * 80)
        print(f"📎 PAPERTEST SUMMARY: {result.experiment_name}")
        print("=" * 80)
        print(f"Type:           {result.experiment_type}")
        print(f"Status:         {'✅ SUCCESS' if result.success else '❌ FAILED'}")
        print(f"Duration:       {result.duration_seconds:.2f}s")
        print()
        if result.success:
            perf = result.to_dict().get("performance", {})
            print("Performance (best-effort):")
            print(f"  Total PnL:      {perf.get('total_pnl', 0.0):>12.2f}")
            print(f"  Realized PnL:   {perf.get('realized_pnl', 0.0):>12.2f}")
            print(f"  Unrealized PnL: {perf.get('unrealized_pnl', 0.0):>12.2f}")
            print(f"  Max Drawdown:   {perf.get('max_drawdown', 0.0):>12.2f}")
            if result.custom_metrics:
                print()
                print("Custom Metrics:")
                for k, v in result.custom_metrics.items():
                    print(f"  {k:<24} {v}")
        else:
            print(f"❌ Error: {result.error_message}")
        print("=" * 80)

    def print_summary_backtest_style(self, result: PapertestResult) -> None:
        """
        Print the same console output layout as backtest/experiments/base_experiment.py::print_summary.

        This is used by the papertest smoke test for side-by-side parity diffs.
        """
        # region agent log
        try:
            import json as _json
            _payload = {
                "sessionId": "debug-session",
                "runId": "papertest_smoke_layout",
                "hypothesisId": "H2",
                "location": "papertest/experiments/base_experiment.py:print_summary_backtest_style:entry",
                "message": "papertest summary rendering entry",
                "data": {
                    "experiment_name": result.experiment_name,
                    "experiment_type": result.experiment_type,
                    "success": result.success,
                    "has_engine_execution_history": bool((result.engine_stats or {}).get("execution_history")),
                    "has_exec_stats_execution_history": bool((result.execution_stats or {}).get("execution_history")),
                },
                "timestamp": int(__import__("time").time() * 1000),
            }
            with open("/Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini/.cursor/debug.log", "a") as _f:
                _f.write(_json.dumps(_payload) + "\n")
        except Exception:
            pass
        # endregion agent log

        print("\n" + "=" * 80)
        print(f"📊 EXPERIMENT SUMMARY: {result.experiment_name}")
        print("=" * 80)
        print(f"Type:           {result.experiment_type}")
        print(f"Status:         {'✅ SUCCESS' if result.success else '❌ FAILED'}")
        print(f"Duration:       {result.duration_seconds:.2f}s")
        print()

        if not result.success:
            print(f"❌ Error: {result.error_message}")
            print("=" * 80)
            return

        # Best-effort "backtest-like" performance metrics from paper broker account info.
        acct = (result.execution_stats or {}).get("account_info") or {}
        try:
            initial_cash = float(((self.config.get("papertest") or {}).get("execution") or {}).get("initial_cash", 100_000.0))
        except Exception:
            initial_cash = 100_000.0
        final_equity = float(acct.get("equity") or acct.get("portfolio_value") or 0.0)
        total_return_pct = ((final_equity / initial_cash) - 1.0) * 100.0 if initial_cash and final_equity else 0.0

        # Trades (fills) normalized to backtest execution_history shape.
        trades = (
            (result.engine_stats or {}).get("execution_history")
            or (result.execution_stats or {}).get("execution_history")
            or []
        )
        total_trades = len(trades)

        # Compute sharpe + max drawdown from a mark-to-market equity curve derived from the EventJournal
        sharpe_ratio = 0.0
        max_drawdown_pct = 0.0
        try:
            journal_dir = str(((self.config.get("papertest") or {}).get("session") or {}).get("journal_dir", "papertest/results/journals"))
            session_id = str((result.engine_stats or {}).get("session_id") or "")
            if session_id:
                eq = self._compute_equity_curve_from_journal(
                    journal_dir=journal_dir,
                    session_id=session_id,
                    initial_cash=initial_cash,
                )
                sharpe_ratio = float(eq.get("sharpe_ratio", 0.0) or 0.0)
                max_drawdown_pct = float(eq.get("max_drawdown_pct", 0.0) or 0.0)
        except Exception:
            sharpe_ratio = 0.0
            max_drawdown_pct = 0.0

        # Compute FIFO win-rate based on sell trade P&L (same convention as backtest BaseExperiment summary table).
        win_rate = 0.0
        try:
            positions: Dict[str, list] = {}
            wins = 0
            sells = 0
            for tr in trades:
                symbol = tr.get("symbol") or "N/A"
                action = (tr.get("action") or tr.get("side") or "").lower()
                quantity = float(tr.get("quantity") or tr.get("qty") or 0.0)
                price = float(tr.get("price") or tr.get("fill_price") or 0.0)
                if symbol not in positions:
                    positions[symbol] = []
                if action == "buy":
                    positions[symbol].append((quantity, price))
                elif action == "sell":
                    sells += 1
                    qty_to_sell = quantity
                    pnl = 0.0
                    while qty_to_sell > 0 and positions[symbol]:
                        entry_qty, entry_price = positions[symbol][0]
                        sold_qty = min(qty_to_sell, entry_qty)
                        pnl += sold_qty * (price - entry_price)
                        qty_to_sell -= sold_qty
                        if sold_qty >= entry_qty:
                            positions[symbol].pop(0)
                        else:
                            positions[symbol][0] = (entry_qty - sold_qty, entry_price)
                    if pnl > 0:
                        wins += 1
            win_rate = (wins / sells * 100.0) if sells else 0.0
        except Exception:
            win_rate = 0.0

        # region agent log
        try:
            import json as _json
            _payload = {
                "sessionId": "debug-session",
                "runId": "papertest_smoke_layout",
                "hypothesisId": "H3",
                "location": "papertest/experiments/base_experiment.py:print_summary_backtest_style:metrics",
                "message": "papertest computed backtest-style metrics",
                "data": {
                    "initial_cash": initial_cash,
                    "final_equity": final_equity,
                    "total_return_pct": total_return_pct,
                    "sharpe_ratio": sharpe_ratio,
                    "max_drawdown_pct": max_drawdown_pct,
                    "total_trades": total_trades,
                    "win_rate": win_rate,
                },
                "timestamp": int(__import__("time").time() * 1000),
            }
            with open("/Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini/.cursor/debug.log", "a") as _f:
                _f.write(_json.dumps(_payload) + "\n")
        except Exception:
            pass
        # endregion agent log

        print("Performance Metrics:")
        print(f"  Total Return:    {total_return_pct:>8.2f}%")
        print(f"  Sharpe Ratio:    {sharpe_ratio:>8.2f}")
        print(f"  Max Drawdown:    {max_drawdown_pct:>8.2f}%")
        print(f"  Total Trades:    {total_trades:>8}")
        print(f"  Win Rate:        {win_rate:>8.1f}%")

        # Custom metrics: align keys used by backtest smoke_test where possible
        custom = dict(result.custom_metrics or {})
        try:
            if (result.engine_stats or {}).get("bars_processed") is not None:
                custom.setdefault("bars_processed", (result.engine_stats or {}).get("bars_processed"))
        except Exception:
            pass

        if custom:
            print()
            print("Custom Metrics:")
            for key, value in custom.items():
                if isinstance(value, float):
                    print(f"  {key:<20} {value:>10.4f}")
                else:
                    print(f"  {key:<20} {str(value):>10}")

        # Print trade list (same layout as backtest BaseExperiment)
        if trades:
            print()
            print("Trade List:")
            print(f"  {'#':<3} {'Timestamp':<20} {'Symbol':<8} {'Action':<6} {'Str':>4} {'Conf':>6} {'Qty':>8} {'Price':>10} {'P&L':>12}")
            print("  " + "-" * 90)

            positions: Dict[str, list] = {}
            for i, trade in enumerate(trades, 1):
                timestamp = str(trade.get("timestamp", "N/A"))[:19]
                symbol = trade.get("symbol", "N/A") or "N/A"
                action = trade.get("action", trade.get("side", "N/A")) or "N/A"
                quantity = float(trade.get("quantity", trade.get("qty", 0.0)) or 0.0)
                price = float(trade.get("price", trade.get("fill_price", 0.0)) or 0.0)

                strength = trade.get("signal_strength", trade.get("strength", 0.0))
                confidence = trade.get("confidence", 0.0)

                if isinstance(strength, (int, float)) and strength > 0:
                    str_display = f"{float(strength):>4.2f}"
                else:
                    str_display = "  - "

                if confidence:
                    conf_display = f"{confidence*100:>5.1f}%" if confidence <= 1 else f"{confidence:>5.1f}%"
                else:
                    conf_display = "    - "

                pnl = 0.0
                pnl_str = ""
                if symbol not in positions:
                    positions[symbol] = []

                if str(action).lower() == "buy":
                    positions[symbol].append((quantity, price))
                elif str(action).lower() == "sell":
                    qty_to_sell = quantity
                    while qty_to_sell > 0 and positions[symbol]:
                        entry_qty, entry_price = positions[symbol][0]
                        sold_qty = min(qty_to_sell, entry_qty)
                        pnl += sold_qty * (price - entry_price)
                        qty_to_sell -= sold_qty
                        if sold_qty >= entry_qty:
                            positions[symbol].pop(0)
                        else:
                            positions[symbol][0] = (entry_qty - sold_qty, entry_price)
                    pnl_str = f"${pnl:>+11.2f}"

                if not pnl_str:
                    pnl_str = " " * 12

                print(
                    f"  {i:<3} {timestamp:<20} {symbol:<8} {action:<6} {str_display} {conf_display} {quantity:>8.2f} ${price:>9.2f} {pnl_str}"
                )

        print("=" * 80)

    def _compute_equity_curve_from_journal(
        self,
        journal_dir: str,
        session_id: str,
        initial_cash: float,
    ) -> Dict[str, Any]:
        """
        Best-effort equity curve, sharpe, and max drawdown from EventJournal.

        Method:
        - Apply FILL events to cash + positions
        - Mark-to-market positions on each BAR close
        - Compute per-bar returns -> sharpe (annualized)
        - Compute peak-to-trough -> max drawdown
        """
        from pathlib import Path
        import math

        from core_engine.system.event_journal import EventJournal

        path = Path(journal_dir) / f"{session_id}.jsonl"
        if not path.exists():
            gz = Path(journal_dir) / f"{session_id}.jsonl.gz"
            path = gz if gz.exists() else path

        cash = float(initial_cash or 0.0)
        positions: Dict[str, float] = {}
        last_price: Dict[str, float] = {}
        equity_series: list[float] = []

        # region agent log
        try:
            _payload = {
                "sessionId": "debug-session",
                "runId": "papertest_smoke_layout",
                "hypothesisId": "H4",
                "location": "papertest/experiments/base_experiment.py:_compute_equity_curve_from_journal:entry",
                "message": "computing equity curve from journal",
                "data": {"path": str(path), "exists": bool(path.exists()), "initial_cash": cash},
                "timestamp": int(__import__("time").time() * 1000),
            }
            with open("/Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini/.cursor/debug.log", "a") as _f:
                _f.write(json.dumps(_payload) + "\n")
        except Exception:
            pass
        # endregion agent log

        if not path.exists():
            return {"sharpe_ratio": 0.0, "max_drawdown_pct": 0.0, "equity_points": 0}

        events = EventJournal.read_journal(str(path))
        bars_seen = 0
        bars_used = 0
        first_bar_ts = None
        last_bar_ts = None
        for ev in events:
            try:
                evd = ev.to_dict() if hasattr(ev, "to_dict") else ev
                category = (evd.get("category") or "").upper()
                et = evd.get("event_type")
                symbol = evd.get("symbol")
                data = evd.get("data") or {}

                if category == "FILL" and et == "fill":
                    side = str(data.get("side") or "").lower()
                    qty = float(data.get("quantity") or 0.0)
                    px = float(data.get("price") or 0.0)
                    comm = float(data.get("commission") or 0.0)
                    if symbol:
                        positions.setdefault(symbol, 0.0)
                        if side == "buy":
                            positions[symbol] += qty
                            cash -= qty * px + comm
                        elif side == "sell":
                            positions[symbol] -= qty
                            cash += qty * px - comm

                if category == "MARKET_DATA" and et == "bar":
                    # Mark-to-market on bar close
                    bars_seen += 1

                    # Align with backtest smoke_test bar set: 1-min RTH only (09:30–15:59 America/New_York).
                    # Backtest uses ~390 bars per day; including the 16:00 bar (391) shifts Sharpe/DD.
                    try:
                        ts_raw = data.get("timestamp") or ""
                        ts_str = str(ts_raw).replace("T", " ")
                        # Example: "2024-12-20 09:30:00-05:00"
                        from datetime import datetime as _dt
                        bar_dt = _dt.fromisoformat(ts_str)
                        hhmm = bar_dt.strftime("%H:%M")
                        if hhmm < "09:30" or hhmm > "15:59":
                            continue
                        if first_bar_ts is None:
                            first_bar_ts = ts_str
                        last_bar_ts = ts_str
                    except Exception:
                        # If timestamp parsing fails, keep bar (best-effort)
                        pass

                    if symbol:
                        try:
                            last_price[symbol] = float((data.get("close") or data.get("vwap") or 0.0))
                        except Exception:
                            last_price[symbol] = last_price.get(symbol, 0.0)
                    equity = cash
                    for sym, q in positions.items():
                        equity += float(q) * float(last_price.get(sym, 0.0))
                    if equity > 0:
                        equity_series.append(float(equity))
                        bars_used += 1
            except Exception:
                continue

        if len(equity_series) < 2:
            return {"sharpe_ratio": 0.0, "max_drawdown_pct": 0.0, "equity_points": len(equity_series)}

        # Returns
        rets: list[float] = []
        for i in range(1, len(equity_series)):
            prev = equity_series[i - 1]
            cur = equity_series[i]
            if prev != 0:
                rets.append((cur - prev) / prev)

        # Max drawdown
        peak = equity_series[0]
        min_dd = 0.0
        for v in equity_series:
            if v > peak:
                peak = v
            if peak > 0:
                dd = (v / peak) - 1.0
                if dd < min_dd:
                    min_dd = dd
        max_drawdown_pct = abs(min_dd) * 100.0

        # Sharpe (match backtest/engine/institutional_backtest_engine.py logic)
        # - use population std (ddof=0)
        # - avoid full-year annualization for 1-day backtests (report raw_sharpe)
        mean_r = sum(rets) / len(rets) if rets else 0.0
        var = 0.0
        if rets:
            var = sum((r - mean_r) ** 2 for r in rets) / len(rets)  # ddof=0
        stdev = math.sqrt(var) if var > 0 else 0.0

        bars_per_day = 390  # assumes 1-minute bars (matches backtest engine)
        n_bars = len(rets)
        trading_days = max(1.0, (n_bars / bars_per_day) if bars_per_day > 0 else 1.0)

        sharpe = 0.0
        raw_sharpe = 0.0
        sharpe_mode = "std_zero"
        if stdev > 0:
            raw_sharpe = mean_r / stdev
            if trading_days <= 1:
                sharpe = raw_sharpe
                sharpe_mode = "raw_1day"
            elif trading_days <= 5:
                sharpe = raw_sharpe * math.sqrt(trading_days)
                sharpe_mode = "sqrt_days"
            else:
                sharpe = raw_sharpe * math.sqrt(252.0 * bars_per_day)
                sharpe_mode = "annualized"

        # region agent log
        try:
            _payload = {
                "sessionId": "debug-session",
                "runId": "papertest_sharpe_align",
                "hypothesisId": "H6",
                "location": "papertest/experiments/base_experiment.py:_compute_equity_curve_from_journal:exit",
                "message": "computed equity/sharpe/dd (backtest-aligned, RTH-filtered)",
                "data": {
                    "equity_points": len(equity_series),
                    "bars_seen": bars_seen,
                    "bars_used": bars_used,
                    "first_bar_ts": first_bar_ts,
                    "last_bar_ts": last_bar_ts,
                    "first_equity": equity_series[0],
                    "last_equity": equity_series[-1],
                    "rets_len": len(rets),
                    "mean_r": mean_r,
                    "stdev_r": stdev,
                    "bars_per_day": bars_per_day,
                    "trading_days": trading_days,
                    "raw_sharpe": raw_sharpe,
                    "sharpe_mode": sharpe_mode,
                    "sharpe": sharpe,
                    "max_drawdown_pct": max_drawdown_pct,
                },
                "timestamp": int(__import__("time").time() * 1000),
            }
            with open("/Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini/.cursor/debug.log", "a") as _f:
                _f.write(json.dumps(_payload) + "\n")
        except Exception:
            pass
        # endregion agent log

        return {"sharpe_ratio": sharpe, "max_drawdown_pct": max_drawdown_pct, "equity_points": len(equity_series)}

    def save_results(self, result: PapertestResult) -> None:
        ts = result.run_timestamp.strftime("%Y%m%d_%H%M%S")
        slug = result.experiment_name.replace(" ", "_").lower()
        json_path = self.output_dir / f"{slug}_{ts}.json"
        with open(json_path, "w") as f:
            json.dump(result.to_dict(), f, indent=2, default=str)
        self.logger.info(f"Results saved to: {json_path}")


