#!/usr/bin/env python3
"""
Comprehensive tests for Regime-Aware Signal Enhancer
====================================================

Tests all functionality of the RegimeAwareSignalEnhancer to achieve 100% coverage.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

from core_engine.processing.signals.regime_aware_enhancer import (
    RegimeAwareSignalEnhancer,
    RegimeAwareSignal,
    RegimeSignalAdjustment
)
from core_engine.type_definitions.strategy import TradingSignal


class TestRegimeSignalAdjustment:
    """Test RegimeSignalAdjustment enum"""

    def test_enum_values(self):
        """Test enum values are correct"""
        assert RegimeSignalAdjustment.AMPLIFY.value == "amplify"
        assert RegimeSignalAdjustment.REDUCE.value == "reduce"
        assert RegimeSignalAdjustment.FILTER.value == "filter"
        assert RegimeSignalAdjustment.MAINTAIN.value == "maintain"


class TestRegimeAwareSignal:
    """Test RegimeAwareSignal dataclass"""

    def test_initialization(self):
        """Test signal initialization"""
        original_signal = Mock()
        signal = RegimeAwareSignal(
            original_signal=original_signal,
            regime="trending",
            regime_confidence=0.8,
            adjustment=RegimeSignalAdjustment.AMPLIFY,
            adjusted_confidence=0.9,
            regime_compatible=True,
            adjustment_reason="Test reason"
        )

        assert signal.original_signal == original_signal
        assert signal.regime == "trending"
        assert signal.regime_confidence == 0.8
        assert signal.adjustment == RegimeSignalAdjustment.AMPLIFY
        assert signal.adjusted_confidence == 0.9
        assert signal.regime_compatible is True
        assert signal.adjustment_reason == "Test reason"


class TestRegimeAwareSignalEnhancer:
    """Test RegimeAwareSignalEnhancer class"""

    @pytest.fixture
    def enhancer(self):
        """Create enhancer instance"""
        return RegimeAwareSignalEnhancer()

    @pytest.fixture
    def mock_signal(self):
        """Create mock signal"""
        signal = Mock()
        signal.confidence = 0.7
        signal.strategy_type = "momentum"
        signal.signal_type = "BUY"
        signal.metadata = {"strategy_type": "momentum"}
        return signal

    @pytest.fixture
    def mock_regime_engine(self):
        """Create mock regime engine"""
        engine = Mock()
        engine.get_current_regime = AsyncMock()
        return engine

    def test_initialization_default(self, enhancer):
        """Test initialization with default config"""
        assert enhancer.config == {}
        assert enhancer.regime_engine is None
        assert "trending" in enhancer.regime_compatibility
        assert "ranging" in enhancer.regime_compatibility
        assert "high_volatility" in enhancer.regime_compatibility
        assert "low_volatility" in enhancer.regime_compatibility
        assert "crisis" in enhancer.regime_compatibility

    def test_initialization_custom_config(self):
        """Test initialization with custom config"""
        config = {"test_param": "test_value"}
        enhancer = RegimeAwareSignalEnhancer(config)
        assert enhancer.config == config

    def test_regime_compatibility_matrix(self, enhancer):
        """Test regime compatibility matrix is properly configured"""
        # Test trending regime
        trending_rules = enhancer.regime_compatibility["trending"]
        assert trending_rules["momentum"] == RegimeSignalAdjustment.AMPLIFY
        assert trending_rules["breakout"] == RegimeSignalAdjustment.AMPLIFY
        assert trending_rules["trend_following"] == RegimeSignalAdjustment.AMPLIFY
        assert trending_rules["mean_reversion"] == RegimeSignalAdjustment.REDUCE
        assert trending_rules["stat_arb"] == RegimeSignalAdjustment.REDUCE

        # Test ranging regime
        ranging_rules = enhancer.regime_compatibility["ranging"]
        assert ranging_rules["mean_reversion"] == RegimeSignalAdjustment.AMPLIFY
        assert ranging_rules["stat_arb"] == RegimeSignalAdjustment.AMPLIFY
        assert ranging_rules["momentum"] == RegimeSignalAdjustment.REDUCE
        assert ranging_rules["breakout"] == RegimeSignalAdjustment.FILTER

        # Test high volatility regime
        high_vol_rules = enhancer.regime_compatibility["high_volatility"]
        assert high_vol_rules["momentum"] == RegimeSignalAdjustment.REDUCE
        assert high_vol_rules["mean_reversion"] == RegimeSignalAdjustment.REDUCE
        assert high_vol_rules["all"] == RegimeSignalAdjustment.REDUCE

        # Test low volatility regime
        low_vol_rules = enhancer.regime_compatibility["low_volatility"]
        assert low_vol_rules["mean_reversion"] == RegimeSignalAdjustment.AMPLIFY
        assert low_vol_rules["momentum"] == RegimeSignalAdjustment.MAINTAIN

        # Test crisis regime
        crisis_rules = enhancer.regime_compatibility["crisis"]
        assert crisis_rules["all"] == RegimeSignalAdjustment.FILTER

    def test_adjustment_multipliers(self, enhancer):
        """Test adjustment multipliers are correct"""
        assert enhancer.adjustment_multipliers[RegimeSignalAdjustment.AMPLIFY] == 1.25
        assert enhancer.adjustment_multipliers[RegimeSignalAdjustment.REDUCE] == 0.70
        assert enhancer.adjustment_multipliers[RegimeSignalAdjustment.FILTER] == 0.0
        assert enhancer.adjustment_multipliers[RegimeSignalAdjustment.MAINTAIN] == 1.0

    def test_set_regime_engine(self, enhancer, mock_regime_engine):
        """Test setting regime engine"""
        enhancer.set_regime_engine(mock_regime_engine)
        assert enhancer.regime_engine == mock_regime_engine

    @pytest.mark.asyncio
    async def test_enhance_signals_with_regime_context(self, enhancer, mock_signal):
        """Test enhancing signals with provided regime context"""
        signals = [mock_signal]
        regime_context = {
            "regime": "trending",
            "confidence": 0.8,
            "volatility": "normal_volatility"
        }

        enhanced_signals = await enhancer.enhance_signals(signals, regime_context)

        assert len(enhanced_signals) == 1
        enhanced = enhanced_signals[0]
        assert enhanced.regime == "trending"
        assert enhanced.regime_confidence == 0.8
        assert enhanced.adjustment == RegimeSignalAdjustment.AMPLIFY
        assert enhanced.regime_compatible is True

    @pytest.mark.asyncio
    async def test_enhance_signals_with_regime_engine(self, enhancer, mock_signal, mock_regime_engine):
        """Test enhancing signals using regime engine"""
        # Mock regime analysis
        mock_regime_analysis = Mock()
        mock_regime_analysis.primary_regime.value = "ranging"
        mock_regime_analysis.confidence = 0.9
        mock_regime_analysis.volatility_regime = "low_volatility"

        mock_regime_engine.get_current_regime.return_value = mock_regime_analysis
        enhancer.set_regime_engine(mock_regime_engine)

        signals = [mock_signal]
        enhanced_signals = await enhancer.enhance_signals(signals)

        assert len(enhanced_signals) == 1
        enhanced = enhanced_signals[0]
        assert enhanced.regime == "ranging"
        assert enhanced.regime_confidence == 0.9
        assert enhanced.adjustment == RegimeSignalAdjustment.REDUCE  # momentum in ranging
        assert enhanced.regime_compatible is True

    @pytest.mark.asyncio
    async def test_enhance_signals_regime_engine_error(self, enhancer, mock_signal, mock_regime_engine):
        """Test enhancing signals when regime engine throws error"""
        mock_regime_engine.get_current_regime.side_effect = Exception("Regime engine error")
        enhancer.set_regime_engine(mock_regime_engine)

        signals = [mock_signal]
        enhanced_signals = await enhancer.enhance_signals(signals)

        assert len(enhanced_signals) == 1
        enhanced = enhanced_signals[0]
        assert enhanced.regime == "unknown"
        assert enhanced.regime_confidence == 0.5

    @pytest.mark.asyncio
    async def test_enhance_signals_no_regime_engine(self, enhancer, mock_signal):
        """Test enhancing signals without regime engine"""
        signals = [mock_signal]
        enhanced_signals = await enhancer.enhance_signals(signals)

        assert len(enhanced_signals) == 1
        enhanced = enhanced_signals[0]
        assert enhanced.regime == "unknown"
        assert enhanced.regime_confidence == 0.5

    @pytest.mark.asyncio
    async def test_enhance_signals_different_regimes(self, enhancer, mock_signal):
        """Test enhancing signals in different regimes"""
        signals = [mock_signal]

        # Test trending regime
        regime_context = {"regime": "trending", "confidence": 0.8}
        enhanced = await enhancer.enhance_signals(signals, regime_context)
        assert enhanced[0].adjustment == RegimeSignalAdjustment.AMPLIFY

        # Test ranging regime
        regime_context = {"regime": "ranging", "confidence": 0.8}
        enhanced = await enhancer.enhance_signals(signals, regime_context)
        assert enhanced[0].adjustment == RegimeSignalAdjustment.REDUCE

        # Test high volatility regime
        regime_context = {"regime": "high_volatility", "confidence": 0.8}
        enhanced = await enhancer.enhance_signals(signals, regime_context)
        assert enhanced[0].adjustment == RegimeSignalAdjustment.REDUCE

        # Test low volatility regime
        regime_context = {"regime": "low_volatility", "confidence": 0.8}
        enhanced = await enhancer.enhance_signals(signals, regime_context)
        assert enhanced[0].adjustment == RegimeSignalAdjustment.MAINTAIN

        # Test crisis regime
        regime_context = {"regime": "crisis", "confidence": 0.8}
        enhanced = await enhancer.enhance_signals(signals, regime_context)
        # Crisis regime filters out signals, so the list should be empty
        assert len(enhanced) == 0

    @pytest.mark.asyncio
    async def test_enhance_signals_confidence_calculation(self, enhancer, mock_signal):
        """Test confidence calculation with different adjustments"""
        signals = [mock_signal]

        # Test amplify adjustment
        regime_context = {"regime": "trending", "confidence": 0.8}
        enhanced = await enhancer.enhance_signals(signals, regime_context)
        expected_confidence = 0.7 * 1.25 * 0.8  # original * multiplier * regime_confidence
        assert abs(enhanced[0].adjusted_confidence - expected_confidence) < 0.001

        # Test reduce adjustment
        regime_context = {"regime": "ranging", "confidence": 0.8}
        enhanced = await enhancer.enhance_signals(signals, regime_context)
        expected_confidence = 0.7 * 0.70 * 0.8
        assert abs(enhanced[0].adjusted_confidence - expected_confidence) < 0.001

        # Test maintain adjustment
        regime_context = {"regime": "low_volatility", "confidence": 0.8}
        enhanced = await enhancer.enhance_signals(signals, regime_context)
        expected_confidence = 0.7 * 1.0 * 0.8
        assert abs(enhanced[0].adjusted_confidence - expected_confidence) < 0.001

    @pytest.mark.asyncio
    async def test_enhance_signals_confidence_cap(self, enhancer, mock_signal):
        """Test confidence is capped at 0.95"""
        # Create signal with very high confidence
        high_confidence_signal = Mock()
        high_confidence_signal.confidence = 0.9
        high_confidence_signal.strategy_type = "momentum"
        high_confidence_signal.signal_type = "BUY"
        high_confidence_signal.metadata = {"strategy_type": "momentum"}

        signals = [high_confidence_signal]
        regime_context = {"regime": "trending", "confidence": 0.9}
        enhanced = await enhancer.enhance_signals(signals, regime_context)

        # Should be capped at 0.95
        assert enhanced[0].adjusted_confidence <= 0.95

    @pytest.mark.asyncio
    async def test_enhance_signals_filtering(self, enhancer, mock_signal):
        """Test that filtered signals are removed from results"""
        signals = [mock_signal]
        regime_context = {"regime": "crisis", "confidence": 0.8}
        enhanced = await enhancer.enhance_signals(signals, regime_context)

        # Filtered signals should not be in results
        assert len(enhanced) == 0

    @pytest.mark.asyncio
    async def test_enhance_signals_error_handling(self, enhancer):
        """Test error handling in enhance_signals"""
        # Test with invalid signal
        invalid_signal = Mock()
        invalid_signal.confidence = "invalid"  # This will cause error in calculation

        signals = [invalid_signal]
        enhanced = await enhancer.enhance_signals(signals)

        # Should return wrapped signals with error handling
        assert len(enhanced) == 1
        assert enhanced[0].regime == "unknown"
        assert enhanced[0].adjustment_reason == "Enhancement failed - using original signal"

    def test_get_signal_strategy_type_from_attribute(self, enhancer):
        """Test getting strategy type from signal.strategy_type"""
        signal = Mock()
        signal.strategy_type = "momentum"

        strategy_type = enhancer._get_signal_strategy_type(signal)
        assert strategy_type == "momentum"

    def test_get_signal_strategy_type_from_metadata(self, enhancer):
        """Test getting strategy type from signal.metadata"""
        class TestSignal:
            def __init__(self):
                self.metadata = {"strategy_type": "mean_reversion"}

        signal = TestSignal()
        strategy_type = enhancer._get_signal_strategy_type(signal)
        assert strategy_type == "mean_reversion"

    def test_get_signal_strategy_type_from_signal_type(self, enhancer):
        """Test inferring strategy type from signal_type"""
        class TestSignal:
            def __init__(self, signal_type):
                self.signal_type = signal_type

        signal = TestSignal("momentum_signal")
        strategy_type = enhancer._get_signal_strategy_type(signal)
        assert strategy_type == "momentum"

        signal = TestSignal("mean_reversion_signal")
        strategy_type = enhancer._get_signal_strategy_type(signal)
        assert strategy_type == "mean_reversion"

    def test_get_signal_strategy_type_unknown(self, enhancer):
        """Test getting strategy type when unknown"""
        class TestSignal:
            def __init__(self):
                pass  # No strategy_type, metadata, or recognizable signal_type

        signal = TestSignal()
        strategy_type = enhancer._get_signal_strategy_type(signal)
        assert strategy_type == "unknown"

    def test_determine_adjustment_with_all_rule(self, enhancer):
        """Test determining adjustment when regime has 'all' rule"""
        adjustment = enhancer._determine_adjustment("high_volatility", "momentum")
        assert adjustment == RegimeSignalAdjustment.REDUCE

        adjustment = enhancer._determine_adjustment("crisis", "any_strategy")
        assert adjustment == RegimeSignalAdjustment.FILTER

    def test_determine_adjustment_with_strategy_rule(self, enhancer):
        """Test determining adjustment with strategy-specific rule"""
        adjustment = enhancer._determine_adjustment("trending", "momentum")
        assert adjustment == RegimeSignalAdjustment.AMPLIFY

        adjustment = enhancer._determine_adjustment("trending", "mean_reversion")
        assert adjustment == RegimeSignalAdjustment.REDUCE

    def test_determine_adjustment_unknown_regime(self, enhancer):
        """Test determining adjustment for unknown regime"""
        adjustment = enhancer._determine_adjustment("unknown_regime", "momentum")
        assert adjustment == RegimeSignalAdjustment.MAINTAIN

    def test_determine_adjustment_unknown_strategy(self, enhancer):
        """Test determining adjustment for unknown strategy"""
        adjustment = enhancer._determine_adjustment("trending", "unknown_strategy")
        assert adjustment == RegimeSignalAdjustment.MAINTAIN

    def test_get_enhancement_stats_empty(self, enhancer):
        """Test getting enhancement stats with empty list"""
        stats = enhancer.get_enhancement_stats([])
        assert stats == {}

    def test_get_enhancement_stats_with_signals(self, enhancer):
        """Test getting enhancement stats with signals"""
        # Create mock enhanced signals
        signals = []
        for i, adjustment in enumerate([RegimeSignalAdjustment.AMPLIFY, RegimeSignalAdjustment.REDUCE,
                                      RegimeSignalAdjustment.MAINTAIN]):
            signal = Mock()
            signal.adjustment = adjustment
            signal.regime_compatible = True
            signal.adjusted_confidence = 0.8
            signal.original_signal = Mock()
            signal.original_signal.confidence = 0.7
            signal.regime = "trending"
            signals.append(signal)

        stats = enhancer.get_enhancement_stats(signals)

        assert stats["total_signals"] == 3
        assert stats["amplified"] == 1
        assert stats["reduced"] == 1
        assert stats["maintained"] == 1
        assert stats["filtered"] == 0
        assert stats["regime"] == "trending"
        assert "avg_adjustment_factor" in stats

    def test_get_enhancement_stats_with_filtered_signals(self, enhancer):
        """Test getting enhancement stats with filtered signals"""
        signals = []
        for i in range(3):
            signal = Mock()
            signal.adjustment = RegimeSignalAdjustment.FILTER
            signal.regime_compatible = False
            signal.adjusted_confidence = 0.0
            signal.original_signal = Mock()
            signal.original_signal.confidence = 0.7
            signal.regime = "crisis"
            signals.append(signal)

        stats = enhancer.get_enhancement_stats(signals)

        assert stats["total_signals"] == 3
        assert stats["filtered"] == 3
        assert stats["regime"] == "crisis"

    @pytest.mark.asyncio
    async def test_enhance_signals_multiple_signals(self, enhancer):
        """Test enhancing multiple signals"""
        # Create multiple signals with different strategy types
        signals = []
        for strategy_type in ["momentum", "mean_reversion", "breakout"]:
            signal = Mock()
            signal.confidence = 0.7
            signal.strategy_type = strategy_type
            signal.signal_type = "BUY"
            signal.metadata = {"strategy_type": strategy_type}
            signals.append(signal)

        regime_context = {"regime": "trending", "confidence": 0.8}
        enhanced = await enhancer.enhance_signals(signals, regime_context)

        assert len(enhanced) == 3
        # All should be compatible in trending regime
        assert all(s.regime_compatible for s in enhanced)
        # Momentum and breakout should be amplified
        assert enhanced[0].adjustment == RegimeSignalAdjustment.AMPLIFY  # momentum
        assert enhanced[2].adjustment == RegimeSignalAdjustment.AMPLIFY  # breakout
        # Mean reversion should be reduced
        assert enhanced[1].adjustment == RegimeSignalAdjustment.REDUCE  # mean_reversion

    @pytest.mark.asyncio
    async def test_enhance_signals_regime_engine_hasattr_checks(self, enhancer, mock_regime_engine):
        """Test enhance_signals when regime engine returns object without expected attributes"""
        # Mock regime analysis without expected attributes
        mock_regime_analysis = Mock()
        # Don't set primary_regime, confidence, or volatility_regime attributes

        mock_regime_engine.get_current_regime.return_value = mock_regime_analysis
        enhancer.set_regime_engine(mock_regime_engine)

        signals = [Mock()]
        enhanced = await enhancer.enhance_signals(signals)

        # Should fall back to default values
        assert enhanced[0].regime == "unknown"
        assert enhanced[0].regime_confidence == 0.5

    def test_regime_compatibility_edge_cases(self, enhancer):
        """Test regime compatibility edge cases"""
        # Test unknown regime
        adjustment = enhancer._determine_adjustment("unknown", "momentum")
        assert adjustment == RegimeSignalAdjustment.MAINTAIN

        # Test empty regime rules
        adjustment = enhancer._determine_adjustment("", "momentum")
        assert adjustment == RegimeSignalAdjustment.MAINTAIN

    @pytest.mark.asyncio
    async def test_enhance_signals_empty_signal_list(self, enhancer):
        """Test enhancing empty signal list"""
        enhanced = await enhancer.enhance_signals([])
        assert enhanced == []

    def test_adjustment_reason_formatting(self, enhancer):
        """Test adjustment reason formatting"""
        class TestSignal:
            def __init__(self):
                self.strategy_type = "momentum"
                self.confidence = 0.7

        signal = TestSignal()

        # Test different regime/strategy combinations
        regime_context = {"regime": "trending", "confidence": 0.8}
        enhanced = asyncio.run(enhancer.enhance_signals([signal], regime_context))

        expected_reason = "momentum signal in trending regime → amplify"
        assert enhanced[0].adjustment_reason == expected_reason


class TestRegimeAwareSignalEnhancerIntegration:
    """Integration tests for RegimeAwareSignalEnhancer"""

    @pytest.fixture
    def real_trading_signal(self):
        """Create real TradingSignal for integration tests"""
        signal = TradingSignal(
            strategy_id="test_momentum",
            symbol="AAPL",
            signal_type="BUY",
            strength=0.8,
            price=150.0,
            quantity=100,
            metadata={"strategy_type": "momentum", "z_score": 2.5}
        )
        # Add confidence as an attribute for testing
        signal.confidence = 0.75
        return signal

    @pytest.mark.asyncio
    async def test_integration_with_real_signal(self, real_trading_signal):
        """Test integration with real TradingSignal"""
        enhancer = RegimeAwareSignalEnhancer()

        signals = [real_trading_signal]
        regime_context = {"regime": "trending", "confidence": 0.8}

        enhanced = await enhancer.enhance_signals(signals, regime_context)

        assert len(enhanced) == 1
        enhanced_signal = enhanced[0]

        # Verify original signal is preserved
        assert enhanced_signal.original_signal == real_trading_signal

        # Verify enhancement details
        assert enhanced_signal.regime == "trending"
        assert enhanced_signal.regime_confidence == 0.8
        assert enhanced_signal.adjustment == RegimeSignalAdjustment.AMPLIFY
        assert enhanced_signal.regime_compatible is True

        # Verify confidence calculation
        expected_confidence = 0.75 * 1.25 * 0.8  # original * amplify * regime_confidence
        assert abs(enhanced_signal.adjusted_confidence - expected_confidence) < 0.001

    @pytest.mark.asyncio
    async def test_integration_multiple_real_signals(self):
        """Test integration with multiple real signals"""
        enhancer = RegimeAwareSignalEnhancer()

        signals = []

        # Create AAPL signal
        aapl_signal = TradingSignal(
            strategy_id="test_momentum",
            symbol="AAPL",
            signal_type="BUY",
            strength=0.8,
            price=150.0,
            quantity=100,
            metadata={"strategy_type": "momentum"}
        )
        aapl_signal.confidence = 0.8
        signals.append(aapl_signal)

        # Create TSLA signal
        tsla_signal = TradingSignal(
            strategy_id="test_mean_reversion",
            symbol="TSLA",
            signal_type="SELL",
            strength=0.6,
            price=200.0,
            quantity=50,
            metadata={"strategy_type": "mean_reversion"}
        )
        tsla_signal.confidence = 0.6
        signals.append(tsla_signal)

        regime_context = {"regime": "ranging", "confidence": 0.9}
        enhanced = await enhancer.enhance_signals(signals, regime_context)

        assert len(enhanced) == 2

        # Momentum signal should be reduced in ranging regime
        momentum_signal = enhanced[0]
        assert momentum_signal.adjustment == RegimeSignalAdjustment.REDUCE

        # Mean reversion signal should be amplified in ranging regime
        mean_reversion_signal = enhanced[1]
        assert mean_reversion_signal.adjustment == RegimeSignalAdjustment.AMPLIFY

    @pytest.mark.asyncio
    async def test_integration_crisis_regime_filtering(self):
        """Test integration with crisis regime filtering"""
        enhancer = RegimeAwareSignalEnhancer()

        signal = TradingSignal(
            strategy_id="test_momentum",
            symbol="AAPL",
            signal_type="BUY",
            strength=0.8,
            price=150.0,
            quantity=100,
            metadata={"strategy_type": "momentum"}
        )
        signal.confidence = 0.9
        signals = [signal]

        regime_context = {"regime": "crisis", "confidence": 0.7}
        enhanced = await enhancer.enhance_signals(signals, regime_context)

        # All signals should be filtered in crisis regime
        assert len(enhanced) == 0


class TestRegimeAwareSignalEnhancerEdgeCases:
    """Test edge cases and error conditions"""

    @pytest.mark.asyncio
    async def test_signal_without_confidence_attribute(self):
        """Test signal without confidence attribute"""
        enhancer = RegimeAwareSignalEnhancer()

        class TestSignal:
            def __init__(self):
                self.strategy_type = "momentum"
                # No confidence attribute

        signal = TestSignal()
        enhanced = await enhancer.enhance_signals([signal])

        # Should use default confidence of 0.6
        assert enhanced[0].adjusted_confidence > 0

    @pytest.mark.asyncio
    async def test_signal_with_none_metadata(self):
        """Test signal with None metadata"""
        enhancer = RegimeAwareSignalEnhancer()

        class TestSignal:
            def __init__(self):
                self.confidence = 0.7
                self.metadata = None
                self.strategy_type = "momentum"

        signal = TestSignal()
        enhanced = await enhancer.enhance_signals([signal])

        # Should fall back to strategy_type attribute
        assert enhanced[0].adjustment_reason == "momentum signal in unknown regime → maintain"

    @pytest.mark.asyncio
    async def test_signal_with_empty_metadata(self):
        """Test signal with empty metadata"""
        enhancer = RegimeAwareSignalEnhancer()

        class TestSignal:
            def __init__(self):
                self.confidence = 0.7
                self.metadata = {}
                self.strategy_type = "momentum"

        signal = TestSignal()
        enhanced = await enhancer.enhance_signals([signal])

        # Should fall back to strategy_type attribute
        assert enhanced[0].adjustment_reason == "momentum signal in unknown regime → maintain"

    @pytest.mark.asyncio
    async def test_signal_without_strategy_type_attributes(self):
        """Test signal without any strategy type attributes"""
        enhancer = RegimeAwareSignalEnhancer()

        class TestSignal:
            def __init__(self):
                self.confidence = 0.7
                # Don't set any strategy type attributes

        signal = TestSignal()
        enhanced = await enhancer.enhance_signals([signal])

        # Should default to "unknown" strategy type
        assert enhanced[0].adjustment_reason == "unknown signal in unknown regime → maintain"

    def test_enhancement_stats_with_zero_confidence(self):
        """Test enhancement stats calculation with zero confidence signals"""
        enhancer = RegimeAwareSignalEnhancer()

        # Create signal with zero confidence
        signal = Mock()
        signal.adjustment = RegimeSignalAdjustment.AMPLIFY
        signal.regime_compatible = True
        signal.adjusted_confidence = 0.8
        signal.original_signal = Mock()
        signal.original_signal.confidence = 0.0  # Zero confidence
        signal.regime = "trending"

        stats = enhancer.get_enhancement_stats([signal])

        # Should handle zero confidence gracefully
        assert "avg_adjustment_factor" in stats
        assert stats["total_signals"] == 1
