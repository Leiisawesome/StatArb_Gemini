"""
Unit Tests for OrderRejectionHandler
Tests intelligent retry logic for all 8 rejection patterns

Test Coverage:
1. Insufficient Margin → Reduce quantity
2. Stock Halted → Wait and retry
3. Price Collar → Adjust price
4. Connection Timeout → Exponential backoff
5. Duplicate Order ID → New ID
6. Market Closed → Cancel
7. Position Limit → Escalate
8. Unknown Error → Escalate
"""

import pytest
from core_engine.system.order_rejection_handler import (
    OrderRejectionHandler,
    RejectionReason,
    RetryAction
)


class TestOrderRejectionHandler:
    """Test suite for OrderRejectionHandler"""

    @pytest.fixture
    def handler(self):
        """Create rejection handler instance"""
        config = {
            'max_retries': 3,
            'backoff_base_seconds': 5,
            'quantity_reduction_factor': 0.5,
            'price_adjustment_bps': 10
        }
        return OrderRejectionHandler(config)

    @pytest.fixture
    def sample_order(self):
        """Create sample order"""
        return {
            'order_id': 'order_123',
            'symbol': 'AAPL',
            'side': 'buy',
            'quantity': 100.0,
            'price': 150.0
        }

    # Pattern 1: Insufficient Margin
    @pytest.mark.asyncio
    async def test_insufficient_margin_reduces_quantity(self, handler, sample_order):
        """Test insufficient margin triggers quantity reduction"""
        resolution = await handler.handle_rejection(
            sample_order,
            "Insufficient buying power to complete order"
        )

        assert resolution.action == RetryAction.RETRY_REDUCED_QUANTITY
        assert resolution.modified_order['quantity'] == 50.0  # 50% reduction
        assert resolution.wait_seconds == 0  # Immediate retry
        assert handler.rejections_by_reason[RejectionReason.INSUFFICIENT_MARGIN] == 1

    # Pattern 2: Stock Halted
    @pytest.mark.asyncio
    async def test_stock_halted_waits_and_retries(self, handler, sample_order):
        """Test stock halted triggers wait and retry"""
        resolution = await handler.handle_rejection(
            sample_order,
            "Stock trading is currently halted"
        )

        assert resolution.action == RetryAction.WAIT_AND_RETRY
        assert resolution.wait_seconds == 30
        assert resolution.modified_order['quantity'] == sample_order['quantity']  # No change
        assert handler.rejections_by_reason[RejectionReason.STOCK_HALTED] == 1

    # Pattern 3: Price Collar
    @pytest.mark.asyncio
    async def test_price_collar_adjusts_price(self, handler, sample_order):
        """Test price collar violation adjusts price"""
        resolution = await handler.handle_rejection(
            sample_order,
            "Order price violates limit up collar"
        )

        assert resolution.action == RetryAction.RETRY_ADJUSTED_PRICE
        # For buy, price should be reduced
        assert resolution.modified_order['price'] < sample_order['price']
        assert resolution.modified_order['price'] == pytest.approx(149.85, abs=0.01)  # -10 bps
        assert handler.rejections_by_reason[RejectionReason.PRICE_COLLAR] == 1

    @pytest.mark.asyncio
    async def test_price_collar_sell_increases_price(self, handler):
        """Test price collar for sell order increases price"""
        sell_order = {
            'order_id': 'order_124',
            'symbol': 'AAPL',
            'side': 'sell',
            'quantity': 100.0,
            'price': 150.0
        }

        resolution = await handler.handle_rejection(
            sell_order,
            "Order price violates limit down collar"
        )

        assert resolution.action == RetryAction.RETRY_ADJUSTED_PRICE
        # For sell, price should be increased
        assert resolution.modified_order['price'] > sell_order['price']
        assert resolution.modified_order['price'] == pytest.approx(150.15, abs=0.01)  # +10 bps

    # Pattern 4: Connection Timeout
    @pytest.mark.asyncio
    async def test_connection_timeout_exponential_backoff(self, handler, sample_order):
        """Test connection timeout uses exponential backoff"""
        # First retry
        resolution1 = await handler.handle_rejection(
            sample_order,
            "Connection timeout to broker"
        )

        assert resolution1.action == RetryAction.RETRY_WITH_BACKOFF
        assert resolution1.wait_seconds == 5  # 5 * 2^0 = 5

        # Second retry (simulate)
        handler.active_retries[sample_order['order_id']].retry_count = 1
        resolution2 = await handler.handle_rejection(
            sample_order,
            "Connection timeout to broker"
        )

        assert resolution2.wait_seconds == 10  # 5 * 2^1 = 10

        # Third retry
        handler.active_retries[sample_order['order_id']].retry_count = 2
        resolution3 = await handler.handle_rejection(
            sample_order,
            "Connection timeout to broker"
        )

        assert resolution3.wait_seconds == 20  # 5 * 2^2 = 20

    # Pattern 5: Duplicate Order ID
    @pytest.mark.asyncio
    async def test_duplicate_order_id_generates_new_id(self, handler, sample_order):
        """Test duplicate order ID generates new ID"""
        resolution = await handler.handle_rejection(
            sample_order,
            "Order ID already exists in system"
        )

        assert resolution.action == RetryAction.RETRY_NEW_ORDER_ID
        assert resolution.modified_order['order_id'] != sample_order['order_id']
        assert sample_order['order_id'] in resolution.modified_order['order_id']  # Contains original
        assert resolution.wait_seconds == 0  # Immediate retry

    # Pattern 6: Market Closed
    @pytest.mark.asyncio
    async def test_market_closed_cancels_order(self, handler, sample_order):
        """Test market closed cancels order"""
        resolution = await handler.handle_rejection(
            sample_order,
            "Market is closed - outside trading hours"
        )

        assert resolution.action == RetryAction.CANCEL_ORDER
        assert resolution.modified_order is None
        assert "cancelled" in resolution.reason.lower()
        assert handler.rejections_by_reason[RejectionReason.MARKET_CLOSED] == 1

    # Pattern 7: Position Limit
    @pytest.mark.asyncio
    async def test_position_limit_escalates(self, handler, sample_order):
        """Test position limit triggers escalation"""
        resolution = await handler.handle_rejection(
            sample_order,
            "Maximum position size limit reached"
        )

        assert resolution.action == RetryAction.ESCALATE
        assert resolution.escalate_immediately is True
        assert resolution.modified_order is None
        assert handler.rejections_by_reason[RejectionReason.POSITION_LIMIT] == 1

    # Pattern 8: Unknown Error
    @pytest.mark.asyncio
    async def test_unknown_error_escalates(self, handler, sample_order):
        """Test unknown error triggers escalation"""
        resolution = await handler.handle_rejection(
            sample_order,
            "Some weird error that doesn't match any pattern"
        )

        assert resolution.action == RetryAction.ESCALATE
        assert resolution.escalate_immediately is True
        assert handler.rejections_by_reason[RejectionReason.UNKNOWN] == 1

    # Max Retries
    @pytest.mark.asyncio
    async def test_max_retries_escalates(self, handler, sample_order):
        """Test that max retries triggers escalation"""
        # Simulate 3 retries
        for i in range(3):
            await handler.handle_rejection(
                sample_order,
                "Insufficient margin"
            )
            handler.active_retries[sample_order['order_id']].retry_count = i + 1

        # 4th attempt should escalate
        resolution = await handler.handle_rejection(
            sample_order,
            "Insufficient margin"
        )

        assert resolution.action == RetryAction.ESCALATE
        assert "Max retries" in resolution.reason
        assert handler.escalations == 1

    # Retry Outcome Tracking
    def test_record_successful_retry(self, handler, sample_order):
        """Test recording successful retry outcome"""
        handler.record_retry_outcome(sample_order['order_id'], success=True)

        assert handler.successful_retries == 1
        assert handler.total_retries == 1

    def test_record_failed_retry(self, handler, sample_order):
        """Test recording failed retry outcome"""
        handler.record_retry_outcome(sample_order['order_id'], success=False)

        assert handler.failed_retries == 1
        assert handler.total_retries == 1

    # Statistics
    @pytest.mark.asyncio
    async def test_statistics_tracking(self, handler, sample_order):
        """Test statistics are tracked correctly"""
        # Generate some rejections
        await handler.handle_rejection(sample_order, "Insufficient margin")
        await handler.handle_rejection(sample_order, "Stock halted")
        await handler.handle_rejection(sample_order, "Connection timeout")

        stats = handler.get_rejection_statistics()

        assert stats['total_rejections'] == 3
        assert len(stats['rejections_by_reason']) >= 3
        assert 'insufficient_margin' in stats['rejections_by_reason']
        assert 'stock_halted' in stats['rejections_by_reason']
        assert 'connection_timeout' in stats['rejections_by_reason']

    def test_report_generation(self, handler):
        """Test rejection report generation"""
        report = handler.generate_rejection_report()

        assert 'ORDER REJECTION HANDLER REPORT' in report
        assert 'Total Rejections' in report
        assert 'Retry Success Rate' in report

    # Pattern Recognition
    def test_rejection_classification(self, handler):
        """Test rejection reason classification"""
        test_cases = [
            ("Insufficient buying power", RejectionReason.INSUFFICIENT_MARGIN),
            ("Trading halted", RejectionReason.STOCK_HALTED),
            ("Price collar violation", RejectionReason.PRICE_COLLAR),
            ("Connection timed out", RejectionReason.CONNECTION_TIMEOUT),
            ("Duplicate order ID", RejectionReason.DUPLICATE_ORDER_ID),
            ("Market closed", RejectionReason.MARKET_CLOSED),
            ("Position limit exceeded", RejectionReason.POSITION_LIMIT),
            ("Random error message", RejectionReason.UNKNOWN)
        ]

        for message, expected_reason in test_cases:
            classified = handler._classify_rejection(message)
            assert classified == expected_reason, f"Failed for: {message}"

    # Multiple Rejections Same Order
    @pytest.mark.asyncio
    async def test_multiple_rejections_increment_retry_count(self, handler, sample_order):
        """Test that multiple rejections increment retry count"""
        # First rejection
        await handler.handle_rejection(sample_order, "Insufficient margin")
        assert handler._get_retry_count(sample_order['order_id']) == 1

        # Second rejection
        await handler.handle_rejection(sample_order, "Insufficient margin")
        assert handler._get_retry_count(sample_order['order_id']) == 2

        # Third rejection
        await handler.handle_rejection(sample_order, "Insufficient margin")
        assert handler._get_retry_count(sample_order['order_id']) == 3


