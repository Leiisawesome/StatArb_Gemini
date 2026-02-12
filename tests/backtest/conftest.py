"""Conftest for backtest regression tests."""

import pytest


def pytest_addoption(parser):
    """Add --update-golden CLI option for re-capturing golden baselines."""
    parser.addoption(
        "--update-golden",
        action="store_true",
        default=False,
        help="Re-capture golden baselines from a fresh smoke test run.",
    )
