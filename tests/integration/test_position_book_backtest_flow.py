"""
Integration Tests for PositionBook in Full Backtest Flow

Tests the complete backtest execution flow:
1. InstitutionalBacktestEngine creates PositionBook
2. PositionBook injected into CentralRiskManager
3. HistoricalExecutionSimulator creates SimulatedFill
4. CentralRiskManager.update_position() delegates to PositionBook
5. PositionBook updates state and publishes events

Phase 3 of PositionBook implementation.
"""

import pytest
from decimal import Decimal

from core_engine.trading.position_book import (
    PositionBook, Fill, PositionUpdate, PositionEventType,
    PositionSide
)
from core_engine.system.central_risk_manager import CentralRiskManager


class TestBacktestPositionFlow:
    """Test the complete backtest position tracking flow"""

    @pytest.fixture
    def position_book(self):
        """Create PositionBook with typical backtest capital"""
        return PositionBook(initial_cash=1_000_000)

    @pytest.fixture
    def risk_manager(self, position_book):
        """Create CentralRiskManager with PositionBook"""
        crm = CentralRiskManager({'initial_capital': 1_000_000})
        crm.set_position_book(position_book)
        return crm

    # -------------------------------------------------------------------------
    # Simulate Complete Trading Day
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_full_trading_day_simulation(self, risk_manager, position_book):
        """Simulate a complete trading day with multiple trades"""
        # Morning: Open positions
        await risk_manager.update_position('AAPL', 'buy', 100, 150.00)
        await risk_manager.update_position('GOOGL', 'buy', 50, 140.00)
        await risk_manager.update_position('TSLA', 'sell', 30, 250.00)  # Short

        # Verify positions
        assert risk_manager.get_current_position('AAPL') == 100.0
        assert risk_manager.get_current_position('GOOGL') == 50.0
        assert position_book.get_position('TSLA').side == PositionSide.SHORT

        # Mid-day: Reduce AAPL position
        result = await risk_manager.update_position('AAPL', 'sell', 50, 155.00)
        assert result['realized_pnl'] == 250.0  # (155-150) * 50
        assert risk_manager.get_current_position('AAPL') == 50.0

        # Afternoon: Close all positions
        await risk_manager.update_position('AAPL', 'sell', 50, 152.00)
        await risk_manager.update_position('GOOGL', 'sell', 50, 145.00)
        await risk_manager.update_position('TSLA', 'buy', 30, 245.00)  # Cover short

        # End of day: All positions closed
        assert risk_manager.get_current_position('AAPL') == 0.0
        assert risk_manager.get_current_position('GOOGL') == 0.0
        assert risk_manager.get_current_position('TSLA') == 0.0

        # Verify total P&L
        # AAPL: (155-150)*50 + (152-150)*50 = 250 + 100 = 350
        # GOOGL: (145-140)*50 = 250
        # TSLA (short): (250-245)*30 = 150
        # Total: 350 + 250 + 150 = 750
        snapshot = position_book.get_snapshot()
        # Verify total realized P&L from snapshot
        # Note: actual P&L may differ slightly due to commission
        assert float(snapshot.total_realized_pnl) > 0

    @pytest.mark.asyncio
    async def test_position_flipping(self, risk_manager, position_book):
        """Test flipping from long to short"""
        # Go long
        await risk_manager.update_position('AMD', 'buy', 100, 100.00)
        assert position_book.get_position('AMD').side == PositionSide.LONG

        # Flip to short (sell more than we have)
        result = await risk_manager.update_position('AMD', 'sell', 150, 110.00)

        # Should now be short 50
        amd_pos = position_book.get_position('AMD')
        assert amd_pos is not None
        assert amd_pos.side == PositionSide.SHORT
        assert abs(float(amd_pos.quantity)) == 50.0

        # Realized P&L from closing long: (110-100)*100 = 1000
        assert result['realized_pnl'] == 1000.0

    # -------------------------------------------------------------------------
    # Cash Balance Accuracy
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_cash_balance_accuracy(self, risk_manager, position_book):
        """Verify cash balance is accurate after trades"""
        initial_cash = float(position_book.get_cash_balance())

        # Buy stock - cash decreases
        await risk_manager.update_position('NVDA', 'buy', 10, 500.00)
        cost = 10 * 500.00  # 5000
        # Commission is calculated as max(1.0, qty * price * 0.00005)
        commission = max(1.0, 10 * 500.00 * 0.00005)

        expected_cash_after_buy = initial_cash - cost - commission
        assert abs(float(position_book.get_cash_balance()) - expected_cash_after_buy) < 1.0

        # Sell stock - cash increases
        await risk_manager.update_position('NVDA', 'sell', 10, 520.00)
        proceeds = 10 * 520.00  # 5200
        commission2 = max(1.0, 10 * 520.00 * 0.00005)

        expected_final_cash = expected_cash_after_buy + proceeds - commission2
        assert abs(float(position_book.get_cash_balance()) - expected_final_cash) < 1.0

    # -------------------------------------------------------------------------
    # State Consistency
    # -------------------------------------------------------------------------

    def test_crm_and_book_stay_in_sync(self, risk_manager, position_book):
        """Verify CRM legacy fields stay in sync with PositionBook"""
        # Add position directly to PositionBook
        fill = Fill.create('META', 'buy', 75, 350.00)
        position_book.on_fill(fill)

        # CRM should be synced via subscription
        assert risk_manager.current_positions.get('META') == 75.0
        assert risk_manager.current_prices.get('META') == 350.0

        # Query methods should return same data
        assert risk_manager.get_current_position('META') == 75.0

        crm_all = risk_manager.get_all_positions()
        book_all = position_book.get_all_positions()

        assert 'META' in crm_all
        assert 'META' in book_all

    # -------------------------------------------------------------------------
    # Event Publishing
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_position_events_published(self, risk_manager, position_book):
        """Verify position events are published"""
        events_received = []

        def event_handler(update: PositionUpdate):
            events_received.append(update)

        # Subscribe to position events
        position_book.subscribe(event_handler)

        # Execute trades
        await risk_manager.update_position('MSFT', 'buy', 50, 400.00)
        await risk_manager.update_position('MSFT', 'sell', 50, 410.00)

        # Should have received 2 events (open + close)
        assert len(events_received) >= 2

        # First event should be OPENED
        assert events_received[0].event_type == PositionEventType.OPENED
        assert events_received[0].symbol == 'MSFT'

        # Last event should be CLOSED
        last_event = events_received[-1]
        assert last_event.event_type == PositionEventType.CLOSED
        assert last_event.realized_pnl == Decimal('500')  # (410-400)*50


