"""
Comprehensive Unit Tests for CentralRiskManager
==============================================

Professional test suite following institutional testing standards.
Tests all critical functionality including authorization, risk assessment,
position management, and emergency controls.

Author: StatArb_Gemini Testing Framework
Version: 1.0.0 (Professional Testing Standards)
"""

import pytest
import asyncio
import logging
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

# Import the components under test
from core_engine.system.central_risk_manager import (
    CentralRiskManager, RiskManagerConfig, TradingDecisionRequest, 
    TradingAuthorization, TradingDecisionType, AuthorizationLevel
)
from core_engine.system.unified_execution_engine import ExecutionUrgency

# Configure test logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Module-level fixtures
@pytest.fixture
def risk_manager_config() -> Dict[str, Any]:
    """Standard risk manager configuration for testing"""
    return {
        'max_position_size': 0.10,
        'max_daily_var': 0.05,
        'position_concentration_limit': 0.15,
        'min_signal_confidence': 0.6,
        'auto_approval_threshold': 0.01,
        'elevated_review_threshold': 0.05
    }

@pytest.fixture
def risk_manager(risk_manager_config) -> CentralRiskManager:
    """Initialize CentralRiskManager for testing"""
    return CentralRiskManager(risk_manager_config)

@pytest.fixture
def sample_trading_request() -> TradingDecisionRequest:
    """Sample trading decision request for testing"""
    return TradingDecisionRequest(
        decision_type=TradingDecisionType.POSITION_ENTRY,
        strategy_id="test_strategy",
        symbol="AAPL",
        side="buy",
        quantity=100.0,
        expected_return=0.05,
        confidence=0.8,
        market_regime="normal_volatility",
        regime_confidence=0.9,
        urgency=ExecutionUrgency.NORMAL
    )


