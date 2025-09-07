#!/usr/bin/env python3
"""
Unified Strategy Registry - Consolidated Strategy Registration and Discovery
==========================================================================

Consolidates strategy registration functionality from multiple systems:
- Enhanced strategy factory (from interfaces)
- Template registry (from trade_engine/templates)
- Auto-discovery and registration
- Strategy lifecycle management

This module provides unified strategy registration, discovery, and management
across all strategy types and implementations.

Author: Professional Trading System Architecture
Version: 2.0.0 (Unified)
"""

import logging
import importlib
import inspect
from typing import Dict, List, Optional, Type, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json

# Import base types
from ..interfaces.strategy_interfaces import StrategyType, StrategyError
from .unified_strategy_system import EnhancedBaseStrategy, TemplateBasedStrategy, UnifiedStrategyConfig

logger = logging.getLogger(__name__)

# ================================================================================
# REGISTRY DATA CLASSES
# ================================================================================

@dataclass
class StrategyRegistration:
    """Strategy registration information"""
    strategy_type: StrategyType
    strategy_class: Type[EnhancedBaseStrategy]
    
    # Registration metadata
    name: str
    description: str = ""
    version: str = "1.0.0"
    author: str = ""
    
    # Template information (if applicable)
    is_template_based: bool = False
    template_name: Optional[str] = None
    template_config: Dict[str, Any] = field(default_factory=dict)
    
    # Registration details
    registered_at: datetime = field(default_factory=datetime.now)
    module_path: str = ""
    
    # Capabilities
    supported_modes: List[str] = field(default_factory=lambda: ["backtest", "live"])
    required_indicators: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'strategy_type': self.strategy_type.value if isinstance(self.strategy_type, StrategyType) else self.strategy_type,
            'strategy_class': self.strategy_class.__name__,
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'author': self.author,
            'is_template_based': self.is_template_based,
            'template_name': self.template_name,
            'template_config': self.template_config,
            'registered_at': self.registered_at.isoformat(),
            'module_path': self.module_path,
            'supported_modes': self.supported_modes,
            'required_indicators': self.required_indicators
        }

# ================================================================================
# UNIFIED STRATEGY REGISTRY
# ================================================================================

