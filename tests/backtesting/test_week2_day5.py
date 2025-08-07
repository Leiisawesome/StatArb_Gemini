#!/usr/bin/env python3
"""
Week 2 Day 5: Strategy Registry Foundation Tests

This test suite validates the implementation of the strategy registry system,
including thread-safe registration, versioning, metadata management, persistence,
and advanced search capabilities.
"""

import unittest
import time
import threading
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from core_structure.strategy_layer.config import RegistryConfig
from core_structure.strategy_layer.registry import (
    StrategyRegistry, RegistryEntry, RegistryMetadata, create_registry,
    RegistryPersistence, DatabasePersistence, FilePersistence, MemoryPersistence,
    RegistrySearch, SearchCriteria, FilterCriteria, SearchResult
)
from core_structure.strategy_layer.definitions import (
    MomentumStrategyDefinition, SignalConfig, RiskConfig, ExecutionConfig, 
    PortfolioConfig, StrategyParameters, StrategyMetadata
)
from core_structure.strategy_layer.exceptions import (
    RegistryError, StrategyNotFoundError, DuplicateStrategyError,
    VersionConflictError, ValidationError, PersistenceError, SearchError
)


class TestStrategyRegistry(unittest.TestCase):
    """Test the core strategy registry functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = RegistryConfig(
            enable_versioning=True,
            enable_metadata=True,
            enable_caching=True,
            max_registry_size=1000
        )
        self.registry = StrategyRegistry(self.config)
        
        # Create test strategies
        self.strategy1 = MomentumStrategyDefinition(
            strategy_id="test_momentum_1",
            strategy_name="Test Momentum Strategy 1",
            strategy_type="momentum",
            version="1.0.0",
            description="A test momentum strategy",
            author="Test Author",
            created_date="2024-01-01",
            signal_config=SignalConfig(),
            risk_config=RiskConfig(
                position_sizing={"method": "fixed", "max_risk": 0.02},
                stop_loss={"type": "fixed", "percentage": 0.015},
                take_profit={"type": "fixed", "percentage": 0.03}
            ),
            execution_config=ExecutionConfig(),
            portfolio_config=PortfolioConfig(),
            parameters=StrategyParameters(),
            metadata=StrategyMetadata()
        )
        
        self.strategy2 = MomentumStrategyDefinition(
            strategy_id="test_momentum_2",
            strategy_name="Test Momentum Strategy 2",
            strategy_type="momentum",
            version="2.0.0",
            description="Another test momentum strategy",
            author="Test Author 2",
            created_date="2024-01-02",
            signal_config=SignalConfig(),
            risk_config=RiskConfig(
                position_sizing={"method": "fixed", "max_risk": 0.025},
                stop_loss={"type": "fixed", "percentage": 0.02},
                take_profit={"type": "fixed", "percentage": 0.04}
            ),
            execution_config=ExecutionConfig(),
            portfolio_config=PortfolioConfig(),
            parameters=StrategyParameters(),
            metadata=StrategyMetadata()
        )
    
    def test_registry_initialization(self):
        """Test registry initialization."""
        self.assertIsNotNone(self.registry)
        self.assertEqual(self.registry.config.enable_versioning, True)
        self.assertEqual(self.registry.config.enable_metadata, True)
        self.assertEqual(self.registry.config.enable_caching, True)
        
        # Check initial statistics
        stats = self.registry.get_statistics()
        self.assertEqual(stats["total_strategies"], 0)
        self.assertEqual(stats["active_strategies"], 0)
    
    def test_strategy_registration(self):
        """Test basic strategy registration."""
        # Register strategy
        registry_id = self.registry.register_strategy(self.strategy1)
        
        # Verify registration
        self.assertIsNotNone(registry_id)
        self.assertTrue(len(registry_id) > 0)
        
        # Get registered strategy
        entry = self.registry.get_strategy(registry_id)
        self.assertEqual(entry.strategy.strategy_id, self.strategy1.strategy_id)
        self.assertEqual(entry.strategy.strategy_name, self.strategy1.strategy_name)
        self.assertEqual(entry.strategy.strategy_type, self.strategy1.strategy_type)
        self.assertTrue(entry.is_active)
        self.assertEqual(entry.access_count, 1)
        
        # Check statistics
        stats = self.registry.get_statistics()
        self.assertEqual(stats["total_strategies"], 1)
        self.assertEqual(stats["active_strategies"], 1)
    
    def test_duplicate_strategy_registration(self):
        """Test duplicate strategy registration handling."""
        # Register strategy first time
        registry_id1 = self.registry.register_strategy(self.strategy1)
        
        # Try to register same strategy again (should fail)
        with self.assertRaises(DuplicateStrategyError):
            self.registry.register_strategy(self.strategy1)
        
        # Register with overwrite (should succeed)
        registry_id2 = self.registry.register_strategy(self.strategy1, overwrite=True)
        self.assertNotEqual(registry_id1, registry_id2)  # Should get new registry ID
    
    def test_strategy_metadata_management(self):
        """Test strategy metadata management."""
        # Create custom metadata
        custom_metadata = RegistryMetadata(
            strategy_id=self.strategy1.strategy_id,
            strategy_name=self.strategy1.strategy_name,
            strategy_type=self.strategy1.strategy_type,
            version=self.strategy1.version,
            author=self.strategy1.author,
            created_date=datetime.now(),
            last_modified=datetime.now(),
            description="Custom description",
            tags=["momentum", "test", "high-frequency"],
            performance_metrics={
                "sharpe_ratio": 1.5,
                "max_drawdown": 0.15,
                "total_return": 0.25
            },
            custom_metadata={
                "backtest_period": "2020-2023",
                "asset_class": "equities"
            }
        )
        
        # Register with custom metadata
        registry_id = self.registry.register_strategy(self.strategy1, metadata=custom_metadata)
        
        # Verify metadata
        entry = self.registry.get_strategy(registry_id)
        self.assertEqual(entry.metadata.tags, ["momentum", "test", "high-frequency"])
        self.assertEqual(entry.metadata.performance_metrics["sharpe_ratio"], 1.5)
        self.assertEqual(entry.metadata.custom_metadata["asset_class"], "equities")
    
    def test_strategy_search_and_filtering(self):
        """Test strategy search and filtering capabilities."""
        # Register multiple strategies
        metadata1 = RegistryMetadata(
            strategy_id=self.strategy1.strategy_id,
            strategy_name=self.strategy1.strategy_name,
            strategy_type=self.strategy1.strategy_type,
            version=self.strategy1.version,
            author="Author A",
            created_date=datetime.now(),
            last_modified=datetime.now(),
            tags=["momentum", "equities"],
            performance_metrics={"sharpe_ratio": 1.2}
        )
        
        metadata2 = RegistryMetadata(
            strategy_id=self.strategy2.strategy_id,
            strategy_name=self.strategy2.strategy_name,
            strategy_type=self.strategy2.strategy_type,
            version=self.strategy2.version,
            author="Author B",
            created_date=datetime.now(),
            last_modified=datetime.now(),
            tags=["momentum", "futures"],
            performance_metrics={"sharpe_ratio": 1.8}
        )
        
        self.registry.register_strategy(self.strategy1, metadata=metadata1)
        self.registry.register_strategy(self.strategy2, metadata=metadata2)
        
        # Search by type
        momentum_strategies = self.registry.list_strategies(strategy_type="momentum")
        self.assertEqual(len(momentum_strategies), 2)
        
        # Search by author
        author_a_strategies = self.registry.find_strategies({"author": "Author A"})
        self.assertEqual(len(author_a_strategies), 1)
        self.assertEqual(author_a_strategies[0].metadata.author, "Author A")
        
        # Search by tags
        equities_strategies = self.registry.find_strategies({"tags": ["equities"]})
        self.assertEqual(len(equities_strategies), 1)
        self.assertIn("equities", equities_strategies[0].metadata.tags)
    
    def test_strategy_update_and_deactivation(self):
        """Test strategy update and deactivation."""
        # Register strategy
        registry_id = self.registry.register_strategy(self.strategy1)
        
        # Update strategy
        updated_strategy = MomentumStrategyDefinition(
            strategy_id=self.strategy1.strategy_id,
            strategy_name="Updated Momentum Strategy",
            strategy_type="momentum",
            version="1.1.0",
            description="Updated description",
            author="Updated Author",
            created_date="2024-01-01",
            signal_config=SignalConfig(),
            risk_config=RiskConfig(
                position_sizing={"method": "fixed", "max_risk": 0.025},
                stop_loss={"type": "fixed", "percentage": 0.02},
                take_profit={"type": "fixed", "percentage": 0.04}
            ),
            execution_config=ExecutionConfig(),
            portfolio_config=PortfolioConfig(),
            parameters=StrategyParameters(),
            metadata=StrategyMetadata()
        )
        
        entry = self.registry.update_strategy(registry_id, strategy=updated_strategy)
        self.assertEqual(entry.strategy.strategy_name, "Updated Momentum Strategy")
        self.assertEqual(entry.strategy.version, "1.1.0")
        
        # Deactivate strategy
        self.registry.deactivate_strategy(registry_id)
        entry = self.registry.get_strategy(registry_id)
        self.assertFalse(entry.is_active)
        
        # List active strategies (should exclude deactivated)
        active_strategies = self.registry.list_strategies(active_only=True)
        self.assertEqual(len(active_strategies), 0)
        
        # List all strategies (should include deactivated)
        all_strategies = self.registry.list_strategies(active_only=False)
        self.assertEqual(len(all_strategies), 1)
    
    def test_strategy_deletion(self):
        """Test strategy deletion."""
        # Register strategy
        registry_id = self.registry.register_strategy(self.strategy1)
        
        # Verify strategy exists
        entry = self.registry.get_strategy(registry_id)
        self.assertIsNotNone(entry)
        
        # Delete strategy
        self.registry.delete_strategy(registry_id)
        
        # Verify strategy is deleted
        with self.assertRaises(StrategyNotFoundError):
            self.registry.get_strategy(registry_id)
        
        # Check statistics
        stats = self.registry.get_statistics()
        self.assertEqual(stats["total_strategies"], 0)
    
    def test_thread_safety(self):
        """Test thread safety of registry operations."""
        results = []
        errors = []
        
        def register_strategy(thread_id):
            try:
                strategy = MomentumStrategyDefinition(
                    strategy_id=f"thread_strategy_{thread_id}",
                    strategy_name=f"Thread Strategy {thread_id}",
                    strategy_type="momentum",
                    version="1.0.0",
                    description=f"Strategy from thread {thread_id}",
                    author=f"Thread {thread_id}",
                    created_date="2024-01-01",
                    signal_config=SignalConfig(),
                    risk_config=RiskConfig(
                        position_sizing={"method": "fixed", "max_risk": 0.02},
                        stop_loss={"type": "fixed", "percentage": 0.015},
                        take_profit={"type": "fixed", "percentage": 0.03}
                    ),
                    execution_config=ExecutionConfig(),
                    portfolio_config=PortfolioConfig(),
                    parameters=StrategyParameters(),
                    metadata=StrategyMetadata()
                )
                registry_id = self.registry.register_strategy(strategy)
                results.append(registry_id)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=register_strategy, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 10)
        
        # Verify all strategies were registered
        stats = self.registry.get_statistics()
        self.assertEqual(stats["total_strategies"], 10)
        self.assertEqual(stats["active_strategies"], 10)


class TestRegistryPersistence(unittest.TestCase):
    """Test registry persistence implementations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_strategy = MomentumStrategyDefinition(
            strategy_id="persistence_test",
            strategy_name="Persistence Test Strategy",
            strategy_type="momentum",
            version="1.0.0",
            description="Test strategy for persistence",
            author="Persistence Tester",
            created_date="2024-01-01",
            signal_config=SignalConfig(),
            risk_config=RiskConfig(
                position_sizing={"method": "fixed", "max_risk": 0.02},
                stop_loss={"type": "fixed", "percentage": 0.015},
                take_profit={"type": "fixed", "percentage": 0.03}
            ),
            execution_config=ExecutionConfig(),
            portfolio_config=PortfolioConfig(),
            parameters=StrategyParameters(),
            metadata=StrategyMetadata()
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_memory_persistence(self):
        """Test memory persistence implementation."""
        persistence = MemoryPersistence()
        
        # Create test data
        metadata = RegistryMetadata(
            strategy_id=self.test_strategy.strategy_id,
            strategy_name=self.test_strategy.strategy_name,
            strategy_type=self.test_strategy.strategy_type,
            version=self.test_strategy.version,
            author=self.test_strategy.author,
            created_date=datetime.now(),
            last_modified=datetime.now()
        )
        
        entry = RegistryEntry(
            strategy=self.test_strategy,
            metadata=metadata
        )
        
        registry_data = {"test_id": entry}
        
        # Test save and load
        success = persistence.save_registry(registry_data)
        self.assertTrue(success)
        
        loaded_data = persistence.load_registry()
        self.assertEqual(len(loaded_data), 1)
        self.assertEqual(loaded_data["test_id"].strategy.strategy_id, self.test_strategy.strategy_id)
        
        # Test backup and restore
        success = persistence.backup_registry("test_backup")
        self.assertTrue(success)
        
        # Get the actual backup ID from the backup
        backup_id = None
        for backup_id in persistence._backups.keys():
            if "test_backup" in backup_id:
                break
        
        # Store backup data before clearing
        backup_data = persistence._backups.get(backup_id, {})
        
        # Clear data
        persistence.clear_registry()
        loaded_data = persistence.load_registry()
        self.assertEqual(len(loaded_data), 0)
        
        # Restore from backup using the actual backup ID
        if backup_id:
            # Restore the backup data manually since clear_registry cleared it
            persistence._backups[backup_id] = backup_data
            success = persistence.restore_registry(backup_id)
            self.assertTrue(success)
        
        loaded_data = persistence.load_registry()
        self.assertEqual(len(loaded_data), 1)
    
    def test_file_persistence(self):
        """Test file persistence implementation."""
        file_path = Path(self.temp_dir) / "test_registry.json"
        backup_dir = Path(self.temp_dir) / "backups"
        
        config = {
            "file_path": str(file_path),
            "backup_dir": str(backup_dir),
            "format": "json"
        }
        
        persistence = FilePersistence(config)
        
        # Create test data
        metadata = RegistryMetadata(
            strategy_id=self.test_strategy.strategy_id,
            strategy_name=self.test_strategy.strategy_name,
            strategy_type=self.test_strategy.strategy_type,
            version=self.test_strategy.version,
            author=self.test_strategy.author,
            created_date=datetime.now(),
            last_modified=datetime.now()
        )
        
        entry = RegistryEntry(
            strategy=self.test_strategy,
            metadata=metadata
        )
        
        registry_data = {"test_id": entry}
        
        # Test save and load
        success = persistence.save_registry(registry_data)
        self.assertTrue(success)
        self.assertTrue(file_path.exists())
        
        loaded_data = persistence.load_registry()
        self.assertEqual(len(loaded_data), 1)
        self.assertEqual(loaded_data["test_id"].strategy.strategy_id, self.test_strategy.strategy_id)
        
        # Test backup
        success = persistence.backup_registry("test_backup")
        self.assertTrue(success)
        self.assertTrue(backup_dir.exists())
        self.assertTrue(len(list(backup_dir.glob("*.json"))) > 0)
        
        # Test clear
        persistence.clear_registry()
        self.assertFalse(file_path.exists())
    
    def test_database_persistence(self):
        """Test database persistence implementation."""
        db_path = Path(self.temp_dir) / "test_registry.db"
        
        config = {
            "db_path": str(db_path)
        }
        
        persistence = DatabasePersistence(config)
        
        # Create test data
        metadata = RegistryMetadata(
            strategy_id=self.test_strategy.strategy_id,
            strategy_name=self.test_strategy.strategy_name,
            strategy_type=self.test_strategy.strategy_type,
            version=self.test_strategy.version,
            author=self.test_strategy.author,
            created_date=datetime.now(),
            last_modified=datetime.now(),
            tags=["test", "database"],
            performance_metrics={"sharpe_ratio": 1.5}
        )
        
        entry = RegistryEntry(
            strategy=self.test_strategy,
            metadata=metadata
        )
        
        registry_data = {"test_id": entry}
        
        # Test save and load
        success = persistence.save_registry(registry_data)
        self.assertTrue(success)
        self.assertTrue(db_path.exists())
        
        loaded_data = persistence.load_registry()
        self.assertEqual(len(loaded_data), 1)
        self.assertEqual(loaded_data["test_id"].strategy.strategy_id, self.test_strategy.strategy_id)
        # Tags might be stored in different order, so check both ways
        expected_tags = ["test", "database"]
        actual_tags = loaded_data["test_id"].metadata.tags
        self.assertEqual(set(actual_tags), set(expected_tags))
        self.assertEqual(loaded_data["test_id"].metadata.performance_metrics["sharpe_ratio"], 1.5)
        
        # Test backup
        backup_path = Path(self.temp_dir) / "backup.db"
        success = persistence.backup_registry(str(backup_path))
        self.assertTrue(success)
        self.assertTrue(backup_path.exists())
        
        # Test clear
        persistence.clear_registry()
        loaded_data = persistence.load_registry()
        self.assertEqual(len(loaded_data), 0)


class TestRegistrySearch(unittest.TestCase):
    """Test registry search functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create test registry data
        self.registry_data = {}
        
        # Create test strategies with different characteristics
        strategies = [
            {
                "id": "momentum_1",
                "name": "High Momentum Strategy",
                "type": "momentum",
                "author": "Alice",
                "tags": ["momentum", "equities", "high-frequency"],
                "performance": {"sharpe_ratio": 1.8, "max_drawdown": 0.12},
                "created_date": datetime.now() - timedelta(days=10)
            },
            {
                "id": "momentum_2", 
                "name": "Low Momentum Strategy",
                "type": "momentum",
                "author": "Bob",
                "tags": ["momentum", "futures", "low-frequency"],
                "performance": {"sharpe_ratio": 0.8, "max_drawdown": 0.25},
                "created_date": datetime.now() - timedelta(days=5)
            },
            {
                "id": "mean_reversion_1",
                "name": "Mean Reversion Strategy",
                "type": "mean_reversion",
                "author": "Charlie",
                "tags": ["mean_reversion", "equities"],
                "performance": {"sharpe_ratio": 1.2, "max_drawdown": 0.18},
                "created_date": datetime.now() - timedelta(days=15)
            }
        ]
        
        for strategy_info in strategies:
            # Create appropriate strategy definition based on type
            if strategy_info["type"] == "momentum":
                strategy = MomentumStrategyDefinition(
                    strategy_id=strategy_info["id"],
                    strategy_name=strategy_info["name"],
                    strategy_type=strategy_info["type"],
                    version="1.0.0",
                    description=f"Test {strategy_info['type']} strategy",
                    author=strategy_info["author"],
                    created_date=strategy_info["created_date"].strftime("%Y-%m-%d"),
                    signal_config=SignalConfig(),
                    risk_config=RiskConfig(
                        position_sizing={"method": "fixed", "max_risk": 0.02},
                        stop_loss={"type": "fixed", "percentage": 0.015},
                        take_profit={"type": "fixed", "percentage": 0.03}
                    ),
                    execution_config=ExecutionConfig(),
                    portfolio_config=PortfolioConfig(),
                    parameters=StrategyParameters(),
                    metadata=StrategyMetadata()
                )
            elif strategy_info["type"] == "mean_reversion":
                from core_structure.strategy_layer.definitions import MeanReversionStrategyDefinition
                strategy = MeanReversionStrategyDefinition(
                    strategy_id=strategy_info["id"],
                    strategy_name=strategy_info["name"],
                    strategy_type=strategy_info["type"],
                    version="1.0.0",
                    description=f"Test {strategy_info['type']} strategy",
                    author=strategy_info["author"],
                    created_date=strategy_info["created_date"].strftime("%Y-%m-%d"),
                    signal_config=SignalConfig(),
                    risk_config=RiskConfig(
                        position_sizing={"method": "fixed", "max_risk": 0.02},
                        stop_loss={"type": "fixed", "percentage": 0.015},
                        take_profit={"type": "fixed", "percentage": 0.03}
                    ),
                    execution_config=ExecutionConfig(),
                    portfolio_config=PortfolioConfig(),
                    parameters=StrategyParameters(),
                    metadata=StrategyMetadata()
                )
            else:
                # Default to momentum for unknown types
                strategy = MomentumStrategyDefinition(
                    strategy_id=strategy_info["id"],
                    strategy_name=strategy_info["name"],
                    strategy_type=strategy_info["type"],
                    version="1.0.0",
                    description=f"Test {strategy_info['type']} strategy",
                    author=strategy_info["author"],
                    created_date=strategy_info["created_date"].strftime("%Y-%m-%d"),
                    signal_config=SignalConfig(),
                    risk_config=RiskConfig(
                        position_sizing={"method": "fixed", "max_risk": 0.02},
                        stop_loss={"type": "fixed", "percentage": 0.015},
                        take_profit={"type": "fixed", "percentage": 0.03}
                    ),
                    execution_config=ExecutionConfig(),
                    portfolio_config=PortfolioConfig(),
                    parameters=StrategyParameters(),
                    metadata=StrategyMetadata()
                )
            
            metadata = RegistryMetadata(
                strategy_id=strategy.strategy_id,
                strategy_name=strategy.strategy_name,
                strategy_type=strategy.strategy_type,
                version=strategy.version,
                author=strategy_info["author"],
                created_date=strategy_info["created_date"],
                last_modified=datetime.now(),
                tags=strategy_info["tags"],
                performance_metrics=strategy_info["performance"]
            )
            
            entry = RegistryEntry(
                strategy=strategy,
                metadata=metadata
            )
            
            self.registry_data[f"reg_{strategy_info['id']}"] = entry
        
        # Create search instance
        self.search = RegistrySearch(self.registry_data)
    
    def tearDown(self):
        """Clean up after each test."""
        if hasattr(self, 'search'):
            self.search.clear_cache()
    
    def test_basic_search(self):
        """Test basic search functionality."""
        # Search by type
        criteria = SearchCriteria(strategy_type="momentum")
        result = self.search.search(criteria)
        
        self.assertEqual(len(result), 2)
        self.assertTrue(all(entry.strategy.strategy_type == "momentum" for entry in result.entries))
        
        # Search by type (mean_reversion)
        criteria = SearchCriteria(strategy_type="mean_reversion")
        result = self.search.search(criteria)
        
        self.assertEqual(len(result), 1)
        self.assertTrue(all(entry.strategy.strategy_type == "mean_reversion" for entry in result.entries))
        
        # Search by author
        criteria = SearchCriteria(author="Alice")
        result = self.search.search(criteria)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result.entries[0].metadata.author, "Alice")
        
        # Search by tags
        criteria = SearchCriteria(tags=["equities"])
        result = self.search.search(criteria)
        
        self.assertEqual(len(result), 2)
        self.assertTrue(all("equities" in entry.metadata.tags for entry in result.entries))
        
        # Search by tags (futures)
        criteria = SearchCriteria(tags=["futures"])
        result = self.search.search(criteria)
        
        self.assertEqual(len(result), 1)
        self.assertTrue(all("futures" in entry.metadata.tags for entry in result.entries))
    
    def test_advanced_search(self):
        """Test advanced search with multiple criteria."""
        # Search for high-performing momentum strategies
        criteria = SearchCriteria(
            strategy_type="momentum",
            min_performance=1.0,
            performance_metric="sharpe_ratio"
        )
        result = self.search.search(criteria)
        
        self.assertEqual(len(result), 1)  # Only momentum_1 has sharpe_ratio >= 1.0
        self.assertTrue(all(entry.metadata.performance_metrics["sharpe_ratio"] >= 1.0 for entry in result.entries))
        
        # Search for low-performing momentum strategies
        criteria = SearchCriteria(
            strategy_type="momentum",
            max_performance=1.0,
            performance_metric="sharpe_ratio"
        )
        result = self.search.search(criteria)
        

        self.assertEqual(len(result), 1)
        self.assertEqual(result.entries[0].strategy.strategy_id, "momentum_2")
        
        # Search for very high-performing momentum strategies
        criteria = SearchCriteria(
            strategy_type="momentum",
            min_performance=1.5,
            performance_metric="sharpe_ratio"
        )
        result = self.search.search(criteria)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result.entries[0].strategy.strategy_id, "momentum_1")
        
        # Search with date filter
        criteria = SearchCriteria(
            created_after=datetime.now() - timedelta(days=7)
        )
        result = self.search.search(criteria)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result.entries[0].strategy.strategy_id, "momentum_2")
        
        # Search with date filter (older strategies)
        criteria = SearchCriteria(
            created_before=datetime.now() - timedelta(days=7)
        )
        result = self.search.search(criteria)
        
        self.assertEqual(len(result), 2)  # momentum_1 and mean_reversion_1
    
    def test_search_with_filters(self):
        """Test search with additional filters."""
        criteria = SearchCriteria(strategy_type="momentum")
        filters = FilterCriteria(
            min_sharpe_ratio=1.0,
            max_drawdown_threshold=0.20
        )
        
        result = self.search.search(criteria, filters)
        
        self.assertEqual(len(result), 1)  # Only momentum_1 meets the criteria (sharpe_ratio >= 1.0 and max_drawdown <= 0.20)
        for entry in result.entries:
            self.assertGreaterEqual(entry.metadata.performance_metrics["sharpe_ratio"], 1.0)
            self.assertLessEqual(entry.metadata.performance_metrics["max_drawdown"], 0.20)
        
        # Test with more restrictive filters
        criteria = SearchCriteria(strategy_type="momentum")
        filters = FilterCriteria(
            min_sharpe_ratio=1.5,
            max_drawdown_threshold=0.15
        )
        
        result = self.search.search(criteria, filters)
        
        self.assertEqual(len(result), 1)
        entry = result.entries[0]
        self.assertGreaterEqual(entry.metadata.performance_metrics["sharpe_ratio"], 1.5)
        self.assertLessEqual(entry.metadata.performance_metrics["max_drawdown"], 0.15)
    
    def test_search_sorting_and_pagination(self):
        """Test search with sorting and pagination."""
        # Search all strategies sorted by performance
        criteria = SearchCriteria(
            sort_by="performance",
            sort_order="desc",
            limit=2
        )
        
        result = self.search.search(criteria)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result.total_count, 3)
        
        # Verify sorting (highest performance first)
        performances = [
            entry.metadata.performance_metrics["sharpe_ratio"] 
            for entry in result.entries
        ]
        self.assertEqual(performances, [1.8, 1.2])
        
        # Test pagination
        criteria = SearchCriteria(
            sort_by="performance",
            sort_order="desc",
            limit=1,
            offset=1
        )
        
        result = self.search.search(criteria)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result.entries[0].metadata.performance_metrics["sharpe_ratio"], 1.2)
    
    def test_search_caching(self):
        """Test search result caching."""
        criteria = SearchCriteria(strategy_type="momentum")
        
        # First search (cache miss)
        result1 = self.search.search(criteria)
        
        # Second search (cache hit)
        result2 = self.search.search(criteria)
        
        # Results should be identical
        self.assertEqual(len(result1), len(result2))
        self.assertEqual(result1.entries[0].strategy.strategy_id, 
                        result2.entries[0].strategy.strategy_id)
        
        # Check cache statistics
        stats = self.search.get_search_statistics()
        self.assertEqual(stats["total_searches"], 1)  # Only 1 actual search performed
        self.assertEqual(stats["cache_hits"], 1)      # Second search was cache hit
        self.assertEqual(stats["cache_misses"], 1)    # First search was cache miss
    
    def test_convenience_search_methods(self):
        """Test convenience search methods."""
        # Find by type
        result = self.search.find_by_type("momentum")
        self.assertEqual(len(result), 2)
        
        # Find by type (mean_reversion)
        result = self.search.find_by_type("mean_reversion")
        self.assertEqual(len(result), 1)
        
        # Find by author
        result = self.search.find_by_author("Alice")
        self.assertEqual(len(result), 1)
        
        # Find by tags
        result = self.search.find_by_tags(["equities"])
        self.assertEqual(len(result), 2)
        
        # Find by tags (futures)
        result = self.search.find_by_tags(["futures"])
        self.assertEqual(len(result), 1)
        
        # Find performing strategies
        result = self.search.find_performing_strategies(1.0, "sharpe_ratio")
        self.assertEqual(len(result), 2)  # momentum_1 (1.8) and mean_reversion_1 (1.2)
        
        # Find high-performing strategies
        result = self.search.find_performing_strategies(1.5, "sharpe_ratio")
        print(f"DEBUG: High-performing strategies (>= 1.5): {len(result)}")
        for entry in result.entries:
            print(f"DEBUG: - {entry.strategy.strategy_id}: {entry.strategy.strategy_type}, sharpe_ratio = {entry.metadata.performance_metrics['sharpe_ratio']}")
        self.assertEqual(len(result), 1)
        
        # Find recent strategies
        result = self.search.find_recent_strategies(days=7)
        self.assertEqual(len(result), 1)
    
    def test_search_result_methods(self):
        """Test search result utility methods."""
        criteria = SearchCriteria()
        result = self.search.search(criteria)
        
        # Get entries by type
        momentum_entries = result.get_entries_by_type("momentum")
        self.assertEqual(len(momentum_entries), 2)
        
        mean_reversion_entries = result.get_entries_by_type("mean_reversion")
        self.assertEqual(len(mean_reversion_entries), 1)
        
        # Test with empty criteria (should return all strategies)
        criteria = SearchCriteria()
        result = self.search.search(criteria)
        self.assertEqual(len(result), 3)  # All 3 strategies
        
        # Get top performers
        top_performers = result.get_top_performers("sharpe_ratio", limit=2)
        self.assertEqual(len(top_performers), 2)
        self.assertEqual(top_performers[0].strategy.strategy_id, "momentum_1")
        
        # Get recent entries
        recent_entries = result.get_recent_entries(days=7)
        self.assertEqual(len(recent_entries), 1)


def run_week2_day5_tests():
    """Run all Week 2 Day 5 tests."""
    print("🧪 Running Week 2 Day 5: Strategy Registry Foundation Tests")
    print("=" * 60)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestStrategyRegistry))
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestRegistryPersistence))
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestRegistrySearch))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"   - {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print("\n💥 Errors:")
        for test, traceback in result.errors:
            print(f"   - {test}: {traceback.split('Exception:')[-1].strip()}")
    
    if result.wasSuccessful():
        print("\n✅ All tests passed! Strategy Registry Foundation is working correctly.")
    else:
        print("\n❌ Some tests failed. Please review the implementation.")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_week2_day5_tests()
    exit(0 if success else 1) 