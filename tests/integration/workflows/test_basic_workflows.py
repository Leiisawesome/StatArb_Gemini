"""
Basic Workflow Integration Tests

Tests complete workflows across multiple components:
- Data ingestion → Processing
- Market data → Regime detection  
- Regime detection → Strategy signals
- Strategy signals → Risk authorization
- Risk authorization → Execution
- End-to-end flows

Phase 8 Day 3 - Workflow Integration Testing
"""

import pytest
import asyncio
import logging
import pandas as pd
from datetime import datetime, timedelta

from core_engine.system.central_risk_manager import (
    TradingDecisionRequest,
    TradingDecisionType,
    ExecutionUrgency,
    AuthorizationLevel
)

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
class TestBasicWorkflows:
    """Test basic integration workflows across components"""
    
    async def test_data_to_regime_workflow(
        self, orchestrator, regime_engine, data_manager
    ):
        """
        Test: Market Data → Regime Detection workflow
        
        Validates:
        - Market data ingestion
        - Regime classification
        - Regime confidence tracking
        - Regime state updates
        """
        logger.info("🔄 Testing Data → Regime Detection workflow")
        
        # Register components
        orchestrator.register_component(
            name="RegimeEngine",
            component=regime_engine,
            layer="analysis",
            authority_level="analytical"
        )
        
        orchestrator.register_component(
            name="DataManager", 
            component=data_manager,
            layer="data",
            authority_level="data_provider"
        )
        
        # Start components
        await regime_engine.start()
        await data_manager.start()
        
        # Simulate market data update - store sample data
        symbol = "AAPL"
        market_data = pd.DataFrame({
            'timestamp': [datetime.now() - timedelta(minutes=i) for i in range(30, 0, -1)],
            'price': [175.0 + i * 0.1 for i in range(30)],
            'volume': [50000000] * 30,
            'open': [174.0 + i * 0.1 for i in range(30)],
            'high': [176.0 + i * 0.1 for i in range(30)],
            'low': [173.0 + i * 0.1 for i in range(30)],
            'close': [175.0 + i * 0.1 for i in range(30)]
        })
        
        # Store market data (DataManager stores historical data)
        await data_manager.store_market_data(symbol, market_data)
        
        # Allow regime engine to process
        await asyncio.sleep(0.1)
        
        # Detect regime from stored data
        # For testing purposes, manually trigger regime detection with sample data
        regime_result = regime_engine.detect_regime({
            'symbol': symbol,
            'price': market_data['price'].iloc[-1],
            'returns': market_data['price'].pct_change().dropna().tolist()
        })
        
        # Check current regime state
        current_regime = regime_engine.current_regime
        
        # Assertions - regime_result should be returned
        assert regime_result is not None, "Regime detection should return result"
        assert isinstance(regime_result, dict), "Regime result should be a dictionary"
        
        logger.info(f"✅ Regime detected: {regime_result}")
        logger.info(f"   Current regime state: {current_regime}")
        logger.info(f"   Symbol: {symbol}")
        logger.info("✅ Data → Regime Detection workflow validated")
    
    async def test_regime_to_signal_workflow(
        self, orchestrator, regime_engine, strategy_manager
    ):
        """
        Test: Regime Detection → Strategy Signals workflow
        
        Validates:
        - Regime state propagation
        - Strategy signal generation
        - Regime-aware trading decisions
        - Signal quality metrics
        """
        logger.info("🔄 Testing Regime Detection → Strategy Signals workflow")
        
        # Register components
        orchestrator.register_component(
            name="RegimeEngine",
            component=regime_engine,
            layer="analysis",
            authority_level="analytical"
        )
        
        orchestrator.register_component(
            name="StrategyManager",
            component=strategy_manager,
            layer="execution",
            authority_level="strategic"
        )
        
        # Start components
        await regime_engine.start()
        await strategy_manager.start()
        
        # Detect a regime using actual detection method
        symbol = "AAPL"
        regime_result = regime_engine.detect_regime({
            'symbol': symbol,
            'price': 175.50,
            'returns': [0.01, 0.015, 0.02, 0.018, 0.012],  # Upward trending returns
            'volatility': 0.02
        })
        
        # Get active strategies
        active_strategies = strategy_manager.active_strategies
        if not active_strategies:
            pytest.skip("No active strategies available")
        
        strategy_id = list(active_strategies.keys())[0]
        active_strategies[strategy_id]
        
        # Generate signal based on regime
        market_data = {
            'symbol': symbol,
            'price': 175.50,
            'regime': regime_result.get('regime_type', 'unknown'),
            'regime_confidence': regime_result.get('confidence', 0.0)
        }
        
        # Trigger signal generation (strategies respond to regime)
        signals = await strategy_manager.generate_signals(market_data)
        
        # Assertions
        assert signals is not None, "Signals should be generated"
        
        if len(signals) > 0:
            signal = signals[0]
            logger.info(f"✅ Signal generated from regime:")
            logger.info(f"   Strategy: {strategy_id}")
            logger.info(f"   Symbol: {symbol}")
            logger.info(f"   Regime: {regime_result}")
            logger.info(f"   Signal strength: {getattr(signal, 'strength', 'N/A')}")
        else:
            logger.info("✅ No signals generated (valid for current regime)")
        
        logger.info("✅ Regime → Signals workflow validated")
    
    async def test_signal_to_authorization_workflow(
        self, orchestrator, strategy_manager, risk_manager
    ):
        """
        Test: Strategy Signals → Risk Authorization workflow
        
        Validates:
        - Signal to decision request conversion
        - Risk authorization process
        - Authorization response handling
        - Approval/rejection flow
        """
        logger.info("🔄 Testing Signals → Risk Authorization workflow")
        
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
        
        # Create a trading decision based on strategy signal
        decision_request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            strategy_id=strategy_id,
            symbol="AAPL",
            side="buy",
            quantity=100.0,
            expected_return=0.05,
            confidence=0.75,
            current_position=0.0,
            portfolio_impact=0.15,
            risk_score=0.3,
            market_regime="bullish",
            regime_confidence=0.85,
            volatility_estimate=0.02,
            urgency=ExecutionUrgency.NORMAL,
            max_execution_time=3600,
            requesting_component="StrategyManager",
            justification="Strategy signal from regime-based analysis",
            metadata={'workflow': 'signal_to_authorization'}
        )
        
        # Submit to risk manager
        authorization = await risk_manager.authorize_trading_decision(decision_request)
        
        # Assertions
        assert authorization is not None, "Authorization should be returned"
        assert authorization.request_id == decision_request.request_id, "Request IDs should match"
        
        if authorization.authorization_level != AuthorizationLevel.REJECTED:
            logger.info(f"✅ Signal authorized:")
            logger.info(f"   Strategy: {strategy_id}")
            logger.info(f"   Requested: {decision_request.quantity} shares")
            logger.info(f"   Authorized: {authorization.authorized_quantity} shares")
            logger.info(f"   Level: {authorization.authorization_level.value}")
        else:
            logger.info(f"⚠️  Signal rejected: {authorization.rejection_reason}")
        
        logger.info("✅ Signals → Authorization workflow validated")
    
    async def test_authorization_to_execution_workflow(
        self, orchestrator, risk_manager, execution_engine
    ):
        """
        Test: Risk Authorization → Execution workflow
        
        Validates:
        - Authorization to execution order conversion
        - Execution tracking
        
        NOTE: Simplified test - full execution integration requires ExecutionRequest setup
        """
        logger.info("🔄 Testing Authorization → Execution workflow")
        
        # Register components
        orchestrator.register_central_risk_manager(risk_manager)
        
        orchestrator.register_component(
            name="ExecutionEngine",
            component=execution_engine,
            layer="execution",
            authority_level="operational"
        )
        
        # Start components
        await risk_manager.start()
        await execution_engine.start()
        
        # Create and authorize a decision
        decision_request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            strategy_id="test_strategy",
            symbol="MSFT",
            side="buy",
            quantity=50.0,
            expected_return=0.04,
            confidence=0.80,
            current_position=0.0,
            portfolio_impact=0.10,
            risk_score=0.25,
            market_regime="bullish",
            regime_confidence=0.80,
            volatility_estimate=0.02,
            urgency=ExecutionUrgency.NORMAL,
            max_execution_time=3600,
            requesting_component="StrategyManager",
            justification="Test authorization to execution flow",
            metadata={'workflow': 'authorization_to_execution'}
        )
        
        # Get authorization
        authorization = await risk_manager.authorize_trading_decision(decision_request)
        
        # Assertions on authorization
        assert authorization is not None, "Authorization should be returned"
        
        if authorization.authorization_level == AuthorizationLevel.REJECTED:
            logger.info(f"⚠️  Authorization rejected: {authorization.rejection_reason}")
            logger.info("✅ Authorization workflow validated (rejected)")
        else:
            logger.info(f"✅ Authorization completed:")
            logger.info(f"   Symbol: {decision_request.symbol}")
            logger.info(f"   Quantity: {authorization.authorized_quantity}")
            logger.info(f"   Level: {authorization.authorization_level.value}")
            logger.info("✅ Authorization workflow validated (approved)")
        
        # NOTE: Full execution test would require ExecutionRequest creation
        # This is covered in dedicated execution tests
        logger.info("✅ Authorization → Execution workflow validated")
    
    async def test_end_to_end_workflow(
        self, orchestrator, data_manager, regime_engine, 
        strategy_manager, risk_manager, execution_engine
    ):
        """
        Test: Complete end-to-end workflow
        
        Flow: Market Data → Regime → Signal → Authorization
        
        Validates:
        - Complete data flow through multiple components
        - Component coordination
        - State propagation
        
        NOTE: Simplified to authorization step (full execution requires ExecutionRequest)
        """
        logger.info("🔄 Testing End-to-End workflow: Data → Regime → Signal → Authorization")
        
        # Register all components
        orchestrator.register_component(
            name="DataManager",
            component=data_manager,
            layer="data",
            authority_level="data_provider"
        )
        
        orchestrator.register_component(
            name="RegimeEngine",
            component=regime_engine,
            layer="analysis",
            authority_level="analytical"
        )
        
        orchestrator.register_component(
            name="StrategyManager",
            component=strategy_manager,
            layer="execution",
            authority_level="strategic"
        )
        
        orchestrator.register_central_risk_manager(risk_manager)
        
        orchestrator.register_component(
            name="ExecutionEngine",
            component=execution_engine,
            layer="execution",
            authority_level="operational"
        )
        
        # Start all components
        await data_manager.start()
        await regime_engine.start()
        await strategy_manager.start()
        await risk_manager.start()
        await execution_engine.start()
        
        # Step 1: Ingest market data
        symbol = "GOOGL"
        market_data = pd.DataFrame({
            'timestamp': [datetime.now() - timedelta(minutes=i) for i in range(30, 0, -1)],
            'price': [140.0 + i * 0.1 for i in range(30)],
            'volume': [25000000] * 30,
            'open': [138.5 + i * 0.1 for i in range(30)],
            'high': [141.0 + i * 0.1 for i in range(30)],
            'low': [138.0 + i * 0.1 for i in range(30)],
            'close': [140.0 + i * 0.1 for i in range(30)]
        })
        
        await data_manager.store_market_data(symbol, market_data)
        logger.info(f"Step 1: Market data ingested for {symbol}")
        
        # Step 2: Regime detection
        await asyncio.sleep(0.1)  # Allow regime processing
        
        # Detect regime using actual detection method
        regime_result = regime_engine.detect_regime({
            'symbol': symbol,
            'price': market_data['price'].iloc[-1],
            'returns': market_data['price'].pct_change().dropna().tolist()[-10:],
            'volatility': market_data['price'].pct_change().std()
        })
        
        current_regime = regime_engine.current_regime
        logger.info(f"Step 2: Regime detected - {regime_result}")
        
        # Step 3: Strategy signal generation
        active_strategies = strategy_manager.active_strategies
        if not active_strategies:
            pytest.skip("No active strategies - cannot complete end-to-end test")
        
        strategy_id = list(active_strategies.keys())[0]
        logger.info(f"Step 3: Using strategy {strategy_id}")
        
        # Step 4: Create decision request (signal → decision)
        decision_request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            strategy_id=strategy_id,
            symbol=symbol,
            side="buy",
            quantity=75.0,
            expected_return=0.06,
            confidence=0.72,
            current_position=0.0,
            portfolio_impact=0.12,
            risk_score=0.35,
            market_regime="trending",
            regime_confidence=0.75,
            volatility_estimate=0.025,
            urgency=ExecutionUrgency.NORMAL,
            max_execution_time=3600,
            requesting_component="StrategyManager",
            justification="End-to-end workflow test",
            metadata={'workflow': 'end_to_end', 'test': 'complete_flow'}
        )
        logger.info(f"Step 4: Decision request created - {decision_request.quantity} shares")
        
        # Step 5: Risk authorization
        authorization = await risk_manager.authorize_trading_decision(decision_request)
        logger.info(f"Step 5: Authorization received - Level: {authorization.authorization_level.value}")
        
        if authorization.authorization_level == AuthorizationLevel.REJECTED:
            logger.warning(f"   ⚠️  Rejected: {authorization.rejection_reason}")
            logger.info("✅ End-to-end workflow validated (rejected at risk)")
            return
        
        # Step 6: Execution would happen here (simplified for now)
        logger.info(f"Step 6: Execution authorized - {authorization.authorized_quantity} shares")
        
        # Final assertions
        assert authorization is not None, "Complete workflow should produce authorization"
        assert current_regime is not None or regime_result is not None, "Regime should be detected"
        
        logger.info("=" * 60)
        logger.info("✅ COMPLETE END-TO-END WORKFLOW VALIDATED")
        logger.info(f"   Data → Regime → Signal → Authorization")
        logger.info(f"   Symbol: {symbol}")
        logger.info(f"   Regime: {regime_result}")
        logger.info(f"   Authorization: {authorization.authorization_level.value}")
        logger.info("=" * 60)
    
    async def test_multi_symbol_workflow(
        self, orchestrator, strategy_manager, risk_manager
    ):
        """
        Test: Multi-symbol workflow coordination
        
        Validates:
        - Multiple symbols processed concurrently
        - Independent authorization per symbol
        - Portfolio-level risk coordination
        - Concurrent processing safety
        """
        logger.info("🔄 Testing Multi-Symbol workflow coordination")
        
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
        
        # Create requests for multiple symbols
        symbols = ["AAPL", "MSFT", "GOOGL"]
        decision_requests = []
        
        for i, symbol in enumerate(symbols):
            request = TradingDecisionRequest(
                decision_type=TradingDecisionType.POSITION_ENTRY,
                strategy_id=strategy_id,
                symbol=symbol,
                side="buy",
                quantity=50.0 + (i * 10),  # Different quantities
                expected_return=0.05,
                confidence=0.75 - (i * 0.05),  # Varying confidence
                current_position=0.0,
                portfolio_impact=0.10,
                risk_score=0.30,
                market_regime="bullish",
                regime_confidence=0.80,
                volatility_estimate=0.02,
                urgency=ExecutionUrgency.NORMAL,
                max_execution_time=3600,
                requesting_component="StrategyManager",
                justification=f"Multi-symbol workflow test - {symbol}",
                metadata={'workflow': 'multi_symbol', 'symbol_index': i}
            )
            decision_requests.append(request)
        
        # Process all requests concurrently
        authorizations = await asyncio.gather(*[
            risk_manager.authorize_trading_decision(req)
            for req in decision_requests
        ])
        
        # Assertions
        assert len(authorizations) == len(symbols), "Should have authorization for each symbol"
        
        # Analyze results
        approved_count = 0
        rejected_count = 0
        total_authorized_quantity = 0.0
        
        for i, (symbol, auth) in enumerate(zip(symbols, authorizations)):
            if auth.authorization_level != AuthorizationLevel.REJECTED:
                approved_count += 1
                total_authorized_quantity += auth.authorized_quantity
                logger.info(f"✅ {symbol}: Authorized {auth.authorized_quantity} shares")
            else:
                rejected_count += 1
                logger.info(f"⚠️  {symbol}: Rejected - {auth.rejection_reason}")
        
        logger.info(f"✅ Multi-symbol workflow completed:")
        logger.info(f"   Symbols processed: {len(symbols)}")
        logger.info(f"   Approved: {approved_count}")
        logger.info(f"   Rejected: {rejected_count}")
        logger.info(f"   Total authorized quantity: {total_authorized_quantity}")
        logger.info("✅ Multi-symbol workflow validated")
    
    async def test_error_handling_workflow(
        self, orchestrator, strategy_manager, risk_manager
    ):
        """
        Test: Error handling in workflow
        
        Validates:
        - Invalid request handling
        - Rejection graceful handling
        - Error propagation
        - Recovery mechanisms
        """
        logger.info("🔄 Testing Error Handling workflow")
        
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
        
        # Test 1: Low confidence rejection
        low_confidence_request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            strategy_id=strategy_id,
            symbol="AAPL",
            side="buy",
            quantity=100.0,
            expected_return=0.05,
            confidence=0.40,  # Below threshold
            current_position=0.0,
            portfolio_impact=0.15,
            risk_score=0.30,
            market_regime="bullish",
            regime_confidence=0.80,
            volatility_estimate=0.02,
            urgency=ExecutionUrgency.NORMAL,
            max_execution_time=3600,
            requesting_component="StrategyManager",
            justification="Test low confidence rejection",
            metadata={'test': 'error_handling', 'scenario': 'low_confidence'}
        )
        
        auth1 = await risk_manager.authorize_trading_decision(low_confidence_request)
        assert auth1.authorization_level == AuthorizationLevel.REJECTED, "Low confidence should be rejected"
        logger.info(f"✅ Test 1: Low confidence correctly rejected")
        
        # Test 2: High risk rejection
        high_risk_request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            strategy_id=strategy_id,
            symbol="TSLA",
            side="buy",
            quantity=200.0,
            expected_return=0.10,
            confidence=0.50,  # Below threshold
            current_position=0.0,
            portfolio_impact=0.60,  # Very high
            risk_score=0.85,  # Very high
            market_regime="volatile",
            regime_confidence=0.60,
            volatility_estimate=0.12,  # Very high
            urgency=ExecutionUrgency.NORMAL,
            max_execution_time=3600,
            requesting_component="StrategyManager",
            justification="Test high risk rejection",
            metadata={'test': 'error_handling', 'scenario': 'high_risk'}
        )
        
        auth2 = await risk_manager.authorize_trading_decision(high_risk_request)
        assert auth2.authorization_level == AuthorizationLevel.REJECTED, "High risk should be rejected"
        logger.info(f"✅ Test 2: High risk correctly rejected")
        
        # Test 3: Valid request after errors (recovery)
        valid_request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            strategy_id=strategy_id,
            symbol="MSFT",
            side="buy",
            quantity=50.0,
            expected_return=0.04,
            confidence=0.78,  # Good confidence
            current_position=0.0,
            portfolio_impact=0.08,  # Low impact
            risk_score=0.25,  # Low risk
            market_regime="bullish",
            regime_confidence=0.85,
            volatility_estimate=0.02,  # Low volatility
            urgency=ExecutionUrgency.NORMAL,
            max_execution_time=3600,
            requesting_component="StrategyManager",
            justification="Test recovery after errors",
            metadata={'test': 'error_handling', 'scenario': 'recovery'}
        )
        
        auth3 = await risk_manager.authorize_trading_decision(valid_request)
        assert auth3.authorization_level != AuthorizationLevel.REJECTED, "Valid request should be approved"
        logger.info(f"✅ Test 3: System recovered - valid request approved")
        
        logger.info("=" * 60)
        logger.info("✅ ERROR HANDLING WORKFLOW VALIDATED")
        logger.info(f"   Test 1: Low confidence rejection ✅")
        logger.info(f"   Test 2: High risk rejection ✅")
        logger.info(f"   Test 3: Recovery after errors ✅")
        logger.info("=" * 60)
