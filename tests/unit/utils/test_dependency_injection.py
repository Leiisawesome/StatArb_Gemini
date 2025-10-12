"""
Unit tests for utils module
"""

import pytest

# Import all utils modules
from core_engine.utils.dependency_injection import (
    ComponentScope, ComponentRegistration, DependencyInjectionContainer,
    get_container, register_component, resolve_component, reset_container
)


class TestDependencyInjection:
    """Test dependency injection utilities"""

    def test_component_scope_enum(self):
        """Test ComponentScope enum values"""
        assert ComponentScope.SINGLETON.value == "singleton"
        assert ComponentScope.TRANSIENT.value == "transient"
        assert ComponentScope.SCOPED.value == "scoped"

    def test_component_registration_creation(self):
        """Test ComponentRegistration creation"""
        registration = ComponentRegistration(
            interface=str,
            implementation=str,
            scope=ComponentScope.SINGLETON,
            factory=lambda: "test",
            instance="pre_created"
        )

        assert registration.interface == str
        assert registration.implementation == str
        assert registration.scope == ComponentScope.SINGLETON
        assert registration.factory() == "test"
        assert registration.instance == "pre_created"

    def test_dependency_injection_container_register(self):
        """Test DependencyInjectionContainer register"""
        container = DependencyInjectionContainer()

        # Register a component
        container.register(str, str, ComponentScope.SINGLETON)

        assert str in container._registrations
        reg = container._registrations[str]
        assert reg.interface == str
        assert reg.implementation == str
        assert reg.scope == ComponentScope.SINGLETON

    def test_dependency_injection_container_register_instance(self):
        """Test DependencyInjectionContainer register_instance"""
        container = DependencyInjectionContainer()

        # Register an instance
        container.register_instance(str, "test_instance")

        assert str in container._registrations
        reg = container._registrations[str]
        assert reg.interface == str
        assert reg.implementation == type("test_instance")
        assert reg.scope == ComponentScope.SINGLETON
        assert reg.instance == "test_instance"

    def test_dependency_injection_container_resolve_singleton(self):
        """Test DependencyInjectionContainer resolve singleton"""
        container = DependencyInjectionContainer()

        # Register a simple class
        class TestClass:
            def __init__(self):
                self.value = "test"

        container.register(TestClass, TestClass, ComponentScope.SINGLETON)

        # Resolve multiple times - should get same instance
        instance1 = container.resolve(TestClass)
        instance2 = container.resolve(TestClass)

        assert isinstance(instance1, TestClass)
        assert isinstance(instance2, TestClass)
        assert instance1 is instance2  # Same instance
        assert instance1.value == "test"

    def test_dependency_injection_container_resolve_transient(self):
        """Test DependencyInjectionContainer resolve transient"""
        container = DependencyInjectionContainer()

        class TestClass:
            def __init__(self):
                self.value = "test"

        container.register(TestClass, TestClass, ComponentScope.TRANSIENT)

        # Resolve multiple times - should get different instances
        instance1 = container.resolve(TestClass)
        instance2 = container.resolve(TestClass)

        assert isinstance(instance1, TestClass)
        assert isinstance(instance2, TestClass)
        assert instance1 is not instance2  # Different instances

    def test_dependency_injection_container_resolve_scoped(self):
        """Test DependencyInjectionContainer resolve scoped"""
        container = DependencyInjectionContainer()

        class TestClass:
            def __init__(self):
                self.value = "test"

        container.register(TestClass, TestClass, ComponentScope.SCOPED)

        # Resolve in same scope - should get same instance
        instance1 = container.resolve(TestClass, "scope1")
        instance2 = container.resolve(TestClass, "scope1")

        assert isinstance(instance1, TestClass)
        assert isinstance(instance2, TestClass)
        assert instance1 is instance2  # Same instance in same scope

        # Resolve in different scope - should get different instance
        instance3 = container.resolve(TestClass, "scope2")

        assert isinstance(instance3, TestClass)
        assert instance3 is not instance1  # Different instance in different scope

    def test_dependency_injection_container_resolve_with_dependencies(self):
        """Test DependencyInjectionContainer resolve with dependencies"""
        container = DependencyInjectionContainer()

        class Dependency:
            def __init__(self):
                self.name = "dependency"

        class Dependent:
            def __init__(self, dependency: Dependency):
                self.dependency = dependency

        # Register dependency first
        container.register(Dependency, Dependency, ComponentScope.SINGLETON)
        # Register dependent class
        container.register(Dependent, Dependent, ComponentScope.SINGLETON)

        # Resolve dependent - should inject dependency
        instance = container.resolve(Dependent)

        assert isinstance(instance, Dependent)
        assert isinstance(instance.dependency, Dependency)
        assert instance.dependency.name == "dependency"

    def test_dependency_injection_container_resolve_unregistered(self):
        """Test DependencyInjectionContainer resolve unregistered component"""
        container = DependencyInjectionContainer()

        with pytest.raises(ValueError, match="Component not registered"):
            container.resolve(str)

    def test_dependency_injection_container_clear_scope(self):
        """Test DependencyInjectionContainer clear_scope"""
        container = DependencyInjectionContainer()

        class TestClass:
            pass

        container.register(TestClass, TestClass, ComponentScope.SCOPED)

        # Create scoped instance
        container.resolve(TestClass, "test_scope")
        assert "test_scope" in container._scoped_instances
        assert TestClass in container._scoped_instances["test_scope"]

        # Clear scope
        container.clear_scope("test_scope")

        assert "test_scope" not in container._scoped_instances

    def test_dependency_injection_container_clear_all_scopes(self):
        """Test DependencyInjectionContainer clear_all_scopes"""
        container = DependencyInjectionContainer()

        class TestClass:
            pass

        container.register(TestClass, TestClass, ComponentScope.SCOPED)

        # Create instances in multiple scopes
        container.resolve(TestClass, "scope1")
        container.resolve(TestClass, "scope2")

        assert len(container._scoped_instances) == 2

        # Clear all scopes
        container.clear_all_scopes()

        assert len(container._scoped_instances) == 0

    def test_dependency_injection_container_get_registered_components(self):
        """Test DependencyInjectionContainer get_registered_components"""
        container = DependencyInjectionContainer()

        class TestClass:
            pass

        container.register(TestClass, TestClass, ComponentScope.SINGLETON)

        registered = container.get_registered_components()

        assert TestClass in registered
        assert isinstance(registered[TestClass], ComponentRegistration)

    def test_global_dependency_injection_functions(self):
        """Test global dependency injection functions"""
        # Reset container
        reset_container()

        # Test register_component
        class TestClass:
            pass

        register_component(TestClass, TestClass, ComponentScope.SINGLETON)

        # Test resolve_component
        instance = resolve_component(TestClass)

        assert isinstance(instance, TestClass)

        # Test get_container
        container = get_container()
        assert isinstance(container, DependencyInjectionContainer)
