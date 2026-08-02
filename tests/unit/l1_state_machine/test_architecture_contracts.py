"""Structural architecture contracts for the trading system.

Drives shipped entry points and classes — not reimplemented stubs — so the
layer map (ingest → core → artifacts → paper shells → production) stays honest.
"""

from __future__ import annotations

import importlib
import inspect

from l1_microstructure.cli import build_parser, main
from l1_microstructure.live.paper import SimulatorPaperTradingRunner
from l1_microstructure.live.routed import RoutedLiveTradingRunner
from l1_microstructure.live.source import SourceBackedPaperRunner
from l1_microstructure.pipeline import L1MicrostructureStateMachine
from l1_microstructure.production.daemon import build_parser as build_daemon_parser
from l1_microstructure.production.runtime import ProductionRuntime
from l1_microstructure.transparent.engine import TransparentStatisticalEngine
from l1_microstructure.transparent.shadow import ComparativeShadowRunner
from l1_microstructure.transparent.workflow import TransparentArtifactDrivenWorkflow
from l1_microstructure.workflow import ArtifactDrivenResearchWorkflow


def test_cli_surface_exposes_research_paper_and_routed_entrypoints() -> None:
    parser = build_parser()
    # argparse stores subparsers; exercise the real builder rather than a copy of command names
    help_text = parser.format_help()
    for command in (
        "workflow",
        "transparent-workflow",
        "list-runs",
        "list-transparent-runs",
        "paper-historical",
        "paper-live",
        "live-routed",
        "ibkr-live-smoke",
    ):
        assert command in help_text
    assert callable(main)


def test_daemon_entry_exposes_preflight_without_starting_runtime() -> None:
    parser = build_daemon_parser()
    help_text = parser.format_help()
    assert "--config" in help_text
    assert "--preflight" in help_text


def test_paper_shells_compose_shared_v1_state_machine() -> None:
    paper_src = inspect.getsource(SimulatorPaperTradingRunner.start)
    assert "L1MicrostructureStateMachine" in paper_src
    source_src = inspect.getsource(SourceBackedPaperRunner._run_events)
    assert "SimulatorPaperTradingRunner" in source_src
    assert "resolve_by_run_id" in source_src  # explicit run_id path
    assert "require_validation_passed" in source_src
    routed_src = inspect.getsource(RoutedLiveTradingRunner.run_live)
    assert "L1MicrostructureStateMachine" in routed_src
    assert "route_orders_externally=True" in routed_src


def test_production_runtime_routes_v1_and_shadows_v2() -> None:
    load_src = inspect.getsource(ProductionRuntime._load_machines)
    assert "L1MicrostructureStateMachine" in load_src
    assert "resolve_passing_by_run_id" in load_src
    assert "route_orders_externally=True" in load_src
    assert "TransparentStatisticalEngine" in load_src or "transparent_shadow" in load_src
    shadow_src = inspect.getsource(ProductionRuntime._process_transparent_shadow)
    assert "transparent_shadow_engines" in shadow_src


def test_transparent_shadow_runner_isolates_candidate_from_baseline() -> None:
    src = inspect.getsource(ComparativeShadowRunner.run)
    assert "self.baseline.on_event" in src
    assert "self.candidate.on_event" in src
    # candidate failures must not abort baseline loop (try/except around candidate)
    assert "try:" in src and "candidate_error" in src


def test_research_workflows_are_distinct_entry_classes() -> None:
    assert ArtifactDrivenResearchWorkflow is not TransparentArtifactDrivenWorkflow
    assert L1MicrostructureStateMachine is not TransparentStatisticalEngine
    # both are importable from package without construction
    assert importlib.import_module("l1_microstructure.workflow").ArtifactDrivenResearchWorkflow is ArtifactDrivenResearchWorkflow
    assert importlib.import_module("l1_microstructure.transparent.engine").TransparentStatisticalEngine is TransparentStatisticalEngine
