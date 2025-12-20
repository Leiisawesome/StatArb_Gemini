"""
Papertest config loader
======================

Loads YAML configs with base override semantics similar to backtest/utils/config_loader.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
import copy
import yaml


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_config(config_path: str, base_config_path: Optional[str] = None) -> Dict[str, Any]:
    cfg_path = Path(config_path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    base_cfg: Dict[str, Any] = {}
    if base_config_path:
        base_path = Path(base_config_path)
        if not base_path.exists():
            raise FileNotFoundError(f"Base config file not found: {base_config_path}")
        base_cfg = yaml.safe_load(base_path.read_text()) or {}

    override_cfg = yaml.safe_load(cfg_path.read_text()) or {}
    merged = _deep_merge(base_cfg, override_cfg)
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


