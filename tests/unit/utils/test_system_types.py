"""
Unit tests for type_definitions module
"""

import pandas as pd
import numpy as np
from datetime import datetime

# Import all types from type_definitions
from core_engine.type_definitions.regime import (
    RegimeState, RegimeConfig, RegimeSignal
)
from core_engine.type_definitions.data import (
    DataConfig, MarketData
)
from core_engine.type_definitions.analytics import (
    PerformanceMetrics
)
from core_engine.type_definitions.broker import (
    BrokerType, BrokerConfig, PaperBroker
)


class TestRegime:
    """Test regime-related types"""

    def test_regime_state_enum(self):
        """Test RegimeState enum values"""
        assert RegimeState.BULL.value == "bull"
        assert RegimeState.BEAR.value == "bear"
        assert RegimeState.SIDEWAYS.value == "sideways"
        assert RegimeState.HIGH_VOLATILITY.value == "high_volatility"
        assert RegimeState.LOW_VOLATILITY.value == "low_volatility"
        assert RegimeState.UNKNOWN.value == "unknown"

    def test_regime_config_creation(self):
        """Test RegimeConfig creation"""
        config = RegimeConfig(
            lookback_window=20,
            volatility_threshold=0.02,
            trend_threshold=0.05,
            regime_persistence=3,
            use_rsi=True,
            rsi_oversold=30,
            rsi_overbought=70,
            use_bollinger=True,
            bollinger_period=20,
            bollinger_std=2.0
        )

        assert config.lookback_window == 20
        assert config.volatility_threshold == 0.02
        assert config.trend_threshold == 0.05
        assert config.regime_persistence == 3
        assert config.use_rsi is True
        assert config.rsi_oversold == 30
        assert config.rsi_overbought == 70
        assert config.use_bollinger is True
        assert config.bollinger_period == 20
        assert config.bollinger_std == 2.0

    def test_regime_signal_creation(self):
        """Test RegimeSignal creation"""
        timestamp = datetime.now()
        signal = RegimeSignal(
            timestamp=timestamp,
            regime=RegimeState.BULL,
            confidence=0.85,
            indicators={"rsi": 65, "trend": 0.03}
        )

        assert signal.timestamp == timestamp
        assert signal.regime == RegimeState.BULL
        assert signal.confidence == 0.85
        assert signal.indicators["rsi"] == 65
        assert signal.indicators["trend"] == 0.03


class TestData:
    """Test data-related types"""

    def test_data_config_creation(self):
        """Test DataConfig creation"""
        config = DataConfig(
            provider="yahoo",
            update_frequency="1min",
            cache_enabled=True,
            cache_duration=300,
            fill_missing=True,
            validate_data=True,
            outlier_detection=True,
            outlier_threshold=3.0
        )

        assert config.provider == "yahoo"
        assert config.update_frequency == "1min"
        assert config.cache_enabled is True
        assert config.cache_duration == 300
        assert config.fill_missing is True
        assert config.validate_data is True
        assert config.outlier_detection is True
        assert config.outlier_threshold == 3.0

    def test_market_data_creation(self):
        """Test MarketData creation"""
        timestamp = datetime.now()
        data = MarketData(
            symbol="AAPL",
            timestamp=timestamp,
            open=149.0,
            high=152.0,
            low=148.5,
            close=151.0,
            volume=1000000,
            adjusted_close=150.5,
            dividend=0.25,
            split_ratio=1.0
        )

        assert data.symbol == "AAPL"
        assert data.timestamp == timestamp
        assert data.open == 149.0
        assert data.high == 152.0
        assert data.low == 148.5
        assert data.close == 151.0
        assert data.volume == 1000000
        assert data.adjusted_close == 150.5
        assert data.dividend == 0.25
        assert data.split_ratio == 1.0

    def test_market_data_to_dict(self):
        """Test MarketData to_dict method"""
        timestamp = datetime(2023, 1, 1, 12, 0, 0)
        data = MarketData(
            symbol="AAPL",
            timestamp=timestamp,
            open=150.0,
            high=155.0,
            low=149.0,
            close=152.0,
            volume=2000000
        )

        data_dict = data.to_dict()

        assert data_dict["symbol"] == "AAPL"
        assert data_dict["timestamp"] == timestamp
        assert data_dict["open"] == 150.0
        assert data_dict["high"] == 155.0
        assert data_dict["low"] == 149.0
        assert data_dict["close"] == 152.0
        assert data_dict["volume"] == 2000000


