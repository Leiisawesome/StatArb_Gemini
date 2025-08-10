"""
Regression Test Suite

Automated regression testing for trading strategies.

Author: Pro Quant Desk Trader
"""

import logging
import json
import os
import hashlib
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

from strategy_layer.base import StrategyConfig, StrategyType, StrategyStatus
from strategy_layer.strategies import (
    MomentumStrategyDefinition,
    PairTradingStrategyDefinition,
    MeanReversionStrategyDefinition
)
from strategy_layer.validation import ValidationConfig, BacktestingValidator


@dataclass
class RegressionTestResult:
    """Result of a regression test"""
    test_name: str
    strategy_id: str
    baseline_hash: str
    current_hash: str
    status: str  # PASS, FAIL, BASELINE_MISSING
    execution_time: float
    differences: Dict[str, Any]
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'test_name': self.test_name,
            'strategy_id': self.strategy_id,
            'baseline_hash': self.baseline_hash,
            'current_hash': self.current_hash,
            'status': self.status,
            'execution_time': self.execution_time,
            'differences': self.differences,
            'error_message': self.error_message
        }


class RegressionTestSuite:
    """Automated regression testing for trading strategies"""
    
    def __init__(self, baseline_dir: str = "baselines", tolerance: float = 0.01):
        self.baseline_dir = baseline_dir
        self.tolerance = tolerance
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Ensure baseline directory exists
        os.makedirs(baseline_dir, exist_ok=True)
    
    def run_regression_tests(self, strategies: List[Any]) -> List[RegressionTestResult]:
        """Run regression tests on all strategies"""
        self.logger.info(f"Starting regression tests for {len(strategies)} strategies")
        
        results = []
        for strategy in strategies:
            result = self._run_strategy_regression_test(strategy)
            results.append(result)
        
        self.logger.info(f"Regression tests completed. Results: {len(results)} tests")
        return results
    
    def _run_strategy_regression_test(self, strategy: Any) -> RegressionTestResult:
        """Run regression test for a single strategy"""
        import time
        start_time = time.time()
        
        try:
            strategy_id = strategy.config.strategy_id
            
            # Generate current test results
            current_results = self._generate_test_results(strategy)
            current_hash = self._hash_results(current_results)
            
            # Get baseline results
            baseline_file = os.path.join(self.baseline_dir, f"{strategy_id}_baseline.json")
            
            if not os.path.exists(baseline_file):
                # Create baseline if it doesn't exist
                self._save_baseline(strategy_id, current_results)
                
                execution_time = time.time() - start_time
                return RegressionTestResult(
                    test_name=f"Regression Test - {strategy_id}",
                    strategy_id=strategy_id,
                    baseline_hash="N/A",
                    current_hash=current_hash,
                    status="BASELINE_MISSING",
                    execution_time=execution_time,
                    differences={"message": "Baseline created"}
                )
            
            # Load baseline results
            baseline_results = self._load_baseline(strategy_id)
            baseline_hash = self._hash_results(baseline_results)
            
            # Compare results
            differences = self._compare_results(baseline_results, current_results)
            
            # Determine test status
            if not differences:
                status = "PASS"
            else:
                status = "FAIL"
            
            execution_time = time.time() - start_time
            
            return RegressionTestResult(
                test_name=f"Regression Test - {strategy_id}",
                strategy_id=strategy_id,
                baseline_hash=baseline_hash,
                current_hash=current_hash,
                status=status,
                execution_time=execution_time,
                differences=differences
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return RegressionTestResult(
                test_name=f"Regression Test - {strategy.config.strategy_id}",
                strategy_id=strategy.config.strategy_id,
                baseline_hash="ERROR",
                current_hash="ERROR",
                status="FAIL",
                execution_time=execution_time,
                differences={},
                error_message=str(e)
            )
    
    def _generate_test_results(self, strategy: Any) -> Dict[str, Any]:
        """Generate test results for regression comparison"""
        results = {
            'strategy_info': {
                'strategy_id': strategy.config.strategy_id,
                'strategy_name': strategy.config.name,
                'strategy_type': strategy.config.strategy_type.value,
                'version': strategy.config.version
            },
            'signal_generation': self._test_signal_generation(strategy),
            'position_sizing': self._test_position_sizing(strategy),
            'risk_management': self._test_risk_management(strategy),
            'entry_exit_logic': self._test_entry_exit_logic(strategy),
            'backtesting': self._test_backtesting(strategy),
            'performance_metrics': self._test_performance_metrics(strategy)
        }
        
        return results
    
    def _test_signal_generation(self, strategy: Any) -> Dict[str, Any]:
        """Test signal generation and return results"""
        try:
            # Create sample market data
            market_data = self._create_sample_market_data()
            
            # Generate signals
            signals = strategy.generate_signals(market_data)
            
            # Calculate signal statistics
            signal_values = list(signals.values()) if signals else []
            
            return {
                'signals_generated': len(signals),
                'signal_names': list(signals.keys()) if signals else [],
                'signal_mean': float(np.mean(signal_values)) if signal_values else 0.0,
                'signal_std': float(np.std(signal_values)) if signal_values else 0.0,
                'signal_min': float(np.min(signal_values)) if signal_values else 0.0,
                'signal_max': float(np.max(signal_values)) if signal_values else 0.0
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _test_position_sizing(self, strategy: Any) -> Dict[str, Any]:
        """Test position sizing and return results"""
        try:
            # Create sample data
            market_data = self._create_sample_market_data()
            signals = {'test_signal': 0.5}
            
            # Calculate position sizes
            position_sizes = strategy.calculate_position_sizes(signals, market_data)
            
            # Calculate position statistics
            size_values = list(position_sizes.values()) if position_sizes else []
            
            return {
                'positions_calculated': len(position_sizes),
                'position_names': list(position_sizes.keys()) if position_sizes else [],
                'position_mean': float(np.mean(size_values)) if size_values else 0.0,
                'position_std': float(np.std(size_values)) if size_values else 0.0,
                'position_min': float(np.min(size_values)) if size_values else 0.0,
                'position_max': float(np.max(size_values)) if size_values else 0.0
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _test_risk_management(self, strategy: Any) -> Dict[str, Any]:
        """Test risk management and return results"""
        try:
            # Create sample data
            market_data = self._create_sample_market_data()
            positions = {'SPY': 0.1}
            
            # Test risk validation
            risk_valid = strategy.validate_risk(positions, market_data)
            
            return {
                'risk_validation_result': risk_valid,
                'positions_tested': positions
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _test_entry_exit_logic(self, strategy: Any) -> Dict[str, Any]:
        """Test entry/exit logic and return results"""
        try:
            # Create sample data
            market_data = self._create_sample_market_data()
            signal = 0.5
            position = 0.1
            
            # Test entry/exit decisions
            should_enter = strategy.should_enter_position('SPY', signal, market_data)
            should_exit = strategy.should_exit_position('SPY', position, market_data)
            
            return {
                'should_enter': should_enter,
                'should_exit': should_exit,
                'test_signal': signal,
                'test_position': position
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _test_backtesting(self, strategy: Any) -> Dict[str, Any]:
        """Test backtesting and return results"""
        try:
            # Create validation config
            config = ValidationConfig(
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 3, 31),
                symbols=['SPY'],
                initial_capital=100000.0
            )
            
            # Create validator
            validator = BacktestingValidator(config)
            
            # Create market data
            market_data = self._create_sample_market_data()
            
            # Run validation
            result = validator.validate_strategy(strategy, market_data)
            
            return {
                'total_return': result.total_return,
                'annualized_return': result.annualized_return,
                'sharpe_ratio': result.sharpe_ratio,
                'sortino_ratio': result.sortino_ratio,
                'max_drawdown': result.max_drawdown,
                'calmar_ratio': result.calmar_ratio,
                'volatility': result.volatility,
                'total_trades': result.total_trades,
                'win_rate': result.win_rate,
                'profit_factor': result.profit_factor
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _test_performance_metrics(self, strategy: Any) -> Dict[str, Any]:
        """Test performance metrics and return results"""
        try:
            import time
            
            # Create sample data
            market_data = self._create_sample_market_data()
            
            # Measure execution times
            times = []
            for _ in range(5):
                start_time = time.time()
                signals = strategy.generate_signals(market_data)
                position_sizes = strategy.calculate_position_sizes(signals, market_data)
                end_time = time.time()
                times.append(end_time - start_time)
            
            return {
                'avg_execution_time': float(np.mean(times)),
                'min_execution_time': float(np.min(times)),
                'max_execution_time': float(np.max(times)),
                'std_execution_time': float(np.std(times))
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _create_sample_market_data(self) -> Dict[str, pd.DataFrame]:
        """Create sample market data for testing"""
        import pandas as pd
        import numpy as np
        
        np.random.seed(42)  # For reproducible results
        
        market_data = {}
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        
        for symbol in ['SPY']:
            # Generate sample price data
            base_price = 100.0
            returns = np.random.normal(0.001, 0.02, 100)
            prices = [base_price]
            
            for i in range(1, 100):
                new_price = prices[-1] * (1 + returns[i])
                prices.append(new_price)
            
            # Create OHLCV data
            data = {
                'open': [p * (1 + np.random.normal(0, 0.005)) for p in prices],
                'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
                'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
                'close': prices,
                'volume': np.random.randint(1000000, 10000000, 100)
            }
            
            df = pd.DataFrame(data, index=dates)
            market_data[symbol] = df
        
        return market_data
    
    def _hash_results(self, results: Dict[str, Any]) -> str:
        """Generate hash for results"""
        # Convert results to JSON string and hash
        json_str = json.dumps(results, sort_keys=True, default=str)
        return hashlib.md5(json_str.encode()).hexdigest()
    
    def _save_baseline(self, strategy_id: str, results: Dict[str, Any]):
        """Save baseline results"""
        baseline_file = os.path.join(self.baseline_dir, f"{strategy_id}_baseline.json")
        
        with open(baseline_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        self.logger.info(f"Baseline saved for strategy {strategy_id}")
    
    def _load_baseline(self, strategy_id: str) -> Dict[str, Any]:
        """Load baseline results"""
        baseline_file = os.path.join(self.baseline_dir, f"{strategy_id}_baseline.json")
        
        with open(baseline_file, 'r') as f:
            return json.load(f)
    
    def _compare_results(self, baseline: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
        """Compare baseline and current results"""
        differences = {}
        
        # Compare strategy info
        if baseline.get('strategy_info') != current.get('strategy_info'):
            differences['strategy_info'] = {
                'baseline': baseline.get('strategy_info'),
                'current': current.get('strategy_info')
            }
        
        # Compare test results
        test_sections = ['signal_generation', 'position_sizing', 'risk_management', 
                        'entry_exit_logic', 'backtesting', 'performance_metrics']
        
        for section in test_sections:
            baseline_section = baseline.get(section, {})
            current_section = current.get(section, {})
            
            section_diff = self._compare_section(baseline_section, current_section)
            if section_diff:
                differences[section] = section_diff
        
        return differences
    
    def _compare_section(self, baseline: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
        """Compare a specific section of results"""
        differences = {}
        
        # Handle error cases
        if 'error' in baseline or 'error' in current:
            if baseline.get('error') != current.get('error'):
                differences['error'] = {
                    'baseline': baseline.get('error'),
                    'current': current.get('error')
                }
            return differences
        
        # Compare numeric values with tolerance
        for key in set(baseline.keys()) | set(current.keys()):
            baseline_val = baseline.get(key)
            current_val = current.get(key)
            
            if isinstance(baseline_val, (int, float)) and isinstance(current_val, (int, float)):
                if abs(baseline_val - current_val) > self.tolerance:
                    differences[key] = {
                        'baseline': baseline_val,
                        'current': current_val,
                        'difference': current_val - baseline_val
                    }
            elif baseline_val != current_val:
                differences[key] = {
                    'baseline': baseline_val,
                    'current': current_val
                }
        
        return differences
    
    def update_baselines(self, strategies: List[Any]):
        """Update all baselines with current results"""
        self.logger.info("Updating all baselines")
        
        for strategy in strategies:
            try:
                strategy_id = strategy.config.strategy_id
                current_results = self._generate_test_results(strategy)
                self._save_baseline(strategy_id, current_results)
                self.logger.info(f"Baseline updated for strategy {strategy_id}")
            except Exception as e:
                self.logger.error(f"Failed to update baseline for strategy {strategy.config.strategy_id}: {e}")
    
    def get_regression_summary(self, results: List[RegressionTestResult]) -> Dict[str, Any]:
        """Get summary of regression test results"""
        if not results:
            return {}
        
        total_tests = len(results)
        passed_tests = len([r for r in results if r.status == "PASS"])
        failed_tests = len([r for r in results if r.status == "FAIL"])
        baseline_missing = len([r for r in results if r.status == "BASELINE_MISSING"])
        
        # Group by strategy
        strategy_results = {}
        for result in results:
            strategy_id = result.strategy_id
            if strategy_id not in strategy_results:
                strategy_results[strategy_id] = []
            strategy_results[strategy_id].append(result)
        
        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'baseline_missing': baseline_missing,
            'pass_rate': passed_tests / total_tests if total_tests > 0 else 0.0,
            'strategy_results': strategy_results,
            'avg_execution_time': float(np.mean([r.execution_time for r in results])),
            'total_execution_time': sum(r.execution_time for r in results)
        }
