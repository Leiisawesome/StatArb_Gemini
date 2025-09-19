"""
Broker Engine Package
Comprehensive multi-broker connectivity and execution management
"""

from .broker_adapter import (
    BrokerAdapter,
    BrokerCredentials, 
    BrokerType,
    ConnectionStatus,
    StandardOrder,
    StandardExecution,
    StandardPosition,
    StandardAccount,
    OrderAction,
    OrderType,
    TimeInForce
)

from .connection_manager import (
    ConnectionManager,
    ConnectionConfig,
    ConnectionPriority,
    ConnectionPool,
    ConnectionMonitor
)

from .protocol_handler import (
    ProtocolHandler,
    ProtocolConfig,
    ProtocolType,
    MessageType,
    FIXProtocolHandler,
    RESTProtocolHandler,
    WebSocketProtocolHandler
)

from .message_processor import (
    MessageProcessor,
    ProcessingConfig,
    ProcessingPriority,
    MessageTransformer,
    MessageRouter
)

from .session_manager import (
    SessionManager,
    SessionConfig,
    SessionType,
    SessionAuthenticator,
    AuthenticationRequest
)

from .broker_manager import (
    BrokerManager,
    BrokerConfig,
    BrokerInfo,
    BrokerStatus,
    ExecutionVenue,
    OrderRequest,
    ExecutionReport,
    BrokerSelector,
    OrderRouter
)

__all__ = [
    # Broker Adapter
    'BrokerAdapter',
    'BrokerCredentials',
    'BrokerType',
    'ConnectionStatus',
    'StandardOrder',
    'StandardExecution',
    'StandardPosition',
    'StandardAccount',
    'OrderAction',
    'OrderType',
    'TimeInForce',
    
    # Connection Manager
    'ConnectionManager',
    'ConnectionConfig',
    'ConnectionPriority',
    'ConnectionPool',
    'ConnectionMonitor',
    
    # Protocol Handler
    'ProtocolHandler',
    'ProtocolConfig',
    'ProtocolType',
    'MessageType',
    'FIXProtocolHandler',
    'RESTProtocolHandler',
    'WebSocketProtocolHandler',
    
    # Message Processor
    'MessageProcessor',
    'ProcessingConfig',
    'ProcessingPriority',
    'MessageTransformer',
    'MessageRouter',
    
    # Session Manager
    'SessionManager',
    'SessionConfig',
    'SessionType',
    'SessionAuthenticator',
    'AuthenticationRequest',
    
    # Broker Manager
    'BrokerManager',
    'BrokerConfig',
    'BrokerInfo',
    'BrokerStatus',
    'ExecutionVenue',
    'OrderRequest',
    'ExecutionReport',
    'BrokerSelector',
    'OrderRouter'
]

__version__ = "1.0.0"
__author__ = "StatArb Gemini Team"
__description__ = "Institutional-grade multi-broker connectivity and execution management engine"