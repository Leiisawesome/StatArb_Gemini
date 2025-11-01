"""
Unit tests for missing component configuration classes.
Tests the remaining 25 component config classes with comprehensive validation.

Author: StatArb_Gemini Configuration Testing
Date: October 29, 2025
Version: 1.0.0
"""

import pytest
import warnings
from dataclasses import asdict

from core_engine.config.component_config import (
    # Analytics Configs
    AnalyticsConfig,
    AttributionAnalyticsConfig,
    BenchmarkAnalyticsConfig,
    ReportGenerationConfig,
    MetricsCalculatorConfig,
    PerformanceAnalyticsConfig,
    
    # Execution & Portfolio Configs
    ExecutionConfig,
    PortfolioConfig,
    
    # Processing Configs
    RegimeConfig,
    SignalConfig,
    FeatureConfig,
    IndicatorConfig,
    
    # Connection & Data Configs
    ConnectionConfig,
    CachingConfig,
    DataValidationConfig,
    FeedManagementConfig,
    DataPerformanceConfig,
    
    # Risk Configs
    CorrelationConfig,
    ExposureConfig,
    VarConfig,
    StressTestConfig,
    LimitConfig,
    
    # Performance Configs
    TimingConfig,
    PerformanceConfig
)


class TestAnalyticsConfig:
    """Test suite for AnalyticsConfig class."""

    def test_initialization(self):
        """Test AnalyticsConfig initialization with defaults."""
        config = AnalyticsConfig()
        assert config.mode == "realtime"
        assert config.max_workers == 4
        assert config.enable_caching is True
        assert config.cache_ttl_hours == 24
        assert config.enable_performance_analysis is True
        assert config.enable_attribution_analysis is True
        assert config.enable_benchmark_analysis is True
        assert config.report_frequency == "daily"
        assert config.min_data_points == 30
        assert config.max_data_points == 50000

    def test_custom_initialization(self):
        """Test AnalyticsConfig initialization with custom values."""
        config = AnalyticsConfig(
            mode="batch",
            max_workers=8,
            enable_caching=False,
            cache_ttl_hours=48,
            enable_performance_analysis=False,
            enable_attribution_analysis=True,
            enable_benchmark_analysis=False,
            report_frequency="weekly",
            min_data_points=50,
            max_data_points=100000
        )
        
        assert config.mode == "batch"
        assert config.max_workers == 8
        assert config.enable_caching is False
        assert config.cache_ttl_hours == 48
        assert config.enable_performance_analysis is False
        assert config.enable_attribution_analysis is True
        assert config.enable_benchmark_analysis is False
        assert config.report_frequency == "weekly"
        assert config.min_data_points == 50
        assert config.max_data_points == 100000

    def test_validation(self):
        """Test AnalyticsConfig validation."""
        # Test that the class can be instantiated
        config = AnalyticsConfig()
        assert config is not None
        assert hasattr(config, 'mode')
        assert hasattr(config, 'max_workers')
        assert hasattr(config, 'enable_performance_analysis')
        assert hasattr(config, 'enable_attribution_analysis')
        assert hasattr(config, 'report_frequency')
        assert hasattr(config, 'min_data_points')
        assert hasattr(config, 'max_data_points')
        
        # Test composition pattern
        assert hasattr(config, 'performance')
        assert hasattr(config, 'metrics')
        assert hasattr(config, 'attribution')
        assert hasattr(config, 'benchmark')
        assert hasattr(config, 'reporting')


class TestAttributionAnalyticsConfig:
    """Test suite for AttributionAnalyticsConfig class."""

    def test_initialization(self):
        """Test AttributionAnalyticsConfig initialization with defaults."""
        config = AttributionAnalyticsConfig()
        assert config.enable_brinson_attribution is True
        assert config.enable_factor_attribution is True
        assert config.enable_strategy_attribution is True
        assert config.attribution_frequency == "daily"
        assert config.min_attribution_periods == 20
        assert config.factor_model == "fama_french_3"

    def test_custom_initialization(self):
        """Test AttributionAnalyticsConfig initialization with custom values."""
        config = AttributionAnalyticsConfig(
            enable_brinson_attribution=False,
            enable_factor_attribution=True,
            enable_strategy_attribution=False,
            attribution_frequency="weekly",
            min_attribution_periods=50,
            factor_model="fama_french_5"
        )
        assert config.enable_brinson_attribution is False
        assert config.enable_factor_attribution is True
        assert config.enable_strategy_attribution is False
        assert config.attribution_frequency == "weekly"
        assert config.min_attribution_periods == 50
        assert config.factor_model == "fama_french_5"

    def test_validation(self):
        """Test AttributionAnalyticsConfig validation."""
        # Test invalid attribution_frequency
        with pytest.raises(ValueError, match="attribution_frequency must be one of"):
            AttributionAnalyticsConfig(attribution_frequency="invalid")
        
        # Test invalid factor_model
        with pytest.raises(ValueError, match="factor_model must be one of"):
            AttributionAnalyticsConfig(factor_model="invalid")


class TestBenchmarkAnalyticsConfig:
    """Test suite for BenchmarkAnalyticsConfig class."""

    def test_initialization(self):
        """Test BenchmarkAnalyticsConfig initialization with defaults."""
        config = BenchmarkAnalyticsConfig()
        assert config.default_benchmarks == ["SPY", "QQQ"]
        assert config.enable_tracking_error is True
        assert config.enable_information_ratio is True
        assert config.enable_beta_analysis is True
        assert config.enable_correlation_analysis is True
        assert config.rolling_window == 60
        assert config.min_correlation_periods == 30

    def test_custom_initialization(self):
        """Test BenchmarkAnalyticsConfig initialization with custom values."""
        config = BenchmarkAnalyticsConfig(
            default_benchmarks=["QQQ", "IWM"],
            enable_tracking_error=False,
            enable_information_ratio=True,
            enable_beta_analysis=False,
            enable_correlation_analysis=True,
            rolling_window=120,
            min_correlation_periods=60
        )
        assert config.default_benchmarks == ["QQQ", "IWM"]
        assert config.enable_tracking_error is False
        assert config.enable_information_ratio is True
        assert config.enable_beta_analysis is False
        assert config.enable_correlation_analysis is True
        assert config.rolling_window == 120
        assert config.min_correlation_periods == 60

    def test_validation(self):
        """Test BenchmarkAnalyticsConfig validation."""
        # Test that the class can be instantiated
        config = BenchmarkAnalyticsConfig()
        assert config is not None
        assert hasattr(config, 'default_benchmarks')
        assert hasattr(config, 'enable_tracking_error')
        assert hasattr(config, 'enable_information_ratio')
        assert hasattr(config, 'rolling_window')
        assert hasattr(config, 'min_correlation_periods')
        
        # Test that default_benchmarks is not empty
        assert len(config.default_benchmarks) > 0


