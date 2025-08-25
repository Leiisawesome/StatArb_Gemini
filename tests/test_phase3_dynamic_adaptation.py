"""
Comprehensive tests for Phase 3: Dynamic Parameter System.

This test suite validates the real-time parameter adaptation, validation,
and rollback mechanisms for trading strategies.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch

# Dynamic adaptation components
from trade_engine.dynamic_adaptation import (
    RealTimeParameterOptimizer,
    ParameterValidator,
    AdaptationRollbackManager,
    AdaptationMetrics,
    AdaptationConfig,
    AdaptationMode,
    AdaptationTriggers,
    PerformanceSnapshot,
    ValidationResult,
    ParameterOptimizationResult
)

# Template system for integration
from trade_engine.templates import template_registry, TemplateConfiguration


class TestAdaptationConfig:
    """Test configuration classes for dynamic adaptation."""
    
    def test_adaptation_config_creation(self):
        """Test basic adaptation configuration creation."""
        config = AdaptationConfig()
        
        assert config.adaptation_mode == AdaptationMode.MODERATE
        assert config.enabled is True
        assert config.triggers is not None
        assert config.bounds is not None
        assert config.should_adapt() is True
    
    def test_adaptation_modes(self):
        """Test different adaptation modes."""
        modes_and_steps = {
            AdaptationMode.CONSERVATIVE: 0.05,
            AdaptationMode.MODERATE: 0.10,
            AdaptationMode.AGGRESSIVE: 0.20,
            AdaptationMode.DISABLED: 0.0
        }
        
        for mode, expected_step in modes_and_steps.items():
            config = AdaptationConfig(adaptation_mode=mode)
            assert config.get_adaptation_step_size() == expected_step
            assert config.should_adapt() == (mode != AdaptationMode.DISABLED)
    
    def test_config_validation(self):
        """Test configuration validation."""
        # Valid configuration
        valid_config = AdaptationConfig(
            learning_rate=0.1,
            momentum_factor=0.9,
            performance_window_trades=100
        )
        assert valid_config.validate_config() is True
        
        # Invalid configurations
        invalid_configs = [
            AdaptationConfig(learning_rate=1.5),  # > 1.0
            AdaptationConfig(momentum_factor=-0.1),  # < 0.0
            AdaptationConfig(performance_window_trades=5)  # < 10
        ]
        
        for config in invalid_configs:
            assert config.validate_config() is False


class TestAdaptationMetrics:
    """Test performance metrics and analysis."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.metrics = AdaptationMetrics("test_strategy")
    
    def test_add_trade_data(self):
        """Test adding trade data for tracking."""
        trade_data = {
            'timestamp': datetime.now(),
            'symbol': 'AAPL',
            'side': 'buy',
            'quantity': 100,
            'price': 150.0,
            'pnl': 500.0,
            'commission': 5.0,
            'position_closed': True,
            'position_value': 15000.0
        }
        
        self.metrics.add_trade(trade_data)
        
        assert len(self.metrics.trade_history) == 1
        assert len(self.metrics.daily_returns) == 1
        assert self.metrics.daily_returns[0] == pytest.approx((500.0 - 5.0) / 15000.0)
    
    def test_performance_snapshot_calculation(self):
        """Test performance snapshot calculation."""
        # Add sample trade data
        trades = [
            {'net_pnl': 100, 'timestamp': datetime.now()},
            {'net_pnl': -50, 'timestamp': datetime.now()},
            {'net_pnl': 200, 'timestamp': datetime.now()},
            {'net_pnl': -30, 'timestamp': datetime.now()}
        ]
        
        for trade in trades:
            self.metrics.trade_history.append(trade)
        
        self.metrics.daily_returns = [0.01, -0.005, 0.02, -0.003]
        
        snapshot = self.metrics.calculate_performance_snapshot()
        
        assert snapshot.strategy_id == "test_strategy"
        assert snapshot.total_trades == 4
        assert snapshot.total_return == 220.0  # 100 - 50 + 200 - 30
        assert snapshot.win_rate == 0.5  # 2 wins out of 4 trades
        assert len(snapshot.daily_returns) == 4
    
    def test_performance_comparison(self):
        """Test comparison between performance snapshots."""
        before = PerformanceSnapshot(
            timestamp=datetime.now(),
            strategy_id="test",
            total_trades=10,
            total_return=1000.0,
            daily_returns=[],
            sharpe_ratio=1.5,
            calmar_ratio=0.0,
            max_drawdown=0.1,
            volatility=0.2,
            var_95=0.0,
            win_rate=0.6,
            profit_factor=1.8,
            average_win=0.0,
            average_loss=0.0,
            largest_win=0.0,
            largest_loss=0.0,
            market_correlation=0.0,
            beta=0.0
        )
        
        after = PerformanceSnapshot(
            timestamp=datetime.now(),
            strategy_id="test",
            total_trades=15,
            total_return=1200.0,
            daily_returns=[],
            sharpe_ratio=1.2,
            calmar_ratio=0.0,
            max_drawdown=0.15,
            volatility=0.25,
            var_95=0.0,
            win_rate=0.55,
            profit_factor=1.5,
            average_win=0.0,
            average_loss=0.0,
            largest_win=0.0,
            largest_loss=0.0,
            market_correlation=0.0,
            beta=0.0
        )
        
        comparison = self.metrics.compare_performance(before, after)
        
        assert comparison['sharpe_change'] == pytest.approx(-0.3)  # 1.2 - 1.5
        assert comparison['return_change'] == 200.0  # 1200 - 1000
        assert comparison['drawdown_change'] == pytest.approx(0.05)  # 0.15 - 0.1
        assert comparison['win_rate_change'] == pytest.approx(-0.05)  # 0.55 - 0.6
    
    def test_adaptation_signal_strength(self):
        """Test adaptation signal strength calculation."""
        # Create performance history with degrading performance
        good_performance = PerformanceSnapshot(
            timestamp=datetime.now() - timedelta(days=1),
            strategy_id="test",
            total_trades=50,
            total_return=1000.0,
            daily_returns=[],
            sharpe_ratio=2.0,
            calmar_ratio=0.0,
            max_drawdown=0.05,
            volatility=0.15,
            var_95=0.0,
            win_rate=0.7,
            profit_factor=2.0,
            average_win=0.0,
            average_loss=0.0,
            largest_win=0.0,
            largest_loss=0.0,
            market_correlation=0.0,
            beta=0.0
        )
        
        poor_performance = PerformanceSnapshot(
            timestamp=datetime.now(),
            strategy_id="test",
            total_trades=60,
            total_return=800.0,
            daily_returns=[],
            sharpe_ratio=0.8,
            calmar_ratio=0.0,
            max_drawdown=0.20,
            volatility=0.30,
            var_95=0.0,
            win_rate=0.4,
            profit_factor=1.1,
            average_win=0.0,
            average_loss=0.0,
            largest_win=0.0,
            largest_loss=0.0,
            market_correlation=0.0,
            beta=0.0
        )
        
        self.metrics.performance_history = [good_performance, poor_performance]
        
        signal_strength = self.metrics.get_adaptation_signal_strength()
        
        # Should detect significant performance degradation
        assert signal_strength > 0.5
        assert signal_strength <= 1.0