class TestCentralRiskManager:
    """Comprehensive test suite for CentralRiskManager"""
    
    # ========================================
    # INITIALIZATION AND LIFECYCLE TESTS
    # ========================================
    
    def test_initialization(self, risk_manager_config):
        """Test CentralRiskManager initialization"""
        risk_manager = CentralRiskManager(risk_manager_config)
        
        # Verify configuration
        assert risk_manager.config.max_position_size == 0.10
        assert risk_manager.config.min_signal_confidence == 0.6
        
        # Verify initial state
        assert not risk_manager.is_initialized
        assert not risk_manager.is_operational
        assert not risk_manager.emergency_mode
        
        # Verify collections are initialized
        assert isinstance(risk_manager.current_positions, dict)
        assert isinstance(risk_manager.authorization_audit, list)
        assert isinstance(risk_manager.escalation_audit, list)
        
        logger.info("✅ Initialization test passed")
    
    @pytest.mark.asyncio
    async def test_component_lifecycle(self, risk_manager):
        """Test ISystemComponent lifecycle methods"""
        
        # Test initialization
        result = await risk_manager.initialize()
        assert result is True
        assert risk_manager.is_initialized
        
        # Test start
        result = await risk_manager.start()
        assert result is True
        assert risk_manager.is_operational
        
        # Test health check
        health = await risk_manager.health_check()
        assert health['healthy'] is True
        assert health['initialized'] is True
        assert health['operational'] is True
        
        # Test status
        status = risk_manager.get_status()
        assert status['component_type'] == 'CentralRiskManager'
        assert status['operational'] is True
        
        # Test stop
        result = await risk_manager.stop()
        assert result is True
        assert not risk_manager.is_operational
        
        logger.info("✅ Component lifecycle test passed")
    
    # ========================================
    # AUTHORIZATION TESTS
    # ========================================
    
    @pytest.mark.asyncio
    async def test_trading_authorization_approval(self, risk_manager, sample_trading_request):
        """Test successful trading authorization"""
        
        await risk_manager.initialize()
        
        # Test authorization
        authorization = await risk_manager.authorize_trading_decision(sample_trading_request)
        
        # Verify authorization result
        assert authorization.authorization_level != AuthorizationLevel.REJECTED
        assert authorization.authorized_quantity > 0
        assert authorization.request_id == sample_trading_request.request_id
        assert authorization.is_valid is True
        
        # Verify authorization is tracked
        assert authorization.authorization_id in risk_manager.active_authorizations
        assert len(risk_manager.authorization_history) > 0
        
        logger.info("✅ Trading authorization approval test passed")
    
    @pytest.mark.asyncio
    async def test_trading_authorization_rejection_low_confidence(self, risk_manager):
        """Test trading authorization rejection due to low confidence"""
        
        await risk_manager.initialize()
        
        # Create low confidence request
        low_confidence_request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            strategy_id="test_strategy",
            symbol="AAPL",
            side="buy",
            quantity=100.0,
            confidence=0.3,  # Below minimum threshold
            market_regime="normal_volatility"
        )
        
        # Test authorization
        authorization = await risk_manager.authorize_trading_decision(low_confidence_request)
        
        # Verify rejection
        assert authorization.authorization_level == AuthorizationLevel.REJECTED
        assert authorization.authorized_quantity == 0.0
        assert "confidence" in authorization.rejection_reason.lower()
        
        logger.info("✅ Low confidence rejection test passed")
    
    @pytest.mark.asyncio
    async def test_position_limit_enforcement(self, risk_manager):
        """Test position limit enforcement"""
        
        await risk_manager.initialize()
        
        # Create large position request that exceeds limits
        large_request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            strategy_id="test_strategy",
            symbol="AAPL",
            side="buy",
            quantity=50000.0,  # Very large quantity
            confidence=0.8,
            market_regime="normal_volatility"
        )
        
        # Test authorization
        authorization = await risk_manager.authorize_trading_decision(large_request)
        
        # Should be rejected or heavily reduced
        if authorization.authorization_level != AuthorizationLevel.REJECTED:
            # If not rejected, should be significantly reduced
            assert authorization.authorized_quantity < large_request.quantity
        
        logger.info("✅ Position limit enforcement test passed")
    
    # ========================================
    # RISK ASSESSMENT TESTS
    # ========================================
    
    def test_risk_impact_calculation(self, risk_manager, sample_trading_request):
        """Test risk impact calculation"""
        
        # Test risk impact calculation
        risk_impact = risk_manager._calculate_risk_impact(sample_trading_request)
        
        # Verify risk impact is calculated
        assert isinstance(risk_impact, float)
        assert risk_impact >= 0.0
        
        # Test with different volatility
        high_vol_request = sample_trading_request
        high_vol_request.volatility_estimate = 0.5
        high_vol_impact = risk_manager._calculate_risk_impact(high_vol_request)
        
        # Higher volatility should increase risk impact
        assert high_vol_impact >= risk_impact
        
        logger.info("✅ Risk impact calculation test passed")
    
    def test_position_limits_check(self, risk_manager, sample_trading_request):
        """Test position limits checking"""
        
        # Test with normal position
        result = risk_manager._check_position_limits(sample_trading_request)
        assert isinstance(result, bool)
        
        # Test with existing position
        risk_manager.current_positions["AAPL"] = 5000.0
        result_with_position = risk_manager._check_position_limits(sample_trading_request)
        
        # Should still be boolean
        assert isinstance(result_with_position, bool)
        
        logger.info("✅ Position limits check test passed")
    
    def test_concentration_limits_check(self, risk_manager, sample_trading_request):
        """Test concentration limits checking"""
        
        result = risk_manager._check_concentration_limits(sample_trading_request)
        assert isinstance(result, bool)
        
        logger.info("✅ Concentration limits check test passed")
    
    # ========================================
    # POSITION MANAGEMENT TESTS
    # ========================================
    
    def test_position_tracking(self, risk_manager):
        """Test position tracking functionality"""
        
        # Test initial state
        assert risk_manager.get_current_position("AAPL") == 0.0
        
        # Test position update
        risk_manager.update_position("AAPL", "buy", 100.0, 150.0)
        assert risk_manager.get_current_position("AAPL") == 100.0
        
        # Test sell position
        risk_manager.update_position("AAPL", "sell", 50.0, 155.0)
        assert risk_manager.get_current_position("AAPL") == 50.0
        
        # Test get all positions
        all_positions = risk_manager.get_all_positions()
        assert "AAPL" in all_positions
        assert all_positions["AAPL"] == 50.0
        
        logger.info("✅ Position tracking test passed")
    
    def test_cash_validation_buy_orders(self, risk_manager):
        """Test cash validation for BUY orders"""
        
        # Create BUY request with cash information
        buy_request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            strategy_id="test_strategy",
            symbol="AAPL",
            side="buy",
            quantity=1000.0,
            confidence=0.8
        )
        
        # Add cash availability (simulate insufficient cash)
        buy_request.available_cash = 10000.0  # Only $10k available
        buy_request.price = 150.0  # $150/share, needs $150k
        
        # Test authorized quantity calculation
        authorized_qty = risk_manager._calculate_authorized_quantity(
            buy_request, 0.05, 1.0
        )
        
        # Should be limited by available cash
        max_affordable = buy_request.available_cash / buy_request.price
        assert authorized_qty <= max_affordable
        
        logger.info("✅ Cash validation for BUY orders test passed")
    
    def test_position_validation_sell_orders(self, risk_manager):
        """Test position validation for SELL orders"""
        
        # Set up existing position
        risk_manager.current_positions["AAPL"] = 50.0
        
        # Create SELL request for more than available
        sell_request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_EXIT,
            strategy_id="test_strategy",
            symbol="AAPL",
            side="sell",
            quantity=100.0,  # More than available
            confidence=0.8
        )
        
        # Test authorized quantity calculation
        authorized_qty = risk_manager._calculate_authorized_quantity(
            sell_request, 0.05, 1.0
        )
        
        # Should be limited by available position
        assert authorized_qty <= 50.0
        
        logger.info("✅ Position validation for SELL orders test passed")
    
    # ========================================
    # REGIME INTEGRATION TESTS
    # ========================================
    
    def test_regime_risk_adjustment(self, risk_manager, sample_trading_request):
        """Test regime-based risk adjustment"""
        
        # Test normal regime
        normal_adjustment = risk_manager._get_regime_risk_adjustment(sample_trading_request)
        assert isinstance(normal_adjustment, float)
        assert normal_adjustment > 0
        
        # Test high volatility regime
        sample_trading_request.market_regime = "high_volatility"
        high_vol_adjustment = risk_manager._get_regime_risk_adjustment(sample_trading_request)
        
        # High volatility should increase risk multiplier
        assert high_vol_adjustment >= normal_adjustment
        
        logger.info("✅ Regime risk adjustment test passed")
    
    # ========================================
    # EMERGENCY CONTROLS TESTS
    # ========================================
    
    def test_emergency_shutdown(self, risk_manager):
        """Test emergency shutdown functionality"""
        
        # Add some active authorizations
        risk_manager.active_authorizations["test_auth"] = TradingAuthorization()
        
        # Test emergency shutdown
        result = risk_manager.emergency_shutdown()
        
        # Verify shutdown
        assert result is True
        assert risk_manager.emergency_mode is True
        assert not risk_manager.is_operational
        assert len(risk_manager.active_authorizations) == 0
        
        logger.info("✅ Emergency shutdown test passed")
    
    # ========================================
    # AUTHORIZATION LEVEL TESTS
    # ========================================
    
    def test_authorization_level_determination(self, risk_manager, sample_trading_request):
        """Test authorization level determination logic"""
        
        # Test automatic approval (low risk, high confidence)
        level = risk_manager._determine_authorization_level(
            0.005,  # risk_impact - Low risk
            True,   # position_check
            True,   # concentration_check
            True,   # strategy_check
            1.0,    # regime_adjustment
            sample_trading_request  # request - High confidence (0.8)
        )
        
        assert level == AuthorizationLevel.AUTOMATIC
        
        # Test elevated review (higher risk)
        level = risk_manager._determine_authorization_level(
            0.03,   # risk_impact - Higher risk
            True,   # position_check
            True,   # concentration_check
            True,   # strategy_check
            1.0,    # regime_adjustment
            sample_trading_request  # request
        )
        
        assert level in [AuthorizationLevel.STANDARD, AuthorizationLevel.ELEVATED]
        
        logger.info("✅ Authorization level determination test passed")
    
    # ========================================
    # ERROR HANDLING TESTS
    # ========================================
    
    @pytest.mark.asyncio
    async def test_authorization_error_handling(self, risk_manager):
        """Test error handling in authorization process"""
        
        await risk_manager.initialize()
        
        # Create malformed request
        malformed_request = TradingDecisionRequest()
        malformed_request.symbol = None  # Invalid symbol
        
        # Test authorization with error
        authorization = await risk_manager.authorize_trading_decision(malformed_request)
        
        # Should handle error gracefully
        assert authorization.authorization_level == AuthorizationLevel.REJECTED
        # Should have a meaningful rejection reason (confidence or other validation)
        assert len(authorization.rejection_reason) > 0
        
        logger.info("✅ Authorization error handling test passed")
    
    # ========================================
    # PERFORMANCE TESTS
    # ========================================
    
    @pytest.mark.asyncio
    async def test_authorization_performance(self, risk_manager, sample_trading_request):
        """Test authorization performance under load"""
        
        await risk_manager.initialize()
        
        # Time multiple authorizations
        start_time = datetime.now()
        
        for i in range(10):
            request = TradingDecisionRequest(
                decision_type=TradingDecisionType.POSITION_ENTRY,
                strategy_id=f"test_strategy_{i}",
                symbol="AAPL",
                side="buy",
                quantity=100.0,
                confidence=0.8
            )
            await risk_manager.authorize_trading_decision(request)
        
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        # Should complete 10 authorizations in reasonable time
        assert total_time < 1.0  # Less than 1 second
        
        logger.info(f"✅ Authorization performance test passed: {total_time:.3f}s for 10 authorizations")
    
    # ========================================
    # INTEGRATION TESTS
    # ========================================
    
    def test_component_registration(self, risk_manager):
        """Test component registration functionality"""
        
        # Create mock components
        mock_strategy_manager = Mock()
        mock_trading_engine = Mock()
        mock_regime_engine = Mock()
        
        # Test component registration
        risk_manager.set_controlled_components(
            strategy_manager=mock_strategy_manager,
            trading_engine=mock_trading_engine,
            regime_engine=mock_regime_engine
        )
        
        # Verify components are registered
        assert risk_manager.strategy_manager is mock_strategy_manager
        assert risk_manager.trading_engine is mock_trading_engine
        assert risk_manager.regime_engine is mock_regime_engine
        
        logger.info("✅ Component registration test passed")
    
    # ========================================
    # AUDIT TRAIL TESTS
    # ========================================
    
    @pytest.mark.asyncio
    async def test_authorization_audit_trail(self, risk_manager, sample_trading_request):
        """Test authorization audit trail functionality"""
        
        await risk_manager.initialize()
        
        # Perform authorization
        authorization = await risk_manager.authorize_trading_decision(sample_trading_request)
        
        # Verify audit trail
        assert len(risk_manager.authorization_history) > 0
        
        # Check audit trail properties
        audit_trail = risk_manager.authorization_audit_trail
        assert isinstance(audit_trail, list)
        
        logger.info("✅ Authorization audit trail test passed")
    
    # ========================================
    # RISK REPORTING TESTS
    # ========================================
    
    def test_risk_status_reporting(self, risk_manager):
        """Test risk status reporting"""
        
        # Get risk status
        status = risk_manager.get_risk_status()
        
        # Verify status structure
        assert 'is_operational' in status
        assert 'emergency_mode' in status
        assert 'risk_metrics' in status
        assert 'portfolio_value' in status
        
        logger.info("✅ Risk status reporting test passed")