class UnifiedStrategyRegistry:
    """
    Unified strategy registry consolidating all strategy registration functionality.
    
    Features:
    - Unified strategy registration and discovery
    - Template-based strategy support
    - Auto-discovery from multiple locations
    - Strategy lifecycle management
    - Enhanced metadata and capabilities tracking
    """
    
    def __init__(self):
        # Main registry
        self._registry: Dict[StrategyType, StrategyRegistration] = {}
        self._name_to_type: Dict[str, StrategyType] = {}
        
        # Template registry (consolidated from trade_engine/templates)
        self._template_registry: Dict[str, Dict[str, Any]] = {}
        
        # Discovery paths
        self._discovery_paths = [
            "core_structure.strategies",
            "trade_engine.strategies",  # Legacy support
        ]
        
        # Statistics
        self._registration_stats = {
            'total_registered': 0,
            'template_based': 0,
            'auto_discovered': 0,
            'manual_registered': 0,
            'last_discovery': None
        }
        
        logger.info("Unified strategy registry initialized")
    
    def register_strategy(self, 
                         strategy_type: StrategyType,
                         strategy_class: Type[EnhancedBaseStrategy],
                         name: Optional[str] = None,
                         description: str = "",
                         version: str = "1.0.0",
                         author: str = "",
                         template_config: Optional[Dict[str, Any]] = None) -> bool:
        """Register a strategy in the unified registry"""
        
        try:
            # Validate strategy class
            if not issubclass(strategy_class, EnhancedBaseStrategy):
                raise ValueError(f"Strategy class must inherit from EnhancedBaseStrategy")
            
            # Generate name if not provided
            if name is None:
                name = strategy_class.__name__
            
            # Check for existing registration
            if strategy_type in self._registry:
                logger.warning(f"Overwriting existing strategy registration: {strategy_type.value}")
            
            # Create registration
            registration = StrategyRegistration(
                strategy_type=strategy_type,
                strategy_class=strategy_class,
                name=name,
                description=description,
                version=version,
                author=author,
                is_template_based=template_config is not None,
                template_config=template_config or {},
                module_path=strategy_class.__module__
            )
            
            # Extract additional metadata from class
            self._extract_strategy_metadata(registration, strategy_class)
            
            # Register
            self._registry[strategy_type] = registration
            self._name_to_type[name.lower()] = strategy_type
            
            # Update statistics
            self._registration_stats['total_registered'] += 1
            self._registration_stats['manual_registered'] += 1
            if template_config:
                self._registration_stats['template_based'] += 1
            
            logger.info(f"Strategy registered: {name} ({strategy_type.value})")
            return True
            
        except Exception as e:
            logger.error(f"Strategy registration failed: {e}")
            return False
    
    def _extract_strategy_metadata(self, registration: StrategyRegistration, strategy_class: Type[EnhancedBaseStrategy]):
        """Extract metadata from strategy class"""
        try:
            # Extract docstring description if not provided
            if not registration.description and strategy_class.__doc__:
                registration.description = strategy_class.__doc__.strip().split('\n')[0]
            
            # Extract required indicators if method exists
            if hasattr(strategy_class, 'required_indicators'):
                try:
                    # Try to get as property or call as method
                    if isinstance(strategy_class.required_indicators, property):
                        # Can't easily get property value without instance
                        pass
                    else:
                        # Try to call as class method
                        indicators = strategy_class.required_indicators
                        if callable(indicators):
                            registration.required_indicators = indicators()
                        else:
                            registration.required_indicators = indicators
                except:
                    pass
            
            # Extract supported modes from class attributes
            if hasattr(strategy_class, 'SUPPORTED_MODES'):
                registration.supported_modes = strategy_class.SUPPORTED_MODES
            
        except Exception as e:
            logger.debug(f"Metadata extraction failed for {strategy_class.__name__}: {e}")
    
    def get_strategy_class(self, strategy_type: StrategyType) -> Optional[Type[EnhancedBaseStrategy]]:
        """Get strategy class by type"""
        registration = self._registry.get(strategy_type)
        return registration.strategy_class if registration else None
    
    def get_strategy_by_name(self, name: str) -> Optional[Type[EnhancedBaseStrategy]]:
        """Get strategy class by name"""
        strategy_type = self._name_to_type.get(name.lower())
        return self.get_strategy_class(strategy_type) if strategy_type else None
    
    def create_strategy_instance(self, 
                                strategy_type: StrategyType,
                                strategy_id: str,
                                config: UnifiedStrategyConfig) -> Optional[EnhancedBaseStrategy]:
        """Create strategy instance from registry"""
        try:
            registration = self._registry.get(strategy_type)
            if not registration:
                raise ValueError(f"Strategy type not registered: {strategy_type}")
            
            strategy_class = registration.strategy_class
            
            # Create instance based on type
            if registration.is_template_based:
                # Create template-based strategy
                if issubclass(strategy_class, TemplateBasedStrategy):
                    return strategy_class(strategy_id, config, registration.template_config)
                else:
                    # Wrap in template-based strategy
                    return TemplateBasedStrategy(strategy_id, config, registration.template_config)
            else:
                # Create regular strategy
                return strategy_class(strategy_id, config)
                
        except Exception as e:
            logger.error(f"Strategy instance creation failed: {e}")
            return None
    
    def get_available_strategies(self) -> List[StrategyType]:
        """Get list of all registered strategy types"""
        return list(self._registry.keys())
    
    def get_strategy_info(self, strategy_type: StrategyType) -> Optional[Dict[str, Any]]:
        """Get detailed information about a strategy"""
        registration = self._registry.get(strategy_type)
        return registration.to_dict() if registration else None
    
    def get_all_strategies_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all registered strategies"""
        return {
            strategy_type.value: registration.to_dict()
            for strategy_type, registration in self._registry.items()
        }
    
    def auto_discover_strategies(self) -> int:
        """Auto-discover strategies from configured paths"""
        discovered_count = 0
        
        try:
            self._registration_stats['last_discovery'] = datetime.now()
            
            for path in self._discovery_paths:
                discovered_count += self._discover_from_path(path)
            
            self._registration_stats['auto_discovered'] += discovered_count
            
            logger.info(f"Auto-discovery completed: {discovered_count} strategies found")
            
        except Exception as e:
            logger.error(f"Auto-discovery failed: {e}")
        
        return discovered_count
    
    def _discover_from_path(self, module_path: str) -> int:
        """Discover strategies from a specific module path"""
        discovered = 0
        
        try:
            # Try to import the module
            try:
                module = importlib.import_module(module_path)
            except ImportError:
                logger.debug(f"Module not found for discovery: {module_path}")
                return 0
            
            # Look for strategy classes
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, EnhancedBaseStrategy) and 
                    obj != EnhancedBaseStrategy and
                    obj != TemplateBasedStrategy):
                    
                    # Try to determine strategy type
                    strategy_type = self._infer_strategy_type(obj, name)
                    
                    if strategy_type and strategy_type not in self._registry:
                        # Auto-register
                        if self.register_strategy(
                            strategy_type=strategy_type,
                            strategy_class=obj,
                            name=name,
                            description=f"Auto-discovered from {module_path}"
                        ):
                            discovered += 1
            
        except Exception as e:
            logger.debug(f"Discovery failed for path {module_path}: {e}")
        
        return discovered
    
    def _infer_strategy_type(self, strategy_class: Type, class_name: str) -> Optional[StrategyType]:
        """Infer strategy type from class"""
        try:
            # Try to get strategy_type property/attribute
            if hasattr(strategy_class, 'strategy_type'):
                strategy_type = strategy_class.strategy_type
                if isinstance(strategy_type, StrategyType):
                    return strategy_type
            
            # Infer from class name
            name_lower = class_name.lower()
            
            if 'momentum' in name_lower:
                return StrategyType.MOMENTUM
            elif 'mean_reversion' in name_lower or 'meanreversion' in name_lower:
                return StrategyType.MEAN_REVERSION
            elif 'pairs' in name_lower or 'pair' in name_lower:
                return StrategyType.PAIRS_TRADING
            elif 'arbitrage' in name_lower:
                return StrategyType.ARBITRAGE
            elif 'custom' in name_lower:
                return StrategyType.CUSTOM
            
            # Default to custom if can't determine
            return StrategyType.CUSTOM
            
        except Exception as e:
            logger.debug(f"Strategy type inference failed for {class_name}: {e}")
            return None
    
    def register_template(self, template_name: str, template_config: Dict[str, Any]) -> bool:
        """Register a strategy template"""
        try:
            self._template_registry[template_name] = {
                'config': template_config,
                'registered_at': datetime.now().isoformat(),
                'version': template_config.get('version', '1.0.0')
            }
            
            logger.info(f"Template registered: {template_name}")
            return True
            
        except Exception as e:
            logger.error(f"Template registration failed: {e}")
            return False
    
    def get_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Get template configuration"""
        return self._template_registry.get(template_name)
    
    def get_available_templates(self) -> List[str]:
        """Get list of available templates"""
        return list(self._template_registry.keys())
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        return {
            **self._registration_stats,
            'registered_strategies': len(self._registry),
            'registered_templates': len(self._template_registry),
            'strategy_types': [st.value for st in self._registry.keys()],
            'template_names': list(self._template_registry.keys())
        }
    
    def clear_registry(self) -> None:
        """Clear all registrations (for testing)"""
        self._registry.clear()
        self._name_to_type.clear()
        self._template_registry.clear()
        self._registration_stats = {
            'total_registered': 0,
            'template_based': 0,
            'auto_discovered': 0,
            'manual_registered': 0,
            'last_discovery': None
        }
        logger.info("Registry cleared")

