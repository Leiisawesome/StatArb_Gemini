#!/usr/bin/env python3
"""
Papertest Suite Runner
=====================

Mirrors backtest/run_suite.py orchestration style.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from papertest.experiments.smoke_test import SmokeTest
from papertest.experiments.baseline_papertest import BaselinePapertest
from papertest.experiments.regime_transition import RegimeTransitionPapertest
from papertest.experiments.latency_stress import LatencyStressPapertest
from papertest.experiments.execution_quality import ExecutionQualityPapertest
from papertest.experiments.checkpoint_restore_determinism import CheckpointRestoreDeterminismPapertest
from papertest.experiments.symbol_picker_test import SymbolPickerTestExperiment
from papertest.utils.config_loader import load_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

EXPERIMENTS = {
    "smoke_test": {
        "class": SmokeTest,
        "default_config": "core_engine/config/catalog/suites/smoke_test_mr.yaml",
        "description": "Quick sanity check (1 symbol, 1 day)",
    },
    "baseline": {
        "class": BaselinePapertest,
        "default_config": "papertest/configs/baseline_papertest.yaml",
        "description": "Multi-day multi-symbol baseline papertest",
    },
    "regime_transition": {
        "class": RegimeTransitionPapertest,
        "default_config": "papertest/configs/regime_transition.yaml",
        "description": "Regime transition handling checks",
    },
    "latency_stress": {
        "class": LatencyStressPapertest,
        "default_config": "papertest/configs/latency_stress.yaml",
        "description": "Execution under elevated latency",
    },
    "execution_quality": {
        "class": ExecutionQualityPapertest,
        "default_config": "papertest/configs/baseline_papertest.yaml",
        "description": "Execution quality metrics / TCA (best-effort)",
    },
    "checkpoint_restore_determinism": {
        "class": CheckpointRestoreDeterminismPapertest,
        "default_config": "papertest/configs/smoke_test.yaml",
        "description": "Checkpoint/restore determinism checks",
    },
    "symbol_picker_test": {
        "class": SymbolPickerTestExperiment,
        "default_config": "papertest/configs/smoke_test.yaml",
        "description": "Integration test: Run Picker -> Artifact -> Papertest Sim",
    },
}


def list_experiments() -> None:
    print("\n" + "=" * 80)
    print("📋 AVAILABLE PAPERTEST EXPERIMENTS")
    print("=" * 80)
    for name, info in EXPERIMENTS.items():
        print(f"\n{name}")
        print(f"  Description: {info['description']}")
        print(f"  Config:      {info['default_config']}")
    print("\n" + "=" * 80)


async def run_experiment(
    experiment_name: str,
    config_path: Optional[str] = None,
    base_config_path: str = "core_engine/config/catalog/papertest/base_config.yaml",
) -> bool:
    if experiment_name not in EXPERIMENTS:
        logger.error(f"Unknown experiment: {experiment_name}")
        return False

    exp_info = EXPERIMENTS[experiment_name]
    if config_path is None:
        config_path = exp_info["default_config"]

    logger.info(f"🚀 Starting papertest experiment: {experiment_name}")
    logger.info(f"   Config: {config_path}")

    try:
        config = load_config(config_path, base_config_path)

        exp_cls = exp_info["class"]
        exp = exp_cls(config)
        logger.info(f"   {exp.get_description()}")
        result = await exp.run()
        exp.print_summary(result)
        exp.save_results(result)
        return result.success
    except Exception as e:
        logger.error(f"❌ Papertest experiment failed: {e}", exc_info=True)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Desk-Grade Papertest Experiment Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--experiment", type=str, help="Experiment to run (e.g., smoke_test)")
    parser.add_argument("--config", type=str, help="Path to experiment config file (YAML)")
    parser.add_argument(
        "--base-config",
        type=str,
        default="core_engine/config/catalog/papertest/base_config.yaml",
        help="Path to base config file",
    )
    parser.add_argument("--list", action="store_true", help="List available experiments")

    args = parser.parse_args()

    if args.list:
        list_experiments()
        return 0

    if args.experiment:
        ok = asyncio.run(run_experiment(args.experiment, args.config, args.base_config))
        return 0 if ok else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


