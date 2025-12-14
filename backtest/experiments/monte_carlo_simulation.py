"""
Experiment 5: Monte Carlo Simulation
=====================================

Probabilistic outcome distribution using random parameter sampling.

Purpose:
- Assess strategy robustness across parameter space
- Generate probability distribution of outcomes
- Identify tail risks and worst-case scenarios
- Complement grid search with broader exploration

Methodology:
- Random sampling from parameter distributions
- Run N simulations (e.g., 100-1000)
- Generate statistical distribution of results
- Calculate confidence intervals and percentiles

Expected Duration: 10-60 minutes (depending on N simulations)

Author: StatArb_Gemini Core Engine
"""

import asyncio
from datetime import datetime
import time
from typing import Dict, Any, List
import numpy as np
import pandas as pd
import json

from backtest.experiments.base_experiment import BaseExperiment, ExperimentResult
from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine
from core_engine.config import BacktestConfig

class MonteCarloSimulation(BaseExperiment):
    """
    Monte Carlo simulation experiment.

    Tests strategy with random parameter sampling to assess robustness.
    """

    def get_description(self) -> str:
        n_simulations = self.config.get('monte_carlo', {}).get('n_simulations', 'N/A')
        return f"Monte Carlo: {n_simulations} random simulations"

    async def run(self) -> ExperimentResult:
        """Run Monte Carlo simulation"""
        start_time = time.time()
        experiment_name = self.config.get('experiment_name', 'Monte_Carlo_Simulation')

        try:
            self.logger.info(f"🔧 Starting Monte Carlo simulation: {experiment_name}")

            # Get Monte Carlo configuration
            mc_config = self.config.get('monte_carlo', {})
            n_simulations = mc_config.get('n_simulations', 100)

            # Get parameter distributions
            param_distributions = self.config.get('parameter_distributions', {})
            if not param_distributions:
                raise ValueError("No parameter_distributions specified")

            self.logger.info(f"   Configuration:")
            self.logger.info(f"     Simulations: {n_simulations}")
            self.logger.info(f"     Parameters: {list(param_distributions.keys())}")

            # Run Monte Carlo simulations
            mc_results = []
            for sim_idx in range(1, n_simulations + 1):
                if sim_idx % 10 == 0:
                    self.logger.info(f"   Progress: {sim_idx}/{n_simulations} simulations...")

                # Sample random parameters
                params = self._sample_parameters(param_distributions)

                # Run backtest with sampled parameters
                try:
                    result = await self._run_simulation(params, sim_idx)

                    mc_results.append({
                        'simulation': sim_idx,
                        'parameters': params,
                        'total_return_pct': result['total_return_pct'],
                        'sharpe_ratio': result['sharpe_ratio'],
                        'max_drawdown_pct': result['max_drawdown_pct'],
                        'total_trades': result['total_trades'],
                        'win_rate': result['win_rate']
                    })

                except Exception as e:
                    self.logger.warning(f"     Simulation {sim_idx} failed: {e}")
                    mc_results.append({
                        'simulation': sim_idx,
                        'parameters': params,
                        'total_return_pct': 0.0,
                        'sharpe_ratio': 0.0,
                        'max_drawdown_pct': 0.0,
                        'total_trades': 0,
                        'win_rate': 0.0,
                        'error': str(e)
                    })

            # Analyze Monte Carlo results
            analysis = self._analyze_monte_carlo_results(mc_results)

            # Calculate duration
            duration = time.time() - start_time

            # Create result
            result = ExperimentResult(
                experiment_name=experiment_name,
                experiment_type="monte_carlo_simulation",
                run_timestamp=datetime.now(),
                duration_seconds=duration,
                engine_results={'monte_carlo_simulations': mc_results},
                total_return_pct=analysis['mean_return_pct'],
                sharpe_ratio=analysis['mean_sharpe'],
                max_drawdown_pct=analysis['worst_drawdown'],
                total_trades=int(analysis['mean_trades']),
                win_rate=analysis['mean_win_rate'],
                custom_metrics={
                    'n_simulations': n_simulations,
                    'successful_simulations': analysis['successful_sims'],
                    'median_return_pct': analysis['median_return_pct'],
                    'return_std_pct': analysis['return_std_pct'],
                    'percentile_5_return': analysis['percentile_5_return'],
                    'percentile_95_return': analysis['percentile_95_return'],
                    'probability_positive': analysis['prob_positive'],
                    'var_95': analysis['var_95'],
                    'best_return_pct': analysis['best_return_pct'],
                    'worst_return_pct': analysis['worst_return_pct']
                },
                success=True
            )

            # Save detailed MC results
            self._save_monte_carlo_results(mc_results, analysis, experiment_name)

            self.logger.info(f"\n✅ Monte Carlo simulation completed in {duration:.2f}s")
            self.logger.info(f"   Mean return: {analysis['mean_return_pct']:.2f}%")
            self.logger.info(f"   Median return: {analysis['median_return_pct']:.2f}%")
            self.logger.info(f"   95% VaR: {analysis['var_95']:.2f}%")
            self.logger.info(f"   Probability of profit: {analysis['prob_positive']:.1f}%")

            return result

        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"❌ Monte Carlo simulation failed: {e}", exc_info=True)

            return ExperimentResult(
                experiment_name=experiment_name,
                experiment_type="monte_carlo_simulation",
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

    def _sample_parameters(self, distributions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Sample random parameters from distributions"""
        params = {}

        for param_name, dist_config in distributions.items():
            dist_type = dist_config.get('type', 'uniform')

            if dist_type == 'uniform':
                # Uniform distribution
                low = dist_config['min']
                high = dist_config['max']
                value = np.random.uniform(low, high)

            elif dist_type == 'normal':
                # Normal distribution
                mean = dist_config['mean']
                std = dist_config['std']
                value = np.random.normal(mean, std)

                # Clip to bounds if provided
                if 'min' in dist_config:
                    value = max(value, dist_config['min'])
                if 'max' in dist_config:
                    value = min(value, dist_config['max'])

            elif dist_type == 'choice':
                # Discrete choice
                choices = dist_config['choices']
                value = np.random.choice(choices)

            else:
                raise ValueError(f"Unknown distribution type: {dist_type}")

            # Round if integer type
            if dist_config.get('dtype') == 'int':
                value = int(round(value))

            params[param_name] = value

        return params

    async def _run_simulation(self, params: Dict[str, Any], sim_idx: int) -> Dict[str, float]:
        """Run single simulation with given parameters"""
        config_dict = self.config.copy()
        config_dict['backtest_name'] = f"MC_Sim_{sim_idx}"

        # Update strategy parameters
        if 'strategy' in config_dict:
            strategy = config_dict['strategy'].copy()
            if 'parameters' not in strategy:
                strategy['parameters'] = {}
            strategy['parameters'].update(params)
            config_dict['strategies'] = [strategy]
            del config_dict['strategy']

        # Remove invalid keys
        for key in ['monte_carlo', 'parameter_distributions', 'experiment_name', 'experiment_type', 'log_level', 'save_trade_log', 'save_regime_log']:
            config_dict.pop(key, None)

        # Run backtest
        engine = InstitutionalBacktestEngine(BacktestConfig(**config_dict))
        await engine.initialize()
        result = await engine.run_backtest()

        # Extract metrics
        performance = result.get('performance', {})
        return {
            'total_return_pct': performance.get('total_return_pct', 0.0),
            'sharpe_ratio': performance.get('sharpe_ratio', 0.0),
            'max_drawdown_pct': performance.get('max_drawdown_pct', 0.0),
            'total_trades': performance.get('total_trades', 0),
            'win_rate': performance.get('win_rate', 0.0) * 100
        }

    def _analyze_monte_carlo_results(self, mc_results: List[Dict]) -> Dict[str, float]:
        """Analyze Monte Carlo simulation results"""
        # Extract returns
        returns = [r['total_return_pct'] for r in mc_results if 'error' not in r]
        sharpes = [r['sharpe_ratio'] for r in mc_results if 'error' not in r]

        if not returns:
            return {
                'mean_return_pct': 0.0,
                'median_return_pct': 0.0,
                'return_std_pct': 0.0,
                'mean_sharpe': 0.0,
                'worst_drawdown': 0.0,
                'mean_trades': 0,
                'mean_win_rate': 0.0,
                'successful_sims': 0,
                'percentile_5_return': 0.0,
                'percentile_95_return': 0.0,
                'prob_positive': 0.0,
                'var_95': 0.0,
                'best_return_pct': 0.0,
                'worst_return_pct': 0.0
            }

        return {
            'mean_return_pct': np.mean(returns),
            'median_return_pct': np.median(returns),
            'return_std_pct': np.std(returns),
            'mean_sharpe': np.mean(sharpes),
            'worst_drawdown': max([r['max_drawdown_pct'] for r in mc_results if 'error' not in r]),
            'mean_trades': np.mean([r['total_trades'] for r in mc_results if 'error' not in r]),
            'mean_win_rate': np.mean([r['win_rate'] for r in mc_results if 'error' not in r]),
            'successful_sims': len(returns),
            'percentile_5_return': np.percentile(returns, 5),
            'percentile_95_return': np.percentile(returns, 95),
            'prob_positive': len([r for r in returns if r > 0]) / len(returns) * 100,
            'var_95': np.percentile(returns, 5),  # Value at Risk (5th percentile)
            'best_return_pct': max(returns),
            'worst_return_pct': min(returns)
        }

    def _save_monte_carlo_results(self, mc_results: List[Dict], analysis: Dict[str, float], experiment_name: str):
        """Save detailed Monte Carlo results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        experiment_slug = experiment_name.replace(" ", "_").lower()

        # Save CSV
        df = pd.DataFrame([{
            'simulation': r['simulation'],
            **r['parameters'],
            'total_return_pct': r['total_return_pct'],
            'sharpe_ratio': r['sharpe_ratio'],
            'max_drawdown_pct': r['max_drawdown_pct'],
            'total_trades': r['total_trades'],
            'win_rate': r['win_rate']
        } for r in mc_results])

        csv_path = self.output_dir / f"{experiment_slug}_mc_{timestamp}.csv"
        df.to_csv(csv_path, index=False)
        self.logger.info(f"   Monte Carlo results saved to: {csv_path}")

        # Save JSON with analysis
        json_path = self.output_dir / f"{experiment_slug}_mc_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump({
                'simulations': mc_results,
                'analysis': analysis
            }, f, indent=2, default=str)

if __name__ == "__main__":
    # Example usage
    async def run_example():
        from backtest.utils.config_loader import load_config

        config = load_config("backtest/configs/monte_carlo.yaml")
        experiment = MonteCarloSimulation(config)
        result = await experiment.run()
        experiment.print_summary(result)
        experiment.save_results(result)

    asyncio.run(run_example())

