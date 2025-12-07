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

from .broker_manager import (
    BrokerManager,
    BrokerConfig
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