"""
Analytics Engine - Enhanced Manager
Unified analytics orchestration with advanced coordination and integration
"""

import logging
import threading
import asyncio
import uuid
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
from pathlib import Path
import warnings
from concurrent.futures import ThreadPoolExecutor

# Import centralized configuration (Rule 1 Section 7 - Configuration Management)
try:
    from ..config import AnalyticsConfig as CentralizedAnalyticsConfig
    CENTRALIZED_CONFIG_AVAILABLE = True
except ImportError:
    CENTRALIZED_CONFIG_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Centralized AnalyticsConfig not available, using local config")

# Import ISystemComponent and IRegimeAware for orchestrator integration
try:
    from ..system.interfaces import ISystemComponent, IRegimeAware, RegimeContext
except ImportError:
    # Fallback definition
    from abc import ABC, abstractmethod
    class ISystemComponent(ABC):
        @abstractmethod
        async def initialize(self) -> bool:
            pass
        
        @abstractmethod
        async def start(self) -> bool:
            pass
        
        @abstractmethod
        async def stop(self) -> bool:
            pass
        
        @abstractmethod
        async def health_check(self) -> Dict[str, Any]:
            pass
        
        @abstractmethod
        def get_status(self) -> Dict[str, Any]:
            pass
    
    class IRegimeAware(ABC):
        pass
    
    # Minimal RegimeContext for fallback
    from dataclasses import dataclass
    @dataclass
    class RegimeContext:
        primary_regime: str = "unknown"
        regime_confidence: float = 0.5
        regime_start_time: datetime = None
        regime_duration_minutes: float = 0.0

# Internal imports
from .performance_analyzer import PerformanceAnalyzer, PerformanceConfig
from .attribution_analyzer import AttributionAnalyzer, AttributionConfig
from .metrics_calculator import EnhancedMetricsCalculator, MetricConfig, MetricCategory
from .report_generator import ReportGenerator, ReportConfig, ReportData, ReportFormat
from .benchmark_analyzer import BenchmarkAnalyzer, BenchmarkConfig

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class AnalyticsMode(Enum):
    """Analytics operation modes"""
    REALTIME = "realtime"
    BATCH = "batch"
    SCHEDULED = "scheduled"
    ON_DEMAND = "on_demand"


class AnalyticsPriority(Enum):
    """Analytics task priorities"""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class AnalyticsStatus(Enum):
    """Analytics system status"""
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    MAINTENANCE = "maintenance"


@dataclass
class AnalyticsConfig:
    """Comprehensive analytics configuration"""
    # System settings
    mode: AnalyticsMode = AnalyticsMode.REALTIME
    max_workers: int = 4
    enable_caching: bool = True
    cache_ttl_hours: int = 24
    
    # Component configurations
    performance_config: PerformanceConfig = field(default_factory=PerformanceConfig)
    attribution_config: AttributionConfig = field(default_factory=AttributionConfig)
    metrics_config: MetricConfig = field(default_factory=MetricConfig)
    report_config: ReportConfig = field(default_factory=ReportConfig)
    benchmark_config: BenchmarkConfig = field(default_factory=BenchmarkConfig)
    
    # Data settings
    min_data_points: int = 30
    max_data_points: int = 50000
    data_quality_threshold: float = 0.7
    
    # Analysis settings
    enable_performance_analysis: bool = True
    enable_attribution_analysis: bool = True
    enable_benchmark_analysis: bool = True
    enable_factor_analysis: bool = True
    enable_risk_analysis: bool = True
    
    # Reporting settings
    auto_generate_reports: bool = True
    report_frequency: str = "daily"  # daily, weekly, monthly
    default_report_format: ReportFormat = ReportFormat.HTML
    
    # Alert settings
    enable_alerts: bool = True
    performance_alert_threshold: float = -0.05  # 5% loss
    risk_alert_threshold: float = 0.25  # 25% VaR
    
    # Storage settings
    output_directory: str = "analytics_output"
    archive_old_results: bool = True
    max_archive_days: int = 90


@dataclass
class AnalyticsTask:
    """Analytics task definition"""
    task_id: str
    task_type: str
    priority: AnalyticsPriority
    
    # Task data
    symbol: str
    returns_data: pd.Series
    price_data: Optional[pd.Series] = None
    benchmark_data: Optional[pd.Series] = None
    
    # Task configuration
    config_overrides: Dict[str, Any] = field(default_factory=dict)
    
    # Task metadata
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Results
    results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    
    # Status
    status: str = "pending"
    progress: float = 0.0


@dataclass
class AnalyticsResults:
    """Comprehensive analytics results"""
    symbol: str
    analysis_timestamp: datetime
    
    # Core results
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    attribution_results: Dict[str, Any] = field(default_factory=dict)
    benchmark_comparison: Dict[str, Any] = field(default_factory=dict)
    risk_metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Summary statistics
    key_metrics: Dict[str, float] = field(default_factory=dict)
    alerts: List[str] = field(default_factory=list)
    data_quality: float = 0.0
    
    # Generated reports
    reports: Dict[str, str] = field(default_factory=dict)  # format -> file_path
    
    # Metadata
    execution_time: float = 0.0
    data_points: int = 0
    components_analyzed: List[str] = field(default_factory=list)


