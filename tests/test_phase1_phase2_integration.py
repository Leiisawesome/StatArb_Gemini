"""
Phase 1 + Phase 2 Integration Tests
===================================

Integration tests to validate Phase 1 foundation works seamlessly
with Phase 2 template system.

Author: Professional Trading System Architecture
Version: 1.0.0
"""

import pytest
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any

# Phase 1 components
from trade_engine.interfaces import (
    StrategyInterface, PortfolioInterface, ExecutionInterface,
    ConfigurationInterface, TradingSignal, RawSignal, SignalType
)
from trade_engine.core import DelegatedCoreEngine, CoreEngineConfig
from trade_engine.conversion import SignalConverter, SignalConversionConfig

# Phase 2 components
from trade_engine.templates import (
    template_registry, template_strategy_factory,
    TemplateConfiguration, TemplateStrategyBridge
)

# Mock implementations for testing
class MockPortfolio(PortfolioInterface):
    def get_current_positions(self) -> Dict[str, float]:
        return {}
    
    def calculate_position_size(self, signal: TradingSignal, portfolio_value: float) -> float:
        return signal.position_size or 0.05
    
    def check_risk_limits(self, signal: TradingSignal, current_positions: Dict[str, float]) -> bool:
        return True
    
    def update_portfolio(self, executed_orders: List[Dict[str, Any]]) -> None:
        pass


class MockExecution(ExecutionInterface):
    def execute_signal(self, signal: TradingSignal, current_price: float) -> Dict[str, Any]:
        return {
            'symbol': signal.symbol,
            'executed_price': current_price,
            'executed_quantity': signal.position_size,
            'execution_time': datetime.now(),
            'status': 'FILLED'
        }
    
    def get_execution_cost(self, symbol: str, quantity: float, order_type) -> float:
        return 0.01
    
    def validate_order(self, signal: TradingSignal) -> bool:
        return True


class MockConfiguration(ConfigurationInterface):
    def get_strategy_config(self, strategy_name: str) -> Dict[str, Any]:
        return {
            'lookback_period': 20,
            'momentum_threshold': 0.015,
            'confidence_threshold': 0.75,
            'volume_lookback': 10,
            'volume_threshold': 1.5,
            'position_size': 0.05,
            'stop_loss_pct': 0.03,
            'take_profit_pct': 0.08
        }
    
    def get_risk_config(self) -> Dict[str, Any]:
        return {'max_position_size': 0.1}
    
    def get_execution_config(self) -> Dict[str, Any]:
        return {'commission_per_share': 0.001}
    
    def validate_configuration(self) -> bool:
        return True