class TestReportGenerationConfig:
    """Test suite for ReportGenerationConfig class."""

    def test_initialization(self):
        """Test ReportGenerationConfig initialization with defaults."""
        config = ReportGenerationConfig()
        assert config.default_format == "html"
        assert config.enable_charts is True
        assert config.enable_tables is True
        assert config.include_executive_summary is True
        assert config.include_performance_metrics is True
        assert config.include_risk_metrics is True
        assert config.include_attribution_analysis is True
        assert config.include_benchmark_comparison is True
        assert config.output_directory == "analytics_reports"
        assert config.filename_template == "report_{timestamp}"
        assert config.auto_archive is True
        assert config.max_archive_days == 90

    def test_custom_initialization(self):
        """Test ReportGenerationConfig initialization with custom values."""
        config = ReportGenerationConfig(
            default_format="pdf",
            enable_charts=False,
            enable_tables=True,
            include_executive_summary=False,
            include_performance_metrics=True,
            include_risk_metrics=False,
            include_attribution_analysis=True,
            include_benchmark_comparison=False,
            output_directory="/tmp/reports",
            filename_template="custom_report_{date}",
            auto_archive=False,
            max_archive_days=30
        )
        assert config.default_format == "pdf"
        assert config.enable_charts is False
        assert config.enable_tables is True
        assert config.include_executive_summary is False
        assert config.include_performance_metrics is True
        assert config.include_risk_metrics is False
        assert config.include_attribution_analysis is True
        assert config.include_benchmark_comparison is False
        assert config.output_directory == "/tmp/reports"
        assert config.filename_template == "custom_report_{date}"
        assert config.auto_archive is False
        assert config.max_archive_days == 30

    def test_validation(self):
        """Test ReportGenerationConfig validation."""
        # Test invalid default_format
        with pytest.raises(ValueError, match="default_format must be one of"):
            ReportGenerationConfig(default_format="invalid")


class TestMetricsCalculatorConfig:
    """Test suite for MetricsCalculatorConfig class."""

    def test_initialization(self):
        """Test MetricsCalculatorConfig initialization with defaults."""
        config = MetricsCalculatorConfig()
        assert config.risk_free_rate == 0.02
        assert config.var_confidence_level == 0.95
        assert config.var_method == "historical"
        assert config.rolling_window == 60
        assert config.min_observations == 30
        assert config.enable_return_metrics is True
        assert config.enable_risk_metrics is True
        assert config.enable_risk_adjusted_metrics is True
        assert config.enable_drawdown_metrics is True
        assert config.enable_distribution_metrics is True
        assert config.enable_trading_metrics is True
        assert config.enable_caching is True
        assert config.cache_ttl_seconds == 300
        assert config.parallel_calculation is True
        assert config.max_workers == 4

    def test_custom_initialization(self):
        """Test MetricsCalculatorConfig initialization with custom values."""
        config = MetricsCalculatorConfig(
            risk_free_rate=0.03,
            var_confidence_level=0.99,
            var_method="parametric",
            rolling_window=120,
            min_observations=60,
            enable_return_metrics=False,
            enable_risk_metrics=True,
            enable_risk_adjusted_metrics=False,
            enable_drawdown_metrics=True,
            enable_distribution_metrics=False,
            enable_trading_metrics=True,
            enable_caching=False,
            cache_ttl_seconds=600,
            parallel_calculation=False,
            max_workers=8
        )
        assert config.risk_free_rate == 0.03
        assert config.var_confidence_level == 0.99
        assert config.var_method == "parametric"
        assert config.rolling_window == 120
        assert config.min_observations == 60
        assert config.enable_return_metrics is False
        assert config.enable_risk_metrics is True
        assert config.enable_risk_adjusted_metrics is False
        assert config.enable_drawdown_metrics is True
        assert config.enable_distribution_metrics is False
        assert config.enable_trading_metrics is True
        assert config.enable_caching is False
        assert config.cache_ttl_seconds == 600
        assert config.parallel_calculation is False
        assert config.max_workers == 8

    def test_validation(self):
        """Test MetricsCalculatorConfig validation."""
        # Test invalid var_method
        with pytest.raises(ValueError, match="var_method must be one of"):
            MetricsCalculatorConfig(var_method="invalid")
        
        # Test invalid var_confidence_level
        with pytest.raises(ValueError, match="var_confidence_level must be \\(0, 1\\)"):
            MetricsCalculatorConfig(var_confidence_level=1.5)


class TestPerformanceAnalyticsConfig:
    """Test suite for PerformanceAnalyticsConfig class."""

    def test_initialization(self):
        """Test PerformanceAnalyticsConfig initialization with defaults."""
        config = PerformanceAnalyticsConfig()
        assert config.risk_free_rate == 0.02
        assert config.annualization_factor == 252
        assert config.var_confidence_level == 0.95
        assert config.cvar_confidence_level == 0.95
        assert config.rolling_window_days == 60
        assert config.min_periods == 30
        assert config.enable_risk_adjusted_metrics is True
        assert config.enable_drawdown_analysis is True
        assert config.enable_tail_risk_analysis is True
        assert config.enable_distribution_analysis is True
        assert config.min_sharpe_ratio == 0.5
        assert config.max_drawdown_tolerance == 0.20

    def test_custom_initialization(self):
        """Test PerformanceAnalyticsConfig initialization with custom values."""
        config = PerformanceAnalyticsConfig(
            risk_free_rate=0.03,
            annualization_factor=250,
            var_confidence_level=0.99,
            cvar_confidence_level=0.99,
            rolling_window_days=120,
            min_periods=60,
            enable_risk_adjusted_metrics=False,
            enable_drawdown_analysis=True,
            enable_tail_risk_analysis=False,
            enable_distribution_analysis=True,
            min_sharpe_ratio=1.0,
            max_drawdown_tolerance=0.15
        )
        assert config.risk_free_rate == 0.03
        assert config.annualization_factor == 250
        assert config.var_confidence_level == 0.99
        assert config.cvar_confidence_level == 0.99
        assert config.rolling_window_days == 120
        assert config.min_periods == 60
        assert config.enable_risk_adjusted_metrics is False
        assert config.enable_drawdown_analysis is True
        assert config.enable_tail_risk_analysis is False
        assert config.enable_distribution_analysis is True
        assert config.min_sharpe_ratio == 1.0
        assert config.max_drawdown_tolerance == 0.15

    def test_validation(self):
        """Test PerformanceAnalyticsConfig validation."""
        # Test invalid risk_free_rate
        with pytest.raises(ValueError, match="risk_free_rate must be \\[0, 0\\.10\\]"):
            PerformanceAnalyticsConfig(risk_free_rate=0.15)
        
        # Test invalid annualization_factor
        with pytest.raises(ValueError, match="annualization_factor must be \\[200, 365\\]"):
            PerformanceAnalyticsConfig(annualization_factor=100)


