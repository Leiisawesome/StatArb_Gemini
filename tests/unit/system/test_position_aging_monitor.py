"""
Unit tests for PositionAgingMonitor

Tests position aging tracking, strategy-specific holding limits,
auto-close expired positions, and alert generation.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

import sys
sys.path.insert(0, '/Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini')

from core_engine.system.position_aging_monitor import (
    PositionAgingMonitor,
    PositionAgeCategory,
    StrategyType
)

@pytest.fixture
def mock_risk_manager():
    """Mock CentralRiskManager"""
    risk_manager = Mock()
    risk_manager.current_positions = {
        'AAPL': 100.0,
        'TSLA': 50.0,
        'NVDA': 75.0
    }
    return risk_manager

@pytest.fixture
def mock_execution_engine():
    """Mock UnifiedExecutionEngine"""
    return Mock()

@pytest.fixture
def aging_monitor(mock_risk_manager, mock_execution_engine):
    """Create PositionAgingMonitor instance"""
    config = {
        'arbitrage_days': 2,
        'mean_reversion_days': 3,
        'stat_arb_days': 5,
        'momentum_days': 7,
        'check_interval_seconds': 3600,
        'auto_close_enabled': True
    }
    return PositionAgingMonitor(mock_risk_manager, mock_execution_engine, config)

class TestPositionAgingMonitor:
    """Test suite for PositionAgingMonitor"""

    def test_initialization(self, aging_monitor):
        """Test monitor initializes correctly"""
        assert aging_monitor is not None
        assert aging_monitor.auto_close_enabled is True
        assert aging_monitor.max_holding_periods[StrategyType.ARBITRAGE] == 2
        assert aging_monitor.max_holding_periods[StrategyType.MOMENTUM] == 7
        assert aging_monitor.total_checks == 0
        assert aging_monitor.total_auto_closes == 0

    def test_record_position_entry(self, aging_monitor):
        """Test recording position entry"""
        entry_time = datetime.now()

        aging_monitor.record_position_entry(
            symbol='AAPL',
            quantity=100,
            entry_price=150.0,
            strategy_id='momentum_1',
            strategy_type='MOMENTUM',
            entry_time=entry_time
        )

        assert 'AAPL' in aging_monitor.position_entries
        entry = aging_monitor.position_entries['AAPL']
        assert entry['symbol'] == 'AAPL'
        assert entry['quantity'] == 100
        assert entry['entry_price'] == 150.0
        assert entry['strategy_id'] == 'momentum_1'
        assert entry['strategy_type'] == StrategyType.MOMENTUM

    def test_record_position_exit(self, aging_monitor):
        """Test recording position exit"""
        # First record entry
        aging_monitor.record_position_entry(
            symbol='AAPL',
            quantity=100,
            entry_price=150.0,
            strategy_id='momentum_1',
            strategy_type='MOMENTUM'
        )

        assert 'AAPL' in aging_monitor.position_entries

        # Now record exit
        aging_monitor.record_position_exit('AAPL')

        assert 'AAPL' not in aging_monitor.position_entries

    @pytest.mark.asyncio
    async def test_check_fresh_position(self, aging_monitor):
        """Test checking fresh position (<50% of limit)"""
        # Record position opened 1 day ago (momentum limit is 7 days)
        entry_time = datetime.now() - timedelta(days=1)

        aging_monitor.record_position_entry(
            symbol='AAPL',
            quantity=100,
            entry_price=150.0,
            strategy_id='momentum_1',
            strategy_type='MOMENTUM',
            entry_time=entry_time
        )

        # Check aging
        report = await aging_monitor.check_position_aging()

        assert report.total_positions == 1
        assert report.fresh_count == 1
        assert report.aging_count == 0
        assert report.stale_count == 0
        assert report.expired_count == 0

        # Check position info
        position = report.positions[0]
        assert position.symbol == 'AAPL'
        assert position.age_category == PositionAgeCategory.FRESH
        assert position.age_days < 3.5  # <50% of 7 days

    @pytest.mark.asyncio
    async def test_check_aging_position(self, aging_monitor):
        """Test checking aging position (50-80% of limit)"""
        # Record position opened 5 days ago (momentum limit is 7 days = 71%)
        entry_time = datetime.now() - timedelta(days=5)

        aging_monitor.record_position_entry(
            symbol='AAPL',
            quantity=100,
            entry_price=150.0,
            strategy_id='momentum_1',
            strategy_type='MOMENTUM',
            entry_time=entry_time
        )

        # Check aging
        report = await aging_monitor.check_position_aging()

        assert report.total_positions == 1
        assert report.fresh_count == 0
        assert report.aging_count == 1
        assert report.stale_count == 0
        assert report.expired_count == 0

        position = report.positions[0]
        assert position.age_category == PositionAgeCategory.AGING

    @pytest.mark.asyncio
    async def test_check_stale_position(self, aging_monitor):
        """Test checking stale position (80-100% of limit)"""
        # Record position opened 6 days ago (momentum limit is 7 days = 86%)
        entry_time = datetime.now() - timedelta(days=6)

        aging_monitor.record_position_entry(
            symbol='AAPL',
            quantity=100,
            entry_price=150.0,
            strategy_id='momentum_1',
            strategy_type='MOMENTUM',
            entry_time=entry_time
        )

        # Check aging
        report = await aging_monitor.check_position_aging()

        assert report.total_positions == 1
        assert report.stale_count == 1

        position = report.positions[0]
        assert position.age_category == PositionAgeCategory.STALE

        # Should have alert action
        assert len(report.actions_taken) > 0
        assert 'stale' in report.actions_taken[0].lower()

    @pytest.mark.asyncio
    async def test_check_expired_position(self, aging_monitor):
        """Test checking expired position (>100% of limit)"""
        # Record position opened 8 days ago (momentum limit is 7 days = 114%)
        entry_time = datetime.now() - timedelta(days=8)

        aging_monitor.record_position_entry(
            symbol='AAPL',
            quantity=100,
            entry_price=150.0,
            strategy_id='momentum_1',
            strategy_type='MOMENTUM',
            entry_time=entry_time
        )

        # Check aging
        report = await aging_monitor.check_position_aging()

        assert report.total_positions == 1
        assert report.expired_count == 1

        position = report.positions[0]
        assert position.age_category == PositionAgeCategory.EXPIRED

        # Should have auto-close action (if enabled)
        if aging_monitor.auto_close_enabled:
            assert len(report.actions_taken) > 0
            assert 'auto-closed' in report.actions_taken[0].lower() or 'expired' in report.actions_taken[0].lower()

    @pytest.mark.asyncio
    async def test_multiple_positions_different_ages(self, aging_monitor):
        """Test checking multiple positions with different ages"""
        now = datetime.now()

        # Fresh position (1 day old, momentum = 7 days)
        aging_monitor.record_position_entry(
            'AAPL', 100, 150.0, 'momentum_1', 'MOMENTUM',
            entry_time=now - timedelta(days=1)
        )

        # Aging position (5 days old, momentum = 7 days)
        aging_monitor.record_position_entry(
            'TSLA', 50, 200.0, 'momentum_2', 'MOMENTUM',
            entry_time=now - timedelta(days=5)
        )

        # Stale position (6 days old, momentum = 7 days)
        aging_monitor.record_position_entry(
            'NVDA', 75, 450.0, 'momentum_3', 'MOMENTUM',
            entry_time=now - timedelta(days=6)
        )

        # Expired position (8 days old, momentum = 7 days)
        aging_monitor.record_position_entry(
            'GOOGL', 25, 140.0, 'momentum_4', 'MOMENTUM',
            entry_time=now - timedelta(days=8)
        )

        report = await aging_monitor.check_position_aging()

        assert report.total_positions == 4
        assert report.fresh_count == 1
        assert report.aging_count == 1
        assert report.stale_count == 1
        assert report.expired_count == 1

    @pytest.mark.asyncio
    async def test_different_strategy_types(self, aging_monitor):
        """Test different strategies have different holding limits"""
        now = datetime.now()

        # Arbitrage position (3 days old, limit is 2 days - EXPIRED)
        aging_monitor.record_position_entry(
            'AAPL', 100, 150.0, 'arb_1', 'ARBITRAGE',
            entry_time=now - timedelta(days=3)
        )

        # Momentum position (3 days old, limit is 7 days - FRESH)
        aging_monitor.record_position_entry(
            'TSLA', 50, 200.0, 'momentum_1', 'MOMENTUM',
            entry_time=now - timedelta(days=3)
        )

        report = await aging_monitor.check_position_aging()

        assert report.total_positions == 2

        # Find positions by symbol
        arb_pos = next(p for p in report.positions if p.symbol == 'AAPL')
        momentum_pos = next(p for p in report.positions if p.symbol == 'TSLA')

        # Arbitrage should be expired (3 > 2 days)
        assert arb_pos.age_category == PositionAgeCategory.EXPIRED
        assert arb_pos.max_age_days == 2

        # Momentum should be fresh (3 < 50% of 7 days)
        assert momentum_pos.age_category == PositionAgeCategory.FRESH
        assert momentum_pos.max_age_days == 7

    @pytest.mark.asyncio
    async def test_auto_close_disabled(self, aging_monitor):
        """Test auto-close can be disabled"""
        aging_monitor.auto_close_enabled = False

        # Record expired position
        entry_time = datetime.now() - timedelta(days=8)
        aging_monitor.record_position_entry(
            'AAPL', 100, 150.0, 'momentum_1', 'MOMENTUM',
            entry_time=entry_time
        )

        report = await aging_monitor.check_position_aging()

        assert report.expired_count == 1
        # Should NOT have auto-close action
        assert not any('auto-closed' in action.lower() for action in report.actions_taken)

    def test_get_aging_statistics(self, aging_monitor):
        """Test getting aging statistics"""
        stats = aging_monitor.get_aging_statistics()

        assert 'total_checks' in stats
        assert 'total_auto_closes' in stats
        assert 'total_alerts' in stats
        assert 'is_running' in stats
        assert stats['total_checks'] == 0
        assert stats['is_running'] is False

    @pytest.mark.asyncio
    async def test_aging_report_generation(self, aging_monitor):
        """Test generating aging report"""
        # Add some positions
        now = datetime.now()
        aging_monitor.record_position_entry(
            'AAPL', 100, 150.0, 'momentum_1', 'MOMENTUM',
            entry_time=now - timedelta(days=5)
        )

        # Run check to populate history
        await aging_monitor.check_position_aging()

        # Generate report
        report_str = aging_monitor.generate_aging_report()

        assert 'POSITION AGING MONITOR REPORT' in report_str
        assert 'Total Checks:' in report_str
        assert 'CURRENT POSITION STATUS:' in report_str
        assert 'STRATEGY HOLDING LIMITS:' in report_str

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

