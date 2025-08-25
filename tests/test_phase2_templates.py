"""
Phase 2 Strategy Template System Tests
=====================================

Unit tests to validate Phase 2 implementation focusing on:
- Template system functionality
- Professional momentum template
- Template-strategy bridge conversion
- Parameter bounds validation

Author: Professional Trading System Architecture
Version: 1.0.0
"""

import pytest
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any

# Import the components under test
from trade_engine.templates import (
    BaseTemplate,
    TemplateRegistry,
    ParameterBounds,
    SignalRule,
    RiskRule,
    EntryExitRule,
    SignalCondition,
    TemplateValidationError,
    template_registry,
    ProfessionalMomentumTemplate,
    TemplateStrategyBridge,
    TemplateConfiguration,
    TemplateStrategyFactory,
    template_strategy_factory
)


class TestTemplateFoundation:
    """Test template system foundation."""
    
    def test_parameter_bounds_validation(self):
        """Test parameter bounds validation."""
        bounds = ParameterBounds(
            min_value=0.1,
            max_value=1.0,
            data_type=float,
            is_required=True
        )
        
        # Valid values
        assert bounds.validate(0.5) is True
        assert bounds.validate(0.1) is True
        assert bounds.validate(1.0) is True
        
        # Invalid values
        assert bounds.validate(0.05) is False  # Below minimum
        assert bounds.validate(1.5) is False   # Above maximum
        assert bounds.validate(None) is False  # Required parameter
        
        # Type conversion
        assert bounds.validate("0.5") is True  # String to float conversion
    
    def test_signal_rule_creation(self):
        """Test signal rule creation and validation."""
        rule = SignalRule(
            rule_id="test_momentum",
            condition=SignalCondition.GREATER_THAN,
            indicator="momentum_score",
            threshold=0.01,
            signal_strength=0.8,
            confidence_multiplier=1.2
        )
        
        assert rule.rule_id == "test_momentum"
        assert rule.condition == SignalCondition.GREATER_THAN
        assert rule.signal_strength == 0.8
        assert rule.confidence_multiplier == 1.2
    
    def test_signal_rule_validation(self):
        """Test signal rule validation."""
        # Invalid signal strength
        with pytest.raises(TemplateValidationError):
            SignalRule(
                rule_id="invalid",
                condition=SignalCondition.GREATER_THAN,
                indicator="test",
                threshold=0.1,
                signal_strength=1.5  # Invalid - over 1.0
            )
        
        # Invalid confidence multiplier
        with pytest.raises(TemplateValidationError):
            SignalRule(
                rule_id="invalid",
                condition=SignalCondition.GREATER_THAN,
                indicator="test",
                threshold=0.1,
                confidence_multiplier=3.0  # Invalid - over 2.0
            )
    
    def test_template_registry(self):
        """Test template registry functionality."""
        registry = TemplateRegistry()
        
        # Create a simple test template
        class TestTemplate(BaseTemplate):
            def _define_template(self):
                self.add_parameter_bounds(
                    "test_param",
                    ParameterBounds(min_value=0.0, max_value=1.0, data_type=float)
                )
        
        template = TestTemplate("test_template", "Test Template", "A test template")
        
        # Register template
        registry.register_template(template, "test")
        
        # Test retrieval
        retrieved = registry.get_template("test_template")
        assert retrieved is not None
        assert retrieved.template_id == "test_template"
        
        # Test listing
        templates = registry.list_templates("test")
        assert "test_template" in templates


