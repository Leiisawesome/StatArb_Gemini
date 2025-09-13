#!/usr/bin/env python3
"""
Universe Selection Configuration Loader
========================================

Configuration loader and manager for the intelligent universe selection system.
This module handles loading, parsing, and validation of universe selection
configurations, providing easy access to selection parameters and constraints.

Key Features:
- YAML configuration loading and validation
- Dynamic configuration updates
- Strategy-specific parameter access
- Market condition adjustments
- Configuration persistence and backup

Author: StatArb Gemini Team
Version: 1.0.0
"""

import os
import logging
import yaml
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

@dataclass
class SelectionConstraints:
    """Selection constraints configuration"""
    max_instruments: int = 10
    min_instruments: int = 3
    max_sector_concentration: float = 0.40
    max_individual_weight: float = 0.25
    min_individual_weight: float = 0.05
    min_liquidity_score: float = 0.30
    min_quality_score: float = 0.40
    max_correlation: float = 0.80
    max_portfolio_volatility: float = 0.25
    max_individual_volatility: float = 0.50
    max_beta: float = 2.0
    min_beta: float = 0.2

@dataclass
class StrategyPreferences:
    """Strategy-specific preferences"""
    min_fitness_score: float = 0.50
    preferred_fitness_score: float = 0.70
    optimal_regimes: List[str] = field(default_factory=list)
    avoid_regimes: List[str] = field(default_factory=list)
    fitness_weight: float = 0.35
    regime_weight: float = 0.25
    statistical_weight: float = 0.20
    liquidity_weight: float = 0.15
    risk_weight: float = 0.05

@dataclass
class ValidationConfig:
    """Validation configuration parameters"""
    in_sample_ratio: float = 0.70
    min_validation_periods: int = 50
    min_sharpe_ratio: float = 0.50
    max_drawdown_threshold: float = -0.25
    min_win_rate: float = 0.45
    significance_level: float = 0.05
    min_statistical_power: float = 0.80
    min_selection_stability: float = 0.70
    max_weight_drift: float = 0.20

@dataclass
class UniverseSelectionConfig:
    """Complete universe selection configuration"""
    config_version: str = "1.0.0"
    last_updated: str = ""
    description: str = ""
    
    # Core configuration
    candidate_universes: Dict[str, List[str]] = field(default_factory=dict)
    selection_constraints: SelectionConstraints = field(default_factory=SelectionConstraints)
    strategy_preferences: Dict[str, StrategyPreferences] = field(default_factory=dict)
    validation_config: ValidationConfig = field(default_factory=ValidationConfig)
    
    # Advanced configuration
    market_condition_adjustments: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    regime_specific_preferences: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    historical_analysis: Dict[str, Any] = field(default_factory=dict)
    output_config: Dict[str, Any] = field(default_factory=dict)
    integration: Dict[str, Any] = field(default_factory=dict)
    advanced_features: Dict[str, Any] = field(default_factory=dict)

