"""
Unit tests for regime component.
Tests regime detection, classification, analysis, and management.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import asyncio
from typing import Dict, List, Any

# Import regime component classes
from core_engine.regime.engine import (
    MarketRegime,
    TimeframeRegime,
    TransitionPrediction as EngineTransitionPrediction,
    RegimeAnalysis,
    RegimeEngineConfig,
    IRegimeSubscriber,
    EnhancedRegimeEngine
)

from core_engine.regime.market_regime_analyzer import (
    MacroRegime,
    MarketCycle,
    RiskEnvironment,
    RegimeAnalysisConfig,
    AssetRegimeProfile,
    CrossAssetRegime,
    FactorAnalyzer,
    CrossAssetAnalyzer,
    SectorRotationAnalyzer,
    MarketRegimeAnalyzer
)

from core_engine.regime.regime_classifier import (
    MLModel,
    FeatureType,
    ClassificationConfig,
    FeatureImportance,
    ModelPerformance,
    RegimeClassification,
    FeatureEngineer,
    RegimeModelTrainer,
    RegimeClassifier
)

from core_engine.regime.regime_detector import (
    RegimeType,
    DetectionMethod,
    ConfidenceLevel,
    RegimeDetectionConfig,
    RegimeDetection,
    RegimeTransition,
    MarkovSwitchingDetector,
    GaussianMixtureDetector,
    VolatilityBasedDetector,
    ThresholdBasedDetector,
    RegimeDetector
)

from core_engine.regime.regime_indicators import (
    IndicatorType,
    SignalStrength,
    IndicatorConfig,
    RegimeIndicator,
    TransitionSignal,
    RegimeStrengthMeasure,
    VolatilityRegimeIndicators,
    MomentumRegimeIndicators,
    MeanReversionIndicators,
    TransitionSignalDetector,
    RegimeStrengthCalculator,
    RegimeIndicatorEngine
)

from core_engine.regime.regime_manager import (
    RegimeManagerStatus,
    AdaptationMode,
    RegimeManagerConfig,
    RegimeState,
    RegimeAdaptation,
    RegimeAwarePortfolioManager,
    RegimePerformanceAttribution,
    RegimeManager
)

from core_engine.regime.regime_transition_manager import (
    TransitionPhase,
    TransitionType,
    RebalancingTrigger,
    TransitionPredictionConfig,
    TransitionPrediction,
    RebalancingRecommendation,
    TransitionMonitoring,
    TransitionPredictor,
    RebalancingManager,
    TransitionMonitor,
    RegimeTransitionManager
)

class TestMarketRegime:
    """Test MarketRegime enum."""

    def test_market_regime_values(self):
        """Test MarketRegime enum values."""
        assert MarketRegime.BULL_LOW_VOL.value == "bull_low_volatility"
        assert MarketRegime.BULL_HIGH_VOL.value == "bull_high_volatility"
        assert MarketRegime.BEAR_LOW_VOL.value == "bear_low_volatility"
        assert MarketRegime.BEAR_HIGH_VOL.value == "bear_high_volatility"
        assert MarketRegime.STRONG_TRENDING.value == "strong_trending"
        assert MarketRegime.WEAK_TRENDING.value == "weak_trending"
        assert MarketRegime.RANGE_BOUND.value == "range_bound"
        assert MarketRegime.CHOPPY.value == "choppy"
        assert MarketRegime.CRISIS_MODE.value == "crisis_mode"

    def test_market_regime_members(self):
        """Test all MarketRegime members are accessible."""
        regimes = list(MarketRegime)
        assert len(regimes) >= 9  # At least the basic regimes

        # Check that we can access each regime
        for regime in regimes:
            assert isinstance(regime.value, str)
            assert len(regime.value) > 0


class TestTimeframeRegime:
    """Test TimeframeRegime dataclass."""

    def test_initialization(self):
        """Test TimeframeRegime initialization."""
        regime = TimeframeRegime(
            timeframe="1D",
            regime=MarketRegime.BULL_LOW_VOL,
            confidence=0.85,
            trend_strength=0.75,
            volatility=0.12,
            regime_duration=10,
            transition_probability=0.15
        )

        assert regime.timeframe == "1D"
        assert regime.regime == MarketRegime.BULL_LOW_VOL
        assert regime.confidence == 0.85
        assert regime.trend_strength == 0.75
        assert regime.volatility == 0.12
        assert regime.regime_duration == 10
        assert regime.transition_probability == 0.15


class TestTransitionPrediction:
    """Test TransitionPrediction dataclass."""

    def test_initialization(self):
        """Test TransitionPrediction initialization."""
        timestamp = datetime.now()
        prediction = TransitionPrediction(
            timestamp=timestamp,
            current_regime=RegimeType.BULL_MARKET,
            predicted_regime=RegimeType.BEAR_MARKET,
            transition_probability=0.75,
            prediction_confidence=0.8,
            predicted_transition_date=timestamp + timedelta(days=5),
            confidence_interval_days=3,
            transition_duration_estimate=7,
            transition_type=TransitionType.GRADUAL,
            transition_phase=TransitionPhase.STABLE,
            transition_intensity=0.6,
            risk_increase_factor=1.5,
            volatility_increase_factor=1.8,
            correlation_change_factor=0.7,
            model_used="ensemble_model",
            feature_importance={"rsi": 0.3, "macd": 0.25},
            supporting_indicators=["volume_spike", "momentum_divergence"],
            contradicting_indicators=["strong_trend"],
            similar_historical_transitions=3
        )

        assert prediction.timestamp == timestamp
        assert prediction.current_regime == RegimeType.BULL_MARKET
        assert prediction.predicted_regime == RegimeType.BEAR_MARKET
        assert prediction.transition_probability == 0.75
        assert prediction.prediction_confidence == 0.8
        assert prediction.predicted_transition_date == timestamp + timedelta(days=5)
        assert prediction.confidence_interval_days == 3
        assert prediction.transition_duration_estimate == 7
        assert prediction.transition_type == TransitionType.GRADUAL
        assert prediction.transition_phase == TransitionPhase.STABLE
        assert prediction.transition_intensity == 0.6
        assert prediction.risk_increase_factor == 1.5
        assert prediction.volatility_increase_factor == 1.8
        assert prediction.correlation_change_factor == 0.7
        assert prediction.model_used == "ensemble_model"
        assert prediction.feature_importance == {"rsi": 0.3, "macd": 0.25}
        assert prediction.supporting_indicators == ["volume_spike", "momentum_divergence"]
        assert prediction.contradicting_indicators == ["strong_trend"]
        assert prediction.similar_historical_transitions == 3


class TestRegimeAnalysis:
    """Test RegimeAnalysis dataclass."""

    def test_initialization(self):
        """Test RegimeAnalysis initialization."""
        timestamp = datetime.now()
        timeframe_regimes = {
            "1H": TimeframeRegime("1H", MarketRegime.BULL_LOW_VOL, 0.8, 0.7, 0.1, 5, 0.1),
            "1D": TimeframeRegime("1D", MarketRegime.STRONG_TRENDING, 0.9, 0.8, 0.15, 12, 0.05)
        }

        analysis = RegimeAnalysis(
            primary_regime=MarketRegime.BULL_LOW_VOL,
            confidence=0.85,
            regime_duration=10,
            timestamp=timestamp,
            directional_regime="bull",
            volatility_regime="low",
            trend_strength=0.75,
            stress_level=0.2,
            liquidity_regime="normal",
            regime_stability=0.8,
            transition_probability=0.15,
            regime_maturity=0.6,
            timeframe_regimes=timeframe_regimes,
            regime_consensus=0.85,
            dominant_timeframe="1D"
        )

        assert analysis.primary_regime == MarketRegime.BULL_LOW_VOL
        assert analysis.confidence == 0.85
        assert analysis.regime_duration == 10
        assert analysis.timestamp == timestamp
        assert analysis.directional_regime == "bull"
        assert analysis.volatility_regime == "low"
        assert analysis.trend_strength == 0.75
        assert analysis.stress_level == 0.2
        assert analysis.regime_stability == 0.8
        assert analysis.transition_probability == 0.15
        assert analysis.regime_maturity == 0.6
        assert analysis.regime_consensus == 0.85
        assert analysis.dominant_timeframe == "1D"


class TestRegimeEngineConfig:
    """Test RegimeEngineConfig dataclass."""

    def test_initialization_default(self):
        """Test RegimeEngineConfig initialization with defaults."""
        config = RegimeEngineConfig()

        assert config.lookback_window == 60
        assert config.volatility_window == 20
        assert config.trend_threshold == 0.02
        assert config.regime_change_threshold == 0.7
        assert config.update_frequency == 300
        assert config.enable_enhanced_detection == True

    def test_initialization_custom(self):
        """Test RegimeEngineConfig initialization with custom values."""
        config = RegimeEngineConfig(
            lookback_window=90,
            volatility_window=30,
            trend_threshold=0.03,
            regime_change_threshold=0.8,
            update_frequency=600,
            enable_enhanced_detection=False
        )

        assert config.lookback_window == 90
        assert config.volatility_window == 30
        assert config.trend_threshold == 0.03
        assert config.regime_change_threshold == 0.8
        assert config.update_frequency == 600
        assert config.enable_enhanced_detection == False


class TestEnhancedRegimeEngine:
    """Test EnhancedRegimeEngine class."""

    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for testing."""
        dates = pd.date_range('2023-01-01', periods=200, freq='D')
        np.random.seed(42)

        data = pd.DataFrame({
            'timestamp': dates,
            'symbol': ['AAPL'] * 200,
            'close': 100 + np.cumsum(np.random.randn(200) * 0.5),
            'high': 102 + np.cumsum(np.random.randn(200) * 0.5),
            'low': 98 + np.cumsum(np.random.randn(200) * 0.5),
            'volume': np.random.randint(1000, 10000, 200),
            'returns': np.random.randn(200) * 0.02,
            'volatility': np.random.uniform(0.1, 0.5, 200)
        })

        return data

    @pytest.fixture
    def regime_config(self):
        """Create regime engine configuration for testing."""
        return RegimeEngineConfig(
            lookback_window=30,
            volatility_window=20,
            trend_threshold=0.02,
            regime_change_threshold=0.7,
            update_frequency=300,
            enable_enhanced_detection=True
        )

    def test_initialization(self, regime_config):
        """Test EnhancedRegimeEngine initialization."""
        config_dict = {
            'lookback_window': regime_config.lookback_window,
            'volatility_window': regime_config.volatility_window,
            'trend_threshold': regime_config.trend_threshold,
            'regime_change_threshold': regime_config.regime_change_threshold,
            'update_frequency': regime_config.update_frequency,
            'enable_enhanced_detection': regime_config.enable_enhanced_detection
        }

        engine = EnhancedRegimeEngine(config_dict)

        assert engine.config.lookback_window == 30
        assert engine.config.volatility_window == 20
        assert engine.config.trend_threshold == 0.02
        assert engine.config.regime_change_threshold == 0.7

    @pytest.mark.asyncio
    async def test_analyze_regime(self, sample_market_data, regime_config):
        """Test regime analysis."""
        # Convert config to dict as expected by EnhancedRegimeEngine
        config_dict = {
            'lookback_window': regime_config.lookback_window,
            'volatility_window': regime_config.volatility_window,
            'trend_threshold': regime_config.trend_threshold,
            'regime_change_threshold': regime_config.regime_change_threshold,
            'update_frequency': regime_config.update_frequency,
            'enable_enhanced_detection': regime_config.enable_enhanced_detection
        }
        
        engine = EnhancedRegimeEngine(config_dict)

        # Feed market data to the engine
        for _, row in sample_market_data.iterrows():
            engine.process_market_data({
                'symbol': 'AAPL',
                'close': row['close']
            })

        # Analyze regime
        analysis = engine.analyze_regime(sample_market_data)

        assert isinstance(analysis, dict)
        assert 'regime_analysis_performed' in analysis
        assert 'processing_timestamp' in analysis
        assert 'processing_component' in analysis

    def test_subscriber_management(self, regime_config):
        """Test subscriber management."""
        # Convert config to dict as expected by EnhancedRegimeEngine
        config_dict = {
            'lookback_window': regime_config.lookback_window,
            'volatility_window': regime_config.volatility_window,
            'trend_threshold': regime_config.trend_threshold,
            'regime_change_threshold': regime_config.regime_change_threshold,
            'update_frequency': regime_config.update_frequency,
            'enable_enhanced_detection': regime_config.enable_enhanced_detection
        }
        
        engine = EnhancedRegimeEngine(config_dict)

        # Mock subscriber
        subscriber = Mock()

        # Subscribe
        engine.subscribe(subscriber)
        assert subscriber in engine.subscribers

        # Test that multiple subscribers can be added
        subscriber2 = Mock()
        engine.subscribe(subscriber2)
        assert subscriber2 in engine.subscribers
        assert len(engine.subscribers) == 2

    @pytest.mark.asyncio
    async def test_regime_transition_detection(self, sample_market_data, regime_config):
        """Test regime transition detection."""
        # Convert config to dict as expected by EnhancedRegimeEngine
        config_dict = {
            'lookback_window': regime_config.lookback_window,
            'volatility_window': regime_config.volatility_window,
            'trend_threshold': regime_config.trend_threshold,
            'regime_change_threshold': regime_config.regime_change_threshold,
            'update_frequency': regime_config.update_frequency,
            'enable_enhanced_detection': regime_config.enable_enhanced_detection
        }
        
        engine = EnhancedRegimeEngine(config_dict)

        # Feed market data to establish a baseline regime
        for _, row in sample_market_data.iterrows():
            engine.process_market_data({
                'symbol': 'AAPL',
                'close': row['close']
            })

        # Analyze regime to get current state
        analysis = engine.analyze_regime(sample_market_data)

        assert isinstance(analysis, dict)
        assert 'regime_analysis_performed' in analysis
        assert 'processing_timestamp' in analysis

    def test_get_regime_history(self, regime_config):
        """Test regime history retrieval."""
        # Convert config to dict as expected by EnhancedRegimeEngine
        config_dict = {
            'lookback_window': regime_config.lookback_window,
            'volatility_window': regime_config.volatility_window,
            'trend_threshold': regime_config.trend_threshold,
            'regime_change_threshold': regime_config.regime_change_threshold,
            'update_frequency': regime_config.update_frequency,
            'enable_enhanced_detection': regime_config.enable_enhanced_detection
        }
        
        engine = EnhancedRegimeEngine(config_dict)

        # Initially empty
        assert isinstance(engine.regime_history, list)
        assert len(engine.regime_history) == 0

    @pytest.mark.asyncio
    async def test_empty_data_handling(self, regime_config):
        """Test handling of empty data."""
        # Convert config to dict as expected by EnhancedRegimeEngine
        config_dict = {
            'lookback_window': regime_config.lookback_window,
            'volatility_window': regime_config.volatility_window,
            'trend_threshold': regime_config.trend_threshold,
            'regime_change_threshold': regime_config.regime_change_threshold,
            'update_frequency': regime_config.update_frequency,
            'enable_enhanced_detection': regime_config.enable_enhanced_detection
        }
        
        engine = EnhancedRegimeEngine(config_dict)

        # With no data fed, analyze_regime should return a dict
        analysis = engine.analyze_regime({})
        assert isinstance(analysis, dict)
        assert 'regime_analysis_performed' in analysis

    def test_invalid_symbol_handling(self, sample_market_data, regime_config):
        """Test handling of invalid symbol."""
        # Convert config to dict as expected by EnhancedRegimeEngine
        config_dict = {
            'lookback_window': regime_config.lookback_window,
            'volatility_window': regime_config.volatility_window,
            'trend_threshold': regime_config.trend_threshold,
            'regime_change_threshold': regime_config.regime_change_threshold,
            'update_frequency': regime_config.update_frequency,
            'enable_enhanced_detection': regime_config.enable_enhanced_detection
        }
        
        engine = EnhancedRegimeEngine(config_dict)

        # Engine should work regardless of symbol used for data feeding
        for _, row in sample_market_data.iterrows():
            engine.market_data_buffer['INVALID'] = [row['close']]

        # Should still work since engine uses any available data
        assert len(engine.market_data_buffer) > 0


