"""
Optimized Interface Communication System
========================================

High-performance interface layer for trade_engine + core_structure architecture
with zero-copy data transfer, async processing, and intelligent caching.

Author: Pro Quant Desk Trader
"""

import asyncio
import mmap
import struct
import pickle
import logging
import time
from typing import Dict, List, Optional, Any, Union, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty
from threading import RLock
import weakref
import uuid

logger = logging.getLogger(__name__)

T = TypeVar('T')

@dataclass
class InterfaceMessage:
    """High-performance message for interface communication"""
    message_id: str
    source_component: str
    target_component: str
    message_type: str
    payload: Any
    timestamp: float
    priority: int = 0  # Higher number = higher priority

@dataclass
class InterfaceMetrics:
    """Performance metrics for interface communication"""
    total_messages: int = 0
    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')
    error_count: int = 0
    throughput_msgs_per_sec: float = 0.0

class SharedMemoryBuffer:
    """High-performance shared memory buffer for zero-copy data transfer"""
    
    def __init__(self, buffer_size: int = 1024 * 1024):  # 1MB default
        self.buffer_size = buffer_size
        self.buffer = mmap.mmap(-1, buffer_size)
        self.write_pos = 0
        self.read_pos = 0
        self.lock = RLock()
        
    def write_data(self, data: bytes) -> bool:
        """Write data to shared buffer with zero copy"""
        data_size = len(data)
        
        with self.lock:
            # Check if we have enough space
            available_space = self.buffer_size - self.write_pos
            if data_size + 4 > available_space:  # +4 for size header
                # Reset buffer if we're near the end
                if self.read_pos > self.buffer_size // 2:
                    self._compact_buffer()
                else:
                    return False  # Buffer full
            
            # Write size header + data
            self.buffer.seek(self.write_pos)
            self.buffer.write(struct.pack('I', data_size))
            self.buffer.write(data)
            self.write_pos += 4 + data_size
            
            return True
    
    def read_data(self) -> Optional[bytes]:
        """Read data from shared buffer with zero copy"""
        with self.lock:
            if self.read_pos >= self.write_pos:
                return None  # No data available
            
            # Read size header
            self.buffer.seek(self.read_pos)
            size_bytes = self.buffer.read(4)
            if len(size_bytes) < 4:
                return None
            
            data_size = struct.unpack('I', size_bytes)[0]
            
            # Read data
            data = self.buffer.read(data_size)
            self.read_pos += 4 + data_size
            
            return data
    
    def _compact_buffer(self):
        """Compact buffer by moving unread data to beginning"""
        unread_size = self.write_pos - self.read_pos
        if unread_size > 0:
            self.buffer.move(0, self.read_pos, unread_size)
        
        self.write_pos = unread_size
        self.read_pos = 0

