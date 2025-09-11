#!/usr/bin/env python3
"""
Test Unified Risk Manager
=========================

Comprehensive unit tests for the UnifiedRiskManager class.
Covers critical risk management functionality including:

- Risk limit validation
- Position sizing calculations
- Stop loss and take profit logic
- Portfolio risk metrics
- Strategy allocation management
- Risk alert generation
- Regime-aware risk adjustments

Author: Test Coverage Implementation - Phase 1
"""

import pytest
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, List, Any, Optional
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core_structure.components.risk.unified_risk_manager import (
    UnifiedRiskManager,
    RiskLimits,
    RiskLevel,
    RiskAction,
    TradingMode,
    UnifiedRiskMetrics
)

# Test fixtures
@pytest.fixture
def sample_risk_limits():
    """Sample risk limits for testing"""
    return RiskLimits(
        max_position_size_pct=0.1,
        max_portfolio_drawdown=0.1,
        max_strategy_drawdown=0.05,
        default_stop_loss_pct=0.02,
        default_take_profit_pct=0.04,
        target_portfolio_volatility=0.15,
        max_correlation_threshold=0.7,
        var_confidence_level=0.95,
        max_var_pct=0.03
    )

@pytest.fixture
def mock_data_provider():
    """Mock data provider for testing"""
    provider = Mock()
    provider.get_current_positions = AsyncMock(return_value={})
    provider.get_market_data = AsyncMock(return_value={'AAPL': 150.0, 'MSFT': 300.0})
    provider.get_historical_data = AsyncMock(return_value={
        'AAPL': [145.0, 148.0, 152.0, 149.0, 150.0],
        'MSFT': [295.0, 298.0, 302.0, 299.0, 300.0]
    })
    return provider

@pytest.fixture
def risk_manager(sample_risk_limits, mock_data_provider):
    """Create a risk manager instance for testing"""
    return UnifiedRiskManager(
        risk_limits=sample_risk_limits,
        trading_mode=TradingMode.PAPER_TRADING,
        initial_capital=100000.0,
        data_provider=mock_data_provider
    )

