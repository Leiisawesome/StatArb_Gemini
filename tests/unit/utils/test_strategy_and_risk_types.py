"""
Unit tests for type_definitions module
"""

import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import Mock
from typing import List

# Import all types from type_definitions
from core_engine.type_definitions.strategy import (
    StrategyType, StrategyConfig, TradingSignal, StrategyMetrics,
    BaseStrategy, StrategyInterface, StrategyManager
)
from core_engine.type_definitions.risk import (
    RiskLevel, RiskConfig, RiskMetrics, RiskResult, RiskManager
)


class TestStrategy:
    """Test strategy-related types"""

    def test_strategy_type_enum(self):
        """Test StrategyType enum values"""
        assert StrategyType.MEAN_REVERSION.value == "mean_reversion"
        assert StrategyType.MOMENTUM.value == "momentum"
        assert StrategyType.PAIRS_TRADING.value == "pairs_trading"
        assert StrategyType.ARBITRAGE.value == "arbitrage"
        assert StrategyType.CUSTOM.value == "custom"

    def test_strategy_config_creation(self):
        """Test StrategyConfig creation"""
        config = StrategyConfig(
            name="momentum_strategy",
            strategy_type=StrategyType.MOMENTUM,
            symbols=["AAPL", "GOOGL"],
            parameters={"lookback": 20, "threshold": 0.05},
            enabled=True,
            risk_limit=0.1,
            position_limit=0.05
        )

        assert config.name == "momentum_strategy"
        assert config.strategy_type == StrategyType.MOMENTUM
        assert config.symbols == ["AAPL", "GOOGL"]
        assert config.parameters["lookback"] == 20
        assert config.enabled is True
        assert config.risk_limit == 0.1
        assert config.position_limit == 0.05

    def test_trading_signal_creation(self):
        """Test TradingSignal creation"""
        timestamp = datetime.now()
        signal = TradingSignal(
            strategy_id="momentum_001",
            symbol="AAPL",
            signal_type="BUY",
            strength=0.8,
            price=150.0,
            quantity=100,
            timestamp=timestamp,
            metadata={"confidence": 0.9}
        )

        assert signal.strategy_id == "momentum_001"
        assert signal.symbol == "AAPL"
        assert signal.signal_type == "BUY"
        assert signal.strength == 0.8
        assert signal.price == 150.0
        assert signal.quantity == 100
        assert signal.timestamp == timestamp
        assert signal.metadata["confidence"] == 0.9

    def test_trading_signal_properties(self):
        """Test TradingSignal computed properties"""
        buy_signal = TradingSignal("strat_1", "AAPL", "BUY", 0.8)
        sell_signal = TradingSignal("strat_1", "AAPL", "SELL", 0.6)
        hold_signal = TradingSignal("strat_1", "AAPL", "HOLD", 0.3)

        assert buy_signal.is_buy is True
        assert buy_signal.is_sell is False
        assert buy_signal.is_hold is False

        assert sell_signal.is_buy is False
        assert sell_signal.is_sell is True
        assert sell_signal.is_hold is False

        assert hold_signal.is_buy is False
        assert hold_signal.is_sell is False
        assert hold_signal.is_hold is True

    def test_strategy_metrics_creation(self):
        """Test StrategyMetrics creation"""
        metrics = StrategyMetrics(
            strategy_id="test_strategy",
            total_return=0.15,
            sharpe_ratio=1.2,
            max_drawdown=0.08,
            win_rate=0.65,
            total_trades=100,
            profitable_trades=65,
            avg_trade_return=0.0015,
            volatility=0.02,
            var_95=0.03
        )

        assert metrics.strategy_id == "test_strategy"
        assert metrics.total_return == 0.15
        assert metrics.sharpe_ratio == 1.2
        assert metrics.max_drawdown == 0.08
        assert metrics.win_rate == 0.65
        assert metrics.total_trades == 100
        assert metrics.profitable_trades == 65
        assert metrics.avg_trade_return == 0.0015
        assert metrics.volatility == 0.02
        assert metrics.var_95 == 0.03

    def test_strategy_metrics_update_from_returns(self):
        """Test StrategyMetrics update_from_returns"""
        # Create sample returns
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        returns = pd.Series(np.random.normal(0.001, 0.02, 100), index=dates)

        metrics = StrategyMetrics(strategy_id="test")
        metrics.update_from_returns(returns)

        assert metrics.total_return != 0.0
        assert metrics.sharpe_ratio != 0.0
        assert metrics.volatility != 0.0
        assert metrics.max_drawdown <= 0.0  # Should be negative or zero

    def test_base_strategy_initialization(self):
        """Test BaseStrategy initialization"""
        config = StrategyConfig(
            name="test_strategy",
            strategy_type=StrategyType.MOMENTUM,
            symbols=["AAPL"]
        )

        # Create a concrete implementation for testing
        class TestStrategy(BaseStrategy):

            def generate_signals(self, data: pd.DataFrame) -> List[TradingSignal]:
                return []

            def update_state(self, data: pd.DataFrame):
                pass

        strategy = TestStrategy(config)

        assert strategy.config == config
        assert strategy.strategy_id == "test_strategy"
        assert strategy.is_active is True
        assert isinstance(strategy.metrics, StrategyMetrics)
        assert strategy.metrics.strategy_id == "test_strategy"

    def test_strategy_interface_initialization(self):
        """Test StrategyInterface initialization"""
        config = StrategyConfig(name="test_strategy", strategy_type=StrategyType.MOMENTUM, symbols=["AAPL"])

        # Create a concrete implementation for testing
        class TestStrategyInterface(StrategyInterface):
            def generate_signals(self, data: pd.DataFrame) -> List[TradingSignal]:
                return []

            def update_state(self, data: pd.DataFrame):
                pass

        strategy = TestStrategyInterface(config)

        assert strategy._signal_callbacks == []
        assert strategy._state_data == {}

    def test_strategy_interface_callbacks(self):
        """Test StrategyInterface callback functionality"""
        config = StrategyConfig(name="test_strategy", strategy_type=StrategyType.MOMENTUM, symbols=["AAPL"])

        # Create a concrete implementation for testing
        class TestStrategyInterface(StrategyInterface):
            def generate_signals(self, data: pd.DataFrame) -> List[TradingSignal]:
                return []

            def update_state(self, data: pd.DataFrame):
                pass

        strategy = TestStrategyInterface(config)

        # Mock callback
        callback_called = []

        def mock_callback(signal):
            callback_called.append(signal)

        strategy.add_signal_callback(mock_callback)

        # Emit signal
        signal = TradingSignal("test_strategy", "AAPL", "BUY", 0.8)
        strategy.emit_signal(signal)

        assert len(callback_called) == 1
        assert callback_called[0] == signal

    def test_strategy_interface_state_management(self):
        """Test StrategyInterface state management"""
        config = StrategyConfig(name="test_strategy", strategy_type=StrategyType.MOMENTUM, symbols=["AAPL"])

        # Create a concrete implementation for testing
        class TestStrategyInterface(StrategyInterface):
            def generate_signals(self, data: pd.DataFrame) -> List[TradingSignal]:
                return []

            def update_state(self, data: pd.DataFrame):
                pass

        strategy = TestStrategyInterface(config)

        # Set and get state
        strategy.set_state("last_price", 150.0)
        strategy.set_state("position_size", 100)

        assert strategy.get_state("last_price") == 150.0
        assert strategy.get_state("position_size") == 100
        assert strategy.get_state("nonexistent", "default") == "default"

    def test_strategy_manager_initialization(self):
        """Test StrategyManager initialization"""
        manager = StrategyManager()

        assert manager.strategies == {}
        assert manager.active_strategies == []

    def test_strategy_manager_register_strategy(self):
        """Test StrategyManager register_strategy"""
        manager = StrategyManager()
        config = StrategyConfig(name="test_strategy", strategy_type=StrategyType.MOMENTUM, symbols=["AAPL"])

        # Mock strategy
        strategy = Mock(spec=BaseStrategy)
        strategy.config = config
        strategy.strategy_id = "test_strategy"
        strategy.is_active = True

        manager.register_strategy(strategy)

        assert "test_strategy" in manager.strategies
        assert "test_strategy" in manager.active_strategies

    def test_strategy_manager_get_strategy(self):
        """Test StrategyManager get_strategy"""
        manager = StrategyManager()

        # Non-existent strategy
        assert manager.get_strategy("nonexistent") is None

        # Add strategy
        config = StrategyConfig(name="test_strategy", strategy_type=StrategyType.MOMENTUM, symbols=["AAPL"])
        strategy = Mock(spec=BaseStrategy)
        strategy.config = config
        strategy.strategy_id = "test_strategy"
        strategy.is_active = True

        manager.register_strategy(strategy)
        assert manager.get_strategy("test_strategy") == strategy

    def test_strategy_manager_generate_all_signals(self):
        """Test StrategyManager generate_all_signals"""
        manager = StrategyManager()

        # Create mock strategies
        config1 = StrategyConfig(name="strat1", strategy_type=StrategyType.MOMENTUM, symbols=["AAPL"])
        config2 = StrategyConfig(name="strat2", strategy_type=StrategyType.MEAN_REVERSION, symbols=["GOOGL"])

        strategy1 = Mock(spec=BaseStrategy)
        strategy1.config = config1
        strategy1.strategy_id = "strat1"
        strategy1.is_active = True
        strategy1.generate_signals.return_value = [
            TradingSignal("strat1", "AAPL", "BUY", 0.8)
        ]

        strategy2 = Mock(spec=BaseStrategy)
        strategy2.config = config2
        strategy2.strategy_id = "strat2"
        strategy2.is_active = True
        strategy2.generate_signals.return_value = [
            TradingSignal("strat2", "GOOGL", "SELL", 0.6)
        ]

        manager.register_strategy(strategy1)
        manager.register_strategy(strategy2)

        # Generate signals
        data = pd.DataFrame()  # Mock data
        signals = manager.generate_all_signals(data)

        assert len(signals) == 2
        assert signals[0].strategy_id == "strat1"
        assert signals[1].strategy_id == "strat2"

    def test_strategy_manager_get_all_metrics(self):
        """Test StrategyManager get_all_metrics"""
        manager = StrategyManager()

        # Create mock strategies
        config = StrategyConfig(name="test_strategy", strategy_type=StrategyType.MOMENTUM, symbols=["AAPL"])
        strategy = Mock(spec=BaseStrategy)
        strategy.config = config
        strategy.strategy_id = "test_strategy"
        strategy.is_active = True
        strategy.get_metrics.return_value = StrategyMetrics(strategy_id="test_strategy", total_return=0.15)

        manager.register_strategy(strategy)

        metrics = manager.get_all_metrics()

        assert "test_strategy" in metrics
        assert metrics["test_strategy"].total_return == 0.15


