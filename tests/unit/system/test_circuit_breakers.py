"""
Unit Tests for TradingCircuitBreakers
Tests all 5 circuit breaker mechanisms with various scenarios

Test Coverage:
1. Manual Kill Switch
2. Order Rate Limiting
3. Daily Loss Limit
4. Drawdown from High
5. Position Concentration
"""

import pytest
import asyncio
from core_engine.system.circuit_breakers import (
    TradingCircuitBreakers,
    CircuitBreakerConfig,
    CircuitBreakerLevel,
    CircuitBreakerType
)

class TestTradingCircuitBreakers:
    """Test suite for TradingCircuitBreakers"""

    @pytest.fixture
    def circuit_breakers(self):
        """Create circuit breakers instance for testing"""
        config = CircuitBreakerConfig(
            max_orders_per_second=10,
            max_orders_per_minute=100,
            daily_loss_limit_pct=-0.02,  # -2%
            max_drawdown_from_high_pct=-0.05,  # -5%
            max_position_concentration=0.20  # 20%
        )
        return TradingCircuitBreakers(config)

    @pytest.mark.asyncio
    async def test_normal_operation_passes(self, circuit_breakers):
        """Test that normal operation passes all checks"""
        status = await circuit_breakers.check_circuit_breakers(
            portfolio_value=100000.0
        )

        assert status.level == CircuitBreakerLevel.NORMAL
        assert status.can_trade is True
        assert len(status.triggered_breakers) == 0

    @pytest.mark.asyncio
    async def test_manual_kill_switch_activation(self, circuit_breakers):
        """Test manual kill switch activation"""
        # Activate kill switch
        success = circuit_breakers.activate_kill_switch(
            user="risk_manager",
            authorization_code="EMERGENCY_OVERRIDE_2025"
        )

        assert success is True
        assert circuit_breakers.kill_switch_active is True
        assert circuit_breakers.can_trade is False

        # Check circuit breakers - should be halted
        status = await circuit_breakers.check_circuit_breakers()

        assert status.level == CircuitBreakerLevel.HALT
        assert status.can_trade is False
        assert CircuitBreakerType.MANUAL_KILL_SWITCH in status.triggered_breakers
        assert "kill switch" in status.halt_reason.lower()

    @pytest.mark.asyncio
    async def test_kill_switch_invalid_code(self, circuit_breakers):
        """Test that invalid authorization code fails"""
        success = circuit_breakers.activate_kill_switch(
            user="unauthorized_user",
            authorization_code="WRONG_CODE"
        )

        assert success is False
        assert circuit_breakers.kill_switch_active is False
        assert circuit_breakers.can_trade is True

    @pytest.mark.asyncio
    async def test_kill_switch_deactivation(self, circuit_breakers):
        """Test kill switch deactivation"""
        # Activate
        circuit_breakers.activate_kill_switch(
            user="risk_manager",
            authorization_code="EMERGENCY_OVERRIDE_2025"
        )

        # Deactivate
        success = circuit_breakers.deactivate_kill_switch(
            user="risk_manager",
            authorization_code="EMERGENCY_OVERRIDE_2025"
        )

        assert success is True
        assert circuit_breakers.kill_switch_active is False
        assert circuit_breakers.can_trade is True

    @pytest.mark.asyncio
    async def test_order_rate_limit_per_second(self, circuit_breakers):
        """Test order rate limiting (per second)"""
        # Record 10 orders (at limit)
        for _ in range(10):
            circuit_breakers.record_order_attempt()

        # 11th order should trigger halt
        circuit_breakers.record_order_attempt()

        status = await circuit_breakers.check_circuit_breakers()

        assert status.can_trade is False
        assert CircuitBreakerType.ORDER_RATE_LIMIT in status.triggered_breakers
        assert "rate limit" in status.halt_reason.lower()

    @pytest.mark.asyncio
    async def test_order_rate_warning_threshold(self, circuit_breakers):
        """Test order rate warning at 80% threshold"""
        # Record 8 orders (80% of 10 limit)
        for _ in range(8):
            circuit_breakers.record_order_attempt()

        status = await circuit_breakers.check_circuit_breakers()

        assert status.can_trade is True
        assert status.level == CircuitBreakerLevel.WARNING
        assert len(status.warnings) > 0
        assert "rate limit" in status.warnings[0].lower()

    @pytest.mark.asyncio
    async def test_daily_loss_limit_breached(self, circuit_breakers):
        """Test daily loss limit breach"""
        # Set portfolio start value
        await circuit_breakers.check_circuit_breakers(portfolio_value=100000.0)

        # Simulate 3% loss (exceeds -2% limit)
        await asyncio.sleep(0.1)  # Small delay
        status = await circuit_breakers.check_circuit_breakers(portfolio_value=97000.0)

        assert status.can_trade is False
        assert CircuitBreakerType.DAILY_LOSS_LIMIT in status.triggered_breakers
        assert "loss limit" in status.halt_reason.lower()

    @pytest.mark.asyncio
    async def test_daily_loss_warning_threshold(self, circuit_breakers):
        """Test daily loss warning at 80% of limit"""
        # Set portfolio start value
        await circuit_breakers.check_circuit_breakers(portfolio_value=100000.0)

        # Simulate 1.6% loss (80% of -2% limit)
        await asyncio.sleep(0.1)
        status = await circuit_breakers.check_circuit_breakers(portfolio_value=98400.0)

        assert status.can_trade is True
        assert status.level == CircuitBreakerLevel.WARNING
        assert any("loss limit" in w.lower() for w in status.warnings)

    @pytest.mark.asyncio
    async def test_drawdown_limit_breached(self, circuit_breakers):
        """Test drawdown from high limit breach"""
        # Set initial high
        await circuit_breakers.check_circuit_breakers(portfolio_value=100000.0)

        # Increase to new high
        await asyncio.sleep(0.1)
        await circuit_breakers.check_circuit_breakers(portfolio_value=110000.0)

        # Drop 6% from high (exceeds -5% limit)
        await asyncio.sleep(0.1)
        status = await circuit_breakers.check_circuit_breakers(portfolio_value=103400.0)

        assert status.can_trade is False
        assert CircuitBreakerType.DRAWDOWN_LIMIT in status.triggered_breakers
        assert "drawdown" in status.halt_reason.lower()

    @pytest.mark.asyncio
    async def test_drawdown_warning_threshold(self, circuit_breakers):
        """Test drawdown warning at 80% of limit"""
        # Set initial high
        await circuit_breakers.check_circuit_breakers(portfolio_value=100000.0)

        # Increase to new high
        await asyncio.sleep(0.1)
        await circuit_breakers.check_circuit_breakers(portfolio_value=110000.0)

        # Drop 4% from high (80% of -5% limit)
        await asyncio.sleep(0.1)
        status = await circuit_breakers.check_circuit_breakers(portfolio_value=105600.0)

        assert status.can_trade is True
        assert status.level == CircuitBreakerLevel.WARNING
        assert any("drawdown" in w.lower() for w in status.warnings)

    @pytest.mark.asyncio
    async def test_position_concentration_breached(self, circuit_breakers):
        """Test position concentration limit breach"""
        # 25% position (exceeds 20% limit)
        status = await circuit_breakers.check_circuit_breakers(
            portfolio_value=100000.0,
            symbol='CONCENTRATED_STOCK',
            position_value=25000.0
        )

        assert status.can_trade is False
        assert CircuitBreakerType.POSITION_CONCENTRATION in status.triggered_breakers
        assert "concentration" in status.halt_reason.lower()

    @pytest.mark.asyncio
    async def test_position_concentration_passes(self, circuit_breakers):
        """Test position concentration within limits"""
        # 15% position (within 20% limit)
        status = await circuit_breakers.check_circuit_breakers(
            portfolio_value=100000.0,
            symbol='NORMAL_STOCK',
            position_value=15000.0
        )

        assert status.can_trade is True
        assert len(status.triggered_breakers) == 0

    @pytest.mark.asyncio
    async def test_daily_reset(self, circuit_breakers):
        """Test daily reset functionality"""
        # Set initial values
        await circuit_breakers.check_circuit_breakers(portfolio_value=100000.0)

        # Simulate loss
        await circuit_breakers.check_circuit_breakers(portfolio_value=98000.0)

        assert circuit_breakers.daily_pnl < 0
        assert circuit_breakers.daily_pnl_pct < 0

        # Perform daily reset
        await circuit_breakers.daily_reset()

        assert circuit_breakers.daily_pnl == 0.0
        assert circuit_breakers.daily_pnl_pct == 0.0
        assert circuit_breakers.intraday_high_value == 98000.0  # Reset to current

    @pytest.mark.asyncio
    async def test_multiple_warnings_accumulated(self, circuit_breakers):
        """Test that multiple warnings are accumulated"""
        # Set portfolio start value
        await circuit_breakers.check_circuit_breakers(portfolio_value=100000.0)

        # Record orders near rate limit
        for _ in range(8):
            circuit_breakers.record_order_attempt()

        # Simulate loss near limit
        status = await circuit_breakers.check_circuit_breakers(
            portfolio_value=98400.0,  # 1.6% loss (near -2% limit)
            symbol='WARN_STOCK',
            position_value=17000.0  # 17% concentration (near 20% limit)
        )

        assert status.can_trade is True
        assert status.level == CircuitBreakerLevel.WARNING
        # Should have multiple warnings
        assert len(status.warnings) >= 2

    def test_statistics_tracking(self, circuit_breakers):
        """Test statistics tracking"""
        stats = circuit_breakers.get_circuit_breaker_statistics()

        assert 'total_checks' in stats
        assert 'halts_triggered' in stats
        assert 'warnings_issued' in stats
        assert 'current_level' in stats
        assert 'can_trade' in stats

    def test_report_generation(self, circuit_breakers):
        """Test circuit breaker report generation"""
        report = circuit_breakers.generate_circuit_breaker_report()

        assert 'CIRCUIT BREAKER REPORT' in report
        assert 'Current Level' in report
        assert 'Trading Enabled' in report
        assert 'Kill Switch' in report

    @pytest.mark.asyncio
    async def test_halt_records_history(self, circuit_breakers):
        """Test that halts are recorded in history"""
        initial_history_count = len(circuit_breakers.breaker_history)

        # Trigger a halt
        circuit_breakers.activate_kill_switch(
            user="test_user",
            authorization_code="EMERGENCY_OVERRIDE_2025"
        )

        await circuit_breakers.check_circuit_breakers()

        assert len(circuit_breakers.breaker_history) > initial_history_count
        assert circuit_breakers.halts_triggered > 0

