"""
Config Loader Utilities
========================

Load and merge YAML configuration files.

Author: StatArb_Gemini Core Engine
"""

from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import fields
import logging
import yaml

from core_engine.utils.config import deep_merge
from core_engine.config.yaml_loader import load_with_includes
from core_engine.config import BacktestConfig

logger = logging.getLogger(__name__)


_KNOWN_EXPERIMENT_KEYS = {
    "experiment_name",
    "experiment_type",
    "strategy",
    "strategies",
    "includes",
    "base_config",
    "_includes_meta",
    "unknown_keys_policy",
}

_ALLOWED_FLAT_CONFIG_KEYS = {f.name for f in fields(BacktestConfig)} | _KNOWN_EXPERIMENT_KEYS


def _enforce_unknown_key_policy(config: Dict[str, Any], config_path: str) -> None:
    """Apply deterministic unknown-key policy for flat backtest configs."""
    if not isinstance(config, dict):
        return

    unknown_keys = sorted(k for k in config.keys() if k not in _ALLOWED_FLAT_CONFIG_KEYS)
    if not unknown_keys:
        return

    policy = str(config.get("unknown_keys_policy", "warn")).strip().lower()
    message = (
        f"Unknown flat config keys in {config_path}: {unknown_keys}. "
        "These keys are ignored by BacktestConfig mapping. "
        "Set unknown_keys_policy: error to fail fast."
    )

    if policy == "error":
        raise ValueError(message)

    logger.warning(message)