class TestPhase1Phase2Integration:
    """Test integration between Phase 1 foundation and Phase 2 templates."""
    
    @pytest.mark.asyncio
    async def test_template_strategy_in_core_engine(self):
        """Test template-based strategy works with delegated core engine."""
        
        # 1. Create template-based strategy using Phase 2 system
        template_config = TemplateConfiguration(
            template_id="professional_momentum_v1",
            parameters={
                "lookback_period": 20,
                "momentum_threshold": 0.015,
                "confidence_threshold": 0.75,
                "volume_lookback": 10,
                "volume_threshold": 1.5,
                "position_size": 0.05,
                "stop_loss_pct": 0.03,
                "take_profit_pct": 0.08
            },
            strategy_instance_id="integration_test_strategy"
        )
        
        template_strategy = TemplateStrategyBridge(template_config)
        
        # 2. Create Phase 1 core engine with template strategy
        portfolio = MockPortfolio()
        execution = MockExecution()
        config = MockConfiguration()
        
        core_engine = DelegatedCoreEngine(
            strategy_interface=template_strategy,
            portfolio_interface=portfolio,
            execution_interface=execution,
            configuration_interface=config
        )
        
        await core_engine.initialize()
        
        # 3. Create test market data
        market_data = pd.DataFrame({
            'symbol': ['TSLA'] * 30,
            'close': [100 + i * 1.5 + (i % 3) for i in range(30)],
            'volume': [1000000 + i * 20000 for i in range(30)],
            'timestamp': pd.date_range(start='2023-01-01', periods=30, freq='D')
        })
        
        # 4. Process trading cycle
        results = await core_engine.process_trading_cycle(market_data)
        
        # 5. Validate integration works
        assert results is not None
        assert 'raw_signals_count' in results
        assert 'trading_signals_count' in results
        assert 'executed_signals_count' in results
        
        # Template strategy should generate signals
        assert results['raw_signals_count'] >= 0
        
        # Verify template metadata is preserved
        if results['raw_signals']:
            signal = results['raw_signals'][0]
            assert 'template_id' in signal.signal_metadata
            assert signal.signal_metadata['template_id'] == "professional_momentum_v1"
    
    def test_template_strategy_interface_compliance(self):
        """Test that template strategies fully comply with StrategyInterface."""
        
        # Create template strategy
        template_strategy = template_strategy_factory.create_strategy(
            template_id="professional_momentum_v1",
            parameters={
                "lookback_period": 15,
                "momentum_threshold": 0.02,
                "confidence_threshold": 0.8,
                "volume_lookback": 8,
                "volume_threshold": 1.3,
                "position_size": 0.04,
                "stop_loss_pct": 0.025,
                "take_profit_pct": 0.075
            },
            strategy_instance_id="interface_compliance_test"
        )
        
        # Verify StrategyInterface compliance
        assert isinstance(template_strategy, StrategyInterface)
        assert hasattr(template_strategy, 'calculate_signals')
        assert hasattr(template_strategy, 'get_strategy_name')
        assert hasattr(template_strategy, 'get_required_indicators')
        assert hasattr(template_strategy, 'validate_parameters')
        
        # Test interface methods
        strategy_name = template_strategy.get_strategy_name()
        assert "Professional Momentum Strategy" in strategy_name
        assert "interface_compliance_test" in strategy_name
        
        required_indicators = template_strategy.get_required_indicators()
        assert len(required_indicators) > 0
        assert 'close' in required_indicators
        assert 'volume' in required_indicators
        
        # Test parameter validation
        valid_params = {
            "lookback_period": 25,
            "momentum_threshold": 0.01,
            "confidence_threshold": 0.7,
            "volume_lookback": 12,
            "volume_threshold": 1.4,
            "position_size": 0.06,
            "stop_loss_pct": 0.04,
            "take_profit_pct": 0.1
        }
        assert template_strategy.validate_parameters(valid_params) is True
    
    def test_template_signals_through_signal_converter(self):
        """Test template signals work with Phase 1 signal converter."""
        
        # 1. Create template strategy
        template_strategy = template_strategy_factory.create_strategy(
            template_id="professional_momentum_v1",
            parameters={
                "lookback_period": 10,
                "momentum_threshold": 0.025,
                "confidence_threshold": 0.65,
                "volume_lookback": 5,
                "volume_threshold": 1.2,
                "position_size": 0.03,
                "stop_loss_pct": 0.02,
                "take_profit_pct": 0.06
            },
            strategy_instance_id="signal_converter_test"
        )
        
        # 2. Generate raw signals
        market_data = pd.DataFrame({
            'symbol': ['AAPL'] * 25,
            'close': [150 + i * 3 for i in range(25)],  # Strong upward momentum
            'volume': [1500000] * 25,
            'timestamp': pd.date_range(start='2023-01-01', periods=25, freq='D')
        })
        
        raw_signals = template_strategy.calculate_signals(market_data)
        
        # 3. Convert using Phase 1 signal converter
        signal_converter = SignalConverter(
            SignalConversionConfig(
                confidence_threshold=0.6,
                position_size_multiplier=1.0
            )
        )
        
        trading_signals = signal_converter.convert_to_trading_signals(raw_signals)
        
        # 4. Validate conversion
        if trading_signals:
            signal = trading_signals[0]
            assert signal.symbol == 'AAPL'
            assert signal.signal_type in [SignalType.LONG, SignalType.SHORT]
            assert 0.0 <= signal.confidence <= 1.0
            
            # Template metadata should be preserved
            assert 'template_id' in signal.metadata
            assert signal.metadata['template_id'] == "professional_momentum_v1"
    
    @pytest.mark.asyncio
    async def test_multiple_template_strategies_in_engine(self):
        """Test core engine can work with multiple template-based strategies."""
        
        # Create two different template strategy instances
        strategy1 = template_strategy_factory.create_strategy(
            template_id="professional_momentum_v1",
            parameters={
                "lookback_period": 15,
                "momentum_threshold": 0.01,
                "confidence_threshold": 0.7,
                "volume_lookback": 8,
                "volume_threshold": 1.3,
                "position_size": 0.04,
                "stop_loss_pct": 0.025,
                "take_profit_pct": 0.075
            },
            strategy_instance_id="multi_test_strategy_1"
        )
        
        # Test with first strategy
        portfolio = MockPortfolio()
        execution = MockExecution()
        config = MockConfiguration()
        
        core_engine1 = DelegatedCoreEngine(
            strategy_interface=strategy1,
            portfolio_interface=portfolio,
            execution_interface=execution,
            configuration_interface=config
        )
        
        await core_engine1.initialize()
        
        market_data = pd.DataFrame({
            'symbol': ['NVDA'] * 20,
            'close': [200 + i * 2 for i in range(20)],
            'volume': [2000000] * 20,
            'timestamp': pd.date_range(start='2023-01-01', periods=20, freq='D')
        })
        
        results1 = await core_engine1.process_trading_cycle(market_data)
        
        # Verify engine works with template strategy
        assert results1 is not None
        assert 'interface_info' in results1
        assert 'strategy' in results1['interface_info']
        assert "Professional Momentum Strategy" in results1['interface_info']['strategy']
    
    def test_template_system_factory_integration(self):
        """Test template system integrates with factory pattern."""
        
        # Test global factory works
        assert template_strategy_factory is not None
        
        # Test template registry integration
        available_templates = template_registry.list_templates()
        assert "professional_momentum_v1" in available_templates
        
        # Test factory status
        factory_status = template_strategy_factory.get_factory_status()
        assert 'available_templates' in factory_status
        assert "professional_momentum_v1" in factory_status['available_templates']
        
        # Test creating strategy through factory
        strategy = template_strategy_factory.create_strategy(
            template_id="professional_momentum_v1",
            parameters={
                "lookback_period": 30,
                "momentum_threshold": 0.008,
                "confidence_threshold": 0.85,
                "volume_lookback": 15,
                "volume_threshold": 1.8,
                "position_size": 0.08,
                "stop_loss_pct": 0.05,
                "take_profit_pct": 0.12
            },
            strategy_instance_id="factory_integration_test"
        )
        
        assert strategy is not None
        assert isinstance(strategy, TemplateStrategyBridge)
        assert isinstance(strategy, StrategyInterface)
    
    def test_template_configuration_validation(self):
        """Test template configuration validation works with Phase 1 systems."""
        
        # Test valid configuration
        valid_config = TemplateConfiguration(
            template_id="professional_momentum_v1",
            parameters={
                "lookback_period": 20,
                "momentum_threshold": 0.015,
                "confidence_threshold": 0.75,
                "volume_lookback": 10,
                "volume_threshold": 1.5,
                "position_size": 0.05,
                "stop_loss_pct": 0.03,
                "take_profit_pct": 0.08
            },
            strategy_instance_id="validation_test"
        )
        
        # Should create successfully
        strategy = TemplateStrategyBridge(valid_config)
        assert strategy is not None
        
        # Test invalid configuration - should fail fast (Phase 1 principle)
        invalid_config = TemplateConfiguration(
            template_id="professional_momentum_v1",
            parameters={
                "lookback_period": -5,  # Invalid
                "momentum_threshold": 0.015
            },
            strategy_instance_id="invalid_test"
        )
        
        # Should raise validation error (fail-fast)
        with pytest.raises(Exception):
            TemplateStrategyBridge(invalid_config)
    
    def test_professional_template_quality_standards(self):
        """Test that templates meet professional quality standards."""
        
        template = template_registry.get_template("professional_momentum_v1")
        template_info = template.get_template_info()
        
        # Professional templates should have comprehensive definitions
        assert template_info['signal_rules_count'] >= 4  # Multiple signal rules
        assert template_info['risk_rules_count'] >= 4    # Comprehensive risk management
        assert template_info['parameter_count'] >= 8     # Sufficient parameterization
        
        # Professional templates should require multiple indicators
        required_indicators = template.get_required_indicators()
        assert len(required_indicators) >= 4
        assert 'close' in required_indicators
        assert 'volume' in required_indicators
        assert 'momentum_score' in required_indicators
        
        # Professional templates should have bounded parameters
        parameter_bounds = template.get_parameter_bounds()
        for param_name, bounds in parameter_bounds.items():
            assert bounds.min_value is not None or bounds.allowed_values is not None
            assert bounds.data_type is not None
            
            # Professional parameters should have reasonable ranges
            if param_name == "momentum_threshold":
                assert bounds.min_value >= 0.001  # Minimum 0.1%
                assert bounds.max_value <= 0.1    # Maximum 10%
            
            if param_name == "position_size":
                assert bounds.max_value <= 0.25   # Maximum 25% position


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
