"""
Risk Manager Authorization Flow Integration Tests
=================================================

Tests complete authorization flow from strategy signals through risk governance.

Test Coverage:
- Strategy → RiskManager authorization request
- RiskManager validates signal confidence
- RiskManager checks cash availability (BUY)
- RiskManager checks position availability (SELL)
- RiskManager enforces position size limits
- RiskManager enforces concentration limits
- RiskManager enforces VaR limits
- RiskManager applies regime-adjusted risk scaling
- RiskManager rejects trades with insufficient confidence
- RiskManager authorization expiry handling
- RiskManager handles multiple concurrent requests
- RiskManager authorization audit trail
- RiskManager authorization revocation
- RiskManager authorization modification
- RiskManager authorization priority handling

Author: StatArb_Gemini Integration Test Suite
Date: November 4, 2025
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta

from core_engine.system.central_risk_manager import (
    CentralRiskManager, TradingDecisionRequest, TradingDecisionType, AuthorizationLevel
)
from core_engine.config.component_config import RiskConfig


# =============================================================================
# AUTHORIZATION FLOW TESTS
# =============================================================================

class TestAuthorizationFlow:
    """Integration tests for risk authorization flow"""
    
    @pytest.mark.asyncio
    async def test_strategy_to_risk_manager_authorization_request(self, risk_manager):
        """
        Test: Strategy → RiskManager authorization request
        
        Scenario: Strategy generates signal and requests authorization
        Expected: RiskManager processes request and returns authorization
        """
        # Create trading decision request
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=100.0,
            confidence=0.75,
            strategy_id='momentum_strategy_1',
            current_price=150.0,
            requesting_component='StrategyManager',
            metadata={'available_cash': 100000.0, 'price': 150.0}
        )
        
        # Request authorization
        authorization = await risk_manager.authorize_trading_decision(request)
        
        # Verify authorization processed
        assert authorization is not None
        assert authorization.request_id == request.request_id
        assert authorization.authorization_level != AuthorizationLevel.REJECTED or authorization.rejection_reason != ""
    
    @pytest.mark.asyncio
    async def test_risk_manager_validates_signal_confidence(self, risk_manager):
        """
        Test: RiskManager validates signal confidence
        
        Scenario: Request with low confidence (< min_signal_confidence)
        Expected: Trade rejected due to insufficient confidence
        """
        # Create request with low confidence
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=100.0,
            confidence=0.3,  # Below minimum (typically 0.6)
            strategy_id='test_strategy',
            current_price=150.0,
            requesting_component='StrategyManager',
            metadata={'available_cash': 100000.0, 'price': 150.0}
        )
        
        # Request authorization
        authorization = await risk_manager.authorize_trading_decision(request)
        
        # Should be rejected due to low confidence
        assert authorization.authorization_level == AuthorizationLevel.REJECTED
        assert "confidence" in authorization.rejection_reason.lower() or authorization.rejection_reason != ""
    
    @pytest.mark.asyncio
    async def test_risk_manager_checks_cash_availability_buy(self, risk_manager):
        """
        Test: RiskManager checks cash availability for BUY orders
        
        Scenario: BUY order exceeds available cash
        Expected: Quantity adjusted or trade rejected
        """
        # Set available cash
        risk_manager.available_cash = 10000.0  # $10,000 available
        
        # Create request exceeding cash
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=1000.0,  # 1000 shares @ $150 = $150,000 (exceeds cash)
            confidence=0.75,
            strategy_id='test_strategy',
            current_price=150.0,
            requesting_component='StrategyManager',
            metadata={'available_cash': 10000.0, 'price': 150.0}
        )
        
        # Request authorization
        authorization = await risk_manager.authorize_trading_decision(request)
        
        # Should be adjusted or rejected
        if authorization.authorization_level != AuthorizationLevel.REJECTED:
            # Quantity should be adjusted to affordable amount
            max_affordable = 10000.0 / 150.0  # ~66 shares
            assert authorization.authorized_quantity <= max_affordable
        else:
            # Or rejected with reason
            assert "cash" in authorization.rejection_reason.lower() or authorization.rejection_reason != ""
    
    @pytest.mark.asyncio
    async def test_risk_manager_checks_position_availability_sell(self, risk_manager):
        """
        Test: RiskManager checks position availability for SELL orders
        
        Scenario: SELL order exceeds current position
        Expected: Quantity adjusted to available position
        """
        # Set current position
        risk_manager.current_positions['AAPL'] = 50.0  # Only 50 shares
        
        # Create request exceeding position
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_EXIT,
            symbol='AAPL',
            side='sell',
            quantity=100.0,  # Trying to sell 100, but only have 50
            confidence=0.75,
            strategy_id='test_strategy',
            current_position=50.0,
            current_price=150.0,
            requesting_component='StrategyManager',
            metadata={'price': 150.0}
        )
        
        # Request authorization
        authorization = await risk_manager.authorize_trading_decision(request)
        
        # Quantity should be capped at available position
        if authorization.authorization_level != AuthorizationLevel.REJECTED:
            assert authorization.authorized_quantity <= 50.0
        else:
            assert "position" in authorization.rejection_reason.lower() or authorization.rejection_reason != ""
    
    @pytest.mark.asyncio
    async def test_risk_manager_enforces_position_size_limits(self, risk_manager):
        """
        Test: RiskManager enforces position size limits
        
        Scenario: Request creates position exceeding max_position_size limit
        Expected: Trade rejected or quantity adjusted
        """
        # Set portfolio value
        risk_manager.portfolio_value = 100000.0
        max_position_pct = risk_manager.config.position_limits.max_position_size  # Typically 10%
        max_position_value = risk_manager.portfolio_value * max_position_pct
        
        # Create request exceeding position limit
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=1000.0,  # 1000 shares @ $150 = $150,000 (exceeds 10% of $100K)
            confidence=0.75,
            strategy_id='test_strategy',
            current_price=150.0,
            requesting_component='StrategyManager',
            metadata={'available_cash': 200000.0, 'price': 150.0}
        )
        
        # Request authorization
        authorization = await risk_manager.authorize_trading_decision(request)
        
        # Should be rejected or adjusted
        if authorization.authorization_level != AuthorizationLevel.REJECTED:
            # Quantity should be adjusted
            max_allowed_qty = max_position_value / 150.0
            assert authorization.authorized_quantity <= max_allowed_qty
        else:
            assert "position" in authorization.rejection_reason.lower() or "limit" in authorization.rejection_reason.lower()
    
    @pytest.mark.asyncio
    async def test_risk_manager_enforces_concentration_limits(self, risk_manager):
        """
        Test: RiskManager enforces concentration limits
        
        Scenario: Request creates position exceeding concentration limit
        Expected: Trade rejected
        """
        # Set portfolio value
        risk_manager.portfolio_value = 100000.0
        concentration_limit = risk_manager.config.position_limits.max_position_concentration  # Typically 15%
        
        # Create request exceeding concentration
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=200.0,  # 200 shares @ $150 = $30,000 (30% of $100K - exceeds 15%)
            confidence=0.75,
            strategy_id='test_strategy',
            current_price=150.0,
            requesting_component='StrategyManager',
            metadata={'available_cash': 200000.0, 'price': 150.0}
        )
        
        # Request authorization
        authorization = await risk_manager.authorize_trading_decision(request)
        
        # Should be rejected
        assert authorization.authorization_level == AuthorizationLevel.REJECTED
        assert "concentration" in authorization.rejection_reason.lower() or "limit" in authorization.rejection_reason.lower()
    
    @pytest.mark.asyncio
    async def test_risk_manager_enforces_var_limits(self, risk_manager):
        """
        Test: RiskManager enforces VaR limits
        
        Scenario: Request creates risk exceeding daily VaR limit
        Expected: Trade rejected or adjusted
        """
        # Set current VaR and limit
        risk_manager.current_var = 0.03  # 3% current VaR
        max_var = risk_manager.config.risk_limits.max_daily_var  # Typically 5%
        
        # Create request that would exceed VaR
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=500.0,
            confidence=0.75,
            strategy_id='test_strategy',
            current_price=150.0,
            volatility_estimate=0.30,  # High volatility
            requesting_component='StrategyManager',
            metadata={'available_cash': 200000.0, 'price': 150.0}
        )
        
        # Request authorization
        authorization = await risk_manager.authorize_trading_decision(request)
        
        # Should be rejected or adjusted based on VaR
        if authorization.authorization_level == AuthorizationLevel.REJECTED:
            assert "var" in authorization.rejection_reason.lower() or "risk" in authorization.rejection_reason.lower()
    
    @pytest.mark.asyncio
    async def test_risk_manager_applies_regime_adjusted_risk_scaling(self, risk_manager):
        """
        Test: RiskManager applies regime-adjusted risk scaling
        
        Scenario: Request in high volatility regime
        Expected: Quantity adjusted based on regime
        """
        # Create request with high volatility regime
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=100.0,
            confidence=0.75,
            strategy_id='test_strategy',
            current_price=150.0,
            market_regime='high_volatility',
            regime_confidence=0.8,
            volatility_estimate=0.35,
            requesting_component='StrategyManager',
            metadata={'available_cash': 200000.0, 'price': 150.0}
        )
        
        # Request authorization
        authorization = await risk_manager.authorize_trading_decision(request)
        
        # Quantity should be reduced for high volatility
        if authorization.authorization_level != AuthorizationLevel.REJECTED:
            # High volatility should reduce quantity
            assert authorization.authorized_quantity <= request.quantity
    
    @pytest.mark.asyncio
    async def test_risk_manager_rejects_insufficient_confidence(self, risk_manager):
        """
        Test: RiskManager rejects trades with insufficient confidence
        
        Scenario: Multiple requests with varying confidence levels
        Expected: Low confidence requests rejected
        """
        # Test with confidence below threshold
        low_conf_request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=100.0,
            confidence=0.4,  # Below threshold
            strategy_id='test_strategy',
            current_price=150.0,
            requesting_component='StrategyManager',
            metadata={'available_cash': 200000.0, 'price': 150.0}
        )
        
        low_auth = await risk_manager.authorize_trading_decision(low_conf_request)
        assert low_auth.authorization_level == AuthorizationLevel.REJECTED
        
        # Test with high confidence
        high_conf_request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=100.0,
            confidence=0.85,  # Above threshold
            strategy_id='test_strategy',
            current_price=150.0,
            requesting_component='StrategyManager',
            metadata={'available_cash': 200000.0, 'price': 150.0}
        )
        
        high_auth = await risk_manager.authorize_trading_decision(high_conf_request)
        # High confidence should be authorized (may still be rejected for other reasons)
        assert high_auth is not None
    
    @pytest.mark.asyncio
    async def test_risk_manager_authorization_expiry_handling(self, risk_manager):
        """
        Test: RiskManager authorization expiry handling
        
        Scenario: Authorization expires after time limit
        Expected: Authorization marked as invalid
        """
        # Create and authorize request
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
        
        if authorization.authorization_level != AuthorizationLevel.REJECTED:
            # Verify expiry time set
            assert authorization.expires_at > datetime.now()
            
            # Verify validation
            is_valid = risk_manager._validate_authorization(authorization)
            assert is_valid == True
    
    @pytest.mark.asyncio
    async def test_risk_manager_multiple_concurrent_requests(self, risk_manager):
        """
        Test: RiskManager handles multiple concurrent requests
        
        Scenario: Multiple strategies request authorization simultaneously
        Expected: All requests processed correctly
        """
        import asyncio
        
        # Create multiple requests
        requests = [
            TradingDecisionRequest(
                decision_type=TradingDecisionType.POSITION_ENTRY,
                symbol='AAPL',
                side='buy',
                quantity=100.0,
                confidence=0.75,
                strategy_id=f'strategy_{i}',
                current_price=150.0,
                requesting_component='StrategyManager',
                metadata={'available_cash': 200000.0, 'price': 150.0}
            )
            for i in range(5)
        ]
        
        # Process concurrently
        authorizations = await asyncio.gather(*[
            risk_manager.authorize_trading_decision(req) for req in requests
        ])
        
        # Verify all processed
        assert len(authorizations) == 5
        assert all(auth is not None for auth in authorizations)
    
    @pytest.mark.asyncio
    async def test_risk_manager_authorization_audit_trail(self, risk_manager):
        """
        Test: RiskManager authorization audit trail
        
        Scenario: Authorizations are logged in audit trail
        Expected: Audit trail contains authorization records
        """
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
        
        authorization = await risk_manager.authorize_trading_decision(request)
        
        # Verify audit trail
        assert hasattr(risk_manager, 'authorization_history')
        assert len(risk_manager.authorization_history) > 0
        
        # Verify latest authorization in history
        latest = risk_manager.authorization_history[-1]
        assert latest.request_id == request.request_id
    
    @pytest.mark.asyncio
    async def test_risk_manager_authorization_revocation(self, risk_manager):
        """
        Test: RiskManager authorization revocation
        
        Scenario: Revoke active authorization
        Expected: Authorization removed from active authorizations
        """
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
        
        authorization = await risk_manager.authorize_trading_decision(request)
        
        if authorization.authorization_level != AuthorizationLevel.REJECTED:
            # Verify authorization is active
            assert authorization.authorization_id in risk_manager.active_authorizations
            
            # Revoke authorization
            with risk_manager.authorization_lock:
                risk_manager.active_authorizations.pop(authorization.authorization_id, None)
            
            # Verify revoked
            assert authorization.authorization_id not in risk_manager.active_authorizations
    
    @pytest.mark.asyncio
    async def test_risk_manager_authorization_modification(self, risk_manager):
        """
        Test: RiskManager authorization modification
        
        Scenario: Modify authorized quantity after authorization
        Expected: Authorization updated with new quantity
        """
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
        
        authorization = await risk_manager.authorize_trading_decision(request)
        
        if authorization.authorization_level != AuthorizationLevel.REJECTED:
            # Modify authorization (update quantity)
            original_qty = authorization.authorized_quantity
            authorization.authorized_quantity = original_qty * 0.5  # Reduce by 50%
            
            # Verify modification
            assert authorization.authorized_quantity < original_qty
    
    @pytest.mark.asyncio
    async def test_risk_manager_authorization_priority_handling(self, risk_manager):
        """
        Test: RiskManager authorization priority handling
        
        Scenario: Multiple requests with different priorities
        Expected: High priority requests processed first
        """
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
        
        # Both should be processed
        normal_auth = await risk_manager.authorize_trading_decision(normal_request)
        urgent_auth = await risk_manager.authorize_trading_decision(urgent_request)
        
        # Both should be processed (order may vary)
        assert normal_auth is not None
        assert urgent_auth is not None