class TestParameterValidator:
    """Test parameter validation system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Use the professional momentum template for testing
        self.validator = ParameterValidator("professional_momentum_v1")
    
    def test_valid_parameter_change(self):
        """Test validation of valid parameter changes."""
        result = self.validator.validate_parameter_change(
            "momentum_threshold",
            0.02,  # Valid value within bounds
            0.015  # Current value
        )
        
        assert result.valid is True
        assert len(result.errors) == 0
    
    def test_invalid_parameter_type(self):
        """Test validation of invalid parameter types."""
        result = self.validator.validate_parameter_change(
            "lookback_period",
            "invalid_string",  # Should be int
            20
        )
        
        assert result.valid is False
        assert "must be" in result.error_message
    
    def test_parameter_out_of_bounds(self):
        """Test validation of parameters outside bounds."""
        # Test below minimum
        result = self.validator.validate_parameter_change(
            "momentum_threshold",
            0.0005,  # Below minimum of 0.001
            0.015
        )
        assert result.valid is False
        assert "below minimum" in result.error_message
        
        # Test above maximum
        result = self.validator.validate_parameter_change(
            "momentum_threshold",
            0.15,  # Above maximum of 0.1
            0.015
        )
        assert result.valid is False
        assert "above maximum" in result.error_message
    
    def test_parameter_set_validation(self):
        """Test validation of complete parameter sets."""
        valid_parameters = {
            "momentum_threshold": 0.02,
            "confidence_threshold": 0.8,
            "position_size": 0.04
        }
        
        result = self.validator.validate_parameter_set(valid_parameters)
        assert result.valid is True
        
        # Test with invalid parameter
        invalid_parameters = {
            "momentum_threshold": 0.5,  # Too high
            "confidence_threshold": 0.8
        }
        
        result = self.validator.validate_parameter_set(invalid_parameters)
        assert result.valid is False
    
    def test_adaptation_magnitude_validation(self):
        """Test validation of adaptation magnitude."""
        current_params = {
            "momentum_threshold": 0.015,
            "position_size": 0.05
        }
        
        # Small changes should be valid
        small_changes = {
            "momentum_threshold": 0.017,  # ~13% change
            "position_size": 0.055  # 10% change
        }
        
        result = self.validator.validate_adaptation_magnitude(
            small_changes, current_params, max_change_percentage=0.25
        )
        assert result.valid is True
        
        # Large changes should be invalid
        large_changes = {
            "momentum_threshold": 0.025,  # ~67% change
            "position_size": 0.08  # 60% change
        }
        
        result = self.validator.validate_adaptation_magnitude(
            large_changes, current_params, max_change_percentage=0.25
        )
        assert result.valid is False
    
    def test_safe_parameter_range(self):
        """Test safe parameter range calculation."""
        current_value = 0.015
        safe_range = self.validator.get_safe_parameter_range(
            "momentum_threshold", current_value
        )
        
        assert 'min' in safe_range
        assert 'max' in safe_range
        assert 'current' in safe_range
        assert safe_range['current'] == current_value
        assert safe_range['min'] < current_value < safe_range['max']
    
    def test_parameter_relationships(self):
        """Test cross-parameter relationship validation."""
        # Test valid relationships
        valid_params = {
            "stop_loss_pct": 0.03,
            "take_profit_pct": 0.08,
            "position_size": 0.05
        }
        
        result = self.validator._validate_parameter_relationships(valid_params)
        assert result.valid is True
        
        # Test invalid relationships (stop loss >= take profit)
        invalid_params = {
            "stop_loss_pct": 0.08,
            "take_profit_pct": 0.05
        }
        
        result = self.validator._validate_parameter_relationships(invalid_params)
        assert result.valid is False
        assert "Stop loss" in result.error_message


class TestAdaptationRollback:
    """Test rollback management system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.rollback_manager = AdaptationRollbackManager("test_strategy")
    
    def test_create_adaptation_snapshot(self):
        """Test creation of adaptation snapshots."""
        parameters_before = {"momentum_threshold": 0.015, "position_size": 0.05}
        parameters_after = {"momentum_threshold": 0.018, "position_size": 0.04}
        
        performance_before = PerformanceSnapshot(
            timestamp=datetime.now(),
            strategy_id="test",
            total_trades=50,
            total_return=1000.0,
            daily_returns=[],
            sharpe_ratio=1.5,
            calmar_ratio=0.0,
            max_drawdown=0.1,
            volatility=0.2,
            var_95=0.0,
            win_rate=0.6,
            profit_factor=1.8,
            average_win=0.0,
            average_loss=0.0,
            largest_win=0.0,
            largest_loss=0.0,
            market_correlation=0.0,
            beta=0.0
        )
        
        market_conditions = {"volatility": 0.2, "correlation": 0.3}
        
        snapshot_id = self.rollback_manager.create_adaptation_snapshot(
            parameters_before=parameters_before,
            parameters_after=parameters_after,
            performance_before=performance_before,
            market_conditions=market_conditions,
            adaptation_reason="Performance degradation",
            adaptation_confidence=0.7,
            expected_improvement=0.15
        )
        
        assert snapshot_id.startswith("snapshot_test_strategy_")
        assert snapshot_id in self.rollback_manager.adaptation_snapshots
        
        snapshot = self.rollback_manager.adaptation_snapshots[snapshot_id]
        assert snapshot.strategy_id == "test_strategy"
        assert snapshot.parameters_before == parameters_before
        assert snapshot.parameters_after == parameters_after
        assert snapshot.adaptation_confidence == 0.7
    
    def test_rollback_decision_evaluation(self):
        """Test rollback decision evaluation."""
        # Create snapshot first (set timestamp to simulate past adaptation)
        past_time = datetime.now() - timedelta(hours=4)  # 4 hours ago
        parameters_before = {"momentum_threshold": 0.015}
        parameters_after = {"momentum_threshold": 0.020}

        performance_before = PerformanceSnapshot(
            timestamp=past_time,
            strategy_id="test",
            total_trades=50,
            total_return=1000.0,
            daily_returns=[],
            sharpe_ratio=2.0,
            calmar_ratio=0.0,
            max_drawdown=0.05,
            volatility=0.15,
            var_95=0.0,
            win_rate=0.7,
            profit_factor=2.0,
            average_win=0.0,
            average_loss=0.0,
            largest_win=0.0,
            largest_loss=0.0,
            market_correlation=0.0,
            beta=0.0
        )

        snapshot_id = self.rollback_manager.create_adaptation_snapshot(
            parameters_before=parameters_before,
            parameters_after=parameters_after,
            performance_before=performance_before,
            market_conditions={"volatility": 0.15},
            adaptation_reason="Testing",
            expected_improvement=0.1
        )
        
        # Manually set snapshot timestamp to past for testing
        self.rollback_manager.adaptation_snapshots[snapshot_id].timestamp = past_time        # Test with poor current performance (should trigger rollback)
        poor_performance = PerformanceSnapshot(
            timestamp=datetime.now(),
            strategy_id="test",
            total_trades=100,  # Sufficient trades
            total_return=500.0,  # Worse return
            daily_returns=[],
            sharpe_ratio=0.5,  # Much worse Sharpe
            calmar_ratio=0.0,
            max_drawdown=0.25,  # Much worse drawdown
            volatility=0.30,
            var_95=0.0,
            win_rate=0.4,  # Much worse win rate
            profit_factor=1.1,
            average_win=0.0,
            average_loss=0.0,
            largest_win=0.0,
            largest_loss=0.0,
            market_correlation=0.0,
            beta=0.0
        )
        
        decision = self.rollback_manager.evaluate_rollback_decision(
            snapshot_id=snapshot_id,
            current_performance=poor_performance,
            current_market_conditions={"volatility": 0.30}
        )
        
        assert decision.should_rollback is True
        assert decision.confidence > 0.6
        assert decision.rollback_parameters == parameters_before
    
    def test_rollback_insufficient_data(self):
        """Test rollback decision with insufficient data."""
        # Create snapshot (set timestamp to past for testing)
        past_time = datetime.now() - timedelta(hours=3)
        
        snapshot_id = self.rollback_manager.create_adaptation_snapshot(
            parameters_before={"momentum_threshold": 0.015},
            parameters_after={"momentum_threshold": 0.020},
            performance_before=PerformanceSnapshot(
                timestamp=past_time,
                strategy_id="test",
                total_trades=50,
                total_return=1000.0,
                daily_returns=[],
                sharpe_ratio=1.5,
                calmar_ratio=0.0,
                max_drawdown=0.1,
                volatility=0.2,
                var_95=0.0,
                win_rate=0.6,
                profit_factor=1.8,
                average_win=0.0,
                average_loss=0.0,
                largest_win=0.0,
                largest_loss=0.0,
                market_correlation=0.0,
                beta=0.0
            ),
            market_conditions={},
            adaptation_reason="Testing"
        )
        
        # Manually set snapshot timestamp to past for testing
        self.rollback_manager.adaptation_snapshots[snapshot_id].timestamp = past_time
        
        # Test with insufficient trades
        insufficient_performance = PerformanceSnapshot(
            timestamp=datetime.now(),
            strategy_id="test",
            total_trades=60,  # Only 10 new trades, less than required 50
            total_return=1100.0,
            daily_returns=[],
            sharpe_ratio=1.0,
            calmar_ratio=0.0,
            max_drawdown=0.15,
            volatility=0.25,
            var_95=0.0,
            win_rate=0.5,
            profit_factor=1.5,
            average_win=0.0,
            average_loss=0.0,
            largest_win=0.0,
            largest_loss=0.0,
            market_correlation=0.0,
            beta=0.0
        )
        
        decision = self.rollback_manager.evaluate_rollback_decision(
            snapshot_id=snapshot_id,
            current_performance=insufficient_performance,
            current_market_conditions={}
        )
        
        assert decision.should_rollback is False
        assert "Insufficient trades" in decision.reason


