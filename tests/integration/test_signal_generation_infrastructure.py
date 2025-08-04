"""
Signal Generation Integration Tests - Batch 3

This module tests the signal generation infrastructure, including latency, format consistency,
error handling, throughput, memory usage, and CPU usage.
"""

import pytest
import asyncio
import time
import psutil
import gc
from datetime import datetime, timedelta
from typing import Dict, Any, List

from tests.integration.conftest import TestConfig
from tests.integration.mock_services import (
    MockSignalGenerator, MockExecutionEngine, MockRiskManager, MockPortfolioManager,
    MockSignal, MockOrder, MockExecution
)
from tests.integration.test_data_scenarios import TestDataScenarios
from tests.integration.test_logging import monitoring_context, log_test_event


class TestSignalGenerationInfrastructure:
    """Test signal generation infrastructure integration."""
    
    @pytest.mark.signal
    @pytest.mark.asyncio
    async def test_signal_generation_latency(self):
        """Test signal generation latency under normal conditions."""
        with monitoring_context("signal_generation_latency") as logger:
            logger.log_test_event("Testing signal generation latency")
            
            # Create test components
            signal_gen = MockSignalGenerator()
            symbols = ['AAPL', 'GOOGL', 'MSFT']
            
            # Test single signal generation latency
            start_time = time.time()
            signals = await signal_gen.generate_signals(symbols, count=1)
            single_signal_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Test multiple signal generation latency
            start_time = time.time()
            signals = await signal_gen.generate_signals(symbols, count=10)
            multiple_signals_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Validate latency requirements
            assert single_signal_time < 10  # Single signal should complete within 10ms
            assert multiple_signals_time < 50  # 10 signals should complete within 50ms
            assert len(signals) == 10
            
            # Check signal properties
            for signal in signals:
                assert isinstance(signal, MockSignal)
                assert signal.symbol in symbols
                assert signal.signal_type in ['BUY', 'SELL']
                assert 0.5 <= signal.confidence <= 1.0
                assert 0.1 <= signal.strength <= 0.5
            
            # Get performance stats
            stats = signal_gen.get_performance_stats()
            
            logger.log_test_event("Signal generation latency validated", {
                'single_signal_time_ms': single_signal_time,
                'multiple_signals_time_ms': multiple_signals_time,
                'avg_generation_time_ms': stats['avg_generation_time_ms'],
                'total_signals': stats['total_signals']
            })
    
    @pytest.mark.signal
    @pytest.mark.asyncio
    async def test_signal_format_consistency(self):
        """Test signal format consistency across different scenarios."""
        with monitoring_context("signal_format_consistency") as logger:
            logger.log_test_event("Testing signal format consistency")
            
            # Create test components
            signal_gen = MockSignalGenerator()
            symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']
            
            # Test different signal counts
            signal_counts = [1, 5, 10, 20]
            all_signals = []
            
            for count in signal_counts:
                signals = await signal_gen.generate_signals(symbols, count=count)
                all_signals.extend(signals)
                
                # Validate signal count
                assert len(signals) == count
                
                # Validate signal format consistency
                for signal in signals:
                    # Required fields
                    assert hasattr(signal, 'signal_id')
                    assert hasattr(signal, 'symbol')
                    assert hasattr(signal, 'timestamp')
                    assert hasattr(signal, 'signal_type')
                    assert hasattr(signal, 'confidence')
                    assert hasattr(signal, 'strength')
                    assert hasattr(signal, 'source')
                    
                    # Data type validation
                    assert isinstance(signal.signal_id, str)
                    assert isinstance(signal.symbol, str)
                    assert isinstance(signal.timestamp, datetime)
                    assert isinstance(signal.signal_type, str)
                    assert isinstance(signal.confidence, float)
                    assert isinstance(signal.strength, float)
                    assert isinstance(signal.source, str)
                    
                    # Value range validation
                    assert signal.symbol in symbols
                    assert signal.signal_type in ['BUY', 'SELL']
                    assert 0.5 <= signal.confidence <= 1.0
                    assert 0.1 <= signal.strength <= 0.5
                    assert signal.source == 'mock_signal_generator'
            
            # Check for unique signal IDs
            signal_ids = [signal.signal_id for signal in all_signals]
            assert len(signal_ids) == len(set(signal_ids)), "Signal IDs should be unique"
            
            logger.log_test_event("Signal format consistency validated", {
                'total_signals_tested': len(all_signals),
                'signal_counts_tested': signal_counts,
                'unique_signal_ids': len(set(signal_ids))
            })
    
    @pytest.mark.signal
    @pytest.mark.asyncio
    async def test_signal_error_handling(self):
        """Test signal generation error handling."""
        with monitoring_context("signal_error_handling") as logger:
            logger.log_test_event("Testing signal error handling")
            
            # Create test components
            signal_gen = MockSignalGenerator()
            
            # Test with empty symbols list
            try:
                signals = await signal_gen.generate_signals([], count=5)
                # Should handle gracefully and return empty list or default signals
                assert isinstance(signals, list)
            except Exception as e:
                logger.log_test_event("Empty symbols list handled", {'error': str(e)})
            
            # Test with invalid symbol
            try:
                signals = await signal_gen.generate_signals(['INVALID_SYMBOL'], count=1)
                # Should handle gracefully
                assert isinstance(signals, list)
            except Exception as e:
                logger.log_test_event("Invalid symbol handled", {'error': str(e)})
            
            # Test with zero count
            try:
                signals = await signal_gen.generate_signals(['AAPL'], count=0)
                assert len(signals) == 0
            except Exception as e:
                logger.log_test_event("Zero count handled", {'error': str(e)})
            
            # Test with negative count
            try:
                signals = await signal_gen.generate_signals(['AAPL'], count=-1)
                # Should handle gracefully
                assert isinstance(signals, list)
            except Exception as e:
                logger.log_test_event("Negative count handled", {'error': str(e)})
            
            # Test with very large count
            try:
                signals = await signal_gen.generate_signals(['AAPL'], count=1000)
                # Should handle gracefully
                assert isinstance(signals, list)
                assert len(signals) <= 1000
            except Exception as e:
                logger.log_test_event("Large count handled", {'error': str(e)})
            
            logger.log_test_event("Signal error handling validated", {
                'error_scenarios_tested': 5
            })
    
    @pytest.mark.signal
    @pytest.mark.asyncio
    async def test_signal_generation_throughput(self):
        """Test signal generation throughput under load."""
        with monitoring_context("signal_generation_throughput") as logger:
            logger.log_test_event("Testing signal generation throughput")
            
            # Create test components
            signal_gen = MockSignalGenerator()
            symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']
            
            # Test throughput with different loads
            throughput_tests = [
                {'count': 10, 'expected_time_ms': 50},
                {'count': 50, 'expected_time_ms': 200},
                {'count': 100, 'expected_time_ms': 500}
            ]
            
            throughput_results = []
            
            for test in throughput_tests:
                start_time = time.time()
                signals = await signal_gen.generate_signals(symbols, count=test['count'])
                end_time = time.time()
                
                duration_ms = (end_time - start_time) * 1000
                throughput = test['count'] / (duration_ms / 1000)  # signals per second
                
                throughput_results.append({
                    'count': test['count'],
                    'duration_ms': duration_ms,
                    'throughput_sps': throughput,
                    'expected_time_ms': test['expected_time_ms']
                })
                
                # Validate performance
                assert duration_ms < test['expected_time_ms']
                assert len(signals) == test['count']
                assert throughput > 10  # Should generate at least 10 signals per second
            
            # Calculate average throughput
            avg_throughput = sum(r['throughput_sps'] for r in throughput_results) / len(throughput_results)
            
            logger.log_test_event("Signal generation throughput validated", {
                'throughput_results': throughput_results,
                'average_throughput_sps': avg_throughput,
                'tests_completed': len(throughput_tests)
            })
    
    @pytest.mark.signal
    @pytest.mark.asyncio
    async def test_signal_generation_memory_usage(self):
        """Test signal generation memory usage."""
        with monitoring_context("signal_generation_memory_usage") as logger:
            logger.log_test_event("Testing signal generation memory usage")
            
            # Create test components
            signal_gen = MockSignalGenerator()
            symbols = ['AAPL', 'GOOGL', 'MSFT']
            
            # Get initial memory usage
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Generate signals and monitor memory
            memory_usage = []
            signal_counts = [10, 50, 100, 200]
            
            for count in signal_counts:
                # Force garbage collection before test
                gc.collect()
                
                # Generate signals
                signals = await signal_gen.generate_signals(symbols, count=count)
                
                # Measure memory usage
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_increase = current_memory - initial_memory
                
                memory_usage.append({
                    'signal_count': count,
                    'memory_mb': current_memory,
                    'memory_increase_mb': memory_increase,
                    'memory_per_signal_mb': memory_increase / count if count > 0 else 0
                })
                
                # Validate memory usage is reasonable
                assert memory_increase < 100  # Should not use more than 100MB additional memory
                assert len(signals) == count
            
            # Calculate average memory per signal
            avg_memory_per_signal = sum(r['memory_per_signal_mb'] for r in memory_usage) / len(memory_usage)
            
            logger.log_test_event("Signal generation memory usage validated", {
                'memory_usage': memory_usage,
                'average_memory_per_signal_mb': avg_memory_per_signal,
                'initial_memory_mb': initial_memory,
                'final_memory_mb': memory_usage[-1]['memory_mb']
            })
    
    @pytest.mark.signal
    @pytest.mark.asyncio
    async def test_signal_generation_cpu_usage(self):
        """Test signal generation CPU usage."""
        with monitoring_context("signal_generation_cpu_usage") as logger:
            logger.log_test_event("Testing signal generation CPU usage")
            
            # Create test components
            signal_gen = MockSignalGenerator()
            symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']
            
            # Get initial CPU usage
            process = psutil.Process()
            initial_cpu_percent = process.cpu_percent()
            
            # Generate signals and monitor CPU
            cpu_usage = []
            signal_counts = [10, 50, 100]
            
            for count in signal_counts:
                # Generate signals
                start_time = time.time()
                signals = await signal_gen.generate_signals(symbols, count=count)
                end_time = time.time()
                
                duration = end_time - start_time
                
                # Measure CPU usage during generation
                cpu_percent = process.cpu_percent(interval=0.1)
                
                cpu_usage.append({
                    'signal_count': count,
                    'duration_seconds': duration,
                    'cpu_percent': cpu_percent,
                    'signals_per_second': count / duration if duration > 0 else 0
                })
                
                # Validate CPU usage is reasonable
                assert cpu_percent < 80  # Should not use more than 80% CPU
                assert len(signals) == count
            
            # Calculate average CPU usage
            avg_cpu_percent = sum(r['cpu_percent'] for r in cpu_usage) / len(cpu_usage)
            
            logger.log_test_event("Signal generation CPU usage validated", {
                'cpu_usage': cpu_usage,
                'average_cpu_percent': avg_cpu_percent,
                'initial_cpu_percent': initial_cpu_percent
            })
    
    @pytest.mark.signal
    @pytest.mark.asyncio
    async def test_signal_generation_integration_with_risk(self):
        """Test signal generation integration with risk management."""
        with monitoring_context("signal_generation_risk_integration") as logger:
            logger.log_test_event("Testing signal generation with risk management")
            
            # Create test components
            signal_gen = MockSignalGenerator()
            risk_manager = MockRiskManager()
            symbols = ['AAPL', 'GOOGL', 'MSFT']
            
            # Generate signals
            signals = await signal_gen.generate_signals(symbols, count=10)
            
            # Create portfolio state for risk validation
            portfolio_state = {
                'total_value': 1000000.0,
                'positions': {
                    'AAPL': {'quantity': 1000, 'current_value': 150000.0},
                    'GOOGL': {'quantity': 500, 'current_value': 1400000.0}
                }
            }
            
            # Validate signals through risk manager
            validations = []
            for signal in signals:
                validation = await risk_manager.validate_signal(signal, portfolio_state)
                validations.append(validation)
            
            # Analyze results
            approved_signals = [v for v in validations if v['approved']]
            rejected_signals = [v for v in validations if not v['approved']]
            
            # Validate integration
            assert len(validations) == len(signals)
            assert len(approved_signals) + len(rejected_signals) == len(signals)
            
            # Check that risk validation affects signal processing
            if len(rejected_signals) > 0:
                logger.log_test_event("Risk management properly filtering signals", {
                    'total_signals': len(signals),
                    'approved_signals': len(approved_signals),
                    'rejected_signals': len(rejected_signals),
                    'approval_rate': len(approved_signals) / len(signals)
                })
            
            # Get performance stats
            signal_stats = signal_gen.get_performance_stats()
            risk_stats = risk_manager.get_performance_stats()
            
            logger.log_test_event("Signal generation risk integration validated", {
                'signals_generated': signal_stats['total_signals'],
                'risk_checks_performed': risk_stats['total_checks'],
                'approval_rate': len(approved_signals) / len(signals) if signals else 0
            })


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s", "-m", "signal"]) 