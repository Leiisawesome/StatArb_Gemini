#!/usr/bin/env python3
"""
Trading Data Collector
======================

Real-time data collection system for the trading dashboard.
Collects performance metrics, positions, orders, and risk data from the trading engine.

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
import json
import threading
from collections import deque

logger = logging.getLogger(__name__)

@dataclass
class TradingSnapshot:
    """Real-time trading data snapshot"""
    timestamp: datetime
    portfolio_value: float
    total_pnl: float
    daily_pnl: float
    positions: Dict[str, Any]
    orders: Dict[str, Any]
    risk_metrics: Dict[str, float]
    strategy_performance: Dict[str, Dict[str, Any]]
    
@dataclass
class PerformanceMetrics:
    """Real-time performance metrics"""
    total_return: float = 0.0
    daily_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    volatility: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0

class TradingDataCollector:
    """
    Real-time trading data collector
    
    Collects and aggregates trading data from multiple sources:
    - Trading engine performance
    - Position and order data
    - Risk metrics
    - Strategy-specific analytics
    """
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        
        # Data storage
        self.snapshots: deque = deque(maxlen=max_history)
        self.current_snapshot: Optional[TradingSnapshot] = None
        
        # Performance tracking
        self.performance_metrics = PerformanceMetrics()
        self.initial_capital = 100000.0
        self.peak_value = 100000.0
        
        # Data sources
        self.trading_engine = None
        self.risk_manager = None
        
        # Real-time updates
        self.update_callbacks: List[Callable] = []
        self.is_collecting = False
        self.collection_interval = 1.0  # seconds
        
        # Threading
        self.collection_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        logger.info("📊 Trading Data Collector initialized")
    
    def register_trading_engine(self, engine):
        """Register trading engine as data source"""
        self.trading_engine = engine
        self.risk_manager = getattr(engine, 'risk_manager', None)
        self.initial_capital = getattr(engine, 'initial_capital', 100000.0)
        self.peak_value = self.initial_capital
        logger.info("🔗 Trading engine registered with data collector")
    
    def add_update_callback(self, callback: Callable):
        """Add callback for real-time updates"""
        self.update_callbacks.append(callback)
        logger.info(f"📡 Update callback registered: {callback.__name__}")
    
    def start_collection(self):
        """Start real-time data collection"""
        if self.is_collecting:
            logger.warning("⚠️  Data collection already running")
            return
        
        self.is_collecting = True
        self.stop_event.clear()
        
        self.collection_thread = threading.Thread(
            target=self._collection_loop,
            daemon=True
        )
        self.collection_thread.start()
        
        logger.info("🚀 Real-time data collection started")
    
    def stop_collection(self):
        """Stop real-time data collection"""
        if not self.is_collecting:
            return
        
        self.is_collecting = False
        self.stop_event.set()
        
        if self.collection_thread:
            self.collection_thread.join(timeout=5.0)
        
        logger.info("🛑 Real-time data collection stopped")
    
    def _collection_loop(self):
        """Main data collection loop"""
        while not self.stop_event.is_set():
            try:
                # Collect current snapshot
                snapshot = self._collect_snapshot()
                if snapshot:
                    self.current_snapshot = snapshot
                    self.snapshots.append(snapshot)
                    
                    # Update performance metrics
                    self._update_performance_metrics(snapshot)
                    
                    # Notify callbacks
                    self._notify_callbacks(snapshot)
                
                # Wait for next collection
                self.stop_event.wait(self.collection_interval)
                
            except Exception as e:
                logger.error(f"❌ Error in data collection loop: {e}")
                self.stop_event.wait(1.0)  # Brief pause on error
    
    def _collect_snapshot(self) -> Optional[TradingSnapshot]:
        """Collect current trading data snapshot"""
        if not self.trading_engine:
            return None
        
        try:
            # Get current timestamp
            timestamp = datetime.now()
            
            # Collect portfolio data
            portfolio_value = getattr(self.trading_engine, 'portfolio_value', self.initial_capital)
            total_pnl = portfolio_value - self.initial_capital
            
            # Calculate daily P&L (simplified - would need session start tracking)
            daily_pnl = total_pnl  # For now, same as total
            
            # Collect positions
            positions = self._collect_positions()
            
            # Collect orders
            orders = self._collect_orders()
            
            # Collect risk metrics
            risk_metrics = self._collect_risk_metrics()
            
            # Collect strategy performance
            strategy_performance = self._collect_strategy_performance()
            
            return TradingSnapshot(
                timestamp=timestamp,
                portfolio_value=portfolio_value,
                total_pnl=total_pnl,
                daily_pnl=daily_pnl,
                positions=positions,
                orders=orders,
                risk_metrics=risk_metrics,
                strategy_performance=strategy_performance
            )
            
        except Exception as e:
            logger.error(f"❌ Error collecting snapshot: {e}")
            return None
    
    def _collect_positions(self) -> Dict[str, Any]:
        """Collect current positions data"""
        positions = {}
        
        if hasattr(self.trading_engine, 'positions'):
            engine_positions = self.trading_engine.positions
            
            for strategy_id, strategy_positions in engine_positions.items():
                for pos_id, position in strategy_positions.items():
                    positions[pos_id] = {
                        'strategy_id': strategy_id,
                        'symbol': position.get('symbol', ''),
                        'quantity': position.get('quantity', 0),
                        'entry_price': position.get('entry_price', 0),
                        'current_price': self._get_current_price(position.get('symbol', '')),
                        'pnl': self._calculate_position_pnl(position),
                        'entry_time': position.get('entry_time', datetime.now()).isoformat(),
                        'side': position.get('side', 'LONG')
                    }
        
        return positions
    
    def _collect_orders(self) -> Dict[str, Any]:
        """Collect current orders data"""
        orders = {}
        
        # This would integrate with the order manager
        if hasattr(self.trading_engine, 'order_manager'):
            order_manager = self.trading_engine.order_manager
            if hasattr(order_manager, 'orders'):
                for order_id, order in order_manager.orders.items():
                    orders[order_id] = {
                        'symbol': order.symbol,
                        'quantity': order.quantity,
                        'side': order.side.value,
                        'type': order.order_type.value,
                        'status': order.status.value,
                        'created_time': order.created_time.isoformat(),
                        'strategy_id': order.strategy_id
                    }
        
        return orders
    
    def _collect_risk_metrics(self) -> Dict[str, float]:
        """Collect current risk metrics"""
        risk_metrics = {}
        
        if self.risk_manager:
            try:
                # Get risk summary from unified risk manager
                risk_summary = self.risk_manager.get_risk_summary()
                
                if "portfolio_metrics" in risk_summary:
                    metrics = risk_summary["portfolio_metrics"]
                    risk_metrics.update({
                        'current_drawdown': metrics.get('current_drawdown', 0.0),
                        'max_drawdown': metrics.get('max_drawdown', 0.0),
                        'volatility': metrics.get('volatility', 0.0),
                        'sharpe_ratio': metrics.get('sharpe_ratio', 0.0),
                        'var_95': metrics.get('var_95', 0.0)
                    })
                
                # Add risk limits
                if hasattr(self.risk_manager, 'risk_limits'):
                    limits = self.risk_manager.risk_limits
                    risk_metrics.update({
                        'max_portfolio_drawdown_limit': limits.max_portfolio_drawdown,
                        'max_position_size_limit': limits.max_position_size_pct,
                        'target_volatility': limits.target_portfolio_volatility
                    })
                
            except Exception as e:
                logger.error(f"❌ Error collecting risk metrics: {e}")
        
        return risk_metrics
    
    def _collect_strategy_performance(self) -> Dict[str, Dict[str, Any]]:
        """Collect strategy-specific performance data"""
        strategy_performance = {}
        
        if hasattr(self.trading_engine, 'strategies'):
            strategies = self.trading_engine.strategies
            
            for strategy_id, config in strategies.items():
                # Calculate strategy-specific metrics
                strategy_positions = self.trading_engine.positions.get(strategy_id, {})
                strategy_pnl = sum(
                    self._calculate_position_pnl(pos) 
                    for pos in strategy_positions.values()
                )
                
                base_allocation = config.get('base_allocation', 0.0)
                allocated_capital = self.initial_capital * base_allocation
                
                strategy_performance[strategy_id] = {
                    'name': config.get('name', strategy_id),
                    'allocation': base_allocation,
                    'allocated_capital': allocated_capital,
                    'current_pnl': strategy_pnl,
                    'return_pct': (strategy_pnl / allocated_capital) if allocated_capital > 0 else 0.0,
                    'positions_count': len(strategy_positions),
                    'symbols': config.get('symbols', [])
                }
        
        return strategy_performance
    
    def _get_current_price(self, symbol: str) -> float:
        """Get current price for symbol"""
        if hasattr(self.trading_engine, 'prices'):
            return self.trading_engine.prices.get(symbol, 0.0)
        return 0.0
    
    def _calculate_position_pnl(self, position: Dict[str, Any]) -> float:
        """Calculate P&L for a position"""
        try:
            symbol = position.get('symbol', '')
            quantity = position.get('quantity', 0)
            entry_price = position.get('entry_price', 0)
            side = position.get('side', 'LONG')
            
            current_price = self._get_current_price(symbol)
            
            if side == 'LONG':
                return (current_price - entry_price) * quantity
            else:
                return (entry_price - current_price) * quantity
                
        except Exception as e:
            logger.error(f"❌ Error calculating position P&L: {e}")
            return 0.0
    
    def _update_performance_metrics(self, snapshot: TradingSnapshot):
        """Update performance metrics based on snapshot"""
        try:
            # Update basic metrics
            self.performance_metrics.total_return = (snapshot.portfolio_value / self.initial_capital - 1) * 100
            self.performance_metrics.daily_return = (snapshot.daily_pnl / self.initial_capital) * 100
            
            # Update peak value and drawdown
            if snapshot.portfolio_value > self.peak_value:
                self.peak_value = snapshot.portfolio_value
            
            current_drawdown = (self.peak_value - snapshot.portfolio_value) / self.peak_value
            self.performance_metrics.current_drawdown = current_drawdown * 100
            
            # Update max drawdown
            if current_drawdown > self.performance_metrics.max_drawdown / 100:
                self.performance_metrics.max_drawdown = current_drawdown * 100
            
            # Update from risk metrics if available
            if 'sharpe_ratio' in snapshot.risk_metrics:
                self.performance_metrics.sharpe_ratio = snapshot.risk_metrics['sharpe_ratio']
            
            if 'volatility' in snapshot.risk_metrics:
                self.performance_metrics.volatility = snapshot.risk_metrics['volatility'] * 100
            
        except Exception as e:
            logger.error(f"❌ Error updating performance metrics: {e}")
    
    def _notify_callbacks(self, snapshot: TradingSnapshot):
        """Notify all registered callbacks of new data"""
        for callback in self.update_callbacks:
            try:
                callback(snapshot, self.performance_metrics)
            except Exception as e:
                logger.error(f"❌ Error in update callback {callback.__name__}: {e}")
    
    def get_current_data(self) -> Dict[str, Any]:
        """Get current trading data for dashboard"""
        if not self.current_snapshot:
            return {}
        
        return {
            'timestamp': self.current_snapshot.timestamp.isoformat(),
            'portfolio_value': self.current_snapshot.portfolio_value,
            'total_pnl': self.current_snapshot.total_pnl,
            'daily_pnl': self.current_snapshot.daily_pnl,
            'performance_metrics': {
                'total_return': self.performance_metrics.total_return,
                'daily_return': self.performance_metrics.daily_return,
                'sharpe_ratio': self.performance_metrics.sharpe_ratio,
                'max_drawdown': self.performance_metrics.max_drawdown,
                'current_drawdown': self.performance_metrics.current_drawdown,
                'volatility': self.performance_metrics.volatility,
                'total_trades': self.performance_metrics.total_trades
            },
            'positions': self.current_snapshot.positions,
            'orders': self.current_snapshot.orders,
            'risk_metrics': self.current_snapshot.risk_metrics,
            'strategy_performance': self.current_snapshot.strategy_performance
        }
    
    def get_historical_data(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get historical data for charts"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        historical_data = []
        for snapshot in self.snapshots:
            if snapshot.timestamp >= cutoff_time:
                historical_data.append({
                    'timestamp': snapshot.timestamp.isoformat(),
                    'portfolio_value': snapshot.portfolio_value,
                    'total_pnl': snapshot.total_pnl,
                    'daily_pnl': snapshot.daily_pnl
                })
        
        return historical_data
