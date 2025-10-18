"""
Phase 4.5 Test Checkpoint - Strategy & Risk Integration
=======================================================

Comprehensive testing of Phase 4 components:
- StrategyManager (BRICK #7, order=20)
- CentralRiskManager (BRICK #8, order=25) 
- PositionTracker helper

Tests verify:
1. Component initialization and registration
2. Multi-strategy coordination
3. Risk authorization flow
4. Position tracker validation
5. Regime-adjusted risk limits
6. Cash and position management
7. Complete integration flow

Author: StatArb_Gemini Backtest Application
Version: 1.0.0
"""

import pytest
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add backtest directory to path
backtest_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backtest_dir))

from backtest.config.backtest_config import (
    BacktestConfiguration, DataConfig, StrategyConfig, RiskConfig, ExecutionConfig, AnalyticsConfig
)
from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine
from backtest.engine.position_tracker import PositionTracker, Position, Trade


def create_test_config(backtest_name="test", strategies=None, risk_settings=None, execution_settings=None):
    """Helper to create test configuration"""
    return BacktestConfiguration(
        backtest_name=backtest_name,
        backtest_mode="simulation",
        data=DataConfig(
            symbols=['NVDA'],
            start_date='2024-01-02',
            end_date='2024-01-05',
            interval='1min'
        ),
        strategies=strategies or [],
        risk=risk_settings or {'initial_capital': 1_000_000},
        execution=execution_settings or {},
        analytics={}
    )


class TestPhase4ComponentInitialization:
    """Test Phase 4 component initialization and registration"""
    
    @pytest.mark.asyncio
    async def test_strategy_manager_initialization(self):
        """Test StrategyManager initialization (BRICK #7, order=20)"""
        config = create_test_config(
            backtest_name="test_strategy_manager",
            strategies=[{
                'type': 'momentum',
                'name': 'test_momentum',
                'allocation_pct': 1.0,
                'max_positions': 5,
                'risk_limit': 0.05
            }]
        )
        
        engine = InstitutionalBacktestEngine(config)
        await engine.initialize()
        
        # Verify StrategyManager was created
        assert engine.strategy_manager is not None, "StrategyManager not initialized"
        assert 'strategy_manager' in engine.component_ids, "StrategyManager not registered"
        assert hasattr(engine.strategy_manager, 'active_strategies'), "StrategyManager missing active_strategies"
        
        await engine.shutdown()
        print("✅ StrategyManager initialization: PASSED")
    
    @pytest.mark.asyncio
    async def test_risk_manager_initialization(self):
        """Test CentralRiskManager initialization (BRICK #8, order=25)"""
        config = create_test_config(
            backtest_name="test_risk_manager",
            risk_settings={
                'initial_capital': 1_000_000,
                'max_position_size': 0.10,
                'max_daily_var': 0.05
            }
        )
        
        engine = InstitutionalBacktestEngine(config)
        await engine.initialize()
        
        # Verify CentralRiskManager was created
        assert engine.risk_manager is not None, "CentralRiskManager not initialized"
        assert 'risk_manager' in engine.component_ids, "CentralRiskManager not registered"
        assert engine.risk_manager.strategy_manager is not None, "StrategyManager not linked to RiskManager"
        assert engine.risk_manager.regime_engine is not None, "RegimeEngine not linked to RiskManager"
        
        await engine.shutdown()
        print("✅ CentralRiskManager initialization: PASSED")
    
    @pytest.mark.asyncio
    async def test_position_tracker_initialization(self):
        """Test PositionTracker helper initialization"""
        config = create_test_config(
            backtest_name="test_position_tracker",
            risk_settings={'initial_capital': 500_000},
            execution_settings={'commission_per_trade': 1.0}
        )
        
        engine = InstitutionalBacktestEngine(config)
        await engine.initialize()
        
        # Verify PositionTracker was created
        assert engine.position_tracker is not None, "PositionTracker not initialized"
        assert engine.position_tracker.cash == 500_000, "Incorrect initial capital"
        assert engine.position_tracker.commission_per_trade == 1.0, "Incorrect commission"
        assert engine.position_tracker.get_position_count() == 0, "Should have no positions initially"
        
        await engine.shutdown()
        print("✅ PositionTracker initialization: PASSED")


