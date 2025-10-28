#!/usr/bin/env python3
"""
Tests for Momentum Strategy Backtest Desk Wiring
===============================================

Separate tests for desk integration (orchestrator, trading engine wiring)
vs. strategy logic tests (which remain in Phase 7 test suites).

Tests the prototype launcher and backtest system integration.

Author: StatArb_Gemini Desk Wiring Tests
Version: 1.0.0
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from momentum_backtest_launcher import MomentumBacktestLauncher
from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine
from core_engine.config.system_config import BacktestConfig, BacktestMode


class TestMomentumBacktestDeskWiring:
    """Test desk wiring for momentum backtest prototype"""

    @pytest.fixture
    async def launcher(self):
        """Create test launcher instance"""
        launcher = MomentumBacktestLauncher()
        yield launcher
        # Cleanup if needed

    @pytest.mark.asyncio
    async def test_launcher_initialization(self, launcher):
        """Test that launcher initializes institutional backtest engine with momentum strategy"""
        with patch('momentum_backtest_launcher.InstitutionalBacktestEngine') as mock_engine:
            # Setup mock
            mock_engine.return_value.initialize = AsyncMock(return_value=True)

            # Test initialization
            success = await launcher.initialize('2023-01-01', '2023-12-31')

            assert success is True
            mock_engine.return_value.initialize.assert_called_once()

            # Verify backtest config was created correctly
            call_args = mock_engine.call_args[0][0]  # First positional argument
            assert isinstance(call_args, BacktestConfig)
            assert call_args.backtest_name == "Momentum Strategy Prototype"
            assert call_args.backtest_mode == BacktestMode.SINGLE_STRATEGY
            assert len(call_args.strategies) == 1
            assert call_args.strategies[0]['type'] == 'momentum'
            assert call_args.strategies[0]['name'] == 'enhanced_momentum'

    @pytest.mark.asyncio
    async def test_backtest_execution_flow(self, launcher):
        """Test the main backtest execution flow using institutional backtest engine"""
        with patch('momentum_backtest_launcher.InstitutionalBacktestEngine') as mock_engine:
            # Setup mock
            mock_engine.return_value.initialize = AsyncMock(return_value=True)
            mock_engine.return_value.run_backtest = AsyncMock(return_value={
                'total_return': 0.15,
                'sharpe_ratio': 1.8,
                'max_drawdown': 0.08,
                'total_trades': 50,
                'winning_trades': 30,
                'signals_generated': 75
            })

            # Initialize first
            await launcher.initialize('2023-01-01', '2023-12-31')

            # Test backtest run
            results = await launcher.run_backtest()

            assert isinstance(results, dict)
            assert 'total_return' in results
            assert 'sharpe_ratio' in results
            assert 'max_drawdown' in results
            assert 'total_trades' in results
            assert 'winning_trades' in results
            assert 'signals_generated' in results

            mock_engine.return_value.run_backtest.assert_called_once()

    @pytest.mark.asyncio
    async def test_momentum_strategy_configuration(self, launcher):
        """Test that momentum strategy is properly configured in backtest config"""
        with patch('momentum_backtest_launcher.InstitutionalBacktestEngine') as mock_engine:
            mock_engine.return_value.initialize = AsyncMock(return_value=True)

            await launcher.initialize('2023-01-01', '2023-12-31')

            # Verify the backtest config contains correct momentum strategy settings
            call_args = mock_engine.call_args[0][0]
            strategy_config = call_args.strategies[0]

            assert strategy_config['type'] == 'momentum'
            assert strategy_config['name'] == 'enhanced_momentum'
            assert strategy_config['allocation_pct'] == 1.0
            assert strategy_config['max_positions'] == 5
            assert strategy_config['risk_limit'] == 0.05
            assert strategy_config['lookback_period'] == 20
            assert strategy_config['momentum_threshold'] == 0.02
            assert strategy_config['adx_threshold'] == 25.0
            assert strategy_config['volume_threshold'] == 1.2

    def test_results_printing(self, launcher, capsys):
        """Test results printing functionality"""
        results = {
            'total_return': 0.15,
            'sharpe_ratio': 1.8,
            'max_drawdown': 0.08,
            'total_trades': 50,
            'winning_trades': 30,
            'signals_generated': 75
        }

        launcher.print_results(results)

        captured = capsys.readouterr()
        assert "MOMENTUM STRATEGY BACKTEST RESULTS" in captured.out
        assert "Total Return: 15.00%" in captured.out
        assert "Sharpe Ratio: 1.80" in captured.out
        assert "Max Drawdown: 8.00%" in captured.out
        assert "Total Trades: 50" in captured.out
        assert "Winning Trades: 30" in captured.out
        assert "Signals Generated: 75" in captured.out


# Integration test for full launcher flow
@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_launcher_integration():
    """Integration test for complete launcher flow using institutional backtest engine"""
    launcher = MomentumBacktestLauncher()

    with patch('momentum_backtest_launcher.InstitutionalBacktestEngine') as mock_engine:
        # Setup mock for successful flow
        mock_engine.return_value.initialize = AsyncMock(return_value=True)
        mock_engine.return_value.run_backtest = AsyncMock(return_value={
            'total_return': 0.12,
            'sharpe_ratio': 1.5,
            'max_drawdown': 0.06,
            'total_trades': 25,
            'winning_trades': 18,
            'signals_generated': 40
        })

        # Run full test
        success = await launcher.initialize('2023-01-01', '2023-06-30')
        assert success

        results = await launcher.run_backtest()
        assert isinstance(results, dict)
        assert results['total_return'] == 0.12

        # Verify engine methods were called correctly
        mock_engine.return_value.initialize.assert_called_once()
        mock_engine.return_value.run_backtest.assert_called_once()

        # Verify backtest config was created with correct parameters
        call_args = mock_engine.call_args[0][0]
        assert call_args.start_date == '2023-01-01'
        assert call_args.end_date == '2023-06-30'
        assert call_args.symbols == ["SPY", "QQQ"]


if __name__ == "__main__":
    pytest.main([__file__])