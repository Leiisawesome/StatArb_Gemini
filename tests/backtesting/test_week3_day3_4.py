#!/usr/bin/env python3
"""
Week 3 Day 3-4: Risk Management Building Blocks Tests
"""

import unittest
import numpy as np
from datetime import datetime

from core_structure.strategy_layer.blocks import (
    PositionSizer,
    PositionSize,
    MomentumPositionSizer,
    PairTradingPositionSizer,
    RiskManager,
    RiskMetrics,
    RiskLimit
)
from core_structure.strategy_layer.config import RiskConfig
from core_structure.strategy_layer.exceptions import PositionError, RiskError, ValidationError


class TestPositionSizerBase(unittest.TestCase):
    """Test base position sizer functionality."""
    
    def setUp(self):
        self.config = RiskConfig(
            position_sizing={"base_allocation": 0.02, "max_allocation": 0.10},
            stop_loss={"percentage": 0.02},
            max_risk=1000.0
        )
        
        class MockPositionSizer(PositionSizer):
            def calculate_position_size(self, signal_strength, portfolio_value, current_price, volatility=None):
                return PositionSize(
                    size=100.0,
                    allocation_percentage=0.05,
                    risk_amount=20.0,
                    confidence=0.8,
                    timestamp=datetime.now()
                )
            
            def _validate_specific_config(self):
                pass
        
        self.position_sizer = MockPositionSizer(self.config)
    
    def test_position_sizer_initialization(self):
        """Test position sizer initialization."""
        self.assertIsNotNone(self.position_sizer)
        self.assertEqual(self.position_sizer.name, "MockPositionSizer")
    
    def test_process_position_sizing_success(self):
        """Test successful position sizing."""
        result = self.position_sizer.process_position_sizing(0.5, 10000.0, 100.0, 0.15)
        
        self.assertIsInstance(result, PositionSize)
        self.assertEqual(result.size, 100.0)
        self.assertEqual(result.allocation_percentage, 0.05)
        self.assertEqual(result.risk_amount, 20.0)


class TestMomentumPositionSizer(unittest.TestCase):
    """Test MomentumPositionSizer class."""
    
    def setUp(self):
        self.config = RiskConfig(
            position_sizing={
                "base_allocation": 0.02,
                "signal_multiplier": 1.0,
                "max_allocation": 0.10,
                "risk_per_trade": 0.01
            },
            stop_loss={"percentage": 0.02},
            max_risk=1000.0
        )
        
        self.position_sizer = MomentumPositionSizer(self.config)
    
    def test_momentum_position_sizer_initialization(self):
        """Test momentum position sizer initialization."""
        self.assertIsNotNone(self.position_sizer)
        self.assertEqual(self.position_sizer.name, "MomentumPositionSizer")
        self.assertEqual(self.position_sizer.base_allocation, 0.02)
        self.assertEqual(self.position_sizer.max_allocation, 0.10)
    
    def test_calculate_position_size_positive_signal(self):
        """Test position size calculation with positive signal."""
        result = self.position_sizer.calculate_position_size(0.5, 10000.0, 100.0, 0.15)
        
        self.assertIsInstance(result, PositionSize)
        self.assertGreater(result.size, 0)
        self.assertGreater(result.allocation_percentage, 0)
        self.assertGreater(result.risk_amount, 0)
    
    def test_calculate_position_size_negative_signal(self):
        """Test position size calculation with negative signal."""
        result = self.position_sizer.calculate_position_size(-0.5, 10000.0, 100.0, 0.15)
        
        # Should return zero position for negative signal
        self.assertEqual(result.size, 0.0)
        self.assertEqual(result.allocation_percentage, 0.0)
        self.assertEqual(result.risk_amount, 0.0)


