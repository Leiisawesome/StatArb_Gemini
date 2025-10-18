"""
Backtest Optimizer Interface

Connects the optimization infrastructure (Phase 0) to the InstitutionalBacktestEngine.
This is the critical bridge that enables systematic strategy optimization.

Architecture:
    Optimization Infrastructure → BacktestOptimizerInterface → InstitutionalBacktestEngine
    (Parameter Management,      (This Module)                   (Core Engine Lego Bricks)
     Symbol Selection,
     Joint Optimization)

Usage:
    optimizer = BacktestOptimizerInterface(engine_config_template)
    results = await optimizer.optimize_strategy(strategy_type, param_space, symbols)
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import sys

# Add project root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine
from backtest.config.backtest_config import (
    BacktestConfiguration,
    DataConfig,
    StrategyConfig,
    RiskConfig,
    ExecutionConfig,
    AnalyticsConfig
)

logger = logging.getLogger(__name__)


class BacktestOptimizerInterface:
    """
    Interface between optimization infrastructure and backtest engine.
    
    This class provides the critical connection that enables:
    1. Running backtests with different parameter configurations
    2. Extracting performance metrics for optimization
    3. Systematic testing across parameter spaces
    4. Symbol-specific strategy optimization
    
    Key Features:
    - Template-based configuration
    - Parameter injection
    - Metric extraction
    - Result normalization
    - Error handling & recovery
    """
    
    def __init__(self, config_template: Optional[Dict[str, Any]] = None):
        """
        Initialize optimizer interface
        
        Args:
            config_template: Base configuration template (optional)
        """
        self.config_template = config_template or self._create_default_template()
        self.backtest_count = 0
        self.results_history: List[Dict[str, Any]] = []
        
        logger.info("✅ BacktestOptimizerInterface initialized")
    
    def _create_default_template(self) -> Dict[str, Any]:
        """Create default configuration template"""
        return {
            'backtest_name': 'optimization_run',
            'backtest_mode': 'historical',
            'data': {
                'start_date': '2024-07-01',  # Q3 2024 - Strong trending period
                'end_date': '2024-09-30',
                'interval': '1min'
            },
            'risk': {
                'initial_capital': 100_000.0,
                'max_position_size': 0.10,
                'max_total_exposure': 1.0,
                'enable_regime_adjustments': True
            },
            'execution': {
                'enable_realistic_fills': True,
                'enable_cost_modeling': True,
                'apply_slippage': True,
                'apply_market_impact': True,
                'apply_spread_cost': True
            },
            'analytics': {
                'enable_regime_attribution': True,
                'enable_strategy_attribution': True,
                'generate_html_report': False,  # Disable for speed
                'generate_json_report': True,
                'generate_csv_trades': False
            }
        }
    
    async def run_single_backtest(
        self,
        strategy_type: str,
        strategy_params: Dict[str, Any],
        symbols: List[str],
        custom_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run a single backtest with specific parameters
        
        Args:
            strategy_type: Type of strategy ('momentum', 'mean_reversion', etc.)
            strategy_params: Strategy-specific parameters
            symbols: List of symbols to trade
            custom_config: Optional config overrides
            
        Returns:
            Dict with performance metrics and metadata
        """
        self.backtest_count += 1
        
        try:
            # Build configuration
            config = self._build_config(
                strategy_type,
                strategy_params,
                symbols,
                custom_config
            )
            
            # Create engine
            engine = InstitutionalBacktestEngine(config=config)
            
            # Initialize
            init_success = await engine.initialize()
            if not init_success:
                logger.error(f"Backtest #{self.backtest_count} initialization failed")
                return self._create_error_result("Initialization failed")
            
            # Run backtest
            logger.info(f"Running backtest #{self.backtest_count}: {strategy_type} with {symbols}")
            results = await engine.run_backtest()
            
            # Extract metrics
            if results.get('success'):
                metrics = self._extract_metrics(results, strategy_type, strategy_params, symbols)
                
                # Store in history
                self.results_history.append(metrics)
                
                return metrics
            else:
                logger.warning(f"Backtest #{self.backtest_count} failed: {results.get('error')}")
                return self._create_error_result(results.get('error', 'Unknown error'))
                
        except Exception as e:
            logger.error(f"Backtest #{self.backtest_count} exception: {e}", exc_info=True)
            return self._create_error_result(str(e))
    
    def _build_config(
        self,
        strategy_type: str,
        strategy_params: Dict[str, Any],
        symbols: List[str],
        custom_config: Optional[Dict[str, Any]] = None
    ) -> BacktestConfiguration:
        """Build BacktestConfiguration from template and parameters"""
        
        # Start with template
        config_dict = self.config_template.copy()
        
        # Apply custom overrides
        if custom_config:
            self._deep_update(config_dict, custom_config)
        
        # Update symbols
        config_dict['data']['symbols'] = symbols
        
        # Build strategy config
        # Extract parameters from nested 'parameters' dict if present
        strategy_params_with_symbols = strategy_params.copy()
        strategy_params_with_symbols['symbols'] = symbols
        
        strategy_config = {
            'strategy_type': strategy_type,
            'strategy_name': f"{strategy_type}_{self.backtest_count}",
            'allocation_pct': 1.0,
            'max_position_size': config_dict['risk']['max_position_size'],
            'parameters': strategy_params_with_symbols
        }
        
        # Create BacktestConfiguration
        config = BacktestConfiguration(
            backtest_name=f"{config_dict['backtest_name']}_{self.backtest_count}",
            backtest_mode=config_dict['backtest_mode'],
            data=DataConfig(**config_dict['data']),
            strategies=[StrategyConfig(**strategy_config)],
            risk=RiskConfig(**config_dict['risk']),
            execution=ExecutionConfig(**config_dict['execution']),
            analytics=AnalyticsConfig(**config_dict['analytics'])
        )
        
        return config
    
    def _extract_metrics(
        self,
        results: Dict[str, Any],
        strategy_type: str,
        strategy_params: Dict[str, Any],
        symbols: List[str]
    ) -> Dict[str, Any]:
        """Extract standardized metrics from backtest results"""
        
        summary = results.get('summary', {}) or {}  # Handle None case
        
        # Standardized metrics for optimization
        metrics = {
            # Identification
            'strategy_type': strategy_type,
            'parameters': strategy_params,
            'symbols': symbols,
            'backtest_number': self.backtest_count,
            'timestamp': datetime.now().isoformat(),
            
            # Performance metrics
            'sharpe_ratio': summary.get('sharpe_ratio', 0.0) if summary else 0.0,
            'sortino_ratio': summary.get('sortino_ratio', 0.0) if summary else 0.0,
            'calmar_ratio': summary.get('calmar_ratio', 0.0) if summary else 0.0,
            'total_return': (summary.get('total_return_pct', 0.0) / 100.0) if summary else 0.0,
            'max_drawdown': (summary.get('max_drawdown_pct', 0.0) / 100.0) if summary else 0.0,
            'win_rate': (summary.get('win_rate', 0.0) / 100.0) if summary else 0.0,
            'profit_factor': summary.get('profit_factor', 0.0) if summary else 0.0,
            
            # Trading statistics
            'total_trades': results.get('total_trades', 0),
            'winning_trades': summary.get('winning_trades', 0) if summary else 0,
            'losing_trades': summary.get('losing_trades', 0) if summary else 0,
            'avg_win': summary.get('avg_win_pct', 0.0) if summary else 0.0,
            'avg_loss': summary.get('avg_loss_pct', 0.0) if summary else 0.0,
            
            # Execution metrics
            'total_bars': results.get('total_bars', 0),
            'duration_seconds': results.get('duration', 0.0),
            'bars_per_second': results.get('bars_per_second', 0.0),
            
            # Capital metrics
            'final_equity': summary.get('final_equity', 100_000.0) if summary else 100_000.0,
            'initial_capital': 100_000.0,
            
            # Status
            'success': True,
            'error': None if results.get('total_trades', 0) > 0 else 'No trades executed',
            'note': 'Strategy found no valid trading opportunities' if results.get('total_trades', 0) == 0 else None
        }
        
        return metrics
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error result"""
        return {
            'strategy_type': 'unknown',
            'parameters': {},
            'symbols': [],
            'backtest_number': self.backtest_count,
            'timestamp': datetime.now().isoformat(),
            'sharpe_ratio': -999.0,  # Clearly bad
            'total_return': -1.0,
            'max_drawdown': 1.0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'total_trades': 0,
            'success': False,
            'error': error_message
        }
    
    def _deep_update(self, base_dict: Dict, update_dict: Dict) -> None:
        """Deep update dictionary (modifies in place)"""
        for key, value in update_dict.items():
            if isinstance(value, dict) and key in base_dict and isinstance(base_dict[key], dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    async def batch_optimize(
        self,
        strategy_type: str,
        parameter_combinations: List[Dict[str, Any]],
        symbols: List[str],
        max_concurrent: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Run multiple backtests concurrently
        
        Args:
            strategy_type: Strategy type
            parameter_combinations: List of parameter dicts to test
            symbols: Symbols to trade
            max_concurrent: Maximum concurrent backtests
            
        Returns:
            List of results
        """
        logger.info(
            f"Starting batch optimization: {strategy_type}, "
            f"{len(parameter_combinations)} combinations, "
            f"{len(symbols)} symbols"
        )
        
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def run_with_semaphore(params):
            async with semaphore:
                return await self.run_single_backtest(
                    strategy_type,
                    params,
                    symbols
                )
        
        tasks = [run_with_semaphore(params) for params in parameter_combinations]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_results = [
            r for r in results 
            if not isinstance(r, Exception) and r.get('success', False)
        ]
        
        logger.info(
            f"Batch optimization complete: {len(valid_results)}/{len(parameter_combinations)} successful"
        )
        
        return valid_results
    
    def get_best_results(
        self,
        results: List[Dict[str, Any]],
        metric: str = 'sharpe_ratio',
        top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get best results sorted by metric
        
        Args:
            results: List of backtest results
            metric: Metric to sort by
            top_n: Number of top results to return
            
        Returns:
            Top N results
        """
        # Filter successful results
        valid_results = [r for r in results if r.get('success', False)]
        
        # Sort by metric (descending)
        sorted_results = sorted(
            valid_results,
            key=lambda x: x.get(metric, -999.0),
            reverse=True
        )
        
        return sorted_results[:top_n]
    
    def generate_optimization_summary(
        self,
        results: List[Dict[str, Any]]
    ) -> str:
        """Generate optimization summary report"""
        
        if not results:
            return "No results to summarize"
        
        valid_results = [r for r in results if r.get('success', False)]
        
        report = []
        report.append("=" * 80)
        report.append("OPTIMIZATION SUMMARY")
        report.append("=" * 80)
        report.append(f"\nTotal Backtests: {len(results)}")
        report.append(f"Successful: {len(valid_results)}")
        report.append(f"Failed: {len(results) - len(valid_results)}")
        
        if valid_results:
            report.append("\nTOP 5 RESULTS (by Sharpe Ratio):")
            report.append("-" * 80)
            
            top_5 = self.get_best_results(valid_results, 'sharpe_ratio', 5)
            
            for i, result in enumerate(top_5, 1):
                report.append(
                    f"\n{i}. Sharpe: {result['sharpe_ratio']:.2f} | "
                    f"Return: {result['total_return']*100:.2f}% | "
                    f"DD: {result['max_drawdown']*100:.2f}% | "
                    f"WR: {result['win_rate']*100:.1f}%"
                )
                report.append(f"   Parameters: {result['parameters']}")
                report.append(f"   Symbols: {', '.join(result['symbols'])}")
        
        report.append("\n" + "=" * 80)
        
        return "\n".join(report)


if __name__ == "__main__":
    """Example usage"""
    
    async def test_interface():
        """Test the optimizer interface"""
        
        interface = BacktestOptimizerInterface()
        
        # Test single backtest
        result = await interface.run_single_backtest(
            strategy_type='momentum',
            strategy_params={
                'lookback_period': 20,
                'momentum_threshold': 0.02
            },
            symbols=['NVDA']
        )
        
        print(f"Test result: {result.get('sharpe_ratio', 0):.2f}")
    
    # Run test
    asyncio.run(test_interface())
    print("✅ Interface test complete")

