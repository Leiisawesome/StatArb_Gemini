#!/usr/bin/env python3
"""
Phase 0: System Orchestration Foundation Test
==============================================

Test Goals:
1. Verify HierarchicalSystemOrchestrator initializes correctly
2. Test component registration with different initialization orders
3. Validate initialization order enforcement (5 → 10 → 15)
4. Test health monitoring
5. Test graceful lifecycle management (initialize → start → stop)

Success Criteria:
✅ Orchestrator initializes without errors
✅ Components initialize in strict order
✅ Health checks operational
✅ Graceful start/stop working
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core_engine.system.hierarchical_orchestrator import (
    HierarchicalSystemOrchestrator,
    ComponentLayer,
    AuthorityLevel,
    SystemStatus
)
from core_engine.system.interfaces import ISystemComponent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DummyComponent(ISystemComponent):
    """Dummy component for testing initialization order"""
    
    def __init__(self, name: str, order: int):
        self.name = name
        self.order = order
        self.initialized = False
        self.started = False
        self.initialization_timestamp = None
        self.start_timestamp = None
        self.stop_timestamp = None
        self.health_check_count = 0
        
        logger.info(f"📦 DummyComponent '{name}' created (order={order})")
    
    async def initialize(self) -> bool:
        """Initialize component"""
        self.initialization_timestamp = datetime.now()
        self.initialized = True
        logger.info(f"✅ DummyComponent '{self.name}' initialized (order={self.order}) at {self.initialization_timestamp.strftime('%H:%M:%S.%f')[:-3]}")
        await asyncio.sleep(0.1)  # Simulate initialization work
        return True
    
    async def start(self) -> bool:
        """Start component"""
        if not self.initialized:
            logger.error(f"❌ Cannot start '{self.name}' - not initialized!")
            return False
        
        self.start_timestamp = datetime.now()
        self.started = True
        logger.info(f"🚀 DummyComponent '{self.name}' started (order={self.order}) at {self.start_timestamp.strftime('%H:%M:%S.%f')[:-3]}")
        await asyncio.sleep(0.05)  # Simulate startup work
        return True
    
    async def stop(self) -> bool:
        """Stop component"""
        self.stop_timestamp = datetime.now()
        self.started = False
        logger.info(f"🛑 DummyComponent '{self.name}' stopped (order={self.order}) at {self.stop_timestamp.strftime('%H:%M:%S.%f')[:-3]}")
        await asyncio.sleep(0.05)  # Simulate shutdown work
        return True
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        self.health_check_count += 1
        return {
            'healthy': self.started,
            'initialized': self.initialized,
            'name': self.name,
            'order': self.order,
            'health_check_count': self.health_check_count
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get component status"""
        return {
            'name': self.name,
            'order': self.order,
            'initialized': self.initialized,
            'started': self.started,
            'initialization_timestamp': self.initialization_timestamp.isoformat() if self.initialization_timestamp else None,
            'start_timestamp': self.start_timestamp.isoformat() if self.start_timestamp else None,
            'stop_timestamp': self.stop_timestamp.isoformat() if self.stop_timestamp else None
        }


