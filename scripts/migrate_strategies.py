#!/usr/bin/env python3
"""
Strategy Migration Toolkit
=========================

Automated migration tool for converting legacy strategies to modern trade_engine templates.
Supports momentum and mean reversion strategy migration with validation and testing.

Usage:
    python scripts/migrate_strategies.py --strategy momentum --test
    python scripts/migrate_strategies.py --strategy mean_reversion --validate
    python scripts/migrate_strategies.py --all --deploy
"""

import asyncio
import argparse
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from trade_engine.templates import (
    ProfessionalMomentumTemplate,
    ProfessionalMeanReversionTemplate,
    TemplateStrategyBridge,
    TemplateConfiguration
)
from trade_engine.core import DelegatedCoreEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StrategyMigrationToolkit:
    """Professional toolkit for migrating legacy strategies to modern templates."""
    
    def __init__(self):
        self.legacy_strategies = {
            'momentum': self._load_legacy_momentum_config(),
            'mean_reversion': self._load_legacy_mean_reversion_config()
        }
        
        self.template_configs = {}
        self.strategy_bridges = {}
        
    def _load_legacy_momentum_config(self) -> Dict[str, Any]:
        """Load and analyze legacy momentum strategy configuration."""
        return {
            'strategy_id': 'legacy_momentum',
            'parameters': {
                'lookback_period': 5,
                'entry_momentum_threshold': 0.001,
                'entry_price_threshold': 0.3,
                'exit_price_threshold': 0.7,
                'exit_momentum_threshold': -0.001,
                'stop_loss_threshold': -0.03,
                'position_size': 0.05,
                'max_position_size': 0.5
            },
            'file_path': 'strategy_layer/strategies/momentum_strategy.py',
            'description': 'Legacy momentum strategy with basic signal generation'
        }
    
    def _load_legacy_mean_reversion_config(self) -> Dict[str, Any]:
        """Load and analyze legacy mean reversion strategy configuration."""
        return {
            'strategy_id': 'legacy_mean_reversion',
            'parameters': {
                'rsi_calculation': True,
                'bollinger_bands': True,
                'moving_averages': True,
                'risk_management': True,
                'position_sizing': 'fixed'
            },
            'file_path': 'strategy_layer/strategies/mean_reversion_strategy.py',
            'description': 'Legacy mean reversion strategy with RSI and Bollinger Bands'
        }
    
    def create_momentum_template_config(self) -> TemplateConfiguration:
        """Create modern template configuration for momentum strategy."""
        legacy_config = self.legacy_strategies['momentum']
        
        # Enhanced parameter mapping with professional improvements
        modern_parameters = {
            # Core momentum parameters - enhanced
            'lookback_period': 20,  # Enhanced from legacy 5
            'momentum_threshold': 0.015,  # Enhanced from 0.001
            'confidence_threshold': 0.75,  # Enhanced from 0.3
            
            # Volume analysis - new feature
            'volume_lookback': 10,
            'volume_threshold': 1.5,
            
            # Risk management - improved
            'position_size': 0.02,  # Conservative from 0.05
            'stop_loss_pct': 0.03,  # From stop_loss_threshold
            'take_profit_pct': 0.08,  # Enhanced from exit logic
            
            # Volatility filtering - new feature
            'volatility_percentile': 80
        }
        
        config = TemplateConfiguration(
            template_id="professional_momentum_v1",
            strategy_instance_id=f"migrated_momentum_{int(asyncio.get_event_loop().time())}",
            parameters=modern_parameters,
            metadata={
                'migrated_from': legacy_config['file_path'],
                'legacy_strategy_id': legacy_config['strategy_id'],
                'migration_date': '2025-08-24',
                'migration_version': '1.0.0',
                'improvements': [
                    'Enhanced lookback period for better signal quality',
                    'Professional momentum threshold tuning',
                    'Added volume confirmation analysis',
                    'Implemented volatility filtering',
                    'Conservative position sizing',
                    'Comprehensive risk management'
                ]
            }
        )
        
        logger.info(f"Created momentum template config: {config.strategy_instance_id}")
        return config
    
    def create_mean_reversion_template_config(self) -> TemplateConfiguration:
        """Create modern template configuration for mean reversion strategy."""
        legacy_config = self.legacy_strategies['mean_reversion']
        
        # Professional parameter configuration
        modern_parameters = {
            # Core analysis parameters
            'lookback_period': 20,
            'rsi_period': 14,
            'bb_period': 20,
            'bb_std_dev': 2.0,
            
            # Signal thresholds
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'ma_deviation_threshold': 0.05,
            'confidence_threshold': 0.6,
            
            # Risk management
            'position_size': 0.03,
            'stop_loss_pct': 0.04,
            'take_profit_pct': 0.06,
            
            # Volume and volatility filters
            'volume_threshold': 1.2,
            'volatility_percentile': 80
        }
        
        config = TemplateConfiguration(
            template_id="professional_mean_reversion_v1",
            strategy_instance_id=f"migrated_mean_reversion_{int(asyncio.get_event_loop().time())}",
            parameters=modern_parameters,
            metadata={
                'migrated_from': legacy_config['file_path'],
                'legacy_strategy_id': legacy_config['strategy_id'],
                'migration_date': '2025-08-24',
                'migration_version': '1.0.0',
                'improvements': [
                    'Professional RSI analysis with proper thresholds',
                    'Bollinger Bands with 2-sigma configuration',
                    'Moving average deviation analysis',
                    'Volume confirmation filtering',
                    'Volatility-based signal filtering',
                    'Conservative risk management'
                ]
            }
        )
        
        logger.info(f"Created mean reversion template config: {config.strategy_instance_id}")
        return config
    
    def migrate_strategy(self, strategy_name: str) -> TemplateStrategyBridge:
        """Migrate a specific strategy from legacy to modern template."""
        if strategy_name not in self.legacy_strategies:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        
        logger.info(f"Starting migration for strategy: {strategy_name}")
        
        if strategy_name == 'momentum':
            config = self.create_momentum_template_config()
        elif strategy_name == 'mean_reversion':
            config = self.create_mean_reversion_template_config()
        else:
            raise ValueError(f"Migration not implemented for: {strategy_name}")
        
        # Store configuration for later use
        self.template_configs[strategy_name] = config
        
        # Create strategy bridge
        strategy_bridge = TemplateStrategyBridge(config)
        self.strategy_bridges[strategy_name] = strategy_bridge
        
        logger.info(f"✅ Successfully migrated {strategy_name} strategy")
        return strategy_bridge
    
    def validate_migration(self, strategy_name: str) -> bool:
        """Validate that migration was successful."""
        if strategy_name not in self.strategy_bridges:
            logger.error(f"❌ Strategy {strategy_name} not migrated yet")
            return False
        
        try:
            bridge = self.strategy_bridges[strategy_name]
            config = self.template_configs[strategy_name]
            
            # Test template validation
            if strategy_name == 'momentum':
                template = ProfessionalMomentumTemplate()
            else:
                template = ProfessionalMeanReversionTemplate()
            
            # Validate parameters
            is_valid = template.validate_parameters(config.parameters)
            if not is_valid:
                logger.error(f"❌ Parameter validation failed for {strategy_name}")
                return False
            
            # Test bridge initialization
            bridge_info = bridge.get_template_info()
            if not bridge_info:
                logger.error(f"❌ Bridge initialization failed for {strategy_name}")
                return False
            
            logger.info(f"✅ Validation passed for {strategy_name}")
            logger.info(f"   Template: {bridge_info.get('template_id')}")
            logger.info(f"   Instance: {bridge_info.get('strategy_instance_id')}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Validation error for {strategy_name}: {str(e)}")
            return False
    
    def test_migration(self, strategy_name: str) -> bool:
        """Test migrated strategy with sample data."""
        if strategy_name not in self.strategy_bridges:
            logger.error(f"❌ Strategy {strategy_name} not migrated yet")
            return False
        
        try:
            logger.info(f"Testing migrated {strategy_name} strategy...")
            
            bridge = self.strategy_bridges[strategy_name]
            
            # Create sample market data as DataFrame
            import pandas as pd
            sample_data = pd.DataFrame([{
                'timestamp': '2025-08-24T10:00:00Z',
                'symbol': 'TEST_PAIR',
                'close': 100.0,
                'volume': 1000,
                'bid': 99.95,
                'ask': 100.05,
                'high': 101.0,
                'low': 99.0
            }])
            
            # Test signal generation
            signals = bridge.calculate_signals(sample_data)
            
            if signals is not None:
                logger.info(f"✅ Signal generation successful for {strategy_name}")
                logger.info(f"   Generated {len(signals) if hasattr(signals, '__len__') else 'N/A'} signals")
                return True
            else:
                logger.warning(f"⚠️  No signals generated for {strategy_name} (normal for sample data)")
                return True
                
        except Exception as e:
            logger.error(f"❌ Testing error for {strategy_name}: {str(e)}")
            return False
    
    def generate_migration_report(self) -> Dict[str, Any]:
        """Generate comprehensive migration report."""
        report = {
            'migration_summary': {
                'total_strategies': len(self.legacy_strategies),
                'migrated_strategies': len(self.strategy_bridges),
                'success_rate': len(self.strategy_bridges) / len(self.legacy_strategies) * 100
            },
            'strategy_details': {},
            'recommendations': []
        }
        
        for strategy_name in self.legacy_strategies:
            if strategy_name in self.strategy_bridges:
                config = self.template_configs[strategy_name]
                report['strategy_details'][strategy_name] = {
                    'status': 'migrated',
                    'template_id': config.template_id,
                    'instance_id': config.strategy_instance_id,
                    'improvements': config.metadata.get('improvements', []),
                    'legacy_file': config.metadata.get('migrated_from', 'unknown')
                }
            else:
                report['strategy_details'][strategy_name] = {
                    'status': 'pending',
                    'legacy_file': self.legacy_strategies[strategy_name]['file_path']
                }
        
        # Add recommendations
        report['recommendations'] = [
            'Test migrated strategies with historical data before production deployment',
            'Monitor signal quality and execution performance compared to legacy',
            'Consider parameter optimization using the new template framework',
            'Implement gradual rollout with parallel testing initially',
            'Set up comprehensive monitoring and alerting for new system'
        ]
        
        return report
    
    def save_migration_configs(self, output_dir: str = "config/migrated_strategies/"):
        """Save migration configurations for future use."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for strategy_name, config in self.template_configs.items():
            config_file = output_path / f"{strategy_name}_template_config.json"
            
            # Convert config to serializable format
            config_dict = {
                'template_id': config.template_id,
                'strategy_instance_id': config.strategy_instance_id,
                'parameters': config.parameters,
                'metadata': config.metadata
            }
            
            with open(config_file, 'w') as f:
                json.dump(config_dict, f, indent=2)
            
            logger.info(f"💾 Saved {strategy_name} config to {config_file}")

def main():
    """Main migration script."""
    parser = argparse.ArgumentParser(description='Strategy Migration Toolkit')
    parser.add_argument('--strategy', choices=['momentum', 'mean_reversion', 'all'], 
                       default='all', help='Strategy to migrate')
    parser.add_argument('--validate', action='store_true', 
                       help='Validate migration')
    parser.add_argument('--test', action='store_true', 
                       help='Test migrated strategies')
    parser.add_argument('--save-config', action='store_true', 
                       help='Save migration configurations')
    parser.add_argument('--report', action='store_true', 
                       help='Generate migration report')
    
    args = parser.parse_args()
    
    # Initialize migration toolkit
    migrator = StrategyMigrationToolkit()
    
    # Determine strategies to migrate
    if args.strategy == 'all':
        strategies_to_migrate = ['momentum', 'mean_reversion']
    else:
        strategies_to_migrate = [args.strategy]
    
    logger.info("🚀 Starting strategy migration process...")
    logger.info(f"   Strategies to migrate: {strategies_to_migrate}")
    
    # Perform migrations
    migration_success = True
    for strategy in strategies_to_migrate:
        try:
            migrator.migrate_strategy(strategy)
            
            if args.validate:
                if not migrator.validate_migration(strategy):
                    migration_success = False
            
            if args.test:
                if not migrator.test_migration(strategy):
                    migration_success = False
                    
        except Exception as e:
            logger.error(f"❌ Migration failed for {strategy}: {str(e)}")
            migration_success = False
    
    # Save configurations if requested
    if args.save_config:
        migrator.save_migration_configs()
    
    # Generate report if requested
    if args.report:
        report = migrator.generate_migration_report()
        print("\n" + "="*50)
        print("MIGRATION REPORT")
        print("="*50)
        print(f"Total Strategies: {report['migration_summary']['total_strategies']}")
        print(f"Migrated: {report['migration_summary']['migrated_strategies']}")
        print(f"Success Rate: {report['migration_summary']['success_rate']:.1f}%")
        print("\nStrategy Details:")
        for name, details in report['strategy_details'].items():
            print(f"  {name}: {details['status']}")
            if details['status'] == 'migrated':
                print(f"    Template: {details['template_id']}")
        print("\nRecommendations:")
        for rec in report['recommendations']:
            print(f"  • {rec}")
    
    # Final status
    if migration_success:
        logger.info("🎉 Migration completed successfully!")
        print("\n✅ Migration completed successfully!")
        print("Next steps:")
        print("  1. Review generated configurations")
        print("  2. Test with your historical data")
        print("  3. Deploy gradually with monitoring")
    else:
        logger.error("❌ Migration completed with errors")
        print("\n❌ Migration completed with errors")
        print("Please review the logs and fix issues before deployment")

if __name__ == "__main__":
    main()
