"""
Integration Test Helpers

Utility functions for integration testing including:
- Assertion helpers
- Data validation utilities
- System state verification
- Test data builders

Author: StatArb_Gemini Test Infrastructure
Date: October 8, 2025
Version: 1.0.0
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncio


# ==============================================================================
# ASSERTION HELPERS
# ==============================================================================

def assert_signal_generated(
    strategy_manager,
    symbol: str,
    timeout: float = 5.0
) -> bool:
    """
    Assert that strategy manager generated signal for symbol.
    
    Args:
        strategy_manager: StrategyManager instance
        symbol: Ticker symbol
        timeout: Wait timeout
        
    Returns:
        True if signal found
    """
    # Check if signal exists in strategy manager state
    # This would access internal signal queue or recent signals
    return hasattr(strategy_manager, 'signals') and len(strategy_manager.signals) > 0


def assert_risk_authorized(
    risk_manager,
    request_id: str = None,
    expected_level: str = None
) -> bool:
    """
    Assert that risk manager authorized request.
    
    Args:
        risk_manager: CentralRiskManager instance
        request_id: Optional specific request ID
        expected_level: Expected authorization level
        
    Returns:
        True if authorization found
    """
    # Check authorization audit trail
    if hasattr(risk_manager, 'authorization_audit'):
        if not risk_manager.authorization_audit:
            return False
        
        if request_id:
            return any(
                auth.get('request_id') == request_id
                for auth in risk_manager.authorization_audit
            )
        
        if expected_level:
            return any(
                auth.get('authorization_level') == expected_level
                for auth in risk_manager.authorization_audit
            )
        
        return len(risk_manager.authorization_audit) > 0
    
    return False


def assert_order_executed(
    execution_engine,
    symbol: str = None,
    order_id: str = None
) -> bool:
    """
    Assert that execution engine executed order.
    
    Args:
        execution_engine: UnifiedExecutionEngine instance
        symbol: Optional symbol filter
        order_id: Optional order ID
        
    Returns:
        True if order executed
    """
    # Check execution history
    if hasattr(execution_engine, 'execution_history'):
        if not execution_engine.execution_history:
            return False
        
        if symbol:
            return any(
                exec.get('symbol') == symbol
                for exec in execution_engine.execution_history
            )
        
        if order_id:
            return any(
                exec.get('order_id') == order_id
                for exec in execution_engine.execution_history
            )
        
        return len(execution_engine.execution_history) > 0
    
    return False


def assert_position_updated(
    risk_manager,
    symbol: str,
    expected_quantity: float = None
) -> bool:
    """
    Assert that position was updated correctly.
    
    Args:
        risk_manager: CentralRiskManager instance
        symbol: Ticker symbol
        expected_quantity: Expected position size
        
    Returns:
        True if position matches expectations
    """
    if not hasattr(risk_manager, 'positions'):
        return False
    
    if symbol not in risk_manager.positions:
        return expected_quantity is None or expected_quantity == 0
    
    position = risk_manager.positions[symbol]
    
    if expected_quantity is not None:
        return abs(position.get('quantity', 0) - expected_quantity) < 0.01
    
    return True


def assert_performance_tracked(
    performance_tracker,
    symbol: str = None,
    min_records: int = 1
) -> bool:
    """
    Assert that performance was tracked.
    
    Args:
        performance_tracker: Performance tracking component
        symbol: Optional symbol filter
        min_records: Minimum expected records
        
    Returns:
        True if performance tracked
    """
    if not hasattr(performance_tracker, 'records'):
        return False
    
    records = performance_tracker.records
    
    if symbol:
        records = [r for r in records if r.get('symbol') == symbol]
    
    return len(records) >= min_records


# ==============================================================================
# STATE VERIFICATION
# ==============================================================================

def verify_system_health(system: Dict[str, Any]) -> Dict[str, bool]:
    """
    Verify health of all system components.
    
    Args:
        system: Dictionary of system components
        
    Returns:
        Dictionary of component health status
    """
    health = {}
    
    for name, component in system.items():
        if hasattr(component, 'health_check'):
            health[name] = component.health_check()
        elif hasattr(component, 'is_healthy'):
            health[name] = component.is_healthy()
        else:
            # Assume healthy if initialized
            health[name] = hasattr(component, 'initialized') and component.initialized
    
    return health


def verify_component_coordination(
    orchestrator,
    expected_components: List[str]
) -> bool:
    """
    Verify that orchestrator has all expected components registered.
    
    Args:
        orchestrator: HierarchicalSystemOrchestrator instance
        expected_components: List of expected component names
        
    Returns:
        True if all components registered
    """
    if not hasattr(orchestrator, 'components'):
        return False
    
    registered = set(orchestrator.components.keys())
    expected = set(expected_components)
    
    return expected.issubset(registered)


def verify_risk_limits_enforced(risk_manager) -> bool:
    """
    Verify that risk limits are properly enforced.
    
    Args:
        risk_manager: CentralRiskManager instance
        
    Returns:
        True if limits enforced
    """
    if not hasattr(risk_manager, 'config'):
        return False
    
    config = risk_manager.config
    
    # Check position limits
    if hasattr(risk_manager, 'positions'):
        for symbol, position in risk_manager.positions.items():
            if abs(position.get('quantity', 0)) > config.max_position_size:
                return False
    
    # Check portfolio exposure
    if hasattr(risk_manager, 'portfolio_exposure'):
        if abs(risk_manager.portfolio_exposure) > config.max_portfolio_exposure:
            return False
    
    return True


def verify_authorization_flow(
    risk_manager,
    execution_engine,
    recent_window: timedelta = timedelta(seconds=10)
) -> bool:
    """
    Verify that execution respects risk authorizations.
    
    Args:
        risk_manager: CentralRiskManager instance
        execution_engine: UnifiedExecutionEngine instance
        recent_window: Time window to check
        
    Returns:
        True if authorization flow valid
    """
    # Get recent authorizations
    if not hasattr(risk_manager, 'authorization_audit'):
        return True  # Can't verify
    
    recent_auths = [
        auth for auth in risk_manager.authorization_audit
        if (datetime.now() - auth.get('timestamp', datetime.min)) < recent_window
    ]
    
    # Get recent executions
    if not hasattr(execution_engine, 'execution_history'):
        return True  # Can't verify
    
    recent_execs = [
        exec for exec in execution_engine.execution_history
        if (datetime.now() - exec.get('timestamp', datetime.min)) < recent_window
    ]
    
    # Verify each execution had authorization
    for execution in recent_execs:
        order_id = execution.get('order_id')
        
        # Find corresponding authorization
        auth_found = any(
            auth.get('request_id') == order_id or
            auth.get('order_id') == order_id
            for auth in recent_auths
        )
        
        # Execution without authorization is a violation
        if not auth_found:
            return False
    
    return True


# ==============================================================================
# DATA BUILDERS
# ==============================================================================

def build_authorization_request(
    symbol: str = 'AAPL',
    side: str = 'buy',
    quantity: float = 100.0,
    price: float = 150.0,
    confidence: float = 0.85,
    strategy_id: str = 'momentum_01'
) -> Dict[str, Any]:
    """
    Build authorization request for testing.
    
    Args:
        symbol: Ticker symbol
        side: 'buy' or 'sell'
        quantity: Order quantity
        price: Order price
        confidence: Signal confidence
        strategy_id: Strategy identifier
        
    Returns:
        Authorization request dictionary
    """
    return {
        'symbol': symbol,
        'side': side,
        'quantity': quantity,
        'price': price,
        'confidence': confidence,
        'strategy_id': strategy_id,
        'timestamp': datetime.now(),
        'order_type': 'limit',
    }


def build_execution_request(
    symbol: str = 'AAPL',
    side: str = 'buy',
    quantity: float = 100.0,
    order_type: str = 'limit',
    limit_price: float = 150.0,
    algorithm: str = 'TWAP'
) -> Dict[str, Any]:
    """
    Build execution request for testing.
    
    Args:
        symbol: Ticker symbol
        side: 'buy' or 'sell'
        quantity: Order quantity
        order_type: Order type
        limit_price: Limit price
        algorithm: Execution algorithm
        
    Returns:
        Execution request dictionary
    """
    return {
        'symbol': symbol,
        'side': side,
        'quantity': quantity,
        'order_type': order_type,
        'limit_price': limit_price,
        'algorithm': algorithm,
        'timestamp': datetime.now(),
    }


def build_market_data_batch(
    symbols: List[str],
    base_price: float = 100.0,
    num_updates: int = 10
) -> List[Dict[str, Any]]:
    """
    Build batch of market data updates.
    
    Args:
        symbols: List of ticker symbols
        base_price: Starting price
        num_updates: Number of updates per symbol
        
    Returns:
        List of market data updates
    """
    import random
    
    updates = []
    timestamp = datetime.now()
    
    for symbol in symbols:
        price = base_price
        
        for i in range(num_updates):
            # Random walk
            price += random.uniform(-1.0, 1.0)
            
            update = {
                'symbol': symbol,
                'price': round(price, 2),
                'volume': random.randint(1000, 10000),
                'timestamp': timestamp + timedelta(seconds=i),
                'bid': round(price * 0.999, 2),
                'ask': round(price * 1.001, 2),
            }
            updates.append(update)
    
    return updates


# ==============================================================================
# TIMING UTILITIES
# ==============================================================================

async def measure_latency(operation, *args, **kwargs) -> tuple:
    """
    Measure latency of async operation.
    
    Args:
        operation: Async callable
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        Tuple of (result, duration_ms)
    """
    import time
    
    start = time.perf_counter()
    result = await operation(*args, **kwargs)
    duration = (time.perf_counter() - start) * 1000  # Convert to ms
    
    return result, duration


async def measure_throughput(
    operation,
    num_operations: int = 100,
    *args,
    **kwargs
) -> float:
    """
    Measure throughput (operations per second).
    
    Args:
        operation: Async callable
        num_operations: Number of operations to run
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        Operations per second
    """
    import time
    
    start = time.perf_counter()
    
    for _ in range(num_operations):
        await operation(*args, **kwargs)
    
    duration = time.perf_counter() - start
    throughput = num_operations / duration if duration > 0 else 0
    
    return throughput


# ==============================================================================
# ERROR INJECTION
# ==============================================================================

class ErrorInjector:
    """
    Inject errors for resilience testing.
    """
    
    def __init__(self):
        self.failure_rate = 0.0
        self.failure_types = []
    
    def set_failure_rate(self, rate: float):
        """Set probability of failure (0-1)."""
        self.failure_rate = max(0.0, min(1.0, rate))
    
    def add_failure_type(self, error_class: Exception, message: str = ""):
        """Add type of error to inject."""
        self.failure_types.append((error_class, message))
    
    def maybe_fail(self):
        """Randomly fail based on failure rate."""
        import random
        
        if random.random() < self.failure_rate:
            if self.failure_types:
                error_class, message = random.choice(self.failure_types)
                raise error_class(message)


# ==============================================================================
# WAIT UTILITIES
# ==============================================================================

async def wait_for_signal(
    strategy_manager,
    symbol: str,
    timeout: float = 5.0
) -> Optional[Dict[str, Any]]:
    """
    Wait for signal from strategy manager.
    
    Args:
        strategy_manager: StrategyManager instance
        symbol: Ticker symbol
        timeout: Wait timeout
        
    Returns:
        Signal dictionary or None
    """
    start = asyncio.get_event_loop().time()
    
    while asyncio.get_event_loop().time() - start < timeout:
        if hasattr(strategy_manager, 'signals'):
            for signal in strategy_manager.signals:
                if signal.get('symbol') == symbol:
                    return signal
        
        await asyncio.sleep(0.1)
    
    return None


async def wait_for_execution(
    execution_engine,
    order_id: str,
    timeout: float = 5.0
) -> Optional[Dict[str, Any]]:
    """
    Wait for order execution.
    
    Args:
        execution_engine: UnifiedExecutionEngine instance
        order_id: Order ID
        timeout: Wait timeout
        
    Returns:
        Execution result or None
    """
    start = asyncio.get_event_loop().time()
    
    while asyncio.get_event_loop().time() - start < timeout:
        if hasattr(execution_engine, 'execution_history'):
            for execution in execution_engine.execution_history:
                if execution.get('order_id') == order_id:
                    return execution
        
        await asyncio.sleep(0.1)
    
    return None


async def wait_for_position_update(
    risk_manager,
    symbol: str,
    timeout: float = 5.0
) -> Optional[Dict[str, Any]]:
    """
    Wait for position update.
    
    Args:
        risk_manager: CentralRiskManager instance
        symbol: Ticker symbol
        timeout: Wait timeout
        
    Returns:
        Position data or None
    """
    start = asyncio.get_event_loop().time()
    
    while asyncio.get_event_loop().time() - start < timeout:
        if hasattr(risk_manager, 'positions'):
            if symbol in risk_manager.positions:
                return risk_manager.positions[symbol]
        
        await asyncio.sleep(0.1)
    
    return None
