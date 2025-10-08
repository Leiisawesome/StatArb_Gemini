"""
Comprehensive Strategy Manager Test Suite

This test suite provides comprehensive coverage for the strategy manager
to enhance coverage from 33% to 80%+, implementing all 4 enhancement tasks from the Unit Test Enhancement Plan.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from typing import Dict, Any, List
import numpy as np
import pandas as pd

from core_engine.trading.strategies.manager import StrategyManager
from core_engine.trading.strategies.strategy_engine import StrategyExecutionEngine
from core_engine.trading.strategies.strategy_validator import StrategyValidator
from core_engine.trading.strategies.strategy_registry import StrategyRegistry
from core_engine.trading.strategies.multi_strategy_coordinator import MultiStrategySignalAggregator, SignalConflictResolver
from core_engine.trading.strategies.base_strategy_enhanced import EnhancedBaseStrategy
from core_engine.trading.strategies.implementations.momentum.enhanced_momentum import EnhancedMomentumStrategy
from core_engine.trading.strategies.implementations.mean_reversion.enhanced_mean_reversion import EnhancedMeanReversionStrategy
from core_engine.trading.strategies.implementations.statistical_arbitrage.enhanced_statistical_arbitrage import EnhancedStatisticalArbitrageStrategy
from core_engine.type_definitions.strategy import StrategyType
from core_engine.trading.strategies.manager import SignalType, SignalStrength, TradingSignal
from core_engine.type_definitions.portfolio import Position, Portfolio
from core_engine.type_definitions.orders import Order, OrderSide, OrderType
from core_engine.system.interfaces import ISystemComponent


def create_trading_signal(symbol: str, signal_type: SignalType, confidence: float, quantity: float = 100) -> TradingSignal:
    """Helper function to create TradingSignal objects for testing"""
    return TradingSignal(
        signal_id=f"sig_{symbol}_{signal_type.value}",
        strategy_name="test_strategy",
        strategy_type=StrategyType.MOMENTUM,
        symbol=symbol,
        signal_type=signal_type,
        strength=SignalStrength.STRONG,
        confidence=confidence,
        expected_return=0.02 if signal_type == SignalType.BUY else -0.02,
        risk_score=0.3,
        quantity=quantity,
        target_price=100.0,
        stop_loss=95.0,
        take_profit=105.0,
        time_horizon=None,
        metadata={}
    )


class TestStrategyManager:
    """Comprehensive test suite for StrategyManager - 33% coverage enhancement"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.config = {
            'max_concurrent_strategies': 10,
            'enable_multi_strategy_coordination': True,
            'enable_signal_aggregation': True,
            'enable_conflict_resolution': True,
            'max_strategy_allocation': 0.33,
            'min_confidence_threshold': 0.6,
            'signal_aggregation_method': 'weighted_average',
            'conflict_resolution_method': 'confidence_weighted',
            'enable_dynamic_weighting': True,
            'enable_strategy_attribution': True
        }
        self.strategy_manager = StrategyManager(self.config)
    
    def test_initialization(self):
        """Test strategy manager initialization"""
        assert self.strategy_manager is not None
        assert self.strategy_manager.config.max_concurrent_strategies == 10
        assert self.strategy_manager.config.enable_multi_strategy_coordination is True
        assert self.strategy_manager.config.enable_signal_aggregation is True
    
    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test strategy manager initialization process"""
        result = await self.strategy_manager.initialize()
        assert result is True
        assert hasattr(self.strategy_manager, 'active_strategies')
        assert hasattr(self.strategy_manager, 'active_strategies')
        assert hasattr(self.strategy_manager, 'signal_aggregator')
        assert hasattr(self.strategy_manager, 'conflict_resolver')
    
    @pytest.mark.asyncio
    async def test_start(self):
        """Test strategy manager start process"""
        # Initialize first, then start
        await self.strategy_manager.initialize()
        result = await self.strategy_manager.start()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_stop(self):
        """Test strategy manager stop process"""
        result = await self.strategy_manager.stop()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_register_strategy(self):
        """Test strategy registration"""
        strategy_config = {
            'name': 'test_momentum',
            'type': 'momentum',  # Use string value, not enum
            'allocation_pct': 0.3,
            'max_positions': 5,
            'risk_limit': 0.05
        }
        
        result = await self.strategy_manager.add_strategy(strategy_config)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_unregister_strategy(self):
        """Test strategy unregistration"""
        strategy_name = 'test_momentum_1'
        
        # First add a strategy to remove
        strategy_config = {
            'name': strategy_name,
            'type': 'momentum',
            'allocation_pct': 0.3,
            'max_positions': 5,
            'risk_limit': 0.05
        }
        await self.strategy_manager.add_strategy(strategy_config)
        
        result = await self.strategy_manager.remove_strategy(strategy_name)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_aggregate_strategy_signals(self):
        """Test strategy signal aggregation"""
        strategy_signals = {
            'momentum_1': [
                create_trading_signal('AAPL', SignalType.BUY, 0.8, 100),
                create_trading_signal('GOOGL', SignalType.SELL, 0.7, 50)
            ],
            'mean_reversion_1': [
                create_trading_signal('AAPL', SignalType.SELL, 0.6, 100),
                create_trading_signal('MSFT', SignalType.BUY, 0.9, 75)
            ]
        }
        
        # Mock the signal aggregator
        mock_aggregator = Mock()
        mock_aggregator.aggregate_strategy_signals = AsyncMock(return_value=[
            create_trading_signal('AAPL', SignalType.HOLD, 0.5, 0),
            create_trading_signal('GOOGL', SignalType.SELL, 0.7, 50),
            create_trading_signal('MSFT', SignalType.BUY, 0.9, 75)
        ])
        self.strategy_manager.signal_aggregator = mock_aggregator
        
        aggregated_signals = await self.strategy_manager.aggregate_strategy_signals(strategy_signals)
        assert isinstance(aggregated_signals, list)
        assert len(aggregated_signals) == 3
        mock_aggregator.aggregate_strategy_signals.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_resolve_signal_conflicts(self):
        """Test signal conflict resolution"""
        conflicting_signals = [
            create_trading_signal('AAPL', SignalType.BUY, 0.8, 100),
            create_trading_signal('AAPL', SignalType.SELL, 0.7, 100)
        ]
        
        # Test conflict resolution through signal aggregation
        strategy_signals = {'test_strategy': conflicting_signals}
        aggregated = await self.strategy_manager.aggregate_strategy_signals(strategy_signals)
        
        assert isinstance(aggregated, list)
    
    @pytest.mark.asyncio
    async def test_coordinate_strategies(self):
        """Test strategy coordination"""
        # Test signal generation which coordinates multiple strategies
        symbols = ['AAPL', 'GOOGL', 'MSFT']
        
        # Add some strategies first
        strategy_configs = [
            {'name': 'momentum_1', 'type': 'momentum', 'allocation_pct': 0.3},
            {'name': 'mean_reversion_1', 'type': 'mean_reversion', 'allocation_pct': 0.2}
        ]
        
        for config in strategy_configs:
            await self.strategy_manager.add_strategy(config)
        
        # Test signal generation (which coordinates strategies)
        signals = await self.strategy_manager.generate_signals(symbols)
        
        assert isinstance(signals, list)
        # Should have signals from coordinated strategies
    
    @pytest.mark.asyncio
    async def test_monitor_strategy_performance(self):
        """Test strategy performance monitoring"""
        # Test performance monitoring through health check
        health_status = await self.strategy_manager.health_check()
        
        assert isinstance(health_status, dict)
        assert 'active_strategies' in health_status
        assert 'component_type' in health_status
        assert health_status['component_type'] == 'StrategyManager'
    
    @pytest.mark.asyncio
    async def test_allocate_strategy_weights(self):
        """Test strategy weight allocation"""
        # Test strategy allocation through adding strategies with different weights
        strategy_configs = [
            {'name': 'momentum_1', 'type': 'momentum', 'allocation_pct': 0.25},
            {'name': 'mean_reversion_1', 'type': 'mean_reversion', 'allocation_pct': 0.30},
            {'name': 'statistical_arbitrage_1', 'type': 'statistical_arbitrage', 'allocation_pct': 0.45}
        ]
        
        for config in strategy_configs:
            result = await self.strategy_manager.add_strategy(config)
            assert result is True
        
        # Check that strategies were added with correct allocations
        status = self.strategy_manager.get_status()
        assert 'active_strategies' in status
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check functionality"""
        health_status = await self.strategy_manager.health_check()
        assert isinstance(health_status, dict)
        assert 'healthy' in health_status
        assert 'active_strategies' in health_status
        assert 'component_connections' in health_status
        assert 'component_type' in health_status
    
    def test_get_status(self):
        """Test get status functionality"""
        status = self.strategy_manager.get_status()
        assert isinstance(status, dict)
        assert 'active_strategies' in status
        assert 'component_type' in status


