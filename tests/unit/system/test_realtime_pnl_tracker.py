"""
Unit Tests for RealTimePnLTracker
Tests real-time P&L tracking, attribution, and reporting

Test Coverage:
1. Market data updates (unrealized P&L)
2. Position entry tracking
3. Position close (realized P&L)
4. Intraday high-water mark
5. Drawdown calculation
6. Position attribution
7. Strategy attribution
8. Daily reset
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock
from core_engine.system.realtime_pnl_tracker import (
    RealTimePnLTracker,
    PnLSnapshot
)


class TestRealTimePnLTracker:
    """Test suite for RealTimePnLTracker"""

    @pytest.fixture
    def mock_risk_manager(self):
        """Create mock risk manager"""
        risk_manager = Mock()
        risk_manager.current_positions = {}
        risk_manager.portfolio_value = 100000.0
        return risk_manager

    @pytest.fixture
    def tracker(self, mock_risk_manager):
        """Create P&L tracker instance"""
        return RealTimePnLTracker(mock_risk_manager, {})

    @pytest.mark.asyncio
    async def test_position_entry_records_cost_basis(self, tracker):
        """Test position entry records cost basis"""
        await tracker.update_position_entry(
            symbol='AAPL',
            quantity=100.0,
            entry_price=150.0,
            strategy_id='momentum_1'
        )

        assert tracker.position_cost_basis['AAPL'] == 150.0
        assert tracker.position_strategy_map['AAPL'] == 'momentum_1'

    @pytest.mark.asyncio
    async def test_market_data_updates_unrealized_pnl(self, tracker, mock_risk_manager):
        """Test market data updates calculate unrealized P&L"""
        # Enter position
        await tracker.update_position_entry(
            symbol='AAPL',
            quantity=100.0,
            entry_price=150.0
        )

        # Set position in risk manager
        mock_risk_manager.current_positions['AAPL'] = 100.0

        # Market moves up to $155
        await tracker.update_market_data('AAPL', 155.0, datetime.now())

        # Unrealized P&L should be $500 (100 shares * $5 gain)
        assert tracker.unrealized_pnl == 500.0
        assert tracker.total_pnl == 500.0
        assert tracker.position_pnl['AAPL'] == 500.0

    @pytest.mark.asyncio
    async def test_position_close_realizes_pnl(self, tracker, mock_risk_manager):
        """Test position close calculates realized P&L"""
        # Enter position
        await tracker.update_position_entry(
            symbol='TSLA',
            quantity=50.0,
            entry_price=250.0,
            strategy_id='momentum_1'
        )

        # Close position at profit
        await tracker.update_position_close(
            symbol='TSLA',
            quantity=50.0,
            exit_price=260.0,
            strategy_id='momentum_1'
        )

        # Realized P&L should be $500 (50 shares * $10 gain)
        assert tracker.realized_pnl == 500.0
        assert tracker.total_pnl == 500.0
        assert tracker.winning_trades == 1
        assert tracker.strategy_pnl['momentum_1'] == 500.0

    @pytest.mark.asyncio
    async def test_losing_trade_tracked(self, tracker):
        """Test losing trade is tracked correctly"""
        # Enter position
        await tracker.update_position_entry(
            symbol='MSFT',
            quantity=100.0,
            entry_price=350.0
        )

        # Close at loss
        await tracker.update_position_close(
            symbol='MSFT',
            quantity=100.0,
            exit_price=340.0
        )

        # Realized P&L should be -$1000
        assert tracker.realized_pnl == -1000.0
        assert tracker.losing_trades == 1
        assert tracker.winning_trades == 0

    @pytest.mark.asyncio
    async def test_intraday_high_tracking(self, tracker, mock_risk_manager):
        """Test intraday high-water mark is tracked"""
        # Enter position
        await tracker.update_position_entry('AAPL', 100.0, 100.0)
        mock_risk_manager.current_positions['AAPL'] = 100.0

        # Price goes up
        await tracker.update_market_data('AAPL', 110.0, datetime.now())

        # High should be $1000 (100 * $10 gain)
        assert tracker.intraday_high == 1000.0
        assert tracker.current_drawdown == 0.0

        # Price drops
        await tracker.update_market_data('AAPL', 105.0, datetime.now())

        # High should remain $1000
        assert tracker.intraday_high == 1000.0
        # Drawdown should be -50% ($500 / $1000)
        assert tracker.current_drawdown == pytest.approx(-0.5, abs=0.01)

    @pytest.mark.asyncio
    async def test_strategy_attribution(self, tracker):
        """Test P&L is attributed to strategies"""
        # Strategy 1: Profitable trade
        await tracker.update_position_entry('AAPL', 100.0, 100.0, 'strategy_1')
        await tracker.update_position_close('AAPL', 100.0, 110.0, 'strategy_1')

        # Strategy 2: Loss trade
        await tracker.update_position_entry('TSLA', 50.0, 200.0, 'strategy_2')
        await tracker.update_position_close('TSLA', 50.0, 190.0, 'strategy_2')

        # Check attribution
        assert tracker.strategy_pnl['strategy_1'] == 1000.0  # +$1000
        assert tracker.strategy_pnl['strategy_2'] == -500.0  # -$500
        assert tracker.total_pnl == 500.0  # Net $500

    @pytest.mark.asyncio
    async def test_multiple_price_updates(self, tracker, mock_risk_manager):
        """Test multiple price updates track correctly"""
        await tracker.update_position_entry('NVDA', 100.0, 400.0)
        mock_risk_manager.current_positions['NVDA'] = 100.0

        # Series of price updates
        await tracker.update_market_data('NVDA', 405.0, datetime.now())
        assert tracker.unrealized_pnl == 500.0

        await tracker.update_market_data('NVDA', 410.0, datetime.now())
        assert tracker.unrealized_pnl == 1000.0

        await tracker.update_market_data('NVDA', 395.0, datetime.now())
        assert tracker.unrealized_pnl == -500.0

    @pytest.mark.asyncio
    async def test_daily_reset(self, tracker):
        """Test daily reset functionality"""
        # Set up some P&L
        tracker.total_pnl = 1000.0
        tracker.intraday_high = 1500.0
        tracker.current_drawdown = -0.33

        # Perform daily reset
        await tracker.daily_reset()

        # Intraday high should reset to current total
        assert tracker.intraday_high == 1000.0
        assert tracker.current_drawdown == 0.0

    def test_get_current_snapshot(self, tracker):
        """Test snapshot creation"""
        tracker.realized_pnl = 100.0
        tracker.unrealized_pnl = 200.0
        tracker.total_pnl = 300.0
        tracker.intraday_high = 400.0
        tracker.current_drawdown = -0.25

        snapshot = tracker.get_current_snapshot()

        assert isinstance(snapshot, PnLSnapshot)
        assert snapshot.realized_pnl == 100.0
        assert snapshot.unrealized_pnl == 200.0
        assert snapshot.total_pnl == 300.0
        assert snapshot.intraday_high == 400.0
        assert snapshot.current_drawdown == -0.25

    def test_top_positions(self, tracker):
        """Test getting top positions by P&L"""
        tracker.position_pnl = {
            'AAPL': 1000.0,
            'TSLA': 500.0,
            'MSFT': -200.0,
            'NVDA': 800.0,
            'GOOGL': -100.0
        }

        top = tracker.get_top_positions(3)

        assert len(top) == 3
        assert top[0] == ('AAPL', 1000.0)
        assert top[1] == ('NVDA', 800.0)
        assert top[2] == ('TSLA', 500.0)

    def test_bottom_positions(self, tracker):
        """Test getting worst positions by P&L"""
        tracker.position_pnl = {
            'AAPL': 1000.0,
            'TSLA': 500.0,
            'MSFT': -200.0,
            'NVDA': 800.0,
            'GOOGL': -300.0
        }

        bottom = tracker.get_bottom_positions(2)

        assert len(bottom) == 2
        assert bottom[0] == ('GOOGL', -300.0)
        assert bottom[1] == ('MSFT', -200.0)

    def test_statistics_calculation(self, tracker):
        """Test P&L statistics calculation"""
        tracker.realized_pnl = 1000.0
        tracker.unrealized_pnl = 500.0
        tracker.total_pnl = 1500.0
        tracker.total_trades = 10
        tracker.winning_trades = 7
        tracker.losing_trades = 3

        stats = tracker.get_pnl_statistics()

        assert stats['realized_pnl'] == 1000.0
        assert stats['unrealized_pnl'] == 500.0
        assert stats['total_pnl'] == 1500.0
        assert stats['total_trades'] == 10
        assert stats['win_rate'] == 0.7

    def test_report_generation(self, tracker):
        """Test P&L report generation"""
        tracker.realized_pnl = 500.0
        tracker.unrealized_pnl = 300.0
        tracker.total_pnl = 800.0

        report = tracker.generate_pnl_report()

        assert 'REAL-TIME P&L REPORT' in report
        assert 'Realized P&L' in report
        assert 'Unrealized P&L' in report
        assert '$500' in report
        assert '$300' in report

    def test_pnl_time_series(self, tracker):
        """Test P&L time series retrieval"""
        # Add some historical snapshots
        now = datetime.now()
        for i in range(5):
            snapshot = PnLSnapshot(
                timestamp=now - timedelta(minutes=i),
                realized_pnl=100.0 * i,
                unrealized_pnl=50.0 * i,
                total_pnl=150.0 * i,
                intraday_high=200.0 * i,
                current_drawdown=-0.1 * i,
                portfolio_value=100000.0 + 1000 * i
            )
            tracker.pnl_history.append(snapshot)

        # Get last 3 minutes
        series = tracker.get_pnl_series(minutes=3)

        assert len(series) == 3


# Integration Test
class TestPnLTrackerIntegration:
    """Integration tests for P&L tracker"""

    @pytest.mark.asyncio
    async def test_full_trading_day_scenario(self):
        """Test complete trading day P&L tracking"""
        # Setup
        mock_risk_manager = Mock()
        mock_risk_manager.current_positions = {}
        mock_risk_manager.portfolio_value = 100000.0

        tracker = RealTimePnLTracker(mock_risk_manager, {})

        # Morning: Enter long position
        await tracker.update_position_entry(
            symbol='AAPL',
            quantity=100.0,
            entry_price=150.0,
            strategy_id='momentum_1'
        )
        mock_risk_manager.current_positions['AAPL'] = 100.0

        # Mid-morning: Price rises
        await tracker.update_market_data('AAPL', 155.0, datetime.now())
        assert tracker.unrealized_pnl == 500.0  # +$500
        assert tracker.intraday_high == 500.0

        # Midday: Price peaks
        await tracker.update_market_data('AAPL', 160.0, datetime.now())
        assert tracker.unrealized_pnl == 1000.0  # +$1000
        assert tracker.intraday_high == 1000.0

        # Afternoon: Price drops
        await tracker.update_market_data('AAPL', 155.0, datetime.now())
        assert tracker.unrealized_pnl == 500.0  # +$500
        assert tracker.intraday_high == 1000.0  # Still $1000
        assert tracker.current_drawdown == -0.5  # -50% from high

        # Close position
        await tracker.update_position_close(
            symbol='AAPL',
            quantity=100.0,
            exit_price=155.0,
            strategy_id='momentum_1'
        )

        # Verify final state
        assert tracker.realized_pnl == 500.0
        assert tracker.unrealized_pnl == 0.0
        assert tracker.total_pnl == 500.0
        assert tracker.winning_trades == 1
        assert tracker.strategy_pnl['momentum_1'] == 500.0

    @pytest.mark.asyncio
    async def test_multiple_positions_tracking(self):
        """Test tracking multiple positions simultaneously"""
        mock_risk_manager = Mock()
        mock_risk_manager.current_positions = {}
        mock_risk_manager.portfolio_value = 100000.0

        tracker = RealTimePnLTracker(mock_risk_manager, {})

        # Enter multiple positions
        positions = [
            {'symbol': 'AAPL', 'quantity': 100, 'price': 150},
            {'symbol': 'TSLA', 'quantity': 50, 'price': 250},
            {'symbol': 'MSFT', 'quantity': 75, 'price': 350}
        ]

        for pos in positions:
            await tracker.update_position_entry(
                symbol=pos['symbol'],
                quantity=pos['quantity'],
                entry_price=pos['price'],
                strategy_id='multi_strategy'
            )
            mock_risk_manager.current_positions[pos['symbol']] = pos['quantity']

        # Update prices
        await tracker.update_market_data('AAPL', 155, datetime.now())  # +$500
        await tracker.update_market_data('TSLA', 260, datetime.now())  # +$500
        await tracker.update_market_data('MSFT', 340, datetime.now())  # -$750

        # Total unrealized should be +$250
        assert tracker.unrealized_pnl == pytest.approx(250.0, abs=1.0)

        # Check individual positions
        assert tracker.position_pnl['AAPL'] == 500.0
        assert tracker.position_pnl['TSLA'] == 500.0
        assert tracker.position_pnl['MSFT'] == -750.0


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v', '--tb=short'])

