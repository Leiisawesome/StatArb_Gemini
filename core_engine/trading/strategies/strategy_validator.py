"""
Strategy Validator (Enhanced, Rule 7)
=====================================

Hard-failing Rule 7 compliance checks for Enhanced strategies.

Enforced boundaries:
- Strategies emit intent only (StrategySignal).
- No broker/execution calls from strategy code.
- No internal position SSOT (`active_positions`, `_positions`).
- No sizing authority (`calculate_position_size` overrides).

This validator is intended to be called by StrategyManager during strategy
registration / initialization.
"""

from __future__ import annotations

import ast
import inspect
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base_strategy_enhanced import EnhancedBaseStrategy

logger = logging.getLogger(__name__)


@dataclass
class Rule7Violation:
    code: str
    message: str
    file_path: Optional[str] = None
    line: Optional[int] = None


class Rule7ComplianceError(RuntimeError):
    def __init__(self, strategy_name: str, violations: List[Rule7Violation]):
        super().__init__(self._format(strategy_name, violations))
        self.strategy_name = strategy_name
        self.violations = violations

    @staticmethod
    def _format(strategy_name: str, violations: List[Rule7Violation]) -> str:
        lines = [f"Rule 7 compliance failed for strategy: {strategy_name}"]
        for v in violations:
            loc = ""
            if v.file_path and v.line:
                loc = f" ({v.file_path}:{v.line})"
            elif v.file_path:
                loc = f" ({v.file_path})"
            lines.append(f"- [{v.code}]{loc}: {v.message}")
        return "\n".join(lines)


@dataclass
class Rule7ComplianceResult:
    ok: bool
    violations: List[Rule7Violation] = field(default_factory=list)