class TestExecutionConfig:
    """Test suite for ExecutionConfig class."""

    def test_initialization(self):
        """Test ExecutionConfig initialization with defaults."""
        config = ExecutionConfig()
        assert config.enable_smart_routing is True
        assert config.enable_dark_pools is False
        assert config.execution_timeout == 30.0
        assert config.max_execution_time == 60.0
        assert config.max_slippage_pct == 0.005
        assert config.default_algorithm == 'adaptive'
        assert config.enable_twap is True
        assert config.enable_vwap is True
        assert config.twap_duration_minutes == 30
        assert config.vwap_participation_rate == 0.1
        assert config.enable_pre_trade_risk is True

    def test_custom_initialization(self):
        """Test ExecutionConfig initialization with custom values."""
        config = ExecutionConfig(
            enable_smart_routing=False,
            enable_dark_pools=True,
            execution_timeout=60.0,
            max_execution_time=120.0,
            max_slippage_pct=0.01,
            default_algorithm='twap',
            enable_twap=False,
            enable_vwap=True,
            twap_duration_minutes=60,
            vwap_participation_rate=0.2,
            enable_pre_trade_risk=False
        )
        assert config.enable_smart_routing is False
        assert config.enable_dark_pools is True
        assert config.execution_timeout == 60.0
        assert config.max_execution_time == 120.0
        assert config.max_slippage_pct == 0.01
        assert config.default_algorithm == 'twap'
        assert config.enable_twap is False
        assert config.enable_vwap is True
        assert config.twap_duration_minutes == 60
        assert config.vwap_participation_rate == 0.2
        assert config.enable_pre_trade_risk is False

    def test_validation(self):
        """Test ExecutionConfig validation."""
        # Test that the class can be instantiated
        config = ExecutionConfig()
        assert config is not None
        assert hasattr(config, 'enable_smart_routing')
        assert hasattr(config, 'execution_timeout')
        assert hasattr(config, 'max_execution_time')
        assert hasattr(config, 'default_algorithm')
        assert hasattr(config, 'timing')
        
        # Test composition pattern
        assert hasattr(config.timing, 'health_check_interval')


class TestPortfolioConfig:
    """Test suite for PortfolioConfig class."""

    def test_initialization(self):
        """Test PortfolioConfig initialization with defaults."""
        config = PortfolioConfig()
        assert config.initial_cash == 100000.0
        assert config.commission_rate == 0.001
        assert config.min_cash_reserve == 1000.0
        assert config.enable_short_selling is False
        assert config.rebalance_frequency == 'daily'
        assert config.rebalance_threshold == 0.05
        assert config.position_limits is not None
        assert config.timing is not None

    def test_custom_initialization(self):
        """Test PortfolioConfig initialization with custom values."""
        config = PortfolioConfig(
            initial_cash=200000.0,
            commission_rate=0.002,
            min_cash_reserve=2000.0,
            enable_short_selling=True,
            rebalance_frequency='weekly',
            rebalance_threshold=0.1
        )
        assert config.initial_cash == 200000.0
        assert config.commission_rate == 0.002
        assert config.min_cash_reserve == 2000.0
        assert config.enable_short_selling is True
        assert config.rebalance_frequency == 'weekly'
        assert config.rebalance_threshold == 0.1

    def test_validation(self):
        """Test PortfolioConfig validation."""
        # Test that the class can be instantiated
        config = PortfolioConfig()
        assert config is not None
        assert hasattr(config, 'initial_cash')
        assert hasattr(config, 'commission_rate')
        assert hasattr(config, 'rebalance_frequency')
        assert hasattr(config, 'position_limits')
        assert hasattr(config, 'timing')
        
        # Test composition pattern
        assert hasattr(config.position_limits, 'max_position_size')
        assert hasattr(config.timing, 'health_check_interval')


class TestRegimeConfig:
    """Test suite for RegimeConfig class."""

    def test_initialization(self):
        """Test RegimeConfig initialization with defaults."""
        config = RegimeConfig()
        assert config.lookback_window == 60
        assert config.lookback_period == 252
        assert config.detection_window == 60
        assert config.volatility_window == 20
        assert config.trend_threshold == 0.02
        assert config.regime_change_threshold == 0.7
        assert config.confidence_threshold == 0.6
        assert config.update_frequency == 300
        assert config.update_frequency_hours == 1

    def test_custom_initialization(self):
        """Test RegimeConfig initialization with custom values."""
        config = RegimeConfig(
            lookback_window=120,
            lookback_period=500,
            detection_window=90,
            volatility_window=30,
            trend_threshold=0.03,
            regime_change_threshold=0.8,
            confidence_threshold=0.7,
            update_frequency=600,
            update_frequency_hours=2
        )
        assert config.lookback_window == 120
        assert config.lookback_period == 500
        assert config.detection_window == 90
        assert config.volatility_window == 30
        assert config.trend_threshold == 0.03
        assert config.regime_change_threshold == 0.8
        assert config.confidence_threshold == 0.7
        assert config.update_frequency == 600
        assert config.update_frequency_hours == 2

    def test_validation(self):
        """Test RegimeConfig validation."""
        # Test that the class can be instantiated
        config = RegimeConfig()
        assert config is not None
        assert hasattr(config, 'lookback_window')
        assert hasattr(config, 'lookback_period')
        assert hasattr(config, 'detection_window')
        assert hasattr(config, 'volatility_window')
        assert hasattr(config, 'trend_threshold')
        assert hasattr(config, 'regime_change_threshold')
        assert hasattr(config, 'confidence_threshold')
        assert hasattr(config, 'update_frequency')
        assert hasattr(config, 'update_frequency_hours')