def load_config(config_path: str, base_config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load experiment configuration from YAML file.

    Args:
        config_path: Path to primary config file
        base_config_path: Optional path to base config (merged first)

    Returns:
        Merged configuration dictionary
    """
    # Load primary config first (supports `includes`)
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    primary_config = load_with_includes(config_file)

    # Centralized config support:
    # If the primary config is in papertest schema, avoid merging the backtest
    # base_config (flat schema), which would otherwise override canonical suite values.
    if isinstance(primary_config.get("papertest"), dict):
        merged = primary_config
        if base_config_path:
            base_path = Path(base_config_path)
            if base_path.exists():
                base_cfg = load_with_includes(base_path)
                if isinstance(base_cfg.get("papertest"), dict):
                    merged = deep_merge(base_cfg, primary_config)
                    logger.info(f"Loaded papertest-schema base config: {base_config_path}")
            else:
                logger.warning(f"Base config not found: {base_config_path}")
        return _papertest_to_backtest_config(merged)

    config: Dict[str, Any] = {}
    # Load base config if provided (supports `includes`)
    if base_config_path:
        base_path = Path(base_config_path)
        if base_path.exists():
            config = load_with_includes(base_path)
            logger.info(f"Loaded base config: {base_config_path}")
        else:
            logger.warning(f"Base config not found: {base_config_path}")

    # Merge configs (primary overrides base)
    config = deep_merge(config, primary_config)

    _enforce_unknown_key_policy(config, config_path)

    logger.info(f"Loaded config: {config_path}")
    return config


def _papertest_to_backtest_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map canonical papertest-schema configs into the flat backtest smoke-test schema.

    This keeps a single canonical config source of truth while allowing existing
    backtest experiments (which expect flat keys) to run unchanged.
    """
    pt = cfg.get("papertest", {}) or {}
    data = pt.get("data", {}) or {}
    buffers = pt.get("buffers", {}) or {}
    risk = pt.get("risk", {}) or {}
    execution = pt.get("execution", {}) or {}
    # Strategy aggregation / coordinator settings (smoke-test knobs)
    min_confidence_threshold = pt.get("min_confidence_threshold", cfg.get("min_confidence_threshold"))
    strategy_manager = pt.get("strategy_manager", {}) or {}

    symbols = data.get("symbols") or []
    interval = data.get("interval")
    start_date = data.get("start_date")
    end_date = data.get("end_date")

    warmup_bars = buffers.get("warmup_required")
    initial_capital = execution.get("initial_cash")

    # Prefer explicit max_position_size; fall back to pct alias.
    max_position_size = risk.get("max_position_size")
    if max_position_size is None:
        max_position_size = risk.get("max_position_pct")
    max_position_pct = risk.get("max_position_pct")
    if max_position_pct is None:
        # Backwards compat: if not specified, treat pct cap as the overall max position size.
        max_position_pct = max_position_size

    # Map concentration limit if available
    max_concentration = risk.get("position_concentration_limit", cfg.get("max_concentration", 0.20))

    # Regime settings
    regime = pt.get("regime", {}) or {}

    out: Dict[str, Any] = {
        "experiment_name": cfg.get("experiment_name", "Smoke_Test"),
        "experiment_type": cfg.get("experiment_type", "smoke_test"),
        "symbols": symbols,
        "interval": interval,
        "start_date": start_date,
        "end_date": end_date,
        "warmup_bars": warmup_bars,
        "initial_capital": initial_capital,
        "allow_shorts": risk.get("allow_shorts", False),
        "min_signal_confidence": risk.get("min_signal_confidence", cfg.get("min_signal_confidence", 0.60)),
        "min_confidence_threshold": min_confidence_threshold if min_confidence_threshold is not None else 0.60,
        "enable_multi_strategy_coordination": strategy_manager.get("enable_multi_strategy_coordination", True),
        "enable_signal_aggregation": strategy_manager.get("enable_signal_aggregation", True),
        "enable_conflict_resolution": strategy_manager.get("enable_conflict_resolution", True),
        "enable_dynamic_weighting": strategy_manager.get("enable_dynamic_weighting", True),
        "isolate_strategy_backtests": strategy_manager.get("isolate_strategy_backtests", False),
        "external_strategy_configs": strategy_manager.get("external_strategy_configs", []),
        "max_position_size": max_position_size if max_position_size is not None else cfg.get("max_position_size", 0.10),
        "max_position_pct": max_position_pct,
        "max_concentration": max_concentration,
        "strategies": pt.get("strategies") or pt.get("strategy") or cfg.get("strategies") or cfg.get("strategy") or [],
    }

    # --- H1 fix: Map previously-dropped execution/risk/regime fields ---

    # Execution fields
    exec_seed = execution.get("seed")
    if exec_seed is not None:
        out["execution_seed"] = exec_seed
    exec_commission = execution.get("commission_per_share")
    if exec_commission is not None:
        out["commission_per_trade"] = exec_commission
    exec_min_commission = execution.get("min_commission")
    if exec_min_commission is not None:
        out["min_commission"] = exec_min_commission
    exec_slippage = execution.get("slippage_bps_max") or execution.get("base_slippage_bps")
    if exec_slippage is not None:
        out["base_slippage_bps"] = exec_slippage
    exec_impact = execution.get("impact_coefficient") or execution.get("linear_coefficient")
    if exec_impact is not None:
        out["linear_coefficient"] = exec_impact
    exec_sqrt = execution.get("sqrt_coefficient")
    if exec_sqrt is not None:
        out["sqrt_coefficient"] = exec_sqrt

    # Risk fields
    risk_max_positions = risk.get("max_positions")
    if risk_max_positions is not None:
        out["max_positions"] = risk_max_positions
    risk_daily_budget = risk.get("daily_risk_budget_pct")
    if risk_daily_budget is not None:
        out["max_daily_var"] = risk_daily_budget
    risk_per_trade = risk.get("per_trade_risk_pct")
    if risk_per_trade is not None:
        out["per_trade_risk_pct"] = risk_per_trade

    # Regime fields
    regime_lookback = regime.get("lookback_window")
    if regime_lookback is not None:
        out["regime_lookback_window"] = regime_lookback
    regime_vol_window = regime.get("volatility_window")
    if regime_vol_window is not None:
        out["regime_volatility_window"] = regime_vol_window

    # Ensure strategies is a list
    if not isinstance(out["strategies"], list):
        out["strategies"] = [out["strategies"]]

    # Additional parity checks for strategy-level fields (if provided in PT schema)
    if out["strategies"]:
        for s in out["strategies"]:
            if not isinstance(s, dict):
                continue
            # Parity: Map 'risk_limit' to 'max_position_size' at strategy level
            if "risk_limit" in s and "max_position_size" not in s:
                s["max_position_size"] = s["risk_limit"]
            # Parity: Ensure 'type' is set even if only 'strategy_type' exists
            if "strategy_type" in s and "type" not in s:
                s["type"] = s["strategy_type"]

    # Pipeline trace settings (Signal-to-PnL trace framework)
    trace = pt.get("trace", {}) or {}
    if trace.get("enable_pipeline_trace"):
        out["enable_pipeline_trace"] = True

    # NOTE: We intentionally do not merge arbitrary flat keys here.
    # If you need a flat override, put it into the canonical papertest schema
    # (or add a dedicated override adapter).
    return out

def save_config(config: Dict[str, Any], output_path: str):
    """
    Save configuration to YAML file.

    Args:
        config: Configuration dictionary
        output_path: Output file path
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    logger.info(f"Saved config: {output_path}")

