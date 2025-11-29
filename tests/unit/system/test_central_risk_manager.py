"""
Unit Tests for Central Risk Manager
====================================

Phase 7 Week 1 Day 1: System Module Testing
File: core_engine/system/central_risk_manager.py

Test Coverage:
- Initialization and configuration
- Authorization flow (signal confidence, cash, position constraints)
- Risk assessment methods
- Quantity calculation with constraints
- Position tracking and monitoring
- Emergency control
- Integration with orchestrator

Target Coverage: 85%+
"""

import pytest
import asyncio
from unittest.mock import Mock

from core_engine.system.central_risk_manager import (
    CentralRiskManager,
    TradingDecisionRequest,
    TradingAuthorization,
    TradingDecisionType,
    AuthorizationLevel
)
from core_engine.system.unified_execution_engine import (
    ExecutionUrgency
)
from core_engine.config import RiskConfig


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def default_config():
    """Default risk manager configuration"""
    return {
        'max_position_size': 0.10,
        'max_daily_var': 0.05,
        'max_total_risk': 0.20,
        'position_concentration_limit': 0.15,
        'strategy_allocation_limit': 0.33,
        'min_signal_confidence': 0.6,
        'high_confidence_threshold': 0.8,
        'extreme_confidence_threshold': 0.9,
        'auto_approval_threshold': 0.01,
        'elevated_review_threshold': 0.05,
        'emergency_threshold': 0.10,
        'real_time_monitoring': False  # Disable for tests
    }


@pytest.fixture
def risk_manager(default_config):
    """Initialize risk manager with default config"""
    return CentralRiskManager(default_config)


@pytest.fixture
async def initialized_risk_manager(default_config):
    """Fully initialized risk manager"""
    manager = CentralRiskManager(default_config)
    await manager.initialize()
    yield manager
    # Cleanup
    await manager.stop()


@pytest.fixture
def buy_request_with_cash():
    """BUY request with sufficient cash"""
    return TradingDecisionRequest(
        decision_type=TradingDecisionType.POSITION_ENTRY,
        strategy_id="test_strategy",
        symbol="AAPL",
        side="buy",
        quantity=100.0,
        expected_return=0.05,
        confidence=0.85,  # High confidence
        current_position=0.0,
        portfolio_impact=0.01,
        risk_score=0.5,
        market_regime="low_volatility",
        regime_confidence=0.9,
        volatility_estimate=0.10,
        current_price=100.0,  # Required for risk calculation
        urgency=ExecutionUrgency.NORMAL,
        max_execution_time=3600,
        requesting_component="test",
        justification="Test trade",
        metadata={
            'available_cash': 950000.0,  # $950k available
            'price': 100.0  # $100/share
        }
    )


@pytest.fixture
def buy_request_insufficient_cash():
    """BUY request with insufficient cash"""
    return TradingDecisionRequest(
        decision_type=TradingDecisionType.POSITION_ENTRY,
        strategy_id="test_strategy",
        symbol="AAPL",
        side="buy",
        quantity=100.0,
        confidence=0.85,
        current_position=0.0,
        market_regime="low_volatility",
        regime_confidence=0.9,
        volatility_estimate=0.10,
        current_price=100.0,  # Required for risk calculation
        metadata={
            'available_cash': 5000.0,  # Only $5k available (need $10k)
            'price': 100.0
        }
    )


@pytest.fixture
def sell_request_with_position():
    """SELL request with existing position"""
    return TradingDecisionRequest(
        decision_type=TradingDecisionType.POSITION_EXIT,
        strategy_id="test_strategy",
        symbol="AAPL",
        side="sell",
        quantity=50.0,
        confidence=0.80,
        current_position=100.0,  # Have 100 shares
        market_regime="low_volatility",
        regime_confidence=0.9,
        volatility_estimate=0.10,
        current_price=100.0,  # Required for risk calculation
        metadata={
            'price': 100.0
        }
    )


