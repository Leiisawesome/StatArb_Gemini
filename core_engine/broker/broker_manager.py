"""
Broker Engine - Broker Manager
Simplified broker management with basic adapter lifecycle management

**Rule 1 Section 7:** Uses centralized BrokerConfig from core_engine.config
**Rule 2:** Implements ISystemComponent and IRegimeAware for orchestrator integration
"""

import logging
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .broker_adapter import (
    BrokerAdapter, BrokerCredentials, BrokerType
)

# Import ISystemComponent and IRegimeAware (Rule 2 - Hierarchical Architecture)
try:
    from ..system.interfaces import ISystemComponent, IRegimeAware, RegimeContext
    INTERFACES_AVAILABLE = True
except ImportError:
    INTERFACES_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("ISystemComponent/IRegimeAware not available - using fallback")

    # Fallback definitions
    class ISystemComponent:
        async def initialize(self) -> bool: pass
        async def start(self) -> bool: pass
        async def stop(self) -> bool: pass
        async def health_check(self) -> Dict[str, Any]: pass
        def get_status(self) -> Dict[str, Any]: pass

    class IRegimeAware:
        def set_regime_engine(self, regime_engine: Any) -> None: pass
        async def on_regime_change(self, new_regime_context: Any) -> None: pass
        def get_current_regime_context(self) -> Optional[Any]: pass
        async def adapt_to_regime(self, regime_context: Any) -> Dict[str, Any]: pass
        def validate_regime_dependency(self) -> bool: pass

    from dataclasses import dataclass
    @dataclass
    class RegimeContext:
        primary_regime: str = "unknown"
        regime_confidence: float = 0.5

# Import centralized configuration (Rule 1 Section 7 - Configuration Management)
try:
    from ..config import BrokerConfig as CentralizedBrokerConfig
    CENTRALIZED_CONFIG_AVAILABLE = True
except ImportError:
    CENTRALIZED_CONFIG_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Centralized BrokerConfig not available, using local config")

import warnings
warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)
import uuid


@dataclass
class BrokerConfig:
    """Broker manager configuration"""
    # Basic settings
    enable_performance_monitoring: bool = True
    metrics_collection_interval: float = 60.0


