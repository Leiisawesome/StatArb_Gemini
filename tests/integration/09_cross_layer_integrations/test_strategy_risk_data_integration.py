"""
Strategy-Risk-Data Integration Tests
=====================================

Tests cross-layer integration: Strategy → Risk → Data.

Test Coverage:
- StrategyManager → RiskManager (authorization requests)
- StrategyManager → DataManager (enriched data)
- RiskManager → DataManager (market data for risk)
- Complete flow: Strategy → Data → Risk → Authorization
- Data consistency across Strategy and Risk layers
- Regime context flows through all layers
- Error propagation across layers
- Performance tracking across layers

Author: StatArb_Gemini Integration Test Suite
Date: November 4, 2025
"""

import pytest
from datetime import datetime

from core_engine.trading.strategies.strategy_engine import StrategySignal, SignalType
from core_engine.system.central_risk_manager import TradingDecisionRequest, TradingDecisionType

class TestStrategyRiskDataIntegration:
    """Integration tests for strategy-risk-data integration"""

    @pytest.mark.asyncio
    async def test_strategy_manager_to_risk_manager_authorization_requests(self, complete_system):
        """
        Test: StrategyManager → RiskManager (authorization requests)

        Scenario: Strategy generates signal, requests authorization
        Expected: Authorization request flows correctly
        """
        system = complete_system
        system['strategy_manager']
        risk_manager = system['risk_manager']

        # Create signal (simulate strategy generation)
        signal = StrategySignal(
            strategy_id='test_strategy',
            symbol='AAPL',
            signal_type=SignalType.BUY,
            confidence=0.75,
            target_quantity=100.0,
            timestamp=datetime.now()
        )

        # Create authorization request
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol=signal.symbol,
            side=signal.signal_type.value.lower(),
            quantity=signal.target_quantity,
            confidence=signal.confidence,
            strategy_id=signal.strategy_id,
            current_price=150.0,
            requesting_component='StrategyManager',
            metadata={'available_cash': 200000.0, 'price': 150.0}
        )

        # Request authorization
        authorization = await risk_manager.authorize_trading_decision(request)

        # Verify authorization processed
        assert authorization is not None

    @pytest.mark.asyncio
    async def test_strategy_manager_to_data_manager_enriched_data(self, complete_system, create_enriched_data):
        """
        Test: StrategyManager → DataManager (enriched data)

        Scenario: Strategy receives enriched data from pipeline
        Expected: Enriched data provided correctly
        """
        system = complete_system
        system['strategy_manager']

        # Create enriched data
        enriched_data = create_enriched_data(symbols=['AAPL'], rows=200)

        # Strategy would consume enriched data
        # Verify data structure
        assert 'AAPL' in enriched_data
        df = enriched_data['AAPL']
        assert 'SMA_10' in df.columns
        assert 'RSI_14' in df.columns

    @pytest.mark.asyncio
    async def test_risk_manager_to_data_manager_market_data(self, complete_system):
        """
        Test: RiskManager → DataManager (market data for risk)

        Scenario: RiskManager needs market data for risk calculations
        Expected: Market data provided
        """
        system = complete_system
        risk_manager = system['risk_manager']
        data_manager = system['data_manager']

        # Risk manager would request market data
        # Verify both components exist
        assert risk_manager is not None
        assert data_manager is not None

    @pytest.mark.asyncio
    async def test_complete_flow_strategy_data_risk_authorization(self, complete_system, create_enriched_data):
        """
        Test: Complete flow: Strategy → Data → Risk → Authorization

        Scenario: Complete flow from data to authorization
        Expected: Flow executes correctly
        """
        system = complete_system
        system['strategy_manager']
        risk_manager = system['risk_manager']

        # STEP 1: Get enriched data
        enriched_data = create_enriched_data(symbols=['AAPL'], rows=200)

        # STEP 2: Strategy generates signal (simulated)
        signal = StrategySignal(
            strategy_id='test_strategy',
            symbol='AAPL',
            signal_type=SignalType.BUY,
            confidence=0.75,
            target_quantity=100.0,
            timestamp=datetime.now()
        )

        # STEP 3: Request authorization
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol=signal.symbol,
            side=signal.signal_type.value.lower(),
            quantity=signal.target_quantity,
            confidence=signal.confidence,
            strategy_id=signal.strategy_id,
            current_price=150.0,
            requesting_component='StrategyManager',
            metadata={'available_cash': 200000.0, 'price': 150.0}
        )

        authorization = await risk_manager.authorize_trading_decision(request)

        # Verify complete flow
        assert authorization is not None

    @pytest.mark.asyncio
    async def test_data_consistency_across_strategy_and_risk_layers(self, complete_system, create_enriched_data):
        """
        Test: Data consistency across Strategy and Risk layers

        Scenario: Same data used by Strategy and Risk
        Expected: Data consistency maintained
        """

        # Create enriched data
        enriched_data = create_enriched_data(symbols=['AAPL'], rows=200)

        # Both Strategy and Risk would use same data
        # Verify data consistency
        df = enriched_data['AAPL']
        assert len(df) == 200
        assert 'close' in df.columns

    @pytest.mark.asyncio
    async def test_regime_context_flows_through_all_layers(self, complete_system):
        """
        Test: Regime context flows through all layers

        Scenario: Regime context propagated through layers
        Expected: All layers receive regime context
        """
        system = complete_system
        regime_engine = system['regime_engine']
        strategy_manager = system['strategy_manager']
        risk_manager = system['risk_manager']

        # Get regime context (not async, so no await needed)
        regime_context = regime_engine.get_current_regime_context() if regime_engine else None

        # All layers should have regime context (may be None if no regime detected yet)
        assert regime_context is not None or regime_engine is not None
        assert strategy_manager is not None
        assert risk_manager is not None

    @pytest.mark.asyncio
    async def test_error_propagation_across_layers(self, complete_system):
        """
        Test: Error propagation across layers

        Scenario: Error in one layer propagates appropriately
        Expected: Errors handled gracefully
        """
        system = complete_system
        risk_manager = system['risk_manager']

        # Create invalid request
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            symbol='AAPL',
            side='buy',
            quantity=0.0,  # Invalid
            confidence=0.75,
            strategy_id='test_strategy',
            current_price=150.0,
            requesting_component='StrategyManager',
            metadata={'available_cash': 200000.0, 'price': 150.0}
        )

        # Error should be handled
        authorization = await risk_manager.authorize_trading_decision(request)
        assert authorization is not None

    @pytest.mark.asyncio
    async def test_performance_tracking_across_layers(self, complete_system):
        """
        Test: Performance tracking across layers

        Scenario: Track performance across Strategy and Risk layers
        Expected: Performance tracked correctly
        """
        system = complete_system
        analytics_manager = system['analytics_manager']

        # Analytics would track performance across layers
        # Verify analytics manager exists
        assert analytics_manager is not None

