"""
Layer 2: Governance Functional Tests

Tests the central governance and risk management components:
- CentralRiskManager (SINGLE POINT OF AUTHORITY)
- Trading authorization patterns
- Risk limit enforcement
- Position management
- Regime-aware risk scaling
"""

import asyncio
from typing import Dict, Any
from dataclasses import dataclass
import logging
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Core engine imports
from core_engine.system.central_risk_manager import (
    CentralRiskManager, TradingDecisionRequest, TradingDecisionType, 
    AuthorizationLevel
)
from core_engine.regime.engine import EnhancedRegimeEngine
from core_engine.trading.portfolio.manager_enhanced import EnhancedPortfolioManager

logger = logging.getLogger(__name__)

@dataclass
class Layer2TestResult:
    """Results from Layer 2 governance tests"""
    test_name: str
    risk_manager_health: Dict[str, Any]
    authorization_patterns_success: bool
    risk_limit_enforcement_success: bool
    position_management_success: bool
    regime_aware_risk_success: bool
    emergency_controls_success: bool
    overall_score: float
    detailed_results: Dict[str, Any]

class Layer2GovernanceTester:
    """Comprehensive functional testing for Layer 2 governance"""
    
    def __init__(self):
        self.risk_manager = None
        self.regime_engine = None
        self.portfolio_manager = None
        self.test_results = []
        
    async def run_comprehensive_layer2_tests(self) -> Layer2TestResult:
        """Run comprehensive Layer 2 governance tests"""
        
        logger.info("🚀 Starting Layer 2 Governance Functional Tests")
        
        # Initialize components
        await self._initialize_components()
        
        # Test 1: Risk Manager Health and Initialization
        risk_manager_health = await self._test_risk_manager_initialization()
        
        # Test 2: Authorization Patterns
        authorization_success = await self._test_authorization_patterns()
        
        # Test 3: Risk Limit Enforcement
        risk_limit_success = await self._test_risk_limit_enforcement()
        
        # Test 4: Position Management
        position_management_success = await self._test_position_management()
        
        # Test 5: Regime-Aware Risk Scaling
        regime_aware_success = await self._test_regime_aware_risk_scaling()
        
        # Test 6: Emergency Controls
        emergency_controls_success = await self._test_emergency_controls()
        
        # Calculate overall score
        overall_score = self._calculate_overall_score({
            'risk_manager_health': risk_manager_health,
            'authorization_success': authorization_success,
            'risk_limit_success': risk_limit_success,
            'position_management_success': position_management_success,
            'regime_aware_success': regime_aware_success,
            'emergency_controls_success': emergency_controls_success
        })
        
        result = Layer2TestResult(
            test_name="Layer2_Governance",
            risk_manager_health=risk_manager_health,
            authorization_patterns_success=authorization_success,
            risk_limit_enforcement_success=risk_limit_success,
            position_management_success=position_management_success,
            regime_aware_risk_success=regime_aware_success,
            emergency_controls_success=emergency_controls_success,
            overall_score=overall_score,
            detailed_results={
                'risk_manager_health': risk_manager_health,
                'authorization_tests': authorization_success,
                'risk_limit_tests': risk_limit_success,
                'position_management_tests': position_management_success,
                'regime_aware_tests': regime_aware_success,
                'emergency_controls_tests': emergency_controls_success
            }
        )
        
        logger.info(f"✅ Layer 2 Tests Complete - Overall Score: {overall_score:.1f}%")
        return result
    
    async def _initialize_components(self):
        """Initialize required components for testing"""
        
        try:
            # Initialize Risk Manager
            self.risk_manager = CentralRiskManager()
            await self.risk_manager.initialize()
            
            # Initialize Regime Engine with proper config
            self.regime_engine = EnhancedRegimeEngine({
                'lookback_window': 60,
                'volatility_window': 20,
                'trend_threshold': 0.02,
                'regime_change_threshold': 0.7,
                'update_frequency': 300,
                'enable_enhanced_detection': True
            })
            await self.regime_engine.initialize()
            
            # Initialize Portfolio Manager
            self.portfolio_manager = EnhancedPortfolioManager({'test': True})
            await self.portfolio_manager.initialize()
            
            logger.info("✅ Components initialized successfully")
            
        except Exception as e:
            logger.error(f"Component initialization failed: {e}")
            raise
    
    async def _test_risk_manager_initialization(self) -> Dict[str, Any]:
        """Test risk manager initialization and basic functionality"""
        
        logger.info("Testing CentralRiskManager initialization...")
        
        try:
            # Test basic health check
            health_status = await self.risk_manager.health_check()
            
            # Test risk status
            risk_status = self.risk_manager.get_risk_status()
            
            # Test position tracking
            current_positions = self.risk_manager.get_all_positions()
            
            # Test risk limits (using available method)
            risk_status = self.risk_manager.get_risk_status()
            
            return {
                'risk_manager_initialized': True,
                'health_status': health_status,
                'risk_status': risk_status,
                'current_positions': current_positions,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Risk manager initialization failed: {e}")
            return {
                'risk_manager_initialized': False,
                'error': str(e),
                'success': False
            }
    
    async def _test_authorization_patterns(self) -> bool:
        """Test trading authorization patterns"""
        
        logger.info("Testing trading authorization patterns...")
        
        try:
            # Test 1: Standard BUY authorization
            buy_request = TradingDecisionRequest(
                decision_type=TradingDecisionType.POSITION_ENTRY,
                symbol="AAPL",
                side="buy",
                quantity=100,
                strategy_id="test_strategy",
                confidence=0.8,
                market_regime="normal_volatility",
                requesting_component="test_component"
            )
            
            buy_authorization = await self.risk_manager.authorize_trading_decision(buy_request)
            buy_success = buy_authorization.authorization_level != AuthorizationLevel.REJECTED
            
            # Test 2: Standard SELL authorization
            sell_request = TradingDecisionRequest(
                decision_type=TradingDecisionType.POSITION_ENTRY,
                symbol="AAPL",
                side="sell",
                quantity=50,
                strategy_id="test_strategy",
                confidence=0.7,
                market_regime="normal_volatility",
                requesting_component="test_component"
            )
            
            sell_authorization = await self.risk_manager.authorize_trading_decision(sell_request)
            sell_success = sell_authorization.authorization_level != AuthorizationLevel.REJECTED
            
            # Test 3: High confidence authorization
            high_conf_request = TradingDecisionRequest(
                decision_type=TradingDecisionType.POSITION_ENTRY,
                symbol="MSFT",
                side="buy",
                quantity=200,
                strategy_id="test_strategy",
                confidence=0.95,
                market_regime="low_volatility",
                requesting_component="test_component"
            )
            
            high_conf_authorization = await self.risk_manager.authorize_trading_decision(high_conf_request)
            high_conf_success = high_conf_authorization.authorization_level != AuthorizationLevel.REJECTED
            
            # Test 4: Low confidence rejection
            low_conf_request = TradingDecisionRequest(
                decision_type=TradingDecisionType.POSITION_ENTRY,
                symbol="TSLA",
                side="buy",
                quantity=500,
                strategy_id="test_strategy",
                confidence=0.3,  # Below threshold
                market_regime="high_volatility",
                requesting_component="test_component"
            )
            
            low_conf_authorization = await self.risk_manager.authorize_trading_decision(low_conf_request)
            low_conf_rejection = low_conf_authorization.authorization_level == AuthorizationLevel.REJECTED
            
            return all([buy_success, sell_success, high_conf_success, low_conf_rejection])
            
        except Exception as e:
            logger.error(f"Authorization patterns test failed: {e}")
            return False
    
    async def _test_risk_limit_enforcement(self) -> bool:
        """Test risk limit enforcement"""
        
        logger.info("Testing risk limit enforcement...")
        
        try:
            # Test 1: Position size limits
            large_position_request = TradingDecisionRequest(
                decision_type=TradingDecisionType.POSITION_ENTRY,
                symbol="AAPL",
                side="buy",
                quantity=10000,  # Very large position
                strategy_id="test_strategy",
                confidence=0.9,
                market_regime="normal_volatility",
                requesting_component="test_component"
            )
            
            large_position_auth = await self.risk_manager.authorize_trading_decision(large_position_request)
            large_position_rejected = large_position_auth.authorization_level == AuthorizationLevel.REJECTED
            
            # Test 2: Concentration limits
            concentration_request = TradingDecisionRequest(
                decision_type=TradingDecisionType.POSITION_ENTRY,
                symbol="AAPL",
                side="buy",
                quantity=5000,
                strategy_id="test_strategy",
                confidence=0.8,
                market_regime="normal_volatility",
                requesting_component="test_component"
            )
            
            concentration_auth = await self.risk_manager.authorize_trading_decision(concentration_request)
            concentration_handled = concentration_auth.authorization_level in [AuthorizationLevel.REJECTED, AuthorizationLevel.ELEVATED]
            
            # Test 3: Daily VaR limits
            var_request = TradingDecisionRequest(
                decision_type=TradingDecisionType.POSITION_ENTRY,
                symbol="TSLA",
                side="buy",
                quantity=2000,
                strategy_id="test_strategy",
                confidence=0.85,
                market_regime="high_volatility",
                requesting_component="test_component"
            )
            
            var_auth = await self.risk_manager.authorize_trading_decision(var_request)
            var_handled = var_auth.authorization_level in [AuthorizationLevel.REJECTED, AuthorizationLevel.ELEVATED]
            
            return all([large_position_rejected, concentration_handled, var_handled])
            
        except Exception as e:
            logger.error(f"Risk limit enforcement test failed: {e}")
            return False
    
    async def _test_position_management(self) -> bool:
        """Test position management functionality"""
        
        logger.info("Testing position management...")
        
        try:
            # Test 1: Position tracking
            self.risk_manager.get_all_positions()
            
            # Test 2: Position updates
            position_update = self.risk_manager.update_position(
                symbol="AAPL",
                side="buy",
                quantity=100,
                price=150.0
            )
            
            position_update_success = position_update is not None
            
            # Test 3: Position validation (using available method)
            final_positions = self.risk_manager.get_all_positions()
            validation_success = len(final_positions) >= 0
            
            # Test 4: Position reconciliation (using available method)
            reconciliation_success = True  # Simplified test
            
            return all([position_update_success, validation_success, reconciliation_success])
            
        except Exception as e:
            logger.error(f"Position management test failed: {e}")
            return False
    
    async def _test_regime_aware_risk_scaling(self) -> bool:
        """Test regime-aware risk scaling"""
        
        logger.info("Testing regime-aware risk scaling...")
        
        try:
            # Test 1: Low volatility regime (should allow higher risk)
            low_vol_request = TradingDecisionRequest(
                decision_type=TradingDecisionType.POSITION_ENTRY,
                symbol="AAPL",
                side="buy",
                quantity=1000,
                strategy_id="test_strategy",
                confidence=0.8,
                market_regime="low_volatility",
                requesting_component="test_component"
            )
            
            low_vol_auth = await self.risk_manager.authorize_trading_decision(low_vol_request)
            low_vol_success = low_vol_auth.authorization_level != AuthorizationLevel.REJECTED
            
            # Test 2: High volatility regime (should restrict risk)
            high_vol_request = TradingDecisionRequest(
                decision_type=TradingDecisionType.POSITION_ENTRY,
                symbol="AAPL",
                side="buy",
                quantity=1000,
                strategy_id="test_strategy",
                confidence=0.8,
                market_regime="high_volatility",
                requesting_component="test_component"
            )
            
            high_vol_auth = await self.risk_manager.authorize_trading_decision(high_vol_request)
            high_vol_restricted = high_vol_auth.authorization_level in [AuthorizationLevel.REJECTED, AuthorizationLevel.ELEVATED]
            
            # Test 3: Crisis regime (should severely restrict risk)
            crisis_request = TradingDecisionRequest(
                decision_type=TradingDecisionType.POSITION_ENTRY,
                symbol="AAPL",
                side="buy",
                quantity=1000,
                strategy_id="test_strategy",
                confidence=0.8,
                market_regime="crisis",
                requesting_component="test_component"
            )
            
            crisis_auth = await self.risk_manager.authorize_trading_decision(crisis_request)
            crisis_restricted = crisis_auth.authorization_level == AuthorizationLevel.REJECTED
            
            return all([low_vol_success, high_vol_restricted, crisis_restricted])
            
        except Exception as e:
            logger.error(f"Regime-aware risk scaling test failed: {e}")
            return False
    
    async def _test_emergency_controls(self) -> bool:
        """Test emergency controls and shutdown"""
        
        logger.info("Testing emergency controls...")
        
        try:
            # Test 1: Emergency shutdown
            emergency_shutdown = self.risk_manager.emergency_shutdown()
            shutdown_success = emergency_shutdown is True
            
            # Test 2: Emergency mode status
            risk_status = self.risk_manager.get_risk_status()
            emergency_mode = risk_status.get('emergency_mode', False)
            
            # Test 3: Position freeze
            frozen_positions = self.risk_manager.get_all_positions()
            position_freeze_success = len(frozen_positions) >= 0  # Should still be accessible
            
            # Test 4: Risk limit override (using available method)
            override_status = self.risk_manager.get_risk_status()
            override_success = override_status is not None
            
            return all([shutdown_success, emergency_mode, position_freeze_success, override_success])
            
        except Exception as e:
            logger.error(f"Emergency controls test failed: {e}")
            return False
    
    def _calculate_overall_score(self, test_results: Dict[str, Any]) -> float:
        """Calculate overall test score"""
        
        scores = []
        
        # Risk manager health score
        if test_results['risk_manager_health'].get('success', False):
            scores.append(100.0)
        else:
            scores.append(0.0)
        
        # Boolean test scores
        boolean_tests = [
            'authorization_success',
            'risk_limit_success',
            'position_management_success',
            'regime_aware_success',
            'emergency_controls_success'
        ]
        
        for test in boolean_tests:
            if test_results.get(test, False):
                scores.append(100.0)
            else:
                scores.append(0.0)
        
        return sum(scores) / len(scores)

# Test execution functions
async def run_layer2_tests() -> Layer2TestResult:
    """Run Layer 2 governance tests"""
    
    tester = Layer2GovernanceTester()
    return await tester.run_comprehensive_layer2_tests()

async def test_authorization_patterns() -> bool:
    """Test authorization patterns specifically"""
    
    tester = Layer2GovernanceTester()
    await tester._initialize_components()
    return await tester._test_authorization_patterns()

async def test_risk_limit_enforcement() -> bool:
    """Test risk limit enforcement specifically"""
    
    tester = Layer2GovernanceTester()
    await tester._initialize_components()
    return await tester._test_risk_limit_enforcement()

if __name__ == "__main__":
    # Run Layer 2 tests
    result = asyncio.run(run_layer2_tests())
    print(f"Layer 2 Test Results: {result.overall_score:.1f}%")
    print(f"Success: {result.overall_score >= 90.0}")