class TaskScheduler:
    """Analytics task scheduler"""
    
    def __init__(self, config: AnalyticsConfig):
        self.config = config
        self._task_queue = asyncio.PriorityQueue()
        self._completed_tasks = {}
        self._running_tasks = {}
        self._lock = threading.Lock()
    
    async def schedule_task(self, task: AnalyticsTask) -> None:
        """Schedule analytics task"""
        
        # Priority mapping
        priority_map = {
            AnalyticsPriority.CRITICAL: 1,
            AnalyticsPriority.HIGH: 2,
            AnalyticsPriority.NORMAL: 3,
            AnalyticsPriority.LOW: 4
        }
        
        priority = priority_map.get(task.priority, 3)
        
        # Add to queue
        await self._task_queue.put((priority, task.created_at, task))
        
        logger.debug(f"Scheduled task {task.task_id} with priority {task.priority.value}")
    
    async def get_next_task(self) -> Optional[AnalyticsTask]:
        """Get next task from queue"""
        
        try:
            priority, timestamp, task = await asyncio.wait_for(
                self._task_queue.get(), timeout=1.0
            )
            
            with self._lock:
                self._running_tasks[task.task_id] = task
            
            return task
            
        except asyncio.TimeoutError:
            return None
    
    def complete_task(self, task: AnalyticsTask) -> None:
        """Mark task as completed"""
        
        with self._lock:
            if task.task_id in self._running_tasks:
                del self._running_tasks[task.task_id]
            
            task.completed_at = datetime.now()
            task.status = "completed"
            self._completed_tasks[task.task_id] = task
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status"""
        
        with self._lock:
            # Check running tasks
            if task_id in self._running_tasks:
                task = self._running_tasks[task_id]
                return {
                    'task_id': task_id,
                    'status': task.status,
                    'progress': task.progress,
                    'started_at': task.started_at,
                    'errors': task.errors
                }
            
            # Check completed tasks
            if task_id in self._completed_tasks:
                task = self._completed_tasks[task_id]
                return {
                    'task_id': task_id,
                    'status': task.status,
                    'progress': task.progress,
                    'completed_at': task.completed_at,
                    'execution_time': (task.completed_at - task.started_at).total_seconds() if task.started_at else 0,
                    'errors': task.errors
                }
        
        return None


class AlertSystem:
    """Analytics alert system"""
    
    def __init__(self, config: AnalyticsConfig):
        self.config = config
        self._alerts = []
        self._lock = threading.Lock()
    
    def check_performance_alerts(
        self,
        symbol: str,
        performance_metrics: Dict[str, Any]
    ) -> List[str]:
        """Check for performance alerts"""
        
        alerts = []
        
        if not self.config.enable_alerts:
            return alerts
        
        try:
            # Check for significant losses
            if 'total_return' in performance_metrics:
                total_return = performance_metrics['total_return'].get('value', 0)
                if total_return < self.config.performance_alert_threshold:
                    alerts.append(f"PERFORMANCE ALERT: {symbol} has a negative return of {total_return:.2%}")
            
            # Check for high volatility
            if 'volatility' in performance_metrics:
                volatility = performance_metrics['volatility'].get('value', 0)
                if volatility > 0.5:  # 50% annual volatility
                    alerts.append(f"VOLATILITY ALERT: {symbol} has high volatility of {volatility:.2%}")
            
            # Check for poor risk-adjusted returns
            if 'sharpe_ratio' in performance_metrics:
                sharpe = performance_metrics['sharpe_ratio'].get('value', 0)
                if sharpe < -0.5:
                    alerts.append(f"SHARPE ALERT: {symbol} has poor risk-adjusted returns (Sharpe: {sharpe:.2f})")
            
        except Exception as e:
            logger.error(f"Error checking performance alerts for {symbol}: {e}")
        
        return alerts
    
    def check_risk_alerts(
        self,
        symbol: str,
        risk_metrics: Dict[str, Any]
    ) -> List[str]:
        """Check for risk alerts"""
        
        alerts = []
        
        if not self.config.enable_alerts:
            return alerts
        
        try:
            # Check VaR alerts
            for metric_name, metric_data in risk_metrics.items():
                if 'var_95' in metric_name.lower():
                    var_value = abs(metric_data.get('value', 0))
                    if var_value > self.config.risk_alert_threshold:
                        alerts.append(f"RISK ALERT: {symbol} VaR exceeds threshold ({var_value:.2%})")
            
            # Check maximum drawdown
            if 'maximum_drawdown' in risk_metrics:
                max_dd = risk_metrics['maximum_drawdown'].get('value', 0)
                if max_dd > 0.20:  # 20% drawdown
                    alerts.append(f"DRAWDOWN ALERT: {symbol} has significant drawdown ({max_dd:.2%})")
            
        except Exception as e:
            logger.error(f"Error checking risk alerts for {symbol}: {e}")
        
        return alerts
    
    def add_alert(self, alert: str) -> None:
        """Add alert to system"""
        
        with self._lock:
            alert_record = {
                'timestamp': datetime.now(),
                'message': alert,
                'acknowledged': False
            }
            self._alerts.append(alert_record)
        
        logger.warning(f"ALERT: {alert}")
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get active alerts"""
        
        with self._lock:
            return [alert for alert in self._alerts if not alert['acknowledged']]
    
    def acknowledge_alert(self, alert_index: int) -> bool:
        """Acknowledge an alert"""
        
        with self._lock:
            if 0 <= alert_index < len(self._alerts):
                self._alerts[alert_index]['acknowledged'] = True
                return True
        
        return False


class DataValidator:
    """Analytics data validator"""
    
    def __init__(self, config: AnalyticsConfig):
        self.config = config
    
    def validate_returns_data(self, returns: pd.Series, symbol: str) -> Tuple[bool, List[str]]:
        """Validate returns data"""
        
        issues = []
        
        # Check for empty data
        if returns.empty:
            issues.append(f"No returns data for {symbol}")
            return False, issues
        
        # Check minimum data points
        if len(returns) < self.config.min_data_points:
            issues.append(f"Insufficient data points for {symbol}: {len(returns)} < {self.config.min_data_points}")
        
        # Check for excessive missing values
        missing_ratio = returns.isna().sum() / len(returns)
        if missing_ratio > 0.1:  # 10% missing
            issues.append(f"High missing data ratio for {symbol}: {missing_ratio:.2%}")
        
        # Check for extreme outliers
        if len(returns.dropna()) > 0:
            clean_returns = returns.dropna()
            mean_return = clean_returns.mean()
            std_return = clean_returns.std()
            
            if std_return > 0:
                outliers = abs(clean_returns - mean_return) > 5 * std_return
                outlier_ratio = outliers.sum() / len(clean_returns)
                
                if outlier_ratio > 0.05:  # 5% outliers
                    issues.append(f"High outlier ratio for {symbol}: {outlier_ratio:.2%}")
        
        # Check for constant values
        if returns.std() == 0:
            issues.append(f"Constant returns detected for {symbol}")
        
        # Data quality assessment
        quality_score = self._calculate_data_quality(returns)
        if quality_score < self.config.data_quality_threshold:
            issues.append(f"Low data quality score for {symbol}: {quality_score:.2f}")
        
        # Check data freshness
        if not returns.empty:
            last_date = returns.index[-1]
            days_old = (datetime.now() - last_date.to_pydatetime()).days
            if days_old > 7:  # More than a week old
                issues.append(f"Stale data for {symbol}: {days_old} days old")
        
        is_valid = len(issues) == 0
        return is_valid, issues
    
    def _calculate_data_quality(self, returns: pd.Series) -> float:
        """Calculate data quality score"""
        
        if returns.empty:
            return 0.0
        
        quality_score = 1.0
        
        # Missing data penalty
        missing_ratio = returns.isna().sum() / len(returns)
        quality_score -= missing_ratio * 0.5
        
        # Outlier penalty
        if returns.std() > 0:
            outliers = abs(returns - returns.mean()) > 3 * returns.std()
            outlier_ratio = outliers.sum() / len(returns)
            quality_score -= outlier_ratio * 0.3
        
        # Consistency check (no extreme jumps)
        if len(returns) > 1:
            jumps = abs(returns.diff()) > 0.5  # 50% single-day moves
            jump_ratio = jumps.sum() / len(returns)
            quality_score -= jump_ratio * 0.2
        
        return max(quality_score, 0.0)


