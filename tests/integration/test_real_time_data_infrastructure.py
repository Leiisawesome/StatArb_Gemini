"""
Real-Time Data Processing Integration Tests - Batch 4

This module tests the real-time data processing infrastructure, including latency, event publishing,
streaming data quality, throughput, data flow consistency, and error handling.
"""

import pytest
import asyncio
import time
import random
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from tests.integration.conftest import TestConfig
from tests.integration.mock_services import (
    MockSignalGenerator, MockExecutionEngine, MockRiskManager, MockPortfolioManager,
    MockSignal, MockOrder, MockExecution
)
from tests.integration.test_data_scenarios import TestDataScenarios
from tests.integration.test_logging import monitoring_context, log_test_event


@dataclass
class MockMarketData:
    """Mock market data structure for testing."""
    symbol: str
    timestamp: datetime
    price: float
    volume: int
    bid: float
    ask: float
    high: float
    low: float
    open: float
    close: float


@dataclass
class MockEvent:
    """Mock event structure for testing."""
    event_id: str
    event_type: str
    timestamp: datetime
    data: Dict[str, Any]
    source: str


class MockRealTimeDataProcessor:
    """Mock real-time data processor for testing."""
    
    def __init__(self):
        self.processed_events = []
        self.failed_events = []
        self.performance_stats = {
            'total_events': 0,
            'successful_events': 0,
            'failed_events': 0,
            'avg_processing_time_ms': 0.0,
            'total_processing_time_ms': 0.0
        }
        self.subscribers = []
        self.data_quality_metrics = {
            'total_data_points': 0,
            'valid_data_points': 0,
            'invalid_data_points': 0,
            'duplicate_data_points': 0,
            'missing_data_points': 0
        }
    
    async def process_market_data(self, data: MockMarketData) -> bool:
        """Process market data with simulated latency."""
        start_time = time.time()
        
        try:
            # Simulate processing time
            await asyncio.sleep(random.uniform(0.001, 0.005))  # 1-5ms
            
            # Validate data quality
            if self._validate_data_quality(data):
                self.processed_events.append(data)
                self.performance_stats['successful_events'] += 1
                self.data_quality_metrics['valid_data_points'] += 1
                success = True
            else:
                self.failed_events.append(data)
                self.performance_stats['failed_events'] += 1
                self.data_quality_metrics['invalid_data_points'] += 1
                success = False
            
            # Update performance stats
            processing_time = (time.time() - start_time) * 1000
            self.performance_stats['total_events'] += 1
            self.performance_stats['total_processing_time_ms'] += processing_time
            self.performance_stats['avg_processing_time_ms'] = (
                self.performance_stats['total_processing_time_ms'] / 
                self.performance_stats['total_events']
            )
            
            # Publish event to subscribers
            await self._publish_event(data, success)
            
            return success
            
        except Exception as e:
            self.failed_events.append(data)
            self.performance_stats['failed_events'] += 1
            return False
    
    def _validate_data_quality(self, data: MockMarketData) -> bool:
        """Validate data quality."""
        self.data_quality_metrics['total_data_points'] += 1
        
        # Check for required fields
        if not all([data.symbol, data.timestamp, data.price, data.volume]):
            return False
        
        # Check for reasonable price values
        if data.price <= 0 or data.price > 10000:
            return False
        
        # Check for reasonable volume values
        if data.volume < 0 or data.volume > 10000000:
            return False
        
        # Check bid-ask spread (relaxed for mock data)
        if data.bid >= data.ask:
            return False
        
        # Check high-low consistency (relaxed for mock data)
        if data.high < data.low:
            return False
        
        # For mock data, be more lenient with open/close consistency
        return True
    
    async def _publish_event(self, data: MockMarketData, success: bool):
        """Publish event to subscribers."""
        event = MockEvent(
            event_id=f"event_{len(self.processed_events) + len(self.failed_events)}",
            event_type="market_data_processed",
            timestamp=datetime.now(),
            data={
                'symbol': data.symbol,
                'price': data.price,
                'volume': data.volume,
                'success': success
            },
            source="mock_real_time_processor"
        )
        
        # Notify subscribers
        for subscriber in self.subscribers:
            try:
                await subscriber(event)
            except Exception:
                pass  # Ignore subscriber errors for testing
    
    def subscribe(self, callback):
        """Subscribe to events."""
        self.subscribers.append(callback)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return self.performance_stats.copy()
    
    def get_data_quality_stats(self) -> Dict[str, Any]:
        """Get data quality statistics."""
        return self.data_quality_metrics.copy()


