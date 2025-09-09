#!/usr/bin/env python3
"""
Backtest Configuration Loader
=============================

Centralized configuration loader for all backtests to eliminate hardcoded
parameters and provide consistent configuration across strategies.

Features:
- YAML-based configuration management
- Environment variable overrides
- Validation and error handling
- Strategy-specific parameter resolution
- Scenario-based testing support

Author: StatArb Gemini Team
Version: 1.0.0
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from datetime import datetime, time
import logging

logger = logging.getLogger(__name__)

@dataclass
class TradingPeriod:
    """Trading period configuration"""
    start_date: str
    end_date: str
    description: str
    start_time: str = "09:30:00"
    end_time: str = "16:00:00"
    timezone: str = "US/Eastern"

@dataclass
class UniverseConfig:
    """Universe configuration"""
    symbols: Optional[List[str]] = None
    pairs: Optional[List[List[str]]] = None
    description: str = ""

@dataclass
class DataConfig:
    """Data configuration"""
    frequency: str
    source: str = "clickhouse"
    fallback: str = "synthetic"
    validation_enabled: bool = True

@dataclass
class RiskConfig:
    """Risk management configuration"""
    max_position_size: float = 0.15
    max_portfolio_risk: float = 0.20
    max_drawdown_limit: float = 0.15
    default_stop_loss: float = 0.03
    default_take_profit: float = 0.06

@dataclass
class BacktestConfig:
    """Complete backtest configuration"""
    # Core parameters
    trading_period: TradingPeriod
    universe: UniverseConfig
    data_config: DataConfig
    capital: float
    risk_config: RiskConfig
    
    # Strategy specific
    strategy_params: Dict[str, Any] = field(default_factory=dict)
    
    # Performance
    benchmark_symbol: str = "SPY"
    risk_free_rate: float = 0.02
    
    # Environment
    log_level: str = "INFO"
    save_results: bool = True
    results_directory: str = "results/"

class BacktestConfigLoader:
    """
    Centralized configuration loader for backtests
    
    Loads configuration from YAML file and provides methods to get
    strategy-specific configurations with proper validation.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration loader
        
        Args:
            config_path: Path to configuration file. If None, uses default location.
        """
        if config_path is None:
            # Default to configs/backtest_config.yml in project root
            project_root = Path(__file__).parent.parent
            config_path = project_root / "configs" / "backtest_config.yml"
        
        self.config_path = Path(config_path)
        self.config_data: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from YAML file"""
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
            with open(self.config_path, 'r') as file:
                self.config_data = yaml.safe_load(file)
            
            logger.info(f"✅ Loaded backtest configuration from {self.config_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load configuration: {e}")
            raise
    
    def get_trading_period(self, period_name: str) -> TradingPeriod:
        """
        Get trading period configuration
        
        Args:
            period_name: Name of the trading period (e.g., 'single_day', 'one_week')
            
        Returns:
            TradingPeriod configuration
        """
        try:
            # Handle default period
            if period_name == "default":
                period_name = self.config_data["trading_periods"]["default"]
            
            period_config = self.config_data["trading_periods"][period_name]
            session_config = self.config_data["trading_session"]
            
            return TradingPeriod(
                start_date=period_config["start_date"],
                end_date=period_config["end_date"],
                description=period_config["description"],
                start_time=session_config["start_time"],
                end_time=session_config["end_time"],
                timezone=session_config["timezone"]
            )
            
        except KeyError as e:
            raise ValueError(f"Trading period '{period_name}' not found in configuration: {e}")
    
    def get_universe(self, universe_name: str) -> UniverseConfig:
        """
        Get universe configuration
        
        Args:
            universe_name: Name of the universe (e.g., 'single_stock', 'tech_stocks')
            
        Returns:
            UniverseConfig configuration
        """
        try:
            # Handle default universe
            if universe_name == "default":
                universe_name = self.config_data["universes"]["default"]
            
            universe_config = self.config_data["universes"][universe_name]
            
            return UniverseConfig(
                symbols=universe_config.get("symbols"),
                pairs=universe_config.get("pairs"),
                description=universe_config.get("description", "")
            )
            
        except KeyError as e:
            raise ValueError(f"Universe '{universe_name}' not found in configuration: {e}")
    
    def get_data_config(self, strategy: str, frequency: Optional[str] = None) -> DataConfig:
        """
        Get data configuration for strategy
        
        Args:
            strategy: Strategy name (momentum, mean_reversion, pairs_trading)
            frequency: Optional frequency override
            
        Returns:
            DataConfig configuration
        """
        try:
            data_config = self.config_data["data_config"]
            
            # Use provided frequency or strategy default
            if frequency is None:
                frequency = data_config["strategy_defaults"].get(strategy, "5min")
            
            return DataConfig(
                frequency=frequency,
                source=data_config["source"]["primary"],
                fallback=data_config["source"]["fallback"],
                validation_enabled=data_config["source"]["validation_enabled"]
            )
            
        except KeyError as e:
            raise ValueError(f"Data configuration error: {e}")
    
    def get_risk_config(self, strategy: str) -> RiskConfig:
        """
        Get risk configuration for strategy
        
        Args:
            strategy: Strategy name
            
        Returns:
            RiskConfig configuration
        """
        try:
            risk_config = self.config_data["risk_config"]
            portfolio_config = risk_config["portfolio"]
            position_config = risk_config["position"]
            
            # Get strategy-specific multipliers
            multipliers = risk_config["strategy_multipliers"].get(strategy, {})
            stop_multiplier = multipliers.get("stop_loss_multiplier", 1.0)
            profit_multiplier = multipliers.get("take_profit_multiplier", 1.0)
            
            return RiskConfig(
                max_position_size=position_config["max_position_size"],
                max_portfolio_risk=portfolio_config["max_drawdown_limit"],
                max_drawdown_limit=portfolio_config["max_drawdown_limit"],
                default_stop_loss=position_config["default_stop_loss"] * stop_multiplier,
                default_take_profit=position_config["default_take_profit"] * profit_multiplier
            )
            
        except KeyError as e:
            raise ValueError(f"Risk configuration error: {e}")
    
    def get_capital(self, strategy: str) -> float:
        """
        Get capital allocation for strategy
        
        Args:
            strategy: Strategy name
            
        Returns:
            Capital amount
        """
        try:
            capital_config = self.config_data["capital_config"]
            return capital_config["strategy_allocations"].get(
                strategy, 
                capital_config["base_capital"]
            )
            
        except KeyError as e:
            raise ValueError(f"Capital configuration error: {e}")
    
    def get_strategy_params(self, strategy: str) -> Dict[str, Any]:
        """
        Get strategy-specific parameters
        
        Args:
            strategy: Strategy name
            
        Returns:
            Dictionary of strategy parameters
        """
        try:
            return self.config_data["strategy_configs"].get(strategy, {})
            
        except KeyError:
            return {}
    
    def get_scenario_config(self, scenario_name: str) -> Dict[str, Any]:
        """
        Get predefined scenario configuration
        
        Args:
            scenario_name: Name of the scenario
            
        Returns:
            Scenario configuration dictionary
        """
        try:
            return self.config_data["scenarios"][scenario_name]
            
        except KeyError as e:
            raise ValueError(f"Scenario '{scenario_name}' not found in configuration: {e}")
    
    def build_backtest_config(self, 
                            strategy: str,
                            scenario: Optional[str] = None,
                            period: Optional[str] = None,
                            universe: Optional[str] = None,
                            frequency: Optional[str] = None,
                            capital: Optional[float] = None) -> BacktestConfig:
        """
        Build complete backtest configuration
        
        Args:
            strategy: Strategy name (momentum, mean_reversion, pairs_trading)
            scenario: Optional scenario name to use as base
            period: Optional trading period override
            universe: Optional universe override
            frequency: Optional frequency override
            capital: Optional capital override
            
        Returns:
            Complete BacktestConfig object
        """
        try:
            # Start with scenario if provided
            if scenario:
                scenario_config = self.get_scenario_config(scenario)
                period = period or scenario_config.get("period", "default")
                universe = universe or scenario_config.get("universe", "default")
                frequency = frequency or scenario_config.get("frequency")
                capital = capital or scenario_config.get("capital")
            
            # Use defaults if not specified
            period = period or "default"
            universe = universe or "default"
            capital = capital or self.get_capital(strategy)
            
            # Build configuration components
            trading_period = self.get_trading_period(period)
            universe_config = self.get_universe(universe)
            data_config = self.get_data_config(strategy, frequency)
            risk_config = self.get_risk_config(strategy)
            strategy_params = self.get_strategy_params(strategy)
            
            # Environment settings
            env_config = self.config_data.get("environment", {})
            performance_config = self.config_data.get("performance_config", {})
            
            return BacktestConfig(
                trading_period=trading_period,
                universe=universe_config,
                data_config=data_config,
                capital=capital,
                risk_config=risk_config,
                strategy_params=strategy_params,
                benchmark_symbol=performance_config.get("benchmark_symbol", "SPY"),
                risk_free_rate=performance_config.get("risk_free_rate", 0.02),
                log_level=env_config.get("log_level", "INFO"),
                save_results=env_config.get("save_results", True),
                results_directory=env_config.get("results_directory", "results/")
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to build backtest configuration: {e}")
            raise
    
    def list_available_periods(self) -> List[str]:
        """Get list of available trading periods"""
        return list(self.config_data["trading_periods"].keys())
    
    def list_available_universes(self) -> List[str]:
        """Get list of available universes"""
        return list(self.config_data["universes"].keys())
    
    def list_available_scenarios(self) -> List[str]:
        """Get list of available scenarios"""
        return list(self.config_data["scenarios"].keys())
    
    def validate_config(self) -> bool:
        """
        Validate configuration file structure
        
        Returns:
            True if configuration is valid, False otherwise
        """
        required_sections = [
            "trading_periods", "universes", "data_config", 
            "capital_config", "risk_config", "scenarios"
        ]
        
        try:
            for section in required_sections:
                if section not in self.config_data:
                    logger.error(f"❌ Missing required section: {section}")
                    return False
            
            # Validate default references
            default_period = self.config_data["trading_periods"].get("default")
            if default_period and default_period not in self.config_data["trading_periods"]:
                logger.error(f"❌ Invalid default trading period: {default_period}")
                return False
            
            default_universe = self.config_data["universes"].get("default")
            if default_universe and default_universe not in self.config_data["universes"]:
                logger.error(f"❌ Invalid default universe: {default_universe}")
                return False
            
            logger.info("✅ Configuration validation passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Configuration validation failed: {e}")
            return False

# Convenience functions for easy access
def load_backtest_config(config_path: Optional[str] = None) -> BacktestConfigLoader:
    """Load backtest configuration"""
    return BacktestConfigLoader(config_path)

def get_strategy_config(strategy: str, 
                       scenario: Optional[str] = None,
                       **overrides) -> BacktestConfig:
    """Get complete configuration for a strategy"""
    loader = load_backtest_config()
    return loader.build_backtest_config(strategy, scenario, **overrides)

# Example usage
if __name__ == "__main__":
    # Test the configuration loader
    loader = BacktestConfigLoader()
    
    if loader.validate_config():
        print("✅ Configuration loaded and validated successfully")
        
        # Show available options
        print(f"Available periods: {loader.list_available_periods()}")
        print(f"Available universes: {loader.list_available_universes()}")
        print(f"Available scenarios: {loader.list_available_scenarios()}")
        
        # Test building configurations
        momentum_config = loader.build_backtest_config("momentum", scenario="feb_2025_test")
        print(f"✅ Momentum config: {momentum_config.trading_period.start_date} to {momentum_config.trading_period.end_date}")
        
        pairs_config = loader.build_backtest_config("pairs_trading", period="jan_2025")
        print(f"✅ Pairs config: {pairs_config.trading_period.start_date} to {pairs_config.trading_period.end_date}")
    else:
        print("❌ Configuration validation failed")
