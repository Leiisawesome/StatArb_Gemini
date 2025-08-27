#!/usr/bin/env python3
"""
Backtesting Data Provider
========================

Provides historical market data for backtesting with production safety validation.

Author: Pro Quant Desk Trader
"""

import pandas as pd
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

# Production safety imports
from ..infrastructure.production_safety import (
    ProductionSafetyFramework, Environment, SafetyLevel, 
    production_safe, ValidationError, FailureMode
)

logger = logging.getLogger(__name__)


class BacktestingDataProvider:
    """
    Provides historical market data for backtesting with production safety validation
    """
    
    def __init__(self, clickhouse_loader, data_request):
        """Initialize backtesting data provider"""
        self.clickhouse_loader = clickhouse_loader
        self.data_request = data_request
        self.historical_data: Optional[pd.DataFrame] = None
        self.symbol_prices: Dict[str, Any] = {}
        self.current_time_index = 0
        self.logger = logging.getLogger(__name__)
        
        # Initialize production safety framework
        self.safety_framework = ProductionSafetyFramework()
        
        # Log safety framework status
        current_env = self.safety_framework.get_current_environment()
        self.logger.info(f"🛡️ Backtesting Data Provider - Environment: {current_env.value}")
        
    @production_safe(FailureMode.MARKET_DATA_UNAVAILABLE)
    async def initialize(self):
        """Load historical data from ClickHouse"""
        try:
            self.logger.info("Loading historical data from ClickHouse...")
            self.historical_data = await self.clickhouse_loader.load_market_data(self.data_request)
            
            if self.historical_data is not None and not self.historical_data.empty:
                self.logger.info(f"✅ Loaded {len(self.historical_data)} data points from ClickHouse")
                # Initialize current prices to first data point
                self._update_current_prices(0)
            else:
                self.logger.warning("⚠️  No historical data loaded from ClickHouse")
                
        except Exception as e:
            self.logger.error(f"Failed to load ClickHouse data: {e}")
            self.historical_data = pd.DataFrame()
    
    def advance_time(self, time_index: int):
        """Advance to specific time index in historical data"""
        if self.historical_data is not None and not self.historical_data.empty:
            max_index = len(self.historical_data) - 1
            self.current_time_index = min(time_index, max_index)
            self._update_current_prices(self.current_time_index)
    
    def _update_current_prices(self, index: int):
        """Update current prices from historical data at specific index"""
        if self.historical_data is not None and not self.historical_data.empty and index < len(self.historical_data):
            row = self.historical_data.iloc[index]
            
            # Extract OHLC prices for all symbols from the row
            for symbol in self.data_request.symbols:
                # Store OHLC data for realistic execution pricing
                symbol_data = {}
                
                # Try symbol-specific columns first (e.g., 'TSLA_close', 'TSLA_high')
                for price_type in ['open', 'high', 'low', 'close']:
                    symbol_col = f"{symbol}_{price_type}"
                    if symbol_col in row:
                        symbol_data[price_type] = row[symbol_col]
                    elif price_type in row:  # Single symbol case
                        symbol_data[price_type] = row[price_type]
                
                if not symbol_data:
                    # 🛡️ PRODUCTION SAFETY: No fallbacks, fail fast with clear error message
                    current_env = self.safety_framework.get_current_environment()
                    
                    if current_env in [Environment.PRODUCTION, Environment.STAGING]:
                        self.safety_framework.record_violation(
                            "missing_symbol_data",
                            f"No price columns found for {symbol} in historical data",
                            critical=True
                        )
                        raise ValidationError(f"❌ DATA ERROR: No price columns found for {symbol} in historical data. "
                                           f"Available columns: {list(row.index)}. "
                                           f"Expected: '{symbol}_open/high/low/close' or 'open/high/low/close'. "
                                           f"Fix the data loading or column mapping!")
                    else:  # DEVELOPMENT
                        self.logger.warning(f"💻 DEVELOPMENT: Missing symbol data for {symbol}, using defaults")
                        symbol_data = {'open': 100.0, 'high': 105.0, 'low': 95.0, 'close': 102.0}
                
                # Store the complete OHLC data for this symbol
                self.symbol_prices[symbol] = symbol_data
                
                # Also store a default 'current_price' for backward compatibility
                # Use close price as the default current price
                if 'close' in symbol_data:
                    self.symbol_prices[f"{symbol}_current"] = symbol_data['close']
    
    @production_safe(FailureMode.PRICE_DATA_MISSING)
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol (equivalent to real-time feed)"""
        # Check for backward compatibility first
        if f"{symbol}_current" in self.symbol_prices:
            return self.symbol_prices[f"{symbol}_current"]
        
        # Check if we have OHLC data
        symbol_data = self.symbol_prices.get(symbol)
        if isinstance(symbol_data, dict) and 'close' in symbol_data:
            return symbol_data['close']
        
        # 🛡️ PRODUCTION SAFETY: Handle missing data according to environment
        current_env = self.safety_framework.get_current_environment()
        
        if current_env in [Environment.PRODUCTION, Environment.STAGING]:
            # No fallbacks in production/staging
            self.safety_framework.record_violation(
                "missing_current_price",
                f"No current price available for {symbol}",
                critical=False
            )
            return None
        else:  # DEVELOPMENT
            # Allow fallback in development
            return self.symbol_prices.get(symbol, 100.0)  # Default development price
    
    @production_safe(FailureMode.PRICE_DATA_MISSING)
    def get_execution_price(self, symbol: str, side: str) -> Optional[float]:
        """
        Get realistic execution price based on order side with production safety validation
        - BUY orders: Use close price (realistic market entry)
        - SELL orders: Use high price (capture profitable exits)
        """
        symbol_data = self.symbol_prices.get(symbol)
        if not isinstance(symbol_data, dict):
            # 🛡️ PRODUCTION SAFETY: Handle missing OHLC data according to environment
            current_env = self.safety_framework.get_current_environment()
            
            if current_env in [Environment.PRODUCTION, Environment.STAGING]:
                # No fallbacks in production/staging
                self.safety_framework.record_violation(
                    "missing_ohlc_data",
                    f"No OHLC data available for {symbol}",
                    critical=False
                )
                return self.get_current_price(symbol)
            else:  # DEVELOPMENT
                # Allow fallback in development
                return self.get_current_price(symbol) or 100.0
        
        if side.upper() == 'BUY':
            # For BUY orders, use close price (realistic entry)
            return symbol_data.get('close', symbol_data.get('high'))
        elif side.upper() == 'SELL':
            # For SELL orders, use high price (capture profitable exits)
            return symbol_data.get('high', symbol_data.get('close'))
        else:
            # Default to close price
            return symbol_data.get('close')
    
    def get_historical_data(self, symbol: str, lookback_periods: int = 100) -> pd.DataFrame:
        """Get historical data for symbol with lookback"""
        if self.historical_data is None or self.historical_data.empty:
            return pd.DataFrame()
        
        # Get data up to current time index
        end_index = self.current_time_index + 1
        start_index = max(0, end_index - lookback_periods)
        
        return self.historical_data.iloc[start_index:end_index].copy()
    
    def get_market_data_snapshot(self) -> Dict[str, Any]:
        """Get current market data snapshot for all symbols"""
        return {
            'symbols': list(self.symbol_prices.keys()),
            'prices': self.symbol_prices.copy(),
            'timestamp': datetime.now(),
            'data_source': 'ClickHouse',
            'current_index': self.current_time_index
        }
