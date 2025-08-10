"""
Strategy Test Suite

Comprehensive testing framework for trading strategies.

Author: Pro Quant Desk Trader
"""

import logging
import unittest
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from strategy_layer.base import StrategyError, StrategyConfig, StrategyType, StrategyStatus
from strategy_layer.strategies import (
    MomentumStrategyDefinition,
    PairTradingStrategyDefinition,
    MeanReversionStrategyDefinition
)
from strategy_layer.validation import (
    ValidationConfig,
    BacktestingValidator,
    WalkForwardValidator,
    ParameterValidator
)


@dataclass
class TestResult:
    """Result of a strategy test"""
    test_name: str
    strategy_id: str
    test_type: str
    status: str  # PASS, FAIL, ERROR
    execution_time: float
    details: Dict[str, Any]
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'test_name': self.test_name,
            'strategy_id': self.strategy_id,
            'test_type': self.test_type,
            'status': self.status,
            'execution_time': self.execution_time,
            'details': self.details,
            'error_message': self.error_message
        }


class StrategyTestSuite:
    """Comprehensive test suite for trading strategies"""
    
    def __init__(self, test_config: Dict[str, Any]):
        self.test_config = test_config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.results: List[TestResult] = []
        
    def run_all_tests(self, strategies: List[Any]) -> List[TestResult]:
        """Run all tests on the provided strategies"""
        self.logger.info(f"Starting comprehensive test suite for {len(strategies)} strategies")
        
        for strategy in strategies:
            self._run_strategy_tests(strategy)
        
        self.logger.info(f"Test suite completed. Results: {len(self.results)} tests")
        return self.results
    
    def _run_strategy_tests(self, strategy: Any):
        """Run all tests for a single strategy"""
        strategy_id = strategy.config.strategy_id
        
        # Unit tests
        self._run_unit_tests(strategy)
        
        # Integration tests
        self._run_integration_tests(strategy)
        
        # Performance tests
        self._run_performance_tests(strategy)
        
        # Validation tests
        self._run_validation_tests(strategy)
    
    def _run_unit_tests(self, strategy: Any):
        """Run unit tests for strategy components"""
        strategy_id = strategy.config.strategy_id
        
        # Test signal generation
        self._test_signal_generation(strategy)
        
        # Test position sizing
        self._test_position_sizing(strategy)
        
        # Test risk management
        self._test_risk_management(strategy)
        
        # Test entry/exit logic
        self._test_entry_exit_logic(strategy)
    
    def _run_integration_tests(self, strategy: Any):
        """Run integration tests"""
        strategy_id = strategy.config.strategy_id
        
        # Test end-to-end strategy execution
        self._test_strategy_execution(strategy)
        
        # Test building block integration
        self._test_building_block_integration(strategy)
        
        # Test configuration integration
        self._test_configuration_integration(strategy)
    
    def _run_performance_tests(self, strategy: Any):
        """Run performance tests"""
        strategy_id = strategy.config.strategy_id
        
        # Test execution speed
        self._test_execution_speed(strategy)
        
        # Test memory usage
        self._test_memory_usage(strategy)
        
        # Test scalability
        self._test_scalability(strategy)
    
    def _run_validation_tests(self, strategy: Any):
        """Run validation tests"""
        strategy_id = strategy.config.strategy_id
        
        # Test backtesting validation
        self._test_backtesting_validation(strategy)
        
        # Test walk-forward validation
        self._test_walk_forward_validation(strategy)
        
        # Test parameter validation
        self._test_parameter_validation(strategy)
    
    def _test_signal_generation(self, strategy: Any):
        """Test signal generation functionality"""
        import time
        start_time = time.time()
        
        try:
            # Create sample market data
            market_data = self._create_sample_market_data()
            
            # Test signal generation
            signals = strategy.generate_signals(market_data)
            
            # Validate signals
            assert isinstance(signals, dict), "Signals should be a dictionary"
            assert len(signals) > 0, "Should generate at least one signal"
            
            for signal_name, signal_value in signals.items():
                assert isinstance(signal_value, (int, float)), f"Signal {signal_name} should be numeric"
                assert -1 <= signal_value <= 1, f"Signal {signal_name} should be between -1 and 1"
            
            execution_time = time.time() - start_time
            
            self.results.append(TestResult(
                test_name="Signal Generation Test",
                strategy_id=strategy.config.strategy_id,
                test_type="UNIT",
                status="PASS",
                execution_time=execution_time,
                details={
                    'signals_generated': len(signals),
                    'signal_names': list(signals.keys()),
                    'signal_values': list(signals.values())
                }
            ))
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.results.append(TestResult(
                test_name="Signal Generation Test",
                strategy_id=strategy.config.strategy_id,
                test_type="UNIT",
                status="FAIL",
                execution_time=execution_time,
                details={},
                error_message=str(e)
            ))
    
    def _test_position_sizing(self, strategy: Any):
        """Test position sizing functionality"""
        import time
        start_time = time.time()
        
        try:
            # Create sample data
            market_data = self._create_sample_market_data()
            signals = {'test_signal': 0.5}
            portfolio_value = 100000.0
            current_positions = {}
            
            # Test position sizing
            position_sizes = strategy.calculate_position_sizes(signals, market_data)
            
            # Validate position sizes
            assert isinstance(position_sizes, dict), "Position sizes should be a dictionary"
            
            for symbol, size in position_sizes.items():
                assert isinstance(size, (int, float)), f"Position size for {symbol} should be numeric"
                assert size >= 0, f"Position size for {symbol} should be non-negative"
            
            execution_time = time.time() - start_time
            
            self.results.append(TestResult(
                test_name="Position Sizing Test",
                strategy_id=strategy.config.strategy_id,
                test_type="UNIT",
                status="PASS",
                execution_time=execution_time,
                details={
                    'position_sizes': position_sizes,
                    'portfolio_value': portfolio_value
                }
            ))
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.results.append(TestResult(
                test_name="Position Sizing Test",
                strategy_id=strategy.config.strategy_id,
                test_type="UNIT",
                status="FAIL",
                execution_time=execution_time,
                details={},
                error_message=str(e)
            ))
    
    def _test_risk_management(self, strategy: Any):
        """Test risk management functionality"""
        import time
        start_time = time.time()
        
        try:
            # Create sample data
            market_data = self._create_sample_market_data()
            positions = {'SPY': 0.1}
            
            # Test risk validation
            risk_valid = strategy.validate_risk(positions, market_data)
            
            # Validate risk check
            assert isinstance(risk_valid, bool), "Risk validation should return boolean"
            
            execution_time = time.time() - start_time
            
            self.results.append(TestResult(
                test_name="Risk Management Test",
                strategy_id=strategy.config.strategy_id,
                test_type="UNIT",
                status="PASS",
                execution_time=execution_time,
                details={
                    'risk_valid': risk_valid,
                    'positions': positions
                }
            ))
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.results.append(TestResult(
                test_name="Risk Management Test",
                strategy_id=strategy.config.strategy_id,
                test_type="UNIT",
                status="FAIL",
                execution_time=execution_time,
                details={},
                error_message=str(e)
            ))
    
    def _test_entry_exit_logic(self, strategy: Any):
        """Test entry/exit logic functionality"""
        import time
        start_time = time.time()
        
        try:
            # Create sample data
            market_data = self._create_sample_market_data()
            signal = 0.5
            position = 0.1
            
            # Test entry logic
            should_enter = strategy.should_enter_position('SPY', signal, market_data)
            assert isinstance(should_enter, bool), "Entry decision should be boolean"
            
            # Test exit logic
            should_exit = strategy.should_exit_position('SPY', position, market_data)
            assert isinstance(should_exit, bool), "Exit decision should be boolean"
            
            execution_time = time.time() - start_time
            
            self.results.append(TestResult(
                test_name="Entry/Exit Logic Test",
                strategy_id=strategy.config.strategy_id,
                test_type="UNIT",
                status="PASS",
                execution_time=execution_time,
                details={
                    'should_enter': should_enter,
                    'should_exit': should_exit,
                    'signal': signal,
                    'position': position
                }
            ))
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.results.append(TestResult(
                test_name="Entry/Exit Logic Test",
                strategy_id=strategy.config.strategy_id,
                test_type="UNIT",
                status="FAIL",
                execution_time=execution_time,
                details={},
                error_message=str(e)
            ))
    
    def _test_strategy_execution(self, strategy: Any):
        """Test end-to-end strategy execution"""
        import time
        start_time = time.time()
        
        try:
            # Create sample data
            market_data = self._create_sample_market_data()
            portfolio_value = 100000.0
            current_positions = {}
            portfolio_data = {}
            
            # Test strategy execution
            result = strategy.execute_strategy('SPY', market_data, portfolio_value, current_positions, portfolio_data)
            
            # Validate execution result
            assert hasattr(result, 'success'), "Execution result should have success attribute"
            assert hasattr(result, 'message'), "Execution result should have message attribute"
            
            execution_time = time.time() - start_time
            
            self.results.append(TestResult(
                test_name="Strategy Execution Test",
                strategy_id=strategy.config.strategy_id,
                test_type="INTEGRATION",
                status="PASS",
                execution_time=execution_time,
                details={
                    'execution_success': result.success,
                    'execution_message': result.message,
                    'portfolio_value': portfolio_value
                }
            ))
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.results.append(TestResult(
                test_name="Strategy Execution Test",
                strategy_id=strategy.config.strategy_id,
                test_type="INTEGRATION",
                status="FAIL",
                execution_time=execution_time,
                details={},
                error_message=str(e)
            ))
    
    def _test_building_block_integration(self, strategy: Any):
        """Test building block integration"""
        import time
        start_time = time.time()
        
        try:
            # Verify building blocks are properly initialized
            assert hasattr(strategy, 'signal_generator'), "Strategy should have signal generator"
            assert hasattr(strategy, 'position_sizer'), "Strategy should have position sizer"
            assert hasattr(strategy, 'risk_manager'), "Strategy should have risk manager"
            assert hasattr(strategy, 'entry_exit_logic'), "Strategy should have entry/exit logic"
            
            execution_time = time.time() - start_time
            
            self.results.append(TestResult(
                test_name="Building Block Integration Test",
                strategy_id=strategy.config.strategy_id,
                test_type="INTEGRATION",
                status="PASS",
                execution_time=execution_time,
                details={
                    'building_blocks': ['signal_generator', 'position_sizer', 'risk_manager', 'entry_exit_logic']
                }
            ))
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.results.append(TestResult(
                test_name="Building Block Integration Test",
                strategy_id=strategy.config.strategy_id,
                test_type="INTEGRATION",
                status="FAIL",
                execution_time=execution_time,
                details={},
                error_message=str(e)
            ))
    
    def _test_configuration_integration(self, strategy: Any):
        """Test configuration integration"""
        import time
        start_time = time.time()
        
        try:
            # Verify configuration is properly loaded
            config = strategy.config
            assert config.strategy_id, "Strategy should have ID"
            assert config.name, "Strategy should have name"
            assert config.strategy_type, "Strategy should have type"
            
            # Verify configuration structure
            assert hasattr(config, 'signal_generation'), "Config should have signal generation"
            assert hasattr(config, 'risk_management'), "Config should have risk management"
            assert hasattr(config, 'entry_exit_logic'), "Config should have entry/exit logic"
            
            execution_time = time.time() - start_time
            
            self.results.append(TestResult(
                test_name="Configuration Integration Test",
                strategy_id=strategy.config.strategy_id,
                test_type="INTEGRATION",
                status="PASS",
                execution_time=execution_time,
                details={
                    'config_id': config.strategy_id,
                    'config_name': config.name,
                    'config_type': config.strategy_type.value
                }
            ))
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.results.append(TestResult(
                test_name="Configuration Integration Test",
                strategy_id=strategy.config.strategy_id,
                test_type="INTEGRATION",
                status="FAIL",
                execution_time=execution_time,
                details={},
                error_message=str(e)
            ))
    
    def _test_execution_speed(self, strategy: Any):
        """Test execution speed"""
        import time
        start_time = time.time()
        
        try:
            # Create sample data
            market_data = self._create_sample_market_data()
            
            # Measure execution time for multiple operations
            times = []
            
            for _ in range(10):
                op_start = time.time()
                signals = strategy.generate_signals(market_data)
                position_sizes = strategy.calculate_position_sizes(signals, market_data)
                op_end = time.time()
                times.append(op_end - op_start)
            
            avg_time = float(np.mean(times))
            max_time = float(np.max(times))
            
            # Performance thresholds
            assert avg_time < 0.1, f"Average execution time {avg_time:.3f}s exceeds 0.1s threshold"
            assert max_time < 0.2, f"Maximum execution time {max_time:.3f}s exceeds 0.2s threshold"
            
            execution_time = time.time() - start_time
            
            self.results.append(TestResult(
                test_name="Execution Speed Test",
                strategy_id=strategy.config.strategy_id,
                test_type="PERFORMANCE",
                status="PASS",
                execution_time=execution_time,
                details={
                                    'avg_execution_time': avg_time,
                'max_execution_time': max_time,
                'min_execution_time': float(np.min(times)),
                'std_execution_time': float(np.std(times))
                }
            ))
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.results.append(TestResult(
                test_name="Execution Speed Test",
                strategy_id=strategy.config.strategy_id,
                test_type="PERFORMANCE",
                status="FAIL",
                execution_time=execution_time,
                details={},
                error_message=str(e)
            ))
    
    def _test_memory_usage(self, strategy: Any):
        """Test memory usage"""
        import time
        import psutil
        import os
        start_time = time.time()
        
        try:
            # Get initial memory usage
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Perform operations
            market_data = self._create_sample_market_data()
            for _ in range(100):
                signals = strategy.generate_signals(market_data)
                position_sizes = strategy.calculate_position_sizes(signals, market_data)
            
            # Get final memory usage
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            # Memory threshold (should not increase by more than 50MB)
            assert memory_increase < 50, f"Memory increase {memory_increase:.1f}MB exceeds 50MB threshold"
            
            execution_time = time.time() - start_time
            
            self.results.append(TestResult(
                test_name="Memory Usage Test",
                strategy_id=strategy.config.strategy_id,
                test_type="PERFORMANCE",
                status="PASS",
                execution_time=execution_time,
                details={
                    'initial_memory_mb': initial_memory,
                    'final_memory_mb': final_memory,
                    'memory_increase_mb': memory_increase
                }
            ))
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.results.append(TestResult(
                test_name="Memory Usage Test",
                strategy_id=strategy.config.strategy_id,
                test_type="PERFORMANCE",
                status="FAIL",
                execution_time=execution_time,
                details={},
                error_message=str(e)
            ))
    
    def _test_scalability(self, strategy: Any):
        """Test scalability with larger datasets"""
        import time
        start_time = time.time()
        
        try:
            # Test with different data sizes
            sizes = [100, 500, 1000]
            times = []
            
            for size in sizes:
                market_data = self._create_sample_market_data(days=size)
                
                op_start = time.time()
                signals = strategy.generate_signals(market_data)
                position_sizes = strategy.calculate_position_sizes(signals, market_data)
                op_end = time.time()
                
                times.append(op_end - op_start)
            
            # Check that time increase is reasonable (not exponential)
            time_ratios = [times[i] / times[i-1] for i in range(1, len(times))]
            avg_ratio = float(np.mean(time_ratios))
            
            assert avg_ratio < 3, f"Average time ratio {avg_ratio:.2f} suggests poor scalability"
            
            execution_time = time.time() - start_time
            
            self.results.append(TestResult(
                test_name="Scalability Test",
                strategy_id=strategy.config.strategy_id,
                test_type="PERFORMANCE",
                status="PASS",
                execution_time=execution_time,
                details={
                    'data_sizes': sizes,
                    'execution_times': times,
                    'time_ratios': time_ratios,
                    'avg_time_ratio': avg_ratio
                }
            ))
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.results.append(TestResult(
                test_name="Scalability Test",
                strategy_id=strategy.config.strategy_id,
                test_type="PERFORMANCE",
                status="FAIL",
                execution_time=execution_time,
                details={},
                error_message=str(e)
            ))
    
    def _test_backtesting_validation(self, strategy: Any):
        """Test backtesting validation"""
        import time
        start_time = time.time()
        
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
            
            # Validate result
            assert hasattr(result, 'total_return'), "Result should have total return"
            assert hasattr(result, 'sharpe_ratio'), "Result should have Sharpe ratio"
            assert hasattr(result, 'max_drawdown'), "Result should have max drawdown"
            
            execution_time = time.time() - start_time
            
            self.results.append(TestResult(
                test_name="Backtesting Validation Test",
                strategy_id=strategy.config.strategy_id,
                test_type="VALIDATION",
                status="PASS",
                execution_time=execution_time,
                details={
                    'total_return': result.total_return,
                    'sharpe_ratio': result.sharpe_ratio,
                    'max_drawdown': result.max_drawdown,
                    'total_trades': result.total_trades
                }
            ))
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.results.append(TestResult(
                test_name="Backtesting Validation Test",
                strategy_id=strategy.config.strategy_id,
                test_type="VALIDATION",
                status="FAIL",
                execution_time=execution_time,
                details={},
                error_message=str(e)
            ))
    
    def _test_walk_forward_validation(self, strategy: Any):
        """Test walk-forward validation"""
        import time
        start_time = time.time()
        
        try:
            # Create validation config
            config = ValidationConfig(
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 6, 30),
                symbols=['SPY'],
                initial_capital=100000.0,
                walk_forward_windows=3,
                validation_split=0.2
            )
            
            # Create validator
            validator = WalkForwardValidator(config)
            
            # Create market data
            market_data = self._create_sample_market_data(days=180)
            
            # Run validation
            result = validator.validate_strategy(strategy, market_data)
            
            # Validate result
            assert hasattr(result, 'total_return'), "Result should have total return"
            assert hasattr(result, 'sharpe_ratio'), "Result should have Sharpe ratio"
            
            execution_time = time.time() - start_time
            
            self.results.append(TestResult(
                test_name="Walk-Forward Validation Test",
                strategy_id=strategy.config.strategy_id,
                test_type="VALIDATION",
                status="PASS",
                execution_time=execution_time,
                details={
                    'total_return': result.total_return,
                    'sharpe_ratio': result.sharpe_ratio,
                    'windows': len(validator.results)
                }
            ))
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.results.append(TestResult(
                test_name="Walk-Forward Validation Test",
                strategy_id=strategy.config.strategy_id,
                test_type="VALIDATION",
                status="FAIL",
                execution_time=execution_time,
                details={},
                error_message=str(e)
            ))
    
    def _test_parameter_validation(self, strategy: Any):
        """Test parameter validation"""
        import time
        start_time = time.time()
        
        try:
            # Create validation config
            config = ValidationConfig(
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 2, 29),
                symbols=['SPY'],
                initial_capital=100000.0
            )
            
            # Create validator
            validator = ParameterValidator(config)
            
            # Create market data
            market_data = self._create_sample_market_data(days=60)
            
            # Run validation
            result = validator.validate_strategy(strategy, market_data)
            
            # Validate result
            assert hasattr(result, 'total_return'), "Result should have total return"
            assert hasattr(result, 'sharpe_ratio'), "Result should have Sharpe ratio"
            
            execution_time = time.time() - start_time
            
            self.results.append(TestResult(
                test_name="Parameter Validation Test",
                strategy_id=strategy.config.strategy_id,
                test_type="VALIDATION",
                status="PASS",
                execution_time=execution_time,
                details={
                    'total_return': result.total_return,
                    'sharpe_ratio': result.sharpe_ratio,
                    'parameters_analyzed': len(validator.sensitivities)
                }
            ))
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.results.append(TestResult(
                test_name="Parameter Validation Test",
                strategy_id=strategy.config.strategy_id,
                test_type="VALIDATION",
                status="FAIL",
                execution_time=execution_time,
                details={},
                error_message=str(e)
            ))
    
    def _create_sample_market_data(self, days: int = 100) -> Dict[str, pd.DataFrame]:
        """Create sample market data for testing"""
        np.random.seed(42)  # For reproducible results
        
        market_data = {}
        dates = pd.date_range(start='2024-01-01', periods=days, freq='D')
        
        for symbol in ['SPY']:
            # Generate sample price data
            base_price = 100.0
            returns = np.random.normal(0.001, 0.02, days)
            prices = [base_price]
            
            for i in range(1, days):
                new_price = prices[-1] * (1 + returns[i])
                prices.append(new_price)
            
            # Create OHLCV data
            data = {
                'open': [p * (1 + np.random.normal(0, 0.005)) for p in prices],
                'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
                'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
                'close': prices,
                'volume': np.random.randint(1000000, 10000000, days)
            }
            
            df = pd.DataFrame(data, index=dates)
            market_data[symbol] = df
        
        return market_data
    
    def get_test_summary(self) -> Dict[str, Any]:
        """Get summary of test results"""
        if not self.results:
            return {}
        
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r.status == "PASS"])
        failed_tests = len([r for r in self.results if r.status == "FAIL"])
        error_tests = len([r for r in self.results if r.status == "ERROR"])
        
        # Group by test type
        test_types = {}
        for result in self.results:
            test_type = result.test_type
            if test_type not in test_types:
                test_types[test_type] = {'total': 0, 'passed': 0, 'failed': 0, 'errors': 0}
            
            test_types[test_type]['total'] += 1
            if result.status == "PASS":
                test_types[test_type]['passed'] += 1
            elif result.status == "FAIL":
                test_types[test_type]['failed'] += 1
            else:
                test_types[test_type]['errors'] += 1
        
        # Calculate average execution time
        avg_execution_time = float(np.mean([r.execution_time for r in self.results]))
        
        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'error_tests': error_tests,
            'pass_rate': passed_tests / total_tests if total_tests > 0 else 0.0,
            'test_types': test_types,
            'avg_execution_time': avg_execution_time,
            'total_execution_time': sum(r.execution_time for r in self.results)
        }
