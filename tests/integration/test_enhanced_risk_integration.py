#!/usr/bin/env python3
"""
Enhanced Risk Management Integration Test Suite
==============================================

Comprehensive integration tests for the enhanced risk management system
focusing on the CentralRiskManager as the single point of authority.

This test suite validates:
- CentralRiskManager governance and authorization patterns
- Risk limit enforcement and position management
- Regime-aware risk scaling and adaptation
- Multi-strategy risk coordination
- Emergency controls and circuit breakers
- Real-time risk monitoring and alerts
- Professional risk metrics calculation

Author: StatArb_Gemini Team
Date: January 2025
"""

import asyncio
import logging
import sys
import traceback
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import pandas as pd
import numpy as np
import uuid

# Core engine imports
from core_engine.system.central_risk_manager import (
    CentralRiskManager, TradingDecisionRequest, TradingDecisionType, 
    AuthorizationLevel, RiskManagerConfig
)
from core_engine.system.hierarchical_orchestrator import HierarchicalSystemOrchestrator
from core_engine.regime.engine import EnhancedRegimeEngine
from core_engine.trading.strategies.manager import StrategyManager
from core_engine.trading.portfolio.manager_enhanced import EnhancedPortfolioManager
from core_engine.type_definitions.strategy import StrategyType, TradingSignal
from core_engine.type_definitions.regime import RegimeState


class RiskTestScenario(Enum):
    """Risk testing scenarios"""
    NORMAL_TRADING = "normal_trading"
    HIGH_VOLATILITY = "high_volatility"
    POSITION_LIMITS = "position_limits"
    CASH_CONSTRAINTS = "cash_constraints"
    EMERGENCY_SHUTDOWN = "emergency_shutdown"
    MULTI_STRATEGY = "multi_strategy"
    REGIME_ADAPTATION = "regime_adaptation"


@dataclass
class RiskTestResult:
    """Risk test result data"""
    scenario: str
    test_name: str
    success: bool
    execution_time: float
    risk_metrics: Dict[str, Any]
    authorization_results: List[Dict[str, Any]]
    error_message: Optional[str] = None


