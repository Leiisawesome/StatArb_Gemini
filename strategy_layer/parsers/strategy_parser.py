"""
Strategy Parser for JSON Strategy Definitions

Main parser for loading, validating, and parsing JSON strategy definitions
into executable strategy objects.

Author: Pro Quant Desk Trader
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from strategy_layer.base import StrategyConfig, StrategyError, StrategyValidationError
from .schema_validator import SchemaValidator


class StrategyParser:
    """Main strategy parser for JSON strategy definitions"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = config or {}
        self.schema_validator = SchemaValidator()
        self._cache = {}
        self._cache_enabled = self.config.get('cache_enabled', True)
        self._cache_ttl = self.config.get('cache_ttl_seconds', 3600)
    
    def parse_strategy_file(self, file_path: str, validate: bool = True) -> Dict[str, Any]:
        """
        Parse strategy from JSON file
        
        Args:
            file_path: Path to the strategy JSON file
            validate: Whether to validate against schema
            
        Returns:
            Parsed strategy data
            
        Raises:
            StrategyValidationError: If validation fails
            StrategyError: If parsing fails
        """
        try:
            # Check cache first
            if self._cache_enabled and file_path in self._cache:
                cached_data = self._cache[file_path]
                if self._is_cache_valid(cached_data):
                    self.logger.info(f"Using cached strategy data for: {file_path}")
                    return cached_data['data']
            
            # Load and parse JSON file
            self.logger.info(f"Parsing strategy file: {file_path}")
            
            if not os.path.exists(file_path):
                raise StrategyError(f"Strategy file not found: {file_path}")
            
            # Validate file extension
            if not self._validate_file_extension(file_path):
                raise StrategyError(f"Invalid file extension for strategy file: {file_path}")
            
            # Check file size
            if not self._validate_file_size(file_path):
                raise StrategyError(f"Strategy file too large: {file_path}")
            
            # Load JSON data
            with open(file_path, 'r', encoding='utf-8') as f:
                strategy_data = json.load(f)
            
            # Validate against schema if requested (using automatic schema selection)
            if validate:
                self.schema_validator.validate_strategy_with_auto_schema(strategy_data)
            
            # Add metadata
            strategy_data = self._add_parsing_metadata(strategy_data, file_path)
            
            # Cache the result
            if self._cache_enabled:
                self._cache[file_path] = {
                    'data': strategy_data,
                    'timestamp': datetime.now(),
                    'file_path': file_path
                }
            
            self.logger.info(f"Successfully parsed strategy file: {file_path}")
            return strategy_data
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in strategy file {file_path}: {e}"
            self.logger.error(error_msg)
            raise StrategyError(error_msg) from e
        except Exception as e:
            error_msg = f"Failed to parse strategy file {file_path}: {e}"
            self.logger.error(error_msg)
            raise StrategyError(error_msg) from e
    
    def parse_strategy_data(self, strategy_data: Dict[str, Any], validate: bool = True) -> Dict[str, Any]:
        """
        Parse strategy from dictionary data
        
        Args:
            strategy_data: Strategy data dictionary
            validate: Whether to validate against schema
            
        Returns:
            Parsed strategy data
            
        Raises:
            StrategyValidationError: If validation fails
            StrategyError: If parsing fails
        """
        try:
            self.logger.info("Parsing strategy data")
            
            # Validate against schema if requested (using automatic schema selection)
            if validate:
                self.schema_validator.validate_strategy_with_auto_schema(strategy_data)
            
            # Add metadata
            strategy_data = self._add_parsing_metadata(strategy_data)
            
            self.logger.info("Successfully parsed strategy data")
            return strategy_data
            
        except Exception as e:
            error_msg = f"Failed to parse strategy data: {e}"
            self.logger.error(error_msg)
            raise StrategyError(error_msg) from e
    
    def parse_strategy_string(self, strategy_json: str, validate: bool = True) -> Dict[str, Any]:
        """
        Parse strategy from JSON string
        
        Args:
            strategy_json: JSON string containing strategy data
            validate: Whether to validate against schema
            
        Returns:
            Parsed strategy data
            
        Raises:
            StrategyValidationError: If validation fails
            StrategyError: If parsing fails
        """
        try:
            self.logger.info("Parsing strategy JSON string")
            
            # Parse JSON string
            strategy_data = json.loads(strategy_json)
            
            # Validate against schema if requested (using automatic schema selection)
            if validate:
                self.schema_validator.validate_strategy_with_auto_schema(strategy_data)
            
            # Add metadata
            strategy_data = self._add_parsing_metadata(strategy_data)
            
            self.logger.info("Successfully parsed strategy JSON string")
            return strategy_data
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON string: {e}"
            self.logger.error(error_msg)
            raise StrategyError(error_msg) from e
        except Exception as e:
            error_msg = f"Failed to parse strategy JSON string: {e}"
            self.logger.error(error_msg)
            raise StrategyError(error_msg) from e
    
    def parse_multiple_strategies(self, file_paths: List[str], validate: bool = True) -> Dict[str, Dict[str, Any]]:
        """
        Parse multiple strategy files
        
        Args:
            file_paths: List of strategy file paths
            validate: Whether to validate against schema
            
        Returns:
            Dictionary mapping file paths to parsed strategy data
            
        Raises:
            StrategyError: If any strategy fails to parse
        """
        results = {}
        errors = []
        
        for file_path in file_paths:
            try:
                strategy_data = self.parse_strategy_file(file_path, validate)
                results[file_path] = strategy_data
            except Exception as e:
                error_msg = f"Failed to parse {file_path}: {e}"
                errors.append(error_msg)
                self.logger.error(error_msg)
        
        if errors:
            raise StrategyError(f"Failed to parse some strategies: {'; '.join(errors)}")
        
        return results
    
    def parse_strategy_directory(self, directory_path: str, validate: bool = True) -> Dict[str, Dict[str, Any]]:
        """
        Parse all strategy files in a directory
        
        Args:
            directory_path: Path to directory containing strategy files
            validate: Whether to validate against schema
            
        Returns:
            Dictionary mapping file paths to parsed strategy data
        """
        strategy_files = []
        directory = Path(directory_path)
        
        if not directory.exists():
            raise StrategyError(f"Directory not found: {directory_path}")
        
        # Find all JSON files
        for file_path in directory.glob("*.json"):
            if self._validate_file_extension(str(file_path)):
                strategy_files.append(str(file_path))
        
        self.logger.info(f"Found {len(strategy_files)} strategy files in {directory_path}")
        
        return self.parse_multiple_strategies(strategy_files, validate)
    
    def _validate_file_extension(self, file_path: str) -> bool:
        """Validate file extension"""
        allowed_extensions = self.config.get('allowed_extensions', ['.json'])
        file_ext = Path(file_path).suffix.lower()
        return file_ext in allowed_extensions
    
    def _validate_file_size(self, file_path: str) -> bool:
        """Validate file size"""
        max_size_mb = self.config.get('max_file_size_mb', 10)
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        return file_size_mb <= max_size_mb
    
    def _add_parsing_metadata(self, strategy_data: Dict[str, Any], file_path: Optional[str] = None) -> Dict[str, Any]:
        """Add parsing metadata to strategy data"""
        metadata = strategy_data.get('metadata', {})
        
        # Add parsing metadata
        parsing_metadata = {
            'parsed_at': datetime.now().isoformat(),
            'parser_version': '1.0.0',
            'parsed_by': self.__class__.__name__
        }
        
        if file_path:
            parsing_metadata['source_file'] = file_path
        
        metadata['parsing'] = parsing_metadata
        strategy_data['metadata'] = metadata
        
        return strategy_data
    
    def _is_cache_valid(self, cached_data: Dict[str, Any]) -> bool:
        """Check if cached data is still valid"""
        if 'timestamp' not in cached_data:
            return False
        
        timestamp = cached_data['timestamp']
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        age_seconds = (datetime.now() - timestamp).total_seconds()
        return age_seconds < self._cache_ttl
    
    def clear_cache(self):
        """Clear the parser cache"""
        self._cache.clear()
        self.logger.info("Parser cache cleared")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache information"""
        return {
            'cache_enabled': self._cache_enabled,
            'cache_ttl_seconds': self._cache_ttl,
            'cached_files': len(self._cache),
            'cache_size_mb': sum(
                len(json.dumps(data['data'])) / (1024 * 1024) 
                for data in self._cache.values()
            )
        }
    
    def validate_strategy(self, strategy_data: Dict[str, Any]) -> bool:
        """
        Validate strategy data
        
        Args:
            strategy_data: Strategy data to validate
            
        Returns:
            True if valid
            
        Raises:
            StrategyValidationError: If validation fails
        """
        return self.schema_validator.validate_strategy(strategy_data)
    
    def get_validation_errors(self, strategy_data: Dict[str, Any]) -> List[str]:
        """
        Get validation errors for strategy data
        
        Args:
            strategy_data: Strategy data to validate
            
        Returns:
            List of validation error messages
        """
        return self.schema_validator.get_validation_errors(strategy_data)
    
    def validate_with_auto_schema(self, strategy_data: Dict[str, Any]) -> bool:
        """
        Validate strategy data with automatic schema selection
        
        Args:
            strategy_data: Strategy data to validate
            
        Returns:
            True if valid
            
        Raises:
            StrategyValidationError: If validation fails
        """
        return self.schema_validator.validate_strategy_with_auto_schema(strategy_data)
    
    def get_schema_for_strategy_type(self, strategy_type: str) -> Optional[Dict[str, Any]]:
        """
        Get the schema dictionary for a specific strategy type
        
        Args:
            strategy_type: Type of strategy
            
        Returns:
            Schema dictionary or None if not found
        """
        return self.schema_validator.get_schema_for_strategy_type(strategy_type)
    
    def get_available_strategy_types(self) -> List[str]:
        """
        Get list of available strategy types that have specific schemas
        
        Returns:
            List of strategy types with dedicated schemas
        """
        return self.schema_validator.get_available_strategy_types()
