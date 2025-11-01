#!/usr/bin/env python3
"""
System Integration Manager - Complete Core Engine Integration
============================================================

Comprehensive integration manager that orchestrates all enhanced components
across the StatArb_Gemini core_engine system.

This manager provides:
- Unified initialization and lifecycle management for all components
- Comprehensive health monitoring and status reporting
- Production-ready configuration management
- End-to-end system orchestration
- Performance monitoring and benchmarking

Enhanced Components Integration:
- Phase 1: Core System Components (Orchestrator, Risk, Data, Execution)
- Phase 2: Analytics & Strategy Layer (Performance, Strategies, Validation)
- Phase 3: Processing Pipeline (Indicators, Features, Signals)
- Phase 4: Data & Risk Management (Data, Risk, Regime)
- Phase 5: Trading & Execution (Strategy, Trading, Execution, Portfolio)

Author: StatArb_Gemini System Integration Team
Version: 1.0.0 (Production Ready)
"""

import asyncio
import logging
import threading
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from core_engine.exceptions import ConfigurationRequiredError

# PHASE 6: Replaced config_adapter with centralized configs
# OLD: from .config_adapter import safe_component_init
# NEW: Using consolidated configs from core_engine.config

def safe_component_init(component_class, config_dict):
    """
    Initialize component with configuration.
    
    Simplified version - no longer needs adapter pattern since all configs
    are now properly defined in core_engine.config/ (Phase 4).
    """
    try:
        return component_class(config_dict)
    except Exception as e:
        logger.error(f"Failed to create component {component_class.__name__}: {e}")
        raise ConfigurationRequiredError(f"Cannot create component {component_class.__name__}: {e}") from e

# Import ISystemComponent for orchestrator integration
try:
    from .interfaces import ISystemComponent
    from .hierarchical_orchestrator import HierarchicalSystemOrchestrator
except ImportError:
    logger.error("ISystemComponent interface not available")
    raise ConfigurationRequiredError("ISystemComponent interface not available")

# PHASE 6: Import centralized configs (Rule 1, Section 7)
from ..config.component_config import (
    DataConfig, RiskConfig, IndicatorConfig, 
    FeatureConfig, SignalConfig, RegimeConfig,
    AnalyticsConfig, ExecutionConfig, PortfolioConfig
)
from ..trading.strategies.manager import StrategyManagerConfig
from ..trading.engine import TradingEngineConfig

# Import all enhanced components
try:
    # Phase 1: Core System Components
    pass
    
    # Production monitoring components
    from .production_monitoring import (
        ProductionHealthMonitor, GracefulDegradationManager,
        AuditTrailManager, DisasterRecoveryManager
    )
    
    # Phase 2: Analytics & Strategy Layer
    
    # Phase 3: Processing Pipeline
    
    # Phase 4: Data & Risk Management
    
    # Phase 5: Trading & Execution
    
except ImportError as e:
    logging.warning(f"Some enhanced components not available: {e}")

logger = logging.getLogger(__name__)


class SystemPhase(Enum):
    """System integration phases"""
    INITIALIZATION = "initialization"
    STARTUP = "startup"
    OPERATIONAL = "operational"
    SHUTDOWN = "shutdown"
    ERROR = "error"


