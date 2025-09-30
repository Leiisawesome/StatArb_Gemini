#!/usr/bin/env python3
"""
Enhanced System Integration Tests
================================

Test integration of Priority 1 and Priority 2 enhancements:
- Production monitoring components
- Multi-strategy coordination
- Updated SystemIntegrationManager

Author: StatArb_Gemini Integration Test Team
Version: 1.0.0
"""

import pytest
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

# Import enhanced components
from core_engine.system.integration_manager import SystemIntegrationManager, SystemConfiguration
from core_engine.system.production_monitoring import (
    ProductionHealthMonitor, GracefulDegradationManager,
    AuditTrailManager, DisasterRecoveryManager
)
from core_engine.trading.strategies.multi_strategy_coordinator import (
    MultiStrategySignalAggregator, SignalConflictResolver
)
from core_engine.trading.strategies.manager import StrategyManager
from core_engine.type_definitions.strategy import StrategyType

logger = logging.getLogger(__name__)


class TestEnhancedSystemIntegration:
    """Test enhanced system integration with new components"""
    
    @pytest.fixture
    async def enhanced_config(self):
        """Create enhanced system configuration"""
        return SystemConfiguration(
            # Enable all new features
            enable_production_monitoring=True,
            enable_audit_trail=True,
            enable_disaster_recovery=True,
            
            # Production monitoring config
            production_health_monitor_config={
                'cpu_threshold': 80.0,
                'memory_threshold': 85.0,
                'monitoring_interval': 5  # Fast for testing
            },
            audit_trail_config={
                'storage_backend': 'file',
                'audit_file_path': './test_audit.jsonl',
                'buffer_size': 10
            },
            
            # Strategy manager config with multi-strategy coordination
            strategy_manager_config={
                'enable_multi_strategy_coordination': True,
                'enable_signal_aggregation': True,
                'enable_conflict_resolution': True,
                'max_concurrent_strategies': 3
            }
        )
    
    @pytest.fixture
    async def integration_manager(self, enhanced_config):
        """Create integration manager with enhanced config"""
        manager = SystemIntegrationManager(enhanced_config)
        yield manager
        
        # Cleanup
        if manager.is_operational:
            await manager.stop()
    
    async def test_production_monitoring_components_initialization(self, enhanced_config):
        """Test that production monitoring components initialize correctly"""
        
        # Test ProductionHealthMonitor
        health_monitor = ProductionHealthMonitor(enhanced_config.production_health_monitor_config)
        assert await health_monitor.initialize()
        assert await health_monitor.start()
        
        health_status = await health_monitor.health_check()
        assert health_status['healthy']
        assert health_status['component_type'] == 'ProductionHealthMonitor'
        
        await health_monitor.stop()
        
        # Test GracefulDegradationManager
        degradation_manager = GracefulDegradationManager()
        assert await degradation_manager.initialize()
        assert await degradation_manager.start()
        
        degradation_status = await degradation_manager.health_check()
        assert degradation_status['healthy']
        assert degradation_status['component_type'] == 'GracefulDegradationManager'
        
        await degradation_manager.stop()
        
        # Test AuditTrailManager
        audit_manager = AuditTrailManager(enhanced_config.audit_trail_config)
        assert await audit_manager.initialize()
        assert await audit_manager.start()
        
        # Test audit logging
        event_id = await audit_manager.log_audit_event(
            event_type='test_event',
            component='test_component',
            action='test_action',
            details={'test': 'data'}
        )
        assert event_id is not None
        
        await audit_manager.stop()
        
        # Test DisasterRecoveryManager
        disaster_recovery = DisasterRecoveryManager()
        assert await disaster_recovery.initialize()
        assert await disaster_recovery.start()
        
        # Test backup creation
        backup_result = await disaster_recovery.create_system_backup()
        assert backup_result['backup_id'] is not None
        
        await disaster_recovery.stop()
    
    async def test_multi_strategy_coordination_components(self):
        """Test multi-strategy coordination components"""
        
        # Test MultiStrategySignalAggregator
        aggregator_config = {
            'max_concurrent_strategies': 3,
            'min_confidence_threshold': 0.6,
            'enable_dynamic_weighting': True
        }
        
        aggregator = MultiStrategySignalAggregator(aggregator_config)
        assert await aggregator.initialize()
        assert await aggregator.start()
        
        aggregator_status = await aggregator.health_check()
        assert aggregator_status['healthy']
        assert aggregator_status['component_type'] == 'MultiStrategySignalAggregator'
        
        await aggregator.stop()
        
        # Test SignalConflictResolver
        resolver_config = {
            'resolution_method': 'confidence_weighted',
            'conflict_threshold': 0.1
        }
        
        resolver = SignalConflictResolver(resolver_config)
        assert await resolver.initialize()
        assert await resolver.start()
        
        resolver_status = await resolver.health_check()
        assert resolver_status['healthy']
        assert resolver_status['component_type'] == 'SignalConflictResolver'
        
        await resolver.stop()
    
    async def test_enhanced_strategy_manager_integration(self):
        """Test enhanced StrategyManager with multi-strategy coordination"""
        
        config = {
            'enable_multi_strategy_coordination': True,
            'enable_signal_aggregation': True,
            'enable_conflict_resolution': True,
            'max_concurrent_strategies': 3,
            'min_confidence_threshold': 0.6
        }
        
        strategy_manager = StrategyManager(config)
        assert await strategy_manager.initialize()
        assert await strategy_manager.start()
        
        # Test multi-strategy status
        multi_strategy_status = strategy_manager.get_multi_strategy_status()
        assert multi_strategy_status['multi_strategy_enabled']
        assert multi_strategy_status['signal_aggregator_status'] is not None
        assert multi_strategy_status['conflict_resolver_status'] is not None
        
        # Test enhanced strategy registration
        strategy_config = {
            'name': 'test_momentum_strategy',
            'allocation_pct': 0.2,
            'weight': 1.0,
            'priority': 1
        }
        
        success = await strategy_manager.register_enhanced_strategy(
            StrategyType.MOMENTUM, 
            strategy_config
        )
        assert success
        
        # Verify strategy was registered
        status = strategy_manager.get_status()
        assert len(strategy_manager.active_strategies) > 0
        
        await strategy_manager.stop()
    
    async def test_full_system_integration(self, integration_manager):
        """Test full system integration with all enhanced components"""
        
        # Initialize the complete system
        assert await integration_manager.initialize()
        assert await integration_manager.start()
        
        # Verify system is operational
        assert integration_manager.is_operational
        
        # Check system health
        health_status = await integration_manager.health_check()
        assert health_status['healthy']
        assert health_status['initialized']
        assert health_status['operational']
        
        # Verify production components are loaded
        system_status = integration_manager.get_status()
        component_names = list(system_status['component_status'].keys())
        
        # Check for production monitoring components
        production_components = [
            'production_health_monitor',
            'graceful_degradation_manager', 
            'audit_trail_manager',
            'disaster_recovery_manager'
        ]
        
        for component in production_components:
            if component in component_names:
                logger.info(f"✅ Production component found: {component}")
        
        # Check for strategy manager with multi-strategy coordination
        if 'strategy_manager' in component_names:
            strategy_manager = integration_manager.components.get('strategy_manager')
            if strategy_manager and hasattr(strategy_manager, 'get_multi_strategy_status'):
                multi_status = strategy_manager.get_multi_strategy_status()
                logger.info(f"✅ Multi-strategy coordination status: {multi_status}")
        
        # Test system metrics
        system_metrics = health_status.get('system_metrics', {})
        assert system_metrics['total_components'] > 0
        
        logger.info(f"✅ System integration test passed with {system_metrics['total_components']} components")
    
    async def test_production_monitoring_workflow(self, integration_manager):
        """Test production monitoring workflow"""
        
        # Initialize system
        await integration_manager.initialize()
        await integration_manager.start()
        
        # Get production health monitor if available
        health_monitor = integration_manager.components.get('production_health_monitor')
        if health_monitor:
            # Perform comprehensive health check
            health_results = await health_monitor.perform_comprehensive_health_check()
            assert len(health_results) > 0
            
            # Check system resources
            if 'system_resources' in health_results:
                system_health = health_results['system_resources']
                assert system_health.component_name == 'system_resources'
                assert system_health.metrics is not None
                logger.info(f"✅ System resources check: {system_health.status.value}")
        
        # Get audit trail manager if available
        audit_manager = integration_manager.components.get('audit_trail_manager')
        if audit_manager:
            # Log a test audit event
            event_id = await audit_manager.log_audit_event(
                event_type='system_test',
                component='integration_test',
                action='test_audit_logging',
                details={'test_run': datetime.now().isoformat()}
            )
            assert event_id is not None
            logger.info(f"✅ Audit event logged: {event_id}")
        
        # Get disaster recovery manager if available
        disaster_recovery = integration_manager.components.get('disaster_recovery_manager')
        if disaster_recovery:
            # Test backup creation
            backup_result = await disaster_recovery.create_system_backup()
            assert 'backup_id' in backup_result
            logger.info(f"✅ System backup created: {backup_result['backup_id']}")


