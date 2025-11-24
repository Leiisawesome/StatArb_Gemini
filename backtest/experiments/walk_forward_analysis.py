"""
Experiment 4: Walk-Forward Analysis
====================================

Out-of-sample testing methodology to validate strategy robustness.

Purpose:
- Test strategy on unseen data
- Prevent overfitting
- Validate parameter stability across time periods
- Measure strategy degradation

Methodology:
- Split period into training + testing windows
- Optimize on training window
- Test on following out-of-sample window
- Roll forward and repeat

Expected Duration: Varies (10-90 minutes depending on windows)

Author: StatArb_Gemini Core Engine
"""

import asyncio
from datetime import datetime, timedelta
import time
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
from pathlib import Path
import json

from backtest.experiments.base_experiment import BaseExperiment, ExperimentResult
from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine
from core_engine.config import BacktestConfig
import itertools


class WalkForwardAnalysis(BaseExperiment):
    """
    Walk-forward analysis experiment.
    
    Tests strategy on out-of-sample periods using rolling train/test windows.
    """
    
    def get_description(self) -> str:
        windows = self.config.get('walk_forward', {}).get('num_windows', 'N/A')
        train_days = self.config.get('walk_forward', {}).get('train_days', 'N/A')
        test_days = self.config.get('walk_forward', {}).get('test_days', 'N/A')
        return f"Walk-forward: {windows} windows ({train_days}d train, {test_days}d test)"
    
    async def run(self) -> ExperimentResult:
        """Run walk-forward analysis"""
        start_time = time.time()
        experiment_name = self.config.get('experiment_name', 'Walk_Forward_Analysis')
        
        try:
            self.logger.info(f"🔧 Starting walk-forward analysis: {experiment_name}")
            
            # Get walk-forward configuration
            wf_config = self.config.get('walk_forward', {})
            train_days = wf_config.get('train_days', 30)
            test_days = wf_config.get('test_days', 7)
            num_windows = wf_config.get('num_windows', 4)
            
            # Get parameter grid for optimization
            param_grid = self.config.get('parameter_grid', {})
            if not param_grid:
                raise ValueError("No parameter_grid specified for optimization")
            
            self.logger.info(f"   Configuration:")
            self.logger.info(f"     Training window: {train_days} days")
            self.logger.info(f"     Testing window: {test_days} days")
            self.logger.info(f"     Number of windows: {num_windows}")
            self.logger.info(f"     Parameter combinations: {self._calculate_grid_size(param_grid)}")
            
            # Generate walk-forward windows
            windows = self._generate_walk_forward_windows(train_days, test_days, num_windows)
            
            # Run walk-forward analysis
            wf_results = []
            for window_idx, (train_start, train_end, test_start, test_end) in enumerate(windows, 1):
                self.logger.info(f"\n   Window {window_idx}/{num_windows}:")
                self.logger.info(f"     Train: {train_start} to {train_end}")
                self.logger.info(f"     Test:  {test_start} to {test_end}")
                
                # PHASE 1: Optimize on training period
                self.logger.info(f"     [1/2] Optimizing on training period...")
                best_params = await self._optimize_on_period(
                    train_start, train_end, param_grid, window_idx
                )
                self.logger.info(f"     Best parameters: {best_params}")
                
                # PHASE 2: Test on out-of-sample period
                self.logger.info(f"     [2/2] Testing on out-of-sample period...")
                test_result = await self._test_on_period(
                    test_start, test_end, best_params, window_idx
                )
                
                wf_results.append({
                    'window': window_idx,
                    'train_period': f"{train_start} to {train_end}",
                    'test_period': f"{test_start} to {test_end}",
                    'best_parameters': best_params,
                    'test_return_pct': test_result['total_return_pct'],
                    'test_sharpe': test_result['sharpe_ratio'],
                    'test_drawdown': test_result['max_drawdown_pct'],
                    'test_trades': test_result['total_trades']
                })
                
                self.logger.info(f"     Test performance: Return={test_result['total_return_pct']:.2f}%, "
                              f"Sharpe={test_result['sharpe_ratio']:.2f}")
            
            # Aggregate results
            aggregate_metrics = self._aggregate_walk_forward_results(wf_results)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Create result
            result = ExperimentResult(
                experiment_name=experiment_name,
                experiment_type="walk_forward_analysis",
                run_timestamp=datetime.now(),
                duration_seconds=duration,
                engine_results={'walk_forward_windows': wf_results},
                total_return_pct=aggregate_metrics['avg_return_pct'],
                sharpe_ratio=aggregate_metrics['avg_sharpe'],
                max_drawdown_pct=aggregate_metrics['worst_drawdown'],
                total_trades=aggregate_metrics['total_trades'],
                win_rate=aggregate_metrics['win_rate'],
                custom_metrics={
                    'num_windows': num_windows,
                    'train_days': train_days,
                    'test_days': test_days,
                    'consistent_windows': aggregate_metrics['consistent_windows'],
                    'parameter_stability': aggregate_metrics['param_stability'],
                    'oos_performance_ratio': aggregate_metrics['oos_ratio'],
                    'walk_forward_efficiency': aggregate_metrics['wf_efficiency']
                },
                success=True
            )
            
            # Save detailed WF results
            self._save_walk_forward_results(wf_results, experiment_name)
            
            self.logger.info(f"\n✅ Walk-forward analysis completed in {duration:.2f}s")
            self.logger.info(f"   Average OOS return: {aggregate_metrics['avg_return_pct']:.2f}%")
            self.logger.info(f"   Average OOS Sharpe: {aggregate_metrics['avg_sharpe']:.2f}")
            self.logger.info(f"   Consistent windows: {aggregate_metrics['consistent_windows']}/{num_windows}")
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"❌ Walk-forward analysis failed: {e}", exc_info=True)
            
            return ExperimentResult(
                experiment_name=experiment_name,
                experiment_type="walk_forward_analysis",
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
    
    def _generate_walk_forward_windows(self, train_days: int, test_days: int, 
                                      num_windows: int) -> List[Tuple[str, str, str, str]]:
        """Generate walk-forward window dates"""
        from datetime import datetime, timedelta
        
        # Parse start and end dates from config
        overall_start = datetime.strptime(self.config['start_date'], '%Y-%m-%d')
        overall_end = datetime.strptime(self.config['end_date'], '%Y-%m-%d')
        
        windows = []
        current_start = overall_start
        
        for i in range(num_windows):
            # Training period
            train_start = current_start
            train_end = train_start + timedelta(days=train_days)
            
            # Testing period
            test_start = train_end
            test_end = test_start + timedelta(days=test_days)
            
            # Check if we exceed overall end date
            if test_end > overall_end:
                break
            
            windows.append((
                train_start.strftime('%Y-%m-%d'),
                train_end.strftime('%Y-%m-%d'),
                test_start.strftime('%Y-%m-%d'),
                test_end.strftime('%Y-%m-%d')
            ))
            
            # Move to next window
            current_start = test_start  # Start next train period at end of test period
        
        return windows
    
    async def _optimize_on_period(self, start_date: str, end_date: str,
                                 param_grid: Dict[str, List], 
                                 window_idx: int) -> Dict[str, Any]:
        """Optimize parameters on training period (grid search)"""
        param_combinations = list(itertools.product(*param_grid.values()))
        best_sharpe = -999
        best_params = {}
        
        for params_tuple in param_combinations:
            params = dict(zip(param_grid.keys(), params_tuple))
            
            # Create config for this combination
            config_dict = self.config.copy()
            config_dict['start_date'] = start_date
            config_dict['end_date'] = end_date
            config_dict['backtest_name'] = f"WF_Train_Window{window_idx}"
            
            # Update strategy parameters
            if 'strategy' in config_dict:
                strategy = config_dict['strategy'].copy()
                if 'parameters' not in strategy:
                    strategy['parameters'] = {}
                strategy['parameters'].update(params)
                config_dict['strategies'] = [strategy]
                del config_dict['strategy']
            
            # Remove invalid keys
            for key in ['walk_forward', 'parameter_grid', 'experiment_name', 'experiment_type', 'log_level', 'save_trade_log', 'save_regime_log']:
                config_dict.pop(key, None)
            
            try:
                # Run backtest
                engine = InstitutionalBacktestEngine(BacktestConfig(**config_dict))
                await engine.initialize()
                result = await engine.run_backtest()
                
                # Extract Sharpe ratio
                sharpe = result.get('performance', {}).get('sharpe_ratio', 0.0)
                
                if sharpe > best_sharpe:
                    best_sharpe = sharpe
                    best_params = params
                    
            except Exception as e:
                self.logger.warning(f"       Optimization failed for {params}: {e}")
                continue
        
        return best_params
    
    async def _test_on_period(self, start_date: str, end_date: str,
                             params: Dict[str, Any], window_idx: int) -> Dict[str, float]:
        """Test parameters on out-of-sample period"""
        config_dict = self.config.copy()
        config_dict['start_date'] = start_date
        config_dict['end_date'] = end_date
        config_dict['backtest_name'] = f"WF_Test_Window{window_idx}"
        
        # Update strategy parameters
        if 'strategy' in config_dict:
            strategy = config_dict['strategy'].copy()
            if 'parameters' not in strategy:
                strategy['parameters'] = {}
            strategy['parameters'].update(params)
            config_dict['strategies'] = [strategy]
            del config_dict['strategy']
        
        # Remove invalid keys
        for key in ['walk_forward', 'parameter_grid', 'experiment_name', 'experiment_type', 'log_level', 'save_trade_log', 'save_regime_log']:
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
            'total_trades': performance.get('total_trades', 0)
        }
    
    def _calculate_grid_size(self, param_grid: Dict[str, List]) -> int:
        """Calculate total combinations in grid"""
        return sum(1 for _ in itertools.product(*param_grid.values()))
    
    def _aggregate_walk_forward_results(self, wf_results: List[Dict]) -> Dict[str, float]:
        """Aggregate walk-forward results"""
        if not wf_results:
            return {}
        
        returns = [r['test_return_pct'] for r in wf_results]
        sharpes = [r['test_sharpe'] for r in wf_results]
        
        return {
            'avg_return_pct': sum(returns) / len(returns),
            'avg_sharpe': sum(sharpes) / len(sharpes),
            'worst_drawdown': max([r['test_drawdown'] for r in wf_results]),
            'total_trades': sum([r['test_trades'] for r in wf_results]),
            'win_rate': len([r for r in wf_results if r['test_return_pct'] > 0]) / len(wf_results) * 100,
            'consistent_windows': len([r for r in wf_results if r['test_return_pct'] > 0]),
            'param_stability': self._calculate_param_stability(wf_results),
            'oos_ratio': sum(returns) / len(returns) if len(returns) > 0 else 0,
            'wf_efficiency': len([r for r in wf_results if r['test_sharpe'] > 0]) / len(wf_results) if len(wf_results) > 0 else 0
        }
    
    def _calculate_param_stability(self, wf_results: List[Dict]) -> float:
        """Calculate parameter stability score (0-1)"""
        if len(wf_results) < 2:
            return 1.0
        
        # Count parameter changes between windows
        param_changes = 0
        total_params = 0
        
        for i in range(1, len(wf_results)):
            prev_params = wf_results[i-1]['best_parameters']
            curr_params = wf_results[i]['best_parameters']
            
            for key in prev_params.keys():
                total_params += 1
                if prev_params[key] != curr_params[key]:
                    param_changes += 1
        
        if total_params == 0:
            return 1.0
        
        return 1.0 - (param_changes / total_params)
    
    def _save_walk_forward_results(self, wf_results: List[Dict], experiment_name: str):
        """Save detailed walk-forward results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        experiment_slug = experiment_name.replace(" ", "_").lower()
        
        # Save JSON
        json_path = self.output_dir / f"{experiment_slug}_wf_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump(wf_results, f, indent=2, default=str)
        
        self.logger.info(f"   Walk-forward results saved to: {json_path}")
        
        # Save CSV summary
        df = pd.DataFrame(wf_results)
        csv_path = self.output_dir / f"{experiment_slug}_wf_{timestamp}.csv"
        df.to_csv(csv_path, index=False)


if __name__ == "__main__":
    # Example usage
    async def run_example():
        from backtest.utils.config_loader import load_config
        
        config = load_config("backtest/configs/walk_forward.yaml")
        experiment = WalkForwardAnalysis(config)
        result = await experiment.run()
        experiment.print_summary(result)
        experiment.save_results(result)
        
    asyncio.run(run_example())

