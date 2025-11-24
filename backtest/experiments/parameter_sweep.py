"""
Experiment 3: Parameter Sweep
==============================

Systematic parameter optimization using grid search over strategy parameters.

Purpose:
- Find optimal parameter combinations
- Understand parameter sensitivity
- Generate parameter heatmaps
- Compare performance across parameter space

Methodology:
- Grid search over specified parameter ranges
- Run backtest for each combination
- Rank results by Sharpe ratio (or custom metric)
- Generate comparison reports

Expected Duration: Varies (5-60 minutes depending on grid size)

Author: StatArb_Gemini Core Engine
"""

import asyncio
from datetime import datetime
import time
from typing import Dict, Any, List, Optional
import itertools
import pandas as pd
from pathlib import Path
import json

from backtest.experiments.base_experiment import BaseExperiment, ExperimentResult
from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine
from core_engine.config import BacktestConfig


class ParameterSweep(BaseExperiment):
    """
    Parameter sweep experiment.
    
    Runs grid search over specified parameter ranges to find optimal combinations.
    """
    
    def get_description(self) -> str:
        param_grid = self.config.get('parameter_grid', {})
        grid_size = self._calculate_grid_size(param_grid)
        return f"Parameter sweep: {grid_size} combinations ({self.config.get('experiment_name', 'N/A')})"
    
    async def run(self) -> ExperimentResult:
        """Run parameter sweep"""
        start_time = time.time()
        experiment_name = self.config.get('experiment_name', 'Parameter_Sweep')
        
        try:
            self.logger.info(f"🔧 Starting parameter sweep: {experiment_name}")
            
            # Get parameter grid
            parameter_grid = self.config.get('parameter_grid', {})
            if not parameter_grid:
                raise ValueError("No parameter_grid specified in config")
            
            # Generate parameter combinations
            param_combinations = self._generate_parameter_combinations(parameter_grid)
            total_combinations = len(param_combinations)
            
            self.logger.info(f"   Total combinations to test: {total_combinations}")
            
            # Run backtest for each combination
            sweep_results = []
            for idx, params in enumerate(param_combinations, 1):
                self.logger.info(f"\n   [{idx}/{total_combinations}] Testing parameters: {params}")
                
                # Create config for this combination
                backtest_config = self._create_backtest_config(params)
                
                # Run backtest
                try:
                    engine = InstitutionalBacktestEngine(backtest_config)
                    await engine.initialize()
                    engine_results = await engine.run_backtest()
                    
                    # Extract performance metrics
                    metrics = self._extract_performance_metrics(engine_results)
                    
                    # Store result
                    sweep_results.append({
                        'parameters': params,
                        'total_return_pct': metrics['total_return_pct'],
                        'sharpe_ratio': metrics['sharpe_ratio'],
                        'max_drawdown_pct': metrics['max_drawdown_pct'],
                        'total_trades': metrics['total_trades'],
                        'win_rate': metrics['win_rate'],
                        'engine_results': engine_results
                    })
                    
                    self.logger.info(f"      Return: {metrics['total_return_pct']:.2f}% | "
                                   f"Sharpe: {metrics['sharpe_ratio']:.2f} | "
                                   f"Trades: {metrics['total_trades']}")
                    
                except Exception as e:
                    self.logger.error(f"      Failed: {e}")
                    sweep_results.append({
                        'parameters': params,
                        'total_return_pct': 0.0,
                        'sharpe_ratio': 0.0,
                        'max_drawdown_pct': 0.0,
                        'total_trades': 0,
                        'win_rate': 0.0,
                        'error': str(e)
                    })
            
            # Analyze results
            analysis = self._analyze_sweep_results(sweep_results)
            
            # Find best combination
            best_result = max(sweep_results, key=lambda x: x['sharpe_ratio'])
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Create result
            result = ExperimentResult(
                experiment_name=experiment_name,
                experiment_type="parameter_sweep",
                run_timestamp=datetime.now(),
                duration_seconds=duration,
                engine_results=best_result.get('engine_results', {}),
                total_return_pct=best_result['total_return_pct'],
                sharpe_ratio=best_result['sharpe_ratio'],
                max_drawdown_pct=best_result['max_drawdown_pct'],
                total_trades=best_result['total_trades'],
                win_rate=best_result['win_rate'],
                custom_metrics={
                    'total_combinations_tested': total_combinations,
                    'best_parameters': best_result['parameters'],
                    'best_sharpe_ratio': best_result['sharpe_ratio'],
                    'best_return_pct': best_result['total_return_pct'],
                    'parameter_sensitivity': analysis['sensitivity'],
                    'top_5_combinations': analysis['top_5']
                },
                success=True
            )
            
            # Save detailed sweep results
            self._save_sweep_results(sweep_results, experiment_name)
            
            self.logger.info(f"\n✅ Parameter sweep completed in {duration:.2f}s")
            self.logger.info(f"   Best parameters: {best_result['parameters']}")
            self.logger.info(f"   Best Sharpe ratio: {best_result['sharpe_ratio']:.2f}")
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"❌ Parameter sweep failed: {e}", exc_info=True)
            
            return ExperimentResult(
                experiment_name=experiment_name,
                experiment_type="parameter_sweep",
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
    
    def _calculate_grid_size(self, parameter_grid: Dict[str, List]) -> int:
        """Calculate total number of combinations in grid"""
        if not parameter_grid:
            return 0
        return sum(1 for _ in itertools.product(*parameter_grid.values()))
    
    def _generate_parameter_combinations(self, parameter_grid: Dict[str, List]) -> List[Dict[str, Any]]:
        """Generate all parameter combinations from grid"""
        keys = list(parameter_grid.keys())
        values = list(parameter_grid.values())
        
        combinations = []
        for combination in itertools.product(*values):
            param_dict = dict(zip(keys, combination))
            combinations.append(param_dict)
        
        return combinations
    
    def _create_backtest_config(self, parameters: Dict[str, Any]) -> BacktestConfig:
        """Create backtest config with specific parameters"""
        config_dict = self.config.copy()
        
        # Ensure backtest_name is set (required parameter)
        if 'backtest_name' not in config_dict:
            config_dict['backtest_name'] = self.config.get('experiment_name', 'Parameter_Sweep')
        
        # Update strategy parameters
        if 'strategy' in config_dict:
            strategy_config = config_dict['strategy'].copy()
            if 'parameters' not in strategy_config:
                strategy_config['parameters'] = {}
            
            # Merge sweep parameters into strategy parameters
            strategy_config['parameters'].update(parameters)
            config_dict['strategies'] = [strategy_config]
            del config_dict['strategy']
        
        # Remove experiment-specific keys that aren't valid BacktestConfig parameters
        # Keep backtest_name as it's required
        invalid_keys = [
            'parameter_grid', 'experiment_name', 'experiment_type',
            'log_level', 'save_trade_log', 'save_regime_log'
        ]
        for key in invalid_keys:
            config_dict.pop(key, None)
        
        return BacktestConfig(**config_dict)
    
    def _analyze_sweep_results(self, sweep_results: List[Dict]) -> Dict[str, Any]:
        """Analyze sweep results for parameter sensitivity"""
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(sweep_results)
        
        # Parameter sensitivity analysis
        sensitivity = {}
        for param_name in sweep_results[0]['parameters'].keys():
            # Extract parameter values
            param_values = [r['parameters'][param_name] for r in sweep_results]
            sharpe_values = [r['sharpe_ratio'] for r in sweep_results]
            
            # Calculate correlation (simple measure of sensitivity)
            if len(set(param_values)) > 1:  # Only if parameter varies
                param_df = pd.DataFrame({'param': param_values, 'sharpe': sharpe_values})
                correlation = param_df['param'].corr(param_df['sharpe'])
                sensitivity[param_name] = correlation
            else:
                sensitivity[param_name] = 0.0
        
        # Top 5 combinations
        sorted_results = sorted(sweep_results, key=lambda x: x['sharpe_ratio'], reverse=True)
        top_5 = [
            {
                'rank': idx + 1,
                'parameters': r['parameters'],
                'sharpe_ratio': r['sharpe_ratio'],
                'return_pct': r['total_return_pct']
            }
            for idx, r in enumerate(sorted_results[:5])
        ]
        
        return {
            'sensitivity': sensitivity,
            'top_5': top_5
        }
    
    def _save_sweep_results(self, sweep_results: List[Dict], experiment_name: str):
        """Save detailed sweep results to CSV and JSON"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        experiment_slug = experiment_name.replace(" ", "_").lower()
        
        # Flatten parameters for CSV
        rows = []
        for result in sweep_results:
            row = result['parameters'].copy()
            row.update({
                'total_return_pct': result['total_return_pct'],
                'sharpe_ratio': result['sharpe_ratio'],
                'max_drawdown_pct': result['max_drawdown_pct'],
                'total_trades': result['total_trades'],
                'win_rate': result['win_rate']
            })
            rows.append(row)
        
        # Save CSV
        df = pd.DataFrame(rows)
        csv_path = self.output_dir / f"{experiment_slug}_sweep_{timestamp}.csv"
        df.to_csv(csv_path, index=False)
        self.logger.info(f"   Sweep results saved to: {csv_path}")
        
        # Save JSON (full results)
        json_path = self.output_dir / f"{experiment_slug}_sweep_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump(sweep_results, f, indent=2, default=str)


# Standalone run function
async def run_parameter_sweep(config: Dict[str, Any] = None):
    """
    Run parameter sweep experiment.
    
    Args:
        config: Optional config dict (uses defaults if None)
    """
    if config is None:
        # Example config
        config = {
            'experiment_name': 'Parameter_Sweep_MeanReversion',
            'symbols': ['AAPL'],
            'start_date': '2024-01-03',
            'end_date': '2024-01-03',
            'parameter_grid': {
                'zscore_entry_threshold': [1.5, 2.0, 2.5],
                'zscore_exit_threshold': [0.3, 0.5, 0.7],
                'base_position_pct': [0.01, 0.02, 0.03]
            }
        }
    
    experiment = ParameterSweep(config)
    result = await experiment.run()
    
    # Print summary
    experiment.print_summary(result)
    
    # Save results
    experiment.save_results(result)
    
    return result


if __name__ == "__main__":
    # Run parameter sweep directly
    result = asyncio.run(run_parameter_sweep())
    exit(0 if result.success else 1)