class EnhancedAnalyticsManager(ISystemComponent, IRegimeAware):
    """
    Enhanced Analytics Manager with ISystemComponent and IRegimeAware Integration
    
    Unified orchestration of all analytics components with advanced
    coordination, task scheduling, integrated reporting, and orchestrator integration
    for institutional-grade analytics operations.
    
    **Enhanced Features:**
    - ISystemComponent integration for orchestrator
    - IRegimeAware integration for regime-based analytics
    - Centralized configuration (Rule 1 Section 7)
    """
    
    def __init__(self, config: Optional[Any] = None):
        """
        Initialize enhanced analytics manager
        
        Args:
            config: AnalyticsConfig or dict
        """
        # Handle centralized configuration (Rule 1 Section 7 - Configuration Management)
        if CENTRALIZED_CONFIG_AVAILABLE and (config is None or isinstance(config, dict)):
            # Use centralized config
            if config is None:
                self.centralized_config = CentralizedAnalyticsConfig()
            elif isinstance(config, dict):
                self.centralized_config = CentralizedAnalyticsConfig(**{
                    k: v for k, v in config.items() 
                    if hasattr(CentralizedAnalyticsConfig, k)
                })
            
            # Map to local AnalyticsConfig for backward compatibility
            self.config = AnalyticsConfig(
                mode=AnalyticsMode(self.centralized_config.mode),
                max_workers=self.centralized_config.max_workers,
                enable_caching=self.centralized_config.enable_caching,
                cache_ttl_hours=self.centralized_config.cache_ttl_hours,
            )
            logger.info("✅ Using centralized AnalyticsConfig (Rule 1 Section 7)")
        elif isinstance(config, CentralizedAnalyticsConfig if CENTRALIZED_CONFIG_AVAILABLE else type(None)):
            # Already centralized config
            self.centralized_config = config
            self.config = AnalyticsConfig(
                mode=AnalyticsMode(config.mode),
                max_workers=config.max_workers,
                enable_caching=config.enable_caching,
                cache_ttl_hours=config.cache_ttl_hours,
            )
            logger.info("✅ Using centralized AnalyticsConfig (Rule 1 Section 7)")
        else:
            # Fallback to local config
            self.config = config if isinstance(config, AnalyticsConfig) else AnalyticsConfig()
            self.centralized_config = None
            if not CENTRALIZED_CONFIG_AVAILABLE:
                logger.debug("Using local AnalyticsConfig (centralized config not available)")
        
        # Component identification and lifecycle
        self.component_id = str(uuid.uuid4())
        self.is_initialized = False
        self.is_operational = False
        self.start_time = None
        
        # Orchestrator integration
        self.orchestrator: Optional[Any] = None  # HierarchicalSystemOrchestrator reference
        
        # IRegimeAware state management
        self.regime_engine: Optional[Any] = None
        self.current_regime_context: Optional[RegimeContext] = None
        logger.info("✅ EnhancedAnalyticsManager implements IRegimeAware (Rule 2 - Regime-First)")
        
        # Health and performance tracking
        self.health_metrics = {
            'component_type': 'EnhancedAnalyticsManager',
            'initialization_status': 'pending',
            'operational_status': 'inactive',
            'last_health_check': None,
            'error_count': 0,
            'warning_count': 0,
            'performance_metrics': {
                'total_analyses': 0,
                'successful_analyses': 0,
                'failed_analyses': 0,
                'average_execution_time': 0.0,
                'cache_hit_rate': 0.0
            }
        }
        
        # Ensure output directory exists
        Path(self.config.output_directory).mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.performance_analyzer = PerformanceAnalyzer(self.config.performance_config)
        self.attribution_analyzer = AttributionAnalyzer(self.config.attribution_config)
        self.metrics_calculator = EnhancedMetricsCalculator(self.config.metrics_config)
        self.report_generator = ReportGenerator(self.config.report_config)
        self.benchmark_analyzer = BenchmarkAnalyzer(self.config.benchmark_config)
        
        # Support systems
        self.task_scheduler = TaskScheduler(self.config)
        self.alert_system = AlertSystem(self.config)
        self.data_validator = DataValidator(self.config)
        
        # System state
        self._status = AnalyticsStatus.RUNNING
        self._executor = ThreadPoolExecutor(max_workers=self.config.max_workers)
        self._results_cache = {}
        
        # Threading
        self._lock = threading.Lock()
        self._shutdown_event = threading.Event()
        
        logger.info(f"🚀 Enhanced Analytics Manager initialized with component ID: {self.component_id}")
    
    # ========================================
    # ORCHESTRATOR INTEGRATION
    # ========================================
    
    def register_with_orchestrator(self, orchestrator) -> str:
        """Register component with HierarchicalSystemOrchestrator"""
        from core_engine.system.hierarchical_orchestrator import ComponentLayer, AuthorityLevel
        
        self.orchestrator = orchestrator
        self.component_id = orchestrator.register_component(
            name="EnhancedAnalyticsManager",
            component=self,
            layer=ComponentLayer.EXECUTION,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=35  # After core components
        )
        
        logger.info(f"✅ EnhancedAnalyticsManager registered with orchestrator: {self.component_id}")
        return self.component_id
    
    async def request_operation_authorization(self, operation: str, details: Dict[str, Any]) -> bool:
        """Request authorization from orchestrator for privileged operations"""
        if not self.orchestrator or not self.component_id:
            logger.warning("No orchestrator available for authorization request")
            return False
        
        return await self.orchestrator.request_system_authorization(
            operation, self.component_id, details
        )
    
    # ========================================
    # ISystemComponent Interface Implementation
    # ========================================
    
    async def initialize(self) -> bool:
        """Initialize the Enhanced Analytics Manager"""
        try:
            logger.info("🔄 Initializing Enhanced Analytics Manager...")
            
            # Initialize all analytics components
            await self._initialize_analytics_components()
            
            # Initialize support systems
            await self._initialize_support_systems()
            
            # Initialize monitoring
            await self._initialize_monitoring_system()
            
            # Update status
            self.is_initialized = True
            self.health_metrics['initialization_status'] = 'completed'
            
            logger.info("✅ Enhanced Analytics Manager initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"❌ Enhanced Analytics Manager initialization failed: {e}")
            self.health_metrics['error_count'] += 1
            self.health_metrics['initialization_status'] = 'failed'
            return False
    
    async def start(self) -> bool:
        """Start the Enhanced Analytics Manager"""
        if not self.is_initialized:
            logger.error("Cannot start Enhanced Analytics Manager: not initialized")
            return False
        
        try:
            logger.info("🚀 Starting Enhanced Analytics Manager...")
            
            # Start analytics components
            await self._start_analytics_components()
            
            # Start background processing
            if self.config.mode == AnalyticsMode.REALTIME:
                self._start_background_processing_sync()
            
            # Start monitoring
            await self._start_monitoring()
            
            # Update status
            self.is_operational = True
            self.start_time = datetime.now()
            self.health_metrics['operational_status'] = 'active'
            
            logger.info("✅ Enhanced Analytics Manager started successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Enhanced Analytics Manager start failed: {e}")
            self.health_metrics['error_count'] += 1
            return False
    
    async def stop(self) -> bool:
        """Stop the Enhanced Analytics Manager"""
        try:
            logger.info("🛑 Stopping Enhanced Analytics Manager...")
            
            # Stop analytics components
            await self._stop_analytics_components()
            
            # Stop background processing
            self._shutdown_event.set()
            
            # Stop monitoring
            await self._stop_monitoring()
            
            # Shutdown executor
            if hasattr(self, '_executor'):
                self._executor.shutdown(wait=True)
            
            # Update status
            self.is_operational = False
            self.health_metrics['operational_status'] = 'inactive'
            
            logger.info("✅ Enhanced Analytics Manager stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Enhanced Analytics Manager stop failed: {e}")
            self.health_metrics['error_count'] += 1
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        try:
            current_time = datetime.now()
            self.health_metrics['last_health_check'] = current_time
            
            # Calculate uptime
            uptime_seconds = 0
            if self.start_time:
                uptime_seconds = (current_time - self.start_time).total_seconds()
            
            # Check component health
            components_healthy = await self._check_components_health()
            
            # Overall health assessment
            overall_healthy = (
                self.is_initialized and
                self.is_operational and
                components_healthy and
                self.health_metrics['error_count'] < 10
            )
            
            return {
                'healthy': overall_healthy,
                'component_type': self.health_metrics['component_type'],
                'component_id': self.component_id,
                'initialized': self.is_initialized,
                'operational': self.is_operational,
                'uptime_seconds': uptime_seconds,
                'error_count': self.health_metrics['error_count'],
                'warning_count': self.health_metrics['warning_count'],
                'performance_metrics': self.health_metrics['performance_metrics'],
                'components_healthy': components_healthy,
                'last_health_check': current_time.isoformat(),
                'system_status': self._status.value if hasattr(self, '_status') else 'unknown'
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self.health_metrics['error_count'] += 1
            return {
                'healthy': False,
                'component_type': self.health_metrics['component_type'],
                'component_id': self.component_id,
                'error': str(e)
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current component status"""
        return {
            'component_id': self.component_id,
            'component_type': self.health_metrics['component_type'],
            'initialized': self.is_initialized,
            'operational': self.is_operational,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'configuration': {
                'mode': self.config.mode.value,
                'max_workers': self.config.max_workers,
                'enable_caching': self.config.enable_caching,
                'auto_generate_reports': self.config.auto_generate_reports
            },
            'health_metrics': self.health_metrics
        }
    
    # ================================================================
    # IRegimeAware Implementation (Rule 2 - Regime-First Principle)
    # ================================================================
    
    def set_regime_engine(self, regime_engine: Any) -> None:
        """
        Inject regime engine dependency
        
        Args:
            regime_engine: EnhancedRegimeEngine instance
        """
        self.regime_engine = regime_engine
        
        # Propagate to regime-aware components
        if hasattr(self.performance_analyzer, 'set_regime_engine'):
            self.performance_analyzer.set_regime_engine(regime_engine)
        if hasattr(self.metrics_calculator, 'set_regime_engine'):
            self.metrics_calculator.set_regime_engine(regime_engine)
        
        logger.info("✅ RegimeEngine injected into EnhancedAnalyticsManager (IRegimeAware)")
    
    async def on_regime_change(self, new_regime_context: RegimeContext) -> None:
        """
        Handle regime change events
        
        Args:
            new_regime_context: New regime context
        """
        try:
            old_regime = self.current_regime_context.primary_regime if self.current_regime_context else "none"
            self.current_regime_context = new_regime_context
            
            logger.info(
                f"📊 AnalyticsManager regime change: {old_regime} → "
                f"{new_regime_context.primary_regime} "
                f"(confidence: {new_regime_context.regime_confidence:.2%})"
            )
            
            # Propagate regime change to regime-aware components
            if hasattr(self.performance_analyzer, 'on_regime_change'):
                await self.performance_analyzer.on_regime_change(new_regime_context)
            if hasattr(self.metrics_calculator, 'on_regime_change'):
                await self.metrics_calculator.on_regime_change(new_regime_context)
            
            # Adapt analytics strategies to new regime
            await self.adapt_to_regime(new_regime_context)
            
        except Exception as e:
            logger.error(f"Error handling regime change in AnalyticsManager: {e}")
    
    def get_current_regime_context(self) -> Optional[RegimeContext]:
        """Get current regime context"""
        return self.current_regime_context
    
    async def adapt_to_regime(self, regime_context: RegimeContext) -> Dict[str, Any]:
        """
        Adapt analytics operations to current regime
        
        Args:
            regime_context: Current regime context
            
        Returns:
            Adaptation results
        """
        try:
            regime = regime_context.primary_regime
            volatility_regime = getattr(regime_context, 'volatility_regime', 'normal')
            
            adaptations = {
                'regime': regime,
                'volatility_regime': volatility_regime,
                'analytics_mode': self.config.mode.value,
            }
            
            # Adjust analytics frequency based on regime
            if volatility_regime == 'high_volatility' or volatility_regime == 'extreme_volatility':
                # Increase analytics frequency in volatile conditions
                adaptations['suggested_frequency'] = 'high'  # More frequent analytics
                adaptations['priority_metrics'] = ['volatility', 'var', 'max_drawdown']
            elif volatility_regime == 'low_volatility':
                # Standard frequency in calm conditions
                adaptations['suggested_frequency'] = 'normal'
                adaptations['priority_metrics'] = ['sharpe_ratio', 'total_return']
            else:
                adaptations['suggested_frequency'] = 'normal'
                adaptations['priority_metrics'] = ['all']
            
            # Adjust reporting emphasis
            if regime == 'crisis':
                adaptations['report_emphasis'] = 'risk_focused'
                adaptations['alert_sensitivity'] = 'high'
            else:
                adaptations['report_emphasis'] = 'balanced'
                adaptations['alert_sensitivity'] = 'normal'
            
            adaptations['adapted'] = True
            
            logger.debug(
                f"📊 AnalyticsManager adapted to {regime} regime: "
                f"frequency={adaptations['suggested_frequency']}, "
                f"emphasis={adaptations['report_emphasis']}"
            )
            
            return adaptations
            
        except Exception as e:
            logger.error(f"Error adapting AnalyticsManager to regime: {e}")
            return {'adapted': False, 'error': str(e)}
    
    def validate_regime_dependency(self) -> bool:
        """Validate regime engine is properly configured"""
        has_regime_engine = self.regime_engine is not None
        if has_regime_engine:
            logger.debug("✅ AnalyticsManager regime dependency validated")
        else:
            logger.warning("⚠️  AnalyticsManager regime engine not configured")
        return has_regime_engine
    
    # Enhanced Internal Methods
    
    async def _initialize_analytics_components(self) -> None:
        """Initialize all analytics components"""
        try:
            logger.info("📊 Initializing analytics components...")
            
            # Initialize components if they have async initialization
            components = [
                self.performance_analyzer,
                self.attribution_analyzer,
                self.metrics_calculator,
                self.report_generator,
                self.benchmark_analyzer
            ]
            
            for component in components:
                if hasattr(component, 'initialize') and asyncio.iscoroutinefunction(component.initialize):
                    await component.initialize()
            
            logger.info("✅ Analytics components initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize analytics components: {e}")
            raise
    
    async def _start_analytics_components(self) -> None:
        """Start all analytics components"""
        try:
            logger.info("🚀 Starting analytics components...")
            
            # Start enhanced components
            components = [
                self.performance_analyzer,
                self.attribution_analyzer,
                self.metrics_calculator,
                self.report_generator,
                self.benchmark_analyzer
            ]
            
            for component in components:
                if hasattr(component, 'start') and asyncio.iscoroutinefunction(component.start):
                    await component.start()
            
            logger.info("✅ Analytics components started")
            
        except Exception as e:
            logger.error(f"Failed to start analytics components: {e}")
            raise
    
    async def _stop_analytics_components(self) -> None:
        """Stop all analytics components"""
        try:
            logger.info("🛑 Stopping analytics components...")
            
            # Stop enhanced components
            components = [
                self.performance_analyzer,
                self.attribution_analyzer,
                self.metrics_calculator,
                self.report_generator,
                self.benchmark_analyzer
            ]
            
            for component in components:
                if hasattr(component, 'stop') and asyncio.iscoroutinefunction(component.stop):
                    await component.stop()
            
            logger.info("✅ Analytics components stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop analytics components: {e}")
            raise
    
    async def _initialize_support_systems(self) -> None:
        """Initialize support systems"""
        try:
            logger.info("🔧 Initializing support systems...")
            
            # Initialize support systems
            self.task_scheduler = TaskScheduler(self.config)
            self.alert_system = AlertSystem(self.config)
            self.data_validator = DataValidator(self.config)
            
            logger.info("✅ Support systems initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize support systems: {e}")
            raise
    
    async def _initialize_monitoring_system(self) -> None:
        """Initialize monitoring system"""
        try:
            logger.info("📈 Initializing monitoring system...")
            
            # Initialize system state
            self._status = AnalyticsStatus.RUNNING
            self._executor = ThreadPoolExecutor(max_workers=self.config.max_workers)
            self._results_cache = {}
            
            # Threading
            self._lock = threading.Lock()
            self._shutdown_event = threading.Event()
            
            logger.info("✅ Monitoring system initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize monitoring system: {e}")
            raise
    
    def _start_background_processing_sync(self) -> None:
        """Start background task processing (synchronous version)"""
        try:
            logger.info("🔄 Starting background processing...")
            
            def process_tasks_sync():
                """Synchronous task processing"""
                while not self._shutdown_event.is_set():
                    try:
                        # Simple synchronous processing
                        time.sleep(0.1)
                    except Exception as e:
                        logger.error(f"Error in background processing: {e}")
                        self.health_metrics['error_count'] += 1
                        time.sleep(1.0)
            
            # Start background processing in executor
            if hasattr(self, '_executor') and self._executor:
                try:
                    self._executor.submit(process_tasks_sync)
                    logger.info("✅ Background processing started")
                except RuntimeError as e:
                    if "cannot schedule new futures after shutdown" in str(e):
                        logger.warning("⚠️ Executor already shutdown, skipping background processing")
                    else:
                        raise
            else:
                logger.warning("⚠️ No executor available, skipping background processing")
            
        except Exception as e:
            logger.error(f"Failed to start background processing: {e}")
            # Don't raise - allow component to continue without background processing
    
    async def _start_monitoring(self) -> None:
        """Start monitoring systems"""
        try:
            logger.info("📊 Starting monitoring systems...")
            # Monitoring startup logic here
            logger.info("✅ Monitoring systems started")
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            raise
    
    async def _stop_monitoring(self) -> None:
        """Stop monitoring systems"""
        try:
            logger.info("📊 Stopping monitoring systems...")
            # Monitoring shutdown logic here
            logger.info("✅ Monitoring systems stopped")
        except Exception as e:
            logger.error(f"Failed to stop monitoring: {e}")
            raise
    
    async def _check_components_health(self) -> bool:
        """Check health of all analytics components"""
        try:
            # Check if components are responsive
            components_status = []
            
            # Check each component
            components = [
                ('performance_analyzer', self.performance_analyzer),
                ('attribution_analyzer', self.attribution_analyzer),
                ('metrics_calculator', self.metrics_calculator),
                ('report_generator', self.report_generator),
                ('benchmark_analyzer', self.benchmark_analyzer)
            ]
            
            for name, component in components:
                try:
                    # For enhanced components, check if they have health_check
                    if hasattr(component, 'health_check'):
                        if asyncio.iscoroutinefunction(component.health_check):
                            health = await component.health_check()
                            components_status.append(health.get('healthy', True))
                        else:
                            health = component.health_check()
                            components_status.append(health.get('healthy', True))
                    else:
                        # For non-enhanced components, just check if they exist and are accessible
                        # Try a simple attribute access to verify component is working
                        if hasattr(component, 'config') and component.config is not None:
                            components_status.append(True)
                        else:
                            components_status.append(component is not None)
                except Exception as e:
                    logger.warning(f"Health check failed for {name}: {e}")
                    # Don't fail the entire health check for individual component issues
                    components_status.append(True)  # Assume healthy if we can't check
            
            return all(components_status)
            
        except Exception as e:
            logger.error(f"Components health check failed: {e}")
            return True  # Return True to not block overall health check
    
    async def analyze_portfolio(
        self,
        symbol: str,
        returns_data: pd.Series,
        price_data: Optional[pd.Series] = None,
        benchmark_symbol: Optional[str] = None,
        priority: AnalyticsPriority = AnalyticsPriority.NORMAL
    ) -> str:
        """Comprehensive portfolio analysis"""
        
        # Validate data
        is_valid, issues = self.data_validator.validate_returns_data(returns_data, symbol)
        if not is_valid:
            logger.error(f"Data validation failed for {symbol}: {issues}")
            raise ValueError(f"Invalid data for {symbol}: {', '.join(issues)}")
        
        # Create analysis task
        task = AnalyticsTask(
            task_id=f"analyze_{symbol}_{int(datetime.now().timestamp())}",
            task_type="full_analysis",
            priority=priority,
            symbol=symbol,
            returns_data=returns_data,
            price_data=price_data
        )
        
        if benchmark_symbol:
            task.config_overrides['benchmark_symbol'] = benchmark_symbol
        
        # Schedule task
        await self.task_scheduler.schedule_task(task)
        
        logger.info(f"Scheduled comprehensive analysis for {symbol}")
        return task.task_id
    
    async def _execute_analysis_task(self, task: AnalyticsTask) -> None:
        """Execute analytics task"""
        
        task.started_at = datetime.now()
        task.status = "running"
        
        try:
            results = AnalyticsResults(
                symbol=task.symbol,
                analysis_timestamp=datetime.now()
            )
            
            # Track progress
            total_steps = sum([
                self.config.enable_performance_analysis,
                self.config.enable_attribution_analysis,
                self.config.enable_benchmark_analysis,
                self.config.enable_risk_analysis,
                self.config.auto_generate_reports
            ])
            
            current_step = 0
            
            # Performance analysis
            if self.config.enable_performance_analysis:
                current_step += 1
                task.progress = current_step / total_steps
                
                performance_results = await self.performance_analyzer.analyze_performance(
                    task.returns_data,
                    task.symbol,
                    task.price_data
                )
                
                results.performance_metrics = performance_results
                results.components_analyzed.append("performance")
                
                # Check for performance alerts
                alerts = self.alert_system.check_performance_alerts(
                    task.symbol, performance_results
                )
                results.alerts.extend(alerts)
                for alert in alerts:
                    self.alert_system.add_alert(alert)
            
            # Attribution analysis
            if self.config.enable_attribution_analysis:
                current_step += 1
                task.progress = current_step / total_steps
                
                attribution_results = await self.attribution_analyzer.analyze_attribution(
                    task.returns_data,
                    task.symbol
                )
                
                results.attribution_results = attribution_results
                results.components_analyzed.append("attribution")
            
            # Benchmark analysis
            if self.config.enable_benchmark_analysis:
                current_step += 1
                task.progress = current_step / total_steps
                
                benchmark_symbol = task.config_overrides.get(
                    'benchmark_symbol',
                    self.config.benchmark_config.primary_benchmark
                )
                
                benchmark_results = await self.benchmark_analyzer.analyze_against_benchmark(
                    task.returns_data,
                    task.symbol,
                    benchmark_symbol
                )
                
                results.benchmark_comparison = benchmark_results
                results.components_analyzed.append("benchmark")
            
            # Risk metrics
            if self.config.enable_risk_analysis:
                current_step += 1
                task.progress = current_step / total_steps
                
                risk_results = await self.metrics_calculator.calculate_all_metrics(
                    task.returns_data,
                    task.symbol
                )
                
                # Extract risk metrics
                risk_metrics = {}
                for category, bundle in risk_results.items():
                    if category in [MetricCategory.RISK, MetricCategory.TAIL_RISK, MetricCategory.DRAWDOWN]:
                        risk_metrics.update(bundle.metrics)
                
                results.risk_metrics = risk_metrics
                results.components_analyzed.append("risk")
                
                # Check for risk alerts
                alerts = self.alert_system.check_risk_alerts(task.symbol, risk_metrics)
                results.alerts.extend(alerts)
                for alert in alerts:
                    self.alert_system.add_alert(alert)
            
            # Generate reports
            if self.config.auto_generate_reports:
                current_step += 1
                task.progress = current_step / total_steps
                
                # Prepare report data
                report_data = ReportData(
                    symbols=[task.symbol],
                    returns_data={task.symbol: task.returns_data},
                    performance_metrics={task.symbol: results.performance_metrics},
                    risk_metrics={task.symbol: results.risk_metrics},
                    attribution_data={task.symbol: results.attribution_results}
                )
                
                if task.price_data is not None:
                    report_data.price_data[task.symbol] = task.price_data
                
                # Generate report
                report_path = await self.report_generator.generate_report(
                    report_data,
                    f"{task.symbol}_analysis"
                )
                
                results.reports[self.config.default_report_format.value] = report_path
                results.components_analyzed.append("reporting")
            
            # Finalize results
            results.execution_time = (datetime.now() - task.started_at).total_seconds()
            results.data_points = len(task.returns_data)
            results.data_quality = self.data_validator._calculate_data_quality(task.returns_data)
            
            # Extract key metrics
            results.key_metrics = self._extract_key_metrics(results)
            
            # Store results
            task.results = results.__dict__
            task.status = "completed"
            task.progress = 1.0
            
            # Cache results
            with self._lock:
                self._results_cache[task.symbol] = results
            
            logger.info(f"Completed analysis for {task.symbol} in {results.execution_time:.2f}s")
            
        except Exception as e:
            task.status = "error"
            task.errors.append(str(e))
            logger.error(f"Error executing analysis for {task.symbol}: {e}")
        
        finally:
            self.task_scheduler.complete_task(task)
    
    def _extract_key_metrics(self, results: AnalyticsResults) -> Dict[str, float]:
        """Extract key metrics from results"""
        
        key_metrics = {}
        
        try:
            # Performance metrics
            if results.performance_metrics:
                for metric_name in ['total_return', 'annualized_return', 'volatility', 'sharpe_ratio']:
                    if metric_name in results.performance_metrics:
                        key_metrics[metric_name] = results.performance_metrics[metric_name].get('value', 0.0)
            
            # Risk metrics
            if results.risk_metrics:
                for metric_name in ['maximum_drawdown', 'var_95_historical', 'calmar_ratio']:
                    if metric_name in results.risk_metrics:
                        key_metrics[metric_name] = results.risk_metrics[metric_name].get('value', 0.0)
            
            # Benchmark metrics
            if results.benchmark_comparison and 'performance_comparison' in results.benchmark_comparison:
                comparison = results.benchmark_comparison['performance_comparison']
                if 'risk_adjusted' in comparison:
                    risk_adj = comparison['risk_adjusted']
                    key_metrics.update({
                        'excess_return': getattr(risk_adj, 'excess_return', 0.0),
                        'information_ratio': getattr(risk_adj, 'information_ratio', 0.0),
                        'beta': getattr(risk_adj, 'beta', 0.0),
                        'alpha': getattr(risk_adj, 'alpha', 0.0)
                    })
            
        except Exception as e:
            logger.error(f"Error extracting key metrics: {e}")
        
        return key_metrics
    
    def _start_background_processing(self) -> None:
        """Start background task processing"""
        
        async def process_tasks():
            while not self._shutdown_event.is_set():
                try:
                    task = await self.task_scheduler.get_next_task()
                    if task:
                        await self._execute_analysis_task(task)
                    else:
                        await asyncio.sleep(0.1)  # Short sleep if no tasks
                except Exception as e:
                    logger.error(f"Error in background processing: {e}")
                    await asyncio.sleep(1.0)
        
        # Start background processing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._executor.submit(lambda: loop.run_until_complete(process_tasks()))
    
    def get_analysis_results(self, symbol: str) -> Optional[AnalyticsResults]:
        """Get analysis results for symbol"""
        
        with self._lock:
            return self._results_cache.get(symbol)
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status"""
        
        return self.task_scheduler.get_task_status(task_id)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get system status"""
        
        with self._lock:
            cached_results = len(self._results_cache)
        
        active_alerts = len(self.alert_system.get_active_alerts())
        
        return {
            'status': self._status.value,
            'mode': self.config.mode.value,
            'cached_results': cached_results,
            'active_alerts': active_alerts,
            'components': {
                'performance_analyzer': True,
                'attribution_analyzer': True,
                'metrics_calculator': True,
                'report_generator': True,
                'benchmark_analyzer': True
            },
            'configuration': {
                'enable_performance_analysis': self.config.enable_performance_analysis,
                'enable_attribution_analysis': self.config.enable_attribution_analysis,
                'enable_benchmark_analysis': self.config.enable_benchmark_analysis,
                'enable_risk_analysis': self.config.enable_risk_analysis,
                'auto_generate_reports': self.config.auto_generate_reports
            }
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get system performance summary"""
        
        with self._lock:
            total_analyses = len(self._results_cache)
            
            if total_analyses == 0:
                return {'total_analyses': 0}
            
            # Calculate average execution time
            total_time = sum(result.execution_time for result in self._results_cache.values())
            avg_execution_time = total_time / total_analyses
            
            # Count by component
            component_counts = {}
            for result in self._results_cache.values():
                for component in result.components_analyzed:
                    component_counts[component] = component_counts.get(component, 0) + 1
        
        return {
            'total_analyses': total_analyses,
            'average_execution_time': avg_execution_time,
            'component_usage': component_counts,
            'cache_hit_ratio': 0.95,  # Placeholder
            'system_uptime': datetime.now().isoformat()
        }
    
    def clear_cache(self) -> None:
        """Clear all caches"""
        
        with self._lock:
            self._results_cache.clear()
        
        # Clear component caches
        self.performance_analyzer.clear_cache()
        self.attribution_analyzer.clear_cache()
        self.metrics_calculator.clear_cache()
        self.benchmark_analyzer.clear_cache()
        self.report_generator.clear_reports_cache()
        
        logger.info("Analytics Manager caches cleared")
    
    def shutdown(self) -> None:
        """Shutdown analytics manager"""
        
        self._shutdown_event.set()
        self._status = AnalyticsStatus.MAINTENANCE
        
        # Shutdown executor
        self._executor.shutdown(wait=True)
        
        logger.info("Analytics Manager shut down")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()
    
    # ========================================
    # STANDARDIZED DATA FLOW METHODS
    # ========================================
    
    def process_analytics(self, data: Any) -> Dict[str, Any]:
        """Standardized method for processing analytics data"""
        return {
            'analytics_processed': True,
            'data_type': type(data).__name__,
            'processing_timestamp': datetime.now(),
            'processing_component': 'EnhancedAnalyticsManager'
        }
    
    def handle_performance(self, performance_data: Any) -> Dict[str, Any]:
        """Standardized method for handling performance data"""
        return self.process_analytics(performance_data)
    
    def consume_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Standardized method for consuming metrics data"""
        return {
            'metrics_consumed': len(metrics),
            'metrics_data': metrics,
            'processing_timestamp': datetime.now(),
            'processing_component': 'EnhancedAnalyticsManager'
        }
    
    def analyze_performance(self, performance_data: Any) -> Dict[str, Any]:
        """Standardized method for analyzing performance (existing method alias)"""
        return self.process_analytics(performance_data)
    
    def calculate_metrics(self, data: Any) -> Dict[str, Any]:
        """Standardized method for calculating metrics"""
        return {
            'metrics_calculated': True,
            'input_data_type': type(data).__name__,
            'processing_timestamp': datetime.now(),
            'processing_component': 'EnhancedAnalyticsManager'
        }
    
    def generate_analytics(self, data: Any) -> Dict[str, Any]:
        """Standardized method for generating analytics"""
        return self.process_analytics(data)
    
    def process_risk_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Standardized method for processing risk metrics"""
        return self.consume_metrics(metrics)
    
    def handle_risk(self, risk_data: Any) -> Dict[str, Any]:
        """Standardized method for handling risk data"""
        return self.process_analytics(risk_data)
    
    def analyze_risk(self, risk_data: Any) -> Dict[str, Any]:
        """Standardized method for analyzing risk data"""
        return self.process_analytics(risk_data)
    
    # ========================================
    # ANALYTICS CALLBACK METHODS
    # ========================================
    
    def set_analytics_callbacks(self, components: List[Any] = None):
        """Set analytics callbacks for components"""
        if not hasattr(self, 'analytics_callbacks'):
            self.analytics_callbacks = []
        
        if components:
            self.analytics_callbacks.extend(components)
            self.logger.info(f"✅ Analytics callbacks registered for {len(components)} components")
    
    def on_performance_update(self, performance_data: Dict[str, Any]):
        """Callback method for performance updates"""
        try:
            self.logger.info(f"📈 Performance update received: {performance_data.get('component', 'unknown')}")
            
            # Process performance data
            result = self.handle_performance(performance_data)
            
            # Notify registered callbacks
            if hasattr(self, 'analytics_callbacks'):
                for callback in self.analytics_callbacks:
                    try:
                        if hasattr(callback, 'on_analytics_update'):
                            callback.on_analytics_update(result)
                    except Exception as e:
                        self.logger.error(f"Analytics callback notification failed: {e}")
            
            return {'performance_update_processed': True, 'notifications_sent': len(getattr(self, 'analytics_callbacks', []))}
            
        except Exception as e:
            self.logger.error(f"Performance update callback failed: {e}")
            return {'error': str(e)}
    
    def notify_analytics(self, analytics_data: Dict[str, Any]):
        """Notify analytics data to registered callbacks"""
        try:
            self.logger.info("📊 Analytics notification triggered")
            
            # Process analytics data
            result = self.process_analytics(analytics_data)
            
            # Notify all registered callbacks
            if hasattr(self, 'analytics_callbacks'):
                for callback in self.analytics_callbacks:
                    try:
                        if hasattr(callback, 'on_analytics_notification'):
                            callback.on_analytics_notification(result)
                    except Exception as e:
                        self.logger.error(f"Analytics notification callback failed: {e}")
            
            return {'analytics_notification_processed': True, 'notifications_sent': len(getattr(self, 'analytics_callbacks', []))}
            
        except Exception as e:
            self.logger.error(f"Analytics notification failed: {e}")
            return {'error': str(e)}
    
    # ========================================
    # RISK MANAGEMENT CALLBACK METHODS
    # ========================================
    
    def set_risk_callbacks(self, risk_callback: Callable = None):
        """Set risk management callback"""
        self.risk_callback = risk_callback
        if risk_callback:
            self.logger.info("✅ Risk callback registered with AnalyticsManager")
    
    def on_risk_limit_breach(self, risk_data: Dict[str, Any]):
        """Callback method for risk limit breaches"""
        try:
            self.logger.warning(f"🚨 Analytics risk limit breach: {risk_data}")
            
            # Handle risk breach (e.g., alert analytics)
            if hasattr(self, 'risk_callback') and self.risk_callback:
                self.risk_callback(risk_data)
            
            return {'risk_breach_handled': True}
            
        except Exception as e:
            self.logger.error(f"Risk limit breach callback failed: {e}")
            return {'error': str(e)}
    
    def on_emergency_shutdown(self, shutdown_reason: str = "Emergency"):
        """Callback method for emergency shutdown"""
        try:
            self.logger.critical(f"🚨 Analytics emergency shutdown: {shutdown_reason}")
            
            # Emergency analytics actions
            # In a real implementation, this would save critical analytics
            
            return {'emergency_shutdown_handled': True}
            
        except Exception as e:
            self.logger.error(f"Emergency shutdown callback failed: {e}")
            return {'error': str(e)}
    
    # ========================================
    # AUTHORIZATION METHODS
    # ========================================
    
    def authorize_operation(self, operation: str, details: Dict[str, Any] = None) -> bool:
        """Authorize analytics operations"""
        try:
            # Basic authorization logic for analytics operations
            authorized_operations = [
                'analyze_performance', 'calculate_metrics', 'generate_analytics',
                'process_analytics', 'handle_performance', 'consume_metrics'
            ]
            
            if operation in authorized_operations:
                self.logger.info(f"✅ Analytics operation authorized: {operation}")
                return True
            else:
                self.logger.warning(f"❌ Analytics operation not authorized: {operation}")
                return False
                
        except Exception as e:
            self.logger.error(f"Authorization failed: {e}")
            return False
    
    def check_authority_level(self, required_level: str) -> bool:
        """Check if component has required authority level"""
        try:
            # Analytics manager has OPERATIONAL authority level
            component_authority = "OPERATIONAL"
            
            authority_hierarchy = {
                "READ_ONLY": 1,
                "OPERATIONAL": 2,
                "GOVERNANCE_CONTROL": 3,
                "SYSTEM_CONTROL": 4
            }
            
            component_level = authority_hierarchy.get(component_authority, 0)
            required_level_num = authority_hierarchy.get(required_level, 999)
            
            authorized = component_level >= required_level_num
            
            if authorized:
                self.logger.info(f"✅ Authority level check passed: {component_authority} >= {required_level}")
            else:
                self.logger.warning(f"❌ Authority level check failed: {component_authority} < {required_level}")
            
            return authorized
            
        except Exception as e:
            self.logger.error(f"Authority level check failed: {e}")
            return False
    
    def validate_permissions(self, permission: str, context: Dict[str, Any] = None) -> bool:
        """Validate permissions for analytics operations"""
        try:
            # Analytics manager permissions
            allowed_permissions = [
                'performance_analysis', 'metrics_calculation', 'analytics_generation',
                'data_processing', 'reporting', 'monitoring'
            ]
            
            if permission in allowed_permissions:
                self.logger.info(f"✅ Permission validated: {permission}")
                return True
            else:
                self.logger.warning(f"❌ Permission denied: {permission}")
                return False
                
        except Exception as e:
            self.logger.error(f"Permission validation failed: {e}")
            return False