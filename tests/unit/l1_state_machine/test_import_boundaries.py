from __future__ import annotations

import subprocess
import sys
import textwrap


def test_public_root_exports_remain_compatible() -> None:
    import l1_microstructure

    assert all(getattr(l1_microstructure, name) is not None for name in l1_microstructure.__all__)


def _run_isolated_imports(source: str) -> subprocess.CompletedProcess[str]:
    script = textwrap.dedent(
        f"""
        import importlib.abc
        import sys

        blocked = {{"ibapi", "massive", "fastapi", "textual", "keyring"}}

        class BlockedDependencyFinder(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname.split(".", 1)[0] in blocked:
                    raise ModuleNotFoundError(f"blocked optional dependency: {{fullname}}")
                return None

        sys.meta_path.insert(0, BlockedDependencyFinder())
        {textwrap.indent(textwrap.dedent(source), "        ").lstrip()}
        loaded_roots = {{name.split(".", 1)[0] for name in sys.modules}}
        assert blocked.isdisjoint(loaded_roots), blocked & loaded_roots
        """
    )
    return subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )


def test_core_replay_and_research_import_without_infrastructure_dependencies() -> None:
    result = _run_isolated_imports(
        """
        import l1_microstructure
        from l1_microstructure import (
            ArtifactDrivenResearchWorkflow,
            DeterministicReplayEngine,
            EventKind,
            FrameworkConfig,
            QuoteEvent,
        )
        from l1_microstructure.ingest import LiveSubscriptionRequest, MarketDataSource, MassivePayloadNormalizer

        assert l1_microstructure.EventKind is EventKind
        assert FrameworkConfig is not None
        assert QuoteEvent is not None
        assert DeterministicReplayEngine is not None
        assert ArtifactDrivenResearchWorkflow is not None
        assert LiveSubscriptionRequest is not None
        assert MarketDataSource is not None
        assert MassivePayloadNormalizer is not None
        """
    )

    assert result.returncode == 0, result.stderr


def test_live_contracts_and_execution_service_do_not_import_ibkr() -> None:
    result = _run_isolated_imports(
        """
        from l1_microstructure.live import (
            OrderRouter,
            ProductionOrderRouter,
            RoutedExecutionService,
            RoutedLiveTradingRunner,
            RunnerConfig,
        )

        assert OrderRouter is not None
        assert ProductionOrderRouter is not None
        assert RoutedExecutionService is not None
        assert RoutedLiveTradingRunner is not None
        assert RunnerConfig is not None
        """
    )

    assert result.returncode == 0, result.stderr


def test_cli_import_is_independent_of_prior_module_import_order() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import l1_microstructure.cli"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
