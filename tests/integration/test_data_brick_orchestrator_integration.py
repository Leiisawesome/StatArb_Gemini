"""
Integration Test: Data Brick with HierarchicalSystemOrchestrator

Tests all data brick components with the orchestrator to validate:
1. Component registration
2. Lifecycle management (initialize → start → stop)
3. Health checks and status reporting
4. Proper ISystemComponent compliance
"""

import pytest
import asyncio
from typing import Dict, Any
from datetime import datetime

# Import orchestrator
from core_engine.system.hierarchical_orchestrator import (
    HierarchicalSystemOrchestrator,
    ComponentLayer,
    AuthorityLevel
)

# Import data brick components
from core_engine.data.manager import ClickHouseDataManager
from core_engine.data.liquidity_engine import LiquidityAssessmentEngine
from core_engine.data.alternative_data_handler import AlternativeDataHandler
from core_engine.data.feeds.manager import FeedManager
from core_engine.data.sources.market_data import MarketDataHandler
from core_engine.data.validation.validator import DataValidator
from core_engine.data.sources.clickhouse import DataEngine, DataEngineConfig

# Import config
from core_engine.config import DataConfig


@pytest.fixture
def orchestrator():
    """Create orchestrator instance"""
    return HierarchicalSystemOrchestrator()


@pytest.fixture
def data_config():
    """Create minimal data config for testing"""
    return DataConfig(
        symbols=['AAPL', 'MSFT'],
        start_date='2024-01-01',
        end_date='2024-01-31',
        enable_caching=True,
        cache_ttl=3600
    )


class TestDataBrickOrchestrationBasic:
    """Basic orchestrator integration tests"""
    
    @pytest.mark.asyncio
    async def test_orchestrator_creation(self, orchestrator):
        """Test orchestrator can be created"""
        assert orchestrator is not None
        assert isinstance(orchestrator, HierarchicalSystemOrchestrator)
        print("✅ Orchestrator created successfully")
    
    @pytest.mark.asyncio
    async def test_liquidity_engine_registration(self, orchestrator):
        """Test LiquidityAssessmentEngine registration"""
        # Create component
        liquidity_engine = LiquidityAssessmentEngine()
        
        # Register with orchestrator
        component_id = orchestrator.register_component(
            name="LiquidityAssessmentEngine",
            component=liquidity_engine,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=12
        )
        
        assert component_id is not None
        assert liquidity_engine.component_id == component_id
        print(f"✅ LiquidityAssessmentEngine registered: {component_id}")
    
    @pytest.mark.asyncio
    async def test_market_data_handler_registration(self, orchestrator):
        """Test MarketDataHandler registration"""
        # Create component with minimal config
        handler = MarketDataHandler(config={'max_real_time_buffer': 100})
        
        # Register with orchestrator
        component_id = orchestrator.register_component(
            name="MarketDataHandler",
            component=handler,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=10
        )
        
        assert component_id is not None
        assert handler.component_id == component_id
        print(f"✅ MarketDataHandler registered: {component_id}")
    
    @pytest.mark.asyncio
    async def test_data_validator_registration(self, orchestrator):
        """Test DataValidator registration"""
        # Create component
        validator = DataValidator(config={'enable_monitoring': False})
        
        # Register with orchestrator
        component_id = orchestrator.register_component(
            name="DataValidator",
            component=validator,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=15
        )
        
        assert component_id is not None
        assert validator.component_id == component_id
        print(f"✅ DataValidator registered: {component_id}")