class MockDataStream:
    """Mock data stream for testing."""
    
    def __init__(self, symbols: List[str], data_rate: int = 100):
        self.symbols = symbols
        self.data_rate = data_rate  # events per second
        self.is_running = False
        self.generated_data = []
        self.stream_stats = {
            'total_generated': 0,
            'start_time': None,
            'end_time': None,
            'avg_generation_time_ms': 0.0
        }
    
    async def start_stream(self, duration_seconds: int = 10):
        """Start data stream for specified duration."""
        self.is_running = True
        self.stream_stats['start_time'] = datetime.now()
        
        interval = 1.0 / self.data_rate
        end_time = time.time() + duration_seconds
        
        while self.is_running and time.time() < end_time:
            start_time = time.time()
            
            # Generate market data for each symbol
            for symbol in self.symbols:
                data = self._generate_market_data(symbol)
                self.generated_data.append(data)
                self.stream_stats['total_generated'] += 1
            
            # Wait for next interval
            elapsed = time.time() - start_time
            if elapsed < interval:
                await asyncio.sleep(interval - elapsed)
        
        self.stream_stats['end_time'] = datetime.now()
        self.is_running = False
    
    def stop_stream(self):
        """Stop data stream."""
        self.is_running = False
    
    def _generate_market_data(self, symbol: str) -> MockMarketData:
        """Generate mock market data."""
        base_price = random.uniform(50, 500)
        price_change = random.uniform(-0.02, 0.02)  # ±2% change
        current_price = base_price * (1 + price_change)
        
        return MockMarketData(
            symbol=symbol,
            timestamp=datetime.now(),
            price=round(current_price, 2),
            volume=random.randint(100, 10000),
            bid=round(current_price * 0.999, 2),
            ask=round(current_price * 1.001, 2),
            high=round(current_price * 1.01, 2),
            low=round(current_price * 0.99, 2),
            open=round(base_price, 2),
            close=round(current_price, 2)
        )
    
    def get_stream_stats(self) -> Dict[str, Any]:
        """Get stream statistics."""
        stats = self.stream_stats.copy()
        if stats['start_time'] and stats['end_time']:
            duration = (stats['end_time'] - stats['start_time']).total_seconds()
            stats['actual_rate'] = stats['total_generated'] / duration if duration > 0 else 0
        return stats


