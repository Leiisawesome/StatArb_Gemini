"""
Enhanced Portfolio Manager - Institutional Grade
Integrates position management, allocation, rebalancing, and cash management
"""
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
import logging
import threading
import asyncio
import time
import uuid
from collections import defaultdict, deque

# Import ISystemComponent for orchestrator integration
try:
    from ...system.interfaces import ISystemComponent
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

from .position_manager import PositionManager, Position, PositionType, PositionSummary
from .allocation_engine import AllocationEngine, AllocationRequest, AllocationResult, AllocationMethod
from .rebalancer import PortfolioRebalancer, RebalanceType, RebalanceResult
from .cash_manager import CashManager, CashTransaction, CashTransactionType

@dataclass
class PortfolioSnapshot:
    """Complete portfolio snapshot"""
    timestamp: datetime
    total_value: Decimal
    cash_balance: Decimal
    invested_capital: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    position_count: int
    strategy_allocation: Dict[str, Decimal]
    currency_exposure: Dict[str, Decimal]
    largest_position: Optional[str] = None
    risk_metrics: Dict[str, Any] = field(default_factory=dict)

class EnhancedPortfolioManager(ISystemComponent):
    """
    Enhanced Portfolio Manager with ISystemComponent Integration
    
    Institutional-grade portfolio manager with orchestrator integration:
    - Implements ISystemComponent for lifecycle management
    - Integrates position management, allocation, rebalancing, and cash management
    - Health monitoring and performance tracking
    - Professional portfolio analytics and reporting
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Component identification and lifecycle
        self.component_id = str(uuid.uuid4())
        self.is_initialized = False
        self.is_operational = False
        self.start_time = None
        
        # Health and performance tracking
        self.health_metrics = {
            'component_type': 'EnhancedPortfolioManager',
            'initialization_status': 'pending',
            'operational_status': 'inactive',
            'last_health_check': None,
            'error_count': 0,
            'warning_count': 0,
            'performance_metrics': {
                'total_portfolio_updates': 0,
                'successful_portfolio_updates': 0,
                'failed_portfolio_updates': 0,
                'average_update_time': 0.0,
                'positions_count': 0
            }
        }
        
        # Initialize components
        self.position_manager = PositionManager(config.get('position_config', {}))
        self.allocation_engine = AllocationEngine(config.get('allocation_config', {}))
        self.cash_manager = CashManager(config.get('cash_config', {}))
        self.rebalancer = PortfolioRebalancer(
            config.get('rebalancer_config', {}),
            self.position_manager,
            self.allocation_engine
        )
        
        # Threading
        self._lock = threading.Lock()
        
        self.logger.info(f"🚀 Enhanced Portfolio Manager initialized with component ID: {self.component_id}")
    
    # ISystemComponent Interface Implementation
    
    async def initialize(self) -> bool:
        """Initialize the Enhanced Portfolio Manager"""
        try:
            self.logger.info("🔄 Initializing Enhanced Portfolio Manager...")
            
            # Initialize portfolio components
            await self._initialize_portfolio_components()
            
            # Initialize monitoring
            await self._initialize_monitoring_system()
            
            # Update status
            self.is_initialized = True
            self.health_metrics['initialization_status'] = 'completed'
            
            self.logger.info("✅ Enhanced Portfolio Manager initialization complete")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Enhanced Portfolio Manager initialization failed: {e}")
            self.health_metrics['error_count'] += 1
            self.health_metrics['initialization_status'] = 'failed'
            return False
    
    async def start(self) -> bool:
        """Start the Enhanced Portfolio Manager"""
        if not self.is_initialized:
            self.logger.error("Cannot start Enhanced Portfolio Manager: not initialized")
            return False
        
        try:
            self.logger.info("🚀 Starting Enhanced Portfolio Manager...")
            
            # Start portfolio operations
            await self._start_portfolio_operations()
            
            # Start monitoring
            await self._start_monitoring()
            
            # Update status
            self.is_operational = True
            self.start_time = datetime.now()
            self.health_metrics['operational_status'] = 'active'
            
            self.logger.info("✅ Enhanced Portfolio Manager started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Enhanced Portfolio Manager start failed: {e}")
            self.health_metrics['error_count'] += 1
            return False
    
    async def stop(self) -> bool:
        """Stop the Enhanced Portfolio Manager"""
        try:
            self.logger.info("🛑 Stopping Enhanced Portfolio Manager...")
            
            # Stop portfolio operations
            await self._stop_portfolio_operations()
            
            # Stop monitoring
            await self._stop_monitoring()
            
            # Update status
            self.is_operational = False
            self.health_metrics['operational_status'] = 'inactive'
            
            self.logger.info("✅ Enhanced Portfolio Manager stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Enhanced Portfolio Manager stop failed: {e}")
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
            
            # Check portfolio operations health
            operations_healthy = await self._check_operations_health()
            
            # Overall health assessment
            overall_healthy = (
                self.is_initialized and
                self.is_operational and
                operations_healthy and
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
                'operations_healthy': operations_healthy,
                'portfolio_value': 0.0,  # Will be calculated if needed
                'positions_count': 0,   # Will be calculated if needed
                'cash_balance': 0.0,    # Will be calculated if needed
                'last_health_check': current_time.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
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
                'portfolio_id': self.portfolio_id,
                'base_currency': self.base_currency,
                'max_portfolio_risk': float(self.max_portfolio_risk),
                'max_position_concentration': float(self.max_position_concentration),
                'max_strategy_allocation': float(self.max_strategy_allocation)
            },
            'health_metrics': self.health_metrics
        }
    
    # Enhanced Internal Methods
    
    async def _initialize_portfolio_components(self) -> None:
        """Initialize portfolio components"""
        try:
            self.logger.info("🔧 Initializing portfolio components...")
            
            # Initialize portfolio state
            self.portfolio_id = self.config.get('portfolio_id', 'default')
            self.inception_date = datetime.now(timezone.utc)
            self.base_currency = self.config.get('base_currency', 'USD')
            
            # Performance tracking
            self.daily_returns: List[Decimal] = []
            self.portfolio_snapshots: List[PortfolioSnapshot] = []
            self.high_water_mark = Decimal('0')
            self.max_drawdown = Decimal('0')
            
            # Risk limits
            self.max_portfolio_risk = Decimal(str(self.config.get('max_portfolio_risk', 0.20)))
            self.max_position_concentration = Decimal(str(self.config.get('max_concentration', 0.10)))
            self.max_strategy_allocation = Decimal(str(self.config.get('max_strategy_allocation', 0.30)))
            
            # Performance metrics
            self.portfolio_metrics = {
                'total_return': Decimal('0'),
                'annualized_return': Decimal('0'),
                'volatility': Decimal('0'),
                'sharpe_ratio': Decimal('0'),
                'max_drawdown': Decimal('0'),
                'win_rate': Decimal('0'),
                'profit_factor': Decimal('0'),
                'calmar_ratio': Decimal('0')
            }
            
            self.logger.info("✅ Portfolio components initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize portfolio components: {e}")
            raise
    
    async def _initialize_monitoring_system(self) -> None:
        """Initialize monitoring system"""
        try:
            self.logger.info("📈 Initializing monitoring system...")
            
            # Initialize performance monitoring
            self.health_metrics['performance_metrics'] = {
                'total_portfolio_updates': 0,
                'successful_portfolio_updates': 0,
                'failed_portfolio_updates': 0,
                'average_update_time': 0.0,
                'positions_count': 0
            }
            
            self.logger.info("✅ Monitoring system initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize monitoring system: {e}")
            raise
    
    async def _start_portfolio_operations(self) -> None:
        """Start portfolio operations"""
        try:
            self.logger.info("📊 Starting portfolio operations...")
            # Portfolio operations are event-driven, no background tasks needed
            self.logger.info("✅ Portfolio operations started")
            
        except Exception as e:
            self.logger.error(f"Failed to start portfolio operations: {e}")
            raise
    
    async def _start_monitoring(self) -> None:
        """Start monitoring systems"""
        try:
            self.logger.info("📊 Starting monitoring systems...")
            # Monitoring is passive for portfolio manager
            self.logger.info("✅ Monitoring systems started")
            
        except Exception as e:
            self.logger.error(f"Failed to start monitoring: {e}")
            raise
    
    async def _stop_portfolio_operations(self) -> None:
        """Stop portfolio operations"""
        try:
            self.logger.info("📊 Stopping portfolio operations...")
            # No background tasks to stop
            self.logger.info("✅ Portfolio operations stopped")
            
        except Exception as e:
            self.logger.error(f"Failed to stop portfolio operations: {e}")
            raise
    
    async def _stop_monitoring(self) -> None:
        """Stop monitoring systems"""
        try:
            self.logger.info("📊 Stopping monitoring systems...")
            # Monitoring is passive for portfolio manager
            self.logger.info("✅ Monitoring systems stopped")
            
        except Exception as e:
            self.logger.error(f"Failed to stop monitoring: {e}")
            raise
    
    async def _check_operations_health(self) -> bool:
        """Check health of portfolio operations"""
        try:
            # Basic health check - verify core functionality
            # Check if components are available
            return (
                self.position_manager is not None and
                self.cash_manager is not None and
                self.allocation_engine is not None and
                self.rebalancer is not None
            )
            
        except Exception as e:
            self.logger.warning(f"Operations health check failed: {e}")
            return False
    
    # Original Portfolio Management Methods
    
    def get_total_value(self) -> Decimal:
        """Get total portfolio value"""
        try:
            positions_value = sum(pos.market_value for pos in self.position_manager.get_all_positions())
            cash_balance = self.cash_manager.get_balance()
            return Decimal(str(positions_value)) + cash_balance
        except Exception as e:
            self.logger.error(f"Error calculating total value: {e}")
            return Decimal('0')
    
    def open_position(self, symbol: str, position_type: PositionType, 
                     signal_strength: Decimal, strategy_id: str,
                     allocation_method: AllocationMethod = None, **kwargs) -> Optional[str]:
        """Open a new position with integrated allocation and cash management"""
        try:
            with self.portfolio_lock:
                # Create allocation request
                allocation_request = AllocationRequest(
                    request_id=f"alloc_{datetime.now().timestamp()}",
                    strategy_id=strategy_id,
                    symbol=symbol,
                    signal_strength=signal_strength,
                    target_allocation=kwargs.get('target_allocation'),
                    max_allocation=kwargs.get('max_allocation'),
                    risk_score=kwargs.get('risk_score'),
                    metadata=kwargs.get('metadata', {})
                )
                
                # Calculate allocation
                allocation_result = self.allocation_engine.calculate_allocation(
                    allocation_request, allocation_method
                )
                
                if not allocation_result or allocation_result.allocated_capital <= 0:
                    self.logger.warning(f"No allocation approved for {symbol}")
                    return None
                
                # Check cash availability
                required_cash = allocation_result.allocated_capital
                available_cash = self.cash_manager.get_available_cash(self.base_currency)
                
                if available_cash < required_cash:
                    self.logger.warning(f"Insufficient cash for {symbol}: "
                                      f"required {required_cash}, available {available_cash}")
                    return None
                
                # Reserve cash
                if not self.cash_manager.reserve_cash(
                    required_cash, 
                    self.base_currency, 
                    reference_id=allocation_request.request_id,
                    description=f"Position opening: {symbol}"
                ):
                    return None
                
                # Calculate position size and entry price
                entry_price = kwargs.get('entry_price', Decimal('100'))  # Should come from market data
                quantity = allocation_result.position_size
                
                # Open position
                position_id = self.position_manager.open_position(
                    symbol=symbol,
                    position_type=position_type,
                    quantity=quantity,
                    entry_price=entry_price,
                    strategy_id=strategy_id,
                    **kwargs
                )
                
                if position_id:
                    # Process cash settlement
                    settlement_transaction = CashTransaction(
                        transaction_id=f"settle_{position_id}",
                        transaction_type=CashTransactionType.TRADE_SETTLEMENT,
                        amount=-required_cash,
                        currency=self.base_currency,
                        description=f"Position opened: {symbol}",
                        reference_id=position_id
                    )
                    
                    self.cash_manager.process_cash_transaction(settlement_transaction)
                    
                    # Update portfolio metrics
                    self._update_portfolio_metrics()
                    
                    self.logger.info(f"Opened position {position_id} for {symbol}: "
                                   f"{quantity} @ {entry_price} (${required_cash})")
                    
                    return position_id
                else:
                    # Release reserved cash on failure
                    self.cash_manager.release_cash_reserve(
                        required_cash, 
                        self.base_currency,
                        reference_id=allocation_request.request_id
                    )
                
                return None
                
        except Exception as e:
            self.logger.error(f"Error opening position for {symbol}: {e}")
            return None
    
    def close_position(self, position_id: str, exit_price: Decimal = None,
                      close_reason: str = "manual") -> bool:
        """Close position with integrated cash management"""
        try:
            with self.portfolio_lock:
                position = self.position_manager.get_position(position_id)
                if not position:
                    return False
                
                # Use current price if exit price not provided
                if exit_price is None:
                    exit_price = position.current_price
                
                # Calculate proceeds
                proceeds = position.quantity * exit_price
                
                # Close position
                if self.position_manager.close_position(position_id, exit_price, close_reason):
                    # Process cash settlement
                    settlement_transaction = CashTransaction(
                        transaction_id=f"close_{position_id}",
                        transaction_type=CashTransactionType.TRADE_SETTLEMENT,
                        amount=proceeds,
                        currency=self.base_currency,
                        description=f"Position closed: {position.symbol}",
                        reference_id=position_id
                    )
                    
                    self.cash_manager.process_cash_transaction(settlement_transaction)
                    
                    # Deallocate from allocation engine
                    self.allocation_engine.deallocate(position.strategy_id, position.symbol)
                    
                    # Update portfolio metrics
                    self._update_portfolio_metrics()
                    
                    self.logger.info(f"Closed position {position_id} for {position.symbol}: "
                                   f"proceeds ${proceeds}")
                    
                    return True
                
                return False
                
        except Exception as e:
            self.logger.error(f"Error closing position {position_id}: {e}")
            return False
    
    def update_market_data(self, price_updates: Dict[str, Decimal]):
        """Update market data across all components"""
        try:
            with self.portfolio_lock:
                # Update position prices
                self.position_manager.update_position_prices(price_updates)
                
                # Update portfolio metrics
                self._update_portfolio_metrics()
                
                self.logger.debug(f"Updated market data for {len(price_updates)} symbols")
                
        except Exception as e:
            self.logger.error(f"Error updating market data: {e}")
    
    def execute_rebalance(self, strategy_id: str = None, 
                         rebalance_type: RebalanceType = RebalanceType.DRIFT_CORRECTION,
                         force: bool = False) -> Optional[RebalanceResult]:
        """Execute portfolio rebalancing"""
        try:
            with self.portfolio_lock:
                return self.rebalancer.execute_rebalance(strategy_id, rebalance_type, force)
                
        except Exception as e:
            self.logger.error(f"Error executing rebalance: {e}")
            return None
    
    def set_strategy_targets(self, strategy_id: str, targets: Dict[str, Decimal]):
        """Set target allocations for a strategy"""
        self.rebalancer.set_target_portfolio(strategy_id, targets)
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio summary"""
        with self.portfolio_lock:
            # Get component summaries
            position_summary = self.position_manager.get_position_summary()
            cash_summary = self.cash_manager.get_cash_summary()
            allocation_summary = self.allocation_engine.get_allocation_summary()
            
            # Calculate total portfolio value
            total_positions_value = position_summary.total_market_value
            total_cash = Decimal(str(cash_summary['total_cash']))
            total_portfolio_value = total_positions_value + total_cash
            
            # Calculate allocations by strategy
            strategy_allocations = {}
            for strategy_id in self.allocation_engine.current_allocations:
                strategy_value = sum(self.allocation_engine.current_allocations[strategy_id].values())
                strategy_allocations[strategy_id] = {
                    'value': float(strategy_value),
                    'percentage': float((strategy_value / total_portfolio_value) * 100) if total_portfolio_value > 0 else 0
                }
            
            return {
                'portfolio_id': self.portfolio_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'total_value': float(total_portfolio_value),
                'cash_balance': float(total_cash),
                'invested_capital': float(total_positions_value),
                'unrealized_pnl': float(position_summary.total_unrealized_pnl),
                'position_count': position_summary.total_positions,
                'strategy_allocations': strategy_allocations,
                'performance_metrics': {k: float(v) for k, v in self.portfolio_metrics.items()},
                'position_summary': {
                    'total_positions': position_summary.total_positions,
                    'long_positions': position_summary.long_positions,
                    'short_positions': position_summary.short_positions,
                    'largest_position': position_summary.largest_position,
                    'unrealized_pnl': float(position_summary.total_unrealized_pnl),
                    'unrealized_pnl_percent': float(position_summary.unrealized_pnl_percent)
                },
                'cash_summary': cash_summary,
                'allocation_summary': allocation_summary,
                'risk_metrics': self._calculate_risk_metrics()
            }
    
    def get_portfolio_snapshot(self) -> PortfolioSnapshot:
        """Create portfolio snapshot"""
        with self.portfolio_lock:
            position_summary = self.position_manager.get_position_summary()
            cash_balance = self.cash_manager.get_cash_balance(self.base_currency)
            
            total_value = position_summary.total_market_value + cash_balance
            
            snapshot = PortfolioSnapshot(
                timestamp=datetime.now(timezone.utc),
                total_value=total_value,
                cash_balance=cash_balance,
                invested_capital=position_summary.total_market_value,
                unrealized_pnl=position_summary.total_unrealized_pnl,
                realized_pnl=self.position_manager.position_metrics['total_realized_pnl'],
                position_count=position_summary.total_positions,
                strategy_allocation=self._get_strategy_allocations(),
                currency_exposure=self._get_currency_exposure(),
                largest_position=position_summary.largest_position,
                risk_metrics=self._calculate_risk_metrics()
            )
            
            self.portfolio_snapshots.append(snapshot)
            
            # Limit snapshot history
            if len(self.portfolio_snapshots) > 10000:
                self.portfolio_snapshots = self.portfolio_snapshots[-5000:]
            
            return snapshot
    
    def calculate_performance_metrics(self) -> Dict[str, Decimal]:
        """Calculate comprehensive performance metrics"""
        try:
            if len(self.portfolio_snapshots) < 2:
                return self.portfolio_metrics
            
            # Calculate returns
            returns = []
            values = [snapshot.total_value for snapshot in self.portfolio_snapshots[-252:]]  # Last year
            
            for i in range(1, len(values)):
                if values[i-1] > 0:
                    daily_return = (values[i] - values[i-1]) / values[i-1]
                    returns.append(daily_return)
            
            if not returns:
                return self.portfolio_metrics
            
            # Total return
            if len(values) > 1 and values[0] > 0:
                total_return = (values[-1] - values[0]) / values[0]
                self.portfolio_metrics['total_return'] = total_return
                
                # Annualized return
                days = len(values) - 1
                if days > 0:
                    annualized_return = ((1 + total_return) ** (Decimal('252') / Decimal(str(days)))) - 1
                    self.portfolio_metrics['annualized_return'] = annualized_return
            
            # Volatility (annualized)
            if len(returns) > 1:
                mean_return = sum(returns) / len(returns)
                variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
                volatility = (variance ** Decimal('0.5')) * (Decimal('252') ** Decimal('0.5'))
                self.portfolio_metrics['volatility'] = volatility
                
                # Sharpe ratio (assuming 0% risk-free rate)
                if volatility > 0:
                    sharpe_ratio = self.portfolio_metrics['annualized_return'] / volatility
                    self.portfolio_metrics['sharpe_ratio'] = sharpe_ratio
            
            # Drawdown analysis
            peak = values[0]
            max_drawdown = Decimal('0')
            
            for value in values:
                if value > peak:
                    peak = value
                
                drawdown = (peak - value) / peak if peak > 0 else Decimal('0')
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
            
            self.portfolio_metrics['max_drawdown'] = max_drawdown
            self.max_drawdown = max_drawdown
            
            # Calmar ratio
            if max_drawdown > 0:
                calmar_ratio = self.portfolio_metrics['annualized_return'] / max_drawdown
                self.portfolio_metrics['calmar_ratio'] = calmar_ratio
            
            # Win rate and profit factor from position manager
            pos_metrics = self.position_manager.get_position_metrics()
            if pos_metrics['total_positions_closed'] > 0:
                self.portfolio_metrics['win_rate'] = Decimal(str(pos_metrics['win_rate']))
            
            return self.portfolio_metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {e}")
            return self.portfolio_metrics
    
    def _update_portfolio_metrics(self):
        """Update portfolio metrics"""
        snapshot = self.get_portfolio_snapshot()
        self.calculate_performance_metrics()
        
        # Update high water mark
        if snapshot.total_value > self.high_water_mark:
            self.high_water_mark = snapshot.total_value
    
    def _get_strategy_allocations(self) -> Dict[str, Decimal]:
        """Get current strategy allocations"""
        allocations = {}
        for strategy_id, symbol_allocations in self.allocation_engine.current_allocations.items():
            allocations[strategy_id] = sum(symbol_allocations.values())
        return allocations
    
    def _get_currency_exposure(self) -> Dict[str, Decimal]:
        """Get currency exposure"""
        # For now, assume all positions are in base currency
        total_value = sum(pos.market_value for pos in self.position_manager.get_all_positions())
        return {self.base_currency: total_value}
    
    def _calculate_risk_metrics(self) -> Dict[str, Any]:
        """Calculate portfolio risk metrics"""
        positions = self.position_manager.get_all_positions()
        
        if not positions:
            return {}
        
        total_value = sum(abs(pos.market_value) for pos in positions)
        
        # Concentration risk
        max_position_weight = Decimal('0')
        if total_value > 0:
            max_position_weight = max(abs(pos.market_value) / total_value for pos in positions)
        
        # Strategy concentration
        strategy_concentrations = {}
        for strategy_id, allocation in self._get_strategy_allocations().items():
            if total_value > 0:
                strategy_concentrations[strategy_id] = allocation / total_value
        
        max_strategy_concentration = max(strategy_concentrations.values()) if strategy_concentrations else Decimal('0')
        
        # Long/short exposure
        long_exposure = sum(pos.market_value for pos in positions if pos.position_type == PositionType.LONG)
        short_exposure = sum(abs(pos.market_value) for pos in positions if pos.position_type == PositionType.SHORT)
        net_exposure = long_exposure - short_exposure
        gross_exposure = long_exposure + short_exposure
        
        return {
            'max_position_concentration': float(max_position_weight),
            'max_strategy_concentration': float(max_strategy_concentration),
            'long_exposure': float(long_exposure),
            'short_exposure': float(short_exposure),
            'net_exposure': float(net_exposure),
            'gross_exposure': float(gross_exposure),
            'leverage': float(gross_exposure / total_value) if total_value > 0 else 0,
            'positions_at_risk': len([p for p in positions if not p.is_profitable])
        }
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk summary"""
        risk_metrics = self._calculate_risk_metrics()
        
        # Add limit checks
        risk_checks = {
            'position_concentration_ok': risk_metrics.get('max_position_concentration', 0) <= float(self.max_position_concentration),
            'strategy_concentration_ok': risk_metrics.get('max_strategy_concentration', 0) <= float(self.max_strategy_allocation),
            'portfolio_risk_ok': self.portfolio_metrics['volatility'] <= self.max_portfolio_risk
        }
        
        return {
            'risk_metrics': risk_metrics,
            'risk_limits': {
                'max_position_concentration': float(self.max_position_concentration),
                'max_strategy_allocation': float(self.max_strategy_allocation),
                'max_portfolio_risk': float(self.max_portfolio_risk)
            },
            'risk_checks': risk_checks,
            'overall_risk_status': all(risk_checks.values())
        }
    
    def portfolio_health_check(self) -> bool:
        """Perform portfolio health check"""
        try:
            # Check component health
            components_healthy = True
            
            # Basic checks
            cash_balance = self.cash_manager.get_cash_balance(self.base_currency)
            if cash_balance < 0:
                self.logger.warning("Negative cash balance detected")
                components_healthy = False
            
            # Risk checks
            risk_summary = self.get_risk_summary()
            if not risk_summary['overall_risk_status']:
                self.logger.warning("Risk limits exceeded")
                components_healthy = False
            
            # Position checks
            stop_loss_alerts = self.position_manager.check_stop_loss_take_profit()
            if stop_loss_alerts:
                self.logger.info(f"Stop loss/take profit alerts: {len(stop_loss_alerts)}")
            
            return components_healthy
            
        except Exception as e:
            self.logger.error(f"Error in portfolio health check: {e}")
            return False
    
    def emergency_liquidation(self) -> bool:
        """Emergency liquidation of all positions"""
        try:
            self.logger.warning("Initiating emergency liquidation")
            
            positions = self.position_manager.get_all_positions()
            closed_positions = 0
            
            for position in positions:
                if self.close_position(position.position_id, position.current_price, "emergency_liquidation"):
                    closed_positions += 1
            
            self.logger.warning(f"Emergency liquidation completed: {closed_positions} positions closed")
            return closed_positions == len(positions)
            
        except Exception as e:
            self.logger.error(f"Error in emergency liquidation: {e}")
            return False
    
    def cleanup(self):
        """Cleanup portfolio manager and all components"""
        try:
            self.position_manager.cleanup()
            self.allocation_engine.cleanup()
            self.cash_manager.cleanup()
            self.rebalancer.cleanup()
            
            self.logger.info(f"Enhanced portfolio manager cleaned up for portfolio {self.portfolio_id}")
            
        except Exception as e:
            self.logger.error(f"Error during portfolio manager cleanup: {e}")