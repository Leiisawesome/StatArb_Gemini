#!/usr/bin/env python3
"""
Week 4 Day 1-2 Batch 4: Integrated Strategy Manager Implementation Tests
"""

import unittest
from datetime import datetime

from core_structure.strategy_layer.management import (
    IntegratedStrategyManager,
    IntegratedStrategyInfo,
    Dependency,
    DependencyType
)
from core_structure.strategy_layer.config import BaseConfig
from core_structure.strategy_layer.exceptions import StrategyError, ValidationError


class TestIntegratedStrategyInfo(unittest.TestCase):
    """Test IntegratedStrategyInfo class."""
    
    def test_integrated_strategy_info_creation(self):
        """Test IntegratedStrategyInfo creation."""
        from core_structure.strategy_layer.management import StrategyInfo, StrategyState
        
        strategy_info = StrategyInfo(
            strategy_id="test_strategy_1",
            strategy_name="Test Strategy",
            strategy_type="momentum",
            state=StrategyState.CREATED,
            created_at=datetime.now()
        )
        
        integrated_info = IntegratedStrategyInfo(
            strategy_info=strategy_info,
            dependency_status="resolved",
            health_status="healthy"
        )
        
        self.assertEqual(integrated_info.strategy_info.strategy_id, "test_strategy_1")
        self.assertEqual(integrated_info.dependency_status, "resolved")
        self.assertEqual(integrated_info.health_status, "healthy")
    
    def test_integrated_strategy_info_validation_success(self):
        """Test successful integrated strategy info validation."""
        from core_structure.strategy_layer.management import StrategyInfo, StrategyState
        
        strategy_info = StrategyInfo(
            strategy_id="test_strategy_1",
            strategy_name="Test Strategy",
            strategy_type="momentum",
            state=StrategyState.CREATED,
            created_at=datetime.now()
        )
        
        integrated_info = IntegratedStrategyInfo(
            strategy_info=strategy_info,
            dependency_status="resolved",
            health_status="healthy"
        )
        
        self.assertTrue(integrated_info.validate())
    
    def test_integrated_strategy_info_validation_missing_strategy_info(self):
        """Test integrated strategy info validation with missing strategy info."""
        integrated_info = IntegratedStrategyInfo(
            strategy_info=None,
            dependency_status="resolved",
            health_status="healthy"
        )
        
        with self.assertRaises(ValidationError):
            integrated_info.validate()