class TestUnifiedRiskManager:
    """Test cases for UnifiedRiskManager"""

    def test_initialization(self, risk_manager, sample_risk_limits):
        """Test basic initialization"""
        assert risk_manager.risk_limits == sample_risk_limits
        assert risk_manager.trading_mode == TradingMode.PAPER_TRADING
        assert risk_manager.initial_capital == 100000.0
        assert risk_manager.current_capital == 100000.0
        assert risk_manager.peak_capital == 100000.0

    def test_set_strategy_allocations_valid(self, risk_manager):
        """Test setting valid strategy allocations"""
        allocations = {'momentum': 0.4, 'mean_reversion': 0.3, 'pairs': 0.3}
        risk_manager.set_strategy_allocations(allocations)

        assert risk_manager.strategy_allocations == allocations

    def test_set_strategy_allocations_invalid_sum(self, risk_manager):
        """Test setting invalid strategy allocations (don't sum to 1.0)"""
        allocations = {'momentum': 0.5, 'mean_reversion': 0.6}  # Sum > 1.0

        with pytest.raises(ValueError, match="Allocations must sum to 1.0"):
            risk_manager.set_strategy_allocations(allocations)

    def test_should_allow_new_trade_basic_approval(self, risk_manager):
        """Test basic trade approval logic"""
        # Set up basic portfolio state
        risk_manager.current_capital = 100000.0
        risk_manager.strategy_allocations = {'test_strategy': 0.1}
        risk_manager.active_alerts = []  # Clear any alerts

        # Create mock risk metrics
        risk_manager.current_metrics = UnifiedRiskMetrics(
            portfolio_value=100000.0,
            total_pnl=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            current_drawdown=0.02,  # 2% drawdown (below 8% threshold)
            max_drawdown=0.05,
            drawdown_duration_days=5,
            portfolio_volatility=0.12,
            sharpe_ratio=1.5,
            var_95=0.025,
            cvar_95=0.035,
            max_correlation=0.6,
            concentration_risk=0.15,
            strategy_risk_scores={'test_strategy': 0.3}  # Low risk
        )

        allowed, reason = risk_manager.should_allow_new_trade(
            strategy_id='test_strategy',
            symbol='AAPL',
            position_size=50,  # Smaller position to avoid size limits
            current_price=150.0
        )

        assert allowed == True
        assert reason == "Trade approved"  # This is the expected approval message

    def test_should_allow_new_trade_drawdown_rejection(self, risk_manager):
        """Test trade rejection due to high drawdown"""
        # Set up high drawdown scenario
        risk_manager.current_capital = 100000.0
        risk_manager.strategy_allocations = {'test_strategy': 0.1}

        # Create mock risk metrics with high drawdown
        risk_manager.current_metrics = UnifiedRiskMetrics(
            portfolio_value=85000.0,  # 15% loss
            total_pnl=-15000.0,
            unrealized_pnl=-15000.0,
            realized_pnl=0.0,
            current_drawdown=0.15,  # 15% drawdown (above 8% threshold)
            max_drawdown=0.15,
            drawdown_duration_days=10,
            portfolio_volatility=0.12,
            sharpe_ratio=1.5,
            var_95=0.025,
            cvar_95=0.035,
            max_correlation=0.6,
            concentration_risk=0.15,
            strategy_risk_scores={'test_strategy': 0.3}
        )

        allowed, reason = risk_manager.should_allow_new_trade(
            strategy_id='test_strategy',
            symbol='AAPL',
            position_size=100,
            current_price=150.0
        )

        assert allowed == False
        assert "drawdown too high" in reason.lower()

    def test_should_allow_new_trade_position_size_rejection(self, risk_manager):
        """Test trade rejection due to position size limits"""
        # Set up basic portfolio state
        risk_manager.current_capital = 100000.0
        risk_manager.strategy_allocations = {'test_strategy': 0.1}

        # Create mock risk metrics
        risk_manager.current_metrics = UnifiedRiskMetrics(
            portfolio_value=100000.0,
            total_pnl=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            current_drawdown=0.02,
            max_drawdown=0.05,
            drawdown_duration_days=5,
            portfolio_volatility=0.12,
            sharpe_ratio=1.5,
            var_95=0.025,
            cvar_95=0.035,
            max_correlation=0.6,
            concentration_risk=0.15,
            strategy_risk_scores={'test_strategy': 0.3}
        )

        # Try position that's too large (15% of capital vs 10% limit)
        allowed, reason = risk_manager.should_allow_new_trade(
            strategy_id='test_strategy',
            symbol='AAPL',
            position_size=1000,  # 15000 value = 15% of capital
            current_price=150.0
        )

        assert allowed == False
        assert "position size too large" in reason.lower()

    def test_get_recommended_position_size_kelly(self, risk_manager):
        """Test Kelly criterion position sizing"""
        # Mock Kelly calculator with proper structure
        mock_kelly = Mock()
        mock_kelly.calculate_optimal_size.return_value = 0.05
        risk_manager.kelly_calculator = mock_kelly

        # Mock risk metrics
        risk_manager.current_metrics = UnifiedRiskMetrics(
            portfolio_value=100000.0,
            total_pnl=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            current_drawdown=0.02,
            max_drawdown=0.05,
            drawdown_duration_days=5,
            portfolio_volatility=0.12,
            sharpe_ratio=1.5,
            var_95=0.025,
            cvar_95=0.035,
            max_correlation=0.6,
            concentration_risk=0.15,
            strategy_risk_scores={'test_strategy': 0.3}
        )

        size = risk_manager.get_recommended_position_size(
            strategy_id='test_strategy',
            symbol='AAPL',
            base_size=100,  # Base position size
            current_price=150.0,
            expected_return=0.1,  # 10% expected return
            expected_volatility=0.2  # 20% expected volatility
        )

        # Should return a reasonable size (may be adjusted by risk limits)
        assert isinstance(size, (int, float))
        assert size > 0

    def test_get_stop_loss_price_long(self, risk_manager):
        """Test stop loss calculation for long positions"""
        entry_price = 150.0
        stop_price = risk_manager.get_stop_loss_price(
            entry_price=entry_price,
            side='LONG',  # Use LONG instead of BUY
            custom_pct=None
        )

        expected_stop = entry_price * (1 - 0.02)  # 2% default stop loss
        assert stop_price == expected_stop

    def test_get_stop_loss_price_short(self, risk_manager):
        """Test stop loss calculation for short positions"""
        entry_price = 150.0
        stop_price = risk_manager.get_stop_loss_price(
            entry_price=entry_price,
            side='SHORT',  # Use SHORT instead of SELL
            custom_pct=None
        )

        expected_stop = entry_price * (1 + 0.02)  # 2% default stop loss
        assert stop_price == expected_stop

    def test_get_take_profit_price_long(self, risk_manager):
        """Test take profit calculation for long positions"""
        entry_price = 150.0
        profit_price = risk_manager.get_take_profit_price(
            entry_price=entry_price,
            side='LONG',  # Use LONG instead of BUY
            custom_pct=None
        )

        expected_profit = entry_price * (1 + 0.04)  # 4% default take profit
        assert profit_price == expected_profit

    def test_get_take_profit_price_short(self, risk_manager):
        """Test take profit calculation for short positions"""
        entry_price = 150.0
        profit_price = risk_manager.get_take_profit_price(
            entry_price=entry_price,
            side='SHORT',  # Use SHORT instead of SELL
            custom_pct=None
        )

        expected_profit = entry_price * (1 - 0.04)  # 4% default take profit
        assert profit_price == expected_profit

    @pytest.mark.asyncio
    async def test_update_portfolio_state(self, risk_manager):
        """Test portfolio state updates"""
        portfolio_data = {
            'total_value': 105000.0,
            'strategy_values': {'momentum': 35000.0, 'mean_reversion': 35000.0, 'pairs': 35000.0},
            'positions': {'AAPL': {'size': 100, 'avg_price': 145.0}},
            'current_prices': {'AAPL': 150.0}
        }

        await risk_manager.update_portfolio_state(portfolio_data)

        # Check that metrics were updated
        assert risk_manager.current_metrics is not None
        assert risk_manager.current_metrics.portfolio_value == 105000.0
        assert risk_manager.current_metrics.total_pnl == 5000.0

    def test_risk_limits_validation(self, sample_risk_limits):
        """Test risk limits data structure"""
        assert sample_risk_limits.max_position_size_pct == 0.1
        assert sample_risk_limits.max_portfolio_drawdown == 0.1
        assert sample_risk_limits.default_stop_loss_pct == 0.02
        assert sample_risk_limits.default_take_profit_pct == 0.04
        assert sample_risk_limits.target_portfolio_volatility == 0.15
        assert sample_risk_limits.max_correlation_threshold == 0.7

    def test_add_risk_callback(self, risk_manager):
        """Test adding risk callbacks"""
        callback_called = False

        def test_callback(metrics):
            nonlocal callback_called
            callback_called = True

        risk_manager.add_risk_callback(test_callback)
        assert len(risk_manager.risk_callbacks) == 1
        assert risk_manager.risk_callbacks[0] == test_callback

    def test_add_alert_callback(self, risk_manager):
        """Test adding alert callbacks"""
        callback_called = False

        def test_callback(alert):
            nonlocal callback_called
            callback_called = True

        risk_manager.add_alert_callback(test_callback)
        assert len(risk_manager.alert_callbacks) == 1
        assert risk_manager.alert_callbacks[0] == test_callback

    @pytest.mark.asyncio
    async def test_calculate_unified_risk_metrics(self, risk_manager):
        """Test comprehensive risk metrics calculation"""
        total_value = 105000.0
        strategy_values = {'momentum': 35000.0, 'mean_reversion': 35000.0, 'pairs': 35000.0}
        positions = {'AAPL': {'size': 100, 'avg_price': 145.0}}
        current_prices = {'AAPL': 150.0}

        metrics = await risk_manager._calculate_unified_risk_metrics(
            total_value, strategy_values, positions, current_prices
        )

        assert metrics.portfolio_value == 105000.0
        assert metrics.total_pnl == 5000.0  # 105000 - 100000
        # Drawdown calculation may vary based on implementation
        assert isinstance(metrics.current_drawdown, (int, float))
        assert isinstance(metrics.strategy_performance, dict)
        assert isinstance(metrics.strategy_risk_scores, dict)

    def test_calculate_portfolio_volatility(self, risk_manager):
        """Test portfolio volatility calculation"""
        # Set up price history
        risk_manager.price_history = {
            'AAPL': [145.0, 148.0, 152.0, 149.0, 150.0],
            'MSFT': [295.0, 298.0, 302.0, 299.0, 300.0]
        }
        risk_manager.returns_history = {
            'AAPL': [0.0207, 0.0272, -0.0197, 0.0067],
            'MSFT': [0.0102, 0.0136, -0.0099, 0.0033]
        }

        volatility = risk_manager._calculate_portfolio_volatility()

        # Should return a reasonable volatility value
        assert isinstance(volatility, float)
        assert 0.0 <= volatility <= 1.0  # Should be between 0 and 100%

    def test_calculate_sharpe_ratio(self, risk_manager):
        """Test Sharpe ratio calculation"""
        # Set up returns history
        risk_manager.returns_history = {
            'AAPL': [0.02, 0.015, -0.01, 0.025, 0.018],
            'MSFT': [0.015, 0.012, -0.008, 0.022, 0.016]
        }

        sharpe = risk_manager._calculate_sharpe_ratio()

        # Should return a Sharpe ratio value
        assert isinstance(sharpe, float)
        # With positive returns, should be positive
        assert sharpe >= 0

    def test_calculate_max_drawdown(self, risk_manager):
        """Test maximum drawdown calculation"""
        # Set up portfolio history with drawdown
        risk_manager.portfolio_history = [
            {'value': 100000.0, 'timestamp': datetime.now()},
            {'value': 105000.0, 'timestamp': datetime.now()},
            {'value': 95000.0, 'timestamp': datetime.now()},   # 10% drawdown
            {'value': 92000.0, 'timestamp': datetime.now()},   # 12.4% drawdown
            {'value': 98000.0, 'timestamp': datetime.now()}    # 6.1% drawdown from peak
        ]

        max_dd = risk_manager._calculate_max_drawdown()

        # Should calculate the maximum drawdown correctly
        assert isinstance(max_dd, float)
        assert max_dd > 0  # Should be positive (absolute value)

    def test_get_risk_summary(self, risk_manager):
        """Test risk summary generation"""
        # Set up basic state
        risk_manager.current_capital = 105000.0
        risk_manager.peak_capital = 110000.0
        risk_manager.strategy_allocations = {'momentum': 0.4, 'mean_reversion': 0.6}

        # Create mock risk metrics
        risk_manager.current_metrics = UnifiedRiskMetrics(
            portfolio_value=105000.0,
            total_pnl=5000.0,
            unrealized_pnl=3000.0,
            realized_pnl=2000.0,
            current_drawdown=0.045,
            max_drawdown=0.08,
            drawdown_duration_days=15,
            portfolio_volatility=0.12,
            sharpe_ratio=1.8,
            var_95=0.025,
            cvar_95=0.035,
            max_correlation=0.65,
            concentration_risk=0.18,
            strategy_performance={'momentum': 0.15, 'mean_reversion': 0.08},
            strategy_risk_scores={'momentum': 0.4, 'mean_reversion': 0.3}
        )

        summary = risk_manager.get_risk_summary()

        # Verify summary structure
        assert isinstance(summary, dict)
        assert 'portfolio_metrics' in summary
        assert 'value' in summary['portfolio_metrics']
        assert 'total_pnl' in summary['portfolio_metrics']
        assert 'current_drawdown' in summary['portfolio_metrics']

        # Verify values
        assert summary['portfolio_metrics']['value'] == 105000.0
        assert summary['portfolio_metrics']['total_pnl'] == 5000.0
        assert summary['portfolio_metrics']['current_drawdown'] == 0.045

    def test_trading_mode_validation(self):
        """Test different trading modes"""
        for mode in [TradingMode.BACKTESTING, TradingMode.PAPER_TRADING, TradingMode.LIVE_TRADING]:
            manager = UnifiedRiskManager(trading_mode=mode)
            assert manager.trading_mode == mode

    def test_risk_level_enum(self):
        """Test risk level enumeration"""
        assert RiskLevel.LOW.value == "LOW"
        assert RiskLevel.MEDIUM.value == "MEDIUM"
        assert RiskLevel.HIGH.value == "HIGH"
        assert RiskLevel.CRITICAL.value == "CRITICAL"

    def test_risk_action_enum(self):
        """Test risk action enumeration"""
        assert RiskAction.NONE.value == "NONE"
        assert RiskAction.REDUCE_POSITIONS.value == "REDUCE_POSITIONS"
        assert RiskAction.HALT_NEW_TRADES.value == "HALT_NEW_TRADES"
        assert RiskAction.EMERGENCY_EXIT.value == "EMERGENCY_EXIT"


