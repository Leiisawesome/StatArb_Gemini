"""
Strategy Factory

Factory system for creating strategy objects from parsed JSON data
and building blocks.

Author: Pro Quant Desk Trader
"""

import logging
from typing import Dict, List, Optional, Any, Type
from abc import ABC, abstractmethod

from strategy_layer.base import StrategyDefinition, StrategyConfig, StrategyType, StrategyError


class StrategyFactory:
    """Factory for creating strategy objects"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._strategy_classes: Dict[str, Type[StrategyDefinition]] = {}
        self._strategy_templates: Dict[str, Dict[str, Any]] = {}
        self._register_default_strategies()
    
    def register_strategy_class(self, strategy_type: str, strategy_class: Type[StrategyDefinition]):
        """
        Register a strategy class for a specific type
        
        Args:
            strategy_type: Strategy type identifier
            strategy_class: Strategy class to register
        """
        self._strategy_classes[strategy_type] = strategy_class
        self.logger.info(f"Registered strategy class for type: {strategy_type}")
    
    def register_strategy_template(self, template_name: str, template_data: Dict[str, Any]):
        """
        Register a strategy template
        
        Args:
            template_name: Name of the template
            template_data: Template data
        """
        self._strategy_templates[template_name] = template_data
        self.logger.info(f"Registered strategy template: {template_name}")
    
    def create_strategy(self, strategy_data: Dict[str, Any]) -> StrategyDefinition:
        """
        Create a strategy object from parsed data
        
        Args:
            strategy_data: Parsed strategy data
            
        Returns:
            Strategy object
            
        Raises:
            StrategyError: If strategy creation fails
        """
        try:
            strategy_type = strategy_data.get('strategy_type')
            if not strategy_type:
                raise StrategyError("Strategy type is required")
            
            # Get strategy class
            strategy_class = self._strategy_classes.get(strategy_type)
            if not strategy_class:
                raise StrategyError(f"No strategy class registered for type: {strategy_type}")
            
            # Create strategy config
            config = StrategyConfig.from_dict(strategy_data)
            
            # Create strategy object
            strategy = strategy_class(config)
            
            self.logger.info(f"Created strategy: {strategy_data.get('strategy_name', 'Unknown')}")
            return strategy
            
        except Exception as e:
            error_msg = f"Failed to create strategy: {e}"
            self.logger.error(error_msg)
            raise StrategyError(error_msg) from e
    
    def create_strategy_from_template(self, template_name: str, **kwargs) -> StrategyDefinition:
        """
        Create a strategy from a template
        
        Args:
            template_name: Name of the template
            **kwargs: Template parameters
            
        Returns:
            Strategy object
            
        Raises:
            StrategyError: If template not found or creation fails
        """
        try:
            # Get template
            template = self._strategy_templates.get(template_name)
            if not template:
                raise StrategyError(f"Strategy template not found: {template_name}")
            
            # Merge template with parameters
            strategy_data = template.copy()
            strategy_data.update(kwargs)
            
            # Create strategy
            return self.create_strategy(strategy_data)
            
        except Exception as e:
            error_msg = f"Failed to create strategy from template {template_name}: {e}"
            self.logger.error(error_msg)
            raise StrategyError(error_msg) from e
    
    def create_strategy_from_file(self, file_path: str) -> StrategyDefinition:
        """
        Create a strategy from a JSON file
        
        Args:
            file_path: Path to strategy JSON file
            
        Returns:
            Strategy object
            
        Raises:
            StrategyError: If file parsing or strategy creation fails
        """
        try:
            from strategy_layer.parsers import StrategyParser
            
            # Parse strategy file
            parser = StrategyParser()
            strategy_data = parser.parse_strategy_file(file_path)
            
            # Create strategy
            return self.create_strategy(strategy_data)
            
        except Exception as e:
            error_msg = f"Failed to create strategy from file {file_path}: {e}"
            self.logger.error(error_msg)
            raise StrategyError(error_msg) from e
    
    def create_strategy_from_string(self, strategy_json: str) -> StrategyDefinition:
        """
        Create a strategy from JSON string
        
        Args:
            strategy_json: JSON string containing strategy data
            
        Returns:
            Strategy object
            
        Raises:
            StrategyError: If parsing or strategy creation fails
        """
        try:
            from strategy_layer.parsers import StrategyParser
            
            # Parse strategy string
            parser = StrategyParser()
            strategy_data = parser.parse_strategy_string(strategy_json)
            
            # Create strategy
            return self.create_strategy(strategy_data)
            
        except Exception as e:
            error_msg = f"Failed to create strategy from string: {e}"
            self.logger.error(error_msg)
            raise StrategyError(error_msg) from e
    
    def get_available_strategy_types(self) -> List[str]:
        """
        Get list of available strategy types
        
        Returns:
            List of strategy type names
        """
        return list(self._strategy_classes.keys())
    
    def get_available_templates(self) -> List[str]:
        """
        Get list of available templates
        
        Returns:
            List of template names
        """
        return list(self._strategy_templates.keys())
    
    def get_strategy_class(self, strategy_type: str) -> Optional[Type[StrategyDefinition]]:
        """
        Get strategy class for a type
        
        Args:
            strategy_type: Strategy type
            
        Returns:
            Strategy class or None if not found
        """
        return self._strategy_classes.get(strategy_type)
    
    def get_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Get template by name
        
        Args:
            template_name: Template name
            
        Returns:
            Template data or None if not found
        """
        return self._strategy_templates.get(template_name)
    
    def validate_strategy_data(self, strategy_data: Dict[str, Any]) -> bool:
        """
        Validate strategy data can be used to create a strategy
        
        Args:
            strategy_data: Strategy data to validate
            
        Returns:
            True if valid
            
        Raises:
            StrategyError: If validation fails
        """
        try:
            strategy_type = strategy_data.get('strategy_type')
            if not strategy_type:
                raise StrategyError("Strategy type is required")
            
            if strategy_type not in self._strategy_classes:
                raise StrategyError(f"No strategy class registered for type: {strategy_type}")
            
            # Try to create config
            StrategyConfig.from_dict(strategy_data)
            
            return True
            
        except Exception as e:
            raise StrategyError(f"Strategy data validation failed: {e}") from e
    
    def _register_default_strategies(self):
        """Register default strategy classes"""
        self.logger.info("Registering default strategy classes")
        
        try:
            # Import concrete strategy implementations
            from strategy_layer.strategies import (
                MomentumStrategyDefinition,
                PairTradingStrategyDefinition,
                MeanReversionStrategyDefinition
            )
            
            # Register momentum strategy
            self.register_strategy_class('momentum', MomentumStrategyDefinition)
            
            # Register pair trading strategy
            self.register_strategy_class('pair_trading', PairTradingStrategyDefinition)
            
            # Register mean reversion strategy
            self.register_strategy_class('mean_reversion', MeanReversionStrategyDefinition)
            
            self.logger.info("Default strategy classes registered successfully")
            
        except ImportError as e:
            self.logger.warning(f"Could not import strategy classes: {e}")
        except Exception as e:
            self.logger.error(f"Error registering strategy classes: {e}")
    
    def _register_default_templates(self):
        """Register default strategy templates"""
        self.logger.info("Registering default strategy templates")
        
        # Basic momentum template
        momentum_template = {
            "strategy_type": "momentum",
            "strategy_name": "Basic Momentum Strategy",
            "version": "1.0.0",
            "description": "Basic momentum trading strategy",
            "signal_generation": {
                "indicators": [
                    {
                        "name": "RSI",
                        "type": "rsi",
                        "parameters": {"period": 14},
                        "weight": 0.5
                    },
                    {
                        "name": "MACD",
                        "type": "macd",
                        "parameters": {"fast": 12, "slow": 26, "signal": 9},
                        "weight": 0.5
                    }
                ],
                "signal_combination": "weighted_average"
            },
            "risk_management": {
                "position_sizing": {
                    "method": "fixed",
                    "max_position_size": 0.1
                },
                "stop_loss": {
                    "enabled": True,
                    "percentage": 0.02
                }
            }
        }
        
        self.register_strategy_template("basic_momentum", momentum_template)
        
        # Basic pair trading template
        pair_trading_template = {
            "strategy_type": "pair_trading",
            "strategy_name": "Basic Pair Trading Strategy",
            "version": "1.0.0",
            "description": "Basic pair trading strategy",
            "signal_generation": {
                "indicators": [
                    {
                        "name": "Z-Score",
                        "type": "zscore",
                        "parameters": {"period": 20},
                        "weight": 1.0
                    }
                ],
                "signal_combination": "weighted_average"
            },
            "risk_management": {
                "position_sizing": {
                    "method": "fixed",
                    "max_position_size": 0.05
                },
                "stop_loss": {
                    "enabled": True,
                    "percentage": 0.03
                }
            }
        }
        
        self.register_strategy_template("basic_pair_trading", pair_trading_template)
        
        self.logger.info("Default strategy templates registered")