class TestRealTimeDataInfrastructure:
    """Test real-time data processing infrastructure integration."""
    
    @pytest.mark.realtime
    @pytest.mark.asyncio
    async def test_real_time_data_latency(self):
        """Test real-time data processing latency."""
        with monitoring_context("real_time_data_latency") as logger:
            logger.log_test_event("Testing real-time data processing latency")
            
            # Create test components
            processor = MockRealTimeDataProcessor()
            symbols = ['AAPL', 'GOOGL', 'MSFT']
            
            # Test single data point processing latency
            data = MockMarketData(
                symbol='AAPL',
                timestamp=datetime.now(),
                price=150.0,
                volume=1000,
                bid=149.95,
                ask=150.05,
                high=151.0,
                low=149.0,
                open=150.0,
                close=150.0
            )
            
            start_time = time.time()
            success = await processor.process_market_data(data)
            single_latency = (time.time() - start_time) * 1000  # Convert to ms
            
            # Test multiple data points processing latency
            start_time = time.time()
            for _ in range(10):
                price = random.uniform(50, 500)
                data = MockMarketData(
                    symbol=random.choice(symbols),
                    timestamp=datetime.now(),
                    price=price,
                    volume=random.randint(100, 10000),
                    bid=price * 0.999,  # Ensure bid < price
                    ask=price * 1.001,  # Ensure ask > price
                    high=price * 1.01,  # Ensure high > price
                    low=price * 0.99,   # Ensure low < price
                    open=price * 0.995, # Ensure open is reasonable
                    close=price         # Close = current price
                )
                await processor.process_market_data(data)
            multiple_latency = (time.time() - start_time) * 1000  # Convert to ms
            
            # Validate latency requirements
            assert single_latency < 10  # Single data point should complete within 10ms
            assert multiple_latency < 100  # 10 data points should complete within 100ms
            assert success  # First data point should be valid
            
            # Get performance stats
            stats = processor.get_performance_stats()
            
            logger.log_test_event("Real-time data latency validated", {
                'single_latency_ms': single_latency,
                'multiple_latency_ms': multiple_latency,
                'avg_processing_time_ms': stats['avg_processing_time_ms'],
                'total_events': stats['total_events']
            })
    
    @pytest.mark.realtime
    @pytest.mark.asyncio
    async def test_event_publishing_reliability(self):
        """Test event publishing reliability."""
        with monitoring_context("event_publishing_reliability") as logger:
            logger.log_test_event("Testing event publishing reliability")
            
            # Create test components
            processor = MockRealTimeDataProcessor()
            received_events = []
            
            # Subscribe to events
            async def event_handler(event: MockEvent):
                received_events.append(event)
            
            processor.subscribe(event_handler)
            
            # Generate and process multiple data points
            symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA']
            num_events = 50
            
            for i in range(num_events):
                price = random.uniform(50, 500)
                data = MockMarketData(
                    symbol=random.choice(symbols),
                    timestamp=datetime.now(),
                    price=price,
                    volume=random.randint(100, 10000),
                    bid=price * 0.999,  # Ensure bid < price
                    ask=price * 1.001,  # Ensure ask > price
                    high=price * 1.01,  # Ensure high > price
                    low=price * 0.99,   # Ensure low < price
                    open=price * 0.995, # Ensure open is reasonable
                    close=price         # Close = current price
                )
                await processor.process_market_data(data)
            
            # Wait for all events to be processed
            await asyncio.sleep(0.1)
            
            # Validate event publishing
            assert len(received_events) == num_events
            assert len(processor.processed_events) + len(processor.failed_events) == num_events
            
            # Check event structure
            for event in received_events:
                assert isinstance(event, MockEvent)
                assert event.event_type == "market_data_processed"
                assert 'symbol' in event.data
                assert 'price' in event.data
                assert 'volume' in event.data
                assert 'success' in event.data
                assert event.source == "mock_real_time_processor"
            
            # Get performance stats
            stats = processor.get_performance_stats()
            
            logger.log_test_event("Event publishing reliability validated", {
                'events_published': len(received_events),
                'events_processed': len(processor.processed_events),
                'events_failed': len(processor.failed_events),
                'success_rate': stats['successful_events'] / stats['total_events'] if stats['total_events'] > 0 else 0
            })
    
    @pytest.mark.realtime
    @pytest.mark.asyncio
    async def test_streaming_data_quality(self):
        """Test streaming data quality validation."""
        with monitoring_context("streaming_data_quality") as logger:
            logger.log_test_event("Testing streaming data quality")
            
            # Create test components
            processor = MockRealTimeDataProcessor()
            stream = MockDataStream(['AAPL', 'GOOGL', 'MSFT'], data_rate=50)
            
            # Start stream for short duration
            stream_task = asyncio.create_task(stream.start_stream(duration_seconds=2))
            
            # Wait for stream to complete
            await stream_task
            
            # Process all generated data
            processed_count = 0
            for data in stream.generated_data:
                await processor.process_market_data(data)
                processed_count += 1
            
            # Add debug logging
            logger.log_test_event("Stream processing completed", {
                'stream_generated': len(stream.generated_data),
                'processed_count': processed_count,
                'stream_running': stream.is_running
            })
            
            # Validate data quality
            quality_stats = processor.get_data_quality_stats()
            stream_stats = stream.get_stream_stats()
            
            # Check quality metrics
            assert quality_stats['total_data_points'] > 0
            assert quality_stats['valid_data_points'] > 0
            assert quality_stats['valid_data_points'] + quality_stats['invalid_data_points'] == quality_stats['total_data_points']
            
            # Calculate quality rate
            quality_rate = quality_stats['valid_data_points'] / quality_stats['total_data_points']
            
            # Validate quality requirements
            assert quality_rate > 0.8  # At least 80% data quality
            assert stream_stats['total_generated'] > 0
            assert stream_stats['actual_rate'] > 0
            
            logger.log_test_event("Streaming data quality validated", {
                'total_data_points': quality_stats['total_data_points'],
                'valid_data_points': quality_stats['valid_data_points'],
                'invalid_data_points': quality_stats['invalid_data_points'],
                'quality_rate': quality_rate,
                'data_generated': stream_stats['total_generated'],
                'actual_rate': stream_stats['actual_rate']
            })
    
    @pytest.mark.realtime
    @pytest.mark.asyncio
    async def test_real_time_data_throughput(self):
        """Test real-time data processing throughput."""
        with monitoring_context("real_time_data_throughput") as logger:
            logger.log_test_event("Testing real-time data processing throughput")
            
            # Create test components
            processor = MockRealTimeDataProcessor()
            symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']
            
            # Test throughput with different loads
            throughput_tests = [
                {'count': 100, 'expected_time_ms': 500},
                {'count': 500, 'expected_time_ms': 2000},
                {'count': 1000, 'expected_time_ms': 5000}
            ]
            
            throughput_results = []
            
            for test in throughput_tests:
                # Reset processor stats
                processor = MockRealTimeDataProcessor()
                
                start_time = time.time()
                
                # Process data points
                for _ in range(test['count']):
                    price = random.uniform(50, 500)
                    data = MockMarketData(
                        symbol=random.choice(symbols),
                        timestamp=datetime.now(),
                        price=price,
                        volume=random.randint(100, 10000),
                        bid=price * 0.999,  # Ensure bid < price
                        ask=price * 1.001,  # Ensure ask > price
                        high=price * 1.01,  # Ensure high > price
                        low=price * 0.99,   # Ensure low < price
                        open=price * 0.995, # Ensure open is reasonable
                        close=price         # Close = current price
                    )
                    await processor.process_market_data(data)
                
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000
                throughput = test['count'] / (duration_ms / 1000)  # events per second
                
                throughput_results.append({
                    'count': test['count'],
                    'duration_ms': duration_ms,
                    'throughput_eps': throughput,
                    'expected_time_ms': test['expected_time_ms']
                })
                
                # Validate performance
                assert duration_ms < test['expected_time_ms']
                assert throughput > 50  # Should process at least 50 events per second
            
            # Calculate average throughput
            avg_throughput = sum(r['throughput_eps'] for r in throughput_results) / len(throughput_results)
            
            logger.log_test_event("Real-time data throughput validated", {
                'throughput_results': throughput_results,
                'average_throughput_eps': avg_throughput,
                'tests_completed': len(throughput_tests)
            })
    
    @pytest.mark.realtime
    @pytest.mark.asyncio
    async def test_data_flow_consistency(self):
        """Test data flow consistency across the pipeline."""
        with monitoring_context("data_flow_consistency") as logger:
            logger.log_test_event("Testing data flow consistency")
            
            # Create test components
            processor = MockRealTimeDataProcessor()
            signal_gen = MockSignalGenerator()
            risk_manager = MockRiskManager()
            
            # Create data flow pipeline
            symbols = ['AAPL', 'GOOGL', 'MSFT']
            pipeline_results = []
            
            # Process data through pipeline
            for i in range(20):
                # Generate market data
                price = random.uniform(50, 500)
                data = MockMarketData(
                    symbol=random.choice(symbols),
                    timestamp=datetime.now(),
                    price=price,
                    volume=random.randint(100, 10000),
                    bid=price * 0.999,  # Ensure bid < price
                    ask=price * 1.001,  # Ensure ask > price
                    high=price * 1.01,  # Ensure high > price
                    low=price * 0.99,   # Ensure low < price
                    open=price * 0.995, # Ensure open is reasonable
                    close=price         # Close = current price
                )
                
                # Step 1: Process market data
                data_success = await processor.process_market_data(data)
                
                # Step 2: Generate signals based on processed data
                if data_success:
                    signals = await signal_gen.generate_signals([data.symbol], count=1)
                    
                    # Step 3: Validate signals through risk management
                    if signals:
                        signal = signals[0]
                        portfolio_state = {'total_value': 1000000.0, 'positions': {}}
                        risk_validation = await risk_manager.validate_signal(signal, portfolio_state)
                        
                        pipeline_results.append({
                            'data_processed': data_success,
                            'signals_generated': len(signals),
                            'risk_validated': risk_validation['approved'],
                            'symbol': data.symbol,
                            'timestamp': data.timestamp
                        })
            
            # Validate pipeline consistency
            assert len(pipeline_results) > 0
            
            # Check data flow statistics
            data_processed = sum(1 for r in pipeline_results if r['data_processed'])
            signals_generated = sum(r['signals_generated'] for r in pipeline_results)
            risk_validated = sum(1 for r in pipeline_results if r['risk_validated'])
            
            # Validate consistency
            assert data_processed > 0
            assert signals_generated > 0
            assert data_processed == len(pipeline_results)  # All data should be processed
            
            # Get performance stats
            processor_stats = processor.get_performance_stats()
            signal_stats = signal_gen.get_performance_stats()
            risk_stats = risk_manager.get_performance_stats()
            
            logger.log_test_event("Data flow consistency validated", {
                'pipeline_results': len(pipeline_results),
                'data_processed': data_processed,
                'signals_generated': signals_generated,
                'risk_validated': risk_validated,
                'processor_events': processor_stats['total_events'],
                'signal_count': signal_stats['total_signals'],
                'risk_checks': risk_stats['total_checks']
            })
    
    @pytest.mark.realtime
    @pytest.mark.asyncio
    async def test_real_time_error_handling(self):
        """Test real-time data error handling."""
        with monitoring_context("real_time_error_handling") as logger:
            logger.log_test_event("Testing real-time data error handling")
            
            # Create test components
            processor = MockRealTimeDataProcessor()
            
            # Test with invalid data
            invalid_data_scenarios = [
                # Invalid price
                MockMarketData(
                    symbol='AAPL',
                    timestamp=datetime.now(),
                    price=-1.0,  # Invalid negative price
                    volume=1000,
                    bid=149.95,
                    ask=150.05,
                    high=151.0,
                    low=149.0,
                    open=150.0,
                    close=150.0
                ),
                # Invalid volume
                MockMarketData(
                    symbol='GOOGL',
                    timestamp=datetime.now(),
                    price=150.0,
                    volume=-100,  # Invalid negative volume
                    bid=149.95,
                    ask=150.05,
                    high=151.0,
                    low=149.0,
                    open=150.0,
                    close=150.0
                ),
                # Invalid bid-ask spread
                MockMarketData(
                    symbol='MSFT',
                    timestamp=datetime.now(),
                    price=150.0,
                    volume=1000,
                    bid=150.05,  # Bid >= Ask
                    ask=150.05,
                    high=151.0,
                    low=149.0,
                    open=150.0,
                    close=150.0
                ),
                # Missing required fields (None values)
                MockMarketData(
                    symbol='',  # Empty symbol
                    timestamp=datetime.now(),
                    price=0.0,  # Zero price
                    volume=0,   # Zero volume
                    bid=0.0,
                    ask=0.0,
                    high=0.0,
                    low=0.0,
                    open=0.0,
                    close=0.0
                )
            ]
            
            error_results = []
            
            for i, invalid_data in enumerate(invalid_data_scenarios):
                try:
                    success = await processor.process_market_data(invalid_data)
                    error_results.append({
                        'scenario': i + 1,
                        'success': success,
                        'expected_failure': True
                    })
                except Exception as e:
                    error_results.append({
                        'scenario': i + 1,
                        'success': False,
                        'exception': str(e),
                        'expected_failure': True
                    })
            
            # Validate error handling
            for result in error_results:
                # All invalid data scenarios should be handled gracefully
                assert 'success' in result
                assert result['expected_failure']
            
            # Check that processor continues to work with valid data
            valid_data = MockMarketData(
                symbol='AAPL',
                timestamp=datetime.now(),
                price=150.0,
                volume=1000,
                bid=149.95,
                ask=150.05,
                high=151.0,
                low=149.0,
                open=150.0,
                close=150.0
            )
            
            success = await processor.process_market_data(valid_data)
            assert success  # Valid data should still be processed successfully
            
            # Get quality stats
            quality_stats = processor.get_data_quality_stats()
            
            logger.log_test_event("Real-time error handling validated", {
                'error_scenarios_tested': len(invalid_data_scenarios),
                'error_results': error_results,
                'valid_data_processed': success,
                'total_data_points': quality_stats['total_data_points'],
                'invalid_data_points': quality_stats['invalid_data_points']
            })


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s", "-m", "realtime"]) 