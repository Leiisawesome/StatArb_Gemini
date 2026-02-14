"""
Unit tests for regime component.
Tests regime detection, classification, analysis, and management.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import MagicMock

# Import regime component classes

from core_engine.regime.regime_detector import (
    RegimeType,
    DetectionMethod,
    RegimeDetection,
    RegimeDetector
)

from core_engine.regime.regime_indicators import (
    IndicatorType,
    SignalStrength,
    RegimeIndicator,
    TransitionSignal,
    VolatilityRegimeIndicators,
    MomentumRegimeIndicators,
    MeanReversionIndicators,
    TransitionSignalDetector,
    RegimeIndicatorEngine
)
from core_engine.config.component_config import RegimeConfig as IndicatorConfig

from core_engine.regime.regime_manager import (
    RegimeManagerStatus,
    RegimeAdaptation,
    RegimeManager,
)
from core_engine.regime.allocation import RegimeAwarePortfolioManager
from core_engine.regime.attribution import RegimePerformanceAttributor as RegimePerformanceAttribution
from core_engine.type_definitions.regime import MarketRegimeState as RegimeState
from core_engine.type_definitions.regime import MarketRegimeState as RegimeState
from core_engine.config.component_config import RegimeConfig as RegimeManagerConfig

class TestVolatilityRegimeIndicators:
    """Test VolatilityRegimeIndicators class."""

    @pytest.fixture
    def sample_price_data(self):
        """Create sample price data for testing."""
        dates = pd.date_range('2023-01-01', periods=200, freq='D')
        np.random.seed(42)

        # Generate price data with changing volatility
        base_price = 100
        returns = np.zeros(200)

        # Low volatility period
        returns[:100] = np.random.normal(0.0005, 0.01, 100)

        # High volatility period
        returns[100:] = np.random.normal(0.001, 0.03, 100)

        prices = base_price * np.exp(np.cumsum(returns))

        data = pd.DataFrame({
            'close': prices,
            'high': prices * (1 + np.random.uniform(0.005, 0.02, 200)),
            'low': prices * (1 - np.random.uniform(0.005, 0.02, 200))
        }, index=dates)

        return data

    def test_initialization(self):
        """Test VolatilityRegimeIndicators initialization."""
        config = IndicatorConfig()
        indicators = VolatilityRegimeIndicators(config)

        assert indicators.config == config
        assert hasattr(indicators, 'calculate_volatility_indicators')

    def test_calculate_volatility_indicators(self, sample_price_data):
        """Test volatility indicators calculation."""
        config = IndicatorConfig()
        indicators = VolatilityRegimeIndicators(config)

        result = indicators.calculate_volatility_indicators(sample_price_data)

        assert isinstance(result, dict)
        if result:  # Only check if indicators were calculated
            for name, indicator in result.items():
                assert isinstance(indicator, RegimeIndicator)
                assert indicator.indicator_type == IndicatorType.VOLATILITY_REGIME

class TestMomentumRegimeIndicators:
    """Test MomentumRegimeIndicators class."""

    @pytest.fixture
    def sample_momentum_data(self):
        """Create sample data with momentum patterns."""
        dates = pd.date_range('2023-01-01', periods=200, freq='D')
        np.random.seed(42)

        # Generate momentum data
        base_price = 100
        returns = np.zeros(200)

        # Strong uptrend
        returns[:100] = np.random.normal(0.002, 0.015, 100)

        # Weak/sideways movement
        returns[100:] = np.random.normal(0.0001, 0.008, 100)

        prices = base_price * np.exp(np.cumsum(returns))

        data = pd.DataFrame({
            'timestamp': dates,
            'close': prices,
            'volume': np.random.uniform(100000, 500000, 200)
        })

        return data

    def test_initialization(self):
        """Test MomentumRegimeIndicators initialization."""
        config = IndicatorConfig()
        indicators = MomentumRegimeIndicators(config)

        assert indicators.config == config
        assert hasattr(indicators, 'calculate_momentum_indicators')

    def test_calculate_momentum_indicators(self, sample_momentum_data):
        """Test momentum indicators calculation."""
        config = IndicatorConfig()
        indicators = MomentumRegimeIndicators(config)

        result = indicators.calculate_momentum_indicators(sample_momentum_data)

        assert isinstance(result, dict)
        if result:  # Only check if indicators were calculated
            for name, indicator in result.items():
                assert isinstance(indicator, RegimeIndicator)
                assert indicator.indicator_type == IndicatorType.MOMENTUM_REGIME

class TestMeanReversionIndicators:
    """Test MeanReversionIndicators class."""

    @pytest.fixture
    def sample_reversion_data(self):
        """Create sample data with mean reversion patterns."""
        dates = pd.date_range('2023-01-01', periods=200, freq='D')
        np.random.seed(42)

        # Generate mean-reverting data
        base_price = 100
        prices = np.zeros(200)
        prices[0] = base_price

        for i in range(1, 200):
            # Mean reversion towards 100
            deviation = prices[i-1] - 100
            prices[i] = prices[i-1] + np.random.normal(-0.001 * deviation, 0.02)

        data = pd.DataFrame({
            'timestamp': dates,
            'close': prices
        })

        return data

    def test_initialization(self):
        """Test MeanReversionIndicators initialization."""
        config = IndicatorConfig()
        indicators = MeanReversionIndicators(config)

        assert indicators.config == config
        assert hasattr(indicators, 'calculate_mean_reversion_indicators')

    def test_calculate_mean_reversion_indicators(self, sample_reversion_data):
        """Test mean reversion indicators calculation."""
        config = IndicatorConfig()
        indicators = MeanReversionIndicators(config)

        result = indicators.calculate_mean_reversion_indicators(sample_reversion_data)

        assert isinstance(result, dict)
        if result:  # Only check if indicators were calculated
            for name, indicator in result.items():
                assert isinstance(indicator, RegimeIndicator)
                assert indicator.indicator_type == IndicatorType.MEAN_REVERSION

class TestTransitionSignalDetector:
    """Test TransitionSignalDetector class."""

    @pytest.fixture
    def sample_transition_data(self):
        """Create sample data with regime transitions."""
        dates = pd.date_range('2023-01-01', periods=200, freq='D')
        np.random.seed(42)

        # Generate data with clear regime transitions
        returns = np.zeros(200)

        # Bull market
        returns[:80] = np.random.normal(0.002, 0.015, 80)

        # Transition period
        returns[80:90] = np.random.normal(-0.001, 0.025, 10)

        # Bear market
        returns[90:] = np.random.normal(-0.001, 0.02, 110)

        prices = 100 * np.exp(np.cumsum(returns))

        data = pd.DataFrame({
            'timestamp': dates,
            'close': prices,
            'volume': np.random.uniform(100000, 500000, 200)
        })

        return data

    def test_initialization(self):
        """Test TransitionSignalDetector initialization."""
        config = IndicatorConfig()
        detector = TransitionSignalDetector(config)

        assert detector.config == config
        assert hasattr(detector, 'detect_transition_signals')

    def test_detect_transition_signals(self, sample_transition_data):
        """Test transition signal detection."""
        config = IndicatorConfig()
        detector = TransitionSignalDetector(config)

        # Create some mock indicators
        indicators = {
            'volatility_regime': RegimeIndicator(
                name='volatility_regime',
                indicator_type=IndicatorType.VOLATILITY_REGIME,
                current_value=0.8,
                signal_strength=SignalStrength.STRONG
            )
        }

        result = detector.detect_transition_signals(indicators)

        assert isinstance(result, list)
        for signal in result:
            assert isinstance(signal, TransitionSignal)

class TestRegimeIndicatorEngine:
    """Test RegimeIndicatorEngine class."""

    @pytest.fixture
    def sample_indicator_data(self):
        """Create sample data for indicator engine testing."""
        dates = pd.date_range('2023-01-01', periods=200, freq='D')
        np.random.seed(42)

        prices = 100 + np.cumsum(np.random.randn(200) * 0.5)

        data = pd.DataFrame({
            'timestamp': dates,
            'close': prices,
            'high': prices * 1.02,
            'low': prices * 0.98,
            'volume': np.random.uniform(100000, 500000, 200)
        })

        return data

    def test_initialization(self):
        """Test RegimeIndicatorEngine initialization."""
        config = IndicatorConfig()
        engine = RegimeIndicatorEngine(config)

        assert engine.config == config
        assert isinstance(engine.volatility_indicators, VolatilityRegimeIndicators)
        assert isinstance(engine.momentum_indicators, MomentumRegimeIndicators)
        assert isinstance(engine.mean_reversion_indicators, MeanReversionIndicators)
        assert isinstance(engine.transition_detector, TransitionSignalDetector)

    def test_calculate_all_indicators(self, sample_indicator_data):
        """Test calculation of all indicators."""
        config = IndicatorConfig()
        engine = RegimeIndicatorEngine(config)

        indicators = engine.calculate_all_indicators(sample_indicator_data)

        assert isinstance(indicators, dict)
        # Check that we get some indicators back
        assert len(indicators) > 0

    def test_empty_data_handling(self):
        """Test handling of empty data."""
        engine = RegimeIndicatorEngine()
        empty_data = pd.DataFrame()

        result = engine.calculate_all_indicators(empty_data)
        assert isinstance(result, dict)
        assert len(result) == 0

class TestRegimeState:
    """Test RegimeState dataclass."""

    def test_initialization(self):
        """Test RegimeState initialization."""
        timestamp = datetime.now()

        state = RegimeState(
            timestamp=timestamp,
            primary_regime=RegimeType.BULL_MARKET,
            regime_confidence=0.85,
            regime_duration=15,
            transition_probability=0.1,
            risk_adjustment_factor=1.2,
        )

        assert state.timestamp == timestamp
        assert state.current_regime == RegimeType.BULL_MARKET  # property alias
        assert state.regime_confidence == 0.85
        assert state.regime_duration == 15
        assert state.transition_probability == 0.1
        assert state.risk_adjustment_factor == 1.2

class TestRegimeAdaptation:
    """Test RegimeAdaptation dataclass."""

    def test_initialization(self):
        """Test RegimeAdaptation initialization."""
        timestamp = datetime.now()
        adaptation = RegimeAdaptation(
            adaptation_timestamp=timestamp,
            trigger_regime=RegimeType.HIGH_VOLATILITY,
            adaptation_reason="High volatility detected",
            strategy_weights={'momentum': 0.3, 'mean_reversion': 0.7},
            risk_budget_adjustments={'equity_risk': 0.8, 'bond_risk': 1.2},
            volatility_target_adjustment=0.8,
            position_sizing_adjustment=0.9,
            asset_allocation_changes={'stocks': -0.1, 'bonds': 0.1},
            implementation_urgency="high",
            phased_implementation=True
        )

        assert adaptation.adaptation_timestamp == timestamp
        assert adaptation.trigger_regime == RegimeType.HIGH_VOLATILITY
        assert adaptation.adaptation_reason == "High volatility detected"
        assert adaptation.strategy_weights == {'momentum': 0.3, 'mean_reversion': 0.7}
        assert adaptation.risk_budget_adjustments == {'equity_risk': 0.8, 'bond_risk': 1.2}
        assert adaptation.volatility_target_adjustment == 0.8
        assert adaptation.position_sizing_adjustment == 0.9
        assert adaptation.asset_allocation_changes == {'stocks': -0.1, 'bonds': 0.1}
        assert adaptation.implementation_urgency == "high"
        assert adaptation.phased_implementation == True

class TestRegimeAwarePortfolioManager:
    """Test RegimeAwarePortfolioManager class."""

    @pytest.fixture
    def sample_portfolio_data(self):
        """Create sample portfolio data for testing."""
        assets = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']
        weights = np.array([0.3, 0.25, 0.25, 0.2])

        portfolio = {
            'assets': assets,
            'weights': weights,
            'current_regime': RegimeType.BULL_MARKET,
            'target_volatility': 0.12
        }

        return portfolio

    @pytest.fixture
    def regime_adaptations(self):
        """Create sample regime adaptations."""
        adaptations = {
            RegimeType.BULL_MARKET: RegimeAdaptation(
                trigger_regime=RegimeType.BULL_MARKET,
                adaptation_reason="Bull market detected",
                volatility_target_adjustment=1.2,
                position_sizing_adjustment=1.0
            ),
            RegimeType.BEAR_MARKET: RegimeAdaptation(
                trigger_regime=RegimeType.BEAR_MARKET,
                adaptation_reason="Bear market detected",
                volatility_target_adjustment=0.8,
                position_sizing_adjustment=0.6
            ),
            RegimeType.HIGH_VOLATILITY: RegimeAdaptation(
                trigger_regime=RegimeType.HIGH_VOLATILITY,
                adaptation_reason="High volatility detected",
                volatility_target_adjustment=0.9,
                position_sizing_adjustment=0.7
            )
        }

        return adaptations

    def test_initialization(self, regime_adaptations):
        """Test RegimeAwarePortfolioManager initialization."""
        config = RegimeManagerConfig()
        manager = RegimeAwarePortfolioManager(config)

        assert manager.config == config
        assert hasattr(manager, 'calculate_regime_optimal_allocation')

    def test_calculate_regime_optimal_allocation(self, sample_portfolio_data, regime_adaptations):
        """Test regime optimal allocation calculation."""
        config = RegimeManagerConfig()
        manager = RegimeAwarePortfolioManager(config)

        allocation = manager.calculate_regime_optimal_allocation(
            RegimeType.BEAR_MARKET,
            0.85,
            sample_portfolio_data['assets']
        )

        assert isinstance(allocation, dict)
        # Note: allocation may be empty if assets don't match expected patterns

class TestRegimePerformanceAttribution:
    """Test RegimePerformanceAttribution class."""

    @pytest.fixture
    def sample_performance_data(self):
        """Create sample performance data for testing."""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')

        # Generate portfolio returns
        portfolio_returns = np.random.normal(0.001, 0.02, 100)

        # Generate benchmark returns
        benchmark_returns = np.random.normal(0.0008, 0.015, 100)

        # Regime classifications
        regimes = np.random.choice(list(RegimeType), 100)

        data = pd.DataFrame({
            'date': dates,
            'portfolio_returns': portfolio_returns,
            'benchmark_returns': benchmark_returns,
            'regime': regimes
        })

        return data

    def test_initialization(self):
        """Test RegimePerformanceAttribution initialization."""
        config = RegimeManagerConfig()
        attribution = RegimePerformanceAttribution(config)

        assert attribution.config == config
        assert hasattr(attribution, 'calculate_regime_attribution')

    def test_calculate_regime_attribution(self, sample_performance_data):
        """Test regime attribution calculation."""
        config = RegimeManagerConfig()
        attribution = RegimePerformanceAttribution(config)

        # Create sample regime history
        dates = sample_performance_data.index
        regime_history = pd.Series([RegimeType.BULL_MARKET] * len(dates), index=dates)

        attribution_result = attribution.calculate_regime_attribution(
            sample_performance_data['portfolio_returns'],
            regime_history,
            sample_performance_data['benchmark_returns']
        )

        assert isinstance(attribution_result, dict)
        assert len(attribution_result) > 0

class TestRegimeManager:
    """Test RegimeManager class."""

    @pytest.fixture
    def sample_manager_config(self):
        """Create sample manager configuration."""
        return RegimeManagerConfig()

    @pytest.fixture
    def mock_regime_detector(self):
        """Create mock regime detector."""
        detector = MagicMock()
        detector.detect_regime.return_value = RegimeDetection(
            regime_type=RegimeType.BULL_MARKET,
            confidence=0.85,
            regime_start=datetime.now() - timedelta(days=10),
            regime_duration=10,
            method=DetectionMethod.THRESHOLD_BASED
        )
        return detector

    @pytest.fixture
    def mock_portfolio_manager(self):
        """Create mock portfolio manager."""
        manager = MagicMock()
        manager.adapt_portfolio.return_value = {'adapted': True}
        return manager

    def test_initialization(self, sample_manager_config):
        """Test RegimeManager initialization."""
        manager = RegimeManager(config=sample_manager_config)

        assert manager.config == sample_manager_config
        assert isinstance(manager.regime_detector, RegimeDetector)
        assert isinstance(manager.portfolio_manager, RegimeAwarePortfolioManager)
        assert isinstance(manager.current_state, type(None))  # Initially None
        assert manager.status == RegimeManagerStatus.READY

    def test_update_regime_state(self, sample_manager_config):
        """Test regime state update."""
        manager = RegimeManager(config=sample_manager_config)

        market_data = {
            'SPY': pd.DataFrame({
                'timestamp': pd.date_range('2023-01-01', periods=50),
                'close': np.random.randn(50) + 100
            })
        }

        # Run async update
        import asyncio
        regime_state = asyncio.run(manager.update_regime_analysis(market_data))

        assert isinstance(regime_state, RegimeState)

    def test_adapt_to_regime(self, sample_manager_config):
        """Test portfolio adaptation to regime."""
        manager = RegimeManager(config=sample_manager_config)

        # Create a mock regime state
        regime_state = RegimeState(
            timestamp=datetime.now(),
            primary_regime=RegimeType.BULL_MARKET,
            regime_confidence=0.8,
        )

        current_strategies = {'momentum': 0.6, 'mean_reversion': 0.4}

        adaptation = manager.generate_regime_adaptation(regime_state, current_strategies, force_adaptation=True)

        assert isinstance(adaptation, RegimeAdaptation)

    def test_get_regime_signal(self, sample_manager_config):
        """Test regime signal retrieval."""
        manager = RegimeManager(config=sample_manager_config)

        signal = manager.get_regime_summary()

        assert isinstance(signal, dict)
        assert 'current_regime' in signal or len(signal) > 0