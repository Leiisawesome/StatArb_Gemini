"""
Production Safety Framework
==========================

Critical production safety system that prevents dangerous fallback behavior
and ensures system integrity in live trading environments.

Features:
- Environment-aware error handling (development vs production)
- Mandatory real data validation in production
- Circuit breakers for fallback scenarios
- Execution result integrity validation
- Silent failure prevention

Author: StatArb_Gemini Production Safety Team
Version: 1.0.0
"""

import logging
import os
from enum import Enum
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
import threading

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for production safety validation failures"""
    pass


class Environment(Enum):
    """System environment types"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class SafetyLevel(Enum):
    """Production safety levels"""
    STRICT = "strict"        # No fallbacks allowed
    CAUTIOUS = "cautious"    # Limited fallbacks with explicit approval
    DEVELOPMENT = "development"  # Fallbacks allowed for development


class FailureMode(Enum):
    """Types of system failures that need safety handling"""
    MARKET_DATA_UNAVAILABLE = "market_data_unavailable"
    EXECUTION_FAILURE = "execution_failure"
    PRICE_DATA_MISSING = "price_data_missing"
    CONNECTIVITY_LOST = "connectivity_lost"
    VALIDATION_BYPASS = "validation_bypass"
    SYNTHETIC_RESULT = "synthetic_result"


@dataclass
class SafetyViolation:
    """Production safety violation record"""
    violation_id: str
    failure_mode: FailureMode
    component: str
    message: str
    timestamp: datetime
    environment: Environment
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    fallback_attempted: bool = False
    fallback_blocked: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProductionSafetyConfig:
    """Configuration for production safety framework"""
    environment: Environment = Environment.DEVELOPMENT
    safety_level: SafetyLevel = SafetyLevel.DEVELOPMENT
    
    # Execution safety
    allow_synthetic_execution_results: bool = True  # False in production
    require_real_market_data: bool = False  # True in production
    validate_execution_integrity: bool = False  # True in production
    
    # Market data safety
    allow_fallback_prices: bool = True  # False in production
    require_live_data_feeds: bool = False  # True in production
    max_data_staleness_seconds: int = 300  # 5 minutes max in production
    
    # Validation safety
    allow_validation_bypass: bool = True  # False in production
    enforce_risk_limits: bool = False  # True in production
    require_execution_confirmation: bool = False  # True in production
    
    # Circuit breaker settings
    max_violations_per_hour: int = 100
    circuit_breaker_timeout_minutes: int = 15
    
    # Monitoring
    enable_safety_alerts: bool = True
    log_all_violations: bool = True


class ProductionSafetyError(Exception):
    """Critical production safety violation"""
    
    def __init__(self, message: str, failure_mode: FailureMode, component: str = "unknown"):
        self.failure_mode = failure_mode
        self.component = component
        self.timestamp = datetime.now()
        super().__init__(f"[PRODUCTION SAFETY] {component}: {message}")


