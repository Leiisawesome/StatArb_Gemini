"""
Test suite for RiskBridge: Production ↔ Backtesting Risk Management Integration

This module provides comprehensive tests for the RiskBridge class, including:
- Basic functionality testing
- Performance testing
- Integration testing
- Error handling testing
- VaR calculation testing
- Risk metrics calculation testing
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import time
import logging

# Add the core_structure to the path
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core_structure'))

from risk.risk_bridge import (
    RiskBridge, 
    RiskBridgeConfig, 
    RiskMetrics,
    PortfolioRiskMetrics,
    RiskLevel,
    RiskMode,
    VaRResult,
    RiskAlert,
    create_risk_bridge,
    calculate_risk_for_backtesting
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestRiskBridge:
    """Test cases for RiskBridge"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.config = RiskBridgeConfig(
            risk_mode=RiskMode.BACKTESTING,
            enable_var_calculation=True,
            var_confidence_level=0.95,
            max_position_size=0.1,
            max_portfolio_risk=0.02,
            stop_loss_pct=0.05,
            take_profit_pct=0.10,
            max_drawdown=0.15,
            daily_loss_limit=0.05,
            max_volatility=0.25
        )
        self.bridge = RiskBridge(self.config)
        
        # Create sample market data
        dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='D')
        self.market_data = pd.DataFrame({
            'open': [100 + i for i in range(len(dates))],
            'high': [105 + i for i in range(len(dates))],
            'low': [95 + i for i in range(len(dates))],
            'close': [102 + i for i in range(len(dates))],
            'volume': [1000000 + i * 10000 for i in range(len(dates))]
        }, index=dates)
        
        # Create sample portfolio state
        self.portfolio_state = {
            'total_value': 100000,
            'cash': 50000,
            'peak_value': 110000,
            'max_drawdown': 0.05,
            'daily_pnl': 1000
        }
        
        # Create sample positions
        self.positions = {
            'AAPL': {
                'quantity': 100,
                'current_price': 150.0,
                'avg_price': 145.0
            },
            'SPY': {
                'quantity': 200,
                'current_price': 400.0,
                'avg_price': 395.0
            },
            'MSFT': {
                'quantity': 50,
                'current_price': 300.0,
                'avg_price': 310.0
            }
        }
    
    def test_risk_bridge_initialization(self):
        """Test RiskBridge initialization"""
        assert self.bridge.config.risk_mode == RiskMode.BACKTESTING
        assert self.bridge.config.enable_var_calculation == True
        assert self.bridge.config.var_confidence_level == 0.95
        assert self.bridge.config.max_position_size == 0.1
        assert self.bridge.config.max_portfolio_risk == 0.02
    
    def test_position_risk_calculation(self):
        """Test position risk calculation"""
        risk_metrics = self.bridge.calculate_position_risk(
            symbol="AAPL",
            position_size=100,
            current_price=150.0,
            avg_price=145.0,
            market_data=self.market_data,
            portfolio_state=self.portfolio_state
        )
        
        assert risk_metrics.symbol == "AAPL"
        assert risk_metrics.position_size == 100
        assert risk_metrics.current_price == 150.0
        assert risk_metrics.avg_price == 145.0
        assert risk_metrics.unrealized_pnl == 500.0  # (150 - 145) * 100
        assert abs(risk_metrics.unrealized_pnl_pct - 0.0345) < 0.01  # (150 - 145) / 145
        assert risk_metrics.var_1d >= 0
        assert risk_metrics.volatility >= 0
        assert risk_metrics.beta == 1.0
        assert isinstance(risk_metrics.risk_level, RiskLevel)
        assert isinstance(risk_metrics.alerts, list)
    
    def test_portfolio_risk_calculation(self):
        """Test portfolio risk calculation"""
        market_data = {
            'AAPL': self.market_data,
            'SPY': self.market_data,
            'MSFT': self.market_data
        }
        
        portfolio_metrics = self.bridge.calculate_portfolio_risk(
            positions=self.positions,
            market_data=market_data,
            portfolio_state=self.portfolio_state
        )
        
        assert portfolio_metrics.total_value > 0
        assert portfolio_metrics.total_pnl > 0
        assert portfolio_metrics.total_pnl_pct > 0
        assert portfolio_metrics.portfolio_var_1d >= 0
        assert portfolio_metrics.portfolio_volatility >= 0
        assert portfolio_metrics.portfolio_beta == 1.0
        assert portfolio_metrics.current_drawdown >= 0
        assert portfolio_metrics.max_drawdown >= 0
        assert isinstance(portfolio_metrics.risk_level, RiskLevel)
        assert len(portfolio_metrics.position_risks) == 3
        assert isinstance(portfolio_metrics.alerts, list)
    
    def test_var_calculation(self):
        """Test VaR calculation"""
        var_result = self.bridge._calculate_var(
            symbol="AAPL",
            market_data=self.market_data,
            position_size=100,
            current_price=150.0
        )
        
        assert var_result.symbol == "AAPL"
        assert var_result.var_1d >= 0
        assert var_result.var_1d_pct >= 0
        assert var_result.var_5d >= 0
        assert var_result.var_5d_pct >= 0
        assert var_result.cvar_1d >= 0
        assert var_result.cvar_1d_pct >= 0
        assert var_result.confidence_level == 0.95
        assert var_result.method in ["historical", "error"]
        assert var_result.calculation_time >= 0
    
    def test_volatility_calculation(self):
        """Test volatility calculation"""
        volatility = self.bridge._calculate_volatility(self.market_data)
        assert volatility >= 0
        assert isinstance(volatility, float)
    
    def test_sharpe_ratio_calculation(self):
        """Test Sharpe ratio calculation"""
        # Test positive Sharpe ratio
        sharpe_positive = self.bridge._calculate_sharpe_ratio(0.1, 0.2)
        assert sharpe_positive == 0.5
        
        # Test negative Sharpe ratio
        sharpe_negative = self.bridge._calculate_sharpe_ratio(-0.1, 0.2)
        assert sharpe_negative == -0.5
        
        # Test zero volatility
        sharpe_zero_vol = self.bridge._calculate_sharpe_ratio(0.1, 0.0)
        assert sharpe_zero_vol == 0.0
    
    def test_risk_level_determination(self):
        """Test risk level determination"""
        # Test low risk
        low_risk = self.bridge._determine_risk_level(0.02, 0.01, 0.1, 0.05)
        assert low_risk == RiskLevel.LOW
        
        # Test medium risk
        medium_risk = self.bridge._determine_risk_level(-0.03, 0.012, 0.15, 0.05)
        assert medium_risk == RiskLevel.MEDIUM
        
        # Test high risk
        high_risk = self.bridge._determine_risk_level(-0.04, 0.016, 0.2, 0.05)
        assert high_risk == RiskLevel.HIGH
        
        # Test critical risk
        critical_risk = self.bridge._determine_risk_level(-0.06, 0.025, 0.3, 0.05)
        assert critical_risk == RiskLevel.CRITICAL
    
    def test_portfolio_risk_level_determination(self):
        """Test portfolio risk level determination"""
        # Test low risk
        low_risk = self.bridge._determine_portfolio_risk_level(0.02, 0.01, 0.1, 0.05)
        assert low_risk == RiskLevel.LOW
        
        # Test medium risk
        medium_risk = self.bridge._determine_portfolio_risk_level(-0.03, 0.012, 0.1, 0.09)
        assert medium_risk == RiskLevel.MEDIUM
        
        # Test high risk
        high_risk = self.bridge._determine_portfolio_risk_level(-0.04, 0.016, 0.1, 0.12)
        assert high_risk == RiskLevel.HIGH
        
        # Test critical risk
        critical_risk = self.bridge._determine_portfolio_risk_level(-0.06, 0.025, 0.1, 0.18)
        assert critical_risk == RiskLevel.CRITICAL
    
    def test_risk_limit_checking(self):
        """Test risk limit checking"""
        # Create a mock order
        class MockOrder:
            def __init__(self, symbol, quantity, price):
                self.symbol = symbol
                self.quantity = quantity
                self.price = price
        
        # Test valid order
        valid_order = MockOrder("AAPL", 100, 150.0)
        is_valid, violations = self.bridge.check_risk_limits(valid_order, self.portfolio_state)
        assert is_valid == True
        assert len(violations) == 0
        
        # Test order exceeding position limit
        large_order = MockOrder("AAPL", 10000, 150.0)
        is_valid, violations = self.bridge.check_risk_limits(large_order, self.portfolio_state)
        assert is_valid == False
        assert len(violations) > 0
    
    def test_stop_loss_creation(self):
        """Test stop-loss creation"""
        stop_loss = self.bridge.create_stop_loss("AAPL", 100, 150.0, 0.05)
        # Should return None if StopLossManager not available, or a stop-loss order
        assert stop_loss is None or hasattr(stop_loss, 'symbol')
    
    def test_take_profit_creation(self):
        """Test take-profit creation"""
        take_profit = self.bridge.create_take_profit("AAPL", 100, 150.0, 0.10)
        # Should return None if StopLossManager not available, or a take-profit order
        assert take_profit is None or hasattr(take_profit, 'symbol')
    
    def test_position_alerts_generation(self):
        """Test position alerts generation"""
        # Test normal position (no alerts)
        alerts = self.bridge._generate_position_alerts("AAPL", 0.05, 0.02, 0.01, 0.1)
        assert len(alerts) == 0
        
        # Test position with stop-loss alert
        alerts = self.bridge._generate_position_alerts("AAPL", 0.05, -0.06, 0.01, 0.1)
        assert len(alerts) > 0
        assert any("Stop-loss triggered" in alert for alert in alerts)
        
        # Test position with take-profit alert
        alerts = self.bridge._generate_position_alerts("AAPL", 0.05, 0.12, 0.01, 0.1)
        assert len(alerts) > 0
        assert any("Take-profit triggered" in alert for alert in alerts)
        
        # Test position with VaR alert
        alerts = self.bridge._generate_position_alerts("AAPL", 0.05, 0.02, 0.025, 0.1)
        assert len(alerts) > 0
        assert any("VaR" in alert for alert in alerts)
        
        # Test position with volatility alert
        alerts = self.bridge._generate_position_alerts("AAPL", 0.05, 0.02, 0.01, 0.3)
        assert len(alerts) > 0
        assert any("Volatility" in alert for alert in alerts)
    
    def test_portfolio_alerts_generation(self):
        """Test portfolio alerts generation"""
        # Test normal portfolio (no alerts)
        alerts = self.bridge._generate_portfolio_alerts(0.02, 0.01, 0.1, 0.05)
        assert len(alerts) == 0
        
        # Test portfolio with drawdown alert
        alerts = self.bridge._generate_portfolio_alerts(0.02, 0.01, 0.1, 0.18)
        assert len(alerts) > 0
        assert any("Drawdown" in alert for alert in alerts)
        
        # Test portfolio with daily loss alert
        alerts = self.bridge._generate_portfolio_alerts(-0.06, 0.01, 0.1, 0.05)
        assert len(alerts) > 0
        assert any("Daily loss" in alert for alert in alerts)
        
        # Test portfolio with VaR alert
        alerts = self.bridge._generate_portfolio_alerts(0.02, 0.025, 0.1, 0.05)
        assert len(alerts) > 0
        assert any("Portfolio VaR" in alert for alert in alerts)
        
        # Test portfolio with volatility alert
        alerts = self.bridge._generate_portfolio_alerts(0.02, 0.01, 0.3, 0.05)
        assert len(alerts) > 0
        assert any("Portfolio volatility" in alert for alert in alerts)
    
    def test_performance_statistics(self):
        """Test performance statistics tracking"""
        # Calculate some risks to populate stats
        self.bridge.calculate_position_risk("AAPL", 100, 150.0, 145.0, self.market_data)
        self.bridge.calculate_portfolio_risk(self.positions, {'AAPL': self.market_data})
        
        stats = self.bridge.get_performance_stats()
        
        assert stats['total_risk_checks'] > 0
        assert stats['total_calculation_time'] > 0
        assert stats['avg_calculation_time'] > 0
        assert stats['risk_checks_per_second'] > 0
    
    def test_error_handling(self):
        """Test error handling"""
        # Test with invalid market data
        risk_metrics = self.bridge.calculate_position_risk(
            symbol="INVALID",
            position_size=100,
            current_price=150.0,
            avg_price=145.0,
            market_data=pd.DataFrame(),  # Empty DataFrame
            portfolio_state=self.portfolio_state
        )
        
        assert risk_metrics.symbol == "INVALID"
        assert risk_metrics.risk_level == RiskLevel.HIGH
        assert len(risk_metrics.alerts) > 0
        assert any("Calculation error" in alert for alert in risk_metrics.alerts)
    
    def test_convenience_function(self):
        """Test convenience function for backtesting"""
        market_data = {
            'AAPL': self.market_data,
            'SPY': self.market_data,
            'MSFT': self.market_data
        }
        
        portfolio_metrics = calculate_risk_for_backtesting(
            self.positions, market_data, self.portfolio_state
        )
        
        assert portfolio_metrics.total_value > 0
        assert portfolio_metrics.total_pnl > 0
        assert len(portfolio_metrics.position_risks) == 3
        assert isinstance(portfolio_metrics.risk_level, RiskLevel)
    
    def test_bridge_shutdown(self):
        """Test bridge shutdown"""
        self.bridge.shutdown()
        # Should not raise any exceptions
    
    def test_reset_performance_stats(self):
        """Test performance statistics reset"""
        # Calculate some risks to populate stats
        self.bridge.calculate_position_risk("AAPL", 100, 150.0, 145.0, self.market_data)
        
        # Verify stats are populated
        stats = self.bridge.get_performance_stats()
        assert stats['total_risk_checks'] > 0
        
        # Reset stats
        self.bridge.reset_performance_stats()
        
        # Verify stats are reset
        stats = self.bridge.get_performance_stats()
        assert stats['total_risk_checks'] == 0
        assert stats['total_calculation_time'] == 0.0

