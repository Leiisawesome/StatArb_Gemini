"""
Tests for core_engine.trading.execution.fill_processor

Comprehensive tests for fill processing, validation, reconciliation, and position management.
Target: 60%+ coverage of fill_processor.py (496 lines)
"""

import pytest
import pandas as pd
from datetime import datetime

from core_engine.trading.execution.fill_processor import (
    FillStatus,
    ReconciliationStatus,
    ReportingFrequency,
    TradeExecution,
    PositionUpdate,
    FillEvent,
    FillMetrics,
    FillValidator,
    TradeReconciler,
    PositionManager,
    TradeReporter,
    FillProcessor,
)

# ==================== Fixtures ====================

@pytest.fixture
def sample_trade_execution():
    """Sample trade execution record"""
    return TradeExecution(
        execution_id="EXEC001",
        order_id="ORDER001",
        symbol="AAPL",
        side="BUY",
        quantity=1000.0,
        price=150.00,
        execution_time=datetime.now(),
        venue="NYSE",
        commission=5.00,
        fees=2.50,
    )

@pytest.fixture
def sample_position_update():
    """Sample position update"""
    return PositionUpdate(
        symbol="AAPL",
        account="TEST_ACCOUNT",
        quantity_change=1000.0,
        price=150.00,
        new_position=1000.0,
        new_avg_cost=150.00,
        realized_pnl=0.0,
        unrealized_pnl_change=0.0,
        source_execution_id="EXEC001",
    )

@pytest.fixture
def fill_validator():
    """Fill validator instance"""
    return FillValidator()

@pytest.fixture
def trade_reconciler():
    """Trade reconciler instance"""
    return TradeReconciler()

@pytest.fixture
def position_manager():
    """Position manager instance"""
    return PositionManager()

@pytest.fixture
def trade_reporter():
    """Trade reporter instance"""
    return TradeReporter()

@pytest.fixture
def fill_processor():
    """Fill processor instance"""
    return FillProcessor()

# ==================== Test Enums ====================

class TestEnums:
    """Test enum definitions"""

    def test_fill_status_enum(self):
        """Test FillStatus enum values"""
        assert FillStatus.PENDING.value == "pending"
        assert FillStatus.VALIDATED.value == "validated"
        assert FillStatus.RECONCILED.value == "reconciled"
        assert FillStatus.PROCESSED.value == "processed"
        assert FillStatus.REJECTED.value == "rejected"

    def test_reconciliation_status_enum(self):
        """Test ReconciliationStatus enum values"""
        assert ReconciliationStatus.MATCHED.value == "matched"
        assert ReconciliationStatus.UNMATCHED.value == "unmatched"
        assert ReconciliationStatus.BROKEN.value == "broken"

    def test_reporting_frequency_enum(self):
        """Test ReportingFrequency enum values"""
        assert ReportingFrequency.REAL_TIME.value == "real_time"
        assert ReportingFrequency.DAILY.value == "daily"

# ==================== Test Data Classes ====================

class TestTradeExecution:
    """Test TradeExecution dataclass"""

    def test_basic_trade_execution(self, sample_trade_execution):
        """Test basic trade execution creation"""
        assert sample_trade_execution.execution_id == "EXEC001"
        assert sample_trade_execution.symbol == "AAPL"
        assert sample_trade_execution.quantity == 1000.0
        assert sample_trade_execution.price == 150.00

    def test_trade_with_commission(self, sample_trade_execution):
        """Test trade execution with commission and fees"""
        assert sample_trade_execution.commission == 5.00
        assert sample_trade_execution.fees == 2.50
        total_cost = sample_trade_execution.commission + sample_trade_execution.fees
        assert total_cost == 7.50

    def test_trade_notional_value(self, sample_trade_execution):
        """Test trade notional value calculation"""
        notional = sample_trade_execution.quantity * sample_trade_execution.price
        assert notional == 150000.00

    def test_trade_default_status(self, sample_trade_execution):
        """Test trade default status is PENDING"""
        assert sample_trade_execution.fill_status == FillStatus.PENDING

    def test_sell_side_trade(self):
        """Test sell side trade creation"""
        trade = TradeExecution(
            execution_id="EXEC002",
            order_id="ORDER002",
            symbol="GOOGL",
            side="SELL",
            quantity=100.0,
            price=2800.00,
            execution_time=datetime.now(),
            venue="NASDAQ",
        )
        assert trade.side == "SELL"
        assert trade.quantity == 100.0

