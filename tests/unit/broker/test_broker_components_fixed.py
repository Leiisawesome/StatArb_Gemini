"""
Comprehensive Broker Component Tests - Fixed Version
Tests for broker adapter, manager, connection manager, and message processor
"""

import pytest
from datetime import datetime


class TestBrokerAdapterEnums:
    """Test broker adapter enums"""
    
    def test_broker_type_enum(self):
        """Test BrokerType enum"""
        from core_engine.broker.broker_adapter import BrokerType
        
        assert BrokerType.INTERACTIVE_BROKERS.value == "interactive_brokers"
        assert BrokerType.ALPACA.value == "alpaca"
        assert BrokerType.TD_AMERITRADE.value == "td_ameritrade"
    
    def test_connection_status_enum(self):
        """Test ConnectionStatus enum"""
        from core_engine.broker.broker_adapter import ConnectionStatus
        
        assert ConnectionStatus.DISCONNECTED.value == "disconnected"
        assert ConnectionStatus.CONNECTING.value == "connecting"
        assert ConnectionStatus.CONNECTED.value == "connected"
        assert ConnectionStatus.AUTHENTICATED.value == "authenticated"
        assert ConnectionStatus.READY.value == "ready"
    
    def test_order_action_enum(self):
        """Test OrderAction enum"""
        from core_engine.broker.broker_adapter import OrderAction
        
        assert OrderAction.BUY.value == "BUY"
        assert OrderAction.SELL.value == "SELL"
        assert OrderAction.SHORT.value == "SHORT"
        assert OrderAction.COVER.value == "COVER"
    
    def test_order_type_enum(self):
        """Test OrderType enum"""
        from core_engine.broker.broker_adapter import OrderType
        
        assert OrderType.MARKET.value == "MKT"
        assert OrderType.LIMIT.value == "LMT"
        assert OrderType.STOP.value == "STP"
        assert OrderType.STOP_LIMIT.value == "STP_LMT"
    
    def test_time_in_force_enum(self):
        """Test TimeInForce enum"""
        from core_engine.broker.broker_adapter import TimeInForce
        
        assert TimeInForce.DAY.value == "DAY"
        assert TimeInForce.GTC.value == "GTC"
        assert TimeInForce.IOC.value == "IOC"
        assert TimeInForce.FOK.value == "FOK"


class TestBrokerManagerEnums:
    """Test broker manager enums"""
    
    def test_broker_status_enum(self):
        """Test BrokerStatus enum"""
        from core_engine.broker.broker_manager import BrokerStatus
        
        assert BrokerStatus.OFFLINE.value == "offline"
        assert BrokerStatus.CONNECTING.value == "connecting"
        assert BrokerStatus.ONLINE.value == "online"
        assert BrokerStatus.DEGRADED.value == "degraded"
        assert BrokerStatus.ERROR.value == "error"
        assert BrokerStatus.MAINTENANCE.value == "maintenance"
    
    def test_execution_venue_enum(self):
        """Test ExecutionVenue enum"""
        from core_engine.broker.broker_manager import ExecutionVenue
        
        assert ExecutionVenue.PRIMARY.value == "primary"
        assert ExecutionVenue.SECONDARY.value == "secondary"
        assert ExecutionVenue.DARK_POOL.value == "dark_pool"
        assert ExecutionVenue.ECN.value == "ecn"
        assert ExecutionVenue.SMART_ROUTING.value == "smart_routing"


class TestConnectionManagerEnums:
    """Test connection manager enums"""
    
    def test_connection_priority_enum(self):
        """Test ConnectionPriority enum"""
        from core_engine.broker.connection_manager import ConnectionPriority
        
        assert ConnectionPriority.PRIMARY.value == "primary"
        assert ConnectionPriority.SECONDARY.value == "secondary"
        assert ConnectionPriority.BACKUP.value == "backup"
        assert ConnectionPriority.EMERGENCY.value == "emergency"
    
    def test_failover_strategy_enum(self):
        """Test FailoverStrategy enum"""
        from core_engine.broker.connection_manager import FailoverStrategy
        
        assert FailoverStrategy.ROUND_ROBIN.value == "round_robin"
        assert FailoverStrategy.PRIORITY_BASED.value == "priority_based"
        assert FailoverStrategy.LOAD_BALANCED.value == "load_balanced"
        assert FailoverStrategy.MANUAL.value == "manual"
    
    def test_health_status_enum(self):
        """Test HealthStatus enum"""
        from core_engine.broker.connection_manager import HealthStatus
        
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.CRITICAL.value == "critical"


