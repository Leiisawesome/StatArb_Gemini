"""
Strategy Engine - Strategy Registry
Comprehensive strategy registration, discovery, and catalog management
"""

import logging
import json
import pickle
import ast
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple, Callable, Set, Type
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import hashlib
import importlib
import inspect
import shutil
import warnings

# Import strategy components
from .strategy_engine import BaseStrategy, StrategyConfig, StrategySignal, StrategyPosition, StrategyMetrics
from .strategy_manager import StrategyTemplate, StrategyDeployment
from .strategy_validator import ValidationResult, ValidationLevel, StrategyValidator

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class RegistryStatus(Enum):
    """Strategy registry status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class StrategyCategory(Enum):
    """Strategy categories"""
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"
    PAIRS_TRADING = "pairs_trading"
    ARBITRAGE = "arbitrage"
    MARKET_MAKING = "market_making"
    TREND_FOLLOWING = "trend_following"
    STATISTICAL_ARBITRAGE = "statistical_arbitrage"
    MACHINE_LEARNING = "machine_learning"
    MULTI_FACTOR = "multi_factor"
    CUSTOM = "custom"


class StrategyComplexity(Enum):
    """Strategy complexity levels"""
    SIMPLE = "simple"       # Basic strategies with few parameters
    MODERATE = "moderate"   # Standard strategies with moderate complexity
    COMPLEX = "complex"     # Advanced strategies with many components
    EXPERT = "expert"       # Sophisticated strategies requiring deep knowledge


@dataclass
class StrategyMetadata:
    """Strategy metadata for registry"""
    
    # Basic information
    strategy_id: str = ""
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    author: str = ""
    created_date: datetime = field(default_factory=datetime.now)
    modified_date: datetime = field(default_factory=datetime.now)
    
    # Classification
    category: StrategyCategory = StrategyCategory.CUSTOM
    complexity: StrategyComplexity = StrategyComplexity.MODERATE
    status: RegistryStatus = RegistryStatus.DEVELOPMENT
    
    # Technical details
    class_name: str = ""
    module_path: str = ""
    file_path: str = ""
    dependencies: List[str] = field(default_factory=list)
    
    # Configuration
    default_config: Optional[Dict[str, Any]] = None
    config_schema: Optional[Dict[str, Any]] = None
    required_data: List[str] = field(default_factory=list)
    
    # Performance and validation
    validation_result: Optional[ValidationResult] = None
    performance_metrics: Optional[Dict[str, float]] = None
    risk_metrics: Optional[Dict[str, float]] = None
    
    # Usage tracking
    usage_count: int = 0
    last_used: Optional[datetime] = None
    deployments: List[str] = field(default_factory=list)
    
    # Documentation and examples
    documentation: str = ""
    examples: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    # Technical metadata
    checksum: str = ""
    file_size: int = 0
    
    # Relationships
    parent_strategy: Optional[str] = None  # For strategy variants
    child_strategies: List[str] = field(default_factory=list)
    related_strategies: List[str] = field(default_factory=list)


@dataclass
class RegistryQuery:
    """Query parameters for strategy search"""
    
    # Basic filters
    name_pattern: Optional[str] = None
    category: Optional[StrategyCategory] = None
    complexity: Optional[StrategyComplexity] = None
    status: Optional[RegistryStatus] = None
    author: Optional[str] = None
    
    # Date filters
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    modified_after: Optional[datetime] = None
    modified_before: Optional[datetime] = None
    
    # Performance filters
    min_sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    min_return: Optional[float] = None
    
    # Technical filters
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    
    # Usage filters
    min_usage_count: Optional[int] = None
    used_after: Optional[datetime] = None
    
    # Sorting and limiting
    sort_by: str = "modified_date"  # name, created_date, modified_date, usage_count
    sort_order: str = "desc"        # asc, desc
    limit: Optional[int] = None


@dataclass
class RegistryStats:
    """Registry statistics"""
    
    total_strategies: int = 0
    active_strategies: int = 0
    production_strategies: int = 0
    
    # By category
    category_counts: Dict[StrategyCategory, int] = field(default_factory=dict)
    
    # By complexity
    complexity_counts: Dict[StrategyComplexity, int] = field(default_factory=dict)
    
    # By status
    status_counts: Dict[RegistryStatus, int] = field(default_factory=dict)
    
    # Usage statistics
    total_usage: int = 0
    most_used_strategy: Optional[str] = None
    recently_added: List[str] = field(default_factory=list)
    recently_modified: List[str] = field(default_factory=list)
    
    # Performance statistics
    avg_sharpe_ratio: Optional[float] = None
    avg_return: Optional[float] = None
    best_performing_strategy: Optional[str] = None
    
    # Registry health
    validation_pass_rate: float = 0.0
    outdated_strategies: List[str] = field(default_factory=list)
    orphaned_files: List[str] = field(default_factory=list)


class StrategyLoader:
    """Load and instantiate strategies"""
    
    def __init__(self):
        self.loaded_modules = {}
        self.loaded_classes = {}
        
        logger.info("Strategy loader initialized")
    
    def load_strategy_class(self, metadata: StrategyMetadata) -> Optional[Type[BaseStrategy]]:
        """Load strategy class from metadata"""
        
        try:
            module_path = metadata.module_path
            class_name = metadata.class_name
            
            # Load module if not already loaded
            if module_path not in self.loaded_modules:
                module = importlib.import_module(module_path)
                self.loaded_modules[module_path] = module
            else:
                module = self.loaded_modules[module_path]
                # Reload module to get latest changes
                importlib.reload(module)
                self.loaded_modules[module_path] = module
            
            # Get class from module
            if hasattr(module, class_name):
                strategy_class = getattr(module, class_name)
                
                # Verify it's a strategy class
                if issubclass(strategy_class, BaseStrategy):
                    self.loaded_classes[f"{module_path}.{class_name}"] = strategy_class
                    return strategy_class
                else:
                    logger.error(f"Class {class_name} is not a BaseStrategy subclass")
                    return None
            else:
                logger.error(f"Class {class_name} not found in module {module_path}")
                return None
                
        except Exception as e:
            logger.error(f"Error loading strategy class: {e}")
            return None
    
    def create_strategy_instance(self, metadata: StrategyMetadata, 
                               config: Optional[StrategyConfig] = None) -> Optional[BaseStrategy]:
        """Create strategy instance"""
        
        try:
            strategy_class = self.load_strategy_class(metadata)
            
            if strategy_class is None:
                return None
            
            # Use provided config or default config
            if config is None and metadata.default_config:
                config = StrategyConfig(**metadata.default_config)
            
            # Create instance
            if config:
                strategy = strategy_class(config)
            else:
                strategy = strategy_class()
            
            # Set strategy ID if available
            if hasattr(strategy, 'strategy_id'):
                strategy.strategy_id = metadata.strategy_id
            
            return strategy
            
        except Exception as e:
            logger.error(f"Error creating strategy instance: {e}")
            return None


class StrategyDiscovery:
    """Discover strategies in filesystem"""
    
    def __init__(self):
        self.discovery_paths = [
            "strategies",
            "core_structure/strategies",
            "custom_strategies"
        ]
        
        logger.info("Strategy discovery initialized")
    
    def discover_strategies(self, search_paths: Optional[List[str]] = None) -> List[StrategyMetadata]:
        """Discover strategies in specified paths"""
        
        try:
            discovered_strategies = []
            paths_to_search = search_paths or self.discovery_paths
            
            for path_str in paths_to_search:
                path = Path(path_str)
                if path.exists():
                    strategies = self._discover_in_path(path)
                    discovered_strategies.extend(strategies)
            
            logger.info(f"Discovered {len(discovered_strategies)} strategies")
            return discovered_strategies
            
        except Exception as e:
            logger.error(f"Error discovering strategies: {e}")
            return []
    
    def _discover_in_path(self, path: Path) -> List[StrategyMetadata]:
        """Discover strategies in a specific path"""
        
        discovered = []
        
        try:
            # Find Python files
            python_files = list(path.rglob("*.py"))
            
            for file_path in python_files:
                if file_path.name.startswith("__"):
                    continue
                
                strategies = self._analyze_file(file_path)
                discovered.extend(strategies)
            
            return discovered
            
        except Exception as e:
            logger.error(f"Error discovering in path {path}: {e}")
            return []
    
    def _analyze_file(self, file_path: Path) -> List[StrategyMetadata]:
        """Analyze a Python file for strategy classes"""
        
        strategies = []
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST to find classes
            tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if class might be a strategy
                    if self._is_strategy_class(node, content):
                        metadata = self._create_metadata_from_ast(node, file_path, content)
                        if metadata:
                            strategies.append(metadata)
            
            return strategies
            
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            return []
    
    def _is_strategy_class(self, class_node: ast.ClassDef, content: str) -> bool:
        """Check if AST class node represents a strategy"""
        
        try:
            # Check if inherits from BaseStrategy
            for base in class_node.bases:
                if isinstance(base, ast.Name) and base.id == "BaseStrategy":
                    return True
                elif isinstance(base, ast.Attribute):
                    # Handle qualified names like module.BaseStrategy
                    if base.attr == "BaseStrategy":
                        return True
            
            # Check for strategy-like patterns in class name
            strategy_patterns = ["Strategy", "Strat", "Trading", "Algorithm"]
            class_name = class_node.name
            
            for pattern in strategy_patterns:
                if pattern in class_name:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking strategy class: {e}")
            return False
    
    def _create_metadata_from_ast(self, class_node: ast.ClassDef, file_path: Path, 
                                content: str) -> Optional[StrategyMetadata]:
        """Create metadata from AST class node"""
        
        try:
            metadata = StrategyMetadata()
            
            # Basic information
            metadata.class_name = class_node.name
            metadata.name = class_node.name
            metadata.file_path = str(file_path)
            
            # Module path (relative to working directory)
            try:
                relative_path = file_path.relative_to(Path.cwd())
                module_path = str(relative_path.with_suffix('')).replace('/', '.')
                metadata.module_path = module_path
            except ValueError:
                metadata.module_path = file_path.stem
            
            # Extract docstring
            if (class_node.body and isinstance(class_node.body[0], ast.Expr) and
                isinstance(class_node.body[0].value, ast.Constant)):
                metadata.description = class_node.body[0].value.value
                metadata.documentation = metadata.description
            
            # Generate strategy ID
            metadata.strategy_id = f"{metadata.module_path}.{metadata.class_name}".lower()
            
            # File metadata
            metadata.file_size = file_path.stat().st_size
            metadata.checksum = self._calculate_file_checksum(file_path)
            metadata.modified_date = datetime.fromtimestamp(file_path.stat().st_mtime)
            
            # Guess category from name
            metadata.category = self._guess_category(class_node.name)
            
            # Set default status
            metadata.status = RegistryStatus.DEVELOPMENT
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error creating metadata: {e}")
            return None
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate file checksum"""
        
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()
        except Exception as e:
            logger.error(f"Error calculating checksum: {e}")
            return ""
    
    def _guess_category(self, class_name: str) -> StrategyCategory:
        """Guess strategy category from class name"""
        
        name_lower = class_name.lower()
        
        if any(word in name_lower for word in ['mean', 'reversion', 'reverting']):
            return StrategyCategory.MEAN_REVERSION
        elif any(word in name_lower for word in ['momentum', 'trend']):
            return StrategyCategory.MOMENTUM
        elif any(word in name_lower for word in ['pairs', 'pair']):
            return StrategyCategory.PAIRS_TRADING
        elif any(word in name_lower for word in ['arbitrage', 'arb']):
            return StrategyCategory.ARBITRAGE
        elif any(word in name_lower for word in ['ml', 'machine', 'learning', 'neural']):
            return StrategyCategory.MACHINE_LEARNING
        else:
            return StrategyCategory.CUSTOM


