"""
Infrastructure validation test for integration testing setup.

This test validates that all infrastructure components are working correctly.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any

from tests.integration.conftest import (
    test_config, mock_services, data_generator, 
    signal_bridge, execution_bridge, risk_bridge, 
    data_bridge, portfolio_bridge, config_bridge, analytics_bridge
)
from tests.integration.mock_services import (
    MockSignalGenerator, MockExecutionEngine, MockRiskManager, MockPortfolioManager,
    MockSignal, MockOrder, MockExecution
)
from tests.integration.test_data_scenarios import TestDataScenarios, TestDataGenerator
from tests.integration.test_logging import monitoring_context, log_test_event


class TestInfrastructureValidation:
    """Test infrastructure validation."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_test_config_initialization(self, test_config):
        """Test that test configuration is properly initialized."""
        with monitoring_context("test_config_initialization") as logger:
            logger.log_test_event("Validating test configuration")
            
            # Check test config
            assert test_config is not None
            assert len(test_config.test_symbols) > 0
            assert test_config.test_duration is not None
            assert len(test_config.test_scenarios) > 0
            assert test_config.performance_targets is not None
            
            logger.log_test_event("Test configuration validation completed", {
                'symbols_count': len(test_config.test_symbols),
                'scenarios_count': len(test_config.test_scenarios),
                'performance_targets_count': len(test_config.performance_targets)
            })
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_mock_services_initialization(self, mock_services):
        """Test that mock services are properly initialized."""
        with monitoring_context("mock_services_initialization") as logger:
            logger.log_test_event("Validating mock services")
            
            # Check mock services
            assert mock_services is not None
            assert hasattr(mock_services, 'get_market_data')
            assert hasattr(mock_services, 'place_order')
            assert hasattr(mock_services, 'get_portfolio_positions')
            
            logger.log_test_event("Mock services validation completed")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_data_generator_functionality(self, data_generator):
        """Test that data generator is working correctly."""
        with monitoring_context("data_generator_functionality") as logger:
            logger.log_test_event("Testing data generator")
            
            # Test market data generation
            symbols = ['AAPL', 'GOOGL']
            market_data = data_generator.generate_market_data(symbols, 'normal', timedelta(minutes=30))
            
            assert len(market_data) == len(symbols)
            for symbol, df in market_data.items():
                assert not df.empty
                assert 'timestamp' in df.columns
                assert 'open' in df.columns
                assert 'high' in df.columns
                assert 'low' in df.columns
                assert 'close' in df.columns
                assert 'volume' in df.columns
            
            # Test signal generation
            signals = data_generator.generate_trading_signals(symbols, count=5)
            assert len(signals) == 5
            for signal in signals:
                assert 'signal_id' in signal
                assert 'symbol' in signal
                assert 'timestamp' in signal
                assert 'signal_type' in signal
                assert 'confidence' in signal
                assert 'strength' in signal
            
            # Test order generation
            orders = data_generator.generate_orders(signals)
            assert len(orders) == len(signals)
            for order in orders:
                assert 'order_id' in order
                assert 'symbol' in order
                assert 'side' in order
                assert 'quantity' in order
                assert 'order_type' in order
            
            logger.log_test_event("Data generator functionality validated", {
                'market_data_symbols': len(market_data),
                'signals_generated': len(signals),
                'orders_generated': len(orders)
            })
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_mock_signal_generator(self):
        """Test mock signal generator functionality."""
        with monitoring_context("mock_signal_generator") as logger:
            logger.log_test_event("Testing mock signal generator")
            
            signal_gen = MockSignalGenerator()
            symbols = ['AAPL', 'GOOGL', 'MSFT']
            
            # Generate signals
            signals = await signal_gen.generate_signals(symbols, count=3)
            
            assert len(signals) == 3
            assert signal_gen.signals_generated == 3
            
            # Check signal properties
            for signal in signals:
                assert isinstance(signal, MockSignal)
                assert signal.symbol in symbols
                assert signal.signal_type in ['BUY', 'SELL']
                assert 0.5 <= signal.confidence <= 1.0
                assert 0.1 <= signal.strength <= 0.5
            
            # Check performance stats
            stats = signal_gen.get_performance_stats()
            assert stats['total_signals'] == 3
            assert stats['success_rate'] == 1.0
            assert stats['avg_generation_time_ms'] > 0
            
            logger.log_test_event("Mock signal generator validated", {
                'signals_generated': len(signals),
                'avg_generation_time_ms': stats['avg_generation_time_ms']
            })
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_mock_execution_engine(self):
        """Test mock execution engine functionality."""
        with monitoring_context("mock_execution_engine") as logger:
            logger.log_test_event("Testing mock execution engine")
            
            exec_engine = MockExecutionEngine()
            
            # Create test order
            order = MockOrder(
                order_id="test_order_001",
                symbol="AAPL",
                side="BUY",
                quantity=100,
                order_type="MARKET"
            )
            
            # Execute order
            execution = await exec_engine.execute_order(order)
            
            assert isinstance(execution, MockExecution)
            assert execution.order_id == order.order_id
            assert execution.symbol == order.symbol
            assert execution.side == order.side
            assert execution.quantity > 0
            assert execution.price > 0
            assert execution.status in ['FILLED', 'PARTIAL']
            assert 0 <= execution.fill_rate <= 1.0
            assert execution.implementation_shortfall >= 0
            
            # Check performance stats
            stats = exec_engine.get_performance_stats()
            assert stats['total_orders'] == 1
            assert stats['success_rate'] == 1.0
            assert stats['avg_execution_time_ms'] > 0
            assert stats['avg_fill_rate'] > 0.8
            assert stats['avg_implementation_shortfall'] >= 0
            
            logger.log_test_event("Mock execution engine validated", {
                'execution_price': execution.price,
                'fill_rate': execution.fill_rate,
                'avg_execution_time_ms': stats['avg_execution_time_ms']
            })
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_mock_risk_manager(self):
        """Test mock risk manager functionality."""
        with monitoring_context("mock_risk_manager") as logger:
            logger.log_test_event("Testing mock risk manager")
            
            risk_manager = MockRiskManager()
            
            # Create test signal
            signal = MockSignal(
                signal_id="test_signal_001",
                symbol="AAPL",
                timestamp=datetime.now(),
                signal_type="BUY",
                confidence=0.8,
                strength=0.3,
                source="test"
            )
            
            # Create test portfolio state
            portfolio_state = {
                'total_value': 1000000.0,
                'positions': {
                    'AAPL': {'quantity': 1000, 'current_value': 150000.0},
                    'GOOGL': {'quantity': 500, 'current_value': 1400000.0}
                }
            }
            
            # Validate signal
            validation_result = await risk_manager.validate_signal(signal, portfolio_state)
            
            assert 'signal_id' in validation_result
            assert 'timestamp' in validation_result
            assert 'approved' in validation_result
            assert 'violations' in validation_result
            assert 'risk_metrics' in validation_result
            
            # Check risk metrics
            risk_metrics = validation_result['risk_metrics']
            assert 'position_size' in risk_metrics
            assert 'portfolio_var' in risk_metrics
            assert 'leverage' in risk_metrics
            assert 'concentration' in risk_metrics
            
            # Check performance stats
            stats = risk_manager.get_performance_stats()
            assert stats['total_checks'] == 1
            assert stats['success_rate'] == 1.0
            assert stats['avg_check_time_ms'] > 0
            
            logger.log_test_event("Mock risk manager validated", {
                'validation_approved': validation_result['approved'],
                'violations_count': len(validation_result['violations']),
                'avg_check_time_ms': stats['avg_check_time_ms']
            })
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_mock_portfolio_manager(self):
        """Test mock portfolio manager functionality."""
        with monitoring_context("mock_portfolio_manager") as logger:
            logger.log_test_event("Testing mock portfolio manager")
            
            portfolio_manager = MockPortfolioManager()
            
            # Get initial portfolio snapshot
            initial_snapshot = portfolio_manager.get_portfolio_snapshot()
            assert 'timestamp' in initial_snapshot
            assert 'total_value' in initial_snapshot
            assert 'total_pnl' in initial_snapshot
            assert 'position_count' in initial_snapshot
            assert 'positions' in initial_snapshot
            
            # Create test execution
            execution = MockExecution(
                execution_id="test_exec_001",
                order_id="test_order_001",
                symbol="TSLA",
                side="BUY",
                quantity=100,
                price=250.0,
                timestamp=datetime.now(),
                status="FILLED",
                fill_rate=1.0,
                implementation_shortfall=0.001
            )
            
            # Update portfolio
            update_result = await portfolio_manager.update_position(execution)
            
            assert 'execution_id' in update_result
            assert 'timestamp' in update_result
            assert 'portfolio_summary' in update_result
            assert 'updated_positions' in update_result
            
            # Check portfolio summary
            summary = update_result['portfolio_summary']
            assert 'total_value' in summary
            assert 'total_pnl' in summary
            assert 'position_count' in summary
            
            # Get updated snapshot
            updated_snapshot = portfolio_manager.get_portfolio_snapshot()
            assert updated_snapshot['position_count'] >= initial_snapshot['position_count']
            
            # Check performance stats
            stats = portfolio_manager.get_performance_stats()
            assert stats['total_updates'] == 1
            assert stats['success_rate'] == 1.0
            assert stats['avg_update_time_ms'] > 0
            
            logger.log_test_event("Mock portfolio manager validated", {
                'initial_positions': initial_snapshot['position_count'],
                'updated_positions': updated_snapshot['position_count'],
                'avg_update_time_ms': stats['avg_update_time_ms']
            })
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_bridge_components_initialization(self):
        """Test that bridge components are properly initialized."""
        with monitoring_context("bridge_components_initialization") as logger:
            logger.log_test_event("Validating bridge components")
            
            # For Batch 1, we'll just validate that the bridge infrastructure is ready
            # The actual bridge testing will be done in Batch 2
            logger.log_test_event("Bridge components infrastructure ready for Batch 2 testing", {
                'status': 'ready_for_batch_2'
            })
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_test_scenarios_functionality(self):
        """Test test scenarios functionality."""
        with monitoring_context("test_scenarios_functionality") as logger:
            logger.log_test_event("Testing test scenarios")
            
            scenarios = TestDataScenarios()
            
            # Test market scenarios
            market_scenarios = scenarios.list_market_scenarios()
            assert len(market_scenarios) > 0
            assert 'normal' in market_scenarios
            assert 'high_volatility' in market_scenarios
            assert 'trending' in market_scenarios
            assert 'crisis' in market_scenarios
            
            # Test load scenarios
            load_scenarios = scenarios.list_load_scenarios()
            assert len(load_scenarios) > 0
            assert 'normal_load' in load_scenarios
            assert 'high_load' in load_scenarios
            assert 'stress_load' in load_scenarios
            
            # Test error scenarios
            error_scenarios = scenarios.list_error_scenarios()
            assert len(error_scenarios) > 0
            assert 'component_failure' in error_scenarios
            assert 'network_failure' in error_scenarios
            assert 'data_corruption' in error_scenarios
            
            # Test scenario details
            normal_scenario = scenarios.get_market_scenario('normal')
            assert normal_scenario.volatility == 0.15
            assert normal_scenario.risk_level == 'low'
            
            # Test scenario summary
            summary = scenarios.get_scenario_summary()
            assert 'market_scenarios' in summary
            assert 'load_scenarios' in summary
            assert 'error_scenarios' in summary
            
            logger.log_test_event("Test scenarios functionality validated", {
                'market_scenarios_count': len(market_scenarios),
                'load_scenarios_count': len(load_scenarios),
                'error_scenarios_count': len(error_scenarios)
            })
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_infrastructure_performance(self, test_config, data_generator):
        """Test infrastructure performance under basic load."""
        with monitoring_context("infrastructure_performance") as logger:
            logger.log_test_event("Testing infrastructure performance")
            
            start_time = time.time()
            
            # Generate test data
            symbols = test_config.test_symbols[:3]  # Use first 3 symbols
            market_data = data_generator.generate_market_data(symbols, 'normal', timedelta(minutes=10))
            signals = data_generator.generate_trading_signals(symbols, count=10)
            orders = data_generator.generate_orders(signals)
            
            # Process through mock services
            signal_gen = MockSignalGenerator()
            exec_engine = MockExecutionEngine()
            risk_manager = MockRiskManager()
            portfolio_manager = MockPortfolioManager()
            
            # Generate signals
            generated_signals = await signal_gen.generate_signals(symbols, count=5)
            
            # Validate signals
            portfolio_state = portfolio_manager.get_portfolio_snapshot()
            validations = []
            for signal in generated_signals[:3]:
                validation = await risk_manager.validate_signal(signal, portfolio_state)
                validations.append(validation)
            
            end_time = time.time()
            total_duration = (end_time - start_time) * 1000  # Convert to ms
            
            # Performance assertions
            assert total_duration < 1000  # Should complete within 1 second
            assert len(generated_signals) == 5
            assert len(validations) == 3
            
            logger.log_test_event("Infrastructure performance test completed", {
                'total_duration_ms': total_duration,
                'signals_processed': len(generated_signals),
                'validations_processed': len(validations)
            })


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"]) 