# Integration Test
class TestRejectionHandlerIntegration:
    """Integration tests for rejection handler"""

    @pytest.mark.asyncio
    async def test_full_retry_workflow(self):
        """Test complete retry workflow"""
        handler = OrderRejectionHandler({
            'max_retries': 3,
            'quantity_reduction_factor': 0.5
        })

        order = {
            'order_id': 'order_999',
            'symbol': 'TEST',
            'side': 'buy',
            'quantity': 1000.0,
            'price': 100.0
        }

        # Attempt 1: Insufficient margin
        resolution1 = await handler.handle_rejection(
            order,
            "Insufficient buying power"
        )

        assert resolution1.action == RetryAction.RETRY_REDUCED_QUANTITY
        assert resolution1.modified_order['quantity'] == 500.0

        # Simulate retry with reduced quantity
        order['quantity'] = resolution1.modified_order['quantity']

        # Attempt 2: Still insufficient (edge case)
        resolution2 = await handler.handle_rejection(
            order,
            "Insufficient buying power"
        )

        assert resolution2.modified_order['quantity'] == 250.0  # Further reduced

        # Record successful retry
        handler.record_retry_outcome(order['order_id'], success=True)

        # Check statistics
        stats = handler.get_rejection_statistics()
        assert stats['total_rejections'] == 2
        assert stats['successful_retries'] == 1
        assert stats['retry_success_rate'] == 1.0

    @pytest.mark.asyncio
    async def test_mixed_rejection_patterns(self):
        """Test handling multiple different rejection patterns"""
        handler = OrderRejectionHandler()

        scenarios = [
            {
                'order': {'order_id': 'o1', 'symbol': 'A', 'side': 'buy', 'quantity': 100, 'price': 50},
                'message': "Insufficient margin",
                'expected_action': RetryAction.RETRY_REDUCED_QUANTITY
            },
            {
                'order': {'order_id': 'o2', 'symbol': 'B', 'side': 'buy', 'quantity': 200, 'price': 75},
                'message': "Stock halted",
                'expected_action': RetryAction.WAIT_AND_RETRY
            },
            {
                'order': {'order_id': 'o3', 'symbol': 'C', 'side': 'sell', 'quantity': 50, 'price': 120},
                'message': "Market closed",
                'expected_action': RetryAction.CANCEL_ORDER
            }
        ]

        for scenario in scenarios:
            resolution = await handler.handle_rejection(
                scenario['order'],
                scenario['message']
            )

            assert resolution.action == scenario['expected_action'], \
                f"Failed for {scenario['message']}"

        # Verify all tracked
        assert handler.total_rejections == 3
        assert len(handler.rejection_history) == 3


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v', '--tb=short'])

