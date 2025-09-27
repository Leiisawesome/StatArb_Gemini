"""
Unit tests for type_definitions module
"""

import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import Mock
from typing import List

# Import all types from type_definitions
from core_engine.type_definitions.orders import (
    OrderType, OrderStatus, OrderSide, Order, ExecutionResult
)
from core_engine.type_definitions.portfolio import (
    Position, PortfolioSnapshot, PortfolioConfig, Portfolio, PortfolioManager
)
from core_engine.type_definitions.strategy import (
    StrategyType, StrategyConfig, TradingSignal, StrategyMetrics,
    BaseStrategy, StrategyInterface, StrategyManager
)
from core_engine.type_definitions.risk import (
    RiskLevel, RiskConfig, RiskMetrics, RiskResult, RiskManager
)
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


class TestOrders:
    """Test order-related types"""

    def test_order_type_enum(self):
        """Test OrderType enum values"""
        assert OrderType.MARKET.value == "market"
        assert OrderType.LIMIT.value == "limit"
        assert OrderType.STOP.value == "stop"
        assert OrderType.STOP_LIMIT.value == "stop_limit"

    def test_order_status_enum(self):
        """Test OrderStatus enum values"""
        assert OrderStatus.PENDING.value == "pending"
        assert OrderStatus.SUBMITTED.value == "submitted"
        assert OrderStatus.PARTIAL_FILLED.value == "partial_filled"
        assert OrderStatus.FILLED.value == "filled"
        assert OrderStatus.CANCELLED.value == "cancelled"
        assert OrderStatus.REJECTED.value == "rejected"

    def test_order_side_enum(self):
        """Test OrderSide enum values"""
        assert OrderSide.BUY.value == "buy"
        assert OrderSide.SELL.value == "sell"

    def test_order_creation(self):
        """Test Order dataclass creation and defaults"""
        order = Order(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET
        )

        assert order.symbol == "AAPL"
        assert order.side == OrderSide.BUY
        assert order.quantity == 100
        assert order.order_type == OrderType.MARKET
        assert order.price is None
        assert order.stop_price is None
        assert order.status == OrderStatus.PENDING
        assert order.filled_quantity == 0.0
        assert order.commission == 0.0
        assert isinstance(order.order_id, str)
        assert isinstance(order.timestamp, datetime)
        assert isinstance(order.metadata, dict)

    def test_order_with_optional_fields(self):
        """Test Order with all optional fields set"""
        timestamp = datetime.now()
        order = Order(
            symbol="AAPL",
            side=OrderSide.SELL,
            quantity=50,
            order_type=OrderType.LIMIT,
            price=150.0,
            stop_price=145.0,
            order_id="test_123",
            status=OrderStatus.SUBMITTED,
            timestamp=timestamp,
            filled_quantity=25.0,
            average_price=148.0,
            commission=5.0,
            strategy_id="momentum",
            metadata={"signal_id": "sig_001"}
        )

        assert order.price == 150.0
        assert order.stop_price == 145.0
        assert order.order_id == "test_123"
        assert order.status == OrderStatus.SUBMITTED
        assert order.timestamp == timestamp
        assert order.filled_quantity == 25.0
        assert order.average_price == 148.0
        assert order.commission == 5.0
        assert order.strategy_id == "momentum"
        assert order.metadata["signal_id"] == "sig_001"

    def test_execution_result_creation(self):
        """Test ExecutionResult dataclass creation"""
        timestamp = datetime.now()
        result = ExecutionResult(
            order_id="order_123",
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            price=150.0,
            commission=1.5,
            timestamp=timestamp,
            execution_id="exec_456",
            success=True,
            broker_order_id="broker_789",
            metadata={"venue": "NASDAQ"}
        )

        assert result.order_id == "order_123"
        assert result.symbol == "AAPL"
        assert result.side == OrderSide.BUY
        assert result.quantity == 100
        assert result.price == 150.0
        assert result.commission == 1.5
        assert result.timestamp == timestamp
        assert result.execution_id == "exec_456"
        assert result.success is True
        assert result.broker_order_id == "broker_789"
        assert result.metadata["venue"] == "NASDAQ"

    def test_execution_result_defaults(self):
        """Test ExecutionResult default values"""
        result = ExecutionResult(
            order_id="order_123",
            symbol="AAPL",
            side=OrderSide.SELL,
            quantity=50,
            price=145.0,
            commission=0.75
        )

        assert result.success is True
        assert result.error_message is None
        assert result.broker_order_id is None
        assert isinstance(result.metadata, dict)
        assert isinstance(result.execution_id, str)
        assert isinstance(result.timestamp, datetime)


