"""
Mock services for integration testing.

This module provides mock implementations of core system services for integration testing.
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import logging
import random
import time

logger = logging.getLogger(__name__)


@dataclass
class MockSignal:
    """Mock trading signal."""
    signal_id: str
    symbol: str
    timestamp: datetime
    signal_type: str  # 'BUY' or 'SELL'
    confidence: float
    strength: float
    source: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class MockOrder:
    """Mock trading order."""
    order_id: str
    symbol: str
    side: str  # 'BUY' or 'SELL'
    quantity: int
    order_type: str  # 'MARKET' or 'LIMIT'
    price: Optional[float] = None
    timestamp: Optional[datetime] = None
    signal_id: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class MockExecution:
    """Mock order execution."""
    execution_id: str
    order_id: str
    symbol: str
    side: str
    quantity: int
    price: float
    timestamp: datetime
    status: str  # 'FILLED', 'PARTIAL', 'REJECTED'
    fill_rate: float
    implementation_shortfall: float
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class MockPosition:
    """Mock portfolio position."""
    symbol: str
    quantity: int
    avg_price: float
    current_price: float
    current_value: float
    unrealized_pnl: float
    timestamp: datetime
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class MockRiskMetrics:
    """Mock risk metrics."""
    timestamp: datetime
    portfolio_var: float
    position_var: Dict[str, float]
    total_exposure: float
    leverage_ratio: float
    concentration_risk: float
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class MockSignalGenerator:
    """Mock signal generator for integration testing."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.signals_generated = 0
        self.last_signal_time = datetime.now()
        self.signal_history = []
        
        # Performance tracking
        self.performance_stats = {
            'total_signals': 0,
            'avg_generation_time_ms': 0,
            'success_rate': 1.0,
            'last_updated': datetime.now()
        }
    
    async def generate_signals(self, symbols: List[str], count: int = 1) -> List[MockSignal]:
        """Generate mock trading signals."""
        start_time = time.time()
        
        try:
            signals = []
            for i in range(count):
                signal = await self._generate_single_signal(symbols)
                signals.append(signal)
                self.signals_generated += 1
                self.signal_history.append(signal)
            
            # Update performance stats
            generation_time = (time.time() - start_time) * 1000  # Convert to ms
            self._update_performance_stats(generation_time, len(signals))
            
            logger.info(f"Generated {len(signals)} signals in {generation_time:.2f}ms")
            return signals
            
        except Exception as e:
            logger.error(f"Error generating signals: {e}")
            self.performance_stats['success_rate'] = 0.0
            raise
    
    async def _generate_single_signal(self, symbols: List[str]) -> MockSignal:
        """Generate a single mock signal."""
        await asyncio.sleep(0.001)  # Simulate processing time
        
        signal = MockSignal(
            signal_id=f"signal_{self.signals_generated:06d}",
            symbol=random.choice(symbols),
            timestamp=datetime.now(),
            signal_type=random.choice(['BUY', 'SELL']),
            confidence=random.uniform(0.5, 1.0),
            strength=random.uniform(0.1, 0.5),
            source="mock_signal_generator",
            metadata={
                'test_signal': True,
                'batch_id': f"batch_{self.signals_generated // 10:03d}"
            }
        )
        
        return signal
    
    def _update_performance_stats(self, generation_time: float, signal_count: int):
        """Update performance statistics."""
        self.performance_stats['total_signals'] += signal_count
        
        # Update average generation time
        total_signals = self.performance_stats['total_signals']
        current_avg = self.performance_stats['avg_generation_time_ms']
        new_avg = ((current_avg * (total_signals - signal_count)) + generation_time) / total_signals
        self.performance_stats['avg_generation_time_ms'] = new_avg
        
        self.performance_stats['last_updated'] = datetime.now()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return self.performance_stats.copy()
    
    def clear_history(self):
        """Clear signal history."""
        self.signal_history.clear()
        self.signals_generated = 0


