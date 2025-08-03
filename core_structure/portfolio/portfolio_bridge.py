"""
PortfolioBridge: Core System ↔ Backtesting Framework Integration

This module provides a bridge between the core system's portfolio management
and the backtesting framework's portfolio requirements.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import time
from enum import Enum

logger = logging.getLogger(__name__)


class PortfolioMode(Enum):
    """Portfolio bridge operation modes"""
    PRODUCTION = "production"
    BACKTESTING = "backtesting"
    SIMULATION = "simulation"
    PAPER_TRADING = "paper_trading"


class PortfolioStatus(Enum):
    """Portfolio status levels"""
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"
    ERROR = "error"


@dataclass
class PortfolioBridgeConfig:
    """Configuration for PortfolioBridge"""
    portfolio_mode: PortfolioMode = PortfolioMode.BACKTESTING
    enable_position_tracking: bool = True
    enable_pnl_tracking: bool = True
    enable_risk_management: bool = True
    max_position_size: float = 0.1
    max_portfolio_risk: float = 0.02
    max_concurrent_operations: int = 10
    timeout_seconds: float = 10.0
    cache_size: int = 1000


@dataclass
class PortfolioBridgeResult:
    """Result from PortfolioBridge operations"""
    operation_type: str
    portfolio_id: str
    data: Union[pd.DataFrame, Dict[str, Any]]
    success: bool
    timestamp: datetime
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time_ms: float = 0.0
    error_message: Optional[str] = None


@dataclass
class PortfolioSnapshot:
    """Portfolio snapshot with current state"""
    portfolio_id: str
    total_value: float
    total_pnl: float
    total_pnl_pct: float
    realized_pnl: float
    unrealized_pnl: float
    cash_balance: float
    margin_used: float
    margin_available: float
    positions: Dict[str, Dict[str, Any]]
    risk_metrics: Dict[str, float]
    status: PortfolioStatus
    timestamp: datetime = field(default_factory=datetime.now)


class PortfolioBridge:
    """Bridge between core system portfolio management and backtesting framework."""
    
    def __init__(self, config: Optional[PortfolioBridgeConfig] = None):
        """Initialize PortfolioBridge with configuration"""
        self.config = config or PortfolioBridgeConfig()
        self.logger = logging.getLogger(f"{__name__}.PortfolioBridge")
        
        # Initialize caching and performance tracking
        self._portfolio_cache: Dict[str, Tuple[Any, datetime]] = {}
        self._performance_stats = {
            'total_operations': 0,
            'production_operations': 0,
            'backtesting_operations': 0,
            'cached_operations': 0,
            'errors': 0,
            'avg_processing_time': 0.0,
            'total_positions': 0
        }
        
        # Thread pool for concurrent operations
        self._executor = ThreadPoolExecutor(max_workers=self.config.max_concurrent_operations)
        
        self.logger.info(f"PortfolioBridge initialized in {self.config.portfolio_mode.value} mode")
    
    async def get_portfolio_snapshot(self, portfolio_id: str) -> PortfolioSnapshot:
        """Get current portfolio snapshot"""
        start_time_ms = time.time()
        
        try:
            # Check cache first
            cache_key = f"snapshot_{portfolio_id}"
            if cache_key in self._portfolio_cache:
                cached_data, cache_time = self._portfolio_cache[cache_key]
                if datetime.now() - cache_time < timedelta(minutes=1):
                    self._performance_stats['cached_operations'] += 1
                    return cached_data
            
            # Create mock portfolio snapshot
            snapshot = self._create_mock_snapshot(portfolio_id)
            
            # Cache the result
            self._portfolio_cache[cache_key] = (snapshot, datetime.now())
            
            # Update performance stats
            self._update_performance_stats('backtesting', time.time() - start_time_ms)
            
            return snapshot
            
        except Exception as e:
            self.logger.error(f"Error getting portfolio snapshot for {portfolio_id}: {e}")
            self._performance_stats['errors'] += 1
            return self._create_fallback_snapshot(portfolio_id)
    
    async def update_position(
        self,
        portfolio_id: str,
        symbol: str,
        quantity: float,
        price: float,
        operation: str = "buy"
    ) -> PortfolioBridgeResult:
        """Update portfolio position"""
        start_time_ms = time.time()
        
        try:
            # Validate position size
            if not self._validate_position_size(symbol, quantity, price):
                raise ValueError(f"Position size validation failed for {symbol}")
            
            # Mock position update
            result = {
                'symbol': symbol,
                'quantity': quantity,
                'price': price,
                'operation': operation,
                'timestamp': datetime.now()
            }
            
            # Update performance stats
            self._update_performance_stats('backtesting', time.time() - start_time_ms)
            
            return PortfolioBridgeResult(
                operation_type='position_update',
                portfolio_id=portfolio_id,
                data=result,
                success=True,
                timestamp=datetime.now(),
                source='backtesting',
                processing_time_ms=(time.time() - start_time_ms) * 1000
            )
            
        except Exception as e:
            self.logger.error(f"Error updating position for {portfolio_id}: {e}")
            self._performance_stats['errors'] += 1
            
            return PortfolioBridgeResult(
                operation_type='position_update',
                portfolio_id=portfolio_id,
                data={},
                success=False,
                timestamp=datetime.now(),
                source='fallback',
                processing_time_ms=(time.time() - start_time_ms) * 1000,
                error_message=str(e)
            )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return self._performance_stats.copy()
    
    def clear_cache(self) -> None:
        """Clear portfolio cache"""
        self._portfolio_cache.clear()
        self.logger.info("Portfolio cache cleared")
    
    def _create_mock_snapshot(self, portfolio_id: str) -> PortfolioSnapshot:
        """Create mock portfolio snapshot"""
        # Mock positions
        positions = {
            'AAPL': {
                'quantity': 100,
                'avg_price': 150.0,
                'current_price': 155.0,
                'market_value': 15500.0,
                'unrealized_pnl': 500.0,
                'unrealized_pnl_pct': 3.33
            },
            'GOOGL': {
                'quantity': 50,
                'avg_price': 2800.0,
                'current_price': 2850.0,
                'market_value': 142500.0,
                'unrealized_pnl': 2500.0,
                'unrealized_pnl_pct': 1.79
            }
        }
        
        total_value = sum(pos['market_value'] for pos in positions.values())
        total_pnl = sum(pos['unrealized_pnl'] for pos in positions.values())
        total_pnl_pct = (total_pnl / total_value * 100) if total_value > 0 else 0
        
        return PortfolioSnapshot(
            portfolio_id=portfolio_id,
            total_value=total_value,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            realized_pnl=0.0,
            unrealized_pnl=total_pnl,
            cash_balance=100000.0,
            margin_used=total_value * 0.5,
            margin_available=100000.0 - (total_value * 0.5),
            positions=positions,
            risk_metrics=self._calculate_basic_risk_metrics(positions),
            status=PortfolioStatus.ACTIVE
        )
    
    def _create_fallback_snapshot(self, portfolio_id: str) -> PortfolioSnapshot:
        """Create fallback portfolio snapshot"""
        return PortfolioSnapshot(
            portfolio_id=portfolio_id,
            total_value=0.0,
            total_pnl=0.0,
            total_pnl_pct=0.0,
            realized_pnl=0.0,
            unrealized_pnl=0.0,
            cash_balance=100000.0,
            margin_used=0.0,
            margin_available=100000.0,
            positions={},
            risk_metrics={},
            status=PortfolioStatus.ERROR
        )
    
    def _validate_position_size(self, symbol: str, quantity: float, price: float) -> bool:
        """Validate position size against limits"""
        try:
            position_value = abs(quantity * price)
            return position_value <= self.config.max_position_size * 1000000
        except Exception as e:
            self.logger.error(f"Error validating position size: {e}")
            return False
    
    def _calculate_basic_risk_metrics(self, positions: Dict[str, Any]) -> Dict[str, float]:
        """Calculate basic risk metrics for positions"""
        try:
            if not positions:
                return {}
            
            total_value = sum(pos['market_value'] for pos in positions.values())
            
            if total_value > 0:
                return {
                    'total_positions': len(positions),
                    'max_position_size': max(pos['market_value'] for pos in positions.values()) / total_value,
                    'avg_position_size': total_value / len(positions)
                }
            else:
                return {
                    'total_positions': len(positions),
                    'max_position_size': 0.0,
                    'avg_position_size': 0.0
                }
                
        except Exception as e:
            self.logger.error(f"Error calculating basic risk metrics: {e}")
            return {}
    
    def _update_performance_stats(self, source: str, processing_time: float):
        """Update performance statistics"""
        try:
            self._performance_stats['total_operations'] += 1
            self._performance_stats['total_positions'] += 1
            
            if source == 'production':
                self._performance_stats['production_operations'] += 1
            elif source == 'backtesting':
                self._performance_stats['backtesting_operations'] += 1
            
            # Update average processing time
            total_operations = self._performance_stats['total_operations']
            current_avg = self._performance_stats['avg_processing_time']
            new_avg = ((current_avg * (total_operations - 1)) + processing_time) / total_operations
            self._performance_stats['avg_processing_time'] = new_avg
            
        except Exception as e:
            self.logger.error(f"Error updating performance stats: {e}")


def create_portfolio_bridge(config: Optional[PortfolioBridgeConfig] = None) -> PortfolioBridge:
    """Factory function to create PortfolioBridge instance"""
    return PortfolioBridge(config)


def get_portfolio_for_backtesting(portfolio_id: str) -> PortfolioSnapshot:
    """Convenience function for backtesting portfolio retrieval"""
    config = PortfolioBridgeConfig(portfolio_mode=PortfolioMode.BACKTESTING)
    bridge = create_portfolio_bridge(config)
    
    # Check if there's already an event loop running
    try:
        loop = asyncio.get_running_loop()
        # Return empty snapshot as fallback
        return PortfolioSnapshot(
            portfolio_id=portfolio_id,
            total_value=0.0,
            total_pnl=0.0,
            total_pnl_pct=0.0,
            realized_pnl=0.0,
            unrealized_pnl=0.0,
            cash_balance=100000.0,
            margin_used=0.0,
            margin_available=100000.0,
            positions={},
            risk_metrics={},
            status=PortfolioStatus.ERROR
        )
    except RuntimeError:
        # No event loop running, we can create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            snapshot = loop.run_until_complete(
                bridge.get_portfolio_snapshot(portfolio_id)
            )
            return snapshot
        finally:
            loop.close() 