@pytest.fixture
def sell_request_no_position():
    """SELL request with no position"""
    return TradingDecisionRequest(
        decision_type=TradingDecisionType.POSITION_EXIT,
        strategy_id="test_strategy",
        symbol="AAPL",
        side="sell",
        quantity=50.0,
        confidence=0.80,
        current_position=0.0,  # No position
        market_regime="low_volatility",
        regime_confidence=0.9,
        volatility_estimate=0.10,
        current_price=100.0,  # Required for risk calculation
        metadata={
            'price': 100.0
        }
    )


@pytest.fixture
def low_confidence_request():
    """Request with confidence below minimum threshold"""
    return TradingDecisionRequest(
        decision_type=TradingDecisionType.POSITION_ENTRY,
        strategy_id="test_strategy",
        symbol="AAPL",
        side="buy",
        quantity=100.0,
        confidence=0.50,  # Below 0.6 minimum
        current_position=0.0,
        market_regime="low_volatility",
        regime_confidence=0.9,
        volatility_estimate=0.10,
        current_price=100.0,  # Required for risk calculation
        metadata={
            'available_cash': 950000.0,
            'price': 100.0
        }
    )


@pytest.fixture
def high_volatility_request():
    """Request in high volatility environment"""
    return TradingDecisionRequest(
        decision_type=TradingDecisionType.POSITION_ENTRY,
        strategy_id="test_strategy",
        symbol="AAPL",
        side="buy",
        quantity=100.0,
        confidence=0.85,
        current_position=0.0,
        market_regime="high_volatility",
        regime_confidence=0.9,
        volatility_estimate=0.35,  # High volatility
        current_price=100.0,  # Required for risk calculation
        metadata={
            'available_cash': 950000.0,
            'price': 100.0
        }
    )


# ============================================================================
# TEST CLASS 1: INITIALIZATION AND CONFIGURATION
# ============================================================================

class TestInitialization:
    """Test initialization and configuration"""
    
    def test_default_initialization(self):
        """Test initialization with default config"""
        manager = CentralRiskManager()
        
        assert manager is not None
        assert manager.config is not None
        assert isinstance(manager.config, RiskConfig)
        assert manager.is_initialized is False
        assert manager.is_operational is False
        assert manager.emergency_mode is False
        assert len(manager.pending_requests) == 0
        assert len(manager.active_authorizations) == 0
        assert len(manager.current_positions) == 0
    
    def test_custom_configuration(self, default_config):
        """Test initialization with custom config"""
        # Create RiskConfig with nested structure
        from core_engine.config import PositionLimits
        custom_limits = PositionLimits(max_position_size=0.05)
        custom_config = RiskConfig(position_limits=custom_limits)
        
        manager = CentralRiskManager(custom_config)
        
        assert manager.config.max_position_size == 0.05
    
    @pytest.mark.asyncio
    async def test_full_initialization(self, risk_manager):
        """Test full initialization process"""
        result = await risk_manager.initialize()
        
        assert result is True
        assert risk_manager.is_initialized is True
        assert risk_manager.is_operational is True
        assert risk_manager.unified_execution_engine is not None
        
        # Cleanup
        await risk_manager.stop()
    
    def test_component_registration(self, risk_manager):
        """Test controlled component registration"""
        mock_strategy_manager = Mock()
        mock_trading_engine = Mock()
        mock_regime_engine = Mock()
        
        risk_manager.set_controlled_components(
            strategy_manager=mock_strategy_manager,
            trading_engine=mock_trading_engine,
            regime_engine=mock_regime_engine
        )
        
        assert risk_manager.strategy_manager == mock_strategy_manager
        assert risk_manager.trading_engine == mock_trading_engine
        assert risk_manager.regime_engine == mock_regime_engine


# ============================================================================
# TEST CLASS 2: AUTHORIZATION FLOW - BASIC
# ============================================================================

