#!/usr/bin/env python3
"""
Desk-Grade Experiment Suite Runner
===================================

Master script to run backtest experiments.

Usage:
    # Run single experiment
    python run_suite.py --experiment smoke_test
    
    # Run with custom config
    python run_suite.py --experiment baseline --config configs/my_config.yaml
    
    # Run full suite
    python run_suite.py --suite all
    
    # List available experiments
    python run_suite.py --list

Principles:
- Zero re-implementation of engine logic
- Orchestrates InstitutionalBacktestEngine only
- Config-driven execution
- Structured output

Author: StatArb_Gemini Core Engine
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backtest.experiments.smoke_test import SmokeTest
from backtest.experiments.baseline_backtest import BaselineBacktest
from backtest.experiments.parameter_sweep import ParameterSweep
from backtest.experiments.walk_forward_analysis import WalkForwardAnalysis
from backtest.experiments.monte_carlo_simulation import MonteCarloSimulation
from backtest.experiments.regime_specific_testing import RegimeSpecificTesting
from backtest.experiments.liquidity_stress_testing import LiquidityStressTesting
from backtest.experiments.correlation_stress_testing import CorrelationStressTesting
from backtest.experiments.survivorship_bias_testing import SurvivorshipBiasTesting
from backtest.experiments.data_error_simulation import DataErrorSimulation
from backtest.utils.config_loader import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Experiment registry
EXPERIMENTS = {
    'smoke_test': {
        'class': SmokeTest,
        'default_config': 'backtest/configs/smoke_test.yaml',
        'description': 'Quick sanity check (1 symbol, 1 day)'
    },
    'baseline': {
        'class': BaselineBacktest,
        'default_config': 'backtest/configs/baseline_backtest.yaml',
        'description': 'Full period baseline backtest (1 month)'
    },
    'parameter_sweep': {
        'class': ParameterSweep,
        'default_config': 'backtest/configs/parameter_sweep.yaml',
        'description': 'Grid search over strategy parameters'
    },
    'walk_forward': {
        'class': WalkForwardAnalysis,
        'default_config': 'backtest/configs/walk_forward_quick.yaml',
        'description': 'Out-of-sample testing with rolling windows'
    },
    'monte_carlo': {
        'class': MonteCarloSimulation,
        'default_config': 'backtest/configs/monte_carlo.yaml',
        'description': 'Probabilistic outcome distribution (100-1000 simulations)'
    },
    'regime_specific': {
        'class': RegimeSpecificTesting,
        'default_config': 'backtest/configs/regime_specific.yaml',
        'description': 'Performance segmented by market regime'
    },
    'liquidity_stress': {
        'class': LiquidityStressTesting,
        'default_config': 'backtest/configs/liquidity_stress.yaml',
        'description': 'Resilience under liquidity constraints'
    },
    'correlation_stress': {
        'class': CorrelationStressTesting,
        'default_config': 'backtest/configs/correlation_stress.yaml',
        'description': 'Portfolio under correlation breakdowns'
    },
    'survivorship_bias': {
        'class': SurvivorshipBiasTesting,
        'default_config': 'backtest/configs/survivorship_bias.yaml',
        'description': 'Realistic survivorship bias simulation'
    },
    'data_error': {
        'class': DataErrorSimulation,
        'default_config': 'backtest/configs/data_error.yaml',
        'description': 'Robustness to data quality issues'
    },
}


def list_experiments():
    """Print available experiments"""
    print("\n" + "="*80)
    print("📋 AVAILABLE EXPERIMENTS")
    print("="*80)
    
    for exp_name, exp_info in EXPERIMENTS.items():
        print(f"\n{exp_name}")
        print(f"  Description: {exp_info['description']}")
        print(f"  Config:      {exp_info['default_config']}")
    
    print("\n" + "="*80)


async def run_experiment(
    experiment_name: str,
    config_path: Optional[str] = None,
    base_config_path: str = "backtest/configs/base_config.yaml"
) -> bool:
    """
    Run a single experiment.
    
    Args:
        experiment_name: Name of experiment to run
        config_path: Optional custom config path
        base_config_path: Base config path
        
    Returns:
        True if experiment succeeded
    """
    if experiment_name not in EXPERIMENTS:
        logger.error(f"Unknown experiment: {experiment_name}")
        logger.info("Run with --list to see available experiments")
        return False
    
    exp_info = EXPERIMENTS[experiment_name]
    
    # Use default config if not provided
    if config_path is None:
        config_path = exp_info['default_config']
    
    logger.info(f"🚀 Starting experiment: {experiment_name}")
    logger.info(f"   Config: {config_path}")
    
    try:
        # Load config
        config = load_config(config_path, base_config_path)
        
        # Instantiate experiment
        experiment_class = exp_info['class']
        experiment = experiment_class(config)
        
        # Run experiment (ORCHESTRATION ONLY - engine is black box)
        logger.info(f"   {experiment.get_description()}")
        result = await experiment.run()
        
        # Print summary
        experiment.print_summary(result)
        
        # Save results
        experiment.save_results(result)
        
        return result.success
        
    except Exception as e:
        logger.error(f"❌ Experiment failed: {e}", exc_info=True)
        return False


async def run_suite(suite_name: str = "all") -> bool:
    """
    Run experiment suite.
    
    Args:
        suite_name: Suite name ('all' or custom)
        
    Returns:
        True if all experiments succeeded
    """
    if suite_name == "all":
        experiments_to_run = list(EXPERIMENTS.keys())
    else:
        # Add custom suite definitions here
        logger.error(f"Unknown suite: {suite_name}")
        return False
    
    logger.info(f"🧪 Running experiment suite: {suite_name}")
    logger.info(f"   Experiments: {len(experiments_to_run)}")
    
    results = []
    for exp_name in experiments_to_run:
        success = await run_experiment(exp_name)
        results.append((exp_name, success))
        
        if not success:
            logger.warning(f"⚠️  Experiment failed: {exp_name}")
    
    # Print suite summary
    print("\n" + "="*80)
    print("📊 SUITE SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for exp_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}  {exp_name}")
    
    print()
    print(f"Results: {passed}/{total} experiments passed")
    print("="*80)
    
    return passed == total


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Desk-Grade Backtest Experiment Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run smoke test
  python run_suite.py --experiment smoke_test
  
  # Run with custom config
  python run_suite.py --experiment baseline --config my_config.yaml
  
  # Run full suite
  python run_suite.py --suite all
  
  # List experiments
  python run_suite.py --list
        """
    )
    
    parser.add_argument(
        '--experiment',
        type=str,
        help='Experiment to run (e.g., smoke_test, baseline)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Path to experiment config file (YAML)'
    )
    
    parser.add_argument(
        '--base-config',
        type=str,
        default='backtest/configs/base_config.yaml',
        help='Path to base config file (default: backtest/configs/base_config.yaml)'
    )
    
    parser.add_argument(
        '--suite',
        type=str,
        help='Run experiment suite (e.g., all)'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List available experiments'
    )
    
    args = parser.parse_args()
    
    # Handle list
    if args.list:
        list_experiments()
        return 0
    
    # Handle suite
    if args.suite:
        success = asyncio.run(run_suite(args.suite))
        return 0 if success else 1
    
    # Handle single experiment
    if args.experiment:
        success = asyncio.run(
            run_experiment(
                args.experiment,
                args.config,
                args.base_config
            )
        )
        return 0 if success else 1
    
    # No arguments - show help
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())

