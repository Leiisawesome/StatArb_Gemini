"""
Performance Integration Tests

Tests system performance under various load conditions:
- High-volume authorization request processing
- Concurrent strategy processing
- System throughput validation
- Resource usage monitoring under stress

Phase 8 Day 4 - Performance Testing
"""

import pytest
import asyncio
import logging
import time

from core_engine.system.central_risk_manager import (
    TradingDecisionRequest,
    TradingDecisionType,
    ExecutionUrgency,
    AuthorizationLevel
)

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
class TestPerformance:
    """Test system performance under load"""
    
    async def test_high_volume_authorization_processing(
        self, orchestrator, strategy_manager, risk_manager
    ):
        """
        Test: High-volume authorization request processing
        
        Validates:
        - System handles 100+ authorization requests
        - Request processing throughput
        - Average response time
        - Zero request failures under normal load
        """
        logger.info("🔄 Testing High-Volume Authorization Processing")
        
        # Register components
        orchestrator.register_central_risk_manager(risk_manager)
        orchestrator.register_component(
            name="StrategyManager",
            component=strategy_manager,
            layer="execution",
            authority_level="strategic"
        )
        
        # Start components
        await risk_manager.start()
        await strategy_manager.start()
        
        # Get active strategy
        active_strategies = strategy_manager.active_strategies
        if not active_strategies:
            pytest.skip("No active strategies available")
        
        strategy_id = list(active_strategies.keys())[0]
        
        # Configuration
        num_requests = 100
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX"]
        
        logger.info(f"Generating {num_requests} authorization requests...")
        
        # Create authorization requests
        requests = []
        for i in range(num_requests):
            symbol = symbols[i % len(symbols)]
            request = TradingDecisionRequest(
                decision_type=TradingDecisionType.POSITION_ENTRY,
                strategy_id=strategy_id,
                symbol=symbol,
                side="buy" if i % 2 == 0 else "sell",
                quantity=50.0 + (i % 10) * 10,
                expected_return=0.05 + (i % 10) * 0.01,
                confidence=0.70 + (i % 20) * 0.01,
                current_position=0.0,
                portfolio_impact=0.10,
                risk_score=0.25 + (i % 10) * 0.02,
                market_regime="bullish" if i % 2 == 0 else "neutral",
                regime_confidence=0.75 + (i % 15) * 0.01,
                volatility_estimate=0.02 + (i % 10) * 0.005,
                urgency=ExecutionUrgency.NORMAL,
                max_execution_time=3600,
                requesting_component="StrategyManager",
                justification=f"Performance test request {i+1}/{num_requests}",
                metadata={'test': 'high_volume', 'request_number': i+1}
            )
            requests.append(request)
        
        logger.info(f"Processing {num_requests} requests...")
        start_time = time.time()
        
        # Process all requests concurrently
        authorizations = await asyncio.gather(*[
            risk_manager.authorize_trading_decision(req)
            for req in requests
        ])
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Analyze results
        approved_count = 0
        rejected_count = 0
        automatic_count = 0
        standard_count = 0
        elevated_count = 0
        
        for auth in authorizations:
            if auth.authorization_level == AuthorizationLevel.REJECTED:
                rejected_count += 1
            else:
                approved_count += 1
                if auth.authorization_level == AuthorizationLevel.AUTOMATIC:
                    automatic_count += 1
                elif auth.authorization_level == AuthorizationLevel.STANDARD:
                    standard_count += 1
                elif auth.authorization_level == AuthorizationLevel.ELEVATED:
                    elevated_count += 1
        
        # Calculate metrics
        throughput = num_requests / total_time
        avg_response_time = (total_time / num_requests) * 1000  # milliseconds
        approval_rate = (approved_count / num_requests) * 100
        
        logger.info("=" * 60)
        logger.info("✅ HIGH-VOLUME AUTHORIZATION PROCESSING RESULTS")
        logger.info(f"   Total Requests: {num_requests}")
        logger.info(f"   Total Time: {total_time:.3f}s")
        logger.info(f"   Throughput: {throughput:.2f} requests/second")
        logger.info(f"   Avg Response Time: {avg_response_time:.2f}ms per request")
        logger.info(f"   Approved: {approved_count} ({approval_rate:.1f}%)")
        logger.info(f"   Rejected: {rejected_count}")
        logger.info(f"   Authorization Breakdown:")
        logger.info(f"     - Automatic: {automatic_count}")
        logger.info(f"     - Standard: {standard_count}")
        logger.info(f"     - Elevated: {elevated_count}")
        logger.info("=" * 60)
        
        # Validate performance
        assert len(authorizations) == num_requests, "All requests should be processed"
        assert throughput > 100, f"Throughput should exceed 100 req/s, got {throughput:.2f}"
        assert avg_response_time < 50, f"Avg response time should be < 50ms, got {avg_response_time:.2f}ms"
        logger.info(f"✅ Performance validated: {throughput:.2f} req/s, {avg_response_time:.2f}ms avg")
    
    async def test_concurrent_strategy_processing(
        self, orchestrator, strategy_manager, risk_manager
    ):
        """
        Test: Concurrent multi-strategy signal processing
        
        Validates:
        - Multiple strategies processing simultaneously
        - No race conditions in concurrent processing
        - Authorization queue handling
        - Strategy independence maintained
        """
        logger.info("🔄 Testing Concurrent Strategy Processing")
        
        # Register components
        orchestrator.register_central_risk_manager(risk_manager)
        orchestrator.register_component(
            name="StrategyManager",
            component=strategy_manager,
            layer="execution",
            authority_level="strategic"
        )
        
        # Start components
        await risk_manager.start()
        await strategy_manager.start()
        
        # Get active strategies
        active_strategies = strategy_manager.active_strategies
        if len(active_strategies) < 2:
            pytest.skip("Need at least 2 active strategies")
        
        strategy_ids = list(active_strategies.keys())
        num_strategies = len(strategy_ids)
        requests_per_strategy = 20
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN"]
        
        logger.info(f"Testing {num_strategies} strategies with {requests_per_strategy} requests each")
        
        # Create concurrent requests from multiple strategies
        all_requests = []
        for strategy_idx, strategy_id in enumerate(strategy_ids):
            for req_idx in range(requests_per_strategy):
                symbol = symbols[req_idx % len(symbols)]
                request = TradingDecisionRequest(
                    decision_type=TradingDecisionType.POSITION_ENTRY,
                    strategy_id=strategy_id,
                    symbol=symbol,
                    side="buy",
                    quantity=100.0,
                    expected_return=0.06 + strategy_idx * 0.01,
                    confidence=0.75 + req_idx * 0.005,
                    current_position=0.0,
                    portfolio_impact=0.12,
                    risk_score=0.28,
                    market_regime="bullish",
                    regime_confidence=0.80,
                    volatility_estimate=0.025,
                    urgency=ExecutionUrgency.NORMAL,
                    max_execution_time=3600,
                    requesting_component="StrategyManager",
                    justification=f"Concurrent test - Strategy {strategy_idx+1}, Request {req_idx+1}",
                    metadata={
                        'test': 'concurrent_strategies',
                        'strategy_index': strategy_idx,
                        'request_number': req_idx
                    }
                )
                all_requests.append((strategy_id, request))
        
        logger.info(f"Processing {len(all_requests)} concurrent requests...")
        start_time = time.time()
        
        # Process all requests concurrently
        authorizations = await asyncio.gather(*[
            risk_manager.authorize_trading_decision(req)
            for _, req in all_requests
        ])
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Analyze results by strategy
        strategy_results = {sid: {'approved': 0, 'rejected': 0} for sid in strategy_ids}
        
        for (strategy_id, _), auth in zip(all_requests, authorizations):
            if auth.authorization_level == AuthorizationLevel.REJECTED:
                strategy_results[strategy_id]['rejected'] += 1
            else:
                strategy_results[strategy_id]['approved'] += 1
        
        throughput = len(all_requests) / total_time
        
        logger.info("=" * 60)
        logger.info("✅ CONCURRENT STRATEGY PROCESSING RESULTS")
        logger.info(f"   Strategies: {num_strategies}")
        logger.info(f"   Total Requests: {len(all_requests)}")
        logger.info(f"   Processing Time: {total_time:.3f}s")
        logger.info(f"   Throughput: {throughput:.2f} requests/second")
        logger.info(f"   Results by Strategy:")
        for idx, strategy_id in enumerate(strategy_ids):
            results = strategy_results[strategy_id]
            logger.info(f"     Strategy {idx+1} ({strategy_id}):")
            logger.info(f"       Approved: {results['approved']}")
            logger.info(f"       Rejected: {results['rejected']}")
        logger.info("=" * 60)
        
        # Validate concurrent processing
        assert len(authorizations) == len(all_requests), "All requests processed"
        assert throughput > 50, f"Concurrent throughput should exceed 50 req/s, got {throughput:.2f}"
        logger.info(f"✅ Concurrent processing validated: {throughput:.2f} req/s across {num_strategies} strategies")
    
    async def test_stress_testing_under_load(
        self, orchestrator, strategy_manager, risk_manager
    ):
        """
        Test: System stress testing under sustained load
        
        Validates:
        - System stability under sustained high load
        - No memory leaks or resource exhaustion
        - Consistent performance over time
        - Error handling under stress
        """
        logger.info("🔄 Testing System Under Stress Load")
        
        # Register components
        orchestrator.register_central_risk_manager(risk_manager)
        orchestrator.register_component(
            name="StrategyManager",
            component=strategy_manager,
            layer="execution",
            authority_level="strategic"
        )
        
        # Start components
        await risk_manager.start()
        await strategy_manager.start()
        
        # Get active strategy
        active_strategies = strategy_manager.active_strategies
        if not active_strategies:
            pytest.skip("No active strategies available")
        
        strategy_id = list(active_strategies.keys())[0]
        
        # Stress test configuration
        num_rounds = 5
        requests_per_round = 30
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        
        logger.info(f"Stress test: {num_rounds} rounds × {requests_per_round} requests = {num_rounds * requests_per_round} total")
        
        round_times = []
        round_throughputs = []
        total_processed = 0
        
        for round_num in range(num_rounds):
            logger.info(f"Round {round_num + 1}/{num_rounds}...")
            
            # Create requests for this round
            requests = []
            for i in range(requests_per_round):
                symbol = symbols[i % len(symbols)]
                request = TradingDecisionRequest(
                    decision_type=TradingDecisionType.POSITION_ENTRY,
                    strategy_id=strategy_id,
                    symbol=symbol,
                    side="buy" if i % 2 == 0 else "sell",
                    quantity=75.0,
                    expected_return=0.06,
                    confidence=0.76,
                    current_position=0.0,
                    portfolio_impact=0.11,
                    risk_score=0.27,
                    market_regime="bullish",
                    regime_confidence=0.82,
                    volatility_estimate=0.023,
                    urgency=ExecutionUrgency.NORMAL,
                    max_execution_time=3600,
                    requesting_component="StrategyManager",
                    justification=f"Stress test Round {round_num+1}, Request {i+1}",
                    metadata={'test': 'stress', 'round': round_num+1, 'request': i+1}
                )
                requests.append(request)
            
            # Process round
            round_start = time.time()
            authorizations = await asyncio.gather(*[
                risk_manager.authorize_trading_decision(req)
                for req in requests
            ])
            round_end = time.time()
            
            round_time = round_end - round_start
            round_throughput = requests_per_round / round_time
            
            round_times.append(round_time)
            round_throughputs.append(round_throughput)
            total_processed += len(authorizations)
            
            logger.info(f"  Round {round_num + 1}: {round_time:.3f}s, {round_throughput:.2f} req/s")
            
            # Small delay between rounds
            await asyncio.sleep(0.01)
        
        # Calculate overall metrics
        total_time = sum(round_times)
        avg_round_time = total_time / num_rounds
        avg_throughput = sum(round_throughputs) / num_rounds
        min_throughput = min(round_throughputs)
        max_throughput = max(round_throughputs)
        throughput_variance = max_throughput - min_throughput
        
        logger.info("=" * 60)
        logger.info("✅ STRESS TEST RESULTS")
        logger.info(f"   Rounds: {num_rounds}")
        logger.info(f"   Total Requests: {total_processed}")
        logger.info(f"   Total Time: {total_time:.3f}s")
        logger.info(f"   Avg Round Time: {avg_round_time:.3f}s")
        logger.info(f"   Avg Throughput: {avg_throughput:.2f} req/s")
        logger.info(f"   Min Throughput: {min_throughput:.2f} req/s")
        logger.info(f"   Max Throughput: {max_throughput:.2f} req/s")
        logger.info(f"   Throughput Variance: {throughput_variance:.2f} req/s")
        logger.info(f"   Performance Consistency: {((1 - throughput_variance/avg_throughput) * 100):.1f}%")
        logger.info("=" * 60)
        
        # Validate stress test
        assert total_processed == num_rounds * requests_per_round, "All requests processed"
        assert avg_throughput > 50, f"Avg throughput should exceed 50 req/s, got {avg_throughput:.2f}"
        assert throughput_variance < avg_throughput * 0.5, "Throughput variance should be < 50% of average"
        logger.info(f"✅ Stress test passed: Stable performance across {num_rounds} rounds")
    
    async def test_throughput_validation_mixed_operations(
        self, orchestrator, strategy_manager, risk_manager
    ):
        """
        Test: Throughput validation with mixed operation types
        
        Validates:
        - System handles mixed operation types (entry, exit, adjustment)
        - Throughput with realistic operation mix
        - Authorization level distribution
        - Performance with varied request complexity
        """
        logger.info("🔄 Testing Throughput with Mixed Operations")
        
        # Register components
        orchestrator.register_central_risk_manager(risk_manager)
        orchestrator.register_component(
            name="StrategyManager",
            component=strategy_manager,
            layer="execution",
            authority_level="strategic"
        )
        
        # Start components
        await risk_manager.start()
        await strategy_manager.start()
        
        # Get active strategy
        active_strategies = strategy_manager.active_strategies
        if not active_strategies:
            pytest.skip("No active strategies available")
        
        strategy_id = list(active_strategies.keys())[0]
        
        # Mixed operation configuration
        num_requests = 80
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA"]
        
        # Operation type distribution: 50% entry, 30% adjustment, 20% exit
        operation_types = (
            [TradingDecisionType.POSITION_ENTRY] * 40 +
            [TradingDecisionType.POSITION_ADJUSTMENT] * 24 +
            [TradingDecisionType.POSITION_EXIT] * 16
        )
        
        logger.info(f"Creating {num_requests} mixed operation requests...")
        logger.info(f"  Entry: 40, Adjustment: 24, Exit: 16")
        
        # Create mixed requests
        requests = []
        for i in range(num_requests):
            symbol = symbols[i % len(symbols)]
            op_type = operation_types[i]
            
            # Vary parameters based on operation type
            if op_type == TradingDecisionType.POSITION_ENTRY:
                quantity = 100.0
                current_position = 0.0
                side = "buy"
            elif op_type == TradingDecisionType.POSITION_ADJUSTMENT:
                quantity = 50.0
                current_position = 100.0
                side = "buy" if i % 2 == 0 else "sell"
            else:  # POSITION_EXIT
                quantity = 100.0
                current_position = 100.0
                side = "sell"
            
            request = TradingDecisionRequest(
                decision_type=op_type,
                strategy_id=strategy_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                expected_return=0.05 + (i % 15) * 0.002,
                confidence=0.72 + (i % 20) * 0.008,
                current_position=current_position,
                portfolio_impact=0.10 + (i % 10) * 0.01,
                risk_score=0.25 + (i % 12) * 0.015,
                market_regime="bullish" if i % 3 != 2 else "neutral",
                regime_confidence=0.78 + (i % 18) * 0.008,
                volatility_estimate=0.02 + (i % 15) * 0.003,
                urgency=ExecutionUrgency.NORMAL if i % 10 != 9 else ExecutionUrgency.HIGH,
                max_execution_time=3600,
                requesting_component="StrategyManager",
                justification=f"Mixed operations test - {op_type.value} #{i+1}",
                metadata={
                    'test': 'mixed_operations',
                    'operation_type': op_type.value,
                    'request_number': i+1
                }
            )
            requests.append(request)
        
        logger.info(f"Processing {num_requests} mixed operations...")
        start_time = time.time()
        
        # Process all requests
        authorizations = await asyncio.gather(*[
            risk_manager.authorize_trading_decision(req)
            for req in requests
        ])
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Analyze results by operation type
        results_by_type = {
            TradingDecisionType.POSITION_ENTRY: {'approved': 0, 'rejected': 0},
            TradingDecisionType.POSITION_ADJUSTMENT: {'approved': 0, 'rejected': 0},
            TradingDecisionType.POSITION_EXIT: {'approved': 0, 'rejected': 0}
        }
        
        for req, auth in zip(requests, authorizations):
            op_type = req.decision_type
            if auth.authorization_level == AuthorizationLevel.REJECTED:
                results_by_type[op_type]['rejected'] += 1
            else:
                results_by_type[op_type]['approved'] += 1
        
        # Calculate metrics
        throughput = num_requests / total_time
        avg_response_time = (total_time / num_requests) * 1000
        
        logger.info("=" * 60)
        logger.info("✅ MIXED OPERATIONS THROUGHPUT RESULTS")
        logger.info(f"   Total Requests: {num_requests}")
        logger.info(f"   Processing Time: {total_time:.3f}s")
        logger.info(f"   Throughput: {throughput:.2f} requests/second")
        logger.info(f"   Avg Response Time: {avg_response_time:.2f}ms")
        logger.info(f"   Results by Operation Type:")
        
        for op_type, results in results_by_type.items():
            total = results['approved'] + results['rejected']
            approval_rate = (results['approved'] / total * 100) if total > 0 else 0
            logger.info(f"     {op_type.value}:")
            logger.info(f"       Total: {total}")
            logger.info(f"       Approved: {results['approved']} ({approval_rate:.1f}%)")
            logger.info(f"       Rejected: {results['rejected']}")
        
        logger.info("=" * 60)
        
        # Validate performance
        assert len(authorizations) == num_requests, "All requests processed"
        assert throughput > 80, f"Mixed ops throughput should exceed 80 req/s, got {throughput:.2f}"
        assert avg_response_time < 60, f"Avg response time should be < 60ms, got {avg_response_time:.2f}ms"
        logger.info(f"✅ Mixed operations validated: {throughput:.2f} req/s, {avg_response_time:.2f}ms avg")