class TestAuthorizationBasic:
    """Test basic authorization flow"""
    
    @pytest.mark.asyncio
    async def test_authorize_buy_with_sufficient_cash(self, initialized_risk_manager, buy_request_with_cash):
        """Test authorization for BUY with sufficient cash"""
        authorization = await initialized_risk_manager.authorize_trading_decision(buy_request_with_cash)
        
        assert authorization is not None
        assert authorization.request_id == buy_request_with_cash.request_id
        assert authorization.authorization_level != AuthorizationLevel.REJECTED
        assert authorization.authorized_quantity > 0
        # Low volatility (0.1) applies 10% increase, so 100 → 110
        assert authorization.authorized_quantity == pytest.approx(110.0, rel=0.01)
        assert authorization.is_valid is True
        assert authorization.rejection_reason == ""
    
    @pytest.mark.asyncio
    async def test_authorize_buy_insufficient_cash(self, initialized_risk_manager, buy_request_insufficient_cash):
        """Test authorization for BUY with insufficient cash"""
        authorization = await initialized_risk_manager.authorize_trading_decision(buy_request_insufficient_cash)
        
        # Should still authorize but with reduced quantity
        assert authorization is not None
        if authorization.authorization_level != AuthorizationLevel.REJECTED:
            # Authorized quantity should be capped by cash
            max_affordable = 5000.0 / 100.0  # $5k / $100/share = 50 shares
            assert authorization.authorized_quantity <= max_affordable
            assert authorization.authorized_quantity < buy_request_insufficient_cash.quantity
        else:
            # Or rejected if below minimum viable quantity
            assert authorization.rejection_reason != ""
    
    @pytest.mark.asyncio
    async def test_authorize_sell_with_position(self, initialized_risk_manager, sell_request_with_position):
        """Test authorization for SELL with existing position"""
        # Set up position
        initialized_risk_manager.current_positions["AAPL"] = 100.0
        
        authorization = await initialized_risk_manager.authorize_trading_decision(sell_request_with_position)
        
        assert authorization is not None
        assert authorization.authorization_level != AuthorizationLevel.REJECTED
        assert authorization.authorized_quantity > 0
        # Low volatility (0.1) applies 10% increase, so 50 → 55
        assert authorization.authorized_quantity == pytest.approx(55.0, rel=0.01)
        assert authorization.authorized_quantity <= 100.0  # Still under position limit
    
    @pytest.mark.asyncio
    async def test_authorize_sell_no_position(self, initialized_risk_manager, sell_request_no_position):
        """Test authorization for SELL with no position"""
        # Ensure no position
        initialized_risk_manager.current_positions["AAPL"] = 0.0
        
        authorization = await initialized_risk_manager.authorize_trading_decision(sell_request_no_position)
        
        # Should be rejected or authorized with 0 quantity
        if authorization.authorization_level == AuthorizationLevel.REJECTED:
            assert "No position" in authorization.rejection_reason or authorization.authorized_quantity == 0.0
        else:
            assert authorization.authorized_quantity == 0.0


# ============================================================================
# TEST CLASS 3: SIGNAL CONFIDENCE VALIDATION
# ============================================================================

class TestSignalConfidence:
    """Test signal confidence validation (new requirement)"""
    
    @pytest.mark.asyncio
    async def test_reject_low_confidence_signal(self, initialized_risk_manager, low_confidence_request):
        """Test rejection of low confidence signal"""
        authorization = await initialized_risk_manager.authorize_trading_decision(low_confidence_request)
        
        assert authorization.authorization_level == AuthorizationLevel.REJECTED
        assert "confidence" in authorization.rejection_reason.lower()
        assert authorization.authorized_quantity == 0.0
    
    @pytest.mark.asyncio
    async def test_high_confidence_automatic_approval(self, initialized_risk_manager):
        """Test automatic approval for high confidence signal"""
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            strategy_id="test_strategy",
            symbol="AAPL",
            side="buy",
            quantity=50.0,  # Small quantity for low risk
            confidence=0.90,  # Extreme confidence
            current_position=0.0,
            market_regime="low_volatility",
            regime_confidence=0.9,
            volatility_estimate=0.10,
            current_price=100.0,  # Required for risk calculation
            portfolio_impact=0.005,  # Low impact
            metadata={
                'available_cash': 950000.0,
                'price': 100.0
            }
        )
        
        authorization = await initialized_risk_manager.authorize_trading_decision(request)
        
        # High confidence + low risk should get automatic approval
        assert authorization.authorization_level == AuthorizationLevel.AUTOMATIC
        assert authorization.authorized_quantity > 0
    
    @pytest.mark.asyncio
    async def test_medium_confidence_standard_approval(self, initialized_risk_manager):
        """Test standard approval for medium confidence"""
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            strategy_id="test_strategy",
            symbol="AAPL",
            side="buy",
            quantity=50.0,
            confidence=0.70,  # Medium confidence
            current_position=0.0,
            market_regime="low_volatility",
            regime_confidence=0.9,
            volatility_estimate=0.10,
            current_price=100.0,  # Required for risk calculation
            metadata={
                'available_cash': 950000.0,
                'price': 100.0
            }
        )
        
        authorization = await initialized_risk_manager.authorize_trading_decision(request)
        
        # Medium confidence should still be approved
        assert authorization.authorization_level in [AuthorizationLevel.AUTOMATIC, AuthorizationLevel.STANDARD]
        assert authorization.authorized_quantity > 0