class TestMessageProcessorEnums:
    """Test message processor enums"""
    
    def test_processing_priority_enum(self):
        """Test ProcessingPriority enum"""
        from core_engine.broker.message_processor import ProcessingPriority
        
        assert ProcessingPriority.CRITICAL.value == "critical"
        assert ProcessingPriority.HIGH.value == "high"
        assert ProcessingPriority.NORMAL.value == "normal"
        assert ProcessingPriority.LOW.value == "low"
        assert ProcessingPriority.BACKGROUND.value == "background"
    
    def test_message_status_enum(self):
        """Test MessageStatus enum"""
        from core_engine.broker.message_processor import MessageStatus
        
        assert MessageStatus.PENDING.value == "pending"
        assert MessageStatus.PROCESSING.value == "processing"
        assert MessageStatus.PROCESSED.value == "processed"
        assert MessageStatus.FAILED.value == "failed"
        assert MessageStatus.REJECTED.value == "rejected"
    
    def test_transformation_type_enum(self):
        """Test TransformationType enum"""
        from core_engine.broker.message_processor import TransformationType
        
        assert TransformationType.NONE.value == "none"
        assert TransformationType.FORMAT_CONVERSION.value == "format_conversion"
        assert TransformationType.FIELD_MAPPING.value == "field_mapping"
        assert TransformationType.ENRICHMENT.value == "enrichment"
        assert TransformationType.VALIDATION.value == "validation"


class TestBrokerDataclasses:
    """Test broker dataclass creation"""
    
    def test_broker_credentials_minimal(self):
        """Test BrokerCredentials minimal creation"""
        from core_engine.broker.broker_adapter import BrokerCredentials, BrokerType
        
        creds = BrokerCredentials(
            broker_type=BrokerType.INTERACTIVE_BROKERS,
            api_key="test-key",
            secret_key="test-secret"
        )
        assert creds.api_key == "test-key"
        assert creds.secret_key == "test-secret"
    
    def test_broker_credentials_full(self):
        """Test BrokerCredentials full creation"""
        from core_engine.broker.broker_adapter import BrokerCredentials, BrokerType
        
        creds = BrokerCredentials(
            broker_type=BrokerType.ALPACA,
            api_key="test-key",
            secret_key="test-secret",
            account_id="test-account",
            paper_trading=True,
            sandbox_mode=True
        )
        assert creds.account_id == "test-account"
        assert creds.paper_trading is True
        assert creds.sandbox_mode is True
    
    def test_broker_config_creation(self):
        """Test BrokerConfig creation"""
        from core_engine.broker.broker_manager import BrokerConfig, ExecutionVenue
        
        # Test with defaults (uses default_factory)
        config = BrokerConfig()
        assert config.default_venue == ExecutionVenue.SMART_ROUTING
        assert config.enable_smart_routing is True
        assert config.enable_pre_trade_risk is True
    
    def test_broker_info_creation(self):
        """Test BrokerInfo creation"""
        from core_engine.broker.broker_manager import BrokerInfo, BrokerStatus
        from core_engine.broker.broker_adapter import BrokerType
        
        info = BrokerInfo(
            broker_id="test-broker",
            broker_type=BrokerType.INTERACTIVE_BROKERS,
            name="Test Broker",
            status=BrokerStatus.ONLINE
        )
        assert info.broker_id == "test-broker"
        assert info.broker_type == BrokerType.INTERACTIVE_BROKERS
        assert info.status == BrokerStatus.ONLINE
    
    def test_order_request_creation(self):
        """Test OrderRequest creation"""
        from core_engine.broker.broker_manager import OrderRequest
        from core_engine.broker.broker_adapter import OrderAction, OrderType
        
        request = OrderRequest(
            request_id="req-123",
            symbol="AAPL",
            action=OrderAction.BUY,
            quantity=100,
            order_type=OrderType.MARKET
        )
        assert request.request_id == "req-123"
        assert request.symbol == "AAPL"
        assert request.action == OrderAction.BUY
        assert request.quantity == 100
    
    def test_execution_report_creation(self):
        """Test ExecutionReport creation"""
        from core_engine.broker.broker_manager import ExecutionReport
        
        now = datetime.now()
        report = ExecutionReport(
            execution_id="exec-123",
            order_request_id="req-456",
            broker_id="broker-789",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            price=150.0,
            execution_time=now
        )
        assert report.execution_id == "exec-123"
        assert report.order_request_id == "req-456"
        assert report.symbol == "AAPL"
        assert report.side == "BUY"
        assert report.quantity == 100
    
    def test_connection_config_creation(self):
        """Test ConnectionConfig creation"""
        from core_engine.broker.connection_manager import ConnectionConfig, FailoverStrategy
        
        config = ConnectionConfig()
        assert config.max_connections == 10
        assert config.connection_timeout == 30.0
        assert config.failover_strategy == FailoverStrategy.PRIORITY_BASED
        
        custom = ConnectionConfig(max_connections=20, heartbeat_interval=15.0)
        assert custom.max_connections == 20
        assert custom.heartbeat_interval == 15.0
    
    def test_processing_config_creation(self):
        """Test ProcessingConfig creation"""
        from core_engine.broker.message_processor import ProcessingConfig
        
        config = ProcessingConfig()
        assert config.max_queue_size == 10000
        assert config.batch_size == 100
        assert config.worker_count == 4
        
        custom = ProcessingConfig(batch_size=50, worker_count=8)
        assert custom.batch_size == 50
        assert custom.worker_count == 8


