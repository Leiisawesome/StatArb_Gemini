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

from .adapters import (
    IBKRAdapter
)

# Handle case where IBKRAdapter is not available (ibapi not installed)
if IBKRAdapter is None:
    # Create a placeholder class for documentation/testing
    class IBKRAdapter:
        """Placeholder IBKRAdapter - requires ibapi package for full functionality"""

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

    # Adapters
    'IBKRAdapter',

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