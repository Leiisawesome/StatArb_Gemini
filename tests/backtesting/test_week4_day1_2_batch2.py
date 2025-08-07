#!/usr/bin/env python3
"""
Week 4 Day 1-2 Batch 2: Configuration Manager Implementation Tests
"""

import unittest
from datetime import datetime

from core_structure.strategy_layer.management import (
    ConfigurationManager,
    StrategyConfiguration,
    ConfigMetadata,
    ConfigVersion
)
from core_structure.strategy_layer.config import BaseConfig
from core_structure.strategy_layer.exceptions import StrategyError, ValidationError


class TestConfigMetadata(unittest.TestCase):
    """Test ConfigMetadata class."""
    
    def test_config_metadata_creation(self):
        """Test ConfigMetadata creation."""
        metadata = ConfigMetadata(
            config_id="test_config_1",
            version="1.0.0",
            version_type=ConfigVersion.DRAFT,
            created_at=datetime.now(),
            created_by="test_user",
            description="Test configuration"
        )
        
        self.assertEqual(metadata.config_id, "test_config_1")
        self.assertEqual(metadata.version, "1.0.0")
        self.assertEqual(metadata.version_type, ConfigVersion.DRAFT)
    
    def test_config_metadata_validation_success(self):
        """Test successful config metadata validation."""
        metadata = ConfigMetadata(
            config_id="test_config_1",
            version="1.0.0",
            version_type=ConfigVersion.DRAFT,
            created_at=datetime.now(),
            created_by="test_user",
            description="Test configuration"
        )
        
        self.assertTrue(metadata.validate())
    
    def test_config_metadata_validation_missing_id(self):
        """Test config metadata validation with missing ID."""
        metadata = ConfigMetadata(
            config_id="",
            version="1.0.0",
            version_type=ConfigVersion.DRAFT,
            created_at=datetime.now(),
            created_by="test_user",
            description="Test configuration"
        )
        
        with self.assertRaises(ValidationError):
            metadata.validate()