# ================================================================================
# GLOBAL REGISTRY INSTANCE AND CONVENIENCE FUNCTIONS
# ================================================================================

# Global unified strategy registry
unified_strategy_registry = UnifiedStrategyRegistry()

def register_strategy(strategy_type: StrategyType, 
                     strategy_class: Type[EnhancedBaseStrategy],
                     **kwargs) -> bool:
    """Convenience function for strategy registration"""
    return unified_strategy_registry.register_strategy(strategy_type, strategy_class, **kwargs)

def get_strategy_class(strategy_type: StrategyType) -> Optional[Type[EnhancedBaseStrategy]]:
    """Convenience function to get strategy class"""
    return unified_strategy_registry.get_strategy_class(strategy_type)

def create_strategy_instance(strategy_type: StrategyType,
                           strategy_id: str,
                           config: UnifiedStrategyConfig) -> Optional[EnhancedBaseStrategy]:
    """Convenience function to create strategy instance"""
    return unified_strategy_registry.create_strategy_instance(strategy_type, strategy_id, config)

def get_available_strategies() -> List[StrategyType]:
    """Convenience function to get available strategies"""
    return unified_strategy_registry.get_available_strategies()

def auto_discover_strategies() -> int:
    """Convenience function for auto-discovery"""
    return unified_strategy_registry.auto_discover_strategies()

def get_registry_info() -> Dict[str, Any]:
    """Convenience function to get registry information"""
    return unified_strategy_registry.get_registry_stats()

# ================================================================================
# INITIALIZATION
# ================================================================================

def _initialize_registry():
    """Initialize the registry with auto-discovery"""
    try:
        discovered = unified_strategy_registry.auto_discover_strategies()
        logger.info(f"Strategy registry initialized with {discovered} auto-discovered strategies")
        return discovered
    except Exception as e:
        logger.error(f"Registry initialization failed: {e}")
        return 0

# Auto-initialize on module import
_discovered_strategies = _initialize_registry()

logger.info("Unified Strategy Registry loaded successfully - Strategy registration consolidated")
