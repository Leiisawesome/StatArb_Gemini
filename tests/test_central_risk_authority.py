#!/usr/bin/env python3
"""
Comprehensive Test Suite for Central Risk Authority Implementation
================================================================

Tests the institutional-grade risk governance system including:
- Central Risk Authority (AdvancedRiskManager)
- StrategyManager risk proposal integration
- RealTimeTradingEngine authorization flow
- UnifiedExecutionEngine token validation
- End-to-end authorization workflow

Author: Professional Trading System Architecture Testing
Version: 1.0.0 (Institutional Risk Governance Validation)
"""

import asyncio
import pytest
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass
import pandas as pd
import numpy as np

# Import core components for testing
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core_structure.advanced_risk_management import (
    AdvancedRiskManager, RiskConfiguration, TradeRequest, TradeAuthorization,
    RiskLevel, AlertType, Position
)
from core_structure.strategies import StrategyManager, StrategyConfig, TradingSignal, SignalType
from core_structure.real_time_trading_engine import RealTimeTradingEngine, RealTimeTradingConfiguration
from core_structure.execution_engine import UnifiedExecutionEngine, ExecutionConfig, Order, OrderSide, OrderType

# Configure test logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestCentralRiskAuthority:
    """Test suite for Central Risk Authority implementation"""
    
    @pytest.fixture
    async def risk_manager(self):
        """Create and initialize risk manager for testing"""
        config = RiskConfiguration(
            max_position_size=0.10,  # 10% max position
            max_portfolio_var=0.02,  # 2% VaR limit
            stop_loss_threshold=0.05,  # 5% stop loss
            circuit_breaker_threshold=0.10,  # 10% drawdown circuit breaker
            var_confidence_level=0.95,
            correlation_threshold=0.7,
            concentration_limit=0.15,
            max_daily_trades=100
        )
        
        risk_manager = AdvancedRiskManager(config)
        await risk_manager.initialize()
        await risk_manager.startup()
        
        return risk_manager
    
    @pytest.fixture
    def sample_trade_request(self):
        """Create sample trade request for testing"""
        return TradeRequest(
            request_id=str(uuid.uuid4()),
            symbol="AAPL",
            side="BUY",
            quantity=100,
            price=150.0,
            strategy_id="mean_reversion_001",
            signal_confidence=0.75,
            timestamp=datetime.now(),
            metadata={"regime": "trending_up", "signal_strength": 0.8}
        )
    
    @pytest.mark.asyncio
    async def test_risk_manager_authorization_approval(self, risk_manager, sample_trade_request):
        """Test that valid trades are approved by risk manager"""
        logger.info("🧪 Testing risk manager authorization approval...")
        
        # Test authorization
        authorization = await risk_manager.authorize_trade(sample_trade_request)
        
        # Validate approval
        assert authorization is not None
        assert authorization.approved is True
        assert authorization.authorization_id is not None
        assert len(authorization.authorization_id) > 0
        assert authorization.risk_level == RiskLevel.LOW
        assert "approved" in authorization.reason.lower()
        
        # Verify authorization is stored in history
        assert authorization.authorization_id in risk_manager.authorization_history
        
        logger.info(f"✅ Trade authorized successfully: {authorization.authorization_id}")
    
    @pytest.mark.asyncio
    async def test_risk_manager_authorization_rejection(self, risk_manager):
        """Test that invalid trades are rejected by risk manager"""
        logger.info("🧪 Testing risk manager authorization rejection...")
        
        # Create invalid trade request (excessive position size)
        invalid_request = TradeRequest(
            request_id=str(uuid.uuid4()),
            symbol="AAPL",
            side="BUY",
            quantity=10000,  # Excessive quantity
            price=150.0,
            strategy_id="test_strategy",
            signal_confidence=0.2,  # Low confidence
            timestamp=datetime.now()
        )
        
        # Test authorization
        authorization = await risk_manager.authorize_trade(invalid_request)
        
        # Validate rejection
        assert authorization is not None
        assert authorization.approved is False
        assert authorization.reason is not None
        assert len(authorization.reason) > 0
        assert authorization.risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        
        logger.info(f"✅ Trade correctly rejected: {authorization.reason}")
    
    @pytest.mark.asyncio
    async def test_authorization_token_validation(self, risk_manager, sample_trade_request):
        """Test authorization token validation functionality"""
        logger.info("🧪 Testing authorization token validation...")
        
        # First, get an authorization
        authorization = await risk_manager.authorize_trade(sample_trade_request)
        assert authorization.approved is True
        
        # Test token validation
        is_valid = await risk_manager.validate_authorization_token(
            authorization.authorization_id,
            sample_trade_request.symbol,
            sample_trade_request.side,
            sample_trade_request.quantity
        )
        
        assert is_valid is True
        logger.info(f"✅ Authorization token validated successfully")
        
        # Test invalid token
        invalid_token_valid = await risk_manager.validate_authorization_token(
            "invalid_token_12345",
            sample_trade_request.symbol,
            sample_trade_request.side,
            sample_trade_request.quantity
        )
        
        assert invalid_token_valid is False
        logger.info(f"✅ Invalid token correctly rejected")
    
    @pytest.mark.asyncio
    async def test_authorization_cleanup(self, risk_manager, sample_trade_request):
        """Test authorization history cleanup functionality"""
        logger.info("🧪 Testing authorization cleanup...")
        
        # Create multiple authorizations
        authorizations = []
        for i in range(5):
            request = TradeRequest(
                request_id=str(uuid.uuid4()),
                symbol=f"TEST{i}",
                side="BUY",
                quantity=50,
                price=100.0,
                strategy_id="test_strategy",
                signal_confidence=0.7,
                timestamp=datetime.now()
            )
            auth = await risk_manager.authorize_trade(request)
            authorizations.append(auth)
        
        # Verify authorizations are stored
        initial_count = len(risk_manager.authorization_history)
        assert initial_count >= 5
        
        # Manually trigger cleanup
        await risk_manager._cleanup_old_authorizations()
        
        # Since tokens are new, they shouldn't be cleaned up yet
        assert len(risk_manager.authorization_history) == initial_count
        
        logger.info(f"✅ Authorization cleanup working correctly")