class TestProfessionalMomentumTemplate:
    """Test professional momentum template."""
    
    def test_momentum_template_creation(self):
        """Test momentum template creation."""
        template = ProfessionalMomentumTemplate(
            "test_momentum",
            "Test Momentum",
            "Test momentum template"
        )
        
        assert template.template_id == "test_momentum"
        assert template.name == "Test Momentum"
        
        # Check that template is properly defined
        parameter_bounds = template.get_parameter_bounds()
        assert "lookback_period" in parameter_bounds
        assert "momentum_threshold" in parameter_bounds
        assert "confidence_threshold" in parameter_bounds
        
        signal_rules = template.get_signal_rules()
        assert len(signal_rules) > 0
        
        risk_rules = template.get_risk_rules()
        assert len(risk_rules) > 0
    
    def test_momentum_template_parameter_validation(self):
        """Test momentum template parameter validation."""
        template = ProfessionalMomentumTemplate(
            "test_momentum",
            "Test Momentum",
            "Test momentum template"
        )
        
        # Valid parameters
        valid_params = {
            "lookback_period": 20,
            "momentum_threshold": 0.015,
            "confidence_threshold": 0.75,
            "volume_lookback": 10,
            "volume_threshold": 1.5,
            "position_size": 0.05,
            "stop_loss_pct": 0.03,
            "take_profit_pct": 0.08
        }
        
        assert template.validate_parameters(valid_params) is True
        
        # Invalid parameters
        invalid_params = {
            "lookback_period": -5,  # Invalid negative
            "momentum_threshold": 0.015,
            "confidence_threshold": 0.75
        }
        
        with pytest.raises(TemplateValidationError):
            template.validate_parameters(invalid_params)
    
    def test_momentum_template_registry_integration(self):
        """Test momentum template is registered in global registry."""
        # Template should be auto-registered
        template = template_registry.get_template("professional_momentum_v1")
        assert template is not None
        assert isinstance(template, ProfessionalMomentumTemplate)
        
        # Check template info
        info = template.get_template_info()
        assert info['template_id'] == "professional_momentum_v1"
        assert "momentum" in info['name'].lower()
    
    def test_momentum_template_professional_parameters(self):
        """Test that momentum template has professional-grade parameters."""
        template = template_registry.get_template("professional_momentum_v1")
        
        bounds = template.get_parameter_bounds()
        
        # Check professional parameter ranges
        assert bounds["momentum_threshold"].min_value == 0.001  # 0.1% minimum
        assert bounds["momentum_threshold"].max_value == 0.1    # 10% maximum
        assert bounds["momentum_threshold"].default_value == 0.015  # 1.5% professional default
        
        assert bounds["confidence_threshold"].min_value == 0.5
        assert bounds["confidence_threshold"].max_value == 0.95
        assert bounds["confidence_threshold"].default_value == 0.75  # 75% professional confidence
        
        assert bounds["position_size"].max_value == 0.25  # 25% maximum position
        assert bounds["stop_loss_pct"].default_value == 0.03  # 3% professional stop