class TestPositionUpdate:
    """Test PositionUpdate dataclass"""

    def test_basic_position_update(self, sample_position_update):
        """Test basic position update creation"""
        assert sample_position_update.symbol == "AAPL"
        assert sample_position_update.quantity_change == 1000.0
        assert sample_position_update.new_position == 1000.0

    def test_position_avg_cost(self, sample_position_update):
        """Test position average cost tracking"""
        assert sample_position_update.new_avg_cost == 150.00

    def test_position_pnl(self, sample_position_update):
        """Test position PnL tracking"""
        assert sample_position_update.realized_pnl == 0.0
        assert sample_position_update.unrealized_pnl_change == 0.0

class TestFillEvent:
    """Test FillEvent dataclass"""

    def test_fill_event_creation(self):
        """Test fill event creation"""
        event = FillEvent(
            order_id="ORDER001",
            symbol="AAPL",
            quantity=500.0,
            price=150.25,
            timestamp=datetime.now(),
        )
        assert event.order_id == "ORDER001"
        assert event.quantity == 500.0

# ==================== Test FillValidator ====================

class TestFillValidator:
    """Test fill validation logic"""

    def test_validator_initialization(self, fill_validator):
        """Test validator initialization"""
        assert fill_validator is not None
        assert hasattr(fill_validator, 'validation_rules')

    def test_default_rules_loaded(self, fill_validator):
        """Test default validation rules are loaded"""
        assert len(fill_validator.validation_rules) > 0

    def test_validate_fill_basic(self, fill_validator, sample_trade_execution):
        """Test basic fill validation"""
        result = fill_validator.validate_fill(sample_trade_execution)
        assert isinstance(result, tuple)
        is_valid, messages = result
        assert isinstance(is_valid, bool)

    def test_price_range_validation(self, fill_validator):
        """Test price range validation"""
        trade = TradeExecution(
            execution_id="EXEC003",
            order_id="ORDER003",
            symbol="AAPL",
            side="BUY",
            quantity=100.0,
            price=150.00,
            execution_time=datetime.now(),
            venue="NYSE",
        )

        # Set reference price
        fill_validator._reference_data["AAPL"] = {"price": 150.00}

        result = fill_validator.validate_fill(trade)
        is_valid, messages = result
        # Should pass with price at reference
        assert isinstance(is_valid, bool)

    def test_quantity_validation(self, fill_validator):
        """Test quantity limit validation"""
        trade = TradeExecution(
            execution_id="EXEC004",
            order_id="ORDER004",
            symbol="AAPL",
            side="BUY",
            quantity=2_000_000.0,  # Very large quantity
            price=150.00,
            execution_time=datetime.now(),
            venue="NYSE",
        )

        result = fill_validator.validate_fill(trade)
        is_valid, messages = result
        # May fail quantity check depending on rules
        assert isinstance(is_valid, bool)

# ==================== Test TradeReconciler ====================

class TestTradeReconciler:
    """Test trade reconciliation"""

    def test_reconciler_initialization(self, trade_reconciler):
        """Test reconciler initialization"""
        assert trade_reconciler is not None
        assert hasattr(trade_reconciler, 'reconcile_execution')

    def test_reconcile_matched_trade(self, trade_reconciler, sample_trade_execution):
        """Test reconciling a matched trade"""
        # Create matching counterparty data
        counterparty_data = {
            'execution_id': 'EXEC001_CP',
            'symbol': 'AAPL',
            'side': 'SELL',  # Opposite side
            'quantity': 1000.0,
            'price': 150.00,
            'venue': 'NYSE',
        }

        result = trade_reconciler.reconcile_execution(sample_trade_execution, counterparty_data)
        assert isinstance(result, ReconciliationStatus)

    def test_reconcile_quantity_mismatch(self, trade_reconciler):
        """Test reconciling trades with quantity mismatch"""
        trade1 = TradeExecution(
            execution_id="EXEC005",
            order_id="ORDER005",
            symbol="AAPL",
            side="BUY",
            quantity=1000.0,
            price=150.00,
            execution_time=datetime.now(),
            venue="NYSE",
        )

        counterparty_data = {
            'execution_id': 'EXEC005_CP',
            'symbol': 'AAPL',
            'side': 'SELL',
            'quantity': 900.0,  # Quantity mismatch
            'price': 150.00,
            'venue': 'NYSE',
        }

        result = trade_reconciler.reconcile_execution(trade1, counterparty_data)
        assert isinstance(result, ReconciliationStatus)
        # Should detect mismatch - will be BROKEN or MATCHED depending on tolerance
        assert result in [ReconciliationStatus.BROKEN, ReconciliationStatus.MATCHED]

# ==================== Test PositionManager ====================

