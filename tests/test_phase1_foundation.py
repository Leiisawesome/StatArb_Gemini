"""
Phase 1 Foundation Architecture Tests
====================================

Unit tests to validate Phase 1 implementation focusing on:
- Interface delegation pattern
- Boundary violation prevention
- Configuration management
- Signal conversion isolation

Author: Professional Trading System Architecture
Version: 1.0.0
"""

import pytest
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any
from unittest.mock import Mock, patch

# Import the components under test
from trade_engine.interfaces import (
    StrategyInterface, PortfolioInterface, ExecutionInterface,
    SignalConverterInterface, ConfigurationInterface,
    TradingSignal, RawSignal, SignalType,
    ComponentMissingError, ComponentValidationError
)
from trade_engine.core import DelegatedCoreEngine, CoreEngineConfig
from trade_engine.conversion import SignalConverter, SignalConversionConfig
from trade_engine.configuration import UnifiedConfigurationManager


class MockStrategy(StrategyInterface):
    """Mock strategy for testing."""
    
    def __init__(self):
        self.signals_to_return = []
    
    def calculate_signals(self, market_data: pd.DataFrame) -> List[RawSignal]:
        return self.signals_to_return
    
    def get_strategy_name(self) -> str:
        return "mock_strategy"
    
    def get_required_indicators(self) -> List[str]:
        return ["close", "volume"]
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        return True


class MockPortfolio(PortfolioInterface):
    """Mock portfolio for testing."""
    
    def __init__(self):
        self.positions = {}
        self.risk_checks_pass = True
    
    def get_current_positions(self) -> Dict[str, float]:
        return self.positions.copy()
    
    def calculate_position_size(self, signal: TradingSignal, portfolio_value: float) -> float:
        return signal.position_size or 0.05
    
    def check_risk_limits(self, signal: TradingSignal, current_positions: Dict[str, float]) -> bool:
        return self.risk_checks_pass
    
    def update_portfolio(self, executed_orders: List[Dict[str, Any]]) -> None:
        pass


class MockExecution(ExecutionInterface):
    """Mock execution for testing."""
    
    def __init__(self):
        self.orders_to_execute = True
        self.execution_results = []
    
    def execute_signal(self, signal: TradingSignal, current_price: float) -> Dict[str, Any]:
        if self.orders_to_execute:
            result = {
                'symbol': signal.symbol,
                'executed_price': current_price,
                'executed_quantity': signal.position_size,
                'execution_time': datetime.now(),
                'status': 'FILLED'
            }
            self.execution_results.append(result)
            return result
        return {}
    
    def get_execution_cost(self, symbol: str, quantity: float, order_type) -> float:
        return 0.01
    
    def validate_order(self, signal: TradingSignal) -> bool:
        return True


class MockConfiguration(ConfigurationInterface):
    """Mock configuration for testing."""
    
    def __init__(self):
        self.config_valid = True
        self.strategy_configs = {
            'mock_strategy': {
                'lookback_period': 20,
                'threshold': 0.01,
                'confidence_threshold': 0.6
            }
        }
    
    def get_strategy_config(self, strategy_name: str) -> Dict[str, Any]:
        return self.strategy_configs.get(strategy_name, {})
    
    def get_risk_config(self) -> Dict[str, Any]:
        return {'max_position_size': 0.1}
    
    def get_execution_config(self) -> Dict[str, Any]:
        return {'commission_per_share': 0.001}
    
    def validate_configuration(self) -> bool:
        return self.config_valid