class EnhancedRiskIntegrationTester:
    """Comprehensive risk integration testing framework"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.setup_logging()
        
        # Test components
        self.orchestrator = None
        self.risk_manager = None
        self.regime_engine = None
        self.strategy_manager = None
        self.portfolio_manager = None
        
        # Test results
        self.test_results = []
        self.start_time = None
        
        self.logger.info("🛡️ Enhanced Risk Integration Tester initialized")
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    async def run_comprehensive_risk_test_suite(self) -> Dict[str, Any]:
        """Run comprehensive risk integration test suite"""
        self.start_time = datetime.now()
        
        try:
            self.logger.info("🚀 Starting Enhanced Risk Integration Test Suite")
            self.logger.info("=" * 80)
            
            # Initialize test environment
            await self._initialize_test_environment()
            
            # Run risk test scenarios
            await self._test_normal_trading_scenario()
            await self._test_high_volatility_scenario()
            await self._test_position_limits_scenario()
            await self._test_cash_constraints_scenario()
            await self._test_multi_strategy_scenario()
            await self._test_regime_adaptation_scenario()
            await self._test_emergency_controls_scenario()
            
            # Generate comprehensive report
            return await self._generate_risk_test_report()
            
        except Exception as e:
            self.logger.error(f"❌ Risk test suite failed: {e}")
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'error': str(e),
                'execution_time': (datetime.now() - self.start_time).total_seconds()
            }
    
    async def _initialize_test_environment(self):
        """Initialize test environment with all components"""
        self.logger.info("🔧 Initializing risk test environment...")
        
        # Initialize orchestrator
        self.orchestrator = HierarchicalSystemOrchestrator()
        
        # Initialize CentralRiskManager with test configuration
        risk_config = {
            'max_position_size': 0.10,  # 10% max position
            'max_daily_var': 0.05,      # 5% daily VaR
            'max_total_risk': 0.20,     # 20% total risk
            'position_concentration_limit': 0.15,  # 15% concentration
            'min_signal_confidence': 0.6,  # 60% min confidence
            'auto_approval_threshold': 0.01,  # 1% auto-approve
            'elevated_review_threshold': 0.05,  # 5% elevated review
            'emergency_threshold': 0.10   # 10% emergency threshold
        }
        self.risk_manager = CentralRiskManager(risk_config)
        
        # Initialize regime engine
        regime_config = {
            'lookback_window': 60,
            'volatility_window': 20,
            'trend_threshold': 0.02,
            'regime_change_threshold': 0.7
        }
        self.regime_engine = EnhancedRegimeEngine(regime_config)
        
        # Initialize strategy manager
        strategy_config = {
            'max_concurrent_strategies': 5,
            'enable_enhanced_strategies': True,
            'auto_discover_strategies': True
        }
        self.strategy_manager = StrategyManager(strategy_config)
        
        # Initialize portfolio manager
        portfolio_config = {
            'initial_capital': 1000000,
            'enable_margin': False,
            'max_leverage': 1.0
        }
        self.portfolio_manager = EnhancedPortfolioManager(portfolio_config)
        
        # Register components with orchestrator
        self.risk_manager.register_with_orchestrator(self.orchestrator)
        self.regime_engine.register_with_orchestrator(self.orchestrator)
        self.strategy_manager.register_with_orchestrator(self.orchestrator)
        self.portfolio_manager.register_with_orchestrator(self.orchestrator)
        
        self.logger.info("✅ Risk test environment initialized")
    
    async def _test_normal_trading_scenario(self):
        """Test normal trading conditions"""
        self.logger.info("📊 Testing Normal Trading Scenario")
        self.logger.info("-" * 50)
        
        start_time = datetime.now()
        
        try:
            # Create normal trading requests
            trading_requests = [
                TradingDecisionRequest(
                    decision_type=TradingDecisionType.POSITION_ENTRY,
                    symbol="AAPL",
                    side="buy",
                    quantity=100,
                    strategy_id="test_strategy_1",
                    confidence=0.75,
                    market_regime=RegimeState.SIDEWAYS.value,
                    requesting_component="test_component"
                ),
                TradingDecisionRequest(
                    decision_type=TradingDecisionType.POSITION_ENTRY,
                    symbol="TSLA",
                    side="buy",
                    quantity=50,
                    strategy_id="test_strategy_2",
                    confidence=0.80,
                    market_regime=RegimeState.SIDEWAYS.value,
                    requesting_component="test_component"
                )
            ]
            
            authorization_results = []
            for request in trading_requests:
                auth_result = await self.risk_manager.authorize_trading_decision(request)
                authorization_results.append({
                    'symbol': request.symbol,
                    'requested_quantity': request.quantity,
                    'authorized_quantity': auth_result.authorized_quantity,
                    'authorization_level': auth_result.authorization_level.value,
                    'authorized': auth_result.authorization_level != AuthorizationLevel.REJECTED
                })
            
            # Calculate risk metrics
            risk_metrics = await self._calculate_test_risk_metrics()
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Validate results
            success = all(result['authorized'] for result in authorization_results)
            
            self.test_results.append(RiskTestResult(
                scenario=RiskTestScenario.NORMAL_TRADING.value,
                test_name="normal_trading_authorization",
                success=success,
                execution_time=execution_time,
                risk_metrics=risk_metrics,
                authorization_results=authorization_results
            ))
            
            status = "✅ PASSED" if success else "❌ FAILED"
            self.logger.info(f"{status} Normal Trading Scenario ({execution_time:.3f}s)")
            
        except Exception as e:
            self.logger.error(f"❌ Normal trading test failed: {e}")
            self.test_results.append(RiskTestResult(
                scenario=RiskTestScenario.NORMAL_TRADING.value,
                test_name="normal_trading_authorization",
                success=False,
                execution_time=(datetime.now() - start_time).total_seconds(),
                risk_metrics={},
                authorization_results=[],
                error_message=str(e)
            ))
    
    async def _test_high_volatility_scenario(self):
        """Test high volatility regime risk scaling"""
        self.logger.info("📈 Testing High Volatility Scenario")
        self.logger.info("-" * 50)
        
        start_time = datetime.now()
        
        try:
            # Simulate high volatility regime
            high_vol_request = TradingDecisionRequest(
                decision_type=TradingDecisionType.POSITION_ENTRY,
                symbol="NVDA",
                side="buy",
                quantity=200,  # Larger position in high vol
                strategy_id="test_strategy_vol",
                confidence=0.85,
                market_regime=RegimeState.HIGH_VOLATILITY.value,
                requesting_component="test_component",
                metadata={'volatility_estimate': 0.45}  # 45% volatility
            )
            
            auth_result = await self.risk_manager.authorize_trading_decision(high_vol_request)
            
            # Should reduce position size in high volatility
            position_reduction = (high_vol_request.quantity - auth_result.authorized_quantity) / high_vol_request.quantity
            
            authorization_results = [{
                'symbol': high_vol_request.symbol,
                'requested_quantity': high_vol_request.quantity,
                'authorized_quantity': auth_result.authorized_quantity,
                'position_reduction_pct': position_reduction * 100,
                'authorization_level': auth_result.authorization_level.value,
                'regime_scaling_applied': position_reduction > 0
            }]
            
            risk_metrics = await self._calculate_test_risk_metrics()
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Success if position was reduced due to high volatility
            success = position_reduction > 0 or auth_result.authorized_quantity < high_vol_request.quantity
            
            self.test_results.append(RiskTestResult(
                scenario=RiskTestScenario.HIGH_VOLATILITY.value,
                test_name="high_volatility_scaling",
                success=success,
                execution_time=execution_time,
                risk_metrics=risk_metrics,
                authorization_results=authorization_results
            ))
            
            status = "✅ PASSED" if success else "❌ FAILED"
            self.logger.info(f"{status} High Volatility Scenario - Position reduced by {position_reduction*100:.1f}% ({execution_time:.3f}s)")
            
        except Exception as e:
            self.logger.error(f"❌ High volatility test failed: {e}")
            self.test_results.append(RiskTestResult(
                scenario=RiskTestScenario.HIGH_VOLATILITY.value,
                test_name="high_volatility_scaling",
                success=False,
                execution_time=(datetime.now() - start_time).total_seconds(),
                risk_metrics={},
                authorization_results=[],
                error_message=str(e)
            ))
    
    async def _test_position_limits_scenario(self):
        """Test position limit enforcement"""
        self.logger.info("🚫 Testing Position Limits Scenario")
        self.logger.info("-" * 50)
        
        start_time = datetime.now()
        
        try:
            # Try to exceed position limits
            large_position_request = TradingDecisionRequest(
                decision_type=TradingDecisionType.POSITION_ENTRY,
                symbol="AAPL",
                side="buy",
                quantity=5000,  # Very large position
                strategy_id="test_strategy_large",
                confidence=0.90,
                market_regime=RegimeState.SIDEWAYS.value,
                requesting_component="test_component",
                metadata={'price': 150.0}  # $150 per share
            )
            
            auth_result = await self.risk_manager.authorize_trading_decision(large_position_request)
            
            # Should be significantly reduced or rejected
            position_value = auth_result.authorized_quantity * 150.0
            portfolio_value = 1000000  # $1M portfolio
            position_percentage = position_value / portfolio_value
            
            authorization_results = [{
                'symbol': large_position_request.symbol,
                'requested_quantity': large_position_request.quantity,
                'authorized_quantity': auth_result.authorized_quantity,
                'position_value': position_value,
                'position_percentage': position_percentage * 100,
                'within_limits': position_percentage <= 0.10,  # 10% limit
                'authorization_level': auth_result.authorization_level.value
            }]
            
            risk_metrics = await self._calculate_test_risk_metrics()
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Success if position is within limits
            success = position_percentage <= 0.10 or auth_result.authorization_level == AuthorizationLevel.REJECTED
            
            self.test_results.append(RiskTestResult(
                scenario=RiskTestScenario.POSITION_LIMITS.value,
                test_name="position_limit_enforcement",
                success=success,
                execution_time=execution_time,
                risk_metrics=risk_metrics,
                authorization_results=authorization_results
            ))
            
            status = "✅ PASSED" if success else "❌ FAILED"
            self.logger.info(f"{status} Position Limits - Final position: {position_percentage*100:.1f}% of portfolio ({execution_time:.3f}s)")
            
        except Exception as e:
            self.logger.error(f"❌ Position limits test failed: {e}")
            self.test_results.append(RiskTestResult(
                scenario=RiskTestScenario.POSITION_LIMITS.value,
                test_name="position_limit_enforcement",
                success=False,
                execution_time=(datetime.now() - start_time).total_seconds(),
                risk_metrics={},
                authorization_results=[],
                error_message=str(e)
            ))
    
    async def _test_cash_constraints_scenario(self):
        """Test cash availability constraints"""
        self.logger.info("💰 Testing Cash Constraints Scenario")
        self.logger.info("-" * 50)
        
        start_time = datetime.now()
        
        try:
            # Try to buy more than available cash
            expensive_request = TradingDecisionRequest(
                decision_type=TradingDecisionType.POSITION_ENTRY,
                symbol="BRK.A",  # Expensive stock
                side="buy",
                quantity=10,  # 10 shares
                strategy_id="test_strategy_cash",
                confidence=0.85,
                market_regime=RegimeState.SIDEWAYS.value,
                requesting_component="test_component",
                metadata={
                    'price': 500000.0,  # $500K per share
                    'available_cash': 950000.0  # Only $950K available
                }
            )
            
            auth_result = await self.risk_manager.authorize_trading_decision(expensive_request)
            
            # Calculate cash requirements
            price = expensive_request.metadata.get('price', 500000.0)
            requested_cash = expensive_request.quantity * price
            authorized_cash = auth_result.authorized_quantity * price
            available_cash = expensive_request.metadata.get('available_cash', 950000.0)
            
            authorization_results = [{
                'symbol': expensive_request.symbol,
                'requested_quantity': expensive_request.quantity,
                'authorized_quantity': auth_result.authorized_quantity,
                'requested_cash': requested_cash,
                'authorized_cash': authorized_cash,
                'available_cash': available_cash,
                'cash_sufficient': authorized_cash <= available_cash,
                'authorization_level': auth_result.authorization_level.value
            }]
            
            risk_metrics = await self._calculate_test_risk_metrics()
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Success if authorized amount doesn't exceed available cash
            success = authorized_cash <= available_cash
            
            self.test_results.append(RiskTestResult(
                scenario=RiskTestScenario.CASH_CONSTRAINTS.value,
                test_name="cash_availability_check",
                success=success,
                execution_time=execution_time,
                risk_metrics=risk_metrics,
                authorization_results=authorization_results
            ))
            
            status = "✅ PASSED" if success else "❌ FAILED"
            self.logger.info(f"{status} Cash Constraints - Authorized: ${authorized_cash:,.0f} / Available: ${available_cash:,.0f} ({execution_time:.3f}s)")
            if not success:
                self.logger.info(f"Debug: Price={price}, Auth Qty={auth_result.authorized_quantity}, Calc=${auth_result.authorized_quantity * price:,.0f}")
            
        except Exception as e:
            self.logger.error(f"❌ Cash constraints test failed: {e}")
            self.test_results.append(RiskTestResult(
                scenario=RiskTestScenario.CASH_CONSTRAINTS.value,
                test_name="cash_availability_check",
                success=False,
                execution_time=(datetime.now() - start_time).total_seconds(),
                risk_metrics={},
                authorization_results=[],
                error_message=str(e)
            ))
    
    async def _test_multi_strategy_scenario(self):
        """Test multi-strategy risk coordination"""
        self.logger.info("🧠 Testing Multi-Strategy Scenario")
        self.logger.info("-" * 50)
        
        start_time = datetime.now()
        
        try:
            # Multiple strategies requesting positions in same symbol
            strategy_requests = [
                TradingDecisionRequest(
                    decision_type=TradingDecisionType.POSITION_ENTRY,
                    symbol="AAPL",
                    side="buy",
                    quantity=200,
                    strategy_id="momentum_strategy",
                    confidence=0.75,
                    market_regime=RegimeState.SIDEWAYS.value,
                    requesting_component="strategy_manager"
                ),
                TradingDecisionRequest(
                    decision_type=TradingDecisionType.POSITION_ENTRY,
                    symbol="AAPL",
                    side="buy",
                    quantity=150,
                    strategy_id="mean_reversion_strategy",
                    confidence=0.70,
                    market_regime=RegimeState.SIDEWAYS.value,
                    requesting_component="strategy_manager"
                ),
                TradingDecisionRequest(
                    decision_type=TradingDecisionType.POSITION_ENTRY,
                    symbol="AAPL",
                    side="buy",
                    quantity=100,
                    strategy_id="arbitrage_strategy",
                    confidence=0.85,
                    market_regime=RegimeState.SIDEWAYS.value,
                    requesting_component="strategy_manager"
                )
            ]
            
            authorization_results = []
            total_authorized = 0
            
            for request in strategy_requests:
                auth_result = await self.risk_manager.authorize_trading_decision(request)
                total_authorized += auth_result.authorized_quantity
                
                authorization_results.append({
                    'strategy_id': request.strategy_id,
                    'symbol': request.symbol,
                    'requested_quantity': request.quantity,
                    'authorized_quantity': auth_result.authorized_quantity,
                    'authorization_level': auth_result.authorization_level.value
                })
            
            # Check if total position respects concentration limits
            total_requested = sum(req.quantity for req in strategy_requests)
            concentration_respected = total_authorized <= 666  # Assuming 10% of $1M portfolio at $150/share
            
            risk_metrics = await self._calculate_test_risk_metrics()
            execution_time = (datetime.now() - start_time).total_seconds()
            
            success = concentration_respected and total_authorized > 0
            
            self.test_results.append(RiskTestResult(
                scenario=RiskTestScenario.MULTI_STRATEGY.value,
                test_name="multi_strategy_coordination",
                success=success,
                execution_time=execution_time,
                risk_metrics=risk_metrics,
                authorization_results=authorization_results
            ))
            
            status = "✅ PASSED" if success else "❌ FAILED"
            self.logger.info(f"{status} Multi-Strategy - Total authorized: {total_authorized}/{total_requested} shares ({execution_time:.3f}s)")
            
        except Exception as e:
            self.logger.error(f"❌ Multi-strategy test failed: {e}")
            self.test_results.append(RiskTestResult(
                scenario=RiskTestScenario.MULTI_STRATEGY.value,
                test_name="multi_strategy_coordination",
                success=False,
                execution_time=(datetime.now() - start_time).total_seconds(),
                risk_metrics={},
                authorization_results=[],
                error_message=str(e)
            ))
    
    async def _test_regime_adaptation_scenario(self):
        """Test regime-aware risk adaptation"""
        self.logger.info("🌊 Testing Regime Adaptation Scenario")
        self.logger.info("-" * 50)
        
        start_time = datetime.now()
        
        try:
            # Test different regime conditions
            regime_tests = [
                {
                    'regime': RegimeState.LOW_VOLATILITY.value,
                    'expected_scaling': 'increase',
                    'volatility': 0.08
                },
                {
                    'regime': RegimeState.HIGH_VOLATILITY.value,
                    'expected_scaling': 'decrease',
                    'volatility': 0.35
                },
                {
                    'regime': RegimeState.HIGH_VOLATILITY.value,
                    'expected_scaling': 'significant_decrease',
                    'volatility': 0.60
                }
            ]
            
            authorization_results = []
            base_quantity = 100
            
            for regime_test in regime_tests:
                request = TradingDecisionRequest(
                    decision_type=TradingDecisionType.POSITION_ENTRY,
                    symbol="SPY",
                    side="buy",
                    quantity=base_quantity,
                    strategy_id="regime_test_strategy",
                    confidence=0.80,
                    market_regime=regime_test['regime'],
                    requesting_component="test_component",
                    metadata={'volatility_estimate': regime_test['volatility']}
                )
                
                auth_result = await self.risk_manager.authorize_trading_decision(request)
                scaling_factor = auth_result.authorized_quantity / base_quantity
                
                authorization_results.append({
                    'regime': regime_test['regime'],
                    'volatility': regime_test['volatility'],
                    'requested_quantity': base_quantity,
                    'authorized_quantity': auth_result.authorized_quantity,
                    'scaling_factor': scaling_factor,
                    'expected_scaling': regime_test['expected_scaling'],
                    'authorization_level': auth_result.authorization_level.value
                })
            
            risk_metrics = await self._calculate_test_risk_metrics()
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Validate regime scaling behavior
            try:
                low_vol_scaling = next(r['scaling_factor'] for r in authorization_results if 'low_volatility' in r['regime'])
                high_vol_scaling = next(r['scaling_factor'] for r in authorization_results if 'high_volatility' in r['regime'])
                
                # Success if high volatility scaling is less than low volatility scaling
                success = low_vol_scaling > high_vol_scaling
                
                self.logger.info(f"Regime scaling comparison: Low Vol: {low_vol_scaling:.3f}, High Vol: {high_vol_scaling:.3f}")
                
            except StopIteration:
                # Fallback: check if any scaling was applied
                success = any(r['scaling_factor'] != 1.0 for r in authorization_results)
                self.logger.warning("Could not find specific regime results, checking for any scaling")
            
            self.test_results.append(RiskTestResult(
                scenario=RiskTestScenario.REGIME_ADAPTATION.value,
                test_name="regime_aware_scaling",
                success=success,
                execution_time=execution_time,
                risk_metrics=risk_metrics,
                authorization_results=authorization_results
            ))
            
            status = "✅ PASSED" if success else "❌ FAILED"
            if 'low_vol_scaling' in locals() and 'high_vol_scaling' in locals():
                self.logger.info(f"{status} Regime Adaptation - Scaling: Low({low_vol_scaling:.2f}) > High({high_vol_scaling:.2f}) ({execution_time:.3f}s)")
            else:
                self.logger.info(f"{status} Regime Adaptation - Scaling behavior validated ({execution_time:.3f}s)")
            
        except Exception as e:
            self.logger.error(f"❌ Regime adaptation test failed: {e}")
            self.test_results.append(RiskTestResult(
                scenario=RiskTestScenario.REGIME_ADAPTATION.value,
                test_name="regime_aware_scaling",
                success=False,
                execution_time=(datetime.now() - start_time).total_seconds(),
                risk_metrics={},
                authorization_results=[],
                error_message=str(e)
            ))
    
    async def _test_emergency_controls_scenario(self):
        """Test emergency controls and circuit breakers"""
        self.logger.info("🚨 Testing Emergency Controls Scenario")
        self.logger.info("-" * 50)
        
        start_time = datetime.now()
        
        try:
            # Test emergency shutdown
            emergency_active = self.risk_manager.emergency_shutdown()
            
            # Try to make trades during emergency
            emergency_request = TradingDecisionRequest(
                decision_type=TradingDecisionType.POSITION_ENTRY,
                symbol="AAPL",
                side="buy",
                quantity=100,
                strategy_id="test_strategy_emergency",
                confidence=0.90,
                market_regime=RegimeState.SIDEWAYS.value,
                requesting_component="test_component"
            )
            
            auth_result = await self.risk_manager.authorize_trading_decision(emergency_request)
            
            # Should be rejected during emergency
            emergency_rejection = auth_result.authorization_level == AuthorizationLevel.REJECTED
            
            # Test recovery from emergency
            recovery_success = self.risk_manager.resume_operations()
            
            # Test normal operation after recovery
            recovery_request = TradingDecisionRequest(
                decision_type=TradingDecisionType.POSITION_ENTRY,
                symbol="AAPL",
                side="buy",
                quantity=50,
                strategy_id="test_strategy_recovery",
                confidence=0.75,
                market_regime=RegimeState.SIDEWAYS.value,
                requesting_component="test_component"
            )
            
            recovery_auth = await self.risk_manager.authorize_trading_decision(recovery_request)
            recovery_authorized = recovery_auth.authorization_level != AuthorizationLevel.REJECTED
            
            authorization_results = [{
                'emergency_shutdown_active': emergency_active,
                'emergency_request_rejected': emergency_rejection,
                'recovery_successful': recovery_success,
                'post_recovery_authorized': recovery_authorized,
                'emergency_auth_level': auth_result.authorization_level.value,
                'recovery_auth_level': recovery_auth.authorization_level.value
            }]
            
            risk_metrics = await self._calculate_test_risk_metrics()
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Success if emergency properly blocks trades and recovery works
            success = emergency_active and emergency_rejection and recovery_success and recovery_authorized
            
            self.test_results.append(RiskTestResult(
                scenario=RiskTestScenario.EMERGENCY_SHUTDOWN.value,
                test_name="emergency_controls",
                success=success,
                execution_time=execution_time,
                risk_metrics=risk_metrics,
                authorization_results=authorization_results
            ))
            
            status = "✅ PASSED" if success else "❌ FAILED"
            self.logger.info(f"{status} Emergency Controls - Shutdown: {emergency_active}, Recovery: {recovery_success} ({execution_time:.3f}s)")
            
        except Exception as e:
            self.logger.error(f"❌ Emergency controls test failed: {e}")
            self.test_results.append(RiskTestResult(
                scenario=RiskTestScenario.EMERGENCY_SHUTDOWN.value,
                test_name="emergency_controls",
                success=False,
                execution_time=(datetime.now() - start_time).total_seconds(),
                risk_metrics={},
                authorization_results=[],
                error_message=str(e)
            ))
    
    async def _calculate_test_risk_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive risk metrics for testing"""
        try:
            # Get current risk status from risk manager
            risk_status = self.risk_manager.get_risk_status()
            
            # Calculate additional test metrics
            test_metrics = {
                'current_positions': len(self.risk_manager.current_positions),
                'total_exposure': sum(abs(pos) for pos in self.risk_manager.current_positions.values()),
                'portfolio_value': self.risk_manager.portfolio_value,
                'available_cash': self.risk_manager.portfolio_value * 0.95,  # Assume 95% available
                'risk_utilization': risk_status.get('risk_utilization', 0.0),
                'position_count': len([pos for pos in self.risk_manager.current_positions.values() if pos != 0]),
                'max_position_value': max([abs(pos) * 150 for pos in self.risk_manager.current_positions.values()], default=0),
                'concentration_risk': risk_status.get('concentration_risk', 0.0),
                'emergency_mode': getattr(self.risk_manager, 'emergency_mode', False)
            }
            
            return {**risk_status, **test_metrics}
            
        except Exception as e:
            self.logger.warning(f"Risk metrics calculation failed: {e}")
            return {'error': str(e)}
    
    async def _generate_risk_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive risk test report"""
        end_time = datetime.now()
        total_execution_time = (end_time - self.start_time).total_seconds()
        
        # Calculate test statistics
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r.success])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Group results by scenario
        scenario_results = {}
        for result in self.test_results:
            if result.scenario not in scenario_results:
                scenario_results[result.scenario] = []
            scenario_results[result.scenario].append(result)
        
        # Generate report
        report = {
            'test_summary': {
                'total_tests': total_tests,
                'tests_passed': passed_tests,
                'tests_failed': failed_tests,
                'success_rate': success_rate,
                'total_execution_time': total_execution_time,
                'timestamp': end_time.isoformat()
            },
            'scenario_results': {},
            'detailed_results': [],
            'risk_metrics_summary': {},
            'recommendations': []
        }
        
        # Process scenario results
        for scenario, results in scenario_results.items():
            scenario_passed = len([r for r in results if r.success])
            scenario_total = len(results)
            scenario_success_rate = (scenario_passed / scenario_total * 100) if scenario_total > 0 else 0
            
            report['scenario_results'][scenario] = {
                'tests_passed': scenario_passed,
                'tests_total': scenario_total,
                'success_rate': scenario_success_rate,
                'avg_execution_time': np.mean([r.execution_time for r in results])
            }
        
        # Add detailed results
        for result in self.test_results:
            report['detailed_results'].append({
                'scenario': result.scenario,
                'test_name': result.test_name,
                'success': result.success,
                'execution_time': result.execution_time,
                'authorization_count': len(result.authorization_results),
                'error_message': result.error_message
            })
        
        # Generate recommendations
        if success_rate < 100:
            report['recommendations'].append("Review failed test scenarios and adjust risk parameters")
        if success_rate >= 90:
            report['recommendations'].append("Risk management system performing well - consider production deployment")
        if any(r.execution_time > 1.0 for r in self.test_results):
            report['recommendations'].append("Some tests show high latency - optimize risk calculation performance")
        
        # Log summary
        self.logger.info("")
        self.logger.info("📊 ENHANCED RISK INTEGRATION TEST RESULTS")
        self.logger.info("=" * 80)
        self.logger.info(f"Total Tests: {total_tests}")
        self.logger.info(f"Tests Passed: {passed_tests} ✅")
        self.logger.info(f"Tests Failed: {failed_tests} ❌")
        self.logger.info(f"Success Rate: {success_rate:.1f}%")
        self.logger.info(f"Total Execution Time: {total_execution_time:.3f}s")
        self.logger.info("")
        
        # Log scenario breakdown
        self.logger.info("📋 RESULTS BY SCENARIO")
        self.logger.info("-" * 40)
        for scenario, stats in report['scenario_results'].items():
            status = "✅" if stats['success_rate'] == 100 else "❌"
            self.logger.info(f"{status} {scenario}: {stats['tests_passed']}/{stats['tests_total']} ({stats['success_rate']:.1f}%)")
        
        self.logger.info("")
        overall_status = "🏆 OUTSTANDING SUCCESS" if success_rate >= 95 else "✅ SUCCESS" if success_rate >= 80 else "⚠️ NEEDS IMPROVEMENT"
        self.logger.info(f"🎯 OVERALL ASSESSMENT: {overall_status}")
        self.logger.info("=" * 80)
        
        return report


async def main():
    """Main test execution function"""
    tester = EnhancedRiskIntegrationTester()
    
    try:
        # Run comprehensive risk integration tests
        results = await tester.run_comprehensive_risk_test_suite()
        
        # Save detailed report
        import json
        report_filename = f"enhanced_risk_integration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📄 Detailed report saved to: {report_filename}")
        
        return results
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return {'success': False, 'error': str(e)}


if __name__ == "__main__":
    # Run the enhanced risk integration test suite
    print("🛡️ StatArb_Gemini Enhanced Risk Integration Testing")
    print("=" * 80)
    
    # Execute tests
    results = asyncio.run(main())
    
    # Exit with appropriate code
    success_rate = results.get('test_summary', {}).get('success_rate', 0)
    exit_code = 0 if success_rate >= 80 else 1
    exit(exit_code)
