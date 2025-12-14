"""
Edge Case Tests: Regime Transitions
====================================

Tests processing components under regime transition scenarios:
- Rapid regime changes
- Contradictory regime signals
- Missing regime context
- Delayed regime updates
- Extreme regime conditions

Author: StatArb_Gemini Test Suite
Version: 1.0.0 (Processing Brick Edge Cases)
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# Import processing components
from core_engine.processing.indicators.engine import EnhancedTechnicalIndicators
from core_engine.processing.features.engineer import EnhancedFeatureEngineer
from core_engine.processing.signals.generator import EnhancedSignalGenerator
from core_engine.system.interfaces import RegimeContext

class TestRegimeTransitionEdgeCases:
    """Test edge cases during regime transitions"""

    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for testing"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
        data = pd.DataFrame({
            'timestamp': dates,
            'open': 100 + np.random.randn(100).cumsum(),
            'high': 101 + np.random.randn(100).cumsum(),
            'low': 99 + np.random.randn(100).cumsum(),
            'close': 100 + np.random.randn(100).cumsum(),
            'volume': np.random.randint(1000, 10000, 100)
        })
        data['symbol'] = 'TEST'
        return data

    @pytest.fixture
    def indicators_engine(self):
        """Create indicators engine"""
        return EnhancedTechnicalIndicators()

    @pytest.fixture
    def feature_engineer(self):
        """Create feature engineer"""
        return EnhancedFeatureEngineer()

    @pytest.fixture
    def signal_generator(self):
        """Create signal generator"""
        return EnhancedSignalGenerator()

    # ============================================================================
    # Rapid Regime Changes
    # ============================================================================

    @pytest.mark.asyncio
    async def test_rapid_regime_changes(self, indicators_engine, sample_market_data):
        """Test behavior during rapid regime changes"""
        # Initialize component
        await indicators_engine.initialize()
        await indicators_engine.start()

        # Simulate rapid regime changes
        regimes = ['low_volatility', 'high_volatility', 'low_volatility', 'crisis']

        for regime in regimes:
            regime_context = RegimeContext(
                primary_regime=regime,
                regime_confidence=0.8,
                regime_start_time=datetime.now(),
                regime_duration_minutes=5.0
            )

            # Trigger regime change
            await indicators_engine.on_regime_change(regime_context)

            # Calculate indicators
            result = indicators_engine.calculate_indicators(sample_market_data)

            # Verify indicators still calculated successfully
            assert result is not None
            assert not result.empty
            assert 'sma_20' in result.columns

        # Verify component health after rapid changes
        health = await indicators_engine.health_check()
        assert health['healthy'] is True

    @pytest.mark.asyncio
    async def test_regime_change_during_calculation(self, feature_engineer, sample_market_data):
        """Test regime change occurring during feature calculation"""
        await feature_engineer.initialize()
        await feature_engineer.start()

        # Start calculation with one regime
        regime_context = RegimeContext(
            primary_regime='low_volatility',
            regime_confidence=0.8,
            regime_start_time=datetime.now(),
            regime_duration_minutes=10.0
        )
        await feature_engineer.on_regime_change(regime_context)

        # Simulate regime change mid-calculation using async callback
        async def change_regime_midway():
            new_regime = RegimeContext(
                primary_regime='high_volatility',
                regime_confidence=0.9,
                regime_start_time=datetime.now(),
                regime_duration_minutes=1.0
            )
            await feature_engineer.on_regime_change(new_regime)

        # Run feature engineering with regime change
        with patch.object(feature_engineer, 'on_regime_change', side_effect=change_regime_midway):
            features = feature_engineer.create_features(sample_market_data)

        # Verify features calculated successfully despite regime change
        assert features is not None
        assert not features.empty

    # ============================================================================
    # Contradictory Regime Signals
    # ============================================================================

    @pytest.mark.asyncio
    async def test_contradictory_regime_signals(self, signal_generator, sample_market_data):
        """Test handling of contradictory regime signals"""
        await signal_generator.initialize()
        await signal_generator.start()

        # Create contradictory regime context
        regime_context = RegimeContext(
            primary_regime='momentum',  # Suggests momentum strategy
            regime_confidence=0.5,  # But low confidence
            regime_start_time=datetime.now(),
            regime_duration_minutes=5.0,
            volatility_regime='high_volatility',  # Suggests caution
            liquidity_regime='low_liquidity'  # Suggests avoiding trades
        )

        await signal_generator.on_regime_change(regime_context)

        # Generate signals
        signals = signal_generator.generate_signals(sample_market_data)

        # Verify signals are appropriately conservative given contradictory signals
        if signals:
            for signal in signals:
                # Confidence should be moderated due to contradictory signals
                assert signal.confidence < 0.8

    # ============================================================================
    # Missing Regime Context
    # ============================================================================

    @pytest.mark.asyncio
    async def test_missing_regime_engine(self, indicators_engine, sample_market_data):
        """Test behavior when regime engine is not set"""
        await indicators_engine.initialize()
        await indicators_engine.start()

        # Don't set regime engine (regime_engine = None)
        assert indicators_engine.regime_engine is None

        # Calculate indicators without regime context
        result = indicators_engine.calculate_indicators(sample_market_data)

        # Should still work with default parameters
        assert result is not None
        assert not result.empty
        assert 'sma_20' in result.columns

    @pytest.mark.asyncio
    async def test_none_regime_context(self, feature_engineer, sample_market_data):
        """Test handling of None regime context"""
        await feature_engineer.initialize()
        await feature_engineer.start()

        # Trigger regime change with None
        await feature_engineer.on_regime_change(None)

        # Create features
        features = feature_engineer.create_features(sample_market_data)

        # Should use default normalization method
        assert features is not None
        assert not features.empty

    @pytest.mark.asyncio
    async def test_incomplete_regime_context(self, signal_generator, sample_market_data):
        """Test handling of incomplete regime context"""
        await signal_generator.initialize()
        await signal_generator.start()

        # Create incomplete regime context
        regime_context = RegimeContext(
            primary_regime='unknown',  # Unknown regime
            regime_confidence=0.0,  # Zero confidence
            regime_start_time=datetime.now(),
            regime_duration_minutes=0.0
        )

        await signal_generator.on_regime_change(regime_context)

        # Generate signals
        signals = signal_generator.generate_signals(sample_market_data)

        # Should still generate signals but with conservative confidence
        # May return empty list if confidence too low - both are valid
        assert signals is not None  # Should not crash

    # ============================================================================
    # Delayed Regime Updates
    # ============================================================================

    @pytest.mark.asyncio
    async def test_stale_regime_context(self, indicators_engine, sample_market_data):
        """Test behavior with stale regime context"""
        await indicators_engine.initialize()
        await indicators_engine.start()

        # Set regime context with old timestamp
        old_regime = RegimeContext(
            primary_regime='low_volatility',
            regime_confidence=0.8,
            regime_start_time=datetime.now() - timedelta(hours=24),
            regime_duration_minutes=1440.0  # 24 hours in minutes
        )

        await indicators_engine.on_regime_change(old_regime)

        # Calculate indicators
        result = indicators_engine.calculate_indicators(sample_market_data)

        # Should still work despite stale regime
        assert result is not None
        assert not result.empty

        # Health check should potentially flag stale regime
        health = await indicators_engine.health_check()
        # Component should still be healthy but may have warnings
        assert 'healthy' in health

    # ============================================================================
    # Extreme Regime Conditions
    # ============================================================================

    @pytest.mark.asyncio
    async def test_extreme_volatility_regime(self, signal_generator, sample_market_data):
        """Test signal generation in extreme volatility regime"""
        await signal_generator.initialize()
        await signal_generator.start()

        # Create extreme volatility regime
        extreme_regime = RegimeContext(
            primary_regime='crisis',
            regime_confidence=0.95,
            regime_start_time=datetime.now(),
            regime_duration_minutes=5.0,
            volatility_regime='extreme_volatility'
        )

        await signal_generator.on_regime_change(extreme_regime)

        # Generate signals
        signals = signal_generator.generate_signals(sample_market_data)

        # In extreme volatility, signals should be heavily filtered
        # or have very low confidence
        if signals:
            for signal in signals:
                # Confidence should be significantly reduced
                assert signal.confidence < 0.5
                # Position sizes should be smaller
                assert signal.position_size < 0.05

    @pytest.mark.asyncio
    async def test_crisis_liquidity_regime(self, feature_engineer, sample_market_data):
        """Test feature engineering in crisis liquidity regime"""
        await feature_engineer.initialize()
        await feature_engineer.start()

        # Create crisis liquidity regime
        crisis_regime = RegimeContext(
            primary_regime='choppy',
            regime_confidence=0.9,
            regime_start_time=datetime.now(),
            regime_duration_minutes=5.0,
            liquidity_regime='crisis_liquidity'
        )

        await feature_engineer.on_regime_change(crisis_regime)

        # Create features
        features = feature_engineer.create_features(sample_market_data)

        # Features should still be created
        assert features is not None
        assert not features.empty

        # But normalization might be more conservative
        # Verify no extreme values in normalized features
        normalized_cols = [col for col in features.columns if '_normalized' in col]
        if normalized_cols:
            for col in normalized_cols:
                # Check for outliers (should be minimal in crisis handling)
                assert features[col].abs().max() < 10  # No extreme outliers

    # ============================================================================
    # Regime Validation
    # ============================================================================

    @pytest.mark.asyncio
    async def test_regime_dependency_validation(self, indicators_engine):
        """Test regime dependency validation"""
        await indicators_engine.initialize()

        # Validate regime dependency before setting regime engine
        validation = indicators_engine.validate_regime_dependency()
        # Should return False or indicate missing regime engine
        assert validation in [False, None] or isinstance(validation, dict)

        # Set regime engine
        mock_regime_engine = Mock()
        indicators_engine.set_regime_engine(mock_regime_engine)

        # Validate again
        validation = indicators_engine.validate_regime_dependency()
        # Should now be valid
        assert validation is True or (isinstance(validation, dict) and validation.get('valid'))

    # ============================================================================
    # Concurrent Regime Changes
    # ============================================================================

    @pytest.mark.asyncio
    async def test_concurrent_regime_updates(self, signal_generator, sample_market_data):
        """Test concurrent regime updates from multiple sources"""
        await signal_generator.initialize()
        await signal_generator.start()

        # Simulate concurrent regime updates
        import asyncio

        async def update_regime_1():
            regime = RegimeContext(primary_regime='trending', regime_confidence=0.8, regime_start_time=datetime.now(), regime_duration_minutes=5.0)
            await signal_generator.on_regime_change(regime)

        async def update_regime_2():
            regime = RegimeContext(primary_regime='choppy', regime_confidence=0.7, regime_start_time=datetime.now(), regime_duration_minutes=5.0)
            await signal_generator.on_regime_change(regime)

        async def update_regime_3():
            regime = RegimeContext(primary_regime='sideways', regime_confidence=0.6, regime_start_time=datetime.now(), regime_duration_minutes=5.0)
            await signal_generator.on_regime_change(regime)

        # Run concurrent updates
        await asyncio.gather(
            update_regime_1(),
            update_regime_2(),
            update_regime_3()
        )

        # Generate signals after concurrent updates
        signals = signal_generator.generate_signals(sample_market_data)

        # Should handle concurrent updates gracefully
        assert signals is not None  # Should not crash

        # Verify component health
        health = await signal_generator.health_check()
        assert health['healthy'] is True

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

