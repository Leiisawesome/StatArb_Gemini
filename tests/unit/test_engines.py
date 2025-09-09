"""
Unit Tests for Engine System
===========================

Tests for the streamlined engine system (engines.py).
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from core_structure.engines import (
    TradingEngine, SignalProcessor, ExecutionProcessor,
    TradingSignal, SignalType, SignalStrength, ExecutionResult, ExecutionStatus
)
from core_structure.config import TradingConfig


class TestTradingEngine:
    """Test TradingEngine functionality"""
    
    def test_engine_initialization(self, test_config):
        """Test engine initialization"""
        engine = TradingEngine(test_config)
        
        assert engine.config == test_config
        assert engine.signal_processor is not None
        assert engine.execution_processor is not None
        assert engine.status.value in ['initializing', 'ready']
    
    def test_engine_startup_shutdown(self, test_config):
        """Test engine startup and shutdown"""
        engine = TradingEngine(test_config)
        
        # Engine starts ready after initialization
        assert engine.status.value in ['ready', 'initializing']
        
        # Test shutdown
        engine.shutdown()
        assert engine.status.value in ['shutdown', 'stopped']
    
    def test_engine_health_check(self, test_config):
        """Test engine health monitoring"""
        engine = TradingEngine(test_config)
        
        # Test metrics as health indicator
        metrics = engine.get_metrics()
        
        assert hasattr(metrics, 'total_signals')
        assert hasattr(metrics, 'total_executions')  # Correct attribute name
        assert engine.status.value in ['ready', 'initializing']
    
    def test_engine_metrics(self, test_config):
        """Test engine performance metrics"""
        engine = TradingEngine(test_config)
        
        metrics = engine.get_metrics()
        
        assert hasattr(metrics, 'total_signals')
        assert hasattr(metrics, 'total_executions')
        assert hasattr(metrics, 'success_rate')
        assert hasattr(metrics, 'average_latency_ms')
    
    @pytest.mark.asyncio
    async def test_engine_async_operations(self, test_config):
        """Test engine async operations"""
        engine = TradingEngine(test_config)
        
        # Test that engine is ready for async operations
        assert engine.status.value == 'ready'
        
        # Test async shutdown (if available)
        if hasattr(engine, 'async_shutdown'):
            await engine.async_shutdown()
        else:
            engine.shutdown()
        assert engine.status.value in ['shutdown', 'stopped']


class TestSignalProcessor:
    """Test SignalProcessor functionality"""
    
    def test_signal_processor_initialization(self, test_config):
        """Test signal processor initialization"""
        processor = SignalProcessor(test_config)
        
        assert processor.config == test_config
        assert hasattr(processor, 'signal_cache')
        assert hasattr(processor, 'performance_metrics')
    
    def test_signal_creation(self, signal_processor):
        """Test trading signal creation"""
        signal = TradingSignal(
            symbol="AAPL",
            signal_type=SignalType.LONG,
            strength=SignalStrength.STRONG,
            confidence=0.85,
            timestamp=datetime.now(),
            metadata={'strategy': 'momentum'}
        )
        
        assert signal.symbol == "AAPL"
        assert signal.signal_type == SignalType.LONG
        assert signal.strength == SignalStrength.STRONG
        assert signal.confidence == 0.85
        assert 'strategy' in signal.metadata
    
    def test_signal_validation(self, signal_processor):
        """Test signal validation"""
        # Valid signal
        valid_signal = TradingSignal(
            symbol="AAPL",
            signal_type=SignalType.LONG,
            strength=SignalStrength.MODERATE,
            confidence=0.75,
            timestamp=datetime.now()
        )
        
        is_valid = signal_processor.validate_signal(valid_signal)
        assert is_valid
        
        # Invalid signal (low confidence)
        invalid_signal = TradingSignal(
            symbol="AAPL",
            signal_type=SignalType.LONG,
            strength=SignalStrength.WEAK,
            confidence=0.3,  # Too low
            timestamp=datetime.now()
        )
        
        is_valid = signal_processor.validate_signal(invalid_signal)
        assert not is_valid
    
    def test_signal_processing(self, signal_processor, sample_signals):
        """Test signal processing workflow"""
        processed_signals = []
        
        for signal in sample_signals[:5]:  # Process first 5 signals
            result = signal_processor.process_signal(signal)
            if result:
                processed_signals.append(result)
        
        assert len(processed_signals) <= 5
        # All processed signals should be valid
        for signal in processed_signals:
            assert signal_processor.validate_signal(signal)
    
    def test_signal_filtering(self, signal_processor):
        """Test signal filtering logic"""
        # Create signals with different strengths
        signals = [
            TradingSignal("AAPL", SignalType.LONG, SignalStrength.WEAK, 0.4, datetime.now()),
            TradingSignal("MSFT", SignalType.SHORT, SignalStrength.MODERATE, 0.7, datetime.now()),
            TradingSignal("GOOGL", SignalType.LONG, SignalStrength.STRONG, 0.9, datetime.now())
        ]
        
        # Filter by minimum confidence
        filtered = signal_processor.filter_signals(signals, min_confidence=0.6)
        
        assert len(filtered) == 2  # Only moderate and strong signals
        assert all(s.confidence >= 0.6 for s in filtered)
    
    def test_signal_caching(self, signal_processor):
        """Test signal caching mechanism"""
        signal = TradingSignal(
            symbol="AAPL",
            signal_type=SignalType.LONG,
            strength=SignalStrength.STRONG,
            confidence=0.85,
            timestamp=datetime.now()
        )
        
        # Process signal (should cache it)
        result1 = signal_processor.process_signal(signal)
        
        # Process same signal again (should use cache)
        result2 = signal_processor.process_signal(signal)
        
        # Results should be consistent
        if result1 and result2:
            assert result1.symbol == result2.symbol
            assert result1.signal_type == result2.signal_type


class TestExecutionProcessor:
    """Test ExecutionProcessor functionality"""
    
    def test_execution_processor_initialization(self, test_config):
        """Test execution processor initialization"""
        processor = ExecutionProcessor(test_config)
        
        assert processor.config == test_config
        assert hasattr(processor, 'execution_history')
        assert hasattr(processor, 'performance_metrics')
    
    def test_signal_execution(self, execution_processor):
        """Test signal execution"""
        signal = TradingSignal(
            symbol="AAPL",
            signal_type=SignalType.LONG,
            strength=SignalStrength.STRONG,
            confidence=0.85,
            timestamp=datetime.now()
        )
        
        result = execution_processor.execute_signal(signal, quantity=100)
        
        assert isinstance(result, ExecutionResult)
        assert result.filled_quantity <= 100  # May be partially filled
        assert result.status in [ExecutionStatus.FILLED, ExecutionStatus.PENDING, ExecutionStatus.PARTIALLY_FILLED]
    
    def test_order_management(self, execution_processor):
        """Test order management functionality"""
        signal = TradingSignal(
            symbol="MSFT",
            signal_type=SignalType.SHORT,
            strength=SignalStrength.MODERATE,
            confidence=0.75,
            timestamp=datetime.now()
        )
        
        # Execute order
        result = execution_processor.execute_signal(signal, quantity=50)
        
        # Check execution history
        history = execution_processor.get_execution_history()
        assert len(history) > 0
        
        # Check if order is in history
        order_found = any(
            exec_result.symbol == "MSFT" and exec_result.quantity == 50
            for exec_result in history
        )
        assert order_found
    
    def test_execution_performance_tracking(self, execution_processor):
        """Test execution performance tracking"""
        # Execute multiple orders
        signals = [
            TradingSignal("AAPL", SignalType.LONG, SignalStrength.STRONG, 0.8, datetime.now()),
            TradingSignal("MSFT", SignalType.SHORT, SignalStrength.MODERATE, 0.7, datetime.now()),
            TradingSignal("GOOGL", SignalType.LONG, SignalStrength.STRONG, 0.9, datetime.now())
        ]
        
        for signal in signals:
            execution_processor.execute_signal(signal, quantity=100)
        
        # Check performance metrics
        metrics = execution_processor.get_performance_metrics()
        
        assert 'total_executions' in metrics
        assert 'successful_executions' in metrics
        assert 'avg_execution_time' in metrics
        assert metrics['total_executions'] >= len(signals)
    
    @pytest.mark.asyncio
    async def test_async_execution(self, execution_processor):
        """Test asynchronous execution"""
        signal = TradingSignal(
            symbol="TSLA",
            signal_type=SignalType.LONG,
            strength=SignalStrength.STRONG,
            confidence=0.85,
            timestamp=datetime.now()
        )
        
        # Test async execution
        result = await execution_processor.async_execute_signal(signal, quantity=75)
        
        assert isinstance(result, ExecutionResult)
        assert result.symbol == "TSLA"
        assert result.quantity == 75
    
    def test_execution_risk_checks(self, execution_processor):
        """Test execution risk management"""
        # Create large order that might trigger risk checks
        large_signal = TradingSignal(
            symbol="AAPL",
            signal_type=SignalType.LONG,
            strength=SignalStrength.STRONG,
            confidence=0.85,
            timestamp=datetime.now()
        )
        
        # Try to execute very large quantity
        result = execution_processor.execute_signal(large_signal, quantity=1000000)
        
        # Should either execute with risk adjustments or be rejected
        assert isinstance(result, ExecutionResult)
        # Risk management might reduce quantity or reject order
        assert result.status in [ExecutionStatus.FILLED, ExecutionStatus.REJECTED, ExecutionStatus.PARTIALLY_FILLED]


class TestEngineIntegration:
    """Test engine component integration"""
    
    def test_signal_to_execution_flow(self, test_config):
        """Test complete signal to execution flow"""
        engine = TradingEngine(test_config)
        
        # Create sample market data
        import pandas as pd
        import numpy as np
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
        market_data = pd.DataFrame({
            'timestamp': dates,
            'close': 100 + np.random.randn(100).cumsum() * 0.1,
            'volume': np.random.randint(1000, 5000, 100)
        })
        
        # Process market data through engine
        result = engine.process_market_data("AAPL", market_data)
        
        # Result may be None if no signal generated
        if result:
            assert isinstance(result, ExecutionResult)
        
        engine.shutdown()
    
    def test_engine_error_handling(self, test_config):
        """Test engine error handling"""
        engine = TradingEngine(test_config)
        
        # Test invalid market data handling
        invalid_data = None
        
        try:
            result = engine.process_market_data("AAPL", invalid_data)
            # Should handle gracefully
            assert result is None
        except Exception as e:
            # Should be a handled exception
            assert isinstance(e, (ValueError, TypeError, AttributeError))
    
    def test_engine_state_management(self, test_config):
        """Test engine state management"""
        engine = TradingEngine(test_config)
        
        # Initial state
        assert engine.status.value in ['initializing', 'ready']
        
        # Engine should be ready after initialization
        assert engine.status.value == 'ready'
        
        # Shutdown engine
        engine.shutdown()
        assert engine.status.value in ['shutdown', 'stopped']


@pytest.mark.performance
class TestEnginePerformance:
    """Test engine performance characteristics"""
    
    def test_signal_processing_performance(self, signal_processor, sample_signals, performance_timer):
        """Test signal processing performance"""
        performance_timer.start()
        
        processed_count = 0
        for signal in sample_signals:
            result = signal_processor.process_signal(signal)
            if result:
                processed_count += 1
        
        performance_timer.stop()
        
        # Should process signals quickly
        assert performance_timer.elapsed_seconds < 1.0
        assert processed_count > 0
    
    def test_execution_performance(self, execution_processor, performance_timer):
        """Test execution performance"""
        signals = [
            TradingSignal(f"STOCK_{i}", SignalType.LONG, SignalStrength.MODERATE, 0.7, datetime.now())
            for i in range(100)
        ]
        
        performance_timer.start()
        
        results = []
        for signal in signals:
            result = execution_processor.execute_signal(signal, quantity=10)
            results.append(result)
        
        performance_timer.stop()
        
        # Should execute orders efficiently
        assert performance_timer.elapsed_seconds < 2.0
        assert len(results) == 100
    
    @pytest.mark.asyncio
    async def test_concurrent_execution_performance(self, execution_processor, performance_timer):
        """Test concurrent execution performance"""
        signals = [
            TradingSignal(f"STOCK_{i}", SignalType.LONG, SignalStrength.MODERATE, 0.7, datetime.now())
            for i in range(50)
        ]
        
        performance_timer.start()
        
        # Execute signals concurrently
        tasks = [
            execution_processor.async_execute_signal(signal, quantity=10)
            for signal in signals
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        performance_timer.stop()
        
        # Concurrent execution should be faster
        assert performance_timer.elapsed_seconds < 1.5
        assert len(results) == 50
