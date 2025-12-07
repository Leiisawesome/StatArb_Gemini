"""
Integration Tests for PositionBook as Single Source of Truth (SSOT)

Tests the integration between:
- InstitutionalBacktestEngine (owns PositionBook)
- CentralRiskManager (receives PositionBook, delegates position operations)

Phase 2 of PositionBook implementation.
"""

import pytest
from decimal import Decimal
from datetime import datetime

from core_engine.system.central_risk_manager import CentralRiskManager
from core_engine.trading.position_book import (
    PositionBook, Fill
)


class TestPositionBookCRMIntegration:
    """Test integration between PositionBook and CentralRiskManager"""

    @pytest.fixture
    def position_book(self):
        """Create a fresh PositionBook instance"""
        return PositionBook(initial_cash=1_000_000)

    @pytest.fixture
    def risk_manager(self, position_book):
        """Create CentralRiskManager with PositionBook injected"""
        crm = CentralRiskManager({'initial_capital': 1_000_000})
        crm.set_position_book(position_book)
        return crm

    # -------------------------------------------------------------------------
    # Position Queries Delegate to PositionBook
    # -------------------------------------------------------------------------

    def test_get_current_position_delegates_to_book(self, risk_manager, position_book):
        """get_current_position() should query PositionBook"""
        # Directly add a position via PositionBook
        fill = Fill.create('AAPL', 'buy', 100, 150.0, commission=1.0)
        position_book.on_fill(fill)

        # Verify CRM.get_current_position() returns PositionBook's value
        pos = risk_manager.get_current_position('AAPL')
        assert pos == 100.0

        # Verify for non-existent symbol
        assert risk_manager.get_current_position('MSFT') == 0.0

    def test_get_all_positions_delegates_to_book(self, risk_manager, position_book):
        """get_all_positions() should query PositionBook"""
        # Add multiple positions directly
        position_book.on_fill(Fill.create('AAPL', 'buy', 100, 150.0))
        position_book.on_fill(Fill.create('TSLA', 'sell', 50, 200.0))

        # Verify CRM returns all positions from PositionBook
        all_pos = risk_manager.get_all_positions()
        assert 'AAPL' in all_pos
        assert 'TSLA' in all_pos
        assert all_pos['AAPL'] == 100.0
        # Note: PositionBook stores SHORT positions as positive quantity with SHORT side
        # The get_all_positions in CRM returns absolute quantity
        assert abs(all_pos['TSLA']) == 50.0

    # -------------------------------------------------------------------------
    # update_position() Delegates to PositionBook
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_update_position_creates_fill_in_book(self, risk_manager, position_book):
        """update_position() should create a Fill in PositionBook"""
        result = await risk_manager.update_position(
            symbol='AAPL',
            side='buy',
            quantity=100,
            price=150.0,
            timestamp=datetime.now()
        )

        # Verify success
        assert result['success'] is True
        assert result['new_position'] == 100.0

        # Verify PositionBook has the position
        aapl_pos = position_book.get_position('AAPL')
        assert aapl_pos is not None
        assert aapl_pos.quantity == Decimal('100')
        assert aapl_pos.avg_entry_price == Decimal('150')

    @pytest.mark.asyncio
    async def test_update_position_sell_calculates_pnl(self, risk_manager, position_book):
        """Selling a position should calculate realized P&L via PositionBook"""
        # Buy position
        await risk_manager.update_position('AAPL', 'buy', 100, 150.0)

        # Sell at profit
        result = await risk_manager.update_position('AAPL', 'sell', 100, 165.0)

        # Verify realized P&L
        assert result['success'] is True
        assert result['new_position'] == 0.0
        expected_pnl = 100 * (165.0 - 150.0)  # $1,500
        assert result['realized_pnl'] == expected_pnl

    # -------------------------------------------------------------------------
    # Cash Balance Sync
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_cash_balance_syncs_on_buy(self, risk_manager, position_book):
        """Buying should reduce cash balance"""
        initial_cash = risk_manager.available_cash

        await risk_manager.update_position('AAPL', 'buy', 100, 150.0)

        # Cash should decrease (cost + commission)
        assert risk_manager.available_cash < initial_cash
        # Should match PositionBook's cash
        assert risk_manager.available_cash == float(position_book.get_cash_balance())

    @pytest.mark.asyncio
    async def test_cash_balance_syncs_on_sell(self, risk_manager, position_book):
        """Selling should increase cash balance"""
        await risk_manager.update_position('AAPL', 'buy', 100, 150.0)
        cash_after_buy = risk_manager.available_cash

        await risk_manager.update_position('AAPL', 'sell', 100, 165.0)

        # Cash should increase (proceeds - commission)
        assert risk_manager.available_cash > cash_after_buy
        # Should match PositionBook's cash
        assert risk_manager.available_cash == float(position_book.get_cash_balance())

    # -------------------------------------------------------------------------
    # Event Subscription
    # -------------------------------------------------------------------------

    def test_crm_receives_position_updates_via_subscription(self, risk_manager, position_book):
        """CRM's subscription callback should sync state from PositionBook"""
        # Initial state
        assert 'GOOG' not in risk_manager.current_positions

        # Add position directly to PositionBook (bypassing CRM)
        position_book.on_fill(Fill.create('GOOG', 'buy', 50, 2800.0))

        # CRM should have synced via subscription callback
        assert risk_manager.current_positions.get('GOOG') == 50.0
        assert risk_manager.current_prices.get('GOOG') == 2800.0

    # -------------------------------------------------------------------------
    # Backward Compatibility
    # -------------------------------------------------------------------------

    def test_has_position_book_returns_true_when_set(self, risk_manager):
        """has_position_book() should return True when PositionBook is injected"""
        assert risk_manager.has_position_book() is True

    def test_position_book_property_returns_injected_instance(self, risk_manager, position_book):
        """position_book property should return the injected instance"""
        assert risk_manager.position_book is position_book

    @pytest.mark.asyncio
    async def test_legacy_path_works_without_position_book(self):
        """CRM should work with legacy path when PositionBook is NOT set"""
        crm = CentralRiskManager({'initial_capital': 500_000})
        # Don't inject PositionBook

        assert crm.has_position_book() is False

        # update_position should still work via legacy path
        result = await crm.update_position('AAPL', 'buy', 100, 150.0)

        assert result['success'] is True
        assert result['new_position'] == 100.0
        assert crm.current_positions.get('AAPL') == 100.0


