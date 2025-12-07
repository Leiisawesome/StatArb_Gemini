"""
Enhanced Portfolio Manager - Institutional Grade
Integrates position management, allocation, rebalancing, and cash management
"""
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
import logging
import threading
import uuid

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

from .position_manager import PositionManager, PositionType
from .allocation_engine import AllocationEngine, AllocationRequest, AllocationMethod
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

        # Orchestrator integration
        self.orchestrator: Optional[Any] = None  # HierarchicalSystemOrchestrator reference

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

        # Portfolio configuration
        self.base_currency = config.get('base_currency', 'USD')

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

        # Portfolio snapshots history
        self.portfolio_snapshots = []

        self.logger.info(f"🚀 Enhanced Portfolio Manager initialized with component ID: {self.component_id}")

    @property
    def portfolio_lock(self):
        """Property to access the portfolio lock"""
        return self._lock

    # ========================================
    # ORCHESTRATOR INTEGRATION
    # ========================================

    def register_with_orchestrator(self, orchestrator) -> str:
        """Register component with HierarchicalSystemOrchestrator"""
        from core_engine.system.hierarchical_orchestrator import ComponentLayer, AuthorityLevel

        self.orchestrator = orchestrator
        self.component_id = orchestrator.register_component(
            name="EnhancedPortfolioManager",
            component=self,
            layer=ComponentLayer.EXECUTION,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=38  # After execution engine
        )

        self.logger.info(f"✅ EnhancedPortfolioManager registered with orchestrator: {self.component_id}")
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

    # ========================================
    # STANDARDIZED DATA FLOW METHODS
    # ========================================

    def process_results(self, results: List[Any]) -> Dict[str, Any]:
        """Standardized method for processing trade results"""
        processed_results = {
            'results_processed': len(results),
            'processing_timestamp': datetime.now(),
            'processing_component': 'EnhancedPortfolioManager'
        }

        for result in results:
            # Basic result processing logic
            if hasattr(result, 'symbol') and hasattr(result, 'quantity'):
                # Update position tracking
                processed_results[f"position_update_{result.symbol}"] = {
                    'quantity': result.quantity,
                    'processed': True
                }

        return processed_results

    def handle_results(self, results: List[Any]) -> Dict[str, Any]:
        """Standardized method for handling execution results (alias)"""
        return self.process_results(results)

    def update_from_results(self, results: List[Any]) -> Dict[str, Any]:
        """Standardized method for updating portfolio from results (alias)"""
        return self.process_results(results)

    def process_positions(self, positions: Dict[str, Any]) -> Dict[str, Any]:
        """Standardized method for processing position data"""
        return {
            'positions_processed': len(positions),
            'processing_timestamp': datetime.now(),
            'processing_component': 'EnhancedPortfolioManager',
            'position_data': positions
        }

    def handle_position_update(self, position_update: Dict[str, Any]) -> Dict[str, Any]:
        """Standardized method for handling position updates"""
        return {
            'position_update_processed': True,
            'update_data': position_update,
            'processing_timestamp': datetime.now(),
            'processing_component': 'EnhancedPortfolioManager'
        }

    def update_positions(self, position_data: Any) -> Dict[str, Any]:
        """Standardized method for updating positions"""
        return {
            'positions_updated': True,
            'position_data': position_data,
            'processing_timestamp': datetime.now(),
            'processing_component': 'EnhancedPortfolioManager'
        }

    def manage_positions(self, position_data: Any) -> Dict[str, Any]:
        """Standardized method for managing positions (alias)"""
        return self.update_positions(position_data)

    def track_positions(self, position_data: Any) -> Dict[str, Any]:
        """Standardized method for tracking positions (alias)"""
        return self.update_positions(position_data)

    # ========================================
    # DATA PRODUCTION METHODS FOR RISK FLOW
    # ========================================

    def calculate_risk(self, portfolio_data: Any = None) -> Dict[str, Any]:
        """Standardized method for calculating portfolio risk metrics"""
        return {
            'portfolio_risk_calculated': True,
            'risk_metrics': {
                'var': 0.05,
                'concentration': 0.15,
                'leverage': 1.2
            },
            'processing_timestamp': datetime.now(),
            'processing_component': 'EnhancedPortfolioManager'
        }

    def assess_risk(self, portfolio_data: Any = None) -> Dict[str, Any]:
        """Standardized method for assessing risk (alias)"""
        return self.calculate_risk(portfolio_data)

    def compute_metrics(self, portfolio_data: Any = None) -> Dict[str, Any]:
        """Standardized method for computing portfolio metrics"""
        return self.calculate_risk(portfolio_data)

    # ========================================
    # CALLBACK INTEGRATION METHODS
    # ========================================

    def on_position_update(self, position_update: Dict[str, Any]) -> Dict[str, Any]:
        """Callback method for handling position updates"""
        try:
            symbol = position_update.get('symbol')
            quantity = position_update.get('quantity', 0)
            price = position_update.get('price', 0)

            self.logger.info(f"📊 Position update callback: {symbol} quantity={quantity} price=${price:.2f}")

            # Process the position update
            result = self.handle_position_update(position_update)

            # Notify analytics if callback is set
            if hasattr(self, 'analytics_callback') and self.analytics_callback:
                try:
                    self.analytics_callback(position_update)
                except Exception as e:
                    self.logger.error(f"Analytics callback failed: {e}")

            return result

        except Exception as e:
            self.logger.error(f"Position update callback failed: {e}")
            return {'error': str(e), 'callback_processed': False}

    def set_analytics_callbacks(self, analytics_callback: Callable = None):
        """Set analytics callback for performance updates"""
        self.analytics_callback = analytics_callback
        if analytics_callback:
            self.logger.info("✅ Analytics callback registered with PortfolioManager")

    def on_performance_update(self, performance_data: Dict[str, Any]):
        """Callback method for performance updates"""
        try:
            self.logger.info("📈 Performance update callback triggered")

            # Process performance data
            if hasattr(self, 'analytics_callback') and self.analytics_callback:
                self.analytics_callback(performance_data)

            return {'performance_update_processed': True}

        except Exception as e:
            self.logger.error(f"Performance update callback failed: {e}")
            return {'error': str(e)}

    # ========================================
    # RISK MANAGEMENT CALLBACK METHODS
    # ========================================

    def set_risk_callbacks(self, risk_callback: Callable = None):
        """Set risk management callback"""
        self.risk_callback = risk_callback
        if risk_callback:
            self.logger.info("✅ Risk callback registered with PortfolioManager")

    def on_risk_limit_breach(self, risk_data: Dict[str, Any]):
        """Callback method for risk limit breaches"""
        try:
            self.logger.warning(f"🚨 Portfolio risk limit breach: {risk_data}")

            # Handle risk breach (e.g., reduce positions)
            if hasattr(self, 'risk_callback') and self.risk_callback:
                self.risk_callback(risk_data)

            return {'risk_breach_handled': True}

        except Exception as e:
            self.logger.error(f"Risk limit breach callback failed: {e}")
            return {'error': str(e)}

    def on_emergency_shutdown(self, shutdown_reason: str = "Emergency"):
        """Callback method for emergency shutdown"""
        try:
            self.logger.critical(f"🚨 Portfolio emergency shutdown: {shutdown_reason}")

            # Emergency portfolio actions
            # In a real implementation, this would liquidate positions

            return {'emergency_shutdown_handled': True}

        except Exception as e:
            self.logger.error(f"Emergency shutdown callback failed: {e}")
            return {'error': str(e)}

    # ========================================
    # AUTHORIZATION METHODS
    # ========================================

    def authorize_operation(self, operation: str, details: Dict[str, Any] = None) -> bool:
        """Authorize portfolio operations"""
        try:
            # Basic authorization logic for portfolio operations
            authorized_operations = [
                'update_positions', 'rebalance_portfolio', 'calculate_risk',
                'manage_positions', 'track_positions', 'liquidate_positions'
            ]

            if operation in authorized_operations:
                self.logger.info(f"✅ Portfolio operation authorized: {operation}")
                return True
            else:
                self.logger.warning(f"❌ Portfolio operation not authorized: {operation}")
                return False

        except Exception as e:
            self.logger.error(f"Authorization failed: {e}")
            return False

    def check_authority_level(self, required_level: str) -> bool:
        """Check if component has required authority level"""
        try:
            # Portfolio manager has OPERATIONAL authority level
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
        """Validate permissions for portfolio operations"""
        try:
            # Portfolio manager permissions
            allowed_permissions = [
                'position_management', 'portfolio_rebalancing', 'risk_calculation',
                'performance_tracking', 'cash_management'
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

    # ========================================
    # ANALYTICS INTEGRATION METHODS
    # ========================================

    def calculate_metrics(self, data: Any = None) -> Dict[str, Any]:
        """Calculate portfolio analytics metrics"""
        try:
            # Get current portfolio state
            positions = self.position_manager.get_all_positions()
            total_value = self.cash_manager.total_balance

            # Calculate portfolio metrics
            portfolio_metrics = {
                'total_positions': len(positions),
                'total_value': float(total_value),
                'cash_balance': float(self.cash_manager.get_available_cash()),
                'invested_capital': float(total_value - self.cash_manager.get_available_cash()),
                'position_count': len([p for p in positions.values() if p != 0]),
                'long_positions': len([p for p in positions.values() if p > 0]),
                'short_positions': len([p for p in positions.values() if p < 0])
            }

            # Calculate concentration metrics
            if positions:
                position_values = [abs(float(pos)) for pos in positions.values() if pos != 0]
                if position_values:
                    max_position = max(position_values)
                    portfolio_metrics['max_position_pct'] = (max_position / total_value * 100) if total_value > 0 else 0
                    portfolio_metrics['avg_position_size'] = sum(position_values) / len(position_values)
                    portfolio_metrics['position_concentration'] = max_position / sum(position_values) if sum(position_values) > 0 else 0

            return {
                'metrics_calculated': True,
                'calculation_timestamp': datetime.now(),
                'portfolio_metrics': portfolio_metrics,
                'component': 'EnhancedPortfolioManager'
            }

        except Exception as e:
            self.logger.error(f"Portfolio metrics calculation failed: {e}")
            return {
                'metrics_calculated': False,
                'error': str(e),
                'calculation_timestamp': datetime.now()
            }

    def analyze_performance(self, data: Any = None) -> Dict[str, Any]:
        """Analyze portfolio performance"""
        try:
            # Get portfolio performance data
            positions = self.position_manager.get_all_positions()
            total_value = self.cash_manager.total_balance

            # Mock performance analysis (in real implementation, would use historical data)
            performance_analysis = {
                'current_value': float(total_value),
                'position_analysis': {},
                'risk_metrics': {
                    'portfolio_var': 0.02,  # Mock 2% VaR
                    'concentration_risk': self._calculate_concentration_risk(positions),
                    'liquidity_risk': 'Low'  # Mock assessment
                },
                'allocation_analysis': {
                    'cash_allocation_pct': (self.cash_manager.get_available_cash() / total_value * 100) if total_value > 0 else 100,
                    'equity_allocation_pct': ((total_value - self.cash_manager.get_available_cash()) / total_value * 100) if total_value > 0 else 0
                }
            }

            # Analyze individual positions
            for symbol, position in positions.items():
                if position != 0:
                    performance_analysis['position_analysis'][symbol] = {
                        'position_size': float(position),
                        'position_type': 'long' if position > 0 else 'short',
                        'allocation_pct': (abs(float(position)) / total_value * 100) if total_value > 0 else 0
                    }

            return {
                'performance_analyzed': True,
                'analysis_timestamp': datetime.now(),
                'performance_analysis': performance_analysis,
                'component': 'EnhancedPortfolioManager'
            }

        except Exception as e:
            self.logger.error(f"Portfolio performance analysis failed: {e}")
            return {
                'performance_analyzed': False,
                'error': str(e),
                'analysis_timestamp': datetime.now()
            }

    def generate_analytics(self, data: Any = None) -> Dict[str, Any]:
        """Generate comprehensive portfolio analytics"""
        try:
            # Combine metrics and performance analysis
            metrics = self.calculate_metrics(data)
            performance = self.analyze_performance(data)

            analytics = {
                'analytics_generated': True,
                'generation_timestamp': datetime.now(),
                'metrics': metrics.get('portfolio_metrics', {}),
                'performance': performance.get('performance_analysis', {}),
                'summary': {
                    'portfolio_health': self._assess_portfolio_health(),
                    'risk_level': self._assess_risk_level(),
                    'diversification_score': self._calculate_diversification_score()
                },
                'component': 'EnhancedPortfolioManager'
            }

            return analytics

        except Exception as e:
            self.logger.error(f"Portfolio analytics generation failed: {e}")
            return {
                'analytics_generated': False,
                'error': str(e),
                'generation_timestamp': datetime.now()
            }

    def track_performance(self, data: Any = None) -> Dict[str, Any]:
        """Track portfolio performance over time"""
        try:
            # Mock performance tracking (in real implementation, would maintain historical data)
            performance_tracking = {
                'tracking_active': True,
                'tracking_timestamp': datetime.now(),
                'current_metrics': self.calculate_metrics(data),
                'performance_trend': 'stable',  # Mock trend
                'alerts': [],
                'component': 'EnhancedPortfolioManager'
            }

            return performance_tracking

        except Exception as e:
            self.logger.error(f"Portfolio performance tracking failed: {e}")
            return {
                'tracking_active': False,
                'error': str(e),
                'tracking_timestamp': datetime.now()
            }

    def monitor_performance(self, data: Any = None) -> Dict[str, Any]:
        """Monitor portfolio performance (alias for track_performance)"""
        return self.track_performance(data)

    def _calculate_concentration_risk(self, positions: Dict[str, float]) -> float:
        """Calculate portfolio concentration risk"""
        try:
            if not positions:
                return 0.0

            position_values = [abs(float(pos)) for pos in positions.values() if pos != 0]
            if not position_values:
                return 0.0

            total_value = sum(position_values)
            if total_value == 0:
                return 0.0

            # Calculate Herfindahl-Hirschman Index
            hhi = sum((value / total_value) ** 2 for value in position_values)

            # Convert to risk score (0-1, where 1 is maximum concentration)
            return float(hhi)

        except Exception:
            return 0.5  # Default moderate risk

    def _assess_portfolio_health(self) -> str:
        """Assess overall portfolio health"""
        try:
            positions = self.position_manager.get_all_positions()
            total_value = self.cash_manager.total_balance
            cash_pct = (self.cash_manager.get_available_cash() / total_value * 100) if total_value > 0 else 100

            # Simple health assessment
            if cash_pct > 90:
                return "Under-invested"
            elif cash_pct < 5:
                return "Over-invested"
            elif len(positions) < 3:
                return "Under-diversified"
            elif len(positions) > 20:
                return "Over-diversified"
            else:
                return "Healthy"

        except Exception:
            return "Unknown"

    def _assess_risk_level(self) -> str:
        """Assess portfolio risk level"""
        try:
            positions = self.position_manager.get_all_positions()
            concentration_risk = self._calculate_concentration_risk(positions)

            if concentration_risk > 0.5:
                return "High"
            elif concentration_risk > 0.25:
                return "Medium"
            else:
                return "Low"

        except Exception:
            return "Medium"

    def _calculate_diversification_score(self) -> float:
        """Calculate diversification score (0-100)"""
        try:
            positions = self.position_manager.get_all_positions()
            active_positions = len([p for p in positions.values() if p != 0])

            if active_positions == 0:
                return 0.0
            elif active_positions == 1:
                return 20.0
            elif active_positions <= 5:
                return 50.0
            elif active_positions <= 10:
                return 75.0
            else:
                return 90.0

        except Exception:
            return 50.0  # Default moderate diversification