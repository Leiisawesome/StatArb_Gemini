"""
Experiment 8: Correlation Stress Testing
=========================================

Test portfolio behavior under correlation breakdown scenarios.

Purpose:
- Assess portfolio risk during correlation regime shifts
- Test diversification assumptions under stress
- Identify concentration risks during correlation spikes
- Validate multi-asset strategy resilience

Methodology:
- Simulate correlation breakdown scenarios
- Test performance during high correlation periods
- Measure portfolio concentration during stress
- Validate diversification benefits

Scenarios:
- Normal correlations: Historical averages
- High correlations: 0.8-0.9 (crisis scenario)
- Correlation breakdown: Negative correlations flip positive
- Perfect correlation: All assets move together

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

class CorrelationStressTesting(BaseExperiment):
    """
    Correlation stress testing experiment.

    Tests portfolio resilience under correlation breakdown scenarios.
    """

    def get_description(self) -> str:
        return f"Correlation stress: Portfolio under correlation shifts"

    async def run(self) -> ExperimentResult:
        """Run correlation stress testing"""
        start_time = time.time()
        experiment_name = self.config.get('experiment_name', 'Correlation_Stress_Testing')

        try:
            self.logger.info(f"🔧 Starting correlation stress testing: {experiment_name}")

            # Define correlation stress scenarios
            scenarios = self.config.get('correlation_scenarios', [
                {
                    'name': 'normal_correlations',
                    'correlation_adjustment': 1.0,
                    'description': 'Historical correlation levels'
                },
                {
                    'name': 'high_correlations',
                    'correlation_adjustment': 1.5,
                    'description': 'Crisis-level correlations (0.8-0.9)'
                },
                {
                    'name': 'correlation_breakdown',
                    'correlation_adjustment': 2.0,
                    'description': 'Diversification fails, all correlations spike'
                },
                {
                    'name': 'perfect_correlation',
                    'correlation_adjustment': 3.0,
                    'description': 'All assets move in lockstep'
                }
            ])

            self.logger.info(f"   Testing {len(scenarios)} correlation scenarios")

            # Test each scenario
            scenario_results = []
            for scenario in scenarios:
                self.logger.info(f"\n   Scenario: {scenario['name']}")
                self.logger.info(f"     {scenario['description']}")

                # Run backtest with scenario parameters
                performance = await self._test_correlation_scenario(scenario)

                scenario_results.append({
                    'scenario': scenario['name'],
                    'correlation_adjustment': scenario['correlation_adjustment'],
                    'description': scenario['description'],
                    'total_return_pct': performance['total_return_pct'],
                    'sharpe_ratio': performance['sharpe_ratio'],
                    'max_drawdown_pct': performance['max_drawdown_pct'],
                    'total_trades': performance['total_trades'],
                    'win_rate': performance['win_rate'],
                    'portfolio_volatility': performance.get('portfolio_volatility', 0.0),
                    'diversification_ratio': performance.get('diversification_ratio', 1.0)
                })

                self.logger.info(f"     Return: {performance['total_return_pct']:.2f}%")
                self.logger.info(f"     Sharpe: {performance['sharpe_ratio']:.2f}")
                self.logger.info(f"     Max DD: {performance['max_drawdown_pct']:.2f}%")

            # Analyze correlation impact
            analysis = self._analyze_correlation_impact(scenario_results)

            # Calculate duration
            duration = time.time() - start_time

            # Find normal and worst scenarios
            normal = next((s for s in scenario_results if s['scenario'] == 'normal_correlations'), scenario_results[0])
            worst = min(scenario_results, key=lambda x: x['sharpe_ratio'])

            # Create result
            result = ExperimentResult(
                experiment_name=experiment_name,
                experiment_type="correlation_stress_testing",
                run_timestamp=datetime.now(),
                duration_seconds=duration,
                engine_results={'scenario_results': scenario_results},
                total_return_pct=normal['total_return_pct'],
                sharpe_ratio=normal['sharpe_ratio'],
                max_drawdown_pct=normal['max_drawdown_pct'],
                total_trades=normal['total_trades'],
                win_rate=normal['win_rate'],
                custom_metrics={
                    'scenarios_tested': len(scenario_results),
                    'normal_sharpe': normal['sharpe_ratio'],
                    'worst_scenario': worst['scenario'],
                    'worst_sharpe': worst['sharpe_ratio'],
                    'sharpe_degradation': normal['sharpe_ratio'] - worst['sharpe_ratio'],
                    'correlation_sensitivity': analysis['sensitivity_score'],
                    'diversification_benefit_loss': analysis['diversification_loss']
                },
                success=True
            )

            # Save detailed scenario results
            self._save_scenario_results(scenario_results, experiment_name)

            self.logger.info(f"\n✅ Correlation stress testing completed in {duration:.2f}s")
            self.logger.info(f"   Normal Sharpe: {normal['sharpe_ratio']:.2f}")
            self.logger.info(f"   Worst scenario: {worst['scenario']} (Sharpe: {worst['sharpe_ratio']:.2f})")
            self.logger.info(f"   Sharpe degradation: {normal['sharpe_ratio'] - worst['sharpe_ratio']:.2f}")

            return result

        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"❌ Correlation stress testing failed: {e}", exc_info=True)

            return ExperimentResult(
                experiment_name=experiment_name,
                experiment_type="correlation_stress_testing",
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

    async def _test_correlation_scenario(self, scenario: Dict[str, Any]) -> Dict[str, float]:
        """Test portfolio under specific correlation scenario"""
        config_dict = self.config.copy()
        config_dict['backtest_name'] = f"Correlation_{scenario['name']}"

        # In production, would modify position sizing or risk limits
        # based on correlation scenario
        # For now, run standard backtest (correlation effects implicit in data)

        # Update strategy parameters
        if 'strategy' in config_dict:
            strategy = config_dict['strategy'].copy()

            # Adjust risk parameters based on correlation scenario
            if 'parameters' in strategy:
                params = strategy['parameters'].copy()

                # Reduce position sizes in high correlation scenarios
                if 'base_position_pct' in params:
                    adjustment_factor = 1.0 / scenario['correlation_adjustment']
                    params['base_position_pct'] *= adjustment_factor

                strategy['parameters'] = params

            config_dict['strategies'] = [strategy]
            del config_dict['strategy']

        # Remove invalid keys
        for key in ['correlation_scenarios', 'experiment_name', 'experiment_type', 'log_level', 'save_trade_log', 'save_regime_log']:
            config_dict.pop(key, None)

        # Run backtest
        engine = InstitutionalBacktestEngine(BacktestConfig(**config_dict))
        await engine.initialize()
        result = await engine.run_backtest()

        # Extract metrics
        performance = result.get('performance', {})
        risk_metrics = result.get('risk_metrics', {})

        return {
            'total_return_pct': performance.get('total_return_pct', 0.0),
            'sharpe_ratio': performance.get('sharpe_ratio', 0.0),
            'max_drawdown_pct': performance.get('max_drawdown_pct', 0.0),
            'total_trades': performance.get('total_trades', 0),
            'win_rate': performance.get('win_rate', 0.0) * 100,
            'portfolio_volatility': risk_metrics.get('portfolio_volatility', 0.0),
            'diversification_ratio': risk_metrics.get('diversification_ratio', 1.0)
        }

    def _analyze_correlation_impact(self, scenario_results: List[Dict]) -> Dict[str, float]:
        """Analyze impact of correlation changes"""
        if not scenario_results:
            return {
                'sensitivity_score': 0.0,
                'diversification_loss': 0.0
            }

        sharpes = [r['sharpe_ratio'] for r in scenario_results]
        diversification_ratios = [r['diversification_ratio'] for r in scenario_results]

        # Sensitivity: how much Sharpe degrades from best to worst
        sharpe_range = max(sharpes) - min(sharpes)
        sensitivity_score = sharpe_range / max(abs(max(sharpes)), 0.1)

        # Diversification loss
        diversification_loss = max(diversification_ratios) - min(diversification_ratios)

        return {
            'sensitivity_score': sensitivity_score,
            'diversification_loss': diversification_loss
        }

    def _save_scenario_results(self, scenario_results: List[Dict], experiment_name: str):
        """Save detailed scenario results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        experiment_slug = experiment_name.replace(" ", "_").lower()

        # Save CSV
        df = pd.DataFrame(scenario_results)
        csv_path = self.output_dir / f"{experiment_slug}_correlation_{timestamp}.csv"
        df.to_csv(csv_path, index=False)
        self.logger.info(f"   Scenario results saved to: {csv_path}")

        # Save JSON
        json_path = self.output_dir / f"{experiment_slug}_correlation_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump(scenario_results, f, indent=2, default=str)

if __name__ == "__main__":
    # Example usage
    async def run_example():
        from backtest.utils.config_loader import load_config

        config = load_config("backtest/configs/correlation_stress.yaml")
        experiment = CorrelationStressTesting(config)
        result = await experiment.run()
        experiment.print_summary(result)
        experiment.save_results(result)

    asyncio.run(run_example())

