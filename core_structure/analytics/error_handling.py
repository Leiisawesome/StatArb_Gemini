"""
Enhanced Error Handling for Analytics Module
Implements circuit breakers, retry mechanisms, and error recovery patterns
"""

import asyncio
import time
import random
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
import functools

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Failing fast
    HALF_OPEN = "half_open" # Testing recovery


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    consecutive_failures: int = 0
    last_failure_time: Optional[float] = None
    state_changes: int = 0
    

@dataclass
class RetryConfig:
    """Retry configuration"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_range: float = 0.1
    

class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""
    pass


class MaxRetriesExceededError(Exception):
    """Raised when maximum retry attempts are exceeded"""
    pass


class CircuitBreaker:
    """
    Circuit breaker implementation for external data sources
    
    Prevents cascading failures by:
    - Tracking failure rates
    - Opening circuit when failure threshold is reached
    - Allowing periodic test requests during recovery
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Union[Exception, Tuple[Exception, ...]] = Exception,
        timeout: float = 30.0
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.timeout = timeout
        
        self._state = CircuitBreakerState.CLOSED
        self._stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()
        
        logger.info(f"CircuitBreaker '{name}' initialized with threshold={failure_threshold}, timeout={recovery_timeout}s")
    
    @property
    def state(self) -> CircuitBreakerState:
        return self._state
    
    @property
    def stats(self) -> CircuitBreakerStats:
        return self._stats
    
    async def __call__(self, func: Callable) -> Any:
        """Execute function with circuit breaker protection"""
        async with self._lock:
            # Check if circuit is open
            if self._state == CircuitBreakerState.OPEN:
                if time.time() - self._stats.last_failure_time < self.recovery_timeout:
                    logger.warning(f"CircuitBreaker '{self.name}' is OPEN - failing fast")
                    raise CircuitBreakerError(f"Circuit breaker '{self.name}' is open")
                else:
                    # Try to recover
                    self._state = CircuitBreakerState.HALF_OPEN
                    self._stats.state_changes += 1
                    logger.info(f"CircuitBreaker '{self.name}' entering HALF_OPEN state for recovery test")
        
        # Execute the function
        self._stats.total_requests += 1
        
        try:
            # Apply timeout
            result = await asyncio.wait_for(func(), timeout=self.timeout)
            await self._on_success()
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"CircuitBreaker '{self.name}' - operation timed out after {self.timeout}s")
            await self._on_failure()
            raise
            
        except self.expected_exception as e:
            logger.error(f"CircuitBreaker '{self.name}' - expected exception: {e}")
            await self._on_failure()
            raise
            
        except Exception as e:
            logger.error(f"CircuitBreaker '{self.name}' - unexpected exception: {e}")
            await self._on_failure()
            raise
    
    async def _on_success(self):
        """Handle successful execution"""
        async with self._lock:
            self._stats.successful_requests += 1
            self._stats.consecutive_failures = 0
            
            if self._state == CircuitBreakerState.HALF_OPEN:
                self._state = CircuitBreakerState.CLOSED
                self._stats.state_changes += 1
                logger.info(f"CircuitBreaker '{self.name}' recovered - state: CLOSED")
    
    async def _on_failure(self):
        """Handle failed execution"""
        async with self._lock:
            self._stats.failed_requests += 1
            self._stats.consecutive_failures += 1
            self._stats.last_failure_time = time.time()
            
            if self._stats.consecutive_failures >= self.failure_threshold:
                if self._state != CircuitBreakerState.OPEN:
                    self._state = CircuitBreakerState.OPEN
                    self._stats.state_changes += 1
                    logger.error(f"CircuitBreaker '{self.name}' OPENED after {self._stats.consecutive_failures} failures")
    
    def reset_circuit_breaker(self):
        """Reset circuit breaker to closed state (for testing/recovery)"""
        self._state = CircuitBreakerState.CLOSED
        self._stats.consecutive_failures = 0
        self._stats.last_failure_time = None
        logger.info(f"CircuitBreaker '{self.name}' manually reset to CLOSED state")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get circuit breaker health status"""
        success_rate = (
            self._stats.successful_requests / self._stats.total_requests 
            if self._stats.total_requests > 0 else 0.0
        )
        
        return {
            "name": self.name,
            "state": self._state.value,
            "stats": {
                "total_requests": self._stats.total_requests,
                "successful_requests": self._stats.successful_requests,
                "failed_requests": self._stats.failed_requests,
                "consecutive_failures": self._stats.consecutive_failures,
                "success_rate": success_rate,
                "state_changes": self._stats.state_changes
            },
            "config": {
                "failure_threshold": self.failure_threshold,
                "recovery_timeout": self.recovery_timeout,
                "timeout": self.timeout
            }
        }


class RetryManager:
    """
    Retry manager with exponential backoff and jitter
    
    Implements intelligent retry patterns:
    - Exponential backoff with jitter
    - Configurable retry policies
    - Context-aware error handling
    """
    
    def __init__(self, config: RetryConfig):
        self.config = config
        logger.info(f"RetryManager initialized with max_attempts={config.max_attempts}, base_delay={config.base_delay}s")
    
    async def execute_with_retry(
        self,
        func: Callable,
        operation_name: str,
        retryable_exceptions: Tuple[Exception, ...] = (Exception,),
        non_retryable_exceptions: Tuple[Exception, ...] = ()
    ) -> Any:
        """Execute function with retry logic"""
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                logger.debug(f"RetryManager - {operation_name}: attempt {attempt}/{self.config.max_attempts}")
                result = await func()
                
                if attempt > 1:
                    logger.info(f"RetryManager - {operation_name}: succeeded on attempt {attempt}")
                
                return result
                
            except non_retryable_exceptions as e:
                logger.error(f"RetryManager - {operation_name}: non-retryable exception: {e}")
                raise
                
            except retryable_exceptions as e:
                last_exception = e
                logger.warning(f"RetryManager - {operation_name}: attempt {attempt} failed: {e}")
                
                if attempt == self.config.max_attempts:
                    logger.error(f"RetryManager - {operation_name}: max attempts reached")
                    break
                
                # Calculate delay with exponential backoff and jitter
                delay = self._calculate_delay(attempt)
                logger.debug(f"RetryManager - {operation_name}: waiting {delay:.2f}s before retry")
                await asyncio.sleep(delay)
        
        # All attempts failed
        raise MaxRetriesExceededError(
            f"Operation '{operation_name}' failed after {self.config.max_attempts} attempts. "
            f"Last exception: {last_exception}"
        )
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter"""
        # Base exponential backoff
        delay = self.config.base_delay * (self.config.exponential_base ** (attempt - 1))
        
        # Apply maximum delay cap
        delay = min(delay, self.config.max_delay)
        
        # Add jitter if enabled
        if self.config.jitter:
            jitter_amount = delay * self.config.jitter_range
            jitter = random.uniform(-jitter_amount, jitter_amount)
            delay += jitter
        
        return max(0.1, delay)  # Minimum 100ms delay


