"""
Data Engine - Enhanced Data Manager
Comprehensive data management with integrated handlers, validation, caching, and feed orchestration
"""

import logging
import threading
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import deque

# Import our data components
from .market_data import MarketDataHandler, MarketDataRequest, MarketDataResponse
from ..alternative_data_handler import AlternativeDataHandler, AlternativeDataRequest, AlternativeDataResponse
from ..validation.validator import DataValidator, ValidationResult, ValidationRule
from ..cache.manager import CacheManager, CacheLevel
from ..feeds.manager import FeedManager, FeedConfiguration, FeedMessage, FeedType

logger = logging.getLogger(__name__)


class DataEngineMode(Enum):
    """Data engine operating modes"""
    LIVE = "live"
    SIMULATION = "simulation"
    BACKTEST = "backtest"
    RESEARCH = "research"


class DataPriority(Enum):
    """Data priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BATCH = "batch"


class DataSource(Enum):
    """Data source types"""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    BACKUP = "backup"
    DERIVED = "derived"
    CACHED = "cached"


@dataclass
class DataEngineConfig:
    """Data engine configuration"""
    mode: DataEngineMode = DataEngineMode.LIVE
    
    # Component enablement
    enable_market_data: bool = True
    enable_alternative_data: bool = True
    enable_data_validation: bool = True
    enable_caching: bool = True
    enable_feed_management: bool = True
    
    # Performance settings
    max_concurrent_requests: int = 100
    request_timeout_seconds: float = 30.0
    data_retention_days: int = 365
    
    # Cache settings
    cache_config: Optional[Dict[str, Any]] = None
    
    # Validation settings
    validation_config: Optional[Dict[str, Any]] = None
    
    # Feed settings
    feed_config: Optional[Dict[str, Any]] = None
    
    # Quality settings
    enable_data_quality_monitoring: bool = True
    quality_threshold: float = 0.95
    
    # Performance monitoring
    enable_performance_monitoring: bool = True
    monitoring_interval_seconds: float = 60.0
    
    # Error handling
    max_retry_attempts: int = 3
    retry_delay_seconds: float = 1.0
    enable_circuit_breaker: bool = True
    
    # Storage settings
    enable_persistence: bool = True
    storage_path: Optional[str] = None
    
    # Advanced features
    enable_data_lineage: bool = True
    enable_audit_trail: bool = True
    enable_compression: bool = True


@dataclass
class DataRequest:
    """Unified data request"""
    request_id: str
    data_type: str
    symbols: List[str]
    fields: List[str]
    
    # Time range
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Request metadata
    priority: DataPriority = DataPriority.NORMAL
    source_preference: List[DataSource] = field(default_factory=lambda: [DataSource.PRIMARY])
    
    # Caching
    use_cache: bool = True
    cache_ttl_seconds: Optional[float] = None
    
    # Validation
    validate_data: bool = True
    validation_rules: List[str] = field(default_factory=list)
    
    # Format options
    format_type: str = "dataframe"  # dataframe, dict, json
    include_metadata: bool = True
    
    # Quality requirements
    min_quality_score: float = 0.8
    allow_partial_data: bool = True
    
    # Callback
    callback: Optional[Callable] = None
    
    # Custom parameters
    custom_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataResponse:
    """Unified data response"""
    request_id: str
    success: bool
    data: Any
    metadata: Dict[str, Any]
    
    # Quality information
    quality_score: Optional[float] = None
    validation_results: Optional[List[ValidationResult]] = None
    
    # Source information
    data_source: DataSource = DataSource.PRIMARY
    source_timestamp: Optional[datetime] = None
    
    # Performance metrics
    processing_time_ms: float = 0.0
    cache_hit: bool = False
    
    # Error information
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    
    # Response timestamp
    response_timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DataEngineStatistics:
    """Data engine performance statistics"""
    # Request statistics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    cached_requests: int = 0
    
    # Performance metrics
    average_response_time_ms: float = 0.0
    cache_hit_rate: float = 0.0
    data_quality_average: float = 0.0
    
    # Component statistics
    market_data_requests: int = 0
    alternative_data_requests: int = 0
    validation_runs: int = 0
    
    # Error statistics
    validation_errors: int = 0
    cache_errors: int = 0
    feed_errors: int = 0
    processing_errors: int = 0
    
    # Resource usage
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    network_bandwidth_mbps: float = 0.0
    
    # Data volume
    total_data_processed_mb: float = 0.0
    records_processed: int = 0
    
    # Uptime
    uptime_seconds: float = 0.0
    last_reset_time: datetime = field(default_factory=datetime.now)
    last_update_time: datetime = field(default_factory=datetime.now)


class DataEngine:
    """
    Enhanced Data Management Engine
    
    Provides unified interface for all data operations with integrated
    market data, alternative data, validation, caching, and feed management.
    """
    
    def __init__(self, config: Optional[DataEngineConfig] = None):
        """Initialize data engine"""
        self.config = config or DataEngineConfig()
        
        # Component initialization
        self.market_data_handler = None
        self.alternative_data_handler = None
        self.data_validator = None
        self.cache_manager = None
        self.feed_manager = None
        
        # Initialize enabled components
        self._initialize_components()
        
        # Request tracking
        self._active_requests = {}
        self._request_history = deque(maxlen=10000)
        
        # Threading
        self._lock = threading.Lock()
        self._executor = None
        
        # Statistics
        self._statistics = DataEngineStatistics()
        self._start_time = datetime.now()
        
        # Event handlers
        self._data_handlers = []
        self._error_handlers = []
        self._status_handlers = []
        
        # Circuit breaker
        self._circuit_breaker_open = False
        self._circuit_breaker_failures = 0
        self._circuit_breaker_last_failure = None
        
        # Background tasks
        self._monitoring_tasks = []
        
        # Data lineage tracking
        self._data_lineage = {} if self.config.enable_data_lineage else None
        
        # Start monitoring
        if self.config.enable_performance_monitoring:
            asyncio.create_task(self._start_monitoring())
        
        logger.info("DataEngine initialized")
    
    def _initialize_components(self) -> None:
        """Initialize data engine components"""
        
        try:
            # Market data handler
            if self.config.enable_market_data:
                self.market_data_handler = MarketDataHandler()
                logger.info("Market data handler initialized")
            
            # Alternative data handler
            if self.config.enable_alternative_data:
                self.alternative_data_handler = AlternativeDataHandler()
                logger.info("Alternative data handler initialized")
            
            # Data validator
            if self.config.enable_data_validation:
                validation_config = self.config.validation_config or {}
                self.data_validator = DataValidator(validation_config)
                logger.info("Data validator initialized")
            
            # Cache manager
            if self.config.enable_caching:
                cache_config = self.config.cache_config or {}
                self.cache_manager = CacheManager(cache_config)
                logger.info("Cache manager initialized")
            
            # Feed manager
            if self.config.enable_feed_management:
                feed_config = self.config.feed_config or {}
                self.feed_manager = FeedManager(feed_config)
                
                # Set up feed message handler
                self.feed_manager.add_message_handler(self._handle_feed_message)
                logger.info("Feed manager initialized")
            
        except Exception as e:
            logger.error(f"Error initializing components: {e}")
            raise
    
    async def get_data(self, request: DataRequest) -> DataResponse:
        """Get data with unified interface"""
        
        start_time = time.time()
        
        try:
            # Check circuit breaker
            if self._circuit_breaker_open:
                return self._create_error_response(
                    request.request_id,
                    "Circuit breaker is open",
                    "CIRCUIT_BREAKER_OPEN"
                )
            
            # Track request
            with self._lock:
                self._active_requests[request.request_id] = request
                self._statistics.total_requests += 1
            
            # Check cache first
            cached_response = await self._check_cache(request)
            if cached_response:
                self._update_statistics(request, cached_response, time.time() - start_time)
                return cached_response
            
            # Route request to appropriate handler
            response = await self._route_request(request)
            
            # Validate data if requested
            if request.validate_data and response.success and self.data_validator:
                response = await self._validate_response(request, response)
            
            # Cache response if successful
            if response.success and request.use_cache and self.cache_manager:
                await self._cache_response(request, response)
            
            # Update statistics
            processing_time = time.time() - start_time
            self._update_statistics(request, response, processing_time)
            
            # Record data lineage
            if self.config.enable_data_lineage:
                self._record_lineage(request, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing data request {request.request_id}: {e}")
            
            # Update circuit breaker
            self._update_circuit_breaker(False)
            
            return self._create_error_response(
                request.request_id,
                str(e),
                "PROCESSING_ERROR"
            )
        
        finally:
            # Clean up request tracking
            with self._lock:
                self._active_requests.pop(request.request_id, None)
    
    async def _route_request(self, request: DataRequest) -> DataResponse:
        """Route request to appropriate data handler"""
        
        # Determine handler based on data type
        if request.data_type in ['market_data', 'price', 'quote', 'trade', 'ohlc']:
            if self.market_data_handler:
                return await self._handle_market_data_request(request)
        
        elif request.data_type in ['news', 'sentiment', 'fundamental', 'alternative']:
            if self.alternative_data_handler:
                return await self._handle_alternative_data_request(request)
        
        else:
            # Try to handle with available handlers
            if self.market_data_handler:
                response = await self._handle_market_data_request(request)
                if response.success:
                    return response
            
            if self.alternative_data_handler:
                response = await self._handle_alternative_data_request(request)
                if response.success:
                    return response
        
        return self._create_error_response(
            request.request_id,
            f"No handler available for data type: {request.data_type}",
            "NO_HANDLER"
        )
    
    async def _handle_market_data_request(self, request: DataRequest) -> DataResponse:
        """Handle market data request"""
        
        try:
            # Convert to market data request
            market_request = MarketDataRequest(
                symbols=request.symbols,
                fields=request.fields,
                start_time=request.start_time,
                end_time=request.end_time,
                **request.custom_params
            )
            
            # Get market data
            market_response = await self.market_data_handler.get_data(market_request)
            
            # Convert to unified response
            return DataResponse(
                request_id=request.request_id,
                success=market_response.success,
                data=market_response.data,
                metadata=market_response.metadata,
                data_source=DataSource.PRIMARY,
                source_timestamp=market_response.timestamp,
                error_message=market_response.error_message if not market_response.success else None
            )
            
        except Exception as e:
            logger.error(f"Error handling market data request: {e}")
            return self._create_error_response(
                request.request_id,
                str(e),
                "MARKET_DATA_ERROR"
            )
    
    async def _handle_alternative_data_request(self, request: DataRequest) -> DataResponse:
        """Handle alternative data request"""
        
        try:
            # Convert to alternative data request
            alt_request = AlternativeDataRequest(
                data_type=request.data_type,
                symbols=request.symbols,
                start_time=request.start_time,
                end_time=request.end_time,
                **request.custom_params
            )
            
            # Get alternative data
            alt_response = await self.alternative_data_handler.get_data(alt_request)
            
            # Convert to unified response
            return DataResponse(
                request_id=request.request_id,
                success=alt_response.success,
                data=alt_response.data,
                metadata=alt_response.metadata,
                data_source=DataSource.PRIMARY,
                source_timestamp=alt_response.timestamp,
                error_message=alt_response.error_message if not alt_response.success else None
            )
            
        except Exception as e:
            logger.error(f"Error handling alternative data request: {e}")
            return self._create_error_response(
                request.request_id,
                str(e),
                "ALTERNATIVE_DATA_ERROR"
            )
    
    async def _check_cache(self, request: DataRequest) -> Optional[DataResponse]:
        """Check cache for existing data"""
        
        if not request.use_cache or not self.cache_manager:
            return None
        
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(request)
            
            # Get from cache
            cached_data = await self.cache_manager.get(cache_key)
            
            if cached_data:
                # Create response from cached data
                response = DataResponse(
                    request_id=request.request_id,
                    success=True,
                    data=cached_data['data'],
                    metadata=cached_data['metadata'],
                    cache_hit=True
                )
                
                with self._lock:
                    self._statistics.cached_requests += 1
                
                logger.debug(f"Cache hit for request {request.request_id}")
                return response
            
        except Exception as e:
            logger.error(f"Error checking cache: {e}")
        
        return None
    
    async def _cache_response(self, request: DataRequest, response: DataResponse) -> None:
        """Cache successful response"""
        
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(request)
            
            # Prepare cache data
            cache_data = {
                'data': response.data,
                'metadata': response.metadata,
                'timestamp': response.response_timestamp
            }
            
            # Cache with TTL
            ttl = request.cache_ttl_seconds
            await self.cache_manager.set(cache_key, cache_data, ttl=ttl)
            
            logger.debug(f"Cached response for request {request.request_id}")
            
        except Exception as e:
            logger.error(f"Error caching response: {e}")
    
    def _generate_cache_key(self, request: DataRequest) -> str:
        """Generate cache key for request"""
        
        key_parts = [
            request.data_type,
            ','.join(sorted(request.symbols)),
            ','.join(sorted(request.fields)),
            str(request.start_time) if request.start_time else 'none',
            str(request.end_time) if request.end_time else 'none'
        ]
        
        return ':'.join(key_parts)
    
    async def _validate_response(self, request: DataRequest, response: DataResponse) -> DataResponse:
        """Validate response data"""
        
        try:
            if not response.success or not response.data:
                return response
            
            # Run validation
            validation_results = await self.data_validator.validate_data(
                response.data,
                rules=request.validation_rules
            )
            
            # Calculate quality score
            quality_score = self.data_validator.calculate_quality_score(validation_results)
            
            # Update response
            response.validation_results = validation_results
            response.quality_score = quality_score
            
            # Check quality threshold
            if quality_score < request.min_quality_score:
                response.success = False
                response.error_message = f"Data quality below threshold: {quality_score:.2f} < {request.min_quality_score:.2f}"
                response.error_code = "QUALITY_THRESHOLD"
            
            with self._lock:
                self._statistics.validation_runs += 1
                if not response.success:
                    self._statistics.validation_errors += 1
            
        except Exception as e:
            logger.error(f"Error validating response: {e}")
            response.error_message = f"Validation error: {str(e)}"
            response.error_code = "VALIDATION_ERROR"
            response.success = False
        
        return response
    
    def _create_error_response(
        self,
        request_id: str,
        error_message: str,
        error_code: str
    ) -> DataResponse:
        """Create error response"""
        
        return DataResponse(
            request_id=request_id,
            success=False,
            data=None,
            metadata={},
            error_message=error_message,
            error_code=error_code
        )
    
    def _update_statistics(
        self,
        request: DataRequest,
        response: DataResponse,
        processing_time: float
    ) -> None:
        """Update engine statistics"""
        
        with self._lock:
            stats = self._statistics
            
            # Request counts
            if response.success:
                stats.successful_requests += 1
            else:
                stats.failed_requests += 1
            
            # Cache hits
            if response.cache_hit:
                stats.cached_requests += 1
            
            # Response time
            total_requests = stats.total_requests
            current_avg = stats.average_response_time_ms
            processing_time_ms = processing_time * 1000
            
            stats.average_response_time_ms = (
                (current_avg * (total_requests - 1) + processing_time_ms) / total_requests
            )
            
            # Cache hit rate
            if stats.total_requests > 0:
                stats.cache_hit_rate = stats.cached_requests / stats.total_requests
            
            # Quality score
            if response.quality_score is not None:
                # Update running average of quality scores
                # This is a simplified calculation
                stats.data_quality_average = (
                    (stats.data_quality_average * 0.9) + (response.quality_score * 0.1)
                )
            
            # Data type specific counts
            if request.data_type in ['market_data', 'price', 'quote', 'trade', 'ohlc']:
                stats.market_data_requests += 1
            elif request.data_type in ['news', 'sentiment', 'fundamental', 'alternative']:
                stats.alternative_data_requests += 1
            
            stats.last_update_time = datetime.now()
    
    def _update_circuit_breaker(self, success: bool) -> None:
        """Update circuit breaker state"""
        
        if not self.config.enable_circuit_breaker:
            return
        
        if success:
            # Reset on success
            self._circuit_breaker_failures = 0
            self._circuit_breaker_open = False
        else:
            # Increment failures
            self._circuit_breaker_failures += 1
            self._circuit_breaker_last_failure = datetime.now()
            
            # Open circuit breaker if too many failures
            if self._circuit_breaker_failures >= 5:  # Threshold
                self._circuit_breaker_open = True
                logger.warning("Circuit breaker opened due to repeated failures")
        
        # Auto-reset circuit breaker after timeout
        if (self._circuit_breaker_open and 
            self._circuit_breaker_last_failure and
            (datetime.now() - self._circuit_breaker_last_failure).total_seconds() > 60):  # 1 minute
            
            self._circuit_breaker_open = False
            self._circuit_breaker_failures = 0
            logger.info("Circuit breaker reset after timeout")
    
    def _record_lineage(self, request: DataRequest, response: DataResponse) -> None:
        """Record data lineage"""
        
        if not self._data_lineage:
            return
        
        lineage_entry = {
            'request_id': request.request_id,
            'timestamp': datetime.now(),
            'data_type': request.data_type,
            'symbols': request.symbols,
            'fields': request.fields,
            'data_source': response.data_source.value,
            'success': response.success,
            'quality_score': response.quality_score,
            'cache_hit': response.cache_hit
        }
        
        self._data_lineage[request.request_id] = lineage_entry
    
    def _handle_feed_message(self, message: FeedMessage) -> None:
        """Handle incoming feed message"""
        
        try:
            # Process feed message
            logger.debug(f"Received feed message: {message.feed_id} - {message.symbol}")
            
            # Route to registered handlers
            for handler in self._data_handlers:
                try:
                    handler(message)
                except Exception as e:
                    logger.error(f"Error in data handler: {e}")
            
            # Update cache if applicable
            if self.cache_manager and message.symbol:
                cache_key = f"feed:{message.feed_id}:{message.symbol}"
                asyncio.create_task(
                    self.cache_manager.set(cache_key, message.data, ttl=60)
                )
            
        except Exception as e:
            logger.error(f"Error handling feed message: {e}")
    
    async def _start_monitoring(self) -> None:
        """Start background monitoring tasks"""
        
        self._monitoring_tasks = [
            asyncio.create_task(self._performance_monitoring()),
            asyncio.create_task(self._health_monitoring()),
            asyncio.create_task(self._resource_monitoring())
        ]
        
        logger.info("Started data engine monitoring")
    
    async def _performance_monitoring(self) -> None:
        """Monitor engine performance"""
        
        while True:
            try:
                await asyncio.sleep(self.config.monitoring_interval_seconds)
                
                with self._lock:
                    stats = self._statistics
                    
                    # Calculate uptime
                    stats.uptime_seconds = (datetime.now() - self._start_time).total_seconds()
                    
                    logger.info(f"Data Engine Performance: "
                              f"{stats.successful_requests}/{stats.total_requests} successful, "
                              f"{stats.cache_hit_rate:.1%} cache hit rate, "
                              f"{stats.average_response_time_ms:.2f}ms avg response time")
                
            except Exception as e:
                logger.error(f"Error in performance monitoring: {e}")
                await asyncio.sleep(self.config.monitoring_interval_seconds)
    
    async def _health_monitoring(self) -> None:
        """Monitor component health"""
        
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Check component health
                unhealthy_components = []
                
                if self.market_data_handler and not hasattr(self.market_data_handler, 'is_healthy'):
                    # Add health check methods to components
                    pass
                
                if unhealthy_components:
                    logger.warning(f"Unhealthy components detected: {unhealthy_components}")
                
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(60)
    
    async def _resource_monitoring(self) -> None:
        """Monitor resource usage"""
        
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                # Monitor memory usage, CPU, etc.
                # This would integrate with system monitoring tools
                
                with self._lock:
                    # Update resource statistics
                    # self._statistics.memory_usage_mb = get_memory_usage()
                    # self._statistics.cpu_usage_percent = get_cpu_usage()
                    pass
                
            except Exception as e:
                logger.error(f"Error in resource monitoring: {e}")
                await asyncio.sleep(300)
    
    def add_data_handler(self, handler: Callable[[FeedMessage], None]) -> None:
        """Add data message handler"""
        with self._lock:
            self._data_handlers.append(handler)
    
    def add_error_handler(self, handler: Callable[[str, Exception], None]) -> None:
        """Add error handler"""
        with self._lock:
            self._error_handlers.append(handler)
    
    def get_statistics(self) -> DataEngineStatistics:
        """Get engine statistics"""
        with self._lock:
            return self._statistics
    
    def get_active_requests(self) -> List[DataRequest]:
        """Get currently active requests"""
        with self._lock:
            return list(self._active_requests.values())
    
    def get_data_lineage(self, request_id: Optional[str] = None) -> Dict[str, Any]:
        """Get data lineage information"""
        if not self._data_lineage:
            return {}
        
        if request_id:
            return self._data_lineage.get(request_id, {})
        else:
            return dict(self._data_lineage)
    
    async def warmup(self) -> None:
        """Warm up data engine components"""
        
        logger.info("Warming up data engine...")
        
        # Warm up cache
        if self.cache_manager:
            await self.cache_manager.warmup_cache({})
        
        # Initialize feed connections
        if self.feed_manager:
            await self.feed_manager.start_monitoring()
        
        logger.info("Data engine warmup completed")
    
    async def cleanup(self) -> None:
        """Cleanup data engine resources"""
        
        logger.info("Cleaning up data engine...")
        
        # Cancel monitoring tasks
        for task in self._monitoring_tasks:
            task.cancel()
        
        # Cleanup components
        if self.cache_manager:
            await self.cache_manager.cleanup()
        
        if self.feed_manager:
            await self.feed_manager.cleanup()
        
        logger.info("Data engine cleanup completed")