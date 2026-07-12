"""Pytest safeguards for the l1_microstructure repository."""

from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-external",
        action="store_true",
        default=False,
        help="run tests that contact Massive or IBKR",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--run-external"):
        return
    skip_external = pytest.mark.skip(reason="external test requires --run-external")
    for item in items:
        if "external" in item.keywords:
            item.add_marker(skip_external)