# ========================================
# INTEGRATION TEST FIXTURES
# ========================================

@pytest.fixture
def mock_execution_engine():
    """Mock UnifiedExecutionEngine for testing"""
    mock_engine = AsyncMock()
    mock_engine.execute_authorized_trade.return_value = Mock(
        status="filled",
        filled_quantity=100.0,
        avg_fill_price=150.0
    )
    return mock_engine


class TestCentralRiskManagerIntegration:
    """Integration tests for CentralRiskManager with other components"""
    
    @pytest.mark.asyncio
    async def test_full_authorization_flow(self, risk_manager_config, mock_execution_engine):
        """Test complete authorization and execution flow"""
        
        # Initialize risk manager with mock execution engine
        risk_manager = CentralRiskManager(risk_manager_config)
        risk_manager.unified_execution_engine = mock_execution_engine
        
        await risk_manager.initialize()
        
        # Create trading request
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            strategy_id="integration_test",
            symbol="AAPL",
            side="buy",
            quantity=100.0,
            confidence=0.8,
            market_regime="normal_volatility"
        )
        
        # Test authorization
        authorization = await risk_manager.authorize_trading_decision(request)
        assert authorization.authorization_level != AuthorizationLevel.REJECTED
        
        # Test execution (if authorized)
        if authorization.authorization_level != AuthorizationLevel.REJECTED:
            result = await risk_manager.execute_authorized_trade(authorization)
            assert result is not None
        
        logger.info("✅ Full authorization flow integration test passed")