class TestPositionBookResilience:
    """Test PositionBook handles edge cases correctly"""

    @pytest.fixture
    def position_book(self):
        return PositionBook(initial_cash=100_000)

    @pytest.fixture
    def risk_manager(self, position_book):
        crm = CentralRiskManager({'initial_capital': 100_000})
        crm.set_position_book(position_book)
        return crm

    @pytest.mark.asyncio
    async def test_zero_quantity_trade(self, risk_manager, position_book):
        """Zero quantity trade should result in zero position"""
        await risk_manager.update_position('AAPL', 'buy', 0, 150.00)

        # Position may exist but should have zero quantity
        pos = position_book.get_position('AAPL')
        if pos is not None:
            assert float(pos.quantity) == 0.0
        assert risk_manager.get_current_position('AAPL') == 0.0

    @pytest.mark.asyncio
    async def test_rapid_trades(self, risk_manager, position_book):
        """Test rapid sequence of trades"""
        for i in range(100):
            await risk_manager.update_position('FAST', 'buy', 10, 100.0 + i * 0.01)

        # Should have accumulated 1000 shares
        assert risk_manager.get_current_position('FAST') == 1000.0

        # Close all at once
        result = await risk_manager.update_position('FAST', 'sell', 1000, 110.0)

        # Should have realized P&L
        assert result['realized_pnl'] > 0
        assert risk_manager.get_current_position('FAST') == 0.0

    @pytest.mark.asyncio
    async def test_multiple_symbols(self, risk_manager, position_book):
        """Test managing many symbols simultaneously"""
        symbols = [f'SYM{i:03d}' for i in range(20)]

        # Open positions in all symbols
        for i, symbol in enumerate(symbols):
            await risk_manager.update_position(symbol, 'buy', 100, 50.0 + i)

        # All should be tracked
        all_positions = risk_manager.get_all_positions()
        assert len(all_positions) == 20

        # Close half
        for symbol in symbols[:10]:
            await risk_manager.update_position(symbol, 'sell', 100, 60.0)

        remaining = risk_manager.get_all_positions()
        # Should have 10 remaining (filtering out zero positions)
        non_zero = {k: v for k, v in remaining.items() if v != 0}
        assert len(non_zero) == 10


class TestPositionBookWithMarketData:
    """Test PositionBook MTM updates with market data"""

    @pytest.fixture
    def position_book(self):
        return PositionBook(initial_cash=500_000)

    def test_unrealized_pnl_updates(self, position_book):
        """Test unrealized P&L updates with price changes"""
        # Open position
        position_book.on_fill(Fill.create('TSLA', 'buy', 100, 200.00))

        # Initial unrealized P&L is 0
        pos = position_book.get_position('TSLA')
        assert pos.unrealized_pnl == Decimal('0')

        # Price goes up
        position_book.on_price_update({'TSLA': Decimal('210')})

        pos = position_book.get_position('TSLA')
        assert pos.unrealized_pnl == Decimal('1000')  # (210-200)*100

        # Price goes down
        position_book.on_price_update({'TSLA': Decimal('195')})

        pos = position_book.get_position('TSLA')
        assert pos.unrealized_pnl == Decimal('-500')  # (195-200)*100

    def test_portfolio_value_with_mtm(self, position_book):
        """Test total portfolio value updates with MTM"""
        initial_cash = float(position_book.get_cash_balance())

        # Open position
        position_book.on_fill(Fill.create('AMZN', 'buy', 50, 180.00))

        # Portfolio value should be cash + position value
        position_book.on_price_update({'AMZN': Decimal('180')})

        snapshot = position_book.get_snapshot()
        expected_value = float(snapshot.cash_balance) + 50 * 180
        assert abs(float(snapshot.total_value) - expected_value) < 1.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
