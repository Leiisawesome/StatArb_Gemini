"""
Unified Data Loader
Provides a single interface for loading data from multiple sources.
"""
import pandas as pd
from typing import List, Optional, Dict, Any
import logging
from pathlib import Path

from .data_config import DataConfig, DataSource, BACKTEST_CONFIG
from .polygon_data_loader import PolygonDataLoader, load_intraday_data as polygon_load_intraday_data
from .data_loader import load_intraday_data as yfinance_load_intraday_data

logger = logging.getLogger(__name__)

class UnifiedDataLoader:
    """
    Unified data loader that can switch between different data sources.
    """
    
    def __init__(self, config: Optional[DataConfig] = None):
        """
        Initialize unified data loader.
        
        Args:
            config: Data configuration, defaults to backtest config
        """
        self.config = config or BACKTEST_CONFIG
        self.polygon_loader = None
        
        if self.config.source == DataSource.POLYGON_OFFLINE:
            self.polygon_loader = PolygonDataLoader(self.config.data_directory)
        
        logger.info(f"Initialized unified data loader with source: {self.config.source.value}")
    
    def load_data(self, 
                  symbols: List[str], 
                  start_date: str, 
                  end_date: str, 
                  interval: str = '1m',
                  data_type: str = 'close') -> pd.DataFrame:
        """
        Load data from the configured source.
        
        Args:
            symbols: List of stock symbols
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            interval: Data interval
            data_type: Type of data to return
            
        Returns:
            DataFrame with requested data
        """
        logger.info(f"Loading data from {self.config.source.value} for {symbols}")
        
        if self.config.source == DataSource.YFINANCE:
            return self._load_from_yfinance(symbols, start_date, end_date, interval, data_type)
        elif self.config.source == DataSource.POLYGON_OFFLINE:
            return self._load_from_polygon_offline(symbols, start_date, end_date, interval, data_type)
        elif self.config.source == DataSource.POLYGON_API:
            return self._load_from_polygon_api(symbols, start_date, end_date, interval, data_type)
        else:
            raise ValueError(f"Unsupported data source: {self.config.source}")
    
    def _load_from_yfinance(self, 
                           symbols: List[str], 
                           start_date: str, 
                           end_date: str, 
                           interval: str,
                           data_type: str) -> pd.DataFrame:
        """Load data from Yahoo Finance."""
        try:
            # Calculate duration for yfinance
            from datetime import datetime
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            duration_days = (end_dt - start_dt).days
            
            # Use the existing yfinance function
            data = yfinance_load_intraday_data(
                symbols, 
                duration_days, 
                interval, 
                self.config.validate_quality
            )
            
            # Filter to exact date range
            data = data[(data.index >= start_date) & (data.index <= end_date)]
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to load data from Yahoo Finance: {e}")
            return pd.DataFrame()
    
    def _load_from_polygon_offline(self, 
                                  symbols: List[str], 
                                  start_date: str, 
                                  end_date: str, 
                                  interval: str,
                                  data_type: str) -> pd.DataFrame:
        """Load data from Polygon.io offline files."""
        try:
            if self.polygon_loader is None:
                raise ValueError("Polygon loader not initialized")
            
            data = self.polygon_loader.load_multiple_symbols(
                symbols, start_date, end_date, interval, data_type
            )
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to load data from Polygon offline: {e}")
            return pd.DataFrame()
    
    def _load_from_polygon_api(self, 
                              symbols: List[str], 
                              start_date: str, 
                              end_date: str, 
                              interval: str,
                              data_type: str) -> pd.DataFrame:
        """Load data from Polygon.io API (placeholder for future implementation)."""
        logger.warning("Polygon API loading not yet implemented")
        return pd.DataFrame()
    
    def get_available_symbols(self) -> List[str]:
        """Get available symbols from the current data source."""
        if self.config.source == DataSource.POLYGON_OFFLINE and self.polygon_loader:
            return self.polygon_loader.get_available_symbols()
        else:
            logger.warning("Symbol availability not supported for current data source")
            return []
    
    def validate_data_quality(self, data: pd.DataFrame) -> tuple[bool, str]:
        """Validate data quality."""
        if self.config.source == DataSource.POLYGON_OFFLINE and self.polygon_loader:
            return self.polygon_loader.validate_data_quality(data)
        else:
            # Use basic validation
            if data.empty:
                return False, "Data is empty"
            if len(data) < 100:
                return False, f"Insufficient data points: {len(data)}"
            return True, "Data quality validation passed"

# Backward compatibility functions
def load_intraday_data(tickers: List[str], duration_days: int, interval: str, 
                      validate_quality: bool = True, 
                      data_source: str = "polygon_offline") -> pd.DataFrame:
    """
    Load intraday data with configurable data source.
    
    Args:
        tickers: List of ticker symbols
        duration_days: Number of days to load
        interval: Data interval
        validate_quality: Whether to validate data quality
        data_source: Data source to use ('yfinance', 'polygon_offline')
        
    Returns:
        DataFrame with price data
    """
    # Create config based on data source
    if data_source == "yfinance":
        config = DataConfig(source=DataSource.YFINANCE)
    elif data_source == "polygon_offline":
        config = DataConfig(source=DataSource.POLYGON_OFFLINE)
    else:
        raise ValueError(f"Unsupported data source: {data_source}")
    
    # Initialize loader
    loader = UnifiedDataLoader(config)
    
    # Calculate date range
    from datetime import datetime, timedelta
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=duration_days)).strftime('%Y-%m-%d')
    
    # Load data
    data = loader.load_data(tickers, start_date, end_date, interval, 'close')
    
    return data

def load_intraday_data_with_retry(tickers: List[str], duration_days: int, interval: str, 
                                 max_retries: int = 3, retry_delay: float = 1.0,
                                 data_source: str = "polygon_offline") -> pd.DataFrame:
    """
    Load intraday data with retry logic and configurable data source.
    """
    for attempt in range(max_retries):
        try:
            data = load_intraday_data(tickers, duration_days, interval, True, data_source)
            if not data.empty:
                return data
            
            if attempt < max_retries - 1:
                logger.info(f"Retry {attempt + 1}/{max_retries} in {retry_delay} seconds...")
                import time as time_module
                time_module.sleep(retry_delay)
                retry_delay *= 2
                
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                import time as time_module
                time_module.sleep(retry_delay)
                retry_delay *= 2
    
    return pd.DataFrame() 