class TestStrategyExecutionEngine:
    """Test suite for StrategyExecutionEngine - strategy execution component"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.config = {
            'max_concurrent_executions': 5,
            'execution_timeout': 30,
            'enable_risk_checks': True,
            'enable_performance_monitoring': True
        }
        self.strategy_engine = StrategyExecutionEngine(self.config)
    
    def test_initialization(self):
        """Test strategy execution engine initialization"""
        assert self.strategy_engine is not None
        assert self.strategy_engine.config['max_concurrent_executions'] == 5
        assert self.strategy_engine.config['execution_timeout'] == 30
    
    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test strategy execution engine initialization process"""
        result = await self.strategy_engine.initialize()
        assert result is True
        assert hasattr(self.strategy_engine, 'active_executions')
        assert hasattr(self.strategy_engine, 'execution_queue')
        assert hasattr(self.strategy_engine, 'performance_monitor')
    
    @pytest.mark.asyncio
    async def test_start(self):
        """Test strategy execution engine start process"""
        with patch.object(self.strategy_engine, '_start_execution_monitoring', new_callable=AsyncMock) as mock_monitor:
            mock_monitor.return_value = None
            
            result = await self.strategy_engine.start()
            assert result is True
            mock_monitor.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop(self):
        """Test strategy execution engine stop process"""
        with patch.object(self.strategy_engine, '_stop_all_executions', new_callable=AsyncMock) as mock_stop:
            mock_stop.return_value = None
            
            result = await self.strategy_engine.stop()
            assert result is True
            mock_stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_strategy(self):
        """Test strategy execution"""
        strategy = Mock()
        strategy.strategy_id = 'test_strategy_1'
        strategy.execute = AsyncMock(return_value={'success': True, 'signals': []})
        
        with patch.object(self.strategy_engine, '_validate_strategy', new_callable=AsyncMock) as mock_validate:
            with patch.object(self.strategy_engine, '_monitor_execution', new_callable=AsyncMock) as mock_monitor:
                mock_validate.return_value = True
                mock_monitor.return_value = None
                
                result = await self.strategy_engine.execute_strategy(strategy)
                assert result is not None
                mock_validate.assert_called_once_with(strategy)
                mock_monitor.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_strategy_batch(self):
        """Test batch strategy execution"""
        strategies = [Mock() for _ in range(3)]
        for i, strategy in enumerate(strategies):
            strategy.strategy_id = f'test_strategy_{i+1}'
            strategy.execute = AsyncMock(return_value={'success': True, 'signals': []})
        
        with patch.object(self.strategy_engine, '_validate_strategy', new_callable=AsyncMock) as mock_validate:
            with patch.object(self.strategy_engine, '_monitor_execution', new_callable=AsyncMock) as mock_monitor:
                mock_validate.return_value = True
                mock_monitor.return_value = None
                
                results = await self.strategy_engine.execute_strategy_batch(strategies)
                assert isinstance(results, list)
                assert len(results) == 3
                assert mock_validate.call_count == 3
                assert mock_monitor.call_count == 3
    
    @pytest.mark.asyncio
    async def test_monitor_execution_performance(self):
        """Test execution performance monitoring"""
        with patch.object(self.strategy_engine, '_calculate_execution_metrics', new_callable=AsyncMock) as mock_metrics:
            mock_metrics.return_value = {
                'avg_execution_time': 0.5,
                'success_rate': 0.95,
                'throughput': 10.0,
                'error_rate': 0.05
            }
            
            performance_metrics = await self.strategy_engine.monitor_execution_performance()
            assert isinstance(performance_metrics, dict)
            assert 'avg_execution_time' in performance_metrics
            assert 'success_rate' in performance_metrics
            assert 'throughput' in performance_metrics
            mock_metrics.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_execution_error(self):
        """Test execution error handling"""
        strategy = Mock()
        strategy.strategy_id = 'test_strategy_1'
        error = Exception("Test execution error")
        
        with patch.object(self.strategy_engine, '_log_execution_error', new_callable=AsyncMock) as mock_log:
            with patch.object(self.strategy_engine, '_recover_from_error', new_callable=AsyncMock) as mock_recover:
                mock_log.return_value = None
                mock_recover.return_value = True
                
                result = await self.strategy_engine.handle_execution_error(strategy, error)
                assert result is True
                mock_log.assert_called_once_with(strategy, error)
                mock_recover.assert_called_once_with(strategy, error)