class MockExecutionEngine:
    """Mock execution engine for integration testing."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.orders_processed = 0
        self.executions = []
        self.order_history = []
        
        # Performance tracking
        self.performance_stats = {
            'total_orders': 0,
            'avg_execution_time_ms': 0,
            'success_rate': 1.0,
            'avg_fill_rate': 0.95,
            'avg_implementation_shortfall': 0.0005,
            'last_updated': datetime.now()
        }
    
    async def execute_order(self, order: MockOrder) -> MockExecution:
        """Execute a mock order."""
        start_time = time.time()
        
        try:
            await asyncio.sleep(0.001)  # Simulate processing time
            
            # Simulate execution with realistic characteristics
            execution = await self._simulate_execution(order)
            
            self.executions.append(execution)
            self.order_history.append(order)
            self.orders_processed += 1
            
            # Update performance stats
            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            self._update_performance_stats(execution_time, execution)
            
            logger.info(f"Executed order {order.order_id} in {execution_time:.2f}ms")
            return execution
            
        except Exception as e:
            logger.error(f"Error executing order: {e}")
            self.performance_stats['success_rate'] = 0.0
            raise
    
    async def _simulate_execution(self, order: MockOrder) -> MockExecution:
        """Simulate order execution with realistic characteristics."""
        # Simulate market impact and price movement
        base_price = 100.0
        if order.price:
            base_price = order.price
        
        # Add some market impact based on order size
        market_impact = (order.quantity / 10000) * 0.001  # 1bp per 10k shares
        
        if order.side == 'BUY':
            execution_price = base_price * (1 + market_impact)
        else:
            execution_price = base_price * (1 - market_impact)
        
        # Add some noise to execution price
        execution_price += random.normalvariate(0, 0.01)
        
        # Simulate fill rate (usually high for market orders)
        fill_rate = random.uniform(0.95, 1.0) if order.order_type == 'MARKET' else random.uniform(0.8, 1.0)
        
        # Calculate implementation shortfall
        implementation_shortfall = abs(execution_price - base_price) / base_price
        
        execution = MockExecution(
            execution_id=f"exec_{order.order_id}",
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=int(order.quantity * fill_rate),
            price=execution_price,
            timestamp=datetime.now(),
            status='FILLED' if fill_rate > 0.95 else 'PARTIAL',
            fill_rate=fill_rate,
            implementation_shortfall=implementation_shortfall,
            metadata={
                'test_execution': True,
                'order_type': order.order_type,
                'signal_id': order.signal_id
            }
        )
        
        return execution
    
    def _update_performance_stats(self, execution_time: float, execution: MockExecution):
        """Update performance statistics."""
        self.performance_stats['total_orders'] += 1
        
        # Update average execution time
        total_orders = self.performance_stats['total_orders']
        current_avg = self.performance_stats['avg_execution_time_ms']
        new_avg = ((current_avg * (total_orders - 1)) + execution_time) / total_orders
        self.performance_stats['avg_execution_time_ms'] = new_avg
        
        # Update average fill rate
        current_fill_avg = self.performance_stats['avg_fill_rate']
        new_fill_avg = ((current_fill_avg * (total_orders - 1)) + execution.fill_rate) / total_orders
        self.performance_stats['avg_fill_rate'] = new_fill_avg
        
        # Update average implementation shortfall
        current_shortfall_avg = self.performance_stats['avg_implementation_shortfall']
        new_shortfall_avg = ((current_shortfall_avg * (total_orders - 1)) + execution.implementation_shortfall) / total_orders
        self.performance_stats['avg_implementation_shortfall'] = new_shortfall_avg
        
        self.performance_stats['last_updated'] = datetime.now()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return self.performance_stats.copy()
    
    def clear_history(self):
        """Clear execution history."""
        self.executions.clear()
        self.order_history.clear()
        self.orders_processed = 0


class MockRiskManager:
    """Mock risk manager for integration testing."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.risk_checks_performed = 0
        self.risk_history = []
        
        # Risk limits
        self.risk_limits = {
            'max_position_size': 10000,
            'max_portfolio_var': 0.02,  # 2%
            'max_leverage': 2.0,
            'max_concentration': 0.2,  # 20%
            'max_daily_loss': 0.05  # 5%
        }
        
        # Performance tracking
        self.performance_stats = {
            'total_checks': 0,
            'avg_check_time_ms': 0,
            'success_rate': 1.0,
            'risk_violations': 0,
            'last_updated': datetime.now()
        }
    
    async def validate_signal(self, signal: MockSignal, portfolio_state: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a trading signal against risk limits."""
        start_time = time.time()
        
        try:
            await asyncio.sleep(0.001)  # Simulate processing time
            
            validation_result = await self._perform_risk_validation(signal, portfolio_state)
            
            self.risk_checks_performed += 1
            self.risk_history.append(validation_result)
            
            # Update performance stats
            check_time = (time.time() - start_time) * 1000  # Convert to ms
            self._update_performance_stats(check_time, validation_result)
            
            logger.info(f"Risk validation completed in {check_time:.2f}ms")
            return validation_result
            
        except Exception as e:
            logger.error(f"Error in risk validation: {e}")
            self.performance_stats['success_rate'] = 0.0
            raise
    
    async def _perform_risk_validation(self, signal: MockSignal, portfolio_state: Dict[str, Any]) -> Dict[str, Any]:
        """Perform risk validation checks."""
        # Calculate position size
        position_size = portfolio_state.get('positions', {}).get(signal.symbol, {}).get('quantity', 0)
        
        # Calculate portfolio VaR (simplified)
        portfolio_value = portfolio_state.get('total_value', 1000000)
        portfolio_var = random.uniform(0.01, 0.03)  # 1-3%
        
        # Calculate leverage
        total_exposure = sum(pos.get('current_value', 0) for pos in portfolio_state.get('positions', {}).values())
        leverage = total_exposure / portfolio_value if portfolio_value > 0 else 0
        
        # Calculate concentration
        max_position_value = max((pos.get('current_value', 0) for pos in portfolio_state.get('positions', {}).values()), default=0)
        concentration = max_position_value / portfolio_value if portfolio_value > 0 else 0
        
        # Check risk limits
        violations = []
        
        if position_size > self.risk_limits['max_position_size']:
            violations.append('position_size_limit')
        
        if portfolio_var > self.risk_limits['max_portfolio_var']:
            violations.append('portfolio_var_limit')
        
        if leverage > self.risk_limits['max_leverage']:
            violations.append('leverage_limit')
        
        if concentration > self.risk_limits['max_concentration']:
            violations.append('concentration_limit')
        
        validation_result = {
            'signal_id': signal.signal_id,
            'timestamp': datetime.now(),
            'approved': len(violations) == 0,
            'violations': violations,
            'risk_metrics': {
                'position_size': position_size,
                'portfolio_var': portfolio_var,
                'leverage': leverage,
                'concentration': concentration
            },
            'metadata': {
                'test_validation': True,
                'risk_manager': 'mock'
            }
        }
        
        return validation_result
    
    def _update_performance_stats(self, check_time: float, validation_result: Dict[str, Any]):
        """Update performance statistics."""
        self.performance_stats['total_checks'] += 1
        
        # Update average check time
        total_checks = self.performance_stats['total_checks']
        current_avg = self.performance_stats['avg_check_time_ms']
        new_avg = ((current_avg * (total_checks - 1)) + check_time) / total_checks
        self.performance_stats['avg_check_time_ms'] = new_avg
        
        # Update violation count
        if not validation_result['approved']:
            self.performance_stats['risk_violations'] += 1
        
        self.performance_stats['last_updated'] = datetime.now()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return self.performance_stats.copy()
    
    def clear_history(self):
        """Clear risk history."""
        self.risk_history.clear()
        self.risk_checks_performed = 0


class MockPortfolioManager:
    """Mock portfolio manager for integration testing."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.positions = {}
        self.transactions = []
        self.portfolio_history = []
        
        # Initialize with some default positions
        self._initialize_default_positions()
        
        # Performance tracking
        self.performance_stats = {
            'total_updates': 0,
            'avg_update_time_ms': 0,
            'success_rate': 1.0,
            'last_updated': datetime.now()
        }
    
    def _initialize_default_positions(self):
        """Initialize with default portfolio positions."""
        default_positions = {
            'AAPL': {'quantity': 1000, 'avg_price': 150.0, 'current_price': 155.0},
            'GOOGL': {'quantity': 500, 'avg_price': 2800.0, 'current_price': 2850.0},
            'MSFT': {'quantity': 800, 'avg_price': 300.0, 'current_price': 310.0}
        }
        
        for symbol, pos_data in default_positions.items():
            self.positions[symbol] = MockPosition(
                symbol=symbol,
                quantity=pos_data['quantity'],
                avg_price=pos_data['avg_price'],
                current_price=pos_data['current_price'],
                current_value=pos_data['quantity'] * pos_data['current_price'],
                unrealized_pnl=pos_data['quantity'] * (pos_data['current_price'] - pos_data['avg_price']),
                timestamp=datetime.now(),
                metadata={'default_position': True}
            )
    
    async def update_position(self, execution: MockExecution) -> Dict[str, Any]:
        """Update portfolio position based on execution."""
        start_time = time.time()
        
        try:
            await asyncio.sleep(0.001)  # Simulate processing time
            
            update_result = await self._process_execution(execution)
            
            self.transactions.append(execution)
            self.portfolio_history.append(update_result)
            
            # Update performance stats
            update_time = (time.time() - start_time) * 1000  # Convert to ms
            self._update_performance_stats(update_time)
            
            logger.info(f"Portfolio updated in {update_time:.2f}ms")
            return update_result
            
        except Exception as e:
            logger.error(f"Error updating portfolio: {e}")
            self.performance_stats['success_rate'] = 0.0
            raise
    
    async def _process_execution(self, execution: MockExecution) -> Dict[str, Any]:
        """Process execution and update portfolio."""
        symbol = execution.symbol
        
        if symbol not in self.positions:
            # Create new position
            self.positions[symbol] = MockPosition(
                symbol=symbol,
                quantity=execution.quantity,
                avg_price=execution.price,
                current_price=execution.price,
                current_value=execution.quantity * execution.price,
                unrealized_pnl=0.0,
                timestamp=execution.timestamp,
                metadata={'new_position': True}
            )
        else:
            # Update existing position
            position = self.positions[symbol]
            
            if execution.side == 'BUY':
                # Add to position
                total_quantity = position.quantity + execution.quantity
                total_cost = (position.quantity * position.avg_price) + (execution.quantity * execution.price)
                new_avg_price = total_cost / total_quantity
                
                position.quantity = total_quantity
                position.avg_price = new_avg_price
                position.current_value = total_quantity * position.current_price
                position.unrealized_pnl = total_quantity * (position.current_price - new_avg_price)
            else:
                # Reduce position
                position.quantity -= execution.quantity
                if position.quantity <= 0:
                    # Position closed
                    del self.positions[symbol]
                else:
                    position.current_value = position.quantity * position.current_price
                    position.unrealized_pnl = position.quantity * (position.current_price - position.avg_price)
            
            position.timestamp = execution.timestamp
        
        # Calculate portfolio summary
        total_value = sum(pos.current_value for pos in self.positions.values())
        total_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        
        update_result = {
            'execution_id': execution.execution_id,
            'timestamp': execution.timestamp,
            'portfolio_summary': {
                'total_value': total_value,
                'total_pnl': total_pnl,
                'position_count': len(self.positions)
            },
            'updated_positions': {symbol: pos.__dict__ for symbol, pos in self.positions.items()},
            'metadata': {
                'test_update': True,
                'portfolio_manager': 'mock'
            }
        }
        
        return update_result
    
    def get_portfolio_snapshot(self) -> Dict[str, Any]:
        """Get current portfolio snapshot."""
        total_value = sum(pos.current_value for pos in self.positions.values())
        total_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        
        return {
            'timestamp': datetime.now(),
            'total_value': total_value,
            'total_pnl': total_pnl,
            'position_count': len(self.positions),
            'positions': {symbol: pos.__dict__ for symbol, pos in self.positions.items()},
            'metadata': {
                'test_snapshot': True,
                'portfolio_manager': 'mock'
            }
        }
    
    def _update_performance_stats(self, update_time: float):
        """Update performance statistics."""
        self.performance_stats['total_updates'] += 1
        
        # Update average update time
        total_updates = self.performance_stats['total_updates']
        current_avg = self.performance_stats['avg_update_time_ms']
        new_avg = ((current_avg * (total_updates - 1)) + update_time) / total_updates
        self.performance_stats['avg_update_time_ms'] = new_avg
        
        self.performance_stats['last_updated'] = datetime.now()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return self.performance_stats.copy()
    
    def clear_history(self):
        """Clear portfolio history."""
        self.transactions.clear()
        self.portfolio_history.clear()
        self._initialize_default_positions() 