# ============================================================================
# TEST CLASS 4: RISK ASSESSMENT METHODS
# ============================================================================

class TestRiskAssessment:
    """Test risk assessment methods"""
    
    def test_calculate_risk_impact(self, initialized_risk_manager, buy_request_with_cash):
        """Test risk impact calculation"""
        risk_impact = initialized_risk_manager._calculate_risk_impact(buy_request_with_cash)
        
        assert risk_impact > 0
        assert risk_impact < 1.0  # Should be reasonable
        
        # Low volatility regime should reduce risk
        assert risk_impact < 0.05  # With low volatility multiplier (0.7)
    
    def test_check_position_limits_pass(self, initialized_risk_manager, buy_request_with_cash):
        """Test position limit check - passing"""
        # Small position, should pass
        buy_request_with_cash.quantity = 50.0
        
        result = initialized_risk_manager._check_position_limits(buy_request_with_cash)
        
        assert result is True
    
    def test_check_position_limits_fail(self, initialized_risk_manager):
        """Test position limit check - failing"""
        request = TradingDecisionRequest(
            symbol="AAPL",
            side="buy",
            quantity=20000.0,  # Huge position (20,000 * $100 = $2M > 10% of $1M portfolio)
            current_price=100.0,  # Required for risk calculation
            metadata={'price': 100.0}
        )
        
        result = initialized_risk_manager._check_position_limits(request)
        
        assert result is False
    
    def test_check_concentration_limits(self, initialized_risk_manager, buy_request_with_cash):
        """Test concentration limit check"""
        result = initialized_risk_manager._check_concentration_limits(buy_request_with_cash)
        
        # Small position should pass
        assert result is True
    
    def test_check_strategy_limits(self, initialized_risk_manager, buy_request_with_cash):
        """Test strategy allocation limit check"""
        # Set low strategy allocation
        initialized_risk_manager.strategy_allocations["test_strategy"] = 0.20  # 20%
        
        result = initialized_risk_manager._check_strategy_limits(buy_request_with_cash)
        
        # Should pass (below 33% limit)
        assert result is True
    
    def test_get_regime_risk_adjustment(self, initialized_risk_manager, buy_request_with_cash):
        """Test regime-based risk adjustment"""
        adjustment = initialized_risk_manager._get_regime_risk_adjustment(buy_request_with_cash)
        
        assert adjustment > 0
        # Low volatility regime has 0.7 multiplier, high confidence (0.9)
        # Expected: 0.7 * 0.9 = 0.63
        assert 0.6 < adjustment < 0.7


# ============================================================================
# TEST CLASS 5: QUANTITY CALCULATION WITH CONSTRAINTS
# ============================================================================