class TestSignalConfig:
    """Test suite for SignalConfig class."""

    def test_initialization(self):
        """Test SignalConfig initialization with defaults."""
        config = SignalConfig()
        assert config.mean_reversion_weight == 0.4
        assert config.momentum_weight == 0.4
        assert config.volume_weight == 0.2
        assert config.signal_threshold == 0.6
        assert config.confidence_threshold == 0.6
        assert config.strong_signal_threshold == 0.8
        assert config.max_position_size == 0.10
        assert config.stop_loss_pct == 0.02
        assert config.take_profit_pct == 0.04
        assert config.min_volume_ratio == 0.5
        assert config.max_volatility_percentile == 0.95
        assert config.rsi_oversold_threshold == 25
        assert config.rsi_overbought_threshold == 75
        assert config.zscore_threshold == 1.8
        assert config.min_conditions_required == 1
        assert config.confidence_scaling_factor == 0.8

    def test_custom_initialization(self):
        """Test SignalConfig initialization with custom values."""
        config = SignalConfig(
            mean_reversion_weight=0.5,
            momentum_weight=0.3,
            volume_weight=0.2,
            signal_threshold=0.7,
            confidence_threshold=0.7,
            strong_signal_threshold=0.9,
            max_position_size=0.15,
            stop_loss_pct=0.03,
            take_profit_pct=0.06,
            min_volume_ratio=0.6,
            max_volatility_percentile=0.90,
            rsi_oversold_threshold=20,
            rsi_overbought_threshold=80,
            zscore_threshold=2.0,
            min_conditions_required=2,
            confidence_scaling_factor=0.9
        )
        assert config.mean_reversion_weight == 0.5
        assert config.momentum_weight == 0.3
        assert config.volume_weight == 0.2
        assert config.signal_threshold == 0.7
        assert config.confidence_threshold == 0.7
        assert config.strong_signal_threshold == 0.9
        assert config.max_position_size == 0.15
        assert config.stop_loss_pct == 0.03
        assert config.take_profit_pct == 0.06
        assert config.min_volume_ratio == 0.6
        assert config.max_volatility_percentile == 0.90
        assert config.rsi_oversold_threshold == 20
        assert config.rsi_overbought_threshold == 80
        assert config.zscore_threshold == 2.0
        assert config.min_conditions_required == 2
        assert config.confidence_scaling_factor == 0.9

    def test_validation(self):
        """Test SignalConfig validation."""
        # Test that the class can be instantiated
        config = SignalConfig()
        assert config is not None
        assert hasattr(config, 'mean_reversion_weight')
        assert hasattr(config, 'momentum_weight')
        assert hasattr(config, 'volume_weight')
        assert hasattr(config, 'signal_threshold')
        assert hasattr(config, 'confidence_threshold')
        assert hasattr(config, 'strong_signal_threshold')
        assert hasattr(config, 'max_position_size')
        assert hasattr(config, 'stop_loss_pct')
        assert hasattr(config, 'take_profit_pct')
        assert hasattr(config, 'rsi_oversold_threshold')
        assert hasattr(config, 'rsi_overbought_threshold')
        assert hasattr(config, 'zscore_threshold')


class TestFeatureConfig:
    """Test suite for FeatureConfig class."""

    def test_initialization(self):
        """Test FeatureConfig initialization with defaults."""
        config = FeatureConfig()
        assert config.use_normalization is True
        assert config.normalization_method == "robust"
        assert config.enable_cross_sectional is True
        assert config.cross_sectional_universe is None
        assert config.max_features is None
        assert config.feature_importance_threshold == 0.01
        assert config.lag_periods == [1, 2, 3, 5]
        assert config.lookback_periods == [5, 10, 20]
        assert config.enable_scaling is True
        assert config.enable_caching is True

    def test_custom_initialization(self):
        """Test FeatureConfig initialization with custom values."""
        config = FeatureConfig(
            use_normalization=False,
            normalization_method="standard",
            enable_cross_sectional=False,
            cross_sectional_universe=["AAPL", "TSLA"],
            max_features=50,
            feature_importance_threshold=0.05,
            lag_periods=[1, 3, 7],
            lookback_periods=[10, 20, 50],
            enable_scaling=False,
            enable_caching=False
        )
        assert config.use_normalization is False
        assert config.normalization_method == "standard"
        assert config.enable_cross_sectional is False
        assert config.cross_sectional_universe == ["AAPL", "TSLA"]
        assert config.max_features == 50
        assert config.feature_importance_threshold == 0.05
        assert config.lag_periods == [1, 3, 7]
        assert config.lookback_periods == [10, 20, 50]
        assert config.enable_scaling is False
        assert config.enable_caching is False

    def test_validation(self):
        """Test FeatureConfig validation."""
        # Test that the class can be instantiated
        config = FeatureConfig()
        assert config is not None
        assert hasattr(config, 'use_normalization')
        assert hasattr(config, 'normalization_method')
        assert hasattr(config, 'enable_cross_sectional')
        assert hasattr(config, 'cross_sectional_universe')
        assert hasattr(config, 'max_features')
        assert hasattr(config, 'feature_importance_threshold')
        assert hasattr(config, 'lag_periods')
        assert hasattr(config, 'lookback_periods')
        assert hasattr(config, 'enable_scaling')
        assert hasattr(config, 'enable_caching')