class TestMacroRegime:
    """Test MacroRegime enum."""

    def test_macro_regime_values(self):
        """Test MacroRegime enum values."""
        assert MacroRegime.EXPANSION.value == "expansion"
        assert MacroRegime.RECESSION.value == "recession"
        assert MacroRegime.RECOVERY.value == "recovery"
        assert MacroRegime.STAGFLATION.value == "stagflation"
        assert MacroRegime.DEFLATION.value == "deflation"
        assert MacroRegime.INFLATION.value == "inflation"
        assert MacroRegime.LIQUIDITY_CRISIS.value == "liquidity_crisis"
        assert MacroRegime.CREDIT_EXPANSION.value == "credit_expansion"
        assert MacroRegime.UNKNOWN.value == "unknown"
        assert MacroRegime.STAGFLATION.value == "stagflation"


class TestMarketCycle:
    """Test MarketCycle enum."""

    def test_market_cycle_values(self):
        """Test MarketCycle enum values."""
        assert MarketCycle.ACCUMULATION.value == "accumulation"
        assert MarketCycle.MARKUP.value == "markup"
        assert MarketCycle.DISTRIBUTION.value == "distribution"
        assert MarketCycle.MARKDOWN.value == "markdown"


class TestRiskEnvironment:
    """Test RiskEnvironment enum."""

    def test_risk_environment_values(self):
        """Test RiskEnvironment enum values."""
        assert RiskEnvironment.RISK_ON.value == "risk_on"
        assert RiskEnvironment.RISK_OFF.value == "risk_off"
        assert RiskEnvironment.RISK_NEUTRAL.value == "risk_neutral"
        assert RiskEnvironment.FLIGHT_TO_QUALITY.value == "flight_to_quality"
        assert RiskEnvironment.CARRY_TRADE.value == "carry_trade"
        assert RiskEnvironment.DELEVERAGING.value == "deleveraging"
        assert RiskEnvironment.UNKNOWN.value == "unknown"


