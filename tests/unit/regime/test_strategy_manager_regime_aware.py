#!/usr/bin/env python3
"""
Unit Tests for StrategyManager IRegimeAware Implementation
=========================================================

Tests that StrategyManager properly implements the IRegimeAware interface
and adapts strategy behavior based on market regime changes.

Author: StatArb_Gemini Testing Team
Date: October 21, 2025
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock

# Import the component
from core_engine.trading.strategies.manager import StrategyManager

# Import interfaces
try:
    from core_engine.system.interfaces import IRegimeAware, RegimeContext
    from core_engine.type_definitions.regime import RegimeType
except ImportError:
    # Fallback for testing
    from enum import Enum
    from dataclasses import dataclass

    class RegimeType(Enum):
        TRENDING_UP = "trending_up"
        TRENDING_DOWN = "trending_down"
        RANGE_BOUND = "range_bound"
        HIGH_VOLATILITY = "high_volatility"
        LOW_VOLATILITY = "low_volatility"

    @dataclass
    class RegimeContext:
        primary_regime: RegimeType
        regime_confidence: float
        volatility_regime: str

class TestStrategyManagerIRegimeAware:
    """Test IRegimeAware interface implementation"""

    @pytest.fixture
    def strategy_manager_config(self):
        """Strategy manager configuration"""
        return {
            'max_concurrent_strategies': 5,
            'signal_generation_interval': 60,
            'min_confidence_threshold': 0.6,
            'max_strategy_allocation': 0.33,
            'enable_regime_awareness': True,
            'enable_multi_strategy_coordination': True
        }

    @pytest.fixture
    def strategy_manager(self, strategy_manager_config):
        """Create StrategyManager instance"""
        return StrategyManager(strategy_manager_config)

    @pytest.fixture
    def mock_regime_engine(self):
        """Mock regime engine"""
        engine = Mock()
        engine.get_current_regime = AsyncMock(return_value=RegimeContext(
            primary_regime=RegimeType.TRENDING_UP,
            regime_confidence=0.85,
            regime_start_time=datetime.now(),
            regime_duration_minutes=30.0,
            volatility_regime='normal_volatility'
        ))
        return engine

    @pytest.fixture
    def trending_regime_context(self):
        """Trending regime context"""
        return RegimeContext(
            primary_regime=RegimeType.TRENDING_UP,
            regime_confidence=0.85,
            regime_start_time=datetime.now(),
            regime_duration_minutes=30.0,
            volatility_regime='normal_volatility'
        )

    @pytest.fixture
    def range_bound_regime_context(self):
        """Range-bound regime context"""
        return RegimeContext(
            primary_regime=RegimeType.RANGE_BOUND,
            regime_confidence=0.75,
            regime_start_time=datetime.now(),
            regime_duration_minutes=45.0,
            volatility_regime='low_volatility'
        )

    @pytest.fixture
    def high_vol_regime_context(self):
        """High volatility regime context"""
        return RegimeContext(
            primary_regime=RegimeType.HIGH_VOLATILITY,
            regime_confidence=0.80,
            regime_start_time=datetime.now(),
            regime_duration_minutes=15.0,
            volatility_regime='high_volatility'
        )

    def test_interface_compliance(self, strategy_manager):
        """Test that StrategyManager implements IRegimeAware"""
        # Check class implements IRegimeAware
        assert isinstance(strategy_manager, IRegimeAware), \
            "StrategyManager must implement IRegimeAware interface"

        # Check all IRegimeAware methods are present
        assert hasattr(strategy_manager, 'set_regime_engine'), \
            "Missing set_regime_engine method"
        assert hasattr(strategy_manager, 'on_regime_change'), \
            "Missing on_regime_change method"
        assert hasattr(strategy_manager, 'get_current_regime_context'), \
            "Missing get_current_regime_context method"
        assert hasattr(strategy_manager, 'adapt_to_regime'), \
            "Missing adapt_to_regime method"
        assert hasattr(strategy_manager, 'validate_regime_dependency'), \
            "Missing validate_regime_dependency method"

        print("✅ StrategyManager implements all IRegimeAware methods")

    def test_set_regime_engine(self, strategy_manager, mock_regime_engine):
        """Test regime engine injection"""
        # Initially no regime engine
        assert not hasattr(strategy_manager, 'regime_engine') or strategy_manager.regime_engine is None

        # Set regime engine
        strategy_manager.set_regime_engine(mock_regime_engine)

        # Verify regime engine is set
        assert strategy_manager.regime_engine is not None
        assert strategy_manager.regime_engine == mock_regime_engine

        # Verify validation passes
        assert strategy_manager.validate_regime_dependency() is True

        print("✅ Regime engine injection works correctly")

    @pytest.mark.asyncio
    async def test_on_regime_change_trending(self, strategy_manager, trending_regime_context):
        """Test regime change handling for trending regime"""
        # Set initial regime
        strategy_manager.current_regime = None

        # Trigger regime change
        await strategy_manager.on_regime_change(trending_regime_context)

        # Verify regime was updated
        assert strategy_manager.current_regime is not None
        assert strategy_manager.current_regime == trending_regime_context

        # Verify regime context is accessible
        current = strategy_manager.get_current_regime_context()
        assert current == trending_regime_context

        print("✅ Regime change handling works for trending regime")

    @pytest.mark.asyncio
    async def test_on_regime_change_range_bound(self, strategy_manager, range_bound_regime_context):
        """Test regime change handling for range-bound regime"""
        # Trigger regime change
        await strategy_manager.on_regime_change(range_bound_regime_context)

        # Verify regime was updated
        assert strategy_manager.current_regime == range_bound_regime_context

        print("✅ Regime change handling works for range-bound regime")

    @pytest.mark.asyncio
    async def test_adapt_to_trending_regime(self, strategy_manager, trending_regime_context):
        """Test strategy adaptation to trending regime"""
        # Adapt to trending regime
        result = await strategy_manager.adapt_to_regime(trending_regime_context)

        # Verify adaptation succeeded
        assert result['success'] is True
        assert result['new_regime'] == 'trending_up'
        assert len(result['adjustments']) > 0

        # Verify trending-specific adaptations
        adjustments = result['adjustments']
        trending_adjustment = next((a for a in adjustments if 'strategy_preferences' in a), None)
        assert trending_adjustment is not None
        assert 'momentum' in trending_adjustment['strategy_preferences']

        print("✅ Trending regime adaptation works correctly")

    @pytest.mark.asyncio
    async def test_adapt_to_range_bound_regime(self, strategy_manager, range_bound_regime_context):
        """Test strategy adaptation to range-bound regime"""
        # Adapt to range-bound regime
        result = await strategy_manager.adapt_to_regime(range_bound_regime_context)

        # Verify adaptation succeeded
        assert result['success'] is True
        assert result['new_regime'] == 'range_bound'

        # Verify range-bound-specific adaptations
        adjustments = result['adjustments']
        range_adjustment = next((a for a in adjustments if 'strategy_preferences' in a), None)
        assert range_adjustment is not None
        assert 'mean_reversion' in range_adjustment['strategy_preferences']

        # Verify risk parameters adjusted for low volatility
        risk_adjustment = next((a for a in adjustments if a.get('reason') == 'low_volatility'), None)
        assert risk_adjustment is not None
        assert risk_adjustment['min_confidence'] < 0.6  # More aggressive

        print("✅ Range-bound regime adaptation works correctly")

    @pytest.mark.asyncio
    async def test_adapt_to_high_volatility_regime(self, strategy_manager, high_vol_regime_context):
        """Test strategy adaptation to high volatility regime"""
        # Adapt to high volatility regime
        result = await strategy_manager.adapt_to_regime(high_vol_regime_context)

        # Verify adaptation succeeded
        assert result['success'] is True

        # Verify high volatility risk adjustments
        adjustments = result['adjustments']
        risk_adjustment = next((a for a in adjustments if a.get('reason') == 'high_volatility'), None)
        assert risk_adjustment is not None
        assert risk_adjustment['min_confidence'] > 0.6  # More conservative
        assert risk_adjustment['max_allocation'] < 0.33  # More conservative

        # Verify config was updated
        assert strategy_manager.config.min_confidence_threshold == 0.7
        assert strategy_manager.config.max_strategy_allocation == 0.25

        print("✅ High volatility regime adaptation works correctly")

    @pytest.mark.asyncio
    async def test_regime_transition_sequence(self, strategy_manager, trending_regime_context,
                                             range_bound_regime_context, high_vol_regime_context):
        """Test sequence of regime transitions"""
        # Transition 1: None -> Trending
        await strategy_manager.on_regime_change(trending_regime_context)
        assert strategy_manager.current_regime == trending_regime_context

        # Transition 2: Trending -> Range-bound
        await strategy_manager.on_regime_change(range_bound_regime_context)
        assert strategy_manager.current_regime == range_bound_regime_context

        # Transition 3: Range-bound -> High Volatility
        await strategy_manager.on_regime_change(high_vol_regime_context)
        assert strategy_manager.current_regime == high_vol_regime_context

        # Verify final state reflects high volatility adaptations
        assert strategy_manager.config.min_confidence_threshold == 0.7
        assert strategy_manager.config.max_strategy_allocation == 0.25

        print("✅ Regime transition sequence works correctly")

    def test_validate_regime_dependency_no_engine(self, strategy_manager):
        """Test regime dependency validation without engine"""
        # Remove regime engine if present
        if hasattr(strategy_manager, 'regime_engine'):
            strategy_manager.regime_engine = None

        # Validation should fail
        assert strategy_manager.validate_regime_dependency() is False

        print("✅ Regime dependency validation detects missing engine")

    def test_validate_regime_dependency_with_engine(self, strategy_manager, mock_regime_engine):
        """Test regime dependency validation with engine"""
        # Set regime engine
        strategy_manager.set_regime_engine(mock_regime_engine)

        # Validation should pass
        assert strategy_manager.validate_regime_dependency() is True

        print("✅ Regime dependency validation passes with engine")

    def test_get_current_regime_context_none(self, strategy_manager):
        """Test getting regime context when none is set"""
        # Initially no regime context
        if hasattr(strategy_manager, 'current_regime'):
            strategy_manager.current_regime = None

        # Should return None
        context = strategy_manager.get_current_regime_context()
        assert context is None

        print("✅ Returns None when no regime context is set")

    @pytest.mark.asyncio
    async def test_get_current_regime_context_after_change(self, strategy_manager, trending_regime_context):
        """Test getting regime context after regime change"""
        # Set regime
        await strategy_manager.on_regime_change(trending_regime_context)

        # Get current context
        context = strategy_manager.get_current_regime_context()

        # Verify context matches
        assert context is not None
        assert context == trending_regime_context
        assert context.primary_regime == RegimeType.TRENDING_UP

        print("✅ Returns correct regime context after change")

    @pytest.mark.asyncio
    async def test_adaptation_metrics(self, strategy_manager, trending_regime_context):
        """Test adaptation returns proper metrics"""
        # Perform adaptation
        result = await strategy_manager.adapt_to_regime(trending_regime_context)

        # Verify metrics structure
        assert 'timestamp' in result
        assert 'previous_regime' in result
        assert 'new_regime' in result
        assert 'adjustments' in result
        assert 'success' in result

        # Verify timestamp is recent
        timestamp = datetime.fromisoformat(result['timestamp'])
        time_diff = (datetime.now() - timestamp).total_seconds()
        assert time_diff < 5, "Timestamp should be recent"

        print("✅ Adaptation metrics are properly structured")

class TestStrategyManagerRegimeIntegration:
    """Test full integration with regime engine"""

    @pytest.fixture
    def strategy_manager(self):
        """Create strategy manager"""
        config = {
            'enable_regime_awareness': True,
            'enable_multi_strategy_coordination': True
        }
        return StrategyManager(config)

    @pytest.fixture
    def mock_regime_engine_with_callbacks(self):
        """Mock regime engine that supports callbacks"""
        engine = Mock()
        engine.callbacks = []

        async def register_callback(callback):
            engine.callbacks.append(callback)

        async def trigger_regime_change(regime_context):
            for callback in engine.callbacks:
                await callback(regime_context)

        engine.register_callback = AsyncMock(side_effect=register_callback)
        engine.trigger_regime_change = AsyncMock(side_effect=trigger_regime_change)

        return engine

    @pytest.mark.asyncio
    async def test_full_regime_integration(self, strategy_manager, mock_regime_engine_with_callbacks):
        """Test full integration: engine injection -> callback registration -> regime change"""
        # Step 1: Inject regime engine
        strategy_manager.set_regime_engine(mock_regime_engine_with_callbacks)

        # Step 2: Validate dependency
        assert strategy_manager.validate_regime_dependency() is True

        # Step 3: Simulate regime change from engine
        new_regime = RegimeContext(
            primary_regime=RegimeType.TRENDING_UP,
            regime_confidence=0.85,
            regime_start_time=datetime.now(),
            regime_duration_minutes=30.0,
            volatility_regime='normal_volatility'
        )

        await strategy_manager.on_regime_change(new_regime)

        # Step 4: Verify adaptation occurred
        current = strategy_manager.get_current_regime_context()
        assert current is not None
        assert current.primary_regime == RegimeType.TRENDING_UP

        print("✅ Full regime integration works end-to-end")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

