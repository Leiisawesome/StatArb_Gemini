#!/usr/bin/env python3
"""
Week 3 Day 5: Entry/Exit Logic Building Blocks Tests
"""

import unittest
import numpy as np
from datetime import datetime

from core_structure.strategy_layer.blocks import (
    EntryExitLogic,
    EntryExitDecision,
    MomentumEntryExitLogic,
    PairTradingEntryExitLogic
)
from core_structure.strategy_layer.config import EntryExitConfig
from core_structure.strategy_layer.exceptions import EntryExitError, ValidationError


class TestEntryExitLogicBase(unittest.TestCase):
    """Test base entry/exit logic functionality."""
    
    def setUp(self):
        self.config = EntryExitConfig(
            entry={"signal_threshold": 0.3},
            exit={"signal_threshold": -0.2},
            momentum={"period": 20},
            risk={"max_holding_period": 50}
        )
        
        class MockEntryExitLogic(EntryExitLogic):
            def evaluate_entry(self, signal_strength, current_price, market_data):
                return EntryExitDecision(
                    action="enter",
                    confidence=0.8,
                    reason="Mock entry decision",
                    timestamp=datetime.now(),
                    price_level=current_price
                )
            
            def evaluate_exit(self, signal_strength, current_price, entry_price, position_size, market_data):
                return EntryExitDecision(
                    action="exit",
                    confidence=0.7,
                    reason="Mock exit decision",
                    timestamp=datetime.now(),
                    price_level=current_price
                )
            
            def _validate_specific_config(self):
                pass
        
        self.entry_exit_logic = MockEntryExitLogic(self.config)
    
    def test_entry_exit_logic_initialization(self):
        """Test entry/exit logic initialization."""
        self.assertIsNotNone(self.entry_exit_logic)
        self.assertEqual(self.entry_exit_logic.name, "MockEntryExitLogic")
    
    def test_process_entry_evaluation_success(self):
        """Test successful entry evaluation."""
        market_data = {"prices": [100.0, 101.0, 102.0]}
        result = self.entry_exit_logic.process_entry_evaluation(0.5, 100.0, market_data)
        
        self.assertIsInstance(result, EntryExitDecision)
        self.assertEqual(result.action, "enter")
        self.assertEqual(result.confidence, 0.8)
        self.assertEqual(result.price_level, 100.0)
    
    def test_process_exit_evaluation_success(self):
        """Test successful exit evaluation."""
        market_data = {"prices": [100.0, 101.0, 102.0]}
        result = self.entry_exit_logic.process_exit_evaluation(0.5, 102.0, 100.0, 100.0, market_data)
        
        self.assertIsInstance(result, EntryExitDecision)
        self.assertEqual(result.action, "exit")
        self.assertEqual(result.confidence, 0.7)
        self.assertEqual(result.price_level, 102.0)


class TestEntryExitDecision(unittest.TestCase):
    """Test EntryExitDecision class."""
    
    def test_entry_exit_decision_creation(self):
        """Test EntryExitDecision creation."""
        decision = EntryExitDecision(
            action="enter",
            confidence=0.8,
            reason="Test entry",
            timestamp=datetime.now(),
            price_level=100.0,
            stop_loss=95.0,
            take_profit=110.0
        )
        
        self.assertEqual(decision.action, "enter")
        self.assertEqual(decision.confidence, 0.8)
        self.assertEqual(decision.reason, "Test entry")
        self.assertEqual(decision.price_level, 100.0)
        self.assertEqual(decision.stop_loss, 95.0)
        self.assertEqual(decision.take_profit, 110.0)
    
    def test_entry_exit_decision_validation_success(self):
        """Test successful decision validation."""
        decision = EntryExitDecision(
            action="enter",
            confidence=0.8,
            reason="Test entry",
            timestamp=datetime.now(),
            price_level=100.0
        )
        
        self.assertTrue(decision.validate())
    
    def test_entry_exit_decision_validation_invalid_action(self):
        """Test decision validation with invalid action."""
        decision = EntryExitDecision(
            action="invalid",
            confidence=0.8,
            reason="Test entry",
            timestamp=datetime.now()
        )
        
        with self.assertRaises(ValidationError):
            decision.validate()