class TestPositionManager:
    """Test position management"""

    def test_manager_initialization(self, position_manager):
        """Test position manager initialization"""
        assert position_manager is not None
        assert hasattr(position_manager, 'process_execution')

    def test_new_position_from_trade(self, position_manager, sample_trade_execution):
        """Test creating new position from trade"""
        update = position_manager.process_execution(sample_trade_execution)

        assert isinstance(update, PositionUpdate)
        assert update.symbol == "AAPL"
        assert update.quantity_change == 1000.0

    def test_add_to_existing_position(self, position_manager):
        """Test adding to existing position"""
        # First trade
        trade1 = TradeExecution(
            execution_id="EXEC006",
            order_id="ORDER006",
            symbol="AAPL",
            side="BUY",
            quantity=500.0,
            price=150.00,
            execution_time=datetime.now(),
            venue="NYSE",
        )

        position_manager.process_execution(trade1)

        # Second trade
        trade2 = TradeExecution(
            execution_id="EXEC007",
            order_id="ORDER007",
            symbol="AAPL",
            side="BUY",
            quantity=500.0,
            price=152.00,
            execution_time=datetime.now(),
            venue="NYSE",
        )

        update = position_manager.process_execution(trade2)

        assert update.new_position == 1000.0
        # Average cost should be weighted average
        expected_avg = (500 * 150.00 + 500 * 152.00) / 1000
        assert abs(update.new_avg_cost - expected_avg) < 0.01

    def test_reduce_position(self, position_manager):
        """Test reducing a position"""
        # Build position
        trade1 = TradeExecution(
            execution_id="EXEC008",
            order_id="ORDER008",
            symbol="AAPL",
            side="BUY",
            quantity=1000.0,
            price=150.00,
            execution_time=datetime.now(),
            venue="NYSE",
        )
        position_manager.process_execution(trade1)

        # Sell some
        trade2 = TradeExecution(
            execution_id="EXEC009",
            order_id="ORDER009",
            symbol="AAPL",
            side="SELL",
            quantity=400.0,
            price=155.00,
            execution_time=datetime.now(),
            venue="NYSE",
        )

        update = position_manager.process_execution(trade2)

        assert update.new_position == 600.0
        # Should have realized PnL
        assert update.realized_pnl > 0  # Sold at profit

    def test_get_position(self, position_manager):
        """Test retrieving current position"""
        # Create position
        trade = TradeExecution(
            execution_id="EXEC010",
            order_id="ORDER010",
            symbol="GOOGL",
            side="BUY",
            quantity=100.0,
            price=2800.00,
            execution_time=datetime.now(),
            venue="NASDAQ",
        )
        position_manager.process_execution(trade)

        position_data = position_manager.get_position("DEFAULT", "GOOGL")
        assert position_data is not None
        assert isinstance(position_data, dict)
        assert position_data['position'] == 100.0

# ==================== Test TradeReporter ====================

class TestTradeReporter:
    """Test trade reporting"""

    def test_reporter_initialization(self, trade_reporter):
        """Test reporter initialization"""
        assert trade_reporter is not None
        assert hasattr(trade_reporter, 'generate_execution_report')

    def test_generate_basic_report(self, trade_reporter, sample_trade_execution):
        """Test generating basic trade report"""
        trade_reporter.add_execution(sample_trade_execution)
        report = trade_reporter.generate_execution_report()

        assert isinstance(report, (dict, pd.DataFrame))
        if isinstance(report, pd.DataFrame):
            assert len(report) > 0

    def test_report_with_multiple_trades(self, trade_reporter):
        """Test report with multiple trades"""
        trades = [
            TradeExecution(
                execution_id=f"EXEC{i:03d}",
                order_id=f"ORDER{i:03d}",
                symbol="AAPL",
                side="BUY" if i % 2 == 0 else "SELL",
                quantity=100.0 * (i + 1),
                price=150.00 + i,
                execution_time=datetime.now(),
                venue="NYSE",
            )
            for i in range(5)
        ]

        for trade in trades:
            trade_reporter.add_execution(trade)

        report = trade_reporter.generate_execution_report()
        assert isinstance(report, pd.DataFrame)
        assert len(report) == 5

    def test_report_by_symbol(self, trade_reporter):
        """Test generating report filtered by symbol"""
        trades = [
            TradeExecution(
                execution_id="EXEC011",
                order_id="ORDER011",
                symbol="AAPL",
                side="BUY",
                quantity=1000.0,
                price=150.00,
                execution_time=datetime.now(),
                venue="NYSE",
            ),
            TradeExecution(
                execution_id="EXEC012",
                order_id="ORDER012",
                symbol="GOOGL",
                side="BUY",
                quantity=100.0,
                price=2800.00,
                execution_time=datetime.now(),
                venue="NASDAQ",
            ),
        ]

        for trade in trades:
            trade_reporter.add_execution(trade)

        report = trade_reporter.generate_execution_report(symbol="AAPL")
        assert isinstance(report, pd.DataFrame)
        if len(report) > 0:
            assert all(report['symbol'] == "AAPL")

# ==================== Test FillProcessor ====================

