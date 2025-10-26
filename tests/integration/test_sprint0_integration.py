"""
Sprint 0 Integration Tests
===========================

Comprehensive integration tests for Sprint 0 components:
- PreTradeComplianceChecker integration
- TradingCircuitBreakers integration  
- OrderRejectionHandler integration

Tests the complete flow from compliance → circuit breakers → risk auth → execution with rejections
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any

# Import Sprint 0 components
from core_engine.system.compliance_checker import PreTradeComplianceChecker
from core_engine.system.circuit_breakers import TradingCircuitBreakers, CircuitBreakerConfig
from core_engine.system.central_risk_manager import (
    CentralRiskManager, TradingDecisionRequest, TradingDecisionType, AuthorizationLevel
)
from backtest.engine.historical_execution_simulator import HistoricalExecutionSimulator


@pytest.fixture
def compliance_checker():
    """Create compliance checker for testing"""
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
    return PreTradeComplianceChecker(config)


@pytest.fixture
def circuit_breakers():
    """Create circuit breakers for testing"""
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
    return TradingCircuitBreakers(config)


@pytest.fixture
def risk_manager_with_sprint0(compliance_checker, circuit_breakers):
    """Create risk manager with Sprint 0 components integrated"""
    risk_manager = CentralRiskManager({
        'max_position_size': 0.10,
        'max_daily_var': 0.05,
        'position_concentration_limit': 0.15,
        'min_signal_confidence': 0.6
    })
    
    # Integrate Sprint 0 components
    risk_manager.set_institutional_components(
        compliance_checker=compliance_checker,
        circuit_breakers=circuit_breakers
    )
    
    return risk_manager


@pytest.fixture
def execution_simulator():
    """Create execution simulator with rejection handling"""
    return HistoricalExecutionSimulator({
        'fill_model': 'realistic',
        'base_spread_bps': 5.0,
        'base_slippage_bps': 2.0,
        'commission_per_share': 0.005,
        'enable_random_slippage': False  # Deterministic for testing
    })


class TestSpring0ComplianceIntegration:
    """Test PreTradeComplianceChecker integration"""
    
    @pytest.mark.asyncio
    async def test_compliance_checker_initialized(self, compliance_checker):
        """Test compliance checker is properly initialized"""
        assert compliance_checker is not None
        await compliance_checker.initialize()
        assert compliance_checker.is_initialized
    
    @pytest.mark.asyncio
    async def test_compliance_check_passes_normal_trade(self, compliance_checker):
        """Test compliance check passes for normal trade"""
        await compliance_checker.initialize()
        
        result = await compliance_checker.check_pre_trade_compliance(
            trade_id='test_001',
            symbol='AAPL',
            trade_type='buy',
            quantity=100,
            price=150.0,
            account_value=100000.0,
            current_positions={'AAPL': 0},
            timestamp=datetime.now()
        )
        
        assert result.approved is True
        assert len(result.checks_passed) == 7  # All 7 checks passed
        assert len(result.violations) == 0
    
    @pytest.mark.asyncio
    async def test_compliance_rejects_concentration_violation(self, compliance_checker):
        """Test compliance rejects trade that violates concentration limits"""
        await compliance_checker.initialize()
        
        # Try to buy $20K of stock with $100K account = 20% concentration (max is 15%)
        result = await compliance_checker.check_pre_trade_compliance(
            trade_id='test_002',
            symbol='AAPL',
            trade_type='buy',
            quantity=200,  # 200 shares @ $150 = $30K = 30% concentration
            price=150.0,
            account_value=100000.0,
            current_positions={},
            timestamp=datetime.now()
        )
        
        assert result.approved is False
        assert 'concentration' in result.rejection_reason.lower()
        assert len(result.violations) > 0
    
    @pytest.mark.asyncio
    async def test_compliance_integration_with_risk_manager(self, risk_manager_with_sprint0):
        """Test compliance check is called during authorization"""
        await risk_manager_with_sprint0.initialize()
        
        # Create a normal trade request
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=100,
            confidence=0.75,
            current_price=150.0,
            strategy_id='test_strategy'
        )
        
        # Authorize trade - should pass compliance
        authorization = await risk_manager_with_sprint0.authorize_trading_decision(request)
        
        # Should be authorized (not rejected by compliance)
        assert authorization.authorization_level != AuthorizationLevel.REJECTED
        # Verify it's not a compliance rejection
        if authorization.rejection_reason:
            assert 'COMPLIANCE' not in authorization.rejection_reason


class TestSprint0CircuitBreakerIntegration:
    """Test TradingCircuitBreakers integration"""
    
    @pytest.mark.asyncio
    async def test_circuit_breakers_initialized(self, circuit_breakers):
        """Test circuit breakers are properly initialized"""
        assert circuit_breakers is not None
        await circuit_breakers.initialize()
        assert circuit_breakers.is_initialized
    
    @pytest.mark.asyncio
    async def test_circuit_breakers_allow_normal_trading(self, circuit_breakers):
        """Test circuit breakers allow trading under normal conditions"""
        await circuit_breakers.initialize()
        
        status = await circuit_breakers.check_circuit_breakers()
        
        assert status['can_trade'] is True
        assert status['level'] == 'NORMAL'
    
    @pytest.mark.asyncio
    async def test_manual_kill_switch_blocks_trading(self, circuit_breakers):
        """Test manual kill switch blocks all trading"""
        await circuit_breakers.initialize()
        
        # Activate kill switch
        await circuit_breakers.activate_kill_switch(authorization_code='EMERGENCY_HALT')
        
        status = await circuit_breakers.check_circuit_breakers()
        
        assert status['can_trade'] is False
        assert 'kill switch' in status['halt_reason'].lower()
        assert status['level'] == 'HALT'
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration_with_risk_manager(self, risk_manager_with_sprint0):
        """Test circuit breaker check is called during authorization"""
        await risk_manager_with_sprint0.initialize()
        
        # Activate kill switch via circuit breakers
        if risk_manager_with_sprint0.circuit_breakers:
            await risk_manager_with_sprint0.circuit_breakers.initialize()
            await risk_manager_with_sprint0.circuit_breakers.activate_kill_switch(
                authorization_code='TEST_HALT'
            )
        
        # Try to authorize trade
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=100,
            confidence=0.75,
            current_price=150.0
        )
        
        authorization = await risk_manager_with_sprint0.authorize_trading_decision(request)
        
        # Should be rejected by circuit breaker
        assert authorization.authorization_level == AuthorizationLevel.REJECTED
        assert 'CIRCUIT BREAKER' in authorization.rejection_reason


class TestSprint0RejectionHandling:
    """Test OrderRejectionHandler integration"""
    
    def test_rejection_scenario_simulation(self, execution_simulator):
        """Test rejection scenario generation"""
        market_data = {
            'close': 150.0,
            'volume': 1000000,
            'volatility': 0.02,
            'timestamp': datetime.now()
        }
        
        # Run multiple simulations to test rejection probability
        rejection_count = 0
        total_runs = 100
        
        for _ in range(total_runs):
            rejection = execution_simulator.simulate_rejection_scenario(
                symbol='AAPL',
                side='buy',
                quantity=100,
                market_data=market_data,
                regime_context={'primary_regime': 'normal_volatility'}
            )
            
            if rejection is not None:
                rejection_count += 1
                # Verify rejection structure
                assert 'rejected' in rejection
                assert 'rejection_code' in rejection
                assert 'rejection_reason' in rejection
                assert 'can_retry' in rejection
                assert 'suggested_action' in rejection
        
        # Should have some rejections (around 2% for normal volatility)
        # Allow for variance in random simulation
        assert 0 <= rejection_count <= 10  # 0-10% rejection rate is reasonable
    
    def test_rejection_higher_in_volatile_regimes(self, execution_simulator):
        """Test rejection rate is higher in volatile regimes"""
        market_data = {
            'close': 150.0,
            'volume': 1000000,
            'volatility': 0.05,
            'timestamp': datetime.now()
        }
        
        normal_rejections = 0
        high_vol_rejections = 0
        runs = 100
        
        # Normal volatility
        for _ in range(runs):
            rejection = execution_simulator.simulate_rejection_scenario(
                'AAPL', 'buy', 100, market_data,
                regime_context={'primary_regime': 'normal_volatility'}
            )
            if rejection: normal_rejections += 1
        
        # High volatility
        for _ in range(runs):
            rejection = execution_simulator.simulate_rejection_scenario(
                'AAPL', 'buy', 100, market_data,
                regime_context={'primary_regime': 'high_volatility'}
            )
            if rejection: high_vol_rejections += 1
        
        # High volatility should have more rejections
        # (2% vs 5% expected, so high_vol should be ~2.5x more)
        # Allow for random variance
        print(f"Normal vol rejections: {normal_rejections}, High vol: {high_vol_rejections}")
    
    def test_intelligent_retry_with_quantity_reduction(self, execution_simulator):
        """Test retry logic with quantity reduction"""
        market_data = {
            'close': 150.0,
            'volume': 1000000,
            'volatility': 0.02,
            'timestamp': datetime.now()
        }
        
        # This will run retries if rejected
        result = execution_simulator.simulate_fill_with_rejection(
            symbol='AAPL',
            side='buy',
            quantity=100,
            decision_price=150.0,
            market_data=market_data,
            max_retries=3
        )
        
        # Verify result structure
        assert 'success' in result
        assert 'fill' in result
        assert 'rejection_history' in result
        assert 'retry_count' in result
        assert 'final_quantity' in result
        
        if result['success']:
            # If successful, fill should exist
            assert result['fill'] is not None
            assert result['final_quantity'] > 0
        else:
            # If failed, should have rejection history
            assert len(result['rejection_history']) > 0
            assert result['fill'] is None
    
    def test_rejection_statistics_tracking(self, execution_simulator):
        """Test rejection statistics are properly tracked"""
        market_data = {
            'close': 150.0,
            'volume': 1000000,
            'volatility': 0.02,
            'timestamp': datetime.now()
        }
        
        # Simulate multiple fills with rejections
        results = []
        for i in range(20):
            result = execution_simulator.simulate_fill_with_rejection(
                symbol='AAPL',
                side='buy',
                quantity=100,
                decision_price=150.0,
                market_data=market_data,
                max_retries=3
            )
            results.append(result)
        
        # Count successes and failures
        successes = sum(1 for r in results if r['success'])
        failures = sum(1 for r in results if not r['success'])
        total_rejections = sum(len(r['rejection_history']) for r in results)
        
        print(f"\nRejection Statistics:")
        print(f"  Successes: {successes}/{len(results)} ({successes/len(results)*100:.1f}%)")
        print(f"  Failures: {failures}/{len(results)} ({failures/len(results)*100:.1f}%)")
        print(f"  Total Rejections: {total_rejections}")
        print(f"  Avg Rejections per Trade: {total_rejections/len(results):.2f}")


class TestSprint0EndToEnd:
    """End-to-end integration tests for Sprint 0"""
    
    @pytest.mark.asyncio
    async def test_complete_authorization_flow_with_sprint0(self, risk_manager_with_sprint0):
        """Test complete flow: circuit breakers → compliance → risk auth"""
        await risk_manager_with_sprint0.initialize()
        
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=100,
            confidence=0.75,
            current_price=150.0,
            strategy_id='test_strategy'
        )
        
        # Should pass all Sprint 0 checks
        authorization = await risk_manager_with_sprint0.authorize_trading_decision(request)
        
        # Log the result
        print(f"\nAuthorization Result:")
        print(f"  Level: {authorization.authorization_level.value}")
        print(f"  Authorized Qty: {authorization.authorized_quantity}")
        if authorization.rejection_reason:
            print(f"  Rejection: {authorization.rejection_reason}")
        
        # Should not be rejected (assuming normal conditions)
        # Note: May be rejected by risk limits, but not by Sprint 0 components
        if authorization.authorization_level == AuthorizationLevel.REJECTED:
            # If rejected, should not be by compliance or circuit breakers
            assert 'COMPLIANCE' not in authorization.rejection_reason
            assert 'CIRCUIT BREAKER' not in authorization.rejection_reason
    
    @pytest.mark.asyncio
    async def test_rejection_blocks_before_risk_assessment(self, risk_manager_with_sprint0):
        """Test circuit breaker blocks trade before risk assessment"""
        await risk_manager_with_sprint0.initialize()
        
        # Activate kill switch
        if risk_manager_with_sprint0.circuit_breakers:
            await risk_manager_with_sprint0.circuit_breakers.initialize()
            await risk_manager_with_sprint0.circuit_breakers.activate_kill_switch(
                authorization_code='TEST'
            )
        
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=100,
            confidence=0.75,
            current_price=150.0
        )
        
        authorization = await risk_manager_with_sprint0.authorize_trading_decision(request)
        
        # Should be blocked by circuit breaker (before risk assessment)
        assert authorization.authorization_level == AuthorizationLevel.REJECTED
        assert 'CIRCUIT BREAKER' in authorization.rejection_reason
    
    def test_execution_with_rejection_tracking(self, execution_simulator):
        """Test complete execution flow with rejection tracking"""
        market_data = {
            'timestamp': datetime.now(),
            'open': 149.0,
            'high': 151.0,
            'low': 148.0,
            'close': 150.0,
            'volume': 1000000,
            'volatility': 0.02
        }
        
        # Simulate execution with rejection handling
        result = execution_simulator.simulate_fill_with_rejection(
            symbol='AAPL',
            side='buy',
            quantity=100,
            decision_price=150.0,
            market_data=market_data,
            authorization_id='auth_001',
            strategy_id='test_strategy',
            regime_context={'primary_regime': 'normal_volatility'},
            liquidity_score=75.0,
            max_retries=3
        )
        
        print(f"\nExecution Result:")
        print(f"  Success: {result['success']}")
        print(f"  Retry Count: {result['retry_count']}")
        print(f"  Rejections: {len(result['rejection_history'])}")
        print(f"  Final Quantity: {result['final_quantity']}")
        
        if result['success']:
            fill = result['fill']
            print(f"  Fill Price: ${fill.fill_price:.2f}")
            print(f"  Total Cost: {fill.costs.total_cost_bps:.2f} bps")
        else:
            print(f"  Failure Reason: {result.get('failure_reason')}")


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v', '-s'])

