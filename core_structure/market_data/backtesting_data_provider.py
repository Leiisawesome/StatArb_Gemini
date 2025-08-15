"""
Backtesting Data Provider
========================

Unified data provider that ensures all components use the same ClickHouse data
during backtesting scenarios.
"""

import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging
from core_structure.market_data.enhanced_clickhouse_loader import EnhancedClickHouseLoader, DataRequest

class BacktestingDataProvider:
    """
    Unified data provider for backtesting scenarios
    
    Ensures all components (execution engine, core engine, strategy components)
    use the same ClickHouse historical data source.
    """
    
    def __init__(self, clickhouse_loader: EnhancedClickHouseLoader, data_request: DataRequest):
        self.clickhouse_loader = clickhouse_loader
        self.data_request = data_request
        self.logger = logging.getLogger(__name__)
        
        # Load all data at initialization
        self.historical_data = None
        self.current_time_index = 0
        self.symbol_prices = {}  # Current prices for each symbol
        
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
            
            # Extract prices for all symbols from the row
            for symbol in self.data_request.symbols:
                # Assuming columns like 'AAPL_close', 'MSFT_close', etc.
                close_col = f"{symbol}_close"
                if close_col in row:
                    self.symbol_prices[symbol] = row[close_col]
                elif 'close' in row:  # Single symbol case
                    self.symbol_prices[symbol] = row['close']
                else:
                    # Fallback price
                    self.symbol_prices[symbol] = 100.0
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol (equivalent to real-time feed)"""
        return self.symbol_prices.get(symbol)
    
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