class TestRealTimeParameterOptimizer:
    """Test real-time parameter optimization."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Use the existing professional momentum template
        from trade_engine.templates.momentum_template import ProfessionalMomentumTemplate
        from trade_engine.templates.base_template import template_registry
        
        # Register template if not already registered
        if template_registry.get_template("professional_momentum_v1") is None:
            template = ProfessionalMomentumTemplate()
            template_registry.register_template(template)
        
        self.config = AdaptationConfig(
            adaptation_mode=AdaptationMode.MODERATE,
            max_adaptations_per_day=2
        )
        
        self.optimizer = RealTimeParameterOptimizer(
            strategy_id="test_strategy",
            template_id="professional_momentum_v1",
            adaptation_config=self.config
        )
    
    @pytest.mark.asyncio
    async def test_optimization_with_sufficient_data(self):
        """Test optimization when sufficient data is available."""
        # Add trade data to trigger adaptation
        for i in range(60):  # Above minimum threshold
            trade_data = {
                'timestamp': datetime.now() - timedelta(days=i//10),
                'symbol': 'AAPL',
                'side': 'buy' if i % 2 == 0 else 'sell',
                'quantity': 100,
                'price': 150.0,
                'pnl': -20.0 if i % 3 == 0 else 50.0,  # Mix of wins/losses
                'commission': 2.0,
                'net_pnl': -22.0 if i % 3 == 0 else 48.0,
                'position_closed': True,
                'position_value': 15000.0
            }
            self.optimizer.add_trade_data(trade_data)

        # Current parameters with poor performance metrics
        current_parameters = {
            "lookback_period": 20,
            "momentum_threshold": 0.015,
            "confidence_threshold": 0.75,
            "volume_lookback": 10,
            "volume_threshold": 1.5,
            "position_size": 0.05,
            "stop_loss_pct": 0.03,
            "take_profit_pct": 0.08
        }

        # Market conditions
        market_conditions = {
            "volatility": 0.25,
            "correlation": 0.3
        }

        # Set poor performance to trigger optimization
        poor_performance = PerformanceSnapshot(
            timestamp=datetime.now(),
            strategy_id="test",
            total_trades=60,
            total_return=500.0,
            daily_returns=[0.01, -0.02, 0.005, -0.01, 0.015],
            sharpe_ratio=0.3,  # Poor Sharpe ratio - should trigger optimization
            calmar_ratio=0.0,
            max_drawdown=0.15,  # High drawdown - should trigger stop loss adjustment
            volatility=0.30,
            var_95=0.0,
            win_rate=0.35,  # Low win rate - should trigger momentum threshold increase
            profit_factor=1.1,
            average_win=0.0,
            average_loss=0.0,
            largest_win=0.0,
            largest_loss=0.0,
            market_correlation=0.0,
            beta=0.0
        )
        
        # Instead of manually setting performance, let's override the calculate_performance_snapshot method
        def mock_calculate_performance():
            return poor_performance
        
        # Monkey patch the method for this test
        original_method = self.optimizer.metrics.calculate_performance_snapshot
        self.optimizer.metrics.calculate_performance_snapshot = mock_calculate_performance

        # Run optimization
        result = await self.optimizer.optimize_parameters(
            current_parameters=current_parameters,
            market_conditions=market_conditions,
            force_optimization=True  # Force for testing
        )

        assert isinstance(result, ParameterOptimizationResult)
        
        # Should succeed and make some parameter changes due to poor performance
        assert result.success is True
        # Should have some parameter changes
        assert len(result.parameters_changed) > 0
        
        # Restore original method
        self.optimizer.metrics.calculate_performance_snapshot = original_method
        assert result.confidence_score >= 0.0
    
    @pytest.mark.asyncio
    async def test_optimization_insufficient_data(self):
        """Test optimization with insufficient data."""
        # Add minimal trade data
        for i in range(5):  # Below minimum threshold
            trade_data = {
                'timestamp': datetime.now(),
                'pnl': 10.0,
                'commission': 1.0,
                'net_pnl': 9.0
            }
            self.optimizer.add_trade_data(trade_data)
        
        current_parameters = {
            "momentum_threshold": 0.015,
            "position_size": 0.05
        }
        
        result = await self.optimizer.optimize_parameters(
            current_parameters=current_parameters,
            market_conditions={}
        )
        
        assert result.success is True
        assert len(result.parameters_changed) == 0
        assert "No optimization needed" in result.optimization_reason
    
    @pytest.mark.asyncio
    async def test_optimization_disabled(self):
        """Test optimization when disabled."""
        disabled_config = AdaptationConfig(
            adaptation_mode=AdaptationMode.DISABLED
        )
        
        disabled_optimizer = RealTimeParameterOptimizer(
            strategy_id="test_strategy",
            template_id="professional_momentum_v1",
            adaptation_config=disabled_config
        )
        
        result = await disabled_optimizer.optimize_parameters(
            current_parameters={"momentum_threshold": 0.015},
            market_conditions={}
        )
        
        assert result.success is True
        assert len(result.parameters_changed) == 0
    
    def test_adaptation_history_tracking(self):
        """Test tracking of optimization history."""
        initial_count = len(self.optimizer.get_optimization_history())
        
        # Simulate adding optimization result
        fake_result = ParameterOptimizationResult(
            success=True,
            parameters_changed={"momentum_threshold": 0.018},
            validation_result=ValidationResult(valid=True),
            optimization_reason="Test",
            confidence_score=0.8,
            expected_improvement=0.1
        )
        
        self.optimizer.optimization_history.append(fake_result)
        
        history = self.optimizer.get_optimization_history()
        assert len(history) == initial_count + 1
        assert history[-1].parameters_changed == {"momentum_threshold": 0.018}


class TestPhase3Integration:
    """Test integration between all Phase 3 components."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_adaptation_flow(self):
        """Test complete adaptation flow from trigger to rollback."""
        # Setup optimizer with realistic configuration
        config = AdaptationConfig(
            adaptation_mode=AdaptationMode.MODERATE,
            triggers=AdaptationTriggers(
                min_sharpe_ratio=1.0,
                max_drawdown_threshold=0.15,
                min_trades_for_adaptation=20
            )
        )
        
        optimizer = RealTimeParameterOptimizer(
            strategy_id="integration_test",
            template_id="professional_momentum_v1",
            adaptation_config=config
        )
        
        # Add sufficient trade data with poor performance
        for i in range(30):
            trade_data = {
                'timestamp': datetime.now() - timedelta(hours=i),
                'symbol': 'AAPL',
                'pnl': -50.0 if i % 2 == 0 else 20.0,  # Net negative
                'commission': 5.0,
                'net_pnl': -55.0 if i % 2 == 0 else 15.0,
                'position_closed': True,
                'position_value': 10000.0
            }
            optimizer.add_trade_data(trade_data)
        
        # Current parameters
        current_parameters = {
            "lookback_period": 20,
            "momentum_threshold": 0.015,
            "confidence_threshold": 0.75,
            "volume_lookback": 10,
            "volume_threshold": 1.5,
            "position_size": 0.05,
            "stop_loss_pct": 0.03,
            "take_profit_pct": 0.08
        }
        
        # Run optimization
        result = await optimizer.optimize_parameters(
            current_parameters=current_parameters,
            market_conditions={"volatility": 0.3, "correlation": 0.2},
            force_optimization=True
        )
        
        # Verify optimization occurred
        assert result.success is True
        assert result.snapshot_id is not None
        
        # Test rollback monitoring
        if result.snapshot_id:
            rollback_needed = await optimizer.monitor_adaptation_performance(
                result.snapshot_id
            )
            # May or may not need rollback depending on implementation
            assert isinstance(rollback_needed, bool)
    
    def test_component_integration_consistency(self):
        """Test that all components work together consistently."""
        strategy_id = "integration_test"
        template_id = "professional_momentum_v1"
        
        # Create all components
        metrics = AdaptationMetrics(strategy_id)
        validator = ParameterValidator(template_id)
        rollback_manager = AdaptationRollbackManager(strategy_id)
        
        # Test that they reference the same strategy/template
        assert metrics.strategy_id == strategy_id
        assert validator.template_id == template_id
        assert rollback_manager.strategy_id == strategy_id
        
        # Test parameter validation consistency
        test_params = {
            "momentum_threshold": 0.02,
            "confidence_threshold": 0.8,
            "position_size": 0.04
        }
        
        validation_result = validator.validate_parameter_set(test_params)
        assert validation_result.valid is True
        
        # All components should work with the same parameter structure
        assert all(param in validator.parameter_bounds for param in test_params.keys())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
