"""
Core Engine Data Types

Lightweight data management for standalone core_engine.
"""

from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging


@dataclass
class DataConfig:
    """Data source configuration"""
    provider: str = "yahoo"  # Default to Yahoo Finance
    update_frequency: str = "1min"  # Data update frequency
    cache_enabled: bool = True
    cache_duration: int = 300  # 5 minutes cache
    
    # Data quality settings
    fill_missing: bool = True
    validate_data: bool = True
    outlier_detection: bool = True
    outlier_threshold: float = 3.0  # Standard deviations


@dataclass
class MarketData:
    """Market data container"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    
    # Additional fields
    adjusted_close: Optional[float] = None
    dividend: Optional[float] = None
    split_ratio: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'adjusted_close': self.adjusted_close,
            'dividend': self.dividend,
            'split_ratio': self.split_ratio
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MarketData':
        """Create from dictionary"""
        return cls(**data)


class DataProvider(ABC):
    """Abstract data provider interface"""
    
    @abstractmethod
    def get_historical_data(self, symbol: str, start_date: datetime, 
                          end_date: datetime, timeframe: str = "1d") -> pd.DataFrame:
        """Get historical market data"""
    
    @abstractmethod
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price"""
    
    @abstractmethod
    def get_multiple_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get current prices for multiple symbols"""


class YahooDataProvider(DataProvider):
    """Yahoo Finance data provider (lightweight implementation)"""
    
    def __init__(self):
        self._cache: Dict[str, tuple] = {}  # symbol -> (data, timestamp)
        self._cache_duration = timedelta(minutes=5)
    
    def get_historical_data(self, symbol: str, start_date: datetime, 
                          end_date: datetime, timeframe: str = "1d") -> pd.DataFrame:
        """Get historical data from Yahoo Finance"""
        try:
            import yfinance as yf
            
            # Create ticker
            ticker = yf.Ticker(symbol)
            
            # Get data
            data = ticker.history(start=start_date, end=end_date, interval=timeframe)
            
            if data.empty:
                # Return empty DataFrame with required columns
                return pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])
            
            # Standardize column names
            data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            data.index.name = 'Date'
            
            return data
            
        except ImportError:
            # Fallback: generate synthetic data
            return self._generate_synthetic_data(symbol, start_date, end_date)
        except Exception as e:
            self.logger.error(f"Error fetching data for {symbol}: {e}")
            return self._generate_synthetic_data(symbol, start_date, end_date)
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol"""
        # Check cache first
        cache_key = f"{symbol}_current"
        if cache_key in self._cache:
            data, timestamp = self._cache[cache_key]
            if datetime.now() - timestamp < self._cache_duration:
                return data
        
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            info = ticker.info
            price = info.get('currentPrice') or info.get('regularMarketPrice')
            
            # Cache result
            self._cache[cache_key] = (price, datetime.now())
            return price
            
        except Exception:
            # Fallback: use last known price or synthetic
            historical = self.get_historical_data(symbol, 
                                                datetime.now() - timedelta(days=2), 
                                                datetime.now())
            if not historical.empty:
                return float(historical['Close'].iloc[-1])
            return 100.0  # Default price
    
    def get_multiple_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get current prices for multiple symbols"""
        prices = {}
        for symbol in symbols:
            price = self.get_current_price(symbol)
            if price is not None:
                prices[symbol] = price
        return prices
    
    def _generate_synthetic_data(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Generate synthetic market data for testing"""
        # Create date range
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Generate synthetic price data
        np.random.seed(hash(symbol) % 1000)  # Consistent seed per symbol
        returns = np.random.normal(0.001, 0.02, len(dates))  # 0.1% daily return, 2% volatility
        
        # Starting price based on symbol hash
        start_price = 50 + (hash(symbol) % 200)
        
        prices = [start_price]
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        # Create OHLCV data
        data = []
        for i, (date, close) in enumerate(zip(dates, prices)):
            # Generate OHLC from close
            volatility = 0.01  # 1% intraday volatility
            high = close * (1 + np.random.uniform(0, volatility))
            low = close * (1 - np.random.uniform(0, volatility))
            open_price = low + (high - low) * np.random.uniform(0.2, 0.8)
            volume = int(np.random.uniform(1000000, 10000000))
            
            data.append({
                'Open': open_price,
                'High': high,
                'Low': low,
                'Close': close,
                'Volume': volume
            })
        
        df = pd.DataFrame(data, index=dates)
        df.index.name = 'Date'
        return df