class TestQuantityCalculation:
    """Test authorized quantity calculation"""
    
    @pytest.mark.asyncio
    async def test_quantity_capped_by_cash(self, initialized_risk_manager):
        """Test quantity capped by available cash"""
        request = TradingDecisionRequest(
            strategy_id="test",
            symbol="AAPL",
            side="buy",
            quantity=200.0,  # Want 200 shares
            confidence=0.85,
            current_position=0.0,
            market_regime="low_volatility",
            regime_confidence=0.9,
            volatility_estimate=0.10,
            current_price=100.0,  # Required for risk calculation
            metadata={
                'available_cash': 15000.0,  # Only afford 150 shares
                'price': 100.0
            }
        )
        
        risk_impact = 0.015  # Low risk
        regime_adjustment = 0.8
        
        authorized_qty = initialized_risk_manager._calculate_authorized_quantity(
            request, risk_impact, regime_adjustment
        )
        
        # Should be capped by cash
        max_affordable = 15000.0 / 100.0  # 150 shares
        assert authorized_qty <= max_affordable
        assert authorized_qty > 0  # But not zero
    
    @pytest.mark.asyncio
    async def test_quantity_capped_by_position(self, initialized_risk_manager):
        """Test SELL quantity capped by position"""
        # Set up position
        initialized_risk_manager.current_positions["AAPL"] = 50.0
        
        request = TradingDecisionRequest(
            strategy_id="test",
            symbol="AAPL",
            side="sell",
            quantity=100.0,  # Want to sell 100
            confidence=0.85,
            current_position=50.0,  # Only have 50
            market_regime="low_volatility",
            regime_confidence=0.9,
            volatility_estimate=0.10,
            current_price=100.0,  # Required for risk calculation
            metadata={'price': 100.0}
        )
        
        risk_impact = 0.01
        regime_adjustment = 0.8
        
        authorized_qty = initialized_risk_manager._calculate_authorized_quantity(
            request, risk_impact, regime_adjustment
        )
        
        # Should be capped by position
        assert authorized_qty <= 50.0
        assert authorized_qty > 0
    
    @pytest.mark.asyncio
    async def test_quantity_reduced_by_high_volatility(self, initialized_risk_manager, high_volatility_request):
        """Test quantity reduction in high volatility"""
        risk_impact = 0.02
        regime_adjustment = 1.5  # High volatility multiplier
        
        authorized_qty = initialized_risk_manager._calculate_authorized_quantity(
            high_volatility_request, risk_impact, regime_adjustment
        )
        
        # Should be significantly reduced due to high volatility (35%)
        # Up to 60% reduction possible
        assert authorized_qty < high_volatility_request.quantity
        assert authorized_qty < high_volatility_request.quantity * 0.5  # At least 50% reduction
    
    @pytest.mark.asyncio
    async def test_quantity_increased_by_low_volatility(self, initialized_risk_manager, buy_request_with_cash):
        """Test quantity increase in low volatility"""
        risk_impact = 0.005  # Very low risk
        regime_adjustment = 0.7  # Low volatility multiplier
        
        authorized_qty = initialized_risk_manager._calculate_authorized_quantity(
            buy_request_with_cash, risk_impact, regime_adjustment
        )
        
        # Should be increased by 10% for low volatility
        # But still capped by cash constraints
        assert authorized_qty > 0
        # Max increase is 1.1x, so could be up to 110 shares
        assert authorized_qty <= buy_request_with_cash.quantity * 1.2
    
    def test_quantity_precision_rounding(self, initialized_risk_manager, buy_request_with_cash):
        """Test quantity rounding to 2 decimal places"""
        risk_impact = 0.007
        regime_adjustment = 0.85
        
        authorized_qty = initialized_risk_manager._calculate_authorized_quantity(
            buy_request_with_cash, risk_impact, regime_adjustment
        )
        
        # Should be rounded to 2 decimals
        assert authorized_qty == round(authorized_qty, 2)


# ============================================================================
# TEST CLASS 6: POSITION TRACKING AND MONITORING
# ============================================================================