class UniverseSelectionConfigLoader:
    """
    Configuration loader and manager for universe selection system
    
    This class handles loading, parsing, validation, and dynamic updates
    of universe selection configurations.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration loader
        
        Args:
            config_path: Path to configuration file (uses default if None)
        """
        self.config_path = config_path or "configs/universe_selection_config.yml"
        self.config: Optional[UniverseSelectionConfig] = None
        self.config_timestamp: Optional[datetime] = None
        
        # Ensure config directory exists
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        logger.info(f"🔧 Universe Selection Config Loader initialized")
        logger.info(f"   📁 Config path: {self.config_path}")
    
    def load_config(self, force_reload: bool = False) -> UniverseSelectionConfig:
        """
        Load configuration from file
        
        Args:
            force_reload: Force reload even if already loaded
            
        Returns:
            Loaded configuration object
        """
        try:
            # Check if reload is needed
            if not force_reload and self.config is not None:
                file_mtime = datetime.fromtimestamp(os.path.getmtime(self.config_path))
                if self.config_timestamp and file_mtime <= self.config_timestamp:
                    logger.debug("📋 Using cached configuration")
                    return self.config
            
            logger.info(f"📖 Loading configuration from {self.config_path}")
            
            # Load YAML configuration
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Parse and validate configuration
            self.config = self._parse_config(config_data)
            self.config_timestamp = datetime.now()
            
            logger.info("✅ Configuration loaded successfully")
            logger.info(f"   📊 Version: {self.config.config_version}")
            logger.info(f"   🎯 Strategies: {list(self.config.strategy_preferences.keys())}")
            logger.info(f"   🌐 Universes: {list(self.config.candidate_universes.keys())}")
            
            return self.config
            
        except FileNotFoundError:
            logger.warning(f"⚠️ Configuration file not found: {self.config_path}")
            logger.info("🔧 Creating default configuration")
            return self._create_default_config()
            
        except Exception as e:
            logger.error(f"❌ Failed to load configuration: {e}")
            logger.info("🔧 Using default configuration")
            return self._create_default_config()
    
    def _parse_config(self, config_data: Dict[str, Any]) -> UniverseSelectionConfig:
        """Parse configuration data into structured objects"""
        try:
            # Parse selection constraints
            constraints_data = config_data.get('selection_constraints', {})
            selection_constraints = SelectionConstraints(**constraints_data)
            
            # Parse strategy preferences
            strategy_preferences = {}
            strategies_data = config_data.get('strategy_preferences', {})
            
            for strategy, prefs_data in strategies_data.items():
                # Handle special fields
                prefs_data = prefs_data.copy()  # Don't modify original
                
                # Remove non-dataclass fields
                non_dataclass_fields = [
                    'preferred_autocorr_range', 'preferred_volatility_range',
                    'preferred_half_life_range', 'preferred_ou_theta_range',
                    'preferred_momentum_persistence', 'min_cointegration_score',
                    'preferred_correlation_range', 'max_correlation_instability'
                ]
                
                for field in non_dataclass_fields:
                    prefs_data.pop(field, None)
                
                # Create strategy preferences object
                strategy_preferences[strategy] = StrategyPreferences(**prefs_data)
            
            # Parse validation config
            validation_data = config_data.get('validation_config', {})
            validation_config = ValidationConfig(**validation_data)
            
            # Create main config object
            config = UniverseSelectionConfig(
                config_version=config_data.get('config_version', '1.0.0'),
                last_updated=config_data.get('last_updated', datetime.now().isoformat()),
                description=config_data.get('description', ''),
                candidate_universes=config_data.get('candidate_universes', {}),
                selection_constraints=selection_constraints,
                strategy_preferences=strategy_preferences,
                validation_config=validation_config,
                market_condition_adjustments=config_data.get('market_condition_adjustments', {}),
                regime_specific_preferences=config_data.get('regime_specific_preferences', {}),
                historical_analysis=config_data.get('historical_analysis', {}),
                output_config=config_data.get('output_config', {}),
                integration=config_data.get('integration', {}),
                advanced_features=config_data.get('advanced_features', {})
            )
            
            return config
            
        except Exception as e:
            logger.error(f"❌ Configuration parsing failed: {e}")
            raise
    
    def _create_default_config(self) -> UniverseSelectionConfig:
        """Create default configuration"""
        try:
            logger.info("🔧 Creating default universe selection configuration")
            
            # Default candidate universes
            default_universes = {
                'large_cap': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'JPM', 'JNJ', 'PG'],
                'technology': ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'AMD', 'CRM', 'ORCL'],
                'financial': ['JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'V', 'MA'],
                'etfs': ['SPY', 'QQQ', 'IWM', 'VTI', 'TLT']
            }
            
            # Default strategy preferences
            default_strategies = {
                'momentum': StrategyPreferences(
                    min_fitness_score=0.50,
                    preferred_fitness_score=0.70,
                    optimal_regimes=['trending', 'bullish'],
                    avoid_regimes=['sideways', 'high_volatility'],
                    fitness_weight=0.40,
                    regime_weight=0.30,
                    liquidity_weight=0.20,
                    risk_weight=0.10
                ),
                'mean_reversion': StrategyPreferences(
                    min_fitness_score=0.50,
                    preferred_fitness_score=0.70,
                    optimal_regimes=['sideways', 'volatile'],
                    avoid_regimes=['strong_trending'],
                    fitness_weight=0.35,
                    regime_weight=0.25,
                    statistical_weight=0.25,
                    risk_weight=0.15
                ),
                'pairs_trading': StrategyPreferences(
                    min_fitness_score=0.40,
                    preferred_fitness_score=0.65,
                    optimal_regimes=['stable', 'low_volatility'],
                    avoid_regimes=['high_volatility'],
                    statistical_weight=0.40,
                    liquidity_weight=0.25,
                    fitness_weight=0.20,
                    risk_weight=0.15
                )
            }
            
            config = UniverseSelectionConfig(
                config_version="1.0.0",
                last_updated=datetime.now().isoformat(),
                description="Default universe selection configuration",
                candidate_universes=default_universes,
                selection_constraints=SelectionConstraints(),
                strategy_preferences=default_strategies,
                validation_config=ValidationConfig()
            )
            
            # Save default configuration
            self._save_config(config)
            
            return config
            
        except Exception as e:
            logger.error(f"❌ Failed to create default configuration: {e}")
            raise
    
    def get_candidate_universe(self, universe_name: str) -> List[str]:
        """
        Get candidate universe by name
        
        Args:
            universe_name: Name of the universe
            
        Returns:
            List of symbols in the universe
        """
        try:
            if self.config is None:
                self.load_config()
            
            universe = self.config.candidate_universes.get(universe_name, [])
            
            if not universe:
                logger.warning(f"⚠️ Universe '{universe_name}' not found, using default")
                # Return a default universe
                all_symbols = []
                for symbols in self.config.candidate_universes.values():
                    all_symbols.extend(symbols)
                universe = list(set(all_symbols))[:10]  # Unique symbols, max 10
            
            logger.debug(f"📊 Universe '{universe_name}': {len(universe)} symbols")
            return universe
            
        except Exception as e:
            logger.error(f"❌ Failed to get universe '{universe_name}': {e}")
            return ['SPY', 'QQQ', 'IWM']  # Fallback
    
    def get_all_candidate_symbols(self) -> List[str]:
        """Get all unique symbols from all universes"""
        try:
            if self.config is None:
                self.load_config()
            
            all_symbols = []
            for universe in self.config.candidate_universes.values():
                all_symbols.extend(universe)
            
            unique_symbols = list(set(all_symbols))
            logger.debug(f"📊 Total unique symbols: {len(unique_symbols)}")
            
            return unique_symbols
            
        except Exception as e:
            logger.error(f"❌ Failed to get all symbols: {e}")
            return []
    
    def get_strategy_preferences(self, strategy: str) -> StrategyPreferences:
        """
        Get strategy-specific preferences
        
        Args:
            strategy: Strategy name
            
        Returns:
            Strategy preferences object
        """
        try:
            if self.config is None:
                self.load_config()
            
            preferences = self.config.strategy_preferences.get(strategy)
            
            if preferences is None:
                logger.warning(f"⚠️ Strategy '{strategy}' preferences not found, using default")
                preferences = StrategyPreferences()
            
            logger.debug(f"🎯 Strategy '{strategy}' preferences loaded")
            return preferences
            
        except Exception as e:
            logger.error(f"❌ Failed to get strategy preferences for '{strategy}': {e}")
            return StrategyPreferences()
    
    def get_selection_constraints(self, 
                                market_condition: Optional[str] = None) -> SelectionConstraints:
        """
        Get selection constraints, optionally adjusted for market conditions
        
        Args:
            market_condition: Current market condition for adjustments
            
        Returns:
            Selection constraints object
        """
        try:
            if self.config is None:
                self.load_config()
            
            # Start with base constraints
            constraints = self.config.selection_constraints
            
            # Apply market condition adjustments
            if market_condition and market_condition in self.config.market_condition_adjustments:
                adjustments = self.config.market_condition_adjustments[market_condition]
                
                # Create adjusted constraints
                constraints_dict = asdict(constraints)
                
                for key, value in adjustments.items():
                    if key in constraints_dict:
                        if key.endswith('_boost'):
                            # Handle boost adjustments
                            base_key = key.replace('_boost', '')
                            if base_key in constraints_dict:
                                constraints_dict[base_key] += value
                        else:
                            # Direct replacement
                            constraints_dict[key] = value
                
                constraints = SelectionConstraints(**constraints_dict)
                logger.debug(f"🌊 Applied '{market_condition}' adjustments to constraints")
            
            return constraints
            
        except Exception as e:
            logger.error(f"❌ Failed to get selection constraints: {e}")
            return SelectionConstraints()
    
    def get_validation_config(self) -> ValidationConfig:
        """Get validation configuration"""
        try:
            if self.config is None:
                self.load_config()
            
            return self.config.validation_config
            
        except Exception as e:
            logger.error(f"❌ Failed to get validation config: {e}")
            return ValidationConfig()
    
    def get_regime_preferences(self, regime: str) -> Dict[str, Any]:
        """
        Get regime-specific preferences
        
        Args:
            regime: Market regime name
            
        Returns:
            Regime preferences dictionary
        """
        try:
            if self.config is None:
                self.load_config()
            
            preferences = self.config.regime_specific_preferences.get(regime, {})
            logger.debug(f"🌊 Regime '{regime}' preferences: {len(preferences)} settings")
            
            return preferences
            
        except Exception as e:
            logger.error(f"❌ Failed to get regime preferences for '{regime}': {e}")
            return {}
    
    def get_output_config(self) -> Dict[str, Any]:
        """Get output configuration"""
        try:
            if self.config is None:
                self.load_config()
            
            return self.config.output_config
            
        except Exception as e:
            logger.error(f"❌ Failed to get output config: {e}")
            return {
                'results_directory': 'configs/universe_selection_results/',
                'primary_format': 'yaml'
            }
    
    def update_strategy_preferences(self, 
                                  strategy: str, 
                                  preferences: StrategyPreferences) -> None:
        """
        Update strategy preferences
        
        Args:
            strategy: Strategy name
            preferences: New preferences
        """
        try:
            if self.config is None:
                self.load_config()
            
            self.config.strategy_preferences[strategy] = preferences
            self._save_config(self.config)
            
            logger.info(f"✅ Updated preferences for strategy '{strategy}'")
            
        except Exception as e:
            logger.error(f"❌ Failed to update strategy preferences: {e}")
    
    def add_candidate_universe(self, name: str, symbols: List[str]) -> None:
        """
        Add new candidate universe
        
        Args:
            name: Universe name
            symbols: List of symbols
        """
        try:
            if self.config is None:
                self.load_config()
            
            self.config.candidate_universes[name] = symbols
            self._save_config(self.config)
            
            logger.info(f"✅ Added universe '{name}' with {len(symbols)} symbols")
            
        except Exception as e:
            logger.error(f"❌ Failed to add candidate universe: {e}")
    
    def _save_config(self, config: UniverseSelectionConfig) -> None:
        """Save configuration to file"""
        try:
            # Update timestamp
            config.last_updated = datetime.now().isoformat()
            
            # Convert to dictionary for YAML serialization
            config_dict = self._config_to_dict(config)
            
            # Create backup of existing config
            if os.path.exists(self.config_path):
                backup_path = f"{self.config_path}.backup"
                os.rename(self.config_path, backup_path)
            
            # Save new configuration
            with open(self.config_path, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
            
            logger.info(f"💾 Configuration saved to {self.config_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save configuration: {e}")
    
    def _config_to_dict(self, config: UniverseSelectionConfig) -> Dict[str, Any]:
        """Convert configuration object to dictionary for serialization"""
        try:
            config_dict = {
                'config_version': config.config_version,
                'last_updated': config.last_updated,
                'description': config.description,
                'candidate_universes': config.candidate_universes,
                'selection_constraints': asdict(config.selection_constraints),
                'strategy_preferences': {},
                'validation_config': asdict(config.validation_config),
                'market_condition_adjustments': config.market_condition_adjustments,
                'regime_specific_preferences': config.regime_specific_preferences,
                'historical_analysis': config.historical_analysis,
                'output_config': config.output_config,
                'integration': config.integration,
                'advanced_features': config.advanced_features
            }
            
            # Convert strategy preferences
            for strategy, prefs in config.strategy_preferences.items():
                config_dict['strategy_preferences'][strategy] = asdict(prefs)
            
            return config_dict
            
        except Exception as e:
            logger.error(f"❌ Configuration serialization failed: {e}")
            return {}
    
    def validate_config(self) -> Tuple[bool, List[str]]:
        """
        Validate current configuration
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        try:
            if self.config is None:
                self.load_config()
            
            errors = []
            
            # Validate candidate universes
            if not self.config.candidate_universes:
                errors.append("No candidate universes defined")
            
            for name, symbols in self.config.candidate_universes.items():
                if not symbols:
                    errors.append(f"Universe '{name}' is empty")
                if not isinstance(symbols, list):
                    errors.append(f"Universe '{name}' is not a list")
            
            # Validate strategy preferences
            if not self.config.strategy_preferences:
                errors.append("No strategy preferences defined")
            
            for strategy, prefs in self.config.strategy_preferences.items():
                if prefs.min_fitness_score < 0 or prefs.min_fitness_score > 1:
                    errors.append(f"Strategy '{strategy}' has invalid min_fitness_score")
                
                if prefs.preferred_fitness_score < prefs.min_fitness_score:
                    errors.append(f"Strategy '{strategy}' preferred_fitness_score < min_fitness_score")
            
            # Validate constraints
            constraints = self.config.selection_constraints
            if constraints.max_instruments < constraints.min_instruments:
                errors.append("max_instruments < min_instruments")
            
            if constraints.max_individual_weight < constraints.min_individual_weight:
                errors.append("max_individual_weight < min_individual_weight")
            
            # Validate validation config
            val_config = self.config.validation_config
            if val_config.in_sample_ratio <= 0 or val_config.in_sample_ratio >= 1:
                errors.append("Invalid in_sample_ratio (must be between 0 and 1)")
            
            is_valid = len(errors) == 0
            
            if is_valid:
                logger.info("✅ Configuration validation passed")
            else:
                logger.warning(f"⚠️ Configuration validation failed: {len(errors)} errors")
                for error in errors:
                    logger.warning(f"   - {error}")
            
            return is_valid, errors
            
        except Exception as e:
            logger.error(f"❌ Configuration validation failed: {e}")
            return False, [str(e)]

# Convenience functions for easy access
def load_universe_selection_config(config_path: Optional[str] = None) -> UniverseSelectionConfig:
    """Load universe selection configuration"""
    loader = UniverseSelectionConfigLoader(config_path)
    return loader.load_config()

def get_candidate_universe(universe_name: str, config_path: Optional[str] = None) -> List[str]:
    """Get candidate universe by name"""
    loader = UniverseSelectionConfigLoader(config_path)
    return loader.get_candidate_universe(universe_name)

def get_strategy_preferences(strategy: str, config_path: Optional[str] = None) -> StrategyPreferences:
    """Get strategy preferences"""
    loader = UniverseSelectionConfigLoader(config_path)
    return loader.get_strategy_preferences(strategy)

# Example usage and testing
if __name__ == "__main__":
    def test_config_loader():
        """Test the configuration loader"""
        logger.info("🔧 Testing Universe Selection Config Loader")
        
        # Test loading
        loader = UniverseSelectionConfigLoader()
        config = loader.load_config()
        
        print(f"✅ Loaded config version: {config.config_version}")
        print(f"📊 Universes: {list(config.candidate_universes.keys())}")
        print(f"🎯 Strategies: {list(config.strategy_preferences.keys())}")
        
        # Test validation
        is_valid, errors = loader.validate_config()
        print(f"✅ Validation: {'PASSED' if is_valid else 'FAILED'}")
        
        if errors:
            for error in errors:
                print(f"   ❌ {error}")
    
    # Run test
    test_config_loader()
