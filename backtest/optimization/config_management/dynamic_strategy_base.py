"""
Dynamic Strategy Base

Provides base class for strategies with dynamic parameter loading from registry.

Features:
- Automatic parameter loading from registry
- Subscribe to parameter updates
- Safe parameter access with defaults
- Integration with CentralParameterRegistry
"""

import logging
from typing import Dict, Any, Optional, Callable
from core_engine.trading.strategies.base_strategy_enhanced import EnhancedBaseStrategy
from .parameter_registry import CentralParameterRegistry


logger = logging.getLogger(__name__)


class EnhancedBaseStrategyWithDynamicConfig(EnhancedBaseStrategy):
    """
    Enhanced base strategy with dynamic parameter loading.
    
    Extends EnhancedBaseStrategy to support dynamic parameter management
    through CentralParameterRegistry.
    
    Usage:
        class MyStrategy(EnhancedBaseStrategyWithDynamicConfig):
            def __init__(self, config, parameter_registry=None):
                super().__init__(config, parameter_registry)
                
            def generate_signals(self, data):
                # Parameters automatically loaded from registry
                threshold = self.get_parameter('threshold', default=0.5)
                ...
    """
    
    def __init__(
        self,
        config: Any,
        parameter_registry: Optional[CentralParameterRegistry] = None,
        symbol: Optional[str] = None
    ):
        """
        Initialize strategy with dynamic parameter loading.
        
        Args:
            config: Strategy configuration
            parameter_registry: Central parameter registry instance
            symbol: Optional symbol for symbol-specific parameters
        """
        super().__init__(config)
        
        self.logger = logging.getLogger(self.__class__.__name__)
        self.parameter_registry = parameter_registry
        self.symbol = symbol
        self._dynamic_parameters: Dict[str, Any] = {}
        self._subscription_active = False
        
        # Load parameters if registry provided
        if self.parameter_registry:
            self._load_parameters()
            self._subscribe_to_updates()
    
    def set_parameter_registry(
        self,
        parameter_registry: CentralParameterRegistry,
        symbol: Optional[str] = None
    ) -> None:
        """
        Set parameter registry and load parameters.
        
        Args:
            parameter_registry: Central parameter registry
            symbol: Optional symbol for symbol-specific parameters
        """
        self.parameter_registry = parameter_registry
        self.symbol = symbol
        
        # Load parameters
        self._load_parameters()
        
        # Subscribe to updates
        self._subscribe_to_updates()
    
    def _load_parameters(self) -> None:
        """Load parameters from registry"""
        if not self.parameter_registry:
            return
        
        try:
            strategy_type = self.config.strategy_type.value
            params = self.parameter_registry.get_parameters(strategy_type, self.symbol)
            
            if params:
                self._dynamic_parameters = params
                symbol_str = self.symbol if self.symbol else "default"
                self.logger.info(
                    f"Loaded {len(params)} parameters for {strategy_type}:{symbol_str}"
                )
            else:
                self.logger.warning(f"No parameters found in registry for {strategy_type}")
                
        except Exception as e:
            self.logger.error(f"Failed to load parameters: {e}")
    
    def _subscribe_to_updates(self) -> None:
        """Subscribe to parameter updates"""
        if not self.parameter_registry or self._subscription_active:
            return
        
        try:
            strategy_type = self.config.strategy_type.value
            self.parameter_registry.subscribe(
                strategy_type,
                self._on_parameters_updated
            )
            self._subscription_active = True
            self.logger.info(f"Subscribed to parameter updates for {strategy_type}")
            
        except Exception as e:
            self.logger.error(f"Failed to subscribe to updates: {e}")
    
    def _on_parameters_updated(
        self,
        strategy_type: str,
        symbol: Optional[str],
        parameters: Dict[str, Any]
    ) -> None:
        """
        Callback for parameter updates.
        
        Args:
            strategy_type: Strategy type
            symbol: Symbol (None for default)
            parameters: Updated parameters
        """
        # Only update if this is for our symbol (or default)
        if symbol != self.symbol and symbol is not None:
            return
        
        try:
            self._dynamic_parameters = parameters
            symbol_str = symbol if symbol else "default"
            self.logger.info(
                f"Parameters updated for {strategy_type}:{symbol_str} "
                f"({len(parameters)} parameters)"
            )
            
            # Call custom handler if implemented
            self.on_parameters_changed(parameters)
            
        except Exception as e:
            self.logger.error(f"Failed to process parameter update: {e}")
    
    def get_parameter(self, key: str, default: Any = None) -> Any:
        """
        Get parameter value with fallback to default.
        
        Args:
            key: Parameter key
            default: Default value if not found
        
        Returns:
            Parameter value or default
        """
        # Try dynamic parameters first
        if key in self._dynamic_parameters:
            return self._dynamic_parameters[key]
        
        # Fallback to config
        if hasattr(self.config, key):
            return getattr(self.config, key)
        
        # Return default
        return default
    
    def on_parameters_changed(self, parameters: Dict[str, Any]) -> None:
        """
        Hook for custom parameter change handling.
        
        Override this method in subclasses to handle parameter changes.
        
        Args:
            parameters: Updated parameters
        """
        # Default implementation does nothing
        # Subclasses can override to implement custom logic
        pass
    
    def get_all_parameters(self) -> Dict[str, Any]:
        """
        Get all current parameters.
        
        Returns:
            Dictionary of all parameters (dynamic + config)
        """
        # Start with config parameters
        all_params = {}
        for attr in dir(self.config):
            if not attr.startswith('_') and not callable(getattr(self.config, attr)):
                all_params[attr] = getattr(self.config, attr)
        
        # Override with dynamic parameters
        all_params.update(self._dynamic_parameters)
        
        return all_params
    
    def validate_parameters(self) -> bool:
        """
        Validate current parameters.
        
        Returns:
            True if parameters are valid
        """
        # Basic validation
        if not self._dynamic_parameters and not self.parameter_registry:
            self.logger.warning("No parameters loaded and no registry configured")
            return False
        
        # Strategy-specific validation can be implemented by subclasses
        return True
    
    def get_parameter_source(self, key: str) -> str:
        """
        Get source of parameter value.
        
        Args:
            key: Parameter key
        
        Returns:
            Source: 'dynamic', 'config', or 'not_found'
        """
        if key in self._dynamic_parameters:
            return 'dynamic'
        elif hasattr(self.config, key):
            return 'config'
        else:
            return 'not_found'

