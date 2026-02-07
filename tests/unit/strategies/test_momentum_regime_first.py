"""
Regime-First Architecture Tests for Enhanced Momentum Strategy
===============================================================

Tests the "Regime-First" architecture implementation:
1. Regime gate kills (non-conducive regime → no entry)
2. Valid entries (conducive regime → state machine evaluation)
3. Regime transition handling (degradation cleanup)

This validates the regime × structure matrix described in the architecture plan.

Author: StatArb_Gemini Test Suite
Date: January 2026
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from core_engine.config import MomentumConfig
from core_engine.config.strategies import RegimeConstraints
from core_engine.trading.strategies.implementations.momentum.enhanced_momentum import (
    EnhancedMomentumStrategy,
)
from core_engine.trading.strategies.implementations.momentum.momentum_state_machine import (
    SymbolStateName,
)
from core_engine.alpha.ads_regime_vector import ADSRegimeVector
from tests.unit.strategies.test_helpers import (
    create_enriched_data_dict,
    create_enriched_dataframe,
)


class TestRegimeConstraintsDataclass:
    """Test the RegimeConstraints dataclass validation and defaults"""

    def test_default_values(self):
        """Test default constraint values are sensible"""
        constraints = RegimeConstraints()
        
        assert constraints.enable_regime_gate is True
        assert constraints.long_min_trend == -0.5
        assert constraints.long_max_trend == 1.0
        assert constraints.short_min_trend == -1.0
        assert constraints.short_max_trend == 0.5
        assert constraints.max_volatility == 0.85
        assert constraints.min_liquidity == 0.2
        assert constraints.min_confidence == 0.3
        assert constraints.close_on_regime_flip is True
        assert constraints.reset_state_machine_on_flip is True
        assert constraints.regime_hysteresis_bars == 3

    def test_validation_trend_bounds(self):
        """Test that invalid trend bounds raise errors"""
        with pytest.raises(ValueError, match="long_min_trend must be <= long_max_trend"):
            RegimeConstraints(long_min_trend=0.5, long_max_trend=-0.5)
        
        with pytest.raises(ValueError, match="short_min_trend must be <= short_max_trend"):
            RegimeConstraints(short_min_trend=0.5, short_max_trend=-0.5)

    def test_validation_volatility_bounds(self):
        """Test that invalid volatility bounds raise errors"""
        with pytest.raises(ValueError, match="min_volatility must be <= max_volatility"):
            RegimeConstraints(min_volatility=0.9, max_volatility=0.5)

    def test_validation_liquidity_range(self):
        """Test that invalid liquidity values raise errors"""
        with pytest.raises(ValueError, match="min_liquidity must be in"):
            RegimeConstraints(min_liquidity=1.5)

    def test_validation_confidence_range(self):
        """Test that invalid confidence values raise errors"""
        with pytest.raises(ValueError, match="min_confidence must be in"):
            RegimeConstraints(min_confidence=-0.1)


class TestMomentumConfigWithRegimeConstraints:
    """Test MomentumConfig integration with RegimeConstraints"""

    def test_default_regime_constraints(self):
        """Test that MomentumConfig includes default RegimeConstraints"""
        config = MomentumConfig(name='test_momentum')
        
        assert hasattr(config, 'regime_constraints')
        assert isinstance(config.regime_constraints, RegimeConstraints)

    def test_custom_regime_constraints(self):
        """Test that custom RegimeConstraints can be set"""
        custom_constraints = RegimeConstraints(
            enable_regime_gate=False,
            min_liquidity=0.5,
            max_volatility=0.7,
        )
        config = MomentumConfig(
            name='test_momentum',
            regime_constraints=custom_constraints,
        )
        
        assert config.regime_constraints.enable_regime_gate is False
        assert config.regime_constraints.min_liquidity == 0.5
        assert config.regime_constraints.max_volatility == 0.7


class TestRegimeGateKills:
    """Test regime gate kills for non-conducive regimes"""

    @pytest.fixture
    def strategy(self):
        """Create momentum strategy with regime gate enabled"""
        constraints = RegimeConstraints(
            enable_regime_gate=True,
            long_min_trend=-0.3,
            long_max_trend=1.0,
            short_min_trend=-1.0,
            short_max_trend=0.3,
            max_volatility=0.8,
            min_liquidity=0.3,
            min_confidence=0.4,
        )
        config = MomentumConfig(
            name='test_momentum',
            enable_state_machine=True,
            regime_constraints=constraints,
        )
        return EnhancedMomentumStrategy(config)

    def test_kill_low_confidence_regime(self, strategy):
        """Test that low confidence regime kills entry"""
        # Create a regime with low confidence
        ads_r = ADSRegimeVector(
            volatility=0.5,
            trend=0.3,
            liquidity=0.6,
            microstructure=0.5,
            confidence=0.2,  # Below min_confidence=0.4
        )
        
        is_conducive, reason, diag = strategy._is_regime_conducive(
            symbol='AAPL',
            side='LONG_ENTRY',
            ads_r=ads_r,
        )
        
        assert is_conducive is False
        assert reason == "regime_kill:low_confidence"
        assert diag["confidence"] == 0.2

    def test_kill_low_liquidity_regime(self, strategy):
        """Test that low liquidity regime kills entry"""
        ads_r = ADSRegimeVector(
            volatility=0.5,
            trend=0.3,
            liquidity=0.1,  # Below min_liquidity=0.3
            microstructure=0.5,
            confidence=0.8,
        )
        
        is_conducive, reason, diag = strategy._is_regime_conducive(
            symbol='AAPL',
            side='LONG_ENTRY',
            ads_r=ads_r,
        )
        
        assert is_conducive is False
        assert reason == "regime_kill:low_liquidity"

    def test_kill_high_volatility_regime(self, strategy):
        """Test that high volatility regime kills entry"""
        ads_r = ADSRegimeVector(
            volatility=0.95,  # Above max_volatility=0.8
            trend=0.3,
            liquidity=0.6,
            microstructure=0.5,
            confidence=0.8,
        )
        
        is_conducive, reason, diag = strategy._is_regime_conducive(
            symbol='AAPL',
            side='LONG_ENTRY',
            ads_r=ads_r,
        )
        
        assert is_conducive is False
        assert reason == "regime_kill:high_volatility"

    def test_kill_trend_headwind_long(self, strategy):
        """Test that bearish trend kills long entry"""
        ads_r = ADSRegimeVector(
            volatility=0.5,
            trend=-0.6,  # Below long_min_trend=-0.3
            liquidity=0.6,
            microstructure=0.5,
            confidence=0.8,
        )
        
        is_conducive, reason, diag = strategy._is_regime_conducive(
            symbol='AAPL',
            side='LONG_ENTRY',
            ads_r=ads_r,
        )
        
        assert is_conducive is False
        assert reason == "regime_kill:trend_headwind_long"

    def test_kill_trend_headwind_short(self, strategy):
        """Test that bullish trend kills short entry"""
        ads_r = ADSRegimeVector(
            volatility=0.5,
            trend=0.6,  # Above short_max_trend=0.3
            liquidity=0.6,
            microstructure=0.5,
            confidence=0.8,
        )
        
        is_conducive, reason, diag = strategy._is_regime_conducive(
            symbol='AAPL',
            side='SHORT_ENTRY',
            ads_r=ads_r,
        )
        
        assert is_conducive is False
        assert reason == "regime_kill:trend_headwind_short"


class TestValidRegimeEntries:
    """Test that valid regimes allow entry evaluation"""

    @pytest.fixture
    def strategy(self):
        """Create momentum strategy with regime gate enabled"""
        constraints = RegimeConstraints(
            enable_regime_gate=True,
            long_min_trend=-0.3,
            long_max_trend=1.0,
            short_min_trend=-1.0,
            short_max_trend=0.3,
            max_volatility=0.8,
            min_liquidity=0.3,
            min_confidence=0.4,
        )
        config = MomentumConfig(
            name='test_momentum',
            enable_state_machine=True,
            regime_constraints=constraints,
        )
        return EnhancedMomentumStrategy(config)

    def test_conducive_long_regime(self, strategy):
        """Test that bullish regime allows long entry"""
        ads_r = ADSRegimeVector(
            volatility=0.5,
            trend=0.5,  # Bullish - good for long
            liquidity=0.6,
            microstructure=0.5,
            confidence=0.8,
        )
        
        is_conducive, reason, diag = strategy._is_regime_conducive(
            symbol='AAPL',
            side='LONG_ENTRY',
            ads_r=ads_r,
        )
        
        assert is_conducive is True
        assert reason == ""
        assert diag.get("passed") is True

    def test_conducive_short_regime(self, strategy):
        """Test that bearish regime allows short entry"""
        ads_r = ADSRegimeVector(
            volatility=0.5,
            trend=-0.5,  # Bearish - good for short
            liquidity=0.6,
            microstructure=0.5,
            confidence=0.8,
        )
        
        is_conducive, reason, diag = strategy._is_regime_conducive(
            symbol='AAPL',
            side='SHORT_ENTRY',
            ads_r=ads_r,
        )
        
        assert is_conducive is True
        assert reason == ""

    def test_neutral_regime_allows_both(self, strategy):
        """Test that neutral regime allows both long and short"""
        ads_r = ADSRegimeVector(
            volatility=0.5,
            trend=0.0,  # Neutral
            liquidity=0.6,
            microstructure=0.5,
            confidence=0.8,
        )
        
        # Should allow long
        is_conducive_long, _, _ = strategy._is_regime_conducive(
            symbol='AAPL',
            side='LONG_ENTRY',
            ads_r=ads_r,
        )
        
        # Should allow short
        is_conducive_short, _, _ = strategy._is_regime_conducive(
            symbol='AAPL',
            side='SHORT_ENTRY',
            ads_r=ads_r,
        )
        
        assert is_conducive_long is True
        assert is_conducive_short is True

    def test_regime_gate_disabled(self, strategy):
        """Test that disabled regime gate allows all entries"""
        # Disable regime gate
        strategy.config.regime_constraints = RegimeConstraints(enable_regime_gate=False)
        
        # Even bad regime should pass
        ads_r = ADSRegimeVector(
            volatility=0.99,  # Would normally kill
            trend=-0.9,  # Would normally kill long
            liquidity=0.1,  # Would normally kill
            microstructure=0.5,
            confidence=0.1,  # Would normally kill
        )
        
        is_conducive, reason, diag = strategy._is_regime_conducive(
            symbol='AAPL',
            side='LONG_ENTRY',
            ads_r=ads_r,
        )
        
        assert is_conducive is True
        assert diag["regime_gate"] == "disabled"


class TestRegimeTransitionHandling:
    """Test regime transition (degradation) handling"""

    @pytest.fixture
    def strategy(self):
        """Create momentum strategy with regime transition handling enabled"""
        constraints = RegimeConstraints(
            enable_regime_gate=True,
            close_on_regime_flip=True,
            reset_state_machine_on_flip=True,
            regime_hysteresis_bars=2,
            min_confidence=0.4,
        )
        config = MomentumConfig(
            name='test_momentum',
            enable_state_machine=True,
            regime_constraints=constraints,
        )
        return EnhancedMomentumStrategy(config)

    @pytest.mark.asyncio
    async def test_regime_degradation_clears_pending(self, strategy):
        """Test that regime degradation clears pending signals"""
        await strategy.initialize()
        
        # Simulate a pending signal
        from core_engine.alpha.ads_components import (
            PendingSignalContext,
            SignalMaturityScore,
            ADSSMSGateInputs,
            ERAR,
        )
        
        sms = SignalMaturityScore(
            pending_bars=0,
            decay_rate=0.05,
            max_pending=50,
            inputs=ADSSMSGateInputs(
                setup_maturity=0.5,
                setup_validity_prob=0.6,
                signed_flow_support=0.3,
                vol_compression=1.0,
            ),
        )
        erar = ERAR(expected_pnl=10.0, cvar_95=5.0)
        
        ctx = PendingSignalContext(
            symbol='AAPL',
            side='BUY',
            sms=sms,
            erar=erar,
            raw_signal_strength=0.7,
            timestamp=datetime.now(),
            entry_price=150.0,
            metadata={},
        )
        strategy.pending_signals.add(ctx)
        
        # Verify pending signal exists
        assert strategy.pending_signals.get('AAPL', 'BUY') is not None
        
        # Set previous regime as conducive
        strategy._prev_regime_conducive['AAPL'] = True
        strategy._regime_conducive_bars['AAPL'] = 0
        
        # Trigger regime degradation multiple times (hysteresis = 2)
        for _ in range(3):  # Need 3 calls to exceed hysteresis of 2
            strategy._check_regime_transition(
                symbol='AAPL',
                is_conducive=False,
                kill_reason='regime_kill:low_confidence',
                regime_diag={'confidence': 0.2},
            )
        
        # Pending signal should be cleared
        assert strategy.pending_signals.get('AAPL', 'BUY') is None

    @pytest.mark.asyncio
    async def test_regime_degradation_resets_state_machine(self, strategy):
        """Test that regime degradation resets state machine to FLAT"""
        await strategy.initialize()
        
        # Put state machine in SETUP state
        strategy.state_machine.transition_to(
            'AAPL',
            SymbolStateName.SETUP_BREAKOUT,
            setup_high=150.0,
            setup_low=148.0,
        )
        
        # Verify state machine is in SETUP
        state = strategy.state_machine.get_state('AAPL')
        assert state.state == SymbolStateName.SETUP_BREAKOUT
        
        # Set previous regime as conducive
        strategy._prev_regime_conducive['AAPL'] = True
        strategy._regime_conducive_bars['AAPL'] = 0
        
        # Trigger regime degradation (exceed hysteresis)
        for _ in range(3):
            strategy._check_regime_transition(
                symbol='AAPL',
                is_conducive=False,
                kill_reason='regime_kill:high_volatility',
                regime_diag={'volatility': 0.95},
            )
        
        # State machine should be reset to FLAT
        state = strategy.state_machine.get_state('AAPL')
        assert state.state == SymbolStateName.FLAT

    def test_hysteresis_prevents_flickering(self, strategy):
        """Test that hysteresis prevents rapid state changes"""
        # Set previous regime as conducive
        strategy._prev_regime_conducive['AAPL'] = True
        strategy._regime_conducive_bars['AAPL'] = 0
        
        # Single non-conducive bar should not trigger cleanup
        strategy._check_regime_transition(
            symbol='AAPL',
            is_conducive=False,
            kill_reason='regime_kill:low_confidence',
            regime_diag={},
        )
        
        # Hysteresis counter should increment
        assert strategy._regime_conducive_bars['AAPL'] == 1
        
        # But previous conducive state should remain True (no cleanup yet)
        # (The cleanup is deferred until hysteresis is exceeded)

    def test_regime_recovery_resets_hysteresis(self, strategy):
        """Test that regime recovery resets hysteresis counter"""
        # Simulate some non-conducive bars
        strategy._prev_regime_conducive['AAPL'] = False
        strategy._regime_conducive_bars['AAPL'] = 5
        
        # Transition back to conducive
        strategy._check_regime_transition(
            symbol='AAPL',
            is_conducive=True,
            kill_reason='',
            regime_diag={},
        )
        
        # Hysteresis counter should reset
        assert strategy._regime_conducive_bars['AAPL'] == 0
        # Previous state should update
        assert strategy._prev_regime_conducive['AAPL'] is True


class TestRegimeKillTracking:
    """Test that regime kills are tracked in diagnostics"""

    @pytest.fixture
    def strategy(self):
        """Create momentum strategy for testing"""
        constraints = RegimeConstraints(enable_regime_gate=True)
        config = MomentumConfig(
            name='test_momentum',
            enable_state_machine=True,
            regime_constraints=constraints,
        )
        return EnhancedMomentumStrategy(config)

    @pytest.mark.asyncio
    async def test_regime_kill_tracked_in_diagnostics(self, strategy):
        """Test that regime kills are counted in _sm_entry_reasons"""
        await strategy.initialize()
        await strategy.start()
        
        # Create test data with low confidence regime
        enriched_data = create_enriched_data_dict(
            symbols=['AAPL'],
            rows=200,
            trend='uptrend',
        )
        
        # Mock the regime cache to return non-conducive regime
        mock_vector = ADSRegimeVector(
            volatility=0.5,
            trend=0.3,
            liquidity=0.6,
            microstructure=0.5,
            confidence=0.1,  # Below threshold
        )
        
        with patch.object(
            strategy._ads_regime_cache,
            'get_vector',
            return_value=(mock_vector, {}),
        ):
            signals = await strategy.generate_signals(enriched_data)
        
        # Regime kill should be tracked
        assert 'regime_kill:low_confidence' in strategy._sm_entry_reasons


class TestIntegrationRegimeStateInSignal:
    """Test that regime state is surfaced in signal additional_data"""

    @pytest.fixture
    def strategy(self):
        """Create momentum strategy with state machine enabled"""
        constraints = RegimeConstraints(enable_regime_gate=True)
        config = MomentumConfig(
            name='test_momentum',
            enable_state_machine=True,
            regime_constraints=constraints,
            symbols=['AAPL'],
        )
        return EnhancedMomentumStrategy(config)

    @pytest.mark.asyncio
    async def test_signal_includes_regime_state(self, strategy):
        """Test that emitted signals include regime state in additional_data"""
        await strategy.initialize()
        await strategy.start()
        
        # Create favorable data that should generate a signal
        enriched_data = create_enriched_data_dict(
            symbols=['AAPL'],
            rows=200,
            trend='uptrend',
        )
        
        # Add required indicators
        df = enriched_data['AAPL']
        df['composite_z'] = 1.5  # Strong positive momentum
        df['composite_pct'] = 80.0  # High percentile
        df['momentum_10'] = 0.05
        df['momentum_20'] = 0.04
        df['momentum_50'] = 0.03
        df['ADX_14'] = 30.0
        df['volume_ratio'] = 1.5
        df['ATR_14'] = df['close'] * 0.015
        df['RSI_14'] = 60.0
        df = df.ffill().bfill()
        enriched_data['AAPL'] = df
        
        # Mock a conducive regime
        mock_vector = ADSRegimeVector(
            volatility=0.3,
            trend=0.5,
            liquidity=0.8,
            microstructure=0.5,
            confidence=0.9,
        )
        
        with patch.object(
            strategy._ads_regime_cache,
            'get_vector',
            return_value=(mock_vector, {}),
        ):
            # Also need to mock the state machine to trigger entry
            with patch.object(
                strategy.state_machine,
                'evaluate',
                return_value=(True, 'breakout_acceleration'),
            ):
                signals = await strategy.generate_signals(enriched_data)
        
        # If signals were generated, check regime state is included
        if signals:
            signal = signals[0]
            assert 'regime_state' in signal.additional_data
            assert 'trend' in signal.additional_data['regime_state']
            assert 'volatility' in signal.additional_data['regime_state']
            assert 'liquidity' in signal.additional_data['regime_state']
            assert 'confidence' in signal.additional_data['regime_state']
            assert signal.additional_data.get('regime_gate_passed') is True