class TestRiskBridgePerformance:
    """Performance tests for RiskBridge"""
    
    def setup_method(self):
        """Set up performance test fixtures"""
        self.config = RiskBridgeConfig(
            risk_mode=RiskMode.BACKTESTING,
            max_concurrent_calculations=10
        )
        self.bridge = RiskBridge(self.config)
        
        # Create large dataset
        dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='D')
        self.market_data = pd.DataFrame({
            'open': [100 + i for i in range(len(dates))],
            'high': [105 + i for i in range(len(dates))],
            'low': [95 + i for i in range(len(dates))],
            'close': [102 + i for i in range(len(dates))],
            'volume': [1000000 + i * 10000 for i in range(len(dates))]
        }, index=dates)
        
        # Create large position set
        self.positions = {
            f'SYMBOL_{i}': {
                'quantity': 100 + i,
                'current_price': 150.0 + i,
                'avg_price': 145.0 + i
            }
            for i in range(50)
        }
        
        self.market_data_dict = {
            f'SYMBOL_{i}': self.market_data for i in range(50)
        }
    
    def test_single_position_performance(self):
        """Test single position risk calculation performance"""
        start_time = time.time()
        risk_metrics = self.bridge.calculate_position_risk(
            "AAPL", 100, 150.0, 145.0, self.market_data
        )
        calculation_time = time.time() - start_time
        
        assert calculation_time < 1.0  # Should complete within 1 second
        assert risk_metrics.symbol == "AAPL"
    
    def test_portfolio_performance(self):
        """Test portfolio risk calculation performance"""
        start_time = time.time()
        portfolio_metrics = self.bridge.calculate_portfolio_risk(
            self.positions, self.market_data_dict
        )
        calculation_time = time.time() - start_time
        
        assert calculation_time < 5.0  # Should complete within 5 seconds
        assert len(portfolio_metrics.position_risks) == 50
        assert portfolio_metrics.total_value > 0
    
    def test_var_calculation_performance(self):
        """Test VaR calculation performance"""
        start_time = time.time()
        var_result = self.bridge._calculate_var(
            "AAPL", self.market_data, 100, 150.0
        )
        calculation_time = time.time() - start_time
        
        assert calculation_time < 1.0  # Should complete within 1 second
        assert var_result.symbol == "AAPL"
        assert var_result.var_1d >= 0