class TestIntegratedStrategyManager(unittest.TestCase):
    """Test IntegratedStrategyManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = BaseConfig()
        self.manager = IntegratedStrategyManager(self.config)
        
        self.test_config_data = {
            "strategy_type": "momentum",
            "signal_generator": "rsi",
            "risk_manager": "basic"
        }
        
        self.test_dependency = Dependency(
            name="market_data",
            version="1.0.0",
            dependency_type=DependencyType.REQUIRED,
            description="Market data feed dependency"
        )
    
    def test_integrated_strategy_manager_initialization(self):
        """Test integrated strategy manager initialization."""
        self.assertIsNotNone(self.manager)
        self.assertIsNotNone(self.manager.strategy_manager)
        self.assertIsNotNone(self.manager.configuration_manager)
        self.assertIsNotNone(self.manager.dependency_manager)
    
    def test_create_strategy_success(self):
        """Test successful integrated strategy creation."""
        strategy_id = self.manager.create_strategy(
            strategy_id="test_strategy_1",
            strategy_name="Test Strategy",
            strategy_type="momentum",
            config_data=self.test_config_data,
            created_by="test_user",
            description="Test momentum strategy",
            tags=["momentum", "rsi"],
            dependencies=[self.test_dependency]
        )
        
        self.assertEqual(strategy_id, "test_strategy_1")
        
        # Check integrated info
        integrated_info = self.manager.get_integrated_strategy_info(strategy_id)
        self.assertIsNotNone(integrated_info)
        self.assertEqual(integrated_info.strategy_info.strategy_id, "test_strategy_1")
        self.assertEqual(integrated_info.strategy_info.strategy_name, "Test Strategy")
        self.assertEqual(integrated_info.strategy_info.strategy_type, "momentum")
        self.assertIsNotNone(integrated_info.configuration)
        self.assertEqual(integrated_info.dependency_status, "resolved")
    
    def test_create_strategy_no_dependencies(self):
        """Test strategy creation without dependencies."""
        strategy_id = self.manager.create_strategy(
            strategy_id="test_strategy_2",
            strategy_name="Test Strategy 2",
            strategy_type="pair_trading",
            config_data=self.test_config_data,
            created_by="test_user"
        )
        
        self.assertEqual(strategy_id, "test_strategy_2")
        
        # Check integrated info
        integrated_info = self.manager.get_integrated_strategy_info(strategy_id)
        self.assertIsNotNone(integrated_info)
        self.assertEqual(integrated_info.dependency_status, "resolved")
    
    def test_start_strategy_success(self):
        """Test successful strategy start with validation."""
        # Create strategy
        strategy_id = self.manager.create_strategy(
            strategy_id="test_strategy_1",
            strategy_name="Test Strategy",
            strategy_type="momentum",
            config_data=self.test_config_data,
            created_by="test_user",
            dependencies=[self.test_dependency]
        )
        
        # Activate configuration
        config_id = f"{strategy_id}_config"
        self.manager.configuration_manager.activate_configuration(config_id)
        
        # Start strategy
        result = self.manager.start_strategy(strategy_id)
        self.assertTrue(result)
        
        # Check strategy state
        integrated_info = self.manager.get_integrated_strategy_info(strategy_id)
        self.assertEqual(integrated_info.strategy_info.state.value, "active")
    
    def test_start_strategy_no_active_configuration(self):
        """Test starting strategy without active configuration."""
        # Create strategy
        strategy_id = self.manager.create_strategy(
            strategy_id="test_strategy_1",
            strategy_name="Test Strategy",
            strategy_type="momentum",
            config_data=self.test_config_data,
            created_by="test_user"
        )
        
        # Try to start strategy without activating configuration
        result = self.manager.start_strategy(strategy_id)
        self.assertFalse(result)
    
    def test_stop_strategy_success(self):
        """Test successful strategy stop."""
        # Create and start strategy
        strategy_id = self.manager.create_strategy(
            strategy_id="test_strategy_1",
            strategy_name="Test Strategy",
            strategy_type="momentum",
            config_data=self.test_config_data,
            created_by="test_user"
        )
        
        config_id = f"{strategy_id}_config"
        self.manager.configuration_manager.activate_configuration(config_id)
        self.manager.start_strategy(strategy_id)
        
        # Stop strategy
        result = self.manager.stop_strategy(strategy_id)
        self.assertTrue(result)
        
        # Check strategy state
        integrated_info = self.manager.get_integrated_strategy_info(strategy_id)
        self.assertEqual(integrated_info.strategy_info.state.value, "stopped")
    
    def test_get_integrated_strategy_info_not_found(self):
        """Test getting integrated strategy info for non-existent strategy."""
        integrated_info = self.manager.get_integrated_strategy_info("non_existent_strategy")
        self.assertIsNone(integrated_info)
    
    def test_get_all_integrated_strategies(self):
        """Test getting all integrated strategies."""
        # Create multiple strategies
        self.manager.create_strategy(
            strategy_id="test_strategy_1",
            strategy_name="Test Strategy 1",
            strategy_type="momentum",
            config_data=self.test_config_data,
            created_by="test_user"
        )
        
        self.manager.create_strategy(
            strategy_id="test_strategy_2",
            strategy_name="Test Strategy 2",
            strategy_type="pair_trading",
            config_data=self.test_config_data,
            created_by="test_user"
        )
        
        all_strategies = self.manager.get_all_integrated_strategies()
        self.assertEqual(len(all_strategies), 2)
        
        strategy_ids = [s.strategy_info.strategy_id for s in all_strategies]
        self.assertIn("test_strategy_1", strategy_ids)
        self.assertIn("test_strategy_2", strategy_ids)
    
    def test_get_strategies_by_health_status(self):
        """Test getting strategies by health status."""
        # Create strategy
        strategy_id = self.manager.create_strategy(
            strategy_id="test_strategy_1",
            strategy_name="Test Strategy",
            strategy_type="momentum",
            config_data=self.test_config_data,
            created_by="test_user"
        )
        
        # Get strategies by health status
        healthy_strategies = self.manager.get_strategies_by_health_status("healthy")
        self.assertEqual(len(healthy_strategies), 1)
        self.assertEqual(healthy_strategies[0].strategy_info.strategy_id, strategy_id)
        
        # Get non-existent health status
        error_strategies = self.manager.get_strategies_by_health_status("error")
        self.assertEqual(len(error_strategies), 0)
    
    def test_update_strategy_configuration_success(self):
        """Test successful strategy configuration update."""
        # Create strategy
        strategy_id = self.manager.create_strategy(
            strategy_id="test_strategy_1",
            strategy_name="Test Strategy",
            strategy_type="momentum",
            config_data=self.test_config_data,
            created_by="test_user"
        )
        
        # Activate configuration
        config_id = f"{strategy_id}_config"
        self.manager.configuration_manager.activate_configuration(config_id)
        
        # Update configuration
        updated_config_data = {
            "strategy_type": "momentum",
            "signal_generator": "macd",  # Changed from rsi
            "risk_manager": "basic"
        }
        
        new_config_id = self.manager.update_strategy_configuration(
            strategy_id=strategy_id,
            config_data=updated_config_data,
            updated_by="test_user_2",
            description="Updated configuration"
        )
        
        self.assertNotEqual(new_config_id, config_id)
        self.assertTrue(new_config_id.startswith(f"{strategy_id}_config_v"))
    
    def test_update_strategy_configuration_no_active_config(self):
        """Test updating strategy configuration without active configuration."""
        # Create strategy
        strategy_id = self.manager.create_strategy(
            strategy_id="test_strategy_1",
            strategy_name="Test Strategy",
            strategy_type="momentum",
            config_data=self.test_config_data,
            created_by="test_user"
        )
        
        # Try to update configuration without activating it
        # This should work now because we fall back to direct configuration lookup
        new_config_id = self.manager.update_strategy_configuration(
            strategy_id=strategy_id,
            config_data=self.test_config_data,
            updated_by="test_user_2"
        )
        
        # Verify that a new configuration was created
        self.assertNotEqual(new_config_id, f"{strategy_id}_config")
        self.assertTrue(new_config_id.startswith(f"{strategy_id}_config_v"))
    
    def test_add_strategy_dependency_success(self):
        """Test successful dependency addition."""
        # Create strategy
        strategy_id = self.manager.create_strategy(
            strategy_id="test_strategy_1",
            strategy_name="Test Strategy",
            strategy_type="momentum",
            config_data=self.test_config_data,
            created_by="test_user"
        )
        
        # Add dependency
        new_dependency = Dependency(
            name="risk_manager",
            version="1.0.0",
            dependency_type=DependencyType.REQUIRED
        )
        
        result = self.manager.add_strategy_dependency(strategy_id, new_dependency)
        self.assertTrue(result)
        
        # Check dependencies
        dependencies = self.manager.dependency_manager.get_dependencies(strategy_id)
        self.assertEqual(len(dependencies), 1)
        self.assertEqual(dependencies[0].name, "risk_manager")
    
    def test_perform_health_check(self):
        """Test health check performance."""
        # Create strategy
        strategy_id = self.manager.create_strategy(
            strategy_id="test_strategy_1",
            strategy_name="Test Strategy",
            strategy_type="momentum",
            config_data=self.test_config_data,
            created_by="test_user"
        )
        
        # Perform health check
        health_status = self.manager.perform_health_check(strategy_id)
        self.assertIn(health_status, ["healthy", "configuration_issue"])
        
        # Check health status
        stored_health_status = self.manager.get_health_status(strategy_id)
        self.assertEqual(stored_health_status, health_status)
    
    def test_get_system_status(self):
        """Test getting system status."""
        # Create strategies
        self.manager.create_strategy(
            strategy_id="test_strategy_1",
            strategy_name="Test Strategy 1",
            strategy_type="momentum",
            config_data=self.test_config_data,
            created_by="test_user"
        )
        
        self.manager.create_strategy(
            strategy_id="test_strategy_2",
            strategy_name="Test Strategy 2",
            strategy_type="pair_trading",
            config_data=self.test_config_data,
            created_by="test_user"
        )
        
        # Get system status
        system_status = self.manager.get_system_status()
        
        self.assertIn("status_counts", system_status)
        self.assertIn("state_counts", system_status)
        self.assertIn("last_updated", system_status)
        
        self.assertEqual(system_status["status_counts"]["total_strategies"], 2)
        self.assertEqual(system_status["state_counts"]["created"], 2)


if __name__ == "__main__":
    unittest.main() 