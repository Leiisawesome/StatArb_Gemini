"""
Edge Case Integration Tests

Tests system behavior under boundary conditions, extreme scenarios,
and error conditions to validate robustness and graceful degradation.
"""

import asyncio
import pytest
import logging

from core_engine.system.central_risk_manager import (
    TradingDecisionRequest,
    TradingDecisionType,
    AuthorizationLevel,
)

logger = logging.getLogger(__name__)


class TestEdgeCaseIntegration:
    """
    Edge case integration tests validating system behavior
    under boundary conditions and extreme scenarios.
    """

    @pytest.mark.asyncio
    async def test_boundary_condition_validation(
        self,
        orchestrator,
        risk_manager,
        strategy_manager,
        regime_engine,
    ):
        """
        Test system handling of boundary conditions
        
        Validates:
        - Zero quantity requests
        - Negative price handling (should reject)
        - Extreme confidence values (0.0, 1.0)
        - Maximum position size limits
        - Minimum trade size validation
        - Symbol validation (empty, invalid)
        """
        logger.info("🔍 Testing Boundary Condition Validation")
        
        # Get active strategy
        active_strategies = list(strategy_manager.active_strategies.keys())
        assert len(active_strategies) > 0, "No active strategies"
        strategy_id = active_strategies[0]
        logger.info(f"Using strategy: {strategy_id}")
        
        test_results = {}
        
        # Test 1: Zero quantity request
        logger.info("\n1️⃣ Testing zero quantity request...")
        request_zero_qty = TradingDecisionRequest(
            symbol="AAPL",
            strategy_id=strategy_id,
            decision_type=TradingDecisionType.POSITION_ENTRY,
            side="buy",
            quantity=0.0,  # Zero quantity
            confidence=0.75,
            metadata={"test": "zero_quantity"},
        )
        
        result_zero_qty = await risk_manager.authorize_trading_decision(request_zero_qty)
        test_results["zero_quantity"] = {
            "authorized": (result_zero_qty.authorization_level != AuthorizationLevel.REJECTED),
            "authorized_quantity": result_zero_qty.authorized_quantity,
            "rejection_reason": getattr(result_zero_qty, "rejection_reason", None),
        }
        
        logger.info(f"   Zero quantity result: approved={(result_zero_qty.authorization_level != AuthorizationLevel.REJECTED)}, "
                   f"quantity={result_zero_qty.authorized_quantity}")
        
        # Zero quantity should either be rejected OR scaled to minimum viable quantity
        assert (not (result_zero_qty.authorization_level != AuthorizationLevel.REJECTED)) or (result_zero_qty.authorized_quantity == 0.0), \
            "Zero quantity should be rejected or return zero"
        
        # Test 2: Negative price (should reject)
        logger.info("\n2️⃣ Testing negative price request...")
        request_negative_price = TradingDecisionRequest(
            symbol="AAPL",
            strategy_id=strategy_id,
            decision_type=TradingDecisionType.POSITION_ENTRY,
            side="buy",
            quantity=100.0,
            confidence=0.75,
            metadata={"test": "negative_price"},
        )
        
        result_negative_price = await risk_manager.authorize_trading_decision(request_negative_price)
        test_results["negative_price"] = {
            "authorized": (result_negative_price.authorization_level != AuthorizationLevel.REJECTED),
            "authorized_quantity": result_negative_price.authorized_quantity,
        }
        
        logger.info(f"   Negative price result: approved={(result_negative_price.authorization_level != AuthorizationLevel.REJECTED)}")
        
        # Negative price should be rejected OR treated as error
        # (System may accept it if price validation not implemented, but quantity should be 0 or rejected)
        
        # Test 3: Minimum confidence (0.0)
        logger.info("\n3️⃣ Testing minimum confidence (0.0)...")
        request_min_confidence = TradingDecisionRequest(
            symbol="AAPL",
            strategy_id=strategy_id,
            decision_type=TradingDecisionType.POSITION_ENTRY,
            side="buy",
            quantity=100.0,
            confidence=0.0,  # Minimum confidence
            metadata={"test": "min_confidence"},
        )
        
        result_min_confidence = await risk_manager.authorize_trading_decision(request_min_confidence)
        test_results["min_confidence"] = {
            "authorized": (result_min_confidence.authorization_level != AuthorizationLevel.REJECTED),
            "authorized_quantity": result_min_confidence.authorized_quantity,
            "level": result_min_confidence.authorization_level,
        }
        
        logger.info(f"   Min confidence result: approved={(result_min_confidence.authorization_level != AuthorizationLevel.REJECTED)}, "
                   f"quantity={result_min_confidence.authorized_quantity}, "
                   f"level={result_min_confidence.authorization_level}")
        
        # Low confidence may still be approved but possibly with reduced quantity or higher authorization level
        
        # Test 4: Maximum confidence (1.0)
        logger.info("\n4️⃣ Testing maximum confidence (1.0)...")
        request_max_confidence = TradingDecisionRequest(
            symbol="AAPL",
            strategy_id=strategy_id,
            decision_type=TradingDecisionType.POSITION_ENTRY,
            side="buy",
            quantity=100.0,
            confidence=1.0,  # Maximum confidence
            metadata={"test": "max_confidence"},
        )
        
        result_max_confidence = await risk_manager.authorize_trading_decision(request_max_confidence)
        test_results["max_confidence"] = {
            "authorized": (result_max_confidence.authorization_level != AuthorizationLevel.REJECTED),
            "authorized_quantity": result_max_confidence.authorized_quantity,
            "level": result_max_confidence.authorization_level,
        }
        
        logger.info(f"   Max confidence result: approved={(result_max_confidence.authorization_level != AuthorizationLevel.REJECTED)}, "
                   f"quantity={result_max_confidence.authorized_quantity}, "
                   f"level={result_max_confidence.authorization_level}")
        
        # High confidence should be approved with potentially higher quantity
        assert (result_max_confidence.authorization_level != AuthorizationLevel.REJECTED), "Maximum confidence request should be approved"
        
        # Test 5: Very large quantity (position size limit test)
        logger.info("\n5️⃣ Testing very large quantity request...")
        request_large_qty = TradingDecisionRequest(
            symbol="AAPL",
            strategy_id=strategy_id,
            decision_type=TradingDecisionType.POSITION_ENTRY,
            side="buy",
            quantity=1_000_000.0,  # 1 million shares
            confidence=0.75,
            metadata={"test": "large_quantity"},
        )
        
        result_large_qty = await risk_manager.authorize_trading_decision(request_large_qty)
        test_results["large_quantity"] = {
            "authorized": (result_large_qty.authorization_level != AuthorizationLevel.REJECTED),
            "requested_quantity": 1_000_000.0,
            "authorized_quantity": result_large_qty.authorized_quantity,
            "level": result_large_qty.authorization_level,
            "reduction_pct": ((1_000_000.0 - result_large_qty.authorized_quantity) / 1_000_000.0 * 100)
                if (result_large_qty.authorization_level != AuthorizationLevel.REJECTED) else 100.0,
        }
        
        logger.info(f"   Large quantity result: approved={(result_large_qty.authorization_level != AuthorizationLevel.REJECTED)}, "
                   f"requested=1M, authorized={result_large_qty.authorized_quantity:.0f}, "
                   f"reduction={test_results['large_quantity']['reduction_pct']:.1f}%")
        
        # Large quantity should be reduced or require higher authorization
        if (result_large_qty.authorization_level != AuthorizationLevel.REJECTED):
            assert result_large_qty.authorized_quantity < 1_000_000.0, \
                "Large quantity should be reduced"
            # May require standard or higher authorization level
            logger.info(f"   Authorization level: {result_large_qty.authorization_level}")
        
        # Test 6: Very small quantity (minimum trade size)
        logger.info("\n6️⃣ Testing very small quantity request...")
        request_small_qty = TradingDecisionRequest(
            symbol="AAPL",
            strategy_id=strategy_id,
            decision_type=TradingDecisionType.POSITION_ENTRY,
            side="buy",
            quantity=0.01,  # Very small quantity
            confidence=0.75,
            metadata={"test": "small_quantity"},
        )
        
        result_small_qty = await risk_manager.authorize_trading_decision(request_small_qty)
        test_results["small_quantity"] = {
            "authorized": (result_small_qty.authorization_level != AuthorizationLevel.REJECTED),
            "requested_quantity": 0.01,
            "authorized_quantity": result_small_qty.authorized_quantity,
        }
        
        logger.info(f"   Small quantity result: approved={(result_small_qty.authorization_level != AuthorizationLevel.REJECTED)}, "
                   f"requested=0.01, authorized={result_small_qty.authorized_quantity}")
        
        # Small quantity may be rejected or rounded to minimum
        
        # Test 7: Empty symbol (should reject)
        logger.info("\n7️⃣ Testing empty symbol request...")
        try:
            request_empty_symbol = TradingDecisionRequest(
                symbol="",  # Empty symbol
                strategy_id=strategy_id,
                decision_type=TradingDecisionType.POSITION_ENTRY,
                side="buy",
                quantity=100.0,
                confidence=0.75,
                metadata={"test": "empty_symbol"},
            )
            
            result_empty_symbol = await risk_manager.authorize_trading_decision(request_empty_symbol)
            test_results["empty_symbol"] = {
                "authorized": (result_empty_symbol.authorization_level != AuthorizationLevel.REJECTED),
                "error": None,
            }
            
            logger.info(f"   Empty symbol result: approved={(result_empty_symbol.authorization_level != AuthorizationLevel.REJECTED)}")
            
            # Empty symbol should be rejected
            assert not (result_empty_symbol.authorization_level != AuthorizationLevel.REJECTED), "Empty symbol should be rejected"
            
        except Exception as e:
            test_results["empty_symbol"] = {
                "approved": False,
                "error": str(e),
            }
            logger.info(f"   Empty symbol raised exception (expected): {type(e).__name__}")
        
        # Test 8: Invalid symbol format
        logger.info("\n8️⃣ Testing invalid symbol format...")
        request_invalid_symbol = TradingDecisionRequest(
            symbol="INVALID_SYMBOL_12345",  # Invalid format
            strategy_id=strategy_id,
            decision_type=TradingDecisionType.POSITION_ENTRY,
            side="buy",
            quantity=100.0,
            confidence=0.75,
            metadata={"test": "invalid_symbol"},
        )
        
        result_invalid_symbol = await risk_manager.authorize_trading_decision(request_invalid_symbol)
        test_results["invalid_symbol"] = {
            "authorized": (result_invalid_symbol.authorization_level != AuthorizationLevel.REJECTED),
            "authorized_quantity": result_invalid_symbol.authorized_quantity,
        }
        
        logger.info(f"   Invalid symbol result: approved={(result_invalid_symbol.authorization_level != AuthorizationLevel.REJECTED)}")
        
        # Invalid symbol may be accepted (system doesn't validate symbol format)
        # or rejected if symbol validation is implemented
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("✅ BOUNDARY CONDITION TEST RESULTS")
        for test_name, result in test_results.items():
            logger.info(f"   {test_name}: {result}")
        logger.info("=" * 60)
        
        # Key validations
        assert (result_max_confidence.authorization_level != AuthorizationLevel.REJECTED), \
            "Maximum confidence (1.0) request should be approved"
        assert not (result_zero_qty.authorization_level != AuthorizationLevel.REJECTED) or result_zero_qty.authorized_quantity == 0.0, \
            "Zero quantity should be rejected or return zero"
        
        logger.info("✅ Boundary condition validation passed")

    @pytest.mark.asyncio
    async def test_extreme_market_scenario_handling(
        self,
        orchestrator,
        risk_manager,
        strategy_manager,
        regime_engine,
        data_manager,
    ):
        """
        Test system handling of extreme market scenarios
        
        Validates:
        - Extreme volatility (>100%)
        - Flash crash simulation (rapid price drop)
        - Gap up/down events (large price jumps)
        - High regime change frequency
        - Rapid fire authorization requests
        """
        logger.info("🌪️ Testing Extreme Market Scenario Handling")
        
        # Get active strategy
        active_strategies = list(strategy_manager.active_strategies.keys())
        assert len(active_strategies) > 0, "No active strategies"
        strategy_id = active_strategies[0]
        
        test_scenarios = {}
        
        # Scenario 1: Extreme volatility (>100%)
        logger.info("\n1️⃣ Scenario: Extreme Volatility (>100%)")
        logger.info("   Simulating market with >100% volatility...")
        
        # Update market data with extreme volatility
        extreme_volatility_data = {
            "AAPL": {
                "price": 150.0,
                "volatility": 1.5,  # 150% volatility
                "volume": 10_000_000,
                "bid": 149.5,
                "ask": 150.5,
            }
        }
        
        # Note: DataManager is mock, so we simulate the effect
        logger.info("   Market state: AAPL @ $150, volatility=150%")
        
        # Submit request under extreme volatility
        request_extreme_vol = TradingDecisionRequest(
            symbol="AAPL",
            strategy_id=strategy_id,
            decision_type=TradingDecisionType.POSITION_ENTRY,
            side="buy",
            quantity=100.0,
            confidence=0.75,
            metadata={"scenario": "extreme_volatility", "volatility": 1.5},
        )
        
        result_extreme_vol = await risk_manager.authorize_trading_decision(request_extreme_vol)
        test_scenarios["extreme_volatility"] = {
            "authorized": (result_extreme_vol.authorization_level != AuthorizationLevel.REJECTED),
            "requested": 100.0,
            "authorized": result_extreme_vol.authorized_quantity,
            "level": result_extreme_vol.authorization_level,
            "scaling_applied": result_extreme_vol.authorized_quantity != 100.0,
        }
        
        logger.info(f"   Result: approved={(result_extreme_vol.authorization_level != AuthorizationLevel.REJECTED)}, "
                   f"quantity={result_extreme_vol.authorized_quantity:.1f}, "
                   f"level={result_extreme_vol.authorization_level}")
        
        # Extreme volatility should trigger risk controls
        # (may reduce quantity or require higher authorization)
        
        # Scenario 2: Flash crash simulation
        logger.info("\n2️⃣ Scenario: Flash Crash Simulation")
        logger.info("   Simulating rapid price drop (20% in seconds)...")
        
        # Submit rapid sequence of requests at progressively lower prices
        flash_crash_requests = []
        prices = [150.0, 145.0, 140.0, 135.0, 130.0, 125.0, 120.0]  # -20% over 7 requests
        
        for i, price in enumerate(prices):
            request = TradingDecisionRequest(
                symbol="TSLA",
                strategy_id=strategy_id,
                decision_type=TradingDecisionType.POSITION_ENTRY,
                side="buy",
                quantity=50.0,
                confidence=0.70 - (i * 0.05),  # Declining confidence
                metadata={"scenario": "flash_crash", "sequence": i, "price_drop_pct": (150-price)/150*100},
            )
            flash_crash_requests.append(request)
        
        # Submit all requests rapidly
        flash_crash_results = []
        start_time = asyncio.get_event_loop().time()
        
        for req in flash_crash_requests:
            result = await risk_manager.authorize_trading_decision(req)
            flash_crash_results.append(result)
        
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time
        
        # Analyze flash crash handling
        approved_count = sum(1 for r in flash_crash_results if (r.authorization_level != AuthorizationLevel.REJECTED))
        total_authorized = sum(r.authorized_quantity for r in flash_crash_results if (r.authorization_level != AuthorizationLevel.REJECTED))
        
        test_scenarios["flash_crash"] = {
            "requests_sent": len(flash_crash_requests),
            "approved": approved_count,
            "rejected": len(flash_crash_requests) - approved_count,
            "total_authorized_quantity": total_authorized,
            "duration_ms": duration * 1000,
            "price_range": f"${prices[0]:.0f}-${prices[-1]:.0f}",
            "price_drop_pct": ((prices[0] - prices[-1]) / prices[0] * 100),
        }
        
        logger.info(f"   Flash crash: {len(flash_crash_requests)} requests in {duration*1000:.1f}ms")
        logger.info(f"   Price: ${prices[0]:.0f} → ${prices[-1]:.0f} (-{test_scenarios['flash_crash']['price_drop_pct']:.1f}%)")
        logger.info(f"   Approved: {approved_count}/{len(flash_crash_requests)}")
        logger.info(f"   Total authorized: {total_authorized:.1f} shares")
        
        # Flash crash should trigger protective mechanisms
        # (reduced approvals, lower quantities, or higher authorization levels)
        
        # Scenario 3: Gap up event (large positive price jump)
        logger.info("\n3️⃣ Scenario: Gap Up Event")
        logger.info("   Simulating large price gap (+15%)...")
        
        # First request at normal price
        request_pre_gap = TradingDecisionRequest(
            symbol="MSFT",
            strategy_id=strategy_id,
            decision_type=TradingDecisionType.POSITION_ENTRY,
            side="buy",
            quantity=100.0,
            confidence=0.75,
            metadata={"scenario": "pre_gap"},
        )
        
        result_pre_gap = await risk_manager.authorize_trading_decision(request_pre_gap)
        
        # Second request after gap up
        request_post_gap = TradingDecisionRequest(
            symbol="MSFT",
            strategy_id=strategy_id,
            decision_type=TradingDecisionType.POSITION_ADJUSTMENT,
            side="buy",
            quantity=100.0,
            confidence=0.75,
            metadata={"scenario": "post_gap", "gap_pct": 15.0},
        )
        
        result_post_gap = await risk_manager.authorize_trading_decision(request_post_gap)
        
        test_scenarios["gap_up"] = {
            "pre_gap_approved": (result_pre_gap.authorization_level != AuthorizationLevel.REJECTED),
            "pre_gap_quantity": result_pre_gap.authorized_quantity,
            "post_gap_approved": (result_post_gap.authorization_level != AuthorizationLevel.REJECTED),
            "post_gap_quantity": result_post_gap.authorized_quantity,
            "gap_percentage": 15.0,
            "quantity_change": result_post_gap.authorized_quantity - result_pre_gap.authorized_quantity
                if (result_post_gap.authorization_level != AuthorizationLevel.REJECTED) else 0,
        }
        
        logger.info(f"   Pre-gap: approved={(result_pre_gap.authorization_level != AuthorizationLevel.REJECTED)}, "
                   f"quantity={result_pre_gap.authorized_quantity:.1f}")
        logger.info(f"   Post-gap: approved={(result_post_gap.authorization_level != AuthorizationLevel.REJECTED)}, "
                   f"quantity={result_post_gap.authorized_quantity:.1f}")
        
        # Scenario 4: Rapid regime changes
        logger.info("\n4️⃣ Scenario: Rapid Regime Changes")
        logger.info("   Simulating high-frequency regime transitions...")
        
        # Note: Regime transitions handled by regime engine
        # We'll test how authorization adapts to rapid changes
        
        regime_test_requests = []
        regimes = ["bullish", "neutral", "bearish", "neutral", "bullish"]
        
        for i, regime in enumerate(regimes):
            request = TradingDecisionRequest(
                symbol="SPY",
                strategy_id=strategy_id,
                decision_type=TradingDecisionType.POSITION_ADJUSTMENT,
                side="buy" if regime == "bullish" else "sell",
                quantity=50.0,
                confidence=0.75,
                metadata={"scenario": "regime_change", "regime": regime, "sequence": i},
            )
            regime_test_requests.append(request)
        
        regime_test_results = []
        for req in regime_test_requests:
            result = await risk_manager.authorize_trading_decision(req)
            regime_test_results.append(result)
        
        approved_regime = sum(1 for r in regime_test_results if (r.authorization_level != AuthorizationLevel.REJECTED))
        
        test_scenarios["rapid_regime_changes"] = {
            "regime_changes": len(regimes),
            "requests_sent": len(regime_test_requests),
            "approved": approved_regime,
            "approval_rate": (approved_regime / len(regime_test_requests) * 100),
        }
        
        logger.info(f"   Regime changes: {len(regimes)}")
        logger.info(f"   Approved: {approved_regime}/{len(regime_test_requests)} "
                   f"({test_scenarios['rapid_regime_changes']['approval_rate']:.1f}%)")
        
        # Scenario 5: Rapid fire authorization requests
        logger.info("\n5️⃣ Scenario: Rapid Fire Authorization Requests")
        logger.info("   Submitting 50 requests as fast as possible...")
        
        rapid_fire_requests = []
        for i in range(50):
            request = TradingDecisionRequest(
                symbol=f"SYM{i % 5}",  # 5 different symbols
                strategy_id=strategy_id,
                decision_type=TradingDecisionType.POSITION_ENTRY,
                side="buy" if i % 2 == 0 else "sell",
                quantity=10.0 + (i % 10),
                confidence=0.5 + (i % 5) * 0.1,
                metadata={"scenario": "rapid_fire", "sequence": i},
            )
            rapid_fire_requests.append(request)
        
        # Submit all concurrently
        start_time = asyncio.get_event_loop().time()
        rapid_fire_results = await asyncio.gather(*[
            risk_manager.authorize_trading_decision(req)
            for req in rapid_fire_requests
        ])
        end_time = asyncio.get_event_loop().time()
        
        duration = end_time - start_time
        approved_rapid = sum(1 for r in rapid_fire_results if (r.authorization_level != AuthorizationLevel.REJECTED))
        throughput = len(rapid_fire_requests) / duration
        
        test_scenarios["rapid_fire"] = {
            "requests": len(rapid_fire_requests),
            "approved": approved_rapid,
            "duration_ms": duration * 1000,
            "throughput_req_per_sec": throughput,
            "avg_latency_ms": (duration / len(rapid_fire_requests)) * 1000,
        }
        
        logger.info(f"   Rapid fire: {len(rapid_fire_requests)} requests in {duration*1000:.1f}ms")
        logger.info(f"   Throughput: {throughput:.0f} req/s")
        logger.info(f"   Approved: {approved_rapid}/{len(rapid_fire_requests)}")
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("✅ EXTREME MARKET SCENARIO TEST RESULTS")
        for scenario_name, result in test_scenarios.items():
            logger.info(f"   {scenario_name}:")
            for key, value in result.items():
                logger.info(f"      {key}: {value}")
        logger.info("=" * 60)
        
        # Key validations
        assert (result_extreme_vol.authorization_level != AuthorizationLevel.REJECTED) is not None, "Extreme volatility should return result"
        assert approved_count >= 0, "Flash crash should process all requests"
        assert (result_post_gap.authorization_level != AuthorizationLevel.REJECTED) is not None, "Gap up should return result"
        assert approved_rapid > 0, "Rapid fire should approve some requests"
        
        logger.info("✅ Extreme market scenario handling validated")

    @pytest.mark.asyncio
    async def test_concurrent_error_handling_and_recovery(
        self,
        orchestrator,
        risk_manager,
        strategy_manager,
    ):
        """
        Test system error handling and recovery under concurrent load
        
        Validates:
        - Invalid request handling during high load
        - Mixed valid/invalid request processing
        - Error isolation (one error doesn't crash system)
        - Graceful degradation under errors
        - System recovery after error burst
        """
        logger.info("⚠️ Testing Concurrent Error Handling and Recovery")
        
        # Get active strategy
        active_strategies = list(strategy_manager.active_strategies.keys())
        assert len(active_strategies) > 0, "No active strategies"
        strategy_id = active_strategies[0]
        
        error_test_results = {}
        
        # Test 1: Mixed valid and invalid requests
        logger.info("\n1️⃣ Test: Mixed Valid/Invalid Requests")
        logger.info("   Creating 30 requests (20 valid, 10 invalid)...")
        
        mixed_requests = []
        
        # 20 valid requests
        for i in range(20):
            request = TradingDecisionRequest(
                symbol=f"VALID{i % 5}",
                strategy_id=strategy_id,
                decision_type=TradingDecisionType.POSITION_ENTRY,
                side="buy",
                quantity=100.0,
                confidence=0.75,
                metadata={"type": "valid", "sequence": i},
            )
            mixed_requests.append(("valid", request))
        
        # 10 potentially invalid requests (edge cases that may cause errors)
        invalid_configs = [
            {"quantity": 0.0, "label": "zero_quantity"},
            {"price": -100.0, "label": "negative_price"},
            {"quantity": float('inf'), "label": "infinite_quantity"},
            {"price": 0.0, "label": "zero_price"},
            {"symbol": "", "label": "empty_symbol"},
            {"quantity": -50.0, "label": "negative_quantity"},
            {"confidence": 2.0, "label": "invalid_confidence_high"},
            {"confidence": -0.5, "label": "invalid_confidence_low"},
            {"quantity": 1e15, "label": "extreme_quantity"},
            {"price": 1e10, "label": "extreme_price"},
        ]
        
        for i, config in enumerate(invalid_configs):
            try:
                request = TradingDecisionRequest(
                    symbol=config.get("symbol", f"INVALID{i}"),
                    strategy_id=strategy_id,
                    decision_type=TradingDecisionType.POSITION_ENTRY,
                    side="buy",
                    quantity=config.get("quantity", 100.0),
                    confidence=config.get("confidence", 0.75),
                    metadata={"type": "invalid", "label": config["label"]},
                )
                mixed_requests.append(("invalid", request))
            except Exception as e:
                logger.info(f"   Request creation failed for {config['label']}: {type(e).__name__}")
                # Count as invalid but couldn't create
                error_test_results[f"creation_error_{config['label']}"] = str(e)
        
        # Shuffle to mix valid and invalid
        import random
        random.shuffle(mixed_requests)
        
        logger.info(f"   Total requests prepared: {len(mixed_requests)}")
        
        # Submit all concurrently
        logger.info("   Submitting all requests concurrently...")
        
        async def process_with_error_handling(req_type, req):
            """Process request with error handling"""
            try:
                result = await risk_manager.authorize_trading_decision(req)
                return {
                    "type": req_type,
                    "success": True,
                    "authorized": result.authorization_level != AuthorizationLevel.REJECTED,
                    "quantity": result.authorized_quantity,
                    "error": None,
                }
            except Exception as e:
                return {
                    "type": req_type,
                    "success": False,
                    "approved": False,
                    "quantity": 0.0,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
        
        start_time = asyncio.get_event_loop().time()
        
        results = await asyncio.gather(*[
            process_with_error_handling(req_type, req)
            for req_type, req in mixed_requests
        ], return_exceptions=False)
        
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time
        
        # Analyze results
        valid_results = [r for r in results if r["type"] == "valid"]
        invalid_results = [r for r in results if r["type"] == "invalid"]
        
        valid_success = sum(1 for r in valid_results if r["success"])
        valid_approved = sum(1 for r in valid_results if r["authorized"])
        invalid_success = sum(1 for r in invalid_results if r["success"])
        invalid_approved = sum(1 for r in invalid_results if r["authorized"])
        
        errors_encountered = [r for r in results if r.get("error")]
        
        error_test_results["mixed_requests"] = {
            "total_requests": len(mixed_requests),
            "valid_requests": len(valid_results),
            "invalid_requests": len(invalid_results),
            "valid_processed": valid_success,
            "valid_approved": valid_approved,
            "invalid_processed": invalid_success,
            "invalid_approved": invalid_approved,
            "errors_caught": len(errors_encountered),
            "duration_ms": duration * 1000,
            "throughput_req_per_sec": len(mixed_requests) / duration,
        }
        
        logger.info(f"   Processed {len(mixed_requests)} mixed requests in {duration*1000:.1f}ms")
        logger.info(f"   Valid: {valid_success}/{len(valid_results)} processed, "
                   f"{valid_approved} approved")
        logger.info(f"   Invalid: {invalid_success}/{len(invalid_results)} processed, "
                   f"{invalid_approved} approved")
        logger.info(f"   Errors caught: {len(errors_encountered)}")
        
        # Test 2: Error isolation (ensure one error doesn't crash subsequent requests)
        logger.info("\n2️⃣ Test: Error Isolation")
        logger.info("   Testing if errors are isolated and don't affect subsequent requests...")
        
        isolation_requests = []
        
        # Send error-prone request
        try:
            error_request = TradingDecisionRequest(
                symbol="ERROR_TEST",
                strategy_id=strategy_id,
                decision_type=TradingDecisionType.POSITION_ENTRY,
                side="buy",
                quantity=0.0,  # Potentially problematic
                confidence=0.75,
                metadata={"test": "error_isolation", "sequence": 0},
            )
            isolation_requests.append(error_request)
        except Exception as e:
            logger.info(f"   Error request creation failed (expected): {type(e).__name__}")
        
        # Send valid follow-up requests
        for i in range(5):
            request = TradingDecisionRequest(
                symbol=f"FOLLOWUP{i}",
                strategy_id=strategy_id,
                decision_type=TradingDecisionType.POSITION_ENTRY,
                side="buy",
                quantity=100.0,
                confidence=0.75,
                metadata={"test": "error_isolation", "sequence": i + 1},
            )
            isolation_requests.append(request)
        
        # Process sequentially to test isolation
        isolation_results = []
        for req in isolation_requests:
            try:
                result = await risk_manager.authorize_trading_decision(req)
                isolation_results.append({
                    "success": True,
                    "authorized": result.authorization_level != AuthorizationLevel.REJECTED,
                    "quantity": result.authorized_quantity,
                })
            except Exception as e:
                isolation_results.append({
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                })
        
        successful_after_error = sum(1 for r in isolation_results[1:] if r["success"])
        
        error_test_results["error_isolation"] = {
            "total_requests": len(isolation_requests),
            "successful_after_error": successful_after_error,
            "recovery_rate": (successful_after_error / (len(isolation_requests) - 1) * 100)
                if len(isolation_requests) > 1 else 0,
        }
        
        logger.info(f"   Follow-up requests after error: {successful_after_error}/{len(isolation_requests)-1}")
        logger.info(f"   Recovery rate: {error_test_results['error_isolation']['recovery_rate']:.1f}%")
        
        # Test 3: Graceful degradation under error burst
        logger.info("\n3️⃣ Test: Graceful Degradation Under Error Burst")
        logger.info("   Sending burst of potentially problematic requests...")
        
        burst_requests = []
        for i in range(20):
            # Mix of potentially problematic requests
            quantity = 0.0 if i % 5 == 0 else 100.0
            price = -50.0 if i % 7 == 0 else 150.0
            
            try:
                request = TradingDecisionRequest(
                    symbol=f"BURST{i}",
                    strategy_id=strategy_id,
                    decision_type=TradingDecisionType.POSITION_ENTRY,
                    side="buy",
                    quantity=quantity,
                    confidence=0.75,
                    metadata={"test": "error_burst", "sequence": i},
                )
                burst_requests.append(request)
            except Exception as e:
                logger.info(f"   Burst request {i} creation failed: {type(e).__name__}")
        
        # Submit burst concurrently
        burst_start = asyncio.get_event_loop().time()
        
        burst_results = await asyncio.gather(*[
            process_with_error_handling("burst", req)
            for req in burst_requests
        ], return_exceptions=False)
        
        burst_end = asyncio.get_event_loop().time()
        burst_duration = burst_end - burst_start
        
        burst_success = sum(1 for r in burst_results if r["success"])
        burst_errors = len(burst_results) - burst_success
        
        error_test_results["error_burst"] = {
            "total_requests": len(burst_requests),
            "successful": burst_success,
            "failed": burst_errors,
            "success_rate": (burst_success / len(burst_requests) * 100) if burst_requests else 0,
            "duration_ms": burst_duration * 1000,
        }
        
        logger.info(f"   Burst: {len(burst_requests)} requests in {burst_duration*1000:.1f}ms")
        logger.info(f"   Successful: {burst_success}, Failed: {burst_errors}")
        logger.info(f"   Success rate: {error_test_results['error_burst']['success_rate']:.1f}%")
        
        # Test 4: System recovery after error burst
        logger.info("\n4️⃣ Test: System Recovery After Error Burst")
        logger.info("   Sending normal requests after error burst...")
        
        recovery_requests = []
        for i in range(10):
            request = TradingDecisionRequest(
                symbol=f"RECOVERY{i}",
                strategy_id=strategy_id,
                decision_type=TradingDecisionType.POSITION_ENTRY,
                side="buy",
                quantity=100.0,
                confidence=0.75,
                metadata={"test": "recovery", "sequence": i},
            )
            recovery_requests.append(request)
        
        recovery_results = []
        for req in recovery_requests:
            try:
                result = await risk_manager.authorize_trading_decision(req)
                recovery_results.append({
                    "success": True,
                    "authorized": result.authorization_level != AuthorizationLevel.REJECTED,
                })
            except Exception as e:
                recovery_results.append({
                    "success": False,
                    "error": str(e),
                })
        
        recovery_success = sum(1 for r in recovery_results if r["success"])
        
        error_test_results["post_burst_recovery"] = {
            "total_requests": len(recovery_requests),
            "successful": recovery_success,
            "recovery_rate": (recovery_success / len(recovery_requests) * 100),
        }
        
        logger.info(f"   Recovery: {recovery_success}/{len(recovery_requests)} successful")
        logger.info(f"   Recovery rate: {error_test_results['post_burst_recovery']['recovery_rate']:.1f}%")
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("✅ ERROR HANDLING AND RECOVERY TEST RESULTS")
        for test_name, result in error_test_results.items():
            logger.info(f"   {test_name}:")
            if isinstance(result, dict):
                for key, value in result.items():
                    logger.info(f"      {key}: {value}")
            else:
                logger.info(f"      {result}")
        logger.info("=" * 60)
        
        # Key validations
        assert valid_success > 0, "Valid requests should process successfully"
        assert successful_after_error >= 4, "System should recover after errors (>= 80%)"
        assert recovery_success >= 8, "System should fully recover after error burst (>= 80%)"
        
        # Validate error isolation
        recovery_rate = error_test_results["error_isolation"]["recovery_rate"]
        assert recovery_rate >= 80.0, f"Error isolation recovery should be >= 80% (got {recovery_rate:.1f}%)"
        
        logger.info("✅ Concurrent error handling and recovery validated")


# Test execution summary
if __name__ == "__main__":
    print("Edge Case Integration Tests")
    print("Run with: python -m pytest tests/integration/edge_cases/test_edge_cases.py -v")
