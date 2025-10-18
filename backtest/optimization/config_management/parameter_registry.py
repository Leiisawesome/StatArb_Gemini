"""
Central Parameter Registry

Provides centralized parameter management with pub/sub notifications for strategy optimization.

Features:
- Subscribe/unsubscribe to parameter updates
- Get/update parameters with symbol-specific overrides
- Parameter versioning and history
- Rollback capability
- Validation framework
"""

import logging
from typing import Dict, Any, List, Callable, Optional, Tuple
from datetime import datetime
import copy
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)


@dataclass
class ParameterVersion:
    """Parameter version with metadata"""
    version: int
    parameters: Dict[str, Any]
    timestamp: datetime
    changed_by: str
    change_reason: Optional[str] = None


class CentralParameterRegistry:
    """
    Central registry for strategy parameters with pub/sub pattern.
    
    Manages parameters with symbol-specific overrides and notifies subscribers
    of parameter changes.
    
    Architecture:
    - Strategy-level default parameters
    - Symbol-specific parameter overrides
    - Version history for rollback
    - Pub/sub notifications for changes
    """
    
    def __init__(self):
        """Initialize the parameter registry"""
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Parameter storage: {strategy_type: {symbol: parameters}}
        # None symbol key = default parameters
        self._parameters: Dict[str, Dict[Optional[str], Dict[str, Any]]] = {}
        
        # Subscribers: {strategy_type: [callback_functions]}
        self._subscribers: Dict[str, List[Callable]] = {}
        
        # Parameter history: {strategy_type: {symbol: [versions]}}
        self._history: Dict[str, Dict[Optional[str], List[ParameterVersion]]] = {}
        
        # Version counters: {strategy_type: {symbol: version_number}}
        self._version_counters: Dict[str, Dict[Optional[str], int]] = {}
        
        self.logger.info("CentralParameterRegistry initialized")
    
    def subscribe(self, strategy_type: str, callback: Callable[[str, Optional[str], Dict[str, Any]], None]) -> str:
        """
        Subscribe to parameter updates for a strategy.
        
        Args:
            strategy_type: Strategy type to subscribe to
            callback: Function to call on parameter updates
                     Signature: callback(strategy_type, symbol, parameters)
        
        Returns:
            Subscription ID for unsubscribing
        """
        if strategy_type not in self._subscribers:
            self._subscribers[strategy_type] = []
        
        self._subscribers[strategy_type].append(callback)
        subscription_id = f"{strategy_type}_{len(self._subscribers[strategy_type])}"
        
        self.logger.info(f"Subscribed to {strategy_type} parameters (ID: {subscription_id})")
        return subscription_id
    
    def unsubscribe(self, strategy_type: str, callback: Callable) -> bool:
        """
        Unsubscribe from parameter updates.
        
        Args:
            strategy_type: Strategy type to unsubscribe from
            callback: Callback function to remove
        
        Returns:
            True if unsubscribed successfully
        """
        if strategy_type not in self._subscribers:
            return False
        
        try:
            self._subscribers[strategy_type].remove(callback)
            self.logger.info(f"Unsubscribed from {strategy_type} parameters")
            return True
        except ValueError:
            self.logger.warning(f"Callback not found for {strategy_type}")
            return False
    
    def get_parameters(self, strategy_type: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Get parameters for a strategy, with symbol-specific overrides.
        
        Args:
            strategy_type: Strategy type
            symbol: Optional symbol for symbol-specific parameters
        
        Returns:
            Parameter dictionary (merges default + symbol-specific)
        """
        # Start with default parameters
        if strategy_type not in self._parameters:
            self.logger.warning(f"No parameters found for {strategy_type}")
            return {}
        
        default_params = self._parameters[strategy_type].get(None, {})
        
        # If no symbol specified, return default
        if symbol is None:
            return copy.deepcopy(default_params)
        
        # Merge symbol-specific overrides
        symbol_params = self._parameters[strategy_type].get(symbol, {})
        merged_params = copy.deepcopy(default_params)
        merged_params.update(symbol_params)
        
        return merged_params
    
    def update_parameters(
        self,
        strategy_type: str,
        parameters: Dict[str, Any],
        symbol: Optional[str] = None,
        changed_by: str = "system",
        change_reason: Optional[str] = None
    ) -> bool:
        """
        Update parameters and notify subscribers.
        
        Args:
            strategy_type: Strategy type
            parameters: New parameters (full or partial)
            symbol: Optional symbol (None = default parameters)
            changed_by: Who made the change
            change_reason: Reason for change
        
        Returns:
            True if update successful
        """
        try:
            # Initialize strategy if needed
            if strategy_type not in self._parameters:
                self._parameters[strategy_type] = {}
                self._history[strategy_type] = {}
                self._version_counters[strategy_type] = {}
            
            # Get current parameters
            current_params = self._parameters[strategy_type].get(symbol, {})
            
            # Merge with new parameters
            updated_params = copy.deepcopy(current_params)
            updated_params.update(parameters)
            
            # Validate parameters
            is_valid, error_msg = self.validate_parameters(strategy_type, updated_params, symbol)
            if not is_valid:
                self.logger.error(f"Parameter validation failed: {error_msg}")
                return False
            
            # Store updated parameters
            self._parameters[strategy_type][symbol] = updated_params
            
            # Increment version
            current_version = self._version_counters[strategy_type].get(symbol, 0) + 1
            self._version_counters[strategy_type][symbol] = current_version
            
            # Save to history
            version = ParameterVersion(
                version=current_version,
                parameters=copy.deepcopy(updated_params),
                timestamp=datetime.now(),
                changed_by=changed_by,
                change_reason=change_reason
            )
            
            if symbol not in self._history[strategy_type]:
                self._history[strategy_type][symbol] = []
            self._history[strategy_type][symbol].append(version)
            
            # Notify subscribers
            self._notify_subscribers(strategy_type, symbol, updated_params)
            
            symbol_str = symbol if symbol else "default"
            self.logger.info(
                f"Updated {strategy_type} parameters (symbol: {symbol_str}, "
                f"version: {current_version}, by: {changed_by})"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update parameters: {e}")
            return False
    
    def rollback_parameters(
        self,
        strategy_type: str,
        version: int,
        symbol: Optional[str] = None
    ) -> bool:
        """
        Rollback parameters to a previous version.
        
        Args:
            strategy_type: Strategy type
            version: Version number to rollback to
            symbol: Optional symbol
        
        Returns:
            True if rollback successful
        """
        try:
            # Check if strategy exists
            if strategy_type not in self._history:
                self.logger.error(f"No history for {strategy_type}")
                return False
            
            # Check if symbol history exists
            if symbol not in self._history[strategy_type]:
                self.logger.error(f"No history for {strategy_type}:{symbol}")
                return False
            
            # Find version
            history = self._history[strategy_type][symbol]
            target_version = None
            for ver in history:
                if ver.version == version:
                    target_version = ver
                    break
            
            if target_version is None:
                self.logger.error(f"Version {version} not found")
                return False
            
            # Rollback
            self._parameters[strategy_type][symbol] = copy.deepcopy(target_version.parameters)
            
            # Notify subscribers
            self._notify_subscribers(strategy_type, symbol, target_version.parameters)
            
            symbol_str = symbol if symbol else "default"
            self.logger.info(f"Rolled back {strategy_type}:{symbol_str} to version {version}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return False
    
    def get_parameter_history(
        self,
        strategy_type: str,
        symbol: Optional[str] = None
    ) -> List[ParameterVersion]:
        """
        Get parameter change history.
        
        Args:
            strategy_type: Strategy type
            symbol: Optional symbol
        
        Returns:
            List of parameter versions
        """
        if strategy_type not in self._history:
            return []
        
        if symbol not in self._history[strategy_type]:
            return []
        
        return self._history[strategy_type][symbol]
    
    def validate_parameters(
        self,
        strategy_type: str,
        parameters: Dict[str, Any],
        symbol: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate parameters.
        
        Args:
            strategy_type: Strategy type
            parameters: Parameters to validate
            symbol: Optional symbol
        
        Returns:
            (is_valid, error_message)
        """
        # Basic validation
        if not isinstance(parameters, dict):
            return False, "Parameters must be a dictionary"
        
        if len(parameters) == 0:
            return False, "Parameters cannot be empty"
        
        # Strategy-specific validation can be added here
        # For now, basic validation passes
        
        return True, None
    
    def _notify_subscribers(
        self,
        strategy_type: str,
        symbol: Optional[str],
        parameters: Dict[str, Any]
    ) -> None:
        """
        Notify all subscribers of parameter changes.
        
        Args:
            strategy_type: Strategy type
            symbol: Symbol (None for default)
            parameters: Updated parameters
        """
        if strategy_type not in self._subscribers:
            return
        
        failed_callbacks = []
        for callback in self._subscribers[strategy_type]:
            try:
                callback(strategy_type, symbol, parameters)
            except Exception as e:
                self.logger.error(f"Subscriber callback failed: {e}")
                failed_callbacks.append(callback)
        
        # Remove failed callbacks
        for callback in failed_callbacks:
            try:
                self._subscribers[strategy_type].remove(callback)
            except ValueError:
                pass
    
    def get_all_strategies(self) -> List[str]:
        """Get list of all registered strategy types"""
        return list(self._parameters.keys())
    
    def get_all_symbols(self, strategy_type: str) -> List[str]:
        """
        Get list of all symbols with parameters for a strategy.
        
        Args:
            strategy_type: Strategy type
        
        Returns:
            List of symbols (excludes None/default)
        """
        if strategy_type not in self._parameters:
            return []
        
        return [sym for sym in self._parameters[strategy_type].keys() if sym is not None]
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get registry status.
        
        Returns:
            Status dictionary with statistics
        """
        total_strategies = len(self._parameters)
        total_symbols = sum(
            len([s for s in symbols.keys() if s is not None])
            for symbols in self._parameters.values()
        )
        total_subscribers = sum(len(subs) for subs in self._subscribers.values())
        
        return {
            'total_strategies': total_strategies,
            'total_symbols': total_symbols,
            'total_subscribers': total_subscribers,
            'strategies': list(self._parameters.keys())
        }