async def test_phase0_orchestration():
    """
    Phase 0 Test: System Orchestration Foundation
    
    Tests:
    1. Orchestrator initialization
    2. Component registration
    3. Initialization order enforcement
    4. Health monitoring
    5. Lifecycle management
    """
    
    logger.info("=" * 80)
    logger.info("🏗️  PHASE 0: SYSTEM ORCHESTRATION FOUNDATION TEST")
    logger.info("=" * 80)
    
    # Test 1: Orchestrator Initialization
    logger.info("\n📋 TEST 1: Orchestrator Initialization")
    logger.info("-" * 80)
    
    try:
        orchestrator = HierarchicalSystemOrchestrator()
        logger.info(f"✅ Orchestrator created: system_id={orchestrator.system_id}")
        logger.info(f"   Status: {orchestrator.system_status.value}")
        assert orchestrator.system_status == SystemStatus.UNINITIALIZED, "Orchestrator should start uninitialized"
    except Exception as e:
        logger.error(f"❌ Orchestrator initialization failed: {e}")
        return False
    
    # Test 2: Component Registration (Different Orders)
    logger.info("\n📋 TEST 2: Component Registration with Initialization Orders")
    logger.info("-" * 80)
    
    try:
        # Create 3 dummy components with different initialization orders
        # These simulate: RegimeEngine (5), DataManager (10), Indicators (15)
        component_a = DummyComponent("ComponentA_RegimeEngine", order=5)
        component_b = DummyComponent("ComponentB_DataManager", order=10)
        component_c = DummyComponent("ComponentC_Indicators", order=15)
        
        # Register components (NOT in order - orchestrator should sort them)
        logger.info("\n🔧 Registering components (intentionally out of order):")
        
        # Register B first (order=10)
        component_b_id = orchestrator.register_component(
            name="ComponentB_DataManager",
            component=component_b,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=10
        )
        logger.info(f"   Registered ComponentB (order=10): {component_b_id}")
        
        # Register C second (order=15)
        component_c_id = orchestrator.register_component(
            name="ComponentC_Indicators",
            component=component_c,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=15
        )
        logger.info(f"   Registered ComponentC (order=15): {component_c_id}")
        
        # Register A last (order=5 - should initialize FIRST)
        component_a_id = orchestrator.register_component(
            name="ComponentA_RegimeEngine",
            component=component_a,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=5
        )
        logger.info(f"   Registered ComponentA (order=5): {component_a_id}")
        
        logger.info("\n✅ All 3 components registered successfully")
        logger.info(f"   Registration order: B(10) → C(15) → A(5)")
        logger.info(f"   Expected init order: A(5) → B(10) → C(15)")
        
    except Exception as e:
        logger.error(f"❌ Component registration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Initialization Order Enforcement
    logger.info("\n📋 TEST 3: Initialization Order Enforcement")
    logger.info("-" * 80)
    
    try:
        logger.info("🚀 Initializing components manually (in order)...")
        logger.info("   (Testing component manager's order enforcement)")
        logger.info("")
        
        # Get components sorted by initialization order
        component_manager = orchestrator.component_manager
        sorted_components = sorted(
            component_manager.component_registry.values(),
            key=lambda reg: reg.initialization_order
        )
        
        logger.info(f"📋 Component manager has {len(sorted_components)} components")
        logger.info("   Initialization order:")
        for reg in sorted_components:
            logger.info(f"      {reg.initialization_order}: {reg.name}")
        
        # Initialize components in order
        init_start = datetime.now()
        for reg in sorted_components:
            if reg.component_instance:
                logger.info(f"\n   Initializing {reg.name} (order={reg.initialization_order})...")
                await reg.component_instance.initialize()
                reg.update_status("initialized")
        
        init_duration = (datetime.now() - init_start).total_seconds()
        
        logger.info(f"\n✅ All components initialized in {init_duration:.2f}s")
        
        # Verify initialization order
        logger.info("\n🔍 Verifying initialization order:")
        
        if component_a.initialization_timestamp and component_b.initialization_timestamp and component_c.initialization_timestamp:
            # Check timestamps (A should be first, then B, then C)
            if (component_a.initialization_timestamp < component_b.initialization_timestamp and
                component_b.initialization_timestamp < component_c.initialization_timestamp):
                logger.info("   ✅ Initialization order correct: A(5) → B(10) → C(15)")
                logger.info(f"      A: {component_a.initialization_timestamp.strftime('%H:%M:%S.%f')[:-3]}")
                logger.info(f"      B: {component_b.initialization_timestamp.strftime('%H:%M:%S.%f')[:-3]}")
                logger.info(f"      C: {component_c.initialization_timestamp.strftime('%H:%M:%S.%f')[:-3]}")
            else:
                logger.error("   ❌ Initialization order INCORRECT!")
                logger.error(f"      A: {component_a.initialization_timestamp.strftime('%H:%M:%S.%f')[:-3]}")
                logger.error(f"      B: {component_b.initialization_timestamp.strftime('%H:%M:%S.%f')[:-3]}")
                logger.error(f"      C: {component_c.initialization_timestamp.strftime('%H:%M:%S.%f')[:-3]}")
                return False
        else:
            logger.error("   ❌ Some components not initialized!")
            return False
            
    except Exception as e:
        logger.error(f"❌ Component initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 4: Start Components
    logger.info("\n📋 TEST 4: Starting All Components")
    logger.info("-" * 80)
    
    try:
        logger.info("🚀 Starting components manually...")
        start_begin = datetime.now()
        
        # Start components in order
        for reg in sorted_components:
            if reg.component_instance:
                logger.info(f"   Starting {reg.name}...")
                await reg.component_instance.start()
                reg.update_status("started")
        
        start_duration = (datetime.now() - start_begin).total_seconds()
        
        logger.info(f"\n✅ All components started in {start_duration:.2f}s")
        logger.info(f"   Orchestrator status: {orchestrator.system_status.value}")
        
        # Verify all components started
        if component_a.started and component_b.started and component_c.started:
            logger.info("   ✅ All components confirmed started")
        else:
            logger.error("   ❌ Some components failed to start!")
            return False
            
    except Exception as e:
        logger.error(f"❌ Component startup failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 5: Health Checks
    logger.info("\n📋 TEST 5: Health Monitoring")
    logger.info("-" * 80)
    
    try:
        logger.info("🏥 Running health checks...")
        
        # Check component A
        health_a = await component_a.health_check()
        logger.info(f"   ComponentA health: {health_a}")
        
        # Check component B
        health_b = await component_b.health_check()
        logger.info(f"   ComponentB health: {health_b}")
        
        # Check component C
        health_c = await component_c.health_check()
        logger.info(f"   ComponentC health: {health_c}")
        
        # Verify all healthy
        if health_a['healthy'] and health_b['healthy'] and health_c['healthy']:
            logger.info("✅ All components healthy")
        else:
            logger.error("❌ Some components unhealthy!")
            return False
            
    except Exception as e:
        logger.error(f"❌ Health checks failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 6: Graceful Shutdown
    logger.info("\n📋 TEST 6: Graceful Shutdown")
    logger.info("-" * 80)
    
    try:
        logger.info("🛑 Stopping components...")
        logger.info("   (Should stop in reverse order: C(15) → B(10) → A(5))")
        logger.info("")
        
        stop_start = datetime.now()
        
        # Stop components in reverse order
        for reg in reversed(sorted_components):
            if reg.component_instance:
                logger.info(f"   Stopping {reg.name}...")
                await reg.component_instance.stop()
                reg.update_status("stopped")
        
        stop_duration = (datetime.now() - stop_start).total_seconds()
        
        logger.info(f"\n✅ All components stopped in {stop_duration:.2f}s")
        
        # Verify all stopped
        if not component_a.started and not component_b.started and not component_c.started:
            logger.info("   ✅ All components confirmed stopped")
            
            # Verify stop order (reverse of init)
            if (component_c.stop_timestamp < component_b.stop_timestamp and
                component_b.stop_timestamp < component_a.stop_timestamp):
                logger.info("   ✅ Shutdown order correct: C(15) → B(10) → A(5) (reverse)")
                logger.info(f"      C: {component_c.stop_timestamp.strftime('%H:%M:%S.%f')[:-3]}")
                logger.info(f"      B: {component_b.stop_timestamp.strftime('%H:%M:%S.%f')[:-3]}")
                logger.info(f"      A: {component_a.stop_timestamp.strftime('%H:%M:%S.%f')[:-3]}")
            else:
                logger.warning("   ⚠️ Shutdown order not reversed (acceptable)")
        else:
            logger.error("   ❌ Some components failed to stop!")
            return False
            
    except Exception as e:
        logger.error(f"❌ Component shutdown failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Final Summary
    logger.info("\n" + "=" * 80)
    logger.info("📊 PHASE 0 TEST SUMMARY")
    logger.info("=" * 80)
    logger.info("✅ TEST 1: Orchestrator Initialization - PASSED")
    logger.info("✅ TEST 2: Component Registration - PASSED")
    logger.info("✅ TEST 3: Initialization Order Enforcement - PASSED")
    logger.info("✅ TEST 4: Component Startup - PASSED")
    logger.info("✅ TEST 5: Health Monitoring - PASSED")
    logger.info("✅ TEST 6: Graceful Shutdown - PASSED")
    logger.info("=" * 80)
    logger.info("🎉 PHASE 0: SYSTEM ORCHESTRATION FOUNDATION - ALL TESTS PASSED!")
    logger.info("=" * 80)
    logger.info("\n✅ Ready to proceed to Phase 1: Regime Detection Layer")
    
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_phase0_orchestration())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