class BrokerManager(ISystemComponent, IRegimeAware):
    """
    Simplified Broker Manager with ISystemComponent and IRegimeAware Integration

    Manages broker adapters with basic lifecycle management.

    **Rule 1 Section 7:** Uses centralized BrokerConfig from core_engine.config
    **Rule 2:** Implements ISystemComponent for orchestrator integration
    **Rule 2:** Implements IRegimeAware for regime-adaptive broker operations
    """

    def __init__(self, config: Optional[Any] = None):
        """
        Initialize broker manager

        Args:
            config: BrokerConfig instance, dict, or None (uses centralized config if available)
        """

        # ================================================================
        # Configuration Management (Rule 1 Section 7)
        # ================================================================

        if CENTRALIZED_CONFIG_AVAILABLE and (config is None or isinstance(config, dict)):
            # Use centralized configuration
            if config is None:
                self.centralized_config = CentralizedBrokerConfig()
            elif isinstance(config, dict):
                # Convert dict to centralized config
                self.centralized_config = CentralizedBrokerConfig(**{
                    k: v for k, v in config.items()
                    if hasattr(CentralizedBrokerConfig, k)
                })

            # Map centralized config to local BrokerConfig for backward compatibility
            self.config = BrokerConfig()
            logger.info("✅ Using centralized BrokerConfig (Rule 1 Section 7)")

        elif isinstance(config, CentralizedBrokerConfig if CENTRALIZED_CONFIG_AVAILABLE else type(None)):
            # Direct centralized config instance
            self.centralized_config = config
            self.config = BrokerConfig()
            logger.info("✅ Using centralized BrokerConfig (Rule 1 Section 7)")

        else:
            # Fallback to local config
            self.config = config if isinstance(config, BrokerConfig) else BrokerConfig()
            self.centralized_config = None
            if not CENTRALIZED_CONFIG_AVAILABLE:
                logger.debug("Using local BrokerConfig (centralized config not available)")

        # ================================================================
        # ISystemComponent State Management
        # ================================================================

        self.is_initialized: bool = False
        self.is_operational: bool = False
        self.component_id: Optional[str] = None
        self.component_name: str = "BrokerManager"
        self.orchestrator: Optional[Any] = None

        # ================================================================
        # IRegimeAware State Management (Rule 2 - Regime-First)
        # ================================================================

        self.regime_engine: Optional[Any] = None
        self.current_regime_context: Optional[RegimeContext] = None
        logger.info("✅ BrokerManager implements ISystemComponent and IRegimeAware (Rule 2)")

        # ================================================================
        # Core Broker Manager Components
        # ================================================================

        # Simple broker adapter storage
        self._broker_adapters: Dict[str, BrokerAdapter] = {}

        # Lock for thread safety
        self._lock = threading.RLock()

        logger.info("Broker manager initialized")

    # ================================================================
    # ISystemComponent Implementation (Rule 2 - Hierarchical Architecture)
    # ================================================================

    async def initialize(self) -> bool:
        """
        Initialize broker manager component

        Returns:
            bool: True if initialization successful
        """
        try:
            with self._lock:
                if self.is_initialized:
                    logger.warning("BrokerManager already initialized")
                    return True

                logger.info("Initializing BrokerManager...")

                # Initialize broker adapters
                for adapter in self._broker_adapters.values():
                    if hasattr(adapter, 'initialize'):
                        await adapter.initialize()

                self.is_initialized = True
                logger.info("✅ BrokerManager initialized successfully")

                return True

        except Exception as e:
            logger.error(f"Failed to initialize BrokerManager: {e}")
            return False

    async def start(self) -> bool:
        """
        Start broker manager component

        Returns:
            bool: True if startup successful
        """
        try:
            with self._lock:
                if not self.is_initialized:
                    logger.error("BrokerManager not initialized")
                    return False

                if self.is_operational:
                    logger.warning("BrokerManager already operational")
                    return True

                logger.info("Starting BrokerManager...")

                # Start broker adapters
                for adapter in self._broker_adapters.values():
                    if hasattr(adapter, 'start'):
                        await adapter.start()

                self.is_operational = True
                logger.info("✅ BrokerManager started successfully")

                return True

        except Exception as e:
            logger.error(f"Failed to start BrokerManager: {e}")
            return False

    async def stop(self) -> bool:
        """
        Stop broker manager component

        Returns:
            bool: True if shutdown successful
        """
        try:
            with self._lock:
                if not self.is_operational:
                    logger.warning("BrokerManager not operational")
                    return True

                logger.info("Stopping BrokerManager...")

                # Stop broker adapters
                for adapter in self._broker_adapters.values():
                    if hasattr(adapter, 'stop'):
                        await adapter.stop()

                self.is_operational = False
                logger.info("✅ BrokerManager stopped successfully")

                return True

        except Exception as e:
            logger.error(f"Failed to stop BrokerManager: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check

        Returns:
            Dict[str, Any]: Health check results
        """
        try:
            with self._lock:
                health_status = {
                    'component': self.component_name,
                    'status': 'healthy' if self.is_operational else 'stopped',
                    'initialized': self.is_initialized,
                    'operational': self.is_operational,
                    'broker_count': len(self._broker_adapters),
                    'timestamp': datetime.now().isoformat()
                }

                # Check broker adapter health
                adapter_health = {}
                for broker_id, adapter in self._broker_adapters.items():
                    if hasattr(adapter, 'health_check'):
                        adapter_health[broker_id] = await adapter.health_check()
                    else:
                        adapter_health[broker_id] = {'status': 'unknown'}

                health_status['broker_adapters'] = adapter_health

                return health_status

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'component': self.component_name,
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def get_status(self) -> Dict[str, Any]:
        """
        Get component status

        Returns:
            Dict[str, Any]: Component status
        """
        return {
            'component_id': self.component_id,
            'component_name': self.component_name,
            'is_initialized': self.is_initialized,
            'is_operational': self.is_operational,
            'broker_count': len(self._broker_adapters)
        }

    # ================================================================
    # IRegimeAware Implementation (Rule 2 - Regime-First Architecture)
    # ================================================================

    def set_regime_engine(self, regime_engine: Any) -> None:
        """
        Set regime engine reference

        Args:
            regime_engine: Regime engine instance
        """
        self.regime_engine = regime_engine
        logger.info("✅ BrokerManager regime engine configured")

    async def on_regime_change(self, new_regime_context: RegimeContext) -> None:
        """
        Handle regime change

        Args:
            new_regime_context: New regime context
        """
        self.current_regime_context = new_regime_context
        logger.info(f"BrokerManager adapting to regime: {new_regime_context.primary_regime}")

    def get_current_regime_context(self) -> Optional[RegimeContext]:
        """
        Get current regime context

        Returns:
            Optional[RegimeContext]: Current regime context
        """
        return self.current_regime_context

    async def adapt_to_regime(self, regime_context: RegimeContext) -> Dict[str, Any]:
        """
        Adapt broker operations to regime

        Args:
            regime_context: Regime context

        Returns:
            Dict[str, Any]: Adaptation results
        """
        # Simple regime adaptation - could be extended based on regime
        adaptation = {
            'regime': regime_context.primary_regime,
            'confidence': regime_context.regime_confidence,
            'actions_taken': []
        }

        logger.info(f"BrokerManager adapted to regime: {regime_context.primary_regime}")
        return adaptation

    def validate_regime_dependency(self) -> bool:
        """
        Validate regime engine dependency

        Returns:
            bool: True if regime engine configured
        """
        has_regime_engine = self.regime_engine is not None

        if has_regime_engine:
            logger.debug("✅ BrokerManager regime dependency validated")
        else:
            logger.warning("⚠️  BrokerManager regime engine not configured")

        return has_regime_engine

    # ================================================================
    # Simplified Broker Management Methods
    # ================================================================

    async def add_broker(self, broker_type: BrokerType, credentials: BrokerCredentials,
                        name: Optional[str] = None) -> str:
        """
        Add broker adapter to manager

        Args:
            broker_type: Type of broker
            credentials: Broker credentials
            name: Optional broker name

        Returns:
            str: Broker ID
        """
        try:
            with self._lock:
                # Generate broker ID
                broker_id = f"{broker_type.value}_{uuid.uuid4().hex[:8]}"

                # Create broker adapter
                broker_adapter = BrokerAdapter(credentials)
                self._broker_adapters[broker_id] = broker_adapter

                logger.info(f"Added broker {broker_id} ({broker_type.value})")
                return broker_id

        except Exception as e:
            logger.error(f"Failed to add broker: {e}")
            raise

    async def remove_broker(self, broker_id: str) -> bool:
        """
        Remove broker adapter from manager

        Args:
            broker_id: Broker ID to remove

        Returns:
            bool: True if removed successfully
        """
        try:
            with self._lock:
                if broker_id not in self._broker_adapters:
                    logger.warning(f"Broker {broker_id} not found")
                    return False

                # Stop adapter if operational
                adapter = self._broker_adapters[broker_id]
                if hasattr(adapter, 'stop'):
                    await adapter.stop()

                # Remove adapter
                del self._broker_adapters[broker_id]

                logger.info(f"Removed broker {broker_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to remove broker {broker_id}: {e}")
            return False

    def get_broker(self, broker_id: str) -> Optional[BrokerAdapter]:
        """
        Get broker adapter by ID

        Args:
            broker_id: Broker ID

        Returns:
            Optional[BrokerAdapter]: Broker adapter or None
        """
        return self._broker_adapters.get(broker_id)

    def list_brokers(self) -> List[str]:
        """
        List all broker IDs

        Returns:
            List[str]: List of broker IDs
        """
        with self._lock:
            return list(self._broker_adapters.keys())

    def get_broker_count(self) -> int:
        """
        Get number of brokers

        Returns:
            int: Number of brokers
        """
        return len(self._broker_adapters)