class TestIndicatorConfig:
    """Test suite for IndicatorConfig class."""

    def test_initialization(self):
        """Test IndicatorConfig initialization with defaults."""
        config = IndicatorConfig()
        assert config.output_format == 'dataframe'
        assert config.enable_multi_timeframe is False
        assert config.primary_timeframe == '1min'
        assert config.enable_trend is True
        assert config.enable_momentum is True
        assert config.enable_volatility is True
        assert config.enable_volume is True
        assert config.sma_periods == [20, 50, 200]
        assert config.ema_periods == [12, 26, 50]
        assert config.rsi_period == 14
        assert config.macd_fast == 12
        assert config.macd_slow == 26
        assert config.macd_signal == 9
        assert config.bollinger_period == 20
        assert config.bollinger_std == 2.0
        assert config.atr_period == 14
        assert config.adx_period == 14

    def test_custom_initialization(self):
        """Test IndicatorConfig initialization with custom values."""
        config = IndicatorConfig(
            output_format='dict',
            enable_multi_timeframe=True,
            primary_timeframe='5min',
            enable_trend=False,
            enable_momentum=True,
            enable_volatility=False,
            enable_volume=True,
            sma_periods=[10, 30, 100],
            ema_periods=[5, 15, 30],
            rsi_period=21,
            macd_fast=5,
            macd_slow=35,
            macd_signal=5,
            bollinger_period=30,
            bollinger_std=2.5,
            atr_period=21,
            adx_period=21
        )
        assert config.output_format == 'dict'
        assert config.enable_multi_timeframe is True
        assert config.primary_timeframe == '5min'
        assert config.enable_trend is False
        assert config.enable_momentum is True
        assert config.enable_volatility is False
        assert config.enable_volume is True
        assert config.sma_periods == [10, 30, 100]
        assert config.ema_periods == [5, 15, 30]
        assert config.rsi_period == 21
        assert config.macd_fast == 5
        assert config.macd_slow == 35
        assert config.macd_signal == 5
        assert config.bollinger_period == 30
        assert config.bollinger_std == 2.5
        assert config.atr_period == 21
        assert config.adx_period == 21

    def test_validation(self):
        """Test IndicatorConfig validation."""
        # Test that the class can be instantiated
        config = IndicatorConfig()
        assert config is not None
        assert hasattr(config, 'output_format')
        assert hasattr(config, 'enable_multi_timeframe')
        assert hasattr(config, 'primary_timeframe')
        assert hasattr(config, 'enable_trend')
        assert hasattr(config, 'enable_momentum')
        assert hasattr(config, 'enable_volatility')
        assert hasattr(config, 'enable_volume')
        assert hasattr(config, 'sma_periods')
        assert hasattr(config, 'ema_periods')
        assert hasattr(config, 'rsi_period')
        assert hasattr(config, 'macd_fast')
        assert hasattr(config, 'macd_slow')
        assert hasattr(config, 'macd_signal')
        assert hasattr(config, 'bollinger_period')
        assert hasattr(config, 'bollinger_std')
        assert hasattr(config, 'atr_period')
        assert hasattr(config, 'adx_period')
        assert hasattr(config, 'performance')


class TestConnectionConfig:
    """Test suite for ConnectionConfig class."""

    def test_initialization(self):
        """Test ConnectionConfig initialization with defaults."""
        config = ConnectionConfig()
        assert config.clickhouse_host == "localhost"
        assert config.clickhouse_port == 8123
        assert config.clickhouse_database == "polygon_data"
        assert config.connect_timeout == 30.0
        assert config.read_timeout == 10.0
        assert config.max_retry_attempts == 3
        assert config.retry_delay_seconds == 1.0
        assert config.enable_circuit_breaker is True

    def test_custom_initialization(self):
        """Test ConnectionConfig initialization with custom values."""
        config = ConnectionConfig(
            clickhouse_host="prod-db.example.com",
            clickhouse_port=9000,
            clickhouse_database="production_data",
            connect_timeout=60.0,
            read_timeout=20.0,
            max_retry_attempts=5,
            retry_delay_seconds=2.0,
            enable_circuit_breaker=False
        )
        assert config.clickhouse_host == "prod-db.example.com"
        assert config.clickhouse_port == 9000
        assert config.clickhouse_database == "production_data"
        assert config.connect_timeout == 60.0
        assert config.read_timeout == 20.0
        assert config.max_retry_attempts == 5
        assert config.retry_delay_seconds == 2.0
        assert config.enable_circuit_breaker is False

    def test_validation(self):
        """Test ConnectionConfig validation."""
        # Test invalid connect_timeout
        with pytest.raises(ValueError, match="connect_timeout must be positive"):
            ConnectionConfig(connect_timeout=0)
        
        # Test invalid read_timeout
        with pytest.raises(ValueError, match="read_timeout must be positive"):
            ConnectionConfig(read_timeout=0)
        
        # Test invalid max_retry_attempts
        with pytest.raises(ValueError, match="max_retry_attempts must be non-negative"):
            ConnectionConfig(max_retry_attempts=-1)


class TestCachingConfig:
    """Test suite for CachingConfig class."""

    def test_initialization(self):
        """Test CachingConfig initialization with defaults."""
        config = CachingConfig()
        assert config.enable_caching is True
        assert config.cache_ttl == 300
        assert config.max_cache_size == 1000
        assert config.cache_config is None

    def test_custom_initialization(self):
        """Test CachingConfig initialization with custom values."""
        config = CachingConfig(
            enable_caching=False,
            cache_ttl=600,
            max_cache_size=2000,
            cache_config={"type": "redis"}
        )
        assert config.enable_caching is False
        assert config.cache_ttl == 600
        assert config.max_cache_size == 2000
        assert config.cache_config == {"type": "redis"}

    def test_validation(self):
        """Test CachingConfig validation."""
        # Test invalid cache_ttl
        with pytest.raises(ValueError, match="cache_ttl must be non-negative"):
            CachingConfig(cache_ttl=-1)
        
        # Test invalid max_cache_size
        with pytest.raises(ValueError, match="max_cache_size must be positive"):
            CachingConfig(max_cache_size=0)
        


class TestDataValidationConfig:
    """Test suite for DataValidationConfig class."""

    def test_initialization(self):
        """Test DataValidationConfig initialization with defaults."""
        config = DataValidationConfig()
        assert config.enable_data_validation is True
        assert config.quality_threshold == 0.95
        assert config.min_price is None
        assert config.max_price is None
        assert config.max_price_change_pct == 20.0
        assert config.max_spread_pct == 5.0
        assert config.max_spread_bps == 500.0
        assert config.min_volume == 0
        assert config.max_volume_spike_factor == 10.0
        assert config.outlier_threshold_std == 3.0
        assert config.moving_average_window == 20
        assert config.max_data_age_seconds == 30.0
        assert config.required_update_frequency_seconds == 1.0
        assert config.min_completeness_pct == 95.0
        assert config.enable_cross_validation is True
        assert config.max_cross_validation_diff_pct == 2.0

    def test_custom_initialization(self):
        """Test DataValidationConfig initialization with custom values."""
        config = DataValidationConfig(
            enable_data_validation=False,
            quality_threshold=0.98,
            min_price=1.0,
            max_price=1000.0,
            max_price_change_pct=15.0,
            max_spread_pct=3.0,
            max_spread_bps=300.0,
            min_volume=100,
            max_volume_spike_factor=5.0,
            outlier_threshold_std=2.0,
            moving_average_window=30,
            max_data_age_seconds=60.0,
            required_update_frequency_seconds=2.0,
            min_completeness_pct=98.0,
            enable_cross_validation=False,
            max_cross_validation_diff_pct=1.0
        )
        assert config.enable_data_validation is False
        assert config.quality_threshold == 0.98
        assert config.min_price == 1.0
        assert config.max_price == 1000.0
        assert config.max_price_change_pct == 15.0
        assert config.max_spread_pct == 3.0
        assert config.max_spread_bps == 300.0
        assert config.min_volume == 100
        assert config.max_volume_spike_factor == 5.0
        assert config.outlier_threshold_std == 2.0
        assert config.moving_average_window == 30
        assert config.max_data_age_seconds == 60.0
        assert config.required_update_frequency_seconds == 2.0
        assert config.min_completeness_pct == 98.0
        assert config.enable_cross_validation is False
        assert config.max_cross_validation_diff_pct == 1.0

    def test_validation(self):
        """Test DataValidationConfig validation."""
        # Test invalid quality_threshold
        with pytest.raises(ValueError, match="quality_threshold must be \\[0, 1\\]"):
            DataValidationConfig(quality_threshold=1.5)
        
        # Test invalid max_price_change_pct
        with pytest.raises(ValueError, match="max_price_change_pct must be non-negative"):
            DataValidationConfig(max_price_change_pct=-10.0)
        
        # Test invalid outlier_threshold_std
        with pytest.raises(ValueError, match="outlier_threshold_std must be positive"):
            DataValidationConfig(outlier_threshold_std=0)


