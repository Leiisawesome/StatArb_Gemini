"""
Trace a single trade's quantity control points from backtest results.

Usage:
  python backtest/utils/trace_qty.py --result backtest/results/smoke_test_YYYYMMDD_HHMMSS.json --trade-index 1
  python backtest/utils/trace_qty.py --result ... --timestamp "2024-12-18 09:32:00-05:00"
  python backtest/utils/trace_qty.py --result ... --trade-index 1 --config core_engine/config/catalog/suites/smoke_test_mom.yaml
"""

import argparse
from datetime import datetime
from typing import Any, Dict, List, Optional
import json

from backtest.utils.config_loader import load_config


def _parse_ts(ts: Any) -> Any:
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            return ts
    return ts


def _load_execution_history(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    engine_results = result.get("engine_results", {}) or {}
    summary = engine_results.get("summary", {}) or {}
    if "execution_history" in summary:
        return summary["execution_history"] or []
    if "execution_history" in engine_results:
        return engine_results["execution_history"] or []
    return []


def _select_trade(trades: List[Dict[str, Any]], trade_index: Optional[int], timestamp: Optional[str]) -> Dict[str, Any]:
    if not trades:
        raise ValueError("No execution_history found in result")

    if timestamp:
        target = _parse_ts(timestamp)
        for trade in trades:
            if _parse_ts(trade.get("timestamp")) == target:
                return trade
        raise ValueError(f"No trade found with timestamp {timestamp}")

    if trade_index is None:
        trade_index = 1
    if trade_index < 1 or trade_index > len(trades):
        raise ValueError(f"trade-index out of range (1..{len(trades)})")
    return trades[trade_index - 1]


def _load_caps(config_path: Optional[str]) -> Dict[str, Any]:
    if not config_path:
        return {}
    cfg = load_config(config_path)
    base_position_pct = None
    strategy_max_position_size = None
    strategies = cfg.get("strategies") or []
    if strategies:
        params = (strategies[0] or {}).get("parameters", {}) or {}
        base_position_pct = params.get("base_position_pct")
        strategy_max_position_size = (strategies[0] or {}).get("max_position_size")
    return {
        "initial_capital": cfg.get("initial_capital"),
        "allow_shorts": cfg.get("allow_shorts"),
        "min_signal_confidence": cfg.get("min_signal_confidence"),
        "max_position_size": cfg.get("max_position_size"),
        "max_position_pct": cfg.get("max_position_pct"),
        "max_concentration": cfg.get("max_concentration"),
        "position_concentration_limit": cfg.get("position_concentration_limit"),
        "max_positions": cfg.get("max_positions"),
        "strategy.base_position_pct": base_position_pct,
        "strategy.max_position_size": strategy_max_position_size,
    }


def _print_trace(trade: Dict[str, Any], caps: Dict[str, Any]) -> None:
    decision_price = trade.get("decision_price") or trade.get("market_price") or trade.get("fill_price")
    requested_qty = trade.get("requested_quantity", trade.get("quantity"))
    final_qty = trade.get("quantity")
    qty_reduction = trade.get("quantity_reduction", 0)
    position_value = None
    if decision_price is not None and requested_qty is not None:
        try:
            position_value = float(decision_price) * float(requested_qty)
        except Exception:
            position_value = None

    target_weight = trade.get("target_weight")
    quantity_type = trade.get("quantity_type")
    target_quantity = trade.get("target_quantity")
    sizing_source = "unknown"
    if quantity_type == "PERCENTAGE" and target_weight:
        sizing_source = "signal.target_weight"
    elif target_quantity:
        sizing_source = "signal.target_quantity"
    else:
        sizing_source = "fallback.base_position_pct_or_max"

    rows = [
        ("signal.confidence", trade.get("confidence")),
        ("signal.strength", trade.get("signal_strength")),
        ("signal.timestamp", trade.get("signal_timestamp")),
        ("signal.bar_close", trade.get("signal_bar_close")),
        ("signal.target_weight", target_weight),
        ("signal.target_quantity", target_quantity),
        ("signal.quantity_type", quantity_type),
        ("sizing.source", sizing_source),
        ("requested_qty", requested_qty),
        ("decision_price", decision_price),
        ("requested_value", position_value),
        ("qty_reduction", qty_reduction),
        ("final_qty", final_qty),
        ("fill_price", trade.get("fill_price")),
        ("total_cost_bps", trade.get("total_cost_bps")),
        ("slippage_bps", trade.get("slippage_bps")),
        ("commission_bps", trade.get("commission_bps")),
        ("realized_pnl", trade.get("realized_pnl")),
        ("authorization_id", trade.get("authorization_id")),
    ]

    if caps:
        position_size_pct_used = None
        if sizing_source.startswith("fallback"):
            position_size_pct_used = caps.get("strategy.base_position_pct") or caps.get("strategy.max_position_size") or caps.get("max_position_size")
        rows.extend([
            ("cap.initial_capital", caps.get("initial_capital")),
            ("cap.allow_shorts", caps.get("allow_shorts")),
            ("cap.min_signal_confidence", caps.get("min_signal_confidence")),
            ("cap.max_position_size", caps.get("max_position_size")),
            ("cap.max_position_pct", caps.get("max_position_pct")),
            ("cap.max_concentration", caps.get("max_concentration") or caps.get("position_concentration_limit")),
            ("cap.max_positions", caps.get("max_positions")),
            ("cap.strategy.base_position_pct", caps.get("strategy.base_position_pct")),
            ("cap.strategy.max_position_size", caps.get("strategy.max_position_size")),
            ("sizing.position_size_pct_used", position_size_pct_used),
        ])

    print("| Control Point | Value |")
    print("|---|---|")
    for key, val in rows:
        print(f"| {key} | {val} |")


def main() -> None:
    parser = argparse.ArgumentParser(description="Trace trade quantity control points from a backtest result JSON.")
    parser.add_argument("--result", required=True, help="Path to results JSON (backtest/results/*.json)")
    parser.add_argument("--trade-index", type=int, default=None, help="1-based index into execution_history")
    parser.add_argument("--timestamp", default=None, help="Exact trade timestamp (ISO string)")
    parser.add_argument("--config", default=None, help="Optional YAML config for caps (suite or backtest config)")
    args = parser.parse_args()

    with open(args.result, "r") as f:
        result = json.load(f)

    trades = _load_execution_history(result)
    trade = _select_trade(trades, args.trade_index, args.timestamp)
    caps = _load_caps(args.config)
    _print_trace(trade, caps)


if __name__ == "__main__":
    main()
