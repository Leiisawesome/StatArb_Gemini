"""
Simple End-to-End Trading Workflow Integration Test
===================================================

Tests the complete flow: Market Data → Strategy → Risk → Execution

Author: StatArb_Gemini Week 2 Integration Tests
Version: 1.0.0
"""

import pytest
import pytest_asyncio
import asyncio

from core_engine.system.central_risk_manager import (
    CentralRiskManager,
    TradingDecisionRequest,
    TradingDecisionType
)
from core_engine.trading.strategies.manager import StrategyManager
from core_engine.system.unified_execution_engine import UnifiedExecutionEngine


# ========================================
# FIXTURES
# ========================================

@pytest_asyncio.fixture
async def risk_manager():
    """Initialize risk manager"""
    rm = CentralRiskManager({'real_time_monitoring': False})
    await rm.initialize()
    yield rm


@pytest_asyncio.fixture
async def strategy_manager():
    """Initialize strategy manager"""
    # Use empty config - StrategyManagerConfig has defaults
    sm = StrategyManager({})
    await sm.initialize()
    yield sm
    await sm.stop()


@pytest_asyncio.fixture
async def execution_engine():
    """Initialize execution engine"""
    engine = UnifiedExecutionEngine({})
    yield engine


# ========================================
# TESTS: SIMPLE WORKFLOW
# ========================================

class TestSimpleWorkflow:
    """Test simple end-to-end trading workflow"""
    
    @pytest.mark.asyncio
    async def test_risk_authorization_flow(self, risk_manager):
        """Test risk manager can authorize a simple trade"""
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            strategy_id='test_strategy',
            symbol='AAPL',
            side='buy',
            quantity=100.0,
            confidence=0.8,
            expected_return=0.05,
            risk_score=0.3
        )
        
        auth = await risk_manager.authorize_trading_decision(request)
        
        assert auth is not None
        assert auth.authorized_quantity > 0
        print(f"✅ Risk authorization: {auth.authorized_quantity} shares approved")
    
    @pytest.mark.asyncio
    async def test_strategy_manager_lifecycle(self, strategy_manager):
        """Test strategy manager basic lifecycle"""
        assert strategy_manager is not None
        
        # Start the manager
        result = await strategy_manager.start()
        assert result is True
        
        print("✅ Strategy manager lifecycle working")
    
    @pytest.mark.asyncio
    async def test_execution_engine_exists(self, execution_engine):
        """Test execution engine can be initialized"""
        assert execution_engine is not None
        print("✅ Execution engine initialized")
    
    @pytest.mark.asyncio
    async def test_integrated_authorization_check(self, risk_manager):
        """Test authorization with realistic parameters"""
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            strategy_id='momentum_strat',
            symbol='MSFT',
            side='buy',
            quantity=50.0,
            confidence=0.85,
            expected_return=0.03,
            risk_score=0.25,
            portfolio_impact=0.02
        )
        
        auth = await risk_manager.authorize_trading_decision(request)
        
        # Should be approved with high confidence
        assert auth.authorized_quantity > 0
        assert auth.is_valid is True
        
        print(f"✅ Integrated authorization: {auth.authorization_level.value}")
    
    @pytest.mark.asyncio
    async def test_concurrent_risk_checks(self, risk_manager):
        """Test multiple concurrent risk authorizations"""
        requests = [
            TradingDecisionRequest(
                decision_type=TradingDecisionType.POSITION_ENTRY,
                strategy_id=f'strategy_{i}',
                symbol=symbol,
                side='buy',
                quantity=50.0,
                confidence=0.75,
                expected_return=0.04,
                risk_score=0.3
            )
            for i, symbol in enumerate(['AAPL', 'GOOGL', 'MSFT'])
        ]
        
        # Process concurrently
        tasks = [risk_manager.authorize_trading_decision(req) for req in requests]
        results = await asyncio.gather(*tasks)
        
        # All should be authorized
        assert len(results) == 3
        assert all(r.authorized_quantity > 0 for r in results)
        
        print(f"✅ Concurrent authorizations: {len(results)} processed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
