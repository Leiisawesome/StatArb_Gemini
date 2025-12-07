"""
Unit Tests for PositionBook
============================

Comprehensive tests for the PositionBook single source of truth.

Test Categories:
1. Position Opening (LONG, SHORT)
2. Position Updates (adding, reducing)
3. Position Closing
4. Position Flipping (long to short, short to long)
5. Cash Balance Tracking
6. P&L Calculations (realized, unrealized)
7. MTM Price Updates
8. Event Publishing
9. Thread Safety
10. Edge Cases

Author: StatArb_Gemini
"""

import pytest
from decimal import Decimal
import threading
import time

from core_engine.trading.position_book import (
    PositionBook,
    PositionUpdate,
    Fill,
    FillSide,
    PositionSide,
    PositionStatus,
    PositionEventType,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def position_book():
    """Create a fresh PositionBook with $100,000 initial capital"""
    return PositionBook(initial_cash=Decimal('100000'))


@pytest.fixture
def book_with_long_position(position_book):
    """PositionBook with an existing LONG position in AAPL"""
    fill = Fill.create(
        symbol='AAPL',
        side='buy',
        quantity=100,
        price=150.00,
        commission=1.00
    )
    position_book.on_fill(fill)
    return position_book


@pytest.fixture
def book_with_short_position(position_book):
    """PositionBook with an existing SHORT position in TSLA"""
    fill = Fill.create(
        symbol='TSLA',
        side='sell',
        quantity=50,
        price=200.00,
        commission=1.00
    )
    position_book.on_fill(fill)
    return position_book


# =============================================================================
# TEST: POSITION OPENING
# =============================================================================

class TestPositionOpening:
    """Tests for opening new positions"""

    def test_open_long_position(self, position_book):
        """Test opening a new LONG position"""
        fill = Fill.create(
            symbol='AAPL',
            side='buy',
            quantity=100,
            price=150.00,
            commission=1.00,
            strategy_id='momentum_1'
        )

        update = position_book.on_fill(fill)

        # Check update
        assert update.event_type == PositionEventType.OPENED
        assert update.symbol == 'AAPL'
        assert update.new_quantity == Decimal('100')
        assert update.new_side == PositionSide.LONG
        assert update.new_avg_price == Decimal('150.00')
        assert update.realized_pnl == Decimal('0')

        # Check position
        pos = position_book.get_position('AAPL')
        assert pos is not None
        assert pos.symbol == 'AAPL'
        assert pos.quantity == Decimal('100')
        assert pos.side == PositionSide.LONG
        assert pos.avg_entry_price == Decimal('150.00')
        assert pos.strategy_id == 'momentum_1'
        assert pos.status == PositionStatus.OPEN
        assert len(pos.fills) == 1

    def test_open_short_position(self, position_book):
        """Test opening a new SHORT position"""
        fill = Fill.create(
            symbol='TSLA',
            side='sell',
            quantity=50,
            price=200.00,
            commission=1.00
        )

        update = position_book.on_fill(fill)

        # Check update
        assert update.event_type == PositionEventType.OPENED
        assert update.new_side == PositionSide.SHORT
        assert update.new_quantity == Decimal('50')

        # Check position
        pos = position_book.get_position('TSLA')
        assert pos is not None
        assert pos.side == PositionSide.SHORT
        assert pos.quantity == Decimal('50')

    def test_open_position_cash_impact(self, position_book):
        """Test that opening a position correctly updates cash"""
        initial_cash = position_book.get_cash_balance()

        fill = Fill.create(
            symbol='AAPL',
            side='buy',
            quantity=100,
            price=150.00,
            commission=5.00
        )

        update = position_book.on_fill(fill)

        expected_cash = initial_cash - (Decimal('100') * Decimal('150.00')) - Decimal('5.00')
        assert position_book.get_cash_balance() == expected_cash
        assert update.cash_change == -(Decimal('100') * Decimal('150.00') + Decimal('5.00'))

    def test_open_short_position_cash_impact(self, position_book):
        """Test that opening a SHORT position correctly updates cash (receive proceeds)"""
        initial_cash = position_book.get_cash_balance()

        fill = Fill.create(
            symbol='TSLA',
            side='sell',
            quantity=50,
            price=200.00,
            commission=5.00
        )

        position_book.on_fill(fill)

        # Sell receives proceeds minus commission
        expected_cash = initial_cash + (Decimal('50') * Decimal('200.00')) - Decimal('5.00')
        assert position_book.get_cash_balance() == expected_cash


# =============================================================================
# TEST: POSITION UPDATES (ADDING)
# =============================================================================

class TestPositionAdding:
    """Tests for adding to existing positions"""

    def test_add_to_long_position(self, book_with_long_position):
        """Test adding to an existing LONG position"""
        book = book_with_long_position

        # Add 50 more shares at higher price
        fill = Fill.create(
            symbol='AAPL',
            side='buy',
            quantity=50,
            price=160.00,
            commission=1.00
        )

        update = book.on_fill(fill)

        # Check update
        assert update.event_type == PositionEventType.UPDATED
        assert update.new_quantity == Decimal('150')
        assert update.realized_pnl == Decimal('0')  # No realized P&L when adding

        # Check new average price: (100 * 150 + 50 * 160) / 150 = 153.33
        pos = book.get_position('AAPL')
        expected_avg = (Decimal('100') * Decimal('150') + Decimal('50') * Decimal('160')) / Decimal('150')
        assert pos.avg_entry_price == expected_avg
        assert pos.quantity == Decimal('150')
        assert len(pos.fills) == 2

    def test_add_to_short_position(self, book_with_short_position):
        """Test adding to an existing SHORT position"""
        book = book_with_short_position

        # Sell 30 more shares at lower price
        fill = Fill.create(
            symbol='TSLA',
            side='sell',
            quantity=30,
            price=190.00,
            commission=1.00
        )

        update = book.on_fill(fill)

        assert update.event_type == PositionEventType.UPDATED
        assert update.new_quantity == Decimal('80')
        assert update.realized_pnl == Decimal('0')

        # Check new average price: (50 * 200 + 30 * 190) / 80 = 196.25
        pos = book.get_position('TSLA')
        expected_avg = (Decimal('50') * Decimal('200') + Decimal('30') * Decimal('190')) / Decimal('80')
        assert pos.avg_entry_price == expected_avg


# =============================================================================
# TEST: POSITION REDUCTION (PARTIAL CLOSE)
# =============================================================================

class TestPositionReduction:
    """Tests for reducing positions (partial closes)"""

    def test_reduce_long_position_profit(self, book_with_long_position):
        """Test reducing LONG position at profit"""
        book = book_with_long_position

        # Sell 50 shares at higher price (profit)
        fill = Fill.create(
            symbol='AAPL',
            side='sell',
            quantity=50,
            price=160.00,
            commission=1.00
        )

        update = book.on_fill(fill)

        # Realized P&L: 50 * (160 - 150) = 500
        assert update.realized_pnl == Decimal('500')
        assert update.event_type == PositionEventType.UPDATED

        pos = book.get_position('AAPL')
        assert pos.quantity == Decimal('50')
        assert pos.avg_entry_price == Decimal('150.00')  # Avg price unchanged
        assert pos.realized_pnl == Decimal('500')

    def test_reduce_long_position_loss(self, book_with_long_position):
        """Test reducing LONG position at loss"""
        book = book_with_long_position

        # Sell 50 shares at lower price (loss)
        fill = Fill.create(
            symbol='AAPL',
            side='sell',
            quantity=50,
            price=140.00,
            commission=1.00
        )

        update = book.on_fill(fill)

        # Realized P&L: 50 * (140 - 150) = -500
        assert update.realized_pnl == Decimal('-500')

    def test_reduce_short_position_profit(self, book_with_short_position):
        """Test reducing SHORT position at profit (price went down)"""
        book = book_with_short_position

        # Buy back 30 shares at lower price (profit for short)
        fill = Fill.create(
            symbol='TSLA',
            side='buy',
            quantity=30,
            price=180.00,
            commission=1.00
        )

        update = book.on_fill(fill)

        # Realized P&L: 30 * (200 - 180) = 600
        assert update.realized_pnl == Decimal('600')

        pos = book.get_position('TSLA')
        assert pos.quantity == Decimal('20')

    def test_reduce_short_position_loss(self, book_with_short_position):
        """Test reducing SHORT position at loss (price went up)"""
        book = book_with_short_position

        # Buy back 30 shares at higher price (loss for short)
        fill = Fill.create(
            symbol='TSLA',
            side='buy',
            quantity=30,
            price=220.00,
            commission=1.00
        )

        update = book.on_fill(fill)

        # Realized P&L: 30 * (200 - 220) = -600
        assert update.realized_pnl == Decimal('-600')


# =============================================================================
# TEST: POSITION CLOSING
# =============================================================================

class TestPositionClosing:
    """Tests for fully closing positions"""

    def test_close_long_position(self, book_with_long_position):
        """Test fully closing a LONG position"""
        book = book_with_long_position

        # Close all 100 shares
        fill = Fill.create(
            symbol='AAPL',
            side='sell',
            quantity=100,
            price=165.00,
            commission=1.00
        )

        update = book.on_fill(fill)

        assert update.event_type == PositionEventType.CLOSED
        assert update.new_quantity == Decimal('0')
        assert update.new_side == PositionSide.FLAT
        assert update.realized_pnl == Decimal('1500')  # 100 * (165 - 150)

        # Position should be removed
        pos = book.get_position('AAPL')
        assert pos is None

        # Realized P&L should be tracked
        assert book.get_realized_pnl() == Decimal('1500')

    def test_close_short_position(self, book_with_short_position):
        """Test fully closing a SHORT position"""
        book = book_with_short_position

        # Buy back all 50 shares
        fill = Fill.create(
            symbol='TSLA',
            side='buy',
            quantity=50,
            price=180.00,
            commission=1.00
        )

        update = book.on_fill(fill)

        assert update.event_type == PositionEventType.CLOSED
        assert update.realized_pnl == Decimal('1000')  # 50 * (200 - 180)

        pos = book.get_position('TSLA')
        assert pos is None


# =============================================================================
# TEST: POSITION FLIPPING
# =============================================================================

class TestPositionFlipping:
    """Tests for flipping positions (long to short or vice versa)"""

    def test_flip_long_to_short(self, book_with_long_position):
        """Test flipping from LONG to SHORT"""
        book = book_with_long_position

        # Sell 150 shares (close 100 long, open 50 short)
        fill = Fill.create(
            symbol='AAPL',
            side='sell',
            quantity=150,
            price=160.00,
            commission=1.00
        )

        update = book.on_fill(fill)

        # Should have realized P&L from closing 100 shares
        assert update.realized_pnl == Decimal('1000')  # 100 * (160 - 150)

        # Should now have 50 share SHORT position
        pos = book.get_position('AAPL')
        assert pos is not None
        assert pos.side == PositionSide.SHORT
        assert pos.quantity == Decimal('50')
        assert pos.avg_entry_price == Decimal('160.00')  # New entry price

    def test_flip_short_to_long(self, book_with_short_position):
        """Test flipping from SHORT to LONG"""
        book = book_with_short_position

        # Buy 80 shares (close 50 short, open 30 long)
        fill = Fill.create(
            symbol='TSLA',
            side='buy',
            quantity=80,
            price=190.00,
            commission=1.00
        )

        update = book.on_fill(fill)

        # Should have realized P&L from closing 50 short shares
        assert update.realized_pnl == Decimal('500')  # 50 * (200 - 190)

        # Should now have 30 share LONG position
        pos = book.get_position('TSLA')
        assert pos is not None
        assert pos.side == PositionSide.LONG
        assert pos.quantity == Decimal('30')
        assert pos.avg_entry_price == Decimal('190.00')


# =============================================================================
# TEST: P&L CALCULATIONS
# =============================================================================

class TestPnLCalculations:
    """Tests for P&L calculations"""

    def test_unrealized_pnl_long_profit(self, book_with_long_position):
        """Test unrealized P&L for LONG position in profit"""
        book = book_with_long_position

        # Update price to 160
        book.on_price_update({'AAPL': Decimal('160.00')})

        pos = book.get_position('AAPL')
        # 100 * (160 - 150) = 1000
        assert pos.unrealized_pnl == Decimal('1000')
        assert book.get_unrealized_pnl() == Decimal('1000')

    def test_unrealized_pnl_long_loss(self, book_with_long_position):
        """Test unrealized P&L for LONG position in loss"""
        book = book_with_long_position

        book.on_price_update({'AAPL': Decimal('140.00')})

        pos = book.get_position('AAPL')
        assert pos.unrealized_pnl == Decimal('-1000')

    def test_unrealized_pnl_short_profit(self, book_with_short_position):
        """Test unrealized P&L for SHORT position in profit (price down)"""
        book = book_with_short_position

        book.on_price_update({'TSLA': Decimal('180.00')})

        pos = book.get_position('TSLA')
        # 50 * (200 - 180) = 1000
        assert pos.unrealized_pnl == Decimal('1000')

    def test_unrealized_pnl_short_loss(self, book_with_short_position):
        """Test unrealized P&L for SHORT position in loss (price up)"""
        book = book_with_short_position

        book.on_price_update({'TSLA': Decimal('220.00')})

        pos = book.get_position('TSLA')
        # 50 * (200 - 220) = -1000
        assert pos.unrealized_pnl == Decimal('-1000')

    def test_total_pnl_multiple_positions(self, position_book):
        """Test total P&L across multiple positions"""
        book = position_book

        # Open AAPL long
        book.on_fill(Fill.create('AAPL', 'buy', 100, 150.00))
        # Open TSLA short
        book.on_fill(Fill.create('TSLA', 'sell', 50, 200.00))

        # Update prices
        book.on_price_update({
            'AAPL': Decimal('160.00'),  # +1000 unrealized
            'TSLA': Decimal('190.00')   # +500 unrealized (short)
        })

        assert book.get_unrealized_pnl() == Decimal('1500')

        # Close AAPL for profit
        book.on_fill(Fill.create('AAPL', 'sell', 100, 165.00))

        # Now have 1500 realized, 500 unrealized
        assert book.get_realized_pnl() == Decimal('1500')
        assert book.get_total_pnl() == Decimal('2000')


# =============================================================================
# TEST: CASH BALANCE
# =============================================================================

class TestCashBalance:
    """Tests for cash balance tracking"""

    def test_initial_cash(self, position_book):
        """Test initial cash balance"""
        assert position_book.get_cash_balance() == Decimal('100000')

    def test_cash_after_buy(self, position_book):
        """Test cash decreases after buy"""
        fill = Fill.create('AAPL', 'buy', 100, 150.00, commission=5.00)
        position_book.on_fill(fill)

        # 100000 - (100 * 150) - 5 = 84995
        assert position_book.get_cash_balance() == Decimal('84995')

    def test_cash_after_sell(self, book_with_long_position):
        """Test cash increases after sell"""
        book = book_with_long_position
        initial_cash = book.get_cash_balance()

        fill = Fill.create('AAPL', 'sell', 50, 160.00, commission=5.00)
        book.on_fill(fill)

        # initial + (50 * 160) - 5
        expected = initial_cash + Decimal('50') * Decimal('160.00') - Decimal('5.00')
        assert book.get_cash_balance() == expected

    def test_cash_includes_commissions(self, position_book):
        """Test that commissions are deducted from cash"""
        fill = Fill.create('AAPL', 'buy', 100, 100.00, commission=10.00, slippage=5.00)
        position_book.on_fill(fill)

        # 100000 - 10000 - 10 - 5 = 89985
        assert position_book.get_cash_balance() == Decimal('89985')


# =============================================================================
# TEST: PORTFOLIO VALUE
# =============================================================================

class TestPortfolioValue:
    """Tests for portfolio value calculations"""

    def test_portfolio_value_with_positions(self, book_with_long_position):
        """Test portfolio value includes position market values"""
        book = book_with_long_position

        cash = book.get_cash_balance()
        pos = book.get_position('AAPL')

        expected_value = cash + pos.market_value
        assert book.get_portfolio_value() == expected_value

    def test_portfolio_value_after_mtm(self, book_with_long_position):
        """Test portfolio value updates with MTM"""
        book = book_with_long_position

        # Update price
        book.on_price_update({'AAPL': Decimal('200.00')})

        cash = book.get_cash_balance()
        pos = book.get_position('AAPL')

        assert pos.market_value == Decimal('100') * Decimal('200.00')
        assert book.get_portfolio_value() == cash + Decimal('20000')


# =============================================================================
# TEST: NET EXPOSURE
# =============================================================================

class TestNetExposure:
    """Tests for net exposure calculations"""

    def test_net_exposure_long(self, book_with_long_position):
        """Test net exposure for LONG position"""
        book = book_with_long_position

        exposure = book.get_net_exposure('AAPL')
        assert exposure == Decimal('100') * Decimal('150.00')  # 15000

    def test_net_exposure_short(self, book_with_short_position):
        """Test net exposure for SHORT position (negative)"""
        book = book_with_short_position

        exposure = book.get_net_exposure('TSLA')
        assert exposure == -(Decimal('50') * Decimal('200.00'))  # -10000

    def test_net_exposure_portfolio(self, position_book):
        """Test total portfolio net exposure"""
        book = position_book

        # Open long AAPL: +15000
        book.on_fill(Fill.create('AAPL', 'buy', 100, 150.00))
        # Open short TSLA: -10000
        book.on_fill(Fill.create('TSLA', 'sell', 50, 200.00))

        total_exposure = book.get_net_exposure()
        assert total_exposure == Decimal('5000')  # 15000 - 10000


# =============================================================================
# TEST: EVENT PUBLISHING
# =============================================================================

class TestEventPublishing:
    """Tests for event subscription and publishing"""

    def test_subscribe_receives_events(self, position_book):
        """Test that subscribers receive position update events"""
        events = []

        def handler(update: PositionUpdate):
            events.append(update)

        position_book.subscribe(handler)

        fill = Fill.create('AAPL', 'buy', 100, 150.00)
        position_book.on_fill(fill)

        assert len(events) == 1
        assert events[0].symbol == 'AAPL'
        assert events[0].event_type == PositionEventType.OPENED

    def test_multiple_subscribers(self, position_book):
        """Test multiple subscribers all receive events"""
        events1 = []
        events2 = []

        position_book.subscribe(lambda u: events1.append(u))
        position_book.subscribe(lambda u: events2.append(u))

        fill = Fill.create('AAPL', 'buy', 100, 150.00)
        position_book.on_fill(fill)

        assert len(events1) == 1
        assert len(events2) == 1

    def test_unsubscribe(self, position_book):
        """Test that unsubscribed handlers no longer receive events"""
        events = []

        def handler(update):
            events.append(update)

        position_book.subscribe(handler)
        position_book.on_fill(Fill.create('AAPL', 'buy', 100, 150.00))

        position_book.unsubscribe(handler)
        position_book.on_fill(Fill.create('AAPL', 'sell', 50, 160.00))

        assert len(events) == 1  # Only first event received

    def test_handler_exception_doesnt_break_others(self, position_book):
        """Test that one handler's exception doesn't affect others"""
        events = []

        def bad_handler(update):
            raise ValueError("Intentional error")

        def good_handler(update):
            events.append(update)

        position_book.subscribe(bad_handler)
        position_book.subscribe(good_handler)

        # Should not raise, and good_handler should still receive event
        fill = Fill.create('AAPL', 'buy', 100, 150.00)
        position_book.on_fill(fill)

        assert len(events) == 1


# =============================================================================
# TEST: SNAPSHOTS
# =============================================================================

class TestSnapshots:
    """Tests for portfolio snapshots"""

    def test_snapshot_captures_state(self, book_with_long_position):
        """Test that snapshot captures current portfolio state"""
        book = book_with_long_position

        snapshot = book.get_snapshot()

        assert snapshot.total_positions == 1
        assert snapshot.long_count == 1
        assert snapshot.short_count == 0
        assert 'AAPL' in snapshot.positions
        assert snapshot.positions_value == Decimal('100') * Decimal('150.00')

    def test_snapshot_is_immutable(self, book_with_long_position):
        """Test that snapshot is not affected by subsequent changes"""
        book = book_with_long_position

        snapshot1 = book.get_snapshot()

        # Close position
        book.on_fill(Fill.create('AAPL', 'sell', 100, 160.00))

        snapshot2 = book.get_snapshot()

        # Original snapshot unchanged
        assert snapshot1.total_positions == 1
        assert snapshot2.total_positions == 0


# =============================================================================
# TEST: THREAD SAFETY
# =============================================================================

class TestThreadSafety:
    """Tests for thread-safe operations"""

    def test_concurrent_reads(self, book_with_long_position):
        """Test concurrent reads don't cause issues"""
        book = book_with_long_position
        results = []

        def reader():
            for _ in range(100):
                pos = book.get_position('AAPL')
                results.append(pos.quantity if pos else Decimal('0'))

        threads = [threading.Thread(target=reader) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 1000
        assert all(q == Decimal('100') for q in results)

    def test_concurrent_writes(self, position_book):
        """Test concurrent writes are handled correctly"""
        book = position_book

        def writer(symbol: str):
            for i in range(10):
                fill = Fill.create(symbol, 'buy', 1, 100.00)
                book.on_fill(fill)

        threads = [
            threading.Thread(target=writer, args=(f'SYM{i}',))
            for i in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have 5 positions, each with quantity 10
        positions = book.get_all_positions()
        assert len(positions) == 5
        for pos in positions.values():
            assert pos.quantity == Decimal('10')

    def test_concurrent_read_write(self, position_book):
        """Test concurrent reads and writes"""
        book = position_book
        read_results = []

        def writer():
            for i in range(50):
                fill = Fill.create('AAPL', 'buy', 1, 100.00)
                book.on_fill(fill)
                time.sleep(0.001)

        def reader():
            for _ in range(100):
                pos = book.get_position('AAPL')
                if pos:
                    read_results.append(pos.quantity)
                time.sleep(0.0005)

        writer_thread = threading.Thread(target=writer)
        reader_threads = [threading.Thread(target=reader) for _ in range(3)]

        writer_thread.start()
        for t in reader_threads:
            t.start()

        writer_thread.join()
        for t in reader_threads:
            t.join()

        # Final position should be 50
        pos = book.get_position('AAPL')
        assert pos.quantity == Decimal('50')


# =============================================================================
# TEST: EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions"""

    def test_zero_quantity_fill(self, position_book):
        """Test handling of zero quantity fill"""
        fill = Fill.create('AAPL', 'buy', 0, 150.00)

        # This should still work but create a zero position
        update = position_book.on_fill(fill)
        assert update.new_quantity == Decimal('0')

    def test_get_nonexistent_position(self, position_book):
        """Test getting a position that doesn't exist"""
        pos = position_book.get_position('NONEXISTENT')
        assert pos is None

    def test_position_quantity_for_nonexistent(self, position_book):
        """Test get_position_quantity for non-existent symbol"""
        qty = position_book.get_position_quantity('NONEXISTENT')
        assert qty == Decimal('0')

    def test_reset(self, book_with_long_position):
        """Test resetting the position book"""
        book = book_with_long_position

        assert len(book.get_all_positions()) > 0

        book.reset()

        assert len(book.get_all_positions()) == 0
        assert book.get_cash_balance() == Decimal('100000')
        assert book.get_realized_pnl() == Decimal('0')

    def test_fill_with_slippage(self, position_book):
        """Test fill with slippage cost"""
        fill = Fill.create(
            symbol='AAPL',
            side='buy',
            quantity=100,
            price=150.00,
            commission=5.00,
            slippage=10.00
        )

        position_book.on_fill(fill)

        # Cash should be reduced by notional + commission + slippage
        expected_cash = Decimal('100000') - Decimal('15000') - Decimal('5') - Decimal('10')
        assert position_book.get_cash_balance() == expected_cash

    def test_very_small_quantities(self, position_book):
        """Test handling of very small fractional quantities"""
        fill = Fill.create('AAPL', 'buy', 0.001, 150.00)
        update = position_book.on_fill(fill)

        pos = position_book.get_position('AAPL')
        assert pos.quantity == Decimal('0.001')

    def test_very_large_quantities(self, position_book):
        """Test handling of very large quantities"""
        fill = Fill.create('AAPL', 'buy', 1000000, 150.00)
        update = position_book.on_fill(fill)

        pos = position_book.get_position('AAPL')
        assert pos.quantity == Decimal('1000000')


# =============================================================================
# TEST: SERIALIZATION
# =============================================================================

class TestSerialization:
    """Tests for serialization methods"""

    def test_position_to_dict(self, book_with_long_position):
        """Test BookPosition.to_dict()"""
        pos = book_with_long_position.get_position('AAPL')
        d = pos.to_dict()

        assert d['symbol'] == 'AAPL'
        assert d['quantity'] == 100.0
        assert d['side'] == 'long'
        assert d['avg_entry_price'] == 150.0

    def test_update_to_dict(self, position_book):
        """Test PositionUpdate.to_dict()"""
        fill = Fill.create('AAPL', 'buy', 100, 150.00)
        update = position_book.on_fill(fill)

        d = update.to_dict()

        assert d['symbol'] == 'AAPL'
        assert d['event_type'] == 'opened'
        assert d['new_quantity'] == 100.0

    def test_snapshot_to_dict(self, book_with_long_position):
        """Test PortfolioSnapshot.to_dict()"""
        snapshot = book_with_long_position.get_snapshot()
        d = snapshot.to_dict()

        assert 'total_value' in d
        assert 'positions' in d
        assert 'AAPL' in d['positions']

    def test_summary(self, book_with_long_position):
        """Test get_summary()"""
        summary = book_with_long_position.get_summary()

        assert summary['position_count'] == 1
        assert summary['long_count'] == 1
        assert summary['short_count'] == 0
        assert 'portfolio_value' in summary
        assert 'return_pct' in summary


# =============================================================================
# TEST: FILL FACTORY
# =============================================================================

class TestFillFactory:
    """Tests for Fill.create() factory method"""

    def test_create_fill_basic(self):
        """Test basic fill creation"""
        fill = Fill.create(
            symbol='AAPL',
            side='buy',
            quantity=100,
            price=150.00
        )

        assert fill.symbol == 'AAPL'
        assert fill.side == FillSide.BUY
        assert fill.quantity == Decimal('100')
        assert fill.price == Decimal('150.00')
        assert fill.fill_id is not None

    def test_create_fill_with_costs(self):
        """Test fill creation with commission and slippage"""
        fill = Fill.create(
            symbol='AAPL',
            side='sell',
            quantity=50,
            price=160.00,
            commission=5.00,
            slippage=2.50
        )

        assert fill.commission == Decimal('5.00')
        assert fill.slippage == Decimal('2.50')
        assert fill.total_cost == Decimal('7.50')

    def test_create_fill_from_enum(self):
        """Test fill creation with FillSide enum"""
        fill = Fill.create(
            symbol='AAPL',
            side=FillSide.BUY,
            quantity=100,
            price=150.00
        )

        assert fill.side == FillSide.BUY

    def test_notional_value(self):
        """Test notional value calculation"""
        fill = Fill.create('AAPL', 'buy', 100, 150.00)

        assert fill.notional_value == Decimal('15000')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