class TestDataBrickLifecycle:
    """Test full lifecycle management of data components"""
    
    @pytest.mark.asyncio
    async def test_liquidity_engine_lifecycle(self, orchestrator):
        """Test LiquidityAssessmentEngine full lifecycle"""
        # Create and register
        engine = LiquidityAssessmentEngine()
        component_id = orchestrator.register_component(
            name="LiquidityEngine",
            component=engine,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=12
        )
        
        # Test initialize
        init_result = await engine.initialize()
        assert init_result is True
        assert engine.is_initialized is True
        print("✅ LiquidityEngine initialized")
        
        # Test start
        start_result = await engine.start()
        assert start_result is True
        assert engine.is_operational is True
        print("✅ LiquidityEngine started")
        
        # Test health check
        health = await engine.health_check()
        assert health['healthy'] is True
        assert health['initialized'] is True
        assert health['operational'] is True
        print(f"✅ LiquidityEngine health check: {health}")
        
        # Test status
        status = engine.get_status()
        assert status['initialized'] is True
        assert status['operational'] is True
        print(f"✅ LiquidityEngine status: {status}")
        
        # Test stop
        stop_result = await engine.stop()
        assert stop_result is True
        assert engine.is_operational is False
        print("✅ LiquidityEngine stopped")
    
    @pytest.mark.asyncio
    async def test_market_data_handler_lifecycle(self, orchestrator):
        """Test MarketDataHandler full lifecycle"""
        # Create and register with config that prevents DataFeed initialization
        handler = MarketDataHandler(config={
            'max_real_time_buffer': 100,
            'enable_performance_monitoring': False,
            'auto_initialize_feeds': False  # Prevent automatic feed initialization
        })
        component_id = orchestrator.register_component(
            name="MarketDataHandler",
            component=handler,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=10
        )
        
        # Override _initialize_default_feeds to be a no-op for testing
        async def mock_init_feeds():
            pass
        handler._initialize_default_feeds = mock_init_feeds
        
        # Test initialize
        init_result = await handler.initialize()
        assert init_result is True
        assert handler.is_initialized is True
        print("✅ MarketDataHandler initialized")
        
        # Test start
        start_result = await handler.start()
        assert start_result is True
        assert handler.is_operational is True
        print("✅ MarketDataHandler started")
        
        # Test health check
        health = await handler.health_check()
        assert health['initialized'] is True
        assert health['operational'] is True
        print(f"✅ MarketDataHandler health check: {health}")
        
        # Test stop
        stop_result = await handler.stop()
        assert stop_result is True
        assert handler.is_operational is False
        print("✅ MarketDataHandler stopped")
    
    @pytest.mark.asyncio
    async def test_data_validator_lifecycle(self, orchestrator):
        """Test DataValidator full lifecycle"""
        # Create and register
        validator = DataValidator(config={'enable_monitoring': False})
        component_id = orchestrator.register_component(
            name="DataValidator",
            component=validator,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=15
        )
        
        # Test initialize
        init_result = await validator.initialize()
        assert init_result is True
        assert validator.is_initialized is True
        print("✅ DataValidator initialized")
        
        # Test start
        start_result = await validator.start()
        assert start_result is True
        assert validator.is_operational is True
        print("✅ DataValidator started")
        
        # Test health check
        health = await validator.health_check()
        assert health['initialized'] is True
        assert health['operational'] is True
        print(f"✅ DataValidator health check: {health}")
        
        # Test stop
        stop_result = await validator.stop()
        assert stop_result is True
        assert validator.is_operational is False
        print("✅ DataValidator stopped")


class TestDataBrickMultiComponent:
    """Test multiple data components orchestrated together"""
    
    @pytest.mark.asyncio
    async def test_multiple_components_registration(self, orchestrator):
        """Test registering multiple data components"""
        components = []
        
        # Register LiquidityEngine
        liquidity = LiquidityAssessmentEngine()
        lid = orchestrator.register_component(
            name="LiquidityEngine",
            component=liquidity,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=12
        )
        components.append(('LiquidityEngine', lid, liquidity))
        
        # Register MarketDataHandler
        market_data = MarketDataHandler(config={'enable_performance_monitoring': False})
        # Mock the feed initialization
        async def mock_init_feeds():
            pass
        market_data._initialize_default_feeds = mock_init_feeds
        mid = orchestrator.register_component(
            name="MarketDataHandler",
            component=market_data,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=10
        )
        components.append(('MarketDataHandler', mid, market_data))
        
        # Register DataValidator
        validator = DataValidator(config={'enable_monitoring': False})
        vid = orchestrator.register_component(
            name="DataValidator",
            component=validator,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=15
        )
        components.append(('DataValidator', vid, validator))
        
        # Verify all registered
        assert len(components) == 3
        for name, comp_id, component in components:
            assert comp_id is not None
            assert component.component_id == comp_id
            print(f"✅ {name} registered: {comp_id}")
    
    @pytest.mark.asyncio
    async def test_multiple_components_coordinated_lifecycle(self, orchestrator):
        """Test coordinated lifecycle of multiple components"""
        # Register components
        liquidity = LiquidityAssessmentEngine()
        orchestrator.register_component(
            name="LiquidityEngine",
            component=liquidity,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=12
        )
        
        market_data = MarketDataHandler(config={'enable_performance_monitoring': False})
        # Mock the feed initialization  
        async def mock_init_feeds():
            pass
        market_data._initialize_default_feeds = mock_init_feeds
        orchestrator.register_component(
            name="MarketDataHandler",
            component=market_data,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=10
        )
        
        validator = DataValidator(config={'enable_monitoring': False})
        orchestrator.register_component(
            name="DataValidator",
            component=validator,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=15
        )
        
        components = [
            ('LiquidityEngine', liquidity),
            ('MarketDataHandler', market_data),
            ('DataValidator', validator)
        ]
        
        # Initialize all
        print("\n🔄 Initializing all components...")
        for name, component in components:
            result = await component.initialize()
            assert result is True
            assert component.is_initialized is True
            print(f"  ✅ {name} initialized")
        
        # Start all
        print("\n🔄 Starting all components...")
        for name, component in components:
            result = await component.start()
            assert result is True
            assert component.is_operational is True
            print(f"  ✅ {name} started")
        
        # Health check all
        print("\n🔄 Health checking all components...")
        for name, component in components:
            health = await component.health_check()
            assert health['healthy'] is True
            assert health['initialized'] is True
            assert health['operational'] is True
            print(f"  ✅ {name} healthy: {health}")
        
        # Stop all
        print("\n🔄 Stopping all components...")
        for name, component in components:
            result = await component.stop()
            assert result is True
            assert component.is_operational is False
            print(f"  ✅ {name} stopped")
        
        print("\n✅ All components completed full lifecycle successfully!")