class ErrorHandlingManager:
    """
    Centralized error handling manager for analytics operations
    
    Coordinates circuit breakers and retry mechanisms
    """
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_managers: Dict[str, RetryManager] = {}
        self._lock = asyncio.Lock()
        
        # Default configurations
        self._setup_default_configurations()
        
        logger.info("ErrorHandlingManager initialized with default configurations")
    
    def _setup_default_configurations(self):
        """Setup default circuit breakers and retry managers"""
        # Database operations
        self.add_circuit_breaker(
            "database",
            failure_threshold=3,
            recovery_timeout=30.0,
            timeout=15.0
        )
        
        self.add_retry_manager(
            "database",
            RetryConfig(max_attempts=3, base_delay=0.5, max_delay=5.0)
        )
        
        # External data sources
        self.add_circuit_breaker(
            "external_data",
            failure_threshold=5,
            recovery_timeout=60.0,
            timeout=30.0
        )
        
        self.add_retry_manager(
            "external_data",
            RetryConfig(max_attempts=5, base_delay=1.0, max_delay=30.0)
        )
        
        # Market data APIs
        self.add_circuit_breaker(
            "market_data_api",
            failure_threshold=3,
            recovery_timeout=45.0,
            timeout=20.0
        )
        
        self.add_retry_manager(
            "market_data_api",
            RetryConfig(max_attempts=4, base_delay=2.0, max_delay=20.0, jitter=True)
        )
    
    def add_circuit_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Union[Exception, Tuple[Exception, ...]] = Exception,
        timeout: float = 30.0
    ):
        """Add a circuit breaker for a specific operation type"""
        self.circuit_breakers[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
            timeout=timeout
        )
    
    def add_retry_manager(self, name: str, config: RetryConfig):
        """Add a retry manager for a specific operation type"""
        self.retry_managers[name] = RetryManager(config)
    
    @asynccontextmanager
    async def protected_operation(
        self,
        operation_name: str,
        circuit_breaker_name: str = "default",
        retry_manager_name: str = "default",
        retryable_exceptions: Tuple[Exception, ...] = (Exception,),
        non_retryable_exceptions: Tuple[Exception, ...] = ()
    ):
        """
        Context manager for protected operations with circuit breaker and retry
        
        Usage:
            async with error_manager.protected_operation("database_query", "database", "database"):
                result = await some_database_operation()
        """
        circuit_breaker = self.circuit_breakers.get(circuit_breaker_name)
        retry_manager = self.retry_managers.get(retry_manager_name)
        
        if not circuit_breaker:
            logger.warning(f"Circuit breaker '{circuit_breaker_name}' not found, creating default")
            self.add_circuit_breaker(circuit_breaker_name)
            circuit_breaker = self.circuit_breakers[circuit_breaker_name]
        
        if not retry_manager:
            logger.warning(f"Retry manager '{retry_manager_name}' not found, creating default")
            self.add_retry_manager(retry_manager_name, RetryConfig())
            retry_manager = self.retry_managers[retry_manager_name]
        
        class ProtectedOperation:
            def __init__(self, cb, rm):
                self.circuit_breaker = cb
                self.retry_manager = rm
            
            async def execute(self, func: Callable) -> Any:
                """Execute function with both circuit breaker and retry protection"""
                return await self.retry_manager.execute_with_retry(
                    lambda: self.circuit_breaker(func),
                    operation_name,
                    retryable_exceptions,
                    non_retryable_exceptions
                )
        
        yield ProtectedOperation(circuit_breaker, retry_manager)
    
    def reset_all_circuit_breakers(self):
        """Reset all circuit breakers to closed state (for testing/recovery)"""
        for name, cb in self.circuit_breakers.items():
            cb.reset_circuit_breaker()
        logger.info("All circuit breakers reset to CLOSED state")
    
    def reset_circuit_breaker(self, name: str):
        """Reset specific circuit breaker to closed state"""
        if name in self.circuit_breakers:
            self.circuit_breakers[name].reset_circuit_breaker()
        else:
            logger.warning(f"Circuit breaker '{name}' not found for reset")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all circuit breakers and retry managers"""
        return {
            "circuit_breakers": {
                name: cb.get_health_status()
                for name, cb in self.circuit_breakers.items()
            },
            "retry_managers": {
                name: {
                    "name": name,
                    "config": {
                        "max_attempts": rm.config.max_attempts,
                        "base_delay": rm.config.base_delay,
                        "max_delay": rm.config.max_delay,
                        "exponential_base": rm.config.exponential_base,
                        "jitter": rm.config.jitter
                    }
                }
                for name, rm in self.retry_managers.items()
            }
        }


# Global error handling manager instance
error_handling_manager = ErrorHandlingManager()


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    timeout: float = 30.0
):
    """Decorator for adding circuit breaker protection to functions"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            cb = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                timeout=timeout
            )
            return await cb(lambda: func(*args, **kwargs))
        return wrapper
    return decorator


def retry_on_failure(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_exceptions: Tuple[Exception, ...] = (Exception,)
):
    """Decorator for adding retry logic to functions"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            retry_manager = RetryManager(
                RetryConfig(
                    max_attempts=max_attempts,
                    base_delay=base_delay,
                    max_delay=max_delay
                )
            )
            return await retry_manager.execute_with_retry(
                lambda: func(*args, **kwargs),
                func.__name__,
                retryable_exceptions
            )
        return wrapper
    return decorator