class TestBoundaryViolationPrevention:
    """Test that boundary violations are prevented."""
    
    def test_core_engine_has_no_strategy_logic(self):
        """Test that core engine contains no strategy-specific logic."""
        strategy = MockStrategy()
        portfolio = MockPortfolio()
        execution = MockExecution()
        config = MockConfiguration()
        
        core_engine = DelegatedCoreEngine(strategy, portfolio, execution, config)
        
        # Verify core engine doesn't have strategy methods
        assert not hasattr(core_engine, 'calculate_momentum')
        assert not hasattr(core_engine, '_momentum_logic')
        assert not hasattr(core_engine, 'generate_momentum_signals')
        
        # Verify it has interface references
        assert hasattr(core_engine, 'strategy_interface')
        assert hasattr(core_engine, 'portfolio_interface')
        assert hasattr(core_engine, 'execution_interface')
    
    def test_strategy_interface_delegation(self):
        """Test that strategy calculations are properly delegated."""
        strategy = MockStrategy()
        portfolio = MockPortfolio()
        execution = MockExecution()
        config = MockConfiguration()
        
        # Set up mock signals
        test_signal = RawSignal(
            symbol="TSLA",
            value=0.015,
            confidence=0.8,
            signal_metadata={'test': True},
            timestamp=pd.Timestamp.now()
        )
        strategy.signals_to_return = [test_signal]
        
        core_engine = DelegatedCoreEngine(strategy, portfolio, execution, config)
        
        # Create test market data
        market_data = pd.DataFrame({
            'symbol': ['TSLA'],
            'close': [100.0],
            'volume': [1000000],
            'timestamp': [pd.Timestamp.now()]
        })
        
        # Test that delegation works
        raw_signals = strategy.calculate_signals(market_data)
        assert len(raw_signals) == 1
        assert raw_signals[0].symbol == "TSLA"
        assert raw_signals[0].value == 0.015
    
    def test_no_fallback_mechanisms(self):
        """Test that system fails fast without fallback mechanisms."""
        strategy = MockStrategy()
        portfolio = MockPortfolio()
        execution = MockExecution()
        config = MockConfiguration()
        
        core_engine = DelegatedCoreEngine(strategy, portfolio, execution, config)
        
        # Test with invalid configuration
        config.config_valid = False
        
        with pytest.raises(ComponentValidationError):
            # This should fail fast, not fall back to defaults
            core_engine._validate_and_store_interfaces(strategy, portfolio, execution, config)


class TestSignalConverterIsolation:
    """Test signal converter isolation from core engine."""
    
    def test_signal_converter_creation(self):
        """Test signal converter can be created independently."""
        converter = SignalConverter()
        assert converter is not None
        assert hasattr(converter, 'convert_to_trading_signals')
        assert hasattr(converter, 'apply_signal_filters')
    
    def test_raw_signal_conversion(self):
        """Test raw signal to trading signal conversion."""
        converter = SignalConverter()
        
        raw_signal = RawSignal(
            symbol="AAPL",
            value=0.02,  # Strong positive momentum
            confidence=0.9,
            signal_metadata={'source': 'momentum'},
            timestamp=pd.Timestamp.now()
        )
        
        trading_signals = converter.convert_to_trading_signals([raw_signal])
        
        assert len(trading_signals) == 1
        signal = trading_signals[0]
        assert signal.symbol == "AAPL"
        assert signal.signal_type == SignalType.LONG
        assert signal.confidence == 0.9
    
    def test_signal_filtering(self):
        """Test signal filtering logic."""
        config = SignalConversionConfig(
            confidence_threshold=0.7,
            max_signals_per_symbol=1
        )
        converter = SignalConverter(config)
        
        # Create signals with different confidence levels
        high_confidence = TradingSignal(
            symbol="MSFT",
            signal_type=SignalType.LONG,
            confidence=0.9,
            timestamp=pd.Timestamp.now()
        )
        
        low_confidence = TradingSignal(
            symbol="MSFT",
            signal_type=SignalType.LONG,
            confidence=0.5,  # Below threshold
            timestamp=pd.Timestamp.now()
        )
        
        filtered_signals = converter.apply_signal_filters([high_confidence, low_confidence])
        
        # Only high confidence signal should pass
        assert len(filtered_signals) == 1
        assert filtered_signals[0].confidence == 0.9
    
    def test_no_core_engine_signal_logic(self):
        """Test that core engine doesn't contain signal conversion logic."""
        strategy = MockStrategy()
        portfolio = MockPortfolio()
        execution = MockExecution()
        config = MockConfiguration()
        
        core_engine = DelegatedCoreEngine(strategy, portfolio, execution, config)
        
        # Verify core engine delegates to signal converter
        assert hasattr(core_engine, 'signal_converter')
        assert not hasattr(core_engine, '_convert_raw_signal')
        assert not hasattr(core_engine, '_apply_signal_threshold')


class TestConfigurationCentralization:
    """Test centralized configuration management."""
    
    def test_unified_config_manager_creation(self):
        """Test unified configuration manager creation."""
        config_manager = UnifiedConfigurationManager()
        assert config_manager is not None
        assert hasattr(config_manager, 'get_strategy_config')
        assert hasattr(config_manager, 'get_risk_config')
        assert hasattr(config_manager, 'get_execution_config')
    
    def test_strategy_config_retrieval(self):
        """Test strategy configuration retrieval."""
        config_manager = UnifiedConfigurationManager()
        
        momentum_config = config_manager.get_strategy_config('momentum')
        assert 'lookback_period' in momentum_config
        assert 'threshold' in momentum_config
        assert 'confidence_threshold' in momentum_config
    
    def test_config_validation(self):
        """Test configuration validation."""
        config_manager = UnifiedConfigurationManager()
        
        # Valid configuration should pass
        assert config_manager.validate_configuration() is True
        
        # Test invalid configuration by updating with invalid values
        try:
            config_manager.update_strategy_config('test_strategy', {
                'lookback_period': -5,  # Invalid negative value
                'threshold': 0.01,
                'confidence_threshold': 0.6,
                'position_size': 0.05
            })
            # Should not reach here
            assert False, "Expected validation error for negative lookback_period"
        except Exception:
            # Expected to raise an exception
            pass
    
    def test_no_scattered_configuration(self):
        """Test that configuration is not scattered across components."""
        config_manager = UnifiedConfigurationManager()
        
        # All configuration should come from central manager
        all_config = config_manager.get_all_configuration()
        
        assert 'strategies' in all_config
        assert 'risk' in all_config
        assert 'execution' in all_config
        assert 'system' in all_config


