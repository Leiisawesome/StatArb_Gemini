"""
Momentum Strategy Baseline Backtest - Phase 1.2

Run baseline backtest on optimal period (NVDA 2023 Q1) to validate the
complete end-to-end optimization workflow before parameter tuning.

Based on Momentum Period Scanner results:
- Best Period: NVDA 2023 Q1 (Score: 46.41)
- Date Range: 2023-01-01 to 2023-03-31
- Expected Signals: 50-200+ (high momentum period)
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

from backtest.optimization.backtest_optimizer_interface import BacktestOptimizerInterface
from backtest.optimization.config_management.parameter_registry import CentralParameterRegistry

# Configure logging with DEBUG level for instrumented strategy
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Also set DEBUG for the momentum strategy specifically
logging.getLogger('core_engine.trading.strategies.implementations.momentum.enhanced_momentum').setLevel(logging.DEBUG)


class MomentumBaselineRunner:
    """Run baseline backtest for Momentum strategy on optimal period"""
    
    def __init__(self):
        self.optimizer_interface = BacktestOptimizerInterface()
        self.parameter_registry = CentralParameterRegistry()
        
        # Baseline configuration based on scanner results
        self.baseline_config = {
            'symbol': 'NVDA',
            'start_date': '2023-01-01',
            'end_date': '2023-03-31',
            'period_label': 'NVDA 2023 Q1',
            'expected_score': 46.41,
            'expected_signals': '50-200+'
        }
    
    def get_baseline_parameters(self) -> Dict[str, Any]:
        """Get baseline Momentum strategy parameters - VERY RELAXED for testing"""
        return {
            # Momentum calculation periods
            'short_period': 10,
            'medium_period': 20,
            'long_period': 50,
            
            # Signal thresholds - VERY RELAXED
            'momentum_threshold': 0.003,  # 0.3% momentum threshold (very low)
            'adx_threshold': 15.0,        # ADX >= 15 (very relaxed)
            'volume_threshold': 0.5,      # Volume >= 50% of avg (very relaxed)
            
            # Position sizing
            'base_position_pct': 0.02,    # 2% base position
            'max_position_pct': 0.10,     # 10% max position
            
            # Risk management
            'momentum_stop_pct': 0.10,    # 10% momentum stop (wider)
            'trailing_stop_pct': 0.05,    # 5% trailing stop (wider)
            'profit_target_ratio': 3.0,   # 3:1 profit target (allow more running)
            'max_holding_period': 50,     # Max 50 bars (longer holding)
            
            # Breakout detection - DISABLED for simplicity
            'enable_breakout_detection': False,
            'breakout_lookback': 20,
            'breakout_threshold': 0.02,
            
            # Multi-timeframe settings
            'lookback_period': 60,
            'short_lookback': 20,
            'medium_lookback': 40,
            'long_lookback': 60
        }
    
    async def run_baseline(self) -> Dict[str, Any]:
        """Run baseline backtest on optimal period"""
        
        logger.info("=" * 80)
        logger.info("🚀 MOMENTUM BASELINE BACKTEST - PHASE 1.2")
        logger.info("=" * 80)
        logger.info("")
        logger.info(f"Period: {self.baseline_config['period_label']}")
        logger.info(f"Symbol: {self.baseline_config['symbol']}")
        logger.info(f"Date Range: {self.baseline_config['start_date']} to {self.baseline_config['end_date']}")
        logger.info(f"Expected Momentum Score: {self.baseline_config['expected_score']}")
        logger.info(f"Expected Signals: {self.baseline_config['expected_signals']}")
        logger.info("")
        
        # Get baseline parameters
        baseline_params = self.get_baseline_parameters()
        
        logger.info("📋 Baseline Parameters:")
        for key, value in baseline_params.items():
            logger.info(f"  - {key}: {value}")
        logger.info("")
        
        # Register parameters with central registry
        self.parameter_registry.update_parameters(
            strategy_type='momentum',
            parameters=baseline_params,
            changed_by='baseline_runner',
            change_reason='Baseline parameters for NVDA 2023 Q1 validation'
        )
        
        logger.info("⏳ Running baseline backtest...")
        logger.info("   This may take 2-5 minutes...")
        logger.info("")
        
        # Run backtest
        try:
            result = await self.optimizer_interface.run_single_backtest(
                strategy_type='momentum',
                strategy_params=baseline_params,
                symbols=[self.baseline_config['symbol']],
                custom_config={
                    'backtest_name': f"momentum_baseline_{self.baseline_config['symbol']}_2023Q1",
                    'data': {
                        'start_date': self.baseline_config['start_date'],
                        'end_date': self.baseline_config['end_date']
                    }
                }
            )
            
            # Analyze results
            logger.info("=" * 80)
            logger.info("📊 BASELINE BACKTEST RESULTS")
            logger.info("=" * 80)
            logger.info("")
            
            # Check if backtest succeeded
            if result.get('success', False):
                metrics = result
                
                logger.info("✅ Backtest completed successfully!")
                logger.info("")
                logger.info("📈 Performance Metrics:")
                logger.info(f"  Total Return: {metrics['total_return'] * 100:.2f}%")
                logger.info(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
                logger.info(f"  Max Drawdown: {abs(metrics['max_drawdown']) * 100:.2f}%")
                logger.info(f"  Win Rate: {metrics['win_rate'] * 100:.2f}%")
                logger.info(f"  Total Trades: {metrics['total_trades']}")
                logger.info("")
                
                # Check for no trades
                if metrics['total_trades'] == 0:
                    logger.warning("⚠️  WARNING: No trades were generated!")
                    logger.warning("   This means the strategy parameters are still too strict")
                    logger.warning("   OR the period doesn't match the strategy type")
                    logger.warning("")
                    logger.warning("   Recommendation:")
                    logger.warning("   1. Further relax parameters (especially momentum_threshold)")
                    logger.warning("   2. Try a different period with stronger momentum")
                    logger.warning("   3. Consider a different strategy type for this period")
                    logger.warning("")
                
                # Validation checks
                validation_results = self._validate_results(metrics)
                
                logger.info("🔍 Validation Results:")
                for check, passed in validation_results.items():
                    status = "✅" if passed else "❌"
                    logger.info(f"  {status} {check}")
                logger.info("")
                
                # Overall assessment
                all_passed = all(validation_results.values())
                if all_passed:
                    logger.info("🎉 SUCCESS: All validation checks passed!")
                    logger.info("   Ready to proceed with parameter optimization (Phase 1.3)")
                else:
                    logger.warning("⚠️  WARNING: Some validation checks failed")
                    logger.warning("   Review results before proceeding")
                
                logger.info("")
                logger.info("=" * 80)
                
                return {
                    'status': 'success',
                    'metrics': metrics,
                    'validation': validation_results,
                    'ready_for_optimization': all_passed
                }
            
            else:
                error_msg = result.get('error', 'Unknown error')
                logger.error(f"❌ Backtest failed: {error_msg}")
                logger.error("   Check logs for details")
                return {
                    'status': 'failed',
                    'error': error_msg
                }
        
        except Exception as e:
            logger.error(f"❌ Baseline backtest exception: {e}", exc_info=True)
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def _validate_results(self, metrics: Dict[str, Any]) -> Dict[str, bool]:
        """Validate backtest results against expectations"""
        
        validation = {}
        
        # Check 1: Trades generated
        validation['Trades Generated (>= 10)'] = metrics['total_trades'] >= 10
        
        # Check 2: Positive total return (convert from decimal to %)
        total_return_pct = metrics['total_return'] * 100
        validation['Positive Return'] = total_return_pct > 0
        
        # Check 3: Reasonable Sharpe ratio
        validation['Sharpe Ratio (>= 0.5)'] = metrics['sharpe_ratio'] >= 0.5
        
        # Check 4: Acceptable drawdown (convert from decimal to %)
        max_drawdown_pct = abs(metrics['max_drawdown']) * 100
        validation['Max Drawdown (<= 30%)'] = max_drawdown_pct <= 30.0
        
        # Check 5: Reasonable win rate (convert from decimal to %)
        win_rate_pct = metrics['win_rate'] * 100
        validation['Win Rate (>= 40%)'] = win_rate_pct >= 40.0
        
        # Check 6: Profit factor
        if 'profit_factor' in metrics:
            validation['Profit Factor (>= 1.0)'] = metrics.get('profit_factor', 0) >= 1.0
        
        return validation
    
    async def save_baseline_results(self, results: Dict[str, Any]):
        """Save baseline results for comparison"""
        
        import json
        from datetime import datetime
        
        output_dir = Path('backtest/optimization')
        output_file = output_dir / 'momentum_baseline_results.json'
        
        # Prepare results for JSON
        save_data = {
            'timestamp': datetime.now().isoformat(),
            'configuration': self.baseline_config,
            'parameters': self.get_baseline_parameters(),
            'results': results,
            'phase': 'Phase 1.2 - Baseline Validation'
        }
        
        with open(output_file, 'w') as f:
            json.dump(save_data, f, indent=2, default=str)
        
        logger.info(f"💾 Baseline results saved to: {output_file}")


async def main():
    """Main execution function"""
    
    runner = MomentumBaselineRunner()
    
    # Run baseline backtest
    results = await runner.run_baseline()
    
    # Save results
    if results['status'] == 'success':
        await runner.save_baseline_results(results)
    
    return results


if __name__ == '__main__':
    results = asyncio.run(main())