class TestStrategyConfiguration(unittest.TestCase):
    """Test StrategyConfiguration class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.metadata = ConfigMetadata(
            config_id="test_config_1",
            version="1.0.0",
            version_type=ConfigVersion.DRAFT,
            created_at=datetime.now(),
            created_by="test_user",
            description="Test configuration"
        )
        
        self.config_data = {
            "strategy_type": "momentum",
            "signal_generator": "rsi",
            "risk_manager": "basic"
        }
    
    def test_strategy_configuration_creation(self):
        """Test StrategyConfiguration creation."""
        config = StrategyConfiguration(
            metadata=self.metadata,
            config_data=self.config_data
        )
        
        self.assertEqual(config.metadata.config_id, "test_config_1")
        self.assertEqual(config.config_data["strategy_type"], "momentum")
    
    def test_strategy_configuration_validation_success(self):
        """Test successful strategy configuration validation."""
        config = StrategyConfiguration(
            metadata=self.metadata,
            config_data=self.config_data
        )
        
        self.assertTrue(config.validate())
    
    def test_strategy_configuration_validation_missing_required_fields(self):
        """Test strategy configuration validation with missing required fields."""
        incomplete_config_data = {
            "strategy_type": "momentum"
            # Missing signal_generator and risk_manager
        }
        
        config = StrategyConfiguration(
            metadata=self.metadata,
            config_data=incomplete_config_data
        )
        
        with self.assertRaises(ValidationError):
            config.validate()


class TestConfigurationManager(unittest.TestCase):
    """Test ConfigurationManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = BaseConfig()
        self.manager = ConfigurationManager(self.config)
        
        self.test_config_data = {
            "strategy_type": "momentum",
            "signal_generator": "rsi",
            "risk_manager": "basic"
        }
    
    def test_configuration_manager_initialization(self):
        """Test configuration manager initialization."""
        self.assertIsNotNone(self.manager)
    
    def test_create_configuration_success(self):
        """Test successful configuration creation."""
        config_id = self.manager.create_configuration(
            config_id="test_config_1",
            config_data=self.test_config_data,
            created_by="test_user",
            description="Test momentum configuration",
            tags=["momentum", "rsi"]
        )
        
        self.assertEqual(config_id, "test_config_1")
        
        # Check configuration
        config = self.manager.get_configuration(config_id)
        self.assertIsNotNone(config)
        self.assertEqual(config.metadata.config_id, "test_config_1")
        self.assertEqual(config.metadata.version, "1.0.0")
        self.assertEqual(config.metadata.version_type, ConfigVersion.DRAFT)
        self.assertTrue(config.metadata.validation_status)
    
    def test_create_configuration_duplicate_id(self):
        """Test configuration creation with duplicate ID."""
        # Create first configuration
        self.manager.create_configuration(
            config_id="test_config_1",
            config_data=self.test_config_data,
            created_by="test_user"
        )
        
        # Try to create second configuration with same ID
        with self.assertRaises(StrategyError):
            self.manager.create_configuration(
                config_id="test_config_1",
                config_data=self.test_config_data,
                created_by="test_user"
            )
    
    def test_activate_configuration_success(self):
        """Test successful configuration activation."""
        # Create configuration
        config_id = self.manager.create_configuration(
            config_id="test_config_1",
            config_data=self.test_config_data,
            created_by="test_user"
        )
        
        # Activate configuration
        result = self.manager.activate_configuration(config_id)
        self.assertTrue(result)
        
        # Check configuration state
        config = self.manager.get_configuration(config_id)
        self.assertEqual(config.metadata.version_type, ConfigVersion.ACTIVE)
        
        # Check active configuration
        active_config = self.manager.get_active_configuration("test_config_1")
        self.assertEqual(active_config.metadata.config_id, config_id)
    
    def test_activate_configuration_not_found(self):
        """Test activating non-existent configuration."""
        with self.assertRaises(StrategyError):
            self.manager.activate_configuration("non_existent_config")
    
    def test_update_configuration_success(self):
        """Test successful configuration update."""
        # Create initial configuration
        config_id = self.manager.create_configuration(
            config_id="test_config_1",
            config_data=self.test_config_data,
            created_by="test_user"
        )
        
        # Update configuration
        updated_config_data = {
            "strategy_type": "momentum",
            "signal_generator": "macd",  # Changed from rsi
            "risk_manager": "basic"
        }
        
        new_config_id = self.manager.update_configuration(
            config_id=config_id,
            config_data=updated_config_data,
            updated_by="test_user_2"
        )
        
        self.assertNotEqual(new_config_id, config_id)
        self.assertTrue(new_config_id.startswith("test_config_1_v"))
        
        # Check new configuration
        new_config = self.manager.get_configuration(new_config_id)
        self.assertEqual(new_config.metadata.version, "1.0.1")
        self.assertEqual(new_config.metadata.created_by, "test_user_2")
        self.assertEqual(new_config.config_data["signal_generator"], "macd")
    
    def test_get_configurations_by_tag(self):
        """Test getting configurations by tag."""
        # Create configurations with tags
        self.manager.create_configuration(
            config_id="test_config_1",
            config_data=self.test_config_data,
            created_by="test_user",
            tags=["momentum", "rsi"]
        )
        
        self.manager.create_configuration(
            config_id="test_config_2",
            config_data=self.test_config_data,
            created_by="test_user",
            tags=["momentum", "macd"]
        )
        
        # Get configurations by tag
        momentum_configs = self.manager.get_configurations_by_tag("momentum")
        self.assertEqual(len(momentum_configs), 2)
        
        rsi_configs = self.manager.get_configurations_by_tag("rsi")
        self.assertEqual(len(rsi_configs), 1)
    
    def test_template_management(self):
        """Test template management."""
        # Add template
        template_data = {
            "strategy_type": "momentum",
            "signal_generator": "rsi",
            "risk_manager": "basic"
        }
        
        self.manager.add_template("momentum_template", template_data)
        
        # Get template
        retrieved_template = self.manager.get_template("momentum_template")
        self.assertEqual(retrieved_template, template_data)
        
        # List templates
        templates = self.manager.list_templates()
        self.assertIn("momentum_template", templates)


if __name__ == "__main__":
    unittest.main() 