class DataManager:
    """Core data management"""
    
    def __init__(self, config: DataConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.provider = self._create_provider()
        self._data_cache: Dict[str, pd.DataFrame] = {}
        self._last_update: Dict[str, datetime] = {}
    
    def _create_provider(self) -> DataProvider:
        """Create data provider based on config"""
        if self.config.provider.lower() == "yahoo":
            return YahooDataProvider()
        else:
            raise ValueError(f"Unsupported data provider: {self.config.provider}")
    
    def get_data(self, symbol: str, start_date: datetime, 
                end_date: datetime, timeframe: str = "1d") -> pd.DataFrame:
        """Get market data with caching"""
        cache_key = f"{symbol}_{timeframe}_{start_date}_{end_date}"
        
        # Check cache
        if (self.config.cache_enabled and 
            cache_key in self._data_cache and
            cache_key in self._last_update):
            
            cache_age = datetime.now() - self._last_update[cache_key]
            if cache_age.total_seconds() < self.config.cache_duration:
                return self._data_cache[cache_key]
        
        # Fetch new data
        data = self.provider.get_historical_data(symbol, start_date, end_date, timeframe)
        
        # Validate and clean data
        if self.config.validate_data:
            data = self._validate_data(data)
        
        if self.config.fill_missing:
            data = self._fill_missing_data(data)
        
        if self.config.outlier_detection:
            data = self._handle_outliers(data)
        
        # Cache result
        if self.config.cache_enabled:
            self._data_cache[cache_key] = data
            self._last_update[cache_key] = datetime.now()
        
        return data
    
    def get_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get current prices for symbols"""
        return self.provider.get_multiple_prices(symbols)
    
    def _validate_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Validate data quality"""
        if data.empty:
            return data
        
        # Remove rows with invalid prices
        data = data[(data['High'] >= data['Low']) & 
                   (data['Close'] > 0) & 
                   (data['Volume'] >= 0)]
        
        # Ensure OHLC consistency
        data = data[(data['Open'] >= data['Low']) & (data['Open'] <= data['High']) &
                   (data['Close'] >= data['Low']) & (data['Close'] <= data['High'])]
        
        return data
    
    def _fill_missing_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Fill missing data points"""
        if data.empty:
            return data
        
        # Forward fill missing values
        data = data.fillna(method='ffill')
        
        # If still missing, backward fill
        data = data.fillna(method='bfill')
        
        return data
    
    def _handle_outliers(self, data: pd.DataFrame) -> pd.DataFrame:
        """Handle outlier data points"""
        if data.empty or len(data) < 10:
            return data
        
        # Calculate returns for outlier detection
        returns = data['Close'].pct_change().dropna()
        
        # Identify outliers using z-score
        z_scores = np.abs((returns - returns.mean()) / returns.std())
        outlier_mask = z_scores > self.config.outlier_threshold
        
        # Replace outlier returns with median
        if outlier_mask.any():
            median_return = returns.median()
            outlier_indices = returns[outlier_mask].index
            
            for idx in outlier_indices:
                if idx in data.index and idx != data.index[0]:
                    prev_idx = data.index[data.index.get_loc(idx) - 1]
                    data.loc[idx, 'Close'] = data.loc[prev_idx, 'Close'] * (1 + median_return)
                    
                    # Adjust OHLC to be consistent with new close
                    data.loc[idx, 'High'] = max(data.loc[idx, 'Close'], data.loc[idx, 'High'])
                    data.loc[idx, 'Low'] = min(data.loc[idx, 'Close'], data.loc[idx, 'Low'])
        
        return data