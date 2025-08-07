#!/usr/bin/env python3
"""
Week 4 Day 1-2: Strategy Manager Implementation Tests

This test file validates the implementation of the strategy management system
including strategy lifecycle management and basic operations.
"""

import unittest
from datetime import datetime

from core_structure.strategy_layer.management import (
    StrategyManager,
    StrategyInfo,
    StrategyState
)
from core_structure.strategy_layer.config import BaseConfig
from core_structure.strategy_layer.exceptions import StrategyError, ValidationError


class TestStrategyInfo(unittest.TestCase):
    """Test StrategyInfo class."""
    
    def test_strategy_info_creation(self):
        """Test StrategyInfo creation."""
        strategy_info = StrategyInfo(
            strategy_id="test_strategy_1",
            strategy_name="Test Strategy",
            strategy_type="momentum",
            state=StrategyState.CREATED,
            created_at=datetime.now()
        )
        
        self.assertEqual(strategy_info.strategy_id, "test_strategy_1")
        self.assertEqual(strategy_info.strategy_name, "Test Strategy")
        self.assertEqual(strategy_info.strategy_type, "momentum")
        self.assertEqual(strategy_info.state, StrategyState.CREATED)
    
    def test_strategy_info_validation_success(self):
        """Test successful strategy info validation."""
        strategy_info = StrategyInfo(
            strategy_id="test_strategy_1",
            strategy_name="Test Strategy",
            strategy_type="momentum",
            state=StrategyState.CREATED,
            created_at=datetime.now()
        )
        
        self.assertTrue(strategy_info.validate())
    
    def test_strategy_info_validation_missing_id(self):
        """Test strategy info validation with missing ID."""
        strategy_info = StrategyInfo(
            strategy_id="",
            strategy_name="Test Strategy",
            strategy_type="momentum",
            state=StrategyState.CREATED,
            created_at=datetime.now()
        )
        
        with self.assertRaises(ValidationError):
            strategy_info.validate()
    
    def test_strategy_info_validation_missing_name(self):
        """Test strategy info validation with missing name."""
        strategy_info = StrategyInfo(
            strategy_id="test_strategy_1",
            strategy_name="",
            strategy_type="momentum",
            state=StrategyState.CREATED,
            created_at=datetime.now()
        )
        
        with self.assertRaises(ValidationError):
            strategy_info.validate()