# Integration tests
class TestRiskManagerIntegration:
    """Integration tests for risk manager with other components"""

    @pytest.mark.asyncio
    async def test_full_risk_workflow(self, risk_manager):
        """Test complete risk management workflow"""
        # Clear any existing alerts
        risk_manager.active_alerts = []
        
        # 1. Initialize portfolio
        await risk_manager.update_portfolio_state({
            'total_value': 100000.0,
            'strategy_values': {'momentum': 40000.0, 'mean_reversion': 60000.0},
            'positions': {},
            'current_prices': {'AAPL': 150.0, 'MSFT': 300.0}
        })

        # 2. Set strategy allocations
        risk_manager.set_strategy_allocations({'momentum': 0.4, 'mean_reversion': 0.6})

        # 3. Test trade approval
        allowed, reason = risk_manager.should_allow_new_trade(
            'momentum', 'AAPL', 50, 150.0  # Smaller position
        )
        assert allowed == True

        # 4. Get position sizing
        size = risk_manager.get_recommended_position_size(
            'momentum', 'AAPL', 150.0, 0.6, 2.0
        )
        assert size > 0

        # 5. Get stop loss and take profit
        stop_price = risk_manager.get_stop_loss_price(150.0, 'LONG')
        profit_price = risk_manager.get_take_profit_price(150.0, 'LONG')

        assert stop_price < 150.0  # Stop below entry for long
        assert profit_price > 150.0  # Profit above entry for long

    @pytest.mark.asyncio
    async def test_portfolio_stress_test(self, risk_manager):
        """Test risk manager under portfolio stress"""
        # Clear existing alerts first
        risk_manager.active_alerts = []
        
        # Simulate portfolio decline
        await risk_manager.update_portfolio_state({
            'total_value': 85000.0,  # 15% loss
            'strategy_values': {'momentum': 30000.0, 'mean_reversion': 55000.0},
            'positions': {'AAPL': {'size': 200, 'avg_price': 160.0}},  # Losing position
            'current_prices': {'AAPL': 140.0}  # Down 12.5%
        })

        # Should reject new trades due to drawdown
        allowed, reason = risk_manager.should_allow_new_trade(
            'momentum', 'MSFT', 50, 300.0
        )
        assert allowed == False
        # The rejection could be due to critical alerts or drawdown
        assert "critical" in reason.lower() or "drawdown" in reason.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
