#!/usr/bin/env python3
"""
Test Suite for UnifiedExecutionEngine Authorization Token Validation
==================================================================

Tests the execution engine's mandatory authorization token validation
and ensures no orders can be executed without proper risk approval.

Author: Professional Trading System Architecture Testing
Version: 1.0.0 (Execution Engine Token Validation)
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core_structure.execution_engine import (
    UnifiedExecutionEngine, ExecutionConfig, Order, OrderSide, OrderType
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ExecutionEngineTokenTests:
    """Test suite for execution engine token validation"""
    
    async def setup_execution_engine(self):
        """Create and initialize execution engine"""
        config = ExecutionConfig(
            default_broker="simulation",
            max_order_size=10000.0,
            order_timeout=300,
            commission_per_share=0.005
        )
        
        engine = UnifiedExecutionEngine(config)
        await engine.startup()
        
        return engine
    
    async def test_order_rejection_without_token(self):
        """Test that orders are rejected without authorization tokens"""
        logger.info("🧪 Testing order rejection without authorization token...")
        
        engine = await self.setup_execution_engine()
        
        # Attempt to submit order without authorization token
        order_id = await engine.submit_order(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET,
            price=150.0
            # No authorization_token provided
        )
        
        # Order should be rejected
        assert order_id is None, "Order should be rejected without authorization token"
        assert engine.unauthorized_executions_blocked >= 1, "Should track unauthorized execution attempts"
        
        logger.info(f"✅ Order correctly rejected without authorization token")
        logger.info(f"📊 Unauthorized executions blocked: {engine.unauthorized_executions_blocked}")
        
        return True
    
    async def test_order_rejection_with_invalid_token(self):
        """Test that orders are rejected with invalid authorization tokens"""
        logger.info("🧪 Testing order rejection with invalid authorization token...")
        
        engine = await self.setup_execution_engine()
        
        # Attempt to submit order with invalid token
        order_id = await engine.submit_order(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET,
            price=150.0,
            authorization_token="invalid_token_123",  # Invalid token
            risk_limits_applied={"max_position": 0.1},
            authorization_timestamp=datetime.now()
        )
        
        # Order should be rejected
        assert order_id is None, "Order should be rejected with invalid token"
        assert engine.unauthorized_executions_blocked >= 1, "Should track unauthorized execution attempts"
        
        logger.info(f"✅ Order correctly rejected with invalid token")
        
        return True
    
    async def test_order_rejection_with_short_token(self):
        """Test that orders are rejected with improperly formatted tokens"""
        logger.info("🧪 Testing order rejection with short/invalid token format...")
        
        engine = await self.setup_execution_engine()
        
        # Attempt to submit order with short token
        order_id = await engine.submit_order(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET,
            price=150.0,
            authorization_token="short",  # Too short token
            risk_limits_applied={"max_position": 0.1},
            authorization_timestamp=datetime.now()
        )
        
        # Order should be rejected
        assert order_id is None, "Order should be rejected with improperly formatted token"
        
        logger.info(f"✅ Order correctly rejected with short token")
        
        return True
    
    async def test_order_approval_with_mocked_valid_token(self):
        """Test that orders are approved with valid authorization tokens (mocked)"""
        logger.info("🧪 Testing order approval with mocked valid authorization token...")
        
        engine = await self.setup_execution_engine()
        
        # Mock the risk manager validation to return True
        from unittest.mock import AsyncMock
        if not hasattr(engine, 'risk_manager') or engine.risk_manager is None:
            engine.risk_manager = AsyncMock()
        engine.risk_manager.validate_authorization_token = AsyncMock(return_value=True)
        
        # Submit order with valid token format
        order_id = await engine.submit_order(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET,
            price=150.0,
            authorization_token="valid_auth_token_12345678",  # Valid format token
            risk_limits_applied={"max_position": 0.1},
            authorization_timestamp=datetime.now()
        )
        
        # Order should be approved
        assert order_id is not None, "Order should be approved with valid token"
        assert len(order_id) > 0, "Order ID should be non-empty"
        
        # Verify token validation was called
        engine.risk_manager.validate_authorization_token.assert_called_once()
        
        logger.info(f"✅ Order approved with valid token: {order_id}")
        
        return order_id
    
    async def test_order_parameter_validation(self):
        """Test basic order parameter validation"""
        logger.info("🧪 Testing order parameter validation...")
        
        engine = await self.setup_execution_engine()
        
        # Mock valid token validation
        from unittest.mock import AsyncMock
        if not hasattr(engine, 'risk_manager') or engine.risk_manager is None:
            engine.risk_manager = AsyncMock()
        engine.risk_manager.validate_authorization_token = AsyncMock(return_value=True)
        
        # Test invalid quantity
        order_id = await engine.submit_order(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=0,  # Invalid quantity
            order_type=OrderType.MARKET,
            price=150.0,
            authorization_token="valid_auth_token_12345678",
            risk_limits_applied={"max_position": 0.1},
            authorization_timestamp=datetime.now()
        )
        
        assert order_id is None, "Order should be rejected with invalid quantity"
        
        # Test excessive quantity
        order_id = await engine.submit_order(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=50000,  # Exceeds max_order_size
            order_type=OrderType.MARKET,
            price=150.0,
            authorization_token="valid_auth_token_12345678",
            risk_limits_applied={"max_position": 0.1},
            authorization_timestamp=datetime.now()
        )
        
        assert order_id is None, "Order should be rejected with excessive quantity"
        
        logger.info(f"✅ Order parameter validation working correctly")
        
        return True
    
    async def test_execution_statistics(self):
        """Test execution statistics tracking"""
        logger.info("🧪 Testing execution statistics tracking...")
        
        engine = await self.setup_execution_engine()
        
        initial_blocked = engine.unauthorized_executions_blocked
        initial_attempted = engine.total_executions_attempted
        
        # Try several unauthorized executions
        for i in range(3):
            await engine.submit_order(
                symbol=f"TEST{i}",
                side=OrderSide.BUY,
                quantity=100,
                order_type=OrderType.MARKET,
                price=150.0
                # No authorization token
            )
        
        # Check statistics
        blocked_count = engine.unauthorized_executions_blocked - initial_blocked
        attempted_count = engine.total_executions_attempted - initial_attempted
        
        assert blocked_count == 3, f"Should have blocked 3 executions, blocked {blocked_count}"
        assert attempted_count == 3, f"Should have attempted 3 executions, attempted {attempted_count}"
        
        logger.info(f"✅ Statistics tracking: {attempted_count} attempted, {blocked_count} blocked")
        
        return True

async def run_execution_engine_tests():
    """Run execution engine token validation tests"""
    logger.info("🚀 Starting Execution Engine Token Validation Tests...")
    logger.info("="*70)
    
    test_suite = ExecutionEngineTokenTests()
    
    try:
        # Test 1: Order rejection without token
        logger.info("\n📋 Test 1: Order Rejection Without Token")
        result1 = await test_suite.test_order_rejection_without_token()
        
        # Test 2: Order rejection with invalid token
        logger.info("\n📋 Test 2: Order Rejection With Invalid Token")
        result2 = await test_suite.test_order_rejection_with_invalid_token()
        
        # Test 3: Order rejection with short token
        logger.info("\n📋 Test 3: Order Rejection With Short Token")
        result3 = await test_suite.test_order_rejection_with_short_token()
        
        # Test 4: Order approval with valid token (mocked)
        logger.info("\n📋 Test 4: Order Approval With Valid Token (Mocked)")
        order_id = await test_suite.test_order_approval_with_mocked_valid_token()
        
        # Test 5: Order parameter validation
        logger.info("\n📋 Test 5: Order Parameter Validation")
        result5 = await test_suite.test_order_parameter_validation()
        
        # Test 6: Execution statistics
        logger.info("\n📋 Test 6: Execution Statistics Tracking")
        result6 = await test_suite.test_execution_statistics()
        
        # Summary
        logger.info("\n" + "="*70)
        logger.info("🎉 EXECUTION ENGINE TESTS COMPLETED SUCCESSFULLY!")
        logger.info("="*70)
        logger.info("✅ Unauthorized execution blocking working")
        logger.info("✅ Authorization token validation enforced")
        logger.info("✅ Order parameter validation active")
        logger.info("✅ Execution statistics tracking operational")
        logger.info("✅ EXECUTION ENGINE SECURITY VALIDATED")
        logger.info("="*70)
        
        return True
        
    except Exception as e:
        logger.error(f"\n❌ EXECUTION ENGINE TEST FAILURE: {e}")
        logger.error("❌ Execution engine security validation failed")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Run the execution engine test suite
    success = asyncio.run(run_execution_engine_tests())
    
    if success:
        print("\n🎯 RESULT: All execution engine tests PASSED")
        print("🔒 Execution Engine security controls validated")
        exit(0)
    else:
        print("\n💥 RESULT: Execution engine tests FAILED")
        exit(1)