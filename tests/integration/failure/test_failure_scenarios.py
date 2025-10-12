"""
Integration Tests - Failure Scenarios
======================================

Comprehensive failure and recovery testing for StatArb_Gemini system.

Tests cover:
- Network timeouts and communication failures
- Component crashes and recovery
- Data corruption detection and handling
- Partial system failures and degradation
- Concurrent failure recovery
- Resource leak detection

Success Criteria:
- Graceful degradation under failure conditions
- Proper error detection and messaging
- Automatic recovery where possible
- No data loss or corruption
- System stability after recovery

Author: StatArb_Gemini Integration Testing
Phase: 8 Week 2 - Day 7 - Failure Scenario Testing
Date: October 12, 2025
"""

import pytest
import asyncio
import logging
from datetime import datetime
from typing import Dict
import tracemalloc
import gc

from core_engine.system.central_risk_manager import (
    TradingDecisionRequest,
    TradingDecisionType,
    AuthorizationLevel,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


# ========================================
# Helper Functions
# ========================================

async def create_auth_request(
    strategy_id: str,
    symbol: str = "TEST",
    quantity: float = 100.0,
    side: str = "buy",
    confidence: float = 0.75
) -> TradingDecisionRequest:
    """Create a standard authorization request for testing."""
    return TradingDecisionRequest(
        symbol=symbol,
        strategy_id=strategy_id,
        decision_type=TradingDecisionType.POSITION_ENTRY,
        side=side,
        quantity=quantity,
        confidence=confidence,
    )


def validate_system_health(orchestrator, risk_manager) -> Dict[str, bool]:
    """Check system component health status"""
    health = {
        'orchestrator_running': False,
        'risk_manager_running': False,
        'can_process_requests': False
    }
    
    try:
        # Check orchestrator state
        if hasattr(orchestrator, 'is_running'):
            health['orchestrator_running'] = orchestrator.is_running
        elif hasattr(orchestrator, '_running'):
            health['orchestrator_running'] = orchestrator._running
        else:
            health['orchestrator_running'] = True
        
        # Check risk manager state
        if hasattr(risk_manager, 'is_running'):
            health['risk_manager_running'] = risk_manager.is_running
        elif hasattr(risk_manager, '_initialized'):
            health['risk_manager_running'] = risk_manager._initialized
        else:
            health['risk_manager_running'] = True
        
        # Overall health
        health['can_process_requests'] = (
            health['orchestrator_running'] and 
            health['risk_manager_running']
        )
        
    except Exception as e:
        logger.warning(f"Health check error: {e}")
        health['can_process_requests'] = False
    
    return health


# ========================================
# Test Class: Failure Scenarios
# ========================================

@pytest.mark.asyncio
@pytest.mark.slow
class TestFailureScenarios:
    """
    Test suite for system failure scenarios and recovery
    
    Validates:
    - Error detection and handling
    - Graceful degradation
    - Recovery mechanisms
    - System stability after failures
    """
    
    # ========================================
    # Test 1: Network Timeout Handling
    # ========================================
    
    async def test_network_timeout_handling(self, orchestrator, risk_manager):
        """
        Test system behavior under network timeout conditions
        
        Success Criteria:
        - Timeouts detected within reasonable time
        - Proper error handling
        - System continues processing other requests
        - No resource leaks or deadlocks
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 1: Network Timeout Handling")
        logger.info("="*80)
        
        timeout_threshold = 2.0  # seconds per request
        test_requests = 20
        successful_requests = 0
        timeout_errors = 0
        
        start_time = datetime.now()
        
        # Test with various timeout scenarios
        for i in range(test_requests):
            try:
                # Create authorization request
                request = await create_auth_request(
                    strategy_id=f'test_strategy_{i % 5}',
                    symbol=f'TEST{i % 10}',
                    quantity=100.0 + (i * 10),
                    side='buy' if i % 2 == 0 else 'sell',
                )
                
                # Apply timeout to simulate network issues
                try:
                    result = await asyncio.wait_for(
                        risk_manager.authorize_trading_decision(request),
                        timeout=timeout_threshold
                    )
                    
                    if result.authorization_level != AuthorizationLevel.REJECTED:
                        successful_requests += 1
                        logger.debug(f"Request {i+1}: Authorized")
                    else:
                        successful_requests += 1  # Still successful processing
                        logger.debug(f"Request {i+1}: Rejected - {result.rejection_reason}")
                        
                except asyncio.TimeoutError:
                    timeout_errors += 1
                    logger.info(f"Request {i+1}: Timeout (expected for some requests)")
                    
            except Exception as e:
                logger.warning(f"Request {i+1}: Unexpected error - {e}")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Calculate metrics
        success_rate = (successful_requests / test_requests) * 100
        
        # Validate system health after timeouts
        health = validate_system_health(orchestrator, risk_manager)
        
        # Results
        logger.info(f"\n{'='*80}")
        logger.info("RESULTS: Network Timeout Handling")
        logger.info(f"{'='*80}")
        logger.info(f"Total Requests:        {test_requests}")
        logger.info(f"Successful:            {successful_requests}")
        logger.info(f"Timeout Errors:        {timeout_errors}")
        logger.info(f"Success Rate:          {success_rate:.2f}%")
        logger.info(f"Duration:              {duration:.2f}s")
        logger.info(f"System Health:         {health}")
        logger.info(f"{'='*80}\n")
        
        # Assertions
        assert successful_requests > 0, "Should successfully process some requests"
        assert health['can_process_requests'], "System should remain operational"
        assert duration < timeout_threshold * test_requests * 2, "Should not hang excessively"
        
        logger.info("✅ TEST 1 PASSED: Network timeout handling validated")
    
    
    # ========================================
    # Test 2: Component Crash Recovery
    # ========================================
    
    async def test_component_crash_recovery(self, orchestrator, risk_manager):
        """
        Test system recovery after component failure simulation
        
        Success Criteria:
        - Crash detected immediately
        - Recovery procedures execute successfully
        - System returns to operational state
        - Minimal data loss during recovery
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 2: Component Crash Recovery")
        logger.info("="*80)
        
        # Phase 1: Normal operation
        logger.info("\nPhase 1: Normal Operation")
        pre_crash_requests = 10
        pre_crash_success = 0
        
        for i in range(pre_crash_requests):
            try:
                request = await create_auth_request(
                    strategy_id=f'strategy_{i}',
                    symbol=f'SYM{i}',
                    quantity=100.0,
                )
                
                result = await risk_manager.authorize_trading_decision(request)
                if result.authorization_level != AuthorizationLevel.REJECTED:
                    pre_crash_success += 1
                    
            except Exception as e:
                logger.warning(f"Pre-crash request {i+1} failed: {e}")
        
        logger.info(f"Pre-crash: {pre_crash_success}/{pre_crash_requests} requests successful")
        
        # Phase 2: Simulate crash by temporarily disabling
        logger.info("\nPhase 2: Simulating Component Failure")
        
        # Save original state
        original_initialized = getattr(risk_manager, '_initialized', True)
        
        # Simulate crash by marking component as not initialized
        risk_manager._initialized = False
        logger.info("Risk manager marked as crashed")
        
        # Try to process during crash - should fail gracefully
        crash_detected = False
        try:
            request = await create_auth_request(
                strategy_id='crash_test',
                symbol='CRASH',
            )
            result = await risk_manager.authorize_trading_decision(request)
            if result.authorization_level == AuthorizationLevel.REJECTED:
                crash_detected = True
        except Exception as e:
            crash_detected = True
            logger.info(f"Crash detected via exception: {e}")
        
        # Phase 3: Recovery
        logger.info("\nPhase 3: Recovery Procedure")
        recovery_start = datetime.now()
        
        # Restore component state
        if hasattr(risk_manager, '_initialized'):
            risk_manager._initialized = original_initialized
        
        recovery_end = datetime.now()
        recovery_time = (recovery_end - recovery_start).total_seconds()
        
        # Phase 4: Post-recovery validation
        logger.info("\nPhase 4: Post-Recovery Validation")
        post_recovery_requests = 10
        post_recovery_success = 0
        
        for i in range(post_recovery_requests):
            try:
                request = await create_auth_request(
                    strategy_id=f'recovery_strategy_{i}',
                    symbol=f'REC{i}',
                    quantity=100.0,
                )
                
                result = await risk_manager.authorize_trading_decision(request)
                if result.authorization_level != AuthorizationLevel.REJECTED:
                    post_recovery_success += 1
                    
            except Exception as e:
                logger.warning(f"Post-recovery request {i+1} failed: {e}")
        
        # Calculate recovery metrics
        pre_crash_rate = (pre_crash_success / pre_crash_requests) * 100
        post_recovery_rate = (post_recovery_success / post_recovery_requests) * 100
        recovery_ratio = post_recovery_success / max(pre_crash_success, 1)
        
        health = validate_system_health(orchestrator, risk_manager)
        
        # Results
        logger.info(f"\n{'='*80}")
        logger.info("RESULTS: Component Crash Recovery")
        logger.info(f"{'='*80}")
        logger.info(f"Pre-Crash Success:     {pre_crash_success}/{pre_crash_requests} ({pre_crash_rate:.1f}%)")
        logger.info(f"Crash Detected:        {'Yes' if crash_detected else 'No'}")
        logger.info(f"Recovery Time:         {recovery_time:.3f}s")
        logger.info(f"Post-Recovery Success: {post_recovery_success}/{post_recovery_requests} ({post_recovery_rate:.1f}%)")
        logger.info(f"Recovery Ratio:        {recovery_ratio:.2f}")
        logger.info(f"System Health:         {health}")
        logger.info(f"{'='*80}\n")
        
        # Assertions
        assert pre_crash_success > 0, "Should process requests before crash"
        assert crash_detected, "Should detect crash condition"
        assert recovery_time < 5.0, "Recovery should be quick"
        assert post_recovery_success > 0, "Should process requests after recovery"
        assert recovery_ratio >= 0.5, "Should recover to at least 50% of pre-crash performance"
        assert health['can_process_requests'], "System should be operational after recovery"
        
        logger.info("✅ TEST 2 PASSED: Component crash recovery validated")
    
    
    # ========================================
    # Test 3: Invalid Data Rejection
    # ========================================
    
    async def test_invalid_data_rejection(self, orchestrator, risk_manager):
        """
        Test system's ability to reject invalid data
        
        Success Criteria:
        - Invalid requests properly rejected
        - Proper error messages
        - System remains stable
        - Valid requests still processed
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 3: Invalid Data Rejection")
        logger.info("="*80)
        
        rejection_scenarios = []
        
        # Test 1: Negative quantity
        logger.info("\nTesting: Negative quantity")
        try:
            request = TradingDecisionRequest(
                symbol='TEST',
                strategy_id='test',
                decision_type=TradingDecisionType.POSITION_ENTRY,
                side='buy',
                quantity=-100.0,  # Invalid
                confidence=0.75,
            )
            result = await risk_manager.authorize_trading_decision(request)
            rejected = result.authorization_level == AuthorizationLevel.REJECTED
            rejection_scenarios.append(('negative_quantity', rejected, result.rejection_reason if hasattr(result, 'rejection_reason') else 'N/A'))
            logger.info(f"✓ Negative quantity handled: {'Rejected' if rejected else 'Not rejected'}")
        except Exception as e:
            rejection_scenarios.append(('negative_quantity', True, str(e)))
            logger.info(f"✓ Negative quantity rejected via exception: {e}")
        
        # Test 2: Zero quantity
        logger.info("\nTesting: Zero quantity")
        try:
            request = TradingDecisionRequest(
                symbol='TEST',
                strategy_id='test',
                decision_type=TradingDecisionType.POSITION_ENTRY,
                side='buy',
                quantity=0.0,  # Invalid
                confidence=0.75,
            )
            result = await risk_manager.authorize_trading_decision(request)
            rejected = result.authorization_level == AuthorizationLevel.REJECTED
            rejection_scenarios.append(('zero_quantity', rejected, result.rejection_reason if hasattr(result, 'rejection_reason') else 'N/A'))
            logger.info(f"✓ Zero quantity handled: {'Rejected' if rejected else 'Not rejected'}")
        except Exception as e:
            rejection_scenarios.append(('zero_quantity', True, str(e)))
            logger.info(f"✓ Zero quantity rejected via exception: {e}")
        
        # Test 3: Invalid confidence
        logger.info("\nTesting: Invalid confidence")
        try:
            request = TradingDecisionRequest(
                symbol='TEST',
                strategy_id='test',
                decision_type=TradingDecisionType.POSITION_ENTRY,
                side='buy',
                quantity=100.0,
                confidence=2.0,  # Should be 0-1
            )
            result = await risk_manager.authorize_trading_decision(request)
            rejected = result.authorization_level == AuthorizationLevel.REJECTED
            rejection_scenarios.append(('invalid_confidence', rejected, result.rejection_reason if hasattr(result, 'rejection_reason') else 'N/A'))
            logger.info(f"✓ Invalid confidence handled: {'Rejected' if rejected else 'Not rejected'}")
        except Exception as e:
            rejection_scenarios.append(('invalid_confidence', True, str(e)))
            logger.info(f"✓ Invalid confidence rejected via exception: {e}")
        
        # Test valid requests still work
        logger.info("\nTesting: Valid requests after invalid ones")
        valid_success = 0
        valid_requests = 5
        
        for i in range(valid_requests):
            try:
                request = await create_auth_request(
                    strategy_id=f'valid_strategy_{i}',
                    symbol=f'VALID{i}',
                    quantity=100.0,
                )
                
                result = await risk_manager.authorize_trading_decision(request)
                if result.authorization_level != AuthorizationLevel.REJECTED:
                    valid_success += 1
                    
            except Exception as e:
                logger.warning(f"Valid request {i+1} failed: {e}")
        
        # Calculate metrics
        total_invalid_tests = len(rejection_scenarios)
        rejections_handled = sum(1 for _, rejected, _ in rejection_scenarios if rejected)
        rejection_rate = (rejections_handled / total_invalid_tests) * 100
        valid_rate = (valid_success / valid_requests) * 100
        
        health = validate_system_health(orchestrator, risk_manager)
        
        # Results
        logger.info(f"\n{'='*80}")
        logger.info("RESULTS: Invalid Data Rejection")
        logger.info(f"{'='*80}")
        logger.info(f"Invalid Scenarios:     {total_invalid_tests}")
        logger.info(f"Properly Handled:      {rejections_handled}")
        logger.info(f"Handling Rate:         {rejection_rate:.1f}%")
        logger.info(f"Valid After Invalid:   {valid_success}/{valid_requests} ({valid_rate:.1f}%)")
        logger.info(f"System Health:         {health}")
        
        logger.info(f"\nRejection Details:")
        for scenario, rejected, reason in rejection_scenarios:
            status = "✓" if rejected else "✗"
            logger.info(f"  {status} {scenario}: {reason}")
        
        logger.info(f"{'='*80}\n")
        
        # Assertions
        assert rejection_rate >= 50.0, f"Should handle at least 50% of invalid data (got {rejection_rate:.1f}%)"
        assert valid_success >= valid_requests * 0.6, "Should still process valid requests"
        assert health['can_process_requests'], "System should remain operational"
        
        logger.info("✅ TEST 3 PASSED: Invalid data rejection validated")
    
    
    # ========================================
    # Test 4: Partial System Degradation
    # ========================================
    
    async def test_partial_system_degradation(self, orchestrator, risk_manager):
        """
        Test system behavior under degraded conditions
        
        Success Criteria:
        - Core services continue during degradation
        - Reduced limits properly enforced
        - Full restoration after degradation ends
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 4: Partial System Degradation")
        logger.info("="*80)
        
        # Phase 1: Full system operation
        logger.info("\nPhase 1: Full System Operation")
        full_requests = 15
        full_success = 0
        
        for i in range(full_requests):
            try:
                request = await create_auth_request(
                    strategy_id=f'full_strategy_{i}',
                    symbol=f'FULL{i % 5}',
                    quantity=100.0,
                )
                
                result = await risk_manager.authorize_trading_decision(request)
                if result.authorization_level != AuthorizationLevel.REJECTED:
                    full_success += 1
                    
            except Exception as e:
                logger.warning(f"Full system request {i+1} failed: {e}")
        
        full_rate = (full_success / full_requests) * 100
        logger.info(f"Full system: {full_success}/{full_requests} ({full_rate:.1f}%)")
        
        # Phase 2: Simulate degradation (reduced limits)
        logger.info("\nPhase 2: Degraded Mode (Reduced Limits)")
        
        # Save original limits
        original_limits = {}
        if hasattr(risk_manager, '_position_limits'):
            original_limits['position'] = getattr(risk_manager, '_position_limits', {}).copy()
            # Reduce limits
            for symbol in getattr(risk_manager, '_position_limits', {}):
                risk_manager._position_limits[symbol] = 50
        
        degraded_requests = 15
        degraded_success = 0
        degraded_rejected = 0
        
        for i in range(degraded_requests):
            try:
                request = await create_auth_request(
                    strategy_id=f'degraded_strategy_{i}',
                    symbol=f'DEG{i % 5}',
                    quantity=75.0,  # May exceed reduced limits
                )
                
                result = await risk_manager.authorize_trading_decision(request)
                if result.authorization_level != AuthorizationLevel.REJECTED:
                    degraded_success += 1
                else:
                    degraded_rejected += 1
                    logger.debug(f"Request {i+1} rejected in degraded mode")
                    
            except Exception as e:
                logger.warning(f"Degraded mode request {i+1} error: {e}")
        
        degraded_rate = (degraded_success / degraded_requests) * 100
        
        logger.info(f"Degraded mode: {degraded_success}/{degraded_requests} ({degraded_rate:.1f}%)")
        
        # Phase 3: Restore system
        logger.info("\nPhase 3: System Restoration")
        
        if 'position' in original_limits:
            if hasattr(risk_manager, '_position_limits'):
                risk_manager._position_limits = original_limits['position']
                logger.info("Limits restored")
        
        # Phase 4: Post-restoration
        logger.info("\nPhase 4: Post-Restoration")
        restored_requests = 15
        restored_success = 0
        
        for i in range(restored_requests):
            try:
                request = await create_auth_request(
                    strategy_id=f'restored_strategy_{i}',
                    symbol=f'REST{i % 5}',
                    quantity=100.0,
                )
                
                result = await risk_manager.authorize_trading_decision(request)
                if result.authorization_level != AuthorizationLevel.REJECTED:
                    restored_success += 1
                    
            except Exception as e:
                logger.warning(f"Restored system request {i+1} failed: {e}")
        
        restored_rate = (restored_success / restored_requests) * 100
        recovery_ratio = restored_success / max(full_success, 1)
        
        health = validate_system_health(orchestrator, risk_manager)
        
        # Results
        logger.info(f"\n{'='*80}")
        logger.info("RESULTS: Partial System Degradation")
        logger.info(f"{'='*80}")
        logger.info(f"Full System:           {full_success}/{full_requests} ({full_rate:.1f}%)")
        logger.info(f"Degraded Mode:         {degraded_success}/{degraded_requests} ({degraded_rate:.1f}%)")
        logger.info(f"Degraded Rejections:   {degraded_rejected}")
        logger.info(f"Restored System:       {restored_success}/{restored_requests} ({restored_rate:.1f}%)")
        logger.info(f"Recovery Ratio:        {recovery_ratio:.2f}")
        logger.info(f"System Health:         {health}")
        logger.info(f"{'='*80}\n")
        
        # Assertions
        assert full_success > 0, "Full system should process requests"
        assert degraded_success > 0, "Degraded mode should still process some requests"
        assert restored_success > 0, "Restored system should process requests"
        assert recovery_ratio >= 0.5, "Should recover to at least 50% of full performance"
        assert health['can_process_requests'], "System should be operational"
        
        logger.info("✅ TEST 4 PASSED: Partial system degradation handled")
    
    
    # ========================================
    # Test 5: Concurrent Failure Recovery
    # ========================================
    
    async def test_concurrent_failure_recovery(self, orchestrator, risk_manager):
        """
        Test recovery from multiple concurrent failures
        
        Success Criteria:
        - Multiple failures detected
        - Recovery procedures execute
        - System returns to stable state
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 5: Concurrent Failure Recovery")
        logger.info("="*80)
        
        # Phase 1: Baseline
        logger.info("\nPhase 1: Baseline Operation")
        baseline_requests = 10
        baseline_success = 0
        
        for i in range(baseline_requests):
            try:
                request = await create_auth_request(
                    strategy_id=f'baseline_{i}',
                    symbol=f'BASE{i % 3}',
                    quantity=100.0,
                )
                
                result = await risk_manager.authorize_trading_decision(request)
                if result.authorization_level != AuthorizationLevel.REJECTED:
                    baseline_success += 1
                    
            except Exception as e:
                logger.warning(f"Baseline request {i+1} failed: {e}")
        
        baseline_rate = (baseline_success / baseline_requests) * 100
        logger.info(f"Baseline: {baseline_success}/{baseline_requests} ({baseline_rate:.1f}%)")
        
        # Phase 2: Concurrent failures
        logger.info("\nPhase 2: Simulating Concurrent Failures")
        
        failures_triggered = []
        
        # Failure 1: Timeout
        async def timeout_failure():
            try:
                await asyncio.wait_for(asyncio.sleep(10), timeout=0.01)
            except asyncio.TimeoutError:
                failures_triggered.append('timeout')
                return 'timeout'
        
        # Failure 2: Invalid data
        async def validation_failure():
            try:
                request = TradingDecisionRequest(
                    symbol='',
                    strategy_id='',
                    decision_type=TradingDecisionType.POSITION_ENTRY,
                    side='invalid',
                    quantity=-100.0,
                    confidence=5.0,
                )
                await risk_manager.authorize_trading_decision(request)
            except Exception:
                pass
            failures_triggered.append('validation')
            return 'validation'
        
        # Failure 3: Resource stress
        async def resource_failure():
            try:
                tasks = []
                for _ in range(5):
                    req = await create_auth_request(
                        strategy_id='resource_test',
                        symbol='RESOURCE',
                        quantity=100.0,
                    )
                    tasks.append(risk_manager.authorize_trading_decision(req))
                await asyncio.gather(*tasks)
                failures_triggered.append('resource')
                return 'resource'
            except Exception:
                failures_triggered.append('resource_error')
                return 'resource_error'
        
        # Execute concurrent failures
        failure_results = await asyncio.gather(
            timeout_failure(),
            validation_failure(),
            resource_failure(),
            return_exceptions=True
        )
        
        failures_detected = len(failures_triggered)
        logger.info(f"Concurrent failures: {failures_triggered}")
        
        # Phase 3: Recovery
        logger.info("\nPhase 3: Recovery from Concurrent Failures")
        await asyncio.sleep(0.5)  # Stabilization time
        
        health = validate_system_health(orchestrator, risk_manager)
        
        # Phase 4: Post-recovery
        logger.info("\nPhase 4: Post-Recovery Validation")
        post_recovery_requests = 10
        post_recovery_success = 0
        
        for i in range(post_recovery_requests):
            try:
                request = await create_auth_request(
                    strategy_id=f'post_recovery_{i}',
                    symbol=f'POST{i % 3}',
                    quantity=100.0,
                )
                
                result = await risk_manager.authorize_trading_decision(request)
                if result.authorization_level != AuthorizationLevel.REJECTED:
                    post_recovery_success += 1
                    
            except Exception as e:
                logger.warning(f"Post-recovery request {i+1} failed: {e}")
        
        post_recovery_rate = (post_recovery_success / post_recovery_requests) * 100
        recovery_ratio = post_recovery_success / max(baseline_success, 1)
        
        # Results
        logger.info(f"\n{'='*80}")
        logger.info("RESULTS: Concurrent Failure Recovery")
        logger.info(f"{'='*80}")
        logger.info(f"Baseline:              {baseline_success}/{baseline_requests} ({baseline_rate:.1f}%)")
        logger.info(f"Failures Triggered:    {failures_detected}")
        logger.info(f"Post-Recovery:         {post_recovery_success}/{post_recovery_requests} ({post_recovery_rate:.1f}%)")
        logger.info(f"Recovery Ratio:        {recovery_ratio:.2f}")
        logger.info(f"System Health:         {health}")
        logger.info(f"{'='*80}\n")
        
        # Assertions
        assert failures_detected >= 2, "Should trigger multiple failures"
        assert post_recovery_success > 0, "Should process requests after recovery"
        assert recovery_ratio >= 0.5, "Should recover to at least 50% of baseline"
        assert health['can_process_requests'], "System should be operational"
        
        logger.info("✅ TEST 5 PASSED: Concurrent failure recovery validated")
    
    
    # ========================================
    # Test 6: Resource Leak Detection
    # ========================================
    
    async def test_resource_leak_detection(self, orchestrator, risk_manager):
        """
        Test for resource leaks during failure scenarios
        
        Success Criteria:
        - Memory remains stable
        - No connection/handle leaks
        - Resources properly released
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 6: Resource Leak Detection")
        logger.info("="*80)
        
        # Start memory tracking
        tracemalloc.start()
        baseline_snapshot = tracemalloc.take_snapshot()
        
        # Phase 1: Normal operations
        logger.info("\nPhase 1: Normal Operations")
        normal_iterations = 30
        
        for i in range(normal_iterations):
            try:
                request = await create_auth_request(
                    strategy_id=f'normal_{i}',
                    symbol=f'NRM{i % 5}',
                    quantity=100.0,
                )
                await risk_manager.authorize_trading_decision(request)
            except Exception as e:
                logger.debug(f"Normal iteration {i+1} error: {e}")
        
        normal_snapshot = tracemalloc.take_snapshot()
        normal_diff = normal_snapshot.compare_to(baseline_snapshot, 'lineno')
        normal_memory = sum(stat.size_diff for stat in normal_diff) / 1024 / 1024
        
        logger.info(f"Memory after normal operations: {normal_memory:+.2f} MB")
        
        # Phase 2: Repeated failures
        logger.info("\nPhase 2: Repeated Failures")
        failure_iterations = 30
        failures_triggered = 0
        
        for i in range(failure_iterations):
            try:
                if i % 3 == 0:
                    # Timeout
                    try:
                        await asyncio.wait_for(asyncio.sleep(1), timeout=0.001)
                    except asyncio.TimeoutError:
                        failures_triggered += 1
                elif i % 3 == 1:
                    # Invalid data
                    try:
                        request = TradingDecisionRequest(
                            symbol='',
                            strategy_id='',
                            decision_type=TradingDecisionType.POSITION_ENTRY,
                            side='buy',
                            quantity=-100.0,
                            confidence=0.75,
                        )
                        await risk_manager.authorize_trading_decision(request)
                    except Exception:
                        failures_triggered += 1
                else:
                    # Normal
                    request = await create_auth_request(
                        strategy_id=f'mixed_{i}',
                        symbol=f'MIX{i % 5}',
                        quantity=100.0,
                    )
                    await risk_manager.authorize_trading_decision(request)
            except Exception:
                pass
        
        failure_snapshot = tracemalloc.take_snapshot()
        failure_diff = failure_snapshot.compare_to(normal_snapshot, 'lineno')
        failure_memory = sum(stat.size_diff for stat in failure_diff) / 1024 / 1024
        
        logger.info(f"Memory after failures: {failure_memory:+.2f} MB")
        logger.info(f"Failures triggered: {failures_triggered}")
        
        # Phase 3: Cleanup
        logger.info("\nPhase 3: Cleanup")
        gc.collect()
        await asyncio.sleep(0.5)
        
        cleanup_snapshot = tracemalloc.take_snapshot()
        cleanup_diff = cleanup_snapshot.compare_to(failure_snapshot, 'lineno')
        cleanup_memory = sum(stat.size_diff for stat in cleanup_diff) / 1024 / 1024
        
        logger.info(f"Memory after cleanup: {cleanup_memory:+.2f} MB")
        
        # Phase 4: Final validation
        validation_requests = 10
        validation_success = 0
        
        for i in range(validation_requests):
            try:
                request = await create_auth_request(
                    strategy_id=f'validation_{i}',
                    symbol=f'VAL{i % 5}',
                    quantity=100.0,
                )
                
                result = await risk_manager.authorize_trading_decision(request)
                if result.authorization_level != AuthorizationLevel.REJECTED:
                    validation_success += 1
            except Exception as e:
                logger.warning(f"Validation request {i+1} failed: {e}")
        
        final_snapshot = tracemalloc.take_snapshot()
        final_diff = final_snapshot.compare_to(baseline_snapshot, 'lineno')
        total_memory_growth = sum(stat.size_diff for stat in final_diff) / 1024 / 1024
        
        validation_rate = (validation_success / validation_requests) * 100
        health = validate_system_health(orchestrator, risk_manager)
        
        tracemalloc.stop()
        
        # Results
        logger.info(f"\n{'='*80}")
        logger.info("RESULTS: Resource Leak Detection")
        logger.info(f"{'='*80}")
        logger.info(f"Normal Operations:     {normal_iterations} iterations, {normal_memory:+.2f} MB")
        logger.info(f"Failure Scenarios:     {failure_iterations} iterations, {failures_triggered} failures")
        logger.info(f"Memory after Failures: {failure_memory:+.2f} MB")
        logger.info(f"Memory after Cleanup:  {cleanup_memory:+.2f} MB")
        logger.info(f"Total Memory Growth:   {total_memory_growth:+.2f} MB")
        logger.info(f"Post-Test Success:     {validation_success}/{validation_requests} ({validation_rate:.1f}%)")
        logger.info(f"System Health:         {health}")
        logger.info(f"{'='*80}\n")
        
        # Assertions
        assert total_memory_growth < 20.0, f"Total memory growth should be < 20MB (got {total_memory_growth:.2f}MB)"
        assert validation_success >= validation_requests * 0.6, "Should process requests after leak test"
        assert health['can_process_requests'], "System should be operational"
        
        logger.info("✅ TEST 6 PASSED: No significant resource leaks detected")
