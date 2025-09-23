"""
Dependency Injection Container - Core Engine
============================================

Lightweight dependency injection system for core_engine components.
Provides centralized component management and dependency resolution.
"""

import logging
from typing import Dict, Type, Any, Optional, Callable, TypeVar
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

T = TypeVar('T')

class ComponentScope(Enum):
    """Component lifecycle scopes"""
    SINGLETON = "singleton"  # One instance for entire application
    TRANSIENT = "transient"  # New instance each time
    SCOPED = "scoped"       # One instance per scope (e.g., per request)

@dataclass
class ComponentRegistration:
    """Component registration metadata"""
    interface: Type
    implementation: Type
    scope: ComponentScope = ComponentScope.SINGLETON
    factory: Optional[Callable[[], Any]] = None
    instance: Optional[Any] = None

class DependencyInjectionContainer:
    """
    Lightweight dependency injection container

    Provides centralized component registration and resolution.
    Supports singleton, transient, and scoped component lifecycles.
    """

    def __init__(self):
        self._registrations: Dict[Type, ComponentRegistration] = {}
        self._scoped_instances: Dict[str, Dict[Type, Any]] = {}

    def register(self, interface: Type[T], implementation: Optional[Type[T]] = None,
                scope: ComponentScope = ComponentScope.SINGLETON,
                factory: Optional[Callable[[], T]] = None) -> 'DependencyInjectionContainer':
        """
        Register a component

        Args:
            interface: The interface/abstract class
            implementation: The concrete implementation class
            scope: Component lifecycle scope
            factory: Optional factory function for complex initialization
        """
        if implementation is None:
            implementation = interface

        registration = ComponentRegistration(
            interface=interface,
            implementation=implementation,
            scope=scope,
            factory=factory
        )

        self._registrations[interface] = registration
        logger.debug(f"Registered component: {interface.__name__} -> {implementation.__name__}")
        return self

    def register_instance(self, interface: Type[T], instance: T) -> 'DependencyInjectionContainer':
        """Register a pre-created instance as a singleton"""
        registration = ComponentRegistration(
            interface=interface,
            implementation=type(instance),
            scope=ComponentScope.SINGLETON,
            instance=instance
        )

        self._registrations[interface] = registration
        logger.debug(f"Registered instance: {interface.__name__} -> {type(instance).__name__}")
        return self

    def resolve(self, interface: Type[T], scope_name: Optional[str] = None) -> T:
        """
        Resolve a component instance

        Args:
            interface: The interface to resolve
            scope_name: Optional scope name for scoped components

        Returns:
            Instance of the requested interface

        Raises:
            ValueError: If component is not registered
        """
        if interface not in self._registrations:
            raise ValueError(f"Component not registered: {interface.__name__}")

        registration = self._registrations[interface]

        # Return existing singleton instance
        if registration.scope == ComponentScope.SINGLETON and registration.instance is not None:
            return registration.instance

        # Return existing scoped instance
        if registration.scope == ComponentScope.SCOPED and scope_name:
            if scope_name in self._scoped_instances and interface in self._scoped_instances[scope_name]:
                return self._scoped_instances[scope_name][interface]

        # Create new instance
        instance = self._create_instance(registration)

        # Store singleton instance
        if registration.scope == ComponentScope.SINGLETON:
            registration.instance = instance

        # Store scoped instance
        elif registration.scope == ComponentScope.SCOPED and scope_name:
            if scope_name not in self._scoped_instances:
                self._scoped_instances[scope_name] = {}
            self._scoped_instances[scope_name][interface] = instance

        return instance

    def _create_instance(self, registration: ComponentRegistration) -> Any:
        """Create a new instance of a component"""
        if registration.factory:
            return registration.factory()
        else:
            # Try to instantiate with dependency injection
            try:
                # Check if implementation has __init__ parameters that need injection
                import inspect
                sig = inspect.signature(registration.implementation.__init__)

                # Skip 'self' parameter
                params = list(sig.parameters.values())[1:]

                kwargs = {}
                for param in params:
                    if param.annotation != inspect.Parameter.empty:
                        try:
                            # Try to resolve dependency
                            kwargs[param.name] = self.resolve(param.annotation)
                        except ValueError:
                            # If dependency not found, try to use default or pass through
                            if param.default != inspect.Parameter.empty:
                                kwargs[param.name] = param.default
                            else:
                                raise

                return registration.implementation(**kwargs)

            except Exception as e:
                logger.warning(f"Failed to inject dependencies for {registration.implementation.__name__}: {e}")
                # Fallback to parameterless instantiation
                return registration.implementation()

    def clear_scope(self, scope_name: str):
        """Clear all instances in a scope"""
        if scope_name in self._scoped_instances:
            del self._scoped_instances[scope_name]

    def clear_all_scopes(self):
        """Clear all scoped instances"""
        self._scoped_instances.clear()

    def get_registered_components(self) -> Dict[Type, ComponentRegistration]:
        """Get all registered components"""
        return self._registrations.copy()

# Global container instance
_container = DependencyInjectionContainer()

def get_container() -> DependencyInjectionContainer:
    """Get the global dependency injection container"""
    return _container

def register_component(interface: Type[T], implementation: Optional[Type[T]] = None,
                      scope: ComponentScope = ComponentScope.SINGLETON,
                      factory: Optional[Callable[[], T]] = None) -> None:
    """Register a component in the global container"""
    _container.register(interface, implementation, scope, factory)

def resolve_component(interface: Type[T], scope_name: Optional[str] = None) -> T:
    """Resolve a component from the global container"""
    return _container.resolve(interface, scope_name)

def reset_container():
    """Reset the global container (for testing)"""
    global _container
    _container = DependencyInjectionContainer()