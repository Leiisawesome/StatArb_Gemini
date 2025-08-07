#!/usr/bin/env python3
"""
Week 4 Day 1-2 Batch 3: Dependency Manager Implementation Tests
"""

import unittest
from datetime import datetime

from core_structure.strategy_layer.management import (
    DependencyManager,
    Dependency,
    DependencyResolution,
    DependencyType,
    DependencyStatus
)
from core_structure.strategy_layer.config import BaseConfig
from core_structure.strategy_layer.exceptions import StrategyError, ValidationError


class TestDependency(unittest.TestCase):
    """Test Dependency class."""
    
    def test_dependency_creation(self):
        """Test Dependency creation."""
        dependency = Dependency(
            name="market_data",
            version="1.0.0",
            dependency_type=DependencyType.REQUIRED,
            description="Market data feed dependency"
        )
        
        self.assertEqual(dependency.name, "market_data")
        self.assertEqual(dependency.version, "1.0.0")
        self.assertEqual(dependency.dependency_type, DependencyType.REQUIRED)
        self.assertEqual(dependency.description, "Market data feed dependency")
    
    def test_dependency_validation_success(self):
        """Test successful dependency validation."""
        dependency = Dependency(
            name="market_data",
            version="1.0.0",
            dependency_type=DependencyType.REQUIRED,
            description="Market data feed dependency"
        )
        
        self.assertTrue(dependency.validate())
    
    def test_dependency_validation_missing_name(self):
        """Test dependency validation with missing name."""
        dependency = Dependency(
            name="",
            version="1.0.0",
            dependency_type=DependencyType.REQUIRED
        )
        
        with self.assertRaises(ValidationError):
            dependency.validate()
    
    def test_dependency_validation_missing_version(self):
        """Test dependency validation with missing version."""
        dependency = Dependency(
            name="market_data",
            version="",
            dependency_type=DependencyType.REQUIRED
        )
        
        with self.assertRaises(ValidationError):
            dependency.validate()
    
    def test_dependency_to_dict(self):
        """Test dependency to dictionary conversion."""
        dependency = Dependency(
            name="market_data",
            version="1.0.0",
            dependency_type=DependencyType.REQUIRED,
            description="Market data feed dependency"
        )
        
        dep_dict = dependency.to_dict()
        
        self.assertEqual(dep_dict["name"], "market_data")
        self.assertEqual(dep_dict["version"], "1.0.0")
        self.assertEqual(dep_dict["dependency_type"], "required")
        self.assertEqual(dep_dict["description"], "Market data feed dependency")


class TestDependencyResolution(unittest.TestCase):
    """Test DependencyResolution class."""
    
    def test_dependency_resolution_creation(self):
        """Test DependencyResolution creation."""
        resolution = DependencyResolution(
            strategy_id="test_strategy_1",
            dependencies=[],
            status=DependencyStatus.RESOLVED,
            resolved_dependencies=["market_data"],
            resolution_time=datetime.now()
        )
        
        self.assertEqual(resolution.strategy_id, "test_strategy_1")
        self.assertEqual(resolution.status, DependencyStatus.RESOLVED)
        self.assertEqual(resolution.resolved_dependencies, ["market_data"])
    
    def test_dependency_resolution_validation_success(self):
        """Test successful dependency resolution validation."""
        resolution = DependencyResolution(
            strategy_id="test_strategy_1",
            dependencies=[],
            status=DependencyStatus.RESOLVED
        )
        
        self.assertTrue(resolution.validate())
    
    def test_dependency_resolution_validation_missing_strategy_id(self):
        """Test dependency resolution validation with missing strategy ID."""
        resolution = DependencyResolution(
            strategy_id="",
            dependencies=[],
            status=DependencyStatus.RESOLVED
        )
        
        with self.assertRaises(ValidationError):
            resolution.validate()