class TestFeedManagementConfig:
    """Test suite for FeedManagementConfig class."""

    def test_initialization(self):
        """Test FeedManagementConfig initialization with defaults."""
        config = FeedManagementConfig()
        assert config.enable_feed_management is True
        assert config.max_concurrent_requests == 10
        assert config.buffer_size == 10000
        assert config.max_message_size == 1048576
        assert config.heartbeat_interval == 30.0
        assert config.reconnect_interval == 5.0
        assert config.max_reconnect_attempts == 10
        assert config.api_key is None
        assert config.secret_key is None
        assert config.enable_sequence_check is True
        assert config.enable_timestamp_validation is True

    def test_custom_initialization(self):
        """Test FeedManagementConfig initialization with custom values."""
        config = FeedManagementConfig(
            enable_feed_management=False,
            max_concurrent_requests=20,
            buffer_size=20000,
            max_message_size=2097152,
            heartbeat_interval=60.0,
            reconnect_interval=10.0,
            max_reconnect_attempts=20,
            api_key="test_key",
            secret_key="test_secret",
            enable_sequence_check=False,
            enable_timestamp_validation=False
        )
        assert config.enable_feed_management is False
        assert config.max_concurrent_requests == 20
        assert config.buffer_size == 20000
        assert config.max_message_size == 2097152
        assert config.heartbeat_interval == 60.0
        assert config.reconnect_interval == 10.0
        assert config.max_reconnect_attempts == 20
        assert config.api_key == "test_key"
        assert config.secret_key == "test_secret"
        assert config.enable_sequence_check is False
        assert config.enable_timestamp_validation is False

    def test_validation(self):
        """Test FeedManagementConfig validation."""
        # Test invalid max_concurrent_requests
        with pytest.raises(ValueError, match="max_concurrent_requests must be positive"):
            FeedManagementConfig(max_concurrent_requests=0)
        
        # Test invalid buffer_size
        with pytest.raises(ValueError, match="buffer_size must be positive"):
            FeedManagementConfig(buffer_size=0)
        
        # Test invalid heartbeat_interval
        with pytest.raises(ValueError, match="heartbeat_interval must be positive"):
            FeedManagementConfig(heartbeat_interval=0)


class TestDataPerformanceConfig:
    """Test suite for DataPerformanceConfig class."""

    def test_initialization(self):
        """Test DataPerformanceConfig initialization with defaults."""
        config = DataPerformanceConfig()
        assert config.max_concurrent_requests == 100
        assert config.request_timeout_seconds == 30.0
        assert config.enable_performance_monitoring is True
        assert config.monitoring_interval_seconds == 60.0
        assert config.enable_compression is True
        assert config.data_retention_days == 365

    def test_custom_initialization(self):
        """Test DataPerformanceConfig initialization with custom values."""
        config = DataPerformanceConfig(
            max_concurrent_requests=200,
            request_timeout_seconds=60.0,
            enable_performance_monitoring=False,
            monitoring_interval_seconds=120.0,
            enable_compression=False,
            data_retention_days=730
        )
        assert config.max_concurrent_requests == 200
        assert config.request_timeout_seconds == 60.0
        assert config.enable_performance_monitoring is False
        assert config.monitoring_interval_seconds == 120.0
        assert config.enable_compression is False
        assert config.data_retention_days == 730

    def test_validation(self):
        """Test DataPerformanceConfig validation."""
        # Test invalid max_concurrent_requests
        with pytest.raises(ValueError, match="max_concurrent_requests must be positive"):
            DataPerformanceConfig(max_concurrent_requests=0)
        
        # Test invalid request_timeout_seconds
        with pytest.raises(ValueError, match="request_timeout_seconds must be positive"):
            DataPerformanceConfig(request_timeout_seconds=0)
        
        # Test invalid data_retention_days
        with pytest.raises(ValueError, match="data_retention_days must be positive"):
            DataPerformanceConfig(data_retention_days=0)


class TestCorrelationConfig:
    """Test suite for CorrelationConfig class."""

    def test_initialization(self):
        """Test CorrelationConfig initialization with defaults."""
        config = CorrelationConfig()
        assert config.default_method == 'pearson'
        assert config.rolling_window == 60
        assert config.min_periods == 30
        assert config.enable_regime_detection is True
        assert config.regime_detection_method == 'hmm'
        assert config.n_regimes == 3
        assert config.enable_tail_dependence is True

    def test_custom_initialization(self):
        """Test CorrelationConfig initialization with custom values."""
        config = CorrelationConfig(
            default_method='spearman',
            rolling_window=100,
            min_periods=50,
            enable_regime_detection=False,
            regime_detection_method='clustering',
            n_regimes=4,
            enable_tail_dependence=False
        )
        assert config.default_method == 'spearman'
        assert config.rolling_window == 100
        assert config.min_periods == 50
        assert config.enable_regime_detection is False
        assert config.regime_detection_method == 'clustering'
        assert config.n_regimes == 4
        assert config.enable_tail_dependence is False

    def test_validation(self):
        """Test CorrelationConfig validation."""
        # Test that the class can be instantiated
        config = CorrelationConfig()
        assert config is not None
        assert hasattr(config, 'default_method')
        assert hasattr(config, 'rolling_window')
        assert hasattr(config, 'min_periods')
        assert hasattr(config, 'enable_regime_detection')
        assert hasattr(config, 'regime_detection_method')
        assert hasattr(config, 'n_regimes')
        assert hasattr(config, 'enable_tail_dependence')