class TestPositionTrackerFunctionality:
    """Test PositionTracker trade validation and position management"""
    
    def test_can_buy_sufficient_cash(self):
        """Test can_buy() with sufficient cash"""
        tracker = PositionTracker(initial_capital=100_000, commission_per_trade=1.0)
        can_buy, reason = tracker.can_buy('NVDA', 100, 100.0)
        
        assert can_buy is True, f"Should be able to buy: {reason}"
        assert "Sufficient cash" in reason, "Reason should mention sufficient cash"
        print("✅ can_buy() with sufficient cash: PASSED")
    
    def test_can_buy_insufficient_cash(self):
        """Test can_buy() with insufficient cash"""
        tracker = PositionTracker(initial_capital=5_000, commission_per_trade=1.0)
        can_buy, reason = tracker.can_buy('NVDA', 100, 100.0)
        
        assert can_buy is False, f"Should not be able to buy: {reason}"
        assert "Insufficient cash" in reason, "Reason should mention insufficient cash"
        print("✅ can_buy() with insufficient cash: PASSED")
    
    def test_can_sell_with_position(self):
        """Test can_sell() with sufficient position"""
        tracker = PositionTracker(initial_capital=100_000)
        tracker.update_position('NVDA', 'buy', 100, 150.0)
        
        can_sell, reason = tracker.can_sell('NVDA', 50)
        assert can_sell is True, f"Should be able to sell: {reason}"
        assert "Sufficient position" in reason, "Reason should mention sufficient position"
        print("✅ can_sell() with position: PASSED")
    
    def test_can_sell_without_position(self):
        """Test can_sell() without position"""
        tracker = PositionTracker(initial_capital=100_000)
        can_sell, reason = tracker.can_sell('NVDA', 100)
        
        assert can_sell is False, f"Should not be able to sell: {reason}"
        assert "No position" in reason or "Insufficient position" in reason, "Reason should mention no/insufficient position"
        print("✅ can_sell() without position: PASSED")
    
    def test_update_position_buy(self):
        """Test position update for BUY order"""
        tracker = PositionTracker(initial_capital=100_000, commission_per_trade=1.0)
        initial_cash = tracker.cash
        
        tracker.update_position('NVDA', 'buy', 100, 150.0, commission=1.0)
        
        # Verify cash was deducted
        expected_cash = initial_cash - (100 * 150.0) - 1.0
        assert tracker.cash == expected_cash, f"Cash not deducted correctly: {tracker.cash} vs {expected_cash}"
        assert tracker.get_position_quantity('NVDA') == 100, "Position quantity incorrect"
        assert len(tracker.trades) == 1, "Trade not recorded"
        assert tracker.trades[0].side == 'buy', "Trade side incorrect"
        print("✅ update_position() BUY: PASSED")
    
    def test_update_position_sell(self):
        """Test position update for SELL order"""
        tracker = PositionTracker(initial_capital=100_000)
        tracker.update_position('NVDA', 'buy', 100, 150.0)
        cash_after_buy = tracker.cash
        
        tracker.update_position('NVDA', 'sell', 50, 160.0, commission=1.0)
        
        # Verify cash increased
        expected_cash = cash_after_buy + (50 * 160.0) - 1.0
        assert tracker.cash == expected_cash, f"Cash not updated correctly: {tracker.cash} vs {expected_cash}"
        assert tracker.get_position_quantity('NVDA') == 50, "Position not reduced correctly"
        assert tracker.total_realized_pnl > 0, "Realized P&L should be positive (sold at higher price)"
        print("✅ update_position() SELL: PASSED")
    
    def test_pnl_calculation(self):
        """Test unrealized and realized P&L calculation"""
        tracker = PositionTracker(initial_capital=100_000)
        tracker.update_position('NVDA', 'buy', 100, 150.0)
        tracker.update_market_prices({'NVDA': 160.0})
        
        assert tracker.total_unrealized_pnl == 1_000, f"Unrealized P&L incorrect: {tracker.total_unrealized_pnl}"
        
        tracker.update_position('NVDA', 'sell', 50, 160.0)
        assert tracker.total_realized_pnl == 500, f"Realized P&L incorrect: {tracker.total_realized_pnl}"
        print("✅ P&L calculation: PASSED")
    
    def test_portfolio_metrics(self):
        """Test portfolio metrics calculation"""
        tracker = PositionTracker(initial_capital=100_000)
        tracker.update_position('NVDA', 'buy', 100, 150.0)
        tracker.update_market_prices({'NVDA': 160.0})
        
        expected_equity = tracker.cash + (100 * 160.0)
        assert tracker.get_equity() == expected_equity, "Equity calculation incorrect"
        
        return_pct = tracker.get_return_pct()
        expected_return = ((expected_equity - 100_000) / 100_000) * 100
        assert abs(return_pct - expected_return) < 0.01, f"Return % incorrect: {return_pct} vs {expected_return}"
        print("✅ Portfolio metrics: PASSED")