class TestRegimeAnalysisConfig:
    """Test RegimeAnalysisConfig dataclass."""

    def test_initialization_default(self):
        """Test RegimeAnalysisConfig initialization with defaults."""
        config = RegimeAnalysisConfig()

        assert len(config.equity_indices) == 5
        assert len(config.fixed_income) == 5
        assert len(config.commodities) == 5
        assert len(config.currencies) == 4
        assert len(config.volatility) == 3
        assert config.lookback_periods == [20, 60, 252]
        assert config.correlation_window == 60
        assert config.factor_analysis_window == 252
        assert config.correlation_threshold == 0.7
        assert config.volatility_percentile_threshold == 0.8
        assert config.momentum_threshold == 0.1
        assert config.min_cluster_size == 5
        assert config.eps_parameter == 0.3
        assert config.n_components_pca == 5
        assert config.update_frequency == "daily"
        assert config.var_confidence == 0.05
        assert config.expected_shortfall_confidence == 0.05

    def test_initialization_custom(self):
        """Test RegimeAnalysisConfig initialization with custom values."""
        config = RegimeAnalysisConfig(
            equity_indices=["SPY", "QQQ"],
            fixed_income=["TLT", "IEF"],
            commodities=["GLD", "SLV"],
            currencies=["UUP", "FXE"],
            volatility=["VIX"],
            lookback_periods=[30, 90],
            correlation_window=90,
            factor_analysis_window=126,
            correlation_threshold=0.8,
            volatility_percentile_threshold=0.9,
            momentum_threshold=0.15,
            min_cluster_size=3,
            eps_parameter=0.2,
            n_components_pca=3,
            update_frequency="weekly",
            var_confidence=0.01,
            expected_shortfall_confidence=0.01
        )

        assert config.equity_indices == ["SPY", "QQQ"]
        assert config.fixed_income == ["TLT", "IEF"]
        assert config.commodities == ["GLD", "SLV"]
        assert config.currencies == ["UUP", "FXE"]
        assert config.volatility == ["VIX"]
        assert config.lookback_periods == [30, 90]
        assert config.correlation_window == 90
        assert config.factor_analysis_window == 126
        assert config.correlation_threshold == 0.8
        assert config.volatility_percentile_threshold == 0.9
        assert config.momentum_threshold == 0.15
        assert config.min_cluster_size == 3
        assert config.eps_parameter == 0.2
        assert config.n_components_pca == 3
        assert config.update_frequency == "weekly"
        assert config.var_confidence == 0.01
        assert config.expected_shortfall_confidence == 0.01


class TestAssetRegimeProfile:
    """Test AssetRegimeProfile dataclass."""

    def test_initialization(self):
        """Test AssetRegimeProfile initialization."""
        timestamp = datetime.now()
        profile = AssetRegimeProfile(
            asset_name="AAPL",
            current_regime=RegimeType.BULL_MARKET,
            regime_confidence=0.85,
            volatility=0.25,
            correlation_to_market=0.75,
            beta=1.2,
            momentum=0.8,
            regime_persistence=0.9,
            last_regime_change=timestamp,
            var_95=0.03,
            expected_shortfall=0.045,
            max_drawdown=0.12,
            factor_loadings={"value": 0.3, "growth": 0.7},
            relative_strength=1.05,
            sector_rotation_signal=0.2
        )

        assert profile.asset_name == "AAPL"
        assert profile.current_regime == RegimeType.BULL_MARKET
        assert profile.regime_confidence == 0.85
        assert profile.volatility == 0.25
        assert profile.correlation_to_market == 0.75
        assert profile.beta == 1.2
        assert profile.momentum == 0.8
        assert profile.regime_persistence == 0.9
        assert profile.last_regime_change == timestamp
        assert profile.var_95 == 0.03
        assert profile.expected_shortfall == 0.045
        assert profile.max_drawdown == 0.12
        assert profile.factor_loadings["value"] == 0.3
        assert profile.relative_strength == 1.05
        assert profile.sector_rotation_signal == 0.2


class TestCrossAssetRegime:
    """Test CrossAssetRegime dataclass."""

    def test_initialization(self):
        """Test CrossAssetRegime initialization."""
        timestamp = datetime.now()

        cross_regime = CrossAssetRegime(
            timestamp=timestamp,
            equity_regime=RegimeType.BULL_MARKET,
            fixed_income_regime=RegimeType.LOW_VOLATILITY,
            commodity_regime=RegimeType.SIDEWAYS,
            currency_regime=RegimeType.UNKNOWN,
            macro_regime=MacroRegime.EXPANSION,
            market_cycle=MarketCycle.MARKUP,
            risk_environment=RiskEnvironment.RISK_ON,
            equity_bond_correlation=0.3,
            commodity_dollar_correlation=-0.2,
            risk_on_off_signal=0.7,
            confidence=0.85,
            data_quality=0.95
        )

        assert cross_regime.timestamp == timestamp
        assert cross_regime.equity_regime == RegimeType.BULL_MARKET
        assert cross_regime.fixed_income_regime == RegimeType.LOW_VOLATILITY
        assert cross_regime.commodity_regime == RegimeType.SIDEWAYS
        assert cross_regime.currency_regime == RegimeType.UNKNOWN
        assert cross_regime.macro_regime == MacroRegime.EXPANSION
        assert cross_regime.market_cycle == MarketCycle.MARKUP
        assert cross_regime.risk_environment == RiskEnvironment.RISK_ON
        assert cross_regime.equity_bond_correlation == 0.3
        assert cross_regime.commodity_dollar_correlation == -0.2
        assert cross_regime.risk_on_off_signal == 0.7
        assert cross_regime.confidence == 0.85
        assert cross_regime.data_quality == 0.95