class TestTemplateStrategyBridge:
    """Test template-strategy bridge conversion."""
    
    def test_template_bridge_creation(self):
        """Test template bridge creation."""
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
            strategy_instance_id="test_momentum_001"
        )
        
        bridge = TemplateStrategyBridge(template_config)
        
        assert bridge.get_strategy_name().endswith("test_momentum_001")
        assert len(bridge.get_required_indicators()) > 0
    
    def test_template_bridge_signal_generation(self):
        """Test template bridge signal generation."""
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
            strategy_instance_id="test_momentum_002"
        )
        
        bridge = TemplateStrategyBridge(template_config)
        
        # Create test market data
        dates = pd.date_range(start='2023-01-01', periods=30, freq='D')
        market_data = pd.DataFrame({
            'symbol': ['TSLA'] * 30,
            'close': [100 + i * 0.5 + (i % 5) * 2 for i in range(30)],  # Trending with noise
            'volume': [1000000 + i * 10000 for i in range(30)],
            'timestamp': dates
        })
        
        # Generate signals
        signals = bridge.calculate_signals(market_data)
        
        # Should generate some signals for trending data
        assert isinstance(signals, list)
        
        # If signals are generated, validate their structure
        if signals:
            signal = signals[0]
            assert hasattr(signal, 'symbol')
            assert hasattr(signal, 'value')
            assert hasattr(signal, 'confidence')
            assert hasattr(signal, 'signal_metadata')
            assert signal.symbol == 'TSLA'
    
    def test_template_bridge_parameter_validation(self):
        """Test template bridge validates parameters."""
        template_config = TemplateConfiguration(
            template_id="professional_momentum_v1",
            parameters={
                "lookback_period": -5,  # Invalid negative
                "momentum_threshold": 0.015
            },
            strategy_instance_id="test_invalid"
        )
        
        # Should raise validation error
        with pytest.raises(TemplateValidationError):
            TemplateStrategyBridge(template_config)
    
    def test_template_bridge_indicator_calculation(self):
        """Test that bridge calculates required indicators."""
        template_config = TemplateConfiguration(
            template_id="professional_momentum_v1",
            parameters={
                "lookback_period": 10,
                "momentum_threshold": 0.01,
                "confidence_threshold": 0.6,
                "volume_lookback": 5,
                "volume_threshold": 1.2,
                "position_size": 0.03,
                "stop_loss_pct": 0.02,
                "take_profit_pct": 0.06
            },
            strategy_instance_id="test_indicators"
        )
        
        bridge = TemplateStrategyBridge(template_config)
        
        # Create test data with clear momentum
        market_data = pd.DataFrame({
            'symbol': ['AAPL'] * 25,
            'close': [100 + i * 2 for i in range(25)],  # Strong upward trend
            'volume': [1000000] * 25,
            'timestamp': pd.date_range(start='2023-01-01', periods=25, freq='D')
        })
        
        # Test indicator calculation
        indicators = bridge._calculate_indicators(market_data)
        
        assert 'momentum_score' in indicators
        assert 'volume_ratio' in indicators
        assert 'trend_strength' in indicators
        assert 'volatility_percentile' in indicators


class TestTemplateStrategyFactory:
    """Test template strategy factory."""
    
    def test_factory_strategy_creation(self):
        """Test factory creates strategies from templates."""
        factory = TemplateStrategyFactory()
        
        parameters = {
            "lookback_period": 15,
            "momentum_threshold": 0.02,
            "confidence_threshold": 0.8,
            "volume_lookback": 8,
            "volume_threshold": 1.3,
            "position_size": 0.04,
            "stop_loss_pct": 0.025,
            "take_profit_pct": 0.075
        }
        
        strategy = factory.create_strategy(
            template_id="professional_momentum_v1",
            parameters=parameters,
            strategy_instance_id="factory_test_001"
        )
        
        assert strategy is not None
        assert isinstance(strategy, TemplateStrategyBridge)
        assert "factory_test_001" in strategy.get_strategy_name()
    
    def test_factory_strategy_retrieval(self):
        """Test factory can retrieve created strategies."""
        factory = TemplateStrategyFactory()
        
        parameters = {
            "lookback_period": 12,
            "momentum_threshold": 0.018,
            "confidence_threshold": 0.7,
            "volume_lookback": 6,
            "volume_threshold": 1.4,
            "position_size": 0.06,
            "stop_loss_pct": 0.035,
            "take_profit_pct": 0.09
        }
        
        # Create strategy
        strategy = factory.create_strategy(
            template_id="professional_momentum_v1",
            parameters=parameters,
            strategy_instance_id="factory_test_002"
        )
        
        # Retrieve strategy
        retrieved = factory.get_strategy("factory_test_002")
        assert retrieved is strategy
        assert retrieved is not None
    
    def test_factory_invalid_template_error(self):
        """Test factory raises error for invalid template."""
        factory = TemplateStrategyFactory()
        
        with pytest.raises(TemplateValidationError):
            factory.create_strategy(
                template_id="nonexistent_template",
                parameters={},
                strategy_instance_id="invalid_test"
            )
    
    def test_global_factory_instance(self):
        """Test global factory instance works."""
        parameters = {
            "lookback_period": 25,
            "momentum_threshold": 0.012,
            "confidence_threshold": 0.65,
            "volume_lookback": 12,
            "volume_threshold": 1.6,
            "position_size": 0.07,
            "stop_loss_pct": 0.04,
            "take_profit_pct": 0.1
        }
        
        strategy = template_strategy_factory.create_strategy(
            template_id="professional_momentum_v1",
            parameters=parameters,
            strategy_instance_id="global_factory_test"
        )
        
        assert strategy is not None
        assert isinstance(strategy, TemplateStrategyBridge)