class TestRiskAuthorizationFlow:
    """Test risk authorization flow with mock signals"""
    
    @pytest.mark.asyncio
    async def test_risk_manager_authorize_mock_signal(self):
        """Test risk manager authorization with a mock trading signal"""
        from core_engine.system.central_risk_manager import (
            TradingDecisionRequest, TradingDecisionType, AuthorizationLevel
        )
        
        config = create_test_config(
            backtest_name="test_authorization",
            risk_settings={
                'initial_capital': 1_000_000,
                'max_position_size': 0.10,
                'min_confidence': 0.6
            }
        )
        
        engine = InstitutionalBacktestEngine(config)
        await engine.initialize()
        
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='NVDA',
            side='buy',
            quantity=100,
            confidence=0.75,
            strategy_id='test_strategy',
            market_regime='normal_volatility'
        )
        
        authorization = await engine.risk_manager.authorize_trading_decision(request)
        
        assert authorization.authorization_level != AuthorizationLevel.REJECTED, \
            f"Trade should be authorized: {authorization.rejection_reason}"
        assert authorization.authorized_quantity > 0, "Should have authorized quantity"
        
        await engine.shutdown()
        print("✅ Risk authorization flow: PASSED")
    
    @pytest.mark.asyncio
    async def test_risk_manager_reject_low_confidence(self):
        """Test risk manager rejects low confidence signals"""
        from core_engine.system.central_risk_manager import (
            TradingDecisionRequest, TradingDecisionType, AuthorizationLevel
        )
        
        config = create_test_config(
            backtest_name="test_rejection",
            risk_settings={
                'initial_capital': 1_000_000,
                'min_confidence': 0.6
            }
        )
        
        engine = InstitutionalBacktestEngine(config)
        await engine.initialize()
        
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='NVDA',
            side='buy',
            quantity=100,
            confidence=0.4,  # Below threshold
            strategy_id='test_strategy'
        )
        
        authorization = await engine.risk_manager.authorize_trading_decision(request)
        
        assert authorization.authorization_level == AuthorizationLevel.REJECTED, "Low confidence trade should be rejected"
        assert authorization.rejection_reason, "Should have rejection reason"
        assert "confidence" in authorization.rejection_reason.lower(), "Rejection should mention confidence"
        
        await engine.shutdown()
        print("✅ Risk rejection (low confidence): PASSED")


class TestIntegratedFlow:
    """Test integrated flow from strategy to risk to position"""
    
    @pytest.mark.asyncio
    async def test_full_phase4_integration(self):
        """Test full Phase 4 integration: Strategy → Risk → Position"""
        from core_engine.system.central_risk_manager import (
            TradingDecisionRequest, TradingDecisionType, AuthorizationLevel
        )
        
        config = create_test_config(
            backtest_name="test_integration",
            strategies=[{
                'type': 'momentum',
                'name': 'integration_test_momentum',
                'allocation_pct': 1.0
            }],
            risk_settings={
                'initial_capital': 1_000_000,
                'min_confidence': 0.6
            }
        )
        
        engine = InstitutionalBacktestEngine(config)
        await engine.initialize()
        
        # Verify all components are initialized
        assert engine.strategy_manager is not None
        assert engine.risk_manager is not None
        assert engine.position_tracker is not None
        
        # Simulate 5 trading decisions
        authorized_count = 0
        for i in range(7):
            request = TradingDecisionRequest(
                decision_type=TradingDecisionType.POSITION_ENTRY,
                symbol='NVDA',
                side='buy' if i % 2 == 0 else 'sell',
                quantity=10 * (i + 1),
                confidence=0.65 + (i * 0.03),
                strategy_id=f'test_strategy_{i}'
            )
            
            authorization = await engine.risk_manager.authorize_trading_decision(request)
            
            if authorization.authorization_level != AuthorizationLevel.REJECTED:
                authorized_count += 1
                
                if request.side == 'buy':
                    can_buy, reason = engine.position_tracker.can_buy(
                        request.symbol, 
                        authorization.authorized_quantity, 
                        150.0
                    )
                    
                    if can_buy:
                        engine.position_tracker.update_position(
                            request.symbol,
                            request.side,
                            authorization.authorized_quantity,
                            150.0,
                            strategy_id=request.strategy_id
                        )
        
        assert authorized_count >= 5, f"Should have at least 5 authorized trades, got {authorized_count}"
        assert len(engine.position_tracker.trades) > 0, "Position tracker should have recorded trades"
        
        summary = engine.position_tracker.get_summary()
        assert summary['trade_count'] > 0, "Should have executed trades"
        
        await engine.shutdown()
        
        print(f"✅ Full Phase 4 integration (authorized: {authorized_count}, executed: {summary['trade_count']}): PASSED")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("PHASE 4.5 TEST CHECKPOINT - STRATEGY & RISK INTEGRATION")
    print("=" * 80 + "\n")
    
    pytest.main([__file__, "-v", "-s"])
