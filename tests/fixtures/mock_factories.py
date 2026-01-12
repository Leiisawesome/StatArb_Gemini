"""
Mock Factories - Test Object Creation
=====================================

Factories for creating mock objects and test doubles for all core components.
"""

import asyncio
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any, Optional, List
from datetime import datetime

from core_engine.data.manager import ClickHouseDataManager
from core_engine.regime.engine import EnhancedRegimeEngine
from core_engine.trading.portfolio.manager_enhanced import EnhancedPortfolioManager

# ========================================
# DATA MANAGER MOCKS
# ========================================

def create_mock_data_manager(
    symbols: Optional[List[str]] = None,
    has_data: bool = True
) -> Mock:
    """Create mock data manager"""
    mock = Mock(spec=ClickHouseDataManager)

    if symbols is None:
        symbols = ['AAPL', 'GOOGL', 'MSFT']

    mock.is_initialized = True
    mock.available_symbols = symbols

    # Mock methods
    if has_data:
        mock.load_market_data = AsyncMock(return_value={
            symbol: Mock(shape=(100, 6)) for symbol in symbols
        })
        mock.get_latest_price = AsyncMock(return_value=100.0)
    else:
        mock.load_market_data = AsyncMock(return_value={})
        mock.get_latest_price = AsyncMock(return_value=None)

    mock.query_data = AsyncMock(return_value=[])
    mock.is_market_open = Mock(return_value=True)

    return mock

# ========================================
# REGIME ENGINE MOCKS
# ========================================

def create_mock_regime_engine(
    current_regime: str = 'normal_volatility',
    confidence: float = 0.8
) -> Mock:
    """Create mock regime engine"""
    mock = Mock(spec=EnhancedRegimeEngine)

    mock.is_initialized = True
    mock.current_regime = current_regime

    # Mock methods
    mock.get_current_regime = AsyncMock(return_value={
        'primary_regime': current_regime,
        'confidence': confidence,
        'market_volatility': 0.15,
        'trend_direction': 'bullish'
    })

    mock.analyze_regime = AsyncMock(return_value={
        'regime': current_regime,
        'confidence': confidence,
        'stability': 0.85
    })

    mock.predict_regime_transition = AsyncMock(return_value={
        'predicted_regime': current_regime,
        'transition_probability': 0.1,
        'time_horizon': 30
    })

    return mock

# ========================================
# PORTFOLIO MANAGER MOCKS
# ========================================

def create_mock_portfolio_manager(
    initial_capital: float = 1000000.0,
    current_positions: Optional[Dict[str, Any]] = None
) -> Mock:
    """Create mock portfolio manager"""
    mock = Mock(spec=EnhancedPortfolioManager)

    mock.is_initialized = True
    mock.total_capital = initial_capital
    mock.available_capital = initial_capital * 0.7
    mock.positions = current_positions or {}

    # Mock methods
    mock.get_position = Mock(side_effect=lambda symbol: current_positions.get(symbol) if current_positions else None)
    mock.update_position = AsyncMock(return_value=True)
    mock.close_position = AsyncMock(return_value=True)

    mock.get_portfolio_value = Mock(return_value=initial_capital)
    mock.get_available_capital = Mock(return_value=initial_capital * 0.7)
    mock.get_portfolio_metrics = Mock(return_value={
        'total_value': initial_capital,
        'unrealized_pnl': 5000.0,
        'realized_pnl': 10000.0,
        'position_count': len(current_positions) if current_positions else 0
    })

    return mock

# ========================================
# STRATEGY MOCKS
# ========================================

def create_mock_strategy(
    strategy_id: str = 'test_strategy',
    strategy_type: str = 'momentum',
    is_active: bool = True,
    generates_signals: bool = True
) -> Mock:
    """Create mock strategy"""
    from core_engine.trading.strategies.base_strategy_enhanced import EnhancedBaseStrategy

    mock = Mock(spec=EnhancedBaseStrategy)

    mock.strategy_id = strategy_id
    mock.strategy_type = strategy_type
    mock.is_active = is_active
    mock.is_initialized = True

    # Mock methods
    if generates_signals:
        from core_engine.trading.strategies.contracts import StrategySignal
        from core_engine.type_definitions.strategy import SignalType
        mock.generate_signals = AsyncMock(return_value=[
            StrategySignal(
                signal_id=f'{strategy_id}_signal_1',
                strategy_id=strategy_id,
                symbol='AAPL',
                signal_type=SignalType.BUY,
                confidence=0.8,
                strength=0.7,
                target_quantity=100.0
            )
        ])
    else:
        mock.generate_signals = AsyncMock(return_value=[])

    mock.initialize = AsyncMock(return_value=True)
    mock.start = AsyncMock(return_value=True)
    mock.stop = AsyncMock(return_value=True)
    mock.update = AsyncMock(return_value=True)

    return mock

