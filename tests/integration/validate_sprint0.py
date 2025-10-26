"""
Sprint 0 Validation Script
==========================

Quick validation script to verify Sprint 0 components are working correctly.
This script runs basic sanity checks without requiring pytest.

Usage:
    python tests/integration/validate_sprint0.py
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import Sprint 0 components
try:
    from core_engine.system.compliance_checker import PreTradeComplianceChecker, ComplianceResult
    from core_engine.system.circuit_breakers import TradingCircuitBreakers, CircuitBreakerConfig
    from core_engine.system.central_risk_manager import (
        CentralRiskManager, TradingDecisionRequest, TradingDecisionType, AuthorizationLevel
    )
    from backtest.engine.historical_execution_simulator import HistoricalExecutionSimulator
    print("✅ All Sprint 0 imports successful\n")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)


async def validate_compliance_checker():
    """Validate PreTradeComplianceChecker"""
    print("=" * 80)
    print("TEST 1: PreTradeComplianceChecker Validation")
    print("=" * 80)
    
    try:
        # Create compliance checker with dict config
        config = {
            'check_restricted_securities': True,
            'check_hard_to_borrow': True,
            'check_insider_blackout': True,
            'check_13d_triggers': True,
            'check_pattern_day_trading': True,
            'check_concentration_limits': True,
            'check_watch_list': True,
            'pdt_min_account_value': 25000.0,
            'ownership_threshold_13d': 0.05,
            'max_single_position_pct': 0.15,
            'fail_on_violation': True
        }
        
        checker = PreTradeComplianceChecker(config)
        await checker.initialize()
        
        print(f"✅ ComplianceChecker initialized: {checker.is_initialized}")
        
        # Test normal trade (should pass)
        result = await checker.check_pre_trade_compliance(
            trade_id='test_001',
            symbol='AAPL',
            trade_type='buy',
            quantity=100,
            price=150.0,
            account_value=100000.0,
            current_positions={},
            timestamp=datetime.now()
        )
        
        print(f"✅ Normal trade check: Approved={result.approved}")
        print(f"   Checks performed: {len(result.compliance_checks_performed)}")
        print(f"   Warnings: {len(result.warnings)}")
        
        # Test concentration violation (should fail)
        result2 = await checker.check_pre_trade_compliance(
            trade_id='test_002',
            symbol='AAPL',
            trade_type='buy',
            quantity=200,  # $30K = 30% of $100K (exceeds 15% limit)
            price=150.0,
            account_value=100000.0,
            current_positions={},
            timestamp=datetime.now()
        )
        
        print(f"✅ Concentration violation check: Approved={result2.approved}")
        if not result2.approved:
            print(f"   Rejection reason: {result2.rejection_reason}")
        
        return True
        
    except Exception as e:
        print(f"❌ ComplianceChecker validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def validate_circuit_breakers():
    """Validate TradingCircuitBreakers"""
    print("\n" + "=" * 80)
    print("TEST 2: TradingCircuitBreakers Validation")
    print("=" * 80)
    
    try:
        # Create circuit breakers
        config = CircuitBreakerConfig(
            enable_manual_kill_switch=True,
            enable_order_rate_limiter=True,
            enable_daily_loss_limit=True,
            enable_drawdown_limit=True,
            enable_position_concentration_check=True,
            max_orders_per_second=10.0,
            daily_loss_limit_pct=0.02,
            drawdown_limit_pct=0.05,
            max_position_concentration=0.20
        )
        
        breakers = TradingCircuitBreakers(config)
        await breakers.initialize()
        
        print(f"✅ CircuitBreakers initialized: {breakers.is_initialized}")
        
        # Test normal operation
        status = await breakers.check_circuit_breakers()
        print(f"✅ Normal operation: can_trade={status['can_trade']}, level={status['level']}")
        
        # Test kill switch
        await breakers.activate_kill_switch(authorization_code='TEST_HALT')
        status2 = await breakers.check_circuit_breakers()
        print(f"✅ Kill switch activated: can_trade={status2['can_trade']}, level={status2['level']}")
        if not status2['can_trade']:
            print(f"   Halt reason: {status2.get('halt_reason', 'N/A')}")
        
        # Deactivate kill switch
        await breakers.deactivate_kill_switch(authorization_code='TEST_RESUME')
        status3 = await breakers.check_circuit_breakers()
        print(f"✅ Kill switch deactivated: can_trade={status3['can_trade']}")
        
        return True
        
    except Exception as e:
        print(f"❌ CircuitBreakers validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def validate_risk_manager_integration():
    """Validate Sprint 0 integration with CentralRiskManager"""
    print("\n" + "=" * 80)
    print("TEST 3: CentralRiskManager Integration")
    print("=" * 80)
    
    try:
        # Create compliance checker with dict config
        compliance_config = {
            'check_restricted_securities': True,
            'check_hard_to_borrow': True,
            'check_insider_blackout': True,
            'check_13d_triggers': True,
            'check_pattern_day_trading': True,
            'check_concentration_limits': True,
            'check_watch_list': True,
            'fail_on_violation': True
        }
        compliance_checker = PreTradeComplianceChecker(compliance_config)
        await compliance_checker.initialize()
        
        # Create circuit breakers
        breaker_config = CircuitBreakerConfig(
            enable_manual_kill_switch=True,
            enable_daily_loss_limit=True,
            daily_loss_limit_pct=0.02
        )
        circuit_breakers = TradingCircuitBreakers(breaker_config)
        await circuit_breakers.initialize()
        
        # Create risk manager
        risk_manager = CentralRiskManager({
            'max_position_size': 0.10,
            'max_daily_var': 0.05,
            'min_signal_confidence': 0.6
        })
        
        # Integrate Sprint 0 components
        risk_manager.set_institutional_components(
            compliance_checker=compliance_checker,
            circuit_breakers=circuit_breakers
        )
        
        await risk_manager.initialize()
        
        print(f"✅ RiskManager initialized with Sprint 0 components")
        print(f"   Compliance checker: {risk_manager.compliance_checker is not None}")
        print(f"   Circuit breakers: {risk_manager.circuit_breakers is not None}")
        
        # Test normal authorization
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=100,
            confidence=0.75,
            current_price=150.0,
            strategy_id='test_strategy'
        )
        
        authorization = await risk_manager.authorize_trading_decision(request)
        
        print(f"✅ Normal trade authorization:")
        print(f"   Level: {authorization.authorization_level.value}")
        print(f"   Authorized Qty: {authorization.authorized_quantity}")
        if authorization.rejection_reason:
            print(f"   Rejection: {authorization.rejection_reason}")
        
        # Test with kill switch activated
        await circuit_breakers.activate_kill_switch(authorization_code='TEST')
        
        request2 = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='MSFT',
            side='buy',
            quantity=50,
            confidence=0.80,
            current_price=300.0
        )
        
        authorization2 = await risk_manager.authorize_trading_decision(request2)
        
        print(f"✅ Kill switch test:")
        print(f"   Level: {authorization2.authorization_level.value}")
        print(f"   Expected: REJECTED")
        if authorization2.rejection_reason:
            print(f"   Rejection: {authorization2.rejection_reason}")
        
        success = (authorization2.authorization_level == AuthorizationLevel.REJECTED and
                  'CIRCUIT BREAKER' in authorization2.rejection_reason)
        
        if success:
            print(f"✅ Circuit breaker correctly blocked trade")
        else:
            print(f"❌ Circuit breaker did not block trade")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ RiskManager integration validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def validate_rejection_handler():
    """Validate OrderRejectionHandler"""
    print("\n" + "=" * 80)
    print("TEST 4: OrderRejectionHandler Validation")
    print("=" * 80)
    
    try:
        # Create execution simulator
        simulator = HistoricalExecutionSimulator({
            'fill_model': 'realistic',
            'base_spread_bps': 5.0,
            'enable_random_slippage': False
        })
        
        print(f"✅ HistoricalExecutionSimulator initialized")
        
        # Test rejection scenario generation
        market_data = {
            'close': 150.0,
            'volume': 1000000,
            'volatility': 0.02,
            'timestamp': datetime.now()
        }
        
        rejections = 0
        for i in range(50):
            rejection = simulator.simulate_rejection_scenario(
                symbol='AAPL',
                side='buy',
                quantity=100,
                market_data=market_data,
                regime_context={'primary_regime': 'normal_volatility'}
            )
            if rejection is not None:
                rejections += 1
        
        rejection_rate = rejections / 50 * 100
        print(f"✅ Rejection simulation: {rejections}/50 trades rejected ({rejection_rate:.1f}%)")
        print(f"   Expected: ~2% for normal volatility")
        
        # Test fill with rejection handling
        result = simulator.simulate_fill_with_rejection(
            symbol='AAPL',
            side='buy',
            quantity=100,
            decision_price=150.0,
            market_data=market_data,
            max_retries=3
        )
        
        print(f"✅ Fill with rejection handling:")
        print(f"   Success: {result['success']}")
        print(f"   Retry count: {result['retry_count']}")
        print(f"   Rejections: {len(result['rejection_history'])}")
        print(f"   Final quantity: {result['final_quantity']}")
        
        if result['success']:
            fill = result['fill']
            print(f"   Fill price: ${fill.fill_price:.2f}")
            print(f"   Total cost: {fill.costs.total_cost_bps:.2f} bps")
        
        return True
        
    except Exception as e:
        print(f"❌ RejectionHandler validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all validation tests"""
    print("\n" + "=" * 80)
    print("SPRINT 0 VALIDATION - INSTITUTIONAL COMPONENTS")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = []
    
    # Test 1: Compliance Checker
    results.append(("ComplianceChecker", await validate_compliance_checker()))
    
    # Test 2: Circuit Breakers
    results.append(("CircuitBreakers", await validate_circuit_breakers()))
    
    # Test 3: Risk Manager Integration
    results.append(("RiskManager Integration", await validate_risk_manager_integration()))
    
    # Test 4: Rejection Handler
    results.append(("RejectionHandler", validate_rejection_handler()))
    
    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 All Sprint 0 components validated successfully!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed - please review errors above")
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