class EnhancedStrategyValidator:
    """
    Validator entrypoint used by StrategyManager.

    This is intentionally focused on Rule 7 boundaries. Other validations
    (data schema completeness, feature availability, etc.) should live in
    pipeline validation.
    """

    FORBIDDEN_ATTRS = {"active_positions", "_positions", "positions"}
    FORBIDDEN_METHOD_OVERRIDES = {"calculate_position_size"}
    FORBIDDEN_IMPORT_SUBSTRINGS = (
        "core_engine.broker",
        "core_engine.trading.execution",
        "core_engine.trading.order",
        "core_engine.trading.broker",
    )
    FORBIDDEN_CALL_NAMES = {
        "place_order",
        "submit_order",
        "send_order",
        "create_order",
    }

    def validate_rule7(self, strategy: EnhancedBaseStrategy) -> Rule7ComplianceResult:
        violations: List[Rule7Violation] = []

        strategy_cls = strategy.__class__
        strategy_name = f"{strategy_cls.__module__}.{strategy_cls.__name__}"

        # Runtime reflection: ensure no sizing override
        try:
            cls_method = inspect.getattr_static(strategy_cls, "calculate_position_size", None)
            base_method = inspect.getattr_static(EnhancedBaseStrategy, "calculate_position_size", None)
            if cls_method is not None and base_method is not None and cls_method is not base_method:
                violations.append(
                    Rule7Violation(
                        code="SIZING_OVERRIDE",
                        message="Strategy overrides calculate_position_size(); sizing authority must live in RiskManager.",
                    )
                )
        except Exception:
            # If reflection fails, rely on AST checks below.
            pass

        # AST checks: parse source file for forbidden patterns
        src_path = inspect.getsourcefile(strategy_cls)
        if src_path:
            try:
                content = Path(src_path).read_text(encoding="utf-8")
                tree = ast.parse(content, filename=src_path)
                violations.extend(self._ast_scan(tree, src_path, target_class_name=strategy_cls.__name__))
            except Exception as e:
                violations.append(
                    Rule7Violation(
                        code="AST_SCAN_FAILED",
                        message=f"Could not AST-scan strategy source for Rule 7 compliance: {e}",
                        file_path=src_path,
                    )
                )

        ok = len(violations) == 0
        return Rule7ComplianceResult(ok=ok, violations=violations)

    def enforce_rule7(self, strategy: EnhancedBaseStrategy) -> None:
        res = self.validate_rule7(strategy)
        if not res.ok:
            raise Rule7ComplianceError(
                strategy_name=f"{strategy.__class__.__module__}.{strategy.__class__.__name__}",
                violations=res.violations,
            )

    def _ast_scan(self, tree: ast.AST, src_path: str, target_class_name: str) -> List[Rule7Violation]:
        violations: List[Rule7Violation] = []

        # 1) Forbidden imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if any(s in alias.name for s in self.FORBIDDEN_IMPORT_SUBSTRINGS):
                        violations.append(
                            Rule7Violation(
                                code="FORBIDDEN_IMPORT",
                                message=f"Forbidden import: {alias.name}",
                                file_path=src_path,
                                line=getattr(node, "lineno", None),
                            )
                        )
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if any(s in mod for s in self.FORBIDDEN_IMPORT_SUBSTRINGS):
                    violations.append(
                        Rule7Violation(
                            code="FORBIDDEN_IMPORT",
                            message=f"Forbidden import-from: {mod}",
                            file_path=src_path,
                            line=getattr(node, "lineno", None),
                        )
                    )

        # Locate the target strategy class in this file and only enforce class-body rules there.
        target_cls: Optional[ast.ClassDef] = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == target_class_name:
                target_cls = node
                break

        if target_cls is None:
            violations.append(
                Rule7Violation(
                    code="CLASS_NOT_FOUND",
                    message=f"Could not find class '{target_class_name}' in AST; cannot enforce class-scoped Rule 7 checks.",
                    file_path=src_path,
                )
            )
            return violations

        # 2) Forbidden attribute assignments (self.active_positions = ...) inside strategy class
        for node in ast.walk(target_cls):
            if isinstance(node, ast.Assign):
                for tgt in node.targets:
                    attr = self._self_attr_name(tgt)
                    if attr and attr in self.FORBIDDEN_ATTRS:
                        violations.append(
                            Rule7Violation(
                                code="FORBIDDEN_POSITION_STATE",
                                message=f"Strategy assigns to '{attr}'. Position SSOT must be PositionBook.",
                                file_path=src_path,
                                line=getattr(node, "lineno", None),
                            )
                        )
            elif isinstance(node, ast.AnnAssign):
                attr = self._self_attr_name(node.target)
                if attr and attr in self.FORBIDDEN_ATTRS:
                    violations.append(
                        Rule7Violation(
                            code="FORBIDDEN_POSITION_STATE",
                            message=f"Strategy defines '{attr}'. Position SSOT must be PositionBook.",
                            file_path=src_path,
                            line=getattr(node, "lineno", None),
                        )
                    )

        # 3) Forbidden method overrides at class level
        for item in target_cls.body:
            if isinstance(item, ast.FunctionDef) and item.name in self.FORBIDDEN_METHOD_OVERRIDES:
                violations.append(
                    Rule7Violation(
                        code="SIZING_OVERRIDE",
                        message=f"Strategy defines '{item.name}'. Sizing must be delegated to RiskManager.",
                        file_path=src_path,
                        line=getattr(item, "lineno", None),
                    )
                )

        # 4) Forbidden execution-style calls inside strategy class
        for node in ast.walk(target_cls):
            if isinstance(node, ast.Call):
                name = self._call_name(node)
                if name and name in self.FORBIDDEN_CALL_NAMES:
                    violations.append(
                        Rule7Violation(
                            code="FORBIDDEN_EXECUTION_CALL",
                            message=f"Forbidden execution call '{name}()' in strategy code.",
                            file_path=src_path,
                            line=getattr(node, "lineno", None),
                        )
                    )

        return violations

    def _self_attr_name(self, node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self":
            return node.attr
        return None

    def _call_name(self, node: ast.Call) -> Optional[str]:
        # func can be Name(...) or Attribute(...)
        fn = node.func
        if isinstance(fn, ast.Name):
            return fn.id
        if isinstance(fn, ast.Attribute):
            return fn.attr
        return None


# Backward-compat alias
StrategyValidator = EnhancedStrategyValidator