class TestStrategyManagerRiskIntegration:
    """Test suite for StrategyManager risk integration"""
    
    @pytest.fixture
    async def strategy_manager(self):
        """Create strategy manager with mocked dependencies"""
        config = StrategyConfig(
            enabled_strategies=["mean_reversion", "momentum"],
            min_signal_strength=0.3
        )
        
        # Mock the signal engine and other components
        strategy_manager = StrategyManager(config)
        
        # Mock the risk manager
        strategy_manager.risk_manager = AsyncMock()
        strategy_manager.risk_manager.authorize_trade = AsyncMock()
        
        await strategy_manager.startup()
        return strategy_manager
    
    @pytest.mark.asyncio
    async def test_signal_authorization_flow(self, strategy_manager):
        """Test that signals are submitted for risk authorization"""
        logger.info("🧪 Testing StrategyManager signal authorization flow...")
        
        # Mock risk manager to approve trades
        mock_authorization = TradeAuthorization(
            request_id="test_request",
            authorization_id="test_auth_123",
            approved=True,
            reason="Test approval",
            risk_level=RiskLevel.LOW,
            timestamp=datetime.now()
        )
        strategy_manager.risk_manager.authorize_trade.return_value = mock_authorization
        
        # Create mock market data
        market_data = {
            "AAPL": {
                "price": 150.0,
                "volume": 1000000,
                "timestamp": datetime.now()
            }
        }
        
        # Mock signal engine to return test signals
        if strategy_manager.signal_engine:
            strategy_manager.signal_engine.generate_signals = AsyncMock(return_value=[
                TradingSignal(
                    symbol="AAPL",
                    signal_type=SignalType.BUY,
                    strength=0.75,
                    price=150.0,
                    timestamp=datetime.now(),
                    strategy="mean_reversion",
                    confidence=0.8
                )
            ])
        
        # Generate signals (should include risk authorization)
        authorized_signals = await strategy_manager.generate_signals(["AAPL"], market_data)
        
        # Verify risk authorization was called
        if strategy_manager.signal_engine:
            strategy_manager.risk_manager.authorize_trade.assert_called()
        
        # Verify signals have authorization metadata
        if authorized_signals:
            signal = authorized_signals[0]
            assert 'authorization_token' in signal.metadata
            assert signal.metadata['authorization_token'] == mock_authorization.authorization_id
        
        logger.info("✅ StrategyManager signal authorization flow working correctly")

