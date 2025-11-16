"""
Unit tests for partial fill simulation

Tests the realistic partial fill mechanism that simulates order execution
based on order size relative to market conditions.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from core_engine.system.unified_execution_engine import (
    MarketAlgorithm,
    ExecutionRequest,
    ExecutionStatus,
    ExecutionAlgorithm,
    ExecutionUrgency
)
from core_engine.system.central_risk_manager import ExecutionAuthorization


class TestPartialFillSimulation:
    """Test partial fill simulation based on order size"""
    
    def setup_method(self):
        """Set up test fixtures"""
        config = {
            'test_mode': True,
            'default_slippage_bps': 5.0
        }
        self.market_algo = MarketAlgorithm(config=config)
        self.market_algo.test_mode = True
    
    @pytest.mark.asyncio
    async def test_small_order_high_fill_rate(self):
        """
        Test that small orders (<$10k) have high fill rates (99-100%)
        
        Small orders should execute with minimal partial fills
        """
        print("\n=== Test: Small Order High Fill Rate ===")
        
        # Create authorization for small order: 50 shares @ $100 = $5,000
        auth = ExecutionAuthorization(
            authorization_id="test_small_001",
            symbol="TSLA",
            side="BUY",
            quantity=50.0,
            price_limit=None
        )
        
        # Create execution request with partial fill simulation enabled
        request = ExecutionRequest(
            authorization=auth,
            algorithm=ExecutionAlgorithm.MARKET,
            urgency=ExecutionUrgency.NORMAL,
            time_horizon=300,
            algorithm_params={
                'current_price': 100.0,
                'simulate_partial_fills': True  # Enable partial fill simulation
            }
        )
        
        # Execute
        result = await self.market_algo.execute(request)
        
        # Verify execution
        assert result.status in [ExecutionStatus.FILLED, ExecutionStatus.PARTIALLY_FILLED]
        assert result.filled_quantity > 0
        assert result.filled_quantity <= 50.0
        
        fill_rate = result.filled_quantity / 50.0
        print(f"Order: 50 shares @ $100 = $5,000")
        print(f"Filled: {result.filled_quantity:.2f} shares ({fill_rate*100:.1f}%)")
        print(f"Remaining: {result.remaining_quantity:.2f} shares")
        print(f"Status: {result.status}")
        
        # Small orders should have 99-100% fill rate
        assert fill_rate >= 0.99, f"Expected fill rate ≥99% for small order, got {fill_rate*100:.1f}%"
        assert fill_rate <= 1.0
    
    @pytest.mark.asyncio
    async def test_medium_order_moderate_fill_rate(self):
        """
        Test that medium orders ($10k-$50k) have moderate fill rates (97-99%)
        
        Medium orders should have slightly more partial fills
        """
        print("\n=== Test: Medium Order Moderate Fill Rate ===")
        
        # Create authorization for medium order: 300 shares @ $100 = $30,000
        auth = ExecutionAuthorization(
            authorization_id="test_medium_001",
            symbol="TSLA",
            side="SELL",
            quantity=300.0,
            price_limit=None
        )
        
        request = ExecutionRequest(
            authorization=auth,
            algorithm=ExecutionAlgorithm.MARKET,
            urgency=ExecutionUrgency.NORMAL,
            time_horizon=300,
            algorithm_params={
                'current_price': 100.0,
                'simulate_partial_fills': True
            }
        )
        
        result = await self.market_algo.execute(request)
        
        fill_rate = result.filled_quantity / 300.0
        print(f"Order: 300 shares @ $100 = $30,000")
        print(f"Filled: {result.filled_quantity:.2f} shares ({fill_rate*100:.1f}%)")
        print(f"Remaining: {result.remaining_quantity:.2f} shares")
        print(f"Status: {result.status}")
        
        # Medium orders should have 97-99% fill rate
        assert fill_rate >= 0.97, f"Expected fill rate ≥97% for medium order, got {fill_rate*100:.1f}%"
        assert fill_rate < 1.0, "Medium order should have some partial fill"
    
    @pytest.mark.asyncio
    async def test_large_order_lower_fill_rate(self):
        """
        Test that large orders ($50k-$100k) have lower fill rates (95-97%)
        
        Large orders face more liquidity constraints
        """
        print("\n=== Test: Large Order Lower Fill Rate ===")
        
        # Create authorization for large order: 800 shares @ $100 = $80,000
        auth = ExecutionAuthorization(
            authorization_id="test_large_001",
            symbol="TSLA",
            side="BUY",
            quantity=800.0,
            price_limit=None
        )
        
        request = ExecutionRequest(
            authorization=auth,
            algorithm=ExecutionAlgorithm.MARKET,
            urgency=ExecutionUrgency.NORMAL,
            time_horizon=300,
            algorithm_params={
                'current_price': 100.0,
                'simulate_partial_fills': True
            }
        )
        
        result = await self.market_algo.execute(request)
        
        fill_rate = result.filled_quantity / 800.0
        print(f"Order: 800 shares @ $100 = $80,000")
        print(f"Filled: {result.filled_quantity:.2f} shares ({fill_rate*100:.1f}%)")
        print(f"Remaining: {result.remaining_quantity:.2f} shares")
        print(f"Status: {result.status}")
        
        # Large orders should have 95-97% fill rate
        assert fill_rate >= 0.95, f"Expected fill rate ≥95% for large order, got {fill_rate*100:.1f}%"
        assert fill_rate < 0.99, f"Expected fill rate <99% for large order, got {fill_rate*100:.1f}%"
        assert result.status == ExecutionStatus.PARTIALLY_FILLED, "Large order should be PARTIALLY_FILLED"
    
    @pytest.mark.asyncio
    async def test_very_large_order_lowest_fill_rate(self):
        """
        Test that very large orders (>$100k) have lowest fill rates (90-95%)
        
        Institutional-size orders face significant liquidity constraints
        """
        print("\n=== Test: Very Large Order Lowest Fill Rate ===")
        
        # Create authorization for very large order: 1500 shares @ $100 = $150,000
        auth = ExecutionAuthorization(
            authorization_id="test_xlarge_001",
            symbol="TSLA",
            side="SELL",
            quantity=1500.0,
            price_limit=None
        )
        
        request = ExecutionRequest(
            authorization=auth,
            algorithm=ExecutionAlgorithm.MARKET,
            urgency=ExecutionUrgency.NORMAL,
            time_horizon=300,
            algorithm_params={
                'current_price': 100.0,
                'simulate_partial_fills': True
            }
        )
        
        result = await self.market_algo.execute(request)
        
        fill_rate = result.filled_quantity / 1500.0
        print(f"Order: 1500 shares @ $100 = $150,000")
        print(f"Filled: {result.filled_quantity:.2f} shares ({fill_rate*100:.1f}%)")
        print(f"Remaining: {result.remaining_quantity:.2f} shares")
        print(f"Status: {result.status}")
        
        # Very large orders should have 90-95% fill rate
        assert fill_rate >= 0.90, f"Expected fill rate ≥90% for very large order, got {fill_rate*100:.1f}%"
        assert fill_rate < 0.97, f"Expected fill rate <97% for very large order, got {fill_rate*100:.1f}%"
        assert result.status == ExecutionStatus.PARTIALLY_FILLED, "Very large order should be PARTIALLY_FILLED"
    
    @pytest.mark.asyncio
    async def test_disabled_partial_fills(self):
        """
        Test that partial fills are disabled when flag is not set
        
        Without simulate_partial_fills flag, orders should fill 100%
        """
        print("\n=== Test: Disabled Partial Fills ===")
        
        # Large order without partial fill simulation
        auth = ExecutionAuthorization(
            authorization_id="test_disabled_001",
            symbol="TSLA",
            side="BUY",
            quantity=1000.0,
            price_limit=None
        )
        
        request = ExecutionRequest(
            authorization=auth,
            algorithm=ExecutionAlgorithm.MARKET,
            urgency=ExecutionUrgency.NORMAL,
            time_horizon=300,
            algorithm_params={
                'current_price': 100.0
                # Note: No 'simulate_partial_fills' flag
            }
        )
        
        result = await self.market_algo.execute(request)
        
        print(f"Order: 1000 shares @ $100 = $100,000")
        print(f"Filled: {result.filled_quantity:.2f} shares")
        print(f"Status: {result.status}")
        
        # Should fill 100% without partial fill simulation
        assert result.filled_quantity == 1000.0, "Without simulation flag, should fill 100%"
        assert result.remaining_quantity == 0.0
        assert result.status == ExecutionStatus.FILLED
    
    @pytest.mark.asyncio
    async def test_multiple_executions_deterministic(self):
        """
        Test that partial fills are deterministic based on timestamp
        
        Same order at same timestamp should produce same fill rate
        """
        print("\n=== Test: Deterministic Partial Fills ===")
        
        # Use fixed timestamp for deterministic testing
        test_timestamp = datetime(2024, 11, 6, 10, 0, 0, tzinfo=timezone.utc)
        
        # Execute same order twice with same authorization time
        results = []
        for i in range(2):
            auth = ExecutionAuthorization(
                authorization_id=f"test_det_{i:03d}",
                symbol="TSLA",
                side="BUY",
                quantity=500.0,
                price_limit=None,
                authorized_at=test_timestamp  # Same authorization time
            )
            
            request = ExecutionRequest(
                authorization=auth,
                algorithm=ExecutionAlgorithm.MARKET,
                urgency=ExecutionUrgency.NORMAL,
                time_horizon=300,
                algorithm_params={
                    'current_price': 100.0,
                    'simulate_partial_fills': True
                }
            )
            
            result = await self.market_algo.execute(request)
            results.append(result)
            print(f"Execution {i+1}: {result.filled_quantity:.2f}/{500.0:.2f} shares ({result.filled_quantity/500.0*100:.1f}%)")
        
        # Both executions should have same fill rate (deterministic)
        assert abs(results[0].filled_quantity - results[1].filled_quantity) < 0.01, \
            "Same timestamp should produce same fill rate"


if __name__ == '__main__':
    # Run tests with verbose output
    pytest.main([__file__, '-v', '-s'])
