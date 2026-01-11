"""
Config Loader Utilities
========================

Load and merge YAML configuration files.

Author: StatArb_Gemini Core Engine
"""

from pathlib import Path
from typing import Dict, Any, Optional
import logging

from core_engine.utils.config import deep_merge
from core_engine.config.yaml_loader import load_with_includes

logger = logging.getLogger(__name__)

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
        "max_position_size": max_position_size if max_position_size is not None else cfg.get("max_position_size", 0.10),
        "max_position_pct": max_position_pct,
        "strategies": pt.get("strategies", cfg.get("strategies", [])),
    }

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