# ========================================
# TEST UTILITIES
# ========================================

def create_test_request(symbol: str = "AAPL", side: str = "buy", 
                       quantity: float = 100.0, confidence: float = 0.8) -> TradingDecisionRequest:
    """Utility function to create test trading requests"""
    return TradingDecisionRequest(
        decision_type=TradingDecisionType.POSITION_ENTRY,
        strategy_id="test_strategy",
        symbol=symbol,
        side=side,
        quantity=quantity,
        confidence=confidence,
        market_regime="normal_volatility",
        regime_confidence=0.9,
        urgency=ExecutionUrgency.NORMAL
    )


# ========================================
# PERFORMANCE BENCHMARKS
# ========================================

class TestCentralRiskManagerPerformance:
    """Performance benchmarks for CentralRiskManager"""
    
    @pytest.mark.asyncio
    async def test_concurrent_authorizations(self, risk_manager_config):
        """Test concurrent authorization handling"""
        
        risk_manager = CentralRiskManager(risk_manager_config)
        await risk_manager.initialize()
        
        # Create multiple concurrent requests
        requests = [
            create_test_request(symbol=f"STOCK_{i}", quantity=100.0)
            for i in range(20)
        ]
        
        # Time concurrent authorizations
        start_time = datetime.now()
        
        # Execute concurrent authorizations
        tasks = [
            risk_manager.authorize_trading_decision(request)
            for request in requests
        ]
        
        results = await asyncio.gather(*tasks)
        
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        # Verify all completed
        assert len(results) == 20
        assert all(isinstance(result, TradingAuthorization) for result in results)
        
        # Performance benchmark
        avg_time_per_auth = total_time / 20
        assert avg_time_per_auth < 0.1  # Less than 100ms per authorization
        
        logger.info(f"✅ Concurrent authorizations test passed: {avg_time_per_auth:.3f}s average per authorization")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