# ========================================
# EXECUTION ALGORITHM MOCKS
# ========================================

def create_mock_execution_algorithm(
    algorithm_name: str = 'TWAP',
    execution_time: float = 300.0,
    market_impact: float = 0.001
) -> Mock:
    """Create mock execution algorithm"""
    from core_engine.system.unified_execution_engine import IExecutionAlgorithm, ExecutionResult, ExecutionStatus

    mock = Mock(spec=IExecutionAlgorithm)

    # Mock methods
    mock.execute = AsyncMock(return_value=ExecutionResult(
        request_id='test_request',
        status=ExecutionStatus.FILLED,
        filled_quantity=100.0,
        avg_fill_price=100.0,
        total_cost=10000.0,
        market_impact=market_impact,
        execution_time=execution_time
    ))

    mock.estimate_execution_time = Mock(return_value=execution_time)
    mock.estimate_market_impact = Mock(return_value=market_impact)

    return mock

# ========================================
# BROKER ADAPTER MOCKS
# ========================================

def create_mock_broker_adapter(
    is_connected: bool = True,
    execution_delay: float = 0.1
) -> Mock:
    """Create mock broker adapter"""
    mock = Mock()

    mock.is_connected = is_connected
    mock.execution_delay = execution_delay

    # Mock methods
    mock.connect = AsyncMock(return_value=True)
    mock.disconnect = AsyncMock(return_value=True)

    mock.submit_order = AsyncMock(return_value={
        'order_id': 'test_order_123',
        'status': 'submitted',
        'timestamp': datetime.now()
    })

    mock.execute_order = AsyncMock(return_value={
        'filled': True,
        'fill_price': 100.0,
        'fill_quantity': 100.0,  # Mock fill quantity
        'venue': 'MOCK'
    })

    mock.cancel_order = AsyncMock(return_value=True)

    mock.get_order_status = AsyncMock(return_value={
        'order_id': 'test_order_123',
        'status': 'filled',
        'filled_quantity': 100.0,
        'avg_fill_price': 100.0
    })

    mock.get_positions = AsyncMock(return_value={})
    mock.get_account_info = AsyncMock(return_value={
        'buying_power': 500000.0,
        'equity': 1000000.0
    })

    return mock

# ========================================
# MONITORING MOCKS
# ========================================

def create_mock_monitor() -> Mock:
    """Create mock system monitor"""
    mock = Mock()

    mock.is_running = True

    # Mock methods
    mock.start_monitoring = AsyncMock(return_value=True)
    mock.stop_monitoring = AsyncMock(return_value=True)

    mock.record_metric = Mock()
    mock.record_event = Mock()

    mock.get_metrics = Mock(return_value={
        'cpu_usage': 25.0,
        'memory_usage': 45.0,
        'active_threads': 8,
        'event_count': 100
    })

    return mock

# ========================================
# AUDIT TRAIL MOCKS
# ========================================

def create_mock_audit_trail() -> Mock:
    """Create mock audit trail manager"""
    mock = Mock()

    mock.is_initialized = True
    mock.audit_log = []

    # Mock methods
    mock.log_event = Mock()
    mock.log_authorization = Mock()
    mock.log_trade = Mock()
    mock.log_risk_event = Mock()

    mock.get_audit_trail = Mock(return_value=[])
    mock.search_events = Mock(return_value=[])

    return mock

# ========================================
# UTILITY FUNCTIONS
# ========================================

def create_mock_with_methods(spec_class, method_returns: Dict[str, Any]) -> Mock:
    """
    Create a mock with specified return values for methods

    Args:
        spec_class: Class to use as spec
        method_returns: Dict mapping method names to return values
    """
    mock = Mock(spec=spec_class)

    for method_name, return_value in method_returns.items():
        if asyncio.iscoroutinefunction(getattr(spec_class, method_name, None)):
            setattr(mock, method_name, AsyncMock(return_value=return_value))
        else:
            setattr(mock, method_name, Mock(return_value=return_value))

    return mock

def reset_all_mocks(*mocks) -> None:
    """Reset all provided mocks"""
    for mock in mocks:
        if hasattr(mock, 'reset_mock'):
            mock.reset_mock()