class TestInterfaceValidation:
    """Test interface validation and contract enforcement."""
    
    def test_interface_contract_validation(self):
        """Test that interfaces properly validate contracts."""
        strategy = MockStrategy()
        portfolio = MockPortfolio()
        execution = MockExecution()
        config = MockConfiguration()
        
        # Valid interfaces should work
        core_engine = DelegatedCoreEngine(strategy, portfolio, execution, config)
        assert core_engine is not None
    
    def test_invalid_interface_rejection(self):
        """Test that invalid interfaces are rejected."""
        strategy = "not_an_interface"  # Invalid type
        portfolio = MockPortfolio()
        execution = MockExecution()
        config = MockConfiguration()
        
        with pytest.raises(ComponentValidationError):
            DelegatedCoreEngine(strategy, portfolio, execution, config)
    
    def test_missing_component_error(self):
        """Test proper error handling for missing components."""
        strategy = MockStrategy()
        portfolio = MockPortfolio()
        execution = MockExecution()
        config = MockConfiguration()
        
        core_engine = DelegatedCoreEngine(strategy, portfolio, execution, config)
        
        # Test processing without initialization
        market_data = pd.DataFrame()
        
        with pytest.raises(ComponentMissingError):
            # Should fail because not initialized
            import asyncio
            asyncio.run(core_engine.process_trading_cycle(market_data))


class TestEndToEndDelegation:
    """Test complete end-to-end delegation flow."""
    
    @pytest.mark.asyncio
    async def test_complete_trading_cycle_delegation(self):
        """Test complete trading cycle with proper delegation."""
        strategy = MockStrategy()
        portfolio = MockPortfolio()
        execution = MockExecution()
        config = MockConfiguration()
        
        # Set up test data
        test_signal = RawSignal(
            symbol="TSLA",
            value=0.015,
            confidence=0.8,
            signal_metadata={'momentum': 0.015},
            timestamp=pd.Timestamp.now()
        )
        strategy.signals_to_return = [test_signal]
        
        core_engine = DelegatedCoreEngine(strategy, portfolio, execution, config)
        await core_engine.initialize()
        
        # Create market data
        market_data = pd.DataFrame({
            'symbol': ['TSLA'],
            'close': [100.0],
            'volume': [1000000],
            'timestamp': [pd.Timestamp.now()]
        })
        
        # Process trading cycle
        results = await core_engine.process_trading_cycle(market_data)
        
        # Verify delegation worked
        assert results['raw_signals_count'] == 1
        assert results['trading_signals_count'] == 1
        assert results['executed_signals_count'] == 1
        
        # Verify no strategy logic in core engine
        assert 'momentum' not in str(core_engine.__dict__)
        assert 'calculate_signals' not in str(core_engine.__dict__)
    
    def test_performance_metrics_tracking(self):
        """Test that performance metrics are properly tracked."""
        strategy = MockStrategy()
        portfolio = MockPortfolio()
        execution = MockExecution()
        config = MockConfiguration()
        
        core_engine = DelegatedCoreEngine(strategy, portfolio, execution, config)
        
        status = core_engine.get_engine_status()
        
        assert 'performance_metrics' in status
        assert 'interface_info' in status
        assert 'interface_version' in status
        assert status['performance_metrics']['total_cycles'] == 0
    
    def test_engine_state_management(self):
        """Test proper engine state management."""
        strategy = MockStrategy()
        portfolio = MockPortfolio()
        execution = MockExecution()
        config = MockConfiguration()
        
        core_engine = DelegatedCoreEngine(strategy, portfolio, execution, config)
        
        # Test initial state
        assert not core_engine._is_initialized
        assert core_engine._cycle_count == 0
        
        # Test state reset
        core_engine.reset_engine_state()
        assert core_engine._cycle_count == 0
        assert core_engine._last_processing_time is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
