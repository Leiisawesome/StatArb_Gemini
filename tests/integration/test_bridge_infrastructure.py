"""
Bridge Architecture Integration Tests - Batch 2

This module tests the integration of bridge components (SignalBridge, ExecutionBridge, RiskBridge).
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List

from tests.integration.conftest import TestConfig
from tests.integration.mock_services import (
    MockSignalGenerator, MockExecutionEngine, MockRiskManager, MockPortfolioManager,
    MockSignal, MockOrder, MockExecution
)
from tests.integration.test_data_scenarios import TestDataScenarios
from tests.integration.test_logging import monitoring_context, log_test_event


class TestBridgeInfrastructure:
    """Test bridge infrastructure integration."""
    
    @pytest.mark.bridge
    @pytest.mark.asyncio
    async def test_signal_bridge_integration(self):
        """Test SignalBridge integration with mock services."""
        with monitoring_context("signal_bridge_integration") as logger:
            logger.log_test_event("Testing SignalBridge integration")
            
            # Create test components
            test_config = TestConfig()
            signal_gen = MockSignalGenerator()
            
            # Generate test signals
            symbols = test_config.test_symbols[:3]
            signals = await signal_gen.generate_signals(symbols, count=5)
            
            # Validate signal properties
            assert len(signals) == 5
            for signal in signals:
                assert isinstance(signal, MockSignal)
                assert signal.symbol in symbols
                assert signal.signal_type in ['BUY', 'SELL']
                assert 0.5 <= signal.confidence <= 1.0
                assert 0.1 <= signal.strength <= 0.5
            
            # Check performance stats
            stats = signal_gen.get_performance_stats()
            assert stats['total_signals'] == 5
            assert stats['success_rate'] == 1.0
            assert stats['avg_generation_time_ms'] > 0
            
            logger.log_test_event("SignalBridge integration validated", {
                'signals_generated': len(signals),
                'avg_generation_time_ms': stats['avg_generation_time_ms'],
                'symbols_tested': len(symbols)
            })
    
    @pytest.mark.bridge
    @pytest.mark.asyncio
    async def test_execution_bridge_integration(self):
        """Test ExecutionBridge integration with mock services."""
        with monitoring_context("execution_bridge_integration") as logger:
            logger.log_test_event("Testing ExecutionBridge integration")
            
            # Create test components
            exec_engine = MockExecutionEngine()
            
            # Create test orders
            orders = []
            for i in range(3):
                order = MockOrder(
                    order_id=f"test_order_{i:03d}",
                    symbol="AAPL",
                    side="BUY" if i % 2 == 0 else "SELL",
                    quantity=100 + i * 50,
                    order_type="MARKET"
                )
                orders.append(order)
            
            # Execute orders
            executions = []
            for order in orders:
                execution = await exec_engine.execute_order(order)
                executions.append(execution)
            
            # Validate execution properties
            assert len(executions) == 3
            for execution in executions:
                assert isinstance(execution, MockExecution)
                assert execution.order_id in [order.order_id for order in orders]
                assert execution.symbol == "AAPL"
                assert execution.quantity > 0
                assert execution.price > 0
                assert execution.status in ['FILLED', 'PARTIAL']
                assert 0 <= execution.fill_rate <= 1.0
                assert execution.implementation_shortfall >= 0
            
            # Check performance stats
            stats = exec_engine.get_performance_stats()
            assert stats['total_orders'] == 3
            assert stats['success_rate'] == 1.0
            assert stats['avg_execution_time_ms'] > 0
            assert stats['avg_fill_rate'] > 0.8
            
            logger.log_test_event("ExecutionBridge integration validated", {
                'orders_executed': len(executions),
                'avg_execution_time_ms': stats['avg_execution_time_ms'],
                'avg_fill_rate': stats['avg_fill_rate']
            })
    
    @pytest.mark.bridge
    @pytest.mark.asyncio
    async def test_risk_bridge_integration(self):
        """Test RiskBridge integration with mock services."""
        with monitoring_context("risk_bridge_integration") as logger:
            logger.log_test_event("Testing RiskBridge integration")
            
            # Create test components
            risk_manager = MockRiskManager()
            
            # Create test signals
            signals = [
                MockSignal(
                    signal_id=f"test_signal_{i:03d}",
                    symbol="AAPL",
                    timestamp=datetime.now(),
                    signal_type="BUY" if i % 2 == 0 else "SELL",
                    confidence=0.7 + i * 0.1,
                    strength=0.2 + i * 0.1,
                    source="test"
                )
                for i in range(3)
            ]
            
            # Create test portfolio state
            portfolio_state = {
                'total_value': 1000000.0,
                'positions': {
                    'AAPL': {'quantity': 1000, 'current_value': 150000.0},
                    'GOOGL': {'quantity': 500, 'current_value': 1400000.0},
                    'MSFT': {'quantity': 800, 'current_value': 240000.0}
                }
            }
            
            # Validate signals
            validations = []
            for signal in signals:
                validation = await risk_manager.validate_signal(signal, portfolio_state)
                validations.append(validation)
            
            # Validate risk validation results
            assert len(validations) == 3
            for validation in validations:
                assert 'signal_id' in validation
                assert 'timestamp' in validation
                assert 'approved' in validation
                assert 'violations' in validation
                assert 'risk_metrics' in validation
                
                # Check risk metrics
                risk_metrics = validation['risk_metrics']
                assert 'position_size' in risk_metrics
                assert 'portfolio_var' in risk_metrics
                assert 'leverage' in risk_metrics
                assert 'concentration' in risk_metrics
            
            # Check performance stats
            stats = risk_manager.get_performance_stats()
            assert stats['total_checks'] == 3
            assert stats['success_rate'] == 1.0
            assert stats['avg_check_time_ms'] > 0
            
            logger.log_test_event("RiskBridge integration validated", {
                'signals_validated': len(validations),
                'avg_check_time_ms': stats['avg_check_time_ms'],
                'risk_violations': stats['risk_violations']
            })
    
    @pytest.mark.bridge
    @pytest.mark.asyncio
    async def test_bridge_component_interaction(self):
        """Test interaction between bridge components."""
        with monitoring_context("bridge_component_interaction") as logger:
            logger.log_test_event("Testing bridge component interaction")
            
            # Create all bridge components
            signal_gen = MockSignalGenerator()
            exec_engine = MockExecutionEngine()
            risk_manager = MockRiskManager()
            portfolio_manager = MockPortfolioManager()
            
            # Create test portfolio state
            portfolio_state = {
                'total_value': 1000000.0,
                'positions': {
                    'AAPL': {'quantity': 1000, 'current_value': 150000.0},
                    'GOOGL': {'quantity': 500, 'current_value': 1400000.0}
                }
            }
            
            # Step 1: Generate signals
            symbols = ['AAPL', 'GOOGL']
            signals = await signal_gen.generate_signals(symbols, count=3)
            logger.log_test_event("Signals generated", {'count': len(signals)})
            
            # Step 2: Validate signals through risk manager
            valid_signals = []
            for signal in signals:
                validation = await risk_manager.validate_signal(signal, portfolio_state)
                if validation['approved']:
                    valid_signals.append(signal)
            
            logger.log_test_event("Signals validated", {
                'total_signals': len(signals),
                'valid_signals': len(valid_signals)
            })
            
            # Step 3: Create orders for valid signals
            orders = []
            for signal in valid_signals:
                order = MockOrder(
                    order_id=f"order_{signal.signal_id}",
                    symbol=signal.symbol,
                    side=signal.signal_type,
                    quantity=int(1000 * signal.strength),
                    order_type="MARKET",
                    signal_id=signal.signal_id
                )
                orders.append(order)
            
            logger.log_test_event("Orders created", {'count': len(orders)})
            
            # Step 4: Execute orders
            executions = []
            for order in orders:
                execution = await exec_engine.execute_order(order)
                executions.append(execution)
            
            logger.log_test_event("Orders executed", {'count': len(executions)})
            
            # Step 5: Update portfolio
            for execution in executions:
                await portfolio_manager.update_position(execution)
            
            # Validate final state
            final_snapshot = portfolio_manager.get_portfolio_snapshot()
            
            # Performance assertions
            signal_stats = signal_gen.get_performance_stats()
            exec_stats = exec_engine.get_performance_stats()
            risk_stats = risk_manager.get_performance_stats()
            portfolio_stats = portfolio_manager.get_performance_stats()
            
            assert signal_stats['total_signals'] == 3
            assert exec_stats['total_orders'] == len(valid_signals)
            assert risk_stats['total_checks'] == 3
            assert portfolio_stats['total_updates'] == len(executions)
            
            logger.log_test_event("Bridge component interaction validated", {
                'signals_generated': signal_stats['total_signals'],
                'orders_executed': exec_stats['total_orders'],
                'risk_checks': risk_stats['total_checks'],
                'portfolio_updates': portfolio_stats['total_updates'],
                'final_positions': final_snapshot['position_count']
            })
    
    @pytest.mark.bridge
    @pytest.mark.asyncio
    async def test_bridge_performance_under_load(self):
        """Test bridge performance under load."""
        with monitoring_context("bridge_performance_under_load") as logger:
            logger.log_test_event("Testing bridge performance under load")
            
            start_time = time.time()
            
            # Create components
            signal_gen = MockSignalGenerator()
            exec_engine = MockExecutionEngine()
            risk_manager = MockRiskManager()
            portfolio_manager = MockPortfolioManager()
            
            # Load test parameters
            symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']
            signal_count = 20
            portfolio_state = {
                'total_value': 1000000.0,
                'positions': {symbol: {'quantity': 100, 'current_value': 15000.0} for symbol in symbols}
            }
            
            # Generate signals
            signals = await signal_gen.generate_signals(symbols, count=signal_count)
            
            # Validate signals
            validations = []
            for signal in signals:
                validation = await risk_manager.validate_signal(signal, portfolio_state)
                validations.append(validation)
            
            # Create and execute orders for approved signals
            approved_signals = [s for s, v in zip(signals, validations) if v['approved']]
            orders = []
            executions = []
            
            for signal in approved_signals:
                order = MockOrder(
                    order_id=f"order_{signal.signal_id}",
                    symbol=signal.symbol,
                    side=signal.signal_type,
                    quantity=100,
                    order_type="MARKET",
                    signal_id=signal.signal_id
                )
                orders.append(order)
            
            # Execute orders
            for order in orders:
                execution = await exec_engine.execute_order(order)
                executions.append(execution)
            
            # Update portfolio
            for execution in executions:
                await portfolio_manager.update_position(execution)
            
            end_time = time.time()
            total_duration = (end_time - start_time) * 1000  # Convert to ms
            
            # Performance assertions
            assert total_duration < 10000  # Should complete within 10 seconds
            assert len(signals) == signal_count
            assert len(validations) == signal_count
            assert len(executions) == len(approved_signals)
            
            # Check performance stats
            signal_stats = signal_gen.get_performance_stats()
            exec_stats = exec_engine.get_performance_stats()
            risk_stats = risk_manager.get_performance_stats()
            portfolio_stats = portfolio_manager.get_performance_stats()
            
            logger.log_test_event("Bridge performance under load validated", {
                'total_duration_ms': total_duration,
                'signals_processed': signal_stats['total_signals'],
                'orders_executed': exec_stats['total_orders'],
                'risk_checks': risk_stats['total_checks'],
                'portfolio_updates': portfolio_stats['total_updates'],
                'avg_signal_time_ms': signal_stats['avg_generation_time_ms'],
                'avg_execution_time_ms': exec_stats['avg_execution_time_ms'],
                'avg_risk_check_time_ms': risk_stats['avg_check_time_ms']
            })


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s", "-m", "bridge"]) 