class FastMessageQueue(Generic[T]):
    """High-performance message queue with priority support"""
    
    def __init__(self, maxsize: int = 10000):
        self.queue = Queue(maxsize=maxsize)
        self.priority_queue = Queue(maxsize=maxsize // 10)  # For high-priority messages
        self.metrics = InterfaceMetrics()
        self._start_time = time.time()
    
    async def put_async(self, item: T, priority: int = 0) -> bool:
        """Put item in queue asynchronously"""
        try:
            if priority > 5:  # High priority threshold
                self.priority_queue.put_nowait(item)
            else:
                self.queue.put_nowait(item)
            
            self.metrics.total_messages += 1
            return True
        except:
            return False
    
    async def get_async(self, timeout: float = 0.1) -> Optional[T]:
        """Get item from queue asynchronously with priority handling"""
        start_time = time.time()
        
        try:
            # Check priority queue first
            try:
                item = self.priority_queue.get_nowait()
                self._update_latency_metrics(start_time)
                return item
            except Empty:
                pass
            
            # Check regular queue
            try:
                item = self.queue.get_nowait()
                self._update_latency_metrics(start_time)
                return item
            except Empty:
                return None
                
        except Exception as e:
            self.metrics.error_count += 1
            logger.error(f"Error getting item from queue: {e}")
            return None
    
    def _update_latency_metrics(self, start_time: float):
        """Update latency metrics"""
        latency_ms = (time.time() - start_time) * 1000
        
        if self.metrics.min_latency_ms == float('inf'):
            self.metrics.min_latency_ms = latency_ms
        else:
            self.metrics.min_latency_ms = min(self.metrics.min_latency_ms, latency_ms)
        
        self.metrics.max_latency_ms = max(self.metrics.max_latency_ms, latency_ms)
        
        # Simple moving average for avg_latency_ms
        if self.metrics.avg_latency_ms == 0:
            self.metrics.avg_latency_ms = latency_ms
        else:
            self.metrics.avg_latency_ms = (self.metrics.avg_latency_ms * 0.9) + (latency_ms * 0.1)
        
        # Calculate throughput
        elapsed_time = time.time() - self._start_time
        if elapsed_time > 0:
            self.metrics.throughput_msgs_per_sec = self.metrics.total_messages / elapsed_time

class OptimizedInterface(ABC):
    """Base class for optimized interfaces"""
    
    def __init__(self, interface_name: str):
        self.interface_name = interface_name
        self.message_queue = FastMessageQueue[InterfaceMessage]()
        self.shared_buffer = SharedMemoryBuffer()
        self.request_handlers: Dict[str, Callable] = {}
        self.is_active = False
        
    @abstractmethod
    async def process_message(self, message: InterfaceMessage) -> Any:
        """Process incoming message"""
        pass
    
    async def send_message(
        self, 
        target_component: str, 
        message_type: str, 
        payload: Any, 
        priority: int = 0
    ) -> str:
        """Send message to target component"""
        message_id = str(uuid.uuid4())
        message = InterfaceMessage(
            message_id=message_id,
            source_component=self.interface_name,
            target_component=target_component,
            message_type=message_type,
            payload=payload,
            timestamp=time.time(),
            priority=priority
        )
        
        success = await self.message_queue.put_async(message, priority)
        if not success:
            logger.error(f"Failed to send message {message_id}")
        
        return message_id
    
    async def start_processing(self):
        """Start message processing loop"""
        self.is_active = True
        while self.is_active:
            message = await self.message_queue.get_async()
            if message:
                try:
                    await self.process_message(message)
                except Exception as e:
                    logger.error(f"Error processing message {message.message_id}: {e}")
            else:
                await asyncio.sleep(0.001)  # Short sleep to prevent busy waiting
    
    def stop_processing(self):
        """Stop message processing"""
        self.is_active = False

class StrategyInterface(OptimizedInterface):
    """Optimized interface for strategy communication"""
    
    def __init__(self):
        super().__init__("strategy_interface")
        self.strategy_cache: Dict[str, Any] = {}
        self.signal_cache: Dict[str, List[Any]] = {}
        
    async def process_message(self, message: InterfaceMessage) -> Any:
        """Process strategy-related messages"""
        if message.message_type == "generate_signals":
            return await self._generate_signals_optimized(message.payload)
        elif message.message_type == "update_parameters":
            return await self._update_parameters_optimized(message.payload)
        elif message.message_type == "get_strategy_state":
            return await self._get_strategy_state_optimized(message.payload)
        else:
            logger.warning(f"Unknown message type: {message.message_type}")
            return None
    
    async def _generate_signals_optimized(self, market_data: Any) -> List[Any]:
        """Generate signals with caching and optimization"""
        # Check cache first
        cache_key = self._generate_cache_key(market_data)
        if cache_key in self.signal_cache:
            logger.debug("Signal cache hit")
            return self.signal_cache[cache_key]
        
        # Generate new signals (implement strategy logic here)
        signals = []  # Placeholder for actual signal generation
        
        # Cache the result
        self.signal_cache[cache_key] = signals
        if len(self.signal_cache) > 1000:  # Limit cache size
            oldest_key = next(iter(self.signal_cache))
            del self.signal_cache[oldest_key]
        
        return signals
    
    async def _update_parameters_optimized(self, parameters: Dict[str, Any]) -> bool:
        """Update strategy parameters with validation"""
        try:
            # Validate parameters
            for key, value in parameters.items():
                if not self._validate_parameter(key, value):
                    logger.error(f"Invalid parameter: {key}={value}")
                    return False
            
            # Update parameters
            self.strategy_cache.update(parameters)
            
            # Clear signal cache since parameters changed
            self.signal_cache.clear()
            
            return True
        except Exception as e:
            logger.error(f"Error updating parameters: {e}")
            return False
    
    async def _get_strategy_state_optimized(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Get current strategy state"""
        return {
            'parameters': self.strategy_cache.copy(),
            'signal_cache_size': len(self.signal_cache),
            'interface_metrics': self.message_queue.metrics
        }
    
    def _generate_cache_key(self, market_data: Any) -> str:
        """Generate cache key for market data"""
        # Simple hash-based cache key (implement proper hashing)
        return str(hash(str(market_data)))
    
    def _validate_parameter(self, key: str, value: Any) -> bool:
        """Validate strategy parameter"""
        # Implement parameter validation logic
        return True

class ExecutionInterface(OptimizedInterface):
    """Optimized interface for execution communication"""
    
    def __init__(self):
        super().__init__("execution_interface")
        self.order_cache: Dict[str, Any] = {}
        self.execution_pool = ThreadPoolExecutor(max_workers=4)
        
    async def process_message(self, message: InterfaceMessage) -> Any:
        """Process execution-related messages"""
        if message.message_type == "execute_order":
            return await self._execute_order_optimized(message.payload)
        elif message.message_type == "cancel_order":
            return await self._cancel_order_optimized(message.payload)
        elif message.message_type == "get_order_status":
            return await self._get_order_status_optimized(message.payload)
        else:
            logger.warning(f"Unknown message type: {message.message_type}")
            return None
    
    async def _execute_order_optimized(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute order with optimization"""
        order_id = order_data.get('order_id', str(uuid.uuid4()))
        
        # Cache the order
        self.order_cache[order_id] = {
            'status': 'pending',
            'order_data': order_data,
            'timestamp': time.time()
        }
        
        # Execute in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self.execution_pool, 
            self._execute_order_sync, 
            order_data
        )
        
        # Update cache
        self.order_cache[order_id].update(result)
        
        return result
    
    def _execute_order_sync(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous order execution (placeholder)"""
        # Implement actual order execution logic
        return {
            'status': 'filled',
            'fill_price': order_data.get('price', 0),
            'fill_quantity': order_data.get('quantity', 0),
            'execution_time': time.time()
        }
    
    async def _cancel_order_optimized(self, order_id: str) -> bool:
        """Cancel order with optimization"""
        if order_id in self.order_cache:
            self.order_cache[order_id]['status'] = 'cancelled'
            return True
        return False
    
    async def _get_order_status_optimized(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order status from cache"""
        return self.order_cache.get(order_id)

class PortfolioInterface(OptimizedInterface):
    """Optimized interface for portfolio communication"""
    
    def __init__(self):
        super().__init__("portfolio_interface")
        self.position_cache: Dict[str, Any] = {}
        self.portfolio_metrics_cache: Dict[str, Any] = {}
        self.last_update_time = 0
        
    async def process_message(self, message: InterfaceMessage) -> Any:
        """Process portfolio-related messages"""
        if message.message_type == "update_position":
            return await self._update_position_optimized(message.payload)
        elif message.message_type == "get_positions":
            return await self._get_positions_optimized(message.payload)
        elif message.message_type == "calculate_metrics":
            return await self._calculate_metrics_optimized(message.payload)
        else:
            logger.warning(f"Unknown message type: {message.message_type}")
            return None
    
    async def _update_position_optimized(self, position_data: Dict[str, Any]) -> bool:
        """Update position with caching"""
        try:
            symbol = position_data['symbol']
            self.position_cache[symbol] = position_data
            self.last_update_time = time.time()
            
            # Invalidate metrics cache since positions changed
            self.portfolio_metrics_cache.clear()
            
            return True
        except Exception as e:
            logger.error(f"Error updating position: {e}")
            return False
    
    async def _get_positions_optimized(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Get positions with caching"""
        symbols = request.get('symbols', list(self.position_cache.keys()))
        
        return {
            symbol: self.position_cache.get(symbol, {})
            for symbol in symbols
        }
    
    async def _calculate_metrics_optimized(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate portfolio metrics with caching"""
        cache_key = str(hash(str(request)))
        
        # Check if we have cached metrics and they're recent
        current_time = time.time()
        if (cache_key in self.portfolio_metrics_cache and 
            current_time - self.last_update_time < 1.0):  # 1 second cache
            return self.portfolio_metrics_cache[cache_key]
        
        # Calculate new metrics
        metrics = self._calculate_metrics_sync()
        
        # Cache the result
        self.portfolio_metrics_cache[cache_key] = metrics
        
        return metrics
    
    def _calculate_metrics_sync(self) -> Dict[str, Any]:
        """Synchronous metrics calculation"""
        # Implement actual metrics calculation
        total_value = sum(
            pos.get('quantity', 0) * pos.get('price', 0)
            for pos in self.position_cache.values()
        )
        
        return {
            'total_value': total_value,
            'position_count': len(self.position_cache),
            'last_updated': self.last_update_time
        }

class InterfaceCoordinator:
    """Coordinates communication between all interfaces"""
    
    def __init__(self):
        self.interfaces: Dict[str, OptimizedInterface] = {}
        self.message_router: Dict[str, str] = {}  # message_type -> interface_name
        self.is_running = False
        
    def register_interface(self, interface: OptimizedInterface):
        """Register an interface with the coordinator"""
        self.interfaces[interface.interface_name] = interface
        logger.info(f"Registered interface: {interface.interface_name}")
    
    async def start_coordination(self):
        """Start coordinating all interfaces"""
        self.is_running = True
        
        # Start all interface processing loops
        tasks = []
        for interface in self.interfaces.values():
            task = asyncio.create_task(interface.start_processing())
            tasks.append(task)
        
        # Wait for all tasks
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Error in interface coordination: {e}")
        finally:
            self.is_running = False
    
    def stop_coordination(self):
        """Stop coordinating all interfaces"""
        self.is_running = False
        for interface in self.interfaces.values():
            interface.stop_processing()
    
    async def send_cross_interface_message(
        self, 
        source_interface: str,
        target_interface: str, 
        message_type: str, 
        payload: Any,
        priority: int = 0
    ) -> Optional[Any]:
        """Send message between interfaces"""
        if target_interface not in self.interfaces:
            logger.error(f"Target interface not found: {target_interface}")
            return None
        
        target = self.interfaces[target_interface]
        message_id = await target.send_message(
            target_interface, message_type, payload, priority
        )
        
        return message_id
    
    def get_interface_metrics(self) -> Dict[str, InterfaceMetrics]:
        """Get metrics for all interfaces"""
        return {
            name: interface.message_queue.metrics
            for name, interface in self.interfaces.items()
        }

# Global coordinator instance
_global_coordinator: Optional[InterfaceCoordinator] = None

def get_interface_coordinator() -> InterfaceCoordinator:
    """Get the global interface coordinator"""
    global _global_coordinator
    if _global_coordinator is None:
        _global_coordinator = InterfaceCoordinator()
    return _global_coordinator

async def initialize_optimized_interfaces():
    """Initialize all optimized interfaces"""
    coordinator = get_interface_coordinator()
    
    # Create and register interfaces
    strategy_interface = StrategyInterface()
    execution_interface = ExecutionInterface()
    portfolio_interface = PortfolioInterface()
    
    coordinator.register_interface(strategy_interface)
    coordinator.register_interface(execution_interface)
    coordinator.register_interface(portfolio_interface)
    
    logger.info("Optimized interfaces initialized")
    return coordinator