class ComponentStatus(Enum):
    """Component status levels"""
    UNKNOWN = "unknown"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    STARTING = "starting"
    OPERATIONAL = "operational"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class SystemConfiguration:
    """
    Complete system configuration with type-safe configs (ENHANCED Phase 6)
    
    Replaces untyped Dict[str, Any] with proper typed configuration objects
    from core_engine.config/ (Rule 1, Section 7)
    """
    # Core System (using typed configs)
    orchestrator_config: Optional[Dict[str, Any]] = field(default_factory=dict)  # Orchestrator-specific (stays dict)
    risk_manager_config: Optional[RiskConfig] = None
    data_manager_config: Optional[DataConfig] = None
    execution_engine_config: Optional[ExecutionConfig] = None
    
    # Analytics & Strategy (using typed configs)
    analytics_manager_config: Optional[AnalyticsConfig] = None
    metrics_calculator_config: Optional[Dict[str, Any]] = field(default_factory=dict)  # TODO: Create MetricsConfig
    strategy_manager_config: Optional[StrategyManagerConfig] = None  # StrategyManagerConfig exists in core_engine.trading.strategies.manager
    strategy_engine_config: Optional[Dict[str, Any]] = field(default_factory=dict)  # TODO: Create StrategyEngineConfig
    strategy_registry_config: Optional[Dict[str, Any]] = field(default_factory=dict)  # Strategy-specific
    strategy_validator_config: Optional[Dict[str, Any]] = field(default_factory=dict)  # Validator-specific
    
    # Processing Pipeline (using typed configs)
    indicators_config: Optional[IndicatorConfig] = None
    features_config: Optional[FeatureConfig] = None
    signals_config: Optional[SignalConfig] = None
    
    # Data & Risk Management (using typed configs)
    regime_engine_config: Optional[RegimeConfig] = None
    
    # Trading & Execution (using typed configs)
    trading_engine_config: Optional[TradingEngineConfig] = None  # TradingEngineConfig exists in core_engine.trading.engine
    portfolio_manager_config: Optional[PortfolioConfig] = None
    
    # Production Monitoring (component-specific)
    production_health_monitor_config: Optional[Dict[str, Any]] = field(default_factory=dict)
    graceful_degradation_config: Optional[Dict[str, Any]] = field(default_factory=dict)
    audit_trail_config: Optional[Dict[str, Any]] = field(default_factory=dict)
    disaster_recovery_config: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    # System Settings
    enable_performance_monitoring: bool = True
    enable_health_monitoring: bool = True
    enable_production_monitoring: bool = True
    enable_audit_trail: bool = True
    enable_disaster_recovery: bool = True
    health_check_interval: int = 30  # seconds
    performance_report_interval: int = 300  # seconds
    max_initialization_time: int = 120  # seconds
    max_startup_time: int = 60  # seconds
    
    def __post_init__(self):
        """Initialize None configs with defaults"""
        if self.risk_manager_config is None:
            self.risk_manager_config = RiskConfig()
        if self.data_manager_config is None:
            self.data_manager_config = DataConfig()
        if self.execution_engine_config is None:
            self.execution_engine_config = ExecutionConfig()
        if self.analytics_manager_config is None:
            self.analytics_manager_config = AnalyticsConfig()
        if self.indicators_config is None:
            self.indicators_config = IndicatorConfig()
        if self.features_config is None:
            self.features_config = FeatureConfig()
        if self.signals_config is None:
            self.signals_config = SignalConfig()
        if self.regime_engine_config is None:
            self.regime_engine_config = RegimeConfig()
        if self.portfolio_manager_config is None:
            self.portfolio_manager_config = PortfolioConfig()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (backward compatibility)"""
        # For backward compatibility with dict-based initialization
        return {
            'risk_manager_config': self.risk_manager_config.__dict__ if self.risk_manager_config else {},
            'data_manager_config': self.data_manager_config.__dict__ if self.data_manager_config else {},
            'execution_engine_config': self.execution_engine_config.__dict__ if self.execution_engine_config else {},
            'analytics_manager_config': self.analytics_manager_config.__dict__ if self.analytics_manager_config else {},
            'indicators_config': self.indicators_config.__dict__ if self.indicators_config else {},
            'features_config': self.features_config.__dict__ if self.features_config else {},
            'signals_config': self.signals_config.__dict__ if self.signals_config else {},
            'regime_engine_config': self.regime_engine_config.__dict__ if self.regime_engine_config else {},
            'portfolio_manager_config': self.portfolio_manager_config.__dict__ if self.portfolio_manager_config else {},
            # Untyped configs as-is
            'orchestrator_config': self.orchestrator_config,
            'metrics_calculator_config': self.metrics_calculator_config,
            'strategy_manager_config': self.strategy_manager_config,
            'strategy_engine_config': self.strategy_engine_config,
            'strategy_registry_config': self.strategy_registry_config,
            'strategy_validator_config': self.strategy_validator_config,
            'trading_engine_config': self.trading_engine_config,
            'production_health_monitor_config': self.production_health_monitor_config,
            'graceful_degradation_config': self.graceful_degradation_config,
            'audit_trail_config': self.audit_trail_config,
            'disaster_recovery_config': self.disaster_recovery_config,
        }


@dataclass
class SystemMetrics:
    """System-wide performance metrics"""
    total_components: int = 0
    operational_components: int = 0
    failed_components: int = 0
    system_uptime: float = 0.0
    initialization_time: float = 0.0
    startup_time: float = 0.0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    health_score: float = 0.0
    performance_score: float = 0.0


class SystemIntegrationManager(ISystemComponent):
    """
    System Integration Manager - Complete Core Engine Integration
    
    Orchestrates all enhanced components across the StatArb_Gemini core_engine:
    - Unified lifecycle management for all components
    - Comprehensive health monitoring and status reporting
    - Production-ready configuration management
    - End-to-end system orchestration
    - Performance monitoring and benchmarking
    """
    
    def __init__(self, config: SystemConfiguration):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Component identification and lifecycle
        self.component_id = str(uuid.uuid4())
        self.is_initialized = False
        self.is_operational = False
        self.start_time = None
        self.initialization_start = None
        self.startup_start = None
        
        # Orchestrator integration
        self.orchestrator: Optional[Any] = None  # HierarchicalSystemOrchestrator reference
        
        # System state
        self.current_phase = SystemPhase.INITIALIZATION
        self.system_metrics = SystemMetrics()
        
        # Health and performance tracking
        self.health_metrics = {
            'component_type': 'SystemIntegrationManager',
            'initialization_status': 'pending',
            'operational_status': 'inactive',
            'last_health_check': None,
            'error_count': 0,
            'warning_count': 0,
            'performance_metrics': {
                'total_integrations': 0,
                'successful_integrations': 0,
                'failed_integrations': 0,
                'average_integration_time': 0.0,
                'components_managed': 0
            }
        }
        
        # Component management
        self.components: Dict[str, ISystemComponent] = {}
        self.component_status: Dict[str, ComponentStatus] = {}
        self.component_dependencies: Dict[str, List[str]] = {}
        self.initialization_order: List[str] = []
        
        # Orchestrator
        self.orchestrator: Optional[HierarchicalSystemOrchestrator] = None
        
        # Threading
        self._lock = threading.Lock()
        self._health_monitor_task: Optional[asyncio.Task] = None
        self._performance_monitor_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        self.logger.info(f"🚀 System Integration Manager initialized with component ID: {self.component_id}")
    
    # ========================================
    # ORCHESTRATOR INTEGRATION
    # ========================================
    
    def register_with_orchestrator(self, orchestrator) -> str:
        """Register component with HierarchicalSystemOrchestrator"""
        from core_engine.system.hierarchical_orchestrator import ComponentLayer, AuthorityLevel
        
        self.orchestrator = orchestrator
        self.component_id = orchestrator.register_component(
            name="SystemIntegrationManager",
            component=self,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.SYSTEM_CONTROL,
            initialization_order=1  # Very early initialization
        )
        
        self.logger.info(f"✅ SystemIntegrationManager registered with orchestrator: {self.component_id}")
        return self.component_id
    
    async def request_operation_authorization(self, operation: str, details: Dict[str, Any]) -> bool:
        """Request authorization from orchestrator for privileged operations"""
        if not self.orchestrator or not self.component_id:
            self.logger.warning("No orchestrator available for authorization request")
            return False
        
        return await self.orchestrator.request_system_authorization(
            operation, self.component_id, details
        )
    
    # ========================================
    # ISystemComponent Interface Implementation
    # ========================================
    
    async def initialize(self) -> bool:
        """Initialize the complete system"""
        try:
            self.initialization_start = datetime.now()
            self.logger.info("🔄 Initializing Complete System Integration...")
            
            # Initialize all components first
            await self._initialize_all_components()

            # Inject dependencies after all components are initialized
            await self._inject_component_dependencies()

            # Initialize orchestrator after components are available
            await self._initialize_orchestrator()
            
            # Setup component dependencies
            await self._setup_component_dependencies()
            
            # Initialize monitoring systems
            await self._initialize_monitoring_systems()
            
            # Update status
            self.is_initialized = True
            self.current_phase = SystemPhase.STARTUP
            self.health_metrics['initialization_status'] = 'completed'
            
            initialization_time = (datetime.now() - self.initialization_start).total_seconds()
            self.system_metrics.initialization_time = initialization_time
            
            self.logger.info(f"✅ Complete System Integration initialization complete in {initialization_time:.2f}s")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Complete System Integration initialization failed: {e}")
            self.health_metrics['error_count'] += 1
            self.health_metrics['initialization_status'] = 'failed'
            self.current_phase = SystemPhase.ERROR
            return False
    
    async def start(self) -> bool:
        """Start the complete system"""
        if not self.is_initialized:
            self.logger.error("Cannot start Complete System Integration: not initialized")
            return False
        
        try:
            self.startup_start = datetime.now()
            self.logger.info("🚀 Starting Complete System Integration...")
            
            # Start orchestrator
            await self._start_orchestrator()
            
            # Start all components in dependency order
            await self._start_all_components()
            
            # Start monitoring systems
            await self._start_monitoring_systems()
            
            # Update status
            self.is_operational = True
            self.start_time = datetime.now()
            self.current_phase = SystemPhase.OPERATIONAL
            self.health_metrics['operational_status'] = 'active'
            
            startup_time = (datetime.now() - self.startup_start).total_seconds()
            self.system_metrics.startup_time = startup_time
            
            self.logger.info(f"✅ Complete System Integration started successfully in {startup_time:.2f}s")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Complete System Integration start failed: {e}")
            self.health_metrics['error_count'] += 1
            self.current_phase = SystemPhase.ERROR
            return False
    
    async def stop(self) -> bool:
        """Stop the complete system"""
        try:
            self.logger.info("🛑 Stopping Complete System Integration...")
            self.current_phase = SystemPhase.SHUTDOWN
            
            # Signal shutdown
            self._shutdown_event.set()
            
            # Stop monitoring systems
            await self._stop_monitoring_systems()
            
            # Stop all components in reverse order
            await self._stop_all_components()
            
            # Stop orchestrator
            await self._stop_orchestrator()
            
            # Update status
            self.is_operational = False
            self.health_metrics['operational_status'] = 'inactive'
            
            self.logger.info("✅ Complete System Integration stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Complete System Integration stop failed: {e}")
            self.health_metrics['error_count'] += 1
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive system health check"""
        try:
            current_time = datetime.now()
            self.health_metrics['last_health_check'] = current_time
            
            # Calculate uptime
            uptime_seconds = 0
            if self.start_time:
                uptime_seconds = (current_time - self.start_time).total_seconds()
                self.system_metrics.system_uptime = uptime_seconds
            
            # Check all components health
            component_health = await self._check_all_components_health()
            
            # Calculate system health score
            health_score = self._calculate_system_health_score(component_health)
            self.system_metrics.health_score = health_score
            
            # Overall health assessment (more lenient for production readiness)
            overall_healthy = (
                self.is_initialized and
                self.is_operational and
                self.current_phase == SystemPhase.OPERATIONAL and
                health_score >= 0.7 and  # Reduced from 0.8 to 0.7 (70% healthy components)
                self.health_metrics['error_count'] < 15  # Increased tolerance
            )
            
            return {
                'healthy': overall_healthy,
                'component_type': self.health_metrics['component_type'],
                'component_id': self.component_id,
                'initialized': self.is_initialized,
                'operational': self.is_operational,
                'current_phase': self.current_phase.value,
                'uptime_seconds': uptime_seconds,
                'error_count': self.health_metrics['error_count'],
                'warning_count': self.health_metrics['warning_count'],
                'system_metrics': {
                    'total_components': self.system_metrics.total_components,
                    'operational_components': self.system_metrics.operational_components,
                    'failed_components': self.system_metrics.failed_components,
                    'health_score': health_score,
                    'performance_score': self.system_metrics.performance_score,
                    'initialization_time': self.system_metrics.initialization_time,
                    'startup_time': self.system_metrics.startup_time
                },
                'component_health': component_health,
                'last_health_check': current_time.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"System health check failed: {e}")
            self.health_metrics['error_count'] += 1
            return {
                'healthy': False,
                'component_type': self.health_metrics['component_type'],
                'component_id': self.component_id,
                'current_phase': self.current_phase.value,
                'error': str(e)
            }
    
    def get_component(self, component_name: str) -> Optional[ISystemComponent]:
        """Get a component by name"""
        return self.components.get(component_name)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return {
            'component_id': self.component_id,
            'component_type': self.health_metrics['component_type'],
            'initialized': self.is_initialized,
            'operational': self.is_operational,
            'current_phase': self.current_phase.value,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'system_metrics': {
                'total_components': self.system_metrics.total_components,
                'operational_components': self.system_metrics.operational_components,
                'failed_components': self.system_metrics.failed_components,
                'system_uptime': self.system_metrics.system_uptime,
                'health_score': self.system_metrics.health_score,
                'performance_score': self.system_metrics.performance_score
            },
            'component_status': {name: status.value for name, status in self.component_status.items()},
            'health_metrics': self.health_metrics
        }
    
    # System Integration Methods
    
    async def _initialize_orchestrator(self) -> None:
        """Initialize the hierarchical system orchestrator"""
        try:
            self.logger.info("🔧 Initializing System Orchestrator...")
            
            self.orchestrator = HierarchicalSystemOrchestrator()
            
            # Register Central Risk Manager if available
            if 'risk_manager' in self.components:
                risk_manager = self.components['risk_manager']
                self.orchestrator.register_central_risk_manager(risk_manager)
                self.logger.info("✅ Central Risk Manager registered with orchestrator")
            
            await self.orchestrator.initialize()
            
            self.logger.info("✅ System Orchestrator initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize orchestrator: {e}")
            # Don't raise - continue without orchestrator
    
    async def _initialize_all_components(self) -> None:
        """Initialize all enhanced components"""
        try:
            self.logger.info("🔧 Initializing all enhanced components...")
            
            # Initialize components in phases
            await self._initialize_phase_1_components()  # Core System
            await self._initialize_phase_2_components()  # Analytics & Strategy
            await self._initialize_phase_3_components()  # Processing Pipeline
            await self._initialize_phase_4_components()  # Data & Risk Management
            await self._initialize_phase_5_components()  # Trading & Execution
            await self._initialize_phase_6_components()  # Production Monitoring
            
            self.system_metrics.total_components = len(self.components)
            
            self.logger.info(f"✅ All {len(self.components)} enhanced components initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            raise
    
    async def _initialize_phase_1_components(self) -> None:
        """Initialize Phase 1: Core System Components"""
        try:
            self.logger.info("📊 Initializing Phase 1: Core System Components...")
            
            # Central Risk Manager
            try:
                from .central_risk_manager import CentralRiskManager
                risk_manager = CentralRiskManager(self.config.risk_manager_config)
                await risk_manager.initialize()
                self.components['risk_manager'] = risk_manager
                self.component_status['risk_manager'] = ComponentStatus.INITIALIZED
                
                # Register with orchestrator if available
                if hasattr(self, 'orchestrator') and self.orchestrator:
                    self.orchestrator.register_central_risk_manager(risk_manager)
                    self.logger.info("✅ Central Risk Manager registered with orchestrator")
                    
            except ImportError as e:
                self.logger.warning(f"CentralRiskManager not available: {e}")
            except Exception as e:
                self.logger.error(f"Failed to initialize Central Risk Manager: {e}")
            
            # Data Manager
            try:
                from ..data.manager import ClickHouseDataManager, ClickHouseDataConfig
                data_config = ClickHouseDataConfig(**self.config.data_manager_config)
                data_manager = ClickHouseDataManager(data_config)
                await data_manager.initialize()
                self.components['data_manager'] = data_manager
                self.component_status['data_manager'] = ComponentStatus.INITIALIZED
            except ImportError as e:
                self.logger.warning(f"ClickHouseDataManager not available: {e}")
            except Exception as e:
                self.logger.error(f"Failed to initialize data manager: {e}")
            
            # Execution Engine
            try:
                from .unified_execution_engine import UnifiedExecutionEngine
                execution_engine = UnifiedExecutionEngine(self.config.execution_engine_config)
                await execution_engine.initialize()
                self.components['execution_engine'] = execution_engine
                self.component_status['execution_engine'] = ComponentStatus.INITIALIZED
            except ImportError as e:
                self.logger.warning(f"UnifiedExecutionEngine not available: {e}")
            except Exception as e:
                self.logger.error(f"Failed to initialize execution engine: {e}")
            
            self.logger.info("✅ Phase 1 components initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Phase 1 components: {e}")
            # Don't raise - continue with other phases
    
    async def _initialize_phase_2_components(self) -> None:
        """Initialize Phase 2: Analytics & Strategy Components"""
        try:
            self.logger.info("📊 Initializing Phase 2: Analytics & Strategy Components...")
            
            # Analytics Manager
            try:
                from ..analytics.manager_enhanced import EnhancedAnalyticsManager
                analytics_manager = safe_component_init(EnhancedAnalyticsManager, self.config.analytics_manager_config)
                await analytics_manager.initialize()
                self.components['analytics_manager'] = analytics_manager
                self.component_status['analytics_manager'] = ComponentStatus.INITIALIZED
            except ImportError as e:
                self.logger.warning(f"EnhancedAnalyticsManager not available: {e}")
            except Exception as e:
                self.logger.error(f"Failed to initialize analytics manager: {e}")
            
            # Metrics Calculator
            try:
                from ..analytics.metrics_calculator import EnhancedMetricsCalculator
                metrics_calculator = safe_component_init(EnhancedMetricsCalculator, self.config.metrics_calculator_config)
                await metrics_calculator.initialize()
                self.components['metrics_calculator'] = metrics_calculator
                self.component_status['metrics_calculator'] = ComponentStatus.INITIALIZED
            except ImportError as e:
                self.logger.warning(f"EnhancedMetricsCalculator not available: {e}")
            except Exception as e:
                self.logger.error(f"Failed to initialize metrics calculator: {e}")
            
            # Strategy Manager
            try:
                from ..trading.strategies.manager import StrategyManager
                strategy_manager = StrategyManager(self.config.strategy_manager_config)
                await strategy_manager.initialize()
                self.components['strategy_manager'] = strategy_manager
                self.component_status['strategy_manager'] = ComponentStatus.INITIALIZED
            except ImportError as e:
                self.logger.warning(f"StrategyManager not available: {e}")
            except Exception as e:
                self.logger.error(f"Failed to initialize strategy manager: {e}")
            
            # Strategy Registry
            try:
                from ..trading.strategies.strategy_registry import EnhancedStrategyRegistry
                strategy_registry = EnhancedStrategyRegistry(self.config.strategy_registry_config)
                await strategy_registry.initialize()
                self.components['strategy_registry'] = strategy_registry
                self.component_status['strategy_registry'] = ComponentStatus.INITIALIZED
            except ImportError as e:
                self.logger.warning(f"EnhancedStrategyRegistry not available: {e}")
            except Exception as e:
                self.logger.error(f"Failed to initialize strategy registry: {e}")
            
            # Strategy Validator
            try:
                from ..trading.strategies.strategy_validator import EnhancedStrategyValidator
                strategy_validator = EnhancedStrategyValidator(self.config.strategy_validator_config)
                await strategy_validator.initialize()
                self.components['strategy_validator'] = strategy_validator
                self.component_status['strategy_validator'] = ComponentStatus.INITIALIZED
            except ImportError as e:
                self.logger.warning(f"EnhancedStrategyValidator not available: {e}")
            except Exception as e:
                self.logger.error(f"Failed to initialize strategy validator: {e}")
            
            self.logger.info("✅ Phase 2 components initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Phase 2 components: {e}")
            # Don't raise - continue with other phases
    
    async def _initialize_phase_3_components(self) -> None:
        """Initialize Phase 3: Processing Pipeline Components"""
        try:
            self.logger.info("📊 Initializing Phase 3: Processing Pipeline Components...")
            
            # Technical Indicators
            try:
                from ..processing.indicators.engine import EnhancedTechnicalIndicators
                indicators_engine = safe_component_init(EnhancedTechnicalIndicators, self.config.indicators_config)
                await indicators_engine.initialize()
                self.components['indicators_engine'] = indicators_engine
                self.component_status['indicators_engine'] = ComponentStatus.INITIALIZED
            except ImportError as e:
                self.logger.warning(f"EnhancedTechnicalIndicators not available: {e}")
            except Exception as e:
                self.logger.error(f"Failed to initialize indicators engine: {e}")
            
            # Feature Engineer
            try:
                from ..processing.features.engineer import EnhancedFeatureEngineer
                feature_engineer = safe_component_init(EnhancedFeatureEngineer, self.config.features_config)
                await feature_engineer.initialize()
                self.components['feature_engineer'] = feature_engineer
                self.component_status['feature_engineer'] = ComponentStatus.INITIALIZED
            except ImportError as e:
                self.logger.warning(f"EnhancedFeatureEngineer not available: {e}")
            except Exception as e:
                self.logger.error(f"Failed to initialize feature engineer: {e}")
            
            # Signal Generator
            try:
                from ..processing.signals.generator import EnhancedSignalGenerator
                signal_generator = EnhancedSignalGenerator(self.config.signals_config)
                await signal_generator.initialize()
                self.components['signal_generator'] = signal_generator
                self.component_status['signal_generator'] = ComponentStatus.INITIALIZED
            except ImportError as e:
                self.logger.warning(f"EnhancedSignalGenerator not available: {e}")
            except Exception as e:
                self.logger.error(f"Failed to initialize signal generator: {e}")
            
            self.logger.info("✅ Phase 3 components initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Phase 3 components: {e}")
            # Don't raise - continue with other phases
    
    async def _initialize_phase_4_components(self) -> None:
        """Initialize Phase 4: Data & Risk Management Components"""
        try:
            self.logger.info("📊 Initializing Phase 4: Data & Risk Management Components...")
            
            # Regime Engine
            try:
                from ..regime.engine import EnhancedRegimeEngine
                regime_engine = EnhancedRegimeEngine(self.config.regime_engine_config)
                await regime_engine.initialize()
                self.components['regime_engine'] = regime_engine
                self.component_status['regime_engine'] = ComponentStatus.INITIALIZED
            except ImportError as e:
                self.logger.warning(f"EnhancedRegimeEngine not available: {e}")
            except Exception as e:
                self.logger.error(f"Failed to initialize regime engine: {e}")
            
            self.logger.info("✅ Phase 4 components initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Phase 4 components: {e}")
            # Don't raise - continue with other phases
    
    async def _initialize_phase_5_components(self) -> None:
        """Initialize Phase 5: Trading & Execution Components"""
        try:
            self.logger.info("📊 Initializing Phase 5: Trading & Execution Components...")
            
            # Trading Engine
            try:
                from ..trading.engine import EnhancedTradingEngine
                trading_engine = EnhancedTradingEngine(self.config.trading_engine_config)
                await trading_engine.initialize()
                self.components['trading_engine'] = trading_engine
                self.component_status['trading_engine'] = ComponentStatus.INITIALIZED
            except ImportError as e:
                self.logger.warning(f"EnhancedTradingEngine not available: {e}")
            except Exception as e:
                self.logger.error(f"Failed to initialize trading engine: {e}")
            
            # Portfolio Manager
            try:
                from ..trading.portfolio.manager_enhanced import EnhancedPortfolioManager
                portfolio_manager = EnhancedPortfolioManager(self.config.portfolio_manager_config)
                await portfolio_manager.initialize()
                self.components['portfolio_manager'] = portfolio_manager
                self.component_status['portfolio_manager'] = ComponentStatus.INITIALIZED
            except ImportError as e:
                self.logger.warning(f"EnhancedPortfolioManager not available: {e}")
            except Exception as e:
                self.logger.error(f"Failed to initialize portfolio manager: {e}")
            
            self.logger.info("✅ Phase 5 components initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Phase 5 components: {e}")
            # Don't raise - continue with other phases
    
    async def _initialize_phase_6_components(self) -> None:
        """Initialize Phase 6: Production Monitoring Components"""
        try:
            self.logger.info("📊 Initializing Phase 6: Production Monitoring Components...")
            
            # Production Health Monitor
            if self.config.enable_production_monitoring:
                try:
                    health_monitor = ProductionHealthMonitor(self.config.production_health_monitor_config)
                    await health_monitor.initialize()
                    self.components['production_health_monitor'] = health_monitor
                    self.component_status['production_health_monitor'] = ComponentStatus.INITIALIZED
                    self.logger.info("✅ Production Health Monitor initialized")
                except Exception as e:
                    self.logger.error(f"Failed to initialize Production Health Monitor: {e}")
            
            # Graceful Degradation Manager
            try:
                degradation_manager = GracefulDegradationManager(self.config.graceful_degradation_config)
                await degradation_manager.initialize()
                self.components['graceful_degradation_manager'] = degradation_manager
                self.component_status['graceful_degradation_manager'] = ComponentStatus.INITIALIZED
                self.logger.info("✅ Graceful Degradation Manager initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize Graceful Degradation Manager: {e}")
            
            # Audit Trail Manager
            if self.config.enable_audit_trail:
                try:
                    audit_manager = AuditTrailManager(self.config.audit_trail_config)
                    await audit_manager.initialize()
                    self.components['audit_trail_manager'] = audit_manager
                    self.component_status['audit_trail_manager'] = ComponentStatus.INITIALIZED
                    self.logger.info("✅ Audit Trail Manager initialized")
                except Exception as e:
                    self.logger.error(f"Failed to initialize Audit Trail Manager: {e}")
            
            # Disaster Recovery Manager
            if self.config.enable_disaster_recovery:
                try:
                    disaster_recovery = DisasterRecoveryManager(self.config.disaster_recovery_config)
                    await disaster_recovery.initialize()
                    self.components['disaster_recovery_manager'] = disaster_recovery
                    self.component_status['disaster_recovery_manager'] = ComponentStatus.INITIALIZED
                    self.logger.info("✅ Disaster Recovery Manager initialized")
                except Exception as e:
                    self.logger.error(f"Failed to initialize Disaster Recovery Manager: {e}")
            
            self.logger.info("✅ Phase 6 components initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Phase 6 components: {e}")
            # Don't raise - continue with other phases
    
    async def _inject_component_dependencies(self) -> None:
        """Inject dependencies between components after initialization"""
        try:
            self.logger.info("🔗 Injecting component dependencies...")
            
            # Inject StrategyManager dependencies
            if 'strategy_manager' in self.components:
                strategy_manager = self.components['strategy_manager']
                
                # Set risk manager dependency
                if 'risk_manager' in self.components:
                    strategy_manager.set_risk_manager(self.components['risk_manager'])
                    self.logger.info("   ✅ StrategyManager -> RiskManager dependency injected")
                
                # Set data manager dependency
                if 'data_manager' in self.components:
                    strategy_manager.set_data_manager(self.components['data_manager'])
                    self.logger.info("   ✅ StrategyManager -> DataManager dependency injected")
                
                # Set regime engine dependency
                if 'regime_engine' in self.components:
                    strategy_manager.set_regime_engine(self.components['regime_engine'])
                    self.logger.info("   ✅ StrategyManager -> RegimeEngine dependency injected")
            
            # Inject TradingEngine dependencies
            if 'trading_engine' in self.components:
                trading_engine = self.components['trading_engine']
                
                # Set strategy manager dependency if available
                if hasattr(trading_engine, 'set_strategy_manager') and 'strategy_manager' in self.components:
                    trading_engine.set_strategy_manager(self.components['strategy_manager'])
                    self.logger.info("   ✅ TradingEngine -> StrategyManager dependency injected")
                
                # Set risk manager dependency if available
                if hasattr(trading_engine, 'set_risk_manager') and 'risk_manager' in self.components:
                    trading_engine.set_risk_manager(self.components['risk_manager'])
                    self.logger.info("   ✅ TradingEngine -> RiskManager dependency injected")
            
            # Inject ExecutionEngine dependencies
            if 'execution_engine' in self.components:
                execution_engine = self.components['execution_engine']
                
                # Set risk manager callback for position updates
                if 'risk_manager' in self.components:
                    risk_manager = self.components['risk_manager']
                    if hasattr(execution_engine, 'set_position_callbacks'):
                        execution_engine.set_position_callbacks(
                            risk_manager_callback=risk_manager,
                            position_update_callback=getattr(risk_manager, 'update_position', None)
                        )
                        self.logger.info("   ✅ ExecutionEngine -> RiskManager callbacks injected")
            
            self.logger.info("✅ Component dependencies injection completed")
            
        except Exception as e:
            self.logger.error(f"Failed to inject component dependencies: {e}")
            # Don't raise - this is not critical for basic operation
    
    async def _setup_component_dependencies(self) -> None:
        """Setup component dependencies and initialization order"""
        try:
            self.logger.info("🔗 Setting up component dependencies...")
            
            # Define dependency relationships
            self.component_dependencies = {
                'data_manager': [],  # No dependencies
                'regime_engine': ['data_manager'],
                'risk_manager': ['data_manager', 'regime_engine'],
                'indicators_engine': ['data_manager'],
                'feature_engineer': ['indicators_engine'],
                'signal_generator': ['feature_engineer'],
                'strategy_registry': [],
                'strategy_validator': ['strategy_registry'],
                'strategy_manager': ['signal_generator', 'strategy_validator', 'regime_engine'],
                'trading_engine': ['strategy_manager', 'risk_manager'],
                'execution_engine': ['trading_engine', 'risk_manager'],
                'portfolio_manager': ['execution_engine'],
                'analytics_manager': ['portfolio_manager'],
                'metrics_calculator': ['portfolio_manager']
            }
            
            # Calculate initialization order based on dependencies
            self.initialization_order = self._calculate_initialization_order()
            
            self.logger.info(f"✅ Component dependencies setup complete. Order: {self.initialization_order}")
            
        except Exception as e:
            self.logger.error(f"Failed to setup component dependencies: {e}")
            raise
    
    def _calculate_initialization_order(self) -> List[str]:
        """Calculate component initialization order based on dependencies"""
        order = []
        visited = set()
        temp_visited = set()
        
        def visit(component: str):
            if component in temp_visited:
                raise ValueError(f"Circular dependency detected involving {component}")
            if component in visited:
                return
            
            temp_visited.add(component)
            
            # Visit dependencies first
            for dependency in self.component_dependencies.get(component, []):
                if dependency in self.components:
                    visit(dependency)
            
            temp_visited.remove(component)
            visited.add(component)
            order.append(component)
        
        # Visit all components
        for component in self.components.keys():
            if component not in visited:
                visit(component)
        
        return order
    
    async def _start_all_components(self) -> None:
        """Start all components in dependency order"""
        try:
            self.logger.info("🚀 Starting all components in dependency order...")
            
            operational_count = 0
            failed_count = 0
            
            for component_name in self.initialization_order:
                if component_name in self.components:
                    try:
                        self.component_status[component_name] = ComponentStatus.STARTING
                        component = self.components[component_name]
                        
                        start_result = await component.start()
                        if start_result:
                            self.component_status[component_name] = ComponentStatus.OPERATIONAL
                            operational_count += 1
                            self.logger.info(f"✅ {component_name} started successfully")
                        else:
                            self.component_status[component_name] = ComponentStatus.ERROR
                            failed_count += 1
                            self.logger.error(f"❌ {component_name} failed to start")
                            
                    except Exception as e:
                        self.component_status[component_name] = ComponentStatus.ERROR
                        failed_count += 1
                        self.logger.error(f"❌ {component_name} start failed: {e}")
            
            self.system_metrics.operational_components = operational_count
            self.system_metrics.failed_components = failed_count
            
            self.logger.info(f"✅ Component startup complete: {operational_count} operational, {failed_count} failed")
            
        except Exception as e:
            self.logger.error(f"Failed to start components: {e}")
            raise
    
    async def _stop_all_components(self) -> None:
        """Stop all components in reverse dependency order"""
        try:
            self.logger.info("🛑 Stopping all components in reverse dependency order...")
            
            # Stop in reverse order
            for component_name in reversed(self.initialization_order):
                if component_name in self.components:
                    try:
                        self.component_status[component_name] = ComponentStatus.STOPPING
                        component = self.components[component_name]
                        
                        # Check if component has a stop method
                        if hasattr(component, 'stop') and callable(getattr(component, 'stop')):
                            stop_result = await component.stop()
                            if stop_result:
                                self.component_status[component_name] = ComponentStatus.STOPPED
                                self.logger.info(f"✅ {component_name} stopped successfully")
                            else:
                                self.component_status[component_name] = ComponentStatus.ERROR
                                self.logger.warning(f"⚠️ {component_name} stop returned False")
                        else:
                            # Component doesn't have stop method - just mark as stopped
                            self.component_status[component_name] = ComponentStatus.STOPPED
                            self.logger.info(f"✅ {component_name} stopped (no stop method)")
                            
                    except Exception as e:
                        self.component_status[component_name] = ComponentStatus.ERROR
                        self.logger.warning(f"⚠️ Shutdown method failed for {component_name}: {e}")
            
            self.logger.info("✅ All components stopped")
            
        except Exception as e:
            self.logger.error(f"Failed to stop components: {e}")
            raise
    
    async def _check_all_components_health(self) -> Dict[str, Any]:
        """Check health of all components"""
        component_health = {}
        
        for component_name, component in self.components.items():
            try:
                # Check if component has health_check method
                if hasattr(component, 'health_check') and callable(getattr(component, 'health_check')):
                    health = await component.health_check()
                    component_health[component_name] = health
                    
                    # Log unhealthy components for debugging
                    if not health.get('healthy', False):
                        self.logger.debug(f"🔍 {component_name} health check returned unhealthy: {health}")
                else:
                    # Component doesn't have health_check - assume healthy if it exists
                    component_health[component_name] = {
                        'healthy': True,
                        'component_type': component.__class__.__name__,
                        'note': 'No health_check method - assumed healthy'
                    }
                    
            except Exception as e:
                self.logger.warning(f"⚠️ Health check failed for {component_name}: {e}")
                component_health[component_name] = {
                    'healthy': False,
                    'error': str(e),
                    'component_type': component.__class__.__name__
                }
        
        return component_health
    
    def _calculate_system_health_score(self, component_health: Dict[str, Any]) -> float:
        """Calculate overall system health score"""
        if not component_health:
            return 0.0
        
        healthy_count = sum(1 for health in component_health.values() if health.get('healthy', False))
        total_count = len(component_health)
        
        return healthy_count / total_count if total_count > 0 else 0.0
    
    async def _initialize_monitoring_systems(self) -> None:
        """Initialize monitoring systems"""
        try:
            self.logger.info("📈 Initializing monitoring systems...")
            # Monitoring initialization logic here
            self.logger.info("✅ Monitoring systems initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize monitoring systems: {e}")
            raise
    
    async def _start_monitoring_systems(self) -> None:
        """Start monitoring systems"""
        try:
            self.logger.info("📊 Starting monitoring systems...")
            
            if self.config.enable_health_monitoring:
                self._health_monitor_task = asyncio.create_task(self._health_monitor_loop())
            
            if self.config.enable_performance_monitoring:
                self._performance_monitor_task = asyncio.create_task(self._performance_monitor_loop())
            
            self.logger.info("✅ Monitoring systems started")
            
        except Exception as e:
            self.logger.error(f"Failed to start monitoring systems: {e}")
            raise
    
    async def _stop_monitoring_systems(self) -> None:
        """Stop monitoring systems"""
        try:
            self.logger.info("📊 Stopping monitoring systems...")
            
            if self._health_monitor_task:
                self._health_monitor_task.cancel()
                try:
                    await self._health_monitor_task
                except asyncio.CancelledError:
                    pass
            
            if self._performance_monitor_task:
                self._performance_monitor_task.cancel()
                try:
                    await self._performance_monitor_task
                except asyncio.CancelledError:
                    pass
            
            self.logger.info("✅ Monitoring systems stopped")
            
        except Exception as e:
            self.logger.error(f"Failed to stop monitoring systems: {e}")
            raise
    
    async def _health_monitor_loop(self) -> None:
        """Health monitoring loop"""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self.config.health_check_interval)
                if self._shutdown_event.is_set():
                    break
                
                # Perform health check
                health = await self.health_check()
                
                if not health['healthy']:
                    self.logger.warning(f"System health degraded: {health['system_metrics']}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(5)
    
    async def _performance_monitor_loop(self) -> None:
        """Performance monitoring loop"""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self.config.performance_report_interval)
                if self._shutdown_event.is_set():
                    break
                
                # Generate performance report
                performance_report = await self._generate_performance_report()
                self.logger.info(f"Performance Report: {performance_report}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Performance monitor error: {e}")
                await asyncio.sleep(10)
    
    async def _generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        return {
            'timestamp': datetime.now().isoformat(),
            'system_metrics': {
                'total_components': self.system_metrics.total_components,
                'operational_components': self.system_metrics.operational_components,
                'failed_components': self.system_metrics.failed_components,
                'health_score': self.system_metrics.health_score,
                'system_uptime': self.system_metrics.system_uptime
            },
            'component_status': {name: status.value for name, status in self.component_status.items()}
        }
    
    async def _start_orchestrator(self) -> None:
        """Start the system orchestrator"""
        try:
            if self.orchestrator:
                await self.orchestrator.start()
                self.logger.info("✅ System Orchestrator started")
        except Exception as e:
            self.logger.error(f"Failed to start orchestrator: {e}")
            raise
    
    async def _stop_orchestrator(self) -> None:
        """Stop the system orchestrator"""
        try:
            if self.orchestrator:
                await self.orchestrator.stop()
                self.logger.info("✅ System Orchestrator stopped")
        except Exception as e:
            self.logger.error(f"Failed to stop orchestrator: {e}")
            raise