class TestPositionTracking:
    """Test position tracking and monitoring"""
    
    @pytest.mark.asyncio
    async def test_update_position_buy(self, initialized_risk_manager):
        """Test position update for BUY"""
        initialized_risk_manager.current_positions["AAPL"] = 50.0
        
        await initialized_risk_manager.update_position("AAPL", "buy", 25.0, 100.0)
        
        assert initialized_risk_manager.current_positions["AAPL"] == 75.0
    
    @pytest.mark.asyncio
    async def test_update_position_sell(self, initialized_risk_manager):
        """Test position update for SELL"""
        initialized_risk_manager.current_positions["AAPL"] = 100.0
        
        await initialized_risk_manager.update_position("AAPL", "sell", 30.0, 100.0)
        
        assert initialized_risk_manager.current_positions["AAPL"] == 70.0
    
    def test_get_current_position(self, initialized_risk_manager):
        """Test getting current position"""
        initialized_risk_manager.current_positions["AAPL"] = 100.0
        
        position = initialized_risk_manager.get_current_position("AAPL")
        
        assert position == 100.0
    
    def test_get_current_position_nonexistent(self, initialized_risk_manager):
        """Test getting position for symbol with no position"""
        position = initialized_risk_manager.get_current_position("NONEXISTENT")
        
        assert position == 0.0
    
    def test_get_all_positions(self, initialized_risk_manager):
        """Test getting all positions"""
        initialized_risk_manager.current_positions["AAPL"] = 100.0
        initialized_risk_manager.current_positions["GOOGL"] = 50.0
        
        positions = initialized_risk_manager.get_all_positions()
        
        assert len(positions) == 2
        assert positions["AAPL"] == 100.0
        assert positions["GOOGL"] == 50.0
        # Should be a copy, not reference
        positions["AAPL"] = 999.0
        assert initialized_risk_manager.current_positions["AAPL"] == 100.0


# ============================================================================
# TEST CLASS 7: EMERGENCY CONTROL
# ============================================================================

class TestEmergencyControl:
    """Test emergency control mechanisms"""
    
    def test_emergency_shutdown(self, initialized_risk_manager):
        """Test emergency shutdown"""
        # Add some active authorizations
        initialized_risk_manager.active_authorizations["auth1"] = TradingAuthorization()
        initialized_risk_manager.active_authorizations["auth2"] = TradingAuthorization()
        
        result = initialized_risk_manager.emergency_shutdown()
        
        assert result is True
        assert initialized_risk_manager.emergency_mode is True
        assert initialized_risk_manager.is_operational is False
        assert len(initialized_risk_manager.active_authorizations) == 0
    
    @pytest.mark.asyncio
    async def test_rejection_during_emergency_mode(self, initialized_risk_manager, buy_request_with_cash):
        """Test that requests are rejected during emergency mode"""
        initialized_risk_manager.emergency_shutdown()
        
        authorization = await initialized_risk_manager.authorize_trading_decision(buy_request_with_cash)
        
        assert authorization.authorization_level == AuthorizationLevel.REJECTED
        assert "emergency mode" in authorization.rejection_reason.lower()
    
    def test_resume_operations(self, initialized_risk_manager):
        """Test resuming operations after emergency"""
        # First shutdown
        initialized_risk_manager.emergency_shutdown()
        assert initialized_risk_manager.emergency_mode is True
        
        # Then resume
        result = initialized_risk_manager.resume_operations()
        
        assert result is True
        assert initialized_risk_manager.emergency_mode is False
        assert initialized_risk_manager.is_operational is True
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, initialized_risk_manager):
        """Test graceful shutdown"""
        initialized_risk_manager.shutdown()
        
        assert initialized_risk_manager.is_operational is False


# ============================================================================
# TEST CLASS 8: ORCHESTRATOR INTEGRATION
# ============================================================================

class TestOrchestratorIntegration:
    """Test integration with orchestrator"""
    
    @pytest.mark.asyncio
    async def test_health_check(self, initialized_risk_manager):
        """Test health check"""
        health = await initialized_risk_manager.health_check()
        
        assert health['healthy'] is True
        assert health['initialized'] is True
        assert health['operational'] is True
        assert health['component_type'] == 'CentralRiskManager'
        assert 'active_authorizations' in health
        assert 'pending_requests' in health
        assert 'portfolio_value' in health
    
    def test_get_status(self, initialized_risk_manager):
        """Test get status"""
        status = initialized_risk_manager.get_status()
        
        assert status['component_type'] == 'CentralRiskManager'
        assert status['initialized'] is True
        assert status['operational'] is True
        assert 'active_authorizations' in status
        assert 'risk_metrics' in status
        assert 'controlled_components' in status
    
    @pytest.mark.asyncio
    async def test_start_component(self, risk_manager):
        """Test starting component"""
        await risk_manager.initialize()
        
        result = await risk_manager.start()
        
        assert result is True
        assert risk_manager.is_operational is True
    
    @pytest.mark.asyncio
    async def test_stop_component(self, initialized_risk_manager):
        """Test stopping component"""
        result = await initialized_risk_manager.stop()
        
        assert result is True
        assert initialized_risk_manager.is_operational is False