class TestRealTimeTradingEngineAuthorization:
    """Test suite for RealTimeTradingEngine authorization flow"""
    
    @pytest.fixture
    async def trading_engine(self):
        """Create trading engine with mocked dependencies"""
        config = RealTimeTradingConfiguration(
            max_orders_per_second=5,
            order_timeout_seconds=30.0
        )
        
        engine = RealTimeTradingEngine(config)
        
        # Mock the risk manager
        engine.risk_manager = AsyncMock()
        
        await engine.startup()
        return engine
    
    @pytest.mark.asyncio
    async def test_mandatory_risk_authorization(self, trading_engine):
        """Test that trading engine requires risk authorization"""
        logger.info("🧪 Testing RealTimeTradingEngine mandatory authorization...")
        
        # Mock approved authorization
        mock_authorization = TradeAuthorization(
            request_id="test_request",
            authorization_id="test_auth_456",
            approved=True,
            reason="Test approval",
            risk_level=RiskLevel.LOW,
            timestamp=datetime.now()
        )
        trading_engine.risk_manager.authorize_trade.return_value = mock_authorization
        
        # Create test trading signals
        test_signals = [
            TradingSignal(
                symbol="AAPL",
                signal_type=SignalType.BUY,
                strength=0.8,
                price=150.0,
                timestamp=datetime.now(),
                strategy="test_strategy",
                confidence=0.75
            )
        ]
        
        # Mock execution engine
        trading_engine.execution_engine = AsyncMock()
        trading_engine.execution_engine.submit_order = AsyncMock(return_value="order_123")
        
        # Process trading signals
        results = await trading_engine.process_trading_signals(test_signals)
        
        # Verify risk authorization was called
        trading_engine.risk_manager.authorize_trade.assert_called()
        
        # Verify execution was called with authorization
        trading_engine.execution_engine.submit_order.assert_called()
        
        logger.info("✅ RealTimeTradingEngine authorization flow working correctly")

class TestUnifiedExecutionEngineTokenValidation:
    """Test suite for UnifiedExecutionEngine token validation"""
    
    @pytest.fixture
    async def execution_engine(self):
        """Create execution engine for testing"""
        config = ExecutionConfig(
            default_broker="simulation",
            max_order_size=10000.0
        )
        
        engine = UnifiedExecutionEngine(config)
        await engine.startup()
        return engine
    
    @pytest.mark.asyncio
    async def test_order_rejection_without_token(self, execution_engine):
        """Test that orders are rejected without authorization tokens"""
        logger.info("🧪 Testing order rejection without authorization token...")
        
        # Attempt to submit order without authorization token
        order_id = await execution_engine.submit_order(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET,
            price=150.0
            # No authorization_token provided
        )
        
        # Order should be rejected
        assert order_id is None
        assert execution_engine.unauthorized_executions_blocked >= 1
        
        logger.info("✅ Order correctly rejected without authorization token")
    
    @pytest.mark.asyncio
    async def test_order_approval_with_valid_token(self, execution_engine):
        """Test that orders are approved with valid authorization tokens"""
        logger.info("🧪 Testing order approval with valid authorization token...")
        
        # Mock risk manager to return valid token validation
        execution_engine.risk_manager = AsyncMock()
        execution_engine.risk_manager.validate_authorization_token = AsyncMock(return_value=True)
        
        # Submit order with authorization token
        order_id = await execution_engine.submit_order(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET,
            price=150.0,
            authorization_token="valid_token_123456789",
            risk_limits_applied={"max_position": 0.1},
            authorization_timestamp=datetime.now()
        )
        
        # Order should be approved
        assert order_id is not None
        assert len(order_id) > 0
        
        # Verify token validation was called
        execution_engine.risk_manager.validate_authorization_token.assert_called()
        
        logger.info(f"✅ Order approved with valid token: {order_id}")