class TestBrokerIntegration:
    """Test broker component integration"""
    
    def test_order_request_with_execution_venue(self):
        """Test order request with specific execution venue"""
        from core_engine.broker.broker_manager import OrderRequest, ExecutionVenue
        from core_engine.broker.broker_adapter import OrderAction, OrderType
        
        request = OrderRequest(
            request_id="req-123",
            symbol="AAPL",
            action=OrderAction.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            limit_price=150.0,
            venue=ExecutionVenue.DARK_POOL
        )
        assert request.venue == ExecutionVenue.DARK_POOL
        assert request.limit_price == 150.0
    
    def test_broker_info_with_capabilities(self):
        """Test BrokerInfo with capabilities"""
        from core_engine.broker.broker_manager import BrokerInfo, BrokerStatus, ExecutionVenue
        from core_engine.broker.broker_adapter import BrokerType, OrderType
        
        info = BrokerInfo(
            broker_id="test-broker",
            broker_type=BrokerType.ALPACA,
            name="Alpaca",
            status=BrokerStatus.ONLINE,
            supported_order_types=[OrderType.MARKET, OrderType.LIMIT],
            supported_venues=[ExecutionVenue.PRIMARY, ExecutionVenue.SMART_ROUTING]
        )
        assert len(info.supported_order_types) == 2
        assert len(info.supported_venues) == 2
    
    def test_connection_config_with_failover(self):
        """Test connection config with failover settings"""
        from core_engine.broker.connection_manager import ConnectionConfig, FailoverStrategy
        
        config = ConnectionConfig(
            failover_strategy=FailoverStrategy.LOAD_BALANCED,
            failover_threshold=0.7,
            recovery_threshold=0.3
        )
        assert config.failover_strategy == FailoverStrategy.LOAD_BALANCED
        assert config.failover_threshold == 0.7
        assert config.recovery_threshold == 0.3


class TestImportPaths:
    """Test that all broker components are importable"""
    
    def test_broker_adapter_imports(self):
        """Test broker adapter imports"""
        from core_engine.broker.broker_adapter import (
            BrokerAdapter, BrokerType
        )
        assert BrokerAdapter is not None
        assert BrokerType is not None
    
    def test_broker_manager_imports(self):
        """Test broker manager imports"""
        from core_engine.broker.broker_manager import (
            BrokerManager, BrokerStatus
        )
        assert BrokerManager is not None
        assert BrokerStatus is not None
    
    def test_connection_manager_imports(self):
        """Test connection manager imports"""
        from core_engine.broker.connection_manager import (
            ConnectionManager, ConnectionPriority
        )
        assert ConnectionManager is not None
        assert ConnectionPriority is not None
    
    def test_message_processor_imports(self):
        """Test message processor imports"""
        from core_engine.broker.message_processor import (
            MessageProcessor, ProcessingPriority
        )
        assert MessageProcessor is not None
        assert ProcessingPriority is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
