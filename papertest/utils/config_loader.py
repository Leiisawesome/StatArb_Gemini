"""
Papertest config loader
======================

Loads YAML configs with base override semantics similar to backtest/utils/config_loader.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime
from zoneinfo import ZoneInfo

from core_engine.utils.config import deep_merge
from core_engine.config.yaml_loader import load_with_includes


def load_config(config_path: str, base_config_path: Optional[str] = None) -> Dict[str, Any]:
    cfg_path = Path(config_path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    base_cfg: Dict[str, Any] = {}
    if base_config_path:
        base_path = Path(base_config_path)
        if not base_path.exists():
            raise FileNotFoundError(f"Base config file not found: {base_config_path}")
        base_cfg = load_with_includes(base_path)

    override_cfg = load_with_includes(cfg_path)
    merged = deep_merge(base_cfg, override_cfg)
    validate_papertest_schema(merged)
    return merged


def validate_papertest_schema(cfg: Dict[str, Any]) -> None:
    pt = cfg.get("papertest")
    if not isinstance(pt, dict):
        raise ValueError("Missing top-level 'papertest' dict in config")

    data = pt.get("data", {})
    if not isinstance(data, dict):
        raise ValueError("papertest.data must be a dict")
    for key in ("symbols", "start_date", "end_date", "interval", "replay_speed"):
        if key not in data:
            raise ValueError(f"papertest.data missing required key: {key}")
    if not isinstance(data.get("symbols"), list) or not data["symbols"]:
        raise ValueError("papertest.data.symbols must be a non-empty list")

    dispatcher = pt.get("dispatcher", {})
    if dispatcher and not isinstance(dispatcher, dict):
        raise ValueError("papertest.dispatcher must be a dict if provided")

    buffers = pt.get("buffers", {})
    if buffers and not isinstance(buffers, dict):
        raise ValueError("papertest.buffers must be a dict if provided")

    risk = pt.get("risk", {})
    if risk and not isinstance(risk, dict):
        raise ValueError("papertest.risk must be a dict if provided")

    execution = pt.get("execution", {})
    if execution and not isinstance(execution, dict):
        raise ValueError("papertest.execution must be a dict if provided")

    debug = pt.get("debug", {})
    if debug and not isinstance(debug, dict):
        raise ValueError("papertest.debug must be a dict if provided")

    # Optional debug controls (strings like "HH:MM")
    if debug:
        for k in ("start_at_time", "stop_at_time"):
            if k in debug and debug[k] is not None and not isinstance(debug[k], (str, int)):
                raise ValueError(f"papertest.debug.{k} must be a string like 'HH:MM' if provided")


def parse_debug_timestamps(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse start_at_time and stop_at_time from config into datetime objects.
    """
    pt = config.get("papertest", {})
    debug_cfg = pt.get("debug", {}) or {}
    data_cfg = pt.get("data", {})
    
    start_date = str(data_cfg.get("start_date", ""))
    tz_name = debug_cfg.get("timezone", "America/New_York")
    
    results = {
        "start_at_timestamp": None,
        "stop_at_timestamp": None,
        "stop_after_bars": debug_cfg.get("stop_after_bars")
    }
    
    if not start_date:
        return results

    day = datetime.strptime(start_date, "%Y-%m-%d").date()
    tz = ZoneInfo(tz_name)

    for key in ("start_at_time", "stop_at_time"):
        val = debug_cfg.get(key)
        if val:
            try:
                hh, mm = [int(x) for x in str(val).split(":")]
                results[key.replace("_time", "_timestamp")] = datetime(
                    day.year, day.month, day.day, hh, mm, tzinfo=tz
                )
            except Exception:
                pass
                
    return results


