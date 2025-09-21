"""
Cash Manager for Portfolio Component
Handles cash management, liquidity planning, and cash optimization
"""
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
import logging

class CashTransactionType(Enum):
    """Types of cash transactions"""
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    DIVIDEND = "dividend"
    INTEREST = "interest"
    TRADE_SETTLEMENT = "trade_settlement"
    FEE = "fee"
    MARGIN_CALL = "margin_call"
    CURRENCY_CONVERSION = "currency_conversion"

class CashStatus(Enum):
    """Cash position status"""
    AVAILABLE = "available"
    RESERVED = "reserved"
    PENDING_SETTLEMENT = "pending_settlement"
    MARGIN_REQUIREMENT = "margin_requirement"

@dataclass
class CashTransaction:
    """Cash transaction record"""
    transaction_id: str
    transaction_type: CashTransactionType
    amount: Decimal
    currency: str
    description: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    settlement_date: Optional[datetime] = None
    reference_id: Optional[str] = None  # Trade ID, order ID, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CashPosition:
    """Cash position by currency"""
    currency: str
    available_balance: Decimal
    reserved_balance: Decimal
    pending_settlements: Decimal
    margin_requirement: Decimal
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def total_balance(self) -> Decimal:
        """Total cash balance"""
        return self.available_balance + self.reserved_balance + self.pending_settlements
    
    @property
    def usable_balance(self) -> Decimal:
        """Balance available for trading"""
        return self.available_balance - self.margin_requirement

@dataclass
class CashForecast:
    """Cash flow forecast"""
    date: datetime
    projected_inflows: Decimal
    projected_outflows: Decimal
    net_flow: Decimal
    projected_balance: Decimal
    confidence_level: Decimal  # 0 to 1

