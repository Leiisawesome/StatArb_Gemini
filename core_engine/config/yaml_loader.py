"""
Centralized YAML config loader
==============================

Adds two capabilities needed for a single canonical config source of truth:

1) `includes`: allow YAML files to include other YAML files (deep-merged)
2) Deep-merge semantics: later configs override earlier configs

This lets BT/PT keep thin wrapper configs under their package dirs while
the canonical configs live in `core_engine/config/catalog/`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Set, Union

import yaml

from core_engine.utils.config import deep_merge


PathLike = Union[str, Path]


def load_yaml(path: PathLike) -> Dict[str, Any]:
    p = Path(path).expanduser()
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {p}")
    data = yaml.safe_load(p.read_text()) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping/dict: {p}")
    return data


def _resolve_include(parent: Path, inc: str) -> Path:
    inc_path = Path(inc).expanduser()
    if inc_path.is_absolute():
        return inc_path
    return (parent / inc_path).resolve()


def load_with_includes(path: PathLike, *, _visited: Optional[Set[Path]] = None) -> Dict[str, Any]:
    """
    Load a YAML file and recursively deep-merge any `includes`.

    Supported keys:
    - `includes`: string or list[string] of paths (relative to this file)
    - `include`: alias for single include (string)
    """
    p = Path(path).expanduser().resolve()
    visited = set(_visited or set())
    if p in visited:
        chain = " -> ".join(str(x) for x in list(visited) + [p])
        raise ValueError(f"Config include cycle detected: {chain}")
    visited.add(p)

    raw = load_yaml(p)

    includes: Any = None
    if "includes" in raw:
        includes = raw.pop("includes")
    elif "include" in raw:
        includes = raw.pop("include")

    merged: Dict[str, Any] = {}
    if includes:
        if isinstance(includes, str):
            include_list = [includes]
        elif isinstance(includes, list) and all(isinstance(x, str) for x in includes):
            include_list = includes
        else:
            raise ValueError(f"`includes` must be a string or list of strings: {p}")

        for inc in include_list:
            inc_path = _resolve_include(p.parent, inc)
            inc_cfg = load_with_includes(inc_path, _visited=visited)
            merged = deep_merge(merged, inc_cfg)

    merged = deep_merge(merged, raw)
    return merged


def load_merged(paths: Iterable[PathLike]) -> Dict[str, Any]:
    """
    Load a sequence of configs (each supports `includes`) and deep-merge them
    in order. Later paths override earlier ones.
    """
    merged: Dict[str, Any] = {}
    for p in paths:
        merged = deep_merge(merged, load_with_includes(p))
    return merged


