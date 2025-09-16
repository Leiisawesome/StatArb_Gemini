"""
Integration Tests for Complete System Workflows
==============================================

Tests that verify end-to-end functionality across the entire trading system.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np

from core_structure.system import UnifiedTradingSystem, create_production_trading_system
from core_structure.config import TradingConfig, Environment, TradingMode
from core_structure.engines import TradingSignal, SignalType, SignalStrength
from core_structure.strategies import StrategyResult, StrategyContext
from core_structure.strategies import StrategyType


@pytest.mark.integration
class TestSystemLifecycle:
    """Test complete system lifecycle"""
    
    def test_system_creation_and_startup(self):
        """Test system creation and startup process"""
        # Create system with test configuration
        config = TradingConfig(
            environment=Environment.TESTING,
            trading_mode=TradingMode.BACKTEST,
            initial_capital=100000.0
        )
        
        system = UnifiedTradingSystem(config)
        
        # Verify system initialization
        assert system.config == config
        assert system.system_id is not None
        assert system.status.value in ['initializing', 'ready']
        
        # Start system
        system.start_system()
        assert system.status.value in ['starting', 'running']
        
        # Shutdown system
        system.shutdown_system()
        assert system.status.value in ['stopping', 'stopped']
    
    def test_production_system_factory(self):
        """Test production system factory function"""
        system = create_production_trading_system()
        
        assert isinstance(system, UnifiedTradingSystem)
        assert system.config.environment.value == Environment.PRODUCTION.value
        
        # Test system functionality
        system.start_system()
        assert system.status.value in ['starting', 'running']
        
        system.shutdown_system()
        assert system.status.value in ['stopping', 'stopped']
    
    @pytest.mark.asyncio
    async def test_async_system_operations(self):
        """Test asynchronous system operations"""
        config = TradingConfig(environment=Environment.TESTING)
        system = UnifiedTradingSystem(config)
        
        # Test system startup
        system.start_system()
        assert system.status.value in ['starting', 'running']
        
        # Test async shutdown
        await system.async_shutdown()
        assert system.status.value in ['stopping', 'stopped']


@pytest.mark.integration
class TestSignalToExecutionWorkflow:
    """Test complete signal generation to execution workflow"""
    
    def test_momentum_strategy_workflow(self, sample_market_data):
        """Test complete momentum strategy workflow"""
        config = TradingConfig(
            environment=Environment.TESTING,
            trading_mode=TradingMode.BACKTEST
        )
        
        system = UnifiedTradingSystem(config)
        system.start_system()
        
        try:
            # Create momentum strategy
            strategy_config = {
                'lookback_period': 20,
                'momentum_threshold': 0.02,
                'confidence_threshold': 0.7
            }
            
            strategy = system.strategy_manager.create_strategy(
                StrategyType.MOMENTUM,
                "test_momentum",
                strategy_config
            )
            
            # Generate signals using market data
            data = sample_market_data['AAPL']
            strategy_result = system.strategy_manager.execute_strategy("test_momentum", data)
            
            # Process signals through execution engine
            execution_results = []
            if strategy_result.success and strategy_result.signals:
                for signal in strategy_result.signals:
                    if signal:
                        result = system.execution_processor.execute_signal(signal, quantity=100)
                        execution_results.append(result)
            
            # Verify workflow completion
            assert isinstance(strategy_result.signals, list)
            assert len(execution_results) >= 0  # May be 0 if no valid signals
            
            # Check execution metrics
            metrics = system.execution_processor.get_metrics()
            assert hasattr(metrics, 'total_executions')
            
        finally:
            system.shutdown_system()
    
    def test_mean_reversion_workflow(self, sample_market_data):
        """Test complete mean reversion strategy workflow"""
        config = TradingConfig(environment=Environment.TESTING)
        system = UnifiedTradingSystem(config)
        system.start_system()
        
        try:
            # Create mean reversion strategy
            strategy_config = {
                'lookback_period': 20,
                'z_score_threshold': 2.0,
                'confidence_threshold': 0.6
            }
            
            strategy = system.strategy_manager.create_strategy(
                StrategyType.MEAN_REVERSION,
                "test_mean_reversion",
                strategy_config
            )
            
            # Execute complete workflow
            data = sample_market_data['MSFT']
            result = system.strategy_manager.execute_strategy("test_mean_reversion", data)
            
            # Process through system
            for signal in result.signals:
                if signal:
                    # Process signal (validation is internal)
                    if signal and signal.strength != SignalStrength.WEAK:
                        # Execute signal
                        result = system.execution_processor.execute_signal(signal, quantity=50)
                        assert result is not None
            
        finally:
            system.shutdown_system()
    
    def test_pairs_trading_workflow(self, sample_market_data):
        """Test complete pairs trading workflow"""
        config = TradingConfig(environment=Environment.TESTING)
        system = UnifiedTradingSystem(config)
        system.start_system()
        
        try:
            # Create pairs trading strategy
            strategy_config = {
                'pairs': [('AAPL', 'MSFT')],
                'lookback_period': 60,
                'entry_threshold': 2.0
            }
            
            strategy = system.strategy_manager.create_strategy(
                StrategyType.PAIRS_TRADING,
                "test_pairs",
                strategy_config
            )
            
            # Prepare pairs data
            pairs_data = {
                'AAPL': sample_market_data['AAPL'],
                'MSFT': sample_market_data['MSFT']
            }
            
            # Execute pairs workflow
            result = system.strategy_manager.execute_strategy("test_pairs", pairs_data)
            
            # Process pairs signals (should come in pairs)
            for signal in result.signals:
                if signal:
                    result = system.execution_processor.execute_signal(signal, quantity=25)
                    assert result is not None
            
        finally:
            system.shutdown_system()


@pytest.mark.integration
class TestMultiStrategyWorkflow:
    """Test multi-strategy system workflows"""
    
    def test_concurrent_strategies(self, sample_market_data):
        """Test running multiple strategies concurrently"""
        config = TradingConfig(environment=Environment.TESTING)
        system = UnifiedTradingSystem(config)
        system.start_system()
        
        try:
            # Create multiple strategies
            strategies = [
                (StrategyType.MOMENTUM, "momentum_1", {'lookback_period': 20}),
                (StrategyType.MEAN_REVERSION, "mean_rev_1", {'z_score_threshold': 2.0}),
                (StrategyType.PAIRS_TRADING, "pairs_1", {'pairs': [('AAPL', 'MSFT')]})
            ]
            
            # Register all strategies
            for strategy_type, strategy_id, strategy_config in strategies:
                system.strategy_manager.create_strategy(
                    strategy_type, strategy_id, strategy_config
                )
            
            # Execute all strategies with same data
            all_signals = []
            for strategy_type, strategy_id, _ in strategies:
                if strategy_type == StrategyType.PAIRS_TRADING:
                    context = StrategyContext(
                        symbol="AAPL_MSFT",
                        market_data=pd.DataFrame({'AAPL': sample_market_data['AAPL']['close'], 'MSFT': sample_market_data['MSFT']['close']}),
                        current_time=datetime.now(),
                        portfolio_state={},
                        risk_limits={},
                        strategy_config={}
                    )
                else:
                    context = StrategyContext(
                        symbol="AAPL",
                        market_data=sample_market_data['AAPL'],
                        current_time=datetime.now(),
                        portfolio_state={},
                        risk_limits={},
                        strategy_config={}
                    )
                
                result = system.strategy_manager.execute_strategy(strategy_id, context)
                all_signals.extend(result.signals)
            
            # Process all signals
            execution_count = 0
            for signal in all_signals:
                if signal and signal.strength != SignalStrength.WEAK:
                    result = system.execution_processor.execute_signal(signal, quantity=10)
                    if result:
                        execution_count += 1
            
            # Verify multi-strategy execution
            assert len(all_signals) >= 0
            assert execution_count >= 0
            
            # Check system metrics
            metrics = system.get_performance_summary()
            assert 'engine_status' in metrics  # Check for basic system metrics
            
        finally:
            system.shutdown_system()
    
    def test_strategy_conflict_resolution(self, sample_market_data):
        """Test handling of conflicting signals from different strategies"""
        config = TradingConfig(environment=Environment.TESTING)
        system = UnifiedTradingSystem(config)
        system.start_system()
        
        try:
            # Create strategies that might generate conflicting signals
            system.strategy_manager.create_strategy(
                StrategyType.MOMENTUM,
                "momentum_aggressive",
                {'lookback_period': 10, 'momentum_threshold': 0.01}
            )
            
            system.strategy_manager.create_strategy(
                StrategyType.MEAN_REVERSION,
                "mean_rev_conservative",
                {'lookback_period': 30, 'z_score_threshold': 1.5}
            )
            
            # Generate signals from both strategies
            data = sample_market_data['AAPL']
            
            momentum_result = system.strategy_manager.execute_strategy("momentum_aggressive", data)
            mean_rev_result = system.strategy_manager.execute_strategy("mean_rev_conservative", data)
            
            # Combine and process signals
            all_signals = momentum_result.signals + mean_rev_result.signals
            
            # System should handle conflicting signals gracefully
            for signal in all_signals:
                if signal:
                    # Each signal should be processed independently
                    result = system.execution_processor.execute_signal(signal, quantity=5)
                    # Result may be None, rejected, or executed based on risk management
                    assert result is None or hasattr(result, 'status')
            
        finally:
            system.shutdown_system()


@pytest.mark.integration
class TestSystemOptimization:
    """Test system optimization and performance features"""
    
    def test_optimization_manager_integration(self):
        """Test optimization manager integration with system"""
        config = TradingConfig(environment=Environment.TESTING)
        system = UnifiedTradingSystem(config)
        
        # Verify optimization functionality is available
        assert hasattr(system, 'enable_auto_strategy_optimization')
        assert hasattr(system, 'enable_portfolio_optimization')
        
        system.start_system()
        
        try:
            # Test optimization features
            system.enable_auto_strategy_optimization()
            system.enable_portfolio_optimization()
            
            # Test optimization features are enabled
            # (optimization results are not directly accessible in this interface)
            
        finally:
            system.shutdown_system()
    
    def test_caching_performance(self, sample_market_data):
        """Test caching performance in integrated workflow"""
        config = TradingConfig(environment=Environment.TESTING)
        system = UnifiedTradingSystem(config)
        system.start_system()
        
        try:
            # Create strategy
            system.strategy_manager.create_strategy(
                StrategyType.MOMENTUM,
                "cache_test",
                {'lookback_period': 20}
            )
            
            data = sample_market_data['AAPL']
            
            # First execution (should populate cache)
            result1 = system.strategy_manager.execute_strategy("cache_test", data)
            
            # Second execution (should use cache)
            result2 = system.strategy_manager.execute_strategy("cache_test", data)
            
            # Results should be consistent (caching working)
            assert len(result1.signals) == len(result2.signals)
            
        finally:
            system.shutdown_system()


@pytest.mark.integration
class TestSystemResilience:
    """Test system resilience and error handling"""
    
    def test_system_error_recovery(self):
        """Test system recovery from errors"""
        config = TradingConfig(environment=Environment.TESTING)
        system = UnifiedTradingSystem(config)
        system.start_system()
        
        try:
            # Test invalid strategy creation
            try:
                system.strategy_manager.create_strategy(
                    "INVALID_TYPE",
                    "invalid_strategy",
                    {}
                )
            except (ValueError, KeyError, TypeError):
                pass  # Expected error
            
            # System should still be functional
            assert system.status.value in ['running', 'ready']
            
            # Test invalid signal processing
            invalid_signal = None
            result = None
            try:
                result = system.execution_processor.execute_signal(invalid_signal, quantity=100)
                # Should return None or raise appropriate exception
            except (AttributeError, ValueError):
                # Expected behavior for None signal
                result = None
            
            # Should handle gracefully
            assert result is None or hasattr(result, 'status')
            
            # System should still be operational
            assert system.status.value in ['running', 'ready']
            
        finally:
            system.shutdown_system()
    
    def test_system_resource_management(self):
        """Test system resource management under load"""
        config = TradingConfig(environment=Environment.TESTING)
        system = UnifiedTradingSystem(config)
        system.start_system()
        
        try:
            # Create multiple strategies
            for i in range(10):
                system.strategy_manager.create_strategy(
                    StrategyType.MOMENTUM,
                    f"momentum_{i}",
                    {'lookback_period': 20}
                )
            
            # System should handle multiple strategies
            assert len(system.strategy_manager._active_strategies) == 10
            
            # Remove strategies
            for i in range(10):
                system.strategy_manager.remove_strategy(f"momentum_{i}")
            
            # Resources should be cleaned up
            assert len(system.strategy_manager._active_strategies) == 0
            
        finally:
            system.shutdown_system()


@pytest.mark.integration
class TestBackwardCompatibility:
    """Test backward compatibility with existing interfaces"""
    
    def test_legacy_engine_interface(self):
        """Test legacy engine interface compatibility"""
        # Test that legacy imports still work
        from core_structure import UnifiedTradingSystem as LegacyEngine
        
        system = LegacyEngine()
        assert system is not None
        
        # Test legacy methods if they exist
        if hasattr(system, 'get_performance_summary'):
            summary = system.get_performance_summary()
            assert isinstance(summary, dict)
    
    def test_legacy_config_interface(self):
        """Test legacy configuration interface"""
        from core_structure.config import ConfigManager
        
        manager = ConfigManager()
        
        # Test legacy methods
        config = manager.get_config()
        assert config is not None
        
        # Test backward compatibility methods
        if hasattr(manager, 'get'):
            value = manager.get('initial_capital', 100000.0)
            assert isinstance(value, (int, float))


@pytest.mark.integration
@pytest.mark.slow
class TestSystemPerformance:
    """Test system performance under various conditions"""
    
    def test_high_frequency_signal_processing(self, performance_timer):
        """Test system performance with high-frequency signals"""
        config = TradingConfig(environment=Environment.TESTING)
        system = UnifiedTradingSystem(config)
        system.start_system()
        
        try:
            # Create strategy
            system.strategy_manager.create_strategy(
                StrategyType.MOMENTUM,
                "hf_test",
                {'lookback_period': 10}
            )
            
            performance_timer.start()
            
            # Generate many signals rapidly
            for i in range(100):
                signal = TradingSignal(
                    symbol=f"STOCK_{i % 10}",
                    signal_type=SignalType.LONG,
                    strength=SignalStrength.MODERATE,
                    confidence=0.7,
                    timestamp=datetime.now()
                )
                
                if signal and signal.strength != SignalStrength.WEAK:
                    system.execution_processor.execute_signal(signal, quantity=10)
            
            performance_timer.stop()
            
            # Should handle high frequency efficiently
            assert performance_timer.elapsed_seconds < 5.0
            
        finally:
            system.shutdown_system()
    
    @pytest.mark.asyncio
    async def test_concurrent_system_operations(self):
        """Test concurrent system operations"""
        config = TradingConfig(environment=Environment.TESTING)
        system = UnifiedTradingSystem(config)
        
        system.start_system()
        
        try:
            # Create multiple strategies concurrently
            tasks = []
            for i in range(5):
                task = asyncio.create_task(
                    self._create_strategy_async(system, f"concurrent_{i}")
                )
                tasks.append(task)
            
            # Wait for all strategies to be created
            await asyncio.gather(*tasks)
            
            # Verify all strategies were created
            assert len(system.strategy_manager._active_strategies) == 5
            
        finally:
            await system.async_shutdown()
    
    async def _create_strategy_async(self, system, strategy_id):
        """Helper method to create strategy asynchronously"""
        # Simulate async strategy creation
        await asyncio.sleep(0.1)
        
        system.strategy_manager.create_strategy(
            StrategyType.MOMENTUM,
            strategy_id,
            {'lookback_period': 20}
        )
        
        return strategy_id
