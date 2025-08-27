"""
Core Engine Migration Utility
============================

Utility to migrate from deprecated LegacyUnifiedCoreEngine to UnifiedCoreEngine.
Handles strategy configuration conversion and provides migration assistance.

Author: Professional Trading System Architecture
Version: 1.0.0
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import warnings

from .unified_core_engine_legacy import UnifiedCoreEngine as LegacyUnifiedCoreEngine, CoreEngineConfig as LegacyCoreEngineConfig, StrategyConfig as LegacyStrategyConfig
from .unified_core_engine import UnifiedCoreEngine, CoreEngineConfig, StrategyConfig
from .strategy_interfaces import StrategyType

logger = logging.getLogger(__name__)


@dataclass
class MigrationReport:
    """Migration report with success/failure details"""
    success: bool
    migrated_strategies: List[str]
    failed_strategies: List[Tuple[str, str]]  # (strategy_id, error_message)
    configuration_changes: Dict[str, Any]
    warnings: List[str]
    recommendations: List[str]


class CoreEngineMigrator:
    """
    Utility to migrate from deprecated LegacyUnifiedCoreEngine to UnifiedCoreEngine.
    
    Provides:
    - Configuration conversion
    - Strategy migration assistance  
    - Validation and compatibility checks
    - Migration report generation
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def migrate_configuration(self, legacy_config: LegacyCoreEngineConfig) -> CoreEngineConfig:
        """Migrate legacy configuration to clean configuration"""
        try:
            # Map configuration fields
            clean_config = CoreEngineConfig(
                engine_id=legacy_config.engine_id,
                trading_mode=legacy_config.trading_mode,
                max_concurrent_strategies=legacy_config.max_concurrent_strategies,
                max_processing_time_ms=legacy_config.max_processing_time_ms,
                enable_monitoring=legacy_config.enable_monitoring,
                enable_caching=legacy_config.enable_caching,
                cache_ttl_seconds=legacy_config.cache_ttl_seconds,
                enable_dashboard=legacy_config.enable_dashboard,
                dashboard_update_interval=legacy_config.dashboard_update_interval,
                dashboard_port=legacy_config.dashboard_port,
                max_portfolio_risk=legacy_config.max_portfolio_risk,
                max_position_size=legacy_config.max_position_size,
                max_drawdown=legacy_config.max_drawdown,
                initial_capital=legacy_config.initial_capital,
                max_order_value=legacy_config.max_order_value,
                commission_rate=legacy_config.commission_rate,
                default_execution_algorithm=legacy_config.default_execution_algorithm,
                enable_ibkr_integration=legacy_config.enable_ibkr_integration,
                ibkr_account_id=legacy_config.ibkr_account_id,
                ibkr_paper_trading=legacy_config.ibkr_paper_trading,
                ibkr_config=legacy_config.ibkr_config,
                signal_config=legacy_config.signal_config,
                risk_limits=legacy_config.risk_limits
            )
            
            self.logger.info("✅ Configuration migration successful")
            return clean_config
            
        except Exception as e:
            self.logger.error(f"❌ Configuration migration failed: {e}")
            raise ValueError(f"Failed to migrate configuration: {e}")
    
    def migrate_strategy_config(self, legacy_strategy: LegacyStrategyConfig) -> StrategyConfig:
        """Migrate legacy strategy configuration to clean strategy configuration"""
        try:
            # Determine strategy type from legacy strategy_type string
            strategy_type = self._convert_strategy_type(legacy_strategy.strategy_type)
            
            # Create clean strategy config
            clean_strategy = StrategyConfig(
                strategy_id=legacy_strategy.strategy_id,
                strategy_name=legacy_strategy.strategy_name,
                strategy_type=strategy_type,
                signal_params=legacy_strategy.signal_params.copy(),
                risk_params=legacy_strategy.risk_params.copy(),
                execution_params=legacy_strategy.execution_params.copy(),
                portfolio_params=legacy_strategy.portfolio_params.copy(),
                metadata=legacy_strategy.metadata.copy(),
                created_at=legacy_strategy.created_at,
                updated_at=legacy_strategy.updated_at
            )
            
            self.logger.debug(f"✅ Strategy config migrated: {legacy_strategy.strategy_id}")
            return clean_strategy
            
        except Exception as e:
            self.logger.error(f"❌ Strategy config migration failed: {legacy_strategy.strategy_id} - {e}")
            raise ValueError(f"Failed to migrate strategy config: {e}")
    
    def _convert_strategy_type(self, legacy_type: str) -> StrategyType:
        """Convert legacy strategy type string to StrategyType enum"""
        legacy_type_lower = legacy_type.lower()
        
        if 'momentum' in legacy_type_lower:
            return StrategyType.MOMENTUM
        elif 'mean' in legacy_type_lower or 'reversion' in legacy_type_lower:
            return StrategyType.MEAN_REVERSION
        elif 'pairs' in legacy_type_lower:
            return StrategyType.PAIRS_TRADING
        elif 'arbitrage' in legacy_type_lower:
            return StrategyType.ARBITRAGE
        else:
            self.logger.warning(f"⚠️ Unknown strategy type: {legacy_type}, defaulting to CUSTOM")
            return StrategyType.CUSTOM
    
    def perform_full_migration(self, legacy_engine: 'LegacyUnifiedCoreEngine') -> Tuple['UnifiedCoreEngine', MigrationReport]:
        """Perform complete migration from legacy to clean engine"""
        warnings.warn(
            "Migrating from deprecated LegacyUnifiedCoreEngine to UnifiedCoreEngine",
            DeprecationWarning
        )
        
        report = MigrationReport(
            success=False,
            migrated_strategies=[],
            failed_strategies=[],
            configuration_changes={},
            warnings=[],
            recommendations=[]
        )
        
        try:
            # Step 1: Migrate configuration
            self.logger.info("🔄 Step 1: Migrating engine configuration")
            clean_config = self.migrate_configuration(legacy_engine.config)
            report.configuration_changes = self._compare_configurations(legacy_engine.config, clean_config)
            
            # Step 2: Create clean engine
            self.logger.info("🔄 Step 2: Creating clean engine instance")
            clean_engine = UnifiedCoreEngine(clean_config)
            
            # Step 3: Migrate strategies
            self.logger.info("🔄 Step 3: Migrating strategy configurations")
            legacy_strategies = getattr(legacy_engine, '_strategy_configs', {})
            
            for strategy_id, legacy_strategy_config in legacy_strategies.items():
                try:
                    clean_strategy_config = self.migrate_strategy_config(legacy_strategy_config)
                    clean_engine.register_strategy(clean_strategy_config)
                    report.migrated_strategies.append(strategy_id)
                    self.logger.info(f"✅ Migrated strategy: {strategy_id}")
                    
                except Exception as e:
                    error_msg = str(e)
                    report.failed_strategies.append((strategy_id, error_msg))
                    self.logger.error(f"❌ Failed to migrate strategy: {strategy_id} - {error_msg}")
            
            # Step 4: Generate recommendations
            self._generate_migration_recommendations(report, legacy_engine, clean_engine)
            
            # Step 5: Final validation
            if self._validate_migration(legacy_engine, clean_engine, report):
                report.success = True
                self.logger.info("✅ Migration completed successfully")
            else:
                report.success = False
                self.logger.warning("⚠️ Migration completed with warnings")
            
            return clean_engine, report
            
        except Exception as e:
            self.logger.error(f"❌ Migration failed: {e}")
            report.success = False
            raise RuntimeError(f"Migration failed: {e}")
    
    def _compare_configurations(self, legacy_config: 'LegacyCoreEngineConfig', 
                              clean_config: CoreEngineConfig) -> Dict[str, Any]:
        """Compare legacy and clean configurations"""
        changes = {}
        
        # Check for removed features
        if hasattr(legacy_config, 'TRADE_ENGINE_AVAILABLE'):
            changes['removed_fallback_mechanisms'] = "Import-dependent fallbacks removed"
        
        changes['architecture_pattern'] = "Changed from monolithic to pure delegation"
        changes['strategy_handling'] = "Strategy logic extracted from core"
        
        return changes
    
    def _generate_migration_recommendations(self, report: MigrationReport, 
                                          legacy_engine: 'LegacyUnifiedCoreEngine',
                                          clean_engine: 'UnifiedCoreEngine'):
        """Generate migration recommendations"""
        recommendations = []
        warnings_list = []
        
        # Check for embedded strategy logic
        if hasattr(legacy_engine, '_process_momentum_signals'):
            recommendations.append(
                "Strategy-specific logic has been extracted to separate strategy classes. "
                "Review custom strategy implementations for consistency."
            )
        
        # Check for fallback mechanisms
        warnings_list.append(
            "Import-dependent fallback behavior has been removed. "
            "Ensure all required dependencies are properly installed."
        )
        
        # Performance recommendations
        recommendations.extend([
            "Test performance with clean engine to ensure consistency",
            "Update any custom code that directly accessed strategy methods",
            "Review monitoring dashboards for compatibility with new metrics format",
            "Consider updating deployment scripts to use UnifiedCoreEngine"
        ])
        
        report.recommendations = recommendations
        report.warnings = warnings_list
    
    def _validate_migration(self, legacy_engine: 'LegacyUnifiedCoreEngine',
                          clean_engine: 'UnifiedCoreEngine',
                          report: MigrationReport) -> bool:
        """Validate migration success"""
        try:
            # Check strategy count
            legacy_strategies = len(getattr(legacy_engine, '_strategy_configs', {}))
            migrated_strategies = len(report.migrated_strategies)
            
            if migrated_strategies < legacy_strategies:
                self.logger.warning(
                    f"⚠️ Not all strategies migrated: {migrated_strategies}/{legacy_strategies}"
                )
                return False
            
            # Check engine status
            if clean_engine.get_engine_status().value != "ready":
                self.logger.warning("⚠️ Clean engine not in ready state")
                return False
            
            # Validation passed
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Migration validation failed: {e}")
            return False
    
    def generate_migration_script(self, legacy_config_path: str, 
                                clean_config_path: str) -> str:
        """Generate migration script for automated migration"""
        script = f'''#!/usr/bin/env python3
"""
Auto-generated migration script
===============================

Migrates from LegacyUnifiedCoreEngine to UnifiedCoreEngine.
Generated by CoreEngineMigrator.

Usage:
    python migration_script.py
"""

import sys
import logging
from core_structure.engine_migration import CoreEngineMigrator
from core_structure.unified_core_engine import UnifiedCoreEngine, CoreEngineConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    try:
        # Load legacy configuration
        # TODO: Implement configuration loading from {legacy_config_path}
        legacy_config = CoreEngineConfig()  # Replace with actual config loading
        
        # Create legacy engine
        legacy_engine = UnifiedCoreEngine(legacy_config)
        
        # Perform migration
        migrator = CoreEngineMigrator()
        clean_engine, report = migrator.perform_full_migration(legacy_engine)
        
        # Report results
        if report.success:
            logger.info("✅ Migration successful!")
            logger.info(f"Migrated strategies: {{', '.join(report.migrated_strategies)}}")
        else:
            logger.error("❌ Migration failed!")
            for strategy_id, error in report.failed_strategies:
                logger.error(f"  - {{strategy_id}}: {{error}}")
        
        # Print recommendations
        if report.recommendations:
            logger.info("📋 Recommendations:")
            for rec in report.recommendations:
                logger.info(f"  - {{rec}}")
        
        # Save clean configuration
        # TODO: Implement configuration saving to {clean_config_path}
        
        return 0 if report.success else 1
        
    except Exception as e:
        logger.error(f"❌ Migration script failed: {{e}}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
'''
        return script


def quick_migrate(legacy_engine: 'LegacyUnifiedCoreEngine') -> 'UnifiedCoreEngine':
    """Quick migration utility for simple cases"""
    migrator = CoreEngineMigrator()
    clean_engine, report = migrator.perform_full_migration(legacy_engine)
    
    if not report.success:
        raise RuntimeError(f"Quick migration failed: {report.failed_strategies}")
    
    return clean_engine