# Integration Test
class TestCircuitBreakerIntegration:
    """Integration tests for circuit breakers"""

    @pytest.mark.asyncio
    async def test_full_trading_day_simulation(self):
        """Test complete trading day scenario"""
        # Initialize
        breakers = TradingCircuitBreakers(CircuitBreakerConfig(
            max_orders_per_second=10,
            daily_loss_limit_pct=-0.02,
            max_drawdown_from_high_pct=-0.05
        ))

        # Morning: Portfolio starts at $100K
        status = await breakers.check_circuit_breakers(portfolio_value=100000.0)
        assert status.can_trade is True

        # Mid-morning: Profit to $105K (new high)
        await asyncio.sleep(0.1)
        status = await breakers.check_circuit_breakers(portfolio_value=105000.0)
        assert status.can_trade is True
        assert breakers.intraday_high_value == 105000.0

        # Afternoon: Drop to $100K (4.76% drawdown - within -5% limit)
        await asyncio.sleep(0.1)
        status = await breakers.check_circuit_breakers(portfolio_value=100000.0)
        assert status.can_trade is True
        assert status.level == CircuitBreakerLevel.WARNING  # Warning issued

        # Late afternoon: Recovery to $102K
        await asyncio.sleep(0.1)
        status = await breakers.check_circuit_breakers(portfolio_value=102000.0)
        assert status.can_trade is True

        # Verify daily stats
        stats = breakers.get_circuit_breaker_statistics()
        assert stats['daily_pnl_pct'] == 0.02  # +2% from start
        assert stats['can_trade'] is True

    @pytest.mark.asyncio
    async def test_emergency_halt_scenario(self):
        """Test emergency halt scenario"""
        # Initialize
        breakers = TradingCircuitBreakers(CircuitBreakerConfig(
            daily_loss_limit_pct=-0.02,
            cancel_pending_orders_on_halt=True
        ))

        # Normal operation
        status = await breakers.check_circuit_breakers(portfolio_value=100000.0)
        assert status.can_trade is True

        # Flash crash: 3% loss
        await asyncio.sleep(0.1)
        status = await breakers.check_circuit_breakers(portfolio_value=97000.0)

        # Should halt trading
        assert status.can_trade is False
        assert status.level == CircuitBreakerLevel.HALT
        assert CircuitBreakerType.DAILY_LOSS_LIMIT in status.triggered_breakers

        # Verify halt recorded
        stats = breakers.get_circuit_breaker_statistics()
        assert stats['halts_triggered'] == 1
        assert not stats['can_trade']

    @pytest.mark.asyncio
    async def test_cascading_breakers(self):
        """Test that first breaker to trigger causes halt"""
        # Initialize
        breakers = TradingCircuitBreakers(CircuitBreakerConfig(
            max_orders_per_second=5,
            daily_loss_limit_pct=-0.02,
            max_position_concentration=0.10
        ))

        # Set up for multiple potential breaches
        await breakers.check_circuit_breakers(portfolio_value=100000.0)

        # Record orders near limit
        for _ in range(5):
            breakers.record_order_attempt()

        # One more order triggers rate limit halt (first breaker)
        breakers.record_order_attempt()

        # Check with loss and concentration (would also breach, but rate limit hits first)
        status = await breakers.check_circuit_breakers(
            portfolio_value=97000.0,  # 3% loss
            symbol='CONC_STOCK',
            position_value=15000.0  # 15% concentration (exceeds 10% limit)
        )

        # Should halt on FIRST breaker (order rate)
        assert status.can_trade is False
        assert CircuitBreakerType.ORDER_RATE_LIMIT in status.triggered_breakers

if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v', '--tb=short'])

