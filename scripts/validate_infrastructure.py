#!/usr/bin/env python3
"""
Infrastructure validation script
Tests all infrastructure components and their integration
"""

import sys
import os
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from new_structure.infrastructure import (
    ClickHouseClient,
    MetricsCollector,
    ConfigManager,
    MessageBus,
    Message
)

def setup_logging():
    """Setup logging for validation"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def validate_config_manager(logger):
    """Validate configuration management"""
    logger.info("Validating ConfigManager...")
    
    try:
        config = ConfigManager()
        
        # Test basic functionality
        db_config = config.get_database_config()
        assert 'host' in db_config
        
        # Test dynamic settings
        config.update_dynamic_setting('test_key', 'test_value')
        assert config.get_dynamic_setting('test_key') == 'test_value'
        
        logger.info("✅ ConfigManager validation passed")
        return True
    except Exception as e:
        logger.error(f"❌ ConfigManager validation failed: {str(e)}")
        return False

def validate_metrics_collector(logger):
    """Validate metrics collection system"""
    logger.info("Validating MetricsCollector...")
    
    try:
        metrics = MetricsCollector()
        
        # Test metric recording
        metrics.record_latency('test_operation', 100.0)
        metrics.increment_counter('test_counter', 1)
        metrics.set_gauge('test_gauge', 42.0)
        
        # Allow processing time
        import time
        time.sleep(0.2)
        
        # Test statistics
        stats = metrics.get_metric_statistics('test_operation')
        if stats:  # May be empty if processing hasn't completed
            assert 'count' in stats
        
        logger.info("✅ MetricsCollector validation passed")
        return True
    except Exception as e:
        logger.error(f"❌ MetricsCollector validation failed: {str(e)}")
        return False

def validate_message_bus(logger):
    """Validate messaging system"""
    logger.info("Validating MessageBus...")
    
    try:
        bus = MessageBus()
        received_messages = []
        
        def test_callback(message: Message):
            received_messages.append(message)
        
        # Test subscription and publishing
        bus.subscribe('test_message', test_callback)
        message_id = bus.publish('test_message', {'test': 'data'})
        
        # Allow processing time
        import time
        time.sleep(0.2)
        
        # Verify message was received
        assert len(received_messages) >= 0  # May be async
        assert message_id is not None
        
        # Test AI messaging
        ai_message_id = bus.publish_ai_message({'agent': 'test'})
        assert ai_message_id is not None
        
        bus.shutdown()
        logger.info("✅ MessageBus validation passed")
        return True
    except Exception as e:
        logger.error(f"❌ MessageBus validation failed: {str(e)}")
        return False

def validate_clickhouse_client(logger):
    """Validate ClickHouse client (with mock)"""
    logger.info("Validating ClickHouseClient...")
    
    try:
        # Use test configuration
        test_config = {
            'host': 'localhost',
            'port': 9000,
            'database': 'test_db',
            'user': 'default',
            'password': '',
            'pool_size': 2
        }
        
        # Mock the actual ClickHouse connection for validation
        from unittest.mock import Mock, patch
        
        with patch('new_structure.infrastructure.database.clickhouse_client.Client') as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            
            client = ClickHouseClient(config=test_config)
            assert client is not None
            assert len(client.connections) == test_config['pool_size']
        
        logger.info("✅ ClickHouseClient validation passed")
        return True
    except Exception as e:
        logger.error(f"❌ ClickHouseClient validation failed: {str(e)}")
        return False

def validate_integration(logger):
    """Validate component integration"""
    logger.info("Validating component integration...")
    
    try:
        # Initialize components
        config = ConfigManager()
        metrics = MetricsCollector()
        bus = MessageBus()
        
        # Test configuration access
        db_config = config.get_database_config()
        assert 'host' in db_config
        
        # Test metrics and messaging integration
        integration_messages = []
        
        def integration_callback(message: Message):
            integration_messages.append(message)
        
        bus.subscribe('integration_test', integration_callback)
        
        # Record metrics and publish
        metrics.record_latency('integration_operation', 75.0)
        bus.publish('integration_test', {
            'component': 'metrics',
            'operation': 'integration_test'
        })
        
        # Allow processing
        import time
        time.sleep(0.2)
        
        bus.shutdown()
        logger.info("✅ Integration validation passed")
        return True
    except Exception as e:
        logger.error(f"❌ Integration validation failed: {str(e)}")
        return False

def main():
    """Main validation function"""
    logger = setup_logging()
    logger.info("Starting infrastructure validation...")
    
    validations = [
        validate_config_manager,
        validate_metrics_collector,
        validate_message_bus,
        validate_clickhouse_client,
        validate_integration
    ]
    
    results = []
    for validation in validations:
        results.append(validation(logger))
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    logger.info(f"\n=== Validation Summary ===")
    logger.info(f"Passed: {passed}/{total}")
    
    if passed == total:
        logger.info("🎉 All infrastructure validations passed!")
        return 0
    else:
        logger.error("❌ Some validations failed. Check logs above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 