#!/usr/bin/env python3
"""
Test Suite for IRegimeAware Implementation in Core Pipeline
===========================================================

Tests the regime adaptation behavior of:
- EnhancedTechnicalIndicators
- EnhancedFeatureEngineer
- EnhancedSignalGenerator

Validates Rule 2 (Hierarchical Architecture with Regime-First) compliance.

Author: StatArb_Gemini Test Suite
Version: 1.0.0
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import Mock, AsyncMock
from dataclasses import dataclass

# Import components
from core_engine.processing.indicators.engine import EnhancedTechnicalIndicators
from core_engine.processing.features.engineer import EnhancedFeatureEngineer
from core_engine.processing.signals.generator import EnhancedSignalGenerator

# Mock RegimeContext
@dataclass
class MockRegimeContext:
    """Mock regime context for testing"""
    primary_regime: Mock = None
    regime_confidence: float = 0.8
    volatility_regime: str = "normal_volatility"
    regime_start_time: datetime = None

    def __post_init__(self):
        if self.primary_regime is None:
            self.primary_regime = Mock(value="normal_volatility")
        if self.regime_start_time is None:
            self.regime_start_time = datetime.now()


class TestIRegimeAwareCompliance:
    """Test IRegimeAware interface compliance"""

    @pytest.fixture
    def mock_regime_engine(self):
        """Create mock regime engine"""
        engine = Mock()
        engine.get_current_regime = AsyncMock(return_value=MockRegimeContext())
        return engine

    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for testing"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
        data = pd.DataFrame({
            'timestamp': dates,
            'open': np.random.uniform(100, 110, 100),
            'high': np.random.uniform(110, 115, 100),
            'low': np.random.uniform(95, 100, 100),
            'close': np.random.uniform(100, 110, 100),
            'volume': np.random.uniform(1000000, 5000000, 100)
        })
        return data

    # ========================================
    # EnhancedTechnicalIndicators Tests
    # ========================================

    def test_indicators_implements_iregime_aware(self):
        """Test that EnhancedTechnicalIndicators implements IRegimeAware"""
        indicators = EnhancedTechnicalIndicators()

        # Check interface methods exist
        assert hasattr(indicators, 'set_regime_engine')
        assert hasattr(indicators, 'on_regime_change')
        assert hasattr(indicators, 'get_current_regime_context')
        assert hasattr(indicators, 'adapt_to_regime')
        assert hasattr(indicators, 'validate_regime_dependency')

    def test_indicators_set_regime_engine(self, mock_regime_engine):
        """Test regime engine injection"""
        indicators = EnhancedTechnicalIndicators()
        indicators.set_regime_engine(mock_regime_engine)

        assert indicators.regime_engine is mock_regime_engine
        assert indicators.validate_regime_dependency() is True

    @pytest.mark.asyncio
    async def test_indicators_regime_adaptation_high_vol(self, mock_regime_engine):
        """Test indicator adaptation to high volatility regime"""
        indicators = EnhancedTechnicalIndicators()
        indicators.set_regime_engine(mock_regime_engine)

        # Create high volatility regime context
        high_vol_regime = MockRegimeContext(
            primary_regime=Mock(value="high_volatility"),
            volatility_regime="high_volatility"
        )

        # Trigger regime change
        await indicators.on_regime_change(high_vol_regime)

        # Verify adaptations
        assert indicators.get_current_regime_context() == high_vol_regime
        assert indicators.config.bb_std == 2.5  # Wider bands
        assert indicators.config.bb_period == 25  # Longer period

    @pytest.mark.asyncio
    async def test_indicators_regime_adaptation_low_vol(self, mock_regime_engine):
        """Test indicator adaptation to low volatility regime"""
        indicators = EnhancedTechnicalIndicators()
        indicators.set_regime_engine(mock_regime_engine)

        # Create low volatility regime context
        low_vol_regime = MockRegimeContext(
            primary_regime=Mock(value="low_volatility"),
            volatility_regime="low_volatility"
        )

        # Trigger regime change
        await indicators.on_regime_change(low_vol_regime)

        # Verify adaptations
        assert indicators.config.bb_std == 1.5  # Tighter bands
        assert indicators.config.bb_period == 15  # Shorter period

    # ========================================
    # EnhancedFeatureEngineer Tests
    # ========================================

    def test_features_implements_iregime_aware(self):
        """Test that EnhancedFeatureEngineer implements IRegimeAware"""
        engineer = EnhancedFeatureEngineer()

        # Check interface methods exist
        assert hasattr(engineer, 'set_regime_engine')
        assert hasattr(engineer, 'on_regime_change')
        assert hasattr(engineer, 'get_current_regime_context')
        assert hasattr(engineer, 'adapt_to_regime')
        assert hasattr(engineer, 'validate_regime_dependency')

    def test_features_set_regime_engine(self, mock_regime_engine):
        """Test regime engine injection"""
        engineer = EnhancedFeatureEngineer()
        engineer.set_regime_engine(mock_regime_engine)

        assert engineer.regime_engine is mock_regime_engine
        assert engineer.validate_regime_dependency() is True

    @pytest.mark.asyncio
    async def test_features_regime_adaptation_high_vol(self, mock_regime_engine):
        """Test feature engineering adaptation to high volatility"""
        engineer = EnhancedFeatureEngineer()
        engineer.set_regime_engine(mock_regime_engine)

        # Create high volatility regime context
        high_vol_regime = MockRegimeContext(
            primary_regime=Mock(value="high_volatility"),
            volatility_regime="high_volatility"
        )

        # Trigger regime change
        await engineer.on_regime_change(high_vol_regime)

        # Verify adaptations
        assert engineer.config.normalization_method == 'robust'  # More robust
        assert engineer.config.lookback_periods == [10, 20, 40]  # Longer periods

    @pytest.mark.asyncio
    async def test_features_regime_adaptation_low_vol(self, mock_regime_engine):
        """Test feature engineering adaptation to low volatility"""
        engineer = EnhancedFeatureEngineer()
        engineer.set_regime_engine(mock_regime_engine)

        # Create low volatility regime context
        low_vol_regime = MockRegimeContext(
            primary_regime=Mock(value="low_volatility"),
            volatility_regime="low_volatility"
        )

        # Trigger regime change
        await engineer.on_regime_change(low_vol_regime)

        # Verify adaptations
        assert engineer.config.normalization_method == 'standard'  # Standard scaling
        assert engineer.config.lookback_periods == [5, 10, 20]  # Shorter periods

    # ========================================
    # EnhancedSignalGenerator Tests
    # ========================================

    def test_signals_implements_iregime_aware(self):
        """Test that EnhancedSignalGenerator implements IRegimeAware"""
        generator = EnhancedSignalGenerator()

        # Check interface methods exist
        assert hasattr(generator, 'set_regime_engine')
        assert hasattr(generator, 'on_regime_change')
        assert hasattr(generator, 'get_current_regime_context')
        assert hasattr(generator, 'adapt_to_regime')
        assert hasattr(generator, 'validate_regime_dependency')

    def test_signals_set_regime_engine(self, mock_regime_engine):
        """Test regime engine injection"""
        generator = EnhancedSignalGenerator()
        generator.set_regime_engine(mock_regime_engine)

        assert generator.regime_engine is mock_regime_engine
        assert generator.validate_regime_dependency() is True

    @pytest.mark.asyncio
    async def test_signals_regime_adaptation_high_vol(self, mock_regime_engine):
        """Test signal generation adaptation to high volatility"""
        generator = EnhancedSignalGenerator()
        generator.set_regime_engine(mock_regime_engine)

        # Create high volatility regime context
        high_vol_regime = MockRegimeContext(
            primary_regime=Mock(value="high_volatility"),
            volatility_regime="high_volatility"
        )

        # Trigger regime change
        await generator.on_regime_change(high_vol_regime)

        # Verify adaptations
        assert generator.config.signal_threshold == 0.5  # Higher threshold
        assert generator.config.strong_signal_threshold == 0.85  # More conservative
        assert generator.config.zscore_threshold == 2.0  # Higher z-score

    @pytest.mark.asyncio
    async def test_signals_regime_adaptation_trending(self, mock_regime_engine):
        """Test signal generation adaptation to trending regime"""
        generator = EnhancedSignalGenerator()
        generator.set_regime_engine(mock_regime_engine)

        # Create trending regime context
        trending_regime = MockRegimeContext(
            primary_regime=Mock(value="trending_bullish"),
            volatility_regime="normal_volatility"
        )

        # Trigger regime change
        await generator.on_regime_change(trending_regime)

        # Verify adaptations
        assert generator.config.momentum_weight == 0.5  # Prioritize momentum
        assert generator.config.mean_reversion_weight == 0.3

    @pytest.mark.asyncio
    async def test_signals_regime_adaptation_range_bound(self, mock_regime_engine):
        """Test signal generation adaptation to range-bound regime"""
        generator = EnhancedSignalGenerator()
        generator.set_regime_engine(mock_regime_engine)

        # Create range-bound regime context
        range_regime = MockRegimeContext(
            primary_regime=Mock(value="range_bound"),
            volatility_regime="normal_volatility"
        )

        # Trigger regime change
        await generator.on_regime_change(range_regime)

        # Verify adaptations
        assert generator.config.momentum_weight == 0.3
        assert generator.config.mean_reversion_weight == 0.5  # Prioritize mean-reversion

    # ========================================
    # Integration Tests
    # ========================================

    @pytest.mark.asyncio
    async def test_full_pipeline_regime_adaptation(self, mock_regime_engine, sample_market_data):
        """Test full pipeline regime adaptation"""
        # Initialize components
        indicators = EnhancedTechnicalIndicators()
        engineer = EnhancedFeatureEngineer()
        generator = EnhancedSignalGenerator()

        # Inject regime engine
        indicators.set_regime_engine(mock_regime_engine)
        engineer.set_regime_engine(mock_regime_engine)
        generator.set_regime_engine(mock_regime_engine)

        # Create high volatility regime
        high_vol_regime = MockRegimeContext(
            primary_regime=Mock(value="high_volatility"),
            volatility_regime="high_volatility"
        )

        # Trigger regime change across pipeline
        await indicators.on_regime_change(high_vol_regime)
        await engineer.on_regime_change(high_vol_regime)
        await generator.on_regime_change(high_vol_regime)

        # Verify all components adapted
        assert indicators.get_current_regime_context() == high_vol_regime
        assert engineer.get_current_regime_context() == high_vol_regime
        assert generator.get_current_regime_context() == high_vol_regime

        # Verify adaptations are consistent with high volatility
        assert indicators.config.bb_std == 2.5
        assert engineer.config.normalization_method == 'robust'
        assert generator.config.signal_threshold == 0.5

    @pytest.mark.asyncio
    async def test_regime_transition_sequence(self, mock_regime_engine):
        """Test regime transition from low vol to high vol"""
        generator = EnhancedSignalGenerator()
        generator.set_regime_engine(mock_regime_engine)

        # Start with low volatility
        low_vol_regime = MockRegimeContext(
            primary_regime=Mock(value="low_volatility"),
            volatility_regime="low_volatility"
        )
        await generator.on_regime_change(low_vol_regime)
        assert generator.config.signal_threshold == 0.35  # Low threshold

        # Transition to high volatility
        high_vol_regime = MockRegimeContext(
            primary_regime=Mock(value="high_volatility"),
            volatility_regime="high_volatility"
        )
        await generator.on_regime_change(high_vol_regime)
        assert generator.config.signal_threshold == 0.5  # High threshold

        # Transition back to normal
        normal_regime = MockRegimeContext(
            primary_regime=Mock(value="normal_volatility"),
            volatility_regime="normal_volatility"
        )
        await generator.on_regime_change(normal_regime)
        assert generator.config.signal_threshold == 0.4  # Normal threshold


class TestRegimeAdaptationMetrics:
    """Test regime adaptation metrics and reporting"""

    @pytest.fixture
    def mock_regime_engine(self):
        """Create mock regime engine"""
        engine = Mock()
        engine.get_current_regime = AsyncMock(return_value=MockRegimeContext())
        return engine

    @pytest.mark.asyncio
    async def test_adaptation_returns_metrics(self, mock_regime_engine):
        """Test that adapt_to_regime returns detailed metrics"""
        indicators = EnhancedTechnicalIndicators()
        indicators.set_regime_engine(mock_regime_engine)

        regime_context = MockRegimeContext(
            primary_regime=Mock(value="high_volatility"),
            volatility_regime="high_volatility"
        )

        result = await indicators.adapt_to_regime(regime_context)

        # Verify result structure
        assert 'timestamp' in result
        assert 'new_regime' in result
        assert 'adjustments' in result
        assert 'success' in result
        assert result['success'] is True
        assert len(result['adjustments']) > 0

    @pytest.mark.asyncio
    async def test_adaptation_error_handling(self, mock_regime_engine):
        """Test error handling in regime adaptation"""
        indicators = EnhancedTechnicalIndicators()
        indicators.set_regime_engine(mock_regime_engine)

        # Create invalid regime context
        invalid_regime = Mock()
        invalid_regime.primary_regime = None  # Will be handled gracefully

        result = await indicators.adapt_to_regime(invalid_regime)

        # Should handle error gracefully (no crash)
        assert 'success' in result
        assert 'new_regime' in result
        # With None primary_regime, it should default to 'unknown'
        assert result['new_regime'] == 'unknown'


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

