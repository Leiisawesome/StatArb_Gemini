"""
Test suite for infrastructure components
"""
import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from new_structure.infrastructure import (
    ClickHouseClient,
    MetricsCollector,
    ConfigManager,
    MessageBus,
    Message
)
from tests.utils.test_helpers import (
    PerformanceMonitor,
    performance_test,
    DataValidation
)

class TestConfigManager:
    """Test configuration management"""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create base config
            base_config = {
                'database': {'host': 'localhost'},
                'monitoring': {'buffer_size': 1000}
            }
            
            import yaml
            with open(os.path.join(temp_dir, 'base_config.yaml'), 'w') as f:
                yaml.dump(base_config, f)
            
            yield temp_dir
    
    def test_config_initialization(self, temp_config_dir):
        """Test config manager initialization"""
        config = ConfigManager(config_dir=temp_config_dir)
        assert config is not None
        assert config.get_database_config()['host'] == 'localhost'
    
    def test_dynamic_settings(self, temp_config_dir):
        """Test dynamic settings functionality"""
        config = ConfigManager(config_dir=temp_config_dir)
        
        # Set dynamic setting
        config.update_dynamic_setting('test_key', 'test_value')
        assert config.get_dynamic_setting('test_key') == 'test_value'
        
        # Test default value
        assert config.get_dynamic_setting('missing_key', 'default') == 'default'

class TestMetricsCollector:
    """Test metrics collection system"""
    
    @pytest.fixture
    def metrics(self):
        """Create metrics collector instance"""
        return MetricsCollector()
    
    def test_latency_recording(self, metrics):
        """Test latency metric recording"""
        metrics.record_latency('test_operation', 100.5)
        
        # Allow some time for background processing
        import time
        time.sleep(0.1)
        
        stats = metrics.get_metric_statistics('test_operation')
        assert 'count' in stats
        assert 'mean' in stats
    
    def test_counter_increment(self, metrics):
        """Test counter metric functionality"""
        metrics.increment_counter('test_counter', 5)
        metrics.increment_counter('test_counter', 3)
        
        # Allow processing time
        import time
        time.sleep(0.1)
        
        # Counter should accumulate
        assert metrics._counters['test_counter'] >= 8
    
    def test_gauge_setting(self, metrics):
        """Test gauge metric functionality"""
        metrics.set_gauge('test_gauge', 42.5)
        
        # Allow processing time
        import time
        time.sleep(0.1)
        
        assert metrics._gauges['test_gauge'] == 42.5
    
    @performance_test(latency_threshold_ms=50)
    def test_metrics_performance(self, metrics):
        """Test metrics collection performance"""
        # Record multiple metrics rapidly
        for i in range(100):
            metrics.record_latency(f'operation_{i % 10}', i)
            metrics.increment_counter('bulk_counter')
            metrics.set_gauge('bulk_gauge', i)

class TestMessageBus:
    """Test messaging system"""
    
    @pytest.fixture
    def message_bus(self):
        """Create message bus instance"""
        bus = MessageBus()
        yield bus
        bus.shutdown()
    
    def test_message_publishing(self, message_bus):
        """Test message publishing"""
        message_id = message_bus.publish(
            'test_message',
            {'data': 'test'},
            source='test_source'
        )
        
        assert message_id is not None
        assert len(message_id) > 0
    
    def test_message_subscription(self, message_bus):
        """Test message subscription and delivery"""
        received_messages = []
        
        def callback(message: Message):
            received_messages.append(message)
        
        # Subscribe to messages
        message_bus.subscribe('test_type', callback)
        
        # Publish message
        message_bus.publish('test_type', {'test': 'data'})
        
        # Allow processing time
        import time
        time.sleep(0.1)
        
        assert len(received_messages) == 1
        assert received_messages[0].type == 'test_type'
        assert received_messages[0].payload['test'] == 'data'
    
    def test_ai_message_channel(self, message_bus):
        """Test AI-specific message channel"""
        received_messages = []
        
        def ai_callback(message: Message):
            received_messages.append(message)
        
        # Subscribe to AI channel
        message_bus.subscribe('ai_messages', ai_callback)
        
        # Publish AI message
        message_bus.publish_ai_message({'agent': 'test_agent', 'action': 'analyze'})
        
        # Allow processing time
        import time
        time.sleep(0.1)
        
        assert len(received_messages) == 1
        assert received_messages[0].source == 'ai_agent'

@pytest.mark.integration
class TestClickHouseClient:
    """Test ClickHouse database client"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing"""
        return {
            'host': 'localhost',
            'port': 9000,
            'database': 'test_db',
            'user': 'default',
            'password': '',
            'pool_size': 2
        }
    
    @patch('new_structure.infrastructure.database.clickhouse_client.Client')
    def test_client_initialization(self, mock_client_class, mock_config):
        """Test ClickHouse client initialization"""
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance
        
        client = ClickHouseClient(config=mock_config)
        
        assert client is not None
        assert len(client.connections) == mock_config['pool_size']
    
    @patch('new_structure.infrastructure.database.clickhouse_client.Client')
    def test_query_execution(self, mock_client_class, mock_config):
        """Test query execution"""
        mock_client_instance = Mock()
        mock_client_instance.execute.return_value = [(1, 'test')]
        mock_client_class.return_value = mock_client_instance
        
        client = ClickHouseClient(config=mock_config)
        result = client._execute_query("SELECT 1, 'test'")
        
        assert result == [(1, 'test')]
        mock_client_instance.execute.assert_called_once()

def test_infrastructure_integration():
    """Test integration between infrastructure components"""
    # Initialize all components
    config = ConfigManager()
    metrics = MetricsCollector()
    message_bus = MessageBus()
    
    # Test component interactions
    received_metrics = []
    
    def metrics_callback(message: Message):
        received_metrics.append(message)
    
    # Subscribe to metrics updates
    message_bus.subscribe('metrics_update', metrics_callback)
    
    # Record some metrics
    metrics.record_latency('integration_test', 50.0)
    
    # Publish metrics update
    message_bus.publish('metrics_update', {
        'metric': 'integration_test',
        'value': 50.0
    })
    
    # Allow processing
    import time
    time.sleep(0.1)
    
    # Verify integration
    assert len(received_metrics) == 1
    assert received_metrics[0].payload['metric'] == 'integration_test'
    
    # Cleanup
    message_bus.shutdown() 