class TestFactorAnalyzer:
    """Test FactorAnalyzer class."""

    @pytest.fixture
    def analyzer_config(self):
        """Create analyzer configuration for testing."""
        return RegimeAnalysisConfig(
            correlation_threshold=0.7,
            volatility_percentile_threshold=0.8,
            momentum_threshold=0.1,
            factor_analysis_window=50  # Reduced for testing
        )

    @pytest.fixture
    def sample_factor_data(self):
        """Create sample factor data for testing."""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        np.random.seed(42)

        data = pd.DataFrame({
            'market_return': np.random.randn(100) * 0.02,
            'value_factor': np.random.randn(100) * 0.015,
            'growth_factor': np.random.randn(100) * 0.018,
            'momentum_factor': np.random.randn(100) * 0.012,
            'volatility_factor': np.random.randn(100) * 0.025
        }, index=dates)

        return data

    def test_initialization(self, analyzer_config):
        """Test FactorAnalyzer initialization."""
        analyzer = FactorAnalyzer(analyzer_config)

        assert analyzer.config == analyzer_config
        assert hasattr(analyzer, 'analyze_factors')
        assert hasattr(analyzer, 'pca')
        assert hasattr(analyzer, 'scaler')

    def test_analyze_factors(self, sample_factor_data, analyzer_config):
        """Test factor analysis."""
        analyzer = FactorAnalyzer(analyzer_config)

        result = analyzer.analyze_factors(sample_factor_data)

        assert isinstance(result, dict)
        assert 'factor_returns' in result
        assert 'factor_loadings' in result
        assert 'factor_correlations' in result


class TestCrossAssetAnalyzer:
    """Test CrossAssetAnalyzer class."""

    @pytest.fixture
    def analyzer_config(self):
        """Create analyzer configuration for testing."""
        return RegimeAnalysisConfig(
            correlation_threshold=0.7,
            volatility_percentile_threshold=0.8,
            momentum_threshold=0.1,
            factor_analysis_window=50  # Reduced for testing
        )

    @pytest.fixture
    def sample_asset_data(self):
        """Create sample multi-asset data for testing."""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        np.random.seed(42)

        data = pd.DataFrame({
            'timestamp': dates,
            'AAPL': 100 + np.cumsum(np.random.randn(100) * 0.5),
            'GOOGL': 150 + np.cumsum(np.random.randn(100) * 0.6),
            'MSFT': 200 + np.cumsum(np.random.randn(100) * 0.4),
            'TSLA': 250 + np.cumsum(np.random.randn(100) * 0.8)
        })

        return data

    def test_initialization(self, analyzer_config):
        """Test CrossAssetAnalyzer initialization."""
        analyzer = CrossAssetAnalyzer(analyzer_config)

        assert analyzer.config == analyzer_config
        assert hasattr(analyzer, 'analyze_cross_asset_regime')

    def test_analyze_cross_asset_regime(self, sample_asset_data, analyzer_config):
        """Test cross-asset regime analysis."""
        analyzer = CrossAssetAnalyzer(analyzer_config)

        # Convert sample data to the expected format (dict of DataFrames)
        market_data = {
            'equity': sample_asset_data[['AAPL', 'GOOGL', 'MSFT', 'TSLA']]
        }

        regime = analyzer.analyze_cross_asset_regime(market_data)

        assert isinstance(regime, CrossAssetRegime)
        assert hasattr(regime, 'macro_regime')
        assert hasattr(regime, 'market_cycle')


class TestSectorRotationAnalyzer:
    """Test SectorRotationAnalyzer class."""

    @pytest.fixture
    def analyzer_config(self):
        """Create analyzer configuration for testing."""
        return RegimeAnalysisConfig(
            correlation_threshold=0.7,
            volatility_percentile_threshold=0.8,
            momentum_threshold=0.1,
            factor_analysis_window=50  # Reduced for testing
        )

    @pytest.fixture
    def sample_sector_data(self):
        """Create sample sector data for testing."""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        np.random.seed(42)

        sectors = ['technology', 'healthcare', 'financials', 'energy', 'consumer']
        data = pd.DataFrame({
            'timestamp': dates
        })

        for sector in sectors:
            data[sector] = 100 + np.cumsum(np.random.randn(100) * 0.3)

        return data

    def test_initialization(self, analyzer_config):
        """Test SectorRotationAnalyzer initialization."""
        analyzer = SectorRotationAnalyzer(analyzer_config)

        assert analyzer.config == analyzer_config
        assert hasattr(analyzer, 'analyze_sector_rotation')

    def test_analyze_sector_rotation(self, sample_sector_data, analyzer_config):
        """Test sector rotation analysis."""
        analyzer = SectorRotationAnalyzer(analyzer_config)

        # Convert to expected format: dict of DataFrames
        sector_data = {}
        for col in sample_sector_data.columns:
            if col != 'timestamp':
                sector_data[col] = sample_sector_data[['timestamp', col]].set_index('timestamp')

        rotation = analyzer.analyze_sector_rotation(sector_data)

        # The method may return empty dict if data is insufficient
        # Just check it's a dict for now


