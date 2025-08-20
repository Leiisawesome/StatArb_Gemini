#!/usr/bin/env python3
"""
Real Data Integration for Multi-Strategy Backtesting
===================================================

Production-grade data integration with:
- ClickHouse data streaming
- Real-time data synchronization
- Data quality validation
- Performance optimization

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, AsyncGenerator
import pandas as pd
import numpy as np
from dataclasses import dataclass

# Core system imports
from core_structure.market_data.enhanced_clickhouse_loader import EnhancedClickHouseLoader
from core_structure.market_data.data_quality_monitor import DataQualityMonitor

logger = logging.getLogger(__name__)

@dataclass
class DataStreamConfig:
    """Configuration for real data streaming"""
    symbols: List[str]
    start_date: datetime
    end_date: datetime
    frequency: str = '5min'
    batch_size: int = 1000
    quality_checks: bool = True
    cache_enabled: bool = True

class RealDataStreamManager:
    """
    Real data stream manager for multi-strategy execution
    """
    
    def __init__(self, config: DataStreamConfig):
        self.config = config
        self.clickhouse_loader = None
        self.quality_monitor = None
        self.data_cache = {}
        self.is_initialized = False
        
    async def initialize(self) -> None:
        """Initialize real data streaming components"""
        logger.info("🔌 Initializing real data stream manager...")
        
        try:
            # Initialize ClickHouse loader
            self.clickhouse_loader = EnhancedClickHouseLoader()
            await self.clickhouse_loader.initialize()
            
            # Initialize data quality monitor if enabled
            if self.config.quality_checks:
                self.quality_monitor = DataQualityMonitor()
                await self.quality_monitor.initialize()
            
            self.is_initialized = True
            logger.info("✅ Real data stream manager initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize real data stream manager: {e}")
            raise
    
    async def stream_data(self) -> AsyncGenerator[Dict[datetime, Dict[str, Any]], None]:
        """Stream real market data for multi-strategy consumption"""
        if not self.is_initialized:
            await self.initialize()
        
        logger.info(f"📊 Starting real data stream: {len(self.config.symbols)} symbols, {self.config.start_date} → {self.config.end_date}")
        
        try:
            # Stream data in batches for memory efficiency
            current_date = self.config.start_date
            batch_count = 0
            
            while current_date <= self.config.end_date:
                # Calculate batch end date
                batch_end = min(
                    current_date + timedelta(days=1),  # 1-day batches
                    self.config.end_date
                )
                
                # Load batch from ClickHouse
                batch_data = await self._load_data_batch(current_date, batch_end)
                
                if batch_data:
                    # Quality validation if enabled
                    if self.config.quality_checks:
                        batch_data = await self._validate_data_quality(batch_data)
                    
                    # Yield synchronized data points
                    for timestamp, market_data in batch_data.items():
                        yield {timestamp: market_data}
                    
                    batch_count += 1
                    logger.debug(f"📊 Streamed batch {batch_count}: {len(batch_data)} data points")
                
                current_date = batch_end
            
            logger.info(f"✅ Real data streaming completed: {batch_count} batches processed")
            
        except Exception as e:
            logger.error(f"Error in real data streaming: {e}")
            raise
    
    async def _load_data_batch(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[datetime, Dict[str, Any]]:
        """Load a batch of data from ClickHouse"""
        try:
            batch_data = {}
            
            for symbol in self.config.symbols:
                # Load data for this symbol and date range
                symbol_data = await self.clickhouse_loader.load_data(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    frequency=self.config.frequency
                )
                
                # Convert to timestamp-indexed format
                for _, row in symbol_data.iterrows():
                    timestamp = row['timestamp']
                    
                    if timestamp not in batch_data:
                        batch_data[timestamp] = {}
                    
                    batch_data[timestamp][symbol] = {
                        'symbol': symbol,
                        'timestamp': timestamp,
                        'open': row['open'],
                        'high': row['high'],
                        'low': row['low'],
                        'close': row['close'],
                        'volume': row['volume']
                    }
            
            return batch_data
            
        except Exception as e:
            logger.error(f"Error loading data batch: {e}")
            return {}
    
    async def _validate_data_quality(
        self, 
        batch_data: Dict[datetime, Dict[str, Any]]
    ) -> Dict[datetime, Dict[str, Any]]:
        """Validate data quality and filter bad data points"""
        if not self.quality_monitor:
            return batch_data
        
        try:
            validated_data = {}
            
            for timestamp, market_data in batch_data.items():
                # Validate each data point
                is_valid = await self.quality_monitor.validate_data_point(market_data)
                
                if is_valid:
                    validated_data[timestamp] = market_data
                else:
                    logger.warning(f"⚠️ Invalid data point filtered: {timestamp}")
            
            logger.debug(f"✅ Data quality validation: {len(validated_data)}/{len(batch_data)} points valid")
            return validated_data
            
        except Exception as e:
            logger.error(f"Error in data quality validation: {e}")
            return batch_data

class MultiStrategySignalAggregator:
    """
    Aggregates and coordinates signals from multiple strategies
    """
    
    def __init__(self):
        self.signal_history = {}
        self.conflict_resolution_rules = {
            'same_symbol_opposite_signals': 'strongest_wins',
            'position_size_conflicts': 'proportional_allocation',
            'timing_conflicts': 'first_signal_priority'
        }
    
    async def aggregate_signals(
        self, 
        timestamp: datetime, 
        strategy_signals: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Aggregate signals from multiple strategies"""
        try:
            aggregated = {
                'timestamp': timestamp,
                'total_signals': 0,
                'buy_signals': [],
                'sell_signals': [],
                'conflicts_resolved': 0,
                'final_signals': []
            }
            
            # Collect all signals
            all_signals = []
            for strategy_id, signals in strategy_signals.items():
                for signal in signals:
                    # Handle both TradingSignal objects and dictionaries
                    if hasattr(signal, 'metadata'):
                        # TradingSignal object - add strategy_id to metadata
                        if signal.metadata is None:
                            signal.metadata = {}
                        signal.metadata['strategy_id'] = strategy_id
                        all_signals.append(signal)
                    else:
                        # Dictionary signal - add strategy_id directly
                        signal['strategy_id'] = strategy_id
                        all_signals.append(signal)
                    aggregated['total_signals'] += 1
            
            # Separate by signal type
            for signal in all_signals:
                # Handle both TradingSignal objects and dictionaries
                if hasattr(signal, 'signal_type'):
                    # TradingSignal object
                    signal_type = str(signal.signal_type)
                    if 'LONG' in signal_type or 'BUY' in signal_type:
                        aggregated['buy_signals'].append(signal)
                    elif 'SHORT' in signal_type or 'SELL' in signal_type:
                        aggregated['sell_signals'].append(signal)
                else:
                    # Dictionary signal
                    if signal.get('signal_type') == 'BUY':
                        aggregated['buy_signals'].append(signal)
                    elif signal.get('signal_type') == 'SELL':
                        aggregated['sell_signals'].append(signal)
            
            # Resolve conflicts
            final_signals = await self._resolve_signal_conflicts(all_signals)
            aggregated['final_signals'] = final_signals
            aggregated['conflicts_resolved'] = len(all_signals) - len(final_signals)
            
            # Store in history
            self.signal_history[timestamp] = aggregated
            
            return aggregated
            
        except Exception as e:
            logger.error(f"Error aggregating signals: {e}")
            return {'timestamp': timestamp, 'error': str(e)}
    
    async def _resolve_signal_conflicts(
        self, 
        signals: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Resolve conflicts between strategy signals"""
        try:
            # Group signals by symbol
            symbol_signals = {}
            for signal in signals:
                # Handle both TradingSignal objects and dictionaries
                if hasattr(signal, 'symbol_pair'):
                    # TradingSignal object
                    symbol = signal.symbol_pair
                else:
                    # Dictionary signal
                    symbol = signal.get('symbol')
                
                if symbol not in symbol_signals:
                    symbol_signals[symbol] = []
                symbol_signals[symbol].append(signal)
            
            resolved_signals = []
            
            for symbol, symbol_signal_list in symbol_signals.items():
                if len(symbol_signal_list) == 1:
                    # No conflict
                    resolved_signals.extend(symbol_signal_list)
                else:
                    # Resolve conflicts for this symbol
                    resolved = await self._resolve_symbol_conflicts(symbol, symbol_signal_list)
                    resolved_signals.extend(resolved)
            
            return resolved_signals
            
        except Exception as e:
            logger.error(f"Error resolving signal conflicts: {e}")
            return signals
    
    async def _resolve_symbol_conflicts(
        self, 
        symbol: str, 
        signals: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Resolve conflicts for a specific symbol"""
        try:
            # Helper function to get signal type
            def get_signal_type(signal):
                if hasattr(signal, 'signal_type'):
                    return str(signal.signal_type)
                else:
                    return signal.get('signal_type', '')
            
            # Helper function to get signal strength
            def get_signal_strength(signal):
                if hasattr(signal, 'strength'):
                    # Convert SignalStrength enum to float if needed
                    strength = signal.strength
                    if hasattr(strength, 'value'):
                        return float(strength.value)
                    else:
                        return float(strength)
                else:
                    return signal.get('strength', 0)
            
            # Check for opposite signals (BUY vs SELL)
            buy_signals = []
            sell_signals = []
            
            for s in signals:
                signal_type = get_signal_type(s)
                if 'BUY' in signal_type or 'LONG' in signal_type:
                    buy_signals.append(s)
                elif 'SELL' in signal_type or 'SHORT' in signal_type:
                    sell_signals.append(s)
            
            if buy_signals and sell_signals:
                # Opposite signals - PREVENT CHURNING by skipping conflicting signals
                logger.info(f"🚫 CONFLICT DETECTED: {symbol} has both BUY ({len(buy_signals)}) and SELL ({len(sell_signals)}) signals - SKIPPING ALL to prevent churning")
                return []  # Skip all conflicting signals to prevent churning
            
            elif len(buy_signals) > 1:
                # Multiple BUY signals - combine or select strongest
                return [max(buy_signals, key=get_signal_strength)]
            
            elif len(sell_signals) > 1:
                # Multiple SELL signals - combine or select strongest
                return [max(sell_signals, key=get_signal_strength)]
            
            else:
                # No conflicts
                return signals
                
        except Exception as e:
            logger.error(f"Error resolving conflicts for {symbol}: {e}")
            return signals

class CoordinatedPortfolioManager:
    """
    Coordinates portfolio management across multiple strategies
    """
    
    def __init__(self, initial_capital: float, strategy_allocations: Dict[str, float]):
        self.initial_capital = initial_capital
        self.strategy_allocations = strategy_allocations
        self.strategy_portfolios = {}
        self.consolidated_portfolio = {
            'cash': initial_capital,
            'positions': {},
            'total_value': initial_capital,
            'unrealized_pnl': 0,
            'realized_pnl': 0
        }
        
        # Initialize strategy-specific portfolios
        for strategy_id, allocation in strategy_allocations.items():
            allocated_capital = initial_capital * allocation
            self.strategy_portfolios[strategy_id] = {
                'allocated_capital': allocated_capital,
                'available_cash': allocated_capital,
                'positions': {},
                'unrealized_pnl': 0,
                'realized_pnl': 0
            }
    
    async def execute_coordinated_trades(
        self, 
        timestamp: datetime, 
        aggregated_signals: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute trades in a coordinated manner across strategies"""
        try:
            execution_results = {
                'timestamp': timestamp,
                'trades_executed': 0,
                'total_trade_value': 0,
                'strategy_executions': {},
                'portfolio_updates': {}
            }
            
            final_signals = aggregated_signals.get('final_signals', [])
            
            for signal in final_signals:
                # Handle both TradingSignal objects and dictionaries
                if hasattr(signal, 'metadata'):
                    # TradingSignal object
                    strategy_id = signal.metadata.get('strategy_id') if signal.metadata else None
                    symbol = signal.symbol_pair
                    signal_type = str(signal.signal_type)
                    strength = signal.strength
                else:
                    # Dictionary signal
                    strategy_id = signal.get('strategy_id')
                    symbol = signal.get('symbol')
                    signal_type = signal.get('signal_type')
                    strength = signal.get('strength', 0)
                
                # Calculate position size based on strategy allocation
                position_size = await self._calculate_position_size(
                    strategy_id, symbol, signal_type, strength
                )
                
                if position_size > 0:
                    # Execute trade
                    trade_result = await self._execute_trade(
                        strategy_id, symbol, signal_type, position_size, timestamp
                    )
                    
                    if trade_result['success']:
                        execution_results['trades_executed'] += 1
                        execution_results['total_trade_value'] += trade_result['trade_value']
                        
                        if strategy_id not in execution_results['strategy_executions']:
                            execution_results['strategy_executions'][strategy_id] = []
                        execution_results['strategy_executions'][strategy_id].append(trade_result)
            
            # Update consolidated portfolio
            await self._update_consolidated_portfolio(timestamp)
            execution_results['portfolio_updates'] = self.consolidated_portfolio.copy()
            
            return execution_results
            
        except Exception as e:
            logger.error(f"Error executing coordinated trades: {e}")
            return {'timestamp': timestamp, 'error': str(e)}
    
    async def _calculate_position_size(
        self, 
        strategy_id: str, 
        symbol: str, 
        signal_type: str, 
        strength: float
    ) -> float:
        """Calculate position size for a trade"""
        try:
            strategy_portfolio = self.strategy_portfolios.get(strategy_id)
            if not strategy_portfolio:
                return 0
            
            available_cash = strategy_portfolio['available_cash']
            
            # Base position size on signal strength and available capital
            # Convert SignalStrength enum to float if needed
            if hasattr(strength, 'value'):
                strength_value = float(strength.value)
            else:
                strength_value = float(strength)
            
            base_position_value = available_cash * 0.1 * strength_value  # 10% max per signal
            
            # Mock price for calculation (in production, use real market price)
            mock_price = 100.0
            position_size = base_position_value / mock_price
            
            return max(0, position_size)
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0
    
    async def _execute_trade(
        self, 
        strategy_id: str, 
        symbol: str, 
        signal_type: str, 
        position_size: float, 
        timestamp: datetime
    ) -> Dict[str, Any]:
        """Execute a single trade"""
        try:
            # Mock execution (in production, this would interface with real execution engine)
            mock_price = 100.0 + np.random.randn() * 2  # Mock price with some variance
            trade_value = position_size * mock_price
            
            # Update strategy portfolio
            strategy_portfolio = self.strategy_portfolios[strategy_id]
            
            if signal_type == 'BUY':
                if symbol not in strategy_portfolio['positions']:
                    strategy_portfolio['positions'][symbol] = {'quantity': 0, 'avg_price': 0}
                
                # Update position
                current_qty = strategy_portfolio['positions'][symbol]['quantity']
                current_avg = strategy_portfolio['positions'][symbol]['avg_price']
                
                new_qty = current_qty + position_size
                new_avg = ((current_qty * current_avg) + (position_size * mock_price)) / new_qty
                
                strategy_portfolio['positions'][symbol]['quantity'] = new_qty
                strategy_portfolio['positions'][symbol]['avg_price'] = new_avg
                strategy_portfolio['available_cash'] -= trade_value
                
            elif signal_type == 'SELL':
                if symbol in strategy_portfolio['positions']:
                    current_qty = strategy_portfolio['positions'][symbol]['quantity']
                    sell_qty = min(position_size, current_qty)
                    
                    if sell_qty > 0:
                        strategy_portfolio['positions'][symbol]['quantity'] -= sell_qty
                        strategy_portfolio['available_cash'] += sell_qty * mock_price
                        
                        # Calculate realized P&L
                        avg_price = strategy_portfolio['positions'][symbol]['avg_price']
                        realized_pnl = sell_qty * (mock_price - avg_price)
                        strategy_portfolio['realized_pnl'] += realized_pnl
            
            return {
                'success': True,
                'strategy_id': strategy_id,
                'symbol': symbol,
                'signal_type': signal_type,
                'position_size': position_size,
                'execution_price': mock_price,
                'trade_value': trade_value,
                'timestamp': timestamp
            }
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _update_consolidated_portfolio(self, timestamp: datetime) -> None:
        """Update consolidated portfolio from all strategy portfolios"""
        try:
            # Reset consolidated positions
            self.consolidated_portfolio['positions'] = {}
            total_cash = 0
            total_unrealized_pnl = 0
            total_realized_pnl = 0
            
            # Aggregate from all strategy portfolios
            for strategy_id, portfolio in self.strategy_portfolios.items():
                total_cash += portfolio['available_cash']
                total_realized_pnl += portfolio['realized_pnl']
                
                # Aggregate positions
                for symbol, position in portfolio['positions'].items():
                    if symbol not in self.consolidated_portfolio['positions']:
                        self.consolidated_portfolio['positions'][symbol] = {
                            'quantity': 0,
                            'total_cost': 0
                        }
                    
                    self.consolidated_portfolio['positions'][symbol]['quantity'] += position['quantity']
                    self.consolidated_portfolio['positions'][symbol]['total_cost'] += (
                        position['quantity'] * position['avg_price']
                    )
            
            # Calculate consolidated metrics
            self.consolidated_portfolio['cash'] = total_cash
            self.consolidated_portfolio['realized_pnl'] = total_realized_pnl
            self.consolidated_portfolio['unrealized_pnl'] = total_unrealized_pnl
            
            # Calculate total portfolio value (simplified)
            position_value = sum(
                pos['quantity'] * 100  # Mock current price
                for pos in self.consolidated_portfolio['positions'].values()
            )
            
            self.consolidated_portfolio['total_value'] = total_cash + position_value
            
        except Exception as e:
            logger.error(f"Error updating consolidated portfolio: {e}")