class ProductionSafetyFramework:
    """
    Central production safety framework that prevents dangerous fallback behavior
    """
    
    _instance: Optional['ProductionSafetyFramework'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'ProductionSafetyFramework':
        """Singleton pattern for global safety framework"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        self.config = self._load_config()
        self.violations: List[SafetyViolation] = []
        self.circuit_breakers: Dict[str, datetime] = {}
        self.violation_counts: Dict[str, int] = {}
        self._start_time = datetime.now()
        
        # Initialize based on environment
        self._setup_environment_safety()
        
        logger.info(f"🛡️ Production Safety Framework initialized")
        logger.info(f"   Environment: {self.config.environment.value}")
        logger.info(f"   Safety Level: {self.config.safety_level.value}")
        logger.info(f"   Real Market Data Required: {self.config.require_real_market_data}")
        logger.info(f"   Synthetic Execution Results Allowed: {self.config.allow_synthetic_execution_results}")
    
    def _load_config(self) -> ProductionSafetyConfig:
        """Load production safety configuration"""
        # Check environment variables
        env_name = os.getenv('TRADING_ENVIRONMENT', 'development').lower()
        
        try:
            environment = Environment(env_name)
        except ValueError:
            logger.warning(f"Unknown environment '{env_name}', defaulting to development")
            environment = Environment.DEVELOPMENT
        
        # Create environment-specific config
        if environment == Environment.PRODUCTION:
            return ProductionSafetyConfig(
                environment=environment,
                safety_level=SafetyLevel.STRICT,
                allow_synthetic_execution_results=False,
                require_real_market_data=True,
                validate_execution_integrity=True,
                allow_fallback_prices=False,
                require_live_data_feeds=True,
                max_data_staleness_seconds=60,  # 1 minute max in production
                allow_validation_bypass=False,
                enforce_risk_limits=True,
                require_execution_confirmation=True
            )
        elif environment == Environment.STAGING:
            return ProductionSafetyConfig(
                environment=environment,
                safety_level=SafetyLevel.CAUTIOUS,
                allow_synthetic_execution_results=False,
                require_real_market_data=True,
                validate_execution_integrity=True,
                allow_fallback_prices=False,
                require_live_data_feeds=True,
                max_data_staleness_seconds=120,  # 2 minutes max in staging
                allow_validation_bypass=False,
                enforce_risk_limits=True,
                require_execution_confirmation=True
            )
        else:
            # Development/Testing - more permissive
            return ProductionSafetyConfig(
                environment=environment,
                safety_level=SafetyLevel.DEVELOPMENT
            )
    
    def _setup_environment_safety(self):
        """Setup environment-specific safety measures"""
        if self.config.environment == Environment.PRODUCTION:
            logger.info("🚨 PRODUCTION MODE: Maximum safety measures active")
            logger.info("   - No fallback behavior allowed")
            logger.info("   - Real market data mandatory")
            logger.info("   - Execution integrity validation enabled")
            logger.info("   - All validation bypasses blocked")
        
        elif self.config.environment == Environment.STAGING:
            logger.info("⚠️ STAGING MODE: Cautious safety measures active")
            logger.info("   - Limited fallback behavior")
            logger.info("   - Real market data preferred")
            logger.info("   - Execution validation enabled")
        
        else:
            logger.info("🔧 DEVELOPMENT MODE: Development safety measures active")
            logger.info("   - Fallback behavior allowed for development")
            logger.info("   - Synthetic data permitted")
    
    def validate_market_data_usage(self, 
                                  component: str,
                                  has_real_data: bool,
                                  data_timestamp: Optional[datetime] = None,
                                  symbol: str = "unknown") -> bool:
        """
        Validate market data usage meets production safety requirements
        
        Args:
            component: Component requesting validation
            has_real_data: Whether real market data is available
            data_timestamp: Timestamp of the data (for staleness check)
            symbol: Symbol being processed
            
        Returns:
            True if usage is safe, False if blocked
            
        Raises:
            ProductionSafetyError: In production if real data unavailable
        """
        # Check real data requirement
        if self.config.require_real_market_data and not has_real_data:
            violation = SafetyViolation(
                violation_id=f"market_data_{datetime.now().isoformat()}",
                failure_mode=FailureMode.MARKET_DATA_UNAVAILABLE,
                component=component,
                message=f"Real market data required in {self.config.environment.value} but not available for {symbol}",
                timestamp=datetime.now(),
                environment=self.config.environment,
                severity="CRITICAL",
                fallback_attempted=True,
                fallback_blocked=True,
                metadata={"symbol": symbol, "has_real_data": has_real_data}
            )
            
            self._record_violation(violation)
            
            raise ProductionSafetyError(
                f"Real market data required in {self.config.environment.value} environment but not available for {symbol}",
                FailureMode.MARKET_DATA_UNAVAILABLE,
                component
            )
        
        # Check data staleness
        if data_timestamp and self.config.max_data_staleness_seconds > 0:
            staleness = (datetime.now() - data_timestamp).total_seconds()
            if staleness > self.config.max_data_staleness_seconds:
                violation = SafetyViolation(
                    violation_id=f"stale_data_{datetime.now().isoformat()}",
                    failure_mode=FailureMode.MARKET_DATA_UNAVAILABLE,
                    component=component,
                    message=f"Market data too stale: {staleness:.0f}s > {self.config.max_data_staleness_seconds}s for {symbol}",
                    timestamp=datetime.now(),
                    environment=self.config.environment,
                    severity="HIGH",
                    metadata={"symbol": symbol, "staleness_seconds": staleness}
                )
                
                self._record_violation(violation)
                
                if self.config.safety_level == SafetyLevel.STRICT:
                    raise ProductionSafetyError(
                        f"Market data too stale ({staleness:.0f}s) for {symbol} in {self.config.environment.value}",
                        FailureMode.MARKET_DATA_UNAVAILABLE,
                        component
                    )
        
        return True
    
    def validate_execution_result(self,
                                component: str,
                                execution_result: Any,
                                is_synthetic: bool = False) -> bool:
        """
        Validate execution result integrity
        
        Args:
            component: Component providing the result
            execution_result: The execution result object
            is_synthetic: Whether this is a synthetic/simulated result
            
        Returns:
            True if result is valid, False if blocked
            
        Raises:
            ProductionSafetyError: If synthetic results not allowed in production
        """
        # Check synthetic result policy
        if is_synthetic and not self.config.allow_synthetic_execution_results:
            violation = SafetyViolation(
                violation_id=f"synthetic_execution_{datetime.now().isoformat()}",
                failure_mode=FailureMode.SYNTHETIC_RESULT,
                component=component,
                message=f"Synthetic execution results not allowed in {self.config.environment.value}",
                timestamp=datetime.now(),
                environment=self.config.environment,
                severity="CRITICAL",
                fallback_attempted=True,
                fallback_blocked=True
            )
            
            self._record_violation(violation)
            
            raise ProductionSafetyError(
                f"Synthetic execution results not allowed in {self.config.environment.value} environment",
                FailureMode.SYNTHETIC_RESULT,
                component
            )
        
        # Additional integrity checks for production
        if self.config.validate_execution_integrity:
            # Check for impossible scenarios
            if hasattr(execution_result, 'executed_quantity') and hasattr(execution_result, 'requested_quantity'):
                if execution_result.executed_quantity > execution_result.requested_quantity * 1.01:  # Allow 1% tolerance
                    violation = SafetyViolation(
                        violation_id=f"impossible_execution_{datetime.now().isoformat()}",
                        failure_mode=FailureMode.EXECUTION_FAILURE,
                        component=component,
                        message=f"Impossible execution: executed ({execution_result.executed_quantity}) > requested ({execution_result.requested_quantity})",
                        timestamp=datetime.now(),
                        environment=self.config.environment,
                        severity="HIGH"
                    )
                    
                    self._record_violation(violation)
                    
                    if self.config.safety_level == SafetyLevel.STRICT:
                        raise ProductionSafetyError(
                            f"Impossible execution quantity detected",
                            FailureMode.EXECUTION_FAILURE,
                            component
                        )
        
        return True
    
    def check_validation_bypass(self, component: str, bypass_reason: str) -> bool:
        """
        Check if validation bypass is allowed
        
        Args:
            component: Component requesting bypass
            bypass_reason: Reason for bypass request
            
        Returns:
            True if bypass allowed, False if blocked
            
        Raises:
            ProductionSafetyError: If bypass not allowed in production
        """
        if not self.config.allow_validation_bypass:
            violation = SafetyViolation(
                violation_id=f"validation_bypass_{datetime.now().isoformat()}",
                failure_mode=FailureMode.VALIDATION_BYPASS,
                component=component,
                message=f"Validation bypass not allowed in {self.config.environment.value}: {bypass_reason}",
                timestamp=datetime.now(),
                environment=self.config.environment,
                severity="CRITICAL",
                fallback_attempted=True,
                fallback_blocked=True,
                metadata={"bypass_reason": bypass_reason}
            )
            
            self._record_violation(violation)
            
            raise ProductionSafetyError(
                f"Validation bypass not allowed in {self.config.environment.value}: {bypass_reason}",
                FailureMode.VALIDATION_BYPASS,
                component
            )
        
        # Log bypass in development mode
        logger.warning(f"🔧 DEVELOPMENT: Validation bypass allowed - {component}: {bypass_reason}")
        return True
    
    def _record_violation(self, violation: SafetyViolation):
        """Record a safety violation"""
        self.violations.append(violation)
        
        # Update violation counts for circuit breaker
        hour_key = f"{violation.component}_{datetime.now().hour}"
        self.violation_counts[hour_key] = self.violation_counts.get(hour_key, 0) + 1
        
        # Check circuit breaker
        if self.violation_counts[hour_key] >= self.config.max_violations_per_hour:
            self.circuit_breakers[violation.component] = datetime.now() + timedelta(
                minutes=self.config.circuit_breaker_timeout_minutes
            )
            logger.error(f"🚨 CIRCUIT BREAKER ACTIVATED: {violation.component} "
                        f"({self.violation_counts[hour_key]} violations/hour)")
        
        # Log violation
        if self.config.log_all_violations:
            log_level = logging.ERROR if violation.severity in ["CRITICAL", "HIGH"] else logging.WARNING
            logger.log(log_level, 
                      f"🛡️ SAFETY VIOLATION [{violation.severity}]: {violation.component} - {violation.message}")
        
        # Alert if configured
        if self.config.enable_safety_alerts and violation.severity == "CRITICAL":
            self._send_safety_alert(violation)
    
    def _send_safety_alert(self, violation: SafetyViolation):
        """Send safety alert for critical violations"""
        # In a real system, this would integrate with alerting systems
        logger.critical(f"🚨 CRITICAL SAFETY ALERT: {violation.component} - {violation.message}")
    
    def get_safety_status(self) -> Dict[str, Any]:
        """Get current safety framework status"""
        return {
            "environment": self.config.environment.value,
            "safety_level": self.config.safety_level.value,
            "total_violations": len(self.violations),
            "critical_violations": len([v for v in self.violations if v.severity == "CRITICAL"]),
            "active_circuit_breakers": len([cb for cb in self.circuit_breakers.values() if cb > datetime.now()]),
            "uptime_hours": (datetime.now() - self._start_time).total_seconds() / 3600,
            "last_violation": self.violations[-1].timestamp if self.violations else None
        }
    
    def get_current_environment(self) -> Environment:
        """Get the current trading environment"""
        return self.config.environment
    
    def get_safety_level(self) -> SafetyLevel:
        """Get the current safety level"""
        return self.config.safety_level
    
    def get_violations(self) -> List[Dict[str, Any]]:
        """Get list of safety violations"""
        return [
            {
                'violation_id': v.violation_id,
                'failure_mode': v.failure_mode.value,
                'component': v.component,
                'message': v.message,
                'timestamp': v.timestamp.isoformat(),
                'environment': v.environment.value,
                'severity': v.severity,
                'fallback_attempted': v.fallback_attempted,
                'fallback_blocked': v.fallback_blocked
            }
            for v in self.violations
        ]
    
    def record_violation(self, violation_type: str, message: str, critical: bool = False):
        """Record a safety violation"""
        failure_mode = FailureMode.VALIDATION_BYPASS  # Default
        if 'market_data' in violation_type.lower():
            failure_mode = FailureMode.MARKET_DATA_UNAVAILABLE
        elif 'execution' in violation_type.lower():
            failure_mode = FailureMode.EXECUTION_FAILURE
        elif 'price' in violation_type.lower():
            failure_mode = FailureMode.PRICE_DATA_MISSING
        elif 'connectivity' in violation_type.lower():
            failure_mode = FailureMode.CONNECTIVITY_LOST
        elif 'synthetic' in violation_type.lower():
            failure_mode = FailureMode.SYNTHETIC_RESULT
        
        violation = SafetyViolation(
            violation_id=f"{violation_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            failure_mode=failure_mode,
            component=violation_type,
            message=message,
            timestamp=datetime.now(),
            environment=self.config.environment,
            severity="CRITICAL" if critical else "HIGH"
        )
        
        self._record_violation(violation)
    
    def validate_operation(self, operation_name: str, critical: bool = False):
        """Validate if operation is allowed given current safety status"""
        # Check circuit breaker
        if len(self.violations) > 5:
            raise ValidationError(f"Circuit breaker active: Too many violations ({len(self.violations)})")
        
        # Check for critical violations in production
        if self.config.environment == Environment.PRODUCTION and critical:
            critical_violations = [v for v in self.violations if v.severity == "CRITICAL"]
            if len(critical_violations) > 0:
                raise ValidationError(f"Critical violations present, operation {operation_name} blocked")
        
        return True


# Global safety framework instance
safety_framework = ProductionSafetyFramework()


def production_safe(failure_mode: FailureMode):
    """
    Decorator to mark functions as production-safe and validate their behavior
    
    Usage:
        @production_safe(FailureMode.MARKET_DATA_UNAVAILABLE)
        def get_market_price(symbol: str) -> float:
            # Function implementation
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            component = f"{func.__module__}.{func.__name__}"
            
            # Check circuit breaker
            if component in safety_framework.circuit_breakers:
                if safety_framework.circuit_breakers[component] > datetime.now():
                    raise ProductionSafetyError(
                        f"Circuit breaker active for {component}",
                        failure_mode,
                        component
                    )
                else:
                    # Remove expired circuit breaker
                    del safety_framework.circuit_breakers[component]
            
            try:
                return func(*args, **kwargs)
            except ProductionSafetyError:
                # Re-raise production safety errors
                raise
            except Exception as e:
                # Log unexpected errors in production-safe functions
                violation = SafetyViolation(
                    violation_id=f"unexpected_error_{datetime.now().isoformat()}",
                    failure_mode=failure_mode,
                    component=component,
                    message=f"Unexpected error in production-safe function: {str(e)}",
                    timestamp=datetime.now(),
                    environment=safety_framework.config.environment,
                    severity="HIGH"
                )
                safety_framework._record_violation(violation)
                raise
        
        return wrapper
    return decorator


def require_real_data(func: Callable) -> Callable:
    """
    Decorator to require real market data in production environments
    
    Usage:
        @require_real_data
        def process_market_data(data, is_real=True):
            # Function will validate is_real=True in production
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        component = f"{func.__module__}.{func.__name__}"
        
        # Check if function has is_real or similar parameter
        is_real = kwargs.get('is_real', kwargs.get('has_real_data', True))
        
        safety_framework.validate_market_data_usage(
            component=component,
            has_real_data=bool(is_real)
        )
        
        return func(*args, **kwargs)
    
    return wrapper


def block_in_production(func: Callable) -> Callable:
    """
    Decorator to block function execution in production environment
    
    Usage:
        @block_in_production
        def use_synthetic_data():
            # This function will be blocked in production
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if safety_framework.config.environment == Environment.PRODUCTION:
            component = f"{func.__module__}.{func.__name__}"
            raise ProductionSafetyError(
                f"Function {func.__name__} is blocked in production environment",
                FailureMode.VALIDATION_BYPASS,
                component
            )
        
        return func(*args, **kwargs)
    
    return wrapper
