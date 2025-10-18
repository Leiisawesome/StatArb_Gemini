"""
Configuration Store

Provides persistent storage for strategy parameters with JSON backend.

Features:
- Save/load parameters to/from JSON files
- Version control
- Configuration listing
- Validation
"""

import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import os


logger = logging.getLogger(__name__)


class ConfigurationStore:
    """
    Persistent storage for strategy parameters.
    
    Storage Structure:
    backtest/config/strategy_params/
        {strategy_type}/
            default.json          # Default parameters
            {symbol}.json         # Symbol-specific parameters
            versions/
                default_v1.json   # Version history
                {symbol}_v1.json
    """
    
    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize configuration store.
        
        Args:
            base_path: Base path for parameter storage
                      (default: backtest/config/strategy_params/)
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        if base_path is None:
            # Default to backtest/config/strategy_params/
            base_path = "backtest/config/strategy_params"
        
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"ConfigurationStore initialized at {self.base_path}")
    
    def save_parameters(
        self,
        strategy_type: str,
        parameters: Dict[str, Any],
        symbol: Optional[str] = None,
        save_version: bool = True
    ) -> bool:
        """
        Save parameters to persistent storage.
        
        Args:
            strategy_type: Strategy type
            parameters: Parameters to save
            symbol: Optional symbol (None = default)
            save_version: Whether to save version history
        
        Returns:
            True if save successful
        """
        try:
            # Create strategy directory
            strategy_path = self.base_path / strategy_type
            strategy_path.mkdir(parents=True, exist_ok=True)
            
            # Determine filename
            if symbol is None:
                filename = "default.json"
            else:
                filename = f"{symbol}.json"
            
            file_path = strategy_path / filename
            
            # Save version history if requested
            if save_version and file_path.exists():
                self._save_version(strategy_type, symbol, file_path)
            
            # Prepare data with metadata
            data = {
                'strategy_type': strategy_type,
                'symbol': symbol,
                'parameters': parameters,
                'saved_at': datetime.now().isoformat(),
                'version': self._get_next_version(strategy_type, symbol)
            }
            
            # Save to JSON
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            symbol_str = symbol if symbol else "default"
            self.logger.info(f"Saved {strategy_type}:{symbol_str} parameters to {file_path}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save parameters: {e}")
            return False
    
    def load_parameters(
        self,
        strategy_type: str,
        symbol: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Load parameters from persistent storage.
        
        Args:
            strategy_type: Strategy type
            symbol: Optional symbol (None = default)
        
        Returns:
            Parameters dictionary or None if not found
        """
        try:
            # Determine file path
            strategy_path = self.base_path / strategy_type
            
            if symbol is None:
                file_path = strategy_path / "default.json"
            else:
                file_path = strategy_path / f"{symbol}.json"
            
            # Check if file exists
            if not file_path.exists():
                symbol_str = symbol if symbol else "default"
                self.logger.warning(f"No parameters found for {strategy_type}:{symbol_str}")
                return None
            
            # Load from JSON
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Validate data
            if 'parameters' not in data:
                self.logger.error(f"Invalid parameter file: {file_path}")
                return None
            
            symbol_str = symbol if symbol else "default"
            self.logger.info(f"Loaded {strategy_type}:{symbol_str} parameters from {file_path}")
            
            return data['parameters']
            
        except Exception as e:
            self.logger.error(f"Failed to load parameters: {e}")
            return None
    
    def list_configurations(self, strategy_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List available configurations.
        
        Args:
            strategy_type: Optional strategy type filter
        
        Returns:
            List of configuration metadata
        """
        configs = []
        
        try:
            # Get strategy directories
            if strategy_type:
                strategy_dirs = [self.base_path / strategy_type]
            else:
                strategy_dirs = [d for d in self.base_path.iterdir() if d.is_dir()]
            
            for strategy_dir in strategy_dirs:
                if not strategy_dir.is_dir():
                    continue
                
                strategy_name = strategy_dir.name
                
                # Skip versions directory
                if strategy_name == "versions":
                    continue
                
                # List all JSON files
                for json_file in strategy_dir.glob("*.json"):
                    # Parse filename
                    if json_file.name == "default.json":
                        symbol = None
                    else:
                        symbol = json_file.stem
                    
                    # Get file stats
                    stat = json_file.stat()
                    
                    configs.append({
                        'strategy_type': strategy_name,
                        'symbol': symbol,
                        'file_path': str(json_file),
                        'size_bytes': stat.st_size,
                        'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
            
            return configs
            
        except Exception as e:
            self.logger.error(f"Failed to list configurations: {e}")
            return []
    
    def delete_configuration(self, strategy_type: str, symbol: Optional[str] = None) -> bool:
        """
        Delete a configuration.
        
        Args:
            strategy_type: Strategy type
            symbol: Optional symbol (None = default)
        
        Returns:
            True if deletion successful
        """
        try:
            # Determine file path
            strategy_path = self.base_path / strategy_type
            
            if symbol is None:
                file_path = strategy_path / "default.json"
            else:
                file_path = strategy_path / f"{symbol}.json"
            
            # Check if file exists
            if not file_path.exists():
                symbol_str = symbol if symbol else "default"
                self.logger.warning(f"No configuration found for {strategy_type}:{symbol_str}")
                return False
            
            # Delete file
            file_path.unlink()
            
            symbol_str = symbol if symbol else "default"
            self.logger.info(f"Deleted {strategy_type}:{symbol_str} configuration")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete configuration: {e}")
            return False
    
    def _save_version(
        self,
        strategy_type: str,
        symbol: Optional[str],
        current_file_path: Path
    ) -> None:
        """
        Save current version to history.
        
        Args:
            strategy_type: Strategy type
            symbol: Symbol (None for default)
            current_file_path: Path to current file
        """
        try:
            # Create versions directory
            versions_dir = self.base_path / strategy_type / "versions"
            versions_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate version filename
            version = self._get_next_version(strategy_type, symbol)
            
            if symbol is None:
                version_filename = f"default_v{version}.json"
            else:
                version_filename = f"{symbol}_v{version}.json"
            
            version_path = versions_dir / version_filename
            
            # Copy current file to version history
            with open(current_file_path, 'r') as src:
                data = json.load(src)
            
            with open(version_path, 'w') as dst:
                json.dump(data, dst, indent=2)
            
            self.logger.info(f"Saved version {version} to {version_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save version: {e}")
    
    def _get_next_version(self, strategy_type: str, symbol: Optional[str]) -> int:
        """
        Get next version number.
        
        Args:
            strategy_type: Strategy type
            symbol: Symbol (None for default)
        
        Returns:
            Next version number
        """
        try:
            versions_dir = self.base_path / strategy_type / "versions"
            
            if not versions_dir.exists():
                return 1
            
            # Find existing versions
            if symbol is None:
                pattern = "default_v*.json"
            else:
                pattern = f"{symbol}_v*.json"
            
            version_files = list(versions_dir.glob(pattern))
            
            if not version_files:
                return 1
            
            # Extract version numbers
            versions = []
            for vf in version_files:
                try:
                    # Extract number from filename like "default_v3.json"
                    version_str = vf.stem.split('_v')[1]
                    versions.append(int(version_str))
                except (IndexError, ValueError):
                    continue
            
            if not versions:
                return 1
            
            return max(versions) + 1
            
        except Exception as e:
            self.logger.error(f"Failed to get next version: {e}")
            return 1
    
    def validate_storage_path(self) -> bool:
        """
        Validate storage path is accessible.
        
        Returns:
            True if path is valid and writable
        """
        try:
            # Check if path exists
            if not self.base_path.exists():
                self.logger.error(f"Storage path does not exist: {self.base_path}")
                return False
            
            # Check if writable
            test_file = self.base_path / ".write_test"
            test_file.touch()
            test_file.unlink()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Storage path validation failed: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get store status.
        
        Returns:
            Status dictionary
        """
        try:
            configs = self.list_configurations()
            
            total_configs = len(configs)
            strategies = set(c['strategy_type'] for c in configs)
            total_size = sum(c['size_bytes'] for c in configs)
            
            return {
                'base_path': str(self.base_path),
                'total_configurations': total_configs,
                'total_strategies': len(strategies),
                'total_size_kb': total_size / 1024,
                'is_valid': self.validate_storage_path()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get status: {e}")
            return {
                'base_path': str(self.base_path),
                'error': str(e)
            }

