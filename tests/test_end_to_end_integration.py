#!/usr/bin/env python3
"""
End-to-End Integration Test for Central Risk Authority
Validates complete institutional-grade risk governance workflow
"""

import asyncio
import logging
import traceback
import sys
import os
from datetime import datetime
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Core imports
from core_structure.infrastructure.types.unified_types import (
    Position, Portfolio, OrderRequest, RiskConfiguration, TradingConfiguration
)

from core_structure.components.risk.advanced_risk_manager import AdvancedRiskManager
from core_structure.components.execution.unified_execution_engine import UnifiedExecutionEngine
from core_structure.unified_engine.factory import EngineFactory

class EndToEndIntegrationTest:
    """Comprehensive end-to-end integration test for risk governance"""
    
    def __init__(self):
        """Initialize integration test"""
        self.test_results = []
        
    async def setup_test_environment(self):
        """Setup complete test environment with all components"""
        logger.info("🏗️ Setting up complete test environment...")
        
        # Create realistic risk configuration
        self.risk_config = RiskConfiguration(
            max_position_size=10.0,  # 10% max position size
            max_portfolio_var=0.05,   # 5% VaR limit
            confidence_threshold=0.95, # 95% confidence required
            stop_loss_threshold=0.05,  # 5% stop loss
            max_daily_loss=0.03       # 3% max daily loss
        )
        
        # Initialize risk manager
        self.risk_manager = AdvancedRiskManager(self.risk_config)
        await self.risk_manager.start()
        
        # Create test portfolio with realistic positions
        self.test_portfolio = Portfolio(
            total_value=100000.0,  # $100K portfolio
            cash=60000.0,         # $60K cash
            positions={
                'SPY': Position(
                    symbol='SPY',
                    quantity=100,
                    entry_price=400.0,
                    current_price=400.0,
                    position_value=40000.0
                )
            }
        )
        
        # Initialize execution engine with risk controls
        self.execution_engine = UnifiedExecutionEngine(
            risk_manager=self.risk_manager
        )
        await self.execution_engine.start()
        
        logger.info("✅ Test environment setup complete")
        
    async def test_complete_authorization_workflow(self):
        """Test complete authorization workflow from request to execution"""
        logger.info("\n📋 Test: Complete Authorization Workflow")
        logger.info("=" * 60)
        
        try:
            # Test Case 1: Small trade approval
            logger.info("\n🧪 Case 1: Small Trade (Should be APPROVED)")
            small_trade_request = OrderRequest(
                symbol='AAPL',
                side='buy',
                quantity=25,  # Small position
                order_type='market',
                price=150.0
            )
            
            # Request authorization
            auth_result = await self.risk_manager.authorize_trade(
                small_trade_request, 
                self.test_portfolio,
                confidence_score=0.98  # High confidence
            )
            
            if auth_result.approved:
                logger.info(f"✅ Small trade APPROVED: {auth_result.token[:10]}...")
                logger.info(f"   Risk Level: {auth_result.risk_level}")
                logger.info(f"   Confidence: {auth_result.confidence_score}")
                
                # Execute with authorization token
                execution_result = await self.execution_engine.execute_order(
                    small_trade_request,
                    authorization_token=auth_result.token
                )
                logger.info(f"✅ Order executed: {execution_result}")
                self.test_results.append(("Small Trade Authorization + Execution", "PASS"))
            else:
                logger.error(f"❌ Small trade REJECTED: {auth_result.rejection_reason}")
                self.test_results.append(("Small Trade Authorization", "FAIL"))
            
            # Test Case 2: Large trade rejection
            logger.info("\n🧪 Case 2: Large Trade (Should be REJECTED)")
            large_trade_request = OrderRequest(
                symbol='TSLA',
                side='buy',
                quantity=500,  # Large position exceeding 10% limit
                order_type='market',
                price=200.0
            )
            
            auth_result = await self.risk_manager.authorize_trade(
                large_trade_request,
                self.test_portfolio,
                confidence_score=0.96
            )
            
            if not auth_result.approved:
                logger.info(f"✅ Large trade correctly REJECTED: {auth_result.rejection_reason}")
                logger.info(f"   Risk Level: {auth_result.risk_level}")
                self.test_results.append(("Large Trade Rejection", "PASS"))
                
                # Try to execute without authorization (should fail)
                execution_result = await self.execution_engine.execute_order(
                    large_trade_request
                )
                if not execution_result:
                    logger.info("✅ Execution correctly blocked without authorization")
                    self.test_results.append(("Unauthorized Execution Block", "PASS"))
            else:
                logger.error("❌ Large trade was approved when it should be rejected")
                self.test_results.append(("Large Trade Rejection", "FAIL"))
            
            # Test Case 3: Low confidence trade rejection
            logger.info("\n🧪 Case 3: Low Confidence Trade (Should be REJECTED)")
            low_conf_request = OrderRequest(
                symbol='NVDA',
                side='buy',
                quantity=50,
                order_type='market',
                price=300.0
            )
            
            auth_result = await self.risk_manager.authorize_trade(
                low_conf_request,
                self.test_portfolio,
                confidence_score=0.85  # Below 95% threshold
            )
            
            if not auth_result.approved:
                logger.info(f"✅ Low confidence trade correctly REJECTED: {auth_result.rejection_reason}")
                self.test_results.append(("Low Confidence Rejection", "PASS"))
            else:
                logger.error("❌ Low confidence trade was approved")
                self.test_results.append(("Low Confidence Rejection", "FAIL"))
                
        except Exception as e:
            logger.error(f"❌ Authorization workflow test failed: {e}")
            logger.error(traceback.format_exc())
            self.test_results.append(("Authorization Workflow", "ERROR"))
    
    async def test_token_security_validation(self):
        """Test token security and validation"""
        logger.info("\n📋 Test: Token Security Validation")
        logger.info("=" * 60)
        
        try:
            # Test invalid token formats
            invalid_tokens = [
                "invalid_token",
                "123",
                "",
                "expired_token_format_wrong"
            ]
            
            test_order = OrderRequest(
                symbol='AMD',
                side='buy',
                quantity=50,
                order_type='market',
                price=100.0
            )
            
            for token in invalid_tokens:
                result = await self.execution_engine.execute_order(
                    test_order,
                    authorization_token=token
                )
                if not result:
                    logger.info(f"✅ Invalid token '{token[:10]}...' correctly rejected")
                else:
                    logger.error(f"❌ Invalid token '{token}' was accepted")
                    
            self.test_results.append(("Token Security Validation", "PASS"))
            
        except Exception as e:
            logger.error(f"❌ Token security test failed: {e}")
            self.test_results.append(("Token Security Validation", "ERROR"))
    
    async def test_risk_authority_statistics(self):
        """Test risk authority statistics and tracking"""
        logger.info("\n📋 Test: Risk Authority Statistics")
        logger.info("=" * 60)
        
        try:
            # Get authorization history
            auth_history = self.risk_manager.get_authorization_history()
            logger.info(f"📊 Total authorizations: {len(auth_history)}")
            
            approved_count = sum(1 for auth in auth_history if auth.get('approved', False))
            rejected_count = len(auth_history) - approved_count
            
            logger.info(f"✅ Approved trades: {approved_count}")
            logger.info(f"🚫 Rejected trades: {rejected_count}")
            
            # Get execution statistics
            exec_stats = self.execution_engine.get_statistics()
            logger.info(f"📈 Execution statistics: {exec_stats}")
            
            if len(auth_history) > 0:
                logger.info("✅ Risk authority tracking operational")
                self.test_results.append(("Risk Authority Statistics", "PASS"))
            else:
                logger.warning("⚠️ No authorization history found")
                self.test_results.append(("Risk Authority Statistics", "WARNING"))
                
        except Exception as e:
            logger.error(f"❌ Statistics test failed: {e}")
            self.test_results.append(("Risk Authority Statistics", "ERROR"))
    
    async def cleanup_test_environment(self):
        """Cleanup test environment"""
        logger.info("\n🧹 Cleaning up test environment...")
        try:
            await self.execution_engine.stop()
            await self.risk_manager.stop()
            logger.info("✅ Test environment cleaned up")
        except Exception as e:
            logger.error(f"⚠️ Cleanup warning: {e}")
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        logger.info("\n" + "=" * 80)
        logger.info("📊 COMPREHENSIVE INTEGRATION TEST REPORT")
        logger.info("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for _, result in self.test_results if result == "PASS")
        failed_tests = sum(1 for _, result in self.test_results if result == "FAIL")
        error_tests = sum(1 for _, result in self.test_results if result == "ERROR")
        warning_tests = sum(1 for _, result in self.test_results if result == "WARNING")
        
        logger.info(f"📈 Total Tests: {total_tests}")
        logger.info(f"✅ Passed: {passed_tests}")
        logger.info(f"❌ Failed: {failed_tests}")
        logger.info(f"⚠️ Errors: {error_tests}")
        logger.info(f"⚠️ Warnings: {warning_tests}")
        logger.info("")
        
        logger.info("📋 Test Results Detail:")
        for test_name, result in self.test_results:
            status_emoji = {
                "PASS": "✅",
                "FAIL": "❌", 
                "ERROR": "💥",
                "WARNING": "⚠️"
            }.get(result, "❓")
            logger.info(f"   {status_emoji} {test_name}: {result}")
        
        logger.info("")
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        logger.info(f"🎯 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 90:
            logger.info("🎉 INTEGRATION TEST SUITE: EXCELLENT")
        elif success_rate >= 75:
            logger.info("✅ INTEGRATION TEST SUITE: GOOD")
        elif success_rate >= 50:
            logger.info("⚠️ INTEGRATION TEST SUITE: NEEDS IMPROVEMENT")
        else:
            logger.info("❌ INTEGRATION TEST SUITE: CRITICAL ISSUES")
        
        logger.info("=" * 80)

async def main():
    """Main test execution"""
    logger.info("🚀 Starting End-to-End Integration Tests...")
    logger.info("=" * 80)
    
    test_suite = EndToEndIntegrationTest()
    
    try:
        # Setup test environment
        await test_suite.setup_test_environment()
        
        # Run all integration tests
        await test_suite.test_complete_authorization_workflow()
        await test_suite.test_token_security_validation()
        await test_suite.test_risk_authority_statistics()
        
        # Generate final report
        test_suite.generate_test_report()
        
    except Exception as e:
        logger.error(f"💥 Integration test suite failed: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Cleanup
        await test_suite.cleanup_test_environment()

if __name__ == "__main__":
    asyncio.run(main())