class StrategyRegistry:
    """
    Comprehensive Strategy Registry
    
    Provides strategy registration, discovery, cataloging, and management capabilities
    including version control, validation tracking, and deployment management.
    """
    
    def __init__(self, registry_path: str = "strategy_registry"):
        """Initialize strategy registry"""
        
        self.registry_path = Path(registry_path)
        self.registry_path.mkdir(exist_ok=True)
        
        # Registry files
        self.metadata_file = self.registry_path / "strategies.json"
        self.index_file = self.registry_path / "index.json"
        self.cache_file = self.registry_path / "cache.pickle"
        
        # Components
        self.loader = StrategyLoader()
        self.discovery = StrategyDiscovery()
        self.validator = StrategyValidator()
        
        # In-memory registry
        self.strategies: Dict[str, StrategyMetadata] = {}
        self.index: Dict[str, Any] = {}
        
        # Load existing registry
        self._load_registry()
        
        logger.info(f"Strategy registry initialized at {self.registry_path}")
    
    def register_strategy(self, strategy_class: Type[BaseStrategy], 
                         metadata: Optional[StrategyMetadata] = None,
                         validate: bool = True) -> str:
        """Register a strategy class"""
        
        try:
            # Create metadata if not provided
            if metadata is None:
                metadata = self._create_metadata_from_class(strategy_class)
            
            # Validate strategy if requested
            if validate:
                strategy_instance = strategy_class()
                validation_result = self.validator.validate_strategy(strategy_instance)
                metadata.validation_result = validation_result
            
            # Store in registry
            strategy_id = metadata.strategy_id
            self.strategies[strategy_id] = metadata
            
            # Update index
            self._update_index(metadata)
            
            # Save registry
            self._save_registry()
            
            logger.info(f"Strategy registered: {strategy_id}")
            return strategy_id
            
        except Exception as e:
            logger.error(f"Error registering strategy: {e}")
            raise
    
    def unregister_strategy(self, strategy_id: str) -> bool:
        """Unregister a strategy"""
        
        try:
            if strategy_id in self.strategies:
                del self.strategies[strategy_id]
                self._rebuild_index()
                self._save_registry()
                
                logger.info(f"Strategy unregistered: {strategy_id}")
                return True
            else:
                logger.warning(f"Strategy not found: {strategy_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error unregistering strategy: {e}")
            return False
    
    def get_strategy(self, strategy_id: str) -> Optional[StrategyMetadata]:
        """Get strategy metadata"""
        
        return self.strategies.get(strategy_id)
    
    def get_strategy_class(self, strategy_id: str) -> Optional[Type[BaseStrategy]]:
        """Get strategy class"""
        
        try:
            metadata = self.get_strategy(strategy_id)
            if metadata:
                return self.loader.load_strategy_class(metadata)
            return None
            
        except Exception as e:
            logger.error(f"Error getting strategy class: {e}")
            return None
    
    def create_strategy_instance(self, strategy_id: str, 
                               config: Optional[StrategyConfig] = None) -> Optional[BaseStrategy]:
        """Create strategy instance"""
        
        try:
            metadata = self.get_strategy(strategy_id)
            if metadata:
                strategy = self.loader.create_strategy_instance(metadata, config)
                
                # Update usage tracking
                if strategy:
                    metadata.usage_count += 1
                    metadata.last_used = datetime.now()
                    self._save_registry()
                
                return strategy
            return None
            
        except Exception as e:
            logger.error(f"Error creating strategy instance: {e}")
            return None
    
    def search_strategies(self, query: Optional[RegistryQuery] = None) -> List[StrategyMetadata]:
        """Search strategies based on query"""
        
        try:
            if query is None:
                query = RegistryQuery()
            
            results = []
            
            for strategy_id, metadata in self.strategies.items():
                if self._matches_query(metadata, query):
                    results.append(metadata)
            
            # Sort results
            results = self._sort_results(results, query.sort_by, query.sort_order)
            
            # Apply limit
            if query.limit:
                results = results[:query.limit]
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching strategies: {e}")
            return []
    
    def list_strategies(self, category: Optional[StrategyCategory] = None,
                       status: Optional[RegistryStatus] = None) -> List[str]:
        """List strategy IDs with optional filters"""
        
        try:
            strategy_ids = []
            
            for strategy_id, metadata in self.strategies.items():
                include = True
                
                if category and metadata.category != category:
                    include = False
                
                if status and metadata.status != status:
                    include = False
                
                if include:
                    strategy_ids.append(strategy_id)
            
            return sorted(strategy_ids)
            
        except Exception as e:
            logger.error(f"Error listing strategies: {e}")
            return []
    
    def update_strategy_metadata(self, strategy_id: str, 
                               updates: Dict[str, Any]) -> bool:
        """Update strategy metadata"""
        
        try:
            if strategy_id not in self.strategies:
                logger.warning(f"Strategy not found: {strategy_id}")
                return False
            
            metadata = self.strategies[strategy_id]
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(metadata, key):
                    setattr(metadata, key, value)
            
            # Update modification date
            metadata.modified_date = datetime.now()
            
            # Update index
            self._update_index(metadata)
            
            # Save registry
            self._save_registry()
            
            logger.info(f"Strategy metadata updated: {strategy_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating strategy metadata: {e}")
            return False
    
    def validate_strategy(self, strategy_id: str, 
                         validation_level: ValidationLevel = ValidationLevel.STANDARD) -> Optional[ValidationResult]:
        """Validate a registered strategy"""
        
        try:
            metadata = self.get_strategy(strategy_id)
            if not metadata:
                logger.warning(f"Strategy not found: {strategy_id}")
                return None
            
            # Create strategy instance
            strategy = self.create_strategy_instance(strategy_id)
            if not strategy:
                logger.error(f"Could not create strategy instance: {strategy_id}")
                return None
            
            # Run validation
            validator = StrategyValidator(validation_level)
            validation_result = validator.validate_strategy(strategy)
            
            # Update metadata with validation result
            metadata.validation_result = validation_result
            metadata.modified_date = datetime.now()
            
            # Save registry
            self._save_registry()
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating strategy: {e}")
            return None
    
    def discover_and_register_strategies(self, search_paths: Optional[List[str]] = None,
                                      auto_validate: bool = False) -> List[str]:
        """Discover and register new strategies"""
        
        try:
            # Discover strategies
            discovered = self.discovery.discover_strategies(search_paths)
            
            registered_ids = []
            
            for metadata in discovered:
                strategy_id = metadata.strategy_id
                
                # Check if already registered
                if strategy_id in self.strategies:
                    # Check if file has been modified
                    existing = self.strategies[strategy_id]
                    if existing.checksum != metadata.checksum:
                        logger.info(f"Strategy file modified, updating: {strategy_id}")
                        self.strategies[strategy_id] = metadata
                        registered_ids.append(strategy_id)
                else:
                    # Register new strategy
                    self.strategies[strategy_id] = metadata
                    registered_ids.append(strategy_id)
                    
                    # Auto-validate if requested
                    if auto_validate:
                        try:
                            strategy_class = self.loader.load_strategy_class(metadata)
                            if strategy_class:
                                strategy = strategy_class()
                                validation_result = self.validator.validate_strategy(strategy)
                                metadata.validation_result = validation_result
                        except Exception as e:
                            logger.warning(f"Auto-validation failed for {strategy_id}: {e}")
            
            # Update index and save
            self._rebuild_index()
            self._save_registry()
            
            logger.info(f"Discovered and registered {len(registered_ids)} strategies")
            return registered_ids
            
        except Exception as e:
            logger.error(f"Error discovering strategies: {e}")
            return []
    
    def get_registry_stats(self) -> RegistryStats:
        """Get registry statistics"""
        
        try:
            stats = RegistryStats()
            
            # Basic counts
            stats.total_strategies = len(self.strategies)
            
            # Count by status
            for metadata in self.strategies.values():
                if metadata.status == RegistryStatus.ACTIVE:
                    stats.active_strategies += 1
                elif metadata.status == RegistryStatus.PRODUCTION:
                    stats.production_strategies += 1
                
                # Category counts
                if metadata.category not in stats.category_counts:
                    stats.category_counts[metadata.category] = 0
                stats.category_counts[metadata.category] += 1
                
                # Complexity counts
                if metadata.complexity not in stats.complexity_counts:
                    stats.complexity_counts[metadata.complexity] = 0
                stats.complexity_counts[metadata.complexity] += 1
                
                # Status counts
                if metadata.status not in stats.status_counts:
                    stats.status_counts[metadata.status] = 0
                stats.status_counts[metadata.status] += 1
            
            # Usage statistics
            stats.total_usage = sum(m.usage_count for m in self.strategies.values())
            
            if self.strategies:
                most_used = max(self.strategies.values(), key=lambda m: m.usage_count)
                stats.most_used_strategy = most_used.strategy_id
            
            # Recently added (last 7 days)
            recent_cutoff = datetime.now() - timedelta(days=7)
            stats.recently_added = [
                m.strategy_id for m in self.strategies.values()
                if m.created_date > recent_cutoff
            ]
            
            # Recently modified (last 7 days)
            stats.recently_modified = [
                m.strategy_id for m in self.strategies.values()
                if m.modified_date > recent_cutoff and m.strategy_id not in stats.recently_added
            ]
            
            # Performance statistics
            valid_strategies = [
                m for m in self.strategies.values()
                if m.performance_metrics and 'sharpe_ratio' in m.performance_metrics
            ]
            
            if valid_strategies:
                sharpe_ratios = [m.performance_metrics['sharpe_ratio'] for m in valid_strategies]
                stats.avg_sharpe_ratio = sum(sharpe_ratios) / len(sharpe_ratios)
                
                best_performing = max(valid_strategies, key=lambda m: m.performance_metrics['sharpe_ratio'])
                stats.best_performing_strategy = best_performing.strategy_id
            
            # Validation statistics
            validated_strategies = [
                m for m in self.strategies.values()
                if m.validation_result is not None
            ]
            
            if validated_strategies:
                passed_validations = [
                    m for m in validated_strategies
                    if m.validation_result.overall_score >= 70
                ]
                stats.validation_pass_rate = len(passed_validations) / len(validated_strategies)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting registry stats: {e}")
            return RegistryStats()
    
    def cleanup_registry(self, remove_orphaned: bool = False) -> Dict[str, int]:
        """Clean up registry"""
        
        try:
            cleanup_stats = {
                'removed_strategies': 0,
                'updated_strategies': 0,
                'orphaned_files': 0
            }
            
            strategies_to_remove = []
            
            for strategy_id, metadata in self.strategies.items():
                # Check if file still exists
                file_path = Path(metadata.file_path)
                
                if not file_path.exists():
                    if remove_orphaned:
                        strategies_to_remove.append(strategy_id)
                        cleanup_stats['orphaned_files'] += 1
                    continue
                
                # Check if file has been modified
                current_checksum = self.discovery._calculate_file_checksum(file_path)
                if current_checksum != metadata.checksum:
                    metadata.checksum = current_checksum
                    metadata.modified_date = datetime.fromtimestamp(file_path.stat().st_mtime)
                    cleanup_stats['updated_strategies'] += 1
            
            # Remove orphaned strategies
            for strategy_id in strategies_to_remove:
                del self.strategies[strategy_id]
                cleanup_stats['removed_strategies'] += 1
            
            # Rebuild index and save
            if cleanup_stats['removed_strategies'] > 0 or cleanup_stats['updated_strategies'] > 0:
                self._rebuild_index()
                self._save_registry()
            
            logger.info(f"Registry cleanup completed: {cleanup_stats}")
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"Error cleaning up registry: {e}")
            return {}
    
    def export_registry(self, export_path: str, format_type: str = "json") -> bool:
        """Export registry to file"""
        
        try:
            export_path_obj = Path(export_path)
            export_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            if format_type == "json":
                # Convert to JSON-serializable format
                export_data = {
                    'registry_info': {
                        'version': '1.0.0',
                        'exported_at': datetime.now().isoformat(),
                        'total_strategies': len(self.strategies)
                    },
                    'strategies': {}
                }
                
                for strategy_id, metadata in self.strategies.items():
                    export_data['strategies'][strategy_id] = asdict(metadata)
                
                with open(export_path_obj, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
            
            elif format_type == "pickle":
                with open(export_path_obj, 'wb') as f:
                    pickle.dump(self.strategies, f)
            
            logger.info(f"Registry exported to {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting registry: {e}")
            return False
    
    def import_registry(self, import_path: str, merge: bool = True) -> bool:
        """Import registry from file"""
        
        try:
            import_path_obj = Path(import_path)
            
            if not import_path_obj.exists():
                logger.error(f"Import file not found: {import_path}")
                return False
            
            if import_path_obj.suffix == '.json':
                with open(import_path_obj, 'r') as f:
                    import_data = json.load(f)
                
                if 'strategies' in import_data:
                    imported_strategies = {}
                    for strategy_id, metadata_dict in import_data['strategies'].items():
                        metadata = StrategyMetadata(**metadata_dict)
                        imported_strategies[strategy_id] = metadata
                else:
                    logger.error("Invalid registry format")
                    return False
            
            elif import_path_obj.suffix == '.pickle':
                with open(import_path_obj, 'rb') as f:
                    imported_strategies = pickle.load(f)
            
            else:
                logger.error(f"Unsupported import format: {import_path_obj.suffix}")
                return False
            
            # Merge or replace
            if merge:
                self.strategies.update(imported_strategies)
            else:
                self.strategies = imported_strategies
            
            # Rebuild index and save
            self._rebuild_index()
            self._save_registry()
            
            logger.info(f"Registry imported from {import_path}: {len(imported_strategies)} strategies")
            return True
            
        except Exception as e:
            logger.error(f"Error importing registry: {e}")
            return False
    
    def _create_metadata_from_class(self, strategy_class: Type[BaseStrategy]) -> StrategyMetadata:
        """Create metadata from strategy class"""
        
        metadata = StrategyMetadata()
        
        # Basic information
        metadata.class_name = strategy_class.__name__
        metadata.name = strategy_class.__name__
        metadata.description = strategy_class.__doc__ or ""
        metadata.documentation = metadata.description
        
        # Module information
        metadata.module_path = strategy_class.__module__
        
        # Generate strategy ID
        metadata.strategy_id = f"{metadata.module_path}.{metadata.class_name}".lower()
        
        # Guess category
        metadata.category = self.discovery._guess_category(metadata.class_name)
        
        # Set default status
        metadata.status = RegistryStatus.DEVELOPMENT
        
        return metadata
    
    def _matches_query(self, metadata: StrategyMetadata, query: RegistryQuery) -> bool:
        """Check if metadata matches query"""
        
        try:
            # Name pattern
            if query.name_pattern:
                if query.name_pattern.lower() not in metadata.name.lower():
                    return False
            
            # Category
            if query.category and metadata.category != query.category:
                return False
            
            # Complexity
            if query.complexity and metadata.complexity != query.complexity:
                return False
            
            # Status
            if query.status and metadata.status != query.status:
                return False
            
            # Author
            if query.author and query.author.lower() not in metadata.author.lower():
                return False
            
            # Date filters
            if query.created_after and metadata.created_date < query.created_after:
                return False
            
            if query.created_before and metadata.created_date > query.created_before:
                return False
            
            if query.modified_after and metadata.modified_date < query.modified_after:
                return False
            
            if query.modified_before and metadata.modified_date > query.modified_before:
                return False
            
            # Performance filters
            if metadata.performance_metrics:
                if query.min_sharpe_ratio:
                    sharpe = metadata.performance_metrics.get('sharpe_ratio', 0)
                    if sharpe < query.min_sharpe_ratio:
                        return False
                
                if query.max_drawdown:
                    drawdown = metadata.performance_metrics.get('max_drawdown', 0)
                    if drawdown > query.max_drawdown:
                        return False
                
                if query.min_return:
                    returns = metadata.performance_metrics.get('total_return', 0)
                    if returns < query.min_return:
                        return False
            
            # Tags
            if query.tags:
                if not any(tag in metadata.tags for tag in query.tags):
                    return False
            
            # Usage filters
            if query.min_usage_count and metadata.usage_count < query.min_usage_count:
                return False
            
            if query.used_after and (not metadata.last_used or metadata.last_used < query.used_after):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error matching query: {e}")
            return False
    
    def _sort_results(self, results: List[StrategyMetadata], 
                     sort_by: str, sort_order: str) -> List[StrategyMetadata]:
        """Sort search results"""
        
        try:
            reverse = (sort_order.lower() == "desc")
            
            if sort_by == "name":
                results.sort(key=lambda m: m.name, reverse=reverse)
            elif sort_by == "created_date":
                results.sort(key=lambda m: m.created_date, reverse=reverse)
            elif sort_by == "modified_date":
                results.sort(key=lambda m: m.modified_date, reverse=reverse)
            elif sort_by == "usage_count":
                results.sort(key=lambda m: m.usage_count, reverse=reverse)
            else:
                # Default to modified_date
                results.sort(key=lambda m: m.modified_date, reverse=reverse)
            
            return results
            
        except Exception as e:
            logger.error(f"Error sorting results: {e}")
            return results
    
    def _update_index(self, metadata: StrategyMetadata) -> None:
        """Update search index"""
        
        try:
            strategy_id = metadata.strategy_id
            
            # Create index entry
            index_entry = {
                'name': metadata.name.lower(),
                'description': metadata.description.lower(),
                'category': metadata.category.value,
                'complexity': metadata.complexity.value,
                'status': metadata.status.value,
                'author': metadata.author.lower(),
                'tags': [tag.lower() for tag in metadata.tags],
                'created_date': metadata.created_date.isoformat(),
                'modified_date': metadata.modified_date.isoformat()
            }
            
            self.index[strategy_id] = index_entry
            
        except Exception as e:
            logger.error(f"Error updating index: {e}")
    
    def _rebuild_index(self) -> None:
        """Rebuild search index"""
        
        try:
            self.index = {}
            for metadata in self.strategies.values():
                self._update_index(metadata)
                
        except Exception as e:
            logger.error(f"Error rebuilding index: {e}")
    
    def _load_registry(self) -> None:
        """Load registry from disk"""
        
        try:
            # Load metadata
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r') as f:
                    data = json.load(f)
                
                for strategy_id, metadata_dict in data.items():
                    metadata = StrategyMetadata(**metadata_dict)
                    self.strategies[strategy_id] = metadata
            
            # Load index
            if self.index_file.exists():
                with open(self.index_file, 'r') as f:
                    self.index = json.load(f)
            else:
                self._rebuild_index()
            
            logger.info(f"Loaded {len(self.strategies)} strategies from registry")
            
        except Exception as e:
            logger.error(f"Error loading registry: {e}")
            self.strategies = {}
            self.index = {}
    
    def _save_registry(self) -> None:
        """Save registry to disk"""
        
        try:
            # Save metadata
            metadata_data = {}
            for strategy_id, metadata in self.strategies.items():
                metadata_data[strategy_id] = asdict(metadata)
            
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata_data, f, indent=2, default=str)
            
            # Save index
            with open(self.index_file, 'w') as f:
                json.dump(self.index, f, indent=2)
            
        except Exception as e:
            logger.error(f"Error saving registry: {e}")