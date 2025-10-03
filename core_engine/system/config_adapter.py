#!/usr/bin/env python3
"""
Configuration Adapter - Handle Configuration Format Differences
==============================================================

Adapter to handle configuration format differences between components
that expect configuration objects vs. dictionaries.

Author: StatArb_Gemini System Integration Team
Version: 1.0.0 (Configuration Compatibility)
"""

from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class GenericConfig:
    """Generic configuration that can be created from any dictionary"""
    
    def __init__(self, **kwargs):
        # Set all provided kwargs as attributes
        for key, value in kwargs.items():
            setattr(self, key, value)
        
        # Set comprehensive defaults if not provided
        defaults = {
            'enable_caching': True,
            'output_directory': './output',
            'use_normalization': True,
            'lag_periods': 5,
            'enable_scaling': True,
            'feature_selection': True,
            'calculation_threads': 2,
            'enable_attribution_analysis': True,
            'mode': 'backtest',
            'enable_performance_tracking': True,
            'auto_discovery_enabled': True,
            'cache_enabled': True,
            'registry_path': './registry',
            'enable_validation': True,
            'mean_reversion_weight': 0.4,
            'momentum_weight': 0.4,
            'volume_weight': 0.2,
            'signal_threshold': 0.5,
            'lookback_window': 30,
            'volatility_window': 10,
            'trend_threshold': 0.01,
            'regime_change_threshold': 0.05,
            'enable_enhanced_detection': True,
            'twap_duration_minutes': 30,
            'vwap_participation_rate': 0.1,
            'max_concurrent_strategies': 5,
            'min_confidence_threshold': 0.6
        }
        
        for key, default_value in defaults.items():
            if not hasattr(self, key):
                setattr(self, key, default_value)


def adapt_config(config_dict: Dict[str, Any]) -> GenericConfig:
    """Adapt a configuration dictionary to a configuration object"""
    if isinstance(config_dict, dict):
        return GenericConfig(**config_dict)
    else:
        # Already a config object
        return config_dict


def safe_component_init(component_class, config_dict: Dict[str, Any]):
    """Safely initialize a component with configuration adaptation"""
    try:
        # First try with the original config
        return component_class(config_dict)
    except (AttributeError, TypeError) as e:
        if "'dict' object has no attribute" in str(e) or "unexpected keyword argument" in str(e):
            # Try with adapted config
            try:
                adapted_config = adapt_config(config_dict)
                return component_class(adapted_config)
            except Exception as e2:
                # Try with None (many components accept None and use defaults)
                try:
                    return component_class(None)
                except Exception as e3:
                    # Try with empty config
                    try:
                        return component_class({})
                    except Exception as e4:
                        # Last resort - try with GenericConfig
                        return component_class(GenericConfig())
        else:
            raise e
