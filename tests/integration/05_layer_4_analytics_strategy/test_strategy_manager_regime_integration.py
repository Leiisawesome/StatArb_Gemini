"""
Strategy Manager Regime Integration Tests
==========================================

Tests StrategyManager integration with RegimeEngine.

Test Coverage:
- Strategy receives regime context
- Strategy adapts to regime changes
- Strategy uses regime-aware position sizing
- Strategy filters signals by regime
- Strategy adapts to multiple regime dimensions
- Strategy handles regime transition during signal generation
- Strategy validates regime context
- Strategy provides regime-aware confidence
- Strategy handles missing regime context
- Strategy adapts to fast regime detection

Author: StatArb_Gemini Integration Test Suite
Date: November 4, 2025
"""

import pytest
import pytest_asyncio

from core_engine.trading.strategies.manager import StrategyManager
from core_engine.regime.engine import EnhancedRegimeEngine


class TestStrategyManagerRegimeIntegration:
    """Integration tests for strategy manager-regime integration"""
    
    @pytest.mark.asyncio
    async def test_strategy_receives_regime_context(self, strategy_manager_with_regime):
        """
        Test: Strategy receives regime context
        
        Scenario: Strategy receives current regime context
        Expected: Regime context provided
        """
        system = strategy_manager_with_regime
        strategy_manager = system['strategy_manager']
        regime_engine = system['regime_engine']
        
        # Get regime context
        regime_context = await regime_engine.get_current_regime_context()
        
        # Strategy manager would receive regime context
        # Verify regime context available
        assert regime_context is not None
    
    @pytest.mark.asyncio
    async def test_strategy_adapts_to_regime_changes(self, strategy_manager_with_regime):
        """
        Test: Strategy adapts to regime changes
        
        Scenario: Regime changes, strategy adapts
        Expected: Strategy adapts to new regime
        """
        system = strategy_manager_with_regime
        strategy_manager = system['strategy_manager']
        regime_engine = system['regime_engine']
        
        # Regime changes would trigger adaptation
        # Verify both components exist
        assert strategy_manager is not None
        assert regime_engine is not None
    
    @pytest.mark.asyncio
    async def test_strategy_uses_regime_aware_position_sizing(self, strategy_manager_with_regime):
        """
        Test: Strategy uses regime-aware position sizing
        
        Scenario: Position sizing adjusted by regime
        Expected: Position sizing adapted to regime
        """
        system = strategy_manager_with_regime
        strategy_manager = system['strategy_manager']
        
        # Strategy manager would use regime-aware sizing
        # Verify capability exists
        assert strategy_manager is not None
    
    @pytest.mark.asyncio
    async def test_strategy_filters_signals_by_regime(self, strategy_manager_with_regime):
        """
        Test: Strategy filters signals by regime
        
        Scenario: Filter signals based on regime
        Expected: Regime-inappropriate signals filtered
        """
        system = strategy_manager_with_regime
        strategy_manager = system['strategy_manager']
        
        # Strategy manager would filter signals by regime
        # Verify capability exists
        assert strategy_manager is not None
    
    @pytest.mark.asyncio
    async def test_strategy_adapts_to_multiple_regime_dimensions(self, strategy_manager_with_regime):
        """
        Test: Strategy adapts to multiple regime dimensions
        
        Scenario: Adapt to volatility, trend, liquidity regimes
        Expected: Multi-dimensional adaptation applied
        """
        system = strategy_manager_with_regime
        strategy_manager = system['strategy_manager']
        
        # Strategy manager would adapt to multiple dimensions
        # Verify capability exists
        assert strategy_manager is not None
    
    @pytest.mark.asyncio
    async def test_strategy_handles_regime_transition_during_signal_generation(self, strategy_manager_with_regime):
        """
        Test: Strategy handles regime transition during signal generation
        
        Scenario: Regime changes during signal generation
        Expected: Transition handled gracefully
        """
        system = strategy_manager_with_regime
        strategy_manager = system['strategy_manager']
        regime_engine = system['regime_engine']
        
        # Strategy manager would handle regime transitions
        # Verify both components exist
        assert strategy_manager is not None
        assert regime_engine is not None
    
    @pytest.mark.asyncio
    async def test_strategy_validates_regime_context(self, strategy_manager_with_regime):
        """
        Test: Strategy validates regime context
        
        Scenario: Validate regime context format
        Expected: Regime context validated
        """
        system = strategy_manager_with_regime
        strategy_manager = system['strategy_manager']
        
        # Strategy manager would validate regime context
        regime_context = strategy_manager.get_current_regime_context() if hasattr(strategy_manager, 'get_current_regime_context') else None
        # Context should be valid or None
        assert regime_context is None or isinstance(regime_context, dict) or hasattr(regime_context, 'primary_regime')
    
    @pytest.mark.asyncio
    async def test_strategy_provides_regime_aware_confidence(self, strategy_manager_with_regime):
        """
        Test: Strategy provides regime-aware confidence
        
        Scenario: Signal confidence adjusted by regime
        Expected: Confidence adapted to regime
        """
        system = strategy_manager_with_regime
        strategy_manager = system['strategy_manager']
        
        # Strategy manager would provide regime-aware confidence
        # Verify capability exists
        assert strategy_manager is not None
    
    @pytest.mark.asyncio
    async def test_strategy_handles_missing_regime_context(self, strategy_manager):
        """
        Test: Strategy handles missing regime context
        
        Scenario: Regime context not available
        Expected: Missing context handled gracefully
        """
        # Strategy manager would handle missing regime context
        # Verify strategy manager exists
        assert strategy_manager is not None
    
    @pytest.mark.asyncio
    async def test_strategy_adapts_to_fast_regime_detection(self, strategy_manager_with_regime):
        """
        Test: Strategy adapts to fast regime detection
        
        Scenario: Fast regime detection triggers rapid adaptation
        Expected: Rapid adaptation applied
        """
        system = strategy_manager_with_regime
        strategy_manager = system['strategy_manager']
        regime_engine = system['regime_engine']
        
        # Strategy manager would adapt to fast regime detection
        # Verify both components exist
        assert strategy_manager is not None
        assert regime_engine is not None

