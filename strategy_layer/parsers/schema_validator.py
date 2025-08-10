"""
Schema Validator for Strategy Definitions

JSON schema validation for trading strategy definitions with comprehensive
error handling and validation reporting.

Author: Pro Quant Desk Trader
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from jsonschema import validate, ValidationError, SchemaError
from jsonschema.validators import validator_for

from strategy_layer.base import StrategyError, StrategyValidationError


class SchemaValidator:
    """JSON schema validator for strategy definitions"""
    
    def __init__(self, schema_dir: Optional[str] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.schema_dir = schema_dir or os.path.join(
            os.path.dirname(__file__), '..', 'schemas'
        )
        self.schemas = {}
        self._load_schemas()
    
    def _load_schemas(self):
        """Load all schema files from the schema directory"""
        schema_path = Path(self.schema_dir)
        if not schema_path.exists():
            self.logger.warning(f"Schema directory not found: {self.schema_dir}")
            return
        
        for schema_file in schema_path.glob("*.json"):
            try:
                with open(schema_file, 'r') as f:
                    schema = json.load(f)
                    schema_name = schema_file.stem
                    self.schemas[schema_name] = schema
                    self.logger.info(f"Loaded schema: {schema_name}")
            except Exception as e:
                self.logger.error(f"Failed to load schema {schema_file}: {e}")
    
    def validate_strategy(self, strategy_data: Dict[str, Any], schema_name: str = "strategy_schema") -> bool:
        """
        Validate strategy data against schema
        
        Args:
            strategy_data: Strategy data to validate
            schema_name: Name of the schema to use
            
        Returns:
            True if valid, raises ValidationError if invalid
            
        Raises:
            StrategyValidationError: If validation fails
        """
        if schema_name not in self.schemas:
            raise StrategyValidationError(f"Schema not found: {schema_name}")
        
        schema = self.schemas[schema_name]
        
        try:
            validate(instance=strategy_data, schema=schema)
            self.logger.info(f"Strategy validation passed for schema: {schema_name}")
            return True
        except ValidationError as e:
            error_msg = f"Strategy validation failed: {e.message}"
            if e.path:
                error_msg += f" at path: {' -> '.join(str(p) for p in e.path)}"
            
            self.logger.error(error_msg)
            raise StrategyValidationError(error_msg) from e
        except SchemaError as e:
            error_msg = f"Schema error: {e.message}"
            self.logger.error(error_msg)
            raise StrategyValidationError(error_msg) from e
    
    def validate_strategy_with_auto_schema(self, strategy_data: Dict[str, Any]) -> bool:
        """
        Validate strategy data with automatic schema selection based on strategy_type
        
        Args:
            strategy_data: Strategy data to validate
            
        Returns:
            True if valid, raises ValidationError if invalid
            
        Raises:
            StrategyValidationError: If validation fails or strategy_type is missing
        """
        # Extract strategy type
        strategy_type = strategy_data.get('strategy_type')
        if not strategy_type:
            raise StrategyValidationError("strategy_type is required for automatic schema selection")
        
        # Auto-select schema based on strategy type
        schema_name = self._get_schema_for_strategy_type(strategy_type)
        
        self.logger.info(f"Auto-selected schema '{schema_name}' for strategy_type '{strategy_type}'")
        
        # Validate with the selected schema
        return self.validate_strategy(strategy_data, schema_name)
    
    def _get_schema_for_strategy_type(self, strategy_type: str) -> str:
        """
        Get the appropriate schema name for a given strategy type
        
        Args:
            strategy_type: Type of strategy
            
        Returns:
            Schema name to use for validation
        """
        # Strategy type to schema mapping
        schema_mapping = {
            'momentum': 'momentum_schema',
            'pair_trading': 'pair_trading_schema',
            'mean_reversion': 'mean_reversion_schema',
            'custom': 'custom_schema'
        }
        
        # Get schema name with fallback to generic schema
        schema_name = schema_mapping.get(strategy_type.lower(), 'strategy_schema')
        
        # Verify the schema exists
        if schema_name not in self.schemas:
            self.logger.warning(f"Specific schema '{schema_name}' not found for strategy_type '{strategy_type}', falling back to generic schema")
            schema_name = 'strategy_schema'
        
        return schema_name
    
    def get_available_strategy_types(self) -> List[str]:
        """
        Get list of available strategy types that have specific schemas
        
        Returns:
            List of strategy types with dedicated schemas
        """
        return ['momentum', 'pair_trading', 'mean_reversion', 'custom']
    
    def get_schema_for_strategy_type(self, strategy_type: str) -> Optional[Dict[str, Any]]:
        """
        Get the schema dictionary for a specific strategy type
        
        Args:
            strategy_type: Type of strategy
            
        Returns:
            Schema dictionary or None if not found
        """
        schema_name = self._get_schema_for_strategy_type(strategy_type)
        return self.schemas.get(schema_name)
    
    def validate_strategy_file(self, file_path: str, schema_name: str = "strategy_schema") -> bool:
        """
        Validate strategy JSON file against schema
        
        Args:
            file_path: Path to the strategy JSON file
            schema_name: Name of the schema to use
            
        Returns:
            True if valid, raises ValidationError if invalid
        """
        try:
            with open(file_path, 'r') as f:
                strategy_data = json.load(f)
            
            return self.validate_strategy(strategy_data, schema_name)
        except FileNotFoundError:
            raise StrategyValidationError(f"Strategy file not found: {file_path}")
        except json.JSONDecodeError as e:
            raise StrategyValidationError(f"Invalid JSON in strategy file: {e}")
    
    def get_validation_errors(self, strategy_data: Dict[str, Any], schema_name: str = "strategy_schema") -> List[str]:
        """
        Get detailed validation errors without raising exceptions
        
        Args:
            strategy_data: Strategy data to validate
            schema_name: Name of the schema to use
            
        Returns:
            List of validation error messages
        """
        if schema_name not in self.schemas:
            return [f"Schema not found: {schema_name}"]
        
        schema = self.schemas[schema_name]
        errors = []
        
        try:
            validate(instance=strategy_data, schema=schema)
        except ValidationError as e:
            for error in e.context:
                error_msg = f"{error.message}"
                if error.path:
                    error_msg += f" at path: {' -> '.join(str(p) for p in error.path)}"
                errors.append(error_msg)
        
        return errors
    
    def validate_schema(self, schema_data: Dict[str, Any]) -> bool:
        """
        Validate schema itself
        
        Args:
            schema_data: Schema data to validate
            
        Returns:
            True if valid, raises SchemaError if invalid
        """
        try:
            validator_for(schema_data)
            self.logger.info("Schema validation passed")
            return True
        except SchemaError as e:
            error_msg = f"Schema validation failed: {e.message}"
            self.logger.error(error_msg)
            raise StrategyValidationError(error_msg) from e
    
    def get_schema(self, schema_name: str) -> Optional[Dict[str, Any]]:
        """
        Get schema by name
        
        Args:
            schema_name: Name of the schema
            
        Returns:
            Schema data or None if not found
        """
        return self.schemas.get(schema_name)
    
    def list_schemas(self) -> List[str]:
        """
        List all available schemas
        
        Returns:
            List of schema names
        """
        return list(self.schemas.keys())
    
    def add_schema(self, schema_name: str, schema_data: Dict[str, Any]):
        """
        Add a new schema
        
        Args:
            schema_name: Name of the schema
            schema_data: Schema data
        """
        # Validate the schema first
        self.validate_schema(schema_data)
        
        self.schemas[schema_name] = schema_data
        self.logger.info(f"Added schema: {schema_name}")
    
    def remove_schema(self, schema_name: str):
        """
        Remove a schema
        
        Args:
            schema_name: Name of the schema to remove
        """
        if schema_name in self.schemas:
            del self.schemas[schema_name]
            self.logger.info(f"Removed schema: {schema_name}")
        else:
            self.logger.warning(f"Schema not found: {schema_name}")
    
    def validate_strategy_type(self, strategy_data: Dict[str, Any]) -> str:
        """
        Validate and return strategy type
        
        Args:
            strategy_data: Strategy data
            
        Returns:
            Strategy type if valid
            
        Raises:
            StrategyValidationError: If strategy type is invalid
        """
        if 'strategy_type' not in strategy_data:
            raise StrategyValidationError("Strategy type is required")
        
        strategy_type = strategy_data['strategy_type']
        valid_types = ['momentum', 'pair_trading', 'mean_reversion', 'custom']
        
        if strategy_type not in valid_types:
            raise StrategyValidationError(f"Invalid strategy type: {strategy_type}")
        
        return strategy_type
    
    def validate_required_fields(self, strategy_data: Dict[str, Any]) -> List[str]:
        """
        Validate required fields are present
        
        Args:
            strategy_data: Strategy data
            
        Returns:
            List of missing required fields
        """
        required_fields = [
            'strategy_id',
            'strategy_name',
            'strategy_type',
            'signal_generation',
            'risk_management'
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in strategy_data:
                missing_fields.append(field)
        
        return missing_fields