class TestRisk:
    """Test risk-related types"""

    def test_risk_level_enum(self):
        """Test RiskLevel enum values"""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"

    def test_risk_config_creation(self):
        """Test RiskConfig creation"""
        config = RiskConfig(
            max_portfolio_risk=0.02,
            max_position_size=0.1,
            max_correlation=0.7,
            stop_loss_pct=0.05,
            daily_loss_limit=0.03,
            max_leverage=1.0,
            margin_requirement=0.5,
            var_confidence=0.95,
            lookback_days=252
        )

        assert config.max_portfolio_risk == 0.02
        assert config.max_position_size == 0.1
        assert config.max_correlation == 0.7
        assert config.stop_loss_pct == 0.05
        assert config.daily_loss_limit == 0.03
        assert config.max_leverage == 1.0
        assert config.margin_requirement == 0.5
        assert config.var_confidence == 0.95
        assert config.lookback_days == 252

    def test_risk_metrics_creation(self):
        """Test RiskMetrics creation"""
        metrics = RiskMetrics(
            portfolio_var=0.015,
            portfolio_volatility=0.18,
            beta=1.2,
            sharpe_ratio=0.8,
            max_drawdown=0.12,
            gross_exposure=150000.0,
            net_exposure=25000.0,
            leverage=1.5
        )

        assert metrics.portfolio_var == 0.015
        assert metrics.portfolio_volatility == 0.18
        assert metrics.beta == 1.2
        assert metrics.sharpe_ratio == 0.8
        assert metrics.max_drawdown == 0.12
        assert metrics.gross_exposure == 150000.0
        assert metrics.net_exposure == 25000.0
        assert metrics.leverage == 1.5
        assert isinstance(metrics.timestamp, datetime)

    def test_risk_result_creation(self):
        """Test RiskResult creation"""
        result = RiskResult(
            approved=True,
            risk_level=RiskLevel.LOW,
            reasons=["Position size within limits"],
            warnings=["High volatility detected"],
            adjusted_quantity=75.0
        )

        assert result.approved is True
        assert result.risk_level == RiskLevel.LOW
        assert result.reasons == ["Position size within limits"]
        assert result.warnings == ["High volatility detected"]
        assert result.adjusted_quantity == 75.0
        assert isinstance(result.timestamp, datetime)

    def test_risk_result_add_reason(self):
        """Test RiskResult add_reason method"""
        result = RiskResult(approved=True, risk_level=RiskLevel.LOW)

        result.add_reason("Position size exceeds limit")

        assert result.approved is False
        assert "Position size exceeds limit" in result.reasons

    def test_risk_result_add_warning(self):
        """Test RiskResult add_warning method"""
        result = RiskResult(approved=True, risk_level=RiskLevel.LOW)

        result.add_warning("High correlation detected")

        assert "High correlation detected" in result.warnings

    def test_risk_manager_initialization(self):
        """Test RiskManager initialization"""
        config = RiskConfig(max_portfolio_risk=0.02)
        manager = RiskManager(config)

        assert manager.config == config
        assert manager.daily_pnl == 0.0
        assert manager.daily_start_value == 0.0
        assert manager.risk_overrides == {}

    def test_risk_manager_check_trade_risk_approved(self):
        """Test RiskManager check_trade_risk approved trade"""
        config = RiskConfig(max_position_size=0.2, max_portfolio_risk=0.02)  # 20% max position
        manager = RiskManager(config)

        result = manager.check_trade_risk(
            symbol="AAPL",
            quantity=100,
            price=100.0,  # $10,000 trade
            portfolio_value=100000.0,
            current_position=0
        )

        assert result.approved is True
        assert result.risk_level == RiskLevel.LOW

    def test_risk_manager_check_trade_risk_position_size_exceeded(self):
        """Test RiskManager check_trade_risk position size exceeded"""
        config = RiskConfig(max_position_size=0.05)  # 5% max position
        manager = RiskManager(config)

        # Try to buy 10% of portfolio value
        result = manager.check_trade_risk(
            symbol="AAPL",
            quantity=1000,  # 150,000 value
            price=150.0,
            portfolio_value=1000000.0,  # 15% of portfolio
            current_position=0
        )

        assert result.approved is False
        assert result.risk_level == RiskLevel.HIGH
        assert "Position size" in " ".join(result.reasons)

    def test_risk_manager_check_trade_risk_daily_loss_limit(self):
        """Test RiskManager check_trade_risk daily loss limit"""
        config = RiskConfig(daily_loss_limit=0.05)  # 5% daily loss limit
        manager = RiskManager(config)

        # Set up daily loss scenario
        manager.daily_start_value = 100000.0
        manager.daily_pnl = -6000.0  # 6% loss

        result = manager.check_trade_risk(
            symbol="AAPL",
            quantity=100,
            price=150.0,
            portfolio_value=94000.0,
            current_position=0
        )

        assert result.approved is False
        assert result.risk_level == RiskLevel.CRITICAL
        assert "Daily loss" in " ".join(result.reasons)

    def test_risk_manager_calculate_portfolio_metrics(self):
        """Test RiskManager calculate_portfolio_metrics"""
        config = RiskConfig()
        manager = RiskManager(config)

        positions = {"AAPL": 100, "GOOGL": 50}
        prices = {"AAPL": 150.0, "GOOGL": 2800.0}

        metrics = manager.calculate_portfolio_metrics(positions, prices)

        expected_gross = 100 * 150.0 + 50 * 2800.0  # 15000 + 140000 = 155000
        assert metrics.gross_exposure == expected_gross
        assert metrics.net_exposure == expected_gross  # All positive positions
        assert len(metrics.position_concentrations) == 2

        # AAPL: 15000/155000 ≈ 0.0968, GOOGL: 140000/155000 ≈ 0.9032
        assert abs(metrics.position_concentrations["AAPL"] - (15000.0 / 155000.0)) < 0.001
        assert abs(metrics.position_concentrations["GOOGL"] - (140000.0 / 155000.0)) < 0.001

    def test_risk_manager_daily_tracking(self):
        """Test RiskManager daily tracking methods"""
        config = RiskConfig()
        manager = RiskManager(config)

        # Set initial value and update P&L
        manager.reset_daily_tracking(100000.0)
        manager.update_daily_pnl(95000.0)  # Now worth 95000

        assert manager.daily_pnl == -5000.0
        assert manager.daily_start_value == 100000.0

        # Reset daily tracking
        manager.reset_daily_tracking(95000.0)
        assert manager.daily_start_value == 95000.0
        assert manager.daily_pnl == 0.0

    def test_risk_manager_trading_overrides(self):
        """Test RiskManager trading overrides"""
        config = RiskConfig()
        manager = RiskManager(config)

        # Set override
        manager.set_risk_override("AAPL", False)

        assert manager.is_trading_allowed("AAPL") is False
        assert manager.is_trading_allowed("GOOGL") is True  # Default