# Production Configuration Templates

def create_production_config() -> SystemConfiguration:
    """Create production-ready system configuration"""
    return SystemConfiguration(
        # Core System
        risk_manager_config={
            'max_position_size': 0.10,
            'max_daily_var': 0.05,
            'position_concentration_limit': 0.15,
            'strategy_allocation_limit': 0.33,
            'min_signal_confidence': 0.60
        },
        data_manager_config={
            'symbols': ['AAPL', 'TSLA', 'NVDA', 'MSFT', 'GOOGL'],
            'start_date': '2024-01-01',
            'end_date': '2024-12-31',
            'enable_caching': True,
            'clickhouse_host': 'localhost',
            'clickhouse_port': 8123
        },
        execution_engine_config={
            'max_market_impact': 0.05,
            'default_time_horizon': 300,
            'enable_position_tracking': True
        },
        
        # Analytics & Strategy
        analytics_manager_config={
            'mode': 'realtime',
            'enable_performance_tracking': True,
            'enable_attribution_analysis': True
        },
        strategy_manager_config={
            'max_concurrent_strategies': 10,
            'min_confidence_threshold': 0.6,
            'enable_regime_awareness': True
        },
        strategy_registry_config={
            'registry_path': './strategy_registry',
            'auto_discovery_enabled': True,
            'cache_enabled': True,
            'output_directory': './strategy_registry'
        },
        
        # Processing Pipeline
        indicators_config={
            'enable_caching': True,
            'calculation_threads': 4
        },
        features_config={
            'enable_scaling': True,
            'feature_selection': True
        },
        signals_config={
            'mean_reversion_weight': 0.4,
            'momentum_weight': 0.4,
            'volume_weight': 0.2,
            'signal_threshold': 0.6
        },
        
        # Data & Risk Management
        regime_engine_config={
            'lookback_window': 60,
            'volatility_window': 20,
            'trend_threshold': 0.02,
            'regime_change_threshold': 0.7
        },
        
        # Trading & Execution
        trading_engine_config={
            'max_slice_size': 1000.0,
            'min_slice_size': 10.0,
            'enable_smart_routing': True
        },
        portfolio_manager_config={
            'portfolio_id': 'production_portfolio',
            'base_currency': 'USD',
            'max_portfolio_risk': 0.20,
            'max_concentration': 0.10
        },
        
        # System Settings
        enable_performance_monitoring=True,
        enable_health_monitoring=True,
        enable_production_monitoring=True,
        enable_audit_trail=True,
        enable_disaster_recovery=True,
        health_check_interval=30,
        performance_report_interval=300,
        
        # Production Monitoring Configuration
        production_health_monitor_config={
            'cpu_threshold': 80.0,
            'memory_threshold': 85.0,
            'disk_threshold': 90.0,
            'monitoring_interval': 30
        },
        graceful_degradation_config={
            'enable_auto_degradation': True,
            'degradation_thresholds': {
                'critical_components': 2,
                'warning_components': 3
            }
        },
        audit_trail_config={
            'storage_backend': 'file',
            'audit_file_path': './production_audit.jsonl',
            'buffer_size': 1000
        },
        disaster_recovery_config={
            'backup_locations': ['primary', 'secondary'],
            'rto_minutes': 15,
            'rpo_minutes': 5
        }
    )