class TestRiskBridgeIntegration:
    """Integration tests for RiskBridge"""
    
    def setup_method(self):
        """Set up integration test fixtures"""
        self.config = RiskBridgeConfig(
            risk_mode=RiskMode.BACKTESTING,
            enable_var_calculation=True
        )
        self.bridge = RiskBridge(self.config)
    
    def test_execution_bridge_integration(self):
        """Test integration with ExecutionBridge"""
        # Simulate execution results from ExecutionBridge
        execution_results = [
            {'symbol': 'AAPL', 'side': 'buy', 'quantity': 100, 'execution_price': 150.0},
            {'symbol': 'SPY', 'sell': 'sell', 'quantity': 50, 'execution_price': 400.0}
        ]
        
        # Convert to positions for risk calculation
        positions = {}
        for result in execution_results:
            symbol = result['symbol']
            positions[symbol] = {
                'quantity': result['quantity'],
                'current_price': result['execution_price'],
                'avg_price': result['execution_price']  # Assume same for simplicity
            }
        
        # Calculate risk
        market_data = {
            'AAPL': pd.DataFrame({'close': [150.0] * 10}),
            'SPY': pd.DataFrame({'close': [400.0] * 10})
        }
        
        portfolio_metrics = self.bridge.calculate_portfolio_risk(positions, market_data)
        
        assert len(portfolio_metrics.position_risks) == 2
        assert portfolio_metrics.total_value > 0
        assert all(result.status == "filled" for result in execution_results)
    
    def test_signal_bridge_integration(self):
        """Test integration with SignalBridge"""
        # Simulate signals from SignalBridge
        signals = {
            'AAPL': 0.8,  # Strong buy signal
            'SPY': -0.3,  # Weak sell signal
            'MSFT': 0.5   # Moderate buy signal
        }
        
        # Convert signals to positions
        positions = {}
        for symbol, signal in signals.items():
            if abs(signal) > 0.1:  # Only trade if signal is significant
                quantity = int(abs(signal) * 100)  # Scale quantity by signal strength
                positions[symbol] = {
                    'quantity': quantity,
                    'current_price': 150.0,
                    'avg_price': 145.0
                }
        
        # Calculate risk
        market_data = {
            symbol: pd.DataFrame({'close': [150.0] * 10}) for symbol in positions.keys()
        }
        
        portfolio_metrics = self.bridge.calculate_portfolio_risk(positions, market_data)
        
        assert len(portfolio_metrics.position_risks) == 3
        assert portfolio_metrics.total_value > 0
        
        # Verify risk levels are appropriate
        for symbol, risk_metrics in portfolio_metrics.position_risks.items():
            assert isinstance(risk_metrics.risk_level, RiskLevel)
            assert risk_metrics.unrealized_pnl > 0  # All positions should be profitable
    
    def test_portfolio_state_integration(self):
        """Test integration with portfolio state"""
        portfolio_state = {
            'total_value': 100000,
            'cash': 50000,
            'peak_value': 110000,
            'max_drawdown': 0.05,
            'daily_pnl': 1000,
            'current_risk': 0.015
        }
        
        positions = {
            'AAPL': {'quantity': 100, 'current_price': 150.0, 'avg_price': 145.0}
        }
        
        market_data = {'AAPL': pd.DataFrame({'close': [150.0] * 10})}
        
        portfolio_metrics = self.bridge.calculate_portfolio_risk(positions, market_data, portfolio_state)
        
        assert portfolio_metrics.total_value > 0
        assert portfolio_metrics.current_drawdown >= 0
        assert portfolio_metrics.max_drawdown >= 0
        assert portfolio_metrics.daily_pnl == 1000
    
    def test_market_data_integration(self):
        """Test integration with market data"""
        # Create realistic market data
        dates = pd.date_range(start='2024-01-01', end='2024-01-10', freq='D')
        market_data = pd.DataFrame({
            'open': [100 + i for i in range(len(dates))],
            'high': [105 + i for i in range(len(dates))],
            'low': [95 + i for i in range(len(dates))],
            'close': [102 + i for i in range(len(dates))],
            'volume': [1000000 + i * 10000 for i in range(len(dates))]
        }, index=dates)
        
        risk_metrics = self.bridge.calculate_position_risk(
            "AAPL", 100, 150.0, 145.0, market_data
        )
        
        assert risk_metrics.symbol == "AAPL"
        assert risk_metrics.var_1d >= 0
        assert risk_metrics.volatility >= 0
        assert risk_metrics.beta == 1.0

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"]) 