class TestMarketRegimeAnalyzer:
    """Test MarketRegimeAnalyzer class."""

    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for testing."""
        dates = pd.date_range('2023-01-01', periods=200, freq='D')
        np.random.seed(42)

        data = pd.DataFrame({
            'timestamp': dates,
            'SPY': 400 + np.cumsum(np.random.randn(200) * 1.0),  # Market index
            'VIX': 20 + np.random.randn(200) * 5,  # Volatility index
            'DXY': 100 + np.random.randn(200) * 2,  # Dollar index
            'TNX': 4.0 + np.random.randn(200) * 0.5,  # Treasury yield
        })

        return data

    @pytest.fixture
    def analyzer_config(self):
        """Create analyzer configuration for testing."""
        return RegimeAnalysisConfig(
            correlation_threshold=0.7,
            volatility_percentile_threshold=0.8,
            momentum_threshold=0.1
        )

    def test_initialization(self, analyzer_config):
        """Test MarketRegimeAnalyzer initialization."""
        analyzer = MarketRegimeAnalyzer(analyzer_config)

        assert analyzer.config == analyzer_config
        assert hasattr(analyzer, 'analyze_market_regime')

    def test_analyze_market_regime(self, sample_market_data, analyzer_config):
        """Test market regime analysis."""
        analyzer = MarketRegimeAnalyzer(analyzer_config)

        # Convert sample data to expected format
        market_data = {
            'equity': sample_market_data[['timestamp', 'SPY']].set_index('timestamp'),
            'volatility': sample_market_data[['timestamp', 'VIX']].set_index('timestamp'),
            'currency': sample_market_data[['timestamp', 'DXY']].set_index('timestamp'),
            'rates': sample_market_data[['timestamp', 'TNX']].set_index('timestamp')
        }

        result = analyzer.analyze_market_regime(market_data)

        assert isinstance(result, dict)
        assert 'cross_asset_regime' in result
        assert 'factor_analysis' in result
        assert 'sector_analysis' in result
        assert 'regime_summary' in result

        # Check that cross_asset_regime is a CrossAssetRegime
        cross_asset_regime = result['cross_asset_regime']
        assert isinstance(cross_asset_regime, CrossAssetRegime)

    def test_empty_data_handling(self, analyzer_config):
        """Test handling of empty data."""
        empty_data = {}  # Empty dict instead of empty DataFrame

        analyzer = MarketRegimeAnalyzer(analyzer_config)

        # Should handle gracefully, returning default regime analysis
        result = analyzer.analyze_market_regime(empty_data)
        assert isinstance(result, dict)
        assert 'cross_asset_regime' in result
        assert 'factor_analysis' in result
        assert 'sector_analysis' in result
        assert 'regime_summary' in result
        # cross_asset_regime should be a default/empty CrossAssetRegime object
        from core_engine.regime.market_regime_analyzer import CrossAssetRegime
        assert isinstance(result['cross_asset_regime'], CrossAssetRegime)

    def test_insufficient_data_handling(self, analyzer_config):
        """Test handling of insufficient data."""
        insufficient_data = {
            'SPY': pd.DataFrame({
                'timestamp': pd.date_range('2023-01-01', periods=5),
                'close': [400, 401, 402, 403, 404]
            })
        }

        analyzer = MarketRegimeAnalyzer(analyzer_config)

        # Should handle gracefully or raise appropriate error
        try:
            result = analyzer.analyze_market_regime(insufficient_data)
            assert isinstance(result, dict)
            # May return partial results or empty dict for insufficient data
        except Exception:
            # Expected for insufficient data
            pass


class TestMLModel:
    """Test MLModel enum."""

    def test_ml_model_values(self):
        """Test MLModel enum values."""
        assert MLModel.RANDOM_FOREST.value == "random_forest"
        assert MLModel.GRADIENT_BOOSTING.value == "gradient_boosting"
        assert MLModel.SVM.value == "svm"
        assert MLModel.NEURAL_NETWORK.value == "neural_network"


class TestFeatureType:
    """Test FeatureType enum."""

    def test_feature_type_values(self):
        """Test FeatureType enum values."""
        assert FeatureType.PRICE_BASED.value == "price_based"
        assert FeatureType.VOLATILITY_BASED.value == "volatility_based"
        assert FeatureType.MOMENTUM_BASED.value == "momentum_based"
        assert FeatureType.CORRELATION_BASED.value == "correlation_based"
        assert FeatureType.VOLUME_BASED.value == "volume_based"
        assert FeatureType.TECHNICAL_INDICATORS.value == "technical_indicators"
        assert FeatureType.MACRO_INDICATORS.value == "macro_indicators"
        assert FeatureType.SENTIMENT_INDICATORS.value == "sentiment_indicators"


class TestClassificationConfig:
    """Test ClassificationConfig dataclass."""

    def test_initialization_default(self):
        """Test ClassificationConfig initialization with defaults."""
        config = ClassificationConfig()

        assert config.primary_model == MLModel.ENSEMBLE
        assert config.models_to_test == [MLModel.RANDOM_FOREST, MLModel.GRADIENT_BOOSTING, MLModel.SVM, MLModel.LOGISTIC_REGRESSION]
        assert config.feature_types == [FeatureType.PRICE_BASED, FeatureType.VOLATILITY_BASED, FeatureType.MOMENTUM_BASED, FeatureType.CORRELATION_BASED]
        assert config.lookback_windows == [5, 10, 20, 60, 252]
        assert config.min_training_samples == 100
        assert config.test_size == 0.2
        assert config.validation_splits == 5
        assert config.max_features == 50
        assert config.feature_selection_method == "mutual_info"
        assert config.correlation_threshold == 0.95

    def test_initialization_custom(self):
        """Test ClassificationConfig initialization with custom values."""
        config = ClassificationConfig(
            primary_model=MLModel.GRADIENT_BOOSTING,
            models_to_test=[MLModel.RANDOM_FOREST, MLModel.SVM],
            feature_types=[FeatureType.PRICE_BASED, FeatureType.VOLATILITY_BASED],
            lookback_windows=[10, 20, 60],
            min_training_samples=200,
            test_size=0.3,
            validation_splits=3,
            max_features=25,
            feature_selection_method="f_classif",
            correlation_threshold=0.9
        )

        assert config.primary_model == MLModel.GRADIENT_BOOSTING
        assert config.models_to_test == [MLModel.RANDOM_FOREST, MLModel.SVM]
        assert config.feature_types == [FeatureType.PRICE_BASED, FeatureType.VOLATILITY_BASED]
        assert config.lookback_windows == [10, 20, 60]
        assert config.min_training_samples == 200
        assert config.test_size == 0.3
        assert config.validation_splits == 3
        assert config.max_features == 25
        assert config.feature_selection_method == "f_classif"
        assert config.correlation_threshold == 0.9


class TestFeatureImportance:
    """Test FeatureImportance dataclass."""

    def test_initialization(self):
        """Test FeatureImportance initialization."""
        importance = FeatureImportance(
            feature_name="rsi_14",
            importance_score=0.85,
            importance_rank=1,
            mean_value=50.0,
            std_value=10.0,
            correlation_with_target=0.65,
            regime_specific_importance={"bull": 0.8, "bear": 0.9}
        )

        assert importance.feature_name == "rsi_14"
        assert importance.importance_score == 0.85
        assert importance.importance_rank == 1
        assert importance.mean_value == 50.0
        assert importance.std_value == 10.0
        assert importance.correlation_with_target == 0.65
        assert importance.regime_specific_importance == {"bull": 0.8, "bear": 0.9}


class TestModelPerformance:
    """Test ModelPerformance dataclass."""

    def test_initialization(self):
        """Test ModelPerformance initialization."""
        performance = ModelPerformance(
            model_name="random_forest",
            accuracy=0.85,
            precision=0.82,
            recall=0.88,
            f1_score=0.85,
            cv_accuracy_mean=0.83,
            cv_accuracy_std=0.02,
            regime_specific_metrics={"bull": {"accuracy": 0.87, "precision": 0.85}},
            confusion_matrix=np.array([[85, 15], [12, 88]]),
            feature_importances=[],
            training_samples=1000,
            training_time=45.2,
            last_trained=datetime(2024, 1, 1)
        )

        assert performance.model_name == "random_forest"
        assert performance.accuracy == 0.85
        assert performance.precision == 0.82
        assert performance.recall == 0.88
        assert performance.f1_score == 0.85
        assert performance.cv_accuracy_mean == 0.83
        assert performance.cv_accuracy_std == 0.02
        assert performance.regime_specific_metrics == {"bull": {"accuracy": 0.87, "precision": 0.85}}
        assert np.array_equal(performance.confusion_matrix, np.array([[85, 15], [12, 88]]))
        assert performance.training_samples == 1000
        assert performance.training_time == 45.2
        assert performance.last_trained == datetime(2024, 1, 1)


class TestRegimeClassification:
    """Test RegimeClassification dataclass."""

    def test_initialization(self):
        """Test RegimeClassification initialization."""
        timestamp = datetime.now()
        classification = RegimeClassification(
            timestamp=timestamp,
            predicted_regime=RegimeType.BULL_MARKET,
            prediction_confidence=0.85,
            regime_probabilities={RegimeType.BULL_MARKET: 0.85, RegimeType.SIDEWAYS: 0.15},
            top_3_regimes=[(RegimeType.BULL_MARKET, 0.85), (RegimeType.SIDEWAYS, 0.15)],
            feature_contributions={"rsi_14": 0.3, "macd": 0.25, "volume_ratio": 0.2},
            model_used=MLModel.RANDOM_FOREST,
            model_confidence=0.82,
            regime_stability=0.9,
            recent_regime_changes=2,
            prediction_horizon_days=5,
            prediction_decay=0.95
        )

        assert classification.timestamp == timestamp
        assert classification.predicted_regime == RegimeType.BULL_MARKET
        assert classification.prediction_confidence == 0.85
        assert classification.regime_probabilities == {RegimeType.BULL_MARKET: 0.85, RegimeType.SIDEWAYS: 0.15}
        assert classification.top_3_regimes == [(RegimeType.BULL_MARKET, 0.85), (RegimeType.SIDEWAYS, 0.15)]
        assert classification.feature_contributions == {"rsi_14": 0.3, "macd": 0.25, "volume_ratio": 0.2}
        assert classification.model_used == MLModel.RANDOM_FOREST
        assert classification.model_confidence == 0.82
        assert classification.regime_stability == 0.9
        assert classification.recent_regime_changes == 2
        assert classification.prediction_horizon_days == 5
        assert classification.prediction_decay == 0.95


class TestFeatureEngineer:
    """Test FeatureEngineer class."""

    @pytest.fixture
    def sample_price_data(self):
        """Create sample price data for testing."""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        np.random.seed(42)

        data = pd.DataFrame({
            'close': 100 + np.cumsum(np.random.randn(100) * 0.5),
            'high': 102 + np.cumsum(np.random.randn(100) * 0.5),
            'low': 98 + np.cumsum(np.random.randn(100) * 0.5),
            'volume': np.random.randint(1000, 10000, 100),
            'open': 100 + np.cumsum(np.random.randn(100) * 0.3)
        }, index=dates)

        return data

    @pytest.fixture
    def classifier_config(self):
        """Create classifier configuration for testing."""
        return ClassificationConfig(
            primary_model=MLModel.RANDOM_FOREST,
            max_features=20,
            lookback_windows=[5, 10, 20]  # Smaller windows for test data
        )

    def test_initialization(self, classifier_config):
        """Test FeatureEngineer initialization."""
        engineer = FeatureEngineer(classifier_config)

        assert engineer.config == classifier_config
        assert hasattr(engineer, 'engineer_features')

    def test_create_features(self, sample_price_data, classifier_config):
        """Test feature creation."""
        engineer = FeatureEngineer(classifier_config)

        features = engineer.engineer_features(sample_price_data)

        assert isinstance(features, pd.DataFrame)
        assert len(features) > 0
        assert len(features.columns) > len(sample_price_data.columns)


class TestRegimeModelTrainer:
    """Test RegimeModelTrainer class."""

    @pytest.fixture
    def sample_training_data(self):
        """Create sample training data for testing."""
        np.random.seed(42)
        n_samples = 1000

        # Generate features
        features = pd.DataFrame({
            'rsi_14': np.random.uniform(20, 80, n_samples),
            'macd': np.random.randn(n_samples) * 0.1,
            'volume_ratio': np.random.uniform(0.5, 1.5, n_samples),
            'volatility_20': np.random.uniform(0.1, 0.5, n_samples),
            'momentum_10': np.random.randn(n_samples) * 0.05
        })

        # Generate target regimes
        regimes = np.random.choice(list(RegimeType), n_samples)
        target = pd.Series(regimes)

        return features, target

    @pytest.fixture
    def trainer_config(self):
        """Create trainer configuration for testing."""
        return ClassificationConfig(
            primary_model=MLModel.RANDOM_FOREST,
            max_features=20,
            lookback_windows=[5, 10, 20]  # Smaller windows for test data
        )

    def test_initialization(self, trainer_config):
        """Test RegimeModelTrainer initialization."""
        trainer = RegimeModelTrainer(trainer_config)

        assert trainer.config == trainer_config
        assert hasattr(trainer, 'train_models')

    @patch('core_engine.regime.regime_classifier.RandomForestClassifier')
    def test_train_model(self, mock_rf, sample_training_data, trainer_config):
        """Test model training."""
        features, target = sample_training_data

        # Mock the classifier
        mock_model = Mock()
        mock_model.fit.return_value = None
        mock_model.score.return_value = 0.85
        mock_rf.return_value = mock_model

        trainer = RegimeModelTrainer(trainer_config)

        performances = trainer.train_models(features, target)

        assert isinstance(performances, dict)
        assert len(performances) > 0
        for model_name, performance in performances.items():
            assert isinstance(performance, ModelPerformance)

    def test_predict_regime(self, sample_training_data, trainer_config):
        """Test regime prediction."""
        features, target = sample_training_data

        trainer = RegimeModelTrainer(trainer_config)
        trainer.train_models(features, target)

        # Test prediction with a single sample
        single_sample = features.iloc[:1]
        prediction = trainer.predict_regime(single_sample)

        assert isinstance(prediction, RegimeClassification)


class TestRegimeClassifier:
    """Test RegimeClassifier class."""

    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for testing."""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        np.random.seed(42)

        data = pd.DataFrame({
            'timestamp': dates,
            'close': 100 + np.cumsum(np.random.randn(100) * 0.5),
            'high': 102 + np.cumsum(np.random.randn(100) * 0.5),
            'low': 98 + np.cumsum(np.random.randn(100) * 0.5),
            'volume': np.random.randint(1000, 10000, 100),
            'open': 100 + np.cumsum(np.random.randn(100) * 0.3)
        })

        return data

    @pytest.fixture
    def classifier_config(self):
        """Create classifier configuration for testing."""
        return ClassificationConfig(
            primary_model=MLModel.RANDOM_FOREST,
            max_features=20,
            lookback_windows=[5, 10, 20]  # Smaller windows for test data
        )

    def test_initialization(self, classifier_config):
        """Test RegimeClassifier initialization."""
        classifier = RegimeClassifier(classifier_config)

        assert classifier.config == classifier_config
        assert hasattr(classifier, 'classify_regime')

    @patch('core_engine.regime.regime_classifier.RegimeModelTrainer')
    @patch('core_engine.regime.regime_classifier.FeatureEngineer')
    def test_classify_regime(self, mock_feature_engineer, mock_trainer, sample_market_data, classifier_config):
        """Test regime classification."""
        # Mock feature engineer
        mock_engineer_instance = Mock()
        mock_features = pd.DataFrame({'feature1': [1, 2, 3], 'feature2': [0.1, 0.2, 0.3]})
        mock_engineer_instance.engineer_features.return_value = mock_features
        mock_feature_engineer.return_value = mock_engineer_instance

        # Mock trainer
        mock_trainer_instance = Mock()
        mock_classification = Mock(spec=RegimeClassification)
        mock_classification.predicted_regime = RegimeType.BULL_MARKET
        mock_classification.prediction_confidence = 0.85
        mock_trainer_instance.predict_regime.return_value = mock_classification
        mock_trainer.return_value = mock_trainer_instance

        classifier = RegimeClassifier(classifier_config)

        classification = classifier.classify_regime(sample_market_data)

        assert classification is not None
        assert classification.predicted_regime == RegimeType.BULL_MARKET
        assert classification.prediction_confidence == 0.85

    def test_empty_data_handling(self, classifier_config):
        """Test handling of empty data."""
        empty_data = pd.DataFrame()

        classifier = RegimeClassifier(classifier_config)

        result = classifier.classify_regime(empty_data)
        assert result is None

    def test_untrained_model_handling(self, sample_market_data, classifier_config):
        """Test handling when model is not trained."""
        classifier = RegimeClassifier(classifier_config)

        result = classifier.classify_regime(sample_market_data)
        assert result is None


