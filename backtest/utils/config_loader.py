"""
Config Loader Utilities
========================

Load and merge YAML configuration files.

Author: StatArb_Gemini Core Engine
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def load_config(config_path: str, base_config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load experiment configuration from YAML file.
    
    Args:
        config_path: Path to primary config file
        base_config_path: Optional path to base config (merged first)
        
    Returns:
        Merged configuration dictionary
    """
    config = {}
    
    # Load base config if provided
    if base_config_path:
        base_path = Path(base_config_path)
        if base_path.exists():
            with open(base_path, 'r') as f:
                config = yaml.safe_load(f) or {}
            logger.info(f"Loaded base config: {base_config_path}")
        else:
            logger.warning(f"Base config not found: {base_config_path}")
    
    # Load primary config
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_file, 'r') as f:
        primary_config = yaml.safe_load(f) or {}
    
    # Merge configs (primary overrides base)
    config = _deep_merge(config, primary_config)
    
    logger.info(f"Loaded config: {config_path}")
    return config


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries.
    
    Args:
        base: Base dictionary
        override: Override dictionary (takes precedence)
        
    Returns:
        Merged dictionary
    """
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def save_config(config: Dict[str, Any], output_path: str):
    """
    Save configuration to YAML file.
    
    Args:
        config: Configuration dictionary
        output_path: Output file path
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    logger.info(f"Saved config: {output_path}")

