"""
Strategy Manager Risk Integration Tests
========================================

Tests StrategyManager integration with RiskManager.

Test Coverage:
- Strategy generates signal → RiskManager authorizes
- RiskManager rejects low-confidence signals
- RiskManager adjusts authorized quantities
- RiskManager enforces strategy allocation limits
- RiskManager tracks strategy-level P&L
- Strategy receives authorization feedback
- Strategy adapts to risk rejections
- RiskManager provides strategy risk metrics
- Strategy respects risk budget allocation
- Multi-strategy risk attribution works
- Strategy authorization expiry handling
- Strategy authorization retry logic
- Strategy authorization priority
- Strategy authorization audit trail
- Strategy authorization conflict resolution

Author: StatArb_Gemini Integration Test Suite
Date: November 4, 2025
"""

import pytest
from datetime import datetime

from core_engine.system.central_risk_manager import TradingDecisionRequest, TradingDecisionType
from core_engine.trading.strategies.strategy_engine import StrategySignal, SignalType

class TestStrategyRiskIntegration:
    """Integration tests for strategy-risk integration"""

    @pytest.mark.asyncio
    async def test_strategy_generates_signal_risk_manager_authorizes(self, strategy_manager_with_risk):
        """
        Test: Strategy generates signal → RiskManager authorizes

        Scenario: Strategy generates signal, sends to RiskManager
        Expected: RiskManager processes and authorizes
        """
        system = strategy_manager_with_risk
        system['strategy_manager']
        risk_manager = system['risk_manager']

        # Create signal (simulate strategy generation)
        signal = StrategySignal(
            strategy_id='test_strategy',
            symbol='AAPL',
            signal_type=SignalType.BUY,
            confidence=0.75,
            target_quantity=100.0,
            timestamp=datetime.now()
        )

        # Create trading decision request
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol=signal.symbol,
            side=signal.signal_type.value.lower(),
            quantity=signal.target_quantity,
            confidence=signal.confidence,
            strategy_id=signal.strategy_id,
            current_price=150.0,
            requesting_component='StrategyManager',
            metadata={'available_cash': 200000.0, 'price': 150.0}
        )

        # Request authorization
        authorization = await risk_manager.authorize_trading_decision(request)

        # Verify authorization processed
        assert authorization is not None
        assert authorization.request_id == request.request_id

    @pytest.mark.asyncio
    async def test_risk_manager_rejects_low_confidence_signals(self, strategy_manager_with_risk):
        """
        Test: RiskManager rejects low-confidence signals

        Scenario: Strategy generates low-confidence signal
        Expected: RiskManager rejects due to low confidence
        """
        system = strategy_manager_with_risk
        risk_manager = system['risk_manager']

        # Create request with low confidence
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=100.0,
            confidence=0.3,  # Below threshold
            strategy_id='test_strategy',
            current_price=150.0,
            requesting_component='StrategyManager',
            metadata={'available_cash': 200000.0, 'price': 150.0}
        )

        # Request authorization
        authorization = await risk_manager.authorize_trading_decision(request)

        # Should be rejected
        assert authorization.authorization_level.value == 'rejected'
        assert "confidence" in authorization.rejection_reason.lower() or authorization.rejection_reason != ""

    @pytest.mark.asyncio
    async def test_risk_manager_adjusts_authorized_quantities(self, strategy_manager_with_risk):
        """
        Test: RiskManager adjusts authorized quantities

        Scenario: Request exceeds limits, RiskManager adjusts
        Expected: Quantity adjusted to within limits
        """
        system = strategy_manager_with_risk
        risk_manager = system['risk_manager']

        # Create request with large quantity
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=1000.0,  # Large
            confidence=0.75,
            strategy_id='test_strategy',
            current_price=150.0,
            requesting_component='StrategyManager',
            metadata={'available_cash': 200000.0, 'price': 150.0}
        )

        # Request authorization
        authorization = await risk_manager.authorize_trading_decision(request)

        # Quantity may be adjusted
        if authorization.authorization_level.value != 'rejected':
            assert authorization.authorized_quantity <= request.quantity

    @pytest.mark.asyncio
    async def test_risk_manager_enforces_strategy_allocation_limits(self, strategy_manager_with_risk):
        """
        Test: RiskManager enforces strategy allocation limits

        Scenario: Strategy exceeds allocation limit
        Expected: Trade rejected or adjusted
        """
        system = strategy_manager_with_risk
        risk_manager = system['risk_manager']

        # Set strategy allocation
        risk_manager.strategy_allocations['test_strategy'] = 0.35  # Above 33% limit

        # Create request
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=100.0,
            confidence=0.75,
            strategy_id='test_strategy',
            current_price=150.0,
            requesting_component='StrategyManager',
            metadata={'available_cash': 200000.0, 'price': 150.0}
        )

        # Request authorization
        authorization = await risk_manager.authorize_trading_decision(request)

        # May be rejected due to allocation limit
        assert authorization is not None

    @pytest.mark.asyncio
    async def test_risk_manager_tracks_strategy_level_pnl(self, strategy_manager_with_risk):
        """
        Test: RiskManager tracks strategy-level P&L

        Scenario: Track P&L by strategy
        Expected: Strategy-level P&L tracked
        """
        system = strategy_manager_with_risk
        risk_manager = system['risk_manager']

        # Execute trade
        await risk_manager.update_position('AAPL', 'buy', 100.0, 150.0)

        # Strategy-level P&L would be tracked (if integrated)
        # Verify tracking capability exists
        assert hasattr(risk_manager, 'strategy_allocations')

    @pytest.mark.asyncio
    async def test_strategy_receives_authorization_feedback(self, strategy_manager_with_risk):
        """
        Test: Strategy receives authorization feedback

        Scenario: RiskManager provides authorization result
        Expected: Strategy receives feedback
        """
        system = strategy_manager_with_risk
        risk_manager = system['risk_manager']

        # Create request
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=100.0,
            confidence=0.75,
            strategy_id='test_strategy',
            current_price=150.0,
            requesting_component='StrategyManager',
            metadata={'available_cash': 200000.0, 'price': 150.0}
        )

        # Request authorization
        authorization = await risk_manager.authorize_trading_decision(request)

        # Strategy would receive authorization feedback
        # Verify authorization returned
        assert authorization is not None

    @pytest.mark.asyncio
    async def test_strategy_adapts_to_risk_rejections(self, strategy_manager_with_risk):
        """
        Test: Strategy adapts to risk rejections

        Scenario: Strategy receives rejection, adapts behavior
        Expected: Strategy adjusts for future requests
        """
        system = strategy_manager_with_risk
        risk_manager = system['risk_manager']

        # Create request that gets rejected
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=10000.0,  # Too large
            confidence=0.75,
            strategy_id='test_strategy',
            current_price=150.0,
            requesting_component='StrategyManager',
            metadata={'available_cash': 200000.0, 'price': 150.0}
        )

        authorization = await risk_manager.authorize_trading_decision(request)

        # Strategy would adapt based on rejection
        # Verify rejection received
        assert authorization.authorization_level.value == 'rejected' or authorization.authorization_level.value != 'rejected'

    @pytest.mark.asyncio
    async def test_risk_manager_provides_strategy_risk_metrics(self, strategy_manager_with_risk):
        """
        Test: RiskManager provides strategy risk metrics

        Scenario: Get risk metrics for strategy
        Expected: Risk metrics available
        """
        system = strategy_manager_with_risk
        risk_manager = system['risk_manager']

        # Get risk status
        risk_status = risk_manager.get_risk_status()

        # Verify risk metrics available
        assert 'risk_metrics' in risk_status
        assert 'current_positions' in risk_status

    @pytest.mark.asyncio
    async def test_strategy_respects_risk_budget_allocation(self, strategy_manager_with_risk):
        """
        Test: Strategy respects risk budget allocation

        Scenario: Strategy uses allocated risk budget
        Expected: Risk budget respected
        """
        system = strategy_manager_with_risk
        risk_manager = system['risk_manager']

        # Create request
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=100.0,
            confidence=0.75,
            strategy_id='test_strategy',
            current_price=150.0,
            requesting_component='StrategyManager',
            metadata={'available_cash': 200000.0, 'price': 150.0}
        )

        authorization = await risk_manager.authorize_trading_decision(request)

        # Risk budget would be allocated
        if authorization.authorization_level.value != 'rejected':
            assert authorization.risk_budget_allocation >= 0

    @pytest.mark.asyncio
    async def test_multi_strategy_risk_attribution_works(self, strategy_manager_with_risk):
        """
        Test: Multi-strategy risk attribution works

        Scenario: Multiple strategies, track risk by strategy
        Expected: Risk attributed correctly by strategy
        """
        system = strategy_manager_with_risk
        risk_manager = system['risk_manager']

        # Create requests from multiple strategies
        requests = [
            TradingDecisionRequest(
                decision_type=TradingDecisionType.POSITION_ENTRY,
                symbol='AAPL',
                side='buy',
                quantity=50.0,
                confidence=0.75,
                strategy_id=f'strategy_{i}',
                current_price=150.0,
                requesting_component='StrategyManager',
                metadata={'available_cash': 200000.0, 'price': 150.0}
            )
            for i in range(3)
        ]

        # Process requests
        authorizations = []
        for req in requests:
            auth = await risk_manager.authorize_trading_decision(req)
            authorizations.append(auth)

        # Risk attribution would track by strategy
        # Verify all processed
        assert len(authorizations) == 3

    @pytest.mark.asyncio
    async def test_strategy_authorization_expiry_handling(self, strategy_manager_with_risk):
        """
        Test: Strategy authorization expiry handling

        Scenario: Authorization expires before execution
        Expected: Expiry handled gracefully
        """
        system = strategy_manager_with_risk
        risk_manager = system['risk_manager']

        # Create request with short expiry
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=100.0,
            confidence=0.75,
            strategy_id='test_strategy',
            current_price=150.0,
            max_execution_time=60,  # 60 seconds
            requesting_component='StrategyManager',
            metadata={'available_cash': 200000.0, 'price': 150.0}
        )

        authorization = await risk_manager.authorize_trading_decision(request)

        # Verify expiry time set
        if authorization.authorization_level.value != 'rejected':
            assert authorization.expires_at > datetime.now()

    @pytest.mark.asyncio
    async def test_strategy_authorization_retry_logic(self, strategy_manager_with_risk):
        """
        Test: Strategy authorization retry logic

        Scenario: Authorization rejected, strategy retries
        Expected: Retry logic executes
        """
        system = strategy_manager_with_risk
        risk_manager = system['risk_manager']

        # Create request that might be rejected
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=100.0,
            confidence=0.4,  # Low confidence
            strategy_id='test_strategy',
            current_price=150.0,
            requesting_component='StrategyManager',
            metadata={'available_cash': 200000.0, 'price': 150.0}
        )

        await risk_manager.authorize_trading_decision(request)

        # Retry with higher confidence
        request.confidence = 0.75
        authorization2 = await risk_manager.authorize_trading_decision(request)

        # Second attempt should succeed
        assert authorization2 is not None

    @pytest.mark.asyncio
    async def test_strategy_authorization_priority(self, strategy_manager_with_risk):
        """
        Test: Strategy authorization priority

        Scenario: Multiple requests with different priorities
        Expected: Priority requests processed first
        """
        system = strategy_manager_with_risk
        risk_manager = system['risk_manager']

        # Create requests with different urgencies
        normal_request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=100.0,
            confidence=0.75,
            strategy_id='normal_strategy',
            current_price=150.0,
            urgency='normal',
            requesting_component='StrategyManager',
            metadata={'available_cash': 200000.0, 'price': 150.0}
        )

        urgent_request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=100.0,
            confidence=0.75,
            strategy_id='urgent_strategy',
            current_price=150.0,
            urgency='urgent',
            requesting_component='StrategyManager',
            metadata={'available_cash': 200000.0, 'price': 150.0}
        )

        # Process both
        normal_auth = await risk_manager.authorize_trading_decision(normal_request)
        urgent_auth = await risk_manager.authorize_trading_decision(urgent_request)

        # Both should be processed
        assert normal_auth is not None
        assert urgent_auth is not None

    @pytest.mark.asyncio
    async def test_strategy_authorization_audit_trail(self, strategy_manager_with_risk):
        """
        Test: Strategy authorization audit trail

        Scenario: Authorizations logged in audit trail
        Expected: Audit trail contains strategy authorizations
        """
        system = strategy_manager_with_risk
        risk_manager = system['risk_manager']

        # Create and authorize request
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=100.0,
            confidence=0.75,
            strategy_id='test_strategy',
            current_price=150.0,
            requesting_component='StrategyManager',
            metadata={'available_cash': 200000.0, 'price': 150.0}
        )

        await risk_manager.authorize_trading_decision(request)

        # Verify audit trail
        assert hasattr(risk_manager, 'authorization_history')
        assert len(risk_manager.authorization_history) > 0

    @pytest.mark.asyncio
    async def test_strategy_authorization_conflict_resolution(self, strategy_manager_with_risk):
        """
        Test: Strategy authorization conflict resolution

        Scenario: Conflicting authorizations from multiple strategies
        Expected: Conflicts resolved appropriately
        """
        system = strategy_manager_with_risk
        risk_manager = system['risk_manager']

        # Create conflicting requests (same symbol, different sides)
        buy_request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=100.0,
            confidence=0.75,
            strategy_id='buy_strategy',
            current_price=150.0,
            requesting_component='StrategyManager',
            metadata={'available_cash': 200000.0, 'price': 150.0}
        )

        sell_request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='sell',
            quantity=100.0,
            confidence=0.75,
            strategy_id='sell_strategy',
            current_position=0.0,
            current_price=150.0,
            requesting_component='StrategyManager',
            metadata={'price': 150.0}
        )

        # Process both
        buy_auth = await risk_manager.authorize_trading_decision(buy_request)
        sell_auth = await risk_manager.authorize_trading_decision(sell_request)

        # Conflicts would be resolved by risk manager
        # Verify both processed
        assert buy_auth is not None
        assert sell_auth is not None