class CashManager:
    """
    Advanced cash management system with multi-currency support,
    liquidity planning, and cash optimization
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Configuration
        self.base_currency = config.get('base_currency', 'USD')
        self.min_cash_buffer = Decimal(str(config.get('min_cash_buffer', 50000)))
        self.target_cash_ratio = Decimal(str(config.get('target_cash_ratio', 0.05)))  # 5%
        self.max_cash_ratio = Decimal(str(config.get('max_cash_ratio', 0.20)))  # 20%
        
        # Cash positions by currency
        self.cash_positions: Dict[str, CashPosition] = {}
        
        # Transaction history
        self.transaction_history: List[CashTransaction] = []
        self.daily_cash_flows: Dict[str, Decimal] = {}  # date -> net flow
        
        # Cash reserves and allocations
        self.strategy_cash_allocations: Dict[str, Decimal] = {}
        self.emergency_reserves: Decimal = Decimal('0')
        self.margin_requirements: Dict[str, Decimal] = {}  # strategy -> requirement
        
        # Interest and yield tracking
        self.interest_rates: Dict[str, Decimal] = {}  # currency -> rate
        self.cash_yields: Dict[str, Decimal] = {}
        
        # Forecast data
        self.cash_forecasts: List[CashForecast] = []
        
        # Exchange rates for multi-currency
        self.exchange_rates: Dict[Tuple[str, str], Decimal] = {}
        
        # Metrics
        self.cash_metrics = {
            'total_transactions': 0,
            'total_inflows': Decimal('0'),
            'total_outflows': Decimal('0'),
            'average_daily_flow': Decimal('0'),
            'cash_utilization': Decimal('0'),
            'interest_earned': Decimal('0'),
            'currency_conversion_costs': Decimal('0')
        }
        
        # Initialize base currency position
        initial_cash = Decimal(str(config.get('initial_cash', 1000000)))
        self._initialize_cash_position(self.base_currency, initial_cash)
        
        self.logger.info(f"Cash manager initialized with {initial_cash} {self.base_currency}")
    
    def get_cash_balance(self, currency: str = None, 
                        include_reserved: bool = False) -> Union[Decimal, Dict[str, Decimal]]:
        """Get cash balance for currency or all currencies"""
        if currency:
            if currency not in self.cash_positions:
                return Decimal('0')
            
            position = self.cash_positions[currency]
            if include_reserved:
                return position.total_balance
            else:
                return position.available_balance
        else:
            # Return all currencies
            balances = {}
            for curr, position in self.cash_positions.items():
                if include_reserved:
                    balances[curr] = position.total_balance
                else:
                    balances[curr] = position.available_balance
            return balances
    
    def get_available_cash(self, currency: str = None) -> Union[Decimal, Dict[str, Decimal]]:
        """Get available cash for trading"""
        if currency:
            if currency not in self.cash_positions:
                return Decimal('0')
            return self.cash_positions[currency].usable_balance
        else:
            return {curr: pos.usable_balance for curr, pos in self.cash_positions.items()}
    
    def reserve_cash(self, amount: Decimal, currency: str = None, 
                    reference_id: str = None, description: str = "Reserved") -> bool:
        """Reserve cash for pending trades"""
        currency = currency or self.base_currency
        
        try:
            if currency not in self.cash_positions:
                self.logger.error(f"Currency {currency} not available")
                return False
            
            position = self.cash_positions[currency]
            
            if position.available_balance < amount:
                self.logger.warning(f"Insufficient available cash in {currency}: "
                                  f"requested {amount}, available {position.available_balance}")
                return False
            
            # Move from available to reserved
            position.available_balance -= amount
            position.reserved_balance += amount
            position.last_updated = datetime.now(timezone.utc)
            
            # Record transaction
            self._record_transaction(
                transaction_type=CashTransactionType.TRADE_SETTLEMENT,
                amount=-amount,
                currency=currency,
                description=f"Reserved: {description}",
                reference_id=reference_id
            )
            
            self.logger.debug(f"Reserved {amount} {currency} for {description}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error reserving cash: {e}")
            return False
    
    def release_cash_reserve(self, amount: Decimal, currency: str = None,
                            reference_id: str = None, description: str = "Released") -> bool:
        """Release reserved cash back to available"""
        currency = currency or self.base_currency
        
        try:
            if currency not in self.cash_positions:
                return False
            
            position = self.cash_positions[currency]
            
            if position.reserved_balance < amount:
                self.logger.warning(f"Insufficient reserved cash in {currency}: "
                                  f"requested {amount}, reserved {position.reserved_balance}")
                # Release what's available
                amount = position.reserved_balance
            
            # Move from reserved to available
            position.reserved_balance -= amount
            position.available_balance += amount
            position.last_updated = datetime.now(timezone.utc)
            
            # Record transaction
            self._record_transaction(
                transaction_type=CashTransactionType.TRADE_SETTLEMENT,
                amount=amount,
                currency=currency,
                description=f"Released: {description}",
                reference_id=reference_id
            )
            
            self.logger.debug(f"Released {amount} {currency} from reserve")
            return True
            
        except Exception as e:
            self.logger.error(f"Error releasing cash reserve: {e}")
            return False
    
    def process_cash_transaction(self, transaction: CashTransaction) -> bool:
        """Process a cash transaction"""
        try:
            currency = transaction.currency
            
            # Ensure currency position exists
            if currency not in self.cash_positions:
                self._initialize_cash_position(currency, Decimal('0'))
            
            position = self.cash_positions[currency]
            
            # Process based on transaction type
            if transaction.transaction_type in [
                CashTransactionType.DEPOSIT, 
                CashTransactionType.DIVIDEND,
                CashTransactionType.INTEREST
            ]:
                # Inflow
                position.available_balance += transaction.amount
                self.cash_metrics['total_inflows'] += transaction.amount
                
            elif transaction.transaction_type in [
                CashTransactionType.WITHDRAWAL,
                CashTransactionType.FEE
            ]:
                # Outflow
                if position.available_balance >= transaction.amount:
                    position.available_balance -= transaction.amount
                    self.cash_metrics['total_outflows'] += transaction.amount
                else:
                    self.logger.error(f"Insufficient cash for transaction {transaction.transaction_id}")
                    return False
                
            elif transaction.transaction_type == CashTransactionType.TRADE_SETTLEMENT:
                # Trade settlement - could be inflow or outflow
                if transaction.amount > 0:
                    # Sale proceeds
                    position.available_balance += transaction.amount
                    self.cash_metrics['total_inflows'] += transaction.amount
                else:
                    # Purchase payment
                    if position.reserved_balance >= abs(transaction.amount):
                        position.reserved_balance -= abs(transaction.amount)
                    else:
                        self.logger.warning(f"Trade settlement amount {transaction.amount} "
                                          f"exceeds reserved cash {position.reserved_balance}")
                        if position.available_balance >= abs(transaction.amount):
                            position.available_balance -= abs(transaction.amount)
                        else:
                            return False
                    
                    self.cash_metrics['total_outflows'] += abs(transaction.amount)
            
            # Update position timestamp
            position.last_updated = datetime.now(timezone.utc)
            
            # Record transaction
            self.transaction_history.append(transaction)
            self._update_daily_flows(transaction)
            self._update_metrics()
            
            self.logger.debug(f"Processed transaction {transaction.transaction_id}: "
                            f"{transaction.amount} {currency}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing transaction {transaction.transaction_id}: {e}")
            return False
    
    def transfer_cash(self, amount: Decimal, from_currency: str, to_currency: str,
                     exchange_rate: Decimal = None) -> bool:
        """Transfer cash between currencies"""
        try:
            if from_currency == to_currency:
                return True
            
            # Get exchange rate
            if exchange_rate is None:
                exchange_rate = self.get_exchange_rate(from_currency, to_currency)
                if exchange_rate is None:
                    self.logger.error(f"No exchange rate available for {from_currency} to {to_currency}")
                    return False
            
            # Check available balance
            if from_currency not in self.cash_positions:
                return False
            
            if self.cash_positions[from_currency].available_balance < amount:
                return False
            
            # Calculate conversion
            conversion_cost = amount * Decimal('0.001')  # 0.1% conversion cost
            net_amount = amount - conversion_cost
            converted_amount = net_amount * exchange_rate
            
            # Process transactions
            # Debit from currency
            from_transaction = CashTransaction(
                transaction_id=f"fx_{datetime.now().timestamp()}_from",
                transaction_type=CashTransactionType.CURRENCY_CONVERSION,
                amount=-amount,
                currency=from_currency,
                description=f"Currency conversion to {to_currency}"
            )
            
            # Credit to currency
            to_transaction = CashTransaction(
                transaction_id=f"fx_{datetime.now().timestamp()}_to",
                transaction_type=CashTransactionType.CURRENCY_CONVERSION,
                amount=converted_amount,
                currency=to_currency,
                description=f"Currency conversion from {from_currency}"
            )
            
            # Process both transactions
            if (self.process_cash_transaction(from_transaction) and
                self.process_cash_transaction(to_transaction)):
                
                self.cash_metrics['currency_conversion_costs'] += conversion_cost
                
                self.logger.info(f"Converted {amount} {from_currency} to "
                               f"{converted_amount} {to_currency} at rate {exchange_rate}")
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error transferring cash: {e}")
            return False
    
    def set_margin_requirement(self, strategy_id: str, requirement: Decimal):
        """Set margin requirement for strategy"""
        self.margin_requirements[strategy_id] = requirement
        
        # Update cash position margin requirements
        total_margin = sum(self.margin_requirements.values())
        if self.base_currency in self.cash_positions:
            self.cash_positions[self.base_currency].margin_requirement = total_margin
        
        self.logger.info(f"Set margin requirement for {strategy_id}: {requirement}")
    
    def calculate_cash_forecast(self, days_ahead: int = 30) -> List[CashForecast]:
        """Calculate cash flow forecast"""
        try:
            forecasts = []
            current_balance = self.get_cash_balance(self.base_currency)
            
            # Calculate average daily flows
            recent_flows = list(self.daily_cash_flows.values())[-30:]  # Last 30 days
            avg_daily_flow = sum(recent_flows) / len(recent_flows) if recent_flows else Decimal('0')
            
            # Generate forecasts
            for days in range(1, days_ahead + 1):
                forecast_date = datetime.now(timezone.utc) + timedelta(days=days)
                
                # Simple forecast based on historical average
                projected_inflows = max(avg_daily_flow, Decimal('0')) * Decimal('1.1')  # 10% buffer
                projected_outflows = abs(min(avg_daily_flow, Decimal('0'))) * Decimal('1.1')
                
                net_flow = projected_inflows - projected_outflows
                projected_balance = current_balance + (net_flow * days)
                
                # Confidence decreases with time
                confidence = max(Decimal('0.1'), Decimal('0.9') - (Decimal(str(days)) / Decimal('100')))
                
                forecast = CashForecast(
                    date=forecast_date,
                    projected_inflows=projected_inflows,
                    projected_outflows=projected_outflows,
                    net_flow=net_flow,
                    projected_balance=projected_balance,
                    confidence_level=confidence
                )
                
                forecasts.append(forecast)
            
            self.cash_forecasts = forecasts
            return forecasts
            
        except Exception as e:
            self.logger.error(f"Error calculating cash forecast: {e}")
            return []
    
    def optimize_cash_allocation(self) -> Dict[str, Any]:
        """Optimize cash allocation across currencies and uses"""
        try:
            total_cash = sum(pos.total_balance for pos in self.cash_positions.values())
            
            optimization_result = {
                'current_allocation': {},
                'recommended_allocation': {},
                'actions': []
            }
            
            # Current allocation
            for currency, position in self.cash_positions.items():
                optimization_result['current_allocation'][currency] = {
                    'balance': float(position.total_balance),
                    'percentage': float((position.total_balance / total_cash) * 100) if total_cash > 0 else 0
                }
            
            # Simple optimization: maintain target cash ratio
            target_cash_amount = total_cash * self.target_cash_ratio
            current_available = sum(pos.available_balance for pos in self.cash_positions.values())
            
            if current_available < target_cash_amount:
                optimization_result['actions'].append({
                    'action': 'increase_cash',
                    'amount': float(target_cash_amount - current_available),
                    'reason': 'Below target cash ratio'
                })
            elif current_available > total_cash * self.max_cash_ratio:
                optimization_result['actions'].append({
                    'action': 'invest_excess_cash',
                    'amount': float(current_available - target_cash_amount),
                    'reason': 'Excess cash above maximum ratio'
                })
            
            return optimization_result
            
        except Exception as e:
            self.logger.error(f"Error optimizing cash allocation: {e}")
            return {}
    
    def get_exchange_rate(self, from_currency: str, to_currency: str) -> Optional[Decimal]:
        """Get exchange rate between currencies"""
        if from_currency == to_currency:
            return Decimal('1')
        
        # Direct rate
        if (from_currency, to_currency) in self.exchange_rates:
            return self.exchange_rates[(from_currency, to_currency)]
        
        # Inverse rate
        if (to_currency, from_currency) in self.exchange_rates:
            inverse_rate = self.exchange_rates[(to_currency, from_currency)]
            return Decimal('1') / inverse_rate if inverse_rate != 0 else None
        
        # Default rate (should be updated with real market data)
        return Decimal('1')
    
    def update_exchange_rates(self, rates: Dict[Tuple[str, str], Decimal]):
        """Update exchange rates"""
        self.exchange_rates.update(rates)
        self.logger.debug(f"Updated {len(rates)} exchange rates")
    
    def calculate_interest(self) -> Decimal:
        """Calculate and apply interest on cash balances"""
        total_interest = Decimal('0')
        
        for currency, position in self.cash_positions.items():
            interest_rate = self.interest_rates.get(currency, Decimal('0'))
            
            if interest_rate > 0 and position.available_balance > 0:
                # Daily interest calculation
                daily_rate = interest_rate / Decimal('365')
                interest_amount = position.available_balance * daily_rate
                
                # Apply interest
                interest_transaction = CashTransaction(
                    transaction_id=f"interest_{currency}_{datetime.now().timestamp()}",
                    transaction_type=CashTransactionType.INTEREST,
                    amount=interest_amount,
                    currency=currency,
                    description="Daily interest"
                )
                
                if self.process_cash_transaction(interest_transaction):
                    total_interest += interest_amount
                    self.cash_metrics['interest_earned'] += interest_amount
        
        return total_interest
    
    def _initialize_cash_position(self, currency: str, initial_amount: Decimal):
        """Initialize cash position for currency"""
        self.cash_positions[currency] = CashPosition(
            currency=currency,
            available_balance=initial_amount,
            reserved_balance=Decimal('0'),
            pending_settlements=Decimal('0'),
            margin_requirement=Decimal('0')
        )
    
    def _record_transaction(self, transaction_type: CashTransactionType, amount: Decimal,
                           currency: str, description: str, reference_id: str = None):
        """Record a cash transaction"""
        transaction = CashTransaction(
            transaction_id=f"cash_{datetime.now().timestamp()}",
            transaction_type=transaction_type,
            amount=amount,
            currency=currency,
            description=description,
            reference_id=reference_id
        )
        
        self.transaction_history.append(transaction)
        self._update_daily_flows(transaction)
    
    def _update_daily_flows(self, transaction: CashTransaction):
        """Update daily cash flow tracking"""
        date_key = transaction.timestamp.date().isoformat()
        
        if date_key not in self.daily_cash_flows:
            self.daily_cash_flows[date_key] = Decimal('0')
        
        self.daily_cash_flows[date_key] += transaction.amount
    
    def _update_metrics(self):
        """Update cash management metrics"""
        self.cash_metrics['total_transactions'] = len(self.transaction_history)
        
        # Calculate average daily flow
        if self.daily_cash_flows:
            flows = list(self.daily_cash_flows.values())
            self.cash_metrics['average_daily_flow'] = sum(flows) / len(flows)
        
        # Calculate cash utilization
        total_cash = sum(pos.total_balance for pos in self.cash_positions.values())
        available_cash = sum(pos.available_balance for pos in self.cash_positions.values())
        
        if total_cash > 0:
            self.cash_metrics['cash_utilization'] = ((total_cash - available_cash) / total_cash) * 100
    
    def get_cash_summary(self) -> Dict[str, Any]:
        """Get comprehensive cash summary"""
        total_cash = sum(pos.total_balance for pos in self.cash_positions.values())
        available_cash = sum(pos.available_balance for pos in self.cash_positions.values())
        reserved_cash = sum(pos.reserved_balance for pos in self.cash_positions.values())
        
        return {
            'total_cash': float(total_cash),
            'available_cash': float(available_cash),
            'reserved_cash': float(reserved_cash),
            'cash_by_currency': {
                currency: {
                    'available': float(pos.available_balance),
                    'reserved': float(pos.reserved_balance),
                    'total': float(pos.total_balance),
                    'usable': float(pos.usable_balance)
                }
                for currency, pos in self.cash_positions.items()
            },
            'margin_requirements': {k: float(v) for k, v in self.margin_requirements.items()},
            'metrics': self.cash_metrics.copy(),
            'recent_transactions': [
                {
                    'id': tx.transaction_id,
                    'type': tx.transaction_type.value,
                    'amount': float(tx.amount),
                    'currency': tx.currency,
                    'description': tx.description,
                    'timestamp': tx.timestamp.isoformat()
                }
                for tx in self.transaction_history[-10:]  # Last 10 transactions
            ]
        }
    
    def cleanup(self):
        """Cleanup cash manager"""
        # Save transaction history if needed
        total_cash = sum(pos.total_balance for pos in self.cash_positions.values())
        
        self.logger.info(f"Cash manager cleaned up. Total cash: {total_cash} "
                        f"across {len(self.cash_positions)} currencies")