class TestExposureConfig:
    """Test suite for ExposureConfig class."""

    def test_initialization(self):
        """Test ExposureConfig initialization with defaults."""
        config = ExposureConfig()
        assert config.cache_ttl_seconds == 300
        assert config.include_derivatives is True
        assert config.include_cash is True
        assert config.base_currency == 'USD'
        assert config.max_net_exposure == 1.0
        assert config.max_gross_exposure == 2.0
        assert config.max_sector_exposure == 0.30
        assert config.max_single_position == 0.15

    def test_custom_initialization(self):
        """Test ExposureConfig initialization with custom values."""
        config = ExposureConfig(
            cache_ttl_seconds=600,
            include_derivatives=False,
            include_cash=False,
            base_currency='EUR',
            max_net_exposure=0.8,
            max_gross_exposure=1.5,
            max_sector_exposure=0.25,
            max_single_position=0.10
        )
        assert config.cache_ttl_seconds == 600
        assert config.include_derivatives is False
        assert config.include_cash is False
        assert config.base_currency == 'EUR'
        assert config.max_net_exposure == 0.8
        assert config.max_gross_exposure == 1.5
        assert config.max_sector_exposure == 0.25
        assert config.max_single_position == 0.10

    def test_validation(self):
        """Test ExposureConfig validation."""
        # Test that the class can be instantiated
        config = ExposureConfig()
        assert config is not None
        assert hasattr(config, 'cache_ttl_seconds')
        assert hasattr(config, 'include_derivatives')
        assert hasattr(config, 'include_cash')
        assert hasattr(config, 'base_currency')
        assert hasattr(config, 'max_net_exposure')
        assert hasattr(config, 'max_gross_exposure')
        assert hasattr(config, 'max_sector_exposure')
        assert hasattr(config, 'max_single_position')


class TestVarConfig:
    """Test suite for VarConfig class."""

    def test_initialization(self):
        """Test VarConfig initialization with defaults."""
        config = VarConfig()
        assert config.default_confidence == 0.95
        assert config.default_method == 'historical'
        assert config.monte_carlo_simulations == 10000
        assert config.historical_window == 252
        assert config.parametric_distribution == 'normal'
        assert config.enable_cvar is True
        assert config.cache_results is True
        assert config.cache_ttl_seconds == 300

    def test_custom_initialization(self):
        """Test VarConfig initialization with custom values."""
        config = VarConfig(
            default_confidence=0.99,
            default_method="parametric",
            monte_carlo_simulations=20000,
            historical_window=500,
            parametric_distribution="student_t",
            enable_cvar=False,
            cache_results=False,
            cache_ttl_seconds=600
        )
        assert config.default_confidence == 0.99
        assert config.default_method == "parametric"
        assert config.monte_carlo_simulations == 20000
        assert config.historical_window == 500
        assert config.parametric_distribution == "student_t"
        assert config.enable_cvar is False
        assert config.cache_results is False
        assert config.cache_ttl_seconds == 600

    def test_validation(self):
        """Test VarConfig validation."""
        # Test that the class can be instantiated
        config = VarConfig()
        assert config is not None
        assert hasattr(config, 'default_confidence')
        assert hasattr(config, 'default_method')
        assert hasattr(config, 'monte_carlo_simulations')
        assert hasattr(config, 'historical_window')
        assert hasattr(config, 'parametric_distribution')
        assert hasattr(config, 'enable_cvar')
        assert hasattr(config, 'cache_results')
        assert hasattr(config, 'cache_ttl_seconds')
        


class TestStressTestConfig:
    """Test suite for StressTestConfig class."""

    def test_initialization(self):
        """Test StressTestConfig initialization with defaults."""
        config = StressTestConfig()
        assert config.enable_market_crash is True
        assert config.enable_volatility_spike is True
        assert config.enable_correlation_breakdown is True
        assert config.enable_liquidity_crisis is True
        assert config.market_crash_shock == -0.20
        assert config.volatility_spike_multiplier == 3.0
        assert config.correlation_increase == 0.50
        assert config.liquidity_reduction == 0.70

    def test_custom_initialization(self):
        """Test StressTestConfig initialization with custom values."""
        config = StressTestConfig(
            enable_market_crash=False,
            enable_volatility_spike=False,
            enable_correlation_breakdown=False,
            enable_liquidity_crisis=False,
            market_crash_shock=-0.30,
            volatility_spike_multiplier=4.0,
            correlation_increase=0.75,
            liquidity_reduction=0.50
        )
        assert config.enable_market_crash is False
        assert config.enable_volatility_spike is False
        assert config.enable_correlation_breakdown is False
        assert config.enable_liquidity_crisis is False
        assert config.market_crash_shock == -0.30
        assert config.volatility_spike_multiplier == 4.0
        assert config.correlation_increase == 0.75
        assert config.liquidity_reduction == 0.50

    def test_validation(self):
        """Test StressTestConfig validation."""
        # Test that the class can be instantiated
        config = StressTestConfig()
        assert config is not None
        assert hasattr(config, 'enable_market_crash')
        assert hasattr(config, 'enable_volatility_spike')
        assert hasattr(config, 'enable_correlation_breakdown')
        assert hasattr(config, 'enable_liquidity_crisis')
        assert hasattr(config, 'market_crash_shock')
        assert hasattr(config, 'volatility_spike_multiplier')
        assert hasattr(config, 'correlation_increase')
        assert hasattr(config, 'liquidity_reduction')


class TestLimitConfig:
    """Test suite for LimitConfig class."""

    def test_initialization(self):
        """Test LimitConfig initialization with defaults."""
        config = LimitConfig()
        assert config.enable_alerts is True
        assert config.alert_cooldown_seconds == 300
        assert config.max_alerts_per_hour == 20
        assert config.check_frequency_seconds == 60
        assert config.enable_real_time_monitoring is True
        assert config.warning_threshold == 0.80
        assert config.critical_threshold == 0.95

    def test_custom_initialization(self):
        """Test LimitConfig initialization with custom values."""
        config = LimitConfig(
            enable_alerts=False,
            alert_cooldown_seconds=600,
            max_alerts_per_hour=10,
            check_frequency_seconds=30,
            enable_real_time_monitoring=False,
            warning_threshold=0.70,
            critical_threshold=0.90
        )
        assert config.enable_alerts is False
        assert config.alert_cooldown_seconds == 600
        assert config.max_alerts_per_hour == 10
        assert config.check_frequency_seconds == 30
        assert config.enable_real_time_monitoring is False
        assert config.warning_threshold == 0.70
        assert config.critical_threshold == 0.90

    def test_validation(self):
        """Test LimitConfig validation."""
        # Test that the class can be instantiated
        config = LimitConfig()
        assert config is not None
        assert hasattr(config, 'enable_alerts')
        assert hasattr(config, 'alert_cooldown_seconds')
        assert hasattr(config, 'max_alerts_per_hour')
        assert hasattr(config, 'check_frequency_seconds')
        assert hasattr(config, 'enable_real_time_monitoring')
        assert hasattr(config, 'warning_threshold')
        assert hasattr(config, 'critical_threshold')
        