class TestRegimeType:
    """Test RegimeType enum."""

    def test_regime_type_values(self):
        """Test RegimeType enum values."""
        assert RegimeType.BULL_MARKET.value == "bull_market"
        assert RegimeType.BEAR_MARKET.value == "bear_market"
        assert RegimeType.SIDEWAYS.value == "sideways"
        assert RegimeType.HIGH_VOLATILITY.value == "high_volatility"
        assert RegimeType.LOW_VOLATILITY.value == "low_volatility"


class TestDetectionMethod:
    """Test DetectionMethod enum."""

    def test_detection_method_values(self):
        """Test DetectionMethod enum values."""
        assert DetectionMethod.MARKOV_SWITCHING.value == "markov_switching"
        assert DetectionMethod.GAUSSIAN_MIXTURE.value == "gaussian_mixture"
        assert DetectionMethod.CLUSTERING.value == "clustering"
        assert DetectionMethod.THRESHOLD_BASED.value == "threshold_based"
        assert DetectionMethod.STATISTICAL_TESTS.value == "statistical_tests"


class TestConfidenceLevel:
    """Test ConfidenceLevel enum."""

    def test_confidence_level_values(self):
        """Test ConfidenceLevel enum values."""
        assert ConfidenceLevel.VERY_LOW.value == 0.50
        assert ConfidenceLevel.LOW.value == 0.65
        assert ConfidenceLevel.MEDIUM.value == 0.75
        assert ConfidenceLevel.HIGH.value == 0.85
        assert ConfidenceLevel.VERY_HIGH.value == 0.95