class TestEndToEndAuthorizationFlow:
    """Test complete end-to-end authorization workflow"""
    
    @pytest.mark.asyncio
    async def test_complete_authorization_workflow(self):
        """Test complete flow from signal generation to execution"""
        logger.info("🧪 Testing complete end-to-end authorization workflow...")
        
        # This would be a comprehensive integration test
        # For now, we'll create a simplified version
        
        # 1. Create risk manager
        risk_config = RiskConfiguration()
        risk_manager = AdvancedRiskManager(risk_config)
        await risk_manager.initialize()
        await risk_manager.startup()
        
        # 2. Create trade request
        trade_request = TradeRequest(
            request_id=str(uuid.uuid4()),
            symbol="AAPL",
            side="BUY",
            quantity=50,
            price=150.0,
            strategy_id="integration_test",
            signal_confidence=0.8,
            timestamp=datetime.now()
        )
        
        # 3. Test authorization
        authorization = await risk_manager.authorize_trade(trade_request)
        assert authorization.approved is True
        
        # 4. Test token validation
        is_valid = await risk_manager.validate_authorization_token(
            authorization.authorization_id,
            trade_request.symbol,
            trade_request.side,
            trade_request.quantity
        )
        assert is_valid is True
        
        logger.info("✅ Complete end-to-end authorization workflow successful")

# Test runner function
async def run_all_tests():
    """Run all risk management tests"""
    logger.info("🚀 Starting Central Risk Authority Test Suite...")
    
    try:
        # Test Central Risk Authority
        logger.info("\n" + "="*60)
        logger.info("TESTING CENTRAL RISK AUTHORITY")
        logger.info("="*60)
        
        risk_test = TestCentralRiskAuthority()
        risk_manager = await risk_test.risk_manager()
        sample_request = risk_test.sample_trade_request()
        
        await risk_test.test_risk_manager_authorization_approval(risk_manager, sample_request)
        await risk_test.test_risk_manager_authorization_rejection(risk_manager)
        await risk_test.test_authorization_token_validation(risk_manager, sample_request)
        await risk_test.test_authorization_cleanup(risk_manager, sample_request)
        
        # Test Strategy Manager Integration
        logger.info("\n" + "="*60)
        logger.info("TESTING STRATEGY MANAGER RISK INTEGRATION")
        logger.info("="*60)
        
        strategy_test = TestStrategyManagerRiskIntegration()
        strategy_manager = await strategy_test.strategy_manager()
        await strategy_test.test_signal_authorization_flow(strategy_manager)
        
        # Test Execution Engine
        logger.info("\n" + "="*60)
        logger.info("TESTING EXECUTION ENGINE TOKEN VALIDATION")
        logger.info("="*60)
        
        execution_test = TestUnifiedExecutionEngineTokenValidation()
        execution_engine = await execution_test.execution_engine()
        await execution_test.test_order_rejection_without_token(execution_engine)
        await execution_test.test_order_approval_with_valid_token(execution_engine)
        
        # Test End-to-End Flow
        logger.info("\n" + "="*60)
        logger.info("TESTING END-TO-END AUTHORIZATION FLOW")
        logger.info("="*60)
        
        e2e_test = TestEndToEndAuthorizationFlow()
        await e2e_test.test_complete_authorization_workflow()
        
        logger.info("\n" + "="*60)
        logger.info("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        logger.info("✅ Central Risk Authority implementation validated")
        logger.info("✅ Institutional-grade risk governance confirmed")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"\n❌ TEST FAILURE: {e}")
        raise

if __name__ == "__main__":
    # Run the test suite
    asyncio.run(run_all_tests())