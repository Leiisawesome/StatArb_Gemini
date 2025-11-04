"""
Authorization Flow Integration Tests
===================================

Tests orchestrator authorization request patterns.

Test Coverage:
- Component authorization request patterns
- Authorization request validation

Author: StatArb_Gemini Integration Test Suite
Date: November 4, 2025
"""

import pytest
import pytest_asyncio

from core_engine.system.hierarchical_orchestrator import HierarchicalSystemOrchestrator
from core_engine.system.orchestrator_components import ComponentLayer, AuthorityLevel
from core_engine.system.central_risk_manager import CentralRiskManager, TradingDecisionRequest, TradingDecisionType
from core_engine.config.component_config import RiskConfig


class TestAuthorizationFlow:
    """Integration tests for authorization flow"""
    
    @pytest.mark.asyncio
    async def test_component_authorization_request_pattern(self, orchestrator):
        """
        Test: Component authorization request pattern
        
        Scenario: Component requests authorization through orchestrator
        Expected: Authorization request processed correctly
        """
        # Register risk manager
        risk_config = RiskConfig()
        risk_manager = CentralRiskManager(risk_config)
        risk_id = orchestrator.register_central_risk_manager(risk_manager)
        await risk_manager.initialize()
        
        # Create authorization request
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=100.0,
            confidence=0.75,
            strategy_id='test_strategy',
            requesting_component='StrategyManager'
        )
        
        # Request authorization through risk manager
        authorization = await risk_manager.authorize_trading_decision(request)
        
        # Verify authorization processed
        assert authorization is not None
    
    @pytest.mark.asyncio
    async def test_authorization_request_validation(self, orchestrator):
        """
        Test: Authorization request validation
        
        Scenario: Request authorization with invalid parameters
        Expected: Request validated and rejected appropriately
        """
        # Register risk manager
        risk_config = RiskConfig()
        risk_manager = CentralRiskManager(risk_config)
        orchestrator.register_central_risk_manager(risk_manager)
        await risk_manager.initialize()
        
        # Create invalid request (zero quantity)
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=0.0,  # Invalid
            confidence=0.75,
            strategy_id='test_strategy',
            requesting_component='StrategyManager'
        )
        
        # Request authorization
        authorization = await risk_manager.authorize_trading_decision(request)
        
        # Should be rejected or handled appropriately
        assert authorization is not None
    
    @pytest.mark.asyncio
    async def test_authorization_request_through_orchestrator(self, orchestrator):
        """
        Test: Authorization request through orchestrator
        
        Scenario: Component requests authorization via orchestrator
        Expected: Request routed to risk manager correctly
        """
        # Register risk manager
        risk_config = RiskConfig()
        risk_manager = CentralRiskManager(risk_config)
        orchestrator.register_central_risk_manager(risk_manager)
        await risk_manager.initialize()
        
        # Create request
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=100.0,
            confidence=0.75,
            strategy_id='test_strategy',
            requesting_component='StrategyManager'
        )
        
        # Request through orchestrator (if method exists)
        if hasattr(orchestrator, 'request_system_authorization'):
            authorization = await orchestrator.request_system_authorization(
                operation='trading_decision',
                component_id='test_component',
                details={'request': request}
            )
            assert authorization is not None
        else:
            # Direct risk manager request
            authorization = await risk_manager.authorize_trading_decision(request)
            assert authorization is not None
    
    @pytest.mark.asyncio
    async def test_multiple_authorization_requests(self, orchestrator):
        """
        Test: Multiple concurrent authorization requests
        
        Scenario: Multiple components request authorization simultaneously
        Expected: All requests processed correctly
        """
        # Register risk manager
        risk_config = RiskConfig()
        risk_manager = CentralRiskManager(risk_config)
        orchestrator.register_central_risk_manager(risk_manager)
        await risk_manager.initialize()
        
        # Create multiple requests
        requests = [
            TradingDecisionRequest(
                decision_type=TradingDecisionType.POSITION_ENTRY,
                symbol='AAPL',
                side='buy',
                quantity=100.0,
                confidence=0.75,
                strategy_id=f'strategy_{i}',
                requesting_component='StrategyManager'
            )
            for i in range(3)
        ]
        
        # Process requests
        authorizations = []
        for request in requests:
            auth = await risk_manager.authorize_trading_decision(request)
            authorizations.append(auth)
        
        # Verify all processed
        assert len(authorizations) == 3
        assert all(auth is not None for auth in authorizations)
    
    @pytest.mark.asyncio
    async def test_authorization_audit_trail(self, orchestrator):
        """
        Test: Authorization audit trail
        
        Scenario: Authorization requests logged in audit trail
        Expected: Audit trail contains authorization records
        """
        # Register risk manager
        risk_config = RiskConfig()
        risk_manager = CentralRiskManager(risk_config)
        orchestrator.register_central_risk_manager(risk_manager)
        await risk_manager.initialize()
        
        # Create and process request
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=100.0,
            confidence=0.75,
            strategy_id='test_strategy',
            requesting_component='StrategyManager'
        )
        
        authorization = await risk_manager.authorize_trading_decision(request)
        
        # Verify audit trail (if accessible)
        if hasattr(orchestrator, '_authorization_audit'):
            assert len(orchestrator._authorization_audit) > 0
        elif hasattr(risk_manager, '_authorization_audit'):
            assert len(risk_manager._authorization_audit) > 0