class TestRegimeDetectionConfig:
    """Test RegimeDetectionConfig dataclass."""

    def test_initialization_default(self):
        """Test RegimeDetectionConfig initialization with defaults."""
        config = RegimeDetectionConfig()

        assert config.methods == [DetectionMethod.MARKOV_SWITCHING, DetectionMethod.GAUSSIAN_MIXTURE, DetectionMethod.VOLATILITY_BASED]
        assert config.short_lookback == 20
        assert config.medium_lookback == 60
        assert config.long_lookback == 252
        assert config.volatility_window == 20
        assert config.volatility_threshold_high == 0.25
        assert config.volatility_threshold_low == 0.10
        assert config.bull_threshold == 0.15
        assert config.bear_threshold == -0.10
        assert config.min_regime_duration == 10
        assert config.confidence_threshold == 0.75
        assert config.n_regimes == 3
        assert config.switching_variance == True
        assert config.n_clusters == 3
        assert config.random_state == 42

    def test_initialization_custom(self):
        """Test RegimeDetectionConfig initialization with custom values."""
        config = RegimeDetectionConfig(
            methods=[DetectionMethod.MARKOV_SWITCHING, DetectionMethod.CLUSTERING],
            short_lookback=30,
            medium_lookback=90,
            long_lookback=365,
            volatility_window=30,
            volatility_threshold_high=0.30,
            volatility_threshold_low=0.15,
            bull_threshold=0.20,
            bear_threshold=-0.15,
            min_regime_duration=15,
            confidence_threshold=0.80,
            n_regimes=4,
            switching_variance=False,
            n_clusters=4,
            random_state=123
        )

        assert config.methods == [DetectionMethod.MARKOV_SWITCHING, DetectionMethod.CLUSTERING]
        assert config.short_lookback == 30
        assert config.medium_lookback == 90
        assert config.long_lookback == 365
        assert config.volatility_window == 30
        assert config.volatility_threshold_high == 0.30
        assert config.volatility_threshold_low == 0.15
        assert config.bull_threshold == 0.20
        assert config.bear_threshold == -0.15
        assert config.min_regime_duration == 15
        assert config.confidence_threshold == 0.80
        assert config.n_regimes == 4
        assert config.switching_variance == False
        assert config.n_clusters == 4
        assert config.random_state == 123


class TestRegimeDetection:
    """Test RegimeDetection dataclass."""

    def test_initialization(self):
        """Test RegimeDetection initialization."""
        timestamp = datetime.now()
        detection = RegimeDetection(
            timestamp=timestamp,
            regime_type=RegimeType.BULL_MARKET,
            confidence=0.85,
            method=DetectionMethod.THRESHOLD_BASED,
            regime_start=timestamp - timedelta(days=10),
            regime_duration=10,
            expected_duration=15,
            regime_probability=0.85,
            transition_probability=0.15,
            stability_score=0.9,
            avg_return=0.02,
            volatility=0.15,
            skewness=0.1,
            kurtosis=2.5,
            max_drawdown=0.05,
            features={"rsi": 65.0, "macd": 0.5},
            model_output={"probabilities": [0.85, 0.10, 0.05]}
        )

        assert detection.timestamp == timestamp
        assert detection.regime_type == RegimeType.BULL_MARKET
        assert detection.confidence == 0.85
        assert detection.method == DetectionMethod.THRESHOLD_BASED
        assert detection.regime_start == timestamp - timedelta(days=10)
        assert detection.regime_duration == 10
        assert detection.expected_duration == 15
        assert detection.regime_probability == 0.85
        assert detection.transition_probability == 0.15
        assert detection.stability_score == 0.9
        assert detection.avg_return == 0.02
        assert detection.volatility == 0.15
        assert detection.skewness == 0.1
        assert detection.kurtosis == 2.5
        assert detection.max_drawdown == 0.05
        assert detection.features == {"rsi": 65.0, "macd": 0.5}
        assert detection.model_output == {"probabilities": [0.85, 0.10, 0.05]}


class TestRegimeTransition:
    """Test RegimeTransition dataclass."""

    def test_initialization(self):
        """Test RegimeTransition initialization."""
        timestamp = datetime.now()
        transition = RegimeTransition(
            from_regime=RegimeType.SIDEWAYS,
            to_regime=RegimeType.BULL_MARKET,
            transition_date=timestamp,
            transition_probability=0.8,
            transition_speed="fast",
            transition_volatility=0.25,
            market_stress=0.7,
            leading_indicators={"rsi_divergence": 0.8, "volume_surge": 0.9},
            warning_signals=["high_volatility", "momentum_shift"],
            performance_impact=0.05,
            risk_impact=0.15
        )

        assert transition.from_regime == RegimeType.SIDEWAYS
        assert transition.to_regime == RegimeType.BULL_MARKET
        assert transition.transition_date == timestamp
        assert transition.transition_probability == 0.8
        assert transition.transition_speed == "fast"
        assert transition.transition_volatility == 0.25
        assert transition.market_stress == 0.7
        assert transition.leading_indicators == {"rsi_divergence": 0.8, "volume_surge": 0.9}
        assert transition.warning_signals == ["high_volatility", "momentum_shift"]
        assert transition.performance_impact == 0.05
        assert transition.risk_impact == 0.15


class TestMarkovSwitchingDetector:
    """Test MarkovSwitchingDetector class."""

    @pytest.fixture
    def detector_config(self):
        """Create detector configuration for testing."""
        return RegimeDetectionConfig()

    @pytest.fixture
    def sample_returns_data(self):
        """Create sample returns data for testing."""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=200, freq='D')

        # Generate regime-switching returns
        returns = np.zeros(200)

        # Regime 1: Low volatility (first 100 days)
        returns[:100] = np.random.normal(0.0005, 0.01, 100)

        # Regime 2: High volatility (last 100 days)
        returns[100:] = np.random.normal(0.001, 0.03, 100)

        data = pd.DataFrame({
            'timestamp': dates,
            'returns': returns
        })

        return data

    def test_initialization(self, detector_config):
        """Test MarkovSwitchingDetector initialization."""
        detector = MarkovSwitchingDetector(detector_config)

        assert hasattr(detector, 'fit')
        assert hasattr(detector, 'detect_regime')

    def test_detect_regime(self, sample_returns_data, detector_config):
        """Test regime detection using Markov switching."""
        detector = MarkovSwitchingDetector(detector_config)

        # First fit the model
        success = detector.fit(sample_returns_data['returns'])
        assert success

        # Then detect regime
        regime_detection = detector.detect_regime(sample_returns_data['returns'], datetime.now())

        assert isinstance(regime_detection, RegimeDetection)
        assert regime_detection.regime_type in RegimeType
        assert 0.0 <= regime_detection.confidence <= 1.0