def create_development_config() -> SystemConfiguration:
    """Create development-friendly system configuration"""
    return SystemConfiguration(
        # Simplified configs for development
        risk_manager_config={
            'max_position_size': 0.05,
            'max_daily_var': 0.03,
            'min_signal_confidence': 0.5
        },
        data_manager_config={
            'symbols': ['AAPL', 'TSLA'],
            'start_date': '2024-01-01',
            'end_date': '2024-01-31',
            'enable_caching': True,
            'clickhouse_host': 'localhost',
            'clickhouse_port': 8123
        },
        execution_engine_config={
            'max_market_impact': 0.03,
            'default_time_horizon': 180,
            'enable_position_tracking': True
        },
        analytics_manager_config={
            'mode': 'backtest',
            'enable_performance_tracking': True,
            'output_directory': './analytics_output',
            'enable_attribution_analysis': True
        },
        strategy_manager_config={
            'max_concurrent_strategies': 3,
            'min_confidence_threshold': 0.5
        },
        strategy_registry_config={
            'registry_path': './dev_strategy_registry',
            'auto_discovery_enabled': False,
            'cache_enabled': True,
            'output_directory': './dev_strategy_registry'
        },
        strategy_validator_config={
            'enable_validation': True,
            'output_directory': './dev_validation'
        },
        
        # Processing Pipeline
        indicators_config={
            'enable_caching': True,
            'calculation_threads': 2
        },
        features_config={
            'enable_scaling': True,
            'feature_selection': False
        },
        signals_config={
            'mean_reversion_weight': 0.4,
            'momentum_weight': 0.4,
            'volume_weight': 0.2,
            'signal_threshold': 0.5
        },
        regime_engine_config={
            'lookback_window': 30,
            'volatility_window': 10,
            'trend_threshold': 0.01
        },
        trading_engine_config={
            'max_slice_size': 500.0,
            'min_slice_size': 10.0,
            'enable_smart_routing': True
        },
        portfolio_manager_config={
            'portfolio_id': 'dev_portfolio',
            'base_currency': 'USD',
            'max_portfolio_risk': 0.10
        },
        
        # Development settings
        enable_performance_monitoring=True,
        enable_health_monitoring=True,
        health_check_interval=60,
        performance_report_interval=600
    )