class TestAnalytics:
    """Test analytics-related types"""

    def test_performance_metrics_creation(self):
        """Test PerformanceMetrics creation"""
        metrics = PerformanceMetrics(
            total_return=0.25,
            annualized_return=0.18,
            excess_return=0.05,
            volatility=0.22,
            sharpe_ratio=0.82,
            sortino_ratio=1.1,
            max_drawdown=-0.15,
            var_95=-0.03,
            total_trades=150,
            win_rate=0.58,
            avg_win=0.015,
            avg_loss=-0.008,
            profit_factor=1.8,
            calmar_ratio=1.2,
            recovery_factor=2.5
        )

        assert metrics.total_return == 0.25
        assert metrics.annualized_return == 0.18
        assert metrics.excess_return == 0.05
        assert metrics.volatility == 0.22
        assert metrics.sharpe_ratio == 0.82
        assert metrics.sortino_ratio == 1.1
        assert metrics.max_drawdown == -0.15
        assert metrics.var_95 == -0.03
        assert metrics.total_trades == 150
        assert metrics.win_rate == 0.58
        assert metrics.avg_win == 0.015
        assert metrics.avg_loss == -0.008
        assert metrics.profit_factor == 1.8
        assert metrics.calmar_ratio == 1.2
        assert metrics.recovery_factor == 2.5

    def test_performance_metrics_calculate_from_returns(self):
        """Test PerformanceMetrics calculate_from_returns"""
        # Create sample returns
        dates = pd.date_range('2023-01-01', periods=252, freq='D')
        returns = pd.Series(np.random.normal(0.001, 0.02, 252), index=dates)

        metrics = PerformanceMetrics()
        metrics.calculate_from_returns(returns)

        # Check that metrics were calculated
        assert hasattr(metrics, 'total_return')
        assert hasattr(metrics, 'volatility')
        assert hasattr(metrics, 'sharpe_ratio')
        assert hasattr(metrics, 'max_drawdown')


class TestBroker:
    """Test broker-related types"""

    def test_broker_type_enum(self):
        """Test BrokerType enum values"""
        assert BrokerType.PAPER.value == "paper"
        assert BrokerType.INTERACTIVE_BROKERS.value == "ib"
        assert BrokerType.ALPACA.value == "alpaca"
        assert BrokerType.TD_AMERITRADE.value == "td"
        assert BrokerType.CUSTOM.value == "custom"

    def test_broker_config_creation(self):
        """Test BrokerConfig creation"""
        config = BrokerConfig(
            broker_type=BrokerType.PAPER,
            api_key="test_key",
            secret_key="test_secret",
            base_url="https://api.example.com",
            paper_trading=True,
            default_commission=0.001,
            min_commission=1.0,
            max_commission=100.0,
            timeout_seconds=30,
            retry_attempts=3,
            partial_fills_allowed=True
        )

        assert config.broker_type == BrokerType.PAPER
        assert config.api_key == "test_key"
        assert config.secret_key == "test_secret"
        assert config.base_url == "https://api.example.com"
        assert config.paper_trading is True
        assert config.default_commission == 0.001
        assert config.min_commission == 1.0
        assert config.max_commission == 100.0
        assert config.timeout_seconds == 30
        assert config.retry_attempts == 3
        assert config.partial_fills_allowed is True

    def test_paper_broker_creation(self):
        """Test PaperBroker creation"""
        config = BrokerConfig(broker_type=BrokerType.PAPER)
        broker = PaperBroker(config)

        assert broker.config == config
        assert broker.connected is False
        assert hasattr(broker, 'cash')
        assert hasattr(broker, 'positions')
        assert hasattr(broker, 'order_callbacks')
        assert broker.cash == 100000.0  # Default starting cash