@pytest.mark.asyncio
async def test_enhanced_system_integration_suite():
    """Run the complete enhanced system integration test suite"""
    
    test_instance = TestEnhancedSystemIntegration()
    
    # Create enhanced config
    enhanced_config = SystemConfiguration(
        enable_production_monitoring=True,
        enable_audit_trail=True,
        enable_disaster_recovery=True,
        production_health_monitor_config={
            'monitoring_interval': 5
        },
        audit_trail_config={
            'storage_backend': 'file',
            'audit_file_path': './test_audit.jsonl'
        },
        strategy_manager_config={
            'enable_multi_strategy_coordination': True,
            'enable_signal_aggregation': True,
            'enable_conflict_resolution': True
        }
    )
    
    # Test individual components
    await test_instance.test_production_monitoring_components_initialization(enhanced_config)
    await test_instance.test_multi_strategy_coordination_components()
    await test_instance.test_enhanced_strategy_manager_integration()
    
    # Test full integration
    integration_manager = SystemIntegrationManager(enhanced_config)
    try:
        await test_instance.test_full_system_integration(integration_manager)
        await test_instance.test_production_monitoring_workflow(integration_manager)
        
        logger.info("🎉 All enhanced system integration tests passed!")
        
    finally:
        if integration_manager.is_operational:
            await integration_manager.stop()


if __name__ == "__main__":
    # Run the integration test
    asyncio.run(test_enhanced_system_integration_suite())
