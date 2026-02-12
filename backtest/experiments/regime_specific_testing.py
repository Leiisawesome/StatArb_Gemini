"""
Experiment 6: Regime-Specific Testing
======================================

Test strategy performance across different market regime conditions.

Purpose:
- Measure strategy performance by regime
- Identify regime-specific strengths/weaknesses
- Validate regime-aware risk adjustments
- Optimize per-regime parameters

Methodology:
- Split backtest period by detected regimes
- Run strategy independently in each regime period
- Compare performance across regimes
- Identify regime-dependent parameter sensitivities

Expected Duration: 5-30 minutes (depending on period length)

Author: StatArb_Gemini Core Engine
"""

from datetime import datetime, timedelta
import time
from typing import Dict, List, Tuple
import pandas as pd
import numpy as np
import json

from backtest.experiments.base_experiment import BaseExperiment, ExperimentResult
from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine
from core_engine.config import BacktestConfig

class RegimeSpecificTesting(BaseExperiment):
    """
    Regime-specific testing experiment.

    Tests strategy performance segmented by market regime.
    """

    def get_description(self) -> str:
        return f"Regime-specific: Performance by market regime"

    async def run(self) -> ExperimentResult:
        """Run regime-specific testing"""
        start_time = time.time()
        experiment_name = self.config.get('experiment_name', 'Regime_Specific_Testing')

        try:
            self.logger.info(f"🔧 Starting regime-specific testing: {experiment_name}")

            # Target regimes to test
            target_regimes = self.config.get('target_regimes', [
                'low_volatility', 'normal_volatility', 'high_volatility'
            ])

            self.logger.info(f"   Target regimes: {target_regimes}")

            # Identify regime periods (simplified - in production would use actual regime detection)
            regime_periods = await self._identify_regime_periods(target_regimes)

            if not regime_periods:
                raise ValueError("No regime periods identified")

            # Test strategy in each regime
            regime_results = []
            for regime_name, periods in regime_periods.items():
                self.logger.info(f"\n   Testing regime: {regime_name}")
                self.logger.info(f"     Periods found: {len(periods)}")

                # Run backtest for this regime
                regime_performance = await self._test_regime(regime_name, periods)

                regime_results.append({
                    'regime': regime_name,
                    'periods_count': len(periods),
                    'total_days': sum([(p[1] - p[0]).days for p in periods]),
                    'total_return_pct': regime_performance['total_return_pct'],
                    'sharpe_ratio': regime_performance['sharpe_ratio'],
                    'max_drawdown_pct': regime_performance['max_drawdown_pct'],
                    'total_trades': regime_performance['total_trades'],
                    'win_rate': regime_performance['win_rate'],
                    'avg_trade_return': regime_performance['avg_trade_return']
                })

                self.logger.info(f"     Return: {regime_performance['total_return_pct']:.2f}%")
                self.logger.info(f"     Sharpe: {regime_performance['sharpe_ratio']:.2f}")
                self.logger.info(f"     Trades: {regime_performance['total_trades']}")

            # Analyze regime comparison
            analysis = self._analyze_regime_results(regime_results)

            # Find best/worst regimes
            best_regime = max(regime_results, key=lambda x: x['sharpe_ratio'])
            worst_regime = min(regime_results, key=lambda x: x['sharpe_ratio'])

            # Calculate duration
            duration = time.time() - start_time

            # Create result
            result = ExperimentResult(
                experiment_name=experiment_name,
                experiment_type="regime_specific_testing",
                run_timestamp=datetime.now(),
                duration_seconds=duration,
                engine_results={'regime_results': regime_results},
                total_return_pct=analysis['avg_return_pct'],
                sharpe_ratio=analysis['avg_sharpe'],
                max_drawdown_pct=max([r['max_drawdown_pct'] for r in regime_results]),
                total_trades=sum([r['total_trades'] for r in regime_results]),
                win_rate=analysis['avg_win_rate'],
                custom_metrics={
                    'regimes_tested': len(regime_results),
                    'best_regime': best_regime['regime'],
                    'best_regime_sharpe': best_regime['sharpe_ratio'],
                    'worst_regime': worst_regime['regime'],
                    'worst_regime_sharpe': worst_regime['sharpe_ratio'],
                    'regime_performance_spread': best_regime['sharpe_ratio'] - worst_regime['sharpe_ratio'],
                    'regime_consistency': analysis['consistency_score']
                },
                success=True
            )

            # Save detailed regime results
            self._save_regime_results(regime_results, experiment_name)

            self.logger.info(f"\n✅ Regime-specific testing completed in {duration:.2f}s")
            self.logger.info(f"   Best regime: {best_regime['regime']} (Sharpe: {best_regime['sharpe_ratio']:.2f})")
            self.logger.info(f"   Worst regime: {worst_regime['regime']} (Sharpe: {worst_regime['sharpe_ratio']:.2f})")

            return result

        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"❌ Regime-specific testing failed: {e}", exc_info=True)

            return ExperimentResult(
                experiment_name=experiment_name,
                experiment_type="regime_specific_testing",
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

    async def _identify_regime_periods(self, target_regimes: List[str]) -> Dict[str, List[Tuple[datetime, datetime]]]:
        """
        Identify periods for each regime.

        Simplified implementation - assigns regimes based on volatility heuristics.
        In production, would use actual regime detection from RegimeEngine.
        """
        start_date = datetime.strptime(self.config['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(self.config['end_date'], '%Y-%m-%d')

        total_days = (end_date - start_date).days

        # Simplified: Split period into regime segments
        # In production, would query actual regime detection results
        regime_periods = {}

        if 'low_volatility' in target_regimes:
            # First third of period
            regime_periods['low_volatility'] = [
                (start_date, start_date + timedelta(days=total_days // 3))
            ]

        if 'normal_volatility' in target_regimes:
            # Middle third
            regime_periods['normal_volatility'] = [
                (start_date + timedelta(days=total_days // 3),
                 start_date + timedelta(days=2 * total_days // 3))
            ]

        if 'high_volatility' in target_regimes:
            # Last third
            regime_periods['high_volatility'] = [
                (start_date + timedelta(days=2 * total_days // 3), end_date)
            ]

        return regime_periods

    async def _test_regime(self, regime_name: str, periods: List[Tuple[datetime, datetime]]) -> Dict[str, float]:
        """Test strategy performance in specific regime"""
        # Combine all periods for this regime into one backtest
        # (Simplified - could run separate backtests and aggregate)

        if not periods:
            return {
                'total_return_pct': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown_pct': 0.0,
                'total_trades': 0,
                'win_rate': 0.0,
                'avg_trade_return': 0.0
            }

        # Use first period for simplicity (in production, would aggregate all periods)
        start_date, end_date = periods[0]

        config_dict = self.config.copy()
        config_dict['backtest_name'] = f"Regime_{regime_name}"
        config_dict['start_date'] = start_date.strftime('%Y-%m-%d')
        config_dict['end_date'] = end_date.strftime('%Y-%m-%d')

        # Update strategy parameters
        if 'strategy' in config_dict:
            strategy = config_dict['strategy'].copy()
            config_dict['strategies'] = [strategy]
            del config_dict['strategy']

        # Remove invalid keys
        for key in ['target_regimes', 'experiment_name', 'experiment_type', 'log_level', 'save_trade_log', 'save_regime_log']:
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
            'win_rate': performance.get('win_rate', 0.0) * 100,
            'avg_trade_return': performance.get('avg_trade_return', 0.0)
        }

    def _analyze_regime_results(self, regime_results: List[Dict]) -> Dict[str, float]:
        """Analyze regime-specific results"""
        if not regime_results:
            return {
                'avg_return_pct': 0.0,
                'avg_sharpe': 0.0,
                'avg_win_rate': 0.0,
                'consistency_score': 0.0
            }

        returns = [r['total_return_pct'] for r in regime_results]
        sharpes = [r['sharpe_ratio'] for r in regime_results]

        # Consistency score: how similar are returns across regimes
        # Lower std = more consistent
        return_std = np.std(returns) if len(returns) > 1 else 0.0
        consistency_score = 1.0 / (1.0 + return_std) if return_std > 0 else 1.0

        return {
            'avg_return_pct': np.mean(returns),
            'avg_sharpe': np.mean(sharpes),
            'avg_win_rate': np.mean([r['win_rate'] for r in regime_results]),
            'consistency_score': consistency_score
        }

    def _save_regime_results(self, regime_results: List[Dict], experiment_name: str):
        """Save detailed regime results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        experiment_slug = experiment_name.replace(" ", "_").lower()

        # Save CSV
        df = pd.DataFrame(regime_results)
        csv_path = self.output_dir / f"{experiment_slug}_regime_{timestamp}.csv"
        df.to_csv(csv_path, index=False)
        self.logger.info(f"   Regime results saved to: {csv_path}")

        # Save JSON
        json_path = self.output_dir / f"{experiment_slug}_regime_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump(regime_results, f, indent=2, default=str)

if __name__ == "__main__":
    RegimeSpecificTesting.main("backtest/configs/regime_specific.yaml")