class TestPortfolio:
    """Test portfolio-related types"""

    def test_position_creation(self):
        """Test Position dataclass creation"""
        pos = Position(
            symbol="AAPL",
            quantity=100,
            average_price=150.0
        )

        assert pos.symbol == "AAPL"
        assert pos.quantity == 100
        assert pos.average_price == 150.0
        assert pos.market_price is None

    def test_position_properties_without_market_price(self):
        """Test Position properties without market price"""
        pos = Position(
            symbol="AAPL",
            quantity=100,
            average_price=150.0
        )

        assert pos.market_value == 15000.0  # quantity * average_price
        assert pos.unrealized_pnl == 0.0  # no market price

    def test_position_properties_with_market_price(self):
        """Test Position properties with market price"""
        pos = Position(
            symbol="AAPL",
            quantity=100,
            average_price=150.0,
            market_price=155.0
        )

        assert pos.market_value == 15500.0  # quantity * market_price
        assert pos.unrealized_pnl == 500.0  # (155-150) * 100

    def test_portfolio_snapshot_creation(self):
        """Test PortfolioSnapshot creation"""
        positions = {
            "AAPL": Position("AAPL", 100, 150.0, 155.0),
            "GOOGL": Position("GOOGL", 50, 2800.0, 2750.0)
        }

        snapshot = PortfolioSnapshot.create(cash=50000.0, positions=positions)

        assert snapshot.cash == 50000.0
        assert snapshot.positions == positions
        assert snapshot.total_value == 50000.0 + 15500.0 + 137500.0  # cash + AAPL + GOOGL
        assert snapshot.unrealized_pnl == 500.0 + (-2500.0)  # AAPL + GOOGL
        assert isinstance(snapshot.timestamp, datetime)

    def test_portfolio_config_creation(self):
        """Test PortfolioConfig creation"""
        config = PortfolioConfig(
            initial_cash=100000.0,
            commission_rate=0.001,
            min_cash_reserve=1000.0,
            max_position_size=0.1,
            enable_short_selling=False
        )

        assert config.initial_cash == 100000.0
        assert config.commission_rate == 0.001
        assert config.min_cash_reserve == 1000.0
        assert config.max_position_size == 0.1
        assert config.enable_short_selling is False

    def test_portfolio_initialization(self):
        """Test Portfolio initialization"""
        config = PortfolioConfig(initial_cash=100000.0)
        portfolio = Portfolio(config)

        assert portfolio.config == config
        assert portfolio.cash == 100000.0
        assert portfolio.positions == {}
        assert portfolio.history == []

    def test_portfolio_get_position(self):
        """Test Portfolio get_position method"""
        config = PortfolioConfig()
        portfolio = Portfolio(config)

        # Position doesn't exist
        assert portfolio.get_position("AAPL") is None

        # Add position
        pos = Position("AAPL", 100, 150.0)
        portfolio.positions["AAPL"] = pos

        assert portfolio.get_position("AAPL") == pos

    def test_portfolio_update_position_new(self):
        """Test Portfolio update_position for new position"""
        config = PortfolioConfig()
        portfolio = Portfolio(config)

        portfolio.update_position("AAPL", 100, 150.0)

        assert "AAPL" in portfolio.positions
        pos = portfolio.positions["AAPL"]
        assert pos.symbol == "AAPL"
        assert pos.quantity == 100
        assert pos.average_price == 150.0
        assert portfolio.cash == config.initial_cash - (100 * 150.0)

    def test_portfolio_update_position_existing(self):
        """Test Portfolio update_position for existing position"""
        config = PortfolioConfig(initial_cash=100000.0)
        portfolio = Portfolio(config)

        # Initial position
        portfolio.update_position("AAPL", 100, 150.0)

        # Add to position
        portfolio.update_position("AAPL", 50, 160.0)

        pos = portfolio.positions["AAPL"]
        assert pos.quantity == 150
        # Average price: (100*150 + 50*160) / 150 = 153.33
        assert abs(pos.average_price - 153.333) < 0.001
        assert portfolio.cash == 100000.0 - (100 * 150.0) - (50 * 160.0)

    def test_portfolio_update_position_close(self):
        """Test Portfolio update_position closing position"""
        config = PortfolioConfig(initial_cash=100000.0)
        portfolio = Portfolio(config)

        # Initial position
        portfolio.update_position("AAPL", 100, 150.0)

        # Close position
        portfolio.update_position("AAPL", -100, 155.0)

        assert "AAPL" not in portfolio.positions
        assert portfolio.cash == 100000.0 - (100 * 150.0) + (100 * 155.0)  # Add proceeds

    def test_portfolio_update_market_prices(self):
        """Test Portfolio update_market_prices"""
        config = PortfolioConfig()
        portfolio = Portfolio(config)

        # Add positions
        portfolio.positions["AAPL"] = Position("AAPL", 100, 150.0)
        portfolio.positions["GOOGL"] = Position("GOOGL", 50, 2800.0)

        # Update prices
        prices = {"AAPL": 155.0, "GOOGL": 2750.0}
        portfolio.update_market_prices(prices)

        assert portfolio.positions["AAPL"].market_price == 155.0
        assert portfolio.positions["GOOGL"].market_price == 2750.0

    def test_portfolio_properties(self):
        """Test Portfolio computed properties"""
        config = PortfolioConfig(initial_cash=100000.0)
        portfolio = Portfolio(config)

        # Add positions with market prices
        portfolio.positions["AAPL"] = Position("AAPL", 100, 150.0, 155.0)
        portfolio.positions["GOOGL"] = Position("GOOGL", 50, 2800.0, 2750.0)

        assert portfolio.total_value == 100000.0 + 15500.0 + 137500.0
        assert portfolio.unrealized_pnl == 500.0 + (-2500.0)

    def test_portfolio_manager_initialization(self):
        """Test PortfolioManager initialization"""
        config = PortfolioConfig(initial_cash=100000.0)
        manager = PortfolioManager(config)

        assert isinstance(manager.portfolio, Portfolio)
        assert manager.config == config

    def test_portfolio_manager_execute_trade_success(self):
        """Test PortfolioManager execute_trade success"""
        config = PortfolioConfig(initial_cash=100000.0, commission_rate=0.001)
        manager = PortfolioManager(config)

        success = manager.execute_trade("AAPL", 100, 150.0)

        assert success is True
        assert manager.portfolio.cash == 100000.0 - (100 * 150.0) - (100 * 150.0 * 0.001)
        assert "AAPL" in manager.portfolio.positions

    def test_portfolio_manager_execute_trade_insufficient_cash(self):
        """Test PortfolioManager execute_trade insufficient cash"""
        config = PortfolioConfig(initial_cash=1000.0)  # Very little cash
        manager = PortfolioManager(config)

        success = manager.execute_trade("AAPL", 100, 150.0)

        assert success is False
        assert manager.portfolio.cash == 1000.0  # Unchanged

    def test_portfolio_manager_get_position_size(self):
        """Test PortfolioManager get_position_size"""
        config = PortfolioConfig()
        manager = PortfolioManager(config)

        # No position
        assert manager.get_position_size("AAPL") == 0.0

        # Add position
        manager.execute_trade("AAPL", 100, 150.0)
        assert manager.get_position_size("AAPL") == 100

    def test_portfolio_manager_can_trade(self):
        """Test PortfolioManager can_trade method"""
        config = PortfolioConfig(
            initial_cash=100000.0,
            max_position_size=0.2,  # 20% max position
            commission_rate=0.001
        )
        manager = PortfolioManager(config)

        # Valid trade (10% of portfolio)
        assert manager.can_trade("AAPL", 100, 100.0) is True  # $10,000 position

        # Invalid trade - insufficient cash
        assert manager.can_trade("AAPL", 2000, 100.0) is False  # $200,000 needed

        # Invalid trade - position size limit exceeded
        manager.execute_trade("AAPL", 150, 100.0)  # Create $15,000 position
        assert manager.can_trade("AAPL", 100, 100.0) is False  # Would exceed 20% limit


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