class TestPositionBookAsSSoT:
    """Test that PositionBook is the Single Source of Truth"""

    @pytest.fixture
    def position_book(self):
        return PositionBook(initial_cash=500_000)

    def test_all_queries_return_consistent_data(self, position_book):
        """All query methods should return consistent position data"""
        # Create a position
        position_book.on_fill(Fill.create('NVDA', 'buy', 25, 400.0))

        # All query methods should agree
        single_pos = position_book.get_position('NVDA')
        all_pos = position_book.get_all_positions()
        snapshot = position_book.get_snapshot()

        assert single_pos.quantity == all_pos['NVDA'].quantity
        assert single_pos.quantity == snapshot.positions['NVDA'].quantity

    def test_position_book_tracks_complete_state(self, position_book):
        """PositionBook should track all position attributes"""
        position_book.on_fill(Fill.create('META', 'buy', 100, 300.0, commission=1.5))

        pos = position_book.get_position('META')

        # Should have all attributes
        assert pos.quantity == Decimal('100')
        assert pos.avg_entry_price == Decimal('300')
        assert pos.total_cost_basis == Decimal('30000')  # 100 * 300
        assert len(pos.fills) == 1
        assert pos.fills[0].commission == Decimal('1.5')

    def test_position_book_calculates_accurate_pnl(self, position_book):
        """PositionBook should calculate accurate realized and unrealized P&L"""
        # Buy 100 shares
        position_book.on_fill(Fill.create('AMD', 'buy', 100, 100.0))

        # Update price
        position_book.on_price_update({'AMD': Decimal('110')})

        pos = position_book.get_position('AMD')
        assert pos.unrealized_pnl == Decimal('1000')  # (110-100) * 100

        # Sell 50 shares at $115
        update = position_book.on_fill(Fill.create('AMD', 'sell', 50, 115.0))

        # Realized P&L from this trade
        assert update.realized_pnl == Decimal('750')  # (115-100) * 50


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
