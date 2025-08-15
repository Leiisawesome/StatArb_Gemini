"""
Legacy Migration Bridge
======================

Bridge system for migrating existing hardcoded strategies to template-based
system while maintaining backward compatibility and gradual migration.

Author: Pro Quant Desk Trader
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Type
from datetime import datetime
import json
import copy

from strategy_layer.base import StrategyDefinition, StrategyConfig, StrategyType, StrategyStatus
from strategy_layer.builders.strategy_factory import StrategyFactory
from strategy_templates.base import (
    TemplateRegistry, BaseTemplate, TemplateMetadata,
    TemplateCategory, TemplateType as TemplateTypeEnum, TemplateStatus
)

logger = logging.getLogger(__name__)

@dataclass
class MigrationResult:
    """Result of strategy migration process"""
    success: bool
    original_strategy_id: str
    template_id: Optional[str] = None
    migration_time: datetime = field(default_factory=datetime.now)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MigrationStats:
    """Statistics for migration process"""
    total_strategies_analyzed: int = 0
    successfully_migrated: int = 0
    migration_failed: int = 0
    templates_created: int = 0
    migration_time_ms: float = 0.0
    strategies_by_type: Dict[str, int] = field(default_factory=dict)

class LegacyMigrationBridge:
    """
    Bridge system for migrating legacy hardcoded strategies to the template-based
    system with backward compatibility and gradual migration support.
    """
    
    def __init__(self, template_registry: TemplateRegistry,
                 legacy_strategy_factory: StrategyFactory):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.template_registry = template_registry
        self.legacy_factory = legacy_strategy_factory
        
        # Migration configuration
        self.migration_mapping = {
            StrategyType.MOMENTUM: self._migrate_momentum_strategy,
            StrategyType.MEAN_REVERSION: self._migrate_mean_reversion_strategy,
            StrategyType.PAIR_TRADING: self._migrate_pair_trading_strategy,
            StrategyType.CUSTOM: self._migrate_custom_strategy
        }
        
        # Track migrated strategies
        self.migrated_strategies: Dict[str, str] = {}  # legacy_id -> template_id
        self.migration_history: List[MigrationResult] = []
        
        self.logger.info("LegacyMigrationBridge initialized")
    
    def migrate_strategy_to_template(self, strategy_object: StrategyDefinition) -> MigrationResult:
        """
        Migrate a legacy strategy object to a template
        """
        try:
            migration_start = datetime.now()
            
            strategy_config = strategy_object.get_config()
            strategy_id = strategy_config.strategy_id
            
            self.logger.info(f"Starting migration for strategy {strategy_id}")
            
            # Check if already migrated
            if strategy_id in self.migrated_strategies:
                template_id = self.migrated_strategies[strategy_id]
                self.logger.info(f"Strategy {strategy_id} already migrated to template {template_id}")
                return MigrationResult(
                    success=True,
                    original_strategy_id=strategy_id,
                    template_id=template_id,
                    warnings=["Strategy already migrated"]
                )
            
            # Get migration handler for strategy type
            migration_handler = self.migration_mapping.get(strategy_config.strategy_type)
            if not migration_handler:
                return MigrationResult(
                    success=False,
                    original_strategy_id=strategy_id,
                    errors=[f"No migration handler for strategy type {strategy_config.strategy_type}"]
                )
            
            # Perform migration
            template = migration_handler(strategy_object)
            
            if not template:
                return MigrationResult(
                    success=False,
                    original_strategy_id=strategy_id,
                    errors=["Migration handler returned no template"]
                )
            
            # Register template
            success = self.template_registry.register_template(template)
            if not success:
                return MigrationResult(
                    success=False,
                    original_strategy_id=strategy_id,
                    errors=["Failed to register migrated template"]
                )
            
            # Track migration
            template_id = template.metadata.template_id
            self.migrated_strategies[strategy_id] = template_id
            
            migration_time = datetime.now()
            migration_duration = (migration_time - migration_start).total_seconds() * 1000
            
            result = MigrationResult(
                success=True,
                original_strategy_id=strategy_id,
                template_id=template_id,
                migration_time=migration_time,
                metadata={
                    'migration_duration_ms': migration_duration,
                    'strategy_type': strategy_config.strategy_type.value,
                    'template_category': template.metadata.category.value,
                    'original_config_size': len(str(strategy_config.to_dict()))
                }
            )
            
            self.migration_history.append(result)
            
            self.logger.info(f"Successfully migrated strategy {strategy_id} to template {template_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Migration failed for strategy {strategy_config.strategy_id}: {e}")
            return MigrationResult(
                success=False,
                original_strategy_id=strategy_config.strategy_id,
                errors=[f"Migration error: {e}"]
            )
    
    def migrate_strategy_config_to_template(self, strategy_config: StrategyConfig) -> MigrationResult:
        """
        Migrate a strategy configuration directly to a template
        """
        try:
            # Create strategy object from config
            strategy_class = self.legacy_factory.get_strategy_class(strategy_config.strategy_type.value)
            if not strategy_class:
                return MigrationResult(
                    success=False,
                    original_strategy_id=strategy_config.strategy_id,
                    errors=[f"No strategy class found for type {strategy_config.strategy_type}"]
                )
            
            strategy_object = strategy_class(strategy_config)
            
            # Migrate the strategy object
            return self.migrate_strategy_to_template(strategy_object)
            
        except Exception as e:
            self.logger.error(f"Config migration failed: {e}")
            return MigrationResult(
                success=False,
                original_strategy_id=strategy_config.strategy_id,
                errors=[f"Config migration error: {e}"]
            )
    
    def migrate_all_legacy_strategies(self) -> Dict[str, MigrationResult]:
        """
        Migrate all available legacy strategies to templates
        """
        results = {}
        
        # Get available strategy types from legacy factory
        strategy_types = self.legacy_factory.get_available_strategy_types()
        
        for strategy_type in strategy_types:
            try:
                # Create a sample strategy for migration
                sample_config = self._create_sample_config(strategy_type)
                result = self.migrate_strategy_config_to_template(sample_config)
                results[strategy_type] = result
                
            except Exception as e:
                self.logger.error(f"Failed to migrate strategy type {strategy_type}: {e}")
                results[strategy_type] = MigrationResult(
                    success=False,
                    original_strategy_id=strategy_type,
                    errors=[f"Migration error: {e}"]
                )
        
        return results
    
    def create_compatibility_adapter(self, template_id: str) -> Optional[StrategyDefinition]:
        """
        Create a legacy-compatible strategy object from a template
        """
        try:
            template = self.template_registry.get_template(template_id)
            if not template:
                self.logger.error(f"Template {template_id} not found")
                return None
            
            # Convert template back to legacy format
            strategy_config = self._convert_template_to_legacy_config(template)
            
            # Create strategy object
            strategy_type = strategy_config.strategy_type.value
            strategy_class = self.legacy_factory.get_strategy_class(strategy_type)
            
            if not strategy_class:
                self.logger.error(f"No legacy strategy class for type {strategy_type}")
                return None
            
            strategy_object = strategy_class(strategy_config)
            
            # Enhance with template metadata
            strategy_object._template_origin = template_id
            strategy_object._is_template_derived = True
            
            return strategy_object
            
        except Exception as e:
            self.logger.error(f"Failed to create compatibility adapter for template {template_id}: {e}")
            return None
    
    def get_migration_stats(self) -> MigrationStats:
        """Get migration statistics"""
        
        successful_migrations = [result for result in self.migration_history if result.success]
        failed_migrations = [result for result in self.migration_history if not result.success]
        
        total_time = sum(
            result.metadata.get('migration_duration_ms', 0)
            for result in self.migration_history
        )
        
        # Count strategies by type
        strategies_by_type = {}
        for result in successful_migrations:
            strategy_type = result.metadata.get('strategy_type', 'unknown')
            strategies_by_type[strategy_type] = strategies_by_type.get(strategy_type, 0) + 1
        
        return MigrationStats(
            total_strategies_analyzed=len(self.migration_history),
            successfully_migrated=len(successful_migrations),
            migration_failed=len(failed_migrations),
            templates_created=len(successful_migrations),
            migration_time_ms=total_time,
            strategies_by_type=strategies_by_type
        )
    
    def _migrate_momentum_strategy(self, strategy_object: StrategyDefinition) -> BaseTemplate:
        """Migrate momentum strategy to template"""
        
        config = strategy_object.get_config()
        
        # Create template metadata
        template_metadata = TemplateMetadata(
            template_id=f"migrated_momentum_{config.strategy_id}",
            name=f"Migrated Momentum Strategy - {config.name}",
            version=config.version,
            category=TemplateCategory.BASE,
            template_type=TemplateTypeEnum.COMPLETE_STRATEGY,
            status=TemplateStatus.VALIDATED,
            description=f"Migrated from legacy momentum strategy: {config.description or config.name}",
            author="Legacy Migration Bridge",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=["migrated", "momentum", "legacy"],
            dependencies=["market_data", "technical_indicators"]
        )
        
        # Extract components from legacy config
        components = {
            "signal_generation": config.signal_generation,
            "risk_management": config.risk_management,
            "entry_exit_logic": config.entry_exit_logic,
            "execution": config.execution,
            "portfolio_management": config.portfolio_management
        }
        
        # Create template
        template = BaseTemplate(
            metadata=template_metadata,
            configuration={
                "legacy_migration": True,
                "original_strategy_type": config.strategy_type.value,
                "migration_timestamp": datetime.now().isoformat()
            },
            parameters=config.parameters,
            components=components
        )
        
        return template
    
    def _migrate_mean_reversion_strategy(self, strategy_object: StrategyDefinition) -> BaseTemplate:
        """Migrate mean reversion strategy to template"""
        
        config = strategy_object.get_config()
        
        template_metadata = TemplateMetadata(
            template_id=f"migrated_mean_reversion_{config.strategy_id}",
            name=f"Migrated Mean Reversion Strategy - {config.name}",
            version=config.version,
            category=TemplateCategory.BASE,
            template_type=TemplateTypeEnum.COMPLETE_STRATEGY,
            status=TemplateStatus.VALIDATED,
            description=f"Migrated from legacy mean reversion strategy: {config.description or config.name}",
            author="Legacy Migration Bridge",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=["migrated", "mean_reversion", "legacy"],
            dependencies=["market_data", "statistical_models"]
        )
        
        components = {
            "signal_generation": config.signal_generation,
            "risk_management": config.risk_management,
            "entry_exit_logic": config.entry_exit_logic,
            "execution": config.execution,
            "portfolio_management": config.portfolio_management
        }
        
        template = BaseTemplate(
            metadata=template_metadata,
            configuration={
                "legacy_migration": True,
                "original_strategy_type": config.strategy_type.value,
                "migration_timestamp": datetime.now().isoformat()
            },
            parameters=config.parameters,
            components=components
        )
        
        return template
    
    def _migrate_pair_trading_strategy(self, strategy_object: StrategyDefinition) -> BaseTemplate:
        """Migrate pair trading strategy to template"""
        
        config = strategy_object.get_config()
        
        template_metadata = TemplateMetadata(
            template_id=f"migrated_pair_trading_{config.strategy_id}",
            name=f"Migrated Pair Trading Strategy - {config.name}",
            version=config.version,
            category=TemplateCategory.BASE,
            template_type=TemplateTypeEnum.COMPLETE_STRATEGY,
            status=TemplateStatus.VALIDATED,
            description=f"Migrated from legacy pair trading strategy: {config.description or config.name}",
            author="Legacy Migration Bridge",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=["migrated", "pair_trading", "legacy"],
            dependencies=["market_data", "cointegration_models"]
        )
        
        components = {
            "signal_generation": config.signal_generation,
            "risk_management": config.risk_management,
            "entry_exit_logic": config.entry_exit_logic,
            "execution": config.execution,
            "portfolio_management": config.portfolio_management
        }
        
        template = BaseTemplate(
            metadata=template_metadata,
            configuration={
                "legacy_migration": True,
                "original_strategy_type": config.strategy_type.value,
                "migration_timestamp": datetime.now().isoformat()
            },
            parameters=config.parameters,
            components=components
        )
        
        return template
    
    def _migrate_custom_strategy(self, strategy_object: StrategyDefinition) -> BaseTemplate:
        """Migrate custom strategy to template"""
        
        config = strategy_object.get_config()
        
        template_metadata = TemplateMetadata(
            template_id=f"migrated_custom_{config.strategy_id}",
            name=f"Migrated Custom Strategy - {config.name}",
            version=config.version,
            category=TemplateCategory.COMPOSITE,
            template_type=TemplateTypeEnum.COMPLETE_STRATEGY,
            status=TemplateStatus.VALIDATED,
            description=f"Migrated from legacy custom strategy: {config.description or config.name}",
            author="Legacy Migration Bridge",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=["migrated", "custom", "legacy"],
            dependencies=["market_data"]
        )
        
        components = {
            "signal_generation": config.signal_generation,
            "risk_management": config.risk_management,
            "entry_exit_logic": config.entry_exit_logic,
            "execution": config.execution,
            "portfolio_management": config.portfolio_management
        }
        
        template = BaseTemplate(
            metadata=template_metadata,
            configuration={
                "legacy_migration": True,
                "original_strategy_type": config.strategy_type.value,
                "migration_timestamp": datetime.now().isoformat()
            },
            parameters=config.parameters,
            components=components
        )
        
        return template
    
    def _create_sample_config(self, strategy_type: str) -> StrategyConfig:
        """Create a sample configuration for migration testing"""
        
        strategy_type_enum = StrategyType(strategy_type)
        
        return StrategyConfig(
            strategy_id=f"sample_{strategy_type}",
            strategy_type=strategy_type_enum,
            name=f"Sample {strategy_type.title()} Strategy",
            version="1.0.0",
            description=f"Sample {strategy_type} strategy for migration",
            status=StrategyStatus.DRAFT,
            signal_generation={
                "type": f"{strategy_type}_signals",
                "parameters": {"lookback": 20, "threshold": 0.02}
            },
            risk_management={
                "position_sizing": {"method": "fixed", "size": 0.02},
                "stop_loss": {"enabled": True, "percentage": 0.05}
            },
            entry_exit_logic={
                "entry_threshold": 0.02,
                "exit_threshold": 0.01
            },
            execution={
                "order_type": "market",
                "execution_delay": 0
            },
            portfolio_management={
                "max_positions": 50,
                "diversification": True
            },
            parameters={
                "lookback_period": 20,
                "signal_threshold": 0.02,
                "position_size": 0.02
            }
        )
    
    def _convert_template_to_legacy_config(self, template: BaseTemplate) -> StrategyConfig:
        """Convert template back to legacy StrategyConfig format"""
        
        # Map template type to strategy type
        strategy_type_mapping = {
            'momentum': StrategyType.MOMENTUM,
            'mean_reversion': StrategyType.MEAN_REVERSION,
            'pair_trading': StrategyType.PAIR_TRADING
        }
        
        # Determine strategy type from template tags
        strategy_type = StrategyType.CUSTOM
        for tag in template.metadata.tags:
            if tag in strategy_type_mapping:
                strategy_type = strategy_type_mapping[tag]
                break
        
        # Create StrategyConfig
        config = StrategyConfig(
            strategy_id=template.metadata.template_id,
            strategy_type=strategy_type,
            name=template.metadata.name,
            version=template.metadata.version,
            description=template.metadata.description,
            status=StrategyStatus.ACTIVE,  # Default to active for compatibility
            created_date=template.metadata.created_at,
            updated_date=template.metadata.updated_at,
            metadata={
                'template_origin': True,
                'original_template_id': template.metadata.template_id
            },
            signal_generation=template.components.get('signal_generation', {}),
            risk_management=template.components.get('risk_management', {}),
            entry_exit_logic=template.components.get('entry_exit_logic', {}),
            execution=template.components.get('execution', {}),
            portfolio_management=template.components.get('portfolio_management', {}),
            parameters=template.parameters
        )
        
        return config