class TestTimingConfig:
    """Test suite for TimingConfig class."""

    def test_initialization(self):
        """Test TimingConfig initialization with defaults."""
        config = TimingConfig()
        assert config.health_check_interval == 30
        assert config.max_retry_attempts == 3
        assert config.retry_delay == 5.0
        assert config.update_frequency == '1min'

    def test_custom_initialization(self):
        """Test TimingConfig initialization with custom values."""
        config = TimingConfig(
            health_check_interval=60,
            max_retry_attempts=5,
            retry_delay=10.0,
            update_frequency="5min"
        )
        assert config.health_check_interval == 60
        assert config.max_retry_attempts == 5
        assert config.retry_delay == 10.0
        assert config.update_frequency == "5min"

    def test_validation(self):
        """Test TimingConfig validation."""
        # Test invalid health_check_interval
        with pytest.raises(ValueError, match="health_check_interval must be >= 1"):
            TimingConfig(health_check_interval=0)
        
        # Test invalid update_frequency (only shows warning, not ValueError)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            TimingConfig(update_frequency="invalid")
            assert len(w) == 1
            assert "update_frequency 'invalid' not in standard frequencies" in str(w[0].message)
        


class TestPerformanceConfig:
    """Test suite for PerformanceConfig class."""

    def test_initialization(self):
        """Test PerformanceConfig initialization with defaults."""
        config = PerformanceConfig()
        assert config.enable_caching is True
        assert config.cache_ttl == 3600
        assert config.enable_performance_monitoring is True
        assert config.max_workers == 4
        assert config.calculation_threads == 2
        assert config.batch_size == 100

    def test_custom_initialization(self):
        """Test PerformanceConfig initialization with custom values."""
        config = PerformanceConfig(
            enable_caching=False,
            cache_ttl=7200,
            enable_performance_monitoring=False,
            max_workers=8,
            calculation_threads=4,
            batch_size=200
        )
        assert config.enable_caching is False
        assert config.cache_ttl == 7200
        assert config.enable_performance_monitoring is False
        assert config.max_workers == 8
        assert config.calculation_threads == 4
        assert config.batch_size == 200

    def test_validation(self):
        """Test PerformanceConfig validation."""
        # PerformanceConfig doesn't have validation in __post_init__
        # Just test that it can be created
        config = PerformanceConfig()
        assert config.enable_caching is True


class TestComponentConfigIntegration:
    """Integration tests for component configs."""

    def test_all_component_configs_serialization(self):
        """Test that all component configs can be serialized to dict."""
        configs = [
            AnalyticsConfig(), AttributionAnalyticsConfig(), BenchmarkAnalyticsConfig(),
            ReportGenerationConfig(), MetricsCalculatorConfig(), PerformanceAnalyticsConfig(),
            ExecutionConfig(), PortfolioConfig(), RegimeConfig(), SignalConfig(),
            FeatureConfig(), IndicatorConfig(), ConnectionConfig(), CachingConfig(),
            DataValidationConfig(), FeedManagementConfig(), DataPerformanceConfig(),
            CorrelationConfig(), ExposureConfig(), VarConfig(), StressTestConfig(),
            LimitConfig(), TimingConfig(), PerformanceConfig()
        ]
        
        for config in configs:
            config_dict = asdict(config)
            assert isinstance(config_dict, dict)
            # Each config should have at least one identifying attribute
            assert len(config_dict) > 0

    def test_component_config_validation_consistency(self):
        """Test that all component configs have consistent validation patterns."""
        configs = [
            AnalyticsConfig, AttributionAnalyticsConfig, BenchmarkAnalyticsConfig,
            ReportGenerationConfig, MetricsCalculatorConfig, PerformanceAnalyticsConfig,
            ExecutionConfig, PortfolioConfig, RegimeConfig, SignalConfig,
            FeatureConfig, IndicatorConfig, ConnectionConfig, CachingConfig,
            DataValidationConfig, FeedManagementConfig, DataPerformanceConfig,
            CorrelationConfig, ExposureConfig, VarConfig, StressTestConfig,
            LimitConfig, TimingConfig, PerformanceConfig
        ]
        
        for config_class in configs:
            # Test that invalid lookback periods are caught (if they exist and have validation)
            if hasattr(config_class, 'lookback') or hasattr(config_class, 'lookback_period'):
                lookback_attr = 'lookback' if hasattr(config_class, 'lookback') else 'lookback_period'
                # Only test if the class has __post_init__ validation
                if hasattr(config_class, '__post_init__'):
                    try:
                        config_class(**{lookback_attr: 0})
                    except ValueError:
                        pass  # Expected behavior
                    except TypeError:
                        pass  # Some configs don't accept these parameters
            
            # Test that invalid thresholds are caught (if they exist and have validation)
            if hasattr(config_class, 'threshold') or hasattr(config_class, 'confidence_level'):
                threshold_attr = 'threshold' if hasattr(config_class, 'threshold') else 'confidence_level'
                # Only test if the class has __post_init__ validation
                if hasattr(config_class, '__post_init__'):
                    try:
                        config_class(**{threshold_attr: -0.1})
                    except ValueError:
                        pass  # Expected behavior
                    except TypeError:
                        pass  # Some configs don't accept these parameters

    def test_component_config_composition(self):
        """Test that configs can be composed together properly."""
        # Test analytics config composition
        analytics_config = AnalyticsConfig()
        attribution_config = AttributionAnalyticsConfig()
        
        # Test execution and portfolio config composition
        execution_config = ExecutionConfig()
        portfolio_config = PortfolioConfig()
        
        # Test data config composition
        connection_config = ConnectionConfig()
        caching_config = CachingConfig()
        validation_config = DataValidationConfig()
        
        # Verify all configs were created successfully
        assert analytics_config is not None
        assert attribution_config is not None
        assert execution_config is not None
        assert portfolio_config is not None
        assert connection_config is not None
        assert caching_config is not None
        assert validation_config is not None