class TestTemplateSystemIntegration:
    """Test complete template system integration."""
    
    def test_end_to_end_template_flow(self):
        """Test complete template to strategy flow."""
        # 1. Get template from registry
        template = template_registry.get_template("professional_momentum_v1")
        assert template is not None
        
        # 2. Create strategy configuration
        parameters = {
            "lookback_period": 20,
            "momentum_threshold": 0.015,
            "confidence_threshold": 0.75,
            "volume_lookback": 10,
            "volume_threshold": 1.5,
            "position_size": 0.05,
            "stop_loss_pct": 0.03,
            "take_profit_pct": 0.08
        }
        
        # 3. Validate parameters
        assert template.validate_parameters(parameters) is True
        
        # 4. Create strategy using factory
        strategy = template_strategy_factory.create_strategy(
            template_id="professional_momentum_v1",
            parameters=parameters,
            strategy_instance_id="integration_test"
        )
        
        # 5. Test strategy interface compliance
        assert hasattr(strategy, 'calculate_signals')
        assert hasattr(strategy, 'get_strategy_name')
        assert hasattr(strategy, 'get_required_indicators')
        assert hasattr(strategy, 'validate_parameters')
        
        # 6. Test signal generation
        market_data = pd.DataFrame({
            'symbol': ['NVDA'] * 30,
            'close': [200 + i * 1.5 for i in range(30)],
            'volume': [2000000 + i * 50000 for i in range(30)],
            'timestamp': pd.date_range(start='2023-01-01', periods=30, freq='D')
        })
        
        signals = strategy.calculate_signals(market_data)
        assert isinstance(signals, list)
    
    def test_template_parameter_resolution(self):
        """Test template parameter resolution in rules."""
        template = template_registry.get_template("professional_momentum_v1")
        
        parameters = {
            "lookback_period": 15,
            "momentum_threshold": 0.02,
            "confidence_threshold": 0.8,
            "volume_lookback": 8,
            "volume_threshold": 1.3,
            "position_size": 0.04,
            "stop_loss_pct": 0.025,
            "take_profit_pct": 0.075
        }
        
        resolved = template.resolve_parameter_references(parameters)
        
        # Check that parameter references are resolved
        assert 'signal_rules' in resolved
        assert 'risk_rules' in resolved
        assert 'parameters' in resolved
        
        # Find a rule that should have resolved parameters
        signal_rules = resolved['signal_rules']
        momentum_rule = next((rule for rule in signal_rules if rule.rule_id == 'momentum_long_primary'), None)
        assert momentum_rule is not None
        assert momentum_rule.threshold == 0.02  # Should be resolved from parameter
    
    def test_template_metadata_information(self):
        """Test template provides comprehensive metadata."""
        template = template_registry.get_template("professional_momentum_v1")
        info = template.get_template_info()
        
        assert 'template_id' in info
        assert 'name' in info
        assert 'description' in info
        assert 'parameter_count' in info
        assert 'signal_rules_count' in info
        assert 'risk_rules_count' in info
        assert 'required_indicators' in info
        
        # Check that template has professional metadata
        assert info['signal_rules_count'] > 0
        assert info['risk_rules_count'] > 0
        assert len(info['required_indicators']) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