class TestStrategyManager(unittest.TestCase):
    """Test StrategyManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = BaseConfig()
        self.manager = StrategyManager(self.config)
    
    def test_strategy_manager_initialization(self):
        """Test strategy manager initialization."""
        self.assertIsNotNone(self.manager)
        self.assertEqual(self.manager.get_strategy_count(), 0)
    
    def test_create_strategy_success(self):
        """Test successful strategy creation."""
        strategy_config = {
            "signal_generator": "momentum",
            "risk_manager": "basic",
            "entry_exit_logic": "momentum"
        }
        
        strategy_id = self.manager.create_strategy(
            strategy_id="test_strategy_1",
            strategy_name="Test Strategy",
            strategy_type="momentum",
            strategy_config=strategy_config
        )
        
        self.assertEqual(strategy_id, "test_strategy_1")
        self.assertEqual(self.manager.get_strategy_count(), 1)
        
        # Check strategy info
        strategy_info = self.manager.get_strategy_info(strategy_id)
        self.assertIsNotNone(strategy_info)
        self.assertEqual(strategy_info.strategy_id, "test_strategy_1")
        self.assertEqual(strategy_info.strategy_name, "Test Strategy")
        self.assertEqual(strategy_info.strategy_type, "momentum")
        self.assertEqual(strategy_info.state, StrategyState.CREATED)
    
    def test_create_strategy_duplicate_id(self):
        """Test strategy creation with duplicate ID."""
        strategy_config = {"test": "config"}
        
        # Create first strategy
        self.manager.create_strategy(
            strategy_id="test_strategy_1",
            strategy_name="Test Strategy 1",
            strategy_type="momentum",
            strategy_config=strategy_config
        )
        
        # Try to create second strategy with same ID
        with self.assertRaises(StrategyError):
            self.manager.create_strategy(
                strategy_id="test_strategy_1",
                strategy_name="Test Strategy 2",
                strategy_type="pair_trading",
                strategy_config=strategy_config
            )
    
    def test_start_strategy_success(self):
        """Test successful strategy start."""
        strategy_config = {"test": "config"}
        
        strategy_id = self.manager.create_strategy(
            strategy_id="test_strategy_1",
            strategy_name="Test Strategy",
            strategy_type="momentum",
            strategy_config=strategy_config
        )
        
        result = self.manager.start_strategy(strategy_id)
        self.assertTrue(result)
        
        strategy_info = self.manager.get_strategy_info(strategy_id)
        self.assertEqual(strategy_info.state, StrategyState.ACTIVE)
        self.assertIsNotNone(strategy_info.started_at)
    
    def test_start_strategy_not_found(self):
        """Test starting non-existent strategy."""
        with self.assertRaises(StrategyError):
            self.manager.start_strategy("non_existent_strategy")
    
    def test_stop_strategy_success(self):
        """Test successful strategy stop."""
        strategy_config = {"test": "config"}
        
        strategy_id = self.manager.create_strategy(
            strategy_id="test_strategy_1",
            strategy_name="Test Strategy",
            strategy_type="momentum",
            strategy_config=strategy_config
        )
        
        # Start strategy first
        self.manager.start_strategy(strategy_id)
        
        # Stop strategy
        result = self.manager.stop_strategy(strategy_id)
        self.assertTrue(result)
        
        strategy_info = self.manager.get_strategy_info(strategy_id)
        self.assertEqual(strategy_info.state, StrategyState.STOPPED)
        self.assertIsNotNone(strategy_info.stopped_at)
    
    def test_stop_strategy_not_found(self):
        """Test stopping non-existent strategy."""
        with self.assertRaises(StrategyError):
            self.manager.stop_strategy("non_existent_strategy")
    
    def test_pause_strategy_success(self):
        """Test successful strategy pause."""
        strategy_config = {"test": "config"}
        
        strategy_id = self.manager.create_strategy(
            strategy_id="test_strategy_1",
            strategy_name="Test Strategy",
            strategy_type="momentum",
            strategy_config=strategy_config
        )
        
        # Start strategy first
        self.manager.start_strategy(strategy_id)
        
        # Pause strategy
        result = self.manager.pause_strategy(strategy_id)
        self.assertTrue(result)
        
        strategy_info = self.manager.get_strategy_info(strategy_id)
        self.assertEqual(strategy_info.state, StrategyState.PAUSED)
    
    def test_resume_strategy_success(self):
        """Test successful strategy resume."""
        strategy_config = {"test": "config"}
        
        strategy_id = self.manager.create_strategy(
            strategy_id="test_strategy_1",
            strategy_name="Test Strategy",
            strategy_type="momentum",
            strategy_config=strategy_config
        )
        
        # Start strategy first
        self.manager.start_strategy(strategy_id)
        
        # Pause strategy
        self.manager.pause_strategy(strategy_id)
        
        # Resume strategy
        result = self.manager.resume_strategy(strategy_id)
        self.assertTrue(result)
        
        strategy_info = self.manager.get_strategy_info(strategy_id)
        self.assertEqual(strategy_info.state, StrategyState.ACTIVE)
    
    def test_remove_strategy_success(self):
        """Test successful strategy removal."""
        strategy_config = {"test": "config"}
        
        strategy_id = self.manager.create_strategy(
            strategy_id="test_strategy_1",
            strategy_name="Test Strategy",
            strategy_type="momentum",
            strategy_config=strategy_config
        )
        
        self.assertEqual(self.manager.get_strategy_count(), 1)
        
        # Remove strategy
        result = self.manager.remove_strategy(strategy_id)
        self.assertTrue(result)
        
        self.assertEqual(self.manager.get_strategy_count(), 0)
        self.assertIsNone(self.manager.get_strategy_info(strategy_id))
    
    def test_remove_strategy_not_found(self):
        """Test removing non-existent strategy."""
        with self.assertRaises(StrategyError):
            self.manager.remove_strategy("non_existent_strategy")
    
    def test_get_all_strategies(self):
        """Test getting all strategies."""
        strategy_config = {"test": "config"}
        
        # Create multiple strategies
        self.manager.create_strategy(
            strategy_id="test_strategy_1",
            strategy_name="Test Strategy 1",
            strategy_type="momentum",
            strategy_config=strategy_config
        )
        
        self.manager.create_strategy(
            strategy_id="test_strategy_2",
            strategy_name="Test Strategy 2",
            strategy_type="pair_trading",
            strategy_config=strategy_config
        )
        
        all_strategies = self.manager.get_all_strategies()
        self.assertEqual(len(all_strategies), 2)
        
        strategy_ids = [s.strategy_id for s in all_strategies]
        self.assertIn("test_strategy_1", strategy_ids)
        self.assertIn("test_strategy_2", strategy_ids)
    
    def test_get_strategies_by_state(self):
        """Test getting strategies by state."""
        strategy_config = {"test": "config"}
        
        # Create strategies
        strategy_id_1 = self.manager.create_strategy(
            strategy_id="test_strategy_1",
            strategy_name="Test Strategy 1",
            strategy_type="momentum",
            strategy_config=strategy_config
        )
        
        strategy_id_2 = self.manager.create_strategy(
            strategy_id="test_strategy_2",
            strategy_name="Test Strategy 2",
            strategy_type="pair_trading",
            strategy_config=strategy_config
        )
        
        # Start one strategy
        self.manager.start_strategy(strategy_id_1)
        
        # Get strategies by state
        created_strategies = self.manager.get_strategies_by_state(StrategyState.CREATED)
        active_strategies = self.manager.get_strategies_by_state(StrategyState.ACTIVE)
        
        self.assertEqual(len(created_strategies), 1)
        self.assertEqual(len(active_strategies), 1)
        
        self.assertEqual(created_strategies[0].strategy_id, strategy_id_2)
        self.assertEqual(active_strategies[0].strategy_id, strategy_id_1)
    
    def test_is_strategy_running(self):
        """Test checking if strategy is running."""
        strategy_config = {"test": "config"}
        
        strategy_id = self.manager.create_strategy(
            strategy_id="test_strategy_1",
            strategy_name="Test Strategy",
            strategy_type="momentum",
            strategy_config=strategy_config
        )
        
        # Initially not running
        self.assertFalse(self.manager.is_strategy_running(strategy_id))
        
        # Start strategy
        self.manager.start_strategy(strategy_id)
        self.assertTrue(self.manager.is_strategy_running(strategy_id))
        
        # Stop strategy
        self.manager.stop_strategy(strategy_id)
        self.assertFalse(self.manager.is_strategy_running(strategy_id))
        
        # Non-existent strategy
        self.assertFalse(self.manager.is_strategy_running("non_existent_strategy"))


if __name__ == "__main__":
    unittest.main() 