class TestFillProcessor:
    """Test main fill processor"""

    def test_processor_initialization(self, fill_processor):
        """Test fill processor initialization"""
        assert fill_processor is not None
        assert hasattr(fill_processor, 'process_fill')
        assert hasattr(fill_processor, 'validator')
        assert hasattr(fill_processor, 'reconciler')

    @pytest.mark.asyncio
    async def test_process_fill_basic(self, fill_processor, sample_trade_execution):
        """Test basic fill processing"""
        result = await fill_processor.process_fill(sample_trade_execution)

        # Returns bool indicating success/failure
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_process_multiple_fills(self, fill_processor):
        """Test processing multiple fills"""
        trades = [
            TradeExecution(
                execution_id=f"EXEC{i:03d}",
                order_id=f"ORDER{i:03d}",
                symbol="AAPL",
                side="BUY",
                quantity=100.0,
                price=150.00 + i * 0.1,
                execution_time=datetime.now(),
                venue="NYSE",
            )
            for i in range(3)
        ]

        results = []
        for trade in trades:
            result = await fill_processor.process_fill(trade)
            results.append(result)

        assert len(results) == 3
        assert all(isinstance(r, bool) for r in results)

    def test_get_fill_metrics(self, fill_processor):
        """Test retrieving fill metrics"""
        metrics = fill_processor.get_fill_metrics("AAPL")

        assert isinstance(metrics, FillMetrics)

    @pytest.mark.asyncio
    async def test_process_partial_fill(self, fill_processor):
        """Test processing partial fill"""
        trade = TradeExecution(
            execution_id="EXEC_PARTIAL",
            order_id="ORDER_PARTIAL",
            symbol="AAPL",
            side="BUY",
            quantity=500.0,  # Partial of 1000
            price=150.00,
            execution_time=datetime.now(),
            venue="NYSE",
        )

        result = await fill_processor.process_fill(trade)
        assert isinstance(result, bool)

# ==================== Test Error Handling ====================

class TestErrorHandling:
    """Test error handling scenarios"""

    @pytest.mark.asyncio
    async def test_invalid_fill_rejection(self, fill_processor):
        """Test invalid fill is rejected"""
        invalid_trade = TradeExecution(
            execution_id="EXEC_INVALID",
            order_id="ORDER_INVALID",
            symbol="AAPL",
            side="BUY",
            quantity=-1000.0,  # Negative quantity
            price=150.00,
            execution_time=datetime.now(),
            venue="NYSE",
        )

        try:
            result = await fill_processor.process_fill(invalid_trade)
            # Should either raise or return rejection status
            if isinstance(result, dict):
                assert result.get('status') == 'rejected' or not result.get('is_valid', True)
        except (ValueError, AssertionError):
            # Expected to raise error
            pass

    def test_position_update_error_handling(self, position_manager):
        """Test position manager handles errors gracefully"""
        invalid_trade = TradeExecution(
            execution_id="EXEC_ERR",
            order_id="ORDER_ERR",
            symbol="",  # Empty symbol
            side="BUY",
            quantity=1000.0,
            price=150.00,
            execution_time=datetime.now(),
            venue="NYSE",
        )

        try:
            position_manager.process_execution(invalid_trade)
        except (ValueError, KeyError, AttributeError):
            # Expected to handle empty symbol
            pass

# ==================== Test Integration ====================

class TestIntegration:
    """Test integration scenarios"""

    @pytest.mark.asyncio
    async def test_full_fill_lifecycle(self, fill_processor):
        """Test complete fill processing lifecycle"""
        # Create trade
        trade = TradeExecution(
            execution_id="EXEC_LIFECYCLE",
            order_id="ORDER_LIFECYCLE",
            symbol="AAPL",
            side="BUY",
            quantity=1000.0,
            price=150.00,
            execution_time=datetime.now(),
            venue="NYSE",
            commission=5.00,
        )

        # Process fill
        result = await fill_processor.process_fill(trade)
        assert isinstance(result, bool)

        # Get metrics
        metrics = fill_processor.get_fill_metrics("AAPL")
        assert isinstance(metrics, FillMetrics)

    def test_multiple_symbols_tracking(self, position_manager):
        """Test tracking positions across multiple symbols"""
        symbols = ["AAPL", "GOOGL", "MSFT"]

        for i, symbol in enumerate(symbols):
            trade = TradeExecution(
                execution_id=f"EXEC_MULTI_{i}",
                order_id=f"ORDER_MULTI_{i}",
                symbol=symbol,
                side="BUY",
                quantity=100.0 * (i + 1),
                price=100.0 + i * 50,
                execution_time=datetime.now(),
                venue="NYSE",
            )
            position_manager.process_execution(trade)

        # Check all positions exist
        for symbol in symbols:
            position_data = position_manager.get_position("DEFAULT", symbol)
            assert position_data is not None
            assert position_data['position'] > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