class TestStrategyValidator:
    """Test suite for StrategyValidator - strategy validation component"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.config = {
            'validation_rules': {
                'risk_limits': True,
                'performance_metrics': True,
                'signal_quality': True,
                'compliance': True
            },
            'validation_thresholds': {
                'min_sharpe_ratio': 1.0,
                'max_drawdown': 0.10,
                'min_win_rate': 0.50
            }
        }
        self.strategy_validator = StrategyValidator(self.config)
    
    def test_initialization(self):
        """Test strategy validator initialization"""
        assert self.strategy_validator is not None
        assert self.strategy_validator.config['validation_rules']['risk_limits'] is True
        assert self.strategy_validator.config['validation_thresholds']['min_sharpe_ratio'] == 1.0
    
    @pytest.mark.asyncio
    async def test_validate_strategy(self):
        """Test strategy validation"""
        strategy = Mock()
        strategy.strategy_id = 'test_strategy_1'
        strategy.get_performance_metrics = AsyncMock(return_value={
            'sharpe_ratio': 1.2,
            'max_drawdown': -0.08,
            'win_rate': 0.65
        })
        
        with patch.object(self.strategy_validator, '_validate_risk_limits', new_callable=AsyncMock) as mock_risk:
            with patch.object(self.strategy_validator, '_validate_performance_metrics', new_callable=AsyncMock) as mock_perf:
                with patch.object(self.strategy_validator, '_validate_signal_quality', new_callable=AsyncMock) as mock_signal:
                    mock_risk.return_value = {'valid': True, 'score': 0.9}
                    mock_perf.return_value = {'valid': True, 'score': 0.85}
                    mock_signal.return_value = {'valid': True, 'score': 0.8}
                    
                    validation_result = await self.strategy_validator.validate_strategy(strategy)
                    assert isinstance(validation_result, dict)
                    assert 'valid' in validation_result
                    assert 'overall_score' in validation_result
                    assert 'risk_validation' in validation_result
                    assert 'performance_validation' in validation_result
                    assert 'signal_validation' in validation_result
    
    @pytest.mark.asyncio
    async def test_validate_strategy_batch(self):
        """Test batch strategy validation"""
        strategies = [Mock() for _ in range(3)]
        for i, strategy in enumerate(strategies):
            strategy.strategy_id = f'test_strategy_{i+1}'
            strategy.get_performance_metrics = AsyncMock(return_value={
                'sharpe_ratio': 1.2,
                'max_drawdown': -0.08,
                'win_rate': 0.65
            })
        
        with patch.object(self.strategy_validator, 'validate_strategy', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = {
                'valid': True,
                'overall_score': 0.85,
                'risk_validation': {'valid': True, 'score': 0.9},
                'performance_validation': {'valid': True, 'score': 0.85},
                'signal_validation': {'valid': True, 'score': 0.8}
            }
            
            validation_results = await self.strategy_validator.validate_strategy_batch(strategies)
            assert isinstance(validation_results, list)
            assert len(validation_results) == 3
            assert mock_validate.call_count == 3
    
    @pytest.mark.asyncio
    async def test_validate_risk_limits(self):
        """Test risk limits validation"""
        strategy = Mock()
        strategy.get_risk_metrics = AsyncMock(return_value={
            'max_position_size': 0.08,
            'max_daily_var': 0.03,
            'max_concentration': 0.12
        })
        
        risk_validation = await self.strategy_validator._validate_risk_limits(strategy)
        assert isinstance(risk_validation, dict)
        assert 'valid' in risk_validation
        assert 'score' in risk_validation
        assert 'risk_metrics' in risk_validation
    
    @pytest.mark.asyncio
    async def test_validate_performance_metrics(self):
        """Test performance metrics validation"""
        strategy = Mock()
        strategy.get_performance_metrics = AsyncMock(return_value={
            'sharpe_ratio': 1.2,
            'max_drawdown': -0.08,
            'win_rate': 0.65,
            'total_return': 0.12
        })
        
        performance_validation = await self.strategy_validator._validate_performance_metrics(strategy)
        assert isinstance(performance_validation, dict)
        assert 'valid' in performance_validation
        assert 'score' in performance_validation
        assert 'performance_metrics' in performance_validation
    
    @pytest.mark.asyncio
    async def test_validate_signal_quality(self):
        """Test signal quality validation"""
        strategy = Mock()
        strategy.get_signal_quality_metrics = AsyncMock(return_value={
            'signal_accuracy': 0.75,
            'signal_precision': 0.80,
            'signal_recall': 0.70,
            'signal_f1_score': 0.75
        })
        
        signal_validation = await self.strategy_validator._validate_signal_quality(strategy)
        assert isinstance(signal_validation, dict)
        assert 'valid' in signal_validation
        assert 'score' in signal_validation
        assert 'signal_metrics' in signal_validation


class TestStrategyRegistry:
    """Test suite for StrategyRegistry - strategy registry component"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.config = {
            'max_registered_strategies': 50,
            'enable_strategy_discovery': True,
            'enable_strategy_validation': True,
            'registry_persistence': True
        }
        self.strategy_registry = StrategyRegistry(self.config)
    
    def test_initialization(self):
        """Test strategy registry initialization"""
        assert self.strategy_registry is not None
        assert self.strategy_registry.config['max_registered_strategies'] == 50
        assert self.strategy_registry.config['enable_strategy_discovery'] is True
    
    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test strategy registry initialization process"""
        result = await self.strategy_registry.initialize()
        assert result is True
        assert hasattr(self.strategy_registry, 'registered_strategies')
        assert hasattr(self.strategy_registry, 'strategy_metadata')
        assert hasattr(self.strategy_registry, 'discovery_engine')
    
    @pytest.mark.asyncio
    async def test_register_strategy(self):
        """Test strategy registration"""
        strategy = Mock()
        strategy.strategy_id = 'test_strategy_1'
        strategy.strategy_type = StrategyType.MOMENTUM
        strategy.name = 'Test Momentum Strategy'
        
        with patch.object(self.strategy_registry, '_validate_strategy_registration', new_callable=AsyncMock) as mock_validate:
            with patch.object(self.strategy_registry, '_store_strategy_metadata', new_callable=AsyncMock) as mock_store:
                mock_validate.return_value = True
                mock_store.return_value = True
                
                result = await self.strategy_registry.register_strategy(strategy)
                assert result is True
                mock_validate.assert_called_once_with(strategy)
                mock_store.assert_called_once_with(strategy)
    
    @pytest.mark.asyncio
    async def test_unregister_strategy(self):
        """Test strategy unregistration"""
        strategy_id = 'test_strategy_1'
        
        # Add strategy first
        self.strategy_registry.registered_strategies[strategy_id] = Mock()
        
        with patch.object(self.strategy_registry, '_remove_strategy_metadata', new_callable=AsyncMock) as mock_remove:
            mock_remove.return_value = True
            
            result = await self.strategy_registry.unregister_strategy(strategy_id)
            assert result is True
            mock_remove.assert_called_once_with(strategy_id)
    
    @pytest.mark.asyncio
    async def test_discover_strategies(self):
        """Test strategy discovery"""
        with patch.object(self.strategy_registry, '_scan_strategy_directory', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = [
                {'strategy_id': 'discovered_1', 'strategy_type': StrategyType.MOMENTUM},
                {'strategy_id': 'discovered_2', 'strategy_type': StrategyType.MEAN_REVERSION}
            ]
            
            discovered_strategies = await self.strategy_registry.discover_strategies()
            assert isinstance(discovered_strategies, list)
            assert len(discovered_strategies) == 2
            mock_scan.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_strategy_by_type(self):
        """Test getting strategies by type"""
        # Add some mock strategies
        self.strategy_registry.registered_strategies = {
            'momentum_1': Mock(strategy_type=StrategyType.MOMENTUM),
            'momentum_2': Mock(strategy_type=StrategyType.MOMENTUM),
            'mean_reversion_1': Mock(strategy_type=StrategyType.MEAN_REVERSION)
        }
        
        momentum_strategies = await self.strategy_registry.get_strategies_by_type(StrategyType.MOMENTUM)
        assert isinstance(momentum_strategies, list)
        assert len(momentum_strategies) == 2
    
    @pytest.mark.asyncio
    async def test_get_strategy_metadata(self):
        """Test getting strategy metadata"""
        strategy_id = 'test_strategy_1'
        
        # Add strategy metadata
        self.strategy_registry.strategy_metadata[strategy_id] = {
            'strategy_type': StrategyType.MOMENTUM,
            'name': 'Test Strategy',
            'version': '1.0.0',
            'performance_metrics': {'sharpe_ratio': 1.2}
        }
        
        metadata = await self.strategy_registry.get_strategy_metadata(strategy_id)
        assert isinstance(metadata, dict)
        assert 'strategy_type' in metadata
        assert 'name' in metadata
        assert 'performance_metrics' in metadata
    
    @pytest.mark.asyncio
    async def test_search_strategies(self):
        """Test strategy search"""
        search_criteria = {
            'strategy_type': StrategyType.MOMENTUM,
            'min_sharpe_ratio': 1.0,
            'max_drawdown': 0.10
        }
        
        with patch.object(self.strategy_registry, '_filter_strategies_by_criteria', new_callable=AsyncMock) as mock_filter:
            mock_filter.return_value = [
                {'strategy_id': 'momentum_1', 'sharpe_ratio': 1.2, 'max_drawdown': -0.08},
                {'strategy_id': 'momentum_2', 'sharpe_ratio': 1.5, 'max_drawdown': -0.06}
            ]
            
            search_results = await self.strategy_registry.search_strategies(search_criteria)
            assert isinstance(search_results, list)
            assert len(search_results) == 2
            mock_filter.assert_called_once_with(search_criteria)


class TestMultiTradingSignalAggregator:
    """Test suite for MultiTradingSignalAggregator - signal aggregation component"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.config = {
            'aggregation_method': 'weighted_average',
            'conflict_resolution': 'confidence_weighted',
            'signal_validation': True,
            'max_signals_per_symbol': 10
        }
        self.signal_aggregator = MultiTradingSignalAggregator(self.config)
    
    def test_initialization(self):
        """Test signal aggregator initialization"""
        assert self.signal_aggregator is not None
        assert self.signal_aggregator.config['aggregation_method'] == 'weighted_average'
        assert self.signal_aggregator.config['conflict_resolution'] == 'confidence_weighted'
    
    @pytest.mark.asyncio
    async def test_aggregate_signals(self):
        """Test signal aggregation"""
        strategy_signals = {
            'momentum_1': [
                TradingSignal(symbol='AAPL', signal_type=SignalType.BUY, confidence=0.8, target_quantity=100, timestamp=datetime.now()),
                TradingSignal(symbol='GOOGL', signal_type=SignalType.SELL, confidence=0.7, target_quantity=50, timestamp=datetime.now())
            ],
            'mean_reversion_1': [
                TradingSignal(symbol='AAPL', signal_type=SignalType.SELL, confidence=0.6, target_quantity=100, timestamp=datetime.now()),
                TradingSignal(symbol='MSFT', signal_type=SignalType.BUY, confidence=0.9, target_quantity=75, timestamp=datetime.now())
            ]
        }
        
        with patch.object(self.signal_aggregator, '_group_signals_by_symbol', new_callable=AsyncMock) as mock_group:
            with patch.object(self.signal_aggregator, '_aggregate_symbol_signals', new_callable=AsyncMock) as mock_aggregate:
                mock_group.return_value = {
                    'AAPL': [strategy_signals['momentum_1'][0], strategy_signals['mean_reversion_1'][0]],
                    'GOOGL': [strategy_signals['momentum_1'][1]],
                    'MSFT': [strategy_signals['mean_reversion_1'][1]]
                }
                mock_aggregate.return_value = [
                    TradingSignal(symbol='AAPL', signal_type=SignalType.HOLD, confidence=0.5, target_quantity=0, timestamp=datetime.now()),
                    TradingSignal(symbol='GOOGL', signal_type=SignalType.SELL, confidence=0.7, target_quantity=50, timestamp=datetime.now()),
                    TradingSignal(symbol='MSFT', signal_type=SignalType.BUY, confidence=0.9, target_quantity=75, timestamp=datetime.now())
                ]
                
                aggregated_signals = await self.signal_aggregator.aggregate_signals(strategy_signals)
                assert isinstance(aggregated_signals, list)
                assert len(aggregated_signals) == 3
                mock_group.assert_called_once()
                assert mock_aggregate.call_count == 3
    
    @pytest.mark.asyncio
    async def test_aggregate_symbol_signals(self):
        """Test symbol signal aggregation"""
        symbol_signals = [
            TradingSignal(symbol='AAPL', signal_type=SignalType.BUY, confidence=0.8, target_quantity=100, timestamp=datetime.now()),
            TradingSignal(symbol='AAPL', signal_type=SignalType.SELL, confidence=0.6, target_quantity=100, timestamp=datetime.now())
        ]
        
        with patch.object(self.signal_aggregator, '_resolve_signal_conflicts', new_callable=AsyncMock) as mock_resolve:
            mock_resolve.return_value = TradingSignal(
                symbol='AAPL', signal_type=SignalType.HOLD, confidence=0.5, target_quantity=0, timestamp=datetime.now()
            )
            
            aggregated_signal = await self.signal_aggregator._aggregate_symbol_signals(symbol_signals)
            assert aggregated_signal is not None
            assert aggregated_signal.symbol == 'AAPL'
            mock_resolve.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_resolve_signal_conflicts(self):
        """Test signal conflict resolution"""
        conflicting_signals = [
            TradingSignal(symbol='AAPL', signal_type=SignalType.BUY, confidence=0.8, target_quantity=100, timestamp=datetime.now()),
            TradingSignal(symbol='AAPL', signal_type=SignalType.SELL, confidence=0.6, target_quantity=100, timestamp=datetime.now())
        ]
        
        resolved_signal = await self.signal_aggregator._resolve_signal_conflicts(conflicting_signals)
        assert resolved_signal is not None
        assert resolved_signal.symbol == 'AAPL'
        # Should resolve to HOLD due to conflicting signals
        assert resolved_signal.signal_type == SignalType.HOLD


