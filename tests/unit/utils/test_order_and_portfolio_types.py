"""
Unit tests for type_definitions module
"""

from datetime import datetime

# Import all types from type_definitions
from core_engine.type_definitions.orders import (
    OrderType, OrderStatus, OrderSide, Order, ExecutionResult
)
from core_engine.type_definitions.portfolio import (
    Position, PortfolioSnapshot, PortfolioConfig, Portfolio, PortfolioManager
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