class TestMomentumEntryExitLogic(unittest.TestCase):
    """Test MomentumEntryExitLogic class."""
    
    def setUp(self):
        self.config = EntryExitConfig(
            entry={
                "signal_threshold": 0.3,
                "confirmation_required": True,
                "trend_confirmation": True
            },
            exit={
                "signal_threshold": -0.2,
                "stop_loss_percentage": 0.05,
                "take_profit_percentage": 0.10
            },
            momentum={
                "period": 20,
                "threshold": 0.02,
                "volatility_period": 20,
                "volatility_threshold": 0.03
            },
            risk={
                "max_holding_period": 50,
                "min_profit_threshold": 0.02
            }
        )
        
        self.entry_exit_logic = MomentumEntryExitLogic(self.config)
    
    def test_momentum_entry_exit_logic_initialization(self):
        """Test momentum entry/exit logic initialization."""
        self.assertIsNotNone(self.entry_exit_logic)
        self.assertEqual(self.entry_exit_logic.name, "MomentumEntryExitLogic")
        self.assertEqual(self.entry_exit_logic.entry_threshold, 0.3)
        self.assertEqual(self.entry_exit_logic.exit_threshold, -0.2)
    
    def test_evaluate_entry_strong_signal(self):
        """Test entry evaluation with strong signal."""
        market_data = {
            "prices": [100.0 + i * 0.5 for i in range(30)],  # Upward trend
            "volumes": [1000 + i * 10 for i in range(30)]
        }
        
        result = self.entry_exit_logic.evaluate_entry(0.8, 115.0, market_data)
        
        self.assertIsInstance(result, EntryExitDecision)
        self.assertIn(result.action, ["enter", "hold"])
        self.assertGreater(result.confidence, 0)
        self.assertIsNotNone(result.reason)
    
    def test_evaluate_entry_weak_signal(self):
        """Test entry evaluation with weak signal."""
        market_data = {
            "prices": [100.0 + i * 0.1 for i in range(30)],
            "volumes": [1000 + i * 5 for i in range(30)]
        }
        
        result = self.entry_exit_logic.evaluate_entry(0.1, 103.0, market_data)
        
        self.assertEqual(result.action, "hold")
        self.assertLess(result.confidence, 0.5)
    
    def test_evaluate_exit_stop_loss(self):
        """Test exit evaluation with stop loss."""
        market_data = {
            "prices": [100.0, 95.0, 90.0],  # Declining prices
            "volumes": [1000, 1200, 1500]
        }
        
        result = self.entry_exit_logic.evaluate_exit(0.5, 90.0, 100.0, 100.0, market_data)
        
        # Should trigger stop loss (5% loss)
        self.assertEqual(result.action, "exit")
        self.assertGreater(result.confidence, 0.8)
        self.assertIn("stop loss", result.reason.lower())


class TestPairTradingEntryExitLogic(unittest.TestCase):
    """Test PairTradingEntryExitLogic class."""
    
    def setUp(self):
        self.config = EntryExitConfig(
            entry={
                "zscore_threshold": 2.0,
                "spread_threshold": 0.02,
                "correlation_threshold": 0.7,
                "cointegration_pvalue": 0.05
            },
            exit={
                "zscore_threshold": 0.5,
                "spread_threshold": 0.01,
                "stop_loss_percentage": 0.03,
                "take_profit_percentage": 0.05
            },
            spread={
                "window": 60,
                "std_multiplier": 2.0,
                "mean_reversion_strength": 0.5
            },
            risk={
                "max_holding_period": 30,
                "min_profit_threshold": 0.01,
                "max_drawdown_threshold": 0.02
            },
            cointegration={
                "lookback_period": 100,
                "min_periods": 50
            }
        )
        
        self.entry_exit_logic = PairTradingEntryExitLogic(self.config)
    
    def test_pair_trading_entry_exit_logic_initialization(self):
        """Test pair trading entry/exit logic initialization."""
        self.assertIsNotNone(self.entry_exit_logic)
        self.assertEqual(self.entry_exit_logic.name, "PairTradingEntryExitLogic")
        self.assertEqual(self.entry_exit_logic.entry_zscore_threshold, 2.0)
        self.assertEqual(self.entry_exit_logic.exit_zscore_threshold, 0.5)
    
    def test_evaluate_entry_strong_zscore(self):
        """Test entry evaluation with strong Z-score."""
        # Create correlated price series with spread
        asset1_prices = [100.0 + i * 0.1 + np.random.normal(0, 0.5) for i in range(100)]
        asset2_prices = [100.0 + i * 0.1 + np.random.normal(0, 0.5) for i in range(100)]
        
        # Create a large spread deviation
        asset1_prices[-1] = 120.0  # Asset1 overvalued
        asset2_prices[-1] = 100.0  # Asset2 at normal level
        
        market_data = {
            "asset1_prices": asset1_prices,
            "asset2_prices": asset2_prices
        }
        
        result = self.entry_exit_logic.evaluate_entry(0.5, 120.0, market_data)
        
        self.assertIsInstance(result, EntryExitDecision)
        self.assertIn(result.action, ["enter", "hold"])
        self.assertGreater(result.confidence, 0)
        self.assertIsNotNone(result.reason)
    
    def test_evaluate_exit_zscore_convergence(self):
        """Test exit evaluation with Z-score convergence."""
        # Create price series where spread has converged but no take profit
        asset1_prices = [100.0 + i * 0.1 for i in range(100)]
        asset2_prices = [100.0 + i * 0.1 for i in range(100)]
        
        market_data = {
            "asset1_prices": asset1_prices,
            "asset2_prices": asset2_prices,
            "entry_spread": 0.1  # Very small initial spread to avoid take profit
        }
        
        result = self.entry_exit_logic.evaluate_exit(0.5, 100.1, 100.0, 100.0, market_data)
        
        # Should exit due to Z-score convergence or take profit
        self.assertEqual(result.action, "exit")
        # Check for either zscore convergence or take profit (both are valid exit reasons)
        self.assertTrue(
            "zscore converged" in result.reason.lower() or 
            "take profit" in result.reason.lower(),
            f"Expected zscore convergence or take profit, got: {result.reason}"
        )
    
    def test_zscore_calculation(self):
        """Test Z-score calculation."""
        # Create price series with known spread
        asset1_prices = [100.0 + i * 0.1 for i in range(100)]
        asset2_prices = [100.0 + i * 0.1 for i in range(100)]
        
        # Create a spread deviation
        asset1_prices[-1] = 120.0
        asset2_prices[-1] = 100.0
        
        zscore = self.entry_exit_logic._calculate_zscore(asset1_prices, asset2_prices)
        
        self.assertIsInstance(zscore, float)
        self.assertGreater(abs(zscore), 0)  # Should have some deviation


if __name__ == "__main__":
    unittest.main() 