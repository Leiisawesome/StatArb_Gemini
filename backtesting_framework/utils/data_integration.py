#!/usr/bin/env python3
"""
Simplified Data Integration for Backtesting Framework

Provides integration with core system DataManager for ClickHouse data access.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import logging
import warnings

# Import core system components
try:
    import sys
    import os
    # Add the parent directory to the path to access core_structure
    current_file = os.path.abspath(__file__)
    # Go up three levels: utils/ -> backtesting_framework/ -> StatArb_Gemini/
    parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    sys.path.append(parent_dir)
    
    # Load .env file from the parent directory
    from dotenv import load_dotenv
    env_file = os.path.join(parent_dir, '.env')
    if os.path.exists(env_file):
        load_dotenv(env_file)
    
    from core_structure.market_data.data_manager import DataManager
    from core_structure.infrastructure.database.clickhouse_client import ClickHouseClient
    
    # Set up environment variables for ClickHouse
    env_mapping = {
        'CLICKHOUSE_HOST': 'DB_HOST',
        'CLICKHOUSE_PORT': 'DB_PORT', 
        'CLICKHOUSE_DATABASE': 'DB_NAME',
        'CLICKHOUSE_USER': 'DB_USER',
        'CLICKHOUSE_PASSWORD': 'DB_PASSWORD'
    }
    
    for clickhouse_var, db_var in env_mapping.items():
        clickhouse_value = os.getenv(clickhouse_var)
        if clickhouse_value:
            os.environ[db_var] = clickhouse_value
    
    CORE_SYSTEM_AVAILABLE = True
except ImportError:
    CORE_SYSTEM_AVAILABLE = False
    logging.error("Core system not available - DataManager import failed")

logger = logging.getLogger(__name__)

class DataIntegrationManager:
    """
    Simplified data integration manager for backtesting framework
    
    Provides unified interface for loading market data from ClickHouse
    via the core system's DataManager.
    """
    
    def __init__(self, cache_data: bool = True):
        """
        Initialize data integration manager
        
        Args:
            cache_data: Whether to cache loaded data
        """
        self.cache_data = cache_data
        self.data_cache: Dict[str, Dict[str, pd.DataFrame]] = {}
        
        # Initialize core system DataManager
        if CORE_SYSTEM_AVAILABLE:
            try:
                self.data_manager = DataManager()
                logger.info("Core system DataManager initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize core DataManager: {e}")
                raise RuntimeError(f"Cannot initialize DataManager: {e}")
        else:
            raise RuntimeError("Core system not available - cannot initialize DataManager")
        
        logger.info("DataIntegrationManager initialized - ClickHouse data access ready")
    
    def load_historical_data(
        self,
        symbols: List[str],
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
        interval: str = '1d',
        include_volume: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """
        Load historical market data from ClickHouse
        
        Args:
            symbols: List of symbols to load
            start_date: Start date for data
            end_date: End date for data
            interval: Data interval ('1d' for daily data)
            include_volume: Whether to include volume data
            
        Returns:
            Dictionary mapping symbols to DataFrames with OHLCV data
        """
        # Convert dates to datetime
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        
        logger.info(f"Loading ClickHouse data for {len(symbols)} symbols from {start_dt} to {end_dt}")
        
        # Check cache first
        cache_key = self._generate_cache_key(symbols, start_dt, end_dt, interval)
        if self.cache_data and cache_key in self.data_cache:
            logger.debug(f"Cache hit for {symbols}")
            return self.data_cache[cache_key]
        
        try:
            # Load data using core system DataManager with improved error handling
            processed_data = {}
            
            # Try loading each symbol individually to isolate connection issues
            for symbol in symbols:
                try:
                    logger.debug(f"Loading data for {symbol}")
                    
                    # Load single symbol
                    data = self.data_manager.load_historical_data(
                        symbols=[symbol],
                        start_date=start_dt,
                        end_date=end_dt
                    )
                    
                    if data and symbol in data and not data[symbol].empty:
                        # Process the data for this symbol
                        symbol_data = self._process_symbol_data(data[symbol], symbol, include_volume)
                        if symbol_data is not None and not symbol_data.empty:
                            processed_data[symbol] = symbol_data
                        else:
                            logger.warning(f"Processed data for {symbol} is empty")
                    else:
                        logger.warning(f"No raw data returned for {symbol}")
                        
                except Exception as e:
                    logger.error(f"Error loading data for {symbol}: {e}")
                    # Continue with other symbols even if one fails
                    continue
            
            # Validate the final processed data
            if processed_data:
                validation_results = self._validate_data(processed_data)
                if validation_results['errors']:
                    logger.error(f"Data validation errors: {validation_results['errors']}")
                if validation_results['warnings']:
                    logger.warning(f"Data validation warnings: {validation_results['warnings']}")
            
            # Cache data if enabled and we have valid data
            if self.cache_data and processed_data:
                self.data_cache[cache_key] = processed_data
                logger.debug(f"Cached data for {len(processed_data)} symbols")
            
            # Log data info
            if processed_data:
                data_info = self._get_data_info(processed_data)
                logger.info(f"Successfully loaded data for {len(processed_data)} symbols")
            else:
                logger.warning("No data was successfully loaded for any symbol")
            
            return processed_data
            
        except Exception as e:
            logger.error(f"Error loading data from ClickHouse: {e}")
            # Return empty dict instead of raising exception to allow test to continue
            return {}
    
    def _generate_cache_key(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        interval: str
    ) -> str:
        """Generate cache key for data request"""
        symbols_str = '-'.join(sorted(symbols))
        return f"clickhouse_{symbols_str}_{start_date.date()}_{end_date.date()}_{interval}"
    
    def _process_symbol_data(
        self,
        df: pd.DataFrame,
        symbol: str,
        include_volume: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        Process data for a single symbol
        
        Args:
            df: Raw DataFrame for the symbol
            symbol: Symbol name
            include_volume: Whether to include volume
            
        Returns:
            Processed DataFrame or None if processing fails
        """
        try:
            if df.empty:
                logger.warning(f"Empty data for {symbol}")
                return None
            
            # Create a copy to avoid modifying original
            processed_df = df.copy()
            
            # Ensure index is datetime
            if not isinstance(processed_df.index, pd.DatetimeIndex):
                if 'date' in processed_df.columns:
                    processed_df = processed_df.set_index('date')
                processed_df.index = pd.to_datetime(processed_df.index)
            
            # Sort by date
            processed_df = processed_df.sort_index()
            
            # Remove duplicates
            processed_df = processed_df[~processed_df.index.duplicated(keep='first')]
            
            # Check for required columns (case insensitive)
            column_mapping = {}
            required_columns = ['open', 'high', 'low', 'close']
            
            for req_col in required_columns:
                found_col = None
                for col in processed_df.columns:
                    if col.lower() == req_col.lower():
                        found_col = col
                        break
                if found_col:
                    column_mapping[found_col] = req_col
                else:
                    logger.warning(f"Missing required column '{req_col}' for {symbol}")
                    return None
            
            # Add volume if available and requested
            if include_volume:
                for col in processed_df.columns:
                    if col.lower() == 'volume':
                        column_mapping[col] = 'volume'
                        break
            
            # Rename columns to standard names
            processed_df = processed_df.rename(columns=column_mapping)
            
            # Select only the columns we want
            final_columns = ['open', 'high', 'low', 'close']
            if include_volume and 'volume' in processed_df.columns:
                final_columns.append('volume')
            
            # Filter to only existing columns
            available_columns = [col for col in final_columns if col in processed_df.columns]
            processed_df = processed_df[available_columns]
            
            # Fill missing values using the newer API
            processed_df = processed_df.ffill().bfill()
            
            # Remove rows with all NaN values
            processed_df = processed_df.dropna(how='all')
            
            if processed_df.empty:
                logger.warning(f"No valid data remaining for {symbol} after processing")
                return None
            
            logger.debug(f"Successfully processed {len(processed_df)} rows for {symbol}")
            return processed_df
            
        except Exception as e:
            logger.error(f"Error processing data for {symbol}: {e}")
            return None

    def _process_data(
        self,
        data: Dict[str, pd.DataFrame],
        include_volume: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """
        Process and standardize data format
        
        Args:
            data: Raw data from DataManager
            include_volume: Whether to include volume
            
        Returns:
            Processed data dictionary
        """
        processed_data = {}
        
        for symbol, df in data.items():
            processed_df = self._process_symbol_data(df, symbol, include_volume)
            if processed_df is not None:
                processed_data[symbol] = processed_df
        
        return processed_data
    
    def _validate_data(self, data: Dict[str, pd.DataFrame]) -> Dict[str, List[str]]:
        """
        Validate data quality
        
        Args:
            data: Data dictionary
            
        Returns:
            Dictionary with validation results
        """
        validation_results = {
            'warnings': [],
            'errors': []
        }
        
        for symbol, df in data.items():
            # Check for required columns
            required_columns = ['open', 'high', 'low', 'close']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                validation_results['errors'].append(
                    f"{symbol}: Missing columns {missing_columns}"
                )
            
            # Check for negative prices
            price_columns = ['open', 'high', 'low', 'close']
            for col in price_columns:
                if col in df.columns and (df[col] <= 0).any():
                    validation_results['warnings'].append(
                        f"{symbol}: Negative or zero prices in {col}"
                    )
            
            # Check OHLC relationships
            if all(col in df.columns for col in price_columns):
                invalid_high = (df['high'] < df[['open', 'close']].max(axis=1)).any()
                invalid_low = (df['low'] > df[['open', 'close']].min(axis=1)).any()
                
                if invalid_high:
                    validation_results['warnings'].append(
                        f"{symbol}: High price lower than open/close"
                    )
                if invalid_low:
                    validation_results['warnings'].append(
                        f"{symbol}: Low price higher than open/close"
                    )
            
            # Check for missing data
            missing_pct = df.isnull().sum() / len(df) * 100
            high_missing = missing_pct[missing_pct > 5]
            if not high_missing.empty:
                validation_results['warnings'].append(
                    f"{symbol}: High missing data percentage: {high_missing.to_dict()}"
                )
        
        return validation_results
    
    def _get_data_info(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        Get information about loaded data
        
        Args:
            data: Data dictionary
            
        Returns:
            Dictionary with data information
        """
        info = {
            'symbols': list(data.keys()),
            'total_symbols': len(data),
            'date_ranges': {},
            'data_points': {},
            'missing_data': {}
        }
        
        for symbol, df in data.items():
            info['date_ranges'][symbol] = {
                'start': df.index.min(),
                'end': df.index.max(),
                'days': len(df)
            }
            info['data_points'][symbol] = len(df)
            
            # Check for missing data
            missing = df.isnull().sum()
            if missing.any():
                info['missing_data'][symbol] = missing.to_dict()
        
        return info
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        cached_symbols = set()
        for key in self.data_cache.keys():
            parts = key.split('_')
            if len(parts) > 1:
                cached_symbols.add(parts[1])
        
        return {
            'cache_size': len(self.data_cache),
            'cached_symbols': list(cached_symbols)
        }
    
    def clear_cache(self):
        """Clear data cache"""
        self.data_cache.clear()
        logger.info("Data cache cleared")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the data integration"""
        return {
            'core_system_available': CORE_SYSTEM_AVAILABLE,
            'data_manager_initialized': hasattr(self, 'data_manager'),
            'cache_enabled': self.cache_data,
            'cache_size': len(self.data_cache)
        } 