class TestDataBrickComponentCompliance:
    """Test ISystemComponent compliance for all data brick components"""
    
    @pytest.mark.asyncio
    async def test_all_components_have_required_methods(self):
        """Verify all data components have required ISystemComponent methods"""
        required_methods = ['initialize', 'start', 'stop', 'health_check', 'get_status']
        
        components_to_test = [
            ('LiquidityAssessmentEngine', LiquidityAssessmentEngine()),
            ('MarketDataHandler', MarketDataHandler(config={'enable_performance_monitoring': False})),
            ('DataValidator', DataValidator(config={'enable_monitoring': False})),
            ('DataEngine', DataEngine(DataEngineConfig(
                enable_market_data=False,
                enable_alternative_data=False,
                enable_data_validation=False,
                enable_caching=False,
                enable_feed_management=False
            ))),
        ]
        
        print("\n🔍 Checking ISystemComponent method compliance...")
        for name, component in components_to_test:
            for method in required_methods:
                assert hasattr(component, method), f"{name} missing {method}"
            print(f"  ✅ {name} has all required methods")
        
        print("\n✅ All components are ISystemComponent compliant!")
    
    @pytest.mark.asyncio
    async def test_all_components_have_lifecycle_state(self):
        """Verify all data components have proper lifecycle state attributes"""
        required_attributes = ['is_initialized', 'is_operational', 'component_id', 'logger']
        
        components_to_test = [
            ('LiquidityAssessmentEngine', LiquidityAssessmentEngine()),
            ('MarketDataHandler', MarketDataHandler(config={'enable_performance_monitoring': False})),
            ('DataValidator', DataValidator(config={'enable_monitoring': False})),
            ('DataEngine', DataEngine(DataEngineConfig(
                enable_market_data=False,
                enable_alternative_data=False,
                enable_data_validation=False,
                enable_caching=False,
                enable_feed_management=False
            ))),
        ]
        
        print("\n🔍 Checking lifecycle state attributes...")
        for name, component in components_to_test:
            for attr in required_attributes:
                assert hasattr(component, attr), f"{name} missing {attr}"
            
            # Verify initial state
            assert component.is_initialized is False, f"{name} should not be initialized yet"
            assert component.is_operational is False, f"{name} should not be operational yet"
            
            print(f"  ✅ {name} has proper lifecycle state")
        
        print("\n✅ All components have proper lifecycle state!")


class TestDataBrickStressTest:
    """Stress test data brick orchestration"""
    
    @pytest.mark.asyncio
    async def test_rapid_lifecycle_cycles(self, orchestrator):
        """Test rapid initialize/start/stop cycles"""
        liquidity = LiquidityAssessmentEngine()
        orchestrator.register_component(
            name="LiquidityEngine",
            component=liquidity,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=12
        )
        
        print("\n🔄 Running 5 rapid lifecycle cycles...")
        for i in range(5):
            # Initialize
            await liquidity.initialize()
            assert liquidity.is_initialized is True
            
            # Start
            await liquidity.start()
            assert liquidity.is_operational is True
            
            # Health check
            health = await liquidity.health_check()
            assert health['healthy'] is True
            
            # Stop
            await liquidity.stop()
            assert liquidity.is_operational is False
            
            print(f"  ✅ Cycle {i+1} completed")
        
        print("\n✅ All 5 rapid cycles completed successfully!")
    
    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self, orchestrator):
        """Test concurrent health checks on multiple components"""
        components = []
        
        for i in range(3):
            liquidity = LiquidityAssessmentEngine()
            orchestrator.register_component(
                name=f"LiquidityEngine_{i}",
                component=liquidity,
                layer=ComponentLayer.SUPPORT,
                authority_level=AuthorityLevel.OPERATIONAL,
                initialization_order=12 + i
            )
            await liquidity.initialize()
            await liquidity.start()
            components.append(liquidity)
        
        print("\n🔄 Running 10 concurrent health checks on 3 components...")
        for cycle in range(10):
            # Run health checks concurrently
            tasks = [comp.health_check() for comp in components]
            results = await asyncio.gather(*tasks)
            
            # Verify all healthy
            for i, health in enumerate(results):
                assert health['healthy'] is True
            
            print(f"  ✅ Concurrent health check cycle {cycle+1} passed")
        
        # Cleanup
        for comp in components:
            await comp.stop()
        
        print("\n✅ All concurrent health checks passed!")


if __name__ == "__main__":
    print("=" * 80)
    print("Data Brick + HierarchicalSystemOrchestrator Integration Test")
    print("=" * 80)
    print("\nRun with: pytest -v -s tests/integration/test_data_brick_orchestrator_integration.py")
    print()

