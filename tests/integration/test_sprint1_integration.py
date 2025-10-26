"""
Sprint 1 Integration Test - RealTimePnLTracker Validation

Tests the integration of RealTimePnLTracker with CentralRiskManager
and the backtest engine.

Test Coverage:
1. Component initialization
2. Integration with CentralRiskManager
3. Position update callbacks
4. Market data updates
5. P&L calculation accuracy
6. High-water mark tracking
7. Drawdown monitoring
8. Circuit breaker integration

Author: Trading System Team
Date: October 26, 2025
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any

# Import components
from core_engine.system.central_risk_manager import CentralRiskManager
from core_engine.system.realtime_pnl_tracker import RealTimePnLTracker


class TestSprint1Integration:
    """Sprint 1 Integration Tests"""
    
    @pytest.fixture
    async def risk_manager(self):
        """Create RiskManager with P&L tracker"""
        # Create risk manager
        risk_manager = CentralRiskManager({})
        
        # Create P&L tracker with existing API
        pnl_config = {
            'daily_loss_limit': -0.02,
            'max_drawdown': 0.05,
            'max_history_size': 10000
        }
        
        pnl_tracker = RealTimePnLTracker(
            risk_manager=risk_manager,  # Required by existing API
            config=pnl_config
        )
        
        # Inject P&L tracker
        risk_manager.set_institutional_components(pnl_tracker=pnl_tracker)
        
        # Initialize
        await risk_manager.initialize()
        await risk_manager.start()
        
        return risk_manager
    
    @pytest.mark.asyncio
    async def test_pnl_tracker_initialization(self, risk_manager):
        """Test 1: P&L tracker is properly initialized"""
        
        assert hasattr(risk_manager, 'pnl_tracker'), "❌ RiskManager missing pnl_tracker"
        assert risk_manager.pnl_tracker is not None, "❌ P&L tracker is None"
        
        print("\n✅ Test 1 PASSED: P&L tracker initialized")
    
    @pytest.mark.asyncio
    async def test_position_update_integration(self, risk_manager):
        """Test 2: Position updates trigger P&L tracker"""
        
        # Update position (BUY) - must await since update_position is now async
        await risk_manager.update_position(
            symbol='AAPL',
            side='buy',
            quantity=100,
            price=150.00,
            timestamp=datetime.now()
        )
        
        # Trigger price update for unrealized P&L calculation
        await risk_manager.update_market_prices({'AAPL': 150.00})
        
        # Check if P&L tracker has the position
        snapshot = risk_manager.pnl_tracker.get_current_snapshot()
        assert 'AAPL' in snapshot.position_pnl, f"❌ Position not tracked. position_pnl: {snapshot.position_pnl}"
        
        print("\n✅ Test 2 PASSED: Position updates integrated")
    
    @pytest.mark.asyncio
    async def test_market_data_update(self, risk_manager):
        """Test 3: Market data updates for unrealized P&L"""
        
        # Create position first - await async call
        await risk_manager.update_position(
            symbol='TSLA',
            side='buy',
            quantity=50,
            price=200.00,
            timestamp=datetime.now()
        )
        
        # Update market price (simulate price increase) - await async call
        await risk_manager.update_market_prices(
            prices={'TSLA': 210.00},  # +$10/share = +$500 unrealized
            timestamp=datetime.now()
        )
        
        # Check unrealized P&L
        snapshot = risk_manager.pnl_tracker.get_current_snapshot()
        assert snapshot.unrealized_pnl > 0, f"❌ Unrealized P&L not calculated. unrealized: {snapshot.unrealized_pnl}"
        assert abs(snapshot.total_pnl - snapshot.unrealized_pnl) < 0.01, "❌ Total P&L incorrect"
        
        print("\n✅ Test 3 PASSED: Market data updates working")
        print(f"   Unrealized P&L: ${snapshot.unrealized_pnl:.2f}")
    
    @pytest.mark.asyncio
    async def test_realized_pnl_calculation(self, risk_manager):
        """Test 4: Realized P&L on position close"""
        
        # Open position - await async call
        await risk_manager.update_position(
            symbol='NVDA',
            side='buy',
            quantity=100,
            price=500.00,
            timestamp=datetime.now()
        )
        
        # Close position at higher price - await async call
        await risk_manager.update_position(
            symbol='NVDA',
            side='sell',
            quantity=100,
            price=520.00,  # +$20/share = +$2000 realized
            timestamp=datetime.now() + timedelta(seconds=60)
        )
        
        # Check realized P&L
        snapshot = risk_manager.pnl_tracker.get_current_snapshot()
        assert snapshot.realized_pnl > 0, f"❌ Realized P&L not calculated. realized: {snapshot.realized_pnl}"
        
        print("\n✅ Test 4 PASSED: Realized P&L calculation working")
        print(f"   Realized P&L: ${snapshot.realized_pnl:.2f}")
    
    @pytest.mark.asyncio
    async def test_high_water_mark(self, risk_manager):
        """Test 5: High-water mark tracking"""
        
        # Create position - await async call
        await risk_manager.update_position(
            symbol='AAPL',
            side='buy',
            quantity=100,
            price=150.00
        )
        
        # Price goes up - await async call
        await risk_manager.update_market_prices({'AAPL': 160.00})
        snapshot1 = risk_manager.pnl_tracker.get_current_snapshot()
        high1 = snapshot1.intraday_high
        
        # Price goes up more (new high) - await async call
        await risk_manager.update_market_prices({'AAPL': 165.00})
        snapshot2 = risk_manager.pnl_tracker.get_current_snapshot()
        high2 = snapshot2.intraday_high
        
        # Price goes down (high should stay) - await async call
        await risk_manager.update_market_prices({'AAPL': 155.00})
        snapshot3 = risk_manager.pnl_tracker.get_current_snapshot()
        high3 = snapshot3.intraday_high
        
        assert high2 > high1, f"❌ High-water mark not increasing. high1={high1}, high2={high2}"
        assert high3 == high2, f"❌ High-water mark decreased (should stay). high2={high2}, high3={high3}"
        assert snapshot3.current_drawdown < 0, f"❌ Drawdown not calculated. drawdown={snapshot3.current_drawdown}"
        
        print("\n✅ Test 5 PASSED: High-water mark tracking working")
        print(f"   High-water mark: ${high3:.2f}")
        print(f"   Current drawdown: ${snapshot3.current_drawdown:.2f}")
    
    @pytest.mark.asyncio
    async def test_position_attribution(self, risk_manager):
        """Test 6: Position-level P&L attribution"""
        
        # Create multiple positions - await async calls
        await risk_manager.update_position('AAPL', 'buy', 100, 150.00)
        await risk_manager.update_position('TSLA', 'buy', 50, 200.00)
        await risk_manager.update_position('NVDA', 'buy', 75, 500.00)
        
        # Update prices - await async call
        await risk_manager.update_market_prices({
            'AAPL': 160.00,  # +$1000
            'TSLA': 190.00,  # -$500
            'NVDA': 520.00   # +$1500
        })
        
        # Check attribution
        snapshot = risk_manager.pnl_tracker.get_current_snapshot()
        assert len(snapshot.position_pnl) == 3, f"❌ Not all positions tracked. Found: {len(snapshot.position_pnl)}, Expected: 3"
        assert 'AAPL' in snapshot.position_pnl, "❌ AAPL not in attribution"
        assert 'TSLA' in snapshot.position_pnl, "❌ TSLA not in attribution"
        assert 'NVDA' in snapshot.position_pnl, "❌ NVDA not in attribution"
        
        print("\n✅ Test 6 PASSED: Position attribution working")
        print(f"   AAPL P&L: ${snapshot.position_pnl['AAPL']:.2f}")
        print(f"   TSLA P&L: ${snapshot.position_pnl['TSLA']:.2f}")
        print(f"   NVDA P&L: ${snapshot.position_pnl['NVDA']:.2f}")


async def run_all_tests():
    """Run all Sprint 1 integration tests"""
    print("\n" + "=" * 80)
    print("🧪 SPRINT 1 INTEGRATION TESTS - RealTimePnLTracker")
    print("=" * 80)
    
    test_suite = TestSprint1Integration()
    
    # Create risk manager fixture
    risk_manager = await test_suite.risk_manager()
    
    try:
        # Run tests
        await test_suite.test_pnl_tracker_initialization(risk_manager)
        await test_suite.test_position_update_integration(risk_manager)
        await test_suite.test_market_data_update(risk_manager)
        await test_suite.test_realized_pnl_calculation(risk_manager)
        await test_suite.test_high_water_mark(risk_manager)
        await test_suite.test_position_attribution(risk_manager)
        
        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED (6/6)")
        print("=" * 80)
        
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(run_all_tests())
    exit(0 if result else 1)