# ============================================================================
# TEST CLASS 9: ADDITIONAL INTEGRATION SCENARIOS
# ============================================================================

class TestIntegrationScenarios:
    """Test integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_full_trade_lifecycle(self, initialized_risk_manager, buy_request_with_cash):
        """Test complete trade lifecycle"""
        # 1. Request authorization
        authorization = await initialized_risk_manager.authorize_trading_decision(buy_request_with_cash)
        
        assert authorization.authorization_level != AuthorizationLevel.REJECTED
        assert authorization.authorized_quantity > 0
        
        # 2. Verify authorization is stored
        assert authorization.authorization_id in initialized_risk_manager.active_authorizations
        
        # 3. Check authorization history
        assert len(initialized_risk_manager.authorization_history) > 0
        assert authorization in initialized_risk_manager.authorization_history
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_authorizations(self, initialized_risk_manager):
        """Test handling multiple concurrent authorization requests"""
        requests = [
            TradingDecisionRequest(
                strategy_id="test",
                symbol=f"SYM{i}",
                side="buy",
                quantity=50.0,
                confidence=0.85,
                current_position=0.0,
                market_regime="low_volatility",
                regime_confidence=0.9,
                volatility_estimate=0.10,
                current_price=100.0,  # Required for risk calculation
                metadata={'available_cash': 950000.0, 'price': 100.0}
            )
            for i in range(5)
        ]
        
        # Request all authorizations concurrently
        authorizations = await asyncio.gather(*[
            initialized_risk_manager.authorize_trading_decision(req)
            for req in requests
        ])
        
        # All should be processed
        assert len(authorizations) == 5
        # Most should be approved (assuming low risk)
        approved = [auth for auth in authorizations if auth.authorization_level != AuthorizationLevel.REJECTED]
        assert len(approved) >= 4  # At least 4 out of 5 approved
    
    @pytest.mark.asyncio
    async def test_position_tracking_across_trades(self, initialized_risk_manager):
        """Test position tracking across multiple trades"""
        # Trade 1: Buy 100 shares
        request1 = TradingDecisionRequest(
            strategy_id="test",
            symbol="AAPL",
            side="buy",
            quantity=100.0,
            confidence=0.85,
            current_position=0.0,
            market_regime="low_volatility",
            regime_confidence=0.9,
            volatility_estimate=0.10,
            current_price=100.0,  # Required for risk calculation
            metadata={'available_cash': 950000.0, 'price': 100.0}
        )
        
        auth1 = await initialized_risk_manager.authorize_trading_decision(request1)
        await initialized_risk_manager.update_position("AAPL", "buy", auth1.authorized_quantity, 100.0)
        
        # Trade 2: Buy another 50 shares
        request2 = TradingDecisionRequest(
            strategy_id="test",
            symbol="AAPL",
            side="buy",
            quantity=50.0,
            confidence=0.85,
            current_position=auth1.authorized_quantity,
            market_regime="low_volatility",
            regime_confidence=0.9,
            volatility_estimate=0.10,
            current_price=100.0,  # Required for risk calculation
            metadata={'available_cash': 940000.0, 'price': 100.0}
        )
        
        auth2 = await initialized_risk_manager.authorize_trading_decision(request2)
        await initialized_risk_manager.update_position("AAPL", "buy", auth2.authorized_quantity, 100.0)
        
        # Verify total position
        total_position = initialized_risk_manager.get_current_position("AAPL")
        expected_total = auth1.authorized_quantity + auth2.authorized_quantity
        assert total_position == pytest.approx(expected_total, rel=0.01)


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
