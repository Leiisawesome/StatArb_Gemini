"""
Strategy Registry (Enhanced, Rule 7)
====================================

This module provides lightweight strategy discovery/registration for the
Enhanced strategy stack:

- Strategies are `EnhancedBaseStrategy` subclasses.
- `implementations/` contains core alpha only.
- The registry is used by `StrategyManager` for (optional) auto-discovery.

Important:
- This replaces the legacy registry that depended on `strategy_engine.py`.
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from core_engine.type_definitions.strategy import StrategyType
from .base_strategy_enhanced import EnhancedBaseStrategy

logger = logging.getLogger(__name__)


@dataclass
class StrategyMetadata:
    """Minimum metadata needed for discovery + registration."""

    strategy_id: str
    name: str
    module_path: str
    file_path: str
    class_name: str
    strategy_type: StrategyType = StrategyType.CUSTOM
    discovered_at: datetime = field(default_factory=datetime.now)
    extra: Dict[str, Any] = field(default_factory=dict)


class StrategyDiscovery:
    """Discover EnhancedBaseStrategy subclasses from python source files (AST-based)."""

    def discover_strategies(self, search_paths: Optional[List[str]] = None) -> List[StrategyMetadata]:
        paths = [Path(p) for p in (search_paths or [])]
        out: List[StrategyMetadata] = []

        for p in paths:
            if not p.exists():
                continue
            for file_path in p.rglob("*.py"):
                if file_path.name.startswith("__"):
                    continue
                out.extend(self._analyze_file(file_path))

        return out

    def _analyze_file(self, file_path: Path) -> List[StrategyMetadata]:
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))
        except Exception:
            return []

        metas: List[StrategyMetadata] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and self._is_enhanced_strategy_class(node):
                class_name = node.name
                strategy_id = f"{file_path.stem}.{class_name}"
                module_path = self._module_path_from_file(file_path)
                metas.append(
                    StrategyMetadata(
                        strategy_id=strategy_id,
                        name=class_name,
                        module_path=module_path,
                        file_path=str(file_path),
                        class_name=class_name,
                    )
                )
        return metas

    def _is_enhanced_strategy_class(self, class_node: ast.ClassDef) -> bool:
        # Detect inheritance by base class name: EnhancedBaseStrategy
        for base in class_node.bases:
            if isinstance(base, ast.Name) and base.id == "EnhancedBaseStrategy":
                return True
            if isinstance(base, ast.Attribute) and base.attr == "EnhancedBaseStrategy":
                return True
        return False

    def _module_path_from_file(self, file_path: Path) -> str:
        # Best-effort; StrategyManager uses metadata mainly for logging.
        # If needed later, this can be made robust by anchoring to repo root / package root.
        parts = list(file_path.parts)
        if "core_engine" in parts:
            idx = parts.index("core_engine")
            mod_parts = parts[idx:]
            if mod_parts[-1].endswith(".py"):
                mod_parts[-1] = mod_parts[-1][:-3]
            return ".".join(mod_parts)
        return file_path.stem


class EnhancedStrategyRegistry:
    """
    Minimal registry used by StrategyManager.

    The registry is intentionally lightweight; StrategyManager remains the
    orchestration authority.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.discovery = StrategyDiscovery()
        self.strategies: Dict[str, StrategyMetadata] = {}
        self.is_initialized = False

    async def initialize(self) -> bool:
        self.is_initialized = True
        return True

    async def register_strategy(
        self,
        strategy_class: Optional[Type[EnhancedBaseStrategy]],
        metadata: Optional[StrategyMetadata] = None,
        validate: bool = True,
    ) -> str:
        # StrategyManager sometimes supplies metadata only (strategy_class=None) during discovery.
        if metadata is None:
            if strategy_class is None:
                raise ValueError("register_strategy requires either strategy_class or metadata")
            metadata = StrategyMetadata(
                strategy_id=strategy_class.__name__,
                name=strategy_class.__name__,
                module_path=strategy_class.__module__,
                file_path=strategy_class.__module__,
                class_name=strategy_class.__name__,
            )

        self.strategies[metadata.strategy_id] = metadata
        return metadata.strategy_id

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self.is_initialized,
            "strategy_count": len(self.strategies),
        }


# Backward-compat alias (used by StrategyManager)
StrategyRegistry = EnhancedStrategyRegistry

