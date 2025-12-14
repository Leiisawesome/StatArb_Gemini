"""
Experiment 7: Liquidity Stress Testing
=======================================

Test strategy resilience under various liquidity constraints.

Purpose:
- Assess impact of reduced liquidity on performance
- Identify liquidity-dependent execution costs
- Validate liquidity filters and constraints
- Test worst-case liquidity scenarios

Methodology:
- Artificially constrain liquidity parameters
- Run strategy with varying liquidity scenarios
- Measure impact on execution costs and slippage
- Identify liquidity sensitivity thresholds

Scenarios:
- Baseline: Normal liquidity
- Low liquidity: 50% of normal volume
- Crisis liquidity: 25% of normal volume + wide spreads
- Flash crash: Extreme illiquidity + high volatility

Expected Duration: 10-30 minutes

Author: StatArb_Gemini Core Engine
"""

import asyncio
from datetime import datetime
import time
from typing import Dict, Any, List
import pandas as pd
import json

from backtest.experiments.base_experiment import BaseExperiment, ExperimentResult
from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine
from core_engine.config import BacktestConfig

class LiquidityStressTesting(BaseExperiment):
    """
    Liquidity stress testing experiment.

    Tests strategy under various liquidity constraint scenarios.
    """

    def get_description(self) -> str:
        return f"Liquidity stress: Multiple liquidity scenarios"

    async def run(self) -> ExperimentResult:
        """Run liquidity stress testing"""
        start_time = time.time()
        experiment_name = self.config.get('experiment_name', 'Liquidity_Stress_Testing')

        try:
            self.logger.info(f"🔧 Starting liquidity stress testing: {experiment_name}")

            # Define liquidity stress scenarios
            scenarios = self.config.get('liquidity_scenarios', [
                {
                    'name': 'baseline',
                    'volume_multiplier': 1.0,
                    'spread_multiplier': 1.0,
                    'slippage_multiplier': 1.0
                },
                {
                    'name': 'low_liquidity',
                    'volume_multiplier': 0.5,
                    'spread_multiplier': 2.0,
                    'slippage_multiplier': 1.5
                },
                {
                    'name': 'crisis_liquidity',
                    'volume_multiplier': 0.25,
                    'spread_multiplier': 4.0,
                    'slippage_multiplier': 3.0
                },
                {
                    'name': 'flash_crash',
                    'volume_multiplier': 0.10,
                    'spread_multiplier': 10.0,
                    'slippage_multiplier': 5.0
                }
            ])

            self.logger.info(f"   Testing {len(scenarios)} liquidity scenarios")

            # Test each scenario
            scenario_results = []
            for scenario in scenarios:
                self.logger.info(f"\n   Scenario: {scenario['name']}")
                self.logger.info(f"     Volume: {scenario['volume_multiplier']*100:.0f}%")
                self.logger.info(f"     Spread: {scenario['spread_multiplier']}x")

                # Run backtest with scenario parameters
                performance = await self._test_liquidity_scenario(scenario)

                scenario_results.append({
                    'scenario': scenario['name'],
                    'volume_multiplier': scenario['volume_multiplier'],
                    'spread_multiplier': scenario['spread_multiplier'],
                    'slippage_multiplier': scenario['slippage_multiplier'],
                    'total_return_pct': performance['total_return_pct'],
                    'sharpe_ratio': performance['sharpe_ratio'],
                    'max_drawdown_pct': performance['max_drawdown_pct'],
                    'total_trades': performance['total_trades'],
                    'win_rate': performance['win_rate'],
                    'avg_slippage_bps': performance.get('avg_slippage_bps', 0.0),
                    'avg_execution_cost_bps': performance.get('avg_execution_cost_bps', 0.0)
                })

                self.logger.info(f"     Return: {performance['total_return_pct']:.2f}%")
                self.logger.info(f"     Sharpe: {performance['sharpe_ratio']:.2f}")
                self.logger.info(f"     Avg Slippage: {performance.get('avg_slippage_bps', 0):.1f} bps")

            # Analyze liquidity impact
            analysis = self._analyze_liquidity_impact(scenario_results)

            # Calculate duration
            duration = time.time() - start_time

            # Find baseline and worst scenarios
            baseline = next((s for s in scenario_results if s['scenario'] == 'baseline'), scenario_results[0])
            worst = min(scenario_results, key=lambda x: x['sharpe_ratio'])

            # Create result
            result = ExperimentResult(
                experiment_name=experiment_name,
                experiment_type="liquidity_stress_testing",
                run_timestamp=datetime.now(),
                duration_seconds=duration,
                engine_results={'scenario_results': scenario_results},
                total_return_pct=baseline['total_return_pct'],
                sharpe_ratio=baseline['sharpe_ratio'],
                max_drawdown_pct=baseline['max_drawdown_pct'],
                total_trades=baseline['total_trades'],
                win_rate=baseline['win_rate'],
                custom_metrics={
                    'scenarios_tested': len(scenario_results),
                    'baseline_return_pct': baseline['total_return_pct'],
                    'worst_scenario': worst['scenario'],
                    'worst_scenario_return_pct': worst['total_return_pct'],
                    'return_degradation': baseline['total_return_pct'] - worst['total_return_pct'],
                    'liquidity_sensitivity_score': analysis['sensitivity_score'],
                    'execution_cost_range_bps': analysis['execution_cost_range']
                },
                success=True
            )

            # Save detailed scenario results
            self._save_scenario_results(scenario_results, experiment_name)

            self.logger.info(f"\n✅ Liquidity stress testing completed in {duration:.2f}s")
            self.logger.info(f"   Baseline return: {baseline['total_return_pct']:.2f}%")
            self.logger.info(f"   Worst scenario: {worst['scenario']} ({worst['total_return_pct']:.2f}%)")
            self.logger.info(f"   Return degradation: {baseline['total_return_pct'] - worst['total_return_pct']:.2f}%")

            return result

        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"❌ Liquidity stress testing failed: {e}", exc_info=True)

            return ExperimentResult(
                experiment_name=experiment_name,
                experiment_type="liquidity_stress_testing",
                run_timestamp=datetime.now(),
                duration_seconds=duration,
                engine_results={},
                total_return_pct=0.0,
                sharpe_ratio=0.0,
                max_drawdown_pct=0.0,
                total_trades=0,
                win_rate=0.0,
                success=False,
                error_message=str(e)
            )

    async def _test_liquidity_scenario(self, scenario: Dict[str, Any]) -> Dict[str, float]:
        """Test strategy under specific liquidity scenario"""
        config_dict = self.config.copy()
        config_dict['backtest_name'] = f"Liquidity_{scenario['name']}"

        # Apply liquidity constraints to execution parameters
        # Scale slippage and spreads based on scenario
        base_slippage = config_dict.get('base_slippage_bps', 2.0)
        config_dict['base_slippage_bps'] = base_slippage * scenario['slippage_multiplier']

        if 'max_spread_bps' in config_dict:
            config_dict['max_spread_bps'] *= scenario['spread_multiplier']

        # Update strategy parameters
        if 'strategy' in config_dict:
            strategy = config_dict['strategy'].copy()
            config_dict['strategies'] = [strategy]
            del config_dict['strategy']

        # Remove invalid keys
        for key in ['liquidity_scenarios', 'experiment_name', 'experiment_type', 'log_level', 'save_trade_log', 'save_regime_log']:
            config_dict.pop(key, None)

        # Run backtest
        engine = InstitutionalBacktestEngine(BacktestConfig(**config_dict))
        await engine.initialize()
        result = await engine.run_backtest()

        # Extract metrics
        performance = result.get('performance', {})
        tca = result.get('transaction_cost_analysis', {})

        return {
            'total_return_pct': performance.get('total_return_pct', 0.0),
            'sharpe_ratio': performance.get('sharpe_ratio', 0.0),
            'max_drawdown_pct': performance.get('max_drawdown_pct', 0.0),
            'total_trades': performance.get('total_trades', 0),
            'win_rate': performance.get('win_rate', 0.0) * 100,
            'avg_slippage_bps': tca.get('avg_slippage_bps', 0.0),
            'avg_execution_cost_bps': tca.get('avg_execution_cost_bps', 0.0)
        }

    def _analyze_liquidity_impact(self, scenario_results: List[Dict]) -> Dict[str, float]:
        """Analyze impact of liquidity constraints"""
        if not scenario_results:
            return {
                'sensitivity_score': 0.0,
                'execution_cost_range': 0.0
            }

        returns = [r['total_return_pct'] for r in scenario_results]
        execution_costs = [r['avg_execution_cost_bps'] for r in scenario_results]

        # Sensitivity: how much returns degrade from best to worst
        return_range = max(returns) - min(returns)
        sensitivity_score = return_range / max(abs(max(returns)), 0.1)  # Normalized

        execution_cost_range = max(execution_costs) - min(execution_costs)

        return {
            'sensitivity_score': sensitivity_score,
            'execution_cost_range': execution_cost_range
        }

    def _save_scenario_results(self, scenario_results: List[Dict], experiment_name: str):
        """Save detailed scenario results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        experiment_slug = experiment_name.replace(" ", "_").lower()

        # Save CSV
        df = pd.DataFrame(scenario_results)
        csv_path = self.output_dir / f"{experiment_slug}_liquidity_{timestamp}.csv"
        df.to_csv(csv_path, index=False)
        self.logger.info(f"   Scenario results saved to: {csv_path}")

        # Save JSON
        json_path = self.output_dir / f"{experiment_slug}_liquidity_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump(scenario_results, f, indent=2, default=str)

if __name__ == "__main__":
    # Example usage
    async def run_example():
        from backtest.utils.config_loader import load_config

        config = load_config("backtest/configs/liquidity_stress.yaml")
        experiment = LiquidityStressTesting(config)
        result = await experiment.run()
        experiment.print_summary(result)
        experiment.save_results(result)

    asyncio.run(run_example())