class TestDependencyManager(unittest.TestCase):
    """Test DependencyManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = BaseConfig()
        self.manager = DependencyManager(self.config)
        
        self.test_dependency = Dependency(
            name="market_data",
            version="1.0.0",
            dependency_type=DependencyType.REQUIRED,
            description="Market data feed dependency"
        )
    
    def test_dependency_manager_initialization(self):
        """Test dependency manager initialization."""
        self.assertIsNotNone(self.manager)
    
    def test_add_dependency_success(self):
        """Test successful dependency addition."""
        result = self.manager.add_dependency("test_strategy_1", self.test_dependency)
        self.assertTrue(result)
        
        # Check dependencies
        dependencies = self.manager.get_dependencies("test_strategy_1")
        self.assertEqual(len(dependencies), 1)
        self.assertEqual(dependencies[0].name, "market_data")
        self.assertEqual(dependencies[0].version, "1.0.0")
    
    def test_add_dependency_duplicate(self):
        """Test adding duplicate dependency."""
        # Add first dependency
        self.manager.add_dependency("test_strategy_1", self.test_dependency)
        
        # Try to add same dependency again
        with self.assertRaises(StrategyError):
            self.manager.add_dependency("test_strategy_1", self.test_dependency)
    
    def test_remove_dependency_success(self):
        """Test successful dependency removal."""
        # Add dependency
        self.manager.add_dependency("test_strategy_1", self.test_dependency)
        
        # Remove dependency
        result = self.manager.remove_dependency("test_strategy_1", "market_data")
        self.assertTrue(result)
        
        # Check dependencies
        dependencies = self.manager.get_dependencies("test_strategy_1")
        self.assertEqual(len(dependencies), 0)
    
    def test_remove_dependency_not_found(self):
        """Test removing non-existent dependency."""
        # Try to remove dependency without adding it
        with self.assertRaises(StrategyError):
            self.manager.remove_dependency("test_strategy_1", "market_data")
    
    def test_remove_dependency_strategy_not_found(self):
        """Test removing dependency from non-existent strategy."""
        with self.assertRaises(StrategyError):
            self.manager.remove_dependency("non_existent_strategy", "market_data")
    
    def test_get_dependencies_empty(self):
        """Test getting dependencies for strategy with no dependencies."""
        dependencies = self.manager.get_dependencies("test_strategy_1")
        self.assertEqual(len(dependencies), 0)
    
    def test_resolve_dependencies_no_dependencies(self):
        """Test resolving dependencies for strategy with no dependencies."""
        resolution = self.manager.resolve_dependencies("test_strategy_1")
        
        self.assertEqual(resolution.strategy_id, "test_strategy_1")
        self.assertEqual(resolution.status, DependencyStatus.RESOLVED)
        self.assertEqual(len(resolution.dependencies), 0)
        self.assertEqual(len(resolution.resolved_dependencies), 0)
        self.assertEqual(len(resolution.unresolved_dependencies), 0)
        self.assertEqual(len(resolution.conflicts), 0)
    
    def test_resolve_dependencies_success(self):
        """Test successful dependency resolution."""
        # Add dependency
        self.manager.add_dependency("test_strategy_1", self.test_dependency)
        
        # Resolve dependencies
        resolution = self.manager.resolve_dependencies("test_strategy_1")
        
        self.assertEqual(resolution.strategy_id, "test_strategy_1")
        self.assertEqual(resolution.status, DependencyStatus.RESOLVED)
        self.assertEqual(len(resolution.dependencies), 1)
        self.assertEqual(len(resolution.resolved_dependencies), 1)
        self.assertEqual(resolution.resolved_dependencies[0], "market_data")
        self.assertEqual(len(resolution.unresolved_dependencies), 0)
        self.assertEqual(len(resolution.conflicts), 0)
    
    def test_resolve_dependencies_caching(self):
        """Test dependency resolution caching."""
        # Add dependency
        self.manager.add_dependency("test_strategy_1", self.test_dependency)
        
        # Resolve dependencies twice
        resolution1 = self.manager.resolve_dependencies("test_strategy_1")
        resolution2 = self.manager.resolve_dependencies("test_strategy_1")
        
        # Both should be the same (cached)
        self.assertEqual(resolution1.strategy_id, resolution2.strategy_id)
        self.assertEqual(resolution1.status, resolution2.status)
        self.assertEqual(resolution1.resolution_time, resolution2.resolution_time)
    
    def test_validate_dependencies_success(self):
        """Test successful dependency validation."""
        # Add dependency
        self.manager.add_dependency("test_strategy_1", self.test_dependency)
        
        # Validate dependencies
        result = self.manager.validate_dependencies("test_strategy_1")
        self.assertTrue(result)
    
    def test_validate_dependencies_no_dependencies(self):
        """Test dependency validation for strategy with no dependencies."""
        result = self.manager.validate_dependencies("test_strategy_1")
        self.assertTrue(result)
    
    def test_get_dependency_conflicts_no_conflicts(self):
        """Test getting dependency conflicts when none exist."""
        # Add dependency
        self.manager.add_dependency("test_strategy_1", self.test_dependency)
        
        conflicts = self.manager.get_dependency_conflicts("test_strategy_1")
        self.assertEqual(len(conflicts), 0)
    
    def test_get_circular_dependencies_no_circular(self):
        """Test getting circular dependencies when none exist."""
        # Add dependency
        self.manager.add_dependency("test_strategy_1", self.test_dependency)
        
        circular = self.manager.get_circular_dependencies("test_strategy_1")
        self.assertEqual(len(circular), 0)
    
    def test_get_dependency_graph(self):
        """Test getting dependency graph."""
        # Add dependencies
        self.manager.add_dependency("test_strategy_1", self.test_dependency)
        
        dep2 = Dependency(
            name="risk_manager",
            version="1.0.0",
            dependency_type=DependencyType.REQUIRED
        )
        self.manager.add_dependency("test_strategy_2", dep2)
        
        graph = self.manager.get_dependency_graph()
        
        self.assertIn("test_strategy_1", graph)
        self.assertIn("test_strategy_2", graph)
        self.assertIn("market_data", graph["test_strategy_1"])
        self.assertIn("risk_manager", graph["test_strategy_2"])
    
    def test_get_strategies_with_dependencies(self):
        """Test getting strategies with dependencies."""
        # Initially no strategies
        strategies = self.manager.get_strategies_with_dependencies()
        self.assertEqual(len(strategies), 0)
        
        # Add dependency
        self.manager.add_dependency("test_strategy_1", self.test_dependency)
        
        strategies = self.manager.get_strategies_with_dependencies()
        self.assertEqual(len(strategies), 1)
        self.assertIn("test_strategy_1", strategies)
    
    def test_clear_resolution_cache(self):
        """Test clearing resolution cache."""
        # Add dependency and resolve
        self.manager.add_dependency("test_strategy_1", self.test_dependency)
        self.manager.resolve_dependencies("test_strategy_1")
        
        # Clear cache
        self.manager.clear_resolution_cache()
        
        # Cache should be cleared (this is internal, but we can test by adding
        # a new dependency and checking that resolution works)
        dep2 = Dependency(
            name="risk_manager",
            version="1.0.0",
            dependency_type=DependencyType.REQUIRED
        )
        self.manager.add_dependency("test_strategy_1", dep2)
        
        resolution = self.manager.resolve_dependencies("test_strategy_1")
        self.assertEqual(len(resolution.dependencies), 2)


if __name__ == "__main__":
    unittest.main() 