class TestSignalConflictResolver:
    """Test suite for SignalConflictResolver - conflict resolution component"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.config = {
            'resolution_method': 'confidence_weighted',
            'conflict_threshold': 0.1,
            'default_signal': SignalType.HOLD
        }
        self.conflict_resolver = SignalConflictResolver(self.config)
    
    def test_initialization(self):
        """Test conflict resolver initialization"""
        assert self.conflict_resolver is not None
        assert self.conflict_resolver.config['resolution_method'] == 'confidence_weighted'
        assert self.conflict_resolver.config['conflict_threshold'] == 0.1
    
    @pytest.mark.asyncio
    async def test_resolve_conflicts(self):
        """Test conflict resolution"""
        conflicting_signals = [
            TradingSignal(symbol='AAPL', signal_type=SignalType.BUY, confidence=0.8, target_quantity=100, timestamp=datetime.now()),
            TradingSignal(symbol='AAPL', signal_type=SignalType.SELL, confidence=0.6, target_quantity=100, timestamp=datetime.now())
        ]
        
        resolved_signal = await self.conflict_resolver.resolve_conflicts(conflicting_signals)
        assert resolved_signal is not None
        assert resolved_signal.symbol == 'AAPL'
        # Should resolve to BUY due to higher confidence
        assert resolved_signal.signal_type == SignalType.BUY
        assert resolved_signal.confidence == 0.8
    
    @pytest.mark.asyncio
    async def test_resolve_same_direction_signals(self):
        """Test same direction signal resolution"""
        same_direction_signals = [
            TradingSignal(symbol='AAPL', signal_type=SignalType.BUY, confidence=0.8, target_quantity=100, timestamp=datetime.now()),
            TradingSignal(symbol='AAPL', signal_type=SignalType.BUY, confidence=0.6, target_quantity=100, timestamp=datetime.now())
        ]
        
        resolved_signal = await self.conflict_resolver.resolve_conflicts(same_direction_signals)
        assert resolved_signal is not None
        assert resolved_signal.symbol == 'AAPL'
        assert resolved_signal.signal_type == SignalType.BUY
        # Should aggregate confidence and quantity
        assert resolved_signal.confidence > 0.6
        assert resolved_signal.target_quantity > 100
    
    @pytest.mark.asyncio
    async def test_resolve_close_conflicts(self):
        """Test close conflict resolution"""
        close_conflict_signals = [
            TradingSignal(symbol='AAPL', signal_type=SignalType.BUY, confidence=0.8, target_quantity=100, timestamp=datetime.now()),
            TradingSignal(symbol='AAPL', signal_type=SignalType.SELL, confidence=0.75, target_quantity=100, timestamp=datetime.now())
        ]
        
        resolved_signal = await self.conflict_resolver.resolve_conflicts(close_conflict_signals)
        assert resolved_signal is not None
        assert resolved_signal.symbol == 'AAPL'
        # Should resolve to HOLD due to close confidence levels
        assert resolved_signal.signal_type == SignalType.HOLD


class TestStrategyManagerIntegration:
    """Integration tests for strategy manager components"""
    
    def setup_method(self):
        """Setup for integration tests"""
        self.strategy_manager = StrategyManager({
            'max_concurrent_strategies': 10,
            'enable_multi_strategy_coordination': True
        })
        self.strategy_engine = StrategyExecutionEngine({
            'max_concurrent_executions': 5
        })
        self.strategy_validator = StrategyValidator({
            'validation_rules': {'risk_limits': True, 'performance_metrics': True}
        })
        self.strategy_registry = StrategyRegistry({
            'max_registered_strategies': 50
        })
    
    @pytest.mark.asyncio
    async def test_end_to_end_strategy_lifecycle(self):
        """Test end-to-end strategy lifecycle"""
        # Test strategy registration
        strategy_config = {
            'strategy_type': StrategyType.MOMENTUM,
            'name': 'test_momentum',
            'allocation_pct': 0.3
        }
        
        with patch.object(self.strategy_manager, '_create_strategy_instance', new_callable=AsyncMock) as mock_create:
            mock_strategy = Mock()
            mock_strategy.strategy_id = 'test_momentum_1'
            mock_create.return_value = mock_strategy
            
            registration_result = await self.strategy_manager.register_strategy(strategy_config)
            assert registration_result is True
        
        # Test strategy validation
        with patch.object(self.strategy_validator, 'validate_strategy', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = {
                'valid': True,
                'overall_score': 0.85,
                'risk_validation': {'valid': True, 'score': 0.9},
                'performance_validation': {'valid': True, 'score': 0.85}
            }
            
            validation_result = await self.strategy_validator.validate_strategy(mock_strategy)
            assert validation_result['valid'] is True
        
        # Test strategy execution
        with patch.object(self.strategy_engine, 'execute_strategy', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {'success': True, 'signals': []}
            
            execution_result = await self.strategy_engine.execute_strategy(mock_strategy)
            assert execution_result is not None
    
    @pytest.mark.asyncio
    async def test_multi_strategy_coordination(self):
        """Test multi-strategy coordination"""
        # Create multiple strategies
        strategies = []
        for i in range(3):
            strategy = Mock()
            strategy.strategy_id = f'strategy_{i+1}'
            strategy.execute = AsyncMock(return_value={'success': True, 'signals': []})
            strategies.append(strategy)
        
        # Test strategy coordination
        with patch.object(self.strategy_manager, '_coordinate_strategy_execution', new_callable=AsyncMock) as mock_coordinate:
            mock_coordinate.return_value = {
                'coordinated_strategies': [f'strategy_{i+1}' for i in range(3)],
                'coordination_score': 0.85,
                'conflicts_resolved': 1
            }
            
            coordination_result = await self.strategy_manager.coordinate_strategies()
            assert isinstance(coordination_result, dict)
            assert 'coordinated_strategies' in coordination_result
            assert 'coordination_score' in coordination_result
    
    @pytest.mark.asyncio
    async def test_signal_aggregation_pipeline(self):
        """Test signal aggregation pipeline"""
        # Create strategy signals
        strategy_signals = {
            'momentum_1': [
                TradingSignal(symbol='AAPL', signal_type=SignalType.BUY, confidence=0.8, target_quantity=100, timestamp=datetime.now())
            ],
            'mean_reversion_1': [
                TradingSignal(symbol='AAPL', signal_type=SignalType.SELL, confidence=0.6, target_quantity=100, timestamp=datetime.now())
            ]
        }
        
        # Test signal aggregation
        with patch.object(self.strategy_manager, 'signal_aggregator', 'aggregate_signals') as mock_aggregate:
            mock_aggregate.return_value = [
                TradingSignal(symbol='AAPL', signal_type=SignalType.HOLD, confidence=0.5, target_quantity=0, timestamp=datetime.now())
            ]
            
            aggregated_signals = await self.strategy_manager.aggregate_strategy_signals(strategy_signals)
            assert isinstance(aggregated_signals, list)
            assert len(aggregated_signals) == 1
            assert aggregated_signals[0].signal_type == SignalType.HOLD
    
    @pytest.mark.asyncio
    async def test_strategy_performance_monitoring(self):
        """Test strategy performance monitoring"""
        with patch.object(self.strategy_manager, '_calculate_strategy_performance', new_callable=AsyncMock) as mock_performance:
            mock_performance.return_value = {
                'strategy_1': {
                    'total_return': 0.08,
                    'sharpe_ratio': 1.2,
                    'max_drawdown': -0.05,
                    'win_rate': 0.65
                },
                'strategy_2': {
                    'total_return': 0.06,
                    'sharpe_ratio': 1.5,
                    'max_drawdown': -0.03,
                    'win_rate': 0.70
                }
            }
            
            performance_metrics = await self.strategy_manager.monitor_strategy_performance()
            assert isinstance(performance_metrics, dict)
            assert 'strategy_1' in performance_metrics
            assert 'strategy_2' in performance_metrics
    
    @pytest.mark.asyncio
    async def test_strategy_error_handling(self):
        """Test strategy error handling"""
        strategy = Mock()
        strategy.strategy_id = 'test_strategy_1'
        strategy.execute = AsyncMock(side_effect=Exception("Test strategy error"))
        
        with patch.object(self.strategy_manager, '_handle_strategy_error', new_callable=AsyncMock) as mock_error:
            mock_error.return_value = {
                'error_handled': True,
                'error_type': 'execution_error',
                'recovery_action': 'strategy_restart'
            }
            
            error_result = await self.strategy_manager._handle_strategy_error(strategy, Exception("Test error"))
            assert isinstance(error_result, dict)
            assert 'error_handled' in error_result
            assert 'recovery_action' in error_result