class TestPairTradingPositionSizer(unittest.TestCase):
    """Test PairTradingPositionSizer class."""
    
    def setUp(self):
        self.config = RiskConfig(
            position_sizing={
                "base_allocation": 0.02,
                "spread_multiplier": 1.0,
                "max_allocation": 0.10,
                "zscore_threshold": 2.0,
                "risk_per_trade": 0.01
            },
            stop_loss={"percentage": 0.02},
            max_risk=1000.0
        )
        
        self.position_sizer = PairTradingPositionSizer(self.config)
    
    def test_pair_trading_position_sizer_initialization(self):
        """Test pair trading position sizer initialization."""
        self.assertIsNotNone(self.position_sizer)
        self.assertEqual(self.position_sizer.name, "PairTradingPositionSizer")
        self.assertEqual(self.position_sizer.base_allocation, 0.02)
        self.assertEqual(self.position_sizer.max_allocation, 0.10)
    
    def test_calculate_position_size_basic(self):
        """Test basic position size calculation."""
        result = self.position_sizer.calculate_position_size(0.5, 10000.0, 100.0, 0.15)
        
        self.assertIsInstance(result, PositionSize)
        self.assertGreater(result.size, 0)
        self.assertGreater(result.allocation_percentage, 0)
        self.assertGreater(result.risk_amount, 0)
    
    def test_calculate_position_size_with_hedge_ratio(self):
        """Test position size calculation with hedge ratio."""
        result = self.position_sizer.calculate_position_size(
            signal_strength=0.5,
            portfolio_value=10000.0,
            current_price=100.0,
            volatility=0.15,
            asset1_price=100.0,
            asset2_price=50.0,
            hedge_ratio=2.0
        )
        
        self.assertIsInstance(result, PositionSize)
        self.assertGreater(result.size, 0)
        self.assertIn("hedge_ratio", result.metadata)
        self.assertEqual(result.metadata["hedge_ratio"], 2.0)


class TestRiskManager(unittest.TestCase):
    """Test RiskManager class."""
    
    def setUp(self):
        self.config = RiskConfig(
            max_portfolio_risk=1000.0,
            enable_risk_monitoring=True,
            risk_alert_threshold=0.8
        )
        
        self.risk_manager = RiskManager(self.config)
        
        # Generate test returns
        np.random.seed(42)
        self.returns = np.random.normal(0.001, 0.02, 100)  # 0.1% mean, 2% std
        self.market_returns = np.random.normal(0.0005, 0.015, 100)  # 0.05% mean, 1.5% std
    
    def test_risk_manager_initialization(self):
        """Test risk manager initialization."""
        self.assertIsNotNone(self.risk_manager)
        self.assertEqual(self.risk_manager.name, "RiskManager")
        self.assertIsNotNone(self.risk_manager.risk_limits)
    
    def test_calculate_risk_metrics(self):
        """Test risk metrics calculation."""
        risk_metrics = self.risk_manager.calculate_risk_metrics(self.returns, 10000.0)
        
        self.assertIsInstance(risk_metrics, RiskMetrics)
        self.assertGreater(risk_metrics.var_95, 0)
        self.assertGreater(risk_metrics.var_99, 0)
        self.assertGreater(risk_metrics.cvar_95, 0)
        self.assertGreater(risk_metrics.cvar_99, 0)
        self.assertGreater(risk_metrics.volatility, 0)
        self.assertGreaterEqual(risk_metrics.max_drawdown, 0)
    
    def test_calculate_risk_metrics_with_market_data(self):
        """Test risk metrics calculation with market data."""
        risk_metrics = self.risk_manager.calculate_risk_metrics(
            self.returns, 10000.0, self.market_returns
        )
        
        self.assertIsInstance(risk_metrics, RiskMetrics)
        self.assertIsNotNone(risk_metrics.beta)
        self.assertIsNotNone(risk_metrics.correlation)
    
    def test_risk_limit_violations(self):
        """Test risk limit violation detection."""
        # Create high-risk returns
        high_risk_returns = np.random.normal(0.001, 0.10, 100)  # 10% volatility
        
        risk_metrics = self.risk_manager.calculate_risk_metrics(high_risk_returns, 10000.0)
        violations = self.risk_manager.check_risk_limits(risk_metrics)
        
        # Should detect some violations
        self.assertGreater(len(violations), 0)
        violation_types = [v["type"] for v in violations]
        
        # Check that we have some type of violation (VaR, CVaR, drawdown, etc.)
        expected_violations = ["VaR_95_violation", "VaR_99_violation", "CVaR_95_violation", 
                              "CVaR_99_violation", "volatility_violation", "drawdown_violation"]
        detected_violations = [vt for vt in violation_types if vt in expected_violations]
        self.assertGreater(len(detected_violations), 0)
    
    def test_risk_summary(self):
        """Test risk summary generation."""
        # Calculate some risk metrics first
        self.risk_manager.calculate_risk_metrics(self.returns, 10000.0)
        
        summary = self.risk_manager.get_risk_summary()
        
        self.assertIn("name", summary)
        self.assertIn("latest_metrics", summary)
        self.assertIn("total_violations", summary)
        self.assertIn("risk_limits", summary)
        self.assertIn("metrics_history_length", summary)
        self.assertEqual(summary["metrics_history_length"], 1)


if __name__ == "__main__":
    unittest.main() 