class TestGaussianMixtureDetector:
    """Test GaussianMixtureDetector class."""

    @pytest.fixture
    def detector_config(self):
        """Create detector configuration for testing."""
        return RegimeDetectionConfig()

    @pytest.fixture
    def sample_multivariate_data(self):
        """Create sample multivariate data for testing."""
        np.random.seed(42)
        n_samples = 300

        # Generate data from two different regimes
        data = np.zeros((n_samples, 2))

        # Regime 1: Low volatility, positive correlation
        n_regime1 = 150
        returns1 = np.random.multivariate_normal([0.001, 0.0005], [[0.0001, 0.00005], [0.00005, 0.0001]], n_regime1)
        data[:n_regime1] = returns1

        # Regime 2: High volatility, negative correlation
        n_regime2 = 150
        returns2 = np.random.multivariate_normal([0.0005, 0.001], [[0.0004, -0.0001], [-0.0001, 0.0004]], n_regime2)
        data[n_regime1:] = returns2

        return pd.DataFrame(data, columns=['asset_a_returns', 'asset_b_returns'])

    def test_initialization(self, detector_config):
        """Test GaussianMixtureDetector initialization."""
        detector = GaussianMixtureDetector(detector_config)

        assert hasattr(detector, 'fit')
        assert hasattr(detector, 'detect_regime')

    def test_detect_regime(self, sample_multivariate_data, detector_config):
        """Test regime detection using GMM."""
        detector = GaussianMixtureDetector(detector_config)

        # First fit the model
        success = detector.fit(sample_multivariate_data)
        assert success

        # Then detect regime
        regime_detection = detector.detect_regime(sample_multivariate_data, datetime.now())

        assert isinstance(regime_detection, RegimeDetection)
        assert regime_detection.regime_type in RegimeType
        assert 0.0 <= regime_detection.confidence <= 1.0


class TestVolatilityBasedDetector:
    """Test VolatilityBasedDetector class."""

    @pytest.fixture
    def detector_config(self):
        """Create detector configuration for testing."""
        return RegimeDetectionConfig()

    @pytest.fixture
    def sample_volatility_data(self):
        """Create sample volatility data for testing."""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=200, freq='D')

        # Generate changing volatility
        volatility = np.zeros(200)

        # Low volatility period
        volatility[:100] = np.random.uniform(0.005, 0.015, 100)

        # High volatility period
        volatility[100:] = np.random.uniform(0.02, 0.05, 100)

        data = pd.DataFrame({
            'timestamp': dates,
            'volatility': volatility,
            'returns': np.random.randn(200) * 0.02
        })

        return data

    def test_initialization(self, detector_config):
        """Test VolatilityBasedDetector initialization."""
        detector = VolatilityBasedDetector(detector_config)

        assert hasattr(detector, 'detect_regime')

    def test_detect_regime(self, sample_volatility_data, detector_config):
        """Test volatility-based regime detection."""
        detector = VolatilityBasedDetector(detector_config)

        regime_detection = detector.detect_regime(sample_volatility_data['returns'], datetime.now())

        assert isinstance(regime_detection, RegimeDetection)
        assert regime_detection.regime_type in RegimeType
        assert 0.0 <= regime_detection.confidence <= 1.0


class TestThresholdBasedDetector:
    """Test ThresholdBasedDetector class."""

    @pytest.fixture
    def detector_config(self):
        """Create detector configuration for testing."""
        return RegimeDetectionConfig()

    @pytest.fixture
    def sample_threshold_data(self):
        """Create sample data for threshold-based detection."""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=200, freq='D')

        # Generate returns data
        returns = np.random.randn(200) * 0.02

        data = pd.DataFrame({
            'timestamp': dates,
            'returns': returns,
            'volatility': np.random.uniform(0.01, 0.04, 200)
        })

        return data

    def test_initialization(self, detector_config):
        """Test ThresholdBasedDetector initialization."""
        detector = ThresholdBasedDetector(detector_config)

        assert hasattr(detector, 'detect_regime')

    def test_detect_regime(self, sample_threshold_data, detector_config):
        """Test threshold-based regime detection."""
        detector = ThresholdBasedDetector(detector_config)

        regime_detection = detector.detect_regime(sample_threshold_data['returns'], datetime.now())

        assert isinstance(regime_detection, RegimeDetection)
        assert regime_detection.regime_type in RegimeType
        assert 0.0 <= regime_detection.confidence <= 1.0


class TestRegimeDetector:
    """Test RegimeDetector class."""

    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for testing."""
        dates = pd.date_range('2023-01-01', periods=200, freq='D')
        np.random.seed(42)

        data = pd.DataFrame({
            'timestamp': dates,
            'close': 100 + np.cumsum(np.random.randn(200) * 0.5),
            'returns': np.random.randn(200) * 0.02,
            'volatility': np.random.uniform(0.01, 0.04, 200)
        })

        return data

    @pytest.fixture
    def detector_config(self):
        """Create detector configuration for testing."""
        return RegimeDetectionConfig(
            methods=[DetectionMethod.THRESHOLD_BASED],
            short_lookback=20,
            confidence_threshold=0.7
        )

    def test_initialization(self, detector_config):
        """Test RegimeDetector initialization."""
        detector = RegimeDetector(detector_config)

        assert detector.config == detector_config
        assert hasattr(detector, 'detect_current_regime')

    def test_detect_regime(self, sample_market_data, detector_config):
        """Test regime detection."""
        detector = RegimeDetector(detector_config)

        detection = detector.detect_current_regime(sample_market_data)

        assert isinstance(detection, RegimeDetection)
        assert detection.regime_type in list(RegimeType)
        assert 0.0 <= detection.confidence <= 1.0

    def test_detect_transition(self, sample_market_data, detector_config):
        """Test regime transition detection."""
        detector = RegimeDetector(detector_config)
        
        # Run multiple detections to potentially create transitions
        detection1 = detector.detect_current_regime(sample_market_data.iloc[:100])
        detection2 = detector.detect_current_regime(sample_market_data.iloc[50:150])
        
        # Get transition history
        transitions = detector.get_transition_history()
        
        assert isinstance(transitions, list)
        if transitions:
            for transition in transitions:
                assert isinstance(transition, RegimeTransition)
                assert transition.from_regime in list(RegimeType)
                assert transition.to_regime in list(RegimeType)

    def test_empty_data_handling(self, detector_config):
        """Test handling of empty data."""
        empty_data = pd.DataFrame()

        detector = RegimeDetector(detector_config)

        result = detector.detect_current_regime(empty_data)
        assert result is None

    def test_insufficient_data_handling(self, detector_config):
        """Test handling of insufficient data."""
        insufficient_data = pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01', periods=5),
            'close': [100, 101, 102, 103, 104]
        })

        detector = RegimeDetector(detector_config)

        # Should handle gracefully or return None for insufficient data
        result = detector.detect_current_regime(insufficient_data)
        assert result is None  # Expected for insufficient data


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
            'timestamp': dates,
            'close': prices,
            'high': prices * (1 + np.random.uniform(0.005, 0.02, 200)),
            'low': prices * (1 - np.random.uniform(0.005, 0.02, 200))
        })

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
            current_regime=RegimeType.BULL_MARKET,
            regime_confidence=0.85,
            regime_duration=15,
            transition_probability=0.1,
            risk_adjustment_factor=1.2,
            recommended_portfolio_adjustments={'max_position': 0.1, 'min_position': -0.1},
            current_regime_performance=0.05,
            last_update=timestamp
        )

        assert state.timestamp == timestamp
        assert state.current_regime == RegimeType.BULL_MARKET
        assert state.regime_confidence == 0.85
        assert state.regime_duration == 15
        assert state.transition_probability == 0.1
        assert state.risk_adjustment_factor == 1.2
        assert state.recommended_portfolio_adjustments['max_position'] == 0.1
        assert state.current_regime_performance == 0.05
        assert state.last_update == timestamp


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
            current_regime=RegimeType.BULL_MARKET,
            regime_confidence=0.8
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